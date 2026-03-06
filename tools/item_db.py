#!/usr/bin/env python3
"""
item_db.py — 物品/交易/嗶嗶帳本 SQLite 操作庫
取代 item_compendium.yaml，支援按需載入以節省 context/token。

使用方式:
    from tools.item_db import ItemDB
    db = ItemDB("加爾德打工人")

    # 道具摘要列表
    items = db.list_items()

    # 按需載入單一道具
    item = db.get_item("SHELL_001")

    # 最近交易
    txs = db.get_recent_transactions(5)

    # 嗶嗶未結清帳單
    pending = db.get_bibi_pending()
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class ItemDB:
    """單一專案的物品/交易 SQLite 資料庫"""

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
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                sub_type TEXT DEFAULT '',
                description TEXT DEFAULT '',
                properties TEXT DEFAULT '{}',
                holder TEXT DEFAULT '',
                obtained_chapter INTEGER,
                current_status TEXT DEFAULT '',
                quantity INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter INTEGER NOT NULL,
                description TEXT NOT NULL,
                balance_after TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS bibi_account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '待結清'
            );
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 道具查詢 ──

    def list_items(self, category: str | None = None) -> list[dict]:
        """列出道具摘要：id, name, category, holder, quantity"""
        sql = "SELECT id, name, category, holder, quantity FROM items"
        params: list = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "holder": r["holder"] or "",
                "quantity": r["quantity"],
            }
            for r in rows
        ]

    def get_item(self, item_id: str) -> dict | None:
        """取得完整道具資料"""
        row = self._conn.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return None
        result = {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "sub_type": row["sub_type"],
            "description": row["description"],
            "holder": row["holder"] or "",
            "obtained_chapter": row["obtained_chapter"],
            "current_status": row["current_status"],
            "quantity": row["quantity"],
        }
        props = json.loads(row["properties"])
        if props:
            result["properties"] = props
        return result

    def search_items(self, keyword: str) -> list[dict]:
        """搜尋道具名稱或描述"""
        pattern = f"%{keyword}%"
        rows = self._conn.execute(
            "SELECT id, name, category, holder, quantity FROM items WHERE name LIKE ? OR description LIKE ? ORDER BY id",
            (pattern, pattern),
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "category": r["category"],
             "holder": r["holder"] or "", "quantity": r["quantity"]}
            for r in rows
        ]

    def get_items_by_holder(self, holder: str) -> list[dict]:
        """查某角色持有的所有道具"""
        rows = self._conn.execute(
            "SELECT id, name, category, holder, quantity FROM items WHERE holder = ? ORDER BY id",
            (holder,),
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "category": r["category"],
             "holder": r["holder"] or "", "quantity": r["quantity"]}
            for r in rows
        ]

    # ── 道具寫入 ──

    def upsert_item(self, item_id: str, name: str, category: str,
                    sub_type: str = "", description: str = "",
                    properties: dict | None = None, holder: str = "",
                    obtained_chapter: int | None = None,
                    current_status: str = "", quantity: int = 1):
        """新增或更新道具"""
        self._conn.execute(
            """INSERT INTO items (id, name, category, sub_type, description, properties, holder, obtained_chapter, current_status, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, category=excluded.category, sub_type=excluded.sub_type,
                 description=excluded.description, properties=excluded.properties, holder=excluded.holder,
                 obtained_chapter=excluded.obtained_chapter, current_status=excluded.current_status,
                 quantity=excluded.quantity""",
            (item_id, name, category, sub_type, description,
             json.dumps(properties or {}, ensure_ascii=False),
             holder, obtained_chapter, current_status, quantity),
        )
        self._conn.commit()

    def update_item(self, item_id: str, **kwargs):
        """更新道具的指定欄位"""
        row = self._conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise ValueError(f"道具不存在: {item_id}")
        allowed = {"name", "category", "sub_type", "description", "holder",
                    "obtained_chapter", "current_status", "quantity"}
        updates = []
        params = []
        for k, v in kwargs.items():
            if k == "properties":
                updates.append("properties = ?")
                params.append(json.dumps(v, ensure_ascii=False))
            elif k in allowed:
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return
        params.append(item_id)
        self._conn.execute(
            f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params
        )
        self._conn.commit()

    # ── 交易查詢 ──

    def get_recent_transactions(self, n: int = 5) -> list[dict]:
        """取得最近 n 筆交易"""
        rows = self._conn.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [
            {"id": r["id"], "chapter": r["chapter"],
             "description": r["description"], "balance_after": r["balance_after"]}
            for r in reversed(rows)
        ]

    def get_transactions_by_range(self, ch_from: int, ch_to: int) -> list[dict]:
        """取得指定章節範圍的交易"""
        rows = self._conn.execute(
            "SELECT * FROM transactions WHERE chapter >= ? AND chapter <= ? ORDER BY id",
            (ch_from, ch_to),
        ).fetchall()
        return [
            {"id": r["id"], "chapter": r["chapter"],
             "description": r["description"], "balance_after": r["balance_after"]}
            for r in rows
        ]

    def get_balance(self) -> str:
        """取得最近一筆有餘額記錄的交易"""
        row = self._conn.execute(
            "SELECT chapter, description, balance_after FROM transactions WHERE balance_after != '' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return "(no balance record)"
        return f"ch{row['chapter']}: {row['balance_after']} — {row['description'][:80]}"

    def add_transaction(self, chapter: int, description: str, balance_after: str = ""):
        """新增交易紀錄"""
        self._conn.execute(
            "INSERT INTO transactions (chapter, description, balance_after) VALUES (?, ?, ?)",
            (chapter, description, balance_after),
        )
        self._conn.commit()

    # ── 嗶嗶帳本查詢 ──

    def get_bibi_pending(self) -> list[dict]:
        """取得未結清的嗶嗶帳本項目"""
        rows = self._conn.execute(
            "SELECT * FROM bibi_account WHERE status NOT LIKE '%已結清%' AND status NOT LIKE '%永久免除%' ORDER BY id"
        ).fetchall()
        return [
            {"id": r["id"], "chapter": r["chapter"],
             "description": r["description"], "status": r["status"]}
            for r in rows
        ]

    def get_bibi_all(self) -> list[dict]:
        """取得全部嗶嗶帳本"""
        rows = self._conn.execute(
            "SELECT * FROM bibi_account ORDER BY id"
        ).fetchall()
        return [
            {"id": r["id"], "chapter": r["chapter"],
             "description": r["description"], "status": r["status"]}
            for r in rows
        ]

    def add_bibi_entry(self, chapter: int, description: str, status: str = "待結清"):
        """新增嗶嗶帳本項目"""
        self._conn.execute(
            "INSERT INTO bibi_account (chapter, description, status) VALUES (?, ?, ?)",
            (chapter, description, status),
        )
        self._conn.commit()

    def settle_bibi(self, entry_id: int, status: str):
        """更新嗶嗶帳本項目狀態"""
        self._conn.execute(
            "UPDATE bibi_account SET status = ? WHERE id = ?",
            (status, entry_id),
        )
        self._conn.commit()

    # ── 統計 ──

    def stats(self) -> dict:
        item_count = self._conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        categories = {}
        for row in self._conn.execute("SELECT category, COUNT(*) as cnt FROM items GROUP BY category"):
            categories[row["category"]] = row["cnt"]
        tx_count = self._conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        bibi_total = self._conn.execute("SELECT COUNT(*) FROM bibi_account").fetchone()[0]
        bibi_pending = self._conn.execute(
            "SELECT COUNT(*) FROM bibi_account WHERE status NOT LIKE '%已結清%' AND status NOT LIKE '%永久免除%'"
        ).fetchone()[0]
        return {
            "project": self.project_name,
            "total_items": item_count,
            "categories": categories,
            "total_transactions": tx_count,
            "bibi_total": bibi_total,
            "bibi_pending": bibi_pending,
            "db_path": self.db_path,
        }
