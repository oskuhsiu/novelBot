---
description: 維護記憶與設定檔同步
---

# /nvMaint - 維護記憶

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `mode` | ❌ | 維護模式 | `mode=full/light` |

### mode 參數說明
- `full`：完整維護所有設定檔（預設）
- `light`：僅 Steps 1-4

## 使用範例

```
/nvMaint proj=霓虹劍仙
/nvMaint proj=霓虹劍仙 mode=light
```

## 執行步驟

### Step 1: 讀取最新章節
// turbo
讀取 `output/chapters/` 中最新完成的章節

### Step 2: 更新長期記憶（必執行）
寫入 ChromaDB `lore_bank` collection（不再寫入 `lore_bank.yaml`）。

```yaml
更新項目:
  - events: 新增本章發生的事件
  - relationship_changes: 記錄關係變動
  - open_foreshadowing: 追蹤新埋設的伏筆
  - closed_foreshadowing: 標記已揭露的伏筆
  - world_facts: 新發現的世界規則
  - item_status: 物品狀態變動
  - permanent_changes: 永久性改變

寫入 ChromaDB（與 YAML 同步）:
  - 對每筆新記錄，執行:
    .venv/bin/python tools/lore_update.py --proj {proj} event --id "{id}" --cat "{category}" --ch {chapter} --name "{name}" --status "{status}" --doc "{document}"
    # --char "{char_id}" 為選填，僅在事件有明確關聯角色時才加上
```

> [!TIP]
> 允許的 category: `global_memory`, `character_memory`, `mystery`, `event`, `world_fact`, `relationship_change`, `foreshadowing`, `item_status`, `permanent_change`
> 允許的 status: `active`, `permanent`, `open`, `closed`, `archived`

### Step 2b: 更新情感記錄（必執行）

讀取 `.agent/skills/memory/emotional_wave_analyzer/SKILL.md` 並遵循其指令分析本章情感。

```bash
.venv/bin/python tools/emotion_query.py --proj {proj} add {chapter_id} --tension {score} --emotion "{primary_emotion}" --elements '{...}' --note "..."
.venv/bin/python tools/emotion_query.py --proj {proj} recent --n 5
# 若超過閾值：
.venv/bin/python tools/emotion_query.py --proj {proj} set-suggestions --json '[...]'
.venv/bin/python tools/emotion_query.py --proj {proj} set-consecutive --json '{...}'
```

### Step 3: 更新敘事進度（必執行）
更新 `config/narrative_progress.yaml`：

```yaml
更新項目:
  - progress.current_chapter: +1
  - progress.words_written: 使用 `word_counter` 技能計算字數並累加（參見 `.agent/skills/execution/word_counter/SKILL.md`）
  - progress.last_updated: 今日日期
  
  **【動態節拍 (Beats) 推進】**
  - 將当前的 `current_beat` 清空。
  - 檢查 `upcoming_beats` 陣列：
    - 若陣列有剩餘項目：彈出 (pop) 第一項，存入 `current_beat`。
    - 若陣列為空：將當前 SubArc 移入 `completed_subarcs`，並將 `active_subarcs` 推進到下一個 SubArc。

  **【生成章節摘要】**
  讀取 `.agent/skills/memory/chapter_summarizer/SKILL.md` 並遵循其指令，對本章全文生成結構化摘要（目標：原文 15-20% 字數）。

  **【寫入章節到 ChromaDB】**
  - 使用 `.venv/bin/python tools/lore_update.py --proj {proj} chapter ...` 將已完成章節寫入向量資料庫。
  - Schema 欄位：chapter_id, title, arc_id, subarc_id, word_count, chapter_summary, completed_at
  - 注意：`chapter_summary` 是由 chapter_summarizer 產生的結構化摘要，非舊版的一句話 ending_summary。
  - 這些資料**不再存放於** `narrative_progress.yaml`。

> [!NOTE]
> `narrative_progress.yaml` 僅包含進度數據和章節節拍，不含 completed_chapters。
> 已完成章節資料存放於 ChromaDB `chapters` collection（位於 `memory/vector_db/`）。
> 讀取 ending_summary 請使用 `ChapterVector.get_chapter(chapter_id)` 或 `get_recent_chapters(n)`。
> 大綱結構存放於 `config/outline_index.yaml`，不可修改大綱檔案。
```


### Step 4: 更新角色資料庫（必執行）

使用 SQLite CLI 更新角色狀態：

```bash
# 讀取角色當前狀態
.venv/bin/python tools/char_query.py --proj {proj} get-state {CHAR_ID}
# 更新角色狀態
.venv/bin/python tools/char_query.py --proj {proj} update-state {CHAR_ID} --json '{"location":"...","health":"...","emotional_state":"...","inventory":[...],"active_goals":[...],"relationships":[...],"last_updated_chapter":N}'
# 更新關係
.venv/bin/python tools/char_query.py --proj {proj} update-rel {SOURCE_ID} {TARGET_ID} --surface "..." --hidden "..." --tension N
```

### Step 5: 更新世界地圖（mode=full）
更新 `config/world_atlas.yaml`：

```yaml
更新項目:
  新區域/地點（如有）:
    - 使用 `skill_world_builder` 擴展世界觀
    - 確保與現有地圖連接
    - 設定危險等級
    - 列出可獲取資源
    - 描述威脅類型
    
  已有地點:
    - 更新控制勢力
    - 更新資源狀態
```

### Step 6: 更新勢力登記（mode=full）
更新 `config/faction_registry.yaml`：

```yaml
更新項目:
  新勢力（如有）:
    - 使用 `skill_faction_forge` 創建完整勢力定義
    - 設定成員列表
    - 初始化外交關係
    
  已有勢力:
    - 更新成員變動
    - 更新領土變動
    - 更新外交狀態
    
  外交矩陣:
    - 關係值調整
    - 新增關係記錄
```

### Step 6b: 更新勢力緊張度（mode=full）
使用 `skill_power_dynamic_updater` 自動分析本章事件對勢力關係的影響：
- 計算緊張度變化
- 檢查閾值觸發
- 更新 `faction_registry.yaml` 中的 `tension` 值

### Step 7: 更新力量體系（mode=full）
更新 `config/power_system.yaml`：

```yaml
更新項目:
  新能力（如有）:
    - 使用 `skill_power_architect` 擴展力量體系
    - 確保與現有體系郏輯自洽
    - 角色新獲得的技能
    
  新物品類別（如有）:
    - buff/道具
    - 建造圖紙
```

### Step 8: 更新物品目錄（mode=full）

使用 SQLite CLI 更新物品資料庫。新物品讀取 `.agent/skills/foundation/item_smith/SKILL.md` 設計後寫入：

```bash
# 新增道具
.venv/bin/python tools/item_query.py --proj {proj} add --json '{"id":"...","name":"...","category":"...","sub_type":"...","description":"...","holder":"...","obtained_chapter":N}'
# 更新道具狀態（消耗/轉移/數量）
.venv/bin/python tools/item_query.py --proj {proj} update {ITEM_ID} --quantity N --status "..."
# 轉移持有者
.venv/bin/python tools/item_query.py --proj {proj} transfer {ITEM_ID} --holder {CHAR_ID} --note "..."
# 新增交易紀錄
.venv/bin/python tools/item_query.py --proj {proj} tx-add {chapter} --desc "..." --balance "結餘約XX銀幣"
# 新增嗶嗶帳本
.venv/bin/python tools/item_query.py --proj {proj} bibi-add {chapter} --desc "..." --status "待結清"
# 結清嗶嗶帳本
.venv/bin/python tools/item_query.py --proj {proj} bibi-settle {entry_id} --status "Ch.N已結清"
```

### Step 9: 冷熱資料分層與歸檔 (Archiving)
// turbo
若 `mode=full`，執行以下歸檔邏輯，將不活躍的資料移入 `memory/archive/`：

```yaml
归檔規則 (The Archivist):
  1. 角色 (Characters):
     - 條件: (狀態為DEAD/MISSING/RETIRED 且 重要性<8) 或 (路人角色且超過1個Arc未出現)
     - 動作: 
       1. 移至 `memory/archive/characters_archive.yaml`
       2. **更新索引**: 在 `memory/archive_index.yaml` 記錄 {id, name, summary, path}
     - 保留: 原檔中刪除，僅在 Index 保留摘要。
     
  2. 物品 (Items):
     - 條件: (狀態為CONSUMED/DESTROYED/LOST 且 等級<Rare)
     - 動作:
       1. 移至 `memory/archive/items_archive.yaml`
       2. **更新索引**: 在 `memory/archive_index.yaml` 記錄 {id, name, path}
     - 保留: 原檔中刪除。
     
  3. 歷史事件 (Lore):
     - 條件: 屬於「上一個Arc」且狀態為 resolved/closed
     - 動作: 
       1. 移至 `memory/archive/arc_{N}_history.md`
       2. **更新索引**: 在 `memory/archive_index.yaml` 記錄 {arc_id, summary_path}
     
  4. 地點/勢力 (Loc/Faction):
     - 條件: 毀滅、併吞或劇情徹底離開該地圖
     - 動作: 移至 `memory/archive/world_archive.yaml` 並更新索引。

> [!TIP]
> **索引機制 (The Catalog)**
> 為了避免歸檔變成「死儲存」，所有移入 `archive/` 的資料，都必須在 `memory/archive_index.yaml` 中保留一條**輕量級索引**。
> 當 AI 在規劃劇情時發現索引中的關鍵字（如「已故的張偉」），便可通過 `read_resource` 或 `view_file` 主動調取檔案。
```

### Step 10: 輸出維護報告
// turbo
顯示維護摘要：
- 更新了哪些檔案
- 新增了多少條目
- 待處理事項提醒

## 維護優先級

| 優先級 | 類別 | 模式 | 說明 |
|--------|------|------|------|
| 1 | 必更新 | light + full | ChromaDB lore, narrative_progress, emotion_log |
| 2 | 高頻更新 | light + full | character_db.current_state |
| 3 | 中頻更新 | full only | faction_registry, world_atlas |
| 4 | 低頻更新 | full only | power_system, item_compendium |

## 輸出

維護完成後，所有設定檔與最新章節內容保持同步。

## 重要注意事項

1. **Context 重用**：在讀取任何檔案前，先確認該檔案內容是否已存在於當前 context 中（例如由 nvChapter 的前序步驟載入）。若已存在，直接使用 context 中的版本，不重複讀取
