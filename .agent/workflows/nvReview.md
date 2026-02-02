---
description: 執行一致性檢查
---

# /nvReview - 一致性檢查

對最近章節執行全面邏輯檢查。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `range` | ❌ | 檢查範圍 (預設最近5章) | `range=5` 或 `range=1-20` |

## 使用範例

```
/nvReview proj=霓虹劍仙
/nvReview proj=劍來 range=10
/nvReview proj=霓虹劍仙 range=1-50
```

## 執行步驟

### Step 1: 載入章節
// turbo
讀取指定範圍的章節內容

### Step 2: 邏輯審查
使用 `skill_logic_auditor` 檢查：
- 世界觀規則遵守
- 角色行為一致性
- 能力使用合法性
- 時空邏輯

### Step 3: 連戲檢查
使用 `skill_consistency_validator` 檢查：
- 物品連續性
- 傷勢追蹤
- 位置轉換

### Step 4: 伏筆健康
使用 `skill_loop_closer` 檢查：
- 休眠伏筆
- 逾期伏筆

### Step 5: 生成報告
```
## 審查報告：{proj}
範圍：第 {start} 章 - 第 {end} 章

### 嚴重問題 (Critical)
- [Ch.5] 主角使用了超過等級的技能

### 警告問題 (Warning)
- [Ch.8] 角色語氣略有偏差

### 輕微問題 (Minor)
- [Ch.12] 環境描寫與之前略有出入

### 通過檢查
- ✅ 時空邏輯
- ✅ 物品狀態

### 建議修正
1. Ch.5 第3段：改為築基級技能
2. ...
```

## 輸出

審查報告到終端，並提供修正建議。
