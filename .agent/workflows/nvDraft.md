---
description: 生成新章節的情節草稿（精簡骨架，可搭配 /nvExpand 擴寫）
---

# /nvDraft - 章節草稿

為接下來的章節 **新生成** 精簡的情節草稿。草稿只包含事件骨架——發生什麼、誰做了什麼、結果如何——不寫完整正文。

支援一次生成多章草稿，每章草稿基於前一章的結果遞進，確保因果連貫。

產出的草稿直接寫入章節檔案，之後可用 `/nvExpand` 逐章擴寫為完整正文。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `n` | ❌ | 生成章數（預設 1） | `n=5` |
| `direction` | ❌ | 劇情導引指示（單章或整體主題） | `direction="潛入敵方基地"` |
| `global_note` | ❌ | 多章批次主題，自動排程為每章指導（僅 n>1 時有效） | `global_note="建設與擴張"` |

> [!NOTE]
> `direction` 與 `global_note` 的差異：
> - `direction`：n=1 時的單章指導；n>1 時每章都套用相同方向
> - `global_note`：僅 n>1 時使用，自動拆分為每章的遞進指導（見 Step 3.5）

## 使用範例

單章：
```
/nvDraft proj=霓虹劍仙
/nvDraft proj=霓虹劍仙 direction="主角小隊潛入敵方基地失敗"
```

多章：
```
/nvDraft proj=霓虹劍仙 n=5
/nvDraft proj=霓虹劍仙 n=5 global_note="建設能源設備與採礦機工廠"
/nvDraft proj=霓虹劍仙 n=3 direction="保持壓抑氣氛"
```

搭配 `/nvExpand` 使用：
```
/nvDraft proj=X n=5              # 生成 5 章草稿
# （檢視 & 手動調整各章草稿）
/nvExpand proj=X chapter=6       # 逐章擴寫
/nvExpand proj=X chapter=7
...
```

## 執行步驟

### Step 1: 載入專案狀態
// turbo
讀取以下檔案：
- `config/novel_config.yaml` - 風格設定、pacing_pointer
- `config/narrative_progress.yaml` - 當前進度
- `config/character_db.yaml` - 角色狀態
- `memory/lore_bank.yaml` - 長期記憶

### Step 2: 載入連貫性上下文 (Sliding Window Mode)
// turbo
載入最小化的連貫性上下文：

```yaml
連貫性檢查:
  1. 確定當前 SubArc:
     - 僅提取 arcs[current_arc].subarcs 中當前 active 的部分
     - ❌ 禁止讀取未來的大綱
     
  2. 載入連貫性資料 (滑動視窗):
     - 當前 SubArc 前文: 僅讀取 completed_chapters[].ending_summary
     - 上一章: 唯一允許讀取全文的舊章節（若過大，僅讀取最後 2000 字）
     - 上一個 SubArc: 僅讀取 ending_summary
     
  3. Arc 邊界處理:
     - 若跨 Arc，僅讀取 previous_arc_ending
```

### Step 2.5: 檢查冷儲存索引
// turbo
讀取 `memory/archive_index.yaml`，若本章劇情涉及已歸檔角色/物品/事件，提取相關條目注入上下文。

### Step 3: 確定劇情範圍 (SubArc Control)
// turbo
從 `narrative_progress.yaml` 讀取：
- `current_subarc_id`
- 當前 SubArc 的 `summary`
- `engine_settings.pacing_pointer`

判斷本章應推進的劇情範圍：
- `pacing_pointer < 1.0`：只推進 SubArc 的一部分
- `pacing_pointer = 1.0`：寫完一個 SubArc
- `pacing_pointer > 1.0`：可包含多個 SubArc

### Step 3.5: Global Note 排程規劃【n>1 且有 global_note 時執行】

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

### Step 4: 生成動機地圖與關係動態
使用 `skill_motivation_engine`（若可用）：
- 分析出場角色的當前動機
- 識別潛在衝突節點
- 生成場景建議

更新關係動態（使用 `skill_relationship_dynamics`，若可用）：
- 更新角色間的信任/張力積分
- 檢查是否有關係達到轉折點閾值
- 輸出關係建議

### Step 5: 草稿生成迴圈

對於 `i = 1 到 n`，依序執行：

#### Step 5a: 確定本章指導
- 若有 `global_note` → 使用排程的 `chapter_notes[i]`
- 若有 `direction` → 使用 `direction`
- 若都無 → 依照 SubArc 大綱自然推進

#### Step 5b: 生成第 i 章草稿

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

#### Step 5c: 上下文遞進【多章模式的關鍵】

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

#### Step 5d: SubArc 邊界處理

若第 i 章推進完成了當前 SubArc：
1. 內部標記 SubArc 為已完成
2. 讀取下一個 SubArc 的 summary 作為新目標
3. 若跨 Arc，讀取新 Arc 的開篇設定

> [!NOTE]
> 此處僅在內部追蹤進度，不實際修改 `narrative_progress.yaml`。
> 所有檔案更新延後到 `/nvExpand` 執行時。

#### Step 5e: 寫入章節檔案
// turbo
將草稿寫入 `output/chapters/chapter_{N}.md`

### Step 6: 輸出確認
// turbo

單章模式：
```
═══════════════════════════════════════════════════════
  📝 第 {N} 章草稿完成
═══════════════════════════════════════════════════════
  章節標題：{title}
  草稿字數：{words}
  事件數量：{event_count}
  SubArc：{subarc_id} ({進度描述})
  
  下一步：/nvExpand proj={proj} chapter={N}
═══════════════════════════════════════════════════════
```

多章模式：
```
═══════════════════════════════════════════════════════
  📝 批次草稿完成 ({n} 章)
═══════════════════════════════════════════════════════
  第 {start} 章：{title} — {一句話摘要} ({words} 字)
  第 {start+1} 章：{title} — {一句話摘要} ({words} 字)
  ...
───────────────────────────────────────────────────────
  SubArc 進度：{subarc_id} → {ending_subarc_id}
  
  下一步：
  - 檢視各章草稿，視需要手動調整
  - 逐章執行 /nvExpand proj={proj} chapter={N}
  - 或批次執行 /nvBatch（待草稿定稿後）
═══════════════════════════════════════════════════════
```

## 輸出

草稿已寫入 `output/chapters/chapter_{N}.md`（每章各一檔）。

**不修改任何設定檔**（維護由 `/nvExpand` 負責）。

## 與 /nvChapter、/nvBatch 的關係

- `/nvChapter` = `/nvDraft`（1章）→ `/nvExpand`（1章）的容器
- `/nvBatch` = `/nvDraft`（n章）→ 逐章 `/nvExpand` 的容器
- 單獨使用 `/nvDraft` 可先生成草稿供人工檢視調整，再手動 `/nvExpand`
