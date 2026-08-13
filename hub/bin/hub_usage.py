"""hub_usage.py — 한도 관련 외부 계약 파서 모음(순수).

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_usage.py 대상).
다루는 외부 포맷은 하나다 — Claude Code CLI 의 statusLine 입력 JSON과 그 캡처 파일
(`rate_limits.*.resets_at`·`rate_limits.*.used_percentage`). 초기화 예정 시각과 사용률
퍼센트 둘 다 이 캡처가 유일한 출처다(결정 P1, docs/prps/hub-card-cleanup-and-usage-source.md) —
Claude 데스크톱 앱이 남기던 비공개 사용량 히스토리 파일은 실제로 사라져 더 이상 다루지
않는다. 우리가 만들지 않는 외부 포맷이라 `hub_parse.py`(/dashboard DOM 파서)와
같은 성격이다 — 계약이 안 맞으면 예외가 아니라 None 을 돌려주고, 호출자(hub_collect.py)가
그 실패를 흡수한다. 설계 근거는 docs/prps/hub-theme-and-usage-panel.md 결정 U2·U3,
docs/prps/hub-usage-reset-time-and-refresh.md 결정 S1~S5·R1·R2·R5, docs/prps/
hub-card-cleanup-and-usage-source.md 결정 P1~P8 이 정본이다.
"""

import json
import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone

USAGE_SESSION_WINDOW_HOURS = 5          # rate_limits.five_hour 가 재는 창의 길이. 만료 기준의 근거(결정 U3)
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
    """세션(5시간)·주간(7일) 한도 사용률 — RateLimitCapture 의 투영(결정 P3)."""

    sampled_at_ms: int      # statusLine 이 이 값들을 관측한 시각(captured_at_ms). 파생값(나이)은
                             # 담지 않는다 — content_key 재작성 폭주 방지(결정 D3)
    session_percent: int    # rate_limits.five_hour.used_percentage 를 내림한 정수(0~100)
    weekly_percent: int     # rate_limits.seven_day.used_percentage 를 내림한 정수(0~100)


@dataclass(frozen=True)
class RateLimitResets:
    """Claude Code statusLine 이 알려 준 한도 창의 초기화 예정 시각. 창은 각각 없을 수 있다."""

    captured_at_ms: int                 # 이 값들을 '처음 관측한' 시각(결정 S3 — 마지막 관측이 아니다)
    session_resets_at_ms: int | None    # rate_limits.five_hour.resets_at (초 → ms 변환됨)
    weekly_resets_at_ms: int | None     # rate_limits.seven_day.resets_at (초 → ms 변환됨)


@dataclass(frozen=True)
class RateLimitCapture:
    """statusLine 이 관측한 한도 스냅샷 1건 — 창별 초기화 예정 시각 + 내림 정수 사용률.

    파일(`~/.claude/hub/rate_limits.json`)과 statusLine stdin 양쪽의 파싱 결과 타입이다.
    화면용 두 타입(UsageSample·RateLimitResets)은 이것의 투영이다(결정 P3).
    """

    captured_at_ms: int                   # 이 값들을 '처음 관측한' 시각(결정 S3 — 마지막 관측이 아니다)
    session_resets_at_ms: int | None      # rate_limits.five_hour.resets_at (초 → ms)
    weekly_resets_at_ms: int | None       # rate_limits.seven_day.resets_at (초 → ms)
    session_used_percent: int | None      # rate_limits.five_hour.used_percentage 를 내림한 정수
    weekly_used_percent: int | None       # rate_limits.seven_day.used_percentage 를 내림한 정수


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


def is_usage_sample_expired(sample: UsageSample, now_ms: int) -> bool:
    """샘플이 세션 창(5시간)보다 오래됐는가 — 그러면 세션 사용률의 근거가 사라진다(결정 U3).

    `session_percent` 는 정의상 5시간 창의 사용률이라, 창 길이가 곧 만료 기준이다. 시계가
    뒤틀려 `now_ms` 가 샘플보다 과거면(나이가 음수) 만료로 보지 않는다.
    """
    age_ms = now_ms - sample.sampled_at_ms
    return age_ms >= USAGE_MAX_SAMPLE_AGE_MS


# ---- statusLine rate_limits (docs/prps/hub-usage-reset-time-and-refresh.md,
#      docs/prps/hub-card-cleanup-and-usage-source.md) ----
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


def _valid_used_percentage(window: object) -> int | None:
    """rate_limits.{five_hour,seven_day}.used_percentage 를 검증해 내림한 정수를 돌려준다.

    실수·정수 모두 허용하되 bool 은 배제하고(U2 와 같은 정신) 0~100 범위 밖은 생략한다.
    statusLine stdin·캡처 파일 양쪽에서 쓰는 퍼센트 추출의 정본이다(결정 P1·P7).
    """
    if not isinstance(window, dict):
        return None
    value = window.get("used_percentage")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not (USAGE_PERCENT_MIN <= value <= USAGE_PERCENT_MAX):
        return None
    return math.floor(value)


def parse_status_line_rate_limits(text: str, captured_at_ms: int) -> RateLimitCapture | None:
    """statusLine stdin JSON 에서 두 창의 초기화 예정 시각 + 사용률을 읽는다.

    네 값(리셋 2개·퍼센트 2개)이 전부 없으면 None(결정 P2) — 창별·필드별로 독립 탈락한다.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return None
    five_hour = rate_limits.get("five_hour")
    seven_day = rate_limits.get("seven_day")
    session_resets_at_ms = _valid_resets_at_ms(five_hour, captured_at_ms)
    weekly_resets_at_ms = _valid_resets_at_ms(seven_day, captured_at_ms)
    session_used_percent = _valid_used_percentage(five_hour)
    weekly_used_percent = _valid_used_percentage(seven_day)
    if (
        session_resets_at_ms is None
        and weekly_resets_at_ms is None
        and session_used_percent is None
        and weekly_used_percent is None
    ):
        return None
    return RateLimitCapture(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
        session_used_percent=session_used_percent,
        weekly_used_percent=weekly_used_percent,
    )


def parse_rate_limit_capture(text: str) -> RateLimitCapture | None:
    """우리가 쓴 캡처 파일을 되읽는다. 계약이 안 맞으면 None(예외를 던지지 않는다).

    구형 파일(퍼센트 키 없음)은 두 퍼센트 필드가 None 인 정상 캡처로 파싱된다(결정 P2,
    읽기 하위 호환) — 마이그레이션 코드는 없다. 퍼센트는 필드 단위로 탈락시키고(엄격 int,
    `_is_valid_percent` 재사용), 리셋 시각은 기존 규칙대로 타입이 안 맞으면 레코드 전체를
    버린다. 네 값이 전부 없으면 None.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    captured_at_ms = payload.get("captured_at_ms")
    if not _is_valid_epoch_ms(captured_at_ms):
        return None
    session_resets_at_ms = payload.get("session_resets_at_ms")
    if session_resets_at_ms is not None and not _is_valid_epoch_ms(session_resets_at_ms):
        return None
    weekly_resets_at_ms = payload.get("weekly_resets_at_ms")
    if weekly_resets_at_ms is not None and not _is_valid_epoch_ms(weekly_resets_at_ms):
        return None
    session_used_percent = payload.get("session_used_percent")
    if session_used_percent is not None and not _is_valid_percent(session_used_percent):
        session_used_percent = None
    weekly_used_percent = payload.get("weekly_used_percent")
    if weekly_used_percent is not None and not _is_valid_percent(weekly_used_percent):
        weekly_used_percent = None
    if (
        session_resets_at_ms is None
        and weekly_resets_at_ms is None
        and session_used_percent is None
        and weekly_used_percent is None
    ):
        return None
    return RateLimitCapture(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
        session_used_percent=session_used_percent,
        weekly_used_percent=weekly_used_percent,
    )


def usage_sample_from_capture(capture: RateLimitCapture) -> UsageSample | None:
    """캡처를 화면용 UsageSample 로 투영한다(결정 P3). 퍼센트가 둘 다 있을 때만 만들어진다."""
    if capture.session_used_percent is None or capture.weekly_used_percent is None:
        return None
    return UsageSample(
        sampled_at_ms=capture.captured_at_ms,
        session_percent=capture.session_used_percent,
        weekly_percent=capture.weekly_used_percent,
    )


def resets_from_capture(capture: RateLimitCapture) -> RateLimitResets | None:
    """캡처를 화면용 RateLimitResets 로 투영한다(결정 P3). 리셋이 둘 다 없으면 None."""
    if capture.session_resets_at_ms is None and capture.weekly_resets_at_ms is None:
        return None
    return RateLimitResets(
        captured_at_ms=capture.captured_at_ms,
        session_resets_at_ms=capture.session_resets_at_ms,
        weekly_resets_at_ms=capture.weekly_resets_at_ms,
    )


def is_session_window_rolled_over(capture: RateLimitCapture, now_ms: int) -> bool:
    """세션(5시간) 창이 이미 리셋됐는가(결정 P5) — 그러면 캡처된 세션 퍼센트는 확실히 틀렸다.

    `session_resets_at_ms` 를 모르면(None) 참으로 취급하지 않는다 — 모름을 롤오버로
    단정하면 근거 없이 패널을 지운다.
    """
    if capture.session_resets_at_ms is None:
        return False
    return capture.session_resets_at_ms <= now_ms


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


def same_capture_values(previous: RateLimitCapture | None, current: RateLimitCapture) -> bool:
    """캡처 시각을 뺀 리셋 2개 + 퍼센트 2개가 모두 같은가 — 같으면 다시 쓰지 않는다(결정 P4).

    `captured_at_ms` 를 비교에 넣으면 0.3초 주기의 원자적 쓰기가 정상 상태에서도 발생한다
    (GOTCHA 4) — 절대 넣지 않는다. (구 `same_reset_times` — 퍼센트도 비교하게 되어 이름을
    바꿨다. 이름이 거짓이 되면 다음 사람이 퍼센트 비교를 빼먹는다.)
    """
    if previous is None:
        return False
    return (
        previous.session_resets_at_ms == current.session_resets_at_ms
        and previous.weekly_resets_at_ms == current.weekly_resets_at_ms
        and previous.session_used_percent == current.session_used_percent
        and previous.weekly_used_percent == current.weekly_used_percent
    )


def format_status_line_summary(capture: RateLimitCapture | None) -> str:
    """캡처로 터미널 상태줄 한 줄을 만든다. 쓸 값이 없으면 빈 문자열.

    상태줄 출력과 패널이 항상 같은 숫자를 보이도록, 퍼센트 추출은 파서(캡처) 하나가
    정본이다(결정 P7) — 이 함수는 캡처를 받기만 하고 다시 파싱하지 않는다.
    """
    if capture is None:
        return ""
    parts = []
    if capture.session_used_percent is not None:
        parts.append(f"세션 {capture.session_used_percent}%")
    if capture.weekly_used_percent is not None:
        parts.append(f"주간 {capture.weekly_used_percent}%")
    return " · ".join(parts)


# ---- 사용량 API 응답 (R1, docs/prps/hub-card-interactions-and-usage.md 「SP3 생략」 개정) ----
# 스파이크 SP3(사전 API 호출)가 생략되고 "첫 폴링이 스파이크를 겸한다" 방식이 승인됨에 따라,
# 1차 대응표는 SP3 실측이 아니라 커뮤니티 사용량 도구들이 공통으로 쓰는 스키마를 따른다.
# 실 스키마가 다르면 schema_mismatch 로 강등되고 describe_json_key_structure 의 결과가
# 자기 진단 창구가 된다 — 대응표가 틀렸을 때 화면이 깨지는 대신 조용히 강등된다(결정 A7).
def _valid_usage_api_percentage(window: object) -> int | None:
    """usage API 창 하나의 utilization(0~100 숫자)을 검증해 내림한 정수를 돌려준다.

    필드명만 다를 뿐(utilization vs used_percentage) 값 검증 규칙은 `_valid_used_percentage`
    를 그대로 재사용한다 — 판정 규칙이 출처마다 갈리면 상태줄과 패널이 다른 숫자를 보이게
    된다(결정 P7 과 같은 이유).
    """
    if not isinstance(window, dict):
        return None
    return _valid_used_percentage({"used_percentage": window.get("utilization")})


def _valid_usage_api_resets_at_ms(window: object, captured_at_ms: int) -> int | None:
    """usage API 창 하나의 resets_at(ISO 8601 문자열)을 ms 로 변환해 검증한다.

    statusLine 경로의 `resets_at` 은 초 단위 epoch 정수지만 usage API 는 ISO 8601 문자열이다
    (1차 대응표). 문자열을 초 단위 epoch 로 바꾼 뒤 `_valid_resets_at_ms` 에 그대로 넘겨
    지평선(단위 혼동) 검사 로직을 두 곳에 중복시키지 않는다. 타임존이 없는 문자열은 UTC 로
    간주한다 — usage API 응답은 UTC 라고 가정하는 것이 로컬 타임존을 추측하는 것보다 안전하다.
    """
    if not isinstance(window, dict):
        return None
    resets_at = window.get("resets_at")
    if not isinstance(resets_at, str):
        return None
    try:
        parsed = datetime.fromisoformat(resets_at)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return _valid_resets_at_ms({"resets_at": int(parsed.timestamp())}, captured_at_ms)


def parse_usage_api_response(text: str, captured_at_ms: int) -> RateLimitCapture | None:
    """usage API 응답 JSON 에서 캡처를 만든다. 계약이 안 맞으면 None(예외를 던지지 않는다).

    1차 대응표(SP3 생략 개정): 최상위 `five_hour`·`seven_day` 객체, 각각
    `utilization`(0~100 숫자)·`resets_at`(ISO 8601 문자열). 반환 타입은 기존
    `RateLimitCapture` 그대로다 — 기존 캡처 파일 포맷·소비자를 바꾸지 않는 것이 이 설계의
    핵심이다(결정 A2).
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    five_hour = payload.get("five_hour")
    seven_day = payload.get("seven_day")
    session_resets_at_ms = _valid_usage_api_resets_at_ms(five_hour, captured_at_ms)
    weekly_resets_at_ms = _valid_usage_api_resets_at_ms(seven_day, captured_at_ms)
    session_used_percent = _valid_usage_api_percentage(five_hour)
    weekly_used_percent = _valid_usage_api_percentage(seven_day)
    if (
        session_resets_at_ms is None
        and weekly_resets_at_ms is None
        and session_used_percent is None
        and weekly_used_percent is None
    ):
        return None
    return RateLimitCapture(
        captured_at_ms=captured_at_ms,
        session_resets_at_ms=session_resets_at_ms,
        weekly_resets_at_ms=weekly_resets_at_ms,
        session_used_percent=session_used_percent,
        weekly_used_percent=weekly_used_percent,
    )


def _describe_json_node(node: object, path: str) -> list[str]:
    """JSON 값 하나를 경로+타입 문자열 목록으로 접는다(재귀, 값은 절대 포함하지 않는다)."""
    if isinstance(node, dict):
        described: list[str] = []
        for key in sorted(node):
            described.extend(_describe_json_node(node[key], f"{path}/{key}"))
        return described
    if isinstance(node, list):
        described = [f"{path} [list len={len(node)}]"]
        if node:
            described.extend(_describe_json_node(node[0], f"{path}/0"))
        return described
    return [f"{path} <{type(node).__name__}>"]


def describe_json_key_structure(text: str) -> list[str] | None:
    """JSON 문자열의 키 경로 + 타입 목록을 만든다. **값은 절대 포함하지 않는다**(불변식 A-SEC).

    schema_mismatch 실패 기록(`last_usage_api_error.json` 의 `response_keys`)에 실려
    자기 진단 창구가 된다(SP3 생략 개정) — 실제 응답 스키마가 1차 대응표와 다를 때, 사람이
    `/hub status` 로 그 구조를 보고 대응표를 고칠 수 있게 한다. JSON 이 아니면 None.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return _describe_json_node(payload, "")
