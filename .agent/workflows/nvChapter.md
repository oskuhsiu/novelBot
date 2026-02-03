---
description: 寫一章
---

# /nvChapter - 寫一章

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `direction` | ❌ | 劇情導引指示，引導本章劇情走向 | `direction="敵方來了強力增援，主角陷入危機"` |

## 使用範例

```
/nvChapter proj=霓虹劍仙
```

帶劇情導引：
```
/nvChapter proj=霓虹劍仙 direction="敵方來了強力增援，主角小隊陷入危機。隊友使用犧牲性技能，讓主角逃脫"
```

## 執行步驟

### Step 1: 載入專案狀態
// turbo
讀取以下檔案：
- `config/novel_config.yaml` - 風格設定、**字數要求** (`words_per_chapter.min`/`target`/`max`)
- `config/narrative_progress.yaml` - 當前進度
- `config/character_db.yaml` - 角色狀態
- `memory/lore_bank.yaml` - 長期記憶

### Step 1.5: 載入連貫性上下文
// turbo
根據 `narrative_progress.yaml` 中的 arc/subarc 結構，載入連貫性上下文：

```yaml
連貫性檢查:
  1. 確定當前 SubArc（次網）:
     - 從 arcs[current_arc].subarcs 找到當前 subarc
     - 讀取 subarc.chapters[] 已完成的章節列表
     
  2. 載入同一 SubArc 的已有章節（如有）:
     - 優先讀取 completed_chapters[].ending_summary（快速）
     - 若無 ending_summary，才讀取 output/chapters/ 完整檔案
     - 彙整為 subarc_context
     
  3. 載入上一個 SubArc 的最後一章（如有）:
     - 找到前一個 subarc（可能跨 arc）
     - 優先讀取 subarc.ending_summary（快速）
     - 若無，讀取其最後一章的內容
     - 提取結尾摘要為 previous_subarc_ending
     
  4. 【Arc 邊界處理】檢查是否跨越 Arc 邊界:
     - 若 current_subarc 是新 Arc 的第一個 SubArc:
       arc_boundary:
         is_new_arc: true
         previous_arc_id: {{previous_arc_id}}
         previous_arc_ending: "{{arcs[previous_arc].ending_summary}}"
         transition_note: "需要自然過渡到新卷主題"
     - 若非新 Arc，則 is_new_arc: false
     
  5. 整合連貫性上下文:
     continuity_context:
       current_subarc_summary: "{{subarc.summary}}"
       previous_chapters_in_subarc: [...]
       previous_subarc_ending: "..."
       arc_boundary: {{arc_boundary}}  # 跨 Arc 資訊
       direction: "{{direction}}"  # 若有傳入 direction 參數
```

> [!IMPORTANT]
> **連貫性優先**
> 同一 SubArc 內的多個章節必須形成連貫敘事。
> 新章節必須：
> - 銜接同 SubArc 前章的結尾
> - 呼應上一 SubArc 的伏筆
> - 依據 direction（若有）引導劇情走向
>
> **Arc 邊界特殊處理**
> 若 `arc_boundary.is_new_arc == true`：
> - 章節開頭需要自然過渡（時間跳躍、場景轉換、或直接銜接）
> - 參考 `previous_arc_ending` 確保不跳脫前文
> - 可適度回顧前卷結尾，但不宜過長

### Step 2: 確定當前章節
// turbo
從 `narrative_progress.yaml` 讀取：
- `meta.current_chapter` → 本章章號
- `outline[chapter]` → 本章大綱

### Step 3: 計算節奏
使用 `skill_pacing_calculator`：
- 讀取 `pacing_pointer`
- 計算本章應推進多少劇情
- 輸出寫作節奏指導

### Step 4: 拆解節拍
使用 `skill_chapter_beater`：
- 將章節大綱拆解為 5-8 個場景節拍
- 分配各節拍的字數權重
- **傳入連貫性上下文**：`continuity_context`（來自 Step 1.5）
- **傳入劇情導引**：`direction`（若有）

### Step 5: 優化張力曲線
使用 `skill_beat_optimizer`：
- 調整節拍順序
- 標記高潮點和緩衝點

### Step 6: 分配內容比例與字數
使用 `skill_weight_balancer`：
- 依據 `content_weights` 分配各類內容比例
- 輸出各節拍的具體字數分配

> [!IMPORTANT]
> **字數要求強制**
> - 每章總字數必須達到 `words_per_chapter.min`（預設 3000 字）
> - 目標字數為 `words_per_chapter.target`（預設 4000 字）
> - 各節拍字數應平均分配，避免出現千字小章

> [!CAUTION]
> **強制檢查點（ASSERT）**
> 執行 Step 7 前，必須確認以下條件已滿足：
> - ✅ `continuity_context` 已載入且非空
> - ✅ `continuity_context.previous_subarc_ending` 已設定（首章除外）
> - ✅ 若 `arc_boundary.is_new_arc == true`，則 `previous_arc_ending` 已設定
> 
> 若任一條件未滿足，**立即停止並報錯**，不得繼續撰寫。

### Step 7: 撰寫正文
依序處理每個節拍，使用：
- `skill_scene_writer` - 撰寫基礎正文
  - **傳入連貫性上下文**：`continuity_context`
  - **傳入劇情導引**：`direction`（若有）
- `skill_dialogue_director` - 優化對話（對話密集場景）
- `skill_dialogue_subtext_editor` - 加入潛台詞（重要對話）
- `skill_identity_validator` - 驗證角色派系對話風格
- `skill_sensory_amplifier` - 增強感官描寫（需要時）
- `skill_technique_elaborator` - 展開技能描寫（戰鬥場景）
- `skill_item_interactor` - 展開道具使用（道具場景）
- `skill_atlas_navigator` - 驗證移動路徑（場景轉換時）

### Step 8: 驗證一致性
使用 `skill_logic_auditor`、`skill_consistency_validator` 和 `skill_world_rule_validator`：
- 檢查與已有設定的衝突
- 驗證角色行為一致性
- 驗證世界規則遵守

### Step 9: 生成結尾鉤子
使用 `skill_cliffhanger_generator`：
- 為章節結尾設計懸念
- 可能觸發 `skill_chaos_engine`（低機率）

### Step 10: 輸出章節
// turbo
寫入 `output/chapters/chapter_{N}.md`

> [!WARNING]
> **字數檢查**
> 若總字數 < `words_per_chapter.min`，必須擴充節拍內容後再輸出。
> 不得輸出不足最低字數的章節。

### Step 11: 輕量維護（自動執行）
章節完成後自動進行輕量維護：

```yaml
必更新:
  lore_bank.yaml:
    - 新增本章事件
    - 記錄伏筆變動
    
  narrative_progress.yaml:
    - 標記章節完成
    - 更新字數統計
    - 【強制】更新 completed_chapters[] 新增本章：
        chapter_id: {{chapter_id}}
        subarc_id: {{current_subarc_id}}
        arc_id: {{current_arc_id}}
        title: {{chapter_title}}
        word_count: {{word_count}}
        completed_at: {{timestamp}}
        ending_summary: {{自動生成：本章最後 500 字的關鍵摘要}}
        ending_state:
          location: {{主要角色結尾位置}}
          key_characters: {{結尾在場角色}}
          unresolved: {{未解決的懸念}}
    - 【強制】若本章是當前 SubArc 的最後一章：
        更新 arcs[arc].subarcs[subarc].ending_summary
    - 【強制】若本章是當前 Arc 的最後一章：
        更新 arcs[arc].ending_summary
    
  character_db.yaml:
    - 更新角色 current_state
    - 標記位置/健康/物品變動

待標記（完整維護時處理）:
  - 新角色（如有）→ pending_new_characters
  - 新地點（如有）→ pending_new_locations
  - 新勢力（如有）→ pending_new_factions
  - 新物品（如有）→ pending_new_items
```

> [!WARNING]
> **ending_summary 為強制欄位**
> 本章完成時，必須生成 `ending_summary`，否則視為章節未完成。
> 此摘要將被後續章節的 Step 1.5 讀取，是連貫性的關鍵。

### Step 12: 輸出確認
// turbo
顯示章節完成資訊：
- 章節標題
- 實際字數 / 目標字數（例：4200/4000 ✅ 或 2500/4000 ⚠️）
- 維護狀態

## 輸出

章節已寫入 `output/chapters/`，輕量維護已完成。

如需完整更新所有設定，請執行 `/nvMaint proj={proj} mode=full`
