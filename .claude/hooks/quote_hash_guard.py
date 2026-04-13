#!/usr/bin/env python3
"""
quote_hash_guard — PreToolUse hook for Bash
攔截引號字串內「換行 + #」的 pattern，避免觸發 path validation 警告。

偵測：
  - 雙引號 "..." 或單引號 '...' 內
  - 出現 literal newline + # 或 \\n + #

動作：
  - 回傳 permissionDecision: "deny"，附上改寫建議
"""
import json
import re
import sys


def find_violation(cmd: str):
    """Walk the command, track quote state, return violation description or None."""
    i = 0
    n = len(cmd)
    in_quote = None
    content_start = 0
    while i < n:
        c = cmd[i]
        if in_quote is None:
            if c in ('"', "'"):
                in_quote = c
                content_start = i + 1
            i += 1
            continue
        # inside a quote
        if c == '\\' and in_quote == '"' and i + 1 < n:
            i += 2
            continue
        if c == in_quote:
            content = cmd[content_start:i]
            # literal newline followed by optional whitespace + #
            if re.search(r'\n[ \t]*#', content):
                return 'literal newline followed by "#"'
            # escaped \n followed by #
            if re.search(r'\\n[ \t]*#', content):
                return '"\\n" escape followed by "#"'
            in_quote = None
        i += 1
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")
    if not cmd:
        sys.exit(0)

    violation = find_violation(cmd)
    if violation is None:
        sys.exit(0)

    reason = (
        f"Bash 指令被攔截：{violation} 出現在引號字串內。\n"
        "原因：此 pattern 會觸發 path validation 警告並中斷工作流。\n"
        "正確做法：\n"
        "  1. 用 Write 工具把腳本寫到 $TMPDIR/<name>.py\n"
        "  2. 再用 Bash 執行 `.venv/bin/python $TMPDIR/<name>.py`\n"
        "不要組 python -c / python3 -c 的內聯腳本。"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
