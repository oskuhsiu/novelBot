"""Helpers for CLI tools that accept JSON via --json.

`resolve_json_arg(value)` lets callers pass either:
  - inline JSON string:  --json '{"a":1}'
  - path reference:      --json @/tmp/payload.json  (curl/gh convention)

Using the @file form avoids embedding complex JSON in bash commands,
which is required by CLAUDE.md rules (no $(), backticks, complex
brace expansion in inline args).
"""
from pathlib import Path


def resolve_json_arg(value: str) -> str:
    """Return the JSON text, reading from file if value starts with '@'.

    Raises FileNotFoundError if the path does not exist.
    """
    if value is None:
        return value
    if value.startswith("@"):
        path = Path(value[1:])
        return path.read_text(encoding="utf-8")
    return value
