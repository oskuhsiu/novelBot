---
name: emotional_wave_analyzer
description: 情感能量監測器 - 追蹤情感波段，自動調節張力節奏
---

# Emotional Wave Analyzer

情感能量監測器 - 追蹤情感波段，自動調節張力節奏。

## 功能說明

監控章節的情感強度，當連續高壓章節過多時，自動建議或強制插入緩衝點。

## 設定參數

在 `novel_config.yaml` 中加入以下設定：

```yaml
emotion_settings:
  # 是否啟用情感監控
  enabled: true
  
  # 高壓閾值（0-100），超過此值被視為「高壓」
  high_tension_threshold: 70
  
  # 低壓閾值（0-100），低於此值被視為「低壓」
  low_tension_threshold: 30
  
  # 連續高壓容許上限（章）
  max_consecutive_high: 3
  
  # 連續低壓容許上限（章）
  max_consecutive_low: 2
  
  # 自動插入緩衝的模式：suggest（建議）/ force（強制）
  buffer_mode: "suggest"
  
  # 情感類型權重
  emotion_weights:
    action: 0.8      # 動作場面的張力貢獻
    dialogue: 0.3    # 對話的張力貢獻
    internal: 0.5    # 內心戲的張力貢獻
    romance: 0.4     # 感情戲的張力貢獻
    mystery: 0.6     # 懸疑元素的張力貢獻
```

## 使用方式

### 在 Workflow 中調用

章節寫作完成後，調用此 Skill 進行情感分析：

```
1. 讀取最近 N 章的情感數據
2. 分析當前章節的情感強度
3. 判斷是否觸發閾值
4. 輸出建議或強制調整
```

## 執行邏輯

### Step 1: 計算章節情感強度

分析章節內容，計算綜合情感值：

```python
def calculate_tension(chapter_content, emotion_weights):
    scores = {
        'action': count_action_scenes(chapter_content) * emotion_weights['action'],
        'dialogue': count_intense_dialogues(chapter_content) * emotion_weights['dialogue'],
        'internal': count_internal_monologue(chapter_content) * emotion_weights['internal'],
        'romance': count_romance_scenes(chapter_content) * emotion_weights['romance'],
        'mystery': count_mystery_elements(chapter_content) * emotion_weights['mystery'],
    }
    return min(100, sum(scores.values()))
```

### Step 2: 追蹤情感歷史

維護情感歷史記錄於 `memory/emotion_log.yaml`：

```yaml
emotion_history:
  chapter_1:
    tension_score: 45
    category: "medium"
    main_emotions: ["緊張", "好奇"]
    
  chapter_2:
    tension_score: 78
    category: "high"
    main_emotions: ["恐懼", "憤怒"]
    
  chapter_3:
    tension_score: 85
    category: "high"
    main_emotions: ["絕望", "戰鬥"]
    
  # 連續3章高壓，觸發警告
```

### Step 3: 閾值檢測

```yaml
detection_logic:
  # 連續高壓檢測
  if consecutive_high >= max_consecutive_high:
    trigger: "HIGH_TENSION_OVERLOAD"
    action: "建議下一章降低張力"
    
  # 連續低壓檢測
  if consecutive_low >= max_consecutive_low:
    trigger: "LOW_TENSION_STAGNATION"
    action: "建議下一章提升張力"
    
  # 極端波動檢測
  if abs(current_tension - previous_tension) > 50:
    trigger: "EMOTIONAL_WHIPLASH"
    action: "建議增加過渡場景"
```

### Step 4: 輸出建議

**suggest 模式**（預設）：
```
⚠️ 情感波段警告
連續 3 章高壓（平均張力 82）
建議下一章加入情感緩衝場景：
- 日常對話（降低 action 權重）
- 角色獨處反思（增加 internal）
- 輕鬆互動（加入幽默元素）
```

**force 模式**：
```
🔒 情感調節強制啟動
根據設定，自動調整下一章的 content_weights：
- combat: 0.5 → 0.1
- dialogue: 0.2 → 0.4
- internal_monologue: 0.1 → 0.3
```

## 與其他 Skill 的連動

1. **nvChapter**：寫作完成後自動調用分析
2. **skill_beat_optimizer**：根據情感建議調整 beats
3. **skill_pacing_calculator**：高壓狀態下自動放慢節奏
4. **skill_chaos_engine**：低壓狀態下可能觸發突發事件

## 輸出格式

```yaml
emotion_analysis:
  chapter: 15
  tension_score: 85
  category: "high"
  
  history_summary:
    last_3_chapters: [78, 82, 85]
    trend: "持續上升"
    consecutive_high: 3
    
  warning:
    triggered: true
    type: "HIGH_TENSION_OVERLOAD"
    
  recommendations:
    - type: "reduce_action"
      priority: "high"
      description: "下一章減少戰鬥場景"
    - type: "add_breathing_room"
      priority: "medium"
      description: "加入日常或反思場景"
      
  next_chapter_adjustment:
    suggested_weights:
      combat: 0.1
      dialogue: 0.4
      internal_monologue: 0.3
      scenery_desc: 0.2
```
