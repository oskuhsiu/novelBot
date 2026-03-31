---
name: emotional_wave_analyzer
description: 情感能量監測器 - 追蹤情感波段，自動調節張力節奏
---

# Emotional Wave Analyzer

監控章節情感強度，連續高/低壓過多時輸出調節建議。

## 評分維度（0-100 tension_score）

| 維度 | 權重 | 高分特徵 |
|------|------|---------|
| action | 0.8 | 戰鬥、追逐、肢體衝突 |
| dialogue | 0.3 | 激烈爭論、威脅、攤牌 |
| internal | 0.5 | 恐懼、焦慮、道德掙扎 |
| romance | 0.4 | 情感衝突、告白、背叛 |
| mystery | 0.6 | 懸疑揭露、線索發現、陰謀 |

## 閾值（預設值，可被 novel_config.yaml `emotion_settings` 覆蓋）

- `high_tension_threshold`: 70 | `low_tension_threshold`: 30
- `max_consecutive_high`: 3 章 | `max_consecutive_low`: 2 章

## 閾值檢測

查詢最近情感歷史，判斷：
- 連續高壓 ≥ max → `HIGH_TENSION_OVERLOAD`：建議降低張力
- 連續低壓 ≥ max → `LOW_TENSION_STAGNATION`：建議提升張力
- 相鄰章節張力差 > 50 → `EMOTIONAL_WHIPLASH`：建議增加過渡

## 輸出

- **suggest 模式**（預設）：輸出警告 + 建議調整的 content_weights
- **force 模式**：直接修改下一章的 content_weights
