#!/usr/bin/env python3
"""
review_db.py — Review 記錄 SQLite 操作庫
追蹤每次審查使用了哪些 assist 工具。

使用方式:
    from tools.review_db import ReviewDB
    db = ReviewDB("加爾德打工人")

    # 新增記錄
    db.add(chapter_id=58, assists=["codex","gemini"], mode="full", source="nvReview")

    # 查某章所有記錄
    rows = db.get(58)

    # 查某章最新一筆
    latest = db.get_latest(58)

    # 列出所有記錄
    rows = db.list_all()

    # 統計
    stats = db.stats()
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class ReviewDB:
    """單一專案的 Review 記錄 SQLite 資料庫"""

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
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS review_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                assists TEXT NOT NULL DEFAULT '[]',
                reviewed_at TEXT NOT NULL,
                mode TEXT DEFAULT '',
                source TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_review_log_chapter ON review_log(chapter_id);
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 查詢 ──

    def get(self, chapter_id: int) -> list[dict]:
        """取得某章所有 review 記錄"""
        rows = self._conn.execute(
            "SELECT * FROM review_log WHERE chapter_id = ? ORDER BY reviewed_at DESC",
            (chapter_id,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_latest(self, chapter_id: int) -> dict | None:
        """取得某章最新一筆 review 記錄"""
        row = self._conn.execute(
            "SELECT * FROM review_log WHERE chapter_id = ? ORDER BY reviewed_at DESC LIMIT 1",
            (chapter_id,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_all(self) -> list[dict]:
        """列出所有記錄（按 chapter_id, reviewed_at 排序）"""
        rows = self._conn.execute(
            "SELECT * FROM review_log ORDER BY chapter_id, reviewed_at DESC"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def stats(self) -> dict:
        """統計：哪些章有記錄、有/無 assist 分佈"""
        total = self._conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0]
        if total == 0:
            return {"project": self.project_name, "total_records": 0}

        chapters_reviewed = self._conn.execute(
            "SELECT COUNT(DISTINCT chapter_id) FROM review_log"
        ).fetchone()[0]

        ch_range = self._conn.execute(
            "SELECT MIN(chapter_id) as mn, MAX(chapter_id) as mx FROM review_log"
        ).fetchone()

        # 有 assist 的章（最新一筆 assists 非空陣列）
        rows = self._conn.execute(
            """SELECT chapter_id, assists FROM review_log
               WHERE id IN (SELECT MAX(id) FROM review_log GROUP BY chapter_id)
               ORDER BY chapter_id"""
        ).fetchall()

        with_assist = []
        without_assist = []
        for r in rows:
            assists = json.loads(r["assists"])
            if assists:
                with_assist.append(r["chapter_id"])
            else:
                without_assist.append(r["chapter_id"])

        return {
            "project": self.project_name,
            "total_records": total,
            "chapters_reviewed": chapters_reviewed,
            "chapter_range": f"{ch_range['mn']}-{ch_range['mx']}",
            "with_assist": with_assist,
            "without_assist": without_assist,
            "db_path": self.db_path,
        }

    # ── 寫入 ──

    def add(self, chapter_id: int, assists: list[str] | None = None,
            mode: str = "", source: str = "", reviewed_at: str = ""):
        """新增一筆 review 記錄"""
        if not reviewed_at:
            import datetime
            reviewed_at = datetime.datetime.now().isoformat(timespec="seconds")
        self._conn.execute(
            "INSERT INTO review_log (chapter_id, assists, reviewed_at, mode, source) VALUES (?, ?, ?, ?, ?)",
            (chapter_id, json.dumps(assists or [], ensure_ascii=False), reviewed_at, mode, source),
        )
        self._conn.commit()

    # ── 內部 ──

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row["id"],
            "chapter_id": row["chapter_id"],
            "assists": json.loads(row["assists"]),
            "reviewed_at": row["reviewed_at"],
            "mode": row["mode"],
            "source": row["source"],
        }
