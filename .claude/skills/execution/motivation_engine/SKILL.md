---
name: motivation_engine
description: 動機引擎 - 計算角色當前動機強度，識別衝突節點，讓角色行為有邏輯依據
---

# 動機引擎 (Motivation Engine)

每章寫作前分析出場角色的**當前動機狀態**並識別**衝突節點**，將「事件驅動」改為「角色驅動」：先決定角色想要什麼，衝突與場景自然從動機交叉產生。

## 輸入

1. 角色 SQLite：`.venv/bin/python tools/char_query.py --proj {{PROJ}} get-public {CHAR_IDS}` → 取 `base_profile.core_desire` / `base_profile.fear` / `current_state`
2. ChromaDB chapters（最近章結尾）：`ChapterVector.get_recent_chapters(n)` → `ending_summary`
3. ChromaDB lore（近期事件與關係變動）：`.venv/bin/python tools/lore_query.py --proj {{PROJ}} lore "{角色名}" --n 10`
4. `{{PROJECT_DIR}}/config/outline_index.yaml` → current_arc → `config/outline/arc_{N}.yaml`：當前 Arc/SubArc 情境
5. `{{PROJECT_DIR}}/config/novel_config.yaml` 的 `theme_settings`（用於 `theme_resonance` 欄位）

## 輸出

更新 `{{PROJECT_DIR}}/memory/motivation_map.yaml`，結構：

```yaml
generated_for_chapter: <int>
timestamp: <ISO>

character_motivations:         # 每個出場 Protagonist/Antagonist/Supporting
  - character_id, name
    active_motivation: {desire, intensity(0-100), urgency: low|medium|high|critical}
    blocking_factors: [{factor, severity: minor|major|critical}]
    potential_actions: [{action, likelihood(0-1), requires: [...]}]
    emotional_state: {primary, secondary, stability(0-100)}
    presence_modulation:       # 情緒→物理表現對照表
      base: "（來自 DB presence 的預設姿態）"
      <情緒名>: "<該情緒下的姿態描述>"
      # 至少涵蓋本章可能經歷的情緒
    theme_resonance: {theme, connection}   # theme_settings.enabled 時

conflict_nodes:                # 多角色動機交叉的爆發點
  - id, type: goal_clash|value_clash|resource_competition|loyalty_conflict|trust_crisis
    participants: [CHAR_IDS]
    description
    stakes: {if_A_wins, if_B_wins}
    tension_level(0-100)
    ready_to_trigger: bool     # 達閾值可在本章觸發
    possible_outcomes: [{outcome, probability, consequence}]

relationship_tensions:         # 關係張力追蹤
  - source, target
    current_tension(0-100), threshold
    underlying_issue, surface_status
    potential_trigger
    if_triggered: {confrontation_type, possible_resolutions: [...]}

scene_suggestions:             # 基於以上分析的自動建議
  - suggestion, reason, theme_fit|purpose
```

## 執行步驟

### Step 1：載入角色狀態
讀所有出場 Protagonist/Antagonist/Supporting 的 `base_profile` + `current_state` + 最近行動（ChromaDB lore_bank）。次要角色簡單記錄即可，不做完整分析。

### Step 2：計算動機強度（每角色）
輸入 core_desire / fear / traits / last_chapter / location / emotional_state / recent_events / arc_summary / subarc_summary。輸出 `active_motivation`、`intensity`、`blocking_factors`、`potential_actions`、`emotional_state`、`presence_modulation`（情緒→姿態對照；場景內情緒會多次轉變，寫作 skill 依當下情緒選用對應表現）。若 `theme_settings.enabled`，額外輸出 `theme_resonance`（動機如何與 `primary_theme` 共鳴）。

### Step 3：識別衝突節點
對所有角色動機兩兩/多方比對，輸出 `conflict_nodes`（參與者、type、description、stakes、tension_level、ready_to_trigger、possible_outcomes）。

### Step 4：分析關係張力
對每對有互動記錄的角色，評估 `current_tension`、潛在爆發點、觸發條件、爆發後走向，輸出 `relationship_tensions`。

### Step 5：生成場景建議
輸出 2–3 個 `scene_suggestions`。考慮因素：
1. 哪些 conflict_nodes 已經成熟（`ready_to_trigger == true`）？
2. 哪些 relationship_tensions 接近閾值？
3. 哪些角色的動機最急迫（intensity 最高）？
4. 如何與當前主題呼應？

每個建議必填：`suggestion`（建議內容）、`reason`（建議理由）、`theme_fit` 或 `purpose`（與主題的關聯或劇情目的）。

### Step 6：寫入 `memory/motivation_map.yaml`

## 觸發閾值

`intensity >= 80` 本章內應有相關行動；`tension >= 70` 可安排對質/衝突；`conflict.ready_to_trigger == true` 可在本章觸發。

## 注意事項

1. **不強制觸發**：建議僅供 chapter_beater 參考，最終由大綱和使用者 `direction` 決定
2. **保持一致性**：動機變化必須有事件支撐，不能無端改變
3. **避免過度分析**：次要角色只需簡單記錄，不用完整分析
4. **與 chaos_engine 配合**：低機率事件可能打破預期動機鏈
5. **更新頻率**：每章執行一次，重大事件後立即更新

## 關聯

呼叫時機：`nvChapter` Step 1.5 之後，作為 `chapter_beater` 前置輸入｜輸出使用者：`chapter_beater`（衝突節點→節拍）、`scene_writer`（行為依據）、`dialogue_director`（對話反映動機）｜協作：`execution/chaos_engine`（低機率事件可打破動機鏈）
