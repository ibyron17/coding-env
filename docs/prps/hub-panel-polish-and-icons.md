# 허브 — 상세 패널 위계 정리 · 헤더 높이 고정 · 새로고침 회전 · lucide 아이콘 전환 (PRP)

> 요구 4건: **R1** 상세 패널의 `detail-head` 아래에 대시보드가 그냥 붙어 보인다 ·
> **R2** 안내 줄 유무에 따라 헤더 높이가 달라져 패널이 들썩인다 ·
> **R3** 새로고침 버튼을 누르면 아이콘이 한 바퀴 돈다 ·
> **R4** 남은 유니코드 글리프 3개(`☾/☀` · `≡` · `»`)를 lucide 인라인 SVG 로 바꾼다

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_template.html` **1개 파일이 기능의 전부** + `tests/run.sh` + `hub/README.md` + 이 문서 |
| 브랜치 | `main` (HEAD `12d49d6`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-card-interactions-and-usage.md`](./hub-card-interactions-and-usage.md)(N1~N8) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md)(Y1~Y4) → [`hub-detail-side-panel.md`](./hub-detail-side-panel.md)(SP1~SP19 · 불변식 H1⁗) → [`hub-session-revival-and-stale-tier1.md`](./hub-session-revival-and-stale-tier1.md)(GN5~GN7) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 공개 DOM 계약(`#dzh-detail-note` 의 토글 수단)과 머리 주석 불변식이 함께 바뀐다 |
| 규모 | **Small~Medium** — 신규 1개(이 문서) / 수정 3개 파일. 템플릿 순증 약 **+52 / −14줄** |
| **Python 변경** | **없음** — `hub/bin/*.py` 전체에 `detail-note`·`refresh`·`glyph` 관련 문자열이 0건임을 확인했다. 스냅샷 계약·서버 경로는 그대로다. 순수하게 **표현 계층**이다 |
| 새 외부 의존성 | **런타임 의존성 0개.** lucide 아이콘의 `<path>` 좌표만 정적 SVG 로 옮겨 적는다 — 기존 새로고침 버튼(334~341행)이 이미 세운 선례다(결정 PV9) |
| 새 색 토큰 | **0개.** `--bg`·`--surface`·`--line`·`--muted`·`--attention` 만 재배치한다 |
| 결정 코드 | **PV**(Panel Visual). 단일 문자 A~Z 는 기존 PRP 들이 소진했고 두 글자 관례(SP·MD·GN·DG·ZG·RV)가 이미 확립돼 있다. `PV`·`MS` 는 저장소 전체에서 미사용임을 확인했다 |
| 승인 상태 | **승인됨 · 구현·검수 완료**(승인 항목 1~5 전부 권고안대로 채택, 검수 PASS — Critical/Major 0건) |

---

## 요구사항 요약

허브의 우측 상세 패널(`hub-detail-side-panel.md` 결정 SP1·SP11)은 헤드 아래에 곧바로
프로젝트 대시보드 `<iframe>` 을 붙인다. R2 재검토 당시의 근거는 **"iframe 안 첫 카드의 상단
테두리가 구분선 자리를 대신 그린다"** 였는데(SP11), 실제 렌더에서는 그 논리가 성립하지
않는다 — 패널 헤드의 배경(`--surface`)과 대시보드 첫 카드의 배경(`--surface`)이 **같은 색**이고,
둘 사이에 있는 것은 카드의 1px 테두리 하나뿐이다. 결과적으로 헤드가 카드 **안쪽 제목처럼**
읽히고, 좌우 16px 구간에만 페이지 배경(`--bg`)이 실낱같이 보여 어색한 절취선을 만든다.
이 문서는 **구분선을 되살리지 않고**(SP11 의 결론은 옳다) 패널 표면 자체를 페이지 배경으로
바꿔 헤드-콘텐츠 위계를 세운다.

같은 헤더 영역에는 두 번째 문제가 있다. 안내 줄(`#dzh-detail-note`, 결정 GN6)은 `hidden`
속성으로 토글되므로 **있는 프로젝트와 없는 프로젝트의 헤더 높이가 다르다.** 패널을 열어 둔
채 다른 카드를 누르면(결정 SP8 의 "내용만 교체") 그 자리에서 iframe 이 위아래로 튄다.

나머지 둘은 상호작용 마감이다 — 새로고침이 접수됐다는 즉시 피드백(R3)과, 저장소에 마지막으로
남은 유니코드 글리프 3개를 이미 도입된 아이콘 체계로 통일하는 것(R4)이다.

### 사용자 스토리

| # | 스토리 |
|---|--------|
| S1 | 패널을 열면 제목이 **페이지 배경 위에** 서고, 그 아래 대시보드 카드가 **떠 있는 카드**로 읽힌다. 허브 카드·대시보드 단독 화면과 같은 위계다 |
| S2 | 안내 줄이 있는 프로젝트와 없는 프로젝트를 번갈아 눌러도 **대시보드가 시작하는 y 좌표가 움직이지 않는다** |
| S3 | 안내 줄이 길어도 **한 줄로 잘리고**, 전문은 마우스를 올리면 툴팁으로 보인다 |
| S4 | 새로고침을 누르면 아이콘이 **한 바퀴 돌아** 클릭이 접수됐음을 알려준다. 연달아 눌러도 매번 처음부터 다시 돈다 |
| S5 | "동작 줄이기"를 켠 사용자는 **회전을 보지 않지만 새로고침은 그대로 동작한다** |
| S6 | 테마 버튼·드래그 핸들·닫기 버튼이 새로고침 버튼과 **같은 선 두께·같은 시각 언어**를 갖는다 |

### 성공 기준 (검증 가능한 형태)

| # | 기준 | 검증 |
|---|------|------|
| G1 | `.detail-panel` 이 `background:var(--bg)` 이고, `.detail-head` 에는 **어떤 배경·테두리 선언도 없다** | T25-95 |
| G2 | `hub_template.html` 의 `border-bottom:` 선언이 **여전히 0건**이다(G8 승계 — SP11 을 번복하지 않았다는 기계적 증거) | T25-85(무수정) |
| G3 | `#dzh-detail-note` 마크업에 `hidden` 속성이 **없고**, JS 에 `panelNoteEl.hidden` 이 **0건**이다 | T25-96 |
| G4 | `.detail-note` 가 `white-space:nowrap` + `visibility:hidden` 를 갖는다(높이 고정의 두 필요조건) | T25-96 |
| G5 | 회전 애니메이션 규칙과 `prefers-reduced-motion` 무효화가 **세트로** 있고, 무효화가 **소스 순서상 뒤**에 있다 | T25-97 |
| G6 | 회전 시간 숫자가 **CSS 에만** 있다 — 회전 IIFE 범위에 `setTimeout(` 이 0건이다 | T25-97 |
| G7 | 글리프 리터럴 `>☾<`·`☀`·`>≡<`·`>»<` 가 **전부 0건**이고, CDN·런타임 로더 흔적(`cdn.`·`unpkg`·`createIcons`)도 0건이다 | T25-98 |
| G8 | `hub/README.md` 의 아이콘 설명이 화면과 일치한다(`☾/☀`·`≡` 표기 소멸) | T25-99 |

---

## 확정된 전제 (재론하지 않는다)

1. **허브 파이썬은 한 줄도 바꾸지 않는다.** 스냅샷 계약·서버 경로·`dashboard_key` 파생 규칙은
   전부 그대로다(SP 초판 전제 1 승계).
2. **`/dashboard` 생성물(`commands/dashboard.md`)도 바꾸지 않는다.** 이 PRP 는 iframe 안 문서를
   **읽기만** 한다 — 특히 `body.dz-embedded #dz-page-head{display:none}`(1352행)과
   `.wrap{max-width:860px;margin:0 auto 32px;padding:0 16px}`(1272행), `.card{…border:1px solid
   var(--line);border-radius:14px…}`(1273행), `body{background:var(--bg)}`(1271행)이
   R1 설계의 입력값이다. 이 네 줄이 바뀌면 결정 PV1 의 근거를 다시 봐야 한다.
3. **새 색 토큰을 만들지 않는다**(SP 초판 전제 4 승계). T25-29·T25-88 이 리터럴 색 회귀를
   기계적으로 막는다.
4. **불변식 H1⁗ 는 유지된다.** 패널·툴팁·사용량·테마 토글은 정적 노드이고 폴링은 이들을
   교체하지 않는다. 이 PRP 는 그 목록을 **늘리지도 줄이지도 않는다** — 다만
   `#dzh-detail-note` 의 갱신 수단이 「`hidden`·`textContent`」에서 「클래스 1개」로 좁아지므로
   머리 주석 41~44행을 개정한다(결정 PV5).
5. **`role="dialog"`·`aria-labelledby`·`aria-label="닫기"`·`data-tooltip="닫기 (Esc)"` 는
   건드리지 않는다**(SP R2 전제 2 승계). 이번 요구는 전부 **시각·모션** 요구다.

### 비목표 (이번 범위 밖 — 명시적으로 건드리지 않는다)

| 항목 | 이유 |
|------|------|
| iframe 안 대시보드의 CSS 변경 | 전제 2 위반. R1 은 **패널 쪽 표면만** 바꿔서 해결된다 |
| 아이콘 스프라이트(`<symbol>`+`<use>`) 도입 | 아이콘이 4종뿐이고 각 1~2회 쓰인다. 재사용 1회짜리에 간접층을 만드는 것은 추측성 추상화다(YAGNI 보류 1) |
| 새로고침 회전을 "폴링이 끝날 때까지 계속 돌리기" | 상태 기계(진행 중/완료/실패)가 생기고, 캐시 히트로 20ms 만에 끝나면 오히려 깜빡임이 된다(결정 PV6, YAGNI 보류 2) |
| 카드 드래그 핸들의 조작 방식 변경 | 결정 DG1~DG7 은 그대로다. **모양만** 바꾼다 |
| 패널 폭·브레이크포인트 | 결정 SP19(550px)·SP3(1024px) 무변경 |

---

## 영향 범위

### 수정 파일 (3개 + 이 문서)

| 파일 | 무엇을 | 왜 |
|------|--------|-----|
| `hub/bin/hub_template.html` | ① 머리 주석 41~44행(안내 줄 계약) 개정 + 아이콘 출처 1줄 신설 ② `.card-drag-handle` 규칙(134~137행)에서 글꼴 선언 2개 제거 + `svg` 크기 규칙 1줄 ③ `.detail-panel`(256~261행) 배경 토큰 교체 + 주석 개정 ④ `.detail-head`(288~297행) 패딩 조정 + 주석 개정 ⑤ `.detail-close`(305~310행) 글꼴 선언 3개 제거 + `svg` 크기 규칙 1줄 ⑥ `.detail-note`(312~314행) 전체 교체 ⑦ 회전 `@keyframes`+규칙+저감 무효화 3줄 신설(`.refresh-btn.connection-lost` 210행 뒤) ⑧ 테마 아이콘 스와핑 CSS 3줄 신설 ⑨ 테마 토글 마크업(342~343행) SVG 2개로 교체 ⑩ 닫기 버튼 마크업(361~362행) SVG 로 교체 ⑪ 안내 줄 마크업(364행) 교체 ⑫ 테마 IIFE 의 `THEME_GLYPH` 폐기(379·408행) ⑬ 회전 IIFE 신설 ⑭ `renderDragHandle`(792~795행) SVG 상수화 ⑮ 패널 IIFE 의 안내 줄 토글(1255~1257행) 교체 | R1~R4 전부 |
| `tests/run.sh` | T25-85 개정(닫기 글리프 토큰), 헤더 문구 2곳(2345·2349행) 범위 갱신, **신규 T25-95~T25-99** | 회귀 검사 |
| `hub/README.md` | 142행 「테마 버튼은 … 아이콘(☾/☀)」 · 177행 「카드 왼쪽 위의 `≡`」 두 문장 | 화면과 문서의 어긋남 방지(T25-99) |

### 미영향 — 건드리지 않는 이유 (직접 확인함)

| 대상 | 근거 |
|------|------|
| `hub/bin/*.py` 전부 | 이 PRP 가 만지는 어떤 식별자도 파이썬에 없다(`grep -rn "detail-note\|refresh-btn\|THEME_GLYPH" hub/bin/*.py` → 0건) |
| `commands/dashboard.md` | 전제 2. iframe 안 문서는 **읽기 전용 입력**이다 |
| T25-63 (3253~3269행) | `<aside id="dzh-detail-panel"`·`id="dzh-detail-frame"`·`.icon-btn`·`THEME_CYCLE = ['light', 'dark']`·`'system'` 부재만 본다. **전부 그대로 남는다**(테마 상태 기계는 무변경 — 아이콘 표현만 바뀐다) |
| T25-76·T25-77·T25-78·T25-79·T25-80 | 패널 마크업 id·레이아웃 토큰·브레이크포인트·슬라이드 전이·`about:blank` 만 본다. 배경 토큰과 무관 |
| T25-88 | `.tier1-prev-label`·`.detail-note` 규칙에 `#` 색 리터럴 0건을 요구한다 — 새 `.detail-note` 규칙도 토큰만 쓰므로 통과(G9 승계) |
| T25-89 | `var PANEL_OPEN_BODY_CLASS` 줄부터 파일 끝까지 `snapshot` 0건을 요구한다. 회전 IIFE 는 **패널 IIFE 앞**에 두므로 이 범위에 들어가지 않는다(GOTCHA 5) |
| T25-93 | `hub_template.html` 의 `run.is_running` 등장 횟수 4를 요구한다 — 세션 칩 코드는 손대지 않는다 |
| `.icon-btn svg{width:18px;height:18px}` (206행) | 헤더 클러스터 두 버튼이 공유한다. 테마 버튼 안에 SVG 가 **2개**가 되어도 규칙은 그대로 적용된다(하나는 `display:none`) |
| 드래그 동작(결정 DG1~DG7) | `renderDragHandle` 의 `draggable`·`aria-hidden`·`data-tooltip`·클래스는 전부 유지한다. 자식 노드만 글리프 → SVG |

---

## 결정 기록

### 결정 PV1 — 패널 표면을 `--surface` → `--bg` 로 바꾼다. **구분선은 되살리지 않는다**

문제를 정확히 좁히면 이렇다. 패널을 위에서부터 훑으면 색이 이렇게 놓여 있다:

| 구간 | 지금 칠해지는 색 | 출처 |
|------|------------------|------|
| 헤드(제목·닫기) | `--surface` | `.detail-panel{background:var(--surface)}` (258행) |
| 헤드의 아래쪽 패딩 12px | `--surface` | 같은 규칙 |
| iframe 최상단 좌우 16px | `--bg` | 대시보드 `body{background:var(--bg)}` + `.wrap{padding:0 16px}` |
| iframe 최상단 가운데 | `--surface` | 대시보드 첫 `.card{background:var(--surface)}` — `margin-top` 이 0이라 **y=0 에서 시작한다** |

즉 **흰 헤드 → 흰 카드**가 1px 선 하나를 사이에 두고 맞닿는다. SP11 이 예측한 "카드 상단
테두리가 구분선 자리를 대신한다"는 관측은 맞지만, 그 선의 **위아래가 같은 색**이라 사용자에게는
구분선이 아니라 "카드 안에 그어진 줄"로 읽힌다. 좌우 16px 의 `--bg` 조각은 그 인상을 더
어색하게 만든다(선이 양 끝에서 끊긴다).

| 안 | 얻는 것 | 잃는 것 |
|----|---------|---------|
| A. `.detail-head` 에 `border-bottom` 복원 | 1줄로 끝난다 | **SP11 을 정면으로 번복한다** — 헤드가 다시 다이얼로그 타이틀바로 읽힌다. G8·T25-85(파일 전체 `border-bottom:` 0건)를 깨야 한다. 그리고 흰 배경 위 흰 배경이라는 **원인은 그대로**라 카드 테두리와 겹쳐 선이 2개로 보인다 |
| B. `.detail-head{background:var(--soft)}` 밴드 | 헤드가 띠로 읽힌다 | 60px 안에 `--soft`→`--bg`→`--surface` 3색이 쌓여 오히려 시끄럽다. 다크에서 세 값(`#1B2634`·`#0E1621`·`#16202D`)의 명도차가 작아 띠가 얼룩처럼 보인다 |
| C. `.detail-head`+`.detail-note` 만 `background:var(--bg)` | 패널의 `--surface` 가 남아 허브 배경과의 대비를 유지한다 | iframe 이 `about:blank` 인 순간(열기 직후·닫힘 뒤) 프레임 영역이 패널 배경(`--surface`)으로 보인다 — 다크에서 **흰 번쩍임의 축소판**이 남는다 |
| **D. `.detail-panel{background:var(--bg)}` — 패널을 "카드"가 아니라 "페이지"로 선언한다** | ① 헤드의 아래 패딩과 안내 줄 자리가 **`--bg` 여백**이 되어 카드가 명확히 떠오른다 ② 대시보드 단독 화면의 `#dz-page-head`(=`--bg` 위의 제목 행)와 **같은 구성**이 된다 — 패널 헤드는 구조적으로 그 헤더의 대역이다(`body.dz-embedded #dz-page-head{display:none}`, `commands/dashboard.md` 1352행) ③ `about:blank` 구간도 `--bg` 라 이어져 보인다 ④ 선언 1개 교체 | 밀어내기 모드에서 허브 본문(`--bg`)과 패널(`--bg`)의 **면색 대비가 사라진다** — 경계는 `border-left:1px solid var(--line)` 과 그림자에만 의존한다 |

> **결정 PV1 — 안 D.** SP11 의 「구분선을 그리지 않는다」는 **유지**하고, 그 결론이 성립하기
> 위한 조건(헤드와 카드가 같은 색이 아닐 것)을 이번에 갖춘다.
> 근거의 핵심은 **대역(代役) 관계**다 — 대시보드는 임베드될 때 자기 헤더 행을 숨기고 그 역할을
> 패널 헤드에 넘긴다. 넘겨받은 쪽이 넘겨준 쪽과 다른 표면 위에 서 있었던 것이 이 문제의
> 원인이므로, 같은 표면(`--bg`)으로 맞추는 것이 가장 적은 수정이면서 가장 정확한 수정이다.
> 잃는 것(허브↔패널 면색 대비)에 대해서는 리스크 P-1 과 1줄 후퇴 경로를 둔다.

### 결정 PV2 — 헤드-카드 사이 여백은 **안내 줄 자리**가 만든다 (R1 과 R2 의 합류점)

R2 를 해결하려면 안내 줄 자리를 **항상 예약**해야 한다(PV3). 예약된 그 자리는 안내가 없는
프로젝트에서 빈 공간이 되는데, PV1 이후 그 공간은 `--bg` 다 — 즉 **버려지는 공간이 아니라
헤드와 카드를 갈라 주는 여백이 된다.** 두 요구가 같은 한 조각을 서로 다른 이유로 필요로 하므로,
따로 쓰던 별도의 여백(`padding-bottom` 증량 등)을 만들지 않는다.

여백의 산술(고정값 — 안내 줄 유무와 무관):

| 조각 | 값 | 근거 |
|------|-----|------|
| `.detail-head` 아래 패딩 | **10px** | `#dz-page-head{margin:28px auto 10px}`(대시보드 1326행)의 아래 여백과 같은 값 |
| 안내 줄 한 줄 상자 | **16px** | `.detail-note{line-height:16px}` — 아래 PV3 이 명시 선언한다 |
| 안내 줄 아래 패딩 | **12px** | 기존 10px 에서 2px 증량. 헤드 블록의 총 높이가 카드 상단 반경(14px)보다 커야 카드가 "붙어" 보이지 않는다 |
| **합계(제목 baseline ~ 카드 top)** | **38px 고정** | 프로젝트가 바뀌어도 변하지 않는다 |

### 결정 PV3 — 안내 줄은 **정적 텍스트 + 클래스 토글**. `hidden` 속성을 버린다

지금은 `panelNoteEl.hidden = !isPreviousTask` 로 토글한다(1256행). `hidden` 은 UA 규칙
`[hidden]{display:none}` 이라 **상자 자체가 사라져** 헤더 높이가 달라진다 — 이것이 R2 의 원인
그 자체다.

| 안 | 평가 |
|----|------|
| A. `hidden` 유지 + 부모에 `min-height` | 헤더 높이는 고정되지만 **제목이 위로 붙었다 가운데로 갔다** 한다(높이는 같은데 내용 정렬이 바뀐다). 래퍼 요소를 새로 만들어야 하고, 안내 줄이 두 줄로 접히면 `min-height` 를 넘어 다시 깨진다 |
| B. `hidden` 유지 + 두 줄 최악값으로 `min-height` | 안내 없는 프로젝트에서 32px 넘는 빈 공간이 상시로 남는다. 그리고 세 줄로 접히면 또 깨진다 — **폭에 의존하는 고정은 고정이 아니다** |
| **C. 텍스트를 마크업에 고정하고 `visibility` 로만 토글 + 한 줄 클램프** | 상자가 **항상** 존재하고(높이 고정), `visibility:hidden` 은 접근성 트리에서도 빠지므로 빈 안내가 낭독되지 않는다. `white-space:nowrap` + `text-overflow:ellipsis` 가 **폭과 무관하게** 정확히 한 줄을 보장한다 |

> **결정 PV3 — 안 C.**
> **`textContent` 를 JS 로 채우지 않고 마크업에 굳히는 것**이 이 안의 핵심이다. 문구는 상수
> 하나(`DETAIL_NOTE_TEXT`, 1198행)이고 프로젝트마다 달라지지 않는다 — JS 로 채우면 "빈 문자열일
> 때 상자 높이가 0 이 된다"는 함정(빈 블록 요소는 줄상자를 만들지 않는다)을 `min-height` 로
> 다시 막아야 하고, 그러면 `line-height` 와 `min-height` 두 숫자가 서로를 참조하는 결합이
> 생긴다. 텍스트를 상시 두면 그 문제가 **존재하지 않는다.**
> **한 줄 클램프는 선택이 아니라 필요조건이다** — 오버레이 모드(뷰포트 < 1024px)에서 패널 폭은
> 뷰포트 폭이므로, 320px 화면에서는 어떤 문구든 접힌다. 접히는 순간 "높이 고정"이 무의미해진다.
> 잘린 문구의 전문은 **`data-tooltip` 이 보존한다**(PV4).
> `line-height:16px` 를 명시 선언한다 — 상속값(`body{line-height:1.5}` × 11.5px ≈ 17.25px)은
> 글꼴 메트릭에 따라 반올림이 달라져 "고정"의 근거가 못 된다.

### 결정 PV4 — 잘린 전문은 `data-tooltip` 으로 보존한다 (마크업 속성으로 고정)

전역 툴팁 싱글턴은 `[data-tooltip]` 을 가진 **임의의 요소**를 `document` 위임으로 잡는다
(결정 T1). 안내 줄은 사용량 패널 바깥이므로 "패널 안에는 툴팁을 두지 않는다"는 제약(R5,
결정 UT1)의 적용 대상이 **아니다**.

- `data-tooltip` 도 마크업에 고정한다 — 텍스트와 같은 문자열이므로 JS 가 둘을 동기화할 이유가 없다.
- `visibility:hidden` 인 요소는 hover·focus 대상이 아니므로 **숨어 있을 때 툴팁이 뜰 수 없다.**
  별도 가드를 넣지 않는다(일어날 수 없는 상황에 대한 방어 금지).
- 결과적으로 패널 IIFE 에서 안내 줄 관련 코드는 **클래스 토글 1줄**로 줄어든다 —
  `DETAIL_NOTE_TEXT` 상수(1198행)와 `panelNoteEl.textContent` 대입이 함께 사라진다.

### 결정 PV5 — 불변식 H1⁗ 의 안내 줄 조항을 좁힌다 (머리 주석 41~44행)

| 지금 (41~44행) | 개정 후 |
|----------------|---------|
| `#dzh-detail-note 는 패널의 정적 자식이며 hidden·textContent 만 바뀐다(결정 GN6~GN7)` | `#dzh-detail-note 는 패널의 정적 자식이며 **detail-note-visible 클래스만** 바뀐다(결정 GN6~GN7 → hub-panel-polish-and-icons.md 결정 PV3). 문구와 data-tooltip 은 마크업에 고정돼 있고, 자리는 안내 유무와 무관하게 **항상 예약된다** — 그 예약된 자리가 헤드와 대시보드 카드를 가르는 여백을 겸한다(결정 PV2).` |

`data-tier1-previous` 가 유일한 출처라는 문장(43~44행)은 **그대로 둔다** — 결정 SP1(패널 IIFE 는
스냅샷을 모른다)의 근거이고 T25-89 가 지키고 있다.

### 결정 PV6 — 회전은 **1회 재생**. 폴링 진행 상태와 연결하지 않는다

| 안 | 평가 |
|----|------|
| A. 폴링이 끝날 때까지 무한 회전 | 상태 기계(대기/진행/성공/실패)가 생기고, 로컬 서버라 응답이 수십 ms 만에 오는 것이 정상이라 **한 프레임 깜빡이고 만다**. 실패 표시는 이미 `.refresh-btn.connection-lost`(210행)가 담당한다 — 같은 정보를 두 채널로 말하게 된다 |
| **B. 클릭 시 1회 360° 회전** | "눌렸다"는 사실만 말한다. 결과는 기존 채널(툴팁 문구·`connection-lost` 색)이 이미 말하고 있다. 상태 변수 0개 |

> **결정 PV6 — 안 B.** 요구는 "한 바퀴 돈다"이고, 그 이상을 만들면 없던 상태를 만든다(YAGNI).
> **시간·이징은 `600ms ease-in-out`.** 저장소의 기존 값(180ms 패널 슬라이드·2.6s 카드 글로우)은
> 각각 "표면 이동"과 "상시 호흡"이라 성격이 다르다 — 클릭 피드백 회전은 새 값이 필요하며,
> 600ms 는 한 바퀴가 회전으로 읽히는 하한(약 400ms)과 조작을 기다리게 하지 않는 상한(약 800ms)
> 사이의 관례값이다. 값 변경은 CSS 한 곳이다(PV7).

### 결정 PV7 — 회전 시간은 **CSS 에만** 산다. 해제는 `animationend`

`setTimeout(REFRESH_SPIN_MS)` 로 클래스를 떼면 같은 숫자가 CSS 와 JS 두 곳에 살게 되고,
저장소는 그 어긋남을 이미 한 번 기계 검사로 막아야 했다(T25-84 — 패널 닫기 180ms 3중 일치).
`animationend` 는 **시간을 알 필요가 없다.**

```js
  refreshIconEl.addEventListener('animationend', function(){
    refreshButton.classList.remove(REFRESH_SPIN_CLASS);
  });
```

- 연속 클릭 재시작은 **클래스 제거 → 강제 리플로우 → 재추가** 관용구로 한다. 제거만 하고 곧바로
  추가하면 브라우저가 두 변경을 한 프레임에 합쳐 "변화 없음"으로 처리해 재생되지 않는다.
- 저감 모드에서는 `animation:none` 이라 `animationend` 가 오지 않고 클래스가 남는다.
  **관측 가능한 영향이 0이며**(애니메이션 선언 자체가 없다), 다음 클릭의 제거-재추가가 어차피
  정상 경로를 탄다. 이 하나를 막자고 타이머를 넣으면 PV7 의 이유가 무너진다 — GOTCHA 4 에
  기록만 남긴다.

### 결정 PV8 — 회전 코드는 **독립 IIFE**로 둔다 (렌더 IIFE 에 넣지 않는다)

렌더 IIFE 는 `file://` 모드에서 1149행에서 **조기 반환**한다. 회전 리스너를 그 뒤에 등록하면
`file://` 로 연 허브에서만 회전이 죽는다 — 원인을 찾기 어려운 종류의 결함이다. 앞에 등록하면
동작하지만, 회전은 스냅샷과 아무 관계가 없는 순수 표현이라 **테마 토글·툴팁·상세 패널과 같은
층위의 독립 IIFE**가 옳다(이 파일이 이미 확립한 구성).

- 배치는 **테마 IIFE 바로 뒤**(420행 다음). 헤더 클러스터의 두 버튼을 다루는 코드가 인접한다.
- **패널 IIFE 뒤에 두지 않는다** — T25-89 가 `var PANEL_OPEN_BODY_CLASS` 부터 파일 끝까지
  `snapshot` 0건을 검사한다. 지금은 회전 IIFE 에 그 문자열이 없지만, 뒤에 두면 미래의 수정이
  그 검사에 걸릴 수 있는 자리에 코드를 놓는 셈이다(GOTCHA 5).

### 결정 PV9 — lucide 는 **정적 인라인 SVG 로만** 쓴다. 런타임 의존성이 아니다

"새 외부 의존성 도입"에 해당하는가를 먼저 판정한다.

| 도입 방식 | 이 저장소에서의 판정 |
|-----------|---------------------|
| `<script src="https://unpkg.com/lucide">` + `lucide.createIcons()` | **기각.** ① `file://` 로 열려야 한다는 요구를 깬다(네트워크 없이 아이콘이 사라진다) ② 허브는 로컬 전용 도구인데 외부 오리진에 매 로드 요청이 나간다 ③ 아이콘이 스크립트 실행 뒤에 나타나 첫 페인트가 흔들린다 ④ 빌드 도구가 없어 SRI·버전 고정 관리 주체가 없다 |
| npm 의존 + 빌드 시 인라인 | **기각.** 이 저장소에 빌드 파이프라인이 없다. 파이프라인을 도입하는 비용이 아이콘 4개의 가치를 압도한다 |
| **path 좌표만 옮겨 적은 정적 인라인 SVG** | **채택.** 산출물은 그냥 마크업이다 — 런타임 코드도, 네트워크도, 잠금 파일도 없다. `hub/install.sh` 가 배포하는 파일 수도 그대로다. **선례가 이미 있다**: 새로고침 버튼(334~341행)이 lucide `refresh-cw` 의 4개 `<path>` 를 그대로 담고 있고, 이 문서는 그것과 **같은 방식으로** 나머지 3곳을 맞춘다 |

> **결정 PV9 — 정적 인라인 SVG.**
> 전역 지침의 "새 의존성 추가는 표준 라이브러리로 불가능할 때만"이 겨냥하는 것은 **런타임·빌드
> 그래프에 들어오는 코드**다. 좌표 숫자를 옮겨 적은 마크업은 그 그래프에 들어오지 않는다 —
> 이것은 의존성 도입이 아니라 **디자인 자산 복사**이며, 이미 파일 안에 같은 성격의 자산
> (파비콘 `data:` URI, 11행)이 있다.
> **출처는 명시한다.** lucide 는 ISC 라이선스이고 저작권 고지 유지가 조건이다. 머리 주석에
> 한 줄을 신설한다:
> ```
>   아이콘은 lucide(ISC, https://lucide.dev)의 path 좌표를 그대로 옮겨 적은 정적 인라인
>   SVG 다 — CDN·런타임 라이브러리를 쓰지 않는다(file:// 로도 열려야 하기 때문, 결정 PV9).
>   viewBox·stroke 속성 관용구는 새로고침 버튼(refresh-cw)이 세운 선례를 그대로 따른다.
> ```
> **구현자 주의**: 아래 「아이콘 좌표」 표의 `d` 값은 이 문서 작성 시점의 lucide 아이콘이다.
> 구현 전에 <https://lucide.dev/icons/{이름}> 에서 **한 번 대조**하고, 다르면 사이트 값을
> 정본으로 삼는다(이 문서를 고쳐 적는다).

### 결정 PV10 — 테마 아이콘은 **두 SVG 를 함께 두고 CSS 가 고른다** (`THEME_GLYPH` 폐기)

지금은 `toggleButton.textContent = THEME_GLYPH[theme]`(408행)로 글리프를 갈아 끼운다. SVG 는
`textContent` 로 넣을 수 없다.

| 안 | 평가 |
|----|------|
| A. `toggleButton.innerHTML = THEME_ICON_SVG[theme]` | 동작하지만 **버튼 내부를 매번 재생성**한다. 정적 노드는 속성·textContent 단위로만 갱신한다는 불변식 H1⁗ 의 원칙이 버튼 안쪽에도 그대로 적용된다. 그리고 sun 은 요소가 9개라 JS 안에 60자짜리 마크업 문자열 두 벌이 산다 |
| **B. 두 SVG 를 마크업에 두고 `:root[data-theme]` 로 하나만 보여준다** | JS 는 `data-theme` 속성만 계속 다룬다(지금 하는 일 그대로). 아이콘 갱신 코드가 **0줄**이 된다. `THEME_GLYPH` 객체가 통째로 사라진다 |

> **결정 PV10 — 안 B.**
> 성립 조건을 확인했다: `applyTheme(currentTheme())`(419행)이 IIFE 말미에 **무조건** 실행되고,
> `currentTheme()` 은 `localStorage` 가 막혀도 `resolveSystemTheme()` 로 낙착하므로
> **`<html data-theme>` 은 항상 존재한다.** 즉 CSS 선택자가 빈손이 되는 상태가 없다.
> 글리프 규약(결정 Y4 — 아이콘은 "지금"이 아니라 "전환될 대상"을 가리킨다)은 그대로다:
> 라이트에서 `moon`(다크로 전환), 다크에서 `sun`(라이트로 전환).
> `aria-label`·`data-tooltip` 은 계속 JS(`THEME_ACTION_LABEL`, 380·409~410행)가 맞춘다 —
> 접근성 이름은 CSS 로 표현할 수 없다.

### 결정 PV11 — 드래그 핸들 SVG 는 **모듈 스코프 상수 1개**로 둔다

`renderDragHandle()`(792~795행)은 카드 수만큼 호출된다. 마크업 문자열을 함수 안에 인라인하면
읽기가 어려워지고, 상수로 빼면 이름이 역할을 말한다.

```js
  // lucide grip-vertical(결정 PV9). 카드마다 반복 삽입되므로 상수 1개로 둔다 — 값은 리터럴이라
  // 매 호출 새 문자열을 만들지 않는다.
  var DRAG_HANDLE_ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
    + 'focusable="false"><circle cx="9" cy="12" r="1"/>…</svg>';
```

- 부모 `<span>` 이 이미 `aria-hidden="true"` 라 자식의 `aria-hidden` 은 중복이지만, **새로고침
  버튼 SVG 와 속성 관용구를 같게 유지**한다(복사·이동 시 안전하고, grep 검사가 하나의 패턴만
  본다).
- `data-tooltip="드래그해서 순서 변경"`·`draggable="true"`·클래스는 **한 글자도 바꾸지 않는다**
  (결정 DG1~DG3 유지).

### 결정 PV12 — 닫기 아이콘은 `x` 가 아니라 **`chevrons-right`** 를 권고한다 (승인 항목 3)

요구서는 후보로 `x` 를 제시했다. 그러나 현재 글리프 `»` 는 취향이 아니라 **결정 SP11 이 근거를
적어 고른 값**이다(300~304행 주석):

> 글리프 »: 패널이 오른쪽으로 밀려 나가는 실제 동작(SP12)을 가리킨다 — `✕`(창을 없앤다)와
> 다른 말을 한다.

lucide 에는 `»` 와 **정확히 같은 의미의 아이콘**이 있다 — `chevrons-right`(겹화살표 2개).
이것을 쓰면 R4(글리프를 아이콘으로 통일)를 만족하면서 SP11 의 근거를 **번복하지 않는다.**
`x` 를 고르면 SP11 을 뒤집는 결정이 되므로, 이 문서에서 그 번복을 명시하고 T25-85 의 문구
근거까지 함께 고쳐야 한다.

| 안 | 얻는 것 | 잃는 것 |
|----|---------|---------|
| **A. `chevrons-right` (권고)** | SP11 의 "밀어 보낸다" 의미 유지 · 결정 번복 0건 · T25-85 는 토큰만 교체 | 요구서가 예시로 든 이름과 다르다 |
| B. `x` | 보편적인 닫기 기호 · 오해 여지 최소 | **SP11 을 번복한다.** 비모달 패널을 "창처럼" 읽게 만든 원인 기호로 돌아간다 |

### 결정 PV13 — 글꼴 선언은 **내 변경이 만든 고아만** 제거한다

`.card-drag-handle{…font-size:13px;line-height:1}`(137행)과
`.detail-close{…font:inherit;font-size:13px;line-height:1}`(308행)은 **글리프를 그리기 위한
선언**이다. 자식이 SVG 로 바뀌면 그리는 대상이 없어져 고아가 된다 → 제거한다.
반대로 `.icon-btn`(201~203행)의 선언은 손대지 않는다 — 이번 변경이 만든 고아가 아니고, 테마
버튼 외에 새로고침 버튼도 공유한다.

크기 규칙은 각 클래스 옆에 **국소로** 둔다(공용 규칙으로 묶지 않는다 — 22px 핸들과 24px 닫기
버튼은 앞으로 서로 다른 크기가 될 수 있고, 지금 같은 값인 것은 우연이다):

```css
  .card-drag-handle svg{width:14px;height:14px}
  .detail-close svg{width:14px;height:14px}
```

---

## 아이콘 좌표 (lucide, ISC — 구현 전 lucide.dev 에서 1회 대조)

공통 래퍼 속성은 **새로고침 버튼(335행)과 글자 단위로 같게** 쓴다:

```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"> … </svg>
```

| 쓰이는 곳 | lucide 이름 | 자식 요소 |
|-----------|-------------|-----------|
| `#dzh-theme-toggle` (라이트일 때 보임) | `moon` | `<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>` |
| `#dzh-theme-toggle` (다크일 때 보임) | `sun` | `<circle cx="12" cy="12" r="4"/>` + `<path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>` |
| `span.card-drag-handle` | `grip-vertical` | `<circle cx="9" cy="12" r="1"/><circle cx="9" cy="5" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="19" r="1"/>` |
| `#dzh-detail-close` | `chevrons-right`(권고) | `<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>` |
| 〃 | `x`(승인 항목 3 에서 채택 시) | `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>` |
| (기존, 무변경) | `refresh-cw` | 336~339행 그대로 |

---

## CSS / DOM / JS 계약 (변경 후)

### 1. 회전 (`.refresh-btn.connection-lost` 210행 **뒤**에 삽입)

```css
  /* 새로고침 회전(PV6) — "클릭이 접수됐다"만 말하는 1회 재생이다. 폴링의 진행/성공/실패는
     이미 data-tooltip 문구와 .connection-lost 색이 말하고 있어 여기서 반복하지 않는다.
     시간 숫자는 이 한 곳에만 산다 — JS 는 animationend 로 끝을 알므로 시간을 모른다(PV7). */
  @keyframes dzh-refresh-spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}
  .refresh-btn.refresh-spinning svg{animation:dzh-refresh-spin 600ms ease-in-out}
  /* 무효화는 반드시 위 규칙보다 뒤에 온다(.card.card-working 124행이 세운 관례). */
  @media (prefers-reduced-motion:reduce){.refresh-btn.refresh-spinning svg{animation:none}}
```

### 2. 테마 아이콘 스와핑 (`.icon-btn svg` 206행 **뒤**에 삽입)

```css
  /* 테마 아이콘(PV10) — 두 SVG 를 마크업에 함께 두고 CSS 가 하나만 보여준다. JS 는 아이콘을
     만들지 않는다(정적 노드는 속성만 갱신한다는 불변식 H1⁗ 의 원칙). 보이는 아이콘은 "지금"이
     아니라 "전환될 대상"이다(결정 Y4) — 라이트에서 moon, 다크에서 sun.
     data-theme 는 테마 IIFE 말미의 applyTheme(currentTheme()) 가 무조건 붙이므로 이 선택자가
     빈손이 되는 상태는 없다(localStorage 가 막혀도 시스템 선호로 낙착한다). */
  .theme-toggle .theme-icon-sun{display:none}
  :root[data-theme="dark"] .theme-toggle .theme-icon-moon{display:none}
  :root[data-theme="dark"] .theme-toggle .theme-icon-sun{display:inline}
```

### 3. 패널 표면·헤더 (248~314행 구간 교체)

```css
  /* 프로젝트 상세 패널(SP1) — … (기존 8줄 주석 유지) …
     배경은 --surface 가 아니라 --bg 다(PV1): 이 패널은 "카드"가 아니라 "페이지"이며, 안에
     띄우는 대시보드 문서의 body 도 같은 --bg 를 칠한다. 헤드가 --surface 였을 때는 대시보드
     첫 카드(--surface)와 같은 색이 맞닿아 헤드가 카드 안쪽 제목처럼 읽혔다 — SP11 이 구분선을
     지운 판단은 옳았고, 그 판단이 성립할 조건(헤드와 카드가 다른 표면일 것)을 여기서 갖춘다.
     대시보드는 임베드되면 자기 헤더 행을 숨기고(#dz-page-head) 그 역할을 이 헤드에 넘긴다 —
     넘겨받은 쪽이 같은 표면 위에 서는 것이 정합적이다. */
  .detail-panel{position:fixed;top:0;right:0;bottom:0;left:0;z-index:30;
                display:flex;flex-direction:column;
                background:var(--bg);color:var(--ink);
                border-left:1px solid var(--line);box-shadow:-16px 0 48px rgba(0,0,0,.28);
                transform:translateX(100%);visibility:hidden;pointer-events:none;
                transition:transform 180ms ease-out, visibility 180ms}
  … (266~287행 무변경) …
  /* 패널 헤더(SP11) — … (기존 주석 유지, "iframe 첫 카드의 상단 테두리가 구분선을 대신한다"는
     문단만 PV1 의 근거로 교체) …
     아래 패딩 10px 은 대시보드 단독 화면의 #dz-page-head{margin:28px auto 10px} 과 같은 값이다.
     헤드와 카드 사이의 나머지 여백은 항상 예약된 안내 줄 자리가 만든다(PV2) — 합계 38px 고정. */
  .detail-head{display:flex;align-items:center;gap:10px;padding:16px 16px 10px}
  .detail-title{…무변경…}
  /* 닫기 컨트롤 — … (기존 주석 유지) … 글리프 » 는 lucide chevrons-right 로 바뀌었고(PV12)
     의미는 같다: 패널이 오른쪽으로 밀려 나간다. 접근성 이름은 여전히 aria-label 이 고정한다. */
  .detail-close{width:24px;height:24px;flex:0 0 auto;padding:0;color:var(--muted);
                background:transparent;border:1px solid var(--line);border-radius:6px;
                cursor:pointer;display:inline-flex;align-items:center;justify-content:center}
  .detail-close:hover{color:var(--accent-ink);border-color:var(--accent)}
  .detail-close:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  .detail-close svg{width:14px;height:14px}
  .detail-frame{flex:1 1 auto;width:100%;border:0}
  /* 안내 줄(결정 GN6 → PV3) — 자리를 **항상** 차지한다. hidden 속성 토글을 버린 이유:
     [hidden]{display:none} 은 상자를 없애 헤더 높이가 프로젝트마다 달라지고, 패널을 연 채
     다른 카드를 누르면 대시보드가 위아래로 튄다(요구 R2). visibility:hidden 은 상자를
     남기면서 접근성 트리에서는 빠지므로 빈 안내가 낭독되지 않는다.
     한 줄 클램프는 높이 고정의 필요조건이다 — 오버레이 모드에서 패널 폭은 뷰포트 폭이라
     어떤 문구든 접힐 수 있다. 전문은 data-tooltip 이 보존한다(PV4).
     line-height 를 명시하는 이유: 상속값(1.5)은 글꼴 메트릭에 따라 반올림이 달라져 "고정"의
     근거가 되지 못한다. */
  .detail-note{margin:0;padding:0 16px 12px;font-size:11.5px;line-height:16px;
               color:var(--attention);overflow:hidden;text-overflow:ellipsis;
               white-space:nowrap;visibility:hidden}
  .detail-note.detail-note-visible{visibility:visible}
```

### 4. 마크업 (342~343 · 361~362 · 364행)

```html
      <button id="dzh-theme-toggle" class="icon-btn theme-toggle" type="button"
              aria-label="다크 테마로 전환" data-tooltip="다크 테마로 전환">
        <svg class="theme-icon-moon" viewBox="0 0 24 24" … >…moon…</svg>
        <svg class="theme-icon-sun"  viewBox="0 0 24 24" … >…sun…</svg>
      </button>
```

```html
    <button id="dzh-detail-close" class="detail-close" type="button"
            aria-label="닫기" data-tooltip="닫기 (Esc)">
      <svg viewBox="0 0 24 24" … >…chevrons-right…</svg>
    </button>
  </div>
  <p id="dzh-detail-note" class="detail-note"
     data-tooltip="이전 작업의 대시보드입니다 — 지금 진행 중인 세션이 시작된 뒤 갱신되지 않았습니다."
  >이전 작업의 대시보드입니다 — 지금 진행 중인 세션이 시작된 뒤 갱신되지 않았습니다.</p>
```

### 5. JS 변경 3곳

**(a) 테마 IIFE** — `THEME_GLYPH` 선언(379행)과 `applyTheme` 의 대입(408행)을 **삭제**.
주석 377~378행은 "글리프·라벨" → "아이콘·라벨"로 문구만 고친다.

```js
  function applyTheme(theme){
    document.documentElement.setAttribute('data-theme', theme);   // 아이콘 선택은 CSS 가 한다(PV10)
    toggleButton.setAttribute('aria-label', THEME_ACTION_LABEL[theme]);
    toggleButton.setAttribute('data-tooltip', THEME_ACTION_LABEL[theme]);
  }
```

**(b) 회전 IIFE 신설** — 테마 IIFE 뒤(420행 다음)

```js
(function(){
  // 새로고침 회전(PV6~PV8) — 클릭 피드백 전용. 렌더 IIFE 안에 넣지 않는 이유: 그 IIFE 는
  // file:// 모드에서 조기 반환하므로 등록 위치에 따라 회전이 조용히 죽는다. 스냅샷을 모르는
  // 순수 표현이라 테마 토글·툴팁과 같은 층위의 독립 IIFE 가 맞다.
  var REFRESH_SPIN_CLASS = 'refresh-spinning';
  var refreshButton = document.getElementById('dzh-refresh');
  var refreshIconEl = refreshButton && refreshButton.querySelector('svg');
  if(!refreshButton || !refreshIconEl) return;

  refreshButton.addEventListener('click', function(){
    // 제거 → 강제 리플로우 → 재추가. 제거만 하고 곧바로 추가하면 브라우저가 두 변경을 한
    // 프레임에 합쳐 "변화 없음"으로 처리해 연속 클릭에서 재생되지 않는다.
    refreshButton.classList.remove(REFRESH_SPIN_CLASS);
    void refreshButton.offsetWidth;
    refreshButton.classList.add(REFRESH_SPIN_CLASS);
  });
  // 시간을 JS 가 알 필요가 없다 — 애니메이션이 끝났다고 브라우저가 알려준다(PV7).
  refreshIconEl.addEventListener('animationend', function(){
    refreshButton.classList.remove(REFRESH_SPIN_CLASS);
  });
})();
```

**(c) 패널 IIFE** — `DETAIL_NOTE_TEXT`(1198행) 삭제, 상수 1개 추가, 안내 줄 토글 교체

```js
  var DETAIL_NOTE_VISIBLE_CLASS = 'detail-note-visible';
  …
    // 안내 줄은 문구·data-tooltip 을 마크업에 고정해 두고 클래스만 토글한다(PV3·PV4) —
    // 자리는 항상 예약돼 있어 프로젝트를 바꿔도 헤더 높이가 변하지 않는다.
    panelNoteEl.classList.toggle(DETAIL_NOTE_VISIBLE_CLASS, isPreviousTask);
```

**(d) `renderDragHandle`(792~795행)**

```js
  function renderDragHandle(){
    return '<span class="card-drag-handle" draggable="true" aria-hidden="true" data-tooltip="'
      + escapeHtml(DRAG_HANDLE_HINT) + '">' + DRAG_HANDLE_ICON_SVG + '</span>';
  }
```

---

## GOTCHA (구현자가 틀리기 쉬운 함정)

1. **`border-bottom` 을 되살리지 마라.** T25-85 가 **파일 전체**에서 `border-bottom:` 0건을
   요구한다(3682행). PV1 은 구분선을 다시 그리는 결정이 **아니다** — 표면 색을 바꿔 선이
   필요 없게 만드는 결정이다.
2. **`.detail-note` 의 `textContent` 를 JS 로 채우지 마라.** 빈 블록 요소는 줄상자를 만들지
   않아 높이가 0 이 된다 — `visibility` 로 감춰도 자리가 예약되지 않는다. 문구는 마크업에 있다.
3. **`hidden` 속성을 지우는 것을 잊지 마라.** CSS 만 고치고 마크업의 `hidden` 을 남기면
   UA 규칙이 이겨서 상자가 계속 사라진다(그리고 T25-96 이 실패한다).
4. **저감 모드에서 `refresh-spinning` 클래스가 남는다.** 의도된 동작이다(PV7) — 보이는 효과가
   없고 다음 클릭이 정상 경로를 탄다. 이걸 고치겠다고 `setTimeout` 을 넣으면 회전 시간이
   CSS·JS 두 곳에 살게 되어 G6·T25-97 이 실패한다.
5. **회전 IIFE 를 패널 IIFE **뒤**에 두지 마라.** T25-89 는 `var PANEL_OPEN_BODY_CLASS` 줄부터
   파일 끝까지 `snapshot` 0건을 검사한다 — 그 범위를 늘리지 않는다.
6. **`void refreshButton.offsetWidth;` 를 "쓸모없는 문장"으로 보고 지우지 마라.** 강제 리플로우가
   목적이며, 지우면 연속 클릭에서 회전이 재생되지 않는다. 주석이 이유를 말한다.
7. **테마 SVG 두 개 모두 `.icon-btn svg{width:18px;height:18px}`(206행)의 적용을 받는다.**
   개별 크기 규칙을 새로 만들지 마라 — 중복이다.
8. **`grip-vertical` 은 `<circle>` 6개다.** `fill="none"` 래퍼 아래에서 `r="1"` + `stroke-width="2"`
   는 사실상 점으로 렌더된다. `fill="currentColor"` 로 "고쳐" 두면 lucide 원본과 달라지고
   14px 에서 뭉갠다.
9. **`escapeHtml` 을 아이콘 문자열에 적용하지 마라.** `DRAG_HANDLE_ICON_SVG` 는 코드가 소유한
   리터럴이고 사용자 데이터가 아니다. 통과시키면 태그가 그대로 글자로 보인다.
10. **머리 주석 41~44행 개정을 잊지 마라.** 안내 줄이 `hidden` 으로 토글된다는 서술이 남으면
    다음 사람이 존재하지 않는 계약을 지키게 된다(T25-99 가 역방향으로 막는다).

---

## 엣지 케이스

| # | 상황 | 동작 |
|---|------|------|
| E1 | 안내 줄이 있는 프로젝트 → 없는 프로젝트로 **교체** | 클래스만 떨어진다. **iframe 의 y 좌표가 1px 도 움직이지 않는다**(요구 R2) |
| E2 | 320px 뷰포트(오버레이 모드)에서 안내 줄이 보이는 프로젝트 | 한 줄로 잘리고 말줄임표가 붙는다. 전문은 툴팁 |
| E3 | 안내 줄이 숨어 있는 동안 그 자리에 마우스를 올린다 | `visibility:hidden` 이라 hover 대상이 아니다 — 툴팁이 뜨지 않는다 |
| E4 | 스크린리더로 패널을 훑는다(안내 없는 프로젝트) | `visibility:hidden` 요소는 접근성 트리에 없다 — 빈 안내가 낭독되지 않는다 |
| E5 | 새로고침을 0.1초 간격으로 5번 클릭 | 매번 처음부터 다시 돈다(제거-리플로우-재추가). 폴링은 기존 `busy` 가드가 처리한다 — **회전과 폴링은 서로를 모른다** |
| E6 | `file://` 로 연 허브에서 새로고침 클릭 | 회전이 재생되고 곧 `location.reload()` 로 페이지가 갈린다. 회전 IIFE 가 렌더 IIFE 의 조기 반환 밖에 있어 등록은 항상 성립한다(PV8) |
| E7 | OS "동작 줄이기" 켬 | 회전 없음. 클릭·갱신은 그대로. 패널 슬라이드도 기존대로 즉시(SP17 승계) |
| E8 | `localStorage` 가 막힌 환경에서 테마 버튼 | `applyTheme(currentTheme())` 가 시스템 선호로 `data-theme` 을 붙이므로 아이콘이 정상 표시된다(PV10 의 성립 조건) |
| E9 | 패널이 열린 채 폴링이 `#dzh-app` 을 교체 | 패널은 정적 노드라 무관(H1⁗). 새로 그려진 카드의 드래그 핸들에도 SVG 가 들어 있다 |
| E10 | 다크 테마에서 패널을 연다 | 헤드·여백이 `--bg`(#0E1621), 카드가 `--surface`(#16202D) — 명도차가 라이트보다 작다. **수동 M2 의 실측 대상**이며 미달이면 리스크 P-1 의 후퇴 경로를 쓴다 |

---

## 테스트 계획

### 기존 검사에 대한 영향 (전수 확인 결과)

| 검사 | 위치 | 처리 |
|------|------|------|
| **T25-85** | 3667~3694행 | **개정.** 토큰 `'>»<'` → `'.detail-close svg{'`(승인 항목 3 에서 `x` 채택 시에도 같다). `'.detail-close{'`·`'class="detail-close"'`·`aria-label="닫기"`·`data-tooltip="닫기 (Esc)"` 와 **`border-bottom:` 0건 검사, `'>✕<'` 부재 검사는 무수정** — G2 의 근거가 여기에 있다 |
| T25-63 | 3253~3269행 | **무수정.** `.icon-btn`·`THEME_CYCLE`·`'system'` 부재만 본다(확인함) |
| T25-76·77·78·79·80 | 3483~3600행대 | **무수정.** 패널 id·레이아웃 토큰·브레이크포인트·전이·`about:blank` 만 본다 |
| T25-88 | 3742~3756행 | **무수정.** `.detail-note{…}` 안 `#` 색 리터럴 0건 — 새 규칙도 토큰만 쓴다 |
| T25-89 | 3758~3781행 | **무수정.** 회전 IIFE 를 패널 IIFE 앞에 두므로 검사 범위가 늘지 않는다(GOTCHA 5) |
| T25-93 | 3852~3866행 | **무수정.** `run.is_running` 4건 — 세션 칩 코드 무변경 |
| T25 헤더 문구 | 2345·2349행 | **갱신.** `T25-1~T25-94` → `T25-1~T25-99` |

### 신규 검사 (정방향 + 역방향 쌍) — `test_hub_docs_and_constants()` 말미에 추가

현재 최대 번호는 **T25-94** 이므로 **T25-95** 부터 쓴다.

| # | 대상 | 정방향(있어야) | 역방향(없어야) |
|---|------|----------------|----------------|
| **T25-95** | PV1 패널 표면 | `.detail-panel{` 규칙 범위 안에 `background:var(--bg)` | 같은 범위에 `background:var(--surface)` · `.detail-head{` 규칙에 `background`·`border` 선언 |
| **T25-96** | PV3·PV4 헤더 높이 고정 | `class="detail-note"` 줄에 `data-tooltip=` · `.detail-note{` 규칙에 `white-space:nowrap`·`visibility:hidden`·`line-height:16px` · `detail-note-visible` | `id="dzh-detail-note"` 줄에 ` hidden` · 파일 전체에 `panelNoteEl.hidden` · `DETAIL_NOTE_TEXT` |
| **T25-97** | PV6~PV8 회전 | `@keyframes dzh-refresh-spin` · `.refresh-btn.refresh-spinning svg{animation:` · `prefers-reduced-motion` 블록 안의 `refresh-spinning` 이 **소스 순서상 뒤** · `animationend` | 회전 IIFE 범위(`var REFRESH_SPIN_CLASS` ~ 그 IIFE 끝)에 `setTimeout(` 0건 |
| **T25-98** | PV9~PV12 아이콘 | `class="theme-icon-moon"` · `class="theme-icon-sun"` · `DRAG_HANDLE_ICON_SVG` · `.card-drag-handle svg{` · `.detail-close svg{` · 머리 주석의 `lucide` | `>☾<` · `☀` · `>≡<` · `>»<` · `THEME_GLYPH` · `cdn.` · `unpkg` · `createIcons` |
| **T25-99** | 문서·주석 정합 | `hub/README.md` 에 `아이콘` 서술 · 머리 주석에 `detail-note-visible` | `hub/README.md` 에 `☾`·`≡` 0건 · 머리 주석에 `hidden·textContent 만 바뀐다` 0건 |

> T25-97 의 순서 비교 구현(선례: T25-79·T25-91 의 줄 번호 비교):
> ```bash
> spin_rule_line=$(grep -n '\.refresh-btn\.refresh-spinning svg{animation:' "$hub_template_file" | head -1 | cut -d: -f1)
> spin_reduce_line=$(grep -n 'prefers-reduced-motion' "$hub_template_file" | while IFS=: read -r n _; do
>     sed -n "${n}p" "$hub_template_file" | grep -q 'refresh-spinning' && echo "$n"; done | head -1)
> [[ -n "$spin_rule_line" && -n "$spin_reduce_line" && "$spin_reduce_line" -gt "$spin_rule_line" ]] || record_failure …
> ```
> (무효화를 한 줄짜리 `@media` 로 쓰는 것이 이 검사를 단순하게 만든다 — 위 CSS 예시가 그렇게 돼 있다.)

### 뮤테이션 검증 (구현 중 1회 — 검사가 **실제로 실패할 수 있는지** 확인)

이 저장소가 실측한 실패 유형이다: "검증을 추가할 때 그 검증이 실제 환경에서 성립하는지 먼저
확인한다"(전역 지침 「실패 사례」). 각 변형 후 `bash tests/run.sh` 가 **빨간불**인지 확인하고 되돌린다.

| 검사 | 변형 | 기대 |
|------|------|------|
| T25-95 | `.detail-panel` 의 `background:var(--bg)` → `var(--surface)` | 실패 |
| T25-96 | 마크업에 `hidden` 을 되살린다 | 실패 |
| T25-96(역) | `.detail-note` 에서 `white-space:nowrap` 제거 | 실패 |
| T25-97 | 저감 무효화 `@media` 줄을 회전 규칙 **앞으로** 옮긴다 | 실패 |
| T25-97(역) | `animationend` 해제를 `setTimeout(600, …)` 로 되돌린다 | 실패 |
| T25-98 | 테마 버튼에 `☾` 한 글자를 되살린다 | 실패 |
| T25-99 | `hub/README.md` 에 `≡` 한 글자를 되살린다 | 실패 |

### 수동 확인 (자동화 불가 — 브라우저 실측)

| # | 절차 | 기대 |
|---|------|------|
| **M1** | 1440px 라이트 테마에서 티어 1 카드 클릭 | 제목이 `--bg` 위에 서고, 그 아래 대시보드 카드가 **테두리·그림자를 가진 떠 있는 카드**로 읽힌다. 헤드와 카드가 맞붙지 않는다 |
| **M2** | 같은 절차를 **다크 테마**로 반복 | 헤드(`#0E1621`)와 카드(`#16202D`)가 구분된다. 구분이 미흡하면 리스크 P-1 의 후퇴 경로를 적용하고 그 결과를 이 문서에 실측 기록으로 덧붙인다 |
| **M3** | 밀어내기 모드에서 허브 본문과 패널의 경계 | 좌측 테두리 + 그림자로 두 면이 갈린다(같은 `--bg` 다). 라이트에서도 경계가 사라져 보이지 않는다 |
| **M4** | 안내 줄 **있는** 프로젝트 ↔ **없는** 프로젝트를 번갈아 클릭 | 대시보드 시작 y 좌표가 **고정**. 개발자 도구에서 `.detail-head` + `.detail-note` 높이 합이 두 경우 같음을 확인 |
| **M5** | 320px 폭으로 줄이고 안내 줄 있는 프로젝트를 연다 | 안내가 **한 줄**로 잘리고 말줄임표가 보인다. 헤더 높이는 그대로 |
| **M6** | 잘린 안내에 마우스를 올린다 | 전역 툴팁이 전문을 보여준다 |
| **M7** | 새로고침을 1회 클릭 | 아이콘이 한 바퀴 돌고 멈춘다. 개발자 도구에서 `refresh-spinning` 클래스가 종료 후 **사라져 있다** |
| **M8** | 새로고침을 빠르게 5회 연타 | 매번 처음부터 다시 돈다(중간에 멈추거나 누적 회전하지 않는다) |
| **M9** | OS "동작 줄이기" 켜고 M7 반복 | 회전 없음. 갱신은 정상(툴팁 문구의 "n초 전 확인"이 갱신된다) |
| **M10** | 라이트에서 테마 버튼 확인 → 클릭 → 다크에서 확인 | moon → sun 으로 바뀐다. 툴팁·`aria-label` 도 함께 바뀐다 |
| **M11** | 카드 왼쪽 위 핸들 확인 + 드래그로 순서 변경 | grip 아이콘이 보이고, 드래그·저장은 이전과 동일하게 동작한다 |
| **M12** | 닫기 버튼 확인 + 클릭 + ESC | 아이콘이 오른쪽 방향을 가리키고, 두 경로 모두 이전과 같이 닫힌다(슬라이드아웃 유지) |
| **M13** | 키보드만으로 Tab 순회 | 새로고침 → 테마 → 카드 순. 드래그 핸들은 여전히 Tab 대상이 아니다(`<span>`·`aria-hidden`) |

---

## 리스크와 완화책

| # | 리스크 | 완화 |
|---|--------|------|
| **P-1** | **밀어내기 모드에서 허브 본문과 패널이 같은 `--bg` 라 경계가 약해 보인다** | 좌측 테두리(`--line`) + 48px 그림자가 남는다. **후퇴 경로가 1줄이다**: 그림자 알파 `.28` → `.38`(중성 검정 리터럴이라 T25-29 의 범주 색 금지에 걸리지 않는다 — 결정 MD2 의 근거 승계). 그래도 부족하면 `.detail-head`·`.detail-note` 만 `--bg` 로 두고 패널은 `--surface` 로 되돌리는 **안 C**(결정 PV1 표)가 다음 후퇴 지점이며, 그 대가는 `about:blank` 구간의 색 불일치다 |
| **P-2** | **다크에서 `--bg`(#0E1621)와 `--surface`(#16202D)의 명도차가 작아 카드가 안 떠 보인다** | 카드에는 `--shadow`(다크: `rgba(0,0,0,.45)`)와 1px `--line`(#26364A) 테두리가 있다 — 색이 아니라 **형태 채널**로 이미 갈린다. 수동 M2 가 실측 게이트이며, 미달 시 P-1 의 후퇴 경로를 쓴다. **미리 예비안을 넣지 않는다** |
| **P-3** | **안내 줄이 잘려 사용자가 이유를 못 읽는다** | 툴팁이 전문을 준다(PV4). 잘림은 550px 고정폭에서는 드물다(문구 47자 × 11.5px ≈ 470px < 518px). 자주 잘린다는 보고가 오면 **문구를 줄인다**(마크업 한 곳) — 승인 항목 4 |
| **P-4** | **lucide path 좌표를 잘못 옮겨 적어 아이콘이 뭉갠다** | 구현 전 lucide.dev 대조 1회(PV9 의 구현자 주의) + 수동 M10~M12 육안 확인. 실패해도 **표시만** 깨지고 동작은 그대로다 |
| **P-5** | **저감 모드에서 `refresh-spinning` 클래스가 남는다** | 의도된 절충(PV7·GOTCHA 4). 관측 가능한 영향 0. 타이머로 "고치면" G6 이 깨진다 |
| **P-6** | **SP11 의 근거 문단이 두 번째로 사실과 어긋난 채 남는다** | 288~296행 주석의 「iframe 첫 카드 테두리가 구분선을 대신한다」 문단을 **PV1 의 근거로 교체**한다(영향 범위 ④). 원문을 지우지 않는 관례는 **PRP 문서**에 적용되는 것이고, 코드 주석은 사실과 어긋나면 고친다 |

---

## YAGNI 보류 (지금 만들지 않는다 + 재방문 트리거)

| # | 보류 항목 | 이유 | 재방문 트리거 |
|---|-----------|------|---------------|
| 1 | **SVG 스프라이트(`<symbol>`+`<use>`)** | 아이콘 4종, 각 1~2회 사용. 간접층이 얻는 것은 몇백 바이트뿐이고 `file://`·`data:` 환경에서 참조 규칙을 하나 더 짊어진다 | 아이콘이 8종을 넘거나, 한 아이콘이 카드마다 3회 이상 반복될 때 |
| 2 | **회전을 폴링 진행 상태와 연동** | 상태 기계가 생기고 로컬 응답이 빨라 깜빡임이 된다(PV6) | "새로고침이 됐는지 모르겠다"가 **회전 도입 이후에도** 보고될 때 |
| 3 | **헤더 영역을 sticky 로 고정** | iframe 은 자기 문서를 스크롤하므로 패널 헤드는 애초에 스크롤되지 않는다. 대상이 없다 | 패널이 iframe 이 아닌 직접 렌더로 바뀔 때 |
| 4 | **안내 줄 2줄 허용 + 헤더 최대 높이** | "최대 높이"는 고정이 아니다. 폭에 의존하는 순간 R2 가 부분적으로 되살아난다(PV3 안 B) | 안내 문구가 두 종류 이상으로 늘어 한 줄에 담기 어려워질 때 |
| 5 | **테마 아이콘에 전환 애니메이션(회전·페이드)** | 요구에 없다. 저감 모드 무효화·타이밍 상수가 또 하나 늘어난다 | 사용자가 명시 요구할 때 |

---

## 검토했으나 채택하지 않은 대안 (요약)

| 대안 | 기각 사유 |
|------|-----------|
| `.detail-head` 에 `border-bottom` 복원 | SP11 을 번복하고 G2·T25-85 를 깬다. 흰 위에 흰이라는 **원인**을 남긴 채 선만 하나 더 그린다(PV1 안 A) |
| 헤드에 `--soft` 밴드 | 60px 안에 3색이 쌓인다. 다크에서 세 값의 명도차가 작아 얼룩으로 보인다(PV1 안 B) |
| 헤드·안내 줄만 `--bg`, 패널은 `--surface` 유지 | `about:blank` 구간에 프레임 영역이 `--surface` 로 보인다 — 다크에서 흰 번쩍임의 축소판(PV1 안 C). **단, P-1 의 2차 후퇴 지점으로 남겨 둔다** |
| 안내 줄을 `hidden` 유지 + 래퍼에 `min-height` | 높이는 고정되나 제목의 수직 정렬이 프로젝트마다 달라지고, 두 줄로 접히면 다시 깨진다(PV3 안 A·B) |
| 회전을 Web Animations API(`element.animate()`)로 | 동작은 같지만 **저감 모드 판정이 CSS 에서 JS 로 옮겨간다** — 이 파일의 모션 정책은 전부 `@media (prefers-reduced-motion)` 한 곳에 모여 있다(124행·280~287행). 정책을 두 언어로 쪼개는 대가가 얻는 것보다 크다 |
| `lucide` CDN 스크립트 + `createIcons()` | `file://` 요구 위반 · 외부 오리진 요청 · 첫 페인트 흔들림 · 버전 고정 주체 없음(PV9) |
| 테마 아이콘을 `innerHTML` 로 교체 | 정적 노드를 재생성한다. 불변식 H1⁗ 의 원칙과 어긋나고 JS 안에 마크업 문자열 두 벌이 산다(PV10 안 A) |

---

## 구현 마일스톤

| # | 내용 | 검증 |
|---|------|------|
| 1 | CSS: 패널 표면(PV1) + 헤더 패딩(PV2) + 안내 줄 규칙(PV3) 교체, 주석 개정 | 수동 M1~M6 |
| 2 | 마크업 + 패널 IIFE 안내 줄 토글 교체, 머리 주석 41~44행 개정(PV5) | 수동 M4·M5, T25-96 |
| 3 | 회전 CSS 3줄 + 회전 IIFE 신설(PV6~PV8) | 수동 M7~M9, T25-97 |
| 4 | 아이콘 4곳 교체(PV9~PV13) + `THEME_GLYPH` 폐기 + 고아 글꼴 선언 제거 | 수동 M10~M13, T25-98 |
| 5 | `tests/run.sh` 개정 2건 + 신규 5건 + 뮤테이션 7건 | `bash tests/run.sh` 전 항목 통과 |
| 6 | `hub/README.md` 2문장 갱신 | T25-99 통과 |

---

## 승인 요청 항목

> 아래 5건은 취향·트레이드오프가 갈리는 지점이다. **각 항목의 권고안대로 진행해도 되는지**
> 확인해 주면 그대로 구현에 들어간다.

### 승인 항목 1 — 패널 표면을 `--surface` → `--bg` 로 바꾼다 (결정 PV1)
**권고: 채택.** 헤드가 "페이지 머리", 대시보드가 "떠 있는 카드"가 되어 대시보드 단독 화면과
같은 위계가 된다. 구분선은 되살리지 않으므로 SP11 은 유지된다.
**대가:** 밀어내기 모드에서 허브 본문과 패널의 면색이 같아지고, 경계는 좌측 테두리와 그림자만
남는다(리스크 P-1, 후퇴 1줄).
**대안:** 헤드·안내 줄만 `--bg` 로 칠하고 패널은 `--surface` 유지 — `about:blank` 구간에서
프레임이 잠깐 다른 색이 된다.

### 승인 항목 2 — 안내 줄 자리를 **항상 예약**하고 한 줄로 자른다 (결정 PV3·PV4)
**권고: 채택.** 안내가 없는 프로젝트에서는 그 자리가 헤드-카드 여백을 겸한다(PV2).
**대가:** 안내가 긴 문구인데 좁은 화면에서는 잘린다(전문은 툴팁).
**대안:** 자르지 않고 두 줄까지 허용 + 헤더에 최대 높이 — 폭에 따라 R2 가 부분적으로 되살아난다.

### 승인 항목 3 — 닫기 아이콘: **`chevrons-right`**(권고) vs **`x`**(요구서 예시) (결정 PV12)
**권고: `chevrons-right`.** 결정 SP11 이 `»` 를 고른 이유("창을 없앤다"가 아니라 "오른쪽으로
밀어 보낸다")를 그대로 유지하면서 아이콘 통일 요구를 만족한다.
**대안:** `x` — 보편적이지만 SP11 을 번복하는 결정이 되며, 그 경우 이 문서에 번복을 명시하고
`.detail-close` 주석의 근거 문단도 함께 고친다.

### 승인 항목 4 — 안내 문구는 **지금 그대로** 둔다 (결정 PV3)
**권고: 유지.** 550px 고정폭에서는 대체로 한 줄에 들어간다(약 470px).
**대안:** 짧게 고쳐 잘림 확률을 더 낮춘다 — 예: "이전 작업의 대시보드입니다 — 현재 세션 이후
갱신되지 않았습니다."(약 35자). 채택 시 마크업 두 곳(텍스트·`data-tooltip`)을 같이 고친다.

### 승인 항목 5 — 회전 무효화를 **회전 규칙 바로 뒤 한 줄짜리 `@media`** 로 둔다 (결정 PV8)
**권고: 채택.** `.card.card-working` 의 무효화(124행)가 이미 같은 자리·같은 형태다 — 규칙과
무효화가 붙어 있어야 한 쪽만 고치는 실수가 눈에 띈다.
**대안:** 패널용 저감 블록(280~287행)에 셀렉터를 추가 — 그 블록은 `transition:none` 전용이라
`animation:none` 규칙을 넣으려면 블록 안에 규칙을 하나 더 만들어야 하고, 그러면 T25-79 가
검사하는 소스 순서 관계에 무관한 셀렉터가 섞인다.
