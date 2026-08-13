# 허브 — 카드 상호작용(순서·모달)·헤더 정리·테마 2상태·사용량 출처 확보 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_template.html` · `hub_server.py` · `hub_model.py` · `hub_collect.py` · `hub_usage.py` (+ 신규 `hub_usage_fetch.py`) |
| 브랜치 | `main` (HEAD `5844f96`) — **작업 트리의 미커밋 변경이 설계 기준선이다** |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md) → [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) → [`hub-usage-collapse-and-grid.md`](./hub-usage-collapse-and-grid.md) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 공개 계약 변경(서버 경로 추가 · `ProjectView` 필드 추가 · `HubConfig` 필드 2개) + 5개 이상 파일 |
| 규모 | Large — 신규 2개 / 수정 13개 파일. 요구 6건이 **서로 독립적으로 되돌릴 수 있게** 마일스톤으로 쪼개져 있다 |
| 새 외부 의존성 | **없음** (Python 표준 라이브러리 `hashlib`·`urllib.request`·`subprocess` / 바닐라 CSS·JS) |
| 회귀 기준선 | `python3 -m unittest discover -s tests/hub -t .` **251건 OK**(실측) · `bash tests/run.sh` **24건** |
| **승인 상태** | **미승인** — 아래 「사용자 승인이 필요한 결정」 5건 |

---

## 요구사항 요약

통합 허브 대시보드(`/hub`)에 대한 개선 요구 6건이다. 성격이 셋으로 갈린다.

1. **데이터 출처 문제(R1)** — 사용량 패널의 유일한 생산자인 statusLine 훅이 **터미널 TUI 에서만
   발화**함이 실측됐다. 사용자는 Claude Code Desktop 앱과 Cursor 만 쓰므로 `rate_limits.json`
   이 영원히 생성되지 않는다. 소비 계약(`rate_limits.json` → `hub_usage.py` → 패널)은 멀쩡하고
   **생산자만 없다.**
2. **카드 상호작용 신설(R2·R3)** — 카드 순서를 사용자가 정하고(드래그, 신규는 맨 앞), 카드를
   누르면 그 프로젝트의 `.claude/dashboard.html` 을 **새 탭이 아니라 허브 안 모달**로 본다.
3. **화면 정리(R4·R5·R6)** — 프로젝트명 툴팁 제거, 우상단 고정 버튼 클러스터를 헤더 행 안으로
   이동, 테마 토글을 다크/라이트 2상태로 축소.

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 내가 정한 순서대로 카드를 보고, 카드를 눌러 그
> 프로젝트의 진행 대시보드를 허브를 떠나지 않고 살펴보고 싶다. 그리고 터미널 `claude` 를 쓰지
> 않더라도 내 사용 한도가 얼마나 남았는지 허브에서 보고 싶다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | 카드를 드래그해 순서를 바꾸면 폴링 재렌더 2회(2분) 뒤에도 그 순서가 유지된다 | 수동 M3 |
| S2 | 새로고침해도(http 오리진) 순서가 유지되고, 새로 나타난 프로젝트는 **맨 앞**에 붙는다 | 수동 M4·M5 |
| S3 | 카드를 누르면 모달이 열리고, 그 안의 티어 1 대시보드가 **5초마다 스스로 갱신**된다 | 수동 M8 |
| S4 | `/project/<잘못된키>/dashboard.html`·`/project/../../etc/passwd` 류 요청이 전부 404 | 자동(단위) |
| S5 | 서버 화이트리스트 확장 후에도 `bin/*.py`·`events/*.jsonl`·`config.json` 은 어떤 경로로도 200 이 아니다 | 자동(단위) |
| S6 | `.project-name` 에 `data-tooltip` 이 없다 | 자동(T25-58) |
| S7 | 새로고침·테마 버튼이 `h1` 과 같은 행 오른쪽에 있고, 뷰포트 360px 에서 `h1` 과 겹치지 않는다 | 수동 M12 |
| S8 | 테마 버튼이 라이트↔다크만 오가고, 첫 로드 시 시스템 선호로 확정된 뒤 OS 테마를 바꿔도 흔들리지 않는다 | 수동 M14 |
| S9 | R1 스파이크 결과가 문서에 기록되고, 성공 시 터미널 세션 없이 사용량 패널이 뜬다 | 수동 M16 |
| S10 | `python3 -m unittest discover -s tests/hub -t .` **≥251건** 통과 · `bash tests/run.sh` **24건** 통과 | 자동 |

---

## 영향 범위

### 신규 파일 (2개)

| 파일 | 이유 | 소속 요구 |
|------|------|----------|
| `hub/bin/hub_usage_fetch.py` | 사용량 API I/O 전용(Keychain 읽기 + HTTPS GET). **OAuth 토큰이 존재하는 유일한 파일**로 격리해 "누가 토큰을 볼 수 있는가"를 파일 하나의 질문으로 만든다 | R1 |
| `tests/hub/test_hub_usage_fetch.py` | 위 모듈의 실패 경로 단위 테스트(네트워크는 전부 mock) | R1 |

### 수정 파일 (13개)

| 파일 | 변경 | 소속 요구 |
|------|------|----------|
| `hub/bin/hub_template.html` | CSS 규칙 약 18개 추가·6개 수정, DOM 3블록 신설(모달·라이브영역·드래그 핸들), IIFE 함수 약 14개 추가, `<head>` 인라인 테마 스크립트 개정, 상단 주석의 불변식 H1′ → **H1″** 개정 | R2·R3·R4·R5·R6 |
| `hub/bin/hub_model.py` | `ProjectView.dashboard_key` 필드 추가, 순수 함수 `project_dashboard_key`·`build_dashboard_registry` 추가, 사용량 폴링 스케줄 순수 함수 3개 + `UsageApiPollState` 추가, `HubConfig` 필드 2개 추가 | R1·R3 |
| `hub/bin/hub_server.py` | 프로젝트 대시보드 라우트 추가, 대시보드 레지스트리를 서버 인스턴스에 보관, `_run_collect_cycle` 반환을 튜플로, 수집 루프에 사용량 폴링 게이트 삽입 | R1·R3 |
| `hub/bin/hub_collect.py` | `_CONFIG_FIELD_TYPES` 2행 추가, 사용량 API 실패 기록 3함수 추가 | R1 |
| `hub/bin/hub_usage.py` | `parse_usage_api_response` 추가(기존 검증 헬퍼 재사용) | R1 |
| `hub/bin/hub.py` | `/hub status` 에 진단 필드 3개 추가 | R1 |
| `hub/install.sh` | `HUB_FILE_COUNT` 11 → **12** | R1 |
| `tests/hub/test_hub_server.py` | `_run_collect_cycle` 튜플 반환에 맞춰 3곳 갱신 + 라우팅·화이트리스트 테스트 신설 | R1·R3 |
| `tests/hub/test_hub_model.py` | `dashboard_key`·레지스트리·폴링 스케줄 테스트 추가 | R1·R3 |
| `tests/hub/test_hub_usage.py` | `parse_usage_api_response` 테스트 추가 | R1 |
| `tests/run.sh` | `test_hub_docs_and_constants` 에 **T25-57~T25-64** 추가, `test_desc` 를 `(T25-1~T25-64)` 로 갱신 | 전부 |
| `hub/README.md` | 「화면 배치」 갱신, 「카드 순서」·「프로젝트 대시보드 모달」 절 신설, 「사용량 패널」에 API 출처 추가, 「설정」 표 2행, 「파일 배치」 2행 | 전부 |
| `commands/hub.md` | `/hub status` 새 필드 3개 설명 | R1 |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_parse.py` | 티어 1 DOM 파서. 이번 변경은 대시보드를 **파싱하지 않고 그대로 서빙**할 뿐이라 계약 접점이 0 이다 |
| `hub/bin/hub_statusline.py` | R1 은 **생산자를 하나 더 붙이는 것**이지 기존 생산자를 바꾸는 것이 아니다. statusLine 경로는 한 줄도 바뀌지 않는다(결정 A2) |
| `hub/bin/hub_hook.py`·`hub_settings.py` | 훅 수집·settings.json 조작. 접점 없음 |
| `hub/bin/hub_daemon.py` | 프로세스·브라우저 제어. 새 라우트는 서버 내부 문제라 데몬이 알 필요가 없다. `probe_http` 는 `/hub.html` 을 계속 쓴다 |
| `commands/dashboard.md` · `/dashboard` 템플릿 | **핵심**: 모달 안 라이브 갱신은 `/dashboard` 생성물을 **한 줄도 고치지 않고** 성립한다(결정 N4 참조). 티어 1 대시보드는 이미 `fetch(location.pathname)` 로 폴링하므로, 허브 서버가 그 경로를 서빙하기만 하면 된다 |
| `tests/hub/fixtures/*.html` | `/dashboard` 생성물 픽스처. 파서만 읽는다 |
| `install.sh`(루트) | 허브는 `hub/install.sh` 로 분리 설치된다(T25-2 가 이 분리를 강제한다) |

---

## 확정된 전제 (재론하지 않는다)

1. **단일 정적 HTML, 빌드 단계 없음.** 프레임워크·CDN·번들러·전처리기 금지. 바닐라 CSS/JS 로만 푼다.
2. **허브 서버는 읽기 전용이다.** 새 경로가 생겨도 **GET 만** 받고, 요청 데이터로 경로를
   조립하지 않으며, 어떤 경로로도 쓰기가 일어나지 않는다. `POST`/`PUT`/`DELETE` 는 구현하지
   않는다(핸들러가 `do_POST` 를 정의하지 않으므로 501 이 나간다).
3. **`file://` 모드는 1급 시민이다.** 서버가 꺼져 있으면 `/hub` 가 `file://` 로 연다
   (`hub.py:94`). 모든 요구는 `file://` 에서의 동작이 정의돼 있어야 하고, 그 모드에서 예외가
   새어 IIFE 전체가 죽는 일이 없어야 한다(`localStorage` 접근은 항상 `try/catch`).
4. **색각 안전 팔레트(Okabe–Ito 파랑–주황 축)를 유지한다.** 새 색 리터럴을 도입하지 않고 기존
   토큰(`--accent`·`--accent-ink`·`--muted`·`--head`·`--line`·`--surface`)만 참조한다(T25-29).
5. **네이티브 `title` 속성 금지.** T25-44 가 `title="` 문자열의 부재를 강제한다. 새로 넣는
   `<iframe>` 의 접근성 이름도 `title` 이 아니라 `aria-label` 로 준다(GOTCHA 5).
6. **순수 레이어 경계는 기계적으로 강제된다.** T25-10 이 `hub_model.py`·`hub_parse.py`·
   `hub_usage.py` 에 `open(`·`Path(`·`os.` 가 없음을 검사한다. 새 순수 함수는 이 제약 안에 있어야
   한다(`hashlib`·`json` 은 걸리지 않는다).

---

## 요구 R1 — 터미널 없이 사용량 데이터 확보

### 문제의 정확한 위치

현재 사용량 파이프라인은 이렇다.

```
[생산자]  Claude Code CLI(터미널 TUI) --stdin JSON--> hub_statusline.py
                                                          |
                                                          v  write_rate_limit_capture
                                              ~/.claude/hub/rate_limits.json
                                                          |
[소비자]  hub_collect.read_rate_limit_capture() ----------+
              -> hub_usage.parse_rate_limit_capture()  (순수)
              -> usage_sample_from_capture / resets_from_capture  (순수)
              -> HubSnapshot.usage / .rate_limit_resets
              -> #dzh-data -> renderUsagePanel()
```

**소비자 전체가 정상이다.** 끊긴 곳은 화살표 하나 — 데스크톱 앱·Cursor 세션에서는 statusLine
커맨드가 실행되지 않아 `rate_limits.json` 이 만들어지지 않는다(오케스트레이터 실측: 데스크톱 앱
활성 세션 중 캡처 미갱신).

또한 다음 두 가지가 실측으로 배제됐다.

- 세션 트랜스크립트(`~/.claude/projects/**.jsonl`)에 rate limit 데이터가 **없다**.
- `~/.claude` 안에 우리 캡처 외의 사용량 파일이 **없다**(데스크톱 앱이 남기던
  `plan-usage-history.json` 은 결정 P1 시점에 이미 사라졌다).

> **따라서 R1 의 과제는 "소비 계약을 바꾸는 것"이 아니라 "생산자를 하나 더 만드는 것"이다.**
> 이 방향을 최우선으로 검토하라는 지시와 코드의 실제 모양이 일치한다.

### 선택지 비교

| 안 | 방법 | 얻는 것 | 잃는 것 / 비용 | 판정 |
|----|------|---------|----------------|------|
| **A** | 상주 서버 수집 루프가 macOS Keychain 의 OAuth accessToken 으로 Anthropic **비공개** usage 엔드포인트를 저빈도 폴링해 `rate_limits.json` 을 쓴다 | 어떤 클라이언트를 쓰든(데스크톱·Cursor·터미널) 동작. 퍼센트 2개 + 리셋 2개를 한 번에 얻는다. **소비자 코드 0줄 변경** | 비공개 API(문서 없음·예고 없이 변경/차단 가능). 자격증명 취급 위험. macOS 한정. 첫 실행 시 Keychain 접근 승인 프롬프트 | **권고(조건부)** |
| B | 주기적으로 헤드리스 CLI(`claude -p …`)를 띄워 statusLine 을 발화시킨다 | 공식 경로만 쓴다 | (1) statusLine 은 TUI 상태줄 렌더링의 일부라 비대화형 `-p` 에서 발화한다는 근거가 없다 — **가정 위에 세운 설계**. (2) 발화하더라도 **한도를 재려고 한도를 태운다**(모델 호출 = 토큰 소모). (3) 사용자 몰래 세션을 만드는 것은 프라이버시 고지 위반 | **기각** |
| C | 데스크톱 앱의 Application Support 데이터를 읽는다 | 자격증명을 안 만진다 | 결정 P1 이 이미 겪은 실패의 재판(파일이 예고 없이 사라졌다). 위치·포맷 모두 미확인이고 앱 업데이트마다 깨진다 | **기각(주 안으로는)** |
| D | 아무것도 하지 않고 "패널은 터미널 세션이 필요하다"를 문서화한다 | 위험 0 | 요구 미충족 | **A 실패 시의 낙착점** |

### 결정 A1 — **스파이크(마일스톤 4-0)가 통과해야만 구현에 들어간다**

이 세션의 권한 정책이 Keychain·앱 데이터 조회를 차단해 **로컬 실재 여부가 미확인**이다.
검증되지 않은 전제 위에 파서와 폴러를 먼저 쓰는 것은 이 저장소가 금지하는 "추측 위의 코드"다.

스파이크는 **코드를 한 줄도 커밋하지 않고** 다음 3개를 확인한다. 메인 세션(사용자 승인 하)에서
수동 실행하고, 결과를 이 문서의 「스파이크 결과」 절에 기록한다.

| # | 확인할 것 | 방법 | 실패 시 |
|---|-----------|------|---------|
| SP1 | Keychain 항목이 존재하고 읽을 수 있는가 | `security find-generic-password -s "Claude Code-credentials" -w` 가 0 을 반환하는가 | → 안 D 로 낙착. R1 종료 |
| SP2 | 그 값이 JSON 이고 accessToken 필드 경로가 무엇인가 | 출력 JSON 의 키 구조 기록(**토큰 값 자체는 절대 기록하지 않는다**) | → 안 D |
| SP3 | usage 엔드포인트가 응답하는가, 응답 스키마의 필드명은 무엇인가 | `curl -sS -o - -w '%{http_code}'` 로 상태코드 + 본문 **키 구조만** 기록 | → 안 D |

> **SP3 의 산출물이 `parse_usage_api_response` 의 필드 대응표를 결정한다.**
> 스파이크 전에는 이 함수의 본문을 쓰지 않는다 — 지금 추측해서 적어 두면, 실제 스키마가
> 다를 때 "왜 이렇게 돼 있지"라는 화석만 남는다.

### 결정 A2 — 기존 소비 계약을 그대로 쓰고 **생산자만 추가한다**

새 생산자의 출력 타입은 기존 `hub_usage.RateLimitCapture` **그대로**다. 따라서:

- `HubSnapshot` 의 필드가 바뀌지 않는다 → `#dzh-data` 계약 불변 → **T25-56 통과**, 템플릿 무변경.
- `rate_limits.json` 포맷이 바뀌지 않는다 → statusLine 생산자와 **공존**한다.
- `same_capture_values`·`write_rate_limit_capture`·`is_usage_sample_expired`·
  `is_session_window_rolled_over`·`drop_passed_resets` 를 전부 재사용한다.

**두 생산자가 공존할 때**: 둘 다 계정 단위의 같은 숫자를 관측하므로 "나중에 관측한 쪽이 이긴다"로
충분하다. `same_capture_values` 게이트 덕분에 값이 같으면 아무도 쓰지 않아 `captured_at_ms` 의
의미("처음 관측한 시각", 결정 S3)도 그대로 보존된다.

### 결정 A3 — 폴링 위치는 **상주 서버 수집 루프 안**, 주기는 별도

수집 루프는 5초마다 돈다. 원격 API 를 5초마다 때리는 것은 논외다. 루프 안에 **독립적인 게이트**를
둔다.

```
매 사이클(5초):
  if should_attempt_usage_api_poll(now_ms, poll_state, config.usage_api_poll_interval_seconds):
      capture, failure = hub_usage_fetch.fetch_rate_limit_capture(now_ms)
      poll_state = next_usage_api_poll_state(now_ms, poll_state, succeeded=capture is not None)
      ...
```

- 기본 주기 `usage_api_poll_interval_seconds = 300`(5분). 한도 창이 5시간·7일이라 5분 해상도면
  충분하고, 하루 288회는 어떤 기준으로도 공손한 빈도다.
- **사이클 안 재시도는 하지 않는다.** 다음 주기가 곧 재시도다 — 재시도 루프를 따로 만들면
  실패가 몰릴 때 요청이 증폭된다.
- **연속 실패마다 지수 백오프**(5 → 10 → 20 → 40 → 60분 상한). HTTP 429 는 곧바로 상한으로
  점프한다(가장 강한 "그만 보내라" 신호에 가장 강하게 반응한다).
- `poll_state` 는 `_collect_loop` 의 **지역 변수**다. 모듈 전역 가변 상태를 만들지 않는다.
- 스케줄 판정은 전부 **순수 함수**(`hub_model.py`)라 시계 없이 단위 테스트된다.

### 결정 A4 — 보안 불변식 (양보 불가)

> **불변식 A-SEC.** OAuth accessToken 은 `hub_usage_fetch.py` 의 **지역 변수로만** 존재한다.
> 로그·`stderr`·`server.log`·`rate_limits.json`·`last_usage_api_error.json`·`hub.html`·
> `warnings` 그 어디에도 나타나지 않는다.

이를 코드 구조로 강제한다.

| 수단 | 내용 |
|------|------|
| 실패 사유는 **고정 어휘** | `fetch_rate_limit_capture` 는 `str(error)` 를 절대 돌려주지 않고 `FAILURE_REASON_MESSAGES` 의 리터럴만 돌려준다. 예외 메시지에 URL·헤더 파편이 섞여 나올 여지를 원천 차단한다 |
| Keychain 호출은 인자 리스트 | `subprocess.run([...], shell=False)` — 기존 T25-49 가 `hub_daemon.py` 에 강제하는 규칙과 같은 규칙을 새 모듈에도 적용한다(T25-61) |
| 토큰은 반환하되 저장하지 않는다 | `read_oauth_access_token()` 의 반환값을 받는 곳은 `fetch_rate_limit_capture` 하나뿐이고, 요청 헤더로 넘긴 뒤 참조를 버린다 |
| 화면에 새로 실리는 것은 없다 | 이 경로가 `hub.html` 에 더하는 값은 **기존과 똑같은 숫자 4개**(퍼센트 2 + 리셋 2)뿐이다 |
| grep 회귀 | T25-60 이 `hub_usage_fetch.py` 안에 `str(error)`·`print(`·`shell=True` 가 없음을 검사한다 |

### 결정 A5 — 실패는 **조용히 강등**하고 사유는 `/hub status` 에만

기존 규칙("usage 가 없으면 경고 없이 패널을 숨긴다", 결정 U3·U4)을 그대로 따른다. 화면에
`warnings` 를 띄우지 않는다 — 5분마다 실패하는 API 의 경고를 페이지에 상주시키면 노이즈다.

대신 **`last_collect_error.json` 과 똑같은 모양**의 파일 하나를 둔다(새 개념 0개).

```
~/.claude/hub/last_usage_api_error.json   {"at_ms": 1765..., "reason": "credential_unavailable"}
```

> **개정(2026-08-13, SP3 생략 개정과 함께)**: `reason` 이 `schema_mismatch` 일 때만 선택 필드
> `response_keys`(응답 JSON 의 키 경로·타입 목록, **값 절대 금지**)가 추가된다. 첫 폴링이
> 스파이크를 겸하기 위한 자기 진단 창구다.

`/hub status` 에 필드 3개를 더한다.

| 필드 | 뜻 |
|------|-----|
| `usage_api_enabled` | `config.usage_api_enabled` 값 |
| `usage_api_last_attempt_age_ms` | 마지막 시도로부터 지난 시간(ms). `null` 이면 아직 한 번도 시도 안 함 |
| `usage_api_last_failure` | `{at_ms, reason}` 또는 `null`. 성공하면 지워진다 |

이 셋으로 "패널이 안 뜨는 이유"의 남은 사각지대가 사라진다: 스위치 off / Keychain 실패 /
인증 만료 / 스키마 변경이 전부 다른 `reason` 으로 구분된다.

### 결정 A6 — `usage_api_enabled` 기본값은 **false**(옵트인)

자격증명을 만지고 외부로 나가는 기능이다. 기본값 on 은 사용자가 모르는 사이에 이 저장소가
자격증명을 읽고 원격 호출을 시작한다는 뜻이다. `/hub statusline on` 이 이미 옵트인인 것과
같은 이유·같은 온도를 유지한다.

### 결정 A7 — 스키마 변경 시의 강등 동작

`parse_usage_api_response` 는 `hub_usage.py` 의 기존 법을 그대로 따른다 — **계약이 안 맞으면
예외가 아니라 `None`**. 그 위에 두 가지를 더한다.

1. `None` 이면 `reason="schema_mismatch"` 로 실패를 기록하고 **기존 캡처를 덮어쓰지 않는다.**
   낡았지만 참인 값이 "값 없음"보다 낫고, 낡은 값은 5시간 만료 규칙(U3)이 알아서 지운다.
2. 퍼센트·리셋 **네 값이 전부 없는** 캡처는 쓰지 않는다(기존 `parse_*` 들의 규칙과 동일).

### 결정 A8 — `file://` 모드와 전경 `hub collect` 에서는 **호출하지 않는다**

폴링은 상주 서버 루프에만 있다. 근거:

- `/hub open` 은 사용자를 기다리게 하는 전경 명령이다. 여기에 최대 10초의 네트워크 왕복을 넣으면
  체감이 즉시 나빠진다.
- 서버가 꺼져 있다는 것은 "허브를 상시로 안 쓴다"는 뜻이고, 그 상태에서 자격증명을 읽는 것은
  사용자의 기대와 어긋난다.
- 결과: 서버가 꺼진 상태에서는 **마지막으로 성공한 캡처**가 그대로 보이다가 5시간 뒤 만료된다.
  기존 동작과 정확히 같다.

### 결정 A9 — macOS 외 플랫폼

`security` 명령이 없으면 `read_oauth_access_token()` 이 `None` → `credential_unavailable` →
조용한 강등. 다른 OS 의 자격증명 저장소를 지금 지원하지 않는다(YAGNI — 사용자는 macOS 다).

### R1 인터페이스

**`hub/bin/hub_usage_fetch.py` (신규 · I/O 전용)**

```python
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"   # ← SP3 이 확정
KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"
FETCH_TIMEOUT_SECONDS = 10
KEYCHAIN_TIMEOUT_SECONDS = 5

FailureReason = Literal[
    "credential_unavailable",   # Keychain 항목 없음·잠김·명령 부재·플랫폼 미지원
    "credential_unparsable",    # 항목은 읽었으나 토큰 필드가 없다
    "http_unauthorized",        # 401/403 — 토큰 만료. 재로그인 필요
    "http_rate_limited",        # 429 — 즉시 백오프 상한
    "http_error",               # 그 외 4xx/5xx
    "network_error",            # 타임아웃·DNS·연결 실패
    "schema_mismatch",          # 200 인데 우리가 아는 모양이 아니다
]

FAILURE_REASON_MESSAGES: dict[str, str]
    """사유 → 사람이 읽는 고정 문구. 예외 메시지를 절대 섞지 않는다(불변식 A-SEC)."""

def read_oauth_access_token() -> str | None:
    """macOS Keychain 에서 Claude Code OAuth accessToken 을 읽는다. 실패하면 None.

    반환값은 절대 로그·파일·hub.html 에 남기지 않는다(불변식 A-SEC).
    """

def fetch_rate_limit_capture(now_ms: int) -> tuple[RateLimitCapture | None, str | None]:
    """사용량 API 를 1회 호출해 캡처를 만든다. (캡처, 실패사유) 중 정확히 하나가 채워진다."""
```

**`hub/bin/hub_usage.py` (순수 · 추가)**

```python
def parse_usage_api_response(text: str, captured_at_ms: int) -> RateLimitCapture | None:
    """usage API 응답 JSON 에서 캡처를 만든다. 계약이 안 맞으면 None(예외를 던지지 않는다).

    필드 대응표는 스파이크 SP3 이 확정한다. 값 검증은 `_valid_used_percentage`·
    `_valid_resets_at_ms` 를 그대로 재사용한다 — 퍼센트 판정 규칙이 출처마다 갈리면
    상태줄과 패널이 다른 숫자를 보이게 된다(결정 P7 과 같은 이유).
    """
```

**`hub/bin/hub_model.py` (순수 · 추가)**

```python
USAGE_API_BACKOFF_MAX_MULTIPLIER = 12          # 기본 5분 기준 상한 60분
USAGE_API_RATE_LIMITED_MULTIPLIER = 12         # 429 는 곧바로 상한

@dataclass(frozen=True)
class UsageApiPollState:
    """사용량 API 폴링의 스케줄 상태. 수집 루프의 지역 변수로만 산다(전역 상태 금지)."""
    last_attempt_at_ms: int | None = None
    consecutive_failures: int = 0
    forced_multiplier: int | None = None        # 429 가 요구한 즉시 상한

def usage_api_poll_delay_ms(state: UsageApiPollState, base_interval_seconds: int) -> int:
    """다음 시도까지 기다릴 시간(ms). 연속 실패마다 2배, 상한까지."""

def should_attempt_usage_api_poll(
    now_ms: int, state: UsageApiPollState, base_interval_seconds: int
) -> bool:
    """지금 사용량 API 를 호출해도 되는가. 첫 시도(last_attempt_at_ms 가 None)는 항상 True."""

def next_usage_api_poll_state(
    now_ms: int, state: UsageApiPollState, failure_reason: str | None
) -> UsageApiPollState:
    """시도 결과를 반영한 **새** 상태를 돌려준다. 성공이면 실패 카운트를 0 으로 되돌린다."""
```

**`HubConfig` 필드 추가**

| 필드 | 타입 | 기본값 | 뜻 |
|------|------|--------|-----|
| `usage_api_enabled` | `bool` | `False` | 사용량 API 폴링 스위치(결정 A6) |
| `usage_api_poll_interval_seconds` | `int` | `300` | 폴링 기본 주기 |

`_CONFIG_FIELD_TYPES` 에 두 행을 같이 추가해야 한다(누락하면 `KeyError` — GOTCHA 1).

**`hub/bin/hub_collect.py` (추가)**

```python
LAST_USAGE_API_ERROR_PATH = HUB_HOME / "last_usage_api_error.json"

def record_usage_api_failure(reason: str) -> None:
    """사용량 API 실패를 기록한다. 이 함수 자신은 예외를 던지지 않는다
    (record_collect_failure 와 완전히 같은 형태·같은 이유)."""

def clear_usage_api_failure() -> None: ...
def read_last_usage_api_failure() -> dict | None: ...
```

> **GOTCHA 2 — `show_usage_panel:false` 는 API 폴링도 끈다.** 기존 규칙은 "스위치가 꺼져 있으면
> 캡처 파일을 **열지도 않는다**"(전제 8)였다. 이 정신을 유지하려면 폴링 게이트는
> `config.show_usage_panel and config.usage_api_enabled` 두 조건을 **모두** 봐야 한다. 하나만
> 보면 "패널을 껐는데 계속 자격증명을 읽고 원격 호출을 한다"는, 사용자가 가장 화낼 상황이 된다.

---

## 요구 R2 — 카드 순서 사용자 지정 + 고정

### 현재 상태

`stableSortedProjects()`(`hub_template.html:722`)가 이미 존재한다. 서버의 활동순 정렬을 무시하고
**최초 등장 순서**를 `projectDisplayOrder` 에 기억해 카드 위치를 고정한다. 다만 (1) 메모리에만
살아 새로고침하면 사라지고, (2) 신규 프로젝트를 **맨 뒤에** 붙이고(`push`), (3) 사용자가 순서를
바꿀 수단이 없다.

즉 **뼈대는 이미 있고 세 가지를 고치면 된다.**

### 저장 위치 — 선택지 비교

| 안 | 방법 | 얻는 것 | 잃는 것 | 판정 |
|----|------|---------|---------|------|
| **A** | `localStorage['dzh-project-order']` = 경로 배열 JSON | 서버 무변경. 테마·사용량 접힘과 **같은 메커니즘**(세 번째 UI 선호가 세 번째 방식을 쓰지 않는다). `file://` 에서도 동작 | 오리진별 분리(`file://` ↔ `http://localhost:8794`), 브라우저별 분리 | **권고** |
| B | `~/.claude/hub/card_order.json` + 서버 쓰기 엔드포인트 | 오리진·브라우저 무관하게 공유 | **읽기 전용 서버라는 설계 정본을 깬다**(전제 2). 루프백 포트에 쓰기가 열리면 로컬의 임의 프로세스가 사용자 설정을 조작할 수 있다. 요청 본문 파싱·원자적 쓰기·동시 탭 충돌 처리가 새로 필요 | 기각 |
| C | 서버가 정렬해 스냅샷에 담는다(순서를 데이터로) | 클라이언트가 단순해진다 | 순서 변경을 서버에 알릴 수단이 없으면 B 와 같은 문제. 게다가 순서가 바뀔 때마다 `snapshot_content_key` 가 바뀌어 `hub.html` 이 재작성된다 | 기각 |

> **결정 O1 — 안 A.** 화면 상태는 서버에 저장하지 않는다는 기존 판단
> (`hub-usage-collapse-and-grid.md` 대안 2, `hub-theme-and-usage-panel.md` 대안 5)을
> 세 번째로 같은 근거로 반복한다. 오리진 분리는 테마·접힘이 이미 지고 있는 **기존 한계**이고,
> 실사용은 서버 모드 하나로 수렴한다.

### 결정 O2 — 저장 순서와 표시 순서를 분리한다

두 배열의 역할이 다르다. 이름으로 구분한다.

| 이름 | 사는 곳 | 내용 | 규칙 |
|------|---------|------|------|
| `storedProjectOrder` | 모듈 스코프 + `localStorage` | 사용자가 정한 순서. **지금 화면에 없는 경로도 남아 있다** | 최대 `MAX_STORED_PROJECT_ORDER`(200)개, 초과분은 뒤에서 잘라낸다 |
| `renderProjectPaths` | 매 렌더 계산(순수) | 이번에 실제로 그릴 카드의 순서 | `신규(서버 활동순) ++ (저장순서 ∩ 현재목록)` |

```js
function orderedProjectPaths(storedOrder, snapshotPaths){   // 순수 — DOM·저장소에 닿지 않는다
  var known = storedOrder.filter(function(p){ return snapshotPaths.indexOf(p) !== -1; });
  var fresh = snapshotPaths.filter(function(p){ return storedOrder.indexOf(p) === -1; });
  return fresh.concat(known);            // ★ 신규는 맨 앞(요구), 신규끼리는 서버 활동순
}
```

### 결정 O3 — 사라진 프로젝트의 엔트리는 **지우지 않는다**

현행 코드는 매 렌더마다 `filter(presentPaths)` 로 즉시 잘라낸다. 순서가 메모리에만 살 때는
무해했지만, 영속되는 순간 **"하루 쉰 프로젝트가 자리를 잃는다"** 는 이 기능의 목적에 정면으로
반하는 동작이 된다(프로젝트는 `ignore_globs` 변경·디렉토리 이동·티어 3 소멸 등으로 일시적으로
목록에서 빠질 수 있다).

- 표시는 어차피 **교집합**이라 없는 엔트리는 화면에 영향이 0 이다.
- 무한 증가만 막으면 된다 → 상한 200개(경로 문자열 200개 ≈ 10KB 미만). 초과 시 **뒤에서**
  자른다(뒤쪽 = 사용자가 가장 나중에 보는 영역).

### 결정 O4 — 저장 시점: "계산된 순서 ≠ 저장된 순서"일 때만

매 렌더마다 쓰면 30초·60초마다 저장소를 두드린다. 드래그 종료 시점에만 쓰면 신규 프로젝트가
저장되지 않는다(다음 로드에서 다시 "신규"로 취급돼 또 맨 앞에 붙으므로 **결과는 같지만**,
신규끼리의 상대 순서가 활동에 따라 흔들린다). 두 조건을 하나로 합친다.

```
매 렌더 끝: if (계산된 순서가 저장된 순서와 다르면) persistProjectOrder(계산된 순서)
```

정상 상태에서는 첫 렌더 1회만 쓰고 그 뒤로는 0회다.

### 결정 O5 — 조작 수단: **전용 드래그 핸들** + 키보드 이동

> **대체됨(superseded, 2026-08-13).** 이 결정은 [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md)
> 의 결정 DG1~DG3 이 대체한다 — 사용자가 드래그 전용 조작을 명시적으로 요구해 키보드
> 이동·낭독(`#dzh-live`)·포커스 복원을 제거했다(WCAG 2.1.1 회귀, 결정 DG2 에 기록). 아래
> 근거는 당시 판단의 기록으로 남긴다.

| 안 | 장점 | 단점 | 판정 |
|----|------|------|------|
| **A. 카드 안 전용 핸들(`≡`)에 HTML5 DnD + 핸들 포커스 시 방향키 이동** | 의존성 0. **R3(카드 전체 클릭)과 충돌이 구조적으로 없다** — 클릭 영역과 드래그 영역이 다른 요소다. 키보드 경로가 있어 WCAG 2.1.1 을 만족 | 핸들 1개가 카드에 추가된다. 터치 미지원(HTML5 DnD 의 한계) | **권고** |
| B. 카드 전체를 draggable | 핸들이 없어 깔끔 | **R3 과 정면 충돌** — "3px 움직인 클릭"이 드래그인지 열기인지 판정해야 한다(임계값 튜닝 = 버그 온상). 카드 안 텍스트 선택도 막힌다 | 기각 |
| C. Pointer Events 로 직접 구현 | 터치 지원 | 100줄 이상. 자동 스크롤·고스트 이미지·접근성을 전부 손으로 만들어야 한다 | 기각(YAGNI) |
| D. 드래그 없이 `◀ ▶` 이동 버튼만 | 가장 단순·가장 접근성 좋음 | 카드가 10개 넘으면 클릭 수가 폭발 | 기각(단, A 의 키보드 경로가 D 를 흡수한다) |

**핸들 스펙**

```html
<button class="card-drag-handle" type="button" draggable="true"
        aria-label="위치 이동: {프로젝트명}" data-tooltip="드래그하거나 ←/→ 키로 순서 변경">≡</button>
```

- `.project-head` 의 **맨 앞**에 놓는다(왼쪽 = 잡는 곳이라는 보편 관례).
- **키보드**(**대체됨 R7** — 조작 수단이 드래그 하나로 줄며 함께 제거된다): 핸들에 포커스가
  있을 때 `ArrowLeft`/`ArrowRight` → 한 칸 이동(`preventDefault` 로 페이지 스크롤 억제).
  `Home`/`End` → 맨 앞/맨 뒤.
- **낭독**(**대체됨 R7** — 키보드 경로가 사라지며 `#dzh-live` 자체가 제거된다): 이동 후 정적
  `aria-live="polite"` 영역(`#dzh-live`)에 `"{이름} — 3 / 9 번째"` 를 넣는다.
- **포커스 복원**(**대체됨 R7** — 드롭은 포커스를 옮기지 않으므로 복원할 대상이 없어진다):
  이동 뒤 재렌더가 포커스를 날리므로, `focusHandleAfterRender` 에 경로를 담아 두고 렌더 직후
  `[data-project-path="…"] .card-drag-handle` 로 포커스를 복원한다.

### 결정 O6 — 드래그 중에는 `#dzh-app` 을 다시 그리지 않는다

폴링(60초)·틱(30초)이 드래그 도중 `app.innerHTML` 을 갈아 끼우면 드래그 중인 노드가 사라져
드롭이 취소된다. `usageEl.innerHTML` 문제(결정 C1)와 **같은 종류의 문제**다.

```js
var isReordering = false;      // dragstart 에서 true, dragend/drop 에서 반드시 false
function render(){
  if(isReordering) return;     // 다음 틱이 알아서 따라잡는다
  …
}
```

`dragend` 는 드롭 성공·취소·`Escape` 어느 경우에도 반드시 발화하므로 플래그가 영구히 걸리는
경로가 없다. 키보드 이동은 순간적이라 이 플래그를 쓰지 않는다.

### 결정 O7 — 이벤트는 전부 `document` 위임

`#dzh-app` 의 자식은 렌더마다 전멸한다. 툴팁 IIFE 가 이미 확립한 규약(결정 T2)을 그대로 따른다.
`dragstart`·`dragover`·`drop`·`dragend`·`keydown` 을 `document` 에 한 번씩만 건다.

카드에는 `data-project-path="{경로}"` 를 부여해 위임 핸들러가 `closest('[data-project-path]')`
로 대상을 찾는다.

> **GOTCHA 3 — `dragover` 에서 `preventDefault()` 를 부르지 않으면 `drop` 이 아예 안 온다.**
> HTML5 DnD 의 가장 흔한 함정이다. 드롭 대상 카드 위에서 반드시 `event.preventDefault()` 를 부른다.

### R2 인터페이스 (템플릿 JS)

```js
var PROJECT_ORDER_STORAGE_KEY = 'dzh-project-order';
var MAX_STORED_PROJECT_ORDER = 200;
var DRAG_HANDLE_SELECTOR = '.card-drag-handle';

function readStoredProjectOrder(): string[]
    /** 저장된 카드 순서를 읽는다. 저장소 차단·깨진 값이면 빈 배열(=서버 순서로 시작). */

function persistProjectOrder(order: string[]): void
    /** 카드 순서를 저장한다. 상한을 넘으면 뒤에서 잘라낸다. 저장 실패는 흡수한다. */

function orderedProjectPaths(storedOrder: string[], snapshotPaths: string[]): string[]
    /** 이번 렌더의 카드 순서. 신규는 맨 앞. 순수 함수 — DOM·저장소에 닿지 않는다. */

function moveProjectPath(order: string[], path: string, targetIndex: number): string[]
    /** path 를 targetIndex 로 옮긴 **새** 배열. 범위를 벗어나면 클램프. 순수 함수. */
    // 폐기됨(R7) — hub-first-entry-and-ui-signals.md 결정 DG4. 드롭이 DOM 순서를 그대로
    // 커밋하므로 인덱스 산술 자체가 필요 없어진다.

function announceProjectPosition(displayName: string, index: number, total: number): void
    /** #dzh-live 에 이동 결과를 넣어 스크린리더가 낭독하게 한다. */
    // 폐기됨(R7) — hub-first-entry-and-ui-signals.md 결정 DG1·DG2. 키보드 경로 제거로
    // #dzh-live 자체도 함께 삭제된다.
```

`stableSortedProjects()` 는 `orderedProjectPaths()` 로 대체되고 삭제된다.

### R2 의 `file://` 모드

동일하게 동작한다. `localStorage` 가 막힌 환경이면 순서 변경이 **이번 로드 동안만** 유효하다
(테마·접힘과 같은 처리). `file://` 모드는 포커스 복귀 시 `location.reload()` 하므로 이 경우
순서가 초기화되는 것이 눈에 띌 수 있다 — 알려진 한계로 문서화한다.

---

## 요구 R3 — 카드 클릭 → 프로젝트 대시보드 모달

### 결정 N1 — 서버 경로: `/project/<16자리 hex>/dashboard.html`

키 후보 비교.

| 안 | 키 | 문제 |
|----|-----|------|
| A. `encode_project_dir_name(path)` 재사용 | `-Users-byron-...` | `/`·`.` 이 모두 `-` 가 되는 단방향 변환이라 **서로 다른 두 경로가 같은 키가 될 수 있다**(`/a.b` 와 `/a/b`). 충돌하면 **다른 프로젝트의 대시보드를 보여준다** — 조용한 오답이라 최악이다 |
| B. 목록 인덱스(`/project/0/…`) | `0`,`1`,… | 수집할 때마다 순서가 바뀐다. 모달을 열어 둔 채 재수집되면 **다른 프로젝트로 바뀐다** |
| **C. `sha256(경로)` 앞 16자리 hex** | `3f9a…` | 충돌 실질 0. 문자 집합이 `[0-9a-f]` 뿐이라 **경로로 오독될 수 있는 문자가 아예 없다**. 경로에서 결정적으로 파생되므로 서버 재기동·재수집 후에도 같은 키가 유지된다 |

> **결정 N1 — 안 C.** 이 설계의 보안 주장은 "키가 안전하다"가 아니라 **"핸들러가 요청 문자열로
> 경로를 조립하지 않는다"** 이다(결정 N3). hex 키는 그 위에 얹는 두 번째 방어선이다.

### 결정 N2 — 키는 서버가 계산해 스냅샷에 싣는다

클라이언트가 sha256 을 계산하려면 `crypto.subtle`(비동기 · `file://`·비보안 컨텍스트에서
불가)이 필요하다. 서버가 계산하는 것이 유일하게 온전한 선택이다.

```python
@dataclass(frozen=True)
class ProjectView:
    …
    dashboard_key: str | None = None    # 티어 1 프로젝트만 값을 갖는다. None 이면 카드가 클릭 대상이 아니다
```

- 기본값 `None` 을 주어 기존 생성자 호출부·테스트가 깨지지 않는다.
- `asdict` 에 결정적으로 포함되므로 `snapshot_content_key` 는 안정적이다(경로가 안 바뀌면 키도
  안 바뀐다 → 불필요한 `hub.html` 재작성 없음).
- **"클릭 가능 ⇔ 티어 1"** 로 규칙을 하나로 묶는다. `dashboard.html` 이 있어도 DOM 계약이 안
  맞아 티어 2 로 강등된 프로젝트는 클릭할 수 없다 — 화면의 배지와 클릭 가능 여부가 **항상
  일치**하는 것이, 별도 플래그를 하나 더 만들어 얻는 이득보다 크다(수용하는 한계).

```python
DASHBOARD_KEY_LENGTH = 16

def project_dashboard_key(project_path: str) -> str:
    """프로젝트 절대경로 → 대시보드 서빙용 불투명 키(sha256 앞 16자리 hex)."""

def build_dashboard_registry(snapshot: HubSnapshot) -> dict[str, str]:
    """스냅샷에서 {대시보드 키: dashboard.html 절대경로} 를 만든다. 티어 1 프로젝트만 담는다."""
```

### 결정 N3 — 핸들러는 **요청 문자열로 경로를 만들지 않는다**

```python
ALLOWED_REQUEST_PATHS = ("/", "/hub.html")      # ← 그대로 유지(T25-15)
PROJECT_DASHBOARD_PATH_PATTERN = re.compile(r"^/project/([0-9a-f]{16})/dashboard\.html$")
```

```
do_GET:
  1. path in ALLOWED_REQUEST_PATHS       → hub.html 서빙 (기존 경로 무변경)
  2. PROJECT_DASHBOARD_PATH_PATTERN 매치 → 키를 **딕셔너리에서 조회**
       registry = self.server.dashboard_paths_by_key
       target = registry.get(key)        ← 문자열 결합 없음. 조회 실패면 404
       target 이 실제 파일이 아니면 404  ← 수집 이후 삭제됐을 수 있다(TOCTOU)
  3. 그 외                               → 404
```

> **경로 traversal 이 구조적으로 불가능한 이유**: 핸들러는 요청에서 얻은 문자열을 **경로의
> 일부로 쓰지 않는다.** 오직 "수집 파이프라인이 만든 딕셔너리의 키인가"만 묻는다. 딕셔너리의
> **값**은 전부 `collect_snapshot` 이 실제로 발견한 프로젝트 경로에서 나왔다. `..`·절대경로·
> URL 인코딩·유니코드 정규화 어떤 기교도 딕셔너리에 없는 키를 만들어 낼 수 없다.
> 정규식(`[0-9a-f]{16}`)은 그 앞에 있는 저렴한 1차 거름망이다.

**레지스트리를 어디에 두는가**: 모듈 전역 가변 상태는 금지다(CLAUDE.md). `ThreadingHTTPServer`
인스턴스의 속성으로 둔다 — 핸들러는 `self.server` 로 닿고, 수집 스레드는 매 사이클 **새 딕셔너리를
통째로 대입**한다(제자리 변형 금지). 참조 교체는 원자적이라 별도 락이 필요 없고, 이 저장소의
불변성 규칙과도 맞는다.

```python
httpd.dashboard_paths_by_key = {}                      # run_server 에서 bind 직후 초기화
…
content_key, registry = _run_collect_cycle(last_content_key)   # 반환 튜플로 변경
if registry is not None:
    httpd.dashboard_paths_by_key = registry            # 통째 교체
```

> `_run_collect_cycle` 의 반환이 `str | None` → `tuple[str | None, dict | None]` 로 바뀐다.
> 기존 테스트 3곳(`test_hub_server.py`)이 반환값을 직접 비교하므로 **언패킹으로 갱신**한다
> (이 저장소는 `read_recent_events` 등 다중 반환에 튜플을 쓰는 관례가 이미 있다).

**응답 헤더**: 기존 `hub.html` 응답과 동일(`Content-Type: text/html; charset=utf-8`,
`Content-Length`, `Cache-Control: no-store`) + **`X-Content-Type-Options: nosniff`**.
nosniff 를 이 경로에만 더하는 이유: `hub.html` 은 이 프로세스가 생성한 파일이지만, 대시보드는
**우리가 만들지 않은 디스크 위의 파일**이라 내용이 무엇이든 `text/html` 로만 해석되게 못 박는다.

### 결정 N4 — 모달 안 라이브 갱신은 **`/dashboard` 를 한 줄도 고치지 않고** 성립한다 (확인함)

`.claude/dashboard.html` 을 직접 읽어 확인한 사실:

| 확인 항목 | 실제 코드 | 결과 |
|-----------|-----------|------|
| 갱신 모드 판정 | `var isServed = location.protocol === 'http:' \|\| location.protocol === 'https:';` (490~510행대) | iframe 이 `http://localhost:8794/...` 를 로드하면 **서버 모드**로 판정된다 |
| 폴링 대상 | `fetch(location.pathname, {cache:'no-store'})` (660행) | iframe 의 `location.pathname` = `/project/<키>/dashboard.html` → **우리가 서빙하는 바로 그 경로** |
| 주기 | `POLL_INTERVAL_MS = 5000` | 모달 안에서 5초마다 자기 자신을 다시 받아 갱신한다 |

> **즉 서버가 그 경로를 서빙하는 것만으로 모달 안 대시보드가 살아 움직인다.** `/dashboard`
> 템플릿·`commands/dashboard.md` 는 손대지 않는다. 이 성질은 수동 확인 M8 로 반드시 실검증한다.

> **보강됨(2026-08-13).** [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md)
> R1 은 이 모달이 좁은 iframe 안에서 대시보드 단독용 플로팅 UI 를 가리는 문제를 고치기 위해
> `commands/dashboard.md` 템플릿에 CSS 1줄 + JS 2줄을 더한다 — 위 표의 세 확인 항목(갱신
> 모드 판정·폴링 대상·주기)은 그대로이며, 라이브 갱신 메커니즘 자체는 여전히 한 줄도
> 바뀌지 않는다.

**알려진 한계**: 대시보드의 PiP(Document Picture-in-Picture) 기능은 iframe 안에서 권한 위임
없이는 동작하지 않을 수 있다. 모달은 "읽기"용이고 PiP 가 필요하면 원래대로 대시보드를 직접 열면
된다 — 지금 `allow` 속성을 추가하지 않는다(YAGNI, 실측 전).

### 결정 N5 — 네이티브 `<dialog>` + `showModal()`

| 안 | 얻는 것 | 잃는 것 |
|----|---------|---------|
| **A. `<dialog>` + `showModal()`** | **포커스 트랩·ESC 닫기·배경 inert·`::backdrop` 이 전부 무료.** 손으로 만들면 50줄 이상이고 정확히 만들기 어렵다 | 스타일링 시 `::backdrop` 관례를 알아야 한다 |
| B. `div` + `role="dialog"` 수제 | 완전한 통제 | 포커스 트랩·복귀·배경 inert 를 직접 구현 → 이 PRP 에서 가장 버그가 날 만한 코드가 된다 |

> **결정 N5 — 안 A.** 이 저장소는 앞서 `<details>/<summary>` 를 기각했지만(그때 얻는 것은 클릭
> 핸들러 한 줄뿐이었다) 여기서 얻는 것은 **포커스 트랩**이다. 크기가 다르다.

```html
<dialog id="dzh-dashboard-modal" class="modal" aria-labelledby="dzh-modal-title">
  <div class="modal-head">
    <span id="dzh-modal-title" class="modal-title"></span>
    <button id="dzh-modal-close" class="icon-btn" type="button"
            aria-label="닫기" data-tooltip="닫기 (Esc)">✕</button>
  </div>
  <iframe id="dzh-modal-frame" class="modal-frame" aria-label="프로젝트 진행 대시보드"></iframe>
</dialog>
```

- **`<dialog>` 는 `#dzh-app` 바깥의 정적 노드다** → 폴링이 파괴하지 않는다(불변식 H1″).
  갱신되는 것은 `#dzh-modal-title` 의 텍스트와 iframe 의 `src` 뿐이다.
- **`aria-label` 을 쓴다**(`title` 아님). T25-44 가 `title="` 를 금지하기 때문이다(GOTCHA 5).
- **닫을 때 `iframe.src` 를 반드시 비운다.** 안 그러면 숨은 iframe 이 5초 폴링을 영원히 계속한다.
  `dialog` 의 `close` 이벤트 하나에서 처리한다(ESC·닫기 버튼·배경 클릭 세 경로가 모두 여기로 모인다).
- **배경 클릭 닫기**: `dialog` 자신에게 온 클릭은 곧 backdrop 클릭이다
  (`if(event.target === modalEl) modalEl.close();`).
- 포커스 복귀는 `showModal()` 이 자동으로 처리한다(연 요소로 되돌아간다). 다만 그 요소는
  다음 렌더에서 사라질 수 있으므로, 사라졌으면 브라우저가 `<body>` 로 보낸다 — 허용한다.

### 결정 N6 — 클릭 대상과 기존 상호작용의 충돌 정리

카드 전체를 클릭 대상으로 삼되, **접근 가능한 조작 수단은 프로젝트명 버튼**으로 둔다.

| 상황 | 처리 |
|------|------|
| 드래그 핸들 클릭(R2) | `closest('.card-drag-handle')` 이면 **무시**. 클릭 영역과 드래그 영역이 애초에 다른 요소다 |
| 카드 안 텍스트를 드래그 선택한 뒤 mouseup | `window.getSelection().toString()` 이 비어 있지 않으면 **무시**(선택 후 의도치 않은 열기 방지) |
| `.sessions` 내부 스크롤 | 스크롤은 click 을 발생시키지 않는다 → 영향 없음 |
| 티어 배지·에이전트 칩(툴팁 트리거) 클릭 | 카드 클릭으로 처리된다(의도된 동작). 툴팁은 기존 `document click` 핸들러가 닫는다 |
| 키보드 | **`.project-name` 을 `<button class="project-name">` 으로 바꾼다.** Tab 도달·Enter/Space 동작·포커스 링을 공짜로 얻는다 |
| 티어 2·3 카드(`dashboard_key` 없음) | 클릭 핸들러가 조기 반환. `cursor:pointer` 를 주지 않고 `.project-name` 도 버튼이 아닌 `<span>` 으로 렌더한다(없는 기능을 있는 척하지 않는다) |

> **왜 카드 전체를 `role="button" tabindex="0"` 으로 만들지 않는가**: 그 안에 이미 포커스 가능한
> 요소(드래그 핸들)가 들어간다. 인터랙티브 요소의 중첩은 접근성 트리를 망가뜨리는 대표적
> 안티패턴이다. **마우스 편의(카드 전체) + 접근 가능한 실제 컨트롤(제목 버튼)** 로 나누는 것이
> 정석이다.

`renderProject` 는 카드에 `data-project-path` 와 `data-dashboard-key`(있을 때만)를 부여한다.
클릭 위임 핸들러는 `closest('[data-dashboard-key]')` 로 대상을 찾는다.

### 결정 N7 — `file://` 모드는 **모달을 열지 않고 사유를 알린다**

`file://` 부모 문서가 다른 디렉토리의 `file://` 문서를 iframe 으로 띄우는 동작은 브라우저마다
다르고(현대 Chrome 은 파일마다 opaque origin 으로 취급해 대개 빈 화면), **조용히 빈 모달이 뜨는
것이 가장 나쁜 결과**다.

- `isServed === false` 면 카드에 `data-dashboard-key` 를 넣지 않는다 → 클릭 대상이 아니다.
- 대신 카드에 `data-tooltip="허브 서버를 켜면(/hub server start) 카드에서 대시보드를 볼 수 있습니다"`
  를 준다. 아무 반응 없는 클릭(조용한 실패)을 만들지 않는다.

> 대안으로 검토한 "`file://` 에서는 새 탭으로 연다"는 기각했다 — 사용자가 명시적으로 새 탭을
> 원하지 않는다고 했고, 두 모드가 다른 상호작용을 갖는 것 자체가 학습 비용이다.

### 결정 N8 — 모달이 열린 채 프로젝트가 사라지면

모달은 계속 열려 있고, iframe 안의 대시보드가 자기 폴링에서 404 를 받아 **자기 방식대로**
"연결 끊김"을 표시한다(그 템플릿에 이미 있는 경로다). 허브는 개입하지 않는다 — 모달을 강제로
닫으면 사용자가 읽던 화면을 빼앗는 것이 된다.

### R3 인터페이스 (템플릿 JS)

```js
var MODAL_ELEMENT_ID = 'dzh-dashboard-modal';
var PROJECT_DASHBOARD_PATH_PREFIX = '/project/';
var PROJECT_DASHBOARD_PATH_SUFFIX = '/dashboard.html';

function projectDashboardUrl(dashboardKey: string): string
    /** 대시보드 키로 서버 경로를 만든다. 순수 함수. */

function openDashboardModal(dashboardKey: string, displayName: string): void
    /** 모달을 열고 iframe 에 프로젝트 대시보드를 싣는다. 제목은 textContent 로 넣는다. */

function closeDashboardModal(): void
    /** 모달을 닫고 **iframe.src 를 비운다** — 숨은 iframe 의 5초 폴링을 반드시 멈춘다. */
```

---

## 요구 R4 — `span.project-name` 툴팁 제거

### 결정 X1

`renderProject`(`hub_template.html:545`)의

```js
'<span class="project-name" data-tooltip="' + escapeHtml(project.display_name) + '">' + …
```

에서 `data-tooltip` 속성을 삭제한다. R3 에 의해 이 요소는 `<button class="project-name">`
(티어 1) 또는 `<span class="project-name">`(티어 2·3)이 된다.

**근거 3가지** (지우는 이유를 남긴다):

1. 툴팁 문구가 **보이는 텍스트와 같다.** 말줄임(`text-overflow:ellipsis`)이 걸렸을 때만 값이
   있었고, 그때조차 바로 아래 `.path` 가 전체 경로를 보여 준다 → 정보 손실 0.
2. `shouldDescribe()` 가 "접근성 이름 == 툴팁 문구"인 경우 `aria-describedby` 를 붙이지 않으므로
   **스크린리더 관점에서는 원래부터 없던 것과 같다** → 접근성 회귀 0.
3. R3 으로 이 요소가 **실제 조작 수단(열기 버튼)** 이 된다. 조작 수단 위의 잉여 툴팁은 진짜
   affordance 를 가린다.

회귀 검사(T25-58): 템플릿에 `project-name" data-tooltip` 문자열이 **없어야** 한다.

---

## 요구 R5 — `.top-actions` 를 `.head-row` 안으로 (오른쪽 정렬)

### 변경 전 / 후

```html
<!-- 변경 전 -->
<div class="top-actions">          ← position:fixed; top:16; right:16; z-index:30
  <button id="dzh-refresh" …>
  <button id="dzh-theme-toggle" …>
</div>
<div class="wrap">
  <div class="head-row"><h1>Claude Agents Manager</h1></div>   ← padding-right:150px

<!-- 변경 후 -->
<div class="wrap">
  <div class="head-row">
    <h1>Claude Agents Manager</h1>
    <div class="top-actions">      ← 문서 흐름. margin-left:auto 로 오른쪽 정렬
      <button id="dzh-refresh" …>
      <button id="dzh-theme-toggle" …>
    </div>
  </div>
```

```css
/* 변경 후 */
.head-row{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.top-actions{margin-left:auto;flex:0 0 auto;display:flex;align-items:center;gap:8px}
```

### 결정 E1 — `padding-right:150px` 은 **삭제**한다

그 값의 존재 이유가 "우상단 고정 클러스터 폭만큼 비워 둔다"였다(현행 71~73행 주석). 클러스터가
흐름 안으로 들어오면 그 예약은 의미가 없을 뿐 아니라 **h1 을 왼쪽으로 몰아 붙이는 잔재**가 된다.
주석도 함께 지운다(내 변경이 만든 고아를 치운다).

좁은 화면 겹침 재발 방지는 세 속성이 담당한다.

| 속성 | 막는 것 |
|------|---------|
| `.top-actions{flex:0 0 auto}` | 버튼이 찌그러져 원형이 타원이 되는 것 |
| `.head-row{flex-wrap:wrap}` | 극단적으로 좁을 때(≈360px 미만) 클러스터가 **아래 줄로 내려간다** — 겹치는 대신 줄바꿈 |
| `.top-actions{margin-left:auto}` | 제목 길이와 무관하게 항상 오른쪽 끝 |

### 결정 E2 — 스크롤 시 버튼이 **함께 올라간다**(수용)

요구가 "고정 해제"이므로 의도된 결과다. 대가와 판단:

| 잃는 것 | 판단 |
|---------|------|
| 스크롤 아래에서 새로고침 버튼이 안 보인다 | 60초 폴링·포커스 복귀 폴링이 있어 수동 새로고침은 예외적 행위다. `Home` 한 번이면 닿는다 |
| **연결 끊김 신호(`.refresh-btn.connection-lost`)가 스크롤 밖으로 나간다** | **실질적 정보 손실이다.** 리스크 R-5 로 등재하고, 실제로 문제가 되면 `.head-row{position:sticky;top:0}` + 배경색으로 되돌리는 것을 예비안으로 남긴다. 지금 만들지는 않는다(YAGNI) |

### 결정 E3 — `z-index:30` 제거의 영향

이전에는 클러스터(30)가 사용량 패널(20)보다 위였다. 이제 클러스터는 흐름 안에 있어 z 축 경쟁에서
빠진다. 두 요소가 겹치려면 뷰포트 높이가 대략 214px 미만이어야 하는데(구 PRP 결정 Z1 이 이미
계산한 값) 브라우저 창으로 사실상 불가능하다. **`.usage` 의 z-index·위치는 건드리지 않는다.**

### 툴팁·기존 코드에 대한 영향 (확인 결과)

| 항목 | 판정 | 근거 |
|------|------|------|
| 커스텀 툴팁 위치 계산 | **무영향** | `tooltipPosition()` 은 `getBoundingClientRect()`(뷰포트 기준) + `position:fixed` 로 계산한다. 트리거가 흐름 안에 있든 고정이든 같다 |
| 스크롤 시 툴팁 | **무영향** | `document.addEventListener('scroll', hideTooltip, {capture:true})` 가 이미 있다 |
| `renderConnectionStatus()` | **무영향** | `#dzh-refresh` 의 `data-tooltip`·`class` 를 갱신할 뿐 위치를 모른다 |
| `body.has-usage .wrap{padding-bottom:…}` | **무영향** | 하단 여백 로직은 헤더와 무관 |

---

## 요구 R6 — 테마 토글을 다크/라이트 2상태로

### 현재 동작

- 순환: `system → light → dark → system`(결정 T2).
- 저장: `light`/`dark` 만 저장하고, **`system` 은 키를 지워서** 표현한다.
- CSS 는 두 갈래: `@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){…} }` 와
  `:root[data-theme="dark"]{…}`.

### 결정 Y1 — 마이그레이션은 "**키 부재 → 시스템 선호로 1회 확정**" 하나뿐이다

**중요한 사실 확인**: 현행 코드는 `'system'` 이라는 문자열을 **저장한 적이 없다**
(`if(next === 'system') localStorage.removeItem(THEME_STORAGE_KEY)`). 따라서 저장소에 있을 수
있는 값은 `light`·`dark`·**부재** 셋뿐이고, 마이그레이션할 "레거시 문자열"이 존재하지 않는다.
그럼에도 읽기는 방어적으로 둔다 — `light`·`dark` 가 아닌 **모든** 값(하위 버전 롤백·수동 편집)을
"부재"와 동일하게 취급한다.

### 결정 Y2 — 확정은 `<head>` 인라인 스크립트에서 (FOUC 방지 유지)

```html
<script>
/* body 파싱 전에 실행돼 첫 페인트부터 확정 테마로 그린다(FOUC 방지).
   저장값이 없으면 시스템 선호를 **한 번만** 읽어 확정하고 그대로 굳힌다(결정 Y1·Y3) —
   이후로는 OS 테마가 바뀌어도 따라가지 않는다. localStorage 는 file:// 등에서 던질 수 있어 감싼다. */
try{
  var s = localStorage.getItem('dzh-theme');
  var t = (s === 'light' || s === 'dark') ? s
        : ((window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', t);
  if(s !== t) localStorage.setItem('dzh-theme', t);
}catch(e){}
</script>
```

- 이 스크립트가 끝나면 **`data-theme` 은 항상 존재**한다.
- `@media (prefers-color-scheme:dark)` 블록은 **지우지 않는다.** `localStorage` 가 던지는 환경
  (private 모드·`file://` 차단)에서는 `data-theme` 이 안 붙는데, 그때 이 블록이 유일한 안전망이다.
  선택자 `:root:not([data-theme="light"])` 는 그대로 옳다. (T25-28 도 `prefers-color-scheme` 와
  `data-theme` 의 존재를 요구한다.)
- `'dzh-theme'` 리터럴 수가 2 → 3 이 되지만 T25-28 의 검사는 `-lt 2`(2회 **이상**)라 통과한다(확인함).

### 결정 Y3 — 초기값 결정 규칙

| 상태 | 초기 테마 | 이후 |
|------|-----------|------|
| 저장값이 `light`/`dark` | 그 값 | 버튼으로만 바뀐다 |
| 저장값 없음/무효 | 시스템 선호를 **1회** 읽어 결정하고 곧바로 저장 | 이후 OS 테마 변경을 따라가지 않는다 |
| `localStorage` 접근 실패 | 시스템 선호(미디어 쿼리) | 버튼은 이번 로드 동안만 유효 |

"시스템을 따라가는 상태"가 사라지는 것이 요구다. 이 트레이드오프를 README 에 한 줄로 고지한다.

### 결정 Y4 — 아이콘 버튼으로 바꾸고 `.icon-btn` 을 공유한다

| 안 | 장단 | 판정 |
|----|------|------|
| A. 텍스트 알약 유지(`테마: 라이트`/`테마: 다크`) | 변경 최소 | 라벨 길이가 달라 클러스터 폭이 토글할 때마다 흔들린다(헤더 안으로 들어온 뒤에는 h1 과의 간격이 눈에 띄게 움직인다) |
| **B. 새로고침과 같은 32px 원형 아이콘 버튼** | 폭 고정(흔들림 0). 나란한 두 버튼이 **같은 모양**이 된다. 툴팁 기구가 이미 있어 라벨 손실이 없다 | `.refresh-btn` 과 공통 스타일을 어떻게 나눌지 결정해야 한다 |

**결정 — 안 B, 공통 규칙을 `.icon-btn` 으로 추출한다.**

```css
/* 32px 원형 아이콘 버튼 — 헤더 클러스터의 두 버튼과 모달 닫기 버튼이 공유한다.
   같은 줄에 나란히 서는 버튼들이 같은 크기·같은 테두리를 갖게 하려고 클래스를 하나로 묶었다.
   (추측성 추상화가 아니라, 지금 3곳이 실제로 같아야 한다는 요구에서 나온 것이다.) */
.icon-btn{width:32px;height:32px;padding:0;color:var(--muted);background:var(--surface);
          border:1px solid var(--line);border-radius:999px;cursor:pointer;
          display:inline-flex;align-items:center;justify-content:center;box-shadow:var(--shadow)}
.icon-btn:hover{color:var(--accent-ink);border-color:var(--accent)}
.icon-btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.refresh-btn.connection-lost{color:var(--attention);border-color:var(--attention);background:var(--attention-soft)}
.icon-btn svg{width:18px;height:18px}
```

`.refresh-btn` 은 `class="icon-btn refresh-btn"` 이 되고, 자기 고유 규칙은
`connection-lost` 모디파이어만 남는다. `.theme-toggle` 규칙은 삭제된다.

> 이것은 "혹시 몰라서" 만드는 추상화가 아니다. **지금 3개(새로고침·테마·모달 닫기)가 같은
> 모양이어야 한다**는 구체적 요구가 근거다. 그리고 `.refresh-btn` 에 없던 `:focus-visible` 이
> 이 통합으로 함께 생긴다 — 구 PRP 가 "별도 티켓 감"으로 남겨 둔 항목이 부수적으로 해소된다.

**버튼 스펙**

```html
<button id="dzh-theme-toggle" class="icon-btn theme-toggle" type="button"
        aria-label="다크 테마로 전환" data-tooltip="다크 테마로 전환">☾</button>
```

- **글리프와 라벨은 "전환될 대상"을 가리킨다.** 라이트일 때 `☾`/"다크 테마로 전환",
  다크일 때 `☀`/"라이트 테마로 전환". 버튼에 동작 라벨을 붙이는 것은 옆의 새로고침 버튼
  (`aria-label="새로고침"`)이 이미 쓰는 규약이다.
- `aria-pressed` 는 쓰지 않는다 — "눌림"은 테마에 자연스러운 은유가 아니고, 매번 바뀌는
  동작 라벨이 더 명확하다.
- `aria-label` 과 `data-tooltip` 이 같으므로 `shouldDescribe()` 가 `aria-describedby` 를 붙이지
  않는다 → **이중 낭독 없음**(기존 툴팁 설계가 이미 처리한다).

```js
var THEME_STORAGE_KEY = 'dzh-theme';
var THEME_CYCLE = ['light', 'dark'];
var THEME_GLYPH = {light:'☾', dark:'☀'};                       // 전환될 **대상**의 글리프
var THEME_ACTION_LABEL = {light:'다크 테마로 전환', dark:'라이트 테마로 전환'};

function resolveSystemTheme(): 'light'|'dark'
    /** 시스템 선호를 1회 읽는다. matchMedia 가 없으면 'light'. */

function currentTheme(): 'light'|'dark'
    /** 지금 유효한 테마. 저장값이 유효하지 않으면 시스템 선호로 확정한다. */

function applyTheme(theme: 'light'|'dark'): void
    /** data-theme 속성 · 글리프 · aria-label · data-tooltip 을 한꺼번에 맞춘다. */
```

---

## 변경 후 DOM 구조 (전체)

```html
<head>
  <script>…FOUC 방지 + 테마 1회 확정(결정 Y2)…</script>       ← 개정
</head>
<body>
<div class="wrap">
  <div class="head-row">                                       ← display:flex (R5)
    <h1>Claude Agents Manager</h1>
    <div class="top-actions">                                  ← ★흐름 안으로 이동 · margin-left:auto
      <button id="dzh-refresh" class="icon-btn refresh-btn" …>
      <button id="dzh-theme-toggle" class="icon-btn theme-toggle" …>   ← ★2상태 아이콘 (R6)
    </div>
  </div>
  <div id="dzh-app">…</div>          ← 폴링이 자식을 교체. **순서는 사용자 상태가 정한다**(R2)
</div>

<aside id="dzh-usage" class="usage" hidden>…</aside>           ← 무변경
<div id="dzh-tooltip" class="tooltip" role="tooltip"></div>    ← 무변경

<dialog id="dzh-dashboard-modal" class="modal"                 ← ★신규 · 정적 (R3)
        aria-labelledby="dzh-modal-title">
  <div class="modal-head">
    <span id="dzh-modal-title" class="modal-title"></span>     ← textContent 만 갱신
    <button id="dzh-modal-close" class="icon-btn" type="button" aria-label="닫기" …>✕</button>
  </div>
  <iframe id="dzh-modal-frame" class="modal-frame"             ← src 만 갱신. title 금지→aria-label
          aria-label="프로젝트 진행 대시보드"></iframe>
</dialog>
<div id="dzh-live" class="sr-only" aria-live="polite"></div>   ← ★신규 · 정적 (R2 낭독)
                                                                ← 제거됨(R7, hub-first-entry-and-ui-signals.md)

<script type="application/json" id="dzh-data">{}</script>      ← 무변경(치환 마커)
```

### 카드 내부 (변경 후)

```html
<div class="card" data-project-path="…" data-dashboard-key="3f9a…">   ← key 는 티어1 + 서버모드일 때만
  <div class="project-head">
    <button class="card-drag-handle" type="button" draggable="true"
            aria-label="위치 이동: …" data-tooltip="드래그하거나 ←/→ 키로 순서 변경">≡</button>   ← ★R2
    <button class="project-name">…</button>            ← ★R3(티어1) · data-tooltip 제거(R4)
    <span class="badge tier" data-tooltip="…">…</span> ← 무변경
    …
```

---

## 불변식 H1′ → **H1″** 개정안

현행 `hub_template.html` 상단 주석(12~33행)의 불변식 문단을 아래로 교체한다.

> **불변식 H1″.** 허브의 폴링·틱이 **내용을 갱신하는** 대상은 다음뿐이다.
> `#dzh-app`(자식 전체 교체) · `#dzh-usage-body`(innerHTML) · `#dzh-usage-summary`(textContent) ·
> `#dzh-refresh` 의 `data-tooltip`·`class` **속성**.
>
> 다음 노드는 **정적**이며 폴링이 절대 교체하지 않는다: `#dzh-usage`, `#dzh-usage-toggle`,
> `#dzh-theme-toggle`, `#dzh-tooltip`, `#dzh-dashboard-modal`(과 그 자식 전부), `#dzh-live`
> (`#dzh-live` 는 **제거됨** — R7, 정본: [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md) 불변식 H1‴).
> 이들의 갱신은 **속성·textContent 단위**로만 한다.
>
> 여기에 이번 개정으로 두 조항이 더해진다.
>
> - **순서는 데이터가 아니라 사용자 상태다.** `#dzh-app` 자식의 **배치 순서**는 스냅샷이 아니라
>   `storedProjectOrder`(모듈 스코프 + `localStorage['dzh-project-order']`)가 정한다. 서버의
>   활동순 정렬은 **아직 저장 순서에 없는 신규 프로젝트끼리의 상대 순서**를 정할 때만 쓰인다.
> - **드래그 중에는 다시 그리지 않는다.** `isReordering` 이 참이면 `render()` 는 `#dzh-app` 을
>   건드리지 않고 즉시 반환한다. 재렌더가 드래그 중인 노드를 파괴하면 드롭이 취소되기 때문이다.
>
> **원칙은 그대로다: 사용자 상태(포커스·접힘·선택·순서·열린 모달)를 가진 것은 재렌더 대상 밖에 둔다.**

구 문서에 대체 표기를 덧붙인다(내용은 지우지 않는다 — 설계 이력 보존).

| 파일 | 추가할 표기 |
|------|-------------|
| `docs/prps/hub-usage-collapse-and-grid.md` 의 「불변식 M2 의 개정 — H1 → H1′」 절 | `> **재개정(H1″).** 정적 노드 목록에 모달·라이브 영역이 추가되고, "#dzh-app 의 자식 **순서**는 사용자 상태" 조항과 "드래그 중 재렌더 금지" 조항이 더해졌다. 정본은 hub_template.html 상단 주석 블록 및 [hub-card-interactions-and-usage.md](./hub-card-interactions-and-usage.md).` |
| `docs/prps/hub-card-cleanup-and-usage-source.md` 의 결정 P1 근처 | `> **보강.** P1(퍼센트의 유일한 출처 = statusLine 캡처)은 **소비 계약**으로는 유효하다. 생산자는 [hub-card-interactions-and-usage.md](./hub-card-interactions-and-usage.md) 의 결정 A2 로 하나 더 늘어난다(파일 포맷·타입은 불변).` |

---

## 데이터 모델 요약 (모듈 간 계약)

| 타입 | 위치 | 변화 |
|------|------|------|
| `HubSnapshot` | `hub_model.py` | **필드 추가 없음** — `projects` 안의 `ProjectView` 만 바뀐다 |
| `ProjectView` | `hub_model.py` | `dashboard_key: str \| None = None` **추가** |
| `HubConfig` | `hub_model.py` | `usage_api_enabled: bool = False`, `usage_api_poll_interval_seconds: int = 300` **추가** |
| `UsageApiPollState` | `hub_model.py` | **신규**(frozen) — 수집 루프 지역 변수 |
| `RateLimitCapture` | `hub_usage.py` | **무변경** ← 이것이 R1 설계의 핵심 |
| `UsageSample`·`RateLimitResets` | `hub_usage.py` | **무변경** |
| `Tier1Snapshot`·`StepView` | `hub_parse.py` | **무변경** |
| `ServerRecord`·`ServerStatus` | `hub_model.py` | **무변경** |

### `#dzh-data` JSON 계약의 변화

```diff
 projects[]: {
   display_name, path, tier, state, last_activity_at_ms,
-  sessions[], tier1, note
+  sessions[], tier1, note, dashboard_key
 }
```

클라이언트는 `project.dashboard_key` 가 truthy 일 때만 카드를 클릭 대상으로 만든다.
**추가 필드 하나 외에 계약 변경이 없으므로 T25-56 은 통과한다.**

### 서버 경로 계약

| 경로 | 응답 | 비고 |
|------|------|------|
| `/` · `/hub.html` | 200 `hub.html` | **무변경**(`ALLOWED_REQUEST_PATHS` 유지 → T25-15 통과) |
| `/project/<[0-9a-f]{16}>/dashboard.html` | 200 그 프로젝트의 `dashboard.html` / 404 | **신규**. 레지스트리 조회로만 해석 |
| 그 외 전부 | 404 | **무변경** |
| `GET` 외 메서드 | 501 (핸들러 미정의) | **무변경** |

### 파일 계약

| 파일 | 변화 |
|------|------|
| `~/.claude/hub/rate_limits.json` | **포맷 무변경**. 생산자가 1 → 2 개로 늘어난다 |
| `~/.claude/hub/last_usage_api_error.json` | **신규** — `last_collect_error.json` 과 같은 모양 |
| `~/.claude/hub/config.json` | 필드 2개 추가(둘 다 선택) |
| `localStorage['dzh-project-order']` | **신규** — 경로 문자열 JSON 배열 |
| `localStorage['dzh-theme']` | 의미 변화: "부재 = 시스템" → **부재 상태가 존재하지 않는다**(첫 로드에 확정) |

---

## 테스트 계획

검증 정본: `bash tests/run.sh`(통합 24건) / `python3 -m unittest discover -s tests/hub -t .`(현재 251건).
이 저장소에는 별도 linter·type checker·JS 테스트 러너가 없다. **JS 테스트 러너를 도입하지 않는다**
— "새 외부 의존성 금지"에 정면으로 걸린다. 템플릿은 grep 회귀 + 수동 확인 두 축으로 검증한다
(직전 PRP 들과 동일한 방침). 순수 JS 함수(`orderedProjectPaths`·`moveProjectPath`·
`projectDashboardUrl`)는 **테스트 불가여도 순수하게 뽑는다** — 리뷰 가능성이 곧 이 파일의 방어선이다.

### 파이썬 단위 테스트 (신규)

**`tests/hub/test_hub_model.py` 추가**

| # | 케이스 | 기대 |
|---|--------|------|
| U1 | `project_dashboard_key` 가 같은 경로에 대해 항상 같은 값 | 결정적 |
| U2 | 다른 두 경로가 다른 키 (`/a.b` vs `/a/b` 포함 — 구 인코딩의 충돌 사례) | 서로 다름 |
| U3 | 키가 `^[0-9a-f]{16}$` 을 만족 | 정규식 통과 |
| U4 | `build_dashboard_registry` 가 티어 1 만 담는다 | 티어 2·3 프로젝트는 키가 없다 |
| U5 | `build_dashboard_registry` 의 값이 `<경로>/.claude/dashboard.html` | 경로 정확 |
| U6 | `compose_project_views` 가 티어 1 에만 `dashboard_key` 를 채운다 | 티어 2·3 은 `None` |
| U7 | `should_attempt_usage_api_poll` — 첫 시도(`last_attempt_at_ms=None`) | `True` |
| U8 | 주기 미도달 / 정확히 도달 / 초과 | `False` / `True` / `True` |
| U9 | 연속 실패 1·2·3회의 지연이 2배씩 늘고 상한에서 멈춘다 | 5·10·20…60분 |
| U10 | 성공하면 `consecutive_failures` 가 0 으로 복귀 | 백오프 해제 |
| U11 | `http_rate_limited` 는 곧바로 상한 배수 | 429 특례 |
| U12 | `next_usage_api_poll_state` 가 **새 객체**를 돌려준다(원본 불변) | `is not` |
| U13 | `snapshot_content_key` 가 `dashboard_key` 추가 후에도 결정적 | 같은 입력 → 같은 키 |

**`tests/hub/test_hub_server.py` 추가**

| # | 케이스 | 기대 |
|---|--------|------|
| U14 | `PROJECT_DASHBOARD_PATH_PATTERN` 이 정상 키를 매치 | 매치 |
| U15 | **traversal 시도 전부 불매치**: `/project/../../etc/passwd`, `/project/%2e%2e/dashboard.html`, `/project/ABCDEF0123456789/dashboard.html`(대문자), `/project/3f9a/dashboard.html`(짧음), `/project/3f9a…/index.html` | 전부 불매치 |
| U16 | 레지스트리에 없는 정상 형식 키 → 404 | 404 |
| U17 | 레지스트리에는 있으나 **파일이 삭제된** 키 → 404 | 404(TOCTOU) |
| U18 | `bin/hub_server.py`·`events/…`·`config.json` 을 노리는 경로 전부 404 | **S5** |
| U19 | `_run_collect_cycle` 이 `(content_key, registry)` 튜플을 돌려준다 | 기존 3건 갱신 |
| U20 | 수집 실패 사이클은 `(None, None)` — 레지스트리를 **비우지 않는다**(직전 것 유지) | 모달이 살아 있다 |

**`tests/hub/test_hub_usage.py` 추가** (스파이크 SP3 확정 후)

| # | 케이스 | 기대 |
|---|--------|------|
| U21 | 정상 응답 → `RateLimitCapture` | 4값 채워짐 |
| U22 | 깨진 JSON / 최상위가 배열 / 필드 전부 없음 | `None` |
| U23 | 퍼센트가 문자열·`bool`·범위 밖 | 그 필드만 `None` |
| U24 | 리셋이 지평선 밖(단위 혼동) | 그 창만 `None` |
| U25 | 어떤 입력에도 **예외를 던지지 않는다** | `None` 반환 |

**`tests/hub/test_hub_usage_fetch.py` (신규 · 네트워크 전부 mock)**

| # | 케이스 | 기대 |
|---|--------|------|
| U26 | `security` 명령이 없다(`FileNotFoundError`) | `credential_unavailable` |
| U27 | 명령이 비영(non-zero) 종료 | `credential_unavailable` |
| U28 | 출력이 JSON 이 아니다 / 토큰 필드 없음 | `credential_unparsable` |
| U29 | HTTP 401·403 / 429 / 500 | `http_unauthorized` / `http_rate_limited` / `http_error` |
| U30 | 타임아웃·`URLError` | `network_error` |
| U31 | 200 인데 파싱 실패 | `schema_mismatch` |
| U32 | **어떤 실패 경로에서도 반환 사유에 토큰 문자열이 없다** | 불변식 A-SEC |
| U33 | `subprocess.run` 이 **리스트 인자 + `shell` 미지정**으로 호출된다 | mock 인자 검사 |

### `tests/run.sh` 추가 (T25-57 ~ T25-64)

`test_hub_docs_and_constants()` 안, 기존 T25-56 블록 뒤에 넣는다.
**함수 상단 `test_desc` 를 `"허브 문서·상수 정합성 (T25-1~T25-64)"` 로 갱신할 것.**

| # | 검사 대상 | 토큰(정확히 이 문자열로 구현할 것) |
|---|-----------|-----------------------------------|
| T25-57 | **R3 서버 라우팅 회귀** | `hub_server.py` 에 `PROJECT_DASHBOARD_PATH_PATTERN`·`[0-9a-f]{16}` 존재, `ALLOWED_REQUEST_PATHS` **여전히 존재**(T25-15 보강), `os.path.join`·`/ self.path`·`+ self.path` 부재(요청 문자열로 경로를 만들지 않는다) |
| T25-58 | **R4 회귀** | `hub_template.html` 에 `project-name" data-tooltip` **부재** |
| T25-59 | **R5 회귀** | `padding-right:150px` **부재**, `position:fixed;top:16px;right:16px` **부재**, `.head-row{display:flex` 존재, `.top-actions{margin-left:auto` 존재 |
| T25-60 | **R1 보안 불변식** | `hub_usage_fetch.py` 에 `shell=True`·`print(`·`str(error)` **부재**, `FAILURE_REASON_MESSAGES` 존재 |
| T25-61 | **R1 구조** | `hub_usage.py` 에 `parse_usage_api_response` 존재(그리고 T25-10 의 순수성 검사를 계속 통과), `hub_model.py` 에 `should_attempt_usage_api_poll`·`UsageApiPollState` 존재, `hub_collect.py` 에 `usage_api_enabled` 타입 등록 존재 |
| T25-62 | **R2 회귀** | `hub_template.html` 에 `'dzh-project-order'`·`orderedProjectPaths`·`isReordering`·`card-drag-handle` 존재, 구 함수 `stableSortedProjects` **부재** |
| T25-63 | **R3·R6 마크업 회귀** | `<dialog id="dzh-dashboard-modal"`·`id="dzh-modal-frame"`·`.icon-btn` 존재. `THEME_CYCLE = ['light', 'dark']` 존재, `'system'` **부재**(3상태 잔재) |
| T25-64 | **문서 정합** | `hub/README.md` 에 `카드 순서`·`모달`·`usage_api_enabled` 존재, `commands/hub.md` 에 `usage_api_last_failure` 존재 |

### 기존 자동 검사에 대한 영향 (전수 확인)

| 검사 | 판정 | 근거 |
|------|------|------|
| T25-1 (`HUB_FILE_COUNT`) | **수정 필요** | `hub_usage_fetch.py` 1개 추가 → 11 → **12**. 검사가 실제 파일 수와 자동 대조하므로 `hub/install.sh` 만 고치면 통과 |
| T25-2 (설치 파일 수) | 위와 함께 통과 | 같은 `declared_count` 를 쓴다 |
| T25-10 (순수 레이어) | 통과 | 새 순수 함수는 `hashlib`·`json` 만 쓴다. `open(`·`Path(`·`os.` 없음. **I/O 는 `hub_usage_fetch.py`(검사 대상 아님)에 있다** |
| T25-11 (`escapeHtml(run.agent_type)`) | 통과 | 세션 렌더 무변경 |
| T25-14 (serve 잔재) | 통과 | 새 모듈에 `start_serving`·`pkill` 등 없음 |
| T25-15 (화이트리스트) | 통과 | `ALLOWED_REQUEST_PATHS` 를 **삭제하지 않고** 라우트를 하나 더 얹는다. `SimpleHTTPRequestHandler` 도입 없음 |
| T25-28 (테마) | 통과 | `prefers-color-scheme`·`data-theme` 유지. `'dzh-theme'` 리터럴 2 → 3(검사는 `-lt 2`) |
| T25-29 (구 팔레트 부재) | 통과 | 새 색 리터럴 0개 |
| T25-41 (`POLL_INTERVAL_MS = 60000` 등) | 통과 | 폴링 주기·사용량 문구 무변경 |
| T25-44 (**`title="` 금지**) | **주의** | 모달 iframe·닫기 버튼에 `title` 을 쓰면 즉시 실패. `aria-label` 을 쓴다(GOTCHA 5) |
| T25-50 (그리드 3열) | 통과 | 그리드 CSS 무변경 |
| T25-51·52·53 (세션·칩·상수 순서) | 통과 | 해당 코드 무변경 |
| T25-56 (`#dzh-data` 계약) | 통과 | `HubSnapshot.usage`·`rate_limit_resets` 필드 정의가 그대로다 |
| `tests/hub/test_hub_collect.py` 등 나머지 | 통과 | `ProjectView.dashboard_key` 는 **기본값이 있어** 기존 생성자 호출이 깨지지 않는다 |

### 수동 확인 목록 (브라우저 실검증 — 자동화 불가)

**A. 카드 순서 (R2)**
- [ ] M1 — 핸들을 잡고 카드를 다른 자리에 떨어뜨리면 그 자리로 간다
- [ ] M2 — 드래그 도중 60초 폴링이 발생해도 드래그가 취소되지 않는다(결정 O6)
- [ ] M3 — 순서 변경 후 2분(틱 4회·폴링 2회) 방치 → 순서 유지
- [ ] M4 — 새로고침(`http://localhost:8794/hub.html`) → 순서 유지
- [ ] M5 — 새 프로젝트에서 세션을 하나 만들어 목록에 등장시킨다 → **맨 앞**에 붙는다
- [ ] M6 — 핸들에 Tab 포커스 → `←`/`→` 로 이동, 포커스가 **이동한 카드에 남아 있고**,
      VoiceOver 가 `"{이름} — 3 / 9 번째"` 를 낭독한다
- [ ] M7 — `file://` 로 열어 드래그 + 콘솔 에러 없음(저장 실패는 정상)

**B. 대시보드 모달 (R3)**
- [ ] M8 — **핵심**: 티어 1 카드를 눌러 모달을 연 뒤, 그 프로젝트에서 `/dashboard log` 를 실행 →
      **모달 안 대시보드가 5초 안에 스스로 갱신된다**(결정 N4 의 실증)
- [ ] M9 — ESC / 닫기 버튼 / 배경 클릭 세 경로 모두 닫히고, 닫은 뒤 **DevTools Network 에
      `/project/…` 요청이 더 이상 안 뜬다**(iframe.src 비우기 확인)
- [ ] M10 — 티어 2·3 카드는 클릭해도 아무 일이 없고 커서가 pointer 가 아니다
- [ ] M10b — 드래그 핸들을 클릭해도 모달이 열리지 않는다. 카드 안 텍스트를 선택한 뒤
      mouseup 해도 열리지 않는다
- [ ] M11 — 모달 열림 상태에서 Tab 이 모달 밖으로 나가지 않는다(포커스 트랩). 닫으면
      포커스가 연 요소로 돌아온다
- [ ] M11b — `file://` 로 열면 카드가 클릭 대상이 아니고, hover 시 안내 툴팁이 뜬다
- [ ] M11c — `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8794/project/../../etc/passwd'` → **404**

**C. 헤더·테마 (R4·R5·R6)**
- [ ] M12 — 새로고침·테마 버튼이 `h1` 과 같은 행 오른쪽 끝. 뷰포트 1440/768/**360**px 에서
      겹침 없음(360px 에서는 아래 줄로 내려가도 된다)
- [ ] M13 — 스크롤해도 버튼이 헤더와 함께 올라간다(고정 해제 확인)
- [ ] M13b — 프로젝트명에 마우스를 올려도 툴팁이 뜨지 않는다. 티어 배지·에이전트 칩·
      새로고침 툴팁은 **그대로 뜬다**
- [ ] M14 — 테마 버튼이 라이트↔다크만 오간다. 저장소를 비우고(`localStorage.clear()`)
      새로고침하면 OS 설정과 같은 테마로 열리고, 그 뒤 **OS 테마를 바꿔도 따라가지 않는다**
- [ ] M14b — 라이트/다크 양쪽에서 아이콘 버튼 2개·모달·드래그 핸들의 대비가 충분하다
- [ ] M15 — 세 버튼(새로고침·테마·모달 닫기)이 **같은 크기·같은 테두리**이고 셋 다
      Tab 포커스 링이 보인다

**D. 사용량 (R1)**
- [ ] M16 — `usage_api_enabled:true` 로 서버 재기동 → **터미널 세션을 한 번도 돌리지 않고**
      5분 안에 패널이 뜬다
- [ ] M17 — `usage_api_enabled:false`(기본) → 네트워크 요청이 **0건**(DevTools·`server.log` 확인)
- [ ] M18 — `show_usage_panel:false` → API 폴링도 멈춘다(GOTCHA 2)
- [ ] M19 — 네트워크를 끊고 방치 → 화면에 경고가 뜨지 않고,
      `/hub status` 의 `usage_api_last_failure.reason` 이 `network_error`
- [ ] M20 — `server.log` 와 `last_usage_api_error.json` 에 **토큰 문자열이 없다**(불변식 A-SEC)

---

## 구현 마일스톤 (단계별 검증 기준)

각 마일스톤은 **그 자체로 커밋 가능하고 독립적으로 되돌릴 수 있다.**

| # | 범위 | 요구 | 의존 | 검증 |
|---|------|------|------|------|
| **1** | 헤더 정리 + 테마 2상태 + 프로젝트명 툴팁 제거. `.icon-btn` 추출. **Python 무변경** | R4·R5·R6 | 없음 | T25-58·59·63 일부, 수동 M12~M15 |
| **2** | 서버 라우트 + `dashboard_key` + 모달. Python(model·server) + 템플릿 | R3 | 없음 | U1~U6·U13~U20, T25-57·63, 수동 M8~M11c |
| **3** | 카드 순서(저장·신규 앞·드래그·키보드). **템플릿만** | R2 | 2 (핸들이 클릭 대상에서 빠지는 처리를 얹는다) | T25-62, 수동 M1~M7 |
| **4-0** | **R1 스파이크(SP1~SP3)** — 코드 0줄. 결과를 이 문서에 기록 | R1 | 없음 | 「스파이크 결과」 절이 채워진다 |
| **4** | R1 구현: `hub_usage_fetch.py` + 파서 + 폴링 게이트 + config + status 필드 | R1 | 4-0 **통과 시에만** | U7~U12·U21~U33, T25-60·61, 수동 M16~M20 |
| **5** | 문서: `hub/README.md`·`commands/hub.md`·구 PRP 대체 표기 2곳·`tests/run.sh` T25-64·`test_desc` | 전부 | 1~4 | `bash tests/run.sh` 전체 통과 |

**권장 순서 근거**: 1은 위험이 가장 낮고 눈에 보이는 성과가 즉시 나온다. 2는 **공개 계약을
바꾸는 유일한 단계**라 검수 시간을 가장 많이 배정한다. 3은 순수 클라이언트라 사용 후 조정이
자유롭다. 4는 **스파이크 결과에 따라 통째로 취소될 수 있으므로 맨 뒤**에 둔다 — 4가 취소돼도
1~3·5는 아무 영향을 받지 않는다.

---

## 스파이크 결과 (마일스톤 4-0 수행 후 채운다)

| # | 확인 항목 | 결과 | 기록 |
|---|-----------|------|------|
| SP1 | Keychain 항목 `Claude Code-credentials` 존재·읽기 | **통과** (2026-08-13) | `security find-generic-password -s "Claude Code-credentials" -w` 성공. 시크릿 길이 4026 |
| SP2 | accessToken 필드 경로 | **통과** (2026-08-13) | JSON 파싱됨. 토큰 경로 = **`claudeAiOauth.accessToken`**(str len 108). 인접 필드: `claudeAiOauth.refreshToken`·`expiresAt`(int)·`rateLimitTier`(str)·`subscriptionType`(str)·`scopes`(list len 5)·최상위 `organizationUuid` |
| SP3 | usage 엔드포인트 URL·상태코드·응답 키 구조 | **사용자 결정으로 생략** (2026-08-13) | 세션 권한 정책이 사전 호출을 차단했고, 사용자가 "터미널 1회 실행" 대신 **생략 + 첫 폴링이 스파이크를 겸하는 방식**을 선택·승인했다. 아래 「개정 — SP3 생략」 참조 |
| 판정 | 안 A 진행 / 안 D 낙착 | **안 A 진행 (개정된 조건)** | SP1·SP2 로 자격증명 경로 확정. 응답 스키마는 커뮤니티에 알려진 형태로 우선 구현하고, 불일치 시 실패 기록의 키 구조로 자기 진단한다 |

> **토큰 값 자체는 이 표에 절대 적지 않는다.** 키 이름과 구조만 기록한다.

### 개정 (2026-08-13) — SP3 생략, 첫 폴링이 스파이크를 겸한다 (사용자 승인)

결정 A1 의 "스파이크 통과가 구현의 전제조건" 조항을 다음으로 개정한다. 사용자가 "구현 전
터미널 1회 실행" 대신 이 방식을 명시적으로 선택했다.

1. **`parse_usage_api_response` 는 커뮤니티 사용량 도구들이 쓰는 알려진 스키마를 1차 대응표로
   구현한다**: 최상위 `five_hour`·`seven_day` 객체, 각각 `utilization`(0~100 숫자) +
   `resets_at`(ISO 8601 문자열). 값 검증은 기존 `_valid_*` 헬퍼 재사용, 계약 불일치는 예외가
   아니라 `None`(결정 A7 그대로).
2. **schema_mismatch 실패 기록에 응답의 키 구조를 남긴다**: `last_usage_api_error.json` 에
   선택 필드 `response_keys`(키 경로 + 타입 목록)를 추가한다. **값은 절대 기록하지 않는다** —
   불변식 A-SEC 유지. 본문이 JSON 이 아니면 Content-Type 과 길이만 남긴다.
3. **배포 후 첫 폴링이 곧 SP3 다**: 성공하면 패널이 뜨고 끝. `schema_mismatch` 면 오케스트레이터가
   `/hub status` 의 `response_keys` 를 읽어 대응표를 실제 스키마로 수정한다 — "추측 위의 코드"
   리스크가 "1회 관측 후 수정"으로 축소되며, 그동안 화면은 기존 강등 규칙(패널 숨김)을 따른다.

### (참고) 생략된 수동 SP3 절차 — 원래 안

아래 스크립트는 **토큰을 프로세스 지역 변수로만 다루고 출력·파일 어디에도 남기지 않는다**(불변식 A-SEC).
엔드포인트 URL 후보와 응답 상태코드·키 구조만 화면에 낸다. 터미널에서 실행하고 그 출력을
`SP3` 행에 붙여 넣으면 `parse_usage_api_response` 의 필드 대응표가 확정된다.

```bash
python3 - <<'PY'
import json, subprocess, urllib.request, urllib.error
raw = subprocess.run(["security","find-generic-password","-s","Claude Code-credentials","-w"],
                     capture_output=True, text=True, timeout=5).stdout.strip()
token = json.loads(raw)["claudeAiOauth"]["accessToken"]
def structure(node, path="", out=None):
    if out is None: out=[]
    if isinstance(node, dict):
        for k in sorted(node): structure(node[k], path+"/"+k, out)
    elif isinstance(node, list):
        out.append(path+" [list len=%d]"%len(node))
        if node: structure(node[0], path+"/0", out)
    else: out.append(path+" <"+type(node).__name__+">")
    return out
for url in ("https://api.anthropic.com/api/oauth/usage",
            "https://api.anthropic.com/api/oauth/profile"):
    for hdr in ({"Authorization":"Bearer "+token,"anthropic-beta":"oauth-2025-04-20"},
                {"Authorization":"Bearer "+token}):
        beta = "beta" if "anthropic-beta" in hdr else "nobeta"
        req = urllib.request.Request(url, headers=hdr, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                body, status = r.read().decode("utf-8","replace"), r.status
        except urllib.error.HTTPError as e:
            body, status = e.read().decode("utf-8","replace"), e.code
        except Exception as e:
            print(url, beta, "EXC", type(e).__name__); continue
        print("="*60); print(url, beta, "->", status)
        try:
            for line in structure(json.loads(body)): print("  ", line)
        except Exception: print("  non-json:", body[:200])
PY
```

---

## 리스크와 완화책

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| R-1 | **비공개 usage API 가 예고 없이 바뀌거나 막힌다** | 패널이 다시 사라진다 | 결정 A7 의 강등(기존 캡처 유지 + `schema_mismatch` 기록). `usage_api_enabled:false` 한 줄로 즉시 무력화. **스파이크로 도입 전에 실재를 확인**하고, 실패 시 안 D 로 낙착 |
| R-2 | **자격증명 노출** | 심각 | 불변식 A-SEC + 고정 어휘 실패 사유 + T25-60 grep + 단위 테스트 U32. 파일 하나로 격리해 검수 범위를 최소화 |
| R-3 | **서버 노출 표면 확대** | 로컬의 다른 프로세스가 프로젝트 대시보드를 읽을 수 있다 | 이미 `hub.html` 에 프롬프트 발췌가 인라인돼 있어 **노출 등급이 올라가지 않는다**(대시보드는 같은 사용자의 로컬 파일이다). 프라이버시 고지에 한 줄 추가. traversal 은 결정 N3 으로 구조적 차단 + U15·U18 로 고정 |
| R-4 | **드래그 중 재렌더로 드롭 취소** | 순서 변경이 가끔 씹힌다 | 결정 O6 의 `isReordering` 게이트. `dragend` 가 모든 경로에서 발화하므로 플래그가 영구히 걸리지 않는다. 수동 M2 |
| R-5 | **연결 끊김 신호가 스크롤 밖으로 나간다**(R5 의 대가) | 서버가 죽은 것을 늦게 안다 | 결정 E2 에 명시. 문제가 되면 `.head-row{position:sticky;top:0}` + 배경으로 되돌린다(예비안, 지금 만들지 않음) |
| R-6 | **모달을 닫고도 iframe 이 폴링을 계속한다** | 서버에 5초마다 유령 요청 | `close` 이벤트에서 `src` 를 비운다. 수동 M9 가 Network 탭으로 직접 확인 |
| R-7 | **HTML5 DnD 가 터치에서 동작하지 않는다** | 아이패드에서 순서 변경 불가 | 키보드 경로(`←`/`→`)가 대체 수단이다. 허브의 주 사용 환경은 데스크톱 브라우저다(수용) |
| R-8 | **`localStorage` 오리진 분리**(`file://` ↔ `http://`) | 서버 on/off 를 오가면 순서·테마가 달라 보인다 | 테마·접힘이 이미 지고 있는 **기존 한계**. 문서화하고 수용 |
| R-9 | **`.icon-btn` 추출이 새로고침 버튼을 건드린다** | 기존 버튼 회귀 | 이동하는 선언이 전부 동일값이고 `connection-lost` 모디파이어는 그대로 남는다. 수동 M15 가 세 버튼을 나란히 비교 |
| R-10 | **`dashboard_key` 추가로 `hub.html` 재작성 폭증** | 디스크 I/O 증가 | 키는 경로에서 결정적으로 파생돼 경로가 안 바뀌면 값도 안 바뀐다 → `snapshot_content_key` 안정. U13 이 고정 |
| R-11 | **티어 1 → 2 강등 시 카드가 갑자기 클릭 불가가 된다** | 사용자 혼란 | 배지 문구도 함께 바뀌므로 화면상 원인이 드러난다(결정 N2 의 "클릭 가능 ⇔ 티어 1" 규칙이 주는 이득) |

---

## 검토했으나 채택하지 않은 대안

1. **순서를 서버 파일에 저장(쓰기 엔드포인트 추가).** 오리진·브라우저 분리 문제가 한 번에
   해결된다. 그러나 읽기 전용 화이트리스트라는 서버 설계 정본을 깨야 하고, 루프백 포트에 쓰기가
   열리면 로컬의 임의 프로세스가 사용자 설정을 바꿀 수 있다 → 기각(결정 O1).
2. **카드 전체를 `draggable="true"` 로.** 핸들이 없어 깔끔하지만 R3(카드 전체 클릭)과 정면
   충돌해 "몇 px 움직였나"로 의도를 추정하는 코드가 필요해진다 → 기각(결정 O5).
3. **모달을 `div` + `role="dialog"` 로 직접 구현.** 완전한 통제를 얻지만 포커스 트랩·배경
   inert·포커스 복귀를 손으로 만들어야 하고, 그 코드가 이 PRP 에서 가장 버그가 날 곳이 된다
   → 기각(결정 N5, 네이티브 `<dialog>` 채택).
4. **키를 `encode_project_dir_name` 재사용으로.** 새 함수가 안 생긴다. 그러나 `/`·`.` 이 모두
   `-` 가 되는 단방향 변환이라 서로 다른 경로가 같은 키가 될 수 있고, 충돌하면 **다른
   프로젝트의 대시보드를 조용히 보여준다** → 기각(결정 N1).
5. **모달 대신 카드 안에 대시보드 요약을 더 그린다.** 서버 변경이 없다. 그러나 티어 1 파서가
   읽는 것은 제목·진행률·단계뿐이고 그 이상은 이미 카드에 다 있다. "대시보드를 본다"는 요구는
   **원본 화면**을 보는 것이다 → 기각.
6. **주기적 헤드리스 CLI 호출로 statusLine 발화 유도.** 공식 경로만 쓴다는 장점이 있으나,
   비대화형 모드에서 statusLine 이 발화한다는 근거가 없고(가정 위의 설계), 발화하더라도
   **한도를 재려고 한도를 태운다** → 기각(R1 선택지 B).
7. **데스크톱 앱 내부 데이터 읽기.** 결정 P1 이 이미 같은 방식으로 한 번 무너졌다. 위치·포맷
   모두 미확인이고 앱 업데이트마다 깨진다 → 기각(R1 선택지 C).
8. **테마 토글을 텍스트 알약으로 유지.** 변경이 최소이지만 라벨 길이 차이로 헤더 안에서 클러스터
   폭이 토글할 때마다 흔들린다 → 기각(결정 Y4).
9. **`.head-row` 를 `position:sticky` 로.** 스크롤해도 버튼이 남는다. 그러나 요구가 "고정 해제"
   이고, sticky 는 배경·z-index 를 새로 정해야 해서 카드가 반투명 헤더 아래로 미끄러지는 문제를
   또 만든다 → 기각(단 R-5 의 예비안으로 남긴다).
10. **JS 테스트 러너(node/jest) 도입.** `orderedProjectPaths`·`moveProjectPath` 를 진짜로
    단위 테스트할 수 있다. "새 외부 의존성 금지 · 빌드 단계 없음" 전제와 정면 충돌 → 기각.
    순수 함수로 뽑아 두는 것까지만 한다.
11. **사용량 API 폴링을 별도 데몬/`launchd` 로 분리.** 서버가 꺼져도 캡처가 갱신된다. 그러나
    프로세스가 하나 더 늘고 생명주기 관리(`server.json` 류)를 통째로 다시 만들어야 한다
    → 기각(결정 A3, 기존 루프에 게이트만 얹는다).

---

## 사용자 승인이 필요한 결정

### 승인 항목 1 — R1: 비공개 API 생산자를 도입할 것인가 (결정 A1·A6)

| 안 | 내용 | 위험 | 비고 |
|----|------|------|------|
| **A (권고)** | **스파이크 통과를 조건으로** Keychain + 비공개 usage 엔드포인트 폴링을 추가. `usage_api_enabled` **기본 off**, 5분 주기, 실패는 조용한 강등 | 비공개 API 의존 · 자격증명 취급 | 소비자 코드 0줄 변경. 스위치 한 줄로 무력화 |
| B | R1 을 포기하고 "패널은 터미널 세션이 필요하다"를 문서화 | 없음 | 요구 미충족 |

> **핵심 질문: 문서화되지 않은 API 와 Keychain 접근을 이 저장소에 들일 것인가.**
> 권고안은 "들이되, 옵트인·격리·조용한 강등·스파이크 선행"의 4중 안전장치를 건다.

### 승인 항목 2 — R2: 사라진 프로젝트의 순서 엔트리 (결정 O3)

| 안 | 동작 | 비고 |
|----|------|------|
| **A (권고)** | **지우지 않는다.** 최대 200개 보관, 표시는 교집합 | 하루 쉰 프로젝트가 자리를 지킨다 |
| B | 현행처럼 즉시 제거 | 목록에서 잠깐 빠지면 자리를 잃고 다음에 **맨 앞**으로 온다 |

### 승인 항목 3 — R3: `file://` 모드의 강등 방식 (결정 N7)

| 안 | 동작 | 비고 |
|----|------|------|
| **A (권고)** | 카드가 클릭 대상이 아니고, 툴팁으로 `/hub server start` 를 안내 | 조용한 실패 없음. 상호작용이 모드마다 갈리지 않는다 |
| B | `file://` 에서만 새 탭으로 연다 | 사용자가 명시적으로 원하지 않은 새 탭이 되살아난다 |

### 승인 항목 4 — R6: 테마 버튼의 모양 (결정 Y4)

| 안 | 모양 | 비고 |
|----|------|------|
| **A (권고)** | 새로고침과 동일한 **32px 원형 아이콘**(`☾`/`☀`). `.icon-btn` 공통 클래스 추출 | 폭 흔들림 0. `.refresh-btn` 의 CSS 가 일부 이동한다 |
| B | 현행 텍스트 알약 유지(`테마: 라이트`/`테마: 다크`) | 변경 최소. 토글마다 클러스터 폭이 흔들린다 |

### 승인 항목 5 — R5: 헤더 버튼의 고정 해제를 감수할 것인가 (결정 E2)

요구대로 고정을 풀면 **연결 끊김 경고색이 스크롤 밖으로 나간다.** 그대로 진행하고(권고),
문제가 되면 `position:sticky` 예비안으로 되돌리는 것으로 승인 요청한다.
