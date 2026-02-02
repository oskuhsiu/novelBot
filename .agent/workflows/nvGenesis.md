---
description: 建立新小說專案，初始化世界觀、角色與大綱
---

# /nvGenesis - 建立新專案

建立新的小說專案資料夾，初始化所有設定檔。支援從簡述自動分析類型與大綱。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `name` | ✅ | 專案名稱 | `name=霓虹劍仙` |
| `alias` | ✅ | 專案代號（簡短英數字） | `alias=neon` |
| `type` | ⚠️ | 小說類型（若有 source 可省略） | `type=賽博龐克修仙` |
| `source` | ❌ | 簡述來源類型 | `source=text/file` |
| `content` | ⚠️ | 簡述內容（source=text時必填） | `content="主角穿越..."` |
| `path` | ⚠️ | 簡述檔案路徑（source=file時必填） | `path=/path/to/outline.md` |
| `lang` | ❌ | 語言 (預設 zh-TW) | `lang=zh-TW` |
| `preset` | ❌ | 使用預設模板 | `preset=xianxia` |
| `pacing` | ❌ | 速度指針 (預設 0.5) | `pacing=0.3` |
| `words` | ❌ | 目標字數 (預設 100000) | `words=200000` |
| `arcs` | ❌ | 大綱數量 (預設 10) | `arcs=8` |
| `subarcs` | ❌ | 每卷細目數 (預設 5~10) | `subarcs=3~5` |

## 使用模式

### 模式 A：手動指定類型
```
/nvGenesis name=霓虹劍仙 alias=neon type=賽博龐克修仙
/nvGenesis name=短篇 alias=short type=懸疑 arcs=5 subarcs=3~5
```

### 模式 B：從簡述文字生成
```
/nvGenesis name=霓虹劍仙 alias=neon source=text content="一個現代程式設計師穿越到賽博龐克世界，發現修仙者用腦機接口練功。他利用現代知識，從底層小修士一步步崛起..."
```

### 模式 C：從檔案生成
```
/nvGenesis name=霓虹劍仙 alias=neon source=file path=/Users/me/ideas/霓虹劍仙構想.md
```

### 混合模式
簡述只作為參考，仍可手動覆蓋：
```
/nvGenesis name=霓虹劍仙 alias=neon source=file path=./idea.md type=修仙 arcs=12
```

## 執行步驟

### Step 0: 解析簡述（若有 source）
如果指定了 `source`，先分析簡述內容：

#### 0.1 載入簡述
```
source=text → 使用 content 參數
source=file → 讀取 path 指定的 .md 或 .txt 檔案
```

#### 0.2 分析簡述
使用 `skill_synopsis_analyzer` 分析簡述，推算：
- **type**：小說類型（如「賽博龐克/修仙/輕鬆」）
- **tone**：語氣風格（如「幽默吐槽」）
- **arcs**：建議大綱數量
- **beats**：每卷細目摘要（直接生成細目！）
- **characters**：識別出的角色概念
- **world_hints**：世界觀提示

輸出範例：
```yaml
synopsis_analysis:
  type: "賽博龐克/修仙/輕鬆"
  tone: "幽默、吐槽、逆襲爽文"
  suggested_arcs: 8
  arc_summaries:
    - title: "第一卷：底層求生"
      summary: "主角穿越後發現自己是最低級的修士..."
      beats:
        - "穿越覺醒，發現世界規則"
        - "獲得作弊系統"
        - "第一次利用現代知識破局"
    - title: "第二卷：初露鋒芒"
      ...
  character_hints:
    - role: protagonist
      concept: "穿越程式設計師，擅長邏輯分析"
    - role: mentor
      concept: "神秘AI導師"
```

### Step 1: 建立專案目錄
// turbo
建立 `projects/{name}/` 目錄結構：
```
projects/{name}/
├── config/
│   ├── novel_config.yaml
│   ├── character_db.yaml
│   ├── world_atlas.yaml
│   ├── faction_registry.yaml
│   ├── power_system.yaml
│   ├── item_compendium.yaml
│   └── narrative_progress.yaml
├── output/
│   ├── chapters/
│   └── style_guide.md
└── memory/
    ├── lore_bank.yaml
    └── emotion_log.yaml
```

### Step 2: 初始化設定檔
// turbo
複製 `templates/` 下的範本到專案目錄，填入基本參數：
- `meta.project_name` = `{name}`
- `meta.alias` = `{alias}`
- `meta.language` = `{lang}`
- `style_profile.genre` = `{type}` 或 `{synopsis_analysis.type}`
- `style_profile.tone` = `{synopsis_analysis.tone}`（若有）
- `engine_settings.pacing_pointer` = `{pacing}`
- `structure.arcs` = `{arcs}` 或 `{synopsis_analysis.suggested_arcs}`
- `structure.subarcs_per_arc` = `{subarcs}` (預設 5~10)

若指定 `preset`，載入預設值覆蓋。

### Step 3: 生成風格指南
使用 `skill_style_setter` 生成 `output/style_guide.md`
- 若有簡述，參考 `synopsis_analysis.tone` 來設定風格

### Step 4: 建構世界觀
使用 `skill_world_builder` 生成初始世界觀，寫入 `world_atlas.yaml`
- 若有簡述，參考 `synopsis_analysis.world_hints`

### Step 5: 設計力量體系
使用 `skill_power_architect` 設計力量系統，寫入 `power_system.yaml`

### Step 6: 創建主要角色
使用 `skill_character_forge` 創建角色：
- 若有簡述，參考 `synopsis_analysis.character_hints`
- 否則預設創建：1 主角 + 1 反派 + 2-3 配角

### Step 7: 建立勢力
使用 `skill_faction_forge` 創建 2-4 個勢力

### Step 8: 規劃大綱
使用 `skill_outline_architect` 規劃全書結構：
- **若有簡述**：直接使用 `synopsis_analysis.arc_summaries` 和 subarcs
- **否則**：根據 `{arcs}` 和 `{subarcs}` 生成

### Step 9: 生成初始道具
使用 `skill_item_smith` 為主角生成初始裝備，寫入 `item_compendium.yaml`

### Step 10: 埋設角色秘密
使用 `skill_character_secret_seeder` 為主要角色生成隱藏動機

### Step 11: 輸出確認
顯示專案建立結果摘要：
```
═══════════════════════════════════════════════════
  專案建立完成
═══════════════════════════════════════════════════
  專案名稱：{name}
  代號：{alias}
  類型：{type}
  來源：{source 或 "手動指定"}
───────────────────────────────────────────────────
  大綱：{arcs} 卷
  細目：約 {total_subarcs} 個
  預估章數：{estimated_chapters}
───────────────────────────────────────────────────
  可使用 /nvChapter proj={alias} 開始寫作
═══════════════════════════════════════════════════
```

## 可用 Presets

| preset | 說明 |
|--------|------|
| `xianxia` | 仙俠/修仙 (combat:0.4, internal:0.2) |
| `scifi` | 科幻 (world_building:0.2, action:0.15) |
| `romance` | 言情 (dialogue:0.4, internal:0.25) |
| `mystery` | 懸疑 (dialogue:0.35, scenery:0.2) |
| `fantasy` | 西幻 (combat:0.35, scenery:0.2) |

## 與 nvMirror 的差異

| 功能 | nvGenesis | nvMirror |
|------|-----------|----------|
| 用途 | **創建**新專案 | 為**已有專案**套用外部架構 |
| 角色 | 從簡述分析或新生成 | 使用專案現有角色 |
| 世界觀 | 從簡述分析或新生成 | 使用專案現有世界觀 |
| 大綱 | 從簡述分析或新生成 | 映射外部架構到現有設定 |
| divergence | 不適用 | 控制偏離程度 |

**何時用 nvGenesis**：我有一個想法，想開新專案
**何時用 nvMirror**：專案已有角色/世界觀，想套用某個故事骨架

## 專案代號說明

`alias` 是一個簡短的英數字代號，方便在後續操作中快速引用專案。所有 `proj=` 參數都支援使用專案名稱或代號。

代號會同時記錄在：
1. `config/novel_config.yaml` 的 `meta.alias`
2. 全域專案註冊檔 `projects/project_registry.yaml`

## 大綱結構說明

本系統採用 **Arc-SubArc-Chapter** 三層架構：

```
Arc (大綱/卷)
├── SubArc 1 (細目/情節點)
│     ├── Chapter 1 (根據 pacing 動態產生，內有多個 beats)
│     └── Chapter 2
├── SubArc 2
│     └── Chapter 3
└── ...
```

> **術語區分**：SubArc 是 Arc 下的細目；Beat 是 Chapter 內的場景節拍，兩者層級不同。

### 章節數計算公式

```
總細目數 = arcs × subarcs_per_arc
總章節數 ≈ 總細目數 / pacing_pointer
```

| 設定 | arcs | subarcs | pacing | 預估章數 |
|------|------|---------|--------|----------|
| 預設 | 10 | 5~10 | 0.5 | 100~200 |
| 快速 | 10 | 5~10 | 1.0 | 50~100 |
| 細臻 | 10 | 5~10 | 0.2 | 250~500 |
| 短篇 | 5 | 3~5 | 0.5 | 30~50 |

### 局部 pacing 覆蓋

每個 Arc 和 SubArc 都可以有自己的 `pacing_pointer`，用以手動調整進程：

```yaml
arcs:
  - arc_id: 1
    title: "第一卷：开篇"
    pacing_pointer: 0.3  # 覆蓋全域，這卷寫得慢
    subarcs:
      - id: "A1_S1"
        summary: "主角訪視"
        pacing_pointer: 0.2  # 這個細目更慢
```

