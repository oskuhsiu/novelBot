---
description: 歸檔過時記憶資料，保持工作檔案精簡
---

# /nvArchive - 歸檔過時記憶

將時間序列型記憶資料（章節記錄、過時 facts、已結束伏筆等）移至 `memory/archive/`，與 `/nvMaint` 互補。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=gou1` |
| `keep` | ❌ | 保留最近 N 章的記錄（預設 10） | `keep=5` |
| `dry` | ❌ | 預覽模式，只列出歸檔候選不執行（預設 false） | `dry=true` |

## 使用範例

```
/nvArchive proj=gou1
/nvArchive proj=gou1 keep=5
/nvArchive proj=gou1 dry=true
```

## 執行步驟

### Step 1: 讀取專案狀態
// turbo
讀取 `config/narrative_progress.yaml` 取得當前章節號（`progress.current_chapter`），計算歸檔臨界線：

```
archive_cutoff = current_chapter - keep
```

同時讀取以下資料：
- ChromaDB `chapters` collection（用來對照過時章節）
- 情感記錄（SQLite）：
  ```bash
  .venv/bin/python tools/emotion_query.py --proj {proj} recent --n 50
  ```
- ChromaDB `lore_bank` collection（`world_fact`, `foreshadowing` 等）

### Step 2: 掃描歸檔候選

依照以下規則建立歸檔候選清單：

#### 2a. `completed_chapters` (ChromaDB)
- **注意**：`completed_chapters` 已移至 ChromaDB 管理，不再存於 `narrative_progress.yaml`。
- **規則**：若有特定的歸檔需求（通常向量資料庫不需要主動歸檔），可執行自訂的 ChromaDB 清理指令。預設跳過此步驟。

#### 2b. `emotion_log`（SQLite）
情感記錄已遷移至 SQLite，資料永久保存不需歸檔（SQLite 查詢不影響 context）。
此步驟跳過。

#### 2c. ChromaDB `lore_bank` — `facts`
- **規則**：AI 逐條審閱，將以下類型標記為「過時」：
  1. **數值/狀態型 facts**：穩健值、碎片能量、位置、庫存等數值，且 `source` 章節 ≤ `archive_cutoff`，且已有更新版本（同類型但更近章節）
  2. **已被取代的 facts**：同系列 FACT 中較舊者
  3. **情境已失效的 facts**：所述場所/設施已毀
- **不歸檔**：世界觀核心規則、傳承機制、種族設定、角色核心能力等永久性知識
- **操作**：使用 `.venv/bin/python tools/lore_update.py --proj {proj} delete --id {id}` 從 ChromaDB 刪除

> [!IMPORTANT]
> Facts 歸檔需要 AI 理解內容語義，不能單純按章節號批量移動。每條 fact 需判斷：「如果今天寫新章節，這條 fact 還有參考價值嗎？」

#### 2d. ChromaDB `lore_bank` — `foreshadowing`
- **規則**：
  - `status: "resolved"` 或 `"closed"` → **自動從 ChromaDB 刪除**
  - `status: "open"` 但 `planted_chapter` ≤ `archive_cutoff` 且無近期更新 → **標記為候選**，在報告中列出供使用者確認

#### 2e. ChromaDB `lore_bank` — `world_changes`
- **規則**：`chapter` ≤ `archive_cutoff` 的項目從 ChromaDB 刪除

### Step 3: 預覽報告（dry=true 時到此為止）
// turbo
輸出歸檔候選清單：

```
📦 nvArchive 預覽報告
─────────────────────────
🔖 歸檔臨界線：Ch.XXX（保留最近 N 章）

📄 narrative_progress: XX 章待歸檔（Ch.1 ~ Ch.XX）
📄 emotion_log: XX 條待歸檔
📄 ChromaDB lore facts: XX 條待歸檔（列出 ID 與摘要）
📄 foreshadowing:
  - 自動歸檔（resolved）: XX 條
  - 候選確認（open 但過早）: XX 條（列出 ID）
📄 world_changes: XX 章待歸檔
```

若 `dry=true`，輸出報告後結束。

### Step 4: 執行歸檔

> [!CAUTION]
> 執行前先備份原檔（複製為 `.bak`），避免意外損失。

對每個檔案執行：
1. 將歸檔項目 **append** 到對應的 archive 檔案尾端
2. 從原檔中 **移除** 已歸檔的項目
3. 確認原檔 YAML 格式正確

執行順序：
```
1. (emotion_log 已在 SQLite，跳過歸檔)
2. ChromaDB lore facts → 刪除過時記錄
3. ChromaDB lore foreshadowing → 刪除已關閉記錄
4. ChromaDB lore world_changes → 刪除過時記錄
```

### Step 5: 更新索引
// turbo
在 `memory/archive/archive_index.yaml` 新增歸檔批次記錄：

```yaml
archive_batches:
  - date: "YYYY-MM-DD"
    cutoff_chapter: XX
    archived:
      emotion_log: (SQLite, skipped)
      lore_deleted: XX entries
      foreshadowing: XX entries
      world_changes: XX entries
```

### Step 6: 輸出歸檔摘要
// turbo
顯示最終報告：

```
✅ nvArchive 完成
─────────────────────────
📦 歸檔臨界線：Ch.XXX

已歸檔：
  📄 emotion_log: (SQLite, 不需歸檔)
  📄 ChromaDB lore facts: XX 條已刪除
  📄 ChromaDB foreshadowing: XX 條已刪除
  📄 ChromaDB world_changes: XX 條已刪除

原檔保留：
  📄 emotion_log: (SQLite, 全量保存)
  📄 ChromaDB lore facts: XX 條（永久 + 近期）
  📄 foreshadowing: XX 條 open
  📄 world_changes: 最近 N 章

⚠️  跳過的 foreshadowing（需手動確認）: XX 條
```

## 注意事項

1. **備份**：執行前自動建立 `.bak` 備份
2. **冪等性**：重複執行不會重複歸檔（已在 archive 的不會再移）
3. **與 nvMaint 的關係**：
   - `nvMaint` Step 9 處理**條件型歸檔**（角色死亡/物品消耗/勢力滅亡）
   - `nvArchive` 處理**時間型瘦身**（舊章節記錄、過時數值、已結束伏筆）
   - 建議先跑 `nvMaint` 再跑 `nvArchive`
4. **Facts 判斷準則**：寧可多留，不可誤刪。不確定是否過時的 fact 保留在原檔
