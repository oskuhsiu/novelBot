---
description: 匯出章節到單一檔案
---

# /nvExport - 匯出

將多章合併匯出為單一文件。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `fmt` | ❌ | 格式 (預設 md) | `fmt=md` 或 `fmt=txt` |
| `range` | ❌ | 章節範圍 (預設全部) | `range=1-10` |

## 使用範例

```
/nvExport proj=霓虹劍仙 fmt=md
/nvExport proj=劍來 fmt=txt range=1-50
/nvExport proj=霓虹劍仙 range=10-20
```

## 執行步驟

### Step 1: 驗證範圍
// turbo
讀取 `output/chapters/` 確認可用章節

### Step 2: 合併內容
// turbo
按順序讀取指定範圍的章節，合併為單一文件

### Step 3: 添加目錄
// turbo
在開頭生成章節目錄

### Step 4: 格式轉換
若 `fmt=txt`：
- 移除 markdown 格式標記
- 轉換為純文字

### Step 5: 輸出
// turbo
寫入 `output/{proj}_{range}.{fmt}`

## 輸出

匯出檔案到 `output/` 目錄。
