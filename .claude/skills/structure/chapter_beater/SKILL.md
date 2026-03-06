---
name: chapter_beater
description: 章節拆解師 - 將章節大綱拆解為衝突驅動的場景節拍 (Conflict-Driven Beats)
---

# 章節拆解師 (Chapter Beater)

## 功能概述

此 Skill 將「一章」的大綱摘要拆解為具體的「情節節拍（Beats）」。

> [!IMPORTANT]
> **v2.0 核心轉變**
> 從「事件導向」轉為「衝突導向」：
> - 舊：這個節拍要「發生什麼事」
> - 新：這個節拍要「解決什麼衝突」+「呼應什麼主題」

節拍是最小的敘事單位，是 Scene Writer 實際執行的指令。

## 輸入

1. 從 `config/narrative_progress.yaml` 讀取：
   - 當前章節的 `summary`
   - 上一章的結尾狀態

2. 從 `config/story_outline.yaml` 讀取：
   - 當前 SubArc 的摘要和結構

2. 從 `config/novel_config.yaml` 讀取：
   - `engine_settings.pacing_pointer`
   - `engine_settings.content_weights`
   - **`theme_settings`**（主題追蹤）

3. 從角色和世界資料庫讀取相關資訊

4. **連貫性上下文**（從 nvChapter Step 1.5 傳入）：
   - `continuity_context.current_subarc_summary`：當前次網摘要
   - `continuity_context.previous_chapters_in_subarc`：同一次網已有章節
   - `continuity_context.previous_subarc_ending`：上一次網結尾
   - **優先使用 ChromaDB `chapters` collection 讀取 `ending_summary`**
     → `ChapterVector.get_chapter(chapter_id)` 或 `get_recent_chapters(n)`
   - **若 `arc_boundary.is_new_arc == true`**，則包含 `previous_arc_ending`

5. **劇情導引**（可選，從參數傳入）：
   - `direction`：使用者指定的劇情走向

6. **【新增】動機地圖**（從 `memory/motivation_map.yaml`）：
   - `character_motivations`：角色當前動機
   - `conflict_nodes`：已識別的衝突節點
   - `relationship_tensions`：關係張力狀態
   - `scene_suggestions`：建議場景

## 輸出

更新 `narrative_progress.yaml` 中當前章節的 `beats` 陣列（新格式）

## 新的節拍結構（v2.0）

```yaml
beats:
  - id: "B1_1"
    # === 基本資訊 ===
    summary: "..."
    location: "..."
    characters: [...]
    
    # === 衝突核心（新增）===
    conflict:
      type: "goal_clash"  # goal_clash/value_clash/resource_competition/internal/relationship
      driver: "CHAR_001.保護妹妹 vs CHAR_002.執行命令"
      stakes: "若主角失敗，妹妹將被..."
      
    # === 角色動機（新增）===
    driving_motivations:
      - character: "CHAR_001"
        wants: "解救妹妹"
        intensity: 85
        action_tendency: "冒險突破"
      - character: "CHAR_002"
        wants: "完成任務"
        intensity: 60
        action_tendency: "按規則辦事"
    
    # === 預期結果 ===
    possible_outcomes:
      - outcome: "主角說服對方"
        likelihood: 0.3
      - outcome: "武力衝突"
        likelihood: 0.5
      - outcome: "第三方介入"
        likelihood: 0.2
    selected_outcome: null  # 由 scene_writer 或 chaos_engine 決定
    
    # === 主題共鳴（新增）===
    theme_resonance:
      theme: "犧牲與代價"
      expression: "主角願意付出什麼來救妹妹？"
      motif_usage: null  # 可選：使用某個主題意象
    
    # === 傳統欄位 ===
    action: "..."
    emotion_shift: "..."
    info_reveal: "..."
    hook: "..."
    weight_hint: null
    status: "pending"
```

## 執行步驟

### Step 0: 載入動機地圖【新增】

```yaml
若 memory/motivation_map.yaml 存在:
  讀取:
    - character_motivations（角色動機）
    - conflict_nodes（衝突節點）
    - relationship_tensions（關係張力）
    - scene_suggestions（場景建議）
    
若不存在:
  呼叫 skill_motivation_engine 先生成
  或使用傳統模式（退化為舊版行為）
```

### Step 1: 分析章節目標

```
讀取當前章節資訊：
- 章節 ID：{{chapter_id}}
- 標題：{{title}}
- 摘要：{{summary}}
- 結構功能：{{structure_role}}
- 情感目標：{{emotion_goal}}

讀取 pacing_pointer：{{pacing_pointer}}
計算節拍數量：基礎 4 個，根據 pacing 調整

【新增】讀取主題設定：
- primary_theme：{{primary_theme}}
- theme_arc 當前階段：{{current_theme_stage}}
- 可用 motifs：{{available_motifs}}
```

### Step 2: 匹配衝突節點【新增】

```
分析 motivation_map 中的衝突節點：

對於每個 ready_to_trigger == true 的衝突：
  評估：
    - 是否適合在本章處理？
    - 與 chapter summary 的關聯程度？
    - 與當前主題的共鳴程度？
    
選擇 1-2 個衝突作為本章核心

若無成熟衝突：
  - 使用 relationship_tensions 設計鋪墊場景
  - 或創造新的微衝突
```

### Step 3: 生成衝突驅動節拍【重構】

```
你是一位精通衝突設計的劇本師。
請將以下章節摘要拆解為 {{beat_count}} 個衝突驅動的場景節拍：

【章節摘要】：{{summary}}
【情感目標】：{{emotion_goal}}
【參與角色】：{{available_characters}}
【可用場景】：{{available_locations}}

## 本章核心衝突
{{selected_conflicts}}

## 角色動機（關鍵！）
{{character_motivations}}

## 主題要求
- 主題：{{primary_theme}}
- 本階段目標：{{theme_arc_stage}}
- 可用意象：{{motifs}}

## 連貫性上下文（必讀）

【當前次網摘要】：{{current_subarc_summary}}
【同一次網前章】：{{previous_chapters_in_subarc}}
【上一次網結尾】：{{previous_subarc_ending}}

## 劇情導引（若有）
{{direction}}

## 節拍設計要求

對於每個節拍，請輸出：

### 基本資訊
1. **節拍 ID**：如 B1_1, B1_2
2. **場景地點**：具體到房間或區域
3. **出場人物**：誰在場

### 衝突核心【必填】
4. **衝突類型**：goal_clash/value_clash/resource_competition/internal/relationship
5. **衝突驅動**：「角色A想要X vs 角色B想要Y」或「角色內心X vs Y」
6. **利害關係**：若此衝突失敗，後果是什麼？

### 角色動機【必填】
7. **出場角色各自想要什麼？**
8. **他們的動機強度如何影響行為？**

### 可能結果
9. **2-3 種可能的結果**及其可能性

### 主題共鳴【若啟用】
10. **此節拍如何呼應主題？**
11. **是否使用主題意象？**

### 傳統要素
12. **外在動作 (Action)**
13. **情緒轉折 (Reaction)**
14. **信息揭露**（可選）
15. **鉤子 (Hook)**

確保：
- 每個節拍都有明確的衝突驅動
- 角色行為有動機支撐
- 節拍序列形成張力曲線
- 至少 1 個節拍呼應主題
```

### Step 4: 設定權重暗示

```
根據 {{content_weights}} 和節拍類型，
為每個節拍設定 weight_hint：

## 權重考量

- 衝突類型為「relationship」→ dialogue: 0.5+
- 衝突類型為「goal_clash」+ 物理對抗 → combat: 0.4+ 或 action: 0.4+
- 衝突類型為「internal」→ internal_monologue: 0.5+
- 主題共鳴場景 → scenery_desc: 0.3+（環境烘托）

大部分節拍使用全域權重即可（weight_hint: null）
```

### Step 5: 寫入 narrative_progress.yaml

使用新的節拍結構（見上方）寫入

## 衝突類型說明

| 類型 | 說明 | 常見表現 |
|------|------|----------|
| goal_clash | 目標衝突 | 兩人都想得到同一件東西 |
| value_clash | 價值觀衝突 | 對錯誤的不同判斷 |
| resource_competition | 資源競爭 | 有限資源的分配 |
| internal | 內心衝突 | 角色自我掙扎 |
| relationship | 關係衝突 | 信任、忠誠、情感問題 |

## 節拍範例（新格式）

```yaml
beats:
  - id: "B1_1"
    summary: "主角與情報販子的談判"
    location: "鏽城 - 地下酒吧"
    characters: ["CHAR_001", "NPC_INFO_DEALER"]
    
    conflict:
      type: "resource_competition"
      driver: "主角需要情報 vs 販子開出背叛盟友的代價"
      stakes: "若不答應，妹妹的線索將消失"
      
    driving_motivations:
      - character: "CHAR_001"
        wants: "找到妹妹"
        intensity: 85
        action_tendency: "可能接受不道德交易"
      - character: "NPC_INFO_DEALER"
        wants: "獲得情報優勢"
        intensity: 70
        action_tendency: "不會讓步"
    
    possible_outcomes:
      - outcome: "主角妥協，用其他方式支付"
        likelihood: 0.4
      - outcome: "主角接受交易，背叛盟友"
        likelihood: 0.3
      - outcome: "談判破裂，主角用武力"
        likelihood: 0.3
    selected_outcome: null
    
    theme_resonance:
      theme: "權力的代價"
      expression: "為了達成目標，願意犧牲什麼？"
      motif_usage: null
    
    action: "談判、心理博弈、金錢與道德的權衡"
    emotion_shift: "焦慮 → 掙扎 → 決斷"
    info_reveal: "販子暗示知道妹妹的下落"
    hook: "主角的選擇將在下一節拍揭曉"
    weight_hint: "dialogue: 0.6"
    status: "pending"
```

## 節拍密度與 pacing_pointer

根據 pacing_pointer 調整節拍的粒度：

| pacing_pointer | 節拍粒度 | 說明 |
|----------------|----------|------|
| 0.1 | 極細 | 一個簡單動作拆成多個節拍 |
| 0.3 | 細 | 每個節拍是一個微場景 |
| 0.5 | 中 | 每個節拍是一個完整場景 |
| 0.7 | 粗 | 每個節拍是多個場景的組合 |
| 1.0 | 極粗 | 節拍只是提綱挈領 |

## 主題共鳴指南

若 `theme_settings.enabled == true`：

1. **每章至少 1 個節拍**要有明確的主題共鳴
2. **不要過度**：不是每個節拍都需要點題
3. **間接優於直接**：通過行動和選擇體現主題，而非說教
4. **意象適度**：每個 Arc 每個意象最多使用 3 次

## 使用時機

- **章節開始前**：將大綱轉化為可執行的節拍
- **調整節奏**：當需要改變某章的詳細程度時

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `skill_outline_architect`：需要章節大綱
  - `skill_pacing_calculator`：需要節奏計算
  - **`skill_motivation_engine`**：需要動機地圖【新增】
- **協作 Skill**：
  - **`skill_relationship_dynamics`**：關係張力參考【新增】
- **後續 Skill**：
  - `skill_beat_optimizer`：優化節拍張力
  - `skill_scene_writer`：執行節拍寫作

## 向後兼容

若 `motivation_map.yaml` 不存在或 `theme_settings.enabled == false`：
- 自動退化為舊版行為
- 節拍結構只包含傳統欄位
- 不影響現有專案

## 注意事項

1. **節拍不是正文**：節拍是指令，不是最終文字
2. **保持靈活**：執行時可以根據實際情況調整
3. **情緒曲線**：確保節拍之間的情緒有起伏
4. **信息節奏**：不要在一個節拍塞太多信息
5. **留白**：有些節拍可以故意簡略，讓寫作時有發揮空間
6. **動機優先**：角色做什麼，取決於他們想要什麼
7. **衝突有意義**：每個衝突都應該推進角色或主題發展
