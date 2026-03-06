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

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，保護主 context 不被大量記憶檔案讀寫消耗。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 讀取 `projects/project_registry.yaml`，解析 `proj` 參數 → 取得專案資料夾名稱
3. 組合路徑：`PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`
3. 驗證參數（`keep` 預設 10，`dry` 預設 false）
4. 判斷執行模式：
   - **自動觸發（如從 nvMaint 後自動呼叫）**：`run_in_background: true`
   - **用戶手動執行 / dry=true 預覽**：`run_in_background: false`
5. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `model`: `haiku`
   - `run_in_background`: 依上述判斷
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
6. 接收並顯示 sub-agent 回傳的歸檔報告

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將 `{{PROJECT_DIR}}`、`{{PROJ}}`、`{{KEEP}}`、`{{DRY}}` 替換為實際值。

````
你是小說記憶歸檔助手。請對專案執行時間型記憶瘦身。

## 任務參數
- 專案路徑：{{PROJECT_DIR}}
- 專案名稱：{{PROJ}}
- 保留最近章數：{{KEEP}}
- 預覽模式：{{DRY}}（true 只列出候選不執行，false 實際執行）
- 專案根目錄：{{REPO_ROOT}}

## Step 1: 讀取專案狀態

讀取 `{{PROJECT_DIR}}/config/narrative_progress.yaml` 取得 `progress.current_chapter`，計算歸檔臨界線：
```
archive_cutoff = current_chapter - {{KEEP}}
```

同時讀取：
- 情感記錄（SQLite）— 使用 CLI 查詢：
  ```bash
  cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} recent --n 50
  ```
- ChromaDB `lore_bank` collection（world_fact, foreshadowing 等）

ChromaDB 查詢用 Bash：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_query.py --proj {{PROJ}} lore "chapter" --n 50
```

## Step 2: 掃描歸檔候選

### 2a. completed_chapters (ChromaDB)
已移至 ChromaDB 管理，預設跳過。

### 2b. emotion_log（SQLite）
情感記錄已遷移至 SQLite，資料永久保存不需歸檔（SQLite 查詢不影響 context）。
此步驟跳過。

### 2c. ChromaDB lore_bank — facts
規則：AI 逐條審閱，將以下類型標記為「過時」：
1. 數值/狀態型 facts：source 章節 ≤ archive_cutoff 且已有更新版本
2. 已被取代的 facts：同系列中較舊者
3. 情境已失效的 facts：所述場所/設施已毀
不歸檔：世界觀核心規則、傳承機制、種族設定、角色核心能力等永久性知識

操作：使用 `cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} delete --id {id}` 從 ChromaDB 刪除過時記錄

**重要**：Facts 歸檔需要理解內容語義，不能單純按章節號批量移動。每條 fact 需判斷：「如果今天寫新章節，這條 fact 還有參考價值嗎？」

### 2d. ChromaDB lore_bank — foreshadowing
規則：
- status: "resolved" 或 "closed" → 自動從 ChromaDB 刪除
- status: "open" 但 planted_chapter ≤ archive_cutoff 且無近期更新 → 標記為候選，在報告中列出

### 2e. ChromaDB lore_bank — world_changes
規則：chapter ≤ archive_cutoff 的項目從 ChromaDB 刪除

## Step 3: 預覽報告

輸出歸檔候選清單：

```
📦 nvArchive 預覽報告
─────────────────────────
🔖 歸檔臨界線：Ch.XXX（保留最近 {{KEEP}} 章）

📄 emotion_log: (SQLite, 不需歸檔)
📄 ChromaDB lore facts: XX 條待歸檔（列出 ID 與摘要）
📄 foreshadowing:
  - 自動歸檔（resolved）: XX 條
  - 候選確認（open 但過早）: XX 條（列出 ID）
📄 world_changes: XX 章待歸檔
```

若 {{DRY}} == true，輸出報告後結束。

## Step 4: 執行歸檔（dry=false 時）

執行前先備份原檔（複製為 .bak）。

對每個檔案執行：
1. 將歸檔項目 append 到對應的 archive 檔案尾端
2. 從原檔中移除已歸檔的項目
3. 確認原檔 YAML 格式正確

執行順序：
1. (emotion_log 已在 SQLite，跳過歸檔)
2. ChromaDB lore facts → 刪除過時記錄
3. ChromaDB lore foreshadowing → 刪除已關閉記錄
4. ChromaDB lore world_changes → 刪除過時記錄

## Step 5: 更新索引

在 `{{PROJECT_DIR}}/memory/archive/archive_index.yaml` 新增歸檔批次記錄：
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

## Step 6: 輸出歸檔摘要

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
  📄 world_changes: 最近 {{KEEP}} 章

⚠️  跳過的 foreshadowing（需手動確認）: XX 條
```

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有操作直接用 Read、Edit、Write、Bash 等工具完成
2. ChromaDB 操作使用 Bash 執行 python 腳本
3. 所有檔案路徑使用絕對路徑
4. 寧可多留，不可誤刪。不確定是否過時的 fact 保留在原檔
5. 備份：執行前自動建立 .bak 備份
6. 冪等性：重複執行不會重複歸檔
````

## 注意事項

1. **備份**：執行前自動建立 `.bak` 備份
2. **冪等性**：重複執行不會重複歸檔（已在 archive 的不會再移）
3. **與 nvMaint 的關係**：
   - `nvMaint` Step 9 處理**條件型歸檔**（角色死亡/物品消耗/勢力滅亡）
   - `nvArchive` 處理**時間型瘦身**（舊章節記錄、過時數值、已結束伏筆）
   - 建議先跑 `nvMaint` 再跑 `nvArchive`
4. **Facts 判斷準則**：寧可多留，不可誤刪。不確定是否過時的 fact 保留在原檔
