---
description: 完整維護 + 完整審查 + 自動修正（單一 sub-agent，assist 由 nvReview 處理）
---

# /nvAudit - 全面維護審查與修正

單一 foreground sub-agent 依序執行：nvReview full（含 assist）→ 自動修正 → nvMaint full。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `range` | ✅ | 審查範圍（`5` 或 `1-20`） | — |
| `assist` | ❌ | 外部 AI 輔助審查（`codex`/`gemini`/`all`） | `none` |

## 使用範例

```
/nvAudit proj=霓虹劍仙 range=5
/nvAudit proj=霓虹劍仙 range=5 assist=codex
/nvAudit proj=霓虹劍仙 range=3 assist=all
```

---

## Dispatcher 流程（主 context 執行）

### Step 0：參數解析

1. `REPO_ROOT` = 當前工作目錄
2. 讀取 `projects/project_registry.yaml`，解析 `proj` → 取得專案資料夾名稱
3. `PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`
4. 解析 `assist`：未指定 → `none`

> Dispatcher **不讀取**任何專案檔案或 SKILL.md。

### Step 1：啟動 Sub-Agent

啟動 Agent tool（`subagent_type: general-purpose`，`run_in_background: false`），prompt 為下方 **Agent Prompt**（替換 `{{...}}`）。

### Step 2：輸出

將 sub-agent 回傳的合併報告**原封不動**輸出給使用者。

---

## Agent Prompt

````
你是小說全面維護審查助手。請依序完成以下三階段任務。

## 參數
- REPO_ROOT: {{REPO_ROOT}}
- PROJECT_DIR: {{PROJECT_DIR}}
- PROJ: {{PROJ}}
- RANGE: {{RANGE}}
- ASSIST: {{ASSIST}}

## 階段一：完整審查（nvReview full）

讀取 `{{REPO_ROOT}}/.claude/skills/nvReview/SKILL.md`，**直接在本 context 內**按其指令執行完整審查（不啟動 sub-agent）。替換參數：
- {{PROJECT_DIR}}, {{PROJ}}, {{REPO_ROOT}}
- {{MODE}} = full
- range={{RANGE}}
- {{ASSIST}} = {{ASSIST}}

> nvReview 是 B 類 skill，沒有 Agent Prompt wrapper，直接跟隨其 Step 0-3.5 執行。

審查完成後，將報告寫入 `{{PROJECT_DIR}}/reviews/review_ch{START}-{END}.md`（實際章號，目錄不存在先建立）。

## 階段二：自動修正

根據階段一的審查報告（含外部 AI 統整結果），修正所有 Critical 和 Warning。

1. **逐一修正**：根據建議方案修改章節檔案
2. **修正原則**：
   - 最小改動，不重寫整章
   - 消除矛盾 + 保持文風 + 不引入新矛盾
   - 設定變更同步更新 yaml/SQLite
3. **修正迴圈**：修正後重新審查（僅審查），仍有 Critical 則再修一輪（最多 2 輪）
4. **儲存修正報告**：將修正報告寫入 `{{PROJECT_DIR}}/reviews/fix_ch{START}-{END}.md`

## 階段三：完整維護（nvMaint full）

讀取 `{{REPO_ROOT}}/.claude/skills/nvMaint/SKILL.md`，**直接在本 context 內**按其指令執行完整維護（nvMaint 是 B 類，無需開 sub-agent）。替換參數：
- {{PROJECT_DIR}}, {{PROJ}}, {{REPO_ROOT}}, {{MODE}} = full

## 最終輸出

```
=== 審查報告 ===
{Claude 審查結果 + 外部 AI 統整（若有）}

=== 修正報告 ===
修正輪數：{N}
已修正：
  - [Ch.{X}] {問題} → {修正方式}（來源：{Claude/Codex/Gemini}）
未解決（如有）：
  - [Ch.{X}] {問題} → {原因}

=== 最終狀態 ===
Critical: {n} (已修正 {m}, 未解決 {k})
Warning: {n} (已修正 {m}, 未解決 {k})
Minor: {n} (未修正，僅記錄)

=== 維護報告 ===
{nvMaint 摘要}
```

## 注意事項
- 無法使用 `/nvXXX` skill 指令，所有內部 skill 改為「Read SKILL.md 路徑並遵循其指令」
- ChromaDB 操作使用 Bash 執行 python 腳本
- 所有檔案路徑使用絕對路徑
````
