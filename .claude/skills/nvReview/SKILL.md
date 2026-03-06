---
description: 執行一致性檢查
---

# /nvReview - 一致性與邏輯審查

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `proj` | ✅ | 專案名稱 | `proj=霓虹劍仙` |
| `range` | ❌ | 檢查範圍 (預設最近5章) | `range=5` 或 `range=1-20` |
| `chapter` | ❌ | 指定審查單章 | `chapter=12` |
| `mode` | ❌ | `light` / `full`（預設） | `mode=light` |

- `light`：Categories 1-3 + 基本錯字
- `full`：全部 8 項檢查
- `chapter` 與 `range` 擇一，都未指定則審查最近 5 章

## 執行模式：Sub-Agent

1. `REPO_ROOT` = 當前工作目錄
2. 從 `projects/project_registry.yaml` 解析 `proj` → `PROJECT_DIR`
3. 啟動 Agent tool（`subagent_type: general-purpose`，`run_in_background: false`）
4. 將下方 Agent Prompt 的 `{{...}}` 替換為實際值
5. 接收並**原封不動**輸出審查報告

---

## Agent Prompt

````
你是小說審查助手。請對專案執行一致性與邏輯審查。

## 任務參數
- 專案路徑：{{PROJECT_DIR}}
- 專案名稱：{{PROJ}}
- 審查模式：{{MODE}}（light 或 full）
- 審查範圍：{{RANGE_OR_CHAPTER}}

## 模式速查
- **light**：僅 Categories 1-3 + 錯字偵測，報告僅列 Critical/Warning
- **full**：全部 Categories 1-8

## Step 1: 載入審查上下文

讀取（按需）：
- `{{PROJECT_DIR}}/config/novel_config.yaml` — 世界觀規則
- `{{PROJECT_DIR}}/config/narrative_progress.yaml` — 時間線
- 角色資料庫（SQLite）：
  ```bash
  cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} list
  cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} get {CHAR_IDS}
  ```
- `{{PROJECT_DIR}}/config/power_system.yaml` — 能力限制（full mode）
- 物品資料庫（SQLite，full mode）：
  ```bash
  cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} list
  cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} get {ITEM_IDS}
  cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} bibi-pending
  cd {{REPO_ROOT}} && .venv/bin/python tools/item_query.py --proj {{PROJ}} balance
  ```

## Step 2: 載入章節文本

- `chapter=N`：讀取 chapter_N.md
- `range=N`：最近 N 章
- `range=A-B`：第 A 到 B 章
- 同時讀取審查範圍前 2-3 章作為前文參照

## 審查類別

### 🔴 Cat 1: 情節邏輯 【light ✅ | full ✅】
- **時間線矛盾**：年齡vs事件、章節間時間流逝、同日事件排列
- **因果矛盾**：結果與前提衝突、重傷後無交代恢復、同時在兩地
- **數量/距離錯誤**：兵力資源不一致、旅行時間不合理

### 🔴 Cat 2: 吃書偵測 【light ✅ | full ✅】

用 ChromaDB 交叉比對：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_query.py --proj {{PROJ}} lore "{關鍵詞}" --n 10
```
- 世界觀法則被破壞、「不可逆」被逆轉、「唯一」出現第二件
- 已死亡角色無解釋出現、已失去能力無解釋恢復

### 🔴 Cat 3: 能力合法性 【light ✅ | full ✅】
- 冷卻/次數限制違反、已消耗品再次出現
- 使用超過等級的能力/未習得技能
- 能力代價被忽略

### 🟡 Cat 4: 錯字與文字品質 【light ✅(僅錯字) | full ✅(全部)】
- light：錯別字、同音異形字、漏字多字、標點誤用
- full：加查語句通順度、主謂賓結構、上下文銜接、突兀用詞

## === LIGHT MODE 到此結束 ===
## 以下 Categories 5-8 僅 mode=full 時執行

### 🟡 Cat 5: 角色行為一致性 【full only】
- 性格偏差（vs base_profile.traits）、語氣一致性、動機連貫

### 🟡 Cat 6: 連戲檢查 【full only】
- 物品連續性、傷勢追蹤、位置轉換、服裝/外貌

### 🟢 Cat 7: 伏筆健康 【full only】
- 休眠伏筆（超過 N 章未提及）、逾期伏筆、伏筆衝突

### 🟢 Cat 8: 世界觀一致性 【full only】
- 地理（vs world_atlas）、文化/社會、政治/勢力

## Step 3: 生成審查報告

```
═══════════════════════════════════════════════════════
  📋 審查報告：{{PROJ}}
  模式：{{MODE}} | 範圍：第 {start} - {end} 章
═══════════════════════════════════════════════════════

🔴 Critical — 必須修正
  [{類別}] [Ch.{N}] {問題}
    引用：「{原文}」
    原因：{為何錯誤}
    建議：{修正方案}

⚠️ Warning — 建議修正
  [{類別}] [Ch.{N}] {問題}
    建議：{修正方案}

💡 Minor — 可選修正
  [{類別}] [Ch.{N}] {問題}

✅ 通過：{列出已通過類別}

  統計：Critical {n} | Warning {n} | Minor {n}
═══════════════════════════════════════════════════════
```

> light 模式：僅列 Critical/Warning。全部通過則輸出 `✅ 第 {N} 章審查通過（light mode）`

## 注意事項
- 無法使用 `/nvXXX` skill，直接用 Read/Bash/Grep 操作
- **Context 重用**：已在 context 中的檔案不重複讀取
````
