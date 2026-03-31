#!/usr/bin/env python3
"""
Agent log analyzer — 分析 Claude Code agent JSONL log 的 token 消耗。

用法:
  .venv/bin/python tools/analyze_log.py <logfile.jsonl>
  .venv/bin/python tools/analyze_log.py <logfile.jsonl> --top 20
  .venv/bin/python tools/analyze_log.py <logfile.jsonl> --detail
  .venv/bin/python tools/analyze_log.py <logfile.jsonl> --turns
"""
import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def parse_args():
    p = argparse.ArgumentParser(description="Analyze agent JSONL log token usage")
    p.add_argument("logfile", help="Path to .jsonl log file")
    p.add_argument("--top", type=int, default=10, help="Show top N entries per section (default: 10)")
    p.add_argument("--detail", action="store_true", help="Show per-turn detail table")
    p.add_argument("--turns", action="store_true", help="Show every turn with tool calls and token usage")
    return p.parse_args()


def load_records(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_turns(records):
    """
    Pair each assistant message with the following user message(s) containing tool_results.
    A 'turn' = one API call (assistant response) + its tool results.
    """
    turns = []
    for i, rec in enumerate(records):
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message", {})
        usage = msg.get("usage", {})
        content = msg.get("content", [])

        # Extract tool calls from this assistant message
        tool_calls = []
        text_blocks = []
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    tc = {
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}),
                    }
                    tool_calls.append(tc)
                elif block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))

        # Collect tool results from subsequent user messages
        tool_results = []
        for j in range(i + 1, len(records)):
            nrec = records[j]
            if nrec.get("type") == "assistant":
                break
            if nrec.get("type") == "user":
                ncontent = nrec.get("message", {}).get("content", [])
                if isinstance(ncontent, list):
                    for block in ncontent:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            result_content = block.get("content", "")
                            result_len = len(result_content) if isinstance(result_content, str) else sum(
                                len(json.dumps(b)) for b in result_content
                            ) if isinstance(result_content, list) else 0
                            tool_results.append({
                                "tool_use_id": block.get("tool_use_id", ""),
                                "content_len": result_len,
                                "is_error": block.get("is_error", False),
                            })

        # Match tool_results back to tool_calls by id
        result_map = {r["tool_use_id"]: r for r in tool_results}
        for tc in tool_calls:
            matched = result_map.get(tc["id"], {})
            tc["result_len"] = matched.get("content_len", 0)
            tc["is_error"] = matched.get("is_error", False)

        turn = {
            "index": i,
            "timestamp": rec.get("timestamp", ""),
            "model": msg.get("model", ""),
            "stop_reason": msg.get("stop_reason", ""),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation": usage.get("cache_creation_input_tokens", 0),
            "cache_read": usage.get("cache_read_input_tokens", 0),
            "tool_calls": tool_calls,
            "text_len": sum(len(t) for t in text_blocks),
        }
        turns.append(turn)

    return turns


def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def print_summary(turns, top_n):
    total_input = sum(t["input_tokens"] for t in turns)
    total_output = sum(t["output_tokens"] for t in turns)
    total_cache_create = sum(t["cache_creation"] for t in turns)
    total_cache_read = sum(t["cache_read"] for t in turns)
    total_api_calls = len(turns)

    # Cost estimation (Opus pricing: $15/M input, $75/M output, cache write $18.75/M, cache read $1.5/M)
    cost_input = total_input * 15 / 1_000_000
    cost_output = total_output * 75 / 1_000_000
    cost_cache_w = total_cache_create * 18.75 / 1_000_000
    cost_cache_r = total_cache_read * 1.5 / 1_000_000
    cost_total = cost_input + cost_output + cost_cache_w + cost_cache_r

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  API calls:         {total_api_calls}")
    print(f"  Input tokens:      {fmt_num(total_input)}")
    print(f"  Output tokens:     {fmt_num(total_output)}")
    print(f"  Cache write:       {fmt_num(total_cache_create)}")
    print(f"  Cache read:        {fmt_num(total_cache_read)}")
    print(f"  Est. cost (Opus):  ${cost_total:.2f}")
    print(f"    input:  ${cost_input:.2f}  output: ${cost_output:.2f}")
    print(f"    cache_w: ${cost_cache_w:.2f}  cache_r: ${cost_cache_r:.2f}")
    if turns:
        t0 = turns[0].get("timestamp", "")
        t1 = turns[-1].get("timestamp", "")
        if t0 and t1:
            print(f"  Time span:         {t0} → {t1}")

    # --- By tool ---
    print()
    print("=" * 70)
    print("TOKEN USAGE BY TOOL")
    print("=" * 70)
    tool_stats = defaultdict(lambda: {"calls": 0, "output_tokens": 0, "result_chars": 0, "errors": 0})
    no_tool_output = 0
    for turn in turns:
        if not turn["tool_calls"]:
            no_tool_output += turn["output_tokens"]
        for tc in turn["tool_calls"]:
            name = tc["name"]
            tool_stats[name]["calls"] += 1
            tool_stats[name]["result_chars"] += tc.get("result_len", 0)
            if tc.get("is_error"):
                tool_stats[name]["errors"] += 1

    # Output tokens are per-turn, not per-tool. Attribute proportionally.
    for turn in turns:
        n_tools = len(turn["tool_calls"])
        if n_tools > 0:
            per_tool = turn["output_tokens"] / n_tools
            for tc in turn["tool_calls"]:
                tool_stats[tc["name"]]["output_tokens"] += int(per_tool)

    sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]["calls"], reverse=True)
    print(f"  {'Tool':<20} {'Calls':>6} {'OutTok':>8} {'ResultChars':>12} {'Errors':>6}")
    print(f"  {'-'*20} {'-'*6} {'-'*8} {'-'*12} {'-'*6}")
    for name, s in sorted_tools:
        print(f"  {name:<20} {s['calls']:>6} {fmt_num(s['output_tokens']):>8} {fmt_num(s['result_chars']):>12} {s['errors']:>6}")
    if no_tool_output:
        print(f"  {'(text-only turns)':<20} {'':>6} {fmt_num(no_tool_output):>8}")

    # --- Costliest turns ---
    print()
    print("=" * 70)
    print(f"TOP {top_n} COSTLIEST TURNS (by input tokens)")
    print("=" * 70)
    by_input = sorted(turns, key=lambda t: t["input_tokens"], reverse=True)[:top_n]
    print(f"  {'#':>3} {'Input':>8} {'Output':>8} {'CacheW':>8} {'CacheR':>8} {'Tools'}")
    print(f"  {'-'*3} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*30}")
    for t in by_input:
        tools = ", ".join(tc["name"] for tc in t["tool_calls"]) or "(text)"
        print(f"  {t['index']:>3} {fmt_num(t['input_tokens']):>8} {fmt_num(t['output_tokens']):>8} "
              f"{fmt_num(t['cache_creation']):>8} {fmt_num(t['cache_read']):>8} {tools}")

    # --- Costliest turns by output ---
    print()
    print("=" * 70)
    print(f"TOP {top_n} COSTLIEST TURNS (by output tokens)")
    print("=" * 70)
    by_output = sorted(turns, key=lambda t: t["output_tokens"], reverse=True)[:top_n]
    print(f"  {'#':>3} {'Output':>8} {'Input':>8} {'Tools'}")
    print(f"  {'-'*3} {'-'*8} {'-'*8} {'-'*30}")
    for t in by_output:
        tools = ", ".join(tc["name"] for tc in t["tool_calls"]) or "(text)"
        print(f"  {t['index']:>3} {fmt_num(t['output_tokens']):>8} {fmt_num(t['input_tokens']):>8} {tools}")

    # --- Largest tool results ---
    print()
    print("=" * 70)
    print(f"TOP {top_n} LARGEST TOOL RESULTS (by result chars)")
    print("=" * 70)
    all_results = []
    for turn in turns:
        for tc in turn["tool_calls"]:
            all_results.append({
                "turn": turn["index"],
                "name": tc["name"],
                "result_len": tc.get("result_len", 0),
                "input_preview": _input_preview(tc),
            })
    all_results.sort(key=lambda x: x["result_len"], reverse=True)
    print(f"  {'Turn':>4} {'Tool':<15} {'ResultChars':>12} {'Input preview'}")
    print(f"  {'-'*4} {'-'*15} {'-'*12} {'-'*40}")
    for r in all_results[:top_n]:
        print(f"  {r['turn']:>4} {r['name']:<15} {fmt_num(r['result_len']):>12} {r['input_preview']}")

    # --- Input token growth ---
    print()
    print("=" * 70)
    print("INPUT TOKEN GROWTH (context window usage over turns)")
    print("=" * 70)
    step = max(1, len(turns) // 20)
    print(f"  {'Turn':>4} {'Input':>8} {'CacheR':>8} {'Bar'}")
    max_input = max((t["input_tokens"] for t in turns), default=1)
    for i, t in enumerate(turns):
        if i % step == 0 or i == len(turns) - 1:
            bar_len = int(40 * t["input_tokens"] / max_input) if max_input else 0
            bar = "█" * bar_len
            print(f"  {i:>4} {fmt_num(t['input_tokens']):>8} {fmt_num(t['cache_read']):>8} {bar}")


def _input_preview(tc):
    inp = tc.get("input", {})
    if tc["name"] == "Read":
        return inp.get("file_path", "")[-50:]
    if tc["name"] == "Write":
        path = inp.get("file_path", "")[-40:]
        clen = len(inp.get("content", ""))
        return f"{path} ({clen} chars)"
    if tc["name"] == "Edit":
        return inp.get("file_path", "")[-50:]
    if tc["name"] == "Bash":
        cmd = inp.get("command", "")
        return cmd[:50]
    if tc["name"] == "Grep":
        return f'/{inp.get("pattern", "")[:30]}/ in {inp.get("path", ".")}'
    if tc["name"] == "Glob":
        return inp.get("pattern", "")[:50]
    if tc["name"] == "Agent":
        return inp.get("description", "")[:50]
    return str(inp)[:50]


def print_turns_detail(turns):
    print()
    print("=" * 70)
    print("ALL TURNS DETAIL")
    print("=" * 70)
    for t in turns:
        tools_str = ", ".join(tc["name"] for tc in t["tool_calls"]) or "(text)"
        print(f"\n  Turn #{t['index']}  [{t.get('timestamp', '')[:19]}]")
        print(f"    Input: {fmt_num(t['input_tokens'])}  Output: {fmt_num(t['output_tokens'])}  "
              f"CacheW: {fmt_num(t['cache_creation'])}  CacheR: {fmt_num(t['cache_read'])}")
        print(f"    Stop: {t['stop_reason']}  TextLen: {t['text_len']}")
        for tc in t["tool_calls"]:
            err = " [ERROR]" if tc.get("is_error") else ""
            preview = _input_preview(tc)
            print(f"    → {tc['name']:<15} result={fmt_num(tc.get('result_len', 0)):>8} chars{err}  {preview}")


def main():
    args = parse_args()
    records = load_records(args.logfile)
    turns = extract_turns(records)
    print_summary(turns, args.top)
    if args.detail or args.turns:
        print_turns_detail(turns)


if __name__ == "__main__":
    main()
