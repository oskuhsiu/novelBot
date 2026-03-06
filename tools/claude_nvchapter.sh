#!/usr/bin/env bash
# Claude Code nvChapter loop — simple single-model script.
# Direct port of codex_nvchapter_loop.sh to Claude Code CLI.
# Each chunk = one `claude -p` call containing nvChapter × N + nvMaint light.
#
# If invoked via `sh script.sh ...`, re-exec with bash.
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

on_int() {
  trap - INT
  echo "Interrupted (Ctrl+C). Stopping all running steps..." >&2
  kill -INT 0 2>/dev/null || true
  exit 130
}
trap on_int INT

usage() {
  cat <<'USAGE'
Usage:
  tools/claude_nvchapter.sh <times> <proj_alias> [flags]

Args:
  <times>        Positive integer. Total number of nvChapter runs.
  <proj_alias>   Project alias in projects/project_registry.yaml,
                 or a literal folder name under projects/ as fallback.

Flags:
  -v / --verbose
      Print the full prompt and claude command before each call.
  --final-full / --no-final-full
      Run/skip the final `nvMaint mode=full` (default: skip).
  --skip-permissions
      Add `--dangerously-skip-permissions` to all claude calls.
  --dry-run
      Print the resolved project + planned steps; do not run anything.

Behavior:
  - Uses opus/medium for everything (single model, single effort).
  - Each chunk = one `claude -p` call running:
      nvChapter × run_n  +  nvMaint mode=light
  - On the last chunk only (with --final-full): + nvMaint mode=full.
  - Ctrl+C once stops the whole pipeline.

Examples:
  tools/claude_nvchapter.sh 5 gou
  tools/claude_nvchapter.sh 5 eve --final-full
  tools/claude_nvchapter.sh 2 gou -v
  CHUNK_SIZE=3 tools/claude_nvchapter.sh 9 gou           # 3+3+3 chapters
  tools/claude_nvchapter.sh 2 gou --dry-run

Env (optional):
  CLAUDE_MODEL           Default: opus
                    Claude model name passed to `claude -p --model`.
  CLAUDE_EFFORT          Default: medium
                    Reasoning effort for all calls.
  CHUNK_SIZE             Default: 1  (allowed: 1..5)
                    How many nvChapter runs per chunk. nvMaint light runs once per chunk.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# --- Defaults ---
times=""
proj_alias=""
final_full="0"
skip_permissions="0"
dry_run="0"
verbose="0"

# --- Parse all args ---
positional=()
while [[ "${1:-}" != "" ]]; do
  case "$1" in
    -v|--verbose)       verbose="1"; shift ;;
    --final-full)       final_full="1"; shift ;;
    --no-final-full)    final_full="0"; shift ;;
    --skip-permissions) skip_permissions="1"; shift ;;
    --dry-run)          dry_run="1"; shift ;;
    -*)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      positional+=("$1"); shift ;;
  esac
done

if [[ ${#positional[@]} -lt 2 ]]; then
  usage
  exit 2
fi
times="${positional[0]}"
proj_alias="${positional[1]}"

if ! [[ "$times" =~ ^[0-9]+$ ]] || [[ "$times" -le 0 ]]; then
  echo "Error: <times> must be a positive integer; got: $times" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v claude >/dev/null 2>&1; then
  echo "Error: 'claude' command not found in PATH." >&2
  exit 127
fi

# --- Config ---
model="${CLAUDE_MODEL:-opus}"
effort="${CLAUDE_EFFORT:-medium}"
chunk="${CHUNK_SIZE:-1}"

if ! [[ "$chunk" =~ ^[0-9]+$ ]] || [[ "$chunk" -lt 1 || "$chunk" -gt 5 ]]; then
  echo "Error: CHUNK_SIZE must be 1..5; got: $chunk" >&2
  exit 2
fi

vlog() {
  if [[ "$verbose" == "1" ]]; then
    echo "[verbose] $*" >&2
  fi
}

# ═══════════════════════════════════════════════════════
#  Project resolution
# ═══════════════════════════════════════════════════════

resolve_project_folder() {
  local alias="$1"
  local reg_file="projects/project_registry.yaml"
  local value

  value="$(awk -v a="$alias" '
    /^[[:space:]]*#/ { next }
    $1 == a ":" {
      $1="";
      sub(/^[[:space:]]+/, "", $0);
      print $0;
      exit
    }
  ' "$reg_file" 2>/dev/null || true)"

  if [[ -n "$value" ]]; then
    value="${value%\"}"
    value="${value#\"}"
    printf '%s' "$value"
    return 0
  fi

  if [[ -d "projects/$alias" ]]; then
    printf '%s' "$alias"
    return 0
  fi

  return 1
}

project_folder="$(resolve_project_folder "$proj_alias" || true)"
if [[ -z "$project_folder" ]]; then
  echo "Error: unknown proj alias '$proj_alias' (not in project_registry.yaml, no folder)" >&2
  exit 2
fi

project_root="$repo_root/projects/$project_folder"
if [[ ! -d "$project_root" ]]; then
  echo "Error: project folder not found: $project_root" >&2
  exit 2
fi

vlog "project resolved: $proj_alias → $project_root"

# ═══════════════════════════════════════════════════════
#  Preflight checks
# ═══════════════════════════════════════════════════════

PREFLIGHT_NEXT_CHAPTER=""
PREFLIGHT_CURRENT_BEAT=""
PREFLIGHT_EFFECTIVE_NEXT_CHAPTER=""
PREFLIGHT_MAX_WRITTEN=""

preflight() {
  local progress_file="$project_root/config/narrative_progress.yaml"
  local next_chapter=""
  local current_beat=""
  local max_completed=""
  local max_file=""
  local max_written=""
  local effective_next=""

  local -a required_files=(
    "$project_root/config/novel_config.yaml"
    "$project_root/config/character_db.yaml"
    "$project_root/config/narrative_progress.yaml"
    "$project_root/memory/lore_bank.yaml"
  )
  for file_path in "${required_files[@]}"; do
    if [[ ! -f "$file_path" ]]; then
      echo "Error: missing required file: $file_path" >&2
      exit 2
    fi
  done

  next_chapter="$(
    awk '
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
    ' "$progress_file" 2>/dev/null || true
  )"

  # Try alternative field name (current_status.chapter)
  if [[ -z "$next_chapter" ]]; then
    next_chapter="$(
      awk '
        BEGIN { in_cs=0 }
        /^[[:space:]]*current_status:[[:space:]]*$/ { in_cs=1; next }
        in_cs && /^[^[:space:]]/ { in_cs=0 }
        in_cs && /^[[:space:]]*chapter:[[:space:]]*/ {
          sub(/^[[:space:]]*chapter:[[:space:]]*/, "", $0)
          gsub(/#.*/, "", $0)
          gsub(/[[:space:]]+$/, "", $0)
          n = $0 + 1
          print n
          exit
        }
      ' "$progress_file" 2>/dev/null || true
    )"
  fi

  current_beat="$(
    awk '
      /^current_beat:[[:space:]]*$/ {
        # block mapping: check if next line has indented content
        getline nextline
        if (nextline ~ /^[[:space:]]+[^[:space:]]/) {
          print "block"
        }
        exit
      }
      /^current_beat:[[:space:]]+[^[:space:]]/ {
        # inline value
        sub(/^current_beat:[[:space:]]+/, "", $0)
        gsub(/#.*/, "", $0)
        gsub(/[[:space:]]+$/, "", $0)
        print $0
        exit
      }
    ' "$progress_file" 2>/dev/null || true
  )"
  if [[ -z "$current_beat" || "$current_beat" == "null" || "$current_beat" == "~" ]]; then
    current_beat=""
  fi

  max_completed="$(
    awk '
      BEGIN { in_cc=0; max=0 }
      /^[[:space:]]*completed_chapters:[[:space:]]*$/ { in_cc=1; next }
      in_cc && /^[^[:space:]]/ { in_cc=0 }
      in_cc && /^[[:space:]]*chapter_id:[[:space:]]*[0-9]+[[:space:]]*$/ {
        gsub(/^[[:space:]]*chapter_id:[[:space:]]*/, "", $0)
        if ($0+0 > max) max=$0+0
      }
      END { if (max>0) print max }
    ' "$progress_file" 2>/dev/null || true
  )"

  max_file="0"
  shopt -s nullglob
  for path in "$project_root/output/chapters"/chapter_*.md; do
    base="${path##*/}"
    num="${base#chapter_}"
    num="${num%.md}"
    if [[ "$num" =~ ^[0-9]+$ ]]; then
      if [[ "$num" -gt "$max_file" ]]; then
        max_file="$num"
      fi
    fi
  done
  shopt -u nullglob
  if [[ "$max_file" == "0" ]]; then max_file=""; fi

  max_written="0"
  if [[ "$max_completed" =~ ^[0-9]+$ ]] && [[ "$max_completed" -gt "$max_written" ]]; then
    max_written="$max_completed"
  fi
  if [[ "$max_file" =~ ^[0-9]+$ ]] && [[ "$max_file" -gt "$max_written" ]]; then
    max_written="$max_file"
  fi
  if [[ "$max_written" == "0" ]]; then max_written=""; fi

  effective_next="$next_chapter"
  if [[ "$max_written" =~ ^[0-9]+$ ]]; then
    effective_next=$((max_written + 1))
  fi

  # Safety check
  if [[ "$next_chapter" =~ ^[0-9]+$ ]] && [[ "$effective_next" =~ ^[0-9]+$ ]] && [[ "$next_chapter" -ne "$effective_next" ]]; then
    echo "Error: progress mismatch detected (refusing to continue to avoid overwriting chapters)." >&2
    echo "  narrative_progress.yaml next_chapter=$next_chapter" >&2
    echo "  inferred_next_chapter=$effective_next (max_written=$max_written)" >&2
    echo "Fix: update narrative_progress.yaml or run nvMaint mode=full, then re-run." >&2
    exit 2
  fi

  PREFLIGHT_NEXT_CHAPTER="$next_chapter"
  PREFLIGHT_CURRENT_BEAT="$current_beat"
  PREFLIGHT_EFFECTIVE_NEXT_CHAPTER="$effective_next"
  PREFLIGHT_MAX_WRITTEN="${max_written:-""}"

  vlog "preflight: next_chapter=$next_chapter current_beat='$current_beat' effective_next=$effective_next max_written=${max_written:-""} max_completed=${max_completed:-""} max_file=${max_file:-""}"
}

# ═══════════════════════════════════════════════════════
#  Navigation preamble
# ═══════════════════════════════════════════════════════

nav_preamble() {
  cat <<EOF
你是 novel agent。工作目錄：$project_root

【硬性路徑與工具規則】
- 只讀寫本專案目錄底下的檔案。
- 禁止存取 repo 其他資料夾 (除 .agent/ 之外)。
- 【警告】計算字數時，嚴禁使用 \`cd\`、\`perl\` 或自己寫腳本。
  必須遵循 .agent/skills/execution/word_counter/SKILL.md 中的標準指令。

【算力節省規則】
- 禁止把章節正文貼到終端輸出。
- 只回報最小必要結果（檔案寫入、字數、是否通過）。

只做我指定的動作，不要提出問題，不要額外建議。
EOF
}

# ═══════════════════════════════════════════════════════
#  Run claude
# ═══════════════════════════════════════════════════════

run_claude() {
  local body="$1"

  # claude -p (pipe mode) is non-interactive; must skip permissions
  # otherwise AI hangs waiting for bash approval that can never be granted
  local -a extra_args=(--dangerously-skip-permissions)

  local prompt
  prompt="$(nav_preamble)

$body"

  local -a cmd=(claude -p --model "$model" --effort "$effort" "${extra_args[@]}" --no-session-persistence)

  if [[ "$verbose" == "1" ]]; then
    # stream-json mode: pipe through jq to show real-time tool activity
    cmd+=(--output-format stream-json)

    echo "" >&2
    echo "┌─── claude command ───────────────────────────────────" >&2
    echo "│ ${cmd[*]}" >&2
    echo "├─── prompt ────────────────────────────────────────────" >&2
    echo "$prompt" | sed 's/^/│ /' >&2
    echo "└───────────────────────────────────────────────────────" >&2
    echo "" >&2
  fi

  vlog "launching claude -p (pid will follow)..."

  if [[ "$verbose" == "1" ]]; then
    # stream-json: pipe through jq filter to show real-time tool activity
    # Must disable pipefail/errexit here — jq parsing failures or claude
    # non-zero exit must not kill the script.
    set +eo pipefail
    echo "$prompt" | ( cd "$project_root" && "${cmd[@]}" ) 2>&1 | \
      jq --unbuffered -r '
        if .type == "assistant" then
          (.message.content[]? |
            if .type == "tool_use" then
              "  🔧 " + .name + (if .input.file_path then " → " + .input.file_path
                elif .input.command then " → " + (.input.command | tostring | .[0:80])
                elif .input.pattern then " → " + .input.pattern
                else "" end)
            elif .type == "text" then
              "  💬 " + (.text | split("\n")[0] | .[0:120])
            else empty end)
        elif .type == "result" then
          "  ✅ done | cost=$" + (.cost_usd // 0 | tostring)
        else empty end
      ' 2>/dev/null || true
    local rc=${PIPESTATUS[0]}
    set -eo pipefail
    vlog "claude exited with rc=$rc"
    return "$rc"
  else
    # non-verbose: plain text output
    echo "$prompt" | ( cd "$project_root" && "${cmd[@]}" ) &
    local claude_pid=$!
    wait "$claude_pid"
    local rc=$?
    return "$rc"
  fi
}

# ═══════════════════════════════════════════════════════
#  Build chunk prompt (mirrors codex version)
# ═══════════════════════════════════════════════════════

build_chunk_body() {
  local run_n="$1"
  local chunk_start="${2:-}"
  local chunk_end="${3:-}"
  local include_full="${4:-0}"

  cat <<EOF
【Preflight（已由本機解析，勿重複掃描）】
- progress.current_chapter: ${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-"(unknown)"}
（本次 chunk 目標：第 ${chunk_start:-"?"}~${chunk_end:-"?"} 章，共 ${run_n} 章）

【本次 chunk 任務】

請「連續」完成以下流程，不要中途停下，不要詢問我是否繼續：
1) 重複 $run_n 次：完整執行
   /nvChapter proj=$proj_alias review=false
   完整遵循 .agent/workflows/nvChapter.md 的所有步驟。
2) chunk 結束後：完整執行
   /nvMaint proj=$proj_alias mode=light
   完整遵循 .agent/workflows/nvMaint.md 的所有步驟。
EOF

  if [[ "$include_full" == "1" ]]; then
    cat <<EOF
3) 這是最後一個 chunk：再完整執行
   /nvMaint proj=$proj_alias mode=full
   完整遵循 .agent/workflows/nvMaint.md 的所有步驟。
EOF
  fi

  cat <<'EOF'

【輸出要求（節省算力）】
- 禁止在終端輸出章節正文。
- 除非遇到錯誤，過程輸出保持最少；最後只輸出必要的檔案/章號/驗證結果。
EOF
}

# ═══════════════════════════════════════════════════════
#  Dry run
# ═══════════════════════════════════════════════════════

print_dry_run() {
  local total="$1"

  preflight

  echo "═══════════════════════════════════════════════════════"
  echo "  DRY RUN — no claude calls"
  echo "═══════════════════════════════════════════════════════"
  echo "  proj_alias=$proj_alias → projects/$project_folder/"
  echo "  total chapters=$total | chunk_size=$chunk"
  echo "  model=$model | effort=$effort"
  echo "  next_chapter=${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-?}"
  echo "  current_beat=${PREFLIGHT_CURRENT_BEAT:-(empty)}"
  echo "───────────────────────────────────────────────────────"
  echo "  Flags: final_full=$final_full | skip_perms=$skip_permissions"
  echo "───────────────────────────────────────────────────────"

  local done=0
  local chunk_idx=0
  while [[ "$done" -lt "$total" ]]; do
    local remaining=$((total - done))
    local run_n="$chunk"
    if [[ "$remaining" -lt "$run_n" ]]; then run_n="$remaining"; fi

    local start="?"
    local end="?"
    if [[ "${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-}" =~ ^[0-9]+$ ]]; then
      start=$((PREFLIGHT_EFFECTIVE_NEXT_CHAPTER + done))
      end=$((start + run_n - 1))
    fi

    chunk_idx=$((chunk_idx + 1))
    local is_last=0
    if [[ $((done + run_n)) -eq "$total" ]]; then is_last=1; fi

    local suffix=""
    if [[ "$is_last" == "1" && "$final_full" == "1" ]]; then
      suffix=" + nvMaint full"
    fi
    echo "  Chunk $chunk_idx: claude -p x1 → nvChapter x$run_n (ch.${start}..${end}) + nvMaint light${suffix}"
    done=$((done + run_n))
  done

  echo "═══════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════
#  Main loop
# ═══════════════════════════════════════════════════════

if [[ "$dry_run" == "1" ]]; then
  print_dry_run "$times"
  exit 0
fi

completed=0
chunk_idx=0
while [[ "$completed" -lt "$times" ]]; do
  remaining=$((times - completed))
  run_n="$chunk"
  if [[ "$remaining" -lt "$run_n" ]]; then run_n="$remaining"; fi

  preflight

  # --- Auto-generate beats if missing ---
  if [[ -z "$PREFLIGHT_CURRENT_BEAT" ]]; then
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "⚡ current_beat 為空，自動執行 nvBeat 生成節拍..."
    echo "───────────────────────────────────────────────────────"
    run_claude "$(cat <<BEATEOF
請完整執行 /nvBeat proj=$proj_alias
完整遵循 .agent/workflows/nvBeat.md 的所有步驟。
只做這一件事，做完就停。
BEATEOF
)"
    echo "───────────────────────────────────────────────────────"
    echo "✅ nvBeat 完成，重新檢查 preflight..."
    echo "───────────────────────────────────────────────────────"
    preflight
  fi

  chunk_start="${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-""}"
  chunk_end=""
  if [[ "$chunk_start" =~ ^[0-9]+$ ]]; then
    chunk_end=$((chunk_start + run_n - 1))
  fi

  chunk_idx=$((chunk_idx + 1))
  is_last=0
  if [[ $((completed + run_n)) -eq "$times" ]]; then is_last=1; fi

  include_full="0"
  if [[ "$final_full" == "1" && "$is_last" == "1" ]]; then
    include_full="1"
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "▶ Chunk $chunk_idx: nvChapter x$run_n (ch.${chunk_start:-?}..${chunk_end:-?}) | completed=$completed/$times"
  echo "  model=$model | effort=$effort"
  echo "═══════════════════════════════════════════════════════"

  body="$(build_chunk_body "$run_n" "$chunk_start" "$chunk_end" "$include_full")"
  run_claude "$body"

  completed=$((completed + run_n))
  echo ""
  echo "✅ Chunk $chunk_idx done | total completed: $completed/$times"
done

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🎉 批次寫作完成"
echo "═══════════════════════════════════════════════════════"
echo "  專案：$proj_alias → $project_folder"
echo "  完成章數：$times"
echo "  Chunks：$chunk_idx"
echo "  模型：$model / $effort"
echo "═══════════════════════════════════════════════════════"
