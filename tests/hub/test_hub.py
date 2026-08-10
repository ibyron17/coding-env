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


if __name__ == "__main__":
    unittest.main()
