"""hub_statusline.py 단위 테스트. 실제 ~/.claude 는 건드리지 않고 hub_collect 의 모듈 상수를
임시 디렉토리로 바꿔치기한 뒤 원상복구한다(WriteHubHtmlAtomicityTest 의 setUp/tearDown 패턴).
docs/prps/hub-usage-reset-time-and-refresh.md 「테스트 계획」 케이스 R26~R29 +
docs/prps/hub-card-cleanup-and-usage-source.md 「테스트 계획」 케이스 N39~N42(퍼센트도
캡처값 비교에 들어간 뒤의 회귀 — 결정 P4).
"""

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_statusline  # noqa: E402

ONE_HOUR_SECONDS = 60 * 60


def _rate_limits_payload(
    now_s: int,
    session_hours_from_now: float = 2.0,
    weekly_hours_from_now: float = 48.0,
    session_used_percentage: float = 23,
    weekly_used_percentage: float = 41,
) -> str:
    payload = {
        "rate_limits": {
            "five_hour": {
                "used_percentage": session_used_percentage,
                "resets_at": now_s + int(session_hours_from_now * ONE_HOUR_SECONDS),
            },
            "seven_day": {
                "used_percentage": weekly_used_percentage,
                "resets_at": now_s + int(weekly_hours_from_now * ONE_HOUR_SECONDS),
            },
        }
    }
    return json.dumps(payload)


class HubStatuslineEntrypointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"

    def tearDown(self) -> None:
        self.temp_dir.chmod(0o755)
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_with_stdin(self, text: str) -> tuple[int, str]:
        captured = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(text)), redirect_stdout(captured):
            exit_code = hub_statusline.main()
        return exit_code, captured.getvalue()


class NormalPayloadTest(HubStatuslineEntrypointTest):
    """케이스 R26 — 정상 페이로드는 캡처 파일과 상태줄 한 줄을 만든다."""

    def test_r26_writes_capture_and_prints_summary(self) -> None:
        now_s = int(time.time())
        exit_code, output = self._run_with_stdin(_rate_limits_payload(now_s))

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.strip(), "세션 23% · 주간 41%")
        self.assertTrue(hub_collect.RATE_LIMITS_PATH.is_file())
        capture, warnings = hub_collect.read_rate_limit_capture()
        self.assertIsNotNone(capture)
        self.assertEqual(warnings, ())


class SameReplayDoesNotRewriteTest(HubStatuslineEntrypointTest):
    """케이스 R27·N40 — 완전히 같은 페이로드(퍼센트 포함)로 재실행하면 파일을 다시 쓰지
    않는다(결정 S3·P4 회귀 방지, GOTCHA 4 — captured_at_ms 를 비교에 넣으면 이 테스트가
    깨진다)."""

    def test_r27_identical_payload_leaves_mtime_unchanged(self) -> None:
        text = _rate_limits_payload(int(time.time()))
        self._run_with_stdin(text)
        mtime_before = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self._run_with_stdin(text)
        mtime_after = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self.assertEqual(mtime_before, mtime_after)


class ChangedResetsRewriteTest(HubStatuslineEntrypointTest):
    """케이스 R28 — 리셋 시각이 달라진 페이로드는 파일을 갱신한다."""

    def test_r28_different_reset_times_rewrite_the_file(self) -> None:
        now_s = int(time.time())
        self._run_with_stdin(_rate_limits_payload(now_s, session_hours_from_now=2.0))
        mtime_before = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self._run_with_stdin(_rate_limits_payload(now_s, session_hours_from_now=3.0))
        mtime_after = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self.assertNotEqual(mtime_before, mtime_after)


class ChangedPercentRewriteTest(HubStatuslineEntrypointTest):
    """케이스 N39 — 리셋 시각은 그대로인데 퍼센트만 달라진 페이로드도 파일을 갱신한다
    (결정 P4 — 비교를 네 값으로 확장한 회귀 방지. 리셋만 비교했다면 이 케이스는 안 써진다)."""

    def test_n39_percent_only_change_rewrites_the_file(self) -> None:
        now_s = int(time.time())
        self._run_with_stdin(_rate_limits_payload(now_s, session_used_percentage=23))
        mtime_before = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self._run_with_stdin(_rate_limits_payload(now_s, session_used_percentage=24))
        mtime_after = hub_collect.RATE_LIMITS_PATH.stat().st_mtime_ns

        self.assertNotEqual(mtime_before, mtime_after)


class FailureIsolationTest(HubStatuslineEntrypointTest):
    """케이스 R29 — 깨진 stdin·rate_limits 없음·쓰기 불가 디렉토리 모두 예외 없이 exit 0."""

    def test_r29_broken_stdin_never_raises(self) -> None:
        exit_code, _output = self._run_with_stdin("{not json")
        self.assertEqual(exit_code, 0)
        self.assertFalse(hub_collect.RATE_LIMITS_PATH.exists())

    def test_r29_missing_rate_limits_never_raises_and_writes_nothing(self) -> None:
        exit_code, output = self._run_with_stdin(json.dumps({"hookEventName": "Status"}))
        self.assertEqual(exit_code, 0)
        self.assertEqual(output.strip(), "")
        self.assertFalse(hub_collect.RATE_LIMITS_PATH.exists())

    def test_r29_unwritable_directory_never_raises_and_preserves_existing_capture(self) -> None:
        now_s = int(time.time())
        self._run_with_stdin(_rate_limits_payload(now_s, session_hours_from_now=2.0))
        existing_bytes = hub_collect.RATE_LIMITS_PATH.read_bytes()

        self.temp_dir.chmod(0o500)  # mkstemp 가 새 임시 파일을 만들 수 없게 한다
        try:
            exit_code, _output = self._run_with_stdin(
                _rate_limits_payload(now_s, session_hours_from_now=5.0)
            )
        finally:
            self.temp_dir.chmod(0o755)

        self.assertEqual(exit_code, 0)
        self.assertEqual(hub_collect.RATE_LIMITS_PATH.read_bytes(), existing_bytes)


if __name__ == "__main__":
    unittest.main()
