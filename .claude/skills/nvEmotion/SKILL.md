---
description: 情感波段分析與自動調整
---

# /nvEmotion - 情感波段分析

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `range` | ❌ | 分析範圍 | `range=1-25` |
| `fix` | ❌ | 自動修復模式 | `fix=true` |

## 使用範例

```bash
# 分析全專案情感曲線
/nvEmotion proj=霓虹劍仙

# 分析特定範圍
/nvEmotion proj=霓虹劍仙 range=10-20

# 啟用自動調整建議
/nvEmotion proj=霓虹劍仙 fix=true
```

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，需要讀取多章進行情緒曲線分析，屬獨立分析任務。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 讀取 `projects/project_registry.yaml`，解析 `proj` 參數 → 取得專案資料夾名稱
3. 組合路徑：`PROJECT_DIR = {{REPO_ROOT}}/projects/{資料夾名稱}`
4. 驗證參數（`range` 預設全部，`fix` 預設 false）
5. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `model`: `haiku`
   - `mode`: `bypassPermissions`
   - `run_in_background`: `false`
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
6. 接收並顯示 sub-agent 回傳的分析報告

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將 `{{PROJECT_DIR}}`、`{{PROJ}}`、`{{RANGE}}`、`{{FIX}}` 替換為實際值。

````
你是情感波段分析助手。請分析專案的情感曲線並生成報告。

## 任務參數
- 專案路徑：{{PROJECT_DIR}}
- 專案名稱：{{PROJ}}
- 分析範圍：{{RANGE}}（例如 "1-25" 或 "全部"）
- 自動修復：{{FIX}}（true/false）
- 專案根目錄：{{REPO_ROOT}}

## Step 1: 讀取設定

讀取 `{{PROJECT_DIR}}/config/novel_config.yaml` 中的 `emotion_settings`：
- high_tension_threshold（預設 70）
- low_tension_threshold（預設 30）
- max_consecutive_high（預設 3）
- max_consecutive_low（預設 2）

## Step 2: 載入章節

讀取 `{{PROJECT_DIR}}/config/narrative_progress.yaml` 確定章節範圍。
讀取範圍內的所有章節檔案：`{{PROJECT_DIR}}/output/chapters/chapter_{N}.md`

## Step 3: 分析各章情感

讀取 `{{REPO_ROOT}}/.claude/skills/memory/emotional_wave_analyzer/SKILL.md` 並遵循其指令。

對每一章分析以下維度：
- 戰鬥場景密度
- 對話張力
- 內心戲強度
- 恐懼/危機元素
- 浪漫/溫馨元素
- 懸念/謎題元素

## Step 4: 生成情感曲線

繪製 ASCII 情感張力曲線圖：
```
章節:  1  2  3  4  5  6  7  8  9  10
張力: ▁▂▄▆█▇▅▃▂▄
      L  M  H  H  H! H  M  L  L  M
```

## Step 5: 檢測問題

檢測：
- 連續高壓（超過 max_consecutive_high）
- 連續低壓（超過 max_consecutive_low）
- 情感斷裂（張力驟升驟降超過 50）

## Step 6: 輸出報告

使用以下格式：
```
═══════════════════════════════════════════════════
  情感波段分析報告
═══════════════════════════════════════════════════
  專案：{{PROJ}}
  分析範圍：第 {start}-{end} 章
───────────────────────────────────────────────────
  情感曲線：

  100│        ╭─╮
   80│    ╭──╯  ╰╮    ╭╮
   60│  ╭╯       ╰╮  ╭╯│
   40│╭╯          ╰╮╯  │    ╭
   20│╯            ╰   ╰──╮╭╯
    0└───────────────────────────
      1  5  10  15  20  25 (章)

───────────────────────────────────────────────────
  統計：
  ├─ 平均張力：{avg}
  ├─ 最高峰：第{N}章（{score}）
  ├─ 最低谷：第{N}章（{score}）
  └─ 標準差：{std}

───────────────────────────────────────────────────
  ⚠️ 問題檢測：

  [WARNING] {問題描述}
  → {建議}

───────────────────────────────────────────────────
  建議調整（fix=true 時自動套用）：
  {調整列表}
═══════════════════════════════════════════════════
```

## Step 7: 自動修復（fix=true 時）

若 fix=true，更新 `{{PROJECT_DIR}}/config/` 中相關的大綱/進度檔案。

## Step 8: 儲存結果

使用 emotion_query CLI 寫入情感記錄（SQLite）：
```bash
# 寫入各章分析結果
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} add {chapter_id} --tension {score} --emotion "{primary_emotion}" --elements '{...}' --note "..."

# 更新緩衝建議
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} set-suggestions --json '[...]'

# 更新連續計數
cd {{REPO_ROOT}} && .venv/bin/python tools/emotion_query.py --proj {{PROJ}} set-consecutive --json '{...}'
```

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有操作直接用 Read、Edit、Write、Bash 等工具完成
2. 所有檔案路徑使用絕對路徑
3. 最終輸出必須是完整的分析報告文字
````

## 輸出

分析結果存放於 SQLite `data/novel.db` 的 `emotion_chapters` 表。
