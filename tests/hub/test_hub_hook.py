"""hub_hook.py 단위 테스트. 실제 ~/.claude 는 건드리지 않고 hub_collect 의 모듈 상수를
임시 디렉토리로 바꿔치기한 뒤 원상복구한다. 검수 M4(서브프로세스 분리)·M5(리텐션 도달성) 대상.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_hook  # noqa: E402

EIGHT_DAYS_SECONDS = 8 * 24 * 60 * 60
ONE_HOUR_SECONDS = 60 * 60


class HubHookScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_events_dir = hub_collect.EVENTS_DIR
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_config_path = hub_collect.CONFIG_PATH
        self.original_spawn_stamp_path = hub_collect.SPAWN_STAMP_PATH
        self.original_heartbeat_path = hub_collect.SERVER_HEARTBEAT_PATH

        hub_collect.EVENTS_DIR = self.temp_dir / "events"
        hub_collect.EVENTS_DIR.mkdir()
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"
        hub_collect.SPAWN_STAMP_PATH = self.temp_dir / ".collect_spawn_stamp"
        hub_collect.SERVER_HEARTBEAT_PATH = self.temp_dir / "server_heartbeat"

    def tearDown(self) -> None:
        hub_collect.EVENTS_DIR = self.original_events_dir
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.CONFIG_PATH = self.original_config_path
        hub_collect.SPAWN_STAMP_PATH = self.original_spawn_stamp_path
        hub_collect.SERVER_HEARTBEAT_PATH = self.original_heartbeat_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_hook_with_stdin(self, payload: dict) -> None:
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            hub_hook.main()


class RetentionReachabilityTest(HubHookScenarioTest):
    """검수 M5 — hub.html 이 없어도(허브 off 상태) 리텐션이 여전히 동작해야 한다."""

    def test_old_event_file_pruned_even_without_hub_html(self) -> None:
        old_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - EIGHT_DAYS_SECONDS))
        old_file = hub_collect.EVENTS_DIR / f"{old_date}.jsonl"
        old_file.write_text('{"t":1,"e":"Stop","s":"s","c":"/repo"}\n')

        self.assertFalse(hub_collect.HUB_HTML_PATH.exists())  # 허브 off 상태 전제

        # 검수 M2-5 이후로는 이 조합(hub.html 없음 + 서버 죽음)이 실제로 spawn 을 한다 — 이
        # 테스트의 관심사는 리텐션 정리이므로 subprocess.Popen 을 모킹해 실제 프로세스를
        # 띄우지 않는다(실제 ~/.claude 를 건드리지 않는다는 이 파일의 전제를 지킨다).
        with mock.patch("subprocess.Popen"):
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s2", "cwd": "/repo"})

        self.assertFalse(old_file.exists())


class SpawnsBackgroundCollectTest(HubHookScenarioTest):
    """검수 M4 — 훅은 재수집을 서브프로세스로 떼어내고 자신은 무거운 작업을 하지 않는다."""

    def test_stale_hub_html_triggers_subprocess_spawn_not_inline_collect(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        with mock.patch("subprocess.Popen") as mock_popen, \
             mock.patch.object(hub_collect, "collect_snapshot") as mock_collect_snapshot, \
             mock.patch.object(hub_collect, "write_hub_html") as mock_write_hub_html:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()
        spawned_command = mock_popen.call_args[0][0]
        self.assertIn("collect", spawned_command)
        mock_collect_snapshot.assert_not_called()
        mock_write_hub_html.assert_not_called()

    def test_fresh_hub_html_does_not_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("fresh-marker")  # mtime = 지금

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_not_called()

    def test_missing_hub_html_spawns_when_server_is_not_alive(self) -> None:
        """검수 M2-5 — 서버가 죽어 있고(하트비트 없음) hub.html 도 없으면 훅 폴백이 뚫려야
        한다. 예전에는 이 조합이 항상 False 라, 상주 서버가 HUB_HOME 쓰기 실패 등으로
        hub.html 을 한 번도 못 만든 채 수집 스레드까지 죽으면 훅 폴백조차 영원히 막혀
        사용자가 영구히 빈 페이지만 보는 이중 실패였다(hub_server_state.should_spawn_collect 참조)."""
        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()


class ServerDelegationTest(HubHookScenarioTest):
    """검수 개정 쟁점 R3 — 상주 서버가 살아 있으면(하트비트 신선) 훅은 spawn 하지 않는다."""

    def test_fresh_heartbeat_suppresses_spawn_even_with_stale_hub_html(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선한 하트비트

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_not_called()

    def test_stale_heartbeat_falls_back_to_hook_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")
        os.utime(hub_collect.SERVER_HEARTBEAT_PATH, (old_time, old_time))  # 서버 크래시 흉내

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()


class ThrottleDebounceStampTest(HubHookScenarioTest):
    """검수 n3 — 훅 버스트(여러 세션이 거의 동시에 훅을 쏘는 경우) 에서 spawn 이 한 번만 일어난다.

    hub.html 의 mtime 은 spawn 된 자식 프로세스가 다 끝나야 바뀌므로, 그것만 보면 뒤따르는
    훅들이 전부 spawn 을 결정해 버린다(실측: 훅 6개 버스트 → 동시 collect 6개). spawn 직전에
    스탬프를 찍어 디바운스 판정 시점을 옮긴다.
    """

    def test_burst_of_hooks_spawns_collect_only_once(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        with mock.patch("subprocess.Popen") as mock_popen:
            for _ in range(3):
                self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()

    def test_stamp_is_touched_before_first_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        self.assertFalse(hub_collect.SPAWN_STAMP_PATH.exists())
        with mock.patch("subprocess.Popen"):
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})
        self.assertTrue(hub_collect.SPAWN_STAMP_PATH.exists())


if __name__ == "__main__":
    unittest.main()
