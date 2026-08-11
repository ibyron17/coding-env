"""hub_usage.py — Claude 데스크톱 앱의 비공개 사용량 히스토리 포맷을 읽는 순수 파서.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_usage.py 대상).
`plan-usage-history.json` 은 우리가 만들지 않는 앱의 비문서 포맷이라 `hub_parse.py`(/dashboard
DOM 파서)와 같은 성격이다 — 계약이 안 맞으면 예외가 아니라 None 을 돌려주고, 호출자
(hub_collect.py)가 그 실패를 흡수한다. 설계 근거는
docs/prps/hub-theme-and-usage-panel.md 결정 M1·U1~U3 이 정본이다.
"""

import json
from dataclasses import dataclass

USAGE_SESSION_WINDOW_HOURS = 5          # u.fh 가 재는 창의 길이. 만료 기준의 근거(결정 U3)
MILLISECONDS_PER_HOUR = 60 * 60 * 1000
USAGE_MAX_SAMPLE_AGE_MS = USAGE_SESSION_WINDOW_HOURS * MILLISECONDS_PER_HOUR
USAGE_PERCENT_MIN = 0
USAGE_PERCENT_MAX = 100


@dataclass(frozen=True)
class UsageSample:
    """plan-usage-history.json 의 마지막 샘플 — 세션(5시간)·주간(7일) 한도 사용률."""

    sampled_at_ms: int      # 원본 t. 파생값(나이)은 담지 않는다 — content_key 재작성 폭주 방지(결정 D3)
    session_percent: int    # 원본 u.fh (0~100)
    weekly_percent: int     # 원본 u.sd (0~100)


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
