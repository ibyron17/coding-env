"""hub_server.py — 상주 서버 본체. `server-run` 의 진입점.

메인 스레드는 허용 경로 화이트리스트만 서빙하는 HTTP 서버, 데몬 스레드는 주기 수집 루프를 돈다.
이 모듈은 I/O 다(HTTP 소켓·파일·시그널) — 순수 로직은 hub_model.py 의 관련 함수들에 있다.
개정 쟁점 R1·R3(docs/prps/hub-dashboard.md) 참조.
"""

import http.server
import os
import signal
import sys
import threading
import time

import hub_collect
import hub_model

BIND_ADDRESS = "127.0.0.1"
# 이 둘만 200 이다. 나머지는 전부 404 — 디렉토리를 통째로 서빙하지 않으므로 노출 표면이
# "이 화이트리스트에 없으면 절대 나가지 않는다"로 고정된다(경로 traversal 여지가 없다).
ALLOWED_REQUEST_PATHS = ("/", "/hub.html")
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
    """허용 경로 2개만 hub.html 을 200 으로 돌려준다. 그 외는 전부 404."""

    def do_GET(self) -> None:
        if self.path not in ALLOWED_REQUEST_PATHS:
            self.send_error(404)
            return
        try:
            body = hub_collect.HUB_HTML_PATH.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", CACHE_CONTROL_NO_STORE)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args) -> None:
        """5초 폴링이 상시로 들어와 server.log 를 부풀리므로 무음으로 오버라이드한다."""


def _run_collect_cycle(last_content_key: str | None) -> str | None:
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
    """
    now_ms = int(time.time() * 1000)
    try:
        snapshot = hub_collect.collect_snapshot(now_ms)
        content_key = hub_model.snapshot_content_key(snapshot)
        needs_write = content_key != last_content_key or not hub_collect.HUB_HTML_PATH.exists()
        if needs_write:
            hub_collect.write_hub_html(snapshot)
        hub_collect.clear_collect_failure()
        return content_key
    except Exception as error:
        hub_collect.record_collect_failure(str(error))
        return None


def _collect_loop(config: hub_model.HubConfig, stop_event: threading.Event) -> None:
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
    """
    last_content_key = None
    while not stop_event.is_set():
        try:
            hub_collect.touch_server_heartbeat()
            last_content_key = _run_collect_cycle(last_content_key)
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

    collect_thread = threading.Thread(target=_collect_loop, args=(config, stop_event), daemon=True)
    collect_thread.start()

    httpd.serve_forever()
    return 0
