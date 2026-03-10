---
description: 寫一章
---

# /nvChapter - 寫一章

透過 `/nvDraft` + `/nvExpand` 完成一章。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `direction` | ❌ | 劇情導引 | `direction="敵方增援，主角陷入危機"` |
| `review` | ❌ | 自動審查（預設 `true`） | `review=false` |

---

## 執行步驟

### Step 0: 檢查節拍
// turbo
讀取 `config/narrative_progress.yaml`。若 `current_beat` 為空 → **自動執行** `/nvBeat proj={proj}` 生成後繼續。

> [!CAUTION]
> 不可因為沒有 beats 就暫停或詢問用戶。

### Step 1: 確定章節號碼
// turbo
從 Step 0 已讀取的 `narrative_progress.yaml` 確定章節號 `N`（**不重複讀取**）。
讀取 `config/outline_index.yaml` 和 `config/outline/arc_{current_arc}.yaml`。

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

直接在主 context 內依序執行，不使用 sub-agent。

> [!CAUTION]
> Review 發現的 Critical/Warning **必須立即修正**。

#### 3.5a: nvMaint light

讀取 `{REPO_ROOT}/.claude/skills/nvMaint/SKILL.md` 的 Agent Prompt，**在主 context 中遵循執行**。
參數：`PROJECT_DIR`=專案路徑, `PROJ`=名稱, `MODE`=light, `REPO_ROOT`=工作目錄

#### 3.5b: nvReview light

若 `review=false` → 跳過。
讀取 `{REPO_ROOT}/.claude/skills/nvReview/SKILL.md` 的 Agent Prompt，**在主 context 中遵循執行**。
參數：`PROJECT_DIR`=專案路徑, `PROJ`=名稱, `MODE`=light, `RANGE_OR_CHAPTER`=chapter={N}

#### 3.5c: 自動修正

若有 Critical/Warning：
1. 逐一修正（最小改動，消除矛盾 + 保持文風 + 不引入新問題）
2. 若涉及設定變更，同步更新 yaml
3. 字數再校驗（`word_counter`），不足則補充
4. 再次 nvReview light（最多 2 輪），仍有 Critical → 標註 `🔴 未解決`

### Step 4: 完成確認
// turbo
```
✅ 第 {N} 章完成 | {title} | {words} 字 / {min}-{max} | 維護：✅ | 審查：{結果}
```

