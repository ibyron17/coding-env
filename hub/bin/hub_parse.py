"""hub_parse.py — /dashboard 생성물(.claude/dashboard.html)의 DOM 계약을 읽는 순수 파서.

이 모듈은 파일시스템·시각·환경에 닿지 않는다(★순수, tests/hub/test_hub_parse.py 대상).
파싱 대상은 commands/dashboard.md 의 불변식 2·5(요소는 한 줄에 하나씩)를 따르는 셀렉터뿐이다.
로그 항목(#dz-log 의 <li>)은 여러 줄에 걸쳐 있어 파싱하지 않는다 — docs/prps/hub-dashboard.md
쟁점 1 참조. 실패는 예외가 아니라 None 이다(호출자가 티어를 강등한다).
"""

import re
from dataclasses import dataclass
from typing import Literal

StepState = Literal["done", "active", "wait"]

# file_mtime_ms 는 이 모듈이 채우지 않는다(파일시스템 접근은 순수 레이어의 경계 밖이다).
# I/O 레이어(hub_collect.py)가 stat 으로 얻은 실제 mtime 을 dataclasses.replace 로 덮어쓴다.
UNSET_FILE_MTIME_MS = 0


@dataclass(frozen=True)
class StepView:
    """선형 진행 표시의 단계 하나(#dz-step-{n})."""

    index: int
    name: str
    state: StepState
    detail: str
    started_at: str | None


@dataclass(frozen=True)
class Tier1Snapshot:
    """/dashboard DOM 에서 읽은 진행 상태 전체."""

    title: str
    subtitle: str
    completed: int
    total: int
    percent: int
    steps: tuple[StepView, ...]
    matrix_done: int | None
    impl_done: int
    impl_total: int
    updated_text: str
    file_mtime_ms: int


_TITLE_PATTERN = re.compile(r'<h1 id="dz-title">(?P<text>.*?)</h1>')
_SUBTITLE_PATTERN = re.compile(r'<div class="sub" id="dz-subtitle">(?P<text>.*?)</div>')
_PROGRESS_PATTERN = re.compile(
    r'<div class="pct" id="dz-progress-pct">'
    r"(?P<completed>\d+)/(?P<total>\d+)\s*·\s*(?P<percent>\d+)%</div>"
)
_UPDATED_PATTERN = re.compile(r'id="dz-updated">(?P<text>.*?)</div>')

_STEP_LINE_PATTERN = re.compile(
    r'<li id="dz-step-(?P<index>\d+)" class="(?P<state>done|active|wait)"'
    r'(?:\s+data-started-at="(?P<started_at>[^"]*)")?>'
    r'<span class="num">\d+</span>(?P<name>.*?)<span class="chip">.*?</span>'
    # .step-detail 이 이 기능 도입 이전 세대의 대시보드에는 존재하지 않는다(검수 m3) — 선택 그룹으로 둔다.
    r'(?:<span class="step-detail">(?P<detail>.*?)</span>)?</li>'
)

_IMPL_LINE_PATTERN = re.compile(
    r'<li id="dz-impl-(?P<index>\d+)" class="(?P<state>done|active|wait)">'
    r'<span class="num">\d+</span>(?P<name>.*?)<span class="chip">.*?</span>'
    r'<span class="step-detail">(?P<detail>.*?)</span></li>'
)

_CELL_LINE_PATTERN = re.compile(
    r'<td class="cell" id="dz-cell-(?P<group>\d+)-(?P<col>\d+)"'
    r' data-state="(?P<state>done|active|wait|na)">(?P<text>.*?)</td>'
)


def _parse_steps(text: str) -> tuple[StepView, ...]:
    """선형 모드(#dz-step-{n})의 단계 목록을 문서 순서대로 돌려준다."""
    steps = []
    for match in _STEP_LINE_PATTERN.finditer(text):
        steps.append(
            StepView(
                index=int(match["index"]),
                name=match["name"].strip(),
                state=match["state"],
                detail=match["detail"] or "",
                started_at=match["started_at"],
            )
        )
    return tuple(steps)


def _count_matrix_done(text: str) -> int | None:
    """매트릭스 모드(#dz-cell-{g}-{p})의 완료 칸 수. 칸이 없으면 None(선형 모드)."""
    states = [match["state"] for match in _CELL_LINE_PATTERN.finditer(text)]
    if not states:
        return None
    return sum(1 for state in states if state == "done")


def _count_impl_progress(text: str) -> tuple[int, int]:
    """「구현」 세부 작업(#dz-impl-{k})의 (완료 수, 전체 수)."""
    impl_states = [match["state"] for match in _IMPL_LINE_PATTERN.finditer(text)]
    done = sum(1 for state in impl_states if state == "done")
    return done, len(impl_states)


def parse_dashboard_html(text: str) -> Tier1Snapshot | None:
    """/dashboard 생성물의 DOM 계약대로 진행 상태를 읽는다. 계약이 안 맞으면 None."""
    title_match = _TITLE_PATTERN.search(text)
    progress_match = _PROGRESS_PATTERN.search(text)
    updated_match = _UPDATED_PATTERN.search(text)
    if not (title_match and progress_match and updated_match):
        return None

    subtitle_match = _SUBTITLE_PATTERN.search(text)
    impl_done, impl_total = _count_impl_progress(text)

    return Tier1Snapshot(
        title=title_match["text"],
        subtitle=subtitle_match["text"] if subtitle_match else "",
        completed=int(progress_match["completed"]),
        total=int(progress_match["total"]),
        percent=int(progress_match["percent"]),
        steps=_parse_steps(text),
        matrix_done=_count_matrix_done(text),
        impl_done=impl_done,
        impl_total=impl_total,
        updated_text=updated_match["text"],
        file_mtime_ms=UNSET_FILE_MTIME_MS,
    )
