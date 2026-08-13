"""hub_usage_fetch.py — 사용량 API I/O 전용(R1, docs/prps/hub-card-interactions-and-usage.md).

OAuth accessToken 이 존재하는 **유일한 파일**이다 — "누가 토큰을 볼 수 있는가"를 이 파일
하나의 질문으로 만들기 위해 격리했다.

불변식 A-SEC(양보 불가): accessToken 은 이 모듈의 **지역 변수로만** 존재한다. 로그·stderr·
server.log·rate_limits.json·last_usage_api_error.json·hub.html·warnings 그 어디에도
나타나지 않는다. 실패 사유는 `FAILURE_REASON_MESSAGES` 의 고정 어휘만 반환한다 — 예외
객체를 문자열로 바꿔 반환값에 섞는 일은 절대 하지 않는다(예외 메시지에 URL·헤더 파편이
섞여 나올 여지를 원천 차단한다). Keychain 호출은 인자를 리스트로 넘기고 셸을 거치지 않는다
(T25-61 이 검사한다).
"""

import json
import subprocess
import urllib.error
import urllib.request
from typing import Literal

import hub_usage

USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"   # SP3 생략 개정 — 1차 대응표(커뮤니티 알려진 엔드포인트)
KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"
FETCH_TIMEOUT_SECONDS = 10
KEYCHAIN_TIMEOUT_SECONDS = 5
ANTHROPIC_BETA_HEADER_VALUE = "oauth-2025-04-20"

_HTTP_STATUS_UNAUTHORIZED = 401
_HTTP_STATUS_FORBIDDEN = 403
_HTTP_STATUS_RATE_LIMITED = 429

FailureReason = Literal[
    "credential_unavailable",   # Keychain 항목 없음·잠김·명령 부재·플랫폼 미지원
    "credential_unparsable",    # 항목은 읽었으나 토큰 필드가 없다
    "http_unauthorized",        # 401/403 — 토큰 만료. 재로그인 필요
    "http_rate_limited",        # 429 — 즉시 백오프 상한
    "http_error",                # 그 외 4xx/5xx
    "network_error",             # 타임아웃·DNS·연결 실패
    "schema_mismatch",           # 200 인데 우리가 아는 모양이 아니다
]

FAILURE_REASON_MESSAGES: dict[str, str] = {
    "credential_unavailable": "Keychain 에서 자격증명을 읽을 수 없습니다",
    "credential_unparsable": "Keychain 항목에서 토큰 필드를 찾을 수 없습니다",
    "http_unauthorized": "인증이 만료됐습니다 — 재로그인이 필요합니다",
    "http_rate_limited": "요청이 제한됐습니다(429)",
    "http_error": "사용량 API 가 오류를 반환했습니다",
    "network_error": "사용량 API 에 연결할 수 없습니다",
    "schema_mismatch": "사용량 API 응답 형식이 예상과 다릅니다",
}


def _read_oauth_access_token_with_reason() -> tuple[str | None, FailureReason | None]:
    """Keychain 에서 토큰을 읽고 실패 사유까지 함께 돌려준다(내부 전용).

    `read_oauth_access_token()`(공개 인터페이스, 사유를 버린다)과 `fetch_rate_limit_capture()`
    가 이 함수를 공유한다 — 후자는 `credential_unavailable`(Keychain 접근 자체 실패)과
    `credential_unparsable`(접근은 됐으나 토큰 필드가 없음)을 구분해야 한다.
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE_NAME, "-w"],
            capture_output=True, text=True, timeout=KEYCHAIN_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "credential_unavailable"
    if result.returncode != 0:
        return None, "credential_unavailable"
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return None, "credential_unparsable"
    claude_oauth = payload.get("claudeAiOauth") if isinstance(payload, dict) else None
    token = claude_oauth.get("accessToken") if isinstance(claude_oauth, dict) else None
    if isinstance(token, str) and token:
        return token, None
    return None, "credential_unparsable"


def read_oauth_access_token() -> str | None:
    """macOS Keychain 에서 Claude Code OAuth accessToken 을 읽는다. 실패하면 None.

    반환값은 절대 로그·파일·hub.html 에 남기지 않는다(불변식 A-SEC).
    """
    token, _reason = _read_oauth_access_token_with_reason()
    return token


def _classify_http_error(status_code: int) -> FailureReason:
    """HTTP 응답 코드를 고정 어휘 사유로 접는다."""
    if status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
        return "http_unauthorized"
    if status_code == _HTTP_STATUS_RATE_LIMITED:
        return "http_rate_limited"
    return "http_error"


def fetch_rate_limit_capture(
    now_ms: int,
) -> tuple[hub_usage.RateLimitCapture | None, FailureReason | None, list[str] | None]:
    """사용량 API 를 1회 호출해 캡처를 만든다.

    반환은 `(캡처, 실패사유, 실패상세)` 3-튜플이다(개정 반영 — SP3 생략과 함께). 캡처 또는
    실패사유 중 정확히 하나가 채워진다. 실패상세는 `schema_mismatch` 일 때만 응답의 키
    구조 목록(값은 없다, 불변식 A-SEC)을 담아 자기 진단 창구가 된다 — 그 외 사유는 항상 None.
    """
    token, credential_failure_reason = _read_oauth_access_token_with_reason()
    if token is None:
        return None, credential_failure_reason, None

    request = urllib.request.Request(
        USAGE_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": ANTHROPIC_BETA_HEADER_VALUE,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return None, _classify_http_error(error.code), None
    except (urllib.error.URLError, OSError):
        return None, "network_error", None
    except Exception:
        # 이 함수는 토큰을 지역 변수로 쥔 채로 원격 호출을 한다(불변식 A-SEC 경계) — 여기서
        # 분류하지 못한 예외를 그대로 밖으로 새어나가게 두면 호출자(_collect_loop)의
        # 범용 핸들러가 그 예외를 문자열로 바꿔 server.log 에 남긴다. http.client.IncompleteRead·
        # BadStatusLine 처럼 OSError 가 아닌 http.client.HTTPException 계열이 실제로 이
        # 경계를 뚫는 사례다(검수 지적). 이런 예외들이 우연히 토큰을 담지 않더라도, "토큰
        # 보유 함수에서 미분류 예외가 경계를 넘는다"는 구조 자체가 A-SEC 이 없애려는 형태라
        # 이 함수만은 마지막 방어선으로 광범위하게 잡는다 — 다른 모듈에는 이 관례를 적용하지
        # 않는다(카프시 #2, 이유가 있는 곳에만 예외 처리를 둔다).
        return None, "network_error", None

    capture = hub_usage.parse_usage_api_response(body, now_ms)
    if capture is None:
        return None, "schema_mismatch", hub_usage.describe_json_key_structure(body)
    return capture, None, None
