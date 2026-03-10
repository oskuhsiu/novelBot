#!/usr/bin/env python3
"""
migrate_db.py — 統一資料遷移腳本
將 YAML 資料遷移至 ChromaDB / SQLite

支援的遷移目標:
  - lore:     lore_bank.yaml → ChromaDB (原 lore_migrate.py)
  - char:     character_db.yaml → SQLite (novel.db)
  - emotion:  emotion_log.yaml → SQLite (novel.db)
  - item:     item_compendium.yaml → SQLite (novel.db)
  - faction:  faction_registry.yaml → SQLite (novel.db)
  - atlas:    world_atlas.yaml → SQLite (novel.db)
  - all:      以上全部

使用方式:
    python tools/migrate_db.py --proj worker char
    python tools/migrate_db.py --proj worker emotion
    python tools/migrate_db.py --proj worker item
    python tools/migrate_db.py --proj worker lore
    python tools/migrate_db.py --proj worker all
    python tools/migrate_db.py --proj worker char --dry-run
    python tools/migrate_db.py --proj worker char --verify
    python tools/migrate_db.py --all-projects all
"""

import argparse
import json
import os
import sys

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.join(ROOT_DIR, "projects")

sys.path.insert(0, ROOT_DIR)
from tools.lore_vector import LoreVector, get_project_folder


# ════════════════════════════════════════════════════════════
#  Character DB 遷移
# ════════════════════════════════════════════════════════════

def parse_character_db(yaml_path: str) -> dict:
    """
    解析 character_db.yaml，回傳 {"characters": [...], "relationships": [...]}
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return {"characters": [], "relationships": []}

    characters = []

    # 正規角色
    for char in data.get("characters", []) or []:
        characters.append(_parse_one_character(char, char_type="character"))

    # 彩蛋角色
    for char in data.get("easter_egg_characters", []) or []:
        characters.append(_parse_one_character(char, char_type="easter_egg"))

    # 關係
    relationships = []
    for rel in data.get("relationships", []) or []:
        relationships.append({
            "source_id": rel.get("source_id", ""),
            "target_id": rel.get("target_id", ""),
            "surface_relation": rel.get("surface_relation", ""),
            "hidden_dynamic": rel.get("hidden_dynamic", ""),
            "common_interest": rel.get("common_interest", ""),
            "tension": rel.get("tension", 0),
        })

    return {"characters": characters, "relationships": relationships}


def _parse_one_character(char: dict, char_type: str) -> dict:
    base = char.get("base_profile", {}) or {}
    state = char.get("current_state", {}) or {}
    return {
        "id": char.get("id", ""),
        "name": char.get("name", ""),
        "role": char.get("role", "Minor"),
        "type": char_type,
        "identity": base.get("identity", ""),
        "base_profile": base,
        "current_state": state,
        "notes": char.get("notes", ""),
    }


def migrate_characters(project_folder: str, dry_run: bool = False, verify: bool = False):
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "config", "character_db.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: {yaml_path} not found")
        return

    print(f"\n  [char] {yaml_path}")
    parsed = parse_character_db(yaml_path)
    chars = parsed["characters"]
    rels = parsed["relationships"]
    print(f"    characters: {len(chars)}, relationships: {len(rels)}")

    if dry_run:
        print("    (dry-run)")
        for c in chars[:5]:
            print(f"      {c['id']:16s} [{c['role']:12s}] {c['name']}")
        if len(chars) > 5:
            print(f"      ... and {len(chars) - 5} more")
        return

    from tools.char_db import CharacterDB
    db = CharacterDB(project_folder)
    try:
        if verify:
            db_count = db.count()
            print(f"    YAML: {len(chars)}, DB: {db_count}")
            if db_count == len(chars):
                print("    OK: counts match")
            else:
                print(f"    MISMATCH: diff={db_count - len(chars)}")
            # spot check
            for c in chars[:3]:
                found = db.get_character(c["id"])
                status = "found" if found else "MISSING"
                print(f"      {c['id']}: {status}")
            return

        for c in chars:
            db.upsert_character(
                c["id"], c["name"], c["role"], c["type"],
                c["identity"], c["base_profile"], c["current_state"], c["notes"],
            )
        for r in rels:
            db.upsert_relationship(
                r["source_id"], r["target_id"],
                r["surface_relation"], r["hidden_dynamic"],
                r["common_interest"], r["tension"],
            )
        print(f"    OK: {db.count()} characters, {len(rels)} relationships -> {db.db_path}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  Emotion Log 遷移
# ════════════════════════════════════════════════════════════

def parse_emotion_log(yaml_path: str) -> dict:
    """
    解析 emotion_log.yaml，回傳
    {"chapters": [...], "analysis": {...}, "consecutive": {...}, "suggestions": [...]}
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return {"chapters": [], "analysis": {}, "consecutive": {}, "suggestions": []}

    chapters = []
    for ch in data.get("chapters", []) or []:
        chapter_id = ch.get("chapter") or ch.get("chapter_id")
        if chapter_id is None or chapter_id == 0:
            continue
        # elements 可能是 {comedy, tension, warmth, mystery} 或更複雜的格式
        elements = ch.get("elements", {}) or {}
        chapters.append({
            "chapter_id": int(chapter_id),
            "tension_score": ch.get("tension_score", 0),
            "primary_emotion": ch.get("primary_emotion", ""),
            "elements": elements,
            "note": ch.get("note", ""),
        })

    analysis = data.get("analysis", {}) or {}
    consecutive = data.get("consecutive_tracking", {}) or {}

    # suggestions 可以是 list[str] 或 list[dict]
    raw_sug = data.get("buffer_suggestions", []) or []
    suggestions = []
    for s in raw_sug:
        if isinstance(s, str):
            suggestions.append(s)
        elif isinstance(s, dict):
            desc = s.get("description", "")
            if desc:
                suggestions.append(desc)

    return {
        "chapters": chapters,
        "analysis": analysis,
        "consecutive": consecutive,
        "suggestions": suggestions,
    }


def migrate_emotions(project_folder: str, dry_run: bool = False, verify: bool = False):
    # 先試 memory/ 再試 config/
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "memory", "emotion_log.yaml")
    if not os.path.exists(yaml_path):
        yaml_path = os.path.join(PROJECT_ROOT, project_folder, "config", "emotion_log.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: emotion_log.yaml not found")
        return

    print(f"\n  [emotion] {yaml_path}")
    parsed = parse_emotion_log(yaml_path)
    chapters = parsed["chapters"]
    print(f"    chapters: {len(chapters)}, suggestions: {len(parsed['suggestions'])}")

    if dry_run:
        print("    (dry-run)")
        for ch in chapters[:5]:
            print(f"      ch.{ch['chapter_id']:3d}  tension={ch['tension_score']:2d}  {ch['primary_emotion']}")
        if len(chapters) > 5:
            print(f"      ... and {len(chapters) - 5} more")
        return

    from tools.emotion_db import EmotionDB
    db = EmotionDB(project_folder)
    try:
        if verify:
            db_count = db.count()
            print(f"    YAML: {len(chapters)}, DB: {db_count}")
            if db_count == len(chapters):
                print("    OK: counts match")
            else:
                print(f"    MISMATCH: diff={db_count - len(chapters)}")
            return

        for ch in chapters:
            db.upsert_chapter(
                ch["chapter_id"], ch["tension_score"],
                ch["primary_emotion"], ch["elements"], ch["note"],
            )
        if parsed["suggestions"]:
            db.set_suggestions(parsed["suggestions"])
        if parsed["consecutive"]:
            db.set_consecutive(parsed["consecutive"])
        print(f"    OK: {db.count()} chapters -> {db.db_path}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  Lore Bank 遷移 (原 lore_migrate.py 邏輯)
# ════════════════════════════════════════════════════════════

def parse_lore_bank(yaml_path: str) -> list[dict]:
    """解析 lore_bank.yaml 為 ChromaDB event 格式（與原 lore_migrate.py 相同）"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    events = []
    counters = {}

    def make_id(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}_{counters[prefix]:03d}"

    # established_facts
    for item in data.get("established_facts", []) or []:
        fact_id = item.get("id", "")
        content = item.get("content", "")
        chapter = item.get("chapter", 0)
        eid = fact_id if fact_id else make_id("fact")
        events.append({
            "id": eid, "document": content,
            "metadata": {
                "category": "event", "character_id": "",
                "chapter_ref": chapter if isinstance(chapter, int) else 0,
                "event_name": content[:60], "status": "active", "original_id": fact_id,
            },
        })

    # global_memory
    for item in data.get("global_memory", []) or []:
        if isinstance(item, str):
            item = {"event": item}
        if not isinstance(item, dict):
            continue
        event_name = item.get("event", "unknown")
        description = item.get("description", "")
        chapter = item.get("chapter_ref", 0)
        status = item.get("status", "active")
        doc = f"{event_name}: {description}" if description else event_name
        events.append({
            "id": make_id("global"), "document": doc,
            "metadata": {
                "category": "global_memory", "character_id": "",
                "chapter_ref": chapter if isinstance(chapter, int) else 0,
                "event_name": event_name,
                "status": status.lower() if isinstance(status, str) else "active",
            },
        })

    # character_memory
    char_mem = data.get("character_memory", {}) or {}
    if isinstance(char_mem, dict):
        for char_id, entries in char_mem.items():
            if not isinstance(entries, list):
                continue
            for item in entries:
                event_name = item.get("event", "unknown")
                description = item.get("description", "")
                chapter = item.get("chapter_ref", 0)
                doc = f"{event_name}: {description}" if description else event_name
                events.append({
                    "id": make_id(f"char_{char_id}"), "document": doc,
                    "metadata": {
                        "category": "character_memory", "character_id": str(char_id),
                        "chapter_ref": chapter if isinstance(chapter, int) else 0,
                        "event_name": event_name, "status": "active",
                    },
                })

    # mysteries
    for item in data.get("mysteries", []) or []:
        if isinstance(item, str):
            item = {"title": item}
        if not isinstance(item, dict):
            continue
        mystery_id = item.get("id", "unknown")
        title = item.get("title", "")
        description = item.get("description", "")
        status = item.get("status", "Unresolved")
        doc = f"{title}: {description}" if description else title
        events.append({
            "id": make_id("mystery"), "document": doc,
            "metadata": {
                "category": "mystery", "character_id": "", "chapter_ref": 0,
                "event_name": title,
                "status": status.lower() if isinstance(status, str) else "unresolved",
                "mystery_id": mystery_id,
            },
        })

    # events — may be a list or a dict of sub-lists (e.g. arc_1: [...])
    raw_events = data.get("events", []) or []
    if isinstance(raw_events, dict):
        flat_events = []
        for _arc_key, arc_list in raw_events.items():
            if isinstance(arc_list, list):
                flat_events.extend(arc_list)
        raw_events = flat_events
    for item in raw_events:
        if isinstance(item, str):
            item = {"summary": item}
        if not isinstance(item, dict):
            continue
        summary = item.get("summary", "") or item.get("description", "") or item.get("event", "")
        chapter = item.get("chapter", 0)
        participants = item.get("participants", [])
        consequences = item.get("consequences", [])
        impact = item.get("impact", "")
        event_id_orig = item.get("id", "")
        doc_parts = [summary]
        if impact:
            doc_parts.append("影響: " + impact)
        if consequences:
            doc_parts.append("後果: " + "; ".join(str(c) for c in consequences))
        doc = ". ".join(p for p in doc_parts if p)
        events.append({
            "id": make_id("event"), "document": doc,
            "metadata": {
                "category": "event",
                "character_id": ", ".join(str(p) for p in participants) if participants else "",
                "chapter_ref": chapter if isinstance(chapter, int) else 0,
                "event_name": summary[:60], "status": "active", "original_id": event_id_orig,
            },
        })

    # world_facts — items may be plain strings
    for item in data.get("world_facts", []) or []:
        if isinstance(item, str):
            item = {"content": item}
        if not isinstance(item, dict):
            continue
        content = item.get("content", "") or item.get("description", "") or item.get("fact", "")
        fact_category = item.get("category", "")
        established = item.get("established_in", "")
        fact_id = item.get("id", "")
        ch = 0
        if isinstance(established, str) and established.startswith("chapter_"):
            try:
                ch = int(established.replace("chapter_", ""))
            except ValueError:
                pass
        elif isinstance(established, int):
            ch = established
        events.append({
            "id": make_id("fact"), "document": content,
            "metadata": {
                "category": "world_fact", "character_id": "", "chapter_ref": ch,
                "event_name": content[:60], "status": "permanent",
                "fact_category": fact_category, "original_id": fact_id,
            },
        })

    # relationship_changes
    for item in data.get("relationship_changes", []) or []:
        if isinstance(item, str):
            item = {"change": item}
        if not isinstance(item, dict):
            continue
        change = item.get("change", "") or item.get("description", "")
        chapter = item.get("chapter", 0)
        current_state = item.get("current_state", "")
        doc = f"{change} (目前: {current_state})" if current_state else change
        events.append({
            "id": make_id("relationship"), "document": doc,
            "metadata": {
                "category": "relationship_change", "character_id": "",
                "chapter_ref": chapter if isinstance(chapter, int) else 0,
                "event_name": change[:60], "status": "active",
            },
        })

    # open_foreshadowing
    for item in data.get("open_foreshadowing", []) or []:
        if isinstance(item, str):
            item = {"hint": item}
        if not isinstance(item, dict):
            continue
        hint = item.get("hint", "") or item.get("content", "") or item.get("description", "")
        planted = item.get("planted_in", "") or item.get("planted_chapter", 0)
        fore_category = item.get("category", "")
        fore_id = item.get("id", "")
        fore_status = item.get("status", "open")
        ch = 0
        if isinstance(planted, str) and planted.startswith("chapter_"):
            try:
                ch = int(planted.replace("chapter_", ""))
            except ValueError:
                pass
        elif isinstance(planted, int):
            ch = planted
        eid = fore_id if fore_id else make_id("foreshadow_open")
        events.append({
            "id": eid, "document": f"[伏筆] {hint}",
            "metadata": {
                "category": "foreshadowing", "character_id": "", "chapter_ref": ch,
                "event_name": hint[:60],
                "status": fore_status.lower() if isinstance(fore_status, str) else "open",
                "foreshadow_category": fore_category, "original_id": fore_id,
            },
        })

    # closed_foreshadowing
    for item in data.get("closed_foreshadowing", []) or []:
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict):
            continue
        desc = item.get("description", "") or item.get("content", "") or item.get("hint", "")
        planted = item.get("planted_in", "") or item.get("planted_chapter", 0)
        fore_id = item.get("id", "")
        ch = 0
        if isinstance(planted, str) and planted.startswith("chapter_"):
            try:
                ch = int(planted.replace("chapter_", ""))
            except ValueError:
                pass
        elif isinstance(planted, int):
            ch = planted
        eid = fore_id if fore_id else make_id("foreshadow_closed")
        events.append({
            "id": eid, "document": f"[已回收伏筆] {desc}",
            "metadata": {
                "category": "foreshadowing", "character_id": "", "chapter_ref": ch,
                "event_name": desc[:60], "status": "closed", "original_id": fore_id,
            },
        })

    # item_status
    for item in data.get("item_status", []) or []:
        if isinstance(item, str):
            item = {"item_id": item}
        if not isinstance(item, dict):
            continue
        item_name = item.get("item_id", "") or item.get("name", "")
        owner = item.get("current_owner", "")
        condition = item.get("condition", "")
        last_seen = item.get("last_seen", "")
        doc = f"物品「{item_name}」由 {owner} 持有，狀態: {condition}"
        ch = 0
        if isinstance(last_seen, str) and last_seen.startswith("chapter_"):
            try:
                ch = int(last_seen.replace("chapter_", ""))
            except ValueError:
                pass
        elif isinstance(last_seen, int):
            ch = last_seen
        events.append({
            "id": make_id("item"), "document": doc,
            "metadata": {
                "category": "item_status", "character_id": owner, "chapter_ref": ch,
                "event_name": item_name,
                "status": condition.lower() if isinstance(condition, str) else "unknown",
            },
        })

    # permanent_changes
    for item in data.get("permanent_changes", []) or []:
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict):
            continue
        char_id = item.get("character_id", "")
        chapter = item.get("chapter", 0)
        desc = item.get("description", "")
        events.append({
            "id": make_id("permanent"), "document": f"[永久改變] {desc}",
            "metadata": {
                "category": "permanent_change", "character_id": str(char_id),
                "chapter_ref": chapter if isinstance(chapter, int) else 0,
                "event_name": desc[:60], "status": "permanent",
            },
        })

    return events


def migrate_lore(project_folder: str, dry_run: bool = False, verify: bool = False):
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "memory", "lore_bank.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: {yaml_path} not found")
        return

    print(f"\n  [lore] {yaml_path}")
    events = parse_lore_bank(yaml_path)
    print(f"    records: {len(events)}")

    cats = {}
    for e in events:
        cat = e["metadata"].get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"      {cat}: {count}")

    if dry_run:
        print("    (dry-run)")
        for e in events[:5]:
            print(f"      [{e['id']}] {e['document'][:60]}...")
        return

    lv = LoreVector(project_folder)

    if verify:
        db_count = lv.count()
        print(f"    YAML: {len(events)}, ChromaDB: {db_count}")
        if db_count == len(events):
            print("    OK: counts match")
        elif db_count > len(events):
            print(f"    ChromaDB has {db_count - len(events)} extra (may include manual adds)")
        else:
            print(f"    MISSING: {len(events) - db_count} records")
        return

    lv.add_events_batch(events)
    print(f"    OK: {lv.count()} records -> {lv.db_path}")


# ════════════════════════════════════════════════════════════
#  Item Compendium 遷移
# ════════════════════════════════════════════════════════════

def parse_item_compendium(yaml_path: str) -> dict:
    """
    解析 item_compendium.yaml，回傳
    {"items": [...], "transactions": [...], "bibi_account": [...]}
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return {"items": [], "transactions": [], "bibi_account": []}

    items = []
    for item in data.get("items", []) or []:
        # 固定欄位
        item_id = item.get("id", "")
        name = item.get("name", "")
        category = item.get("category", "Tool")
        sub_type = item.get("sub_type", "")
        description = item.get("description", "")
        holder = item.get("holder", "")
        obtained_chapter = item.get("obtained_chapter")
        current_status = item.get("current_status", "")
        quantity = item.get("quantity", 1)

        # 剩餘欄位放 properties
        known_keys = {"id", "name", "category", "sub_type", "description",
                       "holder", "obtained_chapter", "current_status", "quantity"}
        properties = {k: v for k, v in item.items() if k not in known_keys}

        items.append({
            "id": item_id, "name": name, "category": category,
            "sub_type": sub_type, "description": description,
            "properties": properties, "holder": str(holder) if holder else "",
            "obtained_chapter": obtained_chapter,
            "current_status": current_status, "quantity": quantity,
        })

    transactions = []
    for tx in data.get("transactions", []) or []:
        chapter = tx.get("chapter", 0)
        desc = tx.get("description", "")
        # 嘗試從描述中提取餘額
        balance = ""
        for marker in ["結餘約", "存款約", "存款維持約", "結餘維持約", "結餘從", "結餘仍約"]:
            if marker in desc:
                idx = desc.index(marker)
                balance = desc[idx:]
                # 取到句號或句尾
                for end_char in ["。", "，", "；", "+"]:
                    if end_char in balance:
                        balance = balance[:balance.index(end_char)]
                        break
                break
        transactions.append({
            "chapter": chapter, "description": desc, "balance_after": balance,
        })

    bibi_entries = []
    bibi_data = data.get("bibi_account", {}) or {}
    for entry in bibi_data.get("entries", []) or []:
        bibi_entries.append({
            "chapter": entry.get("chapter", 0),
            "description": entry.get("description", ""),
            "status": entry.get("status", "待結清"),
        })

    return {"items": items, "transactions": transactions, "bibi_account": bibi_entries}


def migrate_items(project_folder: str, dry_run: bool = False, verify: bool = False):
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "config", "item_compendium.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: {yaml_path} not found")
        return

    print(f"\n  [item] {yaml_path}")
    parsed = parse_item_compendium(yaml_path)
    items = parsed["items"]
    txs = parsed["transactions"]
    bibi = parsed["bibi_account"]
    print(f"    items: {len(items)}, transactions: {len(txs)}, bibi_account: {len(bibi)}")

    if dry_run:
        print("    (dry-run)")
        for it in items[:5]:
            print(f"      {it['id']:12s} {it['category']:16s} {it['name']}")
        if len(items) > 5:
            print(f"      ... and {len(items) - 5} more")
        return

    from tools.item_db import ItemDB
    db = ItemDB(project_folder)
    try:
        if verify:
            s = db.stats()
            print(f"    YAML items: {len(items)}, DB items: {s['total_items']}")
            print(f"    YAML tx: {len(txs)}, DB tx: {s['total_transactions']}")
            print(f"    YAML bibi: {len(bibi)}, DB bibi: {s['bibi_total']}")
            all_match = (s['total_items'] == len(items)
                         and s['total_transactions'] == len(txs)
                         and s['bibi_total'] == len(bibi))
            if all_match:
                print("    OK: all counts match")
            else:
                print("    MISMATCH detected")
            # spot check
            for it in items[:3]:
                found = db.get_item(it["id"])
                status = "found" if found else "MISSING"
                print(f"      {it['id']}: {status}")
            return

        for it in items:
            db.upsert_item(
                it["id"], it["name"], it["category"], it["sub_type"],
                it["description"], it["properties"], it["holder"],
                it["obtained_chapter"], it["current_status"], it["quantity"],
            )
        for tx in txs:
            db.add_transaction(tx["chapter"], tx["description"], tx["balance_after"])
        for entry in bibi:
            db.add_bibi_entry(entry["chapter"], entry["description"], entry["status"])
        s = db.stats()
        print(f"    OK: {s['total_items']} items, {s['total_transactions']} tx, {s['bibi_total']} bibi -> {db.db_path}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  Faction Registry 遷移
# ════════════════════════════════════════════════════════════

def parse_faction_registry(yaml_path: str) -> dict:
    """
    解析 faction_registry.yaml，回傳
    {"factions": [...], "relations": [...], "events": [...]}
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return {"factions": [], "relations": [], "events": []}

    factions = []
    for fac in data.get("factions", []) or []:
        fac_id = fac.get("id", "")
        name = fac.get("name", "")
        tier = fac.get("tier", "")
        faction_type = fac.get("type", "")
        philosophy = fac.get("philosophy", "")
        description = fac.get("description", "")

        # 剩餘欄位放 properties
        known_keys = {"id", "name", "tier", "type", "philosophy", "description"}
        properties = {k: v for k, v in fac.items() if k not in known_keys}

        factions.append({
            "id": fac_id, "name": name, "tier": tier,
            "type": faction_type, "philosophy": philosophy,
            "description": description, "properties": properties,
        })

    relations = []
    for rel in data.get("relations", []) or []:
        source_id = rel.get("source_id", "")
        target_id = rel.get("target_id", "")
        status = rel.get("status", "Neutral")
        tension = rel.get("tension", 0)

        known_keys = {"source_id", "target_id", "status", "tension"}
        properties = {k: v for k, v in rel.items() if k not in known_keys}

        relations.append({
            "source_id": source_id, "target_id": target_id,
            "status": status, "tension": tension, "properties": properties,
        })

    events = []
    for evt in data.get("current_events", []) or []:
        event_id = evt.get("event_id", "")
        affected = evt.get("affected_factions", [])
        description = evt.get("description", "")
        impact = evt.get("impact", "")

        known_keys = {"event_id", "affected_factions", "description", "impact"}
        properties = {k: v for k, v in evt.items() if k not in known_keys}

        events.append({
            "event_id": event_id, "affected_factions": affected,
            "description": description, "impact": impact, "properties": properties,
        })

    return {"factions": factions, "relations": relations, "events": events}


def migrate_factions(project_folder: str, dry_run: bool = False, verify: bool = False):
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "config", "faction_registry.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: {yaml_path} not found")
        return

    print(f"\n  [faction] {yaml_path}")
    parsed = parse_faction_registry(yaml_path)
    facs = parsed["factions"]
    rels = parsed["relations"]
    evts = parsed["events"]
    print(f"    factions: {len(facs)}, relations: {len(rels)}, events: {len(evts)}")

    if dry_run:
        print("    (dry-run)")
        for f in facs[:5]:
            print(f"      {f['id']:12s} [{f['tier']:2s}] {f['name']}")
        if len(facs) > 5:
            print(f"      ... and {len(facs) - 5} more")
        return

    from tools.faction_db import FactionDB
    db = FactionDB(project_folder)
    try:
        if verify:
            db_count = db.count()
            print(f"    YAML: {len(facs)}, DB: {db_count}")
            if db_count == len(facs):
                print("    OK: counts match")
            else:
                print(f"    MISMATCH: diff={db_count - len(facs)}")
            for f in facs[:3]:
                found = db.get_faction(f["id"])
                status = "found" if found else "MISSING"
                print(f"      {f['id']}: {status}")
            return

        for f in facs:
            db.upsert_faction(
                f["id"], f["name"], f["tier"], f["type"],
                f["philosophy"], f["description"], f["properties"],
            )
        for r in rels:
            db.upsert_relation(
                r["source_id"], r["target_id"],
                r["status"], r["tension"], r["properties"],
            )
        for e in evts:
            db.upsert_event(
                e["event_id"], e["affected_factions"],
                e["description"], e["impact"], e["properties"],
            )
        s = db.stats()
        print(f"    OK: {s['total_factions']} factions, {s['total_relations']} relations, {s['total_events']} events -> {db.db_path}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  World Atlas 遷移
# ════════════════════════════════════════════════════════════

def parse_world_atlas(yaml_path: str) -> list[dict]:
    """
    解析 world_atlas.yaml，回傳 list of regions/zones/transit entries。
    每個 region 的 locations 存在 properties JSON 中。
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    entries = []

    # regions（含嵌套 locations）
    for reg in data.get("regions", []) or []:
        reg_id = reg.get("id", "")
        name = reg.get("name", "")
        reg_type = reg.get("type", "region")
        description = reg.get("description", "")

        known_keys = {"id", "name", "type"}
        properties = {k: v for k, v in reg.items() if k not in known_keys}

        entries.append({
            "id": reg_id, "name": name,
            "region_type": reg_type, "parent_id": "",
            "summary": description[:100] if description else "",
            "properties": properties,
        })

    # zones
    for zone in data.get("zones", []) or []:
        zone_id = zone.get("id", "")
        name = zone.get("name", "")
        zone_type = zone.get("type", "zone")
        parent = zone.get("parent_region", "")

        known_keys = {"id", "name", "type", "parent_region"}
        properties = {k: v for k, v in zone.items() if k not in known_keys}

        entries.append({
            "id": zone_id, "name": name,
            "region_type": zone_type, "parent_id": parent,
            "summary": zone.get("mechanics", "")[:100],
            "properties": properties,
        })

    # transit_network (可能是 dict 或 list)
    transit_data = data.get("transit_network", None)
    if isinstance(transit_data, dict):
        # 整個 transit_network 存為單一 entry
        entries.append({
            "id": "TRANSIT_NETWORK", "name": "transit_network",
            "region_type": "transit", "parent_id": "",
            "summary": f"connections: {len(transit_data.get('connections', []))}",
            "properties": transit_data,
        })
    elif isinstance(transit_data, list):
        for transit in transit_data:
            if not isinstance(transit, dict):
                continue
            transit_id = transit.get("id", "")
            transit_type = transit.get("type", "transit")
            name = transit_type

            known_keys = {"id", "type"}
            properties = {k: v for k, v in transit.items() if k not in known_keys}

            entries.append({
                "id": transit_id, "name": name,
                "region_type": "transit", "parent_id": "",
                "summary": f"stops: {transit.get('stops', [])}",
                "properties": properties,
            })

    return entries


def migrate_atlas(project_folder: str, dry_run: bool = False, verify: bool = False):
    yaml_path = os.path.join(PROJECT_ROOT, project_folder, "config", "world_atlas.yaml")
    if not os.path.exists(yaml_path):
        print(f"  skip: {yaml_path} not found")
        return

    print(f"\n  [atlas] {yaml_path}")
    entries = parse_world_atlas(yaml_path)
    print(f"    entries: {len(entries)}")

    types = {}
    for e in entries:
        t = e["region_type"]
        types[t] = types.get(t, 0) + 1
    for t, cnt in sorted(types.items()):
        print(f"      {t}: {cnt}")

    if dry_run:
        print("    (dry-run)")
        for e in entries[:5]:
            print(f"      {e['id']:12s} [{e['region_type']:10s}] {e['name']}")
        if len(entries) > 5:
            print(f"      ... and {len(entries) - 5} more")
        return

    from tools.atlas_db import AtlasDB
    db = AtlasDB(project_folder)
    try:
        if verify:
            db_count = db.count()
            print(f"    YAML: {len(entries)}, DB: {db_count}")
            if db_count == len(entries):
                print("    OK: counts match")
            else:
                print(f"    MISMATCH: diff={db_count - len(entries)}")
            for e in entries[:3]:
                found = db.get_region(e["id"])
                status = "found" if found else "MISSING"
                print(f"      {e['id']}: {status}")
            return

        for e in entries:
            db.upsert_region(
                e["id"], e["name"], e["region_type"],
                e["parent_id"], e["summary"], e["properties"],
            )
        s = db.stats()
        print(f"    OK: {s['total_entries']} entries -> {db.db_path}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  主程式
# ════════════════════════════════════════════════════════════

def migrate_project(project_folder: str, targets: list[str],
                    dry_run: bool = False, verify: bool = False):
    print(f"\n{'='*50}")
    print(f"  {project_folder}")
    print(f"{'='*50}")

    if "lore" in targets or "all" in targets:
        migrate_lore(project_folder, dry_run=dry_run, verify=verify)
    if "char" in targets or "all" in targets:
        migrate_characters(project_folder, dry_run=dry_run, verify=verify)
    if "emotion" in targets or "all" in targets:
        migrate_emotions(project_folder, dry_run=dry_run, verify=verify)
    if "item" in targets or "all" in targets:
        migrate_items(project_folder, dry_run=dry_run, verify=verify)
    if "faction" in targets or "all" in targets:
        migrate_factions(project_folder, dry_run=dry_run, verify=verify)
    if "atlas" in targets or "all" in targets:
        migrate_atlas(project_folder, dry_run=dry_run, verify=verify)


def get_all_projects() -> list[str]:
    """取得所有有相關 YAML 的專案"""
    projects = set()
    if not os.path.isdir(PROJECT_ROOT):
        return []
    for name in sorted(os.listdir(PROJECT_ROOT)):
        proj_dir = os.path.join(PROJECT_ROOT, name)
        if not os.path.isdir(proj_dir):
            continue
        # 有任一 YAML 即算
        if (os.path.exists(os.path.join(proj_dir, "memory", "lore_bank.yaml"))
            or os.path.exists(os.path.join(proj_dir, "config", "character_db.yaml"))
            or os.path.exists(os.path.join(proj_dir, "memory", "emotion_log.yaml"))
            or os.path.exists(os.path.join(proj_dir, "config", "emotion_log.yaml"))
            or os.path.exists(os.path.join(proj_dir, "config", "item_compendium.yaml"))
            or os.path.exists(os.path.join(proj_dir, "config", "faction_registry.yaml"))
            or os.path.exists(os.path.join(proj_dir, "config", "world_atlas.yaml"))):
            projects.add(name)
    return sorted(projects)


def main():
    parser = argparse.ArgumentParser(
        description="統一資料遷移腳本 (YAML -> ChromaDB/SQLite)",
        epilog="targets: lore, char, emotion, item, faction, atlas, all",
    )
    parser.add_argument("--proj", type=str, help="專案名稱或別名")
    parser.add_argument("--all-projects", action="store_true", help="遷移所有專案")
    parser.add_argument("--dry-run", action="store_true", help="預覽模式")
    parser.add_argument("--verify", action="store_true", help="驗證已遷移的資料")
    parser.add_argument("targets", nargs="+", choices=["lore", "char", "emotion", "item", "faction", "atlas", "all"],
                        help="遷移目標")
    args = parser.parse_args()

    if not args.proj and not args.all_projects:
        parser.print_help()
        sys.exit(1)

    mode = "DRY-RUN" if args.dry_run else ("VERIFY" if args.verify else "MIGRATE")
    print(f"  migrate_db [{mode}] targets={args.targets}")

    if args.all_projects:
        projects = get_all_projects()
        print(f"  found {len(projects)} projects")
        for proj in projects:
            migrate_project(proj, args.targets, dry_run=args.dry_run, verify=args.verify)
    else:
        folder = get_project_folder(args.proj)
        if not folder:
            print(f"  project not found: {args.proj}")
            sys.exit(1)
        migrate_project(folder, args.targets, dry_run=args.dry_run, verify=args.verify)

    print(f"\n  done.")


if __name__ == "__main__":
    main()
