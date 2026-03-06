# 資料查詢與遷移工具集

這套工具旨在解決 YAML 檔案隨著寫作進度過度膨脹，導致 LLM 讀寫時 Token 溢出與效能降低的問題。系統透過 ChromaDB（語意檢索）和 SQLite（結構化查詢）儲存資料，CLI 工具讓 LLM 按需查詢，避免全量載入。

---

## 核心工具一覽

### ChromaDB（語意向量檢索）
1. **`lore_vector.py`**: 核心模組（Python Library），提供 DB 連線與操作類別。
2. **`lore_query.py`**: 命令列查詢工具（CLI），語意搜尋長期記憶與章節摘要。
3. **`lore_update.py`**: 命令列寫入工具（CLI），新增/更新事件與章節記錄。

### SQLite（結構化按需查詢）
4. **`char_db.py`** / **`char_query.py`**: 角色資料庫。摘要列表 + 按需載入，取代全量讀取 `character_db.yaml`。
5. **`emotion_db.py`** / **`emotion_query.py`**: 情感記錄。最近 N 章 + 統計分析，取代全量讀取 `emotion_log.yaml`。
6. **`item_db.py`** / **`item_query.py`**: 物品/交易/嗶嗶帳本。按需查詢道具、餘額、未結清帳單，取代全量讀取 `item_compendium.yaml`。

### 遷移與清理
7. **`migrate_db.py`**: 統一遷移腳本（YAML → ChromaDB/SQLite），支援 `lore`, `char`, `emotion`, `item`, `all` 目標。
8. **`slim_progress.py`**: 清理 `narrative_progress.yaml` 中冗長的 `completed_chapters`。

---

## 1. lore_vector.py (核心函式庫)

這是單純供開發或寫作自動化腳本載入的 Python Library，本身沒有 CLI 指令功能。主要提供兩個資料表操作物件：

### 類別：`ChapterVector`
用來讀取、寫入、查詢已完成的章節大綱（ending_summary）。

**範例使用與情境：**
```python
from tools.lore_vector import ChapterVector

cv = ChapterVector("血與火")

# 情境：寫完新的一章（例如在 /nvExpand 最後的輕量維護）
cv.add_chapter(
    chapter_id=82,
    title="破曉前的奇襲",
    arc_id=6,
    subarc_id="6-4",
    word_count=2350,
    ending_summary="主角們潛入敵方基地，在破壞護盾產生器後與敵方守衛長發生激戰。",
    completed_at="2026-03-03"
)

# 情境：/nvDraft 在準備寫新章前，快速翻閱最近 3 章做前情提要
recent_summaries = cv.get_recent_chapters(n=3)

# 情境：忘記某個事件發生在哪一章，打模糊關鍵字問它
search_results = cv.query_chapters("破壞敵方護盾產生器", n=2)
```

### 類別：`LoreVector`
用來管理零碎的、累積的世界觀與設定事件，也就是以前塞在 `lore_bank.yaml` 裡的角色回憶、世界規則和伏筆。

**範例使用與情境：**
```python
from tools.lore_vector import LoreVector

lv = LoreVector("血與火")

# 情境：角色突然學會了新招式（這會由 /lorekeeper 雙寫紀錄）
lv.add_event(
    event_id="char_skill_01",
    document="林默在絕境中強行連結了二階伺服器，領悟了『能量衝擊』。",
    metadata={
        "category": "character_memory",
        "character_id": "CHAR_001",
        "chapter_ref": 82,   # 發生在 82 章
        "event_name": "領悟新技能",
        "status": "active"
    }
)

# 情境：/nvReview 要審查現在的寫作有沒有「吃書」，去搜尋世界規則
rules = lv.query("伺服器連結規則", n=3, where={"category": "world_fact"})

# 情境：重寫某章節（/nvRegen）時，把當初那章留下來的副作用/伏筆刪掉
lv.delete_by_filter({"chapter_ref": 82})
```

---

## 2. lore_query.py (LLM 查詢 CLI)

由於 LLM 在執行 markdown workflow (`/nvDraft`, `/nvReview` 等) 時無法直接呼叫 python class，因此我們提供此命令列包裝程式，讓 LLM 可以透過 `bash` 終端機進行資料庫檢索。

**使用說明：**

*   **查章節前情提要 (`chapters --recent`)**：
    通常在 `/nvDraft` 準備架構下一章時呼叫。
    ```bash
    # 列出「星雲劍仙」專案最近 5 章的結束摘要
    python tools/lore_query.py --proj "星雲劍仙" chapters --recent 5
    ```

*   **搜尋歷史情節 (`chapters [query]`)**：
    如果在寫作中必須確認過往的情節。
    ```bash
    # 在「血與火」專案中找關於「主角斷手」的章節
    python tools/lore_query.py --proj bnf chapters "主角斷手" --n 3
    ```

*   **搜尋已發生事實與伏筆 (`lore [query]`)**：
    常用於 `/nvReview` 檢查吃書，或是 `motivation_engine` 詢問角色動機。
    ```bash
    # 搜尋與「帝國皇帝」有關的所有世界設定或事件
    python tools/lore_query.py --proj bnf lore "帝國皇帝" --n 10
    
    # 搜尋角色 A 在過去發生過什麼事？
    python tools/lore_query.py --proj bnf lore "角色 A 遭遇" --category character_memory
    ```

*   **精確抓取單一章節全文摘要 (`chapter [id]`)**：
    ```bash
    python tools/lore_query.py --proj bnf chapter 15
    ```

*   **檢查與觀測資料庫健康度 (`stats`)**：
    ```bash
    python tools/lore_query.py --proj bnf stats
    ```

---

## 3. migrate_db.py (統一遷移腳本)

統一的 YAML → ChromaDB/SQLite 遷移工具，取代舊的 `lore_migrate.py`。

**使用方法：**
```bash
# 單一目標遷移
python tools/migrate_db.py --proj worker lore       # lore_bank.yaml → ChromaDB
python tools/migrate_db.py --proj worker char       # character_db.yaml → SQLite
python tools/migrate_db.py --proj worker emotion    # emotion_log.yaml → SQLite
python tools/migrate_db.py --proj worker item       # item_compendium.yaml → SQLite

# 全部遷移
python tools/migrate_db.py --proj worker all

# 預覽 / 驗證
python tools/migrate_db.py --proj worker item --dry-run
python tools/migrate_db.py --proj worker item --verify

# 批次遷移所有專案
python tools/migrate_db.py --all-projects all
```

---

## 4. char_query.py (角色資料庫 CLI)

按需查詢角色資料，避免全量載入 `character_db.yaml`（~15K tokens → ~6.5K tokens）。

```bash
# 摘要列表（低 token，開頭做一次）
python tools/char_query.py --proj worker list

# 按需載入完整角色資料（支援逗號分隔）
python tools/char_query.py --proj worker get CHAR_001,CHAR_MON_001

# 只取 current_state（更輕量）
python tools/char_query.py --proj worker get-state CHAR_001

# 更新角色狀態
python tools/char_query.py --proj worker update-state CHAR_001 --json '{"location":"酒館",...}'

# 更新單一欄位
python tools/char_query.py --proj worker update-field CHAR_001 location "紅月酒館"

# 查詢關係
python tools/char_query.py --proj worker relations CHAR_001
```

---

## 5. emotion_query.py (情感記錄 CLI)

按需查詢情感記錄，避免全量載入 `emotion_log.yaml`（~14K tokens → ~1.5K tokens）。

```bash
# 最近 N 章情感
python tools/emotion_query.py --proj worker recent --n 5

# 新增情感記錄
python tools/emotion_query.py --proj worker add 58 --tension 60 --emotion "緊張" --elements '{"tension":0.7}' --note "..."

# 統計分析
python tools/emotion_query.py --proj worker analysis

# 張力範圍圖
python tools/emotion_query.py --proj worker range 1 56
```

---

## 6. item_query.py (物品/交易/嗶嗶帳本 CLI)

按需查詢物品資料，避免全量載入 `item_compendium.yaml`（~4K tokens → ~200-400 tokens）。
transactions 和 bibi_account 是無限增長的追加式資料，SQLite 查詢的 token 量恆定。

```bash
# 道具摘要列表
python tools/item_query.py --proj worker list
python tools/item_query.py --proj worker list --category Evidence

# 完整道具資料（支援逗號分隔）
python tools/item_query.py --proj worker get SHELL_001,CONS_001

# 搜尋道具
python tools/item_query.py --proj worker search 飛劍

# 查某角色持有的道具
python tools/item_query.py --proj worker holder CHAR_001

# 更新道具
python tools/item_query.py --proj worker update CONS_001 --quantity 0 --status "已用完"

# 新增道具
python tools/item_query.py --proj worker add --json '{"id":"NEW_001","name":"...","category":"Tool",...}'

# 轉移持有者
python tools/item_query.py --proj worker transfer EVID_002 --holder CHAR_003 --note "移交公會"

# 當前餘額（最常用）
python tools/item_query.py --proj worker balance

# 最近 N 筆交易
python tools/item_query.py --proj worker tx-recent --n 5

# 新增交易
python tools/item_query.py --proj worker tx-add 57 --desc "委託報酬10銀" --balance "結餘約85銀"

# 章節範圍交易
python tools/item_query.py --proj worker tx-range 50 56

# 嗶嗶未結清帳單（最常用）
python tools/item_query.py --proj worker bibi-pending

# 嗶嗶全部帳本
python tools/item_query.py --proj worker bibi-all

# 新增嗶嗶帳本
python tools/item_query.py --proj worker bibi-add 57 --desc "全程掃描服務費" --status "待結清"

# 結清嗶嗶帳本
python tools/item_query.py --proj worker bibi-settle 3 --status "Ch.57已結清"

# 統計
python tools/item_query.py --proj worker stats
```

---

## 7. slim_progress.py (進度檔清理與轉換)

這是 ChromaDB 計畫的關鍵功能之一。過去我們依賴 `config/narrative_progress.yaml` 儲存進度，而它裡面的 `completed_chapters` 陣列隨時間會變得極度肥大（80章的小說可能這個陣列就有六七千行）。如果讓 LLM 在每次開寫前載入這個 YAML，Token 會被瞬間吃光，記憶會喪失。

這個工具負責將長篇的 `completed_chapters` **搬進** `ChapterVector` 向量庫中，並在搬移成功後，從 `narrative_progress.yaml` **徹底摘除** 歷史章節區塊，使其回歸真正的「進度追蹤」用途。

**使用方法：**
```bash
# 安全起見先查看會搬多少章節、新舊進度檔案的預估大小
python tools/slim_progress.py --proj "血與火" --dry-run

# 確認後執行切割寫入
python tools/slim_progress.py --proj "血與火"

# 如果硬碟滿了想清理所有專案積壓已久的進度檔案：
python tools/slim_progress.py --all
```

> **它的救濟機制**：
> 某些專案曾在壞掉的備份工作流中，導致 YAML 內部存在數個同名的 `completed_chapters:`。
> `yaml.safe_load` 讀到這個會崩潰無法啟動。此工具配有特殊的 Regex 解析邏輯，**能夠繞過嚴格的 YAML 檢查規範，暴力拯救被寫壞的章節陣列並成功遷入資料庫**。
