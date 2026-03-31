---
description: 將 SubArc 動態拆分成數個章節節拍 (Beats)
---
# /nvBeat - 次綱拆分

這是輔助工作流，當切換到新的 SubArc 時被觸發。它會讀取 `pacing_pointer` 參數，評估需要將這個 SubArc 展開成多少章節，並為每一章規劃出「帶有意外與衝突」的具體節拍 (Beat)。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `pacing` | ❌ | 強制指定節奏 (覆蓋 config) | — |

## 使用範例

```
/nvBeat proj=eve
/nvBeat proj=eve pacing=0.5
```

---

## 執行模式：Main Context (B 類)

直接在當前 session 執行，不啟動 sub-agent。

### 初始化
1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. 將下方所有 `{{...}}` 替換為實際值後，依序執行各 Step

> [!IMPORTANT]
> **Sub-agent 環境規則**：若本 SKILL.md 在 sub-agent 內被讀取執行，無法使用 Skill tool。所有 `/nvStyleBank` 調用改為「Read `{{REPO_ROOT}}/.claude/skills/nvStyleBank/SKILL.md` 並按其指令執行」。Skill 結果不是本流程的最終輸出，取得風格範本後必須繼續執行後續步驟。

## CLI Placeholder

以下為 CLI 命令縮寫。`{{...}}` = 初始化/本表定義的固定值；`{...}` = 執行時動態替換。`{{REPO_ROOT}}`/`{{PROJ}}`/`{{PROJECT_DIR}}` 定義見上方初始化 section。**先解析 `{{PROJ}}`，再展開其他 Placeholder。** Step 內 code block 省略 `cd` 前綴，實際執行時補上：

1. 讀取：`cd {{REPO_ROOT}} && cmd1 && cmd2`（失敗即停）

| Placeholder | 展開為 |
|-------------|--------|
| `{{LORE_Q}}` | `.venv/bin/python tools/lore_query.py --proj {{PROJ}}` |

## 執行步驟

### Step 1: 載入專案狀態與 SubArc 資訊
// turbo

> [!IMPORTANT]
> **Context 去重（強制）— 適用於本 Skill 所有步驟**
> 讀取前先檢查 context 中是否已存在（由 nvChapter Step 0/1 等載入）。
> **已在 context** → 直接複用，**禁止重複 Read**。

載入（僅 context 中尚未存在的）：
- `{{PROJECT_DIR}}/config/narrative_progress.yaml` — 讀取 `active_subarcs`
- 根據 `active_subarcs`（例如 `A1_S3`），讀取 `{{PROJECT_DIR}}/config/outline/arc_{N}.yaml` 中對應 SubArc 的完整資訊（title, summary, characters, location, emotion_shift 等）
- `{{PROJECT_DIR}}/config/novel_config.yaml` — 讀取 `engine_settings.pacing_pointer`
- `{{PROJECT_DIR}}/output/style_guide.md`（若存在且 context 中尚未載入）— 酌量參考，影響節拍的語調和節奏規劃
- **伏筆清單**（ChromaDB）：`{{LORE_Q}} lore "伏筆" --category foreshadowing --n 20`

```
═══════════════════════════════════════════════════════
  🪚 開始拆分 SubArc：{active_subarcs}
═══════════════════════════════════════════════════════
  專案：{proj}
  目標綱要：{subarc_title}
  Pacing 指針：{pacing_pointer}
═══════════════════════════════════════════════════════
```

### Step 2: 產生節拍 (Beats)

依以下規則拆分 SubArc 為多個章節節拍：

#### 2a: Pacing 計算

當前 `pacing_pointer`（節奏指針）= {pacing_pointer}（若有 `pacing` 參數則覆蓋）。
對應章節數公式：
- 1.0 → 1 章（極快）
- 0.5 → 2 章（中等）
- 0.2 → 5 章（慢放日常）
- 0.1 → 10 章（極限慢放）

允許根據 SubArc 的情節密度彈性調整 ±2 章。**彈性調整應基於情節密度，非預設取極值。**

#### 2b: 拆分規則

1. 每個 Beat（每一章）的極簡述中，**必須適度添加「意外因子」、「衝突」或「小插曲」**，不要讓它只是流水帳。即使是「純日常」也要有戲劇張力。
2. 輸出格式必須是嚴格的 YAML 陣列格式。
3. **伏筆整合**：檢查已載入的 active/dormant 伏筆清單，判斷哪些 beat 適合 hint（暗示）、reinforce（強化）或 reveal（揭曉）某條伏筆。若適合，在該 beat 的 summary 中標記，例如：`（伏筆暗示：LOOP_XXX）`。不強制每個 beat 都要用伏筆，但不要遺忘長期休眠的伏筆。

#### 2c: 風格參考

- 語調定位：參考 style_guide.md 的 narrator personality、rhythm（若存在）
- 風格錨定：使用 Skill tool 呼叫 `/nvStyleBank` 取得 1 段最接近本 SubArc 基調的真人範本：
  ```
  Skill: nvStyleBank
  args: "proj={{PROJ}} {專案genre} {SubArc基調關鍵詞} n=1 format=brief"
  ```
  讓 beat 的 title 和 summary 語調帶有專案風格（不是通用的「主角發現敵人」）。
  - 收到失敗標記 → 退回使用 style_guide.md 的示範段落（若存在），或跳過風格錨定
  - 收到帶 `[UNMATCHED]` 的結果 → 仍使用，完成後附加：`建議補充風格範本：/nvStyleBankBuilder tags={缺失tags}`

#### 2d: 輸出格式

```yaml
beats:
  - title: "第1拍的標題"
    summary: "第1拍的20~30字極簡述（包含意外因子）。"
  - title: "第2拍的標題"
    summary: "第2拍的20~30字極簡述（包含意外因子）。"
```

SubArc 資訊參考：ID、Title、Summary、參與角色與地點（來自 Step 1 載入的 outline）。

### Step 3: 更新 Narrative Progress
// turbo

將產出的 YAML 陣列寫入 `{{PROJECT_DIR}}/config/narrative_progress.yaml`。

1. 從陣列中取出第一項 (index 0)，放入 `current_beat`。
2. 將剩餘的項目 (index 1 到 N) 放入 `upcoming_beats`。

```yaml
current_beat:
  title: "第1個標題"
  summary: "第1個極簡述"
upcoming_beats:
  - title: "第2個標題"
    summary: "第2個極簡述"
  - title: "第3個標題"
    summary: "第3個極簡述"
```

### Step 4: 輸出報告
// turbo

```
═══════════════════════════════════════════════════════
  ✅ SubArc 拆分完成
═══════════════════════════════════════════════════════
  共拆出 {N} 個節拍 (Beats)
  當前需寫作 Beat：{current_beat.title}

  現在可以執行 `/nvDraft` 產生本章草稿。
═══════════════════════════════════════════════════════
```
