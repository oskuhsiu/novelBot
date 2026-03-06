---
description: 寫一章
---

# /nvChapter - 寫一章

透過 `/nvDraft` + `/nvExpand` 的兩階段流程完成一章。先生成情節骨架，再擴寫為完整正文。

> [!NOTE]
> 本 workflow 是 `/nvDraft` + `/nvExpand` 的便捷容器。
> 若需要在草稿與擴寫之間手動調整劇情，請分開執行 `/nvDraft` 和 `/nvExpand`。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `direction` | ❌ | 劇情導引指示，引導本章劇情走向 | `direction="敵方來了強力增援，主角陷入危機"` |
| `review` | ❌ | 自動審查（預設 `true`，設 `false` 關閉） | `review=false` |

## 使用範例

```
/nvChapter proj=霓虹劍仙
/nvChapter proj=霓虹劍仙 direction="敵方來了強力增援，主角小隊陷入危機。隊友使用犧牲性技能，讓主角逃脫"
/nvChapter proj=霓虹劍仙 review=false
```

---

## 執行步驟

### Step 0: 檢查並自動生成節拍 (Beats)
// turbo
讀取 `config/narrative_progress.yaml`。檢查 `current_beat` 是否為空 (null 或空值)。

若 `current_beat` 為空，代表當前 SubArc 尚未被拆分或已執行完畢。
**自動執行** `/nvBeat proj={proj}` 生成新的章節節拍，完成後繼續後續步驟。

> [!CAUTION]
> 不可因為沒有 beats 就暫停或詢問用戶。直接自動執行 `/nvBeat` 生成後繼續。

### Step 1: 確定章節號碼
// turbo
從 Step 0 已讀取的 `narrative_progress.yaml` 中，確定下一章的章節號碼 `N` 以及 `active_subarcs`（**不重複讀取**）。
讀取 `config/outline_index.yaml` 和 `config/outline/arc_{current_arc}.yaml`，取得當前 SubArc 資訊。

```
═══════════════════════════════════════════════════════
  📖 開始寫作第 {N} 章
═══════════════════════════════════════════════════════
  專案：{proj}
  章節：第 {N} 章
  劇情導引：{direction 或 "依 SubArc 自然推進"}
  流程：nvDraft → nvExpand
═══════════════════════════════════════════════════════
```

### Step 2: 生成草稿
執行 `/nvDraft`，完整遵循其所有步驟：

```
/nvDraft proj={proj} direction={direction}
```

- nvDraft 會自動載入專案狀態、上下文、SubArc 範圍
- nvDraft 會生成動機地圖與關係動態
- 產出的草稿寫入 `output/chapters/chapter_{N}.md`

### Step 3: 擴寫為正文
執行 `/nvExpand`，完整遵循其所有步驟：

```
/nvExpand proj={proj} chapter={N}
```

- nvExpand 會載入上下文（回顧 + 前瞻）
- nvExpand 會分段生成正文，確保字數達標
- nvExpand 會通過硬性字數閘門校驗
- nvExpand 會執行一致性驗證
> [!CAUTION]
> Step 2 和 Step 3 必須**完整執行** nvDraft/nvExpand 的所有步驟，不可跳過。

### Step 3.5: 維護與審查

直接依序執行輕量維護和審查。

> [!CAUTION]
> Review 發現的 Critical/Warning **必須立即修正**。

#### 3.5a: nvMaint light

執行 `/nvMaint proj={proj} mode=light`

#### 3.5b: nvReview light

若 `review=false` → 跳過。

```
/nvReview proj={proj} chapter={N} mode=light
```

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
