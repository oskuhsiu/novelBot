#!/usr/bin/env python3
"""
emotion_query.py — 情感記錄查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 按需查詢情感記錄，節省 context/token。

用法:
  # 最近 N 章摘要
  python tools/emotion_query.py --proj worker recent
  python tools/emotion_query.py --proj worker recent --n 10

  # 單章完整記錄
  python tools/emotion_query.py --proj worker get 57

  # 章節範圍 tension 曲線
  python tools/emotion_query.py --proj worker range 50 57

  # 新增/更新章節記錄
  python tools/emotion_query.py --proj worker add 58 --tension 60 --emotion "緊張/探索" --elements '{"comedy":10,"tension":40,"warmth":15,"mystery":35}' --note "..."

  # 統計分析
  python tools/emotion_query.py --proj worker analysis

  # 緩衝建議
  python tools/emotion_query.py --proj worker suggestions

  # 更新緩衝建議
  python tools/emotion_query.py --proj worker set-suggestions --json '["建議1","建議2"]'

  # 更新連續計數器
  python tools/emotion_query.py --proj worker set-consecutive --json '{"current_high_streak":0,...}'

  # 統計
  python tools/emotion_query.py --proj worker stats
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.emotion_db import EmotionDB


def cmd_recent(db: EmotionDB, args):
    n = getattr(args, "n", 5) or 5
    rows = db.get_recent(n)
    if not rows:
        print("(empty)")
        return
    for r in rows:
        print(f"  ch.{r['chapter_id']:3d}  tension={r['tension_score']:2d}  {r['primary_emotion']}")


def cmd_get(db: EmotionDB, args):
    ch = db.get_chapter(args.chapter_id)
    if not ch:
        print(f"not found: ch.{args.chapter_id}")
        return
    print(json.dumps(ch, ensure_ascii=False, indent=2))


def cmd_range(db: EmotionDB, args):
    rows = db.get_range(args.from_ch, args.to_ch)
    if not rows:
        print("(no data in range)")
        return
    for r in rows:
        bar = "#" * (r["tension_score"] // 5)
        print(f"  ch.{r['chapter_id']:3d}  {r['tension_score']:2d} {bar:20s} {r['primary_emotion']}")


def cmd_add(db: EmotionDB, args):
    elements = json.loads(args.elements) if args.elements else {}
    db.upsert_chapter(
        args.chapter_id,
        tension_score=args.tension or 0,
        primary_emotion=args.emotion or "",
        elements=elements,
        note=args.note or "",
    )
    print(f"OK: ch.{args.chapter_id} emotion record saved")


def cmd_analysis(db: EmotionDB, args):
    a = db.get_analysis()
    if a.get("total_chapters", 0) == 0:
        print("(no data)")
        return
    print(f"  total: {a['total_chapters']} chapters")
    print(f"  avg_tension: {a['average_tension']}")
    print(f"  max: {a['max_tension']}  min: {a['min_tension']}")
    print(f"  std_dev: {a['standard_deviation']}")
    if a.get("high_tension_chapters"):
        print(f"  high (>=60): {a['high_tension_chapters']}")
    if a.get("low_tension_chapters"):
        print(f"  low (<=30): {a['low_tension_chapters']}")


def cmd_suggestions(db: EmotionDB, args):
    sug = db.get_suggestions()
    if not sug:
        print("(no suggestions)")
        return
    for i, s in enumerate(sug, 1):
        print(f"  {i}. {s}")


def cmd_set_suggestions(db: EmotionDB, args):
    data = json.loads(args.json)
    db.set_suggestions(data)
    print(f"OK: {len(data)} suggestions saved")


def cmd_set_consecutive(db: EmotionDB, args):
    data = json.loads(args.json)
    db.set_consecutive(data)
    print("OK: consecutive tracking updated")


def cmd_stats(db: EmotionDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  chapters: {s['total_chapters']}")
    if s.get("chapter_range"):
        print(f"  range: {s['chapter_range']}")
    if s.get("db_path"):
        print(f"  db: {s['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="情感記錄查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    subparsers = parser.add_subparsers(dest="command")

    # recent
    p_recent = subparsers.add_parser("recent", help="最近 N 章摘要")
    p_recent.add_argument("--n", type=int, default=5, help="數量 (預設 5)")

    # get
    p_get = subparsers.add_parser("get", help="單章完整記錄")
    p_get.add_argument("chapter_id", type=int, help="章節號")

    # range
    p_range = subparsers.add_parser("range", help="章節範圍 tension 曲線")
    p_range.add_argument("from_ch", type=int, help="起始章")
    p_range.add_argument("to_ch", type=int, help="結束章")

    # add
    p_add = subparsers.add_parser("add", help="新增/更新章節記錄")
    p_add.add_argument("chapter_id", type=int, help="章節號")
    p_add.add_argument("--tension", type=int, help="張力分數")
    p_add.add_argument("--emotion", type=str, help="主要情感")
    p_add.add_argument("--elements", type=str, help="元素 JSON")
    p_add.add_argument("--note", type=str, help="備註")

    # analysis
    subparsers.add_parser("analysis", help="統計分析")

    # suggestions
    subparsers.add_parser("suggestions", help="緩衝建議")

    # set-suggestions
    p_ss = subparsers.add_parser("set-suggestions", help="更新緩衝建議")
    p_ss.add_argument("--json", required=True, help="JSON 陣列字串")

    # set-consecutive
    p_sc = subparsers.add_parser("set-consecutive", help="更新連續計數器")
    p_sc.add_argument("--json", required=True, help="JSON 物件字串")

    # stats
    subparsers.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    db = EmotionDB(args.proj)
    try:
        commands = {
            "recent": cmd_recent,
            "get": cmd_get,
            "range": cmd_range,
            "add": cmd_add,
            "analysis": cmd_analysis,
            "suggestions": cmd_suggestions,
            "set-suggestions": cmd_set_suggestions,
            "set-consecutive": cmd_set_consecutive,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
