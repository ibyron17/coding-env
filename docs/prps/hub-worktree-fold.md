# 허브 — 워크트리 cwd 를 소유 레포 루트로 **접기**(fold) + 티어 1 **출처 확장** (PRP)

> 요구 2건: **R1** 워크트리에서 도는 세션이 **레포 루트 카드 안에** 나타나고, 창이 굴러도
> 카드에서 사라지지 않는다 · **R2** 그 카드의 진행률이 **지금 갱신되고 있는 대시보드**를 가리킨다
> (클릭해서 열리는 파일도 같은 파일이다)

> **2판 요약 (2026-08-20).** 초판은 구현·검수를 통과했으나 **S8(수동 확인)이 실패**했다.
> 결함 B(flip)는 해결됐고 **결함 A(티어 1 불일치)는 안 고쳐졌다.** 원인은 구현 오류가 아니라
> 이 문서의 설계 구멍이다 — 티어 1 **후보 목록을 만드는 입력**이 `SessionFacts.cwd` 하나뿐인데
> 그 값은 창 안 최초 이벤트로 고정되므로(E1) 워크트리 경로가 후보에 오를 길이 **원리적으로**
> 없었다. 2판은 그 입력을 고치고(결정 **WT16**), **같은 구멍이 다시 열리면 단위 테스트가 잡도록**
> 성공 기준을 이음매 앞으로 옮긴다(결정 **WT20**). 신규 결정 **WT15~WT22**.

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/` **5개 파일**(`hub_project.py`·`hub_parse.py`·`hub_collect.py`·`hub_model.py` + 2판에서 **`hub_session.py` 추가**) + 테스트 **6개** + `tests/run.sh` + `hub/README.md` + PRP 이관 표기 4곳 |
| 브랜치 | `main` (초판 구현은 `2fcadbf`), 작업 위치는 워크트리 `.claude/worktrees/worktree-project-merge` |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md)(쟁점 4·CAM P5) → [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md)(N1~N3) → [`hub-session-revival-and-stale-tier1.md`](./hub-session-revival-and-stale-tier1.md)(GN1~GN3) → [`hub-model-module-split.md`](./hub-model-module-split.md)(MS1~MS4) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 프로젝트 그룹핑 키(공개 데이터 모델의 신원)와 `Tier1Snapshot` 계약이 함께 바뀐다 |
| 규모 | 초판 **Medium**(수정 10개, `hub/bin` +70/−10줄, 테스트 +190줄). **2판 순증은 Small** — `hub/bin` 약 **+18 / −4줄**(5개 파일), 테스트 약 **+230줄**(6개 파일). 신규 파일 0개 |
| **새 모듈** | **없음.** `hub/install.sh:12 HUB_FILE_COUNT=15`·`hub/README.md:18`·`:384`·`tests/run.sh:3881-3886` 네 곳의 「15」 리터럴을 **건드리지 않는다**(근거: 결정 WT13) |
| 새 외부 의존성 | **없음** (stdlib 만, 서브프로세스 0회) |
| 새 config 필드 | **0개.** `ignore_globs` 기본값도 **그대로 둔다**(결정 WT4) |
| 화면 변경 | **없음.** `hub_template.html` 0줄, `SessionView` 0필드, `ProjectView` 0필드(결정 WT11). 2판이 늘리는 `SessionFacts.observed_cwds` 는 **`#dzh-data` 에 실리지 않는다** — 스냅샷에 담기는 것은 `SessionView` 이고 `SessionFacts` 는 담기지 않는다(실측: `SessionView` 에 `cwd` 필드가 없다) |
| 결정 코드 | **WT**(WorkTree). 단일 문자 A~Z 는 소진됐고 두 글자 관례(SP·MD·GN·PV·DG·ZG·RV·MS·OC)가 확립돼 있다. `WT` 가 저장소 전체에서 미사용임을 확인했다(`grep -rn "결정 WT" docs/prps` → 0건) |
| 리스크 코드 | **P-n**(최근 PRP 전부 이 계열) · 회귀 검사 초판 **T25-111~T25-114** + 2판 **T25-115~T25-118**(현재 최대 `T25-114`) |
| 승인 상태 | 초판(WT1~WT14) **승인·구현·검수 완료** (`2fcadbf`) · **2판(WT15~WT22) 미승인 — 「승인 요청 항목」 8~11 회신 대기** |

### 개정 이력

| 개정 | 내용 |
|------|------|
| 초판 (2026-08-20) | 사전 조사(6축 106건 + 공백 보완 3건) 위에서 작성. 결정 WT1~WT14 신설. `hub-dashboard.md` **CAM P5 배제 번복**, `hub-session-revival-and-stale-tier1.md` **GN2 개정**, `hub-card-interactions-and-usage.md` **N3 재진술**, `dashboard-ownership-guard.md` **R4 부분 해소** |
| **2판 — S8 실패 반영 (2026-08-20)** | **사유: 실환경 검증에서 S8 이 실패했다.** 결함 B(flip)는 해결됐으나 결함 A(티어 1 불일치)가 그대로였다 — 설치·재시작 후에도 카드가 어제 파일(`08-19 17:54`)을 가리키고 「이전 작업」 라벨이 켜져 있었다. **원인은 후보 목록을 만드는 입력의 구멍**이다: `plan_tier1_candidates` 의 `observed_paths` 가 `SessionFacts.cwd` 뿐인데 그 값은 창 안 최초 이벤트로 고정되고(E1), `EnterWorktree` 는 살아 있는 세션의 cwd 를 도중에 바꾸므로(E2) 워크트리 경로는 **이벤트에는 있지만 `SessionFacts` 에는 남지 않는다.** 초판은 이 상황(E4)을 정확히 관측하고도 해법을 「`read_tier1_snapshot` 이 경로 하나만 읽는다」에 맞췄다. U-14~U-16 이 `member_paths` 를 **손으로** 넘기는 구조라 이 구멍을 구조적으로 잡을 수 없었고, 검수는 PRP 대비 정합성을 봤기 때문에 통과했다. 신규 결정 **WT15~WT22**, 신규 실측 **E10~E15**, 성공 기준 **S8 재정의 + S9~S13 신설**, 신규 테스트 **U-22~U-30**, 회귀 검사 **T25-115~118**, 뮤테이션 **9~13** |
| 검수 1회차 반영 (2026-08-20) | M1 — `collect_snapshot` 조립부 3줄을 `hub_project.plan_tier1_candidates`(★순수, 신설)로 추출하고 `hub_collect._collect_tier1_snapshots`(신설)가 조립 루프를 맡도록 분리. 참조하는 모든 테스트가 `_read_tier1_for_root` 를 mock.patch 로 우회해 이 조립을 실행하는 테스트가 없었던 결함을 해소(단위 테스트 6건 신설, 뮤테이션 3건 재검증). m2 — `hub_collect._read_tier1_for_root` 의 미사용 `root: str` 인자 제거. m3 — U-12 를 다중 이벤트 시나리오 + 실제 `should_ignore_cwd` 호출로 재작성(항진명제 제거). m5 — `plan_tier1_candidates` 에 빈 문자열 루트 제외 가드 추가. `tests/run.sh` T25-111~114 를 `note_failure`(누적형)로 전환(M2, 8680112 규약 적용) |

> **줄 번호 기준선.** 초판의 모든 줄 번호는 **HEAD `fb054b8` 의 커밋 상태**를 직접 열어
> 확인한 값이다. **2판의 줄 번호·측정치는 초판 구현이 들어간 `2fcadbf` 기준**이며, 2판을 쓰면서
> 전부 다시 열어 확인했다. 초판 시점의 줄 번호는 지우지 않는다(어느 시점의 값인지만 구분한다).

---

## 1. 진단의 근거

**E1~E9 는 초판 작성 세션의 측정이고, E10~E15 는 2판이 초판 구현(`2fcadbf`)이 설치된 상태에서
직접 재측정한 값이다.** 2판의 측정은 전부 읽기 전용 스크립트로 수행했고 그대로 재실행 가능하다
(`scratchpad/diag_m5.py`·`diag_flip.py`·`diag_wt15.py`·`diag_wt15b.py`·`diag_wt15c.py`).

### E1~E9 (초판)

| # | 사실 | 측정 방법 |
|---|------|-----------|
| **E1** | `SessionFacts.cwd` 는 **2일 창 안 최초 이벤트**의 cwd 로 한 번 정해지고 이후 절대 갱신되지 않는다 | `hub_session.py:210-212`(`_new_session_builder(cwd=event.cwd)`) + `:184-207`(`_apply_tracked_event` 6개 분기에 cwd 없음) 직접 확인 |
| **E2** | `EnterWorktree` 는 **이미 살아 있는 세션의 cwd 를 도중에 바꾼다**. 그래서 첫 이벤트는 거의 항상 레포 루트다 — 보존된 8일 134세션 중 **첫 이벤트가 워크트리인 세션 0건** | `~/.claude/hub/events/*.jsonl` 8개 파일 전수 집계 |
| **E3** | **「워크트리 세션은 허브에 안 보인다」는 전제는 거의 틀렸다.** 지금 이 세션(`5b6a1f57`)은 이미 `coding-env` 카드에 들어 있다 | `hub_collect._group_sessions_by_project(events, cfg.ignore_globs)` 읽기 전용 실행 → `coding-env` 그룹 15세션(`5b6a1f57` 포함) |
| **E4** | **결함 A(지금 라이브)**: 카드의 티어 1 은 레포 루트 파일(`2026-08-19 17:54:15` · 「허브 상세 패널 — …」 · **100%**)이고, 워크트리의 오늘 파일(`2026-08-20 11:06:02` · 「워크트리 cwd → 레포 루트 병합」 · **0%**)은 **읽히지 않는다** | 두 경로에 `hub_collect.read_tier1_snapshot()` 직접 호출 |
| **E5** | **결함 B(시한폭탄)**: 창이 굴러 최초 이벤트가 만료되면 세션 cwd 가 워크트리로 바뀌고 `ignore_globs` 에 걸려 **진행 중인 세션이 카드에서 조용히 사라진다** — 그룹 크기 15 → 1 | 첫 워크트리 이벤트 이전을 잘라낸 이벤트 목록으로 `build_session_facts` → `_group_sessions_by_project` 재실행(읽기 전용 시뮬레이션) |
| **E6** | 창이 날짜 파일 2개(오늘·어제)라 **flip 시점은 「48시간 뒤」가 아니라 「모레 자정」**이다 | `hub_collect.py:167-171` |
| **E7** | cwd drift 는 워크트리 전용 현상이 **아니다.** 2일 창 다중 cwd 3건 중 워크트리는 1건, 나머지는 scratchpad 로 튀거나 다른 프로젝트로 튄다 | 이벤트 파일 직접 집계 |
| **E8** | 문자열 접기(`/.claude/worktrees/` 앞 절단)가 git 의 실제 소유 관계와 **일치한다** | `git worktree list`, `cat <worktree>/.git`(=`gitdir: <repo>/.git/worktrees/<name>`), `git rev-parse --git-common-dir` |
| **E9** | fold-first 로 순서를 뒤집어도 `/tmp`·`/private/tmp` 가드는 **살아남는다**. 접힌 `/private/tmp/x/scratch-repo` 도 여전히 `/private/tmp/**` 에 걸린다 | 7개 경로에 대해 `should_ignore_cwd(fold(p), globs)` 직접 실행(기본값·사용자 config 양쪽) |

### E10~E15 (2판 — 초판 구현이 설치·가동 중인 상태에서 재측정)

| # | 사실 | 측정 방법 |
|---|------|-----------|
| **E10** | **결함 B(flip)는 해결됐다.** 실데이터로 창을 굴리면 세션 cwd 가 워크트리로 바뀌어도 `coding-env` 그룹에 남는다(그룹 크기 2, 대상 세션 포함) | 첫 워크트리 이벤트 이전을 잘라낸 이벤트 목록으로 `_group_sessions_by_project` 재실행 (`diag_flip.py`) |
| **E11** | **결함 A 는 안 고쳐졌다.** 지금 이 순간 `coding-env` 그룹의 `SessionFacts.cwd` 고유값은 **레포 루트 하나뿐**이고, `plan_tier1_candidates` 가 만든 멤버 목록도 `('/Users/byron/private/project/coding-env',)` 로 **워크트리가 없다.** 그런데 이벤트 원본 cwd 에는 워크트리 경로가 **있다** | 설치된 코드로 `load_config` → `read_recent_events` → `_group_sessions_by_project` → `plan_tier1_candidates` 를 순서대로 실행 (`diag_m5.py`) |
| **E12** | **역설이 성립한다** — 창이 굴러 cwd 가 워크트리로 바뀌면 **그때는** 워크트리가 티어 1 후보에 들어간다(`('/…/coding-env', '/…/coding-env/.claude/worktrees/worktree-project-merge')`). 즉 **결함 A 는 결함 B 가 발동할 상황이 돼서야 고쳐진다.** 사용자가 지금 보는 화면에서는 고쳐지지 않는다 | 위 flip 시뮬레이션의 그룹으로 `plan_tier1_candidates` 재실행 (`diag_flip.py`) |
| **E13** | **후보 입력을 이벤트 원본 cwd 로 넓혀도 노이즈는 fold→ignore 가 걸러낸다.** 2일 창에서 `SessionFacts.cwd` 4개 vs 이벤트 원본 cwd 7개. 늘어난 3개 중 `/Users/byron`(사용자 config 의 ignore)와 scratchpad 1건(`/private/tmp/**`)은 걸러지고 **워크트리 1건만 후보로 남는다** | 늘어난 경로마다 `should_ignore_cwd(fold(p), globs)` 직접 실행 (`diag_wt15.py`) |
| **E14** | **그래도 fold→ignore 만으로는 부족하다.** 보존된 8일 전수(이벤트 1,257건)에서 「이벤트에만 있고 `SessionFacts` 에는 없는」 cwd 는 4개인데, 그중 1개는 **프로젝트의 하위 디렉토리**(`…/klago-ui-oneffice-micro/public/word/js/script`)다. fold 는 항등이고 ignore 에도 안 걸려 **새 티어 1 루트가 된다.** 지금은 그곳에 `dashboard.html` 이 없어 카드가 안 생길 뿐이고, 생기면 **한 프로젝트가 카드 둘로 쪼개진다** | 8일 이벤트 파일 전수 파싱 후 루트 집합 비교, 각 루트의 `.claude/dashboard.html` 존재 확인 (`diag_wt15b.py`) |
| **E15** | **권고안(WT16+WT17)을 실데이터로 시뮬레이션하면 결함 A 가 고쳐진다.** 루트 집합은 **변하지 않고**(4개 그대로) `coding-env` 멤버만 워크트리가 추가된다. 그 결과 티어 1 승자가 **워크트리 대시보드**(「워크트리 cwd → 레포 루트 병합」, 0%)로 바뀌고 「이전 작업」 라벨은 **꺼진다**(세션 시작 `08-20 09:50` < 파일 mtime `08-20 13:04`). 대조: `facts.cwd == source_path` 방식(=후보 (a))은 live 집합이 **0** 이라 라벨이 우연히 꺼지는 반면, `source_path in observed_cwds` 방식(=후보 (c))은 live 집합이 **1** 이고 실제 대소 비교로 꺼진다 | 세션별 관측 cwd 를 이벤트에서 재구성해 앵커 규칙으로 후보를 만들고 `_collect_tier1_snapshots` → `is_tier1_from_previous_task` 까지 실행 (`diag_wt15c.py`) |

> **E11 이 이 개정의 출발점이다.** 초판은 E4 로 이 상황을 **정확히 관측**하고도 해법을
> 「`read_tier1_snapshot` 이 프로젝트 경로 하나만 읽는다」에 맞췄다. 진짜 병목은 그 **앞 단계**,
> 곧 **후보 목록을 만드는 입력**이었다. 리더를 아무리 고쳐도 후보 목록에 워크트리가 없으면
> 읽을 것이 없다.

### 결정 WT1 — 문제 정의를 실측 위에 다시 쓴다

원래 요구는 「워크트리 세션이 허브에 안 보이니 레포 루트 카드로 합쳐 달라」였다. **E3 이 그 전제를
반박했다** — 이미 보인다. 따라서 성공 기준을 「워크트리 세션이 보이게 된다」로 잡으면 **이미 되는
일을 검증하는 공허한 PRP** 가 된다.

이 작업이 고치는 것은 실제로 관측된 결함 두 개다.

| 결함 | 상태 | 증상 | fold 만으로 고쳐지는가 |
|------|------|------|------------------------|
| **A. 티어 1 불일치** | **지금도 라이브**(E4 → **E11 로 재확인**) | 카드 진행률이 어제의 다른 작업(100%)을 가리키고 「이전 작업」 라벨이 상시 점등. 클릭해도 어제 파일이 열린다 | **아니다** — 티어 1 리더가 여전히 레포 루트 한 파일만 본다 |
| **B. flip** | **해결됨**(E5·E6 → **E10 으로 확인**) | 날짜 경계를 넘으면 진행 중인 세션이 카드에서 통째로 사라진다 | **그렇다** — fold 의 유일하게 실증된 정당화 근거 |

> **2판의 정정.** 위 「fold 만으로 고쳐지는가」 칸의 A 행은 **맞았지만 불충분했다.** 초판은
> 「리더를 고치면 A 도 고쳐진다」로 이어갔는데, 리더가 읽을 **후보 목록**을 만드는 입력이
> 그대로였다. 결함 A 의 정확한 원인 문장은 이렇게 다시 쓴다 —
> **「티어 1 후보 목록의 입력이 `SessionFacts.cwd` 하나뿐이고, 그 값은 창 안 최초 이벤트로
> 고정되므로(E1) 살아 있는 세션이 워크트리로 들어가도(E2) 워크트리 경로는 후보에 오를 길이
> 없다.」** 이 문장이 결정 WT15~WT17 의 근거다.

---

## 2. 요구사항 / 사용자 스토리 / 성공 기준

### 사용자 스토리

> 레포 루트에서 작업을 시작해 워크트리로 들어간 사용자로서,
> 허브의 그 레포 카드 하나만 보면 **워크트리에서 진행 중인 작업의 현재 단계**를 알고 싶다.
> 워크트리마다 카드가 따로 생기거나, 날짜가 바뀌었다고 세션이 사라지거나,
> 어제 끝난 다른 작업의 100% 가 붙어 있으면 그 카드를 신뢰할 수 없다.

### 성공 기준 (전부 검증 가능한 형태)

| # | 기준 | 검증 수단 |
|---|------|-----------|
| **S1** | 세션의 cwd 가 `<repo>/.claude/worktrees/<name>` 일 때 그 세션은 **`<repo>` 그룹**에 들어간다 | 단위 — `_group_sessions_by_project` 반환 dict 의 키 |
| **S2** | **E5 의 flip 시나리오를 재현해도** 세션이 사라지지 않는다: 첫 이벤트가 워크트리인 이벤트 목록으로 그룹핑하면 `<repo>` 그룹에 그 세션이 있다 | 단위 — 이벤트 목록을 잘라 넣는 결정적 테스트 |
| **S3** | 워크트리는 **별도 카드가 되지 않는다** — 스냅샷 `projects[].path` 에 `/.claude/worktrees/` 를 포함한 경로가 하나도 없다 | 단위 + `hub.html` 의 `#dzh-data` JSON 파싱 |
| **S4** | 레포 루트와 워크트리 양쪽에 `dashboard.html` 이 있을 때 카드의 티어 1 은 **mtime 이 더 새로운 쪽**이다 | 단위(임시 디렉토리 트리 + `os.utime`) |
| **S5** | `build_dashboard_registry` 가 돌려주는 경로가 **S4 에서 이긴 그 파일**이다(카드 내용과 클릭 대상이 같은 파일) | 단위 — registry 값 직접 단언 |
| **S6** | 워크트리 파일이 이긴 상태에서 「이전 작업」 라벨은 **그 워크트리의 세션만** 기준으로 판정된다 | 단위 — `tier1_is_previous_task` |
| **S7** | 워크트리가 없는 프로젝트의 스냅샷은 **변경 전과 완전히 동일**하다 | 기존 375건 전량 통과 + 신규 동치 테스트 |
| **S8** | 실환경 확인 — **§7 「수동 확인(S8)」의 유효 조건을 먼저 만족시킨 뒤에** 확인한다 | 수동 확인 (2판에서 재정의) |

#### 2판 신설 — S8 이 잡은 것을 단위 테스트가 잡게 한다

> **이번 개정의 핵심이다.** S8 이 유일하게 결함을 잡았다는 것은 곧 **자동 검증이 이음매를
> 덮지 못했다**는 뜻이다. S1~S7 은 전부 `_read_tier1_for_root` 나 `_group_sessions_by_project`
> 같은 **중간 함수에 손으로 입력을 넣어** 검증됐고, 그 손 입력이 프로덕션에서는 절대 만들어지지
> 않는 값(멤버에 워크트리가 들어 있는 튜플)이었다. S9~S13 은 **입력 지점을 이벤트 쪽으로
> 끌어올린다**.

| # | 기준 | 검증 수단 |
|---|------|-----------|
| **S9** | **실패 시나리오가 그대로 성공 기준이다.** 「① 세션 `cwd` 는 레포 루트 ② 워크트리 cwd 는 **이벤트에만** 존재 ③ 워크트리에 더 새로운 `dashboard.html`」 인 **이벤트 파일**에서 시작해 `collect_snapshot` 을 돌리면 티어 1 승자가 **워크트리 파일**이다 | 단위 — 임시 디렉토리에 이벤트 `.jsonl` + 대시보드 2개를 만들고 `collect_snapshot()` 호출 (U-22) |
| **S10** | 같은 입력에서 `build_dashboard_registry` 가 돌려주는 경로가 **그 워크트리 파일**이다 (S5 를 이음매 앞으로 옮긴 것 — S5 는 손으로 만든 `ProjectView` 로 검증했다) | 단위 — U-22 가 만든 스냅샷을 그대로 넘긴다 |
| **S11** | 같은 입력에서 「이전 작업」 라벨이 **세션 시작 시각과 파일 mtime 의 실제 대소**로 판정된다. **양방향 두 케이스**로 확인한다(라벨 ON 1건 · OFF 1건) — 「live 집합이 비어서 우연히 꺼짐」은 통과로 인정하지 않는다 | 단위 — U-24·U-25 |
| **S12** | **카드 중립성**: 후보 입력을 넓혀도 프로젝트 카드 집합이 **한 개도 늘거나 줄지 않는다.** 이벤트에 프로젝트 **하위 디렉토리** cwd 가 있고 그곳에 `dashboard.html` 이 있어도 카드는 하나다(E14 가 실데이터로 이 입력의 존재를 확인했다) | 단위 — U-26 + 실데이터 대조(E15) |
| **S13** | `SessionFacts.observed_cwds[0] == SessionFacts.cwd` 가 **언제나** 참이다(내부 이벤트 필터에 걸린 이벤트를 포함해서) — 두 필드가 서로 다른 규칙으로 채워져 조용히 어긋나는 것을 막는다(결정 WT19) | 단위 — U-28 |

**S1~S7 은 유지한다.** 다만 **S4·S5 는 S9·S10 으로 대체되는 것이 아니라 보강된다** — 기존
테스트(U-14~U-17)는 그대로 두되, **그 테스트만으로 만족되는 성공 기준은 이제 하나도 없다**
(결정 WT20).

### 확정된 전제

- ~~한 세션은 언제나 **정확히 하나의 cwd** 를 갖는다~~ → **2판 정정.** 한 세션은 정확히 하나의
  **그룹 키**를 갖는다(`build_session_facts` 가 session_id 키 dict 를 반환하고
  `_group_sessions_by_project` 가 그 `cwd` 를 접어 키로 쓴다). 그래서 **중복 렌더 가능성이 0**
  이라는 결론은 그대로 유효하다. 그러나 「cwd 가 하나」는 **틀렸다** — `EnterWorktree` 는 살아
  있는 세션의 cwd 를 바꾸고(E2), 실데이터에서 한 세션이 최대 **3개**의 서로 다른 cwd 를
  관측했다(E13·E14). `SessionFacts.cwd` 는 「그 세션의 cwd」가 아니라 **「그 세션의 첫 이벤트
  cwd」**다. 이 혼동이 이번 결함의 뿌리다(결정 WT15).
- 워크트리 경로는 레포 루트 경로의 **엄격한 하위 경로**다(E8). 접기는 경로를 **짧게만** 만든다.
- `config.roots` 가 비어 있어 카드는 **오직 이벤트 cwd** 에서 생긴다. 스캔 경로 접기는
  「`roots` 를 설정한 사용자」를 위한 방어이지 이 사용자의 동작 경로가 아니다.
- 데이터 마이그레이션은 **불필요**하다 — 훅은 cwd 를 필터 없이 전부 기록해 왔고(`hub_hook.py:98`),
  수집은 2일치만 읽는다. 배포 즉시 과거 2일치가 새 규칙으로 재해석된다.

### 비목표 (이번에 하지 않는다)

| 비목표 | 이유 | 재방문 트리거 |
|--------|------|---------------|
| 티어 3(`~/.claude/projects` 인코딩 디렉토리명) 접기 | 티어 3 은 「세션도 대시보드도 없는 프로젝트」의 마지막 활동 시각 폴백이다. 워크트리에서 일하면 티어 2 세션이 이미 카드를 만든다 → 화면 기여 0. 접으면 `activity[name] = …`(`hub_collect.py:284`)를 max 병합으로, `tier3_by_path` 컴프리헨션(`:379`)도 함께 고쳐야 한다(결정 WT5) | 「2일 창 밖 워크트리의 마지막 활동 시각이 필요하다」는 요구가 실제로 생기면 |
| 관례 밖 워크트리(`git worktree add ../foo`) | 문자열 규칙으로는 원리적으로 못 잡는다. **오늘도 접히지 않고 별도 카드로 보이므로 회귀가 아니라 커버리지 미달**이다. 잡으려면 I/O 가 필수(결정 WT3) | 관례 밖 워크트리를 실제로 쓰기 시작하면 |
| 세션 줄에 「어느 워크트리인지」 표시 | `SessionView`(`hub_session.py:81-91`)에 신규 필드 + `#dzh-data` 계약 + 템플릿 + T25 검사까지 범위가 두 배가 된다. 카드 제목은 티어 1 대시보드의 `#dz-title` 을 이미 보여주므로 **무엇을 보고 있는지는 식별 가능**하다(결정 WT11) | 한 카드에 워크트리 세션이 2개 이상 동시에 도는 상황이 실제로 생기면 |
| 일반적 cwd 정규화(scratchpad·크로스 프로젝트 drift) | E7 이 밝힌 같은 뿌리(첫 이벤트가 승자)의 나머지 2/3. 해법이 서로 다르고(scratchpad 는 접을 대상이 없고, 크로스 프로젝트는 접으면 안 된다) **관측된 증상이 없다**(결정 WT2) | drift 로 세션이 사라지는 사례가 실제로 관측되면 |
| 허브가 `dashboard_enabled` 스위치를 읽는 것 | 허브 역사상 **두 번째 프로젝트 로컬 파일 계약**이 된다. 지금도 허브는 이 스위치를 전혀 읽지 않는다(결정 WT10) | 개인 off 사용자가 워크트리 대시보드 되살아남을 실제로 신고하면 |
| 진단용 CLI 출력 / 서버 JSON 엔드포인트 | `render_hub_html` 이 `HubSnapshot` 전체를 `#dzh-data` 에 심으므로 **검증 수단은 이미 있다**(결정 WT12) | — |
| `commands/dashboard.md` 변경 | 읽기 시점 병합만 하므로 **한 줄도 고칠 필요가 없다**(§9 부수 발견) | — |

---

## 3. 영향 범위

### 수정 파일

> **2판 표기 규칙.** 아래 표는 초판 내용을 지우지 않는다. 2판이 더하는 것은 **「2판」 접두**로
> 구분한다.

| 파일 | 무엇을 | 근거 결정 |
|------|--------|-----------|
| `hub/bin/hub_session.py` (★순수) — **2판 신설 대상** | `_MutableSession` 에 관측 cwd 누적 필드 1개, `_new_session_builder` 초기화 1줄, `build_session_facts` 누적 1~2줄(**내부 이벤트 필터보다 앞**), `_freeze_session` 동결 1줄, `SessionFacts` 에 `observed_cwds` 필드 1개. **약 +8줄.** `hub_project` 를 임포트하지 않는다(T25-102) — 접기는 여기서 하지 않고 **원본 cwd 만** 모은다 | **WT16·WT19** |
| `hub/bin/hub_project.py` (★순수) | 상수 1개 + 순수 함수 4개 신설(`fold_worktree_path`·`group_paths_by_repo_root`·`select_tier1_source`·`plan_tier1_candidates`, 마지막은 검수 1회차 M1), `_live_session_start_times_ms` 에 인자 1개 추가, `compose_project_views` 안 3줄 · **2판**: `plan_tier1_candidates` 본문의 `observed_paths` 산출을 `facts.observed_cwds` 로 바꾸고 **앵커 조건 1줄 추가**(약 +5/−2줄, **시그니처 무변경**), `_live_session_start_times_ms` 의 비교를 `==` 에서 `in` 으로(1줄, **시그니처 무변경**) | WT3·WT6·WT9, M1 · **WT16·WT17·WT18** |
| `hub/bin/hub_parse.py` (★순수) | `Tier1Snapshot` 에 `source_path` 필드 1개 + `UNSET_SOURCE_PATH` 상수 1개 | WT7 |
| `hub/bin/hub_collect.py` (I/O) | `_group_sessions_by_project` 그룹 키 접기, `read_tier1_snapshot` 이 `source_path` 도 채움, `_read_tier1_for_root`(검수 1회차 m2 로 `root` 인자 제거) + `_collect_tier1_snapshots`(검수 1회차 M1 신설) 신설, `collect_snapshot` 후보 조립을 `plan_tier1_candidates` 호출로 축소 | WT4·WT5·WT6, M1·m2 |
| `hub/bin/hub_model.py` (★순수) | `build_dashboard_registry` — `tier1.source_path` 사용 + `tier1 is None`·`UNSET_SOURCE_PATH` 방어 가드와 그 사유 주석(메인 세션 검토 지적 반영). 초판은 「2줄」로 예상했으나 실제 9줄 | WT8 |
| `tests/hub/test_hub_session.py` — **2판 신설 대상** | `ObservedCwdsTest` 신규 클래스(U-28·U-29) — `observed_cwds` 누적·중복 제거·순서·`[0] == cwd` 불변식, 내부 필터 이벤트도 기여하는지 | §7 |
| `tests/hub/test_hub_project.py` | 신규 클래스 4개(`FoldWorktreePathTest`·`GroupPathsByRepoRootTest`·`PlanTier1CandidatesTest`[검수 1회차 M1]·`SelectTier1SourceTest`) + GN 테스트 보강 · **2판**: `PlanTier1CandidatesTest` 에 U-27·U-30 추가, GN 테스트에 U-24 추가, `SessionFacts` 픽스처 8곳에 `observed_cwds` 명시 | §7 |
| `tests/hub/test_hub_collect.py` | 신규 클래스 3개(`WorktreeFoldGroupingTest`·`Tier1SourceSelectionTest`·`CollectTier1SnapshotsTest`[검수 1회차 M1]). **기존 `Tier3IgnoreFilterTest` 는 무변경**(티어 3 을 접지 않으므로) · **2판**: `CollectSnapshotWorktreeTier1Test` 신규 클래스(U-22·U-23·**U-24**·U-25·U-26) — **이벤트 파일에서 시작하는 유일한 티어 1 테스트**다(결정 WT20). U-24 는 이 클래스와 `test_hub_project.py` 의 GN 테스트 **양쪽**에 둔다(검수 3회차: 뮤테이션 11 에서 둘 다 반응하는 이중 레이어) | §7 |
| `tests/hub/test_hub_model.py` | `build_dashboard_registry` 가 `tier1.source_path` 를 쓰는지 단언 | §7 |
| `tests/hub/test_hub_parse.py` | 파서가 `source_path` 를 `UNSET_SOURCE_PATH` 로 남기는지 단언 | §7 |
| `tests/hub/test_hub_server.py` | `tier=1` 인데 `tier1=None` 인 픽스처를 실제 `Tier1Snapshot` 으로 교체. **초판이 누락한 파일이다** — `build_dashboard_registry` 의 `tier1 is None` 가드가 신설되면서 그 픽스처가 registry 를 비게 만들어 반드시 고쳐야 했다(재검수 2회차 지적) | WT8 |
| `tests/run.sh` | T25-111~T25-114 신설(검수 1회차 M2 로 `note_failure` 누적형 전환) · **2판**: T25-115~T25-118 신설(전부 `note_failure` 누적형) | §7 |
| `hub/README.md` | 티어 표(`:340`) 출처 문구 + `ignore_globs` 행(`:359`) 주석 | §6 |

### 미영향 — 건드리지 않는 이유 (전수 확인)

| 대상 | 확인 결과 |
|------|-----------|
| `hub.py`·`hub_daemon.py`·`hub_settings.py`·`hub_statusline.py`·`hub_usage.py`·`hub_usage_fetch.py`·`hub_server_state.py` **7개** | `cwd`·`worktree`·`project_path`·`project_root`·`ignore_globs`·`encode_project`·`ProjectView`·`projects` **8개 심볼 grep 전부 0건**. 프로젝트 경로 개념을 아는 모듈은 `hub_project.py`·`hub_collect.py` **둘뿐**임이 전수로 확인됐다 |
| `hub/bin/hub_template.html` | 결정 WT11 — 새 필드는 `#dzh-data` JSON 에 실리지만 템플릿은 읽지 않는다. `SessionView`·`ProjectView` 무변경이라 렌더 경로가 그대로다 |
| `hub/bin/hub_server.py` | 라우트 정규식(`^/project/([0-9a-f]{16})/dashboard\.html$`)·`ALLOWED_REQUEST_PATHS` 무변경. registry 의 **값만** 바뀌고 키 계산(`sha256(project.path)`)은 그대로다 |
| ~~`hub/bin/hub_session.py`~~ | 초판: 「`SessionFacts.cwd` 를 **재작성하지 않는다** — 접기는 그룹 키에서만 일어난다(결정 WT5). 원본 cwd 는 GN 판정에 그대로 필요하다」 → **2판에서 「미영향」이 아니게 됐다.** `cwd` 재작성 금지는 **그대로 유효**하지만(결정 WT19 가 WT14 를 재확인한다), 관측 cwd 집합을 담을 필드가 **추가**된다. 위 「수정 파일」 표로 옮겼다 |
| `hub/bin/hub_hook.py` | 훅은 payload cwd 를 가공 없이 기록한다. 이벤트 스키마 무변경 |
| `hub/install.sh` · `hub/README.md:18`·`:384` · `tests/run.sh:3881-3886` | **새 모듈을 만들지 않으므로** 「15개 파일」 리터럴 4곳 전부 무변경(결정 WT13) |
| `commands/dashboard.md` (1679줄) | 읽기 시점 병합이라 쓰기 쪽 계약(`data-owner-token`·`data-server-port`·포트 스캔)이 전부 그대로다 |
| `~/.claude/hub/config.json` | 사용자 config 를 고치라고 요구하지 않는다(결정 WT4) |
| `tests/hub/fixtures/` | `hub_parse` 의 파싱 로직을 안 건드린다 — 새 HTML fixture 불필요 |

---

## 4. 결정 기록

### 결정 WT2 — 범위: fold + 티어 1 출처 확장을 **한 PRP 로 묶되, 2단계로 구현**한다

| 안 | 내용 | 트레이드오프 |
|----|------|--------------|
| 안 1 | fold 만 | 결함 B 만 고치고 **결함 A(지금 라이브)는 그대로**. 사용자가 보는 증상(어제 100% + 「이전 작업」 상시 점등)이 하나도 안 바뀐다 |
| 안 2 | 티어 1 확장만 | 결함 A 는 고쳐지지만 **flip 이 오면 카드째 사라져** 티어 1 도 같이 사라진다. 또 티어 1 후보 목록을 만들려면 「어느 워크트리가 이 레포 소속인가」가 필요한데 그게 곧 fold 다 |
| **안 3(권고)** | **둘 다, 단계 1 → 단계 2 순서로** | 단계 1 이 만드는 `group_paths_by_repo_root` 의 **멤버 목록이 곧 단계 2 의 티어 1 후보**다. 두 단계가 같은 자료구조를 공유하므로 나눠 만들 이유가 없다. 대신 단계 1 만으로도 테스트가 전부 통과하는 상태를 거쳐 커밋 경계를 남긴다 |

**근거**: 조사가 티어 1 확장을 「분리 가능하지만 생략 불가」로 판정했고, E4 가 그것을 **지금 라이브인
결함**으로 확정했다. 승인자가 범위를 줄이고 싶다면 **단계 2 를 잘라내는 것**이 유일하게 일관된
절단선이다(승인 요청 항목 1).

### 결정 WT3 — 판정은 **순수 문자열 마커 절단**이다. git 호출도 `.git` 파일 읽기도 하지 않는다

```python
WORKTREE_PATH_MARKER = "/.claude/worktrees/"
```

| 안 | 정확도 | 비용 | 계층 |
|----|--------|------|------|
| **안 A(권고) 문자열 마커 절단** | 관례 경로 100%(E8). 관례 밖 워크트리는 못 잡음 | **0** | `hub_project.py`(★순수) — 단위 테스트가 가장 싸다 |
| 안 B `<worktree>/.git` 평문 파일 읽기 | 관례 밖도 잡음. 서브모듈 워크트리에서 부정확 | 수집 사이클(5초)마다 후보 수만큼 `open`+`read` | `hub_collect.py` 로 강제 이동 |
| 안 C `git rev-parse --git-common-dir` | 가장 정확 | **5초마다 워크트리 수만큼 fork** | `hub_collect.py` + 실패 경로 신설 |

**근거**: `hub_project.py:3` 의 ★순수 계약(「파일시스템·시각·환경변수에 닿지 않는다」)은 관례가
아니라 `tests/run.sh:2356-2363`(T25-10)이 `grep -qE 'open\(|Path\(|os\.'` 로 기계 강제한다.
`os.path.dirname` 조차 걸린다. 안 A 는 `str.find` + 슬라이스만 쓰므로 이 가드를 자연히 통과한다.

> **주의(구현자에게)**: 그 grep 은 `subprocess.run(`·`subprocess.check_output(` 은 **통과시킨다**
> (실측). 「테스트가 안 막으니 넣어도 된다」로 가지 마라 — 진짜 계약은 docstring 이다.

**절단 방향은 `find`(첫 번째 마커)다.** 중첩 워크트리 `/a/repo/.claude/worktrees/w1/.claude/worktrees/w2`
에서 첫 마커로 자르면 `/a/repo`(최외곽 레포)까지 한 번에 접히고, 마지막 마커(`rfind`)로 자르면
`/a/repo/.claude/worktrees/w1` — **여전히 워크트리 경로**라 뒤이은 ignore 에 걸려 세션이 통째로
사라진다. 실측으로 두 결과가 다름을 확인했다.

### 결정 WT4 — **fold → ignore** 순서. `ignore_globs` 기본값도 사용자 config 도 손대지 않는다

| 안 | 이 사용자에게 켜지는가 | 접기 실패 시 | 비용 |
|----|----------------------|--------------|------|
| **안 A(권고) 기본값 유지 + fold 를 ignore 앞에** | **켜진다**(config 내용과 무관) | 워크트리가 **오늘처럼 조용히 숨는다**(안전 실패) | 0 |
| 안 B 기본값에서 워크트리 glob 제거 | **안 켜진다** | 워크트리가 **별도 카드로 나타난다**(사용자가 명시적으로 원하지 않는 결과) | 사용자 config 편집 안내 필요 |
| 안 C `fold_worktrees: bool` 신설 | 켜진다 | 선택 가능 | `HubConfig`·`_CONFIG_FIELD_TYPES`·`hub/README.md` 표 동시 변경 + 요청되지 않은 설정 가능성(YAGNI) |

**근거 (실측)**: `config.json` 의 `ignore_globs` 는 기본값과 **병합되지 않고 통째로 대체된다**
(`hub_collect.py:107` → `:124`). 그리고 이 사용자의 실제 config 에는 기본값 3개가 복제된 뒤
`/Users/byron` 이 추가돼 있다. **기본값만 고치는 안 B 는 요구를 낸 당사자에게 도달하지 못한다.**

**부작용을 정직하게 적는다**: fold-first 로 가면 `**/.claude/worktrees/**` 는 **티어 1·2 경로에
대해 죽은 패턴**이 된다(접힌 루트는 이 glob 에 절대 매칭되지 않는다 — E9). 즉 「워크트리를 허브에서
빼고 싶다」는 손잡이가 사라진다. 그 손잡이를 살리는 안 C 를 **채택하지 않는 이유**는, 요구를 낸
당사자가 정확히 반대 방향을 요청했고 지금 필요 없는 설정 가능성을 미리 만들지 않기 위해서다(YAGNI).
그 glob 은 **티어 3 인코딩명 필터에서는 계속 살아 있다**(티어 3 을 접지 않으므로 — 결정 WT5).

**`/tmp` 가드는 안전하다**(E9): `/private/tmp/x/scratch-repo/.claude/worktrees/w` 는 접으면
`/private/tmp/x/scratch-repo` 이고 이는 여전히 `/private/tmp/**` 에 걸린다.

### 결정 WT5 — 개입 지점은 **두 곳**. 티어 3 은 접지 않는다

`ignore_globs` 는 서로 다른 **세 지점**에 적용된다. 티어별로 개입 여부를 각각 못 박는다.

| 티어 | 적용 지점 | 개입 | 순서 |
|------|-----------|------|------|
| 티어 2 (세션 그룹핑) | `hub_collect.py:205`(ignore) → `:207`(그룹 키) | **한다** — `fold_worktree_path(facts.cwd)` 를 먼저 계산하고 **그 결과로** `should_ignore_cwd` 를 호출한 뒤 **접힌 값을 그룹 키로 쓴다** | fold → ignore → group |
| 티어 1 (후보 경로) | `hub_collect.py:359-363` | **한다** — 관측 경로 전체를 `group_paths_by_repo_root` 로 묶고, **접힌 루트에만** ignore 를 적용한다 | fold → ignore |
| 티어 3 (인코딩 디렉토리명) | `hub_collect.py:276` | **하지 않는다** | 무변경 |

**ignore 는 접힌 루트에만 적용한다** — 멤버(워크트리 경로)에 개별 적용하면 전부 glob 에 걸려
티어 1 후보 확장이 그 자리에서 죽는다. 이것이 fold-first 순서의 실질적 내용이다.

**티어 3 을 접지 않는 이유**: (a) 화면 기여 0 — 워크트리에서 일하면 티어 2 세션이 이미 카드를
만든다. (b) 접으면 `activity[entry.name] = …`(`:284`)이 **뒤엣것이 앞엣것을 덮어쓰는** 대입이라
max 병합으로 바꿔야 하고, `tier3_by_path` 컴프리헨션(`:379`)도 같은 문제를 갖는다. (c) 기존 테스트
`test_worktree_and_tmp_encoded_names_are_excluded`(`tests/hub/test_hub_collect.py:169-178`)를
**뒤집지 않아도 된다** — 접지 않기로 하면 그 단언이 그대로 참으로 남고, 그 glob 도 계속 의미를 갖는다.

### 결정 WT6 — 티어 1 승자는 **mtime 최신**, 동률이면 **레포 루트**

| 안 | 결과 | 채택 여부 |
|----|------|-----------|
| 레포 루트 고정 | 결함 A 가 그대로 남는다(E4). 「워크트리 진행률을 보고 싶다」는 요구의 정확한 반대 | ✕ |
| **mtime 최신(권고)** | 「이 레포에서 **가장 최근에 갱신된 대시보드**」라는 한 줄로 설명되는 규칙. 결정적·순수·테스트 가능 | **○** |
| 레포 루트 우선 + 히스테리시스 | 승자 요동을 줄이지만 「얼마나 더 새로워야 하는가」라는 임의 상수가 새로 필요하고, 그 상수를 정할 측정치가 없다 | ✕ (YAGNI, P-2 로 관리) |
| 후보 N개 노출 | `ProjectView.tier1` 단수 → 복수, 라우트 정규식(키 1 : 대시보드 1), 패널 UI 재설계까지 번진다 | ✕ (범위 초과) |

**동률 처리**: 후보 목록을 **`(레포 루트, 워크트리…)` 순서**로 만들고 `max(candidates, key=…)` 를
쓴다. 파이썬 `max` 는 **동률일 때 앞의 것을 돌려주므로** 레포 루트 우선이 자료 순서에서 자연히
떨어진다. 이 성질에 암묵적으로 기대지 않도록 **동률 테스트로 못 박는다**(§7 U-9).

**버려진 워크트리 문제**(디렉토리는 남았지만 아무도 안 쓰는 워크트리의 낡은 대시보드가 계속 이기는
경우)는 성립하지 않는다 — 버려진 파일은 mtime 이 갱신되지 않으므로 레포 루트가 한 번이라도 갱신되면
곧바로 진다. **살아 있는 두 대시보드가 번갈아 이기는 요동**만 실제 위험이고, 그것은 P-2 로 관리한다.

> **→ 재확인(2판, 결정 WT21).** 규칙 자체는 흔들리지 않는다. 바뀌는 것은 **발동 시점**이다 —
> 초판 구현에서는 워크트리가 후보에 들어가는 일이 사실상 없었으므로(E11) 이 규칙이 한 번도
> 실제로 작동한 적이 없다. 2판 이후에는 **배포 즉시 워크트리 파일이 이긴다**(E15 로 확인).
> 따라서 P-2(승자 요동)는 「이론적 위험」에서 **「즉시 활성」**으로 승격된다.

### 결정 WT7 — 티어 1 출처 경로는 `Tier1Snapshot.source_path` 로 실어 나른다

```python
# hub_parse.py
UNSET_SOURCE_PATH = ""      # file_mtime_ms 와 같은 계열 — I/O 레이어가 replace 로 채운다

@dataclass(frozen=True)
class Tier1Snapshot:
    ...
    file_mtime_ms: int
    source_path: str = UNSET_SOURCE_PATH   # 이 스냅샷을 읽어 온 dashboard.html 의 **소유 디렉토리**
```

| 안 | 비용 | 판단 |
|----|------|------|
| **안 A(권고) `Tier1Snapshot.source_path`** | 필드 1개 + 상수 1개. `compose_project_views` **시그니처 무변경**. 기존 Tier1Snapshot 생성 5곳이 전부 키워드 인자라 **기본값만 주면 무변경**(실측) | **○** |
| 안 B `ProjectView.tier1_source_path` | `compose_project_views` 에 인자 1개 추가 + **네 번째 `path -> 값` 병렬 dict**. tier1 과 반드시 동기화돼야 하는 값을 따로 들고 다니는 구조 | ✕ |

**근거**: `hub_parse.py:15-17` 이 **바로 이 패턴의 선례를 명시적으로 적어 두었다** —
「`file_mtime_ms` 는 이 모듈이 채우지 않는다. I/O 레이어(hub_collect.py)가 stat 으로 얻은 실제
mtime 을 `dataclasses.replace` 로 덮어쓴다」. 경로 **문자열**을 담는 것은 파일시스템에 **닿는** 것이
아니므로 ★순수 계약(`hub_parse.py:3`)과 충돌하지 않는다.

**저장하는 값은 파일 경로가 아니라 소유 디렉토리다.** `<dir>/.claude/dashboard.html` 의 상대경로
상수(`PROJECT_DASHBOARD_RELATIVE_PATH`)는 이미 정본이 하나뿐이므로(`hub_project.py:18-23`), 결정을
한 번만 내리고 나르는 목적은 **디렉토리**를 나르는 것으로 충분하다. 이렇게 하면 GN 판정(결정 WT9)이
`facts.cwd == tier1.source_path` 라는 **직접 비교 한 줄**이 된다(경로에서 디렉토리를 되뽑는 헬퍼 불필요).

### 결정 WT8 — `build_dashboard_registry` 는 경로를 **재조립하지 않고** `tier1.source_path` 를 쓴다

```python
# 변경 전: registry[project_dashboard_key(project.path)] = project.path + "/" + PROJECT_DASHBOARD_RELATIVE_PATH
# 변경 후: registry[project_dashboard_key(project.path)] = project.tier1.source_path + "/" + PROJECT_DASHBOARD_RELATIVE_PATH
```

**키는 그대로 `project.path`(접힌 레포 루트)다.** 카드의 신원(`data-project-path`)·카드 순서
localStorage·패널 신원이 전부 이 문자열에 묶여 있고(결정 OC1), 워크트리 경로는 **지금까지 한 번도
렌더된 적이 없으므로** 기존 사용자의 저장 상태를 깨뜨리지 않는다.

**결정 N3(핸들러는 요청 문자열로 경로를 만들지 않는다)은 유지된다** — 값은 여전히 `collect_snapshot`
이 실제로 발견하고 `is_file()` 로 확인한 경로에서만 나온다. traversal 차단 논거를 다시 세울 필요가 없다.

이 결정을 빠뜨리면 **카드에 보이는 진행률과 클릭해서 열리는 파일이 다른 파일**이 되는 조용한 불일치가
성립한다. 저장소가 가장 싫어하는 실패 모드다(「경로를 지어내지 않는다」와 같은 계열).

### 결정 WT9 — GN1 의 live 세션 집합을 **티어 1 출처와 같은 cwd** 로 좁힌다 (GN2 개정)

```python
def _live_session_start_times_ms(sessions, session_views, tier1_source_path: str) -> tuple[int, ...]:
    return tuple(
        facts.started_at_ms
        for facts, view in zip(sessions, session_views)
        if view.state in LIVE_SESSION_STATES and facts.cwd == tier1_source_path
    )
```

**이것은 축소가 아니라 정정이다.** `is_tier1_from_previous_task` 는 「이 그룹의 살아 있는 세션이
곧 이 파일을 갱신하는 주체」를 전제한다. `/dashboard` 는 **cwd 상대경로**에만 쓰므로
(`commands/dashboard.md:449`), 파일 `<D>/.claude/dashboard.html` 을 갱신하는 세션은 **cwd 가 정확히
`<D>` 인 세션뿐**이다. 좁힌 집합이 곧 그 전제의 정확한 표현이다.

**비워크트리 프로젝트에서는 완전한 무동작이다** — 접기 전에는 그룹 키 = cwd = 티어 1 출처였으므로
`facts.cwd == tier1.source_path` 가 항상 참이다. 즉 이 변경은 **엄격한 일반화**이고 기존 GN 표
(`hub-session-revival-and-stale-tier1.md:266-290`, 8행)의 판정 결과를 하나도 바꾸지 않는다.

좁히지 않으면: 워크트리 세션이 레포 루트 파일 mtime 이후에 시작했다는 이유만으로 레포 카드에
「이전 작업」이 붙는(또는 반대로 안 붙는) **우연**이 된다.

| 대안 | 기각 사유 |
|------|-----------|
| 워크트리 세션을 live 집합에서 통째 제외 | 승자가 워크트리 파일일 때 **아무도 그 파일의 세대를 판정하지 못한다** |
| 라벨을 포기(항상 False) | 결정 GN1~GN3 이 해결한 실제 문제(좀비 stale 세션의 세대 오염)를 되돌린다 |

> **→ 재개정(2판, 결정 WT18).** 위 원칙(「파일을 갱신하는 주체는 그 cwd 의 세션뿐」)은 옳지만
> **비교 대상이 틀렸다.** `facts.cwd` 는 그 세션의 **첫 이벤트** cwd 이지 「그 세션의 cwd」가
> 아니다(E1). 워크트리로 들어간 세션은 `facts.cwd` 가 레포 루트로 남아 있어, 승자가 워크트리
> 파일이면 **일치하는 세션이 하나도 없다** — 실측으로 live 집합이 **0** 이 됐다(E15). 그러면
> `is_tier1_from_previous_task` 의 `if not live: return False` 분기를 타 **라벨이 우연히
> 꺼진다.** 지금 화면에서는 답이 맞지만 근거가 틀렸고, 인접한 경우(워크트리 파일이 먼저 쓰이고
> 그 뒤에 세션이 워크트리로 들어온 경우)에는 **답 자체가 틀린다.** 비교를
> `tier1.source_path in facts.observed_cwds` 로 바꾼다.

### 결정 WT10 — `dashboard_enabled` 스위치는 이번에도 **읽지 않는다** (현행 유지 + 문서화)

| 안 | 코드 비용 | 위험 |
|----|-----------|------|
| **안 A(권고) 무시 + 문서화** | **0** | 개인 off 사용자에게 워크트리 대시보드가 티어 1 로 되살아난다 |
| 안 B 워크트리 파일을 티어 1 후보에서 제외 | registry·`ProjectView` 무변경 | **결함 A 를 안 고친다** — 이 PRP 의 절반이 사라진다 |
| 안 C 허브가 소유 레포 루트의 `settings.local.json` 을 읽음 | 허브 역사상 **두 번째 프로젝트 로컬 파일 계약** + T23-7(`tests/run.sh:2192-2197`) 확장 필수 | 규범이 「코드가 신뢰하는 사실」로 승격된다 |

**위험 범위가 실측으로 좁혀진다.** off 스위치는 둘이고 워크트리 전파성이 정반대다.

- **팀 단위 off**(CLAUDE.md 항목 삭제·주석) = **커밋 대상 → 워크트리에 그대로 전파**된다.
  이 경우 워크트리 세션도 애초에 `/dashboard` 를 부르지 않아 파일이 생기지 않는다 → **안전**.
- **개인 off**(`.claude/settings.local.json`) = `.gitignore:6` 등재 → 워크트리에 존재하지 않는다
  → 워크트리 세션은 켜진 채로 돈다 → **손상 시나리오는 여기 하나뿐이다.**

또한 **허브는 오늘도 이 스위치를 모른다**(`grep -rn dashboard_enabled hub/` → 0건). 개인 off 를 눌러도
기존 `dashboard.html` 은 지워지지 않으므로 카드는 지금도 티어 1 로 뜬다. 이번 변경은 **새로운 종류의
문제를 만드는 것이 아니라 기존 간극을 넓힌다** — 정직하게 그렇게 적는다.

「워크트리마다 다시 off 를 누르면 된다」는 완화책은 **제시하지 않는다** — 그 파일은 커밋 불가이고
워크트리와 함께 사라진다(실측 `git check-ignore -v`).

### 결정 WT11 — 화면 표시는 **한 줄도 바꾸지 않는다**

`hub_template.html`·`SessionView`·`ProjectView` 무변경. 「지금 보고 있는 것이 어느 워크트리의
진행률인가」는 **티어 1 대시보드의 제목(`#dz-title`)이 이미 카드에 렌더되므로** 식별 가능하다
(E4 의 두 제목이 서로 완전히 다르다). 카드 이름은 `_display_name(레포 루트)` 라 **오염되지 않는다**.

새 필드(`source_path`)는 `#dzh-data` JSON 에 실리지만 템플릿이 읽지 않으므로 화면 영향 0 이다.
`snapshot_content_key` 에도 실리지만 **시간에 무관한 안정값**이라 매 사이클 `hub.html` 재작성을
유발하지 않는다.

### 결정 WT12 — 검증은 **순수 단위 테스트 + `#dzh-data` JSON**. 진단 CLI 를 만들지 않는다

- `hub.py collect --json` 은 `projects` 를 **개수로만** 낸다(`hub.py:57-62`). 게다가 개수는
  fold 검증에 **애매한 신호**다 — 레포 루트가 이미 카드면 fold 후에도 그대로고, 없으면 +1 이다.
- `cmd_status` 는 프로젝트 정보를 전혀 내지 않는다(`hub.py:211-243`). 서버에도 JSON 엔드포인트가
  없다(`hub_server.py:27`).
- **그러나** `render_hub_html` 이 `json.dumps(asdict(snapshot))` 로 `HubSnapshot` 전체를
  `#dzh-data` 에 심는다(`hub_model.py:77-91`). 최소 템플릿으로 render → payload 를 잘라
  `json.loads` → `parsed["projects"][0][...]` 를 단언하는 패턴이 **이미 5개 테스트 파일에 있다**.

따라서 새 인프라 없이 S1~S7 을 전부 자동 검증할 수 있다. 진단 출력 추가는 배제한다(YAGNI).

### 결정 WT13 — **새 모듈을 만들지 않는다**

fold 로직은 순수 함수 3개(약 25줄)다. 새 모듈로 빼면 `hub/install.sh:12 HUB_FILE_COUNT=15` ·
`hub/README.md:18` · `hub/README.md:384` · `tests/run.sh:3881-3886` **네 곳의 리터럴**을 동시에
고쳐야 하고, `tests/run.sh:3881` 의 grep 은 **하드코딩된 문자열**이라 자동 추종하지 않는다.
25줄을 위해 배포 게이트를 흔들 이유가 없다.

> 비대칭 기록: `hub/install.sh` 는 복사만 하고 대상의 잔존 파일을 지우지 않는데(`:106-113`) 검증은
> **대상 디렉토리**의 파일 수를 센다(`:95-102`). 그래서 **파일 수를 늘리는 쪽보다 줄이는 쪽이 훨씬
> 비싸다**(재설치가 「기대 N개, 실제 N+1개」로 실패하고 rollback 이 없다). 이번 안은 어느 쪽도 아니다.

### 결정 WT14 — 세션 `cwd` 자체는 재작성하지 않는다

접기는 **그룹 키에서만** 일어난다. `SessionFacts.cwd`(원본 워크트리 경로)는 그대로 살아 있어야
결정 WT9 의 출처 대조가 가능하다.

| 대안 | 기각 사유 |
|------|-----------|
| `_new_session_builder` 진입 전 이벤트 cwd 정규화 | 원본이 영구 소실 → WT9 불가능. `hub_session.py`(★순수) 계약도 함께 바뀐다 |
| `SessionFacts.cwd` 를 **마지막 이벤트 cwd** 로 변경 | flip 을 반대 방향으로 뒤집을 뿐이다 — 지금 레포 루트로 보이는 세션이 **즉시** 워크트리로 이동해 사라진다 |
| 「창 안 최초의 **비무시** cwd」 로 변경 | flip 을 못 막는다 — 창이 굴러 **모든** 이벤트가 워크트리가 되면 비무시 후보가 0 이 된다(실측 시나리오 E5 가 정확히 그 경우다) |

> **→ 재확인(2판, 결정 WT19).** WT14 는 **번복되지 않는다.** 위 표의 기각 사유 세 줄은 전부
> 그대로 유효하고, `SessionFacts.cwd` 는 여전히 「창 안 최초 이벤트의 cwd」로 남는다. 2판이
> 하는 일은 **덮어쓰기가 아니라 덧붙이기**다 — 관측된 cwd 들을 담는 **새 필드**가 생긴다.

---

## 4-2. 결정 기록 (2판 — S8 실패 반영)

### 결정 WT15 — 결함 A 의 병목은 **리더가 아니라 후보 목록의 입력**이다 (진단 정정)

초판의 인과 사슬은 이랬다.

```
결함 A(카드가 어제 파일을 가리킨다)
  → 원인: read_tier1_snapshot 이 프로젝트 경로 하나만 읽는다
  → 해법: 후보를 여러 개 읽고 mtime 최신을 고른다(WT6·WT7)
```

**두 번째 줄이 틀렸다.** 리더는 후보 목록을 받아 읽을 뿐이고, 그 목록을 만드는 것은
`plan_tier1_candidates` 다. 그 함수의 입력은 `sessions_by_path` 의 값에서 뽑은
`{facts.cwd}` 하나뿐인데(현행 `hub_project.py:140`), `SessionFacts.cwd` 는 창 안 **최초
이벤트**로 고정되고(E1) `EnterWorktree` 는 **살아 있는 세션의 cwd 를 도중에 바꾼다**(E2).
따라서 워크트리 경로는 **이벤트에는 기록돼 있지만 `SessionFacts` 에는 남지 않아 후보 목록에
오를 길이 원리적으로 없다**(E11 로 직접 확인).

올바른 사슬은 이렇다.

```
결함 A
  → 원인: 티어 1 후보 목록의 입력이 SessionFacts.cwd 뿐이고,
          그 값은 세션의 cwd 가 아니라 세션의 "첫 이벤트 cwd" 다
  → 해법: 관측된 cwd 를 잃지 않고 후보 입력까지 나른다(WT16)
```

**초판이 왜 이걸 놓쳤는지도 기록해 둔다.** E4 가 상황을 정확히 관측했다 — 「루트 파일은 읽히고
워크트리 파일은 안 읽힌다」. 그 관측에서 **읽기 쪽**으로 시선이 갔고, **후보가 애초에 생기지
않는다**는 앞 단계를 확인하지 않았다. E4 를 얻은 방법(`read_tier1_snapshot()` 을 **두 경로에
손으로** 호출)이 이미 「경로 두 개는 이미 있다」를 전제하고 있었다 — **측정 방법이 결론을
미리 정한 경우**다. 2판의 E11 은 같은 사실을 `load_config` → `collect` 순서 그대로 실행해
확인했고, 그래서 후보 목록이 비어 있음이 드러났다.

### 결정 WT16 — 워크트리 경로는 **`SessionFacts.observed_cwds`** 로 나른다 (쟁점 1)

```python
# hub_session.py (★순수)
@dataclass(frozen=True)
class SessionFacts:
    session_id: str
    cwd: str                        # 창 안 최초 이벤트의 cwd (결정 WT14 — 그대로 유지)
    observed_cwds: tuple[str, ...]  # 이 창에서 관측된 모든 cwd, 첫 관측 순, 중복 제거
    ...
```

| 안 | 결함 A 를 고치는가 | 쟁점 3(GN 판정)을 고치는가 | 계층 | 비용 | 판단 |
|----|-------------------|---------------------------|------|------|------|
| **(a)** 이벤트 원본 cwd **집합**을 후보 입력에 포함 | ○ | **✕** — 집합에는 **어느 세션의 cwd 인지**가 없다. `_live_session_start_times_ms` 는 세션마다 판정해야 한다 | `hub_collect` → `hub_project` 로 인자 추가 | `plan_tier1_candidates` **시그니처 변경** + `collect_snapshot` 배선 | ✕ |
| **(b)** 레포 루트의 `.claude/worktrees/` 디렉토리 스캔 | ○ | ✕ (같은 이유) | **★순수에서 못 한다** — `hub_collect` 로 내려간다(T25-10 이 `Path(`·`os.` 를 기계 차단) | 수집 주기(5초)마다 디렉토리 I/O. **이벤트 없는 워크트리까지 상시 후보**가 돼 P-2 표면적이 넓어진다 | ✕ |
| **(c) 권고** `SessionFacts` 에 관측 cwd 집합 | ○ | **○** — 세션별로 붙어 있으므로 `source_path in facts.observed_cwds` 한 줄 | `hub_session.py`(★순수) 안에서 끝난다. `hub_project` 임포트 불필요(T25-102 안전) | 필드 1개(+8줄). **`plan_tier1_candidates`·`_live_session_start_times_ms` 시그니처 무변경** | **○** |

**권고 근거 1 — (a)·(b)는 쟁점 3 을 구조적으로 못 고친다.** 두 안 모두 「이 레포에 워크트리
경로가 있다」는 **레포 단위** 사실만 준다. 그런데 「이전 작업」 라벨은 **세션 단위** 판정이다
(어느 세션이 이 파일을 갱신하는 주체인가). 실측이 이 차이를 드러냈다(E15): (a) 방식에서는
live 집합이 **0** 이라 라벨이 `if not live: return False` 분기로 **우연히** 꺼지고, (c)
방식에서는 live 집합이 **1** 이라 **실제 대소 비교**(세션 시작 `09:50` < 파일 mtime `13:04`)로
꺼진다. 오늘은 둘 다 「꺼짐」이지만, 워크트리 파일이 먼저 쓰이고 그 뒤 세션이 워크트리로 들어온
경우에는 라벨이 **켜져야 하고** (a)는 그때도 꺼진 채로 남는다.

**권고 근거 2 — (c)만 ★순수 계약 안에서 끝난다.** (b)는 디렉토리 스캔이라 `hub_project.py`
(★순수)에 둘 수 없고 `hub_collect.py` 로 내려간다. 그러면 접기·후보 판정이 I/O 레이어로 흩어져
단위 테스트에 디렉토리 트리 빌더가 필요해진다 — 결정 WT3 이 이미 같은 이유로 안 B·C 를 기각했다.

**권고 근거 3 — 데이터가 이미 있고 I/O 증가가 0 이다.** 훅은 cwd 를 필터 없이 전부 기록해 왔다
(`hub_hook.py:98`). (c)는 **이미 읽고 있는 이벤트**를 버리지 않는 것뿐이다. 새 파일 읽기 0회,
새 서브프로세스 0회. 티어 1 읽기 횟수는 **실제 워크트리 수만큼만** 는다(실측: 4 → 5, E13).

**(b)를 완전히 배제하지는 않는다.** (b)의 고유 능력은 **이벤트가 없는 워크트리**를 잡는 것인데,
이 사용자에게 그런 워크트리는 **0건**이다(`.claude/worktrees/` 에 디렉토리 1개, 그 워크트리에서
이벤트가 나온다 — 실측). 지금 필요 없는 능력이므로 YAGNI 로 미룬다. 「2일 창 밖의 워크트리
대시보드를 카드에 띄우고 싶다」는 요구가 실제로 생기면 재방문한다.

**메모리·직렬화 영향은 0 이다.** `SessionFacts` 는 `#dzh-data` 에 실리지 않는다 — 스냅샷에 담기는
세션 타입은 `SessionView` 이고 거기엔 `cwd` 자체가 없다(실측). 따라서 템플릿·`snapshot_content_key`·
`ProjectView` 필드 순서 검사(T25-87) 어느 것도 건드리지 않는다.

### 결정 WT17 — 관측 cwd 는 **멤버만 늘리고 루트를 새로 만들지 않는다** (앵커 규칙)

```python
# hub_project.plan_tier1_candidates — 시그니처는 그대로다
anchors = set(sessions_by_path) | {fold_worktree_path(p) for p in scanned_paths}
observed = {p for group in sessions_by_path.values() for facts in group for p in facts.observed_cwds}
members_by_root = group_paths_by_repo_root(sorted(observed | set(scanned_paths)))
return {
    root: members
    for root, members in members_by_root.items()
    if root and root in anchors and not should_ignore_cwd(root, ignore_globs)
}
```

**이 한 줄(`root in anchors`)이 없으면 후보 확장이 카드를 만들어 낸다.** `tier1_by_path` 의 키는
`compose_project_views` 에서 곧바로 프로젝트 경로가 되므로(`hub_collect.py:428-430`), 새 루트 =
새 카드다.

**그런 입력이 실제로 존재한다**(E14): 보존된 8일 전수에서 「이벤트에만 있는」 cwd 4개 중 하나가
프로젝트의 **하위 디렉토리**(`…/klago-ui-oneffice-micro/public/word/js/script`)다. fold 는 항등
(마커 없음)이고 `ignore_globs` 에도 안 걸린다. 지금은 그곳에 `dashboard.html` 이 없어 카드가 안
생길 뿐이고, 누군가 그 디렉토리에서 `/dashboard` 를 한 번 부르면 **한 프로젝트가 카드 둘로
쪼개진다.** fold→ignore 는 이 경우를 **막지 못한다** — 걸러 준 것은 scratchpad 2건과
`/Users/byron` 뿐이었다(E13).

**앵커 규칙은 오늘의 루트 집합을 정확히 재현한다.** 오늘의 루트 = `fold(facts.cwd)` 와
`fold(scanned)` 의 합집합인데, `_group_sessions_by_project` 가 이미 `fold(facts.cwd)` 를 키로
쓰므로 `set(sessions_by_path)` 가 곧 그것이다. **따라서 이 조건은 어떤 루트도 새로 만들지 않고
어떤 루트도 없애지 않는다** — 실데이터에서 루트 4개가 그대로임을 확인했다(E15).

| 대안 | 기각 사유 |
|------|-----------|
| 앵커 없이 관측 cwd 를 그대로 루트로 | 위 하위 디렉토리 사례에서 카드가 쪼개진다. 사용자가 「카드를 합쳐 달라」고 요청한 것의 정반대 |
| 관측 cwd 중 **워크트리 마커가 있는 것만** 받아들인다 | 결과는 거의 같지만 규칙이 「무엇을 허용할지」의 열거가 된다. 앵커 규칙은 「이미 아는 프로젝트의 것만」이라는 **불변식**이라 새 경로 형태가 나타나도 안전 쪽으로 실패한다 |
| 루트가 늘어나는 것을 허용하되 카드 생성만 막는다 | `tier1_by_path` 와 카드 집합을 분리해야 한다 — `compose_project_views` 계약 변경. 얻는 것이 없다 |

### 결정 WT18 — GN 판정 비교를 `in observed_cwds` 로 바꾼다 (WT9 재개정, 쟁점 3)

```python
# 변경 전(초판): if view.state in LIVE_SESSION_STATES and facts.cwd == tier1_source_path
# 변경 후(2판): if view.state in LIVE_SESSION_STATES and tier1_source_path in facts.observed_cwds
```

**시그니처는 그대로다**(`tier1_source_path: str` 인자 유지). 바뀌는 것은 비교 한 줄이다.

| 상황 | 초판(`==`) | 2판(`in`) | 옳은 답 |
|------|-----------|-----------|---------|
| 워크트리 없는 프로젝트 | 참(그룹 키 = cwd = 출처) | 참(`observed_cwds[0] == cwd`) | 동일 — **완전 무동작** |
| 세션이 레포 루트에서 시작해 워크트리로 이동, 워크트리 파일이 승자 (**지금 이 상황**) | live 집합 **0** → 라벨 off (**우연히 맞음**) | live 집합 **1**, `09:50 < 13:04` → 라벨 off (**근거를 갖고 맞음**) | off |
| 워크트리 파일이 10:00 에 쓰이고, 11:00 에 시작한 세션이 워크트리로 이동해 live | live 집합 0 → 라벨 off (**틀림**) | live 집합 1, `11:00 > 10:00` → 라벨 **on** | on |
| 워크트리 세션이 첫 이벤트부터 워크트리(창이 구른 뒤) | 참 | 참 | 동일 |

**GN2 개정 표기는 다시 쓰지 않는다** — `hub-session-revival-and-stale-tier1.md:247` 에 초판이
남긴 화살표의 문장(「티어 1 파일의 소유 디렉토리와 cwd 가 같은 working 세션」)에서 *cwd* 의 뜻만
「그 세션이 이 창에서 관측한 cwd 중 하나」로 정밀해진다. §6 이관 표기에 한 줄을 덧붙인다.

### 결정 WT19 — WT14 는 **번복이 아니라 재확인**. `observed_cwds[0] == cwd` 를 불변식으로 못 박는다

WT14 가 금지한 것은 **`cwd` 를 다른 값으로 바꾸는 것**이다(정규화·마지막 이벤트·첫 비무시 cwd
세 안을 전부 기각했다). 2판은 `cwd` 를 그대로 두고 **필드를 하나 더한다.** 두 결정은 충돌하지
않는다.

두 필드가 서로 다른 규칙으로 채워져 조용히 어긋나는 것을 막기 위해 **채우는 지점을 하나로 묶는다**.

- `cwd` 는 `_new_session_builder` 가 **첫 이벤트**에서 정한다(현행 유지).
- `observed_cwds` 는 `build_session_facts` 의 루프에서 **모든 이벤트**에 대해, **내부 이벤트
  필터(`if is_filtered:`)보다 앞에서** 누적한다. `cwd` 도 필터보다 앞(빌더 생성 시점)에서
  정해지므로 두 값의 모집단이 같아진다.
- 따라서 **`observed_cwds[0] == cwd` 가 언제나 참**이고, 이것을 성공 기준 S13 · 테스트 U-28 로
  못 박는다.

> **T25-86 과의 관계.** `tests/run.sh:3513-3520` 이 `if is_filtered:` 가
> `_apply_tracked_event(session, event)` 호출보다 **앞 줄**임을 기계 검사한다. 누적을 필터
> **앞**에 두는 것은 이 검사와 무관하다(누적은 `_apply_tracked_event` 가 아니다). 구현자는
> `session.last_event_at_ms = …` 대입 옆에 붙이면 된다.

**필드에 기본값을 주지 않는다.** `observed_cwds: tuple[str, ...]` 을 **기본값 없이** 선언해
손으로 만드는 픽스처 8곳이 값을 반드시 대게 한다. 기본값 `()` 를 주면 픽스처가 조용히 「관측 cwd
없음」이 되고, 그러면 `in observed_cwds` 가 언제나 거짓이라 **GN 테스트가 통째로 무력해진다** —
이번 결함과 정확히 같은 모양의 구멍이다. 대가는 테스트 픽스처 8곳 수정이고, 그 8곳은 전부
키워드 인자라 한 줄씩 추가하면 된다(실측). 필드 순서는 `cwd` **바로 뒤**에 둔다(둘의 관계를
읽는 순서로 드러낸다).

### 결정 WT20 — 성공 기준은 **이음매 앞**에서 시작한다 (쟁점 2)

**진단**: U-14~U-16 은 `_read_tier1_for_root((self.root, self.worktree))` 처럼 **멤버 튜플을
손으로** 넘긴다. 그 튜플은 **프로덕션이 만들 수 없는 값**이었다 — 후보 목록에 워크트리가 들어간
적이 없으니까(E11). 검수 1회차가 같은 계열의 문제를 한 번 잡아 `plan_tier1_candidates` 를
추출했지만(M1), 그 새 테스트(`PlanTier1CandidatesTest`)도 **`sessions_by_path` 를 손으로**
만들었고 그 손 입력의 `SessionFacts.cwd` 에 워크트리를 넣어 두었다. **손 입력이 프로덕션의
데이터 흐름을 재현하지 않으면 이음매는 검증되지 않는다.**

**규칙**: 이 PRP 의 성공 기준 중 **티어 1 승자·registry·「이전 작업」 라벨에 관한 것(S9~S12)은
`collect_snapshot` 또는 `build_session_facts` 를 입력 지점으로 삼는 테스트로만 충족된다.**
중간 함수에 손 입력을 넣는 테스트는 **유지**하되(정의역을 못 박는 값이 있다), 그것만으로
만족되는 성공 기준은 **하나도 없다**.

**실행 가능성은 이미 확인됐다.** `tests/hub/test_hub_collect.py:804-833`
(`CollectSnapshotRateLimitIsolationTest`)이 `EVENTS_DIR`·`PROJECTS_DIR`·`CONFIG_PATH`·
`RATE_LIMITS_PATH` 네 상수를 임시 디렉토리로 바꿔 놓고 `collect_snapshot()` 을 통째로 호출한 뒤
`snapshot.projects` 를 단언한다. **새 인프라 없이** 같은 패턴을 쓴다(결정 WT12 와 일관).

| 대안 | 기각 사유 |
|------|-----------|
| 중간 함수 테스트를 더 촘촘히 | 이번 결함이 정확히 그 방식으로 통과했다. **입력을 손으로 만드는 한 프로덕션이 만들 수 없는 값을 계속 검증하게 된다** |
| 실데이터(`~/.claude/hub/events`)를 읽는 테스트 | 테스트가 사용자 홈에 의존한다. 결정적이지 않고 CI 에서 무의미하다. 진단 스크립트로는 유용하지만 테스트로는 안 된다 |
| 통합 테스트를 `tests/run.sh` 로 | run.sh 는 grep 기반 정합성 검사다. 동작 검증은 unittest 쪽 계약이다 |

### 결정 WT21 — WT6(mtime 최신)은 **그대로 유효**하다. 다만 P-2 가 즉시 활성이 된다

승자 규칙을 바꿀 이유는 없다. 「이 레포에서 가장 최근에 갱신된 대시보드」는 여전히 한 줄로
설명되고, 순수·결정적이며, 이번 개정이 그 전제를 건드리지 않는다.

**바뀌는 것은 발동 시점**이다. 초판 구현에서는 워크트리가 후보에 들어가는 일이 사실상 없었으므로
(E11) 이 규칙은 **한 번도 실제로 작동한 적이 없다.** 2판 배포 즉시 워크트리 파일이 이긴다(E15).
따라서 P-2(승자 요동)와 §9 의 「레포 루트 파일이 더 새로운 순간」 예외가 **관측 가능한 동작**이
된다. 히스테리시스는 여전히 넣지 않는다(임의 상수의 근거가 될 측정치가 없다) — 실제로 거슬리면
그때 도입한다.

**동률 처리(`max` 가 앞을 유지 + 후보 순서 `(루트, 워크트리…)`)도 그대로다.** 앵커 규칙은
`group_paths_by_repo_root` 의 순서 계약을 건드리지 않는다(필터만 한다).

### 결정 WT22 — S8 의 **유효 조건**을 명문화한다 (쟁점 4)

이번에 S8 만 결함을 잡았다. 다음 라운드에서도 그 역할을 하려면 **「언제 확인해야 유효한가」**가
체크리스트에 들어 있어야 한다. 초판 S8 에는 그것이 없었다.

**핵심 위험은 vacuous pass 다.** 창이 굴러 `SessionFacts.cwd` 가 이미 워크트리가 된 상태에서
확인하면 **개정 전 코드로도 통과한다**(E12 가 이것을 증명한다 — 그 조건에서는 초판 구현도
워크트리를 후보에 넣는다). 즉 **확인 시점의 세션 상태가 검증의 유효성을 좌우한다.**

따라서 S8 은 세 부분으로 나눈다.

1. **사전 조건 확인(P)** — 「세션 cwd 는 레포 루트, 이벤트에는 워크트리 cwd」 상태임을 먼저
   측정하고 그 출력을 기록한다. 이 조건이 아니면 **확인을 중단하고 조건이 성립하는 세션에서
   다시 한다**.
2. **정적 확인(V)** — 카드의 제목·진행률·라벨·클릭 대상.
3. **인과 확인(C)** — 워크트리 대시보드를 **한 번 갱신하고** 카드가 따라 바뀌는지. 정적 확인만
   하면 「우연히 맞는 화면」을 통과시킬 수 있다(이번 라운드의 라벨이 정확히 그런 경우였다 —
   E15 의 (a) 열).

상세 절차는 §7 「수동 확인(S8)」에 적는다.

---

## 5. 데이터 모델·인터페이스 계약

### 신규 (전부 `hub/bin/hub_project.py` — ★순수)

```python
WORKTREE_PATH_MARKER = "/.claude/worktrees/"
"""Claude Code 가 만드는 워크트리의 관례 경로 마커. 이 앞이 소유 레포 루트다(결정 WT3)."""


def fold_worktree_path(path: str) -> str:
    """워크트리 경로를 소유 레포 루트로 접는다. 워크트리가 아니면 원본 그대로.

    마커가 여러 번 나오면(중첩 워크트리) **첫 번째**에서 자른다 — 최외곽 레포까지 한 번에 접힌다.
    """


def group_paths_by_repo_root(paths: Sequence[str]) -> dict[str, tuple[str, ...]]:
    """경로들을 소유 레포 루트별로 묶는다.

    키는 접힌 루트, 값은 **접기 전 원본 경로들**이며 순서는 `(루트, 워크트리…사전순)` 이다.
    루트는 입력에 없어도 언제나 첫 원소로 들어간다 — 레포 루트의 dashboard.html 은 그 레포에
    세션이 없어도 티어 1 후보이기 때문이다. 이 순서가 티어 1 동률 처리의 근거다(결정 WT6).
    """


def select_tier1_source(candidates: Sequence[Tier1Snapshot]) -> Tier1Snapshot | None:
    """티어 1 후보 중 파일 mtime 이 가장 새로운 것을 고른다. 동률이면 목록 앞이 이긴다(결정 WT6)."""


def plan_tier1_candidates(
    sessions_by_path: dict[str, tuple[SessionFacts, ...]],
    scanned_paths: Sequence[str],
    ignore_globs: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """세션 관측 cwd·스캔 경로를 소유 레포 루트별 티어 1 후보 멤버로 묶는다(결정 WT2·WT5).

    `collect_snapshot` 조립부 3줄(observed_paths/members_by_root/candidate_paths)을 이
    함수로 추출한 것이다(검수 1회차 M1 — 그 3줄이 `collect_snapshot` 안에 있을 때는 이를
    참조하는 모든 테스트가 `_read_tier1_for_root` 를 `mock.patch` 로 우회해 실제로 실행하는
    테스트가 하나도 없었다). 빈 문자열 루트는 후보에서 제외한다(검수 1회차 m5).
    """
```

### 2판 신규 — `hub/bin/hub_session.py` (★순수)

```python
@dataclass(frozen=True)
class SessionFacts:
    session_id: str
    cwd: str
    # 이 창에서 관측된 모든 cwd. 첫 관측 순서, 중복 제거, **기본값 없음**(결정 WT19).
    # observed_cwds[0] == cwd 가 언제나 참이다 — 둘 다 내부 이벤트 필터보다 앞에서 정해진다.
    # `EnterWorktree` 가 살아 있는 세션의 cwd 를 바꾸므로(E2) `cwd` 하나로는 "이 세션이 어디서
    # 일했는가"를 답할 수 없다. 티어 1 후보(WT16)와 GN 세대 판정(WT18)이 이 값을 쓴다.
    observed_cwds: tuple[str, ...]
    started_at_ms: int
    ...
```

`_MutableSession` 에 같은 이름의 가변 리스트를 두고 `build_session_facts` 루프에서
「없으면 덧붙인다」로 누적한 뒤 `_freeze_session` 이 튜플로 동결한다. 중복 제거는 리스트 선형
탐색으로 충분하다 — 한 세션의 서로 다른 cwd 는 실데이터에서 **최대 3개**다(E13·E14).

> **접기를 여기서 하지 않는 이유**: `hub_session.py` 는 `hub_project` 를 임포트할 수 없다
> (`tests/run.sh:3851` T25-102 가 의존 방향을 기계 강제한다). 원본 cwd 만 모으고 접기는
> `hub_project` 쪽에서 한다 — 어차피 원본이 필요하다(결정 WT18 의 `in` 비교 대상).

### 변경 시그니처

| 함수 | 변경 전 | 변경 후 |
|------|---------|---------|
| `hub_project._live_session_start_times_ms` | `(sessions, session_views)` | `(sessions, session_views, tier1_source_path: str)` |
| `hub_collect.read_tier1_snapshot` | 반환 스냅샷에 `file_mtime_ms` 만 채움 | `source_path=project_path` 도 함께 채움 (`dataclasses.replace` 인자 1개 추가) |
| `hub_collect._read_tier1_for_root` | — (신설) | `(member_paths: Sequence[str]) -> tuple[Tier1Snapshot \| None, tuple[str, ...]]` — 멤버마다 읽고 `select_tier1_source` 로 고른 승자와 경고들을 돌려준다. **검수 1회차 m2 로 `root: str` 인자를 제거했다** — 본문 어디에서도 쓰이지 않았다(멤버 첫 원소가 곧 루트라는 `group_paths_by_repo_root` 의 순서 계약으로 충분하다) |
| `hub_collect._collect_tier1_snapshots` | — (신설, 검수 1회차 M1) | `(tier1_candidates_by_root: dict[str, tuple[str, ...]]) -> tuple[dict[str, Tier1Snapshot], tuple[str, ...]]` — 후보 루트마다 `_read_tier1_for_root` 를 불러 승자와 경고를 모은다(I/O 레이어, `collect_snapshot` 의 조립 루프를 분리) |
| `hub_project.plan_tier1_candidates` | — (신설, 검수 1회차 M1) | `(sessions_by_path, scanned_paths, ignore_globs) -> dict[str, tuple[str, ...]]` — 위 「신규」 절 참조 |
| `hub_model.build_dashboard_registry` | 값 = `project.path + "/" + …` | 값 = `project.tier1.source_path + "/" + …` |

**시그니처가 안 바뀌는 것(중요)**: `compose_project_views` · `should_ignore_cwd` ·
`resolve_project_dirs` · `encode_project_dir_name` · `render_hub_html` · `snapshot_content_key` ·
`_tier3_activity_by_encoded_name`.

**2판이 바꾸는 시그니처: 없다.** `build_session_facts` · `plan_tier1_candidates` ·
`_live_session_start_times_ms` · `_read_tier1_for_root` · `_collect_tier1_snapshots` ·
`read_tier1_snapshot` **전부 무변경**이고, 바뀌는 것은 **본문과 데이터 모델 한 필드**뿐이다.
이것이 후보 (c)를 고른 부수 효과다 — 후보 (a)는 `plan_tier1_candidates` 에 인자를 하나 더해
`collect_snapshot` 배선까지 손대야 했다.

| 함수 | 2판 변경 (본문만) |
|------|-------------------|
| `hub_session.build_session_facts` | 루프에서 `observed_cwds` 누적(내부 이벤트 필터보다 **앞**) |
| `hub_project.plan_tier1_candidates` | `observed_paths` 를 `facts.observed_cwds` 로, 반환 컴프리헨션에 `root in anchors` 조건 추가 |
| `hub_project._live_session_start_times_ms` | `facts.cwd == tier1_source_path` → `tier1_source_path in facts.observed_cwds` |

### `collect_snapshot` 조립부 (검수 1회차 M1 반영 후 형태)

> 최초 설계는 이 조립 3줄(`observed_paths`/`members_by_root`/`candidate_paths`)을
> `collect_snapshot` 안에 직접 두는 것이었다. 검수 1회차에서 이 조립을 실행하는 테스트가
> 하나도 없음이 실측으로 드러나(참조하는 모든 테스트가 `_read_tier1_for_root` 를
> `mock.patch` 로 우회) `hub_project.plan_tier1_candidates`(★순수)로 추출했다. 아래가 그
> 반영 후 형태다 — `_collect_tier1_snapshots`(hub_collect.py, I/O)가 조립 루프를 맡는다.

```python
sessions_by_path = _group_sessions_by_project(events, config.ignore_globs)   # 키가 이미 접힌 루트
scanned_paths = scan_roots_for_projects(config.roots, config.scan_depth)

tier1_candidates_by_root = hub_project.plan_tier1_candidates(
    sessions_by_path, scanned_paths, config.ignore_globs
)
tier1_by_path, tier1_read_warnings = _collect_tier1_snapshots(tier1_candidates_by_root)

# 티어 3 은 무변경 — resolve_project_dirs(list(tier3_by_encoded_name), list(tier1_candidates_by_root))
```

---

## 6. 정본 이관 표기 (원문은 어느 절에서도 지우지 않는다 — 화살표만 덧붙인다)

| 파일 | 지점 | 덧붙일 표기 |
|------|------|-------------|
| `docs/prps/hub-dashboard.md` | `:612-613` 「worktree cwd 를 레포 루트로 병합하는 로직(CAM P5)은 만들지 않는다 — 애초에 제외하기로 했으므로 필요 없다(YAGNI)」 | `→ **번복(2026-08-20, hub-worktree-fold.md)** — 이 배제는 「worktree 를 ignore_globs 로 제외한다」는 전제의 파생 결론이었다. 실측이 전제를 무너뜨렸다: worktree 세션은 이미 카드에 들어와 있고(첫 이벤트가 레포 루트라서), 진짜 결함은 ① 창이 굴렀을 때의 소실 ② 티어 1 이 레포 루트 파일만 읽는 불일치였다. 결정 WT1~WT6 이 정본이다.` |
| `docs/prps/hub-dashboard.md` | `:928` 기각 대안 표 행 | `**[번복 — hub-worktree-fold.md]**` 를 사유 칸 앞에 붙인다 |
| `docs/prps/hub-dashboard.md` | `:610-611` 「35개 중 20개가 scratchpad·worktree」 | `→ **재측정(2026-08-20)** — 36개 중 scratchpad 14, worktree 문자열 4 이고 그 4 중 3 은 /private/tmp 스크래치패드 **안**의 worktree 다. 노이즈 논거를 지탱하는 것은 `/private/tmp/**` 이지 worktree glob 이 아니다.` |
| `docs/prps/hub-session-revival-and-stale-tier1.md` | `:247` 초판이 덧붙인 화살표 문장(**2판 추가 표기**) | `→ **정밀화(2026-08-20, hub-worktree-fold.md 결정 WT18)** — 「티어 1 파일의 소유 디렉토리와 cwd 가 같은 working 세션」에서 **cwd** 의 뜻이 「그 세션이 이 창에서 관측한 cwd 중 하나」로 정밀해졌다. `SessionFacts.cwd` 는 창 안 **최초 이벤트**의 cwd 라(E1) 워크트리로 이동한 세션에서는 그 값이 레포 루트로 남아 있어 일치하는 세션이 0 이 됐다(E15). 비워크트리 프로젝트에서는 여전히 완전한 무동작이라 :266-290 판정 표 8행은 그대로 유효하다.` |
| `docs/prps/hub-session-revival-and-stale-tier1.md` | `:247` 「결정 GN2 — 판정 집합은 `working` 세션뿐이다」 | `→ **개정(2026-08-20, hub-worktree-fold.md 결정 WT9)** — 판정 집합에 조건이 하나 더 붙는다: **티어 1 파일의 소유 디렉토리와 cwd 가 같은** working 세션. 워크트리 fold 이후 한 그룹의 세션이 여러 디렉토리에서 오기 때문이다. 비워크트리 프로젝트에서는 무동작이라 :266-290 의 판정 표 8행은 그대로 유효하다.` |
| `docs/prps/hub-card-interactions-and-usage.md` | `:588` 「결정 N3 — 핸들러는 요청 문자열로 경로를 만들지 않는다」 | `→ **재진술(2026-08-20)** — registry 의 **값**이 `project.path` 재조립에서 `tier1.source_path` 로 바뀌었다(결정 WT8). 값이 여전히 collect 가 실제로 발견·`is_file()` 확인한 경로에서만 나오므로 N3 의 불변식은 그대로다. **키**는 변함없이 `sha256(project.path)` 다.` |
| `docs/prps/dashboard-ownership-guard.md` | R4 절(`:685` 부근, 안 1 보류 기록) | `→ **부분 해소(2026-08-20, hub-worktree-fold.md)** — 「프로젝트 1 : 대시보드 1」 전제가 읽기 쪽에서 깨졌다. worktree 는 파일 분리를 토큰이 아니라 **디렉토리로** 이미 달성한 형태이고, 허브는 후보 중 mtime 최신을 고른다(결정 WT6). 쓰기 쪽 소유권 가드(안 1)는 **여전히 보류**다 — 읽기 시점 병합이라 dashboard.md 는 무변경.` |
| `hub/README.md` | `:340` 티어 표의 티어 1 출처 칸 | `<프로젝트>/.claude/dashboard.html` → `<프로젝트 또는 그 워크트리>/.claude/dashboard.html (여럿이면 mtime 최신)` |
| `hub/README.md` | `:359` `ignore_globs` 행 | 「이 패턴에 맞는 경로는 제외한다」 뒤에 `. 단 worktree 경로는 **먼저 소유 레포 루트로 접힌 뒤** 이 판정을 받으므로, worktree 패턴은 티어 1·2 에서는 사실상 발동하지 않는다(티어 3 인코딩명 필터에서는 그대로 유효)` |

---

## 7. 테스트 계획

**정본 명령**: `python3 -m unittest discover -s tests/hub -t "$REPO_ROOT"` (stdlib unittest 전용 —
pytest fixture·parametrize·tmp_path 금지) / `bash tests/run.sh`.
**기준선(실측)**: 초판 작성 시점 `Ran 375 tests / OK`, **2판 작성 시점(`2fcadbf` 설치본)
`Ran 403 tests / OK`**(직접 실행해 확인). **테스트 개수를 단언하는 검증 항목은 쓰지 않는다**(T24 는
종료 코드만 본다).

> **2판이 테스트 계획에서 바꾸는 것.** U-1~U-21 은 **하나도 지우지 않는다.** 더하는 것은
> **입력 지점을 이벤트 쪽으로 끌어올린 테스트**(U-22~U-30)이고, 그것이 결정 WT20 의 내용이다.
> 초판 테스트가 틀린 것은 아니다 — **프로덕션이 만들 수 없는 값을 검증했을 뿐**이다.

### 기존 테스트에 대한 영향 (전수 판정)

| 테스트 | 판정 | 근거 |
|--------|------|------|
| `test_hub_project.py:145` **M15** (`worktree 경로는 무시 대상`) | **유지 — 무변경** | `should_ignore_cwd` 자체를 안 고친다. 접기가 그 앞에 놓일 뿐이고, 이 술어는 **티어 3 인코딩명 필터에서 계속 살아 있다**(결정 WT5) |
| `test_hub_collect.py:169` (`티어 3 인코딩명 제외`) | **유지 — 무변경** | 티어 3 을 접지 않기로 했으므로 단언이 그대로 참이다 |
| `Tier1Snapshot` 을 만드는 5곳(`hub_parse.py:118` + 테스트 4곳) | **무변경** | 전부 키워드 인자이고 신규 필드에 기본값이 있다(실측) |
| `tier=1` 인데 `tier1=None` 인 `ProjectView` 픽스처(`test_hub_model.py`·`test_hub_server.py`·`test_hub_project.py` 의 `_tier1` 헬퍼) | **수정 — 초판의 예상이 빗나간 지점** | 원인은 신규 필드의 기본값 유무가 **아니라** `build_dashboard_registry` 의 `tier1 is None` 가드와 GN9 의 `facts.cwd == tier1_source_path` 조건이다. 옛 픽스처는 `_project_tier`(`tier==1 ⟺ tier1 is not None`)상 **프로덕션이 만들 수 없는 상태**를 조립하고 있었고, 옛 코드가 `tier1` 을 안 봤기 때문에만 통과했다(검수 1회차에서 정당한 계약 반영으로 판정) |
| `compose_project_views` 호출 4곳(테스트) | **무변경** | 시그니처를 안 바꾼다 |
| `test_hub_model.py` registry 테스트 | **수정** | 값의 출처가 `project.path` → `tier1.source_path` |
| `tests/run.sh` T25-10(순수 가드)·T25-87(필드 순서)·T25-1/2·T25-103/104 | **전부 무변경** | 새 모듈 0개, `ProjectView` 필드 0개 추가, `os.`/`Path(`/`open(` 미사용 |

### 신규 단위 테스트 (초판 — U-1~U-21, 2판에서 하나도 지우지 않는다)

| # | 클래스/파일 | 입력 | 기대 |
|---|-------------|------|------|
| U-1 | `FoldWorktreePathTest` (`test_hub_project.py`) | `/repo/.claude/worktrees/w` | `/repo` |
| U-2 | 〃 | `/repo` (워크트리 아님) | `/repo` (항등) |
| U-3 | 〃 | `/repo/.claude/worktrees/feature/sub` (다단 이름) | `/repo` |
| U-4 | 〃 | `/a/repo/.claude/worktrees/w1/.claude/worktrees/w2` (중첩) | `/a/repo` — **`rfind` 구현이면 실패한다** |
| U-5 | 〃 | `/Users/u/.claude/worktrees/x` | `/Users/u` (엣지 X-3 을 문서화하는 테스트) |
| U-6 | `GroupPathsByRepoRootTest` | `["/repo/.claude/worktrees/w"]` | `{"/repo": ("/repo", "/repo/.claude/worktrees/w")}` — **루트가 입력에 없어도 첫 원소** |
| U-7 | 〃 | 워크트리 2개 + 루트 | 값 순서가 `(루트, 사전순 워크트리 2개)` |
| U-8 | `SelectTier1SourceTest` | mtime 이 다른 후보 2개 | 큰 쪽 |
| U-9 | 〃 | **mtime 동률** 후보 2개, 루트가 앞 | **루트가 이긴다**(결정 WT6 을 못 박음) |
| U-10 | 〃 | 빈 목록 | `None` |
| U-11 | `WorktreeFoldGroupingTest` (`test_hub_collect.py`) | 워크트리 cwd 이벤트 목록 | 그룹 키가 레포 루트 (**S1**) |
| U-12 | 〃 | **동일 세션의 이벤트 2건**(둘 다 워크트리 cwd, E5 재현) | 레포 루트 그룹에 그 세션이 있다 (**S2** — 검수 1회차 m3 로 재작성: 「접기 전」 비교는 손수 그룹핑 대신 원본 cwd 에 `should_ignore_cwd` 를 직접 호출해 단언한다. 이전 버전은 손수 재구현이 `should_ignore_cwd` 를 전혀 거치지 않아 항진명제였다) |
| U-13 | 〃 | 워크트리 cwd 가 `/private/tmp/...` 아래 | 접은 뒤에도 여전히 제외된다 (E9 회귀 방어) |
| U-14 | `Tier1SourceSelectionTest` | 임시 트리에 루트·워크트리 dashboard.html 2개 + `os.utime` 으로 mtime 조작 | 승자가 새 쪽, `snapshot.source_path` 가 그 디렉토리 (**S4**) |
| U-15 | 〃 | 워크트리에만 dashboard.html | 레포 루트 카드가 tier 1 로 승격되고 `source_path` = 워크트리 |
| U-16 | 〃 | 루트에만 dashboard.html | **변경 전과 동일**(`source_path` = 루트) (**S7**) |
| U-17 | `test_hub_model.py` | tier 1 + `source_path` = 워크트리인 `ProjectView` | registry 값이 워크트리 파일 경로 (**S5**) |
| U-18 | `test_hub_project.py` GN | 승자 = 워크트리 파일, live 세션 = 루트 세션 1 + 워크트리 세션 1 | 워크트리 세션만 판정에 들어간다 (**S6**) |
| U-19 | 〃 | 워크트리 없는 프로젝트 | GN 판정 결과가 변경 전과 동일 (**S7**) |
| U-20 | `test_hub_parse.py` | `parse_dashboard_html` 결과 | `source_path == UNSET_SOURCE_PATH` (순수 레이어가 채우지 않음) |
| U-21 | `render_hub_html` → `#dzh-data` 파싱 | 워크트리 세션이 있는 스냅샷 | `projects[].path` 중 `/.claude/worktrees/` 포함 경로 0건 (**S3**) |

### 2판 신규 단위 테스트 (U-22~U-30 — 이것이 이번 개정의 핵심이다)

#### 공통 픽스처 — `CollectSnapshotWorktreeTier1Test` (`tests/hub/test_hub_collect.py`)

**이 클래스가 「이벤트 파일 → 스냅샷」 전 구간을 도는 유일한 티어 1 테스트다**(결정 WT20).
선례는 `CollectSnapshotRateLimitIsolationTest`(`:804-833`) — 같은 방식으로 모듈 상수를 임시
디렉토리로 바꾼다.

```
setUp
  temp = mkdtemp()
  hub_collect.EVENTS_DIR      = temp/"events"
  hub_collect.PROJECTS_DIR    = temp/"projects"     # 티어 3 격리
  hub_collect.CONFIG_PATH     = temp/"config.json"
  hub_collect.RATE_LIMITS_PATH= temp/"rate_limits.json"
  (tearDown 에서 전부 원복 + shutil.rmtree)

디렉토리 트리
  <temp>/repo/.claude/dashboard.html                                  ← 레포 루트 대시보드
  <temp>/repo/.claude/worktrees/w/.claude/dashboard.html              ← 워크트리 대시보드

config.json
  {"ignore_globs": ["**/.claude/worktrees/**"], "show_usage_panel": false}
```

**config 를 이렇게 쓰는 이유 두 가지.**
`ignore_globs` 에서 `/tmp/**`·`/private/tmp/**` 를 **뺀다** — `tempfile.mkdtemp()` 는 `TMPDIR`
을 따르므로 환경에 따라 픽스처 전체가 무시 대상이 될 수 있다. 반대로 `**/.claude/worktrees/**`
는 **반드시 남긴다** — 그것이 fold-first 순서를 검증하는 대상이다(U-11 이 같은 이유로 기본값을
쓴다). `show_usage_panel: false` 는 `_capture_for_snapshot` 이 파일을 **열지도 않게** 한다
(`hub_collect.py:383`, 결정 U4) — 테스트가 사용자 홈의 캡처 파일에 의존하지 않는다.

**이벤트 파일 이름은 `now_ms` 의 로컬 날짜로 지어야 한다** — `read_recent_events` 가
「오늘+어제」 파일만 읽는다(`_recent_event_file_paths`). 줄 스키마는 최소 4키다:
`{"t": 밀리초, "e": 훅이름, "s": 세션ID, "c": cwd}`(`hub_session.parse_event_line:120-124`).

**핵심은 이벤트 두 줄의 모양이다** — 이것이 실데이터에서 확정된 실패 시나리오다(E11).

```
{"t": T-2h,  "e": "UserPromptSubmit", "s": "s1", "c": "<temp>/repo"}                     ← 첫 이벤트 = 레포 루트
{"t": T-30m, "e": "UserPromptSubmit", "s": "s1", "c": "<temp>/repo/.claude/worktrees/w"} ← 워크트리는 이벤트에만
```

이 두 줄이면 `SessionFacts.cwd == "<temp>/repo"` 이고 워크트리는 `observed_cwds` 에만 남는다.
**개정 전 코드에서는 이 입력으로 워크트리가 절대 티어 1 후보가 되지 않는다.**

| # | 테스트 | 입력 (위 픽스처 + 차이) | 단언 | 기준 |
|---|--------|------------------------|------|------|
| **U-22** | `test_worktree_dashboard_wins_when_only_events_know_the_worktree` | 루트 mtime = `T-24h`, 워크트리 mtime = `T-10m` | ① `len(snapshot.projects) == 1` ② `projects[0].path == <temp>/repo` ③ `tier == 1` ④ `tier1.title == "워크트리 작업"` ⑤ `tier1.source_path == <워크트리>` | **S9** |
| **U-23** | `test_root_dashboard_wins_when_it_is_newer` (**대조군**) | 루트 mtime = `T-10m`, 워크트리 mtime = `T-24h` | `tier1.title == "루트 작업"`, `source_path == <temp>/repo` | S9 역방향 — **양방향으로 움직이는 테스트임을 보장한다**(검수 2회차가 「결과를 줄이는 뮤테이션에 반응 못 하는 단언」을 실제로 잡았다) |
| **U-24** | `test_previous_task_label_turns_on_when_session_started_after_the_worktree_file` | 워크트리 mtime = `T-2h`, 세션 첫 이벤트 = `T-1h` | `projects[0].tier1_is_previous_task is True` | **S11 (ON)** — **(a)안과 (c)안을 가르는 테스트다.** `facts.cwd == source_path` 로 되돌리면 live 집합이 비어 `False` 가 된다 |
| **U-25** | `test_previous_task_label_stays_off_when_the_live_session_predates_the_file` | 워크트리 mtime = `T-10m`, 세션 첫 이벤트 = `T-2h` | `tier1_is_previous_task is False` **그리고** 그 판정에 쓰인 live 집합이 비어 있지 않다(같은 픽스처로 `compose_project_views` 를 직접 불러 확인하거나, U-24 와 짝지어 「같은 입력에서 mtime 만 바꾸면 결과가 뒤집힌다」로 단언) | **S11 (OFF)** — 「우연히 꺼짐」을 통과로 인정하지 않는다 |
| **U-26** | `test_subdirectory_cwd_never_creates_a_second_card` | 이벤트에 셋째 줄 `"c": "<temp>/repo/sub"` 추가 + `<temp>/repo/sub/.claude/dashboard.html` 생성 | ① `len(snapshot.projects) == 1` ② `projects[0].path == <temp>/repo` ③ 어떤 project.path 도 `/sub` 로 끝나지 않는다 | **S12** — 앵커 규칙(WT17). **이 입력은 실데이터에 존재한다**(E14) |

| # | 테스트 | 클래스 | 입력 | 기대 | 기준 |
|---|--------|--------|------|------|------|
| **U-27** | `test_worktree_in_observed_cwds_becomes_a_tier1_member` | `PlanTier1CandidatesTest` (`test_hub_project.py`) | `sessions_by_path = {"/repo": (facts,)}` 이고 `facts.cwd == "/repo"`, `facts.observed_cwds == ("/repo", "/repo/.claude/worktrees/w")`, **기본 ignore_globs** | 반환 멤버가 `("/repo", "/repo/.claude/worktrees/w")` | S9 의 순수 단위 대응 — **이번 결함의 최소 재현** |
| **U-28** | `test_observed_cwds_first_element_is_always_cwd` | `ObservedCwdsTest` (`test_hub_session.py`, 신설) | 이벤트 3건(루트 → 워크트리 → 루트) | `facts.cwd == facts.observed_cwds[0]` **그리고** `observed_cwds == ("/repo", "/repo/.claude/worktrees/w")`(중복 제거·첫 관측 순) | **S13** |
| **U-29** | `test_internally_filtered_event_still_contributes_its_cwd` | 〃 | 첫 이벤트 루트, 둘째가 **compact `SessionStart`**(내부 필터 대상)이고 cwd 가 워크트리 | 워크트리가 `observed_cwds` 에 **있다** | WT19 — 누적 지점이 필터보다 앞임을 못 박는다 |
| **U-30** | `test_foreign_observed_path_creates_no_root_and_no_member` | `PlanTier1CandidatesTest` | `facts.cwd == "/repo"`, `observed_cwds == ("/repo", "/other/project", "/repo/sub")` | 반환 키가 `{"/repo"}` 하나이고 멤버는 `("/repo",)` — 남의 프로젝트도 하위 디렉토리도 들어오지 않는다 | S12 의 순수 단위 대응 |

#### 기존 테스트에 대한 2판의 영향

| 테스트 | 판정 | 근거 |
|--------|------|------|
| `SessionFacts(...)` 를 손으로 만드는 **8곳**(`test_hub_project.py:25`·`110`·`132`·`137`·`241`·`312`·`325`·`430`, 실측) | **수정 필수** | `observed_cwds` 에 기본값을 주지 않기 때문이다(결정 WT19). 대부분 `observed_cwds=(cwd,)` 한 줄이면 되고, GN 테스트 일부는 워크트리를 포함한 값이 필요하다 |
| `PlanTier1CandidatesTest` 기존 케이스 | **수정** | 손으로 만든 `SessionFacts` 의 `cwd` 에 워크트리를 넣어 두었다면 **프로덕션이 만들 수 없는 값**이다 — `cwd` 는 레포 루트, 워크트리는 `observed_cwds` 로 옮긴다. 「창이 구른 뒤」 케이스(둘 다 워크트리)는 **한 건 남긴다** |
| U-14~U-16 (`_read_tier1_for_root` 손 입력) | **유지 — 무변경** | 정의역을 못 박는 값이 있다. 다만 **이제 어떤 성공 기준도 이 테스트만으로 만족되지 않는다**(WT20) |
| U-18·U-19 (GN) | **수정** | `facts.cwd == source_path` → `source_path in observed_cwds` 로 판정이 바뀐다. U-19(비워크트리 무동작)는 `observed_cwds=(cwd,)` 만 채우면 **결과가 그대로**여야 한다 — 그 동일성 자체가 단언 대상이다 |
| `test_hub_server.py`·`test_hub_model.py`·`test_hub_parse.py` | **무변경** | `SessionFacts` 를 만들지 않는다(실측: 생성 8곳이 전부 `test_hub_project.py`) |
| `tests/run.sh` T25-10(순수 가드)·T25-86(필터 순서)·T25-102(의존 방향) | **전부 무변경이어야 한다** | `hub_session.py` 에 `os.`·`Path(`·`open(` 를 넣지 않고, 누적을 `_apply_tracked_event` 안에 넣지 않으며, `hub_project` 를 임포트하지 않는다 |

### `tests/run.sh` 회귀 검사 (초판 신설 — 당시 최대 `T25-110`)

| # | 검사 | 실패 시 잡히는 표류 |
|---|------|--------------------|
| **T25-111** | `hub_project.py` 에 `WORKTREE_PATH_MARKER = "/.claude/worktrees/"` 리터럴이 있다 | 마커 문자열이 조용히 바뀌어 아무것도 안 접힘 |
| **T25-112** | `hub_collect.py` 에서 `fold_worktree_path` 또는 `group_paths_by_repo_root` 호출이 **`should_ignore_cwd` 보다 앞 줄**에 있다(`grep -n` 줄번호 비교 — T25-87 과 같은 방식) | fold-first 순서가 뒤집혀 기능이 통째로 무력화 |
| **T25-113** | `hub_model.py` 에 `project.path + "/" + PROJECT_DASHBOARD_RELATIVE_PATH` 가 **남아 있지 않다** | 결정 WT8 되돌림(카드/패널 불일치 부활) |
| **T25-114** | `hub_project.py` 에 `os.`·`Path(`·`open(`·`subprocess` 가 없다 — **`subprocess` 를 명시적으로 추가**한다 | T25-10 의 grep 이 `subprocess.run(` 을 통과시키는 실측 구멍을 메운다 |

### 2판 `tests/run.sh` 회귀 검사 (T25-115~118 — 전부 `note_failure` 누적형)

| # | 검사 | 실패 시 잡히는 표류 |
|---|------|--------------------|
| **T25-115** | `hub_session.py` 에 `observed_cwds: tuple[str, ...]` 이 있고 **`observed_cwds: tuple[str, ...] = ()` 는 없다** | 필드에 기본값이 슬쩍 붙어 픽스처가 조용히 「관측 cwd 없음」이 되는 것(결정 WT19 의 정확한 실패 모드) |
| **T25-116** | `hub_project.py` 에 `facts.observed_cwds` 가 있고, `plan_tier1_candidates` 본문에 옛 표현 `{facts.cwd for` 가 **없다** | 후보 입력을 옛 입력으로 되돌리는 것 = **이번 결함의 재발** |
| **T25-117** | `hub_project.py` 에 `tier1_source_path in facts.observed_cwds` 가 있고 `facts.cwd == tier1_source_path` 가 **없다** | GN 판정이 후보 (a) 수준으로 되돌아가는 것(결정 WT18 되돌림) |
| **T25-118** | `tests/hub/test_hub_collect.py` 에 `class CollectSnapshotWorktreeTier1Test` 와 `hub_collect.collect_snapshot(` 가 **둘 다** 있다 | 이음매 테스트가 삭제되거나 중간 함수 호출로 「간소화」되는 것 — 결정 WT20 을 문서가 아니라 게이트로 지킨다 |

> **T25-118 의 한계를 정직하게 적는다.** grep 은 클래스가 **존재**하는지만 본다. 그 안의 단언이
> 약해지는 것은 못 잡는다. 진짜 안전망은 아래 뮤테이션 9~13 이고, T25-118 은 **삭제**만 막는다.

### 뮤테이션 검증 (구현자가 반드시 수행)

1. `fold_worktree_path` 의 `find` → `rfind` 로 바꾸면 **U-4 가 실패해야 한다.**
2. `_group_sessions_by_project` 에서 fold 와 ignore 순서를 뒤집으면 **U-11·U-12 가 실패해야 한다.**
3. `select_tier1_source` 의 `max` → `min` 으로 바꾸면 **U-8·U-14 가 실패해야 한다.**
4. `build_dashboard_registry` 를 옛 조립으로 되돌리면 **U-17 이 실패해야 한다.**
5. `_live_session_start_times_ms` 의 cwd 조건을 지우면 **U-18 이 실패해야 한다.**

**검수 1회차 M1 로 추가된 뮤테이션 3건** (전부 재검증 완료 — 397 OK + run.sh 24/24 로는 잡히지
않던 것들이었다):

6. `_collect_tier1_snapshots` 에서 `_read_tier1_for_root(member_paths)` → `_read_tier1_for_root((root,))`
   로 바꾸면(멤버 대신 루트만 넘김) **`CollectTier1SnapshotsTest.test_full_member_tuple_is_forwarded_not_just_the_root`
   가 실패해야 한다.**
7. `plan_tier1_candidates` 의 `observed_paths = {facts.cwd for …}` → `set(sessions_by_path)` 로
   바꾸면 **`PlanTier1CandidatesTest.test_worktree_member_survives_fold_then_ignore_with_default_globs`
   가 실패해야 한다.**
8. `plan_tier1_candidates` 에서 ignore 를 (접힌 루트가 아니라) 멤버 각각의 원본 경로에 적용하도록
   바꾸면 **위 7번과 동일한 테스트가 실패해야 한다.**

   > 재검수 2회차 정정: 초판은 여기에 `test_ignored_root_is_excluded_entirely` 도 함께 실패한다고
   > 적었으나 실측 결과 그 테스트는 반응하지 않는다. 기대값이 `{}` 라 **결과를 줄이는 방향의
   > 뮤테이션에는 구조적으로 반응할 수 없다.** 뮤테이션 자체는 앞의 테스트가 검출하므로 커버리지
   > 구멍은 아니다 — 「전부 검출된다」는 문구 쪽이 틀렸던 것이다.

**2판 신규 뮤테이션 9~13** (구현 후 반드시 하나씩 넣어 보고 「기대한 테스트가 실패」를 확인한다):

| # | 뮤테이션 | 실패해야 하는 테스트 |
|---|----------|---------------------|
| **9** | `plan_tier1_candidates` 의 `facts.observed_cwds` 를 `(facts.cwd,)` 로 되돌린다 (**이번 결함의 정확한 재현**) | **U-22·U-27** |
| **10** | `build_session_facts` 의 cwd 누적을 `if is_filtered:` **뒤로** 옮긴다 | **U-29** |
| **11** | `_live_session_start_times_ms` 의 `tier1_source_path in facts.observed_cwds` 를 `facts.cwd == tier1_source_path` 로 되돌린다 (= 후보 (a) 수준) | **U-24** (U-25 는 반응하지 않는다 — 기대값이 `False` 라 「집합을 줄이는」 뮤테이션에 구조적으로 반응할 수 없다. 검수 2회차가 같은 함정을 지적했으므로 미리 적어 둔다) |
| **12** | `plan_tier1_candidates` 의 `root in anchors` 조건을 지운다 | **U-26·U-30** |
| **13** | `select_tier1_source` 의 `max` → `min` (기존 뮤테이션 3 의 이음매 확장) | **U-8·U-14 에 더해 U-22 도** 실패해야 한다. 실패하지 않으면 U-22 의 픽스처가 mtime 차이를 만들지 못한 것이다 |

**뮤테이션 9 가 이번 개정의 판정 기준이다.** 그것을 넣었을 때 `403+` 케이스 중 **U-22 와 U-27
둘 다** 실패하지 않는다면, 2판도 초판과 같은 구멍을 남긴 것이다.

### 수동 확인 (S8 — 2판에서 재작성, 결정 WT22)

> **왜 재작성하는가.** 이번 라운드에서 **S8 만 결함을 잡았다.** 그런데 초판 S8 에는
> 「어떤 조건에서 확인해야 유효한가」가 없었다. **창이 굴러 `SessionFacts.cwd` 가 이미
> 워크트리가 된 상태에서 확인하면 개정 전 코드로도 통과한다**(E12 가 증명). 그 vacuous pass 를
> 막는 것이 아래 **G 단계**다.

#### G. 사전 조건 — **유효 조건 게이트** (이것부터 하고, 출력을 보고서에 붙인다)

```bash
python3 <진단 스크립트>   # scratchpad/diag_m5.py 와 동등한 읽기 전용 3줄 조회
```

확인해야 하는 출력 세 줄 — **셋이 전부 성립할 때만 이 라운드의 S8 이 유효하다.**

- [ ] **G-1** `coding-env` 그룹의 `SessionFacts.cwd` 고유값이 **레포 루트 하나뿐**이다
      (워크트리가 섞여 있으면 → **중단**. 창이 이미 굴렀으므로 결함 A 를 검증하지 못한다)
- [ ] **G-2** 이벤트 원본 cwd 에는 **워크트리 경로가 있다** (없으면 → **중단**. 검증할 대상이 없다)
- [ ] **G-3** 워크트리의 `.claude/dashboard.html` 이 레포 루트의 것보다 **mtime 이 새롭다**
      (아니면 → 워크트리에서 `/dashboard` 를 한 번 호출해 만든 뒤 다시 G 부터)

> **G-1 이 성립하지 않는 상태에서 통과한 S8 은 증거로 인정하지 않는다.** 이것이 2판이
> 초판 검증 절차에 대해 내리는 유일한 절차적 판정이다. (게이트 코드는 `G-n` 이다 —
> `P-n` 은 이 문서에서 **리스크 코드**로 이미 쓰이고 있다.)

#### V. 정적 확인 (설치 → 재시작 → 화면)

```bash
hub/install.sh --force      # 1. 설치본 갱신 (이 단계를 빠뜨리면 "고쳤는데 화면이 그대로")
/hub server restart         # 2. 돌고 있는 프로세스를 새 코드로 갈아 끼운다
```

**두 대시보드의 제목을 미리 적어 두고 대조한다**(둘은 완전히 다른 문자열이라 식별 가능하다).

- [ ] **V-1** `coding-env` 카드가 **하나만** 있고 `worktree-project-merge` 카드가 없다
- [ ] **V-2** 그 카드의 제목이 **워크트리 대시보드의 제목**이다 (레포 루트 제목이 보이면 실패)
- [ ] **V-3** 진행률이 워크트리 대시보드의 값이다 (초판 실패 시 `100%` 가 보였다)
- [ ] **V-4** 「이전 작업」 라벨이 **꺼져 있다**
- [ ] **V-5** 카드를 클릭하면 **워크트리의** dashboard.html 이 패널에 뜬다
- [ ] **V-6** 다른 프로젝트 카드(`daily-pulse`·`klago-…`·`claude-agents-manager`)의 **개수와
      제목이 변하지 않았다** (앵커 규칙 WT17 의 실환경 확인 — 카드가 하나라도 늘면 실패)

#### C. 인과 확인 (정적 확인만으로는 「우연히 맞는 화면」을 통과시킨다)

- [ ] **C-1** 워크트리에서 `/dashboard log` 등으로 대시보드를 **한 번 갱신**하고, 수집 주기
      (5초) 뒤 카드의 제목·진행률이 **따라 바뀐다**
- [ ] **C-2** 레포 루트에서 대시보드를 갱신하면 카드가 **레포 루트 쪽으로 넘어간다**
      (결정 WT6/WT21 의 mtime 최신 규칙이 실제로 작동하는지 — 이 전환이 P-2 리스크의 실물이다.
      확인 후 워크트리를 다시 갱신해 원상 복구한다)

> **C-1 이 이번 라운드에서 가장 중요한 항목이다.** 초판 실패 화면에서도 「이전 작업」 라벨은
> 꺼져 있을 수 있었다(live 집합이 비면 꺼진다 — E15). 정적 확인만으로는 배선이 살아 있는지
> 알 수 없고, **갱신이 화면에 반영되는지**가 유일하게 확실한 신호다.

---

## 8. 엣지 케이스

| # | 상황 | 처리 |
|---|------|------|
| **X-1** | 중첩 워크트리 | 첫 마커에서 자름 → 최외곽 레포 (U-4) |
| **X-2** | 다단 워크트리 이름(`a/b`) — `EnterWorktree` 의 `name` 이 `/` 구분 다단 세그먼트를 허용한다 | 고정 깊이·부모의 부모 방식은 **틀린다**. 마커 절단만이 옳다 (U-3) |
| **X-3** | `$HOME/.claude/worktrees/x` → `$HOME` 으로 접힘 | **가드를 붙이지 않는다.** 관례상 그것이 맞는 답이고(그 워크트리의 소유 레포는 `$HOME` 이다), 이 사용자의 config 에는 `/Users/byron` 이 ignore 로 들어 있어 실질 영향이 없다(실측). 동작을 U-5 로 문서화 |
| **X-4** | 후행 슬래시가 붙은 cwd | 실데이터에 없다(2일 창 cwd 고유값 전부 후행 슬래시 없는 절대경로). 마커가 있으면 절단이 정상 동작하고, 없으면 **오늘과 동일**하게 별도 키가 된다 — 회귀 아님 |
| **X-5** | 워크트리가 삭제됐는데 이벤트만 남음 | `read_tier1_snapshot` 이 `is_file()` 로 걸러 후보에서 자동 탈락. registry 는 매 사이클 재생성되고 서빙 실패는 404 로 접힌다 |
| **X-6** | 워크트리 dashboard.html 이 DOM 계약 불일치 | 그 후보만 `None` + 경고 1건, 나머지 후보로 승자 결정. 후보가 전부 실패하면 티어 2 로 강등(오늘과 같은 동작) |
| **X-7** | 한 카드의 세션 수가 늘어남(`coding-env` 이미 15) | `.sessions` 는 카드 안에서 내부 스크롤(`overflow-y:auto`)이고 상한이 없다. 카드 높이 340px 고정이라 **레이아웃은 깨지지 않는다**. 스크롤 없이 보이는 예산이 3줄인 것은 오늘과 같다 |
| **X-8** | 워크트리 세션이 working 이라 레포 루트 카드가 **글로우**한다 | **의도된 동작**이다 — 그 레포에서 실제로 작업이 진행 중이다. `_project_state`(앞이 이긴다)·`_last_activity_at_ms`(max)가 자연히 흡수한다 |
| **X-9** | 클라이언트 세션 숨김(done+무발췌, 12시간 초과 stale)이 서버 집계와 어긋남 | **오늘도 있는 어긋남**(결정 V1, 클라이언트 전용 필터)이 워크트리 세션 때문에 조금 더 자주 보일 수 있다. 서버로 올리지 않는다 — 별건 |
| **X-10** (2판) | 한 세션이 **워크트리 두 개**를 오간다 | `observed_cwds` 에 둘 다 남고 둘 다 같은 루트로 접히므로 **둘 다 티어 1 후보 멤버**가 된다. 승자는 mtime 최신(WT6). 앵커 규칙과 충돌하지 않는다 |
| **X-11** (2판) | 세션이 **다른 프로젝트**로 `cd` 했다(E13 의 실제 사례: 한 세션의 cwd 가 scratchpad 로 튀었다) | 그 경로는 자기 루트로 접히고 앵커에 없으면 **통째로 탈락**(U-30). 그 프로젝트에 **자기 세션 그룹이 이미 있으면** 앵커에 있지만, 그 경우 멤버는 자기 자신뿐이라 **오늘과 완전히 동일**하다. 어느 쪽이든 카드는 변하지 않는다 |
| **X-12** (2판) | `observed_cwds` 가 비정상적으로 길어진다 | 상한을 **두지 않는다.** 실데이터에서 한 세션의 서로 다른 cwd 는 최대 3개이고(E13·E14 전수), 값은 문자열 몇 개다. 상한 상수를 정할 측정 근거가 없다(YAGNI) |
| **X-13** (2판) | 워크트리가 삭제됐는데 `observed_cwds` 에 경로가 남아 있다 | X-5 와 동일하게 `read_tier1_snapshot` 의 `is_file()` 에서 탈락한다. 앵커 규칙은 루트만 보므로 영향 없다 |
| **X-14** (2판) | 세션의 **모든** 이벤트가 워크트리다(창이 구른 뒤) | `cwd` = 워크트리 → 그룹 키는 접힌 루트(초판 fold, E10 확인), `observed_cwds` = (워크트리,) → 멤버에 워크트리. **초판 동작과 같고 2판이 되돌리지 않는다** — U-12 를 그대로 유지하는 이유다 |

---

## 9. 부수 발견 — `commands/dashboard.md` 「자동 발행」 3-a

`commands/dashboard.md` 는 허브 서버가 살아 있으면 대시보드 대신 허브 페이지를 열라고 지시하고,
그 근거로 「허브에서 카드를 클릭하면 그 대시보드가 열린다」를 든다. **워크트리에서는 이 근거가 오늘
거짓이다** — 클릭하면 레포 루트 파일이 열려 방금 만든 대시보드에 닿지 못한다(결정 WT8 과 같은 뿌리).

**판정: 이번 범위에 넣되 `dashboard.md` 는 한 줄도 고치지 않는다.** 결정 WT8 이 registry 값을
승자 파일로 바꾸는 순간 그 근거가 **다시 참이 되기 때문**이다. 별건으로 뺄 필요도, 문서를 고칠
필요도 없다. 수동 확인 S8 의 ~~마지막 항목~~ **V-5 항목**이 이것을 검증한다(2판에서 S8 을 G/V/C
3단계로 재작성했다).

(예외: 레포 루트 파일이 워크트리 파일보다 새로운 순간에는 여전히 루트 파일이 열린다. 워크트리에서
작업 중이라면 그 상태는 곧 뒤집히므로 실질 문제가 아니다 — P-2 로 관리.)

> **2판 주석.** 초판은 「결정 WT8 이 registry 값을 바꾸는 순간 근거가 다시 참이 된다」고 적었는데,
> **실제로는 참이 되지 않았다** — 워크트리가 티어 1 후보에 오르지 못해 승자가 계속 레포 루트였기
> 때문이다(E11). 즉 이 절의 판정은 **결정 WT16 이 들어가야 비로소 성립한다.** S8 의 **C-1**
> (워크트리 대시보드를 갱신하면 카드가 따라 바뀐다)이 이것을 인과로 확인하는 항목이다.

---

## 10. 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| **P-1** | 접기가 **의도치 않은 경로를 합쳐** 카드가 통째로 사라지거나 엉뚱한 곳에 생긴다. `config.roots` 가 비어 있어 그룹 키가 **카드 생성의 유일한 입력**이라 파급이 크다 | 접기는 경로를 **짧게만** 만들고 마커가 없으면 항등이다. U-1~U-7 이 정의역을 못 박고, U-16·U-19·S7 이 「워크트리 없는 프로젝트는 완전 동일」을 단언한다. 배포 후 첫 수집에서 카드 목록을 눈으로 대조(S8 마지막 항목) |
| **P-2** | **승자 요동** — 레포 루트 세션과 워크트리 세션이 둘 다 `/dashboard` 를 쓰면 mtime 승자가 번갈아 바뀌고, 열려 있는 패널의 내용이 예고 없이 다른 작업의 대시보드로 바뀐다(패널은 `location.pathname` 을 재fetch 한다) | 히스테리시스를 **넣지 않는다**(임의 상수의 근거가 없다 — 결정 WT6). 대신 **카드에 티어 1 제목이 렌더되므로 무엇으로 바뀌었는지는 화면에 드러난다.** 실제로 거슬리면 그때 히스테리시스나 승자 표식을 도입한다(재방문 트리거). **승인 요청 항목 3** |
| **P-3** | 개인 `/dashboard off` 사용자에게 워크트리 대시보드가 **되살아난다** | 위험 범위가 「개인 off 사용자」로 한정됨을 실측으로 확인(팀 off 는 워크트리에 전파되므로 안전). 허브는 오늘도 이 스위치를 모른다 — 새 문제가 아니라 기존 간극의 확대다. `hub/README.md` 에 한 줄 고지. **승인 요청 항목 4** |
| **P-4** | 「워크트리를 허브에서 숨기기」 손잡이 상실 | fold-first 의 구조적 귀결이다(결정 WT4). 요구를 낸 당사자가 정확히 반대를 요청했다. 되살리려면 `fold_worktrees: bool` 신설 — 지금은 YAGNI. **승인 요청 항목 2** |
| **P-5** | 티어 1 읽기 횟수 증가(멤버 수만큼 `is_file()`+`read`, 수집 주기 5초) | 워크트리 없는 프로젝트는 멤버 1개로 **완전히 동일**하다. 증가분은 실제 워크트리 수(현재 1)에 비례하고 상한이 명확하다. **측정된 병목이 아니므로 캐시를 넣지 않는다** — 모듈 전역 캐시는 테스트가 같은 모듈 객체를 공유해 순서 의존 실패를 만든다 |
| **P-6** | 상주 서버가 **옛 코드로 계속 돈다** → 「고쳤는데 화면이 그대로」로 오진 | S8 의 2단계(`install.sh --force` → `/hub server restart`)를 검증 절차에 못 박았다. 낡은 설치본에서 restart 하면 argparse 가 깨지므로 순서가 중요하다 |
| **P-7** | 접기 실패가 **화면에 아무 신호도 안 남긴다**(`unresolved_dir_names` 는 렌더되지 않는다) | 단위 테스트가 유일한 안전망임을 인정하고, 그래서 U-1~U-21 이 순수 함수 이음매를 전부 덮는다(결정 WT12). 진단 출력은 만들지 않는다 |
| **P-8** | 배포 직후 화면이 **즉시** 바뀐다(과거 2일치 워크트리 세션이 갑자기 합류하고 `snapshot_content_key` 가 바뀌어 `hub.html` 이 1회 재작성된다) | 정상 동작이다. S8 에 「어떤 카드가 어떻게 변하는지」 대조 항목을 넣었다 |
| **P-9** (2판) | **앵커 규칙이 정당한 후보를 막는다** — 관측 cwd 로만 알려진 프로젝트는 영원히 카드가 되지 않는다 | **의도된 동작이다.** 카드는 「세션 그룹 키 또는 스캔 경로」에서만 생긴다는 오늘의 규칙을 **그대로 유지**하는 것이고, 실데이터에서 루트 집합이 변하지 않음을 확인했다(E15). 만약 「이벤트 cwd 로만 아는 프로젝트도 카드가 돼야 한다」는 요구가 생기면 그것은 **별개의 기능 요구**이지 이번 결함의 일부가 아니다 |
| **P-10** (2판) | `observed_cwds` 에 **기본값이 없어서** 앞으로 `SessionFacts` 를 만드는 코드가 전부 이 필드를 대야 한다 | **의도된 마찰이다**(결정 WT19). 기본값 `()` 를 주면 픽스처가 조용히 「관측 cwd 없음」이 되고 `in observed_cwds` 판정이 언제나 거짓이 된다 — **이번 결함과 같은 모양의 구멍**. T25-115 가 기본값이 슬쩍 붙는 것을 감시한다. 비용은 픽스처 8곳(전부 키워드 인자, 한 줄씩) |
| **P-11** (2판) | **P-2 가 이론에서 즉시 활성으로 승격된다** — 승자 요동이 이번에 처음으로 실제 관측 가능해진다(초판 구현에서는 워크트리가 후보에 들어간 적이 없다, E11) | 히스테리시스는 여전히 넣지 않는다(WT21). 대신 **S8 의 C-2 가 이 전환을 의도적으로 한 번 일으켜 본다** — 사용자가 실물을 보고 거슬리는지 판단할 수 있게 한다. 거슬린다면 그때 히스테리시스나 승자 표식을 도입한다 |
| **P-12** (2판) | 「이전 작업」 라벨이 **이제 실제로 켜질 수 있다.** 초판 구현에서는 워크트리 승자일 때 live 집합이 항상 비어 라벨이 늘 꺼져 있었다(E15) | 정상 동작이며 결정 GN1 의 원래 의도다. 라벨이 처음 켜지는 것을 「회귀」로 오인하지 않도록 여기 적어 둔다. U-24 가 켜지는 조건을 못 박고, U-25 가 꺼지는 조건을 못 박는다 |

---

## 11. 구현 마일스톤

| 단계 | 내용 | 완료 기준 |
|------|------|-----------|
| **M0** | 이 PRP 승인 | 「승인 요청 항목」 1~7 회신 |
| **M1** (단계 1 — fold) | `hub_project.py` 상수 + `fold_worktree_path` + `group_paths_by_repo_root`, `hub_collect.py` 그룹 키·후보 조립 | U-1~U-7·U-11~U-13·U-21 통과, **기존 375건 전량 통과**. 여기서 커밋 경계 |
| **M2** (단계 2 — 티어 1 출처) | `hub_parse.py` 필드, `hub_collect.py` `_read_tier1_for_root`, `hub_project.py` `select_tier1_source` + GN 좁히기, `hub_model.py` registry | U-8~U-10·U-14~U-20 통과 |
| **M3** | `tests/run.sh` T25-111~114 + 뮤테이션 검증 5건 | `bash tests/run.sh` 통과, 뮤테이션 5건 전부 「기대한 테스트가 실패」 확인 |
| **M4** | 문서 — `hub/README.md` 2곳 + 이관 표기 6곳 | grep 으로 표기 존재 확인 |
| **M5** | 실환경 검증 (초판) | ~~S8 체크리스트 5항목~~ → **실패**. 2판의 M6~M9 로 이어진다 |
| **M6** (2판) | 이 개정 승인 | 「승인 요청 항목」 8~11 회신 |
| **M7** (2판, 데이터) | `hub_session.py` — `observed_cwds` 누적·동결 + 픽스처 8곳 갱신 | U-28·U-29 통과, **기존 403건 전량 통과**. 여기서 커밋 경계 |
| **M8** (2판, 배선) | `hub_project.py` — `plan_tier1_candidates` 입력 교체 + 앵커 조건, `_live_session_start_times_ms` 비교 교체 | U-27·U-30·U-24·U-25 통과 |
| **M9** (2판, 이음매·게이트) | `CollectSnapshotWorktreeTier1Test` 신설 + `tests/run.sh` T25-115~118 + 뮤테이션 9~13 | U-22·U-23·U-26 통과, `bash tests/run.sh` 통과, **뮤테이션 9 를 넣었을 때 U-22·U-27 이 둘 다 실패함을 눈으로 확인** |
| **M10** (2판) | 실환경 재검증 | S8 의 **G → V → C** 순서. G 단계 출력을 보고서에 첨부 |

---

## 12. 검토했으나 채택하지 않은 대안

| 대안 | 기각 사유 |
|------|-----------|
| `ignore_globs` 기본값에서 워크트리 glob 제거 | config 가 통째 대체라 **요구를 낸 당사자에게 도달하지 못한다**. 게다가 접기에 실패한 워크트리가 **별도 카드로 나타나** 요구를 정면으로 위반한다(결정 WT4) |
| `fold_worktrees: bool` config 필드 신설 | 요청되지 않은 설정 가능성. `HubConfig`·`_CONFIG_FIELD_TYPES`·README 표 동시 변경. 필요해지면 그때(P-4 재방문) |
| git 서브프로세스로 소유 레포 판정 | 수집 루프가 5초 주기다. `hub_collect` 에 서브프로세스라는 새 실패 경로가 생기고, 순수 레이어에서 접기를 못 하게 된다(결정 WT3) |
| `<worktree>/.git` 평문 파일 파싱 | 정확도가 조금 오르지만 접기가 I/O 레이어로 내려가 단위 테스트에 디렉토리 트리 빌더가 필요해진다. 관례 밖 워크트리는 **오늘도 별도 카드**라 회귀가 아니다 |
| 티어 3 인코딩명도 접기 | 화면 기여 0인데 `:284` 대입과 `:379` 컴프리헨션 두 곳을 max 병합으로 바꿔야 하고 기존 테스트 1건을 뒤집는다(결정 WT5) |
| `ProjectView.tier1_source_path` 필드 | tier1 과 동기화돼야 하는 값을 **네 번째 병렬 dict** 로 나른다. `Tier1Snapshot` 에 넣으면 `file_mtime_ms` 선례와 정확히 같은 모양이 된다(결정 WT7) |
| 티어 1 후보를 N개 노출(카드에 여러 대시보드) | `ProjectView.tier1` 단수 → 라우트 정규식(키 1 : 대시보드 1) → 패널 UI 재설계로 번진다. `dashboard-ownership-guard.md` R4 안 1 의 전면 도입이며 이번 범위를 크게 넘는다 |
| 승자 결정에 히스테리시스(`stale_after_minutes` 재사용 등) | 임의 상수의 근거가 될 측정치가 없다. 요동이 실제로 관측되면 그때(P-2) |
| `SessionFacts.cwd` 를 마지막 이벤트 cwd 로 | flip 을 반대 방향으로 뒤집을 뿐이다(결정 WT14) |
| 세션 줄에 워크트리 라벨 표시 | `SessionView` 신규 필드 → `#dzh-data` 계약 → 템플릿 → T25 검사로 범위가 두 배. 카드 제목(티어 1 `#dz-title`)이 이미 식별 수단이다(결정 WT11) |
| 진단용 `collect --json` 확장 | `#dzh-data` 로 이미 기계 검증이 가능하다. `projects` 개수는 fold 검증에 **방향이 케이스마다 다른** 애매한 신호다(결정 WT12) |
| fold 로직을 새 모듈(`hub_worktree.py`)로 분리 | 25줄을 위해 「15개 파일」 리터럴 4곳과 배포 게이트를 흔든다(결정 WT13) |
| **(2판)** 이벤트 원본 cwd **집합**을 `plan_tier1_candidates` 인자로 추가 (쟁점 1 후보 a) | 결함 A 는 고치지만 **쟁점 3 을 구조적으로 못 고친다** — 집합에는 어느 세션의 cwd 인지가 없는데 「이전 작업」 판정은 세션 단위다. 실측으로 live 집합이 0 이 되어 라벨이 **우연히** 맞는 상태가 된다(E15). 게다가 `plan_tier1_candidates` 시그니처와 `collect_snapshot` 배선이 바뀐다(결정 WT16) |
| **(2판)** 레포 루트의 `.claude/worktrees/` 디렉토리 스캔 (쟁점 1 후보 b) | **★순수 계층에서 못 한다** — `hub_collect` 로 내려가 결정 WT3 이 이미 기각한 구조가 된다. 수집 주기(5초)마다 디렉토리 I/O 가 늘고, **이벤트 없는 워크트리까지 상시 후보**가 돼 승자 요동(P-2) 표면적이 넓어진다. 고유 능력(이벤트 없는 워크트리)이 지금 필요 없다 — 이 사용자의 워크트리는 1개이고 그것은 이벤트를 낸다(실측) |
| **(2판)** `observed_cwds` 에 기본값 `()` 를 준다 | 픽스처 8곳을 안 고쳐도 되지만, 손으로 만든 세션이 조용히 「관측 cwd 없음」이 되어 `in observed_cwds` 판정이 언제나 거짓이 된다. **이번 결함과 같은 모양의 구멍**을 테스트 쪽에 새로 파는 것이다(결정 WT19) |
| **(2판)** 앵커 없이 관측 cwd 를 그대로 티어 1 루트로 | 프로젝트 **하위 디렉토리** cwd 가 카드를 하나 더 만든다. 그런 입력이 실데이터에 실제로 있다(E14). 「카드를 합쳐 달라」는 요구의 정반대(결정 WT17) |
| **(2판)** 중간 함수 테스트를 더 촘촘히 해서 이음매를 덮는다 | 이번 결함이 **정확히 그 방식으로** 검수를 통과했다. 손 입력이 프로덕션의 데이터 흐름을 재현하지 않으면 몇 개를 더해도 같은 구멍이 남는다(결정 WT20) |
| **(2판)** `SessionFacts.cwd` 를 워크트리로 바꾸는 별도 필드 없는 해법 | WT14 가 기각한 세 안(정규화·마지막 이벤트·첫 비무시)의 재탕이다. 어느 쪽이든 GN 판정에 필요한 원본이 소실된다 |

---

## 13. 승인 요청 항목 (한눈에 보기)

| # | 쟁점 | 권고 | 다른 선택이 가능한가 |
|---|------|------|---------------------|
| 1 | **범위** — fold 만인가, 티어 1 출처 확장까지인가 | **둘 다**(단계 1 → 2) | ○ 단계 2 를 잘라낼 수 있다. 그러면 **결함 A(어제 100% + 「이전 작업」 상시 점등)는 그대로 남는다** |
| 2 | **`ignore_globs` 처리** | 기본값·사용자 config **무변경**, fold 를 ignore **앞에** | ○ 기본값에서 제거(단 이 사용자에게 안 켜짐) / 별도 스위치 신설 |
| 3 | **티어 1 승자 규칙** | **mtime 최신, 동률은 레포 루트** | ○ 레포 루트 고정(결함 A 유지) / 히스테리시스 도입 |
| 4 | **`dashboard_enabled` 충돌** | **무시 + 문서화**(위험은 개인 off 사용자 한정) | ○ 워크트리 파일을 티어 1 후보에서 제외(= 항목 1 의 단계 2 포기와 같음) / 허브가 스위치를 읽음(프로젝트 로컬 파일 계약 +1) |
| 5 | **GN 세대 판정** | **티어 1 출처와 같은 cwd 의 세션만** — GN2 개정 | ○ 워크트리 세션 통째 제외 / 판정 포기 |
| 6 | **티어 3 접기** | **하지 않는다**(화면 기여 0, 기존 테스트 2건 보존) | ○ 접는다(그러면 `:284`·`:379` max 병합 + 테스트 1건 반전) |
| 7 | **화면 표시** | **변경 0** — 워크트리 라벨을 만들지 않는다 | ○ `SessionView` 에 라벨 필드 추가(범위 약 2배) |
| **8** (2판) | **워크트리 발견 경로** — 쟁점 1 | **`SessionFacts.observed_cwds` 신설**(후보 c) | ○ 이벤트 cwd 집합을 인자로(후보 a — 쟁점 3 을 못 고침) / 디렉토리 스캔(후보 b — ★순수 계층 이탈) |
| **9** (2판) | **카드 중립성 앵커** | **관측 cwd 는 멤버만 늘리고 루트를 새로 만들지 않는다** | ○ 앵커 없이 허용(하위 디렉토리 cwd 가 카드를 쪼갠다 — E14) |
| **10** (2판) | **`observed_cwds` 기본값** | **기본값 없음** — 픽스처 8곳이 값을 반드시 대게 한다 | ○ 기본값 `()`(픽스처 수정 0곳, 대신 GN 테스트가 조용히 무력해진다) |
| **11** (2판) | **S8 절차** | **G(사전 조건) → V(정적) → C(인과)** 3단계. G-1 불성립 시 확인 중단 | ○ 초판처럼 정적 확인만(이번 라운드에서 그것이 통과 후 실패로 드러났다) |

### 항목별 상세

**항목 1 — 범위.** 단계 1 만 하면 「모레 자정에 세션이 사라지는 일」은 막지만, 사용자가 **지금
화면에서 보고 있는 잘못**(어제 작업의 100%, 「이전 작업」 라벨)은 하나도 안 고쳐진다. 두 단계가
`group_paths_by_repo_root` 의 멤버 목록을 공유하므로 함께 만드는 비용이 따로 만드는 비용보다 싸다.

**항목 2 — `ignore_globs`.** 이 선택이 **「이 사용자에게 기능이 켜지는가」를 직접 결정한다.**
사용자의 실제 `~/.claude/hub/config.json` 이 기본값 3개를 복제해 두었고, config 는 병합이 아니라
통째 대체다. 기본값만 고치는 안은 켜지지 않는다.

**항목 3 — 승자 규칙.** mtime 최신을 고르면 **지금 이 순간 워크트리 파일이 이긴다**(E4: 워크트리
11:06 vs 루트 어제 17:54). 즉 요구가 곧바로 만족된다. 대가는 P-2(승자 요동)이고, 그것이 실제로
거슬리는지는 써 봐야 안다.

**항목 4 — `dashboard_enabled`.** 세 안의 **비용 등급이 크게 다르다**: 무시 = 코드 0 / 후보 제외 =
결함 A 포기 / 허브가 읽음 = **허브 역사상 두 번째 프로젝트 로컬 파일 계약** + T23-7 확장. 지금 이
레포에서는 스위치가 켜져 있어(필드 자체가 없음) **관측된 손상이 아니라 구조적 추론**이다.

**항목 5 — GN 판정.** 권고안은 축소가 아니라 **정정**이다(`/dashboard` 가 cwd 상대경로에만 쓰므로,
파일을 갱신하는 주체는 그 cwd 의 세션뿐이다). 비워크트리 프로젝트에서는 완전한 무동작이라 기존 GN 표
8행이 그대로 유효하다.

**항목 6 — 티어 3.** 접지 않으면 기존 테스트 2건(M15·티어 3 인코딩명 제외)을 **하나도 뒤집지
않는다**. 접으면 조용히 덮어쓰는 두 지점을 max 병합으로 고쳐야 하는데, 그 대가로 얻는 것은 화면에
드러나지 않는 값 하나다.

**항목 7 — 화면 표시.** 「어느 워크트리인지」는 카드에 이미 렌더되는 **티어 1 대시보드 제목**으로
구분된다(E4 의 두 제목은 완전히 다르다). 라벨 필드를 만들면 `SessionView` → `#dzh-data` 계약 →
템플릿 → T25 검사까지 파급된다.

**항목 8 — 발견 경로(가장 중요한 결정).** 세 후보 모두 결함 A 를 고치지만 **쟁점 3(「이전 작업」
라벨)에서 갈린다.** (a)·(b)는 「이 레포에 워크트리가 있다」는 **레포 단위** 사실만 주는데, 라벨은
**세션 단위** 판정이다. 실측이 그 차이를 드러냈다(E15): (a)에서는 live 집합이 0 이라 라벨이
`if not live: return False` 로 **우연히** 꺼지고, (c)에서는 live 집합이 1 이라 **실제 시각 비교**로
꺼진다. 오늘 화면은 둘 다 같지만, 워크트리 파일이 먼저 쓰이고 세션이 나중에 워크트리로 들어온
경우에 (a)는 **틀린 답**을 낸다. 부수 효과로 (c)는 **어떤 함수 시그니처도 바꾸지 않는다.**

**항목 9 — 앵커.** 이 한 줄이 없으면 후보 확장이 **카드를 만들어 낸다**(`tier1_by_path` 의 키가
곧 프로젝트 경로다). 그런 입력이 가정이 아니라 **실데이터에 있다** — 8일 전수에서 한 세션의 cwd 가
프로젝트 하위 디렉토리로 튀었고(E14), 그곳에 `dashboard.html` 이 생기는 순간 한 프로젝트가 카드
둘로 쪼개진다. 앵커 규칙은 오늘의 루트 집합을 **정확히 재현**한다(E15 로 확인).

**항목 10 — 기본값.** 이것은 취향이 아니라 **이번 결함의 재발 방지**다. 기본값을 주면 손으로 만든
`SessionFacts` 가 조용히 「관측 cwd 없음」이 되고, `source_path in observed_cwds` 가 언제나 거짓이
되어 GN 테스트가 통째로 무력해진다 — **테스트가 프로덕션이 만들 수 없는 값을 검증하는** 정확히
같은 모양이다. 대가는 픽스처 8곳(전부 키워드 인자, 한 줄씩)이다.

**항목 11 — S8 절차.** 이번 라운드에서 **S8 만 결함을 잡았다.** 그런데 초판 S8 에는 유효 조건이
없었고, 창이 굴러 `SessionFacts.cwd` 가 이미 워크트리인 상태에서 확인했다면 **개정 전 코드로도
통과했을 것이다**(E12). G 단계는 그 vacuous pass 를 막고, C 단계는 「우연히 맞는 화면」을 막는다.
승인자가 이 절차를 무겁다고 판단하면 최소한 **G-1 만은 남겨 달라** — 나머지 없이도 그 한 줄이
이번과 같은 오판을 막는다.
