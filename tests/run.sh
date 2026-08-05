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

  # commands 8개 확인
  local commands_count
  commands_count=$(count_files_recursive "./.claude/commands")
  if ! assert_equals 8 "$commands_count" "commands 파일 개수"; then
    record_failure "$test_name" "commands 파일 개수: 기대=8, 실제=$commands_count"
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

# T17: 커맨드 8종(의존 사슬 7종 + 독립 커맨드 1종)이 설치되고 의존 사슬이 닫히는지 확인
test_commands_installed() {
  local test_name="T17"
  local test_desc="커맨드 8종 설치 및 의존 사슬 완결"
  log_test_name "$test_name" "$test_desc"

  local sandbox
  sandbox=$(mktemp -d)
  trap "rm -rf '$sandbox'" EXIT

  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1

  local command_name
  for command_name in prp-prd prp-plan prp-implement prp-pr prp-commit code-review env-update dashboard; do
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
  if ! echo "$output" | grep -q "전역에 동일한 커맨드 7개"; then
    record_failure "$test_name" "동일 7개 안내가 없음"
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
# 설치·문서 정합성만 자동 검증한다 (하위 검증 T22-1~T22-15).
test_dashboard_template_integrity() {
  local test_name="T22"
  local test_desc="dashboard 템플릿 무결성 (T22-1~T22-15)"
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

  # T22-2: 필수 셀렉터 7종이 템플릿에 모두 존재
  local required_selector
  for required_selector in dz-title dz-subtitle dz-progress-bar dz-progress-pct dz-step- \
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

  # T22-6: init 절차에 기존 파일 덮어쓰기 가드 문구 존재 (재발 방지책)
  # 실행 코드가 없는 LLM 지시문이라 가드 "로직"의 실제 동작은 검증할 수 없고,
  # 지시문 안에 가드 문구가 남아있는지만 grep 으로 확인한다.
  if ! grep -q "덮어쓰지 않는다" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-6: init 기존 파일 가드 문구 미발견"
    return 1
  fi

  # T22-7: div.legend 컴포넌트가 템플릿에서 제거됐는지 확인 (사용자 요청, 회귀 방지)
  if grep -q 'class="legend"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-7: div.legend 가 여전히 템플릿에 남아있음"
    return 1
  fi

  # T22-8: 세션 구분 마커(session-head) 가 템플릿/절차에 존재하는지 확인
  if ! grep -q "session-head" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-8: session-head 세션 구분 마커 미발견"
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

  # T22-11: 템플릿의 #dz-log 여는 태그에 현재 세션 번호가 박혀 있음
  if ! grep -q 'id="dz-log" data-current-session="1"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-11: #dz-log 의 data-current-session=\"1\" 기본값 미발견"
    return 1
  fi

  # T22-12: log 절차가 깨진 완전일치 grep 으로 퇴행하지 않았는지 확인 (이번 라운드에서 가장 중요한 테스트).
  # #dz-log 여는 태그가 data-current-session 을 갖는 순간 완전일치는 영원히 매칭에 실패하므로
  # 옛 패턴의 부활과 새 패턴의 누락을 양방향으로 막는다.
  if grep -q "grep -n '<ul class=\"log\" id=\"dz-log\">'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-12: 깨진 완전일치 grep 패턴이 여전히 남아있음"
    return 1
  fi
  if ! grep -q "grep -n 'id=\"dz-log\"'" "$dashboard_command_file"; then
    record_failure "$test_name" "T22-12: 부분일치 grep 패턴 미발견"
    return 1
  fi

  # T22-13: 로그 항목 스키마에 data-session 이 포함됨
  if ! grep -q 'data-seq="12" data-session="2"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-13: 로그 항목 스키마의 data-session 미발견"
    return 1
  fi

  # T22-14: 세션 탭 CSS 골격과 삽입 마커가 템플릿에 존재
  if ! grep -q 'label\[for\^="dzs-"\]' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-14: 세션 탭 라벨 CSS 골격 미발견"
    return 1
  fi
  if ! grep -q 'DZ:SESSION-RULES' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-14: DZ:SESSION-RULES 삽입 마커 미발견"
    return 1
  fi

  # T22-15: 새 탭에 checked 를 넣지 말라는 문구가 절차에 존재
  # (checked 중복으로 사용자의 탭 선택이 매 새로고침마다 리셋되는 버그 방지)
  if ! grep -q '새 탭 라디오에 `checked` 를 넣지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-15: 새 탭 checked 금지 문구 미발견"
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
  total_tests=21  # T1~T22 (T11 결번)

  # 각 테스트 실행
  register_and_run_tests

  # 결과 출력
  print_test_summary
}

main "$@"
