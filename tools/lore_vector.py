#!/usr/bin/env python3
"""
lore_vector.py — ChromaDB 向量資料庫操作庫
用於 lore_bank 和 chapters 的語意搜尋與 CRUD 操作

使用方式:
    # === lore_bank ===
    from tools.lore_vector import LoreVector
    lv = LoreVector("血與火")
    lv.add_event("global_001", "林默學會念力干擾", {
        "category": "character_memory",
        "character_id": "CHAR_001",
        "chapter_ref": 9,
        "event_name": "戰鬥進化",
        "status": "active",
    })
    results = lv.query("林默的念力進化", n=5)

    # === chapters ===
    from tools.lore_vector import ChapterVector
    cv = ChapterVector("血與火")
    cv.add_chapter(
        chapter_id=81, title="血洗掠奪者", arc_id=6, subarc_id="6-3",
        word_count=2400, ending_summary="707連武裝車隊...",
        completed_at="2026-02-28",
    )
    ch = cv.get_chapter(81)
    recent = cv.get_recent_chapters(n=5)
    results = cv.query_chapters("主角突襲敵方營地", n=3)
"""

import os
import chromadb
from chromadb.config import Settings

CHROMA_SETTINGS = Settings(anonymized_telemetry=False)

# 預設的專案根目錄
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


class LoreVector:
    """
    單一專案的 lore_bank 向量資料庫操作類
    負責管理 ChromaDB 中的 'lore_bank' collection，這裡儲存的是
    從 YAML 解析出來的各類設定與事件紀錄（如 world_facts, events, mysteries）。
    
    【設計理念】
    傳統的 lore_bank.yaml 會隨時間膨脹到難以讀取。
    轉換為向量儲存後，允許通過語意進行「情境提要」的檢索，
    不再需要依賴寫死的大型 YAML 結構。
    """

    def __init__(self, project_name: str, collection_name: str = "lore_bank"):
        """
        初始化向量資料庫連線
        
        底層採用 ChromaDB 的 PersistentClient，資料以 SQLite 儲存在本機。

        Args:
            project_name: 專案資料夾名稱（如 "血與火"）
            collection_name: collection 名稱（預設 "lore_bank"）
        """
        self.project_name = project_name
        self.db_path = os.path.join(PROJECT_ROOT, project_name, "memory", "vector_db")
        os.makedirs(self.db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.db_path, settings=CHROMA_SETTINGS)
        # 設定 metadata 啟用 cosine 相似度 (預設為 l2 norm)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_event(self, event_id: str, document: str, metadata: dict | None = None):
        """
        新增或更新單筆事件/設定紀錄到向量庫
        這通常會在 nvMaint 或 lorekeeper 執行雙寫機制時呼叫。

        Args:
            event_id: 唯一 ID（如 "charMem_CHAR001_ch09_001", "global_001"）
            document: 事件描述文字（將被向量化，用於語意搜尋）
            metadata: 附加 metadata。必須包含 'category', 'event_name', 'status' 等核心欄位，
                      這使得查詢時除了語意，還能通過 filter 過濾。
        """
        meta = {"project": self.project_name}
        if metadata:
            # ChromaDB metadata 的限制：只支援 str, int, float, bool
            # 不支援 list, dict 等巢狀結構，所以遇到這類資料需扁平化處理或跳過
            for k, v in metadata.items():
                if v is not None:
                    meta[k] = v

        self.collection.upsert(
            ids=[event_id],
            documents=[document],
            metadatas=[meta],
        )

    def add_events_batch(self, events: list[dict]):
        """
        批次新增多筆事件/設定。
        主要由 lore_migrate.py 呼叫，用於初次將龐大的 lore_bank.yaml 遷移至資料庫。

        Args:
            events: 包含字典的列表，格式為: [{"id": str, "document": str, "metadata": dict}]
        """
        if not events:
            return

        ids = [e["id"] for e in events]
        documents = [e["document"] for e in events]
        metadatas = []
        for e in events:
            meta = {"project": self.project_name}
            if e.get("metadata"):
                for k, v in e["metadata"].items():
                    if v is not None:  # 過濾掉 null 以防 ChromaDB 報錯
                        meta[k] = v
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, text: str, n: int = 5, where: dict | None = None) -> list[dict]:
        """
        語意查詢 (Semantic Query)。
        這是整個系統與 ChromaDB 互動最核心的功能，當 LLM (如 nvDraft, nvReview) 
        需要回憶過去劇情時，會使用此方法。

        Args:
            text: 查詢文字（如 "林默的念力進化過程"）
            n: 返回的最大相關結果數量
            where: (可選) metadata 過濾器，如 {"category": "world_fact"}

        Returns:
            符合查詢結果的清單，附加 distance 欄位代表相似度距離 (越小越相似)
        """
        # 防止 n 超過實際集合大小導致 ChromaDB 報錯
        kwargs = {
            "query_texts": [text],
            "n_results": min(n, self.collection.count()) if self.collection.count() > 0 else n,
        }
        if where:
            kwargs["where"] = where

        if self.collection.count() == 0:
            return []

        results = self.collection.query(**kwargs)

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return output

    def delete_event(self, event_id: str):
        """刪除指定 ID 的記錄"""
        self.collection.delete(ids=[event_id])

    def delete_by_filter(self, where: dict):
        """
        根據 metadata 過濾器批次刪除記錄。
        重要用途：nvRegen 重寫章節時，用來清理掉當初該章節生成的舊 lore 資料，
        避免新舊設定矛盾 (例如 where={"chapter_ref": 80})。
        """
        self.collection.delete(where=where)

    def get_event(self, event_id: str) -> dict | None:
        """精確取得指定 ID 的單筆記錄"""
        result = self.collection.get(ids=[event_id])
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "document": result["documents"][0],
                "metadata": result["metadatas"][0],
            }
        return None

    def list_all(self, where: dict | None = None, limit: int = 100) -> list[dict]:
        """
        列出所有/符合條件的記錄
        通常僅供開發/除錯驗證使用，不在正常 AI 寫作流程被呼叫。
        """
        kwargs = {"limit": limit}
        if where:
            kwargs["where"] = where

        results = self.collection.get(**kwargs)

        output = []
        for i in range(len(results["ids"])):
            output.append({
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
            })
        return output

    def count(self) -> int:
        """返回記錄總數"""
        return self.collection.count()

    def stats(self) -> dict:
        """返回統計資訊"""
        total = self.count()
        all_items = self.list_all(limit=10000) if total > 0 else []

        categories = {}
        chapters = set()
        for item in all_items:
            cat = item["metadata"].get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            ch = item["metadata"].get("chapter_ref")
            if ch is not None:
                chapters.add(ch)

        return {
            "project": self.project_name,
            "total_records": total,
            "categories": categories,
            "chapter_range": f"{min(chapters)}-{max(chapters)}" if chapters else "N/A",
            "db_path": self.db_path,
        }


# ============================================================
# lore_bank Schema 允許的 category 值
# ============================================================
LORE_CATEGORIES = {
    "global_memory",        # 全局大事件
    "character_memory",     # 角色記憶
    "mystery",              # 懸念/謎團
    "event",                # 事件記錄
    "world_fact",           # 世界設定
    "relationship_change",  # 關係變化
    "foreshadowing",        # 伏筆
    "item_status",          # 物品追蹤
    "permanent_change",     # 永久改變
}

# lore_bank 必填 metadata 欄位
LORE_REQUIRED_META = {"category", "event_name", "status"}

# lore_bank 允許的 status 值
LORE_STATUSES = {"active", "permanent", "open", "closed", "archived"}


class ChapterVector:
    """
    已完成章節向量資料庫操作類
    負責管理 ChromaDB 中的 'chapters' collection。
    
    【設計理念】
    過去所有的章節 completed_chapters 都存放在 narrative_progress.yaml 中，
    導致 YAML 檔案過於龐大且難以進行語意檢索。
    改用向量資料庫後，可以大幅減少 YAML 體積，且允許 LLM 在創作時
    直接「語意搜尋」特定情節發生在哪一章。

    Schema（嚴格）:
        id:           "ch_{chapter_id}"    (string)  # 確保唯一性
        document:     ending_summary 全文   (string)  # 用於 ChromaDB 的 embedding 和語意搜尋
        metadata:
            # metadata 是為了後續可以進行精確過濾 (where 子句)
            chapter_id:   int   (必填)
            arc_id:       int   (必填)
            subarc_id:    str   (必填, 如 "A1_S3")
            title:        str   (必填)
            word_count:   int   (必填)
            completed_at: str   (必填, 如 "2026-02-28")
            project:      str   (自動填入)
    """

    REQUIRED_FIELDS = {"chapter_id", "arc_id", "subarc_id", "title", "word_count", "completed_at"}

    def __init__(self, project_name: str):
        """
        初始化 ChapterVector 操作類別。
        
        Args:
            project_name: 專案名稱（作為資料夾路徑參考）
        """
        self.project_name = project_name
        self.db_path = os.path.join(PROJECT_ROOT, project_name, "memory", "vector_db")
        os.makedirs(self.db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.db_path, settings=CHROMA_SETTINGS)
        # 設定 cosine 相似度計算
        self.collection = self.client.get_or_create_collection(
            name="chapters",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chapter(
        self,
        chapter_id: int,
        title: str,
        arc_id: int,
        subarc_id: str,
        word_count: int,
        ending_summary: str,
        completed_at: str = "",
    ):
        """
        新增或更新一個已完成的章節。
        如果 chapter_id 已存在，upsert 邏輯會自動覆蓋舊資料（適用於 nvRegen 章節重寫）。

        Args:
            chapter_id:     章節編號
            title:          章節標題
            arc_id:         所屬卷 (大章節)
            subarc_id:      所屬 SubArc (次網，如 "A1_S3")
            word_count:     本章字數
            ending_summary: 章節結尾摘要 (本文將被向量化，供語意搜尋使用)
            completed_at:   完成日期字串 (如 "2026-02-28")
        """
        if not ending_summary:
            raise ValueError(f"ending_summary 不能為空 (chapter {chapter_id})")

        self.collection.upsert(
            ids=[f"ch_{chapter_id}"],
            documents=[ending_summary],
            metadatas=[{
                "chapter_id": chapter_id,
                "arc_id": arc_id,
                "subarc_id": str(subarc_id),
                "title": title,
                "word_count": word_count,
                "completed_at": completed_at or "",
                "project": self.project_name,
            }],
        )

    def add_chapters_batch(self, chapters: list[dict]):
        """
        批次新增/更新章節資料。主要用於 slim_progress.py 進行初次資料遷移時使用，
        比起跑迴圈單次加，可以大幅減少 I/O 時間。

        Args:
            chapters: 包含章節 dict 的 list。每個 dict 必須符合 schema。
        """
        if not chapters:
            return

        ids = []
        documents = []
        metadatas = []
        for ch in chapters:
            # 嚴格驗證必填欄位，防止產生髒資料
            missing = self.REQUIRED_FIELDS - set(ch.keys())
            if missing:
                raise ValueError(f"章節缺少必填欄位: {missing} (chapter {ch.get('chapter_id', '?')})")
            if not ch.get("ending_summary"):
                raise ValueError(f"ending_summary 不能為空 (chapter {ch['chapter_id']})")

            ids.append(f"ch_{ch['chapter_id']}")
            documents.append(ch["ending_summary"])
            metadatas.append({
                "chapter_id": ch["chapter_id"],
                "arc_id": ch["arc_id"],
                "subarc_id": str(ch["subarc_id"]),
                "title": ch["title"],
                "word_count": ch["word_count"],
                "completed_at": ch.get("completed_at", ""),
                "project": self.project_name,
            })

        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def get_chapter(self, chapter_id: int) -> dict | None:
        """
        精確取得某一章的完整資料。
        用於 nvDraft 等 workflow 需要精準調用上一章 summary 時。

        Args:
            chapter_id: 章節編號
            
        Returns:
            章節字典，若找不到回傳 None
        """
        result = self.collection.get(ids=[f"ch_{chapter_id}"])
        if result["ids"]:
            meta = result["metadatas"][0]
            return {
                "chapter_id": meta.get("chapter_id"),
                "title": meta.get("title"),
                "ending_summary": result["documents"][0],
                "arc_id": meta.get("arc_id"),
                "subarc_id": meta.get("subarc_id"),
                "word_count": meta.get("word_count"),
                "completed_at": meta.get("completed_at"),
            }
        return None

    def get_recent_chapters(self, n: int = 5) -> list[dict]:
        """
        取得最近 N 章的資料 (按 chapter_id 降序排列)。
        主要用於提供 LLM 最近寫作的「連貫性前情提要」。

        Args:
            n: 要取出的章數
            
        Returns:
            以 chapter_id 降序排列的章節清單
        """
        total = self.collection.count()
        if total == 0:
            return []

        # ChromaDB 預設的 get 無法直接按欄位 sort，所以全取出來在 memory 中 sort
        # 由於章節數量通常在幾百章以內，記憶體排序開銷極低
        all_items = self.collection.get(limit=total)
        results = []
        for i in range(len(all_items["ids"])):
            meta = all_items["metadatas"][i]
            results.append({
                "chapter_id": meta.get("chapter_id", 0),
                "title": meta.get("title", ""),
                "ending_summary": all_items["documents"][i],
                "arc_id": meta.get("arc_id"),
                "subarc_id": meta.get("subarc_id"),
                "word_count": meta.get("word_count"),
                "completed_at": meta.get("completed_at"),
            })

        results.sort(key=lambda x: x["chapter_id"], reverse=True)
        return results[:n]

    def query_chapters(self, text: str, n: int = 5, where: dict | None = None) -> list[dict]:
        """
        語意搜尋章節（計算 ending_summary 與查詢字串的 Cosine 相似度）。
        當需要確認「主角在哪一章殺了某個反派」或「某個道具在哪一章獲得」時非常有用。

        Args:
            text: 自然語言查詢文字 ("主角在沙漠中戰鬥")
            n: 返回數量
            where: (可選) metadata 過濾器，如 {"subarc_id": "A1_S3"}

        Returns:
            包含 similarity distance 評分的章節清單
        """
        total = self.collection.count()
        if total == 0:
            return []

        kwargs = {"query_texts": [text], "n_results": min(n, total)}
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)
        output = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            output.append({
                "chapter_id": meta.get("chapter_id"),
                "title": meta.get("title"),
                "ending_summary": results["documents"][0][i],
                "arc_id": meta.get("arc_id"),
                "subarc_id": meta.get("subarc_id"),
                "word_count": meta.get("word_count"),
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return output

    def count(self) -> int:
        """返回已入庫的章節總數"""
        return self.collection.count()

    def stats(self) -> dict:
        """返回統計資訊"""
        total = self.count()
        if total == 0:
            return {"project": self.project_name, "total_chapters": 0, "db_path": self.db_path}

        all_items = self.collection.get(limit=total)
        arcs = {}
        ch_ids = []
        total_words = 0
        for i in range(len(all_items["ids"])):
            meta = all_items["metadatas"][i]
            aid = meta.get("arc_id", 0)
            arcs[aid] = arcs.get(aid, 0) + 1
            ch_ids.append(meta.get("chapter_id", 0))
            total_words += meta.get("word_count", 0)

        return {
            "project": self.project_name,
            "total_chapters": total,
            "chapter_range": f"{min(ch_ids)}-{max(ch_ids)}",
            "arcs": arcs,
            "total_words": total_words,
            "db_path": self.db_path,
        }


def get_project_folder(proj_alias: str) -> str | None:
    """
    從 project_registry.yaml 解析專案別名

    Args:
        proj_alias: 專案別名或資料夾名

    Returns:
        實際專案資料夾名，或 None
    """
    import yaml

    registry_path = os.path.join(PROJECT_ROOT, "project_registry.yaml")
    if not os.path.exists(registry_path):
        # 如果沒有 registry，直接當作資料夾名
        proj_dir = os.path.join(PROJECT_ROOT, proj_alias)
        return proj_alias if os.path.isdir(proj_dir) else None

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    # 先檢查是不是別名
    projects = registry.get("projects", {})
    if proj_alias in projects:
        return projects[proj_alias]

    # 再檢查是不是直接的資料夾名
    proj_dir = os.path.join(PROJECT_ROOT, proj_alias)
    if os.path.isdir(proj_dir):
        return proj_alias

    # 最後檢查是不是資料夾名的值
    for alias, folder in projects.items():
        if folder == proj_alias:
            return folder

    return None
