---
description: 寫一章
---

# /nvChapter - 寫一章

透過 `/nvDraft` + `/nvExpand` 完成一章。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | — |
| `direction` | ❌ | 劇情導引 | — |
| `review` | ❌ | 自動審查 | `true` |
| `maint` | ❌ | 維護模式，僅接受 `true`/`false` | `true` |

## 執行模式：Main Context (B 類)

直接在當前 session 執行，不啟動 sub-agent。

### 初始化
1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. 將下方所有 `{{...}}` 替換為實際值後，依序執行各 Step

> [!IMPORTANT]
> **Sub-agent 環境規則**：若本 SKILL.md 在 sub-agent 內被讀取執行，無法使用 `/nvXXX` Skill 指令。所有 `/nvBeat`、`/nvDraft`、`/nvExpand` 等調用改為「Read 對應 `{{REPO_ROOT}}/.claude/skills/{skillName}/SKILL.md` 並按其指令執行」。

---

## 執行步驟

### Step 0: 檢查節拍
// turbo
讀取 `{{PROJECT_DIR}}/config/narrative_progress.yaml`。若 `current_beat` 為空 → **自動執行** `/nvBeat proj={proj}` 生成後繼續。

> [!CAUTION]
> 不可因為沒有 beats 就暫停或詢問用戶。

### Step 1: 確定章節號碼
// turbo
從 Step 0 已讀取的 `narrative_progress.yaml` 確定章節號 `N`（**不重複讀取**）。
讀取 `{{PROJECT_DIR}}/config/outline_index.yaml` 和 `{{PROJECT_DIR}}/config/outline/arc_{current_arc}.yaml`。

```
📖 開始寫作第 {N} 章 | 專案：{proj} | 導引：{direction 或 "自然推進"} | 流程：nvDraft → nvExpand
```

### Step 2: 生成草稿

> [!CAUTION]
> Step 2 和 Step 3 必須**完整執行** nvDraft/nvExpand 的所有步驟，不可跳過。

```
/nvDraft proj={proj} direction={direction}
```

### Step 3: 擴寫為正文

```
/nvExpand proj={proj} chapter={N}
```

### Step 3.5: 維護與審查（主 Context 內執行）

直接在主 context 內依序執行，不使用 sub-agent。實際執行順序：3.5a → 3.5b → 3.5c → 3.5d。

> [!CAUTION]
> Review 發現的 Critical/Warning **必須立即修正**（3.5b），修正完才執行 Maint（3.5c）。

#### 3.5a: nvReview light

若 `review=false` → 跳過整個 3.5a + 3.5b。
讀取 `{{REPO_ROOT}}/.claude/skills/nvReview/SKILL.md`，按其初始化 section 設定變數後，依序執行各 Step。
參數：`proj`={{PROJ}}, `mode`=light, `chapter`={N}, `assist`=none

#### 3.5b: 自動修正

若有 Critical/Warning：
1. 逐一修正（最小改動，消除矛盾 + 保持文風 + 不引入新問題）
2. 若涉及設定變更，同步更新 yaml
3. 字數再校驗——若修正僅改措辭未刪除大段文本則跳過；不足則補充。校驗指令：`cd {{REPO_ROOT}} && .venv/bin/python tools/word_count.py {{PROJECT_DIR}}/output/chapters/chapter_{N}.md`
4. 再次 nvReview light（最多 2 輪），仍有 Critical → 標註 `🔴 未解決`

#### 3.5c: nvMaint light

若 `maint=false` → 跳過。
修正完成後才執行本步驟（確保 Maint 基於修正後的文本）。
讀取 `{{REPO_ROOT}}/.claude/skills/nvMaint/SKILL.md`，按其初始化 section 設定變數後，依序執行各 Step。
參數：`proj`={{PROJ}}, `mode`=light, `chapter`={N}

#### 3.5d: 進度推進

更新 `{{PROJECT_DIR}}/config/narrative_progress.yaml`：
- `current_chapter`: +1
- `last_updated`: 今日日期

> **禁止**寫入 `completed_chapters` 欄位（已遷至 ChromaDB）。殘留則忽略。

**節拍推進：**
- 清空 `current_beat`
- `upcoming_beats` 有剩餘 → 彈出第一項存入 `current_beat`
- 為空 → 當前 SubArc 移入 `completed_subarcs`（只寫 `id` + `chapters`，不寫 `ending_summary`），推進下一個 SubArc

**章節摘要：** 讀取 `{{REPO_ROOT}}/.claude/skills/memory/chapter_summarizer/SKILL.md`，**嚴格按照保留/去除規則執行**。生成摘要（目標：原文 15-20%），寫入：
```
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} chapter --id {N} --title "..." --arc "..." --subarc "..." --words {word_count} --summary "..."
```
> `{word_count}` 使用 Step 3.5b 字數校驗的結果，不另行計算。

### Step 4: 完成確認
// turbo
```
✅ 第 {N} 章完成 | {title} | {words} 字 / {min}-{max} | 維護：{maint結果} | 審查：{review結果}
```

