"""hub_server.py 단위 테스트. 검수 M1 — 쓰기 게이트가 hub.html 실재를 함께 확인하는지,
쓰기 실패 시 캐시가 무효화되고 실패 기록이 지워지지 않는지 확인한다.
검수 M2 — 사이클 안의 어떤 예외도(기록 자체의 실패까지 포함) 수집 스레드를 죽이지 못하는지,
쓰기가 없어도 성공한 사이클이면 낡은 실패 기록을 지우는지 확인한다.
"""

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
import hub_server  # noqa: E402


def _minimal_snapshot(collected_at_ms: int = 1) -> hub_model.HubSnapshot:
    return hub_model.HubSnapshot(
        collected_at_ms=collected_at_ms, projects=(), unresolved_dir_names=(), warnings=()
    )


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
            last_key = hub_server._run_collect_cycle(None)
        self.assertTrue(hub_collect.HUB_HTML_PATH.exists())

        hub_collect.HUB_HTML_PATH.unlink()  # 외부에서 삭제/손상된 상황을 흉내낸다
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            next_key = hub_server._run_collect_cycle(last_key)  # 캐시 키 기준으로는 "내용 불변"

        self.assertEqual(last_key, next_key)
        self.assertTrue(hub_collect.HUB_HTML_PATH.exists(), "hub.html 이 재생성되지 않음")

    def test_write_failure_invalidates_cache_and_keeps_failure_recorded(self) -> None:
        """검수 M1(2) — 쓰기 실패 시 다음 사이클이 반드시 재시도하고, 그 사이 실패 기록이
        지워지지 않는다(옛 캐시 키가 남으면 다음 사이클이 쓰기를 건너뛰고 실패 증거까지
        clear_collect_failure() 로 지워 버리는 것이 원래 결함이었다)."""
        snapshot = _minimal_snapshot()
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot), \
             mock.patch.object(hub_collect, "write_hub_html", side_effect=OSError("disk full")):
            first_key = hub_server._run_collect_cycle(None)

        self.assertIsNone(first_key)  # 캐시 무효화 — 다음 사이클이 무조건 다시 쓰기를 시도한다
        recorded = hub_collect.read_last_collect_failure()
        self.assertIsNotNone(recorded)
        self.assertIn("disk full", recorded["reason"])

        # 다음 사이클: 쓰기가 이번엔 성공한다.
        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            second_key = hub_server._run_collect_cycle(first_key)

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
            last_key = hub_server._run_collect_cycle(None)

        hub_collect.record_collect_failure("다른 경로가 남긴 낡은 실패")
        self.assertIsNotNone(hub_collect.read_last_collect_failure())

        with mock.patch.object(hub_collect, "collect_snapshot", return_value=snapshot):
            next_key = hub_server._run_collect_cycle(last_key)  # 내용 불변 + hub.html 실재 → 쓰기 스킵

        self.assertEqual(last_key, next_key)
        self.assertIsNone(hub_collect.read_last_collect_failure())


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
            hub_server._collect_loop(config, stop_event)  # 예외 없이 정상 반환해야 한다

        self.assertGreaterEqual(attempt_count["n"], 2)


if __name__ == "__main__":
    unittest.main()
