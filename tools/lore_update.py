#!/usr/bin/env python3
"""
lore_update.py — ChromaDB 更新與寫入工具
為 LLM 系統提供 Command Line 介面，以寫入或更新 Chapter 摘要與 Lore 事件，避免 LLM 直接寫 Python 腳本。

使用方式:
  # 新增或更新章節
  python tools/lore_update.py chapter --proj bnf --id 82 --title "滿載而歸" --arc 6 --subarc 6-3 --words 4692 --summary "章節摘要" --date "2026-03-03"

  # 新增或更新事件
  python tools/lore_update.py event --proj bnf --id "global_002_ch82" --cat "global_memory" --ch 82 --name "事件名稱" --status "active" --doc "事件詳細內容描述"

  # 刪除指定章節的所有事件
  python tools/lore_update.py delete --proj bnf --ch 82
  
  # 刪除指定 ID 的單一事件
  python tools/lore_update.py delete --proj bnf --id "global_002_ch82"
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.join(ROOT_DIR, "projects")
sys.path.insert(0, ROOT_DIR)

from tools.lore_vector import ChapterVector, LoreVector, get_project_folder

def cmd_chapter(args, folder):
    if not all([args.title, args.arc is not None, args.subarc, args.words is not None, args.summary]):
        print("錯誤：新增章節缺少必填參數 (--title, --arc, --subarc, --words, --summary)")
        sys.exit(1)
        
    cv = ChapterVector(folder)
    cv.add_chapter(
        chapter_id=args.id,
        title=args.title,
        arc_id=args.arc,
        subarc_id=args.subarc,
        word_count=args.words,
        ending_summary=args.summary,
        completed_at=args.date or ""
    )
    print(f"✅ 章節 {args.id} ({args.title}) 已成功寫入/更新至 ChromaDB。")

def cmd_event(args, folder):
    if not all([args.cat, args.name, args.status, args.doc]):
        print("錯誤：新增事件缺少必填參數 (--cat, --name, --status, --doc)")
        sys.exit(1)

    lv = LoreVector(folder)
    metadata = {
        "category": args.cat,
        "event_name": args.name,
        "status": args.status,
    }
    if args.ch is not None:
        metadata["chapter_ref"] = args.ch
    if args.char:
        metadata["character_id"] = args.char

    lv.add_event(
        event_id=args.id,
        document=args.doc,
        metadata=metadata
    )
    print(f"✅ 事件 {args.id} ({args.name}) 已成功寫入/更新至 ChromaDB。")

def cmd_delete(args, folder):
    if args.ch is None and args.id is None:
        print("錯誤：刪除指令缺少必填參數 (--ch 或 --id)")
        sys.exit(1)

    lv = LoreVector(folder)
    if args.id:
        lv.delete_event(args.id)
        print(f"✅ 已成功從 ChromaDB 刪除 event_id={args.id} 的事件。")
    if args.ch:
        lv.delete_by_filter({"chapter_ref": args.ch})
        print(f"✅ 已成功從 ChromaDB 刪除 chapter_ref={args.ch} 的所有事件。")

def main():
    parser = argparse.ArgumentParser(description="ChromaDB 更新與寫入工具")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    subparsers = parser.add_subparsers(dest="command", help="欲執行的操作指令")

    # 子指令：chapter
    parser_chapter = subparsers.add_parser("chapter", help="新增或更新章節 (ChapterVector)")
    parser_chapter.add_argument("--id", required=True, type=int, help="章節編號 (chapter_id)")
    parser_chapter.add_argument("--title", type=str, help="章節標題")
    parser_chapter.add_argument("--arc", type=int, help="所屬 Arc 編號")
    parser_chapter.add_argument("--subarc", type=str, help="所屬 SubArc 代號")
    parser_chapter.add_argument("--words", type=int, help="字數")
    parser_chapter.add_argument("--summary", type=str, help="章節結尾摘要")
    parser_chapter.add_argument("--date", type=str, help="完成日期 (選填)")

    # 子指令：event
    parser_event = subparsers.add_parser("event", help="新增或更新事件 (LoreVector)")
    parser_event.add_argument("--id", required=True, type=str, help="事件唯一 ID (event_id)")
    parser_event.add_argument("--cat", type=str, help="分類 (category)")
    parser_event.add_argument("--ch", type=int, help="相關章節編號 (chapter_ref，選填)")
    parser_event.add_argument("--name", type=str, help="事件名稱 (event_name)")
    parser_event.add_argument("--status", type=str, default="active", help="狀態 (status，預設 active)")
    parser_event.add_argument("--char", type=str, help="相關角色 ID (character_id，選填)")
    parser_event.add_argument("--doc", type=str, help="事件內容文件 (document)")

    # 子指令：delete
    parser_delete = subparsers.add_parser("delete", help="刪除特定章節或ID的事件 (LoreVector)")
    parser_delete.add_argument("--ch", type=int, help="要刪除其相關事件的章節編號 (chapter_ref)")
    parser_delete.add_argument("--id", type=str, help="要刪除的事件唯一 ID (event_id)")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    folder = get_project_folder(args.proj)
    if not folder:
        print(f"❌ 找不到專案名稱或代號: {args.proj}")
        sys.exit(1)

    if args.command == "chapter":
        cmd_chapter(args, folder)
    elif args.command == "event":
        cmd_event(args, folder)
    elif args.command == "delete":
        cmd_delete(args, folder)

if __name__ == "__main__":
    main()
