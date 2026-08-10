# 통합 허브 대시보드 (PRP)

> 문서 형식은 이 레포의 기존 PRP 관례(`session-dashboard.md` 계열)를 따른다.
> `/prp-plan` 의 템플릿(Task 목록·Validation Commands)은 「구현 마일스톤」·「검증 명령」 절로 흡수했다.

---

## 요구사항 요약

로컬 머신에서 돌고 있는 **모든 Claude Code 프로젝트**의 진행 상황(프로젝트 / 세션 / 단계)을
한 페이지에서 **읽기 전용**으로 보는 통합 허브를 만든다. 사용자는 Claude Desktop 앱과 Cursor 확장을
주로 쓰며(터미널 CLI 아님), 여러 프로젝트를 동시에 진행하는 동안 창을 옮겨 다니지 않고 한 화면에서
"어디가 돌고 있고 / 어디가 멈춰 있고 / 각각 어느 단계인지"를 알고 싶다.

명령·제어 기능은 범위 밖이다(중단·프롬프트 주입·승인은 인접 프로젝트 CAM 의 2단계 몫이다).
허브는 **파일에서 기계적으로 읽을 수 있는 사실만** 집계하고, 상주 서버(데몬)를 두지 않는다.

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
- **3번이 사실상의 off 스위치다.** `hub.html` 을 지우면 훅은 append(+리텐션)만 한다. `/hub` 를
  부르면 다시 생긴다.
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
| M9 | `design-architect` → 종료 → `implementer` 시작 | `inferred_phase="구현"`, `running=True` |
| M10 | `Explore` 만 실행 | `inferred_phase is None` |
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
| `serve` 포트 스캔 실패 시 자기가 띄운 Popen 핸들을 유지하고 terminate() 하는 안(검수 R1 nit) | 현재는 재프로브(`_probe_port`)만으로 REUSE/FREE/OCCUPIED 를 판정해 안전하다. 프로세스 생명주기(핸들 보관·종료 시점)를 바꾸는 변경이라 별도 설계 검토가 필요해 이번 라운드에는 보류한다 |
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
