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
| **승인 상태** | **승인됨(2026-08-14)** — 「승인 요청 항목」 1~6 전부 권고안대로 확정 |

### 개정 이력

| 개정 | 내용 |
|------|------|
| 초판 (2026-08-14) | 요구 R1~R3 설계. 결정 코드는 두 글자 **SP**(Side Panel)를 쓴다 — 단일 문자 A~Z 는 기존 PRP 들이 소진했고, 앞선 문서가 **UT/TR/DG/MD** 로 두 글자 관례를 이미 확립했다. 불변식 **H1‴ → H1⁗** 개정 |

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
| P-2 | **패널 안 대시보드가 좁아 읽기 불편** | `/dashboard` 템플릿에 `@media` 가 하나도 없음을 확인했다 — 좁아지면 `ellipsis` 로 정보가 준다. SP4 의 `clamp` 상한 720px 이 완화책이고, 그래도 부족하면 **폭 한 줄**을 키운다. 템플릿 축약 CSS 도입은 YAGNI 보류 3 |
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
| 4 | **닫기 애니메이션** | SP5. `about:blank` 지연과 재클릭 경쟁 상태를 불러온다 | 승인 항목 4 에서 사용자가 원한다고 답할 때(그때는 지연 타이머 + `openDashboardKey` 재진입 가드를 함께 설계한다) |
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
