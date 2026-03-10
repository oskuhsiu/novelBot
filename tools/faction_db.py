#!/usr/bin/env python3
"""
faction_db.py — 勢力資料庫 SQLite 操作庫
取代 faction_registry.yaml，支援按需載入以節省 context/token。

使用方式:
    from tools.faction_db import FactionDB
    db = FactionDB("加爾德打工人")

    # 摘要列表
    summaries = db.list_factions()

    # 完整資料
    fac = db.get_faction("FAC_001")

    # 關係查詢
    rels = db.get_relations("FAC_001")

    # 更新 tension
    db.update_tension("FAC_001", "FAC_002", 75)
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class FactionDB:
    """單一專案的勢力 SQLite 資料庫"""

    def __init__(self, project_name: str):
        folder = get_project_folder(project_name)
        if not folder:
            raise ValueError(f"找不到專案: {project_name}")
        self.project_name = folder
        self.db_dir = os.path.join(PROJECT_ROOT, folder, "data")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, "novel.db")
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS factions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier TEXT DEFAULT '',
                type TEXT DEFAULT '',
                philosophy TEXT DEFAULT '',
                description TEXT DEFAULT '',
                properties TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS faction_relations (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                status TEXT DEFAULT 'Neutral',
                tension INTEGER DEFAULT 0,
                properties TEXT DEFAULT '{}',
                UNIQUE(source_id, target_id)
            );
            CREATE TABLE IF NOT EXISTS faction_events (
                event_id TEXT PRIMARY KEY,
                affected_factions TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                impact TEXT DEFAULT '',
                properties TEXT DEFAULT '{}'
            );
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 查詢 ──

    def list_factions(self) -> list[dict]:
        """列出勢力摘要：id, name, tier, type, philosophy"""
        rows = self._conn.execute(
            "SELECT id, name, tier, type, philosophy FROM factions ORDER BY id"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "tier": r["tier"],
                "type": r["type"],
                "philosophy": (r["philosophy"] or "")[:80],
            }
            for r in rows
        ]

    def get_faction(self, faction_id: str) -> dict | None:
        """取得完整勢力資料"""
        row = self._conn.execute(
            "SELECT * FROM factions WHERE id = ?", (faction_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "tier": row["tier"],
            "type": row["type"],
            "philosophy": row["philosophy"],
            "description": row["description"],
            **json.loads(row["properties"]),
        }

    def get_relations(self, faction_id: str | None = None) -> list[dict]:
        """取得關係。若指定 faction_id，回傳該勢力相關的所有關係。"""
        if faction_id:
            rows = self._conn.execute(
                "SELECT * FROM faction_relations WHERE source_id = ? OR target_id = ? ORDER BY source_id, target_id",
                (faction_id, faction_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM faction_relations ORDER BY source_id, target_id"
            ).fetchall()
        return [
            {
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "status": r["status"],
                "tension": r["tension"],
                **json.loads(r["properties"]),
            }
            for r in rows
        ]

    def get_events(self) -> list[dict]:
        """取得所有勢力事件"""
        rows = self._conn.execute(
            "SELECT * FROM faction_events ORDER BY event_id"
        ).fetchall()
        return [
            {
                "event_id": r["event_id"],
                "affected_factions": json.loads(r["affected_factions"]),
                "description": r["description"],
                "impact": r["impact"],
                **json.loads(r["properties"]),
            }
            for r in rows
        ]

    def search(self, keyword: str) -> list[dict]:
        """搜尋勢力名稱或描述"""
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            "SELECT id, name, tier, type, philosophy FROM factions WHERE name LIKE ? OR description LIKE ? OR philosophy LIKE ? ORDER BY id",
            (pattern, pattern, pattern),
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "tier": r["tier"], "type": r["type"], "philosophy": (r["philosophy"] or "")[:80]}
            for r in rows
        ]

    # ── 寫入 ──

    def upsert_faction(self, faction_id: str, name: str, tier: str = "",
                       faction_type: str = "", philosophy: str = "",
                       description: str = "", properties: dict | None = None):
        """新增或更新勢力"""
        props = properties or {}
        self._conn.execute(
            """INSERT INTO factions (id, name, tier, type, philosophy, description, properties)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, tier=excluded.tier, type=excluded.type,
                 philosophy=excluded.philosophy, description=excluded.description,
                 properties=excluded.properties""",
            (faction_id, name, tier, faction_type, philosophy, description,
             json.dumps(props, ensure_ascii=False)),
        )
        self._conn.commit()

    def upsert_relation(self, source_id: str, target_id: str,
                        status: str = "Neutral", tension: int = 0,
                        properties: dict | None = None):
        """新增或更新勢力關係"""
        props = properties or {}
        self._conn.execute(
            """INSERT INTO faction_relations (source_id, target_id, status, tension, properties)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source_id, target_id) DO UPDATE SET
                 status=excluded.status, tension=excluded.tension, properties=excluded.properties""",
            (source_id, target_id, status, tension,
             json.dumps(props, ensure_ascii=False)),
        )
        self._conn.commit()

    def update_tension(self, source_id: str, target_id: str, tension: int):
        """只更新 tension 值"""
        self._conn.execute(
            "UPDATE faction_relations SET tension = ? WHERE source_id = ? AND target_id = ?",
            (tension, source_id, target_id),
        )
        self._conn.commit()

    def update_field(self, faction_id: str, field: str, value):
        """更新 properties 中的單一欄位"""
        row = self._conn.execute(
            "SELECT properties FROM factions WHERE id = ?", (faction_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"勢力不存在: {faction_id}")
        props = json.loads(row["properties"])
        props[field] = value
        self._conn.execute(
            "UPDATE factions SET properties = ? WHERE id = ?",
            (json.dumps(props, ensure_ascii=False), faction_id),
        )
        self._conn.commit()

    def upsert_event(self, event_id: str, affected_factions: list,
                     description: str = "", impact: str = "",
                     properties: dict | None = None):
        """新增或更新勢力事件"""
        props = properties or {}
        self._conn.execute(
            """INSERT INTO faction_events (event_id, affected_factions, description, impact, properties)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                 affected_factions=excluded.affected_factions, description=excluded.description,
                 impact=excluded.impact, properties=excluded.properties""",
            (event_id, json.dumps(affected_factions, ensure_ascii=False),
             description, impact, json.dumps(props, ensure_ascii=False)),
        )
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM factions").fetchone()[0]

    def stats(self) -> dict:
        total = self.count()
        tiers = {}
        for row in self._conn.execute("SELECT tier, COUNT(*) as cnt FROM factions GROUP BY tier"):
            tiers[row["tier"] or "N/A"] = row["cnt"]
        rel_count = self._conn.execute("SELECT COUNT(*) FROM faction_relations").fetchone()[0]
        evt_count = self._conn.execute("SELECT COUNT(*) FROM faction_events").fetchone()[0]
        return {
            "project": self.project_name,
            "total_factions": total,
            "tiers": tiers,
            "total_relations": rel_count,
            "total_events": evt_count,
            "db_path": self.db_path,
        }
