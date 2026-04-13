---
description: 重啟專案，保留設定但重新生成世界觀、角色和大綱
---

# /nvReboot - 重啟專案

從既有專案的 `novel_config.yaml` 設定重新開始，保留風格和引擎設定，重新生成世界觀、角色和大綱。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 來源專案名稱或代號 | `proj=goblin` |
| `arcs` | ❌ | 新大綱數量（覆蓋原設定） | `arcs=8` |
| `subarcs` | ❌ | 每卷細目數（覆蓋原設定） | `subarcs=5~8` |

## 使用範例

```
/nvReboot proj=goblin
/nvReboot proj=door arcs=8 subarcs=5~8
```

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，與 nvGenesis 類似需要串接多個 foundation skill。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 讀取 `projects/project_registry.yaml`，解析 `proj` 參數 → 取得來源專案資料夾名稱
3. 組合路徑：`SOURCE_DIR = {{REPO_ROOT}}/projects/{來源資料夾}`
4. 驗證參數
5. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `mode`: `bypassPermissions`
   - `run_in_background`: `false`
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
6. 接收 sub-agent 回傳的建立報告
7. 輸出結果給用戶

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將所有 `{{...}}` 變數替換為實際值。

````
你是小說專案重啟助手。請從既有專案設定重新開始一個新版本。

## 任務參數
- 來源專案代號：{{PROJ}}
- 來源專案路徑：{{SOURCE_DIR}}
- 新大綱數量：{{ARCS}}（若為空則沿用原設定）
- 新每卷細目數：{{SUBARCS}}（若為空則沿用原設定）
- 專案根目錄：{{REPO_ROOT}}

## 版本命名規則

重啟後的專案會自動加上流水號：
- 首次重啟：goblin → goblin_1
- 再次重啟：goblin_1 → goblin_2

## Step 1: 查找來源專案

1. 讀取 `{{SOURCE_DIR}}/config/novel_config.yaml`
2. 使用 Bash 掃描 `{{REPO_ROOT}}/projects/` 目錄找出該專案的現有版本
3. 決定新版本流水號，組合新專案路徑 `{{{NEW_DIR}}}`
4. 決定新代號 `{{{NEW_ALIAS}}}`，對應資料夾名 `{{NEW_PROJECT_FOLDER}}`

## Step 2: 建立新專案目錄

使用 Bash 建立目錄結構（與 nvGenesis 相同）：
```
{{{NEW_DIR}}}/
├── config/
│   ├── outline/
├── output/
│   ├── chapters/
└── memory/
```

## Step 3: 複製並更新設定檔

1. 複製來源的 novel_config.yaml
2. 更新 meta.project_id → 新的唯一 ID
3. 更新 meta.alias → NEW_ALIAS
4. 若指定 arcs，更新 structure.arcs
5. 若指定 subarcs，更新 structure.subarcs_per_arc
6. 更新 meta.created_at → 當前日期
7. 若 novel_config 中無 `time_system` 設定，根據 genre 自動補填：
   - 中式古風/仙俠/武俠/歷史架空 → `time_system: "時辰（一天12時辰，一時辰=2小時）"`
   - 其他題材 → `time_system: "小時（一天24小時）"`

## Step 4: 更新專案註冊檔

在 `{{REPO_ROOT}}/projects/project_registry.yaml` 新增：
```yaml
{{NEW_ALIAS}}: "{{NEW_PROJECT_FOLDER}}"
```

## Step 5: 重新生成風格指南

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/style_setter/SKILL.md` 並遵循其指令生成 `{{NEW_DIR}}/output/style_guide.md`。

## Step 6: 重新建構世界觀

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/world_builder/SKILL.md` 並遵循其指令生成新世界觀，直接寫入 SQLite 資料庫：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/atlas_query.py --proj {{NEW_ALIAS}} add --json '{"id":"REG_001","name":"...","region_type":"...","summary":"...","description":"...","climate":"...","locations":[...]}'
```

## Step 7: 重新設計力量體系

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/power_architect/SKILL.md` 並遵循其指令設計力量系統，寫入 `{{NEW_DIR}}/config/power_system.yaml`。

## Step 7.5: 參考原版角色（從資料庫讀取）

從來源專案的 SQLite 資料庫讀取原版角色概念作為參考：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} list
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} get CHAR_001,CHAR_002
```

## Step 8: 重新創建角色

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/character_forge/SKILL.md` 並遵循其指令：
- 1 個主角（可參考原版概念，但重新設計）
- 1 個主要反派
- 2-3 個配角

直接寫入新專案的 SQLite 資料庫（不寫 YAML）：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{NEW_ALIAS}} add --json '{"id":"...","name":"...","role":"...","type":"character","identity":"...","base_profile":{...},"current_state":{...}}'
```
角色間的關係也直接寫入：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{NEW_ALIAS}} add-rel SOURCE_ID TARGET_ID --surface "關係" --tension 50
```

## Step 9: 重新建立勢力

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/faction_forge/SKILL.md` 並遵循其指令創建 2-4 個勢力，直接寫入 SQLite 資料庫：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/faction_query.py --proj {{NEW_ALIAS}} add --json '{"id":"FAC_001","name":"...","tier":"...","type":"...","philosophy":"...","description":"...",...}'
cd {{REPO_ROOT}} && .venv/bin/python tools/faction_query.py --proj {{NEW_ALIAS}} add-rel FAC_001 FAC_002 --status "Hostile" --tension 80
```

## Step 10: 重新規劃大綱

讀取 `{{REPO_ROOT}}/.claude/skills/structure/outline_architect/SKILL.md` 並遵循其指令規劃全書結構：
- 寫入 `{{NEW_DIR}}/config/outline_index.yaml` 和 `{{NEW_DIR}}/config/outline/arc_{N}.yaml`
- 各 Arc 的 SubArc 數量應在指定範圍內隨機變動，勿固定中位數

## Step 11: 生成初始道具

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/item_smith/SKILL.md` 並遵循其指令為主角生成初始裝備，直接寫入 SQLite 資料庫（不寫 YAML）：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{NEW_ALIAS}} add --json '{"id":"...","name":"...","category":"...","description":"...","holder":"CHAR_001","obtained_chapter":0}'
```

## Step 12: 埋設角色秘密

讀取 `{{REPO_ROOT}}/.claude/skills/foundation/character_secret_seeder/SKILL.md` 並遵循其指令為主要角色生成隱藏動機。

## Step 13: 初始化動態檔案

創建 `{{NEW_DIR}}/` 下的檔案：
- `config/narrative_progress.yaml`（初始化）

> 情感記錄與角色關係不寫 YAML — 分別由 SQLite `emotion_log` 表與 `char_query update-rel` 管理。

## Step 14: 輸出確認

```
=== Reboot 完成 ===
來源專案：{source_project}
新專案：{new_project}
代號：{{NEW_ALIAS}}
大綱數：{arcs}
細目數：{subarcs_per_arc}
預估章數：約 {estimated_chapters}

可使用 /nvChapter proj={{NEW_ALIAS}} 開始寫作
```

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有內部 skill 改為「Read SKILL.md 路徑並遵循其指令」
2. 所有檔案路徑使用絕對路徑
3. 來源專案不受影響：不修改或刪除來源專案
4. 新專案與來源專案完全獨立
````

## 與 nvGenesis 的差異

| 項目 | nvGenesis | nvReboot |
|------|-----------|----------|
| 設定 | 全新輸入 | 從原專案繼承 |
| 代號 | 使用者指定 | 自動加流水號 |
| 世界觀 | 全新生成 | 全新生成 |
| 角色 | 全新創建 | 全新創建 |
