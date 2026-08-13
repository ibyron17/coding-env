#!/bin/bash
# 허브 전용 설치기 — coding-env 의 루트 install.sh 와 완전히 독립적이다.
#
# 허브는 머신 전역 자산이다(개정 쟁점 R5) — 설치 위치는 ~/.claude/hub/bin 하나뿐이고
# --scope 인자가 없다. coding-env 를 설치했다고 허브가 함께 설치되지 않는다(요구 R-5).
#
# 소유권 원칙(루트 install.sh 와 동일): 이 스크립트는 hub/bin 이 배포하는 파일만 관리한다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
readonly REPO_ROOT
readonly HUB_FILE_COUNT=12
readonly MAX_DIFF_LINES=20
readonly TARGET_HUB_DIR="$HOME/.claude/hub"
readonly TARGET_BIN_DIR="$TARGET_HUB_DIR/bin"
readonly SOURCE_BIN_DIR="$REPO_ROOT/hub/bin"

force_overwrite="false"
dry_run="false"
do_uninstall="false"

log_info() { echo "[INFO] $*"; }
log_warn() { echo "[WARN] $*" >&2; }
log_ok() { echo "[OK]   $*"; }
log_error() { echo "[ERROR] $*" >&2; }
log_done() { echo "[DONE] $*"; }
log_plan() { echo "  [계획] $*"; }

usage() {
  cat << 'EOF'
Usage: hub/install.sh [--force] [--dry-run] [--uninstall] [--help]

Options:
  --force        수정된 hub/bin 파일 강제 덮어쓰기
  --dry-run      계획만 출력 (파일시스템 변경 없음)
  --uninstall    서버 정지 → 훅 제거 → statusLine 제거 → hub/bin 삭제 (순서 고정. events/·hub.html·config.json 은 보존)
  --help         이 메시지 표시
EOF
}

parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force) force_overwrite="true"; shift ;;
      --dry-run) dry_run="true"; shift ;;
      --uninstall) do_uninstall="true"; shift ;;
      --help) usage; exit 0 ;;
      *) log_error "알 수 없는 옵션: $1"; usage; exit 1 ;;
    esac
  done
}

is_symlinked_path() {
  local candidate_path="$1"
  local resolved_path
  resolved_path=$(cd "$candidate_path" > /dev/null 2>&1 && /bin/pwd -P) || return 1
  if [[ "$candidate_path" == "$resolved_path" || "$candidate_path" == "${resolved_path#/private}" ]]; then
    return 1
  fi
  return 0
}

count_lines() {
  grep -c . || true
}

# 수정 감지 — 대상에 있으나 내용이 다른 관리 파일 목록 (사용자 수정 의심 → --force 필요).
# 대상에만 있는 파일(우리 소유가 아님)은 충돌로 보지 않는다 — 루트 install.sh 의 D1 원칙과 동일.
# __pycache__ 는 실행 시점마다 바뀌는 바이트코드 파생물이라 비교 대상이 아니므로 제외한다.
list_differing_managed_files() {
  diff -rq -x __pycache__ "$SOURCE_BIN_DIR" "$TARGET_BIN_DIR" 2> /dev/null | grep -E "^Files .* differ$" || true
}

check_preconditions() {
  if is_symlinked_path "$TARGET_HUB_DIR"; then
    log_error "심볼릭 링크입니다: $TARGET_HUB_DIR"
    return 1
  fi
  if [[ ! -d "$TARGET_BIN_DIR" || "$force_overwrite" == "true" ]]; then
    return 0
  fi
  local differing_list
  differing_list=$(list_differing_managed_files)
  if [[ -z "$differing_list" ]]; then
    return 0
  fi
  local differing_count
  differing_count=$(printf '%s\n' "$differing_list" | count_lines)
  log_warn "$TARGET_BIN_DIR 에서 수정된 파일이 ${differing_count}건 발견됐습니다"
  printf '%s\n' "$differing_list" | head -n "$MAX_DIFF_LINES" >&2
  log_warn "덮어쓰려면 --force 를 쓰십시오"
  return 1
}

verify_installed_file_count() {
  local installed_count
  installed_count=$(find "$TARGET_BIN_DIR" -maxdepth 1 -type f | wc -l | tr -d ' ')
  if [[ "$installed_count" -ne "$HUB_FILE_COUNT" ]]; then
    log_error "설치 검증 실패 — 기대 ${HUB_FILE_COUNT}개, 실제 ${installed_count}개"
    return 1
  fi
  return 0
}

# hub/bin 최상위의 일반 파일만 배포 대상이다 — __pycache__ 는 테스트 실행이 만든 로컬
# 바이트코드 파생물(.gitignore 대상)이라 배포하지 않는다(소유권 원칙: hub/bin 이 배포하는 파일만 관리).
copy_managed_bin_files() {
  local source_file
  while IFS= read -r -d '' source_file; do
    cp "$source_file" "$TARGET_BIN_DIR/" || return 1
  done < <(find "$SOURCE_BIN_DIR" -maxdepth 1 -type f -print0)
}

perform_install() {
  log_info "허브 설치 (coding-env 설치와 무관 — 별도 자산)"
  check_preconditions || { log_error "설치 중단 — 변경된 파일 없음"; return 1; }

  if ! mkdir -p "$TARGET_BIN_DIR"; then
    log_error "디렉토리 생성 실패: $TARGET_BIN_DIR"
    return 1
  fi
  if ! copy_managed_bin_files; then
    log_error "복사 실패: $SOURCE_BIN_DIR → $TARGET_BIN_DIR"
    return 1
  fi
  verify_installed_file_count || return 1

  log_ok "hub/bin  ${HUB_FILE_COUNT}개 파일 → $TARGET_BIN_DIR/"
  log_done "허브 설치 완료"
  log_info "다음 단계: /hub install (훅 옵트인) → /hub server start → /hub"
  log_info "자세한 설명: $REPO_ROOT/hub/README.md"
  return 0
}

log_install_plan() {
  log_info "허브 설치 계획 (DRY-RUN)"
  check_preconditions || { log_error "사전 조건 실패 — 실제 실행 시 설치되지 않습니다"; return 1; }
  log_plan "mkdir -p $TARGET_BIN_DIR"
  log_plan "hub/bin 최상위 파일 → $TARGET_BIN_DIR/   (${HUB_FILE_COUNT}개, __pycache__ 제외)"
  log_done "${HUB_FILE_COUNT}개 파일이 대상에 반영될 예정. 실제 변경 없음"
  return 0
}

# --uninstall 의 순서가 이 스크립트의 존재 이유다. bin/ 을 먼저 지우면 server-stop 도
# uninstall-hooks 도 실행할 수 없어 서버는 계속 돌고 훅은 존재하지 않는 스크립트를
# 매 이벤트마다 호출하는, 사용자가 손으로 되돌리기 가장 어려운 상태가 된다.
#
# server-stop 의 실패는 `|| true` 로 삼키지 않는다(검수 m2) — 삼키면 서버가 계속 도는 채로
# bin/ 이 삭제돼, "돌고 있는 서버 + 그 서버를 끌 유일한 수단(hub.py)의 소멸"이라는, 정지
# 수단이 사라진 상태가 만들어진다. 결과를 파싱해 ok=false 면 --force 없이는 중단한다.
#
# ok 판정은 `grep -q '"ok": true'` 같은 문자열 매칭이 아니라 실제 JSON 파싱으로 한다(검수 n1)
# — 문자열 매칭은 `json.dumps` 의 키-값 사이 공백 규칙(기본은 `": "` 지만 보장된 계약이 아니다)
# 에 결합돼, 그 규칙이 바뀌면 `ok:true` 인데도 조용히 미가동으로 오판할 수 있다.
stop_server_or_abort() {
  local hub_py="$1"
  local stop_result
  stop_result=$(python3 "$hub_py" server-stop --json)
  echo "$stop_result"
  if echo "$stop_result" | python3 -c 'import json, sys; sys.exit(0 if json.load(sys.stdin).get("ok") else 1)' 2>/dev/null; then
    return 0
  fi
  if [[ "$force_overwrite" == "true" ]]; then
    log_warn "서버 정지 실패를 --force 로 무시하고 계속합니다(서버가 계속 실행 중일 수 있습니다)"
    return 0
  fi
  log_error "서버 정지 실패 — bin/ 삭제를 중단합니다"
  log_error "그대로 진행하면 서버는 계속 도는데 끌 수단(hub.py)만 사라집니다"
  log_error "원인을 해결하거나, 그래도 강행하려면 --force 를 쓰십시오"
  return 1
}

perform_uninstall() {
  local hub_py="$TARGET_BIN_DIR/hub.py"
  if [[ -f "$hub_py" ]]; then
    log_info "상주 서버 정지 중..."
    stop_server_or_abort "$hub_py" || return 1
    log_info "훅 제거 중..."
    python3 "$hub_py" uninstall-hooks --json || true
    log_info "statusLine 제거 중..."
    python3 "$hub_py" uninstall-statusline --json || true
  else
    log_warn "$hub_py 가 없어 서버 정지·훅 제거를 건너뜁니다"
  fi

  if ! rm -rf "$TARGET_BIN_DIR"; then
    log_error "삭제 실패: $TARGET_BIN_DIR"
    return 1
  fi
  log_ok "$TARGET_BIN_DIR 삭제 완료"
  log_done "허브 제거 완료"
  log_info "사용자 데이터·잔존 상태 파일은 지우지 않았습니다 — 직접 결정하십시오:"
  log_info "  $TARGET_HUB_DIR/events/  (이벤트 로그)"
  log_info "  $TARGET_HUB_DIR/hub.html  (마지막 화면)"
  log_info "  $TARGET_HUB_DIR/config.json  (설정, 있는 경우)"
  log_info "  $TARGET_HUB_DIR/server.json, server_heartbeat  (정지 실패로 남아 있을 수 있음)"
  log_info "  $TARGET_HUB_DIR/server.log  (서버 로그)"
  log_info "  $TARGET_HUB_DIR/.collect_spawn_stamp  (훅 디바운스 스탬프)"
  log_info "  $TARGET_HUB_DIR/rate_limits.json  (한도 초기화 예정 시각 캡처, 있는 경우)"
  return 0
}

main() {
  parse_arguments "$@"

  if [[ "$do_uninstall" == "true" ]]; then
    perform_uninstall
    return $?
  fi
  if [[ "$dry_run" == "true" ]]; then
    log_install_plan
    return $?
  fi
  perform_install
}

main "$@"
