# tools/ 工具索引

所有 skill 呼叫的 CLI 工具都放在這裡。使用時一律透過：

```bash
cd <repo_root> && .venv/bin/python tools/<name>.py <args>
```

不確定用法時執行 `--help`。**這份索引不需載入進 LLM context**，skill 若缺某個工具，先 `Glob tools/**/*.py` 再對目標檔 `--help` 即可。

`lore_query.py` / `lore_update.py` 的詳細參數說明見 `tools/README.md`。

---

## 資料庫 / CLI 查詢（每個 skill 都會用）

| 工具 | 用途 |
|---|---|
| `char_query.py` | 角色資料查詢與更新（list/get/get-state/get-base/relations/search/update-state/update-field/update-rel/add/add-rel/stats）。`--json` 接受 inline 或 `@path` |
| `emotion_query.py` | 情感記錄（recent/get/range/add/analysis/suggestions/set-suggestions/set-consecutive/stats）。`--json`/`--elements` 支援 `@path` |
| `item_query.py` | 物品/交易/嗶嗶帳本（list/get/search/holder/by-category/update/add/transfer/balance/tx-*/bibi-*/stats）。`--json` 支援 `@path` |
| `faction_query.py` | 勢力資料庫（list/get/relations/events/search/add/add-rel/add-event/update-tension/update-field/stats）。`--json` 支援 `@path` |
| `atlas_query.py` | 世界地圖區域/地點（list/get/search/add/update-field/stats）。`--json` 支援 `@path` |
| `lore_query.py` | ChromaDB 向量檢索（lore/chapter/chapters/events/stats） |
| `lore_update.py` | ChromaDB 寫入（chapter/event/batch-event/delete）。`--json` 支援 `@path` |
| `review_query.py` / `review_db.py` | 審查結果查詢與持久化 |
| `style_bank_query.py` | 風格範本查詢與維護（search/random/list-tags/list-authors/list/stats/coverage/add/add-batch/remove/add-tags/remove-tag） |

---

## 核心工具

| 工具 | 用途 |
|---|---|
| `word_count.py` | **字數統計（唯一可用）**。禁用 `wc -m`/`perl`/`awk`/自寫 regex |
| `pack_context.py` | 打包 context 給本地 LLM（nvLocalLLM 使用） |
| `local_llm.py` | 本地 LLM API client（Qwen 等） |
| `czbooks_manage.py` | czbooks.net 章節上傳/更新/刪除/列表（nvUpload 使用） |
| `web_fetch.py` | 網頁抓取（nvStyleBankBuilder 暖站、抓取文本） |
| `migrate_db.py` | YAML → SQLite / ChromaDB 統一遷移（lore+char+emotion+item+faction+atlas） |

---

## 共用 helper（`tools/commons/`）

| 模組 | 用途 |
|---|---|
| `commons/json_arg.py` | `resolve_json_arg(value)`：讓 `--json` 接受 inline JSON 或 `@path` 檔案引用。所有 DB CLI 已整合 |

---

## Scheduler（`tools/scheduler/`）

nvScheduler 專用，避免在 SKILL.md 內嵌 `python -c`。

| 工具 | 用途 |
|---|---|
| `scheduler/state_write.py` | 把狀態 JSON 寫到 `$TMPDIR/claude_scheduler_<proj>.json` |
| `scheduler/pre_check.py` | 回傳 `{"paused": bool, "usage": float|null}` 給主迴圈判斷 |

---

## 維護 / 手動工具（不被 skill 自動呼叫）

| 工具 | 用途 |
|---|---|
| `slim_progress.py` | 清理 `narrative_progress.yaml` 的冗長 `completed_chapters`，並把舊章節摘要倒入 ChromaDB |
| `analyze_log.py` | 分析 Claude Code JSONL log（debug 用） |
| `fix_garbled.py` | 修復編碼錯誤的檔案（一次性） |

---

## 底層資料類別（從 Python import，不要從 Bash 呼叫）

```
char_db.py        emotion_db.py      item_db.py
faction_db.py     atlas_db.py        review_db.py
style_bank_db.py  lore_vector.py
```

這些是各 `*_query.py` 的 back-end。
