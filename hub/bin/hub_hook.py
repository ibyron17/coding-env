#!/usr/bin/env python3
"""hub_hook.py — 훅 엔트리. stdin 이벤트 1줄 append + 리텐션 정리 + 쓰로틀 재수집 spawn. 항상 exit 0.

세션을 막지 않는 것이 이 스크립트의 유일한 절대 규칙이다 — 모든 예외를 여기서 삼킨다.
훅 설치 커맨드 문자열의 `|| true`·`>/dev/null` 은 2차 방어일 뿐, 1차 방어는 이 스크립트 자신이다.

재수집(`hub.py collect`)은 이 프로세스가 직접 하지 않고 분리된 프로세스로 spawn 한다(검수 M4) —
프로젝트 수에 비례해 늘어나는 파일 읽기 비용을 훅 자신이 지면, "훅은 항상 빠르게 끝난다"는
보장이 성립하지 않는다. 훅 자신의 작업은 append + 리텐션 정리(수 ms)뿐이다.

**상주 서버가 켜져 있으면 훅은 spawn 하지 않는다**(개정 쟁점 R3) — 서버가 5초 주기로 수집을
전담하므로 훅까지 같은 일을 하면 중복이다. 판정은 순수 함수 `should_spawn_collect` 하나로
빠져 단위 테스트가 가능하다. 서버 생존 판정은 하트비트 파일 mtime 만 본다(`stat()` 1회) —
포트 프로브·PID 조회는 훅을 지연시킬 수 있어 넣지 않는다(불변 원칙 1).
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import hub_collect
import hub_model
import hub_server_state

HUB_PY_PATH = Path(__file__).resolve().parent / "hub.py"
# 기록 상한. 카드에 보이는 길이가 아니라 **툴팁이 보여줄 전문**의 상한이다 — 카드는
# EXCERPT_DISPLAY_MAX_CHARS(hub_template.html)로 다시 줄여 보여주고, 그때 잘린 뒷부분을 툴팁이
# 맡는다. 이 상한이 120 이던 동안은 툴팁이 보여줄 것이 애초에 기록되지 않았다.
# 500 자의 근거(실측 187건 · 8일분): 사용자가 타이핑한 프롬프트는 중간값 51자·p90 571자라
# 88건 중 79건이 이 안에 온전히 들어간다. 1000자로 올려도 담기는 건수는 81건으로 2건만
# 늘어나는데(긴 것들은 어차피 수천 자다) 저장량은 1.3배가 되므로 여기서 끊는다.
# 이 값을 올리면 events/*.jsonl 평문 보관 분량과 hub.html 인라인 크기가 함께 늘어난다 —
# README 「프라이버시 고지」와 commands/hub.md 의 설치 동의 문구가 이 숫자를 그대로 인용하므로
# 같이 고쳐야 한다.
# 또 하나의 상한 근거 — `_append_event_line` 의 "1회 write() = 사실상 원자적 append" 논거는
# 줄 하나가 파이썬 텍스트 버퍼(io.DEFAULT_BUFFER_SIZE = 8192B) 안에 들어간다는 전제 위에 서
# 있다. 이 줄에는 프롬프트만 있는 게 아니라 길이를 제한하지 않는 `c`(cwd)도 함께 실리므로,
# 최악의 줄은 "가장 깊은 경로 + 전부 제어문자인 프롬프트"다(제어문자는 JSON 이 `\uXXXX` 6B 로
# 이스케이프해 문자당 가장 길다 — 비BMP 4B·한글 3B 보다 크다). 실측: cwd 1024B(macOS PATH_MAX)
# + 제어문자 500자 + 말줄임표 = 4127B 로 버퍼의 절반이다. 이 상한을 올리려면 위 계산부터
# 다시 해야 한다(테스트가 먼저 깨지게 해 두었다).
PROMPT_EXCERPT_MAX_CHARS = 500
# 상한에서 잘렸으면 그 사실이 툴팁에 보여야 한다 — 붙이지 않으면 툴팁이 "전문"이라고 거짓말한다.
PROMPT_TRUNCATION_MARK = "…"
REFRESH_THROTTLE_SECONDS = 5
THROTTLE_MS = REFRESH_THROTTLE_SECONDS * 1000


# 훅이 받는 `prompt` 에는 사용자가 타이핑한 것 외에 CLI 가 앞에 덧붙이는 블록이 섞여 온다.
# 실측(187건)에서 관측된 것은 세 종류이고, 성격이 둘로 갈린다 — `<ide_selection>`·
# `<ide_opened_file>` 은 **뒤에 실제 입력이 이어지고**(예: "…</ide_selection>현재 수정사항들을
# slide 에도 동일하게 적용해줘."), `<task-notification>` 은 뒤에 아무것도 없는 순수 알림이다.
# 그래서 "이런 프롬프트는 버린다"가 아니라 "선행 블록만 벗겨낸다"로 판정한다 — 벗기고 남은
# 것이 곧 사용자가 입력한 프롬프트이고, 남은 것이 없으면 기록할 프롬프트가 없다는 뜻이다.
# 앞에서만 벗긴다 — 사용자가 본문 중간에 쓴 태그를 지우면 그건 입력 왜곡이다. 앵커는 패턴의
# `\A` 가 아니라 `match(prompt, offset)` 이 담당한다(`\A` 는 문자열 진짜 처음에만 맞아
# offset > 0 에서 영구히 실패한다). 선행 공백은 패턴의 `\s*` 가 함께 먹는다.
# `ide_\w+` 로 계열을 묶은 것은 관측된 두 태그가 같은 IDE 연동 계열이라는 근거에 따른 것이며,
# 슬래시 커맨드는 벗길 대상이 아니다 — 실측에서 `/hub server restart` 처럼 타이핑한 원문
# 그대로 도착한다.
AUTO_INJECTED_PROMPT_BLOCK = re.compile(r"\s*<(ide_\w+|task-notification)>.*?</\1>", re.DOTALL)


def strip_auto_injected_blocks(prompt: str) -> str:
    """프롬프트 앞에 붙은 CLI 자동주입 블록을 벗겨내고 사용자가 입력한 부분만 남긴다.

    앞뒤 공백도 함께 정리한다 — "벗기고 남은 것이 있는가"의 판정이 공백 하나에 갈리면 안 되고,
    화면에 실리는 발췌에 앞뒤 공백을 남길 이유도 없다.

    블록마다 문자열을 새로 슬라이스하지 않고 오프셋만 옮긴다(검수 3차 MEDIUM) — 슬라이스는
    남은 길이에 비례하므로 블록이 n개 연속되면 O(n²)이 되고, 이 파일의 절대 규칙("세션을
    막지 않는다")과 정면으로 부딛친다. 오프셋 방식은 입력 길이에 선형이다.
    """
    offset = 0
    while True:
        match = AUTO_INJECTED_PROMPT_BLOCK.match(prompt, offset)
        if match is None:
            return prompt[offset:].strip()
        offset = match.end()


def _clip_prompt(prompt: str) -> str:
    """기록 상한을 넘는 프롬프트를 자른다. 잘렸으면 말줄임표를 붙여 그 사실을 남긴다."""
    if len(prompt) <= PROMPT_EXCERPT_MAX_CHARS:
        return prompt
    return prompt[:PROMPT_EXCERPT_MAX_CHARS] + PROMPT_TRUNCATION_MARK


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
        # 전부 자동주입이었으면 `p` 를 아예 싣지 않는다 — 그 경우 세션의 발췌는 직전에 입력한
        # 프롬프트를 그대로 유지한다(hub_session._apply_tracked_event 가 None 을 덮어쓰지 않는다).
        typed_prompt = strip_auto_injected_blocks(str(prompt))
        if typed_prompt:
            fields["p"] = _clip_prompt(typed_prompt)
    return fields


def _append_event_line(fields: dict) -> None:
    """events/<오늘>.jsonl 에 1회 write() 로 한 줄을 append 한다(짧은 줄 = 동시 append 안전)."""
    hub_collect.EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    today = time.strftime(hub_collect.DATE_FORMAT, time.localtime())
    file_path = hub_collect.EVENTS_DIR / f"{today}.jsonl"
    line = json.dumps(fields, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(file_path, "a", encoding="utf-8") as event_file:
        event_file.write(line)


def _mtime_ms_or_none(path) -> int | None:
    try:
        return int(path.stat().st_mtime * 1000)
    except OSError:
        return None


def _should_spawn_collect_now(config: hub_model.HubConfig) -> bool:
    """`should_spawn_collect`(순수)에 지금 시각의 파일 상태를 채워 판정한다.

    서버 생존은 하트비트 mtime 만으로 판정한다(포트 프로브·PID 조회는 훅을 지연시킬 수 있어
    넣지 않는다 — 불변 원칙 1). 서버가 죽으면 TTL 이 지나며 이 훅 폴백이 자동으로 부활한다.
    """
    ttl_ms = hub_server_state.server_heartbeat_ttl_ms(config.server_collect_interval_seconds)
    heartbeat_mtime_ms = _mtime_ms_or_none(hub_collect.SERVER_HEARTBEAT_PATH)
    server_alive = hub_server_state.is_server_alive(int(time.time() * 1000), heartbeat_mtime_ms, ttl_ms)
    return hub_server_state.should_spawn_collect(
        now_ms=int(time.time() * 1000),
        server_alive=server_alive,
        hub_html_mtime_ms=_mtime_ms_or_none(hub_collect.HUB_HTML_PATH),
        spawn_stamp_mtime_ms=_mtime_ms_or_none(hub_collect.SPAWN_STAMP_PATH),
        throttle_ms=THROTTLE_MS,
    )


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

    if _should_spawn_collect_now(config):
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
