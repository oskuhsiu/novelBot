#!/usr/bin/env python3
"""
emotion_db.py — 情感記錄 SQLite 操作庫
取代 emotion_log.yaml，支援按需查詢以節省 context/token。

使用方式:
    from tools.emotion_db import EmotionDB
    db = EmotionDB("加爾德打工人")

    # 最近 N 章摘要
    recent = db.get_recent(10)

    # 單章完整記錄
    ch = db.get_chapter(57)

    # 新增/更新
    db.upsert_chapter(58, tension_score=60, primary_emotion="緊張/探索",
                      elements={"comedy":10,"tension":40,"warmth":15,"mystery":35},
                      note="...")

    # 統計
    stats = db.get_analysis()
    suggestions = db.get_suggestions()
"""

import json
import os
import sqlite3

from tools.lore_vector import get_project_folder

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class EmotionDB:
    """單一專案的情感記錄 SQLite 資料庫"""

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
            CREATE TABLE IF NOT EXISTS emotion_chapters (
                chapter_id INTEGER PRIMARY KEY,
                tension_score INTEGER DEFAULT 0,
                primary_emotion TEXT DEFAULT '',
                elements TEXT DEFAULT '{}',
                note TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS emotion_meta (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT '{}'
            );
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── 查詢 ──

    def get_chapter(self, chapter_id: int) -> dict | None:
        """取得單章完整記錄"""
        row = self._conn.execute(
            "SELECT * FROM emotion_chapters WHERE chapter_id = ?", (chapter_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "chapter_id": row["chapter_id"],
            "tension_score": row["tension_score"],
            "primary_emotion": row["primary_emotion"],
            "elements": json.loads(row["elements"]),
            "note": row["note"],
        }

    def get_recent(self, n: int = 5) -> list[dict]:
        """取得最近 N 章摘要（chapter_id, tension_score, primary_emotion）"""
        rows = self._conn.execute(
            "SELECT chapter_id, tension_score, primary_emotion FROM emotion_chapters ORDER BY chapter_id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            {
                "chapter_id": r["chapter_id"],
                "tension_score": r["tension_score"],
                "primary_emotion": r["primary_emotion"],
            }
            for r in rows
        ]

    def get_range(self, from_ch: int, to_ch: int) -> list[dict]:
        """取得章節範圍內的 tension 曲線"""
        rows = self._conn.execute(
            "SELECT chapter_id, tension_score, primary_emotion FROM emotion_chapters WHERE chapter_id BETWEEN ? AND ? ORDER BY chapter_id",
            (from_ch, to_ch),
        ).fetchall()
        return [
            {
                "chapter_id": r["chapter_id"],
                "tension_score": r["tension_score"],
                "primary_emotion": r["primary_emotion"],
            }
            for r in rows
        ]

    def get_analysis(self) -> dict:
        """計算統計數據"""
        rows = self._conn.execute(
            "SELECT tension_score FROM emotion_chapters ORDER BY chapter_id"
        ).fetchall()
        if not rows:
            return {"total_chapters": 0}

        scores = [r["tension_score"] for r in rows]
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        high = self._conn.execute(
            "SELECT chapter_id FROM emotion_chapters WHERE tension_score >= 60 ORDER BY chapter_id"
        ).fetchall()
        low = self._conn.execute(
            "SELECT chapter_id FROM emotion_chapters WHERE tension_score <= 30 ORDER BY chapter_id"
        ).fetchall()

        return {
            "total_chapters": len(scores),
            "average_tension": round(avg, 1),
            "max_tension": max(scores),
            "min_tension": min(scores),
            "standard_deviation": round(std_dev, 1),
            "high_tension_chapters": [r["chapter_id"] for r in high],
            "low_tension_chapters": [r["chapter_id"] for r in low],
        }

    def get_suggestions(self) -> list[str]:
        """取得緩衝建議（從 emotion_meta 讀取）"""
        row = self._conn.execute(
            "SELECT value FROM emotion_meta WHERE key = 'buffer_suggestions'"
        ).fetchone()
        if not row:
            return []
        return json.loads(row["value"])

    def get_consecutive(self) -> dict:
        """取得連續計數器"""
        row = self._conn.execute(
            "SELECT value FROM emotion_meta WHERE key = 'consecutive_tracking'"
        ).fetchone()
        if not row:
            return {}
        return json.loads(row["value"])

    # ── 寫入 ──

    def upsert_chapter(self, chapter_id: int, tension_score: int = 0,
                       primary_emotion: str = "", elements: dict | None = None,
                       note: str = ""):
        """新增或更新章節情感記錄"""
        self._conn.execute(
            """INSERT INTO emotion_chapters (chapter_id, tension_score, primary_emotion, elements, note)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(chapter_id) DO UPDATE SET
                 tension_score=excluded.tension_score, primary_emotion=excluded.primary_emotion,
                 elements=excluded.elements, note=excluded.note""",
            (chapter_id, tension_score, primary_emotion,
             json.dumps(elements or {}, ensure_ascii=False), note),
        )
        self._conn.commit()

    def set_suggestions(self, suggestions: list[str]):
        """更新緩衝建議"""
        self._conn.execute(
            "INSERT INTO emotion_meta (key, value) VALUES ('buffer_suggestions', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (json.dumps(suggestions, ensure_ascii=False),),
        )
        self._conn.commit()

    def set_consecutive(self, data: dict):
        """更新連續計數器"""
        self._conn.execute(
            "INSERT INTO emotion_meta (key, value) VALUES ('consecutive_tracking', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (json.dumps(data, ensure_ascii=False),),
        )
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM emotion_chapters").fetchone()[0]

    def stats(self) -> dict:
        total = self.count()
        if total == 0:
            return {"project": self.project_name, "total_chapters": 0}
        row = self._conn.execute(
            "SELECT MIN(chapter_id) as mn, MAX(chapter_id) as mx FROM emotion_chapters"
        ).fetchone()
        return {
            "project": self.project_name,
            "total_chapters": total,
            "chapter_range": f"{row['mn']}-{row['mx']}",
            "db_path": self.db_path,
        }
