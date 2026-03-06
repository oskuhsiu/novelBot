---
name: style_setter
description: 風格定調器 - 讀取專案設定，產生動態寫作指引，定義小說的「文字氣味」
---

# 風格定調器 (Style Setter)

## 功能概述

此 Skill 負責定義小說的敘事風格，是創作的第一步。它會讀取 `novel_config.yaml` 的 `style_profile` 區塊，並產生一份完整的「風格指南」供後續寫作 Skill 參考。

## 輸入

從 `templates/novel_config.yaml` 讀取以下欄位：

```yaml
style_profile:
  genre: ""              # 小說類型
  perspective: ""        # 敘事視角
  tone: ""               # 文字語氣
  reference_authors: []  # 參考作家
  awards: []             # 獲獎獎項
  linguistic_rules: []   # 語言規則
  guide: []              # 風格指南
```

同時讀取：
- `meta.language`: 小說使用的語言

## 輸出

產生或更新 `output/style_guide.md`，包含：

1. **風格定位**：根據 genre 和 tone 描述整體風格走向
2. **視角規範**：根據 perspective 定義敘事限制
3. **語言特色**：根據 linguistic_rules 列出具體寫作要求
4. **參考範例**：模仿 reference_authors 的風格，產生示範段落
5. **禁忌清單**：列出此風格應避免的寫法

## 執行步驟

### Step 1: 讀取設定
```
讀取 templates/novel_config.yaml
提取 style_profile 與 meta.language
```

### Step 2: 分析風格定位
```
你現在是一位獲得 {{awards}} 的頂尖小說家。
請根據以下參數，分析並定義這部小說的敘事風格：

【類型】：{{genre}}
【敘事視角】：{{perspective}}
【文字溫度】：{{tone}}
【參照作家】：{{reference_authors}}
【語言】：{{language}}

請輸出以下內容：
1. 風格特徵總結（50字以內）
2. 適合此風格的句式結構（短句/長句/混合）
3. 修辭手法偏好（比喻/排比/對仗/極簡）
4. 節奏感描述（緊湊/舒緩/張弛有度）
```

### Step 3: 產生語言規範
```
根據以下語言規則，產生具體的寫作規範：

【規則】：
{{linguistic_rules}}

請轉化為可執行的寫作指引，例如：
- 「應該做」：具體的正面範例
- 「避免」：具體的負面範例
```

### Step 4: 撰寫示範段落
```
請以 {{reference_authors}} 的風格，撰寫一段 200 字的示範段落。

情境：主角首次進入一個陌生的危險環境。

要求：
- 展示第 {{perspective}} 的敘事技巧
- 體現 {{tone}} 的文字溫度
- 融入 {{genre}} 的類型特色
```

### Step 5: 輸出風格指南
將上述分析結果整理為 `output/style_guide.md`

## 風格指南範本

```markdown
# 《專案名稱》風格指南

## 基本設定
- **類型**：{{genre}}
- **視角**：{{perspective}}
- **語氣**：{{tone}}
- **參考作家**：{{reference_authors}}

## 風格特徵
{{風格分析結果}}

## 寫作規範
### 應該做
- ...

### 避免
- ...

## 示範段落
{{示範文字}}

---
*此指南由 Style Setter 自動產生，供所有寫作 Skill 參考*
```

## 使用時機

- **創世階段**：新專案初始化時首先執行
- **風格調整**：當需要修改 novel_config.yaml 的 style_profile 後重新執行
- **章節開始前**：每章開始前，其他 Skill 應先讀取風格指南

## 與其他 Skill 的關聯

- **被呼叫於**：`workflow_genesis` 的第一步
- **輸出被使用於**：
  - `skill_scene_writer`：遵循風格寫作
  - `skill_dialogue_director`：對話風格參考
  - `skill_sensory_amplifier`：描寫風格參考

## 注意事項

1. 風格指南一旦產生，不應頻繁修改，以維持全書一致性
2. 若需調整風格，建議在章節交界處進行
3. `awards` 欄位是可選的，用於提升 AI 的寫作品質暗示
