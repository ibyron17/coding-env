"""hub_project.py — 프로젝트를 발견하고 세션 뷰·티어 1 스냅샷을 프로젝트 뷰로 합성하는 순수 로직.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_project.py 대상).
디렉토리명 인코딩은 **정방향 전용**이다(역방향 디코딩은 원리적으로 모호하다 —
docs/prps/hub-dashboard.md). 세대 판정(tier1_is_previous_task)의 근거는
docs/prps/hub-session-revival-and-stale-tier1.md 결정 GN1~GN3 이 정본이다.
"""

import fnmatch
import hashlib
from dataclasses import dataclass
from typing import Literal, Sequence

from hub_parse import Tier1Snapshot
from hub_session import SessionFacts, SessionState, SessionView, compute_session_view

DASHBOARD_KEY_LENGTH = 16          # sha256(경로) 앞 자리 수 — 대시보드 서빙용 불투명 키(결정 N1)
# 프로젝트 루트 기준 .claude/dashboard.html 의 상대경로. 정본은 여기 하나뿐이다 —
# hub_collect.py(I/O) 는 이 값을 pathlib 조인에, 이 모듈은 문자열 접합에 그대로 재사용한다
# (검수 m3: hub_collect 가 이미 hub_project 를 import 하므로 중복 선언을 없앨 수 있다).
# 앞에 "/" 를 붙이지 않는다 — 붙이면 pathlib 의 `/` 연산자가 뒤 조각을 절대경로로 취급해
# 앞부분을 통째로 버리는 함정에 걸린다(예: 루트 / 슬래시로 시작하는 조각).
PROJECT_DASHBOARD_RELATIVE_PATH = ".claude/dashboard.html"

# 앞이 이긴다 — 하나라도 working 이면 프로젝트는 working.
PROJECT_STATE_PRIORITY: tuple[SessionState, ...] = ("working", "idle", "stale", "done")

# 살아 있는 세션 = 지금 이 프로젝트에서 실제로 일하고 있는 세션(결정 GN2,
# docs/prps/hub-session-revival-and-stale-tier1.md). stale·done 을 넣지 않는다 — 부활 규칙(RV1)이
# 만드는 좀비 stale 세션이 세대 판정(is_tier1_from_previous_task)을 조용히 깨뜨린다(실측 E6).
LIVE_SESSION_STATES: frozenset[SessionState] = frozenset({"working"})


# ---- 표시(view) ----
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


# ---- 프로젝트 발견 — 정방향 인코딩 전용 ----
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


# ---- 프로젝트 합성 ----
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
