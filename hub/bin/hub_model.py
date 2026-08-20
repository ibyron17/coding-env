"""hub_model.py — 허브 스냅샷 계약(HubSnapshot·HubConfig)과 그 직렬화·렌더(순수).

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_model.py 대상).
여기 있는 것은 **대외 계약**뿐이다 — HubSnapshot 은 hub_template.html 의 #dzh-data 와,
HubConfig 는 ~/.claude/hub/config.json 과 맺은 계약이며, render_hub_html 이 전자를 HTML 에
새기는 유일한 지점이다. 계산은 hub_session·hub_project·hub_server_state·hub_usage 에 있다
(분리 근거: docs/prps/hub-model-module-split.md 결정 MS1).
"""

import json
from dataclasses import asdict, dataclass

from hub_parse import UNSET_SOURCE_PATH
from hub_project import PROJECT_DASHBOARD_RELATIVE_PATH, ProjectView, project_dashboard_key
from hub_usage import RateLimitResets, UsageSample

_DATA_MARKER_OPEN = '<script type="application/json" id="dzh-data">'
_DATA_MARKER_CLOSE = "</script>"


# ---- 입력 ----
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


# ---- 표시(view) ----
@dataclass(frozen=True)
class HubSnapshot:
    """허브 페이지 하나에 인라인되는 전체 데이터."""

    collected_at_ms: int
    projects: tuple[ProjectView, ...]
    unresolved_dir_names: tuple[str, ...]
    warnings: tuple[str, ...]
    usage: UsageSample | None = None    # statusLine 캡처(rate_limits.json)의 투영. 없으면 패널을 그리지 않는다(만료는 is_stale 로 표시된다)
    rate_limit_resets: RateLimitResets | None = None    # 없으면 초기화 예정 시각 줄을 그리지 않는다


def build_dashboard_registry(snapshot: HubSnapshot) -> dict[str, str]:
    """스냅샷에서 {대시보드 키: dashboard.html 절대경로} 를 만든다. 티어 1 프로젝트만 담는다.

    서버(hub_server.py)가 요청 경로의 키를 이 딕셔너리에서만 조회하므로, 값은 전부 이 함수가
    실제로 발견한 프로젝트 경로에서 나온다 — 요청 문자열이 경로 조립에 쓰이는 지점이 없다(결정 N3).
    """
    registry: dict[str, str] = {}
    for project in snapshot.projects:
        if project.tier != 1 or project.tier1 is None:
            continue
        # 불변식: tier==1 인 project.tier1 은 항상 hub_collect._read_tier1_for_root 가
        # dataclasses.replace 로 source_path 를 채운 결과다(hub_parse.UNSET_SOURCE_PATH 로
        # 남지 않는다, 결정 WT7·WT8). 그 계약이 깨지면 "" + "/" + PROJECT_DASHBOARD_RELATIVE_PATH
        # 라는 엉뚱한 경로가 조립되므로, 값이 비어 있는 경우는 등록하지 않는다(방어적 제외).
        source_path = project.tier1.source_path
        if source_path == UNSET_SOURCE_PATH:
            continue
        registry[project_dashboard_key(project.path)] = source_path + "/" + PROJECT_DASHBOARD_RELATIVE_PATH
    return registry


def snapshot_content_key(snapshot: HubSnapshot) -> str:
    """collected_at_ms 를 제외한 스냅샷 내용의 안정적 키. 같으면 hub.html 을 다시 쓰지 않는다."""
    content = asdict(snapshot)
    content.pop("collected_at_ms", None)
    return json.dumps(content, sort_keys=True, ensure_ascii=False)


# ---- 렌더링 ----
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
