---
description: "MANUAL ONLY - 建構風格範本資料庫：從網路搜集真人文本片段並入庫"
---

# /nvStyleBankBuilder - 風格範本資料庫建構器

從網路搜集大量真人小說文本片段，經驗證、分類、打 tag 後存入全域 `data/style_bank.db`。

採用 **Dispatcher + BG Workers** 架構：Dispatcher 在主 context 負責規劃與暖站；每位作家由一個獨立 BG agent 處理。

## 參數

| 參數 | 必填 | 說明 | 預設 |
|------|------|------|------|
| `author` | ❌ | 指定單一作家 | — |
| `authors` | ❌ | 逗號分隔多位作家（批量模式） | — |
| `tags` | ❌ | 指定 tag（逗號分隔，只補充這些 tag） | — |
| `genre` | ❌ | 指定 genre（只補充該 genre 的範本） | — |
| `coverage` | ❌ | 只輸出覆蓋度報告，不抓取 | false |

## 使用範例

```
/nvStyleBankBuilder
/nvStyleBankBuilder author=烽火戲諸侯
/nvStyleBankBuilder authors=方想,管平潮,妖夜,跃千愁
/nvStyleBankBuilder tags=冷幽默,荒謬升級
/nvStyleBankBuilder genre=仙俠
/nvStyleBankBuilder coverage
```

---

## Dispatcher 流程（主 context 執行）

### Step 0：參數解析

1. `REPO_ROOT` = 當前工作目錄
2. 解析參數（author / authors / tags / genre / coverage）

### Step 1：環境檢查

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/style_bank_query.py stats
```

如果 `coverage=true`：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/style_bank_query.py coverage
```
輸出覆蓋度報告後結束。

查已有作家：
```bash
cd {{REPO_ROOT}} && .venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/style_bank.db')
rows = conn.execute('SELECT DISTINCT author FROM passages ORDER BY author').fetchall()
for r in rows: print(r[0])
conn.close()
"
```

### Step 2：暖站（拿 permission）

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/web_fetch.py fetch --text-only "https://tw.hjwzw.com/"
cd {{REPO_ROOT}} && .venv/bin/python tools/web_fetch.py fetch --text-only "https://big5.quanben-xiaoshuo.com/"
cd {{REPO_ROOT}} && .venv/bin/python tools/web_fetch.py fetch --text-only "https://czbooks.net/"
```

記下哪些站可用。

### Step 3：規劃目標作家清單

- **有 `author` 參數** → 單一作家
- **有 `authors` 參數** → 解析逗號分隔清單
- **有 `tags`/`genre` 參數** → 讀 `{{REPO_ROOT}}/novel_types.md` 選 3-4 位最合適的新作家
- **無參數** → 讀 `{{REPO_ROOT}}/novel_types.md` 選 3-4 位還沒收過的作家

為每位作家準備：作家名、代表作品名、建議站點、tag 重點方向。
跳過 Step 1 中已有的作家。

### Step 4：啟動 BG Workers

為每位作家啟動一個 BG Agent（**一個 message 內同時啟動所有**）：
- `subagent_type: general-purpose`
- `model: sonnet`
- `mode: bypassPermissions`
- `run_in_background: true`

每個 BG agent 的 prompt 使用下方 **BG Worker Prompt Template**。

### Step 5：等待 + 彙整

BG agents 完成後自動通知。收到所有結果後：

```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/style_bank_query.py stats
```

輸出合併報告：
```
風格範本庫更新完成
   本次新增：{N} 段（{author_1}: {n1}, {author_2}: {n2}, ...）
   DB 總計：{total} 段，{tag_count} 個 tag，{author_count} 位作家
```

---

## BG Worker Prompt Template

````
你是風格範本採集員。只負責一位作家的文本搜集、驗證、入庫。

## 任務
- 作家：{AUTHOR_NAME}
- 代表作：{WORK_NAME}
- 可用站點：{AVAILABLE_SITES}
- Tag 重點方向：{TAG_FOCUS}
- REPO_ROOT: {REPO_ROOT}

## 第一步：讀取規則
用 Read tool 讀取 {REPO_ROOT}/data/style_bank_worker_rules.md，嚴格遵守其中所有規則。
將 {AUTHOR_KEY}、{AUTHOR_NAME}、{WORK_NAME}、{REPO_ROOT} 替換為上方實際值。

## 流程
1. WebSearch 搜尋章節 URL（≤3 次）
2. web_fetch 逐頁抓取（≤5 次）
3. 切割 100-600 字片段，依規則驗證 + 打 tag
4. Write JSON 到臨時檔，add-batch --file 入庫
5. 回報：作家、新增段數、來源、覆蓋 tag
````
