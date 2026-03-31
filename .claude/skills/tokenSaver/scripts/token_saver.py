#!/usr/bin/env python3
"""token_saver.py — 壓縮常見 CLI 輸出，節省 LLM token。

原則：去除 LLM 不需要的格式噪音（permissions、timestamp、owner、
diff headers、context lines）。grep 截短 >200 字元行，diff 去 context lines。

用法：.venv/bin/python .claude/skills/tokenSaver/scripts/token_saver.py <command...>
"""
import subprocess
import sys
import re
import os

# 噪音目錄 — find/ls 時可安全摺疊
NOISE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "target", "dist", "build", ".next", ".nuxt",
    ".egg-info", "*.egg-info", ".DS_Store",
}


# ── ls 壓縮器 ──────────────────────────────────────────

def compress_ls(text: str) -> str:
    """去除 permissions/owner/group/timestamp，只留檔名+大小+目錄標記。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    # ls -R 格式
    if any(l.endswith(":") and "/" in l for l in lines):
        return _compress_ls_recursive(lines)

    result = []
    for line in lines:
        compressed = _compress_ls_line(line)
        if compressed is not None:
            result.append(compressed)

    if not result:
        return text
    return "\n".join(result)


def _compress_ls_line(line: str) -> str | None:
    """解析 ls -l 的一行，去掉 metadata，保留檔名+大小。"""
    # 跳過 "total NNN" 行
    if line.startswith("total "):
        return None
    # 跳過 . 和 .. 目錄
    if re.match(r"^[dlrwxst@\+\-\.]+\s+.*\s+\.\.?$", line):
        return None

    # ls -l 格式: permissions links owner group size month day time name
    m = re.match(
        r"^([drwxlst@\+\-\.]+)\s+"  # permissions (incl. ACL +)
        r"\d+\s+"                  # links
        r"\S+\s+"                  # owner
        r"\S+\s+"                  # group
        r"(\d+)\s+"               # size
        r"\w+\s+\d+\s+[\d:]+\s+" # timestamp
        r"(.+)$",                  # name
        line,
    )
    if m:
        perms, size_str, name = m.group(1), int(m.group(2)), m.group(3)
        size_h = _human_size(size_str)
        is_dir = perms.startswith("d")
        suffix = "/" if is_dir else ""
        # 目錄不顯示大小
        if is_dir:
            return f"{name}{suffix}"
        return f"{name}{suffix}\t{size_h}"

    # 非 ls -l 格式（普通 ls），原樣保留
    return line


def _human_size(n: int) -> str:
    """bytes → human readable"""
    if n < 1024:
        return f"{n}B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f}K"
    elif n < 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}M"
    return f"{n / 1024 / 1024 / 1024:.1f}G"


def _compress_ls_recursive(lines: list) -> str:
    """ls -R：對每個目錄區塊做壓縮。"""
    groups = []
    current_dir = ""
    current_files = []
    for line in lines:
        if line.endswith(":"):
            if current_dir:
                groups.append((current_dir, current_files))
            current_dir = line
            current_files = []
        elif line.strip() and line.strip() not in (".", ".."):
            current_files.append(line)
    if current_dir:
        groups.append((current_dir, current_files))

    parts = []
    for dir_name, files in groups:
        # 跳過噪音目錄的內容，只顯示目錄名 + 計數
        base = dir_name.rstrip(":").split("/")[-1]
        if base in NOISE_DIRS:
            parts.append(f"{dir_name} ({len(files)} items, skipped)")
            continue
        parts.append(dir_name)
        for f in files:
            compressed = _compress_ls_line(f)
            if compressed is not None:
                parts.append(compressed)
    return "\n".join(parts)


# ── find 壓縮器 ────────────────────────────────────────

def compress_find(text: str) -> str:
    """平面路徑列表 → 樹狀分組，過濾噪音目錄。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    # 過濾噪音目錄（整棵子樹摺疊成一行計數）
    clean = []
    noise_counts: dict[str, int] = {}
    for line in lines:
        parts = line.strip().split("/")
        # 檢查路徑中是否包含噪音目錄
        noise_hit = None
        for i, p in enumerate(parts):
            if p in NOISE_DIRS:
                noise_hit = "/".join(parts[: i + 1])
                break
        if noise_hit:
            noise_counts[noise_hit] = noise_counts.get(noise_hit, 0) + 1
        else:
            clean.append(line)

    # 按父目錄分組
    groups: dict[str, list] = {}
    for line in clean:
        parent = "/".join(line.strip().rsplit("/", 1)[:-1]) or "."
        fname = line.strip().rsplit("/", 1)[-1]
        groups.setdefault(parent, []).append(fname)

    result = []
    for parent in sorted(groups.keys()):
        files = groups[parent]
        result.append(f"{parent}/")
        for f in sorted(files):
            result.append(f"  {f}")

    # 噪音目錄摘要
    if noise_counts:
        result.append("")
        for d, cnt in sorted(noise_counts.items()):
            result.append(f"({d}/ — {cnt} files, filtered)")

    # 統計摘要
    ext_counts: dict[str, int] = {}
    for line in clean:
        ext = os.path.splitext(line)[-1]
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
    if ext_counts:
        top = sorted(ext_counts.items(), key=lambda x: -x[1])[:8]
        ext_str = " ".join(f"{e}({c})" for e, c in top)
        result.append(f"\n{len(clean)} files | {ext_str}")

    return "\n".join(result)


# ── grep/rg 壓縮器 ─────────────────────────────────────

def compress_grep(text: str) -> str:
    """按檔案分組，去前導空白，截短過長行。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    MAX_LINE_LEN = 200  # 單行最長字元

    groups: dict[str, list] = {}
    ungrouped = []

    for line in lines:
        # file:linenum:content 或 file:linenum-content
        m = re.match(r"^([^:]+):(\d+)[:：\-](.*)$", line)
        if m:
            filepath, lineno, content = m.group(1), m.group(2), m.group(3)
            # 去前導空白
            content = content.lstrip()
            # 截短過長行（保留頭尾）
            if len(content) > MAX_LINE_LEN:
                half = MAX_LINE_LEN // 2
                content = content[:half] + " ... " + content[-half:]
            groups.setdefault(filepath, []).append(f"{lineno}: {content}")
        else:
            ungrouped.append(line)

    if not groups:
        return text.strip()

    result = []
    for filepath in sorted(groups.keys()):
        matches = groups[filepath]
        result.append(f"── {filepath} ({len(matches)})")
        for m in matches:
            result.append(f"  {m}")

    if ungrouped:
        result.append("")
        result.extend(ungrouped)

    return "\n".join(result)


# ── diff 壓縮器 ────────────────────────────────────────

def compress_diff(text: str) -> str:
    """去 diff metadata/headers/context lines，只留變更行 + hunk 位置。"""
    lines = text.strip().splitlines()
    if not lines:
        return text

    files = _parse_diff_files(lines)
    if not files:
        return text.strip()

    result = []
    total_add = 0
    total_del = 0

    for fname, file_lines in files:
        additions = 0
        deletions = 0
        file_result = []

        for fl in file_lines:
            # 去掉 index, ---, +++ 等 header
            if fl.startswith("index ") or fl.startswith("--- ") or fl.startswith("+++ "):
                continue
            # 去掉 similarity index 行
            if fl.startswith("similarity index "):
                continue
            # 保留 Binary files 通知
            if fl.startswith("Binary files "):
                file_result.append(fl)
                continue
            # 保留 file mode 資訊（new/deleted/old/new mode）
            if re.match(r"^(new|deleted|old) (file )?mode \d+", fl):
                file_result.append(fl)
                continue
            # 保留 rename/copy from/to
            if re.match(r"^(rename|copy) (from|to) ", fl):
                file_result.append(fl)
                continue
            # 保留 "\ No newline at end of file"
            if fl.startswith("\\ "):
                file_result.append(fl)
                continue
            # 保留 hunk header（@@ 行）
            if fl.startswith("@@"):
                file_result.append(fl)
                continue
            # 保留變更行
            if fl.startswith("+"):
                additions += 1
                file_result.append(fl)
            elif fl.startswith("-"):
                deletions += 1
                file_result.append(fl)
            # 去掉 context 行（空格開頭的未變更行）— 這是省 token 的關鍵

        total_add += additions
        total_del += deletions
        result.append(f"── {fname}  +{additions} -{deletions}")
        result.extend(file_result)
        result.append("")

    result.append(f"{len(files)} file(s)  +{total_add} -{total_del}")
    return "\n".join(result)


def _parse_diff_files(lines: list) -> list:
    """解析 unified diff 為 [(filename, [lines]), ...]"""
    files = []
    current_name = None
    current_lines = []

    for line in lines:
        if line.startswith("diff --git") or line.startswith("diff "):
            if current_name:
                files.append((current_name, current_lines))
            m = re.search(r"b/(.+)$", line)
            current_name = m.group(1) if m else line
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name:
        files.append((current_name, current_lines))
    return files



# ── 命令分類 ──────────────────────────────────────────

def classify_command(cmd: str) -> str | None:
    """判斷命令類型，回傳對應壓縮器名稱。"""
    stripped = re.sub(r"^(cd\s+[^;&|]+\s*&&\s*)", "", cmd.strip())
    stripped = re.sub(r"^([A-Z_]+=\S+\s+)+", "", stripped)
    # 只看第一個命令（分號/pipe 前）
    stripped = re.split(r"[;|]", stripped)[0].strip()

    tokens = stripped.split()
    if not tokens:
        return None

    base = os.path.basename(tokens[0])

    if base in ("ls", "exa", "eza"):
        return "ls"
    if base == "find":
        return "find"
    if base in ("grep", "rg", "ripgrep"):
        return "grep"
    if base == "git" and len(tokens) > 1 and tokens[1] == "diff":
        return "diff"
    if base == "diff":
        return "diff"

    return None


COMPRESSORS = {
    "ls": compress_ls,
    "find": compress_find,
    "grep": compress_grep,
    "diff": compress_diff,
}


# ── Main ──────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: token_saver.py <command...>", file=sys.stderr)
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    kind = classify_command(cmd)

    # 執行原始命令
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=os.environ.get("ORIGINAL_CWD", None),
    )

    stdout = result.stdout
    stderr = result.stderr

    # 壓縮 stdout
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
