# Token Saver — Python 工具鏈

Python 壓縮器，由 `scripts/token_saver_python.py` 處理。

## 壓縮器

### pytest

- **策略**：failure focus（參考 rtk state machine parsing）
- 只保留 FAILURES/ERRORS 區塊 + summary 行
- 去掉 PASSED 行、progress dots、session header、warnings
- 全部 pass 時回傳 summary 一行

### ruff

- **策略**：按 rule code 分組（參考 rtk rule-based grouping）
- 格式：`── E501 (3)` + 底下列出各檔案位置
- 保留 fixable 統計

### mypy

- **策略**：按檔案分組（參考 rtk file-based grouping）
- 格式：`── path/file.py (5)` + 底下列出 `行號: [E/W/N] 訊息`
- 保留 summary 行

## 未來可擴展

| 命令 | 策略 | 優先度 |
|------|------|--------|
| `pip list` | 去版本號或壓成單行 | 低 |
| `pip install` | 只留最終結果 | 低 |
| `black` / `isort` | 只留變更檔案列表 | 低 |
