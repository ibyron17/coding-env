# PRP — 허브 카드 정리 + 사용량 퍼센트 출처 교체

> 설계 문서. **구현 코드는 이 문서에 없다.** 승인 후 `implementer` 가 이 문서를 입력으로 구현한다.
> 대상 브랜치: `feature/hub-dashboard` · 저장소 소스(`hub/bin/`)만 다룬다.
> 선행 정본: [`hub-dashboard.md`](./hub-dashboard.md) ·
> [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md) ·
> [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md) ·
> [`hub-session-activity-and-tooltip.md`](./hub-session-activity-and-tooltip.md) ·
> [`hub-usage-reset-time-and-refresh.md`](./hub-usage-reset-time-and-refresh.md)
>
> 이 PRP 는 위 문서들의 결정 **D4·D5(칩 상한·오버플로) · S7(퍼센트 미캡처) · U3(만료) ·
> R3(패널 게이팅) · G1~G5(그리드 열 수)** 를 개정한다. 원문은 지우지 않고 개정 표기만 덧붙인다
> (이 레포의 기존 이력 보존 방식).
>
> 결정 번호 namespace: **W**(그리드 폭) · **V**(세션 표시) · **K**(칩) · **Z**(stale 컷오프) ·
> **P**(퍼센트 출처). 신규 단위 테스트 케이스는 **N1~** 로 새로 매긴다(기존 case·R·A 번호와 충돌 없음).

---

## 1. 요구사항 요약

허브 대시보드(`/hub`)의 화면 밀도와 데이터 정확성을 정리한다. (1) 프로젝트 카드 그리드가
와이드 모니터에서 4열까지 벌어져 카드가 잘게 쪼개지므로 **최대 3열**로 제한한다.
(2) 상태 배지와 경과시간만 남은 **정보 없는 「완료」 세션 줄을 숨긴다**. (3) 종료된 서브에이전트
타입까지 `+N` 칩으로 접어 보여주는 현행 동작을 **단순화**한다. (4) `SessionEnd` 없이 죽어
「소식 없음」으로 며칠 남는 세션의 **표시 기한 컷오프** 도입 여부를 결정한다. (5) 가장 중요한
항목 — 사용량 패널이 **완전히 사라진 상태**를 복구한다. 퍼센트 출처였던 데스크톱 앱 파일
(`plan-usage-history.json`)이 실제로 없어졌으므로, 이미 리셋 시각의 출처로 쓰고 있는
**Claude Code CLI statusLine 입력의 `rate_limits.*.used_percentage`** 를 퍼센트 출처로 승격한다.

1~4는 표시층(HTML 템플릿)만 만지는 변경이고, 5는 파서·I/O·스냅샷·문서·배포 절차까지 걸친다.

---

## 2. 실측으로 확인된 사실 (재조사 대상 아님)

### 2.1 환경 (2026-08-12 이 머신에서 직접 확인)

| # | 사실 | 확인 방법 |
|---|------|----------|
| E1 | `~/Library/Application Support/Claude/plan-usage-history.json` **없음** | `ls` → `No such file or directory` |
| E2 | `~/.claude/settings.json` 에 `statusLine` **없음**(키 자체가 부재, 최상위 키 11개 중 없음) | `json.loads` 후 키 목록 확인 |
| E3 | `~/.claude/hub/rate_limits.json` **없음**(hub.html·server.json·server_heartbeat·server.log·events/ 만 존재) | `ls ~/.claude/hub/` |

→ E1 때문에 `_usage_for_snapshot` 이 항상 `None`(경고 없음, 결정 U3·U4 의 정상 경로)이고,
`renderUsagePanel` 이 패널을 숨긴다. E2 때문에 `hub_statusline.py` 가 아예 실행되지 않아
E3(캡처 부재)이 된다. **두 원인이 독립적으로 각각 패널을 죽인다** — 하나만 고치면 안 된다.

### 2.2 statusLine 입력 계약 (선행 PRP 가 CLI 바이너리에서 확인, 재조사 불필요)

```js
// statusLine 입력 페이로드 조립부 (~/.local/share/claude/versions/2.1.139 내 실제 코드)
{...Z.five_hour&&{five_hour:{used_percentage:Z.five_hour.utilization*100,resets_at:Z.five_hour.resets_at}},
 ...Z.seven_day&&{seven_day:{used_percentage:Z.seven_day.utilization*100,resets_at:Z.seven_day.resets_at}}}
```

| 사실 | 내용 | 이 PRP 에 미치는 영향 |
|------|------|----------------------|
| `used_percentage` | `utilization * 100` → **실수**(23.5 등), 0~100 스케일 | 내림 정수로 캡처한다(결정 P2). 스케일 변경 리스크는 §14 리스크 3 |
| `resets_at` | UNIX epoch **초** | 기존 처리 그대로(×1000) |
| `rate_limits` 키 | `five_hour`·`seven_day` 중 **하나라도** 있을 때만 존재 | 창별 독립 부재를 계속 허용한다 |
| 등장 시점 | Pro/Max 구독 세션의 **첫 API 응답 이후** | 세션을 한 번은 돌려야 캡처가 생긴다 |
| 실행 빈도 | 최대 **0.3초마다** | 쓰기 증폭 방지가 필수(결정 P4) |
| 비용 | `python3` 1회 기동 42.0ms(`hub_collect` 임포트 포함, 중앙값 n=10) | 이번 변경으로 늘지 않는다 |

### 2.3 코드 사실 (직접 읽고 확인)

| # | 사실 | 위치 |
|---|------|------|
| C1 | 그리드는 `repeat(auto-fill,minmax(320px,1fr))` + `gap:12px`, 컨테이너 폭은 `.wrap{max-width:1440px;padding:0 16px}` → 콘텐츠 폭 최대 1408px | `hub_template.html:59-60` |
| C2 | `renderProject` 는 `project.sessions.length` 로만 `<ul class="sessions">` 를 감싼다 | `hub_template.html:485-486` |
| C3 | `renderAgentRuns` 는 `MAX_VISIBLE_AGENT_CHIPS=2` 로 자르고 초과분을 `.agent-chip-more` `+N` 칩으로 접는다 | `hub_template.html:341, 438-449` |
| C4 | `summarize_agent_runs` 는 타입별로 합쳐 **최근 시작 내림차순**으로 전부 돌려준다(종료된 것 포함) | `hub_model.py:378-401` |
| C5 | `_project_state` 는 `session_views` 로 프로젝트 배지를 집계하고, 세션이 **비면** `_project_state_without_sessions`(idle/stale) 로 갈라진다 | `hub_model.py:445-463` |
| C6 | `_project_tier` 는 `session_views` 가 아니라 `SessionFacts` 로 티어를 정한다 | `hub_model.py:439-442` |
| C7 | `read_recent_events` 는 **오늘 + 어제** 이벤트 파일만 읽는다 | `hub_collect.py:164-193` |
| C8 | `build_session_facts` 는 dict 삽입 순서(= 첫 이벤트 순서)를 유지하고 `compose_project_views` 가 그대로 싣는다 → **세션 목록은 오래된 것부터** | `hub_model.py:328-348, 489-491` |
| C9 | `_valid_used_percentage` 는 이미 실수/정수를 받아 `math.floor` 한다(bool 배제, 0~100) | `hub_usage.py:209-222` |
| C10 | `collect_snapshot` 은 `_usage_for_snapshot` 과 `_rate_limit_resets_for_snapshot` 을 **각각** 부른다(캡처 단일 출처가 되면 파일을 두 번 읽고 경고가 중복된다 — GOTCHA 5) | `hub_collect.py:407-410` |
| C11 | `escapeHtml` 은 `& < > " '` 를 모두 이스케이프한다. 모든 툴팁은 `data-tooltip`(T25-44 가 `title="` 0건 강제) | `hub_template.html:501-504` |
| C12 | 배포 파일 수 `HUB_FILE_COUNT=11`, 실제 `hub/bin` 파일 11개 | `hub/install.sh:12` |

### 2.4 과제 설명의 전제 2건 정정 (설계 판단에 직접 영향)

1. **stale 세션은 7일이 아니라 최대 약 24~48시간 남는다.** `event_retention_days=7` 은
   *파일 삭제* 기한이고, 표시에 쓰이는 창은 C7(오늘 + 어제 파일)이다. 마지막 이벤트가 어제보다
   오래된 세션은 스냅샷에 아예 없다. → 항목 4 의 컷오프가 막아 주는 최대 잔존은 약 하루 반이다.
2. **세션 줄은 오래된 것부터 그려진다**(C8). 즉 죽은 세션이 **살아 있는 세션 위**에 놓이고,
   `.sessions{overflow-y:auto}` 안에서 현재 작업이 스크롤 아래로 밀린다. 항목 4 가 지적하는
   불편의 절반은 잔존이 아니라 **이 순서** 때문이다(§5.4 안 2).

---

## 3. 확정된 전제 (재론하지 않는다)

1. **단일 정적 HTML, 빌드 단계 없음.** 프레임워크·CDN·JS 테스트 러너를 도입하지 않는다.
2. **`#dzh-data` JSON 계약 불가침.** `render_hub_html` 이 치환하는 마커 형태와
   `HubSnapshot` 의 최상위 필드 이름(`usage`·`rate_limit_resets` 포함)은 그대로 둔다.
3. **불변식 H1′ 불변.** 폴링이 내용을 갱신하는 요소는 `#dzh-app`·`#dzh-collected-at`·
   `#dzh-usage-body`·`#dzh-usage-summary` 네 개뿐이다. 이 PRP 는 새 갱신 대상을 만들지 않는다.
4. **모든 툴팁은 `data-tooltip`.** 네이티브 `title` 을 되살리지 않는다(T25-44).
5. **새 외부 의존성 0, 새 배포 파일 0.** `HUB_FILE_COUNT` 는 11 그대로다.
6. **새 `config.json` 필드를 만들지 않는다.** 표시 스위치는 `show_usage_panel` 하나,
   캡처 on/off 는 `/hub statusline on|off` 가 담당한다(선행 PRP 결정 R3-b·기각 대안 9).
7. **새 색 리터럴을 도입하지 않는다**(T25-29 통과 유지).
8. **`show_usage_panel:false` 는 "읽지 않는다"** — 캡처 파일도 열지 않는다.

---

## 4. 영향 범위

### 4.1 수정 파일

| # | 파일 | 변경 요지 | 항목 |
|---|------|----------|------|
| 1 | `hub/bin/hub_template.html` | CSS 그리드 1줄 · 상수 2~3개 · JS 함수 3개 추가/수정(`visibleAgentRuns`·`shouldRenderSession`·`renderProject` 필터) · `renderAgentRuns` 축소 · `USAGE_CYCLE_NOTE` 문구 · `.agent-chip-more` CSS 제거 · 상단 주석 1줄 | 1·2·3·4·5 |
| 2 | `hub/bin/hub_usage.py` | dataclass 1개 추가 · 순수 함수 4개 추가 · 3개 시그니처/의미 변경 · 1개 삭제(`parse_usage_history`) · 모듈 docstring | 5 |
| 3 | `hub/bin/hub_collect.py` | `PLAN_USAGE_HISTORY_PATH`·`read_latest_usage_sample` 삭제 · `_usage_for_snapshot`·`_rate_limit_resets_for_snapshot` 을 `_capture_for_snapshot` 하나로 통합 · `collect_snapshot` 배선 3줄 | 5 |
| 4 | `hub/bin/hub_statusline.py` | 파싱 1회로 통합(출력도 캡처에서 만든다) · 비교 함수 교체 1줄 · docstring | 5 |
| 5 | `hub/bin/hub.py` | `_usage_sample_age_ms` 재정의(캡처 기반) · `_rate_limit_resets_remaining_ms` 에 투영 1줄 | 5 |
| 6 | `hub/bin/hub_model.py` | `HubSnapshot.usage` 주석 1줄(출처 변경 표기)뿐 — **필드·시그니처 변경 없음** | 5 |
| 7 | `hub/README.md` | 「화면 배치」 3행 · 「사용량 패널」 절 전면 개정 · 「한도 초기화 예정 시각」 절 2행 · 「프라이버시 고지」 1행 · 설정표 1행 | 1~5 |
| 8 | `commands/hub.md` | `/hub status` 의 `usage_sample_age_ms` 설명 개정 · `/hub statusline on` 고지 문구에 "패널의 퍼센트도 이 등록이 있어야 뜬다" 추가 | 5 |
| 9 | `tests/run.sh` | T25-31·32·41·43 개정, T25-50~56 신규, 헤더 범위 문구 2곳(`T25-1~T25-49` → `T25-1~T25-56`) | 1~5 |
| 10 | `tests/hub/test_hub_usage.py` | `ParseUsageHistoryTest` 삭제 · `SameResetTimesTest` 개정 · 신규 클래스 3개 | 5 |
| 11 | `tests/hub/test_hub_collect.py` | `UsageForSnapshotTest`·`CollectSnapshotUsageIsolationTest` 를 캡처 기반으로 재작성 | 5 |
| 12 | `tests/hub/test_hub_statusline.py` | 픽스처에 `used_percentage` 추가 · 퍼센트 변화 시 재기록 케이스 1건 | 5 |
| 13 | `docs/prps/hub-*.md` 4개 | 개정 표기만 덧붙임(§9) | — |

### 4.2 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_parse.py` | 티어 1(`/dashboard` DOM) 파서. 접점 없음 |
| `hub/bin/hub_server.py`·`hub_daemon.py`·`hub_hook.py` | 수집 루프는 `collect_snapshot()` 만 부른다. statusLine 은 훅이 아니다 |
| `hub/bin/hub_settings.py` | statusLine 등록 로직은 그대로 옳다. 이번 변경은 "그것을 켜라"는 배포 절차 문제다 |
| `hub/install.sh` | 배포 파일 수 불변(11) |
| `.claude/dashboard.html` | **접근 금지**(과제 지시). 티어 1 계약은 `commands/dashboard.md` 문서로만 참조한다 |
| `HubConfig` 스키마 | 전제 6 |
| 루트 `install.sh`·`README.md`·`commands/dashboard.md` | 허브와 분리된 자산(T25-21·T25-22 가 분리를 강제) |

---

## 5. 항목별 설계

### 5.1 항목 1 — `#dzh-app` 최대 3열 (결정 W1·W2)

#### 현행 계산

콘텐츠 폭 `W` = `min(1440, viewport) - 32`. 열 수 `n = floor((W + 12) / (320 + 12))`.
`W=1408` 이면 `floor(1420/332) = 4` → **와이드 모니터에서 4열**.
README 가 고지한 임계값(≤683px 1열 / 684~1015px 2열 / 1016~1347px 3열 / ≥1348px 4열)과 일치한다.

#### 결정 W1 — 트랙 최소폭을 "3열일 때의 폭"으로 올린다 (미디어 쿼리 없이)

```css
/* 최대 3열 — 트랙 최소폭을 (콘텐츠폭 − gap 2개)/3 로 올리면 4열이 산술적으로 불가능해진다.
   24px 은 같은 줄의 gap:12px 2개다(3열의 gap 개수) — gap 을 고치면 이 값도 같이 고쳐야 한다.
   -1px 은 서브픽셀 반올림이 비율을 3 아래로 떨어뜨려 2열로 붕괴하는 것을 막는 여유다(GOTCHA 1).
   max(320px, …) 가 좁은 폭에서는 종전 320px 을 그대로 쓰게 해 2·1열 반응형을 보존한다. */
#dzh-app{display:grid;grid-template-columns:repeat(auto-fill,minmax(max(320px,calc((100% - 24px)/3 - 1px)),1fr));gap:12px;align-items:start}
```

**왜 정확히 3열인가(증명)**: `W ≥ 984` 이면 `max()` 가 `(W-24)/3 - 1` 을 고르고,
`n = floor((W+12) / ((W+12)/3 - 1))`. 분모가 `(W+12)/3` 보다 작으므로 비율은 항상 3 초과이고,
4 가 되려면 `(W+12)/3 - 1 ≤ (W+12)/4` → `W ≤ 0` 이어야 한다 → **모든 실제 폭에서 정확히 3열.**
`W < 984` 이면 `max()` 가 320px 을 고르므로 **현행과 완전히 동일**하다(1열/2열 임계값 불변).

| viewport | 콘텐츠 폭 W | 트랙 최소폭 | 열 수 |
|---------|------------|-----------|------|
| 420px | 388 | 320 | 1 |
| 700px | 668 | 320 | 2 |
| 1016px | 984 | 320 | 3 |
| 1200px | 1168 | 380.3 | 3 |
| 1440px 이상 | 1408 | 460.3 | 3 |

#### 결정 W2 — `.card{height:340px}` 과 `.wrap{max-width:1440px}` 은 건드리지 않는다

카드가 3열에서 최대 460px 로 **넓어진다**(현행 4열의 340px 대비). 카드 높이 340px 은 "헤더 +
세션 3개"를 근거로 고정된 값이라(템플릿 65~67행 주석) 폭 변화와 독립이다. `max-width` 를 줄여
3열을 만드는 대안은 §15 대안 1 에서 기각한다.

#### 검증 방법 (수동 M1)

1. 브라우저 개발자도구 반응형 모드로 폭 **420 / 700 / 1016 / 1200 / 1440 / 1920** 을 순회한다.
2. 각 폭에서 콘솔 1줄로 열 수를 기계적으로 확인한다:
   `getComputedStyle(document.getElementById('dzh-app')).gridTemplateColumns.split(' ').length`
   → 기대값 `1, 2, 3, 3, 3, 3`.
3. 1920px 에서 카드가 잘리거나 가로 스크롤이 생기지 않는지 확인한다.

---

### 5.2 항목 2 — 정보 없는 「완료」 세션 줄 숨김 (결정 V1~V3)

#### 결정 V1 — 필터는 **클라이언트**(표시층)에 둔다

서버(`hub_model`)에서 세션을 제거하면 C5 에 의해 프로젝트 배지가 바뀐다. 실측 시나리오:
"완료 세션 1개만 있는 프로젝트"에서 세션을 제거하면 `_project_state` 가
`_project_state_without_sessions` 로 갈라져 마지막 활동이 30분 넘었으면 **`done`(중립 윤곽선)
대신 `stale`(주의색 점선)** 이 된다. 끝난 프로젝트가 경고색으로 바뀌는 것은 개선이 아니라 회귀다.
또한 선행 결정 D5("서버는 사실을 다 준다, 화면은 공간에 맞춰 고른다")와 정합한다.

#### 결정 V2 — 숨김 조건은 "**완료** + **표시할 내용 없음**"

```
숨긴다 ⟺ state === 'done' && !task_excerpt && 표시할 칩이 0개
```

- `state`(stale 오버레이가 적용된 값)가 아니라 `base_state` 를 쓰면 stale 이 된 done 세션…은
  존재하지 않는다(`_compute_base_state` 가 done 이면 stale 오버레이를 걸지 않는다, `hub_model.py:364`).
  두 값이 done 에서 항상 같으므로 **`state === 'done'` 을 쓴다**(템플릿이 이미 쓰는 필드).
- "표시할 칩이 0개"는 `agent_runs` 의 길이가 아니라 **항목 3 의 필터를 통과한 칩 수**로 판정한다.
  판정 함수를 렌더 함수와 공유해(`visibleAgentRuns`) "칩이 없는데 줄이 남는" 어긋남을 원천 차단한다.
- `idle`·`working`·`stale` 은 건드리지 않는다(항목 4 가 stale 만 별도로 다룬다).

#### 결정 V3 — 전부 걸러지면 `<ul class="sessions">` 자체를 그리지 않는다

`renderProject` 의 `project.sessions.length` 판정을 **필터 후 배열 길이**로 바꾼다(C2).
빈 `<ul>` 은 `.sessions{border-top}` 이 없어 시각적으로는 무해하지만, 접근성 트리에 빈 목록을
남기지 않는 편이 정확하다.

**받아들이는 대가**: 카드 높이는 340px 고정이므로(W2) 세션이 줄어도 카드가 작아지지 않고
여백이 남는다. 티어 배지가 `세션 활동`(티어 2, C6 은 `SessionFacts` 로 판정하므로 불변)인데
세션 줄이 하나도 없는 카드가 생길 수 있다 — README 에 한 줄로 명시한다.

**상호작용 주의**: `record_prompt_excerpt:false` 인 사용자는 모든 세션에 `task_excerpt` 가
없으므로, 항목 3 에서 **안 B(실행 중만)** 를 고르면 **모든 완료 세션이 사라진다**. 안 A 를
고르면 칩이 남아 계속 보인다. 이 조합은 §16 승인 항목 2 에 명시한다.

---

### 5.3 항목 3 — agent-runs 칩 단순화 (결정 K1~K3)

#### 현행

`summarize_agent_runs`(서버)가 이벤트 창(오늘+어제, C7) 안의 **모든** 서브에이전트 타입을
타입별로 합쳐 최근 시작순으로 준다 → 클라이언트가 2개만 그리고 나머지를 `+N` 칩으로 접는다
(결정 D4·D5). 실행 중 타입만 `●` 글리프 + `.agent-chip-running` 강조.

#### 요구의 두 가지 해석 (추측하지 않고 둘 다 제시한다 — 승인 항목 2)

과제 문장 "종료된 타입까지 `+N` 으로 접어 보여줄 필요 없다" 는 두 갈래로 읽힌다.

| 안 | 동작 | 서버 | 클라이언트 | 상실 |
|----|------|------|-----------|------|
| **A (권고)** | 칩 2개 유지, **`+N` 칩만 제거** | `summarize_agent_runs` 정렬을 "실행 중 먼저 → 최근 시작순"으로 변경 | `runs.slice(0,2)` 만 남기고 오버플로 블록 삭제 | 3번째 이후 **종료된** 타입이 조용히 사라진다(툴팁으로도 못 본다) |
| **B** | **실행 중 타입만** 칩으로 표시, 상한·오버플로 개념 자체 제거 | 변경 없음(사실 그대로 준다) | `runs.filter(r => r.is_running)` | 완료·대기 세션의 칩이 전부 사라진다 → 항목 2 와 결합해 세션 줄 자체가 사라질 수 있다 |
| C | 상한 제거, 전부 줄바꿈 | 변경 없음 | 상한 삭제 | 없음. 대신 `Explore` 등이 섞이면 세션 1개가 카드 절반을 먹는다(D4 가 이미 기각한 형태) |

**권고는 A.** 근거:

1. **B 는 직전 사용자 요구의 반전이다.** `agent_runs` 는 "완료 세션이 무엇을 했는지 남아야
   한다"는 요구로 `active_agent_types`(실행 중만)를 **대체**하며 만들어졌고(결정 D1),
   `tests/run.sh` **T25-43** 이 그 회귀를 명시적으로 막고 있다("`active_agent_types` 가
   부활함 — 완료 세션이 다시 빈 목록이 된다"). B 를 고르면 그 테스트의 의도 자체를 개정해야 한다.
2. **요구의 문자적 대상은 `+N` 칩**이다. A 는 그 하나만 제거하고 나머지는 손대지 않는다(수술적).
3. **A 의 상실은 정렬 변경으로 대부분 메워진다.** 지금은 최근 시작순이라 실행 중 타입이 3번째로
   밀려 `+N` 안에 숨을 수 있다. "실행 중 먼저"로 바꾸면 **진행 중인 것은 항상 보인다** — 칩 줄의
   목적(지금 무엇이 돌고 있나)이 상한과 무관하게 달성된다.

#### 결정 K1 — 상한 자르기는 클라이언트, 정렬은 서버 (D5 유지)

`MAX_VISIBLE_AGENT_CHIPS`(=2)는 남긴다. `visibleAgentRuns(runs)` 순수 함수 하나가 "보이는 칩"의
유일한 판정자가 되고, `renderAgentRuns` 와 항목 2 의 `shouldRenderSession` 이 그것을 공유한다.

#### 결정 K2 — `summarize_agent_runs` 정렬을 "실행 중 먼저 → 최근 시작순 → 타입명" 으로 (안 A 채택 시)

정렬 키를 `(0 if is_running else 1, -latest_started_at_ms, agent_type)` 로 바꾼다.
전부 결정적이므로 `snapshot_content_key` 안정성은 유지된다(D2 의 타이브레이크 근거 보존).

#### 결정 K3 — `.agent-chip-more` CSS 규칙은 **삭제**한다

`+N` 칩을 없애면 이 규칙은 우리 변경이 만든 고아다(전역 지침: 내 변경이 만든 고아는 제거).
`.agent-chip`·`.agent-chip-running`·`.glyph`·`.sr-only` 는 그대로 쓴다.
안 B 를 고르면 `MAX_VISIBLE_AGENT_CHIPS` 상수도 함께 고아가 되므로 삭제하고 T25-43 의 토큰
목록에서 뺀다.

---

### 5.4 항목 4 — stale 세션 표시 기한 (선택 결정, 결정 Z1)

#### 사실 확인 후의 실제 문제 크기

§2.4-1 에 따라 잔존 상한은 7일이 아니라 **약 24~48시간**이다. 그리고 §2.4-2 에 따라 죽은 세션이
**살아 있는 세션 위에** 놓인다. 사용자가 체감한 불편은 이 둘의 합이다.

| 안 | 내용 | 새 상수 | 정보 손실 | 순서 문제 해결 |
|----|------|--------|----------|--------------|
| **1 (권고)** | 클라이언트 컷오프 — `state==='stale' && (now - last_event_at_ms) >= 12시간` 이면 숨김 | 1개 | 반나절 넘게 죽은 세션 | ✕ |
| 2 | 컷오프 없이 **세션 정렬을 최신순으로**(클라이언트 `slice().sort()`) | 0개 | 없음 | ○ |
| 3 | 도입하지 않음(현행 유지) | 0개 | 없음 | ✕ |

**권고: 안 1 을 채택하고, 안 2 를 함께 채택할지는 사용자가 고른다**(§16 승인 항목 3).
두 안은 배타적이지 않다 — 안 1 은 "이어서 할 수 없는 세션을 치운다", 안 2 는 "지금 중요한 것을
위로 올린다"로 서로 다른 문제를 푼다. 안 2 만으로도 체감 개선이 크므로 컷오프를 원치 않으면
안 2 단독도 유효하다.

#### 결정 Z1 — 12시간의 근거 (그리고 그것이 임의값이라는 정직한 고백)

- 컷오프는 `stale_after_minutes`(30분)와 이벤트 표시 창(≈24~48시간) **사이**의 어떤 값이어야
  의미가 있다. 12시간은 그 구간을 반으로 가르며, "출근해서 어제 죽은 세션을 보지 않는다 /
  점심 전에 멈춘 세션은 오후에도 보인다"는 하루 작업 흐름의 경계와 맞는다.
- **더 나은 앵커가 없음을 인정한다.** 리셋 창(5시간)·보관 기한(7일)은 이 판정과 무관하다.
  그래서 `config.json` 필드로 만들지 않고(전제 6) **템플릿 상수 1개**로 둔다 — 되돌리기가
  1줄이고, 값 변경도 1줄이다.
- 서버가 아니라 클라이언트에 둔다(V1 과 같은 근거: 프로젝트 배지를 바꾸지 않는다).
- **프로젝트 배지는 영향받지 않는다** — 숨겨도 스냅샷의 `state` 집계는 그대로다. 즉 세션 줄이
  없는데 프로젝트 배지가 `소식 없음` 인 카드가 나올 수 있다(V3 의 대가와 같은 성격).

---

### 5.5 항목 5 — 사용량 패널 복구: 퍼센트 출처 교체 (결정 P1~P8)

#### 결정 P1 — 퍼센트 출처를 **캡처 파일 단일 출처**로 교체한다 (승인 항목 1)

| 안 | 내용 | 판단 |
|----|------|------|
| **A (권고)** | 캡처(`rate_limits.json`) **단일 출처**. 데스크톱 파일 읽기 코드(`PLAN_USAGE_HISTORY_PATH`·`read_latest_usage_sample`·`parse_usage_history`)를 삭제 | 출처가 하나면 신선도 규칙·경고·진단 필드도 하나다. E1 로 이미 죽은 경로를 유지할 근거가 없다 |
| B | 캡처 **우선** + 데스크톱 **폴백** | 두 신선도 의미(앱 15분 샘플링 vs CLI 실시간)가 한 패널에 섞이고, 실측 불가능한 경로가 남아 썩는다. 선행 PRP 리스크 5("두 출처의 불일치")를 영구화한다 |
| C | 데스크톱 우선 + 캡처 폴백(현행 우선순위 유지) | E1 환경에서 항상 2순위로 떨어지는데 1순위 코드를 유지하는 형태. 가장 근거가 약하다 |

A 의 대가는 정직하게 둘이다. (1) **`/hub statusline on` 이 사실상 필수가 된다** — 옵트인
설계는 유지하되, 켜지 않으면 패널이 없다(README·`/hub status`·커맨드 고지에 명시).
(2) `parse_usage_history` 와 그 단위 테스트 17건이 삭제된다 — 이 코드는 무관한 죽은 코드가
아니라 **이번 요구가 대체하는 대상**이라 삭제가 맞다(수술적 변경 원칙에 저촉되지 않는다).
데스크톱 파일이 부활하면 되돌리기는 국소적이다(§15 대안 4).

> **보강.** P1(퍼센트의 유일한 출처 = statusLine 캡처)은 **소비 계약**으로는 유효하다.
> 생산자는 [hub-card-interactions-and-usage.md](./hub-card-interactions-and-usage.md) 의
> 결정 A2 로 하나 더 늘어난다(파일 포맷·타입은 불변).

#### 결정 P2 — 캡처 파일 스키마를 **하위 호환**으로 확장한다

```jsonc
// ~/.claude/hub/rate_limits.json  (신형)
{
  "captured_at_ms": 1786433123899,
  "session_resets_at_ms": 1786440000000,   // 없을 수 있다(창 부재)
  "weekly_resets_at_ms": 1786900000000,    // 없을 수 있다
  "session_used_percent": 23,              // 신규. 내림 정수 0~100. 없을 수 있다
  "weekly_used_percent": 41                // 신규. 없을 수 있다
}
```

- **읽기 하위 호환**: 구형 캡처(퍼센트 키 없음)는 두 필드가 `None` 인 정상 캡처로 파싱된다 →
  리셋 줄은 계속 뜨고 퍼센트만 없다(= 패널 없음). 마이그레이션 코드 0줄.
- **쓰기 상위 호환**: 신형 파일을 구형 코드가 읽어도 `.get()` 기반이라 여분 키를 무시한다
  (허브를 되돌려도 깨지지 않는다).
- **유효성 판정 변경**: 지금은 "리셋 시각 둘 다 없으면 `None`". 새 규칙은
  **"네 값이 전부 없으면 `None`"** — 퍼센트만 있는 페이로드도 캡처할 값이 있다(이제 퍼센트가
  패널의 본체다).
- 퍼센트 필드 검증은 파일 읽기 경로에서 `_is_valid_percent`(엄격 int, bool 배제, 0~100)를
  재사용하고, **필드 단위로** 버린다(`_valid_resets_at_ms` 가 창 단위로 버리는 선례와 동일).

#### 결정 P3 — 스냅샷 계약은 그대로. 캡처를 **두 갈래로 투영**한다

```
statusLine stdin ─parse─▶ RateLimitCapture ─┬─ usage_sample_from_capture ─▶ UsageSample      → snapshot.usage
캡처 파일 ───────parse─▶ (같은 타입)        └─ resets_from_capture ──────▶ RateLimitResets  → snapshot.rate_limit_resets
```

`HubSnapshot` 의 필드 이름·형태는 **바뀌지 않는다**(전제 2). 캡처 dataclass 를 스냅샷에 그대로
싣는 대안은 같은 퍼센트가 `usage` 와 `rate_limit_resets` 양쪽에 중복 직렬화되어(#dzh-data 안에
같은 숫자가 두 벌) 클라이언트가 어느 쪽을 읽어야 하는지 모호해지므로 기각한다.

#### 결정 P4 — 쓰기 증폭 방지: 비교를 **네 값 전부**로 확장한다

`same_reset_times(previous, current)` → **`same_capture_values(previous, current)`**:
`captured_at_ms` 를 제외한 **리셋 2개 + 퍼센트 2개**가 모두 같으면 다시 쓰지 않는다.
이름을 바꾸는 이유는 함수가 더 이상 "reset times" 만 비교하지 않기 때문이다(이름이 거짓이 되면
다음 사람이 퍼센트 비교를 빼먹는다).

**쓰기 빈도 정량**(0.3초 주기 = 시간당 최대 12,000회 호출 기준):

| 상황 | 쓰기 횟수 |
|------|----------|
| `rate_limits` 없는 세션(API 키·무료) | **0회** (파일을 열지도 않는다 — 현행 그대로) |
| 값 변화 없음 | **0회** (P4) |
| 5시간 창을 0%→100% 로 소진 | 정수 경계 **최대 100회 / 5시간** ≈ 3분당 1회 |
| 주간 창 | 최대 100회 / 7일 |

→ 최악의 쓰기 비율은 호출 대비 **0.4% 미만**(54,000회 호출 중 200회). 원자적 쓰기 1회는
100바이트 임시 파일 + `rename` 이다.

#### 결정 P5 — 신선도 규칙: **5시간 만료(U3 유지) + 세션 창 롤오버 검사(신설)**

| 조건 | 판정 | 근거 |
|------|------|------|
| 캡처 나이 ≥ 5시간 | 퍼센트 미표시 | U3 그대로. `five_hour` 창 길이가 곧 근거의 유효기간이다 |
| `session_resets_at_ms` 가 알려져 있고 **이미 지났다** | 퍼센트 미표시 | 창이 리셋됐으므로 캡처된 세션 퍼센트는 **확실히 틀렸다**(나이가 3시간이어도). 실측 가능한 흔한 경로: 10:00 캡처 · 12:00 리셋 · 13:00 조회 |
| 둘 다 아님 | 표시 | — |

두 번째 규칙은 새 상수를 만들지 않고(이미 캡처에 있는 절대 시각을 쓴다) "틀린 숫자보다 없는
숫자가 낫다"(U1·U2 의 정신)를 지킨다. 순수 함수 `is_session_window_rolled_over(capture, now_ms)`
로 분리해 단위 테스트한다. **이 규칙만 빼고 싶으면** `_capture_for_snapshot` 의 조건 1줄과
테스트 3건을 지우면 된다(국소적).

**받아들이는 대가**: 세션 창이 리셋된 뒤 새 세션을 돌리기 전까지 패널이 사라진다. 이는
"퍼센트가 없으면 패널 없음"(R3) 게이팅의 정직한 귀결이다. 주간 퍼센트만 남기는 부분 패널은
템플릿이 막대 2개를 모두 요구하므로(`renderUsagePanel` 의 `if(!sessionBar || !weeklyBar)`)
새 표시 상태 3개를 만들어야 한다 → 기각(§15 대안 6).

#### 결정 P6 — `UsageSample.sampled_at_ms` = **캡처 시각**, 주기 문구를 교체한다

| 항목 | 현행 | 개정 |
|------|------|------|
| `sampled_at_ms` 의미 | 데스크톱 앱의 샘플 시각 `t` | statusLine 이 그 값을 **관측한 시각**(`captured_at_ms`) |
| `USAGE_CYCLE_NOTE` | `'· 약 15분 주기'`(앱 샘플링 주기) | **`'· 세션 진행 중에만 갱신'`** |
| 메타 줄 예시 | `마지막 갱신 12분 전 · 약 15분 주기` | `마지막 갱신 방금 · 세션 진행 중에만 갱신` |

"약 15분 주기"는 데스크톱 앱 전제 문구다. 새 출처는 **세션이 돌 때 실시간, 안 돌면 정지**라
주기 개념이 없다 — 그 사실을 그대로 쓴다. `T25-41` 이 이 문구를 grep 으로 고정하고 있으므로
테스트도 함께 개정한다(§11.3).

부수 효과: `usage-meta` 툴팁(절대 시각)과 `usage-reset` 툴팁("이 정보를 확인한 시각")이 같은
타임스탬프를 보여준다. 중복이지만 각 줄의 문맥에서 각각 옳으므로 그대로 둔다(수술적).

#### 결정 P7 — `format_status_line_summary` 를 캡처에서 만든다 (파싱 1회로 통합)

현재 `hub_statusline._run` 은 같은 stdin 을 **두 번** `json.loads` 한다(출력용 1회, 캡처용 1회)
— 그리고 퍼센트 추출 규칙이 출력 경로와 캡처 경로에 각각 존재하게 되면 두 숫자가 어긋날 수
있다. 시그니처를 `format_status_line_summary(capture: RateLimitCapture | None) -> str` 로 바꿔
**퍼센트 추출의 정본을 파서 하나로** 만든다. 상태줄과 패널이 항상 같은 숫자를 보이는 것은
이 통합의 직접 산물이다.

실행 순서는 계약을 유지한다: `stdin 읽기 → 파싱(순수, 예외를 던지지 않는다) → print → 파일 I/O`.
파싱은 파일에 닿지 않으므로 "출력 먼저, I/O 나중"(리스크 2 완화책)은 그대로다.

#### 결정 P8 — `content_key` 재작성 폭주 영향 (결정 D3 정합 검증)

퍼센트가 `snapshot.usage` 에 실리면 `snapshot_content_key` 가 퍼센트 변화마다 바뀌어
`hub.html` 이 재작성되고, 폴링 클라이언트가 재렌더한다. 정량:

| 축 | 값 |
|----|-----|
| 퍼센트가 바뀌는 최대 빈도 | 내림 정수라 5시간 창 기준 **≤100회/5시간**(≈3분당 1회) |
| 같은 기간 이벤트 기반 변화 | 세션 1턴마다 `last_event_at_ms` 가 바뀐다(UserPromptSubmit·Stop·Subagent* ≥2건/턴) → 활성 작업 중 **분당 수 회** |
| 유휴 시 | 세션이 없으면 statusLine 이 돌지 않아 캡처가 안 바뀐다 → **추가 재작성 0회** |

→ 퍼센트 기여분은 기존 이벤트 churn 의 **작은 분수**이고, 유휴 상태의 정적 성질(D3 이 지키려던
것)은 보존된다. **D3 위반이 아니다.** 선행 PRP 가 기각 대안 6("퍼센트도 캡처")에서 우려한 것은
**실수 그대로** 캡처하는 경우였고, 내림 정수는 그 우려를 해소한다.

#### `_capture_for_snapshot` — 캡처 파일을 **사이클당 1회만** 읽는다

C10 때문에 지금 구조를 그대로 두면 캡처 파일을 2회 읽고, 계약 불일치 경고가 `warnings` 에
**2건 중복**되어 화면에 두 줄로 뜬다. 사설 함수 2개를 하나로 합친다.

```
_capture_for_snapshot(now_ms, config) -> (UsageSample | None, RateLimitResets | None, warnings)
  1. show_usage_panel 이 false 면 (None, None, ()) — 파일을 열지 않는다(전제 8)
  2. read_rate_limit_capture() 1회
  3. usage  = usage_sample_from_capture(capture) → 만료/롤오버(P5) 적용
  4. resets = resets_from_capture(capture) → drop_passed_resets(now_ms) 적용(R5 서버 필터 유지)
```

#### 표시 규칙 (개정 후)

| 상태 | 패널 | 리셋 줄 | 경고 | 진단 |
|------|------|--------|------|------|
| `show_usage_panel:false` | 없음 | 없음 | 없음 | `usage_panel_enabled:false` |
| 캡처 파일 없음(statusLine 미설치 또는 세션 미실행) | 없음 | 없음 | **없음**(정상 경로) | `statusline_installed`·`rate_limit_capture_age_ms:null` |
| 캡처 계약 불일치 | 없음 | 없음 | 1건 | 동일 |
| 캡처에 퍼센트 없음(구형 캡처·`rate_limits` 에 `used_percentage` 부재) | 없음 | 없음(패널 자체가 없다) | 없음 | `rate_limit_capture_age_ms` 는 숫자, `usage_sample_age_ms:null` ← **이 조합이 원인 지목의 핵심** |
| 퍼센트 한쪽만 있음 | 없음 | 없음 | 없음 | 위와 같다 |
| 캡처 나이 ≥5시간 또는 세션 창 롤오버 | 없음 | 없음 | 없음 | `usage_sample_age_ms` 가 숫자(만료는 값으로 판단) |
| 정상 | 막대 2개 | 아직 안 지난 창만 | 없음 | 전부 숫자 |

---

## 6. 데이터 모델

### 6.1 신규 — `hub_usage.RateLimitCapture`

```python
@dataclass(frozen=True)
class RateLimitCapture:
    """statusLine 이 관측한 한도 스냅샷 1건 — 창별 초기화 예정 시각 + 내림 정수 사용률.

    파일(`~/.claude/hub/rate_limits.json`)과 statusLine stdin 양쪽의 파싱 결과 타입이다.
    화면용 두 타입(UsageSample·RateLimitResets)은 이것의 투영이다(결정 P3).
    """

    captured_at_ms: int                  # 이 값들을 '처음 관측한' 시각(결정 S3 — 마지막 관측이 아니다)
    session_resets_at_ms: int | None      # rate_limits.five_hour.resets_at (초 → ms)
    weekly_resets_at_ms: int | None       # rate_limits.seven_day.resets_at (초 → ms)
    session_used_percent: int | None       # rate_limits.five_hour.used_percentage 를 내림한 정수
    weekly_used_percent: int | None        # rate_limits.seven_day.used_percentage 를 내림한 정수
```

### 6.2 유지 (형태 변경 없음)

| 타입 | 상태 | 비고 |
|------|------|------|
| `UsageSample(sampled_at_ms, session_percent, weekly_percent)` | **그대로** | `sampled_at_ms` 의 의미만 개정(P6). 스냅샷·템플릿 계약 불변 |
| `RateLimitResets(captured_at_ms, session_resets_at_ms, weekly_resets_at_ms)` | **그대로** | 스냅샷·템플릿 계약 불변 |
| `HubSnapshot` | **그대로** | `usage`·`rate_limit_resets` 필드 이름·순서·기본값 전부 유지 |
| `SubagentRunView(agent_type, phase, is_running)` | **그대로** | 항목 3 은 정렬만 바꾼다(안 A) 또는 아무것도 안 바꾼다(안 B) |
| `HubConfig` | **그대로** | 전제 6 |

### 6.3 삭제

`hub_collect.PLAN_USAGE_HISTORY_PATH`(상수) — 데스크톱 파일 경로. 승인 항목 1 에서 A 를
고른 경우에만.

---

## 7. 인터페이스 (공개 함수 시그니처)

### 7.1 `hub/bin/hub_usage.py` (★순수 — 파일시스템·시각·환경변수에 닿지 않는다)

| 구분 | 시그니처 | 계약 |
|------|----------|------|
| 신규 | `parse_status_line_rate_limits(text: str, captured_at_ms: int) -> RateLimitCapture \| None` | **반환 타입만 변경**. 네 값이 전부 없으면 `None`. 창별·필드별 독립 탈락 |
| 변경 | `parse_rate_limit_capture(text: str) -> RateLimitCapture \| None` | 구형 파일(퍼센트 키 없음) 수용. 네 값 전부 없으면 `None`. 예외를 던지지 않는다 |
| 신규 | `usage_sample_from_capture(capture: RateLimitCapture) -> UsageSample \| None` | 퍼센트 **둘 다** 있을 때만 `UsageSample`(`sampled_at_ms = captured_at_ms`). 하나라도 없으면 `None` |
| 신규 | `resets_from_capture(capture: RateLimitCapture) -> RateLimitResets \| None` | 리셋 둘 다 없으면 `None` |
| 신규 | `is_session_window_rolled_over(capture: RateLimitCapture, now_ms: int) -> bool` | `session_resets_at_ms` 가 있고 `<= now_ms` 면 `True`. 없으면 `False`(모르면 참으로 취급하지 않는다) |
| 개명 | `same_capture_values(previous: RateLimitCapture \| None, current: RateLimitCapture) -> bool` | `captured_at_ms` 를 뺀 **네 값**이 모두 같은가. `previous is None` → `False`. (구 `same_reset_times`) |
| 변경 | `format_status_line_summary(capture: RateLimitCapture \| None) -> str` | 인자가 **텍스트에서 캡처로**. 쓸 값이 없으면 `''` |
| 유지 | `is_usage_sample_expired(sample: UsageSample, now_ms: int) -> bool` | 5시간 규칙 그대로(U3) |
| 유지 | `drop_passed_resets(resets: RateLimitResets, now_ms: int) -> RateLimitResets \| None` | 그대로 |
| 삭제 | ~~`parse_usage_history(text: str) -> UsageSample \| None`~~ | 데스크톱 출처 제거(P1-A) |
| 사설 변경 | `_valid_used_percentage(window: object) -> int \| None` | docstring 개정 — "상태줄 출력 전용, 캡처하지 않는다(S7)" 문장 삭제. 이제 **캡처의 정본**이다 |

### 7.2 `hub/bin/hub_collect.py` (I/O)

| 구분 | 시그니처 | 계약 |
|------|----------|------|
| 유지 | `read_rate_limit_capture() -> tuple[RateLimitCapture \| None, tuple[str, ...]]` | 반환 타입만 변경. 파일 부재는 경고 없음, 읽기 실패·계약 불일치만 경고 1건. **절대 예외를 던지지 않는다** |
| 유지 | `write_rate_limit_capture(capture: RateLimitCapture) -> None` | 인자 타입만 변경. `dataclasses.asdict` + `_atomic_write_text` 그대로 |
| 신규(사설) | `_capture_for_snapshot(now_ms: int, config: HubConfig) -> tuple[UsageSample \| None, RateLimitResets \| None, tuple[str, ...]]` | 스위치·만료·롤오버·지난 값까지 적용. **파일 읽기 1회** |
| 삭제 | ~~`read_latest_usage_sample()`~~ · ~~`_usage_for_snapshot()`~~ · ~~`_rate_limit_resets_for_snapshot()`~~ | 위 하나로 통합 |
| 유지 | `collect_snapshot(now_ms: int) -> HubSnapshot` | 배선 3줄만 교체. 반환 계약 불변 |

### 7.3 `hub/bin/hub.py` (CLI)

| 구분 | 시그니처 | 계약 |
|------|----------|------|
| 변경(사설) | `_usage_sample_age_ms(now_ms: int, config: HubConfig) -> int \| None` | **캡처에서 퍼센트를 실을 수 있을 때만** 나이(= `now - captured_at_ms`). 스위치 off·캡처 부재·계약 불일치·퍼센트 부재면 `None` |
| 변경(사설) | `_rate_limit_resets_remaining_ms(now_ms: int, config: HubConfig) -> dict \| None` | 캡처 → `resets_from_capture` → `drop_passed_resets` 로 1줄 추가 |
| 유지 | `_rate_limit_capture_age_ms(...)` | 캡처 자체의 나이(퍼센트 유무 무관). 위 필드와 **쌍으로** 원인을 가른다 |

`cmd_status` 의 JSON 필드 이름은 전부 그대로다(문서·스킬 계약 보존).

### 7.4 `hub/bin/hub_statusline.py` (I/O 진입점)

```
_run():
  payload_text = sys.stdin.read()
  capture = hub_usage.parse_status_line_rate_limits(payload_text, now_ms)   # 순수, 예외 없음
  print(hub_usage.format_status_line_summary(capture))                      # 출력 먼저
  if capture is None: return                                                # 파일 접근 0회
  previous, _warnings = hub_collect.read_rate_limit_capture()
  if not hub_usage.same_capture_values(previous, capture):
      hub_collect.write_rate_limit_capture(capture)
```

`main()` 의 "항상 exit 0 · 어떤 예외도 밖으로 내지 않는다" 계약은 그대로다.

### 7.5 `hub/bin/hub_template.html` (JS — 전부 순수 함수 + 기존 렌더 함수 수정)

| 구분 | 시그니처 | 계약 |
|------|----------|------|
| 신규 | `visibleAgentRuns(runs)` → `array` | 화면에 실을 칩 목록의 **유일한 판정자**. 안 A: `slice(0, MAX_VISIBLE_AGENT_CHIPS)` / 안 B: `filter(is_running)` |
| 변경 | `renderAgentRuns(runs)` → `string` | `visibleAgentRuns` 를 쓰고 `+N` 블록 삭제 |
| 신규 | `shouldRenderSession(session)` → `boolean` | V2(+ Z1 채택 시 stale 컷오프) 판정. 순수 |
| 변경 | `renderProject(project)` → `string` | 세션을 `shouldRenderSession` 으로 걸러 `<ul>` 생성 여부까지 결정(V3) |
| 변경 | `renderUsagePanel(usage, resets)` | 문구 상수만 변경(P6). 게이팅 로직 불변 |
| 상수 | `USAGE_CYCLE_NOTE = '· 세션 진행 중에만 갱신'` · `STALE_SESSION_HIDE_AFTER_MS = 12 * MS_PER_HOUR`(Z1 채택 시) | GOTCHA 2 참조 |

---

## 8. 설계 결정과 근거 (요약표)

| # | 결정 | 한 줄 근거 |
|---|------|-----------|
| W1 | 트랙 최소폭을 `max(320px, calc((100% - 24px)/3 - 1px))` 로 | 미디어 쿼리·새 breakpoint 없이 3열 상한을 **산술적으로** 만든다. 좁은 폭 동작은 완전히 불변 |
| W2 | `.wrap{max-width}`·`.card{height}` 불변 | 카드 높이는 세션 3개 기준의 독립 결정. 폭 제한을 `max-width` 로 하면 카드가 320px 로 좁아진다 |
| V1 | 세션 숨김 필터는 **클라이언트** | 서버에서 지우면 `_project_state` 가 `done` → `stale` 로 바뀐다(끝난 프로젝트가 경고색). D5 와 정합 |
| V2 | 숨김 조건 = `done` + 발췌 없음 + **보이는 칩 0개** | 칩 판정을 렌더와 공유해 "칩 없는데 줄만 남는" 어긋남을 없앤다 |
| V3 | 전부 걸러지면 `<ul>` 미생성 | 빈 목록을 접근성 트리에 남기지 않는다 |
| K1 | 상한은 클라이언트, 정렬은 서버 (D5 유지) | 서버가 자르면 화면이 공간에 맞출 자유를 잃는다 |
| K2 | `summarize_agent_runs` 정렬 = 실행 중 → 최근 → 타입명 | `+N` 을 없애면 상한 밖으로 밀린 **실행 중** 칩이 안 보일 수 있다. 정렬로 해결 |
| K3 | `.agent-chip-more`(+ 안 B 면 `MAX_VISIBLE_AGENT_CHIPS`) 삭제 | 우리 변경이 만든 고아만 제거 |
| Z1 | stale 컷오프 12시간, 클라이언트, 템플릿 상수 1개 | 앵커가 임의적임을 인정하고 되돌리기 비용을 1줄로 유지 |
| P1 | 퍼센트 = **캡처 단일 출처**, 데스크톱 경로 삭제 | 출처가 하나면 신선도·경고·진단도 하나. 죽은 1순위를 유지할 근거가 없다 |
| P2 | 캡처 스키마에 내림 정수 퍼센트 2개 추가(하위·상위 호환) | 마이그레이션 0줄. 구형 캡처는 "퍼센트 없는 정상 캡처" |
| P3 | 캡처 → (UsageSample, RateLimitResets) **두 갈래 투영** | `#dzh-data` 계약 불변 + 같은 숫자를 두 벌 직렬화하지 않는다 |
| P4 | 비교를 네 값으로 확장하고 함수명 개명 | 이름이 거짓이 되면 다음 사람이 퍼센트 비교를 빼먹는다. 정상 상태 쓰기 0회(S3) 유지 |
| P5 | 만료 = 5시간(U3) **또는** 세션 창 롤오버 | 나이가 어려도 창이 리셋되면 그 퍼센트는 확실히 틀렸다 |
| P6 | `sampled_at_ms` = 캡처 시각, 주기 문구 교체 | "약 15분 주기"는 데스크톱 앱 전제 문구다. 새 출처에는 주기가 없다 |
| P7 | 상태줄 출력도 캡처에서 만든다(파싱 1회) | 퍼센트 추출 규칙의 정본을 하나로 → 상태줄과 패널이 항상 같은 숫자 |
| P8 | D3(재작성 폭주)와 정합함을 정량으로 확인 | 내림 정수는 ≤100회/5시간, 이벤트 churn 의 작은 분수. 유휴 시 추가 0회 |
| — | **디자인 패턴 도입 없음** | dataclass 1개 + 순수 함수 5개 + JS 순수 함수 2개 + CSS 1줄. 추상화할 두 번째 사례가 없다(YAGNI) |

---

## 9. 구 PRP 개정 표기 (구현 범위에 포함 — 원문 삭제 금지)

| 파일 | 위치 | 덧붙일 문장 |
|------|------|-------------|
| `hub-session-activity-and-tooltip.md` | 결정 표 D4 행 아래 | `> **개정됨.** \`+N\` 오버플로 칩은 [\`hub-card-cleanup-and-usage-source.md\`](./hub-card-cleanup-and-usage-source.md) 결정 K1~K3 으로 제거됐다. 상한 2개는 유지하되(안 A) 상한 밖으로 밀린 종료 타입은 표시되지 않는다.` |
| 〃 | 결정 표 D5 행 아래 | `> **유지됨(부분 개정).** "자르기는 클라이언트, 요약은 서버" 는 그대로다. 다만 정렬 규칙이 "실행 중 먼저 → 최근 시작순" 으로 바뀌었다(K2).` |
| 〃 | 승인 항목 2 절 끝 | `> **재결정됨.** 상한 2개는 유지, \`+N\` 칩은 폐기(K1).` |
| `hub-theme-and-usage-panel.md` | 「사용량 데이터 출처」 절 | `> **개정됨(2회차).** \`plan-usage-history.json\` 은 2026-08 실측으로 사라졌다. 퍼센트의 출처는 statusLine 입력의 \`rate_limits.*.used_percentage\` 로 교체됐다 — [\`hub-card-cleanup-and-usage-source.md\`](./hub-card-cleanup-and-usage-source.md) 결정 P1.` |
| 〃 | 결정 표 U3 행 아래 | `> **확장됨.** 5시간 만료는 그대로 유효하고, 여기에 "세션 창 롤오버 시 즉시 만료"(P5)가 더해졌다.` |
| 〃 | 결정 표 U1 행 아래 | `> **적용 대상 소멸.** \`parse_usage_history\` 삭제와 함께 이 규칙의 대상이 없어졌다(원칙 자체는 P2 의 필드 단위 탈락으로 계승).` |
| 〃 | 「패널 명세」 표의 「주기 고지」 행 | `> **개정됨.** \`· 약 15분 주기\` → \`· 세션 진행 중에만 갱신\`(P6).` |
| `hub-usage-reset-time-and-refresh.md` | 결정 표 S7 행 아래 | `> **개정됨.** \`used_percentage\` 를 **캡처한다**(내림 정수). 기각 근거였던 "타입 규칙 불일치"는 내림 정수로, "재작성 폭주"는 정량 평가로 해소됐다 — 결정 P2·P4·P8.` |
| 〃 | 기각 대안 4·6 항목 끝 | `> **채택됨(재검토).** 데스크톱 파일이 실제로 사라져 전제가 바뀌었다 — 결정 P1.` |
| 〃 | 결정 표 R3 행 아래 | `> **유지됨.** 퍼센트가 없으면 패널이 없다는 게이팅은 그대로다. 다만 그 퍼센트의 출처가 캡처로 바뀌었으므로, 이제 \`/hub statusline on\` 이 패널 표시의 사실상 전제다.` |
| `hub-usage-collapse-and-grid.md` | 그리드 결정(G1~G5) 절 | `> **개정됨.** 열 수 상한이 4 → **3** 으로 제한됐다(결정 W1). 1·2열 임계값(683/1015px)은 불변.` |

---

## 10. GOTCHA

1. **서브픽셀 반올림이 3열을 2열로 붕괴시킬 수 있다.** `calc((100% - 24px)/3)` 을 그대로 쓰면
   트랙+gap 이 콘텐츠폭의 정확히 1/3 이 되어 비율이 3.0 에 걸린다. 브라우저 레이아웃 단위
   (Chromium 1/64px)가 위로 반올림하면 비율이 2.9999… 가 되어 **2열**이 된다. `-1px` 여유는
   장식이 아니라 이 붕괴를 막는 값이다 — 지우지 마라.
2. **`STALE_SESSION_HIDE_AFTER_MS` 는 `MS_PER_HOUR` 선언(현재 361행) *뒤에* 선언해야 한다.**
   `var` 호이스팅은 선언만 올리고 할당은 올리지 않는다 — 앞에 두면 `12 * undefined = NaN` 이
   되어 비교가 항상 `false` 가 되고 컷오프가 **조용히** 죽는다.
3. **항목 2 와 항목 3 은 같은 함수를 공유한다.** `shouldRenderSession` 이 `agent_runs.length` 를
   직접 보면 안 된다(안 B 에서 종료 칩이 걸러지는데 줄은 남는다). 반드시 `visibleAgentRuns` 를
   경유한다.
4. **`same_capture_values` 에서 `captured_at_ms` 를 비교에 넣으면 0.3초마다 원자적 쓰기가
   발생한다.** 결정 S3 의 전부가 이 제외다. 테스트 R27(동일 페이로드 재생 시 mtime 불변)이
   회귀를 막지만, 픽스처에 퍼센트가 없으면 **새 필드의 회귀는 못 잡는다** → 픽스처에
   `used_percentage` 를 넣어야 한다.
5. **캡처 파일을 사이클당 두 번 읽으면 경고가 두 줄로 뜬다.** `collect_snapshot` 이 사설 함수
   2개를 각각 부르던 구조(C10)를 그대로 두고 퍼센트만 캡처에서 읽으면 이 버그가 생긴다 →
   `_capture_for_snapshot` 하나로 통합한다.
6. **퍼센트 스케일이 0~1 로 바뀌면 `math.floor` 가 조용히 `0%` 를 만든다.** `_valid_used_percentage`
   는 실수를 허용하므로 `0.43` → `0` 이다. 이것이 U2 가 원래 막던 실패이고, 이제 그 값이 패널에
   실린다 → §14 리스크 3 의 감지 경로를 README·`/hub status` 에 남긴다.
7. **`used_percentage > 100`(초과 사용) 은 검증에서 탈락해 패널이 사라진다.** CLI 는
   `utilization*100` 을 그대로 주므로 100 을 넘을 수 있는지는 미확인이다 — 클램프하지 않고
   현행 규칙을 유지한다(일어나지 않을 상황에 코드를 넣지 않는다). 발생하면 `/hub status` 의
   `rate_limit_capture_age_ms` 는 숫자인데 `usage_sample_age_ms` 가 `null` 인 조합으로 나타난다.
8. **`hub_usage.py` 는 ★순수를 유지해야 한다.** T25-10 이 `open(`·`Path(`·`os.` 부재를 강제한다.
   새 함수도 `now_ms`·`captured_at_ms` 를 **인자로** 받는다.
9. **설치본과 저장소는 별개다.** `hub/bin/` 을 고쳐도 `~/.claude/hub/bin/` 에는 반영되지 않는다 →
   `hub/install.sh --force` + `/hub server restart` 없이는 화면이 바뀌지 않는다(§13).
10. **`/hub statusline on` 을 켜도 즉시 값이 생기지 않는다.** `rate_limits` 는 Pro/Max 세션의
    **첫 API 응답 이후**에 붙는다 — 등록 후 한 턴을 진행해야 `rate_limits.json` 이 생긴다.
11. **템플릿 상단 주석 블록의 데이터 계약 서술도 갱신 대상이다**(13~28행). `rate_limit_resets`
    설명에 "퍼센트도 같은 캡처에서 온다"를 한 줄 덧붙인다 — 다음 사람이 출처를 데스크톱 앱으로
    오해하지 않게.

---

## 11. 테스트 계획

검증 정본: `bash tests/run.sh`(전체) / `python3 -m unittest discover -s tests/hub -t .`(파이썬).
이 레포에는 별도 linter·type checker 설정이 없다. **JS 단위 테스트는 없다**(러너 도입은 전제 1
위반) — 템플릿은 `tests/run.sh` T25 의 grep 회귀 + 수동 확인 두 축으로 검증한다.

### 11.1 신규 — `tests/hub/test_hub_usage.py` (★순수, 케이스 N1~N24)

`parse_status_line_rate_limits`

| # | 입력 | 기대 |
|---|------|------|
| N1 | 두 창 정상(`used_percentage: 23.5`·`41`) | 퍼센트가 `23`·`41`(내림), 리셋 2개 ms 매핑 |
| N2 | `five_hour` 만 존재 | 세션 값 2개만 채워지고 주간은 `None` |
| N3 | `used_percentage` 없이 `resets_at` 만 | 리셋만 채워짐(구 동작 보존) |
| N4 | `resets_at` 없이 `used_percentage` 만 | **캡처가 만들어진다**(유효성 규칙 변경의 핵심, P2) |
| N5 | `used_percentage: true` / `"23"` | 그 필드만 탈락 |
| N6 | `used_percentage: 101` / `-1` | 그 필드만 탈락 |
| N7 | `used_percentage: 0` / `100` | 경계 수용 |
| N8 | `rate_limits` 키 없음 | `None`(예외 없음) |
| N9 | 네 값 전부 무효 | `None` |
| N10 | 깨진 JSON / 빈 문자열 | `None`(예외 없음) |

`parse_rate_limit_capture`

| # | 입력 | 기대 |
|---|------|------|
| N11 | 신형 5필드 라운드트립(`asdict`→`json`→파싱) | 원본과 동일한 `RateLimitCapture` |
| N12 | **구형 3필드**(퍼센트 키 없음) | 퍼센트 `None` 인 정상 캡처 — **하위 호환의 핵심** |
| N13 | 퍼센트만 있고 리셋 없음 | 정상 캡처 |
| N14 | 퍼센트가 실수(`23.5`)로 저장된 파일 | 그 필드만 `None`(파일 경로는 엄격 int) |
| N15 | `captured_at_ms` 누락/문자열 | `None` |
| N16 | 네 값 전부 없음 | `None` |
| N17 | 여분 키가 있는 파일(상위 호환) | 알려진 키만 읽고 정상 파싱 |

투영·판정

| # | 대상 | 입력 | 기대 |
|---|------|------|------|
| N18 | `usage_sample_from_capture` | 퍼센트 둘 다 있음 | `UsageSample(sampled_at_ms=captured_at_ms, …)` |
| N19 | 〃 | 한쪽만 / 둘 다 없음 | `None` |
| N20 | `resets_from_capture` | 리셋 한쪽만 | 그쪽만 채워진 `RateLimitResets` |
| N21 | 〃 | 리셋 둘 다 없음 | `None` |
| N22 | `is_session_window_rolled_over` | 리셋이 `now` 보다 과거 / 미래 / `None` | `True` / `False` / `False` |
| N23 | `same_capture_values` | `captured_at_ms` 만 다름 | `True`(재기록 없음) |
| N24 | 〃 | 퍼센트 1개만 다름 / 리셋 1개만 다름 / `previous=None` | 전부 `False` |

`format_status_line_summary`(캡처 인자 버전)

| # | 입력 | 기대 |
|---|------|------|
| N25 | 퍼센트 2개 있는 캡처 | `세션 23% · 주간 41%` |
| N26 | 퍼센트 한쪽만 / 없음 / `None` 캡처 | `세션 23%` / `''` / `''` |

**삭제**: `ParseUsageHistoryTest`(케이스 1~13 + m5 경계) · `IsUsageSampleExpiredTest` 는
**유지**(케이스 14~17, U3 그대로) · `SameResetTimesTest` → `SameCaptureValuesTest` 로 개정.

### 11.2 추가/재작성 — `tests/hub/test_hub_collect.py` · `test_hub_statusline.py`

| # | 대상 | 시나리오 | 기대 |
|---|------|---------|------|
| N30 | `_capture_for_snapshot` | 캡처 파일 없음 | `(None, None, ())` — **경고 0건** |
| N31 | 〃 | `show_usage_panel:false` | `(None, None, ())` + `Path.read_text` **미호출**(기존 case19 의 I/O 경계 검증 방식을 그대로 계승) |
| N32 | 〃 | 정상 신형 캡처 | `UsageSample`·`RateLimitResets` 둘 다 채워짐 |
| N33 | 〃 | 구형 캡처(퍼센트 없음) | `usage is None`, `resets` 는 채워짐 |
| N34 | 〃 | 캡처 나이 6시간 | `usage is None`(만료), 경고 0건 |
| N35 | 〃 | 나이 3시간 + 세션 리셋이 1시간 전 | `usage is None`(**P5 롤오버**), 경고 0건 |
| N36 | 〃 | 깨진 캡처 파일 | `(None, None, 경고 1건)` — 경고가 **1건**임을 확인(GOTCHA 5 회귀) |
| N37 | `collect_snapshot` | 깨진 캡처 파일 | 프로젝트 수집이 죽지 않고 `snapshot.usage is None`, 경고 1건 |
| N38 | `write/read_rate_limit_capture` | 신형 라운드트립 | 5필드 보존 |
| N39 | `hub_statusline` 진입점 | 퍼센트만 변한 재생 | 파일이 **다시 쓰인다**(mtime 변화) |
| N40 | 〃 | 완전 동일 페이로드 재생(퍼센트 포함) | mtime **불변**(GOTCHA 4) |
| N41 | 〃 | `rate_limits` 없음 | 파일 미생성 + 상태줄 빈 줄 + exit 0 |
| N42 | 〃 | 깨진 stdin | 예외 없음 + exit 0 |

기존 `UsageForSnapshotTest`(case18~23·case_m1) 와 `CollectSnapshotUsageIsolationTest`(case24) 는
데스크톱 파일 경로를 monkeypatch 하므로 **캡처 파일 기반으로 재작성**한다. `case_m1`(찢긴
멀티바이트 읽기)의 의도는 살려 `read_rate_limit_capture` 대상으로 옮긴다 — 다만 `read_text` 에
`errors="replace"` 가 없으므로(현행) **`UnicodeDecodeError` 가 `except OSError` 를 뚫는다**:
이 사실을 확인해 `errors="replace"` 를 추가할지는 구현 시 테스트가 먼저 드러내게 한다(N43).

| # | 대상 | 시나리오 | 기대 |
|---|------|---------|------|
| N43 | `read_rate_limit_capture` | 잘린 멀티바이트 바이트열 | 예외 없음 + 경고 1건 (필요하면 `errors="replace"` 추가) |

### 11.3 `tests/run.sh` — T25 개정 4건 + 신규 7건

| 번호 | 상태 | 내용 |
|------|------|------|
| T25-31 | **개정** | `plan-usage-history.json` grep 삭제 → `used_percentage`·`statusLine`·`show_usage_panel` 이 `hub/README.md` 에 있는지로 교체. (죽은 전제를 테스트로 고정하지 않는다) |
| T25-32 | **개정** | 그리드 토큰 `repeat(auto-fill,minmax(320px,1fr))` → 새 트랙 리터럴. `max-width:1440px`·`display:grid`·`align-items:start`·`grid-column:1/-1` 은 유지 |
| T25-41 | **개정** | `약 15분 주기` grep 삭제 → `세션 진행 중에만 갱신` 으로 교체. `POLL_INTERVAL_MS = 60000` 검사는 유지 |
| T25-43 | **개정** | 안 A: 토큰 목록에서 `agent-chip-more` 관련을 제거하고 **부재 검사**로 뒤집는다(`agent-chip-more` 가 남아 있으면 실패). `active_agent_types` 부재·`summarize_agent_runs`·`agent_runs`·`renderAgentRuns`·`agent-chip`·`MAX_VISIBLE_AGENT_CHIPS` 는 유지. 안 B: `MAX_VISIBLE_AGENT_CHIPS` 를 목록에서 빼고 주석의 의도 문장을 개정 |
| T25-50 | 신규 | 그리드 3열 상한 회귀 — `max(320px` 와 `/3 - 1px)` 가 템플릿에 있고, `hub/README.md` 의 열 수 고지가 `1~3열` 로 갱신돼 있다 |
| T25-51 | 신규 | 세션 필터가 **클라이언트에만** 있다 — 템플릿에 `shouldRenderSession`·`visibleAgentRuns` 존재 + `hub_model.py` 에 `sessions=session_views` 가 그대로 있다(서버가 세션을 걸러내지 않는다는 증거) |
| T25-52 | 신규 | 칩 단순화 회귀 — 안 A: 템플릿에 `+' + overflowRuns.length` 류 오버플로 흔적이 없고 `hub_model.py` 정렬 키에 `is_running` 이 있다. 안 B: 템플릿에 `is_running` 필터가 있다 |
| T25-53 | 신규(Z1 채택 시) | `STALE_SESSION_HIDE_AFTER_MS` 가 템플릿에 있고 `MS_PER_HOUR` **뒤에** 선언돼 있다(GOTCHA 2 — 선언 줄 번호 비교) |
| T25-54 | 신규 | 퍼센트 출처 회귀 — `hub_collect.py`·`hub_usage.py` 에 `plan-usage-history`·`PLAN_USAGE_HISTORY_PATH`·`parse_usage_history` 가 **없고**, `session_used_percent`·`usage_sample_from_capture`·`same_capture_values` 가 있다 |
| T25-55 | 신규 | 문서 정합 — `commands/hub.md` 의 `usage_sample_age_ms` 설명에 데스크톱 앱 문구가 없고 `statusLine` 전제가 명시돼 있다 |
| T25-56 | 신규 | `#dzh-data` 계약 불변 — `hub_model.py` 의 `HubSnapshot` 에 `usage`·`rate_limit_resets` 두 필드가 그대로 있고 템플릿이 `snapshot.usage`·`snapshot.rate_limit_resets` 를 읽는다 |
| 헤더 | **개정** | 주석 `T25-1~T25-49` 와 `test_desc` 문자열 **두 곳** 모두 `T25-1~T25-56` 으로 |

---

## 12. 수동 확인 절차

전제: `hub/install.sh --force` → `/hub statusline on` → **Claude Code 세션 1턴 진행** →
`/hub server restart` → 브라우저에서 `http://127.0.0.1:8794/` 열기.

| # | 절차 | 기대 |
|---|------|------|
| M1 | 폭 420/700/1016/1200/1440/1920 순회 + 콘솔 열 수 확인(§5.1) | `1,2,3,3,3,3` · 가로 스크롤 없음 |
| M2 | 완료 세션이 있는 카드 확인 | 발췌·칩이 없는 완료 세션 줄이 없다. 발췌가 있는 완료 세션은 그대로 보인다 |
| M3 | 모든 세션이 걸러진 카드 확인 | `<ul class="sessions">` 자체가 없다(요소 검사) · 레이아웃 깨짐 없음 |
| M4 | 서브에이전트를 2종 이상 돌린 세션 확인 | `+N` 칩이 없다 · 안 A 면 실행 중 칩이 항상 첫 자리 |
| M5 | (Z1 채택 시) 12시간 넘은 stale 세션 확인 | 줄이 사라진다. 12시간 안쪽 stale 은 남는다 |
| M6 | `cat ~/.claude/hub/rate_limits.json` | 5필드가 있고 퍼센트가 정수다 |
| M7 | 상태줄과 패널 비교 | 상태줄 `세션 N% · 주간 M%` 와 패널 막대 숫자가 **정확히 같다**(P7) |
| M8 | 패널 펼침 | 막대 2개 + 창별 초기화 줄 + `마지막 갱신 … · 세션 진행 중에만 갱신` |
| M9 | 파일 mtime 관찰 — 세션을 5분간 idle 로 두기 | `rate_limits.json` mtime 이 변하지 않는다(P4) |
| M10 | `/hub status` | `statusline_installed:true` · `usage_sample_age_ms` 와 `rate_limit_capture_age_ms` 둘 다 숫자 |
| M11 | 구형 캡처 시뮬레이션 — 퍼센트 2필드를 손으로 지우고 `/hub server restart` | 패널은 사라지고 경고는 0건, `/hub status` 에서 capture age 는 숫자·sample age 는 `null` |
| M12 | `show_usage_panel:false` 로 두고 재수집 | 패널 없음 · 경고 없음 |
| M13 | 라이트/다크 테마 각각 확인 | 새 색 리터럴 없음 → 두 테마 모두 정상 |

---

## 13. 구현 순서 (마일스톤 — 각각 커밋 가능)

| # | 범위 | 검증 |
|---|------|------|
| 1 | 항목 1 — CSS 1줄 + README 열 수 고지 + T25-32·T25-50 | M1 · `bash tests/run.sh` |
| 2 | 항목 2+3 — 템플릿 JS(`visibleAgentRuns`·`shouldRenderSession`·`renderProject`·`renderAgentRuns`) + (안 A 면) `hub_model.summarize_agent_runs` 정렬 + `.agent-chip-more` 삭제 + README + T25-43·51·52 | M2~M4 · `unittest`(정렬 케이스) |
| 3 | 항목 4(선택) — 상수 1개 + 조건 1줄 + T25-53 | M5 |
| 4 | 항목 5-a — `hub_usage.py` 순수 확장/삭제 + 단위 테스트 N1~N26 (**배선 전, 독립**) | `unittest` |
| 5 | 항목 5-b — `hub_collect.py`(`_capture_for_snapshot`) · `hub_statusline.py` · `hub.py` 배선 + N30~N43 | `unittest` · `echo '{...}' \| python3 hub_statusline.py` 수동 |
| 6 | 항목 5-c — 템플릿 문구·주석 + `hub/README.md`·`commands/hub.md` + 구 PRP 개정 표기 + T25-31·41·54·55·56 + 헤더 범위 | `bash tests/run.sh` 전체 |
| 7 | 배포·수동 확인 — `hub/install.sh --force` → `/hub statusline on` → 세션 1턴 → `/hub server restart` | M6~M13 |

1·3 은 서로 독립이고, 2 는 1 과 독립이다. 5 는 4 에, 6 은 5 에 의존한다. **7 은 마지막에 한 번**
(설치본이 바뀌면 화면 확인이 가능해진다 — GOTCHA 9).

---

## 14. 리스크와 완화

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | `minmax(max(…), 1fr)` 의 브라우저 편차 | 열 수가 기대와 다르다 | `max()`·`calc()` 는 2020년 이후 전 브라우저 지원. M1 이 6개 폭에서 기계적으로 확인 |
| 2 | 컷오프·숨김이 필요한 정보를 지운다 | 사용자가 세션을 못 찾는다 | 조건이 좁다(완료+무정보 / stale+12시간). 되돌리기는 각각 1줄. `/hub status` 의 이벤트 수는 그대로 |
| 3 | **`used_percentage` 스케일 변경(0~100 → 0~1)** | 패널이 조용히 `0%` 를 그린다 | GOTCHA 6. 상태줄과 패널이 같은 값을 쓰므로(P7) 두 곳이 동시에 0% 가 되어 눈에 띈다. 감지 후 규칙 1줄 수정으로 대응 |
| 4 | statusLine 을 켜지 않으면 패널이 없다 | "고쳤다더니 안 보인다" | 배포 절차에 `/hub statusline on` 포함(§13-7) · README·`/hub status`·커맨드 고지 3곳에 전제 명시 |
| 5 | 세션 창 롤오버 후 패널이 사라진다(P5) | 화면이 자주 비어 보인다 | 정직한 상태다. 세션을 한 턴 돌리면 즉시 복구된다. README 에 1행 |
| 6 | `rate_limits` 는 Pro/Max 세션에서만 온다 | API 키 사용자에게 기능 없음 | 기존 고지 유지. 파일 부재는 경고 없는 정상 경로 |
| 7 | `hub.html` 재작성 증가 | 폴링 재렌더가 잦아진다 | P8 정량 — 이벤트 churn 의 작은 분수, 유휴 시 0회 |
| 8 | 데스크톱 파일 부활 | 삭제한 경로를 다시 만들어야 한다 | 삭제 diff 가 그 자체로 복구 지침이다(§15 대안 4). git 이력에 남는다 |
| 9 | 항목 2·3 조합이 완료 세션을 전부 없앤다 (`record_prompt_excerpt:false` + 안 B) | 세션 이력이 화면에서 사라진다 | 승인 항목 2 에 명시. 안 A 는 이 조합에서도 칩이 남는다 |

---

## 15. 검토했으나 채택하지 않은 대안

1. **`.wrap{max-width}` 를 1016px 로 줄여 3열을 만든다.** CSS 1줄로 끝나고 계산이 자명하다.
   그러나 카드가 모든 폭에서 최소치(320px)로 좁아져 프로젝트명·경로·발췌의 잘림이 지금보다
   심해진다. 3열 상한의 목적은 "카드를 넓게"인데 정반대가 된다 → 기각.
2. **미디어 쿼리로 `repeat(3, 1fr)` 을 고정한다.** 의도가 코드에 그대로 드러난다. 그러나 새
   breakpoint 상수(1016px 등)를 하드코딩해야 하고, 그 값이 `auto-fill` 계산과 이중으로
   존재하게 되어 한쪽만 고치는 어긋남이 생긴다 → 기각(W1 은 상수 0개).
3. **세션 필터를 서버(`hub_model.compose_project_views`)에 둔다.** 클라이언트가 단순해지고
   `#dzh-data` 도 작아진다. 그러나 `_project_state` 가 세션 유무로 갈라져(C5) 끝난 프로젝트
   배지가 `done` → `stale` 로 바뀐다 — 표시 개선을 하려다 상태 판정을 망친다 → 기각(V1).
4. **데스크톱 파일을 폴백으로 남긴다(P1 안 B).** macOS 사용자가 statusLine 을 켜지 않아도
   패널이 뜬다. 그러나 실측 불가능한 경로(파일이 없다)가 남아 썩고, 두 신선도 의미가 한
   메타 줄에 섞이며, 선행 PRP 리스크 5(두 출처 불일치)를 영구화한다 → 기각. 파일이 부활하면
   삭제 diff 를 되돌리는 국소 작업이다.
5. **캡처 dataclass 를 스냅샷에 그대로 싣는다(투영 없음).** 함수 2개를 아낀다. 그러나 같은
   퍼센트가 `usage` 와 `rate_limit_resets` 양쪽에 직렬화되어 `#dzh-data` 안에 같은 숫자가 두
   벌 생기고, 클라이언트가 어느 쪽을 읽어야 하는지 모호해진다 → 기각(P3).
6. **세션 창이 롤오버되면 주간 막대만 남긴다.** 정보 손실이 적다. 그러나 `renderUsagePanel` 의
   "막대 2개 필수" 게이팅을 부분 패널로 바꿔야 하고(새 표시 상태 3개), 접힘 요약 문구도
   분기가 필요하다 → 기각(P5의 대가를 수용).
7. **퍼센트 임계값(예: 80% 이상 경고색)을 넣는다.** 요구 범위 밖 + 새 매직 임계값 + 새 색
   → 기각(선행 PRP 의 같은 판단과 일관).
8. **`config.json` 에 컷오프·열 수·칩 상한을 노출한다.** "유연성"이 요구되지 않았고, 각 값은
   상수 1개라 수정이 1줄이다 → 기각(YAGNI, 전제 6).
9. **캡처에 퍼센트를 실수 그대로 저장하고 표시할 때 내림한다.** 원본 보존이라는 명분이 있다.
   그러나 `23.4→23.5` 같은 변화마다 파일이 다시 쓰이고 `content_key` 가 흔들려 결정 D3·S3 을
   정면으로 어긴다 → 기각(P2 는 **캡처 시점에** 내림한다).
10. **세션 정렬을 서버에서 최신순으로 바꾼다.** `compose_project_views` 1줄이다. 그러나
    `snapshot_content_key` 의 입력 순서가 바뀌어 기존 스냅샷과의 비교가 한 번 어긋나고(무해하나
    노이즈), 정렬은 표시 관심사다 → 클라이언트 정렬(§5.4 안 2)로 제시하고 서버 변경은 기각.

---

## 16. 사용자 승인이 필요한 결정 (구현 전 확인)

### 승인 항목 1 — 퍼센트 출처 우선순위 (결정 P1)

| 안 | 내용 | 대가 |
|----|------|------|
| **A (권고)** | 캡처 단일 출처. 데스크톱 파일 읽기 코드·테스트 17건 **삭제** | `/hub statusline on` 이 패널의 사실상 전제가 된다 |
| B | 캡처 우선 + 데스크톱 폴백(두 리더 유지) | 실측 불가능한 경로가 남고, 두 신선도 의미가 섞인다 |
| C | 데스크톱 우선 + 캡처 폴백 | 이 환경에서 1순위가 항상 실패하는 형태 |

### 승인 항목 2 — 칩 표시 방식 (결정 K1~K3)

| 안 | 세션 줄 예시 | 상실 |
|----|-------------|------|
| **A (권고)** | `✓ 완료 2시간 전 [implementer] [code-reviewer]` | 3번째 이후 종료 타입이 툴팁으로도 안 보인다 |
| B | `✓ 완료 2시간 전` (실행 중인 것만 칩) | 완료·대기 세션의 칩이 사라진다. **항목 2 와 결합하면** 완료 세션 줄 자체가 사라진다(`record_prompt_excerpt:false` 면 전부) → T25-43 의 의도(“완료 세션이 다시 빈 목록이 되지 않는다”)를 개정해야 한다 |

### 승인 항목 3 — stale 세션 표시 기한 (결정 Z1)

| 안 | 내용 | 비고 |
|----|------|------|
| **1 (권고)** | 12시간 컷오프 도입(클라이언트, 상수 1개) | 앵커는 임의값임을 인정. 되돌리기 1줄 |
| 2 | 컷오프 없이 **세션 정렬을 최신순으로** | 정보 손실 0. 죽은 세션이 살아 있는 세션 아래로 내려간다(§2.4-2 의 진짜 원인) |
| 1+2 | 둘 다 | 서로 다른 문제를 각각 해결 |
| 3 | 도입하지 않음 | 실제 잔존 상한은 7일이 아니라 약 24~48시간(§2.4-1) |

### 승인 항목 4 — 세션 창 롤오버 만료 (결정 P5)

캡처 나이가 5시간 미만이어도 **세션 리셋 시각이 지났으면** 퍼센트를 숨긴다. 정확성은 오르지만
패널이 더 자주 사라진다. 제외하려면 조건 1줄 + 테스트 3건을 빼면 된다.

### 승인 항목 5 — 삭제 범위 확인

- `hub_usage.parse_usage_history` + 단위 테스트 **17건** 삭제(승인 항목 1-A 채택 시)
- `hub_collect.PLAN_USAGE_HISTORY_PATH`·`read_latest_usage_sample` 삭제
- 템플릿 `.agent-chip-more` CSS 삭제(+ 안 B 면 `MAX_VISIBLE_AGENT_CHIPS` 상수)
- `tests/run.sh` T25-31·41 의 **기존 grep 토큰 2개**(`plan-usage-history.json`·`약 15분 주기`) 삭제
  — 죽은 전제를 테스트로 고정하지 않기 위한 것이며, 테스트의 "문구가 유실되지 않는다"는 의도는
  새 토큰으로 계승한다

---

## 17. 발견 사항 — 이번 변경이 만들지 않은 문제 (언급만, 삭제·수정하지 않는다)

1. **`read_rate_limit_capture` 는 `errors="replace"` 없이 `read_text` 한다** →
   찢긴 멀티바이트 읽기 시 `UnicodeDecodeError` 가 `except OSError` 를 뚫는다.
   `read_latest_usage_sample` 은 같은 문제를 이미 검수 M1 에서 고쳤다(선례 존재).
   이번에 그 함수가 **유일한 사용량 출처가 되므로** 테스트 N43 으로 확인하고, 필요하면
   `errors="replace"` 1개를 추가한다(범위 내로 편입 — 이번 변경이 이 경로의 중요도를 올린다).
2. **세션 목록이 오래된 것부터 그려진다**(C8) — §2.4-2. 승인 항목 3-2 로만 제시하고,
   선택되지 않으면 손대지 않는다.
3. **`usage-meta` 툴팁과 `usage-reset` 툴팁이 같은 타임스탬프를 보여준다**(P6 부수 효과).
   중복이지만 각 문맥에서 옳으므로 그대로 둔다.
4. **`.card{height:340px}` 고정** 때문에 세션을 숨겨도 카드가 작아지지 않는다. 고정 높이는
   독립 결정(템플릿 65~67행 주석)이므로 이 PRP 에서 건드리지 않는다.
