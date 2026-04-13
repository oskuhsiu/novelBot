---
name: brief_expander
description: 摘要擴寫器 - 將情節骨架擴展為符合目標字數的完整正文
---

# 摘要擴寫器 (Brief Expander)

## 功能概述

將一份精簡的情節骨架（Brief）擴展為完整的小說正文，同時嚴格遵守專案的字數要求、風格設定和內容權重。

> [!IMPORTANT]
> **與 scene_writer 的區別**
> - `scene_writer`：從節拍（Beat）指令生成正文，一次處理一個節拍
> - `brief_expander`：從完整章節的情節摘要出發，自動拆解 → 分配 → 擴寫 → 組合，一次性產出整章

## 輸入

1. **章節檔案**（`output/chapters/chapter_{N}.md`）：
   - 可能是 `/nvDraft` 產出的精簡骨架
   - 也可能是字數不足的正文
   - Skill 會自動判斷內容類型並選擇對應模式

2. **專案設定**（從 `config/novel_config.yaml`）：
   - `words_per_chapter.min` / `target` / `max`
   - `content_weights`（各類內容佔比）
   - `style_profile`（風格、語氣、視角）
   - `engine_settings.pacing_pointer`

3. **連貫性上下文**（從 ChromaDB `chapters` collection 和 `config/outline/arc_{current_arc}.yaml`）：
   - 上一章 `ending_summary`：使用 `ChapterVector.get_chapter(chapter_id)` 讀取
   - 當前 SubArc 摘要（由 `outline_index.yaml` 取得 current_arc 後讀 `outline/arc_{current_arc}.yaml`）
   - 角色當前狀態

4. **風格指南**（從 `output/style_guide.md`，若存在）

5. **前瞻上下文**（從 `output/chapters/chapter_{N+1}.md`，若有）：
   - 下一章的開場事件或狀態
   - 用於確保本章結尾能順利銜接
   - 包含：`next_opening_events` (事件), `next_opening_state` (狀態)

## 輸出

完整的章節正文，字數落在 `words_per_chapter.min` ~ `words_per_chapter.max` 範圍內。

## 執行步驟

### Step 1: 解析 Brief 事件

```yaml
解析流程:
  1. 將 Brief 中的每個事件轉化為一個「場景種子」
  2. 每個場景種子包含:
     - event: "原始事件描述"
     - characters: ["涉及角色"]
     - location: "推斷地點"
     - type: "action/dialogue/transition/reveal"
     - voice_override: "從事件的 voice: 行解析，若無則 null"
```

### Step 2: 計算字數分配

```yaml
字數分配:
  target_words: {{words_per_chapter.target}}
  scene_count: {{len(scene_seeds)}}
  
  分配策略:
    1. 基礎分配: target_words / scene_count = base_per_scene
    2. 權重調整:
       - 衝突/高潮場景: base × 1.5
       - 過渡/連接場景: base × 0.6
       - 對話場景: base × 1.0
       - 揭露場景: base × 1.2
    3. 分配結果總和必須 ≈ target_words（±10%）
```

### Step 3: 擴寫場景

對每個場景種子，依序擴寫：

```yaml
擴寫規則:
  聲音確認: 每個場景擴寫前，確定該場景的聲音——若 voice_override 存在則合併覆蓋至章節預設，否則使用章節預設。場景的語調、能量和對話質感必須匹配。
  每個事件骨架句 → 完整場景段落:
  
  1. 環境鋪墊 (約 15% 字數):
     - 場景地點的感官細節
     - 氣氛營造
     - 與劇情相關的環境描寫
     
  2. 角色進場與互動 (約 40% 字數):
     - 角色**首次出場**用 presence 和 appearance（物理形象），不用性格標籤。同章後續場景可跳過入場
     - 對話展開（將 brief 中的「結論」拆為過程）
     - 角色反應用具體動作（優先取自 presence 習慣動作），不用「內心感到 X」
     - 性格通過行動和對話自然流露，不由旁白宣告
     
  3. 事件推進 (約 30% 字數):
     - 事件的具體經過
     - 因果邏輯的展開
     - 決策的掙扎過程
     
  4. 餘韻與銜接 (約 15% 字數):
     - 事件的即時後果
     - 情感沉澱
     - **引向下一場景的過渡**
     - **若為本章最後場景**：必須參照前瞻上下文 (Forward Context)
       - 確保角色位置移動到下一章開場地點
       - 確保角色狀態符合下一章開場設定
       - 鋪墊下一章的觸發事件
```

> [!IMPORTANT]
> **擴寫 ≠ 灌水**
> - ✅ 將「主角突破防線」展開為具體的行動過程
> - ✅ 將「雙方達成協議」展開為談判的拉鋸
> - ❌ 堆砌與劇情無關的環境描寫
> - ❌ 重複描述同一件事
> - ❌ 加入 brief 中不存在的新劇情線

### Step 4: 風格潤色

```yaml
潤色檢查:
  1. 語氣一致性: 對照 style_profile.tone
  2. 視角一致性: 對照 style_profile.perspective
  3. 內容權重: 對照 content_weights 微調各段落比例
  4. 角色聲音: 對照 character_db（使用 get-public）確認對白風格
  5. 角色活度: 角色入場是否用了性格標籤而非物理形象？traits 是否被旁白直接宣告？
```

### Step 5: 字數校驗與調整

取得 `total_words`（**禁止**自行寫 regex 或用 `wc`）：
```
.venv/bin/python tools/word_count.py <chapter_file>
```

```yaml
字數校驗:
  若 total_words < words_per_chapter.min:
    → 擴充策略:
      1. 找到字數最少的場景
      2. 增加感官描寫層次
      3. 深化角色內心轉折
      4. 擴展對話的來回次數
      
  若 total_words > words_per_chapter.max:
    → 壓縮策略:
      1. 精簡過渡段落
      2. 削減重複性描寫
      3. 合併相似場景
```

> [!CAUTION]
> **絕對邊界**
> - 最終字數 **必須** ≥ `words_per_chapter.min`
> - 最終字數 **不應** 超過 `words_per_chapter.max`
> - 若無法達標，報告原因而非強行灌水

### Step 6: 組合輸出

將所有場景按時間序列組合為完整章節。場景之間不加分隔符號，確保行文自然流暢。

## 反向展開指南

Brief 中的壓縮寫法如何展開：

| Brief 寫法 | 擴寫方向 |
|------------|----------|
| 「A 決定做 X」 | 展開決策過程：考量、猶豫、下定決心 |
| 「A 與 B 交涉，結果是 Y」 | 展開對話：開場、拉鋸、讓步、達成 |
| 「A 擊敗了 B」 | 展開戰鬥：試探、僵持、轉折、分勝負 |
| 「A 得知了秘密 Z」 | 展開揭露過程：線索、推理或被告知、震驚反應 |
| 「A 從地點 X 移動到 Y」 | 展開旅程：途中所見、內心思考、抵達時的感受 |
| 「勢力關係改變」 | 展開轉折：導火線事件、雙方反應、新格局確立 |

## 與其他 Skill 的關聯

- **前置 Skill**：
  - nvBrief：提供標準化的 brief 輸入
  - `structure/weight_balancer`：提供內容比例分配
- **協作 Skill**：
  - `execution/scene_writer`：可選擇性地呼叫以處理個別場景
  - `execution/dialogue_director`：優化對話密集場景
  - `execution/sensory_amplifier`：強化環境描寫
- **後續 Skill**：
  - `memory/logic_auditor`：檢查邏輯一致性
  - `memory/consistency_validator`：驗證與前後文的連貫

## 注意事項

1. **忠於 Brief**：擴寫的情節走向必須與 Brief 一致，不可擅自新增或刪減事件
2. **字數分配合理**：高潮場景多分字數，過渡場景少分字數
3. **風格服務劇情**：描寫方式應配合事件的緊張程度
4. **保持節奏**：避免所有場景都以同樣的速度展開
5. **銜接自然**：場景之間的過渡要流暢，不生硬
