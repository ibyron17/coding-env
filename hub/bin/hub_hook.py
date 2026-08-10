#!/usr/bin/env python3
"""hub_hook.py — 훅 엔트리. stdin 이벤트 1줄 append + 리텐션 정리 + 쓰로틀 재수집 spawn. 항상 exit 0.

세션을 막지 않는 것이 이 스크립트의 유일한 절대 규칙이다 — 모든 예외를 여기서 삼킨다.
훅 설치 커맨드 문자열의 `|| true`·`>/dev/null` 은 2차 방어일 뿐, 1차 방어는 이 스크립트 자신이다.

재수집(`hub.py collect`)은 이 프로세스가 직접 하지 않고 분리된 프로세스로 spawn 한다(검수 M4) —
프로젝트 수에 비례해 늘어나는 파일 읽기 비용을 훅 자신이 지면, "훅은 항상 빠르게 끝난다"는
보장이 성립하지 않는다. 훅 자신의 작업은 append + 리텐션 정리(수 ms)뿐이다.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import hub_collect

HUB_PY_PATH = Path(__file__).resolve().parent / "hub.py"
PROMPT_EXCERPT_MAX_CHARS = 120
REFRESH_THROTTLE_SECONDS = 5


def _project_fields(payload: dict, record_prompt_excerpt: bool) -> dict:
    """훅 페이로드에서 화면에 쓰이는 필드만 골라 짧은 키로 투영한다."""
    fields = {
        "t": int(time.time() * 1000),
        "e": payload.get("hook_event_name", ""),
        "s": payload.get("session_id", ""),
        "c": payload.get("cwd", ""),
    }
    optional_keys = {"source": "so", "reason": "r", "agent_id": "ai", "agent_type": "at"}
    for payload_key, short_key in optional_keys.items():
        if payload.get(payload_key) is not None:
            fields[short_key] = payload[payload_key]
    prompt = payload.get("prompt")
    if record_prompt_excerpt and prompt:
        fields["p"] = str(prompt)[:PROMPT_EXCERPT_MAX_CHARS]
    return fields


def _append_event_line(fields: dict) -> None:
    """events/<오늘>.jsonl 에 1회 write() 로 한 줄을 append 한다(짧은 줄 = 동시 append 안전)."""
    hub_collect.EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    today = time.strftime(hub_collect.DATE_FORMAT, time.localtime())
    file_path = hub_collect.EVENTS_DIR / f"{today}.jsonl"
    line = json.dumps(fields, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(file_path, "a", encoding="utf-8") as event_file:
        event_file.write(line)


def _hub_html_is_stale_enough_to_refresh() -> bool:
    """hub.html 이 없으면(허브 미사용) False, 있고 쓰로틀 창을 넘겼으면 True.

    스탬프 파일(SPAWN_STAMP_PATH)이 있으면 hub.html 의 mtime 대신 그것을 쓴다(검수 n3) —
    hub.html 은 spawn 된 collect 가 끝나야 갱신되므로, 버스트(여러 훅이 거의 동시에 도착)
    상황에서 뒤따르는 훅들이 여전히 오래된 mtime 을 보고 각자 spawn 을 결정해 버린다.
    """
    if not hub_collect.HUB_HTML_PATH.exists():
        return False
    if hub_collect.SPAWN_STAMP_PATH.exists():
        reference_mtime = hub_collect.SPAWN_STAMP_PATH.stat().st_mtime
    else:
        reference_mtime = hub_collect.HUB_HTML_PATH.stat().st_mtime
    age_seconds = time.time() - reference_mtime
    return age_seconds >= REFRESH_THROTTLE_SECONDS


def _spawn_background_collect() -> None:
    """`hub.py collect` 를 분리된 프로세스로 띄운다 — 훅 자신은 그 결과를 기다리지 않는다.

    spawn 직전에 디바운스 스탬프를 찍어(검수 n3) 뒤따르는 훅들의 쓰로틀 판정이 곧바로
    갱신되게 한다. 이 순서(스탬프 먼저)가 중요하다 — Popen 이 실패해도 스탬프는 남아
    다음 훅이 재시도할 기회를 5초 뒤로 미루는 것이, 매 훅마다 재시도를 시도하는 것보다 낫다.
    """
    hub_collect.touch_spawn_stamp()
    try:
        subprocess.Popen(
            [sys.executable, str(HUB_PY_PATH), "collect"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def _run() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    config, _config_warnings = hub_collect.load_config()
    _append_event_line(_project_fields(payload, config.record_prompt_excerpt))
    # hub.html 이 없어도(허브 off 상태) 항상 실행돼야 "최대 N일 보관" 고지가 성립한다(검수 M5).
    hub_collect.prune_old_event_files(int(time.time() * 1000), config.event_retention_days)

    if _hub_html_is_stale_enough_to_refresh():
        _spawn_background_collect()


def main() -> int:
    """항상 0 을 반환한다 — 이 훅이 세션 진행을 막는 일은 원리적으로 없어야 한다."""
    try:
        _run()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
