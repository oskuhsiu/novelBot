---
description: 批次寫作多章（狀態機模式）
---

# /nvBatch - 狀態機批次寫作

> [!CAUTION]
> **狀態機強制執行聲明**
> 此 workflow 採用「配置檔驅動的狀態機模式」。
> 每次迴圈只專注於**一章**的生成與審查，完成後更新設定檔，並**自動**遞迴觸發下一章，直到達成設定檔中的目標章數為止。
> 
> **禁止行為**：
> - ❌ 一次性生成多章草稿（嚴禁 `/nvMulti`）。只能每次生成1章草稿。
> - ❌ 嚴禁在同一個文字回應或同一次產出中，一口氣連寫多章正文。AI 往往會因為想要「一次做完」而偷工減料。
> - ❌ 嚴禁「假跑」或「模擬」執行流程。每個章節都「必須」獨立發起工具調用，確實經歷讀取、草稿、擴寫、寫入檔案、更新狀態的物理步驟。
> - ❌ 嚴禁將小說本文輸出在對話文字中 (No Sandbox Output)！正文唯二的目的地是「變數」和透過工具「寫入硬碟」。對話框僅能作為狀態與除錯報告用。
> - ❌ 忘記更新 `nvbatch_config.yaml`。
> - ❌ 完成一章後停下來等用戶確認（這是自動批次，不該中斷）。
> 
> **狀態機原子性宣告 (Atomicity)**：
> 每一輪的單章生成都是完全獨立的進程。在第 N 章尚未被實體存入 `.md` 檔案且 `nvbatch_config.yaml` 未成功更新前，第 N+1 章在邏輯上**絕對不存在**，你也絕對不能開始預想下一章的話題。
> 
> **正確行為**：
> - ✅ 初始化/讀取狀態檔 → 生成1章草稿 → 擴寫這1章 → 驗證實體檔案 → 更新狀態檔 → 自動繼續迴圈。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `n` | `init`必填 | 要啟動的新批次章數（若空缺則表示接續未完成的狀態） | `n=5` |
| `proj` | ✅ | 專案名稱 | `proj=bnf` |
| `maint` | ❌ | 維護頻率 (light/every/end)。預設: light | `maint=every` |
| `review` | ❌ | 審查頻率 (light/every/end/false)。預設: light | `review=every` |
| `global_note` | ❌ | 全批次主題/目標 | `global_note="著重絕望感"` |

---

## 狀態機執行流程

### Step 1: 狀態機初始化與讀取
// turbo
檢查 `projects/{proj}/config/nvbatch_config.yaml`。

**情境 A：啟動新批次（用戶提供了 `n` 參數）**
1. 讀取 `projects/{proj}/config/narrative_progress.yaml` 取得 `current_chapter`，設為起始章節。
2. 寫入或覆寫 `projects/{proj}/config/nvbatch_config.yaml`，格式如下：
```yaml
enabled: true
target_chapters: {n}
completed_chapters: 0
current_target: {current_chapter}
start_chapter: {current_chapter}
parameters:
  maint: "{maint}"
  review: "{review}"
  global_note: "{global_note}"
```
3. 印出「狀態機初始化完成」報告。

**情境 B：接續中斷的批次（用戶僅輸入 `/nvBatch proj={proj}`）**
1. 讀取 `nvbatch_config.yaml`。
2. 若 `enabled: false`，回報「目前無進行中的批次任務」。
3. 若 `enabled: true`，印出「狀態機自動接續」報告，進入 Step 2。

---

### Step 2: 狀態判斷與結束條件 (The Gate)
// turbo
讀取 `nvbatch_config.yaml`。

**檢查：** `completed_chapters >= target_chapters`
- **若為 True（已完成所有目標章節）**：
  1. 執行最終維護（如果 parameters.maint 設為 end 或是 full）：
     透過 sub-agent 執行 nvMaint —— 讀取 `{{REPO_ROOT}}/.claude/skills/nvMaint/SKILL.md` 中的 Agent Prompt，填入參數後啟動 Agent tool（`subagent_type: general-purpose`, `model: sonnet`, `run_in_background: false`）
  2. 執行結束審查（如果 parameters.review 設為 light 或 end）：
     透過 sub-agent 執行 nvReview —— 讀取 `{{REPO_ROOT}}/.claude/skills/nvReview/SKILL.md` 中的 Agent Prompt，填入 `range={start_chapter}-{current_target-1}` 和 `mode={review}` 後啟動 Agent tool（`subagent_type: general-purpose`, `model: sonnet`, `run_in_background: false`）
  3. 將 `nvbatch_config.yaml` 的 `enabled` 設為 `false`。
  4. 輸出「👑 批次任務全數完成總結報告」，**終止執行**。
- **若為 False（尚未完成）**：
  進一步檢查 `projects/{proj}/config/narrative_progress.yaml` 中的 `current_beat`。若為空，先自動呼叫 `/nvBeat proj={proj}` 生成 Beat。
  進入 Step 3。

---

### Step 3: 單章極限專注生成 (One-Chapter Loop)
每次只執行**1章**，禁止批次。目標章節為 `current_target`。

#### 3: 單章完整生成與審查
呼叫 `/nvChapter` 來完成草稿、擴寫、以及審查流程（這確保了若 `current_beat` 為空，也會自動觸發 `/nvBeat`）：

```
/nvChapter proj={proj} direction={parameters.global_note} review={parameters.review}
```

這會自動生成 `chapter_{current_target}` 的草稿與正文，並根據 review 參數自動進行審查修復。

#### 3.5: 額外維護 (依參數)
- 如果 `parameters.maint == "every"`，透過 sub-agent 執行 nvMaint：
  讀取 `{{REPO_ROOT}}/.claude/skills/nvMaint/SKILL.md` 中的 Agent Prompt，填入 `mode=full` 後啟動 Agent tool（`subagent_type: general-purpose`, `model: sonnet`, `run_in_background: false`）
(註：nvChapter 已內建 light maint。若 `parameters.maint` 設為 `every`，則每章完成後都會執行 full maint（背景執行）；若設為 `end`，則每一章只會進行 light maint，直到整個批次結束時才在 Step 2 執行一次滿版的 full maint。)

---

### Step 4: 更新狀態與強制遞迴 (Status Update & Self-Trigger)
// turbo
本章節完成後：
1. **實體檔案檢驗閘門 (File Verification Gate)**：
   - 強制要求：呼叫檔案讀取工具，確認 `output/chapters/chapter_{current_target}.md` 確實在硬碟上產生。
   - 檢查該檔案字數，若為 0 則退回重建。沒有通過這個物理檢驗，絕對不准往下執行！
2. **切點更新 (Checkpointing)**：更新 `projects/{proj}/config/nvbatch_config.yaml`：
   - `completed_chapters` += 1
   - `current_target` += 1
   - 更新完畢後，**強制**再用工具讀取一次 `nvbatch_config.yaml`，確認自己沒有寫爛。
3. 輸出單章完成報告：
```
✅ 已完成第 {current_target - 1} 章 | 批次進度：{completed_chapters}/{target_chapters} | 實體檔案已驗證寫入硬碟並建立查核點。
```
4. **【強制遞迴】**：單章結算與接續
身為全自主 Agent，你**絕對不可停下來等待用戶指示**。
但你**也絕對不可在同一次文字輸出中，隨便噴出多章的小說內容**來交差。

> [!IMPORTANT]
> **無縫接軌與防偷懶嚴格守則 (Anti-Lazy Strict Rules)**
> 1. **物理強制分次**：你每次循環都「只處理一章」。當實體驗證通過，且設定檔（Checkpoint）更新並被重新讀取後，當前 Task 才算關閉。此時你才被允許正式「啟動下一輪的 Step 2」。
> 2. **嚴禁合成輸出**：就算我叫你不要停，你也「絕對不准」只用大聲說話的方式連寫多章。你必須確確實實地從「讀檔、檢查目標」開始，為下一章發起再一次完全隔離的 `/nvChapter` 工具調用步驟。
> 3. 只要 `completed_chapters < target_chapters`，Agent 必須自行銜接上述的「實體物理流程」，不斷重複直到目標達成。

---

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| 擴寫字數不足 | 退回 Step 3b 重寫本章，不推進狀態機 |
| 維護失敗 | 重試一次，仍失敗則報告，保留目前 `nvbatch_config.yaml` 狀態 |
| 執行中斷停機 | 用戶隨時可用 `/nvBatch proj={proj}` 自動讀取 config 續傳。 |
