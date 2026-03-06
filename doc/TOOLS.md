# Tools 使用說明

## czbooks_manage.py — czbooks.net 章節管理工具

**位置：** `tools/czbooks_manage.py`

管理 czbooks.net 上的小說章節，支援列出、刪除、上傳、更新四種操作。

### 前置需求

1. **Python 套件**
   ```bash
   pip3 install --break-system-packages pyyaml beautifulsoup4 curl_cffi
   ```

2. **Cookie 檔案** — `.czbooks_cookie`（專案根目錄）
   - 格式：`blackcat_SESSID=<your_session_id>`
   - 取得方式：登入 czbooks.net → 瀏覽器 DevTools → Application → Cookies → 複製 `blackcat_SESSID` 的值
   - Cookie 過期後需重新取得

3. **專案註冊** — `projects/project_registry.yaml`
   - 需有對應的 proj alias，例如 `gou1: "苟真君_1"`

### 章節檔案格式

本地章節檔案位於 `projects/<資料夾>/output/chapters/chapter_N.md`，格式：

```markdown
# 第 N 章 — 標題

正文內容...

---
## 章節總結
（這部分會被自動裁切，不會上傳）
```

- 首行 `# 標題` → 自動作為 czbooks 章節名稱
- 尾部 `---` 分隔線及 `## 章節總結` → 上傳時自動移除

### 子命令

#### `list` — 列出所有章節

```bash
python3 tools/czbooks_manage.py list --proj gou1 [--novel-id cr3jji]
```

輸出表格包含：章節編號、ID、字數、發佈狀態、章節名稱。

#### `delete` — 批次刪除章節

```bash
# 先 dry run 確認
python3 tools/czbooks_manage.py delete --proj gou1 --novel-id cr3jji --range 35-110 --dry

# 實際刪除
python3 tools/czbooks_manage.py delete --proj gou1 --novel-id cr3jji --range 35-110
```

- 從最後一章往前刪，避免分頁偏移
- 每次刪除間隔 1 秒

#### `upload` — 批次上傳新章節

```bash
# 草稿模式
python3 tools/czbooks_manage.py upload --proj gou1 --novel-id cr3jji --range 35-130 --state draft

# 直接發佈
python3 tools/czbooks_manage.py upload --proj gou1 --novel-id cr3jji --range 35-130 --state post
```

- 需要至少一個現有章節作為錨點（新章節接在最後一章之後）
- 每次上傳間隔 1.5 秒

#### `update` — 批次更新已有章節

```bash
python3 tools/czbooks_manage.py update --proj gou1 --novel-id cr3jji --range 35-50 --state post
```

- 以本地 chapter_N.md 覆蓋 czbooks 上對應章節的內容
- 按章節編號自動匹配 czbooks 上的 chapter_id

### 參數一覽

| 參數 | 必要 | 說明 |
|------|------|------|
| `--proj` | 是 | 專案代號（對應 project_registry.yaml） |
| `--novel-id` | 否 | 直接指定 czbooks novel_id，省略則自動從作者後台查找 |
| `--range` | 是* | 章節範圍：`35-120`、`35~120`、或單一章 `35`（list 不需要） |
| `--state` | 否 | `draft`（草稿，預設）或 `post`（發佈） |
| `--dry` | 否 | Dry run，只顯示操作目標不實際執行 |

### 已知的 novel_id 對照

| 專案 | proj | novel_id |
|------|------|----------|
| 苟真君 | gou1 | cr3jji |
