"""hub_server_state 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M21~M26,
D6(parse_server_record) — hub_daemon.py 와 hub_collect.py 가 공유하는 파서를 하나로
합쳤다(검수 m3). 실사용 경로(hub_collect.read_server_record)를 이 테스트가 직접 덮는다."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_server_state  # noqa: E402  (sys.path 조정 후 임포트)

BASE_TIME_MS = 1_786_000_000_000


class ShouldSpawnCollectTest(unittest.TestCase):
    """M21~M24 — 훅의 재수집 spawn 판정(개정 쟁점 R3)."""

    THROTTLE_MS = 5000

    def test_m21_server_alive_always_false(self) -> None:
        """서버가 살아 있으면 쓰로틀이 지났어도 spawn 하지 않는다 — 서버가 전담한다."""
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=True,
            hub_html_mtime_ms=BASE_TIME_MS - 60_000, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m22_server_dead_no_stamp_hub_html_stale(self) -> None:
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=BASE_TIME_MS - 6000, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertTrue(result)

    def test_m23_server_dead_recent_stamp_is_throttled(self) -> None:
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=BASE_TIME_MS - 60_000, spawn_stamp_mtime_ms=BASE_TIME_MS - 2000,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m24_hub_html_missing_but_server_alive_is_false(self) -> None:
        """서버가 살아 있으면 hub.html 이 없어도 False — 다음 사이클에 서버가 만든다."""
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=True,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m24b_hub_html_missing_and_server_dead_with_no_stamp_spawns_immediately(self) -> None:
        """검수 M2-5 — 서버가 죽고 hub.html 도 없으면(HUB_HOME 쓰기 실패 등으로 한 번도 못
        만든 경우 포함) 훅 폴백이 곧바로 뚫려야 한다. 예전에는 hub_html_mtime_ms 가 None 이면
        서버 상태와 무관하게 항상 False 라, 상주 서버가 hub.html 을 한 번도 못 만든 채 수집
        스레드까지 죽으면 훅 폴백조차 영원히 막히는 이중 실패였다."""
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertTrue(result)

    def test_m24c_hub_html_missing_and_server_dead_but_recent_stamp_is_throttled(self) -> None:
        """즉시 재시도를 허용해도 쓰로틀은 여전히 산다 — 매 훅마다 spawn 하지 않는다."""
        result = hub_server_state.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=BASE_TIME_MS - 2000,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)


class IsServerAliveTest(unittest.TestCase):
    """M25 — 하트비트 나이로 상주 서버 생존을 판정한다."""

    TTL_MS = 15_000

    def test_m25_no_heartbeat_file(self) -> None:
        self.assertFalse(hub_server_state.is_server_alive(BASE_TIME_MS, None, self.TTL_MS))

    def test_m25_just_before_ttl(self) -> None:
        heartbeat_mtime_ms = BASE_TIME_MS - (self.TTL_MS - 1)
        self.assertTrue(hub_server_state.is_server_alive(BASE_TIME_MS, heartbeat_mtime_ms, self.TTL_MS))

    def test_m25_just_after_ttl(self) -> None:
        heartbeat_mtime_ms = BASE_TIME_MS - self.TTL_MS
        self.assertFalse(hub_server_state.is_server_alive(BASE_TIME_MS, heartbeat_mtime_ms, self.TTL_MS))


class ServerHeartbeatTtlMsTest(unittest.TestCase):
    """M26 — 수집 주기 3배, 하한 15초."""

    def test_m26_short_interval_hits_floor(self) -> None:
        self.assertEqual(hub_server_state.server_heartbeat_ttl_ms(1), 15_000)

    def test_m26_default_interval_hits_floor(self) -> None:
        self.assertEqual(hub_server_state.server_heartbeat_ttl_ms(5), 15_000)

    def test_m26_long_interval_uses_multiplier(self) -> None:
        self.assertEqual(hub_server_state.server_heartbeat_ttl_ms(60), 180_000)


class ParseServerRecordTest(unittest.TestCase):
    """D6 — 정상 1건, 나머지 전부 None(예외 없음). hub_daemon.py 와 hub_collect.py 가 공유하는
    파서를 hub_server_state.py 하나로 합쳤다(검수 m3) — 실사용 경로(hub_collect.read_server_record)를
    이 테스트가 직접 덮는다."""

    def test_d6_valid_record(self) -> None:
        record = hub_server_state.parse_server_record(
            '{"pid": 123, "port": 8794, "started_at_ms": 1786000000000}'
        )
        self.assertIsNotNone(record)
        self.assertEqual((record.pid, record.port, record.started_at_ms), (123, 8794, 1786000000000))

    def test_d6_missing_field(self) -> None:
        self.assertIsNone(hub_server_state.parse_server_record('{"pid": 123, "port": 8794}'))

    def test_d6_broken_json(self) -> None:
        self.assertIsNone(hub_server_state.parse_server_record("{not valid json"))

    def test_d6_empty_file(self) -> None:
        self.assertIsNone(hub_server_state.parse_server_record(""))


if __name__ == "__main__":
    unittest.main()
