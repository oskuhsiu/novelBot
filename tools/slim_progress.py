#!/usr/bin/env python3
"""
slim_progress.py — narrative_progress.yaml 瘦身 + 章節入 ChromaDB

功能：
  1. 從 narrative_progress.yaml 提取所有 completed_chapters
  2. 寫入 ChromaDB chapters collection
  3. 從 narrative_progress.yaml 移除 completed_chapters
  4. 刪除 YAML archive 檔案（若存在）

用法：
  python tools/slim_progress.py --proj bnf
  python tools/slim_progress.py --proj bnf --dry-run
  python tools/slim_progress.py --all
"""

import argparse
import os
import re
import sys
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
PROJECTS_DIR = os.path.join(ROOT_DIR, "projects")
REGISTRY_PATH = os.path.join(PROJECTS_DIR, "project_registry.yaml")

sys.path.insert(0, ROOT_DIR)
from tools.lore_vector import ChapterVector, get_project_folder


def get_all_projects() -> list[str]:
    """取得所有有 narrative_progress.yaml 的專案"""
    results = []
    for d in os.listdir(PROJECTS_DIR):
        prog = os.path.join(PROJECTS_DIR, d, "config", "narrative_progress.yaml")
        if os.path.isfile(prog):
            results.append(d)
    return sorted(results)


def parse_progress_raw(filepath: str) -> tuple[list[dict], dict]:
    """
    用原始文字方式 (Regex) 解析 narrative_progress.yaml。
    
    【為什麼不用單純的 yaml.safe_load?】
    因為在某些舊專案中，可能會有腳本或 LLM 錯誤地寫入了多個 `completed_chapters:` 區塊
    (Duplicate Keys)，標準的 yaml.safe_load 會直接拋出 ConstructorError 拒絕解析。
    為了能在不破壞舊資料的前提下救出所有章節，此函式使用 Regex 將檔案切割，
    分段解析 YAML 並將所有的 completed_chapters 陣列合併。

    Args:
        filepath: narrative_progress.yaml 的路徑

    Returns:
        tuple[list[dict], dict]:
            - all_chapters: 提取出的所有章節 dict 清單
            - other_data: 扣除 completed_chapters 外，剩下的其他設定資料 (如 current_beat等)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # 尋找所有出現 completed_chapters: 的行首
    pattern = re.compile(r'^completed_chapters:\s*(\[\])?\s*$', re.MULTILINE)
    matches = list(pattern.finditer(raw))

    if not matches:
        try:
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            data = {}
        return [], data

    all_chapters = []

    # 提早切出檔頭（位於第一個 completed_chapters 之前的內容，通常是 current_beat 等變數）
    first_cc_pos = matches[0].start()
    header_text = raw[:first_cc_pos]
    try:
        other_data = yaml.safe_load(header_text) or {}
    except yaml.YAMLError:
        other_data = {}

    # 針對每一個 completed_chapters 區塊進行切割與獨立解析
    for i, m in enumerate(matches):
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(raw)

        segment_text = raw[m.start():end_pos]
        # 修復空陣列寫法導致的解析問題
        segment_text = re.sub(
            r'^completed_chapters:\s*\[\]\s*\n',
            'completed_chapters:\n',
            segment_text,
            count=1,
        )

        try:
            segment_data = yaml.safe_load(segment_text)
        except yaml.YAMLError:
            continue

        if segment_data and "completed_chapters" in segment_data:
            chapters = segment_data["completed_chapters"]
            if isinstance(chapters, list):
                all_chapters.extend(chapters)

    return all_chapters, other_data


def get_chapter_id(ch: dict) -> int:
    """從 chapter dict 取得 chapter ID (相容舊標籤名稱)"""
    return ch.get("chapter_id") or ch.get("chapter") or 0


def normalize_chapter(ch: dict) -> dict:
    """
    將不同格式、歷史遺留版本的 chapter dict 標準化為 ChapterVector.REQUIRED_FIELDS schema。
    不同時期的 workflow 可能輸出了 `summary` 或是 `words`，這邊統一收束。
    """
    cid = get_chapter_id(ch)
    # 嘗試多個欄位名作為 ending_summary 來源
    summary = ch.get("ending_summary") or ch.get("summary") or ""
    return {
        "chapter_id": cid,
        "title": ch.get("title", f"第{cid}章"),
        "arc_id": ch.get("arc_id", 0),
        "subarc_id": str(ch.get("subarc_id") or ch.get("subarc") or ""),
        "word_count": ch.get("word_count") or ch.get("words") or 0,
        "ending_summary": summary,
        "completed_at": ch.get("completed_at", ""),
    }


def slim_project(project_folder: str, dry_run: bool = False) -> dict:
    """瘦身單一專案"""
    project_dir = os.path.join(PROJECTS_DIR, project_folder)
    progress_path = os.path.join(project_dir, "config", "narrative_progress.yaml")
    archive_path = os.path.join(project_dir, "memory", "archive", "narrative_progress_archive.yaml")

    if not os.path.isfile(progress_path):
        return {"project": project_folder, "status": "skip", "reason": "無 narrative_progress.yaml"}

    # 1. 解析所有 completed_chapters（處理重複 key）
    all_chapters, other_data = parse_progress_raw(progress_path)

    # 也讀取 YAML archive（若存在）
    if os.path.isfile(archive_path):
        with open(archive_path, "r", encoding="utf-8") as f:
            arch_data = yaml.safe_load(f) or {}
        archive_chapters = arch_data.get("completed_chapters", []) or []
        all_chapters.extend(archive_chapters)

    # 去重：以 chapter_id 為 key
    seen = {}
    for ch in all_chapters:
        cid = get_chapter_id(ch)
        if cid:
            seen[cid] = ch
    all_chapters = list(seen.values())
    all_chapters.sort(key=lambda c: get_chapter_id(c))

    # 標準化
    normalized = []
    skipped = 0
    for ch in all_chapters:
        n = normalize_chapter(ch)
        if not n["ending_summary"]:
            skipped += 1
            continue
        normalized.append(n)

    result = {
        "project": project_folder,
        "total_chapters": len(normalized),
        "skipped_no_summary": skipped,
        "dry_run": dry_run,
    }

    if not normalized:
        result["status"] = "skip"
        result["reason"] = "無可遷移的章節"
        return result

    if dry_run:
        result["status"] = "dry_run"
        return result

    # 2. 寫入 ChromaDB
    cv = ChapterVector(project_folder)
    cv.add_chapters_batch(normalized)
    result["db_count"] = cv.count()

    # 3. 重寫 narrative_progress.yaml（移除 completed_chapters）
    other_data.pop("completed_chapters", None)
    with open(progress_path, "w", encoding="utf-8") as f:
        yaml.dump(other_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
    result["new_size_kb"] = round(os.path.getsize(progress_path) / 1024, 1)

    # 4. 刪除 YAML archive（若存在）
    if os.path.isfile(archive_path):
        os.remove(archive_path)
        result["archive_deleted"] = True

    result["status"] = "done"
    return result


def main():
    parser = argparse.ArgumentParser(description="narrative_progress → ChromaDB 遷移工具")
    parser.add_argument("--proj", type=str, help="專案別名或資料夾名")
    parser.add_argument("--all", action="store_true", help="處理所有專案")
    parser.add_argument("--dry-run", action="store_true", help="僅預覽，不實際修改")
    args = parser.parse_args()

    if not args.proj and not args.all:
        parser.error("必須指定 --proj 或 --all")

    print("=" * 54)
    print("  📋 narrative_progress → ChromaDB 遷移")
    print("=" * 54)
    print()

    if args.all:
        projects = get_all_projects()
    else:
        folder = get_project_folder(args.proj) or args.proj
        projects = [folder]

    total_migrated = 0
    for proj in projects:
        print(f"📂 專案: {proj}")
        result = slim_project(proj, dry_run=args.dry_run)

        if result["status"] == "skip":
            print(f"   ⏩ 跳過: {result['reason']}")
        elif result["status"] == "dry_run":
            print(f"   📊 章節數: {result['total_chapters']}")
            if result["skipped_no_summary"]:
                print(f"   ⚠️  跳過 {result['skipped_no_summary']} 章（無 ending_summary）")
            print(f"   🔍 模式: 預覽 (dry-run)")
        elif result["status"] == "done":
            print(f"   📊 遷入 DB: {result['db_count']} 章")
            if result["skipped_no_summary"]:
                print(f"   ⚠️  跳過 {result['skipped_no_summary']} 章（無 ending_summary）")
            print(f"   📏 progress 新大小: {result['new_size_kb']} KB")
            if result.get("archive_deleted"):
                print(f"   🗑️  已刪除 YAML archive")
            total_migrated += result["db_count"]
        print()

    print("=" * 54)
    if args.dry_run:
        print("  🔍 預覽完成（未修改任何檔案）")
    else:
        print(f"  ✅ 完成（共遷移 {total_migrated} 章到 ChromaDB）")
    print("=" * 54)


if __name__ == "__main__":
    main()
