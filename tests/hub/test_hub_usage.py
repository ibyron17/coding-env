"""hub_usage 단위 테스트. docs/prps/hub-theme-and-usage-panel.md 「테스트 계획」 케이스 1~17 +
docs/prps/hub-usage-reset-time-and-refresh.md 「테스트 계획」 케이스 R1~R14b."""

import dataclasses
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_usage  # noqa: E402  (sys.path 조정 후 임포트)

BASE_TIME_MS = 1_786_433_123_899


def _history_text(samples: list) -> str:
    return json.dumps({"version": 2, "samples": samples})


def _sample(t=BASE_TIME_MS, fh=10, sd=19, **overrides) -> dict:
    payload = {"t": t, "org": "c2af3bdd-…", "u": {"fh": fh, "sd": sd}}
    payload.update(overrides)
    return payload


class ParseUsageHistoryTest(unittest.TestCase):
    """케이스 1~13."""

    def test_case1_last_of_three_samples_is_mapped(self) -> None:
        samples = [_sample(t=1, fh=1, sd=1), _sample(t=2, fh=2, sd=2), _sample(t=3, fh=10, sd=19)]
        result = hub_usage.parse_usage_history(_history_text(samples))
        self.assertEqual(result, hub_usage.UsageSample(sampled_at_ms=3, session_percent=10, weekly_percent=19))

    def test_case_m5_boundary_values_zero_and_hundred_are_accepted(self) -> None:
        """검수 m5 — 0·100 경계값이 허용되는지 확인한다. 기존 픽스처가 전부 fh=10,sd=19 라
        `_is_valid_percent` 가 `0 < v < 100` 으로(양끝 배제) 잘못 바뀌어도 다른 테스트가
        전부 통과했다. fh:0 은 세션 시작 직후 가장 흔한 값이고 100 은 한도 도달 순간이다."""
        samples = [_sample(fh=0, sd=100)]
        result = hub_usage.parse_usage_history(_history_text(samples))
        self.assertEqual(
            result, hub_usage.UsageSample(sampled_at_ms=BASE_TIME_MS, session_percent=0, weekly_percent=100)
        )

    def test_case2_empty_samples_list(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history(_history_text([])))

    def test_case3_samples_key_missing(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history(json.dumps({"version": 2})))

    def test_case4_top_level_is_array(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history(json.dumps([_sample()])))

    def test_case4_top_level_is_string(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history(json.dumps("not an object")))

    def test_case5_broken_json_does_not_raise(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history("{not json"))

    def test_case6_empty_string(self) -> None:
        self.assertIsNone(hub_usage.parse_usage_history(""))

    def test_case7_last_sample_missing_fh(self) -> None:
        samples = [_sample(), {"t": BASE_TIME_MS, "u": {"xu": 5}}]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case8_fh_as_float_scale_change_is_rejected(self) -> None:
        """U2 회귀 방지의 핵심 — 실수 스케일로 바뀌면 조용히 통과시키지 않는다."""
        samples = [_sample(fh=0.87)]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case9_fh_as_bool_is_rejected(self) -> None:
        samples = [_sample(fh=True)]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case10_fh_over_100_is_rejected(self) -> None:
        samples = [_sample(fh=101)]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case10_sd_below_zero_is_rejected(self) -> None:
        samples = [_sample(sd=-1)]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case11_t_as_string_is_rejected(self) -> None:
        samples = [_sample(t=str(BASE_TIME_MS))]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))

    def test_case12_version_3_with_unchanged_shape_still_parses(self) -> None:
        """버전 게이트 부재 회귀 방지 — version 필드는 검사하지 않는다."""
        payload = {"version": 3, "samples": [_sample(t=5, fh=7, sd=8)]}
        result = hub_usage.parse_usage_history(json.dumps(payload))
        self.assertEqual(result, hub_usage.UsageSample(sampled_at_ms=5, session_percent=7, weekly_percent=8))

    def test_case13_u_is_not_a_dict(self) -> None:
        samples = [{"t": BASE_TIME_MS, "u": [1, 2]}]
        self.assertIsNone(hub_usage.parse_usage_history(_history_text(samples)))


class IsUsageSampleExpiredTest(unittest.TestCase):
    """케이스 14~17."""

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


class ParseStatusLineRateLimitsTest(unittest.TestCase):
    """케이스 R1~R9."""

    def test_r1_both_windows_present_are_mapped_to_ms(self) -> None:
        session_s = _resets_at_s(2)
        weekly_s = _resets_at_s(48)
        text = json.dumps(
            {"rate_limits": {"five_hour": {"resets_at": session_s}, "seven_day": {"resets_at": weekly_s}}}
        )
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertEqual(
            result,
            hub_usage.RateLimitResets(
                captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS,
                session_resets_at_ms=session_s * 1000,
                weekly_resets_at_ms=weekly_s * 1000,
            ),
        )

    def test_r2_only_five_hour_present(self) -> None:
        text = json.dumps({"rate_limits": {"five_hour": {"resets_at": _resets_at_s(2)}}})
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.weekly_resets_at_ms)
        self.assertIsNotNone(result.session_resets_at_ms)

    def test_r3_only_seven_day_present(self) -> None:
        text = json.dumps({"rate_limits": {"seven_day": {"resets_at": _resets_at_s(48)}}})
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_resets_at_ms)
        self.assertIsNotNone(result.weekly_resets_at_ms)

    def test_r4_rate_limits_key_absent_is_normal_payload(self) -> None:
        text = json.dumps({"hookEventName": "Status"})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r5_rate_limits_not_a_dict(self) -> None:
        text = json.dumps({"rate_limits": "not-a-dict"})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r5_window_not_a_dict(self) -> None:
        text = json.dumps({"rate_limits": {"five_hour": "not-a-dict", "seven_day": "not-a-dict"}})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r6_resets_at_as_string_that_window_is_dropped(self) -> None:
        text = json.dumps(
            {
                "rate_limits": {
                    "five_hour": {"resets_at": str(_resets_at_s(2))},
                    "seven_day": {"resets_at": _resets_at_s(48)},
                }
            }
        )
        result = hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS)
        self.assertIsNone(result.session_resets_at_ms)
        self.assertIsNotNone(result.weekly_resets_at_ms)

    def test_r6_resets_at_as_float_and_bool_both_windows_dropped_is_none(self) -> None:
        text = json.dumps(
            {"rate_limits": {"five_hour": {"resets_at": 1.5}, "seven_day": {"resets_at": True}}}
        )
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r7_resets_at_already_in_ms_is_rejected_by_horizon_check(self) -> None:
        """단위 오류 시뮬레이션 — 이미 ms 인 값을 다시 ×1000 하면 지평선을 아득히 벗어난다."""
        text = json.dumps({"rate_limits": {"five_hour": {"resets_at": RATE_LIMIT_CAPTURED_AT_MS + 3600_000}}})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r8_resets_at_in_the_past_is_dropped(self) -> None:
        text = json.dumps({"rate_limits": {"five_hour": {"resets_at": _resets_at_s(-1)}}})
        self.assertIsNone(hub_usage.parse_status_line_rate_limits(text, RATE_LIMIT_CAPTURED_AT_MS))

    def test_r9_broken_json_does_not_raise(self) -> None:
        self.assertIsNone(hub_usage.parse_status_line_rate_limits("{not json", RATE_LIMIT_CAPTURED_AT_MS))

    def test_r9_empty_string(self) -> None:
        self.assertIsNone(hub_usage.parse_status_line_rate_limits("", RATE_LIMIT_CAPTURED_AT_MS))


class DropPassedResetsTest(unittest.TestCase):
    """케이스 R10~R12."""

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


class SameResetTimesTest(unittest.TestCase):
    """케이스 R13."""

    def test_r13_only_captured_at_differs_is_still_same(self) -> None:
        previous = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=2
        )
        current = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS + 5000, session_resets_at_ms=1, weekly_resets_at_ms=2
        )
        self.assertTrue(hub_usage.same_reset_times(previous, current))

    def test_r13_previous_none_is_not_same(self) -> None:
        current = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=2
        )
        self.assertFalse(hub_usage.same_reset_times(None, current))

    def test_r13_differing_reset_time_is_not_same(self) -> None:
        previous = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=2
        )
        current = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=3
        )
        self.assertFalse(hub_usage.same_reset_times(previous, current))


class ParseRateLimitCaptureTest(unittest.TestCase):
    """케이스 R14."""

    def test_r14_round_trip_via_asdict_and_json(self) -> None:
        original = hub_usage.RateLimitResets(
            captured_at_ms=RATE_LIMIT_CAPTURED_AT_MS, session_resets_at_ms=1, weekly_resets_at_ms=2
        )
        text = json.dumps(dataclasses.asdict(original))
        self.assertEqual(hub_usage.parse_rate_limit_capture(text), original)

    def test_r14_missing_field_returns_none(self) -> None:
        text = json.dumps({"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS})
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_r14_wrong_type_field_returns_none(self) -> None:
        text = json.dumps(
            {"captured_at_ms": RATE_LIMIT_CAPTURED_AT_MS, "session_resets_at_ms": "not-an-int", "weekly_resets_at_ms": None}
        )
        self.assertIsNone(hub_usage.parse_rate_limit_capture(text))

    def test_r14_broken_json_returns_none(self) -> None:
        self.assertIsNone(hub_usage.parse_rate_limit_capture("{not json"))


class FormatStatusLineSummaryTest(unittest.TestCase):
    """케이스 R14b."""

    def test_r14b_float_and_int_used_percentage_are_floored(self) -> None:
        text = json.dumps(
            {"rate_limits": {"five_hour": {"used_percentage": 23.5}, "seven_day": {"used_percentage": 41}}}
        )
        self.assertEqual(hub_usage.format_status_line_summary(text), "세션 23% · 주간 41%")

    def test_r14b_no_rate_limits_returns_empty_string(self) -> None:
        self.assertEqual(hub_usage.format_status_line_summary(json.dumps({"hookEventName": "Status"})), "")

    def test_r14b_broken_json_returns_empty_string(self) -> None:
        self.assertEqual(hub_usage.format_status_line_summary("{not json"), "")


if __name__ == "__main__":
    unittest.main()
