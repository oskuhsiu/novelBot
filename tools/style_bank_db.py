#!/usr/bin/env python3
"""
style_bank_db.py — 全域風格範本資料庫 SQLite 操作庫

使用方式:
    from tools.style_bank_db import StyleBankDB
    db = StyleBankDB()

    # 新增範本
    pid = db.add_passage(author="會說話的肘子", work="大王饒命", text="...",
                         chapter="第125章", source_url="...",
                         style_note="表面天真實則精準打擊",
                         tags=["comedy", "冷幽默"])

    # 按 tag 查詢
    results = db.search_by_tags(["comedy", "冷幽默"], mode="all", limit=5)

    # 隨機取
    results = db.random_by_tags(["emotion"], limit=2)

    # 統計
    stats = db.get_stats()
    coverage = db.get_coverage()
"""

import json
import os
import re
import sqlite3

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "style_bank.db")


def _count_chars(text: str) -> int:
    """計算中文字數（中文字+中文標點+英文單詞）"""
    cn = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    pn = len(re.findall(r"[\u3000-\u303f\uff01-\uff60\u2018-\u201f\u2014\u2026\uff5e]", text))
    en = len(re.findall(r"[a-zA-Z0-9]+", text))
    return cn + pn + en


class StyleBankDB:
    """全域風格範本 SQLite 資料庫"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS passages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                work TEXT NOT NULL,
                chapter TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                text TEXT NOT NULL,
                style_note TEXT DEFAULT '',
                lang TEXT DEFAULT 'zh-TW',
                char_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'general'
            );
            CREATE TABLE IF NOT EXISTS passage_tags (
                passage_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (passage_id, tag_id),
                FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            );
            CREATE INDEX IF NOT EXISTS idx_pt_tag ON passage_tags(tag_id);
            CREATE INDEX IF NOT EXISTS idx_pt_passage ON passage_tags(passage_id);
            CREATE INDEX IF NOT EXISTS idx_passages_author ON passages(author);
            CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category);
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── Tag 管理 ──

    def _ensure_tag(self, name: str, category: str = "general") -> int:
        """取得或建立 tag，回傳 tag_id"""
        row = self._conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self._conn.execute(
            "INSERT INTO tags (name, category) VALUES (?, ?)", (name, category)
        )
        self._conn.commit()
        return cur.lastrowid

    def _link_tags(self, passage_id: int, tag_names: list[str], category: str = "general"):
        """將 tags 關聯到 passage"""
        for tag_name in tag_names:
            tag_id = self._ensure_tag(tag_name.strip(), category)
            self._conn.execute(
                "INSERT OR IGNORE INTO passage_tags (passage_id, tag_id) VALUES (?, ?)",
                (passage_id, tag_id),
            )
        self._conn.commit()

    # ── 寫入 ──

    def add_passage(
        self,
        author: str,
        work: str,
        text: str,
        chapter: str = "",
        source_url: str = "",
        style_note: str = "",
        lang: str = "zh-TW",
        tags: list[str] | None = None,
        tag_category: str = "general",
    ) -> int:
        """新增一段範本，回傳 passage_id"""
        char_count = _count_chars(text)
        cur = self._conn.execute(
            """INSERT INTO passages (author, work, chapter, source_url, text, style_note, lang, char_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (author, work, chapter, source_url, text, style_note, lang, char_count),
        )
        pid = cur.lastrowid
        if tags:
            self._link_tags(pid, tags, tag_category)
        self._conn.commit()
        return pid

    def add_batch(self, entries: list[dict]) -> list[int]:
        """批次新增多段範本"""
        ids = []
        for e in entries:
            pid = self.add_passage(
                author=e["author"],
                work=e["work"],
                text=e["text"],
                chapter=e.get("chapter", ""),
                source_url=e.get("source_url", ""),
                style_note=e.get("style_note", ""),
                lang=e.get("lang", "zh-TW"),
                tags=e.get("tags"),
                tag_category=e.get("tag_category", "general"),
            )
            ids.append(pid)
        return ids

    # ── 查詢 ──

    def _row_to_dict(self, row) -> dict:
        """將 passage row 轉為 dict（含 tags）"""
        d = dict(row)
        tags = self._conn.execute(
            """SELECT t.name, t.category FROM tags t
               JOIN passage_tags pt ON t.id = pt.tag_id
               WHERE pt.passage_id = ?""",
            (d["id"],),
        ).fetchall()
        d["tags"] = [{"name": t["name"], "category": t["category"]} for t in tags]
        return d

    def get_passage(self, passage_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM passages WHERE id = ?", (passage_id,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def search_by_tags(
        self, tags: list[str], mode: str = "all", limit: int = 10, author: str | None = None
    ) -> list[dict]:
        """
        按 tag 搜尋。mode='all' 要求同時符合所有 tag，mode='any' 符合任一。
        """
        if not tags:
            return []

        placeholders = ",".join("?" * len(tags))

        if mode == "all":
            sql = f"""
                SELECT p.* FROM passages p
                JOIN passage_tags pt ON p.id = pt.passage_id
                JOIN tags t ON t.id = pt.tag_id
                WHERE t.name IN ({placeholders})
                {"AND p.author = ?" if author else ""}
                GROUP BY p.id
                HAVING COUNT(DISTINCT t.name) = ?
                ORDER BY p.id DESC
                LIMIT ?
            """
            params = list(tags)
            if author:
                params.append(author)
            params.extend([len(tags), limit])
        else:
            sql = f"""
                SELECT DISTINCT p.* FROM passages p
                JOIN passage_tags pt ON p.id = pt.passage_id
                JOIN tags t ON t.id = pt.tag_id
                WHERE t.name IN ({placeholders})
                {"AND p.author = ?" if author else ""}
                ORDER BY p.id DESC
                LIMIT ?
            """
            params = list(tags)
            if author:
                params.append(author)
            params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def random_by_tags(
        self, tags: list[str], limit: int = 2, mode: str = "any"
    ) -> list[dict]:
        """隨機取範本（避免每次錨定同一段）"""
        if not tags:
            return []

        placeholders = ",".join("?" * len(tags))

        if mode == "all":
            sql = f"""
                SELECT p.* FROM passages p
                JOIN passage_tags pt ON p.id = pt.passage_id
                JOIN tags t ON t.id = pt.tag_id
                WHERE t.name IN ({placeholders})
                GROUP BY p.id
                HAVING COUNT(DISTINCT t.name) = ?
                ORDER BY RANDOM()
                LIMIT ?
            """
            params = list(tags) + [len(tags), limit]
        else:
            sql = f"""
                SELECT DISTINCT p.* FROM passages p
                JOIN passage_tags pt ON p.id = pt.passage_id
                JOIN tags t ON t.id = pt.tag_id
                WHERE t.name IN ({placeholders})
                ORDER BY RANDOM()
                LIMIT ?
            """
            params = list(tags) + [limit]

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search_by_keyword(self, keyword: str, limit: int = 10) -> list[dict]:
        """在 text 和 style_note 中搜尋關鍵字"""
        rows = self._conn.execute(
            """SELECT * FROM passages
               WHERE text LIKE ? OR style_note LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_authors(self) -> list[dict]:
        """列出所有作家及其範本數"""
        rows = self._conn.execute(
            """SELECT author, COUNT(*) as count
               FROM passages GROUP BY author ORDER BY count DESC""",
        ).fetchall()
        return [dict(r) for r in rows]

    def list_by_author(self, author: str) -> list[dict]:
        """列出某作家的所有範本（摘要）"""
        rows = self._conn.execute(
            """SELECT id, author, work, chapter, char_count, style_note
               FROM passages WHERE author = ? ORDER BY id""",
            (author,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_by_tag(self, tag_name: str) -> list[dict]:
        """列出某 tag 下的所有範本（摘要）"""
        rows = self._conn.execute(
            """SELECT p.id, p.author, p.work, p.chapter, p.char_count, p.style_note
               FROM passages p
               JOIN passage_tags pt ON p.id = pt.passage_id
               JOIN tags t ON t.id = pt.tag_id
               WHERE t.name = ?
               ORDER BY p.id""",
            (tag_name,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Tag 查詢 ──

    def list_tags(self, category: str | None = None) -> list[dict]:
        """列出所有 tag 及其範本數量"""
        if category:
            rows = self._conn.execute(
                """SELECT t.name, t.category, COUNT(pt.passage_id) as count
                   FROM tags t
                   LEFT JOIN passage_tags pt ON t.id = pt.tag_id
                   WHERE t.category = ?
                   GROUP BY t.id
                   ORDER BY count DESC""",
                (category,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT t.name, t.category, COUNT(pt.passage_id) as count
                   FROM tags t
                   LEFT JOIN passage_tags pt ON t.id = pt.tag_id
                   GROUP BY t.id
                   ORDER BY count DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    # ── 管理 ──

    def remove_passage(self, passage_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM passages WHERE id = ?", (passage_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def add_tags_to_passage(self, passage_id: int, tag_names: list[str], category: str = "general"):
        self._link_tags(passage_id, tag_names, category)

    def remove_tag_from_passage(self, passage_id: int, tag_name: str):
        self._conn.execute(
            """DELETE FROM passage_tags WHERE passage_id = ? AND tag_id = (
                SELECT id FROM tags WHERE name = ?
            )""",
            (passage_id, tag_name),
        )
        self._conn.commit()

    # ── 統計 ──

    def get_stats(self) -> dict:
        passages = self._conn.execute("SELECT COUNT(*) as c FROM passages").fetchone()["c"]
        tags = self._conn.execute("SELECT COUNT(*) as c FROM tags").fetchone()["c"]
        authors = self._conn.execute("SELECT COUNT(DISTINCT author) as c FROM passages").fetchone()["c"]
        works = self._conn.execute("SELECT COUNT(DISTINCT work) as c FROM passages").fetchone()["c"]
        avg_chars = self._conn.execute("SELECT AVG(char_count) as c FROM passages").fetchone()["c"]
        return {
            "total_passages": passages,
            "total_tags": tags,
            "total_authors": authors,
            "total_works": works,
            "avg_char_count": round(avg_chars, 1) if avg_chars else 0,
        }

    def get_coverage(self) -> dict:
        """各 tag 的覆蓋度報告"""
        tags = self.list_tags()
        weak = [t for t in tags if t["count"] < 3]
        by_category = {}
        for t in tags:
            cat = t["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(t)
        return {
            "tags": tags,
            "weak_tags": weak,
            "by_category": by_category,
            "total_tags": len(tags),
            "weak_count": len(weak),
        }
