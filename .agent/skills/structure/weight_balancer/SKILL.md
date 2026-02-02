---
name: weight_balancer
description: 權重平衡器 - 讀取 content_weights 分配各類內容的文字比例
---

# 權重平衡器 (Weight Balancer)

## 功能概述

此 Skill 負責根據 `content_weights` 分配章節或節拍中各類內容的文字比例。它確保小說的內容組成符合預期的風格和類型需求。

## 核心概念

### content_weights 定義
每種內容類型的權重（0-1），總和應為 1：
- `combat`：戰鬥描寫
- `dialogue`：對話
- `internal_monologue`：內心獨白
- `scenery_desc`：環境描寫
- `world_building`：世界觀補充
- `action`：動作描寫（非戰鬥）

### 權重轉換
```
實際字數 = 權重 × 節拍總字數
例：combat: 0.5，節拍 2000 字
→ 戰鬥描寫約 1000 字
```

## 輸入

1. 從 `templates/novel_config.yaml` 讀取：
   - `engine_settings.content_weights`

2. 從當前節拍讀取：
   - `weight_hint`（局部覆蓋）
   - `action`（節拍類型）

## 輸出

內容分配方案，提供給 Scene Writer 使用

## 執行邏輯

### Step 1: 讀取權重設定
```
讀取全域權重：{{content_weights}}
讀取節拍的 weight_hint：{{weight_hint}}

若 weight_hint 存在，使用局部覆蓋：
- 僅覆蓋指定的類型
- 其他類型重新按比例分配
```

### Step 2: 分析節拍類型
```
根據節拍的 action 描述，判斷內容類型偏向：

## 節拍類型識別

【戰鬥型】關鍵字：對決、戰鬥、交手、打鬥
→ 傾向提高 combat 權重

【對話型】關鍵字：談話、協商、審問、爭執
→ 傾向提高 dialogue 權重

【探索型】關鍵字：探索、觀察、進入、發現
→ 傾向提高 scenery_desc 權重

【內心型】關鍵字：思考、回憶、掙扎、決定
→ 傾向提高 internal_monologue 權重

【動作型】關鍵字：逃跑、追逐、潛入、操作
→ 傾向提高 action 權重
```

### Step 3: 計算最終分配
```
## 分配計算

基於：
- 全域權重：{{content_weights}}
- 局部覆蓋：{{weight_hint}}
- 節拍類型：{{beat_type}}

產出最終分配：

content_allocation:
  combat: {{final_combat_weight}}
  dialogue: {{final_dialogue_weight}}
  internal_monologue: {{final_internal_weight}}
  scenery_desc: {{final_scenery_weight}}
  world_building: {{final_worldbuilding_weight}}
  action: {{final_action_weight}}

字數分配（總字數 {{total_words}}）：
  combat: {{combat_words}} 字
  dialogue: {{dialogue_words}} 字
  ...
```

### Step 4: 生成寫作指引
```
## 寫作指引

【主要內容】（權重 > 0.3）
- {{primary_type}}：約 {{primary_words}} 字
- 這是本節拍的核心，應該精心雕琢

【次要內容】（0.1 < 權重 < 0.3）
- {{secondary_types}}：各約 {{secondary_words}} 字
- 作為輔助和過渡

【點綴內容】（權重 < 0.1）
- {{minor_types}}：各約 {{minor_words}} 字
- 可以簡略或省略

【融合建議】
- 戰鬥中穿插對話：{{example}}
- 對話中帶入心理：{{example}}
- 動作中嵌入環境：{{example}}
```

## 權重分配範例

### 範例 1：戰鬥重場景
```yaml
# 全域權重
content_weights:
  combat: 0.5
  dialogue: 0.2
  internal_monologue: 0.1
  scenery_desc: 0.15
  action: 0.05

# 節拍：激烈對決
weight_hint: null  # 使用全域

# 結果（2000字）
allocation:
  combat: 1000 字 - 招式交換、傷害描寫、戰術變化
  dialogue: 400 字 - 戰鬥中的嘲諷、吶喊、威脅
  scenery_desc: 300 字 - 戰場環境破壞、天氣
  internal: 200 字 - 瞬間的判斷、恐懼、興奮
  action: 100 字 - 走位、閃避的基礎動作
```

### 範例 2：關鍵對話場景
```yaml
# 全域權重（同上）

# 節拍：交接硬盤時的對話
weight_hint: "dialogue: 0.6"  # 局部覆蓋

# 重新計算後
allocation:
  dialogue: 60% → 1200 字
  combat: 10% → 200 字（緊張氛圍）
  internal: 15% → 300 字
  scenery: 10% → 200 字
  action: 5% → 100 字
```

## 特殊場景處理

### 純對話場景
```
當 dialogue > 0.7 時：
- 減少「他說」「她說」
- 增加動作描寫穿插
- 用環境聲音點綴
```

### 純戰鬥場景
```
當 combat > 0.7 時：
- 避免連續的動作句
- 插入瞬間的心理活動
- 用環境互動增加變化
```

### 沉思場景
```
當 internal_monologue > 0.5 時：
- 用感官錨定現在
- 避免大段意識流
- 穿插外部刺激打斷
```

## 使用時機

- **節拍開始前**：確定內容分配
- **寫作檢查時**：驗證比例是否符合

## 與其他 Skill 的關聯

- **前置**：`skill_pacing_calculator`（確定總字數）
- **輸出到**：`skill_scene_writer`（作為寫作指引）

## 注意事項

1. **權重是指引，不是精確計算**：允許 ±20% 的彈性
2. **自然融合**：內容類型應該自然穿插，不是分段堆砌
3. **戲劇需求優先**：關鍵時刻可以突破權重限制
4. **讀者體驗**：單一類型持續太久會造成疲勞
