"""hub_server.py — 상주 서버 본체. `server-run` 의 진입점.

메인 스레드는 허용 경로 화이트리스트만 서빙하는 HTTP 서버, 데몬 스레드는 주기 수집 루프를 돈다.
이 모듈은 I/O 다(HTTP 소켓·파일·시그널) — 순수 로직은 hub_model.py 의 관련 함수들에 있다.
개정 쟁점 R1·R3(docs/prps/hub-dashboard.md) 참조.
"""

import http.server
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path

import hub_collect
import hub_model
import hub_usage
import hub_usage_fetch

BIND_ADDRESS = "127.0.0.1"
# 이 둘만 200 이다. 나머지는 전부 404 — 디렉토리를 통째로 서빙하지 않으므로 노출 표면이
# "이 화이트리스트에 없으면 절대 나가지 않는다"로 고정된다(경로 traversal 여지가 없다).
ALLOWED_REQUEST_PATHS = ("/", "/hub.html")
# 요청 문자열에서 뽑는 것은 정규식이 확정한 16자리 hex 뿐이다 — 이 문자열은 절대 경로 조립에
# 쓰이지 않고 오직 dashboard_paths_by_key 딕셔너리의 조회 키로만 쓰인다(결정 N3).
PROJECT_DASHBOARD_PATH_PATTERN = re.compile(r"^/project/([0-9a-f]{16})/dashboard\.html\Z")
SERVER_LOG_MAX_BYTES = 256 * 1024
CACHE_CONTROL_NO_STORE = "no-store"


def _truncate_log_if_oversized(log_path, max_bytes: int) -> None:
    """server.log 가 max_bytes 를 넘으면 시작 시 잘라낸다(사후 원인 규명 창구가 무한히 크지 않게)."""
    try:
        if log_path.stat().st_size <= max_bytes:
            return
        tail_bytes = log_path.read_bytes()[-max_bytes:]
        log_path.write_bytes(tail_bytes)
    except OSError:
        pass


class _HubRequestHandler(http.server.BaseHTTPRequestHandler):
    """허용 경로 2개는 hub.html 을, 프로젝트 대시보드 경로는 레지스트리 조회로 서빙한다.
    그 외는 전부 404(결정 N3 — 요청 문자열로 경로를 조립하지 않는다)."""

    def do_GET(self) -> None:
        if self.path in ALLOWED_REQUEST_PATHS:
            self._serve_hub_html()
            return
        dashboard_match = PROJECT_DASHBOARD_PATH_PATTERN.match(self.path)
        if dashboard_match:
            self._serve_project_dashboard(dashboard_match.group(1))
            return
        self.send_error(404)

    def _serve_hub_html(self) -> None:
        try:
            body = hub_collect.HUB_HTML_PATH.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self._respond_with_html(body)

    def _serve_project_dashboard(self, dashboard_key: str) -> None:
        """`dashboard_key` 는 정규식이 이미 `[0-9a-f]{16}` 로 검증했다 — 딕셔너리 조회 결과만
        신뢰하고, 조회 실패(모르는 키)와 파일 부재(수집 이후 삭제된 TOCTOU)를 모두 404 로 접는다."""
        registry: dict[str, str] = getattr(self.server, "dashboard_paths_by_key", {})
        target_path = registry.get(dashboard_key)
        if target_path is None:
            self.send_error(404)
            return
        try:
            body = Path(target_path).read_bytes()
        except OSError:
            self.send_error(404)
            return
        # 대시보드는 이 프로세스가 만든 파일이 아니라 디스크 위의 파일이다 — 내용이 무엇이든
        # text/html 로만 해석되게 못 박는다(hub.html 응답에는 없는 방어선, 결정 N3).
        self._respond_with_html(body, extra_headers={"X-Content-Type-Options": "nosniff"})

    def _respond_with_html(self, body: bytes, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", CACHE_CONTROL_NO_STORE)
        for header_name, header_value in (extra_headers or {}).items():
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args) -> None:
        """5초 폴링이 상시로 들어와 server.log 를 부풀리므로 무음으로 오버라이드한다."""


def _run_collect_cycle(
    last_content_key: str | None,
) -> tuple[str | None, dict[str, str] | None]:
    """한 사이클: 수집 → (내용이 바뀌었거나 hub.html 이 없으면) 쓰기 → 실패 기록/해제.

    설계 결정 5(실패 격리)의 서버판이다 — 한 사이클의 예외가 상주 프로세스를 죽이면
    "사용자가 끄기 전까지 산다"(요구 R-1)가 조용히 깨진다.

    쓰기 게이트에 `hub.html` 실재 여부를 반드시 함께 본다(검수 M1) — content_key 만 보면
    파일이 삭제·손상돼도 내용이 그대로인 한 영구히 재생성되지 않는 "조용한 비복구 실패"가 된다.
    쓰기 자체가 실패하면(`write_hub_html` 예외) 캐시를 `None` 으로 무효화해 다음 사이클이
    반드시 다시 시도하게 한다 — 실패한 채로 `last_content_key` 가 낡은 값으로 남으면, 다음
    사이클이 "내용 동일"로 오판해 쓰기를 건너뛰고 그 상태에서 `clear_collect_failure()` 까지
    불러 실패 증거를 지워 버린다.

    `clear_collect_failure()` 는 쓰기가 일어났을 때만이 아니라 **이 사이클이 예외 없이
    끝나면(쓰기를 건너뛰었어도) 항상** 호출한다(검수 n2) — 쓰기를 건너뛰는 경우는 내용이
    같고 hub.html 도 실재할 때뿐이라 이미 "정상"이 확인된 상태다. 예전에는 쓰기 발생 사이클
    에서만 지워, 안정 상태(내용 불변 + hub.html 실재)가 오래 지속되면 그전에 다른 경로
    (예: 전경 `cmd_collect`)가 남긴 실패 기록이 영구 잔존해 `/hub status` 가 허위 경보를 냈다.

    반환값은 `(content_key, dashboard_registry)` 튜플이다(개정 쟁점 R3). 성공하면 둘 다
    채워지고(내용이 안 바뀌어 쓰기를 건너뛰었어도 레지스트리는 매 사이클 새로 만든다 — 순수
    함수라 비용이 없다), 실패하면 둘 다 `None` 이다 — 호출자(`_collect_loop`)가 `None` 을
    "직전 레지스트리를 그대로 유지하라"는 신호로 읽는다.
    """
    now_ms = int(time.time() * 1000)
    try:
        snapshot = hub_collect.collect_snapshot(now_ms)
        content_key = hub_model.snapshot_content_key(snapshot)
        needs_write = content_key != last_content_key or not hub_collect.HUB_HTML_PATH.exists()
        if needs_write:
            hub_collect.write_hub_html(snapshot)
        hub_collect.clear_collect_failure()
        return content_key, hub_model.build_dashboard_registry(snapshot)
    except Exception as error:
        hub_collect.record_collect_failure(str(error))
        return None, None


def _apply_dashboard_registry(
    httpd: http.server.ThreadingHTTPServer, registry: dict[str, str] | None
) -> None:
    """레지스트리를 서버 인스턴스에 통째로 교체한다(결정 N3) — `None` 이면 손대지 않는다.

    수집 실패 사이클(`registry is None`)에도 직전 레지스트리를 유지해야 이미 열려 있는
    모달의 폴링이 죽지 않는다(U20).
    """
    if registry is not None:
        httpd.dashboard_paths_by_key = registry


def _write_usage_api_capture(capture: hub_usage.RateLimitCapture) -> None:
    """사용량 API 캡처를 statusLine 생산자와 같은 공존 규칙으로 쓴다(결정 A2) —
    `same_capture_values` 게이트를 거쳐야 두 생산자가 값이 같을 때 서로를 덮어쓰지 않는다.

    로컬 쓰기 실패는 여기서 흡수하고 기존 collect 실패 채널(`record_collect_failure`)에
    남긴다 — 사용량 API 백오프 스케줄(poll_state)은 원격 API 와의 상호작용 결과만 반영해야
    하므로, 로컬 디스크 문제를 그 스케줄에 섞지 않는다.
    """
    try:
        previous, _warnings = hub_collect.read_rate_limit_capture()
        if not hub_usage.same_capture_values(previous, capture):
            hub_collect.write_rate_limit_capture(capture)
    except OSError as error:
        hub_collect.record_collect_failure(str(error))


def _run_usage_api_poll_cycle(
    now_ms: int, poll_state: hub_model.UsageApiPollState, config: hub_model.HubConfig
) -> hub_model.UsageApiPollState:
    """사용량 API 폴링 게이트 1사이클(R1, 결정 A3).

    `show_usage_panel`·`usage_api_enabled` 이 **둘 다** 참일 때만 자격증명을 읽고 원격
    호출을 한다(GOTCHA 2) — 하나만 보면 "패널을 껐는데 계속 자격증명을 읽고 원격 호출을
    한다"는, 사용자가 가장 화낼 상황이 된다. 캡처가 오면 기존 공존 규칙으로 쓰고 실패
    기록을 지운다. 실패(`schema_mismatch` 포함)면 **기존 캡처 파일을 덮어쓰지 않고**
    (결정 A7) 사유·상세를 `last_usage_api_error.json` 에 남긴다.
    """
    if not (config.show_usage_panel and config.usage_api_enabled):
        return poll_state
    if not hub_model.should_attempt_usage_api_poll(now_ms, poll_state, config.usage_api_poll_interval_seconds):
        return poll_state

    capture, failure_reason, failure_detail = hub_usage_fetch.fetch_rate_limit_capture(now_ms)
    if capture is not None:
        _write_usage_api_capture(capture)
        hub_collect.clear_usage_api_failure()
    else:
        # fetch_rate_limit_capture 의 계약(캡처 또는 실패사유 중 정확히 하나)상 이 분기에서
        # failure_reason 은 항상 채워져 있다 — record_usage_api_failure(reason: str) 에
        # None 을 넘길 일은 없다.
        hub_collect.record_usage_api_failure(failure_reason, failure_detail)
    return hub_model.next_usage_api_poll_state(now_ms, poll_state, failure_reason)


def _collect_loop(
    config: hub_model.HubConfig,
    stop_event: threading.Event,
    httpd: http.server.ThreadingHTTPServer,
) -> None:
    """데몬 스레드 본체. 기동 즉시 1회 수집하고 이후 주기마다 반복한다.

    하트비트는 사이클 **시작 직후에도** 찍는다(검수 Nit1) — 수집이 오래 걸리는 동안 하트비트가
    갱신되지 않으면, 실제로는 일하고 있는 서버를 외부 관찰자가 "죽었다"고 오판할 수 있다.
    사이클이 끝난 뒤에도 다시 찍는다 — 하트비트의 뜻은 "서버가 살아 있다"이지 "수집이
    성공했다"가 아니다(개정 쟁점 R3).

    사이클 전체를 try/except 로 한 번 더 감싼다(검수 M2-1, 최종 방어선) — `_run_collect_cycle`
    이 스스로 예외를 흡수하지만, `record_collect_failure` 가 실패를 기록하려다 자기 자신도
    예외를 던지는 상관 실패(1차 실패의 흔한 원인인 HUB_HOME 쓰기 불가는 이 함수가 쓰는 파일
    쓰기에도 똑같이 영향을 준다)나 `touch_server_heartbeat` 자체의 실패처럼 `_run_collect_cycle`
    바깥에서 나는 예외까지 있다. 이 한 곳이 예외로 빠져나가면 데몬 스레드가 죽고, "사용자가
    끄기 전까지 산다"(요구 R-1)가 조용히 깨진다. 여기서 잡은 예외는 다시 실패할 수 있는
    I/O(record_collect_failure 등)를 부르지 않고 stderr 에만 남긴다 — 이 print 자체가 마지막
    방어선이라 더 실패할 여지를 만들지 않는 것이 핵심이다.

    `httpd` 는 대시보드 레지스트리를 실어 둘 곳이다(결정 N3) — 호출부(단위 테스트 포함)가
    매번 명시적으로 넘긴다("테스트 편의용 선택 인자"는 그 자체로 추측성 유연성이라 두지
    않는다). `usage_api_poll_state` 도 이 함수의 **지역 변수**다(결정 A3 — 전역 가변 상태
    금지) — 사용량 API 폴링은 5초 수집 주기와 별도 스케줄(기본 5분)로 이 루프에 얹힌 게이트다.
    """
    last_content_key = None
    usage_api_poll_state = hub_model.UsageApiPollState()
    while not stop_event.is_set():
        try:
            hub_collect.touch_server_heartbeat()
            last_content_key, registry = _run_collect_cycle(last_content_key)
            _apply_dashboard_registry(httpd, registry)
            # collect_snapshot(위)이 느릴 수 있어, 폴링 게이트 판정 직전에 now_ms 를 다시
            # 잰다(검수 m2) — should_attempt_usage_api_poll 의 주기 판정이 그 지연만큼
            # 밀리지 않게 한다.
            usage_api_poll_state = _run_usage_api_poll_cycle(
                int(time.time() * 1000), usage_api_poll_state, config
            )
            hub_collect.touch_server_heartbeat()
        except Exception as error:
            print(f"수집 루프 사이클에서 처리되지 않은 예외: {error}", file=sys.stderr)
        stop_event.wait(config.server_collect_interval_seconds)


def run_server(config: hub_model.HubConfig) -> int:
    """HTTP 서버(메인) + 수집 루프(데몬 스레드)를 띄우고 블로킹한다.

    bind 성공 직후 server.json 을 쓰고, SIGTERM 을 받으면 상태 파일을 정리하고 종료한다.
    """
    _truncate_log_if_oversized(hub_collect.SERVER_LOG_PATH, SERVER_LOG_MAX_BYTES)

    try:
        httpd = http.server.ThreadingHTTPServer((BIND_ADDRESS, config.server_port), _HubRequestHandler)
    except OSError as error:
        print(f"포트 {config.server_port} bind 실패: {error}", file=sys.stderr)
        return 1
    httpd.dashboard_paths_by_key = {}    # 첫 수집 사이클 전까지는 프로젝트 대시보드가 전부 404

    try:
        hub_collect.write_server_record(
            hub_model.ServerRecord(pid=os.getpid(), port=config.server_port, started_at_ms=int(time.time() * 1000))
        )
    except OSError as error:
        # server.json 이 없으면 hub_daemon 이 이 프로세스를 영원히 찾을 수 없다(검수 Nit4) —
        # 기록 없는 고아 서버로 계속 도는 것보다, 사유를 남기고 즉시 종료하는 편이 안전하다.
        print(f"server.json 쓰기 실패 — 기록 없는 고아 서버를 막기 위해 종료합니다: {error}", file=sys.stderr)
        httpd.server_close()
        return 1

    stop_event = threading.Event()
    own_pid = os.getpid()

    def _handle_sigterm(_signum, _frame) -> None:
        stop_event.set()
        hub_collect.clear_server_state(expected_pid=own_pid)
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_sigterm)

    collect_thread = threading.Thread(target=_collect_loop, args=(config, stop_event, httpd), daemon=True)
    collect_thread.start()

    httpd.serve_forever()
    return 0
