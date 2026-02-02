---
name: illustrator
description: 插畫與封面生成器 - 根據小說內容生成高品質的圖像提示詞 (Image Prompts)
---

# 插畫師 (Illustrator)

## 功能概述

此 Skill 負責將抽象的小說文字轉換為具體的圖像生成提示詞 (Prompts)。它能理解角色外貌、場景氛圍、光影效果和藝術風格，為 AI 繪圖工具（如 Midjourney, Stable Diffusion 或 DALL-E）提供精準的指令。

## 輸入

可以接受以下類型的輸入：
1. **角色 ID**：從 `character_db.yaml` 讀取外貌描述
2. **場景 ID**：從 `world_atlas.yaml` 讀取環境描述
3. **物品 ID**：從 `item_compendium.yaml` 讀取物品細節
4. **自定義描述**：使用者的直接描述
5. **風格參數**：指定的藝術風格（如：anime, realistic, oil painting）

## 輸出

生成 `generate_image` 工具所需的 Prompt。

## 執行步驟

### Step 1: 讀取基礎資料
```
讀取 config/novel_config.yaml 中的 style_profile，確定整體美術風格。
若輸入為 ID，從對應的 yaml 檔中提取 description, appearance, atmosphere 等關鍵字。
```

### Step 2: 建構畫面元素
```
[主體]：核心角色或物品，詳細描述其特徵（髮色、瞳色、服裝、裝備、動作）。
[環境]：背景細節（地點、天氣、時間、光源）。
[構圖]：鏡頭角度（全身、半身、特寫、廣角）、視線方向。
[氛圍]：情緒基調（恐怖、溫馨、壯闊）。
[風格]：藝術流派、媒介（數位繪圖、水彩）、渲染引擎（Unreal Engine 5, Octane Render）。
```

### Step 3: 優化提示詞 (Prompt Engineering)
```
將描述轉化為英文 Prompt（AI 繪圖通常對英文理解較好）：
- 添加質量修飾詞：highly detailed, 8k resolution, masterpiece, best quality.
- 添加負面提示詞概念（雖然此工具不直接支援負面提示，但在 Prompt 中強調正面特徵以排除負面）。
```

### Step 4: 輸出
```
返回完整的 Prompt 字符串。
```

## Prompt 模板範例

```
(Subject: A goblin warrior with green skin, wearing rusty armor), (Action: holding a sword, standing defensively), (Environment: dark underground mine, bioluminescent mushrooms), (Lighting: cinematic lighting, rim light, dramatic shadows), (Style: dark fantasy, concept art, semi-realistic, detailed texture), (Quality: 8k, masterpiece)
```
