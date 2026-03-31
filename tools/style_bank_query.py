#!/usr/bin/env python3
"""
style_bank_query.py — 全域風格範本資料庫查詢 CLI

用法:
  # 按 tag 搜尋（AND）
  python tools/style_bank_query.py search --tags comedy,冷幽默 --n 3

  # 按 tag 搜尋（OR）
  python tools/style_bank_query.py search --tags comedy,冷幽默 --mode any --n 5

  # 按作家 + tag
  python tools/style_bank_query.py search --tags tension --author 烽火戲諸侯 --n 2

  # 關鍵字搜尋
  python tools/style_bank_query.py search --keyword "表裡不一" --n 5

  # 隨機取（避免重複錨定）
  python tools/style_bank_query.py random --tags emotion --n 2

  # 按 ID 取
  python tools/style_bank_query.py get 42

  # 列出所有 tag
  python tools/style_bank_query.py list-tags
  python tools/style_bank_query.py list-tags --category emotion

  # 列出所有作家
  python tools/style_bank_query.py list-authors

  # 按作家列出
  python tools/style_bank_query.py list --author 會說話的肘子

  # 按 tag 列出
  python tools/style_bank_query.py list --tag comedy

  # 統計
  python tools/style_bank_query.py stats

  # 覆蓋度報告
  python tools/style_bank_query.py coverage

  # 新增單段（inline JSON）
  python tools/style_bank_query.py add --json '{"author":"...","work":"...","text":"...","tags":["comedy"]}'

  # 新增單段（從檔案讀取，適合含引號的文本）
  python tools/style_bank_query.py add --file /tmp/passage.json

  # 批次新增
  python tools/style_bank_query.py add-batch --json '[{...},{...}]'
  python tools/style_bank_query.py add-batch --file /tmp/passages.json

  # 刪除
  python tools/style_bank_query.py remove 42

  # 加 tag
  python tools/style_bank_query.py add-tags 42 新tag1,新tag2

  # 移除 tag
  python tools/style_bank_query.py remove-tag 42 舊tag
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.style_bank_db import StyleBankDB


_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def fmt_passage_brief(p: dict) -> str:
    """格式化範本摘要（一行）"""
    note = p.get("style_note", "")[:40]
    return f"  #{p['id']:<4d} [{p['author']}] 《{p['work']}》{p.get('chapter', '')}  ({p.get('char_count', '?')}字)  {note}"


def fmt_passage_full(p: dict) -> str:
    """格式化完整範本"""
    tags = ", ".join(t["name"] for t in p.get("tags", []))
    lines = [
        f"#{p['id']} — {p['author']}《{p['work']}》{p.get('chapter', '')}",
        f"Tags: {tags}",
        f"Style: {p.get('style_note', '')}",
        "---",
        p["text"],
    ]
    return "\n".join(lines)


# ── 查詢指令 ──

def cmd_search(db: StyleBankDB, args):
    if args.keyword:
        results = db.search_by_keyword(args.keyword, limit=args.n)
    elif args.tags:
        tag_list = [t.strip() for t in args.tags.split(",")]
        mode = getattr(args, "mode", "all") or "all"
        author = getattr(args, "author", None)
        results = db.search_by_tags(tag_list, mode=mode, limit=args.n, author=author)
    else:
        print("Error: --tags or --keyword required", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("(no results)")
        return

    for p in results:
        print(fmt_passage_full(p))
        print()


def cmd_random(db: StyleBankDB, args):
    tag_list = [t.strip() for t in args.tags.split(",")]
    mode = getattr(args, "mode", "any") or "any"
    results = db.random_by_tags(tag_list, limit=args.n, mode=mode)
    if not results:
        print("(no results)")
        return
    for p in results:
        print(fmt_passage_full(p))
        print()


def cmd_get(db: StyleBankDB, args):
    p = db.get_passage(args.id)
    if not p:
        print(f"not found: {args.id}")
        return
    print(fmt_passage_full(p))


def cmd_list_tags(db: StyleBankDB, args):
    category = getattr(args, "category", None)
    tags = db.list_tags(category=category)
    if not tags:
        print("(no tags)")
        return
    if getattr(args, "names_only", False):
        print(", ".join(t["name"] for t in tags))
        return
    for t in tags:
        print(f"  {t['name']:20s} [{t['category']:12s}] {t['count']} passages")


def cmd_list_authors(db: StyleBankDB, args):
    authors = db.list_authors()
    if not authors:
        print("(no authors)")
        return
    for a in authors:
        print(f"  {a['author']:20s} {a['count']} passages")


def cmd_list(db: StyleBankDB, args):
    if args.author:
        results = db.list_by_author(args.author)
    elif args.tag:
        results = db.list_by_tag(args.tag)
    else:
        print("Error: --author or --tag required", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("(no results)")
        return
    for p in results:
        print(fmt_passage_brief(p))


def cmd_stats(db: StyleBankDB, args):
    stats = db.get_stats()
    print(fmt_json(stats))


def cmd_coverage(db: StyleBankDB, args):
    cov = db.get_coverage()
    print(f"Total tags: {cov['total_tags']}")
    print(f"Weak tags (<3 passages): {cov['weak_count']}")
    print()
    for cat, tags in cov["by_category"].items():
        print(f"[{cat}]")
        for t in tags:
            bar = "#" * min(t["count"], 20)
            print(f"  {t['name']:20s} {t['count']:3d} {bar}")
        print()
    if cov["weak_tags"]:
        print("Weak tags:")
        for t in cov["weak_tags"]:
            print(f"  {t['name']} ({t['category']}) = {t['count']}")


# ── 寫入指令 ──

def _load_json(args) -> str:
    """從 --json 或 --file 載入 JSON 字串"""
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    return args.json


def cmd_add(db: StyleBankDB, args):
    data = json.loads(_load_json(args))
    pid = db.add_passage(
        author=data["author"],
        work=data["work"],
        text=data["text"],
        chapter=data.get("chapter", ""),
        source_url=data.get("source_url", ""),
        style_note=data.get("style_note", ""),
        lang=data.get("lang", "zh-TW"),
        tags=data.get("tags"),
        tag_category=data.get("tag_category", "general"),
    )
    print(f"Added passage #{pid}")


def cmd_add_batch(db: StyleBankDB, args):
    entries = json.loads(_load_json(args))
    ids = db.add_batch(entries)
    print(f"Added {len(ids)} passages: #{', #'.join(str(i) for i in ids)}")


# ── 管理指令 ──

def cmd_remove(db: StyleBankDB, args):
    ok = db.remove_passage(args.id)
    if ok:
        print(f"Removed passage #{args.id}")
    else:
        print(f"not found: {args.id}")


def cmd_add_tags(db: StyleBankDB, args):
    tag_list = [t.strip() for t in args.tags.split(",")]
    db.add_tags_to_passage(args.id, tag_list)
    print(f"Added tags {tag_list} to passage #{args.id}")


def cmd_remove_tag(db: StyleBankDB, args):
    db.remove_tag_from_passage(args.id, args.tag)
    print(f"Removed tag '{args.tag}' from passage #{args.id}")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="style_bank_query — 風格範本資料庫 CLI")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Search passages by tags or keyword")
    p_search.add_argument("--tags", help="Comma-separated tag names")
    p_search.add_argument("--keyword", help="Keyword to search in text/style_note")
    p_search.add_argument("--mode", default="all", choices=["all", "any"], help="Tag match mode")
    p_search.add_argument("--author", help="Filter by author")
    p_search.add_argument("--n", type=int, default=5, help="Max results")

    # random
    p_random = sub.add_parser("random", help="Random passages by tags")
    p_random.add_argument("--tags", required=True, help="Comma-separated tag names")
    p_random.add_argument("--mode", default="any", choices=["all", "any"], help="Tag match mode")
    p_random.add_argument("--n", type=int, default=2, help="Number of results")

    # get
    p_get = sub.add_parser("get", help="Get passage by ID")
    p_get.add_argument("id", type=int, help="Passage ID")

    # list-tags
    p_lt = sub.add_parser("list-tags", help="List all tags with counts")
    p_lt.add_argument("--category", help="Filter by category")
    p_lt.add_argument("--names-only", action="store_true", help="Output tag names only (comma-separated)")

    # list-authors
    sub.add_parser("list-authors", help="List all authors with passage counts")

    # list
    p_list = sub.add_parser("list", help="List passages by author or tag")
    p_list.add_argument("--author", help="Filter by author")
    p_list.add_argument("--tag", help="Filter by tag")

    # stats
    sub.add_parser("stats", help="Show database statistics")

    # coverage
    sub.add_parser("coverage", help="Show tag coverage report")

    # add
    p_add = sub.add_parser("add", help="Add a passage")
    p_add_g = p_add.add_mutually_exclusive_group(required=True)
    p_add_g.add_argument("--json", help="JSON passage data (inline)")
    p_add_g.add_argument("--file", help="Path to JSON file containing passage data")

    # add-batch
    p_ab = sub.add_parser("add-batch", help="Add multiple passages")
    p_ab_g = p_ab.add_mutually_exclusive_group(required=True)
    p_ab_g.add_argument("--json", help="JSON array of passage data (inline)")
    p_ab_g.add_argument("--file", help="Path to JSON file containing passage array")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a passage")
    p_rm.add_argument("id", type=int, help="Passage ID")

    # add-tags
    p_at = sub.add_parser("add-tags", help="Add tags to a passage")
    p_at.add_argument("id", type=int, help="Passage ID")
    p_at.add_argument("tags", help="Comma-separated tag names")

    # remove-tag
    p_rt = sub.add_parser("remove-tag", help="Remove a tag from a passage")
    p_rt.add_argument("id", type=int, help="Passage ID")
    p_rt.add_argument("tag", help="Tag name to remove")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    global _PRETTY
    _PRETTY = args.pretty

    db = StyleBankDB()
    try:
        cmd_map = {
            "search": cmd_search,
            "random": cmd_random,
            "get": cmd_get,
            "list-tags": cmd_list_tags,
            "list-authors": cmd_list_authors,
            "list": cmd_list,
            "stats": cmd_stats,
            "coverage": cmd_coverage,
            "add": cmd_add,
            "add-batch": cmd_add_batch,
            "remove": cmd_remove,
            "add-tags": cmd_add_tags,
            "remove-tag": cmd_remove_tag,
        }
        cmd_map[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
