# 허브 — `hub_model.py`(799줄) 도메인 모듈 분리 (PRP)

> 요구 1건: `hub_model.py` 가 **파일 800줄 상한에 닿았고**, 서로 무관한 5개 도메인
> (세션 · 프로젝트 · 상주 서버 · 사용량 폴링 · 렌더)이 한 파일에 산다. 파일 안의
> 「---- N. …」 섹션 주석을 분리 경계 후보로 검토해 도메인 단위로 쪼갠다.

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_model.py`(799줄) 분해 → 신규 3개 + 기존 `hub_usage.py` 편입 |
| 브랜치 | `main` (HEAD `12d49d6`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) 「모듈 구성」(44·84·95행) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 새 모듈 3개 추가 + 공개 심볼의 소속(임포트 경로) 변경. 전형적인 「새 모듈/디렉토리 구조 변경」 |
| 규모 | **Medium(넓지만 얕다)** — **동작 변경 0줄.** 수정 14개 파일(소스 5 · 테스트 5 · `tests/run.sh` · `hub/install.sh` · `hub/README.md` · `hub-dashboard.md`) + 신규 6개(소스 3 · 테스트 3 · 이 문서) |
| **동작 변경** | **없음.** 순수 이동이다. 함수 본문·상수 값·시그니처가 한 글자도 바뀌지 않는다(결정 MS7 이 이를 기계적으로 검증한다) |
| 새 외부 의존성 | **없음** (stdlib 만) |
| 결정 코드 | **MS**(Module Split). 저장소 전체에서 미사용임을 확인했다 |
| 승인 상태 | **승인됨 · 구현·검수 완료**(승인 항목 1~5 전부 권고안대로 채택, 검수 PASS — Critical/Major/Minor 0건) |

---

## 요구사항 요약

`hub_model.py` 는 "이벤트 → 세션 사실 → 표시 상태로 접는 순수 로직"이라는 docstring(1~6행)으로
시작하지만, 실제로는 그 밖에 **네 가지 무관한 도메인**을 더 담고 있다 — 상주 서버 생존 판정과
`server.json` 파싱(649~721행), 사용량 API 폴링 백오프(724~776행), 스냅샷 직렬화와 HTML 렌더
(779~799행), 그리고 설정 기본값(`HubConfig`, 63~81행). 섹션 번호가 **9 다음에 8** 이 오는 것
(724행 → 786행)이 이 파일이 이미 관리 한계를 지났다는 가장 정직한 증거다.

799줄은 전역 지침의 **파일 800줄 상한**에 사실상 도달한 값이라, 다음 기능 하나면 반드시 넘는다.
이 문서는 파일 안에 이미 그어져 있는 경계선(섹션 주석)을 따라 **도메인 모듈로 분리**하되,
**동작은 한 줄도 바꾸지 않는다.**

### 사용자 스토리 (여기서 "사용자"는 다음에 이 코드를 고칠 사람이다)

| # | 스토리 |
|---|--------|
| S1 | 세션 상태 판정을 고치려는 사람이 **250줄짜리 파일 하나**만 열면 된다 — 서버 하트비트·렌더 코드를 스크롤로 지나치지 않는다 |
| S2 | 파일 이름만 보고 어디를 열지 안다(`hub_session` · `hub_project` · `hub_server_state`) |
| S3 | 순수 레이어 경계 검사(T25-10)가 **새 파일 3개에도** 자동으로 걸린다 |
| S4 | 테스트 파일이 소스와 1:1 로 대응한다(`hub_parse`↔`test_hub_parse` 관례가 전 모듈로 확장된다) |
| S5 | 이 리팩토링이 **아무 동작도 바꾸지 않았음**을 기계적으로 증명받는다 |

### 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G1 | `hub/bin/*.py` 중 **800줄을 넘는 파일이 0개**이고, 분리된 4개 파일 모두 400줄 이하다 | 검증 V1 |
| G2 | 이동 전후로 **모든 공개 함수·클래스·모듈 상수의 AST 가 동일**하다(주석 제외 코드 무변경) | 검증 **V2** — 가장 값진 게이트 |
| G3 | `python3 -m unittest discover -s tests/hub -t .` 의 **테스트 수가 362 로 같고** 전부 통과한다 | 검증 V3 |
| G4 | `bash tests/run.sh` 전 항목 통과 | 검증 V4 |
| G5 | 순환 임포트가 없다 — 의존 방향이 단방향 DAG 다 | 검증 V5 |
| G6 | `hub/install.sh` 의 `HUB_FILE_COUNT` 와 실제 파일 수가 일치한다(12 → 15) | T25-1(무수정, 값만 갱신) |
| G7 | 소스 어디에도 `hub_model.` 로 더 이상 존재하지 않는 심볼을 참조하는 곳이 없다 | 검증 V3·V4 + 검증 V6(정적 grep) |

---

## 확정된 전제 (재론하지 않는다)

1. **동작을 바꾸지 않는다.** 버그로 보이는 것을 발견해도 이 커밋에서 고치지 않는다 —
   **언급만 하고 그대로 옮긴다**(전역 지침 「수술적으로 변경한다」).
2. **순수성 계약은 유지된다.** 분리되는 모든 코드는 파일시스템·시각·환경변수에 닿지 않는다.
   새 파일들도 T25-10 의 검사 대상에 편입한다(결정 MS6).
3. **`hub_template.html` 은 건드리지 않는다.** 데이터 계약(`#dzh-data` 의 snake_case JSON)은
   `asdict(snapshot)` 이 만들고, `asdict` 는 dataclass 가 어느 모듈에 선언됐는지 묻지 않는다.
4. **`hub_parse.py`·`hub_usage_fetch.py`·`hub_settings.py`·`hub_statusline.py` 는 무영향이다.**
   전자 둘은 `hub_model` 을 임포트하지 않고, 후자 둘은 `hub_model.*` 참조가 0건이다(확인함).
5. **모든 소비자가 `import hub_model` + 속성 접근 형태다.** `from hub_model import X` 는
   저장소 전체에 0건이다(요구서 확인 + 재확인함). 모듈 안쪽끼리는 반대로 `from hub_parse import
   Tier1Snapshot`(14행) 형태를 쓴다 — 이 두 관례를 각각 그대로 유지한다(결정 MS3).

### 비목표 (이번 범위 밖 — 명시적으로 건드리지 않는다)

| 항목 | 이유 |
|------|------|
| 패키지화(`hub/bin/hub/` 디렉토리 + `__init__.py`) | 배포기(`hub/install.sh`)가 `hub/bin` **최상위 파일**을 세어 검증한다(`find -maxdepth 1 -type f`). 디렉토리 구조를 바꾸면 배포기·검사·`sys.path` 관례가 한꺼번에 열린다. 얻는 것은 이름공간 하나뿐이다 |
| 함수 쪼개기·이름 개선·타입 강화 | 전제 1. 리팩토링 두 종류(이동 / 수정)를 한 커밋에 섞으면 V2 게이트가 무의미해진다 |
| `MILLISECONDS_PER_SECOND` 중복 제거 | **이미 중복이다**(`hub_model.py:652` · `hub_usage.py:26`). 이 분리가 만드는 것이 아니고, 값 `1000` 하나를 위해 잎 모듈 사이에 의존을 만드는 것이 더 비싸다(결정 MS4) |
| 14개 PRP 문서의 `hub_model.py` 인용 갱신 | 역사 기록이다. 저장소 관례는 "원문을 지우지 않는다". 포인터는 **한 곳**에만 둔다(결정 MS10) |
| `hub_collect.py`(563줄) 등 다른 파일의 분리 | 상한에 닿지 않았다. 요구에도 없다 |

---

## 현재 구조 — 실측 (분리 경계의 근거)

`hub_model.py` 의 섹션과 그 도메인·의존을 전수 조사한 결과다.

| 파일 내 위치 | 섹션 주석 | 담긴 것 | 다른 섹션에 대한 의존 |
|--------------|-----------|---------|----------------------|
| 17~18 · 20 · 29~33 | (없음) | `SessionState`·`Phase`·`SHORT_ID_LENGTH`·`PHASE_BY_AGENT_TYPE` | — |
| 21~27 · 35~41 | (없음) | `DASHBOARD_KEY_LENGTH`·`PROJECT_DASHBOARD_RELATIVE_PATH`·`PROJECT_STATE_PRIORITY`·`LIVE_SESSION_STATES` | — |
| 43~44 | (없음) | `_DATA_MARKER_OPEN/CLOSE` | 렌더 전용 |
| 47~61 | `---- 입력 ----` | `HookEvent` | — |
| 63~81 | 〃 | `HubConfig` | — (설정 기본값) |
| 84~107 | `---- 사실(fact) ----` | `SubagentFact`·`SessionFacts` | — |
| 110~133 | `---- 표시(view) ----` | `SubagentRunView`·`SessionView` | — |
| 136~152 | 〃 | `ProjectView` | `Tier1Snapshot`·`SessionView` |
| 155~164 | 〃 | `HubSnapshot` | `ProjectView`·`UsageSample`·`RateLimitResets` |
| 167~206 | `---- 상주 서버 ----` / `---- 브라우저 열기 ----` | `ServerRecord`·`ServerStatus`·`BrowserOpenResult` | — |
| 209~223 | `---- 1. 내부 이벤트 필터 ----` | 술어 2개 | `HookEvent` |
| 226~252 | `---- 이벤트 파싱 ----` | `parse_event_line` | `HookEvent` |
| 255~377 | `---- 2. 세션 사실 접기 ----` | `_Mutable*` 2개 + 헬퍼 5개 + `build_session_facts` | 섹션 1 |
| 380~438 | `---- 3. 세션 표시 상태 ----` | `SUBAGENT_ZOMBIE_AFTER_MS`·`is_running_subagent`·`_compute_base_state`·`compute_session_view` | 섹션 4 |
| 441~481 | `---- 4. 서브에이전트 요약 ----` | `summarize_agent_runs` | 섹션 3 |
| 484~510 | `---- 5. 프로젝트 발견 ----` | `encode_project_dir_name`·`resolve_project_dirs`·`should_ignore_cwd` | — |
| 513~632 | `---- 6. 프로젝트 합성 ----` | 헬퍼 6개 + `project_dashboard_key`·`is_tier1_from_previous_task`·`compose_project_views` | 섹션 3·`Tier1Snapshot` |
| 635~646 | 〃 | `build_dashboard_registry` | `HubSnapshot`·섹션 6 |
| 649~721 | `---- 7. 상주 서버 ----` | 상수 3개 + `server_heartbeat_ttl_ms`·`is_server_alive`·`parse_server_record`·`should_spawn_collect` | **없음** |
| 724~776 | `---- 9. 사용량 API 폴링 스케줄 ----` | `UsageApiPollState` + 함수 3개 | **없음**(`MILLISECONDS_PER_SECOND` 만) |
| 779~783 | (섹션 밖) | `snapshot_content_key` | `HubSnapshot` |
| 786~799 | `---- 8. 렌더링 ----` | `render_hub_html` | `HubSnapshot`·`_DATA_MARKER_*` |

**핵심 관측 3가지:**

1. **섹션 3 ↔ 4 는 쪼갤 수 없다.** `compute_session_view` 가 `summarize_agent_runs` 를 부르고,
   둘 다 `is_running_subagent` 를 공유한다 — 이 공유가 "카드 상태와 칩이 어긋날 수 없다"는
   결정 ZG4 의 **구조적 장치**이고, T25-92 가 두 함수 본문 모두에 그 호출이 있는지 검사한다.
   나누면 그 검사가 파일 경계를 넘어 깨진다.
2. **섹션 7 과 9 는 다른 어떤 섹션에도 의존하지 않는다.** 가장 싸게 떼어낼 수 있는 두 덩어리다.
3. **의존 방향에 사이클이 없다.** 세션 → 프로젝트 → 스냅샷/렌더의 한 방향뿐이다.

---

## 결정 기록

### 결정 MS1 — 4개 도메인으로 나눈다 (신규 3 + 기존 `hub_usage.py` 편입 1)

| 새 파일 | 예상 줄 수 | 책임 (한 문장) | 받아 오는 구간 |
|---------|-----------|----------------|----------------|
| **`hub_session.py`** | ~350 | 훅 이벤트를 세션 사실로 접고, 그 사실을 화면 표시 상태로 판정한다 | 17~18 · 20 · 29~33 · 47~61 · 84~133 · 209~481 |
| **`hub_project.py`** | ~190 | 프로젝트를 발견하고, 세션 뷰·티어 1 스냅샷을 프로젝트 뷰로 합성한다 | 21~27 · 35~41 · 136~152 · 484~632 |
| **`hub_server_state.py`** | ~125 | 상주 서버의 기록 형식과 생존·재수집 판정 | 167~206 · 649~721 |
| `hub_usage.py`(기존 416 → ~470) | +55 | (기존) 한도 외부 계약 파서 **+ 사용량 API 폴링 스케줄** | 724~776 |
| `hub_model.py`(잔여) | ~85 | 허브 스냅샷 계약(`HubSnapshot`·`HubConfig`)과 그 직렬화·렌더 | 43~44 · 63~81 · 155~164 · 635~646 · 779~799 |

> **결정 MS1.** 섹션 1~4 는 **한 덩어리**(관측 1), 5~6 은 한 덩어리, 7 은 독립,
> 9 는 사용량 도메인으로 귀속, 8+스냅샷 계약은 `hub_model` 이름을 지킨다.
> **더 잘게 쪼개지 않는 이유**: 섹션 1~2(이벤트 파싱)를 따로 떼면 `HookEvent` 를 어디에 둘지가
> 곧바로 문제가 되고(파싱과 소비가 갈린다), 섹션 5(발견)를 따로 떼면 27줄짜리 모듈이 된다.
> 지금 필요 없는 경계를 미리 긋지 않는다(YAGNI).

**`hub_model.py` 를 85줄로 남기는 것이 낭비 아닌가?** 아니다. 이 파일이 지키는 것은
**허브의 대외 계약**이다 — `HubSnapshot` 은 `hub_template.html` 의 `#dzh-data` 와 맺은 계약이고,
`HubConfig` 는 `config.json` 과 맺은 계약이며, `render_hub_html` 은 그 계약을 HTML 에 새기는
유일한 지점이다. 계약이 한 파일에 모여 있는 것은 그 자체로 값이 있다(`hub_parse.py` 가 130줄인
것과 같은 종류의 값). 그리고 이 이름을 남기면 **`import hub_model` 을 쓰는 5개 소비자 중
4개가 그 줄을 그대로 유지한다.**

### 결정 MS2 — **파사드를 만들지 않는다.** 호출부를 함께 고친다

요구서가 지목한 핵심 트레이드오프다. 두 전략을 끝까지 계산했다.

| | **전략 A — `hub_model.py` 를 재노출 파사드로** | **전략 B — 실제 분리 + 호출부 갱신(권고)** |
|---|---|---|
| 파이썬 소스 변경 | 0개 | **5개**(`hub_hook`·`hub`·`hub_daemon`·`hub_server`·`hub_collect`) — import 줄과 속성 접두어뿐 |
| 파이썬 테스트 변경 | 0개 | 5개(접두어 치환 + `test_hub_model.py` 분할) |
| **`tests/run.sh` 변경** | **필요** — 28개 grep 이 `$hub_model_file` 을 본다. 파사드에는 `SUBAGENT_ZOMBIE_AFTER_MS`·`LIVE_SESSION_STATES`·`if is_filtered:` 같은 **토큰이 물리적으로 없다.** 게다가 T25-86·87·91·92 는 **한 파일 안에서의 줄 번호 순서·함수 본문 추출**을 검사하므로 파사드로는 애초에 만족시킬 수 없다 | **필요** — 같은 28곳 |
| 영구 비용 | 모든 심볼에 **도달 경로가 2개**가 된다. 새 코드가 어느 쪽을 쓸지 규약이 없어 드리프트가 시작된다. 되돌릴 계획 없는 중복 층이다 | 없음 |
| YAGNI 판정 | **소비자가 0인 추상화.** 저장소 밖에서 `hub_model` 을 임포트하는 코드가 없다(허브는 `~/.claude/hub/bin` 에만 설치되는 자족 도구다) | — |

> **결정 MS2 — 전략 B.**
> 파사드가 사려는 것은 "호출부를 안 고쳐도 된다"인데, **어차피 고쳐야 하는 가장 큰 덩어리
> (`tests/run.sh` 28곳 + 테스트 5개)는 전혀 사 주지 못한다.** 파사드가 실제로 아끼는 것은
> **소스 5개 파일의 import 줄과 속성 접두어**뿐이고, 그 대가로 "같은 것에 이름이 둘"이라는
> 영구 부채를 진다. 전역 지침의 "추측성 추상화 금지"와 "이름만 읽고 역할을 알 수 있어야 한다"에
> 정면으로 걸린다.
> **되돌리기 비용도 비대칭이다** — 전략 B 는 기계적 치환이라 문제가 생기면 `git revert` 한 번이고,
> 전략 A 는 한 번 만들면 지우는 데 다시 전략 B 를 해야 한다.

### 결정 MS3 — 임포트 관례: **소비자는 `import <모듈>`, 모듈끼리는 `from <모듈> import <이름>`**

저장소에 이미 두 관례가 공존하며 각각 이유가 있다.

| 층 | 관례 | 근거 |
|----|------|------|
| I/O 모듈 → 순수 모듈 (`hub_collect` → `hub_model`) | `import hub_model` + `hub_model.X` | 호출부에서 **어느 레이어의 함수인지가 눈에 보인다.** 저장소 전체가 이미 이 형태이며 예외 0건 |
| 순수 모듈 → 순수 모듈 (`hub_model` → `hub_parse`) | `from hub_parse import Tier1Snapshot` | 타입 주석에 쓰이므로 접두어가 붙으면 시그니처가 길어진다(14~15행이 이미 이 형태) |

새 모듈 사이의 의존도 **후자**를 따른다:

```python
# hub_project.py
from hub_parse import Tier1Snapshot
from hub_session import SessionFacts, SessionState, SessionView, compute_session_view

# hub_model.py (잔여)
from hub_project import PROJECT_DASHBOARD_RELATIVE_PATH, ProjectView, project_dashboard_key
from hub_usage import RateLimitResets, UsageSample
```

### 결정 MS4 — 의존 그래프 (단방향 DAG · 순환 없음)

```
                     hub_parse ──┐
                                 ├──> hub_project ──> hub_model
  hub_session ───────────────────┘                        │
                                 hub_usage ───────────────┘
  hub_server_state   (어느 것도 임포트하지 않는다 — 완전한 잎)
```

- **`hub_server_state.py` 는 잎이다** — `json`·`dataclasses` 만 임포트한다. 이것이 중요한 이유는
  `parse_server_record` 의 docstring(671~678행)이 남긴 이력 때문이다: 이 함수는 원래
  `hub_daemon.py` 와 `hub_collect.py` 에 **사본이 둘** 있었고, 그 이유가 "순환 임포트를 피하려는
  시도"였다. 잎 모듈에 두면 그 위험이 구조적으로 재발할 수 없다.
- `hub_usage.py` 도 잎을 유지한다(섹션 9 는 `MILLISECONDS_PER_SECOND` 외에 아무것도 안 쓴다).
- **`MILLISECONDS_PER_SECOND` 중복 허용**: `hub_server_state.py` 와 `hub_usage.py` 가 각자
  선언한다. **이 중복은 지금도 있다**(`hub_model.py:652` · `hub_usage.py:26`) — 분리가 만드는
  것이 아니다. 값 `1000` 을 공유하려고 두 잎 모듈 사이에 간선을 긋거나 `hub_constants.py` 를
  만드는 것은 얻는 것보다 비싸다.

### 결정 MS5 — 심볼 귀속표 (전수 — 구현자는 이 표만 보면 된다)

| 심볼 | 종류 | 현재 줄 | 새 소속 |
|------|------|---------|---------|
| `SessionState` · `Phase` | 타입 별칭 | 17~18 | `hub_session` |
| `SHORT_ID_LENGTH` | 상수 | 20 | `hub_session` |
| `PHASE_BY_AGENT_TYPE` | 상수 | 29~33 | `hub_session` |
| `HookEvent` | dataclass | 47~61 | `hub_session` |
| `SubagentFact` · `SessionFacts` | dataclass | 85~107 | `hub_session` |
| `SubagentRunView` · `SessionView` | dataclass | 111~133 | `hub_session` |
| `is_internal_session_start` · `is_untracked_internal_subagent_stop` | 함수 | 210~223 | `hub_session` |
| `parse_event_line` | 함수 | 227~252 | `hub_session` |
| `_MutableSubagent` · `_MutableSession` · `_handle_subagent_start` · `_handle_subagent_stop` · `_apply_tracked_event` · `_new_session_builder` · `_freeze_session` · `build_session_facts` | 비공개+함수 | 256~377 | `hub_session` |
| `SUBAGENT_ZOMBIE_AFTER_MS` · `is_running_subagent` · `_compute_base_state` · `compute_session_view` | 상수+함수 | 386~438 | `hub_session` |
| `summarize_agent_runs` | 함수 | 442~481 | `hub_session` |
| `DASHBOARD_KEY_LENGTH` | 상수 | 21 | `hub_project` |
| `PROJECT_DASHBOARD_RELATIVE_PATH` | 상수 | 22~27 | `hub_project` |
| `PROJECT_STATE_PRIORITY` · `LIVE_SESSION_STATES` | 상수 | 35~41 | `hub_project` |
| `ProjectView` | dataclass | 136~152 | `hub_project` |
| `encode_project_dir_name` · `resolve_project_dirs` · `should_ignore_cwd` | 함수 | 485~510 | `hub_project` |
| `_display_name` · `_project_tier` · `_project_state_without_sessions` · `_project_state` · `_last_activity_at_ms` · `project_dashboard_key` · `is_tier1_from_previous_task` · `_live_session_start_times_ms` · `compose_project_views` | 함수 | 514~632 | `hub_project` |
| `ServerRecord` · `ServerStatus` · `BrowserOpenResult` | dataclass | 168~206 | `hub_server_state` |
| `SERVER_HEARTBEAT_TTL_MULTIPLIER` · `SERVER_HEARTBEAT_MIN_TTL_SECONDS` · `MILLISECONDS_PER_SECOND` | 상수 | 650~652 | `hub_server_state` |
| `server_heartbeat_ttl_ms` · `is_server_alive` · `parse_server_record` · `should_spawn_collect` | 함수 | 655~721 | `hub_server_state` |
| `USAGE_API_BACKOFF_MAX_MULTIPLIER` · `USAGE_API_RATE_LIMITED_MULTIPLIER` · `UsageApiPollState` · `usage_api_poll_delay_ms` · `should_attempt_usage_api_poll` · `next_usage_api_poll_state` | 상수+함수 | 725~776 | **`hub_usage`**(기존 파일 말미) |
| `HubConfig` | dataclass | 63~81 | `hub_model`(잔류) |
| `HubSnapshot` | dataclass | 155~164 | `hub_model`(잔류) |
| `build_dashboard_registry` | 함수 | 635~646 | `hub_model`(잔류) |
| `snapshot_content_key` | 함수 | 779~783 | `hub_model`(잔류) |
| `_DATA_MARKER_OPEN` · `_DATA_MARKER_CLOSE` · `render_hub_html` | 상수+함수 | 43~44 · 787~799 | `hub_model`(잔류) |

### 결정 MS6 — 선언 **순서**를 파일 안에서 보존한다 (검사 4개가 순서를 본다)

`tests/run.sh` 는 단순 grep 이 아니라 **줄 번호 비교와 함수 본문 추출**을 쓴다. 이동 후에도
같은 파일 안에서 아래 순서가 유지돼야 한다.

| 검사 | 강제하는 순서 | 새 소속 |
|------|---------------|---------|
| T25-86 | `if is_filtered:` **<** `_apply_tracked_event(session, event)` | `hub_session` (한 함수 안이라 자동 보존) |
| T25-91 | `SUBAGENT_ZOMBIE_AFTER_MS` **<** `def is_running_subagent(` **<** `def _compute_base_state(` | `hub_session` |
| T25-92 | `_compute_base_state` 본문의 끝 경계가 `^def compute_session_view(` 다 → **두 함수가 이 순서로 인접해야 한다.** 그리고 `summarize_agent_runs` 는 그 **뒤**에 온다(현재 배치) | `hub_session` |
| T25-87 | `dashboard_key: str \| None = None` **<** `tier1_is_previous_task: bool = False` (`ProjectView` 필드 순서) · `^LIVE_SESSION_STATES` 가 줄 첫 칸에서 시작 | `hub_project` |

> **결정 MS6.** 각 모듈 안에서 **원본의 상대 순서를 그대로 유지한다.** 위 4개가 우연히 지켜지길
> 바라지 않고, 규칙으로 못박는다: "모듈 안 선언 순서는 `hub_model.py` 원본의 등장 순서와 같다."
> 이 규칙 하나면 순서 검사 4개가 자동으로 만족되고, `git diff` 도 읽기 쉬워진다.
> 다만 **섹션 주석의 번호는 지운다** — `---- 1. 내부 이벤트 필터 ----` → `---- 내부 이벤트 필터 ----`.
> 번호는 800줄 파일 하나를 훑기 위한 장치였고, 파일이 나뉘면 "9 다음에 8" 같은 잔재만 남는다.

### 결정 MS7 — 「코드 무변경」을 **AST 로 증명**한다 (검증 V2)

이 리팩토링의 유일한 진짜 위험은 "옮기다 한 줄을 바꿨는데 아무도 모른다"이다. 눈으로 보는
`git diff` 는 파일이 통째로 옮겨지면 도움이 되지 않는다. **AST 비교**가 그 증명이다.

```python
# 1회성 검증 스크립트(커밋하지 않는다). 주석·공백·docstring 위치 변화는 무시하고
# 코드 구조만 비교한다 — ast.dump 는 기본적으로 줄 번호를 담지 않는다.
import ast, subprocess

def symbols(source: str) -> dict[str, str]:
    collected = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            collected[node.name] = ast.dump(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    collected[target.id] = ast.dump(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            collected[node.target.id] = ast.dump(node)
    return collected

before = symbols(subprocess.run(
    ["git", "show", "HEAD:hub/bin/hub_model.py"], capture_output=True, text=True).stdout)
after = {}
for path in ["hub_model.py", "hub_session.py", "hub_project.py",
             "hub_server_state.py", "hub_usage.py"]:
    after.update(symbols(open("hub/bin/" + path).read()))

print("사라진 심볼 :", sorted(set(before) - set(after)))
print("바뀐 심볼   :", sorted(k for k in set(before) & set(after) if before[k] != after[k]))
```

**기대 출력: 두 줄 모두 빈 목록.** 하나라도 이름이 찍히면 그 심볼을 옮기다 건드린 것이다.

> `hub_usage.py` 를 `after` 에 포함하는 이유는 섹션 9 가 그리로 가기 때문이다. 그 파일의
> 기존 심볼은 `before` 에 없으므로 비교에 영향을 주지 않는다.

### 결정 MS8 — 주석·docstring 은 **딱 5종류만** 고친다

전제 1("동작을 바꾸지 않는다")은 주석에도 적용하되, **다른 모듈 이름을 지칭하는 문장은 고쳐야
사실이 된다.** 허용 목록을 명시한다 — 이 목록 밖의 문자는 한 글자도 바뀌지 않는다.

| # | 허용되는 편집 | 대상 |
|---|---------------|------|
| 1 | 모듈 docstring 신설/개정 | 새 파일 3개 + `hub_model.py` + `hub_usage.py` |
| 2 | `import` 문 | 새 파일 3개 + `hub_model.py` + 소비자 5개 + 테스트 5개 |
| 3 | 섹션 주석의 **번호 제거** | `---- N. …` → `---- … ----`(MS6) |
| 4 | 다른 모듈 이름을 지칭하는 주석 문장 **9곳**(아래 표) | 사실 정정 |
| 5 | `hub_model.` → `hub_session.` 등 **속성 접두어** | 소비자 5개 + 테스트 5개 |

**허용 4의 전수 목록**(`grep -n "hub_model\.py" hub/bin/*.py tests/hub/*.py` 결과):

| 파일:줄 | 지금 | 고칠 방향 |
|---------|------|-----------|
| `hub_daemon.py:4` | "`parse_server_record` 는 hub_model.py 에 있다" | → `hub_server_state.py` |
| `hub_daemon.py:65` | "parse_server_record 는 hub_model.py 로 옮겼다" | → `hub_server_state.py` |
| `hub_collect.py:4` | "hub_model.py·hub_parse.py(순수)의 결과를 조립해" | → 새 모듈 이름 나열 |
| `hub_collect.py:535` | "hub_model.py 는 …" | → `hub_server_state.py` |
| `hub_model.py:1·3` | 모듈 docstring | 허용 1 로 재작성 |
| `hub_model.py:22~27` | `PROJECT_DASHBOARD_RELATIVE_PATH` 주석의 "hub_collect 가 이미 hub_model 을 import 하므로" | → `hub_project` |
| `hub_model.py:674~677` | `parse_server_record` docstring 의 "둘 다 이미 hub_model 을 임포트하므로 순환이 없다" | → `hub_server_state`(잎 모듈이라 순환 불가라는 더 강한 사실로) |
| `hub_server.py:4` | "순수 로직은 hub_model.py 의 관련 함수들에 있다" | → 새 모듈 이름 나열 |
| `test_hub_daemon.py:3` · `test_hub_model.py:1093` | 테스트 이관 안내 | → `test_hub_server_state.py` |

### 결정 MS9 — 테스트 파일도 **1:1 로 쪼갠다**. 테스트 수 362 불변이 게이트다

저장소 관례는 소스 1개 ↔ 테스트 1개다(`test_hub_parse`·`test_hub_usage`·`test_hub_usage_fetch`·
`test_hub_settings`). `test_hub_model.py`(1200줄, 105 테스트, 26 클래스)를 그대로 두면 이
관례가 깨지고 "hub_model 을 테스트한다"는 이름이 거짓말이 된다.

| 새 테스트 파일 | 옮겨 가는 테스트 클래스 |
|----------------|------------------------|
| **`tests/hub/test_hub_session.py`** | `SessionStateLadderTest` · `InternalEventFilterTest` · `SubagentTrackingTest` · `SubagentZombieGuardTest` · `SummarizeAgentRunsTest` · `SessionRevivalTest` · `ParseEventLineTest` |
| **`tests/hub/test_hub_project.py`** | `Tier1GenerationTest` · `EncodeProjectDirNameTest` · `ShouldIgnoreCwdTest` · `ComposeProjectViewsTest` · `Tier1PriorityTest` · `ProjectDashboardKeyTest` · `ComposeProjectViewsDashboardKeyTest` |
| **`tests/hub/test_hub_server_state.py`** | `ShouldSpawnCollectTest` · `IsServerAliveTest` · `ServerHeartbeatTtlMsTest` · `ParseServerRecordTest` |
| `tests/hub/test_hub_usage.py`(기존에 추가) | `ShouldAttemptUsageApiPollTest` · `UsageApiPollDelayMsTest` · `NextUsageApiPollStateTest` |
| `tests/hub/test_hub_model.py`(잔여) | `RenderHubHtmlTest` · `BuildDashboardRegistryTest` · `SnapshotContentKeyTest` · `SnapshotContentKeyDashboardKeyTest` · `UsageSnapshotContentKeyTest` |

- **테스트 메서드는 한 글자도 바꾸지 않는다.** 바뀌는 것은 파일 상단의 import 와
  `hub_model.` → `hub_session.` 류 접두어뿐이다.
- 여러 모듈의 심볼을 함께 쓰는 테스트(예: `ComposeProjectViewsTest` 가 `SessionFacts` 를 만든다)는
  **필요한 모듈을 모두 임포트한다.** 접두어가 어느 도메인의 값인지 드러내므로 오히려 읽기 좋아진다.
- **게이트**: `python3 -m unittest discover -s tests/hub -t .` 의 `Ran N tests` 가 **362 로 동일**.
  줄어들면 테스트가 실종된 것이고, 늘어나면 이 커밋의 범위를 넘은 것이다.

### 결정 MS10 — 문서 이관 표기는 **한 곳에만** 둔다

`docs/prps/*.md` 14개 파일이 `hub_model.py` 를 총 139회 인용한다(전수 확인). 전부에 이관
화살표를 다는 것은 비현실적이고, 그 문서들은 **당시의 사실을 적은 역사 기록**이라 저장소 관례
("원문을 지우지 않는다")상 고칠 대상도 아니다.

| 파일 | 조치 |
|------|------|
| `docs/prps/hub-dashboard.md` 44·84·95행(모듈 구성표·레이어표·트리) | **개정.** 새 파일 3개를 표에 추가하고, `hub_model.py` 행에 `→ **분리됨(hub-model-module-split.md 결정 MS1)** — 심볼 귀속표는 그 문서가 정본` 을 덧붙인다 |
| 나머지 13개 PRP | **무수정.** 이 문서의 결정 MS5(심볼 귀속표)가 조회 테이블 역할을 한다 |
| `hub/README.md` 18·363행 | "12개 파일" → "15개 파일" |
| `hub/install.sh` 12행 | `HUB_FILE_COUNT=12` → `15` |

---

## 새 모듈의 docstring (신규 작성 — 유일한 새 산문)

기존 순수 모듈(`hub_model.py:1~6`·`hub_parse.py`·`hub_usage.py:1~13`)의 형식을 그대로 따른다:
**한 줄 요약 → 순수성 선언 + 테스트 파일 → 설계 정본 PRP.**

```python
"""hub_session.py — 훅 이벤트를 세션 사실로 접고, 그 사실을 표시 상태로 판정하는 순수 로직.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_session.py 대상).
`now_ms` 는 항상 인자로 받는다 — 테스트가 시계에 의존하지 않게 하기 위해서다.
상태 판정 규칙의 근거는 docs/prps/hub-dashboard.md 「상태 판정 규칙」 절이 정본이며,
좀비 서브에이전트 가드는 docs/prps/hub-zombie-subagent-guard.md, 세션 부활 규칙은
docs/prps/hub-session-revival-and-stale-tier1.md 가 정본이다.
"""

"""hub_project.py — 프로젝트를 발견하고 세션 뷰·티어 1 스냅샷을 프로젝트 뷰로 합성하는 순수 로직.

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_project.py 대상).
디렉토리명 인코딩은 **정방향 전용**이다(역방향 디코딩은 원리적으로 모호하다 —
docs/prps/hub-dashboard.md). 세대 판정(tier1_is_previous_task)의 근거는
docs/prps/hub-session-revival-and-stale-tier1.md 결정 GN1~GN3 이 정본이다.
"""

"""hub_server_state.py — 상주 서버의 기록 형식과 생존·재수집 판정(순수).

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_server_state.py 대상).
어떤 허브 모듈도 임포트하지 않는 **잎 모듈**이다 — parse_server_record 가 예전에
hub_daemon.py·hub_collect.py 에 사본으로 갈라져 있던 이유가 "순환 임포트 회피"였고(검수 m3),
잎으로 두면 그 위험이 구조적으로 재발할 수 없다. 설계 정본은
docs/prps/hub-dashboard.md 「상주 서버」 절과 docs/prps/hub-server-control-skill.md 다.
"""
```

`hub_model.py` 의 docstring도 다시 쓴다(범위가 줄었다):

```python
"""hub_model.py — 허브 스냅샷 계약(HubSnapshot·HubConfig)과 그 직렬화·렌더(순수).

이 모듈은 파일시스템·시각·환경변수에 닿지 않는다(★순수, tests/hub/test_hub_model.py 대상).
여기 있는 것은 **대외 계약**뿐이다 — HubSnapshot 은 hub_template.html 의 #dzh-data 와,
HubConfig 는 ~/.claude/hub/config.json 과 맺은 계약이며, render_hub_html 이 전자를 HTML 에
새기는 유일한 지점이다. 계산은 hub_session·hub_project·hub_server_state·hub_usage 에 있다
(분리 근거: docs/prps/hub-model-module-split.md 결정 MS1).
"""
```

`hub_usage.py` 의 docstring 첫 줄만 넓힌다:
`"""hub_usage.py — 한도 관련 외부 계약 파서 모음(순수)."""` →
`"""hub_usage.py — 한도 관련 외부 계약 파서 + 사용량 API 폴링 스케줄(순수)."""`

---

## 소비자 갱신표 (기계적 치환 — 이 표가 전부다)

### 소스 5개

| 파일 | 지금 | 분리 후 |
|------|------|---------|
| `hub_hook.py` | `import hub_model` | `import hub_model`(`HubConfig`) **+ `import hub_server_state`**(`is_server_alive`·`server_heartbeat_ttl_ms`·`should_spawn_collect`) |
| `hub.py` | `import hub_model` | `import hub_model`(`HubConfig`·`HubSnapshot`) **+ `import hub_server_state`**(`is_server_alive`·`server_heartbeat_ttl_ms`) |
| `hub_daemon.py` | `import hub_model` | **`import hub_model` 삭제** → `import hub_server_state` 만(`BrowserOpenResult`·`ServerStatus`·`is_server_alive`·`parse_server_record`·`server_heartbeat_ttl_ms` 전부 그리로 간다) |
| `hub_server.py` | `import hub_model` · `import hub_usage` | `hub_model`(`HubConfig`·`build_dashboard_registry`·`snapshot_content_key`) **+ `hub_server_state`**(`ServerRecord`) **+ 기존 `hub_usage`**(`UsageApiPollState`·`next_usage_api_poll_state`·`should_attempt_usage_api_poll` — **새 import 줄이 필요 없다**) |
| `hub_collect.py` | `import hub_model` · `hub_parse` · `hub_usage` | `hub_model`(`HubConfig`·`HubSnapshot`·`render_hub_html`) **+ `hub_session`**(`HookEvent`·`SessionFacts`·`build_session_facts`·`parse_event_line`) **+ `hub_project`**(`PROJECT_DASHBOARD_RELATIVE_PATH`·`compose_project_views`·`encode_project_dir_name`·`resolve_project_dirs`·`should_ignore_cwd`) **+ `hub_server_state`**(`ServerRecord`·`parse_server_record`) |

`hub_statusline.py`·`hub_settings.py`·`hub_parse.py`·`hub_usage_fetch.py` — **무변경**(`hub_model.*` 참조 0건).

### 테스트 5개

| 파일 | 치환 |
|------|------|
| `test_hub.py` | `hub_model.BrowserOpenResult`·`hub_model.ServerStatus` → `hub_server_state.*` |
| `test_hub_daemon.py` | `hub_model.HubConfig` 유지 · `hub_model.ServerRecord` → `hub_server_state.ServerRecord` |
| `test_hub_collect.py` | `HubConfig`·`HubSnapshot`·`snapshot_content_key` 유지 · `ServerRecord`·`parse_server_record` → `hub_server_state.*` |
| `test_hub_server.py` | `HubConfig`·`HubSnapshot` 유지 · `ProjectView`·`project_dashboard_key` → `hub_project.*` · `UsageApiPollState` → `hub_usage.*` |
| `test_hub_model.py` | 결정 MS9 대로 4개 파일로 분할 |

---

## `tests/run.sh` 갱신표 (28곳 전수)

`test_hub_docs_and_constants()` 의 지역 변수 선언부(2356행 부근)에 3줄을 추가한다:

```bash
  local hub_session_file="$REPO_ROOT/hub/bin/hub_session.py"
  local hub_project_file="$REPO_ROOT/hub/bin/hub_project.py"
  local hub_server_state_file="$REPO_ROOT/hub/bin/hub_server_state.py"
```

| 검사 | 위치 | 지금 보는 파일 | 바꿀 대상 |
|------|------|----------------|-----------|
| **T25-1** | 2362~2368 | `HUB_FILE_COUNT` | **값만** 12 → 15(파일 수 검사 로직은 무수정) |
| **T25-8** | 2435~2444 | `hub_model_file` | **무수정** — `server_port: int = 8794` 는 `HubConfig` 와 함께 잔류 |
| **T25-10** | 2451~2458 | 순수 파일 3개 목록 | **추가** — `hub_session.py`·`hub_project.py`·`hub_server_state.py` (총 6개) |
| **T25-13** | 2492~2503 | `render_hub_html_file`(=hub_model.py) | **무수정** — `render_hub_html` 잔류 |
| **T25-43** | 2892·2902 | `hub_model_file` | → `hub_session_file`(`summarize_agent_runs`·`agent_runs`·`active_agent_types` 부재) |
| **T25-51** | 3076 | `hub_model_file` | → `hub_project_file`(`sessions=session_views`) |
| **T25-52** | 3087 | `hub_model_file` | → `hub_session_file` |
| **T25-56** | 3140·3144 | `hub_model_file` | **무수정** — `HubSnapshot` 필드 잔류 |
| **T25-61** | 3229 | `hub_model_file` | → `hub_usage_file`(`should_attempt_usage_api_poll`·`UsageApiPollState`) |
| **T25-86** | 3698~3712 | `hub_model_file` | → `hub_session_file`(줄 번호 비교 포함) |
| **T25-87** | 3721~3739 | `hub_model_file` | → `hub_project_file`(줄 번호 비교 포함) |
| **T25-91** | 3805~3826 | `hub_model_file` | → `hub_session_file`(3중 순서 비교 포함) |
| **T25-92** | 3833~3849 | `hub_model_file` | → `hub_session_file`(awk 본문 추출 2건) |
| **T25-93** | 3853~3861 | `hub_model_file` | → `hub_session_file`(`zombie_after_ms` 기본 인자 **정확히 2건**) |
| **T24** | 2329 | `test_desc` 문구 | "hub_parse·hub_model 단위 테스트" → "허브 순수 모듈 단위 테스트" |
| **T25** 헤더 | 2345·2349 | `T25-1~T25-94` | 신규 검사를 더하면 갱신(아래) |

### 신규 검사 (T25-95 부터 — 이 분리가 **되돌아가지 않게** 못박는다)

> **주의**: `hub-panel-polish-and-icons.md` 도 T25-95~99 를 쓴다. 두 PRP 를 함께 구현하면
> **먼저 병합되는 쪽이 95~99 를 가져가고 나중 쪽은 100~** 을 쓴다. 이 문서는 편의상 T25-100~ 로
> 적고, 단독 구현 시 95~ 로 당긴다(승인 항목 5).

| # | 대상 | 정방향(있어야) | 역방향(없어야) |
|---|------|----------------|----------------|
| **T25-100** | MS1 파일 존재·크기 | `hub_session.py`·`hub_project.py`·`hub_server_state.py` 가 존재하고, `hub/bin/*.py` 전부가 **800줄 이하** | — |
| **T25-101** | MS2 파사드 부재 | — | `hub_model.py` 에 `from hub_session import *` 류 재노출 0건 · `hub_model.py` 에 `def compute_session_view` 등 이동한 심볼 정의 0건 |
| **T25-102** | MS4 순환·잎 계약 | `hub_server_state.py` 의 import 가 stdlib 뿐(`^import \|^from ` 줄에 `hub_` 0건) · `hub_session.py` 에 `hub_project` 0건 | `hub_project.py` 에 `import hub_model` 0건(역방향 간선 금지) |
| **T25-103** | MS9 테스트 1:1 | `tests/hub/test_hub_session.py`·`test_hub_project.py`·`test_hub_server_state.py` 존재 | `test_hub_model.py` 에 `SubagentZombieGuardTest`·`ComposeProjectViewsTest`·`ParseServerRecordTest` 0건(잔류 회귀) |
| **T25-104** | 문서 정합 | `hub/README.md` 에 `15개 파일` · `hub-dashboard.md` 모듈표에 `hub_session.py` | `hub/README.md` 에 `12개 파일` 0건 |

---

## 검증 (구현자가 순서대로 실행한다)

| # | 명령 | 기대 |
|---|------|------|
| **V1** | `wc -l hub/bin/*.py \| sort -rn \| head` | 최대값이 **800 미만**, 분리 4파일이 400 이하 |
| **V2** | 결정 MS7 의 AST 비교 스크립트 | **"사라진 심볼: []" · "바뀐 심볼: []"** ← 이 게이트를 통과하지 못하면 다음으로 가지 않는다 |
| **V3** | `python3 -m unittest discover -s tests/hub -t .` | `Ran 362 tests` · `OK` (**숫자가 362 여야 한다**) |
| **V4** | `bash tests/run.sh` | 전 항목 통과 |
| **V5** | `cd hub/bin && python3 -c "import hub_collect, hub_daemon, hub_hook, hub_server, hub_statusline"` | 예외 없음(순환 임포트가 있으면 여기서 터진다) |
| **V6** | `grep -rn "hub_model\.\(compute_session_view\|build_session_facts\|parse_server_record\|compose_project_views\|is_server_alive\|should_spawn_collect\|UsageApiPollState\)" hub/bin tests` | **0건** |
| **V7** | `bash hub/install.sh --dry-run` | 계획 파일 수가 15로 보고된다 |
| **V8** | 실사용 스모크 — `/hub server restart` 후 `hub.html` 이 갱신되고 카드가 보인다 | 순수 이동이므로 화면이 **이전과 완전히 같아야** 한다 |

---

## GOTCHA (구현자가 틀리기 쉬운 함정)

1. **`compute_session_view` 와 `summarize_agent_runs` 를 다른 파일에 두지 마라.** T25-92 가
   두 함수 **본문 각각**에 `is_running_subagent(` 호출이 있는지 검사하고, 그 검사는
   "카드 상태와 칩이 어긋날 수 없다"는 결정 ZG4·ZG5 를 지키는 장치다. 파일이 갈리면 검사도,
   그 검사가 지키던 성질도 함께 흐려진다.
2. **선언 순서를 "정리"하지 마라.** 알파벳순·공개/비공개순으로 재배열하고 싶어지지만,
   T25-86·87·91·92 가 **줄 번호 순서**를 본다(GOTCHA 1 과 같은 이유). 원본 순서를 그대로 옮긴다(MS6).
3. **`SUBAGENT_ZOMBIE_AFTER_MS` 는 `is_running_subagent` 보다 위에 있어야 한다.** 함수 기본
   인자(`zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS`)는 **정의 시점에 평가**되므로 아래에
   두면 `NameError` 로 임포트 자체가 실패한다. 지금 순서가 그 이유로 정해져 있다.
4. **`zombie_after_ms: int = SUBAGENT_ZOMBIE_AFTER_MS` 는 정확히 2건이어야 한다**(T25-93).
   `compute_session_view` 와 `summarize_agent_runs` 둘 다 `hub_session.py` 로 가므로 자연히
   지켜지지만, "한쪽은 상수를 직접 쓰자" 같은 정리를 하면 깨진다.
5. **`hub_daemon.py` 의 `import hub_model` 을 지우는 것을 잊지 마라.** 쓰던 심볼이 전부
   `hub_server_state` 로 가므로 남기면 미사용 임포트가 된다(전역 지침: "내 변경 때문에 쓰이지
   않게 된 import 는 제거한다").
6. **`hub_server.py` 에는 `import hub_usage` 가 이미 있다.** 섹션 9 를 그리로 옮겨도
   **새 import 줄이 필요 없다** — 접두어만 `hub_model.` → `hub_usage.` 로 바뀐다.
7. **`hub_collect.py` 는 네 모듈을 전부 쓴다.** 임포트 4줄이 되는 유일한 파일이며, 그것이
   이 파일이 "조립기"라는 사실의 정직한 표현이다. 줄이려고 파사드를 만들지 마라(MS2).
8. **`asdict(snapshot)` 은 중첩 dataclass 를 재귀 변환한다** — `ProjectView`·`SessionView` 가
   다른 모듈로 가도 JSON 출력은 **글자 하나 안 바뀐다.** `hub_template.html` 을 확인하러 갈
   필요가 없다(전제 3).
9. **`test_hub_model.py:1093` 의 주석은 지금은 참이지만 이동 후 거짓이 된다.** 허용 편집 4 에
   들어 있다 — 놓치면 다음 사람이 존재하지 않는 파일을 찾는다.
10. **`hub/install.sh` 의 `HUB_FILE_COUNT` 를 안 고치면 설치가 실패한다**(98~99행이 실제
    파일 수와 비교해 abort 한다). T25-1 이 먼저 잡아 주지만, 실사용 스모크(V7·V8) 전에
    반드시 고친다.

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| **P-1** | **옮기다 한 줄을 바꿨는데 아무도 모른다** — 이 작업의 유일한 진짜 위험 | **검증 V2(AST 비교)가 정면으로 막는다.** 눈이나 diff 에 의존하지 않는다. V3 의 테스트 수 362 불변이 2차 그물 |
| **P-2** | **순환 임포트** | 의존 그래프가 DAG 임을 설계에서 못박고(MS4), `hub_server_state` 를 잎으로 둔다. V5 가 임포트 1회로 실증하고 T25-102 가 회귀를 막는다 |
| **P-3** | **`tests/run.sh` 갱신 누락으로 검사가 조용히 무력화된다** — grep 대상 파일에 토큰이 없으면 `record_failure` 가 나므로 **실패로 드러난다**. 그러나 반대 방향(잘못된 파일을 가리켜 우연히 통과)은 조용하다 | 갱신표(위)가 28곳 전수이며, 각 검사의 "지금 보는 파일 → 바꿀 대상"을 1:1 로 적었다. 구현 후 `grep -c 'hub_model_file' tests/run.sh` 가 **5**(T25-8·10·13·56 + 선언 1줄)인지 세어 확인한다 |
| **P-4** | **배포된 `~/.claude/hub/bin` 에 옛 `hub_model.py` 가 남아 새 모듈과 섞인다** | `hub/install.sh` 는 소스에 없는 파일을 지우지 않는다 — 옛 `hub_model.py` 는 **덮어써지고**(이름이 유지되므로) 나머지 3개가 추가될 뿐이라 유령 모듈이 생기지 않는다. 그래도 `HUB_FILE_COUNT` 검증(98행)이 15개를 확인한다. V7·V8 로 실측 |
| **P-5** | **`/hub` 가 도는 도중에 설치해 반쪽 상태가 된다** | 기존 관례 그대로 — `hub/install.sh --uninstall` 이 아니라 재설치는 서버 재기동(`/hub server restart`)으로 마무리한다(V8). 이 PRP 가 새로 만드는 위험이 아니다 |
| **P-6** | **`hub_model.py` 가 85줄로 줄어 "왜 남겼나" 라는 의문이 재발한다** | 새 docstring 이 이유를 적는다("여기 있는 것은 대외 계약뿐이다"). MS1 의 근거 문단이 정본 |
| **P-7** | **두 PRP 가 T25 번호를 동시에 쓴다** | 승인 항목 5 — 병합 순서에 따라 번호를 당긴다. 번호 충돌은 `tests/run.sh` 를 읽으면 즉시 보인다(같은 번호가 두 번 나온다) |

---

## YAGNI 보류 (지금 만들지 않는다 + 재방문 트리거)

| # | 보류 항목 | 이유 | 재방문 트리거 |
|---|-----------|------|---------------|
| 1 | **패키지화(`hub/bin/hub/` + `__init__.py`)** | 배포기가 최상위 파일을 세고, `sys.path` 관례가 파일 평면에 맞춰져 있다. 얻는 것은 이름공간 하나 | `hub/bin` 이 20개 파일을 넘어 최상위가 읽기 어려워질 때 |
| 2 | **`hub_constants.py`(공유 상수 모듈)** | 지금 공유되는 것은 `MILLISECONDS_PER_SECOND` 하나이고, 그 중복은 이미 존재한다 | 세 모듈 이상이 같은 상수를 셋 이상 공유하게 될 때 |
| 3 | **`hub_model.py` 를 `hub_snapshot.py` 로 개명** | 잔여 내용에는 그 이름이 더 정확하지만, 개명은 소비자 4개 + 테스트 3개 + 문서를 **추가로** 흔든다. 이 커밋의 목적은 크기와 응집이지 이름이 아니다 | 다음에 `hub_model.py` 를 실질적으로 고칠 일이 생겼을 때 함께 |
| 4 | **`hub_collect.py`(563줄) 분리** | 상한에 닿지 않았고 요구에 없다 | 700줄을 넘을 때 |
| 5 | **`compose_project_views`(39줄) 등 긴 함수 쪼개기** | 전제 1. 이동과 수정을 섞으면 V2 게이트가 무의미해진다 | 이 분리가 병합된 **다음** 커밋에서 별건으로 |

---

## 검토했으나 채택하지 않은 대안 (요약)

| 대안 | 기각 사유 |
|------|-----------|
| **`hub_model.py` 를 재노출 파사드로 남긴다** | 어차피 고쳐야 하는 `tests/run.sh` 28곳·테스트 5개를 전혀 아껴 주지 못하면서, "같은 것에 이름이 둘"이라는 영구 중복을 만든다. T25-86·87·91·92 는 **한 파일 안의 줄 번호 순서**를 보므로 파사드로는 원리적으로 만족시킬 수 없다(MS2) |
| **최소 분리 — `hub_session.py` 하나만 떼고 끝낸다** | 799 → 약 450 이라 상한 문제는 풀리지만, 남는 파일이 "프로젝트 + 설정 + 서버 + 사용량 폴링 + 렌더"라는 이름 붙일 수 없는 잡탕으로 남는다. 다음 사람이 같은 작업을 다시 해야 한다 |
| **섹션 9 를 독립 모듈(`hub_usage_poll.py`)로** | 55줄짜리 모듈이 생기고 `hub_usage*` 가 셋이 된다. 사용량 도메인의 순수 로직은 `hub_usage.py` 가 이미 담당하며, 그 파일은 편입 후에도 470줄로 여유가 있다. **다만 취향이 갈리는 지점이라 승인 항목 2 로 올린다** |
| **`ServerRecord` 등을 `hub_daemon.py` 로 되돌린다** | `hub_server.py`·`hub_collect.py` 도 쓴다. 되돌리면 검수 m3 가 없앤 "사본 두 벌" 문제가 부활한다(`parse_server_record` docstring 이 그 이력을 남겨 놓았다) |
| **한 번에 옮기지 않고 여러 커밋으로 점진 이동** | 중간 커밋마다 `tests/run.sh` 가 빨간불이 된다(검사가 옛 파일을 가리킨다). 검증 V2·V3·V4 가 전부 "한 번에 옮겼을 때"만 의미를 갖는다 |

---

## 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | `hub_session.py` 생성(순서 보존) + `hub_model.py` 에서 해당 구간 삭제 | V2 부분 실행(사라진 심볼 없음 확인) |
| 2 | `hub_project.py` · `hub_server_state.py` 생성 + `hub_usage.py` 편입 + `hub_model.py` 잔여 정리 · docstring 5개 | **V1 · V2 전체 · V5** |
| 3 | 소스 소비자 5개 import·접두어 갱신 + 주석 9곳 정정 | V5 · V6 |
| 4 | 테스트 5개 갱신 + `test_hub_model.py` 4분할 | **V3(Ran 362 · OK)** |
| 5 | `tests/run.sh` 28곳 재지정 + 신규 5건 + `HUB_FILE_COUNT` 12→15 | **V4** |
| 6 | `hub/README.md` · `hub-dashboard.md` 문서 갱신 | V4(T25-104) |
| 7 | 설치·스모크 | V7 · V8 |

---

## 승인 요청 항목

> 아래 5건은 취향·트레이드오프가 갈리는 지점이다. **각 항목의 권고안대로 진행해도 되는지**
> 확인해 주면 그대로 구현에 들어간다.

### 승인 항목 1 — **파사드를 만들지 않고 호출부 10개를 함께 고친다** (결정 MS2)
**권고: 채택.** 파사드가 아끼는 것은 소스 5개의 import 줄뿐이고, 진짜 비용인 `tests/run.sh`
28곳과 테스트 5개는 어느 쪽이든 고쳐야 한다. 대신 "같은 것에 이름이 둘"이라는 영구 부채가 남는다.
**대안:** 파사드를 두고 호출부를 그대로 둔다 — 이 경우에도 `tests/run.sh` 는 새 파일들을
가리키도록 고쳐야 하므로, 실제로 줄어드는 diff 는 약 30줄뿐이다.

### 승인 항목 2 — **사용량 API 폴링 스케줄(섹션 9)을 `hub_usage.py` 로 편입한다** (결정 MS1)
**권고: 채택.** 사용량 도메인의 순수 로직이 이미 그 파일에 있고, 편입 후에도 470줄로 여유가 있다.
`hub_server.py` 는 이미 `hub_usage` 를 임포트하므로 새 import 줄도 필요 없다.
**대안:** 독립 모듈 `hub_usage_poll.py`(약 55줄) — 파일 수가 16이 되고 `hub_usage*` 가 셋이 된다.

### 승인 항목 3 — 모듈 이름: **`hub_session` · `hub_project` · `hub_server_state`** (결정 MS1)
**권고: 채택.** 앞 둘은 도메인 명사이고 형제 관례(`hub_parse`·`hub_usage`)와 맞는다.
`hub_server_state` 는 "`hub_server.py`(HTTP I/O)·`hub_daemon.py`(프로세스 I/O)가 공유하는
**순수 판정·기록 형식**"이라는 뜻이다.
**대안:** `hub_server_state` → `hub_process`(pid·생존·spawn 을 다룬다는 뜻은 맞지만
`BrowserOpenResult` 가 어색해진다) 또는 `hub_supervision`(추상적이다).

### 승인 항목 4 — `hub_model.py` 이름을 **그대로 유지**하고 85줄로 남긴다 (결정 MS1 · YAGNI 보류 3)
**권고: 채택.** 남는 것은 "허브의 대외 계약"이라는 뚜렷한 책임이고, 이름을 지키면 소비자 4개와
테스트 3개의 import 줄이 그대로 살아 diff 가 줄어든다.
**대안:** `hub_snapshot.py` 로 개명 — 잔여 내용에는 더 정확하지만 이번 커밋의 범위를 넓힌다.

### 승인 항목 5 — **두 PRP 의 T25 번호 배분** (리스크 P-7)
**권고:** `hub-panel-polish-and-icons.md`(UI)가 **T25-95~99**, 이 문서가 **T25-100~104**.
UI 쪽이 규모가 작아 먼저 병합될 가능성이 높다는 판단이다.
**대안:** 이 문서를 먼저 구현한다면 번호를 서로 맞바꾼다(이 문서 95~99, UI 100~104).
