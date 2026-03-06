#!/usr/bin/env python3
"""
lore_query.py — ChromaDB 查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 查詢 lore_bank 和 chapters

用法:
  # 語意搜尋 lore
  python tools/lore_query.py --proj bnf lore "主角的念力進化"
  python tools/lore_query.py --proj bnf lore "伏筆" --n 10
  python tools/lore_query.py --proj bnf lore "角色關係" --category character_memory

  # 查詢章節
  python tools/lore_query.py --proj bnf chapter 81
  python tools/lore_query.py --proj bnf chapters --recent 5
  python tools/lore_query.py --proj bnf chapters "突襲敵營" --n 3

  # 按章節查 lore
  python tools/lore_query.py --proj bnf lore-by-chapter 81

  # 統計
  python tools/lore_query.py --proj bnf stats
"""

import argparse
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.lore_vector import LoreVector, ChapterVector, get_project_folder


def resolve_project(proj_alias: str) -> str:
    folder = get_project_folder(proj_alias)
    if not folder:
        print(f"❌ 找不到專案: {proj_alias}")
        sys.exit(1)
    return folder


def cmd_lore_search(args):
    """
    語意搜尋 lore_bank 的 CLI 指令處理。
    當 LLM 在 nvDraft 或 nvReview 需要回憶某個設定或事件時會呼叫此指令。
    例如：LLM 讀到主角要使用某個法寶，但不確定法寶設定，
    就會執行：python lore_query.py --proj bnf lore "某法寶的設定"
    """
    proj = resolve_project(args.proj)
    lv = LoreVector(proj)

    if lv.count() == 0:
        print("⚠️  lore_bank 為空（尚未遷移？）")
        return

    where = {}
    if args.category:
        where["category"] = args.category

    results = lv.query(args.query, n=args.n, where=where if where else None)

    print(f"🔍 搜尋 lore: \"{args.query}\" (共 {len(results)} 筆)")
    print()
    for r in results:
        meta = r["metadata"]
        cat = meta.get("category", "?")
        ch = meta.get("chapter_ref", "?")
        dist = f"{r['distance']:.3f}" if r.get("distance") is not None else "?"
        # 輸出格式極度精簡，這很重要，因為這些輸出會直接進入 LLM 的 Context Window
        print(f"  [{cat}] ch.{ch} (dist={dist})")
        print(f"  {r['document']}")
        print()


def cmd_chapter_get(args):
    """
    精確取得某一章的 CLI 指令處理。
    主要用於 nvDraft/nvExpand 在 Sliding Window 中需要精確抓取「上一章」
    或「上一個 SubArc 最後一章」的 summary 提供連貫性上下文。
    """
    proj = resolve_project(args.proj)
    cv = ChapterVector(proj)

    ch = cv.get_chapter(args.chapter_id)
    if not ch:
        print(f"❌ 找不到第 {args.chapter_id} 章")
        return

    print(f"📖 第 {ch['chapter_id']} 章: {ch['title']}")
    print(f"   Arc: {ch['arc_id']} | SubArc: {ch['subarc_id']} | 字數: {ch['word_count']}")
    print(f"   完成: {ch.get('completed_at', '?')}")
    print()
    print(f"ending_summary:")
    print(ch["ending_summary"])


def cmd_chapters_recent(args):
    """
    取得最近 N 章 summary 的 CLI 指令處理。
    在 nvDraft 的 Step 1，LLM 會透過這個指令快速建立「前情提要」。
    """
    proj = resolve_project(args.proj)
    cv = ChapterVector(proj)

    chapters = cv.get_recent_chapters(n=args.recent)
    if not chapters:
        print("⚠️  chapters 為空")
        return

    print(f"📖 最近 {len(chapters)} 章:")
    print()
    for ch in chapters:
        print(f"  第 {ch['chapter_id']} 章: {ch['title']} ({ch['word_count']}字)")
        summary = ch["ending_summary"]
        # 如果是列出多章前情提要，為節省 token 稍微截斷超長 summary
        if len(summary) > 120:
            summary = summary[:120] + "..."
        print(f"    {summary}")
        print()


def cmd_chapters_search(args):
    """
    語意搜尋章節的 CLI 指令處理。
    用於當我們忘記某個事件發生在哪一章時，用自然語言搜尋。
    """
    proj = resolve_project(args.proj)
    cv = ChapterVector(proj)

    if cv.count() == 0:
        print("⚠️  chapters 為空")
        return

    results = cv.query_chapters(args.query, n=args.n)
    print(f"🔍 搜尋章節: \"{args.query}\" (共 {len(results)} 筆)")
    print()
    for r in results:
        dist = f"{r['distance']:.3f}" if r.get("distance") is not None else "?"
        print(f"  第 {r['chapter_id']} 章: {r['title']} (dist={dist})")
        summary = r["ending_summary"]
        if len(summary) > 150:
            summary = summary[:150] + "..."
        print(f"    {summary}")
        print()


def cmd_lore_by_chapter(args):
    """
    按章節列出 lore 記錄的 CLI 指令處理。
    主要用於開發/除錯，例如「我想看看第 10 章到底產生了哪些設定和伏筆」。
    """
    proj = resolve_project(args.proj)
    lv = LoreVector(proj)

    results = lv.list_all(where={"chapter_ref": args.chapter_id}, limit=100)
    if not results:
        print(f"⚠️  第 {args.chapter_id} 章無 lore 記錄")
        return

    print(f"📋 第 {args.chapter_id} 章的 lore 記錄 (共 {len(results)} 筆):")
    print()
    for r in results:
        cat = r["metadata"].get("category", "?")
        print(f"  [{cat}] {r['document']}")
        print()


def cmd_stats(args):
    """
    輸出統計的 CLI 指令處理。
    用於檢查資料庫完整性，在 nvMaint 跑完後也可能呼叫以確認狀態。
    """
    proj = resolve_project(args.proj)
    lv = LoreVector(proj)
    cv = ChapterVector(proj)

    print(f"📊 專案: {proj}")
    print()

    # lore stats
    lore_stats = lv.stats()
    print(f"  lore_bank: {lore_stats['total_records']} 筆記錄")
    if lore_stats.get("categories"):
        for cat, count in sorted(lore_stats["categories"].items()):
            print(f"    - {cat}: {count}")
    if lore_stats.get("chapter_range"):
        print(f"    章節範圍: {lore_stats['chapter_range']}")

    print()

    # chapter stats
    ch_stats = cv.stats()
    print(f"  chapters: {ch_stats.get('total_chapters', 0)} 章")
    if ch_stats.get("chapter_range"):
        print(f"    章節範圍: {ch_stats['chapter_range']}")
    if ch_stats.get("total_words"):
        print(f"    總字數: {ch_stats['total_words']}")
    if ch_stats.get("arcs"):
        for arc, count in sorted(ch_stats["arcs"].items()):
            print(f"    - Arc {arc}: {count} 章")

    print()
    print(f"  DB 路徑: {lv.db_path}")


def main():
    parser = argparse.ArgumentParser(description="ChromaDB 查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    subparsers = parser.add_subparsers(dest="command")

    # lore <query>
    p_lore = subparsers.add_parser("lore", help="語意搜尋 lore_bank")
    p_lore.add_argument("query", help="查詢文字")
    p_lore.add_argument("--n", type=int, default=5, help="返回數量 (預設 5)")
    p_lore.add_argument("--category", type=str, help="過濾 lore category")

    # chapter <id>
    p_ch = subparsers.add_parser("chapter", help="取得指定章節")
    p_ch.add_argument("chapter_id", type=int, help="章節號")

    # chapters [query]
    p_chs = subparsers.add_parser("chapters", help="搜尋/列出章節")
    p_chs.add_argument("query", nargs="?", help="搜尋文字（不填則列最近 N 章）")
    p_chs.add_argument("--n", type=int, default=5, help="返回數量 (預設 5)")
    p_chs.add_argument("--recent", type=int, help="最近 N 章")

    # lore-by-chapter <id>
    p_lbc = subparsers.add_parser("lore-by-chapter", help="按章節列出 lore")
    p_lbc.add_argument("chapter_id", type=int, help="章節號")

    # stats
    p_stats = subparsers.add_parser("stats", help="輸出統計")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "lore":
        cmd_lore_search(args)
    elif args.command == "chapter":
        cmd_chapter_get(args)
    elif args.command == "chapters":
        if args.query:
            cmd_chapters_search(args)
        else:
            if not args.recent:
                args.recent = args.n
            cmd_chapters_recent(args)
    elif args.command == "lore-by-chapter":
        cmd_lore_by_chapter(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
