# 허브 — 한도 초기화 예정 시각 표시 + 펼침 시 즉시 갱신 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/` (통합 허브 대시보드) |
| 브랜치 | `feature/hub-dashboard` (HEAD `ac71456`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md) → [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md) → **이 문서** |
| 워크플로우 경로 | **전체 경로** (새 모듈 추가 · 데이터 모델 변경 · 새 CLI 서브커맨드 · 전역 `settings.json` 변경) |
| 규모 | Medium — 신규 2개 / 수정 10개 파일, 실행 코드 증분 약 200줄 + 템플릿 약 45줄 |
| 새 외부 의존성 | **없음** (python3 stdlib · 바닐라 JS/CSS 유지) |
| 승인 상태 | **승인됨** (2026-08-12) — 아래 「사용자 승인 확정 사항」 참조 |

---

## 사용자 승인 확정 사항 (2026-08-12)

「사용자 승인이 필요한 핵심 결정」 5건 중 실질적 분기가 있던 항목 2("상태줄에 무엇을 출력할
것인가")는 **안 A(퍼센트 한 줄, `세션 23% · 주간 41%`)로 확정**됐다. 나머지 4건(전역
`settings.json` 사용+충돌 시 거부, 배포 파일 11개, staleness="지나면 사라진다", 패널 게이팅
불변)은 본문 설계 그대로 승인됐다 — 이 문서의 해당 절을 재론하지 않는다.

---

## 요구사항 요약

허브의 사용량 패널은 지금 세션(5시간)·주간(7일) **사용률**만 보여 준다. "언제 초기화되는가"는
어디에도 없어서, 한도에 가까워졌을 때 사용자는 "얼마나 기다려야 하는지"를 알 수 없다.
이 PRP 는 두 가지를 더한다. **(1)** 패널을 **펼쳤을 때** 세션·주간 각각의 **초기화 예정 시각**을
표시한다. 출처는 Claude Code CLI 가 `statusLine` 명령에 stdin 으로 넘겨 주는 **공식 입력 JSON 의
`rate_limits.*.resets_at`** 이며, 이를 받아 파일로 남기는 캡처 스크립트를 새로 설치한다.
**(2)** 패널을 클릭해 펼치는 순간 다음 폴링(최대 5초)을 기다리지 않고 **그 자리에서 한 번 더**
최신 스냅샷을 받아 다시 그린다. 정기 폴링 주기(5초)와 데스크톱 앱의 사용량 갱신 주기(약 15분)는
**바꾸지 않는다.**

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 한도가 차오를 때 "몇 시에 풀리는지"를 패널을 펼쳐
> 곧바로 확인하고, 펼치는 그 순간의 최신 값을 보고 싶다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | `/hub statusline on` 후 Claude Code 세션을 1회 진행하면 `~/.claude/hub/rate_limits.json` 이 생기고 두 리셋 시각이 들어 있다 | 수동 M2 |
| S2 | 패널을 펼치면 세션·주간 막대 **각각 아래**에 `초기화 18:32 · 2시간 12분 뒤` 형태의 줄이 보인다 | 수동 M4 |
| S3 | 리셋 시각이 지나면 그 줄이 사라진다(과거 시각을 절대 표시하지 않는다) | 자동(단위) + 수동 M6 |
| S4 | 이미 다른 `statusLine` 이 설정돼 있으면 설치가 **거부**되고 기존 설정이 그대로 남는다 | 자동(단위) + 수동 M1b |
| S5 | 접힘 → 펼침 클릭 시 5초를 기다리지 않고 즉시 fetch 가 1회 발생한다 | 수동 M7(네트워크 탭) |
| S6 | `POLL_INTERVAL_MS`(5000)·`server_collect_interval_seconds`(5)·"약 15분 주기" 문구가 그대로다 | 자동 T25-41 |
| S7 | 캡처 파일이 없거나 깨져도 패널·수집이 종전대로 동작한다(실패 격리) | 자동(단위) |
| S8 | `bash tests/run.sh` 전체 통과(T25-38~42 신규 포함) | 자동 |

---

## 실측으로 확인된 사실 (재조사 대상 아님)

### 1. statusLine 입력 JSON 의 `rate_limits` (공식 스키마)

공식 문서(<https://code.claude.com/docs/en/statusline>)에 더해, **설치된 CLI 바이너리
(`~/.local/share/claude/versions/2.1.139`)에서 직접 확인**했다.

```js
// statusLine 입력 페이로드 조립부 (바이너리 내 실제 코드)
...(k.five_hour||k.seven_day)&&{rate_limits:k}, ...
// k 의 조립부
{...Z.five_hour&&{five_hour:{used_percentage:Z.five_hour.utilization*100,resets_at:Z.five_hour.resets_at}},
 ...Z.seven_day&&{seven_day:{used_percentage:Z.seven_day.utilization*100,resets_at:Z.seven_day.resets_at}}}
// 다른 지점: new Date(q.resets_at*1000) — 단위가 '초'임을 확정
```

| 사실 | 내용 | 설계에 미치는 영향 |
|------|------|-------------------|
| `resets_at` 단위 | **UNIX epoch 초** (`*1000` 으로 Date 생성) | 캡처 시점에 ms 로 변환해 저장한다(레포 전체가 ms) |
| `used_percentage` | `utilization * 100` → **실수**(23.5 등) | 기존 `UsageSample` 의 엄격 int 규칙(U2)과 타입이 다르다 → **캡처하지 않는다**(결정 S7) |
| `rate_limits` 키 | `five_hour` 또는 `seven_day` 가 **하나라도 있을 때만** 존재 | 필드 부재는 정상. 두 창은 **각각 독립적으로** 없을 수 있다 |
| 등장 시점 | Claude.ai 구독자(Pro/Max)의 세션에서 **첫 API 응답 이후**부터 | 세션이 하나도 안 돌면 새 값이 오지 않는다(= 캡처가 낡는다) |
| 실행 주체 | 사용자가 `settings.json` 에 등록한 임의의 셸 명령. CC 가 stdin 으로 위 JSON 전체를 준다 | 우리는 **stdout 이 아니라 부수효과(파일 쓰기)** 를 노린다 |
| 실행 빈도 | 문서상 **최대 0.3초마다**(메시지 갱신 시) | 아래 「비용 실측」 참조 — 정상 상태에서 파일을 쓰지 않는 설계가 필수 |

### 2. 현재 사용자의 `settings.json` 상태 (확인함)

`~/.claude/settings.json` 의 최상위 키는 `agentPushNotifEnabled`·`model`·`theme` 뿐이고
**`statusLine` 은 없다.** 프로젝트 `.claude/settings.local.json` 에도 없다(`permissions` 만 존재).
→ 지금은 충돌이 없다. 그러나 **설계는 "이미 남의 statusLine 이 있는 경우"를 반드시 다룬다**(결정 S4).

### 3. 비용 실측 — `hub_statusline.py` 의 임포트 선택 근거

같은 머신에서 python3 프로세스 1회 기동 비용(중앙값, n=10):

| 구성 | 중앙값 | 최소 |
|------|--------|------|
| `python3 -c pass` | 18.9ms | 18.3ms |
| stdlib 만 (`json,os,sys,tempfile,pathlib`) | 28.5ms | 27.8ms |
| `+ import hub_usage` | **29.2ms** | 26.7ms |
| `+ import hub_collect` | **42.0ms** | 40.8ms |

→ `hub_usage`(순수, `json`+`dataclasses` 만 임포트)는 **사실상 공짜**, `hub_collect` 는 약 **+13ms**.
이 수치가 결정 S5 의 근거다.

### 4. 기각된 대안 — 데스크톱 앱 히스토리에서 리셋 시각을 추정

`~/Library/Application Support/Claude/plan-usage-history.json` 에는 **창의 시작·종료 시각이
아예 없다**(`t`·`u.fh`·`u.sd` 뿐). 급락 지점으로 리셋을 역산할 수는 있으나 앱이 꺼져 있던
구간(실측 최대 간격 2.4일)만큼 오차가 생긴다. 사용자가 명시적으로 공식 API 조사를 요청했고,
위 1번이 그 답이다. → **추정 금지. 공식 값만 쓴다.**

---

## 확정된 전제 (재론하지 않는다)

1. **단일 정적 HTML, 빌드 단계 없음.** 프레임워크·CDN·JS 테스트 러너를 도입하지 않는다.
2. **허브 서버는 읽기 전용 2경로 화이트리스트다**(`hub_server.py:21`). 브라우저가 서버에
   "지금 다시 수집하라"고 시킬 수 있는 엔드포인트를 만들지 않는다(요구 2의 해석 근거).
3. **기존 결정 U1~U4 · H1′ 는 그대로다.** 이 PRP 는 그 위에 얹는 증분이며, 이전 결정을
   폐기하지 않는다(확장 표기만 추가 — 아래 「구 PRP 확장 표기」).
4. **`show_usage_panel:false` 는 여전히 "읽지 않는다"** — 캡처 파일도 읽지 않는다.
5. 새 색 리터럴을 도입하지 않는다(`var(--muted)` 만 참조) → 라이트/다크·T25-29 자동 통과.

---

## 영향 범위

### 신규 파일 (2개)

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_statusline.py` | statusLine 진입점(I/O). stdin → 파싱 → 변화 시에만 캡처 파일 쓰기 → 상태줄 한 줄 출력. **배포 파일 10 → 11** |
| `tests/hub/test_hub_statusline.py` | 위 진입점의 계약(항상 exit 0 · 무변화 시 미기록) 테스트 |

### 수정 파일 (10개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_usage.py` | dataclass 1개 + 순수 함수 4개 + 상수 3개 (약 80줄) | 한도 관련 외부 계약 파서의 자리(결정 S2) |
| `hub/bin/hub_model.py` | `HubSnapshot` 에 `rate_limit_resets` 필드 1개 | 페이지에 인라인되는 데이터 정의가 여기다 |
| `hub/bin/hub_collect.py` | 경로 상수 1개, 공개 함수 2개, 사설 함수 1개, `collect_snapshot` 배선 3줄 | 파일시스템에 닿는 유일한 모듈 |
| `hub/bin/hub_settings.py` | 상수 3개 + 예외 1개 + 순수 함수 3개 + I/O 함수 3개 (약 70줄) | `settings.json` 소유권을 가진 유일한 모듈 |
| `hub/bin/hub.py` | 서브커맨드 2개, `cmd_status` 진단 필드 3개 | CLI 조립 |
| `hub/bin/hub_template.html` | CSS 규칙 1개 + JS 함수 3개 + `renderUsagePanel` 시그니처 1개 + 토글 핸들러 3줄 | 화면 |
| `hub/install.sh` | `HUB_FILE_COUNT=10` → `11`, `--uninstall` 에 `uninstall-statusline` 1줄 | 배포 파일 증가 + 제거 순서(결정 S8) |
| `hub/README.md` | "10개" → "11개"(2곳), 「한도 초기화 예정 시각」 절 신설, 프라이버시 고지 1항, 파일 배치 1행, 제거 절 1행 | T25-1/T25-40/T25-42 및 문서 정합 |
| `commands/hub.md` | `argument-hint` 갱신, `/hub statusline on\|off` 절 2개, `/hub status` 필드 3개 설명 | 서브커맨드·상태 필드가 문서와 어긋나지 않게 |
| `tests/run.sh` | T25-38~42 추가, `test_desc` 를 `(T25-1~T25-42)` 로 갱신 | grep 회귀 방지 |

기존 테스트 파일 3개(`test_hub_usage.py`·`test_hub_settings.py`·`test_hub_collect.py`·
`test_hub_model.py`)에도 케이스를 추가한다(아래 「테스트 계획」). 위 표의 "수정 파일 10개"는
실행 코드·문서 기준이며 테스트 파일은 별도로 센다.

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_parse.py` | 티어 1(`/dashboard` DOM) 파서. 접점 없음 |
| `hub/bin/hub_server.py` | 수집 루프는 `collect_snapshot()` 만 부른다 — 배선은 그 안에서 끝난다 |
| `hub/bin/hub_daemon.py`·`hub_hook.py` | 프로세스·훅 관리. statusLine 은 훅이 아니다(별도 최상위 필드) |
| `tests/hub/fixtures/*.html` | 전부 `/dashboard` 생성물이며 `test_hub_parse.py` 만 읽는다 |
| `commands/dashboard.md`·루트 `install.sh`·루트 `README.md` | 허브와 분리된 자산(T25-21·T25-22 가 이 분리를 강제한다) |
| `HubConfig`(= `config.json` 스키마) | **새 config 필드를 만들지 않는다** — 표시 스위치는 `show_usage_panel` 하나로 충분하고, 캡처 on/off 는 `/hub statusline on\|off` 가 담당한다(결정 R3-b) |

---

## 파일 구조와 모듈 경계

```
hub/bin/
├── hub_usage.py       ★순수 (확장)  plan-usage-history.json → UsageSample | None
│                                    statusLine JSON / 캡처 파일 → RateLimitResets | None
├── hub_parse.py       ★순수         /dashboard DOM → Tier1Snapshot | None
├── hub_model.py       ★순수         이벤트 → 사실 → 표시 상태, HubSnapshot 정의, 렌더
├── hub_collect.py      I/O          파일 읽기·쓰기 · 스냅샷 조립
├── hub_settings.py     I/O          ~/.claude/settings.json 소유권(훅 6개 + statusLine)
├── hub_statusline.py   I/O (신규)   statusLine 진입점 — stdin → 캡처 파일 → stdout 한 줄
├── hub_hook.py         I/O          훅 진입점 (선례: 진입점은 hub_collect 를 임포트한다)
└── hub.py / hub_server.py / hub_daemon.py / hub_template.html
```

**의존 방향**: `hub_statusline → {hub_usage, hub_collect}`, `hub_collect → {hub_model, hub_parse,
hub_usage}`, `hub_model → hub_usage`. `hub_usage` 는 아무것도 임포트하지 않는다 → **순환 없음.**
`hub_hook.py`(진입점 → `hub_collect`)와 완전히 같은 모양이다.

### 결정 S2 — 새 파서를 `hub_usage.py` **안에** 넣는다 (새 순수 모듈을 만들지 않는다)

**근거**

1. **같은 관심사다.** `hub_usage.py` 의 존재 이유는 "한도 사용에 관한 외부 포맷을 안전하게
   읽는 순수 파서"다. `plan-usage-history.json`(퍼센트)과 statusLine `rate_limits`(리셋 시각)는
   **같은 패널 하나를 채우는 두 조각**이다. 갈라 두면 "이 패널의 데이터 규칙"이 두 파일에
   흩어진다.
2. **크기가 문제되지 않는다.** 현재 95줄 → 약 175줄. 전역 지침 권장 범위(200~400) 안이다.
   `hub_model.py`(569줄)에 넣을 수 없었던 M1 의 상황과 다르다.
3. **비용이 실재한다.** 순수 모듈을 하나 더 만들면 배포 파일이 12개가 되고
   `HUB_FILE_COUNT`·README 문구·T25-10 목록을 또 고쳐야 한다. 이번에 이미 진입점 1개 때문에
   11개로 올리는데, 근거가 약한 12번째를 더할 이유가 없다.

**비용(정직하게)**: 모듈 docstring 을 "히스토리 포맷 파서" → "한도 관련 외부 계약 파서 모음"으로
넓혀야 한다. T25-10 의 순수 경계 검사(`open(`·`Path(`·`os.` 부재)는 그대로 적용된다 —
**새 함수도 파일시스템·시각에 닿지 않는다**(`captured_at_ms`·`now_ms` 는 항상 인자로 받는다).

### 결정 S5 — `hub_statusline.py` 는 `hub_collect` 를 임포트한다 (측정 기반)

statusLine 은 최대 0.3초마다 실행되므로 임포트 비용이 문제가 될 수 있다. 실측(위 「비용 실측」)은
`hub_collect` 임포트가 **+13ms**(28.5 → 42.0ms)임을 보여 준다. 그럼에도 임포트를 택한다:

- **경로와 원자적 쓰기의 정본이 하나여야 한다.** 이 레포는 같은 로직의 사본이 갈라져 운영
  경로와 테스트 대상이 달라진 사고(검수 m3, `parse_server_record`)를 이미 겪었고 그때
  **중복을 제거하는 쪽**으로 결론냈다. `RATE_LIMITS_PATH` 를 두 파일에 각각 두면 한쪽만
  바뀌었을 때 **캡처는 성공하는데 아무도 읽지 않는** 무성음 실패가 된다.
- **13ms 는 총 42ms 의 일부이고, 바닥값 19ms 는 어떤 선택으로도 못 줄인다.** 30% 절감을 위해
  단일 정본을 포기하는 거래는 남는 장사가 아니다.
- **진짜 비용은 임포트가 아니라 파일 쓰기다.** 결정 S3(변화 시에만 쓴다)이 정상 상태의 쓰기를
  0회로 만든다. 읽기는 100바이트 캐시 히트다.

→ 그래도 비용이 문제라면 되돌리기는 국소적이다(대안 5 참조). **승인 항목이 아니라 기록으로 남긴다.**

---

## 데이터 모델

### 신규 — `hub_usage.py`

```python
MILLISECONDS_PER_SECOND = 1000
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
# 리셋 시각이 캡처 시각으로부터 이 범위를 벗어나면 버린다. 목적은 '초 ↔ 밀리초' 단위 혼동을
# 잡는 것이다(단위가 틀리면 1000배 어긋나므로 임계값의 정확한 크기는 중요하지 않다).
# 8 = 가장 긴 창(7일) + 하루 여유.
RATE_LIMIT_MAX_HORIZON_DAYS = 8
RATE_LIMIT_MAX_HORIZON_MS = RATE_LIMIT_MAX_HORIZON_DAYS * MILLISECONDS_PER_DAY


@dataclass(frozen=True)
class RateLimitResets:
    """Claude Code statusLine 이 알려 준 한도 창의 초기화 예정 시각. 창은 각각 없을 수 있다."""

    captured_at_ms: int                 # 이 값들을 '처음 관측한' 시각(결정 S3 — 마지막 관측이 아니다)
    session_resets_at_ms: int | None    # rate_limits.five_hour.resets_at (초 → ms 변환됨)
    weekly_resets_at_ms: int | None     # rate_limits.seven_day.resets_at (초 → ms 변환됨)
```

**불변식**: `session_resets_at_ms` 와 `weekly_resets_at_ms` 가 **둘 다 `None` 인 인스턴스는 만들지
않는다** — 파서가 그 경우 `None` 을 돌려준다. "빈 껍데기"를 스냅샷에 싣지 않는다(요구 2의 정신).

### 변경 — `hub_model.HubSnapshot`

```python
@dataclass(frozen=True)
class HubSnapshot:
    collected_at_ms: int
    projects: tuple[ProjectView, ...]
    unresolved_dir_names: tuple[str, ...]
    warnings: tuple[str, ...]
    usage: UsageSample | None = None
    rate_limit_resets: RateLimitResets | None = None   # ★신규. 없으면 리셋 줄을 그리지 않는다
```

- `usage` **뒤**에 둔다 — 기본값 있는 필드의 순서 제약을 만족하고, 키워드 인자를 쓰는 기존 테스트
  헬퍼(`_minimal_snapshot()`)가 무수정 통과한다.
- `asdict()` 가 중첩 dataclass 를 펴므로 JSON 계약은 `"rate_limit_resets": {...} | null` 이 된다.

### 결정 R1 — `UsageSample` 에 필드를 더하지 않고 **별도 필드**로 둔다

`UsageSample` 의 docstring 은 "`plan-usage-history.json` 의 마지막 샘플"이다. 출처가 다른 값
(Claude Code CLI)을 그 안에 섞으면 그 문장이 곧 거짓이 되고, 엄격 int 검증(U2)의 적용 범위도
흐려진다. **출처가 둘이면 데이터클래스도 둘이다.** 렌더 시점에 둘을 합치는 비용은 인자 하나뿐이다.

### 결정 S3 — 캡처 파일은 **값이 바뀔 때만** 쓴다 (결정 D3 의 직접 귀결)

`captured_at_ms` 를 "마지막으로 본 시각"으로 매번 갱신하면, statusLine 이 도는 동안
`snapshot_content_key()` 가 **매 5초 사이클마다 달라져** `hub.html` 이 무조건 재작성되고 브라우저는
매번 전체 재파싱·재렌더를 한다. 이는 결정 D3(now 파생값 금지)이 막으려던 바로 그 폭주다.

→ `hub_statusline.py` 는 기존 캡처를 읽어 **리셋 시각 두 개가 모두 같으면 아무것도 쓰지 않는다.**
그 결과 `captured_at_ms` 의 뜻은 **"이 리셋 시각을 처음 관측한 시각"** 이 된다. 고정된 미래
시각에 대해서는 "마지막으로 봤다"보다 "언제부터 알고 있었다"가 더 정확한 정보이기도 하다.

부수 효과로 최대 0.3초마다의 원자적 쓰기(mkstemp+rename)가 정상 상태에서 **0회**가 된다.

### 캡처 파일 — `~/.claude/hub/rate_limits.json`

```json
{"captured_at_ms": 1786433123899, "session_resets_at_ms": 1786440000000, "weekly_resets_at_ms": 1786872000000}
```

- 위치는 기존 상태 파일들(`server.json`·`last_collect_error.json`)과 같은 `HUB_HOME` 직하.
- `hub/install.sh --uninstall` 은 이 파일을 지우지 않는다(사용자 데이터 보존 원칙) — 완료
  메시지의 잔존 파일 목록에 1행을 더한다.

---

## 인터페이스

### `hub_usage.py` (순수 — 파일시스템·시각·환경에 닿지 않는다)

```python
def parse_status_line_rate_limits(text: str, captured_at_ms: int) -> RateLimitResets | None:
    """statusLine stdin JSON 에서 두 창의 초기화 예정 시각을 읽는다. 쓸 값이 없으면 None."""

def parse_rate_limit_capture(text: str) -> RateLimitResets | None:
    """우리가 쓴 캡처 파일을 되읽는다. 계약이 안 맞으면 None(예외를 던지지 않는다)."""

def drop_passed_resets(resets: RateLimitResets, now_ms: int) -> RateLimitResets | None:
    """이미 지난 초기화 시각을 버린다 — 지난 값은 더 이상 참이 아니다. 둘 다 지났으면 None."""

def same_reset_times(previous: RateLimitResets | None, current: RateLimitResets) -> bool:
    """캡처 시각을 뺀 리셋 시각 두 개가 같은가 — 같으면 다시 쓰지 않는다(결정 S3)."""

def format_status_line_summary(text: str) -> str:
    """statusLine stdin JSON 으로 터미널 상태줄 한 줄을 만든다. 쓸 값이 없으면 빈 문자열."""
```

**검증 규칙 (한 곳에 모은다)**

| 대상 | 규칙 | 근거 |
|------|------|------|
| `resets_at`(초) | 엄격 int(bool 배제) — 기존 `_is_valid_epoch_ms` 재사용 | U2 와 같은 규칙. 규칙이 하나면 설명도 테스트도 하나다 |
| 변환 후 ms | `captured_at_ms < value <= captured_at_ms + RATE_LIMIT_MAX_HORIZON_MS` | 단위 혼동(초↔ms)과 과거 값을 한 번에 잡는다 |
| `rate_limits` 없음 | `None` (경고 없음) | 구독 종류·세션 초반에 정상적으로 발생한다 |
| 두 창 중 하나만 유효 | 유효한 쪽만 담은 인스턴스 | 문서가 "각 창은 독립적으로 없을 수 있다"고 명시 |
| 두 창 모두 무효 | `None` | 빈 껍데기 금지 |
| `used_percentage` | **읽지 않는다** | 결정 S7 |

`format_status_line_summary` 만 `used_percentage` 를 본다(화면 출력 전용, 캡처하지 않는다).
`Math.floor` 와 같게 내림하고, 실수·정수 모두 허용하되 bool 은 배제하고 0~100 범위 밖은 생략한다.

### `hub_collect.py` (I/O)

```python
RATE_LIMITS_PATH = HUB_HOME / "rate_limits.json"

def read_rate_limit_capture() -> tuple[hub_usage.RateLimitResets | None, tuple[str, ...]]:
    """캡처 파일을 읽어 판다. 이 함수는 절대 예외를 던지지 않는다."""

def write_rate_limit_capture(resets: hub_usage.RateLimitResets) -> None:
    """캡처를 원자적으로 쓴다(hub_statusline.py 전용 쓰기 경로). _atomic_write_text 재사용."""

def _rate_limit_resets_for_snapshot(
    now_ms: int, config: hub_model.HubConfig
) -> tuple[hub_usage.RateLimitResets | None, tuple[str, ...]]:
    """스위치 · 만료(지난 값)까지 적용해 화면에 실을 리셋 시각을 고른다(사설)."""
```

**반환 계약** (`read_latest_usage_sample` 의 표와 같은 격):

| 상황 | 값 | 경고 | 근거 |
|------|-----|------|------|
| `show_usage_panel: false` | `None` | 없음 | 파일을 **열지도 않는다**(U4 와 동일) |
| 캡처 파일 없음 | `None` | **없음** | statusLine 미설치·미실행이 정상 상태다 |
| 읽기 실패(권한 등) | `None` | 1건 | 파일은 있는데 못 읽는 건 비정상 |
| 계약 불일치(손상·수기 편집) | `None` | 1건 | 사용자가 알아야 한다 |
| 리셋 시각이 전부 지남 | `None` | **없음** | 세션을 안 돌렸을 뿐이다. 정상 시나리오 |
| 한쪽만 지남 | 남은 쪽만 | 없음 | |
| 정상 | `RateLimitResets` | 없음 | |

`collect_snapshot()` 배선(3줄):

```python
    rate_limit_resets, rate_limit_warnings = _rate_limit_resets_for_snapshot(now_ms, config)
    warnings.extend(rate_limit_warnings)
    return hub_model.HubSnapshot(..., usage=usage, rate_limit_resets=rate_limit_resets)
```

### `hub_settings.py` (I/O + 순수 판정)

```python
STATUSLINE_KEY = "statusLine"
STATUSLINE_MARKER = "# DZH_HUB_STATUSLINE"
STATUSLINE_COMMAND = (
    'python3 "$HOME/.claude/hub/bin/hub_statusline.py" 2>/dev/null || true   ' + STATUSLINE_MARKER
)
STATUSLINE_CONFLICT_REASON = "이미 다른 statusLine 이 설정돼 있습니다 — 손대지 않고 중단합니다"


class HubStatusLineConflictError(Exception):
    """settings.json 의 statusLine 이 우리 것이 아닐 때 발생한다(덮어쓰기 금지)."""


# ---- 순수 ----
def statusline_owner(settings: dict) -> str:
    """statusLine 의 소유자를 판정한다: 'none' | 'hub' | 'foreign'."""

def merge_hub_statusline(settings: dict) -> dict:
    """우리 statusLine 을 넣은 새 settings dict 를 돌려준다(입력 불변, 멱등).
    남의 statusLine 이 있으면 HubStatusLineConflictError."""

def strip_hub_statusline(settings: dict) -> dict:
    """우리 것일 때만 statusLine 키를 제거한 새 dict 를 돌려준다(입력 불변, 멱등)."""


# ---- I/O ----
def install_statusline() -> dict:
    """{'ok': True, 'installed': bool, 'already_installed': bool} 또는 {'ok': False, 'reason': ...}"""

def uninstall_statusline() -> dict:
    """{'ok': True, 'removed': bool} 또는 {'ok': False, 'reason': ...}"""

def statusline_install_status() -> bool:
    """우리 statusLine 이 설치돼 있는가. 파싱 실패면 False."""
```

`statusline_owner` 판정표 (이 함수가 결정 S4 의 전부다):

| `settings["statusLine"]` | 판정 | 이유 |
|---------------------------|------|------|
| 키 없음 / `None` | `none` | 설치 가능 |
| dict 이고 `command` 문자열에 마커 포함 | `hub` | 우리 것 — 멱등 설치·안전 제거 |
| 그 밖의 모든 값(마커 없는 dict, 문자열, 숫자…) | `foreign` | **남의 것 — 절대 건드리지 않는다** |

`install_statusline()` 의 추가 사전 조건: `~/.claude/hub/bin/hub_statusline.py` 가 **실재해야**
한다. 없으면 `{"ok": false, "reason": "...hub_statusline.py 가 없습니다 — hub/install.sh 를 먼저
실행하십시오"}`. 근거: statusLine 실패는 `2>/dev/null` 로 **설계상 무성음**이라, 설치 시점이
잘못을 잡을 수 있는 유일한 창구다.

### `hub_statusline.py` (신규 진입점 — `hub_hook.py` 와 같은 골격)

```python
def _run() -> None:
    """stdin JSON → (변화 시) 캡처 파일 → 상태줄 한 줄 출력."""

def main() -> int:
    """항상 0 을 반환한다 — 이 스크립트가 사용자 상태줄을 깨뜨리는 일은 원리적으로 없어야 한다."""
```

실행 순서(이 순서가 곧 성능 설계다):

1. `payload_text = sys.stdin.read()` — 실패해도 예외를 밖으로 내보내지 않는다.
2. `print(hub_usage.format_status_line_summary(payload_text))` — **먼저 출력한다.** 뒤의 파일
   작업이 어떻게 되든 사용자 상태줄은 이미 그려진다.
3. `resets = hub_usage.parse_status_line_rate_limits(payload_text, now_ms)`. `None` 이면
   **파일을 만지지 않고 종료**(rate_limits 없는 세션의 정상 경로 = 파일 I/O 0회).
4. `previous, _ = hub_collect.read_rate_limit_capture()`
5. `if not hub_usage.same_reset_times(previous, resets): hub_collect.write_rate_limit_capture(resets)`
6. 전체를 `try/except Exception: pass` 로 감싸고 `return 0`.

> **GOTCHA 1 — stdout 을 절대 리다이렉트하지 마라.** 훅 커맨드(`>/dev/null 2>&1 || true`)를
> 그대로 베끼면 상태줄이 통째로 사라진다. statusLine 에서 **stdout 은 출력 채널**이다.
> 커맨드 문자열은 `2>/dev/null || true` 만 쓴다. T25-38 이 이 회귀를 잡는다.

> **GOTCHA 2 — 예외를 밖으로 내지 마라.** 트레이스백은 `2>/dev/null` 로 가려지지만, 그 실행의
> stdout 이 비면 상태줄이 깜빡인다. `hub_hook.py` 와 같은 이유·같은 처리다.

### `hub.py` — 서브커맨드 2개 + 진단 필드 3개

```python
def cmd_install_statusline(args: argparse.Namespace) -> int:
    """`/hub statusline on` — settings.json 에 우리 statusLine 을 넣는다(멱등, 충돌 시 거부)."""

def cmd_uninstall_statusline(args: argparse.Namespace) -> int:
    """`/hub statusline off` — 우리 statusLine 만 제거한다."""
```

`build_parser()` 의 `subcommand_names` 에 `"install-statusline"`, `"uninstall-statusline"` 을,
`COMMAND_HANDLERS` 에 같은 키를 더한다(기존 `install-hooks` 패턴과 글자 그대로 같은 모양).

`cmd_status` 추가 필드 3개:

```python
        "statusline_installed": hub_settings.statusline_install_status(),
        "rate_limit_capture_age_ms": <int | None>,        # 캡처 부재·계약 불일치면 None
        "rate_limit_resets_remaining_ms": <dict | None>,  # {"session": int|None, "weekly": int|None}
```

세 필드가 각각 다른 질문에 답한다 — 리셋 줄이 안 보이는 이유는 ①statusLine 미설치
②세션 미실행(캡처 없음) ③리셋 시각이 이미 지남 ④`show_usage_panel:false` 넷인데, 화면에서는
전부 똑같이 "줄 없음"으로 보인다. 이 레포가 반복해 지켜 온 원칙(`last_collect_failure`·
`usage_sample_age_ms` — 전부 "조용한 실패를 관측 가능하게")과 같은 판단이다.

### `#dzh-data` JSON 계약 (템플릿이 읽는 형태)

```jsonc
{ "collected_at_ms": 1786433123899,
  "projects": [ /* 기존 그대로 */ ],
  "unresolved_dir_names": [],
  "warnings": [],
  "usage": { "sampled_at_ms": …, "session_percent": 43, "weekly_percent": 71 },
  "rate_limit_resets": { "captured_at_ms": …, "session_resets_at_ms": …, "weekly_resets_at_ms": … } }
```

---

## settings.json 충돌 정책 (결정 S4)

### 문제 — `hooks` 와 달리 `statusLine` 은 **단일 값**이다

`hooks` 는 이벤트마다 **배열**이라 우리 엔트리를 append 해 CAM·Litmus 와 공존할 수 있었다
(`merge_hub_hooks`). `statusLine` 은 `settings.json` 최상위의 **값 하나**다 — 우리가 쓰면
남의 것은 사라진다. **병합 패턴을 그대로 재사용할 수 없다.**

### 결정 — 감지하면 **거부**한다. 체이닝하지 않는다.

```
none    → 설치한다
hub     → 이미 설치됨(멱등, 파일을 쓰지 않는다)
foreign → {"ok": false, "reason": "...", "current_command": "<기존 값>"} 으로 중단
```

거부 메시지는 기존 값을 함께 보여 준다 — 사용자가 무엇을 지워야 하는지 알아야 조치할 수 있다.

**기존 statusLine 을 감싸는(chaining) 안을 기각한 이유**

1. **stdin 은 한 번만 읽힌다.** 원래 스크립트에 같은 JSON 을 다시 먹이려면 우리가 읽은 전문을
   자식 프로세스의 stdin 으로 파이프해야 하고, 그러려면 `subprocess` 기동이 매 0.3초마다 하나 더
   붙는다(측정된 19ms 바닥값이 2배가 된다).
2. **원래 명령을 우리 파일에 보관해야 한다** — 즉 사용자의 설정 일부를 우리가 소유하게 된다.
   제거 시 복원 실패·부분 복원 같은 새 실패 모드가 생긴다.
3. **이 레포의 소유권 원칙과 정면으로 어긋난다.** `hub_settings.py` 의 첫 문단은 "기존 훅은
   절대 읽지도 고치지도 않는다 — 마커로만 우리 엔트리를 찾는다"이다. 남의 명령을 읽어 우리
   설정에 복사하는 것은 그 원칙의 위반이다.
4. **거부는 되돌릴 수 있고 조용한 손상은 되돌릴 수 없다.** 거부당한 사용자는 1분이면
   대응하지만, 덮어쓴 statusLine 은 백업 파일을 뒤져야 한다.

> **GOTCHA 3 — 마커는 셸 주석이다.** `... || true   # DZH_HUB_STATUSLINE` 의 `#` 는 셸이
> 해석한다. statusLine 커맨드는 `$HOME` 확장을 위해 어차피 셸로 실행되며(공식 예시가 파이프·
> 명령 치환을 쓴다), 같은 파일의 훅 커맨드가 이미 같은 방식으로 운영 중이다. 그래도 설치 후
> **새 세션에서 상태줄이 실제로 그려지는지 눈으로 1회 확인**한다(수동 M1).

### 제거 순서 (결정 S8)

`hub/install.sh --uninstall` 은 지금 **서버 정지 → 훅 제거 → `bin/` 삭제** 순이다. 여기에
**statusLine 제거**를 훅 제거 옆에 끼운다. 넣지 않으면 `bin/` 이 사라진 뒤에도 모든 세션이
없는 스크립트를 최대 0.3초마다 실행하고, `2>/dev/null || true` 때문에 **아무 소리 없이 빈
상태줄**만 남는다 — 사용자가 원인을 찾기 가장 어려운 상태다.

```bash
    python3 "$hub_py" uninstall-hooks --json || true
    python3 "$hub_py" uninstall-statusline --json || true   # ★신규 — rm -rf 보다 반드시 앞
```

T25-39 가 이 순서를 고정한다.

---

## 화면 명세 — 초기화 예정 시각

### 펼침 상태 (변경 후)

```
┌──────────────────────────────────────┐
│ Claude 사용 한도                  ▾ │
│ 세션 (5시간)                   43%   │
│ ▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│              초기화 18:32 · 2시간 12분 뒤 │   ← ★신규
│ 주간 (7일)                     71%   │
│ ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░  │
│           초기화 8/15 09:14 · 2일 뒤 │   ← ★신규
│ 마지막 갱신 5분 전 · 약 15분 주기    │
└──────────────────────────────────────┘
```

접힘 상태의 요약(`세션 43% · 주간 71%`)은 **바꾸지 않는다** — 요구가 "펼쳤을 때"이고,
알약을 키우면 결정 L2("접으면 작게")를 스스로 어긴다(결정 R4).

### 표시 규칙

| 항목 | 규칙 |
|------|------|
| 위치 | 각 막대 **바로 아래** 한 줄(`.usage-reset`), 우측 정렬, 11px, `var(--muted)` |
| 절대 시각 | 같은 날이면 `18:32`, 다른 날이면 `8/15 09:14` (24시간·0 패딩, 로컬 시간) |
| 상대 시간 | ` · ` 뒤에 `곧`(<1분) / `N분 뒤` / `N시간 M분 뒤` / `N일 뒤` |
| 값이 없을 때 | **줄 자체를 그리지 않는다.** "정보 없음" 같은 자리표시를 만들지 않는다 |
| 지난 값 | 그리지 않는다(서버·클라이언트 이중 필터, 결정 R5) |
| 캡처 시각 | 줄의 `title` 속성에 `이 정보를 확인한 시각: 2026-08-12 09:14:03` (호버 툴팁) |
| 갱신 | 기존 30초 틱(`setInterval(render, TICK_MS)`)이 상대 시간을 다시 계산한다. **새 타이머 없음** |

### 결정 R2 — staleness 정책: **"지나면 사라진다"가 전부다**

퍼센트(U3)는 나이가 들면 **틀린 값**이 되지만, 리셋 시각은 **절대 시각**이라 그 시각이 지나기
전까지는 며칠 묵어도 여전히 참이다. 그래서 나이 임계값을 새로 만들지 않는다:

- 새 매직 넘버가 늘지 않는다(U3 의 5시간처럼 "데이터 자신의 창 길이"라는 근거를 댈 수 없는
  임의 숫자가 될 것이다).
- 아직 참인 정보를 나이를 이유로 숨기는 것은 사용자에게 손해다. 예: 3일 전 캡처의 주간 리셋이
  내일이라면 그 값은 지금도 맞다.
- **지난 값은 필터가 이미 지운다.** 낡음이 위험해지는 유일한 지점이 리셋 시각 통과인데, 그것이
  곧 만료 조건이다 → **데이터가 거짓이 되는 바로 그 순간 사라진다.**

낡음을 완전히 감추지는 않는다 — `title` 툴팁에 캡처 시각을, `/hub status` 에
`rate_limit_capture_age_ms` 를 노출한다. 화면 본문에는 두 번째 시각(캡처 시각)을 상시 표시하지
않는다: 이미 "마지막 갱신 N분 전"(퍼센트 출처)이 있어 **서로 다른 두 신선도 숫자가 나란히 뜨면
사용자가 어느 쪽이 무엇인지 알 수 없게 된다.**

### 결정 R3 — 패널 게이팅은 그대로다 (퍼센트가 없으면 패널 자체가 없다)

리셋 시각만 있고 퍼센트가 없는 상태(비-macOS·데스크톱 앱 미설치·샘플 만료)에서는 **패널이
뜨지 않는다.** 즉 리셋 시각은 **기존 패널의 장식**이지 패널을 띄우는 조건이 아니다.

- 요구는 "펼쳤을 때 리셋 시각도 보이게"이지 "패널의 표시 조건을 바꿔라"가 아니다.
- 게이팅을 "둘 중 하나라도 있으면"으로 바꾸면 막대 없는 패널·요약 문자열의 대체 표기 등
  **새로운 상태가 3개 이상** 늘어난다(`renderUsageBar` 이중 가드, `usageSummaryText` 폴백…).
- **수용하는 한계**: 터미널 전용(비-macOS) 사용자에게 이 기능은 여전히 존재하지 않는다.
  `hub/README.md` 에 한 줄로 명시한다. 훗날 statusLine 을 퍼센트의 출처로도 승격하면 이 한계가
  통째로 사라지지만, 그것은 별도 PRP 다(대안 4).

### 결정 R5 — 지난 값 필터를 서버와 브라우저 **양쪽**에 둔다

중복처럼 보이지만 아니다. 서버 필터는 수집 시점(5초 주기)에만 돈다 — **브라우저 탭은 몇 시간
열려 있을 수 있다.** 페이지가 열린 채 18:32 를 지나면 클라이언트 필터가 없는 한 "초기화 18:32 ·
0분 뒤"가 화면에 박힌다. 클라이언트 필터는 30초 틱마다 그 줄을 스스로 걷어낸다.

---

## 요구 2 — 펼침 시 즉시 갱신

### 현행 폴링 체인 (확인 완료)

`hub_template.html` 하단 IIFE: `setInterval(poll, POLL_INTERVAL_MS=5000)` + `visibilitychange`·
`focus` 에서도 `poll()` 을 직접 호출한다. `poll()` 은 `busy` 플래그로 중복 실행을 막고,
받은 HTML 이 이전과 같으면 `renderConnectionStatus()` 만, 다르면 `#dzh-data` 를 다시 파싱해
`render()` 를 부른다. → **"이벤트가 나면 poll() 을 한 번 더 부른다"는 이미 이 파일의 확립된
관용구다.** 새 개념을 도입할 필요가 없다.

### 변경 (토글 핸들러에 3줄)

```js
  usageToggleButton.addEventListener('click', function(){
    isUsageCollapsed = !isUsageCollapsed;
    persistUsageCollapsed(isUsageCollapsed);
    applyUsageCollapsedState();
    if(isUsageCollapsed) return;
    renderUsagePanel(snapshot.usage, snapshot.rate_limit_resets);  // ① 라벨을 지금 시각으로 다시 계산
    if(isServed) poll();                                           // ② 서버에 최신 스냅샷을 즉시 요청
  });
```

- **①은 오프라인에서도 동작한다.** 상대 시간("2시간 12분 뒤")은 최대 30초 낡아 있을 수 있는데,
  펼치는 순간 다시 계산하면 사용자가 보는 첫 숫자가 항상 정확하다. `file://` 모드에서 유일하게
  가능한 갱신이기도 하다.
- **②는 서버 모드에서만.** `poll()` 은 `location.pathname` 을 fetch 하므로 `file://` 에서
  부르면 무조건 실패해 `connectionLost` 를 켠다.

> **GOTCHA 4 — 핸들러 등록 위치를 옮기지 마라.** 토글 리스너는 `if(!isServed){ … return; }`
> **앞**에 등록돼 있어야 한다. 뒤로 옮기면 `file://` 모드에서 접기 기능 자체가 사라진다.
> 그 자리에서 `poll` 을 참조할 수 있는 것은 `function poll(){}` 이 **함수 선언(호이스팅)**
> 이기 때문이다 — 훗날 `var poll = function(){}` 로 바꾸면 클릭 시 TypeError 가 난다.

> **GOTCHA 5 — `busy` 는 그대로 둔다.** 폴링이 이미 진행 중이면 이번 클릭의 `poll()` 은 즉시
> 반환한다. 진행 중인 응답이 곧(수 ms) 도착하므로 재시도 큐를 만들 이유가 없다(YAGNI).

### 정직한 효과 범위 (결정 X3)

| 무엇이 빨라지나 | 무엇이 그대로인가 |
|-----------------|-------------------|
| 다음 폴링까지의 대기 **최대 5초**가 사라진다 | 서버 재수집 주기 5초(`server_collect_interval_seconds`) |
| 상대 시간 라벨이 즉시 정확해진다(최대 30초 이득) | 데스크톱 앱의 사용량 갱신 주기 **약 15분** — 우리가 제어하지 않는다 |

즉 이 변경은 **폴링 지연을 없애는 것**이지 데이터 원본을 더 자주 만드는 것이 아니다. 그래서
`USAGE_CYCLE_NOTE`("· 약 15분 주기")는 그대로 두며, 오히려 이 문구가 있어야 "펼쳤는데 숫자가
안 변했다"를 사용자가 오해하지 않는다. 서버에 "지금 다시 수집하라"를 시키는 안은 읽기 전용
화이트리스트 원칙을 깨야 해서 기각한다(대안 3).

---

## 변경 후 템플릿 (인터페이스)

### CSS — 규칙 1개 추가

```css
  .usage-reset{font-size:11px;color:var(--muted);margin-top:3px;text-align:right}
```

`body.has-usage .wrap{padding-bottom:var(--usage-clearance,184px)}` 의 **fallback 숫자와 주석**은
줄이 2개 늘어난 만큼 갱신한다(현재 주석: "펼침 실측 153 + 여유 32 ≈ 185"). 구현자가 실제
펼침 높이를 재서 `실측값 + 32` 로 적는다 — 이 값은 JS 가 못 도는 경우에만 쓰이지만, **내 변경이
낡게 만든 숫자이므로 내가 고친다.**

### JS — 순수 함수 2개 + 렌더 함수 1개

```js
var USAGE_RESET_LABEL = '초기화';
var MS_PER_HOUR = 3600000;
var MS_PER_DAY = 86400000;

function remainingLabel(untilMs, nowMs)
    /** 남은 시간을 사람이 읽는 문자열로. 이미 지났으면 null(호출자가 줄을 그리지 않는다). */
    // '곧' | 'N분 뒤' | 'N시간 M분 뒤' | 'N일 뒤'

function usageResetText(resetsAtMs, nowMs)
    /** '초기화 18:32 · 2시간 12분 뒤'. 값이 없거나 이미 지났으면 null. 순수 — DOM 에 닿지 않는다. */
    // 같은 날이면 HH:MM, 다른 날이면 M/D HH:MM (24시간·0 패딩)

function renderUsageResetRow(resetsAtMs)
    /** 초기화 예정 시각 한 줄의 HTML. 그릴 값이 없으면 빈 문자열. */
    // '<div class="usage-reset" title="…">초기화 18:32 · 2시간 12분 뒤</div>'
```

`renderUsagePanel(usage, resets)` 변경(불변식 H1′ 준수 — `#dzh-usage-body` 만 쓴다):

```js
  var sessionResetRow = renderUsageResetRow(resets && resets.session_resets_at_ms);
  var weeklyResetRow  = renderUsageResetRow(resets && resets.weekly_resets_at_ms);
  usageBodyEl.innerHTML = sessionBar + sessionResetRow + weeklyBar + weeklyResetRow + metaHtml;
```

호출부는 `render()` 안의 `renderUsagePanel(snapshot.usage, snapshot.rate_limit_resets)` 와
토글 핸들러 두 곳뿐이다.

**방어 규칙**(기존 `clampPercent` 의 관행 그대로): `Number()` 강제 변환 후 `isFinite` 가 아니면
줄을 그리지 않는다. `title` 값은 `escapeHtml()` 을 통과시킨다(T25-37 이 따옴표 이스케이프를
이미 보장한다).

**접근성**: 리셋 줄은 펼침 본문 안의 평문이라 막대(`role="progressbar"`) 뒤에 자연스럽게
낭독된다. 새 ARIA 속성을 만들지 않는다. 접힘 알약의 접근성 이름은 종전 그대로다.

**불변식 H1′ 는 개정되지 않는다** — 갱신 대상은 여전히 `#dzh-app`·`#dzh-collected-at`·
`#dzh-usage-body`·`#dzh-usage-summary` 네 개뿐이고, 새 요소는 전부 `#dzh-usage-body` **안**에
그려진다. 상단 주석 블록에는 데이터 계약 한 줄(`rate_limit_resets`)만 덧붙인다.

---

## 구 PRP 확장 표기 (구현 범위에 포함)

이전 세션의 U5 대체 선례를 그대로 따른다 — **원문을 지우지 않고 표기만 덧붙인다.**
`docs/prps/hub-theme-and-usage-panel.md` 3곳:

| 위치 | 추가할 문장 |
|------|-------------|
| 「확정된 전제」 3항(패널 내용은 막대 2개 + 마지막 갱신 시각까지) | `> **확장됨.** 이 범위는 [\`hub-usage-reset-time-and-refresh.md\`](./hub-usage-reset-time-and-refresh.md) 가 넓혔다 — 펼침 상태에 창별 **초기화 예정 시각** 한 줄이 추가된다. \`u.xu\`·스파크라인은 여전히 범위 밖이다.` |
| 「사용량 데이터 출처」의 "대안이 없음은 확인됐다" 문단 | `> **개정됨.** 이 조사는 \`plan-usage-history.json\` 을 **퍼센트의 출처**로 볼 때만 유효하다. **초기화 예정 시각**의 공식 출처는 Claude Code 의 statusLine 입력 JSON(\`rate_limits.*.resets_at\`)이며, [\`hub-usage-reset-time-and-refresh.md\`](./hub-usage-reset-time-and-refresh.md) 가 이를 쓴다.` |
| 「패널 명세」 표의 마지막 행 아래 | `| 초기화 예정 시각 | 창별로 한 줄(현행: hub-usage-reset-time-and-refresh.md 결정 R2·R4) |` |

`hub-usage-collapse-and-grid.md` 는 **수정하지 않는다** — H1′·C1~C6 이 전부 그대로 유효하다.

---

## 설계 결정 요약

| # | 결정 | 한 줄 근거 |
|---|------|-----------|
| S1 | 리셋 시각의 출처는 statusLine `rate_limits` 뿐 | 히스토리 역산은 추정이고, 이건 공식 값이다 |
| S2 | 파서는 `hub_usage.py` 확장, 신규 파일은 진입점 1개 | 같은 패널을 채우는 두 조각을 한 파일에. 175줄로 끝난다 |
| S3 | 리셋 값이 **바뀔 때만** 캡처 파일을 쓴다 | 결정 D3(content_key 폭주) + 0.3초 주기 원자적 쓰기 회피 |
| S4 | 남의 statusLine 이 있으면 **거부** | 단일 값 필드라 병합이 불가능. 소유권 원칙 |
| S5 | `hub_statusline.py` 는 `hub_collect` 를 임포트(+13ms 실측) | 경로·원자적 쓰기의 정본은 하나여야 한다(검수 m3 선례) |
| S6 | 상태줄 stdout = 퍼센트 한 줄(데이터 없으면 빈 줄) | 이미 손에 있는 값이고, 빈 상태줄은 사용자가 요구하지 않은 UI 후퇴다 · **승인 항목 2** |
| S7 | `used_percentage` 는 캡처하지 않는다 | 같은 숫자의 출처를 둘로 만들지 않는다. 타입 규칙(U2)도 다르다 · **개정됨.** `used_percentage` 를 **캡처한다**(내림 정수). 기각 근거였던 "타입 규칙 불일치"는 내림 정수로, "재작성 폭주"는 정량 평가로 해소됐다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) 결정 P2·P4·P8. |
| S8 | `--uninstall` 에 statusLine 제거를 편입 | 없는 스크립트를 0.3초마다 부르는 무성음 상태 방지 |
| R1 | 스냅샷 필드를 분리(`rate_limit_resets`) | 출처가 둘이면 데이터클래스도 둘 |
| R2 | staleness = "지나면 사라진다"가 전부 | 절대 시각은 지나기 전까지 참이다. 임의 임계값 금지 |
| R3 | 패널 게이팅 불변(퍼센트 없으면 패널 없음) | 요구는 장식 추가지 표시 조건 변경이 아니다 · **승인 항목 5** · **유지됨.** 퍼센트가 없으면 패널이 없다는 게이팅은 그대로다. 다만 그 퍼센트의 출처가 캡처로 바뀌었으므로, 이제 `/hub statusline on` 이 패널 표시의 사실상 전제다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md). |
| R4 | 리셋 줄은 펼침 본문에만 | 요구가 "펼쳤을 때". 접힘 알약을 키우면 결정 L2 위반 |
| R5 | 지난 값 필터를 서버·클라이언트 양쪽에 | 탭이 몇 시간 열려 있으면 서버 필터만으로는 못 막는다 |
| X1 | 펼칠 때만 `poll()` 1회 재사용 | `focus`·`visibilitychange` 와 같은 관용구. 새 개념 0 |
| X2 | `file://` 는 로컬 재렌더만 | fetch 가 원리적으로 실패한다. reload 는 과한 부작용 |
| X3 | 5초·15분 상수는 그대로 | 사용자 요구가 "주기는 유지". 원본이 더 자주 안 나온다 |
| — | 디자인 패턴 도입 없음 | dataclass 1개 + 순수 함수 6개 + JS 함수 3개. 추상화할 두 번째 사례가 없다 |

---

## 테스트 계획

검증 정본: `bash tests/run.sh`(전체) / `python3 -m unittest discover -s tests/hub -t .`(파이썬).
이 레포에는 별도 linter·type checker 설정이 없다. **JS 단위 테스트는 없다**(러너 도입은
"새 외부 의존성 금지"에 정면으로 걸린다) — 템플릿은 grep 회귀 + 수동 확인 두 축으로 검증한다.

### 신규/추가 — `tests/hub/test_hub_usage.py` (순수, 케이스 R1~R14)

`parse_status_line_rate_limits(text, captured_at_ms)`

| # | 입력 | 기대 |
|---|------|------|
| R1 | 두 창 모두 정상(`resets_at` 초) | 두 필드가 **×1000 된 ms** 로 매핑된다 |
| R2 | `five_hour` 만 존재 | `weekly_resets_at_ms is None`, 세션만 채워짐 |
| R3 | `seven_day` 만 존재 | 대칭 |
| R4 | `rate_limits` 키 자체가 없음(정상 페이로드) | `None` (예외 없음) |
| R5 | `rate_limits` 가 dict 가 아님 / 창이 dict 가 아님 | `None` |
| R6 | `resets_at` 이 문자열/실수/bool | 그 창은 버려짐. 둘 다면 `None` — **단위·타입 회귀의 핵심** |
| R7 | `resets_at` 이 이미 ms 로 들어옴(단위 오류 시뮬레이션) | `None` — 지평선 검사가 잡는다 |
| R8 | `resets_at` 이 캡처 시각보다 과거 | 그 창은 버려짐 |
| R9 | 깨진 JSON · 빈 문자열 | `None` (예외 없음) |

`drop_passed_resets(resets, now_ms)`

| # | 입력 | 기대 |
|---|------|------|
| R10 | 세션만 지남 | 주간만 남은 새 인스턴스(원본 불변) |
| R11 | 둘 다 지남 | `None` |
| R12 | `now_ms == session_resets_at_ms` (경계) | 지난 것으로 본다(버림) |

`same_reset_times` / `parse_rate_limit_capture` / `format_status_line_summary`

| # | 입력 | 기대 |
|---|------|------|
| R13 | `captured_at_ms` 만 다르고 리셋 시각 동일 | `same_reset_times` 가 `True`(= 다시 쓰지 않는다) |
| R14 | 왕복: `asdict` → JSON → `parse_rate_limit_capture` | 원본과 같은 인스턴스. 필드 누락·타입 오류면 `None` |
| R14b | `used_percentage: 23.5`·`41` 혼합 | `format_status_line_summary` 가 `세션 23% · 주간 41%`(내림). 값 없으면 `''` |

### 추가 — `tests/hub/test_hub_settings.py` (순수 + I/O, 케이스 R15~R18)

기존 `MergeHubHooksTest`/`StripHubHooksTest` 의 형식(입력 불변 검사 포함)을 그대로 따른다.

| # | 시나리오 | 기대 |
|---|---------|------|
| R15 | `statusline_owner`: 키 없음 / 우리 마커 / 남의 명령 / 문자열 값 | `none` / `hub` / `foreign` / `foreign` |
| R16 | `merge_hub_statusline` — 없음에서 설치, 2회 호출 | 멱등. 입력 dict 불변 |
| R17 | `merge_hub_statusline` — **남의 statusLine 존재** | `HubStatusLineConflictError`. **원본 값이 그대로 살아 있다** |
| R18 | `strip_hub_statusline` — 우리 것 / 남의 것 / 키 없음 | 제거 / **보존** / no-op. `hooks` 키는 어느 경우에도 손대지 않는다 |
| R18b | `install_statusline()` — `hub_statusline.py` 부재 | `{"ok": False, reason 에 파일명 포함}`, settings.json 미변경 |

### 추가 — `tests/hub/test_hub_collect.py` (케이스 R19~R23)

기존 `UsageForSnapshotTest` 의 monkeypatch 패턴(모듈 상수를 임시 경로로 바꾸고 `tearDown` 에서
복원)을 그대로 따른다.

| # | 시나리오 | 기대 |
|---|---------|------|
| R19 | 캡처 파일 없음 | `(None, ())` — **경고 0건** |
| R20 | 깨진 JSON / 권한 없음(`chmod 000`) | `(None, 경고 1건)`, 예외 없음 |
| R21 | `show_usage_panel: false` | `(None, ())` 이며 **파일을 읽지 않는다**(`mock.patch` 로 read 호출 0회) |
| R22 | 두 리셋 시각이 모두 과거 | `(None, ())` — 경고 없음 |
| R23 | 캡처가 깨진 상태에서 `collect_snapshot()` | `projects`·`usage` 정상, `rate_limit_resets` 만 `None` — **실패 격리 회귀 방지** |
| R23b | `write_rate_limit_capture` → `read_rate_limit_capture` 왕복 | 같은 값. 파일이 원자적으로 교체된다 |

### 추가 — `tests/hub/test_hub_model.py` (케이스 R24~R25)

| # | 시나리오 | 기대 |
|---|---------|------|
| R24 | `rate_limit_resets` 만 다른 두 스냅샷 | `snapshot_content_key` 가 **다르다** |
| R25 | `rate_limit_resets=None` 스냅샷 렌더 | `render_hub_html` 결과에 `"rate_limit_resets": null` 이 있고 JSON 이 파싱된다 |

### 신규 — `tests/hub/test_hub_statusline.py` (I/O 진입점, 케이스 R26~R29)

`sys.stdin` 을 `io.StringIO` 로 갈아 끼우고 `hub_collect.RATE_LIMITS_PATH`·`HUB_HOME` 을 임시
디렉토리로 바꾼다(`WriteHubHtmlAtomicityTest` 의 setUp/tearDown 패턴).

| # | 시나리오 | 기대 |
|---|---------|------|
| R26 | 정상 페이로드 | 캡처 파일 생성 + stdout 한 줄. `main()` 이 `0` |
| R27 | **같은** 페이로드로 재실행 | 파일 `st_mtime_ns` **불변**(다시 쓰지 않는다 — 결정 S3 회귀) |
| R28 | 리셋 시각이 달라진 페이로드 | 파일이 갱신된다 |
| R29 | 깨진 stdin / `rate_limits` 없음 / 쓰기 불가 디렉토리 | 예외 없이 `main()` 이 `0`. 기존 캡처 파일이 **훼손되지 않는다** |

### 추가 — `tests/run.sh` (T25-38 ~ T25-42)

`test_hub_docs_and_constants()` 안, 기존 T25-37 블록 **뒤**, `log_ok` **앞**에 넣는다.
**함수 상단의 `test_desc` 를 `"허브 문서·상수 정합성 (T25-1~T25-42)"` 으로 갱신할 것.**
`hub_settings_file`·`hub_template_file`·`hub_install_file`·`hub_command_file` 지역 변수는 이미 선언돼 있다.

| # | 검사 | 실패 시 무엇을 막는가 |
|---|------|----------------------|
| T25-38 | `hub_settings.py` 의 statusLine 커맨드 줄이 **stdout 을 리다이렉트하지 않는다**(검사식은 아래 GOTCHA 6 의 코드 블록이 정본). 같은 줄에 `2>/dev/null`·`|| true`·마커는 **존재해야** 한다 | GOTCHA 1 — stdout 을 막아 상태줄이 통째로 사라지는 회귀 |
| T25-39 | `hub/install.sh` 에서 `uninstall-statusline` 의 줄 번호 < `rm -rf "$TARGET_BIN_DIR"` 의 줄 번호 (T25-23 과 같은 방식) | 없는 스크립트를 부르는 무성음 상태 |
| T25-40 | 마커 `# DZH_HUB_STATUSLINE` 가 `hub_settings.py`·`commands/hub.md`·`hub/README.md` 세 곳에 존재(T25-3 선례) | 마커 문서화 유실 |
| T25-41 | `hub_template.html` 에 `usage-reset`·`rate_limit_resets`·`초기화 `·`renderUsageResetRow` 가 있고, **`POLL_INTERVAL_MS = 5000`** 과 `약 15분 주기` 가 그대로다 | 리셋 줄 유실 + **요구 "주기는 유지"의 회귀** |
| T25-42 | `hub/README.md` 에 `rate_limits.json`·`statusline` 이, `commands/hub.md` 에 `install-statusline`·`uninstall-statusline` 이 존재 | 문서-코드 불일치 |

`HUB_FILE_COUNT` 11 ↔ 실제 파일 수 11 은 **기존 T25-1 이 자동 대조**한다(상수만 고치면 통과).

> **GOTCHA 6 — `2>/dev/null` 은 `>/dev/null` 을 부분 문자열로 포함한다.** 단순
> `grep -F '>/dev/null'` 로는 "stdout 리다이렉트 금지"를 검사할 수 없다(정상 커맨드가 항상
> 걸린다). `>` 앞 문자가 숫자가 아닌 경우만 잡는 정규식(`(^|[^0-9])>/dev/null`)을 써야
> `2>/dev/null` 은 통과시키고 ` >/dev/null`·`&>/dev/null` 만 잡는다.

```bash
  # T25-38 검사식 (정본) — 이 grep 이 무언가를 찾으면 실패다
  if grep -F 'hub_statusline.py' "$hub_settings_file" | grep -qE '(^|[^0-9])>/dev/null'; then
    record_failure "$test_name" "T25-38: statusLine 커맨드가 stdout 을 리다이렉트함 — 상태줄이 사라진다"
    return 1
  fi
```

### 기존 테스트에 대한 영향 (확인 결과)

| 검사 | 판정 | 근거 |
|------|------|------|
| T25-1 | **상수 수정 필요** | `hub/install.sh` 의 `HUB_FILE_COUNT=10` → `11` |
| T25-2 | 무영향 | 같은 상수를 참조해 실제 설치 파일 수를 센다 |
| T25-4 | 무영향 | 훅 커맨드 문자열(`\|\| true` + `>/dev/null` 한 줄)이 그대로 남는다. **새 statusLine 커맨드는 다른 줄이다** |
| T25-10 | 무영향 | `hub_usage.py` 는 여전히 순수(새 함수도 `open(`·`Path(`·`os.` 를 쓰지 않는다). `hub_statusline.py` 는 순수 목록에 **넣지 않는다** |
| T25-14 | 주의 | 폐기 패턴 `pkill`·`/hub serve[^r]` 검사가 `hub/bin/*.py` **전체**에 걸린다 → 새 파일에 그 문자열을 넣지 않는다 |
| T25-33 | 무영향 | `usageEl.innerHTML` 을 부활시키지 않는다(`usageBodyEl.innerHTML` 만 쓴다) |
| T25-35·T25-37 | 무영향 | 패널 위치·escapeHtml 미변경 |
| `tests/hub/*.py` 기존 케이스 | 무영향 | 새 필드는 기본값 `None` 이라 키워드 인자 헬퍼가 그대로 통과 |

### 수동 확인 목록 (자동화 불가)

**A. 설치·충돌**
- [ ] M1 — `/hub statusline on` → 새 터미널 세션에서 상태줄에 `세션 N% · 주간 N%` 가 뜬다
      (마커 셸 주석이 실제로 무해함을 확인하는 지점, GOTCHA 3)
- [ ] M1b — `settings.json` 에 임의의 `statusLine` 을 손으로 넣고 `/hub statusline on` → **거부**되고
      그 값이 **그대로 남아 있다**
- [ ] M2 — 세션을 1회 진행한 뒤 `~/.claude/hub/rate_limits.json` 에 두 리셋 시각이 있다
- [ ] M3 — `/hub statusline off` → `settings.json` 에서 `statusLine` 키가 사라지고 다른 키는 그대로다
- [ ] M3b — `hub/install.sh --uninstall` → statusLine 이 제거된 뒤에 `bin/` 이 지워진다

**B. 화면**
- [ ] M4 — 패널을 펼치면 막대 2개 각각 아래에 초기화 줄이 보인다(라이트/다크 양쪽 대비 확인)
- [ ] M5 — 마지막 카드·푸터가 가려지지 않는다(줄 2개가 늘어난 만큼 하단 여백이 자동으로 커진다)
- [ ] M6 — 캡처 파일의 `session_resets_at_ms` 를 과거로 손수 바꾸면 세션 줄만 사라진다
- [ ] M6b — 캡처 파일을 지우면 패널이 **종전 모습 그대로**(퍼센트 막대만) 남는다
- [ ] M6c — 줄에 마우스를 올리면 캡처 시각 툴팁이 뜬다

**C. 즉시 갱신**
- [ ] M7 — 개발자 도구 네트워크 탭을 열고 접힘 → 펼침 클릭 시 **fetch 가 즉시 1회** 발생한다
- [ ] M8 — 펼침 → 접힘 클릭에서는 fetch 가 발생하지 **않는다**
- [ ] M9 — `file://` 로 열어 펼침 클릭 → 콘솔 에러 없이 라벨만 다시 계산된다
- [ ] M10 — 60초 이상 방치해도 접힘/펼침 상태와 초기화 줄이 유지된다(30초 틱 2회)

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 검증 |
|---|------|------|
| 1 | `hub_usage.py` 순수 함수 5개 + dataclass (**배선 전, 독립**) | `unittest discover` 케이스 R1~R14b |
| 2 | `hub_collect.py` 읽기/쓰기 + `hub_statusline.py` 진입점 | 케이스 R19~R23b, R26~R29. 손으로 `echo '{...}' \| python3 hub_statusline.py` |
| 3 | `hub_settings.py` statusLine 병합/제거 + `hub.py` 서브커맨드 2개 + `install.sh` 2곳 | 케이스 R15~R18b, 수동 M1~M3b |
| 4 | `hub_model.HubSnapshot` 필드 + `collect_snapshot` 배선 | 케이스 R24~R25 |
| 5 | 템플릿 — 초기화 줄(CSS 1 + JS 3함수) | 수동 M4~M6c |
| 6 | 템플릿 — 펼침 즉시 갱신(3줄) | 수동 M7~M10 |
| 7 | 문서(`hub/README.md`·`commands/hub.md`·구 PRP 확장 표기 3곳) + `HUB_FILE_COUNT` + T25-38~42 | `bash tests/run.sh` 전체 통과 |

1과 3은 서로 의존하지 않는다. 5는 4에, 6은 5에 의존한다. 각 마일스톤은 그 자체로 커밋 가능하다.

---

## 리스크와 완화책

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | **전역 `settings.json` 을 바꾼다 — 모든 프로젝트의 터미널에 영향** | 사용자가 원치 않는 상태줄이 생긴다 | 옵트인 서브커맨드(자동 설치 없음, 설계 결정 4의 원칙), 실행 전 고지 문구(`commands/hub.md`), `off` 로 완전 복구 |
| 2 | **statusLine 이 최대 0.3초마다 python3 를 띄운다** | 세션당 CPU 상승(실측 42ms/회) | 정상 상태에서 파일 쓰기 0회(결정 S3), 출력 먼저·I/O 나중, `rate_limits` 없으면 파일 접근 0회. 부담되면 `off` |
| 3 | **비공개가 아닌 공식 스키마지만 여전히 변할 수 있다** | 리셋 줄이 사라진다(최선) | 엄격 검증 + 지평선 검사 → 실패는 항상 "없는 값"이지 "틀린 값"이 아니다. `/hub status` 3필드로 원인 추적 |
| 4 | **캡처가 낡는다** — 세션을 며칠 안 돌리면 새 값이 없다 | 오래된 리셋 시각이 표시될 수 있다 | 지난 값은 자동 소멸(결정 R2). 아직 안 지난 값은 여전히 참이다. 툴팁에 캡처 시각 병기 |
| 5 | **두 출처의 불일치** — 퍼센트는 앱(≤15분 지연), 리셋 시각은 CLI | "43%인데 리셋이 1분 뒤"처럼 어긋나 보일 수 있다 | 각 값에 자기 신선도를 병기(메타 줄·툴팁). 창이 리셋되면 퍼센트도 곧 따라 내려간다 |
| 6 | **다중 세션·다중 조직** — 여러 세션이 같은 파일을 쓴다 | 마지막 쓴 세션의 값이 남는다 | 한도는 계정 단위라 값이 같다. 조직을 오가는 계정의 한계는 기존 org 고지와 같은 격으로 README 에 1행 |
| 7 | **셸 주석 마커가 동작하지 않는 환경** | 상태줄이 아예 안 뜬다 | 수동 M1 이 최초 1회 확인. 실패하면 마커를 스크립트 경로 문자열(`hub_statusline.py`)로 바꾸는 국소 수정으로 대체 가능 |
| 8 | **`bin/` 삭제 후 statusLine 잔존** | 무성음으로 빈 상태줄 | 결정 S8 + T25-39 |
| 9 | **`rate_limits` 는 Pro/Max 구독 세션에서만 온다** | API 키 사용자에게는 기능이 없다 | README 에 명시. 파일 부재는 경고 없는 정상 경로 |
| 10 | **펼침 즉시 갱신이 기대만큼 "새롭지" 않다** | "눌러도 숫자가 그대로"라는 인상 | 결정 X3 의 정직한 효과 범위를 README·패널 문구("약 15분 주기")로 유지 |

---

## 검토했으나 채택하지 않은 대안

1. **히스토리(`plan-usage-history.json`)의 사용률 급락 지점으로 리셋 시각을 역산한다.**
   새 설치 절차가 전혀 필요 없고 macOS 사용자에게 즉시 동작한다. 그러나 앱이 꺼져 있던 구간
   (실측 최대 2.4일)만큼 오차가 나고, 그 오차를 사용자에게 표시할 방법이 없다 →
   **"틀린 시각"은 "없는 시각"보다 나쁘다**(결정 U1 과 같은 정신)로 기각.
2. **기존 statusLine 을 감싸(chaining) 공존한다.** 사용자를 거부하지 않아도 된다. 그러나 stdin
   재공급을 위한 자식 프로세스가 0.3초마다 하나 더 붙고, 남의 명령 문자열을 우리 설정에
   복사·복원해야 하며(소유권 원칙 위반), 부분 복원이라는 새 실패 모드가 생긴다 → 기각(결정 S4).
3. **브라우저가 서버에 "지금 다시 수집"을 요청하는 엔드포인트를 만든다(요구 2).**
   펼침 즉시 진짜 최신 수집을 얻는다. 그러나 읽기 전용 2경로 화이트리스트라는 서버 설계 정본을
   깨야 하고, 얻는 것은 최대 5초의 신선도뿐이다(원본은 15분마다 바뀐다) → 기각.
4. **퍼센트도 statusLine 에서 가져와 데스크톱 앱 의존을 없앤다.** 터미널 전용 환경에서도 패널이
   뜨고 출처가 하나로 준다. 그러나 (a) `used_percentage` 는 실수라 U2 검증 규칙을 다시 설계해야
   하고, (b) 세션이 안 돌면 퍼센트가 통째로 낡아 U3(5시간 만료)의 근거가 흔들리며, (c) 이번
   요구("리셋 시각을 보고 싶다")의 범위를 크게 넘는다 → 기각(별도 PRP 감).

   > **채택됨(재검토).** 데스크톱 파일이 실제로 사라져 전제가 바뀌었다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) 결정 P1.
5. **`hub_statusline.py` 가 `hub_collect` 를 임포트하지 않고 경로·원자적 쓰기를 자체 구현한다.**
   호출당 13ms(31%)를 아낀다. 그러나 `RATE_LIMITS_PATH` 의 정본이 둘이 되어, 한쪽만 바뀌면
   "캡처는 되는데 아무도 읽지 않는" 무성음 실패가 된다(검수 m3 의 재발) → 기각(결정 S5).
6. **캡처 파일에 `used_percentage` 도 함께 저장해 둔다(장래 대비).** 나중에 대안 4로 갈 때
   편하다. 그러나 퍼센트는 자주 변해 `snapshot_content_key` 를 매 사이클 흔들고(D3 위반),
   지금 아무도 읽지 않는 필드다 → 기각(YAGNI).

   > **채택됨(재검토).** 데스크톱 파일이 실제로 사라져 전제가 바뀌었다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) 결정 P1.
7. **접힘 알약에도 리셋 시각을 넣는다.** 펼치지 않고 확인할 수 있다. 그러나 알약이 약 100px
   길어져 결정 L2("접으면 작게")를 정면으로 어기고, 요구는 "펼쳤을 때"다 → 기각.
8. **리셋 임박(예: 10분 이내)에 색을 바꾼다.** 새 매직 임계값 + 새 색 상태. 요구는 "시각을
   보여 달라"까지다 → 기각(하위 PRP 의 임계값 색 기각과 같은 판단).
9. **`config.json` 에 `capture_rate_limits` 스위치를 새로 만든다.** 표시 스위치
   (`show_usage_panel`)와 캡처 스위치를 분리한다. 그러나 캡처를 끄는 수단은 이미
   `/hub statusline off` 라는 더 정확한 형태로 존재한다 → 기각(YAGNI).

---

## 사용자 승인이 필요한 핵심 결정

### 1. 전역 `settings.json` 의 `statusLine` 을 우리가 차지한다 (결정 S4·S8)

`/hub statusline on` 은 **모든 프로젝트의 터미널 상태줄**에 영향을 준다(현재 이 사용자는
statusLine 을 쓰지 않으므로 충돌은 없다). 실행 전 고지 → 사용자 확인 절차를 `/hub install`
(훅)과 같은 격으로 둔다. **남의 statusLine 이 있으면 설치를 거부**하고 절대 덮어쓰지 않는다.

### 2. 상태줄에 무엇을 출력할 것인가 (결정 S6)

| 안 | 출력 | 장단 |
|----|------|------|
| **A. 퍼센트 한 줄** (권고) | `세션 23% · 주간 41%` | 이미 stdin 에 있는 값이라 비용 0. 상태줄이 비지 않는다 |
| B. 아무것도 출력하지 않음 | (빈 줄) | "우리는 화면을 차지하지 않는다"가 명확. 빈 행이 남을 수 있다 |
| C. 퍼센트 + 리셋 시각 | `세션 23% (18:32) · 주간 41%` | 정보가 가장 많지만 상태줄이 길어지고 범위를 넘는다 |

### 3. 배포 파일 10개 → **11개** (결정 S2)

신규는 진입점 `hub/bin/hub_statusline.py` **하나뿐**이고, 파서는 `hub_usage.py` 를 확장한다
(별도 순수 모듈을 만들면 12개가 된다). `HUB_FILE_COUNT`·`hub/README.md` 문구 2곳을 함께 고친다.

### 4. staleness 정책 = "지나면 사라진다"가 전부 (결정 R2)

캡처 나이에 대한 임계값을 **두지 않는다.** 리셋 시각은 지나기 전까지 참이므로, 낡은 캡처의
아직 안 지난 값은 그대로 보여 준다(캡처 시각은 툴팁 + `/hub status` 로 확인). 대안은 "N시간
넘은 캡처는 숨긴다"인데, 근거 없는 임계값이 하나 늘고 아직 참인 정보를 숨기게 된다.

### 5. 리셋 시각은 **기존 패널의 장식**이다 (결정 R3)

퍼센트(데스크톱 앱)가 없으면 패널 자체가 안 뜨므로, **비-macOS·터미널 전용 환경에서는 리셋
시각만으로 패널이 뜨지 않는다.** 이 한계를 수용할지, 아니면 게이팅을 "둘 중 하나라도 있으면"
으로 넓힐지(상태 3개 증가) 확인이 필요하다.
