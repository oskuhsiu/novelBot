---
name: outline_architect
description: 大綱建築師 - 根據 Arc-SubArc 結構規劃全書大綱
---

# 大綱建築師 (Outline Architect)

## 功能概述

此 Skill 負責規劃小說的整體結構，使用 **Arc-SubArc-Chapter** 三層架構：
- **Arc（大綱/卷）**：故事的主要分段，預設 10 個
- **SubArc（細目/情節點）**：每個 Arc 內的具體情節，預設每卷 5~10 個
- **Chapter（章節）**：根據 pacing_pointer 動態生成，每章內有自己的 beats

> [!IMPORTANT]
> **術語區分**
> - **SubArc**：Arc 下的細目，代表一個完整情節段落
> - **Beat**：Chapter 內的場景節拍，由 chapter_beater 生成
> 
> 兩者層級不同，請勿混淆！

## 核心概念

### 三層架構

```
Arc 1: 開篇
├── SubArc 1.1: 主角訪視 (pacing: 0.2 → 需 5 章)
│     ├── Chapter 1 (內有 5-8 個 beats)
│     ├── Chapter 2
│     └── ...
├── SubArc 1.2: 觸發事件 (pacing: 0.5 → 需 2 章)
└── SubArc 1.3: 踏上旅程 (pacing: 1.0 → 需 1 章)

Arc 2: 試煉
├── SubArc 2.1: 第一次考驗
...
```

### 章節數計算

```
單個 SubArc 的章節數 = 1 / subarc.pacing_pointer (或 arc.pacing_pointer 或 全域 pacing_pointer)
總章節數 = Σ(每個 SubArc 的章節數)
```

例如：
- 10 個 Arc × 8 個 SubArc = 80 個 SubArc
- pacing_pointer = 0.5 → 每個 SubArc 約 2 章
- 總章節數 ≈ 160 章

## 輸入

1. 從 `config/novel_config.yaml` 讀取：
   - `style_profile`：類型與風格
   - `engine_settings.pacing_pointer`：全域速度指針
   - `structure.arcs`：大綱數量（預設 10）
   - `structure.subarcs_per_arc`：每卷細目數（預設 5~10）

2. 從 `config/character_db.yaml` 讀取：
   - 主要角色的 `core_desire` 和 `fear`

## 輸出

更新 `config/narrative_progress.yaml` 的 `arcs` 區塊

## 執行步驟

### Step 1: 讀取設定
```yaml
# 從 config/novel_config.yaml 讀取
structure:
  arcs: {{arc_count}}              # 預設 10
  subarcs_per_arc: {{subarc_range}} # 預設 "5~10"

engine_settings:
  pacing_pointer: {{global_pacing}} # 預設 0.5
```

### Step 2: 選擇結構模型
```
根據 {{genre}} 和 arc 數量，分配結構節點：

【三幕式分配】（10 個 Arc 為例）
- Arc 1-2：第一幕（開端）20%
- Arc 3-7：第二幕（發展）50%
- Arc 8-10：第三幕（結局）30%

【英雄旅程分配】（12 階段）
映射到 Arc 數量，確保關鍵節點落在合適位置

【關鍵節點】
- 觸發事件：Arc 1 內
- 第一幕結尾：Arc 2 結尾
- 中點大轉折：約 Arc 5
- 最黑暗時刻：約 Arc 8
- 高潮：Arc 9-10
```

### Step 3: 生成 Arc 大綱
```
你是一位資深的小說策劃。
請根據以下設定，規劃 {{arc_count}} 個 Arc：

【類型】：{{genre}}
【主角核心慾望】：{{protagonist_desire}}
【主角最大恐懼】：{{protagonist_fear}}

對於每個 Arc，請輸出：
1. **arc_id**：編號
2. **title**：卷名（吸引力標題）
3. **summary**：本卷核心主題（1-2 句）
4. **emotion_arc**：情感走向（如：緊張→釋然→震驚）
5. **structure_role**：在整體結構中的功能
6. **pacing_pointer**（可選）：若此卷需要特殊節奏，指定覆蓋值
```

### Step 4: 為每個 Arc 生成 SubArcs
```
對於 Arc {{arc_id}}：{{arc_title}}

請生成 {{subarc_count}} 個 SubArc（依據 subarcs_per_arc 範圍）：

【Arc 摘要】：{{arc_summary}}
【前一個 Arc 結尾】：{{previous_arc_ending}}
【下一個 Arc 開頭】：{{next_arc_beginning}}

對於每個 SubArc，請輸出：
1. **id**：A{arc_id}_S{subarc_num}（如 A1_S3）
2. **summary**：本細目核心事件（1 句話）
3. **characters**：出場角色 ID
4. **location**：場景地點
5. **emotion_shift**：情緒變化（如：平靜→緊張）
6. **hook**：結尾鉤子（讓讀者想繼續）
7. **pacing_pointer**（可選）：若此細目需要特殊節奏

確保：
- 首個 SubArc 銜接前一 Arc
- 末個 SubArc 設下懸念，引向下一 Arc
- 各 SubArc 之間有邏輯遞進
```

### Step 5: 寫入 narrative_progress.yaml

```yaml
# Narrative Progress - 劇情進度

progress:
  current_arc: 1
  current_subarc_id: "A1_S1"
  current_chapter: 1
  chapters_written: 0
  words_written: 0

arcs:
  - arc_id: 1
    title: "..."
    summary: "..."
    emotion_arc: "..."
    structure_role: "..."
    pacing_pointer: null  # 使用全域，或指定覆蓋值
    subarcs:
      - id: "A1_S1"
        summary: "..."
        characters: ["CHAR_001"]
        location: "..."
        emotion_shift: "..."
        hook: "..."
        pacing_pointer: null
        chapters: []  # 執行時動態填入
        is_completed: false
    is_completed: false
```

## 大綱範例

```yaml
arcs:
  - arc_id: 1
    title: "頻段錯誤"
    summary: "主角捲入黑市陰謀，被迫踏上逃亡之路"
    emotion_arc: "平靜→緊張→決心"
    structure_role: "開篇 + 觸發事件"
    pacing_pointer: 0.3  # 慢節奏開場，建立世界觀
    subarcs:
      - id: "A1_S1"
        summary: "黑市交易被突襲打斷"
        characters: ["CHAR_001"]
        location: "聽劍閣地下層"
        emotion_shift: "平靜→驚恐"
        hook: "神秘女子出現"
        pacing_pointer: 0.2  # 特別慢，細膩鋪陳
        
      - id: "A1_S2"
        summary: "與神秘女子暫時結盟逃亡"
        characters: ["CHAR_001", "CHAR_002"]
        location: "鏽城管道網"
        emotion_shift: "驚恐→警惕"
        hook: "發現追兵不是衝著他來"
```

## pacing_pointer 優先級

```
SubArc.pacing_pointer > Arc.pacing_pointer > 全域 pacing_pointer
```

當計算某個 SubArc 需要多少章時：
1. 先檢查 SubArc 是否有指定 pacing_pointer
2. 若無，使用 Arc 的 pacing_pointer
3. 若無，使用 config 中的全域 pacing_pointer

## 章節動態生成

章節不在規劃階段產生，而是在 `/nvChapter` 執行時：
1. 讀取當前 SubArc
2. 確定該 SubArc 的有效 pacing_pointer
3. 計算需要多少章完成此 SubArc
4. 使用 `skill_chapter_beater` 為章節生成內部 beats
5. 使用 `skill_scene_writer` 撰寫正文

## 使用時機

- **創世階段**：完成世界觀和角色後
- **調整方向**：劇情需要大幅調整時
- **延長故事**：需要增加 Arc 時

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `skill_character_forge`：需要角色動機
  - `skill_world_builder`：需要場景資訊
- **後續 Skill**：
  - `skill_chapter_beater`：為章節生成內部 beats
  - `skill_pacing_calculator`：計算實際章節數

## 注意事項

1. **Arc 是骨架，SubArc 是肌肉**：Arc 決定大方向，SubArc 決定具體發展
2. **預留彈性**：不要把每個細節都寫死
3. **情感曲線**：確保讀者情緒有起伏
4. **伏筆意識**：在 Arc 規劃時就考慮埋設與回收
5. **局部調速**：用 pacing_pointer 讓重要段落有足夠篇幅展開
