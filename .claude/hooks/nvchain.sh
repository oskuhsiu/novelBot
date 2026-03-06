#!/usr/bin/env bash
# nvChain — PostToolUse hook for automatic nvChapter chaining.
# Triggers after Skill(nvComplete) completes; outputs continuation
# instructions to stderr so Claude reads and follows them.
#
# Claude Code hooks receive JSON on stdin (NOT environment variables).
# PostToolUse hooks must use stderr + exit 2 for Claude to receive output.

set -uo pipefail

# ─── Read JSON from stdin ───
HOOK_INPUT="$(cat)"

# ─── Guard: only fire on Skill tool ───
tool_name="$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_name', ''))
except:
    print('')
" 2>/dev/null || true)"

if [[ "$tool_name" != "Skill" ]]; then
  exit 0
fi

# ─── Guard: only fire on nvComplete skill ───
skill_name="$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    if isinstance(ti, str):
        import json as j2
        ti = j2.loads(ti)
    print(ti.get('skill', ''))
except:
    print('')
" 2>/dev/null || true)"

if [[ "$skill_name" != "nvComplete" ]]; then
  exit 0
fi

# ─── Locate config ───
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="$REPO_ROOT/.claude/hooks/nvchain_config.yaml"

if [[ ! -f "$CONFIG_FILE" ]]; then
  exit 0
fi

# ─── Parse config with awk (no yq dependency) ───
parse_yaml_value() {
  local key="$1"
  local file="$2"
  awk -v k="$key" '
    /^[[:space:]]*#/ { next }
    $0 ~ "^" k ":" {
      sub("^" k ":[[:space:]]*", "", $0)
      gsub(/#.*/, "", $0)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
      gsub(/^"(.*)"$/, "\\1", $0)
      print $0
      exit
    }
  ' "$file" 2>/dev/null || true
}

enabled="$(parse_yaml_value "enabled" "$CONFIG_FILE")"
if [[ "$enabled" != "true" ]]; then
  exit 0
fi

target_chapter="$(parse_yaml_value "target_chapter" "$CONFIG_FILE")"
proj="$(parse_yaml_value "proj" "$CONFIG_FILE")"
direction="$(parse_yaml_value "direction" "$CONFIG_FILE")"
review="$(parse_yaml_value "review" "$CONFIG_FILE")"
compact_on="$(parse_yaml_value "compact_on" "$CONFIG_FILE")"
clean_on="$(parse_yaml_value "clean_on" "$CONFIG_FILE")"

# Defaults
target_chapter="${target_chapter:-999}"
proj="${proj:-eve}"
review="${review:-true}"
compact_on="${compact_on:-5}"
clean_on="${clean_on:-0}"

# ─── Resolve project folder ───
project_folder=""
reg_file="$REPO_ROOT/projects/project_registry.yaml"

if [[ -f "$reg_file" ]]; then
  project_folder="$(awk -v a="$proj" '
    /^[[:space:]]*#/ { next }
    $1 == a ":" {
      $1=""
      sub(/^[[:space:]]+/, "", $0)
      gsub(/"/, "", $0)
      print $0
      exit
    }
  ' "$reg_file" 2>/dev/null || true)"
fi

if [[ -z "$project_folder" ]] && [[ -d "$REPO_ROOT/projects/$proj" ]]; then
  project_folder="$proj"
fi

if [[ -z "$project_folder" ]]; then
  echo "[nvChain] Error: cannot resolve project '$proj'" >&2
  exit 2
fi

# ─── Read current chapter from narrative_progress.yaml ───
progress_file="$REPO_ROOT/projects/$project_folder/config/narrative_progress.yaml"

if [[ ! -f "$progress_file" ]]; then
  echo "[nvChain] Error: missing $progress_file" >&2
  exit 2
fi

# Parse chapters_written (= last completed chapter number)
chapters_written="$(awk '
  BEGIN { in_progress=0 }
  /^[[:space:]]*progress:[[:space:]]*$/ { in_progress=1; next }
  in_progress && /^[^[:space:]]/ { in_progress=0 }
  in_progress && /^[[:space:]]*chapters_written:[[:space:]]*/ {
    sub(/^[[:space:]]*chapters_written:[[:space:]]*/, "", $0)
    gsub(/#.*/, "", $0)
    gsub(/[[:space:]]+$/, "", $0)
    print $0
    exit
  }
' "$progress_file" 2>/dev/null || true)"

# Fallback: current_chapter - 1
if [[ -z "$chapters_written" ]] || ! [[ "$chapters_written" =~ ^[0-9]+$ ]]; then
  current_chapter="$(awk '
    BEGIN { in_progress=0 }
    /^[[:space:]]*progress:[[:space:]]*$/ { in_progress=1; next }
    in_progress && /^[^[:space:]]/ { in_progress=0 }
    in_progress && /^[[:space:]]*current_chapter:[[:space:]]*/ {
      sub(/^[[:space:]]*current_chapter:[[:space:]]*/, "", $0)
      gsub(/#.*/, "", $0)
      gsub(/[[:space:]]+$/, "", $0)
      print $0
      exit
    }
  ' "$progress_file" 2>/dev/null || true)"
  if [[ -n "$current_chapter" ]] && [[ "$current_chapter" =~ ^[0-9]+$ ]]; then
    chapters_written=$((current_chapter - 1))
  fi
fi

if [[ -z "$chapters_written" ]] || ! [[ "$chapters_written" =~ ^[0-9]+$ ]]; then
  echo "[nvChain] Error: cannot determine chapters_written" >&2
  exit 2
fi

# Also check max file-based chapter
max_file=0
shopt -s nullglob
for path in "$REPO_ROOT/projects/$project_folder/output/chapters"/chapter_*.md; do
  base="${path##*/}"
  num="${base#chapter_}"
  num="${num%.md}"
  if [[ "$num" =~ ^[0-9]+$ ]] && [[ "$num" -gt "$max_file" ]]; then
    max_file="$num"
  fi
done
shopt -u nullglob

# Use the higher of config chapter or file-based chapter
just_written="$chapters_written"
if [[ "$max_file" -gt "$just_written" ]]; then
  just_written="$max_file"
fi

# ─── Check target (flag only, don't exit yet — SubArc/Arc check first) ───
target_reached=false
if [[ "$just_written" -ge "$target_chapter" ]]; then
  target_reached=true
fi

# ─── Detect SubArc / Arc completion ───
on_subarc_complete="$(parse_yaml_value "on_subarc_complete" "$CONFIG_FILE")"
on_arc_complete="$(parse_yaml_value "on_arc_complete" "$CONFIG_FILE")"
last_arc="$(parse_yaml_value "last_arc" "$CONFIG_FILE")"
on_subarc_complete="${on_subarc_complete:-true}"
on_arc_complete="${on_arc_complete:-true}"
last_arc="${last_arc:-0}"

# Parse current_beat.title from narrative_progress.yaml
# Handles both inline (current_beat: null) and block-style YAML
current_beat_title="$(awk '
  BEGIN { in_beat=0 }
  /^current_beat:/ {
    sub(/^current_beat:[[:space:]]*/, "", $0)
    gsub(/[[:space:]]+$/, "", $0)
    if ($0 == "null" || $0 == "~") {
      print "EMPTY"
      exit
    }
    if ($0 != "") {
      # Unexpected inline value
      print "HAS_CONTENT"
      exit
    }
    # Empty after colon = block mapping, check nested title
    in_beat=1
    next
  }
  in_beat && /^[^[:space:]]/ {
    # Left the current_beat block without finding title
    print "EMPTY"
    exit
  }
  in_beat && /^[[:space:]]+title:[[:space:]]*/ {
    sub(/^[[:space:]]+title:[[:space:]]*/, "", $0)
    gsub(/#.*/, "", $0)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
    gsub(/^"(.*)"$/, "\\1", $0)
    gsub(/^'"'"'/, "", $0)
    gsub(/'"'"'$/, "", $0)
    if ($0 == "" || $0 == "null" || $0 == "~") {
      print "EMPTY"
    } else {
      print "HAS_CONTENT"
    }
    exit
  }
' "$progress_file" 2>/dev/null || echo "EMPTY")"
current_beat_title="${current_beat_title:-EMPTY}"

# Parse upcoming_beats count from narrative_progress.yaml
upcoming_count="$(awk '
  BEGIN { in_list=0; count=0; done=0 }
  /^upcoming_beats:/ {
    sub(/^upcoming_beats:[[:space:]]*/, "", $0)
    gsub(/[[:space:]]+$/, "", $0)
    if ($0 == "[]" || $0 == "null" || $0 == "~") {
      print "0"
      done=1
      exit
    }
    if ($0 == "") {
      # Block format - count items below
      in_list=1
    }
    next
  }
  in_list && /^[^[:space:]-]/ { print count; done=1; exit }
  in_list && /^[[:space:]]*-[[:space:]]/ { count++ }
  END { if (!done && in_list) print count }
' "$progress_file" 2>/dev/null || echo "0")"
upcoming_count="${upcoming_count:-0}"

# Parse current_arc
current_arc="$(awk '
  BEGIN { in_progress=0 }
  /^[[:space:]]*progress:[[:space:]]*$/ { in_progress=1; next }
  in_progress && /^[^[:space:]]/ { in_progress=0 }
  in_progress && /^[[:space:]]*current_arc:[[:space:]]*/ {
    sub(/^[[:space:]]*current_arc:[[:space:]]*/, "", $0)
    gsub(/#.*/, "", $0)
    gsub(/[[:space:]]+$/, "", $0)
    print $0
    exit
  }
' "$progress_file" 2>/dev/null || true)"
current_arc="${current_arc:-0}"

subarc_completed=false
arc_completed=false

# SubArc complete = current_beat empty AND upcoming_beats empty
if [[ "$current_beat_title" == "EMPTY" ]] && [[ "$upcoming_count" -eq 0 ]]; then
  subarc_completed=true
fi

# Arc detection method 1: check outline structure (timely detection)
# When SubArc is completing, check if it's the last SubArc of the current Arc
if [[ "$subarc_completed" == "true" ]] && [[ "$on_arc_complete" == "true" ]]; then
  current_subarc_id="$(awk '
    BEGIN { in_progress=0 }
    /^[[:space:]]*progress:[[:space:]]*$/ { in_progress=1; next }
    in_progress && /^[^[:space:]]/ { in_progress=0 }
    in_progress && /^[[:space:]]*current_subarc_id:[[:space:]]*/ {
      sub(/^[[:space:]]*current_subarc_id:[[:space:]]*/, "", $0)
      gsub(/#.*/, "", $0)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
      print $0
      exit
    }
  ' "$progress_file" 2>/dev/null || true)"

  # Find last SubArc ID in the outline file for current arc
  outline_file="$REPO_ROOT/projects/$project_folder/config/outline/arc_${current_arc}.yaml"
  last_subarc_id=""
  if [[ -f "$outline_file" ]]; then
    last_subarc_id="$(awk '
      /^[[:space:]]*- id:[[:space:]]*/ {
        sub(/^[[:space:]]*- id:[[:space:]]*/, "", $0)
        gsub(/#.*/, "", $0)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
        gsub(/^"(.*)"$/, "\\1", $0)
        last=$0
      }
      END { print last }
    ' "$outline_file" 2>/dev/null || true)"
  fi

  if [[ -n "$current_subarc_id" ]] && [[ -n "$last_subarc_id" ]] && [[ "$current_subarc_id" == "$last_subarc_id" ]]; then
    arc_completed=true
  fi
fi

# Arc detection method 2 (fallback): detect arc transition after nvMaint has run
if [[ "$arc_completed" != "true" ]] && [[ "$last_arc" -gt 0 ]] && [[ "$current_arc" =~ ^[0-9]+$ ]] && [[ "$current_arc" -ne "$last_arc" ]]; then
  arc_completed=true
fi

# Update last_arc in config
if [[ "$current_arc" =~ ^[0-9]+$ ]] && [[ "$current_arc" -ne "$last_arc" ]]; then
  if grep -q "^last_arc:" "$CONFIG_FILE" 2>/dev/null; then
    sed -i '' "s/^last_arc:.*$/last_arc: $current_arc/" "$CONFIG_FILE"
  fi
fi

# Read pacing_pointer from novel_config.yaml for review range
novel_config="$REPO_ROOT/projects/$project_folder/config/novel_config.yaml"
pacing_pointer=""
if [[ -f "$novel_config" ]]; then
  pacing_pointer="$(awk '
    /^[[:space:]]*pacing_pointer:[[:space:]]*/ {
      sub(/^[[:space:]]*pacing_pointer:[[:space:]]*/, "", $0)
      gsub(/#.*/, "", $0)
      gsub(/[[:space:]]+$/, "", $0)
      print $0
      exit
    }
  ' "$novel_config" 2>/dev/null || true)"
fi
pacing_pointer="${pacing_pointer:-0.4}"

# Calculate review_chapters = ceil(1/pacing)
review_chapters="$(python3 -c "import math; print(math.ceil(1.0/$pacing_pointer))" 2>/dev/null || echo 3)"
review_start=$((just_written - review_chapters + 1))
if [[ "$review_start" -lt 1 ]]; then
  review_start=1
fi

# ─── Handle SubArc/Arc completion ───
if [[ "$arc_completed" == "true" ]] && [[ "$on_arc_complete" == "true" ]]; then
  # Build continuation command (or stop if target reached)
  if [[ "$target_reached" == "true" ]]; then
    continue_line="自動鏈式續寫結束（目標第 ${target_chapter} 章已達成）。"
  else
    nv_cmd="/nvChapter proj=$proj"
    if [[ -n "$direction" ]] && [[ "$direction" != '\1' ]] && [[ "$direction" != '""' ]]; then
      nv_cmd="$nv_cmd direction=\"$direction\""
    fi
    if [[ "$review" == "false" ]]; then
      nv_cmd="$nv_cmd review=false"
    fi
    continue_line="完成後繼續：$nv_cmd"
  fi

  cat >&2 <<EOF

=== [nvChain] Arc ${last_arc} 完成！ ===
第 ${just_written} 章完成 | 目標：第 ${target_chapter} 章 | 剩餘：$((target_chapter - just_written)) 章

Arc 完成，請執行維護審查：
1. /nvAudit proj=$proj range=${review_start}-${just_written}
${continue_line}
================================
EOF
  exit 2
fi

if [[ "$subarc_completed" == "true" ]] && [[ "$on_subarc_complete" == "true" ]]; then
  # Build continuation command (or stop if target reached)
  if [[ "$target_reached" == "true" ]]; then
    continue_line="自動鏈式續寫結束（目標第 ${target_chapter} 章已達成）。"
  else
    nv_cmd="/nvChapter proj=$proj"
    if [[ -n "$direction" ]] && [[ "$direction" != '\1' ]] && [[ "$direction" != '""' ]]; then
      nv_cmd="$nv_cmd direction=\"$direction\""
    fi
    if [[ "$review" == "false" ]]; then
      nv_cmd="$nv_cmd review=false"
    fi
    continue_line="完成後繼續：$nv_cmd"
  fi

  cat >&2 <<EOF

=== [nvChain] SubArc 完成！ ===
第 ${just_written} 章完成 | 目標：第 ${target_chapter} 章 | 剩餘：$((target_chapter - just_written)) 章

SubArc 完成，請執行維護審查：
1. /nvAudit proj=$proj range=${review_start}-${just_written}
${continue_line}
================================
EOF
  exit 2
fi

# ─── Target reached without SubArc/Arc completion ───
if [[ "$target_reached" == "true" ]]; then
  cat >&2 <<EOF

=== [nvChain] ===
目標章節已達成！第 ${just_written} 章完成（目標：第 ${target_chapter} 章）
自動鏈式續寫結束。
=================
EOF
  exit 2
fi

# ─── Determine next action ───
last_digit=$((just_written % 10))

# Build nvChapter command
nv_cmd="/nvChapter proj=$proj"
if [[ -n "$direction" ]] && [[ "$direction" != '\1' ]] && [[ "$direction" != '""' ]]; then
  nv_cmd="$nv_cmd direction=\"$direction\""
fi
if [[ "$review" == "false" ]]; then
  nv_cmd="$nv_cmd review=false"
fi

# Determine context action
context_action=""
if [[ "$compact_on" != "-1" ]] && [[ "$last_digit" -eq "$compact_on" ]]; then
  context_action="compact"
elif [[ "$clean_on" != "-1" ]] && [[ "$last_digit" -eq "$clean_on" ]]; then
  context_action="clear"
fi

# ─── Output instructions to stderr + exit 2 ───
{
cat <<EOF

=== [nvChain] 自動鏈式續寫 ===
第 ${just_written} 章完成 | 目標：第 ${target_chapter} 章 | 剩餘：$((target_chapter - just_written)) 章
EOF

if [[ "$context_action" == "compact" ]]; then
  cat <<EOF

【Context 管理】章節尾數為 ${compact_on}，需要壓縮 context。
請告知使用者執行 /compact 指令，完成後繼續執行：
$nv_cmd

（提示使用者：「請輸入 /compact 壓縮對話記憶，完成後我會繼續寫下一章。」）
================================
EOF
elif [[ "$context_action" == "clear" ]]; then
  cat <<EOF

【Context 管理】章節尾數為 ${clean_on}，需要清除 context。
請告知使用者執行 /clear 指令，完成後在新的對話中執行：
$nv_cmd

（提示使用者：「請輸入 /clear 清除對話記憶，然後重新輸入上述指令繼續寫作。」）
================================
EOF
else
  cat <<EOF

繼續執行下一章：
$nv_cmd
================================
EOF
fi
} >&2

exit 2
