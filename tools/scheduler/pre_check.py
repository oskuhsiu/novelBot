#!/usr/bin/env python3
"""Pre-phase check for nvScheduler: pause flag + 5h rate-limit usage.

Reads:
    $TMPDIR/claude_scheduler_<proj>.pause  (pause flag file)
    $TMPDIR/claude_rate_limits.json        (rate limits snapshot, may be missing)

Outputs a single JSON line:
    {"paused": bool, "usage": float | null}

Usage:
    pre_check.py --proj <alias>
"""
import argparse
import json
import os
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description="nvScheduler pre-phase check")
    parser.add_argument("--proj", required=True, help="Project alias")
    args = parser.parse_args()

    tmp = tempfile.gettempdir()
    pause_path = os.path.join(tmp, f"claude_scheduler_{args.proj}.pause")
    rate_path = os.path.join(tmp, "claude_rate_limits.json")

    result = {"paused": os.path.isfile(pause_path), "usage": None}
    if os.path.isfile(rate_path):
        try:
            with open(rate_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            result["usage"] = d.get("five_hour", {}).get("used_percentage")
        except (OSError, json.JSONDecodeError):
            pass
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
