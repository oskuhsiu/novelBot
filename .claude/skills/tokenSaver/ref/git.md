# Token Saver — Git 延伸

## Hook 直接改寫（不過 python）

| 命令 | 改寫規則 |
|------|----------|
| `git status [any flags]` | → `git status -sb` |
| `git log [flags]` | → 注入 `--oneline --decorate`（已有 `--oneline` 則跳過） |
| `git branch -v/-vv` | → 去掉 verbose flags |

## Python 壓縮器（scripts/token_saver_git.py）

### git show

- commit header：去 Author/Date，壓成 `short_hash message`
- diff 部分：複用 `compress_diff`（去 context lines / metadata）
- merge commit（無 diff）：只壓縮 header

## Hook 路由

hook 自動判斷 git 子命令：
- `git status` / `git log` / `git branch` → hook 直接改寫 flag
- `git diff` → `token_saver.py`（主腳本）
- `git show` → `token_saver_git.py`（本腳本）

## 未來可擴展

| 命令 | 策略 | 優先度 |
|------|------|--------|
| `git blame` | 去 author/date，只留 short_hash + 內容 | 中 |
| `git stash list` | 去 hash，只留 message | 低 |
| `git remote -v` | fetch/push 相同時合併 | 低 |
