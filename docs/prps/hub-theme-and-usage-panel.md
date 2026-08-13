# 허브 다크 테마 + 토큰 사용량 플로팅 패널 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/` (통합 허브 대시보드) |
| 브랜치 | `feature/hub-dashboard` |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) — 이 문서는 그 위에 얹는 증분이다 |
| 워크플로우 경로 | **전체 경로** (새 모듈 추가 · 데이터 모델 변경 · 3개 이상 파일) |
| 규모 | Medium — 신규 2개 / 수정 10개 파일, 실행 코드 증분 약 200줄 + 템플릿 약 120줄 |
| 새 외부 의존성 | **없음** (python3 stdlib · 바닐라 JS/CSS 유지) |

---

## 요구사항 요약

허브 대시보드(`~/.claude/hub/hub.html`)는 지금 라이트 테마 하나뿐이고, "지금 내가 한도를
얼마나 썼는지"는 어디에서도 보이지 않는다. 이 PRP 는 두 가지를 더한다. **(1)** 색각 안전한
파랑–주황 축으로 팔레트를 재설계하고 다크 테마를 추가해 시스템 설정(`prefers-color-scheme`)을
따르되 사용자가 수동으로 덮어쓸 수 있게 한다. **(2)** 페이지 하단에 플로팅 패널을 띄워
5시간 세션 한도와 7일 주간 한도의 사용률을 막대 2개 + 마지막 갱신 시각으로 보여준다.
사용량 데이터의 출처는 Claude 데스크톱 앱이 남기는 비공개 파일 하나뿐이므로, 이 PRP 의
설계 부담 대부분은 "**없거나, 오래됐거나, 스키마가 바뀐 데이터를 어떻게 조용히 접을 것인가**"에
쏠려 있다.

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 허브를 하루 종일 열어 두고도 눈이 편하고,
> 한도에 부딪히기 전에 남은 여유를 곁눈으로 확인하고 싶다.

---

## 확정된 전제 (이 PRP 에서 재론하지 않는다)

1. **색각 안전 팔레트를 쓴다.** 사용자의 `~/.claude/settings.json` 테마가 `dark-daltonized` 다.
   현행 상태 배지의 초록(`#1F8A70`)/주황(`#F59E0B`)/빨강(`#C2410C`)은 적록색약에서 구별이
   어렵다 → **파랑–주황 축**으로 재설계하고 **색 이외의 채널(형태·텍스트)을 병행**한다.
   라이트·다크 양쪽 모두 적용한다.
2. **데이터가 없으면 사용량 패널 자체를 렌더링하지 않는다.** 빈 껍데기도, "0%" 오해도 만들지 않는다.
3. **패널 내용은 세션·주간 막대 2개 + 마지막 갱신 시각까지다.** `u.xu` 필드와 추이
   스파크라인은 범위 밖이다.

> **확장됨.** 이 범위는 [`hub-usage-reset-time-and-refresh.md`](./hub-usage-reset-time-and-refresh.md) 가 넓혔다 — 펼침 상태에 창별 **초기화 예정 시각** 한 줄이 추가된다. `u.xu`·스파크라인은 여전히 범위 밖이다.

### 사용량 데이터 출처 (실측 완료 — 재조사 대상 아님)

`~/Library/Application Support/Claude/plan-usage-history.json` (`-rw-------`, 116KB)

```json
{"version": 2,
 "samples": [{"t": 1786433123899, "org": "c2af3bdd-…", "u": {"fh": 10, "sd": 19}}]}
```

| 필드 | 뜻 | 실측 |
|------|-----|------|
| `t` | epoch ms | 1359개, 오름차순 단조 증가 확인. **마지막 원소가 최신** |
| `u.fh` | **5시간 세션 한도 사용률(0~100 정수)** | 항상 존재 |
| `u.sd` | **7일 주간 한도 사용률(0~100 정수)** | 항상 존재 |
| `u.xu` | 의미 불확실(1359개 중 32개에만 존재) | **쓰지 않는다** |
| `org` | 조직 UUID | 실측 환경엔 1종뿐 |

갱신 간격 중앙값 **15.2분**, 최대 간격 **약 2.4일**(앱을 켜지 않은 구간). 이 "최대 간격"이
아래 만료 규칙의 근거다 — 파일은 존재하지만 내용이 며칠 묵어 있는 상태가 **정상적으로**
발생한다.

**대안이 없음은 확인됐다**: `~/.claude/projects/*/*.jsonl` 의 `message.usage` 에는 분모(한도)가
없고, `policy-limits.json` 은 정책 제약이며, 트랜스크립트의 `error.rateLimits` 는 전부 `null`,
`metrics/costs.jsonl` 은 0만 든 유물이다.

> **개정됨.** 이 조사는 `plan-usage-history.json` 을 **퍼센트의 출처**로 볼 때만 유효하다. **초기화 예정 시각**의 공식 출처는 Claude Code 의 statusLine 입력 JSON(`rate_limits.*.resets_at`)이며, [`hub-usage-reset-time-and-refresh.md`](./hub-usage-reset-time-and-refresh.md) 가 이를 쓴다.

> **개정됨(2회차).** `plan-usage-history.json` 은 2026-08 실측으로 사라졌다. 퍼센트의 출처는 statusLine 입력의 `rate_limits.*.used_percentage` 로 교체됐다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) 결정 P1.

---

## 영향 범위

### 신규 파일 (2개)

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_usage.py` | 외부 비공개 포맷을 읽는 **순수 파서**. 아래 「모듈 경계」에 근거 |
| `tests/hub/test_hub_usage.py` | 위 모듈의 단위 테스트(`unittest discover` 가 자동 수집) |

### 수정 파일 (10개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_model.py` | `HubSnapshot` 에 `usage` 필드 1개 추가, `from hub_usage import UsageSample` | 페이지에 인라인되는 전체 데이터의 정의가 여기다 |
| `hub/bin/hub_collect.py` | 경로 상수 1개, 공개 함수 1개, 사설 함수 1개, `collect_snapshot` 배선 3줄, `_CONFIG_FIELD_TYPES` 1행 | 파일시스템에 닿는 유일한 모듈 |
| `hub/bin/hub_template.html` | 팔레트 토큰화 + 다크 블록 + 테마 토글 + 사용량 패널 | 화면 전체 |
| `hub/bin/hub.py` | `cmd_status` 에 진단 필드 2개 | 패널이 안 보이는 이유를 관측 가능하게 |
| `hub/install.sh` | `HUB_FILE_COUNT=9` → `10` | 배포 파일이 1개 늘었다 |
| `hub/README.md` | 설치 문구 2곳(9개→10개), config 표 1행, 「사용량 패널」 절 신설, 프라이버시 고지 1항 추가 | T25-1/T25-3 및 문서 정합 |
| `commands/hub.md` | `/hub status` 절에 새 필드 2개 설명 | 상태 보고 필드가 문서와 어긋나지 않게 |
| `tests/hub/test_hub_collect.py` | 사용량 읽기 실패 격리 테스트 4건, config 검증 1건 | 기존 `ReadRecentEventsFailureIsolationTest` 패턴을 그대로 답습 |
| `tests/hub/test_hub_model.py` | `snapshot_content_key` × `usage` 테스트 2건 | 캐시 키 회귀 방지 |
| `tests/run.sh` | T25 하위 검증 5건 추가(T25-27~31) | 팔레트·테마·순수 경계·문서 정합의 grep 회귀 방지 |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_parse.py` | 티어 1(`/dashboard` DOM) 파서. 사용량과 무관 |
| `hub/bin/hub_server.py` | 수집 루프는 `collect_snapshot()` 만 부른다 — 사용량 배선은 그 안에서 끝난다 |
| `hub/bin/hub_daemon.py`·`hub_hook.py`·`hub_settings.py` | 프로세스·훅·settings 관리. 접점 없음 |
| `tests/hub/fixtures/*.html` | **`/dashboard` 생성물**(티어 1 파서 입력)이지 `hub_template.html` 의 산출물이 아니다. `test_hub_parse.py` 만 이 픽스처를 읽는다 → **템플릿을 바꿔도 깨지지 않는다** (아래 「테스트 계획 · 기존 테스트 영향」에서 재확인) |
| `commands/dashboard.md` | `/dashboard` 는 별도 자산. 이 PRP 는 허브 템플릿만 건드린다 |
| 루트 `install.sh`·`README.md` | 허브 설치는 분리돼 있다(T25-21·T25-22 가 이 분리를 강제한다) |

---

## 파일 구조와 모듈 경계

### 레이어 배치

```
hub/bin/
├── hub_usage.py     ★순수 (신규)  외부 비공개 JSON → UsageSample | None
├── hub_parse.py     ★순수         /dashboard DOM → Tier1Snapshot | None
├── hub_model.py     ★순수         이벤트 → 사실 → 표시 상태, HubSnapshot 정의, 렌더
├── hub_collect.py    I/O          파일 읽기 · 스냅샷 조립 · hub.html 원자적 쓰기
├── hub_template.html 정적 템플릿   #dzh-data 블록 하나만 치환된다
└── hub.py / hub_server.py / hub_daemon.py / hub_hook.py / hub_settings.py  (무변경)
```

**의존 방향**: `hub_collect → {hub_model, hub_parse, hub_usage}`, `hub_model → hub_usage`
(`HubSnapshot.usage` 의 타입 때문). `hub_usage` 는 아무것도 임포트하지 않는다 → **순환 없음**.
이는 `hub_model → hub_parse`(`ProjectView.tier1`) 와 완전히 같은 모양이다.

### 결정 M1 — 파싱 로직을 `hub_model.py` 에 넣지 않고 새 모듈 `hub_usage.py` 를 만든다

**근거**

1. **선례가 명확하다.** `hub_parse.py` 는 "외부 생성물의 계약을 읽는 순수 파서, 실패는 예외가
   아니라 `None`" 이라는 정확히 같은 역할로 이미 독립 모듈이다. 사용량 파일은 그보다 더
   외부(우리가 만들지도 않는 데스크톱 앱의 비문서 포맷)다.
2. **`hub_model.py` 의 선언된 책임과 다르다.** 그 모듈의 docstring 은 "이벤트 → 세션 사실 →
   표시 상태로 접는 순수 로직" 이다. 사용량은 이벤트도 세션도 아니다. 여기 끼워 넣으면
   모듈 설명이 곧 거짓이 된다.
3. **크기.** `hub_model.py` 는 이미 565줄이다(전역 지침 권장 200~400, 상한 800). 60줄을 더
   보태 625줄로 만드는 것보다 60줄짜리 응집도 높은 파일 하나가 낫다.

**비용(정직하게)**: 배포 파일이 9개 → 10개가 되어 `hub/install.sh` 의 `HUB_FILE_COUNT`,
`hub/README.md` 의 "9개 파일" 문구 2곳, 그리고 `tests/run.sh` T25-10 의 순수 파일 목록을 함께
고쳐야 한다. T25-1 은 선언값과 실제 파일 수를 자동 대조하므로, 상수만 고치면 통과한다.
이 비용은 1회성이고 기계적이다. → **사용자 승인 항목 1** 로 올린다.

### 결정 M2 — 폴링 동기화 영역을 명문화한다 (템플릿 불변식)

`hub.html` 은 서버가 5초마다 다시 쓰고, 브라우저는 자기 URL 을 다시 받아 **문자열 전체를
비교**한 뒤 달라졌으면 `#dzh-data` 만 새로 파싱해 `render()` 를 부른다
(`hub_template.html:214-236`). 그런데 `render()` 는 **DOM 을 통째로 갈아 끼우지 않는다** —
`app.innerHTML` 과 `collectedAtLabel.textContent` 두 곳만 쓴다. 즉 `#dzh-app` **바깥의 DOM 은
폴링이 건드리지 않는다.** (`/dashboard` 가 `outerHTML` 대입을 여러 요소에 하기 때문에
"라디오는 치환하지 않는다"를 못 박아야 했던 것과 대비된다 — 허브는 구조적으로 더 안전하다.)

이 성질에 기대되, 명시적 불변식으로 고정한다:

> **불변식 H1.** 허브 폴링이 내용을 갱신하는 요소는 `#dzh-app`, `#dzh-collected-at`,
> `#dzh-usage` **세 개뿐이다.** 그 밖의 요소(테마 토글 버튼 포함)는 어떤 경로로도 치환하지
> 않는다. 새 UI 를 더할 때 사용자 상태를 가진 요소는 반드시 이 셋 바깥에 둔다.

> **개정됨.** H1 은 [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md) 의
> **H1′** 로 대체됐다 — 갱신 대상이 `#dzh-usage` 에서 `#dzh-usage-body`·`#dzh-usage-summary`
> 로 한 겹 안으로 이동했다.

- **테마 토글 버튼**: `#dzh-app` 바깥의 정적 마크업 → 5초 폴링에도 DOM 노드가 그대로 살아
  있고, 테마 상태는 `<html data-theme>` 속성 + `localStorage` 에 있어 폴링과 무관하다.
- **사용량 패널**: 내용은 스냅샷 파생이므로 매 `render()` 마다 다시 그려야 한다. 그래서
  **컨테이너(`#dzh-usage`)는 정적, 내용은 파생**으로 나눈다. 패널 안에는 접기/닫기 같은
  **사용자 상태를 두지 않는다**(아래 결정 U5) — 그러면 재렌더가 무해해진다.

---

## 데이터 모델

### 신규 — `hub_usage.py`

```python
USAGE_SESSION_WINDOW_HOURS = 5          # u.fh 가 재는 창의 길이. 만료 기준의 근거
MILLISECONDS_PER_HOUR = 60 * 60 * 1000
USAGE_MAX_SAMPLE_AGE_MS = USAGE_SESSION_WINDOW_HOURS * MILLISECONDS_PER_HOUR
USAGE_PERCENT_MIN = 0
USAGE_PERCENT_MAX = 100


@dataclass(frozen=True)
class UsageSample:
    """plan-usage-history.json 의 마지막 샘플 — 세션(5시간)·주간(7일) 한도 사용률."""

    sampled_at_ms: int      # 원본 t. 파생값(나이)은 담지 않는다 — 결정 D3 참조
    session_percent: int    # 원본 u.fh (0~100)
    weekly_percent: int     # 원본 u.sd (0~100)
```

### 변경 — `hub_model.HubSnapshot`

```python
@dataclass(frozen=True)
class HubSnapshot:
    """허브 페이지 하나에 인라인되는 전체 데이터."""

    collected_at_ms: int
    projects: tuple[ProjectView, ...]
    unresolved_dir_names: tuple[str, ...]
    warnings: tuple[str, ...]
    usage: UsageSample | None = None    # 없으면 패널을 그리지 않는다(요구 2)
```

기본값 `None` 을 **마지막 필드**로 둔다 — 기존 필드는 전부 기본값이 없으므로 순서 제약을
만족하고, `_minimal_snapshot()` 같은 기존 테스트 헬퍼(키워드 인자 사용)가 그대로 통과한다.
`asdict()` 가 중첩 dataclass 를 dict 로 펴므로 JSON 계약은 `"usage": {...} | null` 이 된다.

### 변경 — `hub_model.HubConfig`

```python
    show_usage_panel: bool = True    # false 면 사용량 파일을 아예 읽지 않는다
```

`hub_collect._CONFIG_FIELD_TYPES` 에 `"show_usage_panel": bool` 한 행을 더한다(타입 검증 대상).

### 결정 D3 — **now 파생값을 스냅샷에 담지 않는다** (성능상 필수)

상주 서버는 `snapshot_content_key()`(= `collected_at_ms` 를 뺀 내용 해시)가 **바뀌었을 때만**
`hub.html` 을 다시 쓴다(`hub_server.py:83`). 만약 `UsageSample` 에 `age_ms` 나 `elapsed_label`
같은 "지금 기준" 파생값을 넣으면 **매 5초 사이클마다 키가 달라져** hub.html 이 무조건 재작성되고,
그러면 브라우저의 문자열 비교도 매번 불일치 → 전체 재파싱·재렌더가 5초마다 일어난다. 지금의
"변화 없으면 아무 일도 없다" 최적화가 통째로 무력화된다.

→ **스냅샷에는 절대시각(`sampled_at_ms`)만 담고, 경과 시간은 브라우저가 `Date.now()` 로
계산한다.** 템플릿에는 이미 같은 일을 하는 `elapsedLabel(fromMs)` 와 30초 틱
(`setInterval(render, TICK_MS)`)이 있으므로 새 코드가 필요 없다.

만료 판정(아래 U3)은 이 규칙의 **예외가 아니다** — 만료 여부는 5시간에 한 번 값이 뒤집히는
불린이라, 키가 바뀌는 것도 그 순간 한 번뿐이다(그리고 그때는 실제로 화면이 바뀌어야 한다).

---

## 인터페이스

### `hub_usage.py` (순수 — 파일시스템·시각·환경에 닿지 않는다)

```python
def parse_usage_history(text: str) -> UsageSample | None:
    """사용량 히스토리 JSON 텍스트에서 마지막 샘플을 읽는다. 계약이 안 맞으면 None."""

def is_usage_sample_expired(sample: UsageSample, now_ms: int) -> bool:
    """샘플이 세션 창(5시간)보다 오래됐는가 — 그러면 세션 사용률의 근거가 사라진다."""
```

### `hub_collect.py` (I/O)

```python
PLAN_USAGE_HISTORY_PATH = (
    Path.home() / "Library" / "Application Support" / "Claude" / "plan-usage-history.json"
)

def read_latest_usage_sample() -> tuple[hub_usage.UsageSample | None, tuple[str, ...]]:
    """사용량 히스토리 파일을 읽어 마지막 샘플을 돌려준다. 이 함수는 절대 예외를 던지지 않는다."""

def _usage_for_snapshot(
    now_ms: int, config: hub_model.HubConfig
) -> tuple[hub_usage.UsageSample | None, tuple[str, ...]]:
    """스위치 · 만료까지 적용해 화면에 실을 샘플을 고른다(사설)."""
```

`collect_snapshot()` 배선 (3줄 + 인자 1개):

```python
    usage, usage_warnings = _usage_for_snapshot(now_ms, config)
    warnings.extend(usage_warnings)
    return hub_model.HubSnapshot(..., usage=usage)
```

**반환 계약** (이 표가 이 기능의 핵심 명세다):

| 상황 | 샘플 | 경고 | 근거 |
|------|------|------|------|
| `show_usage_panel: false` | `None` | 없음 | 파일을 **열지도 않는다**. 사용자가 명시적으로 껐다 |
| 파일 없음 | `None` | **없음** | macOS 데스크톱 앱이 없는 환경(리눅스·터미널 전용)에선 이게 **정상**이다. 경고를 내면 그 사용자들에게 영구 경고가 박힌다 |
| 읽기 실패(권한 등) | `None` | 1건 | 파일은 있는데 못 읽는 건 비정상이다 |
| 계약 불일치(스키마 변경·손상) | `None` | 1건 | 앱 업데이트로 포맷이 바뀐 신호 — 사용자가 알아야 한다. `dashboard.html DOM 계약 불일치 → 티어 2 강등` 경고와 같은 성격 |
| 만료(5시간 초과) | `None` | **없음** | 앱을 안 켰을 뿐이다. 실측 최대 간격이 2.4일인 정상 시나리오 |
| 정상 | `UsageSample` | 없음 | |

### `hub.py` — `cmd_status` 진단 필드 2개

```python
        "usage_panel_enabled": config.show_usage_panel,
        "usage_sample_age_ms": <int | None>,     # 스위치 off·파일 없음·계약 불일치면 None
```

패널이 안 보이는 네 가지 이유(스위치 off / 파일 없음 / 계약 불일치 / 만료)는 화면상 전부
"패널 없음"으로 똑같이 보인다. 계약 불일치만 warnings 로 드러나므로, 나머지 셋을 구분할
창구가 `/hub status` 밖에 없다. 이 레포가 반복해 지켜 온 원칙(`last_collect_failure`,
`crashed_evidence`, `collect_stalled` — 전부 "조용한 실패를 관측 가능하게")과 같은 판단이다.
필드 2개, 코드 4줄.

### `#dzh-data` JSON 계약 (템플릿이 읽는 형태)

```jsonc
{ "collected_at_ms": 1786433123899,
  "projects": [ /* 기존 그대로 */ ],
  "unresolved_dir_names": [],
  "warnings": [],
  "usage": { "sampled_at_ms": 1786433123899, "session_percent": 10, "weekly_percent": 19 } }
```

---

## 기능 1 — 다크 테마와 색각 안전 팔레트

### 결정 T1 — CSS 는 `prefers-color-scheme` 로 기본을 잡고, `[data-theme]` 속성이 덮어쓴다

```css
:root{ color-scheme:light; --bg:#EEF3F8; … }              /* 라이트 기본값 */
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){ color-scheme:dark; --bg:#0E1621; … }
}
:root[data-theme="dark"]{ color-scheme:dark; --bg:#0E1621; … }   /* 수동 오버라이드 */
```

- **JS 없이도 시스템 설정을 따른다.** 허브 페이지는 본문 전체가 JS 렌더이지만, **배경색만은
  JS 이전에 확정**되어야 FOUC 가 없다. 인라인 스크립트가 어떤 이유로든 실패해도(아래 T3 의
  `localStorage` 예외 등) 다크 사용자에게 흰 화면이 남지 않는다.
- **다크 토큰 블록이 두 번 나온다**(미디어 쿼리 + 속성 셀렉터). CSS 는 미디어 경계를 넘어
  셀렉터를 묶을 수 없어 불가피하다. JS 로 항상 `data-theme` 를 확정 기입하면 중복은 사라지지만
  "스크립트 실패 = 테마 실패" 를 만든다 → 12줄 중복을 택한다.
- `color-scheme` 을 함께 선언한다 — 스크롤바·기본 캔버스·폼 컨트롤이 테마를 따라간다.
  `<head>` 에 `<meta name="color-scheme" content="light dark">` 도 넣는다.

### 결정 T2 — 토글은 **3상태 순환**(시스템 → 라이트 → 다크 → 시스템)

2상태(라이트/다크) 토글은 첫 클릭 순간 "시스템 따라가기"로 **돌아갈 방법이 영구히 사라진다.**
OS 를 시간대별 자동 전환으로 쓰는 사용자에게는 기능 후퇴다. 3상태의 추가 비용은 분기 하나와
라벨 맵 하나(약 5줄)뿐이다.

저장 규약: `localStorage['dzh-theme']` 에 `'light' | 'dark'` 만 넣는다. **키가 없으면 시스템**
— 별도의 `'system'` 값을 저장하지 않으므로 "삭제 = 시스템 복귀"가 자연스럽고, 값 검증도
화이트리스트 2개로 끝난다.

버튼은 현재 모드를 **텍스트로** 표시한다(`테마: 시스템` / `테마: 라이트` / `테마: 다크`) —
아이콘만 쓰면 "지금 어느 모드인지"가 색·모양에만 실려 이 PRP 의 전제 1을 스스로 어긴다.

### 결정 T3 — FOUC 는 `<head>` 인라인 스크립트로 제거하고, `localStorage` 실패를 허용한다

```html
<head>
  …
  <script>
  /* body 파싱 전에 실행돼 첫 페인트부터 확정 테마로 그린다(FOUC 방지).
     localStorage 접근은 file:// 나 저장소 차단 환경에서 던질 수 있어 반드시 감싼다. */
  try{var m=localStorage.getItem('dzh-theme');
      if(m==='light'||m==='dark')document.documentElement.setAttribute('data-theme',m);}catch(e){}
  </script>
</head>
```

- `<head>` 안, 스타일 뒤, `<body>` 앞 → 첫 페인트 전에 속성이 확정된다.
- **`try/catch` 는 필수다.** 허브는 서버가 꺼져 있으면 `file://` 로도 열린다(`hub.py:101`).
  일부 브라우저 설정에서 `file://` 의 `localStorage` 접근은 `SecurityError` 를 던진다. 이 예외가
  새면 head 스크립트가 죽고 — 더 나쁘게는 — 하단 IIFE 에서 같은 일이 나면 **페이지 전체가
  안 그려진다**. 템플릿이 이미 같은 이유로 `parseSnapshotJson` 을 `try/catch` 로 감싼 선례
  (검수 n4)가 있다. 실패 시 동작: 시스템 설정만 따르고, 토글은 **이번 페이지 로드 동안만** 작동.
- 상수 `'dzh-theme'` 는 head 스크립트와 본문 IIFE 두 곳에 리터럴로 등장한다(head 스크립트는
  자족적이어야 해서 공유가 불가능하다). 이 중복은 T25-28 grep 으로 고정한다.

**수용하는 한계**: `http://localhost:8794` 와 `file://` 는 서로 다른 오리진이라 테마 선택이
공유되지 않는다. 해결하려면 서버에 쓰기 엔드포인트가 필요한데 허브는 **읽기 전용 화이트리스트
2경로**가 설계 정본이다(`hub_server.py:21`). 그 원칙을 깨면서까지 풀 문제가 아니다.

### 결정 T4 — 시스템 테마 변경을 실시간으로 따라간다 (오버라이드가 없을 때만)

허브는 하루 종일 열어 두는 페이지다. `matchMedia('(prefers-color-scheme: dark)')` 의
`change` 는 CSS 미디어 쿼리가 알아서 처리하므로 **JS 가 할 일은 없다** — `data-theme` 속성이
없을 때 미디어 쿼리가 그대로 먹기 때문이다. 즉 이 요구는 T1 의 CSS 구조에서 **공짜로**
따라온다. 별도 리스너를 달지 않는다.

### 팔레트 — 파랑–주황 축 (Okabe–Ito 기반)

색은 Okabe–Ito 색각 안전 팔레트에서 가져온다(파랑 `#0072B2`, 하늘 `#56B4E9`, 주황 `#E69F00`).
**같은 색을 라이트/다크에 그대로 쓰지 않는다** — `#E69F00` 은 흰 배경에서 대비 2.3:1 로
본문 텍스트 기준(WCAG AA 4.5:1)에 크게 미달한다. 그래서 라이트에서는 어둡게 조정한 주황을,
다크에서는 원색을 쓴다. **이것이 테마별 토큰이 필요한 진짜 이유다**(단순 반전이 아니다).

| 토큰 | 라이트 | 다크 | 용도 |
|------|--------|------|------|
| `--bg` | `#EEF3F8` | `#0E1621` | 페이지 배경 |
| `--surface` | `#FFFFFF` | `#16202D` | 카드·패널 |
| `--ink` | `#172033` | `#E6EDF5` | 본문 |
| `--head` | `#12335B` | `#DCE7F2` | h1·프로젝트명 (기존 `--navy` 대체) |
| `--muted` | `#5A6879` | `#94A5B8` | 보조 텍스트 |
| `--line` | `#D9E2EC` | `#26364A` | 테두리 |
| `--soft` | `#F4F7FB` | `#1B2634` | 옅은 배경 |
| `--accent` | `#0072B2` | `#56B4E9` | 진행·강조 (파랑) |
| `--accent-ink` | `#005B8F` | `#8ACBF0` | 파랑 계열 **텍스트**(대비 확보) |
| `--accent-soft` | `#E4F0F8` | `#12324A` | 파랑 배지 배경 |
| `--attention` | `#B45309` | `#E69F00` | 주의·경고 (주황) |
| `--attention-soft` | `#FBEEDC` | `#3B2B0D` | 주황 배지 배경 |
| `--shadow` | `0 8px 24px rgba(19,51,91,.06)` | `0 8px 24px rgba(0,0,0,.45)` | 카드 그림자 |

**초록(`#1F8A70`)과 빨강(`#C2410C`)은 템플릿에서 완전히 사라진다.** T25-30 이 이 문자열의
부재를 grep 으로 고정한다.

### 상태 배지 — 색 + 형태 + 텍스트 3채널

| 상태 | 색 | 형태(글리프) | 텍스트 | 색맹 시나리오 |
|------|-----|-------------|--------|--------------|
| `working` | 파랑 채움 + 좌측 인셋 바 | `●` | 작업중 | 주황과 명도·글리프 모두 다름 |
| `idle` | 중립(soft/muted) | `○` | 대기 | 채움 없음으로 구분 |
| `stale` | 주황 채움 + 좌측 인셋 바 | `▲` | 소식 없음 · 직전 X | 파랑과 글리프가 다름 |
| `done` | 투명 + 실선 테두리 | `✓` | 완료 | 유채색을 아예 쓰지 않음 |

- 글리프는 **JS 상수 맵**으로 넣는다 — 템플릿에 이미 있는 `STATE_LABEL` 옆에 `STATE_GLYPH` 를
  나란히 두는 것이 이 파일의 기존 문법이고, `aria-hidden="true"` 를 붙일 수 있어(CSS
  `::before` 로는 불가능) 스크린리더가 "검은 원"을 읽지 않는다.
- **텍스트가 1차 채널**이다. 색과 글리프는 훑어보기(scan) 속도를 위한 **중복** 채널이다.

```js
var STATE_GLYPH = {working:'●', idle:'○', stale:'▲', done:'✓'};

function renderStateBadge(state, baseState){
  var label = baseState ? stateLabel(state, baseState) : STATE_LABEL[state];
  return '<span class="badge state-' + state + '">'
       + '<span class="glyph" aria-hidden="true">' + STATE_GLYPH[state] + '</span>'
       + label + '</span>';
}
```

**GOTCHA**: 세션 배지는 `stateLabel(state, base_state)`(stale 이면 "직전 …" 병기)를, 프로젝트
배지는 `STATE_LABEL[state]` 를 쓴다 — 지금 코드가 그렇다(`hub_template.html:105` vs `:140`).
공통 함수로 묶을 때 `baseState` 를 **선택 인자**로 두지 않으면 stale 프로젝트에서
"소식 없음 · 직전 undefined" 가 나온다.

**GOTCHA**: `stateLabel()` 안의 `'직전 '` 문자열과 `renderTier1ActiveStep` ·
`renderTier1ImplProgress` 함수명은 **T25-12 가 grep 으로 검사한다.** 리팩토링하더라도 이 세
토큰은 그대로 남겨야 한다.

### 경고 표시

`.warnings` 는 빨강 대신 `--attention`(주황) + 좌측 3px 보더 + `::before{content:"⚠ "}` 로
바꾼다. 색만으로 심각도를 전달하지 않기 위해서다.

---

## 기능 2 — 토큰 사용량 플로팅 패널

### 결정 U1 — **마지막 원소 하나만** 본다. 뒤에서부터 유효한 것을 찾지 않는다

역방향 스캔은 얼핏 견고해 보이지만 더 나쁘다: `version: 3` 에서 마지막 샘플의 필드명이
바뀌면 스캔은 **몇 시간 전 샘플**을 찾아내 아무 표시 없이 화면에 올린다. 사용자는 그것이
낡은 값인지 알 수 없다. 마지막 원소만 보면 그 경우 패널이 사라지고 경고가 뜬다 —
**틀린 숫자보다 없는 숫자가 낫다.**

> **적용 대상 소멸.** `parse_usage_history` 삭제와 함께 이 규칙의 대상이 없어졌다(원칙 자체는 P2 의 필드 단위 탈락으로 계승) — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) 결정 P1·P2.

### 결정 U2 — 타입 검증은 **엄격한 int**, 범위는 0~100

```python
def _valid_percent(value: object) -> bool:
    # bool 은 int 의 서브클래스라 명시적으로 배제한다.
    # float 을 거부하는 이유가 핵심이다 — 스키마가 0~100 정수에서 0.0~1.0 실수로 바뀌면
    # 느슨한 변환은 "0%" 를 조용히 그린다. 그건 데이터 없음보다 나쁜 거짓말이다(요구 2와 같은 정신).
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100
```

`t` 도 같은 규칙(엄격한 int)을 쓴다 — 규칙이 하나면 설명도 테스트도 하나다.

**`version` 은 검사하지 않는다.** 버전이 3으로 올라도 모양이 같으면 잘 도는 패널을 죽일
이유가 없고, 모양이 바뀌면 위 필드 검증이 이미 잡는다. **검사는 값의 모양에만 건다.**

### 결정 U3 — 샘플이 **5시간**보다 오래되면 패널을 렌더링하지 않는다

`u.fh` 는 정의상 5시간 창의 사용률이다. 샘플이 5시간보다 오래됐다면 그 창은 **현재 창과 전혀
겹치지 않는다** — 즉 "세션 82%" 는 현재에 대해 아무 말도 하지 않는 숫자다. 그래서 만료
기준은 임의의 매직 넘버가 아니라 **데이터 자신의 창 길이**다(`USAGE_SESSION_WINDOW_HOURS = 5`).

- **주간 막대만 남기지 않고 패널 전체를 숨긴다.** 부분 패널은 새 상태를 하나 더 만들고
  ("세션은 왜 없지?"), 요구 3이 정의한 패널은 막대 **2개**다. 단순함을 택한다.
- **중간 상태(dim 처리, "오래됨" 배지)를 만들지 않는다.** 패널은 항상 "마지막 갱신 N분 전"을
  표시하므로 신선도는 이미 연속적으로 노출된다. 임계값과 시각 상태를 하나 더 만들 이유가 없다.

> **확장됨.** 5시간 만료는 그대로 유효하고, 여기에 "세션 창 롤오버 시 즉시 만료"(P5)가 더해졌다 — [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md).

### 결정 U4 — `config.json` 스위치 `show_usage_panel` 을 제공한다 (기본 `true`)

**근거 3가지**

1. **선례와 일관.** `hub/README.md` 「프라이버시 고지」는 "127.0.0.1:8794 에 닿는 로컬의 다른
   프로세스는 hub.html 에 인라인된 내용을 읽을 수 있다"고 이미 고지했고, 그 대응으로
   `record_prompt_excerpt:false` 를 제공한다. 이제 인라인되는 항목이 하나 늘었으니 같은 격의
   대응을 붙이는 것이 이 문서의 약속을 지키는 길이다.
2. **화면 공유·스크린샷.** 계정 단위 사용률은 프로젝트 이름보다 사적인 축의 정보다. 발표나
   페어링 중에 끄고 싶은 것은 자연스러운 요구다.
3. **탈출구.** 앱 포맷이 바뀌어 경고가 계속 뜨거나 패널이 거슬릴 때, 사용자가 코드를 고치지
   않고 멈출 수 있는 유일한 수단이다.

**중요**: `false` 는 **CSS 로 숨기는 것이 아니라 파일을 읽지 않는 것**이다. 그래야 진짜
프라이버시 제어다. 비용은 config 필드 1개 + 타입 표 1행 + README 1행 + 분기 1개.

### 결정 U5 — 패널에 닫기/접기 버튼을 두지 않는다

> **대체됨(superseded).** 이 결정은 [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md)
> 의 결정 C1 이 대체한다 — 사용자가 접기/펼치기를 명시적으로 요구했고, 폴링 내성은 불변식
> H1′ 로 해결했다. 아래 근거는 당시 판단의 기록으로 남긴다.

닫기 버튼은 곧바로 "폴링을 견뎌야 하는 사용자 상태"가 되어 `localStorage` 왕복과 재렌더
설계를 요구한다(테마와 같은 부담). 끄는 수단은 이미 U4 로 있고, 요구는 "보여준다"까지다.
YAGNI.

### 패널 명세

```
                          ┌─────────────────────────────────┐
                          │ Claude 사용 한도                │
                          │ 세션 (5시간)              10%   │
                          │ ▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
                          │ 주간 (7일)                19%   │
                          │ ▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░  │
                          │ 마지막 갱신 5분 전 · 약 15분 주기│
                          └─────────────────────────────────┘
                                   (화면 하단 고정)
```

| 항목 | 사양 |
|------|------|
| 배치 | `position:fixed; bottom:16px; left:50%; transform:translateX(-50%)`, `width:min(420px, calc(100vw - 32px))`, `z-index:20` (현행: hub-usage-collapse-and-grid.md L1·L3) |
| 컨테이너 | `<aside id="dzh-usage" class="usage" hidden></aside>` — **정적 마크업, `#dzh-app` 바깥**(불변식 H1) |
| 가림 방지 | 패널이 있을 때만 `document.body.classList.add('has-usage')` → `body.has-usage .wrap{padding-bottom:132px}`. 없을 때 빈 여백을 남기지 않는다 (현행: hub-usage-collapse-and-grid.md L1·L3) |
| 막대 | `<div class="usage-bar" role="progressbar" aria-valuenow=… aria-valuemin="0" aria-valuemax="100" aria-label="세션 한도 사용률">` + 내부 `<span>` 의 `width:N%` |
| 색 | 두 막대 모두 `--accent`(파랑) 단색. **임계값 색 변화 없음**(아래 대안 3) |
| 숫자 | 항상 정수 % 텍스트를 병기 — 막대 길이 + 숫자 = 2채널 |
| 시각 | `elapsedLabel(usage.sampled_at_ms)` 재사용, `title` 에 `formatTimestamp()` 절대시각 |
| 주기 고지 | `· 약 15분 주기` 정적 문구 — 5초 폴링과 갱신 주기가 다름을 사용자가 오해하지 않게 한다(리스크 3). **개정됨.** `· 세션 진행 중에만 갱신`(결정 P6, [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)) |
| 갱신 | `render()` 말미에서 `renderUsagePanel(snapshot.usage)` 호출. 30초 틱이 경과 라벨을 갱신한다 |
| 초기화 예정 시각 | 창별로 한 줄(현행: hub-usage-reset-time-and-refresh.md 결정 R2·R4) |

**JS 방어 규칙**: `#dzh-data` 는 신뢰 가능한 서버 생성물이지만 템플릿의 관행대로 방어한다 —
`Number()` 로 강제 변환 후 `isFinite` 가 아니면 패널을 그리지 않고, 막대 폭은
`Math.max(0, Math.min(100, value))` 로 클램프한다(표시 숫자는 원값). 이는 레이아웃 붕괴와
스타일 속성 주입을 동시에 막는다.

---

## 설계 결정 요약

| # | 결정 | 한 줄 근거 |
|---|------|-----------|
| M1 | 새 순수 모듈 `hub_usage.py` | `hub_parse.py` 선례 — 외부 계약 파서는 독립 모듈 |
| M2 | 폴링 동기화 영역 불변식 H1 | 사용자 상태를 가진 요소를 `#dzh-app` 밖에 둔다 → H1′ 로 개정됨 |
| D3 | 스냅샷에 now 파생값 금지 | content_key 가 매 사이클 바뀌어 재작성 폭주 |
| T1 | 미디어 쿼리 + 속성 오버라이드 | JS 실패해도 시스템 테마는 산다 |
| T2 | 3상태 순환 | "시스템으로 되돌리기"를 잃지 않는다 |
| T3 | head 인라인 스크립트 + try/catch | FOUC 제거, `file://` localStorage 예외 흡수 |
| T4 | 시스템 변경 리스너 없음 | CSS 미디어 쿼리가 이미 처리 |
| U1 | 마지막 원소만 파싱 | 낡은 샘플을 최신인 척 보여주지 않는다 |
| U2 | 엄격 int + 0~100 | 실수 스케일 변경이 "0%" 로 조용히 새는 것을 막는다 |
| U3 | 5시간 만료 → 미표시 | 창 길이 = 근거의 유효기간 |
| U4 | `show_usage_panel` 스위치 | 프라이버시 고지의 기존 약속과 일관 |
| U5 | 닫기 버튼 없음 | 폴링을 견디는 상태를 늘리지 않는다(YAGNI) → **대체됨**(hub-usage-collapse-and-grid.md C1) |
| — | 디자인 패턴 도입 없음 | 함수 3개 + dataclass 1개로 끝난다. 추상화할 두 번째 사례가 없다 |

---

## 테스트 계획

검증 정본: `bash tests/run.sh` (전체) / `python3 -m unittest discover -s tests/hub -t .` (파이썬).
이 레포에는 별도 linter·type checker 설정이 없다.

### 신규 — `tests/hub/test_hub_usage.py` (순수 로직)

`parse_usage_history`

| # | 입력 | 기대 |
|---|------|------|
| 1 | 샘플 3개(정상) | 마지막 샘플의 `t`/`fh`/`sd` 가 매핑된다 |
| 2 | `samples: []` | `None` |
| 3 | `samples` 키 없음 | `None` |
| 4 | 최상위가 배열/문자열 | `None` |
| 5 | 깨진 JSON(`"{not json"`) | `None` (예외 없음) |
| 6 | 빈 문자열 | `None` |
| 7 | 마지막 샘플에 `fh` 없음(`xu` 만 존재) | `None` |
| 8 | `fh: 0.87` (실수 스케일 변경) | `None` — **U2 회귀 방지의 핵심** |
| 9 | `fh: true` (bool) | `None` |
| 10 | `fh: 101` / `sd: -1` | `None` |
| 11 | `t: "1786433123899"` (문자열) | `None` |
| 12 | `version: 3` 인데 모양 동일 | 정상 파싱 — **버전 게이트 부재 회귀 방지** |
| 13 | `u` 가 dict 가 아님 | `None` |

`is_usage_sample_expired`

| # | 입력 | 기대 |
|---|------|------|
| 14 | 나이 4시간 59분 | `False` |
| 15 | 나이 정확히 5시간 | `True` (경계 포함) |
| 16 | 나이 5시간 1분 | `True` |
| 17 | 미래 시각(now < sampled_at, 시계 뒤틀림) | `False` |

### 추가 — `tests/hub/test_hub_collect.py`

기존 `ReadRecentEventsFailureIsolationTest` 의 monkeypatch 패턴(모듈 상수를 임시 경로로 바꾸고
`tearDown` 에서 복원)을 그대로 따른다.

| # | 시나리오 | 기대 |
|---|---------|------|
| 18 | 파일 없음 | `(None, ())` — **경고 0건**. 비-macOS 사용자 회귀 방지 |
| 19 | `show_usage_panel: false` | `(None, ())` 이며 **파일을 읽지 않는다**(`mock.patch` 로 read 호출 0회 확인) |
| 20 | 깨진 JSON | `(None, 경고 1건)`, 예외 없음 |
| 21 | 권한 없는 파일(`chmod 000`) | `(None, 경고 1건)`, 예외 없음 |
| 22 | 만료된 샘플(6시간 전) | `(None, ())` — 경고 없음 |
| 23 | 정상 파일 | `UsageSample` 반환 |
| 24 | 사용량 파일이 깨진 상태에서 `collect_snapshot()` | `projects` 는 정상 수집되고 `usage` 만 `None` — **실패 격리 회귀 방지** |
| 25 | `config.json` 의 `show_usage_panel: "yes"` | 기본값 `True` + 경고 1건 (기존 `LoadConfigValidationTest` 패턴) |

### 추가 — `tests/hub/test_hub_model.py`

| # | 시나리오 | 기대 |
|---|---------|------|
| 26 | `usage` 만 다른 두 스냅샷 | `snapshot_content_key` 가 **다르다**(패널 변화가 재작성을 유발한다) |
| 27 | `collected_at_ms` 만 다르고 `usage` 동일 | 키가 **같다**(5초마다 재작성되지 않는다 — D3 회귀 방지) |
| 28 | `usage=None` 스냅샷 렌더 | `render_hub_html` 결과에 `"usage": null` 이 들어가고 JSON 이 파싱된다 |

### 추가 — `tests/run.sh` T25 하위 검증

| # | 검사 |
|---|------|
| T25-27 | T25-10(순수 레이어 경계)의 파일 목록에 `hub_usage.py` 추가 — `open(`·`Path(`·`os.` 부재 |
| T25-28 | `hub_template.html` 에 `prefers-color-scheme` 와 `data-theme` 가 모두 존재하고, `'dzh-theme'` 리터럴이 2회 이상 등장(head 스크립트 + 본문 IIFE) |
| T25-29 | `hub_template.html` 에 `#1F8A70`·`#C2410C`·`#F59E0B` 가 **없다**(색각 안전 팔레트 회귀 방지) |
| T25-30 | `hub_template.html` 에 `STATE_GLYPH` 와 `aria-hidden` 이 존재(색 이외 채널 회귀 방지) |
| T25-31 | `hub/README.md` 에 `show_usage_panel` 행과 `plan-usage-history.json` 언급이 존재 |
| (기존) T25-1 | `HUB_FILE_COUNT` 10 ↔ 실제 파일 수 10 자동 대조 — 상수만 고치면 통과 |

### 기존 테스트 영향 — 확인 결과

| 대상 | 판정 | 근거 |
|------|------|------|
| `tests/hub/fixtures/*.html` (4개) | **안 깨진다** | 전부 `/dashboard` 생성물이며 `test_hub_parse.py` 만 읽는다. `hub_template.html` 과 무관 |
| `WriteHubHtmlAtomicityTest` | **안 깨진다** | 렌더 결과를 `'id="dzh-data">'` 로 자른 뒤 **그 다음** 첫 `</script>` 까지를 JSON 으로 판다. head 인라인 스크립트는 데이터 블록보다 **앞**에 있으므로 이 분할에 걸리지 않는다 |
| `_minimal_snapshot()` 헬퍼 | **안 깨진다** | 키워드 인자로 생성 → 기본값 `None` 인 새 필드는 무시된다 |
| `render_hub_html` 의 마커 탐색 | 주의 | `_DATA_MARKER_OPEN` 첫 등장 → 그 뒤 첫 `</script>` 를 치환한다. **데이터 블록 안쪽에 어떤 태그도 넣지 않는다**는 제약만 지키면 된다 |

### 수동 확인 (자동화 대상 아님)

- [ ] 다크 선호 OS 에서 새로고침 — **흰 화면 번쩍임이 없다**(FOUC)
- [ ] 토글 3회 클릭 시 시스템 → 라이트 → 다크 → 시스템 순환, 새로고침 후에도 선택 유지
- [ ] 서버 가동 중 5초 폴링을 30초 이상 지켜봐도 **테마가 초기화되지 않는다**
- [ ] `file://` 로 열었을 때 토글이 동작(저장은 안 될 수 있음), 콘솔 에러 없음
- [ ] 데스크톱 앱을 끄고 5시간 뒤(또는 파일 `t` 를 손으로 되돌려) 패널이 사라진다
- [ ] `config.json` 에 `show_usage_panel:false` → 패널 없음, `/hub status` 가 `enabled:false`
- [ ] macOS 라이트/다크 접근성 시뮬레이터 또는 색맹 시뮬레이터로 배지 4종 구분 가능

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 검증 |
|---|------|------|
| 1 | 템플릿 팔레트 토큰화 + 다크 블록 + head 스크립트 + 토글 + 배지 3채널 (**파이썬 무변경**) | 브라우저 수동 확인 4건, T25-28~30 |
| 2 | `hub_usage.py` + `test_hub_usage.py` (**배선 전, 독립**) | `unittest discover` 통과(케이스 1~17) |
| 3 | `hub_model` 필드 + `hub_collect` 배선 + config 스위치 + 테스트 | 케이스 18~28 통과 |
| 4 | 템플릿 사용량 패널 렌더 | 실제 화면에 막대 2개 표시, 하단 가림 없음 |
| 5 | `hub.py status` 2필드 + `install.sh` 10 + `README`·`commands/hub.md` + T25 5건 | `bash tests/run.sh` 전체 통과 |

각 마일스톤은 그 자체로 커밋 가능하다. 1과 2는 서로 의존하지 않아 순서를 바꿔도 된다.

---

## 리스크와 완화책

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | **허브의 읽기 경계를 벗어난다.** 지금까지 허브는 `~/.claude` 안만 읽었는데, macOS 데스크톱 앱 전용 경로를 새로 읽는다 | 리눅스·윈도우·터미널 전용 사용자에겐 항상 없는 파일 | 파일 부재를 **경고 없이** 정상 처리(반환 계약 표). 경로 상수는 `hub_collect` 한 곳에만 존재. `hub/README.md` 에 "macOS 데스크톱 앱이 있을 때만 표시된다"를 명시 |
| 2 | **비공개·비문서 포맷.** `version:2` 스키마가 앱 업데이트로 바뀔 수 있다 | 패널이 사라지거나(최선) 틀린 숫자를 보인다(최악) | 엄격 타입·범위 검증(U2), 마지막 원소만(U1), 실패는 `None` + 경고 1건. **파싱 실패가 collect 전체를 죽이지 않는다** — 케이스 24 가 이를 고정 |
| 3 | **갱신 주기(~15분) ≠ 폴링 주기(5초)** | 실시간 수치로 오해 | 패널에 "마지막 갱신 N분 전 · 약 15분 주기" 상시 노출, 5시간 초과는 미표시(U3) |
| 4 | **프라이버시** — 사용률이 `hub.html` 에 인라인되어 로컬 타 프로세스가 읽을 수 있다 | 계정 단위 정보 노출 | `show_usage_panel:false` 로 **읽기 자체를 중단**(U4), `hub/README.md` 프라이버시 고지에 1항 추가 |
| 5 | **다중 org.** 실측 환경은 org 1종뿐이라 조직 전환 시 동작이 미검증이다 | 다른 조직의 마지막 샘플이 현재 조직 것으로 보일 수 있다 | 마지막 샘플의 org 를 **필터하지 않는다**(어느 org 가 "현재"인지 알 방법이 허브에 없다). 이 한계를 `hub/README.md` 에 한 줄로 명시하고, 조직을 오가는 사용자는 U4 스위치로 끈다 |
| 6 | 서버가 파일을 읽는 중 앱이 파일을 통째로 다시 쓴다(찢긴 읽기) | 그 사이클만 JSON 파싱 실패 | 다음 사이클(5초)에 자동 복구. 경고 1건은 순간적으로 뜰 수 있으나 실패 격리는 유지 |
| 7 | 테마 오버라이드가 오리진별로 갈린다(`http` vs `file`) | 서버 on/off 를 오갈 때 테마가 달라 보인다 | 수용(T3). 해소하려면 읽기 전용 서버 원칙을 깨야 한다 |
| 8 | 새 파일 추가로 배포 파일 수 계약이 어긋난다 | `hub/install.sh` 설치 검증 실패 → 설치 중단 | 마일스톤 5에서 상수·문서·테스트를 한 커밋에 함께 고친다. T25-1 이 자동 대조 |

---

## 검토했으나 채택하지 않은 대안

1. **`hub_model.py` 에 파싱 함수를 넣고 새 파일을 만들지 않는다.**
   설치 파일 수·문서·테스트 목록 수정이 없어 가장 싸다. 그러나 `hub_model` 의 선언된 책임
   (이벤트→세션→표시)과 무관한 외부 포맷이 섞이고, 이미 565줄인 파일이 더 커진다.
   `hub_parse.py` 라는 반대 선례가 같은 레포 안에 있다 → 기각. (승인 항목 1에서 뒤집을 수 있다.)
2. **사용량 파일을 브라우저가 직접 읽는다(서버가 새 엔드포인트로 서빙).**
   `hub.html` 에 인라인하지 않으므로 프라이버시 표면이 줄어든다. 그러나 허용 경로 2개
   화이트리스트(`/`, `/hub.html`)라는 보안 설계 정본을 깨야 하고, `file://` 모드에서는 아예
   동작하지 않는다 → 기각.
3. **80% 임계값에서 막대를 주황으로 바꾼다.**
   위험 신호로 유용해 보이지만 (a) 매직 임계값을 새로 도입하고, (b) 막대 길이 + 숫자로 이미
   2채널이 확보돼 있으며, (c) 요구는 "사용률을 보여준다"까지다 → 기각(YAGNI).
4. **`u.xu` 를 세 번째 막대로 추가한다.**
   의미가 불확실하고(1359개 중 32개), 사용자 결정 3이 명시적으로 범위 밖으로 뒀다 → 기각.
5. **테마를 서버가 `hub.html` 에 구워 넣는다(오리진 문제 해소).**
   서버에 쓰기 경로가 생겨야 하고, 여러 브라우저 탭이 서로의 테마를 덮어쓴다 → 기각.
6. **`hub_server.py` 가 사용량 파일을 별도 주기(15분)로 읽는다.**
   파일 I/O 한 번은 5초 사이클에서 무시할 만한 비용이고(116KB, 로컬 SSD), 별도 타이머는
   상태와 실패 경로를 하나 더 만든다 → 기각. 측정 없는 최적화를 하지 않는다는 원칙과도 맞는다.

---

## 사용자 승인이 필요한 핵심 결정

1. **새 파일 `hub/bin/hub_usage.py` 를 추가한다** → 배포 파일 9개 → **10개**
   (`hub/install.sh` 상수 · `hub/README.md` 문구 2곳 · T25-10 목록 동반 수정).
   원치 않으면 대안 1(= `hub_model.py` 에 통합)로 되돌릴 수 있다.
2. **사용량 출처는 macOS 데스크톱 앱 전용 경로 하나뿐이며, 없거나 5시간보다 오래된 샘플은
   경고 없이 패널을 숨긴다.** 다른 OS·터미널 전용 사용자에게는 이 기능이 존재하지 않는다.
3. **`config.json` 에 `show_usage_panel`(기본 `true`)을 추가한다** — `false` 면 파일을 읽지도
   않는다. 프라이버시 고지의 기존 약속(`record_prompt_excerpt`)과 같은 격의 스위치다.
