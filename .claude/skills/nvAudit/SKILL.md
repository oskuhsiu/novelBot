---
description: 完整維護 + 完整審查 + 自動修正（單一前景 sub-agent）
---

# /nvAudit - 全面維護審查與修正

在單一 foreground sub-agent 中依序執行 nvMaint full、nvReview full，並自動修正所有發現的問題。

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

## 執行模式：Sub-Agent（A 類）

本 skill 透過**單一 foreground sub-agent** 執行全部流程（維護 → 審查 → 修正），保護主 context。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 讀取 `projects/project_registry.yaml`，解析 `proj` 參數 → 取得專案資料夾名稱
3. 組合路徑：`PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`
4. 讀取以下兩個 SKILL.md 的 Agent Prompt 段落：
   - `{REPO_ROOT}/.claude/skills/nvMaint/SKILL.md`
   - `{REPO_ROOT}/.claude/skills/nvReview/SKILL.md`
5. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `run_in_background`: `false`
   - `prompt`: 組合下方「Agent Prompt」模板，替換所有模板變數

> [!IMPORTANT]
> Dispatcher 只做參數解析和路徑組合，不讀取任何專案檔案。所有檔案讀寫在 sub-agent 內完成。

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將 `{{REPO_ROOT}}`、`{{PROJECT_DIR}}`、`{{PROJ}}`、`{{RANGE}}` 替換為實際值，並將 nvMaint / nvReview 的 Agent Prompt 內容嵌入對應位置。

````
你是小說全面維護審查助手。請依序完成以下三階段任務。

## 階段一：完整維護（nvMaint full）

{nvMaint SKILL.md 的 Agent Prompt 內容，替換：}
- {{PROJECT_DIR}} = {實際路徑}
- {{PROJ}} = {實際專案名}
- {{MODE}} = full
- {{REPO_ROOT}} = {實際路徑}

## 階段二：完整審查（nvReview full）

{nvReview SKILL.md 的 Agent Prompt 內容，替換：}
- {{PROJECT_DIR}} = {實際路徑}
- {{PROJ}} = {實際專案名}
- {{MODE}} = full
- {{RANGE_OR_CHAPTER}} = range={{RANGE}}

## 階段三：自動修正

根據階段二的審查報告，修正所有 Critical 和 Warning 問題。

### 修正流程

1. **逐一修正**：根據審查報告中每個問題的「建議修正方案」，直接修改對應章節檔案中的問題段落
2. **修正原則**：
   - 最小改動原則：只改有問題的句子/段落，不重寫整章
   - 修正必須同時滿足：消除邏輯矛盾 + 保持文風一致 + 不引入新矛盾
   - 若修正涉及設定變更（如角色狀態、物品），同步更新對應的 yaml 設定檔
3. **修正後驗證**：修正完成後，對修改過的章節重新執行審查（僅審查，不重複維護）
   - 若仍有 Critical → 再修正一次（最多 2 輪修正）
   - 若 2 輪後仍有 Critical → 在報告中標註未解決並列出殘留問題

### 修正迴圈邏輯

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
    re-review modified chapters (nvReview full, 僅審查步驟)
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

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有內部 skill 改為「Read SKILL.md 路徑並遵循其指令」
2. ChromaDB 操作使用 Bash 執行 python 腳本
3. 所有檔案路徑使用絕對路徑
4. 最終輸出必須是完整的合併報告文字
````

## 輸出

合併報告由 sub-agent 生成並回傳，包含維護摘要、審查結果、修正記錄與最終狀態。
