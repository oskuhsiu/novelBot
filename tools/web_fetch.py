#!/usr/bin/env python3
"""
web_fetch.py — curl_cffi 封裝，繞過 Cloudflare 防護抓取網頁內容

用法:
  # 抓取單頁
  python tools/web_fetch.py fetch "https://tw.hjwzw.com/Book/Read/36308,12703012"

  # 測試來源站可用性
  python tools/web_fetch.py test-sites

  # 抓取並只輸出正文（去 HTML tag）
  python tools/web_fetch.py fetch --text-only "https://example.com/chapter/1"
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """從 HTML 中提取純文字"""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "head"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self._text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self):
        return "".join(self._text)


def html_to_text(html: str) -> str:
    """將 HTML 轉為純文字"""
    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    # 清理多餘空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_url(url: str, timeout: int = 30) -> dict:
    """
    使用 curl_cffi 抓取 URL，回傳 dict:
    {
        "ok": bool,
        "status_code": int,
        "html": str,       # 原始 HTML
        "text": str,        # 純文字（去 HTML tag）
        "url": str,
        "error": str | None
    }
    """
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        return {
            "ok": False,
            "status_code": 0,
            "html": "",
            "text": "",
            "url": url,
            "error": "curl_cffi not installed. Run: pip install curl_cffi",
        }

    try:
        resp = cffi_requests.get(
            url,
            impersonate="chrome",
            timeout=timeout,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            },
        )
        html = resp.text
        return {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code,
            "html": html,
            "text": html_to_text(html),
            "url": url,
            "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}",
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": 0,
            "html": "",
            "text": "",
            "url": url,
            "error": str(e),
        }


# 初始候選來源站
CANDIDATE_SITES = [
    {"name": "黃金屋", "url": "https://tw.hjwzw.com", "test_path": "/"},
    {"name": "全本小說網", "url": "https://big5.quanben-xiaoshuo.com", "test_path": "/"},
    {"name": "巴哈姆特", "url": "https://home.gamer.com.tw", "test_path": "/"},
    {"name": "czbooks", "url": "https://czbooks.net", "test_path": "/"},
]


def test_sites() -> list[dict]:
    """測試所有候選來源站的可用性"""
    results = []
    for site in CANDIDATE_SITES:
        url = site["url"] + site["test_path"]
        result = fetch_url(url, timeout=15)
        status = "ok" if result["ok"] else "fail"
        # 檢查是否被 Cloudflare 擋
        if result["ok"] and "cf-browser-verification" in result["html"].lower():
            status = "cloudflare"
        results.append({
            "name": site["name"],
            "url": site["url"],
            "status": status,
            "status_code": result["status_code"],
            "error": result["error"],
        })
    return results


# ── CLI ──

def cmd_fetch(args):
    result = fetch_url(args.url, timeout=args.timeout)
    if args.text_only:
        if result["ok"]:
            print(result["text"])
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_test_sites(args):
    results = test_sites()
    for r in results:
        icon = "ok" if r["status"] == "ok" else "CF" if r["status"] == "cloudflare" else "xx"
        print(f"  [{icon}] {r['name']:12s} {r['url']:40s} {r.get('error', '') or ''}")


def main():
    parser = argparse.ArgumentParser(description="web_fetch — curl_cffi wrapper")
    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser("fetch", help="Fetch a URL")
    p_fetch.add_argument("url", help="URL to fetch")
    p_fetch.add_argument("--text-only", action="store_true", help="Output plain text only")
    p_fetch.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")

    sub.add_parser("test-sites", help="Test candidate source sites")

    args = parser.parse_args()
    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "test-sites":
        cmd_test_sites(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
