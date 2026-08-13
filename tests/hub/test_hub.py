"""hub.py CLI 엔트리 단위 테스트. 검수 M7(4) — collect 예외를 ok:false 계약으로 변환하는지 확인."""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub  # noqa: E402
import hub_collect  # noqa: E402
import hub_daemon  # noqa: E402
import hub_model  # noqa: E402
import hub_settings  # noqa: E402


class _Args:
    def __init__(self, as_json: bool = True) -> None:
        self.json = as_json


class CmdCollectFailureContractTest(unittest.TestCase):
    """검수 M7 — hub.py cmd_collect/cmd_open 은 예상치 못한 예외를 원시 트레이스백으로 흘리지 않는다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_collect_snapshot_exception_becomes_ok_false_contract(self) -> None:
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=RuntimeError("boom")):
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = hub.cmd_collect(_Args())

        self.assertEqual(exit_code, 1)
        payload = json.loads(captured.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("boom", payload["reason"])

    def test_failure_is_recorded_and_readable_via_status(self) -> None:
        with mock.patch.object(hub_collect, "collect_snapshot", side_effect=RuntimeError("boom")):
            with redirect_stdout(io.StringIO()):
                hub.cmd_collect(_Args())

        recorded = hub_collect.read_last_collect_failure()
        self.assertIsNotNone(recorded)
        self.assertIn("boom", recorded["reason"])

    def test_success_clears_previous_failure_record(self) -> None:
        hub_collect.record_collect_failure("이전 실패")
        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             mock.patch.object(hub_collect, "write_hub_html"):
            mock_collect.return_value = mock.Mock(projects=())
            with redirect_stdout(io.StringIO()):
                exit_code = hub.cmd_collect(_Args())

        self.assertEqual(exit_code, 0)
        self.assertIsNone(hub_collect.read_last_collect_failure())


class CmdOpenServerAwareTest(unittest.TestCase):
    """개정 쟁점 R2 — `/hub`(cmd_open)는 서버를 절대 기동하지 않는다(요구 R-2)."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_heartbeat_path = hub_collect.SERVER_HEARTBEAT_PATH
        self.original_config_path = hub_collect.CONFIG_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.SERVER_HEARTBEAT_PATH = self.temp_dir / "server_heartbeat"
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.SERVER_HEARTBEAT_PATH = self.original_heartbeat_path
        hub_collect.CONFIG_PATH = self.original_config_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _stub_open_browser(self):
        """실제 브라우저를 띄우지 않는 hub_daemon.open_browser 대체(GOTCHA 3).

        `mock.patch("webbrowser.open")` 는 cmd_open 이 hub_daemon.open_browser 를 거쳐
        `/usr/bin/open` 을 서브프로세스로 실행하는 경로를 전혀 막지 못한다 — hub_daemon
        모듈의 함수 자체를 대체해야 한다.
        """
        return mock.patch.object(
            hub_daemon, "open_browser",
            return_value=hub_model.BrowserOpenResult(opened=True, focus_requested=True, fallback_reason=None),
        )

    def test_fresh_heartbeat_and_existing_hub_html_opens_http_url_without_collecting(self) -> None:
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선
        hub_collect.HUB_HTML_PATH.write_text("<html></html>")

        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             self._stub_open_browser():
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = hub.cmd_open(_Args())

        self.assertEqual(exit_code, 0)
        mock_collect.assert_not_called()
        payload = json.loads(captured.getvalue())
        self.assertTrue(payload["server_alive"])
        self.assertTrue(payload["url"].startswith("http://localhost:8794"))
        self.assertNotIn("note", payload)

    def test_fresh_heartbeat_but_missing_hub_html_recovers_with_one_time_collect(self) -> None:
        """검수 M1 — 하트비트만으로 서버 URL 을 열면 hub.html 이 없을 때 깨진 링크를 연다.
        server_alive=true 여도 hub.html 실재를 확인해 1회 수집으로 복구해야 한다."""
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선, hub.html 은 없음

        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             mock.patch.object(hub_collect, "write_hub_html"), \
             self._stub_open_browser():
            mock_collect.return_value = mock.Mock(projects=())
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = hub.cmd_open(_Args())

        self.assertEqual(exit_code, 0)
        mock_collect.assert_called_once()
        payload = json.loads(captured.getvalue())
        self.assertTrue(payload["server_alive"])
        self.assertTrue(payload["url"].startswith("file://"))
        self.assertIn("다음 수집 주기", payload["note"])

    def test_no_heartbeat_collects_once_and_opens_file_url_with_note(self) -> None:
        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             mock.patch.object(hub_collect, "write_hub_html"), \
             self._stub_open_browser():
            mock_collect.return_value = mock.Mock(projects=())
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = hub.cmd_open(_Args())

        self.assertEqual(exit_code, 0)
        mock_collect.assert_called_once()
        payload = json.loads(captured.getvalue())
        self.assertFalse(payload["server_alive"])
        self.assertTrue(payload["url"].startswith("file://"))
        self.assertIn("server start", payload["note"])

    def test_open_payload_exposes_browser_focus_field(self) -> None:
        """계약 회귀 — `open --json` payload 에 browser_focus_requested 가 노출된다."""
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선
        hub_collect.HUB_HTML_PATH.write_text("<html></html>")

        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             self._stub_open_browser():
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = hub.cmd_open(_Args())

        self.assertEqual(exit_code, 0)
        mock_collect.assert_not_called()
        payload = json.loads(captured.getvalue())
        self.assertIn("browser_focus_requested", payload)
        self.assertTrue(payload["browser_focus_requested"])


class CmdStatusServerSummaryTest(unittest.TestCase):
    """검수 M2-3 — `/hub status` 가 server_collect_stalled 를 서버 요약에 포함하는지 확인한다.
    실제 ~/.claude 는 건드리지 않는다 — HUB_HTML_PATH·hook_install_status·이벤트 읽기·
    config.json·사용량 히스토리·마지막 collect 실패 기록을 전부 모킹/격리한다(검수 M2 — cmd_status 가
    load_config()·_usage_sample_age_ms() 를 호출하게 되면서 실제 개발자 머신의
    비공개 사용량 파일을 읽던 회귀가 있었다).

    LAST_COLLECT_ERROR_PATH 도 격리한다(검수 R2-n1) — cmd_status 는 read_last_collect_failure()
    도 부르는데, 그 상수는 HUB_HOME 과 별개로 임포트 시점에 확정되므로 직접 바꿔야 한다.
    RATE_LIMITS_PATH·SETTINGS_PATH 도 같은 이유로 격리한다 — cmd_status 가
    hub_settings.statusline_install_status()·hub_collect.read_rate_limit_capture() 를
    새로 호출하게 되면서(docs/prps/hub-usage-reset-time-and-refresh.md, 사용률 퍼센트까지
    이 캡처 하나로 통합된 뒤로는 docs/prps/hub-card-cleanup-and-usage-source.md 결정 P1)
    실제 개발자 머신의 ~/.claude/settings.json·~/.claude/hub/rate_limits.json 을 읽던
    회귀가 생길 수 있었다. 이 클래스의 "실제 ~/.claude 를 건드리지 않는다"는 주장이 문자
    그대로 참이 되는 조건이다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_config_path = hub_collect.CONFIG_PATH
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        self.original_settings_path = hub_settings.SETTINGS_PATH
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"  # 존재하지 않는 경로 — 실제 파일 미접근
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"  # 존재하지 않으면 기본값
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"  # 존재하지 않으면 None
        hub_settings.SETTINGS_PATH = self.temp_dir / "settings.json"  # 존재하지 않으면 미설치로 판정

    def tearDown(self) -> None:
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.CONFIG_PATH = self.original_config_path
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        hub_settings.SETTINGS_PATH = self.original_settings_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_status(self, collect_stalled: bool) -> hub_model.ServerStatus:
        return hub_model.ServerStatus(
            record=None, process_present=True, heartbeat_age_ms=1, alive=not collect_stalled,
            http_ok=True, crashed_evidence=False, log_tail=None, orphaned_evidence=False,
            collect_stalled=collect_stalled,
        )

    def _run_cmd_status(self, collect_stalled: bool) -> dict:
        with mock.patch.object(hub_daemon, "server_status", return_value=self._make_status(collect_stalled)), \
             mock.patch.object(hub_collect, "read_recent_events", return_value=([], ())), \
             mock.patch("hub_settings.hook_install_status", return_value={}):
            captured = io.StringIO()
            with redirect_stdout(captured):
                hub.cmd_status(_Args())
        return json.loads(captured.getvalue())

    def test_collect_stalled_is_surfaced_in_status_summary(self) -> None:
        payload = self._run_cmd_status(collect_stalled=True)
        self.assertTrue(payload["server_collect_stalled"])

    def test_collect_not_stalled_is_surfaced_as_false(self) -> None:
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertFalse(payload["server_collect_stalled"])

    def test_usage_sample_age_ms_is_null_when_switch_is_off(self) -> None:
        """`commands/hub.md` 의 공개 출력 계약 — 스위치 off 면 usage_sample_age_ms 는 null."""
        hub_collect.CONFIG_PATH.write_text(json.dumps({"show_usage_panel": False}))
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertFalse(payload["usage_panel_enabled"])
        self.assertIsNone(payload["usage_sample_age_ms"])

    def test_usage_sample_age_ms_is_null_when_usage_file_is_absent(self) -> None:
        """`commands/hub.md` 의 공개 출력 계약 — 캡처 파일이 없으면 enabled 는 true 인데 age 는 null.

        statusLine 을 등록하지 않은 사용자가 **항상** 보게 되는 상태다(검수 R2-n2, 결정 P1).
        스위치 off 와 값이 다르다는 점이 핵심이다 — off 는 enabled 도 false 다. setUp 이 잡아 둔
        임시 경로에 파일을 쓰지 않는 것만으로 이 상황이 재현된다.
        """
        self.assertFalse(hub_collect.RATE_LIMITS_PATH.exists())
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertTrue(payload["usage_panel_enabled"])
        self.assertIsNone(payload["usage_sample_age_ms"])

    def test_usage_sample_age_ms_is_int_when_usage_file_is_normal(self) -> None:
        """`commands/hub.md` 의 공개 출력 계약 — 캡처에 퍼센트가 있으면 usage_sample_age_ms 는
        정수다(결정 P1 — 퍼센트의 유일한 출처가 캡처 파일로 바뀌었다)."""
        hub_collect.RATE_LIMITS_PATH.write_text(
            json.dumps(
                {
                    "captured_at_ms": 1,
                    "session_resets_at_ms": None,
                    "weekly_resets_at_ms": None,
                    "session_used_percent": 10,
                    "weekly_used_percent": 19,
                }
            )
        )
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertTrue(payload["usage_panel_enabled"])
        self.assertIsInstance(payload["usage_sample_age_ms"], int)

    def test_rate_limit_diagnostic_fields_are_null_when_capture_and_statusline_are_absent(self) -> None:
        """docs/prps/hub-usage-reset-time-and-refresh.md 「hub.py」 절 — statusline_installed·
        rate_limit_capture_age_ms·rate_limit_resets_remaining_ms 3필드가 새로 추가된다."""
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertFalse(payload["statusline_installed"])
        self.assertIsNone(payload["rate_limit_capture_age_ms"])
        self.assertIsNone(payload["rate_limit_resets_remaining_ms"])

    def test_rate_limit_diagnostic_fields_are_null_when_switch_is_off_even_if_capture_exists(self) -> None:
        """검수 MEDIUM 1 회귀 방지 — PRP 「확정된 전제」4: show_usage_panel:false 는 usage 파일뿐
        아니라 rate_limits 캡처 파일도 읽지 않는다. 캡처가 있어도 스위치가 꺼져 있으면 두
        진단 필드는 null 이어야 한다(캡처 부재와 스위치 off 를 구분 못 하는 회귀를 잡는다)."""
        hub_collect.CONFIG_PATH.write_text(json.dumps({"show_usage_panel": False}))
        hub_collect.RATE_LIMITS_PATH.write_text(
            json.dumps({"captured_at_ms": 1, "session_resets_at_ms": 2, "weekly_resets_at_ms": 3})
        )
        payload = self._run_cmd_status(collect_stalled=False)
        self.assertFalse(payload["usage_panel_enabled"])
        self.assertIsNone(payload["rate_limit_capture_age_ms"])
        self.assertIsNone(payload["rate_limit_resets_remaining_ms"])


if __name__ == "__main__":
    unittest.main()
