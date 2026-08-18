"""hub_collect.py — I/O 레이어. 프로젝트 발견 · 3티어 읽기 · 스냅샷 조립 · hub.html 원자적 쓰기.

hub/bin 안에서 파일시스템·프로세스·네트워크에 닿는 유일한 모듈이다.
hub_model.py·hub_session.py·hub_project.py·hub_server_state.py·hub_parse.py(순수)의
결과를 조립해 ~/.claude/hub/hub.html 을 만든다.
"""

import dataclasses
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import hub_model
import hub_parse
import hub_project
import hub_server_state
import hub_session
import hub_usage

HUB_HOME = Path.home() / ".claude" / "hub"
EVENTS_DIR = HUB_HOME / "events"
HUB_HTML_PATH = HUB_HOME / "hub.html"
CONFIG_PATH = HUB_HOME / "config.json"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "hub_template.html"
# 배경 spawn(hub_hook.py)의 stdout/stderr 는 DEVNULL 이라 실패가 완전히 무성음이 된다 — 마지막
# collect 실패를 이 파일에 남겨 `/hub status` 가 읽을 수 있게 한다(검수 M7).
LAST_COLLECT_ERROR_PATH = HUB_HOME / "last_collect_error.json"
# 사용량 API 폴링(R1) 실패 기록 — last_collect_error.json 과 완전히 같은 모양이다(새 개념 0개,
# 결정 A5). schema_mismatch 일 때만 response_keys(키 구조, 값 없음)가 더 실린다.
LAST_USAGE_API_ERROR_PATH = HUB_HOME / "last_usage_api_error.json"
# 훅 버스트(같은 5초 안에 여러 세션이 동시에 훅을 쏘는 경우) 디바운스용 스탬프(검수 n3).
# hub.html 의 mtime 은 spawn 된 collect 가 끝나야 바뀌므로, 그 사이 도착하는 훅들은 여전히
# 오래된 mtime 을 보고 각자 spawn 을 결정해 버린다 — spawn 직전에 이 파일을 touch 하면
# 뒤따르는 훅들이 곧바로 "최근에 이미 처리했다"고 판단한다.
SPAWN_STAMP_PATH = HUB_HOME / ".collect_spawn_stamp"
# 상주 서버(개정 1 rev2) 상태 파일 3종. server.json 은 서버 자신이 bind 직후 1회,
# server_heartbeat 는 수집 루프가 매 사이클, server.log 는 stderr 리다이렉션 대상이다.
SERVER_RECORD_PATH = HUB_HOME / "server.json"
SERVER_HEARTBEAT_PATH = HUB_HOME / "server_heartbeat"
SERVER_LOG_PATH = HUB_HOME / "server.log"
# hub_statusline.py 가 statusLine stdin 에서 캡처한 한도 초기화 예정 시각 + 사용률 —
# 퍼센트의 유일한 출처다(결정 P1, docs/prps/hub-card-cleanup-and-usage-source.md).
RATE_LIMITS_PATH = HUB_HOME / "rate_limits.json"


class HubCollectError(Exception):
    """collect 파이프라인에서 예상된 실패(배포 자산 누락 등)를 나타낸다(검수 M7).

    session.json 파싱 실패(설계 결정 5)를 제외한 나머지는 원래 "실패 → 한 티어 낮은 표시"로
    흡수해야 하는데, 템플릿 파일처럼 흡수할 하위 티어가 없는 경우에 한해 이 예외로 사유를 분명히
    하고 호출자(hub.py)가 `{"ok": false, "reason": ...}` 계약으로 변환한다.
    """

PROJECT_MARKER_NAMES = (".claude", ".git")
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
DATE_FORMAT = "%Y-%m-%d"


# 필드별 기대 타입(검수 m5). bool 은 int 의 서브클래스라 int 기대 필드에 실수로 통과할 수 있지만,
# 그 정도 오탐은 사용자가 config.json 에 숫자를 불(bool)로 잘못 적는 실제 시나리오가 아니라
# 무시할 만하다 — 여기서 막는 것은 "roots" 에 문자열을 넣는 등 명백한 스키마 오류다.
_CONFIG_FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
    "roots": (list, tuple),
    "ignore_globs": (list, tuple),
    "scan_depth": int,
    "stale_after_minutes": int,
    "event_retention_days": int,
    "record_prompt_excerpt": bool,
    "server_port": int,
    "server_collect_interval_seconds": int,
    "show_usage_panel": bool,
    "usage_api_enabled": bool,
    "usage_api_poll_interval_seconds": int,
}


# 개정 1(rev2)에서 폐기된 키. 조용히 무시하면 마이그레이션은 필요 없지만, 사용자가 그
# 필드를 여전히 유효하다고 믿고 있을 수 있다 — 대체 필드를 안내한다(검수 m4).
_DEPRECATED_CONFIG_FIELD_GUIDANCE: dict[str, str] = {
    "serve_port_candidates": "'server_port' 로 대체됐습니다(상주 서버는 후보 순회 없이 고정 포트 하나만 씁니다)",
}


def _validate_config_overrides(raw: dict, defaults: hub_model.HubConfig) -> tuple[dict, tuple[str, ...]]:
    """raw 의 각 필드 타입을 검증해 (안전한 override, 경고 목록) 을 돌려준다.

    알 수 없는 키는 무시하되(존재해도 무해하다) 사유를 warnings 에 남긴다(검수 m4) — 조용히
    무시하면 오타나 폐기된 키(`serve_port_candidates` 등)를 사용자가 눈치챌 방법이 없다.
    """
    known_fields = {field.name for field in dataclasses.fields(defaults)}
    overrides: dict = {}
    warnings: list[str] = []
    for key, value in raw.items():
        if key not in known_fields:
            guidance = _DEPRECATED_CONFIG_FIELD_GUIDANCE.get(key, "무시합니다 — 오타인지 확인하십시오")
            warnings.append(f"config.json: 알 수 없는 필드 '{key}' — {guidance}")
            continue
        if not isinstance(value, _CONFIG_FIELD_TYPES[key]):
            warnings.append(f"config.json: '{key}' 타입이 맞지 않아 기본값을 씁니다")
            continue
        overrides[key] = tuple(value) if isinstance(value, list) else value
    return overrides, tuple(warnings)


def load_config() -> tuple[hub_model.HubConfig, tuple[str, ...]]:
    """~/.claude/hub/config.json 을 읽는다. 없거나 깨졌으면 기본값 전부.
    필드 타입이 안 맞으면 그 필드만 기본값으로 되돌리고 사유를 warnings 로 돌려준다(검수 m5)."""
    defaults = hub_model.HubConfig()
    if not CONFIG_PATH.exists():
        return defaults, ()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults, (f"{CONFIG_PATH}: JSON 파싱 실패 — 기본값을 씁니다",)
    if not isinstance(raw, dict):
        return defaults, (f"{CONFIG_PATH}: 최상위 값이 객체가 아니라 기본값을 씁니다",)
    overrides, warnings = _validate_config_overrides(raw, defaults)
    return dataclasses.replace(defaults, **overrides), warnings


# ---- 프로젝트 발견 (config.roots 스캔, 쟁점 4) ----
def _has_project_marker(directory: Path) -> bool:
    """.claude 또는 .git 존재 여부. `Path.exists` 는 ENOENT 만 흡수하고 EACCES 는 올린다
    (macOS 실측, 검수 M7) — 권한 없는 디렉토리를 훑다 collect 전체가 죽지 않도록 감싼다."""
    try:
        return any((directory / marker).exists() for marker in PROJECT_MARKER_NAMES)
    except OSError:
        return False


def _scan_directory(directory: Path, remaining_depth: int) -> list[str]:
    matches = []
    if _has_project_marker(directory):
        matches.append(str(directory))
    if remaining_depth <= 0:
        return matches
    try:
        children = [child for child in directory.iterdir() if child.is_dir()]
    except OSError:
        return matches
    for child in children:
        matches.extend(_scan_directory(child, remaining_depth - 1))
    return matches


def scan_roots_for_projects(roots: tuple[str, ...], scan_depth: int) -> list[str]:
    """config.roots 를 scan_depth 까지 훑어 .claude 또는 .git 을 가진 디렉토리를 찾는다."""
    found = []
    for root in roots:
        root_path = Path(root).expanduser()
        if root_path.is_dir():
            found.extend(_scan_directory(root_path, scan_depth))
    return found


# ---- 티어 2: 이벤트 로그 ----
def _date_string(epoch_ms: int) -> str:
    return time.strftime(DATE_FORMAT, time.localtime(epoch_ms / 1000))


def _recent_event_file_paths(now_ms: int) -> list[Path]:
    dates = [_date_string(now_ms), _date_string(now_ms - MILLISECONDS_PER_DAY)]
    unique_dates = list(dict.fromkeys(dates))
    return [EVENTS_DIR / f"{date}.jsonl" for date in unique_dates]


def read_recent_events(now_ms: int) -> tuple[list[hub_session.HookEvent], tuple[str, ...]]:
    """오늘 + 어제 이벤트 파일을 읽어 파싱된 이벤트를 시간순으로 돌려준다.

    파일 하나를 못 읽어도 나머지로 계속 진행한다(검수 M7, 리스크 6 "이벤트 손실은 1건 한정"과
    같은 원칙) — `errors="replace"` 로 깨진 바이트(동시 append 찢김 등)를 U+FFFD 로 바꿔
    디코딩 자체가 죽지 않게 하고, 그 결과로 JSON 이 안 맞는 줄만 parse_event_line 에서 탈락한다.
    파일 단위 읽기 실패(권한 등)는 그 파일만 건너뛰고 사유를 warnings 로 돌려준다.
    """
    events = []
    warnings: list[str] = []
    for file_path in _recent_event_file_paths(now_ms):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            warnings.append(f"{file_path}: 이벤트 파일 읽기 실패 ({error})")
            continue
        for line in text.splitlines():
            event = hub_session.parse_event_line(line)
            if event is not None:
                events.append(event)
    events.sort(key=lambda event: event.received_at_ms)
    return events, tuple(warnings)


def _group_sessions_by_project(
    events: list[hub_session.HookEvent], ignore_globs: tuple[str, ...]
) -> dict[str, tuple[hub_session.SessionFacts, ...]]:
    """이벤트를 세션 사실로 접고 cwd 별로 묶는다. 무시 패턴에 해당하는 cwd 는 제외한다."""
    grouped: dict[str, list[hub_session.SessionFacts]] = {}
    for facts in hub_session.build_session_facts(events).values():
        if hub_project.should_ignore_cwd(facts.cwd, ignore_globs):
            continue
        grouped.setdefault(facts.cwd, []).append(facts)
    return {path: tuple(sessions) for path, sessions in grouped.items()}


def prune_old_event_files(now_ms: int, retention_days: int) -> None:
    """retention_days 보다 오래된 이벤트 파일을 삭제한다. 살아 있는 파일은 절대 다시 쓰지 않는다.

    hub.html 이 없어도(허브 off 상태) 호출돼야 "최대 N일 보관" 고지가 성립한다 — 공개 함수로 두어
    hub_hook.py 가 append 직후 곧바로 호출한다(검수 M5).
    """
    if not EVENTS_DIR.is_dir():
        return
    cutoff_date = time.strftime(DATE_FORMAT, time.localtime((now_ms - retention_days * MILLISECONDS_PER_DAY) / 1000))
    for file_path in EVENTS_DIR.glob("*.jsonl"):
        match = re.match(r"(\d{4}-\d{2}-\d{2})\.jsonl$", file_path.name)
        if match and match[1] < cutoff_date:
            file_path.unlink(missing_ok=True)


# ---- 티어 1: /dashboard DOM ----
def read_tier1_snapshot(project_path: str) -> tuple[hub_parse.Tier1Snapshot | None, str | None]:
    """프로젝트의 .claude/dashboard.html 을 읽어 판다. (스냅샷, 경고 메시지) 튜플을 돌려준다."""
    dashboard_path = Path(project_path) / hub_project.PROJECT_DASHBOARD_RELATIVE_PATH
    if not dashboard_path.is_file():
        return None, None
    try:
        text = dashboard_path.read_text(encoding="utf-8")
        mtime_ms = int(dashboard_path.stat().st_mtime * 1000)
    except OSError as error:
        return None, f"{project_path}: dashboard.html 읽기 실패 ({error})"
    snapshot = hub_parse.parse_dashboard_html(text)
    if snapshot is None:
        return None, f"{project_path}: dashboard.html DOM 계약 불일치 — 티어 2로 강등"
    return dataclasses.replace(snapshot, file_mtime_ms=mtime_ms), None


# ---- 티어 3: ~/.claude/projects 의 mtime ----
def _encoded_ignore_globs(ignore_globs: tuple[str, ...]) -> tuple[str, ...]:
    """ignore_globs(실경로 패턴)를 encode_project_dir_name 과 같은 규칙으로 인코딩한다.

    `/`·`.` 만 `-` 로 바뀌므로 `*` 는 그대로 남아 fnmatch 패턴으로 계속 쓸 수 있다.
    """
    return tuple(hub_project.encode_project_dir_name(pattern) for pattern in ignore_globs)


def _tier3_activity_by_encoded_name(
    ignore_globs: tuple[str, ...]
) -> tuple[dict[str, int], tuple[str, ...]]:
    """~/.claude/projects/<인코딩>/*.jsonl (maxdepth 1) mtime 최댓값을 인코딩명별로 모은다.

    ignore_globs 를 인코딩한 패턴으로도 걸러 scratchpad·worktree 소음을 원천에서 제거한다
    (검수 m4) — 그러지 않으면 이 항목들이 매칭에 실패해 "미확인 프로젝트" 개수만 부풀린다.

    두 지점에 OSError 가드를 둔다(검수 R3-m1): `iterdir()` 실패(권한 없음 등)는 티어 3
    전체를 포기하고(티어 1·2 는 산다), entry 단위 stat 실패(glob 열거와 stat 사이의 TOCTOU)는
    그 프로젝트만 건너뛴다. 상주 서버에서는 수집 루프가 매 사이클 같은 예외를 다시 만나므로
    이 구멍을 열어 두면 위험이 더 크다.
    """
    if not PROJECTS_DIR.is_dir():
        return {}, ()
    encoded_ignore_globs = _encoded_ignore_globs(ignore_globs)
    try:
        entries = list(PROJECTS_DIR.iterdir())
    except OSError as error:
        return {}, (f"{PROJECTS_DIR}: 목록 조회 실패 — 티어 3 전체를 건너뜁니다 ({error})",)

    activity: dict[str, int] = {}
    warnings: list[str] = []
    for entry in entries:
        if not entry.is_dir() or hub_project.should_ignore_cwd(entry.name, encoded_ignore_globs):
            continue
        try:
            mtimes = [child.stat().st_mtime for child in entry.glob("*.jsonl")]
        except OSError as error:
            warnings.append(f"{entry}: mtime 조회 실패 — 이 프로젝트만 건너뜁니다 ({error})")
            continue
        if mtimes:
            activity[entry.name] = int(max(mtimes) * 1000)
    return activity, tuple(warnings)


# ---- 한도 초기화 예정 시각 + 사용률 (docs/prps/hub-usage-reset-time-and-refresh.md,
#      docs/prps/hub-card-cleanup-and-usage-source.md 결정 P1~P8) ----
def read_rate_limit_capture() -> tuple[hub_usage.RateLimitCapture | None, tuple[str, ...]]:
    """캡처 파일을 읽어 판다. 이 함수는 절대 예외를 던지지 않는다.

    반환 계약(PRP 「반환 계약」 표가 정본): 파일 부재는 statusLine 미설치·미실행의 정상
    상태라 경고를 내지 않는다. 읽기 실패·계약 불일치만 경고 1건을 남긴다. 퍼센트의 유일한
    출처가 됐으므로(결정 P1) `errors="replace"` 로 찢긴 멀티바이트 읽기를 흡수한다 — 그러지
    않으면 `UnicodeDecodeError`(ValueError 서브클래스)가 `except OSError` 를 뚫는다
    (read_latest_usage_sample 의 검수 M1 선례와 같은 문제, §17 발견 1).
    """
    if not RATE_LIMITS_PATH.is_file():
        return None, ()
    try:
        text = RATE_LIMITS_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return None, (f"{RATE_LIMITS_PATH}: 한도 초기화 시각 캡처 파일 읽기 실패 ({error})",)
    capture = hub_usage.parse_rate_limit_capture(text)
    if capture is None:
        return None, (f"{RATE_LIMITS_PATH}: 캡처 파일 계약 불일치 — 사용량 패널을 표시하지 않습니다",)
    return capture, ()


def write_rate_limit_capture(capture: hub_usage.RateLimitCapture) -> None:
    """캡처를 원자적으로 쓴다(hub_statusline.py 전용 쓰기 경로). _atomic_write_text 재사용."""
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dataclasses.asdict(capture), ensure_ascii=False)
    _atomic_write_text(RATE_LIMITS_PATH, HUB_HOME, "rate_limits.json.", payload)


def _capture_for_snapshot(
    now_ms: int, config: hub_model.HubConfig
) -> tuple[hub_usage.UsageSample | None, hub_usage.RateLimitResets | None, tuple[str, ...]]:
    """캡처를 **사이클당 1회만** 읽어 화면에 실을 사용률·리셋 시각을 고른다(사설, 결정 P3).

    `show_usage_panel` 이 꺼져 있으면 캡처 파일을 열지도 않는다(전제 8) — CSS 로 숨기는 게
    아니라 읽기 자체를 중단하는 것이 진짜 프라이버시 제어다. 사용률은 5시간 만료(U3) 또는
    세션 창 롤오버(결정 P5)여도 **숨기지 않는다** — `mark_stale_usage_sample` 이 `is_stale`
    로 표시만 하고 값은 그대로 살려 둔다(R-B, 결정 EX1·EX5) — 화면은 그 값을 "조회되지
    않음"으로 그린다. 지난 리셋 시각은 여기(서버 쪽 1차 필터, 결정 R5)에서 걷어낸다 —
    클라이언트 쪽 2차 필터는 템플릿이 30초 틱마다 담당한다. 두 사설 함수
    (_usage_for_snapshot·_rate_limit_resets_for_snapshot)가 각각 파일을 읽던 구조를 여기
    하나로 합쳐, 계약 불일치 경고가 2건으로 중복되는 문제(GOTCHA 5)를 없앤다.
    """
    if not config.show_usage_panel:
        return None, None, ()
    capture, warnings = read_rate_limit_capture()
    if capture is None:
        return None, None, warnings

    usage = hub_usage.usage_sample_from_capture(capture)
    if usage is not None:
        usage = hub_usage.mark_stale_usage_sample(usage, capture, now_ms)  # 숨기지 않고 표식만 단다(R-B)

    resets = hub_usage.resets_from_capture(capture)
    if resets is not None:
        resets = hub_usage.drop_passed_resets(resets, now_ms)

    return usage, resets, warnings


# ---- 합성 ----
def collect_snapshot(now_ms: int) -> hub_model.HubSnapshot:
    """3티어를 전부 읽어 하나의 HubSnapshot 으로 합성한다. 실패는 warnings 로 드러난다."""
    config, config_warnings = load_config()
    prune_old_event_files(now_ms, config.event_retention_days)

    events, event_read_warnings = read_recent_events(now_ms)
    sessions_by_path = _group_sessions_by_project(events, config.ignore_globs)
    scanned_paths = scan_roots_for_projects(config.roots, config.scan_depth)

    candidate_paths = {
        path
        for path in set(sessions_by_path) | set(scanned_paths)
        if not hub_project.should_ignore_cwd(path, config.ignore_globs)
    }

    tier1_by_path: dict[str, hub_parse.Tier1Snapshot] = {}
    warnings: list[str] = [*config_warnings, *event_read_warnings]
    for path in candidate_paths:
        snapshot, warning = read_tier1_snapshot(path)
        if snapshot is not None:
            tier1_by_path[path] = snapshot
        if warning is not None:
            warnings.append(warning)

    tier3_by_encoded_name, tier3_warnings = _tier3_activity_by_encoded_name(config.ignore_globs)
    warnings.extend(tier3_warnings)
    resolved, unresolved = hub_project.resolve_project_dirs(
        list(tier3_by_encoded_name), list(candidate_paths)
    )
    tier3_by_path = {resolved[name]: mtime for name, mtime in tier3_by_encoded_name.items() if name in resolved}

    stale_after_ms = config.stale_after_minutes * 60 * 1000
    projects = hub_project.compose_project_views(
        tier1_by_path, sessions_by_path, tier3_by_path, now_ms, stale_after_ms
    )
    usage, rate_limit_resets, capture_warnings = _capture_for_snapshot(now_ms, config)
    warnings.extend(capture_warnings)
    return hub_model.HubSnapshot(
        collected_at_ms=now_ms,
        projects=projects,
        unresolved_dir_names=unresolved,
        warnings=tuple(warnings),
        usage=usage,
        rate_limit_resets=rate_limit_resets,
    )


def _atomic_write_text(final_path: Path, directory: Path, prefix: str, text: str) -> None:
    """directory 안에 고유한 임시 파일을 만들어 text 를 쓰고 final_path 로 원자적으로 교체한다.

    고정된 임시 파일명을 여러 프로세스가 공유하면 동시 쓰기가 뒤섞인 파일을 발행할 수 있다
    (검수 M2) — `tempfile.mkstemp` 로 매 호출마다 고유한 이름을 받는다.
    """
    temp_fd, temp_name = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(text)
        temp_path.replace(final_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def write_hub_html(snapshot: hub_model.HubSnapshot) -> None:
    """hub.html 을 프로세스마다 고유한 임시 파일에 쓴 뒤 원자적으로 교체한다.

    템플릿을 못 읽으면(배포 누락 등) 원시 OSError 대신 사유가 분명한 HubCollectError 를 던진다
    (검수 M7) — 호출자(hub.py)가 이를 잡아 `{"ok": false, "reason": ...}` 계약으로 변환한다.
    """
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise HubCollectError(f"{TEMPLATE_PATH}: 템플릿 읽기 실패 ({error})") from error
    rendered = hub_model.render_hub_html(template, snapshot)
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(HUB_HTML_PATH, HUB_HOME, "hub.html.", rendered)


def touch_spawn_stamp() -> None:
    """collect 재수집을 spawn 하기 직전에 찍는 디바운스 스탬프(검수 n3).

    hub.html 의 mtime 은 spawn 된 자식이 다 끝나야 갱신되므로, 그 사이 도착하는 훅들이 전부
    같은 오래된 mtime 을 보고 각자 spawn 을 결정해 버린다 — 결정 시점을 이 파일로 옮긴다.
    """
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    SPAWN_STAMP_PATH.touch(exist_ok=True)


def record_collect_failure(reason: str) -> None:
    """마지막 collect 실패를 관측 가능한 위치에 남긴다. 이 함수 자신은 절대 예외를 던지지 않는다.

    배경 spawn(hub_hook.py)은 stdout/stderr 가 DEVNULL 이라 실패가 완전히 무성음이 된다 —
    `/hub status` 가 이 파일을 읽어 사용자에게 보여줄 수 있게 한다(검수 M7).

    기록 자체가 실패해도(검수 M2) 예외를 올리지 않고 stderr(상주 서버라면 server.log 로
    리다이렉션된다)로만 남긴다 — 1차 실패의 가장 흔한 원인이 HUB_HOME 쓰기 불가라, 이 함수가
    그대로 예외를 던지면 "실패를 기록하려다 또 실패하는" 상관 실패가 호출자의 예외 처리
    범위를 뚫고 나가 상주 서버의 수집 스레드 전체를 죽인다.
    """
    try:
        HUB_HOME.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"at_ms": int(time.time() * 1000), "reason": reason}, ensure_ascii=False)
        _atomic_write_text(LAST_COLLECT_ERROR_PATH, HUB_HOME, "last_collect_error.json.", payload)
    except OSError as error:
        print(f"collect 실패 기록 자체가 실패했습니다: {reason} (기록 실패 사유: {error})", file=sys.stderr)


def clear_collect_failure() -> None:
    """collect 가 성공하면 이전 실패 기록을 지운다."""
    LAST_COLLECT_ERROR_PATH.unlink(missing_ok=True)


def read_last_collect_failure() -> dict | None:
    """마지막으로 기록된 collect 실패(있으면)를 읽는다. 없거나 깨졌으면 None."""
    if not LAST_COLLECT_ERROR_PATH.exists():
        return None
    try:
        return json.loads(LAST_COLLECT_ERROR_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---- 사용량 API 폴링 실패 기록 (R1) — record_collect_failure 와 완전히 같은 형태(결정 A5) ----
def record_usage_api_failure(reason: str, response_keys: list[str] | None = None) -> None:
    """사용량 API 실패를 기록한다. 이 함수 자신은 절대 예외를 던지지 않는다
    (`record_collect_failure` 와 완전히 같은 형태·같은 이유 — 기록 자체의 실패가 호출자의
    예외 처리 범위를 뚫고 나가면 안 된다).

    `response_keys` 는 `reason="schema_mismatch"` 일 때만 채운다(SP3 생략 개정의 자기 진단
    창구) — 키 경로 + 타입 목록뿐이며 값은 절대 담지 않는다(불변식 A-SEC).
    """
    try:
        HUB_HOME.mkdir(parents=True, exist_ok=True)
        payload: dict = {"at_ms": int(time.time() * 1000), "reason": reason}
        if response_keys is not None:
            payload["response_keys"] = response_keys
        _atomic_write_text(
            LAST_USAGE_API_ERROR_PATH,
            HUB_HOME,
            "last_usage_api_error.json.",
            json.dumps(payload, ensure_ascii=False),
        )
    except OSError as error:
        print(f"사용량 API 실패 기록 자체가 실패했습니다: {reason} (기록 실패 사유: {error})", file=sys.stderr)


def clear_usage_api_failure() -> None:
    """사용량 API 폴링이 성공하면 이전 실패 기록을 지운다."""
    LAST_USAGE_API_ERROR_PATH.unlink(missing_ok=True)


def read_last_usage_api_failure() -> dict | None:
    """마지막으로 기록된 사용량 API 실패(있으면)를 읽는다. 없거나 깨졌으면 None."""
    if not LAST_USAGE_API_ERROR_PATH.exists():
        return None
    try:
        return json.loads(LAST_USAGE_API_ERROR_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---- 상주 서버 상태 (개정 1 rev2) ----
def touch_server_heartbeat() -> None:
    """상주 서버의 수집 루프가 매 사이클 호출한다 — 생존 판정의 정본(TTL 안이면 살아 있다)."""
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    SERVER_HEARTBEAT_PATH.touch(exist_ok=True)


def read_server_heartbeat_mtime_ms() -> int | None:
    """하트비트 파일의 mtime(ms). 없으면 None."""
    try:
        return int(SERVER_HEARTBEAT_PATH.stat().st_mtime * 1000)
    except OSError:
        return None


def write_server_record(record: hub_server_state.ServerRecord) -> None:
    """server.json 을 원자적으로 쓴다. 서버 자신이 bind 성공 직후 1회만 호출한다."""
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dataclasses.asdict(record), ensure_ascii=False)
    _atomic_write_text(SERVER_RECORD_PATH, HUB_HOME, "server.json.", payload)


def read_server_record() -> hub_server_state.ServerRecord | None:
    """server.json 을 읽어 판다. 없거나 깨졌으면 None.

    파싱은 hub_server_state.parse_server_record(순수)에 위임한다(검수 m3) — 예전에는 순환
    임포트를 피하려고 이 함수 안에 같은 로직을 따로 두었는데, 그 결과 실제 운영 경로(이 함수)가
    테스트 대상(hub_daemon 의 사본)과 다른 코드를 쓰는 위험이 있었다. hub_server_state.py 는
    다른 허브 모듈을 임포트하지 않는 잎 모듈이라 순환이 구조적으로 불가능하다.
    """
    try:
        text = SERVER_RECORD_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    return hub_server_state.parse_server_record(text)


def clear_server_state(expected_pid: int | None = None) -> None:
    """server.json + 하트비트를 제거한다. SIGTERM 정리와 stale 정리 양쪽에서 쓴다.

    `expected_pid` 가 주어지면 **compare-and-delete** 로 동작한다(검수 m1) — 삭제 직전에
    server.json 을 다시 읽어 그 pid 가 여전히 `expected_pid` 와 같을 때만 지운다. 무조건
    삭제하면, 이 함수를 부르기로 판단한 시점과 실제 삭제 시점 사이에 다른 프로세스(다른
    셸의 `server-start` 등)가 새 서버를 띄워 server.json 을 갈아 끼웠을 경우 방금 뜬 새
    서버의 기록을 지워 CLI 로는 더 이상 찾지도 끌 수도 없는 고아로 만든다(실측).
    `expected_pid` 를 생략하면(기본값 `None`) 무조건 삭제한다 — 다만 실사용 호출부는 SIGTERM
    핸들러를 포함해 전부 자신의 pid 를 `expected_pid` 로 넘긴다(검수 Nit). 이 무조건 삭제
    경로는 지금은 어떤 실행 경로도 밟지 않는 방어적 기본값이고, 최소 동작 확인은 테스트에서만
    한다.
    """
    if expected_pid is not None:
        current_record = read_server_record()
        if current_record is not None and current_record.pid != expected_pid:
            return
    SERVER_RECORD_PATH.unlink(missing_ok=True)
    SERVER_HEARTBEAT_PATH.unlink(missing_ok=True)
