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
/nvMirror proj=霓虹劍仙 source=text content="第一章：主角被陷害入獄..."
/nvMirror proj=霓虹劍仙 source=file path=/Users/me/reference/outline.md
/nvMirror proj=霓虹劍仙 source=url url=https://example.com/novel-outline
/nvMirror proj=霓虹劍仙 source=text content="..." divergence=0.8 chapters=10
```

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，三階段 pipeline（解構→映射→重組）完全獨立。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 讀取 `projects/project_registry.yaml`，解析 `proj` 參數 → 取得專案資料夾名稱
3. 組合路徑：`PROJECT_DIR = {REPO_ROOT}/projects/{資料夾名稱}`
3. 驗證參數（`divergence` 預設 0.5，`chapters` 預設 5）
4. 若 `source=file`，確認檔案路徑存在
5. 若 `source=url`，將 URL 傳給 sub-agent（sub-agent 用 WebFetch 抓取）
6. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `run_in_background`: `false`
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
7. 接收並顯示 sub-agent 回傳的映射報告

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將所有 `{{...}}` 變數替換為實際值。

````
你是架構逆向與重鑄助手。請借用外部劇情骨架並映射到目標專案。

## 任務參數
- 目標專案路徑：{{PROJECT_DIR}}
- 目標專案名稱：{{PROJ}}
- 來源類型：{{SOURCE}}（text/file/url）
- 來源內容：{{CONTENT}}（source=text 時）
- 來源路徑：{{PATH}}（source=file 時）
- 來源網址：{{URL}}（source=url 時）
- 差異化程度：{{DIVERGENCE}}（0-1，預設 0.5）
- 生成章數：{{CHAPTERS}}（預設 5）
- 專案根目錄：{{REPO_ROOT}}

## Step 1: 載入來源素材

根據 source 類型：
- text：直接使用 content 參數
- file：讀取指定路徑的檔案內容
- url：使用 WebFetch 抓取網頁內容

## Step 2: 結構解構 (Deconstruct)

讀取 `{{REPO_ROOT}}/.claude/skills/structure/schema_re_architect/SKILL.md` 並遵循其指令分析來源素材。

提取抽象結構：
- 衝突核心：主要矛盾
- 角色功能：各角色的敘事作用（導師/對手/盟友/背叛者）
- 轉折節點：關鍵事件的位置和類型
- 情感曲線：張力的高低變化
- 節奏模式：快慢交替的規律

## Step 3: 載入目標專案

讀取目標專案的設定檔：
- `{{PROJECT_DIR}}/config/novel_config.yaml`
- 角色資料庫（SQLite）：`cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} list` + 按需 `get`
- `{{PROJECT_DIR}}/config/faction_registry.yaml`
- `{{PROJECT_DIR}}/config/world_atlas.yaml`
- `{{PROJECT_DIR}}/config/power_system.yaml`

## Step 4: 語義映射 (Map)

將抽象結構映射到目標專案：
- 角色對應：source 角色功能 → target 角色
- 場景對應：source 場景 → target 地點
- 力量對應：source 能力 → target 力量體系

## Step 5: 差異化處理 (Divergence)

根據 divergence 參數調整映射：
- 0.0：完全複製轉折邏輯，僅替換名詞
- 0.3：保留大框架，細節允許變化
- 0.5：保留衝突核心和主要節點，解決方法自由發揮
- 0.7：僅參考情感曲線和節奏，具體事件自訂
- 1.0：僅借用起始動機，隨後完全自主演化

## Step 6: 重構大綱 (Reconstruct)

生成新的章節大綱：
```yaml
chapter_X:
  title: "章節標題（符合目標專案風格）"
  source_reference: "對應來源的第N章"
  beats:
    - id: "BX_1"
      summary: "場景描述（使用目標專案的角色/地點/力量）"
  divergence_notes: "這裡與來源不同的地方"
```

## Step 7: 一致性驗證

讀取 `{{REPO_ROOT}}/.claude/skills/memory/consistency_validator/SKILL.md` 並遵循其指令檢查：
- 大綱與目標專案設定相容
- 角色行為符合 base_profile
- 場景符合 world_atlas 地理邏輯

## Step 8: 寫入大綱

將生成的大綱寫入 `{{PROJECT_DIR}}/output/mirror_outline.yaml`（或追加到 story_outline.yaml）。

## Step 9: 輸出報告

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

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有內部 skill 改為「Read SKILL.md 路徑並遵循其指令」
2. 所有檔案路徑使用絕對路徑
3. 最終輸出必須是完整的映射報告文字
````

## 輸出

生成的大綱存放於 `output/mirror_outline.yaml` 或直接整合至 `story_outline.yaml`。
