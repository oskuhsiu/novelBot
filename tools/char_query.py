#!/usr/bin/env python3
"""
char_query.py — 角色資料庫查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 按需查詢角色資料，節省 context/token。

用法:
  # 列出所有角色摘要（低 token，開頭固定做一次）
  python tools/char_query.py --proj worker list
  python tools/char_query.py --proj worker list --role Supporting

  # 完整角色資料（按需載入）
  python tools/char_query.py --proj worker get CHAR_001

  # 只取 current_state
  python tools/char_query.py --proj worker get-state CHAR_001

  # 只取 base_profile
  python tools/char_query.py --proj worker get-base CHAR_001

  # 查詢關係
  python tools/char_query.py --proj worker relations
  python tools/char_query.py --proj worker relations CHAR_001

  # 搜尋角色
  python tools/char_query.py --proj worker search 索倫

  # 更新 current_state（整體替換）
  python tools/char_query.py --proj worker update-state CHAR_001 --json '{"location":"酒館",...}'

  # 更新單一欄位
  python tools/char_query.py --proj worker update-field CHAR_001 location "紅月酒館"

  # 更新關係
  python tools/char_query.py --proj worker update-rel CHAR_001 CHAR_MON_001 --surface "契約夥伴" --tension 45

  # 統計
  python tools/char_query.py --proj worker stats

  # 批次取得多角色（逗號分隔）
  python tools/char_query.py --proj worker get CHAR_001,CHAR_MON_001,CHAR_MON_002
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.char_db import CharacterDB
from tools.commons.json_arg import resolve_json_arg


_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def cmd_list(db: CharacterDB, args):
    role = getattr(args, "role", None)
    chars = db.list_characters(role=role, char_type="character")
    eggs = db.list_characters(char_type="easter_egg")

    if not chars and not eggs:
        print("(empty)")
        return

    if chars:
        for c in chars:
            identity = c["identity"] or ""
            print(f"  {c['id']:16s} [{c['role']:12s}] {c['name']}  {identity}")

    if eggs:
        print(f"\n  --- easter_egg ---")
        for c in eggs:
            print(f"  {c['id']:16s} [{c['role']:12s}] {c['name']}")


def _cmd_get_impl(args, getter):
    ids = args.char_id.split(",")
    for char_id in ids:
        char_id = char_id.strip()
        ch = getter(char_id)
        if not ch:
            print(f"not found: {char_id}")
            continue
        if len(ids) > 1:
            print(f"--- {char_id} ---")
        print(fmt_json(ch))
        if len(ids) > 1:
            print()


def cmd_get(db: CharacterDB, args):
    _cmd_get_impl(args, db.get_character)


def cmd_get_public(db: CharacterDB, args):
    _cmd_get_impl(args, db.get_character_public)


def cmd_get_state(db: CharacterDB, args):
    ids = args.char_id.split(",")
    for char_id in ids:
        char_id = char_id.strip()
        state = db.get_state(char_id)
        if not state:
            print(f"not found: {char_id}")
            continue
        if len(ids) > 1:
            print(f"--- {char_id} ---")
        print(fmt_json(state))


def cmd_get_base(db: CharacterDB, args):
    ids = args.char_id.split(",")
    for char_id in ids:
        char_id = char_id.strip()
        base = db.get_base(char_id)
        if not base:
            print(f"not found: {char_id}")
            continue
        if len(ids) > 1:
            print(f"--- {char_id} ---")
        print(fmt_json(base))


def _cmd_relations_impl(args, getter, show_hidden=True):
    char_id = getattr(args, "char_id", None)
    rels = getter(char_id)
    if not rels:
        print("(no relationships)")
        return
    for r in rels:
        print(f"  {r['source_id']} -> {r['target_id']}  tension={r['tension']}")
        print(f"    surface: {r['surface_relation']}")
        if show_hidden and r.get("hidden_dynamic"):
            print(f"    hidden:  {r['hidden_dynamic'][:100]}")
        print()


def cmd_relations(db: CharacterDB, args):
    _cmd_relations_impl(args, db.get_relationships)


def cmd_relations_public(db: CharacterDB, args):
    _cmd_relations_impl(args, db.get_relationships_public, show_hidden=False)


def cmd_search(db: CharacterDB, args):
    results = db.search(args.keyword)
    if not results:
        print("(no match)")
        return
    for c in results:
        print(f"  {c['id']:16s} [{c['role']:12s}] {c['name']}  {c['identity']}")


def cmd_update_state(db: CharacterDB, args):
    state = json.loads(resolve_json_arg(args.json))
    db.update_state(args.char_id, state)
    print(f"OK: {args.char_id} current_state updated")


def cmd_update_field(db: CharacterDB, args):
    # Try to parse value as JSON, fallback to string
    try:
        value = json.loads(args.value)
    except (json.JSONDecodeError, TypeError):
        value = args.value
    db.update_field(args.char_id, args.field, value)
    print(f"OK: {args.char_id}.{args.field} updated")


def cmd_update_rel(db: CharacterDB, args):
    db.upsert_relationship(
        args.source_id, args.target_id,
        surface_relation=args.surface or "",
        hidden_dynamic=args.hidden or "",
        common_interest=args.common or "",
        tension=args.tension or 0,
    )
    print(f"OK: {args.source_id} -> {args.target_id} updated")


def cmd_add(db: CharacterDB, args):
    data = json.loads(resolve_json_arg(args.json))
    char_id = data.pop("id")
    name = data.pop("name")
    role = data.pop("role", "Minor")
    char_type = data.pop("type", "character")
    identity = data.pop("identity", "")
    base_profile = data.pop("base_profile", {})
    current_state = data.pop("current_state", {})
    notes = data.pop("notes", "")
    db.upsert_character(char_id, name, role, char_type, identity,
                        base_profile, current_state, notes)
    print(f"OK: {char_id} ({name}) added")


def cmd_add_rel(db: CharacterDB, args):
    db.upsert_relationship(
        args.source_id, args.target_id,
        surface_relation=args.surface or "",
        hidden_dynamic=args.hidden or "",
        common_interest=args.common or "",
        tension=args.tension or 0,
    )
    print(f"OK: {args.source_id} -> {args.target_id} added")


def cmd_stats(db: CharacterDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  characters: {s['total_characters']}")
    for role, cnt in sorted(s.get("roles", {}).items()):
        print(f"    - {role}: {cnt}")
    print(f"  relationships: {s['total_relationships']}")
    print(f"  db: {s['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="角色資料庫查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", help="列出角色摘要")
    p_list.add_argument("--role", type=str, help="過濾角色類型")

    # get
    p_get = subparsers.add_parser("get", help="取得完整角色資料（支援逗號分隔多角色）")
    p_get.add_argument("char_id", help="角色 ID（可逗號分隔）")

    # get-public
    p_gp = subparsers.add_parser("get-public", help="取得角色資料（過濾 secret/hidden）")
    p_gp.add_argument("char_id", help="角色 ID（可逗號分隔）")

    # get-state
    p_gs = subparsers.add_parser("get-state", help="只取 current_state")
    p_gs.add_argument("char_id", help="角色 ID（可逗號分隔）")

    # get-base
    p_gb = subparsers.add_parser("get-base", help="只取 base_profile")
    p_gb.add_argument("char_id", help="角色 ID（可逗號分隔）")

    # relations
    p_rel = subparsers.add_parser("relations", help="查詢關係")
    p_rel.add_argument("char_id", nargs="?", help="角色 ID（不填列出全部）")

    # relations-public
    p_relp = subparsers.add_parser("relations-public", help="查詢關係（過濾 hidden_dynamic/common_interest）")
    p_relp.add_argument("char_id", nargs="?", help="角色 ID（不填列出全部）")

    # search
    p_search = subparsers.add_parser("search", help="搜尋角色")
    p_search.add_argument("keyword", help="搜尋關鍵字")

    # update-state
    p_us = subparsers.add_parser("update-state", help="更新 current_state")
    p_us.add_argument("char_id", help="角色 ID")
    p_us.add_argument("--json", required=True, help="JSON 字串")

    # update-field
    p_uf = subparsers.add_parser("update-field", help="更新單一欄位")
    p_uf.add_argument("char_id", help="角色 ID")
    p_uf.add_argument("field", help="欄位名")
    p_uf.add_argument("value", help="新值")

    # update-rel
    p_ur = subparsers.add_parser("update-rel", help="更新關係")
    p_ur.add_argument("source_id", help="來源角色 ID")
    p_ur.add_argument("target_id", help="目標角色 ID")
    p_ur.add_argument("--surface", type=str, help="表面關係")
    p_ur.add_argument("--hidden", type=str, help="潛在關係")
    p_ur.add_argument("--common", type=str, help="共同利益")
    p_ur.add_argument("--tension", type=int, help="緊張度 0-100")

    # add
    p_add = subparsers.add_parser("add", help="新增角色")
    p_add.add_argument("--json", required=True, help="JSON 字串（必含 id, name）")

    # add-rel
    p_ar = subparsers.add_parser("add-rel", help="新增關係")
    p_ar.add_argument("source_id", help="來源角色 ID")
    p_ar.add_argument("target_id", help="目標角色 ID")
    p_ar.add_argument("--surface", type=str, help="表面關係")
    p_ar.add_argument("--hidden", type=str, help="潛在關係")
    p_ar.add_argument("--common", type=str, help="共同利益")
    p_ar.add_argument("--tension", type=int, help="緊張度 0-100")

    # stats
    subparsers.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    global _PRETTY
    _PRETTY = args.pretty

    db = CharacterDB(args.proj)
    try:
        commands = {
            "list": cmd_list,
            "get": cmd_get,
            "get-public": cmd_get_public,
            "get-state": cmd_get_state,
            "get-base": cmd_get_base,
            "relations": cmd_relations,
            "relations-public": cmd_relations_public,
            "search": cmd_search,
            "update-state": cmd_update_state,
            "update-field": cmd_update_field,
            "update-rel": cmd_update_rel,
            "add": cmd_add,
            "add-rel": cmd_add_rel,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
