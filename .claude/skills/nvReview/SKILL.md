---
description: 執行一致性檢查
---

# /nvReview - 一致性與邏輯審查

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `range` | ❌ | 檢查範圍 | 最近 5 章 |
| `chapter` | ❌ | 指定審查單章 | — |
| `mode` | ❌ | `light` / `full` | `full` |
| `assist` | ❌ | 外部 AI 輔助（`none`/`codex`/`gemini`/`all`） | `none` |

- `light`：Cat 1-4（含 2.5；4c 除外），報告僅列 Critical/Warning
- `full`：全部 Cat 1-8（含 2.5）+ 批判性閱讀
- `chapter` 與 `range` 擇一，都未指定則審查最近 5 章
- `assist`：派出 Teammates 平行執行外部 AI 審查

## 執行模式：Main Context (B 類)

直接在當前 session 執行，不啟動 sub-agent。只有 assist teammates 使用 background sub-agent。

### 初始化
1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. `{{MODE}}` = mode 參數值（預設 `full`）
4. `{{ASSIST}}` = assist 參數值（預設 `none`）
5. 將下方所有 `{{...}}` 替換為實際值後，依序執行各 Step

## CLI Placeholder

以下為 CLI 命令縮寫。`{{...}}` = 初始化/本表定義的固定值；`{...}` = 執行時動態替換。`{{REPO_ROOT}}`/`{{PROJ}}`/`{{PROJECT_DIR}}`/`{{MODE}}`/`{{ASSIST}}` 定義見上方初始化 section。**先解析 `{{PROJ}}`，再展開其他 Placeholder。** Step 內 code block 省略 `cd` 前綴，實際執行時補上：

1. 讀取：`cd {{REPO_ROOT}} && cmd1 && cmd2`（失敗即停）
2. 寫入：`cd {{REPO_ROOT}} && cmd1 ; cmd2 ; cmd3`（`cd` 用 `&&` 確保成功，`;` 串連後續寫入，單項失敗不阻斷）
3. 先批次載入，再分析審查

| Placeholder | 展開為 |
|-------------|--------|
| `{{CHAR}}` | `.venv/bin/python tools/char_query.py --proj {{PROJ}}` |
| `{{ITEM}}` | `.venv/bin/python tools/item_query.py --proj {{PROJ}}` |
| `{{LORE_Q}}` | `.venv/bin/python tools/lore_query.py --proj {{PROJ}}` |
| `{{FAC}}` | `.venv/bin/python tools/faction_query.py --proj {{PROJ}}` |
| `{{ATLAS}}` | `.venv/bin/python tools/atlas_query.py --proj {{PROJ}}` |
| `{{REVIEW}}` | `.venv/bin/python tools/review_query.py --proj {{PROJ}}` |

## Step 0:【必執行】初始化

```
mkdir -p {{PROJECT_DIR}}/reviews
```

## Step 1:【必執行】載入審查素材

> **最小載入原則**：只載入審查範圍章節實際需要的資料，不 dump 整個資料庫。
> **並行原則**：無依賴的讀取/查詢必須在**同一個 API turn** 內並行發出，減少 API call。

### 1a. 確定審查範圍（1 turn）

讀取 `narrative_progress.yaml` 的 `current_chapter`。**注意：`current_chapter` 語義是「下一章待寫編號」，最新已完成章節 = `current_chapter - 1`。** 以此為基準，用 `range`/`chapter` 參數計算目標章節範圍（{START}-{END}），再從 progress 區塊找出所屬 subarc。

### 1b. 並行載入所有素材（1 turn，多個 tool call）

確定範圍後，在**同一個 API turn** 內並行發出以下所有 tool call：

**Read（並行）：**
- 所有目標章節全文（每章一個 Read，並行發出）
- 前文參照章節（light 單章用 Bash `{{LORE_Q}} chapters --recent 3 --full` 替代）
- `novel_config.yaml`（若 context 中無）
- `power_system.yaml`（full mode 且章節涉及能力使用時）
- Outline 檔（full mode：目標章節所屬 arc 的 `arc_N.yaml`）
- `{{REPO_ROOT}}/.claude/skills/nvHumanize/patterns.md`（若 context 中無）

> 所有已在 context 中的檔案跳過，不重複讀取。

### 1c. 資料庫查詢（1 turn，多個 Bash 並行）

掃描已載入的章節文本，識別登場角色和涉及物品，在**同一個 API turn** 內並行發出：

```
# Bash call 1: 角色（只 get 登場角色）
{{CHAR}} get {登場角色IDs}
# Bash call 2: 物品（full mode，涉及物品時才查；無則跳過）
{{ITEM}} get {涉及物品IDs}
# Bash call 3: ChromaDB lore（full mode）
{{LORE_Q}} lore-by-chapter {START}
```

> 若章節無物品相關內容，跳過物品查詢。balance / bibi-pending 只在涉及經濟交易時才查。

### 1d. 載入完成

> **所有資料在 Step 1 一次載入完畢**。後續步驟僅允許 ChromaDB 語意搜尋及按需 CLI 驗證查詢，不再批次載入新檔案。

## Step 1.5:【ASSIST ≠ none 時】寫暫存檔 + 派出 Teammates

> 若 `{{ASSIST}}` = `none`，跳過。否則讀取 `{{REPO_ROOT}}/.claude/skills/nvReview/assist_flow.md` 的 Step 1.5 並按步驟執行。

## Step 2:【必執行】批判性閱讀 + 分類審查

> 章節已在 Step 1 載入，不需重複讀取。

### 【full mode only】批判性閱讀

不帶 checklist，像人類編輯逐段閱讀。對每一段問：
1. **邏輯自洽**：推導/計算是否內部自洽？
2. **Config 比對**：數字/規則是否與 config 一致？（**config 是 source of truth**，lore 可能有錯）
3. **認知匹配**：角色知識和確信程度是否匹配其資訊量？
4. **直覺異常**：有無「讀起來怪怪的」但不屬於任何 Category 的東西？

> 發現併入 Step 3 報告（標記 `[批判性閱讀]`）。

## 審查類別

### 🔴 Cat 1: 情節邏輯 【light ✅ | full ✅】
- **時間線矛盾**：年齡vs事件、章節間時間流逝、同日事件排列
- **因果矛盾**：結果與前提衝突、重傷後無交代恢復、同時在兩地
- **數量/距離錯誤**：兵力資源不一致、旅行時間不合理
- **內部邏輯自洽**：同一段落中推理/計算、術語定義前後一致？數字推導每步成立？

### 資源數字精度容差

審查前讀取 `novel_config.yaml` 的 `style_profile.resource_precision`（預設 `relative`）：
- **strict**：所有資源數量偏差 → Critical
- **relative**：低於主角當前等階一階的資源，±5 不計 Warning；低兩階以上不審查數量
- **relaxed**：僅審查劇情關鍵資源（涉及交易/賭注/生死門檻），其餘不審查數量

> 主角當前等階從 `char_query.py get` 的 `current_state` 判斷。此容差適用於 Cat 2、Cat 3、Cat 6。

### 🔴 Cat 2: 吃書偵測 【light ✅ | full ✅】

**⚡ 批次查詢流程**（減少 API turn）：
1. 先通讀所有章節，列出所有需要驗證的疑點（純思考，不發 tool call）
2. 將所有疑點的 lore 查詢在**同一個 API turn** 內並行發出：多個 `Bash: {{LORE_Q}} lore "{關鍵詞}" --n 10`
3. 根據結果，若有延伸疑點 → 再次批次並行查詢（同一 turn 發出）
4. 重複直到收斂。同一主題換關鍵詞最多 3 次，仍查不到就以現有資訊判斷

- 世界觀法則被破壞、「不可逆」被逆轉、「唯一」出現第二件
- 已死亡角色無解釋出現、已失去能力無解釋恢復

**Outline 一致性（full mode）：**
- ChromaDB 章節摘要是否與實際章節內容一致
- 相鄰 subarc 之間數據有無不合理跳躍
- 未完成 subarc 的 outline `summary` 與已寫章節方向是否矛盾

**Config vs Text 數值比對（full mode）：**
- 逐一比對文本中引用的數值與 config 定義
- **Config 是 source of truth**，文本偏離 → Critical
- ⚠️ ChromaDB lore 可能有過時數據，不可作為數值驗證唯一依據

### 🔴 Cat 2.5: 資訊邊界 【light ✅ | full ✅】

對每句可疑的角色對白/內心戲，問：「截至本章此刻，這個角色是怎麼知道這件事的？」
答案必須是：親眼見/親耳聽/被告知/合理推理/前文已揭露。答不出來 → Critical。

必抓：
- 未登場角色被點名或預先指派用途
- 角色知道他人的 secret / hidden_profile / hidden_dynamic
- 派系 secret_dealings 被當成 common knowledge
- 限制視角旁白直接斷言他人真實動機
- 角色知道未來章節才會取得的情報

**知識來源分級：**
- 「系統性知識來源」（天道知識庫、AI 輔助、異能感知等）**不能作為萬用藉口**
- 區分：系統可提供（OK，需文中提示來源）/ 經驗知識（需觀察描寫）/ 推理知識（需展示過程）
- 缺少來源提示 → Warning

嚴重度：直接知道不該知道的事 → Critical | 可改猜測語氣修復 → Warning | 有系統來源但缺提示 → Warning

### 🔴 Cat 3: 能力合法性 【light ✅ | full ✅】
- 冷卻/次數限制違反、已消耗品再次出現
- 使用超過等級的能力/未習得技能
- 能力代價被忽略

### 🟡 Cat 4: 錯字與文字品質 + AI 痕跡 【light ✅(4a,4b) | full ✅(全部)】

**4a: 錯字** — 錯別字、同音異形字、漏字多字、標點誤用

**4b: AI 寫作痕跡** — 讀取 `{{REPO_ROOT}}/.claude/skills/nvHumanize/patterns.md`（19 組模式），逐段比對：
- P1 修飾堆疊、P2 贅詞填充、P3 公式開頭/轉場、P4 情感/反應公式
- P5 過度平行、P7 的字連綴、P10 破折號成癮（確有必要或明顯更好時才用，每千字仍 ≤2）
- P11 比喻輪替、P12 對話後必解釋、P14 懸念金句結尾
- P15 角色性格旁白（每章至多 1 次，第 2 次起 → Warning）
- P16「不是X是Y」句式濫用（每千字 ≤1 次，同段連續 → Warning）
- P17 短句斷裂假張力（500 字內 2+ 個單字獨立段落 → Warning）
- P18 旁白替讀者翻譯（「不是在X，是在說Y」→ Warning）
- P19 面板/系統數據灌水（非決策性精確數值 → Warning）
- 命中 → ⚠️ Warning，附原文引用 + 改寫建議

**4b-density: AI 感密度統計**（light + full 均執行）— 對每章統計：
- 「不是…是…」出現次數 / 千字（閾值 ≤1.0，超過 → Warning）
- 精確數字（百分比、小數、面板格式數據塊）出現次數 / 千字（閾值 ≤2.0，超過 → Warning）
- 完整面板格式輸出（【...】數據塊）次數 / 章（閾值 ≤3，超過 → Warning）
- 統計結果附在報告末尾，格式：`📊 AI感密度：不是X是Y {n}/千字 | 精確數字 {n}/千字 | 面板塊 {n}/章`

**⚡ Grep 並行**：所有模式 × 所有章節的 Grep 在**同一個 API turn** 內並行發出。例如 4 個模式 × 3 章 = 12 個 Grep tool call 一次發出。

**4c: 文中字數自洽（full only）** — 掃描「寫下/說了/吐出/留下… X 個字」，數引號內實際字數（標點不算），不符 → Critical。

## === LIGHT MODE 到此結束 ===
## 以下 Categories 5-8 僅 mode=full 時執行

### 🟡 Cat 5: 角色行為一致性 【full only】
- 性格偏差（vs base_profile.traits）、語氣一致性、動機連貫
- traits 是否通過行動和對話展示而非旁白宣告？「一向冷靜的他」→ Warning
- **確信-資訊匹配**：確信程度是否匹配資訊量？零經驗+零驗證卻用斷言語氣 → Warning

### 🟡 Cat 6: 連戲檢查 【full only】
- 物品連續性、傷勢追蹤、位置轉換、服裝/外貌

### 🟢 Cat 7: 世界觀一致性 【full only】
- 地理一致性：章節中提及的地名、距離、環境描述是否與 atlas 記錄一致 → 不符 Warning，嚴重矛盾 Critical
  - 查詢：`{{ATLAS}} search "{地名}"` 或 `{{ATLAS}} get {REG_ID}`
- 勢力領地/據點是否與 faction 記錄一致 → 不符 Warning
  - 查詢：`{{FAC}} get {FAC_ID}`

### 🟡 Cat 8: 冗餘偵測 【full only】
- 與前 2-3 章**語意高度重複**的段落（超過 3 行同一內容重述）→ Warning
- 同一報告/清單/設定在多章重複列舉（應改為簡要引用）→ Warning

## Step 3:【必執行】生成審查報告

```
═══════════════════════════════════════════════════════
  📋 審查報告：{{PROJ}}
  模式：{{MODE}} | 範圍：第 {START} - {END} 章
═══════════════════════════════════════════════════════

🔴 Critical — 必須修正
  [{類別}] [Ch.{N}] {問題}
    引用：「{原文}」
    原因：{為何錯誤}
    建議：{修正方案}

⚠️ Warning — 建議修正
  [{類別}] [Ch.{N}] {問題}
    建議：{修正方案}

💡 Minor — 可選修正
  [{類別}] [Ch.{N}] {問題}

✅ 通過：{列出已通過類別}

  統計：Critical {n} | Warning {n} | Minor {n}
═══════════════════════════════════════════════════════
```

> light 模式：僅列 Critical/Warning。全部通過則輸出 `✅ 第 {N} 章審查通過（light mode）`

## Step 3.5:【ASSIST ≠ none 時】統整外部 AI 發現

> 若 `{{ASSIST}}` = `none`，跳過。否則讀取 `{{REPO_ROOT}}/.claude/skills/nvReview/assist_flow.md` 的 Step 3.5 並按步驟執行。

## Step 4:【必執行】記錄 Review 至資料庫

審查報告輸出後，記錄本次使用的 assist 工具：

```
{{REVIEW}} add {CH} --assists {ASSISTS} --mode {{MODE}} --source {SOURCE}
```

- `{CH}`：逐章記錄。若審查範圍是 A-B，對每一章各執行一次 add
- `{ASSISTS}`：`{{ASSIST}}` 的實際值。`none` → `none`；`codex` → `codex`；`gemini` → `gemini`；`all` → `codex,gemini`。若 Step 3.5 中某 assist 逾時未回，仍記錄已派出的（因為有嘗試）
- `{SOURCE}`：`nvReview`（若被 nvAudit 呼叫，仍記 `nvReview`）

## 注意事項
- 無法使用 `/nvXXX` skill，直接用 Read/Bash/Grep 操作
- **Context 重用**：讀取前確認 context 中是否已存在，已存在則不重複讀取（Step 1 載入的設定檔、角色、章節，後續直接引用 context）
- **Sub-agent 環境**：若本 skill 在 nvAudit sub-agent 內執行，Bash 中禁止使用 `$()` 或 backtick 取得時間戳，改用 Python `datetime`
