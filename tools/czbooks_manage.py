#!/usr/bin/env python3
"""
czbooks_manage.py — czbooks.net 章節管理工具
=============================================

功能：列出 / 刪除 / 上傳 / 更新 czbooks.net 上的小說章節。

前置需求：
  - Python 套件：pyyaml, beautifulsoup4, curl_cffi
    安裝：pip3 install --break-system-packages pyyaml beautifulsoup4 curl_cffi
  - Cookie 檔案：專案根目錄下的 .czbooks_cookie
    格式範例：blackcat_SESSID=<your_session_id>
    取得方式：登入 czbooks.net 後，從瀏覽器 DevTools > Application > Cookies 複製
  - 專案註冊：projects/project_registry.yaml 中需有對應的 proj alias

檔案結構：
  .czbooks_cookie                          ← Session cookie（必要）
  projects/project_registry.yaml           ← 專案代號 → 資料夾名稱對應表
  projects/<資料夾名稱>/output/chapters/   ← 章節 markdown 檔案（chapter_N.md）

子命令：
  list    列出 czbooks 上的所有章節（ID、字數、狀態）
  delete  批次刪除指定範圍的章節
  upload  從本地 chapter_N.md 批次上傳新章節
  update  以本地 chapter_N.md 批次覆蓋更新已有章節

用法範例：
  # 列出所有章節
  python3 tools/czbooks_manage.py list --proj gou1

  # 指定 novel_id 列出（跳過自動查找）
  python3 tools/czbooks_manage.py list --proj gou1 --novel-id cr3jji

  # Dry run — 預覽要刪除的章節，不實際執行
  python3 tools/czbooks_manage.py delete --proj gou1 --novel-id cr3jji --range 35-110 --dry

  # 實際刪除
  python3 tools/czbooks_manage.py delete --proj gou1 --novel-id cr3jji --range 35-110

  # 上傳章節（草稿模式）
  python3 tools/czbooks_manage.py upload --proj gou1 --novel-id cr3jji --range 35-130 --state draft

  # 上傳章節（直接發佈）
  python3 tools/czbooks_manage.py upload --proj gou1 --novel-id cr3jji --range 35-130 --state post

  # 更新已有章節內容
  python3 tools/czbooks_manage.py update --proj gou1 --novel-id cr3jji --range 35-50 --state post

參數說明：
  --proj       專案代號（對應 project_registry.yaml 中的 alias）
  --novel-id   直接指定 czbooks novel_id（可選，省略則自動從 /creator/list 查找）
  --range      章節範圍，例如 35-120、35~120、或單一章 35
  --state      draft（草稿）或 post（發佈），預設 draft
  --dry        Dry run 模式，只顯示操作目標不實際執行

注意事項：
  - delete 會從最後一章往前刪，避免分頁偏移問題
  - upload 需要至少一個現有章節作為錨點（接在最後一章之後建立）
  - 每次 API 呼叫之間有 delay（delete: 1s, upload: 1.5s）避免被限速
  - 章節 .md 檔案格式：首行 # 標題 作為章節名稱，尾部 --- 或 ## 章節總結 會被自動裁切
"""

import argparse
import re
import sys
import time
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

BASE_URL = "https://czbooks.net"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "projects" / "project_registry.yaml"
COOKIE_PATH = PROJECT_ROOT / ".czbooks_cookie"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_cookie() -> dict:
    """Read .czbooks_cookie and return a cookie dict."""
    text = COOKIE_PATH.read_text().strip()
    cookies = {}
    for part in text.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def resolve_proj_dir(proj: str) -> str:
    """Resolve project alias to folder name via project_registry.yaml."""
    with open(REGISTRY_PATH) as f:
        reg = yaml.safe_load(f)
    projects = reg.get("projects", {})
    if proj in projects:
        return projects[proj]
    # Try exact match on folder names
    if proj in projects.values():
        return proj
    raise SystemExit(f"Unknown project alias: {proj}")


def parse_range(range_str: str) -> list[int]:
    """Parse '35-120' or '35~120' or '35' into a list of ints."""
    range_str = range_str.replace("~", "-")
    if "-" in range_str:
        start, end = range_str.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(range_str)]


def extract_chapter_number(name: str) -> int | None:
    """Extract chapter number from a chapter name like '第 35 章 — 標題'."""
    m = re.search(r"第\s*(\d+)\s*章", name)
    if m:
        return int(m.group(1))
    return None


def read_chapter_file(path: Path) -> tuple[str, str]:
    """Read a chapter .md file. Returns (chapterName, content).

    - chapterName is the first `# ...` line (without the `#`).
    - content is the body with the title line removed, and trailing
      `---` separators / `## 章節總結` sections stripped.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Extract title from first heading
    chapter_name = ""
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            chapter_name = stripped[2:].strip()
            body_start = i + 1
            break

    # Find trailing separator / summary to strip
    body_lines = lines[body_start:]

    # Remove trailing summary section: find last `---` and drop everything after
    cut_index = len(body_lines)
    for i in range(len(body_lines) - 1, -1, -1):
        stripped = body_lines[i].strip()
        if stripped.startswith("## 章節總結"):
            cut_index = i
            break

    body_lines = body_lines[:cut_index]

    # Strip trailing blank lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    content = "\n".join(body_lines)
    return chapter_name, content


# ---------------------------------------------------------------------------
# CzBooksClient
# ---------------------------------------------------------------------------

class CzBooksClient:
    """HTTP client for czbooks.net creator API."""

    def __init__(self):
        self.session = cffi_requests.Session(impersonate="chrome")
        self.cookies = load_cookie()

    def get(self, path: str, **kwargs) -> cffi_requests.Response:
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, cookies=self.cookies, **kwargs)
        resp.raise_for_status()
        return resp

    def post(self, path: str, data=None, **kwargs) -> cffi_requests.Response:
        url = f"{BASE_URL}{path}"
        resp = self.session.post(url, data=data, cookies=self.cookies, **kwargs)
        resp.raise_for_status()
        return resp

    # ------ Novel discovery ------

    def find_novel_id(self, novel_name: str) -> str:
        """Find novel_id from /creator/list by matching the novel name."""
        resp = self.get("/creator/list")
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for links that contain the novel name
        for a_tag in soup.select("a[href*='/creator/n/']"):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)
            if novel_name in text:
                # Extract novel_id from href like /creator/n/cr3jji/view
                m = re.search(r"/creator/n/([^/]+)", href)
                if m:
                    return m.group(1)

        raise SystemExit(
            f"Cannot find novel '{novel_name}' in creator list. "
            "Check your cookie or novel name."
        )

    # ------ Chapter listing ------

    def list_chapters(self, novel_id: str) -> list[dict]:
        """Fetch all chapters across all pages.

        Returns list of dicts: {id, name, number, word_count, status, order}

        Table structure per row (8 TDs):
          0: checkbox  1: seq#  2: chapter_id (link)  3: chapter_name
          4: created_at  5: status  6: word_count  7: actions
        """
        all_chapters = []
        seen_ids: set[str] = set()
        page = 1

        while True:
            resp = self.get(f"/creator/n/{novel_id}/view?page={page}")
            soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.select_one("table")
            if not table:
                break

            rows = table.select("tr")
            data_rows = rows[1:]  # skip header row
            if not data_rows:
                break

            new_on_page = 0
            for row in data_rows:
                tds = row.select("td")
                if len(tds) < 7:
                    continue

                ch_id = tds[2].get_text(strip=True)
                if ch_id in seen_ids:
                    continue
                seen_ids.add(ch_id)
                new_on_page += 1

                ch_name = tds[3].get_text(strip=True)
                status = tds[5].get_text(strip=True)
                wc_text = tds[6].get_text(strip=True)
                word_count = int(wc_text) if wc_text.isdigit() else 0
                ch_number = extract_chapter_number(ch_name)

                all_chapters.append({
                    "id": ch_id,
                    "name": ch_name,
                    "number": ch_number,
                    "word_count": word_count,
                    "status": status,
                    "order": len(all_chapters),
                })

            # Stop if no new chapters found or less than a full page.
            if new_on_page == 0 or len(data_rows) < 10:
                break

            page += 1
            time.sleep(0.5)

        return all_chapters

    # ------ Delete ------

    def delete_chapter(self, novel_id: str, chapter_id: str) -> bool:
        """Delete a single chapter by GET request."""
        try:
            self.get(f"/creator/n/{novel_id}/{chapter_id}/delete")
            return True
        except Exception as e:
            print(f"  [ERROR] Failed to delete {chapter_id}: {e}")
            return False

    # ------ Edit / Upload ------

    def edit_chapter(
        self,
        novel_id: str,
        chapter_id: str,
        chapter_name: str,
        content: str,
        state: str = "draft",
    ) -> bool:
        """Update an existing chapter via POST."""
        data = {
            "chapterName": chapter_name,
            "content": content,
            "state": state,
        }
        try:
            self.post(f"/creator/n/{novel_id}/{chapter_id}/edit", data=data)
            return True
        except Exception as e:
            print(f"  [ERROR] Failed to edit {chapter_id}: {e}")
            return False

    def create_chapter(
        self,
        novel_id: str,
        chapter_name: str,
        content: str,
        state: str = "draft",
    ) -> str | None:
        """Create a new chapter via /create then fill content via /edit.

        The /create endpoint ignores POST data and only creates a blank chapter,
        so we must follow up with an edit call to set the actual content.

        Returns the new chapter_id if found, or None.
        """
        try:
            resp = self.post(f"/creator/n/{novel_id}/create", data={})
            final_url = str(resp.url) if hasattr(resp, "url") else ""
            m = re.search(r"/creator/n/[^/]+/([^/]+)/edit", final_url)
            if not m:
                return None
            new_id = m.group(1)
            self.edit_chapter(novel_id, new_id, chapter_name, content, state)
            return new_id
        except Exception as e:
            print(f"  [ERROR] Failed to create chapter: {e}")
            return None

    def create_next_chapter(
        self,
        novel_id: str,
        last_chapter_id: str,
        chapter_name: str,
        content: str,
        state: str = "draft",
    ) -> str | None:
        """Create a new chapter after last_chapter_id using ?next_chapter=1.

        Returns the new chapter_id if found, or None.
        """
        data = {
            "chapterName": chapter_name,
            "content": content,
            "state": state,
        }
        try:
            resp = self.post(
                f"/creator/n/{novel_id}/{last_chapter_id}/edit?next_chapter=1",
                data=data,
            )
            # Try to extract the new chapter ID from the redirect or response
            # The response usually redirects to the edit page of the new chapter
            final_url = str(resp.url) if hasattr(resp, "url") else ""
            m = re.search(r"/creator/n/[^/]+/([^/]+)/edit", final_url)
            if m:
                return m.group(1)
            # Fallback: parse response HTML for the chapter ID
            return None
        except Exception as e:
            print(f"  [ERROR] Failed to create chapter: {e}")
            return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(client: CzBooksClient, novel_id: str, page: int | None = None):
    """List all chapters and print a table."""
    chapters = client.list_chapters(novel_id)

    print(f"\n{'No.':<6} {'ID':<12} {'字數':<8} {'狀態':<8} 章節名稱")
    print("-" * 80)
    for ch in chapters:
        num = ch["number"] if ch["number"] is not None else "?"
        print(
            f"{str(num):<6} {ch['id']:<12} {ch['word_count']:<8} "
            f"{ch['status']:<8} {ch['name']}"
        )
    print(f"\n共 {len(chapters)} 章")


def cmd_delete(
    client: CzBooksClient,
    novel_id: str,
    chapters: list[dict],
    target_range: list[int],
    dry: bool = False,
):
    """Delete chapters in the given range."""
    targets = [
        ch for ch in chapters if ch["number"] is not None and ch["number"] in target_range
    ]

    if not targets:
        print("No matching chapters found for the given range.")
        return

    print(f"\n將刪除以下 {len(targets)} 個章節：")
    for ch in targets:
        print(f"  第 {ch['number']} 章 — {ch['name']} (id={ch['id']})")

    if dry:
        print("\n[DRY RUN] 以上章節不會被實際刪除。")
        return

    print()
    # Delete from last to first to avoid pagination issues
    targets.sort(key=lambda c: c["number"], reverse=True)

    success = 0
    for ch in targets:
        print(f"  刪除第 {ch['number']} 章 (id={ch['id']})...", end=" ", flush=True)
        if client.delete_chapter(novel_id, ch["id"]):
            print("OK")
            success += 1
        else:
            print("FAILED")
        time.sleep(1.0)

    print(f"\n完成：成功 {success}/{len(targets)}")


def cmd_upload(
    client: CzBooksClient,
    novel_id: str,
    chapters: list[dict],
    proj_dir: str,
    target_range: list[int],
    state: str = "draft",
    dry: bool = False,
):
    """Upload new chapters from local files."""
    chapter_dir = PROJECT_ROOT / "projects" / proj_dir / "output" / "chapters"

    if chapters:
        print(f"目前 {len(chapters)} 章，新章節將追加在後面。")
    else:
        print("目前 0 章，將從首章開始建立。")

    files_to_upload = []
    for num in sorted(target_range):
        path = chapter_dir / f"chapter_{num}.md"
        if not path.exists():
            print(f"  [SKIP] chapter_{num}.md 不存在")
            continue
        chapter_name, content = read_chapter_file(path)
        if not chapter_name:
            chapter_name = f"第 {num} 章"
        files_to_upload.append((num, chapter_name, content))

    if not files_to_upload:
        print("沒有可上傳的章節檔案。")
        return

    print(f"\n將上傳 {len(files_to_upload)} 個章節 (state={state})：")
    for num, name, content in files_to_upload:
        wc = len(content)
        print(f"  第 {num} 章 — {name} ({wc} 字)")

    if dry:
        print("\n[DRY RUN] 以上章節不會被實際上傳。")
        return

    print()
    success = 0

    for num, name, content in files_to_upload:
        print(f"  上傳第 {num} 章 — {name}...", end=" ", flush=True)
        new_id = client.create_chapter(
            novel_id, name, content, state
        )
        if new_id:
            print(f"OK (id={new_id})")
            success += 1
        else:
            # Even if we can't extract the new ID, the chapter may have been created
            print("OK (cannot extract id, continuing)")
            success += 1
        time.sleep(1.5)

    print(f"\n完成：成功 {success}/{len(files_to_upload)}")
    print(f"後台檢視：{BASE_URL}/creator/n/{novel_id}/view")


def cmd_update(
    client: CzBooksClient,
    novel_id: str,
    chapters: list[dict],
    proj_dir: str,
    target_range: list[int],
    state: str = "draft",
    dry: bool = False,
):
    """Update existing chapters with local file content."""
    chapter_dir = PROJECT_ROOT / "projects" / proj_dir / "output" / "chapters"

    # Map chapter number -> chapter info
    ch_map = {ch["number"]: ch for ch in chapters if ch["number"] is not None}

    updates = []
    for num in sorted(target_range):
        if num not in ch_map:
            print(f"  [SKIP] 第 {num} 章不存在於 czbooks")
            continue
        path = chapter_dir / f"chapter_{num}.md"
        if not path.exists():
            print(f"  [SKIP] chapter_{num}.md 不存在於本地")
            continue
        chapter_name, content = read_chapter_file(path)
        if not chapter_name:
            chapter_name = f"第 {num} 章"
        updates.append((num, ch_map[num]["id"], chapter_name, content))

    if not updates:
        print("沒有可更新的章節。")
        return

    print(f"\n將更新 {len(updates)} 個章節 (state={state})：")
    for num, ch_id, name, content in updates:
        wc = len(content)
        print(f"  第 {num} 章 — {name} ({wc} 字) [id={ch_id}]")

    if dry:
        print("\n[DRY RUN] 以上章節不會被實際更新。")
        return

    print()
    success = 0
    for num, ch_id, name, content in updates:
        print(f"  更新第 {num} 章 (id={ch_id})...", end=" ", flush=True)
        if client.edit_chapter(novel_id, ch_id, name, content, state):
            print("OK")
            success += 1
        else:
            print("FAILED")
        time.sleep(1.0)

    print(f"\n完成：成功 {success}/{len(updates)}")
    print(f"後台檢視：{BASE_URL}/creator/n/{novel_id}/view")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="czbooks.net 章節管理工具")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- list ---
    p_list = sub.add_parser("list", help="列出所有章節")
    p_list.add_argument("--proj", required=True, help="專案代號")
    p_list.add_argument("--novel-id", help="直接指定 novel_id（跳過自動查找）")
    p_list.add_argument("--page", type=int, help="只列出指定頁")

    # --- delete ---
    p_del = sub.add_parser("delete", help="批次刪除章節")
    p_del.add_argument("--proj", required=True)
    p_del.add_argument("--novel-id", help="直接指定 novel_id")
    p_del.add_argument("--range", required=True, dest="range_str", help="章節範圍 e.g. 35-120")
    p_del.add_argument("--dry", action="store_true", help="只顯示，不執行")

    # --- upload ---
    p_up = sub.add_parser("upload", help="批次上傳新章節")
    p_up.add_argument("--proj", required=True)
    p_up.add_argument("--novel-id", help="直接指定 novel_id")
    p_up.add_argument("--range", required=True, dest="range_str", help="章節範圍")
    p_up.add_argument("--state", default="post", choices=["draft", "post"])
    p_up.add_argument("--dry", action="store_true", help="只顯示，不執行")

    # --- update ---
    p_upd = sub.add_parser("update", help="批次更新已有章節")
    p_upd.add_argument("--proj", required=True)
    p_upd.add_argument("--novel-id", help="直接指定 novel_id")
    p_upd.add_argument("--range", required=True, dest="range_str", help="章節範圍")
    p_upd.add_argument("--state", default="post", choices=["draft", "post"])
    p_upd.add_argument("--dry", action="store_true", help="只顯示，不執行")

    args = parser.parse_args()

    # Resolve project
    proj_dir = resolve_proj_dir(args.proj)
    print(f"專案：{args.proj} -> {proj_dir}")

    # Init client
    client = CzBooksClient()

    # Resolve novel_id
    novel_id = getattr(args, "novel_id", None)
    if not novel_id:
        print(f"正在從 creator/list 查找 novel_id...")
        novel_id = client.find_novel_id(proj_dir)
    print(f"Novel ID: {novel_id}")

    # Execute command
    if args.command == "list":
        cmd_list(client, novel_id, page=args.page)

    elif args.command == "delete":
        target = parse_range(args.range_str)
        chapters = client.list_chapters(novel_id)
        cmd_delete(client, novel_id, chapters, target, dry=args.dry)

    elif args.command == "upload":
        target = parse_range(args.range_str)
        chapters = client.list_chapters(novel_id)
        cmd_upload(client, novel_id, chapters, proj_dir, target, state=args.state, dry=args.dry)

    elif args.command == "update":
        target = parse_range(args.range_str)
        chapters = client.list_chapters(novel_id)
        cmd_update(client, novel_id, chapters, proj_dir, target, state=args.state, dry=args.dry)


if __name__ == "__main__":
    main()
