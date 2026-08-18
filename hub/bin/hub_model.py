"""hub_model.py — 이벤트 → 세션 사실 → 표시 상태로 접는 순수 로직.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_model.py 대상).
`now_ms` 는 항상 인자로 받는다 — 테스트가 시계에 의존하지 않게 하기 위해서다.
상태 판정 규칙의 근거는 docs/prps/hub-dashboard.md 「상태 판정 규칙」 절이 정본이다.
"""

import fnmatch
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal, Sequence

from hub_parse import Tier1Snapshot
from hub_usage import RateLimitResets, UsageSample

SessionState = Literal["working", "idle", "stale", "done"]
Phase = Literal["설계", "구현", "검수"]

SHORT_ID_LENGTH = 8
DASHBOARD_KEY_LENGTH = 16          # sha256(경로) 앞 자리 수 — 대시보드 서빙용 불투명 키(결정 N1)
# 프로젝트 루트 기준 .claude/dashboard.html 의 상대경로. 정본은 여기 하나뿐이다 —
# hub_collect.py(I/O) 는 이 값을 pathlib 조인에, 이 모듈은 문자열 접합에 그대로 재사용한다
# (검수 m3: hub_collect 가 이미 hub_model 을 import 하므로 중복 선언을 없앨 수 있다).
# 앞에 "/" 를 붙이지 않는다 — 붙이면 pathlib 의 `/` 연산자가 뒤 조각을 절대경로로 취급해
# 앞부분을 통째로 버리는 함정에 걸린다(예: 루트 / 슬래시로 시작하는 조각).
PROJECT_DASHBOARD_RELATIVE_PATH = ".claude/dashboard.html"

PHASE_BY_AGENT_TYPE: dict[str, Phase] = {
    "design-architect": "설계",
    "implementer": "구현",
    "code-reviewer": "검수",
}

# 앞이 이긴다 — 하나라도 working 이면 프로젝트는 working.
PROJECT_STATE_PRIORITY: tuple[SessionState, ...] = ("working", "idle", "stale", "done")

# 살아 있는 세션 = 지금 이 프로젝트에서 실제로 일하고 있는 세션(결정 GN2,
# docs/prps/hub-session-revival-and-stale-tier1.md). stale·done 을 넣지 않는다 — 부활 규칙(RV1)이
# 만드는 좀비 stale 세션이 세대 판정(is_tier1_from_previous_task)을 조용히 깨뜨린다(실측 E6).
LIVE_SESSION_STATES: frozenset[SessionState] = frozenset({"working"})

_DATA_MARKER_OPEN = '<script type="application/json" id="dzh-data">'
_DATA_MARKER_CLOSE = "</script>"


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


@dataclass(frozen=True)
class HubConfig:
    """~/.claude/hub/config.json 이 없으면 전부 이 기본값을 쓴다."""

    roots: tuple[str, ...] = ()
    ignore_globs: tuple[str, ...] = (
        "**/.claude/worktrees/**",
        "/tmp/**",
        "/private/tmp/**",
    )
    scan_depth: int = 3
    stale_after_minutes: int = 30
    event_retention_days: int = 7
    record_prompt_excerpt: bool = True
    server_port: int = 8794                        # 상주 서버 고정 포트(북마크 가능해야 한다)
    server_collect_interval_seconds: int = 5       # 수집 루프 주기
    show_usage_panel: bool = True                  # false 면 사용량 파일을 아예 읽지 않는다(결정 U4)
    usage_api_enabled: bool = False                # 사용량 API 폴링 스위치, 기본 off(결정 A6 — 옵트인)
    usage_api_poll_interval_seconds: int = 300     # 폴링 기본 주기(5분, 결정 A3)


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


@dataclass(frozen=True)
class ProjectView:
    """프로젝트 하나의 화면 표시 상태 — 소속 세션과 티어 1 스냅샷을 합성한 것."""

    display_name: str
    path: str | None
    tier: Literal[1, 2, 3]
    state: SessionState
    last_activity_at_ms: int
    sessions: tuple[SessionView, ...]
    tier1: Tier1Snapshot | None
    note: str | None
    dashboard_key: str | None = None    # 티어 1 프로젝트만 값을 갖는다. None 이면 카드가 클릭 대상이 아니다
    # 티어 1 파일이 "지금 일하는 세션보다 오래된" 세대인가(결정 GN1~GN3).
    # 이름에 stale 을 쓰지 않는다 — 세션의 stale(30분 무소식)·사용량의 is_stale(조회되지 않음)과
    # 뜻이 다르다.
    tier1_is_previous_task: bool = False


@dataclass(frozen=True)
class HubSnapshot:
    """허브 페이지 하나에 인라인되는 전체 데이터."""

    collected_at_ms: int
    projects: tuple[ProjectView, ...]
    unresolved_dir_names: tuple[str, ...]
    warnings: tuple[str, ...]
    usage: UsageSample | None = None    # statusLine 캡처(rate_limits.json)의 투영. 없으면 패널을 그리지 않는다(만료는 is_stale 로 표시된다)
    rate_limit_resets: RateLimitResets | None = None    # 없으면 초기화 예정 시각 줄을 그리지 않는다


# ---- 상주 서버 (개정 1 rev2) ----
@dataclass(frozen=True)
class ServerRecord:
    """server.json 의 내용 — 서버 자신이 bind 성공 직후 1회 쓴다."""

    pid: int
    port: int
    started_at_ms: int


@dataclass(frozen=True)
class ServerStatus:
    """`/hub server status` 의 보고 단위."""

    record: ServerRecord | None
    process_present: bool
    heartbeat_age_ms: int | None
    alive: bool
    http_ok: bool
    crashed_evidence: bool
    log_tail: str | None
    orphaned_evidence: bool                        # 하트비트는 살아 있는데 server.json 이 없다(검수 m1)
    collect_stalled: bool                          # 프로세스는 살아 있는데 수집 스레드만 죽었다(검수 M2)


# ---- 브라우저 열기 (재기동 + 포커스, docs/prps/hub-server-control-skill.md) ----
@dataclass(frozen=True)
class BrowserOpenResult:
    """브라우저 열기 시도의 결과. `focus_requested` 는 '포그라운드로 올리는 경로를 썼다'는
    뜻이며, 실제로 창이 올라왔는지는 OS 소관이라 확인하지 않는다.

    `fallback_reason` 이 필요한 이유: macOS 에서 탭은 떴는데 창이 뒤에 남는 상황이 이 기능이
    고치려는 증상이다. 폴백이 조용히 일어나면 사용자는 "고쳐졌다더니 그대로"만 보게 된다 —
    이 필드가 그 원인을 표면화하는 유일한 창구다.
    """

    opened: bool                       # URL 을 여는 데 성공했는가
    focus_requested: bool              # 포커스를 가져오는 경로(/usr/bin/open)로 열었는가
    # 포커스 경로 실패 사유 또는(포커스 경로가 없던 플랫폼이면) webbrowser 예외. 정상이면 None
    fallback_reason: str | None


# ---- 1. 내부 이벤트 필터 ----
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


# ---- 2. 세션 사실 접기 ----
@dataclass
class _MutableSubagent:
    agent_type: str
    started_at_ms: int
    ended_at_ms: int | None


@dataclass
class _MutableSession:
    cwd: str
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


# ---- 3. 세션 표시 상태 ----
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


# ---- 4. 서브에이전트 요약 ----
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


# ---- 5. 프로젝트 발견 — 정방향 인코딩 전용 ----
def encode_project_dir_name(absolute_path: str) -> str:
    """절대경로를 ~/.claude/projects 의 디렉토리명으로 인코딩한다(정방향 전용)."""
    encoded_characters = []
    for character in absolute_path:
        encoded_characters.append("-" if character in "/." else character)
    return "".join(encoded_characters)


def resolve_project_dirs(
    encoded_names: Sequence[str], candidate_paths: Sequence[str]
) -> tuple[dict[str, str], tuple[str, ...]]:
    """인코딩 디렉토리명 → 절대경로 매칭 결과와, 매칭되지 않은 이름들을 돌려준다."""
    encoded_to_path = {encode_project_dir_name(path): path for path in candidate_paths}
    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for name in encoded_names:
        if name in encoded_to_path:
            resolved[name] = encoded_to_path[name]
        else:
            unresolved.append(name)
    return resolved, tuple(unresolved)


def should_ignore_cwd(cwd: str, ignore_globs: Sequence[str]) -> bool:
    """cwd 가 무시 패턴(worktree·scratchpad 등)에 해당하는지 판정한다."""
    return any(fnmatch.fnmatch(cwd, pattern) for pattern in ignore_globs)


# ---- 6. 프로젝트 합성 ----
def _display_name(path: str) -> str:
    trimmed = path.rstrip("/")
    return trimmed.rsplit("/", 1)[-1] if trimmed else path


def _project_tier(tier1: Tier1Snapshot | None, sessions: tuple[SessionFacts, ...]) -> int:
    if tier1 is not None:
        return 1
    return 2 if sessions else 3


def _project_state_without_sessions(last_activity_at_ms: int, now_ms: int, stale_after_ms: int) -> SessionState:
    """세션이 하나도 없는 프로젝트(티어 1/3 전용)의 상태.

    `done` 은 `SessionEnd` 를 관측했고 그 뒤 재부착(`SessionStart`, compact 제외)이 없을
    때만 성립하는 상태다(결정 RV3) — 세션이 없으면 그 근거가 없으므로 마지막 활동 시각만으로
    idle/stale 을 가른다(검수 M3, docs/prps/hub-dashboard.md 「상태 판정 규칙 4」 참조).
    """
    if now_ms - last_activity_at_ms >= stale_after_ms:
        return "stale"
    return "idle"


def _project_state(
    session_views: tuple[SessionView, ...], last_activity_at_ms: int, now_ms: int, stale_after_ms: int
) -> SessionState:
    if not session_views:
        return _project_state_without_sessions(last_activity_at_ms, now_ms, stale_after_ms)
    ranked = sorted(session_views, key=lambda view: PROJECT_STATE_PRIORITY.index(view.state))
    return ranked[0].state


def _last_activity_at_ms(
    tier1: Tier1Snapshot | None, session_views: tuple[SessionView, ...], tier3_mtime: int
) -> int:
    candidates = [tier3_mtime]
    if tier1 is not None:
        candidates.append(tier1.file_mtime_ms)
    candidates.extend(view.last_event_at_ms for view in session_views)
    return max(candidates)


def project_dashboard_key(project_path: str) -> str:
    """프로젝트 절대경로 → 대시보드 서빙용 불투명 키(sha256 앞 16자리 hex, 결정 N1).

    `encode_project_dir_name` 과 달리 서로 다른 두 경로가 같은 키가 되는 충돌이 실질적으로
    없고, 문자 집합이 `[0-9a-f]` 뿐이라 경로로 오독될 여지가 없다.
    """
    digest = hashlib.sha256(project_path.encode("utf-8")).hexdigest()
    return digest[:DASHBOARD_KEY_LENGTH]


def is_tier1_from_previous_task(
    tier1_file_mtime_ms: int, live_session_start_times_ms: Sequence[int]
) -> bool:
    """살아 있는 세션이 있고, 그 전부가 대시보드 파일이 갱신된 뒤에 시작됐는가(결정 GN1).

    경계는 엄격한 `>` 다 — 같은 밀리초에 시작·갱신됐다면 그 세션이 갱신했다고 본다.
    `all()` 은 한 세션이라도 대시보드보다 먼저 시작했으면 라벨을 켜지 않는다(오탐 회피 방향).
    """
    if not live_session_start_times_ms:
        return False
    return all(start_ms > tier1_file_mtime_ms for start_ms in live_session_start_times_ms)


def _live_session_start_times_ms(
    sessions: tuple[SessionFacts, ...], session_views: tuple[SessionView, ...]
) -> tuple[int, ...]:
    """살아 있는 세션들의 시작 시각. 표시 상태는 뷰가, 시작 시각은 사실이 갖고 있다.

    `sessions` 와 `session_views` 는 `compose_project_views` 안에서 같은 순서로 만들어지므로
    `zip` 이 안전하다 — 두 튜플을 함수 밖으로 넘겨 다시 조립하지 않는다.
    """
    return tuple(
        facts.started_at_ms
        for facts, view in zip(sessions, session_views)
        if view.state in LIVE_SESSION_STATES
    )


def compose_project_views(
    tier1_by_path: dict[str, Tier1Snapshot],
    sessions_by_path: dict[str, tuple[SessionFacts, ...]],
    tier3_last_activity_by_path: dict[str, int],
    now_ms: int,
    stale_after_ms: int,
) -> tuple[ProjectView, ...]:
    """세 티어의 사실을 프로젝트별로 합성해 화면 표시 뷰를 만든다. 정렬은 마지막 활동 내림차순."""
    all_paths = set(tier1_by_path) | set(sessions_by_path) | set(tier3_last_activity_by_path)
    views = []
    for path in all_paths:
        tier1 = tier1_by_path.get(path)
        sessions = sessions_by_path.get(path, ())
        session_views = tuple(
            compute_session_view(facts, now_ms, stale_after_ms) for facts in sessions
        )
        live_session_start_times_ms = _live_session_start_times_ms(sessions, session_views)
        tier1_is_previous_task = tier1 is not None and is_tier1_from_previous_task(
            tier1.file_mtime_ms, live_session_start_times_ms
        )
        last_activity_at_ms = _last_activity_at_ms(
            tier1, session_views, tier3_last_activity_by_path.get(path, 0)
        )
        tier = _project_tier(tier1, sessions)
        views.append(
            ProjectView(
                display_name=_display_name(path),
                path=path,
                tier=tier,
                state=_project_state(session_views, last_activity_at_ms, now_ms, stale_after_ms),
                last_activity_at_ms=last_activity_at_ms,
                sessions=session_views,
                tier1=tier1,
                note=None,
                dashboard_key=project_dashboard_key(path) if tier == 1 else None,
                tier1_is_previous_task=tier1_is_previous_task,
            )
        )
    return tuple(sorted(views, key=lambda view: view.last_activity_at_ms, reverse=True))


def build_dashboard_registry(snapshot: HubSnapshot) -> dict[str, str]:
    """스냅샷에서 {대시보드 키: dashboard.html 절대경로} 를 만든다. 티어 1 프로젝트만 담는다.

    서버(hub_server.py)가 요청 경로의 키를 이 딕셔너리에서만 조회하므로, 값은 전부 이 함수가
    실제로 발견한 프로젝트 경로에서 나온다 — 요청 문자열이 경로 조립에 쓰이는 지점이 없다(결정 N3).
    """
    registry: dict[str, str] = {}
    for project in snapshot.projects:
        if project.tier != 1:
            continue
        registry[project_dashboard_key(project.path)] = project.path + "/" + PROJECT_DASHBOARD_RELATIVE_PATH
    return registry


# ---- 7. 상주 서버 (개정 1 rev2) ----
SERVER_HEARTBEAT_TTL_MULTIPLIER = 3      # 수집 주기의 3배까지는 살아 있다고 본다
SERVER_HEARTBEAT_MIN_TTL_SECONDS = 15    # 주기를 아주 짧게 잡아도 하한을 둔다
MILLISECONDS_PER_SECOND = 1000


def server_heartbeat_ttl_ms(collect_interval_seconds: int) -> int:
    """하트비트를 '살아 있음'으로 인정하는 최대 나이(ms)."""
    ttl_seconds = max(
        collect_interval_seconds * SERVER_HEARTBEAT_TTL_MULTIPLIER,
        SERVER_HEARTBEAT_MIN_TTL_SECONDS,
    )
    return ttl_seconds * MILLISECONDS_PER_SECOND


def is_server_alive(now_ms: int, heartbeat_mtime_ms: int | None, ttl_ms: int) -> bool:
    """하트비트 나이로 상주 서버 생존을 판정한다. 파일이 없으면 False."""
    if heartbeat_mtime_ms is None:
        return False
    return (now_ms - heartbeat_mtime_ms) < ttl_ms


def parse_server_record(text: str) -> ServerRecord | None:
    """server.json 텍스트를 판다. 깨졌거나 필드가 없으면 None(예외를 던지지 않는다).

    hub_daemon.py(신원 확인·kill 경로)와 hub_collect.py(read_server_record)가 둘 다 이
    함수를 쓴다 — 예전에는 두 곳에 같은 로직이 따로 있어(순환 임포트를 피하려는 시도),
    실제 운영 경로(hub_collect.read_server_record)가 테스트 대상(hub_daemon 사본)과
    달라지는 위험이 있었다(검수 m3). 둘 다 이미 hub_model 을 임포트하므로 순환이 없다.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return ServerRecord(
            pid=int(payload["pid"]),
            port=int(payload["port"]),
            started_at_ms=int(payload["started_at_ms"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def should_spawn_collect(
    now_ms: int,
    server_alive: bool,
    hub_html_mtime_ms: int | None,
    spawn_stamp_mtime_ms: int | None,
    throttle_ms: int,
) -> bool:
    """훅이 재수집을 spawn 해야 하는가. 서버가 살아 있으면 항상 False(수집 위임).

    `hub_html_mtime_ms` 가 없을 때(서버가 아직/다시는 hub.html 을 만들지 못한 상태)도 서버가
    죽어 있으면 True 를 돌려준다(검수 M2-5) — 예전에는 이 경우 무조건 False 라, 상주 서버가
    HUB_HOME 쓰기 불가 등으로 hub.html 을 한 번도 못 만든 채 수집 스레드까지 죽으면 훅 폴백
    조차 영원히 뚫리지 않는 이중 실패였다(실측: 서버는 HTTP 로 계속 응답해 `server_alive` 는
    이미 이 함수 호출 전 단계에서 False 로 판정되지만, hub.html 부재가 이어지면 사용자는
    영구히 빈 페이지만 본다). `spawn_stamp` 로는 여전히 쓰로틀한다 — 스탬프가 없으면(첫
    시도) 곧바로 True.
    """
    if server_alive:
        return False
    if hub_html_mtime_ms is None:
        if spawn_stamp_mtime_ms is None:
            return True
        return (now_ms - spawn_stamp_mtime_ms) >= throttle_ms
    reference_mtime_ms = (
        spawn_stamp_mtime_ms if spawn_stamp_mtime_ms is not None else hub_html_mtime_ms
    )
    return (now_ms - reference_mtime_ms) >= throttle_ms


# ---- 9. 사용량 API 폴링 스케줄 (R1, 순수) ----
USAGE_API_BACKOFF_MAX_MULTIPLIER = 12          # 기본 5분 기준 상한 60분
USAGE_API_RATE_LIMITED_MULTIPLIER = 12         # 429 는 곧바로 상한(결정 A3)


@dataclass(frozen=True)
class UsageApiPollState:
    """사용량 API 폴링의 스케줄 상태. 수집 루프의 지역 변수로만 산다(전역 상태 금지, 결정 A3)."""

    last_attempt_at_ms: int | None = None
    consecutive_failures: int = 0
    forced_multiplier: int | None = None        # 429 가 요구한 즉시 상한


def usage_api_poll_delay_ms(state: UsageApiPollState, base_interval_seconds: int) -> int:
    """다음 시도까지 기다릴 시간(ms). 연속 실패마다 2배, 상한까지(결정 A3 — 5→10→20→40→60분).

    `consecutive_failures` 가 0·1 이면 배수는 1(기본 주기 그대로) — 첫 실패 직후에는 아직
    백오프를 태우지 않는다. `forced_multiplier`(429 특례)가 있으면 지수 계산을 건너뛰고
    그 배수를 곧바로 쓴다 — 가장 강한 "그만 보내라" 신호에 가장 강하게 반응한다.
    """
    if state.forced_multiplier is not None:
        multiplier = state.forced_multiplier
    else:
        multiplier = min(2 ** max(state.consecutive_failures - 1, 0), USAGE_API_BACKOFF_MAX_MULTIPLIER)
    return base_interval_seconds * multiplier * MILLISECONDS_PER_SECOND


def should_attempt_usage_api_poll(
    now_ms: int, state: UsageApiPollState, base_interval_seconds: int
) -> bool:
    """지금 사용량 API 를 호출해도 되는가. 첫 시도(last_attempt_at_ms 가 None)는 항상 True."""
    if state.last_attempt_at_ms is None:
        return True
    delay_ms = usage_api_poll_delay_ms(state, base_interval_seconds)
    return (now_ms - state.last_attempt_at_ms) >= delay_ms


def next_usage_api_poll_state(
    now_ms: int, state: UsageApiPollState, failure_reason: str | None
) -> UsageApiPollState:
    """시도 결과를 반영한 **새** 상태를 돌려준다(원본은 불변). 성공(`failure_reason is None`)
    이면 실패 카운트를 0 으로 되돌린다. `http_rate_limited` 는 곧바로 상한 배수로 점프한다
    (결정 A3) — 그 외 실패 사유는 지수 백오프 카운터만 늘린다.
    """
    if failure_reason is None:
        return UsageApiPollState(last_attempt_at_ms=now_ms, consecutive_failures=0, forced_multiplier=None)
    forced_multiplier = USAGE_API_RATE_LIMITED_MULTIPLIER if failure_reason == "http_rate_limited" else None
    return UsageApiPollState(
        last_attempt_at_ms=now_ms,
        consecutive_failures=state.consecutive_failures + 1,
        forced_multiplier=forced_multiplier,
    )


def snapshot_content_key(snapshot: HubSnapshot) -> str:
    """collected_at_ms 를 제외한 스냅샷 내용의 안정적 키. 같으면 hub.html 을 다시 쓰지 않는다."""
    content = asdict(snapshot)
    content.pop("collected_at_ms", None)
    return json.dumps(content, sort_keys=True, ensure_ascii=False)


# ---- 8. 렌더링 ----
def render_hub_html(template: str, snapshot: HubSnapshot) -> str:
    """템플릿의 데이터 마커를 스냅샷 JSON 으로 치환한다. 순수 — 파일을 쓰지 않는다."""
    payload = json.dumps(asdict(snapshot), ensure_ascii=False)
    # <script type="application/json"> 내부는 raw text 다 — HTML 실체 참조(엔티티)는 브라우저가
    # 복원해 주지 않아 JSON.parse 가 그 리터럴 문자열을 그대로 반환하는 버그가 된다(검수 M1).
    # </script> 주입을 막으면서 JSON.parse 에서 원문 그대로 복원되게 하려면 JSON 자체가 정의하는
    # 유니코드 이스케이프(\uXXXX)를 써야 한다.
    escaped_payload = (
        payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )
    start = template.index(_DATA_MARKER_OPEN) + len(_DATA_MARKER_OPEN)
    end = template.index(_DATA_MARKER_CLOSE, start)
    return template[:start] + escaped_payload + template[end:]
