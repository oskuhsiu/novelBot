#!/bin/bash
# token_saver_hook.sh — PreToolUse hook for Bash commands
# 攔截特定命令：
#   1) 直接改寫 flag（git status/log/branch, tree, docker, gh）— 不過 python
#   2) 通過 token_saver 腳本壓縮輸出（ls/find/grep/diff, pytest/ruff/mypy, curl）

INPUT="$(cat)"
COMMAND="$(echo "$INPUT" | jq -r '.tool_input.command // empty')"
CWD="$(echo "$INPUT" | jq -r '.cwd // empty')"

if [ -z "$COMMAND" ]; then
    exit 0
fi

# 不處理帶 pipe 的命令（已有自訂處理）
if echo "$COMMAND" | grep -q '|'; then
    exit 0
fi

# 取得 repo root（hook 本身的位置往上兩層）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv/bin/python"
SKILLS="$REPO_ROOT/.claude/skills/tokenSaver/scripts"

# 去掉前導 cd 和環境變數，取得核心命令用於判斷
STRIPPED="$(echo "$COMMAND" | sed 's/^[A-Z_]*=[^ ]* //g')"
BASE="$(echo "$STRIPPED" | awk '{print $1}' | xargs basename 2>/dev/null)"
ARG2="$(echo "$STRIPPED" | awk '{print $2}')"

emit() {
    jq -n --arg cmd "$1" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            updatedInput: { command: $cmd }
        }
    }'
    exit 0
}

# ── 1. 直接改寫 flag（不需 python） ─────────────────────

# Git
if [ "$BASE" = "git" ]; then
    case "$ARG2" in
        status)
            # 保留原始 flags（如 path filter），注入 -sb
            if echo "$COMMAND" | grep -q '\-sb\|\-s '; then
                exit 0
            fi
            NEW_CMD="$(echo "$COMMAND" | sed 's/git status/git status -sb/')"
            emit "$NEW_CMD"
            ;;
        log)
            if echo "$COMMAND" | grep -q '\-\-oneline'; then
                exit 0
            fi
            NEW_CMD="$(echo "$COMMAND" | sed 's/git log/git log --oneline --decorate/')"
            emit "$NEW_CMD"
            ;;
        branch|br)
            NEW_CMD="$(echo "$COMMAND" | sed 's/ -vv\?//g')"
            emit "$NEW_CMD"
            ;;
    esac
fi

# Tree — 注入噪音目錄過濾
NOISE_PATTERN="node_modules|.git|__pycache__|.venv|venv|.mypy_cache|.pytest_cache|.ruff_cache|.tox|dist|build|.next|.nuxt|.egg-info|.DS_Store"
if [ "$BASE" = "tree" ]; then
    if echo "$COMMAND" | grep -q '\-I'; then
        exit 0
    fi
    NEW_CMD="$(echo "$COMMAND" | sed "s/tree/tree -I '$NOISE_PATTERN'/")"
    emit "$NEW_CMD"
fi

# Docker — 用 --format 精簡表格
if [ "$BASE" = "docker" ]; then
    case "$ARG2" in
        ps)
            if echo "$COMMAND" | grep -q '\-\-format'; then
                exit 0
            fi
            # 保留原始 flags（-a, --filter 等），注入 --format
            NEW_CMD="$(echo "$COMMAND" | sed "s/docker ps/docker ps --format 'table {{.Names}}\\\t{{.Status}}\\\t{{.Image}}\\\t{{.Ports}}'/")"
            emit "$NEW_CMD"
            ;;
        images)
            if echo "$COMMAND" | grep -q '\-\-format'; then
                exit 0
            fi
            NEW_CMD="$(echo "$COMMAND" | sed "s/docker images/docker images --format 'table {{.Repository}}\\\t{{.Tag}}\\\t{{.Size}}'/")"
            emit "$NEW_CMD"
            ;;
    esac
fi

# GitHub CLI — 精簡欄位
if [ "$BASE" = "gh" ]; then
    ARG3="$(echo "$STRIPPED" | awk '{print $3}')"
    if [ "$ARG3" = "list" ] && ! echo "$COMMAND" | grep -q '\-\-json'; then
        case "$ARG2" in
            pr)
                emit "gh pr list --json number,title,state,author --template '{{range .}}#{{.number}} {{.title}} ({{.state}}, @{{.author.login}}){{\"\\n\"}}{{end}}'"
                ;;
            issue)
                emit "gh issue list --json number,title,state,author --template '{{range .}}#{{.number}} {{.title}} ({{.state}}, @{{.author.login}}){{\"\\n\"}}{{end}}'"
                ;;
        esac
    fi
fi

# ── 2. 通過 python 壓縮器 ───────────────────────────────
SHOULD_REWRITE=0
SAVER=""
case "$BASE" in
    # System（主壓縮器）
    ls|exa|eza)   SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver.py" ;;
    find)         SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver.py" ;;
    grep|rg)      SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver.py" ;;
    diff)         SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver.py" ;;
    git)
        case "$ARG2" in
            diff)  SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver.py" ;;
            show)  SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_git.py" ;;
        esac
        ;;
    # Python 工具鏈
    pytest)       SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_python.py" ;;
    ruff)         SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_python.py" ;;
    mypy)         SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_python.py" ;;
    # Cloud（curl progress stripping）
    curl|wget)    SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_cloud.py" ;;
esac

# python -m pytest 也要攔截
if [ "$BASE" = "python" ] || [ "$BASE" = "python3" ]; then
    if echo "$COMMAND" | grep -q '\-m pytest'; then
        SHOULD_REWRITE=1; SAVER="$SKILLS/token_saver_python.py"
    fi
fi

if [ "$SHOULD_REWRITE" -eq 1 ]; then
    emit "ORIGINAL_CWD=\"$CWD\" $VENV $SAVER $COMMAND"
fi

# 不需要處理的命令，正常放行
exit 0
