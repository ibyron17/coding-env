"""hub_usage.py — 한도 관련 외부 계약 파서 모음(순수).

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_usage.py 대상).
두 종류의 외부 포맷을 다룬다 — (1) Claude 데스크톱 앱의 비공개 사용량 히스토리
(`plan-usage-history.json`, 퍼센트 출처), (2) Claude Code CLI 의 statusLine 입력 JSON과
그 캡처 파일(`rate_limits.*.resets_at`, 초기화 예정 시각 출처). 둘 다 우리가 만들지 않는
외부 포맷이라 `hub_parse.py`(/dashboard DOM 파서)와 같은 성격이다 — 계약이 안 맞으면
예외가 아니라 None 을 돌려주고, 호출자(hub_collect.py)가 그 실패를 흡수한다. 설계 근거는
docs/prps/hub-theme-and-usage-panel.md 결정 M1·U1~U3, docs/prps/hub-usage-reset-time-and-refresh.md
결정 S1~S3·R1·R2 가 정본이다.
"""

import json
import math
from dataclasses import dataclass, replace

USAGE_SESSION_WINDOW_HOURS = 5          # u.fh 가 재는 창의 길이. 만료 기준의 근거(결정 U3)
MILLISECONDS_PER_HOUR = 60 * 60 * 1000
USAGE_MAX_SAMPLE_AGE_MS = USAGE_SESSION_WINDOW_HOURS * MILLISECONDS_PER_HOUR
USAGE_PERCENT_MIN = 0
USAGE_PERCENT_MAX = 100

MILLISECONDS_PER_SECOND = 1000
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
# 리셋 시각이 캡처 시각으로부터 이 범위를 벗어나면 버린다. 목적은 '초 ↔ 밀리초' 단위 혼동을
# 잡는 것이다(단위가 틀리면 1000배 어긋나므로 임계값의 정확한 크기는 중요하지 않다).
# 8 = 가장 긴 창(7일) + 하루 여유.
RATE_LIMIT_MAX_HORIZON_DAYS = 8
RATE_LIMIT_MAX_HORIZON_MS = RATE_LIMIT_MAX_HORIZON_DAYS * MILLISECONDS_PER_DAY


@dataclass(frozen=True)
class UsageSample:
    """plan-usage-history.json 의 마지막 샘플 — 세션(5시간)·주간(7일) 한도 사용률."""

    sampled_at_ms: int      # 원본 t. 파생값(나이)은 담지 않는다 — content_key 재작성 폭주 방지(결정 D3)
    session_percent: int    # 원본 u.fh (0~100)
    weekly_percent: int     # 원본 u.sd (0~100)


@dataclass(frozen=True)
class RateLimitResets:
    """Claude Code statusLine 이 알려 준 한도 창의 초기화 예정 시각. 창은 각각 없을 수 있다."""

    captured_at_ms: int                 # 이 값들을 '처음 관측한' 시각(결정 S3 — 마지막 관측이 아니다)
    session_resets_at_ms: int | None    # rate_limits.five_hour.resets_at (초 → ms 변환됨)
    weekly_resets_at_ms: int | None     # rate_limits.seven_day.resets_at (초 → ms 변환됨)


def _is_valid_percent(value: object) -> bool:
    """0~100 범위의 엄격한 int 인가(결정 U2).

    bool 은 int 의 서브클래스라 명시적으로 배제한다. float 을 거부하는 것이 핵심이다 —
    스키마가 0~100 정수에서 0.0~1.0 실수로 바뀌면 느슨한 변환은 "0%" 를 조용히 그린다.
    그건 데이터 없음보다 나쁜 거짓말이다.
    """
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and USAGE_PERCENT_MIN <= value <= USAGE_PERCENT_MAX
    )


def _is_valid_epoch_ms(value: object) -> bool:
    """엄격한 int 인가. `t` 필드도 percent 와 같은 규칙을 쓴다 — 규칙이 하나면 설명도 테스트도 하나다."""
    return isinstance(value, int) and not isinstance(value, bool)


def parse_usage_history(text: str) -> UsageSample | None:
    """사용량 히스토리 JSON 텍스트에서 마지막 샘플을 읽는다. 계약이 안 맞으면 None.

    `samples` 의 마지막 원소만 본다(결정 U1) — 역방향 스캔은 스키마가 바뀐 신형 샘플을
    건너뛰고 몇 시간 전의 구형 샘플을 "최신인 척" 보여줄 수 있다. 마지막 원소만 보면 그
    경우 조용히 None 이 되어 패널이 사라진다 — 틀린 숫자보다 없는 숫자가 낫다.
    `version` 필드는 검사하지 않는다 — 검사는 값의 모양에만 건다.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        return None
    last_sample = samples[-1]
    if not isinstance(last_sample, dict):
        return None
    usage = last_sample.get("u")
    if not isinstance(usage, dict):
        return None
    sampled_at_ms = last_sample.get("t")
    session_percent = usage.get("fh")
    weekly_percent = usage.get("sd")
    if not (
        _is_valid_epoch_ms(sampled_at_ms)
        and _is_valid_percent(session_percent)
        and _is_valid_percent(weekly_percent)
    ):
        return None
    return UsageSample(
        sampled_at_ms=sampled_at_ms,
        session_percent=session_percent,
        weekly_percent=weekly_percent,
    )


def is_usage_sample_expired(sample: UsageSample, now_ms: int) -> bool:
    """샘플이 세션 창(5시간)보다 오래됐는가 — 그러면 세션 사용률의 근거가 사라진다(결정 U3).

    `u.fh` 는 정의상 5시간 창의 사용률이라, 창 길이가 곧 만료 기준이다. 시계가 뒤틀려
    `now_ms` 가 샘플보다 과거면(나이가 음수) 만료로 보지 않는다.
    """
    age_ms = now_ms - sample.sampled_at_ms
    return age_ms >= USAGE_MAX_SAMPLE_AGE_MS


# ---- statusLine rate_limits (docs/prps/hub-usage-reset-time-and-refresh.md) ----
def _valid_resets_at_ms(window: object, captured_at_ms: int) -> int | None:
    """rate_limits.{five_hour,seven_day} 하나를 검증해 ms 단위 리셋 시각을 돌려준다.

    엄격 int(U2 와 같은 규칙, bool 배제) + 지평선 검사(단위 혼동·과거 값을 한 번에 잡는다)를
    통과하지 못하면 그 창은 조용히 버려진다 — 두 창은 각각 독립적으로 없을 수 있다.
    """
    if not isinstance(window, dict):
        return None
    resets_at = window.get("resets_at")
    if not _is_valid_epoch_ms(resets_at):
        return None
    resets_at_ms = resets_at * MILLISECONDS_PER_SECOND
    if not (captured_at_ms < resets_at_ms <= captured_at_ms + RATE_LIMIT_MAX_HORIZON_MS):
        return None
    return resets_at_ms


def parse_status_line_rate_limits(text: str, captured_at_ms: int) -> RateLimitResets | None:
    """statusLine stdin JSON 에서 두 창의 초기화 예정 시각을 읽는다. 쓸 값이 없으면 None."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return None
    session_resets_at_ms = _valid_resets_at_ms(rate_limits.get("five_hour"), captured_at_ms)
    weekly_resets_at_ms = _valid_resets_at_ms(rate_limits.get("seven_day"), captured_at_ms)
    if session_resets_at_ms is None and weekly_resets_at_ms is None:
        return None
    return RateLimitResets(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
    )


def parse_rate_limit_capture(text: str) -> RateLimitResets | None:
    """우리가 쓴 캡처 파일을 되읽는다. 계약이 안 맞으면 None(예외를 던지지 않는다)."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    captured_at_ms = payload.get("captured_at_ms")
    session_resets_at_ms = payload.get("session_resets_at_ms")
    weekly_resets_at_ms = payload.get("weekly_resets_at_ms")
    if not _is_valid_epoch_ms(captured_at_ms):
        return None
    if session_resets_at_ms is not None and not _is_valid_epoch_ms(session_resets_at_ms):
        return None
    if weekly_resets_at_ms is not None and not _is_valid_epoch_ms(weekly_resets_at_ms):
        return None
    if session_resets_at_ms is None and weekly_resets_at_ms is None:
        return None
    return RateLimitResets(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
    )


def drop_passed_resets(resets: RateLimitResets, now_ms: int) -> RateLimitResets | None:
    """이미 지난 초기화 시각을 버린다 — 지난 값은 더 이상 참이 아니다. 둘 다 지났으면 None."""
    session_resets_at_ms = resets.session_resets_at_ms
    if session_resets_at_ms is not None and session_resets_at_ms <= now_ms:
        session_resets_at_ms = None
    weekly_resets_at_ms = resets.weekly_resets_at_ms
    if weekly_resets_at_ms is not None and weekly_resets_at_ms <= now_ms:
        weekly_resets_at_ms = None
    if session_resets_at_ms is None and weekly_resets_at_ms is None:
        return None
    return replace(
        resets, session_resets_at_ms=session_resets_at_ms, weekly_resets_at_ms=weekly_resets_at_ms
    )


def same_reset_times(previous: RateLimitResets | None, current: RateLimitResets) -> bool:
    """캡처 시각을 뺀 리셋 시각 두 개가 같은가 — 같으면 다시 쓰지 않는다(결정 S3)."""
    if previous is None:
        return False
    return (
        previous.session_resets_at_ms == current.session_resets_at_ms
        and previous.weekly_resets_at_ms == current.weekly_resets_at_ms
    )


def _valid_used_percentage(window: object) -> int | None:
    """rate_limits.{five_hour,seven_day}.used_percentage 를 검증해 내림한 정수를 돌려준다.

    실수·정수 모두 허용하되 bool 은 배제하고(U2 와 같은 정신) 0~100 범위 밖은 생략한다.
    이 값은 상태줄 출력 전용이다 — 캡처 파일에는 절대 쓰지 않는다(결정 S7).
    """
    if not isinstance(window, dict):
        return None
    value = window.get("used_percentage")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not (USAGE_PERCENT_MIN <= value <= USAGE_PERCENT_MAX):
        return None
    return math.floor(value)


def format_status_line_summary(text: str) -> str:
    """statusLine stdin JSON 으로 터미널 상태줄 한 줄을 만든다. 쓸 값이 없으면 빈 문자열."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return ""
    session_percent = _valid_used_percentage(rate_limits.get("five_hour"))
    weekly_percent = _valid_used_percentage(rate_limits.get("seven_day"))
    parts = []
    if session_percent is not None:
        parts.append(f"세션 {session_percent}%")
    if weekly_percent is not None:
        parts.append(f"주간 {weekly_percent}%")
    return " · ".join(parts)
