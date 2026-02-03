---
description: 批次寫作多章
---

# /nvBatch - 批次寫作

> [!CAUTION]
> **強制執行聲明**
> 此 workflow 的每個步驟都是**強制性**的，不得跳過或簡化。
> 若任何步驟失敗，必須**立即停止**並報告錯誤，不得繼續執行後續章節。

> [!IMPORTANT]
> **自動繼續機制 - 禁止中途停止**
> 本 workflow 是**完整的批次作業**，必須連續完成用戶指定的 `n` 章後才能停止。
> 
> **禁止行為**：
> - ❌ 完成一章後停下來等待用戶指示
> - ❌ 在章節之間要求用戶確認
> - ❌ 詢問用戶「是否繼續」
> - ❌ 報告「第 X 章完成，請告訴我是否繼續」
> 
> **正確行為**：
> - ✅ 完成第 1 章 → 立即開始第 2 章
> - ✅ 完成第 2 章 → 立即開始第 3 章
> - ✅ ... 重複直到完成指定的 n 章
> - ✅ 完成 n 章後停止，報告批次結果

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `n` | ✅ | 章數 | `n=5` |
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `maint` | ❌ | 維護頻率 | `maint=light/every/end` |

### maint 參數說明
- `light`：每章輕量維護，批次結束完整維護 **（預設）**
- `every`：每章完整維護（最完整但較慢）
- `end`：僅批次結束維護（不建議，可能遺漏細節）

## 使用範例

```
/nvBatch n=5 proj=霓虹劍仙
/nvBatch n=10 proj=劍來 maint=every
/nvBatch n=20 proj=霓虹劍仙 maint=end
```

---

## 執行步驟

### Step 1: 驗證專案
// turbo
確認 `projects/{proj}/` 存在且設定完整：
- 讀取 `config/novel_config.yaml`
- 讀取 `config/narrative_progress.yaml`
- 讀取 `config/character_db.yaml`
- 讀取 `memory/lore_bank.yaml`

> [!WARNING]
> **強制檢查**
> 若任一檔案不存在或格式錯誤，**立即停止**並報告：
> `❌ 專案驗證失敗：{缺失檔案}`

---

### Step 2: 批次迴圈【自動執行，禁止中斷】
對於 `i = 1 到 n`，**自動依序**執行以下步驟：

```
迴圈邏輯（必須自動執行，不得中斷）：
for i = 1 to n:
    執行 Step 2a: /nvChapter
    執行 Step 2b: 維護
    執行 Step 2c: 報告進度
    執行 Step 2d: 確認連貫性
    # → 自動進入下一迴，不得停止
end for
# → 全部完成後，才進入 Step 3
```

#### Step 2a: 執行 /nvChapter【強制完整執行】

> [!CAUTION]
> **不可簡化**
> 每章都必須**完整執行** nvChapter 的所有步驟，包括：
> - Step 1.5 連貫性上下文載入（**強制**）
> - Step 7 前的 ASSERT 檢查點（**強制**）
> - Step 11 的 ending_summary 生成（**強制**）
>
> **禁止行為**：
> - ❌ 跳過連貫性檢查直接寫作
> - ❌ 省略 ending_summary 生成
> - ❌ 合併多章內容一次產出

執行 `/nvChapter proj={proj}`

**執行後驗證**：
```yaml
章節完成檢查:
  - 檔案已寫入: output/chapters/chapter_{i}.md
  - ending_summary 已生成: completed_chapters[] 已更新
  - 字數達標: word_count >= words_per_chapter.min
```

> [!WARNING]
> 若上述任一項未滿足，**立即停止批次**並報告：
> `❌ 第 {i} 章驗證失敗：{原因}`

#### Step 2b: 章節維護【強制執行】

無論 `maint` 參數為何，以下項目**必須更新**：

```yaml
【每章必更新 - 不可跳過】:
  narrative_progress.yaml:
    - completed_chapters[]: 新增本章記錄
    - ending_summary: 本章結尾摘要（強制）
    - ending_state: 結尾狀態（強制）
    - progress.current_chapter: +1
    
  lore_bank.yaml:
    - events[]: 本章事件
```

**額外維護**（根據 maint 參數）：

| maint | 額外操作 |
|-------|----------|
| `light` | 更新 character_db.current_state，標記 pending 項目 |
| `every` | 執行完整 `/nvMaint mode=full` |
| `end` | 延後到批次結束 |

#### Step 2c: 進度報告
// turbo
顯示完成進度：
```
✅ 已完成 {i}/{n} 章 | 字數：{words} | ending_summary：已記錄
```

#### Step 2d: 下一章連貫性確認【強制】

> [!IMPORTANT]
> 在開始下一章之前，**必須確認**：
> - 上一章的 `ending_summary` 已寫入 `narrative_progress.yaml`
> - 上一章的 `ending_state` 已記錄位置和角色狀態
>
> 這是確保批次章節間連貫性的關鍵步驟。

---

### Step 3: 批次結束完整維護【強制執行】

> [!CAUTION]
> **必定執行**
> 無論 `maint` 設為何值，批次結束時**必定**執行完整維護。
> 此步驟**不可跳過**。

執行 `/nvMaint proj={proj} mode=full`

包含：
1. **長期記憶** - `lore_bank.yaml`
2. **敘事進度** - `narrative_progress.yaml`
3. **角色資料庫** - `character_db.yaml`（含新角色）
4. **世界地圖** - `world_atlas.yaml`（含新地點）
5. **勢力登記** - `faction_registry.yaml`（含新勢力）
6. **力量體系** - `power_system.yaml`（含新能力）
7. **物品目錄** - `item_compendium.yaml`（含新物品）

---

### Step 4: 完成報告與自檢
// turbo
顯示批次完成摘要：

```
═══════════════════════════════════════════════════════
  批次寫作完成報告
═══════════════════════════════════════════════════════
  完成章數：{n}
  總字數：{words}
  當前進度：第 {chapter} 章 / 共 {total} 章
───────────────────────────────────────────────────────
  連貫性自檢：
  ├─ ending_summary 記錄：{n}/{n} ✅
  ├─ 章節銜接驗證：通過 ✅
  └─ 記憶庫同步：完成 ✅
───────────────────────────────────────────────────────
  設定更新：
  ├─ 新增角色：{x} 人
  ├─ 新增地點：{y} 處
  ├─ 新增勢力：{z} 個
  ├─ 新增物品：{w} 件
  └─ 開放伏筆：{f} 條
═══════════════════════════════════════════════════════
```

---

## 輸出

批次完成後：
- 所有章節已寫入 `output/chapters/`
- 所有設定檔已與劇情同步
- 記憶庫完整更新
- 所有章節的 `ending_summary` 已記錄

---

## 錯誤處理

| 錯誤類型 | 處理方式 |
|----------|----------|
| 專案不存在 | 停止，報告錯誤 |
| 連貫性上下文載入失敗 | 停止當前章節，報告錯誤 |
| 字數不足 | 重新擴充該章，不繼續 |
| ending_summary 未生成 | 停止，補生成後再繼續 |
| 維護失敗 | 重試一次，仍失敗則報告 |

