# 허브 — 프로젝트 상세보기를 모달에서 **우측 슬라이드 패널**로 전환 (PRP)

> 요구 3건: R1 카드 클릭 시 모달이 아니라 **우측 패널** · R2 패널이 열릴 때
> **메인 영역이 좌측으로 밀리며 슬라이드** · R3 **좁은 화면에서는 오버레이 허용**

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_template.html`(허브 화면) **1개 파일이 기능의 전부** + 테스트·문서 |
| 브랜치 | `main` (HEAD `3c83a54`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md)(결정 N1~N8) → [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md)(결정 MD1~MD4 · 불변식 H1‴) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 공개 DOM 계약(`#dzh-dashboard-modal` → `#dzh-detail-panel`)과 불변식이 함께 바뀐다 |
| 규모 | **Small~Medium** — 신규 1개(이 문서) / 수정 5개 파일. 허브 템플릿 순증 약 **+55 / −40줄** |
| 새 외부 의존성 | **없음** (바닐라 CSS/JS. 새 색 리터럴 1개는 기존 모달 그림자와 같은 성격 — 결정 SP2 참조) |
| **Python 변경** | **없음** — `hub/bin/*.py` 전체에 `modal`·`dialog` 문자열이 **0건**임을 확인했다(`grep -rn "modal\|dashboard-modal" hub/bin/*.py` → 결과 없음). 서버 경로 `/project/<key>/dashboard.html` 은 그대로 쓴다 |
| **승인 상태** | 초판: **승인됨(2026-08-14)** — 「승인 요청 항목」 1~6 전부 권고안대로 확정(단 **항목 1 은 R2 에서 번복**) · **R2: 승인됨(2026-08-14)** — 「R2 재승인 요청 항목」 1~5 전부 권고안대로 확정. 초안의 6건 중 **헤드 시안 A** 와 **패널 폭 550px** 2건은 사용자 지시로 확정(C1·C2) |

### 개정 이력

| 개정 | 내용 |
|------|------|
| 초판 (2026-08-14) | 요구 R1~R3 설계. 결정 코드는 두 글자 **SP**(Side Panel)를 쓴다 — 단일 문자 A~Z 는 기존 PRP 들이 소진했고, 앞선 문서가 **UT/TR/DG/MD** 로 두 글자 관례를 이미 확립했다. 불변식 **H1‴ → H1⁗** 개정 |
| **R2 (2026-08-14)** | 배포 후 후속 요구 2건 — ① **헤드를 다이얼로그 타이틀바가 아닌 패널 헤더로**(결정 SP11) ② **닫힐 때도 애니메이션**(결정 SP12~SP17). 결정 **SP5 의 「닫기 애니메이션 미도입」을 번복**하고 그에 딸린 **GOTCHA 1 을 개정**하며 **승인 항목 4 를 뒤집는다**. **YAGNI 보류 4 가 예고한 재방문이며, 그 트리거 문구가 지시한 대로 지연 타이머 + `openDashboardKey` 재진입 가드를 함께 설계했다.** 결정 SP11~SP18 신설, 검사 T25-79 개정 · T25-82~85 신설. 원문은 어느 절에서도 지우지 않고 개정 화살표만 덧붙였다 |
| **R2 재검토 (2026-08-14, HEAD `12d49d6`)** | R2 초안 승인이 **보류**됐다 — 사유는 「PR #3 을 먼저 처리하고 최신 소스로 다시 검토하라」. PR #3(`12d49d6`)이 `commands/dashboard.md` 의 대시보드 템플릿을 **허브 색 토큰·다크 모드로 재작성**하면서 **결정 SP11 의 구분선 근거 문장이 사실이 아니게 됐다** → 근거를 교체하고(결론·시안 A 는 유지) `commands/dashboard.md`·`tests/run.sh` 인용 줄 번호를 **전부 재확인**했다. 사용자 지시로 **헤드 시안 A 확정** · **패널 폭 고정 550px 확정**(초판 결정 SP4·초판 승인 항목 1 번복) → 결정 **SP19** 신설. 승인 항목을 「R2 재승인 요청 항목」 1~5 로 재구성했다. `hub/bin/hub_template.html` 은 PR #3 이 건드리지 않았으므로 그 파일 인용은 전부 그대로 유효함을 **직접 재확인**했다 |

---

## 요구사항 요약

허브의 프로젝트 카드를 클릭하면 지금은 화면 한가운데에 `<dialog>` 모달이 뜨고 배경 전체가
어두워진다(결정 N5·MD1). 모달은 **배경을 못 쓰게 만드는 것이 목적인 UI** 라서, "여러 프로젝트를
한 페이지에서 훑어본다"는 허브의 목적과 어긋난다 — 대시보드를 읽는 동안 카드 목록이 사라지고,
다른 프로젝트로 옮기려면 반드시 닫았다 다시 열어야 한다. 이 문서는 상세보기를 **우측에서 밀려
들어오는 비모달 패널**로 바꿔, 넓은 화면에서는 카드 목록과 상세 대시보드를 **동시에** 두고,
좁은 화면에서는 패널이 화면을 덮게 한다.

### 사용자 스토리

| # | 스토리 |
|---|--------|
| S1 | 넓은 화면에서 카드를 누르면 **메인 목록이 왼쪽으로 밀리면서** 우측에서 패널이 미끄러져 들어온다. 목록은 그대로 보이고 **클릭도 된다** |
| S2 | 패널이 열린 채로 다른 카드를 누르면 패널이 **닫히지 않고 내용만 바뀐다** |
| S3 | 좁은 화면(노트북 분할·태블릿)에서는 패널이 메인 영역을 **덮는다**. 배경을 잘못 눌러 엉뚱한 일이 일어나지 않는다 |
| S4 | 패널이 열려 있는 동안에도 허브의 1분 폴링·30초 틱이 카드를 갱신하고, **패널은 살아 있다** |
| S5 | 닫으면 패널 안 대시보드의 5초 폴링도 함께 멈춘다(숨은 요청이 남지 않는다) |

### 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G1 | `hub_template.html` 에 `<dialog id="dzh-dashboard-modal"`·`showModal(`·`::backdrop` 이 **0건**이고 `<aside id="dzh-detail-panel"` 이 존재한다 | T25-76 |
| G2 | 밀어내기 규칙(`padding-right:var(--dzh-panel-width)`)과 오버레이 기본 규칙이 **하나의 브레이크포인트 리터럴**(`1024px`)만 쓴다 | T25-77·T25-78 |
| G3 | CSS 의 브레이크포인트 숫자와 JS 상수 `PANEL_PUSH_MIN_WIDTH_PX` 가 **기계적으로 같음**이 확인된다 | T25-78 |
| G4 | 열기 애니메이션 규칙과 `prefers-reduced-motion` 무효화가 **세트로** 있고, 무효화가 **소스 순서상 뒤**에 있다 | T25-79 |
| G5 | 닫을 때 iframe 이 `about:blank` 로 간다(리스크 R-6 승계) | T25-80 · 수동 M5 |
| G6 | 같은 카드를 다시 눌러도 iframe 이 **재로딩되지 않는다** | 수동 M3 |
| G7 | 폴링이 `#dzh-app` 을 통째로 교체해도 열린 패널이 유지된다 | 수동 M6 |

---

## 확정된 전제 (재론하지 않는다)

1. **허브 파이썬은 한 줄도 바꾸지 않는다.** 서버 경로·스냅샷 계약·`dashboard_key` 파생 규칙
   (결정 N1~N3)은 전부 그대로다. 이 변경은 순수하게 **표현 계층**이다.
2. **`/dashboard` 생성물의 동작 계약도 바꾸지 않는다.** `body.dz-embedded` 는
   `window.self !== window.top` 판정이라(`commands/dashboard.md` 1321~1326행) iframe 을 담는 그릇이
   모달이든 패널이든 **판정이 동일**하다. 플로팅(PiP) 버튼 숨김도 그대로 성립한다.
3. **`file://` 모드는 이전과 같이 클릭 대상이 아니다**(결정 N7 승계). 서버 모드에서만 카드에
   `data-dashboard-key` 가 붙고(템플릿 760~763행), 패널 IIFE 는 그 속성만 본다.
4. **새 색 토큰을 만들지 않는다.** 표면·경계는 `var(--surface)`·`var(--line)`, 그림자만 중성
   검정 반투명 리터럴(결정 MD2 의 근거를 그대로 승계 — T25-29 가 금지하는 것은 색각 안전성이
   없는 **범주 색** 리터럴이다).
5. **불변식 H1 계열의 원칙은 유지된다**: 사용자 상태(포커스·접힘·선택·순서·**열린 상세 패널**)를
   가진 노드는 재렌더 대상 밖에 둔다.

### 비목표 (이번 범위 밖 — 명시적으로 건드리지 않는다)

| 항목 | 이유 |
|------|------|
| 패널 리사이즈 핸들(드래그로 폭 조절) | YAGNI. 요구에 없고, 폭 상태의 영속화·불변식 편입까지 끌고 온다(YAGNI 보류 1) |
| 열린 프로젝트의 카드 하이라이트 | 두 IIFE 의 독립성(불변식 H1⁗ 의 설계 의도)을 깨야 한다(YAGNI 보류 2) |
| 패널 안 대시보드의 좁은 폭 전용 CSS | `/dashboard` 템플릿 변경이 필요하다. 전제 2 위반(YAGNI 보류 3) |
| 여러 패널 동시 열기 / 탭 | 요구에 없다. 싱글턴 하나로 끝난다 |

---

## 영향 범위

### 수정 파일 (5개)

| 파일 | 무엇을 | 왜 |
|------|--------|-----|
| `hub/bin/hub_template.html` | ① 머리 주석 20~24행(정적 노드 목록)·50~52행(모달 문단) 개정 ② `:root` 에 `--dzh-panel-width` 1줄 추가(55~62행) ③ 모달 CSS 블록 **전체 교체**(228~262행, 약 −27/+34줄) ④ 모달 DOM 블록 교체(306~314행) ⑤ 사용량 패널 바깥 클릭 가드 1줄 수정(1028행) ⑥ 모달 IIFE **전체 교체**(1124~1177행, 약 −54/+75줄) | R1·R2·R3 전부 |
| `tests/run.sh` | 기존 T25-63·T25-64·T25-66·T25-69·T25-70 개정, T22-101 토큰 교체(승인 항목 6 채택 시), **신규 T25-76~T25-81** | 회귀 검사 |
| `hub/README.md` | 「프로젝트 대시보드 모달」 절(185~205행) → 「프로젝트 상세 패널」로 개정. 「프라이버시 고지」 116~117행의 "모달" 표현 | 사용자 문서 |
| `docs/prps/hub-card-interactions-and-usage.md` | 결정 **N5 에 「대체됨」 표기**, N8·리스크 R-6 에 「승계됨」 표기 | 정본 이관 |
| `docs/prps/hub-first-entry-and-ui-signals.md` | 「불변식 H1″ → H1‴ 개정」 절과 결정 MD1~MD4 에 **이관 표기** | 정본 이관 |

> 표기 관례의 선례: `hub-onboarding-statusline-and-stale-usage.md` 의 결정 EX7 이
> `hub-first-entry-and-ui-signals.md` 의 H1‴ 표 5행에 `→ **부분 대체됨** — …` 한 줄을 덧붙였다.
> 같은 방식만 쓴다 — **원문을 지우지 않고 이관 화살표를 덧붙인다.**

### 조건부 수정 (승인 항목 6)

| 파일 | 무엇을 |
|------|--------|
| `commands/dashboard.md` | "허브 모달" 표현 10곳(195·196·212·215·753·837·874·876·975·1193·1255~1258·1321행 주변) → "허브 상세 패널". **동작·계약은 무변경**, 문구만 |

### 미영향 — 건드리지 않는 이유 (직접 확인함)

| 대상 | 근거 |
|------|------|
| `hub/bin/*.py` 전부 | `modal`·`dialog` 문자열 **0건**(grep 확인). 서버가 서빙하는 경로는 그대로다 |
| `commands/dashboard.md` 의 **동작 계약** | `body.dz-embedded` 는 `self !== top` 판정(1321~1326행)이라 그릇의 종류를 묻지 않는다. CSS 규칙 `body.dz-embedded #dz-pip-btn,…{display:none}`(1258행)도 그대로 유효 |
| `tests/run.sh` T22-97·98·99 | 각각 `body.dz-embedded #dz-pip-btn` CSS 셀렉터(1780행)·`window.self !== window.top`(1788행)·`isEmbedded` 등장 횟수 2(1795행)를 검사한다 — **셀렉터와 식별자만 본다.** 주석 문구를 바꿔도 통과한다(확인함) |
| `#dzh-app` 그리드 규칙(89행) | 트랙 폭이 `100%` 기준 비율식이라 컨테이너가 좁아지면 3열 → 2열 → 1열로 **자동 대응**한다. CSS 수정 불필요 |
| `.tooltip`(223행, `z-index:40`) | 뷰포트 좌표로 배치되는 `position:fixed` 라 `body` 패딩과 무관. 패널(`z-index:30`)보다 **위**에 남는다 |
| 드래그 순서 변경(결정 DG1~DG6) | 패널 IIFE 는 `document` 위임 클릭만 쓴다. 드래그 핸들 가드(`closest('.card-drag-handle')`, 결정 N6)를 그대로 유지한다 |

---

## 결정 기록

### 결정 SP1 — 요소는 `<aside role="dialog">`. `<dialog>` 를 **버린다**

| 안 | 얻는 것 | 잃는 것 |
|----|---------|---------|
| A. `<dialog>` + `showModal()` (현행) | 포커스 트랩·ESC·배경 inert·`::backdrop` 무료 | **배경을 쓸 수 없다** — 요구 R2 의 "밀어내기"가 무의미해진다(밀어내 봐야 만질 수 없는 배경이다) |
| B. `<dialog>` + `show()` (비모달) | `close` 이벤트라는 수렴점 1개 | **ESC 를 주지 않는다**(브라우저는 모달 dialog 에만 close request 를 처리한다) · **`::backdrop` 이 렌더되지 않는다**(top layer 가 아니다) · 포커스 트랩·inert 도 없다 → **결정 N5 가 근거로 삼은 "공짜" 4개가 전부 사라진다.** 남는 것은 `dialog:not([open]){display:none}` 이라는 UA 규칙뿐인데, 이것이 슬라이드 애니메이션과 정면으로 싸운다(SP5) |
| C. `popover="auto"` | light-dismiss·ESC 무료, top layer | **light-dismiss 가 치명적이다** — 배경 카드 클릭이 곧 패널 닫기라, 요구 S2("다른 카드 클릭 = 내용 교체")와 정확히 충돌한다. top layer 라 `.tooltip`(z-index 40)이 패널 뒤로 숨는다 |
| **D. `<aside>` + `role="dialog"` + 수동 배선** | `display` 를 **내가 소유**한다 → `visibility`+`transform` 만으로 열기 애니메이션이 성립(신문법 불필요) · 넓은 화면에서 배경이 살아 있다 · `z-index` 로 `.tooltip` 과의 순서를 통제한다 | ESC·포커스 이동·복귀를 직접 쓴다(약 12줄) |

> **결정 SP1 — 안 D.** 결정 N5 를 **대체한다.**
> N5 의 논거는 "손으로 만들면 50줄 넘는 **포커스 트랩**을 공짜로 얻는다"였다. 이번에는
> **포커스 트랩을 만들면 안 된다** — 넓은 화면에서 배경 목록을 계속 쓰는 것이 이 기능의 목적이다.
> 안 B 를 골라도 ESC 는 직접 써야 하므로, `<dialog>` 를 붙들고 얻는 것은 사실상 없고
> `display:none` 토글이라는 **부채만 남는다**(SP5 참조).
> 좁은 화면의 배경 차단은 트랩 코드가 아니라 **`inert` 속성 2줄**로 해결한다(SP3).

**접근성 배선 (안 D 가 직접 져야 하는 몫):**

| 항목 | 처리 |
|------|------|
| 역할 | `role="dialog"` + `aria-labelledby="dzh-detail-title"`. `<aside>` 기본 역할(`complementary`)은 "닫을 수 있는 일시적 표면"을 표현하지 못한다 |
| `aria-modal` | **오버레이 모드에서만 `true`**. 배경을 실제로 `inert` 로 만드는 그 순간에만 붙인다 — 트랩 없이 `aria-modal="true"` 를 상시로 붙이는 것은 스크린리더에 거짓말이다 |
| 닫힌 상태 | `visibility:hidden` — Tab 순서·접근성 트리에서 **사라진다**. `transform` 만으로 화면 밖에 두면 닫힌 패널의 버튼에 Tab 이 들어간다 |
| 포커스 진입 | 열 때 닫기 버튼으로 이동. 그러지 않으면 키보드 사용자는 `.project-name` 버튼에서 Enter 를 눌러도 다음 Tab 이 카드 목록으로 계속 흘러 패널을 영영 못 만난다 |
| 포커스 복귀 | 닫을 때 연 요소로 복귀. **단, 폴링이 그 카드를 이미 파괴했을 수 있다** → `isConnected` 확인 후 아니면 `<body>` 로 낙착(결정 N5 의 동일 조항 승계) |
| ESC | `document` keydown 1개. **iframe 안에 포커스가 있으면 오지 않는다**(엣지 E5) — 현행 모달도 같은 한계라 회귀가 아니다. 그래서 닫기 버튼이 1차 수단이다 |

### 결정 SP2 — 밀어내기는 `body{padding-right}` 전이, 패널 자신은 `transform` 슬라이드

| 안 | 평가 |
|----|------|
| A. `.wrap{transform:translateX(-W)}` | 컴포지터 친화적이지만 **메인이 좁아지지 않고 그냥 왼쪽으로 나간다** — `.wrap` 은 `max-width:1440px;margin:32px auto`(83행)라 화면이 1440+2W 보다 좁으면 좌측이 화면 밖으로 잘린다. 요구는 "밀린다"이지 "잘린다"가 아니다 |
| B. `body{display:grid;grid-template-columns:1fr Wpx}` 전이 | 패널이 그리드 칸이 되면 **문서와 함께 스크롤된다.** 카드가 20개인 허브에서 상세 패널이 위로 스크롤돼 사라지는 것은 명백한 퇴행이다. `position:sticky` 로 되살리면 안 C 보다 복잡해진다 |
| **C. `body{padding-right}` 전이 + 패널은 `position:fixed` + `transform` 슬라이드** | 밀어내기는 레이아웃 변화 그대로(정직하게 재배치된다 — 3열 → 2열 자동 대응), 슬라이드는 컴포지터 트랙. 패널은 항상 뷰포트 고정 |

> **결정 SP2 — 안 C.**
> **웹 규칙(`transform`/`opacity` 만 애니메이션)을 여기서는 의도적으로 일부 벗어난다.**
> push 는 본질이 레이아웃 변화이며, 우리가 원하는 결과(카드 그리드가 3열→2열로 **재배치**되는 것)
> 자체가 리플로우다. `transform` 으로는 그 결과를 만들 수 없다.
> 비용을 통제하는 근거:
> - 지속 시간이 **180ms 한 번**이고, 열 때만 재생된다(닫기는 즉시 — SP5).
> - 리플로우 대상은 `#dzh-app` 그리드 1개와 카드 N개(카드 높이는 `340px` 고정이라 세로 방향
>   전파가 없다 — 99행).
> - **`backdrop-filter` 를 넣지 않는다는 결정 MD3 의 근거가 여기서도 그대로다** — 폴링(60초)·틱(30초)이
>   배경을 통째로 교체하는 화면에서 상시 합성 비용을 만드는 장식은 도입하지 않는다. 이번 리플로우는
>   상시가 아니라 **열 때 1회**다.
> - 실측 잔상이 관측되면 **후퇴 경로가 1줄**이다: `body.dzh-panel-open` 의 `transition` 만 지우면
>   밀어내기는 즉시, 패널 슬라이드는 유지된다(기능 손실 0).

**`.usage` 패널 동반 이동(놓치기 쉬운 부분).** 사용량 패널은 `position:fixed;right:16px;bottom:16px;
z-index:20`(196행)이라 `body` 패딩의 영향을 **받지 않는다** — 그대로 두면 패널 밑에 깔린다.
밀어내기 모드에서만 `transform:translateX(calc(-1 * var(--dzh-panel-width)))` 로 같이 옮긴다
(`right` 를 바꾸지 않는 이유: 이 요소만큼은 컴포지터 트랙으로 옮길 수 있고, 그 편이 싸다).

### 결정 SP3 — 오버레이 전환 기준 **1024px**, 전폭(full-bleed), dim·배경 클릭 닫기 **없음**

> **재도출(R2 재검토, 2026-08-14) — 결론 유지.** 아래 폭 산술의 입력값 하나가 바뀌었다
> (`clamp()` 하한 400px → **고정 550px**, 결정 SP19). 최소 뷰포트는 `400+352=752` 에서
> **`550+352=902`** 로 올라가지만 **1024px 은 그대로 둔다** — 근거는 SP19 에 재계산해 두었다.

폭 산술(실측 값 기준):
- 카드 1열의 최소 폭 = `320px`(89행 `max(320px, …)`) + `.wrap` 좌우 패딩 `32px` = **352px**.
- 밀어내기 모드에서 패널이 `clamp()` 하한 `400px`(SP4)일 때, 메인이 1열을 온전히 유지하려면
  뷰포트 ≥ `400 + 352 = 752px`. 여기에 여백을 얹어 **1024px** 을 고른다.
- 1024px 은 임의의 취향값이 아니라 **"밀어내도 카드 1열이 여유 있게 남는 최소 크기"** 이고,
  동시에 관례적인 데스크톱 경계라 사용자의 기대와도 맞는다.

| 항목 | 결정 | 근거 |
|------|------|------|
| 좁은 화면 폭 | **전폭**(`left:0;right:0`) | 좁을수록 대시보드에 줄 픽셀이 아깝다. `100vw` 를 쓰지 않는 이유는 GOTCHA 4 |
| 배경 dim | **없음** | 전폭이라 **가려질 배경이 없다.** dim 은 "덮개 뒤에 뭔가 있다"를 보여줄 때만 값을 한다 |
| 배경 클릭 닫기 | **없음** | 누를 배경이 없다. 유일한 닫기 수단은 닫기 버튼·ESC 두 개이며 둘 다 항상 화면에 있다 |
| 키보드·스크린리더 | **`inert`** 를 `.wrap` 과 `#dzh-usage` 에 건다 | 보이지 않는 배경으로 Tab 이 들어가는 것을 속성 하나로 막는다. 포커스 트랩 코드를 쓰지 않는 이유 |
| 배경 스크롤 | `body{overflow:hidden}` (오버레이 모드에서만) | 덮인 동안 뒤 문서가 스크롤되면 닫았을 때 읽던 위치가 사라져 있다 |

**CSS 는 오버레이가 기본, 밀어내기가 `@media (min-width:1024px)` 덧쓰기다.** 브레이크포인트
리터럴이 **한 곳에만** 존재하도록(그리고 `1023.98px` 같은 반쪽 값을 만들지 않도록) 모바일 퍼스트
순서를 택한다. JS 쪽 `matchMedia` 도 같은 문자열을 조립한다 → 두 값의 일치는 T25-78 이 기계적으로 강제한다.

### 결정 SP4 — 패널 폭 `clamp(400px, 40vw, 720px)` (비율 + 상·하한)

> **→ 번복(R2, 2026-08-14) — 사용자 지시로 고정 550px.** 정본은 **결정 SP19** 다.
> 아래 원문(비율 + 상·하한 논거, 뷰포트 표)은 **지우지 않는다** — 550 고정이 무엇을
> 포기하는지(27인치에서의 폭 확장) 읽을 수 있어야 하기 때문이다. 550 기준으로 다시
> 계산한 뷰포트 표는 SP19 에 있다. **변하지 않는 것**: `--dzh-panel-width` 가 `:root`
> 한 줄이라는 구조와, 그 값이 밀어내기 폭·`.usage` 이동량의 단일 출처라는 계약.

패널 안 대시보드의 실제 제약(직접 확인):
- `/dashboard` 템플릿의 `.wrap` 은 `max-width:860px;padding:0 16px`(`commands/dashboard.md` 1200행),
  `.card` 는 `padding:26px 30px`(1201행) → **가로 chrome 92px**.
- **`@media` 쿼리가 한 줄도 없다**(전수 grep 확인). 좁아지면 `max-width` 상한이 자연히 풀리고
  `.step-detail`·`.entry .lead` 가 `text-overflow:ellipsis` 로 줄어들 뿐이다 → 깨지지 않지만 정보가 준다.
- `body.dz-pip` 축약 CSS(1259~1262행)가 있지만 이는 **Document PiP 창 전용**이며 iframe 에는 붙지 않는다.

| 뷰포트 | 패널 폭 | 남는 메인 | 카드 열 수 |
|--------|---------|-----------|------------|
| 1024px | 410px | 614px | 1열 |
| 1280px | 512px | 768px | 2열 |
| 1440px | 576px | 864px | 2열 |
| 1920px | 720px | 1200px | 3열 |

> **결정 SP4 — `clamp(400px, 40vw, 720px)`.** 고정폭은 27인치에서 대시보드를 쓸데없이 좁게 두고,
> 순수 비율은 좁은 화면에서 읽을 수 없는 폭까지 내려간다. 상한 `720px` 은 **대시보드 원본 폭
> `860+32=892px` 에 근접하되 1920px 화면에서 카드 3열(필요 1016px)을 지키는** 상한이다 — 위 표의
> 마지막 줄이 이 값을 고른 이유 전부다.
> **리사이즈 핸들은 도입하지 않는다**(YAGNI 보류 1): 요구에 없고, 폭을 사용자 상태로 만드는 순간
> `localStorage` 키·불변식 편입·드래그 핸들과의 조작 충돌이 한꺼번에 따라온다. 폭이 불만이면
> `--dzh-panel-width` **한 줄**을 고치면 된다.

### 결정 SP5 — 열기 180ms `ease-out` **슬라이드만**. 닫기는 즉시 (결정 MD4 승계)

> **부분 번복(R2, 2026-08-14)** — 「닫기 애니메이션을 만들지 않는다」는 사용자 요구로 뒤집혔다.
> 정본은 **SP12**(닫힘 상태 표현) · **SP14**(`about:blank` 지연) · **SP15**(재진입 가드) ·
> **SP16**(밀어내기 복귀). 아래 표의 시간·이징(180ms `ease-out`)과 reduced-motion 원칙,
> 그리고 명세도 함정에 대한 경고는 **그대로 유지된다** — 무효화 블록의 셀렉터만 6개로 늘어난다(SP17).
> 아래 CSS 예시의 「전이를 열린 상태 규칙 안에만」 기법은 **R2 에서 기본 규칙으로 옮겨졌다**(SP12).

```css
.detail-panel{…;transform:translateX(100%);visibility:hidden}                    /* transition 없음 */
body.dzh-panel-open .detail-panel{transform:none;visibility:visible;
                                  transition:transform 180ms ease-out}           /* 열림 상태에만 선언 */
```

**`transition` 을 "열린 상태 규칙" 안에만 선언하는 것이 핵심 기법이다.** 클래스가 붙는 순간에는
전이가 살아 있어 슬라이드가 재생되고, 클래스가 떨어지는 순간에는 전이 선언 자체가 사라져
**즉시** 닫힌다. JS 타이머가 0개다.

| 항목 | 값 | 근거 |
|------|-----|------|
| 시간·이징 | **180ms ease-out** | 기존 `modal-open`·`backdrop-fade`(238·251행)와 같은 값. 저장소에 이미 있는 관례를 새 값으로 흔들지 않는다 |
| 속성 | `transform` 만 | `opacity` 를 겹치지 않는다 — 측면에서 들어오는 표면은 이동만으로 충분하고, 두 속성을 겹치면 저사양에서 반투명 합성이 추가된다 |
| 밀어내기 | `padding-right` 전이(같은 180ms) | SP2 |
| 닫기 애니메이션 | **만들지 않는다** | 결정 MD4 의 근거 승계 + **새 근거 1개**: 닫기를 애니메이션하면 슬라이드가 끝날 때까지 `about:blank` 를 미뤄야 하고(안 그러면 빠져나가는 패널이 흰 화면으로 번쩍인다), 그 지연 동안 재클릭이 들어오면 **새로 연 패널을 지연 타이머가 지워버리는 경쟁 상태**가 생긴다. 즉시 닫기는 이 문제 자체를 없앤다 |
| reduced-motion | 열림 상태 3규칙의 `transition` 을 전부 `none` | 아래 소스 순서 주의 |

**`prefers-reduced-motion` 오버라이드의 명세도(specificity) 함정 — 저장소가 이미 한 번 밟았다.**
254~257행 주석이 남긴 교훈("오버라이드는 반드시 그 규칙들보다 뒤에 와야 실제로 적용된다")에
**명세도 조건이 추가**된다. `body.dzh-panel-open .detail-panel` 은 (0,2,1)이므로 `.detail-panel`
단독(0,1,0)으로 덮을 수 없다. 셀렉터를 **그대로 반복해서** 적는다:

```css
@media (prefers-reduced-motion:reduce){
  body.dzh-panel-open,
  body.dzh-panel-open .detail-panel,
  body.dzh-panel-open #dzh-usage{transition:none}
}
```

### 결정 SP6 — 불변식 **H1‴ → H1⁗** 개정 (정본은 이 절이다)

`hub_template.html` 머리 주석의 개정 지점만 적는다.

| # | 위치 | 변경 |
|---|------|------|
| 1 | 23~24행 정적 노드 목록 | `#dzh-dashboard-modal(과 그 자식 전부)` → **`#dzh-detail-panel(과 그 자식 전부)`**. 나머지 4개(`#dzh-usage`·`#dzh-usage-toggle`·`#dzh-theme-toggle`·`#dzh-tooltip`)는 그대로 |
| 2 | 33~34행 원칙 문장 | "사용자 상태(포커스·접힘·선택·순서·**열린 모달**)" → "…·**열린 상세 패널**)" |
| 3 | 50~52행 모달 문단 | 전체 교체: "프로젝트 대시보드 모달(#dzh-dashboard-modal, … 결정 N5)은 `<dialog>`+showModal() 정적 싱글턴이다" → "프로젝트 **상세 패널**(`#dzh-detail-panel`, `docs/prps/hub-detail-side-panel.md` 결정 SP1)은 **비모달 `<aside>` 정적 싱글턴**이다. 카드 클릭이 iframe 문서와 제목만 바꾸고, 닫힘에서 iframe 을 `about:blank` 로 보내 숨은 폴링을 멈춘다. **열림 상태의 유일한 진실은 패널 IIFE 의 `openDashboardKey` 이며 `body.dzh-panel-open` 은 그 값의 CSS 투영이다**" |
| 4 | **신설 조항 ③** | "**밀어내기는 `body` 의 클래스 하나로만 표현한다.** `#dzh-app` 이나 카드에는 패널 열림 상태를 반영하지 않는다 — 반영하는 순간 매 렌더마다 그 상태를 다시 계산해야 하고, 두 IIFE 의 독립성이 깨진다" |

**정본 이관 표기**(원문 삭제 없이 화살표만 덧붙인다):

| 파일 | 지점 | 덧붙일 표기 |
|------|------|-------------|
| `hub-first-entry-and-ui-signals.md` | 「불변식 H1″ → H1‴ 개정」 절 머리 | `→ **대체됨(2026-08-14)** — 정본은 hub-detail-side-panel.md 결정 SP6(H1⁗)` |
| 〃 | 결정 MD1·MD2 | `→ **폐기됨** — 모달 표면 자체가 사라졌다(SP1). ::backdrop 규칙도 함께 사라진다` |
| 〃 | 결정 MD3 | `→ **근거 승계** — blur 미도입 논거(폴링이 배경을 교체한다)가 SP2 의 리플로우 비용 판단에 그대로 쓰였다` |
| 〃 | 결정 MD4 | `→ **원칙 유지** — "열기만 애니메이션한다"는 SP5 가 그대로 이어받는다(구현 기법만 keyframes → 상태 규칙 transition 으로 바뀐다)` |
| `hub-card-interactions-and-usage.md` | 결정 N5 | `→ **대체됨(2026-08-14)** — hub-detail-side-panel.md 결정 SP1` |
| 〃 | 결정 N6 | `→ **유지** — 드래그 핸들·텍스트 선택 가드는 패널에서도 그대로다` |
| 〃 | 결정 N7 | `→ **유지** — file:// 모드는 여전히 클릭 대상이 아니다` |
| 〃 | 결정 N8 | `→ **승계** — hub-detail-side-panel.md 엣지 E3` |
| 〃 | 리스크 R-6 | `→ **승계** — 패널에서도 닫힘 시 about:blank 가 유일한 정지 수단이다(SP7)` |

### 결정 SP7 — 폴링 공존: 정적 싱글턴 유지 + 상태를 `#dzh-app` 밖에만 둔다

패널은 `#dzh-app` **바깥**의 정적 노드이므로 1분 폴링·30초 틱이 `#dzh-app` 자식을 통째로 교체해도
패널·iframe·그 안의 5초 폴링은 **전혀 영향받지 않는다**(현행 모달과 동일한 성질).

| 상황 | 동작 |
|------|------|
| 폴링이 `#dzh-app` 교체 | 패널 유지. iframe 재로딩 없음. **밀어내기도 유지된다** — 클래스가 `body` 에 있기 때문 |
| 열린 프로젝트가 스냅샷에서 사라짐 | **패널을 강제로 닫지 않는다**(결정 N8 승계). iframe 안 대시보드가 자기 폴링에서 404 를 받아 스스로 "연결 끊김"을 표시한다. 읽던 화면을 빼앗지 않는다 |
| 드래그 중(`isReordering`) | 렌더가 멈추는 구간이지만 패널과 무관하다. 드래그 핸들 클릭은 패널을 열지 않는다(결정 N6 가드 유지) |
| 닫힘 | `about:blank` 로 이동시켜 숨은 5초 폴링을 **반드시** 멈춘다. `visibility:hidden` 도 `display:none` 도 iframe 의 타이머를 멈추지 않는다 — 이 사실이 리스크 R-6 이 여전히 살아 있는 이유다 |

### 결정 SP8 — 같은 카드 재클릭은 **무동작**, 다른 카드는 **교체**

| 상황 | 동작 | 근거 |
|------|------|------|
| 닫힌 상태에서 카드 클릭 | 연다 + 닫기 버튼으로 포커스 이동 | — |
| **같은** 카드 재클릭 | **아무것도 하지 않는다**(early return) | 토글로 만들면 "실수로 두 번 눌러 닫힘"이 생기고, 재로딩으로 만들면 **읽던 대시보드의 스크롤 위치가 초기화된다.** 취향 문제가 아니라 손해가 명확한 쪽을 피한 것이다. 닫는 수단은 이미 2개(버튼·ESC) 있다 |
| **다른** 카드 클릭 | 제목 + iframe 문서만 교체. **닫았다 열지 않는다** | 요구 S2. 닫기-열기로 구현하면 패널이 나갔다 들어오는 깜빡임이 생긴다 |
| 교체 시 `about:blank` 경유 | **하지 않는다** | 새 문서로 직접 이동하면 옛 문서가 그 자리에서 파기되고 타이머도 함께 죽는다. 중간에 빈 문서를 한 번 더 태우는 것은 흰 번쩍임만 추가한다 |

### 결정 SP9 — iframe 이동은 `contentWindow.location.replace()` (뒤로가기 오염 제거)

`iframe.src = url` 대입은 **부모 문서의 세션 히스토리에 항목을 남긴다.** 지금도 모달을 한 번
열고 닫으면 항목 2개가 쌓여, 사용자가 뒤로가기를 누르면 허브를 떠나는 대신 iframe 이 되감긴다.
모달 시절에는 빈도가 낮아 드러나지 않았지만, **패널은 카드를 옮겨 다니며 쓰는 UI** 라 항목이
클릭 수만큼 쌓인다.

```js
/** iframe 을 새 문서로 교체 이동시킨다 — src 대입과 달리 뒤로가기 기록을 남기지 않는다. */
function loadPanelDocument(url){
  panelFrameEl.contentWindow.location.replace(url);
}
```

- iframe 은 문서에 상시 존재하는 정적 노드라 `contentWindow` 는 항상 non-null 이다 →
  **분기를 만들지 않는다**("일어날 수 없는 상황에 대한 에러 처리 금지").
- 초기 상태는 same-origin `about:blank` 이고 이후 문서도 허브 서버와 same-origin 이라 접근이 막히지 않는다.
- 열기·교체·닫기 세 경로가 **이 함수 하나**를 쓴다.

> 이 결정은 요구에 없는 개선이라 **승인 항목 5** 로 올린다. 기각되면 `panelFrameEl.src = url`
> 대입으로 되돌리면 되고, 다른 결정은 하나도 흔들리지 않는다.

### 결정 SP10 — 식별자·클래스 개명표 ("modal" 이라는 거짓말을 남기지 않는다)

| 옛 이름 | 새 이름 | 비고 |
|---------|---------|------|
| `#dzh-dashboard-modal` | `#dzh-detail-panel` | 정적 노드 목록·불변식 문구가 함께 바뀐다(SP6) |
| `#dzh-modal-title` | `#dzh-detail-title` | `aria-labelledby` 대상 |
| `#dzh-modal-frame` | `#dzh-detail-frame` | |
| `#dzh-modal-close` | `#dzh-detail-close` | `.icon-btn` 은 그대로 공유 |
| `.modal` / `.modal-head` / `.modal-title` / `.modal-frame` | `.detail-panel` / `.detail-head` / `.detail-title` / `.detail-frame` | |
| `.modal::backdrop`, `@keyframes modal-open`, `@keyframes backdrop-fade` | **삭제** | 대체물 없음 |
| `MODAL_ELEMENT_ID`, `openDashboardModal`, `closeDashboardModal` | `PANEL_OPEN_BODY_CLASS`, `openDetailPanel`, `closeDetailPanel` | |
| (신설) | `PANEL_PUSH_MIN_WIDTH_PX`, `--dzh-panel-width`, `body.dzh-panel-open`, `openDashboardKey`, `loadPanelDocument`, `applyBackgroundInert` | |

개명을 하지 않고 `.modal` 이름을 그대로 재사용하면 테스트·문서 diff 는 줄지만, **모달이 아닌
것을 모달이라 부르는 코드**가 남는다("이름만 읽고 역할을 알 수 있어야 한다"). 개명 비용은
grep 치환 수준이고 검사 개정은 어차피 필요하다.

---

## DOM / CSS / JS 계약 (변경 후)

### DOM (306~314행 교체)

```html
<aside id="dzh-detail-panel" class="detail-panel" role="dialog" aria-labelledby="dzh-detail-title">
  <div class="detail-head">
    <span id="dzh-detail-title" class="detail-title"></span>
    <button id="dzh-detail-close" class="icon-btn" type="button"
            aria-label="닫기" data-tooltip="닫기 (Esc)">✕</button>
  </div>
  <iframe id="dzh-detail-frame" class="detail-frame"
          aria-label="프로젝트 진행 대시보드"></iframe>
</aside>
```

`title=` 속성을 쓰지 않는다(T25-44 금지 — 결정 N5 의 GOTCHA 5 승계). 위치는 지금 모달이 있던
자리 그대로 `#dzh-tooltip` 다음, `#dzh-data` 앞이다.

### 새로 생기는 계약

| 이름 | 소유 | 의미 |
|------|------|------|
| `--dzh-panel-width` | `:root`(55~62행) | 패널 폭. **밀어내기 폭과 `.usage` 이동량이 같은 값을 쓰도록 강제하는 단일 출처** |
| `body.dzh-panel-open` | 패널 IIFE | 패널이 열려 있다. `openDashboardKey !== null` 의 CSS 투영이며 **JS 상태의 사본이 아니다**(읽지 않는다) |
| `#dzh-detail-panel` | 정적 마크업 | 불변식 H1⁗ 의 정적 노드 |
| `z-index:30` | `.detail-panel` | `.usage`(20) 위, `.tooltip`(40) 아래. **닫기 버튼의 툴팁이 패널 위에 뜨기 위한 순서다** — 현행 모달은 top layer 라 이 툴팁이 가려졌다(부수적 개선) |

### JS 상태 모델 (패널 IIFE 스코프, 전역 없음)

| 이름 | 타입 | 의미 |
|------|------|------|
| `openDashboardKey` | `string \| null` | 열린 프로젝트의 `dashboard_key`. `null` 이면 닫힘. **열림 상태의 유일한 진실** |
| `panelOpenerElement` | `Element \| null` | 패널을 연 요소. 닫을 때 포커스를 되돌린다. 재렌더로 사라졌으면 `isConnected` 가 false |
| `pushModeQuery` | `MediaQueryList` | `(min-width:1024px)`. 오버레이 여부 판정의 단일 출처 |

### 공개 함수 시그니처 (템플릿 JS)

```js
function projectDashboardUrl(dashboardKey: string): string
    /** 대시보드 키로 서버 경로를 만든다. 순수 함수. */

function loadPanelDocument(url: string): void
    /** 패널 iframe 을 그 문서로 교체 이동시킨다(뒤로가기 기록을 남기지 않는다, SP9). */

function applyBackgroundInert(): void
    /** 오버레이 모드로 열려 있을 때만 배경(.wrap·#dzh-usage)을 inert 로, 패널을 aria-modal 로 만든다. */

function openDetailPanel(dashboardKey: string, displayName: string, openerElement: Element): void
    /** 패널을 열거나 이미 열린 패널의 내용을 바꾼다. 같은 프로젝트면 아무것도 하지 않는다(SP8). */

function closeDetailPanel(): void
    /** 패널을 닫고 iframe 을 about:blank 로 보낸다 — 숨은 5초 폴링을 반드시 멈춘다(R-6). */
```

---

## 구현 계획 (파일별)

### 1. `hub/bin/hub_template.html` — CSS (228~262행 **전체 교체**)

```css
  /* 프로젝트 상세 패널(SP1) — 카드 클릭 시 우측에서 밀려 들어오는 **비모달** 패널이다.
     <dialog> 를 쓰지 않는 이유(결정 SP1): 넓은 화면에서는 배경 목록을 계속 써야 하므로
     showModal() 의 포커스 트랩·inert 가 해가 되고, show() 는 ESC 를 주지 않으며
     ::backdrop 도 렌더되지 않아 결정 N5 가 근거로 삼은 "공짜" 넷이 모두 사라진다.
     기본 규칙이 좁은 화면(오버레이)이고 아래 min-width 쿼리가 넓은 화면(밀어내기)을
     덧쓴다 — 브레이크포인트 리터럴을 한 곳에만 두기 위한 배치다(GOTCHA 2).
     닫힌 상태를 visibility:hidden 으로 두는 것은 필수다 — transform 만으로 화면 밖에
     내보내면 닫힌 패널의 버튼이 Tab 순서와 접근성 트리에 그대로 남는다. */
  .detail-panel{position:fixed;top:0;right:0;bottom:0;left:0;z-index:30;
                display:flex;flex-direction:column;
                background:var(--surface);color:var(--ink);
                border-left:1px solid var(--line);box-shadow:-16px 0 48px rgba(0,0,0,.28);
                transform:translateX(100%);visibility:hidden}
  /* 전이 선언을 "열린 상태" 규칙 안에만 둔다 — 클래스가 붙는 순간에는 슬라이드가 재생되고,
     떨어지는 순간에는 전이 선언 자체가 사라져 즉시 닫힌다. 닫기 애니메이션을 만들지 않는
     결정(SP5, MD4 승계)을 JS 타이머 없이 CSS 만으로 표현하는 방법이다. */
  body.dzh-panel-open{overflow:hidden}
  body.dzh-panel-open .detail-panel{transform:none;visibility:visible;
                                    transition:transform 180ms ease-out}
  /* 밀어내기 모드 — 이 값(1024)은 JS 의 PANEL_PUSH_MIN_WIDTH_PX 와 같아야 한다(T25-78). */
  @media (min-width:1024px){
    .detail-panel{left:auto;width:var(--dzh-panel-width);border-radius:14px 0 0 14px}
    /* .usage 는 position:fixed 라 body 패딩을 따라오지 않는다 — 같은 폭만큼 직접 옮긴다. */
    body.dzh-panel-open{overflow:visible;padding-right:var(--dzh-panel-width);
                        transition:padding-right 180ms ease-out}
    body.dzh-panel-open #dzh-usage{transform:translateX(calc(-1 * var(--dzh-panel-width)));
                                   transition:transform 180ms ease-out}
  }
  /* 이 오버라이드는 위 세 규칙보다 반드시 뒤에 오고, 셀렉터를 그대로 반복해야 한다 —
     body.dzh-panel-open .detail-panel 은 (0,2,1)이라 .detail-panel 단독으로는 못 덮는다
     (모달 시절 같은 함정을 한 번 밟았다 — 옛 254~257행 주석). */
  @media (prefers-reduced-motion:reduce){
    body.dzh-panel-open,
    body.dzh-panel-open .detail-panel,
    body.dzh-panel-open #dzh-usage{transition:none}
  }
  .detail-head{display:flex;align-items:center;justify-content:space-between;gap:12px;
               padding:14px 18px;border-bottom:1px solid var(--line)}
  .detail-title{font-size:14px;font-weight:800;color:var(--head);overflow:hidden;
                text-overflow:ellipsis;white-space:nowrap}
  .detail-frame{flex:1 1 auto;width:100%;border:0}
```

`:root`(55~62행)에 1줄 추가 — 색 토큰 블록이 아니라 **테마 무관 값**이므로 다크 블록에는 넣지 않는다:

```css
    /* 패널 폭(SP4). 밀어내기 폭·.usage 이동량이 같은 값을 쓰게 하는 단일 출처다. */
    --dzh-panel-width:clamp(400px, 40vw, 720px);
```

### 2. `hub/bin/hub_template.html` — JS (1124~1177행 **전체 교체**)

```js
(function(){
  // 프로젝트 상세 패널(SP1~SP9) — 카드를 누르면 그 프로젝트의 dashboard.html 을 우측 패널의
  // iframe 으로 띄운다. <aside> 는 #dzh-app 바깥의 정적 마크업이라 폴링·틱과 무관하다
  // (불변식 H1⁗). 카드가 data-dashboard-key 를 가졌는지만으로 클릭 가능 여부가 정해지므로
  // (결정 N2·N7) 이 IIFE 는 snapshot 을 몰라도 된다 — 렌더 IIFE 와 완전히 분리돼 있다.
  var PANEL_OPEN_BODY_CLASS = 'dzh-panel-open';
  var PANEL_PUSH_MIN_WIDTH_PX = 1024;      // CSS 의 @media (min-width:1024px) 와 같은 값(GOTCHA 2)
  var PROJECT_DASHBOARD_PATH_PREFIX = '/project/';
  var PROJECT_DASHBOARD_PATH_SUFFIX = '/dashboard.html';
  var BLANK_DOCUMENT_URL = 'about:blank';
  var DASHBOARD_KEY_ATTRIBUTE = 'data-dashboard-key';
  var CLICKABLE_CARD_SELECTOR = '[' + DASHBOARD_KEY_ATTRIBUTE + ']';

  var panelEl = document.getElementById('dzh-detail-panel');
  var panelTitleEl = document.getElementById('dzh-detail-title');
  var panelFrameEl = document.getElementById('dzh-detail-frame');
  var panelCloseButton = document.getElementById('dzh-detail-close');
  var mainEl = document.querySelector('.wrap');
  var usageEl = document.getElementById('dzh-usage');
  if(!panelEl || !panelTitleEl || !panelFrameEl || !panelCloseButton || !mainEl) return;

  var pushModeQuery = matchMedia('(min-width:' + PANEL_PUSH_MIN_WIDTH_PX + 'px)');
  var openDashboardKey = null;      // 열림 상태의 유일한 진실. body 클래스는 이 값의 투영이다
  var panelOpenerElement = null;    // 닫을 때 포커스를 되돌릴 요소

  // 대시보드 키로 서버 경로를 만든다. 순수 함수.
  function projectDashboardUrl(dashboardKey){
    return PROJECT_DASHBOARD_PATH_PREFIX + dashboardKey + PROJECT_DASHBOARD_PATH_SUFFIX;
  }

  // 패널 iframe 을 그 문서로 교체 이동시킨다(SP9) — src 대입은 부모 문서의 히스토리에 항목을
  // 남겨, 카드를 옮겨 다닐수록 사용자의 뒤로가기가 허브가 아니라 iframe 을 되감게 된다.
  function loadPanelDocument(url){
    panelFrameEl.contentWindow.location.replace(url);
  }

  // 오버레이 모드로 열려 있을 때만 배경을 조작 불가로 만든다(SP3). 포커스 트랩 코드를 쓰지
  // 않는 이유이자, aria-modal 을 상시로 붙이지 않는 이유다 — 실제로 막았을 때만 그렇게 말한다.
  function applyBackgroundInert(){
    var isOverlayOpen = openDashboardKey !== null && !pushModeQuery.matches;
    mainEl.inert = isOverlayOpen;
    if(usageEl) usageEl.inert = isOverlayOpen;
    if(isOverlayOpen) panelEl.setAttribute('aria-modal', 'true');
    else panelEl.removeAttribute('aria-modal');
  }

  // 패널을 열거나 이미 열린 패널의 내용을 바꾼다. 같은 프로젝트면 아무것도 하지 않는다 —
  // 재로딩하면 읽던 대시보드의 스크롤 위치가 사라진다(결정 SP8).
  function openDetailPanel(dashboardKey, displayName, openerElement){
    if(dashboardKey === openDashboardKey) return;
    var wasClosed = openDashboardKey === null;
    openDashboardKey = dashboardKey;
    panelTitleEl.textContent = displayName;
    loadPanelDocument(projectDashboardUrl(dashboardKey));
    document.body.classList.add(PANEL_OPEN_BODY_CLASS);
    applyBackgroundInert();
    if(!wasClosed) return;                  // 내용 교체일 뿐이면 포커스를 건드리지 않는다
    panelOpenerElement = openerElement;
    panelCloseButton.focus();
  }

  // 패널을 닫고 iframe 을 비운다 — 숨은 iframe 의 5초 폴링을 반드시 멈춘다(리스크 R-6).
  // visibility:hidden 도 display:none 도 iframe 의 타이머를 멈추지 않는다.
  function closeDetailPanel(){
    if(openDashboardKey === null) return;
    openDashboardKey = null;
    document.body.classList.remove(PANEL_OPEN_BODY_CLASS);
    applyBackgroundInert();                 // 포커스 복귀보다 먼저 — inert 안의 요소는 포커스를 못 받는다
    loadPanelDocument(BLANK_DOCUMENT_URL);
    if(panelOpenerElement && panelOpenerElement.isConnected) panelOpenerElement.focus();
    panelOpenerElement = null;
  }

  panelCloseButton.addEventListener('click', closeDetailPanel);
  // 비모달 패널이라 브라우저가 ESC 를 대신 처리해 주지 않는다(SP1). iframe 안에 포커스가
  // 있으면 keydown 이 그 문서로 가 여기 오지 않는다 — 그래서 닫기 버튼이 1차 수단이다.
  document.addEventListener('keydown', function(event){
    if(event.key === 'Escape') closeDetailPanel();
  });
  // 열어 둔 채 창 크기를 바꾸면 모드가 바뀐다 — inert·aria-modal 을 다시 계산한다.
  pushModeQuery.addEventListener('change', applyBackgroundInert);

  document.addEventListener('click', function(event){
    if(event.target.closest('.card-drag-handle')) return;         // 결정 N6 — 드래그 핸들은 별도 조작
    if((window.getSelection() || {}).toString()) return;          // 결정 N6 — 텍스트 선택 후 클릭 무시
    var card = event.target.closest(CLICKABLE_CARD_SELECTOR);
    if(!card) return;
    var nameEl = card.querySelector('.project-name');
    openDetailPanel(card.getAttribute(DASHBOARD_KEY_ATTRIBUTE),
                    nameEl ? nameEl.textContent : '', nameEl || card);
  });
})();
```

### 3. `hub/bin/hub_template.html` — 1줄 수정 (1028행)

```js
    if(event.target.closest('dialog')) return;              // 옛 코드
    if(event.target.closest('#dzh-detail-panel')) return;   // 상세 패널 클릭은 페이지 클릭이 아니다(결정 Q4 승계)
```

### 4. `hub/README.md` — 「프로젝트 대시보드 모달」(185~205행) → 「프로젝트 상세 패널」

바뀌는 서술만:
- 제목과 도입 문장의 "모달" → "우측 상세 패널".
- "ESC·닫기 버튼·배경(바깥 어두운 영역) 클릭 세 가지 모두로 닫을 수 있다" → **"닫기 버튼과 ESC
  두 가지로 닫는다"**(배경 클릭 닫기는 사라진다 — SP3).
- "모달이 열리면 배경이 뚜렷하게 어둡게 눌리고…" 문단 → **"넓은 화면에서는 목록이 왼쪽으로
  밀리고 패널이 우측에서 미끄러져 들어온다. 목록은 그대로 보이고 다른 카드를 눌러 내용을 바꿀
  수 있다. 좁은 화면(1024px 미만)에서는 패널이 화면을 덮는다."**
- 5초 자동 갱신·PiP 버튼 숨김·`file://` 안내 3문단은 **그대로**(동작이 같다).
- 116~117행 「프라이버시 고지」의 "모달" 2회 → "상세 패널".

---

## GOTCHA (구현자가 틀리기 쉬운 함정)

1. **`transition` 을 `.detail-panel` 기본 규칙에 적으면 닫기까지 애니메이션된다.** 그 순간
   결정 SP5 의 전제가 깨지고, 슬라이드가 끝나기 전에 `about:blank` 가 실행돼 **빠져나가는 패널이
   흰 화면으로 번쩍인다.** 전이 선언은 반드시 `body.dzh-panel-open …` 규칙 **안에만** 둔다.
   > **개정(R2) — 이 항목은 정확히 반대로 뒤집혔다.** 닫기 애니메이션이 요구가 됐으므로 전이
   > 선언은 이제 **기본 규칙에 둔다**(SP12). 여기서 경고한 흰 번쩍임은 사라지지 않았고,
   > **`setTimeout(PANEL_CLOSE_ANIMATION_MS)` 지연**이 그것을 막는다(SP14). 이 문단의 인과
   > 분석(전이 위치 → 닫기 애니메이션 → blank 시점 문제)은 **여전히 옳으며 R2 설계의 출발점**이다.
   > 새 함정은 GOTCHA 11~18 을 보라.
2. **브레이크포인트가 두 곳에 산다.** CSS `@media (min-width:1024px)` 와 JS
   `PANEL_PUSH_MIN_WIDTH_PX = 1024`. 한쪽만 고치면 "밀어내는데 배경이 inert" 또는 "덮었는데
   배경에 Tab 이 들어간다"는 조용한 어긋남이 된다. **T25-78 이 두 숫자를 추출해 비교한다.**
   그래서 CSS 는 `1023.98px` 같은 반쪽 값을 쓰지 않고 모바일 퍼스트로 짠다.
3. **`prefers-reduced-motion` 오버라이드의 명세도.** `.detail-panel` 단독(0,1,0)으로는
   `body.dzh-panel-open .detail-panel`(0,2,1)의 `transition` 을 못 덮는다. **셀렉터를 그대로
   반복**하고, 반드시 소스 순서상 **뒤**에 둔다(모달 시절 같은 함정을 한 번 밟았다).
4. **오버레이 폭에 `100vw` 를 쓰지 마라.** `100vw` 는 세로 스크롤바 폭을 포함해 뷰포트보다
   넓어질 수 있고, `position:fixed` 요소의 우측 넘침은 브라우저에 따라 가로 스크롤바를 만든다.
   `left:0;right:0` 이면 산술 자체가 없다.
5. **`.usage` 는 `body` 패딩을 따라오지 않는다**(`position:fixed`). 밀어내기 모드에서 같은 폭만큼
   직접 옮기지 않으면 사용량 패널이 상세 패널 **밑에 깔린다**. 반대로 오버레이 모드에서는 옮기지
   않는다 — 패널이 전폭이라 어차피 덮인다.
6. **`inert` 해제보다 포커스 복귀가 먼저 오면 조용히 실패한다.** `closeDetailPanel()` 은
   `applyBackgroundInert()`(해제) → `focus()` 순서를 지켜야 한다. 순서를 바꾸면 포커스가
   `<body>` 로 떨어지고 아무 에러도 나지 않는다.
7. **`iframe.src` 대입으로 되돌아가지 마라(SP9 채택 시).** 디버깅 중 `panelFrameEl.src = url` 로
   바꾸면 동작은 같아 보이지만 뒤로가기 오염이 되살아난다. T25-80 이 역방향으로 막는다.
8. **`z-index:30` 을 40 이상으로 올리지 마라.** `.tooltip` 이 40 이고, 닫기 버튼의
   `data-tooltip="닫기 (Esc)"` 가 패널 위에 떠야 한다.
9. **ESC keydown 리스너가 하나 더 늘어난다.** 툴팁 IIFE 가 이미 461~463행에서 ESC 로
   `hideTooltip()` 을 한다. 두 리스너는 독립적으로 동작하며 `stopPropagation` 을 **쓰지 않는다**
   (이 파일에는 `stopPropagation` 이 0건이고, 넣는 순간 등록 순서에 의존하는 코드가 된다).
10. **머리 주석 개정을 잊지 마라.** `#dzh-dashboard-modal` 이 정적 노드 목록에 남아 있으면
    다음 사람이 존재하지 않는 노드를 불변식으로 지키게 된다(T25-76 이 역방향으로 막는다).

---

## 엣지 케이스

| # | 상황 | 동작 |
|---|------|------|
| E1 | 패널을 연 채 창을 1024px 아래로 줄인다 | CSS 가 오버레이로 전환(밀어내기 패딩 사라짐), `change` 리스너가 `inert`·`aria-modal` 을 켠다. 패널은 열린 채 유지 |
| E2 | 패널을 연 채 창을 1024px 위로 키운다 | 반대. `inert` 해제. iframe 재로딩 없음 |
| E3 | 열린 프로젝트가 스냅샷에서 사라진다 | **패널 유지**(결정 N8 승계). iframe 안 대시보드가 404 를 받아 스스로 "연결 끊김" 표시. 카드가 없으니 재클릭은 불가하고, 사용자가 닫으면 정상 종료 |
| E4 | 폴링이 `#dzh-app` 을 교체하는 순간 카드를 클릭 | 클릭은 `document` 위임이라 교체된 새 카드에서도 그대로 잡힌다. 교체 직전 노드를 눌렀다면 `openerElement.isConnected` 가 false 가 되고 닫을 때 포커스는 `<body>` 로 낙착 |
| E5 | iframe 안(대시보드)을 클릭한 뒤 ESC | **닫히지 않는다** — keydown 이 iframe 문서로 간다. 현행 모달도 동일한 한계라 회귀가 아니다. 닫기 버튼은 항상 보인다 |
| E6 | 텍스트를 드래그 선택하고 마우스를 놓았는데 카드 위였다 | 열지 않는다(결정 N6 가드 유지) |
| E7 | 드래그 핸들로 카드 순서를 바꾼다 | 패널과 무관. 핸들 클릭은 가드로 무시된다 |
| E8 | `file://` 로 허브를 열었다 | 카드에 `data-dashboard-key` 가 없어 클릭 대상이 아니다. 안내 툴팁만(결정 N7 승계). 패널 IIFE 는 아무 일도 하지 않는다 |
| E9 | 사용량 패널이 펼쳐진 상태에서 카드 클릭 | 사용량 패널은 접힌다(카드 클릭은 "바깥 클릭"이다 — 기존 동작). 닫기 버튼 클릭은 새 가드(`#dzh-detail-panel`)로 접지 않는다 |
| E10 | 프로젝트가 하나도 없다(빈 허브) | 클릭 대상이 없어 패널이 열릴 일이 없다 |
| E11 | 열린 패널의 프로젝트를 다시 클릭 | 무동작(SP8). 스크롤 위치·폴링이 그대로 유지된다 |
| E12 | reduced-motion 사용자 | 패널이 즉시 나타나고 메인도 즉시 밀린다. **기능은 하나도 잃지 않는다** |

---

## 테스트 계획 — `tests/run.sh`

### 기존 검사에 대한 영향 (전수 확인 결과)

| 검사 | 위치 | 처리 |
|------|------|------|
| **T25-63** | 3029~3046행 | **개정.** 토큰 `'<dialog id="dzh-dashboard-modal"'` → `'<aside id="dzh-detail-panel"'`, `'id="dzh-modal-frame"'` → `'id="dzh-detail-frame"'`. `.icon-btn`·`THEME_CYCLE`·`'system'` 검사는 **무수정** |
| **T25-64** | 3047~3057행 | **개정.** `hub/README.md` 문서 토큰 `"모달"` → `"상세 패널"`(README 개정과 짝) |
| **T25-66** | 3078~3096행 | **개정.** `closest('dialog')` → `closest('#dzh-detail-panel')`. `closest('#dzh-usage')` 검사와 **줄 번호 순서 검사는 무수정**(GOTCHA 2 강제 로직은 그대로 유효) |
| **T25-69** | 3158~3182행 | **폐기 → T25-77 로 대체.** `.modal::backdrop`·`.modal{` 테두리 검사는 대상 자체가 사라진다. README `'어둡'` 토큰 검사도 함께 폐기(배경 dim 이 없어진다) |
| **T25-70** | 3184~3191행 | **폐기 → T25-79 로 대체.** `animation:modal-open`·`@keyframes` 2종은 사라진다. **"애니메이션과 reduced-motion 무효화는 반드시 세트"라는 검사 의도는 T25-79 가 그대로 승계한다** |
| **T22-97·98·99** | 1780·1788·1795행 | **무수정.** CSS 셀렉터·판정식·식별자 등장 횟수만 본다(주석 문구 변경의 영향 없음 — 확인함) |
| **T22-101** | 1814~1822행 | **조건부 개정**(승인 항목 6 채택 시): `grep -qF '모달'` → `'패널'`. 미채택이면 무수정 |
| T25-65·67·68·71~75 | — | **무수정.** 모달과 무관한 토큰만 본다(확인함) |

### 신규 검사 (정방향 + 역방향 쌍)

`test_hub_docs_and_constants()`(2125행~, `test_name="T25"`)에 이어 붙인다. 현재 최대 번호는
**T25-75** 이므로 **T25-76** 부터 쓴다.

| # | 대상 | 정방향(있어야) | 역방향(없어야) |
|---|------|----------------|----------------|
| **T25-76** | SP1 마크업 | `<aside id="dzh-detail-panel"` · `id="dzh-detail-frame"` · `role="dialog"` · `aria-labelledby="dzh-detail-title"` | `<dialog id="dzh-dashboard-modal"` · `showModal(` · `dzh-modal-frame` · `#dzh-dashboard-modal`(머리 주석 잔재 포함) |
| **T25-77** | SP2·SP3 레이아웃 | `--dzh-panel-width:` · `padding-right:var(--dzh-panel-width)` · `translateX(calc(-1 * var(--dzh-panel-width)))` · `transform:translateX(100%)` · `visibility:hidden` | `.modal::backdrop{` · `@keyframes backdrop-fade` |
| **T25-78** | SP3 브레이크포인트 **일치**(기계적 강제) | CSS `@media (min-width:NNNNpx)` 의 숫자와 JS `PANEL_PUSH_MIN_WIDTH_PX = NNNN` 의 숫자를 각각 추출해 **같은지 비교**. 어느 한쪽이 없으면 실패 | — |
| **T25-79** | SP5 애니메이션 세트 + **소스 순서** | `transition:transform 180ms ease-out` · `prefers-reduced-motion` 블록 안의 `body.dzh-panel-open .detail-panel` · 그 블록의 줄 번호가 `body.dzh-panel-open .detail-panel{transform:none` 규칙보다 **크다** | `animation:modal-open` · `@keyframes modal-open` |
| **T25-80** | SP7·SP9 폴링 정지 | `about:blank` · `contentWindow.location.replace(` · `openDashboardKey` | `panelFrameEl.src` (src 대입 회귀) |
| **T25-81** | 문서 정합 | `hub/README.md` 에 `상세 패널` · `밀` · `덮` ; `hub_template.html` 머리 주석에 `H1⁗` | `hub/README.md` 에 `모달` **0건** |

> T25-78 의 구현 형태(선례: T25-66 의 줄 번호 비교, T22-99 의 등장 횟수 비교):
> ```bash
> css_breakpoint=$(grep -oE '@media \(min-width:[0-9]+px\)' "$hub_template_file" | head -1 | grep -oE '[0-9]+')
> js_breakpoint=$(grep -oE 'PANEL_PUSH_MIN_WIDTH_PX = [0-9]+' "$hub_template_file" | grep -oE '[0-9]+')
> [[ -n "$css_breakpoint" && "$css_breakpoint" == "$js_breakpoint" ]] || record_failure …
> ```

### 뮤테이션 검증 (구현 중 1회 — 검사가 **실제로 실패할 수 있는지** 확인)

각 신규 검사에 대해 아래 1줄 변형을 넣고 `bash tests/run.sh` 가 **빨간불**이 되는지 확인한 뒤
되돌린다. (이 저장소의 실측된 실패 유형: "검증을 추가할 때 그 검증이 실제 환경에서 성립하는지
먼저 확인한다".)

| 검사 | 변형 | 기대 |
|------|------|------|
| T25-76 | `<aside id="dzh-detail-panel"` → `<aside id="dzh-panel"` | 실패 |
| T25-76(역) | 머리 주석에 `#dzh-dashboard-modal` 한 단어를 되살린다 | 실패 |
| T25-77 | `padding-right:var(--dzh-panel-width)` → `padding-right:480px` | 실패 |
| T25-78 | CSS 만 `@media (min-width:1200px)` 로 바꾼다 | 실패 |
| T25-79 | `prefers-reduced-motion` 블록을 `.detail-panel` 규칙 **앞으로** 옮긴다 | 실패 |
| T25-79(역) | `@keyframes modal-open` 을 되살린다 | 실패 |
| T25-80 | `loadPanelDocument` 안을 `panelFrameEl.src = url` 로 되돌린다 | 실패 |
| T25-81 | `hub/README.md` 에 "모달" 한 단어를 되살린다 | 실패 |

### 수동 확인 (자동화 불가 — 브라우저 실측)

| # | 절차 | 기대 |
|---|------|------|
| M1 | 1440px 창에서 카드 클릭 | 목록이 왼쪽으로 밀리며 패널이 우측에서 미끄러져 들어온다. 카드가 3열 → 2열로 재배치. 사용량 패널도 함께 왼쪽으로 이동 |
| M2 | 패널이 열린 채 **다른** 카드 클릭 | 패널이 닫히지 않고 제목·내용만 바뀐다. 슬라이드 재생 없음 |
| M3 | **같은** 카드 재클릭 | 아무 변화 없음. 대시보드 스크롤 위치 유지(DevTools Network 에 새 요청 없음) |
| M4 | 900px 창에서 카드 클릭 | 패널이 화면을 덮는다. 배경 스크롤 불가, Tab 이 배경으로 나가지 않는다 |
| M5 | 닫기 후 DevTools Network 5분 관찰 | `/project/…/dashboard.html` 요청이 **더 이상 오지 않는다**(리스크 R-6) |
| M6 | 패널을 연 채 60초 이상 대기 | 배경 카드가 갱신되어도 패널·iframe 이 그대로다. 밀어내기도 유지 |
| M7 | 패널을 3번 열고 닫은 뒤 **뒤로가기** 1회 | 허브 이전 페이지로 나간다(iframe 되감기 없음 — SP9 채택 시) |
| M8 | OS 의 "동작 줄이기"를 켜고 M1 반복 | 즉시 나타난다. 기능 손실 없음 |
| M9 | 키보드만으로: Tab → `.project-name` → Enter | 패널이 열리고 포커스가 닫기 버튼에 있다. ESC 로 닫으면 원래 카드로 포커스 복귀 |
| M10 | 라이트·다크 두 테마에서 패널 경계 확인 | 좌측 테두리(`var(--line)`)와 그림자가 두 테마 모두에서 표면을 분리한다 |
| M11 | 닫기 버튼에 마우스를 올린다 | "닫기 (Esc)" 툴팁이 **패널 위에** 뜬다(현행 모달에서는 top layer 에 가려졌다) |

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| P-1 | **밀어내기 리플로우가 저사양 기기에서 끊긴다** | 180ms·열 때 1회로 제한. 후퇴 경로가 1줄이다(`body.dzh-panel-open` 의 `transition` 삭제 → 밀어내기 즉시, 슬라이드 유지). 측정 전 추가 최적화는 하지 않는다 |
| P-2 | **패널 안 대시보드가 좁아 읽기 불편** | `/dashboard` 템플릿에 `@media` 가 하나도 없음을 확인했다 — 좁아지면 `ellipsis` 로 정보가 준다. SP4 의 `clamp` 상한 720px 이 완화책이고, 그래도 부족하면 **폭 한 줄**을 키운다. 템플릿 축약 CSS 도입은 YAGNI 보류 3 **→ 재평가(R2 재검토, SP19 ③)**: 폭이 550 고정이 되면서 대시보드 내용폭이 **항상 517px** 이 됐다 — 초판이 승인 시점에 받아들였던 최악값(1024px 뷰포트에서 377px)보다 **항상 넓으므로 리스크가 커지지 않는다.** 잃는 것은 큰 화면에서의 상향 여지뿐이고, 후퇴 경로는 초판과 같은 **66행 한 줄**이다 |
| P-3 | **좁은 화면에서 배경 Tab 누수** | `inert` 로 막는다. `inert` 미지원 구형 브라우저에서는 시각적으로만 덮이는 수준으로 강등(기능은 유지) |
| P-4 | **모드 전환(리사이즈) 시 상태 불일치** | `matchMedia change` 리스너 하나가 `inert`·`aria-modal` 을 재계산한다. 밀어내기/오버레이 전환 자체는 CSS 가 한다(JS 개입 없음) — 상태를 두 곳에서 관리하지 않는 설계다 |
| P-5 | **브레이크포인트 이중 정의** | T25-78 이 기계적으로 강제(GOTCHA 2) |
| P-6 | **iframe 폴링이 안 멈춤(R-6 승계)** | 닫기의 유일한 경로가 `closeDetailPanel()` 이고 그 안에서 `about:blank` 로 보낸다. T25-80 + 수동 M5 |
| P-7 | **`contentWindow.location.replace` 가 예상과 다르게 동작** | 승인 항목 5 로 분리했다. 기각·문제 발생 시 `src` 대입으로 되돌리는 것이 1줄이며 다른 결정에 영향이 없다 |
| P-8 | **문서 이관 누락으로 옛 결정(N5·MD1)이 살아 있는 것처럼 읽힘** | SP6 의 이관 표기표를 구현 체크리스트에 넣는다. T25-81 이 README 잔재를 막는다(PRP 본문은 사람이 확인) |

---

## YAGNI 보류 (지금 만들지 않는다 + 재방문 트리거)

| # | 보류 항목 | 이유 | 재방문 트리거 |
|---|-----------|------|---------------|
| 1 | **패널 리사이즈 핸들** | 요구에 없다. 폭이 사용자 상태가 되면 `localStorage` 키 + 불변식 편입 + 드래그 핸들(카드 순서)과의 조작 개념 충돌이 한꺼번에 따라온다. `--dzh-panel-width` 한 줄로 조절 가능한 것을 UI 로 만들 필요가 없다 | 사용자가 폭을 **프로젝트마다 다르게** 두고 싶다고 말할 때 |
| 2 | **열린 프로젝트의 카드 하이라이트** | 카드는 매 렌더 재생성되므로 강조를 유지하려면 렌더 IIFE 가 패널 상태를 알아야 한다 → 지금 완전히 분리된 두 IIFE(H1⁗ 의 설계 의도)가 결합된다. 어떤 프로젝트인지는 **패널 제목**이 이미 말한다 | 카드가 20개를 넘어 "어느 걸 열었더라"가 실제 불편으로 보고될 때 |
| 3 | **패널 폭 전용 대시보드 축약 CSS**(`body.dz-embedded` 에 `dz-pip` 류 축약 적용) | `/dashboard` 템플릿 변경이 필요해 전제 2 를 깬다. 축약 CSS 는 이미 존재하지만(`body.dz-pip …`) 그것은 PiP 창 전용 규격이라 그대로 재사용하면 두 문맥이 한 클래스에 얽힌다 | P-2 가 실제 불편으로 보고되고, SP4 의 폭 상향으로도 해결되지 않을 때 |
| 4 | **닫기 애니메이션** | SP5. `about:blank` 지연과 재클릭 경쟁 상태를 불러온다 | 승인 항목 4 에서 사용자가 원한다고 답할 때(그때는 지연 타이머 + `openDashboardKey` 재진입 가드를 함께 설계한다) **→ 해소(R2, 2026-08-14): 트리거가 발동했고 예고한 두 가지를 그대로 설계했다(SP14·SP15)** |
| 5 | **여러 패널·탭·히스토리(뒤로가기로 패널 닫기)** | 요구에 없다. URL 상태화는 허브 서버의 라우팅 계약까지 건드린다 | 공유 가능한 딥링크(`/hub.html#project=<key>`) 요구가 나올 때 |

---

## 검토했으나 채택하지 않은 대안 (요약)

| 대안 | 기각 사유 |
|------|-----------|
| `<dialog>` 를 `show()` 로 유지 | ESC·`::backdrop`·트랩·inert 가 전부 사라져 `<dialog>` 를 쓸 이유가 없어지는데, `display:none` 토글이라는 부채만 남아 닫기/열기 애니메이션 처리를 `@starting-style`·`allow-discrete` 신문법으로 밀어낸다(SP1 안 B) |
| `popover="auto"` | light-dismiss 가 "다른 카드 클릭 = 내용 교체"와 정면 충돌한다. top layer 라 툴팁이 가려진다(SP1 안 C) |
| `grid-template-columns` 전이로 밀어내기 | 패널이 문서와 함께 스크롤돼 사라진다(SP2 안 B) |
| `.wrap` 에 `transform` 만 걸기 | 메인이 좁아지지 않고 좌측이 잘린다(SP2 안 A) |
| 좁은 화면에서 dim + 배경 클릭 닫기 | 전폭 패널이라 가려질 배경도, 누를 배경도 없다. 없는 것을 위한 코드다(SP3) |
| 화면 크기에 따라 `show()`/`showModal()` 을 갈아 끼우기 | 열어 둔 채 리사이즈하면 `close()` → 재오픈이 필요하고, `close` 핸들러가 iframe 을 비우는 것과 얽혀 **재진입 가드**가 필요해진다. CSS 미디어 쿼리 하나로 끝날 일을 JS 상태 기계로 만든다 |

---

## 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | CSS 교체(228~262행) + `:root` 1줄 + 머리 주석 개정 | 브라우저에서 패널이 **닫힌 상태로** 보이지 않는지, Tab 이 들어가지 않는지 |
| 2 | DOM 교체(306~314행) + JS IIFE 교체(1124~1177행) + 1028행 가드 | 수동 M1~M6, M9 |
| 3 | `tests/run.sh` 개정 5건 + 신규 6건 + 뮤테이션 8건 | `bash tests/run.sh` 전 항목 통과 |
| 4 | `hub/README.md` + PRP 이관 표기 4개 파일 | T25-81 통과 + 이관표 대조 |

---

## 승인 요청 항목

> 아래 6건은 취향·트레이드오프가 갈리는 지점이다. **각 항목의 권고안대로 진행해도 되는지**
> 확인해 주면 그대로 구현에 들어간다.

### 승인 항목 1 — 패널 폭: `clamp(400px, 40vw, 720px)` (결정 SP4)

> **→ 번복(R2, 2026-08-14) — 사용자 지시로 고정 550px.** 초판에서는 이 권고대로
> 채택·구현됐고(`hub_template.html` 66행), R2 재검토에서 사용자가 고정폭을 지시했다.
> 정본은 결정 **SP19**. 이 항목은 **재승인 대상이 아니다**(이미 확정된 지시다).
**권고: 채택.** 1280px 화면에서 512px, 1920px 화면에서 720px 이 된다. 고정폭은 큰 화면에서 대시보드를
좁게 가두고, 순수 비율은 작은 화면에서 읽을 수 없게 만든다. **대안:** 고정 `480px` / 더 넓은 상한 `860px`
(단 1920px 에서 카드 3열이 깨진다).

### 승인 항목 2 — 오버레이 전환 기준: **1024px**, **전폭**, **dim 없음**, **배경 클릭 닫기 없음** (결정 SP3)
**권고: 채택.** 1024px 은 "밀어내도 카드 1열이 여유 있게 남는 최소 크기"라는 산술에서 나온 값이다.
전폭이면 가릴 배경이 없어 dim·배경 클릭 닫기가 의미를 잃고, 그 대신 `inert` 로 키보드 접근만 막는다.
**대안:** 좁은 화면에서도 여백을 남긴 오버레이(32px 인셋) + 어두운 배경 + 배경 클릭 닫기(= 현행 모달에 가까운 경험).

### 승인 항목 3 — 넓은 화면에서 배경은 **계속 조작 가능**하다 (결정 SP1)
**권고: 채택.** 패널이 열린 채 스크롤·드래그 순서 변경·다른 카드 클릭이 전부 된다. 이것이 모달을
버리는 이유 자체다. **대안:** 밀어내되 배경을 `inert` 로 막는다(= 시각적으로만 패널, 실질은 모달).

### 승인 항목 4 — **닫기 애니메이션은 만들지 않는다** (결정 SP5, MD4 승계)

> **번복(R2, 2026-08-14)** — 사용자가 「닫힐 때도 애니메이션」을 명시 요구했다. 아래 **대안**
> 문구("닫기도 180ms — 이 경우 지연 타이머 + `openDashboardKey` 재진입 가드를 함께 넣는다")가
> 그대로 R2 의 설계 지시가 됐다 → 결정 SP12·SP14·SP15.

**권고: 채택(만들지 않음).** 열기 180ms 슬라이드만 둔다. 닫기를 애니메이션하면 `about:blank` 를
슬라이드 종료까지 미뤄야 하고, 그 지연 중 재클릭이 들어오면 새로 연 패널을 지연 타이머가 지우는
경쟁 상태가 생긴다. **대안:** 닫기도 180ms — 이 경우 지연 타이머 + `openDashboardKey` 재진입 가드를 함께 넣는다.

### 승인 항목 5 — iframe 이동을 `contentWindow.location.replace()` 로 바꾼다 (결정 SP9)
**권고: 채택.** 요구에 없는 개선이지만, 패널은 카드를 옮겨 다니며 쓰는 UI 라 `src` 대입이 남기는
뒤로가기 항목이 클릭 수만큼 쌓인다(지금도 있는 문제이나 빈도가 달라진다). **대안:** 기존 `src` 대입 유지
(되돌리는 비용 1줄).

### 승인 항목 6 — `commands/dashboard.md` 의 "허브 모달" 표현 10곳을 "허브 상세 패널"로 고친다 (결정 SP10)
**권고: 채택하되 문구만.** 동작 계약(`body.dz-embedded`, `self !== top`)은 한 글자도 바꾸지 않는다.
특히 975행은 `/dashboard init` **사용자 보고 문구**("이 대시보드가 모달로 열립니다")라 화면과 어긋나면
그 자체가 버그다. 채택 시 T22-101 의 grep 토큰(`'모달'` → `'패널'`)도 함께 고친다.
**대안:** 허브 밖 파급을 0 으로 두고 문구를 방치(문서와 화면이 어긋난 채로 남는다) / 975행 한 줄만 수정.

---

# R2 개정 (2026-08-14) — 헤드 패널화 + 닫기 애니메이션 + 폭 고정

> 초판이 배포된 뒤 들어온 후속 요구 2건 + 재검토에서 확정된 폭 1건.
> **줄 번호 기준선(2026-08-14 재검토)**: 이 절의 모든 줄 번호는 **HEAD `12d49d6`(PR #3 병합 후)의
> 실제 파일을 읽고 확인한 값**이다. 초안은 `a378aaa` 기준이었고, PR #3 이 `commands/dashboard.md`
> (+322줄)와 `tests/run.sh`(+248줄)를 바꿔 **두 파일의 인용이 전부 시프트됐다** — 재검토에서
> `tests/run.sh` 의 T25 계열은 일괄 **+222**, T22 계열은 일괄 **+36** 이동했음을 확인하고 갱신했다.
> **`hub/bin/hub_template.html` 은 PR #3 의 변경 대상이 아니므로(`git show --stat 12d49d6` 확인)
> 그 파일 인용은 초안 그대로 유효하다.** 재검토에서 다음 범위를 직접 다시 읽어 확인했다 —
> 20~24·33~36·52~55(머리 주석) · 60~62·66·71~72·80~81(색 토큰과 `--dzh-panel-width`) ·
> 86·94(`box-sizing`·그리드) · 122·126~130·134~136·145·157·158·163(카드 헤더 관용구) ·
> 181·186~191(`.icon-btn`) · 201·202·206·211~213·218·228(사용량 패널·툴팁) ·
> 241~273(패널 CSS 전체) · 279~285(테마 확정 스크립트) · 293·301·317~325(DOM) ·
> 422·432·453·455(툴팁 타이머 관용구) · 1140~1156·1183~1206·1208~1225(패널 IIFE).
> **불일치는 0건이었다.**

| 항목 | 값 |
|------|-----|
| 요구 | ① `aside#dzh-detail-panel` 의 **헤드가 다이얼로그 UI 같다 → 패널 UI 로 고친다** ② **닫힐 때도 애니메이션한다** ③ **패널 가로 폭을 고정 550px 로**(재검토에서 추가된 사용자 지시) |
| 대상 | `hub/bin/hub_template.html` **1개 파일이 기능의 전부** + `tests/run.sh` + `hub/README.md` + PRP 2개(이 문서·`hub-first-entry-and-ui-signals.md`) |
| 규모 | **Small** — 템플릿 순증 약 **+14 / −8줄** + `:root` 1줄 **값 치환**(순증 0). 새 CSS 클래스 1개(`.detail-close`), 새 JS 함수 1개(`scheduleBlankAfterSlide`), 새 상수 1개(`PANEL_CLOSE_ANIMATION_MS`) |
| **Python 변경** | **없음** — 초판과 같다. 순수 표현 계층이다 |
| **`commands/dashboard.md` 변경** | **없음** — PR #3 이 이미 바꿨고, R2 는 그 결과를 **읽기만** 한다(초판 전제 2 유지). 재검토가 바꾼 것은 **이 문서의 근거 문장과 인용 줄 번호**이지 그 파일이 아니다 |
| 새 외부 의존성 | **없음**. **새 색 리터럴 0개** — 요구 1 은 기존 토큰(`--line`·`--muted`·`--head`·`--accent`·`--accent-ink`)만 쓴다 |
| 번복되는 초판 결정 | **SP5**(닫기 미도입) · **GOTCHA 1**(전이를 기본 규칙에 두지 마라) · **승인 항목 4**(미도입 채택) · **YAGNI 보류 4**(해소 — 그 트리거가 예고한 설계를 여기서 한다) · **SP4**(폭 `clamp` → 고정 550px, 결정 SP19) · **승인 항목 1**(같은 건) |
| 승인 상태 | **재승인 대기** — 「R2 재승인 요청 항목」 1~5. 초안의 항목 1(헤드 시안)·패널 폭은 **확정**되어 아래 「R2 확정 사항」으로 이동했다 |

## R2 확정 사항 (사용자 지시 — 재론하지 않는다)

> 초안 승인 요청에서 사용자가 **보류**를 택했고, 그 자리에서 두 가지가 확정됐다.
> 이 둘은 **재승인 항목이 아니다.** 아래는 확정 내용과, 최신 소스 기준으로 재검증한 결과다.

| # | 확정 | 정본 | 재검토 결과 |
|---|------|------|-------------|
| C1 | **헤드 시안 A** — 구분선 삭제 · 카드 제목과 같은 타이포 · 24px 투명 사각 버튼 · `»` 글리프 | 결정 **SP11** | **유지.** 단 **구분선 삭제의 근거 문단이 통째로 교체됐다**(PR #3 이 그 문단의 사실 전제를 무효화했다). 새 근거는 SP11 의 「구분선 근거 — R2 재검토 개정」. 시안 A CSS 는 **`padding` 의 좌우 값 18px → 16px 한 곳만** 바뀐다(정렬 근거는 같은 절) |
| C2 | **패널 가로 폭 = 고정 `550px`** | 결정 **SP19**(초판 SP4·초판 승인 항목 1 을 번복) | **성립.** 브레이크포인트 1024px 유지가 타당함을 재도출했고, 1920px 에서 카드 3열이 유지됨을 확인했다. `--dzh-panel-width` 가 `:root` 한 줄이라는 구조는 그대로이며 T25-77·T25-78 은 **무수정**이다 |

**보류 사유였던 「최신 소스 기준 재검토」의 결론 한 줄**: PR #3 이 대시보드에 허브 색 토큰과
다크 모드를 이식하면서 **패널 헤드와 iframe 내용 사이의 「색 단차」가 사라졌다**(양쪽이 같은
`--surface` 가 됐다). 그러나 그 자리에 **iframe 문서 첫 카드의 상단 테두리(1px `var(--line)`,
좌우 16px 인셋, 반경 14px)** 가 정확히 들어와 있어 **시안 A(구분선 없음)는 보완책 없이 성립한다**
— 근거는 바뀌었고 결론은 그대로다. 자세한 대조는 SP11 을 보라.

## R2 요구사항 요약

초판은 모달을 우측 패널로 바꿨지만 **헤드 부분은 옛 `.modal-head` 를 글자 하나 바꾸지 않고
승계했다**(제목 span + `✕` 원형 버튼 + 전폭 `border-bottom` — 전형적인 다이얼로그 타이틀바).
표면은 패널인데 머리는 여전히 창(window)이라 말하고 있다. 또한 초판은 **열 때만** 애니메이션하고
닫을 때는 즉시 사라지게 했는데(결정 SP5), 실제로 써 보면 들어올 때와 나갈 때가 비대칭이라
"닫혔다"가 아니라 "사라졌다"로 읽힌다. R2 는 이 둘을 고친다.

### R2 사용자 스토리

| # | 스토리 |
|---|--------|
| S6 | 패널의 머리를 봤을 때 **다이얼로그 창이 아니라 화면의 한 구역**으로 읽힌다. 닫기 컨트롤은 "창을 없앤다(✕)"가 아니라 "오른쪽으로 밀어 보낸다(»)"고 말한다 |
| S7 | 닫기 버튼·ESC 를 누르면 패널이 **들어올 때와 같은 속도로 오른쪽으로 미끄러져 나가고**, 밀렸던 목록도 같은 시간에 걸쳐 제자리로 돌아온다 |
| S8 | 나가는 동안 패널 안이 **흰 화면으로 번쩍이지 않는다** — 내용을 유지한 채로 나간다 |
| S9 | 나가는 도중에 다른 카드를 눌러도 **새로 연 패널이 지워지지 않는다** |
| S10 | "동작 줄이기"를 켠 사용자는 R1 과 똑같이 **즉시** 열리고 닫힌다. 잃는 기능이 없다 |

### R2 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G8 | `hub_template.html` 에 `border-bottom` 이 **0건**이다(현재 유일한 1건이 `.detail-head` 다 — 270행. **병합 후 재확인: `grep -c` 결과 여전히 1**) | T25-85 |
| G9 | 닫기 버튼이 `.icon-btn`(페이지 최상위 액션 표기)을 쓰지 않고 `.detail-close` 를 쓰며, `aria-label="닫기"`·`data-tooltip="닫기 (Esc)"` 는 그대로다 | T25-85 |
| G10 | `transition` 선언이 **닫힌(기본) 규칙**에 있고 `visibility` 가 같은 시간으로 함께 전이된다 | T25-79(개정) |
| G11 | CSS 슬라이드 시간 · CSS `visibility` 시간 · JS `PANEL_CLOSE_ANIMATION_MS` **세 숫자가 기계적으로 같다** | T25-84 |
| G12 | `about:blank` 지연에 `transitionend` 를 **쓰지 않는다**(0건). 지연 취소는 `openDetailPanel` 안에서만 일어난다 | T25-82 · T25-83 |
| G13 | 닫는 중 재클릭이 새로 연 패널을 지우지 않는다 | 수동 M13 · M14 |
| **G14** | `--dzh-panel-width` 가 **고정 `550px`** 이고 여전히 `:root` **한 줄**이며, 밀어내기 폭·`.usage` 이동량이 그 토큰을 통해서만 쓰인다 | T25-77(무수정) · 수동 **M21** |
| **G15** | 패널 헤드의 제목·닫기 컨트롤이 **아래 대시보드 카드의 좌·우변과 같은 x 좌표**에 선다(좌우 패딩 16px) | 수동 **M18**(개정) |

---

## R2 확정된 전제 (재론하지 않는다)

1. **초판의 전제 1~5 는 전부 그대로다.** 파이썬 무변경, `/dashboard` 계약 무변경, `file://` 비대상,
   새 색 토큰 금지, 불변식 H1 계열 유지.
2. **`role="dialog"` 와 `aria-labelledby="dzh-detail-title"` 는 건드리지 않는다.** 요구 1 은 **시각**
   요구다. 접근성 역할까지 함께 바꾸면(`complementary`·`region`) SP1 이 근거로 든 "닫을 수 있는
   일시적 표면"이라는 성질이 스크린리더에서 사라진다 — 화면에서 덜 창처럼 보이는 것과, 보조기술에
   창이 아니라고 말하는 것은 다른 문제다. T25-76 이 두 토큰을 이미 지키고 있다(3484행).
3. **`z-index:30` 도 그대로다**(GOTCHA 8 유효). 닫기 컨트롤의 툴팁이 패널 위에 떠야 한다.
4. **헤드 마크업 변경은 불변식 H1⁗ 에 무영향이다.** `#dzh-detail-panel` 은 폴링이 절대 교체하지
   않는 정적 노드이고(머리 주석 23~24행), 이번 변경은 **그 정적 노드 내부의 정적 마크업**을 바꾼다.
   렌더 IIFE 는 이 서브트리를 읽지도 쓰지도 않는다(확인함 — 패널 IIFE 만 `getElementById` 로 잡는다,
   1148~1151행).

### R2 비목표

| 항목 | 이유 |
|------|------|
| 패널 헤더에 액션 추가(새 탭에서 열기·고정 등) | 요구에 없다. 헤드를 "패널처럼" 만드는 것과 기능을 얹는 것은 별개다 |
| `role`·`aria-modal` 배선 변경 | 전제 2 |
| 열기 애니메이션의 시간·이징 변경 | 요구는 "닫을 때도"이지 "열 때 다르게"가 아니다. 180ms 는 그대로 쓴다 |
| 패널 안 대시보드(iframe 문서)의 헤더 | `/dashboard` 템플릿 변경 = 초판 전제 2 위반 |
| 뒤로가기로 패널 닫기 / 딥링크 | 초판 YAGNI 보류 5 그대로 |

---

## R2 영향 범위

### 수정 파일 (5개)

| 파일 | 무엇을 | 왜 |
|------|--------|-----|
| `hub/bin/hub_template.html` | ① 머리 주석 33~36행 조항 ③ 뒤에 **조항 ④ 신설**(닫기 지연·타이머 불변식) ② `.icon-btn` 주석 181행의 "모달 닫기 버튼" 문구 개정 ③ 패널 CSS 241~273행 중 **전이 3개를 기본 규칙으로 이동 + `visibility`·`pointer-events` 추가**(SP12·SP13·SP16) ④ `prefers-reduced-motion` 블록 264~268행 **셀렉터 6개로 확장**(SP17) ⑤ `.detail-head`·`.detail-title` 269~272행 **교체** + `.detail-close` 신설(SP11, 헤드 좌우 패딩 **16px**) ⑥ DOM 320~321행 닫기 버튼 class·글리프 교체 ⑦ JS 1140~1146행 상수 1개 추가, 1183~1206행 open/close 개정, `scheduleBlankAfterSlide` 신설 **⑧ `:root` 66행 `--dzh-panel-width` 값을 `clamp(400px, 40vw, 720px)` → `550px` 로 치환**(SP19, 순증 0줄) | 요구 1·2·3 전부 |
| `tests/run.sh` | **T25-79 개정**(3527~3547행), **신규 T25-82~T25-85**, **함수 설명 문자열 2곳 갱신**(2346행 주석·2349행 `test_desc` 의 `T25-1~T25-81` → `T25-1~T25-85`). T25-63·76·77·78·80 은 **무수정**, T25-81 은 토큰 1개 추가(영향 전수 확인 결과 아래 표) | 회귀 검사 |
| `hub/README.md` | 204~205행에 닫힘 서술 1문장 추가(“같은 시간에 걸쳐 미끄러져 나간다”), 202행의 닫기 수단 문장은 그대로 | 사용자 문서 |
| `docs/prps/hub-detail-side-panel.md` | **이 R2 절**(SP5·GOTCHA 1·승인 항목 4·YAGNI 보류 4 에 개정 화살표 + R2 본문) | 정본 |
| `docs/prps/hub-first-entry-and-ui-signals.md` | 결정 MD4 의 이관 표기 **재개정**(아래 이관 표기표) | 정본 이관 |

### 미영향 — 건드리지 않는 이유 (직접 확인함)

| 대상 | 근거 |
|------|------|
| `hub/bin/*.py` 전부 | 초판과 동일. 표현 계층만 바뀐다 |
| `commands/dashboard.md` | **R2 는 이 파일을 한 글자도 바꾸지 않는다**(초판 전제 2 유지). PR #3 이 이미 이 파일을 크게 바꿨지만(+322줄) 그 변경은 **R2 의 입력**이지 대상이 아니다 — R2 가 하는 일은 그 결과를 **읽어 SP11 의 근거를 갱신**한 것뿐이다. `body.dz-embedded` 판정(`window.self !== window.top`)도, iframe 안 문서의 폴링·PiP 계약도 그대로다 |
| `.icon-btn` **규칙 자체**(186~191행) | 헤더의 새로고침·테마 버튼 2개가 계속 쓴다. **주석 1줄만** 개정한다(닫기 버튼이 빠지므로) |
| `.tooltip`(228행) · 툴팁 IIFE | `data-tooltip` 속성을 유지하므로 배선이 그대로다. `.detail-close` 는 새 클래스일 뿐 트리거 조건(속성 존재)은 같다 |
| 패널 IIFE 의 클릭 위임·ESC·`matchMedia` 배선(1208~1225행) | 닫기 **경로**는 그대로 `closeDetailPanel()` 하나다. 바뀌는 것은 그 함수의 마지막 두 줄뿐이다 |
| `#dzh-usage` 접힘 로직 | `#dzh-usage` 에 `transition:transform` 을 더하지만 접힘은 `width`·`padding` 을 바꾼다 — 전이 속성 목록에 없다(GOTCHA 14) |

---

## 결정 기록 (R2)

### 결정 SP11 — 헤드를 **패널 헤더**로: 구분선 제거 · 후행 컨트롤 강등 · 방향성 글리프

**"다이얼로그 타이틀바"의 정체를 먼저 특정한다.** 현재 헤드(269~272·318~322행)가 창처럼 읽히는
이유는 넷이고, 전부 이 저장소의 다른 헤더에는 **없는** 것들이다.

| # | 현재 헤드의 특징 | 이 허브의 다른 헤더는? |
|---|------------------|------------------------|
| 1 | 전폭 `border-bottom:1px solid var(--line)`(270행) | **`border-bottom` 은 이 파일 전체에서 이 한 줄뿐이다**(전수 grep 확인). `.project-head`(122행)·`.usage-toggle`(206행) 어느 쪽도 구분선을 쓰지 않는다. `.sessions li` 의 `border-top:1px solid var(--soft)`(163행)는 목록 구분자이고 색 토큰도 다르다 |
| 2 | `✕` 글리프 — "이 창을 없앤다" | 허브에 `✕` 는 이 하나뿐이다. 접힘은 `▾/▸`(212~213행), 순서는 그랩 핸들 — **전부 방향·상태를 가리키는 글리프**다 |
| 3 | 닫기 버튼이 `.icon-btn`(32px 원형·`--surface` 배경·`box-shadow`, 186~188행) | `.icon-btn` 은 **페이지 최상위 액션**(새로고침·테마)의 표기다. 그 주석(181행)이 스스로 "헤더 클러스터의 두 버튼과 **모달** 닫기 버튼이 공유한다"고 적고 있다 — **모달이 사라진 지금 이 공유는 근거를 잃었다**. **[R2 재검토 보강]** PR #3 이 `.icon-btn` 을 대시보드에도 이식했는데(`commands/dashboard.md` 1339~1343행) **그쪽 사용처는 `#dz-theme-toggle` 단 하나, 역시 페이지 최상위 액션이다**(1383행). 즉 두 템플릿을 합쳐 `.icon-btn` 사용처 4곳 중 **패널 닫기 버튼만 최상위 액션이 아니다** |
| 4 | `justify-content:space-between`(269행) | 이 파일에서 이 선언은 `.usage-row`(218행, 라벨/값 행)와 여기뿐이다. 헤더의 관용구는 **후행 요소에 `margin-left:auto`** 이거나(`.last-activity` 157행·`.usage-caret` 211행) **선행 요소에 `flex:1 1 auto`** 다(`.project-name` 135행) |

> **결정 SP11 — 시안 A 채택**(세 시안 비교는 다음 절). 위 4가지를 전부 이 허브의 관용구로 바꾼다:
> **구분선 삭제 · 제목은 `.project-name` 과 같은 타이포(15px/800/`--head`) + `flex:1 1 auto` ·
> 닫기 컨트롤은 `.card-drag-handle` 계열의 24px 투명 사각 버튼 · 글리프는 `»`.**

**구분선을 지워도 헤드와 내용이 붙어 보이지 않는 근거(직접 확인함).** 패널 아래쪽은 iframe 이고,
그 문서(`/dashboard` 템플릿)의 `body` 배경은 **`#EEF3F8` 하드코딩**이다(`commands/dashboard.md`
1199행). 그 파일에 `prefers-color-scheme`·`data-theme` 은 **0건**이라 다크 변형이 없다. 즉
라이트 테마에서는 `#FFFFFF`(`--surface`) 위의 `#EEF3F8`, 다크 테마에서는 `#16202D` 위의 `#EEF3F8` —
**두 테마 모두 헤드와 내용 사이에 이미 색 단차가 있다.** 지금의 `border-bottom` 은 그 단차 위에
한 줄을 더 얹은 중복 장식이고, 그 중복이 정확히 "창틀"로 읽힌다.

> **→ 개정(R2 재검토, 2026-08-14) — 위 문단의 사실 전제는 PR #3(`12d49d6`)이 무효화했다.**
> 원문은 남긴다(무엇이 왜 틀렸는지 읽을 수 있어야 하므로). **결론(구분선 삭제)은 유지되고,
> 근거는 아래로 통째로 교체된다.** 아래 내용은 전부 병합 후 파일을 직접 읽어 확인한 것이다.

#### 구분선 근거 — R2 재검토 개정 (최신 소스 대조)

**① 「하드코딩·다크 변형 없음」은 더 이상 사실이 아니다.** PR #3 이 대시보드에 허브의 색 토큰
전체와 다크 모드를 이식했다. 두 파일의 값은 **문자 그대로 동일하다**:

| 토큰 | 허브 `hub_template.html` | 대시보드 `commands/dashboard.md` |
|------|--------------------------|----------------------------------|
| `--bg` (라이트/다크) | `#EEF3F8` / `#0E1621` (60·71·80행) | `#EEF3F8` / `#0E1621` (1246·1255·1264행) |
| `--surface` (라이트/다크) | `#FFFFFF` / `#16202D` (60·71·80행) | `#FFFFFF` / `#16202D` (1246·1255·1264행) |
| `--line` (라이트/다크) | `#D9E2EC` / `#26364A` (61·72·81행) | `#D9E2EC` / `#26364A` (1247·1256·1265행) |

`body{…background:var(--bg)}`(1271행)로 바뀌었고 다크 변형이 둘(`@media (prefers-color-scheme:dark)`
1252행 · `:root[data-theme="dark"]` 1262행) 생겼다. 게다가 **패널 안에서는 테마가 반드시 허브와
일치한다** — 임베드 문서는 `dzh-theme` 를 읽기 전용으로 추종하고(`<head>` FOUC 스크립트 1367~1375행,
본문 IIFE 1593~1666행, `storage` 리스너 포함), 허브는 첫 로드에서 그 키를 **반드시 기록한다**
(`hub_template.html` 279~285행). 즉 "패널은 다크인데 iframe 은 라이트" 같은 조합이 생길 수 없다.

**② 그래서 「색 단차」는 사라졌다 — 헤드 바로 아래에서 만나는 두 면이 같은 `--surface` 다.**
경로를 끝까지 따라가면 이렇다:

1. `body.dz-embedded #dz-page-head{display:none}`(1352행) — 패널 안에서는 대시보드 자신의 헤더가
   통째로 숨는다. 그 규칙의 주석이 이유를 직접 적고 있다: *"허브 상세 패널의 헤드가 같은 프로젝트
   명을 이미 표시한다(hub_template.html 의 패널 제목)"*(1350~1351행).
2. `.wrap{max-width:860px;margin:0 auto 32px;padding:0 16px}`(1272행) — **PR #3 이 `margin:32px auto`
   에서 바꿨다.** 위 여백이 `#dz-page-head` 로 옮겨갔고, 그 헤더는 1 에 의해 숨는다.
3. 결과: 첫 `.card{background:var(--surface);border:1px solid var(--line);border-radius:14px}`(1273행)
   가 **iframe 최상단에 밀착**한다. 패널 표면도 `var(--surface)`(`hub_template.html` 243행) →
   **두 테마 모두 같은 색이 맞닿는다.** 초안이 근거로 삼은 단차는 없다.

**③ 그러나 그 자리에는 더 나은 경계가 이미 들어와 있다.** 밀착한 첫 카드가 가져오는 것은
**1px `var(--line)` 상단 테두리 + 좌우 16px 인셋(`.wrap` 패딩) + 14px 라운드 코너**다. 인셋
바깥 16px 에는 `--bg` 가 보인다. 라이트에서는 `#FFFFFF` 위의 `#D9E2EC`, 다크에서는 `#16202D`
위의 `#26364A` — **허브 자신이 모든 카드 경계에 쓰는 바로 그 조합이고, 두 테마 모두에서 검증된
것이다.** 이것은 초판이 「차선」으로 두었던 **시안 C(인셋 구분선)의 시각을 iframe 내용이 공짜로
제공**하는 것과 같다. 그러므로 `.detail-head` 의 `border-bottom` 은 **인셋 선 위에 전폭 선을 하나
더 얹는 이중선**이고, 그 이중성이 정확히 "창틀"로 읽힌다 — **초안의 결론 문장은 근거만 바뀐 채
그대로 성립한다.** 보완책은 필요 없다.

**④ 세로 리듬도 우연이 아니라 대응 관계다.** 단독 창에서 카드 위 여백은
`#dz-page-head{max-width:860px;margin:28px auto 10px;padding:0 16px}`(1326~1327행)의 **아래 10px**
이다. 패널에서는 그 헤더가 숨으므로 그 10px 의 역할을 **패널 헤드의 `padding-bottom`** 이 대신한다
→ 시안 A 의 `12px` 이 그 대응물이다(10 vs 12, 사실상 같은 리듬).

**⑤ 가로 정렬 — 초안의 `18px` 을 `16px` 로 고친다(시안 A 안에서의 유일한 수치 변경).**
단독 창에서는 `#dz-page-head{padding:0 16px}` 와 `.wrap{padding:0 16px}` 가 프로젝트명과 카드
좌변을 **같은 16px** 에 세운다. 패널에서도 같아야 한다 — `.detail-frame{width:100%;border:0}`
(273행)이 패널 **콘텐츠 박스**를 가득 채우므로 iframe 내부의 16px 과 `.detail-head` 의 좌우
패딩은 **원점이 같다.** 따라서 `padding:16px 18px 12px` → **`padding:16px 16px 12px`** 면
제목·닫기 컨트롤이 아래 카드의 좌·우변과 정확히 맞는다. `18px` 이면 2px 어긋난다.
**정직한 단서**: iframe 안에 클래식(자리를 차지하는) 세로 스크롤바가 뜨는 환경에서는 내용이
그만큼 왼쪽으로 밀려 우변 정렬이 그만큼 어긋난다 — 오버레이 스크롤바 환경(macOS 기본)에서는
어긋나지 않는다. 이 차이는 CSS 로 없앨 수 없고 **수동 M18 이 확인한다**(설계 변경 사유가 아니다).

**⑥ 시안 B 를 기각한 근거가 하나 더 늘었다(파일 간 계약).** 초판 YAGNI 보류 2 의 논거
("어떤 프로젝트인지는 패널 제목이 이미 말한다") 위에, 이제 **대시보드 템플릿이 자기 헤더를 숨기는
근거로 그 사실을 명시적으로 인용한다**(1350~1352행, 검사 **T22-124** 가 그 규칙을 고정한다).
패널 제목을 보조 텍스트로 낮추면 **두 문서 어디에도 프로젝트명이 제대로 표시되지 않는다.**

**`»` 를 고르는 이유는 R2 요구 2 와 맞물린다.** 초판에서는 닫기가 즉시였으므로 방향성 글리프가
일어나지 않는 동작을 약속하는 꼴이었다. R2 에서 패널이 **실제로 오른쪽으로 미끄러져 나가므로**
`»` 는 그 동작의 예고가 된다. 두 요구가 서로를 정당화하는 지점이다.
접근성은 강등되지 않는다 — `aria-label="닫기"` 가 접근성 이름을 고정하고(글리프는 이름이 아니다),
`data-tooltip="닫기 (Esc)"` 가 마우스·키보드 사용자에게 문구를 준다. **둘 다 그대로 유지한다.**

### 헤드 시안 비교 (CSS 전문)

세 시안 모두 마크업 골격(`div.detail-head > span#dzh-detail-title + button#dzh-detail-close`)과
`aria-labelledby` 관계를 유지한다. 바뀌는 것은 CSS 와 버튼의 `class`·글리프뿐이다.

#### 시안 A — **패널 헤더** (권고)

```css
  /* 패널 헤더(SP11) — 다이얼로그 타이틀바가 아니다. 이 허브의 헤더 관용구를 그대로 쓴다:
     구분선 없음(.project-head·.usage-toggle 어느 쪽도 쓰지 않는다), 제목이 flex:1 1 auto 로
     남는 폭을 먹고 컨트롤이 자연히 오른쪽 끝에 선다(.project-head 와 같은 구성).
     border-bottom 을 지워도 경계가 흐려지지 않는다 — 아래 iframe 문서의 첫 카드가 자기
     상단 테두리(1px var(--line), 좌우 16px 인셋, 반경 14px)를 그 자리에 이미 그린다
     (commands/dashboard.md 1272~1273행 + 1352행: 패널 안에서는 #dz-page-head 가 숨어
     .wrap 이 최상단에 밀착한다). 두 파일의 색 토큰 값이 동일하므로 라이트·다크 모두 성립한다.
     좌우 패딩 16px 은 취향이 아니라 정렬값이다 — iframe 이 패널 콘텐츠 박스를 가득 채우므로
     이 16px 과 대시보드 .wrap 의 padding:0 16px 이 같은 원점을 공유한다(SP11 ⑤). */
  .detail-head{display:flex;align-items:center;gap:10px;padding:16px 16px 12px}
  .detail-title{font-size:15px;font-weight:800;color:var(--head);overflow:hidden;
                text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1 1 auto}
  /* 닫기 컨트롤 — .icon-btn(32px 원형·그림자)은 페이지 최상위 액션(새로고침·테마)의 표기라
     패널 안 컨트롤이 그것을 쓰면 헤드가 창 제목줄로 읽힌다. 카드의 .card-drag-handle 과
     같은 계열(작고 투명하고 사각)로 낮춰 "이 구역의 컨트롤"이라는 위계를 준다.
     글리프 »: 패널이 오른쪽으로 밀려 나가는 실제 동작(SP12)을 가리킨다 — 접근성 이름은
     aria-label 이 고정하므로 글리프가 낯설어도 낭독은 "닫기"다. */
  .detail-close{width:24px;height:24px;flex:0 0 auto;padding:0;color:var(--muted);
                background:transparent;border:1px solid var(--line);border-radius:6px;
                cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
                font:inherit;font-size:13px;line-height:1}
  .detail-close:hover{color:var(--accent-ink);border-color:var(--accent)}
  .detail-close:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
```

```html
    <button id="dzh-detail-close" class="detail-close" type="button"
            aria-label="닫기" data-tooltip="닫기 (Esc)">»</button>
```

- **얻는 것**: `border-bottom` 0건(허브 전체 일관), 제목이 카드의 프로젝트명과 같은 타이포라
  "이 구역은 그 카드의 확대판"으로 읽힌다, 컨트롤 위계가 카드 내부 컨트롤과 맞는다.
- **잃는 것**: `✕` 보다 `»` 의 학습 비용이 미세하게 높다(툴팁·`aria-label` 로 상쇄).
- **테마**: `.card-drag-handle` 이 이미 두 테마에서 검증된 조합이다(`transparent` + `--line` +
  `--muted`, 126~130행). 새 색 리터럴 0개.

#### 시안 B — 오버라인 컴팩트 헤더

```css
  .detail-head{display:flex;align-items:center;gap:8px;padding:14px 18px 8px}
  .detail-title{font-size:11.5px;font-weight:800;letter-spacing:.4px;color:var(--muted);
                overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1 1 auto}
  .detail-close{/* 시안 A 와 동일 */}
```

제목을 `.path`(158행)·`.last-activity`(157행) 계열의 작은 보조 텍스트로 낮춰 헤드를 거의
지워버린다. **기각**: 초판 YAGNI 보류 2 가 "열린 프로젝트의 카드 하이라이트를 만들지 않는" 근거로
**"어떤 프로젝트인지는 패널 제목이 이미 말한다"**를 들었다. 제목을 보조 텍스트로 낮추면 그 근거가
무너져 보류 2 를 다시 열어야 한다. 시각 정리의 대가로 정보 구조를 잃는 교환이다.

#### 시안 C — 인셋 구분선 + 카드 소제목

```css
  .detail-head{display:flex;align-items:center;gap:10px;margin:0 18px;padding:16px 0 12px;
               border-bottom:1px solid var(--soft)}
  .detail-title{/* 시안 A 와 동일 */}
  .detail-close{/* 시안 A 와 동일 */}
```

구분선을 유지하되 **패널 가장자리에 닿지 않게 인셋**하고 색을 `--line` → `--soft` 로 낮춘다
(인셋된 선은 창틀이 아니라 콘텐츠 구조로 읽힌다 — `.sessions li` 의 `--soft` 선례와 같은 계열).
**차선**: 구분선을 남기고 싶다는 취향이 있으면 이쪽이다. 다만 `border-bottom` 이 0건이 되지 않아
G8·T25-85 의 역방향 토큰을 `border-bottom:1px solid var(--line)}` 로 좁혀야 하고, 그러면
"허브에는 가로 구분선이 없다"는 단순한 규칙 하나를 잃는다.

> **→ 후보에서 탈락(R2 재검토, 2026-08-14).** 두 가지 이유다. ① 사용자가 **시안 A 를 확정**했다.
> ② 재검토에서 드러났듯 **iframe 첫 카드가 이미 인셋 선을 그 자리에 그린다**(SP11 ③) — 시안 C 를
> 얹으면 8~12px 간격을 두고 **인셋 선이 두 줄** 생긴다. 초판이 시안 C 를 차선으로 둔 전제("구분선이
> 하나도 없어지는 것이 불안하다")가 사실과 달랐던 셈이다. **이 항목은 재승인 대상이 아니다.**

### 결정 SP12 — 닫힘 상태 표현: 전이 선언을 **닫힌(기본) 규칙**으로 옮기고 `visibility` 를 함께 전이시킨다

| 안 | 얻는 것 | 잃는 것 |
|----|---------|---------|
| A. **전이를 기본 규칙에 두고 `transition:transform 180ms ease-out, visibility 180ms`** | `visibility` 는 **전이 중(진행률 0 초과 1 미만) 항상 `visible`** 로 계산되는 특수 보간 규칙을 가진다 → 닫힐 때 180ms 동안 보이다가 끝에서 숨고, 열릴 때는 즉시 보인다. **한 선언이 양방향을 모두 처리한다.** 상태 클래스가 늘지 않아 "패널의 시각 상태 = `body.dzh-panel-open` 의 순수 함수"라는 초판 성질이 유지된다. **닫는 도중 재클릭하면 브라우저가 현재 위치에서 부드럽게 되돌린다**(JS 개입 0) | 초판 GOTCHA 1 을 뒤집는다 → 문서·검사 개정 필요 |
| B. `dzh-panel-closing` 상태 클래스 + JS 로 부착·제거 | 닫힘 전용 이징·시간을 따로 줄 수 있다 | **상태가 셋이 된다**(열림·닫는 중·닫힘). 재클릭 시 "닫는 중" 클래스를 손으로 걷어내야 하고, 그 취소를 빠뜨리면 패널이 열린 채 `closing` 스타일을 입는다. `openDashboardKey` 하나가 진실이라는 초판 계약(1157행)이 깨진다 |
| C. `transitionend` 를 기다렸다가 `visibility` 를 JS 로 토글 | — | 스타일을 JS 가 소유하게 된다. 이벤트가 안 오는 경로(SP14 참조)가 그대로 시각 버그가 된다 — 패널이 영영 `visible` 로 남는다 |
| D. `transition-delay` 로 `visibility 0s linear 180ms` 를 기본 규칙에, 열림 규칙에 `visibility 0s` 를 다시 선언 | 안 A 와 결과가 같다 | **두 선언이 짝을 이뤄야 한다** — 열림 규칙의 재선언을 빠뜨리면 열 때도 180ms 동안 안 보이다가 끝에서 튀어나온다(전이는 **after-change style** 의 `transition-*` 를 쓰기 때문). 안 A 는 이 짝 자체가 없다 |

> **결정 SP12 — 안 A.** **초판 결정 SP5 의 "닫기는 즉시" 를 번복한다**(사용자 요구).
> 핵심은 `visibility` 의 특수 보간이다: 양 끝점 중 하나가 `visible` 이면 전이 중 값은 계속
> `visible` 이다. 그래서 **지연(`transition-delay`)도, 상태 클래스도, JS 도 필요 없다** —
> 시간 하나를 `transform` 과 공유하는 것으로 끝난다.
> 결과적으로 R2 의 CSS 는 초판보다 **선언이 줄어든다**: 열림 규칙 3곳에 흩어져 있던 `transition`
> 이 기본 규칙 3곳으로 **옮겨갈 뿐** 개수가 같고, 열림 규칙에는 "바뀌는 값"만 남는다.

### 결정 SP13 — 나가는 패널은 입력을 받지 않는다 (`pointer-events` 짝)

닫기 애니메이션은 이 UI 에 **없던 상태**를 만든다: JS 는 "닫힘"인데 픽셀은 아직 거기 있는 180ms.
그 창에서 패널이 클릭을 받으면, 눌러도 아무 일도 안 하는 닫기 버튼이 살아 있는 것처럼 보이고
(이미 `openDashboardKey === null` 이라 `closeDetailPanel()` 이 즉시 반환한다), 밀어내기 모드에서는
**되돌아오는 배경으로 재배치되는 카드 위를 나가는 패널이 덮고 있어** 카드 클릭이 빗나간다.

```css
.detail-panel{…;pointer-events:none}                       /* 기본(닫힘·나가는 중) */
body.dzh-panel-open .detail-panel{…;pointer-events:auto}   /* 열림 */
```

`visibility:hidden` 이 이미 완전히 닫힌 뒤의 입력을 막으므로, 이 두 선언이 실제로 일하는 구간은
**나가는 180ms 뿐**이다 — 즉 죽은 코드가 아니라 새 상태를 위해 정확히 필요한 만큼이다.

### 결정 SP14 — `about:blank` 지연은 **`setTimeout(PANEL_CLOSE_ANIMATION_MS)`**. `transitionend` 는 쓰지 않는다

슬라이드가 끝나기 전에 iframe 을 비우면 빠져나가는 패널이 흰 화면으로 번쩍인다(초판 SP5 가
닫기 애니메이션을 기각한 이유 그 자체). 지연 수단은 둘뿐이다.

| 수단 | 이벤트가 **안 오거나 늦는** 경로 | 판정 |
|------|-----------------------------------|------|
| `transitionend` | ① **`prefers-reduced-motion` 에서 `transition:none` 이면 전이가 없어 이벤트가 아예 발화하지 않는다** → iframe 이 영원히 폴링한다(리스크 R-6 재발) ② **백그라운드 탭은 스타일·애니메이션 갱신이 정지돼 전이가 진행되지 않는다** → 이벤트가 탭 복귀까지 **상한 없이** 밀린다 ③ `transform` 과 `visibility` 두 속성이 각각 발화해 `propertyName` 필터가 필요하다 | **기각** |
| `setTimeout` | 백그라운드 탭에서 **1초 이상으로 스로틀될 수 있다** — 그러나 **상한이 있고**, 그 순간 화면은 보이지도 않으므로 흰 번쩍임이라는 시각적 목적과 무관하다 | **채택** |

> **결정 SP14 — `setTimeout`.** 요구된 "이벤트가 안 오는 경로의 폴백"에 대한 답은 **폴백을 두는
> 것이 아니라 이벤트를 쓰지 않는 것**이다. `transitionend` 를 채택하면 폴백은 결국 타이머가 되고,
> 그러면 **하나의 일에 메커니즘이 둘**이 된다(둘이 모두 발화하는 순서까지 다뤄야 한다).
> 지연의 목적은 "애니메이션이 끝났음을 안다"가 아니라 **"사용자가 아직 볼 수 있는 동안에는 비우지
> 않는다"** 이고, 그 목적에는 상한이 보장된 타이머가 정확히 맞는 도구다.
> 타이머 관용구는 이 파일에 이미 있다 — 툴팁 IIFE 의 `showTimerId`/`TOOLTIP_SHOW_DELAY_MS`
> (422·432·453·455행). **이름·`null` 센티넬·해제 형태를 그대로 따른다.**
> 검사 T25-82 가 `transitionend` 를 **역방향 토큰**으로 막아 이 결정을 코드에 고정한다.

### 결정 SP15 — 재진입 가드: **"대기 중 타이머가 있다 ⇒ 닫혀 있다"** 불변식 하나로 끝낸다

경쟁 상태의 실체: `closeDetailPanel()` 이 T+180 에 `about:blank` 를 예약한다. 그 사이에 패널이
다시 열리면 **방금 연 패널의 문서를 그 타이머가 지운다**(사용자에게는 영영 로딩되지 않는 흰 패널).
초판 YAGNI 보류 4 가 예고한 바로 그 문제다.

**불변식 (이것이 설계의 전부다):**

> **대기 중인 blank 타이머가 존재하면 `openDashboardKey === null` 이다.**
>
> - 타이머를 예약하는 곳은 `closeDetailPanel()` **한 곳**이고, 그 함수는 예약 직전에
>   `openDashboardKey = null` 로 만든다. → 성립
> - `openDashboardKey` 가 `null` 이 아니게 되는 곳은 `openDetailPanel()` **한 곳**이고,
>   그 함수는 상태를 바꾸기 전에 타이머를 취소한다. → 보존

이 불변식에서 네 가지 재진입 시나리오가 **가드 코드 없이** 전부 풀린다.

| # | 닫는 중(지연 창 안)에 들어온 입력 | 결과 |
|---|-----------------------------------|------|
| ① | **같은** 카드 클릭 | `openDashboardKey` 는 이미 `null` 이라 SP8 의 조기 반환에 걸리지 않는다 → 타이머 취소 후 정상 재오픈. 패널은 현재 위치에서 되돌아 들어온다(CSS 가 처리). iframe 은 그 프로젝트 문서를 **다시 로드**한다(스크롤 초기화) — 즉시 닫기였던 초판과 같은 결과라 회귀가 아니다(대안은 YAGNI 보류 6) |
| ② | **다른** 카드 클릭 | 타이머 취소 → 제목·문서 교체 → 슬라이드 되돌림. 새 문서가 지워지지 않는다 |
| ③ | **ESC 연타** | 두 번째 ESC 는 `closeDetailPanel()` 첫 줄 `if(openDashboardKey === null) return;`(1199행)에 걸린다 → **타이머가 두 번 예약되지 않는다** |
| ④ | **닫기 버튼 재클릭** | ③ 과 동일 경로(같은 함수) |

> **결정 SP15 — 취소는 `openDetailPanel()` 안에서만 한다.**
> `closeDetailPanel()` 에도 방어적으로 `clearTimeout` 을 넣고 싶어지지만, **그 지점에서 대기
> 타이머는 존재할 수 없다**(위 불변식 + 1199행 조기 반환에서 증명된다). "일어날 수 없는 상황에
> 대한 에러 처리 금지" 원칙대로 넣지 않는다. 대신 **불변식을 머리 주석 조항 ④ 로 못 박아**,
> 나중에 상태를 바꾸는 세 번째 경로를 만드는 사람이 규칙을 알게 한다.
> 세대(generation) 토큰 비교도 검토했다 — 같은 결과를 내지만 변수 하나(카운터)와 개념 하나
> (세대)를 더 도입하면서 **취소되지 않은 타이머가 계속 살아 있게** 둔다. `clearTimeout` 한 줄이
> 더 단순하고, 이 파일에 이미 있는 관용구다(422·432·453행).
> 검사 T25-83 이 "`clearTimeout` 은 `openDetailPanel` 과 `closeDetailPanel` **사이**에 있다"를
> 줄 번호로 기계 검증한다(선례: T25-66 의 줄 번호 비교, 3307~3315행).

### 결정 SP16 — 밀어내기 복귀도 **대칭으로** 애니메이션한다

패널만 180ms 에 걸쳐 나가고 배경이 즉시 제자리로 튀면, 눈에는 **두 사건**으로 보인다(패널이
나가는 것과 화면이 덜컥 넓어지는 것). 요구 2 의 의도는 "패널이 나가는 장면"이지 "패널만 나가는
장면"이 아니다. SP12 와 **같은 기법**을 그대로 적용한다 — 전이를 열림 규칙에서 기본 규칙으로 옮긴다.

```css
@media (min-width:1024px){
  .detail-panel{left:auto;width:var(--dzh-panel-width);border-radius:14px 0 0 14px}
  /* 전이는 "닫힌" 기본 규칙에 둔다 — 클래스가 붙을 때와 떨어질 때 모두 살아 있는 유일한
     위치다. 열림 규칙에는 "바뀌는 값"만 남는다(SP12·SP16). */
  body{transition:padding-right 180ms ease-out}
  #dzh-usage{transition:transform 180ms ease-out}
  body.dzh-panel-open{overflow:visible;padding-right:var(--dzh-panel-width)}
  body.dzh-panel-open #dzh-usage{transform:translateX(calc(-1 * var(--dzh-panel-width)))}
}
```

세 요소(패널·`body` 패딩·`#dzh-usage`)가 **같은 180ms·같은 이징**을 공유하므로 열기와 닫기가
모두 하나의 동작으로 읽힌다. 오버레이 모드(<1024px)에는 밀어내기 자체가 없어 해당 사항이 없다.

**`body{overflow:hidden}` 은 애니메이션하지 않는다**(할 수도 없다). 오버레이 모드에서 닫는 순간
스크롤바가 즉시 돌아오지만, 그 순간 패널은 아직 화면을 **전폭으로 덮고 있어** 레이아웃 이동이
보이지 않는다 — 패널이 비켜났을 때는 이미 정착해 있다.

### 결정 SP17 — reduced-motion: CSS 는 6셀렉터 무효화, **JS 는 저감 여부를 모른다**

CSS 쪽은 초판의 기법(셀렉터를 그대로 반복 + 소스 순서 뒤)을 **기본 규칙까지 확장**한다.
전이가 기본 규칙으로 옮겨갔으므로 무효화 대상도 함께 늘어난다.

```css
  @media (prefers-reduced-motion:reduce){
    .detail-panel,
    body,
    #dzh-usage,
    body.dzh-panel-open,
    body.dzh-panel-open .detail-panel,
    body.dzh-panel-open #dzh-usage{transition:none}
  }
```

명세도 확인(전부 뒤에 오므로 동률이면 소스 순서로 이긴다): `.detail-panel`(0,1,0)=동률,
`body`(0,0,1)=동률, `#dzh-usage`(1,0,0)=동률, 나머지 셋은 초판과 같다. **미디어 쿼리는 명세도를
올리지 않으므로 순서가 전부다** — 그래서 이 블록은 반드시 `@media (min-width:1024px)` 블록보다
**뒤**에 있어야 한다(T25-79 가 강제).

**JS 쪽 — 저감 모드에서 `about:blank` 지연을 없앨 것인가?**

| 안 | 평가 |
|----|------|
| **A. JS 는 저감 여부를 모른다. 지연은 언제나 `PANEL_CLOSE_ANIMATION_MS`** | 저감 모드에서 패널은 t=0 에 **이미 보이지 않는다**(`transition:none` → `visibility` 즉시 `hidden`). 그 뒤 180ms 동안 iframe 이 살아 있는 것은 **관측 불가능**하고, iframe 폴링 주기가 5초라 R-6 에도 영향이 없다. **분기 0개, 경로 1개** |
| B. `matchMedia('(prefers-reduced-motion:reduce)').matches ? 0 : 180` 을 지연값으로 | 요구 5 의 문면에 더 가깝다. 경로는 여전히 하나로 수렴한다(값만 갈린다). 대신 CSS 의 미디어 문자열과 JS 의 문자열이 **또 하나의 이중 정의**가 된다(브레이크포인트가 이미 그래서 T25-78 을 낳았다) |

> **결정 SP17 — 안 A 를 권고**하되 **R2 승인 항목 4 로 올린다**(요구 5 의 문면과 다르기 때문).
> 관측 불가능한 차이를 위해 미디어 쿼리 문자열을 하나 더 이중 정의하지 않는다는 판단이다.
> **정직한 단서**: 지연 창(180ms) 안에 iframe 의 5초 폴링이 한 번 걸릴 확률이 약 3.6% 있고,
> 그때 닫기 직후 요청 1건이 더 나간다. 이것은 **저감 모드만의 문제가 아니라 지연 자체의 성질**이라
> 안 B 로 바꿔도 애니메이션 경로에는 그대로 남는다 → 수동 검사 M5 를 그에 맞게 개정한다.

### 결정 SP18 — 주석·문서 정합 (거짓말을 남기지 않는다)

| 위치 | 현재 | R2 |
|------|------|-----|
| `hub_template.html` 181행 | "32px 원형 아이콘 버튼 — 헤더 클러스터의 두 버튼과 **모달 닫기 버튼**이 공유한다(결정 Y4)" | "…헤더 클러스터의 두 버튼이 공유한다(결정 Y4). **상세 패널의 닫기 컨트롤은 이 클래스를 쓰지 않는다** — 페이지 최상위 액션과 패널 안 컨트롤의 위계를 구분한다(결정 SP11)" |
| 〃 246~248행 | "전이 선언을 '열린 상태' 규칙 안에만 둔다 … 즉시 닫힌다" | **교체** — "전이 선언은 '닫힌(기본) 규칙'에 둔다. 클래스가 붙을 때와 떨어질 때 모두 살아 있는 유일한 위치다. `visibility` 를 같은 시간으로 함께 전이시키면 **전이 중에는 계속 `visible`** 로 계산돼(특수 보간) 나가는 동안 패널이 사라지지 않는다 — 지연도 상태 클래스도 필요 없다(SP12)" |
| 〃 머리 주석 33~36행 | 조항 ①②③ | **조항 ④ 신설**: "닫기는 `PANEL_CLOSE_ANIMATION_MS` 동안의 슬라이드아웃이며 그 사이 iframe 을 비우지 않는다. `about:blank` 는 같은 시간만큼 지연 실행되고, **대기 중인 그 타이머가 존재하면 `openDashboardKey` 는 반드시 `null` 이다** — 취소는 `openDetailPanel` 한 곳에서만 한다(SP15)" |
| `hub/README.md` 204~205행 | "…패널이 우측에서 미끄러져 들어온다." | 문장 끝에 추가: "**닫으면 같은 시간에 걸쳐 오른쪽으로 미끄러져 나가고, 밀렸던 목록도 함께 제자리로 돌아온다.**" |

> **개정(R2 재검토)**: 이 행의 대상 줄(204~205행)은 병합 후에도 그대로다. PR #3 이 그 **아래**에
> 테마 추종 설명 2줄(206~207행)을 더했을 뿐이라 삽입 지점이 밀리지 않는다(직접 확인함).
> 새 2줄에 `모달` 이 없으므로 **T25-81 의 역방향 검사도 그대로 통과한다.**

### 결정 SP19 — 패널 폭은 **고정 `550px`** (초판 SP4·초판 승인 항목 1 을 번복한다)

> **사용자 지시로 확정된 사항이다.** 이 절은 "왜 550 인가"를 논증하지 않는다 — 550 을 입력으로
> 놓았을 때 **초판이 550 이 아닌 값을 전제로 세운 산술들이 여전히 성립하는지**를 재도출한다.
> 초판 SP4 의 원문(비율 + 상·하한 논거)은 지우지 않고 번복 화살표만 덧붙였다.

```css
    /* 패널 폭(SP19, 초판 SP4 번복). 밀어내기 폭·.usage 이동량이 같은 값을 쓰게 하는 단일 출처다. */
    --dzh-panel-width:550px;
```

**바뀌는 것은 `hub_template.html` 66행 한 줄의 값뿐이다.** 토큰 이름·선언 위치(`:root`)·참조 3곳
(254·256·258행)은 한 글자도 바뀌지 않는다 — 초판이 "폭이 불만이면 한 줄을 고치면 된다"고 적어 둔
그 한 줄을 실제로 고치는 것이다.

#### ① 브레이크포인트 재도출 — **1024px 을 그대로 둔다** (근거는 더 강해졌다)

초판 SP3 의 산술은 `clamp()` 하한 400 을 입력으로 썼다: `400 + 352 = 752` → "여유를 얹어 1024".
550 고정이면 하한 산술은 `550 + 352 = 902` 가 되고, 1024 에서의 여유는 `1024 − 902 = 122px` 다
(초판은 272px). **여전히 양수이므로 카드 1열은 온전히 남는다.** 그런데 재검토에서 **더 단단한
하한이 하나 더 나왔다** — 사용량 패널이다.

`.usage` 는 `position:fixed;right:16px;width:min(420px, …)`(201행)이고 밀어내기 모드에서
`translateX(-550px)` 로 함께 옮겨진다(258행). 그 **왼쪽 끝** 좌표는

```
usage_left = viewport − 16(right) − 550(panel) − 420(usage) = viewport − 986
```

이므로 `usage_left ≥ 0` 이려면 **뷰포트 ≥ 986px** 이어야 한다. 즉 550 고정에서는

> **밀어내기 브레이크포인트의 하한이 「카드 1열」(902)이 아니라 「사용량 패널」(986)이 정한다.**

1024 는 986 을 넘는 **가장 가까운 관례적 데스크톱 경계**다. 이로써 1024 는 초판의 "여유를 얹은
취향값"에서 **산술적 최솟값 바로 위의 값**으로 성격이 바뀐다.

| 후보 | 판정 |
|------|------|
| **1024 (유지, 권고)** | 카드 1열 여유 122px · 사용량 패널 여유 38px. 둘 다 양수. **T25-78 이 강제하는 CSS/JS 쌍을 건드리지 않는다**(변경 0줄) |
| 960 | **산술적으로 실격.** `960 − 986 = −26px` → 밀어내기 모드에서 **사용량 패널 왼쪽이 화면 밖으로 잘린다** |
| 1152 로 상향 | 여유는 늘지만, 지금 밀어내기가 정상 동작하는 1024~1151 구간 사용자를 오버레이로 강등시킨다. 얻는 것 없이 기능을 뺏는다 |

> **결론: 브레이크포인트는 바꾸지 않는다.** 초판 SP3·GOTCHA 2·T25-78·`PANEL_PUSH_MIN_WIDTH_PX`
> 전부 **무수정**이다. (`hub_template.html` 의 `@media (min-width:` 는 253행 **1곳뿐**임을 재확인했다
> — T25-78 의 `head -1` 추출이 여전히 안전하다.)

#### ② 뷰포트별 표 — 550 고정 기준 재계산 (초판 SP4 표의 대체)

산식은 초판과 같다. 메인 폭 = `뷰포트 − 550`, `.wrap` 내용폭 `C = min(1440, 메인) − 32`,
트랙 최소폭 `T = max(320, (C−24)/3 − 1)`, 열 수 `= floor((C+12)/(T+12))`(94행 그리드 규칙).

| 뷰포트 | 패널 폭 | 남는 메인 | `.wrap` 내용폭 | 카드 열 수 | (참고) 초판 clamp 의 열 수 |
|--------|---------|-----------|----------------|------------|-----------------------------|
| 1024px | 550px | 474px | 442px | **1열** | 1열 |
| 1280px | 550px | 730px | 698px | **2열** | 2열 |
| 1440px | 550px | 890px | 858px | **2열** | 2열 |
| 1920px | 550px | 1370px | 1338px | **3열** | 3열 |

> **1920px 에서 카드 3열이 유지된다**(요구된 확인 지점). `C = 1338` 에서 트랙 최소폭이
> `max(320, 437) = 437` 로 올라가고 `floor(1350/449) = 3` 이다. 4열은 94행 주석이 설명하는
> `(100% − 24px)/3 − 1` 장치가 산술적으로 막는다.
>
> **네 지점 모두 열 수가 초판과 같다** — 폭을 고정해도 배경 목록의 레이아웃 체감은 바뀌지 않는다.
> 바뀌는 것은 **패널 안 대시보드가 받는 폭**뿐이다(아래 ③).

#### ③ 패널 안 대시보드가 실제로 받는 폭 (초판 P-2 의 재평가)

`.detail-panel` 은 `box-sizing:border-box`(86행) + `border-left:1px`(244행)이므로 콘텐츠 박스는
**549px**, iframe 은 그것을 가득 채운다(273행). 그 안에서 `.wrap{padding:0 16px}`(1272행) →
**내용폭 517px**, `.card{padding:26px 30px}`(1273행)까지 빼면 **카드 내부 455px**.

| 뷰포트 | 초판 clamp 의 대시보드 내용폭 | 550 고정의 내용폭 | 차이 |
|--------|------------------------------|-------------------|------|
| 1024px | 377px | **517px** | **+140** |
| 1280px | 479px | **517px** | **+38** |
| 1440px | 543px | **517px** | −26 |
| 1920px | 687px | **517px** | −170 |

교차점은 `40vw = 550` → **뷰포트 1375px** 이다. 즉 **1375px 미만에서는 550 고정이 초판보다 넓고,
그 위에서는 좁다.** 초판 P-2("패널 안 대시보드가 좁아 읽기 불편")는 **가장 좁았던 구간에서
개선되고, 큰 화면에서의 상향 여지를 잃는다**는 형태로 바뀐다. 초판이 승인 시점에 이미 받아들였던
최악값(377px)보다 항상 넓으므로 **새 리스크가 생기지는 않는다.** 큰 화면에서 더 넓게 쓰고 싶어지면
후퇴 경로는 초판과 같은 **한 줄**이다(66행).

#### ④ 검사·계약에 미치는 영향 — 전부 **무수정**임을 코드로 확인했다

| 대상 | 판정 | 확인한 내용 |
|------|------|-------------|
| **T25-77** | **무수정** | 정방향 토큰이 `'--dzh-panel-width:'`(값 없이 선언 존재만)와 `padding-right:var(--dzh-panel-width)` 등 **참조 형태**만 본다(3498~3514행). 값이 `clamp(…)` 든 `550px` 든 통과한다 |
| **T25-78** | **무수정** | 브레이크포인트가 바뀌지 않는다(①). CSS `@media (min-width:1024px)` ↔ JS `PANEL_PUSH_MIN_WIDTH_PX = 1024` 쌍 그대로 |
| `--dzh-panel-width` 계약 | **무수정** | "밀어내기 폭과 `.usage` 이동량이 같은 값을 쓰도록 강제하는 단일 출처"라는 초판 계약이 값의 종류와 무관하다 |
| 초판 GOTCHA 4(`100vw` 금지) | **무수정** | 오버레이 모드 규칙(`left:0;right:0`)은 폭 토큰을 쓰지 않는다 |

**`550` 리터럴을 검사하지 않는다(의도적).** T25-84 가 시간 3값의 **상호 일치**를 보되 `180` 을
리터럴로 적지 않는 것과 같은 성질이다 — 폭은 "한 줄 고치면 되는 값"이라는 것이 초판부터의 설계
의도이고, 리터럴 검사를 넣으면 그 한 줄을 고칠 때마다 검사도 함께 고쳐야 해 **의도를 스스로 배반한다.**
폭에 대해 기계적으로 지킬 가치가 있는 성질은 "**단일 출처를 통해 쓰인다**"이며 그것은 T25-77 이
이미 지키고 있다.

#### ⑤ 고정폭의 상한 (다음 사람이 이 값을 만질 때의 가드레일)

밀어내기 브레이크포인트(1024)에서 사용량 패널이 잘리지 않으려면

```
--dzh-panel-width ≤ 1024 − 16 − 420 = 588px
```

이어야 한다. **550 은 38px 여유를 남긴다.** 이 상한을 넘기려면 브레이크포인트도 함께 올려야
하고(그러면 T25-78 이 CSS·JS 두 곳을 강제한다), 그것은 「폭 한 줄만 고치면 된다」의 범위를
벗어나는 변경이다 — 그때는 이 절을 다시 열어야 한다. **이 문단이 그 트리거다.**

---

## 구현 계획 (R2, 파일별)

### 1. `hub/bin/hub_template.html` — CSS (66행 + 241~273행)

먼저 `:root` 66행의 **값 한 개**를 치환한다(SP19 — 이름·위치·참조는 그대로다):

```css
    /* 패널 폭(SP19, 초판 SP4 번복). 밀어내기 폭·.usage 이동량이 같은 값을 쓰게 하는 단일 출처다. */
    --dzh-panel-width:550px;
```

이어서 패널 CSS 241~273행. 바뀌는 **선언만** 적는다(주석 개정은 SP18 표).

```css
  .detail-panel{position:fixed;top:0;right:0;bottom:0;left:0;z-index:30;
                display:flex;flex-direction:column;
                background:var(--surface);color:var(--ink);
                border-left:1px solid var(--line);box-shadow:-16px 0 48px rgba(0,0,0,.28);
                transform:translateX(100%);visibility:hidden;pointer-events:none;
                transition:transform 180ms ease-out, visibility 180ms}
  body.dzh-panel-open{overflow:hidden}
  body.dzh-panel-open .detail-panel{transform:none;visibility:visible;pointer-events:auto}
  @media (min-width:1024px){
    .detail-panel{left:auto;width:var(--dzh-panel-width);border-radius:14px 0 0 14px}
    body{transition:padding-right 180ms ease-out}
    #dzh-usage{transition:transform 180ms ease-out}
    body.dzh-panel-open{overflow:visible;padding-right:var(--dzh-panel-width)}
    body.dzh-panel-open #dzh-usage{transform:translateX(calc(-1 * var(--dzh-panel-width)))}
  }
  @media (prefers-reduced-motion:reduce){
    .detail-panel,
    body,
    #dzh-usage,
    body.dzh-panel-open,
    body.dzh-panel-open .detail-panel,
    body.dzh-panel-open #dzh-usage{transition:none}
  }
  /* SP11 — .detail-head / .detail-title / .detail-close 는 「시안 A」 CSS 전문을 그대로 */
  .detail-frame{flex:1 1 auto;width:100%;border:0}
```

> **`transition:transform 180ms ease-out, visibility 180ms` 는 파일에서 유일한 토큰**이어야 한다
> (`transition:transform 180ms ease-out` 만으로는 `#dzh-usage` 규칙과 겹친다) — T25-79·T25-84 가
> 이 토큰을 앵커로 쓴다.

### 2. `hub/bin/hub_template.html` — DOM (320~321행)

```html
    <button id="dzh-detail-close" class="detail-close" type="button"
            aria-label="닫기" data-tooltip="닫기 (Esc)">»</button>
```

`id`·`type`·`aria-label`·`data-tooltip` 은 한 글자도 바뀌지 않는다. `class` 와 글리프만 바뀐다.

### 3. `hub/bin/hub_template.html` — JS (1140~1206행)

```js
  var PANEL_CLOSE_ANIMATION_MS = 180;      // CSS 의 transition 시간과 같은 값(T25-84)
  …
  var panelBlankTimerId = null;            // 닫기 슬라이드가 끝난 뒤 iframe 을 비울 예약(SP14)

  // 슬라이드가 끝난 뒤에 iframe 을 비운다(리스크 R-6) — 나가는 도중에 비우면 빠져나가는 패널이
  // 흰 화면으로 번쩍인다. transitionend 를 쓰지 않는 이유는 GOTCHA 12: 저감 모드에서는 발화하지
  // 않고 백그라운드 탭에서는 상한 없이 밀린다.
  function scheduleBlankAfterSlide(){
    panelBlankTimerId = setTimeout(function(){
      panelBlankTimerId = null;
      loadPanelDocument(BLANK_DOCUMENT_URL);
    }, PANEL_CLOSE_ANIMATION_MS);
  }

  function openDetailPanel(dashboardKey, displayName, openerElement){
    if(dashboardKey === openDashboardKey) return;
    // 닫는 중(지연 창)에 들어온 클릭 — 예약을 취소하지 않으면 방금 연 패널의 문서를 그 타이머가
    // 지운다. 이 한 줄이 "대기 타이머 ⇒ 닫힘" 불변식의 유일한 보존 지점이다(SP15).
    if(panelBlankTimerId !== null){ clearTimeout(panelBlankTimerId); panelBlankTimerId = null; }
    var wasClosed = openDashboardKey === null;
    …                                       // 이하 초판과 동일(1186~1193행)
  }

  function closeDetailPanel(){
    if(openDashboardKey === null) return;   // 여기서 반환되므로 대기 타이머는 존재할 수 없다(SP15)
    openDashboardKey = null;
    document.body.classList.remove(PANEL_OPEN_BODY_CLASS);
    applyBackgroundInert();
    scheduleBlankAfterSlide();              // 초판의 loadPanelDocument(BLANK_DOCUMENT_URL) 자리
    if(panelOpenerElement && panelOpenerElement.isConnected) panelOpenerElement.focus();
    panelOpenerElement = null;
  }
```

- **제목을 지우지 않는다.** `panelTitleEl.textContent = ''` 를 닫기에 넣고 싶어지지만, 넣으면
  나가는 180ms 동안 **머리가 빈 패널**이 보인다(GOTCHA 16).
- 나머지 배선(1208~1225행)은 **한 글자도 바뀌지 않는다**.

---

## GOTCHA (R2 — 구현자가 틀리기 쉬운 함정)

11. **초판 GOTCHA 1 은 이제 반대다.** "전이를 기본 규칙에 두지 마라"가 **"기본 규칙에 두어라"**로
    뒤집혔다(SP12). 옛 문장을 기억하고 열림 규칙으로 되돌리면 닫기 애니메이션이 조용히 사라진다
    — 화면은 초판처럼 멀쩡해 보이므로 **검사(T25-79)만이 잡는다.**
12. **`transitionend` 로 바꾸지 마라.** "타이머보다 정확하다"는 직관이 정확히 틀리는 자리다 —
    저감 모드에서는 발화 자체가 없고(전이가 없다), 백그라운드 탭에서는 상한 없이 밀린다.
    T25-82 가 역방향으로 막는다.
13. **`visibility` 를 전이 목록에서 빼면 즉시 사라진다.** `transform` 만 전이시키면 클래스가
    떨어지는 순간 `visibility:hidden` 이 즉시 적용돼 슬라이드가 **보이지 않는다**(애니메이션은
    실행되지만 투명 인간이다). 이 실패는 화면상 초판과 구분되지 않는다 — T25-79 가 토큰으로 잡는다.
14. **`#dzh-usage` 의 전이 목록에 `all` 을 쓰지 마라.** 사용량 패널의 접힘은 `width`·`padding` 을
    바꾼다(202행). `transition:all` 이면 **접기/펴기가 180ms 동안 늘어나는 애니메이션이 된다** —
    R2 가 요구하지 않은 동작이다. `transform` 만 적는다. 같은 이유로 `body` 도 `padding-right` 만.
15. **`prefers-reduced-motion` 블록은 이제 6셀렉터다.** 기본 규칙 3개(`.detail-panel`·`body`·
    `#dzh-usage`)를 빠뜨리면 저감 모드에서 **닫기만 애니메이션되는** 반쪽 상태가 된다.
    미디어 쿼리는 명세도를 올리지 않으므로, 이 블록은 반드시 `@media (min-width:1024px)` 블록
    **뒤**에 있어야 한다(T25-79 가 줄 번호로 강제).
16. **닫을 때 제목·`inert` 를 정리하려 들지 마라.** 제목을 비우면 나가는 패널의 머리가 빈다.
    `inert` 해제는 반대로 **즉시** 해야 한다(180ms 지연시키면 그 사이 포커스 복귀가 조용히 실패한다
    — 초판 GOTCHA 6 이 그대로 유효하다).
17. **`.icon-btn` 규칙을 지우지 마라.** 닫기 버튼이 빠져도 헤더의 새로고침·테마 버튼 2개가 계속
    쓴다(293·301행). T25-63 이 `.icon-btn` 토큰을 검사한다(3254행).
18. **`»` 를 `aria-hidden` 으로 감싸거나 `aria-label` 을 지우지 마라.** 글리프가 접근성 이름이
    되어 버리면 스크린리더가 "우측 이중 꺾쇠"를 읽는다. `aria-label="닫기"` 가 이름을 고정한다.

---

## 엣지 케이스 (R2)

| # | 상황 | 동작 |
|---|------|------|
| E13 | 오버레이 모드에서 닫는 중(180ms) 배경 상태 | `inert` 는 **즉시** 해제된다(포커스 복귀 때문). 그 180ms 동안 배경은 조작 가능하지만 패널이 덮고 있고, 패널은 `pointer-events:none`(SP13)이라 클릭이 배경으로 통과한다 — 사용자 관점에서는 "이미 닫힌 화면"과 같다 |
| E14 | 닫는 중 창 크기를 브레이크포인트 너머로 바꾼다 | `pushModeQuery` 의 `change` 가 `applyBackgroundInert()` 를 부르고, `openDashboardKey === null` 이라 아무것도 켜지 않는다. CSS 는 모드만 갈아탄다. 타이머는 그대로 만료돼 iframe 을 비운다 |
| E15 | 닫은 직후 요청 1건이 더 나간다 | 지연 창(180ms) 안에 iframe 의 5초 폴링이 걸릴 확률 약 3.6%. **지연 방식의 본질적 성질**이며 R-6 을 깨지 않는다(그 뒤로는 영구히 멈춘다). 수동 검사 M5 를 "닫기 후 **0.5초 이후**로는 요청이 없다"로 개정한다 |
| E16 | 닫는 중 탭을 백그라운드로 보낸다 | `setTimeout` 이 1초 이상으로 스로틀될 수 있다 → blank 가 그만큼 늦는다. 화면이 보이지 않으므로 시각 영향 0, 상한은 존재한다 |
| E17 | 저감 모드에서 닫는다 | 패널이 즉시 사라진다(`transition:none` → `visibility` 즉시). iframe blank 는 180ms 뒤(SP17 안 A) — 보이지 않는 차이다 |
| E18 | 나가는 도중 페이지를 새로고침/이탈 | iframe 과 타이머가 문서와 함께 파기된다. 남는 상태가 없다 |
| E19 | 헤드 제목이 아주 긴 프로젝트명 | `flex:1 1 auto;min-width:0` + `text-overflow:ellipsis` 로 잘린다(카드 `.project-name` 과 같은 처리, 134~136행). 닫기 컨트롤은 `flex:0 0 auto` 라 절대 밀려나지 않는다 |
| E20 | `»` 글꼴 미지원 환경 | U+00BB 는 기본 시스템 글꼴 전부에 있다(라틴-1 보충). 최악의 경우에도 툴팁·`aria-label` 이 의미를 전달한다 |

---

## 테스트 계획 (R2) — `tests/run.sh`

### 기존 검사에 대한 영향 (전수 확인 결과)

> **줄 번호 전수 갱신(R2 재검토, 2026-08-14).** PR #3 이 `tests/run.sh` 를 +248줄 늘리면서
> **T25 계열은 일괄 +222, T22 계열은 일괄 +36** 이동했다(양 끝 검사를 각각 대조해 확인). 아래는
> 병합 후 실측값이다. **T25 계열 검사의 내용은 PR #3 이 한 줄도 바꾸지 않았다** — `hub_template.html`
> 이 PR 의 변경 대상이 아니었으므로 그 파일을 보는 검사들도 그대로다(`git show --stat 12d49d6` 확인).

| 검사 | 위치(병합 후) | 처리 |
|------|---------------|------|
| **T25-79** | 3527~3547행 | **개정.** 아래 상세 |
| T25-63 | 3251~3267행 | **무수정.** `'<aside id="dzh-detail-panel"'`·`'id="dzh-detail-frame"'`·`'.icon-btn'` 세 토큰 모두 R2 이후에도 존재한다(`.icon-btn` 규칙은 헤더 버튼용으로 남는다) |
| T25-76 | 3481~3496행 | **무수정.** `role="dialog"`·`aria-labelledby="dzh-detail-title"` 를 유지하는 것이 R2 전제 2 다 |
| T25-77 | 3498~3514행 | **무수정.** `transform:translateX(100%)`·`visibility:hidden` 토큰이 기본 규칙에 그대로 남는다(전이가 추가될 뿐). **폭이 `550px` 로 바뀌어도 무수정이다** — 정방향 토큰이 `'--dzh-panel-width:'` 선언 존재와 참조 형태만 본다(결정 SP19 ④) |
| T25-78 | 3516~3525행 | **무수정.** 브레이크포인트 1024 를 바꾸지 않는다(SP19 ①). `@media (min-width:` 가 `hub_template.html` 253행 1곳뿐이라 `head -1` 추출이 여전히 안전함도 재확인했다 |
| T25-80 | 3549~3561행 | **무수정.** `about:blank`·`contentWindow.location.replace(`·`openDashboardKey` 전부 유지, `panelFrameEl.src` 역방향도 유지 |
| T25-81 | 3563~3580행 | **개정(토큰 1개 추가).** `hub/README.md` 정방향 토큰에 `'나간다'` 를 더해 닫힘 서술을 강제한다. **역방향(`'모달'` 0건)은 그대로 통과한다** — PR #3 이 README 에 더한 2줄(206~207행, 테마 추종)에 `모달` 이 없음을 확인했다 |
| T25-66 | 3297~3321행 | **무수정.** `closest('#dzh-detail-panel')` 가드는 그대로다 |
| T22-97·98·99·101 | 1816·1824·1831·1850행 | **무수정.** R2 는 `body.dz-embedded` 계약을 건드리지 않는다. **T22-97 재확인**: PR #3 이 CSS 를 `body.dz-embedded #dz-pip-btn,body.dz-embedded #dz-pip-hint,body.dz-embedded #dz-theme-toggle{display:none}`(1349행)으로 늘렸지만 검사는 부분 문자열만 보므로 통과한다. **T22-101 재확인**: 초판 승인 항목 6 이 구현돼 이미 `'패널'` 토큰을 검사하고 있다 |
| **T22-111~127** | 2038~2224행 | **무수정 · 번호 충돌 없음.** PR #3 이 신설한 대시보드 검사군이며 `test_dashboard_template_integrity()` 안에 산다. 허브 검사는 `test_hub_docs_and_constants()` 의 **T25** 네임스페이스라 신규 T25-82~85 와 겹치지 않는다(현재 T25 최대 번호는 여전히 **T25-81**임을 확인했다) |
| **T22-124** | 2180~2185행 | **무수정 · 단 SP11 이 의존한다.** `body.dz-embedded #dz-page-head` 규칙을 고정하는 검사다 — 이 규칙이 살아 있어야 패널 헤드가 프로젝트명의 **유일한 표시처**가 된다(SP11 ⑥) |

### T25-79 개정 — 검사 **의도**를 새 구조로 옮긴다

초판 T25-79 의 의도는 **"애니메이션과 `prefers-reduced-motion` 무효화는 반드시 세트이고,
무효화가 소스 순서상 뒤에 있어야 한다"** 였다. R2 는 애니메이션이 양방향이 되고 무효화 대상이
늘었으므로, 같은 의도를 다음 4개 검사로 옮긴다.

| # | 검사 | 잡는 실패 |
|---|------|-----------|
| 79-a | `transition:transform 180ms ease-out, visibility 180ms` 토큰 존재 | GOTCHA 13(`visibility` 누락 → 슬라이드가 보이지 않음) |
| 79-b | 그 토큰의 줄 번호가 `body.dzh-panel-open .detail-panel{transform:none` 줄 번호보다 **작다** | GOTCHA 11(전이를 열림 규칙으로 되돌림 = 닫기 애니메이션 소실). 전이가 **기본 규칙에 있음**을 위치로 증명한다 |
| 79-c | `prefers-reduced-motion` 블록의 **첫 셀렉터 줄**(`^  \.detail-panel,$`)이 `body.dzh-panel-open #dzh-usage{transform:` 줄보다 **크다** | GOTCHA 15(무효화 블록이 앞에 오면 명세도 동률에서 진다) |
| 79-d | 그 블록에 6셀렉터가 모두 있다 — `.detail-panel,`·`  body,`·`  #dzh-usage,`·`body.dzh-panel-open,`·`body.dzh-panel-open .detail-panel,`·`body.dzh-panel-open #dzh-usage{transition:none}` | GOTCHA 15(기본 규칙 3개 누락 → 저감 모드에서 닫기만 애니메이션) |
| 79-e | (역방향, 초판 승계) `animation:modal-open`·`@keyframes modal-open` 0건 | 모달 잔재 |

### 신규 검사 (정방향 + 역방향 쌍)

현재 최대 번호는 **T25-81**(3563행)이므로 **T25-82** 부터 쓴다(병합 후 재확인 — PR #3 이
신설한 것은 T22 계열뿐이라 T25 최대 번호는 그대로다). 붙이는 위치는
`test_hub_docs_and_constants()` 의 T25-81 블록 뒤, `log_ok` 앞(**3580~3582행 사이**)이다.
**함께 고칠 것**: 같은 함수의 설명 문자열 2곳 — 2346행 주석 `# T25: 허브 문서·상수 정합성
(하위 검증 T25-1~T25-81)` 과 2349행 `local test_desc="허브 문서·상수 정합성 (T25-1~T25-81)"` 을
**`T25-1~T25-85`** 로 바꾼다. 선례가 바로 옆에 있다 — PR #3 이 T22 를 늘리면서 998·1002행의
`T22-1~T22-127` 을 같은 방식으로 갱신했다.

| # | 대상 | 정방향(있어야) | 역방향(없어야) |
|---|------|----------------|----------------|
| **T25-82** | SP14 닫기 지연 경로 | `PANEL_CLOSE_ANIMATION_MS` · `panelBlankTimerId` · `scheduleBlankAfterSlide` · `clearTimeout(panelBlankTimerId)` | **`transitionend`**(GOTCHA 12) · **`dzh-panel-closing`**(SP12 안 B 로의 회귀 — 상태 클래스를 만들지 않는다) |
| **T25-83** | SP15 재진입 가드의 **위치**(기계적) | `clearTimeout(panelBlankTimerId)` 의 줄 번호가 `function openDetailPanel(` 과 `function closeDetailPanel(` **사이**에 있다 · `scheduleBlankAfterSlide();` 호출 줄이 `function closeDetailPanel(` 보다 **뒤**에 있다 | — |
| **T25-84** | SP12·SP14 **시간 3중 일치**(기계적) | CSS 슬라이드 ms · CSS `visibility` ms · JS `PANEL_CLOSE_ANIMATION_MS` **세 숫자가 모두 같다.** 하나라도 못 뽑으면 실패 | — |
| **T25-85** | SP11 헤드 패널화 | `.detail-close{` · `class="detail-close"` · `>»<` · `aria-label="닫기"` · `data-tooltip="닫기 (Esc)"` | **`border-bottom`**(파일 전체 0건 — G8) · `<button id="dzh-detail-close" class="icon-btn"` · `>✕<` |

> **T25-84 의 구현 형태**(선례: T25-78, 3516~3525행):
> ```bash
> css_slide_ms=$(grep -oE 'transition:transform [0-9]+ms ease-out, visibility [0-9]+ms' \
>                  "$hub_template_file" | head -1 | grep -oE '[0-9]+' | head -1)
> css_visibility_ms=$(grep -oE 'transition:transform [0-9]+ms ease-out, visibility [0-9]+ms' \
>                  "$hub_template_file" | head -1 | grep -oE '[0-9]+' | tail -1)
> js_close_ms=$(grep -oE 'PANEL_CLOSE_ANIMATION_MS = [0-9]+' "$hub_template_file" | grep -oE '[0-9]+')
> [[ -n "$js_close_ms" && "$css_slide_ms" == "$css_visibility_ms" \
>    && "$css_slide_ms" == "$js_close_ms" ]] || record_failure …
> ```
> **`180` 을 리터럴로 적지 않는다** — 세 값이 서로 같은지만 본다. 시간을 바꾸고 싶으면 세 곳을
> 함께 고치게 되고, 검사는 그때도 통과한다(T25-78 과 같은 성질).

> **T25-83 의 구현 형태**(선례: T25-66 의 줄 번호 비교, 3307~3315행):
> ```bash
> open_fn_line=$(grep -n 'function openDetailPanel(' "$hub_template_file" | head -1 | cut -d: -f1)
> close_fn_line=$(grep -n 'function closeDetailPanel(' "$hub_template_file" | head -1 | cut -d: -f1)
> cancel_line=$(grep -n 'clearTimeout(panelBlankTimerId)' "$hub_template_file" | head -1 | cut -d: -f1)
> [[ -n "$cancel_line" && "$cancel_line" -gt "$open_fn_line" && "$cancel_line" -lt "$close_fn_line" ]] \
>   || record_failure …
> ```
> 이 검사는 **취소가 열기 경로에 있음**을 강제하는 동시에, `closeDetailPanel` 안에 중복 취소를
> 넣는 것도(그때는 두 번째 `clearTimeout` 이 생겨 `head -1` 밖으로 밀리지 않지만, 함수 순서를
> 뒤집으면 실패한다) 구조를 고정한다. **선행 조건**: `openDetailPanel` 이 `closeDetailPanel` 보다
> 위에 있다는 현재 배치(1183행 < 1198행)를 유지한다.

### 뮤테이션 검증 (구현 중 1회 — 검사가 **실제로 실패할 수 있는지** 확인)

각 변형을 넣고 `bash tests/run.sh` 가 **빨간불**이 되는지 확인한 뒤 되돌린다.

| 검사 | 변형 | 기대 |
|------|------|------|
| T25-79-a | `, visibility 180ms` 를 지운다 | 실패 |
| T25-79-b | 전이 선언을 `body.dzh-panel-open .detail-panel` 규칙으로 되돌린다(= 초판 상태) | 실패 |
| T25-79-c | `prefers-reduced-motion` 블록을 `@media (min-width:1024px)` 블록 **앞으로** 옮긴다 | 실패 |
| T25-79-d | 무효화 블록에서 `  body,` 한 줄을 지운다 | 실패 |
| T25-79-e | `@keyframes modal-open` 을 되살린다 | 실패 |
| T25-82 | `scheduleBlankAfterSlide()` 안을 `panelFrameEl.addEventListener('transitionend', …)` 로 바꾼다 | 실패(역방향 토큰) |
| T25-83 | `clearTimeout(panelBlankTimerId)` 를 `openDetailPanel` 에서 `closeDetailPanel` 로 옮긴다 | 실패 |
| T25-84 | JS 만 `PANEL_CLOSE_ANIMATION_MS = 240` 으로 바꾼다 | 실패 |
| T25-84(역) | CSS 만 `visibility 240ms` 로 바꾼다 | 실패 |
| T25-85 | 닫기 버튼 `class="detail-close"` → `class="icon-btn"` 로 되돌린다 | 실패 |
| T25-85(역) | `.detail-head` 에 `border-bottom:1px solid var(--line)` 를 되살린다 | 실패 |
| T25-81 | README 의 닫힘 서술 문장을 지운다 | 실패 |

### 수동 확인 (자동화 불가 — 브라우저 실측)

초판 M1~M11 은 그대로 유효하다(**M5 만 개정**). 아래를 더한다.

| # | 절차 | 기대 |
|---|------|------|
| **M5(개정)** | 닫고 **0.5초 뒤부터** DevTools Network 5분 관찰 | `/project/…/dashboard.html` 요청이 오지 않는다. **닫는 순간 1건이 더 보일 수 있다**(E15) — 그 이후로 끊기면 통과 |
| M12 | 1440px 창에서 패널을 닫는다 | 패널이 오른쪽으로 미끄러져 나가고, **목록과 사용량 패널도 같은 180ms 동안** 제자리로 돌아온다. 어느 것도 덜컥 튀지 않는다 |
| M13 | 닫는 도중(180ms 안) **다른** 카드를 클릭 | 패널이 되돌아 들어오며 새 프로젝트 내용이 뜬다. **흰 화면으로 남지 않는다**(SP15 ②) |
| M14 | 닫는 도중 **같은** 카드를 클릭 | 되돌아 들어오고 그 프로젝트가 다시 로드된다. 빈 패널이 되지 않는다(SP15 ①) |
| M15 | 닫는 도중 나가는 패널 위를 클릭 | 아무 일도 없거나 **뒤의 카드가 눌린다**. 닫기 버튼처럼 보이는 것을 눌러도 오류가 없다(SP13) |
| M16 | ESC 를 5회 연타 | 한 번만 닫히고 이후는 무동작. 콘솔 오류 없음(SP15 ③) |
| M17 | 저감 모드에서 M12 반복 | 즉시 사라진다. 슬라이드·복귀 애니메이션이 전혀 없다 |
| **M18(개정)** | 라이트·다크 **두 테마에서** 헤드 확인. 허브 헤더의 테마 토글로 전환하며 본다(iframe 이 `storage` 이벤트로 즉시 따라오는지도 함께 본다) | ① 구분선 없이도 제목 줄과 대시보드 내용의 경계가 분명하다 — **경계 역할은 iframe 첫 카드의 상단 테두리**(좌우 16px 인셋)가 한다 ② `»` 버튼 테두리가 두 테마 모두에서 보인다 ③ **제목의 왼쪽 끝과 아래 카드의 왼쪽 변이 같은 x 에 선다**(G15). 세로 스크롤바가 자리를 차지하는 환경에서는 **우변만** 그만큼 어긋날 수 있다 — 알려진 허용 오차다(SP11 ⑤) |
| M19 | 헤드의 `»` 에 마우스를 올린다 / Tab 으로 포커스 | "닫기 (Esc)" 툴팁이 패널 **위에** 뜬다. 포커스 링이 잘리지 않는다(`outline-offset:2px`) |
| M20 | 스크린리더로 패널을 연다 | 버튼이 "닫기"로 낭독된다(글리프가 읽히지 않는다) |
| **M21** | 창 폭을 **1024 · 1280 · 1440 · 1920px** 로 바꿔가며 패널을 연다(SP19 ② 표 대조) | 패널이 네 폭 모두에서 **550px 로 같다.** 카드 열 수가 **1 · 2 · 2 · 3** 이다. **1024px 에서 사용량 패널이 왼쪽으로 잘리지 않는다**(가장 빡빡한 지점 — 여유 38px) |

---

## 리스크와 완화책 (R2)

| # | 리스크 | 완화 |
|---|--------|------|
| P-9 | **닫기 애니메이션이 "느리다"고 느껴진다** — 열기와 달리 닫기는 사용자가 이미 다음 행동으로 넘어간 뒤라 지연이 더 크게 느껴진다 | 180ms 는 열기와 같은 값이고 지각 임계(약 200ms) 아래다. 불만이 나오면 **닫기만 짧게** 하는 것은 세 값(CSS 2 + JS 1)을 함께 고치는 일이며 T25-84 가 그 동기화를 강제한다 → R2 승인 항목 2 |
| P-10 | **지연 창에서 iframe 요청 1건이 더 나간다**(E15) | 확률 약 3.6%, R-6 의 본질(영구 정지)은 깨지지 않는다. M5 개정으로 검사 기준을 정직하게 맞춘다 |
| P-11 | **`»` 가 "닫기"로 안 읽힌다** | `aria-label`·툴팁 유지. 그래도 불만이면 **글리프 한 글자**만 `✕` 로 되돌리면 되고 다른 결정은 흔들리지 않는다(T25-85 의 토큰 2개만 수정) → R2 승인 항목 1 |
| P-12 | **구분선 제거로 헤드와 내용이 붙어 보인다** | ~~`/dashboard` 배경이 `#EEF3F8` 하드코딩이라 두 테마 모두 색 단차가 있음을 확인했다~~ **→ 완화 근거 교체(R2 재검토)**: 색 단차는 PR #3 이후 **사라졌고**(양쪽 다 `--surface`), 대신 iframe 첫 카드의 **1px `--line` 인셋 상단 테두리**가 그 자리에 들어와 있다(SP11 ③). 즉 시안 C 가 만들려던 선이 이미 있다. 그래도 부족하다는 판단이 나오면 되돌릴 곳은 시안 C 가 아니라 **헤드의 `padding-bottom` 한 값**(12px → 16~20px)이다 — 선을 더 긋는 대신 간격을 준다 |
| P-13 | **저감 모드 사용자에게 blank 가 180ms 늦다**(SP17 안 A) | 관측 불가능(패널이 이미 안 보인다). 뒤집으려면 `matchMedia` 한 줄이며 다른 결정에 영향 없다 → R2 승인 항목 4 |
| P-14 | **`pointer-events` 짝을 한쪽만 넣는다** | 열림 규칙의 `pointer-events:auto` 를 빠뜨리면 **패널을 아예 못 누른다**(치명적이지만 즉시 드러난다). 수동 M15 + 열기 경로의 M9(키보드) |
| **P-15** | **헤드/카드 경계가 `/dashboard` 템플릿의 레이아웃에 의존한다**(파일 간 결합) — PR #3 이 `.wrap{margin:32px auto}` → `margin:0 auto 32px}` 로 바꾸면서 임베드 시 첫 카드가 최상단에 밀착하게 됐다. 그 파일이 다시 바뀌면 SP11 ③ 의 근거가 또 흔들린다 | **감수한다(설계 판단).** ① 이 결합은 **읽기 방향 한쪽뿐**이며 허브는 아무것도 강제하지 않는다 ② 최악의 경우 나타나는 증상은 "헤드와 카드 사이 여백이 달라진다" 이지 기능 손실이 아니다 ③ 반대 방향(대시보드가 패널 헤드에 의존)은 이미 **T22-124** 가 고정하고 있다. 자동 검사로 이 결합을 강제하는 것은 두 템플릿의 픽셀 값을 묶는 일이라 **명백한 과잉**이다 — 수동 M18 로 충분하다 |

---

## YAGNI 보류 (R2 — 지금 만들지 않는다 + 재방문 트리거)

| # | 보류 항목 | 이유 | 재방문 트리거 |
|---|-----------|------|---------------|
| 6 | **닫는 중 재오픈 시 iframe 재로딩 건너뛰기** | 현재 문서 URL 을 추적하는 상태(`loadedDocumentUrl`)를 하나 더 만들어야 하고, 그 상태와 `openDashboardKey` 의 동기화가 새 불변식이 된다. 초판(즉시 닫기)에서도 재로딩됐으므로 회귀가 아니다 | 닫자마자 같은 카드를 다시 여는 흐름이 실제 사용 패턴으로 보고될 때 |
| 7 | **닫기 전용 이징·시간**(예: 150ms `ease-in`) | 저장소가 `180ms ease-out` 하나로 통일돼 있다(초판 SP5 의 "이미 있는 관례를 새 값으로 흔들지 않는다"). 방향별 이징은 값 2개·검사 앵커 2개를 새로 만든다 | P-9 이 실제 불만으로 보고될 때(R2 승인 항목 2) |
| 8 | **`@starting-style`·`allow-discrete` 신문법 도입** | `visibility` 의 특수 보간만으로 요구가 전부 충족된다. `display` 를 전이시킬 이유가 없다 | 패널을 `display:none` 으로 바꿔야 할 이유가 생길 때(현재 없다) |
| 9 | **헤드에 액션 추가**(새 탭 열기·고정) | 요구에 없다. R2 는 "헤드가 창처럼 보인다"를 고치는 것이지 헤드에 기능을 넣는 것이 아니다 | 패널 안 대시보드를 단독 탭에서 열고 싶다는 요구가 나올 때 |
| 10 | **패널 열림/닫힘을 `body` 밖 다른 요소에도 반영** | 불변식 H1⁗ 조항 ③ 그대로 | — |

---

## 검토했으나 채택하지 않은 대안 (R2 요약)

| 대안 | 기각 사유 |
|------|-----------|
| `dzh-panel-closing` 상태 클래스 | 상태가 셋이 되고 재클릭 시 손으로 걷어내야 한다. `openDashboardKey` 단일 진실이 깨진다(SP12 안 B) |
| `transitionend` 로 blank 시점 결정 | 저감 모드에서 발화하지 않고 백그라운드 탭에서 상한 없이 밀린다. 폴백을 두면 한 일에 메커니즘이 둘이 된다(SP14) |
| `visibility 0s linear 180ms` 지연 기법 | 결과는 같지만 열림 규칙에 `visibility 0s` 를 짝으로 재선언해야 하고, 빠뜨리면 **열 때** 튄다(SP12 안 D) |
| 세대(generation) 토큰으로 재진입 방어 | 변수와 개념을 하나씩 더 쓰면서 취소되지 않은 타이머를 남긴다. `clearTimeout` 한 줄이 더 단순하다(SP15) |
| 밀어내기 복귀는 즉시(패널만 애니메이션) | 한 동작이 두 사건으로 보인다(SP16) |
| 헤드 제목을 보조 텍스트로 축소(시안 B) | "어떤 프로젝트인지는 패널 제목이 말한다"는 초판 YAGNI 보류 2 의 근거가 무너진다 |
| `role="dialog"` → `role="complementary"` 로 함께 변경 | 요구 1 은 시각 요구다. 보조기술 계약까지 바꾸면 "닫을 수 있는 일시적 표면"이라는 성질을 잃는다(R2 전제 2) |
| 폭 고정에 맞춰 브레이크포인트를 960px 로 낮춤 | **산술적으로 실격.** 밀어내기 모드에서 사용량 패널 왼쪽이 26px 잘린다(SP19 ①) |
| 폭 고정에 맞춰 브레이크포인트를 1152px 로 올림 | 여유는 늘지만 지금 정상 동작하는 1024~1151 구간을 오버레이로 강등시킨다. 얻는 것 없이 기능을 뺏는다(SP19 ①) |
| `550px` 리터럴을 검사로 고정 | 폭은 "한 줄 고치면 되는 값"이라는 것이 초판부터의 설계 의도다. 리터럴 검사는 그 한 줄을 고칠 때마다 검사도 고치게 만들어 **의도를 스스로 배반한다**. 기계적으로 지킬 가치가 있는 성질(단일 출처 경유)은 T25-77 이 이미 지킨다(SP19 ④) |
| 구분선 삭제의 보완책으로 `.detail-head{box-shadow:0 1px 0 var(--line)}` | `border-bottom` 을 다른 이름으로 되살리는 것이다 — **T25-85 의 역방향 토큰은 통과하면서 화면에는 같은 전폭 선이 생긴다**(검사를 우회하는 형태). 애초에 보완책 자체가 필요 없다(SP11 ③) |

---

## 정본 이관 표기 (R2 — 원문 삭제 없이 화살표만 덧붙인다)

| 파일 | 지점 | 덧붙일 표기 |
|------|------|-------------|
| 이 문서 | 결정 **SP5** | `→ **부분 번복(R2)** — "닫기 애니메이션을 만들지 않는다"는 사용자 요구로 뒤집혔다. 정본은 SP12(상태 표현)·SP14(지연)·SP15(재진입 가드)·SP16(밀어내기 복귀). 시간·이징(180ms ease-out)과 reduced-motion 원칙은 그대로 유지된다` |
| 〃 | **GOTCHA 1** | `→ **개정(R2)** — 반대로 뒤집혔다. 전이 선언은 이제 기본 규칙에 둔다(SP12). about:blank 번쩍임은 지연 타이머가 막는다(SP14)` |
| 〃 | **승인 항목 4** | `→ **번복(R2, 2026-08-14)** — 사용자가 "닫힐 때도 애니메이션"을 명시 요구했다. 그때의 대안 문구("닫기도 180ms — 이 경우 지연 타이머 + openDashboardKey 재진입 가드를 함께 넣는다")가 그대로 R2 의 설계가 됐다` |
| 〃 | **YAGNI 보류 4** | `→ **해소(R2)** — 재방문 트리거가 발동했다` |
| 〃 | 초판 결정 **SP4** | `→ **번복(R2, 2026-08-14)** — 사용자 지시로 고정 550px. 정본은 결정 SP19` (원문·뷰포트 표는 보존한다 — 550 고정이 무엇을 포기하는지 읽을 수 있어야 한다) |
| 〃 | 초판 **승인 항목 1** | `→ **번복(R2, 2026-08-14)** — 사용자 지시로 고정 550px. 재승인 대상이 아니다` |
| 〃 | 초판 결정 **SP3** | `→ **재도출(R2 재검토)** — 결론(1024px) 유지. 550 고정에서는 하한을 「카드 1열」(902)이 아니라 「사용량 패널」(986)이 정한다(SP19 ①)` |
| 〃 | **시안 C** | `→ **후보 탈락(R2 재검토)** — 시안 A 확정 + iframe 첫 카드가 이미 인셋 선을 그린다(SP11 ③)` |
| `hub-first-entry-and-ui-signals.md` | 결정 **MD4** | 기존 `→ **원칙 유지** …` 문장 **아래에** 한 줄 추가: `→ **원칙 폐기(2026-08-14, R2)** — "열기만 애니메이션한다"는 원칙 자체가 사용자 요구로 폐기됐다. 정본은 hub-detail-side-panel.md 결정 SP12·SP14~SP17(양방향 애니메이션). MD4 의 기술적 근거(<dialog>.close() 가 즉시라 @starting-style·allow-discrete 가 필요하다)는 <dialog> 를 버린 SP1 이후 더 이상 성립하지 않는다` |

> **MD4 재개정이 필요한 이유를 명시한다**: MD4 의 논거는 `<dialog>` 의 `close()` 가 즉시라는
> **요소 고유의 제약**이었다. SP1 이 `<aside>` 로 바꾼 순간 그 제약이 사라졌고, R2 는 그
> 사라진 제약을 실제로 활용한다. "원칙 유지"라는 초판의 이관 표기는 이제 사실과 다르다.

---

## R2 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | CSS 전이 이동 + `visibility`·`pointer-events` + 저감 6셀렉터(SP12·SP13·SP16·SP17) | 수동 M12·M15·M17 |
| 2 | JS 상수·`scheduleBlankAfterSlide`·open/close 개정(SP14·SP15) | 수동 M5(개정)·M13·M14·M16 |
| 3 | 헤드 CSS·마크업 교체(SP11, 좌우 패딩 16px) | 수동 M18·M19·M20 |
| 3-b | `:root` 66행 `--dzh-panel-width:550px` 치환(SP19) | 수동 **M21** + `bash tests/run.sh` 의 T25-77·T25-78 통과 |
| 4 | 주석·README 개정(SP18) + PRP 이관 표기 2건 | 이관표 대조 |
| 5 | `tests/run.sh` — T25-79 개정, T25-81 토큰 1개 추가, 신규 T25-82~85, **함수 설명 문자열 2곳(2346·2349행) `T25-1~T25-85` 로 갱신**, 뮤테이션 12건 | `bash tests/run.sh` 전 항목 통과 |

---

## R2 재승인 요청 항목

> **재구성(R2 재검토, 2026-08-14).** 초안의 6건 중 **항목 1(헤드 시안)** 은 사용자 지시로 확정되어
> 「R2 확정 사항 C1」로 옮겼고, 재검토에서 새로 확정된 **패널 폭 550px** 은 C2 로 들어갔다.
> 남은 **5건이 재승인 대상**이다.
>
> **번호는 초안 그대로 둔다(2~6).** 문서 곳곳(SP17·P-9·P-11·P-13·YAGNI 보류 7)이 이 번호로
> 서로를 참조하고 있어, 번호를 당기면 그 참조들이 조용히 어긋난다 — 이 저장소가 결정 코드를
> 재사용하지 않는 것과 같은 이유다.

### 재승인 대상 한눈에 보기

| 항목 | 내용 | 재검증 결과 | 권고 |
|------|------|-------------|------|
| ~~1~~ | ~~헤드 시안 A~~ | **확정(C1)** — 근거 문단만 교체됨(SP11) | — |
| **2** | 닫기 시간·이징 **180ms `ease-out`** | **유지.** `hub_template.html` 의 `transition:` 선언이 **정확히 3개이고 전부 `180ms ease-out`** 임을 병합 후 재확인했다(251·257·259행) | 채택 |
| **3** | 밀어내기 복귀도 함께 애니메이션 | **유지.** 근거·비용(선언 이동뿐, 추가 0줄) 모두 그대로 | 채택 |
| **4** | JS 는 `prefers-reduced-motion` 을 읽지 않는다 | **유지 + 단서 1개 추가**(아래) | 채택 |
| **5** | 나가는 패널은 클릭을 받지 않는다(`pointer-events` 짝) | **유지.** 근거 그대로 | 채택 |
| **6** | T25-85 역방향 토큰 = `border-bottom` **파일 전체 0건** | **강화됨.** 시안 C 가 후보에서 탈락해 토큰을 좁힐 이유가 사라졌다. `grep -c` 재확인 결과 여전히 1건뿐이다 | 채택 |
| — | (신설) 패널 폭 **550px** | **확정(C2)** — 결정 SP19 | — |

### R2 승인 항목 1 — 헤드 시안: **A(패널 헤더)** — 구분선 삭제 + `»` + 24px 투명 사각 버튼 (결정 SP11)

> **→ 확정(R2 재검토, 2026-08-14) — 재승인 대상이 아니다.** 사용자가 시안 A 를 확정했다.
> **단, 아래 권고문의 근거 중 하나는 이제 다른 내용으로 대체됐다** — 구분선 삭제의 근거였던
> 「iframe 배경과의 색 단차」는 PR #3 으로 성립하지 않고, 새 근거는 SP11 의 「구분선 근거 —
> R2 재검토 개정」이다. 시안 A CSS 에서 바뀐 값은 **좌우 패딩 18px → 16px** 한 곳뿐이다.

**권고: 시안 A 채택.** 근거는 취향이 아니라 파일 안의 실측이다 — `border-bottom` 은 이 파일에서
`.detail-head` 한 곳뿐이고(270행), `.icon-btn` 은 그 주석이 스스로 "**모달** 닫기 버튼과 공유"라고
적은 최상위 액션 표기이며(181행), 헤더의 관용구는 `flex:1 1 auto` + 후행 `flex:0 0 auto` 다
(`.project-head` 122·135·145행). 새 색 리터럴 0개.
**대안:** 시안 C(인셋 구분선 유지 — 분리감을 더 원할 때) / 시안 B(제목 축소 — **비권고**, 초판
YAGNI 보류 2 의 근거를 무너뜨린다) / 글리프만 `✕` 유지(시안 A + `✕`).

### R2 승인 항목 2 — 닫기 시간·이징: **180ms `ease-out`**(열기와 동일) (결정 SP12·SP16)
**권고: 채택.** 저장소가 `180ms ease-out` 하나로 통일돼 있고(초판 SP5), 방향별 이징을 도입하면
값 2개·검사 앵커 2개가 새로 생긴다. **대안:** 닫기만 `150ms ease-in`(진입=감속·이탈=가속이라는
관례적 조합. 채택 시 T25-84 의 추출 정규식과 T25-79-a 토큰을 함께 고친다).

> **재검증(R2 재검토) — 유지.** "저장소가 하나로 통일돼 있다"를 실측으로 확인했다:
> `hub/bin/hub_template.html` 의 `transition:` 선언은 **정확히 3개**(251·257·259행)이고
> **전부 `180ms ease-out`** 이며, 네 번째는 무효화(`transition:none`, 267행)다. PR #3 은
> 이 파일을 건드리지 않았으므로 이 근거는 초안 그대로 유효하다.

### R2 승인 항목 3 — **밀어내기 복귀도 함께 애니메이션한다** (결정 SP16)
**권고: 채택.** 패널만 나가고 배경이 즉시 튀면 한 동작이 두 사건으로 보인다. 비용은 전이 선언
2개를 열림 규칙 → 기본 규칙으로 **옮기는 것뿐**(추가 0줄). **대안:** 패널만 애니메이션(배경 즉시
복귀 — 리플로우 시간을 180ms 에서 0 으로 줄이지만 초판 P-1 의 후퇴 경로와 같은 상태가 된다).

### R2 승인 항목 4 — **JS 는 `prefers-reduced-motion` 을 읽지 않는다**(지연은 언제나 180ms) (결정 SP17)
**권고: 채택.** 요구 5 의 문면("저감 모드에서는 `about:blank` 도 즉시")과 **다른 제안**이라 특히
확인이 필요하다. 저감 모드에서 패널은 t=0 에 이미 보이지 않으므로 180ms 뒤 blank 는 관측
불가능하고, iframe 폴링 주기(5초) 대비 무의미한 차이다. 대신 미디어 쿼리 문자열의 이중 정의
(CSS·JS)를 만들지 않는다. **대안:** `matchMedia('(prefers-reduced-motion:reduce)').matches ? 0 : 180`
— 경로는 여전히 하나지만 이중 정의가 하나 늘고, 그러면 T25-78 류의 문자열 일치 검사가 하나 더 필요하다.

> **재검증(R2 재검토) — 유지 + 정직한 단서 1개.** 병합된 `/dashboard` 템플릿에는
> `prefers-reduced-motion` 이 **0건**이고 `.bar-inner{…transition:width .4s}`(1276행)가 하나 있다.
> 즉 **저감 모드 사용자가 패널을 열면 패널·밀어내기는 멈추지만 iframe 안 진행바는 계속
> 애니메이션한다.** 이것은 이 항목의 판단(지연값을 분기할 것인가)과는 **무관한 별개 사안**이며,
> 고치려면 `/dashboard` 템플릿을 바꿔야 해 **초판 전제 2 를 깬다** — 그래서 R2 는 손대지 않는다.
> **관측 사실로 기록만 남긴다**(향후 `/dashboard` 쪽 요구가 생기면 그쪽 PRP 의 입력이다).

### R2 승인 항목 5 — **나가는 패널은 클릭을 받지 않는다**(`pointer-events` 짝) (결정 SP13)
**권고: 채택.** 선언 2개, JS 0줄. 닫기 애니메이션이 만들어 낸 새 상태("JS 는 닫힘, 픽셀은 남음")를
입력 계층에서도 닫힘으로 만든다. **대안:** 미도입(180ms 동안 죽은 닫기 버튼이 클릭을 삼킨다).

### R2 승인 항목 6 — 검사 T25-85 의 역방향 토큰을 **`border-bottom` 파일 전체 0건**으로 잡는다 (G8)
**권고: 채택.** 지금 실제로 1건뿐이므로 "허브에는 가로 구분선이 없다"는 규칙을 통째로 고정할 수
있다. **대안:** 토큰을 `border-bottom:1px solid var(--line)}` 로 좁힌다(시안 C 를 고르면 이쪽이
**필수**다 — 시안 C 는 `--soft` 인셋 선을 남기므로).

> **재검증(R2 재검토) — 권고가 더 단단해졌다.** ① `grep -c border-bottom hub/bin/hub_template.html`
> 은 병합 후에도 **1**(270행, `.detail-head`)이다. ② **시안 C 가 후보에서 탈락**했으므로(사용자가
> 시안 A 를 확정했고, iframe 첫 카드가 이미 인셋 선을 그린다) 토큰을 좁혀야 할 이유 자체가
> 사라졌다 — 대안 문구는 이제 **선택지가 아니라 기록**이다.
> **함께 막아야 할 우회로**: 이 검사는 `border-bottom` 이라는 **철자**를 보므로,
> `.detail-head{box-shadow:0 1px 0 var(--line)}` 로 같은 전폭 선을 되살리면 **통과한다.**
> 그 우회는 「검토했으나 채택하지 않은 대안(R2)」에 명시해 두었다 — 검사로 막지 않는 이유는,
> 막으려면 `box-shadow` 전체를 금지해야 하는데 `.icon-btn`·`.card`·`.usage` 가 전부 쓰기 때문이다
> (**규칙이 대상을 넘어서면 안 된다**).
