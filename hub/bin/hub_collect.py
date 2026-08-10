"""hub_collect.py — I/O 레이어. 프로젝트 발견 · 3티어 읽기 · 스냅샷 조립 · hub.html 원자적 쓰기.

hub/bin 안에서 파일시스템·프로세스·네트워크에 닿는 유일한 모듈이다.
hub_model.py·hub_parse.py(순수)의 결과를 조립해 ~/.claude/hub/hub.html 을 만든다.
"""

import dataclasses
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import hub_model
import hub_parse

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
# 훅 버스트(같은 5초 안에 여러 세션이 동시에 훅을 쏘는 경우) 디바운스용 스탬프(검수 n3).
# hub.html 의 mtime 은 spawn 된 collect 가 끝나야 바뀌므로, 그 사이 도착하는 훅들은 여전히
# 오래된 mtime 을 보고 각자 spawn 을 결정해 버린다 — spawn 직전에 이 파일을 touch 하면
# 뒤따르는 훅들이 곧바로 "최근에 이미 처리했다"고 판단한다.
SPAWN_STAMP_PATH = HUB_HOME / ".collect_spawn_stamp"


class HubCollectError(Exception):
    """collect 파이프라인에서 예상된 실패(배포 자산 누락 등)를 나타낸다(검수 M7).

    session.json 파싱 실패(설계 결정 5)를 제외한 나머지는 원래 "실패 → 한 티어 낮은 표시"로
    흡수해야 하는데, 템플릿 파일처럼 흡수할 하위 티어가 없는 경우에 한해 이 예외로 사유를 분명히
    하고 호출자(hub.py)가 `{"ok": false, "reason": ...}` 계약으로 변환한다.
    """

DASHBOARD_RELATIVE_PATH = ".claude/dashboard.html"
PROJECT_MARKER_NAMES = (".claude", ".git")
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
DATE_FORMAT = "%Y-%m-%d"
SERVE_BIND_ADDRESS = "127.0.0.1"
SERVER_STARTUP_WAIT_SECONDS = 0.3
VALID_PORT_RANGE = range(1024, 65536)


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
    "serve_port_candidates": (list, tuple),
}


def _validate_config_overrides(raw: dict, defaults: hub_model.HubConfig) -> tuple[dict, tuple[str, ...]]:
    """raw 의 각 필드 타입을 검증해 (안전한 override, 경고 목록) 을 돌려준다."""
    known_fields = {field.name for field in dataclasses.fields(defaults)}
    overrides: dict = {}
    warnings: list[str] = []
    for key, value in raw.items():
        if key not in known_fields:
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


def read_recent_events(now_ms: int) -> tuple[list[hub_model.HookEvent], tuple[str, ...]]:
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
            event = hub_model.parse_event_line(line)
            if event is not None:
                events.append(event)
    events.sort(key=lambda event: event.received_at_ms)
    return events, tuple(warnings)


def _group_sessions_by_project(
    events: list[hub_model.HookEvent], ignore_globs: tuple[str, ...]
) -> dict[str, tuple[hub_model.SessionFacts, ...]]:
    """이벤트를 세션 사실로 접고 cwd 별로 묶는다. 무시 패턴에 해당하는 cwd 는 제외한다."""
    grouped: dict[str, list[hub_model.SessionFacts]] = {}
    for facts in hub_model.build_session_facts(events).values():
        if hub_model.should_ignore_cwd(facts.cwd, ignore_globs):
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
    dashboard_path = Path(project_path) / DASHBOARD_RELATIVE_PATH
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
    return tuple(hub_model.encode_project_dir_name(pattern) for pattern in ignore_globs)


def _tier3_activity_by_encoded_name(ignore_globs: tuple[str, ...]) -> dict[str, int]:
    """~/.claude/projects/<인코딩>/*.jsonl (maxdepth 1) mtime 최댓값을 인코딩명별로 모은다.

    ignore_globs 를 인코딩한 패턴으로도 걸러 scratchpad·worktree 소음을 원천에서 제거한다
    (검수 m4) — 그러지 않으면 이 항목들이 매칭에 실패해 "미확인 프로젝트" 개수만 부풀린다.
    """
    if not PROJECTS_DIR.is_dir():
        return {}
    encoded_ignore_globs = _encoded_ignore_globs(ignore_globs)
    activity = {}
    for entry in PROJECTS_DIR.iterdir():
        if not entry.is_dir():
            continue
        if hub_model.should_ignore_cwd(entry.name, encoded_ignore_globs):
            continue
        mtimes = [child.stat().st_mtime for child in entry.glob("*.jsonl")]
        if mtimes:
            activity[entry.name] = int(max(mtimes) * 1000)
    return activity


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
        if not hub_model.should_ignore_cwd(path, config.ignore_globs)
    }

    tier1_by_path: dict[str, hub_parse.Tier1Snapshot] = {}
    warnings: list[str] = [*config_warnings, *event_read_warnings]
    for path in candidate_paths:
        snapshot, warning = read_tier1_snapshot(path)
        if snapshot is not None:
            tier1_by_path[path] = snapshot
        if warning is not None:
            warnings.append(warning)

    tier3_by_encoded_name = _tier3_activity_by_encoded_name(config.ignore_globs)
    resolved, unresolved = hub_model.resolve_project_dirs(
        list(tier3_by_encoded_name), list(candidate_paths)
    )
    tier3_by_path = {resolved[name]: mtime for name, mtime in tier3_by_encoded_name.items() if name in resolved}

    stale_after_ms = config.stale_after_minutes * 60 * 1000
    projects = hub_model.compose_project_views(
        tier1_by_path, sessions_by_path, tier3_by_path, now_ms, stale_after_ms
    )
    return hub_model.HubSnapshot(
        collected_at_ms=now_ms,
        projects=projects,
        unresolved_dir_names=unresolved,
        warnings=tuple(warnings),
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
    """마지막 collect 실패를 관측 가능한 위치에 남긴다.

    배경 spawn(hub_hook.py)은 stdout/stderr 가 DEVNULL 이라 실패가 완전히 무성음이 된다 —
    `/hub status` 가 이 파일을 읽어 사용자에게 보여줄 수 있게 한다(검수 M7).
    """
    HUB_HOME.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"at_ms": int(time.time() * 1000), "reason": reason}, ensure_ascii=False)
    _atomic_write_text(LAST_COLLECT_ERROR_PATH, HUB_HOME, "last_collect_error.json.", payload)


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


# ---- 로컬 정적 서버 (상주 프로세스 없음 — 부르면 뜨고 끝나는 스크립트뿐) ----
def _is_valid_port(port: int) -> bool:
    return port in VALID_PORT_RANGE


def _serve_url(port: int) -> str:
    return f"http://localhost:{port}/hub.html"


_PORT_PROBE_TIMEOUT_SECONDS = 1


def _probe_port(port: int) -> str:
    """포트가 이 hub.html 을 이미 서빙 중이면 REUSE, 비어 있으면 FREE, 남의 서버면 OCCUPIED."""
    with socket.socket() as probe_socket:
        probe_socket.settimeout(_PORT_PROBE_TIMEOUT_SECONDS)
        if probe_socket.connect_ex((SERVE_BIND_ADDRESS, port)) != 0:
            return "FREE"
    try:
        served_bytes = urllib.request.urlopen(_serve_url(port), timeout=_PORT_PROBE_TIMEOUT_SECONDS).read()
    except OSError:
        return "OCCUPIED"
    return "REUSE" if served_bytes == HUB_HTML_PATH.read_bytes() else "OCCUPIED"


def _launch_server(port: int) -> dict:
    """`/dashboard serve` 3단계와 같은 패턴 — 임시 디렉토리에 심볼릭 링크 하나만 두고 서빙한다."""
    temp_dir = Path(tempfile.mkdtemp(prefix="dzh-hub-"))
    (temp_dir / "hub.html").symlink_to(HUB_HTML_PATH)
    command = [
        sys.executable, "-m", "http.server", str(port),
        "--bind", SERVE_BIND_ADDRESS, "--directory", str(temp_dir),
    ]
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(SERVER_STARTUP_WAIT_SECONDS)
    if _probe_port(port) != "REUSE":
        return {"ok": False, "reason": f"포트 {port} 기동 확인 실패(다른 프로세스가 선점했을 수 있음)"}
    return {"ok": True, "port": port, "started": True, "url": _serve_url(port)}


def start_serving(requested_port: int | None) -> dict:
    """hub.html 을 로컬 서버로 발행한다. 이미 서빙 중이면 재사용하고 새로 띄우지 않는다."""
    if not HUB_HTML_PATH.is_file():
        return {"ok": False, "reason": "hub.html 이 없습니다 — 먼저 hub.py open 을 실행하십시오"}
    if requested_port is not None and not _is_valid_port(requested_port):
        return {"ok": False, "reason": "포트는 1024~65535 범위여야 합니다"}
    config, _config_warnings = load_config()
    candidates = [requested_port] if requested_port else list(config.serve_port_candidates)
    for port in candidates:
        probe = _probe_port(port)
        if probe == "REUSE":
            return {"ok": True, "port": port, "started": False, "url": _serve_url(port)}
        if probe == "FREE":
            return _launch_server(port)
    return {"ok": False, "reason": "포트 후보가 전부 다른 서버에 쓰이고 있습니다"}


def stop_serving(requested_port: int | None) -> dict:
    """지정한 포트(없으면 후보 전부)에서 이 서버 패턴과 일치하는 http.server 를 종료한다."""
    config, _config_warnings = load_config()
    ports = [requested_port] if requested_port else list(config.serve_port_candidates)
    stopped = []
    for port in ports:
        if not _is_valid_port(port):
            continue
        pattern = f"http.server {port} --bind {SERVE_BIND_ADDRESS}"
        result = subprocess.run(["pkill", "-f", pattern], capture_output=True, check=False)
        if result.returncode == 0:
            stopped.append(port)
    return {"ok": True, "stopped_ports": stopped}
