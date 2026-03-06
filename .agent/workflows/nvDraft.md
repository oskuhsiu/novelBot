---
description: 生成新章節的情節草稿（精簡骨架，可搭配 /nvExpand 擴寫）
---

# /nvDraft - 章節草稿

為下一章生成精簡的情節草稿——只包含事件骨架（發生什麼、誰做了什麼、結果如何），不寫完整正文。產出寫入章節檔案，之後可用 `/nvExpand` 擴寫。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `direction` | ❌ | 劇情導引 | `direction="潛入敵方基地"` |
| `review` | ❌ | 草稿審查（預設 `true`） | `review=false` |

## 使用範例

```
/nvDraft proj=霓虹劍仙
/nvDraft proj=霓虹劍仙 direction="主角小隊潛入敵方基地失敗"
```

---

## 執行步驟

### Step 1: 載入專案狀態
// turbo

> [!IMPORTANT]
> **Context 去重（強制）**
> 以下每個檔案，讀取前先檢查當前對話 context 中是否**已存在其內容**（例如由 nvChapter Step 0/1、nvBeat、或同輪先前呼叫載入）。
> - **已在 context 中** → 直接複用，**不重複讀取**
> - **不在 context 中** → 正常讀取
> 這條規則適用於本 Skill 所有步驟的所有檔案讀取。

載入（僅 context 中尚未存在的）：
- `config/novel_config.yaml` — 風格、pacing_pointer
- `config/narrative_progress.yaml` — 進度
- `config/outline_index.yaml` + `config/outline/arc_{current_arc}.yaml` — 大綱
- 角色資料庫：`char_query.py --proj {proj} list` → 按需 `get {IDS}` → 按需 `relations {ID}`
- ChromaDB：`lore_query.py --proj {proj} lore "{關鍵詞}" --n 10` + `chapters --recent 5`

### Step 2: 載入連貫性上下文 (Sliding Window Mode)
// turbo
載入最小化的連貫性上下文：

```yaml
連貫性檢查:
  1. 確定當前 SubArc（從 outline/arc_{current_arc}.yaml 讀取）:
     - 僅提取當前 arc 的 subarcs 中，符合 narrative_progress.yaml `active_subarcs` 的部分
     - ❌ 禁止讀取未來的大綱
     
  2. 載入連貫性資料 (滑動視窗):
     - 當前 SubArc 前文: 從 ChromaDB `chapters` collection 讀取 summary
       → 使用 `ChapterVector.get_chapter(chapter_id)` 精確查詢
       → 或 `ChapterVector.get_recent_chapters(n)` 取最近 N 章
     - 上一章: 唯一允許讀取全文的舊章節（若過大，僅讀取最後 2000 字）
     - 上一個 SubArc: 僅讀取 summary（從 ChromaDB）

  2b. Context 去重（同一對話多次呼叫時）:
     - 讀取前，先檢查當前對話中是否已有目標章節的 summary 或全文
       （來自先前的 nvDraft/nvExpand/nvChapter 呼叫）
     - 已存在於 context 的章節：跳過，不重複讀取
     - 僅對 context 中尚未存在的章節查詢 ChromaDB 或讀取檔案
     - 上一章全文同理：若剛在本輪對話中寫完，context 中已有，跳過讀取

  3. Arc 邊界處理:
     - 若跨 Arc，僅讀取 previous_arc_ending
```

### Step 2.5: 檢查冷儲存索引
// turbo
讀取 `memory/archive_index.yaml`，若本章劇情涉及已歸檔角色/物品/事件，提取相關條目注入上下文。

### Step 3: 確定劇情範圍 (Beat Control)
// turbo
從 context 中已有的 `narrative_progress.yaml` 提取 `active_subarcs` 以及 **`current_beat`**（Step 1 已讀取，不重複讀取）。
從 context 中已有的 `outline/arc_{current_arc}.yaml` 提取當前 SubArc 的 `summary` 作為背景脈絡（Step 1 已讀取，不重複讀取）。

> [!IMPORTANT]
> **絕對聚焦於 Current Beat**
> LLM 在生成草稿時，必須**主要根據 `current_beat.summary`** 來推進劇情。
> SubArc summary 僅作為「大方向背景」。
> 確保本章的劇情發展與意外事件被鎖定在當前節拍內，**嚴禁**超車推進到下一個節拍或演完結尾。

### Step 4: 動機地圖與關係動態
分析出場角色動機、識別衝突節點、檢查關係轉折閾值。

### Step 5: 草稿生成

#### 5a: 確定指導
有 `direction` → 使用之。無 → 依 SubArc 自然推進。注入 `pacing_pointer` 指導。

#### 5b: 生成草稿

> [!IMPORTANT]
> **草稿格式規範**
> 草稿只寫「發生什麼」，不寫「怎麼發生」：
> - ✅ 「主角與守衛交戰，突破防線進入基地」
> - ❌ 「主角握緊長劍，冷冷地看著守衛，霓虹燈映在他的臉上…」

輸出格式：

```markdown
# 第 {N} 章 — {章節標題}

## 事件序列

1. {事件描述}
2. {事件描述}
3. ...

## 關鍵決策

- {角色} 選擇 {X}（影響：{後果}）

## 衝突與互動

- {角色A} vs {角色B}：{衝突核心}，結果：{結果}

## 狀態變化

- {角色}: {變化}
- 世界: {變化}

## 章末鉤子

{懸念/轉折描述}
```

#### 5c: 寫入
// turbo
將草稿寫入 `output/chapters/chapter_{N}.md`

### Step 5.5: 草稿邏輯審查【review=true 時】

執行 `/nvReview proj={proj} chapter={N} mode=light`（聚焦情節邏輯和吃書）。

> `review=false` 或從 `/nvBatch` 呼叫時跳過。

### Step 6: 輸出確認
// turbo

使用 `word_counter` 計算字數。

```
📝 第 {N} 章草稿完成 | 標題：{title} | {words} 字 | {event_count} 事件 | SubArc：{id}
下一步：/nvExpand proj={proj} chapter={N}
```

**不修改任何設定檔**（維護由 nvExpand/nvChapter 負責）。
