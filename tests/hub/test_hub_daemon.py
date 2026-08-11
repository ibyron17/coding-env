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


if __name__ == "__main__":
    unittest.main()
