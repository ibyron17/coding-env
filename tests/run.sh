#!/bin/bash
# coding-env install.sh 테스트 스위트
# 각 케이스를 독립 임시 디렉토리에서 실행, HOME 치환으로 실제 ~/.claude 보호

set -euo pipefail

# 레포 루트 (이 스크립트의 부모 디렉토리)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_SCRIPT="$REPO_ROOT/install.sh"

# 통계
total_tests=0
passed_tests=0
failed_tests=0
failed_list=()

# 색상 코드
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'  # No Color

# ============================================================================
# 헬퍼 함수
# ============================================================================

log_test_name() {
  echo ""
  echo "======================================================================"
  echo "[$1] $2"
  echo "======================================================================"
}

log_info() {
  echo "[INFO] $*"
}

log_ok() {
  echo -e "${GREEN}[OK]${NC} $*"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*"
}

# 테스트 실패 기록
record_failure() {
  local test_name="$1"
  local reason="$2"
  ((failed_tests++))
  failed_list+=("$test_name: $reason")
  log_error "$reason"
}

# 단순 비교
assert_equals() {
  local expected="$1"
  local actual="$2"
  local message="$3"
  if [[ "$expected" != "$actual" ]]; then
    return 1
  fi
  return 0
}

# 파일 존재 확인
assert_file_exists() {
  local file_path="$1"
  local message="$2"
  if [[ ! -f "$file_path" ]]; then
    log_error "파일 미존재: $file_path ($message)"
    return 1
  fi
  return 0
}

# 파일 미존재 확인
assert_file_not_exists() {
  local file_path="$1"
  local message="$2"
  if [[ -f "$file_path" ]]; then
    log_error "파일 존재함 (기대: 미존재): $file_path ($message)"
    return 1
  fi
  return 0
}

# 디렉토리 존재 확인
assert_dir_exists() {
  local dir_path="$1"
  local message="$2"
  if [[ ! -d "$dir_path" ]]; then
    log_error "디렉토리 미존재: $dir_path ($message)"
    return 1
  fi
  return 0
}

# 디렉토리 미존재 확인
assert_dir_not_exists() {
  local dir_path="$1"
  local message="$2"
  if [[ -d "$dir_path" ]]; then
    log_error "디렉토리 존재함 (기대: 미존재): $dir_path ($message)"
    return 1
  fi
  return 0
}

# 종료 코드 확인
assert_exit_code() {
  local expected_code="$1"
  local actual_code="$2"
  local message="$3"
  if [[ "$expected_code" != "$actual_code" ]]; then
    log_error "종료 코드 불일치: 기대=$expected_code, 실제=$actual_code ($message)"
    return 1
  fi
  return 0
}

# 파일 개수 확인 (특정 디렉토리 아래)
count_files_recursive() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo 0
  else
    find "$dir" -type f | wc -l | xargs echo  # Trim whitespace from wc output
  fi
}

# 디렉토리 비교
assert_dirs_equal() {
  local dir1="$1"
  local dir2="$2"
  local message="$3"
  local diff_output
  diff_output=$(diff -r "$dir1" "$dir2" 2>&1 || true)
  if [[ -n "$diff_output" ]]; then
    log_error "디렉토리 내용 불일치 ($message)"
    echo "$diff_output" | head -10
    return 1
  fi
  return 0
}

# 파일 내용 일치 확인
assert_file_content_equals() {
  local file_path="$1"
  local expected_content="$2"
  local message="$3"
  local actual_content
  actual_content=$(cat "$file_path" 2>/dev/null || echo "")
  if [[ "$expected_content" != "$actual_content" ]]; then
    log_error "파일 내용 불일치 ($message)"
    log_error "기대:"
    echo "$expected_content" | head -5
    log_error "실제:"
    echo "$actual_content" | head -5
    return 1
  fi
  return 0
}

# ============================================================================
# 테스트 케이스
# ============================================================================

# T1: --scope project 신규 설치
test_scope_project_new_install() {
  local test_name="T1"
  local test_desc="--scope project 신규 설치"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  local exit_code=0
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1 || exit_code=$?

  if ! assert_exit_code 0 "$exit_code" "install.sh exit code"; then
    record_failure "$test_name" "설치 실패: exit code $exit_code"
    return 1
  fi

  # rules 37개 확인
  local rules_count
  rules_count=$(count_files_recursive "./.claude/rules")
  if ! assert_equals 37 "$rules_count" "rules 파일 개수"; then
    record_failure "$test_name" "rules 파일 개수: 기대=37, 실제=$rules_count"
    return 1
  fi

  # agents 4개 확인
  local agents_count
  agents_count=$(count_files_recursive "./.claude/agents")
  if ! assert_equals 4 "$agents_count" "agents 파일 개수"; then
    record_failure "$test_name" "agents 파일 개수: 기대=4, 실제=$agents_count"
    return 1
  fi

  # commands 9개 확인
  local commands_count
  commands_count=$(count_files_recursive "./.claude/commands")
  if ! assert_equals 9 "$commands_count" "commands 파일 개수"; then
    record_failure "$test_name" "commands 파일 개수: 기대=9, 실제=$commands_count"
    return 1
  fi

  # CLAUDE.md 존재 확인
  if ! assert_file_exists "./CLAUDE.md" "CLAUDE.md"; then
    record_failure "$test_name" "CLAUDE.md 미존재"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T2: --scope user 신규 설치
test_scope_user_new_install() {
  local test_name="T2"
  local test_desc="--scope user 신규 설치"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  # HOME을 샌드박스로 치환해 실제 ~/.claude 보호
  local exit_code=0
  HOME="$sandbox" "$INSTALL_SCRIPT" --scope user > /dev/null 2>&1 || exit_code=$?

  if ! assert_exit_code 0 "$exit_code" "install.sh exit code"; then
    record_failure "$test_name" "설치 실패: exit code $exit_code"
    return 1
  fi

  # $HOME/.claude/rules 생성 확인
  if ! assert_dir_exists "$sandbox/.claude/rules" ".claude/rules"; then
    record_failure "$test_name" ".claude/rules 디렉토리 미생성"
    return 1
  fi

  # $HOME/.claude/agents 생성 확인
  if ! assert_dir_exists "$sandbox/.claude/agents" ".claude/agents"; then
    record_failure "$test_name" ".claude/agents 디렉토리 미생성"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T3: 멱등성 — 2회 연속 실행 후 차이 없음
test_idempotency() {
  local test_name="T3"
  local test_desc="멱등성: 2회 연속 실행"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # 첫 번째 실행
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # 상태 캡처
  local first_state
  first_state=$(find "./.claude" -type f -exec md5sum {} \; | sort)

  # 초 경계를 넘겨 manifest 타임스탬프 재기록이 감지되도록 강제
  sleep 1

  # 두 번째 실행
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # 상태 비교
  local second_state
  second_state=$(find "./.claude" -type f -exec md5sum {} \; | sort)

  if ! assert_equals "$first_state" "$second_state" "두 상태 동일"; then
    record_failure "$test_name" "멱등성 위반: 상태 변경"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T4: 부분 손상 수복
test_partial_damage_recovery() {
  local test_name="T4"
  local test_desc="부분 손상 수복: rules/common/testing.md 삭제 후 재실행"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # 첫 번째 설치
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # 파일 삭제
  rm -f "./.claude/rules/common/testing.md"

  # 재실행
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # 파일 복구 확인
  if ! assert_file_exists "./.claude/rules/common/testing.md" "testing.md 복구"; then
    record_failure "$test_name" "testing.md 미복구"
    return 1
  fi

  # rules 37개 확인
  local rules_count
  rules_count=$(count_files_recursive "./.claude/rules")
  if ! assert_equals 37 "$rules_count" "rules 파일 개수"; then
    record_failure "$test_name" "rules 파일 개수: 기대=37, 실제=$rules_count"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T5: CLAUDE.md 충돌 시 중단
test_claude_md_conflict() {
  local test_name="T5"
  local test_desc="CLAUDE.md 충돌 시 중단"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # CLAUDE.md 사전 생성
  echo "existing content" > ./CLAUDE.md
  local original_content
  original_content=$(cat ./CLAUDE.md)

  # 설치 시도
  local exit_code=0
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1 || exit_code=$?

  # exit 1 확인
  if ! assert_exit_code 1 "$exit_code" "exit code 1"; then
    record_failure "$test_name" "exit code: 기대=1, 실제=$exit_code"
    return 1
  fi

  # CLAUDE.md 내용 불변 확인
  local current_content
  current_content=$(cat ./CLAUDE.md)
  if ! assert_equals "$original_content" "$current_content" "CLAUDE.md 불변"; then
    record_failure "$test_name" "CLAUDE.md 내용 변경됨"
    return 1
  fi

  # rules/agents 미설치 확인
  if [[ -d "./.claude/rules" ]]; then
    record_failure "$test_name" "rules 디렉토리가 생성됨 (기대: 미생성)"
    return 1
  fi

  if [[ -d "./.claude/agents" ]]; then
    record_failure "$test_name" "agents 디렉토리가 생성됨 (기대: 미생성)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T6: --force 백업
test_force_backup() {
  local test_name="T6"
  local test_desc="--force 백업: CLAUDE.md.bak-* 생성"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # CLAUDE.md 사전 생성
  local original_content="original content"
  echo "$original_content" > ./CLAUDE.md

  # --force 설치
  local exit_code=0
  "$INSTALL_SCRIPT" --scope project --force > /dev/null 2>&1 || exit_code=$?

  if ! assert_exit_code 0 "$exit_code" "exit code 0"; then
    record_failure "$test_name" "설치 실패: exit code $exit_code"
    return 1
  fi

  # 백업 파일 존재 확인
  local backup_files
  backup_files=$(ls -1 ./CLAUDE.md.bak-* 2>/dev/null | wc -l | xargs echo)
  if [[ "$backup_files" != "1" ]]; then
    record_failure "$test_name" "백업 파일 개수: 기대=1, 실제=$backup_files"
    return 1
  fi

  # 백업 파일 내용 확인
  local backup_content
  backup_content=$(cat ./CLAUDE.md.bak-* 2>/dev/null)
  if ! assert_equals "$original_content" "$backup_content" "백업 내용"; then
    record_failure "$test_name" "백업 내용 불일치"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T7: --force 2회 실행
test_force_double_run() {
  local test_name="T7"
  local test_desc="--force 2회 실행: 백업 파일 2개"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # CLAUDE.md 사전 생성
  echo "content 1" > ./CLAUDE.md

  # 첫 번째 --force 실행
  "$INSTALL_SCRIPT" --scope project --force > /dev/null 2>&1
  sleep 1  # 타임스탬프 보장

  # CLAUDE.md 수정
  echo "content 2" > ./CLAUDE.md

  # 두 번째 --force 실행
  "$INSTALL_SCRIPT" --scope project --force > /dev/null 2>&1

  # 백업 파일 2개 존재 확인
  local backup_files
  backup_files=$(ls -1 ./CLAUDE.md.bak-* 2>/dev/null | wc -l | xargs echo)
  if ! assert_equals 2 "$backup_files" "백업 파일 개수"; then
    record_failure "$test_name" "백업 파일 개수: 기대=2, 실제=$backup_files"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T8: --dry-run 부작용 0
test_dry_run_no_side_effect() {
  local test_name="T8"
  local test_desc="--dry-run: 파일시스템 변경 없음"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # 기존 파일 생성
  echo "existing" > existing_file.txt
  local existing_mtime
  existing_mtime=$(stat -f%m existing_file.txt 2>/dev/null || stat -c%Y existing_file.txt 2>/dev/null)
  sleep 1

  # --dry-run 실행
  "$INSTALL_SCRIPT" --scope project --dry-run > /dev/null 2>&1

  # 대상 디렉토리 미생성 확인
  if ! assert_dir_not_exists "./.claude" "./.claude 생성됨"; then
    record_failure "$test_name" "./.claude 디렉토리가 생성됨 (기대: 미생성)"
    return 1
  fi

  # 기존 파일 mtime 불변 확인
  local current_mtime
  current_mtime=$(stat -f%m existing_file.txt 2>/dev/null || stat -c%Y existing_file.txt 2>/dev/null)
  if ! assert_equals "$existing_mtime" "$current_mtime" "파일 mtime"; then
    record_failure "$test_name" "기존 파일의 mtime이 변경됨"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T9: --scope 누락 시 usage + exit 1
test_missing_scope() {
  local test_name="T9"
  local test_desc="--scope 누락 시 usage + exit 1"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # --scope 없이 실행
  local exit_code=0
  local output
  output=$("$INSTALL_SCRIPT" 2>&1)
  exit_code=$?

  if ! assert_exit_code 1 "$exit_code" "exit code 1"; then
    record_failure "$test_name" "exit code: 기대=1, 실제=$exit_code"
    return 1
  fi

  # usage 출력 확인 (--scope 문자열 포함)
  if ! echo "$output" | grep -q "\-\-scope"; then
    record_failure "$test_name" "usage 메시지에 --scope 미포함"
    return 1
  fi

  # 파일시스템 변경 없음 확인
  if [[ -d "./.claude" ]]; then
    record_failure "$test_name" "./.claude 디렉토리가 생성됨 (기대: 미생성)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T10: 쓰기 권한 없음
test_no_write_permission() {
  local test_name="T10"
  local test_desc="쓰기 권한 없음: chmod 500"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "chmod -R 755 '$sandbox' 2>/dev/null; rm -rf '$sandbox'" EXIT

  # 읽기 전용으로 변경
  chmod 500 "$sandbox"

  cd "$sandbox"

  # 설치 시도
  local exit_code=0
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1 || exit_code=$?

  # exit 1 확인
  if ! assert_exit_code 1 "$exit_code" "exit code 1"; then
    record_failure "$test_name" "exit code: 기대=1, 실제=$exit_code"
    return 1
  fi

  # 권한 복구 (정리를 위해)
  chmod 755 "$sandbox"

  # 부분 설치 없음 확인
  if [[ -d "$sandbox/.claude" ]]; then
    record_failure "$test_name" "./.claude 디렉토리가 생성됨 (부분 설치)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T12: paths frontmatter 보존
test_paths_frontmatter_preserved() {
  local test_name="T12"
  local test_desc="paths frontmatter 보존"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # react/coding-style.md 확인
  local react_file="./.claude/rules/react/coding-style.md"
  if ! assert_file_exists "$react_file" "react/coding-style.md"; then
    record_failure "$test_name" "react/coding-style.md 미존재"
    return 1
  fi

  # 첫 줄이 --- 인지 확인
  local first_line
  first_line=$(head -1 "$react_file")
  if ! assert_equals "---" "$first_line" "첫 줄 YAML marker"; then
    record_failure "$test_name" "첫 줄이 '---'가 아님: $first_line"
    return 1
  fi

  # paths: 문자열 포함 확인
  if ! grep -q "^paths:" "$react_file"; then
    record_failure "$test_name" "paths: 필드 미발견"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T13: 상대경로 참조 보존
test_relative_path_references_work() {
  local test_name="T13"
  local test_desc="상대경로 참조 보존"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # typescript/coding-style.md 확인
  local ts_file="./.claude/rules/typescript/coding-style.md"
  if ! assert_file_exists "$ts_file" "typescript/coding-style.md"; then
    record_failure "$test_name" "typescript/coding-style.md 미존재"
    return 1
  fi

  # ../common/coding-style.md 참조 확인
  if ! grep -q "\.\./common/" "$ts_file"; then
    record_failure "$test_name" "../common/ 상대경로 참조 미발견"
    return 1
  fi

  # 실제 파일이 존재하는지 확인
  local common_file="./.claude/rules/common/coding-style.md"
  if ! assert_file_exists "$common_file" "common/coding-style.md (대상)"; then
    record_failure "$test_name" "상대경로가 가리키는 실제 파일 미존재"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T14: 심볼릭 링크 대상 감지
test_symlink_target_warning() {
  local test_name="T14"
  local test_desc="심볼릭 링크 대상 감지 및 중단"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  local real_dir
  real_dir=$(mktemp -d)
  trap "rm -rf '$real_dir'" EXIT

  # 심볼릭 링크 생성
  local symlink_path="$sandbox/symlink"
  ln -s "$real_dir" "$symlink_path"

  cd "$symlink_path"

  # 설치 시도
  local exit_code=0
  local output
  output=$("$INSTALL_SCRIPT" --scope project 2>&1)
  exit_code=$?

  # exit 1 확인 (경고 후 중단)
  if ! assert_exit_code 1 "$exit_code" "exit code 1"; then
    record_failure "$test_name" "exit code: 기대=1, 실제=$exit_code"
    return 1
  fi

  # .claude 디렉토리 미생성 확인
  if [[ -d "./.claude" ]]; then
    record_failure "$test_name" "./.claude 디렉토리가 생성됨 (기대: 미생성)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T15: D1 전용 — diff 감지 및 --force 요구
test_diff_detection_requires_force() {
  local test_name="T15"
  local test_desc="D1: diff 감지 및 --force 요구"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"

  # 초기 설치
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # rules 파일 수정
  echo "# modified" >> "./.claude/rules/common/coding-style.md"

  # 재실행 (--force 없음)
  local exit_code=0
  local output
  output=$("$INSTALL_SCRIPT" --scope project 2>&1)
  exit_code=$?

  # exit 1 확인
  if ! assert_exit_code 1 "$exit_code" "exit code 1"; then
    record_failure "$test_name" "exit code: 기대=1, 실제=$exit_code (diff 미감지)"
    return 1
  fi

  # 차이 파일 목록이 파일명과 함께 실제로 출력돼야 한다 (D1 스펙 요구사항)
  if ! echo "$output" | grep -q "common/coding-style.md"; then
    record_failure "$test_name" "차이 파일 목록에 common/coding-style.md 가 없음"
    return 1
  fi

  # --force 없이는 수정 내용이 보존돼야 한다 (덮어쓰지 않았음을 확인)
  if ! grep -q "^# modified$" "./.claude/rules/common/coding-style.md"; then
    record_failure "$test_name" "--force 없이 사용자 수정이 덮어써졌음"
    return 1
  fi

  # --force 재실행 후 성공 확인
  exit_code=0
  "$INSTALL_SCRIPT" --scope project --force > /dev/null 2>&1 || exit_code=$?
  if ! assert_exit_code 0 "$exit_code" "exit code 0 (--force)"; then
    record_failure "$test_name" "--force 재실행 실패"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# 모든 테스트 등록 및 실행
# T16: 소유권 원칙 — 대상에만 있는 파일은 충돌로 보지 않고 삭제하지도 않는다.
# 회귀 방지: 사용자의 ~/.claude/agents 에는 배포 대상 4개 외 수십 개가 공존한다.
test_unmanaged_files_preserved() {
  local test_name="T16"
  local test_desc="소유권 원칙: 대상에만 있는 파일 보존 및 충돌 미판정"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # 배포 대상이 아닌 파일을 대상 디렉토리에 추가
  echo "# 사용자 소유 에이전트" > "./.claude/agents/my-own-agent.md"
  mkdir -p "./.claude/rules/custom"
  echo "# 사용자 보유 규칙" > "./.claude/rules/custom/team-style.md"

  # --force 없이 재실행: 충돌로 판정하지 않아야 한다
  local exit_code=0
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1 || exit_code=$?
  if ! assert_exit_code 0 "$exit_code" "exit code 0 (남의 파일은 충돌이 아님)"; then
    record_failure "$test_name" "대상 전용 파일을 충돌로 오판: exit=$exit_code"
    return 1
  fi

  # 남의 파일이 보존돼야 한다
  if [[ ! -f "./.claude/agents/my-own-agent.md" ]]; then
    record_failure "$test_name" "사용자 소유 에이전트가 삭제됨"
    return 1
  fi
  if [[ ! -f "./.claude/rules/custom/team-style.md" ]]; then
    record_failure "$test_name" "사용자 보유 규칙이 삭제됨"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T17: 커맨드 9종(의존 사슬 7종 + 독립 커맨드 2종)이 설치되고 의존 사슬이 닫히는지 확인
test_commands_installed() {
  local test_name="T17"
  local test_desc="커맨드 9종 설치 및 의존 사슬 완결"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  local command_name
  for command_name in prp-prd prp-plan prp-implement prp-pr prp-commit code-review env-update dashboard hub; do
    if [[ ! -f "./.claude/commands/$command_name.md" ]]; then
      record_failure "$test_name" "$command_name.md 미설치"
      return 1
    fi
  done

  # 설치된 커맨드가 참조하는 다른 커맨드가 모두 설치돼 있어야 한다 (사슬 완결)
  local referenced
  for referenced in $(grep -rhoE '/(prp-[a-z]+|code-review)\b' ./.claude/commands/ | sort -u | tr -d '/'); do
    if [[ ! -f "./.claude/commands/$referenced.md" ]]; then
      record_failure "$test_name" "참조되지만 미설치인 커맨드: $referenced"
      return 1
    fi
  done

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T18: 전역 커맨드와 다를 때 경고, 같을 때 안내 (--scope project)
test_global_command_overlap_report() {
  local test_name="T18"
  local test_desc="전역 커맨드 비교 보고"
  log_test_name "$test_name" "$test_desc"

  local sandbox sandbox_home
  sandbox=$(mktemp -d)
  sandbox_home=$(mktemp -d)
  trap "rm -rf '$sandbox' '$sandbox_home'" EXIT

  # 가짜 전역: 5개는 동일, prp-plan 만 다르게
  mkdir -p "$sandbox_home/.claude/commands"
  cp "$REPO_ROOT/commands"/*.md "$sandbox_home/.claude/commands/"
  echo "# 전역에서 수정됨" >> "$sandbox_home/.claude/commands/prp-plan.md"

  cd "$sandbox"
  local output
  output=$(HOME="$sandbox_home" "$INSTALL_SCRIPT" --scope project 2>&1)

  if ! echo "$output" | grep -q "전역 커맨드와 내용이 다릅니다.*prp-plan"; then
    record_failure "$test_name" "전역 불일치 경고에 prp-plan 이 없음"
    return 1
  fi
  # 우선순위 방향이 사실과 맞아야 한다: 커맨드는 전역 > 프로젝트 (skills 문서)
  if ! echo "$output" | grep -q "전역이 프로젝트보다 우선"; then
    record_failure "$test_name" "우선순위 안내가 없거나 방향이 틀림 (전역>프로젝트여야 함)"
    return 1
  fi
  if ! echo "$output" | grep -q "전역에 동일한 커맨드 8개"; then
    record_failure "$test_name" "동일 8개 안내가 없음"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T19: --scope user 는 대상이 곧 전역이므로 비교 보고를 생략한다
test_global_report_skipped_for_user_scope() {
  local test_name="T19"
  local test_desc="--scope user 는 전역 비교 생략"
  log_test_name "$test_name" "$test_desc"

  local sandbox sandbox_home
  sandbox=$(mktemp -d)
  sandbox_home=$(mktemp -d)
  trap "rm -rf '$sandbox' '$sandbox_home'" EXIT

  mkdir -p "$sandbox_home/.claude/commands"
  cp "$REPO_ROOT/commands"/*.md "$sandbox_home/.claude/commands/"
  echo "# 전역에서 수정됨" >> "$sandbox_home/.claude/commands/prp-plan.md"

  cd "$sandbox"
  local output
  output=$(HOME="$sandbox_home" "$INSTALL_SCRIPT" --scope user --force 2>&1)

  if echo "$output" | grep -q "전역"; then
    record_failure "$test_name" "--scope user 인데 전역 비교 메시지가 출력됨"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T20: Manifest 생성 확인
test_manifest_created_after_install() {
  local test_name="T20"
  local test_desc="Manifest 생성 및 기본 검증"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  # Manifest 파일 존재 확인
  if ! assert_file_exists "./.claude/.coding-env.json" "manifest 파일"; then
    record_failure "$test_name" "manifest 파일 미존재"
    return 1
  fi

  # Manifest 필드 검증 (grep 사용, jq 없음)
  local manifest_content
  manifest_content=$(cat "./.claude/.coding-env.json")

  if ! echo "$manifest_content" | grep -q '"version": 1'; then
    record_failure "$test_name" "version 필드 미발견 또는 잘못됨"
    return 1
  fi

  if ! echo "$manifest_content" | grep -q '"scope": "project"'; then
    record_failure "$test_name" "scope 필드 미발견 또는 값 잘못됨"
    return 1
  fi

  if ! echo "$manifest_content" | grep -q '"repo_path"'; then
    record_failure "$test_name" "repo_path 필드 미발견"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T21: Manifest 필드 완결성 및 dry-run 미생성
test_manifest_fields_complete() {
  local test_name="T21"
  local test_desc="Manifest 필드 완결성 및 dry-run 검증"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  local manifest_content
  manifest_content=$(cat "./.claude/.coding-env.json")

  # 필수 필드 확인
  if ! echo "$manifest_content" | grep -q '"installed_at"'; then
    record_failure "$test_name" "installed_at 필드 미발견"
    return 1
  fi

  if ! echo "$manifest_content" | grep -q '"installed_from_commit"'; then
    record_failure "$test_name" "installed_from_commit 필드 미발견"
    return 1
  fi

  if ! echo "$manifest_content" | grep -q '"target_base_dir"'; then
    record_failure "$test_name" "target_base_dir 필드 미발견"
    return 1
  fi

  if ! echo "$manifest_content" | grep -q '"files_count"'; then
    record_failure "$test_name" "files_count 필드 미발견"
    return 1
  fi

  # dry-run 시 manifest 미생성 확인
  local sandbox_dry
  sandbox_dry=$(mktemp -d)
  trap "rm -rf '$sandbox' '$sandbox_dry'" EXIT

  cd "$sandbox_dry"
  "$INSTALL_SCRIPT" --scope project --dry-run > /dev/null 2>&1

  if [[ -f "./.claude/.coding-env.json" ]]; then
    record_failure "$test_name" "--dry-run 시 manifest가 생성됨 (기대: 미생성)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T22: dashboard 템플릿 무결성 — LLM 지시문 방식이라 런타임 Edit 결과는 검증 대상이 아니고,
# 설치·문서 정합성만 자동 검증한다 (하위 검증 T22-1~T22-104).
test_dashboard_template_integrity() {
  local test_name="T22"
  local test_desc="dashboard 템플릿 무결성 (T22-1~T22-104)"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  local dashboard_command_file="./.claude/commands/dashboard.md"

  # T22-1: commands/dashboard.md 설치됨
  if ! assert_file_exists "$dashboard_command_file" "dashboard.md"; then
    record_failure "$test_name" "T22-1: dashboard.md 미설치"
    return 1
  fi

  # T22-2: 필수 셀렉터 6종이 템플릿에 모두 존재
  local required_selector
  for required_selector in dz-title dz-progress-bar dz-progress-pct dz-step- \
    dz-log dz-updated; do
    if ! grep -q "$required_selector" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-2: 셀렉터 미발견: $required_selector"
      return 1
    fi
  done

  # T22-3: 결과 배지 4종 CSS class 정의 존재
  local badge_class
  for badge_class in impl pass fail commit; do
    if ! grep -q "\.badge\.${badge_class}" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-3: 배지 class 미발견: .badge.$badge_class"
      return 1
    fi
  done

  # T22-4: 필터 라디오 3종과 CSS 규칙 존재
  if ! grep -q "dzf-review:checked" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-4: 필터 CSS 규칙(dzf-review:checked) 미발견"
    return 1
  fi
  if ! grep -q 'id="dzf-all"' "$dashboard_command_file" \
    || ! grep -q 'id="dzf-impl"' "$dashboard_command_file" \
    || ! grep -q 'id="dzf-review"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-4: 필터 라디오 3종 미발견"
    return 1
  fi

  # T22-5: install.sh 의 COMMANDS_FILE_COUNT 가 실제 파일 수와 일치 (재발 방지책)
  # 이번 변경처럼 커맨드를 추가하고 상수를 안 고치는 실수를 잡는 목적.
  local declared_count
  declared_count=$(grep -oE '^readonly COMMANDS_FILE_COUNT=[0-9]+' "$INSTALL_SCRIPT" | grep -oE '[0-9]+$')
  local actual_count
  actual_count=$(ls "$REPO_ROOT/commands"/*.md | wc -l | xargs echo)
  if ! assert_equals "$actual_count" "$declared_count" "COMMANDS_FILE_COUNT 일치"; then
    record_failure "$test_name" "T22-5: COMMANDS_FILE_COUNT=$declared_count, 실제 파일 수=$actual_count"
    return 1
  fi

  # T22-7: div.legend 컴포넌트가 템플릿에서 제거됐는지 확인 (사용자 요청, 회귀 방지)
  if grep -q 'class="legend"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-7: div.legend 가 여전히 템플릿에 남아있음"
    return 1
  fi

  # T22-8(역방향): 세션 구분 마커(session-head) 가 완전히 제거됐는지 확인 — 세션 탭 UI 전면 삭제
  if grep -q "session-head" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-8: session-head 세션 구분 마커가 여전히 남아있음"
    return 1
  fi

  # T22-9: log 절차가 파일 전체 Read 대신 grep+windowed Read 방식을 문서화했는지 확인
  # (가변 비용 회귀 방지 — 다시 "파일 전체를 Read"로 되돌아가지 않았는지 확인)
  if ! grep -q "파일 전체를 Read하지 않는다" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-9: log 절차의 windowed-read 최적화 문구 미발견"
    return 1
  fi

  # T22-10: 작업 추적 타이틀이 인라인 <b> 가 아니라 block 요소로 분리됐는지 확인
  # (필터 라디오와 같은 줄에 붙어 보이던 레이아웃 버그의 회귀 방지)
  if ! grep -q 'class="log-title"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-10: log-title 블록 요소 미발견"
    return 1
  fi

  # T22-12: log 절차가 깨진 완전일치 grep 으로 퇴행하지 않았는지 확인 (이번 라운드에서 가장 중요한 테스트).
  # #dz-log 여는 태그가 data-server-port 를 갖는 순간 완전일치는 영원히 매칭에 실패하므로
  # 옛 패턴의 부활과 새 패턴의 누락을 양방향으로 막는다.
  if grep -q "grep -n '<ul class=\"log\" id=\"dz-log\">'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-12: 깨진 완전일치 grep 패턴이 여전히 남아있음"
    return 1
  fi
  if ! grep -q "grep -n 'id=\"dz-log\"'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-12: 부분일치 grep 패턴 미발견"
    return 1
  fi

  # T22-14(역방향): 세션 탭 CSS 골격과 삽입 마커가 완전히 제거됐는지 확인
  if grep -q 'label\[for\^="dzs-"\]' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-14: 세션 탭 라벨 CSS 골격이 여전히 남아있음"
    return 1
  fi
  if grep -q 'DZ:SESSION-RULES' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-14: DZ:SESSION-RULES 삽입 마커가 여전히 남아있음"
    return 1
  fi

  # T22-18(역방향): 세션별 .entry 필터 규칙(#dzs-*)이 완전히 제거됐는지 확인
  if grep -q '#dz-log > li:not(\[data-session=' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-18: 세션 필터가 옛 '> li' 패턴으로 되돌아감"
    return 1
  fi
  if grep -q '#dzs-1:checked ~ #dz-log .entry:not(\[data-session="1"\])' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-18: 세션별 .entry 필터 규칙(#dzs-1)이 여전히 남아있음"
    return 1
  fi

  # T22-19: 그룹 문법이 호출 규약에 문서화됨 (「그룹 × 단계」 통일 모델, 회귀 방지)
  if ! grep -qF '그룹A:단계1,단계2' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-19: 그룹 문법 예시(그룹A:단계1,단계2) 미발견"
    return 1
  fi

  # T22-20: 하위 호환 정규화 규칙 존재 — 선형 호출을 그룹 모드로 오해석하지 않아야 한다
  if ! grep -q '이름 없는 그룹 1개' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-20: '이름 없는 그룹 1개' 정규화 규칙 미발견"
    return 1
  fi

  # T22-21: 혼합 문법 시 중단 규칙 존재 — 오타를 추측 해석하는 퇴행 방지
  if ! grep -q '섞여 있다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-21: 혼합 문법 중단 규칙(섞여 있다) 미발견"
    return 1
  fi

  # T22-22: 매트릭스 셀렉터 2종 존재 (dz-cell-, dz-group-) — 셀렉터 계약 누락 방지
  if ! grep -q 'dz-cell-' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-22: dz-cell- 셀렉터 미발견"
    return 1
  fi
  if ! grep -q 'dz-group-' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-22: dz-group- 셀렉터 미발견"
    return 1
  fi

  # T22-23: 매트릭스 CSS 가 템플릿에 상주 — init 이 CSS 를 주입하는 방식으로 퇴행하지 않아야 한다
  if ! grep -q 'table\.matrix{' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-23: table.matrix{ CSS 규칙 미발견"
    return 1
  fi

  # T22-24: 선형 자산 비퇴화 — 매트릭스로 통합하며 선형 화면을 없애지 않아야 한다 (확정 방향 1)
  if ! grep -qF '<ol class="steps" id="dz-steps">' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-24: 선형 단계 목록 <ol id=\"dz-steps\"> 미발견"
    return 1
  fi
  if ! grep -q 'dz-step-{n}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-24: dz-step-{n} 패턴 미발견"
    return 1
  fi

  # T22-25: step 그룹 인자 문법 문서화 — 그룹 모드 갱신 방법이 불명확해지는 회귀 방지
  if ! grep -qF 'step <g>.<p>' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-25: step <g>.<p> 문법 미발견"
    return 1
  fi

  # T22-26: 결정적 완료 계수 명령 존재 — <style> 줄까지 세는 헐거운 패턴으로 퇴행 방지
  if ! grep -qF 'dz-cell-.*data-state="done"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-26: 결정적 완료 계수 명령(dz-cell-.*data-state=\"done\") 미발견"
    return 1
  fi

  # T22-27: 색 토큰 불변 — 새 디자인 시스템 도입(요청 위반) 방지, 완전 일치로 확인
  if ! grep -qF ':root{--ink:#172033;--muted:#5E6B7D;--line:#D9E2EC;--soft:#F4F7FB;--blue:#1E5AA8;--navy:#12335B;--green:#1F8A70;--orange:#F59E0B;--red:#C2410C;}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-27: :root 색 토큰 줄이 변경됨"
    return 1
  fi

  # T22-28: 게이트 전용 개념 미신설 — 별도 게이트 컴포넌트 부활(확정 방향 5 위반) 방지.
  # 이 검증은 매칭되면 실패다(역방향 assertion) — dz-gate- 셀렉터가 존재해서는 안 된다.
  if grep -q 'dz-gate-' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-28: dz-gate- 전용 셀렉터가 신설됨(게이트는 단계 1개 그룹으로 표현해야 함)"
    return 1
  fi

  # T22-29: file:// 리로드 경로 비퇴화 — if(!isServed){...} 분기 자체와 그 판정식이 남아있는지
  # 확인한다(location.reload()·visibilitychange 만 보면 폴링/PiP 분기의 동일 문자열에도 매칭돼
  # 분기 전체를 지워도 통과하는 결함이 있었다).
  if ! grep -qF "if(!isServed){" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-29: if(!isServed){ 분기 미발견"
    return 1
  fi
  if ! grep -qF "location.protocol === 'http:'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-29: isServed 판정식(location.protocol === 'http:') 미발견"
    return 1
  fi

  # T22-30: 폴링 경로 존재 — 미구현 / 브라우저 캐시로 갱신이 멈추는 퇴행 방지
  if ! grep -q 'DOMParser' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-30: DOMParser 미발견"
    return 1
  fi
  if ! grep -qF "cache:'no-store'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-30: cache:'no-store' 미발견"
    return 1
  fi

  # T22-31: 기능 감지 존재 — 감지 없이 호출해 미지원 브라우저에서 예외가 나는 퇴행 방지
  if ! grep -qF "'documentPictureInPicture' in window" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-31: documentPictureInPicture 기능 감지 미발견"
    return 1
  fi

  # T22-32: 자동 진입 금지 — 주석 문구만으로는 실제로 setTimeout/setInterval 로 자동 open 을
  # 넣어도 통과하는 결함이 있었다. requestWindow 호출이 정확히 1곳(click 리스너 안)뿐이고,
  # 타이머에서 호출되지 않는지까지 함께 확인한다.
  if ! grep -q '자동 재시도하지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-32: 자동 재시도 금지 문구 미발견"
    return 1
  fi
  if [[ "$(grep -c 'requestWindow' "$dashboard_command_file")" -ne 1 ]]; then
    record_failure "$test_name" "T22-32: requestWindow 호출이 정확히 1곳이 아님(click 리스너 밖에서 열릴 가능성)"
    return 1
  fi
  if grep -qE 'setTimeout\(.*requestWindow|setInterval\(.*requestWindow' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-32: setTimeout/setInterval 에서 requestWindow 를 호출함(자동 진입 회귀)"
    return 1
  fi

  # T22-33: 스타일시트 복사 — PiP 창이 무스타일로 뜨는 퇴행 방지(CSS 미상속은 실측된 제약)
  if ! grep -qF "querySelectorAll('style')" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-33: querySelectorAll('style') 미발견"
    return 1
  fi
  if ! grep -q 'head.appendChild' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-33: head.appendChild 미발견"
    return 1
  fi

  # T22-34: 이동 방식 + 복귀 경로 — 복제 방식으로 바꾸거나 복귀를 빠뜨려 opener 가 영구히 비는 퇴행 방지
  if ! grep -qF 'body.appendChild(wrap)' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-34: body.appendChild(wrap) 미발견"
    return 1
  fi
  if ! grep -q 'pagehide' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-34: pagehide 미발견"
    return 1
  fi
  if ! grep -qF 'insertBefore(wrap, pipButton)' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-34: insertBefore(wrap, pipButton) 미발견(PiP 복귀 경로 미검증)"
    return 1
  fi

  # T22-35: 서버 바인딩 안전 — .claude 를 모든 인터페이스에 노출하는 회귀 방지(역방향 assertion 포함)
  if ! grep -qF -- '--bind 127.0.0.1' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-35: --bind 127.0.0.1 미발견"
    return 1
  fi
  if grep -q '0\.0\.0\.0' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-35: 0.0.0.0 바인딩 문자열이 발견됨"
    return 1
  fi

  # T22-36: serve 가 인터페이스에 노출 — 절차만 있고 규약·힌트에 없어 아무도 못 쓰는 퇴행 방지
  if ! head -4 "$dashboard_command_file" | grep -q 'serve'; then
    record_failure "$test_name" "T22-36: argument-hint 에 serve 미발견"
    return 1
  fi
  if ! grep -q '/dashboard serve' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-36: /dashboard serve 언급 미발견"
    return 1
  fi

  # T22-37: 플로팅 UI 가 .wrap 바깥에 있는지 — 템플릿에서의 마지막 등장 위치로 판정한다.
  # (.wrap 안에 있으면 PiP 창으로 같이 이동해 버튼으로 창을 닫을 수 없게 된다)
  local pip_button_line wrap_end_line
  pip_button_line=$(grep -n 'id="dz-pip-btn"' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  wrap_end_line=$(grep -n 'id="dz-updated"' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  if [[ -z "$pip_button_line" || -z "$wrap_end_line" || "$pip_button_line" -lt "$wrap_end_line" ]]; then
    record_failure "$test_name" "T22-37: 플로팅 버튼이 .wrap 바깥(#dz-updated 뒤)에 있지 않음"
    return 1
  fi

  # T22-38: grep 유일성 불변식 — 스크립트가 [id="dz-log"] 형태를 쓰면 log·step 의 grep 앵커가
  # 줄 수를 잘못 세어 절차 전체가 깨진다(역방향 assertion).
  if grep -q '\[id="dz-' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-38: [id=\"dz- 형태의 셀렉터 문자열이 발견됨"
    return 1
  fi

  # T22-39: 로그 카드 식별자 존재 — id 없이 구조 셀렉터(:nth-of-type)로 되돌아가는 회귀 방지
  if ! grep -qF 'id="dz-log-card"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-39: id=\"dz-log-card\" 미발견"
    return 1
  fi

  # T22-40: PiP 압축 규칙 존재 — 압축 뷰 자체의 유실 방지
  if ! grep -qF 'body.dz-pip #dz-log-card{display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-40: body.dz-pip #dz-log-card{display:none} 미발견"
    return 1
  fi

  # T22-41: 로그 앵커 비충돌 — log 절차 0-a 의 grep 앵커 `id="dz-log"` 는 닫는 따옴표까지 포함하므로
  # id="dz-log-card" 에 걸리지 않아야 한다. 걸리면 앵커가 2줄을 매칭해 log 절차 전체가 깨진다.
  # (전체 카운트 방식은 이 파일이 마크다운 산문 안에서 'id="dz-log"' 를 예시로 여러 번 인용하기 때문에
  # 쓸 수 없다 — 템플릿 전문 구간만 대상으로 좁혀서 충돌 가능성을 직접 확인한다.)
  if awk '/^## 템플릿 전문/,/^```$/' "$dashboard_command_file" | grep -n 'id="dz-log"' | grep -q 'dz-log-card'; then
    record_failure "$test_name" "T22-41: 로그 카드 id 가 log 절차의 grep 앵커와 충돌함"
    return 1
  fi
  if [[ "$(awk '/^## 템플릿 전문/,/^```$/' "$dashboard_command_file" | grep -c 'id="dz-log"')" -ne 1 ]]; then
    record_failure "$test_name" "T22-41: 템플릿 안 id=\"dz-log\" 매칭 줄 수가 1이 아님(로그 카드 id 충돌 가능성)"
    return 1
  fi

  # T22-42: CSS 로만 숨김 — 스크립트가 카드를 DOM 에서 떼어내는 방식으로 퇴행하면 폴링이
  # 세션 변경으로 오판해 무한 리로드에 빠진다(역방향 assertion).
  if grep -qE '(getElementById|querySelector)\([^)]*dz-log-card' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-42: 스크립트가 dz-log-card 를 getElementById/querySelector 로 참조함"
    return 1
  fi

  # T22-43: 로그 동기화 비퇴화 — 압축을 넣으며 로그 동기화를 함께 지우지 않았는지 확인
  if ! grep -qF 'function syncLog' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-43: function syncLog 미발견"
    return 1
  fi
  if ! grep -qF "live.innerHTML = next.innerHTML" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-43: live.innerHTML = next.innerHTML 미발견"
    return 1
  fi

  # T22-44: 단계 상세 마크업·CSS — 상세 span 또는 빈 값 숨김 규칙 유실(빈 회색 줄 잔존) 방지
  if ! grep -qF 'class="step-detail"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-44: class=\"step-detail\" 미발견"
    return 1
  fi
  if ! grep -qF '.step-detail:empty{display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-44: .step-detail:empty{display:none} 미발견"
    return 1
  fi

  # T22-45: PiP 는 활성 상세만 — 요청 1·2 를 잇는 규칙의 유실(좁은 창이 상세로 도배) 방지
  if ! grep -qF 'body.dz-pip ol.steps li:not(.active) .step-detail' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-45: body.dz-pip ol.steps li:not(.active) .step-detail 미발견"
    return 1
  fi

  # T22-46: 상세 규약 문서화 — 절차만 있고 규약에 없어 아무도 못 쓰는 회귀, 불변식 3 문구 유실 방지
  if ! head -4 "$dashboard_command_file" | grep -q '상세'; then
    record_failure "$test_name" "T22-46: argument-hint 에 '상세' 미발견"
    return 1
  fi
  if ! grep -qF 'step <n> <done|active|wait> ["상세"]' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-46: 호출 규약에 step <n> <done|active|wait> [\"상세\"] 미발견"
    return 1
  fi
  if ! grep -q '줄바꿈을 넣지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-46: '줄바꿈을 넣지 않는다' 문구 미발견"
    return 1
  fi

  # T22-47: PiP 창 높이 콘텐츠 맞춤 — 고정 620px 요청 후 리사이즈를 안 하면 압축 뷰에서
  # 하단에 빈 여백이 남는 회귀(실제 사용자 리포트)가 재발한다.
  if ! grep -qF 'function resizePipToFit(){' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-47: function resizePipToFit 미발견"
    return 1
  fi
  if ! grep -qF 'pipWindow.resizeTo(PIP_WIDTH,' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-47: resizeTo 호출 미발견"
    return 1
  fi
  if ! grep -qF 'resizePipToFit();' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-47: apply() 안에서 resizePipToFit 호출 미발견"
    return 1
  fi

  # T22-48: 구현 세부 작업 슬롯 셀렉터 4종 존재 — 슬롯 자체의 유실 방지
  if ! grep -qF 'id="dz-impl-card"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-48: id=\"dz-impl-card\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-impl-tasks"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-48: id=\"dz-impl-tasks\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-impl-count"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-48: id=\"dz-impl-count\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-impl-{k}"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-48: id=\"dz-impl-{k}\" 미발견"
    return 1
  fi

  # T22-49: 자동 숨김 규칙 존재 — 빈 카드가 모든 세션에 노출되는 회귀 방지(확정 사항 3 위반)
  if ! grep -qF '#dz-impl-card:not(:has(#dz-impl-tasks li)){display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-49: 구현 세부 작업 카드 자동 숨김 규칙 미발견"
    return 1
  fi

  # T22-50: 레이아웃 CSS 재사용 — 중복 정의가 생기면 매크로 목록과 세부 목록이 갈라진다(역방향 assertion).
  if ! grep -qF '<ol class="steps" id="dz-impl-tasks">' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-50: <ol class=\"steps\" id=\"dz-impl-tasks\"> 미발견"
    return 1
  fi
  if grep -q 'ol\.impl-tasks' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-50: ol.impl-tasks 레이아웃 규칙이 중복 정의됨"
    return 1
  fi

  # T22-51: 폴링 동기화 추가 — 카드가 동기화에서 빠지면 http://·PiP 에서 영구히 stale 된다(설계 결정 5).
  if ! grep -qF 'function syncImplCard(fresh){' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-51: function syncImplCard(fresh){ 미발견"
    return 1
  fi
  if ! grep -qF 'syncImplCard(fresh);' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-51: apply() 안에서 syncImplCard 호출 미발견"
    return 1
  fi

  # T22-52: CSS 로만 숨김 — 스크립트가 impl 카드를 DOM 에서 떼어내거나 인라인 스타일로 숨기면
  # 폴링의 outerHTML 대입 대상이 사라져 카드가 영구히 되살아나지 않는다(역방향 assertion).
  if grep -n 'dz-impl-card' "$dashboard_command_file" | grep -qE 'remove\(|style\.display'; then
    record_failure "$test_name" "T22-52: 스크립트가 dz-impl-card 를 DOM/인라인 스타일로 조작함"
    return 1
  fi

  # T22-53: 기존 시각화 동기화 비퇴화 — 새 동기화를 넣으며 기존 함수를 개조·파손하지 않았는지 확인
  if ! grep -qF "querySelector('#dz-steps,#dz-matrix')" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-53: querySelector('#dz-steps,#dz-matrix') 미발견"
    return 1
  fi

  # T22-54: 매크로 진행률 비침해 문구 — 세부 완료가 매크로 분모에 섞여 step 전이 산술이 무너지는 회귀 방지(불변식 6)
  if ! grep -q '구현 세부 작업의 상태 변화는 매크로 진행률을 바꾸지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-54: 매크로 진행률 비침해 문구 미발견"
    return 1
  fi

  # T22-55: 데이터 출처 한계 문구 — 사라지면 실시간 진행률로 오인된다(확정 사항 2)
  if ! grep -q '서브에이전트 내부의 실시간 진행률이 아니다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-55: '서브에이전트 내부의 실시간 진행률이 아니다' 문구 미발견"
    return 1
  fi
  if ! grep -q '디스패치' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-55: '디스패치' 문구 미발견"
    return 1
  fi

  # T22-56: 병렬 active 허용 문구 — 단일 활성 가정이 슬며시 들어오면 이 패널의 존재 이유가 사라진다
  if ! grep -q '동시에 여러 항목이 active 일 수 있다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-56: '동시에 여러 항목이 active 일 수 있다' 문구 미발견"
    return 1
  fi

  # T22-57: 규약 노출 — 절차만 있고 규약에 없으면 아무도 못 쓴다
  if ! head -4 "$dashboard_command_file" | grep -q 'impl set'; then
    record_failure "$test_name" "T22-57: argument-hint 에 'impl set' 미발견"
    return 1
  fi
  if ! grep -qF '/dashboard impl <k> <done|active|wait> ["상세"]' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-57: 호출 규약에 /dashboard impl <k> <done|active|wait> [\"상세\"] 미발견"
    return 1
  fi

  # T22-58: 가드 문구 + PiP 미숨김 — 재호출이 진행 상태를 날리는 회귀 / 곁눈질 화면에서 가장 값진
  # 카드를 숨기는 규칙이 몰래 추가되는 회귀를 각각 막는다(뒤쪽은 역방향 assertion, 설계 결정 6).
  if ! grep -q '이미 목록이 있으면 덮어쓰지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-58: '이미 목록이 있으면 덮어쓰지 않는다' 가드 문구 미발견"
    return 1
  fi
  if grep -qF 'body.dz-pip #dz-impl-card{display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-58: PiP 에서 impl 카드를 숨기는 규칙이 추가됨"
    return 1
  fi

  # T22-61: 호출 규약 비대화 방지 (최우선, 역방향) — 커밋 a6966aa 는 "현재 위치/다음 단계" 카드를
  # 위해 step 에 선택 인자 3개를 요구했다가 그 무게 때문에 기능째 제거됐다. 「지금」 카드는 순수
  # 파생 뷰이므로 dz-current 계열 셀렉터나 규약상의 위치/다음단계 인자가 다시 나타나면 같은
  # 실패의 재발이다.
  if grep -qE 'dz-current|"현재 위치"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-61: 제거된 dz-current 계열 셀렉터·인자가 부활함"
    return 1
  fi
  if ! grep -qF 'step <n> <done|active|wait> ["상세"]' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-61: step 호출 규약 원형 미발견"
    return 1
  fi

  # T22-68: 자동 발행 절 제목 존재 — 절차 자체가 유실되면 init 의 두 분기가 참조할 대상이 없다.
  if ! grep -qF '## 자동 발행 — `init` 의 공통 하위 절차' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-68: 자동 발행 절 제목 미발견"
    return 1
  fi

  # T22-69: file:// 폴백 생존(최우선) — 서버 실패 시 URL 을 아무것도 못 주는 순수 퇴행을 막는다
  # (설계 결정 4).
  if ! grep -qF 'file://' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-69: file:// 문자열이 문서에서 사라짐"
    return 1
  fi
  # sed | grep -q 로 직접 파이프하지 않는다 — grep -q 가 매칭 즉시 종료하면 앞단 sed 가
  # SIGPIPE 를 받고, pipefail 이 그 종료 상태를 파이프 전체 결과로 흘려 매칭이 있어도
  # 실패로 보이는 경우가 있다(bash 3.2 실측). 다른 sed 범위 검사(T22-81 등)와 같은 관례로
  # 변수에 먼저 담아 그 안전한 값을 grep 한다.
  local autopublish_section
  autopublish_section=$(sed -n '/^## 자동 발행/,/^## `serve`/p' "$dashboard_command_file")
  if ! grep -q '폴백' <<< "$autopublish_section"; then
    record_failure "$test_name" "T22-69: 자동 발행 절 안에 폴백 표기 미발견"
    return 1
  fi

  # T22-70: init 이 마지막 단계에서 자동 발행을 참조 — 링크가 없으면 발행 없이 절차가 끝난다.
  # 범위를 init 절로 좁히는 이유는 자동 발행 절 자신의 산문에서 오탐이 나기 때문이다.
  local init_section_autopublish_count
  init_section_autopublish_count=$(sed -n '/^## `init`/,/^## `step`/p' "$dashboard_command_file" | grep -cF '[자동 발행]')
  if [[ "$init_section_autopublish_count" -lt 1 ]]; then
    record_failure "$test_name" "T22-70: init 절 범위에서 '[자동 발행]' 링크 미발견"
    return 1
  fi

  # T22-71: 포트 스캔 계약 3토큰 — 유실되면 메인 세션이 스캔 출력을 임의 해석하게 된다.
  local scan_token
  for scan_token in REUSE FREE NONE; do
    if ! grep -qF "$scan_token" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-71: 포트 스캔 토큰 미발견: $scan_token"
      return 1
    fi
  done

  # T22-72: REUSE 가 FREE 보다 우선 — 없으면 같은 프로젝트에 서버가 계속 쌓인다(설계 결정 2).
  if ! grep -qF '`REUSE` 가 `FREE` 보다 우선한다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-72: REUSE 우선순위 문구 미발견"
    return 1
  fi

  # T22-73: 바인딩 안전(T22-35 의 확장, 역방향+정방향) — 자동 경로가 --bind 127.0.0.1 을 빼먹고
  # .claude 를 LAN 에 노출하는 회귀를 막는다.
  local bind_occurrence_count
  bind_occurrence_count=$(grep -c -- '--bind 127.0.0.1' "$dashboard_command_file")
  if [[ "$bind_occurrence_count" -lt 2 ]]; then
    record_failure "$test_name" "T22-73: --bind 127.0.0.1 등장 횟수가 2 미만"
    return 1
  fi
  if grep -q '0\.0\.0\.0' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-73: 0.0.0.0 바인딩 문자열이 발견됨"
    return 1
  fi

  # T22-74: 실패가 init 을 중단시키지 않음 — 발행 실패가 착수 자체를 막으면 안 된다(설계 결정 7).
  if ! grep -qF '이 절차의 어떤 실패도 `init` 을 중단시키지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-74: 실패 비차단 문구 미발견"
    return 1
  fi

  # T22-75: SSH 가드 — 원격 세션에서 엉뚱한 머신의 브라우저를 여는 사고를 막는다(설계 결정 6).
  if ! grep -qF 'SSH_CONNECTION' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-75: SSH_CONNECTION 가드 미발견"
    return 1
  fi

  # T22-76: 브라우저 열기 무재시도 — 열기 실패 시 무한 재시도로 이어지는 회귀를 막는다.
  if ! grep -qF '재시도하지 않고' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-76: 재시도 금지 문구 미발견"
    return 1
  fi

  # T22-77: step/log/impl 비발행 — 갱신 명령마다 탭이 열리는 최악의 회귀를 막는다(확정 사항 3).
  if ! grep -qF '서버를 띄우지도, 브라우저를 열지도 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-77: step·log·impl 비발행 문구 미발견"
    return 1
  fi

  # T22-78: serve 의 명시 포트 무추측 규칙 생존(역방향) — 자동 스캔을 넣으며 명시 포트의
  # 무추측 규칙까지 지워 버리는 회귀를 막는다.
  if ! grep -qF '다른 포트를 **추측해서 재시도하지 말고**' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-78: serve 의 명시 포트 무추측 규칙 미발견"
    return 1
  fi

  # T22-79: stop 안내에 포트 포함 — 자동 경로가 8792 를 썼는데 안내가 8791 을 죽이라고 하면
  # 엉뚱한 서버를 끈다.
  if ! grep -qF '/dashboard serve stop {포트}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-79: /dashboard serve stop {포트} 미발견"
    return 1
  fi

  # T22-80: 템플릿의 #dz-log 여는 태그에 포트 각인 슬롯이 비어 있는 상태로 존재하는지 확인 —
  # data-server-port 가 유실되면 이 한 줄이 잡아낸다.
  if ! grep -qF 'id="dz-log" data-server-port=""' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-80: #dz-log 각인 슬롯(data-server-port) 미발견"
    return 1
  fi

  # T22-81: 각인 "호출 지점"이 자동 발행 3단계와 serve 3·4단계 모두에 있는지 확인한다.
  # data-server-port 라는 리터럴은 공통 절차(「포트 각인」) 본문에도 나오므로 그것만 세면
  # 호출부가 통째로 삭제돼도 통과해 버린다(실측 회귀: 호출부 삭제 후에도 예전 버전은 통과했다) —
  # 그래서 [포트 각인] 호출 링크 자체를 앵커로 쓴다. 한쪽만 유실돼도 "자동으로 뜬 서버" 또는
  # "수동 serve 서버" 중 하나가 영영 안 죽는다(요구사항 3).
  # 카운트 임계값 방식은 무관한 편집이 카운트를 채우면 조용히 무력해진다(R1 회귀 재현으로
  # 확인됨: MEDIUM-2 수정이 serve 4단계의 [포트 각인] 참조를 1개에서 2개로 늘려, "serve 절
  # 전체에서 2개 이상"이라는 임계값이 3단계(기동 시) 각인이 통째로 삭제돼도 4단계 2개만으로
  # 충족돼 버렸다). 그래서 호출 지점마다 범위를 쪼개 각각 최소 1회를 확인한다.
  local autopublish_call_section serve_start_section serve_stop_section
  autopublish_call_section=$(sed -n '/^### 3\. URL 확정과 포트 각인/,/^### 4\./p' "$dashboard_command_file")
  if [[ -z "$autopublish_call_section" ]]; then
    record_failure "$test_name" "T22-81: 「자동 발행」 3단계(URL 확정과 포트 각인) 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if ! grep -qF '[포트 각인]' <<< "$autopublish_call_section"; then
    record_failure "$test_name" "T22-81: 「자동 발행」 3단계에 [포트 각인] 호출 없음(자동으로 뜬 서버가 영영 안 죽는 회귀)"
    return 1
  fi
  serve_start_section=$(sed -n '/^3\. 아래를 \*\*백그라운드\*\*/,/^4\. `stop`/p' "$dashboard_command_file")
  if [[ -z "$serve_start_section" ]]; then
    record_failure "$test_name" "T22-81: serve 3단계(기동) 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if ! grep -qF '[포트 각인]' <<< "$serve_start_section"; then
    record_failure "$test_name" "T22-81: serve 3단계(기동 성공 시)에 [포트 각인] 호출 없음(수동 serve 서버가 영영 안 죽는 회귀)"
    return 1
  fi
  serve_stop_section=$(sed -n '/^4\. `stop`/,/^5\. 위 \[자동 발행\]/p' "$dashboard_command_file")
  if [[ -z "$serve_stop_section" ]]; then
    record_failure "$test_name" "T22-81: serve 4단계(stop) 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if ! grep -qF '[포트 각인]' <<< "$serve_stop_section"; then
    record_failure "$test_name" "T22-81: serve 4단계(stop 시)에 [포트 각인] 호출 없음(각인 해제 누락 — 낡은 각인이 다른 프로젝트 서버를 끄는 회귀)"
    return 1
  fi

  # T22-82: log 절에 자동 종료 로직과 commit 전용 분기 조건이 함께 존재하는지 확인.
  local log_section
  log_section=$(sed -n '/^## `log`/,/^## 자동 발행/p' "$dashboard_command_file")
  if ! grep -qF 'pkill -f "http.server' <<< "$log_section"; then
    record_failure "$test_name" "T22-82: log 절에서 pkill 자동 종료 로직 미발견"
    return 1
  fi
  if ! grep -qF '첫 인자가 `commit` 일 때만' <<< "$log_section"; then
    record_failure "$test_name" "T22-82: log 절에서 commit 전용 분기 조건 미발견"
    return 1
  fi

  # T22-83(역방향): 종료 로직이 step·impl 절로 번지지 않았는지 확인. T22-77(비발행)의 대칭.
  # 역방향 테스트는 범위 추출이 실패(앵커 유실)하면 grep -q 가 그냥 실패해 "조용히 통과"해
  # 버리므로, 범위가 비어 있지 않은지부터 먼저 확인한다.
  local step_impl_section
  step_impl_section=$(sed -n '/^## `step`/,/^## `log`/p' "$dashboard_command_file")
  if [[ -z "$step_impl_section" ]]; then
    record_failure "$test_name" "T22-83: step·impl 절 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if grep -q 'pkill' <<< "$step_impl_section"; then
    record_failure "$test_name" "T22-83: step·impl 절 범위에 pkill 이 번져 있음"
    return 1
  fi

  # T22-84(역방향): 불변식 8 — <script> 블록은 data-server-port 를 읽지도 쓰지도 않는다.
  local script_block
  script_block=$(sed -n '/^<script>/,/<\/script>/p' "$dashboard_command_file")
  if [[ -z "$script_block" ]]; then
    record_failure "$test_name" "T22-84: <script> 블록 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if grep -q 'data-server-port' <<< "$script_block"; then
    record_failure "$test_name" "T22-84: <script> 블록이 data-server-port 를 참조함(불변식 8 위반)"
    return 1
  fi

  # T22-85(역방향): 요구사항 2의 유일한 보증 — poll() 실패 경로가 PiP 창을 닫거나 리로드하면
  # "커밋 직전 화면에서 고정"이라는 목표가 깨진다.
  local poll_body
  poll_body=$(sed -n '/function poll(){/,/setInterval(poll,/p' "$dashboard_command_file")
  if [[ -z "$poll_body" ]]; then
    record_failure "$test_name" "T22-85: poll() 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if grep -q 'close()\|location.reload' <<< "$poll_body"; then
    record_failure "$test_name" "T22-85: poll() 실패 경로에서 close()/location.reload 발견 — PiP 고정 회귀"
    return 1
  fi

  # T22-86: sleep 6 지연과 그 근거(POLL_INTERVAL_MS) — 지연을 "불필요한 대기"로 오해해
  # 지우면 커밋 화면이 PiP 에 닿지 못한다. log 절 범위로 좁혀서 검사한다(파일 전역이면
  # 이 지연이 log commit 경로 밖으로 옮겨져도 통과해 버린다).
  if ! grep -qF 'sleep 6 && pkill' <<< "$log_section"; then
    record_failure "$test_name" "T22-86: log 절 범위에서 sleep 6 && pkill 미발견"
    return 1
  fi
  if ! grep -qF 'POLL_INTERVAL_MS' <<< "$log_section"; then
    record_failure "$test_name" "T22-86: log 절 범위에서 POLL_INTERVAL_MS 근거 문구 미발견"
    return 1
  fi

  # T22-87: 종료 코드 1(이미 꺼진 서버) 비에러 처리 문구 — 없으면 커밋 턴마다 불필요한
  # 에러 보고가 발생한다(요구사항 4).
  if ! grep -qF '종료 코드 1' <<< "$log_section" && ! grep -qF '에러가 아니다' <<< "$log_section"; then
    record_failure "$test_name" "T22-87: log 절 범위에서 '종료 코드 1' 또는 '에러가 아니다' 문구 미발견"
    return 1
  fi

  # T22-91(역방향): 세션 탭 UI 잔재 전무 확인 — data-current-session·data-session=·
  # sessionTabsChanged·dzs- 중 어느 문자열도 파일에 남아있지 않아야 한다.
  local session_relic
  for session_relic in 'data-current-session' 'data-session=' 'sessionTabsChanged' 'dzs-'; do
    if grep -qF -- "$session_relic" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-91: 세션 탭 잔재 발견: $session_relic"
      return 1
    fi
  done

  # T22-92(역방향+정방향): 부제(#dz-subtitle) 잔재 전무 확인 — 셀렉터·마크업이 모두 사라지고
  # 동적 셀렉터 표 제목이 6종으로 갱신됐는지 함께 본다.
  if grep -qF 'dz-subtitle' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-92: dz-subtitle 잔재 발견"
    return 1
  fi
  if grep -qF 'class="sub"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-92: class=\"sub\" 잔재 발견"
    return 1
  fi
  if ! grep -qF '동적(치환 대상) — 6 셀렉터' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-92: 동적 셀렉터 표 제목이 6 셀렉터로 갱신되지 않음"
    return 1
  fi

  # T22-93(정방향+역방향): init 이 단일 분기인지 확인 — 「이미 존재하면」 분기가 없고,
  # rm -f 로 항상 새로 시작한다는 근거가 init 절 범위 안에 있어야 한다.
  local init_section
  init_section=$(sed -n '/^## `init`/,/^## `step`/p' "$dashboard_command_file")
  if [[ -z "$init_section" ]]; then
    record_failure "$test_name" "T22-93: init 절 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if grep -qF '이미 존재하면' <<< "$init_section"; then
    record_failure "$test_name" "T22-93: init 절에 '이미 존재하면' 분기가 남아있음"
    return 1
  fi
  if ! grep -qF 'rm -f .claude/dashboard.html' <<< "$init_section"; then
    record_failure "$test_name" "T22-93: init 절에 rm -f .claude/dashboard.html 미발견"
    return 1
  fi
  if ! grep -qF '읽지 않은 기존 파일을 덮어쓰지 못한다' <<< "$init_section"; then
    record_failure "$test_name" "T22-93: Write 도구 제약 근거 문구 미발견"
    return 1
  fi

  # T22-94(정방향+역방향): 브라우저 열기 개정 — 자동 발행 4번 범위에 탭 활성화(전면) 지시가
  # 있고, open -g(백그라운드) 옵션이 어디에도 없어야 한다.
  local browser_open_section
  browser_open_section=$(sed -n '/^### 4\. 브라우저 열기/,/^### 5\./p' "$dashboard_command_file")
  if [[ -z "$browser_open_section" ]]; then
    record_failure "$test_name" "T22-94: 브라우저 열기 절 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  if ! grep -qF '전면으로 올리는' <<< "$browser_open_section"; then
    record_failure "$test_name" "T22-94: 탭 활성화(전면) 지시 미발견"
    return 1
  fi
  if grep -qF 'open -g' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-94: open -g(백그라운드) 옵션 문자열 발견"
    return 1
  fi

  # T22-96(역방향): 「지금」 카드 잔재 전무 확인 — dz-now-card·renderNowCard·data-started-at·
  # now-row 중 어느 문자열도 파일에 남아있지 않아야 한다(카드 자체를 제거하기로 한 결정).
  local now_card_relic
  for now_card_relic in 'dz-now-card' 'dz-now-elapsed' 'dz-now-since' 'dz-now-next' 'renderNowCard' 'data-started-at' 'now-row' 'now-label' 'now-value' 'now-title'; do
    if grep -qF -- "$now_card_relic" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-96: 「지금」 카드 잔재 발견: $now_card_relic"
      return 1
    fi
  done

  # T22-97(R1): body.dz-embedded #dz-pip-btn CSS 규칙 존재 — 허브 모달 안에서 플로팅 버튼을
  # 숨기는 규칙 자체가 없으면 R1 전체가 죽어 있다.
  if ! grep -qF 'body.dz-embedded #dz-pip-btn' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-97: body.dz-embedded #dz-pip-btn CSS 규칙 미발견"
    return 1
  fi

  # T22-98(R1): 임베드 판정식 — self !== top 이 없으면 늘 false 로 오판정한다.
  if ! grep -qF 'window.self !== window.top' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-98: window.self !== window.top 판정식 미발견"
    return 1
  fi

  # T22-99(R1, GOTCHA 3): isEmbedded 는 선언 1 + 사용 1, 정확히 2줄이어야 한다 — 그 이상이면
  # 문서 산문에도 그 식별자를 쓴 것이고, if(isEmbedded) return 이 있으면 폴링이 임베드
  # 판정으로 조기 반환하는 회귀다(결정 B2).
  if [[ "$(grep -c 'isEmbedded' "$dashboard_command_file")" -ne 2 ]]; then
    record_failure "$test_name" "T22-99: isEmbedded 등장 횟수가 정확히 2가 아님"
    return 1
  fi
  if grep -qE 'if\(isEmbedded\) return' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-99: if(isEmbedded) return 발견(폴링 조기 반환 회귀)"
    return 1
  fi

  # T22-100(R2): 3-a 절차 어휘 4종 — 절 자체가 없으면 허브 우선 열기가 전혀 동작하지 않는다.
  local r2_step3a_token
  for r2_step3a_token in '### 3-a. 열기 대상 확정' 'NOHUB' 'server-status --json' '열기 대상 URL'; do
    if ! grep -qF -- "$r2_step3a_token" "$dashboard_command_file"; then
      record_failure "$test_name" "T22-100: 3-a 절 토큰 미발견: $r2_step3a_token"
      return 1
    fi
  done

  # T22-101(R2, 결정 F3): 허브 기본 포트를 하드코딩하지 않는다(역방향) + 보고 표에 모달
  # 문구 존재(결정 F5 의 대시보드 URL 병기 회귀 방지).
  if grep -qF '8794' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-101: 허브 기본 포트(8794) 가 하드코딩됨"
    return 1
  fi
  if ! grep -qF '모달' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-101: 보고 표에 '모달' 문구 미발견(대시보드 URL 병기 회귀)"
    return 1
  fi

  # T22-102(R6): 4번 범위에 폐쇄 어휘·구조 4종이 모두 있는지 확인한다.
  local browser_open_r6_section
  browser_open_r6_section=$(sed -n '/^### 4\. 브라우저 열기/,/^### 5\./p' "$dashboard_command_file")
  if [[ -z "$browser_open_r6_section" ]]; then
    record_failure "$test_name" "T22-102: 브라우저 열기 절 범위 추출 실패 — 앵커가 깨졌다"
    return 1
  fi
  local r6_token
  for r6_token in 'FOCUSED' 'NOTFOUND' 'UNSUPPORTED' 'osascript'; do
    if ! grep -qF -- "$r6_token" <<< "$browser_open_r6_section"; then
      record_failure "$test_name" "T22-102: 4번 범위에 $r6_token 미발견"
      return 1
    fi
  done

  # T22-103(R6, 가장 값진 검사): ① is running 검사 존재(GOTCHA 10 — 없으면 꺼진 브라우저를
  # 실행시킨다) ② 4번 범위에 '2-b 를 건너뛰고' 또는 '끝이다' 존재(GOTCHA 11 — 중복 탭 방지).
  if ! grep -qF 'is running' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-103: 'is running' 검사 미발견(꺼진 브라우저를 실행시키는 회귀)"
    return 1
  fi
  if ! grep -qF '2-b 를 건너뛰고' <<< "$browser_open_r6_section" \
    && ! grep -qF '끝이다' <<< "$browser_open_r6_section"; then
    record_failure "$test_name" "T22-103: 4번 범위에 '2-b 를 건너뛰고' 또는 '끝이다' 미발견(중복 탭 회귀)"
    return 1
  fi

  # T22-104(R6, 결정 TR4 역방향): URL 매칭은 정확 일치여야 한다 — 느슨한 매칭 흔적이 있으면
  # 남의 프로젝트 탭을 앞으로 가져올 수 있다.
  if ! grep -qF 'URL of' <<< "$browser_open_r6_section"; then
    record_failure "$test_name" "T22-104: 'URL of' 미발견(URL 비교 코드 자체가 없음)"
    return 1
  fi
  if grep -qE 'starts with|contains' <<< "$browser_open_r6_section"; then
    record_failure "$test_name" "T22-104: 느슨한 매칭 흔적(starts with/contains) 발견"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T23: 대시보드 옵션의 대화형 설치·사후 전환 절차 문서 정합성 (하위 검증 T23-1~T23-11).
# 이 기능은 README.md · CLAUDE.md · commands/dashboard.md 세 문서가 같은 설정 키
# (dashboard_enabled)에 합의해야만 동작하므로, 문자열 정합성 회귀를 grep 으로 막는다.
test_dashboard_option_docs() {
  local test_name="T23"
  local test_desc="대시보드 옵션 설치·전환 절차 문서 정합성 (T23-1~T23-11)"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  local dashboard_command_file="./.claude/commands/dashboard.md"
  # README.md 는 install.sh 가 배포하는 파일이 아니므로(레포 자체 문서) 설치된 사본이 아니라
  # 레포 원본을 검사한다 — T22-5 가 install.sh 를 REPO_ROOT 기준으로 검사하는 것과 동일 방식.
  local readme_file="$REPO_ROOT/README.md"

  # T23-1: README 에 AI 에이전트 설치 절차 섹션이 존재
  if ! grep -q "AI 에이전트로 설치" "$readme_file"; then
    record_failure "$test_name" "T23-1: README 에 AI 에이전트 설치 절차 섹션 미발견"
    return 1
  fi

  # T23-2: 절차가 대상 프로젝트 바깥 clone 을 명시
  if ! grep -q "바깥에 clone" "$readme_file"; then
    record_failure "$test_name" "T23-2: 바깥에 clone 문구 미발견"
    return 1
  fi

  # T23-3: CLAUDE.md 충돌 시 자동 --force 금지 문구가 존재
  if ! grep -q "자동으로 .*--force.* 를 붙이지 않는다" "$readme_file"; then
    record_failure "$test_name" "T23-3: 자동 --force 금지 문구 미발견"
    return 1
  fi

  # T23-4: 설치 절차가 대시보드 옵션 질문 단계를 포함
  if ! grep -q "대시보드 옵션 질문" "$readme_file"; then
    record_failure "$test_name" "T23-4: 대시보드 옵션 질문 단계 미발견"
    return 1
  fi

  # T23-5: dashboard.md 에 on/off 절이 존재
  if ! grep -q '^## `on` / `off`' "$dashboard_command_file"; then
    record_failure "$test_name" "T23-5: on/off 절 미발견"
    return 1
  fi

  # T23-6: frontmatter argument-hint 에 on·off 가 노출
  if ! head -4 "$dashboard_command_file" | grep -q "| on | off"; then
    record_failure "$test_name" "T23-6: argument-hint 에 on/off 미노출"
    return 1
  fi

  # T23-7: 세 문서(CLAUDE.md·README.md·dashboard.md)가 키 이름을 동일 표기로 참조.
  # 이 항목이 가장 중요하다 — 한 곳에서 이름이 어긋나면 미지의 설정 키로 조용히 무시된다.
  local doc_file
  for doc_file in "$REPO_ROOT/CLAUDE.md" "$readme_file" "$dashboard_command_file"; do
    if [[ "$(grep -c "dashboard_enabled" "$doc_file")" -lt 1 ]]; then
      record_failure "$test_name" "T23-7: dashboard_enabled 미참조: $doc_file"
      return 1
    fi
  done

  # T23-8: on/off 절이 기존 필드 보존을 명시
  if ! grep -q "기존 필드는 어떤 경우에도 건드리지 않는다" "$dashboard_command_file"; then
    record_failure "$test_name" "T23-8: 기존 필드 보존 문구 미발견"
    return 1
  fi

  # T23-9: 파싱 불가 파일을 덮어쓰지 않는다는 문구 존재
  if ! grep -q "덮어쓰면 사용자의 권한 허용 목록이 사라진다" "$dashboard_command_file"; then
    record_failure "$test_name" "T23-9: 파싱 불가 파일 보호 문구 미발견"
    return 1
  fi

  # T23-10: on/off 가 대시보드 HTML 을 만들지도 지우지도 않음을 명시
  if ! grep -q "만들지도 지우지도 않는다" "$dashboard_command_file"; then
    record_failure "$test_name" "T23-10: HTML 비접촉 문구 미발견"
    return 1
  fi

  # T23-11: README 가 병합 절차를 복제하지 않고 참조만 함 (DRY 경계 회귀 방지).
  # README 에 절차 전문을 붙여넣으면 이 문자열이 급증하므로 상한을 둔다.
  local settings_json_mentions
  settings_json_mentions=$(grep -c "settings.local.json" "$readme_file")
  if [[ "$settings_json_mentions" -gt 3 ]]; then
    record_failure "$test_name" "T23-11: README 가 병합 절차를 복제한 것으로 의심됨 (settings.local.json 언급 ${settings_json_mentions}회)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T24: 허브 순수 로직 단위 테스트 (stdlib unittest). 종료 코드만 검사하고,
# 실패 시 출력을 그대로 흘려보내 원인을 바로 알 수 있게 한다.
test_hub_unit_tests() {
  local test_name="T24"
  local test_desc="hub_parse·hub_model 단위 테스트 (python3 -m unittest discover)"
  log_test_name "$test_name" "$test_desc"

  local output
  local exit_code=0
  output=$(cd "$REPO_ROOT" && python3 -m unittest discover -s tests/hub -t "$REPO_ROOT" 2>&1) || exit_code=$?

  if [[ "$exit_code" -ne 0 ]]; then
    echo "$output"
    record_failure "$test_name" "python3 -m unittest discover 실패 (exit $exit_code)"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

# T25: 허브 문서·상수 정합성 (하위 검증 T25-1~T25-74)
test_hub_docs_and_constants() {
  local test_name="T25"
  local test_desc="허브 문서·상수 정합성 (T25-1~T25-74)"
  log_test_name "$test_name" "$test_desc"

  local hub_settings_file="$REPO_ROOT/hub/bin/hub_settings.py"
  local hub_hook_file="$REPO_ROOT/hub/bin/hub_hook.py"
  local hub_py_file="$REPO_ROOT/hub/bin/hub.py"
  local hub_collect_file="$REPO_ROOT/hub/bin/hub_collect.py"
  local hub_model_file="$REPO_ROOT/hub/bin/hub_model.py"
  local hub_server_file="$REPO_ROOT/hub/bin/hub_server.py"
  local hub_daemon_file="$REPO_ROOT/hub/bin/hub_daemon.py"
  local hub_install_file="$REPO_ROOT/hub/install.sh"
  local hub_command_file="$REPO_ROOT/commands/hub.md"
  local env_update_command_file="$REPO_ROOT/commands/env-update.md"
  local dashboard_command_file="$REPO_ROOT/commands/dashboard.md"
  local readme_file="$REPO_ROOT/README.md"

  # T25-1(개정 R-M5 — 대상 이동): HUB_FILE_COUNT 는 이제 hub/install.sh 가 갖는다(값 10)
  local declared_count actual_count
  declared_count=$(grep -oE '^readonly HUB_FILE_COUNT=[0-9]+' "$hub_install_file" | grep -oE '[0-9]+$')
  actual_count=$(find "$REPO_ROOT/hub/bin" -maxdepth 1 -type f | wc -l | tr -d ' ')
  if ! assert_equals "$actual_count" "$declared_count" "HUB_FILE_COUNT 일치"; then
    record_failure "$test_name" "T25-1: HUB_FILE_COUNT=$declared_count, 실제 파일 수=$actual_count"
    return 1
  fi

  # T25-2(개정 R-M5 — 반전): 루트 install.sh 는 hub 를 전혀 모른다. hub/install.sh 가 독립 설치한다
  local sandbox_root sandbox_hub
  sandbox_root=$(mktemp -d)
  sandbox_hub=$(mktemp -d)
  trap "rm -rf '$sandbox_root' '$sandbox_hub'" EXIT

  HOME="$sandbox_root" "$INSTALL_SCRIPT" --scope user > /dev/null 2>&1
  if [[ -d "$sandbox_root/.claude/hub" ]]; then
    record_failure "$test_name" "T25-2: 루트 install.sh --scope user 후 .claude/hub 가 생성됨 (기대: 미생성)"
    return 1
  fi

  HOME="$sandbox_hub" "$hub_install_file" > /dev/null 2>&1
  local installed_hub_count
  installed_hub_count=$(find "$sandbox_hub/.claude/hub/bin" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$installed_hub_count" -ne "$declared_count" ]]; then
    record_failure "$test_name" "T25-2: hub/install.sh 설치 후 hub/bin 파일 수=$installed_hub_count (기대 $declared_count)"
    return 1
  fi

  # T25-3(개정 R-4 — 대상 이동): 마커 문서화는 이제 hub/README.md 가 맡는다(root README.md 는 분리됨)
  local marker="# DZH_HUB_HOOK"
  local hub_readme_file="$REPO_ROOT/hub/README.md"
  local doc_file
  for doc_file in "$hub_settings_file" "$hub_command_file" "$hub_readme_file"; do
    if ! grep -qF "$marker" "$doc_file"; then
      record_failure "$test_name" "T25-3: $marker 마커 미발견: $doc_file"
      return 1
    fi
  done

  # T25-4: 훅 커맨드 문자열에 || true 와 >/dev/null 이 모두 있다
  if ! grep -F "|| true" "$hub_settings_file" | grep -qF ">/dev/null"; then
    record_failure "$test_name" "T25-4: 훅 커맨드에 || true 와 >/dev/null 이 한 줄에 함께 없음"
    return 1
  fi

  # T25-5: type: "http" 를 쓰지 말라는 근거 문구
  if ! grep -qF 'type: "http"' "$hub_command_file"; then
    record_failure "$test_name" "T25-5: type:\"http\" 관련 근거 문구 미발견"
    return 1
  fi

  # T25-6: dashboard.md 에 불변식 2·5 문구가 여전히 존재한다 (티어 1 파서의 전제)
  if ! grep -qF '<li id="dz-step-…">' "$dashboard_command_file"; then
    record_failure "$test_name" "T25-6: 불변식 2 문구(dz-step) 미발견"
    return 1
  fi
  if ! grep -qF '<li id="dz-impl-…">' "$dashboard_command_file"; then
    record_failure "$test_name" "T25-6: 불변식 5 문구(dz-impl) 미발견"
    return 1
  fi

  # T25-7: hub_hook.py 에 Notification 문자열이 없다 (미설치 결정의 회귀 방지)
  if grep -q "Notification" "$hub_hook_file"; then
    record_failure "$test_name" "T25-7: hub_hook.py 에 Notification 문자열이 존재함"
    return 1
  fi

  # T25-8(개정 — 포트 상수가 hub_model.py 로 이동): 8794 정합, 8791 부재
  if ! grep -q "8794" "$hub_model_file" || ! grep -q "8794" "$hub_command_file"; then
    record_failure "$test_name" "T25-8: 포트 8794 가 hub_model.py 또는 commands/hub.md 에 없음"
    return 1
  fi
  if grep -q "8791" "$hub_model_file" "$hub_command_file"; then
    record_failure "$test_name" "T25-8: /dashboard 의 포트 8791 이 허브 파일에 등장함"
    return 1
  fi

  # T25-9: README.md 가 "독립 커맨드 2종"으로 갱신됐다
  if ! grep -qF "독립 커맨드 2종" "$readme_file"; then
    record_failure "$test_name" "T25-9: README 에 '독립 커맨드 2종' 문구 미발견"
    return 1
  fi

  # T25-10(+ T25-27 — hub_usage.py 추가): hub_model.py·hub_parse.py·hub_usage.py 에
  # 파일시스템 접근이 없다 (순수 레이어 경계의 기계적 강제)
  local pure_file
  for pure_file in "$REPO_ROOT/hub/bin/hub_model.py" "$REPO_ROOT/hub/bin/hub_parse.py" "$REPO_ROOT/hub/bin/hub_usage.py"; do
    if grep -qE 'open\(|Path\(|os\.' "$pure_file"; then
      record_failure "$test_name" "T25-10: $pure_file 에 파일시스템 접근 흔적(open(/Path(/os.)이 있음"
      return 1
    fi
  done

  local hub_template_file="$REPO_ROOT/hub/bin/hub_template.html"

  # T25-11(수정 — 세션 줄 재구성 반영): 세션 줄의 동적 값은 반드시 escapeHtml 을 통과한다.
  # 기존 부정 검사(`+ session.short_id +` 리터럴 금지)는 그대로 둔다 — short_id 렌더가
  # 폐기됐어도 되살아나는 것을 막는 값이 있다. 아래 긍정 검사만 새 렌더 대상으로 교체했다:
  # session.short_id 는 더 이상 렌더되지 않고(세션 줄이 agent_runs 로 재구성됨), 대신 세션
  # 줄이 실제로 넣는 동적 값(run.agent_type)이 escapeHtml 을 통과하는지 확인한다.
  if grep -qF "+ session.short_id +" "$hub_template_file"; then
    record_failure "$test_name" "T25-11: session.short_id 가 escapeHtml 없이 삽입됨(m9 회귀)"
    return 1
  fi
  if ! grep -qF "escapeHtml(run.agent_type)" "$hub_template_file"; then
    record_failure "$test_name" "T25-11: 서브에이전트 타입명이 escapeHtml 없이 삽입됨"
    return 1
  fi

  # T25-12(검수 M6 회귀): 티어 1 렌더에 활성 단계·구현 진행·stale 병기가 반영됐다
  if ! grep -qF "renderTier1ActiveStep" "$hub_template_file"; then
    record_failure "$test_name" "T25-12: 티어 1 렌더에 활성 단계 표시가 없음"
    return 1
  fi
  if ! grep -qF "renderTier1ImplProgress" "$hub_template_file"; then
    record_failure "$test_name" "T25-12: 티어 1 렌더에 구현 진행(impl_done/impl_total) 표시가 없음"
    return 1
  fi
  if ! grep -qF "직전 " "$hub_template_file"; then
    record_failure "$test_name" "T25-12: stale 세션의 '직전 <base_state>' 병기 문구가 없음"
    return 1
  fi

  # T25-13(검수 M1 회귀): JSON 유니코드 이스케이프로 교체됐고, HTML 엔티티 치환으로 되돌아가지 않았다
  local render_hub_html_file="$REPO_ROOT/hub/bin/hub_model.py"
  if ! grep -qF "u003c" "$render_hub_html_file"; then
    record_failure "$test_name" "T25-13: render_hub_html 에 JSON 유니코드 이스케이프(u003c)가 없음"
    return 1
  fi
  if grep -qF "&lt;" "$render_hub_html_file"; then
    record_failure "$test_name" "T25-13: render_hub_html 이 HTML 엔티티 치환으로 회귀함(M1 회귀)"
    return 1
  fi

  # T25-14: hub/bin/*.py·commands/hub.md 에 serve 잔재가 없다(폐기 회귀 방지, 개정 쟁점 R2)
  local serve_leftover_pattern='start_serving|stop_serving|/hub serve[^r]|pkill'
  local source_file
  for source_file in "$REPO_ROOT"/hub/bin/*.py "$hub_command_file"; do
    if grep -qE "$serve_leftover_pattern" "$source_file"; then
      record_failure "$test_name" "T25-14: $source_file 에 폐기된 serve 잔재가 남아 있음"
      return 1
    fi
  done

  # T25-15: hub_server.py 가 SimpleHTTPRequestHandler 를 쓰지 않고 화이트리스트를 갖는다(노출 표면 회귀 방지)
  if grep -qF "SimpleHTTPRequestHandler" "$hub_server_file"; then
    record_failure "$test_name" "T25-15: hub_server.py 가 SimpleHTTPRequestHandler 를 사용함(디렉토리 전체 노출 위험)"
    return 1
  fi
  if ! grep -qF "ALLOWED_REQUEST_PATHS" "$hub_server_file"; then
    record_failure "$test_name" "T25-15: hub_server.py 에 ALLOWED_REQUEST_PATHS 화이트리스트가 없음"
    return 1
  fi

  # T25-16(검수 Nit2 — AST 검사로 승격): hub_daemon.py 의 **같은 함수 안에서** os.kill 호출보다
  # is_our_server_process 호출이 먼저 나와야 한다(PID 재사용 방어 회귀 방지). 텍스트 줄 번호
  # 비교보다 엄밀하다 — 함수 경계를 실제로 구분하므로 무관한 함수의 신원 확인이 우연히
  # 앞줄에 있다는 이유로 통과하는 오탐이 없다.
  local ast_check_output
  ast_check_output=$(python3 - "$hub_daemon_file" <<'PYEOF'
import ast
import sys

source_path = sys.argv[1]
tree = ast.parse(open(source_path, encoding="utf-8").read(), filename=source_path)


def is_os_kill_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "kill"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
    )


def is_identity_check_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "is_our_server_process"
    )


violations = []
kill_call_total = 0
for func in ast.walk(tree):
    if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    kill_calls = [n for n in ast.walk(func) if is_os_kill_call(n)]
    if not kill_calls:
        continue
    kill_call_total += len(kill_calls)
    check_lines = [n.lineno for n in ast.walk(func) if is_identity_check_call(n)]
    for kill_call in kill_calls:
        if not any(line < kill_call.lineno for line in check_lines):
            violations.append(f"{func.name}() 의 {kill_call.lineno}번째 줄")

if kill_call_total == 0:
    print("NO_KILL_CALLS_FOUND")
elif violations:
    print("VIOLATIONS:" + "; ".join(violations))
else:
    print("OK")
PYEOF
)
  if [[ "$ast_check_output" == "NO_KILL_CALLS_FOUND" ]]; then
    record_failure "$test_name" "T25-16: hub_daemon.py 에서 os.kill 호출을 찾지 못함"
    return 1
  fi
  if [[ "$ast_check_output" != "OK" ]]; then
    record_failure "$test_name" "T25-16: 신원 확인 없이 os.kill 을 호출하는 지점 — $ast_check_output"
    return 1
  fi

  # T25-17: hub_daemon.py 에 start_new_session=True 가 있다(세션 무관 수명, 요구 R-1 의 기계적 강제)
  if ! grep -qF "start_new_session=True" "$hub_daemon_file"; then
    record_failure "$test_name" "T25-17: hub_daemon.py 에 start_new_session=True 가 없음"
    return 1
  fi

  # T25-18: _tier3_activity_by_encoded_name 이 except OSError 를 포함한다(R3-m1 회귀)
  local tier3_function_body
  tier3_function_body=$(awk '/^def _tier3_activity_by_encoded_name\(/{flag=1; next} flag && /^def /{exit} flag{print}' "$hub_collect_file")
  if ! echo "$tier3_function_body" | grep -qF "except OSError"; then
    record_failure "$test_name" "T25-18: _tier3_activity_by_encoded_name 에 except OSError 가드가 없음"
    return 1
  fi

  # T25-19: commands/hub.md 에 last_collect_failure·event_read_warnings 등장(R3-m2 회귀)
  if ! grep -qF "last_collect_failure" "$hub_command_file"; then
    record_failure "$test_name" "T25-19: commands/hub.md 에 last_collect_failure 미언급"
    return 1
  fi
  if ! grep -qF "event_read_warnings" "$hub_command_file"; then
    record_failure "$test_name" "T25-19: commands/hub.md 에 event_read_warnings 미언급"
    return 1
  fi

  # T25-20: hub.py 의 cmd_open 함수 본문에 서버 기동 호출이 없다(암묵 기동 회귀 방지, 요구 R-2)
  local cmd_open_body
  cmd_open_body=$(awk '/^def cmd_open\(/{flag=1; next} flag && /^def /{exit} flag{print}' "$hub_py_file")
  if echo "$cmd_open_body" | grep -qE "start_server|server-start"; then
    record_failure "$test_name" "T25-20: cmd_open 이 서버를 기동하는 것으로 보임(암묵 기동 회귀)"
    return 1
  fi

  # T25-21: 루트 install.sh 에 hub 문자열이 등장하지 않는다(설치 분리의 기계적 강제, 요구 R-5)
  local root_hub_mentions
  root_hub_mentions=$(grep -c "hub" "$INSTALL_SCRIPT" || true)
  if [[ "$root_hub_mentions" -ne 0 ]]; then
    record_failure "$test_name" "T25-21: install.sh 에 hub 문자열이 ${root_hub_mentions}건 등장함(기대 0)"
    return 1
  fi

  # T25-22(검수 Nit3 — 임계값 완화): README.md 의 허브 언급이 14줄 이하이고 hub/README.md
  # 링크를 포함한다(문서 분리 회귀 방지). 대소문자 구분 검색이다 — case-insensitive 는
  # "GitHub" 까지 세어 오탐한다. 10 은 소소한 문구 조정에도 쉽게 넘는 빡빡한 값이었다.
  local readme_hub_mentions readme_hub_link_count
  readme_hub_mentions=$(grep -c "hub" "$readme_file" || true)
  readme_hub_link_count=$(grep -cF "hub/README.md" "$readme_file" || true)
  if [[ "$readme_hub_mentions" -gt 14 ]]; then
    record_failure "$test_name" "T25-22: README.md 의 허브 언급이 ${readme_hub_mentions}줄(기대 14줄 이하)"
    return 1
  fi
  if [[ "$readme_hub_link_count" -eq 0 ]]; then
    record_failure "$test_name" "T25-22: README.md 에 hub/README.md 링크가 없음"
    return 1
  fi

  # T25-23: hub/install.sh --uninstall 절차에서 server-stop·uninstall-hooks 가 rm -rf 보다 앞에 온다
  local server_stop_line uninstall_hooks_line rm_rf_line
  server_stop_line=$(grep -n "server-stop" "$hub_install_file" | head -1 | cut -d: -f1)
  uninstall_hooks_line=$(grep -n "uninstall-hooks" "$hub_install_file" | head -1 | cut -d: -f1)
  rm_rf_line=$(grep -n 'rm -rf "\$TARGET_BIN_DIR"' "$hub_install_file" | head -1 | cut -d: -f1)
  if [[ -z "$server_stop_line" || -z "$uninstall_hooks_line" || -z "$rm_rf_line" ]]; then
    record_failure "$test_name" "T25-23: server-stop/uninstall-hooks/rm -rf 셋 중 하나를 hub/install.sh 에서 찾지 못함"
    return 1
  fi
  if [[ "$server_stop_line" -ge "$rm_rf_line" || "$uninstall_hooks_line" -ge "$rm_rf_line" ]]; then
    record_failure "$test_name" "T25-23: server-stop·uninstall-hooks 가 rm -rf 보다 앞에 있지 않음(순서 위반)"
    return 1
  fi

  # T25-24: commands/env-update.md 에 조건부 허브 절과 판정 경로(hub/bin/hub.py)가 있다(R-5 연동 회귀)
  if ! grep -qF "Phase 4b" "$env_update_command_file"; then
    record_failure "$test_name" "T25-24: commands/env-update.md 에 Phase 4b 절이 없음"
    return 1
  fi
  if ! grep -qF "hub/bin/hub.py" "$env_update_command_file"; then
    record_failure "$test_name" "T25-24: commands/env-update.md 에 판정 경로(hub/bin/hub.py)가 없음"
    return 1
  fi

  # T25-25: commands/hub.md 사전 조건이 install.sh --scope user 를 안내하지 않고 hub/install.sh 를 안내한다
  if grep -qF "install.sh --scope user 를 먼저 실행" "$hub_command_file"; then
    record_failure "$test_name" "T25-25: commands/hub.md 가 존재하지 않는 절차(install.sh --scope user)를 안내함"
    return 1
  fi
  if ! grep -qF "hub/install.sh" "$hub_command_file"; then
    record_failure "$test_name" "T25-25: commands/hub.md 사전 조건에 hub/install.sh 안내가 없음"
    return 1
  fi

  # T25-26(검수 n1 회귀 — 2방향 실측): stop_server_or_abort 의 ok 판정은 문자열 매칭이 아니라
  # 실제 JSON 파싱이다. 압축 JSON(`"ok":true`, 공백 없음)으로도 성공을 오판 없이 인식해야
  # 한다 — 예전의 `grep -q '"ok": true'` 였다면 이 공백 없는 형태를 실패로 오판했을 것이다.
  # 반대로 ok:false 면 --force 없이 반드시 중단하고 bin/ 을 보존해야 한다(정지 수단 소멸 방지).
  local sandbox_stop_ok sandbox_stop_fail
  sandbox_stop_ok=$(mktemp -d)
  sandbox_stop_fail=$(mktemp -d)
  trap "rm -rf '$sandbox_root' '$sandbox_hub' '$sandbox_stop_ok' '$sandbox_stop_fail'" EXIT

  mkdir -p "$sandbox_stop_ok/.claude/hub/bin"
  cat > "$sandbox_stop_ok/.claude/hub/bin/hub.py" << 'PYEOF'
#!/usr/bin/env python3
import sys
subcommand = sys.argv[1] if len(sys.argv) > 1 else ""
if subcommand == "server-stop":
    print('{"ok":true,"was_running":true}')
elif subcommand == "uninstall-hooks":
    print('{"ok":true,"removed":[]}')
else:
    print('{"ok":true}')
PYEOF

  mkdir -p "$sandbox_stop_fail/.claude/hub/bin"
  cat > "$sandbox_stop_fail/.claude/hub/bin/hub.py" << 'PYEOF'
#!/usr/bin/env python3
import sys
subcommand = sys.argv[1] if len(sys.argv) > 1 else ""
if subcommand == "server-stop":
    print('{"ok":false,"reason":"테스트로 강제한 실패"}')
elif subcommand == "uninstall-hooks":
    print('{"ok":true,"removed":[]}')
else:
    print('{"ok":true}')
PYEOF

  HOME="$sandbox_stop_ok" "$hub_install_file" --uninstall > /dev/null 2>&1
  if [[ -d "$sandbox_stop_ok/.claude/hub/bin" ]]; then
    record_failure "$test_name" "T25-26: server-stop 성공(압축 JSON)인데 bin/ 이 삭제되지 않음(오판 의심)"
    return 1
  fi

  if HOME="$sandbox_stop_fail" "$hub_install_file" --uninstall > /dev/null 2>&1; then
    record_failure "$test_name" "T25-26: server-stop 실패인데 hub/install.sh --uninstall 이 성공(exit 0)으로 끝남"
    return 1
  fi
  if [[ ! -f "$sandbox_stop_fail/.claude/hub/bin/hub.py" ]]; then
    record_failure "$test_name" "T25-26: server-stop 실패 시 bin/ 이 보존되지 않음(정지 수단 소멸)"
    return 1
  fi

  # T25-28(결정 T1·T3 회귀): 다크 테마는 미디어 쿼리 + data-theme 속성 오버라이드 둘 다로
  # 성립하고, 'dzh-theme' 리터럴은 head FOUC 스크립트 + 본문 IIFE 두 곳에 각각 등장해야 한다
  # (head 스크립트는 자족적이어야 해서 상수 공유가 불가능하다).
  if ! grep -qF "prefers-color-scheme" "$hub_template_file"; then
    record_failure "$test_name" "T25-28: hub_template.html 에 prefers-color-scheme 가 없음"
    return 1
  fi
  if ! grep -qF "data-theme" "$hub_template_file"; then
    record_failure "$test_name" "T25-28: hub_template.html 에 data-theme 가 없음"
    return 1
  fi
  local dzh_theme_literal_count
  dzh_theme_literal_count=$(grep -oF "'dzh-theme'" "$hub_template_file" | wc -l | tr -d ' ')
  if [[ "$dzh_theme_literal_count" -lt 2 ]]; then
    record_failure "$test_name" "T25-28: 'dzh-theme' 리터럴이 ${dzh_theme_literal_count}회만 등장(기대 2회 이상)"
    return 1
  fi

  # T25-29(팔레트 회귀 방지): 색각 안전성이 없는 구형 초록·빨강·주황이 템플릿에서 완전히 사라져야 한다.
  local legacy_color
  for legacy_color in "#1F8A70" "#C2410C" "#F59E0B"; do
    if grep -qF "$legacy_color" "$hub_template_file"; then
      record_failure "$test_name" "T25-29: hub_template.html 에 색각 안전성 없는 팔레트($legacy_color)가 남아 있음"
      return 1
    fi
  done

  # T25-30(색 이외 채널 회귀 방지): 상태 배지가 색만이 아니라 글리프로도 구분되고,
  # 그 글리프는 스크린리더에서 숨겨진다(aria-hidden).
  if ! grep -qF "STATE_GLYPH" "$hub_template_file"; then
    record_failure "$test_name" "T25-30: hub_template.html 에 STATE_GLYPH 가 없음"
    return 1
  fi
  if ! grep -qF "aria-hidden" "$hub_template_file"; then
    record_failure "$test_name" "T25-30: hub_template.html 에 aria-hidden 이 없음"
    return 1
  fi

  # T25-31(문서 정합, 개정 — 죽은 전제를 테스트로 고정하지 않는다): show_usage_panel 스위치와
  # 데이터 출처(statusLine 캡처의 used_percentage)가 hub/README.md 에 문서화돼 있다.
  # plan-usage-history.json 은 결정 P1 로 사라진 경로라 더 이상 grep 대상이 아니다(승인 항목 5).
  local hub_readme_usage_file="$REPO_ROOT/hub/README.md"
  local usage_source_token
  for usage_source_token in "show_usage_panel" "used_percentage" "statusLine"; do
    if ! grep -qF "$usage_source_token" "$hub_readme_usage_file"; then
      record_failure "$test_name" "T25-31: hub/README.md 에 $usage_source_token 언급이 없음"
      return 1
    fi
  done

  # T25-32(결정 G1~G5 회귀): 프로젝트 목록이 뷰포트 폭에 따라 열 수가 바뀌는 그리드이고,
  # 카드가 행 높이에 맞춰 늘어나지 않으며, 비-카드 요소는 한 행을 다 쓴다.
  local grid_token
  for grid_token in "max-width:1440px" "display:grid" \
                    "repeat(auto-fill,minmax(max(320px,calc((100% - 24px)/3 - 1px)),1fr))" \
                    "align-items:start" "grid-column:1/-1"; do
    if ! grep -qF "$grid_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-32: hub_template.html 에 그리드 규칙($grid_token)이 없음"
      return 1
    fi
  done

  # T25-33(결정 C1 · 불변식 H1′ 회귀 — 이 파일에서 가장 중요한 검사):
  # 접기 버튼은 정적 마크업이어야 하고, 패널 컨테이너를 통째로 다시 그리는 코드가 되살아나면
  # 접힘 상태가 30초 틱마다 초기화된다.
  if ! grep -qF '<button id="dzh-usage-toggle"' "$hub_template_file"; then
    record_failure "$test_name" "T25-33: 접기 버튼이 정적 마크업으로 존재하지 않음"
    return 1
  fi
  if ! grep -qF 'id="dzh-usage-body"' "$hub_template_file"; then
    record_failure "$test_name" "T25-33: 파생 본문 컨테이너(#dzh-usage-body)가 없음"
    return 1
  fi
  if grep -qF "usageEl.innerHTML" "$hub_template_file"; then
    record_failure "$test_name" "T25-33: usageEl.innerHTML 대입이 부활함 — 재렌더가 접기 버튼을 파괴한다"
    return 1
  fi

  # T25-34(제약 C8 회귀): 접기 토글의 상태가 접근성 트리에 노출되고, 기존 막대의
  # progressbar 시맨틱이 리팩토링 중 유실되지 않는다.
  local a11y_token
  for a11y_token in "aria-expanded" 'aria-controls="dzh-usage-body"' 'role="progressbar"'; do
    if ! grep -qF "$a11y_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-34: hub_template.html 에 접근성 속성($a11y_token)이 없음"
      return 1
    fi
  done

  # T25-35(결정 L1·L3·C2 회귀): 패널은 우하단 고정이고(중앙 정렬 흔적이 남으면 안 된다),
  # 하단 여백은 실측 커스텀 속성으로 주며, 접힘 상태는 전용 키에 저장된다.
  if grep -qF "translateX(-50%)" "$hub_template_file"; then
    record_failure "$test_name" "T25-35: 하단 중앙 정렬(translateX(-50%))이 남아 있음"
    return 1
  fi
  local panel_token
  for panel_token in "right:16px;bottom:16px" "--usage-clearance" "'dzh-usage-collapsed'"; do
    if ! grep -qF -- "$panel_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-35: hub_template.html 에 패널 규칙($panel_token)이 없음"
      return 1
    fi
  done

  # T25-36(문서 정합): 화면 배치 변경이 hub/README.md 에 반영돼 있다.
  local hub_readme_layout_file="$REPO_ROOT/hub/README.md"
  local doc_token
  for doc_token in "우하단" "접기" "그리드"; do
    if ! grep -qF "$doc_token" "$hub_readme_layout_file"; then
      record_failure "$test_name" "T25-36: hub/README.md 에 화면 배치 설명($doc_token)이 없음"
      return 1
    fi
  done

  # T25-37(검수 m3 회귀): escapeHtml 이 따옴표도 이스케이프한다. usage-meta 의 title="..." 이
  # 이 함수의 첫 속성 자리 사용처라, 따옴표를 넘기면 그대로 속성이 끊길 수 있었다.
  if ! grep -qF '.replace(/"/g' "$hub_template_file"; then
    record_failure "$test_name" 'T25-37: escapeHtml 에 큰따옴표 이스케이프가 없음'
    return 1
  fi
  if ! grep -qF ".replace(/'/g" "$hub_template_file"; then
    record_failure "$test_name" "T25-37: escapeHtml 에 작은따옴표 이스케이프가 없음"
    return 1
  fi

  # T25-38(GOTCHA 1 회귀): statusLine 커맨드 줄이 stdout 을 리다이렉트하지 않는다.
  # `2>/dev/null` 은 `>/dev/null` 을 부분 문자열로 포함하므로 grep -F '>/dev/null' 로는
  # 검사할 수 없다(정상 커맨드가 항상 걸린다) — `>` 앞 문자가 숫자가 아닌 경우만 잡는다(GOTCHA 6).
  if grep -F 'hub_statusline.py' "$hub_settings_file" | grep -qE '(^|[^0-9])>/dev/null'; then
    record_failure "$test_name" "T25-38: statusLine 커맨드가 stdout 을 리다이렉트함 — 상태줄이 사라진다"
    return 1
  fi
  if ! grep -F 'hub_statusline.py' "$hub_settings_file" | grep -qF '2>/dev/null'; then
    record_failure "$test_name" "T25-38: statusLine 커맨드 줄에 2>/dev/null 이 없음"
    return 1
  fi
  if ! grep -F 'hub_statusline.py' "$hub_settings_file" | grep -qF '|| true'; then
    record_failure "$test_name" "T25-38: statusLine 커맨드 줄에 || true 가 없음"
    return 1
  fi
  # 마커(# DZH_HUB_STATUSLINE)는 STATUSLINE_MARKER 변수 참조로 이어붙는다(HOOK_MARKER 와
  # 같은 관행) — 소스상 같은 줄에 리터럴로 나타나지 않는다. 마커 존재 자체는 T25-40 이
  # 파일 전체를 대상으로 검사한다(T25-3 과 같은 방식).

  # T25-39(T25-23 과 같은 방식): hub/install.sh --uninstall 에서 uninstall-statusline 이
  # rm -rf "$TARGET_BIN_DIR" 보다 앞에 온다 — 없는 스크립트를 부르는 무성음 상태를 막는다.
  local uninstall_statusline_line rm_rf_line_t39
  uninstall_statusline_line=$(grep -n "uninstall-statusline" "$hub_install_file" | head -1 | cut -d: -f1)
  rm_rf_line_t39=$(grep -n 'rm -rf "\$TARGET_BIN_DIR"' "$hub_install_file" | head -1 | cut -d: -f1)
  if [[ -z "$uninstall_statusline_line" || -z "$rm_rf_line_t39" ]]; then
    record_failure "$test_name" "T25-39: uninstall-statusline/rm -rf 중 하나를 hub/install.sh 에서 찾지 못함"
    return 1
  fi
  if [[ "$uninstall_statusline_line" -ge "$rm_rf_line_t39" ]]; then
    record_failure "$test_name" "T25-39: uninstall-statusline 이 rm -rf 보다 앞에 있지 않음(순서 위반)"
    return 1
  fi

  # T25-40(T25-3 선례): statusLine 마커 문서화가 hub_settings.py·commands/hub.md·hub/README.md
  # 세 곳에 존재한다.
  local statusline_marker="# DZH_HUB_STATUSLINE"
  for doc_file in "$hub_settings_file" "$hub_command_file" "$hub_readme_file"; do
    if ! grep -qF "$statusline_marker" "$doc_file"; then
      record_failure "$test_name" "T25-40: $statusline_marker 마커 미발견: $doc_file"
      return 1
    fi
  done

  # T25-43(세션 활동 노출 회귀 — 개정: agent-chip-more 부재 검사로 반전): 세션 표시가
  # '실행 중인 것만' 으로 되돌아가지 않고, "+N" 오버플로 칩(agent-chip-more)도 되살아나지
  # 않는다(결정 K1~K3).
  if grep -qF "active_agent_types" "$hub_template_file" "$hub_model_file"; then
    record_failure "$test_name" "T25-43: active_agent_types 가 부활함 — 완료 세션이 다시 빈 목록이 된다"
    return 1
  fi
  if grep -qF "agent-chip-more" "$hub_template_file"; then
    record_failure "$test_name" "T25-43: agent-chip-more 가 남아 있음 — +N 오버플로 칩은 결정 K3 로 삭제됨"
    return 1
  fi
  local session_activity_token
  for session_activity_token in "summarize_agent_runs" "agent_runs"; do
    if ! grep -qF "$session_activity_token" "$hub_model_file"; then
      record_failure "$test_name" "T25-43: hub_model.py 에 $session_activity_token 이 없음"
      return 1
    fi
  done
  for session_activity_token in "renderAgentRuns" "agent-chip" "MAX_VISIBLE_AGENT_CHIPS"; do
    if ! grep -qF "$session_activity_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-43: hub_template.html 에 $session_activity_token 이 없음"
      return 1
    fi
  done

  # T25-41(요구 "주기는 유지"의 회귀 방지): 초기화 예정 시각 표시에 필요한 토큰이 전부
  # hub_template.html 에 있고, 폴링 주기·사용량 갱신 주기 문구는 바뀌지 않았다.
  local reset_time_token
  for reset_time_token in "usage-reset" "rate_limit_resets" "초기화 " "renderUsageResetRow"; do
    if ! grep -qF "$reset_time_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-41: hub_template.html 에 초기화 예정 시각 토큰($reset_time_token)이 없음"
      return 1
    fi
  done
  # 폴링 주기는 5초에서 1분으로 바뀌었다(사용자 요청 — 5초는 너무 짧다). 이 검사는 원래
  # 5000 을 고정했는데, 그 커밋은 주기 변경을 모르는 상태에서 작성됐다. 값만 갱신하고
  # "주기가 임의로 바뀌지 않는다"는 검사의 의도는 그대로 유지한다.
  if ! grep -qF "POLL_INTERVAL_MS = 60000" "$hub_template_file"; then
    record_failure "$test_name" "T25-41: POLL_INTERVAL_MS = 60000 회귀(폴링 주기가 바뀜)"
    return 1
  fi
  # '약 15분 주기'는 데스크톱 앱 샘플링 주기 전제 문구였다. 퍼센트 출처가 statusLine 캡처로
  # 바뀌며(결정 P1·P6) 그 전제 자체가 사라졌다 — 새 문구로 교체한다(승인 항목 5).
  if ! grep -qF "세션 진행 중에만 갱신" "$hub_template_file"; then
    record_failure "$test_name" "T25-41: '세션 진행 중에만 갱신' 문구 회귀(사용량 갱신 주기 고지 유실)"
    return 1
  fi

  # T25-42(문서 정합): hub/README.md·commands/hub.md 에 새 파일·서브커맨드가 문서화돼 있다.
  if ! grep -qF "rate_limits.json" "$hub_readme_file"; then
    record_failure "$test_name" "T25-42: hub/README.md 에 rate_limits.json 언급이 없음"
    return 1
  fi
  if ! grep -qiF "statusline" "$hub_readme_file"; then
    record_failure "$test_name" "T25-42: hub/README.md 에 statusline 언급이 없음"
    return 1
  fi
  if ! grep -qF "install-statusline" "$hub_command_file"; then
    record_failure "$test_name" "T25-42: commands/hub.md 에 install-statusline 이 없음"
    return 1
  fi
  if ! grep -qF "uninstall-statusline" "$hub_command_file"; then
    record_failure "$test_name" "T25-42: commands/hub.md 에 uninstall-statusline 이 없음"
    return 1
  fi

  # T25-44(커스텀 툴팁 회귀): 네이티브 title 툴팁이 하나도 남지 않고, 커스텀 툴팁이 위임·
  # 접근성·해제 경로를 모두 갖는다. (<title> 요소는 속성 형태가 아니라 이 검사에 걸리지 않는다)
  if grep -qF 'title="' "$hub_template_file"; then
    record_failure "$test_name" "T25-44: 네이티브 title 속성이 남아 있음 — data-tooltip 을 쓸 것"
    return 1
  fi
  local tooltip_token
  for tooltip_token in 'id="dzh-tooltip"' 'role="tooltip"' 'data-tooltip' 'aria-describedby' \
                       "'mouseover'" "'focusin'" "Escape" "MutationObserver"; do
    if ! grep -qF -- "$tooltip_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-44: hub_template.html 에 툴팁 계약($tooltip_token)이 없음"
      return 1
    fi
  done

  # T25-45(문서 정합): 세션 줄 구성과 툴팁 거동이 hub/README.md 에 반영돼 있다.
  for doc_token in "서브에이전트" "툴팁"; do
    if ! grep -qF "$doc_token" "$hub_readme_file"; then
      record_failure "$test_name" "T25-45: hub/README.md 에 화면 설명($doc_token)이 없음"
      return 1
    fi
  done

  # T25-46(브라우저 타이틀 회귀): 탭 제목이 "Claude Agents Manager" 로 고정돼 있다.
  if ! grep -qF '<title>Claude Agents Manager</title>' "$hub_template_file"; then
    record_failure "$test_name" "T25-46: hub_template.html 에 <title>Claude Agents Manager</title> 가 없음"
    return 1
  fi

  # T25-47(파비콘 회귀): 인라인 SVG data: URI 파비콘 링크가 유지돼 있다.
  if ! grep -qF 'rel="icon"' "$hub_template_file"; then
    record_failure "$test_name" "T25-47: hub_template.html 에 rel=\"icon\" 이 없음"
    return 1
  fi
  if ! grep -qF 'data:image/svg+xml' "$hub_template_file"; then
    record_failure "$test_name" "T25-47: hub_template.html 에 data:image/svg+xml 파비콘이 없음"
    return 1
  fi

  # T25-48(재기동 계약 회귀): server-restart 가 CLI·데몬·커맨드 문서 세 곳에 있고,
  # 그것을 만들면서 멱등 start 를 force 로 바꾸는 회귀(GOTCHA 1)가 없다.
  local restart_token
  for restart_token in "server-restart" "cmd_server_restart"; do
    if ! grep -qF "$restart_token" "$hub_py_file"; then
      record_failure "$test_name" "T25-48: hub.py 에 $restart_token 이 없음"
      return 1
    fi
  done
  for restart_token in "def restart_server" "def restart_note" "_wait_for_port_release"; do
    if ! grep -qF "$restart_token" "$hub_daemon_file"; then
      record_failure "$test_name" "T25-48: hub_daemon.py 에 $restart_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF '"already_running": True' "$hub_daemon_file"; then
    record_failure "$test_name" "T25-48: start_server 의 멱등(already_running)이 사라짐 — restart 와 별도 경로여야 한다"
    return 1
  fi
  for restart_token in "server restart" "server-restart"; do
    if ! grep -qF "$restart_token" "$hub_command_file"; then
      record_failure "$test_name" "T25-48: commands/hub.md 에 $restart_token 이 없음"
      return 1
    fi
  done
  if ! grep -E '^argument-hint:' "$hub_command_file" | grep -qF "server restart"; then
    record_failure "$test_name" "T25-48: argument-hint 에 'server restart' 미노출"
    return 1
  fi

  # T25-49(브라우저 포커스 회귀): 포커스 경로가 hub_daemon 에 하나만 있고, 셸을 거치지 않으며,
  # hub.py 에는 webbrowser 직접 호출이 남지 않는다(경로 이중화 방지).
  local focus_token
  for focus_token in "def browser_open_command" "/usr/bin/open" "darwin" "webbrowser"; do
    if ! grep -qF "$focus_token" "$hub_daemon_file"; then
      record_failure "$test_name" "T25-49: hub_daemon.py 에 $focus_token 이 없음"
      return 1
    fi
  done
  if grep -qF "shell=True" "$hub_daemon_file"; then
    record_failure "$test_name" "T25-49: hub_daemon.py 가 shell=True 를 씀 — URL 을 셸에 넘기지 않는다"
    return 1
  fi
  if grep -qF "webbrowser" "$hub_py_file"; then
    record_failure "$test_name" "T25-49: hub.py 에 webbrowser 직접 호출이 남음 — hub_daemon.open_browser 로 단일화할 것"
    return 1
  fi
  if ! grep -qF "browser_focus_requested" "$hub_command_file"; then
    record_failure "$test_name" "T25-49: commands/hub.md 에 browser_focus_requested 보고 규칙이 없음"
    return 1
  fi
  for focus_token in "restart" "포커스"; do
    if ! grep -qF "$focus_token" "$hub_readme_file"; then
      record_failure "$test_name" "T25-49: hub/README.md 에 서버 제어 설명($focus_token)이 없음"
      return 1
    fi
  done

  # T25-50(결정 W1 회귀): 그리드 트랙 최소폭이 3열 상한 계산식으로 바뀌었고, hub/README.md 의
  # 열 수 고지가 1~3열로 갱신돼 있다.
  if ! grep -qF "max(320px" "$hub_template_file"; then
    record_failure "$test_name" "T25-50: hub_template.html 에 max(320px 트랙 계산이 없음"
    return 1
  fi
  if ! grep -qF "/3 - 1px)" "$hub_template_file"; then
    record_failure "$test_name" "T25-50: hub_template.html 에 3열 상한 계산(/3 - 1px)이 없음(GOTCHA 1)"
    return 1
  fi
  if ! grep -qF "1~3열" "$hub_readme_file"; then
    record_failure "$test_name" "T25-50: hub/README.md 의 열 수 고지가 1~3열로 갱신되지 않음"
    return 1
  fi

  # T25-51(결정 V1 회귀): 완료 세션 숨김 필터는 클라이언트에만 있다 — 서버(hub_model)는
  # 세션을 걸러내지 않는다(sessions=session_views 가 그대로 있다는 것이 그 증거다).
  local client_filter_token
  for client_filter_token in "shouldRenderSession" "visibleAgentRuns"; do
    if ! grep -qF "$client_filter_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-51: hub_template.html 에 $client_filter_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF "sessions=session_views" "$hub_model_file"; then
    record_failure "$test_name" "T25-51: hub_model.py 가 세션을 걸러내는 것으로 보임(sessions=session_views 부재)"
    return 1
  fi

  # T25-52(결정 K1~K3 회귀 — 안 A): "+N" 오버플로 칩 로직(overflowRuns)이 없고,
  # summarize_agent_runs 의 정렬 키에 실행 중 우선순위(K2)가 반영돼 있다.
  if grep -qF "overflowRuns" "$hub_template_file"; then
    record_failure "$test_name" "T25-52: hub_template.html 에 오버플로 칩 흔적(overflowRuns)이 남아 있음"
    return 1
  fi
  if ! grep -qF "0 if is_running_by_type[agent_type] else 1" "$hub_model_file"; then
    record_failure "$test_name" "T25-52: hub_model.py 의 summarize_agent_runs 정렬 키에 실행 중 우선순위(K2)가 없음"
    return 1
  fi

  # T25-53(GOTCHA 2 회귀 — 결정 Z1): STALE_SESSION_HIDE_AFTER_MS 가 존재하고, MS_PER_HOUR
  # 선언보다 뒤에 선언돼 있다. var 호이스팅은 선언만 끌어올리고 할당은 올리지 않으므로 앞에
  # 두면 12 * undefined = NaN 이 되어 컷오프가 조용히 죽는다.
  local ms_per_hour_decl_line stale_cutoff_decl_line
  ms_per_hour_decl_line=$(grep -n "var MS_PER_HOUR" "$hub_template_file" | head -1 | cut -d: -f1)
  stale_cutoff_decl_line=$(grep -n "var STALE_SESSION_HIDE_AFTER_MS" "$hub_template_file" | head -1 | cut -d: -f1)
  if [[ -z "$ms_per_hour_decl_line" || -z "$stale_cutoff_decl_line" ]]; then
    record_failure "$test_name" "T25-53: MS_PER_HOUR/STALE_SESSION_HIDE_AFTER_MS 선언을 hub_template.html 에서 찾지 못함"
    return 1
  fi
  if [[ "$stale_cutoff_decl_line" -le "$ms_per_hour_decl_line" ]]; then
    record_failure "$test_name" "T25-53: STALE_SESSION_HIDE_AFTER_MS 가 MS_PER_HOUR 보다 앞서 선언됨(GOTCHA 2)"
    return 1
  fi

  # T25-54(결정 P1 회귀 — 퍼센트 출처 교체): 데스크톱 앱 사용량 히스토리 경로·파서가
  # 소스에 남아 있지 않고, 캡처 단일 출처의 새 계약(신규 필드·투영 함수·비교 함수)이 있다.
  local hub_usage_file="$REPO_ROOT/hub/bin/hub_usage.py"
  local desktop_usage_token
  for desktop_usage_token in "plan-usage-history" "PLAN_USAGE_HISTORY_PATH" "parse_usage_history"; do
    if grep -qF "$desktop_usage_token" "$hub_collect_file" || grep -qF "$desktop_usage_token" "$hub_usage_file"; then
      record_failure "$test_name" "T25-54: hub_collect.py/hub_usage.py 에 데스크톱 앱 흔적($desktop_usage_token)이 남아 있음"
      return 1
    fi
  done
  local capture_source_token
  for capture_source_token in "session_used_percent" "usage_sample_from_capture" "same_capture_values"; do
    if ! grep -qF "$capture_source_token" "$hub_usage_file"; then
      record_failure "$test_name" "T25-54: hub_usage.py 에 캡처 단일 출처 토큰($capture_source_token)이 없음"
      return 1
    fi
  done

  # T25-55(문서 정합 — 결정 P1, R1 로 재개정): commands/hub.md 의 usage_sample_age_ms 설명에
  # 데스크톱 앱 문구가 없고, 퍼센트 출처가 명시돼 있다. "유일한 출처"는 R1(사용량 API 폴링,
  # 결정 A2)이 두 번째 생산자를 더하면서 더 이상 참이 아니게 됐다 — "퍼센트의 출처는" 으로
  # 완화해 두 생산자를 모두 포괄한다(T25-54 가 이미 겪은 것과 같은 종류의 재개정).
  if grep -qF "macOS 데스크톱 앱" "$hub_command_file"; then
    record_failure "$test_name" "T25-55: commands/hub.md 에 macOS 데스크톱 앱 문구가 남아 있음(결정 P1 위반)"
    return 1
  fi
  if ! grep -qF "퍼센트의 출처는" "$hub_command_file"; then
    record_failure "$test_name" "T25-55: commands/hub.md 의 usage_sample_age_ms 설명에 출처 설명이 없음"
    return 1
  fi

  # T25-56(전제 2 회귀 — #dzh-data 계약 불변): HubSnapshot 의 usage·rate_limit_resets 두
  # 필드가 그대로 있고, 템플릿이 여전히 snapshot.usage·snapshot.rate_limit_resets 를 읽는다.
  if ! grep -qF "usage: UsageSample | None = None" "$hub_model_file"; then
    record_failure "$test_name" "T25-56: hub_model.py 의 HubSnapshot.usage 필드가 계약과 다름"
    return 1
  fi
  if ! grep -qF "rate_limit_resets: RateLimitResets | None = None" "$hub_model_file"; then
    record_failure "$test_name" "T25-56: hub_model.py 의 HubSnapshot.rate_limit_resets 필드가 계약과 다름"
    return 1
  fi
  local snapshot_field_token
  for snapshot_field_token in "snapshot.usage" "snapshot.rate_limit_resets"; do
    if ! grep -qF "$snapshot_field_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-56: hub_template.html 이 $snapshot_field_token 를 읽지 않음"
      return 1
    fi
  done

  # T25-57(R3 서버 라우팅 회귀, hub-card-interactions-and-usage.md 결정 N3): 프로젝트
  # 대시보드 라우트는 정규식으로만 해석되고, 기존 화이트리스트는 그대로 남으며, 요청
  # 문자열(self.path)로 경로를 조립하는 코드가 없다.
  if ! grep -qF "PROJECT_DASHBOARD_PATH_PATTERN" "$hub_server_file"; then
    record_failure "$test_name" "T25-57: hub_server.py 에 PROJECT_DASHBOARD_PATH_PATTERN 이 없음"
    return 1
  fi
  if ! grep -qF '[0-9a-f]{16}' "$hub_server_file"; then
    record_failure "$test_name" "T25-57: hub_server.py 에 [0-9a-f]{16} 패턴이 없음"
    return 1
  fi
  if ! grep -qF "ALLOWED_REQUEST_PATHS" "$hub_server_file"; then
    record_failure "$test_name" "T25-57: hub_server.py 에 ALLOWED_REQUEST_PATHS 가 없음(T25-15 보강)"
    return 1
  fi
  local path_concat_token
  for path_concat_token in "os.path.join" "/ self.path" "+ self.path"; do
    if grep -qF "$path_concat_token" "$hub_server_file"; then
      record_failure "$test_name" "T25-57: hub_server.py 가 요청 문자열로 경로를 조립하는 것으로 보임($path_concat_token)"
      return 1
    fi
  done

  # T25-58(R4 회귀, 결정 X1): .project-name 에 data-tooltip 이 없다 — 보이는 텍스트와
  # 같아 제거해도 정보 손실이 없다.
  if grep -qF 'project-name" data-tooltip' "$hub_template_file"; then
    record_failure "$test_name" "T25-58: hub_template.html 의 project-name 에 data-tooltip 잔재가 있음"
    return 1
  fi

  # T25-59(R5 회귀, 결정 E1~E3): 헤더 버튼 클러스터가 고정 위치를 버리고 .head-row 문서
  # 흐름 안으로 들어왔다.
  if grep -qF "padding-right:150px" "$hub_template_file"; then
    record_failure "$test_name" "T25-59: hub_template.html 에 padding-right:150px 잔재가 있음"
    return 1
  fi
  if grep -qF "position:fixed;top:16px;right:16px" "$hub_template_file"; then
    record_failure "$test_name" "T25-59: hub_template.html 에 .top-actions 고정 위치 잔재가 있음"
    return 1
  fi
  if ! grep -qF ".head-row{display:flex" "$hub_template_file"; then
    record_failure "$test_name" "T25-59: hub_template.html 에 .head-row{display:flex 가 없음"
    return 1
  fi
  if ! grep -qF ".top-actions{margin-left:auto" "$hub_template_file"; then
    record_failure "$test_name" "T25-59: hub_template.html 에 .top-actions{margin-left:auto 가 없음"
    return 1
  fi

  # T25-60(R1 보안 불변식, 결정 A4): hub_usage_fetch.py 에 shell=True·print(·str(error) 가
  # 없고, FAILURE_REASON_MESSAGES 고정 어휘가 있다(불변식 A-SEC).
  local hub_usage_fetch_file="$REPO_ROOT/hub/bin/hub_usage_fetch.py"
  local forbidden_token
  for forbidden_token in "shell=True" "print(" "str(error)"; do
    if grep -qF "$forbidden_token" "$hub_usage_fetch_file"; then
      record_failure "$test_name" "T25-60: hub_usage_fetch.py 에 금지 토큰($forbidden_token)이 있음"
      return 1
    fi
  done
  if ! grep -qF "FAILURE_REASON_MESSAGES" "$hub_usage_fetch_file"; then
    record_failure "$test_name" "T25-60: hub_usage_fetch.py 에 FAILURE_REASON_MESSAGES 가 없음"
    return 1
  fi

  # T25-61(R1 구조): hub_usage.py 에 parse_usage_api_response, hub_model.py 에
  # should_attempt_usage_api_poll·UsageApiPollState, hub_collect.py 에 usage_api_enabled
  # 타입 등록이 있다(T25-10 이 hub_usage.py·hub_model.py 의 순수성을 이미 강제한다).
  if ! grep -qF "parse_usage_api_response" "$hub_usage_file"; then
    record_failure "$test_name" "T25-61: hub_usage.py 에 parse_usage_api_response 가 없음"
    return 1
  fi
  local model_token
  for model_token in "should_attempt_usage_api_poll" "UsageApiPollState"; do
    if ! grep -qF "$model_token" "$hub_model_file"; then
      record_failure "$test_name" "T25-61: hub_model.py 에 $model_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF '"usage_api_enabled": bool' "$hub_collect_file"; then
    record_failure "$test_name" "T25-61: hub_collect.py 의 _CONFIG_FIELD_TYPES 에 usage_api_enabled 등록이 없음"
    return 1
  fi

  # T25-62(R2 회귀): 카드 순서 저장·드래그 핸들 관련 토큰이 존재하고, 구 함수
  # stableSortedProjects 는 orderedProjectPaths 로 대체돼 사라졌다.
  local order_token
  for order_token in "'dzh-project-order'" "orderedProjectPaths" "isReordering" "card-drag-handle"; do
    if ! grep -qF "$order_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-62: hub_template.html 에 $order_token 이 없음"
      return 1
    fi
  done
  if grep -qF "stableSortedProjects" "$hub_template_file"; then
    record_failure "$test_name" "T25-62: hub_template.html 에 구 함수 stableSortedProjects 가 남아 있음"
    return 1
  fi

  # T25-63(R3·R6 마크업 회귀, 결정 N5·Y1~Y4): 대시보드 모달 마크업과 .icon-btn 공통
  # 클래스가 존재하고, 테마 토글은 라이트/다크 2상태만 남았다.
  local modal_markup_token
  for modal_markup_token in '<dialog id="dzh-dashboard-modal"' 'id="dzh-modal-frame"' ".icon-btn"; do
    if ! grep -qF "$modal_markup_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-63: hub_template.html 에 $modal_markup_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF "THEME_CYCLE = ['light', 'dark']" "$hub_template_file"; then
    record_failure "$test_name" "T25-63: hub_template.html 의 THEME_CYCLE 이 2상태가 아님"
    return 1
  fi
  if grep -qF "'system'" "$hub_template_file"; then
    record_failure "$test_name" "T25-63: hub_template.html 에 3상태 테마 잔재('system')가 남아 있음"
    return 1
  fi

  # T25-64(문서 정합, M5): hub/README.md 에 카드 순서·모달·usage_api_enabled 설명이 있고,
  # commands/hub.md 에 usage_api_last_failure 설명이 있다.
  local readme_doc_token
  for readme_doc_token in "카드 순서" "모달" "usage_api_enabled"; do
    if ! grep -qF "$readme_doc_token" "$hub_readme_file"; then
      record_failure "$test_name" "T25-64: hub/README.md 에 $readme_doc_token 설명이 없음"
      return 1
    fi
  done
  if ! grep -qF "usage_api_last_failure" "$hub_command_file"; then
    record_failure "$test_name" "T25-64: commands/hub.md 에 usage_api_last_failure 설명이 없음"
    return 1
  fi

  # T25-65(R3): working 카드 glow — CSS 규칙 + JS 방출 + pulse·접근성 분기가 모두 있어야
  # 신호 자체와 저감 대응이 함께 산다(개정 1 — pulse 와 reduced-motion 분기는 반드시 함께).
  local r3_token
  for r3_token in '.card.card-working{' "card-working'" '@keyframes card-working-glow' 'prefers-reduced-motion'; do
    if ! grep -qF -- "$r3_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-65: hub_template.html 에 $r3_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF '작업중' "$hub_readme_file"; then
    record_failure "$test_name" "T25-65: hub/README.md 「화면 배치」에 작업중 강조 설명이 없음"
    return 1
  fi

  # T25-66(R4): 바깥 클릭 리스너 — closest 가드 2종이 있어야 하고, GOTCHA 2 를 줄 번호
  # 비교로 기계적으로 강제한다(T25-53 선례) — if(!isServed){ 뒤로 가면 file:// 모드에서
  # 기능이 조용히 사라진다.
  if ! grep -qF "closest('#dzh-usage')" "$hub_template_file"; then
    record_failure "$test_name" "T25-66: closest('#dzh-usage') 가드 미발견"
    return 1
  fi
  if ! grep -qF "closest('dialog')" "$hub_template_file"; then
    record_failure "$test_name" "T25-66: closest('dialog') 가드 미발견"
    return 1
  fi
  # if(!isServed){ 는 renderConnectionStatus() 안에도 한 번 더 나온다(무관한 기존 코드) —
  # 리스너 등록을 지키는 실제 게이트는 IIFE 끝의 reload 분기이므로 **마지막** 등장을 앵커로
  # 쓴다(T22-37 이 pip 버튼 위치를 마지막 등장으로 판정하는 것과 같은 관례).
  local outside_click_guard_line is_served_gate_line
  outside_click_guard_line=$(grep -n "closest('#dzh-usage')" "$hub_template_file" | head -1 | cut -d: -f1)
  is_served_gate_line=$(grep -n 'if(!isServed){' "$hub_template_file" | tail -1 | cut -d: -f1)
  if [[ -z "$outside_click_guard_line" || -z "$is_served_gate_line" || "$outside_click_guard_line" -ge "$is_served_gate_line" ]]; then
    record_failure "$test_name" "T25-66: 바깥 클릭 리스너가 if(!isServed){ 뒤에 등록됨(GOTCHA 2 위반)"
    return 1
  fi
  if ! grep -qF '바깥' "$hub_readme_file"; then
    record_failure "$test_name" "T25-66: hub/README.md 사용량 패널 절에 바깥 클릭 설명이 없음"
    return 1
  fi

  # T25-67(R5, 역방향 중심): 패널 안 툴팁 2종과 죽은 옵저버가 사라졌는지 확인하면서도,
  # renderUsageResetRow·usage-meta·data-tooltip(패널 밖)은 여전히 살아 있어야 한다 —
  # "지운 것"과 "지우면 안 되는 것"을 함께 감사한다.
  if grep -qF '이 정보를 확인한 시각' "$hub_template_file"; then
    record_failure "$test_name" "T25-67: '이 정보를 확인한 시각' 툴팁 문구가 남아 있음"
    return 1
  fi
  if grep -qF 'usage-meta" data-tooltip' "$hub_template_file"; then
    record_failure "$test_name" "T25-67: usage-meta 의 data-tooltip 속성이 남아 있음"
    return 1
  fi
  # ③ 반전(R-B): R5 는 이 옵저버를 지웠지만(결정 UT4), R-B 가 조건부로 되살렸다(결정 EX7) —
  # 만료 안내 줄(.usage-stale-note)이 패널 안 유일한 트리거이므로 T25-71 이 이 복원을 강제한다.
  if ! grep -qF 'usageBodyElForTooltipObserver' "$hub_template_file"; then
    record_failure "$test_name" "T25-67: usageBodyElForTooltipObserver 가 없음(R-B 가 조건부로 복원해야 함, 결정 EX7)"
    return 1
  fi
  if ! grep -qF 'renderUsageResetRow' "$hub_template_file"; then
    record_failure "$test_name" "T25-67: renderUsageResetRow 함수가 사라짐(과잉 제거)"
    return 1
  fi
  if ! grep -qF 'usage-meta' "$hub_template_file" || ! grep -qF 'data-tooltip' "$hub_template_file"; then
    record_failure "$test_name" "T25-67: usage-meta 또는 data-tooltip(패널 밖) 이 과잉 제거됨"
    return 1
  fi
  if ! grep -qF 'rate_limit_capture_age_ms' "$hub_readme_file"; then
    record_failure "$test_name" "T25-67: hub/README.md 에 캡처 시각 진단 창구(rate_limit_capture_age_ms) 언급이 없음"
    return 1
  fi

  # T25-68(R7, 정·역 혼합): 라이브 이동 구현 4토큰이 있고, 제거된 키보드 경로의 흔적 6종은
  # 전부 0건이어야 한다(전수 확인 — PRP 자체 확인 결과와 일치).
  local r7_positive_token
  for r7_positive_token in 'setDragImage' 'compareDocumentPosition' 'card-dragging' 'commitReorder(currentCardOrder())'; do
    if ! grep -qF -- "$r7_positive_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-68: hub_template.html 에 $r7_positive_token 이 없음"
      return 1
    fi
  done
  local r7_removed_token
  for r7_removed_token in 'keyboardMoveTargetIndex' 'announceProjectPosition' 'moveProjectPath' 'dzh-live' 'restoreHandleFocusAfterRender' 'ArrowLeft'; do
    if grep -qF -- "$r7_removed_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-68: hub_template.html 에 제거 대상 $r7_removed_token 이 남아 있음"
      return 1
    fi
  done
  local card_order_section
  card_order_section=$(sed -n '/^## 카드 순서/,/^## /p' "$hub_readme_file")
  if grep -qF '←' <<< "$card_order_section"; then
    record_failure "$test_name" "T25-68: hub/README.md 「카드 순서」에 ← 가 남아 있음(키보드 조작 잔재)"
    return 1
  fi
  if ! grep -qF '드래그' <<< "$card_order_section"; then
    record_failure "$test_name" "T25-68: hub/README.md 「카드 순서」에 드래그 설명이 없음"
    return 1
  fi

  # T25-69(R8): 모달 depth·경계 — ::backdrop·테두리가 있고 옛 border:0 은 사라졌는지 확인한다.
  if ! grep -qF '.modal::backdrop{' "$hub_template_file"; then
    record_failure "$test_name" "T25-69: .modal::backdrop 규칙이 없음"
    return 1
  fi
  local modal_rule_line
  modal_rule_line=$(grep -n '^  \.modal{' "$hub_template_file" | head -1 | cut -d: -f1)
  if [[ -z "$modal_rule_line" ]]; then
    record_failure "$test_name" "T25-69: .modal{ 규칙을 찾지 못함"
    return 1
  fi
  local modal_rule_text
  modal_rule_text=$(sed -n "${modal_rule_line},+2p" "$hub_template_file")
  if ! grep -qF 'border:1px solid var(--line)' <<< "$modal_rule_text"; then
    record_failure "$test_name" "T25-69: .modal 규칙에 border:1px solid var(--line) 이 없음"
    return 1
  fi
  if grep -qF 'border:0' <<< "$modal_rule_text"; then
    record_failure "$test_name" "T25-69: .modal 규칙에 옛 border:0 이 남아 있음"
    return 1
  fi
  if ! grep -qF '어둡' "$hub_readme_file"; then
    record_failure "$test_name" "T25-69: hub/README.md 모달 절에 배경 어두워짐 설명이 없음"
    return 1
  fi

  # T25-70: 모달 열기 애니메이션 — 애니메이션 규칙 2개와 reduced-motion 무효화가 세트로
  # 있어야 한다(T25-65 의 card-working-glow 와 같은 원칙 — 하나만 지워지는 회귀를 막는다).
  local modal_animation_token
  for modal_animation_token in 'animation:modal-open' '@keyframes modal-open' '@keyframes backdrop-fade' '.modal[open],.modal[open]::backdrop{animation:none}'; do
    if ! grep -qF -- "$modal_animation_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-70: hub_template.html 에 $modal_animation_token 이 없음"
      return 1
    fi
  done

  # T25-71(R-B 표시 + 툴팁 복원): 만료(조회되지 않음) 표시 토큰 4개가 있고, 그 툴팁 트리거를
  # 위해 tooltipDismissObserver 가 #dzh-usage-body 를 다시 관찰한다(GOTCHA 1 의 기계적 강제).
  local stale_display_token
  for stale_display_token in "usage-stale-note" "USAGE_STALE_TOOLTIP" "usage-pct-empty" "is_stale"; do
    if ! grep -qF -- "$stale_display_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-71: hub_template.html 에 $stale_display_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF "tooltipDismissObserver.observe(usageBodyElForTooltipObserver" "$hub_template_file"; then
    record_failure "$test_name" "T25-71: tooltipDismissObserver 가 #dzh-usage-body 를 다시 관찰하지 않음(GOTCHA 1)"
    return 1
  fi

  # T25-72(R-B 파이썬 계약): UsageSample.is_stale·mark_stale_usage_sample 이 hub_usage.py 에
  # 있고, hub_collect.py 가 그 함수를 부른다. 역방향(핵심) — _capture_for_snapshot 범위 안에
  # 만료 시 지우던 옛 경로(usage = None)가 되살아나지 않았다.
  if ! grep -qF "is_stale: bool = False" "$hub_usage_file"; then
    record_failure "$test_name" "T25-72: hub_usage.py 에 is_stale: bool = False 필드가 없음"
    return 1
  fi
  if ! grep -qF "def mark_stale_usage_sample" "$hub_usage_file"; then
    record_failure "$test_name" "T25-72: hub_usage.py 에 mark_stale_usage_sample 함수가 없음"
    return 1
  fi
  if ! grep -qF "mark_stale_usage_sample" "$hub_collect_file"; then
    record_failure "$test_name" "T25-72: hub_collect.py 가 mark_stale_usage_sample 을 호출하지 않음"
    return 1
  fi
  local capture_for_snapshot_body
  capture_for_snapshot_body=$(sed -n '/^def _capture_for_snapshot/,/^# ---- 합성 ----/p' "$hub_collect_file")
  if echo "$capture_for_snapshot_body" | grep -qF "usage = None"; then
    record_failure "$test_name" "T25-72: _capture_for_snapshot 에 옛 숨김 경로(usage = None)가 되살아남"
    return 1
  fi

  # T25-73(R-A 온보딩 + 소유권 원칙): 정방향 — commands/hub.md 의 /hub install 절에
  # install-statusline 이 있고, hub/install.sh 의 "다음 단계" 줄과 hub/README.md 「빠른 시작」에
  # 상태줄 언급이 있다. 역방향(핵심, 전제 1 의 기계적 강제) — hub/install.sh 는 settings.json 도
  # install-statusline 도 모른다.
  local hub_install_section
  hub_install_section=$(sed -n '/^## `\/hub install`/,/^## `\/hub off`/p' "$hub_command_file")
  if ! echo "$hub_install_section" | grep -qF "install-statusline"; then
    record_failure "$test_name" "T25-73: commands/hub.md 의 /hub install 절에 install-statusline 이 없음"
    return 1
  fi
  if ! grep -F "다음 단계" "$hub_install_file" | grep -qF "상태줄"; then
    record_failure "$test_name" "T25-73: hub/install.sh 의 '다음 단계' 안내에 상태줄 언급이 없음"
    return 1
  fi
  local quick_start_section
  quick_start_section=$(sed -n '/^## 빠른 시작/,/^## /p' "$hub_readme_file")
  if ! echo "$quick_start_section" | grep -qF "상태줄"; then
    record_failure "$test_name" "T25-73: hub/README.md 「빠른 시작」에 상태줄 언급이 없음"
    return 1
  fi
  if grep -qF "settings.json" "$hub_install_file"; then
    record_failure "$test_name" "T25-73: hub/install.sh 가 settings.json 을 언급함(전제 1 위반)"
    return 1
  fi
  # "install-statusline" 은 기존 --uninstall 절차의 "uninstall-statusline" 호출 안에도 부분
  # 문자열로 존재한다(u+install-statusline) — 그 문자열 자체를 금지하면 항상 거짓양성이 난다.
  # 실제로 막아야 할 것은 **단독 직접 호출**이므로, 전체 등장 횟수가 uninstall-statusline
  # 등장 횟수와 같은지(=모든 등장이 그 안에만 있는지)로 판정한다.
  local install_statusline_total uninstall_statusline_total
  install_statusline_total=$(grep -oF "install-statusline" "$hub_install_file" | wc -l | tr -d ' ')
  uninstall_statusline_total=$(grep -oF "uninstall-statusline" "$hub_install_file" | wc -l | tr -d ' ')
  if [[ "$install_statusline_total" -ne "$uninstall_statusline_total" ]]; then
    record_failure "$test_name" "T25-73: hub/install.sh 가 install-statusline 을 (uninstall-statusline 바깥에서) 직접 호출함(전제 1 위반)"
    return 1
  fi

  # T25-74(문서 정합): hub/README.md 사용량 패널 절에 '조회되지 않음' 설명이 있고, 역방향 —
  # R-B 이전의 낡은 숨김 서술("5시간보다 오래됐거나 … 패널 전체를 표시하지 않는다")이 남아
  # 있지 않다(문서와 동작이 어긋난 채 방치되는 것을 막는다).
  local usage_panel_section
  usage_panel_section=$(sed -n '/^## 사용량 패널/,/^## /p' "$hub_readme_file")
  if ! echo "$usage_panel_section" | grep -qF "조회되지 않음"; then
    record_failure "$test_name" "T25-74: hub/README.md 사용량 패널 절에 '조회되지 않음' 설명이 없음"
    return 1
  fi
  if echo "$usage_panel_section" | grep -qF "5시간보다 오래됐거나(세션을 한동안 안"; then
    record_failure "$test_name" "T25-74: hub/README.md 에 R-B 이전의 낡은 숨김 서술이 남아 있음"
    return 1
  fi

  log_ok "$test_name 통과"
  ((passed_tests++))
}

register_and_run_tests() {
  test_scope_project_new_install || true
  test_scope_user_new_install || true
  test_idempotency || true
  test_partial_damage_recovery || true
  test_claude_md_conflict || true
  test_force_backup || true
  test_force_double_run || true
  test_dry_run_no_side_effect || true
  test_missing_scope || true
  test_no_write_permission || true
  test_paths_frontmatter_preserved || true
  test_relative_path_references_work || true
  test_symlink_target_warning || true
  test_diff_detection_requires_force || true
  test_unmanaged_files_preserved || true
  test_commands_installed || true
  test_global_command_overlap_report || true
  test_global_report_skipped_for_user_scope || true
  test_manifest_created_after_install || true
  test_manifest_fields_complete || true
  test_dashboard_template_integrity || true
  test_dashboard_option_docs || true
  test_hub_unit_tests || true
  test_hub_docs_and_constants || true
}

# 테스트 결과 요약 출력
print_test_summary() {
  echo ""
  echo "=========================================="
  echo "테스트 결과"
  echo "=========================================="
  echo "총 테스트: $total_tests"
  echo -e "통과: ${GREEN}$passed_tests${NC}"
  echo -e "실패: ${RED}$failed_tests${NC}"

  if [[ $failed_tests -gt 0 ]]; then
    echo ""
    echo "실패한 테스트:"
    for failure in "${failed_list[@]}"; do
      echo "  - $failure"
    done
    echo ""
    return 1
  fi

  echo ""
  log_ok "모든 테스트 통과"
  return 0
}

# ============================================================================
# 메인 러너
# ============================================================================

main() {
  echo ""
  echo "=========================================="
  echo "coding-env install.sh 테스트 스위트"
  echo "=========================================="
  echo ""

  # install.sh 존재 확인
  if [[ ! -f "$INSTALL_SCRIPT" ]]; then
    log_error "install.sh 미존재: $INSTALL_SCRIPT"
    exit 1
  fi

  log_info "레포 루트: $REPO_ROOT"
  log_info "install.sh: $INSTALL_SCRIPT"
  echo ""

  # 전체 테스트 개수
  total_tests=24  # T1~T25 (T11 결번)

  # 각 테스트 실행
  register_and_run_tests

  # 결과 출력
  print_test_summary
}

main "$@"
