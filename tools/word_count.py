#!/usr/bin/env python3
"""word_count.py — 計算中文章節的準確字數（中文字＋中文標點＋英數單詞）

規則：
- 中文字 (U+4E00–U+9FFF, U+3400–U+4DBF)：每字算 1
- 中文標點（全形標點）：每個算 1
- 英數單詞（連續 a-z/A-Z/0-9）：整串算 1
- Markdown 語法、空白、換行：不計入

用法：
    .venv/bin/python tools/word_count.py <file> [<file> ...]

單檔輸出：純數字
多檔輸出：每行 `<count>\t<file>`，最後一行 `<total>\tTOTAL`
"""
import re
import sys

CN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
PN_RE = re.compile(r"[\u3000-\u303f\uff01-\uff60\u2018-\u201f\u2014\u2026\uff5e]")
EN_RE = re.compile(r"[a-zA-Z0-9]+")


def count_text(text: str) -> int:
    return len(CN_RE.findall(text)) + len(PN_RE.findall(text)) + len(EN_RE.findall(text))


def count_file(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return count_text(f.read())


HELP_TEXT = """word_count.py — 中文章節字數統計

用法：
    .venv/bin/python tools/word_count.py <file> [<file> ...]

規則：
    - 中文字 (U+4E00–U+9FFF, U+3400–U+4DBF)：每字算 1
    - 中文標點（全形標點）：每個算 1
    - 英數單詞（連續 a-z/A-Z/0-9）：整串算 1
    - Markdown 語法、空白、換行：不計入

輸出：
    - 單檔：純數字
    - 多檔：每行 `<count>\\t<file>`，最後一行 `<total>\\tTOTAL`

選項：
    -h, --help    顯示此說明並結束
"""


def main(argv):
    if len(argv) < 2:
        print("usage: word_count.py <file> [<file> ...]", file=sys.stderr)
        return 2
    if argv[1] in ("-h", "--help"):
        print(HELP_TEXT)
        return 0
    files = argv[1:]
    if len(files) == 1:
        print(count_file(files[0]))
        return 0
    total = 0
    for p in files:
        n = count_file(p)
        total += n
        print(f"{n}\t{p}")
    print(f"{total}\tTOTAL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
