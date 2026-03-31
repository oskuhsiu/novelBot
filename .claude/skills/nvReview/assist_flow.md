# nvReview Assist Flow

> 本檔**僅由 nvReview SKILL.md** 在 `assist ≠ none` 時讀取。
>
> **Placeholder 來源**：`{{REPO_ROOT}}`、`{{PROJ}}`、`{{PROJECT_DIR}}`、`{{ASSIST}}` 由主檔初始化步驟替換。`{{REVIEW_INPUT}}` 在本檔 Step 1.5 定義。`{START}`/`{END}` 是主檔 Step 1a 確定的審查範圍首末章號。

## Step 1.5: 寫暫存檔 + 派出 Teammates

### 寫暫存檔（精簡版）

> **原則**：磁碟上能讀到的只給路徑，sub-agent 自己讀。只有動態查詢結果（SQLite / ChromaDB）才貼入。

`{{REVIEW_INPUT}}` = `{{PROJECT_DIR}}/reviews/assist_input_ch{START}-{END}.md`

用 **Write tool** 一次寫入（不用 heredoc），內容結構：

```markdown
# 小說審查任務
你是繁體中文小說審查助手。請對以下章節執行一致性審查，找出：
1. 情節邏輯矛盾（時間線、因果、數量）
2. 吃書（與設定中的規則矛盾）
3. 資訊邊界違反（角色知道不該知道的事）
4. 能力合法性問題（違反能力限制）
5. 錯字與 AI 寫作痕跡
6. 角色行為偏離性格設定

對每個發現，請列出：嚴重度(Critical/Warning/Minor)、章節號、問題描述、原文引用、建議修正。
只列出你有把握的問題，不確定的標為 [不確定]。

## 請讀取以下檔案
- 設定檔：{novel_config.yaml 絕對路徑}
- 進度檔：{narrative_progress.yaml 絕對路徑}
- 能力系統：{power_system.yaml 絕對路徑}（若 Step 1 已載入）
- Outline：{arc_N.yaml 絕對路徑}（若 Step 1 已載入）
- 前文章節：{chapter_X.md 絕對路徑}（2-3 章）
- 目標章節：{chapter_Y.md 絕對路徑}

## 動態查詢結果（無法從磁碟讀取）

### 登場角色（完整 JSON，禁止摘要）
{直接貼入 char_query.py get 的完整 JSON 輸出，包含 base_profile、hidden_profile、current_state。不可自行精簡或改寫。}

### ChromaDB 章節摘要
{貼入 lore_query.py chapters --recent N --full 的輸出}

### 物品資料（若有）
{貼入 item_query.py 的輸出}
```

> **不貼入**：config 全文、outline 全文、power_system 全文、章節原文 — 這些都在磁碟上，給路徑即可。

### 派出 Teammates

> **路徑規則**：所有 Teammate prompt 中的路徑必須是**已替換的絕對路徑**，不可留 `{{REVIEW_INPUT}}` 或 `{{PROJECT_DIR}}` 等未展開 placeholder。
> **檔名規則**：`review_ch{START}-{END}_codex.md` / `review_ch{START}-{END}_gemini.md`（實際章號）。

使用 **Agent tool**（`run_in_background: true`）派出。Prompt 極簡。**以下範例中的 `{{...}}` 必須在派出前替換為實際絕對路徑字串**：

**codex（ASSIST = `codex` 或 `all`）：**
> ⚠️ Codex CLI 須在 Claude sandbox 外執行（Bash 加 `dangerouslyDisableSandbox: true`）。
```
name: "codex-reviewer", run_in_background: true
prompt: 你是 Codex 審查 Teammate。用 Bash 執行（foreground，必須 dangerouslyDisableSandbox: true）：
  codex exec --sandbox workspace-write --full-auto "讀取 {{REVIEW_INPUT}} 並按其中指令審查。結果寫入 {{PROJECT_DIR}}/reviews/review_ch{START}-{END}_codex.md"
  若未安裝回報略過。
```

**gemini（ASSIST = `gemini` 或 `all`）：**
```
name: "gemini-reviewer", run_in_background: true
prompt: 你是 Gemini 審查 Teammate。用 Bash 執行（foreground）：
  gemini -p "讀取 {{REVIEW_INPUT}} 並按其中指令審查。結果寫入 {{PROJECT_DIR}}/reviews/review_ch{START}-{END}_gemini.md" --approval-mode auto_edit --output-format text
  若未安裝回報略過。
```

> 派出後**不等待**，立即回到主流程 Step 2。

---

## Step 3.5: 統整外部 AI 發現

預期結果檔案：
- `{{PROJECT_DIR}}/reviews/review_ch{START}-{END}_codex.md`（若有 codex）
- `{{PROJECT_DIR}}/reviews/review_ch{START}-{END}_gemini.md`（若有 gemini）

### 等待 Teammates 完成

1. **先檢查通知**：檢查 context 中是否已有所有 Teammate 的 `<task-notification>`（status=completed）
2. **若全部到齊** → `test -f` 確認檔案存在，直接讀取
3. **若未完成** → 用**單一 Bash call** 的 while 迴圈等待（`timeout: 300000`）：
```bash
seq 1 12 | while read _n; do test -f "{codex_file}" && test -f "{gemini_file}" && echo "READY" && exit 0; sleep 15; done; echo "TIMEOUT"
```
> 只等待實際派出的 assist 對應的檔案。若只有 codex 則只檢查 codex 檔案。
> 結果為 `READY` → 讀取檔案；`TIMEOUT` → 用已到齊的繼續，未到齊標記「逾時未回」
4. **超時** → 用已到齊的繼續，未到齊標記「逾時未回」

### 統整

讀取到齊的檔案，與 Claude 審查報告比對：

1. **去重**：移除與 Claude 審查重複的問題
2. **驗證**：回到原文和設定比對（引用不存在 → 幻覺丟棄，邏輯有誤 → 丟棄）
3. **採納**：通過驗證的標記 `[Codex]` / `[Gemini]`，附加到報告末尾
4. 末尾增加統整摘要：
```
=== 外部 AI 輔助審查 ===
來源：{Codex / Gemini / Codex + Gemini}
新增發現：{n} 項（Critical {x}, Warning {y}, Minor {z}）
已過濾幻覺：{n} 項
與 Claude 審查重複：{n} 項
```

### 清理

統整完成後，使用 `TaskStop` 終止所有仍在運行的 assist sub-agent（`codex-reviewer`、`gemini-reviewer`），避免殘留 background task 佔用資源。
