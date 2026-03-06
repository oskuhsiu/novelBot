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
> **Context 去重（強制）— 適用於本 Skill 所有步驟**
> 讀取前先檢查 context 中是否已存在（由 nvChapter Step 0/1、nvBeat 等載入）。
> **已在 context** → 直接複用，**禁止重複 Read**。

載入（僅 context 中尚未存在的）：
- `config/novel_config.yaml` — 風格、pacing_pointer
- `config/narrative_progress.yaml` — 進度
- `config/outline_index.yaml` + `config/outline/arc_{current_arc}.yaml` — 大綱
- 角色資料庫：`char_query.py --proj {proj} list` → 按需 `get {IDS}` → 按需 `relations {ID}`
- ChromaDB：`lore_query.py --proj {proj} lore "{關鍵詞}" --n 10` + `chapters --recent 5`

### Step 2: 載入連貫性上下文
// turbo

```yaml
連貫性檢查:
  1. 當前 SubArc（從 outline 讀取，❌ 禁止讀取未來大綱）
  2. 滑動視窗:
     - 當前 SubArc 前文: ChromaDB chapters summary
     - 上一章: 唯一允許讀取全文的舊章節
     - 上一個 SubArc: 僅 summary
  3. Context 去重: 已在 context 的章節跳過
  4. 跨 Arc: 僅讀取 previous_arc_ending
```

### Step 2.5: 檢查冷儲存索引
// turbo
讀取 `memory/archive_index.yaml`，若本章涉及已歸檔條目則提取注入。

### Step 3: 確定劇情範圍 (Beat Control)
// turbo

> [!IMPORTANT]
> **絕對聚焦於 current_beat.summary**
> SubArc summary 僅作為大方向背景。**嚴禁**超車推進到下一個節拍或演完結尾。

### Step 4: 動機地圖與關係動態

分析出場角色動機、識別衝突節點、檢查關係轉折閾值。

### Step 5: 草稿生成

#### 5a: 確定指導
有 `direction` → 使用之。無 → 依 SubArc 自然推進。注入 `pacing_pointer` 指導。

#### 5b: 生成草稿

> [!IMPORTANT]
> 草稿只寫「發生什麼」，不寫「怎麼發生」。

輸出格式：

```markdown
# 第 {N} 章 — {標題}

## 事件序列
1. {事件}
2. {事件}

## 關鍵決策
- {角色} 選擇 {X}（影響：{後果}）

## 衝突與互動
- {A} vs {B}：{核心}，結果：{結果}

## 狀態變化
- {角色}: {變化}

## 章末鉤子
{懸念/轉折}
```

#### 5c: 寫入
// turbo
寫入 `output/chapters/chapter_{N}.md`

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
