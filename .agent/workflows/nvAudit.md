---
description: 完整維護 + 完整審查 + 自動修正
---

# /nvAudit - 全面維護審查與修正

依序執行 nvMaint full、nvReview full，並自動修正所有發現的問題。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `range` | ✅ | 審查範圍 | `range=5` 或 `range=1-20` |

### range 參數說明
- `range=N`：審查最近 N 章
- `range=A-B`：審查第 A 章到第 B 章

## 使用範例

```
/nvAudit proj=霓虹劍仙 range=5
/nvAudit proj=劍來 range=1-20
```

---

## 執行步驟

### 階段一：完整維護（nvMaint full）

執行 `/nvMaint proj={proj} mode=full`，確保所有設定檔已更新。

### 階段二：完整審查（nvReview full）

執行 `/nvReview proj={proj} range={range} mode=full`，全 8 項類別檢查。

### 階段三：自動修正

根據階段二的審查報告，修正所有 Critical 和 Warning 問題。

#### 修正流程

1. **逐一修正**：根據審查報告中每個問題的「建議修正方案」，直接修改對應章節檔案中的問題段落
2. **修正原則**：
   - 最小改動原則：只改有問題的句子/段落，不重寫整章
   - 修正必須同時滿足：消除邏輯矛盾 + 保持文風一致 + 不引入新矛盾
   - 若修正涉及設定變更（如角色狀態、物品），同步更新對應的 yaml 設定檔
3. **修正後驗證**：修正完成後，對修改過的章節重新執行審查（僅審查，不重複維護）
   - 若仍有 Critical → 再修正一次（最多 2 輪修正）
   - 若 2 輪後仍有 Critical → 在報告中標註未解決並列出殘留問題

#### 修正迴圈邏輯

```
round = 0
max_rounds = 2
issues = 階段二審查報告中的 Critical + Warning

while issues exist and round < max_rounds:
  for each issue:
    apply fix to chapter file based on issue.suggestion
    if fix involves setting changes:
      update corresponding yaml config files
  round += 1
  if round < max_rounds:
    re-review modified chapters (/nvReview full, 僅審查步驟)
    issues = new Critical + Warning
  else:
    mark remaining as 未解決
```

## 執行順序

1. 先完成階段一（完整維護），確保所有設定檔已更新
2. 再執行階段二（完整審查），全 8 項類別檢查
3. 若有 Critical/Warning，執行階段三（自動修正 + 驗證迴圈）
4. 最後輸出合併報告，格式：

```
=== 維護報告 ===
{nvMaint 的維護摘要：更新了哪些檔案、新增了多少條目}

=== 審查報告 ===
{nvReview 的審查結果，含 Critical/Warning/Minor 分級}

=== 修正報告 ===
修正輪數：{N}
已修正：
  - [Ch.{X}] {問題描述} → {修正方式}
  - ...
未解決（如有）：
  - [Ch.{X}] {問題描述} → {原因}

=== 最終狀態 ===
Critical: {n} (已修正 {m}, 未解決 {k})
Warning: {n} (已修正 {m}, 未解決 {k})
Minor: {n} (未修正，僅記錄)
```

## 輸出

合併報告包含維護摘要、審查結果、修正記錄與最終狀態。
