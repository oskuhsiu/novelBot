---
description: 預覽接下來的章節規劃
---

# /nvPreview - 預覽規劃

預覽接下來 N 章會發生什麼，不實際寫作。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `n` | ❌ | 預覽章數 (預設 3) | `n=5` |
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |

## 使用範例

```
/nvPreview n=3 proj=霓虹劍仙
/nvPreview n=10 proj=劍來
```

## 執行步驟

### Step 1: 載入大綱
// turbo
讀取 `narrative_progress.yaml` 的 `outline`

### Step 2: 計算範圍
// turbo
從 `current_chapter` 開始，取接下來 `n` 章

### Step 3: 生成預覽
對於每章，輸出：
- 章節標題
- 摘要
- 預計節拍 (beats)
- 情緒走向
- 可能觸發的伏筆

### Step 4: 張力分析
使用 `skill_beat_optimizer` 分析這 N 章的張力曲線

### Step 5: 建議
提供調整建議：
- 是否需要插入緩衝章節
- 是否需要引入意外事件
- 可回收的伏筆

## 輸出

預覽報告到終端，不修改任何檔案。
