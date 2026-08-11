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

    def test_fresh_heartbeat_and_existing_hub_html_opens_http_url_without_collecting(self) -> None:
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선
        hub_collect.HUB_HTML_PATH.write_text("<html></html>")

        with mock.patch.object(hub_collect, "collect_snapshot") as mock_collect, \
             mock.patch("webbrowser.open"):
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
             mock.patch("webbrowser.open"):
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
             mock.patch("webbrowser.open"):
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


class CmdStatusServerSummaryTest(unittest.TestCase):
    """검수 M2-3 — `/hub status` 가 server_collect_stalled 를 서버 요약에 포함하는지 확인한다.
    실제 ~/.claude 는 건드리지 않는다 — HUB_HTML_PATH·hook_install_status·이벤트 읽기를 전부 모킹한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_html_path = hub_collect.HUB_HTML_PATH
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"  # 존재하지 않는 경로 — 실제 파일 미접근

    def tearDown(self) -> None:
        hub_collect.HUB_HTML_PATH = self.original_html_path
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


if __name__ == "__main__":
    unittest.main()
