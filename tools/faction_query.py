#!/usr/bin/env python3
"""
faction_query.py — 勢力資料庫查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 按需查詢勢力資料，節省 context/token。

用法:
  # 列出所有勢力摘要
  python tools/faction_query.py --proj worker list

  # 完整勢力資料
  python tools/faction_query.py --proj worker get FAC_001
  python tools/faction_query.py --proj worker get FAC_001,FAC_002

  # 查詢關係
  python tools/faction_query.py --proj worker relations
  python tools/faction_query.py --proj worker relations FAC_001

  # 查詢事件
  python tools/faction_query.py --proj worker events

  # 搜尋
  python tools/faction_query.py --proj worker search 天宮

  # 新增勢力
  python tools/faction_query.py --proj worker add --json '{"id":"FAC_001","name":"天宮財閥",...}'

  # 新增關係
  python tools/faction_query.py --proj worker add-rel FAC_001 FAC_002 --status "Hostile" --tension 80

  # 新增事件
  python tools/faction_query.py --proj worker add-event --json '{"event_id":"EVT_001","affected_factions":["FAC_001"],...}'

  # 更新 tension
  python tools/faction_query.py --proj worker update-tension FAC_001 FAC_002 75

  # 更新勢力屬性
  python tools/faction_query.py --proj worker update-field FAC_001 territory '["LOC_001","LOC_002"]'

  # 統計
  python tools/faction_query.py --proj worker stats
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.faction_db import FactionDB


_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def cmd_list(db: FactionDB, args):
    facs = db.list_factions()
    if not facs:
        print("(empty)")
        return
    for f in facs:
        print(f"  {f['id']:12s} [{f['tier']:2s}] [{f['type']:12s}] {f['name']}  {f['philosophy']}")


def _cmd_get_impl(args, getter):
    ids = args.faction_id.split(",")
    for fid in ids:
        fid = fid.strip()
        fac = getter(fid)
        if not fac:
            print(f"not found: {fid}")
            continue
        if len(ids) > 1:
            print(f"--- {fid} ---")
        print(fmt_json(fac))
        if len(ids) > 1:
            print()


def cmd_get(db: FactionDB, args):
    _cmd_get_impl(args, db.get_faction)


def cmd_get_public(db: FactionDB, args):
    _cmd_get_impl(args, db.get_faction_public)


def _cmd_relations_impl(args, getter):
    faction_id = getattr(args, "faction_id", None)
    rels = getter(faction_id)
    if not rels:
        print("(no relations)")
        return
    base_exclude = {"source_id", "target_id", "status", "tension"}
    for r in rels:
        print(f"  {r['source_id']} -> {r['target_id']}  status={r['status']}  tension={r['tension']}")
        props = {k: v for k, v in r.items() if k not in base_exclude}
        if props:
            for k, v in props.items():
                val = str(v)[:100] if isinstance(v, str) else str(v)
                print(f"    {k}: {val}")
        print()


def cmd_relations(db: FactionDB, args):
    _cmd_relations_impl(args, db.get_relations)


def cmd_relations_public(db: FactionDB, args):
    _cmd_relations_impl(args, db.get_relations_public)


def cmd_events(db: FactionDB, args):
    evts = db.get_events()
    if not evts:
        print("(no events)")
        return
    for e in evts:
        print(f"  {e['event_id']}  factions={e['affected_factions']}")
        print(f"    desc: {e['description'][:100]}")
        if e.get("impact"):
            print(f"    impact: {e['impact'][:100]}")
        print()


def cmd_search(db: FactionDB, args):
    results = db.search(args.keyword)
    if not results:
        print("(no match)")
        return
    for f in results:
        print(f"  {f['id']:12s} [{f['tier']:2s}] [{f['type']:12s}] {f['name']}  {f['philosophy']}")


def cmd_add(db: FactionDB, args):
    data = json.loads(args.json)
    faction_id = data.pop("id")
    name = data.pop("name")
    tier = data.pop("tier", "")
    faction_type = data.pop("type", "")
    philosophy = data.pop("philosophy", "")
    description = data.pop("description", "")
    # Remaining fields go into properties
    properties = data
    db.upsert_faction(faction_id, name, tier, faction_type, philosophy, description, properties)
    print(f"OK: {faction_id} ({name}) added")


def cmd_add_rel(db: FactionDB, args):
    props = {}
    if args.history:
        props["history"] = args.history
    if args.secret:
        props["secret_dealings"] = args.secret
    if args.trade is not None:
        props["trade_agreement"] = args.trade
    db.upsert_relation(
        args.source_id, args.target_id,
        status=args.status or "Neutral",
        tension=args.tension or 0,
        properties=props if props else None,
    )
    print(f"OK: {args.source_id} -> {args.target_id} added")


def cmd_add_event(db: FactionDB, args):
    data = json.loads(args.json)
    event_id = data.pop("event_id")
    affected = data.pop("affected_factions", [])
    description = data.pop("description", "")
    impact = data.pop("impact", "")
    properties = data
    db.upsert_event(event_id, affected, description, impact, properties)
    print(f"OK: {event_id} added")


def cmd_update_tension(db: FactionDB, args):
    db.update_tension(args.source_id, args.target_id, args.tension)
    print(f"OK: {args.source_id} -> {args.target_id} tension={args.tension}")


def cmd_update_field(db: FactionDB, args):
    try:
        value = json.loads(args.value)
    except (json.JSONDecodeError, TypeError):
        value = args.value
    db.update_field(args.faction_id, args.field, value)
    print(f"OK: {args.faction_id}.{args.field} updated")


def cmd_stats(db: FactionDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  factions: {s['total_factions']}")
    for tier, cnt in sorted(s.get("tiers", {}).items()):
        print(f"    - {tier}: {cnt}")
    print(f"  relations: {s['total_relations']}")
    print(f"  events: {s['total_events']}")
    print(f"  db: {s['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="勢力資料庫查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="列出勢力摘要")

    # get
    p_get = subparsers.add_parser("get", help="取得完整勢力資料（逗號分隔多勢力）")
    p_get.add_argument("faction_id", help="勢力 ID（可逗號分隔）")

    # get-public
    p_gp = subparsers.add_parser("get-public", help="取得勢力資料（過濾 secret_dealings）")
    p_gp.add_argument("faction_id", help="勢力 ID（可逗號分隔）")

    # relations
    p_rel = subparsers.add_parser("relations", help="查詢關係")
    p_rel.add_argument("faction_id", nargs="?", help="勢力 ID（不填列出全部）")

    # relations-public
    p_relp = subparsers.add_parser("relations-public", help="查詢關係（過濾 secret_dealings）")
    p_relp.add_argument("faction_id", nargs="?", help="勢力 ID（不填列出全部）")

    # events
    subparsers.add_parser("events", help="查詢勢力事件")

    # search
    p_search = subparsers.add_parser("search", help="搜尋勢力")
    p_search.add_argument("keyword", help="搜尋關鍵字")

    # add
    p_add = subparsers.add_parser("add", help="新增勢力")
    p_add.add_argument("--json", required=True, help="JSON 字串（必含 id, name）")

    # add-rel
    p_ar = subparsers.add_parser("add-rel", help="新增勢力關係")
    p_ar.add_argument("source_id", help="來源勢力 ID")
    p_ar.add_argument("target_id", help="目標勢力 ID")
    p_ar.add_argument("--status", type=str, help="關係狀態 (Allied/Hostile/Neutral/...)")
    p_ar.add_argument("--tension", type=int, help="緊張度 0-100")
    p_ar.add_argument("--history", type=str, help="歷史關係描述")
    p_ar.add_argument("--secret", type=str, help="秘密往來")
    p_ar.add_argument("--trade", type=bool, help="貿易協定", default=None)

    # add-event
    p_ae = subparsers.add_parser("add-event", help="新增勢力事件")
    p_ae.add_argument("--json", required=True, help="JSON 字串（必含 event_id）")

    # update-tension
    p_ut = subparsers.add_parser("update-tension", help="更新 tension")
    p_ut.add_argument("source_id", help="來源勢力 ID")
    p_ut.add_argument("target_id", help="目標勢力 ID")
    p_ut.add_argument("tension", type=int, help="新 tension 值")

    # update-field
    p_uf = subparsers.add_parser("update-field", help="更新勢力屬性")
    p_uf.add_argument("faction_id", help="勢力 ID")
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

    db = FactionDB(args.proj)
    try:
        commands = {
            "list": cmd_list,
            "get": cmd_get,
            "get-public": cmd_get_public,
            "relations": cmd_relations,
            "relations-public": cmd_relations_public,
            "events": cmd_events,
            "search": cmd_search,
            "add": cmd_add,
            "add-rel": cmd_add_rel,
            "add-event": cmd_add_event,
            "update-tension": cmd_update_tension,
            "update-field": cmd_update_field,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
