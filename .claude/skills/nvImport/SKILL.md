---
description: 從既有內容導入並繼續寫作
---

# /nvImport - 導入既有內容

從已有的小說內容導入，建立資料庫後繼續寫作。

## 參數

| 參數 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `file` | ✅ | 來源檔案 | `file=existing.txt` |
| `proj` | ✅ | 新專案名稱 | `proj=霓虹劍仙` |
| `type` | ❌ | 小說類型 | `type=仙俠` |
| `lang` | ❌ | 語言 | `lang=zh-TW` |

## 使用範例

```
/nvImport file=~/novels/my_novel.txt proj=霓虹劍仙 type=賽博龐克
/nvImport file=existing.md proj=劍來
```

---

## 執行模式：Sub-Agent

本 skill 透過 sub-agent 執行，因為需要解析大檔案 + 結構萃取 + 向量索引，完全獨立處理。

### 調度步驟（主 context 執行）

1. 取得 repo 根目錄：`REPO_ROOT` = 當前工作目錄（即專案 repo 根）
2. 驗證必填參數（`file`、`proj`）
3. 確認來源檔案路徑存在（展開 `~` 為絕對路徑）
4. 組合路徑：`PROJECT_DIR = {{REPO_ROOT}}/projects/{proj}`
5. 啟動 Agent tool：
   - `subagent_type`: `general-purpose`
   - `mode`: `bypassPermissions`
   - `run_in_background`: `false`
   - `prompt`: 將下方「Agent Prompt」的變數替換為實際值
6. 接收 sub-agent 回傳的導入報告
7. 輸出結果給用戶

---

## Agent Prompt

以下為傳給 sub-agent 的完整指令。Dispatcher 需將所有 `{{...}}` 變數替換為實際值。

````
你是小說導入助手。請從既有小說內容導入並建立專案資料庫。

## 任務參數
- 來源檔案：{{FILE}}
- 專案名稱：{{PROJ}}
- 小說類型：{{TYPE}}（若為空則自動分析）
- 語言：{{LANG}}（預設 zh-TW）
- 專案路徑：{{PROJECT_DIR}}
- 專案根目錄：{{REPO_ROOT}}

## Step 1: 讀取來源

讀取 {{FILE}} 的內容。若檔案很大，分段讀取。

## Step 2: 分析結構

分析既有內容：
- 章節劃分（識別章節標記）
- 角色提取（出現的所有角色名）
- 場景識別（地點和場景）
- 事件提取（關鍵劇情事件）

## Step 3: 建立專案

使用 Bash 建立 `{{PROJECT_DIR}}/` 目錄結構：
```
{{PROJECT_DIR}}/
├── config/
│   ├── outline/
├── output/
│   ├── chapters/
└── memory/
```

從 `{{REPO_ROOT}}/templates/` 複製範本並填入基本參數。

## Step 4: 提取角色

從文本中識別角色（名稱、出場頻率、性格推測、關係推測），直接寫入 SQLite 資料庫（不寫 YAML）：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} add --json '{"id":"CHAR_001","name":"...","role":"Protagonist","type":"character","identity":"...","base_profile":{...},"current_state":{...}}'
```
角色間的關係也直接寫入：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/char_query.py --proj {{PROJ}} add-rel SOURCE_ID TARGET_ID --surface "關係" --tension 50
```

## Step 5: 提取場景

識別地點和場景（名稱、描述、出現章節），直接寫入 SQLite 資料庫：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/atlas_query.py --proj {{PROJ}} add --json '{"id":"REG_001","name":"...","region_type":"...","summary":"...","description":"...","locations":[...]}'
```

## Step 6: 建立記憶庫

提取已發生事件（關鍵事件、關係變動、物品交換），寫入 ChromaDB：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} event --id "{id}" --cat "{category}" --ch {chapter} --name "{name}" --status "{status}" --doc "{document}"
# --char "{char_id}" 為選填，僅在事件有明確關聯角色時才加上
```

## Step 7: 分析風格

分析既有風格特徵（句式偏好、用詞風格、節奏特徵），寫入 `{{PROJECT_DIR}}/output/style_guide.md`。

## Step 8: 複製章節並建立向量索引

將既有章節分別寫入 `{{PROJECT_DIR}}/output/chapters/chapter_{N}.md`。

對每一章生成 ending_summary 並寫入 ChromaDB：
```bash
cd {{REPO_ROOT}} && .venv/bin/python tools/lore_update.py --proj {{PROJ}} chapter --id {N} --title "{title}" --arc "imported" --subarc "imported" --words {word_count} --summary "{ending_summary}"
```

## Step 9: 準備繼續

設定 `{{PROJECT_DIR}}/config/narrative_progress.yaml`：
- current_chapter = 既有章節數 + 1

生成後續大綱建議，寫入 outline 檔案。

更新 `{{REPO_ROOT}}/projects/project_registry.yaml` 新增專案。

## Step 10: 輸出確認

```
═══════════════════════════════════════════════════
  導入完成
═══════════════════════════════════════════════════
  來源：{{FILE}}
  專案名稱：{{PROJ}}
  匯入章數：{N} 章
  識別角色：{count} 個
  識別場景：{count} 個
  事件記錄：{count} 條
───────────────────────────────────────────────────
  可使用 /nvChapter proj={{PROJ}} 繼續寫作
═══════════════════════════════════════════════════
```

## 重要注意事項

1. 你無法使用 `/nvXXX` skill 指令，所有操作直接用 Read、Write、Bash 等工具完成
2. ChromaDB 操作使用 Bash 執行 python 腳本
3. 所有檔案路徑使用絕對路徑
4. 最終輸出必須是完整的導入報告文字
````

## 輸出

專案建立完成，可用 `/nvChapter proj={proj}` 繼續寫作。
