# 통합 허브 대시보드 (PRP)

> 문서 형식은 이 레포의 기존 PRP 관례(`session-dashboard.md` 계열)를 따른다.
> `/prp-plan` 의 템플릿(Task 목록·Validation Commands)은 「구현 마일스톤」·「검증 명령」 절로 흡수했다.

> ## 개정 이력
>
> | 판 | 날짜 | 상태 | 내용 |
> |----|------|------|------|
> | 초판 | 2026-08-10 | 구현·검수 3회 완료, 커밋 `2d34c8a` | 3티어 수집 · 서버리스 훅 · 읽기 전용 페이지 |
> | ~~개정 1 rev1~~ | 2026-08-11 | **반려** | launchd LaunchAgent · README/install.sh 통합 — 아래 rev2 § 「rev1 반려 사유」 |
| **개정 1 rev2** | 2026-08-11 | **설계 · 승인 대기** | **서버 상시화**(세션 무관 분리 프로세스) + **문서 분리**(`hub/README.md`) + **설치 분리**(`hub/install.sh`) |
>
> **초판 본문은 그대로 둔다.** 개정 1이 무효화하거나 교체하는 서술에는 해당 위치에
> `> **[개정 1로 무효]**` / `> **[개정 1로 교체]**` 표시를 달았다 — 표시가 없는 서술은 전부 유효하다.
> 개정 내용의 정본은 문서 끝의 **「개정 1 — 서버 상시화」** 절이다.

---

## 요구사항 요약

로컬 머신에서 돌고 있는 **모든 Claude Code 프로젝트**의 진행 상황(프로젝트 / 세션 / 단계)을
한 페이지에서 **읽기 전용**으로 보는 통합 허브를 만든다. 사용자는 Claude Desktop 앱과 Cursor 확장을
주로 쓰며(터미널 CLI 아님), 여러 프로젝트를 동시에 진행하는 동안 창을 옮겨 다니지 않고 한 화면에서
"어디가 돌고 있고 / 어디가 멈춰 있고 / 각각 어느 단계인지"를 알고 싶다.

명령·제어 기능은 범위 밖이다(중단·프롬프트 주입·승인은 인접 프로젝트 CAM 의 2단계 몫이다).
허브는 **파일에서 기계적으로 읽을 수 있는 사실만** 집계하고, 상주 서버(데몬)를 두지 않는다.

> **[개정 1로 무효]** 마지막 문장의 "상주 서버(데몬)를 두지 않는다"는 폐기됐다. 개정 1은
> **사용자가 명시적으로 켜고 끄는 상주 서버**를 도입한다. "읽기 전용 · 명령 제어 없음 ·
> 기계적으로 읽히는 사실만 집계"라는 나머지 범위 제약은 **그대로 유지된다** — 상주화되는 것은
> 갱신 주체이지 허브의 권한이 아니다. 정본: 「개정 1 — 서버 상시화」 § 개정 요구사항.

---

## 영향 범위

### 신규 파일

| 파일 | 줄 수(예상) | 역할 |
|------|------------|------|
| `hub/bin/hub.py` | ~150 | CLI 엔트리. 서브커맨드(`collect`/`open`/`serve`/`stop`/`install-hooks`/`uninstall-hooks`/`status`) 디스패치와 I/O 조립 |
| `hub/bin/hub_model.py` | ~200 | **★순수.** 이벤트 → 세션 사실 → 표시 상태, 단계 추정, 경로 인코딩 매칭, 프로젝트 합성 |
| `hub/bin/hub_parse.py` | ~120 | **★순수.** `dashboard.html` 텍스트 → `Tier1Snapshot` (줄 단위 정규식) |
| `hub/bin/hub_collect.py` | ~180 | I/O. 프로젝트 발견 · 3티어 읽기 · 스냅샷 조립 · `hub.html` 원자적 쓰기 |
| `hub/bin/hub_hook.py` | ~70 | 훅 엔트리. stdin 이벤트 1줄 append + 쓰로틀 재수집. **항상 exit 0** |
| `hub/bin/hub_settings.py` | ~140 | `~/.claude/settings.json` 병합 설치/제거(백업 + 원자적 교체 + 멱등) |
| `hub/bin/hub_template.html` | ~260 | 허브 페이지 골격(`<style>` + `<script>` + 데이터 마커). 데이터는 여기에 인라인된다 |
| `commands/hub.md` | ~120 | `/hub` 커맨드. **얇은 지시문** — 어떤 파이썬 서브커맨드를 어떤 순서로 부르고 무엇을 보고할지 |
| `tests/hub/test_hub_parse.py` | ~140 | `hub_parse` 단위 테스트(stdlib `unittest`) |
| `tests/hub/test_hub_model.py` | ~220 | `hub_model` 단위 테스트 |
| `tests/hub/fixtures/*.html` | — | 실제 `dashboard.html` 사본 4종(선형 / 매트릭스 / impl 있음 / 옛 세대) |
| `docs/prps/hub-dashboard.md` | — | 이 문서 |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `install.sh` | `HUB_FILE_COUNT=7` 상수 추가, `target_hub_dir` 해석(**`--scope user` 전용**), `check_no_symlink_targets`·`check_directory_conflict`·`install_directory` 각 1줄, manifest `files_count.hub`, dry-run 계획 1줄, 완료 합계 조건부 가산, `COMMANDS_FILE_COUNT` 8 → 9 |
| `tests/run.sh` | 커맨드 개수 기대값 8 → 9(T17 목록에 `hub` 추가), `total_tests` 22 → 24, 신규 T24(파이썬 단위 테스트 실행)·T25(허브 문서·상수 정합성) |
| `README.md` | 커맨드 표 1행, "의존 사슬 7종 + 독립 커맨드 1종" → "**독립 커맨드 2종**", `/hub` 설명 단락(프라이버시 고지 포함), 디렉토리 트리에 `hub/` |
| `CLAUDE.md` | **수정하지 않는다** (아래 「미영향」 참조) |
| `commands/dashboard.md` | **선택 1줄** — 데이터 모델 절에 "이 DOM 계약에는 외부 읽기 소비자(`/hub`)가 있다. 불변식 2·5(요소 1줄 1개)를 깨면 허브 파서가 조용히 티어를 강등한다"는 고지. 절차·템플릿은 한 글자도 바꾸지 않는다 |

### 미영향 (건드리지 않는 이유)

- **`CLAUDE.md`** — 허브는 워크플로우 단계에 개입하지 않는다. `/dashboard` 처럼 "착수 시 init, 전환 시 step" 같은 트리거가 없고, 사용자가 보고 싶을 때 열어 보는 관측 도구다. 워크플로우 지침에 넣으면 매 세션이 부담해야 하는 규칙이 하나 늘어난다.
- **`agents/`** — 서브에이전트는 허브 파일에 접근하지 않는다(아래 설계 결정 7).
- **`rules/`** — 코드 품질 기준 계층이며 워크플로우 산출물과 무관.
- **`commands/dashboard.md` 의 절차·템플릿** — 쟁점 1의 결론에 따라 `/dashboard` 의 계약은 **읽기만** 한다.

---

## 파일 구조와 모듈 경계

### 레이어

| 레이어 | 실체 | 책임 | 외부 세계 접촉 |
|--------|------|------|---------------|
| 지시문 | `commands/hub.md` | 어떤 서브커맨드를 언제 부르고 무엇을 보고할지 | 없음(LLM 이 읽는다) |
| 엔트리 | `hub.py` · `hub_hook.py` | 인자·stdin 해석, 조립, 보고, 종료 코드 | 프로세스 경계 |
| I/O | `hub_collect.py` · `hub_settings.py` | 파일 발견·읽기·쓰기, `settings.json` 병합, 서버 기동 | **여기에만 있다** |
| 순수 | `hub_model.py` · `hub_parse.py` | 파싱·상태 판정·단계 추정·경로 매칭 | **없음. 단위 테스트 대상** |
| 표현 | `hub_template.html` → `~/.claude/hub/hub.html` | 인라인된 JSON 을 렌더 | 브라우저 |

레이어 간 통신은 아래 「데이터 모델」의 `dataclass` 로만 한다. 순수 레이어는 파일시스템·시각·환경변수를
읽지 않는다(`now_ms` 는 인자로 받는다) — 그래서 테스트가 시계에 의존하지 않는다.

### 런타임 배치

```
~/.claude/hub/
├── bin/                    # install.sh 소유 (배포물). 사용자 데이터가 섞이지 않는다
│   ├── hub.py  hub_model.py  hub_parse.py  hub_collect.py  hub_hook.py  hub_settings.py
│   └── hub_template.html
├── config.json             # 선택. 없으면 전부 기본값
├── events/YYYY-MM-DD.jsonl # 티어 2 이벤트 로그 (append-only, 날짜별)
└── hub.html                # 생성물. 사용자가 브라우저로 여는 유일한 파일
```

**`bin/` 격리가 핵심이다.** `install.sh` 는 `diff -rq` 로 "우리가 배포한 파일이 대상에서 수정됐는가"를
판정하는데(소유권 원칙), 소스와 런타임 데이터가 같은 디렉토리에 있으면 `events/`·`hub.html` 이 매번
`Only in target` 으로 나타난다. 지금 로직은 그걸 무시하도록 이미 작성돼 있지만(`list_missing_managed_files`
는 `Only in <source>` 만 본다), 소스 트리와 가변 데이터를 섞는 배치는 앞으로의 어떤 검증 강화도
깨뜨린다. 한 단 내리는 비용으로 그 위험이 사라진다.

---

## 데이터 모델

### 티어 3 계층 구조 — 프로젝트마다 "가진 것 중 가장 높은 티어"로 표시한다

| 티어 | 출처 | 얻는 것 | 없으면 |
|------|------|--------|-------|
| 1 | `<프로젝트>/.claude/dashboard.html` | 제목·단계별 상태·상세·진행률·구현 세부 진행 | 티어 2로 강등 |
| 2 | `~/.claude/hub/events/*.jsonl` | 세션 목록·working/idle/stale/done·단계 **추정**·작업 발췌 | 티어 3으로 강등 |
| 3 | `~/.claude/projects/<인코딩>/*.jsonl` 의 **mtime** | 마지막 활동 시각뿐 | 그 프로젝트는 목록에 없다 |

**티어 3에서 파일 내용은 절대 열지 않는다.** 비공개 포맷이라 버전에 취약하다(CAM 의 "내부 파일 파싱
금지" 절대 규칙과 같은 판단). 읽는 것은 파일 이름(= `session_id`)과 mtime 둘뿐이다.

> **실측 (2026-08-10)**: `~/.claude/projects/<dir>` 의 **디렉토리 mtime 은 쓸 수 없다.** coding-env
> 디렉토리 mtime 은 `17:56` 인데 그 안의 세션 `*.jsonl` 은 `18:16` 이었다 — 기존 파일에 append 해도
> 디렉토리 엔트리는 바뀌지 않기 때문이다. 그래서 티어 3의 마지막 활동 시각은 **`maxdepth 1` 의
> `*.jsonl` mtime 최댓값**으로 정의한다. 이 한 줄이 티어 3을 쓸모 없는 것에서 쓸모 있는 것으로 바꾼다.

### 이벤트 스키마 (티어 2) — `events/YYYY-MM-DD.jsonl` 한 줄

기록하는 필드는 **화면에 실제로 쓰이는 것만**이다. 훅 페이로드의 나머지(`transcript_path`,
`permission_mode`, `last_assistant_message`, `agent_transcript_path`, `prompt_id`)는 기록하지 않는다 —
쓰지 않는 데이터를 남기면 파일이 커지고 유출 표면만 넓어진다.

```jsonc
{"t":1786000000123,"e":"UserPromptSubmit","s":"9dbd335d-…","c":"/Users/byron/private/project/coding-env","p":"허브 대시보드 설계해줘"}
{"t":1786000005001,"e":"SubagentStart","s":"9dbd335d-…","c":"/Users/…/coding-env","ai":"agt_01…","at":"design-architect"}
{"t":1786000900500,"e":"SessionEnd","s":"9dbd335d-…","c":"/Users/…/coding-env","r":"prompt_input_exit"}
```

| 키 | 원 필드 | 있는 이벤트 | 비고 |
|----|--------|-----------|------|
| `t` | (writer 생성) | 전부 | 수신 시각 epoch ms. **훅 실행 시각이 곧 이벤트 시각**이다 |
| `e` | `hook_event_name` | 전부 | |
| `s` | `session_id` | 전부 | 티어 3의 파일명과 같은 키다 |
| `c` | `cwd` | 전부 | **프로젝트 식별의 정본** — 인코딩 역변환이 필요 없는 정확한 절대경로 |
| `so` | `source` | `SessionStart` | `startup`\|`resume`\|`clear`\|`compact`\|`fork` |
| `r` | `reason` | `SessionEnd` | |
| `ai` | `agent_id` | `Subagent*` | 서브에이전트 추적 키(타입이 아니다 — 같은 타입 동시 다중 가능) |
| `at` | `agent_type` | `Subagent*` | 빈 문자열이 실존한다(아래 필터 규칙) |
| `p` | `prompt` | `UserPromptSubmit` | **`PROMPT_EXCERPT_MAX=120` 자로 절단.** `config.record_prompt_excerpt=false` 면 생략 |

키를 짧게 쓰는 이유는 미학이 아니다 — **한 줄이 짧아야 동시 append 가 안전하다.** 여러 세션의 훅이
같은 파일에 동시에 쓰는데, `O_APPEND` 로 연 파일에 대한 **1회 `write()`** 는 짧은 길이에서 사실상
원자적이다. 그래서 (a) 반드시 한 번의 `write()` 로 개행까지 쓰고, (b) `p` 를 절단해 줄 길이 상한을
확보하고, (c) 읽는 쪽은 깨진 줄을 **조용히 건너뛴다.**

### 허브 상태 모델 (순수 레이어의 타입)

```python
# ---- 입력 ----
@dataclass(frozen=True)
class HookEvent:
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
    roots: tuple[str, ...] = ()                     # 기본값: 스캔하지 않는다 (아래 쟁점 4)
    ignore_globs: tuple[str, ...] = (
        "**/.claude/worktrees/**", "/tmp/**", "/private/tmp/**")
    scan_depth: int = 3
    stale_after_minutes: int = 30
    event_retention_days: int = 7
    record_prompt_excerpt: bool = True
    serve_port_candidates: tuple[int, ...] = (8794, 8795, 8796)

# ---- 사실(fact) ----
@dataclass(frozen=True)
class SubagentFact:
    agent_id: str
    agent_type: str
    started_at_ms: int
    ended_at_ms: int | None

@dataclass(frozen=True)
class SessionFacts:
    session_id: str
    cwd: str
    started_at_ms: int
    last_event_at_ms: int
    last_event_name: str
    turn_state: Literal["running", "ended"]
    ended_at_ms: int | None                          # SessionEnd 수신 시점. 이후 터미널
    task_excerpt: str | None                         # 마지막 UserPromptSubmit 의 발췌
    subagents: tuple[SubagentFact, ...]

# ---- 표시(view) ----
SessionState = Literal["working", "idle", "stale", "done"]
Phase = Literal["설계", "구현", "검수"]

@dataclass(frozen=True)
class SessionView:
    session_id: str
    short_id: str                                    # 앞 8자
    state: SessionState
    base_state: Literal["working", "idle", "done"]    # stale 일 때 "stale · 직전 working" 병기용
    last_event_at_ms: int
    task_excerpt: str | None
    inferred_phase: Phase | None
    inferred_phase_running: bool
    active_agent_types: tuple[str, ...]
```

> **개정됨.** `inferred_phase`·`inferred_phase_running`·`active_agent_types` 세 필드는
> [`hub-session-activity-and-tooltip.md`](./hub-session-activity-and-tooltip.md) 의
> `agent_runs: tuple[SubagentRunView, ...]` 로 대체됐다(결정 D1·D3).

```python
@dataclass(frozen=True)
class StepView:                                      # 티어 1
    index: int
    name: str
    state: Literal["done", "active", "wait"]
    detail: str
    started_at: str | None                            # "YYYY-MM-DD HH:MM" 원문 그대로

@dataclass(frozen=True)
class Tier1Snapshot:
    title: str
    subtitle: str
    completed: int
    total: int
    percent: int
    steps: tuple[StepView, ...]                       # 매트릭스 세션이면 빈 튜플
    matrix_done: int | None                           # 매트릭스 세션의 완료 칸 수
    impl_done: int
    impl_total: int
    updated_text: str
    file_mtime_ms: int                                # 마지막 활동 시각의 정본(텍스트가 아니라 mtime)

@dataclass(frozen=True)
class ProjectView:
    display_name: str
    path: str | None                                  # 확정된 절대경로. 미확인이면 None
    tier: Literal[1, 2, 3]
    state: SessionState
    last_activity_at_ms: int
    sessions: tuple[SessionView, ...]
    tier1: Tier1Snapshot | None
    note: str | None                                  # 예: "경로 미확인"

@dataclass(frozen=True)
class HubSnapshot:
    collected_at_ms: int
    projects: tuple[ProjectView, ...]
    unresolved_dir_names: tuple[str, ...]
    warnings: tuple[str, ...]                         # 설정 오류·파싱 실패를 화면에 드러낸다
```

`HubSnapshot` 을 그대로 JSON 직렬화한 것이 `hub.html` 에 인라인되는 데이터다. 필드명은 snake_case
그대로 쓴다(생산자와 소비자가 하나뿐이라 변환 계층을 만들 이유가 없다).

---

## 상태 판정 규칙 (전부 순수 함수)

### 1. 내부 이벤트 필터 — 먼저 걸러야 하는 두 가지

CAM 의 930건 전수 실측(`PROJECT_CONTEXT.md` §3.1 M9)이 확정한 사실을 그대로 채택한다.

```python
def is_internal_session_start(event: HookEvent) -> bool:
    """compact 등 CLI 내부 사유로 발생한 SessionStart 인가."""
    return event.hook_event_name == "SessionStart" and event.source == "compact"

def is_untracked_internal_subagent_stop(event: HookEvent, known_agent_ids: frozenset[str]) -> bool:
    """agent_type 이 비어 있고 대응하는 SubagentStart 를 본 적 없는 SubagentStop 인가."""
    return (event.hook_event_name == "SubagentStop"
            and not (event.agent_type or "")
            and (event.agent_id or "") not in known_agent_ids)
```

두 술어가 참이면 **`last_event_at_ms`·`last_event_name` 은 갱신하되 서브에이전트를 만들지 않고
`task_excerpt` 도 건드리지 않는다.** "세션이 아직 살아 있다"(stale 판정의 근거)와 "사용자에게 보여줄
서술"을 분리하는 것이다. `SubagentStart` 를 실제로 관측한 `agent_id` 는 이 규칙에서 절대 제외되지
않는다(오탐 방지 안전판). 이 규칙이 없으면 허브는 위임한 적 없는 작업을 단계 배지로 승격시킨다.

### 2. 세션 표시 상태 — 우선순위 사다리 + stale 오버레이

```python
def compute_session_view(facts: SessionFacts, now_ms: int, stale_after_ms: int) -> SessionView
```

```
base_state:
  1. ended_at_ms is not None                                   → "done"   (터미널)
  2. turn_state == "running" 또는 살아 있는 서브에이전트 존재     → "working"
  3. 그 외                                                      → "idle"

overlay:
  base_state != "done" 이고 now_ms - last_event_at_ms >= stale_after_ms → state = "stale"
  그 외                                                                 → state = base_state
```

- `done` 은 터미널이다 — 시간이 지나도 `stale` 로 덮이지 않는다(끝난 세션에 "소식 없음"은 거짓이다).
- `stale` 이어도 `base_state` 를 함께 실어 UI 가 `stale · 직전 working` 으로 병기한다.
- **`needs_input`(승인 대기) 상태는 만들지 않는다.** CAM 실측(2026-08-04): Desktop·Cursor 의 GUI 승인
  카드는 `Notification(permission_prompt)` 을 발화하지 않는다. 이 사용자는 그 두 표면만 쓰므로,
  그 상태를 만들면 **영원히 켜지지 않는 등불**이 된다(쟁점 2의 결론과 같은 근거).

### 3. 단계 추정 — 서브에이전트 타입 → 단계

> **개정됨.** `infer_phase()` 는 삭제되고 `summarize_agent_runs()` 가 각 서브에이전트 타입에
> `phase` 를 붙인다. "티어 1 이 이긴다"·"매핑되지 않은 타입은 단계로 승격하지 않는다"
> (→ `phase=None`)는 그대로다. **"추정" 라벨 규칙**은 세션 단위 단계를 화면에 띄우는 경우에만
> 적용된다.

```python
PHASE_BY_AGENT_TYPE: dict[str, Phase] = {
    "design-architect": "설계", "implementer": "구현", "code-reviewer": "검수"}

def infer_phase(facts: SessionFacts) -> tuple[Phase | None, bool]:
    """가장 최근에 시작된 '매핑된' 서브에이전트의 단계와 그 실행 여부를 돌려준다."""
```

- 후보는 `PHASE_BY_AGENT_TYPE` 에 있는 타입뿐이다. `Explore`·`general-purpose` 등은 **단계로 승격하지
  않는다**(추정을 넓히면 틀린 단계를 자신 있게 표시한다).
- `started_at_ms` 최댓값 하나만 본다. `ended_at_ms is None` 이면 `running=True`.
- **티어 1이 있으면 티어 1의 단계가 이긴다.** 티어 1은 오케스트레이터가 직접 각인한 **사실**이고
  추정이 아니다. `inferred_phase` 는 티어 2 전용 표시이며 화면에 `추정` 라벨을 반드시 붙인다.

### 4. 프로젝트 합성

```python
PROJECT_STATE_PRIORITY = ("working", "idle", "stale", "done")   # 앞이 이긴다
```

- 프로젝트 상태 = 소속 세션 상태 중 우선순위가 가장 높은 것. 하나라도 working 이면 프로젝트는 working.
- 프로젝트 마지막 활동 = `max(티어1 파일 mtime, 세션 last_event_at 최댓값, 티어3 jsonl mtime 최댓값)`.
- **세션이 0개인 프로젝트(티어 1 전용 또는 티어 3 전용)** — 개정(구현 검수 반영, 메인 세션 승인):
  `done` 으로 판정하지 않는다. `done` 은 **`SessionEnd` 를 실제로 관측한 세션이 하나라도 있을 때만**
  성립하는 상태이기 때문이다(위 「세션 표시 상태」 규칙 그대로). 세션이 없으면 그 근거 자체가 없으므로,
  대신 마지막 활동 시각만으로 `idle`/`stale` 을 가른다: `now_ms - last_activity_at_ms >= stale_after_ms`
  면 `stale`, 아니면 `idle`. 이 규칙이 없으면 방금 활동한 티어 3 전용 프로젝트가 영구히 "완료"로
  보이는 오류가 난다(검수 M3).
- 정렬: **마지막 활동 내림차순** 하나뿐이다. 상태로 정렬하면 상태가 바뀔 때마다 카드가 튄다
  (CAM M9 가 같은 이유로 상태 정렬을 제거했다).

---

## 인터페이스

### 커맨드 호출 규약 — `/hub`

```
/hub                      # 수집 → hub.html 갱신 → 발행(서버 재사용/기동) → 브라우저 열기
/hub install              # 전역 훅 6개 설치 (옵트인, 멱등)
/hub off                  # 전역 훅 제거 (우리 마커가 붙은 엔트리만)
/hub status               # 훅 설치 상태 · 이벤트 파일 · 마지막 수집 시각 보고
/hub serve [포트] | /hub serve stop
```

> **[개정 1로 교체]** `serve` 계열은 **폐기**되고 `/hub server start|stop|status` 로 대체된다.
> 인자 없는 `/hub` 도 더 이상 서버를 암묵 기동하지 않는다. 정본: 「개정 1」 § 개정 쟁점 R2.

`commands/hub.md` 는 **얇다.** 실행할 명령과 보고 문구, 그리고 실패 시의 안내만 담는다.

```bash
python3 "$HOME/.claude/hub/bin/hub.py" open --json     # 결과 요약을 JSON 한 줄로 돌려준다
python3 "$HOME/.claude/hub/bin/hub.py" install-hooks
python3 "$HOME/.claude/hub/bin/hub.py" status --json
```

> **`/dashboard` 와 정반대 배치이며 그 이유는 명확하다.** `/dashboard` 는 *LLM 만이 아는 사실*(지금
> 어느 단계인지, 방금 뭘 지시했는지)을 기록하므로 절차가 지시문이어야 한다. `/hub` 는 *파일에서
> 기계적으로 읽히는 사실*만 집계하므로 절차가 코드여야 한다 — 그래야 (a) 매 갱신이 토큰을 쓰지 않고
> (b) 훅이 사람 없이 스스로 갱신할 수 있다. 후자가 없으면 이 기능의 가치가 대부분 사라진다.

### 훅 커맨드 문자열 (6개 이벤트에 동일하게 설치)

```
python3 "$HOME/.claude/hub/bin/hub_hook.py" >/dev/null 2>&1 || true   # DZH_HUB_HOOK
```

- **`|| true` 는 생략 금지.** `Stop` 훅의 exit 2 는 세션 종료를 블로킹한다(CAM 실측).
- **`>/dev/null` 도 생략 금지.** `UserPromptSubmit` 훅의 stdout 은 세션 컨텍스트로 주입될 수 있다 —
  진단 출력 한 줄이 사용자 프롬프트를 오염시킨다.
- `# DZH_HUB_HOOK` 은 **설치·제거의 유일한 판정 키**다. 커맨드 문자열이 바뀌어도 마커로 찾는다.
- `type` 은 반드시 `"command"` 다. `type:"http"` 는 v2.1.108 에서 발동하지 않음이 실측됐다(CAM).

설치 대상 6개: `SessionStart`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionEnd`.
**`Notification` 은 설치하지 않는다**(위 상태 판정 2의 근거).

### 순수 함수 시그니처 (테스트 대상)

```python
# hub_parse.py
def parse_dashboard_html(text: str) -> Tier1Snapshot | None:
    """/dashboard 생성물의 DOM 계약대로 진행 상태를 읽는다. 계약이 안 맞으면 None."""

# hub_model.py
def parse_event_line(line: str) -> HookEvent | None:
    """이벤트 로그 한 줄을 파싱한다. 깨진 줄은 None (호출자가 건너뛴다)."""
def build_session_facts(events: Sequence[HookEvent]) -> dict[str, SessionFacts]:
    """시간순 이벤트 목록을 세션별 사실로 접는다. 내부 이벤트 필터를 여기서 적용한다."""
def compute_session_view(facts: SessionFacts, now_ms: int, stale_after_ms: int) -> SessionView:
def infer_phase(facts: SessionFacts) -> tuple[Phase | None, bool]:
def encode_project_dir_name(absolute_path: str) -> str:
    """절대경로를 ~/.claude/projects 의 디렉토리명으로 인코딩한다(정방향 전용)."""
def resolve_project_dirs(encoded_names: Sequence[str], candidate_paths: Sequence[str]
                         ) -> tuple[dict[str, str], tuple[str, ...]]:
    """인코딩 디렉토리명 → 절대경로 매칭 결과와, 매칭되지 않은 이름들을 돌려준다."""
def should_ignore_cwd(cwd: str, ignore_globs: Sequence[str]) -> bool:
def compose_project_views(...) -> tuple[ProjectView, ...]:
def render_hub_html(template: str, snapshot: HubSnapshot) -> str:
    """템플릿의 데이터 마커를 스냅샷 JSON 으로 치환한다. 순수 — 파일을 쓰지 않는다."""
```

### 허브 페이지가 읽는 파일 계약

**아무 파일도 읽지 않는다.** 데이터는 페이지 안에 인라인돼 있다.

```html
<script type="application/json" id="dzh-data">{ …HubSnapshot… }</script>
```

- 직렬화 시 `<`·`>`·`&` 를 `<`·`>`·`&` 로 이스케이프한다. 프롬프트 발췌에
  `</script>` 가 들어오면 페이지가 통째로 깨진다 — **이건 가정이 아니라 반드시 막아야 하는 입력**이다.
- 갱신 모드는 `/dashboard` 와 **같은 판정**을 쓴다: `location.protocol` 이 `http(s)` 면 `poll`,
  아니면 `reload`(포커스 복귀 시 `location.reload()`). fetch 성공 여부로 추론하지 않는다.
- `poll` 모드는 자기 URL(`hub.html`)을 5초마다 받아 **파일 전체 문자열을 비교**하고, 달라졌을 때만
  새 JSON 을 꺼내 다시 렌더한다. 라이브 DOM 과 비교하지 않는다(사용자가 접어 둔 카드를 되펴지 않기 위해).
- 경과 시간("6분 전")은 30초마다 인라인된 epoch ms 로 **재계산**한다. 수집이 멈춰도 시간은 정직하다.
- 「수집 시각」을 항상 표시한다 — 허브가 멈췄을 때 그 사실이 화면에 드러나야 한다.

---

## 확정한 쟁점 6가지와 근거

### 쟁점 1 — 티어 1 파싱: **(a) 허브가 DOM 을 직접 파싱한다**

`/dashboard` 의 계약을 **읽기만** 한다. JSON 데이터 블록을 심는 (b) 안은 기각한다.

**(a)를 고른 결정적 근거는 "이미 줄 단위로 grep 가능하게 설계돼 있다"는 것이다.** `dashboard.md` 의
불변식 2·5 는 `<li id="dz-step-…">`·`<td id="dz-cell-…">`·`<li id="dz-impl-…">` 를 **반드시 한 줄에
하나씩** 쓰도록 강제하고, 불변식 3 은 상세에 줄바꿈을 금지한다. 실제 생성물에서 확인했다:

```
123:    <h1 id="dz-title">통합 허브 대시보드 (hub-dashboard)</h1>
126:    <div class="pct" id="dz-progress-pct">0/4 · 0%</div>
128:    <li id="dz-step-1" class="active" data-started-at="2026-08-10 18:12">…<span class="step-detail">…</span></li>
```

즉 파서는 정규식 8개짜리 줄 단위 스캐너로 끝난다. 상태 표현이 **이미 기계 판독용**이므로 두 번째
표현을 만들 이유가 없다.

**(b)를 기각한 이유**: `/dashboard` 의 불변식 7·8 은 "같은 정보의 출처가 둘이 되면 어느 쪽이 정답인지
알 수 없게 된다"를 두 번이나 명문화하고, 실제로 그 이유로 「지금」 카드의 직접 쓰기 경로를 제거했다
(커밋 `a6966aa`). JSON 미러를 심는 것은 정확히 그 실패의 세 번째 사례가 된다. 게다가 미러 유지 비용은
**소비자가 아닌 소유자**가 낸다 — 세션당 수십 번 불리는 `step`·`log`·`impl` 마다 Edit 이 하나 늘고,
그 대상은 자기 화면에 아무 영향이 없다.

**대가와 그 대비**: 허브 파서는 `/dashboard` 의 DOM 계약에 의존한다. 계약이 깨지면 조용히 티어가
강등돼 화면에서 사라질 수 있다. 대응 셋:
1. 파서는 **실패를 예외로 만들지 않는다** — `None` 을 돌려 티어 2로 강등하고 `warnings` 에 사유를 남긴다.
2. `tests/run.sh` T25 가 `dashboard.md` 안에 불변식 2·5 문구가 **여전히 존재하는지** grep 한다
   (두 문서의 계약을 잇는 회귀 테스트).
3. `dashboard.md` 에 소비자 고지 1줄(위 「수정 파일」의 선택 항목).

**파싱하는 것과 하지 않는 것 (YAGNI)**: 파싱 대상은 한 줄에 담긴 것뿐이다 — 제목·부제·진행률·단계
li·매트릭스 칸 수·impl 카운트·갱신 시각. **로그 항목(`#dz-log` 의 `<li>`)은 파싱하지 않는다.**
`<details>`/`<summary>` 로 8줄에 걸쳐 있어 멀티라인 파서가 필요한데, "지금 무슨 일이 일어나는지"는
`active` 단계의 `.step-detail`(한 줄)이 이미 말해 준다. 마지막 활동 시각도 `#dz-updated` 텍스트가 아니라
**파일 mtime** 으로 얻는다(파싱 없음, 더 정확).

### 쟁점 2 — 훅 이벤트 스키마: 6개 이벤트 · 9개 필드 · 날짜별 파일

**어떤 훅인가** (설치 6 / 미설치 1)

| 훅 | 설치 | 이유 |
|----|------|------|
| `UserPromptSubmit` | ✅ | **"턴이 시작됐다"의 유일한 신호.** 이게 없으면 `working` 을 한 번도 표시할 수 없다(CAM M2 가 같은 이유로 추가했다) |
| `Stop` | ✅ | 턴 종료 → `idle` |
| `SessionStart` | ✅ | 세션 등장 + `source` 로 compact 등 내부 시작 판별 |
| `SessionEnd` | ✅ | `done`(터미널) 판정의 유일한 근거 |
| `SubagentStart` | ✅ | `agent_type` 이 100% 채워진다(CAM 실측 150건) → 단계 추정의 입력 |
| `SubagentStop` | ✅ | 단계 종료. 단 `agent_type=""` 필터 필수 |
| `Notification` | ❌ | **Desktop·Cursor GUI 승인 카드는 발화하지 않는다**(CAM 실측 2026-08-04). 이 사용자의 두 표면에서 영원히 안 켜질 등불을 위해 훅 4개(matcher 별)를 심지 않는다 |

**어떤 필드인가**: 위 「이벤트 스키마」 표의 9개. 화면에 쓰이지 않는 필드는 기록하지 않는다.
`prompt` 는 120자 절단 + `config.record_prompt_excerpt` 스위치 + README 프라이버시 고지.
(`~/.claude/projects` 에 이미 전문 트랜스크립트가 평문으로 있으므로 한계적 노출 증가는 작지만,
새 평문 파일을 만드는 사실 자체는 문서에 적는다.)

**파일 레이아웃: 날짜별 1파일** (`events/2026-08-10.jsonl`)

| 대안 | 기각 이유 |
|------|----------|
| 세션별 1파일 | 수백 개의 작은 파일이 쌓이고, 읽는 쪽은 매 갱신마다 전부 열어야 한다(비용이 세션 수에 비례) |
| 단일 파일 | 무한 증가. 리텐션을 하려면 append-only 파일을 다시 써야 하는데, 그 순간 동시 append 와 경합한다 |

날짜별이면 (a) 읽기는 **오늘 + 어제 2파일**로 고정(stale 판정 창 30분을 훨씬 덮는다), (b) 리텐션은
`event_retention_days`(기본 7) 보다 오래된 파일을 **unlink** 하면 끝 — 살아 있는 파일을 절대 다시 쓰지
않는다. 리텐션은 수집 시점에 하루 1회만 수행한다.

### 쟁점 3 — 갱신과 상태 판정: 훅이 갱신하고, 판정은 순수 함수다

> **[개정 1로 부분 교체]** "누가 `hub.html` 을 다시 쓰는가 — 훅이다"는 **서버가 꺼져 있을 때의
> 폴백 경로**로 격하된다. 서버가 켜져 있으면 수집은 **상주 서버가 전담**하고 훅은 append +
> 리텐션만 한다. 「상태 판정 규칙」(working/idle/stale/done, 단계 추정, 티어 1 우선)과 훅의
> `exit 0` 절대 규칙, 원자적 교체, 5초 쓰로틀, 디바운스 스탬프는 **전부 그대로 유효하다**.
> 정본: 「개정 1」 § 개정 쟁점 R3.

**상태 판정 규칙은 위 「상태 판정 규칙」 절이 정본이다**(4종: working/idle/stale/done, `stale_after_minutes`
기본 30, 단계 추정 3종 매핑, 티어 1 우선).

**누가 `hub.html` 을 다시 쓰는가 — 훅이다.** 데몬 없이 자동 갱신을 얻는 유일한 길이다.

```
hub_hook.py:
  1. stdin JSON 파싱 → 필드 투영 → events/<today>.jsonl 에 1줄 append        (항상 수행)
  2. event_retention_days 보다 오래된 이벤트 파일 unlink                     (항상 수행 — 3번보다 먼저)
  3. ~/.claude/hub/hub.html 이 존재하지 않으면 → 종료                        (아직 허브를 안 쓰는 사용자)
  4. hub.html mtime 이 REFRESH_THROTTLE_SEC(5초) 이내면 → 종료               (쓰로틀)
  5. `hub.py collect` 를 분리된 프로세스로 spawn(훅 자신은 기다리지 않는다)
  6. 어떤 경로에서도 exit 0
```

> **개정(구현 검수 반영)**: 최초 설계는 4번에서 재수집을 훅 프로세스 자신이 하고
> `HOOK_BUDGET_MS=400` 초과 시 포기하는 안이었다. 그런데 그 예산 검사는 재수집(비용이 큰 작업)
> **앞**에서 "지금까지 걸린 시간"만 재므로 사실상 항상 통과하는 무효 가드였다(검수 M4). 재수집
> 자체의 소요 시간을 보장할 수 없으면 예산 개념이 성립하지 않는다. 그래서 재수집을 `hub.py collect`
> 서브프로세스로 완전히 떼어내는 안으로 교체했다 — 훅은 항상 append + 리텐션 정리(수 ms)만 지고,
> 원자적 교체(임시파일 → `os.replace`)는 그 자식 프로세스의 책임이다. `HOOK_BUDGET_MS` 는 폐기한다.

- **2번(리텐션)은 3번보다 먼저, hub.html 존재 여부와 무관하게 항상 실행된다.** 리텐션이 재수집
  경로 안에만 있으면 "허브를 끈"(`hub.html` 삭제) 상태에서 이벤트 파일이 무기한 쌓여 "최대 7일"
  고지가 거짓이 된다(검수 M5).
- **3번은 더 이상 off 스위치가 아니다(M2-5 로 정정).** `hub.html` 을 지워도 서버가 죽어 있으면
  훅이 폴백 수집을 spawn 해 복구한다(위 M24b/M24c) — 서버가 하트비트 쓰기 실패 등으로 `hub.html`
  을 한 번도 못 만든 채 수집 스레드까지 죽는 이중 실패를 막기 위한 확장이다. 서버가 살아 있으면
  여전히 위임하므로(M24) 이중 수집은 아니다. 훅 자체를 멈추려면 `/hub off` 로 훅을 제거해야 한다.
- **4번이 비용 상한이다.** 여러 세션이 동시에 돌아도 재수집 프로세스 spawn 은 5초에 한 번뿐이다.
- **5번의 원자적 교체가 필수다.** 동시에 여러 `collect` 프로세스가 겹쳐도(흔치 않지만 가능하다)
  각자 고유한 임시 파일 이름을 써야 한다 — 고정된 임시 파일명을 공유하면 두 프로세스가 같은
  파일을 동시에 쓰다 뒤섞인 내용이 발행될 수 있다(검수 M2). `tempfile.mkstemp` 로 매번 새 이름을
  받는다.
- **6번은 절대 규칙이다.** 훅은 어떤 경우에도 세션을 막지 않는다(`|| true` 는 2차 방어일 뿐이고,
  스크립트 자신이 모든 예외를 삼켜야 한다).

브라우저 쪽 갱신은 `/dashboard` 와 같은 2티어다: `http` → 5초 폴링(파일 전체 문자열 비교),
`file://` → 포커스 복귀 리로드. **`/hub serve` 를 쓰면 다른 프로젝트에서 프롬프트를 입력한 지
5~10초 안에 화면이 스스로 바뀐다** — 사람도 데몬도 개입하지 않는다. 이게 이 설계의 결과물이다.

### 쟁점 4 — 프로젝트 발견: **인코딩은 정방향으로만 쓴다. 역디코딩하지 않는다**

**역변환은 원리적으로 불가능하다** — 실측으로 확인했다:

```
-Users-byron-private-project-claude-agents-manager     ← /Users/byron/private/project/claude-agents-manager
-Users-byron--claude-projects-…                        ← /Users/byron/.claude/projects/…
```

`/` 와 **`.` 가 둘 다** `-` 로 매핑되고(`/.` → `--`), 게다가 `claude-agents-manager` 처럼 하이픈을
포함한 디렉토리명이 실재한다. 다대일 매핑을 역으로 풀면 반드시 존재하지 않는 경로를 지어낸다.

**그래서 정방향 매칭만 한다:**

1. **후보 실경로 집합을 만든다.**
   - (a) 이벤트의 `cwd` 값 전부 — 정확한 절대경로다. **인코딩 문제가 아예 없다.**
   - (b) `config.roots` 를 `scan_depth`(기본 3) 까지 스캔해 `.claude/` 또는 `.git` 을 가진 디렉토리.
2. 후보마다 `encode_project_dir_name(path)` 를 계산해 `~/.claude/projects/<name>` 과 **정확일치** 매칭한다.
3. 매칭되지 않은 인코딩 디렉토리는 **경로를 지어내지 않는다.** `unresolved_dir_names` 에 원본 이름
   그대로 담아 화면 하단에 "미확인 프로젝트 N개"로 접어 둔다. 이게 티어 3의 정직한 한계다.

인코딩 규칙은 **실측으로 확인된 것만** 적는다(절대경로의 `/`·`.` → `-`). 다른 문자에 규칙이 더 있다면
매칭이 실패해 "미확인"으로 남을 뿐, 잘못된 경로를 표시하지 않는다.

**기본값은 `roots: []` 다** — 설정이 없으면 스캔하지 않고 이벤트 `cwd` 만 쓴다. 레포에 특정 사용자의
디렉토리 구조를 하드코딩하지 않고, 훅만 설치하면 즉시 동작한다. `roots` 를 넣으면 "아직 이번 리텐션
창에 세션이 없었던 프로젝트"까지 티어 1/3으로 보인다.

**노이즈 필터가 필요하다는 것도 실측이 말한다**: 현재 `~/.claude/projects` 의 35개 중 **20개가
scratchpad·worktree** 경로다(`/private/tmp/claude-501/…`, `.claude/worktrees/…`). 기본
`ignore_globs` 가 이들을 제외한다. **worktree cwd 를 레포 루트로 병합하는 로직(CAM P5)은 만들지
않는다** — 애초에 제외하기로 했으므로 필요 없다(YAGNI).

### 쟁점 5 — 훅 설치기: install.sh 는 훅을 건드리지 않고, `/hub install` 이 옵트인으로 한다

**`~/.claude/settings.json` 은 `install.sh` 의 소유가 아니다.** `session-dashboard.md` 설계 결정 4가
이미 그 경계를 정했다("install.sh 가 settings.json 소유권을 갖지 않는다"). 배포와 훅 설치를 분리한다:

- `install.sh` → `hub/bin/` 파일만 배포. **훅은 건드리지 않는다.**
- `/hub install` → 훅 6개 설치(명시적 옵트인, 멱등). `/hub off` → 제거.

**병합 절차** (`hub_settings.py`)

1. `settings.json` 을 Read → **JSON 파싱 실패면 즉시 중단**하고 사실만 보고한다. 깨진 파일을 덮어쓰면
   사용자의 권한 허용 목록이 사라진다(`/dashboard on|off` 절차와 같은 판단).
2. `hooks.<이벤트>` 배열에 **matcher 없는 우리 엔트리 1개를 append** 한다. 기존 엔트리는 읽지도 고치지도
   않는다. 이건 선택이 아니라 필수다 — 실측한 현재 상태:

   | 이벤트 | 이미 있는 훅 |
   |--------|-------------|
   | `SessionStart`·`SubagentStart`·`SubagentStop` | CAM(`curl → 127.0.0.1:8790`) |
   | `Stop`·`SessionEnd`·`UserPromptSubmit` | CAM + Litmus(`litmus-hook`, matcher `""`) |
   | `PreToolUse`·`PostToolUse`·`Notification` | Litmus / CAM (우리는 손대지 않는다) |

3. 중복 판정은 **커맨드 문자열의 `DZH_HUB_HOOK` 마커**로 한다. 이미 있으면 아무것도 하지 않고
   "이미 설치됨"을 보고한다(멱등).
4. `settings.json.bak-<ISO타임스탬프>` 백업 후, 임시 파일에 쓰고 `os.replace` 로 **원자적 교체**.
   (홈에 이미 CAM 이 만든 같은 관례의 백업 파일들이 있어 형식을 맞춘다.)
5. 제거는 **마커가 붙은 엔트리만** 삭제한다. 배열이 비면 그 키를 지우고, `hooks` 가 비면 `hooks` 를
   지운다. **CAM·Litmus 훅은 어떤 경우에도 건드리지 않는다.**

`/hub status` 는 6개 이벤트 각각의 설치 여부, 오늘 이벤트 수, 마지막 수집 시각을 한 표로 보고한다.

### 쟁점 6 — 배포: `--scope user` 전용 새 디렉토리 + 새 커맨드 `/hub`

> **[개정 1로 전면 철회]** 아래 「`install.sh` 변경」 5개 항목은 **전부 되돌린다**(요구 R-5).
> 루트 `install.sh` 는 허브를 **전혀 모르게** 되고, 허브는 `hub/install.sh` 로 따로 설치한다.
> 단 `COMMANDS_FILE_COUNT=9` 는 **유지**된다 — `commands/hub.md` 는 커맨드 파일이라 계속 배포된다.
> "허브는 머신 전역 자산"이라는 판단도 유지되며, 이제 `hub/install.sh` 에 `--scope` 가 없다는
> 구조로 강제된다. 정본: 「개정 1 rev2」 § 개정 쟁점 R5.

**`install.sh` 변경**

- `readonly HUB_FILE_COUNT=7`, `readonly COMMANDS_FILE_COUNT=9`(8 → 9).
- `target_hub_dir="$HOME/.claude/hub/bin"` — **`--scope user` 에서만 설치한다.** project scope 에서는
  건너뛰고 한 줄 안내한다. 근거: 허브는 머신 전역 자산이다. 프로젝트마다 사본이 생기면 어느
  `hub.html` 이 정본인지 모호해지고, 훅이 가리킬 경로도 하나여야 한다.
- `check_no_symlink_targets`·`check_directory_conflict`·`install_directory` 에 각 1줄, manifest
  `files_count.hub`(project scope 에서는 0), dry-run 계획 1줄, 완료 합계 조건부 가산.
- `MANIFEST_VERSION` 은 올리지 않는다 — 필드 추가는 기존 소비자(`/env-update`)를 깨지 않는다.
  (`env-update` 절차가 `files_count` 를 해석하는 방식을 확인한 뒤, 깨진다면 그때 올린다.)

**새 커맨드 `/hub` (`commands/hub.md`)** — `/dashboard hub` 서브커맨드 안은 기각한다.
`dashboard.md` 는 이미 1512줄이고 **호출될 때마다 통째로 컨텍스트에 로드된다.** `step` 한 번의 비용에
무관한 기능의 지시문을 얹을 이유가 없다. 두 커맨드는 데이터 방향도 반대다(하나는 쓰고 하나는 읽는다).

**README** — 커맨드 표 1행, "의존 사슬 7종 + 독립 커맨드 1종" → "**독립 커맨드 2종**"(3곳: 표 머리말,
설명 문단, 디렉토리 트리 주석), `/hub` 설명 단락(훅 옵트인 · 프라이버시 고지 · 티어 한계).

> **[개정 1로 축소·이동]** `/hub` 설명 단락과 배포 대상 표의 `hub/bin` 행, 트리의 hub 7줄은
> **`hub/README.md` 로 옮긴다**(요구 R-4). coding-env README 에는 커맨드 표 1행(축약)과 트리 1줄만
> 남기고 둘 다 `hub/README.md` 링크를 단다. "독립 커맨드 2종" 표기는 유지된다(커맨드는 계속
> 배포되므로). 정본: 「개정 1 rev2」 § 개정 쟁점 R4.

> **[개정 1로 교체]** 아래 「`/hub serve` 의 문서 루트」 문단은 임시 디렉토리 + 심볼릭 링크 +
> `python3 -m http.server` 를 전제한다. 개정 1의 상주 서버는 우리가 소유한 프로세스이므로
> **허용 경로 화이트리스트(`/`·`/hub.html`)** 로 대체한다. 포트도 후보 3개 순회가 아니라
> **8794 단일 고정**이다. `events/*.jsonl`·`bin/*.py` 를 노출하지 않는다는 **금지 자체는 유지**된다.
> 정본: 「개정 1」 § 개정 쟁점 R2 · R3.

**`/hub serve` 의 문서 루트** — `~/.claude/hub/` 를 그대로 서빙하지 않는다. `events/*.jsonl`(프롬프트
발췌 포함)과 `bin/*.py` 를 HTTP 로 노출할 이유가 없다. `/dashboard serve` 3단계와 **같은 패턴**으로
임시 디렉토리에 `hub.html` 심볼릭 링크 하나만 두고 `--bind 127.0.0.1` 로 서빙한다. 포트 후보는
**8794·8795·8796** — `/dashboard` 의 8791~8793 과 겹치지 않게 분리한다.

---

## 설계 결정과 근거 (쟁점 밖)

### 1. 실행 코드(python3 stdlib)를 도입한다 — 이 레포 최초

`session-dashboard.md` 설계 결정 1은 "셸 스크립트를 만들지 않는다"였다. 그 근거는 (a) 배포 카운트·소유권
로직 확장, (b) `jq` 의존성이었다. 허브에서는 그 판단이 **뒤집힌다**:

- 허브의 가치는 **사람이 부르지 않아도 갱신되는 것**이다. 훅은 LLM 을 부를 수 없다 → 코드가 필요하다.
- 집계는 프로젝트 수 × 3티어의 파일 읽기다. LLM 이 매 갱신마다 하면 토큰 비용이 화면 한 번 볼 값을
  훨씬 넘고, 결과가 비결정적이다.
- **python3 는 새 의존성이 아니다.** `/dashboard` 의 「자동 발행」이 이미 `python3 -m http.server` 와
  인라인 `python3 -c` 포트 스캐너에 의존한다. 표준 라이브러리만 쓰고 `jq` 는 도입하지 않는다.

### 2. 서버는 정적 파일 서버뿐이다 (상주 프로세스 없음)

> **[개정 1로 무효]** "상주 프로세스 없음"은 폐기됐다. 다만 **CAM 을 재구현하지 않는다**는
> 이 결정의 진짜 근거는 유지된다 — 개정 1의 상주 서버는 WebSocket 도 SQLite 도 명령 제어도
> 없는 **python3 stdlib 정적 서버 + 주기 수집 루프**이며, 관측 대상과 데이터 모델은 초판 그대로다.
> 정본: 「개정 1」 § 개정 쟁점 R1.

허브 프로세스는 "부르면 실행되고 끝나는" 스크립트뿐이다. 상시 데몬 + WebSocket + SQLite 는
**인접 프로젝트 CAM 이 이미 하는 일**이다. coding-env 는 데몬 없는 워크플로우 자산 저장소이고,
같은 것을 두 번 만들면 두 개를 함께 유지해야 한다.

### 3. 상태 파일(JSON 스냅샷)을 따로 두지 않는다

데이터는 `hub.html` 안에 인라인된다. 별도 `snapshot.json` 을 두면 (a) `file://` 에서는 `fetch` 가
막혀 페이지가 읽을 수 없고(그래서 `http`/`file` 두 데이터 경로가 생긴다), (b) 같은 정보의 출처가
둘이 된다. `/dashboard` 의 "DOM 이 곧 상태" 와 같은 판단이며, 폴링도 같은 메커니즘(자기 파일을
받아 문자열 비교)을 그대로 재사용한다. 테스트는 `render_hub_html` 이 순수 함수라 파일 없이 검증한다.

### 4. 디자인 패턴을 도입하지 않는다

Repository·Strategy·플러그인 티어 등록기 같은 구조는 만들지 않는다. 티어는 **3개로 고정**이고 늘어날
계획이 없다(YAGNI). 각 티어는 `hub_collect.py` 의 함수 하나(`read_tier1` / `read_tier2` / `read_tier3`)이고,
합성은 `compose_project_views` 하나다.

### 5. 실패는 전부 "한 티어 낮은 표시"로 처리한다

`/dashboard` 의 「자동 발행」 원칙(실패는 에러가 아니라 폴백)을 그대로 쓴다. 티어 1 파싱 실패 → 티어 2,
이벤트 파일 없음 → 티어 3, `~/.claude/projects` 없음 → 그 프로젝트 없음. 예외를 던지는 경로는
`settings.json` 파싱 실패(사용자 데이터 보호를 위한 의도적 중단) 하나뿐이다.

### 6. 프로젝트별 on/off 스위치를 만들지 않는다

`/dashboard` 는 프로젝트별 `dashboard_enabled` 를 갖지만, 허브는 전역 자산이라 스위치도 전역 하나면
족하다: 훅 설치 여부(`/hub install` / `/hub off`) + `hub.html` 존재 여부(위 쟁점 3의 2번).

### 7. 훅이 이벤트를 쓰는 것은 "서브에이전트 접근 금지" 원칙을 깨지 않는다

`session-dashboard.md` 설계 결정 4의 원칙은 **"서브에이전트가 `.claude/dashboard.html` 을 갱신하지
않는다"** 다. 훅은 서브에이전트가 아니라 **CLI 가 실행하는 외부 프로세스**이고, 쓰는 대상은 프로젝트의
대시보드가 아니라 허브의 이벤트 로그다. 프로젝트 `dashboard.html` 은 오케스트레이터만 쓰고 허브는
**읽기만** 한다 — 원칙은 그대로 유지된다. (이 오해가 리스크이므로 문서에 명시한다.)

---

## 테스트 계획

### 왜 파이썬 테스트를 추가하는가

기존 `tests/run.sh` 는 install.sh 와 마크다운 문서의 정합성을 검증하는 bash 스위트다. 이번에 처음으로
**순수 로직**이 들어오므로 CLAUDE.md 의 "핵심 순수 로직은 단위 테스트를 함께 작성한다"가 적용된다.
stdlib `unittest` 만 쓰고(새 의존성 없음), bash 스위트가 그것을 감싸 실행한다.

### T24 — 파이썬 단위 테스트 (신규)

```bash
python3 -m unittest discover -s tests/hub -t "$REPO_ROOT" -v
```

`tests/run.sh` 는 종료 코드만 검사한다(실패 시 출력을 그대로 흘린다).

#### `test_hub_parse.py` — 티어 1 파서

| TC | 케이스 | 기대 |
|----|--------|------|
| P1 | 실제 선형 대시보드 픅스처 | 제목·부제·`0/4 · 0%`·단계 4개(state/detail/started_at) 정확 |
| P2 | 매트릭스 대시보드 픅스처 | `steps` 는 빈 튜플, `matrix_done` 이 채워짐 |
| P3 | `impl` 목록이 있는 픅스처 | `impl_done`/`impl_total` 정확 |
| P4 | `<style>` 의 `.matrix td.cell[data-state="done"]` 규칙 줄 | **완료 칸으로 세지 않는다**(`id` 접두 매칭 필수 — `dashboard.md` 의 감사 grep 이 같은 함정을 문서화했다) |
| P5 | 로그 항목이 여러 줄에 걸쳐 있는 픅스처 | 파서가 오작동하지 않고 로그를 무시한다 |
| P6 | `dz-now-card` 가 없는 옛 세대 픅스처 | 파싱은 성공하고 없는 필드는 기본값 |
| P7 | 대시보드가 아닌 HTML / 빈 문자열 / 잘린 파일 | `None`(예외를 던지지 않는다) |
| P8 | `.step-detail` 에 이스케이프된 `&lt;T&gt;` | 언이스케이프 없이 그대로 담긴다(렌더가 텍스트로 넣는다) |

#### `test_hub_model.py` — 상태 판정

| TC | 케이스 | 기대 |
|----|--------|------|
| M1 | `SessionStart` → `UserPromptSubmit` | `working` |
| M2 | … → `Stop` | `idle` |
| M3 | … → `SessionEnd` 후 2시간 경과 | **`done` 유지**(stale 로 덮이지 않는다) |
| M4 | 마지막 이벤트 후 31분(임계 30분) | `stale`, `base_state="working"` 보존 |
| M5 | `SessionStart(source="compact")` | `last_event_at` 만 갱신, `task_excerpt` 불변 |
| M6 | `SubagentStop(agent_type="")` + 대응 Start 없음 | **서브에이전트를 만들지 않는다** |
| M7 | `SubagentStop(agent_type="")` + 같은 `agent_id` 의 Start 관측됨 | 정상 종료 처리(안전판) |
| M8 | 같은 `agent_type` 두 개 동시(`agent_id` 다름) | 둘 다 추적, 하나만 끝나도 다른 하나는 running |
| M9 | `design-architect` → 종료 → `implementer` 시작 | `inferred_phase="구현"`, `running=True` → 대체됨(hub-session-activity-and-tooltip.md A1·A4) |
| M10 | `Explore` 만 실행 | `inferred_phase is None` → 대체됨(hub-session-activity-and-tooltip.md A1·A4) |
| M11 | 깨진 JSON 줄 · 필드 누락 줄 | 건너뛰고 나머지로 상태를 만든다 |
| M12 | `encode_project_dir_name("/Users/b/private/project/claude-agents-manager")` | `-Users-b-private-project-claude-agents-manager` |
| M13 | `encode_project_dir_name("/Users/b/.claude/projects/x")` | `-Users-b--claude-projects-x`(`.` → `-`) |
| M14 | 매칭되지 않는 인코딩 디렉토리 | `unresolved` 에 남고 **`path is None`**(경로를 지어내지 않는다) |
| M15 | `should_ignore_cwd` — worktree·`/private/tmp` 경로 | `True` |
| M16 | 프로젝트 상태 합성 — working 1 + done 3 | `working` |
| M17 | 정렬 — 마지막 활동 내림차순 | 상태와 무관하게 시간순 |
| M18 | `render_hub_html` — 발췌에 `</script>` 포함 | 출력에 `</script>` 리터럴이 없다(`<` 이스케이프) |
| M19 | `render_hub_html` — 마커가 정확히 1회 치환됨 | 템플릿의 다른 부분이 변하지 않는다 |
| M20 | 이벤트가 0건인 프로젝트(티어 3만) | `tier=3`, `sessions=()`, 활동 시각은 jsonl mtime |

### T25 — 허브 문서·상수 정합성 (bash, grep 회귀)

| TC | 검증 |
|----|------|
| T25-1 | `install.sh` 의 `HUB_FILE_COUNT` == `ls hub/bin/* \| wc -l` |
| T25-2 | `--scope user` 설치 후 `~/.claude/hub/bin/` 7개 파일 존재, `--scope project` 설치 후 `.claude/hub` **미생성** |
| T25-3 | 훅 마커 `DZH_HUB_HOOK` 가 `hub_settings.py`·`commands/hub.md`·`README.md` 에서 **동일 문자열**로 등장 |
| T25-4 | 훅 커맨드 문자열에 `\|\| true` 와 `>/dev/null` 이 모두 있다(둘 중 하나만 있으면 실패) |
| T25-5 | `commands/hub.md` 에 `type: "http"` 를 쓰지 말라는 근거 문구가 있다 |
| T25-6 | **`commands/dashboard.md` 에 불변식 2·5 문구가 여전히 존재한다** — 티어 1 파서의 전제 |
| T25-7 | `hub_hook.py` 에 `Notification` 문자열이 없다(미설치 결정의 회귀 방지) |
| T25-8 | 포트 후보 `8794` 가 `hub.py`·`commands/hub.md` 에 일치하고, `8791` 을 쓰지 않는다 |
| T25-9 | `README.md` 가 "독립 커맨드 2종"으로 갱신됐다 |
| T25-10 | `hub_model.py`·`hub_parse.py` 에 파일시스템 접근(`open(`·`Path(`·`os.`)이 **없다** — 순수 레이어 경계의 기계적 강제 |

T25-10 이 이 스위트에서 가장 값진 테스트다. "순수 로직 분리"는 문서로 부탁하면 반드시 무너지지만,
grep 한 줄로 강제하면 무너지지 않는다.

### 수동 확인 (자동화 대상 아님)

- `/hub install` 전후 `~/.claude/settings.json` 을 `diff` — 우리 엔트리 6개만 추가되고 CAM·Litmus 훅 무손실.
- `/hub` → 브라우저에서 프로젝트 카드가 티어별로 보이고, 미확인 개수가 표시되는지.
- `/hub serve` 후 **다른 프로젝트** Cursor 창에서 프롬프트 1회 → 5~10초 안에 허브가 스스로 갱신되는지.
- Desktop 앱 세션과 Cursor 확장 세션이 둘 다 잡히는지(표면 무관 동작 확인).
- `/hub off` 후 세션을 계속 써도 이벤트 파일이 더 이상 늘지 않는지.
- 훅 설치 상태에서 세션 종료(`SessionEnd`)가 실제로 `done` 으로 보이는지.

---

## 구현 마일스톤 (단계별 검증 기준)

| M | 범위 | 검증 기준 (통과 못 하면 다음으로 가지 않는다) |
|---|------|--------------------------------------------|
| **M1** | `hub_parse.py` + `hub_model.py` + 픅스처 + 단위 테스트 | `python3 -m unittest discover -s tests/hub` 전부 통과. 픅스처는 실제 `.claude/dashboard.html` 사본 4종 |
| **M2** | `hub_collect.py` + `hub_template.html` + `hub.py collect\|open` | 이 머신에서 `hub.py open` 실행 → `~/.claude/hub/hub.html` 이 생기고, 브라우저에서 프로젝트가 티어별로 보이며 scratchpad 20개가 제외되고 미확인 개수가 표시된다 |
| **M3** | `hub_hook.py` + `hub_settings.py` + `install-hooks`/`uninstall-hooks` | 설치 전후 `settings.json` diff 에 **우리 엔트리 6개만** 추가. 프롬프트 1회 → `events/<today>.jsonl` 에 1줄. `uninstall-hooks` 후 파일이 설치 전과 **동일**(백업 파일 제외) |
| **M4** | `serve`/`stop` + 페이지 폴링·포커스 리로드 | `/hub serve` 후 다른 프로젝트에서 프롬프트 → 10초 내 화면 갱신. `file://` 로 열면 포커스 복귀 시 갱신. 훅 1회 실행 시간이 400ms 를 넘지 않음(`time` 측정) |
| **M5** | `install.sh` · `tests/run.sh` · `README.md` · `commands/hub.md` | `tests/run.sh` 24개 전부 통과. `install.sh --scope user --dry-run` 계획에 `hub/bin` 7개 포함. `--scope project` 는 hub 를 계획하지 않는다 |

> **[개정 1로 교체]** M1~M5 는 초판 구현으로 **전부 완료**됐다(커밋 `2d34c8a`). 단 **M3 의 검증
> 기준은 R3-m3 에 따라 개정한다** — "설치 전과 **동일**" → "설치 전과 **의미적으로 동일**(우리
> 엔트리 제거 후 남는 빈 배열 키의 정리는 허용)". 개정 1의 작업 단위는 아래 「개정 1」 §
> 개정 마일스톤(R-M1~R-M5)이다.

`/prp-implement` 의 검증 루프에 넣을 명령:

```bash
python3 -m unittest discover -s tests/hub -t .      # 순수 로직
python3 -m py_compile hub/bin/*.py                  # 구문
bash tests/run.sh                                   # 설치·문서 정합성
bash -n install.sh                                  # 셸 구문
```

> **린터·포매터**: 이 레포에는 파이썬 도구 설정이 없다. 새 의존성을 도입하지 않기 위해 `ruff`/`black` 을
> 추가하지 않고, 표준 라이브러리로 가능한 `py_compile` 만 게이트로 쓴다. 사용자가 원하면 별건으로 제안한다.

---

## 리스크와 완화책

### 1. 훅이 세션을 막거나 오염시킨다 (가장 심각)

- `|| true`(exit 2 블로킹 차단) + `>/dev/null 2>&1`(**`UserPromptSubmit` 의 stdout 은 컨텍스트로
  주입될 수 있다**) + 스크립트 자체가 모든 예외를 삼키고 항상 exit 0.
- 재수집(프로젝트 수에 비례해 늘어나는 파일 읽기)은 훅 프로세스 자신이 하지 않는다 — `hub.py collect`
  서브프로세스로 spawn 하고 훅은 즉시 반환한다. 훅 자신의 작업은 append + 리텐션 정리(수 ms)뿐이라
  프로젝트가 늘어도 훅 실행 시간은 늘지 않는다(`HOOK_BUDGET_MS` 예산 검사 방식은 재수집 자체의
  소요를 보장하지 못해 폐기했다 — 검수 M4).
- T25-4 가 두 안전장치(`\|\| true`·`>/dev/null`)의 문자열을 회귀 테스트한다.

### 2. 프롬프트 발췌가 평문 파일에 남는다 (프라이버시)

120자 절단 + `config.record_prompt_excerpt: false` 스위치 + README 고지 + 7일 리텐션.
`~/.claude/projects` 에 이미 전문 트랜스크립트가 평문으로 있으므로 한계적 노출은 작지만, **새 파일을
만든다는 사실**은 문서에 적는다. `/hub serve` 가 이 디렉토리를 서빙하지 않는 것(심볼릭 링크 1개만)도
같은 이유다.

### 3. `/dashboard` 의 DOM 계약이 바뀌면 티어 1이 조용히 사라진다

파서 실패 → 예외가 아니라 티어 강등 + `warnings` 표시(화면에 드러난다). T25-6 이 불변식 문구를,
`dashboard.md` 의 선택 1줄이 사람에게 알린다. 최악의 경우 손실은 "티어 2로 표시"이며 허브는 계속 돈다.

### 4. `~/.claude/projects` 인코딩 규칙이 바뀐다

내용을 파싱하지 않으므로 **JSONL 포맷 변경에는 면역**이다. 디렉토리명 규칙이 바뀌면 매칭이 실패해
"미확인 N개"로 드러난다 — 조용히 틀린 경로를 보여주는 실패 모드가 원리적으로 없다.

### 5. 훅 페이로드 필드가 바뀐다

없는 필드는 `None` 으로 들어오고 상태는 한 단 열화된다(`working` 을 못 잡으면 `idle`). 파싱 실패로
세션이 사라지지 않게, `session_id`·`hook_event_name`·`cwd` 세 개만 필수로 두고 나머지는 전부 optional.

### 6. 동시 append 경합

단일 `O_APPEND` 파일에 **1회 `write()`** + 짧은 줄 길이 상한(발췌 120자)으로 사실상 원자성을 얻는다.
읽는 쪽은 깨진 줄을 건너뛰므로 최악의 손실은 이벤트 1건이다. 파일 락은 쓰지 않는다 — 락은 훅을
지연시킬 수 있고(요구사항 1 위반), 얻는 것은 이벤트 1건이다.

### 7. `settings.json` 손상

파싱 실패 시 중단 + 타임스탬프 백업 + `os.replace` 원자적 교체. 마커 기반 제거로 남의 훅을 지우지 않는다.

### 8. 허브가 멈춘 것을 눈치채지 못한다

「수집 시각」을 항상 표시하고, 경과 시간을 브라우저가 30초마다 재계산한다. 페이지가 멈추면 시간이
계속 늘어나 그 사실이 보인다("6분 전"이 "3시간 전"이 된다).

> **[개정 1로 강화]** 상주 서버는 갱신이 없어도 폴링에 응답하므로, 브라우저가 **폴링 성공/실패
> 자체**로 서버 생존을 직접 표시한다("서버 연결됨 · N초 전 확인" / "서버 연결 끊김"). 경과 시간
> 재계산은 그대로 유지된다. 정본: 「개정 1」 § 개정 쟁점 R3 - 화면 표시.

---

## 검토했으나 채택하지 않은 대안

| 대안 | 기각 이유 |
|------|----------|
| 상주 서버(Node/Fastify) + WebSocket + SQLite | **CAM 이 이미 그 아키텍처다.** coding-env 는 데몬 없는 워크플로우 자산 저장소이며, 같은 것을 두 벌 유지할 이유가 없다 |
| `~/.claude/projects/*.jsonl` 내용 파싱 | 비공개 포맷 — 버전 하나에 통째로 깨진다. 파일명·mtime 만으로 필요한 신호(세션 존재·마지막 활동)를 얻는다 |
| `/dashboard` 에 기계용 JSON 블록 심기(쟁점 1의 b) | 같은 상태의 출처가 둘이 된다(불변식 7·8 이 두 번 금지한 실패). 비용을 소비자가 아니라 소유자가 낸다 |
| `type:"http"` 훅 | v2.1.108 에서 발동하지 않음이 실측됨(CAM 2026-08-03) |
| `Notification` 훅 4개 설치 | Desktop·Cursor GUI 승인 카드는 발화하지 않는다(CAM 실측) — 이 사용자의 두 표면에서 켜지지 않는 등불 |
| 별도 `snapshot.json` + 페이지가 `fetch` | `file://` 에서 `fetch` 가 막혀 데이터 경로가 둘로 갈라진다 |
| `~/.claude/projects` 디렉토리명 역디코딩 | `/` 와 `.` 가 모두 `-` 로 매핑돼 원리적으로 모호하다(실측). 정방향 인코딩 + 정확일치로 대체 |
| 세션별 이벤트 파일 | 파일 수가 세션 수만큼 늘고 읽기 비용이 그에 비례한다 |
| `install.sh` 가 훅을 자동 설치 | `settings.json` 은 install.sh 의 소유가 아니다(기존 설계 결정 4). 사용자 훅을 말없이 건드리는 설치기는 신뢰를 잃는다 |
| `/dashboard hub` 서브커맨드 | `dashboard.md`(1512줄)는 호출마다 전량 로드된다. 무관한 기능이 `step` 한 번의 비용을 올린다 |
| worktree cwd → 레포 루트 병합(CAM P5) | worktree·scratchpad 를 애초에 `ignore_globs` 로 제외하기로 했으므로 필요 없다(YAGNI) |
| ~~`serve` 포트 스캔 실패 시 자기가 띄운 Popen 핸들을 유지하고 terminate() 하는 안(검수 R1 nit)~~ | **[개정 1로 무의미]** `serve` 자체가 폐기되고, 프로세스 생명주기는 `hub_daemon.py` 의 PID + `ps` 신원 확인이 관리한다 — 이 항목은 더 이상 판단 대상이 아니다 |
| `events/`·`hub/` 디렉토리를 0o700 으로 제한(검수 R1 nit m7/m10) | 프라이버시 리스크는 이미 120자 절단 + 7일 리텐션 + `record_prompt_excerpt` 스위치로 완화돼 있다. 기존에 다른 권한으로 이미 존재하는 디렉토리에 사후 chmod 를 적용하는 경우까지 고려하면 범위가 넓어져 별건으로 미룬다 |

---

## 워크플로우 경로 판정

**전체 경로(설계 → 구현 → 검수) 대상이다.** 근거 4개 각각이 단독으로 요건을 충족한다:

- 새 모듈/레이어 추가(`hub/bin/` — 이 레포 최초의 실행 코드)와 디렉토리 구조 변경
- 새 공개 인터페이스(`/hub` 커맨드, 훅 커맨드 문자열, 이벤트 스키마, `config.json`)
- 12개 신규 + 4개 수정 파일
- **민감 영역**: `~/.claude/settings.json`(다른 도구의 훅과 공존) 수정과 사용자 프롬프트의 평문 기록

---

## 사용자 승인이 필요한 핵심 결정

1. **이 레포에 처음으로 실행 코드(python3 stdlib)를 들인다** — 데몬 없는 자동 갱신을 얻는 유일한 길이고,
   python3 는 `/dashboard` 가 이미 의존하는 도구다. 대가는 `install.sh`·테스트 스위트의 확장이다.
2. **훅은 `install.sh` 가 아니라 `/hub install` 이 옵트인으로 설치하고, 프롬프트 발췌 120자가
   `~/.claude/hub/events/` 에 평문으로 7일간 남는다**(`config` 로 끌 수 있음).
3. **티어 1은 `/dashboard` 의 DOM 을 읽기만 한다** — `dashboard.md` 의 계약·절차는 바꾸지 않고,
   대신 파싱 실패를 티어 강등으로 흡수하며 불변식 문구를 T25-6 이 감시한다.

---
---

# 개정 1 (rev2) — 서버 상시화 · 문서 분리 · 설치 분리 (2026-08-11)

> 이 절이 개정 1 의 **정본**이다. 초판 본문과 충돌하는 서술이 있으면 이 절이 이긴다.
> 초판의 충돌 지점에는 각각 `> **[개정 1로 …]**` 표시를 달아 두었다.
> **rev1 은 반려됐다** — 아래 「rev1 반려 사유와 rev2 의 변경점」 참조.

## rev1 반려 사유와 rev2 의 변경점

| 쟁점 | rev1(반려) | rev2 | 사유 |
|------|-----------|------|------|
| 상시화 메커니즘 | launchd LaunchAgent (`RunAtLoad`+`KeepAlive`) | **세션 무관 분리 프로세스**(`start_new_session=True`) | "상시"의 의미가 **재부팅 생존이 아니다**. 사용자가 원한 것은 "**Claude 세션이 끝나도 시스템이 죽이지 않는다**"이며, 재부팅 자동 기동과 크래시 자동 재기동은 **요구가 아니다** |
| 이식성 | macOS 전용, 열린 질문 Q1 | **POSIX 전반(macOS·Linux)** | launchd 를 버리면 Q1 이 **자연 해소**된다 |
| 문서 | coding-env `README.md` 에 `/hub` 상세 12줄 + 배포 표 + 트리 7줄 | **`hub/README.md` 신설**, coding-env README 에는 **존재 언급 + 링크만** | 허브는 coding-env 본체의 워크플로우 자산이 아니다. 본체 문서에 섞으면 본체를 읽는 사람이 무관한 부담을 진다 |
| 설치 | `install.sh --scope user` 가 hub/bin 을 함께 설치 | **`hub/install.sh` 독립 스크립트**. 루트 `install.sh` 는 허브를 **전혀 모른다** | coding-env 를 설치했다고 상주 프로세스·전역 훅을 쓸 준비가 된 것은 아니다. 설치 동의는 분리돼야 한다 |

**rev1 에서 그대로 유지되는 결정**(이미 승인 가능했던 것들): `/hub server start|stop|status` 명시적
제어와 `cmd_open` 암묵 기동 제거, `serve` 폐기 + 포트 8794 고정, 상주 서버의 5초 주기 수집 전담과
훅의 하트비트 위임, 허용 경로 화이트리스트, 쓰기 억제, R3 잔여 Minor 3건 흡수.

---

## 개정 요구사항 (rev2 기준)

| # | 요구 | 초판이 못 하는 이유 |
|---|------|-------------------|
| R-1 | 서버는 **사용자가 직접 띄우고, 사용자가 종료하기 전까지 시스템(Claude 세션 종료 등)이 죽이지 않는다** | 초판 서버는 `/hub` 호출에 딸려 뜨는 임시 `http.server` 다. 부모 셸의 프로세스 그룹에 매여 있어 세션·터미널 수명에 종속된다 |
| R-2 | 기동/종료는 **자동이 아니라 사용자가 직접** 컨트롤한다 | `/hub`(= `hub.py open`)가 서버를 **암묵 기동**한다(`hub.py:71`) |
| R-3 | 서버가 떠 있으면 **PC 의 모든 프로젝트**가 보이고, **살아 있는 동안 화면이 항상 현재 상태를 반영**해야 한다 | 갱신 동력이 훅 이벤트뿐이라, 훅 미설치 프로젝트의 티어 1/3 변화와 **이벤트가 없어서 발생하는 상태 변화(30분 무활동 → `stale`)** 를 원리적으로 못 잡는다 |
| R-4 | 허브 문서를 coding-env 의 `CLAUDE.md`·`README.md` **본문에 넣지 않는다** | 초판이 README 3곳(배포 표·커맨드 표·상세 단락)과 트리 7줄을 본문에 넣었다 |
| R-5 | coding-env 설치가 허브를 **함께 설치하지 않는다**. 허브는 별도 명령으로 설치하고, `/env-update` 는 **이미 설치돼 있을 때만** 함께 갱신한다 | `install.sh --scope user` 가 hub/bin 7개를 무조건 설치한다 |

**"상시"의 확정 정의** — 이 문서에서 "상시"는 다음을 뜻하며, 그 밖은 요구가 아니다.

| 요구다 | 요구가 아니다 |
|--------|--------------|
| Claude Code 세션이 끝나도 계속 산다 | 재부팅 후 자동 기동 |
| 부모 터미널·셸이 닫혀도 계속 산다(SIGHUP 면역) | 크래시 시 자동 재기동 |
| 사용자가 `stop` 하기 전까지 우리가 끄지 않는다 | 무중단 보장 |
| **죽었다면 그 사실이 관측 가능하다** | 죽은 것을 우리가 되살린다 |

**변하지 않는 불변 원칙** (rev2 도 다섯 개를 전부 지킨다):

1. 훅은 어떤 실패에도 세션을 막지 않는다(`exit 0`, 현재 실측 80ms).
2. `127.0.0.1` 바인딩 고정. `events/*.jsonl`·`bin/*.py` 를 HTTP 로 노출하지 않는다.
3. 실패 격리(설계 결정 5): 입력 하나가 수집 전체를 죽이지 않고, 실패는 관측 가능해야 한다.
4. python3 표준 라이브러리만. 새 외부 의존성 없음. 순수/I-O 레이어 분리 유지.
5. `~/.claude/projects` 트랜스크립트 **내용**은 파싱하지 않는다(mtime 만).

---

## 이 개정이 무효화·교체하는 초판 서술 (전수)

| 초판 위치 | 초판 서술 | 개정 1 rev2 |
|----------|----------|------------|
| 요구사항 요약 마지막 문장 | "상주 서버(데몬)를 두지 않는다" | **무효.** 사용자가 켜고 끄는 상주 서버를 둔다 |
| 인터페이스 § 호출 규약 | `/hub serve [포트] \| /hub serve stop` | **교체.** `/hub server start\|stop\|status` |
| 인터페이스 § 호출 규약 | `/hub` = "…→ 발행(서버 재사용/기동) → 브라우저 열기" | **교체.** `/hub` 는 서버를 띄우지 않는다 |
| 쟁점 3 | "누가 `hub.html` 을 다시 쓰는가 — **훅이다.** 데몬 없이 자동 갱신을 얻는 유일한 길" | **부분 교체.** 서버 가동 중엔 서버 전담, 훅은 폴백 |
| 쟁점 3 마지막 문단 | "`/hub serve` 를 쓰면 … 5~10초 안에 화면이 스스로 바뀐다" | **교체.** `/hub server start` 후 상시로 그렇게 된다 |
| 쟁점 6 § `/hub serve` 의 문서 루트 | 임시 디렉토리 + 심볼릭 링크 + `python3 -m http.server`, 포트 후보 8794~8796 | **교체.** 허용 경로 화이트리스트, 포트 **8794 단일 고정** |
| 쟁점 6 § `install.sh` 변경 | `HUB_FILE_COUNT=7`, `target_hub_dir`(`--scope user` 전용), manifest `files_count.hub`, dry-run·합계 가산 | **전면 철회(R-5).** 루트 `install.sh` 에서 허브 흔적을 **전부 제거**한다 |
| 쟁점 6 § README | 커맨드 표 1행 + `/hub` 설명 단락 + 트리 + "독립 커맨드 2종" | **축소(R-4).** 커맨드 표 1행(축약) + 트리 1줄 + `hub/README.md` 링크만 |
| 영향 범위 § 수정 파일 `install.sh`·`README.md` 행 | 위 두 줄에 해당하는 계획 | **교체** |
| 설계 결정 2 | "서버는 정적 파일 서버뿐이다 (상주 프로세스 없음)" | **무효**(제목만). "CAM 을 재구현하지 않는다"는 근거는 유지 |
| 데이터 모델 § `HubConfig` | `serve_port_candidates = (8794, 8795, 8796)` | **교체.** `server_port: int = 8794` + `server_collect_interval_seconds: int = 5` |
| 구현 마일스톤 M4 | `serve`/`stop` + 폴링 | **교체.** R-M1~R-M6 |
| 구현 마일스톤 M3 | "`uninstall-hooks` 후 파일이 설치 전과 **동일**" | **개정(R3-m3).** "**의미적으로 동일**(빈 배열 키 정리는 허용)" |
| 구현 마일스톤 M5 | "`install.sh --scope user --dry-run` 계획에 `hub/bin` 7개 포함" | **반전.** `--dry-run` 계획에 `hub` 가 **등장하지 않아야** 한다 |
| 리스크 8 | 「수집 시각」 + 경과 시간 재계산 | **강화.** 폴링 성공/실패로 서버 생존을 직접 표시 |
| 미채택 대안 § `serve` Popen 핸들 유지 | 보류 | **무의미.** `serve` 폐기로 판단 대상 소멸 |

**유효한 채로 남는 것**: 3티어 계층 구조와 강등 규칙, 이벤트 스키마 9필드, 상태 판정 규칙 전부,
쟁점 1(티어 1 DOM 파싱), 쟁점 2(훅 6개·날짜별 파일·리텐션), 쟁점 4(정방향 인코딩 매칭),
쟁점 5(훅 설치기 — **`install.sh` 가 훅을 건드리지 않는다**는 원칙이 이제 설치 스크립트 분리로
한 단계 더 강해진다), 설계 결정 1·3·4·5·6·7, 리스크 1~7, 순수 레이어 경계,
**`CLAUDE.md` 미영향**(초판 「미영향」의 판단을 rev2 가 재확인한다 — 앞으로도 넣지 않는다).

---

## 개정 쟁점 R1 — 상시화: **세션 무관 분리 프로세스**(`start_new_session=True`)

### 결론

`hub.py server-start` 가 서버를 **새 세션·새 프로세스 그룹**으로 띄우고 **즉시 반환**한다.
부모(Claude 세션의 Bash 툴)가 끝나도, 터미널이 닫혀도, 프로세스 그룹에 SIGHUP/SIGTERM 이 뿌려져도
서버는 살아남는다. 재부팅하면 사라지고, 크래시하면 그대로 죽는다 — **둘 다 의도된 동작이다.**

```python
subprocess.Popen(
    [sys.executable, str(HUB_PY_PATH), "server-run"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=<server.log 파일 핸들>,
    start_new_session=True,   # ← setsid(2). 이것이 "세션 무관 수명"의 전부다
    close_fds=True,
)
```

**`start_new_session=True` 가 하는 일**(POSIX `setsid`):
새 세션 리더가 되어 (a) 부모의 프로세스 그룹에서 빠져나오므로 셸이 종료 시 그룹에 보내는
SIGHUP 을 받지 않고, (b) 제어 터미널을 갖지 않으므로 터미널이 닫혀도 영향이 없으며,
(c) Claude Code 가 세션 종료 시 자식 프로세스 그룹을 정리하더라도 그 대상에 들어가지 않는다.

**이 레포에서 이미 검증된 패턴이다.** `hub_hook.py:83` 의 배경 collect spawn 이 정확히
`start_new_session=True` 를 쓰고 있고, 훅이 끝난 뒤에도 그 자식이 끝까지 수집을 마치는 것이
초판 구현에서 확인됐다. **새 개념을 도입하는 것이 아니라 이미 도는 패턴을 한 단계 오래 쓰는 것이다.**

### 더블 포크(고전적 데몬화)를 하지 않는 이유

부모가 `Popen` 직후 반환하므로 자식은 곧바로 init(PID 1)에 재부모화되어 좀비가 남지 않는다.
표준 스트림 3개를 모두 리다이렉트했고 새 세션이라 제어 터미널을 획득할 경로도 없다.
더블 포크가 막는 문제가 **하나도 남아 있지 않으므로** 하지 않는다(YAGNI).

### 이식성 — 열린 질문 Q1 이 해소된다

`start_new_session` 은 POSIX 전역이다(macOS·Linux 동일). **Windows 는 애초에 이 레포의 지원
범위가 아니다** — `install.sh`·`hub/install.sh` 가 bash 스크립트이고 `/dashboard` 가 `open` 에
의존한다. rev1 이 남겼던 "비 macOS 를 어떻게 할 것인가"(Q1)는 **선택지가 사라져 해소된다.**
플랫폼 분기 코드가 한 줄도 필요 없다.

### 프로세스 신원 관리 — launchd 의 Label 이 하던 일을 우리가 한다

launchd 를 버리면 "이 PID 가 정말 우리 서버인가"를 우리가 판정해야 한다. **PID 만 믿고 죽이면
PID 재사용으로 남의 프로세스를 죽인다** — 재부팅 후 낡은 `server.json` 이 남아 있는 상황이 정확히
그 시나리오다(재부팅 자동 기동을 하지 않기로 했으므로 이 상황은 **정상적으로 자주 발생한다**).

**두 파일로 관리한다.**

| 파일 | 쓰는 주체 | 내용 | 판정에서의 역할 |
|------|----------|------|----------------|
| `~/.claude/hub/server.json` | **서버 자신**이 bind 성공 직후 1회 | `{"pid":…, "port":…, "started_at_ms":…}` | PID **조회**용. 이 파일의 존재는 "살아 있음"의 근거가 **아니다** |
| `~/.claude/hub/server_heartbeat` | 서버의 수집 루프가 매 사이클 `touch` | (mtime 만) | **생존 판정의 정본**(TTL 안이면 살아 있다) |

- **`server.json` 을 부모가 아니라 서버가 쓰는 이유**: 포트 bind 에 실패하면 파일이 아예 생기지
  않는다. 부모가 `Popen.pid` 로 미리 쓰면 "뜨지도 못한 서버의 PID"가 기록된다.
- **kill 전 신원 확인은 `ps` 로 한다**: `ps -p <pid> -o args=` 출력에 우리 `hub.py` 경로와
  `server-run` 이 **둘 다** 있어야 한다. POSIX 표준 유틸이고 새 의존성이 아니다.
  판정 자체는 순수 함수 `is_our_server_process(ps_output, hub_py_path)` 로 분리해 단위 테스트한다.
- **`ps` 를 실행할 수 없거나 판정이 실패하면 죽이지 않는다.** "확인할 수 없으면 손대지 않는다"가
  안전한 기본값이다 — 사실만 보고하고 사용자가 판단한다.
- 서버는 `SIGTERM` 핸들러에서 `server.json`·하트비트를 스스로 지우고 종료한다. `SIGKILL` 이나
  크래시로 못 지운 경우는 `stop`/`status` 가 stale 로 판정해 정리한다.

### 크래시는 되살리지 않는다. 대신 **보이게** 한다

요구가 "죽으면 status 로 보이고 사용자가 다시 start 한다"이므로, 관측 경로 세 개를 둔다.

| 관측 지점 | 신호 |
|----------|------|
| `/hub server status` | `record_present=true` + `alive=false` + `process_present=false` → **"비정상 종료된 흔적이 있습니다"** + `server.log` 마지막 줄 |
| `/hub status` | 서버 요약 한 줄(`alive`)과 `last_collect_failure` 를 함께 보고 |
| 브라우저 화면 | 폴링 연속 실패 → **"서버 연결 끊김 — 화면이 〈시각〉 에 멈췄습니다"** |

`server.log`(= 서버의 stderr)가 사후 원인 규명의 유일한 창구이므로, `server-run` 은 시작 시
이 파일이 `SERVER_LOG_MAX_BYTES`(256KB)를 넘으면 잘라낸다.

---

## 개정 쟁점 R2 — 제어 인터페이스: `serve` 폐기, `/hub server start|stop|status`

### 새 호출 규약

```
/hub                      # 수집(서버 꺼짐일 때만) → hub.html 갱신 → 브라우저 열기. 서버를 띄우지 않는다
/hub server start         # 상주 서버 기동 (분리 프로세스). 멱등
/hub server stop          # 상주 서버 종료 (신원 확인 → SIGTERM → 필요 시 SIGKILL → 상태 파일 정리)
/hub server status        # 프로세스 · 하트비트 · HTTP 응답 · 비정상 종료 흔적 보고
/hub install | /hub off   # (초판 그대로) 전역 훅 6개 설치/제거
/hub status               # (초판 + 확장) 훅 · 이벤트 · 마지막 수집 · 실패 · 서버 요약
```

`hub.py` 서브커맨드: `server-start` · `server-stop` · `server-status` · **`server-run`**(서버 루프
본체. `server-start` 가 spawn 하는 내부 엔트리이며, 사람이 직접 부르는 것은 포그라운드 디버깅용).

### `serve`/`stop` 을 공존시키지 않고 폐기하는 이유

공존은 **구체적인 결함을 만든다.** 초판 `stop_serving` 의 종료 수단이
`pkill -f "http.server {port} --bind 127.0.0.1"` 인데(`hub_collect.py:423`), 임시 서버와 상주 서버가
같은 포트대를 쓰면 `/hub serve stop` 이 **상주 서버까지 죽인다** — "사용자가 종료하기 전까지 죽지
않는다"(요구 R-1)가 다른 커맨드의 부작용으로 깨진다. 상시 서버가 있는 세계에서 임시 서버는 존재
이유가 없다. **`pkill` 은 rev2 에서 완전히 사라진다**(패턴 매칭 kill 대신 PID + `ps` 신원 확인).

### 포트: 후보 3개 순회 → **8794 단일 고정**

상시 서버의 URL 은 북마크·PiP 창·브라우저 탭에 **고정으로 박히므로** 매번 달라지면 안 된다.
8794 가 점유돼 있으면 기동을 **거부하고** 사유를 보고한다(`config.json` 의 `server_port` 로 변경).
`serve_port_candidates` 는 폐기한다 — 기존 `config.json` 에 남아 있어도 알 수 없는 키는 무시되므로
(`_validate_config_overrides`) 마이그레이션 코드가 필요 없다.

### "자동으로 뜨고 내리는" 경로 전수 확인 결과

커밋 `2d34c8a` 전수 확인: **암묵 기동 1건, 암묵 종료 0건.**

| 경로 | 현재 | 개정 |
|------|------|------|
| `hub.py:71` `cmd_open` → `hub_collect.start_serving(None)` | **암묵 기동 — 유일한 위반** | **제거.** `open` 은 서버를 절대 띄우지 않는다 |
| `hub_hook.py` | 서버를 띄우지 않는다(`hub.py collect` 만 spawn) | 그대로 + 서버 가동 중 spawn 위임(R3) |
| `hub_collect.stop_serving` | `/hub serve stop` 만이 호출. 자동 호출 경로 없음 | 함수째 삭제 |
| `/dashboard log commit` 의 서버 자동 종료 패턴 | **hub 에는 없다**(`commands/hub.md` 에 대응 절 없음 — 확인 완료) | 도입하지 않는다 |
| `install.sh` | 훅도 서버도 건드리지 않는다 | 그대로(+ R-5 로 허브 자체를 모르게 된다) |
| **`/env-update`**(신규 접점) | — | 서버가 떠 있을 때만, **사용자 확인을 받고** stop→재설치→start. **자동 기동이 아니라 사용자가 켜 둔 상태의 복원**이다(R5 에서 상술) |

### 개정된 `/hub`(인자 없음)의 동작

```
1. 서버 하트비트가 신선한가?
   예    → 수집하지 않는다(서버가 5초마다 하고 있다). http://localhost:8794/hub.html 을 연다
   아니오 → 1회 collect + write 후 file://…/hub.html 을 열고 아래를 함께 보고한다
            "허브 서버가 꺼져 있어 이번 한 번만 수집했습니다.
             `/hub server start` 로 켜면 항상 최신 상태가 유지됩니다."
2. 어떤 분기에서도 서버를 기동하지 않는다.
```

### `server-start` / `server-stop` 절차

```
server-start
 1. 하트비트가 신선                        → {"ok":true,"already_running":true} (멱등, 아무것도 안 함)
 2. server.json 이 있고 ps 신원 확인 통과   → already_running (기동 직후라 하트비트가 아직일 수 있다)
 3. server_port 프로브 → 남의 서버          → 실패 보고(포트를 뺏지 않는다)
 4. Popen(start_new_session=True) 후 즉시 반환
 5. 하트비트가 신선해질 때까지 최대 SERVER_START_WAIT_SECONDS(5) 폴링
      성공 → {"ok":true,"pid":…,"url":…}
      실패 → server.log 마지막 몇 줄을 reason 에 담아 실패 보고 (원인이 보이지 않으면 안 된다)

server-stop
 1. server.json 없음                       → {"ok":true,"was_running":false} (에러가 아니다)
 2. ps -p <pid> -o args= → 신원 불일치      → 프로세스를 건드리지 않고 stale 상태 파일만 정리하고 보고
    ps 실행 자체가 실패                     → 아무것도 죽이지 않고 사실만 보고 (안전한 기본값)
 3. SIGTERM → SERVER_STOP_WAIT_SECONDS(5) 동안 0.2초 간격으로 ps 재확인
 4. 그래도 살아 있으면 SIGKILL
 5. server.json · 하트비트 제거 → 보고
```

---

## 개정 쟁점 R3 — 신선도: 상주 서버가 주기 수집을 **전담**하고, 훅은 하트비트로 위임 판정한다

### 현행 훅 spawn 재수집만으로는 요구 R-3 를 만족할 수 없다

1. **훅 미설치 상태의 티어 1 변화** — 훅은 옵트인이므로 설치하지 않은 사용자에게는 갱신 동력이 없다.
2. **티어 3(`~/.claude/projects/*.jsonl` mtime) 변화** — 이벤트를 남기지 않는 활동은 mtime 만 바뀐다.
3. **시간 경과로 발생하는 상태 전이** — `working` → 30분 무활동 → `stale`. **이것은 "이벤트가
   없어서" 일어나는 변화다.** 이벤트 기반 갱신으로는 잡을 수 없음이 정의상 자명하다. 지금 화면은
   경과 시간 문자열만 늘어나고 상태 배지는 `working` 인 채로 남는다.

3번 하나만으로 (a)안은 "살아 있는 동안 화면이 항상 현재 상태를 반영"을 못 지킨다.

### 채택: 상주 서버 프로세스가 수집 루프를 함께 돈다

`hub_server.py` 한 프로세스가 둘을 한다.

```
메인 스레드 : ThreadingHTTPServer(127.0.0.1, server_port) — 허용 경로 화이트리스트 핸들러
데몬 스레드 : 수집 루프
              0) 기동 직후 즉시 1회 수집 (화면이 뜨자마자 최신)
              1) collect_snapshot(now_ms)
              2) key = snapshot_content_key(snapshot)   ← 순수. 직전과 다를 때만 write_hub_html()
              3) 하트비트 touch                          ← 수집 성공/실패와 무관하게 항상
              4) 예외는 여기서 삼키고 record_collect_failure() 에 남긴다 — 루프는 죽지 않는다
              5) server_collect_interval_seconds(기본 5) 대기 → 1 로
```

- **4번이 설계 결정 5(실패 격리)의 서버판이다.** 한 사이클의 예외가 상주 프로세스를 죽이면
  요구 R-1 이 조용히 깨진다. 사유는 초판이 만들어 둔 `last_collect_error.json` 에 남고
  `/hub status` 가 읽는다(관측 경로를 새로 만들지 않는다).
- **3번은 수집이 실패해도 찍는다.** 하트비트의 뜻은 "수집이 성공했다"가 아니라 "서버가 살아
  있다"이다. 둘을 섞으면 수집 실패 시 훅까지 깨어나 **같은 이유로 똑같이 실패하는 수집을 5초마다
  추가로** 돌린다.

### 쓰기 억제 — 5초마다 무조건 다시 쓰지 않는다

주기 수집을 그대로 두면 `collected_at_ms` 때문에 **내용이 같아도 파일이 매번 달라지고**, 브라우저
폴링(파일 전체 문자열 비교)이 5초마다 전체 재렌더를 한다. 초판에 없던 부작용이다.

```python
def snapshot_content_key(snapshot: HubSnapshot) -> str:
    """collected_at_ms 를 뺀 스냅샷 내용의 안정적 키. 같으면 hub.html 을 다시 쓰지 않는다."""
```

`stale` 전이처럼 시간이 만드는 변화도 `state` 필드 값이 바뀌므로 키가 달라진다 — 정확히 원하는
동작이다. 디스크 쓰기도 실제 변화가 있을 때만 발생한다.

### 화면 표시 — 서버 생존은 폴링 자체가 증명한다

쓰기를 억제하면 `collected_at_ms` 는 "마지막 **변화** 시각"이 된다. 그것만 보여주면 사용자는 허브가
멈춘 것과 변화가 없는 것을 구별할 수 없다(초판 리스크 8 의 재발).

| 모드 | 표시 |
|------|------|
| `poll`(http) · 폴링 성공 | `마지막 변화: 〈시각〉 · 서버 연결됨 (N초 전 확인)` |
| `poll` · 연속 실패 `POLL_FAILURE_THRESHOLD`(2)회 | `서버 연결 끊김 — 화면이 〈시각〉 에 멈췄습니다` |
| `reload`(file://) | `마지막 변화: 〈시각〉 · 허브 서버 꺼짐` |

경과 시간 30초 재계산은 초판 그대로 유지된다. **크래시를 되살리지 않기로 했으므로 이 표시가
요구("죽었음을 관측할 수 있어야 한다")의 사용자 대면 절반을 맡는다.**

### 이중 수집 조정 — 서버가 켜져 있으면 훅은 append 만 한다

**서버 존재 판정은 하트비트 파일 mtime 으로 한다.**

| 후보 | 판단 |
|------|------|
| 포트 프로브(TCP connect) | 훅마다 소켓 연결 + 무응답 시 타임아웃 대기 — **훅을 지연시킬 수 있는 것은 넣지 않는다**(불변 원칙 1). 기각 |
| PID 파일 + `kill(pid,0)` | PID 재사용 문제가 남고, 훅 경로에 프로세스 조회를 넣게 된다. 기각 |
| **하트비트 mtime** | **채택.** `stat()` 1회(수 µs), 네트워크·프로세스 조회 없음. **서버가 죽으면 TTL 이 지나며 훅 폴백이 자동으로 부활한다**(크래시 시 갱신이 완전히 멎지 않는다) |

```python
SERVER_HEARTBEAT_TTL_MULTIPLIER = 3      # 수집 주기의 3배까지는 살아 있다고 본다
SERVER_HEARTBEAT_MIN_TTL_SECONDS = 15    # 주기를 아주 짧게 잡아도 하한을 둔다
```

개정된 `hub_hook.py` 절차:

```
1. stdin JSON 파싱 → 필드 투영 → events/<today>.jsonl 에 1줄 append     (항상)
2. 리텐션 정리                                                          (항상)
3. should_spawn_collect(...) 가 False 면 종료
     - 서버가 살아 있으면 여기서 끝난다        ← 위임 규칙
     - hub.html 이 없어도 여기서 끝난다        (초판의 off 스위치, 유지)
     - 쓰로틀 창(5초) 안이면 여기서 끝난다     (초판 유지, 디바운스 스탬프 포함)
4. 스탬프 touch 후 `hub.py collect` spawn
5. 어떤 경로에서도 exit 0
```

판정 전체가 **순수 함수 하나**(`should_spawn_collect`)로 빠져 단위 테스트가 가능해진다 — 초판에서는
이 판정이 I/O 와 섞여 있어(`_hub_html_is_stale_enough_to_refresh`) 테스트 대상이 아니었다.

### 노출 표면 — 심볼릭 링크 대신 허용 경로 화이트리스트

```python
ALLOWED_REQUEST_PATHS = ("/", "/hub.html")   # 이 둘만 200. 나머지는 전부 404
```

- 디렉토리를 통째로 서빙하지 않으므로 "그 디렉토리에 무엇이 생기든 노출된다"는 위험이 없다.
- `mkdtemp` 정리 책임, 심볼릭 링크 추적, 경로 traversal(`/../../.claude/settings.json`)이 **한 번에
  사라진다** — 화이트리스트에 없으면 404 이므로 경로 정규화 버그의 여지가 없다.
- `log_message` 를 무음으로 오버라이드한다(5초 폴링이 상시로 들어와 `server.log` 를 부풀린다).
- `Cache-Control: no-store` 를 붙인다(폴링이 캐시를 받으면 갱신이 멈춘다).
- `127.0.0.1` 바인딩은 불변 원칙 2 그대로.

---

## 개정 쟁점 R4 — 문서 분리: `hub/README.md` 신설, coding-env README 는 링크만

### 새 문서 `hub/README.md` (신규, ~150줄)

허브의 **모든** 사용자 대면 서술이 여기로 모인다. coding-env README 를 읽는 사람은 허브를 몰라도 된다.

| 절 | 내용 |
|----|------|
| 무엇인가 | 로컬 모든 프로젝트의 진행 상황을 한 페이지에서 읽기 전용으로. 명령·제어는 범위 밖 |
| **설치** | `hub/install.sh` 실행 → `~/.claude/hub/bin/` 9개. **coding-env 설치와 별개**임을 첫 문장에 명시 |
| 빠른 시작 | `hub/install.sh` → `/hub install`(훅 옵트인) → `/hub server start` → `/hub` |
| 서버 | start/stop/status, 포트 8794, **Claude 세션과 무관하게 살고 재부팅하면 사라진다**, 죽었을 때 보는 법 |
| 훅 옵트인 | 6개 이벤트, `DZH_HUB_HOOK` 마커, 다른 도구 훅 무손상 |
| **프라이버시 고지** | 프롬프트 발췌 120자 · 최대 7일 · `record_prompt_excerpt:false` · **서버 가동 중 `127.0.0.1:8794` 가 열려 있다** |
| 티어 한계 | 3티어와 각 티어에서 얻는 것/못 얻는 것, "미확인 프로젝트"의 의미 |
| 설정 | `~/.claude/hub/config.json` 전체 필드 표 |
| 제거 | `hub/install.sh --uninstall`(서버 정지 → 훅 제거 → bin 삭제 순서) |
| 파일 배치 | `~/.claude/hub/` 런타임 트리 |
| 설계 근거 | `docs/prps/hub-dashboard.md` 링크 |

### coding-env `README.md` 에서 제거·축소할 것 (현재 위치 기준)

| 현재 | 지금 | rev2 |
|------|------|------|
| L90 배포 대상 표의 `\| hub/bin/ \| 7 \| 설치 안 됨 \| ~/.claude/hub/bin/ \|` 행 | 있음 | **삭제.** `install.sh` 가 더 이상 배포하지 않으므로 배포 표에 남아 있으면 **거짓 서술**이 된다 |
| L92 합계 "project 51개 · **user 58개**(hub/bin 포함)" | 51 / 58 | **"project·user 모두 51개"** — 허브가 빠지며 두 scope 가 같아진다 |
| L96 "`hub/bin/` 은 LLM 컨텍스트가 아니라 python3 가 실행하는 코드라…" 주석 | 있음 | **삭제** |
| L123 커맨드 표의 `hub` 행 | 긴 설명 | **한 줄로 축약** — "로컬 모든 프로젝트의 진행 상황을 한 페이지에 집계 (**별도 설치** — [hub/README.md](hub/README.md))" |
| L156~167 `/hub` 상세 단락(12줄) | 있음 | **삭제 → `hub/README.md` 로 이동** |
| L172 "…`dashboard`·`hub` 는 이 사슬을…" | 있음 | 문장 유지(커맨드 표와의 정합) |
| L341~349 트리의 `hub/bin/` 7줄 | 파일별 주석 | **1줄로 축약** — `├── hub/    # 통합 허브 — 별도 설치(hub/README.md)` |
| L352 `docs/prps/hub-dashboard.md` | 있음 | **유지**(설계 문서는 `docs/prps/` 관례를 따른다) |
| L355 `tests/hub/` | 있음 | **유지**(레포 테스트 스위트의 일부다) |

→ coding-env README 에 남는 허브 언급은 **커맨드 표 1행 + 트리 1줄**, 둘 다 `hub/README.md` 링크를
달고 "별도 설치"임을 밝힌다. 요구 R-4("존재 언급 + 링크 한 줄 정도")를 만족한다.

**`CLAUDE.md` 는 지금도 허브를 언급하지 않으며 앞으로도 넣지 않는다.** 초판 「미영향」의 근거
("허브는 워크플로우 단계에 개입하지 않는 관측 도구다")가 그대로 유효하고, rev2 는 여기에
"설치 자체가 분리됐으므로 워크플로우 문서가 전제할 수 없는 자산이 됐다"를 더한다.

### `commands/hub.md` 는 `commands/` 에 남는다 — 그 정합을 어떻게 맞추는가

`commands/hub.md` 는 **커맨드 정의 파일**이므로 다른 8개와 함께 `commands/` 에서 배포된다
(`COMMANDS_FILE_COUNT=9` 유지). 따라서 **허브를 설치하지 않은 사용자도 `/hub` 를 부를 수 있다.**

초판 `commands/hub.md` 의 「사전 조건」이 이미 이 경우를 다루지만 문구가 `install.sh --scope user`
를 가리키므로 **반드시 개정해야 한다**(그대로 두면 R-5 이후 존재하지 않는 절차를 안내한다).

```
1. `~/.claude/hub/bin/hub.py` 가 없으면 아래를 보고하고 중단한다.
2. 안내에 넣을 레포 경로는 `~/.claude/.coding-env.json` 의 `repo_path` 를 읽어 채운다
   (`/env-update` Phase 1 과 같은 방법). manifest 가 없으면 경로 없이 일반 문구로 안내한다.
```

> 허브 실행 코드가 설치돼 있지 않습니다. 허브는 coding-env 설치와 **분리**돼 있어 별도로
> 설치해야 합니다:
>
>     {repo_path}/hub/install.sh
>
> 무엇이 설치되고 무엇이 기록되는지: `{repo_path}/hub/README.md`

`commands/hub.md` 는 계속 **얇게** 유지한다 — 설명은 `hub/README.md` 로 넘기고, 이 파일에는
호출할 서브커맨드와 보고 문구만 남긴다(`dashboard.md` 가 1512줄이 된 전철을 밟지 않는다).

---

## 개정 쟁점 R5 — 설치 분리: `hub/install.sh` 독립 + `/env-update` 조건부 연동

### 루트 `install.sh` 에서 허브 흔적을 전부 제거한다 (되돌리기 목록)

| 위치 | 지금 | rev2 |
|------|------|------|
| L15 | `readonly HUB_FILE_COUNT=7` | **삭제** |
| L28 | `target_hub_dir=""` | **삭제** |
| L99~100 | 주석 + `[[ "$scope" == "user" ]] && target_hub_dir=…` | **삭제** |
| L176 | `check_no_symlink_targets` 루프의 `"$target_hub_dir"` | **삭제** |
| L227 | `check_directory_conflict "$REPO_ROOT/hub/bin" …` | **삭제** |
| L377~378, L393 | `build_manifest_json` 의 `hub_files_count` 와 `"hub": …` | **삭제** |
| L462~466 | dry-run 계획의 hub 2줄 + 건너뜀 안내 | **삭제** |
| L495~500 | `install_directory "hub" …` + 건너뜀 안내 | **삭제** |
| L506 | 완료 합계의 `+ hub_files_count` | **삭제** |

**`MANIFEST_VERSION` 은 올리지 않는다.** `files_count.hub` 키 삭제는 필드 **제거**라 원칙적으로는
소비자를 깨뜨릴 수 있지만, 전수 확인 결과 **소비자가 없다**: `commands/env-update.md` 는
`installed_from_commit` 만 읽고(Phase 5), `tests/run.sh` 의 T21(`manifest_fields_complete`)은
`files_count` 키의 **존재**만 검사한다. 이미 설치된 머신의 manifest 에 `hub` 키가 남아 있어도
무해하며 다음 설치 때 사라진다.

### 새 파일 `hub/install.sh` (신규, ~110줄)

```
hub/install.sh [--force] [--dry-run] [--uninstall] [--help]
```

**`--scope` 인자가 없다.** 허브의 설치 위치는 `~/.claude/hub/bin` 하나뿐이다 — 초판 쟁점 6 의
"허브는 머신 전역 자산"이라는 결정이 이제 **문서가 아니라 스크립트 구조로 강제된다**(프로젝트마다
사본이 생겨 어느 `hub.html` 이 정본인지 모호해지는 실패가 원천 봉쇄된다).

절차:

```
--dry-run 아니면:
  1. ~/.claude/hub 가 심볼릭 링크면 중단
  2. 대상이 이미 있고 --force 가 아니면:
       diff -rq hub/bin ~/.claude/hub/bin 의 "differ" 줄을 수집
       비어 있지 않으면 목록을 보여주고 --force 를 요구하며 exit 1
  3. mkdir -p ~/.claude/hub/bin && cp -R hub/bin/. ~/.claude/hub/bin/
  4. 설치된 파일 수 == HUB_FILE_COUNT(9) 검증. 아니면 실패
  5. 완료 보고 + 다음 단계 안내(/hub install, /hub server start, hub/README.md)

--uninstall:
  1. ~/.claude/hub/bin/hub.py 가 있으면 python3 hub.py server-stop     ← 순서가 중요하다
  2. 이어서 python3 hub.py uninstall-hooks                             ← bin 을 지우기 전에
  3. rm -rf ~/.claude/hub/bin
  4. events/ · hub.html · config.json 은 **지우지 않는다.** 사용자 데이터이며,
     지울지는 사용자가 직접 결정한다(경로만 안내한다)
```

**`--uninstall` 의 순서가 이 스크립트의 존재 이유다.** 허브는 설치 후 **상주 프로세스 1개 + 전역 훅
6개**를 남긴다. `bin/` 을 먼저 지우면 `server-stop` 도 `uninstall-hooks` 도 실행할 수 없어 **서버는
계속 돌고 훅은 존재하지 않는 스크립트를 매 이벤트마다 호출한다.** 사용자가 손으로 되돌리기 가장
어려운 상태이고, 그것을 막는 것이 이 세 줄의 순서다.

### 루트 `install.sh` 의 공유 함수를 재사용하지 않는 이유

루트의 `install_directory` 는 `list_missing_managed_files`·`list_differing_managed_files`·
`copy_directory_contents`·`verify_managed_files_installed`·`count_lines` 에 의존하고, 그 위에
2개 scope · CLAUDE.md 병합 · manifest · 전역 커맨드 중복 보고가 얹혀 있다. **허브가 필요로 하는
것은 그중 "수정 감지 → `--force` 요구" 하나뿐이고**, 허브의 대상은 사용자 파일이 섞이지 않는
단일 `bin/` 디렉토리다(초판이 `bin/` 격리를 그렇게 설계했다). 40여 줄로 끝나는 일에 공유 라이브러리
추출(`install-lib.sh`)을 하면 **검수 3회를 통과한 배포 스크립트를 구조적으로 흔드는 대가**를 치른다.
"수술적으로 변경한다"에 어긋난다. 중복되는 것은 정책 한 줄이며, `tests/run.sh` 가 양쪽을 각각 검증한다.

### `/env-update` 연동 — 판정 방법과 절차

**판정: `~/.claude/hub/bin/hub.py` 의 존재 여부.** 사실을 직접 본다.

| 후보 | 판단 |
|------|------|
| manifest `files_count.hub` | **기각.** 루트 `install.sh` 가 더 이상 허브를 만지지 않으므로, 이 필드는 "install.sh 가 남의 설치 상태를 기록하는" 부정확한 값이 된다(허브만 따로 지워도 갱신되지 않는다) |
| 허브 전용 manifest(`~/.claude/hub/.coding-env-hub.json`) | **기각(YAGNI).** env-update 는 버전을 비교하지 않고 항상 최신으로 덮으므로(루트와 같은 정책) 메타데이터가 필요 없다. 상태 파일을 하나 더 만들면 그것이 틀릴 수 있는 새 경로가 된다 |
| **`~/.claude/hub/bin/hub.py` 존재** | **채택.** 항상 정확하고, 유지할 상태가 없다 |

`commands/env-update.md` 에 **Phase 4b — HUB REINSTALL (conditional)** 를 Phase 4 와 5 사이에 추가한다.

```
1. ~/.claude/hub/bin/hub.py 가 없으면
     → "[INFO] Hub is not installed. Skipping." 한 줄만 보고하고 Phase 5 로. 아무것도 만들지 않는다.

2. 있으면:
   a. python3 ~/.claude/hub/bin/hub.py server-status --json 으로 alive 를 읽는다
   b. alive=true 면 사용자에게 확인을 받는다:
        "[INFO] Hub server is running. Stop it, update, and start it again? (y/n)"
        n → 재설치를 건너뛴다(돌고 있는 서버가 옛 코드를 계속 실행함을 경고하고 Phase 5 로)
        y → server-stop
   c. "$repo_path/hub/install.sh" 실행
        exit 1(수정 감지) → "--force 로 덮어쓸까요? (y/n)" → y 면 --force 재실행
                            (루트 install.sh 의 충돌 처리와 **같은 패턴**)
   d. b 에서 서버를 껐던 경우에만 server-start 로 되돌린다
   e. 훅은 건드리지 않는다 — 커맨드 문자열이 바뀌었으면 install-hooks 가 멱등이므로
      "필요하면 /hub install 을 다시 실행하십시오" 한 줄만 안내한다
```

- **b 가 필수인 이유**: 서버가 도는 중에 `bin/*.py` 를 갈아끼우면 **그 프로세스는 옛 코드를 계속
  실행한다.** 사용자는 업데이트했다고 믿는데 화면은 옛 로직으로 돌아간다.
- **d 는 "자동 기동"이 아니다.** 사용자가 **켜 두었던 상태를 복원**하는 것이고, b 에서 명시적
  동의를 받았다. 켜 두지 않았던 서버를 켜는 일은 어떤 경우에도 없다.

---

## 개정 쟁점 R6 — 직전 검수(R3)의 잔여 Minor 3건 흡수

### R3-m1 — 티어 3 읽기 2경로에 `OSError` 가드

`hub_collect._tier3_activity_by_encoded_name` 의 두 지점이 무방비다.

| 지점 | 실패 시나리오 | 현재 결과 |
|------|-------------|----------|
| `PROJECTS_DIR.iterdir()` (`hub_collect.py:236`) | 권한 없음(EACCES), 디렉토리 소멸 | **collect 전체가 죽는다** |
| `child.stat()` in `entry.glob("*.jsonl")` (`:241`) | glob 열거와 stat 사이 파일 소멸(TOCTOU) → `FileNotFoundError` | **collect 전체가 죽는다** |

`_has_project_marker`·`_scan_directory`·`read_recent_events` 는 이미 같은 가드를 갖고 있으므로
이 두 곳만 설계 결정 5 의 구멍이다. **상주 서버에서는 이 구멍이 더 위험하다** — 수집 루프가
매 5초 같은 예외를 만나 실패 기록만 쌓는다.

**개정**: 반환 타입을 `dict[str,int]` → `tuple[dict[str,int], tuple[str,...]]` 로 바꿔 경고를 함께
돌려주고, `collect_snapshot` 이 `HubSnapshot.warnings` 에 합류시킨다(`read_recent_events` 와 **같은
형태** — 새 패턴을 만들지 않는다). `iterdir()` 실패 → 티어 3 전체 포기(티어 1·2 는 산다),
`entry` 단위 실패 → **그 프로젝트만** 건너뛰고 경고 1줄.

### R3-m2 — `commands/hub.md` status 절에 실패 필드 보고 지시 추가

`hub.py status` 는 이미 `last_collect_failure`·`event_read_warnings` 를 내보내지만(`hub.py:120-122`),
`commands/hub.md` 는 세 필드만 보고하라고 적혀 있다 — **관측 경로를 만들어 두고 읽으라고 말하지
않았다.** status 절에 아래를 추가한다.

> `last_collect_failure` 가 `null` 이 아니거나 `event_read_warnings` 가 비어 있지 않으면 **그 내용을
> 표보다 먼저 한 줄로 보고한다.** 허브가 조용히 멈춰 있는 상태를 사용자가 표의 숫자에서 유추하게
> 두지 않는다.

여기에 rev2 가 추가하는 서버 요약(`server.alive`, 비정상 종료 흔적)도 같은 절에서 함께 보고한다.

### R3-m3 — 마일스톤 M3 검증 기준을 의미 동등으로 개정

`strip_hub_hooks` 는 우리 엔트리를 뺀 뒤 **빈 배열이 된 이벤트 키를 정리**하고 `hooks` 가 비면
`hooks` 키도 지운다(초판 쟁점 5 의 5번이 그렇게 설계했다). 원래 그 이벤트에 우리 훅만 있었다면
제거 후 파일은 설치 전과 **바이트 동일하지 않다.**

**개정된 기준**: "설치 전과 **의미적으로 동일**하다 — 우리 엔트리가 전부 사라지고, **다른 도구의
훅 엔트리가 하나도 변하지 않으며**, 우리 때문에 새로 생긴 빈 배열·빈 컨테이너 키의 정리는
허용한다." 검증은 바이트 비교가 아니라 **다른 도구 엔트리의 집합 비교**로 한다.

---

## 개정 데이터 모델

```python
@dataclass(frozen=True)
class HubConfig:
    # …(초판 필드 그대로)…
    # serve_port_candidates 는 삭제된다
    server_port: int = 8794                       # 상주 서버 고정 포트(북마크 가능해야 한다)
    server_collect_interval_seconds: int = 5      # 수집 루프 주기

@dataclass(frozen=True)
class ServerRecord:                               # server.json 의 내용
    pid: int
    port: int
    started_at_ms: int

@dataclass(frozen=True)
class ServerStatus:                               # /hub server status 의 보고 단위
    record: ServerRecord | None                   # None = server.json 없음
    process_present: bool                         # ps 신원 확인 통과
    heartbeat_age_ms: int | None                  # None = 하트비트 파일 없음
    alive: bool                                   # heartbeat_age_ms < ttl_ms
    http_ok: bool                                 # 127.0.0.1:{port}/hub.html 이 200
    crashed_evidence: bool                        # record 있음 + alive 아님 + process_present 아님
    log_tail: str | None                          # crashed_evidence 일 때 server.log 마지막 줄들
```

`crashed_evidence` 를 **필드로 못 박는 이유**: "죽었음을 관측할 수 있어야 한다"가 요구이므로, 그
판정을 보고 시점의 즉흥적 조합에 맡기지 않고 타입에 박아 커맨드 문서가 그 이름 하나만 읽게 한다.

`_CONFIG_FIELD_TYPES` 에 `server_port: int`, `server_collect_interval_seconds: int` 를 추가하고
`serve_port_candidates` 를 제거한다.

---

## 개정 인터페이스

### 새 순수 함수 (테스트 대상)

```python
# hub_model.py
def snapshot_content_key(snapshot: HubSnapshot) -> str:
    """collected_at_ms 를 제외한 스냅샷 내용의 안정적 키. 같으면 hub.html 을 다시 쓰지 않는다."""
def server_heartbeat_ttl_ms(collect_interval_seconds: int) -> int:
    """하트비트를 '살아 있음'으로 인정하는 최대 나이(ms)."""
def is_server_alive(now_ms: int, heartbeat_mtime_ms: int | None, ttl_ms: int) -> bool:
    """하트비트 나이로 상주 서버 생존을 판정한다. 파일이 없으면 False."""
def should_spawn_collect(now_ms: int, server_alive: bool, hub_html_mtime_ms: int | None,
                         spawn_stamp_mtime_ms: int | None, throttle_ms: int) -> bool:
    """훅이 재수집을 spawn 해야 하는가. 서버가 살아 있으면 항상 False(수집 위임)."""

# hub_daemon.py — 아래 둘만 순수하다(모듈의 나머지는 I/O)
def is_our_server_process(ps_output: str, hub_py_path: str) -> bool:
    """`ps -p <pid> -o args=` 출력이 우리 hub.py server-run 인가. PID 재사용으로 남의
    프로세스를 죽이지 않기 위한 유일한 안전장치이며, 판정할 수 없으면 False 다."""
def parse_server_record(text: str) -> ServerRecord | None:
    """server.json 텍스트를 판다. 깨졌거나 필드가 없으면 None(예외를 던지지 않는다)."""
```

### 새 I/O 함수

```python
# hub_server.py — 상주 서버 본체
def run_server(config: HubConfig) -> int:
    """HTTP 서버(메인) + 수집 루프(데몬 스레드)를 띄우고 블로킹한다. server-run 의 진입점.
    bind 성공 직후 server.json 을 쓰고, SIGTERM 에 상태 파일을 정리하고 종료한다."""

# hub_daemon.py — 프로세스 생명주기
def start_server() -> dict    # 멱등 확인 → 포트 프로브 → 분리 spawn → 하트비트 대기
def stop_server() -> dict     # 신원 확인 → SIGTERM → (필요 시) SIGKILL → 상태 파일 정리
def server_status() -> ServerStatus

# hub_collect.py
def touch_server_heartbeat() -> None
def read_server_heartbeat_mtime_ms() -> int | None
def read_server_record() -> ServerRecord | None
def write_server_record(record: ServerRecord) -> None
def clear_server_state() -> None                 # server.json + 하트비트 제거
# start_serving / stop_serving / _probe_port / _launch_server / _serve_url / _is_valid_port 삭제
```

**모듈 이름이 `hub_launchd.py` 가 아니라 `hub_daemon.py` 인 것은 rev2 의 결과다** — 특정 OS 서비스
관리자에 묶이지 않는다는 사실이 이름에 드러나야 한다.

---

## 개정 영향 범위

### 신규 파일 (5개)

| 파일 | 줄 수(예상) | 역할 |
|------|------------|------|
| `hub/bin/hub_server.py` | ~150 | 상주 서버 — 화이트리스트 핸들러 + 수집 루프 + 하트비트 + `server.json` + SIGTERM 정리 |
| `hub/bin/hub_daemon.py` | ~170 | 프로세스 생명주기 — 분리 spawn · 신원 확인 · SIGTERM/SIGKILL · 상태 보고 |
| `hub/install.sh` | ~110 | **허브 전용 설치기**(`--force`/`--dry-run`/`--uninstall`) |
| `hub/README.md` | ~150 | **허브 사용자 문서 전부**(R-4) |
| `tests/hub/test_hub_daemon.py` | ~90 | `is_our_server_process`·`parse_server_record` 순수 테스트 |

> `hub_server.py` 와 `hub_daemon.py` 를 나누는 이유: 관심사가 다르다. 전자는 "요청을 처리하고
> 주기적으로 수집한다", 후자는 "그 프로세스를 띄우고 죽이고 상태를 본다". 합치면 330줄이 되고,
> 포그라운드 디버깅(`server-run`)이 생명주기 코드를 끌고 온다. 반대로 `hub_daemon.py` 의 순수
> 함수 2개를 **또 다른 파일로 분리하지는 않는다** — 파일을 하나 더 만들 만큼의 문제가 없다(YAGNI).

### 수정 파일

| 파일 | 변경 |
|------|------|
| `hub/bin/hub.py` | `serve`/`stop`·`cmd_serve`·`_parse_serve_args` **삭제**, `server-start`/`server-stop`/`server-status`/`server-run` 추가, `cmd_open` 의 `start_serving` 호출 제거(하트비트 분기로 교체), `cmd_status` 에 서버 요약 추가 |
| `hub/bin/hub_collect.py` | `start_serving`·`stop_serving`·`_probe_port`·`_launch_server`·`_serve_url`·`_is_valid_port`·`SERVE_BIND_ADDRESS`·`SERVER_STARTUP_WAIT_SECONDS`·`VALID_PORT_RANGE` **삭제**, 하트비트·`server.json` I/O 추가, 티어 3 `OSError` 가드(R3-m1), `_CONFIG_FIELD_TYPES` 갱신 |
| `hub/bin/hub_hook.py` | `_hub_html_is_stale_enough_to_refresh` → 순수 `should_spawn_collect` 호출로 교체 |
| `hub/bin/hub_model.py` | `HubConfig` 필드 교체, `ServerRecord`·`ServerStatus` 추가, 순수 함수 4개 추가 |
| `hub/bin/hub_template.html` | 폴링 성공/실패 추적, 「수집 시각」 → 「마지막 변화 + 서버 연결 상태」 |
| `commands/hub.md` | frontmatter `argument-hint`, 호출 규약, **사전 조건 안내 문구(R-4)**, `serve` 절 → `server` 절, status 절 실패 필드 지시(R3-m2) |
| `commands/env-update.md` | **Phase 4b(조건부 허브 재설치) 신설** + 에러 처리 표 2행 |
| `install.sh` | **허브 흔적 9곳 전부 제거**(R-5 표) |
| `README.md` | 허브 서술 축소·이동(R-4 표) |
| `tests/run.sh` | T25 개정·추가(아래), 총 24개 유지 |
| `tests/hub/test_hub_model.py` | 순수 함수 4개 케이스 추가 |
| `docs/prps/hub-dashboard.md` | 이 개정 |

### 미영향

`hub_parse.py`·`hub_settings.py`·**`CLAUDE.md`**·`agents/`·`rules/`·`commands/dashboard.md`.

---

## 개정 테스트 계획

### 순수 로직 단위 테스트

#### `test_hub_model.py` 추가

| TC | 케이스 | 기대 |
|----|--------|------|
| M21 | `should_spawn_collect(server_alive=True, …쓰로틀 지남…)` | **False** — 서버가 전담한다 |
| M22 | `server_alive=False`, 스탬프 없음, hub.html mtime 6초 전 | True |
| M23 | `server_alive=False`, 스탬프 2초 전 | False (쓰로틀) |
| M24 | `hub_html_mtime_ms=None`, `server_alive=True` | **False** — 서버가 아직 첫 수집을 못 했을 뿐, 전담권은 서버에 있다 |
| M24b | `hub_html_mtime_ms=None`, `server_alive=False`, 스탬프 없음 | **True** — 즉시 spawn(서버가 죽어 hub.html 을 아예 못 만든 상태에서 훅 폴백까지 막히면 이중 실패가 된다, R2 M2-5) |
| M24c | `hub_html_mtime_ms=None`, `server_alive=False`, 스탬프 최근 | False(쓰로틀) — M23 과 같은 디바운스 규칙이 이 경로에도 적용된다 |
| M25 | `is_server_alive` — 하트비트 없음 / TTL 직전 / TTL 직후 | False / True / False |
| M26 | `server_heartbeat_ttl_ms(1)`·`(5)`·`(60)` | 15000 / 15000 / 180000 (하한 확인) |
| M27 | `snapshot_content_key` — `collected_at_ms` 만 다른 두 스냅샷 | **같은 키**(쓰기 억제 성립) |
| M28 | `snapshot_content_key` — 세션이 `working` → `stale` | 다른 키(시간이 만든 변화도 잡힌다) |
| M29 | `snapshot_content_key` — `warnings` 만 다름 | 다른 키(실패가 화면에 드러나야 한다) |

#### `test_hub_daemon.py` (신규)

| TC | 케이스 | 기대 |
|----|--------|------|
| D1 | `is_our_server_process("python3 /Users/x/.claude/hub/bin/hub.py server-run", …)` | True |
| D2 | 같은 hub.py 지만 `collect` 서브커맨드 | **False**(배경 collect 프로세스를 서버로 오인하지 않는다) |
| D3 | 전혀 다른 프로세스(`/usr/sbin/cupsd`) | **False — PID 재사용 방어의 핵심** |
| D4 | 빈 문자열 / `ps` 실패 시의 빈 출력 | **False**(확인할 수 없으면 죽이지 않는다) |
| D5 | 경로에 공백이 든 홈 디렉토리 | True(부분 문자열 판정이 공백에 깨지지 않는다) |
| D6 | `parse_server_record` — 정상 / 필드 누락 / 깨진 JSON / 빈 파일 | 정상 1건, 나머지 전부 `None`(예외 없음) |

### T25 개정·추가 (bash grep 회귀)

| TC | 검증 | 상태 |
|----|------|------|
| T25-1 | `HUB_FILE_COUNT` == 실제 `hub/bin/*` 수 | **대상 이동** — `install.sh` → **`hub/install.sh`** 에서 읽는다(값 9) |
| T25-2 | 설치 결과 검증 | **반전** — `install.sh --scope user` 후 `~/.claude/hub` 가 **생성되지 않음** + `hub/install.sh` 실행 후 9개 존재 |
| T25-8 | 포트 `8794` 정합, `8791` 부재 | **개정** — 포트 상수가 `hub_model.py` 로 옮겨가므로 검사 대상을 `hub_model.py`·`commands/hub.md` 로 변경 |
| **T25-14** | `hub/bin/*.py`·`commands/hub.md` 에 `serve` 잔재 없음(`start_serving`·`stop_serving`·`/hub serve`·`pkill`) | 신규 — 폐기 회귀 방지 |
| **T25-15** | `hub_server.py` 가 `SimpleHTTPRequestHandler` 를 쓰지 않고 `ALLOWED_REQUEST_PATHS` 를 갖는다 | 신규 — 노출 표면 회귀 방지 |
| **T25-16** | `hub_daemon.py` 의 kill 경로가 `is_our_server_process` 를 거친다 | 신규 — **PID 재사용 방어의 회귀 방지** |
| **T25-17** | `hub_daemon.py` 에 `start_new_session=True` 가 있다 | 신규 — 세션 무관 수명(요구 R-1)의 기계적 강제 |
| **T25-18** | `_tier3_activity_by_encoded_name` 이 `except OSError` 를 포함 | 신규 — R3-m1 회귀 |
| **T25-19** | `commands/hub.md` 에 `last_collect_failure`·`event_read_warnings` 등장 | 신규 — R3-m2 회귀 |
| **T25-20** | `hub.py` 의 `cmd_open` 경로에 서버 기동 호출이 없다 | 신규 — **암묵 기동 회귀 방지(요구 R-2)** |
| **T25-21** | **`install.sh` 에 `hub` 문자열이 등장하지 않는다** | 신규 — **설치 분리(R-5)의 기계적 강제** |
| **T25-22** | `README.md` 의 허브 언급이 **N줄 이하**이고 `hub/README.md` 링크를 포함한다 | 신규 — 문서 분리(R-4) 회귀 방지 |
| **T25-23** | `hub/install.sh --uninstall` 절차에서 `server-stop`·`uninstall-hooks` 가 `rm -rf` **앞**에 온다(줄 번호 비교) | 신규 — 되돌릴 수 없는 상태를 만드는 순서 회귀 방지 |
| **T25-24** | `commands/env-update.md` 에 조건부 허브 절과 판정 경로(`hub/bin/hub.py`)가 있다 | 신규 — R-5 연동 회귀 |
| **T25-25** | `commands/hub.md` 사전 조건이 `install.sh --scope user` 를 안내하지 **않고** `hub/install.sh` 를 안내한다 | 신규 — 존재하지 않는 절차 안내 방지 |

T25-20·T25-21 이 이 개정에서 가장 값진 회귀 테스트다. "자동으로 뜨지 않는다"와 "함께 설치되지
않는다"는 문서로 부탁하면 다음 편의 개선에서 반드시 되돌아오지만, grep 한 줄로 강제하면 되돌아오지
않는다(T25-10 과 같은 논리).

### 통합 검증 (스크립트/수동 — 자동 스위트에 넣지 않는다)

프로세스 기동·종료는 실행 머신의 상태를 바꾸므로 `tests/run.sh` 샌드박스에 넣지 않는다.

| 항목 | 방법 | 기대 |
|------|------|------|
| 기동 | `hub.py server-start` | `server.json` 생성, 5초 내 하트비트 신선, `curl 127.0.0.1:8794/hub.html` 200 |
| **세션 무관 수명(요구 R-1)** | Claude Code 세션의 Bash 툴에서 `server-start` → **그 세션을 종료** → 새 세션에서 `server-status` | **`alive=true`.** 이것이 이 개정의 핵심 수용 기준이다 |
| 터미널 SIGHUP 면역 | 별도 터미널에서 start → 그 터미널 강제 종료 | 서버 생존 |
| 이중 기동 방지 | `server-start` 2회 | 두 번째는 `already_running=true`, `pgrep -f "hub.py server-run"` **1개** |
| 정지 | `server-stop` | 프로세스 무검출, `server.json`·하트비트 제거 |
| **PID 재사용 방어** | `server.json` 의 `pid` 를 무관한 실행 중 프로세스(예: 사용자 셸)의 PID 로 바꾼 뒤 `server-stop` | **그 프로세스를 죽이지 않고** stale 상태 파일만 정리하고 보고 |
| **재부팅 후 동작(의도된 사라짐)** | 재부팅 후 `server-status` | 프로세스 없음을 **정직하게 보고**하고, 낡은 `server.json` 의 PID 로 아무도 죽이지 않는다 |
| **크래시 관측** | `kill -9 <pid>` 후 `server-status` | `crashed_evidence=true` + `server.log` 꼬리 보고. **자동으로 되살아나지 않는다** |
| 노출 금지 | `curl -o /dev/null -w '%{http_code}' 127.0.0.1:8794{경로}` | `/`·`/hub.html` → 200. `/events/…jsonl`·`/bin/hub.py`·`/../../.claude/settings.json`·`/config.json` → **전부 404** |
| 훅 위임 | 서버 가동 중 다른 프로젝트에서 프롬프트 1회 | 이벤트 1줄 추가, **`pgrep -f "hub.py collect"` 무검출** |
| 폴백 부활 | `server-stop` 후 프롬프트 1회 | `hub.py collect` 가 다시 spawn 된다 |
| 신선도(R-3) | 서버 가동 + 훅 **미설치** 상태에서 다른 프로젝트의 `dashboard.html` 을 `step` 으로 갱신 | 10초 내 허브 카드가 바뀐다 |
| 신선도(stale 전이) | `stale_after_minutes: 1` 로 두고 방치 | 배지가 스스로 `working` → `stale` (**초판이 못 하던 것**) |
| 훅 지연 | `time` 으로 훅 1회 | 초판 실측 80ms 대비 유의미한 증가 없음(`stat()` 1회 추가) |
| 수집 비용 | 포그라운드 `server-run` 에서 수집 1회 측정 | **주기(5초)의 20% 이하** |
| 쓰기 억제 | 변화 없이 60초 방치 | `hub.html` mtime 불변 |
| 화면 연결 표시 | 페이지를 연 채 `server-stop` | 10초 내 "서버 연결 끊김" |
| **설치 분리(R-5)** | 깨끗한 홈에 `install.sh --scope user` | `~/.claude/hub` 가 **생성되지 않는다**. 이어서 `hub/install.sh` → 9개 설치 |
| **`/hub` 미설치 UX** | 허브 미설치 상태에서 `/hub` | `hub/install.sh` 경로를 담은 안내가 나오고 **아무것도 만들지 않는다** |
| **`--uninstall` 순서** | 서버·훅이 있는 상태에서 `hub/install.sh --uninstall` | 서버 정지 → 훅 제거 → `bin/` 삭제. `settings.json` 에 `DZH_HUB_HOOK` 잔재 없음. `events/`·`hub.html` 은 **남아 있다** |
| **env-update 연동** | 허브 설치 + 서버 가동 상태에서 `/env-update` | 확인 후 stop→재설치→start. 허브 **미설치** 상태에서는 건너뛰고 아무것도 만들지 않는다 |

---

## 개정 마일스톤 (단계별 검증 기준)

| M | 범위 | 검증 기준 (통과 못 하면 다음으로 가지 않는다) |
|---|------|--------------------------------------------|
| **R-M1** | `hub_model.py` 순수 4개 + `hub_daemon.py` 순수 2개 + 단위 테스트(M21~M29, D1~D6) | `python3 -m unittest discover -s tests/hub -t .` 전부 통과. 아직 어떤 동작도 바뀌지 않는다 |
| **R-M2** | `hub_server.py`(화이트리스트 핸들러 + 수집 루프 + 하트비트 + `server.json` + SIGTERM 정리) | 포그라운드 `server-run` 에서 「노출 금지」 6개 URL 기대대로. 하트비트 5초 갱신. 변화 없으면 mtime 불변. 수집 1회 ≤ 주기의 20% |
| **R-M3** | `hub_daemon.py` + `server-start`/`server-stop`/`server-status` | 「세션 무관 수명」·터미널 SIGHUP 면역·이중 기동 방지·**PID 재사용 방어**·크래시 관측 5개 전부 통과 |
| **R-M4** | `hub_hook.py` 위임 + `cmd_open` 암묵 기동 제거 + `serve` 전면 삭제 + R3-m1 가드 | 「훅 위임」·「폴백 부활」·「신선도」 통과. 훅 실행 시간 회귀 없음. 권한 0 디렉토리를 `~/.claude/projects` 에 두어도 collect 가 죽지 않는다 |
| **R-M5** | **설치·문서 분리** — `hub/install.sh`, `hub/README.md`, `install.sh` 되돌리기, `README.md` 축소, `commands/hub.md` 사전 조건, `commands/env-update.md` Phase 4b | 「설치 분리」·「`/hub` 미설치 UX」·「`--uninstall` 순서」·「env-update 연동」 통과. `grep -c hub install.sh` == **0** |
| **R-M6** | `hub_template.html` 연결 표시 + `tests/run.sh`(T25-14~25, T25-1·2·8 개정) | `bash tests/run.sh` 24개 전부 통과. 「화면 연결 표시」 통과 |

> **R-M5 를 R-M6 앞에 두는 순서가 의도적이다.** 설치 분리는 다른 모든 검증의 전제(어디에 무엇이
> 설치되는가)를 바꾸므로, 테스트 스위트를 고치기 전에 확정돼야 한다.

검증 루프 명령(초판과 동일 + 1줄):

```bash
python3 -m unittest discover -s tests/hub -t .      # 순수 로직
python3 -m py_compile hub/bin/*.py                  # 구문
bash tests/run.sh                                   # 설치·문서 정합성
bash -n install.sh                                  # 셸 구문
bash -n hub/install.sh                              # 셸 구문 (신규)
```

---

## 개정 리스크와 완화책

### R-1. 상시 열린 포트가 새로운 노출 표면이다 (가장 주의할 것)

초판의 임시 서버는 `/hub` 를 부른 동안만 열렸다. 이제 **8794 가 사용자가 끌 때까지 열린다.**

- 완화: `127.0.0.1` 바인딩(원격 불가) + **허용 경로 2개 화이트리스트**(`events/`·`bin/`·`config.json`
  은 원리적으로 404) + 노출되는 유일한 내용은 `hub.html`(사용자가 보려고 만든 화면).
- **인증 토큰은 넣지 않는다.** 루프백 + 화이트리스트 2개 + 읽기 전용이라는 조건에서 토큰은 URL 을
  북마크 불가능하게 만드는 비용만 낸다(요구 R-1 과 충돌).
- **`hub/README.md` 의 프라이버시 절에 고지한다**(coding-env README 가 아니라 — R-4).
- 남는 사실: 이 포트에 닿는 로컬 프로세스는 `hub.html` 에 인라인된 프롬프트 발췌 120자를 읽을 수
  있다. 끄는 수단은 `record_prompt_excerpt:false` 와 `/hub server stop`.

### R-2. PID 재사용으로 남의 프로세스를 죽인다

재부팅 자동 기동을 하지 않기로 했으므로 **낡은 `server.json` 이 남는 상황이 정상적으로 자주
발생한다** — 이 리스크는 이론이 아니다.

- 완화: kill 전에 **반드시** `is_our_server_process` 를 통과해야 한다. 판정 불가·`ps` 실패면
  **아무것도 죽이지 않는다.** T25-16 이 이 가드의 제거를 막고, D1~D5 가 판정을 검증하며,
  통합 검증의 「PID 재사용 방어」가 실제 동작을 확인한다.

### R-3. 상주 프로세스가 배터리·CPU 를 계속 쓴다

- 완화: 쓰기 억제(변화 없으면 디스크 쓰기 0), `server_collect_interval_seconds` 조정 가능.
- R-M2 검증에 **수집 1회 ≤ 주기의 20%** 를 넣어 측정 없는 방치를 막는다.
- **적응형 백오프는 만들지 않는다**(YAGNI). 측정이 기준을 넘을 때 근거를 갖고 도입한다.

### R-4. 크래시하면 갱신이 멈추고 아무도 되살리지 않는다 (의도된 동작의 대가)

- 완화 셋: `status` 의 `crashed_evidence` + `server.log` 꼬리, 화면의 "서버 연결 끊김",
  그리고 **하트비트 TTL 이 지나면 훅 폴백이 자동으로 부활**해 갱신이 완전히 멎지는 않는다.
- 자동 재기동은 **요구가 아니므로 만들지 않는다.** 넣으면 요구 R-2("사용자가 직접 컨트롤")와
  회색지대가 생긴다.

### R-5. 서버가 도는 중에 `bin/*.py` 가 교체된다

`hub/install.sh` 나 `/env-update` 가 파일을 갈아끼워도 **돌고 있는 프로세스는 옛 코드를 계속
실행한다.** 사용자는 업데이트했다고 믿는다.

- 완화: `/env-update` Phase 4b 가 `alive` 를 먼저 확인하고 stop→갱신→start 를 **동의를 받아**
  수행한다. `hub/install.sh` 를 직접 실행한 경우에는 완료 메시지에
  "서버가 실행 중이면 `/hub server stop` 후 다시 `start` 해야 새 코드가 적용됩니다"를 넣는다.

### R-6. 훅이 서버 존재를 오판한다

하트비트가 낡았는데 서버는 살아 있는 경우(수집이 오래 걸림) → 훅이 중복 수집을 spawn 한다.

- 최악의 결과는 `hub.html` 이 한 번 더 원자적으로 교체되는 것뿐이다(초판의 동시 collect 안전성
  설계가 그대로 유효: `tempfile.mkstemp` + `os.replace`). TTL 을 주기의 3배로 두어 여유가 있고,
  반대 방향 오판은 TTL 이 지나면 반드시 해소된다.

### R-7. 5초 주기 재렌더가 사용자의 화면 조작을 되돌린다

쓰기 억제로 **초판과 동일한 빈도**(실제 변화가 있을 때만)로 유지된다. 설계 단계에서 제거됐고,
R-M2 의 "변화 없이 60초 방치 → mtime 불변"이 검증한다.

### R-8. 설치가 두 단계가 되어 사용자가 허브를 못 찾는다 (R-5 의 대가)

- 완화: coding-env README 커맨드 표 1행이 "**별도 설치**"와 `hub/README.md` 링크를 달고,
  `/hub` 를 부르면 실제 레포 경로가 채워진 설치 안내가 나온다(R-4 의 사전 조건 UX).
  **알아내는 경로가 두 개**이며 둘 다 한 번에 정답으로 이어진다.

---

## 검토했으나 채택하지 않은 대안

| 대안 | 기각 이유 |
|------|----------|
| **launchd LaunchAgent(`RunAtLoad`+`KeepAlive`) — rev1 의 채택안** | **사용자가 반려했다.** "상시"의 의미가 재부팅 생존이 아니라 "Claude 세션이 죽여도 살아남는다"였다. 재부팅 자동 기동과 크래시 자동 재기동은 요구가 아니며, 요구하지 않은 동작을 위해 macOS 전용 의존(`~/Library/LaunchAgents` 쓰기, `launchctl` 호출, plist 소유권·원상복구 로직)을 지는 것은 정당화되지 않는다. `start_new_session=True` 한 줄이 실제 요구를 전부 만족한다 |
| systemd user unit(Linux) + launchd(macOS) 이중 지원 | 위와 같은 이유로 불필요. 게다가 OS 별 분기 두 벌을 문서·테스트가 모두 감당해야 한다 |
| 고전적 더블 포크 데몬화 | `Popen` 즉시 반환 + `start_new_session` + 표준 스트림 리다이렉트로 더블 포크가 막는 문제(좀비·제어 터미널 재획득)가 **하나도 남지 않는다**(YAGNI) |
| `nohup` 셸 래핑 | `start_new_session` 이 SIGHUP 면역을 이미 제공한다. 셸을 한 겹 더 끼우면 PID 가 래퍼의 것이 되어 신원 확인이 더 어려워진다 |
| 서버에 `/shutdown` 엔드포인트를 두고 `stop` 이 HTTP 로 종료 요청 | PID 재사용 위험은 사라지지만, **로컬의 아무 프로세스나 우리 서버를 끌 수 있게 된다.** 읽기 전용 원칙과 노출 표면 최소화에 어긋난다 |
| `pkill -f` 패턴으로 서버 종료(초판 `stop_serving` 방식 유지) | 패턴이 우연히 일치하는 남의 프로세스를 죽인다. PID + `ps` 신원 확인이 정확히 그 문제를 푼다 |
| 서버 생존 판정을 포트 프로브로 | 훅마다 소켓 연결 + 타임아웃 가능성. **훅을 지연시킬 수 있는 것은 넣지 않는다**(불변 원칙 1) |
| 서버 생존 판정을 PID + `kill(pid,0)` 로 | PID 재사용 문제가 남고, 훅의 뜨거운 경로에 프로세스 조회가 들어간다 |
| 크래시 시 훅이 서버를 되살림 | 요구가 아니다. 훅이 상주 프로세스를 띄우는 순간 요구 R-2("사용자가 직접 컨트롤")가 정면으로 깨진다 |
| FSEvents/`kqueue` 파일 감시로 즉시 반영 | 시간이 만드는 상태 전이(`stale`)를 못 잡아 **어차피 주기 루프가 필요하다.** 두 메커니즘을 함께 유지할 이유가 없고, stdlib 만으로는 이식성 있게 쓸 수 없다(불변 원칙 4) |
| WebSocket/SSE push | 5초 폴링이 이미 요구를 만족한다. 연결 수명·재연결 처리를 얻고 잃는 것은 최대 5초 지연 단축뿐 |
| 훅이 서버에 HTTP 로 이벤트를 직접 전송(CAM 방식) | 훅이 네트워크 호출을 하게 되고, 서버가 꺼져 있으면 훅이 지연·실패한다(불변 원칙 1 위반). 파일 append 는 서버 유무와 무관하게 항상 성공한다 |
| URL 인증 토큰 | 북마크 불가(요구 R-1 과 충돌). 루프백 + 화이트리스트 2개 + 읽기 전용에서 비용이 이득을 넘는다 |
| 적응형 수집 주기 | 측정 없는 최적화. R-M2 기준을 넘길 때 근거를 갖고 도입한다 |
| **루트 `install.sh` 에 `--hub` 플래그 추가**(설치 로직 공유) | "함께 설치되지 않는다"는 만족하지만 **허브가 coding-env 설치 스크립트 안에 계속 남는다** — 요구 R-5 의 취지(설치 동의의 분리)에 어긋난다. 그리고 `install.sh` 의 hub 문자열 0개를 강제하는 T25-21 을 쓸 수 없게 된다 |
| **공유 라이브러리 `install-lib.sh` 추출 후 양쪽에서 source** | 허브가 실제로 필요한 것은 "수정 감지 → `--force` 요구" 하나뿐인데, 검수 3회를 통과한 배포 스크립트를 구조적으로 흔든다. "수술적으로 변경한다"에 어긋난다 |
| env-update 판정을 manifest `files_count.hub` 로 | 루트 `install.sh` 가 허브를 만지지 않게 되므로 그 필드는 **남의 설치 상태를 기록하는 부정확한 값**이 된다(허브만 따로 지워도 갱신되지 않는다) |
| 허브 전용 manifest(`~/.claude/hub/.coding-env-hub.json`) | env-update 는 버전을 비교하지 않고 항상 최신으로 덮으므로 메타데이터가 필요 없다. 상태 파일이 하나 늘면 그것이 틀릴 수 있는 새 경로가 생긴다(YAGNI) |
| `hub/README.md` 대신 `docs/hub.md` | 허브 디렉토리 안에 두어야 `hub/install.sh` 와 나란히 발견된다. `docs/` 는 이 레포에서 설계 문서(`docs/prps/`)의 자리다 |
| `commands/hub.md` 도 배포에서 제외 | 커맨드 파일을 빼면 `/hub` 자체가 존재하지 않아 **설치 안내를 띄울 주체가 사라진다.** 커맨드는 배포하고 실행 코드만 분리하는 것이 미설치 UX 를 가능하게 한다 |

---

## 개정의 워크플로우 경로 판정

**전체 경로(설계 → 구현 → 검수) 대상이다.** 근거 4개 각각이 단독으로 요건을 충족한다:

- 새 모듈 추가(`hub_server.py`·`hub_daemon.py`) — 이 레포 최초의 **상주 프로세스**,
  그리고 **새 설치 스크립트**(`hub/install.sh`)
- 공개 인터페이스 변경(`/hub serve` **폐기** → `/hub server`, `HubConfig` 필드 교체,
  `install.sh` 의 배포 범위 축소, manifest 필드 제거)
- 5개 신규 + 12개 수정
- **민감 영역**: 세션을 벗어나 사는 프로세스의 기동/종료(**남의 프로세스를 죽일 수 있는 코드**),
  상시로 열리는 로컬 포트, 배포 스크립트의 소유 범위 변경

---

## 사용자 승인이 필요한 핵심 결정

1. **상시화 = 세션 무관 분리 프로세스**(`start_new_session=True`). 재부팅하면 사라지고 크래시하면
   그대로 죽되, **죽었다는 사실은 `status`·화면·`server.log` 세 곳에서 관측된다.** kill 전
   `ps` 신원 확인으로 PID 재사용 사고를 막는다. (launchd 는 「채택하지 않은 대안」으로 이동.)
2. **문서·설치 분리** — `hub/README.md` 신설 + `hub/install.sh` 독립 실행. 루트 `install.sh` 는
   허브를 **전혀 모르게** 된다(`grep -c hub install.sh` == 0 을 T25-21 이 강제).
   `/env-update` 는 `~/.claude/hub/bin/hub.py` **존재 여부**로 판정해 있을 때만 함께 갱신한다.
3. **`serve` 폐기 + `/hub` 암묵 기동 제거 + 상주 서버가 5초 주기 수집 전담**(훅은 하트비트로 위임).
   대가는 상시로 열린 로컬 포트 하나와 사용자가 끌 때까지 사는 프로세스 하나다.

### 함께 답이 필요한 열린 질문

| # | 질문 | 설계자의 기본안 |
|---|------|---------------|
| ~~Q1~~ | ~~비 macOS 지원~~ | **해소.** launchd 를 버려 POSIX 전반에서 동일하게 동작한다 |
| Q2 | 수집 주기 5초가 적절한가(배터리 vs 신선도) | **5초 기본 + `config.json` 조정.** R-M2 에서 실측해 기준 초과 시 재검토 |
| Q3 | `/hub`(인자 없음)가 서버가 꺼져 있을 때 **켤지 물어봐야** 하는가 | **안내만.** 물어보는 것도 자동 기동의 완곡한 형태이고, 요구 R-2 의 취지는 "내가 켠 것만 뜬다"이다 |
| Q4 | `hub/install.sh --uninstall` 을 포함할지 | **포함.** 허브는 상주 프로세스와 전역 훅을 남기므로 "어떻게 완전히 지우지?"가 실제 질문이 되고, **삭제 순서를 틀리면 되돌리기 어려운 상태**가 만들어진다 |
| Q5 | `--uninstall` 이 `events/`·`hub.html`·`config.json` 도 지울지 | **지우지 않고 경로만 안내.** 사용자 데이터이며, 설치 스크립트가 말없이 지우면 신뢰를 잃는다 |
| Q6 | `/env-update` 가 서버 재기동 확인을 **매번** 물을지 | **매번 묻는다.** 자동 기동 금지 원칙과의 경계에 있는 유일한 지점이라 침묵하지 않는다 |
