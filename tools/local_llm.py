#!/usr/bin/env python3
"""
local_llm.py — 本地 LLM API 閘道 (OpenAI-compatible)

用法:
  # 審查模式：讀取 assist_input 檔 + 引用檔案，送出審查請求
  python tools/local_llm.py review --input /path/to/assist_input.md --output /path/to/review.md

  # 生成模式：從 prompt 檔或 stdin 生成內容
  python tools/local_llm.py generate --prompt-file /path/to/prompt.md --output /path/to/output.md
  python tools/local_llm.py generate --prompt "寫一段打鬥場景" --output /path/to/output.md

  # 直接對話（結果印到 stdout）
  python tools/local_llm.py chat --system "你是小說作家" --prompt "寫一段對話"

  # 測試連線
  python tools/local_llm.py ping

環境變數:
  LOCAL_LLM_URL   API base URL (預設: http://localhost:8000)，自動附加 /v1/chat/completions
  LOCAL_LLM_MODEL 模型名稱 (預設: Qwen3.5-9B)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

# ── 預設值 ──────────────────────────────────────────────
API_PATH = "/v1/chat/completions"
DEFAULT_URL = os.environ.get(
    "LOCAL_LLM_URL",
    "http://localhost:8000",
)
DEFAULT_MODEL = os.environ.get("LOCAL_LLM_MODEL", "Qwen3.5-9B")
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.6
TIMEOUT_SECONDS = 300  # 5 分鐘，本地模型可能較慢


# ── 工具函式 ─────────────────────────────────────────────
def call_api(messages, *, url=DEFAULT_URL, model=DEFAULT_MODEL,
             max_tokens=DEFAULT_MAX_TOKENS, temperature=DEFAULT_TEMPERATURE):
    """呼叫 OpenAI-compatible chat completions API（streaming via curl）"""
    endpoint = url.rstrip("/") + API_PATH
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    })

    t0 = time.time()
    try:
        proc = subprocess.Popen(
            ["curl", "-s", "-S", "--max-time", str(TIMEOUT_SECONDS),
             "-N",  # no-buffer for streaming
             "-H", "Content-Type: application/json",
             "-d", "@-", endpoint],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        proc.stdin.write(payload)
        proc.stdin.close()

        # 逐行讀取 SSE stream
        chunks = []
        usage = {}
        for line in proc.stdout:
            line = line.strip()
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]  # 去掉 "data: "
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content", "")
                if text:
                    chunks.append(text)
                # 最後一個 chunk 可能帶 usage
                if "usage" in chunk:
                    usage = chunk["usage"]
            except json.JSONDecodeError:
                continue

        proc.wait(timeout=10)
        stderr_out = proc.stderr.read()

        if proc.returncode != 0 and not chunks:
            print(f"[ERROR] curl 失敗 (rc={proc.returncode}): {stderr_out.strip()}", file=sys.stderr)
            sys.exit(1)

    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"[ERROR] API 逾時 ({TIMEOUT_SECONDS}s)", file=sys.stderr)
        sys.exit(1)

    if not chunks:
        print("[ERROR] streaming 無回應內容", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - t0
    content = "".join(chunks)

    # 砍掉 Qwen3 的 think 區塊（含有/無 <think> 開始標籤的情況）
    content = re.sub(r"<think>[\s\S]*?</think>\s*", "", content)
    content = re.sub(r"^[\s\S]*?</think>\s*", "", content)
    content = content.strip()

    print(f"[local_llm] model={model} elapsed={elapsed:.1f}s "
          f"prompt_tokens={usage.get('prompt_tokens', '?')} "
          f"completion_tokens={usage.get('completion_tokens', '?')}",
          file=sys.stderr)

    return content


def read_file(path):
    """讀取檔案，回傳內容字串"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_output(content, output_path=None):
    """寫入檔案或印到 stdout"""
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[local_llm] 已寫入: {output_path}", file=sys.stderr)
    else:
        print(content)


def resolve_files_from_assist_input(input_text):
    """
    從 assist_input.md 解析「請讀取以下檔案」區段中的路徑，
    讀取每個檔案內容，組裝成完整 prompt。
    """
    sections = []
    sections.append(input_text)

    # 找出所有 "- xxx：/path/to/file" 格式的路徑
    path_pattern = re.compile(r"[-–]\s*[^：:]*[：:]\s*(/\S+)")
    paths_found = path_pattern.findall(input_text)

    for p in paths_found:
        p = p.strip()
        if os.path.isfile(p):
            sections.append(f"\n\n--- 檔案: {os.path.basename(p)} ---\n")
            sections.append(read_file(p))
        else:
            sections.append(f"\n\n--- 檔案: {p} (不存在，跳過) ---\n")

    return "\n".join(sections)


# ── 子命令 ───────────────────────────────────────────────
def cmd_review(args):
    """審查模式：讀取 assist_input，解析引用檔案，送出審查"""
    input_text = read_file(args.input)
    full_prompt = resolve_files_from_assist_input(input_text)

    messages = [
        {"role": "system", "content": (
            "/no_think\n你是繁體中文小說審查助手。仔細閱讀所有素材，"
            "找出情節矛盾、吃書、資訊邊界違反、能力不合法、錯字等問題。"
            "對每個發現列出：嚴重度(Critical/Warning/Minor)、章節號、"
            "問題描述、原文引用、建議修正。只列有把握的問題，不確定標 [不確定]。"
        )},
        {"role": "user", "content": full_prompt},
    ]

    result = call_api(messages, max_tokens=args.max_tokens,
                      temperature=args.temperature)
    write_output(result, args.output)


def cmd_generate(args):
    """生成模式：從 prompt 生成內容"""
    if args.prompt_file:
        user_prompt = read_file(args.prompt_file)
    elif args.prompt:
        user_prompt = args.prompt
    else:
        user_prompt = sys.stdin.read()

    system = args.system or "你是一位繁體中文網路小說作家，擅長寫出生動、有張力的場景。"
    system = "/no_think\n" + system

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]

    result = call_api(messages, max_tokens=args.max_tokens,
                      temperature=args.temperature)
    write_output(result, args.output)


def cmd_chat(args):
    """直接對話，結果印到 stdout"""
    system = args.system or "你是一位繁體中文網路小說作家助手。"
    system = "/no_think\n" + system
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": args.prompt},
    ]
    result = call_api(messages, max_tokens=args.max_tokens,
                      temperature=args.temperature)
    print(result)


def cmd_ping(args):
    """測試 API 連線"""
    messages = [{"role": "user", "content": "ping"}]
    try:
        result = call_api(messages, max_tokens=16, temperature=0)
        print(f"OK: {result[:100]}")
    except SystemExit:
        print("FAIL")
        sys.exit(1)


# ── CLI ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="本地 LLM API 閘道")
    parser.add_argument("--url", default=DEFAULT_URL, help="API endpoint URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名稱")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # review
    p_rev = sub.add_parser("review", help="審查模式")
    p_rev.add_argument("--input", required=True, help="assist_input.md 路徑")
    p_rev.add_argument("--output", required=True, help="輸出審查結果路徑")
    p_rev.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p_rev.add_argument("--temperature", type=float, default=0.6)

    # generate
    p_gen = sub.add_parser("generate", help="生成模式")
    p_gen.add_argument("--prompt-file", help="prompt 檔案路徑")
    p_gen.add_argument("--prompt", help="直接輸入 prompt")
    p_gen.add_argument("--system", help="system prompt")
    p_gen.add_argument("--output", help="輸出路徑（不指定則 stdout）")
    p_gen.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p_gen.add_argument("--temperature", type=float, default=0.7)

    # chat
    p_chat = sub.add_parser("chat", help="直接對話")
    p_chat.add_argument("--prompt", required=True, help="對話內容")
    p_chat.add_argument("--system", help="system prompt")
    p_chat.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p_chat.add_argument("--temperature", type=float, default=0.7)

    # ping
    sub.add_parser("ping", help="測試連線")

    args = parser.parse_args()

    # 用 args 覆蓋 call_api 預設（keyword-only 參數用 __kwdefaults__）
    call_api.__kwdefaults__["url"] = args.url
    call_api.__kwdefaults__["model"] = args.model

    dispatch = {"review": cmd_review, "generate": cmd_generate,
                "chat": cmd_chat, "ping": cmd_ping}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
