#!/usr/bin/env python3
"""token_saver_cloud.py — 壓縮 Cloud/System 工具輸出。

處理：curl (去 progress bar)
（docker, gh 由 hook 直接改寫 --format flag）

用法：.venv/bin/python .claude/skills/tokenSaver/scripts/token_saver_cloud.py <command...>
"""
import subprocess
import sys
import re
import os


# ANSI escape code pattern
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# curl progress bar patterns
CURL_PROGRESS_RE = re.compile(
    r"^\s*(%\s+Total|"          # progress header
    r"\d+\s+\d+\s+\d+|"        # progress numbers
    r"[#\-=]+|"                 # progress bar characters
    r"\s*Dload|"                # download header
    r"\s*Upload|"               # upload header
    r"\s*\d+[kMG]?\s+\d+)"     # transfer stats
)


def compress_curl(text: str) -> str:
    """去掉 curl progress bar 和 ANSI codes，保留完整 response body。

    rtk 策略：progress filtering + ANSI stripping，不截斷內容。
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    result = []
    for line in lines:
        # 去 ANSI codes
        clean = ANSI_RE.sub("", line)
        # 去 progress bar 行
        if CURL_PROGRESS_RE.match(clean):
            continue
        # 去 curl stats 行（速度、時間等）
        if re.match(r"^\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+", clean):
            continue
        # 去空行（連續）
        if not clean.strip():
            if result and not result[-1].strip():
                continue
        result.append(clean)

    return "\n".join(result)


def classify_command(cmd: str) -> str | None:
    stripped = re.sub(r"^(cd\s+[^;&|]+\s*&&\s*)", "", cmd.strip())
    stripped = re.sub(r"^([A-Z_]+=\S+\s+)+", "", stripped)
    stripped = re.split(r"[;|]", stripped)[0].strip()

    tokens = stripped.split()
    if not tokens:
        return None

    base = os.path.basename(tokens[0])
    if base in ("curl", "wget"):
        return "curl"

    return None


COMPRESSORS = {
    "curl": compress_curl,
}


def main():
    if len(sys.argv) < 2:
        print("Usage: token_saver_cloud.py <command...>", file=sys.stderr)
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    kind = classify_command(cmd)

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=os.environ.get("ORIGINAL_CWD", None),
    )

    stdout = result.stdout
    stderr = result.stderr

    # curl 的 progress 通常在 stderr
    if kind == "curl":
        if stderr:
            original_len = len(stderr)
            compressed = compress_curl(stderr)
            compressed_len = len(compressed)
            if compressed_len < original_len:
                saving = round((1 - compressed_len / original_len) * 100)
                stderr = compressed + f"\n[token_saver: curl_progress, -{saving}%]"

    if stdout:
        sys.stdout.write(stdout)
        if not stdout.endswith("\n"):
            sys.stdout.write("\n")
    if stderr:
        sys.stderr.write(stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
