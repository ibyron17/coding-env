"""hub_session.py — 훅 이벤트를 세션 사실로 접고, 그 사실을 표시 상태로 판정하는 순수 로직.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_session.py 대상).
`now_ms` 는 항상 인자로 받는다 — 테스트가 시계에 의존하지 않게 하기 위해서다.
상태 판정 규칙의 근거는 docs/prps/hub-dashboard.md 「상태 판정 규칙」 절이 정본이며,
좀비 서브에이전트 가드는 docs/prps/hub-zombie-subagent-guard.md, 세션 부활 규칙은
docs/prps/hub-session-revival-and-stale-tier1.md 가 정본이다.
"""

import json
from dataclasses import dataclass
from typing import Literal, Sequence

SessionState = Literal["working", "idle", "stale", "done"]
Phase = Literal["설계", "구현", "검수"]

SHORT_ID_LENGTH = 8

PHASE_BY_AGENT_TYPE: dict[str, Phase] = {
    "design-architect": "설계",
    "implementer": "구현",
    "code-reviewer": "검수",
}


# ---- 입력 ----
@dataclass(frozen=True)
class HookEvent:
    """이벤트 로그 한 줄이 나타내는 훅 이벤트 하나."""

    received_at_ms: int
    hook_event_name: str
    session_id: str
    cwd: str
    source: str | None
    reason: str | None
    agent_id: str | None
    agent_type: str | None
    prompt_excerpt: str | None


# ---- 사실(fact) ----
@dataclass(frozen=True)
class SubagentFact:
    """서브에이전트 실행 1건."""

    agent_id: str
    agent_type: str
    started_at_ms: int
    ended_at_ms: int | None


@dataclass(frozen=True)
class SessionFacts:
    """한 세션의 이벤트를 접어 만든 사실. 표시 판정의 입력이다."""

    session_id: str
    cwd: str
    # 이 창에서 관측된 모든 cwd. 첫 관측 순서, 중복 제거, **기본값 없음**(결정 WT19,
    # docs/prps/hub-worktree-fold.md). observed_cwds[0] == cwd 가 언제나 참이다 — 둘 다
    # 내부 이벤트 필터보다 앞에서 정해진다. `EnterWorktree` 가 살아 있는 세션의 cwd 를
    # 바꾸므로(E2) `cwd` 하나로는 "이 세션이 어디서 일했는가"를 답할 수 없다. 티어 1
    # 후보(결정 WT16)와 GN 세대 판정(결정 WT18)이 이 값을 쓴다.
    observed_cwds: tuple[str, ...]
    started_at_ms: int
    last_event_at_ms: int
    last_event_name: str
    turn_state: Literal["running", "ended"]
    ended_at_ms: int | None
    task_excerpt: str | None
    subagents: tuple[SubagentFact, ...]


# ---- 표시(view) ----
@dataclass(frozen=True)
class SubagentRunView:
    """세션에서 실행된 서브에이전트 타입 1종의 표시 상태(같은 타입의 여러 실행을 하나로 합친 것)."""

    agent_type: str            # 훅이 준 원문 그대로. 예: "implementer", "workflow-subagent"
    phase: Phase | None        # PHASE_BY_AGENT_TYPE 에 없으면 None
    # 같은 타입 실행 중 하나라도 "지금 돌고 있다고 볼 수 있으면"(is_running_subagent) True.
    # 좀비(SUBAGENT_ZOMBIE_AFTER_MS 초과 미종료)는 여기서도 False — 상태 판정과 같은 술어를
    # 쓰므로 카드 상태와 어긋날 수 없다(결정 ZG4, docs/prps/hub-zombie-subagent-guard.md).
    is_running: bool


@dataclass(frozen=True)
class SessionView:
    """세션 사실로부터 판정한 화면 표시 상태."""

    session_id: str
    short_id: str
    state: SessionState
    base_state: Literal["working", "idle", "done"]
    last_event_at_ms: int
    task_excerpt: str | None
    agent_runs: tuple[SubagentRunView, ...]


# ---- 내부 이벤트 필터 ----
def is_internal_session_start(event: HookEvent) -> bool:
    """compact 등 CLI 내부 사유로 발생한 SessionStart 인가."""
    return event.hook_event_name == "SessionStart" and event.source == "compact"


def is_untracked_internal_subagent_stop(
    event: HookEvent, known_agent_ids: frozenset[str]
) -> bool:
    """agent_type 이 비어 있고 대응하는 SubagentStart 를 본 적 없는 SubagentStop 인가."""
    return (
        event.hook_event_name == "SubagentStop"
        and not (event.agent_type or "")
        and (event.agent_id or "") not in known_agent_ids
    )


# ---- 이벤트 파싱 ----
def parse_event_line(line: str) -> HookEvent | None:
    """이벤트 로그 한 줄을 파싱한다. 깨진 줄은 None (호출자가 건너뛴다)."""
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        received_at_ms = int(payload["t"])
        hook_event_name = str(payload["e"])
        session_id = str(payload["s"])
        cwd = str(payload["c"])
    except (KeyError, TypeError, ValueError):
        return None
    return HookEvent(
        received_at_ms=received_at_ms,
        hook_event_name=hook_event_name,
        session_id=session_id,
        cwd=cwd,
        source=payload.get("so"),
        reason=payload.get("r"),
        agent_id=payload.get("ai"),
        agent_type=payload.get("at"),
        prompt_excerpt=payload.get("p"),
    )


# ---- 세션 사실 접기 ----
@dataclass
class _MutableSubagent:
    agent_type: str
    started_at_ms: int
    ended_at_ms: int | None


@dataclass
class _MutableSession:
    cwd: str
    observed_cwds: list[str]
    started_at_ms: int
    last_event_at_ms: int
    last_event_name: str
    turn_state: Literal["running", "ended"]
    ended_at_ms: int | None
    task_excerpt: str | None
    subagents: dict[str, _MutableSubagent]
    known_agent_ids: set[str]


def _handle_subagent_start(session: _MutableSession, event: HookEvent) -> None:
    agent_id = event.agent_id or ""
    session.known_agent_ids.add(agent_id)
    session.subagents[agent_id] = _MutableSubagent(
        agent_type=event.agent_type or "",
        started_at_ms=event.received_at_ms,
        ended_at_ms=None,
    )


def _handle_subagent_stop(session: _MutableSession, event: HookEvent) -> None:
    agent_id = event.agent_id or ""
    existing = session.subagents.get(agent_id)
    if existing is not None:
        existing.ended_at_ms = event.received_at_ms
        return
    session.subagents[agent_id] = _MutableSubagent(
        agent_type=event.agent_type or "",
        started_at_ms=event.received_at_ms,
        ended_at_ms=event.received_at_ms,
    )


def _apply_tracked_event(session: _MutableSession, event: HookEvent) -> None:
    """필터를 통과한(내부 이벤트가 아닌) 이벤트를 세션 사실에 반영한다."""
    if event.hook_event_name == "UserPromptSubmit":
        session.turn_state = "running"
        # 발췌는 "있을 때만" 덮어쓴다 — 훅은 프롬프트가 전부 CLI 자동주입(`<task-notification>` 등)
        # 이면 `p` 를 아예 싣지 않는다(hub_hook.strip_auto_injected_blocks). 무조건 대입하면 서브
        # 에이전트가 끝날 때마다 그 None 이 발췌를 지워, "마지막으로 **입력한** 프롬프트"라는
        # 발췌의 의미가 깨진다. 턴 상태(running)는 자동주입이든 아니든 갱신해야 하므로 위에 둔다.
        if event.prompt_excerpt is not None:
            session.task_excerpt = event.prompt_excerpt
    elif event.hook_event_name == "Stop":
        session.turn_state = "ended"
    elif event.hook_event_name == "SessionEnd":
        session.ended_at_ms = event.received_at_ms
    elif event.hook_event_name == "SessionStart":
        # 재부착(resume·startup·clear)은 "이 세션이 다시 살아났다"는 유일한 권위 있는 신호다
        # (결정 RV1, docs/prps/hub-session-revival-and-stale-tier1.md). compact 는 이 함수에
        # 도달하지 못한다(build_session_facts 의 필터가 is_internal_session_start 로 앞서
        # continue 한다) — 그 필터가 곧 부활 오발동을 막는 안전판이다.
        session.ended_at_ms = None
    elif event.hook_event_name == "SubagentStart":
        _handle_subagent_start(session, event)
    elif event.hook_event_name == "SubagentStop":
        _handle_subagent_stop(session, event)


def _new_session_builder(event: HookEvent) -> _MutableSession:
    return _MutableSession(
        cwd=event.cwd,
        observed_cwds=[],
        started_at_ms=event.received_at_ms,
        last_event_at_ms=event.received_at_ms,
        last_event_name=event.hook_event_name,
        turn_state="ended",
        ended_at_ms=None,
        task_excerpt=None,
        subagents={},
        known_agent_ids=set(),
    )


def _freeze_session(session_id: str, session: _MutableSession) -> SessionFacts:
    subagents = tuple(
        SubagentFact(
            agent_id=agent_id,
            agent_type=sub.agent_type,
            started_at_ms=sub.started_at_ms,
            ended_at_ms=sub.ended_at_ms,
        )
        for agent_id, sub in session.subagents.items()
    )
    return SessionFacts(
        session_id=session_id,
        cwd=session.cwd,
        observed_cwds=tuple(session.observed_cwds),
        started_at_ms=session.started_at_ms,
        last_event_at_ms=session.last_event_at_ms,
        last_event_name=session.last_event_name,
        turn_state=session.turn_state,
        ended_at_ms=session.ended_at_ms,
        task_excerpt=session.task_excerpt,
        subagents=subagents,
    )


def build_session_facts(events: Sequence[HookEvent]) -> dict[str, SessionFacts]:
    """시간순 이벤트 목록을 세션별 사실로 접는다. 내부 이벤트 필터를 여기서 적용한다."""
    builders: dict[str, _MutableSession] = {}
    for event in events:
        session = builders.get(event.session_id)
        if session is None:
            session = _new_session_builder(event)
            builders[event.session_id] = session
        session.last_event_at_ms = event.received_at_ms
        session.last_event_name = event.hook_event_name
        # observed_cwds 누적은 내부 이벤트 필터보다 앞이다(결정 WT19) — cwd 도 필터 이전
        # (빌더 생성 시점)에 정해지므로 두 값의 모집단이 같아 observed_cwds[0] == cwd 가
        # 언제나 참이다. 내부 이벤트(compact 등)도 실제로 관측된 cwd 이므로 여기서 놓치면
        # 안 된다(U-29).
        if event.cwd not in session.observed_cwds:
            session.observed_cwds.append(event.cwd)

        is_filtered = is_internal_session_start(event) or is_untracked_internal_subagent_stop(
            event, frozenset(session.known_agent_ids)
        )
        if is_filtered:
            continue
        _apply_tracked_event(session, event)
    return {
        session_id: _freeze_session(session_id, session)
        for session_id, session in builders.items()
    }


# ---- 세션 표시 상태 ----
# 서브에이전트가 API 오류 등으로 죽으면 SubagentStop 훅이 발화하지 않는다(실측 E1·E5 — 3일간
# 고아 18건, docs/prps/hub-zombie-subagent-guard.md). 그 좀비 1건이 세션을 영구히 working 으로
# 붙잡는 것을 막는 나이 상한이다. 90분의 근거: 3일간 완료된 정상 실행 90건의 최장이 47.3분
# (p90 18.4분)이며, 90분은 그 1.9배다(결정 ZG2 의 표). 상한을 넘긴 실행은 "죽었다"가 아니라
# "지금 돌고 있다는 근거가 없다"로 본다.
SUBAGENT_ZOMBIE_AFTER_MS = 90 * 60 * 1000


def is_running_subagent(subagent: SubagentFact, now_ms: int, zombie_after_ms: int) -> bool:
    """지금 실제로 돌고 있다고 볼 수 있는 실행인가 — 이미 끝났거나 좀비면 False."""
    if subagent.ended_at_ms is not None:
        return False
    return (now_ms - subagent.started_at_ms) < zombie_after_ms


# `done` = `SessionEnd` 를 관측했고, 그 뒤로 재부착(`SessionStart`, compact 제외)을 보지
# 못했다(결정 RV3, docs/prps/hub-session-revival-and-stale-tier1.md). `done` 은 여전히
# `stale` 로 덮이지 않는 터미널 표시이지만, 터미널인 것은 표시일 뿐 사실이 아니다 — 세션은
# 되살아날 수 있고, 되살아나면 `done` 은 취소된다(_apply_tracked_event 의 SessionStart 분기가
# ended_at_ms 를 해제한다).
#
# `working` = 메인 턴이 진행 중이거나(`turn_state == "running"`), 또는 `SubagentStop` 없이
# 시작 후 `SUBAGENT_ZOMBIE_AFTER_MS`(90분) 이내인 서브에이전트가 하나라도 있다(결정 ZG7). 90분을
# 넘긴 미종료 실행은 실행 근거에서 제외한다 — 죽었다고 단정하는 것이 아니라, 지금 돌고 있다는
# 근거로 인정하지 않는다는 뜻이다. 같은 술어가 서브에이전트 칩의 `is_running` 도 결정하므로,
# 상태와 칩은 어긋날 수 없다.
def _compute_base_state(
    facts: SessionFacts, now_ms: int, zombie_after_ms: int
) -> Literal["working", "idle", "done"]:
    if facts.ended_at_ms is not None:
        return "done"
    has_running_subagent = any(
        is_running_subagent(sub, now_ms, zombie_after_ms) for sub in facts.subagents
    )
    if facts.turn_state == "running" or has_running_subagent:
        return "working"
    return "idle"


def compute_session_view(
    facts: SessionFacts,
    now_ms: int,
    stale_after_ms: int,
    zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS,
) -> SessionView:
    """우선순위 사다리(done > working > idle) + stale 오버레이로 표시 상태를 정한다."""
    base_state = _compute_base_state(facts, now_ms, zombie_after_ms)
    is_stale = base_state != "done" and (now_ms - facts.last_event_at_ms) >= stale_after_ms
    agent_runs = summarize_agent_runs(facts, now_ms, zombie_after_ms)
    return SessionView(
        session_id=facts.session_id,
        short_id=facts.session_id[:SHORT_ID_LENGTH],
        state="stale" if is_stale else base_state,
        base_state=base_state,
        last_event_at_ms=facts.last_event_at_ms,
        task_excerpt=facts.task_excerpt,
        agent_runs=agent_runs,
    )


# ---- 서브에이전트 요약 ----
def summarize_agent_runs(
    facts: SessionFacts, now_ms: int, zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS
) -> tuple[SubagentRunView, ...]:
    """세션의 서브에이전트를 타입별로 합쳐, 실행 중 타입을 먼저 두고 그 다음 최근 시작 순으로
    돌려준다(종료된 것도 포함).

    실행 중 우선순위(결정 K2)는 클라이언트의 칩 상한(결정 K1)이 "+N" 오버플로 칩 없이도
    지금 진행 중인 작업을 놓치지 않게 하기 위한 것이다 — 정렬 키가 전부 결정적이므로
    snapshot_content_key 안정성(결정 D2)에는 영향이 없다. `is_running` 은 `_compute_base_state`
    와 같은 술어(`is_running_subagent`)를 쓴다 — 좀비 실행은 여기서도 실행 중으로 보지 않는다
    (결정 ZG1·ZG4, 상태와 칩이 어긋나지 않게 하는 구조적 장치).
    """
    latest_started_at_ms: dict[str, int] = {}
    is_running_by_type: dict[str, bool] = {}
    for sub in facts.subagents:
        if not sub.agent_type:
            continue
        latest_started_at_ms[sub.agent_type] = max(
            latest_started_at_ms.get(sub.agent_type, sub.started_at_ms), sub.started_at_ms
        )
        is_running_by_type[sub.agent_type] = (
            is_running_by_type.get(sub.agent_type, False)
            or is_running_subagent(sub, now_ms, zombie_after_ms)
        )
    ordered_types = sorted(
        latest_started_at_ms,
        key=lambda agent_type: (
            0 if is_running_by_type[agent_type] else 1,
            -latest_started_at_ms[agent_type],
            agent_type,
        ),
    )
    return tuple(
        SubagentRunView(
            agent_type=agent_type,
            phase=PHASE_BY_AGENT_TYPE.get(agent_type),
            is_running=is_running_by_type[agent_type],
        )
        for agent_type in ordered_types
    )
