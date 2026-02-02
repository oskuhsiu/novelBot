---
name: chapter_beater
description: 章節拆解師 - 將章節大綱拆解為具體的場景節拍 (Beats)
---

# 章節拆解師 (Chapter Beater)

## 功能概述

此 Skill 將「一章」的大綱摘要拆解為具體的「情節節拍（Beats）」。節拍是最小的敘事單位，是 Scene Writer 實際執行的指令。

## 輸入

1. 從 `templates/narrative_progress.yaml` 讀取：
   - 當前章節的 `summary`
   - 上一章的結尾狀態

2. 從 `templates/novel_config.yaml` 讀取：
   - `engine_settings.pacing_pointer`
   - `engine_settings.content_weights`

3. 從角色和世界資料庫讀取相關資訊

## 輸出

更新 `templates/narrative_progress.yaml` 中當前章節的 `beats` 陣列

## 執行步驟

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
```

### Step 2: 生成場景節拍
```
你是一位精通場景設計的劇本師。
請將以下章節摘要拆解為 {{beat_count}} 個具體的場景節拍：

【章節摘要】：{{summary}}
【情感目標】：{{emotion_goal}}
【參與角色】：{{available_characters}}
【可用場景】：{{available_locations}}

## 節拍設計

對於每個節拍，請輸出：

1. **節拍 ID**：如 B1_1, B1_2
2. **場景地點**：具體到房間或區域
3. **出場人物**：誰在場
4. **發生什麼事 (Action)**：
   - 外在動作（看得見的事件）
   - 角色互動類型（對話/衝突/合作/etc.）
5. **情緒轉折 (Reaction)**：
   - 角色情緒從 A 到 B 的變化
   - 如：「從自信到動搖」「從敵意到理解」
6. **信息揭露**：這個節拍揭露什麼資訊（可選）
7. **鉤子 (Hook)**：這個節拍結尾留下什麼懸念

確保節拍之間有邏輯連接。
```

### Step 3: 設定權重暗示
```
根據 {{content_weights}} 和章節需求，
為每個節拍設定 weight_hint（如果需要覆蓋全域權重）：

## 權重考量

- 若此節拍是「關鍵對話」，設定 dialogue: 0.6+
- 若此節拍是「戰鬥場面」，設定 combat: 0.5+
- 若此節拍是「環境探索」，設定 scenery_desc: 0.4+
- 若此節拍是「心理描寫」，設定 internal_monologue: 0.4+

大部分節拍使用全域權重即可（weight_hint: null）
```

### Step 4: 寫入 narrative_progress.yaml
```yaml
beats:
  - id: "B1_1"
    summary: "..."
    location: "..."
    characters: [...]
    action: "..."
    emotion_shift: "..."
    info_reveal: "..."
    hook: "..."
    weight_hint: null
    status: "pending"
```

## 節拍範例

```yaml
beats:
  - id: "B1_1"
    summary: "黑市交易現場的環境與氣氛鋪陳"
    location: "聽劍閣地下層 - 黑市交易區"
    characters: ["CHAR_001"]
    action: "主角穿過擁擠的黑市，觀察環境，抵達交易點"
    emotion_shift: "平靜 → 警覺"
    info_reveal: "展示這個世界的地下經濟面貌"
    hook: "神秘交易對象遲到了"
    weight_hint: "scenery_desc: 0.4"
    status: "pending"

  - id: "B1_2"
    summary: "與神秘人的硬盤交接"
    location: "聽劍閣地下層 - 私密包廂"
    characters: ["CHAR_001", "NPC_MYSTERIOUS"]
    action: "交易進行，但硬盤讀取時出現異常數據脈衝"
    emotion_shift: "警覺 → 疑惑 → 緊張"
    info_reveal: "硬盤中似乎藏有預期之外的東西"
    hook: "門外傳來騷動，似乎是執法隊"
    weight_hint: "dialogue: 0.5"
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

## 使用時機

- **章節開始前**：將大綱轉化為可執行的節拍
- **調整節奏**：當需要改變某章的詳細程度時

## 與其他 Skill 的關聯

- **前置 Skill**：
  - `skill_outline_architect`：需要章節大綱
  - `skill_pacing_calculator`：需要節奏計算
- **後續 Skill**：
  - `skill_beat_optimizer`：優化節拍張力
  - `skill_scene_writer`：執行節拍寫作

## 注意事項

1. **節拍不是正文**：節拍是指令，不是最終文字
2. **保持靈活**：執行時可以根據實際情況調整
3. **情緒曲線**：確保節拍之間的情緒有起伏
4. **信息節奏**：不要在一個節拍塞太多信息
5. **留白**：有些節拍可以故意簡略，讓寫作時有發揮空間
