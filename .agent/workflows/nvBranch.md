---
description: 從指定章節開始分支劇情
---

# /nvBranch - 分支劇情

從指定章節建立劇情分支，用於測試不同走向或多結局。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 來源專案 | `proj=霓虹劍仙` |
| `ch` | ✅ | 分支起點章節 | `ch=10` |
| `name` | ✅ | 分支名稱 | `name=bad_end` |
| `desc` | ❌ | 分支描述 | `desc="主角選擇背叛"` |

## 使用範例

```
/nvBranch proj=霓虹劍仙 ch=10 name=bad_end
/nvBranch proj=劍來 ch=50 name=route_b desc="選擇加入天宮"
```

## 執行步驟

### Step 1: 驗證來源
// turbo
確認來源專案和章節存在

### Step 2: 建立分支專案
// turbo
建立 `projects/{proj}_{name}/` 目錄

### Step 3: 複製設定
// turbo
複製來源專案的所有設定檔到分支

### Step 4: 複製章節
// turbo
複製第 1 章到第 {ch} 章的內容

### Step 5: 複製記憶
// turbo
複製到第 {ch} 章為止的記憶庫狀態

### Step 6: 設定進度
// turbo
設定分支的 `narrative_progress.yaml`:
- `current_chapter` = {ch} + 1
- 標記為分支專案

### Step 7: 分支設定
記錄分支資訊:
```yaml
branch_info:
  parent: {proj}
  branch_point: {ch}
  name: {name}
  description: {desc}
  created_at: {timestamp}
```

## 輸出

分支專案建立完成，可用 `/nvChapter proj={proj}_{name}` 繼續寫作。

## 使用場景

1. **多結局** - 從關鍵抉擇點分出不同結局
2. **備案測試** - 測試不同劇情走向的效果
3. **平行發展** - 同時發展多條故事線
