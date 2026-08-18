"""hub_server.py 단위 테스트. 검수 M1 — 쓰기 게이트가 hub.html 실재를 함께 확인하는지,
쓰기 실패 시 캐시가 무효화되고 실패 기록이 지워지지 않는지 확인한다.
검수 M2 — 사이클 안의 어떤 예외도(기록 자체의 실패까지 포함) 수집 스레드를 죽이지 못하는지,
쓰기가 없어도 성공한 사이클이면 낡은 실패 기록을 지우는지 확인한다.
"""

import http.client
import http.server
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_model  # noqa: E402
import hub_project  # noqa: E402
import hub_server  # noqa: E402
import hub_usage  # noqa: E402
import hub_usage_fetch  # noqa: E402


def _minimal_snapshot(collected_at_ms: int = 1) -> hub_model.HubSnapshot:
    return hub_model.HubSnapshot(
        collected_at_ms=collected_at_ms, projects=(), unresolved_dir_names=(), warnings=()
    )


class _DummyHttpd:
    """`dashboard_paths_by_key` 속성만 있으면 되는 최소 더미(m1) — 실제 소켓을 bind 하는
    `ThreadingHTTPServer` 없이 `_collect_loop` 의 레지스트리 배선만 검증한다."""


class RunCollectCycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deleted_hub_html_is_regenerated_even_when_content_unchanged(self) -> None:
        """검수 M1(1) — hub.html 이 삭제/손상돼도 내용이 그대로면 다음 사이클에 재생성돼야 한다.
        content_key 만으로 쓰기를 게이트하면 이 경우 영구히 재생성되지 않는다."""
        snapshot = _minimal_snapshot()
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            last_key, _ = hub_server._run_collect_cycle(None)
        self.assertTrue(hub_collect.HUB_HTML_PATH.exists())

        hub_collect.HUB_HTML_PATH.unlink()  # 외부에서 삭제/손상된 상황을 흉내낸다
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            next_key, _ = hub_server._run_collect_cycle(last_key)  # 캐시 키 기준으로는 "내용 불변"

        self.assertEqual(last_key, next_key)
        self.assertTrue(hub_collect.HUB_HTML_PATH.exists(), "hub.html 이 재생성되지 않음")

    def test_write_failure_invalidates_cache_and_keeps_failure_recorded(self) -> None:
        """검수 M1(2) — 쓰기 실패 시 다음 사이클이 반드시 재시도하고, 그 사이 실패 기록이
        지워지지 않는다(옛 캐시 키가 남으면 다음 사이클이 쓰기를 건너뛰고 실패 증거까지
        clear_collect_failure() 로 지워 버리는 것이 원래 결함이었다)."""
        snapshot = _minimal_snapshot()
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot), \
             mock.patch.object(hub_collect, "write_hub_html", side_effect=OSError("disk full")):
            first_key, _ = hub_server._run_collect_cycle(None)

        self.assertIsNone(first_key)  # 캐시 무효화 — 다음 사이클이 무조건 다시 쓰기를 시도한다
        recorded = hub_collect.read_last_collect_failure()
        self.assertIsNotNone(recorded)
        self.assertIn("disk full", recorded["reason"])

        # 다음 사이클: 쓰기가 이번엔 성공한다.
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            second_key, _ = hub_server._run_collect_cycle(first_key)

        self.assertIsNotNone(second_key)
        self.assertTrue(hub_collect.HUB_HTML_PATH.exists())
        self.assertIsNone(hub_collect.read_last_collect_failure())  # 성공 후에만 실패 기록 해제

    def test_no_write_needed_still_clears_stale_failure_record(self) -> None:
        """검수 n2 — 쓰기가 필요 없는(내용 불변 + hub.html 실재) 사이클도 성공했다면 이전
        실패 기록을 지운다. 예전에는 clear_collect_failure() 가 쓰기 발생 사이클에서만 불려,
        안정 상태가 오래 지속되면 다른 경로(예: 전경 cmd_collect)가 남긴 낡은 실패 기록이
        `/hub status` 에 영구히 허위 경보로 남았다."""
        snapshot = _minimal_snapshot()
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            last_key, _ = hub_server._run_collect_cycle(None)

        hub_collect.record_collect_failure("다른 경로가 남긴 낡은 실패")
        self.assertIsNotNone(hub_collect.read_last_collect_failure())

        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            next_key, _ = hub_server._run_collect_cycle(last_key)  # 내용 불변 + hub.html 실재 → 쓰기 스킵

        self.assertEqual(last_key, next_key)
        self.assertIsNone(hub_collect.read_last_collect_failure())


class RunCollectCycleRegistryTest(unittest.TestCase):
    """U19~U20 — _run_collect_cycle 이 (content_key, registry) 튜플을 돌려주고,
    실패 사이클은 (None, None) 이라 호출자가 직전 레지스트리를 그대로 유지할 수 있다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_u19_successful_cycle_returns_content_key_and_registry(self) -> None:
        snapshot = _minimal_snapshot()
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            content_key, registry = hub_server._run_collect_cycle(None)
        self.assertIsNotNone(content_key)
        self.assertEqual(registry, {})

    def test_u20_failed_cycle_returns_none_none(self) -> None:
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=RuntimeError("collect 실패")):
            content_key, registry = hub_server._run_collect_cycle(None)
        self.assertIsNone(content_key)
        self.assertIsNone(registry)


class ProjectDashboardPathPatternTest(unittest.TestCase):
    """U14~U15 — 대시보드 경로 정규식이 정상 키만 매치하고 traversal·변형 시도는 전부 불매치."""

    def test_u14_valid_key_matches_and_captures_group(self) -> None:
        match = hub_server.PROJECT_DASHBOARD_PATH_PATTERN.match(
            "/project/3f9a1b2c3d4e5f60/dashboard.html"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "3f9a1b2c3d4e5f60")

    def test_u15_traversal_and_malformed_paths_do_not_match(self) -> None:
        malformed_paths = (
            "/project/../../etc/passwd",
            "/project/%2e%2e/dashboard.html",
            "/project/ABCDEF0123456789/dashboard.html",   # 대문자
            "/project/3f9a/dashboard.html",                # 짧음
            "/project/3f9a1b2c3d4e5f60/index.html",
        )
        for path in malformed_paths:
            with self.subTest(path=path):
                self.assertIsNone(hub_server.PROJECT_DASHBOARD_PATH_PATTERN.match(path))


class _RunningHubServerTestCase(unittest.TestCase):
    """실제 소켓에 bind 한 서버로 라우팅을 검증하기 위한 공통 준비(U16~U18)."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_html_path = hub_collect.HUB_HTML_PATH
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.HUB_HTML_PATH.write_text("<html>hub</html>", encoding="utf-8")

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), hub_server._HubRequestHandler)
        self.httpd.dashboard_paths_by_key = {}
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.server_thread.join(timeout=2)
        hub_collect.HUB_HTML_PATH = self.original_html_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get(self, path: str) -> http.client.HTTPResponse:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.httpd.server_address[1], timeout=5
        )
        connection.request("GET", path)
        response = connection.getresponse()
        response.read()
        connection.close()
        return response


class ProjectDashboardRoutingTest(_RunningHubServerTestCase):
    """U16~U18 — 레지스트리 조회 실패·TOCTOU·기존 화이트리스트 유지를 실제 서버로 확인한다."""

    def test_u16_well_formed_but_unregistered_key_is_404(self) -> None:
        self.assertEqual(self._get("/project/0000000000000000/dashboard.html").status, 404)

    def test_u17_registered_key_with_deleted_file_is_404(self) -> None:
        dashboard_path = self.temp_dir / "dashboard.html"
        dashboard_path.write_text("<html>dashboard</html>", encoding="utf-8")
        self.httpd.dashboard_paths_by_key = {"1111111111111111": str(dashboard_path)}
        dashboard_path.unlink()  # 수집 이후 삭제된 상황(TOCTOU)을 흉내낸다
        self.assertEqual(self._get("/project/1111111111111111/dashboard.html").status, 404)

    def test_u18_internal_files_stay_404_through_new_route(self) -> None:
        """S5 — 라우트가 하나 늘어도 bin/*.py·events/*.jsonl·config.json 은 어떤 경로로도 200 이 아니다."""
        blocked_paths = ("/bin/hub_server.py", "/events/x.jsonl", "/config.json")
        for blocked_path in blocked_paths:
            with self.subTest(path=blocked_path):
                self.assertEqual(self._get(blocked_path).status, 404)

    def test_registered_key_serves_dashboard_with_nosniff_header(self) -> None:
        dashboard_path = self.temp_dir / "dashboard.html"
        dashboard_path.write_text("<html>dashboard</html>", encoding="utf-8")
        self.httpd.dashboard_paths_by_key = {"2222222222222222": str(dashboard_path)}
        response = self._get("/project/2222222222222222/dashboard.html")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")


class CollectLoopDashboardRegistryWiringTest(unittest.TestCase):
    """m1 — `_collect_loop` 가 `httpd` 에 레지스트리를 실제로 배선하는지 확인한다.
    `httpd` 는 이제 필수 인자다(추측성 유연성인 기본값 `None` 을 없앴다) — 모든 호출부가
    명시적으로 넘긴다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_one_cycle(self, collect_snapshot_side_effect) -> _DummyHttpd:
        """stop_event 를 사이클 안에서(collect_snapshot 호출 시) 세워 정확히 한 바퀴만 돈다."""
        stop_event = threading.Event()
        httpd = _DummyHttpd()

        def fake_collect_snapshot(now_ms):
            stop_event.set()
            return collect_snapshot_side_effect(now_ms)

        config = hub_model.HubConfig(server_collect_interval_seconds=0)
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=fake_collect_snapshot), \
             mock.patch.object(hub_collect, "touch_server_heartbeat"):
            hub_server._collect_loop(config, stop_event, httpd)
        return httpd

    def test_successful_cycle_fills_dashboard_paths_by_key(self) -> None:
        tier1_project = hub_project.ProjectView(
            display_name="repo", path="/repo", tier=1, state="idle",
            last_activity_at_ms=1, sessions=(), tier1=None, note=None,
        )
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=1, projects=(tier1_project,), unresolved_dir_names=(), warnings=(),
        )
        httpd = self._run_one_cycle(lambda now_ms: snapshot)
        expected_key = hub_project.project_dashboard_key("/repo")
        self.assertIn(expected_key, httpd.dashboard_paths_by_key)

    def test_failed_cycle_keeps_previous_registry(self) -> None:
        stop_event = threading.Event()
        httpd = _DummyHttpd()
        httpd.dashboard_paths_by_key = {"deadbeefdeadbeef": "/old/.claude/dashboard.html"}

        def fake_collect_snapshot(now_ms):
            stop_event.set()
            raise RuntimeError("collect 실패")

        config = hub_model.HubConfig(server_collect_interval_seconds=0)
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=fake_collect_snapshot), \
             mock.patch.object(hub_collect, "touch_server_heartbeat"):
            hub_server._collect_loop(config, stop_event, httpd)

        self.assertEqual(httpd.dashboard_paths_by_key, {"deadbeefdeadbeef": "/old/.claude/dashboard.html"})


class CollectLoopResilienceTest(unittest.TestCase):
    """검수 M2-1 — 사이클 전체를 감싸는 try/except 가 최종 방어선인지 확인한다.

    `record_collect_failure` 자신은 예외를 던지지 않게 고쳤지만(검수 M2-2), 이 테스트는 그
    수정과 무관하게 `_collect_loop` 자체도 방어선을 가져야 한다는 요구를 직접 검증한다 — 여기
    서는 `record_collect_failure` 를 일부러 예외를 던지도록 흉내 내(상관 실패 재현) 그래도
    루프가 다음 사이클로 넘어가는지 본다.
    """

    def test_record_collect_failure_raising_does_not_kill_the_loop(self) -> None:
        stop_event = threading.Event()
        attempt_count = {"n": 0}

        def fake_record_collect_failure(reason: str) -> None:
            attempt_count["n"] += 1
            if attempt_count["n"] >= 2:
                stop_event.set()
            raise OSError("기록 자체가 실패했다고 흉내낸다")

        config = hub_model.HubConfig(server_collect_interval_seconds=0)
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=RuntimeError("collect 실패")), \
             mock.patch.object(hub_collect, "record_collect_failure", side_effect=fake_record_collect_failure), \
             mock.patch.object(hub_collect, "touch_server_heartbeat"):
            hub_server._collect_loop(config, stop_event, _DummyHttpd())  # 예외 없이 정상 반환해야 한다

        self.assertGreaterEqual(attempt_count["n"], 2)


class RunUsageApiPollCycleTest(unittest.TestCase):
    """GOTCHA 2 회귀 — show_usage_panel·usage_api_enabled 가 둘 다 참일 때만 자격증명을
    읽고 원격 호출을 한다. 캡처 성공/실패에 따른 파일 부수효과도 함께 확인한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        self.original_usage_api_error_path = hub_collect.LAST_USAGE_API_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"
        hub_collect.LAST_USAGE_API_ERROR_PATH = self.temp_dir / "last_usage_api_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        hub_collect.LAST_USAGE_API_ERROR_PATH = self.original_usage_api_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _capture(self, session_percent=23, weekly_percent=41) -> hub_usage.RateLimitCapture:
        return hub_usage.RateLimitCapture(
            captured_at_ms=1, session_resets_at_ms=None, weekly_resets_at_ms=None,
            session_used_percent=session_percent, weekly_used_percent=weekly_percent,
        )

    def test_disabled_switch_never_calls_fetch(self) -> None:
        config = hub_model.HubConfig(show_usage_panel=True, usage_api_enabled=False)
        with mock.patch.object(hub_usage_fetch, "fetch_rate_limit_capture") as mocked_fetch:
            result = hub_server._run_usage_api_poll_cycle(1_000, hub_usage.UsageApiPollState(), config)
        mocked_fetch.assert_not_called()
        self.assertEqual(result, hub_usage.UsageApiPollState())

    def test_usage_panel_off_blocks_fetch_even_if_api_enabled(self) -> None:
        """GOTCHA 2 의 핵심 — usage_api_enabled 만 보면 안 된다."""
        config = hub_model.HubConfig(show_usage_panel=False, usage_api_enabled=True)
        with mock.patch.object(hub_usage_fetch, "fetch_rate_limit_capture") as mocked_fetch:
            hub_server._run_usage_api_poll_cycle(1_000, hub_usage.UsageApiPollState(), config)
        mocked_fetch.assert_not_called()

    def test_successful_fetch_writes_capture_and_clears_failure(self) -> None:
        config = hub_model.HubConfig(show_usage_panel=True, usage_api_enabled=True)
        capture = self._capture()
        hub_collect.record_usage_api_failure("network_error")
        with mock.patch.object(hub_usage_fetch, "fetch_rate_limit_capture", return_value=(capture, None, None)):
            next_state = hub_server._run_usage_api_poll_cycle(1_000, hub_usage.UsageApiPollState(), config)
        written, _warnings = hub_collect.read_rate_limit_capture()
        self.assertEqual(written, capture)
        self.assertIsNone(hub_collect.read_last_usage_api_failure())
        self.assertEqual(next_state.consecutive_failures, 0)

    def test_failed_fetch_records_failure_and_does_not_touch_capture_file(self) -> None:
        config = hub_model.HubConfig(show_usage_panel=True, usage_api_enabled=True)
        with mock.patch.object(
            hub_usage_fetch, "fetch_rate_limit_capture", return_value=(None, "schema_mismatch", ["/x <str>"])
        ):
            next_state = hub_server._run_usage_api_poll_cycle(1_000, hub_usage.UsageApiPollState(), config)
        self.assertFalse(hub_collect.RATE_LIMITS_PATH.exists())
        recorded = hub_collect.read_last_usage_api_failure()
        self.assertEqual(recorded["reason"], "schema_mismatch")
        self.assertEqual(recorded["response_keys"], ["/x <str>"])
        self.assertEqual(next_state.consecutive_failures, 1)

    def test_not_yet_due_skips_fetch(self) -> None:
        config = hub_model.HubConfig(
            show_usage_panel=True, usage_api_enabled=True, usage_api_poll_interval_seconds=300
        )
        state = hub_usage.UsageApiPollState(last_attempt_at_ms=1_000, consecutive_failures=0)
        with mock.patch.object(hub_usage_fetch, "fetch_rate_limit_capture") as mocked_fetch:
            result = hub_server._run_usage_api_poll_cycle(1_000 + 1000, state, config)  # 1초 뒤 — 5분 미도달
        mocked_fetch.assert_not_called()
        self.assertEqual(result, state)


if __name__ == "__main__":
    unittest.main()
