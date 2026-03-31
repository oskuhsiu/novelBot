#!/usr/bin/env python3
"""
review_query.py — Review 記錄查詢 CLI

用法:
  # 新增記錄（ch.58 用了 codex + gemini，full mode，來源 nvReview）
  python tools/review_query.py --proj worker add 58 --assists codex,gemini --mode full --source nvReview

  # 新增記錄（ch.59 沒用 assist）
  python tools/review_query.py --proj worker add 59 --assists none --mode full --source nvReview

  # 查某章所有記錄
  python tools/review_query.py --proj worker get 58

  # 查某章最新一筆
  python tools/review_query.py --proj worker latest 58

  # 列出所有記錄
  python tools/review_query.py --proj worker list

  # 統計
  python tools/review_query.py --proj worker stats
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.review_db import ReviewDB

_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def cmd_add(db: ReviewDB, args):
    assists_str = args.assists or "none"
    if assists_str == "none":
        assists = []
    else:
        assists = [a.strip() for a in assists_str.split(",") if a.strip()]
    db.add(
        chapter_id=args.chapter_id,
        assists=assists,
        mode=args.mode or "",
        source=args.source or "",
    )
    label = ",".join(assists) if assists else "none"
    print(f"OK: ch.{args.chapter_id} review recorded (assists={label})")


def cmd_get(db: ReviewDB, args):
    rows = db.get(args.chapter_id)
    if not rows:
        print(f"no records: ch.{args.chapter_id}")
        return
    for r in rows:
        assists = ",".join(r["assists"]) if r["assists"] else "none"
        print(f"  [{r['reviewed_at']}] ch.{r['chapter_id']} assists={assists} mode={r['mode']} source={r['source']}")


def cmd_latest(db: ReviewDB, args):
    r = db.get_latest(args.chapter_id)
    if not r:
        print(f"no records: ch.{args.chapter_id}")
        return
    print(fmt_json(r))


def cmd_list(db: ReviewDB, args):
    rows = db.list_all()
    if not rows:
        print("(empty)")
        return
    for r in rows:
        assists = ",".join(r["assists"]) if r["assists"] else "none"
        print(f"  ch.{r['chapter_id']:3d}  [{r['reviewed_at']}]  assists={assists}  mode={r['mode']}  src={r['source']}")


def cmd_stats(db: ReviewDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  total_records: {s['total_records']}")
    if s["total_records"] == 0:
        return
    print(f"  chapters_reviewed: {s['chapters_reviewed']}")
    print(f"  chapter_range: {s['chapter_range']}")
    print(f"  with_assist (latest): {s['with_assist']}")
    print(f"  without_assist (latest): {s['without_assist']}")


def main():
    parser = argparse.ArgumentParser(description="Review 記錄查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    subparsers = parser.add_subparsers(dest="command")

    # add
    p_add = subparsers.add_parser("add", help="新增 review 記錄")
    p_add.add_argument("chapter_id", type=int, help="章節號")
    p_add.add_argument("--assists", type=str, default="none", help="使用的 assist（逗號分隔，如 codex,gemini；none=未使用）")
    p_add.add_argument("--mode", type=str, help="light / full")
    p_add.add_argument("--source", type=str, help="nvReview / nvAudit")

    # get
    p_get = subparsers.add_parser("get", help="查某章所有 review 記錄")
    p_get.add_argument("chapter_id", type=int, help="章節號")

    # latest
    p_latest = subparsers.add_parser("latest", help="查某章最新一筆")
    p_latest.add_argument("chapter_id", type=int, help="章節號")

    # list
    subparsers.add_parser("list", help="列出所有記錄")

    # stats
    subparsers.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    global _PRETTY
    _PRETTY = args.pretty

    db = ReviewDB(args.proj)
    try:
        commands = {
            "add": cmd_add,
            "get": cmd_get,
            "latest": cmd_latest,
            "list": cmd_list,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
