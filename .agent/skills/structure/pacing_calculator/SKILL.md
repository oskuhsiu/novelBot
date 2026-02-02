---
name: pacing_calculator
description: 速度指針計算器 - 根據 pacing_pointer 計算本章應涵蓋的內容範圍
---

# 速度指針計算器 (Pacing Calculator)

## 功能概述

此 Skill 負責根據 `pacing_pointer` 計算本章應該涵蓋多少劇情內容。它是控制故事節奏的核心工具，決定敘事的「快」或「慢」。

## 核心概念

### pacing_pointer 定義
- **1.0**：一章完成一個細目（快節奏，事件密集）
- **0.5**：兩章完成一個細目（中等節奏）
- **0.1**：十章完成一個細目（慢節奏，細膩展開）

### 計算公式
```
本章應完成的細目數 = pacing_pointer × 基礎細目數（通常為 1）
本節拍需展開的字數 = words_per_chapter × pacing_pointer
```

## 輸入

1. 從 `templates/novel_config.yaml` 讀取：
   - `engine_settings.pacing_pointer`
   - `engine_settings.content_weights`

2. 從 `templates/narrative_progress.yaml` 讀取：
   - `progress.current_chapter`
   - `progress.current_beat_id`
   - 當前章節的 `beats` 列表

## 輸出

計算結果，提供給其他 Skill 使用：
- 本章應完成的節拍數量
- 每個節拍的建議字數
- 內容詳細程度指引

## 執行邏輯

### Step 1: 讀取當前狀態
```
讀取 pacing_pointer：{{pacing_pointer}}
讀取當前節拍：{{current_beat_id}}
讀取剩餘節拍列表：{{remaining_beats}}
```

### Step 2: 計算本章內容範圍
```
## 計算公式

【慢節奏模式】pacing_pointer < 0.3
- 本章完成 1 個節拍
- 節拍展開為 5-10 個微場景
- 注重：感官描寫、心理活動、環境細節
- 字數分配：每個微場景 800-1500 字

【中節奏模式】0.3 ≤ pacing_pointer ≤ 0.7
- 本章完成 2-3 個節拍
- 每個節拍為 1 個完整場景
- 平衡：動作、對話、描寫
- 字數分配：每個節拍 2000-3000 字

【快節奏模式】pacing_pointer > 0.7
- 本章完成 4+ 個節拍
- 多個場景快速切換
- 重點：動作、對話、事件
- 字數分配：每個節拍 1000-1500 字
```

### Step 3: 產生詳細程度指引
```
根據 pacing_pointer = {{pacing_pointer}}，請給出寫作指引：

## 描寫深度
- 環境描寫：{{scenery_detail_level}}
- 心理描寫：{{psychology_detail_level}}
- 動作描寫：{{action_detail_level}}
- 對話密度：{{dialogue_density}}

## 時間密度
- 敘事時間：本章涵蓋 {{narrative_time}} 的故事時間
- 實時比例：1 字 ≈ {{time_per_word}} 故事時間

## 展開方式
慢節奏（0.1）：
- 一個簡單動作可以寫成一段
- 每個感官都可以細寫
- 角色的每個念頭都可以展開

快節奏（1.0）：
- 多個動作壓縮成一句
- 只寫最關鍵的感官
- 只呈現關鍵決定，省略掙扎過程
```

### Step 4: 輸出計算結果
```yaml
pacing_result:
  chapter_id: {{current_chapter}}
  pacing_pointer: {{pacing_pointer}}
  
  content_allocation:
    beats_to_complete: {{beat_count}}
    starting_beat: "{{current_beat_id}}"
    ending_beat: "{{target_beat_id}}"
    
  writing_guidelines:
    detail_level: "{{low/medium/high}}"
    words_per_beat: {{suggested_words}}
    
  special_notes:
    - "{{any special considerations}}"
```

## 節奏調整範例

### 範例 1：慢節奏戰鬥
```
pacing_pointer: 0.2
節拍：「兩人展開對決」

展開方式：
- 場景 1：對峙（500字）- 環境、雙方站位、氣勢描寫
- 場景 2：試探（800字）- 第一次交鋒，互相試探招式
- 場景 3：認真（1200字）- 開始動真格，幾次交鋒細寫
- 場景 4：轉折（1000字）- 一方佔優或發生意外
- 場景 5：決勝（1500字）- 最後對決，詳細描寫招式

總計：5000字完成一個「對決」節拍
```

### 範例 2：快節奏戰鬥
```
pacing_pointer: 0.9
節拍：「兩人展開對決」

展開方式：
「劍光閃過三次，主角的飛劍被震飛。
敵人的第二擊直取咽喉，他拼盡最後一絲算力啟動離線模式——
刀尖堪堪停在頸側半寸。」

總計：100字概括整場對決
```

## 動態調整

### 局部節奏變化
某些節拍可能需要不同於全域的 pacing：
- `weight_hint` 中可以包含 `local_pacing: 0.3`
- 表示這個節拍需要放慢

### 情節需求覆蓋
- 高潮場景：即使全域快節奏，也應該放慢
- 過渡場景：即使全域慢節奏，也可以加快

## 使用時機

- **章節開始前**：計算本章內容範圍
- **節拍開始前**：確認詳細程度
- **調整節奏時**：重新計算分配

## 與其他 Skill 的關聯

- **讀取自**：`novel_config.yaml`、`narrative_progress.yaml`
- **影響到**：
  - `skill_chapter_beater`：節拍數量
  - `skill_scene_writer`：描寫詳細程度
  - `skill_technique_elaborator`：技能描寫詳細度
  - `skill_sensory_amplifier`：感官描寫程度

## 注意事項

1. **節奏一致性**：同一場景內，節奏應該一致
2. **戲劇需求優先**：關鍵時刻不該因為全域設定而草草帶過
3. **讀者體驗**：持續的慢節奏會讓讀者疲勞
4. **靈活運用**：pacing_pointer 是指引，不是枷鎖
