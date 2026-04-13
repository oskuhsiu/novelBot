---
name: outline_architect
description: 大綱建築師 - 根據 Arc-SubArc 結構規劃全書大綱
---

# 大綱建築師 (Outline Architect)

規劃小說整體結構：**Arc（卷，預設 10）→ SubArc（情節段，預設每卷 5–10）→ Chapter（動態生成）**。
章節數公式：`單 SubArc 章數 = 1 / pacing_pointer`，總章數 = Σ 各 SubArc 章數。

> **術語**：SubArc 是 Arc 下的情節段（本 skill 產出）；Beat 是 Chapter 內的場景節拍（由 chapter_beater 產出）。兩者層級不同。

## 輸入

1. `{{PROJECT_DIR}}/config/novel_config.yaml`：`style_profile`（含 genre、tags、main_plot_trope）、`engine_settings.pacing_pointer`、`structure.arcs`（預設 10）、`structure.subarcs_per_arc`（預設 5~10）
2. 角色 SQLite：`.venv/bin/python tools/char_query.py --proj {{PROJ}} list` → 篩 role==Protagonist → `get {CHAR_IDS}` → 取 `core_desire` / `fear`
3. Trope 庫：`{{REPO_ROOT}}/templates/trope_library.yaml` 的 `category: Plot` 列表（全域共用）
4. 伏筆狀態（增量時）：`.venv/bin/python tools/lore_query.py --proj {{PROJ}} lore "伏筆" --category foreshadowing`

## 輸出

雙檔結構（讀取端只需載入 index + 當前 arc）：

```yaml
# {{PROJECT_DIR}}/config/outline_index.yaml  — 輕量索引
current_arc: <int>
arcs:
  - {arc_id, title, summary, emotion_arc, structure_role, pacing_pointer|null,
     file: "outline/arc_{N}.yaml", is_completed: false}
```

```yaml
# {{PROJECT_DIR}}/config/outline/arc_{N}.yaml  — 完整內容
arc_id, title, summary
subarcs:
  - id: "A{arc_id}_S{n}"      # e.g. A1_S3
    summary                    # 1 句核心事件
    characters: [CHAR_IDS]
    location
    emotion_shift              # 平靜→緊張
    hook                       # 結尾鉤子
    pacing_pointer: null       # 覆蓋用，通常 null
    chapters: []               # nvChapter 執行時動態填入
    is_completed: false
is_completed: false
```

`pacing_pointer` 優先級：`SubArc > Arc > 全域`。

## 執行步驟

### Step 0：結構檢查（新增 Arc/SubArc 前必做）
讀 `outline_index.yaml`。若存在，對已完成/進行中的 arcs 從對應 `outline/arc_{N}.yaml` 取細節，彙整：
- `last_arc_summary`、`last_subarc_ending`（當前位置、懸而未決衝突、角色狀態）
- `pending_foreshadowing`（從 ChromaDB lore 查 `--category foreshadowing`，排除已回收者）
- `character_trajectories`（各主要角色 current_state + next_growth_opportunity）
- `thematic_progression`

增量約束：新 Arc 必須銜接 `last_arc_summary`；新 SubArc 延續 `last_subarc_ending`；必須安排回收 `pending_foreshadowing`；角色行為符合 `character_trajectories`。
若 `outline_index.yaml` 不存在但 `story_outline.yaml` 存在 → 視為 legacy，於 Step 5 改寫為新 schema。若兩者皆無 → 直接進 Step 1 全新生成。

### Step 1：讀取設定
取 `structure.arcs` / `structure.subarcs_per_arc` / `engine_settings.pacing_pointer`。

### Step 2：選擇 Plot Trope
若 `style_profile.main_plot_trope` 為空：從 `trope_library.yaml` 的 `category: Plot` 依 genre/tags 匹配，無明顯匹配則隨機挑通用型（PLT_001/PLT_002）。否則用指定 ID 對應的 description。將 trope 作為核心敘事骨架（例：「復仇」→ Arc1-2 種子、Arc3-7 積蓄、Arc8-10 爆發）。

### Step 3：生成 Arc 大綱
對每個 Arc 輸出 `arc_id, title, summary（呼應 trope 階段）, emotion_arc, structure_role, pacing_pointer(可選)`。輸入：genre、trope name+desc、protagonist core_desire+fear。

### Step 4：為每個 Arc 生成 SubArcs
在 `subarcs_per_arc` 範圍內**隨機**取數量（不要固定中位數）。對每個 SubArc 輸出 schema 所有欄位。要求：首個 SubArc 銜接前一 Arc 結尾，末個 SubArc 設懸念引向下一 Arc，彼此邏輯遞進。

### Step 5：寫入檔案
寫 `outline_index.yaml` + 各 `outline/arc_{N}.yaml`。**Legacy migration**：若原有 `story_outline.yaml`，拆解轉寫為新 schema，舊檔備份為 `story_outline.yaml.bak` 不再更新。

## 注意事項

1. **Arc 是骨架，SubArc 是肌肉**：Arc 決定大方向，SubArc 決定具體發展
2. **預留彈性**：不要把每個細節都寫死
3. **情感曲線**：確保讀者情緒有起伏
4. **伏筆意識**：Arc 規劃時就考慮埋設與回收
5. **局部調速**：用 `pacing_pointer` 讓重要段落有足夠篇幅展開

## 關聯

前置：`foundation/character_forge`、`foundation/world_builder`｜後續：`structure/chapter_beater`（章內 beats）、`structure/pacing_calculator`（章數計算）、`/nvChapter`（動態生章並呼叫 scene_writer）
