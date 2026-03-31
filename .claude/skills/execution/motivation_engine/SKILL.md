---
name: motivation_engine
description: 動機引擎 - 計算角色當前動機強度，識別衝突節點，讓角色行為有邏輯依據
---

# 動機引擎 (Motivation Engine)

## 功能概述

此 Skill 是「角色驅動系統」的核心，負責在每章開始前分析所有出場角色的**當前動機狀態**，識別可能產生的**衝突節點**，讓劇情發展有內在邏輯支撐。

> [!IMPORTANT]
> **核心轉變**
> 從「這一章要發生什麼事」變成「角色想要什麼，他們會怎麼做」

## 設計理念

傳統的劇情推進是「事件驅動」的：
- 大綱說第三章要打架 → 所以角色打架

動機引擎改為「角色驅動」：
- 角色A想要X，角色B想要Y，兩者衝突 → 自然產生衝突場景

## 輸入

1. 從角色資料庫（SQLite）讀取：
   ```bash
   .venv/bin/python tools/char_query.py --proj {proj} get-public {CHAR_IDS}
   ```
   提取：`base_profile.core_desire`、`base_profile.fear`、`current_state`

2. 從 ChromaDB `chapters` collection 讀取：
   - 最近章節的 `ending_summary`
   - 使用 `ChapterVector.get_recent_chapters(n)` 取得

3. 從 `config/story_outline.yaml` 讀取：
   - 當前 Arc/SubArc 的情境

3. 從 ChromaDB 讀取近期事件與事實：
   - 執行: `.venv/bin/python tools/lore_query.py --proj {project} lore "{角色名字}" --n 10`
   - 最近發生的重大事件
   - 角色間的關係變動

4. 從 `config/novel_config.yaml` 讀取：
   - `theme_settings`：確保動機與主題共鳴

## 輸出

更新或產生 `memory/motivation_map.yaml`

```yaml
# 動機地圖 - 每章寫作前自動生成
generated_for_chapter: 5
timestamp: "2026-02-03T10:00:00"

character_motivations:
  - character_id: "CHAR_001"
    name: "李玄"
    
    # 當前活躍動機（可能與 core_desire 不同）
    active_motivation:
      desire: "找到失蹤的妹妹"
      intensity: 85  # 0-100，越高越急迫
      urgency: "high"  # low/medium/high/critical
      
    # 阻礙因素（為什麼還沒達成）
    blocking_factors:
      - factor: "不知道妹妹的下落"
        severity: "critical"
      - factor: "實力不足以對抗綁架者"
        severity: "major"
        
    # 潛在行動（角色可能採取的行動）
    potential_actions:
      - action: "向情報販子購買消息"
        likelihood: 0.7
        requires: ["金錢", "接觸管道"]
      - action: "冒險潛入敵人據點"
        likelihood: 0.5
        requires: ["實力提升", "情報"]
      - action: "尋求強者庇護換取線索"
        likelihood: 0.3
        requires: ["放下尊嚴"]
        
    # 情緒傾向
    emotional_state:
      primary: "焦慮"
      secondary: "憤怒"
      stability: 40  # 越低越不穩定

    # 存在感調變（情緒→物理表現）
    presence_modulation:
      base: "靠牆站著，指尖敲大腿"
      焦慮: "不停走動，手插口袋又抽出來"
      憤怒: "站得很直，下巴繃緊，手垂在身側不動"
      放鬆: "癱在椅子上，腳翹桌面，手指轉筆"

    # 與主題的共鳴
    theme_resonance:
      theme: "權力的代價"
      connection: "為了救妹妹，願意付出什麼代價？"

# 衝突節點（多角色動機交叉時的爆發點）
conflict_nodes:
  - id: "CONFLICT_001"
    type: "goal_clash"  # goal_clash / value_clash / resource_competition
    participants: ["CHAR_001", "CHAR_003"]
    
    description: "李玄想獲得情報，但情報販子索要的代價是背叛盟友"
    
    stakes:
      if_char_001_wins: "獲得妹妹下落，但失去盟友信任"
      if_char_003_wins: "保住秘密，但李玄可能採取極端手段"
      
    tension_level: 75
    ready_to_trigger: true  # 達到閾值，可以在本章觸發
    
    possible_outcomes:
      - outcome: "李玄妥協，用其他方式支付"
        probability: 0.4
        consequence: "拖延時間，但保持道德底線"
      - outcome: "李玄接受交易，背叛盟友"
        probability: 0.3
        consequence: "加速劇情，但角色墮落"
      - outcome: "李玄用武力逼問"
        probability: 0.3
        consequence: "短期有效，但結下大敵"

# 關係張力（達到閾值可能爆發的關係）
relationship_tensions:
  - source: "CHAR_001"
    target: "CHAR_002"
    current_tension: 65
    threshold: 70  # 達到此值會自動觸發關係事件
    
    underlying_issue: "CHAR_002 曾見死不救"
    surface_status: "表面合作"
    
    potential_trigger: "當 CHAR_001 再次需要 CHAR_002 幫助時"
    
    if_triggered:
      confrontation_type: "質問與爆發"
      possible_resolutions:
        - "真相大白，誤會解開"
        - "決裂，成為敵人"
        - "冷戰，關係降級"

# 場景建議（基於動機分析的自動建議）
scene_suggestions:
  - suggestion: "本章可以觸發 CONFLICT_001"
    reason: "李玄的焦慮已達 85，會更容易做出極端選擇"
    theme_fit: "呼應『權力的代價』主題"
    
  - suggestion: "可以安排 CHAR_001 和 CHAR_002 的深度對話"
    reason: "關係張力接近閾值（65/70），但未到爆發點"
    purpose: "為後續衝突埋下伏筆"
```

## 執行步驟

### Step 1: 載入角色當前狀態

```yaml
讀取所有 Protagonist/Antagonist/Supporting 角色:
  - base_profile（固定設定）
  - current_state（動態狀態）
  - 最近的行動記錄（from ChromaDB lore_bank）
```

### Step 2: 計算動機強度

```
對於每個角色 {{character}}：

你是一位角色心理學專家。
請根據以下資料，分析角色的當前動機狀態：

【角色基本設定】
- 核心慾望：{{core_desire}}
- 核心恐懼：{{fear}}
- 性格特質：{{traits}}

【當前狀態】
- 最後出現章節：{{last_chapter}}
- 當前位置：{{location}}
- 情緒狀態：{{emotional_state}}
- 最近經歷的事件：{{recent_events}}

【劇情情境】
- 當前 Arc 主題：{{arc_summary}}
- 當前 SubArc 目標：{{subarc_summary}}

請輸出：
1. **active_motivation**：當前最迫切的動機是什麼？
2. **intensity**：動機強度（0-100）
3. **blocking_factors**：什麼阻止他達成目標？
4. **potential_actions**：他可能採取什麼行動？
5. **emotional_state**：當前情緒傾向
6. **presence_modulation**：角色的物理表現如何隨情緒變化？
   輸出一組情緒→存在感的對照表（至少涵蓋本章可能經歷的情緒）：
   ```yaml
   presence_modulation:
     base: "靠牆站著，指尖敲大腿"          # 預設（來自 DB presence）
     焦慮: "不停走動，手插口袋又抽出來"
     憤怒: "站得很直，下巴繃緊，手垂在身側不動"
     放鬆: "癱在椅子上，腳翹桌面，手指轉筆"
   ```
   場景內角色情緒會多次轉變，寫作 skill 依當下情緒選用對應的 presence 表現
```

### Step 3: 識別衝突節點

```
你是一位劇情衝突設計師。
請根據以下角色動機，識別可能的衝突節點：

【角色動機列表】
{{motivation_list}}

【衝突類型】
- goal_clash：目標直接衝突（兩人都想要同一件東西）
- value_clash：價值觀衝突（對與錯的不同判斷）
- resource_competition：資源競爭（有限資源的爭奪）
- loyalty_conflict：忠誠衝突（同時效忠於對立方）
- trust_crisis：信任危機（懷疑與猜忌）

請輸出所有可能的衝突節點，包括：
1. 參與者
2. 衝突類型
3. 具體描述
4. 可能的結果
5. 張力等級
6. 是否已達觸發條件
```

### Step 4: 分析關係張力

```
對於每對有互動記錄的角色：

請分析 {{char_a}} 和 {{char_b}} 的當前關係張力：

【關係歷史】
- 初始關係：{{initial_relation}}
- 關係變化記錄：{{relationship_changes}}

【各自動機】
- {{char_a}} 的動機：{{motivation_a}}
- {{char_b}} 的動機：{{motivation_b}}

請評估：
1. 當前張力等級（0-100）
2. 潛在的爆發點
3. 可能的觸發條件
4. 爆發後的可能走向
```

### Step 5: 生成場景建議

```
基於以上分析，請提供 2-3 個場景建議：

考慮因素：
1. 哪些衝突節點已經成熟？
2. 哪些關係張力接近閾值？
3. 哪些角色的動機最急迫？
4. 如何與當前主題呼應？

輸出格式：
- 建議內容
- 建議理由
- 與主題的關聯
```

### Step 6: 寫入 motivation_map.yaml

將分析結果結構化後寫入 `memory/motivation_map.yaml`

## 與其他 Skill 的關聯

- **被呼叫於**：
  - `nvChapter` 的 Step 1.5 之後（連貫性上下文載入後）
  - 作為 `chapter_beater` 的前置輸入

- **輸入來源**：
  - 角色資料庫（SQLite, via `char_query.py`）
  - ChromaDB `lore_bank` collection
  - `narrative_progress.yaml`

- **輸出被使用於**：
  - `chapter_beater`：用衝突節點設計節拍
  - `scene_writer`：角色行為有動機依據
  - `dialogue_director`：對話反映角色動機

## 與主題追蹤的整合

動機引擎會自動檢查角色動機與 `theme_settings` 的關聯：

```yaml
若 theme_settings.enabled == true:
  對於每個角色動機:
    - 分析動機如何與 primary_theme 產生共鳴
    - 記錄在 theme_resonance 欄位
    - 在 scene_suggestions 中優先建議與主題相關的衝突
```

## 觸發閾值說明

| 閾值 | 含義 | 建議處理 |
|------|------|----------|
| intensity >= 80 | 角色極度迫切 | 本章內應有相關行動 |
| tension >= 70 | 關係即將爆發 | 可安排對質/衝突 |
| conflict.ready_to_trigger | 衝突條件成熟 | 可在本章觸發 |

## 注意事項

1. **不強制觸發**：建議僅供參考，最終由大綱和用戶 direction 決定
2. **保持一致性**：動機變化要有事件支撐，不能無端改變
3. **避免過度分析**：次要角色只需簡單記錄，不用完整分析
4. **與 chaos_engine 配合**：低機率事件可能打破預期動機鏈
5. **更新頻率**：每章執行一次，重大事件後立即更新

## 範例輸出

```yaml
# 範例：霓虹劍仙 第5章前的動機地圖

character_motivations:
  - character_id: "CHAR_001"
    name: "李玄"
    active_motivation:
      desire: "破解加密硬盤中父親的遺留信息"
      intensity: 70
    blocking_factors:
      - factor: "缺乏高級解密設備"
        severity: "major"
    potential_actions:
      - action: "尋找黑市解密專家"
        likelihood: 0.6
      - action: "潛入企業數據中心"
        likelihood: 0.4
    emotional_state:
      primary: "困惑"
      secondary: "思念"
    theme_resonance:
      theme: "真相與記憶"
      connection: "父親的遺產代表著李玄對過去的執念"

conflict_nodes:
  - id: "CONFLICT_C5_01"
    type: "resource_competition"
    participants: ["CHAR_001", "CHAR_003"]
    description: "李玄需要解密專家，但專家已被對手預約"
    tension_level: 60
    ready_to_trigger: true

scene_suggestions:
  - suggestion: "安排李玄與解密專家的談判場景"
    reason: "動機強度達70，且存在資源競爭衝突"
    theme_fit: "呼應『真相與記憶』主題"
```
