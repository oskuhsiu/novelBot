---
description: 自動排程器：依序執行 nvBatch 和 nvAudit
---

# /nvScheduler - 自動排程器

依序透過 Skill tool 執行 /nvBatch → /nvAudit，迴圈 N 輪。
nvBatch 和 nvAudit 各自的 dispatcher 會 spawn 自己的 sub-agent，nvScheduler 不額外包層。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅* | 專案名稱或 alias（`status=true` 時可省略） | （無，空則報錯結束） |
| `rounds` | ❌ | 跑幾輪（1 輪 = nvBatch + nvAudit） | `3` |
| `limit` | ❌ | 5h usage 百分比閾值，超過暫停等冷卻 | `70` |
| `n` | ❌ | nvBatch 每批章數 | `3` |
| `range` | ❌ | nvAudit 審查範圍 | `3` |
| `maint` | ❌ | nvBatch 維護頻率 | `light` |
| `review` | ❌ | nvBatch 審查頻率 | `light` |
| `assist` | ❌ | nvAudit 外部 AI 輔助 | `none` / `codex` / `gemini` / `all` |
| `pause` | ❌ | 暫停排程（可從另一個 session 執行） | `pause=true` |
| `resume` | ❌ | 恢復暫停的排程（在同一 session 口頭說即可） | `resume=true` |
| `reset` | ❌ | 清除該 proj 排程狀態檔後結束 | `reset=true` |
| `status` | ❌ | 顯示所有 proj 排程狀態後結束 | `status=true` |

## 使用方式

```
/nvScheduler proj=bnf
/nvScheduler proj=bnf rounds=5 limit=60
/nvScheduler proj=bnf rounds=3 n=6 range=5 assist=all
/nvScheduler proj=bnf reset=true
/nvScheduler status=true
```

---

## 路徑規則

`TMPDIR` = `$TMPDIR` 環境變數（sandbox 自動設定，通常為 `/private/tmp/claude-{UID}/`）。
`TMPDIR` 是一個**完整的目錄路徑**（如 `/private/tmp/claude-xxx`），不是前綴片段，不一定有尾部 `/`。
Bash 中拼接檔案路徑時**必須**用 `"${TMPDIR}/filename"` 而非 `"${TMPDIR}filename"`。

| 用途 | 路徑 |
|------|------|
| 排程狀態 | `${TMPDIR}/claude_scheduler_{proj}.json` |
| 暫停旗標 | `${TMPDIR}/claude_scheduler_{proj}.pause` |

⚠️ 常見錯誤：`"${TMPDIR}claude_scheduler_..."` → 缺少 `/` → 產生如 `/tmp/claudeclaude_scheduler_...` 的錯誤路徑。

---

## 重要：JSON 寫入方式

**禁止**使用 `cat > file << EOF` 寫 JSON（會觸發 sandbox 安全警告）。
所有狀態檔寫入一律使用 Python：

```bash
python3 -c "import json,tempfile,os; p=os.path.join(tempfile.gettempdir(),'claude_scheduler_{proj}.json'); json.dump({JSON_DICT}, open(p,'w'))"
```

---

## 執行流程

### Step 0a: 控制指令處理
// turbo

依序檢查，若命中則執行後**立即結束**：

**`status=true`**（不需要 proj）：
- 列出所有 `{TMPDIR}/claude_scheduler_*.json`
- 讀取每個的 `last_completed`、`last_completed_at`、`current_round`、`total_rounds`
- 格式化輸出 → **結束**

**`pause=true`**（需要 proj）：
- 建立旗標：`touch {TMPDIR}/claude_scheduler_{proj}.pause`
- 輸出「{proj} 排程已暫停。排程迴圈會在下一個 phase 前偵測到並等待。」→ **結束**

**`reset=true`**（需要 proj）：
- 刪除 `{TMPDIR}/claude_scheduler_{proj}.json`
- 輸出「{proj} 排程狀態已清除」→ **結束**

---

### Step 0b: 正常執行前的基本檢查
// turbo

- 若 `proj` 為空 → 輸出錯誤 → **結束**
- 設定 `REPO_ROOT` = 當前工作目錄
- 讀取 `projects/project_registry.yaml`，解析 proj alias → 取得專案資料夾名稱
- 設定 `PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`

---

### Step 1: 讀取排程狀態（支援從中斷處繼續）
// turbo

讀取 `{TMPDIR}/claude_scheduler_{proj}.json`：

- 若檔案不存在或損壞 → `next_phase = "nvBatch"`, `next_round = 1`
- 若 `last_completed == "nvBatch"` → `next_phase = "nvAudit"`, `next_round = current_round`
- 若 `last_completed == "nvAudit"` → `next_phase = "nvBatch"`, `next_round = current_round + 1`
- 若 `next_round > rounds` → 輸出「上次已完成全部輪數，使用 reset=true 重新開始」→ **結束**

---

### Step 2: 輸出啟動資訊

```
nvScheduler 已啟動
  專案: {proj}
  輪數: {rounds}（從 Round {next_round} {next_phase} 開始）
  5h limit: {limit}%
  nvBatch: n={n}, maint={maint}, review={review}
  nvAudit: range={range}, assist={assist}
```

---

### Step 3: 主迴圈

```
for round = next_round to rounds:
  for phase in [nvBatch, nvAudit]（若 next_phase 指定則從該 phase 開始）:

    1. 前置檢查：pause + 5h usage（合併為單一 Python 呼叫，避免多次 Bash approval）
       ```bash
       python3 -c "
       import json,os,tempfile
       tmp=tempfile.gettempdir()
       pf=os.path.join(tmp,'claude_scheduler_{proj}.pause')
       result={'paused':os.path.isfile(pf),'usage':None}
       try:
        d=json.load(open('/private/tmp/claude_rate_limits.json'))
        result['usage']=d.get('five_hour',{}).get('used_percentage')
       except: pass
       print(json.dumps(result))
       "
       ```
       - 解析輸出 JSON：
         - 若 `paused == true` → 輸出「⏸ {proj} 排程已暫停（Round {round} {phase} 前）。說 resume 繼續。」
           - 使用 AskUserQuestion 等待使用者回應
           - 收到 resume 指令後：`rm -f {TMPDIR}/claude_scheduler_{proj}.pause`，繼續
         - 若 `usage >= limit` → 建立 pause 旗標，輸出「5h usage {N}% >= {limit}%，排程暫停。說 resume 繼續」
           - 使用 AskUserQuestion 等待 → 收到 resume 後刪除 pause 旗標，繼續
         - 若 `usage == null` → 繼續（檔案不存在或無法解析）

    3. 更新狀態檔：running = {phase}

    4. 透過 Skill tool 呼叫對應 skill：
       - nvBatch：Skill tool → /nvBatch proj={proj} n={n} maint={maint} review={review}
         （nvBatch 的 dispatcher 會自行 spawn fg sub-agent）
       - nvAudit：Skill tool → /nvAudit proj={proj} range={range} assist={assist}
         （nvAudit 的 dispatcher 會自行 spawn fg sub-agent）

    5. Skill 完成後：
       - 更新狀態檔：last_completed = {phase}, last_completed_at = {ISO}
       - **禁止 Bash 中使用 `$()` 或 backtick**，時間戳必須用 Python `datetime` 取得
       - 輸出「✅ Round {round} {phase} 完成」

結束迴圈後：
  rm -f {TMPDIR}/claude_scheduler_{proj}.pause
  rm -f {TMPDIR}/claude_scheduler_{proj}.json
  輸出「nvScheduler 全部完成：{rounds} 輪（狀態檔已清除）」
```

---

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| Skill 執行失敗 | 不更新 last_completed（保持上一個成功狀態），顯示錯誤，**結束** |
| 執行中斷 | 狀態檔保留，使用者可重新 `/nvScheduler` 從中斷處繼續 |
| 5h usage 超限 | 更新狀態檔後結束，使用者可稍後重新執行繼續 |
