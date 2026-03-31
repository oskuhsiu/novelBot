#!/usr/bin/env python3
"""token_saver_git.py — 壓縮 git 延伸命令輸出。

目前處理：git show
（git status/log/branch 由 hook 直接改寫 flag，不需 python）

用法：.venv/bin/python .claude/skills/tokenSaver/scripts/token_saver_git.py <command...>
"""
import subprocess
import sys
import re
import os

# 複用主腳本的 diff 壓縮器
sys.path.insert(0, os.path.dirname(__file__))
from token_saver import compress_diff


# ── git show 壓縮器 ────────────────────────────────────

def _compress_commit_header(text: str) -> str:
    """壓縮 commit header：去 Author/Date，壓成 short_hash + message。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    result = []
    current_hash = None
    current_message_lines = []
    current_decoration = ""

    def flush():
        if current_hash:
            short = current_hash[:7]
            msg = " ".join(current_message_lines).strip()
            if current_decoration:
                result.append(f"{short} ({current_decoration}) {msg}")
            else:
                result.append(f"{short} {msg}")

    for line in lines:
        m = re.match(r"^commit ([0-9a-f]+)(.*)", line)
        if m:
            flush()
            current_hash = m.group(1)
            current_message_lines = []
            dec_match = re.search(r"\((.+?)\)", m.group(2))
            current_decoration = dec_match.group(1) if dec_match else ""
            continue
        if line.startswith("Merge:"):
            current_message_lines.insert(0, "[merge]")
            continue
        if line.startswith("Author:") or line.startswith("Date:"):
            continue
        if not line.strip():
            continue
        current_message_lines.append(line.strip())

    flush()
    return "\n".join(result)


def compress_git_show(text: str) -> str:
    """git show = commit header + diff。分別壓縮兩部分。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    # 找到 diff 開始的位置
    diff_start = None
    for i, line in enumerate(lines):
        if line.startswith("diff --git") or line.startswith("diff "):
            diff_start = i
            break

    if diff_start is None:
        return _compress_commit_header(text)

    header_text = "\n".join(lines[:diff_start])
    diff_text = "\n".join(lines[diff_start:])

    header_compressed = _compress_commit_header(header_text)
    diff_compressed = compress_diff(diff_text)

    return header_compressed + "\n\n" + diff_compressed


# ── 命令分類 ──────────────────────────────────────────

def classify_git_command(cmd: str) -> str | None:
    """判斷 git 子命令類型。"""
    stripped = re.sub(r"^(cd\s+[^;&|]+\s*&&\s*)", "", cmd.strip())
    stripped = re.sub(r"^([A-Z_]+=\S+\s+)+", "", stripped)
    stripped = re.split(r"[;|]", stripped)[0].strip()

    tokens = stripped.split()
    if len(tokens) < 2 or os.path.basename(tokens[0]) != "git":
        return None

    if tokens[1] == "show":
        return "git_show"

    return None


COMPRESSORS = {
    "git_show": compress_git_show,
}


# ── Main ──────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: token_saver_git.py <command...>", file=sys.stderr)
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    kind = classify_git_command(cmd)

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=os.environ.get("ORIGINAL_CWD", None),
    )

    stdout = result.stdout
    stderr = result.stderr

    if kind and stdout:
        original_len = len(stdout)
        compressed = COMPRESSORS[kind](stdout)
        compressed_len = len(compressed)
        if compressed_len < original_len:
            saving = round((1 - compressed_len / original_len) * 100)
            stdout = compressed + f"\n[token_saver: {kind}, -{saving}%]"

    if stdout:
        sys.stdout.write(stdout)
        if not stdout.endswith("\n"):
            sys.stdout.write("\n")
    if stderr:
        sys.stderr.write(stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
