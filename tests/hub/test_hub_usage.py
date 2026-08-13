"""hub_usage 단위 테스트. docs/prps/hub-usage-reset-time-and-refresh.md 「테스트 계획」
케이스 R10~R12(변경 없는 함수) + docs/prps/hub-card-cleanup-and-usage-source.md 「테스트 계획」
케이스 N1~N26(캡처 단일 출처로 교체된 함수들)."""

import dataclasses
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_usage  # noqa: E402  (sys.path 조정 후 임포트)

BASE_TIME_MS = 1_786_433_123_899


class IsUsageSampleExpiredTest(unittest.TestCase):
    """케이스 14~17 — U3 그대로(캡처의 sampled_at_ms 로 판단해도 만료 규칙은 불변)."""

    def _sample_at(self, sampled_at_ms: int) -> hub_usage.UsageSample:
        return hub_usage.UsageSample(sampled_at_ms=sampled_at_ms, session_percent=10, weekly_percent=19)

    def test_case14_age_four_hours_fifty_nine_minutes_is_not_expired(self) -> None:
        age_ms = (4 * 60 + 59) * 60 * 1000
        sample = self._sample_at(BASE_TIME_MS - age_ms)
        self.assertFalse(hub_usage.is_usage_sample_expired(sample, BASE_TIME_MS))

    def test_case15_age_exactly_five_hours_is_expired_boundary_inclusive(self) -> None:
        sample = self._sample_at(BASE_TIME_MS - hub_usage.USAGE_MAX_SAMPLE_AGE_MS)
        self.assertTrue(hub_usage.is_usage_sample_expired(sample, BASE_TIME_MS))

    def test_case16_age_five_hours_one_minute_is_expired(self) -> None:
        age_ms = hub_usage.USAGE_MAX_SAMPLE_AGE_MS + 60 * 1000
        sample = self._sample_at(BASE_TIME_MS - age_ms)
        self.assertTrue(hub_usage.is_usage_sample_expired(sample, BASE_TIME_MS))

    def test_case17_future_timestamp_clock_skew_is_not_expired(self) -> None:
        sample = self._sample_at(BASE_TIME_MS + 60_000)
        self.assertFalse(hub_usage.is_usage_sample_expired(sample, BASE_TIME_MS))


RATE_LIMIT_CAPTURED_AT_MS = 1_786_433_120_000
RATE_LIMIT_CAPTURED_AT_S = RATE_LIMIT_CAPTURED_AT_MS // 1000


def _resets_at_s(hours_from_capture: float) -> int:
    return RATE_LIMIT_CAPTURED_AT_S + int(hours_from_capture * 3600)


def _window(used_percentage=None, resets_at=None) -> dict:
    window: dict = {}
    if used_percentage is not None:
        window["used_percentage"] = used_percentage
    if resets_at is not None:
        window["resets_at"] = resets_at
    return window


def _stdin_text(five_hour: dict | None = None, seven_day: dict | None = None) -> str:
    rate_limits = {}
    if five_hour is not None:
        rate_limits["five_hour"] = five_hour
    if seven_day is not None:
        rate_limits["seven_day"] = seven_day
    return json.dumps({"rate_limits": rate_limits})


class ParseStatusLineRateLimitsTest(unittest.TestCase):
    """케이스 N1~N10 — statusLine stdin JSON → RateLimitCapture(리셋 2개 + 퍼센트 2개)."""

    def test_n1_both_windows_normal_maps_floored_percent_and_resets_ms(self) -> None:
        session_s = _resets_at_s(2)
        weekly_s = _resets_at_s(48)
        text = _stdin_text(
            _window(used_percentage=23.5, resets_at=session_s),
            _window(used_percentage=41, resets_at=weekly_s),
        )
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertEqual(
            result,
            hub_usage.RateLimitCapture(
                captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS,
                session_resets_at_ms=session_s * 1000,
                weekly_resets_at_ms=weekly_s * 1000,
                session_used_percent=23,
                weekly_used_percent=41,
            ),
        )

    def test_n2_only_five_hour_present_leaves_weekly_none(self) -> None:
        text = _stdin_text(_window(used_percentage=10, resets_at=_resets_at_s(2)))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertEqual(result.session_used_percent, 10)
        self.assertIsNotNone(result.session_resets_at_ms)
        self.assertIsNone(result.weekly_used_percent)
        self.assertIsNone(result.weekly_resets_at_ms)

    def test_n3_resets_at_only_without_used_percentage_keeps_old_behavior(self) -> None:
        text = _stdin_text(_window(resets_at=_resets_at_s(2)))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNotNone(result.session_resets_at_ms)
        self.assertIsNone(result.session_used_percent)

    def test_n4_used_percentage_only_without_resets_at_still_builds_capture(self) -> None:
        """유효성 규칙 변경의 핵심(결정 P2) — 퍼센트만 있어도 캡처가 만들어진다."""
        text = _stdin_text(_window(used_percentage=10))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNotNone(result)
        self.assertEqual(result.session_used_percent, 10)
        self.assertIsNone(result.session_resets_at_ms)

    def test_n5_used_percentage_bool_is_dropped_field_only(self) -> None:
        text = _stdin_text(
            _window(used_percentage=True, resets_at=_resets_at_s(2)),
            _window(used_percentage=41),
        )
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)
        self.assertEqual(result.weekly_used_percent, 41)

    def test_n5_used_percentage_string_is_dropped_field_only(self) -> None:
        text = _stdin_text(_window(used_percentage="23", resets_at=_resets_at_s(2)))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_n6_used_percentage_over_100_is_dropped_field_only(self) -> None:
        text = _stdin_text(_window(used_percentage=101, resets_at=_resets_at_s(2)))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_n6_used_percentage_below_zero_is_dropped_field_only(self) -> None:
        text = _stdin_text(_window(used_percentage=-1, resets_at=_resets_at_s(2)))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_n7_used_percentage_boundary_zero_and_hundred_are_accepted(self) -> None:
        text = _stdin_text(_window(used_percentage=0), _window(used_percentage=100))
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertEqual(result.session_used_percent, 0)
        self.assertEqual(result.weekly_used_percent, 100)

    def test_n8_rate_limits_key_absent_is_normal_payload(self) -> None:
        text = json.dumps({"hookEventName": "Status"})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_n9_all_four_values_invalid_returns_none(self) -> None:
        text = _stdin_text(_window(used_percentage=True, resets_at="bad"))
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_n10_broken_json_does_not_raise(self) -> None:
        self.assertIsNone(hub_usage.parse_status_line_rate_limits("{not json", RATE_LIMIT_CAPTURED_AT_MS))

    def test_n10_empty_string_does_not_raise(self) -> None:
        self.assertIsNone(hub_usage.parse_status_line_rate_limits("", RATE_LIMIT_CAPTURED_AT_MS))


class DropPassedResetsTest(unittest.TestCase):
    """케이스 R10~R12 — 함수 시그니처·의미 불변, 그대로 유지."""

    def _resets(self, session_resets_at_ms, weekly_resets_at_ms) -> hub_usage.RateLimitResets:
        return hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS,
            session_resets_at_ms=session_resets_at_ms,
            weekly_resets_at_ms=weekly_resets_at_ms,
        )

    def test_r10_only_session_passed_keeps_weekly_original_unchanged(self) -> None:
        now_ms = RATE_LIMIT_CAPTURED_AT_MS + 10_000
        original = self._resets(session_resets_at_ms=now_ms - 1, weekly_resets_at_ms=now_ms + 10_000)
        result = hub_usage.drop_passed_resets(original, now_ms)
        self.assertEqual(result, self._resets(session_resets_at_ms=None, weekly_resets_at_ms=now_ms + 10_000))
        self.assertEqual(original.session_resets_at_ms, now_ms - 1)  # 원본 불변

    def test_r11_both_passed_returns_none(self) -> None:
        now_ms = RATE_LIMIT_CAPTURED_AT_MS + 10_000
        original = self._resets(session_resets_at_ms=now_ms - 1, weekly_resets_at_ms=now_ms - 1)
        self.assertIsNone(hub_usage.drop_passed_resets(original, now_ms))

    def test_r12_now_equals_session_resets_at_is_treated_as_passed(self) -> None:
        now_ms = RATE_LIMIT_CAPTURED_AT_MS + 10_000
        original = self._resets(session_resets_at_ms=now_ms, weekly_resets_at_ms=now_ms + 10_000)
        result = hub_usage.drop_passed_resets(original, now_ms)
        self.assertIsNone(result.session_resets_at_ms)


def _capture(
    captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS,
    session_resets_at_ms=None,
    weekly_resets_at_ms=None,
    session_used_percent=None,
    weekly_used_percent=None,
) -> hub_usage.RateLimitCapture:
    return hub_usage.RateLimitCapture(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
        session_used_percent=session_used_percent,
        weekly_used_percent=weekly_used_percent,
    )


class SameCaptureValuesTest(unittest.TestCase):
    """케이스 N23~N24 (구 SameResetTimesTest, R13). 캡처 시각을 뺀 네 값 비교로 확장(결정 P4)."""

    def test_n23_only_captured_at_differs_is_still_same(self) -> None:
        previous = _capture(session_resets_at_ms=1, weekly_resets_at_ms=2, session_used_percent=23, weekly_used_percent=41)
        current = _capture(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS + 5000,
            session_resets_at_ms=1, weekly_resets_at_ms=2, session_used_percent=23, weekly_used_percent=41,
        )
        self.assertTrue(hub_usage.same_capture_values(previous, current))

    def test_n24_differing_session_percent_is_not_same(self) -> None:
        previous = _capture(session_used_percent=23, weekly_used_percent=41)
        current = _capture(session_used_percent=24, weekly_used_percent=41)
        self.assertFalse(hub_usage.same_capture_values(previous, current))

    def test_n24_differing_reset_time_is_not_same(self) -> None:
        previous = _capture(session_resets_at_ms=1, weekly_resets_at_ms=2)
        current = _capture(session_resets_at_ms=1, weekly_resets_at_ms=3)
        self.assertFalse(hub_usage.same_capture_values(previous, current))

    def test_n24_previous_none_is_not_same(self) -> None:
        current = _capture(session_resets_at_ms=1, weekly_resets_at_ms=2)
        self.assertFalse(hub_usage.same_capture_values(None, current))


class ParseRateLimitCaptureTest(unittest.TestCase):
    """케이스 N11~N17 (구 R14) — 캡처 파일(신형 5필드, 구형 3필드 하위 호환) 되읽기."""

    def test_n11_round_trip_via_asdict_and_json(self) -> None:
        original = _capture(
            session_resets_at_ms=1, weekly_resets_at_ms=2, session_used_percent=23, weekly_used_percent=41
        )
        text = json.dumps(dataclasses.asdict(original))
        self.assertEqual(hub_usage.parse_rate_limit_capture(text), original)

    def test_n12_legacy_three_field_file_has_percent_none(self) -> None:
        """하위 호환의 핵심 — 퍼센트 키 자체가 없는 구형 파일도 정상 캡처로 파싱된다."""
        text = json.dumps(
            {"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS, "session_resets_at_ms": 1, "weekly_resets_at_ms": 2}
        )
        result = hub_usage.parse_rate_limit_capture(text)
        self.assertEqual(
            result, _capture(session_resets_at_ms=1, weekly_resets_at_ms=2, session_used_percent=None, weekly_used_percent=None)
        )

    def test_n13_percent_only_without_resets_is_normal_capture(self) -> None:
        text = json.dumps(
            {"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS, "session_used_percent": 23, "weekly_used_percent": 41}
        )
        result = hub_usage.parse_rate_limit_capture(text)
        self.assertEqual(result, _capture(session_used_percent=23, weekly_used_percent=41))

    def test_n14_percent_stored_as_float_drops_that_field_only(self) -> None:
        """파일 경로는 엄격 int(`_is_valid_percent`) — 실수는 그 필드만 None."""
        text = json.dumps(
            {
                "captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS,
                "session_resets_at_ms": 1,
                "session_used_percent": 23.5,
                "weekly_used_percent": 41,
            }
        )
        result = hub_usage.parse_rate_limit_capture(text)
        self.assertIsNone(result.session_used_percent)
        self.assertEqual(result.weekly_used_percent, 41)

    def test_n15_captured_at_ms_missing_returns_none(self) -> None:
        text = json.dumps({"session_used_percent": 23})
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_n15_captured_at_ms_as_string_returns_none(self) -> None:
        text = json.dumps({"captured_at_ms": str(RATE_LIMIT_CAPTURED_AT_MS), "session_used_percent": 23})
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_n16_all_four_values_missing_returns_none(self) -> None:
        text = json.dumps({"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS})
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_n17_extra_keys_are_ignored_upward_compat(self) -> None:
        text = json.dumps(
            {
                "captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS,
                "session_used_percent": 23,
                "weekly_used_percent": 41,
                "future_field": "should be ignored",
            }
        )
        result = hub_usage.parse_rate_limit_capture(text)
        self.assertEqual(result, _capture(session_used_percent=23, weekly_used_percent=41))

    def test_wrong_type_reset_field_returns_none(self) -> None:
        """리셋 필드는 타입이 안 맞으면(퍼센트와 달리) 레코드 전체가 무효다 — 기존 규칙 보존."""
        text = json.dumps(
            {"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS, "session_resets_at_ms": "not-an-int", "weekly_resets_at_ms": None}
        )
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_broken_json_returns_none(self) -> None:
        self.assertIsNone(hub_usage.parse_rate_limit_capture("{not json"))


class UsageSampleFromCaptureTest(unittest.TestCase):
    """케이스 N18~N19."""

    def test_n18_both_percents_present_projects_usage_sample(self) -> None:
        capture = _capture(session_used_percent=23, weekly_used_percent=41)
        self.assertEqual(
            hub_usage.usage_sample_from_capture(capture),
            hub_usage.UsageSample(sampled_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_percent=23, weekly_percent=41),
        )

    def test_n19_only_one_percent_present_is_none(self) -> None:
        capture = _capture(session_used_percent=23)
        self.assertIsNone(hub_usage.usage_sample_from_capture(capture))

    def test_n19_both_percents_absent_is_none(self) -> None:
        capture = _capture(session_resets_at_ms=1)
        self.assertIsNone(hub_usage.usage_sample_from_capture(capture))


class ResetsFromCaptureTest(unittest.TestCase):
    """케이스 N20~N21."""

    def test_n20_only_session_reset_present_projects_that_field_only(self) -> None:
        capture = _capture(session_resets_at_ms=1)
        result = hub_usage.resets_from_capture(capture)
        self.assertEqual(
            result,
            hub_usage.RateLimitResets(
                captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=None
            ),
        )

    def test_n21_both_resets_absent_is_none(self) -> None:
        capture = _capture(session_used_percent=23)
        self.assertIsNone(hub_usage.resets_from_capture(capture))


class IsSessionWindowRolledOverTest(unittest.TestCase):
    """케이스 N22."""

    def test_n22_reset_in_the_past_is_rolled_over(self) -> None:
        capture = _capture(session_resets_at_ms=RATE_LIMIT_CAPTURED_AT_MS - 1)
        self.assertTrue(hub_usage.is_session_window_rolled_over(capture, RATE_LIMIT_CAPTURED_AT_MS))

    def test_n22_reset_in_the_future_is_not_rolled_over(self) -> None:
        capture = _capture(session_resets_at_ms=RATE_LIMIT_CAPTURED_AT_MS + 1)
        self.assertFalse(hub_usage.is_session_window_rolled_over(capture, RATE_LIMIT_CAPTURED_AT_MS))

    def test_n22_unknown_reset_is_not_treated_as_rolled_over(self) -> None:
        capture = _capture(session_used_percent=23)
        self.assertFalse(hub_usage.is_session_window_rolled_over(capture, RATE_LIMIT_CAPTURED_AT_MS))


class FormatStatusLineSummaryTest(unittest.TestCase):
    """케이스 N25~N26 — 인자가 텍스트에서 캡처로 바뀐 버전."""

    def test_n25_both_percents_present(self) -> None:
        capture = _capture(session_used_percent=23, weekly_used_percent=41)
        self.assertEqual(hub_usage.format_status_line_summary(capture), "세션 23% · 주간 41%")

    def test_n26_only_session_percent_present(self) -> None:
        capture = _capture(session_used_percent=23)
        self.assertEqual(hub_usage.format_status_line_summary(capture), "세션 23%")

    def test_n26_no_percent_present(self) -> None:
        capture = _capture(session_resets_at_ms=1)
        self.assertEqual(hub_usage.format_status_line_summary(capture), "")

    def test_n26_capture_none(self) -> None:
        self.assertEqual(hub_usage.format_status_line_summary(None), "")


if __name__ == "__main__":
    unittest.main()
