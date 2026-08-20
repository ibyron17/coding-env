# 허브 — 세션 부활 · 구세대 대시보드 플로팅 · 「이전 작업」 표시 (PRP)

> 요구 3건: **R1** 재개된 세션이 영구히 `완료` 로 굳어 작업중 glow 가 안 켜진다 ·
> **R2** 상세 패널 안 대시보드에 플로팅 버튼이 보인다 · **R3** 새 작업 중인데 카드·패널에
> **이전 작업**의 대시보드가 현재처럼 표시된다

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_model.py`(판정 본체) · `hub/bin/hub_template.html`(표시) + 테스트·문서 |
| 브랜치 | `main` (HEAD `8aafdb3`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md)(「상태 판정 규칙」 272~356행) → [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md) → [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md) → [`hub-detail-side-panel.md`](./hub-detail-side-panel.md)(패널 정본 · 불변식 H1⁗) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 상태 판정 규칙(정본 문서)과 스냅샷 데이터 계약(`ProjectView` 필드 1개)이 함께 바뀐다 |
| 규모 | **Small** — 신규 1개(이 문서) / 수정 6개 파일. Python 순증 약 **+30줄**, 템플릿 순증 약 **+25줄** |
| 새 외부 의존성 | **없음** (stdlib · 바닐라 CSS/JS). **새 색 리터럴 0개** — 기존 토큰 `--muted`·`--attention` 만 쓴다 |
| 결정 코드 | **RV**(Revival, R1) · **LG**(Legacy dashboard, R2) · **GN**(Generation, R3). 단일 문자 A~Z 와 `DG/MD/SP/TR/UT/ON/EX` 는 이미 소진됐고 위 3개는 미사용임을 확인했다(`grep -rhoE "결정 [A-Z]{1,3}[0-9]+" docs/prps/*.md`) |
| 승인 상태 | **승인됨(2026-08-14)** — 「승인 요청 항목」 1~5 전부 권고안대로 확정(카드 시안 A·문구 포함) |

### 진단의 근거 (이 문서를 쓰면서 직접 재검증한 것만 적는다)

| # | 관측 | 출처 |
|---|------|------|
| E1 | 세션 `8dd0eba0`(coding-env)은 `13:01:50 SessionEnd(reason=other)` → `13:07:11 SessionStart(source=resume)` → 이후 활동 **24건**인데도 `ended_at_ms` 가 남아 `done` 이다 | `~/.claude/hub/events/2026-08-14.jsonl` 실측 |
| E2 | 재개 `SessionStart` 의 `source` 는 `resume` 이다 — `is_internal_session_start`(hub_model.py 198~200행)가 거르는 값은 `compact` 뿐이므로 **재개 이벤트는 필터를 통과한다** | 같은 로그 + 소스 |
| E3 | `SessionStart` 는 허브가 항상 설치하는 훅이다(`HOOK_EVENTS`, hub_settings.py 31~37행) — 부활 트리거로 삼아도 "그 훅만 없는 설치"는 존재하지 않는다 | 소스 |
| E4 | klago 의 `.claude/dashboard.html`(8/13 11:47 생성)에 `dz-embedded` 가 **0건**이다. 현행 생성기(`commands/dashboard.md` 1344~1352행)에는 숨김 CSS 가 있다 → **구세대 생성물 문제이고 현행 코드는 정상** | `grep -c` 실측 |
| E5 | klago 의 현재 세션 `7443adc9` 는 `08-14 13:54` 시작, 대시보드 파일 mtime 은 `08-13 11:47` → **세션 시작이 파일 갱신보다 뒤**다 | `stat` + 이벤트 로그 |
| E6 | R1 을 고치면 klago 의 좀비 세션 `6d665dd7`(8/13 09:08 시작, 마지막 활동 8/14 13:25)이 `done` → `stale` 로 살아난다. 이 세션은 **대시보드 파일보다 먼저 시작**했다 → R3 판정 집합에 `stale` 을 넣으면 R3 가 **klago 에서 안 켜진다**(실측 `P_all_nondone=False`) | 프로브 실행 결과(아래 표) |
| E7 | `ended_at_ms` 를 읽는 곳은 `hub_model._compute_base_state` **하나뿐**이다(`grep -rn "ended_at_ms" hub/bin/*.py`) | 소스 |
| E8 | `ProjectView` 를 소비하는 파이썬은 템플릿 렌더 경로뿐이다 — `hub.py`·`hub_server.py`·`hub_daemon.py` 에 `tier1`·`ProjectView` 참조가 **0건** | 소스 |

**프로브 실측(부활 규칙 적용 후 세대 판정 술어 4안 비교, 2026-08-14 16:45 기준)**

| 프로젝트 | 대시보드 mtime | 살아 있는 세션(부활 후) | `P_working_all` | `P_maxstart_nondone` | `P_all_nondone` |
|---|---|---|---|---|---|
| coding-env | 08-14 16:39 | `8dd0eba0` working(시작 08-13 15:02) | **False** ✅ | False ✅ | False ✅ |
| klago-…-micro | 08-13 11:47 | `7443adc9` working(08-14 13:54) · `6d665dd7` stale(08-13 09:08) | **True** ✅ | True ✅ | **False** ❌ |
| OnefficeWiki | 08-10 12:52 | `d264075c` stale(08-13 09:08) | **False** ✅ | **True** ❌(휴면 프로젝트에 라벨) | True ❌ |

> ✅/❌ 는 "사용자가 기대하는 표시와 일치하는가". 이 표가 결정 GN2(판정 집합)의 유일한 근거다 —
> 세 후보 중 **모든 프로젝트에서 기대와 일치한 것은 `P_working_all` 계열뿐이다.**

---

## 요구사항 요약

허브 카드의 상태는 이벤트를 접어 만든 순수 판정이다. 그런데 Claude Code 는 앱 재시작·세션
재개 시 **같은 `session_id` 로 이벤트를 계속 낸다**. 현재 모델은 `SessionEnd` 를 터미널 상태로
보고 되돌리지 않으므로(hub_model.py 294~295행 · 363~365행), 재개된 세션은 **영구히 `완료`** 가 되어
지금 돌고 있는 작업의 glow 가 켜지지 않는다(R1). 또 티어 1 정보(대시보드 파싱)는 파일이 존재하는
한 카드·패널에 **무조건 현재 작업처럼** 표시되므로, 새 작업을 시작한 프로젝트에서 며칠 전 작업의
제목·진행률이 지금 것처럼 읽힌다(R3). 마지막으로 플로팅 숨김 기능(커밋 `1e3d65a`) 도입 **전**에
생성된 대시보드 파일에는 숨김 CSS 자체가 없어, 상세 패널 안에서 플로팅 버튼이 보인다(R2).

이 문서는 R1 을 **부활 규칙**으로, R3 를 **세대 판정 술어 + 표시**로 고치고, R2 는 대응 방식을
승인 항목으로 올린다(권고: 알려진 한계로 문서화).

### 사용자 스토리

| # | 스토리 |
|---|--------|
| S1 | 앱을 재시작하거나 세션을 재개한 뒤 작업을 계속하면, 카드가 다시 **작업중**으로 빛난다 |
| S2 | 며칠 전 작업의 대시보드가 남아 있는 프로젝트에서 새 세션이 돌면, 카드의 티어 1 줄이 **「이전 작업」** 으로 표시되고 톤이 낮아진다 |
| S3 | 그 프로젝트의 상세 패널을 열면 패널 머리 아래에 **한 줄 안내**가 붙어, iframe 안 내용이 지금 작업이 아닐 수 있음을 알려준다 |
| S4 | 그 프로젝트가 `/dashboard init`(또는 `step`·`log`)을 한 번 수행하면 라벨·안내가 **저절로 사라진다** |
| S5 | 진짜로 끝난 세션(재개하지 않은 세션)은 여전히 `완료` 로 남는다 — 부활이 과잉 발동하지 않는다 |

### 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G1 | `SessionEnd` 뒤 `SessionStart(source≠compact)` 가 오면 세션 상태가 `done` 이 아니다 | 단위 RV2·RV3 |
| G2 | `SessionEnd` 뒤 `SessionStart(source=compact)`·`Stop`·`SubagentStop` 은 부활을 **일으키지 않는다** | 단위 RV4~RV6 |
| G3 | E1 의 실측 시퀀스를 그대로 넣으면 `state == "working"` 이다(사용자 보고 재현) | 단위 RV9 |
| G4 | `is_tier1_from_previous_task` 가 int → bool 순수 함수이고 경계(`start == mtime`)가 명시적이다 | 단위 GN1~GN5 |
| G5 | `stale` 좀비 세션이 있어도 klago 형태(E5·E6)에서 판정이 `True` 다 | 단위 GN7 |
| G6 | 스냅샷 JSON(`#dzh-data`)에 `tier1_is_previous_task` 가 실린다 | 단위 GN9 |
| G7 | 카드 라벨·패널 안내가 **텍스트 채널**을 반드시 가진다(색만으로 말하지 않는다) | T25-88·T25-89 |
| G8 | 패널 IIFE 가 여전히 `snapshot` 을 모른다(결정 SP1 의 IIFE 분리 유지) | T25-89 역방향(기계적) |
| G9 | 새 색 리터럴이 0개다 | T25-88 역방향 |

---

## 확정된 전제 (재론하지 않는다)

1. **이벤트 스키마(`{t,e,s,c,so,r,ai,at,p}`)와 `hub_hook.py` 는 건드리지 않는다.** 기존 이벤트
   로그와의 호환이 깨진다. 이번 판정은 **이미 수집되는 이벤트만**으로 성립한다(E2·E3 확인).
2. **`/dashboard` 생성물(`commands/dashboard.md`·`.claude/dashboard.html`)은 건드리지 않는다.**
   허브는 그 파일의 **읽기 전용 소비자**다(T25-75 가 `data-owner-token` 참조를 금지로 못박았다).
3. **새 색 리터럴 금지.** `--muted`·`--attention`·`--accent-ink` 만 쓴다(선례: `.usage-pct-empty`·
   `.usage-stale-note`, hub_template.html 228~231행).
4. **불변식 H1⁗ 유지**(정본: `hub-detail-side-panel.md` 결정 SP6). 패널의 새 노드도 정적이며
   `hidden`·`textContent` 속성 단위로만 갱신한다.
5. **판정은 파이썬(순수 레이어), 표시는 템플릿.** 이 저장소에는 JS 테스트 러너가 없고
   grep 회귀만 있다 — 표 기반으로 검증해야 하는 술어는 반드시 `hub_model.py` 에 둔다.

### 비목표 (이번 범위 밖 — 명시적으로 건드리지 않는다)

| # | 비목표 | 이유 |
|---|--------|------|
| B1 | **고아 서브에이전트 정리** — `SubagentStart` 만 있고 `SubagentStop` 이 없는 실행 | 실측으로 흔함이 확인됐다(klago `7443adc9` 는 14:51 에 `workflow-subagent` 를 11건 시작했고 대응 `SubagentStop` 이 없다). 원인은 세션 부활이 아니라 백그라운드 에이전트의 훅 미발화이며, 별도 조사가 필요하다. 엣지 X6 에 남긴다 → **개정 →(`hub-zombie-subagent-guard.md`)**: 근본 원인(훅 미발화)은 여전히 범위 밖이지만, 그 흔적(90분 넘게 미종료인 실행)을 화면에서 가려주는 나이 기반 좀비 가드가 도입됐다 |
| B2 | `needs_input`·`crashed` 등 새 세션 상태 | `hub-dashboard.md` 「상태 판정 규칙 2」의 "영원히 켜지지 않는 등불" 논거를 승계한다 |
| B3 | 대시보드 세대(생성 시점 템플릿 버전) 자동 마이그레이션 | 허브가 다른 도구의 생성물을 고치는 일은 소유권 계약 위반이다(전제 2) |
| B4 | 이벤트 보관 창(오늘+어제, hub_collect.py 163~166행) 확대 | 엣지 X5 로 영향만 기록한다. 창을 넓히면 수집 비용·구세대 세션 소음이 함께 늘어난다 |

---

## 영향 범위

### 수정 파일 (6개)

| 파일 | 변경 | 요구 |
|------|------|------|
| `hub/bin/hub_model.py` | ① `_apply_tracked_event`(287~299행)에 `SessionStart` 분기 1개(결정 RV1) ② `LIVE_SESSION_STATES` 상수 + `is_tier1_from_previous_task()` 순수 함수 신설(결정 GN1·GN2) ③ `ProjectView`(128~140행)에 `tier1_is_previous_task: bool = False` 필드 ④ `compose_project_views`(508~541행)에서 그 필드를 채우는 3줄 ⑤ `_project_state_without_sessions`(467~476행) docstring 의 `done` 정의 보강 | R1·R3 |
| `hub/bin/hub_template.html` | ① `.tier1-prev-label`·`.card[data-tier1-previous]` 톤다운 CSS(162~164행 뒤) ② `.detail-note` CSS(300행 뒤) ③ 패널 마크업에 `<p id="dzh-detail-note">` 1줄(344~352행) ④ `renderTier1`(764~769행) 라벨 방출 ⑤ `renderProject`(799~801행) `data-tier1-previous` 속성 방출 ⑥ 패널 IIFE(1176~1182·1222~1236·1241~1249행)에서 안내 줄 표시/해제 ⑦ 머리 계약 주석(20~58행)에 새 노드 편입 | R3 |
| `tests/hub/test_hub_model.py` | 표 기반 단위 테스트 2세트 — `SessionRevivalTest`(RV1~RV9) · `Tier1GenerationTest`(GN1~GN9) | R1·R3 |
| `tests/run.sh` | `test_hub_docs_and_constants()`(2347행~)에 **T25-86 ~ T25-90** 5건 추가(현재 최대 번호 `T25-85`, 3665행) | 전부 |
| `hub/README.md` | ① 「화면 배치」(133행~)에 「이전 작업」 라벨 1줄 ② 「프로젝트 상세 패널」의 **199행**(“플로팅(PiP) 버튼·안내 줄이 보이지 않는다** — CSS 가 숨긴다.”) 단정을 구세대 예외 서술로 교정(결정 LG1) ③ 「알려진 한계」 절 신설 또는 같은 절에 편입 | R2·R3 |
| `docs/prps/hub-dashboard.md` | 「상태 판정 규칙 2」(295~315행)에 부활 규칙을 **개정 화살표로** 덧붙인다(원문 삭제 금지 — 이 저장소의 개정 관례). 규칙 4(344~356행)의 `done` 근거 문장에도 같은 화살표 | R1 |

### 미영향 — 건드리지 않는 이유 (직접 확인함)

| 대상 | 근거 |
|------|------|
| `hub/bin/hub_hook.py`·`hub_settings.py` | 수집 스키마·훅 목록이 그대로다(전제 1, E3) |
| `hub/bin/hub_collect.py` | 필요한 입력(`file_mtime_ms`·정렬된 이벤트)이 **이미** 있다. `read_recent_events` 가 `received_at_ms` 로 정렬해 주므로(191행) 접기 순서 전제가 성립한다 |
| `hub/bin/hub_parse.py` | 새 DOM 계약을 읽지 않는다(결정 LG1 채택 시). `Tier1Snapshot.file_mtime_ms`(45행)를 그대로 쓴다 |
| `hub/bin/hub.py`·`hub_server.py`·`hub_daemon.py` | `ProjectView` 필드를 참조하지 않는다(E8) |
| `commands/dashboard.md`·`.claude/dashboard.html` | 전제 2 |
| `hub_statusline.py` | 세션 상태를 읽지 않는다 |

---

## 결정 기록 — R1 부활 규칙

### 결정 RV1 — 부활 트리거는 **`SessionStart`(내부 필터 통과분)** 하나다

```python
# hub_model._apply_tracked_event 에 추가되는 분기
elif event.hook_event_name == "SessionStart":
    # 재부착(resume·startup·clear)은 "이 세션이 다시 살아났다"는 유일한 권위 있는 신호다.
    # compact 는 이 함수에 도달하지 못한다(build_session_facts 의 필터, 350~354행).
    session.ended_at_ms = None
```

| 안 | 내용 | 판정 |
|----|------|------|
| **(a) `SessionStart`(compact 제외)** | 재부착 이벤트만 부활 | **채택.** 의미가 정확하다("세션이 다시 열렸다"). 필터가 이미 존재해 compact 오발동이 구조적으로 불가능하다(E2). 훅이 항상 설치된다(E3). E1 에서 `SessionEnd`→`SessionStart` 사이 5분 21초 동안만 `done` 이고 그 뒤로는 정확하다 |
| (b) 모든 추적 이벤트 | 활동 증거면 무엇이든 부활 | **기각.** `SubagentStop` 은 `SessionEnd` 보다 **뒤에** 도착할 수 있다 — 실측에서 `SubagentStop` 직후 `SessionStart(compact)` 가 같은 초에 찍히는 패턴(klago `6d665dd7` 10:45:53, 14:29:47)이 확인됐다. 종료된 세션의 뒤늦은 꼬리 이벤트가 세션을 되살리면 `완료` 가 사실상 사라진다. `Stop` 도 부활 근거가 될 수 없다(턴이 끝났다는 뜻이다) |
| (c) `UserPromptSubmit` 만 | 사람의 입력만 부활 | **기각(부분 채택 불필요).** E1 에서 재부착(13:07:11)과 첫 프롬프트(13:11:23) 사이 **4분 12초**가 여전히 `done` 이다. 또 "재개했지만 아직 프롬프트를 안 넣은" 세션이 계속 `완료` 로 남아 사용자가 보는 화면과 어긋난다. (a) 가 이 창을 없애고, (a) 를 채택하면 (c) 를 더할 이득이 없다 |

**오판 시나리오 점검**

| # | 시나리오 | (a) 의 결과 | 평가 |
|---|----------|-------------|------|
| 1 | 진짜 종료(재개 없음) | `SessionStart` 가 오지 않는다 → `done` 유지 | 정상(S5) |
| 2 | `SessionEnd` 뒤 지연 도착한 `SubagentStop` | 부활 없음(RV5) | 정상 — (b) 기각의 근거 |
| 3 | 자동 compact 중 `SessionStart(compact)` | 필터가 `_apply_tracked_event` 진입 자체를 막는다 | 정상(RV4). **이 필터가 곧 안전판이다** |
| 4 | 이벤트 순서 역전 | `read_recent_events` 가 `received_at_ms` 로 정렬(hub_collect.py 191행) 후 접는다 | 구조적으로 발생하지 않음 |
| 5 | 같은 초에 `SessionEnd` 와 `SessionStart` 가 찍힘 | 파일 안 등장 순서대로 접힌다(`list.sort` 는 안정 정렬) → append 순서 = 실제 발생 순서 | 허용 |
| 6 | 턴이 running 인 채 세션이 죽고, 나중에 재개만 함 | `ended_at_ms` 만 지우므로 `turn_state="running"` 이 남아 최대 30분간 `working` 으로 보인다(그 뒤 `stale` 오버레이가 덮는다) | **허용 — 결정 RV2 참조** |

### 결정 RV2 — 부활은 **`ended_at_ms = None` 만** 한다 (턴·서브에이전트 상태는 손대지 않는다)

부활 시 함께 초기화할 수 있는 것이 두 개 더 있다: `turn_state = "ended"` 와 "고아
서브에이전트를 재부착 시각으로 종료 처리". 둘 다 **하지 않는다.**

| 안 | 실패 모드 | 상한 |
|----|-----------|------|
| **(최소, 채택)** `ended_at_ms` 만 해제 | 시나리오 6 — 죽기 전 턴이 running 이었으면 재부착 후 잠깐 `working` 으로 보인다 | **30분**(`stale` 오버레이가 덮는다. `stale` 카드는 glow 하지 않는다 — 템플릿 804행은 `state === 'working'` 일 때만 클래스를 방출한다) |
| (확장) `turn_state="ended"` + 고아 종료 | 같은 `session_id` 에 **두 프로세스가 붙는 경우**(`claude --resume` 을 다른 터미널에서 실행) 진행 중인 턴·서브에이전트가 강제로 꺼진다 → 실제로 돌고 있는데 glow 가 **사라진다** | 다음 `UserPromptSubmit` 까지 **무한** |

최소 안의 실패는 상한이 있고 최대 안의 실패는 상한이 없다. 게다가 이번 요구는 "glow 가 안
켜진다" 이므로, glow 를 끌 수 있는 변경은 요구와 반대 방향이다. **1줄로 끝나는 쪽을 고른다(YAGNI).**
고아 서브에이전트는 별도 문제이며 비목표 B1·엣지 X6 로 남긴다.

### 결정 RV3 — `done` 의 의미 재서술 (정본 문장)

> **`done` = `SessionEnd` 를 관측했고, 그 뒤로 재부착(`SessionStart`, compact 제외)을 보지
> 못했다.** `done` 은 여전히 `stale` 로 덮이지 않는 터미널 표시이지만, **터미널인 것은 표시일
> 뿐 사실이 아니다** — 세션은 되살아날 수 있고, 되살아나면 `done` 은 취소된다.

이 문장이 3곳에 반영돼야 한다: `hub_model._compute_base_state` 위 주석 · `_project_state_without_sessions`
docstring(467~476행, "SessionEnd 를 실제로 관측했을 때만" → "관측했고 그 뒤 재부착이 없을
때만") · `docs/prps/hub-dashboard.md` 「상태 판정 규칙 2」(개정 화살표).

세션이 0개인 프로젝트를 `done` 으로 판정하지 않는 기존 규칙(규칙 4)은 **그대로 유효하다** —
근거("`done` 은 관측된 사실이 있어야 한다")가 강화될 뿐이다.

---

## 결정 기록 — R2 구세대 대시보드의 플로팅 노출

### 결정 LG1 — **알려진 한계로 문서화**한다. 허브는 iframe 문서에 스타일을 주입하지 않는다

| 안 | 내용 | 판정 |
|----|------|------|
| **(a) 문서화 + 자연 치유** | `hub/README.md` 의 단정 문장을 교정하고, 구세대 파일은 다음 `/dashboard init` 에서 저절로 고쳐짐을 적는다 | **채택(권고).** ① 원인이 허브에 없다(E4) ② R3 의 「이전 작업」 표시가 **바로 이 화면들**(오래된 대시보드)을 이미 지목한다 — 두 증상이 같은 원인(구세대 파일)을 공유하므로 사용자는 두 번째 신호를 이미 받는다 ③ 코드 0줄 |
| (b) 허브가 same-origin iframe 에 숨김 스타일 주입 | `panelFrameEl.contentDocument` 에 `<style>` 삽입 | **기각.** 비용이 정직하게 크다 — ⓐ 허브가 "읽기 전용 소비자" 계약을 깬다(전제 2 · T25-75 가 지키려는 것) ⓑ `#dz-pip-btn`·`#dz-pip-hint`·`#dz-page-head`·`#dz-theme-toggle` 4개 셀렉터를 허브가 **복제 보관**하게 되어 `dz-embedded` 가 없애려던 중복이 되살아난다 ⓒ 주입 시점(load 이벤트) · 재주입(문서 교체) · `about:blank` 경합까지 관리해야 한다 ⓓ 구세대 파일을 고쳐 주면 사용자가 `init` 을 할 이유가 사라져 **구세대가 영구화**된다 |
| (c) 허브가 세대를 감지해 안내만 한다(읽기 전용) | `hub_parse` 가 `dz-embedded` 존재 여부를 필드로 올리고 패널에 "구세대 대시보드" 안내 | **기각(보류).** 주입보다는 정직하지만, `Tier1Snapshot` 에 필드 1개 + 표시 1개가 늘고 **자기 치유되는 문제**에 영구 코드를 남긴다. R3 안내 줄과 문구가 겹친다. YAGNI 보류 2 로 남기고 재방문 트리거를 붙인다 |

**잔여 리스크(정직하게):** 대시보드 파일보다 **먼저 시작한** 세션이 계속 살아 있는 구세대
프로젝트에서는 R3 라벨도 켜지지 않으므로 플로팅 노출이 아무 신호 없이 남는다. 이벤트 창이
2일이라 이 조합은 "이틀 넘게 이어지는 세션 + 그보다 오래된 구세대 대시보드"로 제한된다.

---

## 결정 기록 — R3 세대 불일치 표시

### 결정 GN1 — 판정 술어는 **int → bool 순수 함수**로 분리한다

```python
# hub_model.py
# 살아 있는 세션 = 지금 이 프로젝트에서 실제로 일하고 있는 세션(결정 GN2).
LIVE_SESSION_STATES: frozenset[SessionState] = frozenset({"working"})

def is_tier1_from_previous_task(
    tier1_file_mtime_ms: int, live_session_start_times_ms: Sequence[int]
) -> bool:
    """살아 있는 세션이 있고, 그 전부가 대시보드 파일이 갱신된 뒤에 시작됐는가."""
    if not live_session_start_times_ms:
        return False
    return all(start_ms > tier1_file_mtime_ms for start_ms in live_session_start_times_ms)
```

- **입력이 정수뿐이라 표 기반 테스트가 곧바로 성립한다**(전제 5). 세션 뷰·사실을 인자로 받으면
  테스트가 fixture 조립부터 시작해야 하고, 판정과 추출이 한 함수에 섞인다.
- 추출은 `compose_project_views` 안 3줄이다. `sessions`(`SessionFacts`, `started_at_ms` 보유)와
  `session_views`(상태 보유)는 같은 자리에서 같은 순서로 만들어지므로 `zip` 이 안전하다
  (hub_model.py 521~523행 — 뷰가 사실에서 1:1 로 생성된다).

```python
def _live_session_start_times_ms(
    sessions: tuple[SessionFacts, ...], session_views: tuple[SessionView, ...]
) -> tuple[int, ...]:
    """살아 있는 세션들의 시작 시각. 표시 상태는 뷰가, 시작 시각은 사실이 갖고 있다."""
    return tuple(
        facts.started_at_ms
        for facts, view in zip(sessions, session_views)
        if view.state in LIVE_SESSION_STATES
    )
```

- **경계는 엄격한 `>`** 다. `start_ms == mtime_ms` 면 `False`(= 이 세션이 갱신했다고 본다) —
  같은 밀리초에 세션이 시작되고 대시보드가 쓰였다면 후자가 전자의 결과일 개연성이 훨씬 높다.
- `all()` 은 **한 세션이라도 대시보드보다 먼저 시작했으면 라벨을 켜지 않는다**(오탐 회피 방향).

### 결정 GN2 — 판정 집합은 **`working` 세션**뿐이다 (`stale`·`idle`·`done` 제외)

> **개정(2026-08-20, hub-worktree-fold.md 결정 WT9)** — 판정 집합에 조건이 하나 더 붙는다:
> **티어 1 파일의 소유 디렉토리와 cwd 가 같은** working 세션. 워크트리 fold 이후 한 그룹의
> 세션이 여러 디렉토리에서 오기 때문이다. 비워크트리 프로젝트에서는 무동작이라 :266-290 의
> 판정 표 8행은 그대로 유효하다.

> **정밀화(2026-08-20, hub-worktree-fold.md 결정 WT18)** — 「티어 1 파일의 소유 디렉토리와
> cwd 가 같은 working 세션」에서 **cwd** 의 뜻이 「그 세션이 이 창에서 관측한 cwd 중 하나」로
> 정밀해졌다. `SessionFacts.cwd` 는 창 안 **최초 이벤트**의 cwd 라(E1) 워크트리로 이동한
> 세션에서는 그 값이 레포 루트로 남아 있어 일치하는 세션이 0 이 됐다(E15). 비워크트리
> 프로젝트에서는 여전히 완전한 무동작이라 :266-290 판정 표 8행은 그대로 유효하다.

실측 표(위 「진단의 근거」)가 이 결정의 유일한 근거다.

| 후보 집합 | klago(켜져야) | OnefficeWiki(꺼져야) | coding-env(꺼져야) |
|---|---|---|---|
| **`working` 전부(채택)** | ✅ True | ✅ False | ✅ False |
| 비-`done` 중 최근 시작 1개 | ✅ True | ❌ True(1일 넘게 조용한 휴면 프로젝트에 라벨) | ✅ False |
| 비-`done` 전부 | ❌ False(좀비 `stale` 세션이 라벨을 죽인다 — E6) | ❌ True | ✅ False |

- **`stale` 을 넣으면 R1 의 부활 규칙이 R3 를 깨뜨린다**(E6). 부활로 `done` → `stale` 이 된
  좀비 세션은 옛날에 시작했으므로 `all()` 을 항상 거짓으로 만든다. 두 요구가 한 문서에 있어서
  발견된 상호작용이다 — GOTCHA 3 에 기계적 강제를 걸어 둔다.
- **`idle` 은 넣지 않는다.** 넣으면 "붙어 있지만 조용한 세션"까지 라벨 대상이 되어 판정이
  넓어지고, `working` 만으로 이미 요구가 충족된다(YAGNI). 대신 라벨은 세션이 조용해지면
  사라진다 — 승인 항목 4 로 올린다.
- 라벨의 의미가 집합 선택으로 확정된다: **"지금 일하고 있는 세션들 중 어느 것도 이 대시보드를
  갱신한 적이 없다."**

### 결정 GN3 — 앵커는 `SessionFacts.started_at_ms` 다 (재부착 시각도, 마지막 프롬프트도 아니다)

| 앵커 후보 | 실측 기반 기각 사유 |
|---|---|
| **`started_at_ms`(채택)** | 세션 정체성의 시작. E5 에서 klago 를 정확히 켜고 coding-env 를 정확히 끈다 |
| 재부착 시각(`SessionStart` 최신) | **기각.** coding-env 세션 `8dd0eba0` 은 **작업 도중** 13:07 에 재부착했다(E1). 대시보드가 13:00 에 갱신됐다면 재부착 앵커는 "이전 작업"이라고 **거짓 신고**한다. CLI 재시작은 작업 경계가 아니다 |
| 마지막 `UserPromptSubmit` | **기각.** 정상 작업 중에도 프롬프트는 대시보드 갱신 사이사이에 계속 들어온다(coding-env 실측: 마지막 프롬프트 16:28 > 대시보드 갱신 16:20). 거의 항상 켜지는 라벨은 신호가 아니다. 새 필드도 필요하다 |

`started_at_ms` 는 "이벤트 창(오늘+어제) 안에서 처음 본 이벤트 시각"이므로 이틀 넘게 살아 있는
세션에서는 실제 시작보다 **늦게** 잡힌다(엣지 X5). 그 경우에도 오탐 조건은 "대시보드가 이틀 넘게
갱신되지 않았다"로 제한되므로 라벨의 주장("지금 세션이 이 대시보드를 갱신한 적 없다")은 대체로
참이다.

**경계 오판 표**

| # | 상황 | 시각 관계 | 판정 | 평가 |
|---|------|-----------|------|------|
| 1 | 새 세션 시작 → 30초 뒤 `/dashboard init` | start > mtime(옛 파일) | True(30초간) | **참이다.** 그 30초 동안 화면의 티어 1 은 실제로 이전 작업이다 |
| 2 | `/dashboard init` 직전 몇 초 | 같음 | True | 같음 — 그리고 `init` 이 mtime 을 올리는 순간 다음 수집에서 꺼진다 |
| 3 | 같은 세션이 `init` 없이 새 작업 시작 | start < mtime | **False(놓침)** | 허용(안전한 방향). 재방문 트리거: YAGNI 보류 1 |
| 4 | CLI 재시작(같은 `session_id`, resume) | start 불변 | 변화 없음 | 정상 — 앵커 선택의 근거(GN3) |
| 5 | CLI 재시작(새 `session_id`)으로 같은 작업 계속 | start > mtime | True(오판) | `step`·`log` 한 번이면 해소된다. 소유권 가드(`dashboard-ownership-guard.md`)가 이 상황에서 `init` 재실행을 유도하므로 창이 짧다 |
| 6 | 세션이 이벤트 창(2일)을 넘겨 잘림 | start 가 실제보다 늦다 | True 가능 | 대시보드가 2일 이상 방치된 경우에 한정 — 사실상 참 |
| 7 | 모든 세션이 `stale`/`done` | 살아 있는 세션 0개 | False | 의도(GN2). 상태 배지·경과 시간이 이미 "지금 것이 아니다"를 말한다 |
| 8 | 티어 1 없음 | — | False | `compose_project_views` 가 `tier1 is None` 이면 계산조차 하지 않는다 |

### 결정 GN4 — 스냅샷 데이터 계약: `ProjectView.tier1_is_previous_task: bool = False`

**`hub_model.py` 측**

```python
@dataclass(frozen=True)
class ProjectView:
    ...
    dashboard_key: str | None = None
    # 티어 1 파일이 "지금 일하는 세션보다 오래된" 세대인가(결정 GN1~GN3).
    # 이름에 stale 을 쓰지 않는다 — 세션의 stale(30분 무소식)·사용량의 is_stale(조회되지 않음)과
    # 뜻이 다르다.
    tier1_is_previous_task: bool = False
```

- **필드 순서 함정:** `dashboard_key` 가 기본값을 가진 마지막 필드다 → 새 필드는 반드시 **그 뒤**에
  와야 한다(그 앞에 넣으면 `TypeError: non-default argument follows default argument`).
- `snapshot_content_key`(688~692행)에 자동 포함되므로 값이 바뀔 때 `hub.html` 이 다시 쓰인다 —
  배포 직후 1회 추가 기록이 발생한다(정상).
- `SessionView` 에는 새 필드를 넣지 않는다. `started_at_ms` 를 뷰까지 올리면 세션마다 JSON 이
  커지는데 클라이언트는 그 값을 쓰지 않는다(YAGNI).

**`hub_template.html` 측**

| 소비 지점 | 사용 |
|---|---|
| `renderProject`(799~801행) | `if(project.tier1_is_previous_task) cardAttrs += ' data-tier1-previous="1"';` — **속성 하나가 CSS 스코프와 패널 인계를 겸한다**(선례: `data-dashboard-key` 가 `cursor:pointer` 스코프와 클릭 판정을 겸한다, 108~110행) |
| `renderTier1(tier1, isPreviousTask)`(764~769행) | 라벨 span 접두 |
| 패널 IIFE(1222~1236행) | 클릭된 카드의 속성을 읽어 안내 줄 표시 |

### 결정 GN5 — 카드 표시: **텍스트 라벨 + 톤 다운** (시안 A)

| 시안 | 형태 | 판정 |
|------|------|------|
| **A(권고)** | `.tier1-pct` 앞에 `<span class="tier1-prev-label">이전 작업</span>`(색 `--attention`) + `.card[data-tier1-previous]` 스코프로 티어 1 세 줄을 `--muted` 로 톤 다운 | **권고.** 색·굵기·텍스트 3채널이고, 라벨 텍스트가 색 없이도 성립한다(G7). CSS 3줄 + 속성 1개 + span 1개. 선례가 그대로 있다(`.usage-stale-note` = `--attention`, `.usage-pct-empty` = `--muted`) |
| B | 라벨만 붙이고 톤은 그대로 | 톤이 유지되면 `--accent-ink` 굵은 글씨의 시각 위계가 "지금 것"이라고 계속 말한다. 라벨 하나로 그 위계를 뒤집기 어렵다 |
| C | `.project-head` 에 네 번째 `.badge` 추가 | **기각.** `.project-head{flex-wrap:nowrap}`(125행)에 이미 배지 3개(티어·상태·경과)가 있다 — 좁은 카드에서 넘친다 |

```css
/* 이전 작업(결정 GN5) — 새 색 토큰을 만들지 않는다(.usage-stale-note 와 같은 관례). */
.tier1-prev-label{color:var(--attention);font-weight:800}
.tier1-prev-label::after{content:" · "}
.card[data-tier1-previous] .tier1-pct{color:var(--muted)}
.card[data-tier1-previous] .tier1-active{color:var(--muted)}
```

렌더 결과: `이전 작업 · {제목} — 4/4 · 100%` (기존 줄 구조·`.tier1-impl` 은 그대로).

### 결정 GN6 — 패널 표시: 머리 아래 **정적 안내 줄** 1개. 데이터는 **카드 속성**에서 받는다

```html
<!-- #dzh-detail-panel 안, .detail-head 와 iframe 사이 -->
<p id="dzh-detail-note" class="detail-note" hidden></p>
```

```css
.detail-note{margin:0;padding:0 16px 10px;font-size:11.5px;color:var(--attention)}
```

- 패널 IIFE 는 여전히 **스냅샷을 모른다**(결정 SP1 의 IIFE 분리 유지, G8). 클릭 핸들러가 이미
  카드 요소를 손에 들고 있으므로(1263~1267행) `card.getAttribute('data-tier1-previous')` 한 번으로
  끝난다 — 새 통신 채널을 만들지 않는다.
- `openDetailPanel(dashboardKey, displayName, openerElement, isPreviousTask)` 로 인자 하나만 늘린다.
  같은 카드 재클릭은 여전히 무동작(SP8)이고, 다른 카드로 교체할 때 안내 줄도 함께 바뀐다.
- `closeDetailPanel` 은 안내 줄을 **지우지 않는다** — 제목을 지우지 않는 것과 같은 이유다
  (닫히는 180ms 동안 내용이 사라지면 깜빡인다, GOTCHA 16 승계).
- 문구: `이전 작업의 대시보드입니다 — 지금 진행 중인 세션이 시작된 뒤 갱신되지 않았습니다.`
- **생명주기:** 열 때 1회 판정한다(승인 항목 5). 패널이 열려 있는 동안 그 프로젝트가
  `/dashboard` 를 쓰면 iframe 내용은 라이브로 바뀌지만 안내 줄은 남는다 → 엣지 X4.

### 결정 GN7 — 머리 계약 주석(H1⁗) 편입 문구

`hub_template.html` 20~58행의 정적 노드 목록에 `#dzh-detail-note` 를 더하고 한 문장을 넣는다:

> `#dzh-detail-note` 는 패널의 정적 자식이며 `hidden`·`textContent` 만 바뀐다. 그 값의 출처는
> 스냅샷이 아니라 **클릭된 카드의 `data-tier1-previous` 속성**이다 — 패널 IIFE 가 스냅샷을
> 모른다는 결정 SP1 을 유지하기 위한 우회다.

불변식 자체의 개정(H1⁗ → 다음 기호)은 **하지 않는다.** 조항이 바뀌는 것이 아니라 정적 노드
목록에 항목 하나가 추가될 뿐이다(정본 문서 `hub-detail-side-panel.md` 결정 SP6 은 그대로).

---

## 데이터 모델 (변경 요약)

```python
# 변경 없음: HookEvent · SessionFacts · SubagentFact · SessionView · Tier1Snapshot · HubSnapshot
# 변경: ProjectView 에 필드 1개 추가(결정 GN4)
ProjectView(..., dashboard_key: str | None = None, tier1_is_previous_task: bool = False)

# 신설 상수·함수 (hub_model.py, 전부 순수)
LIVE_SESSION_STATES: frozenset[SessionState]
def is_tier1_from_previous_task(tier1_file_mtime_ms: int, live_session_start_times_ms: Sequence[int]) -> bool
def _live_session_start_times_ms(sessions, session_views) -> tuple[int, ...]
```

`#dzh-data` JSON: `projects[].tier1_is_previous_task` (boolean) 1개 추가. 기존 필드 변경·삭제 없음.

---

## GOTCHA (구현자가 틀리기 쉬운 함정)

| # | 함정 | 회피 |
|---|------|------|
| 1 | `SessionStart` 분기를 `build_session_facts` 의 **필터보다 앞**에 두면 compact 가 부활 트리거가 된다 | 분기는 반드시 `_apply_tracked_event` 안에 둔다(필터는 350~354행에서 이미 걸러 `continue` 한다). T25-86 이 두 줄의 순서를 기계적으로 검사한다 |
| 2 | `ProjectView` 새 필드를 `dashboard_key` **앞**에 넣으면 즉시 `TypeError` | 기본값 있는 필드는 맨 뒤(결정 GN4) |
| 3 | `LIVE_SESSION_STATES` 에 `"stale"` 을 넣으면 R3 가 klago 에서 조용히 안 켜진다(E6) | T25-87 이 그 리터럴에 `stale`·`done` 이 없음을 검사한다. 단위 GN7 이 동작으로도 잡는다 |
| 4 | `zip(sessions, session_views)` 의 순서 전제 | `compose_project_views` 안에서 뷰를 만든 **직후** 같은 스코프에서 호출한다. 두 튜플을 함수 밖으로 넘겨 다시 조립하지 않는다 |
| 5 | `renderTier1` 시그니처를 바꾸면 호출부(814행)도 함께 바꿔야 한다 | 인자 추가는 1곳뿐임을 확인했다(`renderTier1(` 호출 1건) |
| 6 | 패널 안내 줄을 `render()` 쪽에서 갱신하려는 유혹 | `#dzh-app` 밖의 노드를 렌더 IIFE 가 만지면 H1⁗ 의 설계 의도(두 IIFE 독립)가 깨진다. T25-89 역방향이 패널 IIFE 범위에 `snapshot` 문자열이 0건임을 검사한다 |
| 7 | `hidden` 속성과 `display:flex` 의 충돌 | `.detail-note` 에 `display` 를 선언하지 않는다(선언하면 UA 의 `[hidden]{display:none}` 을 덮어써 항상 보인다) |
| 8 | 라벨을 색으로만 표현 | 텍스트 `이전 작업` 이 필수다(G7). `.tier1-prev-label::after` 의 구분자는 장식이며 의미를 담지 않는다 |

---

## 엣지 케이스

| # | 상황 | 처리 |
|---|------|------|
| X1 | `SessionStart` 만 있고 그 앞에 `SessionEnd` 가 없는 새 세션 | `ended_at_ms` 는 이미 `None` → 부활은 무해한 무동작(`_new_session_builder`, 302~313행) |
| X2 | `SessionEnd` → `SessionStart` → `SessionEnd` → `SessionStart` 반복 | 마지막 이벤트가 이긴다(멱등, 단위 RV8) |
| X3 | 티어 1 파일이 세션보다 **미래** mtime(시계 역행·파일 복사) | `start > mtime` 이 거짓 → 라벨 없음(안전한 방향) |
| X4 | 패널이 열린 채 그 프로젝트가 `/dashboard` 를 쓴다 | iframe 은 라이브로 바뀌고 안내 줄은 남는다. 카드 라벨은 다음 수집(≤5초) + 다음 렌더에서 사라진다 → 두 표면이 일시적으로 어긋난다(승인 항목 5) |
| X5 | 세션이 이벤트 창(오늘+어제)을 넘겨 산다 | `started_at_ms` 가 실제보다 늦다(경계 표 6). 창 확대는 비목표 B4 |
| X6 | 고아 서브에이전트로 `working` 이 영구 유지되는 세션 | 이번 범위 밖(B1). **부작용:** 그 세션이 살아 있는 동안 R3 라벨의 대상 집합에 계속 남는다 — 라벨 방향으로는 오탐이 아니다(그 세션이 대시보드를 갱신한 적 없다면 라벨은 참이다) → **개정 →(`hub-zombie-subagent-guard.md`)**: 좀비 가드가 90분 이후 그 세션을 살아 있는 세션 집합에서 뺀다 — 위 부작용(R3 라벨 대상 집합 오염)이 해소된다(결정 ZG6) |
| X7 | 티어 1 이 있는데 세션이 0개(대시보드만 남은 프로젝트) | 살아 있는 세션 0개 → 라벨 없음. `_project_state_without_sessions` 경로와 일관 |
| X8 | 구세대 대시보드 + 새 세션 | R3 라벨이 켜진다 → 사용자가 `init` 을 하면 R2 도 함께 해소된다(결정 LG1 의 논거 ②) |

---

## 테스트 계획

이 저장소에는 두 층이 있다: **T24** = `python3 -m unittest discover -s tests/hub`(tests/run.sh
2325~2345행) · **T25** = 소스·문서 문자열 grep 회귀(`test_hub_docs_and_constants()`, 2347행~).
**부활 규칙과 세대 판정은 순수 로직이므로 T24(표 기반 단위 테스트)가 1차 층이고**, 표시·문서·
구조 불변식은 T25 로 잠근다.

### 1층 — 단위 테스트 (`tests/hub/test_hub_model.py` 에 클래스 2개 추가)

기존 관례를 그대로 쓴다: 모듈 상단 `_event()`·`_facts_from()` 헬퍼(18~35행), `BASE_TIME_MS`,
`STALE_AFTER_MS`.

**`SessionRevivalTest` — 결정 RV1·RV2**

| # | 이벤트 열 | 기대 |
|---|-----------|------|
| RV1 | `UserPromptSubmit` → `SessionEnd` | `done`(회귀 방어 — 기존 M3 와 같은 사실) |
| RV2 | `SessionEnd` → `SessionStart(source="resume")` | `idle`, `facts.ended_at_ms is None` |
| RV3 | `SessionEnd` → `SessionStart("resume")` → `UserPromptSubmit` | `working` |
| RV4 | `SessionEnd` → `SessionStart(source="compact")` | **`done`**(필터가 부활을 막는다 — GOTCHA 1 의 동작 검증) |
| RV5 | `SubagentStart` → `SubagentStop` → `SessionEnd` → `SubagentStop`(같은 agent_id, 지연 도착) | `done` |
| RV6 | `SessionEnd` → `Stop` | `done` |
| RV7 | `SessionEnd` → `SessionStart("resume")`, `now = last_event + 31분` | `stale`, `base_state == "idle"` |
| RV8 | `SessionEnd` → `SessionStart("resume")` → `SessionEnd` → `SessionStart("resume")` | `idle`(멱등, X2) |
| RV9 | **E1 실측 축약**: `UserPromptSubmit` → `SessionEnd` → `SessionStart("resume")` → `UserPromptSubmit` → `SubagentStart(design-architect)` → `Stop` | `working` **+ `base_state == "working"`**(사용자 보고 재현, G3) |
| RV10 | `SessionStart(source="startup")` 단독 | `idle`(X1 — 부활이 무동작) |

**`Tier1GenerationTest` — 결정 GN1~GN4**

| # | 입력 | 기대 |
|---|------|------|
| GN1 | `is_tier1_from_previous_task(mtime, ())` | `False` |
| GN2 | `(mtime, (mtime + 1,))` | `True` |
| GN3 | `(mtime, (mtime - 1,))` | `False` |
| GN4 | `(mtime, (mtime - 1, mtime + 1))` | `False`(하나라도 앞서면 아니다) |
| GN5 | `(mtime, (mtime,))` | `False`(경계 = 엄격한 `>`) |
| GN6 | `compose_project_views`: 티어 1(mtime=T) + `working` 세션(시작 T+1분) | 뷰의 `tier1_is_previous_task is True` |
| GN7 | 같은 함수: `working`(시작 T+1분) + **`stale`**(시작 T−1시간, 마지막 이벤트 31분 전) | **`True`**(GN2 검증 — klago 실측 형태, G5) |
| GN8 | 티어 1 없음(티어 2 프로젝트) + `working` 세션 | `False` |
| GN9 | `render_hub_html` 왕복 후 JSON | `projects[0]["tier1_is_previous_task"] is True`(선례: 기존 `test_a8`, 176~198행) |
| GN10 | `idle` 세션만(시작 T+1분) | `False`(결정 GN2 — 승인 항목 4 가 뒤집히면 이 케이스가 `True` 로 바뀐다) |

### 2층 — grep 회귀 (`tests/run.sh`, T25-86 ~ T25-90)

현재 최대 번호가 **T25-85** 이므로 **T25-86** 부터 쓴다.

| # | 대상 | 정방향(있어야) | 역방향(없어야) / 기계적 검사 |
|---|------|----------------|------------------------------|
| **T25-86** | RV1 부활 규칙 + 순서(GOTCHA 1) | `hub_model.py` 에 `elif event.hook_event_name == "SessionStart":` · 같은 분기 아래 `session.ended_at_ms = None` | **기계적**: `is_filtered` 의 `continue` 줄 번호 < `_apply_tracked_event(session, event)` 호출 줄 번호(선례: T25-83 의 줄 번호 비교). 어느 쪽이 없으면 실패 |
| **T25-87** | GN1·GN2·GN4 파이썬 계약 | `def is_tier1_from_previous_task(` · `LIVE_SESSION_STATES` · `tier1_is_previous_task: bool = False` | `LIVE_SESSION_STATES` 선언 줄에 `stale`·`done` **0건**(GOTCHA 3). `dashboard_key` 필드 줄 번호 < `tier1_is_previous_task` 필드 줄 번호(GOTCHA 2) |
| **T25-88** | GN5 카드 표시 | `data-tier1-previous` · `tier1-prev-label` · `이전 작업` · `.card[data-tier1-previous] .tier1-pct{color:var(--muted)}` | 새 CSS 규칙(`.tier1-prev-label`·`.detail-note`)에 `#` 색 리터럴 **0건**(G9): `grep -E '\.(tier1-prev-label\|detail-note)\{[^}]*#[0-9a-fA-F]{3}'` |
| **T25-89** | GN6·GN7 패널 안내 + IIFE 분리 | `id="dzh-detail-note"` · `data-tier1-previous` 를 읽는 `getAttribute` · 머리 주석에 `#dzh-detail-note` | **기계적(가장 값진 검사)**: 패널 IIFE 범위(`var PANEL_OPEN_BODY_CLASS` 줄 ~ 파일 끝)에 `snapshot` 문자열 **0건**(G8). `panelFrameEl.src` 회귀 금지(T25-80 승계) |
| **T25-90** | 문서 정합(R2·R3) | `hub/README.md` 에 `이전 작업` · `구세대` · `/dashboard init` ; `docs/prps/hub-dashboard.md` 에 `재부착` | `hub/README.md` 에 옛 단정 문구 `— CSS 가 숨긴다` **0건**(결정 LG1 이 교정한다). **이 토큰은 실측으로 확정했다** — 199행 원문은 `…보이지 않는다** — CSS 가 숨긴다.` 로 볼드 마커가 사이에 있어 `보이지 않는다 — CSS…` 는 문자열로 존재하지 않는다 |

### 뮤테이션 검증 (구현 중 1회 — 검사가 **실제로 실패하는지** 확인 후 되돌린다)

| 검사 | 변형 | 기대 |
|------|------|------|
| RV4 | 부활 분기를 `build_session_facts` 의 필터 **앞**으로 옮긴다 | 실패 |
| RV9 | `session.ended_at_ms = None` 을 지운다 | 실패(현재 버그 재현) |
| GN5 | 경계를 `>=` 로 바꾼다 | 실패 |
| GN7 | `LIVE_SESSION_STATES` 에 `"stale"` 을 더한다 | 실패 |
| GN9 | `tier1_is_previous_task` 를 `ProjectView` 에서 뺀다 | 실패(+ `compose_project_views` 도 깨진다) |
| T25-86 | 분기를 `if event.hook_event_name == "SessionStart"` 로만 남기고 `ended_at_ms` 대입을 지운다 | 실패 |
| T25-87 | `LIVE_SESSION_STATES` 에 `"stale"` 을 더한다 | 실패 |
| T25-88 | `.tier1-prev-label{color:#B45309}` 로 하드코딩한다 | 실패 |
| T25-89 | 패널 IIFE 안에서 `snapshot.projects` 를 참조해 안내 줄을 만든다 | 실패 |
| T25-90 | README 의 옛 단정 문구를 되살린다 | 실패 |

### 수동 확인 (브라우저·실환경)

| # | 절차 | 기대 |
|---|------|------|
| M1 | coding-env 세션에서 `bash tests/run.sh` 후 허브 새로고침 | coding-env 카드가 **작업중**으로 빛난다(R1 해소, E1 재현) |
| M2 | klago 카드 확인 | 티어 1 줄이 `이전 작업 · AI HTML SVG 유실 …` 이고 톤이 낮다 |
| M3 | klago 카드 클릭 | 패널 머리 아래에 안내 한 줄. iframe 내용은 그대로 |
| M4 | klago 에서 `/dashboard init` 실행 후 5초 대기 | 카드 라벨이 사라진다. **플로팅 버튼도 사라진다**(R2 자연 치유, 결정 LG1 논거 ②) |
| M5 | 라이트·다크 두 테마 | 라벨·안내 줄이 두 테마에서 읽힌다(`--attention`·`--muted` 만 사용) |
| M6 | `동작 줄이기` 켠 상태 | 변화 없음(애니메이션을 추가하지 않는다) |
| M7 | 세션을 30분 이상 방치 | 카드가 `소식 없음` 으로 바뀌고 라벨이 사라진다(결정 GN2·승인 항목 4 의 실물 확인) |

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| P-1 | **부활이 `완료` 를 사실상 없앤다**(과잉 발동) | 트리거를 `SessionStart` 하나로 좁혔다(RV1). RV1·RV5·RV6 이 "부활하지 않아야 하는" 경우를 명시적으로 잠근다 |
| P-2 | 부활 후 죽기 전 턴이 running 이라 잠깐 헛 glow | 상한 30분(`stale` 오버레이). 결정 RV2 의 트레이드오프 표에 기록 |
| P-3 | **R1 수정이 R3 판정을 깨뜨린다**(좀비 세션이 `stale` 로 살아난다) | 실측으로 먼저 발견해 `LIVE_SESSION_STATES` 를 `working` 만으로 확정(GN2). GOTCHA 3 + T25-87 + 단위 GN7 로 3중 잠금 |
| P-4 | 「이전 작업」 라벨 오탐으로 사용자가 화면을 불신 | 오탐 방향을 `all()` + 엄격한 `>` + `working` 한정으로 최소화. 경계 표 8행 전수 검토. 후퇴 경로: `LIVE_SESSION_STATES = frozenset()` 한 줄로 기능 무효화 |
| P-5 | 패널 안내 줄이 열려 있는 동안 낡는다 | X4 로 기록. 승인 항목 5 에서 사용자가 라이브 동기화를 원하면 재설계(자기 주기 재조회) |
| P-6 | 구세대 대시보드 문제를 문서화만 해서 재발 보고 | R3 라벨이 같은 화면을 지목하고, M4 로 치유 경로를 확인한다. 재방문 트리거는 YAGNI 보류 2 |
| P-7 | 스냅샷 필드 추가로 `snapshot_content_key` 가 바뀌어 `hub.html` 1회 재기록 | 정상 동작이다(내용이 실제로 바뀌었다). 폴링은 전체 문자열 비교라 부작용 없음 |

---

## YAGNI 보류 (지금 만들지 않는다 + 재방문 트리거)

| # | 보류 | 이유 | 재방문 트리거 |
|---|------|------|---------------|
| 1 | **같은 세션 안의 작업 전환 감지**(경계 표 3) | 작업 경계를 알 수 있는 신호가 이벤트에 없다. `task_excerpt` 변화로 추정하면 프롬프트마다 라벨이 켜진다(GN3 에서 기각한 앵커와 같은 실패) | 한 세션에서 `init` 없이 새 작업을 하는 습관이 실제 오해를 낳았다고 보고될 때 |
| 2 | **구세대 대시보드 감지 필드**(결정 LG1 안 c) | 자기 치유되는 문제에 영구 코드를 남긴다 | R3 라벨로도 안 잡히는 구세대 노출이 재보고될 때(결정 LG1 「잔여 리스크」 조합) |
| 3 | **패널 안내 줄 라이브 동기화**(X4) | 두 IIFE 사이에 새 통신 경로(CustomEvent 또는 별도 폴링)가 필요하다. 안내 줄은 조언이며, 낡아도 화면의 다른 신호와 모순되기만 한다 | 승인 항목 5 에서 사용자가 원한다고 답할 때 |
| 4 | **부활 횟수·세션 수명 표시**("3번째 재개") | 요구에 없다. 화면에 숫자를 하나 더 얹는 비용이 정보 가치보다 크다 | — |
| 5 | **고아 서브에이전트 정리**(B1) | 원인 조사가 먼저다(훅 미발화인지, `agent_id` 불일치인지) | 카드가 영구히 glow 하는 프로젝트가 보고될 때 |

---

## 검토했으나 채택하지 않은 대안 (요약)

| 대안 | 기각 사유 |
|------|-----------|
| 부활을 "모든 추적 이벤트"로 | 종료 세션의 지연 `SubagentStop` 이 되살린다(RV1 안 b, 실측 패턴 확인) |
| 부활 시 `turn_state`·고아 서브에이전트까지 초기화 | 실패 상한이 없어진다(RV2) |
| 대시보드의 `data-owner-token` 으로 소유 세션을 직접 비교 | **T25-75 가 금지**한다(허브가 `/dashboard` 의 속성을 읽으면 두 도구가 재결합). 게다가 klago 의 구세대 파일에는 그 속성이 **0건**이라 이번 사례를 못 잡는다(직접 확인) |
| 판정 술어를 클라이언트(JS)에 두기 | 이 저장소에 JS 테스트 러너가 없다 — 표 기반 검증이 불가능해진다(전제 5) |
| 앵커를 재부착 시각 또는 마지막 프롬프트로 | 실측에서 각각 거짓 신고를 만든다(GN3) |
| 판정 집합을 "비-`done` 전부" 또는 "최근 시작 1개" | 실측 표에서 klago·OnefficeWiki 를 틀린다(GN2) |
| 허브가 iframe 에 숨김 CSS 주입 | 소유권 계약·셀렉터 복제·구세대 영구화(LG1 안 b) |
| `stale`/`is_stale` 이라는 이름 재사용 | 세션 `stale`(30분 무소식) · 사용량 `is_stale`(조회되지 않음)과 뜻이 달라 세 번째 의미가 겹친다(GN4) |

---

## 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | `hub_model.py` 부활 분기 1줄 + 주석 + `done` 정의 보강 | `SessionRevivalTest` RV1~RV10 통과 |
| 2 | `LIVE_SESSION_STATES`·`is_tier1_from_previous_task`·`_live_session_start_times_ms`·`ProjectView` 필드·`compose_project_views` 배선 | `Tier1GenerationTest` GN1~GN10 통과 |
| 3 | 템플릿 CSS·마크업·`renderTier1`·`renderProject`·패널 IIFE·머리 주석 | 브라우저 수동 M1~M3, M5 |
| 4 | `tests/run.sh` T25-86~90 추가 + 뮤테이션 10건 확인 후 되돌리기 | `bash tests/run.sh` 전체 초록 |
| 5 | `hub/README.md` 2곳 + `docs/prps/hub-dashboard.md` 개정 화살표 | T25-90 |

---

## 승인 요청 항목

> 각 항목에 **권고안**이 있다. "권고대로"라고 답하면 그대로 확정한다.

### 승인 항목 1 — 부활 트리거: **`SessionStart`(compact 제외)** 하나만 (결정 RV1)
**권고: 그대로.** `UserPromptSubmit` 을 함께 트리거로 삼는 안(c)은 (a)를 채택하면 얻는 것이
없고, "모든 추적 이벤트"(b)는 종료 세션의 지연 꼬리 이벤트로 `완료` 를 무너뜨린다.

### 승인 항목 2 — 부활은 `ended_at_ms` **해제만** (결정 RV2)
**권고: 그대로(최소).** 확장안은 같은 세션에 두 프로세스가 붙는 경우 **진행 중인 glow 를 끈다** —
상한 없는 실패다. 최소안의 실패(재부착 후 최대 30분 헛 glow)는 `stale` 오버레이가 상한을 준다.

### 승인 항목 3 — R2(구세대 플로팅): **알려진 한계로 문서화** (결정 LG1)
**권고: 안 (a).** 원인이 허브 밖에 있고(E4), R3 라벨이 같은 화면을 이미 지목하며, `init` 한 번으로
치유된다(M4). 주입안(b)은 소유권 계약 파기 + 셀렉터 4개 복제 + 구세대 영구화를 대가로 요구한다.

### 승인 항목 4 — 라벨 대상 세션 집합: **`working` 만** (결정 GN2)
**권고: `working` 만.** 실측 3개 프로젝트에서 유일하게 전부 기대와 일치했다. 대가는 **세션이
조용해지면(`idle`·`stale`) 라벨이 사라진다**는 것이다 — `idle` 을 포함하면 라벨이 더 오래 남지만
판정이 넓어진다. `idle` 포함을 원하면 상수 한 줄(`{"working", "idle"}`)과 단위 GN10 만 바뀐다.

### 승인 항목 5 — 패널 안내 줄: **열 때 1회 판정** (결정 GN6 · 엣지 X4)
**권고: 1회 판정.** 라이브 동기화는 두 IIFE 사이 새 통신 경로를 요구한다(YAGNI 보류 3).
낡은 안내가 실제로 방해가 된다고 판단되면 자기 주기 재조회로 올린다.

### (참고) 취향 확인 — 카드 시안은 **A(라벨 + 톤 다운)** 를 권고한다 (결정 GN5)
문구는 `이전 작업 · {제목} — 4/4 · 100%`, 패널 문구는
`이전 작업의 대시보드입니다 — 지금 진행 중인 세션이 시작된 뒤 갱신되지 않았습니다.` 다.
다른 문구를 원하면 이 두 문자열만 바뀐다(코드 구조 영향 없음).
