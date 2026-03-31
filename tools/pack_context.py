#!/usr/bin/env python3
"""
pack_context.py — 為本地 LLM 打包 context（自含式 markdown）

所有資料直接 import DB 類別讀取，不經 Agent，不留路徑讓 LLM 自己讀。
按 token budget 分層填充，超過就停。

用法:
  # 審查打包（指定章節範圍）
  python tools/pack_context.py --proj bnf review --chapters 55-57

  # 審查打包（單章）
  python tools/pack_context.py --proj bnf review --chapters 55

  # 生成打包（給前後文 + 指令）
  python tools/pack_context.py --proj bnf generate --chapter 58 --instruction-file /path/to/prompt.md

  # 指定 budget（預設 80000）
  python tools/pack_context.py --proj bnf review --chapters 55-57 --budget 80000

  # 輸出到檔案（預設 stdout）
  python tools/pack_context.py --proj bnf review --chapters 55-57 -o /tmp/packed.md

輸出: 自含式 markdown，直接餵給 local_llm.py
"""

import argparse
import glob
import json
import os
import re
import sys
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.char_db import CharacterDB
from tools.item_db import ItemDB
from tools.faction_db import FactionDB
from tools.atlas_db import AtlasDB
from tools.lore_vector import ChapterVector, LoreVector, get_project_folder

PROJECT_ROOT = os.path.join(ROOT_DIR, "projects")


# ── Token 估算 ────────────────────────────────────────────
def estimate_tokens(text: str) -> int:
    """粗估 token 數：中文字×1.5 + 英文 word×1.3 + 標點"""
    if not text:
        return 0
    cn = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    punc = len(re.findall(r'[\u3000-\u303f\uff01-\uff60\u2018-\u201f\u2014\u2026]', text))
    en = len(re.findall(r'[a-zA-Z0-9]+', text))
    return int(cn * 1.5 + punc + en * 1.3)


class ContextPacker:
    """分層打包器"""

    def __init__(self, proj_alias: str, budget: int = 80000):
        self.proj_alias = proj_alias
        self.budget = budget
        self.used = 0
        self.sections = []

        # 解析專案路徑
        folder = get_project_folder(proj_alias)
        if not folder:
            print(f"找不到專案: {proj_alias}", file=sys.stderr)
            sys.exit(1)
        self.project_dir = os.path.join(PROJECT_ROOT, folder)
        self.config_dir = os.path.join(self.project_dir, "config")
        # 章節可能在 output/chapters/ 或 chapters/
        ch_dir = os.path.join(self.project_dir, "output", "chapters")
        if not os.path.isdir(ch_dir):
            ch_dir = os.path.join(self.project_dir, "chapters")
        self.chapters_dir = ch_dir

        # DB instances (lazy)
        self._char_db = None
        self._item_db = None
        self._faction_db = None
        self._atlas_db = None
        self._chapter_vec = None
        self._lore_vec = None

    # ── DB lazy init ──
    @property
    def char_db(self):
        if not self._char_db:
            self._char_db = CharacterDB(self.proj_alias)
        return self._char_db

    @property
    def item_db(self):
        if not self._item_db:
            self._item_db = ItemDB(self.proj_alias)
        return self._item_db

    @property
    def faction_db(self):
        if not self._faction_db:
            self._faction_db = FactionDB(self.proj_alias)
        return self._faction_db

    @property
    def atlas_db(self):
        if not self._atlas_db:
            self._atlas_db = AtlasDB(self.proj_alias)
        return self._atlas_db

    @property
    def chapter_vec(self):
        if not self._chapter_vec:
            self._chapter_vec = ChapterVector(self.proj_alias)
        return self._chapter_vec

    @property
    def lore_vec(self):
        if not self._lore_vec:
            self._lore_vec = LoreVector(self.proj_alias)
        return self._lore_vec

    # ── 工具 ──
    def _try_add(self, title: str, content: str) -> bool:
        """嘗試加入一個 section，超 budget 回傳 False"""
        tokens = estimate_tokens(content)
        if self.used + tokens > self.budget:
            return False
        self.sections.append(f"## {title}\n\n{content}")
        self.used += tokens
        return True

    def _force_add(self, title: str, content: str):
        """強制加入（Priority 1，不檢查 budget）"""
        tokens = estimate_tokens(content)
        self.sections.append(f"## {title}\n\n{content}")
        self.used += tokens

    def _read_file(self, path: str) -> str:
        """安全讀檔"""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _read_chapter(self, ch_num: int) -> str:
        """讀取章節檔案（嘗試多種命名格式）"""
        candidates = [
            f"chapter_{ch_num}.md",
            f"chapter_{ch_num:02d}.md",
            f"chapter_{ch_num:03d}.md",
        ]
        for name in candidates:
            path = os.path.join(self.chapters_dir, name)
            if os.path.isfile(path):
                return self._read_file(path)
        return ""

    def _extract_appearing_chars(self, texts: list) -> list:
        """從章節文本中提取登場角色 ID"""
        all_chars = self.char_db.list_characters()
        found_ids = set()
        combined = "\n".join(texts)
        for c in all_chars:
            name = c["name"]
            # 名字可能是 "林默 (Lin Mo)" 格式，取中文部分
            cn_name = re.split(r'\s*[\(（]', name)[0].strip()
            if cn_name and cn_name in combined:
                found_ids.add(c["id"])
        return list(found_ids)

    def _get_config_rules(self) -> str:
        """從 novel_config.yaml 摘取關鍵規則"""
        path = os.path.join(self.config_dir, "novel_config.yaml")
        raw = self._read_file(path)
        if not raw:
            return ""
        try:
            cfg = yaml.safe_load(raw)
        except Exception:
            return raw[:3000]

        parts = []
        # 摘取關鍵 section
        for key in ["world_rules", "forbidden_words", "writing_rules",
                     "naming_conventions", "power_rules", "genre", "setting"]:
            if key in cfg:
                val = cfg[key]
                if isinstance(val, (dict, list)):
                    parts.append(f"### {key}\n```yaml\n{yaml.dump(val, allow_unicode=True, default_flow_style=False).strip()}\n```")
                else:
                    parts.append(f"### {key}\n{val}")
        return "\n\n".join(parts) if parts else raw[:3000]

    def _get_progress_excerpt(self, target_chapters: list) -> str:
        """從 narrative_progress.yaml 摘取進度摘要（容許不同 YAML 結構）"""
        path = os.path.join(self.config_dir, "narrative_progress.yaml")
        raw = self._read_file(path)
        if not raw:
            return ""
        try:
            prog = yaml.safe_load(raw)
        except Exception:
            return raw[:2000]

        if not isinstance(prog, dict):
            return raw[:2000]

        parts = []

        # current_chapter 可能在頂層或 progress 子層
        cur_ch = prog.get("current_chapter")
        if not cur_ch:
            p = prog.get("progress", {})
            if isinstance(p, dict):
                cur_ch = p.get("current_chapter")
        if not cur_ch:
            cs = prog.get("current_state", {})
            if isinstance(cs, dict):
                cur_ch = cs.get("current_chapter")
        parts.append(f"current_chapter: {cur_ch or '?'}")

        # 嘗試提取 subarc 資訊（結構因專案而異）
        def _scan_arcs(arcs):
            """掃描 arc list/dict 找匹配的 subarc"""
            if isinstance(arcs, list):
                for arc in arcs:
                    if isinstance(arc, dict):
                        _scan_arc(arc)
            elif isinstance(arcs, dict):
                _scan_arc(arcs)

        def _scan_arc(arc):
            for sa in arc.get("completed_subarcs", []):
                if not isinstance(sa, dict):
                    continue
                chapters = sa.get("chapters", [])
                if any(ch in chapters for ch in target_chapters):
                    parts.append(f"\n### {sa.get('id', '?')} ({sa.get('title', '')})")
                    parts.append(f"chapters: {chapters}")
                    if sa.get("ending_summary"):
                        parts.append(f"ending: {sa['ending_summary'][:200]}")
            cur = arc.get("current_subarc", {})
            if isinstance(cur, dict) and cur:
                chapters = cur.get("chapters", [])
                if any(ch in chapters for ch in target_chapters) or not chapters:
                    parts.append(f"\n### [current] {cur.get('id', '?')} ({cur.get('title', '')})")
                    if cur.get("summary"):
                        parts.append(f"summary: {cur['summary'][:300]}")

        # 各種可能的 key
        for key in ["progress", "arcs", "current_state"]:
            val = prog.get(key)
            if val:
                _scan_arcs(val)

        # current_beat（多數專案有）
        cb = prog.get("current_beat")
        if isinstance(cb, dict):
            parts.append(f"\ncurrent_beat: {cb.get('id', '?')} — {cb.get('title', '')}")

        return "\n".join(parts)

    def _get_chapter_summaries(self, n: int = 10) -> str:
        """從 ChromaDB 取最近 N 章摘要"""
        try:
            recent = self.chapter_vec.get_recent_chapters(n=n)
        except Exception:
            return ""
        if not recent:
            return ""
        lines = []
        for ch in recent:
            cid = ch.get("chapter_id", "?")
            title = ch.get("title", "")
            summary = ch.get("ending_summary", "")
            lines.append(f"Ch.{cid} {title}: {summary}")
        return "\n".join(lines)

    def _get_power_system_excerpt(self) -> str:
        """讀取 power_system.yaml 摘要"""
        path = os.path.join(self.config_dir, "power_system.yaml")
        raw = self._read_file(path)
        if not raw:
            return ""
        # 只取前 3000 字元（通常包含核心規則）
        if len(raw) > 3000:
            return raw[:3000] + "\n...(截斷)"
        return raw

    # ── 打包模式 ──

    def pack_review(self, chapters: list) -> str:
        """審查模式打包"""
        # Priority 1: 指令 + 目標章節全文
        self._force_add("指令", (
            "你是繁體中文小說審查助手。請對以下章節執行一致性審查。\n"
            "只列出你**有把握**的問題，格式：\n"
            "- [Critical/Warning/Minor] [Ch.N] 問題描述 | 原文：「...」| 建議：...\n\n"
            "重點檢查：情節邏輯矛盾、吃書（與設定規則矛盾）、資訊邊界違反（角色知道不該知道的事）、"
            "能力合法性、錯字。不確定的標 [不確定]。\n"
            "不要有任何廢話、開場白、總結語。直接列出發現。沒有問題就回「無發現」。"
        ))

        chapter_texts = []
        for ch_num in chapters:
            text = self._read_chapter(ch_num)
            if text:
                self._force_add(f"第 {ch_num} 章（審查目標）", text)
                chapter_texts.append(text)
            else:
                self._force_add(f"第 {ch_num} 章", "（找不到章節檔案）")

        # Priority 2: 角色、設定、進度
        char_ids = self._extract_appearing_chars(chapter_texts)
        if char_ids:
            chars_data = []
            for cid in char_ids:
                ch = self.char_db.get_character(cid)
                if ch:
                    chars_data.append(ch)
            if chars_data:
                self._try_add("登場角色", json.dumps(chars_data, ensure_ascii=False, indent=1))

        rules = self._get_config_rules()
        if rules:
            self._try_add("設定規則（novel_config 摘取）", rules)

        progress = self._get_progress_excerpt(chapters)
        if progress:
            self._try_add("進度摘要", progress)

        # Priority 3: 前文摘要、前文章節
        summaries = self._get_chapter_summaries(n=10)
        if summaries:
            self._try_add("前文摘要（ChromaDB）", summaries)

        # 嘗試加入前 1-2 章全文
        min_ch = min(chapters)
        for prev in range(max(1, min_ch - 2), min_ch):
            text = self._read_chapter(prev)
            if text:
                if not self._try_add(f"第 {prev} 章（前文參照）", text):
                    break  # budget 不夠了

        # Priority 4: 能力系統
        power = self._get_power_system_excerpt()
        if power:
            self._try_add("能力系統", power)

        return self._build_output("review", chapters)

    def pack_generate(self, chapter: int, instruction: str = "") -> str:
        """生成模式打包"""
        # Priority 1: 指令
        if not instruction:
            instruction = "請根據以下前文和設定，撰寫下一個場景。直接輸出內容，不要前言或解說。"
        self._force_add("生成指令", instruction)

        # Priority 2: 前文章節全文（最近 1-2 章）
        chapter_texts = []
        for prev in range(max(1, chapter - 2), chapter):
            text = self._read_chapter(prev)
            if text:
                self._force_add(f"第 {prev} 章（前文）", text)
                chapter_texts.append(text)

        # 如果目標章節已存在（擴寫場景），也加入
        target_text = self._read_chapter(chapter)
        if target_text:
            self._force_add(f"第 {chapter} 章（當前草稿）", target_text)
            chapter_texts.append(target_text)

        # Priority 2: 角色
        char_ids = self._extract_appearing_chars(chapter_texts) if chapter_texts else []
        if char_ids:
            chars_data = []
            for cid in char_ids:
                ch = self.char_db.get_character(cid)
                if ch:
                    # generate 模式不給 hidden_profile
                    bp = ch.get("base_profile", {})
                    bp.pop("secret", None)
                    bp.pop("hidden_profile", None)
                    bp.pop("hidden_skills", None)
                    chars_data.append(ch)
            if chars_data:
                self._try_add("角色資料", json.dumps(chars_data, ensure_ascii=False, indent=1))

        # Priority 2: 設定
        rules = self._get_config_rules()
        if rules:
            self._try_add("設定規則", rules)

        # Priority 3: 前文摘要
        summaries = self._get_chapter_summaries(n=8)
        if summaries:
            self._try_add("前文摘要", summaries)

        # Priority 3: 進度
        progress = self._get_progress_excerpt([chapter])
        if progress:
            self._try_add("進度摘要", progress)

        # Priority 4: 能力系統
        power = self._get_power_system_excerpt()
        if power:
            self._try_add("能力系統", power)

        return self._build_output("generate", [chapter])

    def _build_output(self, mode: str, chapters: list) -> str:
        """組裝最終輸出"""
        if self.used > self.budget:
            print(f"⚠️ 超過 budget: {self.used}/{self.budget} tokens。"
                  f"建議減少章節數。", file=sys.stderr)
        header = (
            f"# Context Pack | {self.proj_alias} | mode={mode} | "
            f"chapters={','.join(str(c) for c in chapters)} | "
            f"tokens≈{self.used}/{self.budget}\n"
        )
        return header + "\n" + "\n\n".join(self.sections)


# ── CLI ──────────────────────────────────────────────────
def parse_chapters(s: str) -> list:
    """解析 '55-57' 或 '55' 為 list"""
    if "-" in s:
        a, b = s.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s)]


def main():
    parser = argparse.ArgumentParser(description="為本地 LLM 打包 context")
    parser.add_argument("--proj", required=True, help="專案別名")
    parser.add_argument("--budget", type=int, default=80000, help="Token budget (預設 80000)")
    parser.add_argument("-o", "--output", help="輸出路徑（預設 stdout）")
    sub = parser.add_subparsers(dest="mode", required=True)

    # review
    p_rev = sub.add_parser("review", help="審查模式")
    p_rev.add_argument("--chapters", required=True, help="章節範圍，如 55-57 或 55")

    # generate
    p_gen = sub.add_parser("generate", help="生成模式")
    p_gen.add_argument("--chapter", type=int, required=True, help="目標章節號")
    p_gen.add_argument("--instruction-file", help="生成指令檔路徑")
    p_gen.add_argument("--instruction", help="直接輸入生成指令")

    args = parser.parse_args()
    packer = ContextPacker(args.proj, budget=args.budget)

    if args.mode == "review":
        chapters = parse_chapters(args.chapters)
        result = packer.pack_review(chapters)
    elif args.mode == "generate":
        instruction = ""
        if args.instruction_file:
            with open(args.instruction_file, "r", encoding="utf-8") as f:
                instruction = f.read()
        elif args.instruction:
            instruction = args.instruction
        result = packer.pack_generate(args.chapter, instruction)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"已打包: {args.output} (≈{packer.used} tokens)", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
