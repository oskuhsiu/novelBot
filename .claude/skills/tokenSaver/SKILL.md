---
name: tokenSaver
description: PreToolUse hook 自動壓縮 CLI 輸出，節省 LLM token
autoContext: false
---

# Token Saver

透過 PreToolUse hook 自動攔截 Bash 命令，壓縮輸出以節省 token。
零配置、零侵入 — hook 自動改寫命令或壓縮結果。

## 原則

- 能用原生 flag 解決的就直接改寫 flag（不過 python）
- 需要結構化壓縮的才走 python 腳本
- **最小化資料損失**（grep 截短 >200 字元行，diff 去 context lines，pytest 去 passed/warnings）
- 帶 pipe `|` 的命令不攔截

## 直接改寫 flag（hook 層，零開銷）

| 命令 | 改寫為 |
|------|--------|
| `git status` | `git status -sb` |
| `git log` | 注入 `--oneline --decorate` |
| `git branch -v/-vv` | 去掉 verbose flags |
| `tree` | 注入 `-I` 噪音目錄 pattern |
| `docker ps` | `--format` 精簡表格 |
| `docker images` | `--format` 精簡表格 |
| `gh pr list` | `--json` + `--template` 一行一筆 |
| `gh issue list` | `--json` + `--template` 一行一筆 |

## Python 壓縮器

| 命令 | 腳本 | 策略 |
|------|------|------|
| `ls` / `find` / `grep` / `diff` / `git diff` | token_saver.py | 去格式噪音、分組 |
| `git show` | token_saver_git.py | header 壓縮 + diff 壓縮 |
| `pytest` | token_saver_python.py | failure-only |
| `ruff` | token_saver_python.py | 按 rule 分組 |
| `mypy` | token_saver_python.py | 按檔案分組 |
| `curl` / `wget` | token_saver_cloud.py | 去 progress bar（不截斷 body） |

## 延伸文件

- [Git 延伸](ref/git.md)
- [Python 工具鏈](ref/python.md)
- [Cloud / System](ref/cloud.md)

## 腳本位置

所有腳本必須透過 `.venv/bin/python` 執行，位於 `.claude/skills/tokenSaver/scripts/`。
