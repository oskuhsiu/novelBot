---
description: 將 SubArc 動態拆分成數個章節節拍 (Beats)
---
# /nvBeat - 次綱拆分

這是輔助工作流，當切換到新的 SubArc 時被觸發。它會讀取 `pacing_pointer` 參數，評估需要將這個 SubArc 展開成多少章節，並為每一章規劃出「帶有意外與衝突」的具體節拍 (Beat)。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=eve` |
| `pacing` | ❌ | 強制指定節奏 (覆蓋 config) | `pacing=0.2` |

## 使用範例

```
/nvBeat proj=eve
/nvBeat proj=eve pacing=0.5
```

---

## 執行步驟

### Step 1: 載入專案狀態與 SubArc 資訊
// turbo

從 `config/narrative_progress.yaml` 讀取 `active_subarcs`。
根據 `active_subarcs`（例如 `A1_S3`），到對應的 `config/outline/arc_{N}.yaml` 中讀取這個 SubArc 的完整資訊（包含 title, summary, characters, location, emotion_shift 等）。
同時讀取 `config/novel_config.yaml` 裡的 `engine_settings.pacing_pointer`。

```
═══════════════════════════════════════════════════════
  🪚 開始拆分 SubArc：{active_subarcs}
═══════════════════════════════════════════════════════
  專案：{proj}
  目標綱要：{subarc_title}
  Pacing 指針：{pacing_pointer}
═══════════════════════════════════════════════════════
```

### Step 2: 使用 LLM 產生節拍 (Beats) 的 Prompt 構建

使用以下 prompt 向 LLM 要求拆分（假設使用 `skill_outline_architect` 或直接 prompt 生成）：

```prompt
你是一個專業的小說大綱企劃。現在有一個「次綱 (SubArc)」的情節需要被展開成多個具體的章節。

【系統參數】
當前的 pacing_pointer (節奏指針) 為: {pacing_pointer}
這個數字代表了劇情的推演速度。
- 1.0 代表節奏極快，1個 SubArc 大約只需要 1 章就能講完。
- 0.5 代表中等節奏，大約對應 2 章。
- 0.2 代表極慢的日常/細節節奏，大約對應 5 章。
- 0.1 代表水文級別的極限慢放，大約對應 10 章。

請分析下方【SubArc 資訊】，並「參考」上述公式，提出你認為最合適的章節拆分數量（允許根據劇情張力彈性調整 ±2 章）。

然後，產出這 {N} 個章節的節拍 (Beats) 列表。

【強制要求】
1. 為了避免平淡無聊，每一個 Beat (也就是每一章) 的極簡述中，**必須適度添加「意外因子」、「衝突」或「小插曲」**，不要讓它只是流水帳。即使是「純日常」也要有戲劇張力。
2. 輸出的格式必須是嚴格的 YAML 陣列格式。

【SubArc 資訊】
ID: {subarc_id}
Title: {subarc_title}
Summary: {subarc_summary}
... (包含參與角色與地點)

【預期輸出格式範例】
beats:
  - title: "第1拍的標題"
    summary: "第1拍的20~30字極簡述（包含意外因子）。"
  - title: "第2拍的標題"
    summary: "第2拍的20~30字極簡述（包含意外因子）。"
```

### Step 3: 更新 Narrative Progress
// turbo

將 LLM 產出的 YAML 陣列寫入 `config/narrative_progress.yaml`。

1. 從陣列中取出第一項 (index 0)，放入 `current_beat`。
2. 將剩餘的項目 (index 1 到 N) 放入 `upcoming_beats`。

```yaml
current_beat:
  title: "LLM產出的第1個標題"
  summary: "LLM產出的第1個極簡述"
upcoming_beats:
  - title: "LLM產出的第2個標題"
    summary: "LLM產出的第2個極簡述"
  - title: "LLM產出的第3個標題"
    summary: "LLM產出的第3個極簡述"
```

### Step 4: 輸出報告
// turbo

```
═══════════════════════════════════════════════════════
  ✅ SubArc 拆分完成
═══════════════════════════════════════════════════════
  共拆出 {N} 個節拍 (Beats)
  當前需寫作 Beat：{current_beat.title}
  
  現在可以執行 `/nvDraft` 產生本章草稿。
═══════════════════════════════════════════════════════
```
