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
/nvGenesis name=霓虹劍仙 alias=neon source=text content="一個現代程式設計師穿越到賽博龐克世界..."
```

### 模式 C：從檔案生成
```
/nvGenesis name=霓虹劍仙 alias=neon source=file path=/Users/me/ideas/霓虹劍仙構想.md
```

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，因為需要串接 8+ 個 foundation skill，一次消耗巨量 token。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 驗證必填參數（`name`、`alias`）
3. 組合路徑：`PROJECT_DIR = {REPO_ROOT}/projects/{name}`
3. 若 `source=file`，確認檔案路徑存在
4. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `run_in_background`: `false`
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
5. 接收 sub-agent 回傳的建立報告
6. 輸出結果給用戶

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將所有 `{{...}}` 變數替換為實際值。

````
你是小說專案建立助手。請建立一個全新的小說專案。

## 任務參數
- 專案名稱：{{NAME}}
- 專案代號：{{ALIAS}}
- 小說類型：{{TYPE}}（若為空則從 source 分析推算）
- 來源類型：{{SOURCE}}（text/file/空）
- 來源內容：{{CONTENT}}（source=text 時的文字內容）
- 來源路徑：{{PATH}}（source=file 時的檔案路徑）
- 語言：{{LANG}}（預設 zh-TW）
- 預設模板：{{PRESET}}（空=不使用）
- 速度指針：{{PACING}}（預設 0.5）
- 目標字數：{{WORDS}}（預設 100000）
- 大綱數量：{{ARCS}}（預設 10）
- 每卷細目數：{{SUBARCS}}（預設 5~10）
- 專案路徑：{{PROJECT_DIR}}
- 專案根目錄：{{REPO_ROOT}}
- 模板路徑：{{REPO_ROOT}}/templates/

## Step 0: 解析簡述（若有 source）

若指定了 source：
- source=text → 使用 content 參數
- source=file → 讀取 path 指定的檔案

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/synopsis_analyzer/SKILL.md` 並遵循其指令分析簡述，推算 type、tone、arcs、beats、characters、world_hints。

## Step 1: 建立專案目錄

使用 Bash 建立目錄結構：
```
{{PROJECT_DIR}}/
├── config/
│   ├── outline/
├── output/
│   ├── chapters/
└── memory/
```

## Step 2: 初始化設定檔

複製 `{{REPO_ROOT}}/templates/` 下的範本到 `{{PROJECT_DIR}}/config/`，填入：
- meta.project_name = {{NAME}}
- meta.alias = {{ALIAS}}
- meta.language = {{LANG}}
- style_profile.genre = {{TYPE}} 或分析結果
- engine_settings.pacing_pointer = {{PACING}}
- structure.arcs = {{ARCS}}
- structure.subarcs_per_arc = {{SUBARCS}}

若指定 preset，載入預設值覆蓋。

## Step 3: 生成風格指南

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/style_setter/SKILL.md` 並遵循其指令生成 `{{PROJECT_DIR}}/output/style_guide.md`。

## Step 3.5: 設定主題追蹤

分析並設定 `{{PROJECT_DIR}}/config/novel_config.yaml` 中的 `theme_settings`：
- 識別主要主題和次要主題
- 設計 2-3 個主題意象
- 規劃主題弧線（opening, development, crisis, resolution）

## Step 4: 建構世界觀

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/world_builder/SKILL.md` 並遵循其指令生成世界觀，直接寫入 SQLite 資料庫：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/atlas_query.py --proj {{ALIAS}} add --json '{"id":"REG_001","name":"...","region_type":"...","summary":"...","description":"...","climate":"...","locations":[...]}'
```

## Step 5: 設計力量體系

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/power_architect/SKILL.md` 並遵循其指令設計力量系統，寫入 `{{PROJECT_DIR}}/config/power_system.yaml`。

## Step 6: 創建主要角色

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/character_forge/SKILL.md` 並遵循其指令：
- 若有簡述，參考分析結果中的 character_hints
- 否則預設創建：1 主角 + 1 反派 + 2-3 配角

直接寫入 SQLite 資料庫（不寫 YAML）。對每個角色執行：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{ALIAS}} add --json '{"id":"...","name":"...","role":"...","type":"character","identity":"...","base_profile":{...},"current_state":{...}}'
```
角色間的關係也直接寫入：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{ALIAS}} add-rel SOURCE_ID TARGET_ID --surface "關係" --tension 50
```

## Step 7: 建立勢力

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/faction_forge/SKILL.md` 並遵循其指令創建 2-4 個勢力，直接寫入 SQLite 資料庫：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/faction_query.py --proj {{ALIAS}} add --json '{"id":"FAC_001","name":"...","tier":"...","type":"...","philosophy":"...","description":"...",...}'
cd {{REPO_ROOT}} && .venv/bin/python tools/faction_query.py --proj {{ALIAS}} add-rel FAC_001 FAC_002 --status "Hostile" --tension 80
```

## Step 8: 規劃大綱

讀取 `{{REPO_ROOT}}/.claude/skills/structure/outline_architect/SKILL.md` 並遵循其指令規劃全書結構：
- 寫入 `{{PROJECT_DIR}}/config/outline_index.yaml`
- 寫入 `{{PROJECT_DIR}}/config/outline/arc_{N}.yaml`（每個 Arc 一個檔案）
- 若有簡述，使用分析結果中的 arc_summaries
- 確保大綱與 theme_arc 對應

## Step 9: 生成初始道具

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/item_smith/SKILL.md` 並遵循其指令為主角生成初始裝備，直接寫入 SQLite 資料庫（不寫 YAML）：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{ALIAS}} add --json '{"id":"...","name":"...","category":"...","description":"...","holder":"CHAR_001","obtained_chapter":0}'
```

## Step 10: 初始化動態檔案

創建 `{{PROJECT_DIR}}/memory/` 下的動態追蹤檔案：
- emotion_log.yaml（空白模板） — 情感記錄實際使用 SQLite
- motivation_map.yaml（動機地圖模板）
- relationship_dynamics.yaml（關係動態模板）
- archive_index.yaml（冷儲存索引模板）

## Step 11: 埋設角色秘密

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/character_secret_seeder/SKILL.md` 並遵循其指令為主要角色生成隱藏動機。

## Step 12: 更新專案註冊檔

在 `{{REPO_ROOT}}/projects/project_registry.yaml` 新增：
```yaml
{{ALIAS}}: "{{NAME}}"
```

## Step 13: 輸出確認

顯示專案建立結果摘要：
```
═══════════════════════════════════════════════════
  專案建立完成
═══════════════════════════════════════════════════
  專案名稱：{{NAME}}
  代號：{{ALIAS}}
  類型：{type}
  來源：{source 或 "手動指定"}
───────────────────────────────────────────────────
  大綱：{arcs} 卷
  細目：約 {total_subarcs} 個
  預估章數：{estimated_chapters}
───────────────────────────────────────────────────
  可使用 /nvChapter proj={{ALIAS}} 開始寫作
═══════════════════════════════════════════════════
```

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有內部 skill 改為「Read SKILL.md 路徑並遵循其指令」
2. 所有檔案路徑使用絕對路徑
3. 最終輸出必須是完整的建立報告文字

## 可用 Presets

| preset | 說明 |
|--------|------|
| xianxia | 仙俠/修仙 (combat:0.4, internal:0.2) |
| scifi | 科幻 (world_building:0.2, action:0.15) |
| romance | 言情 (dialogue:0.4, internal:0.25) |
| mystery | 懸疑 (dialogue:0.35, scenery:0.2) |
| fantasy | 西幻 (combat:0.35, scenery:0.2) |

## 大綱結構說明

本系統採用 Arc-SubArc-Chapter 三層架構。

章節數計算公式：
```
總細目數 = arcs × subarcs_per_arc
總章節數 ≈ 總細目數 / pacing_pointer
```
````

## 與 nvMirror 的差異

| 功能 | nvGenesis | nvMirror |
|------|-----------|----------|
| 用途 | **創建**新專案 | 為**已有專案**套用外部架構 |
| 角色 | 從簡述分析或新生成 | 使用專案現有角色 |
| 世界觀 | 從簡述分析或新生成 | 使用專案現有世界觀 |
| 大綱 | 從簡述分析或新生成 | 映射外部架構到現有設定 |

## 專案代號說明

`alias` 是一個簡短的英數字代號，方便在後續操作中快速引用專案。代號會同時記錄在：
1. `config/novel_config.yaml` 的 `meta.alias`
2. 全域專案註冊檔 `projects/project_registry.yaml`
