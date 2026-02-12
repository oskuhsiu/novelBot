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

## 使用範例

```
/nvChapter proj=霓虹劍仙
/nvChapter proj=霓虹劍仙 direction="敵方來了強力增援，主角小隊陷入危機。隊友使用犧牲性技能，讓主角逃脫"
```

---

## 執行步驟

### Step 1: 確定章節號碼
// turbo
讀取 `config/narrative_progress.yaml`，確定下一章的章節號碼 `N`。

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
- nvExpand 會執行輕量維護（含 `ending_summary`）

> [!CAUTION]
> **完整執行，不可簡化**
> Step 2 和 Step 3 必須**完整執行** nvDraft 和 nvExpand 的所有步驟。
> 不可因為是從 nvChapter 呼叫而跳過任何步驟（如字數校驗、維護）。

### Step 4: 完成確認
// turbo
```
═══════════════════════════════════════════════════════
  ✅ 第 {N} 章完成
═══════════════════════════════════════════════════════
  章節標題：{title}
  最終字數：{words} / 目標 {min}-{max}（目標 {target}）
  ending_summary：已記錄 ✅
═══════════════════════════════════════════════════════
```

---

## 輸出

章節已寫入 `output/chapters/chapter_{N}.md`，輕量維護已完成。

如需完整更新所有設定，請執行 `/nvMaint proj={proj} mode=full`
