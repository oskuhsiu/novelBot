---
name: chapter_beater
description: 章節拆解師 - 將章節大綱拆解為衝突驅動的場景節拍 (Conflict-Driven Beats)
---

# 章節拆解師 (Chapter Beater)

把「一章大綱」拆解成 conflict-driven beats（scene_writer 的執行指令）。
核心原則：每個節拍要「解決什麼衝突」+「呼應什麼主題」，而非單純「發生什麼事」。

> **術語**：SubArc = Arc 下的情節段（由 outline_architect 規劃）；Beat = 章內場景節拍（本 skill 產出）。兩者層級不同。

## 輸入

1. `{{PROJECT_DIR}}/config/narrative_progress.yaml`：當前章的 summary、上一章結尾
2. `{{PROJECT_DIR}}/config/outline_index.yaml` → current_arc → `config/outline/arc_{N}.yaml`：當前 SubArc 摘要
3. `{{PROJECT_DIR}}/config/novel_config.yaml`：`engine_settings.pacing_pointer`、`content_weights`、`theme_settings`
4. 角色/世界資料庫（`char_query.py`、`atlas_query.py`）
5. **連貫性上下文**（由 nvChapter Step 1.5 傳入）：`current_subarc_summary`、`previous_chapters_in_subarc`、`previous_subarc_ending`；若 `arc_boundary.is_new_arc` 則含 `previous_arc_ending`。優先用 ChromaDB `chapters` collection (`ChapterVector.get_chapter` / `get_recent_chapters`) 的 `ending_summary`
6. **動機地圖** `memory/motivation_map.yaml`：`character_motivations`、`conflict_nodes`、`relationship_tensions`、`scene_suggestions`
7. 可選 `direction`：使用者指定劇情走向

若 `motivation_map.yaml` 不存在，先呼叫 `execution/motivation_engine` 生成；若 `theme_settings.enabled == false`，退化為只填傳統欄位。

## 輸出

更新 `narrative_progress.yaml` 當前章的 `beats[]`。每個 beat 欄位：

```yaml
- id: "B{chap}_{n}"            # e.g. B1_1
  summary: ...
  location: ...
  characters: [CHAR_ID, ...]
  conflict:                    # 必填
    type: goal_clash|value_clash|resource_competition|internal|relationship
    driver: "A 想要 X vs B 想要 Y"
    stakes: "失敗後果"
  driving_motivations:         # 必填，每個出場角色一條
    - {character, wants, intensity, action_tendency}
  possible_outcomes:           # 2-3 個
    - {outcome, likelihood}
  selected_outcome: null       # 由 scene_writer/chaos_engine 填
  theme_resonance:             # theme_settings.enabled 時必填
    {theme, expression, motif_usage}
  action: ...                  # 外在動作
  emotion_shift: ...           # 情緒轉折
  info_reveal: ...             # 可選
  hook: ...                    # 鉤子
  weight_hint: null            # 多數情況 null，特殊節拍才覆寫全域權重
  status: pending
```

## 執行步驟

### Step 0：載入動機地圖
若存在則讀 `character_motivations` / `conflict_nodes` / `relationship_tensions` / `scene_suggestions`；否則先呼叫 motivation_engine。

### Step 1：分析章節目標
從 narrative_progress 取 chapter_id/title/summary/structure_role/emotion_goal。依 `pacing_pointer` 決定節拍數（基礎 4 個，細節粒度越細則越多）。讀 `theme_settings.primary_theme` 與當前 theme_arc 階段。

### Step 2：匹配衝突節點
從 `conflict_nodes` 挑出 `ready_to_trigger == true` 且與 chapter summary/主題匹配者（1–2 個作為本章核心）。若無成熟衝突，用 `relationship_tensions` 設計鋪墊，或建立新的微衝突。

### Step 3：生成衝突驅動節拍
對每個節拍輸出上方 schema 所有欄位。要求：
- 每個節拍都有明確 `conflict` 與 `driving_motivations`
- 節拍序列形成張力曲線
- 若 `theme_settings.enabled`，至少 1 個節拍 `theme_resonance` 非空（間接表達優先，避免說教；每 Arc 每個 motif 最多 3 次）

### Step 4：設定 weight_hint
多數節拍留 `null` 用全域權重。特例：`conflict.type == relationship` → `dialogue: 0.5+`；`goal_clash` + 物理對抗 → `combat`/`action: 0.4+`；`internal` → `internal_monologue: 0.5+`；主題共鳴場景 → `scenery_desc: 0.3+`。

### Step 5：寫回 narrative_progress.yaml 當前章 `beats[]`。

## 節拍粒度（依 pacing_pointer）

| pacing | 粒度 | 說明 |
|---|---|---|
| 0.1 | 極細 | 一個簡單動作拆成多個節拍 |
| 0.3 | 細 | 每個節拍是一個微場景 |
| 0.5 | 中 | 每個節拍是一個完整場景 |
| 0.7 | 粗 | 每個節拍是多個場景的組合 |
| 1.0 | 極粗 | 節拍只是提綱挈領 |

## 主題共鳴指南（`theme_settings.enabled == true` 時）

1. 每章**至少 1 個節拍**有明確主題共鳴
2. **不要過度**：不是每個節拍都需要點題
3. **間接優於直接**：通過行動與選擇體現主題，而非說教
4. **意象適度**：每個 Arc 每個 motif 最多使用 3 次

## 注意事項

1. **節拍不是正文**：節拍是指令，不是最終文字
2. **保持靈活**：執行時可依實際情況調整
3. **情緒曲線**：確保節拍之間的情緒有起伏
4. **信息節奏**：不要在一個節拍塞太多信息
5. **留白**：有些節拍可以故意簡略，讓寫作時有發揮空間
6. **動機優先**：角色做什麼，取決於他們想要什麼
7. **衝突有意義**：每個衝突都應該推進角色或主題發展

## 關聯

前置：`structure/outline_architect`、`structure/pacing_calculator`、`execution/motivation_engine`｜協作：`memory/relationship_dynamics`｜後續：`structure/beat_optimizer`、`execution/scene_writer`
