---
description: 管理 czbooks.net 上的章節：上傳、更新、刪除、列表
---

# /nvUpload
此 workflow 用於管理 czbooks 平台上的章節，包括上傳、更新、刪除和列出。

## 使用條件
- 具有存放在專案根目錄的 `.czbooks_cookie`（已設置妥當）。
- 具有目標的 `proj` 參數（例如：`gou1`），或提供確切的 `novel-id`。
- 可設定 `state=draft` 或 `state=post`（預設為草稿模式）。
- 支援區段 `range=11-20`（也可用波浪號 11~20）或單一章節 `range=35`。

## 支援的操作

### 列出章節
```bash
.venv/bin/python tools/czbooks_manage.py list --proj <proj>
```

### 上傳新章節
```bash
.venv/bin/python tools/czbooks_manage.py upload --proj <proj> --range <range> --state <draft|post> [--dry]
```

### 更新已有章節
```bash
.venv/bin/python tools/czbooks_manage.py update --proj <proj> --range <range> --state <draft|post> [--dry]
```

### 刪除章節
```bash
.venv/bin/python tools/czbooks_manage.py delete --proj <proj> --range <range> [--dry]
```

## 參數說明
| 參數 | 說明 |
|------|------|
| `--proj` | 專案代號（對應 project_registry.yaml） |
| `--novel-id` | 直接指定 novel_id（跳過自動查找） |
| `--range` | 章節範圍，例如 `35-120` 或 `35` |
| `--state` | `draft`（草稿）或 `post`（發佈），預設 draft |
| `--dry` | Dry run，只顯示不執行 |

## 執行步驟
1. 讀取 `projects/project_registry.yaml` 取得 `proj` 對應的真實資料夾名稱。
2. 直接呼叫 `.venv/bin/python tools/czbooks_manage.py` 並帶入對應的子命令與參數。
3. 腳本內部會：
   - 使用 `project_registry.yaml` 找出小說的中文名稱。
   - 分析作者後台 (`/creator/list`) 找出對應的 Novel ID。
   - 對清單中的每一個 MD 檔案，自動抽取首列的 `# 標題` 作為章節名稱。
   - 自動將 `---` 之類的分隔線或章尾總結 (如 `## 章節總結`) 進行尾段裁切。
4. 回報結果給使用者，並提供後台檢視網址。

## 注意事項
- 刪除操作會從最後一章往前刪，避免分頁問題。
- 上傳操作需要現有章節作為錨點（使用最後一章的 edit + `?next_chapter=1`）。
- 每次操作之間有 delay 避免被限速。
- 建議先使用 `--dry` 確認操作目標再正式執行。
