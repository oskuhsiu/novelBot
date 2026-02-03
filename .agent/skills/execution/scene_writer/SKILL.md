---
name: scene_writer
description: 正文生成器 - 根據節拍指令撰寫正文，遵循風格指南與內容權重
---

# 正文生成器 (Scene Writer)

## 功能概述

此 Skill 是實際產生小說正文的核心工具。它根據節拍（Beat）的指令，結合風格指南、角色設定和內容權重，撰寫符合要求的文字。

## 核心原則

1. **展示而非講述 (Show, Don't Tell)**：用行動和細節呈現，而非直接描述
2. **風格一致**：嚴格遵循 style_guide.md 的規範
3. **角色一致**：對白和行為須符合角色的 base_profile
4. **權重遵循**：內容比例符合 content_weights

## 輸入

1. **節拍資訊**（從 narrative_progress.yaml）：
   - `summary`：本節拍要寫什麼
   - `location`：場景地點
   - `characters`：出場角色
   - `action`：發生的事件
   - `emotion_shift`：情緒變化
   - `enhancement_notes`：強化建議

2. **風格指南**（從 output/style_guide.md）

3. **角色資料**（從 character_db.yaml）

4. **內容分配**（從 weight_balancer 計算結果）

5. **連貫性上下文**（從 nvChapter Step 1.5 傳入）：
   - `continuity_context.current_subarc_summary`：當前次網摘要
   - `continuity_context.previous_chapters_in_subarc`：同一次網已有章節摘要
   - `continuity_context.previous_subarc_ending`：上一次網結尾
   - **`continuity_context.arc_boundary`**：跨 Arc 資訊（若適用）
     - `is_new_arc`：是否為新 Arc 的第一章
     - `previous_arc_ending`：前一卷的結尾摘要

6. **劇情導引**（可選，從參數傳入）：
   - `direction`：使用者指定的劇情走向

## 輸出

正文段落，寫入 `output/chapters/chapter_XX.md`

## 執行步驟

### Step 1: 準備上下文
```
讀取當前節拍：{{beat}}
讀取風格指南：{{style_guide}}
讀取角色資料：{{characters}}
讀取上一節拍結尾：{{previous_ending}}
讀取內容分配：{{content_allocation}}
```

### Step 2: 生成正文
```
你是一位 {{awards}} 獲獎的小說家。
請根據以下指令撰寫正文：

## 基本資訊
【場景】：{{location}}
【出場角色】：{{characters_info}}
【前情】：{{previous_context}}

## 連貫性上下文（必讀）

【當前次網摘要】：{{current_subarc_summary}}
【同一次網前章摘要】：
{{previous_chapters_in_subarc}}

【上一次網結尾】：
{{previous_subarc_ending}}

## 劇情導引（若有）
{{direction}}

> 若有 direction，正文內容必須朝指定方向發展。
> 第一個節拍必須銜接前章結尾，確保讀者無縫閱讀。

## 本節拍要求
【事件】：{{action}}
【情緒轉折】：{{emotion_shift}}
【鉤子】：{{hook}}

## 風格要求
{{style_requirements}}

## 內容分配
- 對話：約 {{dialogue_percent}}%
- 動作/戰鬥：約 {{action_percent}}%
- 環境描寫：約 {{scenery_percent}}%
- 內心活動：約 {{internal_percent}}%

## 寫作指引
{{enhancement_notes}}

## 注意事項
1. 展示而非講述
2. 多用具體、感官的細節
3. 對話要符合角色性格
4. 動作要有動詞力量
5. 適時穿插不同類型的內容
6. **銜接前章**：若有前章內容，需自然銜接
7. **依循導引**：若有 direction，確保劇情朝該方向發展

目標字數：{{target_words}} 字

請開始撰寫：
```

### Step 3: 品質檢查
```
請檢查剛才寫的段落：

1. 【風格一致】是否符合 {{genre}} 的類型特色？
2. 【角色聲音】每個角色的語氣是否可區分？
3. 【節奏】是否有長短句交替？
4. 【感官】是否包含具體的感官細節？
5. 【鉤子】結尾是否留有懸念或張力？

如有問題，請修正。
```

### Step 4: 輸出正文
寫入章節檔案，並記錄元數據

## 正文範例

輸入節拍：
```yaml
id: "B1_1"
summary: "黑市交易現場的環境與氣氛鋪陳"
location: "聽劍閣地下層 - 黑市交易區"
characters: ["CHAR_001"]
action: "主角穿過擁擠的黑市，觀察環境，抵達交易點"
emotion_shift: "平靜 → 警覺"
enhancement_notes:
  - "加入聲音細節：叫賣聲、機械嗡響"
  - "描寫氣味：油煙、廉價香水"
```

輸出正文：
```markdown
霓虹燈的冷光從天花板滲落，給整片地下市場染上一層病態的青紫。
李玄側身閃過一個推著懸浮貨車的販子，鏽跡斑斑的金屬輪廓貼著
他的風衣擦過。

「煉神丹——三折！買二送一！」叫賣聲從左側傳來。
「新到的築基防火牆，只要一千信用幣——」右邊有人敲打著全息
看板。

空氣裡混著油煙、廉價香水和某種金屬灼燒的刺鼻味。電子義眼
自動過濾掉刺目的廣告投影，只留下必要的路徑標識。

他的腳步沒有停頓，但感官已經全面張開。

「108號雅間。」耳機裡傳來線人的聲音。

左眼的戰鬥輔助程序閃過一串分析：前方走廊，2個可疑熱源，
武器信號微弱。不是執法隊。

李玄右手無意識地觸碰了一下胸口，那裡，折疊飛劍正維持著
待機狀態。
```

## 特殊場景處理

### 戰鬥場景
```
【追加指令】
1. 動作要有動詞力量，避免「進行戰鬥」這種抽象描述
2. 每個招式包含：起手→運轉→效果
3. 穿插戰術思考（1-2句）
4. 描寫物理後果（破壞、傷口）
5. 根據 pacing 決定詳細程度
```

### 對話密集場景
```
【追加指令】
1. 減少「他說」「她說」
2. 用動作標記代替說話標籤
3. 每 3-4 句對話穿插一個動作或環境描寫
4. 對話要有潛台詞
5. 不同角色的用詞要有區別
```

### 獨處內心場景
```
【追加指令】
1. 避免純粹的意識流
2. 用當下的感官錨定
3. 內心活動要有具體的意象
4. 適時被外部刺激打斷
```

## 使用時機

- **章節寫作**：每個節拍呼叫一次
- **重寫優化**：對已有段落進行改寫

## 與其他 Skill 的關聯

- **前置**：
  - `skill_pacing_calculator`：決定詳細程度
  - `skill_weight_balancer`：決定內容比例
  - `skill_beat_optimizer`：提供強化建議
- **協作**：
  - `skill_dialogue_director`：優化對話
  - `skill_sensory_amplifier`：強化感官
- **後續**：
  - `skill_logic_auditor`：檢查邏輯衝突

## 注意事項

1. **不要過度描寫**：只描寫對劇情有意義的細節
2. **動作要有意義**：每個動作都應該推進劇情或揭示性格
3. **避免重複**：不要用不同的話說同一件事
4. **保持懸念**：每個節拍結尾都應該讓讀者想繼續
5. **字數彈性**：±15% 是可接受的範圍

## 字數強制要求

> [!IMPORTANT]
> **每章最低字數：3000 字**
> **每節拍最低字數：500 字**
> 
> 若完成所有節拍後總字數不足：
> 1. 擴充感官描寫和環境細節
> 2. 加入角色心理活動
> 3. 豐富對話內容和潛台詞
> 4. 細化動作過程
> 
> **不可縮減節拍數量來達標**
