# 허브 우선 진입 · 모달/플로팅 · 카드 · 사용량 패널 상호작용 정리 (PRP)

> 요구 8건: R1 모달 내 플로팅 숨김 · R2 허브 우선 열기 · R3 작업중 카드 glow ·
> R4 사용량 패널 바깥 클릭 접기 · **R5 패널 내 툴팁 제거** · **R6 기존 탭 재사용** ·
> **R7 드래그 전용 순서 변경 + 라이브 이동** · **R8 모달 depth·경계**

| 항목 | 값 |
|------|-----|
| 대상 | `commands/dashboard.md`(절차 문서 + 생성 템플릿) · `hub/bin/hub_template.html`(허브 화면) |
| 브랜치 | `main` (HEAD `5d4ed5b`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md) → [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md) → **이 문서** / 플로팅은 [`dashboard-pip-floating.md`](./dashboard-pip-floating.md) |
| 워크플로우 경로 | **전체 경로** (9개 파일 + `init` 절차의 결정적 분기 2개 + 기능 1개 제거) |
| 규모 | **Medium** — 신규 0개 / 수정 9개 파일. 허브 템플릿 순증 약 +35 / −55줄, 대시보드 템플릿 +5줄, 절차 문서 별도 |
| 새 외부 의존성 | **없음** (바닐라 CSS/JS · 새 파이썬 모듈 없음 · 새 CLI 서브커맨드 없음 · `osascript` 는 macOS 기본 제공 도구다 — 설치물이 아니다) |
| **Python 변경** | **없음** — R2 는 이미 존재하는 `hub.py server-status --json` 계약을 **소비만** 한다. R6 은 절차 문서 + `osascript`. 근거는 「영향 범위 · 미영향」 |
| **승인 상태** | **승인됨(2026-08-13, 개정 2)** — 항목 1~9 전부 확정: 1(`/hub.html`)·2(로컬 서버 유지)·3(pulse 채택)·4(영속화)·5(캡처 절대 시각 버림)·6(Chrome·Safari 만)·7(키보드 순서 변경 제거 확정)·8(blur 미채택)·9(/hub 비대칭 수용) |

### 개정 이력

| 개정 | 내용 |
|------|------|
| 초판 | R1~R4 설계. 승인 항목 1~4 제시 |
| 개정 1 (2026-08-13) | 항목 1(`/hub.html`)·2(로컬 서버 유지)·4(영속화) 확정. 항목 3 은 사용자가 **pulse 선택** → 결정 D3 개정. T22-99 에 `isEmbedded` 식별자 제약 추가 |
| **개정 2 (2026-08-13)** | **요구 R5~R8 통합.** 결정 코드는 두 글자를 쓴다(**UT**/**TR**/**DG**/**MD**) — 기존 PRP 들이 단일 문자 A~Z 를 이미 거의 다 소진해, 새 그룹을 단일 문자로 붙이면 다른 문서의 결정과 충돌한다. 불변식 **H1″ → H1‴** 개정(R7 이 `#dzh-live` 를 제거한다) |

---

## 요구사항 요약

허브(`/hub`)와 프로젝트 대시보드(`/dashboard`)가 각각 완성된 뒤 드러난 **상호작용 어긋남 8건**을
고친다.

초판 4건 — (1) 허브가 프로젝트 대시보드를 모달(iframe)로 띄우는데, 그 안에 대시보드 단독 화면용
플로팅 버튼이 그대로 떠서 좁은 모달의 내용을 가린다. (2) `/dashboard init` 은 허브가 이미 켜져
있어도 프로젝트 대시보드 탭을 따로 여는데, 사용자는 여러 프로젝트를 함께 보는 허브를 진입점으로
쓰고 싶다. (3) 허브 카드가 3열로 늘어난 뒤 "지금 작업중인 프로젝트"를 상태 배지로만 구분해서
훑어 찾기 어렵다. (4) 사용량 패널을 접으려면 제목 줄을 정확히 다시 눌러야 한다 — 바깥을 눌러
닫는 보편적 동작이 없다.

개정 2 의 4건 — **(5)** 사용량 패널 안에서 마우스를 올릴 때마다 툴팁이 떠서 시끄럽다. **(6)** 브라우저
열기가 매번 새 탭을 만들어, 같은 대시보드/허브 탭이 세션마다 쌓인다. **(7)** 카드 순서 변경이 방향키
경로까지 갖고 있어 조작 수단이 둘로 갈려 있고, 드래그 중에는 **카드 자체가 움직이지 않아** 어디에
놓이는지 알 수 없다. **(8)** 모달이 배경과 depth 차이가 없고 경계선이 잘 보이지 않는다.

여덟 요구는 모두 **표시·진입·조작 경로**에 관한 것이다. 데이터 계약(`HubSnapshot`, `#dzh-data`,
`/dashboard` DOM 갱신 맵, `rate_limits.json` 포맷)은 한 글자도 바뀌지 않는다.

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 세션을 시작하면 (이미 열려 있던) 허브 탭 하나에서
> 시작해 작업중인 프로젝트를 바로 찾고, 카드를 눌러 진행을 또렷한 모달로 보고, 카드는 잡아서
> 원하는 자리로 끌어다 놓고, 화면은 필요할 때만 말을 걸었으면 좋겠다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | 허브 모달로 열린 대시보드에 `#dz-pip-btn`·`#dz-pip-hint` 가 **보이지 않는다** | 수동 M1 |
| S2 | 같은 대시보드를 단독 탭(`http://localhost:8791/dashboard.html`)에서 열면 플로팅이 **그대로 동작한다** | 수동 M2 |
| S3 | 모달 안 대시보드가 여전히 5초마다 스스로 갱신된다(플로팅 숨김이 폴링을 죽이지 않는다) | 수동 M3 |
| S4 | 허브 서버가 켜진 상태에서 `/dashboard init` 을 하면 **허브 페이지**가 열리고 포커스를 받는다 | 수동 M4 |
| S5 | 허브가 꺼져 있거나 미설치면 `init` 의 브라우저 열기 동작이 **변경 전과 정확히 같다** | 수동 M5·M6 |
| S6 | `init` 보고에 허브 URL과 프로젝트 대시보드 단독 URL이 **둘 다** 있다 | 수동 M4 |
| S7 | `state === 'working'` 카드만 테두리 glow(은은한 pulse 포함)를 갖고, 라이트·다크 두 테마에서 모두 보이며, `prefers-reduced-motion: reduce` 에서는 pulse 없이 정적 glow 만 남는다 | 수동 M7 |
| S8 | 사용량 패널이 펼쳐진 상태에서 패널 밖(빈 배경·카드 등)을 클릭하면 접히고, 새로고침 후에도 접힌 채다 | 수동 M8 |
| S9 | 제목 줄 클릭으로 펼치는 동작이 바깥 클릭 리스너 때문에 즉시 되접히지 **않는다** | 수동 M9 |
| **S11** | 사용량 패널 안 어디에 마우스를 올려도 툴팁이 **뜨지 않는다**. 패널 밖 툴팁(새로고침·티어 배지·칩 등)은 그대로 동작한다 | 수동 M13 |
| **S12** | 같은 URL 탭이 이미 열려 있을 때 `init` 을 다시 실행하면 **새 탭이 생기지 않고** 그 탭이 앞으로 온다(macOS · Chrome/Safari) | 수동 M14 |
| **S13** | 탭을 못 찾거나 macOS 가 아니거나 권한이 거부되면 **기존 `open` 경로로 폴백**하고, 어떤 경우에도 `init` 이 중단되지 않는다 | 수동 M15·M16 |
| **S14** | 탭 탐색이 **꺼져 있는 브라우저를 실행시키지 않는다**(빈 창이 뜨지 않는다) | 수동 M17 |
| **S15** | 핸들을 잡고 끌면 **카드 자체가** 드래그 중 실시간으로 자리를 옮기고, 놓은 자리가 곧 최종 순서다 | 수동 M18 |
| **S16** | 드래그를 Escape 로 취소하거나 카드 밖에 놓으면 **원래 순서로 되돌아간다** | 수동 M19 |
| **S17** | 방향키·Home·End 로는 순서가 바뀌지 않고, 핸들은 Tab 순서에서 빠진다(마우스 전용임이 화면·접근성 트리에서 일치한다) | 수동 M20 |
| **S18** | 모달이 열리면 배경이 어두워지고 모달 테두리가 라이트·다크 두 테마에서 또렷하다 | 수동 M21 |
| S10 | `bash tests/run.sh` 전체 통과(T22-97~104 · T25-65~69 신규 포함) | 자동 |

---

## 확정된 전제 (재론하지 않는다)

1. **두 화면 모두 단일 정적 HTML + 바닐라 CSS/JS 다.** 프레임워크·CDN·빌드 단계·전처리기 금지.
   드래그 라이브 이동도 **손으로** 만든다(SortableJS 등 도입 금지).
2. **`commands/dashboard.md` 는 LLM 이 따라 실행하는 절차 문서다.** 새 분기는 **폐쇄 어휘 출력**
   (2번 포트 스캔의 `REUSE`/`FREE`/`NONE` 선례)으로만 만들고, 어휘 밖의 출력은 해석하지 않는다.
3. **자동 발행의 어떤 실패도 `init` 을 중단시키지 않는다.** 새로 추가되는 판정(3-a·4번 2-a)도 이
   원칙 안에 있다(실패 = 기존 동작 유지).
4. **허브는 읽기 전용이다.** 서버는 2경로 화이트리스트 + 프로젝트 대시보드 라우트뿐이고
   (`hub_server.ALLOWED_REQUEST_PATHS`), 쓰기 엔드포인트를 만들지 않는다.
5. **색각 안전 팔레트 유지.** 범주(카테고리) 색은 기존 토큰(`var(--accent)` 등)만 쓴다. T25-29 가
   금지하는 것은 구형 초록·빨강·주황 리터럴(`#1F8A70`·`#C2410C`·`#F59E0B`) 3개이며(확인함),
   **중성 검정 반투명 오버레이는 범주 색이 아니라 이 금지에 걸리지 않는다**(결정 MD2).
6. **불변식 H1‴**(개정 2, 아래 「불변식 H1″ → H1‴」). 사용자 상태를 가진 노드는 재렌더 대상 밖에
   두되, **드래그 중에는 DOM 이 일시적으로 순서의 진실이 된다**(결정 DG5).
7. **`osascript` 는 macOS 가 기본 제공하는 실행 파일이다.** 설치·의존성 추가가 아니다. 다만
   **Automation(TCC) 권한**이 필요하며 그 실패는 폴백으로 흡수한다(결정 TR5).

### 비목표 (이번 변경 범위 밖 — 명시적으로 건드리지 않는다)

| 항목 | 이유 |
|------|------|
| **세션 종료 후에도 허브 모달이 대시보드 파일을 열어 주는 동작** | **의도된 설계다.** 허브 서버가 디스크의 `.claude/dashboard.html` 을 직접 읽어 서빙한다(`hub_server._serve_project_dashboard` ← `hub_model.build_dashboard_registry`). 로컬 대시보드 서버(8791~8793)의 수명과 무관한 것이 이 구조의 장점이며, 이번 변경은 이 경로를 강화하는 방향이다 |
| `/dashboard serve` 의 브라우저 열기 | 사용자가 **로컬 서버를 명시적으로 요청**한 경로다. 그때 허브를 여는 것은 요청과 어긋난다(결정 F7). **단, R6 의 탭 재사용은 `serve` 에도 적용한다** — 「브라우저 열기」 절차를 공유하기 때문이다(결정 TR7) |
| `step`·`log`·`impl` 의 발행·브라우저 열기 | 지금도 하지 않는다(T22-77 이 문구를 고정한다). 유지 |
| 사용량 패널의 Escape 닫기 | 패널은 모달이 아니다. Escape 는 이미 툴팁 해제에 쓰인다(결정 Q6) |
| `working` 외 상태의 카드 시각 변경 | 요구가 없다. 상태 배지가 이미 4상태를 텍스트+글리프+색으로 구분한다 |
| 허브 카드 강제 즉시 갱신(`hub.py collect` 호출) | 허브 데몬의 소유 영역이다(결정 F8) |
| **`/hub` 커맨드(`hub_daemon.open_browser`)의 탭 재사용** | R6 은 `commands/dashboard.md` 의 절차만 고친다. `hub.py` 경로에 같은 규칙을 넣으면 **파이썬 변경**(`browser_open_command` 개조 + 단위 테스트 + T25-49 재작성)이 되어 이 PRP 의 "Python 무변경" 전제를 깬다. 비대칭이 남는 것을 **알고 수용**하며, 별도 요구가 되면 이 문서의 결정 TR1~TR6 을 그대로 옮긴다 |
| **Chrome·Safari 외 브라우저의 탭 재사용** | 결정 TR3. Edge·Brave·Arc 등은 앱 이름을 하나씩 열거해야 하는 무한 확장이다 → 폴백(새 탭) |
| **터치 드래그** | HTML5 DnD 의 구조적 한계다(결정 O5 가 이미 기각). Pointer Events 재구현은 100줄+ |
| **키보드로 카드 순서 바꾸기** | **R7 로 제거한다.** 사용자 명시 요구이며 WCAG 2.1.1 회귀임을 결정 DG2 에 기록한다 |
| `rate_limits.json` 의 `captured_at_ms` 필드 제거 | R5 로 **소비만** 끊긴다. 필드 자체는 남긴다(결정 UT3) |

---

## 영향 범위

### 수정 파일 (9개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_template.html` | ① `.card.card-working` CSS 3줄(R3) ② `renderProject` 클래스 방출 2줄(R3) ③ 바깥 클릭 접기 리스너 9줄(R4) ④ **패널 내 `data-tooltip` 2곳 제거 + `renderUsageResetRow` 시그니처 축소 + 툴팁 옵저버의 `#dzh-usage-body` 관찰 제거(R5)** ⑤ **방향키 이동 계열 6개 함수·리스너·`#dzh-live` 삭제, 핸들을 `<span>` 으로, 드래그 라이브 이동·`setDragImage`·`.card-dragging` 추가(R7)** ⑥ **`.modal` border/그림자 + `.modal::backdrop`(R8)** ⑦ 상단 계약 주석(H1‴) 갱신 | R3·R4·R5·R7·R8 의 전부 |
| `commands/dashboard.md` | ① 「템플릿 전문」에 CSS 규칙 1줄 + JS 2줄(R1) ② 템플릿 상단 주석 1줄 ③ 「갱신 모드」 표시 조건 1항목 ④ 「정적 요소 추가」 표 1행 신설 + 1행 보강 ⑤ 「자동 발행」에 `3-a` 절 신설 + 티어 표·직교 문장·5번 보고 표 갱신(R2) ⑥ **4번 「브라우저 열기」를 1 / 2-a(탭 재사용) / 2-b(OS 열기) / 3 구조로 개정(R6)** | R1·R2·R6 의 전부 |
| `tests/run.sh` | `test_dashboard_template_integrity` 에 T22-97~104, `test_hub_docs_and_constants` 에 T25-65~69 추가. `test_desc` 문자열 2곳 + 999행 주석의 범위 표기 갱신 | 새 불변식의 grep 회귀 방지 |
| `hub/README.md` | 「화면 배치」 2행(glow · 패널 툴팁 없음) · 「사용량 패널」 2행(바깥 클릭 · 캡처 시각 창구) · 「프로젝트 대시보드 모달」 3행(플로팅 숨김 · `/dashboard` 무수정 문장 정정 · 배경/경계) · **「카드 순서」 절 재작성(키보드 2행 삭제 → 라이브 이동·마우스 전용 2행)** | 문서 정합(T25-65·66·67·69 가 검사) |
| `docs/prps/hub-card-interactions-and-usage.md` | ① 결정 N4 에 "보강됨" 표기 ② **결정 O5 에 "대체됨" 표기**(키보드 이동·낭독·포커스 복원 폐기) ③ **R2 인터페이스 절의 `moveProjectPath`·`announceProjectPosition`·`keyboardMoveTargetIndex` 3항목에 "폐기됨" 표기** ④ 962·990행의 `#dzh-live` 언급에 "제거됨" 표기 | 두 설계 문서가 모순된 채 남지 않게(`hub-usage-collapse-and-grid.md` 가 결정 U5 를 "대체됨"으로 표기한 선례) |
| `docs/prps/dashboard-pip-floating.md` | 146행 「플로팅 가능 조건」에 "보강됨" 표기 1곳 | 같은 문장이 이 PRP 의 정본이다. 조건 자체는 바뀌지 않고 **표시 조건**이 더해진다 |
| **`docs/prps/hub-usage-reset-time-and-refresh.md`** | **561행 「표시 규칙」 표의 "캡처 시각 → 줄의 툴팁" 행에 "폐기됨(R5)" 표기** | 그 행이 R5 로 사라지는 유일한 정본 |
| **`docs/prps/hub-card-cleanup-and-usage-source.md`** | **415행 "부수 효과: `usage-meta` 툴팁 · `usage-reset` 툴팁 …" 문장에 "폐기됨(R5)" 표기** | 같은 이유 |
| **`docs/prps/hub-session-activity-and-tooltip.md`** | **312행 「교체 대상 4곳」 표의 `.usage-meta` 행에 "폐기됨(R5)" 표기** | 그 표가 툴팁 트리거 목록의 정본이다 |

### 신규 파일 (1개)

| 파일 | 역할 |
|------|------|
| `docs/prps/hub-first-entry-and-ui-signals.md` | 이 문서 |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/*.py` **전부** | **이 변경은 파이썬을 한 줄도 고치지 않는다.** R2 는 `hub.py server-status --json` 을 **소비**만 한다 — 그 출력 계약(`ServerStatus` = `record`·`alive`·`http_ok`…)은 이미 존재하고 `commands/hub.md` 118행이 이미 문서화한 공개 인터페이스다. R5 는 `rate_limit_resets.captured_at_ms` 의 **소비만** 끊는다(생산은 그대로 — 결정 UT3). R6 은 절차 문서 + `osascript`(파이썬 경로가 아니다). R1·R3·R4·R7·R8 은 브라우저 안 표시·조작 로직이다 |
| `hub/install.sh` | 배포 파일 수 불변(10개) → `HUB_FILE_COUNT` 그대로. T25-1 자동 대조 통과 |
| `commands/hub.md` | 서브커맨드 호출 규약과 `/hub status` 필드만 설명한다. `server-status --json` 의 계약은 이미 적혀 있고 새 필드를 만들지 않으므로 **수정하지 않는다** |
| `install.sh`(루트) | 커맨드 파일 수 불변 → `COMMANDS_FILE_COUNT` 그대로(T22-5). 허브를 모른다는 성질도 그대로(T25-21) |
| `tests/hub/*.py`, `tests/hub/fixtures/*.html` | 파이썬 무변경. 픽스처는 `/dashboard` 생성물이고 `test_hub_parse.py` 만 읽는다 — 이번 템플릿 증분은 `<style>` 과 `<script>` 안이라 티어 1 파서가 보는 `#dz-step-*`·`#dz-log` 구조에 닿지 않는다 |
| `CLAUDE.md`(루트·전역) | 워크플로우 규칙 변경 없음 |

---

## 요구 R1 — 허브 모달 안에서는 플로팅 UI 를 숨긴다

### 문제의 정확한 위치

허브 모달은 `<iframe id="dzh-modal-frame">` 의 `src` 를 `/project/<16자리 hex>/dashboard.html` 로
바꿔 프로젝트 대시보드를 그대로 띄운다(`hub_template.html` 1106~1115행). 그 문서는
`commands/dashboard.md` 「템플릿 전문」이 만든 파일이고, 그 안에는

```html
<button id="dz-pip-btn" type="button">플로팅</button>   <!-- position:fixed;top:18px;right:18px -->
<div id="dz-pip-hint" hidden></div>                      <!-- position:fixed;top:54px;right:18px -->
```

가 `.wrap` 바깥에 있다(1057~1058행). `position:fixed` 는 iframe 안에서 **iframe 뷰포트**를 기준으로
잡히므로, 모달 오른쪽 위에 버튼이 그대로 떠서 대시보드 내용을 가린다.

### 숨기지 않으면 생기는 실제 고장 (숨김이 "기능 상실"이 아닌 이유)

모달 안에서 이 버튼이 **눌리면** 다음이 일어난다.

1. 플로팅 진입은 `.wrap` 서브트리를 **복제가 아니라 이동**시킨다
   (`pipDocument.body.appendChild(wrap)`, 1198행 — 폴링이 계속 같은 노드를 갱신하도록 의도된 설계다).
2. 복귀 경로는 opener 문서가 살아 있다는 전제에 기대 있다
   (`win.addEventListener('pagehide', … document.body.insertBefore(wrap, pipButton))`, 1206~1208행).
3. 그런데 모달을 닫으면 허브가 iframe 을 `about:blank` 로 보낸다
   (`closeDashboardModal`, 1120~1123행 / `close` 이벤트, 1131행). **opener 문서 자체가 파괴된다.**
   → 되돌아갈 곳이 사라지고, 사용자는 대시보드 화면을 잃는다.

즉 모달 안 플로팅은 "쓸 수는 있지만 좁다" 수준이 아니라 **구조적으로 깨지는 조합**이다. 반면
같은 대시보드를 단독 탭(`http://localhost:8791/dashboard.html`)에서 열면 플로팅은 그대로 동작하고,
그 URL 은 `init` 보고에 항상 남는다(결정 F5) — **진입 경로가 유지되므로 기능 상실이 아니다.**

> 브라우저가 iframe 문서의 Document PiP 를 애초에 허용하는지는 환경마다 다르다(권한 정책 대상).
> 이 설계는 **그 판정에 의존하지 않는다** — 위 1~3 은 허용되는 환경에서 오히려 더 나쁘게
> 끝나므로, 결론은 어느 쪽이든 같다.

### 결정 B1 — 판정은 `window.self !== window.top`, 반영은 `<body>` 클래스 하나

```js
var isEmbedded = window.self !== window.top;
if(isEmbedded) document.body.classList.add('dz-embedded');
```

- `self !== top` 은 **WindowProxy 신원 비교**라 크로스 오리진에서도 예외를 던지지 않는다
  (`top.location` 을 읽으면 던진다 — 그건 하지 않는다).
- 반영을 `<body>` 클래스로 하는 이유: 이 파일에는 이미 **같은 관례**가 있다(`body.dz-pip` 이
  PiP 창 문서의 좁은 창 규칙 스코프다, 「정적 요소 추가」 표). 새 개념을 만들지 않는다.
- 대안(`pipButton.hidden = true`)을 쓰지 않는 이유: `#dz-pip-btn` 규칙에 `display` 가 없어 지금은
  동작하겠지만, 나중에 누가 그 규칙에 `display:inline-flex` 를 넣으면 **조용히 다시 보이게 된다**.
  CSS 로 못 박는 편이 회귀에 강하고, `#dz-pip-hint[hidden]{display:none}` 이 이미 같은 이유로
  존재한다.

### 결정 B2 — 임베드 판정은 **표시에만** 쓴다. 폴링·동기화는 한 줄도 분기하지 않는다

모달 안 라이브 갱신(5초 폴링)은
[`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md) 결정 N4 의 핵심 성질이다.
`if(isEmbedded) return;` 류의 조기 반환을 넣으면 그것이 통째로 죽는다. `isEmbedded` 의 사용처는
**위 두 줄이 전부**이며, 이 사실을 T22-99 가 기계적으로 고정한다.

### 결정 B3 — `disabled` 를 함께 걸지 않는다 (메커니즘 1개)

`display:none` 이면 클릭도 Tab 포커스도 불가능하다. 여기에 `pipButton.disabled = true` 를 더하면
같은 결과에 메커니즘이 둘이 되고, `reasonHint`(버튼이 비활성인 **영구 사유** 문자열, 1084행)의
의미가 "지원되지 않음"과 "여기서는 안 보여줌"으로 오염된다. **한 가지 수단만 쓴다.**

### 결정 B4 — `#dz-pip-hint` 도 함께 숨긴다

안내 줄만 남기는 안을 검토했으나 버렸다. 임베드 문맥에서 그 문구들이 **틀리기** 때문이다.

| 기존 문구 | 모달 안에서 틀린 이유 |
|-----------|----------------------|
| "플로팅 창은 로컬 서버에서만 동작합니다. `/dashboard serve` 를 실행하고 …" | 모달 안은 이미 http 다. 그리고 플로팅을 권해서는 안 된다 |
| "대시보드를 읽지 못했습니다. `/dashboard serve` 로 로컬 서버가 켜져 있는지 확인하세요." | 모달 안 폴링의 출처는 **허브 서버**다. `/dashboard serve` 는 무관하다 |

폴링 실패가 조용해지는 손실은 허용한다 — 모달 안 폴링이 실패하는 상황은 곧 허브 서버가 죽은
상황이고, 그때는 **허브 페이지 자신이** 새로고침 버튼을 경고색으로 바꿔 "화면이 멈췄다"를
이미 보여준다(`renderConnectionStatus`, `.refresh-btn.connection-lost`).

### R1 인터페이스 (템플릿 증분)

```css
/* 「템플릿 전문」 <style> — #dz-pip-hint[hidden] 규칙 바로 뒤 */
body.dz-embedded #dz-pip-btn,body.dz-embedded #dz-pip-hint{display:none}
```

```js
/* 「템플릿 전문」 <script> — var reasonHint = ''; 다음, if(!isServed){ 앞 */
var isEmbedded = window.self !== window.top;
if(isEmbedded) document.body.classList.add('dz-embedded');
```

배치 규칙(둘 다 필수):

- CSS 는 `#dz-pip-btn` 기본 규칙 **뒤**에 둔다(같은 값이라도 순서 의존을 만들지 않는다).
- JS 는 반드시 `if(!isServed){ … return; }`(1089행) **앞**에 둔다. 뒤로 옮기면 `file://` 로 열린
  문서가 iframe 에 박혔을 때 숨김이 통째로 사라진다 — 사용량 패널 토글이 같은 이유로 같은
  위치 제약을 갖는다(`hub_template.html` 975~977행의 GOTCHA 4 와 동일한 함정).

---

## 요구 R2 — 허브 서버가 살아 있으면 `init` 이 허브를 연다

### 현재 절차와 바뀌는 지점

```
1. 서버 가용성 확인 (python3)
2. 포트 스캔 → REUSE / FREE / NONE
   2-a. 기동
3. URL 확정과 포트 각인            ← "확정된 URL" 을 이 단계가 정한다
  ★3-a. 열기 대상 확정 (신설, R2)  ← 브라우저로 열 URL 만 따로 정한다
4. 브라우저 열기                    ← 열기 대상 URL 을 연다
   1. 세션의 URL 열기 도구(있으면)
  ★2-a. 이미 열린 탭 찾기 (신설, R6 · macOS 전용)
  ★2-b. OS 기본 열기 명령           ← 기존 2번
   3. 아무것도 하지 않는다
5. 보고                             ← 두 URL 을 모두 적는다
```

**용어를 둘로 쪼갠다** — 지금은 "확정된 URL" 하나가 표시·각인·열기를 겸하고 있어, 열기 대상만
바꾸려면 문장이 모호해진다.

| 용어 | 정의 | 쓰이는 곳 |
|------|------|----------|
| **대시보드 URL** | 3번이 티어 1·2 로 확정한 이 프로젝트 대시보드의 URL | 포트 각인 · 보고(항상) |
| **열기 대상 URL** | 3-a 가 정한, 실제로 브라우저에 여는 URL | 4번(2-a 의 탐색 대상이자 2-b 의 인자) |

### 결정 F1 — 허브 생존 판정은 `hub.py server-status --json` 하나로 한다

| 안 | 내용 | 판정 |
|----|------|------|
| **A (채택)** | `python3 ~/.claude/hub/bin/hub.py server-status --json` 의 `alive`·`http_ok`·`record.port` | 허브의 **공개 인터페이스**를 쓴다. 생존 판정식(하트비트 TTL = 수집주기×3, 하한 15초)이 `hub_model.server_heartbeat_ttl_ms` 한 곳에만 산다. `--json` 은 정확히 JSON 한 줄만 출력한다(`hub.py:_report`) |
| B | `~/.claude/hub/server.json` 직접 읽기 | **거부.** 그 파일에는 `pid`·`port`·`started_at_ms` 만 있고 생존 정보가 없다. 살아 있는지 알려면 `server_heartbeat` mtime + config 의 수집 주기 + TTL 배수를 절차 문서가 다시 구현해야 한다 → 계약이 두 곳으로 갈라진다 |
| C | 포트 프로브 | **거부.** 포트를 알려면 config 를 먼저 읽어야 하고(=하드코딩 금지 위반), 열린 소켓이 "그게 허브다"를 증명하지 않는다 |

### 결정 F2 — 게이트는 `alive` **AND** `http_ok` **AND** `record.port` 세 조건 전부

- `alive`(하트비트) 만으로는 부족하다. 하트비트가 신선해도 `hub.html` 이 아직 없거나 지워졌으면
  그 URL 은 404 다 — `cmd_open` 이 검수 M1 에서 이미 겪은 함정이다(`hub.py:78~81`).
- `http_ok` 는 `_check_http_ok` 가 **실제로** `http://localhost:{config.server_port}/hub.html` 을
  GET 해 200 을 확인한 결과다(`hub_daemon.py:129~134`, 타임아웃 1초).
  → **200 을 받은 그 URL 을 그대로 열면 "열었더니 404" 가 구조적으로 불가능하다.**
- `record.port` 가 정수가 아니면(server.json 부재·손상) 열 곳을 모른다 → `NOHUB`.

> **엣지 케이스**: `http_ok` 는 `config.server_port` 를 찌르고 우리가 여는 것은 `record.port` 다.
> 서버 기동 후 `config.json` 의 포트를 바꾸면 둘이 갈린다. 그때 `http_ok` 는 **거짓**이 되어
> `NOHUB` 로 떨어지고 기존 동작이 유지된다 — 실패 방향이 항상 안전한 쪽이다.

### 결정 F3 — 열 URL 은 `http://localhost:{record.port}/hub.html`, 포트는 절대 하드코딩하지 않는다

`/` 와 `/hub.html` 은 둘 다 200 이다(`ALLOWED_REQUEST_PATHS`). `/hub.html` 을 고르는 근거 3개:

1. **`http_ok` 가 검증한 정확히 그 URL 이다**(결정 F2). `/` 를 열면 "확인한 것"과 "여는 것"이
   갈라진다.
2. `/hub` 커맨드(`hub.py cmd_open`, 86행)가 이미 사용자에게 주는 문자열과 **같다** → 저장소
   안에 허브 URL 표기가 하나만 존재한다.
3. **R6 의 탭 재사용이 정확 일치 비교이므로**(결정 TR4), 표기를 하나로 유지하는 것이 곧
   "탭이 실제로 재사용될 확률"이다. 개정 2 에서 이 근거는 **추측이 아니라 요구**가 됐다.

**포트는 3-a 의 출력에서만 온다.** 기본값 `8794` 를 `commands/dashboard.md` 에 적어 넣지 않는다
(`~/.claude/hub/config.json` 의 `server_port` 로 바뀔 수 있다). T22-101 이 `8794` 0건을 강제한다.

### 결정 F4 — 로컬 대시보드 서버(8791~8793) 기동과 포트 각인은 **그대로 유지한다**

허브를 열게 되었으니 로컬 서버는 필요 없다는 판단을 검토했고, **거부한다.** 근거 3개:

1. **플로팅의 유일한 진입점이다.** R1 로 모달 안에서는 플로팅이 사라지므로, 플로팅을 쓰려면
   `http://localhost:{포트}/dashboard.html` 단독 탭이 **반드시** 있어야 한다. 티어 2(`file://`)는
   플로팅이 원천적으로 불가능하다(「갱신 모드」).
2. **`log commit` 의 자동 종료가 각인에 의존한다.** `#dz-log` 의 `data-server-port` 가 비면
   `log commit` 이 서버를 끄지 못하고, 세션이 끝나도 서버가 남는다. 각인을 건너뛰는 순간
   "아무도 끌 수 없는 서버"가 생긴다(T22-81 이 각인 호출부를 지키는 이유가 정확히 이것이다).
3. **허브 경로와 서로 간섭하지 않는다.** 허브 모달은 디스크의 `.claude/dashboard.html` 을 허브
   서버가 직접 읽어 서빙하므로(`_serve_project_dashboard`) 로컬 서버의 유무·수명과 **무관**하다.
   유지 비용이 허브 경로에 아무 부작용을 주지 않는다.

> 그래서 이 요구는 "무엇을 띄우는가"가 아니라 **"무엇을 브라우저에 보여주는가"만** 바꾼다.
> 티어 판정(1/2), 기동, 각인, 실패 폴백은 전부 그대로다.

### 결정 F5 — 보고에는 **두 URL 을 모두** 적는다

허브를 열었더라도 대시보드 단독 URL 을 보고에서 빼지 않는다. 빼면 결정 F4-1(플로팅 진입점)이
문서상 사라져 아무도 그 URL 을 알 수 없게 된다. 보고 문구는 "플로팅 창은 이 단독 탭에서만
동작합니다"를 함께 달아 R1 과 연결한다.

### 결정 F6 — 실패는 전부 `NOHUB` 로 접는다 (기존 동작 정확히 유지)

| 상황 | 출력 |
|------|------|
| `~/.claude/hub/bin/hub.py` 부재(허브 미설치) | `NOHUB` |
| `python3` 부재 · 명령 자체 실패 · 타임아웃(10초) | `NOHUB`(명령이 실패했으므로 절차가 그렇게 본다) |
| JSON 파싱 실패 · 예상 필드 부재 | `NOHUB` |
| `alive`/`http_ok` 중 하나라도 거짓 | `NOHUB` |
| 위 어휘(`HUB {포트}` / `NOHUB`) 밖의 출력 | **추측하지 않고** `NOHUB` |

이 단계는 「자동 발행」의 실패 비차단 원칙 안에 있다 — 어떤 실패도 `init` 을 중단시키지 않고,
최악의 결과가 **변경 전과 완전히 같다.**

### 결정 F7 — 판정 시점은 3번(포트 각인) **뒤**, 4번(브라우저 열기) **앞**

- 2번(포트 스캔)보다 앞에 두면 "허브가 살아 있으니 로컬 서버는 건너뛴다"는 유혹이 생긴다 —
  결정 F4 가 그것을 거부했다.
- 3번보다 앞에 두면 이 판정의 실패가 각인 절차에 영향을 줄 여지가 생긴다. 각인은 `log commit`
  이 의존하는 유일한 창구이므로 **먼저 끝내 둔다.**
- `serve`·`step`·`log`·`impl` 은 이 판정을 하지 않는다. `serve` 는 사용자가 로컬 서버를 명시적으로
  요청한 경로라 프로젝트 대시보드를 여는 것이 요청과 일치한다.

### 결정 F8 — 허브 카드가 이 프로젝트를 반영하기까지의 지연은 **받아들인다** (GOTCHA)

허브 상주 서버는 `server_collect_interval_seconds`(기본 **5초**)마다 수집하고, 티어 1 판정과
`dashboard_key` 는 그 수집 결과에서 나온다(`build_dashboard_registry`). 방금 만든 대시보드가
카드로 보이기까지 최대 1주기 걸린다. 강제 수집(`hub.py collect`)을 부르지 않는 이유:

- 전경 수집은 `hub.html` 을 **다른 프로세스가** 덮어쓰는 경로다. 상주 서버의 `last_content_key`
  캐시와 어긋나 불필요한 재쓰기를 유발한다.
- 5초는 사용자가 브라우저 탭을 인식하고 시선을 옮기는 시간보다 짧다. 문제를 만들지 않는다.

### R2 인터페이스 (`commands/dashboard.md` 「자동 발행」 3-a 절 문안)

````markdown
### 3-a. 열기 대상 확정 — 허브가 살아 있으면 허브를 연다

> 3번이 확정한 것은 **대시보드 URL**(보고·각인용)이다. 이 단계는 **브라우저로 열 URL** 만
> 따로 정한다. 통합 허브(`/hub`) 서버가 살아 있으면 프로젝트 대시보드 대신 **허브 페이지**를
> 연다 — 허브에서 이 프로젝트 카드를 클릭하면 같은 대시보드가 모달로 열리므로, 여러
> 프로젝트를 함께 보는 화면이 진입점이 되는 편이 낫다.

Bash 1회. 셸이 변수 확장을 하지 않도록 `$` 를 쓰지 않는다(2번과 같은 관례).

```bash
python3 -c "
import json, os, pathlib, subprocess, sys
hub_py = pathlib.Path(os.path.expanduser('~/.claude/hub/bin/hub.py'))
if not hub_py.exists():
    print('NOHUB'); raise SystemExit
try:
    done = subprocess.run([sys.executable, str(hub_py), 'server-status', '--json'],
                          capture_output=True, text=True, timeout=10)
    status = json.loads(done.stdout)
    port = (status.get('record') or {}).get('port')
    alive = status.get('alive') and status.get('http_ok') and isinstance(port, int)
    print('HUB', port) if alive else print('NOHUB')
except Exception:
    print('NOHUB')
"
```

출력은 반드시 아래 둘 중 하나다. **다른 해석을 만들지 않는다.**

| 출력 | 열기 대상 URL |
|------|--------------|
| `HUB {포트}` | `http://localhost:{포트}/hub.html` — 허브 페이지 |
| `NOHUB` | 3번이 확정한 **대시보드 URL**(기존 동작) |

- **포트는 이 출력에서만 온다.** 허브 기본 포트를 이 문서에 적어 넣지 않는다 —
  `~/.claude/hub/config.json` 으로 바뀔 수 있다.
- 명령이 실패하거나(허브 미설치·`python3` 없음·타임아웃) 위 둘이 아닌 출력이 나오면
  **추측하지 말고 `NOHUB` 로 본다.** 이 단계의 어떤 실패도 `init` 을 중단시키지 않으며,
  실패하면 변경 전과 정확히 같은 동작이 남는다.
- **로컬 서버(2번)와 포트 각인(3번)은 이 판정과 무관하게 그대로 수행한다.** 허브 모달은 디스크의
  `.claude/dashboard.html` 을 허브 서버가 직접 읽어 서빙하므로 로컬 서버와 무관하고, 로컬 서버는
  여전히 (a) 플로팅 창(허브 모달 안에서는 쓸 수 없다) (b) 단독 탭 열람 (c) `log commit` 의 자동
  종료에 쓰인다.
- 허브가 이 프로젝트 카드를 반영하기까지 최대 1 수집 주기(기본 5초) 걸린다. **강제 수집을
  부르지 않는다** — 허브 상주 서버가 스스로 따라잡는다.
````

### R2 가 함께 고쳐야 하는 기존 문장 (전수)

| 위치 | 현재 | 변경 |
|------|------|------|
| 티어 표 「얻는 것」 티어 1 | "5초 폴링 자동 갱신 + 플로팅 버튼 활성" | "… + 플로팅 버튼 활성(**단독 탭에서만** — 허브 모달 안에서는 숨는다)" |
| 「브라우저 열기는 티어와 직교한다」 문단 | "티어 1·2 어느 쪽이든 **확정된 URL** 에 대해 …" | "… 어느 쪽이든 **3-a 가 정한 열기 대상 URL** 에 대해 …" |
| 3번 절 제목·본문 | "URL 확정과 포트 각인" | 제목 유지(T22-81 앵커). 본문의 "확정된 티어에 따라" 문장에 "이 URL 이 **대시보드 URL** 이다" 1구 추가 |
| 4번 도입문 | "아래 순서로 한 번씩만 시도한다" | 앞에 "여기서 `<URL>` 은 3-a 가 정한 **열기 대상 URL** 이다." 1문장 추가 (R6 이 이 절을 더 개정한다) |
| 5번 보고 표 | 티어 1·2 / 브라우저 실패 3행 | **1행 신설**: 「허브를 연 경우(3-a `HUB`)」 → 허브 URL · "허브 페이지를 열었습니다 — 이 프로젝트 카드를 클릭하면 이 대시보드가 모달로 열립니다" · **대시보드 URL 도 함께**(플로팅 창은 이 단독 탭에서만 동작한다) |

---

## 요구 R3 — 작업중(working) 프로젝트 카드 테두리 glow

### 현재 상태

`renderProject`(743~768행)가 만드는 카드에서 상태는 **상태 배지 하나**로만 드러난다
(`renderStateBadge`, `.badge.state-working{background:var(--accent-ink);color:var(--bg)}`).
카드가 3열 그리드로 늘어난 뒤(결정 W1) 배지는 카드 안쪽의 작은 요소라, 화면을 훑어
"지금 돌고 있는 프로젝트"를 찾는 동작에 잘 걸리지 않는다.

### 결정 D1 — 신호는 **테두리 색 + 바깥 glow**, 기존 토큰만 쓴다

```css
.card.card-working{border-color:var(--accent);box-shadow:var(--shadow),0 0 14px -2px var(--accent)}
```

- `var(--shadow)` 를 **먼저 유지**한다 — 빼면 working 카드만 그림자를 잃어 평면이 된다.
- 두 번째 그림자는 `offset 0 0 / blur 14px / spread -2px` 다. 음수 spread 는 halo 를 카드 윤곽에
  붙여 인접 카드(gap 12px)로 번지지 않게 한다.
- 색은 `var(--accent)` 하나뿐이다 → 라이트(`#0072B2`)·다크(`#56B4E9`) 두 테마가 자동으로 성립하고
  새 토큰·새 리터럴이 없어 T25-29 도 그대로 통과한다.
- 규칙 위치는 `.card[data-dashboard-key]:hover` 바로 뒤다(`.card` 변종을 한 곳에 모은다).
- **호버와의 상호작용(확인함)**: `.card[data-dashboard-key]:hover` 는 `border-color` 만 같은 값으로
  덮고 `box-shadow` 를 건드리지 않는다 → 호버 중에도 glow 가 유지된다. 명시도는
  `.card.card-working`(0,2,0) < `:hover`(0,3,0) 이지만 값이 동일해 충돌이 없다.

### 결정 D2 — `state === 'working'` 만. 조건부 클래스 **1개**만 붙인다

```js
// working 만 강조한다 — stale 은 base_state 가 working 이어도 "소식 없음"이므로 강조하면
// 지금 돌고 있다고 오해하게 된다.
var stateClass = project.state === 'working' ? ' card-working' : '';
return '<div class="card' + stateClass + '"' + cardAttrs + '>'
```

- `card-state-{state}` 를 4상태 전부에 붙이는 안은 **거부한다** — 쓰이지 않는 클래스 3개를
  미리 만드는 추측성 확장이다(YAGNI). 필요해지면 그때 한 줄로 늘린다.
- `stale`(직전 working 포함)·`idle`·`done` 은 무변경. `stale` 을 강조하지 않는 이유는 그것이
  경고성 상태이고 이미 점선 테두리 배지로 구분되기 때문이다.
- **R7 과의 합성(개정 2)**: 드래그 중에는 `.card-dragging`(결정 DG6)이 함께 붙을 수 있다. 두
  클래스는 서로 다른 속성(`box-shadow`/`border-color` vs `opacity`)을 쓰므로 충돌하지 않는다.

### 결정 D3 — 은은한 pulse 를 넣는다 (개정 1 — 사용자 선택, 2026-08-13)

초판은 정적 glow 를 제안했다(`box-shadow` 는 컴포지터 친화 속성이 아니어서 상시 리페인트가
발생한다 — `rules/web/performance.md`). 승인 항목 3 에서 **사용자가 pulse 를 선택**해 개정한다.
리페인트 비용은 다음 세 가지로 제한한다:

| 완화 | 내용 |
|------|------|
| 느린 주기 | `2.6s ease-in-out infinite alternate` — 프레임당 변화량이 작다 |
| 대상 최소화 | working 카드에만 적용된다(동시 1~3장이 일반적) |
| `prefers-reduced-motion: reduce` | pulse 를 끄고 **정적 glow(결정 D1)로 낙착** — 신호 자체는 잃지 않는다 |

pulse 는 base `box-shadow`(결정 D1)를 유지한 채 blur·spread 만 좁은 범위(10px/-3px ↔ 18px/-1px)를
오간다 — 신호의 "존재"는 애니메이션과 무관하게 상시 성립하고, 애니메이션은 스캔 보조를 강화할
뿐이다. 최종 CSS(결정 D1 의 규칙을 대체하는 완성형):

```css
.card.card-working{border-color:var(--accent);box-shadow:var(--shadow),0 0 14px -2px var(--accent);animation:card-working-glow 2.6s ease-in-out infinite alternate}
@keyframes card-working-glow{from{box-shadow:var(--shadow),0 0 10px -3px var(--accent)}to{box-shadow:var(--shadow),0 0 18px -1px var(--accent)}}
@media (prefers-reduced-motion:reduce){.card.card-working{animation:none}}
```

**재렌더와의 상호작용(허용)**: 카드는 30초 틱마다 재생성되므로 애니메이션 위상이 그때마다
리셋된다. 2.6s 주기의 은은한 효과라 위상 리셋은 체감되지 않으며, 이를 막으려면 카드를 재렌더
대상 밖에 둬야 해(불변식 H1‴ 위반) 비용이 훨씬 크다.

### 결정 D4 — 접근성: glow 는 **중복 신호**다

색만으로 정보를 전달하지 않는다(WCAG 1.4.1) — 같은 카드의 상태 배지가 이미 **텍스트("작업중") +
글리프(●) + 색** 3채널을 갖는다. glow 는 그 위에 얹는 스캔 보조 신호이므로 새로운 접근성 부채를
만들지 않는다. `aria-*` 를 추가하지 않는다(보조기술은 배지 텍스트로 이미 같은 정보를 얻는다 —
중복 낭독을 만들지 않는다).

### 불변식과의 관계

카드는 `#dzh-app` 자식이라 **매 렌더 전멸·재생성**된다. `card-working` 은 사용자 상태가 아니라
**스냅샷에서 매번 다시 파생되는 값**이므로 재렌더 대상 **안**에 있는 것이 옳다 → 폴링·틱과
충돌하지 않고, 정적 노드 목록에 새 항목이 생기지 않는다. **R3 만으로는 H1″ 개정이 필요 없다**
(개정 2 의 H1‴ 는 R7 이 유발한다).

---

## 요구 R4 — 사용량 패널 바깥 클릭 시 접기

### 현재 상태

`#dzh-usage` 는 우하단 고정 패널이고, 접힘은 제목 줄(`#dzh-usage-toggle`) 클릭/Enter/Space 로만
전환된다(978~985행). 상태는 모듈 스코프 `isUsageCollapsed` + `localStorage['dzh-usage-collapsed']`
한 쌍이며 `applyUsageCollapsedState()` 가 클래스·`aria-expanded`·하단 여백을 한꺼번에 맞춘다.

### 결정 Q1 — `document` 위임 리스너 1개

`#dzh-usage` 자체는 정적 노드지만, **"바깥"의 대부분(프로젝트 카드)은 매 렌더 교체된다.**
카드에 리스너를 붙이면 첫 재렌더에 전부 죽는다 → 위임이 유일한 방법이다. 이 파일의 기존
관례와도 같다(툴팁·드래그·모달 전부 `document` 위임, 결정 T2·O7).

### 결정 Q2 — 접힘을 **영속화한다** (토글과 완전히 같은 경로)

```js
isUsageCollapsed = true;
persistUsageCollapsed(isUsageCollapsed);
applyUsageCollapsedState();
```

- 접힘 상태의 저장 키는 하나뿐이다(`dzh-usage-collapsed`). "이번 로드 동안만 접힘"을 도입하면
  같은 화면 상태가 두 종류가 되고 `applyUsageCollapsedState` 의 단일 진실이 깨진다.
- 실수로 접혔을 때의 비용이 낮다 — 되돌리기는 클릭 1회이고, 접혀도 한 줄 요약
  (`세션 43% · 주간 71%`)이 남아 정보 손실이 없다.

### 결정 Q3 — 패널이 `hidden` 이면 **아무것도 하지 않는다**

사용량 데이터가 없으면 패널은 `hidden` 이다(결정 U3·U4). 그 상태에서 아무 클릭이 접힘을
저장하면, 나중에 데이터가 생겼을 때 **사용자가 접은 적 없는 패널이 접힌 채로** 뜬다. 이건 실재
가능한 오작동이라 가드가 추측성 방어가 아니다.

### 결정 Q4 — `<dialog>` 안·배경 클릭은 "페이지 클릭"이 아니다

`showModal()` 중에는 배경이 inert 이므로, 그 클릭은 "패널 바깥 페이지를 눌렀다"가 아니다.
판정은 `event.target.closest('dialog')` **한 줄**로 한다.

- 배경(backdrop) 클릭은 `event.target === dialog` 이므로 이 검사에 함께 걸린다
  (모달 IIFE 1127~1129행이 같은 성질을 이용한다).
- `#dzh-dashboard-modal` id 를 쓰지 않는 이유: 렌더 IIFE 가 모달 IIFE 를 몰라도 되게 유지한다
  (두 IIFE 의 독립성은 불변식 H1‴ 의 설계 의도다).

### 결정 Q5 — 티어 1 카드 클릭이 모달을 열면서 패널을 접는 것은 **수용한다**

카드는 패널 바깥이므로 두 리스너가 각자 규칙대로 동작한 결과다. 모달을 닫으면 패널은 접힌
채로 남는다. 카드만 예외로 빼면 "바깥이면 접힌다"는 규칙에 아무도 모르는 예외가 생긴다 —
**규칙을 단순하게 유지한다.** (모달이 열려 있는 동안의 클릭은 결정 Q4 가 이미 무시한다.)

### 결정 Q6 — Escape 로는 접지 않는다

패널은 모달이 아니고 포커스를 갇히지도 않는다. Escape 는 이미 툴팁 해제(423행)에 쓰인다 —
같은 키에 두 번째 의미를 붙이지 않는다. 요구에도 없다(비목표).

### R4 인터페이스 (템플릿 증분)

```js
/* 렌더 IIFE — usageToggleButton 클릭 리스너(985행) 바로 뒤, 드래그 리스너들 앞 */
// 패널 바깥 클릭으로 접는다(결정 Q1~Q5). 위 토글과 마찬가지로 이 리스너도 반드시
// `if(!isServed){ … return; }` 앞에 등록돼야 한다 — 뒤로 가면 file:// 모드에서 기능이
// 통째로 사라진다(GOTCHA 2).
document.addEventListener('click', function(event){
  if(isUsageCollapsed) return;                       // 이미 접혀 있으면 할 일이 없다
  if(usageEl.hidden) return;                         // 패널이 없는 화면에서 접힘을 저장하지 않는다(결정 Q3)
  if(event.target.closest('#dzh-usage')) return;     // 패널 안(토글 버튼 포함)은 토글 리스너 소관(GOTCHA 1)
  if(event.target.closest('dialog')) return;         // 모달·배경 클릭은 페이지 클릭이 아니다(결정 Q4)
  isUsageCollapsed = true;
  persistUsageCollapsed(isUsageCollapsed);
  applyUsageCollapsedState();
});
```

---

## 요구 R5 — 사용량 패널 안 툴팁 전부 제거

### 제거 대상 (전수 — 패널 안에는 이 둘뿐임을 확인했다)

| # | 위치 | 현재 문구 | 트리거 |
|---|------|----------|--------|
| ① | `renderUsageResetRow`(845~853행) | `이 정보를 확인한 시각: {formatTimestamp(captured_at_ms)}` | `.usage-reset` 줄(세션·주간 각 1개) |
| ② | `renderUsagePanel`(910~911행) | `{formatTimestamp(usage.sampled_at_ms)}` (절대 시각) | `.usage-meta` 줄 |

패널 밖 툴팁(`#dzh-refresh`·`#dzh-theme-toggle`·`#dzh-modal-close`·`.badge.tier`·`.agent-chip`·
`.card-drag-handle`·`file://` 안내)은 **그대로 둔다.** 요구는 "패널 안"에 한정된다.

### 결정 UT1 — 정보는 **버린다**. 텍스트로 승격하지 않는다

| 안 | 판정 |
|----|------|
| **A (채택) 그냥 버린다** | 패널에는 상대 시각(`마지막 갱신 3분 전`)이 **남는다** — 신선도 판단이라는 실사용 목적은 그것으로 충족된다. 절대 시각은 진단 영역에 이미 두 창구가 있다: `/hub status` 의 `rate_limit_capture_age_ms`·`usage_sample_age_ms`(둘 다 나이(ms)를 준다) |
| B `usage-meta` 텍스트에 절대 시각 병기 | **거부.** 요구의 방향(패널을 조용하게)과 반대다. 우하단 고정 패널의 폭(≤420px)에 문자열이 하나 더 붙어 줄바꿈 위험도 생긴다 |
| C 접힘/펼침에 따라 다른 창구 신설 | **거부(YAGNI).** 요구에 없는 UI 를 만든다 |

### 결정 UT2 — `renderUsageResetRow` 의 시그니처를 **줄인다** (고아 인자 금지)

```js
// 변경 전: renderUsageResetRow(resetsAtMs, capturedAtMs)
// 변경 후: renderUsageResetRow(resetsAtMs)
```

- 호출부(`renderUsagePanel`)의 `var capturedAtMs = resets && resets.captured_at_ms;` 한 줄도 함께
  제거한다 — 내 변경이 만든 고아는 치운다.
- `formatTimestamp` 는 **삭제하지 않는다**: `renderConnectionStatus`(922행)가 여전히 쓴다(확인함).

### 결정 UT3 — `rate_limit_resets.captured_at_ms` **필드 자체는 남긴다** (소비만 끊는다)

템플릿이 이 필드를 읽는 곳이 사라지지만 파이썬·JSON 계약에서는 지우지 않는다.

- 지우면 `hub_model.RateLimitResets`·`hub_usage`·`rate_limits.json` 포맷·`tests/hub/*.py`·문서가
  동시에 움직인다 — **요구는 "툴팁 제거"이며 소비 중단만으로 100% 충족된다.**
- 그 값은 파일 포맷의 일부이고 `same_capture_values` 의 비교 제외 대상으로 이미 의미가 있다
  (원래 있던 코드는 요청 없이 지우지 않는다).
- 결과적으로 "생산되지만 화면이 소비하지 않는 필드"가 하나 생긴다. **이 문장이 그 기록이다** —
  다음 검수가 "왜 안 쓰는 필드를 보내나"를 다시 묻지 않게 한다.

### 결정 UT4 — 툴팁 옵저버의 `#dzh-usage-body` 관찰을 **제거한다**

431~435행의 `tooltipDismissObserver` 는 `#dzh-app` 과 `#dzh-usage-body` 두 곳의 `childList` 를
감시해 "트리거 노드가 교체됐는데 포인터가 멈춰 있어 낡은 툴팁이 남는" 상황을 막는다(결정 T6).
R5 이후 `#dzh-usage-body` 안에는 트리거가 **하나도 없으므로** 그 관찰은 절대 유용하게 발화할 수
없다 → `usageBodyElForTooltipObserver` 선언과 `observe` 호출 2줄을 지운다.

- `#dzh-app` 관찰은 **그대로 둔다**(카드 안 티어 배지·칩이 여전히 트리거다).
- T25-44 가 요구하는 `MutationObserver` 토큰은 남는 관찰과 `tooltipTextRefreshObserver` 로 충족된다.
- 되돌릴 때의 지침: 패널 안에 다시 `data-tooltip` 을 넣으려면 이 관찰도 함께 되살려야 한다.

### R5 인터페이스 (변경 후 형태)

```js
// 초기화 예정 시각 한 줄의 HTML. 그릴 값이 없으면 빈 문자열.
// 툴팁은 R5 로 제거됐다 — 패널 안에서는 마우스를 올려도 아무 말도 걸지 않는다(결정 UT1).
// 캡처 시각은 /hub status 의 rate_limit_capture_age_ms 로 진단한다.
function renderUsageResetRow(resetsAtMs){
  var text = usageResetText(resetsAtMs, Date.now());
  if(text === null) return '';
  return '<div class="usage-reset">' + escapeHtml(text) + '</div>';
}
```

```js
// renderUsagePanel 안 — data-tooltip 없이
usageBodyEl.innerHTML = sessionBar + sessionResetRow + weeklyBar + weeklyResetRow
  + '<div class="usage-meta">' + meta + '</div>';
```

---

## 요구 R6 — 브라우저 열기 시 기존 탭 재사용

### 문제와 제약

`open "<URL>"`(macOS)·`xdg-open`(Linux) 은 **항상 새 탭**을 만든다. 세션마다 `init` 을 부르면 같은
허브/대시보드 탭이 쌓인다. macOS 에서 이미 열린 탭을 찾아 활성화하는 유일한 실용 경로는
**AppleScript(`osascript`)로 브라우저의 탭 목록을 순회**하는 것이다.

### 결정 TR1 — 별도 하위 단계(4번 2-a)로 넣고, 실패는 기존 경로로 폴백한다

「브라우저 열기」(4번)를 다음 구조로 개정한다. **1번(세션의 URL 열기 도구)과 3번(아무것도 하지
않는다)은 손대지 않는다.**

```
1. 세션에 URL 을 여는 도구가 있으면 그것을 쓴다                    ← 무변경(탭 활성화 지시 포함)
2. 없으면 OS 경로로 간다. SSH 세션이면 2-a·2-b 를 모두 건너뛴다.
   2-a. (macOS 만) 이미 열린 탭을 찾아 앞으로 가져온다 → FOCUSED 면 끝
   2-b. FOCUSED 가 아니면 기존 OS 기본 열기 명령(open / xdg-open)   ← 기존 2번 그대로
3. 둘 다 못 하면 아무것도 하지 않는다                              ← 무변경
```

- **SSH 가드는 2-a 에도 적용된다.** 원격 세션에서 원격 머신의 브라우저 탭을 조작하는 것도
  사용자가 보는 화면과 무관하다. 기존 `$SSH_CONNECTION` 문구(T22-75)를 2-a·2-b 공통 전제로
  끌어올린다.
- **재시도하지 않는다.** 2-a 는 한 번만 시도하고, 어떤 실패도 곧 2-b 로 간다(T22-76 의 원칙).

### 결정 TR2 — 출력은 폐쇄 어휘 3개

| 출력 | 의미 | 다음 행동 |
|------|------|----------|
| `FOCUSED` | 같은 URL 탭을 찾아 앞으로 가져왔다 | **끝.** 5번(보고)으로. `open` 을 부르지 않는다 |
| `NOTFOUND` | macOS 지만 그 URL 탭이 없다(또는 대상 브라우저가 안 떠 있다·권한 거부·스크립트 실패) | 2-b 로 |
| `UNSUPPORTED` | macOS 가 아니다 | 2-b 로 |
| 그 밖의 출력·명령 실패 | — | **추측하지 않고** 2-b 로 |

### 결정 TR3 — 대상 브라우저는 **Chrome·Safari 둘만**, 그리고 **실행 중일 때만** 본다

- Edge·Brave·Arc·Vivaldi 등 Chromium 계열은 AppleScript 사전이 Chrome 과 거의 같지만, 앱 이름을
  하나씩 열거하는 것은 끝이 없다. **둘만 지원하고 나머지는 폴백(새 탭)** 으로 둔다 — 최악의
  결과가 지금과 같으므로 안전한 축소다(승인 항목 6 에서 확장 여부를 묻는다).
- **`is running` 검사는 생략할 수 없다(치명적).** AppleScript 의 `tell application "X"` 는 X 가
  꺼져 있으면 **X 를 실행시킨다** — 탭을 찾으려다 빈 브라우저 창을 띄우는 최악의 부작용이
  된다. `application "X" is running` 은 실행시키지 않으므로 이것으로 먼저 걸러야 한다.
- 탐색 순서는 Chrome → Safari. 정확 일치라 오탐이 없어 순서는 성능(먼저 맞을 확률)만 바꾼다.

### 결정 TR4 — URL 매칭은 **정확 일치**(접두·포트 무관 일치 금지)

접두 일치를 **거부하는 결정적 이유**: 대시보드 URL 의 포트는 스캔 결과에 따라 8791~8793 중
하나이고, **다른 프로젝트가 다른 포트에서 자기 대시보드를 서빙하고 있을 수 있다.**
`localhost:*/dashboard.html` 같은 느슨한 일치는 **남의 프로젝트 탭을 앞으로 가져온다** — 조용히
틀리는 최악의 실패다.

- 비교는 브라우저가 돌려주는 `URL of tab` 문자열과 열기 대상 URL 의 **문자 그대로 일치**다.
- 정규화도 하지 않는다(끝의 `/` 보정조차 넣지 않는다) — 결정 F3 이 허브 URL 표기를 이미
  `/hub.html` 하나로 고정했고, 대시보드 URL 도 절차가 유일한 형태로 만든다. 정규화 규칙은
  없어도 성립하며, 넣으면 "어디까지 같게 볼 것인가"라는 판정이 새로 생긴다.
- 사용자가 손으로 `http://localhost:8794/` 를 열어 둔 탭은 매칭되지 않아 새 탭이 하나 생긴다.
  **수용한다** — 반대 방향(오탐)의 피해가 훨씬 크다.

### 결정 TR5 — Automation(TCC) 권한 실패는 조용히 폴백한다

`osascript` 가 다른 앱을 제어하려면 최초 1회 "Terminal 이(가) Google Chrome 을 제어하려고 합니다"
승인이 필요하다. 거부하거나 프롬프트를 무시하면 명령이 non-zero 로 끝난다 → `NOTFOUND` → 2-b.

- **보고(5번)에 최초 1회 안내 한 줄**을 넣는다(기존 "허용 목록 추가" 안내와 같은 자리):
  "탭 재사용을 쓰려면 최초 1회 자동화(Automation) 권한 승인이 필요합니다 — 거부해도 새 탭으로
  열리며 다른 동작에는 영향이 없습니다."
- 권한 상태를 미리 조회하지 않는다(그 API 자체가 또 다른 권한을 요구한다). **시도하고 실패를
  흡수하는 것이 결정적이다.**

### 결정 TR6 — `open -g` 금지는 유지되고, 활성화는 `activate` 로 한다

기존 단정(T22-94: `open -g` 문자열 0건)은 그대로다. 2-a 는 `open` 을 쓰지 않고 AppleScript 의
`set index of window to 1` + `activate` 로 창·앱을 앞으로 가져온다 — "기본이 곧 포커스"라는 기존
원칙과 방향이 같다.

### 결정 TR7 — 이 개정은 「브라우저 열기」 절차를 쓰는 **모든 호출자**에 적용된다

`init`(자동 발행)과 `serve` 5단계가 같은 절을 참조한다. 탭 재사용은 URL 이 무엇이든 옳은
동작이므로 호출자별 분기를 만들지 않는다 — 절차 문서에 분기가 늘면 결정성이 떨어진다.

### R6 인터페이스 (`commands/dashboard.md` 4번 2-a 절 문안)

````markdown
**2-a. (macOS 만) 이미 열린 탭을 찾아 앞으로 가져온다.** `uname -s` 가 `Darwin` 일 때만 의미가
있다. Bash 1회, 출력은 폐쇄 어휘 3개(`FOCUSED`/`NOTFOUND`/`UNSUPPORTED`) 중 하나다.
`{열기 대상 URL}` 만 채우고 나머지는 그대로 쓴다.

```bash
if [ "$(uname -s)" != "Darwin" ]; then echo UNSUPPORTED; else
osascript 2>/dev/null <<'APPLESCRIPT' || echo NOTFOUND
set targetURL to "{열기 대상 URL}"
if application "Google Chrome" is running then
  tell application "Google Chrome"
    repeat with theWindow in windows
      set tabIndex to 0
      repeat with theTab in tabs of theWindow
        set tabIndex to tabIndex + 1
        if URL of theTab is targetURL then
          set active tab index of theWindow to tabIndex
          set index of theWindow to 1
          activate
          return "FOCUSED"
        end if
      end repeat
    end repeat
  end tell
end if
if application "Safari" is running then
  tell application "Safari"
    repeat with theWindow in windows
      repeat with theTab in tabs of theWindow
        if URL of theTab is targetURL then
          set current tab of theWindow to theTab
          set index of theWindow to 1
          activate
          return "FOCUSED"
        end if
      end repeat
    end repeat
  end tell
end if
return "NOTFOUND"
APPLESCRIPT
fi
```

| 출력 | 다음 행동 |
|------|----------|
| `FOCUSED` | **끝이다.** 2-b 를 건너뛰고 5번(보고)으로 간다 — `open` 을 부르면 방금 앞으로 가져온 탭 옆에 중복 탭이 생긴다 |
| `NOTFOUND` · `UNSUPPORTED` · 그 밖의 출력 · 명령 실패 | 아래 **2-b** 로 간다 |

- **`is running` 검사를 지우지 마라.** `tell application` 은 꺼져 있는 앱을 **실행시킨다** — 탭을
  찾으려다 빈 브라우저 창이 뜬다.
- URL 비교는 **정확 일치**다. 포트를 무시하거나 접두 일치로 바꾸면 **다른 프로젝트의 대시보드
  탭**을 앞으로 가져온다(대시보드 포트는 8791~8793 중 하나로 프로젝트마다 다르다).
- 최초 1회 자동화(Automation) 권한 승인이 필요하다. 거부하면 `NOTFOUND` 가 되어 2-b 로 폴백하며
  **재시도하지 않는다.**
````

---

## 요구 R7 — 카드 이동은 드래그 전용 + 드래그 중 카드가 실제로 움직인다

### R7-① 제거 대상 (전수 나열 — 이 목록이 구현 체크리스트다)

| # | 위치(현재 행) | 대상 | 처리 |
|---|--------------|------|------|
| 1 | 274 | `<div id="dzh-live" class="sr-only" aria-live="polite"></div>` | **삭제** |
| 2 | 46~47 | 상단 주석의 `#dzh-live` 언급 2곳(정적 노드 목록 + 설명 문장) | **삭제**(H1‴ 개정) |
| 3 | 489 | `DRAG_HANDLE_HINT = '드래그하거나 ←/→ 키로 순서 변경'` | **문구 교체** → `'드래그해서 순서 변경'` |
| 4 | 513 | `focusHandleAfterRenderPath` 선언 | **삭제** |
| 5 | 514 | `liveRegionEl` 선언 | **삭제** |
| 6 | 562~568 | `moveProjectPath()` | **삭제**(결정 DG4 로 호출자가 사라진다) |
| 7 | 570~574 | `announceProjectPosition()` | **삭제** |
| 8 | 583~590 | `keyboardMoveTargetIndex()` | **삭제** |
| 9 | 595~602 | `commitReorder(newDisplayOrder, focusPath)` | **시그니처 축소** → `commitReorder(newDisplayOrder)`. 본문의 `focusHandleAfterRenderPath = focusPath;` 삭제 |
| 10 | 604~617 | `restoreHandleFocusAfterRender()` | **삭제** |
| 11 | 971 | `render()` 안의 `restoreHandleFocusAfterRender();` 호출 | **삭제** |
| 12 | 1029~1044 | `keydown` 리스너(ArrowLeft/Right/Home/End) | **삭제** |
| 13 | 107 | `.card-drag-handle:focus-visible{…}` CSS | **삭제**(포커스 대상이 아니게 된다) |
| 14 | 729~733 | `renderDragHandle()` | **재작성**(결정 DG3) |
| 15 | `hub/README.md` 「카드 순서」 | 키보드 조작 1행 + 낭독 문구 | **삭제·교체** |
| 16 | `.sr-only` CSS(148~149) | — | **유지.** `renderAgentChip` 이 여전히 쓴다(확인함) |

**확인 결과: 위 어느 항목도 `tests/run.sh` 가 단정하지 않는다.** `dzh-live`·`aria-live`·
`moveProjectPath`·`keyboardMove`·`announce`·`aria-label` 를 전수 grep 했고 0건이다. T25-62 가
요구하는 토큰(`'dzh-project-order'`·`orderedProjectPaths`·`isReordering`·`card-drag-handle`)은
모두 **살아남는다**. T25-34 의 a11y 토큰은 `aria-expanded`·`aria-controls="dzh-usage-body"`·
`role="progressbar"` 3개뿐이라(확인함) 전부 무관하다. T25-30 의 `aria-hidden` 도 상태 배지
글리프에서 계속 등장한다. **따라서 삭제해야 할 기존 단정이 하나도 없다.**

### 결정 DG1 — 조작 수단을 **드래그 하나로** 합친다

키보드 경로는 "같은 일을 하는 두 번째 코드 경로"였고, 그것 때문에 포커스 복원·낭독 영역·인덱스
산술이라는 부수 장치 3개가 붙어 있었다. 하나로 줄이면 위 표 16항목 중 12개가 그냥 사라진다.

### 결정 DG2 — WCAG 2.1.1 회귀는 **사용자 명시 결정**이다 (기록)

키보드만으로는 카드 순서를 바꿀 수 없게 된다. 이는 WCAG 2.1.1(Keyboard) 관점의 **회귀**이며,
설계자가 권한 것이 아니라 **사용자가 명시적으로 요구한 축소**임을 여기에 기록한다.

남는 접근성 성질(축소되지 않는 것):

- **콘텐츠 접근성은 유지된다.** 프로젝트명 버튼(`button.project-name`)·모달·사용량 토글·헤더
  버튼은 전부 키보드로 도달·조작 가능하다. 잃는 것은 **재배치 기능** 하나다.
- 카드 순서는 "읽기 편의를 위한 시각적 배치"이며 정보 접근의 전제가 아니다(서버 활동순 기본
  정렬만으로도 모든 카드에 도달한다).
- 되돌리는 비용: 결정 O5 의 키보드 경로를 다시 붙이면 된다(이 문서와
  [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md) 결정 O5 에 원안이 남아 있다).

**대체 표기 대상**: `hub-card-interactions-and-usage.md` 결정 O5(제목이 "전용 드래그 핸들 + 키보드
이동")와 그 하위 3항목(키보드/낭독/포커스 복원), R2 인터페이스 절의 함수 3개, 962·990행의
`#dzh-live` 언급.

### 결정 DG3 — 핸들은 `<button>` 이 아니라 `<span aria-hidden="true">` 로 바꾼다

```js
// 드래그 전용 핸들(결정 DG1~DG3). 키보드로 아무 것도 할 수 없게 됐으므로 <button> 이 아니다 —
// 포커스는 받지만 Enter/Space 에 반응하지 않는 컨트롤은 보조기술 사용자에게 거짓말이 된다.
// aria-hidden 으로 접근성 트리에서 빼고, Tab 순서에서도 자연히 빠진다(span 은 기본 비포커스).
function renderDragHandle(project){
  return '<span class="card-drag-handle" draggable="true" aria-hidden="true" data-tooltip="'
    + escapeHtml(DRAG_HANDLE_HINT) + '">≡</span>';
}
```

- `type="button"`·`aria-label` 이 사라진다. `aria-label` 이 프로젝트명을 담고 있었으므로
  `escapeHtml(project.display_name)` 사용처가 이 함수에서 없어진다 → 인자 `project` 자체가
  불필요해지지만 **호출부 형태 유지를 위해 인자는 남기지 않는다**: 호출부(`renderProject`)도
  `renderDragHandle()` 로 함께 바꾼다(고아 인자 금지).
- CSS 는 대체로 그대로 쓸 수 있다(`.card-drag-handle` 이 이미 `background:transparent`·`border`·
  `display:inline-flex`·`cursor:grab` 을 명시한다). `:focus-visible` 규칙만 지운다.
- 드래그 시작 판정(`event.target.closest(DRAG_HANDLE_SELECTOR)`)은 그대로 동작한다 —
  `draggable="true"` 는 요소 종류와 무관하다.

### 결정 DG4 — 드래그 중 **DOM 을 직접 옮기고**, drop 은 **DOM 순서를 그대로 커밋**한다

이것이 R7 의 핵심이며, 동시에 가장 큰 **단순화**다.

| 단계 | 변경 전 | 변경 후 |
|------|---------|---------|
| `dragstart` | 핸들 기본 고스트 | `setDragImage(card, …)` 로 **카드 전체**가 고스트가 되고, 원본 카드에 `.card-dragging` 을 붙인다 |
| `dragover` | `preventDefault()` 만 | `preventDefault()` + **대상 카드 위치로 드래그 중인 카드 노드를 실제로 이동**(`insertBefore`) |
| `drop` | `currentCardOrder()` → `order.indexOf(target)` → `moveProjectPath(...)` 인덱스 산술 | `commitReorder(currentCardOrder())` — **DOM 이 이미 최종 순서다.** 인덱스 산술이 사라진다 |
| `dragend` | `isReordering=false; render()` | 동일(무변경) |

**라이브 이동의 방향 판정은 좌표를 쓰지 않는다.** 현재 DOM 순서만 본다:

```js
// 대상이 드래그 중인 카드보다 뒤에 있으면(=내가 앞) 대상 '뒤'로, 아니면 대상 '앞'으로 넣는다.
// 이 규칙은 기존 moveProjectPath(order, path, order.indexOf(target)) 의 의미와 정확히 같다
// (앞→뒤 이동은 제거로 한 칸 당겨진 만큼 대상 뒤가 되고, 뒤→앞 이동은 대상 앞이 된다).
// 좌표(중심점) 비교를 쓰지 않는 이유: 3열 그리드에서는 좌우와 상하가 섞여 "어느 축의
// 중심인가"라는 판정이 새로 생기고, 그 판정이 곧 튜닝 대상(버그 온상)이 된다.
var draggedIsBefore = !!(draggedCard.compareDocumentPosition(targetCard)
                         & Node.DOCUMENT_POSITION_FOLLOWING);
app.insertBefore(draggedCard, draggedIsBefore ? targetCard.nextSibling : targetCard);
```

**진동(oscillation)이 생기지 않는 이유 — 이 설계의 핵심 근거**: 이동 직후 포인터 아래 슬롯에는
**드래그 중인 카드 자신**이 놓인다(카드 높이가 `340px` 고정이고 그리드 트랙 폭도 균일해서 모든
슬롯 크기가 같다). 다음 `dragover` 는 `targetCard === draggedCard` 로 즉시 반환하므로 **한 번
움직인 뒤 고정점에 도달한다.** 별도의 "마지막 대상 기억" 상태가 필요 없다.

> **의존 관계 명시**: 이 성질은 `.card{height:340px}`(균일 슬롯)에 의존한다. 카드 높이를
> 가변으로 바꾸는 변경을 하면 진동 가능성이 되살아나므로 이 절을 다시 읽어야 한다. 실측에서
> 진동이 보이면 최소 처방은 `lastDragOverPath` 1개를 추가해 같은 대상 반복을 무시하는 것이다.

### 결정 DG5 — 드래그 중에는 **DOM 이 순서의 진실**이다 (불변식 H1‴ 의 새 조항)

지금까지 순서는 한 방향으로만 흘렀다: `storedProjectOrder` → `render()` → DOM. R7 은 드래그
구간에서 **그 방향을 뒤집는다**: DOM → `currentCardOrder()` → `commitReorder` → `storedProjectOrder`.

- 이것이 안전한 이유는 이미 있는 `isReordering` 게이트다(결정 O6) — 드래그 중에는 `render()` 가
  `#dzh-app` 을 건드리지 않으므로 폴링·틱이 라이브 이동을 덮어쓸 수 없다.
- **취소 경로가 자동으로 옳아진다**: Escape·카드 밖 드롭은 `drop` 을 발화시키지 않고 `dragend`
  만 발화한다 → `render()` 가 `storedProjectOrder` 로 다시 그려 **라이브 이동이 전부 되돌아간다.**
  별도 롤백 코드가 없다.
- `drop` 에서 "같은 카드에 놓았으면 무시" 하던 조기 반환(1012행)은 **제거한다** — 라이브 이동
  뒤에는 그 비교가 의미를 잃고(이미 옮겨져 있다), 조건 없이 현재 DOM 순서를 커밋하는 것이
  항상 옳다. 같은 자리에 놓으면 저장값이 그대로라 `persistProjectOrder` 가 같은 값을 한 번 쓸
  뿐이다(무해).

### 결정 DG6 — 원본 카드에 `.card-dragging` 을 붙인다 (놓일 자리를 보여 주는 신호)

```css
/* 드래그 중인 원본 카드 — 고스트(반투명 복제)와 구분되도록 낮춘다. 놓일 자리가 곧
   이 카드의 현재 위치다(결정 DG4 의 라이브 이동). */
.card.card-dragging{opacity:.55}
```

- `dragend` 가 `render()` 를 부르면 카드가 재생성되므로 **클래스 제거 코드가 필요 없다**(재렌더가
  청소한다). 예외 경로(드래그 중 탭 전환 등)에서도 `dragend` 는 반드시 발화한다.
- `opacity` 는 컴포지터 친화 속성이라 pulse(결정 D3)와 겹쳐도 추가 리페인트 부담이 없다.

### 결정 DG7 — `setDragImage` 의 오프셋은 포인터 상대 위치로 준다

```js
var cardRect = card.getBoundingClientRect();
event.dataTransfer.setDragImage(card, event.clientX - cardRect.left, event.clientY - cardRect.top);
```

핸들이 카드 왼쪽 위에 있으므로 오프셋은 작은 값이 되고, 고스트가 커서에 자연스럽게 매달린다.
`setDragImage` 는 호출 시점의 스냅샷을 쓰므로, 그 뒤 원본이 라이브 이동해도 고스트는 커서를
따라간다.

### R7 인터페이스 (변경 후 리스너 3개 요약)

```js
document.addEventListener('dragstart', function(event){
  var handle = event.target.closest(DRAG_HANDLE_SELECTOR);
  var card = handle && handle.closest('[data-project-path]');
  if(!card) return;
  draggedProjectPath = card.getAttribute('data-project-path');
  isReordering = true;
  card.classList.add('card-dragging');
  var cardRect = card.getBoundingClientRect();
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', draggedProjectPath);   // Firefox 필수
  event.dataTransfer.setDragImage(card, event.clientX - cardRect.left, event.clientY - cardRect.top);
});

document.addEventListener('dragover', function(event){
  if(draggedProjectPath === null) return;
  var targetCard = event.target.closest('[data-project-path]');
  if(!targetCard) return;
  event.preventDefault();                       // 없으면 drop 이 오지 않는다(기존 GOTCHA)
  var draggedCard = app.querySelector('.card-dragging');
  if(!draggedCard || targetCard === draggedCard) return;
  var draggedIsBefore = !!(draggedCard.compareDocumentPosition(targetCard)
                           & Node.DOCUMENT_POSITION_FOLLOWING);
  app.insertBefore(draggedCard, draggedIsBefore ? targetCard.nextSibling : targetCard);
});

document.addEventListener('drop', function(event){
  if(draggedProjectPath === null) return;
  if(!event.target.closest('[data-project-path]')) return;
  event.preventDefault();
  commitReorder(currentCardOrder());            // DOM 이 곧 최종 순서다(결정 DG4·DG5)
});
```

`dragend`(1023~1027행)는 무변경이다 — `draggedProjectPath = null; isReordering = false; render();`

---

## 요구 R8 — 모달의 depth·경계

### 현재 상태와 원인

```css
.modal{…;padding:0;border:0;border-radius:14px;background:var(--surface);…;box-shadow:var(--shadow)}
```

- `border:0` — 경계가 배경색 차이에만 의존한다. 다크 테마에서 `--surface #16202D` 와
  `--bg #0E1621` 은 밝기 차가 작아 윤곽이 흐리다.
- `box-shadow:var(--shadow)` 는 **카드용** 토큰이다(라이트 `rgba(19,51,91,.06)` — 매우 옅다).
  1040×760 짜리 큰 표면을 떠 보이게 하기엔 약하다.
- `::backdrop` 규칙이 **없다** → UA 기본값(Chrome 의 옅은 반투명)만 적용돼 배경이 거의 그대로
  보인다. depth 가 느껴지지 않는 가장 큰 원인이다.

### 결정 MD1 — 세 가지를 함께 바꾼다 (하나만으로는 부족하다)

```css
.modal{width:min(1040px, calc(100vw - 32px));height:min(760px, calc(100vh - 32px));
       padding:0;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--ink);
       box-shadow:0 24px 64px rgba(0,0,0,.35)}
.modal::backdrop{background:rgba(8,14,22,.55)}
```

| 요소 | 역할 |
|------|------|
| `::backdrop` 어두운 오버레이 | **depth 의 주역.** 배경을 눌러 모달 표면을 앞으로 띄운다. 라이트 테마에서는 `--surface #FFFFFF` 와 대비가 극대화되고, 다크에서도 `--surface` 가 눌린 배경보다 밝아진다 |
| `border:1px solid var(--line)` | **경계의 주역.** 테마 토큰이라 두 테마 모두에서 표면 대비 한 단계 진한 선이 된다. `box-sizing:border-box`(전역)라 크기 계산이 바뀌지 않는다 |
| 전용 그림자 | 보조. 어두워진 배경 위에서는 그림자 기여가 줄지만 라운딩 주변의 부드러운 이탈감을 만든다 |

### 결정 MD2 — 오버레이·그림자 색은 **토큰화하지 않고 인라인 리터럴**로 둔다

- **두 테마에서 같은 값을 원한다.** 모달 배경을 어둡게 덮는 것은 라이트·다크 공통 관례이며,
  테마 변수를 만들면 "다크에서는 얼마나 다르게?"라는 근거 없는 값이 하나 더 생긴다.
- `::backdrop` 은 top layer 에 그려지는 의사 요소로, `var()` 상속 동작이 브라우저 버전에 따라
  달랐던 이력이 있다. **리터럴이 결정적이다.**
- 사용처가 각각 1곳뿐이다 — 토큰은 2곳 이상에서 같아야 할 때 만든다(`.icon-btn` 을 클래스로
  묶은 결정 Y4 의 기준과 같다).
- **T25-29 와 충돌하지 않음(확인함)**: 그 검사가 금지하는 것은 색각 안전성이 없는 **범주 색**
  리터럴 `#1F8A70`·`#C2410C`·`#F59E0B` 3개다. `rgba(8,14,22,.55)`·`rgba(0,0,0,.35)` 는 중성
  검정 반투명이며 범주 구분에 쓰이지 않는다.

### 결정 MD3 — `backdrop-filter: blur()` 는 **넣지 않는다** (승인 항목 8)

- 모달이 열려 있는 동안에도 폴링(60초)·틱(30초)이 배경 `#dzh-app` 을 통째로 교체한다 → blur 는
  그때마다 배경 합성을 다시 해야 한다. 상시 비용이 있는 장식이다.
- 요구는 "depth 와 경계"이며 어두운 오버레이만으로 달성된다.
- 원하면 `.modal::backdrop` 에 `backdrop-filter:blur(2px)` 한 줄을 더하는 것으로 끝난다
  (승인 항목 8 에서 묻는다).

### 결정 MD4 — 닫기 애니메이션·transition 을 만들지 않는다 (YAGNI)

`::backdrop` 에 transition 을 걸면 `<dialog>` 의 즉시 `close()` 와 어긋나 사라지는 순간이
어색해지고, `@starting-style`·`allow-discrete` 같은 신문법을 끌어와야 한다. 요구에 없다.

---

## 불변식 H1″ → **H1‴** 개정 (개정 2)

`hub_template.html` 상단 주석(20~47행)의 개정 지점만 적는다. **정본은 이 절이다.**

| # | 변경 |
|---|------|
| 1 | 정적 노드 목록에서 **`#dzh-live` 를 제거**한다(R7 로 요소 자체가 사라진다). 남는 목록: `#dzh-usage`·`#dzh-usage-toggle`·`#dzh-theme-toggle`·`#dzh-tooltip`·`#dzh-dashboard-modal`(과 그 자식 전부) |
| 2 | 마지막 문장의 "`#dzh-live` 는 카드 순서 변경(R2)을 스크린리더에 알리는 aria-live 정적 영역이다" **삭제** |
| 3 | 조항 ②(드래그 중 재렌더 금지)를 **강화**한다: "드래그 중에는 다시 그리지 않는다 — `isReordering` 이 참이면 `render()` 는 즉시 반환한다. 그 사이 `dragover` 가 `#dzh-app` 자식의 **순서를 직접 바꾸며**(라이브 이동), 따라서 **드래그 구간에서는 DOM 이 저장 순서보다 앞서 있다.** `drop` 이 그 DOM 순서를 커밋하고, `dragend` 가 한 번 다시 그려 둘을 맞춘다. 취소·카드 밖 드롭은 `drop` 없이 `dragend` 만 발화하므로 재렌더가 라이브 이동을 자동으로 되돌린다" |
| 4 | 사용량 패널 조항에 **접힘을 바꾸는 경로가 둘**(토글 버튼 클릭 · 패널 바깥 클릭)이며 둘 다 같은 함수(`applyUsageCollapsedState`)와 같은 저장 키를 쓴다는 1문장 추가 |
| 5 | 사용량 패널 조항에 **패널 안에는 툴팁 트리거를 두지 않는다**(R5)는 1문장 추가 — 되살리려면 `tooltipDismissObserver` 의 `#dzh-usage-body` 관찰도 함께 되살려야 한다는 조건을 붙인다 |

---

## 데이터 모델 — 모듈 간 계약 (변경 요약)

**파이썬·JSON 계약 변경은 없다.** 소비·생산하는 계약은 전부 기존 것이다.

| 계약 | 방향 | 이번 변경에서의 역할 |
|------|------|---------------------|
| `hub.py server-status --json` → `dataclasses.asdict(ServerStatus)` | 소비(신규 소비자 1) | `record.port: int \| None` · `alive: bool` · `http_ok: bool` 세 필드만 읽는다. 필드를 **추가하지 않는다** |
| `HubSnapshot.projects[].state: "working"\|"idle"\|"stale"\|"done"` | 소비 | R3 의 클래스 방출 조건. 서버 계산식 무변경 |
| `localStorage['dzh-usage-collapsed'] = '1' \| (키 없음)` | 소비·생산 | R4 가 기존 키를 그대로 쓴다. 새 키를 만들지 않는다 |
| `localStorage['dzh-project-order'] = string[]` | 소비·생산 | R7 이 기존 키·형식을 그대로 쓴다. **쓰는 시점만** 바뀐다(drop 시 DOM 순서) |
| `HubSnapshot.rate_limit_resets.captured_at_ms` | **소비 중단** | R5. 필드는 남기고 화면이 읽지 않는다(결정 UT3) |

### 함수 시그니처 변경·삭제 (템플릿 JS)

| 함수 | 변경 |
|------|------|
| `renderUsageResetRow(resetsAtMs, capturedAtMs)` | → `renderUsageResetRow(resetsAtMs)` (결정 UT2) |
| `commitReorder(newDisplayOrder, focusPath)` | → `commitReorder(newDisplayOrder)` (결정 DG4) |
| `renderDragHandle(project)` | → `renderDragHandle()` (결정 DG3) |
| `moveProjectPath` · `announceProjectPosition` · `keyboardMoveTargetIndex` · `restoreHandleFocusAfterRender` | **삭제**(호출자 소멸) |
| `orderedProjectPaths` · `nextStoredProjectOrder` · `currentCardOrder` · `usageResetText` · `formatTimestamp` | **유지**(모두 사용처가 남아 있음 — 확인함) |

### 새로 생기는 DOM/CSS/절차 계약

| 이름 | 소유 파일 | 의미 |
|------|----------|------|
| `body.dz-embedded` | `commands/dashboard.md` 템플릿 | 이 문서가 iframe 안이다. 플로팅 버튼·안내 줄을 숨기는 CSS 스코프. 폴링·동기화와 무관 |
| `.card.card-working` | `hub/bin/hub_template.html` | 프로젝트 상태가 `working`. 데이터 파생이라 매 렌더 재계산 |
| `.card.card-dragging` | `hub/bin/hub_template.html` | 지금 드래그 중인 원본 카드. **드래그 중 이 노드를 찾는 셀렉터로도 쓰인다**(`app.querySelector('.card-dragging')`) — 표시와 식별을 겸하는 유일한 클래스이므로 지우지 말 것 |
| `.modal::backdrop` | `hub/bin/hub_template.html` | 모달 배경 오버레이 |
| 3-a 출력 어휘 `HUB {포트}` / `NOHUB` | `commands/dashboard.md` | 열기 대상 판정의 폐쇄 어휘 |
| 4번 2-a 출력 어휘 `FOCUSED` / `NOTFOUND` / `UNSUPPORTED` | `commands/dashboard.md` | 탭 재사용 판정의 폐쇄 어휘 |

---

## GOTCHA (구현 중 반드시 확인)

1. **바깥 클릭이 토글을 즉시 되접는 고전 버그.** 토글 버튼 클릭은 버튼(타깃) → `document`(버블)로
   전파되므로, `closest('#dzh-usage')` 가드가 없으면 "펼치자마자 접힌다". 이 파일에는
   `stopPropagation` 이 **0건**임을 확인했다(그래서 리스너 등록 순서에 의존하는 해법을 쓸 수 없고,
   써서도 안 된다).
2. **리스너 등록 위치(치명적).** R1 의 임베드 판정과 R4 의 바깥 클릭 리스너는 **둘 다**
   해당 파일의 `if(!isServed){ … return; }` **앞**에 있어야 한다. 뒤로 가면 `file://` 모드에서
   기능이 조용히 사라진다. `hub_template.html` 975~977행이 같은 함정을 이미 주석으로 남겼고,
   R4 는 T25-66 이 **줄 번호 비교로** 강제한다(T25-53 선례).
3. **T22-32 는 `requestWindow` 등장 횟수가 정확히 1 이어야 통과한다.** R1 의 문서 갱신(「갱신 모드」,
   「정적 요소 추가」 표, 템플릿 주석) 어디에도 `requestWindow` 라는 문자열을 쓰지 마라.
4. **T22-37 은 줄 번호 비교다.** `id="dz-updated"` 라는 리터럴을 템플릿의 `#dz-pip-btn` 마크업 줄
   **뒤쪽**에 새로 쓰면 통과 조건이 깨진다. 새 문장은 템플릿 앞(규격 절)에만 넣는다.
5. **T22-81 의 sed 범위 앵커.** 3-a 절을 넣어도 `/^### 3\. URL 확정과 포트 각인/,/^### 4\./` 범위
   안에 `[포트 각인]` 링크가 남아야 한다 → **3번 본문의 각인 링크를 3-a 로 옮기지 마라.**
   T22-94 의 `/^### 4\. 브라우저 열기/,/^### 5\./` 범위와 그 안의 '전면으로 올리는' 문구도 유지.
6. **`event.target.closest` 는 Element 를 전제한다.** 이 파일의 기존 리스너들이 이미 같은 전제로
   동작한다(1134행 등) — 새 가드를 도입하지 말고 관례를 따른다(일관성).
7. **`pipDocument.body.className = 'dz-pip'`(대입)** 은 클래스를 통째로 갈아치운다. 임베드와 PiP 는
   동시에 성립할 수 없으므로(임베드면 버튼이 없다) 실무 영향은 없다 — 하지만 나중에 이 대입을
   `classList.add` 로 바꾸려는 사람이 이 문장을 근거로 삼지 않도록, 여기서 "동시 성립 불가"를
   못 박아 둔다.
8. **3-a 는 `python3 -c` 안에서 `$` 를 쓰지 않는다.** 홈 디렉토리는 `os.path.expanduser('~')` 로
   푼다 — 셸 확장과 파이썬 리터럴이 섞이면 절차가 비결정적으로 읽힌다(2번 스캔과 같은 관례).
9. **`init` 에 Bash 가 최대 2회 늘어난다**(3-a · 4번 2-a). 최초 1회 권한 프롬프트가 뜰 수 있다 —
   기존 보고 문구(허용 목록 추가 안내)가 이미 그 자리를 갖고 있고, R6 은 여기에 Automation 권한
   안내 한 줄을 더한다(결정 TR5).
10. **`tell application` 은 꺼진 앱을 실행시킨다(R6 최대 함정).** `application "X" is running`
    검사를 빼면 탭을 찾으려다 **빈 브라우저 창이 뜬다.** 2-a 스크립트에서 이 두 줄을 절대
    지우지 마라. T22-103 이 `is running` 존재를 단정한다.
11. **`FOCUSED` 뒤에 `open` 을 부르면 중복 탭이 생긴다.** 2-a 성공 시 2-b 를 **반드시** 건너뛴다.
    절차 문서에 "끝이다" 를 명시하고, T22-103 이 그 문구를 고정한다.
12. **URL 정확 일치를 느슨하게 만들면 남의 프로젝트 탭이 앞으로 온다.** 대시보드 포트는
    8791~8793 중 하나이고 프로젝트마다 다르다(결정 TR4). 접두 일치·포트 와일드카드 금지.
13. **`heredoc` 안에서 URL 을 치환한다.** `<<'APPLESCRIPT'`(따옴표 있는 구분자)는 셸 확장을
    막으므로, 오케스트레이터가 `{열기 대상 URL}` 자리에 **문자열을 직접 써 넣어야** 한다.
    구분자의 따옴표를 지우면 URL 안의 `$`·백틱이 셸에 해석될 여지가 생긴다.
14. **`dragover` 에서 `preventDefault()` 를 빼면 `drop` 이 아예 오지 않는다**(기존 GOTCHA 3 유지).
    라이브 이동 코드를 넣으면서 이 호출을 조건문 뒤로 밀지 마라 — `targetCard` 를 찾은 직후,
    이동 판정 **앞**에서 부른다.
15. **드래그 중 노드 이동은 `isReordering` 게이트가 있어야만 안전하다.** 게이트를 지우거나
    `render()` 가 드래그 중에 돌면 드래그 중인 노드가 파괴돼 드롭이 취소된다(결정 O6·DG5).
16. **`.card-dragging` 은 표시와 식별을 겸한다.** `app.querySelector('.card-dragging')` 이 드래그
    중인 카드를 찾는 유일한 경로다 — 클래스명을 바꾸면 두 곳을 함께 고쳐야 한다.
17. **카드 높이 균일성에 의존한다.** 진동이 없는 근거가 `.card{height:340px}` 이다(결정 DG4).
    그 값을 가변으로 바꾸는 변경은 이 절을 다시 읽어야 한다.
18. **T25-44 는 `title="` 0건을 요구한다.** R8 의 모달 CSS·R5 의 정리에서 `title=` 속성을
    실수로 넣지 마라(툴팁은 `data-tooltip` 뿐이다).

---

## 테스트 계획

### 기존 자동 검사에 대한 영향 (전수 확인 결과)

| 검사 | 판정 | 근거 |
|------|------|------|
| T22-2(6 셀렉터) · T22-3·4 | 영향 없음 | 셀렉터·배지·라디오 무변경 |
| T22-27(`:root` 색 토큰 완전 일치) | 영향 없음 | R1 은 `display:none` 뿐 — 새 색 토큰 없음 |
| T22-29(`if(!isServed){` + 판정식) | 영향 없음 | 분기 자체를 유지하고 **그 앞에** 두 줄을 넣는다 |
| T22-31(PiP 기능 감지) | 영향 없음 | `hasPipSupport` 유지 |
| **T22-32(`requestWindow` 정확히 1회)** | **주의** | 문서 갱신에 그 단어를 쓰지 않으면 통과(GOTCHA 3) |
| T22-33·34(스타일 복사·복귀 경로) | 영향 없음 | PiP 흐름 무변경 |
| **T22-37(플로팅 UI 가 `.wrap` 바깥)** | **주의** | GOTCHA 4 준수 시 통과 |
| T22-38(`[id="dz-` 금지) | 영향 없음 | 새 코드는 `classList`·`getElementById` 만 쓴다 |
| T22-40·42·45(`body.dz-pip` 규칙·CSS 로만 숨김) | 영향 없음 | `dz-pip` 규칙 무변경. `dz-embedded` 도 **CSS 로만 숨기는** 같은 원칙을 따른다 |
| T22-68~70(자동 발행 절 제목·`file://`·`[자동 발행]` 링크) | 영향 없음 | 절 제목·링크·폴백 문구 유지 |
| T22-71·72(`REUSE`/`FREE`/`NONE`, 우선순위 문구) | 영향 없음 | 2번 무변경. 3-a·4번 2-a 는 **별도 어휘**를 쓴다 |
| T22-73(`--bind 127.0.0.1` ≥2회, `0.0.0.0` 부재) | 영향 없음 | 기동 명령 무변경 |
| T22-74(실패 비차단) · **T22-75(SSH 가드)** · **T22-76('재시도하지 않고')** · T22-77 · T22-79 | 영향 없음(**주의**) | 문구를 그대로 남긴다. R6 이 4번을 재구성하므로 **`SSH_CONNECTION` 과 '재시도하지 않고' 를 지우지 않도록** 구현 체크리스트에 넣는다 |
| **T22-81(각인 호출부 3범위)** | **주의** | GOTCHA 5 준수 시 통과 |
| T22-82~87(`log commit` 자동 종료) | 영향 없음 | 결정 F4 로 각인·종료 경로 무변경 |
| **T22-94(4번 범위의 '전면으로 올리는', `open -g` 부재)** | **주의** | 4번을 재구성하되 1번 항목의 '전면으로 올리는' 문구를 **그대로 남긴다**. 2-a 는 `activate` 를 쓰므로 `open -g` 는 여전히 0건(결정 TR6) |
| T25-1(`HUB_FILE_COUNT`) · T22-5(`COMMANDS_FILE_COUNT`) | 영향 없음 | 파일 수 불변 |
| T25-8(허브 파일에 `8791` 부재) | 영향 없음 | 허브 파일을 건드리지 않는다. 역방향으로 **dashboard.md 에 `8794` 부재**를 T22-101 로 새로 고정 |
| **T25-29(구형 팔레트 3색 부재)** | 영향 없음(확인함) | 금지 리터럴은 `#1F8A70`·`#C2410C`·`#F59E0B` 뿐. R8 의 `rgba(8,14,22,.55)`·`rgba(0,0,0,.35)` 는 걸리지 않는다 |
| T25-33(`usageEl.innerHTML` 부활 금지) | 영향 없음 | R4·R5 는 `usageBodyEl.innerHTML` 만 쓴다(기존과 동일) |
| **T25-34(a11y 토큰 3개)** | 영향 없음(확인함) | 토큰은 `aria-expanded`·`aria-controls="dzh-usage-body"`·`role="progressbar"` 뿐 — R5·R7 이 지우는 것과 겹치지 않는다 |
| T25-30(`STATE_GLYPH`·`aria-hidden`) | 영향 없음 | 상태 배지 글리프가 유지되고, R7 의 핸들도 `aria-hidden` 을 쓴다 |
| **T25-41(초기화 시각 토큰 4개)** | 영향 없음 | `usage-reset`·`rate_limit_resets`·`초기화 `·`renderUsageResetRow` 는 R5 이후에도 전부 남는다(사라지는 것은 `data-tooltip` 속성뿐) |
| **T25-44(`title="` 0건 + 툴팁 계약 8토큰)** | **주의** | `data-tooltip` 은 패널 밖에 다수 남고, `MutationObserver` 도 `#dzh-app` 관찰·`tooltipTextRefreshObserver` 로 남는다 → 통과. `title=` 을 새로 넣지 않을 것(GOTCHA 18) |
| T25-51·52(클라이언트 필터·칩 토큰) | 영향 없음 | 해당 함수 무변경 |
| T25-53(`STALE_SESSION_HIDE_AFTER_MS` 선언 순서) | 영향 없음 | 상수 선언 순서를 건드리지 않는다 |
| **T25-62(순서 토큰 4개)** | 영향 없음(확인함) | `'dzh-project-order'`·`orderedProjectPaths`·`isReordering`·`card-drag-handle` 4개 모두 R7 이후에도 존재. 금지 토큰 `stableSortedProjects` 도 여전히 0건 |
| **T25-63(모달 마크업 3토큰 + 테마 2상태)** | 영향 없음 | `<dialog id="dzh-dashboard-modal"`·`id="dzh-modal-frame"`·`.icon-btn` 는 R8 이 건드리지 않는다(변경은 `.modal` 규칙과 `::backdrop` 추가) |
| `tests/hub/*.py` (파이썬 단위 테스트) | 영향 없음 | **파이썬 무변경** |
| **삭제해야 하는 기존 단정** | **없음(전수 확인)** | `dzh-live`·`aria-live`·`moveProjectPath`·`keyboardMove`·`announce`·`aria-label`·`captured_at_ms`·`확인한 시각`·`usage-meta` 를 `tests/run.sh` 전체에서 grep 했고 관련 단정이 0건이다 → **R5·R7 의 삭제는 어떤 검사도 깨지 않는다** |

### 신규 자동 검사 (`tests/run.sh`)

`test_dashboard_template_integrity`(T22) — `test_desc` 를 `(T22-1~T22-104)` 로, 999행 주석 범위도 함께 갱신.

| # | 대상 | 단정 |
|---|------|------|
| T22-97 | R1 CSS | `body.dz-embedded #dz-pip-btn` 문자열 존재 (정방향) |
| T22-98 | R1 판정식 | `window.self !== window.top` 존재 (정방향) |
| T22-99 | R1 부작용 금지 | `grep -c isEmbedded` 가 **정확히 2줄**(선언 1 + 사용 1)이고 `if(isEmbedded) return` 이 **없다**(역방향 — 임베드 판정이 폴링을 죽이는 회귀를 막는다). 이 계수 때문에 `isEmbedded` 라는 식별자를 `dashboard.md` 의 산문·표·주석에 쓰면 안 된다 — 문서에서는 `body.dz-embedded` 또는 판정식으로 지칭한다(GOTCHA 3 과 같은 종류의 함정) |
| T22-100 | R2 절차 | 3-a 절 제목(`### 3-a. 열기 대상 확정`)·`NOHUB`·`server-status --json`·`열기 대상 URL` 4토큰 존재 |
| T22-101 | R2 포트 하드코딩 금지 | `commands/dashboard.md` 에 `8794` 가 **0건**(역방향, 결정 F3 의 기계적 강제) + 보고 표에 `모달` 문구 존재(결정 F5 의 두 URL 병기 유지) |
| **T22-102** | **R6 어휘·구조** | 4번 범위(`/^### 4\. 브라우저 열기/,/^### 5\./`)에 `FOCUSED`·`NOTFOUND`·`UNSUPPORTED`·`osascript` 4토큰이 모두 존재 |
| **T22-103** | **R6 최대 함정 2개(가장 값진 검사)** | ① `is running` 문자열 존재(GOTCHA 10 — 없으면 꺼진 브라우저를 실행시킨다) ② 4번 범위에 `2-b 를 건너뛰고` 또는 `끝이다` 문구 존재(GOTCHA 11 — 중복 탭 방지) |
| **T22-104** | **R6 매칭 규칙 역방향** | 4번 범위에 `URL of` 가 존재하고, 느슨한 매칭 흔적(`starts with`·`contains`)이 **0건**(결정 TR4 — 남의 프로젝트 탭 활성화 방지) |

`test_hub_docs_and_constants`(T25) — `test_desc` 를 `(T25-1~T25-69)` 으로 갱신.

| # | 대상 | 단정 |
|---|------|------|
| T25-65 | R3 | `.card.card-working{` 과 `card-working'`(JS 방출) 존재. `@keyframes card-working-glow` 와 `prefers-reduced-motion` 도 존재(개정 1 — pulse 와 접근성 분기는 반드시 함께). `hub/README.md` 「화면 배치」에 `작업중` 강조 설명 존재 |
| T25-66 | R4 | ① `closest('#dzh-usage')` 존재 ② `closest('dialog')` 존재 ③ **줄 번호 비교** — `closest('#dzh-usage')` 가 `if(!isServed){` 보다 앞(GOTCHA 2 의 기계적 강제, T25-53 선례) ④ `hub/README.md` 사용량 패널 절에 바깥 클릭 설명 존재 |
| **T25-67** | **R5 (역방향 중심)** | ① `이 정보를 확인한 시각` 이 **0건** ② `usage-meta" data-tooltip` 이 **0건** ③ `usageBodyElForTooltipObserver` 가 **0건**(결정 UT4) ④ 그럼에도 `renderUsageResetRow`·`usage-meta`·`data-tooltip`(패널 밖) 은 여전히 존재 ⑤ `hub/README.md` 에 캡처 시각 진단 창구(`rate_limit_capture_age_ms`) 언급 존재 |
| **T25-68** | **R7 (정·역 혼합)** | 정방향: `setDragImage`·`compareDocumentPosition`·`card-dragging`·`commitReorder(currentCardOrder())` 존재. 역방향: `keyboardMoveTargetIndex`·`announceProjectPosition`·`moveProjectPath`·`dzh-live`·`restoreHandleFocusAfterRender`·`ArrowLeft` 가 **전부 0건**. 문서: `hub/README.md` 「카드 순서」에 `←` 가 0건이고 '드래그' 설명이 존재 |
| **T25-69** | **R8** | `.modal::backdrop` 규칙 존재 + `.modal{` 규칙에 `border:1px solid var(--line)` 존재 + 구 `border:0` 이 `.modal` 규칙에서 **사라짐**. `hub/README.md` 모달 절에 배경 어두워짐 설명 존재 |

### 순수 로직 단위 테스트

새로 생기는 **순수 함수가 없다.** R7 은 오히려 순수 함수 1개(`moveProjectPath`)를 **없앤다** —
인덱스 산술을 DOM 순서 읽기로 대체하기 때문이다(결정 DG4). 따라서 `tests/hub/*.py` 에 추가할
파이썬 단위 테스트가 없고, 삭제할 것도 없다(그 함수는 애초에 JS 라 파이썬 테스트가 없었다).
이 사실을 명시해 "테스트를 빠뜨린 것"과 "테스트할 순수 로직이 없는 것"을 구분한다.

> **부수 효과(수용)**: 순서 계산 로직이 순수 함수에서 DOM 조작으로 옮겨가면서 자동 검증
> 가능성이 낮아진다. 대신 **검증 가능성의 총량은 늘어난다** — 화면에 보이는 것이 곧 커밋될
> 순서라서(결정 DG4) 수동 확인 M18·M19 가 이전보다 훨씬 직접적인 검증이 된다.

### 수동 확인 목록 (브라우저 실검증 — 자동화 불가)

| # | 절차 | 기대 |
|---|------|------|
| M1 | `/hub server start` → 허브에서 티어 1 카드 클릭 | 모달 안 대시보드에 플로팅 버튼·안내 줄이 **없다** |
| M2 | 같은 프로젝트에서 `http://localhost:8791/dashboard.html` 단독 탭 열기 | 플로팅 버튼이 보이고 눌리면 PiP 창이 뜬다 |
| M3 | M1 상태로 모달을 열어 두고 `/dashboard step 2 done` 실행 | 모달 안 화면이 5초 안에 스스로 갱신된다 |
| M4 | 허브 서버 켜진 상태에서 `/dashboard init "제목" "A\|B"` | **허브 페이지**가 열려 포커스를 받는다. 보고에 허브 URL + 대시보드 단독 URL 이 **둘 다** 있다 |
| M5 | `/hub server stop` 후 같은 `init` | 프로젝트 대시보드 URL 이 열린다(변경 전과 동일) |
| M6 | `~/.claude/hub` 를 임시로 옮기고(허브 미설치 재현) `init` | 변경 전과 동일. 오류·경고가 없다 |
| M7 | 작업중 세션이 있는 프로젝트를 라이트·다크 두 테마에서 확인. OS '동작 줄이기' 설정으로도 1회 | 그 카드만 테두리 glow + 은은한 pulse. 호버해도 유지. reduce motion 에서는 정적 glow |
| M8 | 패널 펼친 뒤 빈 배경 클릭 → 새로고침 | 접힌다. 새로고침 후에도 접힌 채다 |
| M9 | 접힌 패널의 제목 줄 클릭 | 펼쳐지고 **즉시 되접히지 않는다**(GOTCHA 1) |
| M10 | 사용량 데이터 없는 상태에서 아무 곳 클릭 → 데이터 생긴 뒤 새로고침 | 패널이 **펼쳐진 채** 뜬다(결정 Q3) |
| M11 | 모달을 열고 모달 안·배경 클릭 | 모달 뒤 패널의 접힘 상태가 바뀌지 않는다(결정 Q4) |
| M12 | 좁은 화면(390px)에서 M1·M8 반복 | 레이아웃 붕괴 없음 |
| **M13** | 사용량 패널의 막대·퍼센트·초기화 줄·갱신 줄에 각각 마우스를 올린다. 이어서 패널 **밖**(새로고침 버튼·티어 배지·서브에이전트 칩)에 올린다 | 패널 안에서는 **어디서도 툴팁이 뜨지 않고**, 패널 밖 툴팁은 전부 정상 |
| **M14** | 허브 탭을 열어 둔 채 `/dashboard init` 재실행 (Chrome, 그다음 Safari) | **새 탭이 생기지 않고** 기존 탭이 앞으로 온다. 창도 앞으로 온다 |
| **M15** | 그 URL 탭을 모두 닫고 `init` | 새 탭이 열린다(2-b 폴백). 오류 문구 없음 |
| **M16** | 자동화 권한 프롬프트에서 **거부**한 뒤 `init` | 새 탭이 열리고 `init` 은 정상 완료. 보고에 권한 안내 한 줄 |
| **M17** | Chrome·Safari 를 **모두 종료**한 상태에서 `init` | 탭 탐색이 브라우저를 **실행시키지 않는다**(빈 창 없음). 기본 브라우저로 새 탭만 열린다 |
| **M18** | 3열 상태에서 핸들을 잡고 다른 카드 위로 천천히 끈다 | **카드 자체가** 실시간으로 자리를 옮기고 다른 카드가 밀린다. 진동·깜빡임 없음. 놓으면 그 순서가 유지되고 새로고침 후에도 남는다 |
| **M19** | 드래그 중 Escape / 카드 밖(빈 여백·푸터)에 놓기 | **원래 순서로 되돌아간다**(결정 DG5) |
| **M20** | 핸들에 Tab 으로 도달 시도 · 카드에 포커스 두고 ←/→/Home/End | 핸들은 Tab 순서에 **없고**, 방향키로 순서가 바뀌지 않는다. 스크린리더가 핸들을 낭독하지 않는다 |
| **M21** | 라이트·다크 두 테마에서 모달을 연다 | 배경이 뚜렷하게 어두워지고 모달 테두리가 또렷하다. 배경 클릭으로 닫히는 동작은 그대로 |
| **M22** | 모달을 열어 둔 채 60초 이상 방치(폴링 2회) | 배경이 갱신돼도 오버레이·경계가 흐트러지지 않는다 |

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 완료 기준 |
|---|------|----------|
| 1 | **R4** (`hub_template.html` 9줄 + 주석) | M8·M9·M10·M11 통과. T25-66 통과 |
| 2 | **R3** (CSS 3줄 + JS 2줄) | M7 통과(reduce motion 포함). T25-65 통과 |
| 3 | **R5** (툴팁 2곳 + 시그니처 + 옵저버 정리) | M13 통과. T25-67 통과. **T25-41·44 회귀 없음** |
| 4 | **R8** (CSS 2줄) | M21·M22 통과. T25-69 통과. **T25-29·63 회귀 없음** |
| 5 | **R7-①** (제거 16항목) | M20 통과. T25-68 의 역방향 단정 통과. **T25-34·62 회귀 없음.** 이 시점에 드래그는 여전히 기존(고스트) 방식으로 동작해야 한다 |
| 6 | **R7-②** (라이브 이동 + `setDragImage` + `.card-dragging`) | M18·M19 통과. T25-68 전체 통과 |
| 7 | **R1** (템플릿 CSS 1줄 + JS 2줄 + 문서 4곳) | M1·M2·M3 통과. T22-97~99 통과. **T22-32·37 회귀 없음** |
| 8 | **R2** (3-a 절 + 기존 문장 5곳) | M4·M5·M6 통과. T22-100·101 통과. **T22-74~81 회귀 없음** |
| 9 | **R6** (4번 재구성) | M14~M17 통과. T22-102~104 통과. **T22-75·76·94 회귀 없음** |
| 10 | 문서 정합 (`hub/README.md` 9행 · 이전 PRP **5곳** 대체/보강 표기) | `bash tests/run.sh` 전체 통과 |

순서 근거:

- **허브 템플릿(1~6) 을 먼저, 절차 문서(7~9) 를 나중에.** 파일이 달라 서로 간섭하지 않고, 절차
  문서는 기존 grep 단정을 가장 많이 지나가므로 마지막에 몰아서 검증한다.
- **R7 은 ①(제거)과 ②(라이브 이동)를 반드시 나눈다.** ① 이 끝난 시점에도 드래그가 기존 방식으로
  동작하는지를 확인해야, ② 에서 무언가 깨졌을 때 원인이 제거인지 신규 로직인지 갈린다.
- R1 은 R2·R6 보고 문구("플로팅은 단독 탭에서만")의 전제이므로 그 앞에 둔다.
- R6 이 마지막인 이유: 4번 절을 구조적으로 재구성하므로 R2 의 3-a 가 먼저 자리를 잡아야 한다.

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| 1 | `init` 에 Bash 가 늘어 권한 프롬프트가 뜬다 | 기존 허용 목록 안내 + Automation 안내(결정 TR5). 실패해도 폴백으로 기존 동작이 남는다 |
| 2 | 허브를 열었는데 카드가 아직 안 보인다(최대 1 수집 주기) | 기본 5초. 결정 F8 에서 강제 수집을 거부한 근거를 남긴다 |
| 3 | 바깥 클릭 접기가 "실수로 닫힘"으로 체감된다 | 접혀도 한 줄 요약이 남고 되돌리기는 클릭 1회(결정 Q2) |
| 4 | 카드 클릭이 모달 열기 + 패널 접기를 동시에 한다 | 규칙 단순성을 택했다(결정 Q5). 모달이 패널을 덮어 보이지 않는다 |
| 5 | glow 가 다크에서 과하거나 라이트에서 약할 수 있다 | 수동 M7 에서 두 테마 실측. `blur`·`spread` 두 숫자만 조정 |
| 6 | `server-status` 가 1초 HTTP 프로브를 하므로 `init` 이 약간 느려진다 | 프로브 1초·서브프로세스 10초 상한. 정상 경로는 수십 ms |
| 7 | 절차 문서 편집이 기존 grep 단정을 깬다 | GOTCHA 3~5·10~13 + 「기존 자동 검사」 표를 체크리스트로 쓰고 마일스톤마다 `tests/run.sh` |
| 8 | pulse 의 `box-shadow` 애니메이션이 상시 리페인트를 만든다 | 2.6s 저주파 + working 한정 + reduced-motion 분기. 체감 문제 시 결정 D3 을 정적 glow 로 되돌린다 |
| **9** | **캡처 절대 시각을 화면에서 볼 수 없게 된다(R5)** | 상대 시각이 패널에 남고, `/hub status` 의 `rate_limit_capture_age_ms`·`usage_sample_age_ms` 가 창구다. `hub/README.md` 에 이 사실을 1행 적는다(T25-67 이 검사) |
| **10** | **탭 재사용이 "엉뚱한 탭"을 앞으로 가져온다** | 정확 일치로 구조적으로 차단(결정 TR4) + T22-104 가 느슨한 매칭 흔적 0건을 강제 |
| **11** | **AppleScript 가 브라우저를 실행시켜 빈 창이 뜬다** | `is running` 선행 검사(결정 TR3) + T22-103 이 그 문자열을 강제 + M17 이 실측 |
| **12** | **탭 수가 많으면 순회가 느리다** | 순회는 로컬 IPC 이며 탭 수십 개 규모에서 수백 ms 수준이다. 어차피 1회 시도 후 폴백이고, 지연이 문제가 되면 Chrome 만 보도록 좁히면 된다 |
| **13** | **키보드 순서 변경 상실(WCAG 2.1.1 회귀)** | 사용자 명시 결정임을 결정 DG2 에 기록. 콘텐츠 접근성은 유지되며 원안이 문서에 남아 되돌리기가 가능하다 |
| **14** | **가변 높이 카드가 도입되면 드래그 진동이 되살아난다** | 결정 DG4 의 의존 관계 명시 + GOTCHA 17. 최소 처방(`lastDragOverPath` 1개 추가)까지 미리 적어 둔다 |
| **15** | **모달 오버레이가 라이트 테마에서 과하게 어둡다** | `.55` 는 실측 조정 대상 1개 숫자다(M21). 토큰이 아니라 인라인이라 되돌리기가 1곳이다 |

---

## 검토했으나 채택하지 않은 대안

1. **R1 을 허브 쪽에서 푼다** — 허브가 iframe 에 `?embed=1` 쿼리를 붙이거나 `postMessage` 로
   지시하는 안. **거부.** ① 라우트 정규식이 `^/project/([0-9a-f]{16})/dashboard\.html\Z` 로 쿼리 없는
   정확 일치라 보안 근거(결정 N3)를 건드린다 ② `postMessage` 는 두 문서 사이에 새 프로토콜을
   만든다 — iframe 안에서 스스로 알 수 있는 사실이다.
2. **R1 을 `#dz-pip-btn` 제거(`remove()`)로 푼다** — **거부.** 이 저장소는 "CSS 로만 숨기고 DOM 에서
   제거하지 않는다"를 이미 불변식으로 갖는다(T22-42).
3. **R2 를 `hub.py open --json` 재사용으로 푼다** — **거부.** `cmd_open` 은 서버가 죽어 있으면
   전경 수집 후 `file://hub.html` 을 연다 — 요구와 정반대다.
4. **R2 를 위해 `hub.py` 에 `is-alive` 서브커맨드를 추가한다** — **거부(YAGNI).** 소비자가 하나고
   `server-status --json` 이 필요한 세 필드를 이미 준다.
5. **R3 을 카드 배경색으로 푼다** — **거부.** 카드 안 배지·칩이 `--soft`/`--accent-soft` 를 이미
   쓰고 있어 층위가 뭉개진다.
6. **R4 를 `focusout` 으로 푼다** — **거부.** 빈 배경 클릭은 포커스를 옮기지 않고, 키보드 사용자가
   Tab 으로 지나가는 순간 접힌다.
7. **R5 에서 캡처 시각을 `usage-meta` 텍스트로 승격한다** — **거부.** 요구 방향(조용한 패널)과
   반대이고 ≤420px 폭에서 줄바꿈 위험이 있다(결정 UT1-B).
8. **R6 을 `open -a "Google Chrome" URL` 로 푼다** — **거부.** 그것도 새 탭을 만든다. 탭 재사용은
   탭 목록을 조회할 수 있는 AppleScript 경로 말고는 방법이 없다.
9. **R6 을 브라우저별 원격 디버깅 포트(CDP)로 푼다** — **거부.** 브라우저를 특수 플래그로
   띄워야 하고, 그건 사용자 환경을 바꾸는 침습적 요구다.
10. **R6 을 `hub_daemon.browser_open_command` 개조로 푼다**(파이썬에서 osascript 호출) — **보류.**
    설계상 더 좋은 자리(포커스 경로가 이미 거기 있다)이지만 **파이썬 변경 + 단위 테스트 +
    T25-49 재작성**이 따라온다. 이 PRP 의 "Python 무변경" 전제를 지키고, 비대칭을 비목표 표에
    기록한다. 별도 요구가 오면 결정 TR1~TR6 을 그대로 옮기면 된다.
11. **R7 의 라이브 이동을 좌표(중심점) 비교로 푼다** — **거부.** 3열 그리드에서 좌우·상하가 섞여
    "어느 축의 중심인가"라는 판정이 새로 생기고, 그 임계값이 곧 튜닝 대상(버그 온상)이 된다.
    DOM 순서 비교는 임계값이 **없다**(결정 DG4).
12. **R7 에서 placeholder(빈 자리 표시) 노드를 삽입한다** — **거부.** 실제 카드를 옮기면 그 자체가
    placeholder 다. 노드를 하나 더 만들면 `currentCardOrder()` 가 그것을 걸러야 하고
    (`[data-project-path]` 셀렉터에 예외가 생긴다), drop 시 제거 누락이라는 새 실패 경로가 생긴다.
13. **R7 에서 키보드 경로를 `◀ ▶` 버튼으로 대체한다** — **거부(요구 밖).** 결정 O5-D 가 이미
    기각한 안이고, 사용자는 "드래그 전용"을 요구했다. 필요해지면 결정 DG2 의 되돌리기 지침을 쓴다.
14. **R8 에서 `--shadow-strong` 토큰을 신설한다** — **거부.** 사용처가 1곳이다(결정 MD2).

---

## 사용자 승인이 필요한 결정

### 승인 항목 1 — R2: 여는 허브 URL 을 `/hub.html` 로 한다 (결정 F3)

**→ 확정(2026-08-13): `/hub.html` 채택.** 개정 2 에서 근거가 하나 강해졌다 — R6 의 탭 재사용이
**정확 일치** 비교이므로, 표기를 하나로 고정하는 것이 곧 탭이 재사용될 조건이다.

### 승인 항목 2 — R2: 로컬 대시보드 서버(8791~8793) 기동·각인 유지 (결정 F4)

**→ 확정(2026-08-13): 유지.**

### 승인 항목 3 — R3: pulse 애니메이션 여부 (결정 D3)

**→ 개정(2026-08-13): 사용자가 pulse 를 선택** — 완화 3종·최종 CSS·재렌더 상호작용은 결정 D3 참조.

### 승인 항목 4 — R4: 바깥 클릭 접힘을 `localStorage` 에 영속화 (결정 Q2)

**→ 확정(2026-08-13): 영속화.**

### 승인 항목 5 — R5: 캡처 절대 시각을 **버린다** (결정 UT1)

패널 안 툴팁 2개를 지우면 "이 정보를 확인한 시각"(절대 시각)을 볼 창구가 화면에서 사라진다.
설계는 **버리는 안**을 제안한다 — 패널에 상대 시각(`마지막 갱신 3분 전`)이 남아 신선도 판단이
가능하고, 절대 시각은 `/hub status` 의 `rate_limit_capture_age_ms`·`usage_sample_age_ms` 두 필드에
이미 있다. **대안**은 `usage-meta` 텍스트에 절대 시각을 병기하는 것(패널이 한 줄 더 길어진다).

### 승인 항목 6 — R6: 지원 브라우저를 **Chrome·Safari 둘로 좁힌다** (결정 TR3)

Edge·Brave·Arc 등은 AppleScript 사전이 Chrome 과 거의 같지만 앱 이름을 하나씩 열거해야 한다.
설계는 **둘만 지원하고 나머지는 새 탭 폴백**을 제안한다(최악의 결과 = 지금과 동일).
**대안**: Chromium 계열 이름 3~4개를 배열로 열거해 순회(스크립트 약 10줄 증가, 유지 대상 증가).

### 승인 항목 7 — R7: **키보드 순서 변경 기능 제거**(WCAG 2.1.1 회귀) (결정 DG1·DG2)

방향키·Home/End 이동, 스크린리더 낭독(`#dzh-live`), 포커스 복원이 모두 사라지고 핸들이
`aria-hidden` 인 `<span>` 이 된다. 이는 **접근성 축소**이며 사용자 요구에 따른 것임을 문서에
기록한다. 되돌리려면 결정 O5 의 원안을 다시 붙인다. **이 항목은 되돌리기 비용이 가장 큰
결정이므로 명시적 확인이 필요하다.**

### 승인 항목 8 — R8: `backdrop-filter: blur()` 를 **넣지 않는다** (결정 MD3)

모달이 열린 동안에도 폴링이 배경 DOM 을 교체하므로 blur 는 그때마다 재합성 비용을 낸다.
설계는 **어두운 오버레이만**을 제안한다. 원하면 `.modal::backdrop` 에 `backdrop-filter:blur(2px)`
한 줄을 더한다.

### 승인 항목 9 — R6: `/hub` 커맨드에는 탭 재사용을 **적용하지 않는다**(비대칭 수용)

`/dashboard` 는 탭을 재사용하고 `/hub` 는 매번 새 탭을 여는 비대칭이 남는다. 대칭을 원하면
`hub_daemon.browser_open_command` 를 고쳐야 하고, 그 순간 **파이썬 변경 + 단위 테스트 + T25-49
재작성**이 이 PRP 범위로 들어온다(미채택 대안 10). 별도 요구로 분리하는 것을 제안한다.
