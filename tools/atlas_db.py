#!/usr/bin/env python3
"""
atlas_db.py — 世界地圖 SQLite 操作庫
取代 world_atlas.yaml，按區域存 JSON blob，支援按需載入。

使用方式:
    from tools.atlas_db import AtlasDB
    db = AtlasDB("加爾德打工人")

    # 摘要列表
    regions = db.list_regions()

    # 完整區域資料（含 locations）
    reg = db.get_region("REG_001")

    # 搜尋地點
    results = db.search("酒館")
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class AtlasDB:
    """單一專案的世界地圖 SQLite 資料庫"""

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
            CREATE TABLE IF NOT EXISTS world_regions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                region_type TEXT DEFAULT 'region',
                parent_id TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                properties TEXT DEFAULT '{}'
            );
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 查詢 ──

    def list_regions(self, region_type: str | None = None,
                     parent_id: str | None = None) -> list[dict]:
        """列出區域摘要：id, name, region_type, parent_id, summary"""
        sql = "SELECT id, name, region_type, parent_id, summary FROM world_regions WHERE 1=1"
        params: list = []
        if region_type:
            sql += " AND region_type = ?"
            params.append(region_type)
        if parent_id is not None:
            sql += " AND parent_id = ?"
            params.append(parent_id)
        sql += " ORDER BY id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "region_type": r["region_type"],
                "parent_id": r["parent_id"],
                "summary": (r["summary"] or "")[:100],
            }
            for r in rows
        ]

    def get_region(self, region_id: str) -> dict | None:
        """取得完整區域資料（含 locations 等所有 properties）"""
        row = self._conn.execute(
            "SELECT * FROM world_regions WHERE id = ?", (region_id,)
        ).fetchone()
        if not row:
            return None
        result = {
            "id": row["id"],
            "name": row["name"],
            "region_type": row["region_type"],
            "parent_id": row["parent_id"],
        }
        props = json.loads(row["properties"])
        result.update(props)
        return result

    def search(self, keyword: str) -> list[dict]:
        """搜尋區域/地點名稱或描述（含 properties JSON 內的文字）"""
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            "SELECT id, name, region_type, parent_id, summary FROM world_regions "
            "WHERE name LIKE ? OR summary LIKE ? OR properties LIKE ? ORDER BY id",
            (pattern, pattern, pattern),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "region_type": r["region_type"],
                "parent_id": r["parent_id"],
                "summary": (r["summary"] or "")[:100],
            }
            for r in rows
        ]

    # ── 寫入 ──

    def upsert_region(self, region_id: str, name: str,
                      region_type: str = "region", parent_id: str = "",
                      summary: str = "", properties: dict | None = None):
        """新增或更新區域"""
        props = properties or {}
        self._conn.execute(
            """INSERT INTO world_regions (id, name, region_type, parent_id, summary, properties)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, region_type=excluded.region_type,
                 parent_id=excluded.parent_id, summary=excluded.summary,
                 properties=excluded.properties""",
            (region_id, name, region_type, parent_id, summary,
             json.dumps(props, ensure_ascii=False)),
        )
        self._conn.commit()

    def update_field(self, region_id: str, field: str, value):
        """更新 properties 中的單一欄位"""
        row = self._conn.execute(
            "SELECT properties FROM world_regions WHERE id = ?", (region_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"區域不存在: {region_id}")
        props = json.loads(row["properties"])
        props[field] = value
        self._conn.execute(
            "UPDATE world_regions SET properties = ? WHERE id = ?",
            (json.dumps(props, ensure_ascii=False), region_id),
        )
        self._conn.commit()

    def delete_region(self, region_id: str):
        """刪除區域"""
        self._conn.execute("DELETE FROM world_regions WHERE id = ?", (region_id,))
        self._conn.commit()

    def count(self, region_type: str | None = None) -> int:
        if region_type:
            return self._conn.execute(
                "SELECT COUNT(*) FROM world_regions WHERE region_type = ?", (region_type,)
            ).fetchone()[0]
        return self._conn.execute("SELECT COUNT(*) FROM world_regions").fetchone()[0]

    def stats(self) -> dict:
        total = self.count()
        types = {}
        for row in self._conn.execute(
            "SELECT region_type, COUNT(*) as cnt FROM world_regions GROUP BY region_type"
        ):
            types[row["region_type"] or "N/A"] = row["cnt"]
        return {
            "project": self.project_name,
            "total_entries": total,
            "types": types,
            "db_path": self.db_path,
        }
