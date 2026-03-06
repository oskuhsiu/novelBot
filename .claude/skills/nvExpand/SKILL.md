---
description: 將字數不足的章節擴寫至目標字數
---

# /nvExpand - 章節擴寫

將單一章節擴寫至目標字數範圍。適用於：
- `/nvDraft` 產出的情節骨架 → 擴寫為完整正文
- 任何字數不達標的章節 → 補足至目標

> [!CAUTION]
> **絕對禁令**
> 1. **字數不達標 = 未完成 = 禁止進入下一步**。`words_per_chapter.min` 是硬性下限。
> 2. **禁止將小說本文輸出在對話文字中**。正文唯二的目的地是「變數」和透過工具「寫入硬碟」。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `chapter` | ✅ | 章節號碼 | `chapter=5` |

## 使用範例

```
/nvExpand proj=霓虹劍仙 chapter=5
```

搭配 `/nvDraft` 使用：
```
/nvDraft proj=霓虹劍仙        # 先產出骨架
# （可手動編輯草稿調整劇情方向）
/nvExpand proj=霓虹劍仙 chapter=5   # 再擴寫為完整正文
```

---

## 執行步驟

### Step 0: 載入專案設定
// turbo

> [!IMPORTANT]
> **Context 去重（強制）— 適用於本 Skill 所有步驟**
> 讀取前先檢查 context 中是否已存在（由 nvChapter、nvDraft 等載入）。
> **已在 context** → 直接複用，**禁止重複 Read**。

載入設定（僅讀取 context 中尚未存在的）：
- `config/novel_config.yaml` — words_per_chapter (min/max/target)、content_weights、style_profile
- `config/narrative_progress.yaml` — 當前進度
- `config/outline_index.yaml` + `config/outline/arc_{current_arc}.yaml` — 大綱
- 角色資料庫：`char_query.py --proj {proj} list` / `get {IDS}`
- `output/style_guide.md`（若存在）

```
⚙️ 字數要求：{min} - {max}（目標 {target}） | 擴寫目標：第 {chapter} 章
```

### Step 1: 字數檢測
// turbo

> [!CAUTION]
> **Context 去重（再次強調）**
> `chapter_{chapter}.md` 很可能剛由 nvDraft 寫入，**已在 context 中**。
> 已在 context → **禁止 Read**，直接用 context 中的版本。

使用 `word_counter` 技能計算字數（參見 `.claude/skills/execution/word_counter/SKILL.md`）。

若字數已在 min ~ max 範圍 → 報告達標並結束。

### Step 2: 載入上下文
// turbo
**回顧**：當前 SubArc 摘要 + 上一章全文（context 中已有則複用）
**前瞻**：下一章內容（草稿→讀全文取前 1-2 事件；正文→讀前 2000 字；不存在→無約束）

開頭必須銜接上一章結尾，結尾必須銜接下一章開頭（若存在）。

### Step 3: 擬定擴寫計畫

| 內容類型 | 模式 | 策略 |
|----------|------|------|
| 骨架草稿 | 全面擴寫 | 每個事件骨架句→場景，依重要性分配字數 |
| 正文不足 | 補強模式 | 識別薄弱段落，針對性擴充 |

**字數規劃（強制）**：規劃總字數 **必須 ≥ target**。場景不夠→在此步驟新增場景。

```
📊 模式：{模式} | 目標：{target} 字 | 當前：{current} 字 | 規劃：{planned} 字 ({scene_count} 場景)
```

### Step 4: 分段擴寫

> [!CAUTION]
> **禁止**一次生成整章。必須分段寫作，每段寫完後計算累計字數。

依 Step 3 場景分配逐場景生成。若累計 + 剩餘規劃 < target → 擴充或追加場景。

擴寫原則：展開事件過程、深化互動對話、補充環境感官描寫、挖掘內心活動。遵守 content_weights 和 style_profile。禁止灌水、重複描述、新增草稿外劇情線。

結尾銜接：參照前瞻上下文，確保角色位置/狀態與下一章吻合。

### Step 5: 字數校驗（硬性閘門）
// turbo

> [!CAUTION]
> **HARD GATE — 不可跳過**
> - `< min` → 回到 Step 4 擴充（最多 3 次）
> - `> max` → 精簡過渡和重複
> - `min ≤ count ≤ max` → ✅ 通過

### Step 6: 一致性驗證

驗證：不違反 ChromaDB lore/角色資料庫、角色行為一致、上下章銜接連貫。

### Step 7: 寫入檔案
// turbo

覆寫 `output/chapters/chapter_{chapter}.md`。正文直接寫入，對話只輸出路徑和字數。

> nvExpand 不做任何維護操作，由 nvChapter/nvBatch 的 sub-agent 處理。

### Step 8: 完成確認
// turbo
```
✅ 第 {chapter} 章擴寫完成 | 標題：{title} | {before}→{after} 字 ({ratio}x) | 目標 {min}-{max}
```

---

## 錯誤處理

| 錯誤 | 處理 |
|------|------|
| 章節不存在 | 停止，提示先 /nvDraft |
| 字數不達標 | 回 Step 4，最多 3 次 |
| 角色不一致 | 標記並修正 |
