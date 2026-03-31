---
description: 維護記憶與設定檔同步
---

# /nvMaint - 維護記憶

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `mode` | ❌ | `light` / `full` | `light` |
| `chapter` | ❌ | 指定要處理的章節號 | 自動偵測 |

## 執行模式：Main Context (B 類)

直接在當前 session 執行，不啟動 sub-agent。

### 初始化
1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. 將下方所有 `{{...}}` 替換為實際值後，依序執行各 Step

## 模式速查
- **light**：Phase A → B → C → D（見下方 Light Mode 並行流程）
- **full**：Phase A → B → C → D，然後 Steps 5-9, 10

## CLI Placeholder

以下為 CLI 命令縮寫。`{{...}}` = 初始化/本表定義的固定值；`{...}` = 執行時動態替換。`{{REPO_ROOT}}`/`{{PROJ}}`/`{{PROJECT_DIR}}` 定義見上方初始化 section。**先解析 `{{PROJ}}`，再展開其他 Placeholder。** Step 內 code block 省略 `cd` 前綴，實際執行時補上：

1. 讀取：`cd {{REPO_ROOT}} && cmd1 && cmd2`（失敗即停）
2. 寫入：`cd {{REPO_ROOT}} && cmd1 ; cmd2 ; cmd3`（`cd` 用 `&&` 確保成功，`;` 串連後續寫入，單項失敗不阻斷）
3. 先批次讀，再分析，再批次寫

| Placeholder | 展開為 |
|-------------|--------|
| `{{CHAR}}` | `.venv/bin/python tools/char_query.py --proj {{PROJ}}` |
| `{{EMO}}` | `.venv/bin/python tools/emotion_query.py --proj {{PROJ}}` |
| `{{LORE}}` | `.venv/bin/python tools/lore_update.py --proj {{PROJ}}` |
| `{{ITEM}}` | `.venv/bin/python tools/item_query.py --proj {{PROJ}}` |
| `{{FAC}}` | `.venv/bin/python tools/faction_query.py --proj {{PROJ}}` |
| `{{ATLAS}}` | `.venv/bin/python tools/atlas_query.py --proj {{PROJ}}` |

---

## Light Mode 並行流程

> light mode 使用以下 Phase 結構取代逐步執行，減少 API call 次數。

### Phase A: 並行讀取（1 個 API turn，多個 tool call）

判斷要處理的章節號：
1. 若 caller 傳入 `chapter` 參數 → 直接使用該章號
2. 否則 → 列出 `{{PROJECT_DIR}}/output/chapters/` 目錄，取最大編號的章節檔案

在**同一個 API turn** 內並行發出以下 tool call：
- **Read** 章節檔案（若 context 中已有則跳過）
- **Bash**: `{{CHAR}} get-state ID1,ID2,ID3`（本章出場角色）
- **Read** `{{REPO_ROOT}}/.claude/skills/memory/emotional_wave_analyzer/SKILL.md`（若 context 中已有則跳過）

### Phase B: 統一分析（1 個 API turn，純文字思考）

根據章節內容 + 角色當前狀態 + 情感評分規則，**一次性決定**以下所有更新內容：

1. **Lore events**：要新增哪些事件（id、category、name、doc、status）
2. **Emotion scores**：tension 分數、emotion 描述、elements、note；是否超過閾值需要 set-suggestions/set-consecutive
3. **Character state**：每個出場角色的 current_state 變更、關係變更

> id 格式：`evt_{category}_{ch}`，如 `evt_event_60`、`evt_relationship_change_60_02`（同章多筆加序號）。
> category: `global_memory` `character_memory` `mystery` `event` `world_fact` `relationship_change` `foreshadowing` `item_status` `permanent_change`
> status: `active` `permanent` `open` `closed` `archived`
> `char` 選填，僅在有明確關聯角色時加上

### Phase C: 並行寫入（1 個 API turn，多個 tool call）

在**同一個 API turn** 內並行發出以下 Bash call：

**Bash call 1** — Lore + Emotion（`;` 串連）：
```
{{LORE}} batch-event --json '[...]' ; {{EMO}} add {ch} --tension {score} --emotion "..." --elements '{...}' --note "..."
```

**Bash call 2** — Character state（`;` 串連）：
```
{{CHAR}} update-state ID1 --json '{...}' ; {{CHAR}} update-state ID2 --json '{...}'
```

**Bash call 3**（僅在有關係變更時） — Character relations：
```
{{CHAR}} update-rel SRC TGT --surface "..." --hidden "..." --tension N
```

### Phase D: 驗證 + 報告（1 個 API turn）

**Bash**（`;` 串連）：
```
{{EMO}} recent --n 5
```
- 若 Phase B 判定超過閾值 → 追加：`{{EMO}} set-suggestions --json '[...]' ; {{EMO}} set-consecutive --json '{...}'`
- 列出：更新了哪些項目、新增多少條目、待處理事項

---

## === LIGHT MODE 到此結束 ===

## Full Mode 逐步流程

> full mode 包含 light mode 的 Phase A-D，然後繼續執行以下 Steps 5-9。

## Step 3:【已移至 nvChapter】

> 進度推進（current_chapter increment、beat 推進、章節摘要）已移至 nvChapter Step 3.5d。nvMaint 不再修改敘事進度。

## 以下 Steps 5-9 僅 mode=full 時執行

## Step 5:【full only】更新世界地圖

新區域讀取 `{{REPO_ROOT}}/.claude/skills/foundation/world_builder/SKILL.md`。
```
{{ATLAS}} list
{{ATLAS}} add --json '{"id":"REG_NEW","name":"...","region_type":"...","summary":"...","description":"...","locations":[...]}'
{{ATLAS}} update-field REG_001 climate "..."
```

## Step 6:【full only】更新勢力登記

新勢力讀取 `{{REPO_ROOT}}/.claude/skills/foundation/faction_forge/SKILL.md`。
```
# ⚡ 批次讀
{{FAC}} list && {{FAC}} relations
# 寫入（按需）
{{FAC}} add --json '{"id":"...","name":"...","tier":"...","type":"...","philosophy":"...","description":"..."}'
{{FAC}} update-tension FAC_001 FAC_002 85
{{FAC}} update-field FAC_001 notable_members '["CHAR_001","CHAR_003"]'
{{FAC}} add-rel FAC_001 FAC_NEW --status "Neutral" --tension 30
```

讀取 `{{REPO_ROOT}}/.claude/skills/memory/power_dynamic_updater/SKILL.md`，**嚴格按照事件表與閾值規則執行，不得跳過**。

## Step 7:【full only】更新力量體系

更新 `{{PROJECT_DIR}}/config/power_system.yaml`。新能力讀取 `{{REPO_ROOT}}/.claude/skills/foundation/power_architect/SKILL.md`。

## Step 8:【full only】更新物品目錄

新物品讀取 `{{REPO_ROOT}}/.claude/skills/foundation/item_smith/SKILL.md` 設計後寫入：
```
{{ITEM}} add --json '{"id":"...","name":"...","category":"...","sub_type":"...","description":"...","holder":"...","obtained_chapter":N}'
{{ITEM}} update {ID} --quantity N --status "..."
{{ITEM}} transfer {ID} --holder {CHAR_ID} --note "..."
{{ITEM}} tx-add {ch} --desc "..." --balance "結餘約XX銀幣"
{{ITEM}} bibi-add {ch} --desc "..." --status "待結清"
{{ITEM}} bibi-settle {entry_id} --status "Ch.N已結清"
```

## Step 9:【full only】冷熱資料歸檔

1. **角色**：(DEAD/MISSING/RETIRED 且重要性<8) 或 (路人且超過1 Arc未出現) → `{{CHAR}} update-field {ID} status archived`（update-field 接受任意頂層欄位名），並匯出至 `archive/characters_archive.yaml`
2. **物品**：(CONSUMED/DESTROYED/LOST 且等級<Rare) → `{{ITEM}} update {ID} --status archived`，並匯出至 `archive/items_archive.yaml`
3. **事件**：上一 Arc 且 resolved/closed → `archive/arc_{N}_history.md`
4. **地點/勢力**：毀滅/併吞/離開 → `{{ATLAS}} update-field {REG_ID} status archived` / `{{FAC}} update-field {FAC_ID} status archived`，並匯出至 `archive/world_archive.yaml`

均需同步更新 `archive_index.yaml`。SQLite 為 source of truth，YAML 歸檔僅作離線參考。

## Step 10:【必執行】輸出維護報告

列出：更新了哪些檔案、新增多少條目、待處理事項。

## 注意事項
- 無法使用 `/nvXXX` skill，改為「Read SKILL.md 並嚴格按步驟執行」
- ChromaDB 操作使用 Bash 執行
- **Context 重用**：讀取前確認是否已在 context 中，已存在則不重複讀取
- **Sub-agent 環境**：若本 skill 在 nvAudit sub-agent 內執行，Bash 中禁止使用 `$()` 或 backtick 取得時間戳，改用 Python `datetime`
