"""hub_daemon 단위 테스트. 순수 함수(D1~D5)는 docs/prps/hub-dashboard.md 「개정 테스트 계획」 참조.

D6(parse_server_record)은 hub_model.py 로 옮겨 tests/hub/test_hub_model.py 에 있다(검수 m3).
I/O 함수(server_status·stop_server)는 검수 m1(고아 신호·compare-and-delete) 회귀 테스트 대상이다.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_daemon  # noqa: E402
import hub_model  # noqa: E402

HUB_PY_PATH = "/Users/x/.claude/hub/bin/hub.py"


class IsOurServerProcessTest(unittest.TestCase):
    """D1~D5 — PID 재사용 방어의 핵심 판정."""

    def test_d1_matching_server_run_process(self) -> None:
        ps_output = f"python3 {HUB_PY_PATH} server-run"
        self.assertTrue(hub_daemon.is_our_server_process(ps_output, HUB_PY_PATH))

    def test_d2_same_hub_py_but_collect_subcommand(self) -> None:
        """배경 collect 프로세스를 서버로 오인하지 않는다."""
        ps_output = f"python3 {HUB_PY_PATH} collect"
        self.assertFalse(hub_daemon.is_our_server_process(ps_output, HUB_PY_PATH))

    def test_d3_entirely_different_process(self) -> None:
        """PID 재사용 방어의 핵심 — 전혀 다른 프로세스는 False."""
        ps_output = "/usr/sbin/cupsd"
        self.assertFalse(hub_daemon.is_our_server_process(ps_output, HUB_PY_PATH))

    def test_d4_empty_output_is_unverifiable(self) -> None:
        """확인할 수 없으면(ps 실패 등의 빈 출력) 죽이지 않는다."""
        self.assertFalse(hub_daemon.is_our_server_process("", HUB_PY_PATH))
        self.assertFalse(hub_daemon.is_our_server_process("python3 x server-run", ""))

    def test_d5_home_directory_with_spaces(self) -> None:
        """부분 문자열 판정이 경로의 공백에 깨지지 않는다."""
        spaced_path = "/Users/x y/.claude/hub/bin/hub.py"
        ps_output = f"python3 {spaced_path} server-run"
        self.assertTrue(hub_daemon.is_our_server_process(ps_output, spaced_path))


class BrowserOpenCommandTest(unittest.TestCase):
    """D9 — 플랫폼 판정을 순수 함수로 떼어 세 플랫폼 전부를 단위 테스트로 덮는다."""

    def test_b1_darwin_uses_open_command_that_focuses(self) -> None:
        url = "http://localhost:8794/hub.html"
        self.assertEqual(
            hub_daemon.browser_open_command("darwin", url),
            ["/usr/bin/open", url],
        )

    def test_b2_linux_falls_back_to_webbrowser(self) -> None:
        url = "http://localhost:8794/hub.html"
        self.assertIsNone(hub_daemon.browser_open_command("linux", url))

    def test_b3_windows_falls_back_to_webbrowser(self) -> None:
        url = "http://localhost:8794/hub.html"
        self.assertIsNone(hub_daemon.browser_open_command("win32", url))

    def test_b4_url_stays_one_argv_element_even_with_spaces(self) -> None:
        """셸 인젝션 표면 부재의 회귀(GOTCHA 5) — 공백 있는 URL 도 argv 원소 하나로 그대로 간다."""
        url = "file:///Users/x y/.claude/hub/hub.html"
        command = hub_daemon.browser_open_command("darwin", url)
        self.assertEqual(len(command), 2)
        self.assertEqual(command[1], url)


class RestartNoteTest(unittest.TestCase):
    """restart_server 의 stop 단계 이례를 사용자 문구로 바꾸는 순수 함수."""

    def test_n1_clean_stop_has_no_note(self) -> None:
        self.assertIsNone(hub_daemon.restart_note({"ok": True, "was_running": True}))

    def test_n2_forced_kill_is_reported(self) -> None:
        stop_result = {"ok": True, "was_running": True, "forced": True}
        self.assertEqual(hub_daemon.restart_note(stop_result), hub_daemon.FORCED_STOP_NOTE)

    def test_n3_stop_reason_is_passed_through_verbatim(self) -> None:
        """문구를 두 곳에서 관리하지 않는다 — stop_server 가 만든 문구를 그대로 옮긴다."""
        reason = "PID 가 재사용됐습니다 — 그 프로세스는 건드리지 않고 상태 파일만 정리했습니다"
        stop_result = {"ok": True, "was_running": False, "reason": reason}
        self.assertEqual(hub_daemon.restart_note(stop_result), reason)


class HubDaemonIoScenarioTest(unittest.TestCase):
    """server_status/stop_server 의 I/O 시나리오. 실제 ~/.claude 는 건드리지 않는다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_record_path = hub_collect.SERVER_RECORD_PATH
        self.original_heartbeat_path = hub_collect.SERVER_HEARTBEAT_PATH
        self.original_config_path = hub_collect.CONFIG_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.SERVER_RECORD_PATH = self.temp_dir / "server.json"
        hub_collect.SERVER_HEARTBEAT_PATH = self.temp_dir / "server_heartbeat"
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.SERVER_RECORD_PATH = self.original_record_path
        hub_collect.SERVER_HEARTBEAT_PATH = self.original_heartbeat_path
        hub_collect.CONFIG_PATH = self.original_config_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class ServerStatusOrphanedEvidenceTest(HubDaemonIoScenarioTest):
    """검수 m1 — 하트비트는 살아 있는데 server.json 이 없는 상태를 이상 신호로 관측한다."""

    def test_fresh_heartbeat_without_record_is_orphaned(self) -> None:
        hub_collect.touch_server_heartbeat()
        with mock.patch.object(hub_daemon, "_check_http_ok", return_value=False):
            status = hub_daemon.server_status()
        self.assertTrue(status.orphaned_evidence)
        self.assertFalse(status.crashed_evidence)

    def test_no_heartbeat_no_record_is_not_orphaned(self) -> None:
        with mock.patch.object(hub_daemon, "_check_http_ok", return_value=False):
            status = hub_daemon.server_status()
        self.assertFalse(status.orphaned_evidence)


class ServerStatusCollectStalledTest(HubDaemonIoScenarioTest):
    """검수 M2-3/M2-4(2) — 프로세스(HTTP 서버 스레드)는 살아 있는데 수집 데몬 스레드만 죽어
    하트비트가 만료된 상태를 crashed_evidence 와 구분해 이름 붙인다."""

    def test_process_present_but_heartbeat_expired_is_collect_stalled(self) -> None:
        record = hub_model.ServerRecord(pid=999, port=8794, started_at_ms=1)
        hub_collect.write_server_record(record)
        ps_output_with_marker = f"python3 {hub_daemon.HUB_PY_PATH} server-run"
        with mock.patch.object(hub_daemon, "_ps_args_for_pid", return_value=ps_output_with_marker), \
             mock.patch.object(hub_daemon, "_check_http_ok", return_value=True):
            status = hub_daemon.server_status()
        self.assertTrue(status.process_present)
        self.assertFalse(status.alive)
        self.assertTrue(status.collect_stalled)
        self.assertFalse(status.crashed_evidence)  # 완전 사망이 아니라 수집 스레드만 사망
        self.assertIsNotNone(status.log_tail)

    def test_process_present_and_heartbeat_fresh_is_not_collect_stalled(self) -> None:
        record = hub_model.ServerRecord(pid=999, port=8794, started_at_ms=1)
        hub_collect.write_server_record(record)
        hub_collect.touch_server_heartbeat()
        ps_output_with_marker = f"python3 {hub_daemon.HUB_PY_PATH} server-run"
        with mock.patch.object(hub_daemon, "_ps_args_for_pid", return_value=ps_output_with_marker), \
             mock.patch.object(hub_daemon, "_check_http_ok", return_value=True):
            status = hub_daemon.server_status()
        self.assertFalse(status.collect_stalled)
        self.assertIsNone(status.log_tail)


class StopServerCompareAndDeleteTest(HubDaemonIoScenarioTest):
    """검수 m1 — stop 진행 중 다른 프로세스가 이미 새 서버를 등록했으면 그 기록을 지우지 않는다."""

    def test_stop_does_not_wipe_a_newer_server_registered_mid_race(self) -> None:
        old_record = hub_model.ServerRecord(pid=111, port=8794, started_at_ms=1)
        hub_collect.write_server_record(old_record)

        def fake_ps_args(pid: int) -> str:
            # "그 사이" 다른 셸이 새 서버를 등록했다고 흉내낸 뒤, 예전 프로세스는 이미
            # 종료된 것처럼 보이는 빈 출력을 돌려줘 정리 분기를 태운다.
            hub_collect.write_server_record(hub_model.ServerRecord(pid=222, port=8794, started_at_ms=2))
            return ""

        with mock.patch.object(hub_daemon, "_ps_args_for_pid", side_effect=fake_ps_args):
            result = hub_daemon.stop_server()

        self.assertTrue(result["ok"])
        surviving_record = hub_collect.read_server_record()
        self.assertIsNotNone(surviving_record)
        self.assertEqual(surviving_record.pid, 222)


class RestartServerSequenceTest(HubDaemonIoScenarioTest):
    """restart_server 의 조합 계약(D3~D7) — stop/start 를 그대로 호출하고, stop 실패 시 start 를
    시도하지 않으며, 고아 하트비트는 실패로 보고한다. `_wait_for_port_release` 는 실제 소켓을
    건드리지 않도록 패치한다(테스트가 8794 포트를 폴링할 이유가 없다)."""

    def setUp(self) -> None:
        super().setUp()
        self.wait_patcher = mock.patch.object(hub_daemon, "_wait_for_port_release")
        self.mock_wait = self.wait_patcher.start()

    def tearDown(self) -> None:
        self.wait_patcher.stop()
        super().tearDown()

    def test_s1_stop_failure_never_starts_a_new_server(self) -> None:
        stop_result = {"ok": False, "reason": "ps 실행 실패 — 확인할 수 없어 아무것도 하지 않았습니다"}
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result), \
             mock.patch.object(hub_daemon, "start_server") as mock_start:
            result = hub_daemon.restart_server()

        mock_start.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["phase"], "stop")
        self.assertEqual(result["reason"], stop_result["reason"])

    def test_s2_running_server_is_stopped_then_started(self) -> None:
        """PRP 테스트 계획 S2 — 호출 순서가 stop → 포트대기 → start 여야 한다(GOTCHA 2 완화 회귀 보호)."""
        stop_result = {"ok": True, "was_running": True}
        start_result = {"ok": True, "pid": 2, "url": "http://localhost:8794/hub.html"}
        call_order = mock.Mock()
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result) as mock_stop, \
             mock.patch.object(hub_daemon, "start_server", return_value=start_result) as mock_start:
            call_order.attach_mock(mock_stop, "stop")
            call_order.attach_mock(self.mock_wait, "wait")
            call_order.attach_mock(mock_start, "start")
            result = hub_daemon.restart_server()

        self.assertTrue(result["ok"])
        self.assertTrue(result["stopped_previous"])
        self.assertEqual(result["pid"], 2)
        self.assertEqual(result["url"], start_result["url"])
        self.assertNotIn("note", result)
        default_server_port = hub_model.HubConfig().server_port
        self.assertEqual(
            call_order.mock_calls,
            [mock.call.stop(), mock.call.wait(default_server_port), mock.call.start()],
        )

    def test_s2b_absent_server_is_just_started(self) -> None:
        stop_result = {"ok": True, "was_running": False}
        start_result = {"ok": True, "pid": 3, "url": "http://localhost:8794/hub.html"}
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result), \
             mock.patch.object(hub_daemon, "start_server", return_value=start_result):
            result = hub_daemon.restart_server()

        self.assertTrue(result["ok"])
        self.assertFalse(result["stopped_previous"])

    def test_s3_already_running_after_stop_is_reported_as_failure(self) -> None:
        stop_result = {"ok": True, "was_running": True}
        start_result = {"ok": True, "already_running": True}
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result), \
             mock.patch.object(hub_daemon, "start_server", return_value=start_result):
            result = hub_daemon.restart_server()

        self.assertFalse(result["ok"])
        self.assertEqual(result["phase"], "start")
        self.assertIn("orphaned_evidence", result["reason"])

    def test_s4_forced_stop_surfaces_as_note(self) -> None:
        stop_result = {"ok": True, "was_running": True, "forced": True}
        start_result = {"ok": True, "pid": 4, "url": "http://localhost:8794/hub.html"}
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result), \
             mock.patch.object(hub_daemon, "start_server", return_value=start_result):
            result = hub_daemon.restart_server()

        self.assertTrue(result["ok"])
        self.assertEqual(result["note"], hub_daemon.FORCED_STOP_NOTE)

    def test_s5_start_failure_carries_reason_and_log_tail(self) -> None:
        stop_result = {"ok": True, "was_running": True}
        start_result = {
            "ok": False,
            "reason": "포트 8794 이 이미 사용 중입니다(다른 프로세스)",
            "log_tail": "tail",
        }
        with mock.patch.object(hub_daemon, "stop_server", return_value=stop_result), \
             mock.patch.object(hub_daemon, "start_server", return_value=start_result):
            result = hub_daemon.restart_server()

        self.assertFalse(result["ok"])
        self.assertEqual(result["phase"], "start")
        self.assertEqual(result["reason"], start_result["reason"])
        self.assertEqual(result["log_tail"], start_result["log_tail"])


class OpenBrowserFallbackTest(unittest.TestCase):
    """D8·GOTCHA 7 — 포커스 경로 성공/실패, 미지원 플랫폼, 이중 실패를 예외 없이 흡수한다."""

    URL = "http://localhost:8794/hub.html"

    def test_o1_darwin_success_does_not_touch_webbrowser(self) -> None:
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0)) as mock_run, \
             mock.patch("webbrowser.open") as mock_webbrowser_open:
            result = hub_daemon.open_browser(self.URL, platform_name="darwin")

        mock_run.assert_called_once()
        mock_webbrowser_open.assert_not_called()
        self.assertTrue(result.opened)
        self.assertTrue(result.focus_requested)
        self.assertIsNone(result.fallback_reason)

    def test_o2_darwin_failure_falls_back_with_reason(self) -> None:
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1)), \
             mock.patch("webbrowser.open", return_value=True) as mock_webbrowser_open:
            result = hub_daemon.open_browser(self.URL, platform_name="darwin")

        mock_webbrowser_open.assert_called_once()
        self.assertTrue(result.opened)
        self.assertFalse(result.focus_requested)
        self.assertIsNotNone(result.fallback_reason)

    def test_o3_non_darwin_uses_webbrowser_only(self) -> None:
        with mock.patch("subprocess.run") as mock_run, \
             mock.patch("webbrowser.open", return_value=True):
            result = hub_daemon.open_browser(self.URL, platform_name="linux")

        mock_run.assert_not_called()
        self.assertTrue(result.opened)
        self.assertFalse(result.focus_requested)

    def test_o4_both_paths_failing_is_not_an_exception(self) -> None:
        with mock.patch("subprocess.run", side_effect=OSError("no such file")), \
             mock.patch("webbrowser.open", side_effect=RuntimeError("boom")):
            result = hub_daemon.open_browser(self.URL, platform_name="darwin")

        self.assertFalse(result.opened)

    def test_o5_non_darwin_webbrowser_exception_still_carries_a_reason(self) -> None:
        """검수 지적 — 포커스 경로 자체가 없는 플랫폼(fallback_reason 이 아직 None)에서
        webbrowser.open() 마저 예외를 던지면 그 사유가 소실되지 않아야 한다."""
        with mock.patch("webbrowser.open", side_effect=RuntimeError("boom")):
            result = hub_daemon.open_browser(self.URL, platform_name="linux")

        self.assertFalse(result.opened)
        self.assertEqual(result.fallback_reason, "boom")


if __name__ == "__main__":
    unittest.main()
