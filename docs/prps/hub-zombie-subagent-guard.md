# 허브 — 좀비 서브에이전트 가드 (sticky working 수정) (PRP)

> 요구 2건: **R1** `SubagentStop` 이 영영 오지 않은 서브에이전트 하나가 세션을 `작업중` 으로
> 붙잡아 둔다(카드 glow·상태 배지) · **R2** 그 서브에이전트의 칩이 영구히 실행중(●)으로 남는다

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_model.py`(판정 본체) + 테스트·문서. **`hub_template.html` 은 한 줄도 바뀌지 않는다** |
| 브랜치 | `main` (HEAD `a378aaa`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md)(「상태 판정 규칙 2」 296~316행) → [`hub-session-activity-and-tooltip.md`](./hub-session-activity-and-tooltip.md)(칩 정본) → [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)(결정 K1~K3 칩 상한·정렬) → [`hub-session-revival-and-stale-tier1.md`](./hub-session-revival-and-stale-tier1.md)(직전 수정, 이 문서가 그 **B1·X6** 을 해소한다) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 상태 판정 규칙(정본 문서)과 공개 함수 시그니처 3개가 바뀐다 |
| 규모 | **Small** — 신규 1개(이 문서) / 수정 5개 파일. Python 순증 약 **+25줄**, 템플릿 순증 **0줄** |
| 새 외부 의존성 | **없음** (stdlib). 새 데이터 계약 필드 **0개**, 새 CSS·새 색 리터럴 **0개** |
| 결정 코드 | **ZG**(Zombie Guard). `grep -rhoE "결정 [A-Z]{1,3}[0-9]+" docs/prps/*.md` 로 확인 — 사용 중 접두사는 `A B C D DG E EX F G GN K L LG M MD N O ON P Q R RV S SP T TR U UT V W X Y Z` 이며 `ZG` 는 미사용 |
| 승인 상태 | **미승인** — 「승인 요청 항목」 1~5 회신 대기 |

### 진단의 근거 (이 문서를 쓰면서 직접 재측정한 것만 적는다)

측정 대상: `~/.claude/hub/events/2026-08-{12,13,14}.jsonl` 전량(3일), 완료된 서브에이전트 실행
**90건** · `SubagentStop` **196건**. 상태 재구성은 실제 `hub_model` 모듈에 이벤트를 시각 절단해
넣는 "시간 여행" 프로브로 했다(추정 없음).

| # | 관측 | 출처 |
|---|------|------|
| **E1** | 세션 `8dd0eba0`(coding-env)에서 `2026-08-14 14:48:01` 에 `SubagentStart(code-reviewer, agent_id=a1e56915d8cddf9ab)` 가 기록된 뒤 대응 `SubagentStop` 이 **없다**. 3시간 뒤에도 `ended_at_ms is None` 이다 | 이벤트 로그 실측 |
| **E2** | 그 결과 `summarize_agent_runs` 가 `code-reviewer` 칩을 **3시간 연속 `is_running=True`(●)** 로 준다. 지금 시점 칩 목록: `[design-architect(True), code-reviewer(True), implementer(False)]` — 가운데가 거짓이다 | 실측 프로브 |
| **E3** | 1분 간격 시간 여행(14:48~17:50, 182 표본): 현행 판정은 `working` 126 · `stale` 55 · `idle` 1. **좀비만이 유일한 근거였던 표본이 6건**(16:28 1분 + 17:34~17:38 5분) — 그 6분간 `turn_state=="ended"` 이고 좀비 외에 열린 서브에이전트가 0개였다. 즉 진실은 `idle` 인데 화면은 `작업중` + glow 였다 | 실측 프로브 |
| **E4** | 같은 버그의 **두 번째 독립 사례**: klago 세션 `7443adc9` 에 `14:51` 시작 `workflow-subagent` 고아가 **10건** 열려 있다. 1분 간격 179 표본 중 **16건**에서 좀비만이 `working` 의 근거였다(16:22~16:38) | 실측 프로브 |
| **E5** | 3일간 고아(`SubagentStart` 만 있고 `SubagentStop` 없음) **18건** — `workflow-subagent` 16 · `code-reviewer` 1(E1) · `design-architect` 1(측정 시점에 실제 실행 중인 이 세션). 즉 **드문 사고가 아니라 상시 발생**한다 | 실측 |
| **E6** | 완료된 정상 실행 90건의 소요: **p50 7.0분 · p90 18.4분 · 최장 47.3분**(implementer). 47.3분이 3일간 유일한 40분 초과 사례다 | 실측 |
| **E7** | **`SubagentStop` 196건 중 52건(27%)이 메인 턴 `Stop` 보다 뒤에 도착한다**(예: `8dd0eba0` 17:03 SubagentStart → 17:03 Stop → 17:21 SubagentStop). 즉 서브에이전트는 정상적으로 메인 턴보다 오래 산다 | 실측 |
| **E8** | 정상 백그라운드 실행 중에는 **세션 이벤트가 하나도 발생하지 않는다**(17:03~17:21 구간 이벤트 0건) | 실측 |
| **E9** | `stale` 오버레이는 **완전한 무용지물이 아니다** — 15:19~16:13(진짜 침묵 55분) 구간에서 현행 판정도 `stale` 이었다. 즉 오버레이가 sticky working 의 *일부* 를 덮는다. 다만 그 구간에도 `base_state` 는 `working` 이고 칩은 ● 였다 | 실측 프로브 |
| **E10** | 필터되는 이벤트(compact `SessionStart`, untracked `SubagentStop`)도 `last_event_at_ms` 를 갱신한다(`build_session_facts`, hub_model.py 362~363행 — 필터 판정 365~369행보다 **앞**). 실측: `17:36 SubagentStop(agent_type="")` → `17:36 SessionStart(source=compact)` 두 건이 stale 시계를 리셋했다 | 소스 + 실측 |
| **E11** | `_compute_base_state` 호출부는 **1곳**(hub_model.py 394행) · `compute_session_view` 비테스트 호출부는 **1곳**(570행) · `summarize_agent_runs` 비테스트 호출부는 **1곳**(396행). 테스트 호출은 각각 16건·8건 | `grep -rn` |

**시간 여행 프로브 결과 — 타임아웃 T 후보별 판정 변화(1분 간격)**

| 세션 | 표본 | 현행 | T=30분 | T=60분 | T=90분 | T=120분 |
|---|---|---|---|---|---|---|
| `8dd0eba0` coding-env | 182 | working 126 / stale 55 / **idle 1** | idle 7 | idle 7 | **idle 7** | idle 6 |
| `7443adc9` klago | 179 | working 129 / stale 50 / **idle 0** | idle 19 | idle 19 | **idle 16** | idle 0 |

**T 후보별 오탐(정상 에이전트를 좀비로 오인) — 완료된 90건 전수 대조**

| T | 오인 건수 | 오인 내용 | 실측 최장(47.3분) 대비 여유 |
|---|---|---|---|
| 30분 | **1건** | 47.3분 implementer | **−17.3분** ❌ |
| 45분 | **1건** | 47.3분 implementer | **−2.3분** ❌ |
| 60분 | 0건 | — | +12.7분 ⚠️ |
| **90분(권고)** | **0건** | — | **+42.7분 (1.9×)** ✅ |
| 120분 | 0건 | — | +72.7분 (여유 과다 — klago 사례를 1분도 못 고친다) |

> 이 표가 결정 ZG2(T=90분)의 유일한 근거다. **T=120분은 klago(E4)의 16분 오류를 하나도
> 고치지 못하고**(위 표 `idle 0`), T≤45분은 실측 최장 정상 실행을 죽인다.

**프로젝트 상태·티어1 세대 판정 오염(현행 → T=90분)**

| 시각 | 프로젝트 | 프로젝트 상태 | 살아 있는 세션 수(`LIVE_SESSION_STATES`) |
|---|---|---|---|
| 16:22 | klago | `working` → **`idle`** | 1 → **0** |
| 16:28 | coding-env · klago | `working` → **`idle`** | 1 → **0** |
| 17:34 | coding-env | `working` → **`idle`** | 1 → **0** |

> 좀비가 `working` 으로 남는 동안 그 세션은 `is_tier1_from_previous_task` 의 입력
> (`_live_session_start_times_ms`)에 계속 끼어 있었다 — 직전 PRP 가 **엣지 X6** 로 기록해 둔
> 오염이 실측으로 확인됐고, 이 가드가 그것을 함께 해소한다(결정 ZG6).

---

## 요구사항 요약

허브의 세션 상태 판정에서 `_compute_base_state` 는 `SubagentStop` 을 못 본 서브에이전트가
하나라도 있으면 무조건 `working` 을 돌려준다(hub_model.py 386행). 그런데 서브에이전트는
API 오류로 죽으면서 `SubagentStop` 훅을 발화하지 못하는 일이 있고(E1 — "You've hit your session
limit"), 그런 **좀비 실행 1건이 세션을 영구히 `작업중` 으로 붙잡는다**: 메인 턴이 끝나
(`Stop` 수신, `turn_state=="ended"`) 실제로 아무것도 돌고 있지 않은 순간에도 카드가 glow 하고
(E3 — 실측 6분), 서브에이전트 칩은 3시간째 실행중(●)을 주장하며(E2), 그 세션이 `working` 인
동안 티어 1 세대 판정까지 오염된다(위 표).

이 버그는 오늘 오전에 고친 sticky done(세션 부활, `hub-session-revival-and-stale-tier1.md`)의
**거울상**이다: 그때는 "죽었다는 표시가 안 풀리는" 문제였고, 이번엔 **"살아있다는 표시가 안
풀리는"** 문제다. 이 문서는 **나이 기반 좀비 가드**를 순수 함수 하나로 도입해, 상태 판정과
칩 표시가 **같은 술어**를 공유하도록 만든다.

### 사용자 스토리

| # | 스토리 |
|---|--------|
| S1 | 서브에이전트가 죽어 `SubagentStop` 이 오지 않아도, 메인 턴이 끝나면 카드 glow 와 `작업중` 배지가 꺼진다 |
| S2 | 그 죽은 서브에이전트의 칩은 다른 종료된 칩과 똑같이 중립색으로 보인다 — ● 이 남지 않는다 |
| S3 | 47분 걸리는 정상 구현 에이전트는 실행 내내 계속 `작업중` 으로 빛난다 — 가드가 과잉 발동하지 않는다 |
| S4 | 카드가 `대기` 로 바뀌었는데 칩만 ● 로 남는 **모순된 화면을 볼 수 없다** |
| S5 | 좀비 때문에 옆 프로젝트의 「이전 작업」 라벨이 잘못 켜지거나 꺼지는 일이 없어진다 |

### 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G1 | 좀비만 남은 세션에서 `turn_state=="ended"` 면 `base_state == "idle"` 이다 | 단위 ZG6 |
| G2 | 실측 최장 정상 실행(47.3분)은 좀비로 판정되지 않는다 | 단위 ZG12 |
| G3 | 경계가 명시적이다 — 나이 `T−1` 은 실행, `T` 는 좀비 | 단위 ZG2·ZG3 |
| G4 | **상태 판정과 칩 표시가 같은 술어를 쓴다** — 한쪽만 좀비를 걸러내는 구현이 불가능하다 | 단위 ZG11 + T25-92(기계적) |
| G5 | 좀비가 티어 1 세대 판정의 살아 있는 세션 집합에서 빠진다 | 단위 ZG13 |
| G6 | 매직 넘버가 없다 — `SUBAGENT_ZOMBIE_AFTER_MS` 명명 상수 하나 | T25-91 |
| G7 | 템플릿(`hub_template.html`)이 **한 줄도 바뀌지 않는다** | `git diff --stat` 에 템플릿 부재 |
| G8 | 옛 무조건 판정(`any(sub.ended_at_ms is None ...)`)이 소스에서 사라졌다 | T25-91 역방향 |

---

## 확정된 전제 (재론하지 않는다)

1. **「메인 턴 `Stop` 시 실행 중 서브에이전트를 전부 종료 처리」는 오답이다.** 실측 E7 이
   확정한다 — `SubagentStop` 196건 중 **52건(27%)** 이 `Stop` 보다 뒤에 온다. 그렇게 하면
   정상 백그라운드 실행의 glow 가 매번 꺼진다. 직전 PRP 의 **결정 RV2** 도 같은 이유로 이미
   이 방향을 기각했다("상한 없는 실패").
2. **이벤트 스키마(`{t,e,s,c,so,r,ai,at,p}`)와 `hub_hook.py` 는 건드리지 않는다.** 이 판정은
   이미 수집되는 이벤트만으로 성립한다.
3. **판정은 파이썬(순수 레이어), 표시는 템플릿.** 이 저장소에는 JS 테스트 러너가 없고 grep
   회귀만 있다 — 표 기반으로 검증해야 하는 술어는 반드시 `hub_model.py` 에 둔다
   (직전 PRP 전제 5 승계).
4. **`hub_model.py` 는 시각·파일시스템·환경변수에 닿지 않는다**(모듈 docstring 3~4행,
   T25-10 이 기계적으로 강제). `now_ms` 는 **항상 인자로 받는다.**
5. **직전 PRP 의 결정 RV1~RV3 · GN1~GN7 을 뒤집지 않는다.** 이 문서는 그 문서의 비목표 B1 과
   엣지 X6 을 **해소**하는 방향으로만 작용한다(결정 ZG6).

### 비목표 (이번 범위 밖 — 명시적으로 건드리지 않는다)

| # | 비목표 | 이유 | 재방문 트리거 |
|---|--------|------|---------------|
| **B1** | **`SubagentStop` 미발화 자체의 근본 수정** | 원인은 허브 밖이다 — 서브에이전트가 API 오류로 죽을 때 CLI 가 훅을 발화하지 않는다. 허브는 이벤트의 소비자이며, 발화를 보장할 수단이 없다. 이 문서는 **표시 가드**이지 원인 수정이 아니다(정직하게 명시) | CLI 가 실패한 서브에이전트에 `SubagentStop(reason=error)` 를 주기 시작하면 가드를 완화할 수 있다 |
| **B2** | **필터되는 이벤트의 `last_event_at_ms` 갱신 교정**(E10) | ① 그 동작은 **의도된 설계**다 — `hub-dashboard.md` 「상태 판정 규칙 1」이 명문화했다: *"두 술어가 참이면 `last_event_at_ms`·`last_event_name` 은 갱신하되 서브에이전트를 만들지 않고 `task_excerpt` 도 건드리지 않는다 … '세션이 아직 살아 있다'(stale 판정의 근거)와 '사용자에게 보여줄 서술'을 분리하는 것이다."* compact 는 CLI 가 살아 있다는 강한 증거다 ② 실측 E9 로 브리핑의 전제를 **교정했다** — stale 오버레이는 sticky working 을 *부분적으로 구제한다*(15:19~16:13 실측). 즉 이 갱신은 sticky working 의 **원인이 아니라 지연 요인**이다 ③ 이 가드가 들어가면 stale 에 의존할 필요 자체가 없어진다(가드가 `base_state` 를 직접 고친다) ④ 손대면 `_last_activity_at_ms` → 카드 정렬, 경과 시간 표시까지 파급된다 | compact 직후 경과 시간이 리셋되는 것("방금 활동")이 실제 오해를 낳았다고 보고될 때. 그때는 **표시용 `last_activity_at_ms`** 와 **stale 판정용 시계**를 분리하는 별도 설계로 다룬다 |
| **B3** | **좀비 전용 세 번째 칩 상태**(예: `중단?`) | 결정 ZG4 참조 — 허브가 정직하게 말할 수 있는 것은 "실행 중이라는 근거가 없다"까지다. "죽었다"는 관측이 아니다 | 사용자가 "종료로 보이는데 실제로는 죽은 것"을 구분해야 한다고 요청할 때 |
| **B4** | **`needs_input`·`crashed` 등 새 세션 상태** | `hub-dashboard.md` 「상태 판정 규칙 2」의 "영원히 켜지지 않는 등불" 논거를 승계한다 | — |
| **B5** | **이벤트 보관 창(오늘+어제) 확대** | 직전 PRP 비목표 B4 승계. 엣지 X5 로 영향만 기록한다 | — |

---

## 영향 범위

### 수정 파일 (5개) — 템플릿은 목록에 없다

| 파일 | 변경 | 요구 |
|------|------|------|
| `hub/bin/hub_model.py` | ① `SUBAGENT_ZOMBIE_AFTER_MS` 상수 신설(「3. 세션 표시 상태」 절 머리, 377행 부근) ② `is_running_subagent()` 순수 술어 신설(결정 ZG1) ③ `_compute_base_state(facts, now_ms, zombie_after_ms)` 시그니처 + 386행 판정 교체 ④ `compute_session_view` 에 `zombie_after_ms` 기본 인자 추가 + 두 하위 호출에 전달 ⑤ `summarize_agent_runs(facts, now_ms, zombie_after_ms=…)` 시그니처 + 425~427행 판정 교체 ⑥ `SubagentRunView.is_running` 주석 재서술 | R1·R2 |
| `tests/hub/test_hub_model.py` | ① `SubagentZombieGuardTest`(ZG1~ZG14) 신설 ② 기존 `summarize_agent_runs(facts)` 호출 **8곳**에 `now_ms` 추가(A1~A11, 119·133·139·145·152·160·231·245행) | R1·R2 |
| `tests/run.sh` | `test_hub_docs_and_constants()` 에 **T25-91 ~ T25-94** 4건 추가(현재 최대 `T25-90`) + 2349행 설명 문자열의 범위 표기 `T25-1~T25-90` → `T25-1~T25-94` | 전부 |
| `hub/README.md` | ① 「화면 배치」 157행("실행 중인 서브에이전트 칩은 글리프(●)와 강조색으로…") 뒤에 좀비 가드 1~2줄 ② 「알려진 한계」(217행)에 **B1**(훅 미발화는 허브 밖 원인) 항목 1개 | R1·R2 |
| `docs/prps/hub-dashboard.md` | 「상태 판정 규칙 2」(296~316행)에 **개정 화살표**로 좀비 가드를 덧붙인다 — **원문 코드블록 삭제 금지**(이 저장소의 개정 관례, T25-94 가 기계적으로 강제) | R1 |
| `docs/prps/hub-session-revival-and-stale-tier1.md` | 비목표 **B1** 행과 엣지 **X6** 행에 이 문서로의 개정 화살표 1줄씩(원문 유지) | 정합 |

### 미영향 — 건드리지 않는 이유 (직접 확인함)

| 대상 | 근거 |
|------|------|
| **`hub/bin/hub_template.html`** | 칩은 서버가 준 `run.is_running` 만 읽는다(`renderAgentChip`, 711~720행). 술어가 서버에서 고쳐지면 표시는 저절로 맞는다 — **템플릿 변경 0줄**(G7). 부수 효과: T25-89 의 "패널 IIFE 에 `snapshot` 0건" 검사가 구조적으로 안전하다 |
| `hub/bin/hub_collect.py` | 필요한 입력(`now_ms`)이 이미 `compose_project_views` 로 흐른다(377~379행). `zombie_after_ms` 는 기본값을 쓰므로 호출부 수정이 없다(결정 ZG3) |
| `hub/bin/hub_parse.py`·`hub_usage.py`·`hub.py`·`hub_server.py`·`hub_daemon.py`·`hub_statusline.py` | 세션 서브에이전트 판정을 참조하지 않는다 |
| `HubConfig` | 새 설정 키를 만들지 않는다(결정 ZG3, YAGNI 보류 1) |
| 데이터 계약(`#dzh-data` JSON) | **새 필드 0개.** `agent_runs[].is_running` 의 *값* 만 정확해진다 |
| `commands/dashboard.md`·`.claude/dashboard.html` | 허브는 읽기 전용 소비자다 |

---

## 결정 기록

### 결정 ZG1 — 좀비 판정은 **개별 실행의 나이** 하나로 한다 (순수 술어, 긍정형)

```python
# hub_model.py — 「3. 세션 표시 상태」 절 머리에 상수, 그 뒤에 술어
# 서브에이전트가 API 오류 등으로 죽으면 SubagentStop 훅이 발화하지 않는다(실측 E1·E5 — 3일간
# 고아 18건). 그 좀비 1건이 세션을 영구히 working 으로 붙잡는 것을 막는 나이 상한이다.
# 90분의 근거: 3일간 완료된 정상 실행 90건의 최장이 47.3분(p90 18.4분)이며, 90분은 그 1.9배다
# (결정 ZG2 의 표). 상한을 넘긴 실행은 "죽었다"가 아니라 "지금 돌고 있다는 근거가 없다"로 본다.
SUBAGENT_ZOMBIE_AFTER_MS = 90 * 60 * 1000


def is_running_subagent(subagent: SubagentFact, now_ms: int, zombie_after_ms: int) -> bool:
    """지금 실제로 돌고 있다고 볼 수 있는 실행인가 — 이미 끝났거나 좀비면 False."""
    if subagent.ended_at_ms is not None:
        return False
    return (now_ms - subagent.started_at_ms) < zombie_after_ms
```

**긍정형(`is_running_subagent`)을 고른 이유:** 부정형(`is_zombie_subagent`)으로 쓰면 두 호출부가
모두 `sub.ended_at_ms is None and not is_zombie(...)` 라는 **이중 조건**을 각자 적어야 하고, 한
쪽에서 앞 조건을 빼먹는 순간 상태와 칩이 어긋난다(G4 가 막으려는 실패). 긍정형 하나면 호출부가
`is_running_subagent(sub, now_ms, zombie_after_ms)` 로 끝난다 — **"실행 중"의 정의가 모듈에 딱
한 곳만 존재한다.**

**기각한 판정 기준들**

| 기준 | 기각 사유(실측 근거) |
|------|----------------------|
| 세션의 마지막 이벤트 기준(`now - last_event_at_ms`) | **기각.** 정상 백그라운드 실행 중에는 세션 이벤트가 **0건**이다(E8 — 17:03~17:21 구간). 이 기준이면 정상 실행이 즉시 좀비가 된다 |
| 메인 턴 `Stop` 시 전부 종료 처리 | **기각(확정 전제 1).** `SubagentStop` 의 27%가 `Stop` 보다 뒤에 온다(E7) |
| `SessionEnd`·재부착 시점에 고아 종료 처리 | **기각.** ① 직전 PRP 결정 RV2 가 이미 기각했다(같은 `session_id` 에 두 프로세스가 붙으면 진행 중 glow 를 끈다 — 상한 없는 실패) ② 실측 E1 의 좀비는 `SessionEnd` **없이** 3시간을 버텼다 — 트리거가 오지 않으므로 애초에 이 사례를 못 고친다 |
| API 오류를 감지해 종료 처리 | **기각.** 이벤트 스키마에 실패 사유가 없다(확정 전제 2). 허브는 에이전트가 왜 사라졌는지 볼 수 없다 |
| 클라이언트(JS)에서 나이로 칩만 끄기 | **기각.** ① 칩은 꺼지는데 카드는 계속 glow → S4 가 금지하는 모순 ② 표 기반 테스트가 불가능하다(확정 전제 3) |
| 같은 타입의 더 최근 실행이 있으면 이전 것을 종료 처리 | **기각.** 같은 타입 2개 동시 실행이 정상이다(기존 단위 M8 이 그 사실을 잠그고 있다) |

### 결정 ZG2 — 타임아웃 **T = 90분** (`SUBAGENT_ZOMBIE_AFTER_MS`)

근거는 위 「진단의 근거」의 두 표다. 요약하면 **양방향 오탐의 비용이 비대칭**이다.

| 방향 | 실패 모습 | 상한 | 성격 |
|------|-----------|------|------|
| T 가 너무 **크다** | 좀비가 최대 T 동안 glow 를 붙잡는다 | **T(90분)** — 현행은 **무한** | 개선의 정도 문제 |
| T 가 너무 **작다** | 정말 오래 걸리는 정상 에이전트의 glow 가 **꺼진다** | 그 실행이 끝날 때까지 | **오늘 오전에 고친 버그와 같은 종류**(살아있는데 죽었다고 표시) |

작은 쪽 실패가 더 나쁘다 — 그래서 실측 최장(47.3분)에서 **넉넉히 위쪽**을 고른다. T=60분은
오탐 0건이지만 여유가 12.7분뿐이어서, 한 번 더 긴 구현 작업이 나오면 곧바로 깨진다. T=120분은
여유가 과도해 klago 사례(E4)의 16분 오류를 **한 건도 고치지 못한다**. 90분은 오탐 0건 · 여유
1.9배 · 두 실측 사례를 모두 고치는 유일한 지점이다.

부수적으로 90분은 `stale_after_minutes`(30분)의 정확히 3배다 — "소식 없음"이 세 번 지나갈
동안 끝나지 않은 백그라운드 실행이라는 읽기가 가능하다. 다만 이것은 **사후 설명이지 근거가
아니다**(근거는 실측 표 하나뿐이며, 두 값은 서로 결합돼 있지 않다).

### 결정 ZG3 — 임계값은 **모듈 상수 + 기본 인자**로 흘린다 (`HubConfig` 키를 만들지 않는다)

```python
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
    ...


def summarize_agent_runs(
    facts: SessionFacts, now_ms: int, zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS
) -> tuple[SubagentRunView, ...]:
```

**시그니처 변경 범위를 최소화한 방식과 그 근거**

| 함수 | 변경 | 비테스트 호출부 영향 |
|------|------|----------------------|
| `_compute_base_state` | 인자 2개 추가(기본값 없음 — private 이고 호출부가 1곳뿐이라 기본값이 이득이 없다) | 1곳(394행) |
| `compute_session_view` | `zombie_after_ms` **기본 인자** 1개 추가 | **0곳** — `compose_project_views`(570행)는 그대로 |
| `summarize_agent_runs` | `now_ms` **필수** + `zombie_after_ms` 기본 인자 | **0곳** — 396행은 `compute_session_view` 안이라 함께 수정된다 |

- `now_ms` 를 기본값으로 둘 수는 **없다** — 이 모듈은 시계에 닿지 않는다(확정 전제 4). 그래서
  `summarize_agent_runs` 는 필수 인자가 늘고, 기존 테스트 8곳이 `now_ms=facts.last_event_at_ms`
  를 넘기도록 바뀐다(기계적). 이 churn 은 **얻는 것이 있다**: 칩이 시각에 의존한다는 사실이
  모든 호출부에 드러난다.
- `zombie_after_ms` 는 시계가 아니라 **불변 정수 상수**이므로 기본값이 순수성을 해치지 않는다
  (선례: `SHORT_ID_LENGTH`·`PROJECT_STATE_PRIORITY`). 기본값이 있으면 `hub_collect.py` 와
  `compose_project_views` 를 건드리지 않아도 되고, 단위 테스트는 작은 값을 넘겨 경계를 검증할 수
  있다.
- **`HubConfig` 키를 만들지 않는 이유:** `stale_after_minutes` 라는 선례가 있어 유혹적이지만,
  아무도 요청하지 않은 조절 손잡이다(YAGNI). 키를 만들면 `HubConfig` 필드 + `_CONFIG_TYPES`
  등록 + `hub_collect` 배선 + README 설정 표 + 검증 테스트가 함께 늘어난다. 오탐이 실제로
  보고되면 그때 한 줄로 승격한다(YAGNI 보류 1).

### 결정 ZG4 — 좀비 칩은 **종료된 칩과 똑같이** 보인다 (제외하지 않고, 새 상태도 만들지 않는다)

| 안 | 화면 | 판정 |
|----|------|------|
| **(a) 종료로 표시(권고)** | `is_running=False` → 중립색, ● 없음, 툴팁 `검수 단계 · 종료` | **채택.** 코드 0줄(술어를 공유하는 것만으로 성립) · 템플릿 0줄 · 새 필드 0개. **상태 판정과 구조적으로 일치**한다 — 둘이 같은 술어를 쓰므로 어긋날 수 없다(G4) |
| (b) 칩에서 제외 | 그 타입이 사라진다 | **기각.** 기존 결정(단위 A1·A7, README 149~151행)이 *"세션이 이미 완료됐어도 무슨 서브에이전트가 돌았는지 남는다"* 를 명시적으로 보장한다. 좀비도 **실제로 돌았던 사실**이다 — 지우면 사용자는 검수를 시도한 흔적조차 못 본다. 게다가 `shouldRenderSession` 의 `hasVisibleChip` 이 바뀌어 세션 줄 자체가 사라질 수 있다 |
| (c) 세 번째 상태(`중단?`) | 새 글리프·색·라벨 | **기각(보류).** ① `SubagentRunView` 에 필드 1개 + CSS + 라벨 + 툴팁 문구 + grep 검사가 늘어난다 ② 무엇보다 **허브가 그렇게 말할 자격이 없다** — 관측된 사실은 "`SubagentStop` 을 못 봤고 90분이 지났다"까지이며, 그 에이전트가 죽었는지 훅만 유실됐는지 구분할 정보가 없다. 애매한 상태를 자신 있게 표시하는 것은 `needs_input` 을 만들지 않은 논거(B4)와 같은 실패다 |

**(a) 채택 시 파생 효과 — 전부 확인함**

| 지점 | 효과 |
|------|------|
| 타입 병합(`is_running_by_type`) | 같은 타입에 좀비 1 + 정상 실행 1 이면 **정상 쪽이 이겨** `is_running=True` 다(기존 결정 A2 의 "running wins" 유지). 좀비만이면 `False` |
| 정렬(결정 K2, `0 if is_running_by_type[agent_type] else 1`) | 좀비 타입이 "실행 중 그룹"에서 "종료 그룹"으로 내려가 최근 시작순에 편입된다. 전부 결정적이라 `snapshot_content_key` 안정성에 영향 없음 |
| 칩 상한 2개(결정 K1) | **개선이다** — 좀비가 실행 중 우선순위를 점유하지 않으므로 정말 돌고 있는 타입이 상한 안에 들어온다. 실측 예: klago 의 보이는 칩이 `workflow-subagent(●)` 대신 최근 `code-reviewer` 로 바뀐다 |
| `shouldRenderSession` | `hasVisibleChip` 은 `is_running` 을 보지 않으므로 **변화 없다** — 세션 줄이 사라지는 일은 없다 |
| `SubagentRunView.is_running` 의 뜻 | *"`SubagentStop` 을 못 봤다"* → *"지금 돌고 있다고 볼 수 있다"* 로 **의미가 바뀐다.** 필드 주석(118행)과 README 를 함께 고친다 |

### 결정 ZG5 — 판정 위치: `compute_session_view` **안에서 한 번**, 두 소비자에게 같은 값

`_compute_base_state` 는 `now_ms` 를 받지 않고 `compute_session_view` 는 이미 받는다. 걸러내는
자리의 후보는 셋이었다.

| 자리 | 판정 |
|------|------|
| **`compute_session_view` 가 `now_ms`·`zombie_after_ms` 를 두 하위 함수에 전달(채택)** | **채택.** 두 소비자가 같은 인자로 같은 술어를 호출하므로 일관성이 구조적으로 보장된다. 시그니처 변경 3개 · 비테스트 호출부 영향 0곳 |
| `SessionFacts` 를 좀비 제거한 사본으로 정규화한 뒤 넘긴다 | **기각.** ① `SessionFacts` 는 "사실"이고 좀비 여부는 "지금 시각 기준 해석"이다 — 사실 레이어에 시각을 섞으면 레이어 경계가 무너진다 ② 사본을 만들면 `agent_id` 별 원본 시각이 사라져 나중에 진단이 어렵다 |
| `build_session_facts` 단계에서 좀비를 종료 처리 | **기각.** 순수 접기 단계에 `now_ms` 를 주입해야 하고, 접기 결과가 조회 시각에 따라 달라진다. `is_untracked_internal_subagent_stop` 필터와 판정 순서 문제(직전 PRP GOTCHA 1)가 재발한다 |

### 결정 ZG6 — 티어 1 세대 판정 오염은 **부수적으로 해소된다** (GN 결정은 손대지 않는다)

`LIVE_SESSION_STATES = frozenset({"working"})` 이고, `_live_session_start_times_ms` 는 상태가
그 집합에 있는 세션의 `started_at_ms` 만 모은다. 좀비가 `working` 을 붙잡는 동안 그 세션은
**살아 있는 세션으로 오인되어** `is_tier1_from_previous_task` 의 입력에 섞였다(직전 PRP 엣지 X6,
위 실측 표에서 `live=1 → 0` 으로 확인).

가드는 이 집합에서 **원소를 빼기만 한다**(넣지 않는다). 그래서 GN1~GN7 의 술어·집합·경계를
한 글자도 고치지 않고 오염이 사라진다. 판정이 뒤집힐 수 있는 두 방향 모두 **교정**이다:

| 좀비 세션의 시작 시각 | 가드 전 | 가드 후 | 평가 |
|---|---|---|---|
| 대시보드 mtime **보다 이전** | `all()` 이 항상 거짓 → 라벨 **강제 off**(E6 형태의 오염) | 그 세션이 빠져 남은 `working` 세션만으로 판정 | **교정** — 죽은 세션이 라벨을 죽이지 않는다 |
| 대시보드 mtime **보다 이후** | 라벨 on 에 기여 | 살아 있는 세션이 0개면 `False`(라벨 off) | **교정** — 아무도 일하지 않는데 "이전 작업"이라 말하지 않는다 |

`LIVE_SESSION_STATES` 에 `stale`·`done` 을 넣지 않는다는 **결정 GN2 는 그대로 유지된다** —
T25-87 의 기계적 검사도 그대로 통과한다.

### 결정 ZG7 — 정본 문장 (`base_state` 규칙 재서술)

> **`working` = 메인 턴이 진행 중이거나(`turn_state == "running"`), 또는 `SubagentStop` 없이
> 시작 후 `SUBAGENT_ZOMBIE_AFTER_MS`(90분) 이내인 서브에이전트가 하나라도 있다.** 90분을 넘긴
> 미종료 실행은 **실행 근거에서 제외한다** — 죽었다고 단정하는 것이 아니라, 지금 돌고 있다는
> 근거로 인정하지 않는다는 뜻이다. 같은 술어가 서브에이전트 칩의 `is_running` 도 결정하므로,
> **상태와 칩은 어긋날 수 없다.**

이 문장이 3곳에 반영돼야 한다: `hub_model._compute_base_state` 위 주석 · `hub/README.md`
「화면 배치」 · `docs/prps/hub-dashboard.md` 「상태 판정 규칙 2」(개정 화살표, **원문 코드블록
삭제 금지**).

---

## 데이터 모델 (변경 요약)

```python
# 변경 없음: HookEvent · SessionFacts · SubagentFact · SessionView · ProjectView · HubSnapshot
#           Tier1Snapshot · LIVE_SESSION_STATES · PROJECT_STATE_PRIORITY
# 의미만 변경: SubagentRunView.is_running — "SubagentStop 미관측" → "지금 돌고 있다고 볼 수 있음"
#             (필드 타입·이름·JSON 키 모두 그대로)

# 신설 (hub_model.py, 전부 순수)
SUBAGENT_ZOMBIE_AFTER_MS: int = 90 * 60 * 1000
def is_running_subagent(subagent: SubagentFact, now_ms: int, zombie_after_ms: int) -> bool

# 시그니처 변경
def _compute_base_state(facts: SessionFacts, now_ms: int, zombie_after_ms: int) -> Literal[...]
def compute_session_view(facts, now_ms, stale_after_ms, zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS) -> SessionView
def summarize_agent_runs(facts, now_ms: int, zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS) -> tuple[SubagentRunView, ...]
```

`#dzh-data` JSON: **스키마 변경 0건.** `projects[].sessions[].agent_runs[].is_running` 과
`state`·`base_state` 의 *값* 만 정확해진다.

---

## GOTCHA (구현자가 틀리기 쉬운 함정)

| # | 함정 | 회피 |
|---|------|------|
| **1** | **상수 선언 위치** — `SUBAGENT_ZOMBIE_AFTER_MS` 를 함수들보다 **뒤**에 선언하면 기본 인자 평가 시점(`def` 실행 시)에 `NameError` 가 난다 | 「3. 세션 표시 상태」 절 머리(377행 부근), `_compute_base_state`(383행) **앞**에 선언한다. T25-91 이 줄 번호를 기계적으로 비교한다 |
| **2** | **`MILLISECONDS_PER_SECOND` 재사용 유혹** — 그 상수는 614행(서버 절)에 선언돼 **뒤에 있다**. 앞에서 쓰면 `NameError` | `90 * 60 * 1000` 을 그대로 쓴다. 상수를 앞으로 옮기는 것은 이번 요청 범위 밖이다(수술적 변경) |
| **3** | **`is_running_by_type` 이름 변경 금지** — T25-52 가 리터럴 `0 if is_running_by_type[agent_type] else 1` 을 grep 한다 | `summarize_agent_runs` 안에서 판정식만 `is_running_subagent(...)` 로 바꾸고 **딕셔너리 이름·정렬 키 문자열은 건드리지 않는다** |
| **4** | **한쪽만 고치기** — `_compute_base_state` 만 고치고 `summarize_agent_runs` 를 잊으면 "카드는 `대기` 인데 칩은 ●" 라는 정반대 모순이 생긴다(S4 위반) | 두 곳 모두 `is_running_subagent` 를 호출한다. 단위 ZG11 + T25-92(두 함수 본문 각각에 호출 1건 이상, 기계적)가 강제 |
| **5** | **경계 방향** — `<=` 로 쓰면 나이가 정확히 T 인 실행이 "실행 중"이 된다 | `(now_ms - started_at_ms) < zombie_after_ms` 가 실행 중이다. 즉 **나이 `>= T` 가 좀비**. 단위 ZG2·ZG3 이 양쪽을 잠근다 |
| **6** | **`ended_at_ms` 검사 누락** — 술어에서 조기 반환을 빼면 **이미 끝난 오래된 실행이 좀비로 재분류**되지 않고, 반대로 `now - start >= T` 인 *종료된* 실행이 `False` 로 나와야 하는데… 실제 위험은 순서를 뒤집어 나이를 먼저 보는 경우다 | `ended_at_ms is not None` → 즉시 `False` 를 **맨 앞에** 둔다. 단위 ZG1 이 잠근다 |
| **7** | **기존 테스트 8곳** — `summarize_agent_runs(facts)` 호출이 `TypeError` 로 깨진다 | A1~A11 의 8곳(119·133·139·145·152·160·231·245행)에 `now_ms=facts.last_event_at_ms` 를 넣는다. 그 값이면 기존 기대값이 모두 유지된다(나이 0 ≪ 90분) |
| **8** | **`compute_session_view` 호출부 16곳** | 기본 인자를 썼으므로 **수정 불필요**. 새 인자를 필수로 만들면 16곳이 깨진다 |
| **9** | **`tests/run.sh` 2349행 범위 문자열** | `T25-1~T25-90` → `T25-1~T25-94` 로 함께 고친다(선례: 직전 PRP 가 같은 줄을 갱신했다) |
| **10** | **정본 문서 원문 삭제** — `hub-dashboard.md` 규칙 2 의 코드블록을 새 규칙으로 **덮어쓰면** 이 저장소의 개정 관례(원문 보존 + 개정 화살표)를 깬다 | 코드블록은 그대로 두고 그 아래에 `> **개정 →(결정 ZG7, hub-zombie-subagent-guard.md)**: …` 를 덧붙인다. T25-94 가 원문 줄의 존재를 기계적으로 검사한다 |

---

## 엣지 케이스

| # | 상황 | 처리 |
|---|------|------|
| X1 | **진짜로 90분 넘게 돌아가는 정상 에이전트** | 90분째에 칩이 중립으로 바뀌고 glow 가 꺼진다(오탐). 실측 3일 90건에 사례 0건(E6). 완화: 그 에이전트가 끝나 `SubagentStop` 이 오면 `last_event_at_ms` 가 갱신되어 카드가 "방금 활동"으로 되살아난다 — 오탐의 상한은 그 실행이 끝날 때까지다. 재방문 트리거는 YAGNI 보류 1 |
| X2 | 좀비 1개 + 같은 타입 정상 실행 1개 | 타입 병합에서 정상 쪽이 이겨 `is_running=True`(기존 결정 A2 유지). 단위 ZG8 |
| X3 | `turn_state == "running"` + 좀비만 | `working` — 턴 자체가 근거다. 가드가 과잉 발동하지 않는다. 단위 ZG10 |
| X4 | `now_ms < started_at_ms`(시계 역행·파일 복사) | `음수 < T` → 실행 중으로 본다(**안전한 방향** — 없는 좀비를 만들지 않는다). 단위 ZG5 |
| X5 | 세션이 이벤트 창(오늘+어제)을 넘겨 산다 | 창 밖으로 밀린 `SubagentStart` 는 애초에 접히지 않으므로 좀비도 사라진다. 창 확대는 비목표 B5 |
| X6 | 좀비가 있는 세션에 `SessionEnd` 가 온다 | `done` 이 이긴다(사다리 1단계) — 가드와 무관. 칩은 `is_running=False` 로 남아 `shouldRenderSession` 이 그 줄을 계속 보여준다(결정 ZG4) |
| X7 | 좀비만 있는 세션이 30분 넘게 조용하다 | `idle` → `stale` 오버레이. 가드 이전에는 `working` → `stale` 이었다(`base_state` 만 달랐다) — 화면 라벨은 같지만 병기 문구가 `소식 없음 · 직전 대기` 로 정확해진다 |
| X8 | 한 세션에 좀비가 10건(klago 실측 E4) | 술어가 각 실행에 독립 적용된다. 전부 90분을 넘기면 그 타입 칩 하나가 중립이 된다 |
| X9 | 좀비가 90분 경계를 넘는 순간 | `snapshot_content_key` 가 바뀌어 `hub.html` 이 1회 재기록된다(내용이 실제로 바뀌었으므로 정상). 좀비당 **1회 전이**이며 매 틱 재기록이 아니다 |
| X10 | 좀비가 티어 1 세대 판정에 끼어 있었다 | 결정 ZG6 — 살아 있는 세션 집합에서 빠지며 두 방향 모두 교정이다. 단위 ZG13 |

---

## 테스트 계획

두 층 구조를 그대로 쓴다: **T24** = `python3 -m unittest discover -s tests/hub -t .`
(tests/run.sh 2325~2345행) · **T25** = 소스·문서 grep 회귀(`test_hub_docs_and_constants()`).
좀비 가드는 순수 로직이므로 **T24 가 1차 층**이고, 구조 불변식(단일 판정자·상수 위치·문서
정합)은 T25 로 잠근다.

### 1층 — 단위 테스트 (`tests/hub/test_hub_model.py` 에 클래스 1개 추가)

기존 관례를 그대로 쓴다: 모듈 상단 `_event()`·`_facts_from()` 헬퍼, `BASE_TIME_MS`,
`STALE_AFTER_MS`. 클래스 안에 `ZOMBIE_AFTER_MS = 90 * 60 * 1000` 와
`ONE_MINUTE_MS = 60 * 1000` 을 둔다(매직 넘버 금지).

**`SubagentZombieGuardTest` — 결정 ZG1~ZG6**

| # | 입력 | 기대 |
|---|------|------|
| ZG1 | `is_running_subagent(ended_at_ms 있는 실행, now, T)` | `False` — 종료 검사가 나이보다 먼저다(GOTCHA 6) |
| ZG2 | 미종료, 나이 `T − 1ms` | `True` |
| ZG3 | 미종료, 나이 정확히 `T` | `False` — 경계 = `>=` 가 좀비(GOTCHA 5) |
| ZG4 | 미종료, 나이 `T + 1시간` | `False` |
| ZG5 | 미종료, `now_ms < started_at_ms`(나이 음수) | `True`(X4 — 안전한 방향) |
| **ZG6** | **E1 실측 재현**: `SubagentStart(code-reviewer)` → `UserPromptSubmit` → `Stop`, `now = start + 3시간` | `state == "idle"`, `base_state == "idle"` — **현행 코드에서는 `working`(버그 재현, G1)** |
| ZG7 | 같은 열, `now = start + 89분` | `state == "working"` — 아직 좀비가 아니다(오탐 방어) |
| ZG8 | `SubagentStart(agt-1, implementer, t=0)` 미종료 + `SubagentStart(agt-2, implementer, t=T)`, `now = T` | `working`; 칩 1개 `is_running is True`(X2 — 타입 병합에서 살아 있는 쪽이 이긴다) |
| ZG9 | 좀비(`code-reviewer`, 나이 `T+1분`) + 종료된 `implementer`(최근 시작), `turn_state="ended"` | 두 칩 모두 `is_running is False`; 순서는 `["implementer", "code-reviewer"]`(좀비가 종료 그룹으로 내려가 최근 시작순, 결정 ZG4) |
| ZG10 | 좀비만 + `UserPromptSubmit` 이 마지막(턴 진행 중) | `working`(X3 — 과잉 발동 방어) |
| **ZG11** | 좀비만 있는 세션의 뷰 하나에서 **동시 단정** | `view.state != "working"` **그리고** `all(not run.is_running for run in view.agent_runs)` — 상태와 칩의 모순 금지(G4·S4) |
| **ZG12** | **E6 실측 최장 재현**: 미종료 `implementer`, 나이 `47.3분`, `turn_state="ended"`, `T=기본값` | `working` — 실측 최장 정상 실행이 좀비로 오인되지 않는다(G2) |
| ZG13 | `compose_project_views`: 티어 1(mtime = `BASE_TIME_MS`) + 좀비만 있는 세션(시작 `BASE_TIME_MS + 1분`, 좀비 나이 `T+1분`, 턴 종료) | 프로젝트 `state != "working"`; `tier1_is_previous_task is False`(살아 있는 세션 0개 — 결정 ZG6, G5) |
| ZG14 | `render_hub_html` 왕복 후 JSON | `projects[0]["sessions"][0]["agent_runs"][0]["is_running"] is False`(선례: 기존 `test_a8`·`test_gn9`) |
| ZG15 | 기본 인자 확인 | `compute_session_view(facts, now, STALE_AFTER_MS)` 를 `zombie_after_ms` 없이 호출해도 `SUBAGENT_ZOMBIE_AFTER_MS` 가 적용된다(GOTCHA 8 회귀 — 기존 16곳 호출 형태가 유효함을 명시적으로 잠근다) |

**기존 테스트 수정(기대값 변화 없음, 기계적)**

| 대상 | 수정 |
|------|------|
| `SummarizeAgentRunsTest` A1~A11 중 8곳 | `hub_model.summarize_agent_runs(facts)` → `hub_model.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)`. 그 시점 나이는 0~수백 ms 라 전부 실행 중으로 유지된다 → **기대값 불변** |
| 그 외 (`compute_session_view` 16곳, `compose_project_views`, `SessionRevivalTest`, `Tier1GenerationTest`) | **수정 없음** — 기본 인자 덕분이며, 모든 픽스처의 서브에이전트 나이가 90분 미만이다 |

> 구현자 확인 절차: 먼저 **테스트만 추가/수정하고 실행**해 ZG6·ZG11·ZG12·ZG13 이 **실패**하는
> 것을 눈으로 본 뒤 구현한다(현재 버그 재현 → RED). ZG7·ZG8·ZG10 은 구현 전에도 통과해야 한다
> (회귀 방어선).

### 2층 — grep 회귀 (`tests/run.sh`, T25-91 ~ T25-94)

현재 최대 번호가 **T25-90** 이므로 **T25-91** 부터 쓴다. 정방향+역방향 쌍 관례를 따른다.

| # | 대상 | 정방향(있어야) | 역방향 / 기계적 검사 |
|---|------|----------------|----------------------|
| **T25-91** | ZG1·ZG2 상수·술어 계약 + 선언 순서(GOTCHA 1·2) | `hub_model.py` 에 `SUBAGENT_ZOMBIE_AFTER_MS = 90 * 60 * 1000` · `def is_running_subagent(` | **역방향(핵심)**: 옛 무조건 판정 `sub.ended_at_ms is None for sub in facts.subagents` 가 **0건**(G8 — 이 한 줄이 버그의 본체다). **기계적**: `SUBAGENT_ZOMBIE_AFTER_MS =` 선언 줄 번호 < `def is_running_subagent(` 줄 번호 < `def _compute_base_state(` 줄 번호 (선례: T25-87 의 필드 순서 비교) |
| **T25-92** | ZG5 **단일 판정자**(G4 — 가장 값진 검사) | — | **기계적**: `awk` 로 `def _compute_base_state(` ~ `def compute_session_view(` 범위와 `def summarize_agent_runs(` ~ 다음 `^def ` 범위를 각각 잘라, **두 범위 모두에서 `is_running_subagent(` 이 1건 이상**임을 확인한다. 어느 한쪽이 0이면 실패(GOTCHA 4). 역방향: `summarize_agent_runs` 범위 안에 `ended_at_ms is None` 직접 비교가 **0건** |
| **T25-93** | ZG3 시그니처 + 기존 계약 공존 | `def summarize_agent_runs(` 과 같은 줄 이후에 `now_ms: int` · `zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS` 가 `compute_session_view`·`summarize_agent_runs` 두 시그니처에 존재 | **역방향(회귀 방지)**: T25-52 가 요구하는 리터럴 `0 if is_running_by_type[agent_type] else 1` 이 **그대로 남아 있다**(GOTCHA 3 — 이름을 바꾸면 T25-52 와 함께 깨진다). `hub_template.html` 의 `run.is_running` 참조가 그대로 있다(템플릿 무변경 G7 의 최소 확인) |
| **T25-94** | 문서 정합(ZG7) | `hub/README.md` 에 `좀비` · `90분` ; `docs/prps/hub-dashboard.md` 에 `hub-zombie-subagent-guard` ; `docs/prps/hub-session-revival-and-stale-tier1.md` 에 `hub-zombie-subagent-guard` | **기계적(개정 관례 강제, GOTCHA 10)**: `hub-dashboard.md` 에 **원문 줄** `2. turn_state == "running" 또는 살아 있는 서브에이전트 존재` 가 **여전히 존재**한다 — 개정 화살표로 원문을 덮어쓰면 실패. 역방향: `hub/README.md` 에 옛 단정 `— CSS 가 숨긴다` 0건(T25-90 승계 확인) |

#### grep 토큰 실측 검증 (이 문서를 쓰면서 현재 소스에 직접 대조했다 — 구현자는 재확인 불필요)

직전 PRP 의 T25-90 이 볼드 마커 때문에 존재하지 않는 문자열을 검사하려다 실측으로 교정된
선례가 있다. 그래서 아래 4개 토큰을 **현재 파일에 실제로 실행해** 확인했다.

| 토큰 | 대상 | 실측 결과 |
|------|------|-----------|
| `sub.ended_at_ms is None for sub in facts.subagents` | `hub/bin/hub_model.py` | **386행에 1건** — 수정 후 0건이 되어야 한다(T25-91 역방향) |
| `2. turn_state == "running" 또는 살아 있는 서브에이전트 존재` | `docs/prps/hub-dashboard.md` | **304행에 1건** — 개정 후에도 남아 있어야 한다(T25-94 기계적). 볼드 마커 없는 코드블록 안이라 문자열이 그대로 성립한다 |
| `run.is_running` | `hub/bin/hub_template.html` | **4건**(706·712·713·715행) — 변경 후에도 4건이어야 한다(G7) |
| `0 if is_running_by_type[agent_type] else 1` | `hub/bin/hub_model.py` | **431행에 1건** — T25-52 가 이미 검사 중이며 유지되어야 한다(GOTCHA 3) |

T25-92 의 `awk` 범위 절단도 현재 파일에서 실행해 확인했다 — `def summarize_agent_runs(` ~ 다음
`^def ` 범위 안에 `ended_at_ms is None` 이 **현재 1건**(426행)이고, 그것이 교체 대상이다.

### 뮤테이션 검증 (구현 중 1회 — 검사가 **실제로 실패하는지** 확인 후 되돌린다)

| 검사 | 변형 | 기대 |
|------|------|------|
| ZG3 | 경계를 `<=` 로 바꾼다 | 실패 |
| ZG6 | `_compute_base_state` 의 가드를 지워 옛 판정으로 되돌린다 | 실패(현재 버그 재현) |
| ZG11 | `_compute_base_state` 만 고치고 `summarize_agent_runs` 는 옛 판정을 남긴다 | 실패(상태·칩 모순) |
| ZG12 | `SUBAGENT_ZOMBIE_AFTER_MS` 를 30분으로 낮춘다 | 실패 |
| ZG13 | 가드를 전부 제거한다 | 실패 |
| ZG15 | `zombie_after_ms` 를 필수 인자로 바꾼다 | 실패(`TypeError`) |
| T25-91 | 상수를 `_compute_base_state` 뒤로 옮긴다 | 실패(줄 번호 비교) — 그리고 모듈 임포트 자체가 `NameError` 로 죽는다 |
| T25-91 역방향 | 옛 `any(sub.ended_at_ms is None ...)` 줄을 되살린다 | 실패 |
| T25-92 | `summarize_agent_runs` 에서 `is_running_subagent` 호출을 직접 비교로 되돌린다 | 실패 |
| T25-93 | `is_running_by_type` 을 `running_by_type` 으로 개명한다 | 실패(T25-52 도 함께) |
| T25-94 | `hub-dashboard.md` 규칙 2 코드블록을 개정 내용으로 **대체**한다 | 실패 |

### 수동 확인 (브라우저·실환경)

| # | 절차 | 기대 |
|---|------|------|
| M1 | `bash tests/run.sh` 후 허브 새로고침 | coding-env 카드의 `code-reviewer` 칩(14:48 좀비)이 **중립색**으로 바뀌고 ● 이 사라진다 |
| M2 | klago 카드 확인 | `workflow-subagent` ● 이 중립으로 바뀌고, 보이는 칩 2개가 **최근 `code-reviewer` 우선**으로 재정렬된다(결정 ZG4 파생 효과) |
| M3 | 메인 턴이 끝난 직후(서브에이전트 없이) 카드 관찰 | glow 가 꺼지고 배지가 `대기` 다 — E3 의 6분 창이 재현되지 않는다 |
| M4 | **정상 구현 에이전트를 돌리는 중** 카드 관찰 | 실행 내내 `작업중` + glow 유지, 칩 ● 유지(S3 — 가드 과잉 발동 없음) |
| M5 | 좀비가 있는 프로젝트의 티어 1 줄 | 「이전 작업」 라벨 판정이 좀비 세션을 근거로 삼지 않는다(결정 ZG6) |
| M6 | 라이트·다크 두 테마 | 변화 없음(CSS 를 건드리지 않았다) |
| M7 | `동작 줄이기` 켠 상태 | 변화 없음 |

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| **P-1** | **T=90분이 너무 짧아 정상 장기 실행의 glow 를 끈다** — 오늘 오전에 고친 버그와 같은 종류 | 실측 3일 90건에 90분 초과 사례 **0건**, 최장 47.3분(1.9배 여유). 단위 ZG12 가 실측 최장을 잠근다. 후퇴 경로: 상수 한 줄 상향(호출부 영향 0) |
| P-2 | T=90분이 너무 길어 좀비가 최대 90분 glow 를 붙잡는다 | 현행은 **무한**이므로 순개선이다. 실측에서 실제 오류 창은 1~16분이었다(stale·턴이 나머지를 덮었다) |
| P-3 | **한쪽만 고쳐 상태·칩이 반대로 어긋난다** | 술어를 하나로 만든 것이 1차 방어(결정 ZG1 긍정형). 단위 ZG11 + T25-92 기계적 검사로 2·3중 잠금 |
| P-4 | `is_running` 이 시각 의존이 되어 `snapshot_content_key` 가 흔들린다 | 좀비당 **1회 전이**뿐이다(X9). 이미 `state`·`stale` 도 같은 성질이며 `collected_at_ms` 는 키에서 제외돼 있다(결정 D3) |
| P-5 | 기존 테스트 8곳 수정이 다른 기대값을 건드린다 | 넘기는 `now_ms` 가 `facts.last_event_at_ms` 라 나이 ≈ 0 → 전부 실행 중 유지. 전체 스위트로 확인 |
| P-6 | T25-52 가 이름 변경으로 깨진다 | GOTCHA 3 + T25-93 역방향 |
| P-7 | **근본 원인이 남는다**(훅 미발화) | 비목표 B1 로 정직하게 명시. 이 문서는 표시 가드다 — 좀비가 계속 생기지만 화면이 거짓말하지 않게 된다 |
| P-8 | 직전 PRP 의 GN 결정과 충돌 | 결정 ZG6 — 집합에서 **빼기만** 하므로 GN1~GN7 은 무변경이고 T25-87 도 그대로 통과한다. 단위 ZG13 이 확인 |

---

## YAGNI 보류 (지금 만들지 않는다 + 재방문 트리거)

| # | 보류 | 이유 | 재방문 트리거 |
|---|------|------|---------------|
| 1 | **`HubConfig.subagent_zombie_after_minutes` 설정 키** | 아무도 요청하지 않은 손잡이. 필드 + `_CONFIG_TYPES` + 배선 + README 표 + 테스트가 함께 늘어난다(결정 ZG3) | 정상 에이전트가 좀비로 오인됐다는 보고가 실제로 오면(X1) 그때 승격한다 |
| 2 | **좀비 전용 세 번째 칩 상태**(`중단?`) | 허브가 "죽었다"고 말할 근거가 없다(결정 ZG4 안 c). 비목표 B3 | "종료"와 "죽음"을 구분해야 한다는 요구가 나올 때 |
| 3 | **좀비 발생 건수 표시·경고** | 요구에 없다. 화면에 숫자를 더하는 비용 > 정보 가치 | 좀비가 급증해 원인 추적이 필요해질 때 |
| 4 | **`last_event_at_ms` 를 표시용/판정용으로 분리**(E10·비목표 B2) | 이 가드가 들어가면 stale 에 의존할 필요가 없어진다. 카드 정렬까지 파급된다 | compact 직후 "방금 활동"이 실제 오해를 낳았다고 보고될 때 |
| 5 | **좀비를 이벤트 로그에 별도 기록** | 진단 목적의 새 저장 경로는 이번 요구 밖이다 | 근본 원인(B1) 조사를 시작할 때 |

---

## 검토했으나 채택하지 않은 대안 (요약)

| 대안 | 기각 사유 |
|------|-----------|
| 메인 턴 `Stop` 시 실행 중 서브에이전트 전부 종료 처리 | `SubagentStop` 196건 중 52건(27%)이 `Stop` 뒤에 온다(E7). 정상 백그라운드 실행의 glow 를 매번 끈다. 직전 PRP 결정 RV2 도 같은 방향을 이미 기각했다 |
| 세션 마지막 이벤트 기준 타임아웃 | 정상 실행 중 세션 이벤트가 0건이다(E8) — 정상 실행이 즉시 좀비가 된다 |
| `SessionEnd`·재부착 시점에 고아 종료 처리 | 결정 RV2 가 기각한 방향이고, 실측 좀비는 `SessionEnd` 없이 3시간을 버텼다 — 트리거가 오지 않는다 |
| 클라이언트(JS)에서 칩 나이만으로 ● 끄기 | 카드 glow 와 어긋난다(S4 위반). 표 기반 테스트 불가(확정 전제 3) |
| 좀비를 칩에서 제외 | "완료돼도 무슨 에이전트가 돌았는지 남는다"는 기존 보장(단위 A1·A7)을 깬다. 세션 줄이 사라질 수 있다 |
| 세 번째 칩 상태 신설 | 관측이 뒷받침하지 않는 단정. `needs_input` 을 만들지 않은 논거와 같다 |
| `SessionFacts` 를 좀비 제거 사본으로 정규화 | 사실 레이어에 조회 시각을 섞는다(결정 ZG5) |
| `build_session_facts` 단계에서 종료 처리 | 접기 결과가 조회 시각에 의존하게 되고, 직전 PRP GOTCHA 1(필터 순서)이 재발한다 |
| 부정형 술어(`is_zombie_subagent`) | 호출부마다 이중 조건을 적어야 해서 한쪽 누락이 곧 모순이 된다(결정 ZG1) |
| `LIVE_SESSION_STATES` 를 손봐 티어1 오염만 막기 | 증상의 한 갈래만 가린다 — 카드 glow·칩은 그대로 거짓말한다. 결정 GN2 의 실측 근거도 무너진다 |

---

## 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | `test_hub_model.py` 에 `SubagentZombieGuardTest`(ZG1~ZG15) 추가 + 기존 8곳 호출 수정 | ZG6·ZG11·ZG12·ZG13 **실패**(RED, 버그 재현) · ZG7·ZG8·ZG10 통과 |
| 2 | `hub_model.py`: 상수 + `is_running_subagent` + 세 함수 시그니처·판정 교체 + 주석(결정 ZG7) | `python3 -m unittest discover -s tests/hub -t .` 전체 통과(GREEN) |
| 3 | `tests/run.sh` T25-91~94 추가 + 2349행 범위 문자열 갱신 | `bash tests/run.sh` 전체 초록 |
| 4 | 뮤테이션 11건 확인 후 되돌리기 | 각 항목이 기대대로 실패 |
| 5 | `hub/README.md` 2곳 + `hub-dashboard.md` 개정 화살표 + `hub-session-revival-and-stale-tier1.md` B1·X6 화살표 | T25-94 |
| 6 | 실환경 확인 | 수동 M1~M5 |

---

## 승인 요청 항목

> 각 항목에 **권고안**이 있다. "권고대로"라고 답하면 그대로 확정한다.

### 승인 항목 1 — 좀비 판정 기준: **개별 실행의 나이**, 긍정형 술어 하나 (결정 ZG1)
**권고: 그대로.** 세션 마지막 이벤트 기준은 정상 실행 중 이벤트가 0건이라 즉시 오작동하고(E8),
`Stop`·`SessionEnd` 트리거 방식은 실측 좀비를 아예 못 잡는다(E1 은 `SessionEnd` 가 없었다).

### 승인 항목 2 — 타임아웃 **T = 90분** (결정 ZG2)
**권고: 90분.** 실측 3일 90건 중 최장 47.3분(p90 18.4분)의 **1.9배**다. T≤45분은 실측 최장
실행을 죽이고(오탐 1건), T=60분은 여유가 12.7분뿐이며, T=120분은 klago 사례의 16분 오류를
**한 건도 고치지 못한다**. 트레이드오프: 90분 넘게 도는 정상 에이전트가 생기면 그 시점부터
glow 가 꺼진다(X1) — 오탐의 상한은 그 실행이 끝날 때까지이고, 상수 한 줄로 되돌릴 수 있다.
**더 보수적으로 가려면 120분**을 고를 수 있지만, 그러면 이번에 발견한 두 사례 중 하나만 고쳐진다.

### 승인 항목 3 — 칩 표시: **종료된 칩과 동일**(중립·● 없음) (결정 ZG4)
**권고: 안 (a).** 제외안은 "무슨 에이전트가 돌았는지 남는다"는 기존 보장을 깨고, 세 번째
상태(`중단?`)는 허브가 관측하지 못한 것을 단정한다. (a)는 **템플릿 0줄·새 필드 0개**이며,
상태와 칩이 같은 술어를 쓰므로 모순이 구조적으로 불가능하다.

### 승인 항목 4 — 임계값 전달: **모듈 상수 + 기본 인자** (`HubConfig` 키 없음) (결정 ZG3)
**권고: 그대로.** 설정 키를 만들면 `HubConfig`·`_CONFIG_TYPES`·`hub_collect`·README·테스트가
함께 늘어난다. 대가는 사용자가 값을 조절할 수 없다는 것 — 오탐 보고가 오면 한 줄로 승격한다
(YAGNI 보류 1). 대신 `summarize_agent_runs` 에 `now_ms` 가 **필수 인자로 추가**되어 기존 테스트
8곳이 기계적으로 수정된다(기대값 변화 없음).

### 승인 항목 5 — `last_event_at_ms` 의 필터 앞 갱신(E10): **이번 범위 밖** (비목표 B2)
**권고: 범위 밖.** 실측으로 브리핑의 전제를 교정했다 — `stale` 오버레이는 sticky working 을
**부분적으로 구제한다**(E9: 15:19~16:13 구간이 실제로 `stale` 이었다). 그 갱신은 원인이 아니라
지연 요인이고, `hub-dashboard.md` 「규칙 1」이 명문화한 **의도된 설계**이며(compact 는 CLI 가
살아 있다는 강한 증거), 손대면 카드 정렬·경과 시간까지 파급된다. 이 가드가 `base_state` 를
직접 고치므로 stale 에 의존할 필요 자체가 없어진다. 남는 증상("compact 직후 방금 활동으로
보인다")은 YAGNI 보류 4 에 재방문 트리거와 함께 기록했다.

### (참고) 부수 효과 확인 — 티어 1 「이전 작업」 라벨 판정이 **정확해진다** (결정 ZG6)
좀비가 `working` 을 붙잡는 동안 그 세션은 살아 있는 세션으로 오인돼 세대 판정에 섞였다(직전
PRP 엣지 X6, 실측 `live=1 → 0`). 가드는 그 집합에서 원소를 **빼기만** 하므로 결정 GN1~GN7 과
`LIVE_SESSION_STATES` 는 한 글자도 바뀌지 않는다. 라벨이 켜지거나 꺼지는 변화가 보일 수 있고,
**두 방향 모두 교정**이다.
