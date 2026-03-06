#!/usr/bin/env bash
# Claude Code batch novel writing script.
# Each phase (beat/draft/expand/review/maint) runs as an independent
# `claude -p` call with different model + effort settings.
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
  tools/claude_nvbatch.sh <times> <proj_alias> [flags]
  tools/claude_nvbatch.sh --review-only <proj_alias> [--range START-END] [--review-mode light|full]

Args:
  <times>        Positive integer. Total number of chapters to write.
  <proj_alias>   Project alias in projects/project_registry.yaml,
                 or a literal folder name under projects/ as fallback.

Flags:
  --final-full / --no-final-full
      Run/skip the final `nvMaint mode=full` (default: run).
  --no-review
      Skip Phase 3 (nvReview + auto-fix).
  --no-beat
      Skip Phase 0 (nvBeat auto-trigger).
  --skip-permissions
      Add `--dangerously-skip-permissions` to all claude calls.
  --dry-run
      Print the resolved project + planned steps; do not run anything.
  --review-only
      Review-only mode: skip writing, only run review + auto-fix.
      <times> is not required in this mode.
  --range START-END
      Chapter range for review-only mode (e.g. --range 10-20).
      Default: last 5 chapters.
  --review-mode light|full
      Review depth for review-only mode (default: light).

Behavior:
  Batch mode — each chunk goes through 5 phases with different model/effort:
    Phase 0: nvBeat    (opus/high)   — only if current_beat is empty
    Phase 1: nvDraft   (sonnet/med)  — batch draft all chapters in chunk
    Phase 2: nvExpand  (opus/med)    — expand one chapter at a time
    Phase 3: nvReview  (opus/high)   — review + auto-fix the chunk
    Phase 4: nvMaint   (sonnet/low)  — sync memory & settings

  Review-only mode — runs only Phase 3 (opus/high).

Examples:
  tools/claude_nvbatch.sh 5 gou
  tools/claude_nvbatch.sh 3 eve --no-review
  CHUNK_SIZE=2 tools/claude_nvbatch.sh 6 gou
  tools/claude_nvbatch.sh 1 gou --dry-run

  # Review-only:
  tools/claude_nvbatch.sh --review-only gou                          # last 5 chapters
  tools/claude_nvbatch.sh --review-only gou --range 10-20            # specific range
  tools/claude_nvbatch.sh --review-only eve --range 1-30 --review-mode full

Env (optional):
  CLAUDE_DRAFT_MODEL     Default: sonnet       Draft model
  CLAUDE_DRAFT_EFFORT    Default: medium       Draft effort
  CLAUDE_EXPAND_MODEL    Default: opus         Expand model
  CLAUDE_EXPAND_EFFORT   Default: medium       Expand effort
  CLAUDE_REVIEW_MODEL    Default: opus         Review model
  CLAUDE_REVIEW_EFFORT   Default: high         Review effort
  CLAUDE_BEAT_MODEL      Default: opus         Beat model
  CLAUDE_BEAT_EFFORT     Default: high         Beat effort
  CLAUDE_MAINT_MODEL     Default: sonnet       Maint model
  CLAUDE_MAINT_EFFORT    Default: low          Maint effort
  CHUNK_SIZE             Default: 1  (1..5)    Chapters per chunk
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# --- Defaults ---
times=""
proj_alias=""
final_full="1"
do_review="1"
do_beat="1"
skip_permissions="0"
dry_run="0"
review_only="0"
review_range=""
review_mode="light"

# --- Parse all args (positional + flags mixed) ---
positional=()
while [[ "${1:-}" != "" ]]; do
  case "$1" in
    --final-full)       final_full="1"; shift ;;
    --no-final-full)    final_full="0"; shift ;;
    --no-review)        do_review="0"; shift ;;
    --no-beat)          do_beat="0"; shift ;;
    --skip-permissions) skip_permissions="1"; shift ;;
    --dry-run)          dry_run="1"; shift ;;
    --review-only)      review_only="1"; shift ;;
    --range)
      if [[ -z "${2:-}" ]]; then echo "Error: --range requires a value (e.g. 10-20)" >&2; exit 2; fi
      review_range="$2"; shift 2 ;;
    --review-mode)
      if [[ -z "${2:-}" ]]; then echo "Error: --review-mode requires light|full" >&2; exit 2; fi
      review_mode="$2"; shift 2 ;;
    -*)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      positional+=("$1"); shift ;;
  esac
done

# --- Resolve positional args based on mode ---
if [[ "$review_only" == "1" ]]; then
  # Review-only: only <proj_alias> is required
  if [[ ${#positional[@]} -lt 1 ]]; then
    echo "Error: --review-only requires <proj_alias>" >&2
    usage >&2
    exit 2
  fi
  proj_alias="${positional[0]}"
else
  # Batch mode: <times> <proj_alias> required
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
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v claude >/dev/null 2>&1; then
  echo "Error: 'claude' command not found in PATH." >&2
  exit 127
fi

# --- Model/effort config ---
draft_model="${CLAUDE_DRAFT_MODEL:-sonnet}"
draft_effort="${CLAUDE_DRAFT_EFFORT:-medium}"
expand_model="${CLAUDE_EXPAND_MODEL:-opus}"
expand_effort="${CLAUDE_EXPAND_EFFORT:-medium}"
review_model="${CLAUDE_REVIEW_MODEL:-opus}"
review_effort="${CLAUDE_REVIEW_EFFORT:-high}"
beat_model="${CLAUDE_BEAT_MODEL:-opus}"
beat_effort="${CLAUDE_BEAT_EFFORT:-high}"
maint_model="${CLAUDE_MAINT_MODEL:-sonnet}"
maint_effort="${CLAUDE_MAINT_EFFORT:-low}"
chunk_size="${CHUNK_SIZE:-1}"

if ! [[ "$chunk_size" =~ ^[0-9]+$ ]] || [[ "$chunk_size" -lt 1 || "$chunk_size" -gt 5 ]]; then
  echo "Error: CHUNK_SIZE must be 1..5; got: $chunk_size" >&2
  exit 2
fi

# ═══════════════════════════════════════════════════════
#  Project resolution (same logic as codex version)
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

  current_beat="$(
    awk '
      /^[[:space:]]*current_beat:[[:space:]]*/ {
        sub(/^[[:space:]]*current_beat:[[:space:]]*/, "", $0)
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

  # Safety: prevent overwriting chapters due to stale progress.current_chapter.
  if [[ "$next_chapter" =~ ^[0-9]+$ ]] && [[ "$effective_next" =~ ^[0-9]+$ ]] && [[ "$next_chapter" -ne "$effective_next" ]]; then
    echo "Error: progress mismatch detected (refusing to continue to avoid overwriting chapters)." >&2
    echo "  narrative_progress.yaml progress.current_chapter=$next_chapter" >&2
    echo "  inferred_next_chapter=$effective_next (max_written=$max_written)" >&2
    echo "Fix: update narrative_progress.yaml or run nvMaint mode=full, then re-run." >&2
    exit 2
  fi

  PREFLIGHT_NEXT_CHAPTER="$next_chapter"
  PREFLIGHT_CURRENT_BEAT="$current_beat"
  PREFLIGHT_EFFECTIVE_NEXT_CHAPTER="$effective_next"
  PREFLIGHT_MAX_WRITTEN="${max_written:-""}"
}

# ═══════════════════════════════════════════════════════
#  Navigation preamble (injected into every claude call)
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
#  Core: run claude in print mode
# ═══════════════════════════════════════════════════════

run_claude() {
  local model="$1"
  local effort="$2"
  local body="$3"

  local -a extra_args=()
  if [[ "$skip_permissions" == "1" ]]; then
    extra_args+=(--dangerously-skip-permissions)
  else
    extra_args+=(--permission-mode acceptEdits)
  fi

  local prompt
  prompt="$(nav_preamble)

$body"

  echo "$prompt" | ( cd "$project_root" && claude -p \
    --model "$model" \
    --effort "$effort" \
    "${extra_args[@]}" \
    --no-session-persistence )
}

# ═══════════════════════════════════════════════════════
#  Phase functions
# ═══════════════════════════════════════════════════════

phase_beat() {
  echo "  🪚 Phase 0: nvBeat (${beat_model}/${beat_effort})"
  run_claude "$beat_model" "$beat_effort" "$(cat <<EOF
【Preflight】
- progress.current_chapter: ${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-"?"}

【任務】
執行 /nvBeat proj=$proj_alias

完整遵循 .agent/workflows/nvBeat.md 的所有步驟。
EOF
)"
  echo "  ✅ Phase 0 done"
}

phase_draft() {
  local n="$1"
  local start="$2"
  local end="$3"

  echo "  📝 Phase 1: nvDraft x${n} (${draft_model}/${draft_effort}) [ch.${start}-${end}]"
  run_claude "$draft_model" "$draft_effort" "$(cat <<EOF
【Preflight】
- progress.current_chapter: ${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-"?"}
- 本次目標：第 ${start}~${end} 章（共 ${n} 章）

【任務】
執行 /nvDraft proj=$proj_alias n=$n review=false

完整遵循 .agent/workflows/nvDraft.md 的所有步驟。
禁止中途停止，連續完成 $n 章草稿。
EOF
)"
  echo "  ✅ Phase 1 done"
}

phase_expand() {
  local start="$1"
  local n="$2"
  local end=$((start + n - 1))

  echo "  ✏️  Phase 2: nvExpand ch.${start}-${end} x${n} (${expand_model}/${expand_effort})"
  run_claude "$expand_model" "$expand_effort" "$(cat <<EOF
【Preflight】
- 擴寫範圍：第 ${start}~${end} 章（共 ${n} 章）

【任務】
執行 /nvExpand proj=$proj_alias chapter=$start n=$n

完整遵循 .agent/workflows/nvExpand.md 的所有步驟。
- Step 0 載入設定僅一次，Step 1~8 逐章迴圈執行。
- 每章字數必須達到 config 中的 words_per_chapter.min。
- 禁止中途停止，完成所有 ${n} 章後才停。
EOF
)"
  echo "  ✅ Phase 2 done (ch.${start}-${end})"
}

phase_review() {
  local start="$1"
  local end="$2"
  local mode="${3:-light}"

  echo "  🔍 Phase 3: nvReview ch.${start}-${end} mode=${mode} (${review_model}/${review_effort})"
  run_claude "$review_model" "$review_effort" "$(cat <<EOF
【Preflight】
- 審查範圍：第 ${start}~${end} 章

【任務】
1. 執行 /nvReview proj=$proj_alias range=${start}-${end} mode=${mode}
   完整遵循 .agent/workflows/nvReview.md 的所有步驟。

2. 若發現 Critical 或 Warning 問題，**立即修正**：
   - 根據報告中每個問題的建議修正方案，直接修改對應章節
   - 修正後重新計算字數，確保仍 ≥ min
   - 修正完成後再次審查（最多 2 輪修正）
   - 若 2 輪後仍有 Critical → 標註 🔴 未解決

最終輸出審查/修正摘要。
EOF
)"
  echo "  ✅ Phase 3 done"
}

phase_maint() {
  local mode="$1"

  echo "  🔧 Phase 4: nvMaint mode=${mode} (${maint_model}/${maint_effort})"
  run_claude "$maint_model" "$maint_effort" "$(cat <<EOF
【任務】
執行 /nvMaint proj=$proj_alias mode=$mode

完整遵循 .agent/workflows/nvMaint.md 的所有步驟。
EOF
)"
  echo "  ✅ Phase 4 done"
}

# ═══════════════════════════════════════════════════════
#  Beat check helper (re-reads progress between expands)
# ═══════════════════════════════════════════════════════

check_beat_needed() {
  local progress_file="$project_root/config/narrative_progress.yaml"
  local current_beat
  current_beat="$(
    awk '
      /^[[:space:]]*current_beat:[[:space:]]*/ {
        sub(/^[[:space:]]*current_beat:[[:space:]]*/, "", $0)
        gsub(/#.*/, "", $0)
        gsub(/[[:space:]]+$/, "", $0)
        print $0
        exit
      }
    ' "$progress_file" 2>/dev/null || true
  )"

  if [[ -z "$current_beat" || "$current_beat" == "null" || "$current_beat" == "~" ]]; then
    return 0  # beat needed
  fi
  return 1  # beat NOT needed
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
  echo "  total chapters=$total | chunk_size=$chunk_size"
  echo "  next_chapter=${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-?}"
  echo "  current_beat=${PREFLIGHT_CURRENT_BEAT:-(empty)}"
  echo "───────────────────────────────────────────────────────"
  echo "  Phase config:"
  echo "  ├─ Beat:   ${beat_model}/${beat_effort}"
  echo "  ├─ Draft:  ${draft_model}/${draft_effort}"
  echo "  ├─ Expand: ${expand_model}/${expand_effort}"
  echo "  ├─ Review: ${review_model}/${review_effort} ($([ "$do_review" == "1" ] && echo "enabled" || echo "DISABLED"))"
  echo "  └─ Maint:  ${maint_model}/${maint_effort}"
  echo "───────────────────────────────────────────────────────"
  echo "  Flags: final_full=$final_full | review=$do_review | beat=$do_beat | skip_perms=$skip_permissions"
  echo "───────────────────────────────────────────────────────"

  local done=0
  local chunk_idx=0
  while [[ "$done" -lt "$total" ]]; do
    local remaining=$((total - done))
    local run_n="$chunk_size"
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

    echo "  Chunk $chunk_idx: ch.${start}..${end} (${run_n} chapters)"
    if [[ "$do_beat" == "1" ]]; then
      echo "    Phase 0: nvBeat (if needed)"
    fi
    echo "    Phase 1: nvDraft x${run_n}"
    echo "    Phase 2: nvExpand x${run_n} (batch, single session)"
    if [[ "$do_review" == "1" ]]; then
      echo "    Phase 3: nvReview range=${start}-${end}"
    fi
    if [[ "$is_last" == "1" && "$final_full" == "1" ]]; then
      echo "    Phase 4: nvMaint mode=full"
    else
      echo "    Phase 4: nvMaint mode=light"
    fi

    done=$((done + run_n))
  done

  echo "═══════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════
#  Review-only mode
# ═══════════════════════════════════════════════════════

if [[ "$review_only" == "1" ]]; then
  preflight

  # Determine range
  if [[ -n "$review_range" ]]; then
    # Parse user-specified range (e.g. "10-20")
    r_start="${review_range%%-*}"
    r_end="${review_range##*-}"
  else
    # Default: last 5 chapters
    if [[ "${PREFLIGHT_MAX_WRITTEN:-}" =~ ^[0-9]+$ ]]; then
      r_end="$PREFLIGHT_MAX_WRITTEN"
      r_start=$((r_end - 4))
      if [[ "$r_start" -lt 1 ]]; then r_start=1; fi
    else
      echo "Error: cannot auto-detect range (no written chapters found). Use --range." >&2
      exit 2
    fi
  fi

  if [[ "$dry_run" == "1" ]]; then
    echo "═══════════════════════════════════════════════════════"
    echo "  DRY RUN — review-only mode"
    echo "═══════════════════════════════════════════════════════"
    echo "  proj_alias=$proj_alias → projects/$project_folder/"
    echo "  range: ch.${r_start}-${r_end}"
    echo "  review_mode: $review_mode"
    echo "  model: ${review_model}/${review_effort}"
    echo "═══════════════════════════════════════════════════════"
    exit 0
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "▶ Review-only: ch.${r_start}-${r_end} | mode=${review_mode}"
  echo "═══════════════════════════════════════════════════════"

  phase_review "$r_start" "$r_end" "$review_mode"

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "  🎉 審查完成"
  echo "═══════════════════════════════════════════════════════"
  echo "  專案：$proj_alias → $project_folder"
  echo "  範圍：ch.${r_start}-${r_end}"
  echo "  模式：$review_mode"
  echo "═══════════════════════════════════════════════════════"
  exit 0
fi

# ═══════════════════════════════════════════════════════
#  Main loop (batch mode)
# ═══════════════════════════════════════════════════════

if [[ "$dry_run" == "1" ]]; then
  print_dry_run "$times"
  exit 0
fi

completed=0
chunk_idx=0
while [[ "$completed" -lt "$times" ]]; do
  remaining=$((times - completed))
  run_n="$chunk_size"
  if [[ "$remaining" -lt "$run_n" ]]; then run_n="$remaining"; fi

  # Preflight before each chunk
  preflight

  chunk_start="${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-""}"
  chunk_end=""
  if [[ "$chunk_start" =~ ^[0-9]+$ ]]; then
    chunk_end=$((chunk_start + run_n - 1))
  fi

  chunk_idx=$((chunk_idx + 1))
  is_last=0
  if [[ $((completed + run_n)) -eq "$times" ]]; then is_last=1; fi

  echo ""
  echo "═══════════════════════════════════════════════════════"
  echo "▶ Chunk $chunk_idx: ch.${chunk_start:-?}..${chunk_end:-?} | completed=$completed/$times"
  echo "═══════════════════════════════════════════════════════"

  # ─── Phase 0: Beat (if needed) ───
  if [[ "$do_beat" == "1" ]]; then
    if check_beat_needed; then
      phase_beat
      # Re-read progress after beat generation
      preflight
      chunk_start="${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-""}"
      if [[ "$chunk_start" =~ ^[0-9]+$ ]]; then
        chunk_end=$((chunk_start + run_n - 1))
      fi
    else
      echo "  ⏭️  Phase 0: Beat not needed (current_beat exists)"
    fi
  fi

  # ─── Phase 1: Draft ───
  phase_draft "$run_n" "${chunk_start:-?}" "${chunk_end:-?}"

  # ─── Phase 2: Expand (batch, one session) ───
  if [[ "$chunk_start" =~ ^[0-9]+$ ]]; then
    phase_expand "$chunk_start" "$run_n"
  else
    echo "Error: could not determine chapter numbers for expand" >&2
    exit 2
  fi

  # ─── Phase 3: Review + auto-fix ───
  if [[ "$do_review" == "1" ]]; then
    phase_review "${chunk_start}" "${chunk_end}"
  else
    echo "  ⏭️  Phase 3: Review skipped (--no-review)"
  fi

  # ─── Phase 4: Maint ───
  if [[ "$is_last" == "1" && "$final_full" == "1" ]]; then
    phase_maint "full"
  else
    phase_maint "light"
  fi

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
echo "═══════════════════════════════════════════════════════"
