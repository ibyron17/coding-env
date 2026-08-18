"""hub_usage 단위 테스트. docs/prps/hub-usage-reset-time-and-refresh.md 「테스트 계획」
케이스 R10~R12(변경 없는 함수) + docs/prps/hub-card-cleanup-and-usage-source.md 「테스트 계획」
케이스 N1~N26(캡처 단일 출처로 교체된 함수들)."""

import dataclasses
import json
import os
import sys
import unittest
from datetime import datetime, timezone

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


class MarkStaleUsageSampleTest(unittest.TestCase):
    """신규(R-B) — mark_stale_usage_sample. 나이(U3)·롤오버(P5) 두 판정을 OR 로 접어
    is_stale 하나로 표시한다(결정 EX2·EX5). is_usage_sample_expired·is_session_window_rolled_over
    자체는 무변경이라 그 단위 테스트(case14~17·n22)도 그대로 통과한다."""

    def _sample_at(self, sampled_at_ms: int) -> hub_usage.UsageSample:
        return hub_usage.UsageSample(sampled_at_ms=sampled_at_ms, session_percent=10, weekly_percent=19)

    def test_u1_age_four_hours_fifty_nine_minutes_returns_original_object_unchanged(self) -> None:
        age_ms = (4 * 60 + 59) * 60 * 1000
        sample = self._sample_at(BASE_TIME_MS - age_ms)
        result = hub_usage.mark_stale_usage_sample(sample, _capture(), BASE_TIME_MS)
        self.assertFalse(result.is_stale)
        self.assertIs(result, sample)  # 불필요한 복제 없음

    def test_u2_age_exactly_five_hours_is_stale_boundary_inclusive(self) -> None:
        sample = self._sample_at(BASE_TIME_MS - hub_usage.USAGE_MAX_SAMPLE_AGE_MS)
        result = hub_usage.mark_stale_usage_sample(sample, _capture(), BASE_TIME_MS)
        self.assertTrue(result.is_stale)

    def test_u3_age_five_hours_one_minute_is_stale(self) -> None:
        age_ms = hub_usage.USAGE_MAX_SAMPLE_AGE_MS + 60 * 1000
        sample = self._sample_at(BASE_TIME_MS - age_ms)
        result = hub_usage.mark_stale_usage_sample(sample, _capture(), BASE_TIME_MS)
        self.assertTrue(result.is_stale)

    def test_u4_fresh_age_but_session_reset_already_passed_is_stale(self) -> None:
        """롤오버 단독 사유(결정 EX2) — 나이는 1분뿐이어도 세션 리셋이 이미 지났으면 낡음이다."""
        sample = self._sample_at(BASE_TIME_MS - 60_000)
        capture = _capture(session_resets_at_ms=BASE_TIME_MS - 1)
        result = hub_usage.mark_stale_usage_sample(sample, capture, BASE_TIME_MS)
        self.assertTrue(result.is_stale)

    def test_u5_fresh_and_unknown_session_reset_is_not_stale(self) -> None:
        """기존 n22 규칙 재확인 — 모름(None)을 롤오버로 단정하지 않는다."""
        sample = self._sample_at(BASE_TIME_MS - 60_000)
        result = hub_usage.mark_stale_usage_sample(sample, _capture(session_resets_at_ms=None), BASE_TIME_MS)
        self.assertFalse(result.is_stale)

    def test_u6_clock_skew_future_timestamp_is_not_stale(self) -> None:
        sample = self._sample_at(BASE_TIME_MS + 60_000)
        result = hub_usage.mark_stale_usage_sample(sample, _capture(), BASE_TIME_MS)
        self.assertFalse(result.is_stale)

    def test_u7_original_sample_is_not_mutated(self) -> None:
        sample = self._sample_at(BASE_TIME_MS - hub_usage.USAGE_MAX_SAMPLE_AGE_MS)
        hub_usage.mark_stale_usage_sample(sample, _capture(), BASE_TIME_MS)
        self.assertFalse(sample.is_stale)  # frozen + replace 가 새 객체를 만든다


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


def _resets_at_iso(hours_from_capture: float) -> str:
    """RATE_LIMIT_CAPTURED_AT_MS 로부터 hours_from_capture 시간 뒤의 ISO 8601(UTC) 문자열."""
    epoch_seconds = _resets_at_s(hours_from_capture)
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _usage_api_window(utilization=None, resets_at=None) -> dict:
    window: dict = {}
    if utilization is not None:
        window["utilization"] = utilization
    if resets_at is not None:
        window["resets_at"] = resets_at
    return window


def _usage_api_text(five_hour: dict | None = None, seven_day: dict | None = None) -> str:
    payload: dict = {}
    if five_hour is not None:
        payload["five_hour"] = five_hour
    if seven_day is not None:
        payload["seven_day"] = seven_day
    return json.dumps(payload)


class ParseUsageApiResponseTest(unittest.TestCase):
    """U21~U25 — usage API 1차 대응표(SP3 생략 개정: five_hour/seven_day.utilization/resets_at)."""

    def test_u21_normal_response_maps_all_four_values(self) -> None:
        text = _usage_api_text(
            _usage_api_window(utilization=23.5, resets_at=_resets_at_iso(2)),
            _usage_api_window(utilization=41, resets_at=_resets_at_iso(48)),
        )
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertEqual(result.session_used_percent, 23)
        self.assertEqual(result.weekly_used_percent, 41)
        self.assertIsNotNone(result.session_resets_at_ms)
        self.assertIsNotNone(result.weekly_resets_at_ms)

    def test_u22_broken_json_returns_none(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_api_response("{not json", RATE_LIMIT_CAPTURED_AT_MS))

    def test_u22_top_level_array_returns_none(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_api_response("[1, 2, 3]", RATE_LIMIT_CAPTURED_AT_MS))

    def test_u22_all_fields_missing_returns_none(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_api_response("{}", RATE_LIMIT_CAPTURED_AT_MS))

    def test_u23_percentage_as_string_drops_that_field_only(self) -> None:
        text = _usage_api_text(
            _usage_api_window(utilization="23", resets_at=_resets_at_iso(2)),
            _usage_api_window(utilization=41),
        )
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)
        self.assertEqual(result.weekly_used_percent, 41)

    def test_u23_percentage_as_bool_drops_that_field_only(self) -> None:
        text = _usage_api_text(_usage_api_window(utilization=True, resets_at=_resets_at_iso(2)))
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_u23_percentage_out_of_range_drops_that_field_only(self) -> None:
        text = _usage_api_text(_usage_api_window(utilization=101, resets_at=_resets_at_iso(2)))
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_used_percent)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_u24_resets_at_beyond_horizon_drops_that_window_only(self) -> None:
        """단위 혼동(초/밀리초 등) 검출과 같은 지평선 검사를 ISO 8601 경로에도 적용한다."""
        far_future_iso = _resets_at_iso(24 * 30)  # 30일 뒤 — RATE_LIMIT_MAX_HORIZON_DAYS(8일) 밖
        text = _usage_api_text(_usage_api_window(utilization=23, resets_at=far_future_iso))
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_resets_at_ms)
        self.assertEqual(result.session_used_percent, 23)

    def test_u24_malformed_resets_at_string_drops_that_window_only(self) -> None:
        text = _usage_api_text(_usage_api_window(utilization=23, resets_at="not-a-date"))
        result = hub_usage.parse_usage_api_response(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_resets_at_ms)
        self.assertEqual(result.session_used_percent, 23)

    def test_u25_never_raises_on_any_input(self) -> None:
        malformed_inputs = (
            "",
            "null",
            "42",
            '{"five_hour": "not-a-dict"}',
            '{"five_hour": {"utilization": null}}',
            '{"five_hour": {"utilization": NaN}}',
            '{"five_hour": {"resets_at": 12345}}',
            '{"five_hour": {"resets_at": "9999-99-99T99:99:99"}}',
            '{"five_hour": {"utilization": [1, 2, 3]}}',
        )
        for malformed_text in malformed_inputs:
            with self.subTest(text=malformed_text):
                try:
                    hub_usage.parse_usage_api_response(malformed_text, RATE_LIMIT_CAPTURED_AT_MS)
                except Exception as error:  # noqa: BLE001 -- 이 테스트 자체가 "예외 없음"을 검증한다
                    self.fail(f"parse_usage_api_response 가 예외를 던짐: {error!r}")


class DescribeJsonKeyStructureTest(unittest.TestCase):
    """schema_mismatch 자기 진단(SP3 생략 개정) — 키 경로+타입만 담고 값은 절대 포함하지
    않는다(불변식 A-SEC)."""

    def test_values_never_appear_in_the_output(self) -> None:
        secret_looking_value = "sk-ant-should-never-leak-1234567890"
        text = json.dumps({"token": secret_looking_value, "nested": {"count": 42}, "list": ["x", "y"]})
        described = hub_usage.describe_json_key_structure(text)
        self.assertIsNotNone(described)
        joined = " ".join(described)
        self.assertNotIn(secret_looking_value, joined)
        self.assertNotIn("42", joined)  # 값(int) 도 새어나오지 않는다 — 타입만 남는다
        self.assertIn("/token <str>", described)
        self.assertIn("/nested/count <int>", described)
        self.assertIn("/list [list len=2]", described)

    def test_broken_json_returns_none(self) -> None:
        self.assertIsNone(hub_usage.describe_json_key_structure("{not json"))

    def test_scalar_root_returns_type_only(self) -> None:
        self.assertEqual(hub_usage.describe_json_key_structure("42"), [" <int>"])


class ShouldAttemptUsageApiPollTest(unittest.TestCase):
    """U7~U8 — 첫 시도는 항상 True, 이후로는 주기 도달 여부로 판정한다(결정 A3)."""

    BASE_INTERVAL_SECONDS = 300

    def test_u7_first_attempt_is_always_true(self) -> None:
        state = hub_usage.UsageApiPollState()
        self.assertTrue(
            hub_usage.should_attempt_usage_api_poll(BASE_TIME_MS, state, self.BASE_INTERVAL_SECONDS)
        )

    def test_u8_before_delay_elapses_is_false(self) -> None:
        state = hub_usage.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        almost_five_minutes_ms = 5 * 60 * 1000 - 1
        self.assertFalse(
            hub_usage.should_attempt_usage_api_poll(
                BASE_TIME_MS + almost_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )

    def test_u8_exactly_at_delay_is_true(self) -> None:
        state = hub_usage.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        exactly_five_minutes_ms = 5 * 60 * 1000
        self.assertTrue(
            hub_usage.should_attempt_usage_api_poll(
                BASE_TIME_MS + exactly_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )

    def test_u8_past_delay_is_true(self) -> None:
        state = hub_usage.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        past_five_minutes_ms = 5 * 60 * 1000 + 1
        self.assertTrue(
            hub_usage.should_attempt_usage_api_poll(
                BASE_TIME_MS + past_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )


class UsageApiPollDelayMsTest(unittest.TestCase):
    """U9~U11 — 연속 실패마다 지연이 2배씩 늘고 상한(60분)에서 멈춘다. 429 는 즉시 상한(결정 A3)."""

    BASE_INTERVAL_SECONDS = 300  # 5분
    ONE_MINUTE_MS = 60 * 1000

    def _delay_minutes(self, consecutive_failures: int, forced_multiplier: int | None = None) -> float:
        state = hub_usage.UsageApiPollState(
            consecutive_failures=consecutive_failures, forced_multiplier=forced_multiplier
        )
        return hub_usage.usage_api_poll_delay_ms(state, self.BASE_INTERVAL_SECONDS) / self.ONE_MINUTE_MS

    def test_u9_delay_doubles_per_consecutive_failure_up_to_the_cap(self) -> None:
        self.assertEqual(self._delay_minutes(1), 5)
        self.assertEqual(self._delay_minutes(2), 10)
        self.assertEqual(self._delay_minutes(3), 20)
        self.assertEqual(self._delay_minutes(4), 40)
        self.assertEqual(self._delay_minutes(5), 60)

    def test_u9_delay_stays_capped_beyond_the_fifth_failure(self) -> None:
        self.assertEqual(self._delay_minutes(6), 60)
        self.assertEqual(self._delay_minutes(20), 60)

    def test_u10_success_resets_consecutive_failures_to_zero(self) -> None:
        state = hub_usage.UsageApiPollState(consecutive_failures=4)
        next_state = hub_usage.next_usage_api_poll_state(BASE_TIME_MS, state, failure_reason=None)
        self.assertEqual(next_state.consecutive_failures, 0)
        self.assertIsNone(next_state.forced_multiplier)

    def test_u11_http_rate_limited_jumps_straight_to_the_cap(self) -> None:
        state = hub_usage.UsageApiPollState(consecutive_failures=0)
        next_state = hub_usage.next_usage_api_poll_state(BASE_TIME_MS, state, failure_reason="http_rate_limited")
        self.assertEqual(
            hub_usage.usage_api_poll_delay_ms(next_state, self.BASE_INTERVAL_SECONDS) / self.ONE_MINUTE_MS, 60
        )


class NextUsageApiPollStateTest(unittest.TestCase):
    """U12 — next_usage_api_poll_state 는 항상 새 객체를 돌려준다(원본 불변)."""

    def test_u12_returns_a_new_object_not_the_original(self) -> None:
        original = hub_usage.UsageApiPollState()
        updated = hub_usage.next_usage_api_poll_state(BASE_TIME_MS, original, failure_reason="network_error")
        self.assertIsNot(updated, original)
        self.assertEqual(original, hub_usage.UsageApiPollState())  # 원본 필드도 그대로


if __name__ == "__main__":
    unittest.main()
