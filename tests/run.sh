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
# 설치·문서 정합성만 자동 검증한다 (하위 검증 T22-1~T22-79).
test_dashboard_template_integrity() {
  local test_name="T22"
  local test_desc="dashboard 템플릿 무결성 (T22-1~T22-79)"
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

  # T22-16: 세션 탭 줄과 유형 필터 줄을 분리하는 <br> 이 절차/문서에 존재
  # (두 라디오 그룹이 카드 폭에 따라 같은 줄에 붙어 보이던 레이아웃 문제의 회귀 방지)
  if ! grep -q '<br>' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-16: 세션 탭/유형 필터 줄바꿈(<br>) 미발견"
    return 1
  fi

  # T22-17: 특정 세션 탭 선택 시 session-head 구분선을 전부 숨기는 고정 규칙 존재
  # (사용자 요청 — 모든 세션 탭이 아니면 구분선 자체를 안 보여준다)
  if ! grep -q 'not(#dzs-all) ~ #dz-log .session-head' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-17: session-head 전체 숨김 규칙 미발견"
    return 1
  fi

  # T22-18: 세션별 항목 필터가 .entry 를 대상으로 함 (session-head 는 T22-17 규칙이 전담하므로
  # 이 규칙이 다시 li 전체(> li)를 대상으로 퇴행하지 않았는지 확인)
  if grep -q '#dz-log > li:not(\[data-session=' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-18: 세션 필터가 옛 '> li' 패턴으로 되돌아감"
    return 1
  fi
  if ! grep -q '#dzs-1:checked ~ #dz-log .entry:not(\[data-session="1"\])' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-18: 세션별 .entry 필터 규칙 미발견"
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

  # T22-59: 「지금」 카드 셀렉터 4종 존재 — 카드 자체의 유실을 막는다
  if ! grep -qF 'id="dz-now-card"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-59: id=\"dz-now-card\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-now-phase"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-59: id=\"dz-now-phase\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-now-elapsed"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-59: id=\"dz-now-elapsed\" 미발견"
    return 1
  fi
  if ! grep -qF 'id="dz-now-next"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-59: id=\"dz-now-next\" 미발견"
    return 1
  fi

  # T22-60: 자동 숨김 규칙 존재 — 매트릭스 세션·진행중 없음 상태에서 빈 카드가 노출되는 회귀를
  # 막는다(설계 결정 3·8).
  if ! grep -qF '.wrap:not(:has(#dz-steps li.active)) #dz-now-card{display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-60: 「지금」 카드 자동 숨김 규칙 미발견"
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

  # T22-62: 자동 각인 규칙 문서화 — 각인 시점이 흐려지면 매 호출마다 시각이 리셋되는 회귀로 이어진다.
  if ! grep -qF 'data-started-at' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-62: data-started-at 미발견"
    return 1
  fi
  if ! grep -q '이전 상태 ≠ `active` \*\*이고\*\* 새 상태 = `active`' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-62: data-started-at 각인 전이 조건 문구 미발견"
    return 1
  fi

  # T22-63: 파생 뷰 불변식 문구 — 유실되면 카드에 직접 쓰는 경로가 생기고 인자가 따라 붙는다.
  if ! grep -q '「지금」 카드는 파생 뷰다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-63: '「지금」 카드는 파생 뷰다' 불변식 문구 미발견"
    return 1
  fi

  # T22-64: 렌더러 배치(줄 번호 비교) — file:// 조기 반환보다 앞에 있어야 한다. 뒤에 있으면
  # file:// 로 연 대시보드에서 경과 시간이 영원히 갱신되지 않는데, http:// 테스트로는 정상으로
  # 보여 발견이 가장 어렵다(설계 결정 6).
  if ! grep -qF 'function renderNowCard(){' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-64: function renderNowCard(){ 미발견"
    return 1
  fi
  local render_tick_line early_return_line
  render_tick_line=$(grep -n 'setInterval(renderNowCard' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  early_return_line=$(grep -n 'if(!isServed){' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  if [[ -z "$render_tick_line" || -z "$early_return_line" || "$render_tick_line" -gt "$early_return_line" ]]; then
    record_failure "$test_name" "T22-64: renderNowCard 틱이 file:// 조기 반환 뒤에 있음"
    return 1
  fi

  # T22-65: 폴링이 카드를 치환하지 않음(역방향) — 파생 뷰를 파일 문자열로도 동기화하면 값 출처가
  # 둘로 갈라진다(불변식 7). 검사 범위를 <script> 블록으로 한정한다 — 데이터 모델 절의 폴링 계약
  # 표는 대조를 위해 #dz-impl-card 의 outerHTML 치환을 같은 줄에서 설명하므로, 파일 전체를 훑으면
  # 그 문서 프로즈에서 오탐이 발생한다.
  if sed -n '/^<script>/,/<\/script>/p' "$dashboard_command_file" | grep -n 'dz-now-card' | grep -qE 'outerHTML|innerHTML'; then
    record_failure "$test_name" "T22-65: dz-now-card 가 outerHTML/innerHTML 로 치환됨"
    return 1
  fi
  if ! grep -qF 'renderNowCard();' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-65: apply() 안 renderNowCard() 호출 미발견"
    return 1
  fi

  # T22-66: 매트릭스 방침 문구 — 매트릭스에서 <td> 에 각인하는 범용화 유혹을 막는다.
  if ! grep -q '매트릭스 모드(`<g>.<p>`)에서는 각인하지 않는다' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-66: 매트릭스 모드 각인 배제 문구 미발견"
    return 1
  fi

  # T22-67: PiP 미숨김(역방향) — 곁눈질 화면에서 가장 값진 카드를 숨기는 규칙의 몰래 추가를
  # 막는다(설계 결정 7).
  if grep -qF 'body.dz-pip #dz-now-card{display:none}' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-67: PiP 에서 「지금」 카드를 숨기는 규칙이 추가됨"
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
  if ! sed -n '/^## 자동 발행/,/^## `serve`/p' "$dashboard_command_file" | grep -q '폴백'; then
    record_failure "$test_name" "T22-69: 자동 발행 절 안에 폴백 표기 미발견"
    return 1
  fi

  # T22-70: init 의 두 분기 모두 자동 발행을 참조 — 한 분기만 발행하면 세션 2 가 방치된다
  # (설계 결정 3). 범위를 init 절로 좁히는 이유는 자동 발행 절 자신의 산문에서 오탐이 나기 때문이다.
  local init_section_autopublish_count
  init_section_autopublish_count=$(sed -n '/^## `init`/,/^## `step`/p' "$dashboard_command_file" | grep -c '자동 발행')
  if [[ "$init_section_autopublish_count" -lt 2 ]]; then
    record_failure "$test_name" "T22-70: init 절 범위에서 '자동 발행' 참조가 2회 미만"
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
  total_tests=22  # T1~T23 (T11 결번)

  # 각 테스트 실행
  register_and_run_tests

  # 결과 출력
  print_test_summary
}

main "$@"
