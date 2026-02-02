# Genesis Engine - AI 小說創作系統

一套模組化的 AI 小說創作系統，透過 Skills 和 Workflows 自動化長篇小說創作。

## 快速開始

```bash
# 1. 建立新專案
/nvGenesis name=霓虹劍仙 type=賽博龐克修仙 preset=cyberpunk

# 2. 批次寫作 5 章
/nvBatch n=5 proj=霓虹劍仙

# 3. 查看狀態
/nvStatus proj=霓虹劍仙

# 4. 匯出
/nvExport proj=霓虹劍仙 fmt=md
```

## 指令總覽

### 核心流程

| 指令 | 功能 | 參數 |
|------|------|------|
| `/nvGenesis` | 建立新專案 | `name= type= preset= lang= pacing= words=` |
| `/nvChapter` | 寫一章 | `proj=` |
| `/nvMaint` | 維護記憶 | `proj= mode=full/light` |
| `/nvBatch` | 批次寫作 | `n= proj= maint=light/every/end` |

### 輔助工具

| 指令 | 功能 | 參數 |
|------|------|------|
| `/nvPreview` | 預覽規劃 | `n= proj=` |
| `/nvExport` | 匯出章節 | `fmt=md/txt range= proj=` |
| `/nvStatus` | 狀態總覽 | `proj=` |
| `/nvReview` | 一致性檢查 | `range= proj=` |
| `/nvChatTest` | 角色對話測試 | `"角色名" ID proj=` |

### 進階功能

| 指令 | 功能 | 參數 |
|------|------|------|
| `/nvRegen` | 重新生成章節 | `ch= pacing= weights= style= focus= seed=` |
| `/nvImport` | 導入既有內容 | `file= proj= type=` |
| `/nvBranch` | 分支劇情 | `ch= name= proj=` |
| `/nvPreset` | 查看預設模板 | - |
| `/nvMirror` | 架構逆向與重鑄 | `source=text/file/url content= divergence=` |
| `/nvEmotion` | 情感波段分析 | `range= fix=` |
| `/nvDungeon` | 密境/副本生成 | `name= type= level= floors=` |

## 專案結構

執行 `/nvGenesis` 後會建立：

```
projects/{name}/
├── config/
│   ├── novel_config.yaml      # 核心設定
│   ├── character_db.yaml      # 角色資料庫
│   ├── world_atlas.yaml       # 世界觀地圖
│   ├── faction_registry.yaml  # 勢力登記
│   ├── power_system.yaml      # 力量體系
│   ├── item_compendium.yaml   # 物品目錄
│   └── narrative_progress.yaml # 進度追蹤
├── output/
│   ├── chapters/              # 章節輸出
│   └── style_guide.md         # 風格指南
└── memory/
    ├── lore_bank.yaml         # 長期記憶
    └── emotion_log.yaml       # 情感波段記錄
```

## 核心配置參數

### pacing_pointer (速度指針)

控制每章推進多少劇情：

| 值 | 效果 |
|----|------|
| `1.0` | 快節奏，一章完成一個細目 |
| `0.5` | 中節奏，兩章完成一個細目 |
| `0.1` | 慢節奏，十章完成一個細目 |

### content_weights (內容權重)

控制各類內容的比例：

```yaml
content_weights:
  combat: 0.30           # 戰鬥描寫
  dialogue: 0.25         # 對話
  internal_monologue: 0.15  # 內心獨白
  scenery_desc: 0.15     # 環境描寫
  world_building: 0.10   # 世界觀補充
  action: 0.05           # 動作描寫
```

### emotion_settings (情感監控)

**新功能**：自動監控情感波段，防止連續高壓或低壓：

```yaml
emotion_settings:
  enabled: true
  high_tension_threshold: 70  # 高壓閾值
  low_tension_threshold: 30   # 低壓閾值
  max_consecutive_high: 3     # 連續高壓上限
  max_consecutive_low: 2      # 連續低壓上限
  buffer_mode: "suggest"      # suggest/force
```

### words_per_chapter (每章字數)

```yaml
words_per_chapter:
  min: 3000
  max: 5000
  target: 4000
```

## 可用 Presets

在 `/nvGenesis` 使用 `preset=` 參數：

| preset | 類型 | 特色 |
|--------|------|------|
| `xianxia` | 仙俠 | combat:0.4, internal:0.2 |
| `scifi` | 科幻 | world_building:0.2, action:0.15 |
| `romance` | 言情 | dialogue:0.4, internal:0.3 |
| `mystery` | 懸疑 | dialogue:0.35, scenery:0.2 |
| `fantasy` | 西幻 | combat:0.35, scenery:0.2 |
| `cyberpunk` | 賽博龐克 | combat:0.25, scenery:0.2 |
| `survival` | 末日生存 | combat:0.25, action:0.2, scenery:0.2 |

## nvMirror 使用方式

架構逆向與重鑄：借用外部劇情骨架，填入自己的世界觀。

```bash
# 直接文字輸入
/nvMirror proj=霓虹劍仙 source=text content="第一章：主角被陷害入獄..."

# 指定檔案
/nvMirror proj=霓虹劍仙 source=file path=/path/to/outline.md

# 指定網址
/nvMirror proj=霓虹劍仙 source=url url=https://example.com/novel

# 調整差異化程度（0=照搬，1=自主演化）
/nvMirror proj=霓虹劍仙 source=text content="..." divergence=0.8
```

## 角色雙軌制

系統採用雙軌制角色管理：

- **base_profile**：固定不變的人格基底（性格、背景、說話方式）
- **current_state**：動態更新的當前狀態（位置、健康、物品、情緒）
- **hidden_profile**：隱藏動機與秘密（僅供寫作參考）

這確保角色在成長的同時保持核心性格一致。

## 記憶系統

### 長期記憶 (lore_bank.yaml)
- 已發生事件（不可變）
- 關係變動記錄
- 伏筆追蹤

### 情感記憶 (emotion_log.yaml)
- 各章情感強度
- 張力曲線追蹤
- 自動緩衝建議

### 短期記憶 (status_snapshot)
- 當前場景狀態
- 角色即時狀態
- 物品位置

## 目錄結構

```
novel_bot2/
├── .agent/workflows/   # 16 個 Workflows
├── .agent/skills/      # 32 個 Skills
│   ├── foundation/     # 基石類 (7)
│   ├── structure/      # 結構類 (8)
│   ├── execution/      # 執行類 (8)
│   └── memory/         # 記憶類 (9)
├── templates/          # 設定檔模板
├── docs/               # 詳細文檔
└── projects/           # 專案資料夾
```

## 詳細文檔

- [Skills 說明](docs/SKILLS.md)
- [Workflows 說明](docs/WORKFLOWS.md)
- [Presets 說明](docs/PRESETS.md)
