#!/bin/bash
# coding-env 배포 스크립트.
# CLAUDE.md + rules/ + agents/ 를 프로젝트 디렉토리 또는 사용자 홈에 설치한다.
#
# 소유권 원칙: 이 스크립트는 레포가 배포하는 파일만 관리한다.
# 대상 디렉토리에만 존재하는 파일(사용자의 다른 에이전트·커맨드·규칙 등)은
# 충돌로 보지 않고 삭제하지도 않는다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
readonly REPO_ROOT
readonly RULES_FILE_COUNT=79
readonly AGENTS_FILE_COUNT=4
readonly COMMANDS_FILE_COUNT=6
readonly MAX_DIFF_LINES=20

scope=""
force_overwrite="false"
dry_run="false"
target_base_dir=""
target_claude_md=""
target_rules_dir=""
target_agents_dir=""
target_commands_dir=""

log_info() { echo "[INFO] $*"; }
log_warn() { echo "[WARN] $*" >&2; }
log_ok() { echo "[OK]   $*"; }
log_error() { echo "[ERROR] $*" >&2; }
log_done() { echo "[DONE] $*"; }
log_plan() { echo "  [계획] $*"; }
log_protected() { echo "  [보호] $*"; }

usage() {
  cat << 'EOF'
Usage: install.sh --scope project|user [--force] [--dry-run] [--help]

Options:
  --scope project      현재 디렉토리($PWD)에 설치
  --scope user         $HOME/.claude/ 에 설치
  --force              CLAUDE.md 백업 후 덮어쓰기, 수정된 rules/agents 강제 덮어쓰기
  --dry-run            계획만 출력 (파일시스템 변경 없음)
  --help               이 메시지 표시
EOF
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --scope)
        if [[ $# -lt 2 ]]; then
          log_error "--scope 에 값이 없습니다"
          usage
          exit 1
        fi
        scope="$2"
        shift 2
        ;;
      --force) force_overwrite="true"; shift ;;
      --dry-run) dry_run="true"; shift ;;
      --help) usage; exit 0 ;;
      *) log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
    esac
  done

  if [[ "$scope" != "project" && "$scope" != "user" ]]; then
    log_error "--scope project 또는 --scope user 를 지정하십시오"
    usage
    exit 1
  fi
}

# 심볼릭 링크 판정. macOS 의 /var → /private/var 시스템 링크는 정상으로 취급한다.
is_symlinked_path() {
  local candidate_path="$1"
  local resolved_path
  resolved_path=$(cd "$candidate_path" > /dev/null 2>&1 && /bin/pwd -P) || return 1
  if [[ "$candidate_path" == "$resolved_path" || "$candidate_path" == "${resolved_path#/private}" ]]; then
    return 1
  fi
  return 0
}

resolve_target_paths() {
  if [[ "$scope" == "project" ]]; then
    target_base_dir="$PWD"
    target_claude_md="$PWD/CLAUDE.md"
  else
    target_base_dir="$HOME"
    target_claude_md="$HOME/.claude/CLAUDE.md"
  fi
  target_rules_dir="$target_base_dir/.claude/rules"
  target_agents_dir="$target_base_dir/.claude/agents"
  target_commands_dir="$target_base_dir/.claude/commands"

  if is_symlinked_path "$target_base_dir"; then
    log_error "심볼릭 링크입니다: $target_base_dir"
    return 1
  fi
}

compute_sha256() {
  if command -v sha256sum &> /dev/null; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

count_lines() {
  grep -c . || true
}

# 대상에 없는, 우리가 배포하는 파일 목록 (복원 대상)
list_missing_managed_files() {
  local source_directory="$1"
  local target_directory="$2"
  diff -rq "$source_directory" "$target_directory" 2> /dev/null \
    | grep -E "^Only in $source_directory" || true
}

# 대상에 있으나 내용이 다른, 우리가 배포하는 파일 목록 (사용자 수정 의심 → --force 필요)
list_differing_managed_files() {
  local source_directory="$1"
  local target_directory="$2"
  diff -rq "$source_directory" "$target_directory" 2> /dev/null \
    | grep -E "^Files .* differ$" || true
}

# 경로 생성에 실제로 쓰기가 필요한, 존재하는 최상위 조상 디렉토리를 반환한다.
find_existing_ancestor() {
  local probe_path="$1"
  while [[ ! -d "$probe_path" && "$probe_path" != "/" ]]; do
    probe_path=$(dirname "$probe_path")
  done
  echo "$probe_path"
}

check_write_permission() {
  local writable_ancestor
  writable_ancestor=$(find_existing_ancestor "$target_rules_dir")
  if [[ ! -w "$writable_ancestor" ]]; then
    log_error "쓰기 권한 없음: $writable_ancestor"
    return 1
  fi
  return 0
}

claude_md_is_identical() {
  [[ -f "$target_claude_md" ]] || return 1
  [[ "$(compute_sha256 "$REPO_ROOT/CLAUDE.md")" == "$(compute_sha256 "$target_claude_md")" ]]
}

check_claude_md_conflict() {
  if [[ ! -f "$target_claude_md" ]] || claude_md_is_identical; then
    return 0
  fi
  if [[ "$force_overwrite" == "true" ]]; then
    return 0
  fi
  local target_file_hash
  target_file_hash=$(compute_sha256 "$target_claude_md")
  log_warn "$target_claude_md 가 이미 존재하고 내용이 다릅니다 (sha256 ${target_file_hash:0:12}…)"
  log_warn "덮어쓰려면 --force 를 쓰십시오 (실행 시 .bak-<타임스탬프> 로 백업됩니다)"
  return 1
}

check_no_symlink_targets() {
  local directory_path
  for directory_path in "$target_rules_dir" "$target_agents_dir" "$target_commands_dir"; do
    if [[ -L "$directory_path" ]]; then
      log_error "심볼릭 링크입니다: $directory_path"
      return 1
    fi
  done
  return 0
}

report_directory_differences() {
  local target_directory="$1"
  local differing_list="$2"
  local differing_count
  differing_count=$(printf '%s\n' "$differing_list" | count_lines)

  log_warn "$target_directory 에서 수정된 파일이 ${differing_count}건 발견됐습니다"
  printf '%s\n' "$differing_list" | head -n "$MAX_DIFF_LINES" >&2
  if [[ "$differing_count" -gt "$MAX_DIFF_LINES" ]]; then
    log_warn "…외 $((differing_count - MAX_DIFF_LINES))건"
  fi
  log_warn "덮어쓰려면 --force 를 쓰십시오"
}

# D1: 우리가 배포하는 파일이 대상에서 수정됐으면 --force 를 요구한다.
# 대상에만 있는 파일은 우리 소유가 아니므로 충돌로 보지 않는다.
check_directory_conflict() {
  local source_directory="$1"
  local target_directory="$2"

  if [[ ! -d "$target_directory" || "$force_overwrite" == "true" ]]; then
    return 0
  fi

  local differing_list
  differing_list=$(list_differing_managed_files "$source_directory" "$target_directory")
  if [[ -z "$differing_list" ]]; then
    return 0
  fi

  report_directory_differences "$target_directory" "$differing_list"
  return 1
}

# 모든 쓰기보다 먼저 실행된다. 실패하면 파일을 하나도 건드리지 않은 상태로 중단한다.
check_preconditions() {
  check_write_permission || return 1
  check_no_symlink_targets || return 1
  check_claude_md_conflict || return 1
  check_directory_conflict "$REPO_ROOT/rules" "$target_rules_dir" || return 1
  check_directory_conflict "$REPO_ROOT/agents" "$target_agents_dir" || return 1
  check_directory_conflict "$REPO_ROOT/commands" "$target_commands_dir" || return 1
  return 0
}

# 커맨드 하나를 전역(~/.claude/commands)과 비교해 same | differ | absent 를 출력한다.
classify_against_global_command() {
  local command_file="$1"
  local global_file="$HOME/.claude/commands/$(basename "$command_file")"

  if [[ ! -f "$global_file" ]]; then
    echo absent
  elif cmp -s "$command_file" "$global_file"; then
    echo same
  else
    echo differ
  fi
}

# 전역 커맨드와의 중복 상황을 보고한다.
# --scope user 는 설치 대상이 곧 전역이므로 비교가 의미 없어 생략한다.
report_global_command_overlap() {
  if [[ "$scope" != "project" || ! -d "$HOME/.claude/commands" ]]; then
    return 0
  fi

  local identical_count=0
  local differing_names=""
  local command_file
  for command_file in "$REPO_ROOT/commands"/*.md; do
    case "$(classify_against_global_command "$command_file")" in
      same) identical_count=$((identical_count + 1)) ;;
      differ) differing_names="$differing_names $(basename "$command_file" .md)" ;;
    esac
  done

  if [[ -n "$differing_names" ]]; then
    log_warn "전역 커맨드와 내용이 다릅니다:${differing_names}"
    log_warn "커맨드는 전역이 프로젝트보다 우선하므로 이 머신에서는 전역 버전이 실행됩니다"
    log_warn "프로젝트 사본을 쓰려면 전역을 갱신하십시오: install.sh --scope user"
  fi
  if [[ "$identical_count" -gt 0 ]]; then
    log_info "전역에 동일한 커맨드 ${identical_count}개 존재 — 내용이 같아 동작 차이 없음"
  fi
}

# mkdir + cp 의 실패를 명시적으로 검사한다.
# set -e 는 조건문에서 호출된 함수 내부에 적용되지 않으므로 직접 검사해야 한다.
copy_directory_contents() {
  local source_directory="$1"
  local target_directory="$2"

  if ! mkdir -p "$target_directory"; then
    log_error "디렉토리 생성 실패: $target_directory"
    return 1
  fi
  if ! cp -R "$source_directory/." "$target_directory/"; then
    log_error "복사 실패: $source_directory → $target_directory"
    return 1
  fi
  return 0
}

# 배포한 파일이 전부 대상에 있고 내용이 같은지 확인한다.
# 대상에만 있는 파일은 검사하지 않는다 (우리 소유가 아니므로).
verify_managed_files_installed() {
  local name="$1"
  local source_directory="$2"
  local target_directory="$3"

  local missing_list
  local differing_list
  missing_list=$(list_missing_managed_files "$source_directory" "$target_directory")
  differing_list=$(list_differing_managed_files "$source_directory" "$target_directory")

  if [[ -n "$missing_list" || -n "$differing_list" ]]; then
    log_error "$name/ 설치 검증 실패 — 아래 파일이 반영되지 않았습니다"
    printf '%s\n%s\n' "$missing_list" "$differing_list" | grep -E . | head -n "$MAX_DIFF_LINES" >&2
    return 1
  fi
  return 0
}

install_directory() {
  local name="$1"
  local source_directory="$2"
  local target_directory="$3"
  local managed_count="$4"

  # 대상이 없으면 diff 가 빈 출력을 내므로 0건으로 오계산된다. 신규 설치는 전량이 대상이다.
  local outdated_count
  if [[ ! -d "$target_directory" ]]; then
    outdated_count="$managed_count"
  else
    outdated_count=$(
      { list_missing_managed_files "$source_directory" "$target_directory"
        list_differing_managed_files "$source_directory" "$target_directory"; } | count_lines
    )
  fi

  copy_directory_contents "$source_directory" "$target_directory" || return 1
  verify_managed_files_installed "$name" "$source_directory" "$target_directory" || return 1

  if [[ "$outdated_count" -eq 0 ]]; then
    log_ok "$name/  ${managed_count}개 파일 → 변경 없음"
  elif [[ "$outdated_count" -eq "$managed_count" ]]; then
    log_ok "$name/  ${managed_count}개 파일 → $target_directory/"
  else
    log_ok "$name/  ${outdated_count}개 갱신 (관리 대상 ${managed_count}개) → $target_directory/"
  fi
  return 0
}

backup_existing_claude_md() {
  local backup_path
  backup_path="${target_claude_md}.bak-$(date +%Y%m%d-%H%M%S-%N)"
  if ! cp "$target_claude_md" "$backup_path"; then
    log_error "백업 실패: $backup_path"
    return 1
  fi
  log_info "기존 파일 백업: $backup_path"
  return 0
}

install_claude_md() {
  if claude_md_is_identical; then
    log_ok "CLAUDE.md → 변경 없음"
    return 0
  fi
  if [[ -f "$target_claude_md" ]]; then
    backup_existing_claude_md || return 1
  fi

  local parent_directory
  parent_directory=$(dirname "$target_claude_md")
  if ! mkdir -p "$parent_directory"; then
    log_error "디렉토리 생성 실패: $parent_directory"
    return 1
  fi
  if ! cp "$REPO_ROOT/CLAUDE.md" "$target_claude_md"; then
    log_error "복사 실패: CLAUDE.md → $target_claude_md"
    return 1
  fi
  log_ok "CLAUDE.md → $target_claude_md"
  return 0
}

log_installation_plan() {
  log_info "coding-env 설치 계획 (scope: $scope, DRY-RUN)"
  log_info "대상: $target_base_dir"

  if ! check_preconditions; then
    log_error "사전 조건 실패 — 실제 실행 시 설치되지 않습니다"
    return 1
  fi

  log_plan "mkdir -p $target_rules_dir $target_agents_dir $target_commands_dir"
  log_plan "cp -R rules/. $target_rules_dir/         (${RULES_FILE_COUNT}개)"
  log_plan "cp -R agents/. $target_agents_dir/       (${AGENTS_FILE_COUNT}개)"
  log_plan "cp -R commands/. $target_commands_dir/   (${COMMANDS_FILE_COUNT}개)"

  local planned_total=$((RULES_FILE_COUNT + AGENTS_FILE_COUNT + COMMANDS_FILE_COUNT))
  if claude_md_is_identical; then
    log_protected "$target_claude_md 내용 동일 → 건너뜀"
  else
    log_plan "cp CLAUDE.md $target_claude_md"
    planned_total=$((planned_total + 1))
  fi

  report_global_command_overlap
  log_done "${planned_total}개 파일이 대상에 반영될 예정. 실제 변경 없음"
  return 0
}

perform_installation() {
  log_info "coding-env 설치 (scope: $scope)"
  log_info "대상: $target_base_dir"

  if ! check_preconditions; then
    log_error "설치 중단 — 변경된 파일 없음"
    return 1
  fi

  install_directory "rules" "$REPO_ROOT/rules" "$target_rules_dir" "$RULES_FILE_COUNT" || return 1
  install_directory "agents" "$REPO_ROOT/agents" "$target_agents_dir" "$AGENTS_FILE_COUNT" || return 1
  install_directory "commands" "$REPO_ROOT/commands" "$target_commands_dir" "$COMMANDS_FILE_COUNT" || return 1
  install_claude_md || return 1
  report_global_command_overlap

  log_done "$((RULES_FILE_COUNT + AGENTS_FILE_COUNT + COMMANDS_FILE_COUNT + 1))개 파일 반영 완료"
  return 0
}

main() {
  parse_arguments "$@"
  resolve_target_paths || { log_error "설치 중단 — 변경된 파일 없음"; return 1; }

  if [[ "$dry_run" == "true" ]]; then
    log_installation_plan
    return $?
  fi

  perform_installation
}

main "$@"
