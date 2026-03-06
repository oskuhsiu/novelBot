# 📚 lore_query.py & lore_update.py 參數使用說明

這是一份針對 `ChromaDB` 連接與操作介面的最新、最完整的參數使用說明指南，確保所有 AI 替身在接下來的工作流程中不會再弄錯或搞混這些參數的順序與定義。

---

## 🔍 `lore_query.py` (資料查詢)

`lore_query.py` 負責查詢 Vector DB 中的短期/長期記憶。

**注意：參數必須置於子命令（例如 `lore` 或 `chapters`）的後面，不可放在前面。**

### 1. 搜尋 Lore (事件、設定)
`python tools/lore_query.py --proj <專案> lore [OPTIONS] <查詢內容>`

**參數說明：**
- `<查詢內容>` (必填): 搜尋的自然語言字串。
- `--n N` (選填): 返回的數量，預設 `5`。
- `--category CATEGORY` (選填): 透過 category 過濾，例如 `character_memory`, `global_memory`。

**正確範例：**
```bash
python tools/lore_query.py --proj bnf lore "主角的念力進化"
python tools/lore_query.py --proj bnf lore "伏筆" --n 10
python tools/lore_query.py --proj bnf lore "角色關係" --category character_memory
```

### 2. 獲取特定章節上下文
`python tools/lore_query.py --proj <專案> chapter <章節號>`

**參數說明：**
- `<章節號>` (必填): 章節數字 ID。

**正確範例：**
```bash
python tools/lore_query.py --proj bnf chapter 81
```

### 3. 搜尋/列出多個章節
`python tools/lore_query.py --proj <專案> chapters [OPTIONS] [<查詢內容>]`

**參數說明：**
- `<查詢內容>` (選填): 搜尋章節內容的關鍵字。如果不填則會列出未來的 N 章。
- `--recent N` (選填): 列出最近的 `N` 章（適合快速建立前情提要）。如果不帶 `<查詢內容>`，預設即為 `recent` 模式。
- `--n N` (選填): 返回的數量，如果帶有查詢內容的話預設為 `5`。

**正確範例：**
```bash
# 列出最近 5 章 (最常用)
python tools/lore_query.py --proj bnf chapters --recent 5

# 語意搜尋章節
python tools/lore_query.py --proj bnf chapters "突襲敵營" --n 3
```

---

## 📝 `lore_update.py` (資料寫入與更新)

`lore_update.py` 負責將新的內容與記憶寫入 Vector DB。

**注意：與 query 一樣，所有參數必須接在子指令（如 `chapter` 或 `event`）之後！**

### 1. 新增或更新章節 (Chapter)
寫完新章節，將其寫入記憶庫以供未來檢索。

**正確指令格式：**
`python tools/lore_update.py chapter --proj <專案> --id <章節號> [OPTIONS]`

**必填參數：**
- `--proj PROJ` : 專案代號 (如 `bnf`)
- `--id ID` : 章節號 (例如 `82`)
- `--title TITLE` : 章節名稱
- `--arc ARC` : 歸屬大卷號碼
- `--subarc SUBARC` : 歸屬 SubArc 代號 (如 `6-3`)
- `--words WORDS` : 字數整數
- `--summary SUMMARY` : 章節完整的前情提要摘要

**選填參數：**
- `--date DATE` : 此章節的撰寫/發生時間 (例如 `2026-03-03`)

**正確範例：**
```bash
python tools/lore_update.py chapter --proj bnf --id 82 --title "滿載而歸" --arc 6 --subarc 6-3 --words 4692 --summary "章節摘要" --date "2026-03-03"
```

### 2. 新增或更新事件 Lore (Event)
將特殊的角色記憶、伏筆或是世界觀變更寫入記憶庫。

**正確指令格式：**
`python tools/lore_update.py event --proj <專案> --id <事件ID> [OPTIONS]`

**必填參數：**
- `--proj PROJ` : 專案代號
- `--id ID` : 全域唯一的事件 ID (建議命名法：如 `global_002_ch82`)
- `--cat CAT` : 分類屬性 (必須有，如 `global_memory`, `character_memory`, `foreshadowing`)
- `--name NAME` : 事件的標題/名稱
- `--doc DOC` : 事件/伏筆/設定的詳細內容描述字串

**選填參數：**
- `--ch CH` : 若有直接相關的章節號請帶入 (例如 `82`)
- `--char CHAR` : 有關的專屬角色 ID (例如 `CHAR_001`)
- `--status STATUS` : 狀態，預設為 `active`，如完結可改為 `resolved`

**正確範例：**
```bash
python tools/lore_update.py event --proj bnf --id "global_002_ch82" --cat "global_memory" --ch 82 --name "秦書白發現晶片" --status "active" --doc "秦書白拆解繳獲裝備發現特勤處後門晶片"
```
