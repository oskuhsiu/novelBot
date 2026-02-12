---
description: 批次寫作多章
---

# /nvBatch - 批次寫作

> [!CAUTION]
> **強制執行聲明**
> 此 workflow 的每個步驟都是**強制性**的，不得跳過或簡化。
> 若任何步驟失敗，必須**立即停止**並報告錯誤，不得繼續執行後續章節。

> [!IMPORTANT]
> **自動繼續機制 — 禁止中途停止**
> 本 workflow 是**完整的批次作業**，必須連續完成用戶指定的 `n` 章後才能停止。
> 
> **禁止行為**：
> - ❌ 完成一章後停下來等待用戶指示
> - ❌ 在章節之間要求用戶確認
> - ❌ 詢問用戶「是否繼續」
> 
> **正確行為**：
> - ✅ 完成草稿 → 逐章擴寫 → 全部完成後才停止

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `n` | ✅ | 章數 | `n=5` |
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `maint` | ❌ | 維護頻率 | `maint=light/every/end` |
| `global_note` | ❌ | 全批次主題/目標 | `global_note="能源設備與採礦機工廠"` |

### maint 參數說明
- `light`：每章輕量維護（nvExpand 內建），批次結束完整維護 **（預設）**
- `every`：每章完整維護（擴寫後額外執行 `/nvMaint mode=full`）
- `end`：僅批次結束維護（不建議，可能遺漏細節）

## 使用範例

```
/nvBatch n=5 proj=霓虹劍仙
/nvBatch n=10 proj=劍來 maint=every
/nvBatch n=3 proj=哥布林 global_note="強調飢餓感與受傷的痛苦"
```

---

## 執行步驟

### Step 1: 驗證專案與確定起始章節
// turbo
確認 `projects/{proj}/` 存在且設定完整：
- 讀取 `config/novel_config.yaml` — 記錄字數要求
- 讀取 `config/narrative_progress.yaml` — 確定起始章節號 `start`

> [!WARNING]
> **強制檢查**
> 若任一檔案不存在或格式錯誤，**立即停止**並報告：
> `❌ 專案驗證失敗：{缺失檔案}`

```
═══════════════════════════════════════════════════════
  📚 批次寫作開始
═══════════════════════════════════════════════════════
  專案：{proj}
  批次章數：{n}
  起始章節：第 {start} 章
  字數要求：{min} - {max}（目標 {target}）
  流程：nvDraft（{n}章草稿）→ 逐章 nvExpand
═══════════════════════════════════════════════════════
```

---

### Step 2: 批次生成草稿
執行 `/nvDraft`，一次生成所有 `n` 章的草稿：

```
/nvDraft proj={proj} n={n} global_note={global_note}
```

- 若有 `global_note` → nvDraft 會自動排程為每章的遞進指導
- 若無 `global_note` → nvDraft 依 SubArc 大綱自然推進
- nvDraft 的因果鏈接機制確保多章草稿間的連貫性
- 所有草稿寫入 `output/chapters/chapter_{start}~{start+n-1}.md`

> [!NOTE]
> 草稿階段可以一次生成多章，因為草稿只是骨架（事件序列），不涉及大量文字生成，LLM 不會「偷懶」。

---

### Step 3: 逐章擴寫【核心步驟 — 禁止批次擴寫】

> [!CAUTION]
> **逐章擴寫（One-Chapter-at-a-Time）**
>
> 不可一次呼叫 `/nvExpand n={n}` 來擴寫所有章節。
> 必須**逐章**呼叫，確保每章都獲得 100% 的注意力和嚴格的字數校驗。
>
> ```
> for i = start to start + n - 1:
>     執行 /nvExpand proj={proj} chapter={i}   # 每次只擴寫 1 章
>     驗證完成（字數達標 + ending_summary）
>     執行額外維護（若 maint=every）
>     → 自動進入下一章，不停頓
> end
> ```

#### Step 3a: 擴寫第 i 章

執行 `/nvExpand`，完整遵循其所有步驟：

```
/nvExpand proj={proj} chapter={i}
```

- nvExpand 會載入上下文（回顧 + 前瞻）
- nvExpand 會分析草稿內容、擬定擴寫計畫
- nvExpand 會分段生成正文
- nvExpand 會通過**硬性字數閘門**
- nvExpand 會執行一致性驗證
- nvExpand 會執行輕量維護（含 `ending_summary`）

> [!CAUTION]
> **完整執行，不可簡化**
> 即使是在批次中，每章的 nvExpand 都必須**完整執行**所有步驟。
> 不可因為「還有很多章」就跳過字數校驗或維護。

#### Step 3b: 完成驗證

```yaml
章節完成檢查:
  - 檔案已寫入: output/chapters/chapter_{i}.md
  - ending_summary 已生成: completed_chapters[] 已更新
  - 字數達標: word_count >= words_per_chapter.min
```

> [!WARNING]
> 若上述任一項未滿足，**立即停止批次**並報告：
> `❌ 第 {i} 章驗證失敗：{原因}`

#### Step 3c: 額外維護（maint=every 時）

若 `maint=every`，在本章擴寫完成後額外執行：

```
/nvMaint proj={proj} mode=full
```

#### Step 3d: 進度報告
// turbo
```
✅ 已完成 {completed}/{n} 章 | 字數：{words} | ending_summary：已記錄
```

→ **自動進入下一章**（禁止停頓，禁止詢問用戶）

---

### Step 4: 批次結束完整維護【強制執行】

> [!CAUTION]
> **必定執行**
> 無論 `maint` 設為何值，批次結束時**必定**執行完整維護。
> 此步驟**不可跳過**。

執行 `/nvMaint proj={proj} mode=full`

---

### Step 5: 完成報告
// turbo
```
═══════════════════════════════════════════════════════
  📚 批次寫作完成報告
═══════════════════════════════════════════════════════
  完成章數：{n}
  總字數：{total_words}
  當前進度：第 {current_chapter} 章 / 共 {total} 章
───────────────────────────────────────────────────────
  逐章字數：
  ├─ 第 {start} 章：{words_1} 字 ✅
  ├─ 第 {start+1} 章：{words_2} 字 ✅
  └─ ...
───────────────────────────────────────────────────────
  連貫性自檢：
  ├─ ending_summary 記錄：{n}/{n} ✅
  ├─ 章節銜接驗證：通過 ✅
  └─ 記憶庫同步：完成 ✅
═══════════════════════════════════════════════════════
```

---

## 輸出

批次完成後：
- 所有章節已寫入 `output/chapters/`
- 所有設定檔已與劇情同步
- 所有章節的 `ending_summary` 已記錄
- 記憶庫完整更新

---

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| 專案不存在 | 停止，報告錯誤 |
| 草稿生成失敗（nvDraft） | 停止，報告錯誤 |
| 擴寫字數不足（nvExpand） | nvExpand 內部處理（硬性閘門 + 重試） |
| ending_summary 未生成 | 停止，補生成後再繼續 |
| 維護失敗 | 重試一次，仍失敗則報告 |
