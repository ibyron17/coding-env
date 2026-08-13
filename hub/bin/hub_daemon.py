"""hub_daemon.py — 프로세스 생명주기: 분리 spawn · ps 신원 확인 · SIGTERM/SIGKILL · 상태 보고.

`is_our_server_process`·`browser_open_command`·`restart_note` 만 ★순수하다
(tests/hub/test_hub_daemon.py 대상). `parse_server_record` 는 hub_model.py 에 있다(검수 m3 —
hub_collect.py 와 이중으로 유지하던 순수 파서를 하나로 합쳤다). 나머지(`start_server`/
`stop_server`/`server_status`/`open_browser`/`restart_server`)는 subprocess·시그널·시각에
닿는 I/O 다.

모듈 이름이 `hub_launchd.py` 가 아니라 `hub_daemon.py` 인 것은 개정 1(rev2)의 결과다 —
특정 OS 서비스 관리자(launchd 등)에 묶이지 않는다는 사실이 이름에 드러나야 한다
(docs/prps/hub-dashboard.md 개정 쟁점 R1).
"""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

import hub_collect
import hub_model

# "server-run" 이 있어야 한다 — 같은 hub.py 를 쓰는 배경 collect 프로세스(`hub.py collect`)를
# 서버로 오인하면 PID 재사용 방어의 의미가 없어진다.
SERVER_ENTRY_POINT_MARKER = "server-run"
HUB_PY_PATH = str(Path(__file__).resolve().parent / "hub.py")
BIND_ADDRESS = "127.0.0.1"
PORT_PROBE_TIMEOUT_SECONDS = 1
PS_TIMEOUT_SECONDS = 2
SERVER_START_WAIT_SECONDS = 5
SERVER_START_POLL_INTERVAL_SECONDS = 0.2
SERVER_STOP_WAIT_SECONDS = 5
SERVER_STOP_POLL_INTERVAL_SECONDS = 0.2
SERVER_LOG_TAIL_LINES = 20

# /usr/bin/open 은 -g 가 없으면 앱을 포그라운드로 올린다. 절대 경로를 쓰는 이유: PATH 에
# 같은 이름의 사용자 스크립트가 있으면 그것이 실행될 수 있다.
MACOS_OPEN_COMMAND_PATH = "/usr/bin/open"
MACOS_PLATFORM_NAME = "darwin"
BROWSER_OPEN_TIMEOUT_SECONDS = 5
FORCED_STOP_NOTE = "정상 종료 신호에 응답하지 않아 강제 종료했습니다"
SERVER_RESTART_PORT_WAIT_SECONDS = 3
SERVER_RESTART_PORT_POLL_INTERVAL_SECONDS = 0.1
ORPHANED_HEARTBEAT_REASON = (
    "정지 직후에도 서버가 살아 있다고 판정됐습니다 — 고아 하트비트일 수 있습니다"
    "(`/hub server status` 의 orphaned_evidence 를 확인하십시오)"
)


def is_our_server_process(ps_output: str, hub_py_path: str) -> bool:
    """`ps -p <pid> -o args=` 출력이 우리 hub.py server-run 인가.

    PID 재사용으로 남의 프로세스를 죽이지 않기 위한 유일한 안전장치다. 판정할 수 없으면
    (빈 출력 등) False 를 돌려준다 — "확인할 수 없으면 손대지 않는다"가 안전한 기본값이다.
    """
    if not ps_output or not hub_py_path:
        return False
    return hub_py_path in ps_output and SERVER_ENTRY_POINT_MARKER in ps_output


# parse_server_record 는 hub_model.py 로 옮겼다(검수 m3) — hub_collect.py 와 이중으로
# 유지하던 순수 파서를 하나로 합쳤다. 이 모듈은 (다른 모든 실사용 경로와 마찬가지로)
# hub_collect.read_server_record() 를 통해서만 이 값을 읽는다. 직접 호출이 필요하면
# hub_model.parse_server_record 를 쓴다.


def browser_open_command(platform_name: str, url: str) -> list[str] | None:
    """포커스까지 가져오며 URL 을 여는 외부 명령 argv. 지원 플랫폼이 아니면 None(webbrowser 폴백).

    `url` 은 argv 원소 하나로 그대로 넣는다 — 셸을 거치면 공백이 든 `file://` 경로가 두
    인자로 쪼개지고 셸 메타문자 주입 표면이 생긴다(GOTCHA 5). 리눅스·윈도우는 분기를 두지
    않는다 — `webbrowser` 가 이미 그 플랫폼에서 창을 올린다.
    """
    if platform_name == MACOS_PLATFORM_NAME:
        return [MACOS_OPEN_COMMAND_PATH, url]
    return None


def restart_note(stop_result: dict) -> str | None:
    """stop 단계의 이례(PID 재사용·이미 종료·강제 종료)를 사용자에게 알릴 한 줄로 바꾼다. 정상이면 None.

    `reason` 이 있으면 그 문구를 그대로 옮긴다 — 한국어 설명을 두 곳에서 관리하지 않기
    위해서다(그 문구는 stop_server 가 이미 만든다).
    """
    reason = stop_result.get("reason")
    if reason:
        return reason
    if stop_result.get("forced"):
        return FORCED_STOP_NOTE
    return None


# ---- I/O: 프로세스 조회·기동·종료 ----
def _now_ms() -> int:
    return int(time.time() * 1000)


def _is_port_occupied(port: int) -> bool:
    with socket.socket() as probe_socket:
        probe_socket.settimeout(PORT_PROBE_TIMEOUT_SECONDS)
        return probe_socket.connect_ex((BIND_ADDRESS, port)) == 0


def _ps_args_for_pid(pid: int) -> str | None:
    """`ps -p <pid> -o args=` 출력. 명령 실행 자체가 실패하면 None(판정 불가),
    프로세스가 없으면 빈 문자열, 있으면 그 명령행 문자열."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True, text=True, timeout=PS_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else ""


def _server_log_tail(max_lines: int = SERVER_LOG_TAIL_LINES) -> str:
    try:
        text = hub_collect.SERVER_LOG_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-max_lines:])


def _check_http_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/hub.html", timeout=PORT_PROBE_TIMEOUT_SECONDS) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def _spawn_server_process() -> None:
    """세션 무관 분리 프로세스로 `hub.py server-run` 을 띄운다(개정 쟁점 R1)."""
    hub_collect.HUB_HOME.mkdir(parents=True, exist_ok=True)
    with open(hub_collect.SERVER_LOG_PATH, "a", encoding="utf-8") as log_file:
        subprocess.Popen(
            [sys.executable, HUB_PY_PATH, "server-run"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=log_file,
            start_new_session=True,   # setsid(2) — 부모 세션·터미널과 무관하게 산다
            close_fds=True,
        )


def _server_already_running(ttl_ms: int) -> bool:
    if hub_model.is_server_alive(_now_ms(), hub_collect.read_server_heartbeat_mtime_ms(), ttl_ms):
        return True
    record = hub_collect.read_server_record()
    if record is None:
        return False
    return is_our_server_process(_ps_args_for_pid(record.pid) or "", HUB_PY_PATH)


def start_server() -> dict:
    """멱등 확인 → 포트 프로브 → 분리 spawn → 하트비트 대기."""
    config, _config_warnings = hub_collect.load_config()
    ttl_ms = hub_model.server_heartbeat_ttl_ms(config.server_collect_interval_seconds)

    if _server_already_running(ttl_ms):
        return {"ok": True, "already_running": True}
    if _is_port_occupied(config.server_port):
        return {"ok": False, "reason": f"포트 {config.server_port} 이 이미 사용 중입니다(다른 프로세스)"}

    _spawn_server_process()

    deadline = time.monotonic() + SERVER_START_WAIT_SECONDS
    while time.monotonic() < deadline:
        if hub_model.is_server_alive(_now_ms(), hub_collect.read_server_heartbeat_mtime_ms(), ttl_ms):
            record = hub_collect.read_server_record()
            return {
                "ok": True,
                "pid": record.pid if record else None,
                "url": f"http://localhost:{config.server_port}/hub.html",
            }
        time.sleep(SERVER_START_POLL_INTERVAL_SECONDS)
    return {"ok": False, "reason": "하트비트가 신선해지지 않았습니다", "log_tail": _server_log_tail()}


def stop_server() -> dict:
    """신원 확인 → SIGTERM → (필요 시) SIGKILL → 상태 파일 정리.

    모든 `clear_server_state` 호출에 `expected_pid=record.pid` 를 넘긴다(검수 m1,
    compare-and-delete) — 이 함수가 신원을 확인하고 kill 하기로 판단한 시점과 실제로 상태
    파일을 지우는 시점 사이에, 다른 프로세스가 이미 새 서버를 띄워 server.json 을 갈아
    끼웠을 수 있다. 그 경우 무조건 삭제하면 방금 뜬 새 서버의 기록을 지워 CLI 로 더 이상
    제어할 수 없는 고아로 만든다.
    """
    record = hub_collect.read_server_record()
    if record is None:
        return {"ok": True, "was_running": False}

    ps_args = _ps_args_for_pid(record.pid)
    if ps_args is None:
        return {"ok": False, "reason": "ps 실행 실패 — 확인할 수 없어 아무것도 하지 않았습니다"}
    if not ps_args:
        hub_collect.clear_server_state(expected_pid=record.pid)
        return {"ok": True, "was_running": False, "reason": "프로세스가 이미 종료돼 있어 상태 파일만 정리했습니다"}
    if not is_our_server_process(ps_args, HUB_PY_PATH):
        hub_collect.clear_server_state(expected_pid=record.pid)
        return {
            "ok": True, "was_running": False,
            "reason": "PID 가 재사용됐습니다 — 그 프로세스는 건드리지 않고 상태 파일만 정리했습니다",
        }

    try:
        os.kill(record.pid, signal.SIGTERM)
    except ProcessLookupError:
        hub_collect.clear_server_state(expected_pid=record.pid)
        return {"ok": True, "was_running": False}
    return _wait_for_process_exit(record.pid)


def _wait_for_process_exit(pid: int) -> dict:
    """SIGTERM 후 최대 SERVER_STOP_WAIT_SECONDS 동안 재확인하고, 안 죽으면 SIGKILL."""
    deadline = time.monotonic() + SERVER_STOP_WAIT_SECONDS
    while time.monotonic() < deadline:
        if not is_our_server_process(_ps_args_for_pid(pid) or "", HUB_PY_PATH):
            hub_collect.clear_server_state(expected_pid=pid)
            return {"ok": True, "was_running": True}
        time.sleep(SERVER_STOP_POLL_INTERVAL_SECONDS)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    hub_collect.clear_server_state(expected_pid=pid)
    return {"ok": True, "was_running": True, "forced": True}


def _wait_for_port_release(port: int) -> None:
    """포트가 풀릴 때까지 최대 SERVER_RESTART_PORT_WAIT_SECONDS 동안 폴링한다(D5).

    SIGKILL 직후 커널이 리스닝 소켓을 정리하기까지의 아주 짧은 창에 start 가 돌면 "다른
    프로세스가 점유 중"이라는 틀린 진단이 난다. 대기는 짧고 상한이 있어야 한다(GOTCHA 2) —
    초과해도 그냥 넘어간다. 그때는 정말 남의 프로세스이고 start 의 진단이 정확하다.
    """
    deadline = time.monotonic() + SERVER_RESTART_PORT_WAIT_SECONDS
    while time.monotonic() < deadline and _is_port_occupied(port):
        time.sleep(SERVER_RESTART_PORT_POLL_INTERVAL_SECONDS)


def restart_server() -> dict:
    """기존 서버를 확실히 내린 뒤 새로 띄운다(멱등 start 와 달리 항상 재기동한다).

    stop 이 실패하면 start 를 시도하지 않는다 — 낡은 서버가 살아 있을 수 있는 상태에서
    새로 띄우면 서버가 둘이 되려 시도하거나 포트 충돌로 엉뚱한 진단을 낸다(D4).
    stop_server()·start_server() 를 그대로 호출하며(D3), 그 사이에 포트 해제를 잠깐
    기다린다 — 두 함수의 안전장치(신원 확인·멱등)를 복제하지 않는다(GOTCHA 1).
    """
    stop_result = stop_server()
    if not stop_result.get("ok"):
        return {"ok": False, "phase": "stop", "reason": stop_result.get("reason")}

    config, _config_warnings = hub_collect.load_config()
    _wait_for_port_release(config.server_port)

    start_result = start_server()
    if start_result.get("already_running"):
        # stop 을 성공시킨 직후이므로 이 상태는 정상이 아니다 — 고아 하트비트일 가능성이
        # 크다(D6). 그 파일을 여기서 지우지 않는다(D7) — compare-and-delete 가 막으려던
        # 위험(다른 셸이 그 사이 띄운 새 서버의 기록을 지우는 것)을 재현하지 않기 위해서다.
        return {"ok": False, "phase": "start", "reason": ORPHANED_HEARTBEAT_REASON}
    if not start_result.get("ok"):
        result = {"ok": False, "phase": "start", "reason": start_result.get("reason")}
        if "log_tail" in start_result:
            result["log_tail"] = start_result["log_tail"]
        return result

    result = {
        "ok": True,
        "stopped_previous": stop_result.get("was_running", False),
        "pid": start_result.get("pid"),
        "url": start_result.get("url"),
    }
    note = restart_note(stop_result)
    if note is not None:
        result["note"] = note
    return result


def server_status() -> hub_model.ServerStatus:
    """프로세스 · 하트비트 · HTTP 응답 · 비정상 종료 흔적을 종합 판정한다."""
    config, _config_warnings = hub_collect.load_config()
    record = hub_collect.read_server_record()
    process_present = record is not None and is_our_server_process(
        _ps_args_for_pid(record.pid) or "", HUB_PY_PATH
    )
    heartbeat_mtime_ms = hub_collect.read_server_heartbeat_mtime_ms()
    ttl_ms = hub_model.server_heartbeat_ttl_ms(config.server_collect_interval_seconds)
    alive = hub_model.is_server_alive(_now_ms(), heartbeat_mtime_ms, ttl_ms)
    heartbeat_age_ms = (_now_ms() - heartbeat_mtime_ms) if heartbeat_mtime_ms is not None else None
    crashed_evidence = record is not None and not alive and not process_present
    # 프로세스(HTTP 서버 스레드)는 살아 있는데 하트비트만 만료됐다 — 수집 데몬 스레드만 죽은
    # 상태다(검수 M2). HTTP 는 계속 200 을 돌려줘 겉으론 정상처럼 보이지만, hub.html 은 그
    # 시점부터 영원히 갱신되지 않는다. crashed_evidence 는 "프로세스까지 죽었다"에 한정되므로
    # 이 상태는 이름이 따로 필요하다.
    collect_stalled = process_present and not alive
    # 하트비트는 살아 있는데 server.json 이 없다 — CLI 로는 PID 를 몰라 찾지도 끌 수도 없는
    # 고아 신호다(검수 m1). compare-and-delete 도입 전에는 잘못된 clear_server_state() 가
    # 이 상태를 만들 수 있었다; 지금은 예방됐지만, 과거에 이미 만들어졌거나 수동 조작으로
    # 생길 수 있는 상태이므로 관측 필드로 남겨 사용자가 직접 발견하게 한다.
    orphaned_evidence = record is None and alive
    return hub_model.ServerStatus(
        record=record,
        process_present=process_present,
        heartbeat_age_ms=heartbeat_age_ms,
        alive=alive,
        http_ok=_check_http_ok(config.server_port),
        crashed_evidence=crashed_evidence,
        # crashed_evidence(완전 사망)든 collect_stalled(수집 스레드만 사망)든, 원인 규명에는
        # 같은 server.log 꼬리가 쓰인다(검수 M2-3) — 둘 다 "무언가 죽었다"의 증거 창구다.
        log_tail=_server_log_tail() if (crashed_evidence or collect_stalled) else None,
        orphaned_evidence=orphaned_evidence,
        collect_stalled=collect_stalled,
    )


# ---- I/O: 브라우저 ----
def _fallback_to_webbrowser(url: str, fallback_reason: str | None) -> hub_model.BrowserOpenResult:
    """포커스 경로가 없거나 실패했을 때 webbrowser 로 연다. 예외는 밖으로 내지 않는다(GOTCHA 7).

    webbrowser.open() 이 던지는 예외도 fallback_reason 에 담는다 — 포커스 경로 실패 사유가
    이미 있으면 그것을 보존하고, 없을 때만(포커스 경로 자체가 없던 경우) 이 예외로 채운다.
    그러지 않으면 두 경로가 모두 실패했을 때 사유가 통째로 사라진다.
    """
    try:
        opened = bool(webbrowser.open(url))
    except Exception as error:
        opened = False
        if fallback_reason is None:
            fallback_reason = str(error)
    return hub_model.BrowserOpenResult(opened=opened, focus_requested=False, fallback_reason=fallback_reason)


def open_browser(url: str, platform_name: str = sys.platform) -> hub_model.BrowserOpenResult:
    """포커스 경로로 URL 을 열고, 안 되면 webbrowser 로 폴백한다. 예외를 밖으로 내보내지 않는다."""
    command = browser_open_command(platform_name, url)
    if command is None:
        return _fallback_to_webbrowser(url, fallback_reason=None)
    try:
        result = subprocess.run(
            command, capture_output=True, timeout=BROWSER_OPEN_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return _fallback_to_webbrowser(url, fallback_reason=str(error))
    if result.returncode == 0:
        return hub_model.BrowserOpenResult(opened=True, focus_requested=True, fallback_reason=None)
    return _fallback_to_webbrowser(
        url, fallback_reason=f"{MACOS_OPEN_COMMAND_PATH} 종료 코드 {result.returncode}"
    )
