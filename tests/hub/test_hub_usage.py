"""hub_usage 단위 테스트. docs/prps/hub-theme-and-usage-panel.md 「테스트 계획」 케이스 1~17."""

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


if __name__ == "__main__":
    unittest.main()
