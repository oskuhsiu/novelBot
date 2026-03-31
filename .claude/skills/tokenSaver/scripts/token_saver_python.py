#!/usr/bin/env python3
"""token_saver_python.py — 壓縮 Python 工具鏈輸出。

處理：pytest, ruff, mypy
參考 rtk 策略：pytest failure-only, ruff 按 rule 分組, mypy 按檔案分組。

用法：.venv/bin/python .claude/skills/tokenSaver/scripts/token_saver_python.py <command...>
"""
import subprocess
import sys
import re
import os


# ── pytest 壓縮器 ──────────────────────────────────────

def compress_pytest(text: str) -> str:
    """只保留 FAILED/ERROR 區塊 + summary，去掉 PASSED 和 progress。

    rtk 策略：state machine parsing, failure focus filtering。
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    result = []
    in_failure_block = False
    in_warnings_block = False
    summary_started = False

    for line in lines:
        # warnings section — 整段跳過
        if re.match(r"^=+ warnings summary =+$", line):
            in_warnings_block = True
            continue
        if in_warnings_block:
            # warnings block 結束於下一個 === 行
            if re.match(r"^=+", line):
                in_warnings_block = False
                # 這可能是 final summary，繼續處理
            else:
                continue

        # final summary 行（= N passed, N failed ... =）永遠保留
        if re.match(r"^=+ .*(\d+ passed|\d+ failed|\d+ error).* =+$", line):
            summary_started = True
            result.append(line)
            continue

        # short test summary info header
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            result.append(line)
            continue

        if "short test summary info" in line:
            summary_started = True
            result.append(line)
            continue

        if summary_started:
            result.append(line)
            continue

        # FAILURES / ERRORS section headers
        if re.match(r"^=+ FAILURES =+$", line) or re.match(r"^=+ ERRORS =+$", line):
            in_failure_block = True
            result.append(line)
            continue

        # Individual test failure header
        if re.match(r"^_+ .+ _+$", line):
            in_failure_block = True
            result.append(line)
            continue

        # 結束 failure block
        if in_failure_block and re.match(r"^=+", line):
            in_failure_block = False
            result.append(line)
            continue

        # failure/error block 內容保留
        if in_failure_block:
            result.append(line)
            continue

        # 去掉 PASSED 行、progress dots、collecting 行
        if "PASSED" in line and "::" in line:
            continue
        if re.match(r"^[\.\ssFExX]+$", line):
            continue
        if line.startswith("collecting ") or line.startswith("collected "):
            continue
        # 去掉 platform/rootdir/plugins 等 session header
        if re.match(r"^(platform|rootdir|plugins|cachedir)[ :]", line):
            continue
        # 去掉 pytest header
        if re.match(r"^=+ test session starts =+$", line):
            continue

    if not result:
        # 全部 pass 時回傳簡短訊息
        # 找 summary 行
        for line in lines:
            if re.match(r"^=+ .*(passed|failed|error).* =+$", line):
                return line
        return "all tests passed"

    return "\n".join(result)


# ── ruff 壓縮器 ────────────────────────────────────────

def compress_ruff(text: str) -> str:
    """按 rule code 分組 ruff 錯誤，標示可自動修正。

    rtk 策略：按 rule 分組而非按檔案。
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    # 解析 ruff 輸出格式：file:line:col: RULE message
    by_rule: dict[str, list] = {}
    other_lines = []
    fixable_count = 0
    total_count = 0

    for line in lines:
        m = re.match(r"^(.+?):(\d+):(\d+): ([A-Z]+\d+) (.+)$", line)
        if m:
            filepath, lineno, col, rule, msg = m.groups()
            total_count += 1
            entry = f"  {filepath}:{lineno} {msg}"
            by_rule.setdefault(rule, []).append(entry)
        elif line.startswith("Found ") and "fixable" in line:
            # "Found N errors (M fixable)"
            fix_m = re.search(r"(\d+) fixable", line)
            if fix_m:
                fixable_count = int(fix_m.group(1))
            other_lines.append(line)
        else:
            stripped = line.strip()
            if stripped:
                other_lines.append(line)

    if not by_rule:
        return text.strip()

    result = []
    for rule in sorted(by_rule.keys()):
        entries = by_rule[rule]
        result.append(f"── {rule} ({len(entries)})")
        for e in entries:
            result.append(e)

    if other_lines:
        result.append("")
        result.extend(other_lines)

    return "\n".join(result)


# ── mypy 壓縮器 ────────────────────────────────────────

def compress_mypy(text: str) -> str:
    """按檔案分組 mypy 錯誤，去重複路徑前綴。

    rtk 策略：按檔案分組 + compact line notation。
    """
    lines = text.strip().splitlines()
    if not lines:
        return text

    # 解析 mypy 輸出：file:line: severity: message
    by_file: dict[str, list] = {}
    summary_lines = []

    for line in lines:
        m = re.match(r"^(.+?):(\d+): (error|warning|note): (.+)$", line)
        if m:
            filepath, lineno, severity, msg = m.groups()
            marker = {"error": "E", "warning": "W", "note": "N"}.get(severity, "?")
            by_file.setdefault(filepath, []).append(f"  {lineno}: [{marker}] {msg}")
        elif line.startswith("Found ") or line.startswith("Success"):
            summary_lines.append(line)
        elif line.strip():
            # 可能是多行錯誤的續行
            summary_lines.append(line)

    if not by_file:
        return text.strip()

    result = []
    for filepath in sorted(by_file.keys()):
        entries = by_file[filepath]
        result.append(f"── {filepath} ({len(entries)})")
        result.extend(entries)

    if summary_lines:
        result.append("")
        result.extend(summary_lines)

    return "\n".join(result)


# ── 命令分類 ──────────────────────────────────────────

def classify_command(cmd: str) -> str | None:
    stripped = re.sub(r"^(cd\s+[^;&|]+\s*&&\s*)", "", cmd.strip())
    stripped = re.sub(r"^([A-Z_]+=\S+\s+)+", "", stripped)
    stripped = re.split(r"[;|]", stripped)[0].strip()

    tokens = stripped.split()
    if not tokens:
        return None

    base = os.path.basename(tokens[0])

    # pytest 可能透過 python -m pytest 呼叫
    if base == "pytest" or (base in ("python", "python3") and "-m pytest" in stripped):
        return "pytest"
    if base == "ruff":
        return "ruff"
    if base == "mypy":
        return "mypy"

    return None


COMPRESSORS = {
    "pytest": compress_pytest,
    "ruff": compress_ruff,
    "mypy": compress_mypy,
}


# ── Main ──────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: token_saver_python.py <command...>", file=sys.stderr)
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    kind = classify_command(cmd)

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=os.environ.get("ORIGINAL_CWD", None),
    )

    stdout = result.stdout
    stderr = result.stderr

    # pytest 輸出可能在 stdout 或 stderr
    output = stdout or ""
    if kind == "pytest" and stderr and not stdout:
        output = stderr
        stderr = ""

    if kind and output:
        original_len = len(output)
        compressed = COMPRESSORS[kind](output)
        compressed_len = len(compressed)
        if compressed_len < original_len:
            saving = round((1 - compressed_len / original_len) * 100)
            output = compressed + f"\n[token_saver: {kind}, -{saving}%]"

    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    if stderr:
        sys.stderr.write(stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
