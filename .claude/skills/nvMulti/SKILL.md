---
description: 批次草稿與擴寫多章（多章模式，可先批次草稿再逐章擴寫）
---

# /nvMulti - 多章批次草稿與擴寫

一次生成多章草稿，每章基於前一章結果遞進，確保因果連貫。產出後可選擇自動逐章擴寫。

> [!CAUTION]
> **逐章處理原則**
> 即使是多章模式，每章的草稿與擴寫都是獨立的完整任務。
> - ❌ 禁止同時思考所有章節再批次產出
> - ❌ 禁止在對話中直接輸出正文（正文只寫入檔案）
> - ✅ 每章獨立生成、獨立驗證

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `n` | ✅ | 生成章數 | `n=5` |
| `mode` | ❌ | `draft`=僅草稿、`full`=草稿+擴寫（預設 `draft`） | `mode=full` |
| `direction` | ❌ | 每章都套用的統一方向 | `direction="保持壓抑氣氛"` |
| `global_note` | ❌ | 多章主題，自動拆分為每章的遞進指導 | `global_note="建設與擴張"` |
| `review` | ❌ | 草稿完成後審查（預設 `true`，設 `false` 關閉） | `review=false` |

> [!NOTE]
> `direction` 與 `global_note` 的差異：
> - `direction`：每章都套用相同方向
> - `global_note`：自動拆分為每章的遞進指導（見 Step 2）

## 使用範例

僅草稿（之後手動檢視再逐章擴寫）：
```
/nvMulti proj=霓虹劍仙 n=5
/nvMulti proj=霓虹劍仙 n=5 global_note="建設能源設備與採礦機工廠"
/nvMulti proj=霓虹劍仙 n=3 direction="保持壓抑氣氛"
```

草稿 + 自動擴寫：
```
/nvMulti proj=霓虹劍仙 n=5 mode=full
```

僅草稿，之後手動擴寫：
```
/nvMulti proj=X n=5              # 生成 5 章草稿
# （檢視 & 手動調整各章草稿）
/nvExpand proj=X chapter=6       # 逐章擴寫
/nvExpand proj=X chapter=7
...
```

---

## 執行步驟

### Step 1: 載入專案狀態
// turbo

> [!IMPORTANT]
> **Context 去重（強制）**
> 以下每個檔案，讀取前先檢查當前對話 context 中是否**已存在其內容**。
> - **已在 context 中** → 直接複用，**不重複讀取**
> - **不在 context 中** → 正常讀取

需要以下檔案（僅讀取 context 中尚未存在的）：
- `config/novel_config.yaml` - 風格設定、pacing_pointer
- `config/narrative_progress.yaml` - 當前進度
- `config/outline_index.yaml` - 大綱目錄
- `config/outline/arc_{current_arc}.yaml` - 當前卷大綱結構（arcs/subarcs）
查詢角色資料庫（SQLite）：
```bash
# 載入角色摘要（低 token，開頭做一次）
.venv/bin/python tools/char_query.py --proj {proj} list
# 按需載入出場角色資料（過濾隱藏資訊）
.venv/bin/python tools/char_query.py --proj {proj} get-public {CHAR_IDS}
```

查詢 ChromaDB 長期記憶：
```bash
# 語意搜尋與本章相關的 lore（根據 SubArc summary 或 direction）
.venv/bin/python tools/lore_query.py --proj {proj} lore "{subarc_summary 或 direction 關鍵詞}" --n 10
# 取得最近 5 章的 ending_summary
.venv/bin/python tools/lore_query.py --proj {proj} chapters --recent 5
```

### Step 2: Global Note 排程規劃【有 global_note 時執行】

若提供了 `global_note`，將其拆分為 `n` 個章節的遞進指導：

```yaml
排程規劃:
  1. 分析 global_note 的核心目標
  2. 結合當前 SubArc 大綱，規劃 n 章的遞進路線
  3. 每章有明確的「重點」和「預期進展」
  4. 考慮敘事節奏：起步 → 發展 → 困難 → 推進 → 成果
```

輸出排程：
```
═══════════════════════════════════════════════════════
  📋 草稿排程規劃
  主題：{global_note}
  章數：{n}
═══════════════════════════════════════════════════════
  第 {start} 章：{chapter_note_1}
  第 {start+1} 章：{chapter_note_2}
  ...
═══════════════════════════════════════════════════════
```

### Step 3: 草稿生成迴圈

對於 `i = 1 到 n`，依序執行：

#### Step 3a: 載入連貫性上下文 (Sliding Window)

載入最小化的連貫性上下文：
- 當前 SubArc 前文: 從 ChromaDB `chapters` collection 讀取 summary
- 上一章: 唯一允許讀取全文的舊章節（若過大，僅讀取最後 2000 字）
- 上一個 SubArc: 僅讀取 summary（從 ChromaDB）
- Context 去重：讀取前先檢查 context 中是否已有（來自先前迴圈產出）

檢查冷儲存索引：讀取 `memory/archive_index.yaml`，若本章劇情涉及已歸檔角色/物品/事件，提取相關條目。

#### Step 3b: 確定本章指導
- 若有 `global_note` → 使用排程的 `chapter_notes[i]`
- 若有 `direction` → 使用 `direction`
- 若都無 → 依照 SubArc 大綱自然推進
- **強制注入 `pacing_pointer` 指導方針**

#### Step 3c: 確定劇情範圍 (Beat Control)

從 `narrative_progress.yaml` 提取 `current_beat`。
若 `current_beat` 為空，先自動呼叫 `/nvBeat proj={proj}` 生成。

> [!IMPORTANT]
> **絕對聚焦於 Current Beat**
> 必須主要根據 `current_beat.summary` 來推進劇情。SubArc summary 僅作為背景。

#### Step 3d: 生成動機地圖與關係動態
使用 `skill_motivation_engine`（若可用）分析出場角色動機。
使用 `skill_relationship_dynamics`（若可用）更新關係積分。

#### Step 3e: 生成第 i 章草稿

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

#### Step 3f: 上下文遞進【多章模式的關鍵】

> [!CAUTION]
> **因果鏈接（強制）**
> 生成第 i+1 章草稿前，**必須**將第 i 章草稿的結果納入上下文：
> 1. 將第 i 章的「狀態變化」視為第 i+1 章的起始狀態
> 2. 將第 i 章的「章末鉤子」視為第 i+1 章的開場觸發
> 3. 若第 i 章推進了 SubArc 進度，更新內部的 pacing 追蹤
>
> **禁止行為**：
> - ❌ 忽略前一章草稿的結果
> - ❌ 讓第 i+1 章的狀態與第 i 章矛盾
> - ❌ 重複第 i 章已發生的事件

```yaml
上下文遞進邏輯:
  draft_context:
    chapter_{i}_ending:
      events_summary: "..." # 第 i 章事件摘要
      state_changes: [...]  # 狀態變化
      hook: "..."           # 章末鉤子
      subarc_progress: "..."# SubArc 推進情況

  # → 注入為第 i+1 章的 continuity_context
```

#### Step 3g: SubArc 邊界處理

若第 i 章推進完成了當前 SubArc：
1. 內部標記 SubArc 為已完成
2. 讀取下一個 SubArc 的 summary 作為新目標
3. 若跨 Arc，讀取新 Arc 的開篇設定

> [!NOTE]
> 此處僅在內部追蹤進度，不實際修改 `narrative_progress.yaml`。

#### Step 3h: 寫入章節檔案
// turbo
將草稿寫入 `output/chapters/chapter_{N}.md`

### Step 4: 草稿邏輯審查【review=true 時執行】

若 `review` 不為 `false`，對完成的所有草稿執行邏輯檢查：

```
/nvReview proj={proj} range={start}-{end} mode=light
```

> [!NOTE]
> 草稿階段的 review 聚焦**情節邏輯**和**吃書偵測**。

- 若發現 Critical 問題，標註 ⚠️
- 若全部通過，輸出 `✅ 草稿審查通過`

### Step 5: 草稿完成報告
// turbo

使用 `word_counter` 技能計算字數（參見 `.claude/skills/execution/word_counter/SKILL.md`）。

```
═══════════════════════════════════════════════════════
  📝 批次草稿完成 ({n} 章)
═══════════════════════════════════════════════════════
  第 {start} 章：{title} — {一句話摘要} ({words} 字)
  第 {start+1} 章：{title} — {一句話摘要} ({words} 字)
  ...
───────────────────────────────────────────────────────
  SubArc 進度：{subarc_id} → {ending_subarc_id}
═══════════════════════════════════════════════════════
```

**若 `mode=draft`（預設）**：在此結束，輸出後續建議：
```
  下一步：
  - 檢視各章草稿，視需要手動調整
  - 逐章執行 /nvExpand proj={proj} chapter={N}
```

**若 `mode=full`**：自動進入 Step 6。

---

### Step 6: 逐章擴寫迴圈【僅 mode=full】

> [!CAUTION]
> **逐章迴圈規則（強制）**
> ```
> for i = start to start + n - 1:
>     呼叫 /nvExpand proj={proj} chapter={i}
>     ↓ 第 i 章確認完成（字數達標 + 檔案已寫入）
>     ↓ 然後才開始第 i+1 章
> end
> ```
> - **禁止**同時處理多章
> - **禁止**在完成 n 章之前停下來等待用戶指示
> - 第 i 章完成後，立即自動進入第 i+1 章

對於每一章，呼叫 `/nvExpand proj={proj} chapter={i}` 完成擴寫。

### Step 7: 批次完成報告【僅 mode=full】
// turbo
```
═══════════════════════════════════════════════════════
  🚀 批次擴寫完成（共 {n} 章）
═══════════════════════════════════════════════════════
  擴寫範圍：第 {start} ~ 第 {start+n-1} 章

  逐章字數：
  ├─ 第 {start} 章：{before_1} → {after_1} 字（{ratio_1}x）✅
  ├─ 第 {start+1} 章：{before_2} → {after_2} 字（{ratio_2}x）✅
  └─ ...

  總字數產出：{total_words}
  所有章節達標：✅ / ⚠️
═══════════════════════════════════════════════════════
```

---

## 輸出

草稿已寫入 `output/chapters/chapter_{N}.md`（每章各一檔）。

**不修改任何設定檔**（維護由擴寫後的呼叫者負責）。

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| 擴寫字數不足 | 由 nvExpand 內部處理（重試機制） |
| 角色不一致 | 標記問題並修正後繼續 |
| Beat 為空 | 自動呼叫 /nvBeat 生成 |

## 常見陷阱提醒

> [!WARNING]
> 1. **「偷懶」現象**：章數多時 LLM 傾向縮短每章。解法：逐章獨立處理。
> 2. **虎頭蛇尾**：第一章詳細，後面越來越短。解法：每章獨立任務，相同標準。
> 3. **忽略因果鏈**：後面章節忘記前面章節的狀態變化。解法：Step 3f 強制上下文遞進。
