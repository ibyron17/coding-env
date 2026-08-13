# 허브 — 세션 활동(서브에이전트) 노출 + 전역 커스텀 툴팁 컴포넌트 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_model.py`(데이터 계약) · `hub/bin/hub_template.html`(렌더·인터랙션) |
| 브랜치 | `feature/hub-dashboard` (HEAD `ac71456` + `hub_template.html` 미커밋 수정 있음 — 아래 「출발 상태」) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md) → [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — `SessionView`(공개 데이터 계약) 변경 + 대시보드 전역 인터랙션 컴포넌트 신설 |
| 규모 | Medium — 신규 0개 / 수정 6개 파일. Python 증분 약 +25/−20줄, 템플릿 증분 약 +120줄 |
| 새 외부 의존성 | **없음** (바닐라 CSS/JS · 빌드 단계 없음 · CDN 없음) |
| **승인 상태** | **미승인** — 「사용자 승인이 필요한 미결 선택지」 4건 확인 후 구현 착수 |

---

## 요구사항 요약

허브 대시보드의 세션 목록은 지금 "무슨 작업이었는지"를 사실상 알려주지 못한다. 세션 줄에
찍히는 서브에이전트 타입은 `SessionView.active_agent_types` 인데, 이 필드는
`compute_session_view`(`hub_model.py:341`)에서 **`ended_at_ms is None` 인 것만** 담기 때문에
세션이 끝나면(=대부분의 목록 항목) 항상 빈 배열이 된다. 그 결과 완료된 세션이 여러 개
나열되면 전부 `✓ 완료 · N시간 전` 만 반복된다. **요구 1** 은 세션에서 **실행된 모든**
서브에이전트 타입(종료된 것 포함)을 데이터 계약에 실어 화면에 보이게 한다 — 원재료
(`SessionFacts.subagents`)는 이미 다 모여 있고, 그것을 사람이 읽을 수 있게 내보내는 필드가
없을 뿐이다.

**요구 2** 는 대시보드에 남아 있는 네이티브 `title` 툴팁 4곳(`#dzh-refresh`·`.project-name`·
`.badge.tier`·`.usage-meta`)을 **이 파일 안의 커스텀 툴팁 컴포넌트 하나로 통일**한다. 네이티브
`title` 은 브라우저마다 대략 0.5~1초 지연이 있어 "정보를 확인하러 마우스를 올린" 사용자가
기다려야 하고, 지연·스타일·위치를 전혀 제어할 수 없다. 요구 1 이 만드는 서브에이전트 칩도
보조 설명(단계·진행 여부)을 이 컴포넌트로 전달하므로 두 요구는 한 배치로 묶는다.

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 완료된 세션 목록만 보고도 "이 프로젝트에서
> 무슨 에이전트가 돌았는지"를 알고 싶고, 설명이 필요한 요소에 마우스를 올리면 기다림 없이
> 곧바로 설명이 뜨기를 원한다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | **완료(`done`) 상태 세션에도** 실행됐던 서브에이전트 타입명이 보인다 | 자동 A7 + 수동 M1 |
| S2 | 같은 타입이 두 번 돌면 칩은 1개, 그중 하나라도 실행 중이면 진행 표시가 붙는다 | 자동 A2 + 수동 M2 |
| S3 | 서브에이전트가 없던 세션은 칩 영역이 아예 없다(빈 칩·`+0` 없음) | 자동 A3·A5 + 수동 M3 |
| S4 | 대시보드 어디에도 네이티브 `title` 툴팁이 뜨지 않는다 | T25-39(`title="` 부재) + 수동 M6 |
| S5 | 마우스 진입 후 **약 120ms** 에 툴팁이 뜬다. 스치기만 하면 뜨지 않는다 | 수동 M7 |
| S6 | 뷰포트 네 모서리의 트리거에서 툴팁이 화면 밖으로 잘리지 않는다 | 수동 M9 |
| S7 | Tab 으로 새로고침 버튼에 도달하면 툴팁이 **즉시** 뜨고 `Escape` 로 닫힌다 | 수동 M10 |
| S8 | 폴링 재렌더(30초 틱) **이후에 새로 그려진** 칩·배지에서도 툴팁이 동작한다 | 수동 M12 |
| S9 | `bash tests/run.sh` 전체 통과 (T25-11 수정 + T25-38~40 신규 포함) | 자동 |

---

## 출발 상태 (구현자가 먼저 알아야 하는 사실)

`hub/bin/hub_template.html` 에는 **커밋되지 않은 수정**이 있고(`git diff --stat` → +92/−28),
이 PRP 는 **그 미커밋 상태를 출발점으로** 설계됐다. 특히 다음 세 가지가 이번 설계의 전제다.

1. **세션 줄이 이미 한 번 바뀌었다.** `.short-id` 렌더링이 사라지고 `.session-time`
   (`elapsedLabel(session.last_event_at_ms)`)이 들어왔다. → **`tests/run.sh` T25-11 은 지금
   실패한다**(`escapeHtml(session.short_id)` 리터럴을 요구하는데 템플릿에 없다). 아래 「발견
   사항」 참조 — 이 배치에서 함께 고친다.
2. **카드 높이가 `340px` 로 고정되고 `.sessions` 만 내부 스크롤한다.** 따라서 칩이 늘어나도
   **카드 높이·그리드 배치는 변하지 않는다** — 영향은 "한 화면에 보이는 세션 수"뿐이다.
3. **`.card{overflow:hidden}` · `.sessions{overflow-y:auto}`** — 카드 내부 요소에서 출발하는
   CSS-only 툴팁(`::after`)은 이 두 컨테이너에 **잘린다**. 요구 2 가 `position:fixed` 싱글턴
   방식이어야 하는 결정적 이유다(결정 T1).

---

## 영향 범위

### 수정 파일 (6개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_model.py` | `SubagentRunView` 신설, `SessionView` 필드 3개 → 1개로 교체, `summarize_agent_runs` 신설, `infer_phase` 삭제, `compute_session_view` 3줄 | 요구 1 의 데이터 계약 |
| `hub/bin/hub_template.html` | CSS 규칙 8개 추가·1개 교체, 정적 노드 1개(`#dzh-tooltip`), `title=` 4곳 → `data-tooltip=`, `renderSession` 재작성 + 렌더 함수 3개 신설, 툴팁 IIFE 신설, 상단 주석 블록 보강 | 요구 1 렌더 + 요구 2 전부 |
| `tests/hub/test_hub_model.py` | `SummarizeAgentRunsTest` 신설(A1~A6), done 세션 회귀(A7), 계약·키 테스트(A8·A9), `InferPhaseTest` 삭제, `SessionView` 생성 2곳(258·419행) 갱신 | 요구 1 의 순수 로직 검증 |
| `tests/run.sh` | **T25-11 수정**, T25-38~40 신설, `test_desc`·헤더 주석을 `T25-1~T25-40` 으로 갱신 | 현재 실패 복구 + 새 불변식 grep 회귀 |
| `hub/README.md` | 「화면 배치」에 세션 줄 구성 2행 + 툴팁 1행 추가 | T25-40 및 문서 정합 |
| `docs/prps/hub-dashboard.md` | `SessionView` 블록·「3. 단계 추정」 절·테스트 M9/M10 행에 **개정/대체 표기 3곳**(내용 삭제 없음) | 두 설계 문서가 모순된 채 남지 않게 (직전 PRP 의 이력 보존 관례) |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_collect.py` | **I/O 레이어는 한 줄도 바뀌지 않는다.** `collect_snapshot` 은 `compose_project_views` 만 부르고 세션 필드를 직접 만들거나 읽지 않는다(`hub_collect.py:356-359`). 새 필드는 순수 레이어 안에서 파생된다 — 이 분리가 유지되는지가 이 PRP 의 구조 검증 지점이다 |
| `hub/bin/hub_parse.py`·`hub_usage.py` | 티어 1 파서·사용량 파서. 세션 계약과 접점 없음 |
| `hub/bin/hub.py`·`hub_server.py`·`hub_daemon.py`·`hub_hook.py`·`hub_settings.py` | 세션 필드를 읽는 곳이 없다(확인: `hub.py:57` 은 `len(snapshot.projects)` 만 쓴다). 훅이 기록하는 이벤트 스키마도 그대로다 — **새 훅·새 필드가 필요 없다**(원재료가 이미 있다) |
| `hub/install.sh` | 배포 파일 수 무변경(10개) → `HUB_FILE_COUNT` 그대로, T25-1 통과 |
| `commands/hub.md` | `/hub` 서브커맨드 규약과 `/hub status` 필드만 다룬다(확인: `active_agent_types`·`inferred_phase` 언급 0건). 화면 서술 없음 → **수정하지 않는다** |
| `tests/hub/` 의 나머지 파일 | `SessionView` 를 만들거나 세션 필드를 단언하는 테스트는 `test_hub_model.py` 뿐이다(확인: 258·419행) |

---

## 확정된 전제 (재론하지 않는다)

1. **단일 정적 HTML, 빌드 단계 없음.** 프레임워크·전처리기·CDN 금지. 툴팁은 이 파일 안의
   바닐라 CSS/JS 로만 만든다.
2. **`hub_model.py` 는 순수하다.** 파일시스템·시각·환경변수에 닿지 않는다(T25-10 이 기계적으로
   강제한다). `now_ms` 는 항상 인자로 받는다.
3. **불변식 H1′ 는 개정하지 않는다.** 폴링이 **내용을 갱신하는** 요소는 여전히 `#dzh-app` ·
   `#dzh-collected-at` · `#dzh-usage-body` · `#dzh-usage-summary` 네 개다. 새로 추가되는
   `#dzh-tooltip` 은 **폴링 대상이 아니고**(사용자 상호작용만 내용을 바꾼다) 네 요소 **바깥**의
   정적 싱글턴이라 H1′ 의 마지막 문장("사용자 상태를 가진 요소는 네 요소 바깥에 둔다")을
   그대로 만족한다.
4. **색각 안전 팔레트(Okabe–Ito 파랑–주황 축)를 유지한다.** 새 색 리터럴 0개 — 기존 토큰
   (`--ink`·`--bg`·`--soft`·`--accent-ink`·`--accent-soft`·`--line`·`--muted`)만 참조한다
   (T25-29 통과).
5. **읽기 전용 서버.** 툴팁·칩은 서버에 아무것도 쓰지 않는다. `localStorage` 도 쓰지 않는다
   (툴팁은 지속 상태가 없다).

---

# 요구 1 — 세션 활동(서브에이전트) 노출

## 데이터 모델

### 신설 — `SubagentRunView`

```python
@dataclass(frozen=True)
class SubagentRunView:
    """세션에서 실행된 서브에이전트 타입 1종의 표시 상태(같은 타입의 여러 실행을 하나로 합친 것)."""

    agent_type: str            # 훅이 준 원문 그대로. 예: "implementer", "workflow-subagent"
    phase: Phase | None        # PHASE_BY_AGENT_TYPE 에 없으면 None
    is_running: bool           # 같은 타입 실행 중 하나라도 진행 중이면 True
```

### 변경 — `SessionView`

```python
@dataclass(frozen=True)
class SessionView:
    session_id: str
    short_id: str
    state: SessionState
    base_state: Literal["working", "idle", "done"]
    last_event_at_ms: int
    task_excerpt: str | None
    agent_runs: tuple[SubagentRunView, ...]      # ★신규 — 아래 3개 필드를 대체한다
    # inferred_phase: Phase | None               ← 삭제
    # inferred_phase_running: bool               ← 삭제
    # active_agent_types: tuple[str, ...]        ← 삭제
```

- `active_agent_types` **대체**: `agent_runs` 는 이것의 상위집합이다(실행 중 정보는
  `is_running=True` 로 보존된다). 두 필드를 함께 두면 같은 사실의 출처가 둘이 된다.
- `inferred_phase`·`inferred_phase_running` **대체**: 각 실행에 `phase` 가 붙으므로 세션 단위
  단계는 `agent_runs` 에서 **파생 가능**하다(= "`phase` 가 null 이 아닌 첫 항목"). 계약에
  파생 가능한 중복을 싣지 않는다. 화면에 단계 라벨을 계속 띄울지는 **클라이언트 표시 결정**
  이며 서버 계약과 무관하다(승인 항목 1 — 두 안 모두 이 계약을 그대로 쓴다).

### `#dzh-data` JSON 계약 (변경 후)

```json
{
  "collected_at_ms": 1786000000000,
  "projects": [{
    "display_name": "coding-env", "path": "/Users/b/private/project/coding-env",
    "tier": 2, "state": "done", "last_activity_at_ms": 1786000000000,
    "sessions": [{
      "session_id": "…", "short_id": "a1b2c3d4",
      "state": "done", "base_state": "done",
      "last_event_at_ms": 1785990000000,
      "task_excerpt": "허브 대시보드에 …",
      "agent_runs": [
        {"agent_type": "code-reviewer",   "phase": "검수", "is_running": false},
        {"agent_type": "implementer",     "phase": "구현", "is_running": true},
        {"agent_type": "workflow-subagent","phase": null,  "is_running": false}
      ]
    }],
    "tier1": null, "note": null
  }],
  "unresolved_dir_names": [], "warnings": [], "usage": null
}
```

- 키 이름은 서버 dataclass 필드명 그대로(snake_case) — 기존 계약 규칙과 동일하다.
- 정렬은 **가장 최근에 시작된 타입이 앞**이다. 클라이언트는 순서를 다시 정하지 않는다.

## 인터페이스 (Python)

```python
def summarize_agent_runs(facts: SessionFacts) -> tuple[SubagentRunView, ...]:
    """세션의 모든 서브에이전트를 타입별로 합쳐 최근 시작 순으로 돌려준다(종료된 것도 포함)."""
```

구현 규칙 (전부 순수, 약 14줄 — 함수 1개 책임):

| # | 규칙 | 근거 |
|---|------|------|
| R1 | `agent_type` 이 빈 문자열이면 **제외** | `SubagentStop` 안전판(`hub_model.py:244`)이 만드는 빈 타입이 화면에 빈 칩으로 새는 것을 막는다. 기존 `active_agent_types` 에도 있던 잠재 결함이다 |
| R2 | 같은 `agent_type` 은 **1개로 합친다** | 같은 타입이 여러 번/동시에 돈다(테스트 M8 이 이미 그 사실을 고정한다). 칩이 `implementer, implementer` 로 중복되면 정보가 아니라 소음이다 |
| R3 | `is_running` = 그 타입의 실행 중 **하나라도** `ended_at_ms is None` | "지금 이 타입이 돌고 있나"가 사용자가 알고 싶은 것이다 |
| R4 | 정렬 키 = 그 타입의 `started_at_ms` **최댓값**, 내림차순. 동값이면 `agent_type` **오름차순** | 최근이 앞이어야 "어디까지 갔나"가 먼저 읽힌다. 명시적 타이브레이크가 없으면 순서가 흔들려 `snapshot_content_key` 가 달라지고 **내용이 안 바뀌었는데도 `hub.html` 이 재작성**된다(개정 쟁점 R3 의 쓰기 억제가 무력화) |
| R5 | `phase` = `PHASE_BY_AGENT_TYPE.get(agent_type)` | 단계 어휘는 서버 소유다. 클라이언트에 매핑을 복제하지 않는다 |

`compute_session_view` 의 변경 (3줄):

```python
    # 변경 전: inferred_phase, inferred_phase_running = infer_phase(facts)
    #          active_agent_types = tuple(sub.agent_type for sub in facts.subagents if sub.ended_at_ms is None)
    # 변경 후:
    agent_runs = summarize_agent_runs(facts)
```

`infer_phase` 는 **삭제**한다 — 유일한 호출자가 `compute_session_view` 였고(확인: 레포 전체
grep 결과 `hub_model.py:340` 과 테스트 2곳뿐), 그 지식(`PHASE_BY_AGENT_TYPE` 매핑 + "최근
시작이 이긴다")은 R4·R5 가 그대로 이어받는다. 섹션 제목 `# ---- 4. 단계 추정 ----` 은
`# ---- 4. 서브에이전트 요약 ----` 으로 바꾸고 `summarize_agent_runs` 를 그 자리에 둔다.

## 렌더링 (`hub_template.html`)

```js
/* 상수 */
var MAX_VISIBLE_AGENT_CHIPS = 2;            // 초과분은 "+N" 칩 하나로 접는다(결정 D4)
var AGENT_RUN_RUNNING_GLYPH = '●';          // 상태 배지의 working 글리프와 의도적으로 같은 모양
var AGENT_RUN_RUNNING_LABEL = '진행 중';
var AGENT_RUN_ENDED_LABEL = '종료';
var AGENT_RUN_NO_PHASE_LABEL = '워크플로우 단계 매핑 없음';

function agentRunTooltipText(run): string
    /** 칩 툴팁 문구. 순수 함수 — DOM 에 닿지 않는다. 예: "구현 단계 · 진행 중" */

function renderAgentChip(run): string
    /** 서브에이전트 타입 칩 하나. 실행 중이면 글리프 + 보조기술용 텍스트가 붙는다. */

function renderAgentRuns(runs): string
    /** 칩 목록. 상한을 넘는 타입은 "+N" 칩 하나로 접고 전체 목록을 그 툴팁에 담는다. */

function renderSession(session): string    // 변경 — phaseText·agentTypesText 를 renderAgentRuns 로 교체
```

### 변경 후 세션 줄 마크업

```html
<li>
  <div class="session-line">
    <span class="badge state-done"><span class="glyph" aria-hidden="true">✓</span>완료</span>
    <span class="session-time">2시간 5분 전</span>
    <span class="agent-runs">
      <span class="agent-chip" data-tooltip="검수 단계 · 종료">code-reviewer</span>
      <span class="agent-chip agent-chip-running" data-tooltip="구현 단계 · 진행 중">
        <span class="glyph" aria-hidden="true">●</span>implementer<span class="sr-only"> 진행 중</span>
      </span>
      <span class="agent-chip agent-chip-more" data-tooltip="design-architect, Explore">+2</span>
    </span>
  </div>
  <span class="excerpt">허브 대시보드에 …</span>
</li>
```

### 화면 (변경 전 / 후)

```
변경 전                                  변경 후
┌────────────────────────────┐          ┌────────────────────────────┐
│ ✓ 완료   2시간 전           │          │ ✓ 완료  2시간 전            │
│ 허브 대시보드에 …           │          │ code-reviewer  implementer  │
│                            │          │ 허브 대시보드에 …            │
│ ✓ 완료   5시간 전           │          │                             │
│                            │          │ ✓ 완료  5시간 전   +2 …      │
└────────────────────────────┘          └────────────────────────────┘
  무슨 작업이었는지 알 수 없다             실제로 돌았던 에이전트가 보인다
```

### CSS (신규·교체)

```css
/* .agent-types 규칙을 아래 4개로 교체한다 */
.agent-runs{display:inline-flex;flex-wrap:wrap;gap:4px}
.agent-chip{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;line-height:1.3;
            color:var(--muted);background:var(--soft);border-radius:6px;padding:2px 6px}
.agent-chip-running{color:var(--accent-ink);background:var(--accent-soft)}
.agent-chip-more{background:transparent;border:1px solid var(--line)}
.agent-chip .glyph{margin-right:2px}
.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;
         clip:rect(0,0,0,1px);white-space:nowrap;border:0}
```

> **GOTCHA 1 — `escapeHtml` 은 칩에서도 필수다.** `run.agent_type` 은 훅 페이로드에서 온
> 문자열이고 이제 **속성 자리(`data-tooltip="…"`)에도** 들어간다. T25-37(따옴표 이스케이프)이
> 지키는 성질이 여기서 두 번째 사용처를 얻는다 — 텍스트 자리와 속성 자리 **양쪽 모두**
> `escapeHtml` 을 통과시켜야 한다.

> **GOTCHA 2 — 색만으로 진행 중을 표시하지 않는다.** 실행 중 칩은 (a) 색(`--accent-ink`),
> (b) 글리프 `●`, (c) 보조기술용 텍스트 `진행 중` 세 채널을 갖는다. 글리프는
> `aria-hidden="true"` 라 낭독되지 않으므로 `.sr-only` 텍스트가 없으면 **AT 사용자만 진행
> 여부를 잃는다**(T25-30 이 지키는 원칙의 연장).

---

# 요구 2 — 전역 커스텀 툴팁 컴포넌트

## 마크업 계약

**트리거**: `data-tooltip="설명 문구"` 속성을 가진 임의의 요소. `title` 속성은 **전부 제거**한다
(남기면 네이티브 툴팁이 이중으로 뜬다).

**툴팁 본체**: 문서 전체에 하나뿐인 정적 싱글턴. `<aside id="dzh-usage">` 와 `#dzh-data`
사이(= `#dzh-app` 밖)에 둔다.

```html
<div id="dzh-tooltip" class="tooltip" role="tooltip"></div>
```

### 교체 대상 4곳 (현행 → 변경 후)

| 트리거 | 현행 | 변경 후 | `aria-describedby` |
|--------|------|---------|--------------------|
| `#dzh-refresh` | `title="새로고침"` (정적) | `data-tooltip="새로고침"` | **붙이지 않음** — `aria-label` 과 문구가 같아 이중 낭독이 된다 |
| `.project-name` | `title=` 전체 프로젝트명 | `data-tooltip=` 동일 | **붙이지 않음** — 접근성 이름(=요소 텍스트)과 같다. 말줄임은 시각 표현일 뿐 AT 는 전문을 읽는다 |
| `.badge.tier` | `title=` 티어 설명 | `data-tooltip=` 동일 | 붙인다(문구가 배지 텍스트와 다르다) |
| `.usage-meta` | `title=` 절대 타임스탬프 | `data-tooltip=` 동일 | 붙인다 |
| `.agent-chip`(신규) | — | `data-tooltip=` 단계·진행 여부 | 붙인다 |
| `.agent-chip-more`(신규) | — | `data-tooltip=` 접힌 타입 전체 목록 | 붙인다 |

## 인터페이스 (JS — 독립 IIFE)

테마 토글과 같은 층위의 **자기완결 IIFE** 로 둔다(스냅샷 렌더와 무관한 범용 UI 컴포넌트다).
기존 파일 문법(`var`, 함수 선언, 상수는 대문자 스네이크)을 그대로 따른다.

```js
/* 상수 */
var TOOLTIP_SHOW_DELAY_MS = 120;          // 마우스 hover-intent (결정 T3)
var TOOLTIP_GAP_PX = 8;                   // 트리거와 툴팁 사이 간격
var TOOLTIP_VIEWPORT_MARGIN_PX = 8;       // 뷰포트 경계 최소 여백
var TOOLTIP_VISIBLE_CLASS = 'tooltip-visible';
var TOOLTIP_ELEMENT_ID = 'dzh-tooltip';

/* 상태 — IIFE 모듈 스코프. 전역 변수를 만들지 않는다 */
var tooltipEl = document.getElementById(TOOLTIP_ELEMENT_ID);
var currentTrigger = null;                // 표시 중인 트리거(없으면 null)
var showTimerId = null;

function tooltipPosition(triggerRect, tooltipWidth, tooltipHeight, viewportWidth, viewportHeight)
    /** 트리거 사각형·툴팁 크기·뷰포트로 {left, top} 을 계산한다. 순수 함수 — DOM 에 닿지 않는다. */

function accessibleNameOf(element): string
    /** 트리거의 접근성 이름 근사값. aria-label 이 있으면 그것, 없으면 textContent 를 다듬는다. */

function shouldDescribe(trigger, text): boolean
    /** 툴팁 문구가 접근성 이름과 다를 때만 true — 같으면 aria-describedby 가 이중 낭독이 된다. */

function showTooltip(trigger): void
    /** 문구를 채우고 위치를 잡아 표시하고, 필요하면 aria-describedby 를 연결한다. */

function hideTooltip(): void
    /** 표시를 끄고 지연 타이머를 취소하고 aria-describedby 를 되돌린다. 언제 불려도 안전하다. */

function requestTooltip(trigger, isImmediate): void
    /** 표시 요청. 이미 다른 트리거를 보여주는 중이면 지연 없이 즉시 교체한다(결정 T3). */
```

### `tooltipPosition` — 배치 알고리즘 (순수)

```
left = 트리거 가로 중앙 - 툴팁폭/2       → [MARGIN, 뷰포트폭 - 툴팁폭 - MARGIN] 로 클램프
below = 트리거 bottom + GAP
above = 트리거 top - 툴팁높이 - GAP
top   = (below + 툴팁높이 + MARGIN <= 뷰포트높이) ? below : above
top   → [MARGIN, 뷰포트높이 - 툴팁높이 - MARGIN] 로 클램프
```

- **기본은 아래**다(결정 T4). 위쪽 기본은 `#dzh-refresh`(헤더 우측)의 툴팁이 `top:16px;
  right:16px` 인 `.theme-toggle`(z-index 30)과 겹칠 수 있다.
- 아래가 모자라면 위로 뒤집는다. 양쪽 다 모자란 극단(창 높이 200px 등)에서는 여백에 붙인다.
- 함수가 **순수**하므로 경계 조건을 코드만 읽고 검증할 수 있다(JS 러너가 없는 이 레포에서
  실질적으로 유일한 검증 수단이다 — 대응 수동 확인은 M9).

### 표시 순서 (GOTCHA — 이 순서를 지켜야 한다)

1. 지연 타이머 취소
2. `tooltipEl.textContent = text` — **`innerHTML` 이 아니다**(문구가 그대로 텍스트가 된다)
3. `tooltipEl.style.left = '0px'; tooltipEl.style.top = '0px';` ← **측정 전 좌표 리셋**
4. `offsetWidth` / `offsetHeight` 측정
5. `tooltipPosition(...)` 계산 → `style.left`·`style.top` 적용
6. `classList.add(TOOLTIP_VISIBLE_CLASS)`
7. `shouldDescribe` 면 `trigger.setAttribute('aria-describedby', TOOLTIP_ELEMENT_ID)`

> **GOTCHA 3 — 3번을 빼면 폭 측정이 틀린다.** `position:fixed` + `width:auto` 요소의
> 사용 가능 폭은 `viewportWidth - left` 다. 직전 표시가 화면 오른쪽이었다면 `left` 가 큰 값으로
> 남아 있어 shrink-to-fit 폭이 실제보다 작게 측정되고, 툴팁이 부당하게 여러 줄로 접힌다.

> **GOTCHA 4 — `visibility:hidden` 이어야 측정된다.** `hidden` 속성이나 `display:none` 은
> 레이아웃이 없어 `offsetWidth` 가 0 이다. 숨김은 반드시 `visibility` 로 한다(부수 효과로
> 접근성 트리에서도 제외돼 숨은 상태의 오낭독이 없다).

### 이벤트 배선 — 전부 위임 (`document`)

폴링이 `#dzh-app.innerHTML` 을 통째로 교체하므로 **개별 요소에 리스너를 붙이면 재렌더 후
전부 죽는다.** 리스너는 `document` 에만 붙인다.

| 이벤트 | 처리 |
|--------|------|
| `mouseover` | `closest('[data-tooltip]')` 히트 → `requestTooltip`. 히트 없고 **툴팁 내부도 아니면** → `hideTooltip` |
| `mouseleave`(document) | `hideTooltip` — 포인터가 창 밖으로 나가면 `mouseover` 가 더 안 온다 |
| `focusin` | 트리거면 **지연 0** 으로 표시(포커스 이동은 의도적 행위다) |
| `focusout` | `hideTooltip` |
| `keydown` | `Escape` → `hideTooltip` (WAI-ARIA APG · WCAG 1.4.13 dismissible) |
| `click` | `hideTooltip` — 네이티브 `title` 과 같은 거동. 클릭으로 트리거가 사라지는 경우(사용량 패널 접기 → `.usage-meta` 소멸)의 고아 툴팁도 이 경로가 막는다 |
| `scroll` (capture · passive) | `hideTooltip` — `position:fixed` 라 스크롤하면 트리거와 어긋난다. `.sessions` 내부 스크롤은 버블링하지 않으므로 **capture 로 받아야** 한다 |
| `resize`(window) | `hideTooltip` |
| `MutationObserver(childList)` on `#dzh-app` · `#dzh-usage-body` | `hideTooltip` — 30초 틱이 트리거 노드를 파괴하는데 포인터가 멈춰 있으면 아무 마우스 이벤트도 오지 않아 **낡은 문구가 남는다** |

> **툴팁 내부로 포인터가 들어와도 유지된다**(WCAG 1.4.13 hoverable). 그래서 `mouseover`
> 판정에 "툴팁 내부면 아무것도 하지 않는다"가 들어간다. 툴팁에 `pointer-events:none` 을 주면
> 이 기준을 만족할 수 없다(결정 T5).

### CSS

```css
.tooltip{position:fixed;left:0;top:0;z-index:40;max-width:min(280px,calc(100vw - 32px));
         padding:6px 9px;border-radius:8px;font-size:11.5px;line-height:1.45;font-weight:600;
         color:var(--bg);background:var(--ink);box-shadow:var(--shadow);
         overflow-wrap:anywhere;visibility:hidden}
.tooltip.tooltip-visible{visibility:visible}
```

- **z-index 40** — `.theme-toggle`(30)·`.usage`(20)보다 위여야 한다. `.usage-meta` 트리거가
  사용량 패널 **안**에 있으므로 그보다 낮으면 툴팁이 패널에 가린다.
- **색 반전(`--ink` 배경 / `--bg` 글자)** — 카드·패널이 모두 `--surface` 라, 같은 톤이면
  떠 있는 층으로 읽히지 않는다. 두 토큰은 라이트/다크 양쪽에서 서로 최대 대비를 갖도록 이미
  정의돼 있어 새 색 리터럴이 필요 없다.
- **트랜지션 없음** — 모션이 없으니 `prefers-reduced-motion` 분기도 필요 없다(직전 PRP 의
  캐럿 결정과 같은 판단).

## 접근성

| 항목 | 처리 |
|------|------|
| 마우스 | `mouseover` 위임 + 120ms hover-intent. 표시 중 다른 트리거로 이동하면 즉시 교체 |
| 키보드 | `focusin` 즉시 표시 / `focusout` 숨김. **네이티브 `title` 보다 개선**이다 — 현행 `#dzh-refresh` 는 포커스만으로는 아무 설명도 주지 않는다 |
| 해제 | `Escape` · 클릭 · 스크롤 · 리사이즈 · 트리거 이탈 (dismissible) |
| 유지 | 포인터가 툴팁 위로 들어와도 사라지지 않는다 (hoverable) · 자동으로 사라지지 않는다 (persistent) |
| 연결 | `role="tooltip"` + **표시 중에만** `aria-describedby="dzh-tooltip"` |
| 이중 낭독 방지 | 툴팁 문구가 접근성 이름과 같으면 `aria-describedby` 를 붙이지 않는다(`#dzh-refresh`·`.project-name`) |
| 기존 속성 보존 | `aria-describedby` 를 되돌릴 때 값이 `dzh-tooltip` 인 경우에만 제거한다(확인: 현재 이 속성을 쓰는 요소는 0개지만, 남의 값을 지우지 않는 것이 계약이다) |
| 알려진 한계 | 포커스 불가 요소(`.badge.tier`·`.agent-chip`·`.usage-meta`·`.project-name`)의 툴팁은 **마우스 전용**이다 — 네이티브 `title` 이 가진 한계와 정확히 같고, 이번 변경이 새로 만드는 손실이 아니다. 그래서 **필수 정보는 툴팁에만 두지 않는다**: 티어 배지는 텍스트 자체가 설명형(`대시보드 추적`)이고, 칩은 타입명·진행 글리프·`.sr-only` 텍스트가 항상 보인다. 툴팁은 **보조 채널**이다 |
| 기각 | 포커스 불가 요소에 `tabindex="0"` 을 붙여 키보드로 도달하게 하는 안 — 프로젝트 9개 × 세션 3개 × 칩 2~3개면 탭 스톱이 수십 개가 되어 키보드 사용자에게 **순손실**이다(대안 6) |

---

## 설계 결정과 근거

| # | 결정 | 근거 |
|---|------|------|
| D1 | `active_agent_types` 를 `agent_runs` 로 **대체**(병존 아님) | 새 필드가 상위집합이다. 같은 사실의 출처를 둘로 두면 어긋날 자유도만 생긴다 |
| D2 | 타입별로 **합치고**(dedup) 최근 시작 순으로 정렬 | R2·R4. `implementer, implementer` 는 정보가 아니다. 순서 타이브레이크는 `snapshot_content_key` 안정성 문제이기도 하다 |
| D3 | `phase` 를 **실행 항목에** 싣고 세션 단위 `inferred_phase` 는 제거 | 단계 매핑은 서버 소유 어휘(`PHASE_BY_AGENT_TYPE`)이므로 클라이언트에 복제하지 않는다. 반면 "세션의 단계" 는 `agent_runs` 에서 파생 가능한 중복이다 |
| D4 | 칩 표시 상한 **2개** + `+N` 칩(전체 목록은 그 툴팁) | 카드 폭이 320~486px 다. `design-architect`(16자) + `code-reviewer`(13자)만으로 11px 모노스페이스 약 190px — 3개면 두 줄이 되고 세션당 높이가 늘어 `.sessions` 내부 스크롤이 깊어진다. 상한은 상수 1개라 되돌리기 쉽다(승인 항목 2) |
| D5 | 상한 처리(자르기)는 **클라이언트**, 요약(dedup·정렬)은 **서버** | 레이어 원칙: 서버는 "사실을 다 준다", 화면은 "공간에 맞춰 고른다". 서버가 자르면 툴팁에 실을 나머지 목록을 잃는다 |
| T1 | 툴팁은 `position:fixed` **싱글턴 + JS** | `.card{overflow:hidden}`·`.sessions{overflow-y:auto}` 안에서 출발하는 CSS-only 툴팁(`::after`)은 **잘린다**. 이건 취향이 아니라 이 파일의 기하학적 제약이다 |
| T2 | 리스너는 `document` **위임** | 폴링이 `#dzh-app` 자식을 통째로 교체한다(불변식 H1′). 개별 부착은 재렌더마다 재배선이 필요하고, 그 재배선을 잊는 순간 조용히 죽는다 |
| T3 | 마우스 **120ms** · 키보드 **0ms** · 표시 중 교체 **0ms** · 숨김 **0ms** | 120ms 는 "즉시"로 체감되는 상한(약 150~200ms) 아래이면서, 포인터가 폭 60px 배지를 통상 속도(≈500px/s)로 지나칠 때 머무는 시간(≈120ms)과 같아 **스치는 이동을 걸러낸다**. 네이티브(0.5~1초)보다 4~8배 빠르다. 키보드 포커스는 그 자체가 의도적 행위라 지연이 방해다. 이미 툴팁이 떠 있는 상태의 이동은 "탐색 중"이므로 지연 없이 따라가야 한다 |
| T4 | 기본 배치는 **아래**, 모자라면 위로 뒤집기 | 위를 기본으로 하면 헤더의 `#dzh-refresh` 툴팁이 `.theme-toggle`(고정 우상단)과 겹친다. 트리거 자신의 라벨을 가리지 않는 것도 아래가 낫다 |
| T5 | 툴팁에 `pointer-events:none` 을 주지 **않는다** | WCAG 1.4.13 의 hoverable 을 만족하려면 포인터가 툴팁 위에 올라갈 수 있어야 한다. 대가(툴팁이 드물게 클릭을 한 번 먹는다)는 클릭→숨김으로 흡수된다 |
| T6 | 고아 툴팁 방지에 **MutationObserver** | 대안은 `render()` 안에서 `hideTooltip()` 을 부르는 1줄인데, 그러려면 툴팁이 렌더 IIFE 안으로 들어와야 한다. 관찰자 4줄로 두 IIFE 의 독립성을 지키고, 앞으로 추가되는 다른 재렌더 경로도 자동으로 덮는다 |
| T7 | `aria-describedby` 는 **표시 중에만**, 문구가 접근성 이름과 **다를 때만** | 싱글턴 하나를 여러 트리거가 공유하므로 상시 연결이 불가능하다. 문구가 이름과 같으면 "새로고침, 새로고침"이 된다 |
| — | 디자인 패턴 도입 없음 | 순수 함수 1개 + 표시/숨김 2개 + 위임 리스너 8개다. 상태 기계 클래스도, 이벤트 버스도, 플레이스먼트 엔진도 도입할 근거가 없다(YAGNI) |

> **개정됨(D4).** `+N` 오버플로 칩은 [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)
> 결정 K1~K3 으로 제거됐다. 상한 2개는 유지하되(안 A) 상한 밖으로 밀린 종료 타입은 표시되지
> 않는다.

> **유지됨(D5, 부분 개정).** "자르기는 클라이언트, 요약은 서버" 는 그대로다. 다만 정렬 규칙이
> "실행 중 먼저 → 최근 시작순" 으로 바뀌었다(결정 K2, [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)).

### `hub-dashboard.md` 의 개정 (이력 보존 — 직전 PRP 와 같은 방식)

내용을 지우지 않고 **대체 표기만 덧붙인다**.

| 위치 | 추가할 문장 |
|------|-------------|
| `SessionView` dataclass 블록(209~218행 근처) | `> **개정됨.** `inferred_phase`·`inferred_phase_running`·`active_agent_types` 세 필드는 [`hub-session-activity-and-tooltip.md`](./hub-session-activity-and-tooltip.md) 의 `agent_runs: tuple[SubagentRunView, ...]` 로 대체됐다(결정 D1·D3).` |
| 「3. 단계 추정」 절 제목 아래 | `> **개정됨.** `infer_phase()` 는 삭제되고 `summarize_agent_runs()` 가 각 서브에이전트 타입에 `phase` 를 붙인다. "티어 1 이 이긴다"·"매핑되지 않은 타입은 단계로 승격하지 않는다"(→ `phase=None`)는 그대로다. **"추정" 라벨 규칙**은 세션 단위 단계를 화면에 띄우는 경우에만 적용된다.` |
| 「테스트 계획」 M9·M10 행 | 각 행 끝에 ` → 대체됨(hub-session-activity-and-tooltip.md A1·A4)` |

---

## 발견 사항 — 이번 변경이 만들지 않은 문제

수술적 변경 원칙에 따라 **1번만 이 배치에서 고치고**(요구 1 이 같은 코드를 재작성하므로
피할 수 없다), 나머지는 **언급만 한다**.

| # | 발견 | 처리 |
|---|------|------|
| 1 | **`tests/run.sh` T25-11 이 지금 실패한다.** 미커밋 수정이 `escapeHtml(session.short_id)` 렌더를 없앴는데 검사는 그 리터럴을 요구한다 | **이 배치에서 수정**한다. 검사의 의도("세션 줄의 동적 값이 이스케이프 없이 innerHTML 에 들어가지 않는다")를 살려, 부정 검사(`+ session.` 형태의 무이스케이프 삽입 금지)는 유지하고 긍정 검사 대상을 `escapeHtml(run.agent_type)` 로 바꾼다 |
| 2 | `snapshot.unresolved_dir_names` 가 **아무데도 렌더되지 않는다**(미커밋 수정이 `.unresolved` 렌더와 CSS 를 삭제). 계약에는 남아 있고 `hub/README.md` 는 아직 "미확인 프로젝트 N개로 접혀 표시된다"고 적혀 있다 | **언급만 한다.** 이 PRP 의 요구와 무관하다. 별도 티켓(다시 표시할지 / 계약에서 뺄지) |
| 3 | `.theme-toggle` 에 `:focus-visible` 규칙이 없다 | 직전 PRP 에서도 언급만 한 항목. 그대로 둔다 |
| 4 | **이벤트 읽기 창이 오늘+어제 2일**이라, 그보다 전에 `SubagentStart` 가 있었던 세션은 이 변경 후에도 칩이 비어 있을 수 있다 | 요구 1 의 범위 밖(리스크 1 에 명시). 해결책(창 확대·세션 요약 캐시)은 수집 비용과 맞바꾸는 별도 설계다 |

---

## 테스트 계획

검증 정본: `bash tests/run.sh`(전체) / `python3 -m unittest discover -s tests/hub -t .`(파이썬).
이 레포에는 별도 linter·type checker 설정이 없다. **JS 테스트 러너는 도입하지 않는다**
(외부 의존성 금지 전제) — 템플릿은 grep 회귀 + 수동 확인 2축으로 검증한다.

### 자동 — Python 단위 테스트 (`tests/hub/test_hub_model.py`)

신설 클래스 `SummarizeAgentRunsTest`. 기존 헬퍼(`_event`·`_facts_from`)를 그대로 쓴다.

| # | 이름 | 입력 | 기대 |
|---|------|------|------|
| A1 | `test_a1_all_started_types_survive_after_completion` | `design-architect` Start/Stop → `implementer` Start/Stop → `code-reviewer` Start/Stop | 3개. 순서 `code-reviewer` → `implementer` → `design-architect`. 전부 `is_running=False`. `phase` = 검수·구현·설계 |
| A2 | `test_a2_same_type_is_merged_and_running_wins` | `implementer` Start(+0)/Stop(+100), `implementer` Start(+200) 미종료 | 1개, `is_running=True` |
| A3 | `test_a3_empty_agent_type_is_excluded` | `SubagentStart(agent_type="")` | `()` |
| A4 | `test_a4_unmapped_type_has_no_phase` | `workflow-subagent` Start | 1개, `phase is None`, `is_running=True` |
| A5 | `test_a5_no_subagent_yields_empty_tuple` | `UserPromptSubmit` 만 | `()` |
| A6 | `test_a6_same_start_time_breaks_tie_by_type_name` | 두 타입 같은 `started_at_ms` | `agent_type` 오름차순 (정렬 안정성 = `hub.html` 재작성 억제의 전제) |
| **A7** | `test_a7_done_session_still_exposes_agent_runs` | `implementer` Start/Stop → `SessionEnd` | `view.state == "done"` **이고** `len(view.agent_runs) == 1`, `is_running=False` — **이 PRP 가 고치는 결함의 직접 회귀 테스트** |
| A8 | `test_a8_agent_runs_reaches_json_contract` | `render_hub_html` 결과 파싱 | `parsed["projects"][0]["sessions"][0]["agent_runs"][0]["agent_type"]` 이 원문과 같다. `active_agent_types`·`inferred_phase` 키가 **없다** |
| A9 | `test_a9_agent_runs_difference_changes_content_key` | `agent_runs` 만 다른 두 스냅샷 | `snapshot_content_key` 가 다르다(내용 변화가 재작성을 유발해야 한다) |

기존 테스트 수정 (그 외 전부 무수정 통과가 1차 회귀 안전망이다):

| 위치 | 변경 |
|------|------|
| `InferPhaseTest`(106~124행, M9·M10) | **삭제.** 검증하던 지식은 A1(최근 시작 우선 + 매핑)과 A4(미매핑)가 이어받는다 |
| `RenderHubHtmlTest._minimal_snapshot`(254~267행) | `SessionView(...)` 인자에서 `inferred_phase`·`inferred_phase_running`·`active_agent_types` 삭제, `agent_runs=()` 추가 |
| `SnapshotContentKeyTest._session`(415~420행) | 동일 |

### 자동 — `tests/run.sh` grep 회귀

`test_hub_docs_and_constants()` 안. **함수 상단 `test_desc` 와 2010행 주석을
`T25-1~T25-40` 으로 갱신할 것.**

```bash
  # T25-11(수정 — 세션 줄 재구성 반영): 세션 줄의 동적 값은 반드시 escapeHtml 을 통과한다.
  # 기존 부정 검사(`+ session.short_id +` 리터럴 금지)는 **그대로 둔다** — short_id 렌더가
  # 폐기됐어도 되살아나는 것을 막는 값이 있다. 아래 긍정 검사만 새 렌더 대상으로 교체한다:
  #   삭제:  grep -qF "escapeHtml(session.short_id)"    ← 렌더되지 않는 값을 요구해 현재 실패 중
  #   신설:  grep -qF "escapeHtml(run.agent_type)"      ← 세션 줄이 실제로 넣는 동적 값
  if ! grep -qF "escapeHtml(run.agent_type)" "$hub_template_file"; then
    record_failure "$test_name" "T25-11: 서브에이전트 타입명이 escapeHtml 없이 삽입됨"
    return 1
  fi

  # T25-38(요구 1 회귀): 세션 표시가 '실행 중인 것만' 으로 되돌아가지 않는다.
  if grep -qF "active_agent_types" "$hub_template_file" "$REPO_ROOT/hub/bin/hub_model.py"; then
    record_failure "$test_name" "T25-38: active_agent_types 가 부활함 — 완료 세션이 다시 빈 목록이 된다"
    return 1
  fi
  local session_activity_token
  for session_activity_token in "summarize_agent_runs" "agent_runs"; do
    if ! grep -qF "$session_activity_token" "$REPO_ROOT/hub/bin/hub_model.py"; then
      record_failure "$test_name" "T25-38: hub_model.py 에 $session_activity_token 이 없음"
      return 1
    fi
  done
  for session_activity_token in "renderAgentRuns" "agent-chip" "MAX_VISIBLE_AGENT_CHIPS"; do
    if ! grep -qF "$session_activity_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-38: hub_template.html 에 $session_activity_token 이 없음"
      return 1
    fi
  done

  # T25-39(요구 2 회귀): 네이티브 title 툴팁이 하나도 남지 않고, 커스텀 툴팁이 위임·접근성·
  # 해제 경로를 모두 갖는다. (<title> 요소는 속성 형태가 아니라 이 검사에 걸리지 않는다)
  if grep -qF 'title="' "$hub_template_file"; then
    record_failure "$test_name" "T25-39: 네이티브 title 속성이 남아 있음 — 툴팁이 이중으로 뜬다"
    return 1
  fi
  local tooltip_token
  for tooltip_token in 'id="dzh-tooltip"' 'role="tooltip"' 'data-tooltip' 'aria-describedby' \
                       "'mouseover'" "'focusin'" "Escape" "MutationObserver"; do
    if ! grep -qF -- "$tooltip_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-39: hub_template.html 에 툴팁 계약($tooltip_token)이 없음"
      return 1
    fi
  done

  # T25-40(문서 정합): 세션 줄 구성과 툴팁 거동이 hub/README.md 에 반영돼 있다.
  for doc_token in "서브에이전트" "툴팁"; do
    if ! grep -qF "$doc_token" "$REPO_ROOT/hub/README.md"; then
      record_failure "$test_name" "T25-40: hub/README.md 에 화면 설명($doc_token)이 없음"
      return 1
    fi
  done
```

> `doc_token` 지역 변수는 T25-36 블록에 이미 선언돼 있으므로 재선언하지 않는다.

### 기존 자동 검사에 대한 영향 (확인 결과)

| 검사 | 판정 | 근거 |
|------|------|------|
| T25-1 (`HUB_FILE_COUNT`) | 무영향 | 신규 배포 파일 0개 |
| T25-10 (순수 레이어에 파일시스템 접근 없음) | 무영향 | `summarize_agent_runs` 는 인자만 읽는다 |
| T25-12 (`renderTier1ActiveStep`·`impl_done`·`직전 `) | 무영향 | 티어 1 렌더·`stateLabel` 미변경 |
| T25-28 (테마) · T25-29 (구 팔레트 부재) | 무영향 | 새 색 리터럴 0개, 테마 코드 미변경 |
| T25-30 (`STATE_GLYPH`·`aria-hidden`) | 무영향 | 유지 + 칩 글리프에서 `aria-hidden` 이 하나 더 는다 |
| T25-33 (`usageEl.innerHTML` 부재) | 무영향 | 사용량 렌더 미변경 |
| T25-34 (`aria-expanded`·`role="progressbar"`) | 무영향 | 사용량 마크업 미변경 |
| T25-37 (`escapeHtml` 따옴표) | **무영향 + 강화** | 칩의 `data-tooltip` 이 두 번째 속성 자리 사용처가 된다 |
| `tests/hub/` 의 `test_hub_model.py` 외 전부 | 무영향 | 세션 필드를 만들거나 단언하지 않는다 |

### 수동 확인 목록 (브라우저 실검증 — 자동화 불가)

**A. 세션 활동**
- [ ] M1 — **완료 상태 세션**에 실행됐던 타입명이 보인다(이 PRP 의 존재 이유)
- [ ] M2 — 실행 중 칩에 `●` 글리프 + 강조색이 붙고, 종료 칩은 중립색이다
- [ ] M3 — 서브에이전트가 없던 세션에 빈 칩·`+0` 이 없다
- [ ] M4 — `+N` 칩에 마우스를 올리면 접힌 타입 전체가 툴팁에 나온다
- [ ] M5 — 320px 열에서 칩이 카드 밖으로 넘치지 않고, 카드 높이(340px)가 변하지 않는다
      (`.sessions` 내부 스크롤로 흡수된다)

**B. 툴팁 — 기본 거동**
- [ ] M6 — 네 트리거(새로고침·프로젝트명·티어 배지·사용량 메타) 모두 커스텀 툴팁이 뜨고,
      **네이티브 툴팁이 뒤이어 뜨지 않는다**
- [ ] M7 — 마우스를 올린 뒤 체감상 즉시(≈120ms) 뜬다. 카드 위를 **빠르게 스쳐 지나가면**
      아무것도 뜨지 않는다
- [ ] M8 — 툴팁이 떠 있는 상태에서 옆 칩으로 이동하면 **지연 없이** 문구가 바뀐다
- [ ] M9 — 뷰포트 네 모서리(맨 위 카드·맨 아래 카드·좌우 끝 열)의 트리거에서 툴팁이 잘리지
      않는다. 아래가 좁으면 위로 뒤집힌다. 창 높이 300px 에서도 화면 안에 있다

**C. 툴팁 — 접근성·수명**
- [ ] M10 — Tab 으로 새로고침 버튼에 도달 → 툴팁 **즉시** 표시, `Escape` 로 닫힘, Tab 이탈로 닫힘
- [ ] M11 — VoiceOver: 새로고침 버튼에서 "새로고침"이 **한 번만** 낭독된다(이중 낭독 없음).
      티어 배지 툴팁 문구는 배지 텍스트와 겹치지 않는다
- [ ] M12 — 30초 틱 재렌더 **이후** 새로 그려진 칩·배지에서 툴팁이 동작한다(위임 회귀)
- [ ] M13 — 툴팁 표시 중 스크롤·창 리사이즈·클릭 → 즉시 사라진다. 사용량 패널을 접어
      `.usage-meta` 가 사라져도 고아 툴팁이 남지 않는다
- [ ] M14 — 툴팁 위로 포인터를 옮겨도 사라지지 않는다(WCAG 1.4.13 hoverable)
- [ ] M15 — 라이트/다크 양쪽에서 툴팁 대비가 충분하고, 사용량 패널·테마 토글 **위**에 그려진다
- [ ] M16 — `file://` 로 열어도 툴팁이 동작하고 콘솔 에러가 없다

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 검증 |
|---|------|------|
| 1 | `hub_model.py`: `SubagentRunView` + `summarize_agent_runs` + `SessionView` 교체 + `infer_phase` 삭제 / `test_hub_model.py` A1~A9 + 기존 3곳 수정 | `python3 -m unittest discover -s tests/hub -t .` 통과 |
| 2 | 템플릿 렌더: `renderAgentChip`·`renderAgentRuns`·`agentRunTooltipText` + `renderSession` 재작성 + CSS 6개. `data-tooltip` 속성만 붙이고 **툴팁 컴포넌트는 아직 없다** | 수동 M1~M5. 완료 세션에 타입명이 보인다 |
| 3 | 툴팁 컴포넌트: `#dzh-tooltip` 노드 + CSS 2개 + 독립 IIFE + 기존 `title=` 4곳 교체 | 수동 M6~M16 |
| 4 | 문서·테스트: `run.sh` T25-11 수정·T25-38~40·`test_desc` / `hub/README.md` / `hub-dashboard.md` 개정 표기 3곳 | `bash tests/run.sh` 전체 통과 |

1 과 2 는 순서를 지켜야 한다(2 가 1 의 필드를 읽는다). 3 은 2 에 의존한다(트리거가 있어야
확인이 된다). 각 마일스톤은 그 자체로 커밋 가능하다.

---

## 리스크와 완화책

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | **이벤트 창(오늘+어제) 밖의 세션은 여전히 칩이 없다** | 사용자가 "여전히 안 보인다"고 느낄 수 있다 | 이 PRP 의 범위 밖임을 명시. 창 안의 세션에서는 확실히 개선된다(A7). 창 확대는 수집 비용과 맞바꾸는 별도 설계 |
| 2 | **구버전 `hub.html` 이 남아 있는 과도기** | 새 `hub_model` + 옛 템플릿 조합에서 칩이 안 보인다(옛 코드가 없는 필드를 읽는다) | 무해하고 자기치유다 — 다음 수집(서버 5초 / 훅 폴백)이 새 템플릿으로 다시 쓴다. `hub/install.sh` 로 `bin/` 을 갱신해야 새 템플릿이 배포되는 점을 완료 보고에 적는다 |
| 3 | **`hub.html` 이 배포 직후 1회 전면 재작성**된다(`snapshot_content_key` 변경) | 없음 | 정상 동작. 이후에는 내용이 바뀔 때만 쓴다 |
| 4 | **칩 상한 2개가 정보를 가린다** | 세 번째 이후 타입이 한눈에 안 보인다 | `+N` 툴팁이 전체를 담는다. 상수 1개로 조절(승인 항목 2) |
| 5 | **툴팁이 클릭을 한 번 먹는다**(`pointer-events` 유지의 대가) | 드물게 클릭 1회 손실 | 클릭→숨김이라 두 번째 클릭은 통한다. 기하학상 8px 간격 밖에서만 발생 |
| 6 | **`aria-describedby` 동적 부착의 AT 지원 편차** | 스크린리더가 설명을 놓칠 수 있다 | 필수 정보를 툴팁에만 두지 않는다(배지 텍스트·칩 텍스트·`.sr-only`). M11 로 실측 확인 |
| 7 | **위임 리스너가 `document` 에 8개 붙는다** | 이벤트 소음 | 전부 조건 판정 1~2회로 끝나는 짧은 핸들러다. `scroll` 은 `passive:true` 로 스크롤 성능에 영향을 주지 않는다 |
| 8 | **`title=` 전면 금지 검사(T25-39)가 앞으로 걸림돌이 될 수 있다** | 새 툴팁을 `title` 로 붙이려는 시도가 막힌다 | 그것이 의도다. 실패 메시지에 `data-tooltip` 을 쓰라는 안내를 담는다 |
| 9 | **칩 줄바꿈으로 한 화면에 보이는 세션이 3 → 2 로 줄 수 있다** | 스크롤이 늘어난다 | 카드 높이는 고정이라 배치는 안 깨진다. 상한 2개가 대부분의 세션을 한 줄에 유지한다(M5 확인) |

---

## 검토했으나 채택하지 않은 대안

1. **`title` 속성을 남기고 CSS `::after` 로만 커스텀 표시.** JS 0줄이라 가장 싸다. 그러나
   (a) `title` 이 남으면 네이티브 툴팁이 **이중으로** 뜨고, (b) `.card{overflow:hidden}` ·
   `.sessions{overflow-y:auto}` 가 툴팁을 **잘라먹으며**, (c) 뷰포트 경계 보정이 CSS 로는
   불가능하다 → 기각(결정 T1).
2. **트리거마다 리스너를 직접 붙이고 폴링 후 재배선.** 위임보다 직관적이다. 그러나 재배선
   지점이 `render()` 안으로 들어가 렌더와 인터랙션이 얽히고, 새 재렌더 경로가 추가될 때
   **조용히 죽는다** → 기각(결정 T2).
3. **HTML `popover` 속성 + CSS anchor positioning.** top-layer·light dismiss 를 무료로 얻는다.
   그러나 anchor positioning 은 브라우저 지원이 갈려 **좌표 계산 JS 가 여전히 필요**하고,
   `popover` + `aria-describedby` 조합의 AT 거동 편차가 있으며, top-layer 의 이득은 `z-index:40`
   으로 이미 충분하다. 얻는 것보다 불확실성이 크다 → 기각.
4. **세션당 서브에이전트 실행 이력을 전부(중복·시각 포함) 계약에 싣기.** 나중에 타임라인을
   그릴 여지가 생긴다. 그러나 지금 화면이 쓰지 않는 데이터를 계약에 넣는 것은 추측성 확장이고,
   `hub.html` 크기와 `snapshot_content_key` 변동 빈도만 늘린다 → 기각(YAGNI).
5. **`inferred_phase` 를 그대로 두고 칩만 추가.** 변경이 가장 작다. 그러나 같은 사실이 두
   필드로 존재하고 화면에 `implementer` 와 `구현 추정` 이 나란히 찍힌다(같은 말의 반복) →
   기각. 단, **화면에 단계 라벨을 유지하고 싶다면** 클라이언트에서 `agent_runs` 로 파생할 수
   있어 서버 계약 변경 없이 가능하다(승인 항목 1 의 옵션 B).
6. **포커스 불가 트리거에 `tabindex="0"`.** 키보드로도 툴팁을 볼 수 있다. 그러나 탭 스톱이
   수십 개로 늘어 키보드 사용자에게 순손실이고, APG 도 툴팁을 **원래 포커스 가능한 요소**에
   붙이라고 말한다 → 기각. 대신 필수 정보를 툴팁 밖(보이는 텍스트·`.sr-only`)에 둔다.
7. **툴팁에 페이드 트랜지션.** 부드럽다. 그러나 `prefers-reduced-motion` 분기와 표시 지연이
   겹쳐 체감 지연이 되고, 요구는 "빠르게"다 → 기각.
8. **JS 테스트 러너(node/jest) 도입으로 `tooltipPosition` 단위 테스트.** "새 외부 의존성
   금지 · 빌드 단계 없음" 전제와 정면 충돌 → 기각. 순수 함수로 분리해 **읽기 검증 가능성**만
   확보하고 경계 조건은 수동 M9 로 덮는다.
9. **툴팁 문구를 서버가 전부 만들어 내려보내기(칩 툴팁 포함).** 표현이 한곳에 모인다.
   그러나 화면 문구는 클라이언트 관심사이고, `hub.html` 에 표시용 문자열이 중복 인라인되어
   커진다 → 기각. 서버는 사실(`phase`·`is_running`)만 준다.

---

## 사용자 승인이 필요한 미결 선택지

### 승인 항목 1 — 단계(설계/구현/검수) 라벨을 화면에 계속 띄울까 (결정 D3)

**두 안 모두 서버 계약(`agent_runs` + 실행별 `phase`)은 동일하다.** 차이는 렌더링뿐이다.

| 안 | 세션 줄 | 장단 |
|----|---------|------|
| **A. 칩 툴팁 전용** (권고) | `✓ 완료  2시간 전  code-reviewer  implementer` | 가장 조밀하다. `implementer` 와 `구현 추정` 의 중복이 사라진다. 단계 어휘는 마우스 오버로만 보인다 |
| B. 파생 단계 스팬 유지 | `✓ 완료  2시간 전  code-reviewer  implementer  검수 추정` | 티어 1 카드의 단계 어휘와 화면상 일관된다. 대가는 줄 길이 + 같은 말의 반복. 클라이언트 2줄(`agent_runs` 에서 `phase` 가 null 이 아닌 첫 항목)로 구현 |

A 를 고르면 `hub-dashboard.md` 의 "화면에 `추정` 라벨을 반드시 붙인다" 규칙은 **적용 대상이
없어진다**(개정 표기로 남긴다). B 를 고르면 그 규칙이 그대로 산다.

### 승인 항목 2 — 칩 표시 상한 `MAX_VISIBLE_AGENT_CHIPS` (결정 D4)

| 안 | 결과 | 비고 |
|----|------|------|
| **A. 2개 + `+N`** (권고) | 대부분의 세션이 한 줄에 들어간다 | 320px 열 기준. 전체 목록은 `+N` 툴팁 |
| B. 3개 + `+N` | 전체 경로 세션(설계·구현·검수)이 다 보인다 | 320px 열에서 두 줄이 되어 세션당 높이가 는다 |
| C. 상한 없음(전부 줄바꿈) | 정보 손실 0 | `Explore` 가 섞이면 세션 하나가 카드 절반을 먹는다 |

> **재결정됨.** 상한 2개는 유지, `+N` 칩은 폐기(결정 K1, [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)).

### 승인 항목 3 — `infer_phase()` 삭제와 구 PRP 개정 방식

`hub_model.infer_phase()` 를 **삭제**하고 테스트 M9·M10 을 A1·A4 로 대체하며,
`hub-dashboard.md` 에 **대체 표기 3곳**을 덧붙인다(내용 삭제 없음 — 직전 PRP 와 같은 이력
보존 방식). 이 방식으로 진행할지 확인이 필요하다.

### 승인 항목 4 — 실패 중인 T25-11 을 이 배치에서 고칠지

`tests/run.sh` T25-11 은 **현재 실패한다**(미커밋 템플릿 수정이 `short_id` 렌더를 없앴다).
요구 1 이 같은 함수(`renderSession`)를 재작성하므로 **이 배치에서 함께 고치는 것을 권고**한다
(그러지 않으면 `bash tests/run.sh` 가 이 변경과 무관한 이유로 계속 실패해 완료 판정이 불가능하다).
분리를 원하면 별도 커밋/티켓으로 뺄 수 있으나, 그 경우 이 PRP 의 성공 기준 S9 는
"T25-11 을 제외한 전체 통과"로 완화해야 한다.
