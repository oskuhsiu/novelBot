---
description: 自動排程器：交替執行 nvBatch 和 nvAudit（搭配 /loop 使用）
---

# /nvScheduler - 自動排程器

搭配 `/loop` 使用，每次被觸發時判斷系統狀態，決定要執行 nvBatch 還是 nvAudit。
**所有任務都透過 sub-agent 執行**，保護主 context 不爆。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱或 alias | （無，空則報錯結束） |
| `n` | ❌ | nvBatch 每批章數 | `4` |
| `range` | ❌ | nvAudit 審查範圍 | `4` |
| `maint` | ❌ | nvBatch 維護頻率 | `light` |
| `review` | ❌ | nvBatch 審查頻率 | `light` |
| `reset` | ❌ | 清除排程狀態檔後結束 | `reset=true` |

## 使用方式

```
/loop 10m /nvScheduler proj=bnf
/loop 10m /nvScheduler proj=bnf n=6 range=5
```

管理 loop：
- 列出：請 Claude 執行 CronList
- 取消：請 Claude 執行 CronDelete + job ID

---

## 重要：JSON 寫入方式

**禁止**使用 `cat > file << EOF` 寫 JSON（會觸發 sandbox 安全警告）。
所有狀態檔寫入一律使用 Python：

```bash
.venv/bin/python3 -c "import json; json.dump({JSON_DICT}, open('/private/tmp/claude-502/claude_scheduler_state.json','w'))"
```

例如：
```bash
.venv/bin/python3 -c "import json; json.dump({'last_completed':'nvAudit','proj':'bnf'}, open('/private/tmp/claude-502/claude_scheduler_state.json','w'))"
```

---

## 執行流程

### Step 0: 參數驗證
// turbo
- 若 `reset=true` → 刪除 `/private/tmp/claude-502/claude_scheduler_state.json`，輸出「🗑 排程狀態已清除」→ **結束**
- 若 `proj` 為空 → 輸出「❌ nvScheduler: proj 參數必填」→ **結束**
- 設定 `REPO_ROOT` = 當前工作目錄
- 讀取 `projects/project_registry.yaml`，解析 proj alias → 取得專案資料夾名稱
- 設定 `PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`

### Step 1: 檢查 5h API Usage
// turbo

讀取 `/tmp/claude_usage_cache.json`：

```bash
cat /tmp/claude_usage_cache.json
```

- 若檔案不存在 → **結束**

解析欄位：
- `utilization` = `anthropic-ratelimit-unified-5h-utilization`（0.00~1.00 → 換算為百分比）
- `reset_ts` = `anthropic-ratelimit-unified-5h-reset`（Unix timestamp）
- `now` = 當前時間（`date +%s`）

**判斷：**
- **< 70%** → 繼續
- **>= 70%** 且 **now < reset_ts**（重置時間尚未到）→ 輸出「⏸ 5h usage {N}%，排程暫停等待冷卻（重置於 {reset_ts 轉人類可讀}）」→ **結束**
- **>= 70%** 且 **now >= reset_ts**（重置時間已過，cache 過時）→ 執行以下重新檢查：
  1. 執行 `python3 ~/.claude/usage-check.py` 取得最新 usage（stdout 為 JSON）
  2. 解析新的 `anthropic-ratelimit-unified-5h-utilization`
  3. 若新值 **< 70%** → 輸出「🔄 Usage 已重置 ({新N}%)，繼續執行」→ 繼續
  4. 若新值 **>= 70%** → 輸出「⏸ 5h usage 重新檢查仍為 {新N}%，排程暫停」→ **結束**

### Step 2: 檢查 nvBatch 是否在執行中
// turbo

讀取 `{PROJECT_DIR}/config/nvbatch_config.yaml`：
- 若 `enabled: true` 且 `completed_chapters < target_chapters` → nvBatch 仍在跑
  - 輸出「🔄 nvBatch 執行中 ({completed_chapters}/{target_chapters})，跳過」→ **結束**

### Step 3: 讀取排程狀態
// turbo

讀取 `/private/tmp/claude-502/claude_scheduler_state.json`：

```json
{
  "last_completed": "nvBatch" | "nvAudit" | null,
  "last_completed_at": "ISO timestamp",
  "proj": "bnf"
}
```

- 若檔案不存在 → 視為 `{"last_completed": null}`
- 若檔案中的 `proj` 與當前 `proj` 不同 → 視為 `{"last_completed": null}`（專案切換，重新開始）

### Step 4: 決定並執行任務

根據 `last_completed` 決定下一步：

#### 情境 A：執行 nvBatch（首次執行或上次完成 nvAudit）

當 `last_completed == null` 或 `last_completed == "nvAudit"`：

1. 更新狀態檔：寫入 `/private/tmp/claude-502/claude_scheduler_state.json`
   ```json
   {"last_completed": null, "running": "nvBatch", "proj": "{proj}"}
   ```

2. **透過 sub-agent 執行 nvBatch**（不在主 context 讀 SKILL.md）：
   啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `run_in_background`: `false`
   - `prompt`:
     ```
     你是小說批次寫作助手。

     1. 讀取 {REPO_ROOT}/.claude/skills/nvBatch/SKILL.md
     2. 嚴格遵循其中的狀態機執行流程

     參數：
     - proj = {proj}（專案資料夾：{資料夾名稱}）
     - n = {n}
     - maint = {maint}
     - review = {review}
     - REPO_ROOT = {實際路徑}
     - PROJECT_DIR = {實際路徑}

     重要：
     1. 你無法使用 /nvXXX skill 指令。所有內部 skill 請「Read 對應 SKILL.md 路徑並遵循其指令」
     2. ChromaDB 操作使用 Bash：cd {REPO_ROOT} && .venv/bin/python tools/lore_query.py
     3. 所有檔案路徑使用絕對路徑
     4. /nvChapter 的執行方式：讀取 {REPO_ROOT}/.claude/skills/nvChapter/SKILL.md 並遵循其指令
     ```

3. 完成後更新狀態檔：
   ```json
   {"last_completed": "nvBatch", "last_completed_at": "{ISO timestamp}", "proj": "{proj}"}
   ```

4. 輸出「✅ nvBatch {n}章完成，下次將執行 nvAudit」

#### 情境 B：執行 nvAudit（上次完成 nvBatch）

當 `last_completed == "nvBatch"`：

1. 更新狀態檔：
   ```json
   {"last_completed": null, "running": "nvAudit", "proj": "{proj}"}
   ```

2. **透過 sub-agent 執行 nvAudit**（不在主 context 讀 SKILL.md）：
   啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `run_in_background`: `false`
   - `prompt`:
     ```
     你是小說全面維護審查助手。

     1. 讀取 {REPO_ROOT}/.claude/skills/nvAudit/SKILL.md
     2. 遵循其中「調度步驟」和「Agent Prompt」的完整指令執行

     參數：
     - REPO_ROOT = {實際路徑}
     - PROJECT_DIR = {實際路徑}
     - PROJ = {實際專案名}
     - RANGE = {range}

     重要：
     - 你無法使用 /nvXXX skill 指令，所有內部 skill 請「Read 對應 SKILL.md 路徑並遵循其指令」
     - ChromaDB 操作使用 Bash：cd {REPO_ROOT} && .venv/bin/python tools/lore_query.py
     - 所有檔案路徑使用絕對路徑
     ```

3. 完成後更新狀態檔：
   ```json
   {"last_completed": "nvAudit", "last_completed_at": "{ISO timestamp}", "proj": "{proj}"}
   ```

4. 輸出「✅ nvAudit 完成，下次將執行 nvBatch」

---

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| sub-agent 執行失敗 | 不更新 `last_completed`（下次重試同一任務），輸出錯誤訊息 |
| nvbatch_config.yaml 不存在 | 正常，代表沒有進行中的 batch |
| 狀態檔損壞 | 重置為 `{"last_completed": null}` |
