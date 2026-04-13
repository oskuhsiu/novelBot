#!/usr/bin/env python3
"""
atlas_query.py — 世界地圖查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 按需查詢地圖資料，節省 context/token。

用法:
  # 列出所有區域摘要
  python tools/atlas_query.py --proj worker list
  python tools/atlas_query.py --proj worker list --type region
  python tools/atlas_query.py --proj worker list --parent REG_001

  # 完整區域資料（含 locations）
  python tools/atlas_query.py --proj worker get REG_001
  python tools/atlas_query.py --proj worker get REG_001,ZONE_001

  # 搜尋
  python tools/atlas_query.py --proj worker search 酒館

  # 新增區域
  python tools/atlas_query.py --proj worker add --json '{"id":"REG_001","name":"...","region_type":"region",...}'

  # 更新屬性
  python tools/atlas_query.py --proj worker update-field REG_001 climate "寒冷"

  # 統計
  python tools/atlas_query.py --proj worker stats
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.atlas_db import AtlasDB
from tools.commons.json_arg import resolve_json_arg


_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def cmd_list(db: AtlasDB, args):
    region_type = getattr(args, "type", None)
    parent_id = getattr(args, "parent", None)
    regions = db.list_regions(region_type=region_type, parent_id=parent_id)
    if not regions:
        print("(empty)")
        return
    for r in regions:
        parent = f" parent={r['parent_id']}" if r["parent_id"] else ""
        print(f"  {r['id']:12s} [{r['region_type']:10s}]{parent}  {r['name']}  {r['summary']}")


def cmd_get(db: AtlasDB, args):
    ids = args.region_id.split(",")
    for rid in ids:
        rid = rid.strip()
        reg = db.get_region(rid)
        if not reg:
            print(f"not found: {rid}")
            continue
        if len(ids) > 1:
            print(f"--- {rid} ---")
        print(fmt_json(reg))
        if len(ids) > 1:
            print()


def cmd_search(db: AtlasDB, args):
    results = db.search(args.keyword)
    if not results:
        print("(no match)")
        return
    for r in results:
        parent = f" parent={r['parent_id']}" if r["parent_id"] else ""
        print(f"  {r['id']:12s} [{r['region_type']:10s}]{parent}  {r['name']}  {r['summary']}")


def cmd_add(db: AtlasDB, args):
    data = json.loads(resolve_json_arg(args.json))
    region_id = data.pop("id")
    name = data.pop("name")
    region_type = data.pop("region_type", "region")
    parent_id = data.pop("parent_id", "")
    summary = data.pop("summary", "")
    # Remaining fields go into properties
    properties = data
    db.upsert_region(region_id, name, region_type, parent_id, summary, properties)
    print(f"OK: {region_id} ({name}) added")


def cmd_update_field(db: AtlasDB, args):
    try:
        value = json.loads(args.value)
    except (json.JSONDecodeError, TypeError):
        value = args.value
    db.update_field(args.region_id, args.field, value)
    print(f"OK: {args.region_id}.{args.field} updated")


def cmd_stats(db: AtlasDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  total: {s['total_entries']}")
    for t, cnt in sorted(s.get("types", {}).items()):
        print(f"    - {t}: {cnt}")
    print(f"  db: {s['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="世界地圖查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", help="列出區域摘要")
    p_list.add_argument("--type", type=str, help="過濾類型 (region/zone/transit)")
    p_list.add_argument("--parent", type=str, help="過濾 parent_id")

    # get
    p_get = subparsers.add_parser("get", help="取得完整區域資料（逗號分隔多區域）")
    p_get.add_argument("region_id", help="區域 ID（可逗號分隔）")

    # search
    p_search = subparsers.add_parser("search", help="搜尋區域/地點")
    p_search.add_argument("keyword", help="搜尋關鍵字")

    # add
    p_add = subparsers.add_parser("add", help="新增區域")
    p_add.add_argument("--json", required=True, help="JSON 字串（必含 id, name）")

    # update-field
    p_uf = subparsers.add_parser("update-field", help="更新區域屬性")
    p_uf.add_argument("region_id", help="區域 ID")
    p_uf.add_argument("field", help="欄位名")
    p_uf.add_argument("value", help="新值（支援 JSON）")

    # stats
    subparsers.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    global _PRETTY
    _PRETTY = args.pretty

    db = AtlasDB(args.proj)
    try:
        commands = {
            "list": cmd_list,
            "get": cmd_get,
            "search": cmd_search,
            "add": cmd_add,
            "update-field": cmd_update_field,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
