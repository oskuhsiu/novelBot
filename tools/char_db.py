#!/usr/bin/env python3
"""
char_db.py — 角色資料庫 SQLite 操作庫
取代 character_db.yaml，支援按需載入角色資料以節省 context/token。

使用方式:
    from tools.char_db import CharacterDB
    db = CharacterDB("加爾德打工人")

    # 摘要列表（低 token）
    summaries = db.list_characters()

    # 按需載入完整資料
    char = db.get_character("CHAR_001")

    # 只取 current_state
    state = db.get_state("CHAR_001")

    # 更新 current_state
    db.update_state("CHAR_001", {"location": "酒館", "health": "80%", ...})

    # 關係查詢
    rels = db.get_relationships("CHAR_001")
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class CharacterDB:
    """單一專案的角色 SQLite 資料庫"""

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
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Minor',
                type TEXT NOT NULL DEFAULT 'character',
                identity TEXT DEFAULT '',
                base_profile TEXT DEFAULT '{}',
                current_state TEXT DEFAULT '{}',
                notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                surface_relation TEXT DEFAULT '',
                hidden_dynamic TEXT DEFAULT '',
                common_interest TEXT DEFAULT '',
                tension INTEGER DEFAULT 0,
                UNIQUE(source_id, target_id)
            );
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 查詢 ──

    def list_characters(self, role: str | None = None, char_type: str = "character") -> list[dict]:
        """
        列出角色摘要：id, name, role, identity（前60字）。
        這是開頭固定載入的低 token 操作。
        """
        sql = "SELECT id, name, role, identity FROM characters WHERE type = ?"
        params: list = [char_type]
        if role:
            sql += " AND role = ?"
            params.append(role)
        sql += " ORDER BY id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "role": r["role"],
                "identity": (r["identity"] or "")[:60],
            }
            for r in rows
        ]

    def get_character(self, char_id: str) -> dict | None:
        """取得完整角色資料（base_profile + current_state + notes）"""
        row = self._conn.execute(
            "SELECT * FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "role": row["role"],
            "type": row["type"],
            "base_profile": json.loads(row["base_profile"]),
            "current_state": json.loads(row["current_state"]),
            "notes": row["notes"],
        }

    def get_state(self, char_id: str) -> dict | None:
        """只取 current_state（輕量查詢）"""
        row = self._conn.execute(
            "SELECT current_state FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["current_state"])

    def get_base(self, char_id: str) -> dict | None:
        """只取 base_profile"""
        row = self._conn.execute(
            "SELECT base_profile FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["base_profile"])

    def get_relationships(self, char_id: str | None = None) -> list[dict]:
        """取得關係。若指定 char_id，回傳該角色相關的所有關係。"""
        if char_id:
            rows = self._conn.execute(
                "SELECT * FROM relationships WHERE source_id = ? OR target_id = ? ORDER BY id",
                (char_id, char_id),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM relationships ORDER BY id").fetchall()
        return [
            {
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "surface_relation": r["surface_relation"],
                "hidden_dynamic": r["hidden_dynamic"],
                "common_interest": r["common_interest"],
                "tension": r["tension"],
            }
            for r in rows
        ]

    def search(self, keyword: str) -> list[dict]:
        """搜尋角色名稱或身份描述"""
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            "SELECT id, name, role, identity FROM characters WHERE name LIKE ? OR identity LIKE ? ORDER BY id",
            (pattern, pattern),
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "role": r["role"], "identity": (r["identity"] or "")[:60]}
            for r in rows
        ]

    # ── 寫入 ──

    def upsert_character(self, char_id: str, name: str, role: str,
                         char_type: str, identity: str,
                         base_profile: dict, current_state: dict, notes: str):
        """新增或更新完整角色資料"""
        self._conn.execute(
            """INSERT INTO characters (id, name, role, type, identity, base_profile, current_state, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, role=excluded.role, type=excluded.type,
                 identity=excluded.identity, base_profile=excluded.base_profile,
                 current_state=excluded.current_state, notes=excluded.notes""",
            (char_id, name, role, char_type, identity,
             json.dumps(base_profile, ensure_ascii=False),
             json.dumps(current_state, ensure_ascii=False),
             notes),
        )
        self._conn.commit()

    def update_state(self, char_id: str, state: dict):
        """更新 current_state（整體替換）"""
        self._conn.execute(
            "UPDATE characters SET current_state = ? WHERE id = ?",
            (json.dumps(state, ensure_ascii=False), char_id),
        )
        self._conn.commit()

    def update_field(self, char_id: str, path: str, value):
        """
        更新 current_state 中的單一欄位。
        path 格式: "location", "health", "emotional_state" 等頂層 key。
        """
        row = self._conn.execute(
            "SELECT current_state FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"角色不存在: {char_id}")
        state = json.loads(row["current_state"])
        state[path] = value
        self._conn.execute(
            "UPDATE characters SET current_state = ? WHERE id = ?",
            (json.dumps(state, ensure_ascii=False), char_id),
        )
        self._conn.commit()

    def upsert_relationship(self, source_id: str, target_id: str,
                            surface_relation: str = "", hidden_dynamic: str = "",
                            common_interest: str = "", tension: int = 0):
        """新增或更新關係"""
        self._conn.execute(
            """INSERT INTO relationships (source_id, target_id, surface_relation, hidden_dynamic, common_interest, tension)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(source_id, target_id) DO UPDATE SET
                 surface_relation=excluded.surface_relation, hidden_dynamic=excluded.hidden_dynamic,
                 common_interest=excluded.common_interest, tension=excluded.tension""",
            (source_id, target_id, surface_relation, hidden_dynamic, common_interest, tension),
        )
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]

    def stats(self) -> dict:
        total = self.count()
        roles = {}
        for row in self._conn.execute("SELECT role, COUNT(*) as cnt FROM characters GROUP BY role"):
            roles[row["role"]] = row["cnt"]
        rel_count = self._conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        return {
            "project": self.project_name,
            "total_characters": total,
            "roles": roles,
            "total_relationships": rel_count,
            "db_path": self.db_path,
        }
