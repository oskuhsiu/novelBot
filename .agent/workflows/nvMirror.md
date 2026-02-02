---
description: 架構逆向與重鑄，借用外部劇情骨架
---

# /nvMirror - 架構逆向與重鑄器

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 目標專案名稱 | `proj=霓虹劍仙` |
| `source` | ✅ | 來源類型 | `source=text/file/url` |
| `content` | ⚠️ | 來源內容（source=text時必填） | `content="大綱文字..."` |
| `path` | ⚠️ | 來源路徑（source=file時必填） | `path=/path/to/outline.md` |
| `url` | ⚠️ | 來源網址（source=url時必填） | `url=https://...` |
| `divergence` | ❌ | 差異化程度 0-1 | `divergence=0.5` |
| `chapters` | ❌ | 生成幾章大綱 | `chapters=5` |

### divergence 參數說明
- `0`：完全照搬轉折（僅替換名詞）
- `0.5`：借用大框架，解決方法自定（預設）
- `1.0`：僅借用起始動機，隨後自主演化

## 使用範例

```bash
# 直接文字輸入
/nvMirror proj=霓虹劍仙 source=text content="第一章：主角被陷害入獄。第二章：獄中遇到高人指點..."

# 指定檔案
/nvMirror proj=霓虹劍仙 source=file path=/Users/me/reference/outline.md

# 指定網址
/nvMirror proj=霓虹劍仙 source=url url=https://example.com/novel-outline

# 調整差異化程度
/nvMirror proj=霓虹劍仙 source=text content="..." divergence=0.8 chapters=10
```

## 執行步驟

### Step 1: 載入來源素材
// turbo
根據 `source` 類型載入素材：
- `text`：直接使用 `content` 參數
- `file`：讀取指定路徑的檔案內容
- `url`：使用 `read_url_content` 抓取網頁內容

### Step 2: 結構解構 (Deconstruct)
使用 `skill_schema_re_architect` 分析來源素材，提取抽象結構：

```yaml
解構目標:
  - 衝突核心：主要矛盾是什麼
  - 角色功能：各角色的敘事作用（導師/對手/盟友/背叛者）
  - 轉折節點：關鍵事件的位置和類型
  - 情感曲線：張力的高低變化
  - 節奏模式：快慢交替的規律
```

輸出格式：
```yaml
source_structure:
  conflict_core: "權力鬥爭/生存危機/復仇/成長"
  character_functions:
    - role: "Protagonist"
      function: "底層崛起"
    - role: "Mentor"
      function: "傳授關鍵知識後犧牲"
    - role: "Antagonist"
      function: "代表舊秩序的壓迫"
  turning_points:
    - position: 0.15
      type: "催化劑"
      description: "主角被迫離開舒適區"
    - position: 0.5
      type: "中點轉折"
      description: "獲得力量但付出代價"
    - position: 0.85
      type: "黑暗時刻"
      description: "看似失敗"
  emotional_curve: "低谷-上升-高峰-低谷-最終勝利"
```

### Step 3: 載入目標專案
// turbo
讀取目標專案的設定檔：
- `config/novel_config.yaml` - 風格與世界觀
- `config/character_db.yaml` - 角色庫
- `config/faction_registry.yaml` - 勢力登記
- `config/world_atlas.yaml` - 世界地圖
- `config/power_system.yaml` - 力量體系

### Step 4: 語義映射 (Map)
將抽象結構映射到目標專案：

```yaml
映射規則:
  角色對應:
    source.Protagonist → target.CHAR_001 (或最接近的角色)
    source.Mentor → target.CHAR_XXX
    source.Antagonist → target.FAC_XXX.leader
    
  場景對應:
    source.監獄 → target.LOC_XXX (最接近的封閉空間)
    source.競技場 → target.LOC_XXX
    
  力量對應:
    source.武功 → target.power_system.abilities
    source.法器 → target.item_compendium
```

### Step 5: 差異化處理 (Divergence)
根據 `divergence` 參數調整映射：

```yaml
divergence_rules:
  0.0: "完全複製轉折邏輯，僅替換名詞"
  0.3: "保留大框架，細節允許變化"
  0.5: "保留衝突核心和主要節點，解決方法自由發揮"
  0.7: "僅參考情感曲線和節奏，具體事件自訂"
  1.0: "僅借用起始動機，隨後完全自主演化"
```

### Step 6: 重構大綱 (Reconstruct)
生成新的章節大綱：

```yaml
output_format:
  chapter_X:
    title: "章節標題（符合目標專案風格）"
    source_reference: "對應來源的第N章"
    beats:
      - id: "BX_1"
        summary: "場景描述（使用目標專案的角色/地點/力量）"
        weight_hint: "內容權重覆蓋（可選）"
    divergence_notes: "這裡與來源不同的地方"
```

### Step 7: 一致性驗證
使用 `skill_consistency_validator` 檢查：
- 生成的大綱是否與目標專案設定相容
- 角色行為是否符合 `base_profile`
- 場景是否符合 `world_atlas` 的地理邏輯

### Step 8: 寫入大綱
// turbo
將生成的大綱寫入：
- `config/narrative_progress.yaml` - 追加新章節
- 或輸出到獨立檔案 `output/mirror_outline.yaml`

### Step 9: 輸出報告
顯示映射結果摘要：

```
═══════════════════════════════════════════════════
  架構映射完成
═══════════════════════════════════════════════════
  來源類型：{source}
  差異化程度：{divergence}
  生成章節：{chapters} 章
───────────────────────────────────────────────────
  角色映射：
  ├─ 來源主角 → {target_protagonist}
  ├─ 來源導師 → {target_mentor}
  └─ 來源反派 → {target_antagonist}
───────────────────────────────────────────────────
  轉折點：
  ├─ 催化劑 → 第 {X} 章
  ├─ 中點轉折 → 第 {Y} 章
  └─ 黑暗時刻 → 第 {Z} 章
═══════════════════════════════════════════════════
```

## 輸出

生成的大綱存放於 `output/mirror_outline.yaml` 或直接整合至 `narrative_progress.yaml`。
