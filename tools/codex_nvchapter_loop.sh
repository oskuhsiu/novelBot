#!/usr/bin/env bash
# If invoked via `sh script.sh ...` (or sourced in a non-bash shell), re-exec with bash.
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

on_int() {
  # Ensure a single Ctrl+C stops the whole job (this script + any running codex exec).
  trap - INT
  echo "Interrupted (Ctrl+C). Stopping all running steps..." >&2
  kill -INT 0 2>/dev/null || true
  exit 130
}

trap on_int INT

usage() {
  cat <<'USAGE'
Usage:
  tools/codex_nvchapter_loop.sh <times> <proj_alias>

Args:
  <times>        Positive integer. Total number of nvChapter runs.
  <proj_alias>   Project alias in projects/project_registry.yaml (preferred),
                or a literal folder name under projects/ as fallback.

Flags:
  --final-full / --no-final-full
      Run/skip the final `nvMaint mode=full` (default: skip).
  --schema / --no-schema
      Enable/disable `--output-schema` for minimal JSON output (default: disabled).
  --dry-run
      Print the resolved project + planned steps; do not run `codex exec` and do not write files.

Behavior:
  - Resolves alias -> projects/<folder> via projects/project_registry.yaml.
  - Runs in `--ephemeral` mode to prevent context accumulation across runs.
  - Keeps the agent inside the project folder by `cd projects/<folder>/`.
  - Syncs workflows into projects/<folder>/.codex_prompts/ (unless --dry-run).
  - Safety check: aborts if `config/narrative_progress.yaml progress.current_chapter` disagrees with
    inferred next chapter from `completed_chapters` / `output/chapters/chapter_*.md` (prevents overwrite).
  - Executes sequentially in chunks (see CODEX_CHUNK):
      for each chunk:
        run one `codex exec` which:
          - runs `nvChapter` run_n times (run_n <= CODEX_CHUNK, except last chunk)
          - runs one `nvMaint mode=light` at chunk end
          - on the last chunk only (and only with --final-full): runs one `nvMaint mode=full`
  - Ctrl+C once stops the whole pipeline.

Examples:
  tools/codex_nvchapter_loop.sh 5 match_girl
  tools/codex_nvchapter_loop.sh 5 match_girl --final-full
  CODEX_CHUNK=3 tools/codex_nvchapter_loop.sh 9 match_girl   # (3+3+3) chapters, maint light runs 3 times
  CODEX_CHUNK=3 tools/codex_nvchapter_loop.sh 10 match_girl  # (3+3+3+1) chapters, maint light runs 4 times
  CODEX_OUTPUT_SCHEMA=1 tools/codex_nvchapter_loop.sh 5 match_girl
  tools/codex_nvchapter_loop.sh 2 match_girl --dry-run --schema --final-full

Env (optional):
  CODEX_MODEL              Default: gpt-5.2
                      Codex model name passed to `codex exec -m`.
  CODEX_CHAPTER_EFFORT     Default: high
                      Reasoning effort used for nvChapter runs.
  CODEX_MAINT_EFFORT       Default: medium
                      Reasoning effort used for nvMaint runs.
  CODEX_CHUNK              Default: 1  (allowed: 1..3)
                      How many nvChapter runs per chunk. nvMaint light runs once per chunk.
  CODEX_WORKFLOW_PROMPT    Default: .codex_prompts/nvChapter.md
                      Workflow prompt path (relative to project root).
  CODEX_MAINT_PROMPT       Default: .codex_prompts/nvMaint.md
                      Workflow prompt path (relative to project root).
  CODEX_FINAL_FULL         Default: 0  (set to 1 to run final nvMaint mode=full)
                      Same as --final-full.
  CODEX_OUTPUT_SCHEMA      Default: 0  (set to 1 to force minimal JSON output)
                      Same as --schema. Writes `.codex_prompts/_output_schema.json` (unless --dry-run).
  CODEX_DRY_RUN            Default: 0  (set to 1 to dry-run)
                      Same as --dry-run.

Flags:
  --schema / --no-schema   Enable/disable output schema (same as CODEX_OUTPUT_SCHEMA=1/0)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

times="${1:-}"
proj_alias="${2:-}"
shift 2 || true

final_full="${CODEX_FINAL_FULL:-0}"
use_output_schema="${CODEX_OUTPUT_SCHEMA:-0}"
dry_run="${CODEX_DRY_RUN:-0}"

unknown_option() {
  local arg="${1:-}"
  echo "Error: unknown option: $arg" >&2
  case "$arg" in
    -schema|--schma|--scehma|--shema)
      echo "Hint: did you mean '--schema' ?" >&2
      ;;
    -dry-run|--dryrun|--dry)
      echo "Hint: did you mean '--dry-run' ?" >&2
      ;;
    --finalfull|--final_full|--final)
      echo "Hint: did you mean '--final-full' ?" >&2
      ;;
  esac
  usage >&2
  exit 2
}

while [[ "${1:-}" != "" ]]; do
  case "$1" in
    --final-full)
      final_full="1"
      shift
      ;;
    --no-final-full)
      final_full="0"
      shift
      ;;
    --schema)
      use_output_schema="1"
      shift
      ;;
    --no-schema)
      use_output_schema="0"
      shift
      ;;
    --dry-run)
      dry_run="1"
      shift
      ;;
    *)
      unknown_option "$1"
      ;;
  esac
done

if [[ -z "$times" || -z "$proj_alias" ]]; then
  usage
  exit 2
fi

if ! [[ "$times" =~ ^[0-9]+$ ]] || [[ "$times" -le 0 ]]; then
  echo "Error: <times> must be a positive integer; got: $times" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v codex >/dev/null 2>&1; then
  echo "Error: 'codex' command not found in PATH." >&2
  exit 127
fi

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
  echo "Error: unknown proj alias '$proj_alias' (not in projects/project_registry.yaml) and no folder projects/$proj_alias" >&2
  exit 2
fi

project_root="$repo_root/projects/$project_folder"
if [[ ! -d "$project_root" ]]; then
  echo "Error: project folder not found: $project_root" >&2
  exit 2
fi

model="${CODEX_MODEL:-gpt-5.2}"
chapter_effort="${CODEX_CHAPTER_EFFORT:-high}"
maint_effort="${CODEX_MAINT_EFFORT:-medium}"
chunk="${CODEX_CHUNK:-1}"
workflow_prompt="${CODEX_WORKFLOW_PROMPT:-.codex_prompts/nvChapter.md}"
maint_prompt="${CODEX_MAINT_PROMPT:-.codex_prompts/nvMaint.md}"

if ! [[ "$chunk" =~ ^[0-9]+$ ]] || [[ "$chunk" -lt 1 || "$chunk" -gt 3 ]]; then
  echo "Error: CODEX_CHUNK must be 1..3; got: $chunk" >&2
  exit 2
fi

sync_prompts_into_project() {
  local src="$repo_root/.codex/prompts/"
  local dst="$project_root/.codex_prompts/"
  mkdir -p "$dst"

  # Keep prompts inside the project folder so the agent doesn't need to read outside it.
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$src" "$dst"
  else
    rm -rf "$dst"
    mkdir -p "$dst"
    cp -R "${src}." "$dst"
  fi
}

write_output_schema() {
  local schema_file="$project_root/.codex_prompts/_output_schema.json"
  cat >"$schema_file" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "required": ["ok", "summary", "files_written", "checks", "warnings"],
  "properties": {
    "ok": { "type": "boolean" },
    "summary": { "type": "string" },
    "files_written": { "type": "array", "items": { "type": "string" } },
    "checks": { "type": "array", "items": { "type": "string" } },
    "warnings": { "type": "array", "items": { "type": "string" } }
  }
}
JSON
}

if [[ "$dry_run" != "1" ]]; then
  sync_prompts_into_project

  if [[ "$use_output_schema" == "1" ]]; then
    write_output_schema
  fi
fi

proj_arg="proj=$proj_alias"
chapter_exec_prompt="執行${workflow_prompt} $proj_arg"
maint_light_prompt="執行${maint_prompt} $proj_arg mode=light"
maint_full_prompt="執行${maint_prompt} $proj_arg mode=full"

PREFLIGHT_BLOCK=""
OUTPUT_FORMAT_BLOCK=""
PREFLIGHT_NEXT_CHAPTER=""
PREFLIGHT_CHAPTERS_WRITTEN=""
PREFLIGHT_CURRENT_BEAT=""
PREFLIGHT_EFFECTIVE_NEXT_CHAPTER=""
PREFLIGHT_MAX_WRITTEN=""

preflight() {
  local planned_n="${1:-}"
  local progress_file="$project_root/config/narrative_progress.yaml"
  local next_chapter=""
  local chapters_written=""
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

  chapters_written="$(
    awk '
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

  if [[ -z "$current_beat" ]]; then
    current_beat="(n/a)"
  fi

  # Infer max written chapter from narrative_progress.yaml.completed_chapters and output/chapters/chapter_*.md.
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
  if [[ "$max_file" == "0" ]]; then
    max_file=""
  fi

  max_written="0"
  if [[ "$max_completed" =~ ^[0-9]+$ ]] && [[ "$max_completed" -gt "$max_written" ]]; then
    max_written="$max_completed"
  fi
  if [[ "$max_file" =~ ^[0-9]+$ ]] && [[ "$max_file" -gt "$max_written" ]]; then
    max_written="$max_file"
  fi
  if [[ "$max_written" == "0" ]]; then
    max_written=""
  fi

  effective_next="$next_chapter"
  if [[ "$max_written" =~ ^[0-9]+$ ]]; then
    effective_next=$((max_written + 1))
  fi

  # Safety: prevent re-writing already-written chapter files due to stale progress.current_chapter.
  if [[ "$next_chapter" =~ ^[0-9]+$ ]] && [[ "$effective_next" =~ ^[0-9]+$ ]] && [[ "$next_chapter" -ne "$effective_next" ]]; then
    echo "Error: progress mismatch detected (refusing to continue to avoid overwriting chapters)." >&2
    echo "  projects/$project_folder/config/narrative_progress.yaml progress.current_chapter=$next_chapter" >&2
    if [[ "$max_written" =~ ^[0-9]+$ ]]; then
      echo "  inferred_next_chapter=$effective_next (max_written=$max_written from completed_chapters/output/chapters)" >&2
    else
      echo "  inferred_next_chapter=$effective_next (unable to infer max_written)" >&2
    fi
    echo "Fix: update narrative_progress.yaml or run a repair maint (e.g. nvMaint mode=full) and re-run." >&2
    exit 2
  fi

  PREFLIGHT_NEXT_CHAPTER="$next_chapter"
  PREFLIGHT_CHAPTERS_WRITTEN="$chapters_written"
  PREFLIGHT_CURRENT_BEAT="$current_beat"
  PREFLIGHT_EFFECTIVE_NEXT_CHAPTER="$effective_next"
  PREFLIGHT_MAX_WRITTEN="${max_written:-""}"

  OUTPUT_FORMAT_BLOCK=""
  if [[ "$use_output_schema" == "1" ]]; then
    OUTPUT_FORMAT_BLOCK=$(
      cat <<'EOF'
【輸出格式（強制）】
- 你的「最後一則輸出」必須是單一 JSON 物件，符合 output schema。
- JSON 必須包含：ok(boolean), summary(string), files_written(array), checks(array), warnings(array)。
- 不要在 JSON 前後加任何額外文字。
EOF
    )
  fi

  local planned_range=""
  if [[ "$planned_n" =~ ^[0-9]+$ ]] && [[ "$planned_n" -ge 1 ]] && [[ "$effective_next" =~ ^[0-9]+$ ]]; then
    planned_end=$((effective_next + planned_n - 1))
    planned_range="（本次 chunk 目標：第 ${effective_next}~${planned_end} 章，共 ${planned_n} 章）"
  fi

  PREFLIGHT_BLOCK=$(
    cat <<EOF
【Preflight（已由本機解析，勿重複掃描）】
- progress.current_chapter: ${next_chapter:-"(unknown)"} | inferred_next: ${effective_next:-"(unknown)"}
- progress.chapters_written: ${chapters_written:-"(unknown)"}
- current_beat: ${current_beat}
$planned_range
EOF
  )
}

print_dry_run_plan() {
  local total="$1"
  local chunk_size="$2"

  echo "DRY RUN: no codex exec, no file writes"
  echo "  proj_alias=$proj_alias -> projects/$project_folder/"
  echo "  model=$model"
  echo "  chunk=$chunk_size | chapter_effort=$chapter_effort | maint_effort=$maint_effort"
  echo "  workflow_prompt=$workflow_prompt | maint_prompt=$maint_prompt"
  echo "  schema=$use_output_schema | final_full=$final_full"

  if [[ "$dry_run" == "1" ]]; then
    echo "  note: prompts sync skipped; .codex_prompts/ must exist for real runs"
  fi

  if [[ "$PREFLIGHT_NEXT_CHAPTER" =~ ^[0-9]+$ ]]; then
    echo "  next_chapter(from progress)=$PREFLIGHT_NEXT_CHAPTER | current_beat=$PREFLIGHT_CURRENT_BEAT"
  else
    echo "  next_chapter(from progress)=(unknown) | current_beat=$PREFLIGHT_CURRENT_BEAT"
  fi
  if [[ -n "$PREFLIGHT_EFFECTIVE_NEXT_CHAPTER" ]]; then
    if [[ -n "$PREFLIGHT_MAX_WRITTEN" ]]; then
      echo "  inferred_next=$PREFLIGHT_EFFECTIVE_NEXT_CHAPTER (max_written=$PREFLIGHT_MAX_WRITTEN)"
    else
      echo "  inferred_next=$PREFLIGHT_EFFECTIVE_NEXT_CHAPTER"
    fi
  fi

  local done=0
  while [[ "$done" -lt "$total" ]]; do
    local remaining=$((total - done))
    local run_n="$chunk_size"
    if [[ "$remaining" -lt "$run_n" ]]; then
      run_n="$remaining"
    fi

    local start="?"
    local end="?"
    if [[ "$PREFLIGHT_EFFECTIVE_NEXT_CHAPTER" =~ ^[0-9]+$ ]]; then
      start=$((PREFLIGHT_EFFECTIVE_NEXT_CHAPTER + done))
      end=$((start + run_n - 1))
    fi

    local suffix=""
    if [[ "$final_full" == "1" ]] && [[ $((done + run_n)) -eq "$total" ]]; then
      suffix=" + nvMaint full x1"
    fi
    echo "  chunk: codex exec x1 -> nvChapter x$run_n (expected chapters: $start..$end) + nvMaint light x1$suffix"
    done=$((done + run_n))
  done

  echo "  final: (included in last chunk only when enabled)"
}

nav_preamble() {
  cat <<'EOF'
你是 novel agent。
你目前的工作目錄就是本專案根目錄（允許存取範圍的根）：.

【硬性路徑與工具規則（違反即失敗，立刻停止）】
- 只允許讀寫「本目錄」底下的檔案（任何路徑不得含有 '..'，不得使用絕對路徑）。
- 禁止存取 repo 其他資料夾（例如其他 projects/*、docs/、templates/、.git/ 等）。
- 允許讀取本專案內的 workflow 檔案：.codex_prompts/*
- 允許執行算字數工具，嚴禁使用 `cd` 或 `perl` 或自己寫腳本。
  必須遵循 .agent/skills/execution/word_counter/SKILL.md 中的標準指令。

【算力節省規則】
- 禁止做無目的的大範圍掃描（例如 find/rg 掃整個 tree）。
- 禁止把章節正文貼到終端輸出；只回報最小必要結果（檔案寫入、字數、是否通過）。

只做我指定的動作，不要提出問題，不要額外建議。
EOF
}

run_codex_ephemeral() {
  local effort="$1"
  local body="$2"

  local -a extra_args=()
  if [[ "$use_output_schema" == "1" ]]; then
    extra_args+=(--output-schema ".codex_prompts/_output_schema.json")
  fi

  ( cd "$project_root" && codex exec --ephemeral -m "$model" -c "model_reasoning_effort=\"$effort\"" "${extra_args[@]}" - ) <<EOF
$(nav_preamble)

$PREFLIGHT_BLOCK

$OUTPUT_FORMAT_BLOCK

$body
EOF
}

build_chunk_body() {
  local run_n="$1"
  local chunk_start="${2:-}"
  local chunk_end="${3:-}"
  local include_full="${4:-0}"

  cat <<EOF
【本次 chunk 任務】
- 目標章節：${chunk_start:-"?"}~${chunk_end:-"?"}（共 $run_n 章）

請「連續」完成以下流程，不要中途停下，不要詢問我是否繼續：
1) 重複 $run_n 次：完整執行
   $chapter_exec_prompt
2) chunk 結束後：完整執行
   $maint_light_prompt
EOF

  if [[ "$include_full" == "1" ]]; then
    cat <<EOF
3) 這是最後一個 chunk：再完整執行
   $maint_full_prompt
EOF
  fi

  cat <<'EOF'

【輸出要求（節省算力）】
- 禁止在終端輸出章節正文。
- 除非遇到錯誤，過程輸出保持最少；最後只輸出必要的檔案/章號/驗證結果。
EOF
}

completed=0
while [[ "$completed" -lt "$times" ]]; do
  remaining=$((times - completed))
  run_n="$chunk"
  if [[ "$remaining" -lt "$run_n" ]]; then
    run_n="$remaining"
  fi

  preflight "$run_n"

  if [[ "$dry_run" == "1" ]]; then
    print_dry_run_plan "$times" "$chunk"
    exit 0
  fi

  echo "═══════════════════════════════════════════════════════"
  echo "▶ batch: next $run_n chapter(s) | completed=$completed/$times | proj=$proj_alias -> $project_folder"
  echo "  model=$model"
  echo "  chapter_effort=$chapter_effort | maint_effort=$maint_effort"
  echo "  cwd=$project_root"
  echo "═══════════════════════════════════════════════════════"

  chunk_start="${PREFLIGHT_EFFECTIVE_NEXT_CHAPTER:-""}"
  chunk_end=""
  if [[ "$chunk_start" =~ ^[0-9]+$ ]]; then
    chunk_end=$((chunk_start + run_n - 1))
  fi

  include_full="0"
  if [[ "$final_full" == "1" ]] && [[ $((completed + run_n)) -eq "$times" ]]; then
    include_full="1"
  fi

  body="$(build_chunk_body "$run_n" "$chunk_start" "$chunk_end" "$include_full")"
  echo "▶ codex exec: chunk (chapters ${chunk_start:-"?"}..${chunk_end:-"?"})"
  run_codex_ephemeral "$chapter_effort" "$body"

  completed=$((completed + run_n))
done
