# 허브 온보딩에 statusLine 등록 편입 · 만료 사용량을 "조회되지 않음"으로 표시 (PRP)

> 요구 2건: **R-A** 첫 설치 흐름에서 `/hub statusline on` 도 함께 처리 ·
> **R-B** 5시간 지난 사용량 캡처를 숨기지 말고 "조회되지 않음" 상태 + 툴팁 안내로 표시

| 항목 | 값 |
|------|-----|
| 대상 | `commands/hub.md`(절차) · `hub/install.sh`(안내 문구) · `hub/bin/hub_usage.py`·`hub_collect.py`·`hub_model.py`(만료 계약) · `hub/bin/hub_template.html`(표시) |
| 브랜치 | `main` (HEAD `dc647b1`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md)(결정 U1~U5) → [`hub-usage-reset-time-and-refresh.md`](./hub-usage-reset-time-and-refresh.md)(결정 S1~S5·R1~R5) → [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)(결정 P1~P8) → [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md)(결정 UT1~UT4, 불변식 H1‴) → **이 문서** |
| 워크플로우 경로 | **전체 경로** (데이터 모델 변경 + 8개 파일 + 파이썬 3개 모듈) |
| 규모 | Small–Medium — 신규 0개 / 수정 8개 파일. 파이썬 순증 약 +25줄, 템플릿 +30줄, 절차 문서 별도 |
| 새 외부 의존성 | **없음** |
| **Python 변경** | **있다 — 이 PRP 의 첫 파이썬 변경이다.** `UsageSample` 에 필드 1개, `hub_usage` 에 순수 함수 1개, `hub_collect._capture_for_snapshot` 3줄. 단위 테스트 계획은 「테스트 계획 · 파이썬」 참조 |
| **승인 상태** | **승인됨(2026-08-14)** — 항목 1~4 전부 확정: 1(`/hub install` 에서 등록)·2(확인 1회 + "훅만" 선택지)·3(만료 시 `—` 플레이스홀더)·4(롤오버 동일 상태 통합) |

---

## 요구사항 요약

허브 사용량 패널이 신규 사용자에게 **도달하지 않고**, 기존 사용자에게는 **말없이 사라진다.**

**R-A** — 사용량 패널의 퍼센트는 `~/.claude/hub/rate_limits.json` 캡처에서 오고, 그 캡처를 만드는
표준 경로는 `/hub statusline on` 이다. 그런데 이 명령은 어떤 온보딩 경로에도 없다. `hub/install.sh`
의 마지막 안내는 `"다음 단계: /hub install (훅 옵트인) → /hub server start → /hub"`(130행)뿐이고,
`commands/hub.md` 는 164행에서 "등록하지 않으면 사용량 패널 자체가 존재하지 않습니다"라고
경고하지만 **그 문장을 읽을 기회 자체가 없다.** 결과적으로 신규 사용자는 패널의 존재를 모른다.

**R-B** — 캡처가 5시간(`USAGE_MAX_SAMPLE_AGE_MS`)보다 오래되면 `_capture_for_snapshot` 이
`usage = None` 으로 지워 **패널이 통째로 사라진다**(결정 U3). 사용자 입장에서는 "어제까지 있던
패널이 오늘 없다"가 되고, 화면상 원인 구분이 불가능하다(설치 안 함 / 껐음 / 낡음 / 계약 불일치가
전부 "패널 없음"으로 같다). 사용자는 **패널을 유지하되 "조회되지 않은 상태"로 표시하고 툴팁으로
이유를 알려 주기**를 요구했다.

두 요구는 같은 문제의 양끝이다 — **사용량 패널이 왜 안 보이는지를 화면이 스스로 설명하지 못한다.**
R-A 는 "처음부터 보이게" 하고, R-B 는 "사라지는 대신 말하게" 한다.

### 사용자 스토리

> 허브를 처음 설치하는 사람으로서, 안내를 따라가면 사용량 패널까지 자연히 켜졌으면 좋겠다.
> 며칠 세션을 안 돌린 뒤 허브를 열었을 때는, 패널이 사라지는 대신 "지금은 조회되지 않는 상태이고
> 세션을 한 번 돌리면 갱신된다"고 알려 줬으면 좋겠다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | `hub/install.sh` → `/hub install` 만 따라가면 훅과 statusLine 이 **둘 다** 등록된다 | 수동 M1 |
| S2 | 이미 다른 `statusLine` 이 있으면 **덮어쓰지 않고** 사유를 보고하며, **훅 설치는 그대로 성공**한다 | 수동 M2 |
| S3 | `/hub install` 을 두 번 불러도 `settings.json` 이 다시 쓰이지 않는다(멱등) | 수동 M3 |
| S4 | `hub/install.sh` 는 여전히 `settings.json` 을 **한 번도 건드리지 않는다** | 자동 T25-73 |
| S5 | 캡처가 5시간 넘게 낡으면 패널이 **보이고**, 퍼센트 자리가 `—`, 하단에 `조회되지 않음` 이 뜬다 | 수동 M4 |
| S6 | 그 줄에 마우스를 올리면 **왜 안 되는지 + 어떻게 갱신되는지** 툴팁이 뜬다 | 수동 M5 |
| S7 | 세션 창 롤오버(리셋 시각이 이미 지남)도 같은 "조회되지 않음"으로 보인다 | 수동 M6 |
| S8 | 캡처가 **아예 없으면**(신규 사용자·미등록) 패널은 기존대로 **뜨지 않는다** | 수동 M7 |
| S9 | 신선 → 만료 전이가 일어난 사이클에 `hub.html` 이 **다시 쓰여** 화면이 스스로 바뀐다 | 파이썬 U9 |
| S10 | 만료 상태에서도 아직 지나지 않은 **초기화 예정 시각 줄은 그대로 보인다** | 수동 M8 |
| S11 | `bash tests/run.sh` 전체 통과(T25-71~74 신규 + T25-67 개정 포함) | 자동 |
| S12 | `python3 -m unittest discover tests/hub` 전체 통과(신규 U1~U9 + 기존 N34·N35 개정 포함) | 자동 |

---

## 확정된 전제 (재론하지 않는다)

1. **`settings.json` 소유권 원칙**(`docs/prps/session-dashboard.md` 설계 결정 4, `hub_settings.py`
   모듈 주석): **설치 스크립트는 `settings.json` 을 건드리지 않는다.** 사용자가 `/hub install` ·
   `/hub off` · `/hub statusline on|off` 로 **명시적으로 부를 때만** `hub_settings.py` 가 손댄다.
   R-A 는 이 원칙을 **개정하지 않고** 그 안에서 푼다(결정 ON1).
2. **`statusLine` 은 배열이 아니라 단일 값이다** → 병합이 불가능해 **감지 → 거부**로 동작한다
   (결정 S4). 남의 `statusLine` 은 어떤 경우에도 덮어쓰지 않는다.
3. **허브는 읽기 전용 화면이다.** 서버는 2경로 화이트리스트 + 프로젝트 대시보드 라우트뿐이다.
4. **색각 안전 팔레트 유지.** 새 색 리터럴을 만들지 않고 기존 토큰(`--muted`·`--attention`)만 쓴다
   → T25-29 가 금지하는 구형 리터럴 3개(`#1F8A70`·`#C2410C`·`#F59E0B`)와 무관하다(확인함).
5. **불변식 H1‴**(`hub_template.html` 상단 주석). `#dzh-usage`·`#dzh-usage-toggle` 은 정적이고
   `#dzh-usage-body`(innerHTML)·`#dzh-usage-summary`(textContent)만 파생이다. R-B 는 **파생 영역만**
   건드린다.
6. **캡처 파일 포맷(`rate_limits.json`)은 바뀌지 않는다.** R-B 의 만료 표식은 **디스크에 저장되는
   값이 아니라 수집 시점(now_ms)의 판정**이다 — 두 생산자(statusLine·usage API)는 무변경이다.

### 비목표 (이번 변경 범위 밖 — 명시적으로 건드리지 않는다)

| 항목 | 이유 |
|------|------|
| `hub/install.sh` 가 `settings.json` 을 직접 쓰는 것 | 전제 1 위반. 결정 ON1 에서 기각한 안이다 |
| `hub/install.sh` 에 대화형 프롬프트 추가 | 이 스크립트는 `--dry-run`·`--force` 를 가진 **비대화형** 배포 도구다. TTY 프롬프트를 넣으면 자동화·CI 에서 멈춘다 |
| `/hub off`(훅 제거)가 statusLine 도 함께 제거 | **비대칭을 의도적으로 유지한다**(결정 ON5). 훅만 끄고 상태줄은 남기고 싶은 사용자를 강제로 되돌리지 않는다. 제거 경로는 `/hub statusline off` 하나로 유지 |
| 새 `/hub setup` 서브커맨드 신설 | `/hub install` 과 역할이 겹친다(YAGNI, 미채택 대안 2) |
| **캡처가 아예 없을 때 "조회되지 않음" 패널 표시** | 결정 EX1 — 보여줄 마지막 값이 없다. 신규 사용자 도달 문제는 **R-A 가 온보딩에서 푼다** |
| `show_usage_panel:false` 일 때의 표시 | 사용자가 명시적으로 껐다. 읽기 자체를 하지 않는 것이 진짜 프라이버시 제어다(전제 유지) |
| 계약 불일치(파싱 실패) 캡처의 표시 | 값을 신뢰할 수 없다. 기존 경고 1건 유지 + 숨김 |
| `rate_limits.json` 포맷 변경 | 전제 6 |
| 클라이언트(브라우저)의 만료 2차 재판정 | 결정 EX7 — 서버가 5초마다 판정한다. 서버가 죽으면 화면 전체가 멈춘 것이고 그 사실은 새로고침 버튼이 이미 알린다 |

---

## 영향 범위

### 수정 파일 (8개)

| 파일 | 변경 | 요구 |
|------|------|------|
| `commands/hub.md` | `/hub install` 절에 statusLine 등록 2단계 절차 + 통합 고지문 + 실패 비차단 규칙 추가. `/hub statusline on` 절은 **단독 재실행 경로로 유지**하되 고지문 중복을 정리. 164행 "등록하지 않으면 사용량 패널 자체가 존재하지 않습니다" 문구를 R-B 반영해 정정 | R-A·R-B |
| `hub/install.sh` | 130행 "다음 단계" 안내 문구 1줄(`/hub install (훅 + 상태줄 옵트인)`). **코드 변경 없음 — `settings.json` 을 여전히 건드리지 않는다** | R-A |
| `hub/bin/hub_usage.py` | `UsageSample` 에 `is_stale: bool = False` 필드 1개 + 순수 함수 `mark_stale_usage_sample()` 1개(약 12줄) | R-B |
| `hub/bin/hub_collect.py` | `_capture_for_snapshot` 의 만료 처리 3줄 교체(`usage = None` → `mark_stale_usage_sample(...)`) + docstring 1문단 | R-B |
| `hub/bin/hub_model.py` | **주석 1줄만** — `HubSnapshot.usage` 필드 주석의 "없으면 패널을 그리지 않는다"를 "없으면 패널을 그리지 않는다(만료는 `is_stale` 로 표시된다)"로 정정. **필드 선언 문자열은 그대로 둔다**(T25-56 이 완전 일치로 검사한다 — GOTCHA 3) | R-B |
| `hub/bin/hub_template.html` | ① `usage-stale` 계열 CSS 3줄 ② `renderUsagePanel` 분기 + `showUsagePanel`·`renderUsageStaleRow`·`renderUsageStaleNote` 함수 ③ `usageSummaryText` 분기 ④ **툴팁 옵저버의 `#dzh-usage-body` 관찰 복원 2줄**(H1‴ 조항 5 의 조건 이행) ⑤ 상단 계약 주석 조항 5 갱신 | R-B |
| `tests/run.sh` | **T25-67 ③ 반전**(옵저버 부재 → 존재) + T25-71~74 신규. `test_desc` 와 1985행 주석의 범위 표기 갱신 | 둘 다 |
| `hub/README.md` | 「빠른 시작」 4줄 → statusLine 반영 · 「사용량 패널」의 만료 숨김 서술 2문단 정정 · 「한도 초기화 예정 시각」의 "패널 자체가 뜨지 않으므로" 문장 정정 | 둘 다 |

### 단위 테스트 파일 (수정 2개)

| 파일 | 변경 |
|------|------|
| `tests/hub/test_hub_usage.py` | **신규 클래스** `MarkStaleUsageSampleTest`(U1~U7). 기존 `is_usage_sample_expired`·`is_session_window_rolled_over` 테스트는 **무변경**(두 함수의 계약이 그대로다) |
| `tests/hub/test_hub_collect.py` | **기존 N34·N35 개정**(`usage is None` → `usage.is_stale is True`) + 신규 U8(만료 상태에서도 resets 유지)·U9(`snapshot_content_key` 전이 감지) |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_settings.py` | **파이썬 변경 없음.** `install_hooks()`·`install_statusline()` 이 이미 각각 멱등이고 실패 계약(`ok:false`+`reason`)을 갖는다. R-A 는 **절차 문서가 두 함수를 순서대로 부르는 것**이다(결정 ON2) |
| `hub/bin/hub.py` | 같은 이유. `install-hooks`·`install-statusline` 두 서브커맨드가 이미 존재한다. `_usage_sample_age_ms`(`/hub status`)는 **만료 여부와 무관하게 나이를 보고**하도록 이미 작성돼 있다(확인함) → 무변경 |
| `hub/bin/hub_statusline.py`·`hub_usage_fetch.py`·`hub_server.py`·`hub_daemon.py`·`hub_hook.py`·`hub_parse.py` | 캡처 **생산자**와 서버·훅은 만료 판정에 관여하지 않는다. 전제 6 |
| `commands/dashboard.md`·`commands/env-update.md` | `/dashboard` 자산과 무관 |
| `install.sh`(루트) | 허브를 모른다(T25-21). 그 성질을 그대로 유지 |
| `hub/install.sh` 의 **코드** | 문자열 1줄만 바뀐다. 파일 수·`--uninstall` 순서 불변 → T25-1·2·23·39 무영향 |

---

## 요구 R-A — 첫 설치 흐름에 statusLine 등록을 편입한다

### 문제의 정확한 위치

```
hub/install.sh:130   log_info "다음 단계: /hub install (훅 옵트인) → /hub server start → /hub"
hub/README.md:26-31  빠른 시작 4줄 — statusline 언급 없음
commands/hub.md:164  "…등록하지 않으면 사용량 패널 자체가 존재하지 않습니다"
                      ↑ 이 경고를 읽으려면 이미 /hub statusline on 절을 찾아 들어와야 한다
```

기능은 완성돼 있고 **진입로만 없다.**

### 결정 ON1 — `hub/install.sh` 가 아니라 **`/hub install`** 에서 처리한다

| 안 | 내용 | 판정 |
|----|------|------|
| a | `hub/install.sh` 가 `python3 hub.py install-statusline` 을 직접 호출 | **거부.** ① 전제 1(소유권 원칙) 위반 — 그 원칙은 문서 1곳이 아니라 `hub_settings.py` 모듈 주석·`session-dashboard.md` 결정 4·`hub/install.sh` 의 설계 의도 3곳에 박혀 있다 ② **비대화형 스크립트가 전역 설정을 사전 동의 없이 바꾼다** — statusLine 은 *모든 프로젝트의 터미널 상태줄*에 영향을 준다. 이 저장소는 그런 변경마다 "고지 → 확인"을 요구해 왔다(훅 프라이버시 고지가 그 선례다) ③ `--dry-run` 의 의미가 깨진다(계획만 출력해야 하는데 `settings.json` 을 쓰는 분기가 생긴다) |
| **b (채택)** | `/hub install` 절차가 `install-hooks` 성공 후 `install-statusline` 을 이어 부른다 | **채택.** `settings.json` 을 이미 만지는 **유일한 옵트인 자리**다. 원칙이 그대로 유지되고, 사용자 확인 절차도 이미 그 자리에 있다 |
| c | `hub/install.sh` 에 대화형 프롬프트를 붙여 물어본 뒤 호출 | **거부.** 비대화형 배포 도구다(비목표 표) |

**사용자 표현("첫 설치 시")과의 간극 — 해석을 명시한다.** 사용자가 말한 "첫 설치"는
`hub/install.sh` 단독이 아니라 **`hub/install.sh` → `/hub install` 로 이어지는 온보딩 흐름 전체**로
읽는다. 근거: (1) 사용자의 목적은 "신규 사용자가 사용량 패널에 도달하는 것"이고 안 b 가 그 목적을
100% 달성한다, (2) `hub/install.sh` 만으로는 훅도 설치되지 않아 **허브 자체가 동작하지 않는다** —
`/hub install` 은 이미 필수 단계이지 선택 단계가 아니다, (3) 안 a 는 되돌리기 어려운 원칙 파괴다.
**이 해석은 승인 항목 1 로 올린다.**

### 결정 ON2 — 병합은 **절차(`commands/hub.md`)에서** 한다. 파이썬은 손대지 않는다

`hub.py install-hooks` 서브커맨드 안에 statusLine 등록을 합치는 안을 검토했고 **거부한다.**

| 근거 | 설명 |
|------|------|
| 이름이 거짓이 된다 | `install-hooks` 가 statusLine 도 설치하면, `/hub status`·문서·테스트가 모두 그 거짓말을 따라가야 한다 |
| 대칭이 깨진다 | `uninstall-hooks` 는 statusLine 을 지우지 않는다(결정 ON5) — 설치만 합치면 설치/제거가 비대칭인데 그 비대칭이 **이름에 드러나지 않는다** |
| 고지문이 뭉개진다 | 훅 고지(프롬프트 120자 평문 보관)와 statusLine 고지(모든 프로젝트 상태줄 변경)는 **성격이 다른 두 가지 동의**다. 한 함수 안에 넣으면 어느 것에 동의했는지 흐려진다 |
| 실패 격리가 어려워진다 | 지금은 `settings.json` 을 **각각 원자적으로** 쓴다. 한 서브커맨드로 합치면 "훅은 썼는데 statusLine 에서 실패" 상태의 반환 계약을 새로 설계해야 한다 |
| 기존 계약·테스트가 바뀐다 | `{"ok":True,"installed":[...],"already_installed":[...]}` 를 소비하는 문서·보고·테스트가 전부 영향을 받는다 |

절차 병합은 **Bash 호출 1회 증가**가 전부이고, 위 다섯 문제가 하나도 생기지 않는다.

### 결정 ON3 — 순서는 **훅 먼저, statusLine 나중**

훅은 허브의 본체(데이터 수집)이고 statusLine 은 사용량 패널이라는 **부가 기능**이다. statusLine 을
앞에 두면 남의 `statusLine` 과의 충돌이 본체 설치를 가로막는 모양이 된다. 뒤에 두면 충돌해도
본체는 이미 살아 있다.

### 결정 ON4 — 사용자 확인은 **한 번**, 고지문은 **둘 다** 보여준다

두 고지가 같은 시점·같은 파일(`settings.json`)에 대한 것이므로 확인을 두 번 받는 것은 온보딩
마찰만 늘린다. 대신:

- 고지문에 **"상태줄이 바뀌는 게 싫으면 `/hub statusline off` 로 즉시 되돌릴 수 있습니다"** 를
  1줄 포함한다(되돌리기 경로를 동의 시점에 알린다).
- 사용자가 **"훅만"** 이라고 답하면 statusLine 단계를 **건너뛴다.** 절차에 이 분기를 명시해
  결정성을 유지한다(추측으로 건너뛰거나 강행하지 않는다).

### 결정 ON5 — 실패는 **훅 설치를 되돌리지 않는다**. 사유와 대안만 보고한다

`install-statusline` 의 `ok:false` 는 세 가지다.

| 사유 | 보고 |
|------|------|
| 남의 `statusLine` 이 이미 있다(`current_command` 동봉) | "기존 상태줄 설정을 보존했습니다. 사용량 패널을 쓰려면 `/hub statusline on` 을 직접 실행하거나, 터미널을 건드리지 않는 대안으로 `~/.claude/hub/config.json` 에 `usage_api_enabled: true`(macOS 전용, 옵트인)를 켤 수 있습니다" |
| `hub_statusline.py` 가 없다 | "`hub/install.sh` 를 다시 실행하십시오" (기존 `reason` 그대로) |
| `settings.json` 파싱 실패 | 기존 `reason` 그대로. **재시도하지 않는다** |

어느 경우에도 **훅 설치 결과를 되돌리지 않고, `/hub install` 을 실패로 보고하지 않는다** — 훅은
실제로 설치됐기 때문이다. 이는 `/dashboard` 「자동 발행」의 실패 비차단 원칙과 같은 형태다.

`/hub off`(훅 제거)는 statusLine 을 **건드리지 않는다**(비목표 표). 제거는 `/hub statusline off`
하나로 유지한다 — 훅만 끄고 상태줄은 남기고 싶은 사용자를 강제로 되돌리지 않는다.

### 결정 ON6 — 멱등성은 **기존 함수가 이미 보장한다**

`install_statusline()` 은 `statusline_owner(settings) == "hub"` 면
`{"ok":True,"installed":False,"already_installed":True}` 를 돌려주고 **파일을 쓰지 않는다.**
`install_hooks()` 도 `if installed:` 일 때만 쓴다. 따라서 `/hub install` 재실행은 `settings.json` 을
한 바이트도 바꾸지 않는다 — **절차에 멱등 로직을 새로 만들지 않는다.**

### 결정 ON7 — 문서 진입로를 3곳에서 함께 고친다

| 위치 | 변경 |
|------|------|
| `hub/install.sh:130` | `"다음 단계: /hub install (훅 + 상태줄 옵트인) → /hub server start → /hub"` — **문자열 1줄.** 이 파일은 여전히 `settings.json` 을 모른다(T25-73 이 역방향으로 강제) |
| `hub/README.md` 「빠른 시작」 | `/hub install` 줄의 주석을 `# 2. 전역 훅 6개 + 상태줄 등록(옵트인)` 으로. 「사용량 패널」 절 첫머리에 "이 등록은 `/hub install` 이 함께 처리한다" 1줄 |
| `commands/hub.md` `/hub install` 절 | 절차 2단계 + 통합 고지문 + 실패 비차단 규칙(아래 인터페이스) |

### R-A 인터페이스 (`commands/hub.md` `/hub install` 절 문안)

````markdown
## `/hub install` — 훅 + 상태줄 설치 (옵트인)

**1단계 — 훅.**

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-hooks --json
```

**2단계 — 상태줄.** 1단계의 `ok` 와 무관하게 이어서 실행한다(둘은 독립된 옵트인이다).

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-statusline --json
```

**두 명령 실행 전 아래 고지를 한 번에 보여주고 진행 여부를 확인한다**(최초 1회. 두 결과의
`already_installed` 가 모두 참이면 다음부터 생략):

> **① 전역 훅 6개** — `SessionStart`·`UserPromptSubmit`·`Stop`·`SubagentStart`·`SubagentStop`·
> `SessionEnd` 에 훅을 추가합니다. 프롬프트 앞부분(120자)이 `~/.claude/hub/events/` 에 평문으로
> 최대 7일 보관됩니다(`~/.claude/hub/config.json` 의 `record_prompt_excerpt:false` 로 끌 수 있음).
> **② 터미널 상태줄** — `~/.claude/settings.json` 의 `statusLine` 에 우리 커맨드를 등록합니다.
> **모든 프로젝트의 터미널 상태줄**에 `세션 23% · 주간 41%` 가 상시 표시되고, 그 값이
> `~/.claude/hub/rate_limits.json` 에 캡처돼 **허브의 사용량 패널을 채웁니다.** 이미 다른
> `statusLine` 이 설정돼 있으면 **덮어쓰지 않고 거부**합니다.
> 기존에 설치된 다른 도구의 훅(CAM·Litmus 등)은 건드리지 않습니다.
> 상태줄만 원하지 않으면 나중에 `/hub statusline off` 로 즉시 되돌릴 수 있습니다.

사용자가 **"훅만"** 이라고 답하면 2단계를 건너뛴다. 임의로 건너뛰거나 강행하지 않는다.

**보고** — 두 결과를 한 덩어리로 보고한다.

| 상황 | 보고 |
|------|------|
| 둘 다 성공 | 훅 `installed`/`already_installed` + 상태줄 `installed`/`already_installed`. 이어서 `/hub server start` 를 안내 |
| 훅 성공 · 상태줄 `ok:false` | **`/hub install` 을 실패로 보고하지 않는다.** 훅 결과를 먼저 보고하고, 상태줄은 `reason` 을 그대로 옮긴다. 남의 `statusLine` 충돌(`current_command` 동봉)이면 "기존 설정을 보존했습니다 — 사용량 패널이 필요하면 `/hub statusline on` 을 직접 실행하거나, 터미널을 건드리지 않는 대안으로 `config.json` 의 `usage_api_enabled:true`(macOS 전용, 옵트인)를 쓸 수 있습니다" 한 줄을 덧붙인다 |
| 훅 `ok:false` | 훅의 `reason` 을 그대로 보고하고 **재시도하지 않는다**(`settings.json` 파싱 실패는 사용자의 권한 설정을 보호하기 위한 의도적 중단이다). 2단계 결과도 함께 보고한다 |

두 명령 모두 **멱등**이다 — 이미 설치돼 있으면 `settings.json` 을 쓰지 않는다.
````

---

## 요구 R-B — 만료 캡처를 "조회되지 않음"으로 표시한다

### 현재 동작(정확히)

```python
# hub_collect._capture_for_snapshot (332~337행)
usage = hub_usage.usage_sample_from_capture(capture)
if usage is not None and (
    hub_usage.is_usage_sample_expired(usage, now_ms)          # 나이 ≥ 5시간
    or hub_usage.is_session_window_rolled_over(capture, now_ms)  # 세션 리셋 시각이 이미 지남
):
    usage = None            # ← 스냅샷에서 통째로 탈락 → 템플릿이 패널을 숨긴다
```

```js
// hub_template.renderUsagePanel (890~891행)
if(!usage){ hideUsagePanel(); return; }
```

### 결정 EX1 — 표시 경계: **"값은 있으나 낡음"만** 표시한다

| 상태 | 지금 | 변경 후 | 근거 |
|------|------|---------|------|
| 캡처 파일 없음(statusLine 미등록·세션 미실행) | 숨김 | **숨김(유지)** | 보여줄 마지막 값이 **없다.** "조회되지 않음" 패널만 상시 떠 있으면 **설치하지 않은 기능을 광고하는 UI** 가 된다. 신규 사용자 도달 문제는 **R-A 가 온보딩에서 푼다** — 두 요구가 서로를 보완한다 |
| `show_usage_panel:false` | 숨김 | **숨김(유지)** | 사용자가 명시적으로 껐다. 파일을 읽지도 않는다 |
| 계약 불일치(파싱 실패) | 숨김 + 경고 1건 | **숨김(유지)** | 값을 신뢰할 수 없다. 경고는 이미 `warnings` 로 뜬다 |
| 구형 캡처(퍼센트 필드 없음) | 숨김 | **숨김(유지)** | `usage_sample_from_capture` 가 `None` — 보여줄 값이 없다 |
| **나이 ≥ 5시간** | 숨김 | **표시(조회되지 않음)** | ← 요구의 핵심 |
| **세션 창 롤오버** | 숨김 | **표시(조회되지 않음)** | 결정 EX2 |

### 결정 EX2 — 만료와 롤오버를 **하나의 상태로 묶는다**

사용자 표현은 "5시간이 지나 낡은" 이지만, 롤오버(`is_session_window_rolled_over`)도 화면에서는
같은 현상이다 — **둘 다 "마지막 값이 지금은 참이 아니다"** 이고, 사용자가 할 행동도 같다
("세션을 한 번 돌린다"). 하나만 표시하면 **어떨 땐 패널이 사라지고 어떨 땐 남는**, 사용자가
설명할 수 없는 화면이 된다. 두 판정을 OR 해 `is_stale` **하나**로 접는다.

### 결정 EX3 — 데이터 계약: `UsageSample.is_stale: bool = False` (필드 1개)

| 안 | 내용 | 판정 |
|----|------|------|
| **A (채택)** | `UsageSample` 에 `is_stale: bool = False` 추가, `usage` 는 유지 | 소비자가 **한 값만** 본다. 기본값이 있어 기존 생성자 호출부(단위 테스트 포함)가 전부 그대로 통과한다. **불가능한 조합이 표현되지 않는다** |
| B | `HubSnapshot.usage_state: "fresh"\|"stale"` 열거를 최상위에 추가 | **거부.** `usage=None` + `usage_state="stale"` 같은 **불가능 조합이 타입으로 표현 가능**해지고, 그 정합을 호출자가 손으로 지켜야 한다 |
| C | `HubSnapshot.stale_usage: UsageSample \| None` 별도 필드 | **거부.** "둘 다 있으면?"이라는 불가능 조합이 또 생기고, 소비자가 두 필드를 봐야 한다 |

**`UsageSample` docstring 의 기존 경고와의 관계(중요)** — 그 docstring 은 *"파생값(나이)은 담지
않는다 — content_key 재작성 폭주 방지(결정 D3)"* 라고 못 박고 있다. `is_stale` 은 **파생값이 맞지만
이산(boolean)이다.** 나이(ms)는 5초마다 바뀌어 재작성이 폭주하지만, `is_stale` 은 캡처 수명 동안
**최대 1회** False→True 로 바뀐다. 결정 D3 의 정신(**연속적 파생값 금지**)을 지키면서 그 취지를
정확히 반대로 이용하는 것이 결정 EX4 다. docstring 에 이 구분을 1문장 추가한다.

### 결정 EX4 — `snapshot_content_key` 는 **이미 옳게 동작한다** (추가 장치 없음)

`snapshot_content_key` 는 `collected_at_ms` 만 뺀 스냅샷 전체의 JSON 이다. `is_stale` 이 스냅샷에
실리는 순간:

- 신선 구간: `is_stale=False` 로 **고정** → 키 불변 → `hub.html` 재작성 없음(기존과 동일).
- 만료 전이 사이클: `False → True` → **키가 바뀐다** → `hub_server._run_collect_cycle` 의
  `needs_write` 가 참이 되어 `hub.html` 이 다시 쓰인다 → **폴링이 그 변화를 받아 화면이 스스로
  "조회되지 않음"으로 바뀐다.**
- 만료 구간: `True` 로 고정 → 다시 조용해진다.

즉 **시간 경과만으로 키가 바뀌지 않는 현 구조에 정확히 1회의 이산 전이를 얹는 것**이 이 설계다.
별도의 만료 타이머·강제 재작성 장치를 만들지 않는다. 같은 성질을 `drop_passed_resets` 가 이미
갖고 있다(리셋 시각이 지나는 순간 키가 바뀐다) — **선례가 있고 일관적이다.**
이 성질은 파이썬 테스트 U9 가 기계적으로 고정한다.

### 결정 EX5 — 판정은 **순수 함수 1개**로 뽑는다

```python
def mark_stale_usage_sample(
    sample: UsageSample, capture: RateLimitCapture, now_ms: int
) -> UsageSample:
    """낡은 샘플에 is_stale 표식을 단 새 샘플을 돌려준다(순수). 신선하면 원본 그대로.

    두 가지 낡음을 하나로 접는다(결정 EX2): ① 세션 창(5시간)보다 오래된 샘플
    ② 세션 창이 이미 리셋돼 캡처된 세션 퍼센트가 확실히 틀린 경우. 화면에서 둘을 구분할
    실익이 없다 — 사용자가 할 행동("세션을 한 번 돌린다")이 같다.
    """
    if is_usage_sample_expired(sample, now_ms) or is_session_window_rolled_over(capture, now_ms):
        return replace(sample, is_stale=True)
    return sample
```

- `is_usage_sample_expired`·`is_session_window_rolled_over` 는 **무변경**이다 → 그 단위 테스트
  (case14~17·n22)도 무변경으로 통과한다.
- `replace` 는 이 모듈이 이미 `drop_passed_resets` 에서 쓰는 관용구다(새 import 없음).
- I/O 레이어(`hub_collect`)가 두 판정을 손으로 OR 하지 않게 한다 — **"왜 둘을 묶었나"가 이 함수의
  docstring 한 곳에만 산다.**

`_capture_for_snapshot` 의 변경은 3줄이다:

```python
usage = hub_usage.usage_sample_from_capture(capture)
if usage is not None:
    usage = hub_usage.mark_stale_usage_sample(usage, capture, now_ms)   # 숨기지 않고 표식만 단다(R-B)
```

### 결정 EX6 — 표시 형태: 퍼센트는 `—`, 막대는 그리지 않는다

| 안 | 판정 |
|----|------|
| **A (채택) `—` 플레이스홀더 + 막대 없음 + 마지막 값 미표시** | 낡은 숫자를 화면에 남기면 스크린샷·곁눈질에서 **현재값으로 오해**된다. 그 오해를 피하려는 것이 애초에 결정 U3(숨김)의 이유였고, `_is_valid_percent` 가 float 을 거부하는 이유("0% 를 조용히 그리는 것은 데이터 없음보다 나쁜 거짓말")와 같은 계열이다 |
| B 마지막 값을 흐리게 + 만료 표식 | **거부(승인 항목 3 으로 재확인).** 5시간 넘은 값의 실용 가치가 낮은데 오해 위험은 크다 |
| C 빈 막대(0 폭)를 회색으로 | **거부.** 그것이 바로 "0% 오해" 다 |

막대가 빠져 패널이 짧아지는 것은 `applyUsageClearance()` 가 실측으로 하단 여백을 다시 잡으므로
레이아웃 문제가 없다(기존 장치).

**변경 후 패널(펼침)**

```
Claude 사용 한도                                    ▾
세션 (5시간)                                        —
초기화 18:32 · 2시간 12분 뒤            ← 아직 안 지났으면 그대로(결정 EX8)
주간 (7일)                                          —
초기화 8/20 09:00 · 5일 뒤
조회되지 않음 · 마지막 갱신 7시간 12분 전   ← 툴팁 트리거(결정 EX7)
```

**접힘 한 줄 요약**: `세션 43% · 주간 71%` → **`조회되지 않음`**

### 결정 EX7 — 툴팁은 **한 곳**만 되살린다 (H1‴ 조항 5 의 조건 이행)

직전 PRP 의 결정 UT1·UT4 가 패널 안 툴팁을 전부 없앴고, 불변식 H1‴ 조항 5 가 *"되살리려면
`tooltipDismissObserver` 의 `#dzh-usage-body` 관찰도 함께 되살려야 한다"* 는 조건을 박아 뒀다.
R-B 는 그 조건을 **이행하며 부분 복원**한다.

| 항목 | 결정 |
|------|------|
| 트리거 | **`.usage-stale-note` 한 요소만.** 여러 곳에 붙이면 UT1 의 취지(조용한 패널)와 다시 충돌한다 |
| 문구 | `마지막 확인 이후 5시간이 지나 사용률이 더 이상 유효하지 않습니다. Claude Code 세션을 한 번 시작하면 자동으로 갱신됩니다.` — **왜**(값이 유효하지 않다) + **어떻게**(세션 1회) 두 가지만 담는다 |
| 옵저버 | `tooltipDismissObserver.observe(#dzh-usage-body, {childList:true})` **복원 2줄.** 30초 틱이 본문을 통째로 교체하는데 포인터가 멈춰 있으면 낡은 툴팁이 고아로 남는다(결정 T6) — 트리거가 그 안으로 돌아왔으므로 관찰도 함께 돌아와야 한다 |
| 되살리지 않는 것 | `이 정보를 확인한 시각`(캡처 시각) 툴팁은 **복원하지 않는다** — 결정 UT1 이 그대로 유효하다 |

**「부분 대체됨」 표기 대상**: `hub-first-entry-and-ui-signals.md` 의 결정 UT4 와 불변식 H1‴ 조항 5,
그리고 `hub_template.html` 465행 부근 주석("`#dzh-usage-body` 관찰은 R5 로 지웠다 — 그 안에는
트리거가 더 없어…").

### 결정 EX8 — 초기화 예정 시각 줄은 **만료 상태에서도 그대로 그린다**

리셋 시각은 퍼센트와 달리 **절대 시각**이라 지나기 전까지는 참이다(기존 설계의 명시적 성질 —
`hub/README.md` 「한도 초기화 예정 시각」이 이미 그렇게 적고 있다). 오히려 만료 상태에서 사용자가
가장 알고 싶은 정보가 "언제 초기화되는가"다.

- 이미 지난 값은 서버(`drop_passed_resets`)와 클라이언트(`usageResetText` 의 `remainingLabel`)가
  **이중으로** 걷어낸다 — 변경 없음.
- 세션 리셋이 지났다는 것은 곧 롤오버(만료 사유 ②)이므로, 그 경우 세션 줄만 자연히 사라지고
  주간 줄이 남는다. **일관적이다.**

### 결정 EX9 — 클라이언트는 만료를 **재판정하지 않는다**

`is_stale` 은 서버가 준 값을 그대로 쓴다. 30초 틱은 `elapsedLabel`(마지막 갱신 N분 전)만 다시
계산한다.

- 정상(서버 가동) 상태에서 판정 지연은 최대 1 수집 주기(기본 5초)다.
- 서버가 죽으면 화면 전체가 멈춘 것이고, 그 사실은 새로고침 버튼의 경고색이 이미 알린다
  (`.refresh-btn.connection-lost`).
- `file://` 로 낡은 `hub.html` 을 열면 `is_stale` 도 낡는다 — **화면 전체가 낡은 것과 일관적**이다.
- 클라이언트 2차 판정을 넣으면 `USAGE_MAX_SAMPLE_AGE_MS` 상수가 파이썬과 JS 두 곳에 생긴다
  (같은 규칙의 출처가 둘이 되는 것을 이 저장소는 반복해서 거부해 왔다 — 결정 P7·F1 과 같은 이유).

### R-B 인터페이스 (템플릿 증분)

```css
/* 만료(조회되지 않음) 상태 — 새 색 토큰을 만들지 않고 기존 --muted·--attention 만 쓴다. */
.usage-pct-empty{color:var(--muted);font-weight:700}
.usage-stale-note{color:var(--attention)}
.usage.usage-stale .usage-summary{color:var(--muted)}
```

```js
var USAGE_EMPTY_VALUE = '—';
var USAGE_STALE_LABEL = '조회되지 않음';
var USAGE_STALE_TOOLTIP = '마지막 확인 이후 5시간이 지나 사용률이 더 이상 유효하지 않습니다. '
  + 'Claude Code 세션을 한 번 시작하면 자동으로 갱신됩니다.';

// 만료 행 — 막대를 그리지 않는다. 0% 로 오해되는 빈 막대보다 '값 없음'이 정직하다(결정 EX6).
function renderUsageStaleRow(label){
  return '<div class="usage-row"><span>' + label + '</span>'
    + '<span class="usage-pct usage-pct-empty">' + USAGE_EMPTY_VALUE + '</span></div>';
}

// 만료 안내 한 줄. 패널 안 유일한 툴팁 트리거다(결정 EX7) — 그래서 tooltipDismissObserver 의
// #dzh-usage-body 관찰이 함께 되살아났다(불변식 H1‴ 조항 5 의 조건).
function renderUsageStaleNote(usage){
  return '<div class="usage-meta usage-stale-note" data-tooltip="' + escapeHtml(USAGE_STALE_TOOLTIP)
    + '">' + USAGE_STALE_LABEL + ' · 마지막 갱신 ' + elapsedLabel(usage.sampled_at_ms) + '</div>';
}

// 패널을 실제로 띄우는 유일한 경로 — 신선/만료 두 분기가 표시 상태 갱신을 공유한다.
function showUsagePanel(bodyHtml, summaryText, isStale){
  usageSummaryEl.textContent = summaryText;
  usageBodyEl.innerHTML = bodyHtml;
  usageEl.classList.toggle('usage-stale', isStale);
  usageEl.hidden = false;
  document.body.classList.add('has-usage');
  applyUsageCollapsedState();
}

function usageSummaryText(usage){
  if(usage.is_stale) return USAGE_STALE_LABEL;
  return '세션 ' + usage.session_percent + '% · 주간 ' + usage.weekly_percent + '%';
}
```

`renderUsagePanel` 은 두 본문을 만들어 `showUsagePanel` 에 넘긴다(각 분기 10줄 이하 유지):

```js
function renderUsagePanel(usage, resets){
  if(!usage){ hideUsagePanel(); return; }
  var sessionResetRow = renderUsageResetRow(resets && resets.session_resets_at_ms);
  var weeklyResetRow = renderUsageResetRow(resets && resets.weekly_resets_at_ms);
  if(usage.is_stale){
    showUsagePanel(
      renderUsageStaleRow(USAGE_SESSION_LABEL) + sessionResetRow
      + renderUsageStaleRow(USAGE_WEEKLY_LABEL) + weeklyResetRow
      + renderUsageStaleNote(usage),
      usageSummaryText(usage), true
    );
    return;
  }
  var sessionBar = renderUsageBar(USAGE_SESSION_LABEL, usage.session_percent);
  var weeklyBar = renderUsageBar(USAGE_WEEKLY_LABEL, usage.weekly_percent);
  if(!sessionBar || !weeklyBar){ hideUsagePanel(); return; }
  var meta = '마지막 갱신 ' + elapsedLabel(usage.sampled_at_ms) + ' ' + USAGE_CYCLE_NOTE;
  showUsagePanel(
    sessionBar + sessionResetRow + weeklyBar + weeklyResetRow
    + '<div class="usage-meta">' + meta + '</div>',
    usageSummaryText(usage), false
  );
}
```

---

## 데이터 모델 — 모듈 간 계약

| 계약 | 변경 | 비고 |
|------|------|------|
| `hub_usage.UsageSample` | **필드 1개 추가** — `is_stale: bool = False` | 기본값이 있어 기존 생성자 호출부 전부 하위 호환. `#dzh-data` JSON 에 `"is_stale": false` 가 새로 실린다 |
| `hub_usage.mark_stale_usage_sample(sample, capture, now_ms) -> UsageSample` | **신규(순수)** | 두 만료 판정을 OR 하는 유일한 자리 |
| `hub_model.HubSnapshot.usage` | **선언 무변경** | 의미만 좁혀진다: `None` = "보여줄 값이 없다", `is_stale=True` = "값은 있으나 낡았다" |
| `hub_model.HubSnapshot.rate_limit_resets` | 무변경 | 결정 EX8 |
| `rate_limits.json` 파일 포맷 | **무변경** | 전제 6 — `is_stale` 은 디스크에 저장되지 않는 수집 시점 판정이다 |
| `hub.py status` 의 `usage_sample_age_ms` | **무변경** | 만료 여부와 무관하게 나이를 보고하도록 이미 작성돼 있다(확인함) |
| `settings.json` 병합 계약(`install_hooks`·`install_statusline`) | **무변경** | R-A 는 절차만 바꾼다(결정 ON2) |

**새 DOM/CSS 계약**

| 이름 | 의미 |
|------|------|
| `.usage.usage-stale` | 패널이 만료 상태다. 접힘 요약 색만 낮춘다 |
| `.usage-pct-empty` | 값 없음(`—`) 자리. 강조색을 쓰지 않아 값처럼 보이지 않는다 |
| `.usage-stale-note` | 만료 안내 줄. **패널 안 유일한 툴팁 트리거**(결정 EX7) |

---

## GOTCHA (구현 중 반드시 확인)

1. **툴팁 옵저버 복원을 빠뜨리면 고아 툴팁이 남는다.** `.usage-stale-note` 는 30초 틱마다
   `#dzh-usage-body` 와 함께 파괴·재생성된다. 포인터를 올려 둔 채 틱이 돌면 트리거 노드가 사라진
   뒤에도 툴팁이 떠 있다(결정 T6 이 잡은 그 버그). **복원 2줄이 이 기능의 필수 부품**이며
   T25-71 이 강제한다.
2. **`is_stale` 을 연속값(나이)으로 바꾸지 마라.** `UsageSample` docstring 의 결정 D3 경고가
   그대로 유효하다 — 나이를 담는 순간 `snapshot_content_key` 가 5초마다 바뀌어 `hub.html`
   재작성이 폭주한다. 이산 boolean 이라서만 안전하다(결정 EX4).
3. **`hub_model.py` 의 `usage:` 필드 선언 문자열을 건드리지 마라.** T25-56 이
   `usage: UsageSample | None = None` 을 **완전 일치**로 검사한다. 이번 변경은 그 줄의
   **뒤쪽 주석만** 고친다.
4. **`renderUsageBar` 를 지우지 마라.** 만료 경로에서 호출만 하지 않을 뿐 신선 경로에는 그대로
   필요하고, T25-34 가 `role="progressbar"` 문자열의 존재를 검사한다(그 문자열은 이 함수 안에 있다).
5. **T25-67 ③ 은 이번에 반전된다.** 지금은 `usageBodyElForTooltipObserver` 가 **0건**이어야
   통과하는데, R-B 가 그것을 되살린다 → **테스트를 함께 고치지 않으면 반드시 실패한다.**
   ①(`이 정보를 확인한 시각` 0건)과 ②는 유지된다.
6. **T25-67 ② 가 여전히 통과하는 이유를 알고 있어라.** 그 검사는 `usage-meta" data-tooltip`
   (닫는 따옴표 포함) 패턴이다. 새 만료 줄은 `class="usage-meta usage-stale-note" data-tooltip=`
   이라 매칭되지 않는다. **우연이 아니라 의도다** — 신선 경로의 `usage-meta` 는 여전히 툴팁이
   없어야 하고(결정 UT1), 그 단정은 살아 있어야 한다.
7. **`hub/install.sh` 에 `settings.json`·`install-statusline` 문자열을 넣지 마라.** 소유권 원칙의
   기계적 강제를 T25-73 이 역방향으로 검사한다. 이 파일에서 바뀌는 것은 **안내 문구 1줄**뿐이다.
8. **`/hub install` 2단계는 1단계 실패와 무관하게 실행한다.** 훅 설치 실패(파싱 오류)와 상태줄
   등록은 독립 사건이다. 다만 사용자가 "훅만"이라고 답했으면 2단계 자체를 건너뛴다(결정 ON4).
9. **기존 파이썬 테스트 N34·N35 는 반드시 함께 고쳐야 한다.** 둘 다 `usage is None` 을 단정한다 —
   R-B 이후 그 값은 `is_stale=True` 인 샘플이다. **테스트를 고치지 않으면 구현이 옳아도 빨간불이
   뜬다**(반대로, 고치는 것을 잊으면 이 변경이 의도대로 됐는지 확인할 창구가 사라진다).
10. **`file://` 하위 호환.** 옛 `hub.html` 에는 `is_stale` 필드가 없다 → `usage.is_stale` 이
    `undefined`(falsy) → 신선 경로로 그려진다. 안전하며, 별도 기본값 처리를 넣지 않는다.

---

## 테스트 계획

### 파이썬 단위 테스트 (`tests/hub/`)

**신규 — `tests/hub/test_hub_usage.py` 에 `MarkStaleUsageSampleTest`**

| # | 케이스 | 기대 |
|---|--------|------|
| U1 | 나이 4시간 59분, 리셋 미래 | `is_stale is False`, **반환값이 원본과 동일**(불필요한 복제 없음) |
| U2 | 나이 정확히 5시간 | `is_stale is True`(경계 포함 — 기존 case15 와 같은 경계 규칙) |
| U3 | 나이 5시간 1분 | `is_stale is True` |
| U4 | 나이 1분(신선) + 세션 리셋 시각이 이미 지남 | `is_stale is True`(롤오버 단독 사유, 결정 EX2) |
| U5 | 신선 + `session_resets_at_ms is None`(모름) | `is_stale is False` — 모름을 롤오버로 단정하지 않는다(기존 n22 규칙 재확인) |
| U6 | `now_ms < sampled_at_ms`(시계 역전) | `is_stale is False` |
| U7 | 원본 불변성 | 입력 `UsageSample` 의 `is_stale` 이 호출 후에도 `False`(frozen + `replace` 가 새 객체를 만든다) |

**개정 — `tests/hub/test_hub_collect.py` `CaptureForSnapshotTest`**

| # | 현재 단정 | 변경 후 |
|---|----------|---------|
| N32(정상 캡처) | usage 값 검증 | **`usage.is_stale is False` 단정 추가** |
| N33(구형 캡처, 퍼센트 없음) | `usage is None` | **무변경** — 경계 EX1(보여줄 값 없음) |
| **N34(6시간 지난 캡처)** | `usage is None` | **`usage is not None and usage.is_stale is True`** + 경고 0건 유지 |
| **N35(세션 창 롤오버)** | `usage is None` | **`usage.is_stale is True`** + 경고 0건 유지 |
| N30·N31·N36·N43 | — | **무변경**(파일 없음·스위치 off·파싱 실패·찢긴 멀티바이트는 전부 여전히 `None`) |

**신규 — 두 건**

| # | 대상 | 단정 |
|---|------|------|
| U8 | `_capture_for_snapshot` | 만료 캡처인데 주간 리셋 시각이 미래면 **`resets` 가 그대로 실린다**(결정 EX8) |
| U9 | `hub_model.snapshot_content_key` | `is_stale` 만 다른 두 `HubSnapshot` 의 키가 **서로 다르다**(결정 EX4 의 기계적 고정 — 이 테스트가 없으면 "만료됐는데 화면이 안 바뀐다"는 회귀를 아무도 못 잡는다) |

> **순수성 유지 확인**: 새 함수 `mark_stale_usage_sample` 은 파일시스템·시각에 닿지 않는다
> (`now_ms` 를 인자로 받는다) → T25-10(순수 모듈에 `open(`/`Path(`/`os.` 흔적 금지) 통과.

### `tests/run.sh` — 기존 단정에 대한 영향 (전수 확인)

| 검사 | 판정 | 근거 |
|------|------|------|
| T25-1·2(`HUB_FILE_COUNT`, 설치 파일 수) | 영향 없음 | 파일 추가 없음. `hub/install.sh` 는 문자열 1줄만 |
| T25-21(루트 `install.sh` 에 `hub` 0건) | 영향 없음 | **루트** 스크립트다. 우리는 `hub/install.sh` 를 고친다 |
| T25-23·39(`--uninstall` 순서) | 영향 없음 | 제거 절차 무변경 |
| T25-10(순수 모듈에 파일시스템 흔적 없음) | 영향 없음 | 새 함수도 순수 |
| T25-29(구형 팔레트 3색 부재) | 영향 없음 | `--muted`·`--attention` 기존 토큰만 |
| T25-31(README 의 사용량 출처 토큰) | 영향 없음 | 토큰 유지 |
| T25-33(`usageEl.innerHTML` 부활 금지) | 영향 없음 | `usageBodyEl.innerHTML` 만 쓴다(기존과 동일) |
| **T25-34(`role="progressbar"` 등 a11y 3토큰)** | **주의** | `renderUsageBar` 를 남겨야 통과(GOTCHA 4) |
| T25-41(초기화 시각 4토큰 + `세션 진행 중에만 갱신`) | 영향 없음 | `renderUsageResetRow`·`usage-reset` 유지, `USAGE_CYCLE_NOTE` 는 **신선 경로에 그대로** 남는다 |
| T25-42·64(문서 토큰) | 영향 없음 | 해당 토큰 유지 |
| T25-44(`title="` 0건 + 툴팁 계약 8토큰) | 영향 없음 | 새 툴팁도 `data-tooltip` 이다. `MutationObserver`·`data-tooltip` 토큰은 오히려 늘어난다 |
| T25-54(hub_usage 캡처 토큰 3종) | 영향 없음 | 해당 함수 유지 |
| **T25-56(`usage: UsageSample \| None = None` 완전 일치)** | **주의** | 필드 선언 줄을 건드리지 않으면 통과(GOTCHA 3) |
| T25-63·65·66·68·69·70 | 영향 없음 | 모달·glow·바깥 클릭·드래그·backdrop·애니메이션 무관 |
| **T25-67 ③(`usageBodyElForTooltipObserver` 0건)** | **깨진다 — 반전 대상** | R-B 가 복원한다(GOTCHA 5). ①②는 유지 |
| T22-*(전부) | 영향 없음 | `commands/dashboard.md` 자산과 무관 |

### `tests/run.sh` — 신규 검사

`test_hub_docs_and_constants`(T25) — `test_desc` 를 `(T25-1~T25-74)` 로, 1985행 주석 범위도 갱신.

| # | 대상 | 단정 |
|---|------|------|
| **T25-67 개정** | R5 ↔ R-B 경계 | ③을 **반전**: `usageBodyElForTooltipObserver` 가 **존재해야** 한다(결정 EX7 로 조건부 복원됨). 주석에 "R5 가 지웠고 R-B 가 조건과 함께 되살렸다"는 이력을 남긴다. ①(`이 정보를 확인한 시각` 0건)·②는 그대로 |
| **T25-71** | R-B 표시 + 툴팁 복원 | `hub_template.html` 에 `usage-stale-note`·`USAGE_STALE_TOOLTIP`·`usage-pct-empty`·`is_stale` 4토큰 존재 **AND** `tooltipDismissObserver.observe` 가 `#dzh-usage-body` 를 다시 관찰한다(GOTCHA 1 의 기계적 강제) |
| **T25-72** | R-B 파이썬 계약 | `hub_usage.py` 에 `is_stale: bool = False` 와 `def mark_stale_usage_sample` 존재. `hub_collect.py` 에 `mark_stale_usage_sample` 호출 존재 **AND** 역방향 — `_capture_for_snapshot` 범위(`def _capture_for_snapshot` ~ `# ---- 합성 ----`)에 `usage = None` 이 **0건**(만료 시 지우는 옛 경로가 되살아나지 않게) |
| **T25-73** | R-A 온보딩 + 소유권 원칙 | 정방향: `commands/hub.md` 의 `/hub install` 절 범위에 `install-statusline` 존재, `hub/install.sh` 의 "다음 단계" 줄에 `상태줄` 존재, `hub/README.md` 「빠른 시작」에 상태줄 언급 존재. **역방향(핵심)**: `hub/install.sh` 에 `settings.json` 0건 + `install-statusline` **단독 직접 호출 0건**(전제 1 의 기계적 강제). (구현 중 조정: 초판의 "`install-statusline` 0건" 문구는 기존 `--uninstall` 절차의 `uninstall-statusline` 호출이 부분 문자열로 항상 걸려 자기모순이었다 — 실제 구현은 "`install-statusline` 총 등장 수 == `uninstall-statusline` 등장 수" 비교로 같은 불변식을 강제한다) |
| **T25-74** | 문서 정합 | `hub/README.md` 사용량 패널 절에 `조회되지 않음` 설명 존재 **AND** 역방향 — "5시간보다 오래됐거나 … 패널 전체를 표시하지 않는다" 라는 **낡은 문장이 남아 있지 않다**(문서와 동작이 어긋난 채 방치되는 것을 막는다) |

### 수동 확인 목록 (자동화 불가)

| # | 절차 | 기대 |
|---|------|------|
| M1 | 깨끗한 환경에서 `hub/install.sh` → 안내대로 `/hub install` | 고지문 1회 → 훅 6개 + statusLine 이 **둘 다** 등록된다. 터미널 상태줄에 `세션 …% · 주간 …%` 가 뜬다 |
| M2 | `settings.json` 에 남의 `statusLine` 을 넣어 두고 `/hub install` | 훅은 설치되고 상태줄은 **거부** + 사유·대안(`usage_api_enabled`) 안내. 남의 값이 그대로 살아 있다 |
| M3 | `/hub install` 을 연속 두 번 | 두 번째는 `already_installed` 만 보고. `settings.json` 의 mtime 이 바뀌지 않는다 |
| M4 | `rate_limits.json` 의 `captured_at_ms` 를 6시간 전으로 손수 바꾸고 허브를 새로고침 | 패널이 **보이고** 퍼센트가 `—`, 하단에 `조회되지 않음 · 마지막 갱신 6시간 N분 전` |
| M5 | 그 줄에 마우스를 올린다 / Tab 으로 지나간다 | 툴팁이 뜬다. 다른 곳으로 옮기면 사라진다. **30초 틱이 지나도 고아 툴팁이 남지 않는다**(GOTCHA 1) |
| M6 | `session_resets_at_ms` 를 과거로 바꾸고 나이는 신선하게 유지 | 같은 "조회되지 않음" 화면(결정 EX2) |
| M7 | `rate_limits.json` 을 지우고 새로고침 | 패널이 **뜨지 않는다**(경계 EX1) |
| M8 | M4 상태에서 주간 리셋 시각을 미래로 둔다 | 주간 `초기화 …` 줄이 **그대로 보인다**(결정 EX8) |
| M9 | M4 상태에서 패널을 접는다 | 접힘 알약에 `조회되지 않음` 한 줄. 색이 강조색이 아니다 |
| M10 | 서버를 켜 둔 채 캡처를 5시간 경과 시점까지 방치(또는 시각 조작) | **새로고침 없이** 화면이 스스로 "조회되지 않음"으로 바뀐다(결정 EX4) |
| M11 | 라이트·다크 두 테마에서 M4 확인 | `—` 와 안내 줄이 두 테마 모두에서 읽힌다 |
| M12 | 세션을 한 번 돌린 뒤 허브 확인 | 패널이 정상(퍼센트+막대)으로 **복귀**한다 |

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 완료 기준 |
|---|------|----------|
| 1 | **R-B 파이썬** — `UsageSample.is_stale`, `mark_stale_usage_sample`, `_capture_for_snapshot` 3줄 | 신규 U1~U7 통과. **기존 N34·N35 개정** 후 `python3 -m unittest discover tests/hub` 전체 통과 |
| 2 | **R-B content_key 확인** — U8·U9 추가 | U9 가 만료 전이를 잡는다. 이 시점에 화면은 아직 패널을 숨긴다(`!usage` 가 아니라 `is_stale` 이 참인데 템플릿이 모른다 → **정상적인 중간 상태**) |
| 3 | **R-B 템플릿** — CSS 3줄 + 함수 3개 + 분기 + **옵저버 복원** + 상단 주석 | M4~M12 통과. T25-71 통과. **T25-34·41·44·56 회귀 없음** |
| 4 | **테스트 반전** — T25-67 ③ 개정 + T25-72 추가 | `bash tests/run.sh` 통과 |
| 5 | **R-A 절차·문구** — `commands/hub.md`·`hub/install.sh`·`hub/README.md` | M1~M3 통과. T25-73 통과. **T25-1·2·21·23·39 회귀 없음** |
| 6 | **문서 정합** — `hub/README.md` 사용량 절 정정 · 직전 PRP 2곳 「부분 대체됨」 표기 | T25-74 통과. `bash tests/run.sh` + 파이썬 테스트 전체 통과 |

순서 근거: **파이썬 → 템플릿 → 테스트 → 절차** 순이다. 파이썬이 먼저 끝나야 템플릿이 볼
데이터가 생기고, 마일스톤 2 에서 "중간 상태가 정상"임을 미리 못 박아 두면 구현자가 그 시점의
화면을 버그로 오해하지 않는다. R-A 는 파이썬과 완전히 독립이라 마지막에 몰아서 한다.

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| 1 | 만료 패널이 상시 떠 있어 "화면이 시끄럽다"는 반대 피드백 | 접으면 한 줄(`조회되지 않음`)이고, 접힘 상태는 `localStorage` 로 유지된다. 완전히 끄려면 `show_usage_panel:false` |
| 2 | 만료 표시가 오히려 "고장 났다"는 오해를 준다 | 툴팁이 **왜 + 어떻게**를 모두 담는다(결정 EX7). 색도 오류색(빨강)이 아닌 `--attention`(주의) |
| 3 | `is_stale` 전이가 `hub.html` 재작성을 유발 | **의도된 동작이다**(결정 EX4). 캡처 수명 동안 1회뿐이며 U9 가 그 성질을 고정한다 |
| 4 | 툴팁 옵저버 복원을 빠뜨려 고아 툴팁이 남는다 | GOTCHA 1 + T25-71 이 `observe` 복원을 기계적으로 강제 |
| 5 | `/hub install` 이 상태줄까지 건드리는 것에 거부감 | 고지문에 되돌리기 경로를 명시하고, "훅만" 응답 분기를 절차에 넣었다(결정 ON4). 승인 항목 2 로 올린다 |
| 6 | 남의 `statusLine` 을 쓰는 사용자가 사용량 패널을 못 쓴다 | 기존 제약이며 R-A 가 만든 것이 아니다. 대안(`usage_api_enabled`)을 **실패 보고에 명시**해 처음으로 안내 창구를 만든다(결정 ON5) |
| 7 | 기존 파이썬 테스트 2건을 고치는 것이 "테스트를 맞춰 통과시키는" 안티패턴처럼 보인다 | N34·N35 는 **의도적으로 바뀐 동작**을 검사하던 테스트다. 삭제가 아니라 **새 기대값으로 개정**하고, 그 기대값이 요구의 핵심(만료 시 값이 살아남는다)을 직접 단정한다 |
| 8 | 만료 판정이 서버 시각에 의존해 시계가 뒤틀린 환경에서 오작동 | 기존 두 판정 함수가 이미 시계 역전을 방어한다(U6 이 그 성질을 재확인) |

---

## 검토했으나 채택하지 않은 대안

1. **R-A 를 `hub/install.sh` 에서 처리** — 결정 ON1 에서 3가지 근거로 기각(소유권 원칙·사전 동의
   없는 전역 변경·`--dry-run` 의미 파괴).
2. **`/hub setup` 새 서브커맨드 신설**(설치+훅+상태줄+서버 기동을 한 번에) — **거부(YAGNI).**
   `/hub install` 과 역할이 겹치고, 커맨드가 하나 늘면 문서·테스트·보고 형식이 모두 늘어난다.
   지금 필요한 것은 **기존 명령 하나가 한 단계를 더 하는 것**뿐이다.
3. **`install_hooks()` 안에 statusLine 등록 병합** — 결정 ON2 에서 5가지 근거로 기각.
4. **`/hub off` 가 statusLine 도 제거** — **거부.** 훅만 끄려는 사용자가 상태줄까지 잃는다.
   비대칭을 이름(`uninstall-hooks`)이 정직하게 드러내는 편이 낫다.
5. **R-B 를 `usage_state: "fresh"|"stale"|"absent"` 3상태 열거로** — **거부.** `"absent"` 는
   `usage=None` 과 같은 말이라 표현이 중복되고, 불가능 조합이 타입에 생긴다(결정 EX3-B).
6. **만료 시 마지막 퍼센트를 흐리게 표시** — **거부(승인 항목 3 으로 재확인).** 낡은 숫자가
   현재값으로 오해될 위험이 실용 가치보다 크다(결정 EX6).
7. **클라이언트가 5시간 만료를 스스로 재판정** — **거부.** `USAGE_MAX_SAMPLE_AGE_MS` 가 파이썬과
   JS 두 곳에 생겨 같은 규칙의 출처가 둘이 된다(결정 EX9).
8. **만료를 `warnings` 로 띄운다** — **거부.** `warnings` 는 수집 실패·계약 불일치처럼 **사용자가
   고쳐야 할 이상**을 위한 창구다. "세션을 안 돌렸다"는 정상 상태이며 경고가 아니다.
9. **캡처가 없을 때도 "조회되지 않음" 패널을 띄운다** — **거부.** 설치하지 않은 기능을 광고하는
   UI 가 된다. 그 문제는 R-A 가 온보딩에서 푼다(결정 EX1).

---

## 사용자 승인이 필요한 결정

### 승인 항목 1 — R-A: "첫 설치"를 **`/hub install` 단계**로 해석한다 (결정 ON1)

사용자 표현은 "hub 첫 설치 시"였다. 설계는 이를 **`hub/install.sh` → `/hub install` 온보딩 흐름
전체**로 읽고, 등록 지점을 `/hub install` 에 둔다. 근거는 `settings.json` 소유권 원칙(문서 3곳에
박힌 전제)과 "전역 설정 변경에는 고지 후 동의"라는 이 저장소의 일관된 자세다. `hub/install.sh` 는
**안내 문구 1줄**만 바뀐다.
**대안**: `hub/install.sh` 가 직접 등록 — 원칙 개정이 필요하고 `--dry-run` 의 의미가 깨진다.

### 승인 항목 2 — R-A: 고지·확인은 **한 번**, "훅만" 선택지를 남긴다 (결정 ON4)

훅 고지와 상태줄 고지를 한 화면에 묶어 확인 1회로 받는다(온보딩 마찰 최소화). 상태줄을 원하지
않으면 사용자가 "훅만"이라고 답해 2단계를 건너뛸 수 있고, 나중에 `/hub statusline off` 로도
되돌릴 수 있다.
**대안**: 확인을 두 번 받는다(마찰 증가, 대신 동의 단위가 분명해진다).

### 승인 항목 3 — R-B: 만료 시 **마지막 퍼센트를 보여주지 않는다** (결정 EX6)

퍼센트 자리를 `—` 로 두고 막대를 그리지 않는다. 낡은 숫자를 흐리게라도 남기면 스크린샷·곁눈질
에서 현재값으로 오해될 수 있고, 그 오해를 피하려는 것이 원래 숨김(결정 U3)의 이유였다.
**대안**: `43%` 를 흐리게 + "낡음" 표식(정보량은 늘지만 오해 위험도 늘어난다).

### 승인 항목 4 — R-B: **세션 창 롤오버도 같은 "조회되지 않음"** 으로 묶는다 (결정 EX2)

사용자는 "5시간이 지나 낡은" 경우를 말했지만, 롤오버(세션 리셋 시각이 이미 지남)도 화면에서는
같은 현상이고 사용자가 할 행동도 같다. 두 판정을 하나로 접지 않으면 "어떨 땐 사라지고 어떨 땐
남는" 설명 불가능한 화면이 된다.
**대안**: 롤오버는 기존대로 숨긴다(요구 문언에는 더 충실하지만 화면이 비일관해진다).
