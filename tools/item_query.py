#!/usr/bin/env python3
"""
item_query.py — 物品/交易/嗶嗶帳本查詢 CLI
讓 workflow 中的 LLM 可以透過 terminal 按需查詢物品資料，節省 context/token。

用法:
  # 列出所有道具摘要
  python tools/item_query.py --proj worker list
  python tools/item_query.py --proj worker list --category Evidence

  # 完整道具資料（支援逗號分隔多道具）
  python tools/item_query.py --proj worker get SHELL_001
  python tools/item_query.py --proj worker get SHELL_001,CONS_001

  # 搜尋道具
  python tools/item_query.py --proj worker search 飛劍

  # 查某角色持有的道具
  python tools/item_query.py --proj worker holder CHAR_001

  # 按類別過濾
  python tools/item_query.py --proj worker by-category Evidence

  # 更新道具欄位
  python tools/item_query.py --proj worker update CONS_001 --quantity 0 --status "已用完"

  # 新增道具
  python tools/item_query.py --proj worker add --json '{"id":"NEW_001","name":"...", ...}'

  # 轉移道具持有者
  python tools/item_query.py --proj worker transfer EVID_002 --holder CHAR_003 --note "移交公會"

  # 當前餘額
  python tools/item_query.py --proj worker balance

  # 最近 N 筆交易
  python tools/item_query.py --proj worker tx-recent --n 5

  # 新增交易
  python tools/item_query.py --proj worker tx-add 57 --desc "委託報酬10銀" --balance "85銀"

  # 章節範圍交易
  python tools/item_query.py --proj worker tx-range 50 56

  # 嗶嗶未結清帳單
  python tools/item_query.py --proj worker bibi-pending

  # 嗶嗶全部帳本
  python tools/item_query.py --proj worker bibi-all

  # 新增嗶嗶帳本
  python tools/item_query.py --proj worker bibi-add 57 --desc "全程掃描服務費" --status "待結清"

  # 結清嗶嗶帳本
  python tools/item_query.py --proj worker bibi-settle 3 --status "Ch.57已結清"

  # 統計
  python tools/item_query.py --proj worker stats
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from tools.item_db import ItemDB
from tools.commons.json_arg import resolve_json_arg


_PRETTY = False

def fmt_json(obj) -> str:
    if _PRETTY:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def cmd_list(db: ItemDB, args):
    category = getattr(args, "category", None)
    items = db.list_items(category=category)
    if not items:
        print("(empty)")
        return
    for it in items:
        holder = f" [{it['holder']}]" if it["holder"] else ""
        qty = f" x{it['quantity']}" if it["quantity"] != 1 else ""
        print(f"  {it['id']:12s} {it['category']:16s} {it['name']}{holder}{qty}")


def cmd_get(db: ItemDB, args):
    ids = args.item_id.split(",")
    for item_id in ids:
        item_id = item_id.strip()
        it = db.get_item(item_id)
        if not it:
            print(f"not found: {item_id}")
            continue
        if len(ids) > 1:
            print(f"--- {item_id} ---")
        print(fmt_json(it))
        if len(ids) > 1:
            print()


def cmd_search(db: ItemDB, args):
    results = db.search_items(args.keyword)
    if not results:
        print("(no match)")
        return
    for it in results:
        print(f"  {it['id']:12s} {it['category']:16s} {it['name']}  [{it['holder']}]")


def cmd_holder(db: ItemDB, args):
    items = db.get_items_by_holder(args.holder_id)
    if not items:
        print("(no items)")
        return
    for it in items:
        qty = f" x{it['quantity']}" if it["quantity"] != 1 else ""
        print(f"  {it['id']:12s} {it['category']:16s} {it['name']}{qty}")


def cmd_by_category(db: ItemDB, args):
    items = db.list_items(category=args.category)
    if not items:
        print("(empty)")
        return
    for it in items:
        holder = f" [{it['holder']}]" if it["holder"] else ""
        print(f"  {it['id']:12s} {it['name']}{holder}")


def cmd_update(db: ItemDB, args):
    kwargs = {}
    if args.quantity is not None:
        kwargs["quantity"] = args.quantity
    if args.status is not None:
        kwargs["current_status"] = args.status
    if args.holder is not None:
        kwargs["holder"] = args.holder
    if not kwargs:
        print("nothing to update")
        return
    db.update_item(args.item_id, **kwargs)
    print(f"OK: {args.item_id} updated ({', '.join(kwargs.keys())})")


def cmd_add(db: ItemDB, args):
    data = json.loads(resolve_json_arg(args.json))
    item_id = data.pop("id")
    name = data.pop("name")
    category = data.pop("category", "Tool")
    # Extract known columns
    sub_type = data.pop("sub_type", "")
    description = data.pop("description", "")
    holder = data.pop("holder", "")
    obtained_chapter = data.pop("obtained_chapter", None)
    current_status = data.pop("current_status", "")
    quantity = data.pop("quantity", 1)
    # Remaining fields go into properties
    properties = data
    db.upsert_item(item_id, name, category, sub_type, description,
                   properties, holder, obtained_chapter, current_status, quantity)
    print(f"OK: {item_id} ({name}) added")


def cmd_transfer(db: ItemDB, args):
    kwargs = {"holder": args.holder}
    if args.note:
        kwargs["current_status"] = args.note
    db.update_item(args.item_id, **kwargs)
    print(f"OK: {args.item_id} transferred to {args.holder}")


def cmd_balance(db: ItemDB, args):
    print(db.get_balance())


def cmd_tx_recent(db: ItemDB, args):
    n = getattr(args, "n", 5) or 5
    txs = db.get_recent_transactions(n)
    if not txs:
        print("(no transactions)")
        return
    for tx in txs:
        bal = f" → {tx['balance_after']}" if tx["balance_after"] else ""
        print(f"  ch{tx['chapter']:3d}: {tx['description'][:100]}{bal}")


def cmd_tx_add(db: ItemDB, args):
    db.add_transaction(args.chapter, args.desc, args.balance or "")
    print(f"OK: transaction added (ch{args.chapter})")


def cmd_tx_range(db: ItemDB, args):
    txs = db.get_transactions_by_range(args.ch_from, args.ch_to)
    if not txs:
        print("(no transactions)")
        return
    for tx in txs:
        bal = f" → {tx['balance_after']}" if tx["balance_after"] else ""
        print(f"  ch{tx['chapter']:3d}: {tx['description'][:100]}{bal}")


def cmd_bibi_pending(db: ItemDB, args):
    entries = db.get_bibi_pending()
    if not entries:
        print("(no pending entries)")
        return
    for e in entries:
        print(f"  [{e['id']:3d}] ch{e['chapter']:3d}: {e['description'][:100]}")
        print(f"        status: {e['status']}")


def cmd_bibi_all(db: ItemDB, args):
    entries = db.get_bibi_all()
    if not entries:
        print("(empty)")
        return
    for e in entries:
        print(f"  [{e['id']:3d}] ch{e['chapter']:3d}: {e['description'][:80]}  [{e['status']}]")


def cmd_bibi_add(db: ItemDB, args):
    status = getattr(args, "status", "待結清") or "待結清"
    db.add_bibi_entry(args.chapter, args.desc, status)
    print(f"OK: bibi entry added (ch{args.chapter})")


def cmd_bibi_settle(db: ItemDB, args):
    db.settle_bibi(args.entry_id, args.status)
    print(f"OK: bibi entry #{args.entry_id} → {args.status}")


def cmd_stats(db: ItemDB, args):
    s = db.stats()
    print(f"  project: {s['project']}")
    print(f"  items: {s['total_items']}")
    for cat, cnt in sorted(s.get("categories", {}).items()):
        print(f"    - {cat}: {cnt}")
    print(f"  transactions: {s['total_transactions']}")
    print(f"  bibi: {s['bibi_total']} total, {s['bibi_pending']} pending")
    print(f"  db: {s['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="物品/交易查詢 CLI")
    parser.add_argument("--proj", required=True, type=str, help="專案名稱或代號")
    parser.add_argument("--pretty", action="store_true", help="JSON 美化輸出（預設 compact）")
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", help="列出道具摘要")
    p_list.add_argument("--category", type=str, help="過濾類別")

    # get
    p_get = subparsers.add_parser("get", help="取得完整道具資料（逗號分隔多道具）")
    p_get.add_argument("item_id", help="道具 ID（可逗號分隔）")

    # search
    p_search = subparsers.add_parser("search", help="搜尋道具")
    p_search.add_argument("keyword", help="搜尋關鍵字")

    # holder
    p_holder = subparsers.add_parser("holder", help="查某角色持有的道具")
    p_holder.add_argument("holder_id", help="角色 ID")

    # by-category
    p_cat = subparsers.add_parser("by-category", help="按類別列出道具")
    p_cat.add_argument("category", help="類別名")

    # update
    p_upd = subparsers.add_parser("update", help="更新道具欄位")
    p_upd.add_argument("item_id", help="道具 ID")
    p_upd.add_argument("--quantity", type=int, help="數量")
    p_upd.add_argument("--status", type=str, help="狀態")
    p_upd.add_argument("--holder", type=str, help="持有者")

    # add
    p_add = subparsers.add_parser("add", help="新增道具")
    p_add.add_argument("--json", required=True, help="JSON 字串（必含 id, name）")

    # transfer
    p_tr = subparsers.add_parser("transfer", help="轉移道具持有者")
    p_tr.add_argument("item_id", help="道具 ID")
    p_tr.add_argument("--holder", required=True, help="新持有者")
    p_tr.add_argument("--note", type=str, help="轉移備註")

    # balance
    subparsers.add_parser("balance", help="當前餘額")

    # tx-recent
    p_txr = subparsers.add_parser("tx-recent", help="最近 N 筆交易")
    p_txr.add_argument("--n", type=int, default=5, help="筆數")

    # tx-add
    p_txa = subparsers.add_parser("tx-add", help="新增交易")
    p_txa.add_argument("chapter", type=int, help="章節號")
    p_txa.add_argument("--desc", required=True, help="交易描述")
    p_txa.add_argument("--balance", type=str, help="交易後餘額")

    # tx-range
    p_txrng = subparsers.add_parser("tx-range", help="章節範圍交易")
    p_txrng.add_argument("ch_from", type=int, help="起始章")
    p_txrng.add_argument("ch_to", type=int, help="結束章")

    # bibi-pending
    subparsers.add_parser("bibi-pending", help="嗶嗶未結清帳單")

    # bibi-all
    subparsers.add_parser("bibi-all", help="嗶嗶全部帳本")

    # bibi-add
    p_ba = subparsers.add_parser("bibi-add", help="新增嗶嗶帳本")
    p_ba.add_argument("chapter", type=int, help="章節號")
    p_ba.add_argument("--desc", required=True, help="描述")
    p_ba.add_argument("--status", type=str, default="待結清", help="狀態")

    # bibi-settle
    p_bs = subparsers.add_parser("bibi-settle", help="結清嗶嗶帳本項目")
    p_bs.add_argument("entry_id", type=int, help="帳本項目 ID")
    p_bs.add_argument("--status", required=True, help="新狀態")

    # stats
    subparsers.add_parser("stats", help="統計")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    global _PRETTY
    _PRETTY = args.pretty

    db = ItemDB(args.proj)
    try:
        commands = {
            "list": cmd_list,
            "get": cmd_get,
            "search": cmd_search,
            "holder": cmd_holder,
            "by-category": cmd_by_category,
            "update": cmd_update,
            "add": cmd_add,
            "transfer": cmd_transfer,
            "balance": cmd_balance,
            "tx-recent": cmd_tx_recent,
            "tx-add": cmd_tx_add,
            "tx-range": cmd_tx_range,
            "bibi-pending": cmd_bibi_pending,
            "bibi-all": cmd_bibi_all,
            "bibi-add": cmd_bibi_add,
            "bibi-settle": cmd_bibi_settle,
            "stats": cmd_stats,
        }
        commands[args.command](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
