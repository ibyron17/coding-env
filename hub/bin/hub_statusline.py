#!/usr/bin/env python3
"""hub_statusline.py — statusLine 진입점. stdin → (변화 시) 캡처 파일 → 상태줄 한 줄 출력. 항상 exit 0.

Claude Code CLI 는 statusLine 커맨드를 최대 0.3초마다(메시지 갱신 시) 실행하고 stdout 을
그대로 상태줄에 그린다 — stdin 을 절대 밖으로 되던지지 않고, 어떤 예외도 던지지 않는 것이
이 스크립트의 유일한 절대 규칙이다(hub_hook.py 와 같은 이유·같은 처리).

실행 순서가 곧 성능 설계다(docs/prps/hub-usage-reset-time-and-refresh.md 「hub_statusline.py」
절, docs/prps/hub-card-cleanup-and-usage-source.md 결정 P7 이 정본) — stdin 을 **한 번만**
파싱해 캡처를 만들고, 그 캡처에서 출력 문자열도 만든다(상태줄과 사용량 패널이 항상 같은
숫자를 보이는 이유). 먼저 출력해 상태줄이 항상 그려지게 하고, 그 다음에야 파일 작업을 한다.
`rate_limits` 가 없는 세션(정상 시나리오)은 파일 I/O 가 0회다. 캡처 값(리셋 2개 + 퍼센트
2개)이 이전과 같으면도 다시 쓰지 않는다(결정 S3·P4) — 그래야 0.3초 주기의 원자적 쓰기가
정상 상태에서 0회가 된다.
"""

import sys
import time

import hub_collect
import hub_usage


def _run() -> None:
    payload_text = sys.stdin.read()
    now_ms = int(time.time() * 1000)
    capture = hub_usage.parse_status_line_rate_limits(payload_text, now_ms)
    # 먼저 출력한다 — 뒤의 파일 작업이 어떻게 되든(실패해도) 상태줄은 이미 그려진 뒤다.
    print(hub_usage.format_status_line_summary(capture))
    if capture is None:
        return  # rate_limits 없는 세션의 정상 경로 — 파일을 만지지 않는다

    previous, _warnings = hub_collect.read_rate_limit_capture()
    if not hub_usage.same_capture_values(previous, capture):
        hub_collect.write_rate_limit_capture(capture)


def main() -> int:
    """항상 0 을 반환한다 — 이 스크립트가 사용자 상태줄을 깨뜨리는 일은 원리적으로 없어야 한다."""
    try:
        _run()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
