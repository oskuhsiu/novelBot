---
description: 情感波段分析與自動調整
---

# /nvEmotion - 情感波段分析

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `range` | ❌ | 分析範圍 | `range=1-25` |
| `fix` | ❌ | 自動修復模式 | `fix=true` |

## 使用範例

```bash
# 分析全專案情感曲線
/nvEmotion proj=霓虹劍仙

# 分析特定範圍
/nvEmotion proj=霓虹劍仙 range=10-20

# 啟用自動調整建議
/nvEmotion proj=霓虹劍仙 fix=true
```

## 執行步驟

### Step 1: 讀取設定
// turbo
讀取 `novel_config.yaml` 中的 `emotion_settings`：

```yaml
emotion_settings:
  enabled: true
  high_tension_threshold: 70
  low_tension_threshold: 30
  max_consecutive_high: 3
  max_consecutive_low: 2
  buffer_mode: "suggest"
```

### Step 2: 載入章節
// turbo
讀取 `range` 範圍內的所有章節檔案。

### Step 3: 分析各章情感
對每一章執行 `emotional_wave_analyzer` Skill：

```yaml
分析維度:
  - 戰鬥場景密度
  - 對話張力
  - 內心戲強度
  - 恐懼/危機元素
  - 浪漫/溫馨元素
  - 懸念/謎題元素
```

### Step 4: 生成情感曲線
繪製情感張力曲線圖：

```
章節:  1  2  3  4  5  6  7  8  9  10
張力: ▁▂▄▆█▇▅▃▂▄
      L  M  H  H  H! H  M  L  L  M
      
L=低壓 M=中等 H=高壓 !=警告
```

### Step 5: 檢測問題
```yaml
問題檢測:
  連續高壓:
    threshold: 3
    found: [3,4,5,6]  # 連續4章高壓
    severity: "warning"
    
  連續低壓:
    threshold: 2
    found: [8,9]
    severity: "notice"
    
  情感斷裂:
    description: "張力驟升驟降超過50"
    found: [7→8]  # 85→25
    severity: "warning"
```

### Step 6: 輸出報告

```
═══════════════════════════════════════════════════
  情感波段分析報告
═══════════════════════════════════════════════════
  專案：霓虹劍仙
  分析範圍：第 1-25 章
───────────────────────────────────────────────────
  情感曲線：
  
  100│        ╭─╮
   80│    ╭──╯  ╰╮    ╭╮
   60│  ╭╯       ╰╮  ╭╯│
   40│╭╯          ╰╮╯  │    ╭
   20│╯            ╰   ╰──╮╭╯
    0└───────────────────────────
      1  5  10  15  20  25 (章)
      
───────────────────────────────────────────────────
  統計：
  ├─ 平均張力：62
  ├─ 最高峰：第15章（92）
  ├─ 最低谷：第22章（18）
  └─ 標準差：24

───────────────────────────────────────────────────
  ⚠️ 問題檢測：

  [WARNING] 連續高壓 (第3-6章)
  → 建議在第4章後插入緩衝場景
  
  [WARNING] 情感斷裂 (第7→8章)
  → 張力從85驟降到25，建議增加過渡
  
  [NOTICE] 連續低壓 (第22-23章)
  → 可加入小衝突維持讀者興趣

───────────────────────────────────────────────────
  建議調整（fix=true 時自動套用）：
  
  第4章 → 減少 combat 權重
  第8章 → 增加 internal_monologue
  第22章 → 觸發小型意外事件
═══════════════════════════════════════════════════
```

### Step 7: 自動修復（可選）
若 `fix=true`，更新 `narrative_progress.yaml`：

```yaml
chapter_XX:
  emotion_adjustment:
    original_weights: {...}
    adjusted_weights: {...}
    reason: "緩衝連續高壓"
```

## 輸出

分析結果存放於 `memory/emotion_log.yaml`。
