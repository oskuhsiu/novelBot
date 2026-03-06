---
description: 維護記憶與設定檔同步
---

# /nvMaint - 維護記憶

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `mode` | ❌ | `light`（預設）/ `full` | `mode=full` |

## 執行模式：Sub-Agent

### 調度步驟（主 context 執行）

1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`
3. 啟動 Agent tool（`subagent_type: general-purpose`，`run_in_background: false`）
4. 將下方 Agent Prompt 的 `{{...}}` 替換為實際值

> Dispatcher 只做參數解析和路徑組合，不讀取任何專案檔案。

---

## Agent Prompt

````
你是小說維護助手。請對專案執行記憶與設定檔維護。

## 任務參數
- 專案路徑：{{PROJECT_DIR}}
- 專案名稱：{{PROJ}}
- 維護模式：{{MODE}}（light 或 full）
- 專案根目錄：{{REPO_ROOT}}

## 模式速查
- **light**：僅執行 Steps 1-4
- **full**：執行 Steps 1-9

## Step 1: 讀取最新章節

讀取 `{{PROJECT_DIR}}/config/narrative_progress.yaml` 取得 `current_chapter`。
讀取 `{{PROJECT_DIR}}/output/chapters/` 中最新完成的章節檔案。

## Step 2: 更新長期記憶（必執行）

寫入 ChromaDB `lore_bank` collection。更新項目：events, relationship_changes, open/closed foreshadowing, world_facts, item_status, permanent_changes。

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} event --id "{id}" --cat "{category}" --ch {chapter} --char "{char_id}" --name "{name}" --status "{status}" --doc "{document}"
```

允許的 category: `global_memory`, `character_memory`, `mystery`, `event`, `world_fact`, `relationship_change`, `foreshadowing`, `item_status`, `permanent_change`
允許的 status: `active`, `permanent`, `open`, `closed`, `archived`

## Step 2b: 更新情感記錄（必執行）

讀取 `{{REPO_ROOT}}/.claude/skills/memory/emotional_wave_analyzer/SKILL.md` 並遵循其指令分析本章情感。

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} add {chapter_id} --tension {score} --emotion "{primary_emotion}" --elements '{...}' --note "..."
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} recent --n 5
# 若超過閾值：
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} set-suggestions --json '[...]'
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} set-consecutive --json '{...}'
```

## Step 3: 更新敘事進度（必執行）

更新 `{{PROJECT_DIR}}/config/narrative_progress.yaml`：
- `current_chapter`: +1
- `words_written`: 累加（讀取 `{{REPO_ROOT}}/.claude/skills/execution/word_counter/SKILL.md` 計算字數）
- `last_updated`: 今日日期

**節拍推進：**
- 清空 `current_beat`
- `upcoming_beats` 有剩餘 → 彈出第一項存入 `current_beat`
- `upcoming_beats` 為空 → 當前 SubArc 移入 `completed_subarcs`，推進到下一個 SubArc

**章節摘要：** 讀取 `{{REPO_ROOT}}/.claude/skills/memory/chapter_summarizer/SKILL.md` 並遵循其指令生成摘要（目標：原文 15-20%），寫入 ChromaDB：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} chapter --id {N} --title "{title}" --arc "{arc_id}" --subarc "{subarc_id}" --words {word_count} --summary "{chapter_summary}"
```

## Step 4: 更新角色資料庫（必執行）

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} get-state {CHAR_ID}
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} update-state {CHAR_ID} --json '{"location":"...","health":"...","emotional_state":"...","inventory":[...],"active_goals":[...],"relationships":[...],"last_updated_chapter":N}'
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} update-rel {SOURCE_ID} {TARGET_ID} --surface "..." --hidden "..." --tension N
```

## === LIGHT MODE 到此結束 ===
## 以下 Steps 5-9 僅 mode=full 時執行，light mode 請忽略

## Step 5: 更新世界地圖（full only）

更新 `{{PROJECT_DIR}}/config/world_atlas.yaml`。新區域讀取 `{{REPO_ROOT}}/.claude/skills/foundation/world_builder/SKILL.md`。

## Step 6: 更新勢力登記（full only）

更新 `{{PROJECT_DIR}}/config/faction_registry.yaml`。新勢力讀取 `{{REPO_ROOT}}/.claude/skills/foundation/faction_forge/SKILL.md`。

讀取 `{{REPO_ROOT}}/.claude/skills/memory/power_dynamic_updater/SKILL.md` 分析勢力緊張度。

## Step 7: 更新力量體系（full only）

更新 `{{PROJECT_DIR}}/config/power_system.yaml`。新能力讀取 `{{REPO_ROOT}}/.claude/skills/foundation/power_architect/SKILL.md`。

## Step 8: 更新物品目錄（full only）

使用 CLI 更新物品資料庫（SQLite）。新物品讀取 `{{REPO_ROOT}}/.claude/skills/foundation/item_smith/SKILL.md` 設計後寫入：

```bash
# 新增道具
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} add --json '{"id":"...","name":"...","category":"...","sub_type":"...","description":"...","holder":"...","obtained_chapter":N}'
# 更新道具狀態（消耗/轉移/數量）
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} update {ITEM_ID} --quantity N --status "..."
# 轉移持有者
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} transfer {ITEM_ID} --holder {CHAR_ID} --note "..."
# 新增交易紀錄
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} tx-add {chapter} --desc "..." --balance "結餘約XX銀幣"
# 新增嗶嗶帳本
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} bibi-add {chapter} --desc "..." --status "待結清"
# 結清嗶嗶帳本
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} bibi-settle {entry_id} --status "Ch.N已結清"
```

## Step 9: 冷熱資料歸檔（full only）

歸檔規則：
1. **角色**：(DEAD/MISSING/RETIRED 且重要性<8) 或 (路人且超過1 Arc未出現) → `archive/characters_archive.yaml`
2. **物品**：(CONSUMED/DESTROYED/LOST 且等級<Rare) → `archive/items_archive.yaml`
3. **事件**：上一 Arc 且 resolved/closed → `archive/arc_{N}_history.md`
4. **地點/勢力**：毀滅/併吞/離開 → `archive/world_archive.yaml`

均需同步更新 `archive_index.yaml`。

## Step 10: 輸出維護報告

列出：更新了哪些檔案、新增多少條目、待處理事項。

## 注意事項
- 無法使用 `/nvXXX` skill 指令，改為「Read SKILL.md 並遵循其指令」
- ChromaDB 操作使用 Bash 執行
- **Context 重用**：讀取前確認是否已在 context 中，已存在則不重複讀取
````
