---
name: emotional_wave_analyzer
description: 情感能量監測器 - 追蹤情感波段，自動調節張力節奏
---

# Emotional Wave Analyzer

監控章節的情感強度，當連續高/低壓章節過多時，輸出調節建議。

## 設定參數（來自 novel_config.yaml）

```yaml
emotion_settings:
  enabled: true
  high_tension_threshold: 70    # 超過此值 = 高壓
  low_tension_threshold: 30     # 低於此值 = 低壓
  max_consecutive_high: 3       # 連續高壓上限（章）
  max_consecutive_low: 2        # 連續低壓上限（章）
  buffer_mode: "suggest"        # suggest / force
```

## 執行步驟

### Step 1: 分析章節情感強度

閱讀章節內容，綜合評估以下維度給出 0-100 的 tension_score：

| 維度 | 權重 | 高分特徵 |
|------|------|---------|
| action | 0.8 | 戰鬥、追逐、肢體衝突 |
| dialogue | 0.3 | 激烈爭論、威脅、攤牌 |
| internal | 0.5 | 恐懼、焦慮、道德掙扎 |
| romance | 0.4 | 情感衝突、告白、背叛 |
| mystery | 0.6 | 懸疑揭露、線索發現、陰謀 |

### Step 2: 閾值檢測

查詢最近情感歷史，判斷：
- 連續高壓 ≥ `max_consecutive_high` → `HIGH_TENSION_OVERLOAD`：建議下一章降低張力
- 連續低壓 ≥ `max_consecutive_low` → `LOW_TENSION_STAGNATION`：建議下一章提升張力
- 相鄰章節張力差 > 50 → `EMOTIONAL_WHIPLASH`：建議增加過渡場景

### Step 3: 輸出

**suggest 模式**：輸出警告 + 建議調整的 content_weights
**force 模式**：直接修改下一章的 content_weights

## 與其他 Skill 的連動

- **nvMaint**：章節完成後自動調用，寫入 emotion_query CLI
- **nvDraft**：根據建議調整下一章節奏
