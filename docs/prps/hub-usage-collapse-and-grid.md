# 허브 — 사용량 패널 접기/우하단 이동 + 프로젝트 카드 반응형 그리드 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_template.html` (통합 허브 대시보드 화면) |
| 브랜치 | `feature/hub-dashboard` (HEAD `b81ba14`) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md) → [`hub-theme-and-usage-panel.md`](./hub-theme-and-usage-panel.md) → **이 문서** |
| 워크플로우 경로 | **전체 경로** (공개 계약 변경 없음이나 3개 이상 파일 + 이전 결정 U5 폐기) |
| 규모 | Small–Medium — 신규 0개 / 수정 4개 파일, 템플릿 증분 약 45줄(CSS 20 · DOM 8 · JS 17) |
| 새 외부 의존성 | **없음** (바닐라 CSS/JS · 빌드 단계 없음 · 프레임워크/CDN 없음) |
| **Python 변경** | **없음** — 근거는 「영향 범위 · 미영향」 |
| **승인 상태** | **승인됨 (2026-08-11)** — 아래 확정 사항 참조 |

## 승인 확정 사항 (2026-08-11)

「사용자 승인이 필요한 미결 선택지」 3건이 모두 확정됐다. 구현은 이 값을 따른다.

| 항목 | 확정 | 비고 |
|------|------|------|
| 1. 컨테이너 최대 폭 | **A. `max-width:1440px`** (최대 4열) | 열 전환점 684 / 1016 / 1348px → 2 / 3 / 4열. 메인 세션이 검산해 일치 확인 |
| 2. 접힘 요약 | **B. 세션 + 주간 병기** | `Claude 사용 한도  세션 43% · 주간 71% ▸`. 접근성 낭독 문구도 이 안을 따른다 |
| 3. 구 PRP 의 U5 | **삭제하지 않고 "대체됨" 표기만 추가** | 판단 근거를 남긴다 |

---

## 요구사항 요약

허브 대시보드는 지금 (1) 사용량 플로팅 패널이 화면 **하단 중앙**에 고정돼 항상 같은 크기로
떠 있고, (2) 프로젝트 카드를 `max-width:960px` 안에서 **한 줄에 하나씩** 세로로 쌓는다.
프로젝트가 늘수록 스크롤이 길어지고, 넓은 화면에서 우측 공간이 통째로 놀며, 사용량 패널은
끄는 것(`show_usage_panel:false`) 말고는 줄일 방법이 없다. 이 PRP 는 두 가지를 바꾼다.
**(1)** 사용량 패널을 **오른쪽 아래**로 옮기고 제목 줄을 클릭/키보드로 눌러 **접고 펼칠 수**
있게 한다 — 접으면 한 줄 요약 알약(pill), 펼치면 지금의 막대 2개 상세. 선택은 새로고침과
5초 폴링 재렌더를 모두 견딘다. **(2)** 프로젝트 목록을 **뷰포트 폭에 따라 1~4열로 자동
전환되는 그리드**로 바꾼다.

### 사용자 스토리

> 여러 프로젝트를 동시에 돌리는 개발자로서, 넓은 모니터에서는 프로젝트를 한눈에 격자로 보고,
> 사용량 패널은 필요할 때만 펼쳐 보고 평소에는 작게 접어 두고 싶다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | 뷰포트 390 / 768 / 1024 / 1440 px 에서 카드 열 수가 각각 1 / 2 / 3 / 4 | 수동 M1 |
| S2 | 같은 행의 카드가 세션 목록 유무와 무관하게 **자기 높이만큼만** 차지한다 | 수동 M3 |
| S3 | 접은 뒤 60초(재렌더 2회) 이상 방치해도 접힌 채로 남는다 | 수동 M5 |
| S4 | 접은 뒤 새로고침해도 접힌 채로 열린다(http 오리진) | 수동 M6 |
| S5 | 접힘·펼침 **양쪽 모두** 페이지 최하단에서 마지막 카드와 푸터가 패널에 가리지 않는다 | 수동 M8 |
| S6 | Tab 으로 토글에 도달하고 Enter/Space 로 접힌다. 포커스 링이 보인다 | 수동 M10 |
| S7 | `bash tests/run.sh` 전체 통과(T25-32~36 신규 포함) | 자동 |

---

## 영향 범위

### 수정 파일 (4개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_template.html` | CSS 규칙 9개 추가·5개 수정, `<aside>` 내부 마크업 4줄, IIFE 함수 5개 추가·1개 수정, 상단 주석 블록의 불변식 참조 갱신 | 이 변경의 거의 전부 |
| `tests/run.sh` | `test_hub_docs_and_constants` 에 T25-32~36 추가, `test_desc` 문자열을 `(T25-1~T25-36)` 으로 갱신 | 새 불변식의 grep 회귀 방지 |
| `hub/README.md` | 「사용량 패널」 절 첫 문장(하단 → 우하단) + 접기 동작 1행, 「화면 배치」 3행 신설 | T25-36 및 문서 정합 |
| `docs/prps/hub-theme-and-usage-panel.md` | **결정 U5 대체 표기 3곳**, 불변식 H1 → H1′ 개정 표기 1곳 | 두 설계 문서가 모순된 채 남지 않게 (아래 「U5 대체」) |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_model.py`·`hub_parse.py`·`hub_usage.py` | **순수 레이어. 이 변경은 Python 을 전혀 건드리지 않는다.** `#dzh-data` JSON 계약(`HubSnapshot`)이 그대로다 — 접힘 상태는 서버가 아니라 브라우저 `localStorage` 에 산다. 따라서 `snapshot_content_key`(`hub_model.py:548`)도, `render_hub_html`(`:556`)의 마커 치환도 무변경이고, `hub_server.py:82` 의 "내용이 같으면 다시 쓰지 않는다" 게이트도 영향이 없다 |
| `hub/bin/hub_collect.py`·`hub.py`·`hub_server.py`·`hub_daemon.py`·`hub_hook.py`·`hub_settings.py` | 위와 같은 이유. 템플릿은 이 모듈들에게 **불투명한 문자열**이다 |
| `hub/install.sh` | 배포 파일 수 무변경(10개) → `HUB_FILE_COUNT` 그대로. T25-1 자동 대조 통과 |
| `commands/hub.md` | 이 문서는 **서브커맨드 호출 규약과 `/hub status` 필드**만 설명한다(확인함: 화면 레이아웃에 대한 서술이 한 줄도 없다). 사용량 관련 서술도 `usage_panel_enabled`·`usage_sample_age_ms` 진단 필드뿐이라 이번 변경과 접점이 없다 → **수정하지 않는다** |
| `tests/hub/*.py`, `tests/hub/fixtures/*.html` | 픽스처는 전부 `/dashboard` 생성물이고 `test_hub_parse.py` 만 읽는다. `WriteHubHtmlAtomicityTest` 는 `id="dzh-data">` 이후 첫 `</script>` 를 잘라 JSON 을 파싱하는데, 이번에 추가되는 마크업은 전부 그 블록 **앞**(`<aside>` 내부)이다 → **깨지지 않는다** |
| `commands/dashboard.md` | `/dashboard` 는 별도 자산. 템플릿을 공유하지 않는다 |

---

## 확정된 전제 (재론하지 않는다)

1. **단일 정적 HTML, 빌드 단계 없음.** 프레임워크·CDN·전처리기 금지. CSS Grid 와 바닐라 JS 로만 푼다.
2. **접힘은 순수한 화면 상태다.** 서버에 저장하지 않는다 — 허브 서버는 **읽기 전용 2경로
   화이트리스트**가 설계 정본이며(`hub_server.py:21`), 쓰기 엔드포인트를 만들 이유가 없다.
3. **사용량 패널의 데이터·표시 규칙(U1~U4)은 그대로다.** 데이터가 없거나 만료면 패널 자체가
   없다. 이 PRP 는 **있는 패널을 어떻게 배치·접는가**만 다룬다.
4. **색각 안전 팔레트(Okabe–Ito 파랑–주황 축)를 유지한다.** 새 색 리터럴을 도입하지 않고
   기존 토큰(`var(--accent)` 등)만 참조한다 → 라이트/다크가 자동으로 성립하고 T25-29 도 통과한다.

---

## 변경 후 DOM 구조

```html
<body>
<button id="dzh-theme-toggle" class="theme-toggle" type="button">테마: 시스템</button>   ← 무변경
<div class="wrap">                                          ← max-width 960 → 1440
  <h1>통합 허브 대시보드</h1>
  <div class="sub">…</div>
  <div id="dzh-app">…</div>                                 ← display:grid (자식은 폴링이 교체)
  <div class="foot" id="dzh-collected-at"></div>
</div>

<aside id="dzh-usage" class="usage" hidden>                  ← 정적. 위치만 우하단으로
  <button id="dzh-usage-toggle" class="usage-toggle" type="button"
          aria-expanded="true" aria-controls="dzh-usage-body">   ← ★신규 · 정적 · 절대 교체 금지
    <span class="usage-title">Claude 사용 한도</span>
    <span id="dzh-usage-summary" class="usage-summary"></span>   ← ★신규 · textContent 만 갱신
    <span class="usage-caret" aria-hidden="true"></span>         ← ★신규 · 글리프는 CSS ::before
  </button>
  <div id="dzh-usage-body" class="usage-body"></div>             ← ★신규 · innerHTML 갱신 대상
</aside>

<script type="application/json" id="dzh-data">{}</script>    ← 무변경 (치환 마커)
```

### 화면 (펼침 / 접힘)

```
펼침                                     접힘
┌──────────────────────────────┐         ┌───────────────────────────────────┐
│ Claude 사용 한도          ▾ │         │ Claude 사용 한도  세션 43%·주간 71% ▸│
│ 세션 (5시간)           43%   │         └───────────────────────────────────┘
│ ▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░  │              폭 auto(≈260px) · 높이 ≈40px
│ 주간 (7일)             71%   │
│ ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░  │
│ 마지막 갱신 5분 전 ·약 15분  │
└──────────────────────────────┘
  폭 420px · 높이 ≈152px                       둘 다 화면 오른쪽 아래 고정
```

---

## 상태 모델과 저장 위치 (제약 C1 의 답)

### 문제

`render()` 는 `setInterval(render, TICK_MS=30000)` 로 30초마다, 그리고 폴링이 HTML 문자열
변화를 감지할 때마다 불린다. 현재 `renderUsagePanel()` 은 `usageEl.innerHTML` 에 **패널 전체를
통째로 대입**한다. 접기 버튼을 그 안에 두면 **30초마다 노드가 파괴되어** 접힘 상태와
포커스가 초기화된다.

### 해결 — 정적 껍데기 / 파생 알맹이 분리 + 3중 상태 배치

| 층 | 저장 위치 | 수명 | 역할 |
|----|-----------|------|------|
| 런타임 진실 | IIFE 모듈 스코프 변수 `isUsageCollapsed` (boolean) | 페이지 로드 | 렌더·토글이 참조하는 단일 소스 |
| DOM 반영 | `#dzh-usage` 의 `usage-collapsed` **클래스** + 버튼의 `aria-expanded` | 재렌더 후 재적용 | CSS 와 접근성 트리 |
| 영속 | `localStorage['dzh-usage-collapsed']` = `'1'` (접힘) / **키 없음** (펼침) | 오리진별 영구 | 새로고침 지속 |

**재렌더 후 복원 경로**: `renderUsagePanel()` 은 이제 `#dzh-usage-body.innerHTML` 과
`#dzh-usage-summary.textContent` **두 곳만** 쓰고, 마지막에 `applyUsageCollapsedState()` 를
호출해 클래스·`aria-expanded`·하단 여백을 다시 적용한다. `#dzh-usage-toggle` 노드는
**한 번도 교체되지 않으므로** 리스너도 포커스도 살아남는다.

> **결정 C1 — 접기 버튼을 `#dzh-usage` **안**에 두되, 재렌더 대상에서 제외한다.**
> 상태를 innerHTML 바깥으로 빼는 방법은 두 가지였다. (a) 버튼을 `<aside>` 밖(예: `<body>`
> 직속)에 별도 부유 요소로 두기 — 위치 계산이 두 요소로 쪼개져 좌표 동기화 문제가 생긴다.
> (b) 컨테이너 안에서 **정적 영역과 파생 영역을 나누기** — 채택. 비용은 id 3개와 targeted
> write 2회뿐이고, 패널이 하나의 상자로 움직이는 성질이 유지된다.

### 불변식 M2 의 개정 — H1 → H1′

직전 PRP 의 결정 M2 는 "컨테이너는 정적, 내용은 파생"이었고, 여기서 **컨테이너 = `#dzh-usage`
전체**였다. 이번 변경은 그 경계를 한 겹 안으로 옮긴다. **원칙(사용자 상태를 가진 요소를
재렌더 대상 밖에 둔다)은 그대로 유지되고, 경계선만 이동한다.**

> **불변식 H1′.** 허브의 폴링·틱이 **내용을 갱신하는** 요소는 `#dzh-app`,
> `#dzh-collected-at`, `#dzh-usage-body`, `#dzh-usage-summary` **네 개뿐이다.**
> `#dzh-usage` 와 그 안의 `#dzh-usage-toggle` 은 **정적 노드**이며, 재렌더는 이들의
> `class`·`aria-expanded` **속성만** 갱신한다(노드 교체 금지). 테마 토글 버튼은 종전대로
> 이 네 요소 바깥의 정적 마크업이다. **사용자 상태(포커스·접힘·선택)를 가진 요소는 반드시
> 이 네 요소 바깥에 둔다.**

> **개정됨(2026-08-13).** `#dzh-collected-at` 은 좁은 화면에서 우상단 고정 클러스터와
> 겹치는 문제로 제거됐고, 연결 상태 문구는 `#dzh-refresh` 의 `data-tooltip` **속성** 갱신으로
> 대체됐다. 따라서 현행 갱신 대상은 **요소 3개(`#dzh-app`·`#dzh-usage-body`·
> `#dzh-usage-summary`) + `#dzh-refresh` 의 `data-tooltip`·`class` 속성**이다 — "내용은 파생,
> 사용자 상태를 가진 노드는 교체 금지" 원칙은 그대로다. 정본은 `hub_template.html` 상단
> 주석 블록.

> **재개정(H1″).** 정적 노드 목록에 모달·라이브 영역이 추가되고, "#dzh-app 의 자식
> **순서**는 사용자 상태" 조항과 "드래그 중 재렌더 금지" 조항이 더해졌다. 정본은
> `hub_template.html` 상단 주석 블록 및
> [hub-card-interactions-and-usage.md](./hub-card-interactions-and-usage.md).

`hub_template.html` 상단 주석 블록(현행 7~16행)의 "폴링이 내용을 갱신하는 요소는 … 세 개뿐"
문장을 위 H1′ 로 교체하고, 참조 문서에 이 PRP 를 추가한다.

### 결정 C2 — 저장 규약은 "키 없음 = 기본값"

`localStorage.setItem('dzh-usage-collapsed','1')` / 펼치면 `removeItem`. 별도의 `'expanded'`
값을 쓰지 않는다 — 결정 T2 가 테마에서 이미 쓴 규약("키가 없으면 시스템")과 같은 모양이라
읽는 쪽 검증이 `=== '1'` 하나로 끝난다. **기본값은 펼침**이다(기존 사용자가 보던 화면이
그대로 유지된다).

### 결정 C3 — `localStorage` 실패는 흡수하고 이번 로드 동안만 유효 (제약 C7)

읽기·쓰기 **양쪽 모두** `try/catch` 로 감싼다. 근거는 결정 T3 와 동일하다 — 허브는 서버가
꺼져 있으면 `file://` 로도 열리고(`hub.py:101`), 일부 브라우저 설정에서 `file://` 의
`localStorage` 접근은 `SecurityError` 를 던진다. 예외가 새면 IIFE 전체가 죽어 **페이지가
아예 안 그려진다.**

- 읽기 실패 → `false`(펼침)로 시작.
- 쓰기 실패 → **이번 페이지 로드 동안만** 토글이 동작하고 새로고침하면 펼침으로 돌아온다.
  사용자에게 오류를 띄우지 않는다(테마 토글과 동일한 처리).
- **테마와 달리 `<head>` 인라인 스크립트가 필요 없다.** 패널은 `hidden` 으로 시작해 JS 가
  데이터를 확인한 뒤에야 보이므로, 접힘 상태가 늦게 적용되어 생기는 FOUC 자체가 없다.

---

## 변경 후 CSS

### 그리드 (요구 2)

```css
.wrap{max-width:1440px;margin:32px auto;padding:0 16px}                    /* 960 → 1440 */
#dzh-app{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;align-items:start}
#dzh-app>.empty,#dzh-app>.unresolved,#dzh-app>.warnings{grid-column:1/-1}
.card{…;box-shadow:var(--shadow)}                                          /* margin-bottom:12px 삭제 */
.tier1-active{font-size:12px;color:var(--head);margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
```

### 패널 (요구 1)

```css
body.has-usage .wrap{padding-bottom:var(--usage-clearance,184px)}          /* 132px 상수 폐기 */
.usage{position:fixed;right:16px;bottom:16px;width:min(420px,calc(100vw - 32px));z-index:20;
       background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 18px;box-shadow:var(--shadow)}
.usage.usage-collapsed{width:auto;max-width:calc(100vw - 32px);padding:10px 14px}
.usage-toggle{display:flex;align-items:center;gap:8px;width:100%;padding:0;border:0;background:none;
              font:inherit;color:inherit;text-align:left;cursor:pointer}
.usage-toggle:hover .usage-title{color:var(--accent-ink)}
.usage-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.usage-title{font-size:12.5px;font-weight:800;color:var(--head)}           /* margin-bottom:8px 삭제 */
.usage-summary{font-size:12.5px;font-weight:700;color:var(--accent-ink)}
.usage-caret{margin-left:auto;font-size:10px;color:var(--muted)}
.usage-caret::before{content:"▾"}
.usage.usage-collapsed .usage-caret::before{content:"▸"}
.usage:not(.usage-collapsed) .usage-summary{display:none}
.usage.usage-collapsed .usage-body{display:none}
.usage-body{margin-top:8px}
.usage-body>.usage-row:first-child{margin-top:0}                           /* .usage-title + .usage-row 대체 */
```

> **GOTCHA 1 — `[hidden]` 이 죽는다.** `.usage` 규칙에 **`display` 를 절대 넣지 마라.**
> 현재 `.usage` 에 `display` 가 없기 때문에 UA 스타일시트의 `[hidden]{display:none}` 이 먹고,
> 그래서 `usageEl.hidden = true` 가 동작한다. `display:flex` 등을 추가하면 특이도가 높아져
> **데이터가 없을 때도 빈 패널이 뜬다.** 필요하면 `.usage[hidden]{display:none}` 을 함께 넣는다.
> flex 가 필요한 곳은 자식(`.usage-toggle`)뿐이다.

> **GOTCHA 2 — 사라지는 CSS 규칙 2개.** `.usage-title + .usage-row{margin-top:0}` 는 제목이
> 버튼 안으로 들어가면서 **인접 형제 관계가 끊겨 무효**가 된다(첫 막대 위 간격이 8px 벌어짐).
> `.card{margin-bottom:12px}` 는 그리드 `gap:12px` 와 **겹쳐 24px** 이 되고 `align-items:start`
> 의 행 정렬을 어긋나게 한다. 둘 다 위 스펙대로 대체·삭제한다.

> **GOTCHA 3 — `-webkit-line-clamp` 3종 세트.** `display:-webkit-box`,
> `-webkit-box-orient:vertical`, `overflow:hidden` 이 **모두** 있어야 동작한다. 기존
> `white-space:nowrap;text-overflow:ellipsis` 는 충돌하므로 반드시 제거한다.

---

## 변경 후 JS (인터페이스)

`hub_template.html` 하단 IIFE 안, 사용량 렌더 함수 근처에 배치한다. 기존 파일의 문법
(`var`, 함수 선언, 상수는 대문자 스네이크)을 그대로 따른다.

```js
/* 상수 — 매직 넘버/문자열 금지 규칙 */
var USAGE_COLLAPSE_STORAGE_KEY = 'dzh-usage-collapsed';
var USAGE_COLLAPSED_FLAG = '1';
var USAGE_CLEARANCE_MARGIN_PX = 32;   // 패널 bottom 오프셋 16 + 여유 16

var usageToggleButton = document.getElementById('dzh-usage-toggle');
var usageBodyEl       = document.getElementById('dzh-usage-body');
var usageSummaryEl    = document.getElementById('dzh-usage-summary');
var isUsageCollapsed  = readStoredUsageCollapsed();

function readStoredUsageCollapsed(): boolean
    /** 저장된 접힘 상태를 읽는다. 저장소 접근이 막힌 환경(file:// 등)에서는 펼침으로 본다. */

function persistUsageCollapsed(collapsed: boolean): void
    /** 접힘이면 플래그를 쓰고 펼침이면 키를 지운다. 저장 실패는 무시한다(이번 로드 동안만 유효). */

function usageSummaryText(usage): string
    /** 접힘 상태에 보일 한 줄 요약 문자열. 순수 함수 — DOM 에 닿지 않는다. */
    // 반환 예: '세션 43% · 주간 71%'

function applyUsageClearance(): void
    /** 패널 실측 높이로 본문 하단 여백(--usage-clearance)을 맞춘다. */

function applyUsageCollapsedState(): void
    /** 접힘 상태를 클래스·aria-expanded·하단 여백에 반영한다. 재렌더 후 복원 경로다. */

function renderUsagePanel(usage): void   // 변경
    /** 사용량 패널 내용을 다시 그린다. 컨테이너와 토글 버튼 노드는 건드리지 않는다(H1′). */
```

### `renderUsagePanel` 의 변경 (핵심 diff)

```js
  // 변경 전:  usageEl.innerHTML = '<div class="usage-title">…</div>' + sessionBar + weeklyBar + meta;
  // 변경 후:
  usageSummaryEl.textContent = usageSummaryText(usage);          // ← 속성이 아니라 텍스트 노드
  usageBodyEl.innerHTML = sessionBar + weeklyBar + metaHtml;
  usageEl.hidden = false;
  applyUsageCollapsedState();   // 접힘 상태 + 하단 여백을 매 렌더마다 재적용
```

- **`usageEl.innerHTML` 대입은 완전히 사라진다.** T25-33 이 이 문자열의 **부재**를 grep 으로
  고정한다 — 훗날 누군가 되돌리면 접힘 상태가 30초마다 초기화되는 버그가 그대로 재현되기 때문이다.
- **요약은 `textContent` 로 넣는다.** `escapeHtml` 이 따옴표를 이스케이프하지 않는다는 기존
  결함(별도 티켓)을 우회하는 가장 확실한 방법이고, 이번 변경은 **속성 위치에 데이터 파생값을
  단 하나도 새로 넣지 않는다**(`aria-expanded`·`aria-controls` 는 고정 리터럴).
- 기존 `metaHtml` 의 `title="…escapeHtml(formatTimestamp())…"` 는 **그대로 둔다** — 이번 변경이
  만든 것이 아니고, 손대면 수술 범위를 넘는다(언급만 한다).

### 토글 배선 (한 번만, 정적 노드에)

```js
usageToggleButton.addEventListener('click', function(){
  isUsageCollapsed = !isUsageCollapsed;
  persistUsageCollapsed(isUsageCollapsed);
  applyUsageCollapsedState();
});
```

> **GOTCHA 4 — 측정 순서.** `applyUsageClearance()` 는 `usageEl.offsetHeight` 를 읽는다.
> `hidden` 상태에서는 **0** 이 나온다. 반드시 *내용 채우기 → `hidden=false` → 측정* 순서를
> 지켜야 한다. 위 `renderUsagePanel` 의 호출 순서가 그 순서다.

---

## 설계 결정과 근거

| # | 결정 | 근거 요약 |
|---|------|----------|
| G1 | 그리드 컨테이너는 `#dzh-app` **자기 자신** | 폴링은 이 요소의 **자식만** 교체한다(`app.innerHTML`) — 요소 자체는 살아 있으므로 CSS 가 유지된다. 새 래퍼 div 를 넣으면 렌더 코드를 고쳐야 한다 |
| G2 | `.wrap{max-width:1440px}` | 아래 「열 전환점」 — 4열까지 열되 그 이상은 막는다 · **승인 항목 1** |
| G3 | `repeat(auto-fill,minmax(320px,1fr))` + `gap:12px` | `auto-fit` 은 카드가 1개일 때 빈 트랙을 접어 **1408px 짜리 괴물 카드**를 만든다. `auto-fill` 은 개수와 무관하게 카드 폭이 일정해 예측 가능하다 |
| G4 | `align-items:start` | 제약 C5 — 기본값 `stretch` 는 세션 목록이 없는 카드를 같은 행의 긴 카드 높이까지 늘려 빈 상자로 만든다 |
| G5 | 비-카드 요소는 `grid-column:1/-1` | `.empty`·`.unresolved`·`.warnings` 도 `#dzh-app` 의 **직계 자식**이라 자동으로 그리드 아이템이 된다. 그냥 두면 "불러오는 중…"이 320px 칸에 갇히고 경고가 열 하나에 끼인다 |
| G6 | `.tier1-active` 를 1줄 말줄임 → **2줄 클램프** | 제약 C5. 960px 카드에서 약 74자 보이던 활성 단계가 343px 열에서 **약 25자**로 줄어 핵심 정보가 잘린다. 2줄이면 약 50자를 회복하고 높이 증가는 최대 19px 로 묶인다. **내 변경이 만든 문제만 고친다** |
| C1 | 정적 버튼 + 파생 본문 분리 (H1′) | 위 「상태 모델」. 결정 U5 를 대체한다 |
| C2 | `localStorage` 키 부재 = 펼침(기본값) | 결정 T2 의 규약 재사용 — 검증이 `=== '1'` 하나 |
| C3 | 읽기·쓰기 모두 `try/catch` | 결정 T3 와 동일 근거(`file://` `SecurityError` 로 페이지 전체가 죽는 것을 막는다) |
| C4 | `<button>` + `aria-expanded` + `aria-controls` | 제약 C8. `<details>/<summary>` 기각 근거는 「대안」 3 |
| C5 | 접힘 요약 = **세션·주간 두 숫자** | 제약 C9 · **승인 항목 2** (후보 3개를 아래 제시) |
| C6 | 접힘 시 제목을 **유지**한다 | 레이블 없는 부유 알약("43% · 71%")은 그것을 접은 본인 말고는 해독 불가고, 스크린리더의 접근성 이름도 무의미해진다. 화면 절약의 실체는 **높이 152→40px(-74%)** 이지 폭이 아니다 |
| L1 | `right:16px;bottom:16px` (`left/transform` 제거) | 요구 1. `.theme-toggle` 이 `top:16px;right:16px` 라 **같은 16px 격자에 수직 대칭**으로 놓인다 |
| L2 | 접힘 시 `width:auto` | 고정 420px 을 유지하면 접힘이 "얇고 긴 띠"가 되어 "작게"라는 요구를 만족하지 못한다 |
| L3 | 하단 여백을 **실측값**으로 (`--usage-clearance`) | 제약 C4. 아래 별도 절 |
| Z1 | **z-index 를 바꾸지 않는다** | 제약 C6. 아래 별도 절 |
| — | 디자인 패턴 도입 없음 | 함수 5개 + CSS 규칙 몇 개다. 상태 기계도, 스토어 추상화도, 애니메이션 라이브러리도 도입할 근거가 없다(YAGNI) |

### 결정 G2 — 컨테이너 폭 1440px 과 열 전환점 (제약 C3)

`minmax(320px,1fr)` + `gap:12px` + `.wrap` 좌우 패딩 16px 기준. 가용폭
`W = min(뷰포트, 1440) - 32`, 열 수 `n = floor((W + 12) / 332)`.

| 뷰포트 폭 | 열 수 | 열 폭 | 대표 기기 |
|-----------|-------|-------|-----------|
| ≤ 683px | 1 | 뷰포트 - 32 | 모든 휴대폰(390), 좁은 창 |
| 684 ~ 1015px | 2 | 326 ~ 486px | 아이패드 세로(768) |
| 1016 ~ 1347px | 3 | 320 ~ 431px | 아이패드 가로(1024), 13" 반쪽 창 |
| ≥ 1348px | **4 (상한)** | 320 ~ **343px** | 13"~16" 노트북(1440~1728), 27"(2560) |

> **개정됨.** 열 수 상한이 4 → **3** 으로 제한됐다(결정 W1,
> [`hub-card-cleanup-and-usage-source.md`](./hub-card-cleanup-and-usage-source.md)). 1·2열
> 임계값(683/1015px)은 불변.

- **왜 최소폭 320px 인가**: 배지 3개(`티어 N`·상태·경과)가 붙는 `.project-head` 는
  `flex-wrap:wrap` 이라 좁아지면 `.last-activity` 가 자기 줄로 내려간다. 320px 은 한국어
  프로젝트명 약 20자 + 배지 2개가 한 줄에 들어가는 최소치다. 그 아래로 내리면 카드가
  세로로 길어져 그리드의 이득이 사라진다.
- **왜 1440px 인가**: 1440 을 넘기면(예: `max-width:none`) 2560px 모니터에서 **7열**이 되고
  열 폭은 348px 로 같지만 **좌우 눈 이동이 2.3배**가 되며, 짧은 제목·부제·푸터가 넓은 벌판에
  홀로 남아 페이지 인상이 무너진다. 1440 은 노트북 논리 해상도의 사실상 하한(13" MacBook Air)
  이라 **"노트북에서 4열, 그보다 큰 화면에서도 4열"** 이라는 예측 가능한 결과를 준다.
- **읽기 행장(line length) 은 상한 인상의 피해자가 아니다** — 본문은 전부 카드 **안**에
  있고 카드 폭은 320~486px 로 묶여 있다. 넓어지는 것은 `h1`·`.sub`·`.foot` 뿐이며 모두 한 줄
  이하의 짧은 텍스트다. 이것이 max-width 를 올려도 되는 진짜 이유다.

### 결정 L3 — 하단 여백을 실측한다 (제약 C4)

현행 `body.has-usage .wrap{padding-bottom:132px}` 은 **하단 중앙** 패널을 피하려고 넣은
고정값이다. 두 가지 이유로 상수 방식을 폐기한다.

1. **지금도 값이 정확하지 않다.** 실제 펼침 패널 높이는 약 152px(패딩 28 + 제목 27 + 행 19 +
   막대 12 + 행 27 + 막대 12 + 메타 27) 이고 `bottom:16px` 을 더하면 **168px** 이 필요한데
   `132 + .wrap 하단 margin 32 = 164px` 로 아슬아슬하다. 폰트가 조금만 달라져도 가려진다.

   > **실측 확인(메인 세션, 1440×900 · 합성 스냅샷 9개 프로젝트).** 위 추정이 맞다.
   > 패널 실측 높이 **153px**, 필요 여백 `153 + 16 = 169px`, 확보된 여백
   > `padding-bottom 132 + .wrap margin-bottom 32 = 164px` → **5px 부족**(추정 4px).
   > 실제로 가려지는 것은 마지막 카드가 아니라 그 아래 푸터 `#dzh-collected-at` 이다.
   > 즉 이 결정은 "미래 대비"가 아니라 **현존 결함의 수정**이다.
2. **접힘/펼침으로 값이 두 개가 된다.** 상수 2개를 두면 틀릴 기회도 2배가 된다.

```css
body.has-usage .wrap{padding-bottom:var(--usage-clearance,184px)}
```
```js
document.body.style.setProperty('--usage-clearance',
  (usageEl.offsetHeight + USAGE_CLEARANCE_MARGIN_PX) + 'px');
```

- **접힘/펼침 양쪽에서 가림이 없음의 보장**: 여백 = 패널 실측 높이 + 32px(= `bottom` 오프셋
  16 + 여유 16). 상태가 바뀔 때마다(`applyUsageCollapsedState`) 다시 잰다 → 펼침 ≈ 184px,
  접힘 ≈ 72px. **패널이 오른쪽 아래에 있어도 넓은 화면에서 `.wrap` 우측 하단을 덮는다**
  (예: 1920px 뷰포트에서 `.wrap` 은 x 240~1680, 패널은 x 1484~1904 → 겹친다). 그래서 폭
  조건을 따지지 않고 **항상** 여백을 준다.
- **패널이 없으면 `has-usage` 자체가 없어** 빈 여백이 생기지 않는다(기존 성질 유지).
- **수용하는 한계**: 창 크기를 바꿔 패널 내부 텍스트가 다르게 줄바꿈되면 여백이 최대 30초
  (다음 틱)까지 낡을 수 있다. `resize` 리스너를 달지 않는 이유는, 오차가 몇 픽셀이고 다음
  렌더가 스스로 고치기 때문이다(측정 없는 최적화·불필요한 리스너를 만들지 않는다).

### 결정 Z1 — z-index 는 그대로 둔다 (제약 C6)

`.theme-toggle`(`top:16px;right:16px;z-index:30`) 과 `.usage`(`bottom:16px;z-index:20`) 는
**세로로 반대 끝**에 있다. 겹치려면 뷰포트 높이가 대략 `46(토글 하단) + 168(패널) ≈ 214px`
미만이어야 하는데, 이는 브라우저 창으로 사실상 불가능하다. 만약 겹치더라도 z-index 가 높은
테마 토글이 위에 남는 것이 옳다 — 데이터가 없으면 사라지는 패널과 달리 토글은 **항상 있는
유일한 조작 수단**이기 때문이다.

좁은 폭(모바일)에서는 가로 충돌이 원천적으로 없다(토글은 위, 패널은 아래). 패널 폭은
`min(420px, calc(100vw - 32px))`(접힘은 `max-width:calc(100vw - 32px)`)로 묶여 있어 화면 밖으로
넘치지 않는다. → **z-index·위치 관련 추가 변경 없음.**

### 접근성 (제약 C8)

| 항목 | 처리 |
|------|------|
| 조작 | 진짜 `<button type="button">` — Tab 도달, Enter/Space 동작, 클릭 모두 무료로 얻는다 |
| 상태 | `aria-expanded="true|false"` 를 `applyUsageCollapsedState()` 가 항상 동기화. `aria-controls="dzh-usage-body"` 로 대상 명시 |
| 접힘 시 낭독 | 버튼 접근성 이름 = `"Claude 사용 한도 세션 43% · 주간 71%"` + 상태 `"축소됨"`. **숫자가 접근성 이름 안에 있으므로 접힌 상태에서도 스크린리더 사용자는 펼치지 않고 수치를 얻는다** |
| 펼침 시 낭독 | 요약은 `display:none` → 접근성 트리에서 제거되어 **이중 낭독이 없다**. 버튼은 `"Claude 사용 한도, 확장됨"`, 이어서 본문의 `role="progressbar"` 막대 2개가 기존 `aria-label`("세션 (5시간) 사용률" 등)과 `aria-valuenow` 로 낭독된다 |
| 기존 유지 | 막대의 `role="progressbar"`·`aria-valuenow/min/max`·`aria-label` **전부 그대로**. T25-34 가 `role="progressbar"` 의 생존을 grep 으로 고정한다 |
| 색 이외 채널 | 캐럿 글리프 `▾`/`▸`(형태) + 접힘 시 요약 텍스트 유무(내용) + `aria-expanded`(의미). 색으로 상태를 전달하지 않는다 |
| 색각 안전 | 새 색 리터럴 0개 — `var(--accent)`·`var(--accent-ink)`·`var(--muted)`·`var(--head)` 만 참조하므로 라이트/다크·Okabe–Ito 축이 자동 유지된다(T25-29 통과) |
| 포커스 가시성 | `.usage-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:3px}` |
| 모션 | 없음. 캐럿은 회전이 아니라 **글리프 교체**라 `prefers-reduced-motion` 을 고려할 것이 없다 |

> 참고(수정하지 않음): 기존 `.theme-toggle` 에는 `:focus-visible` 규칙이 없다. 이번 변경이
> 만든 문제가 아니므로 **언급만 하고 손대지 않는다**(수술적 변경 원칙). 별도 티켓 감이다.

---

## 결정 U5 의 대체 (제약 C2)

직전 PRP 의 **결정 U5 는 "패널에 닫기/접기 버튼을 두지 않는다"**였고 근거는 "폴링을 견뎌야
하는 사용자 상태를 늘리지 않는다(YAGNI)"였다. **이번 사용자 요청이 이 결정을 뒤집는다.**

| | 당시 판단 | 지금 |
|---|---|---|
| 요구 | "사용량을 보여준다"까지 | "접고 펼칠 수 있게 하고, 접었을 때는 작게" — **명시적 요구** |
| YAGNI | 아무도 요구하지 않은 기능 | 요구가 생겼으므로 YAGNI 가 더 이상 적용되지 않는다 |
| 비용 | "폴링을 견디는 상태" 설계 부담 | 부담은 실재했다. **H1′ 로 경계를 옮겨 해소**했고 순증 JS 는 약 17줄이다 |

U5 의 근거는 **틀리지 않았다** — 상태를 innerHTML 안에 두면 30초마다 초기화된다는 예측은
정확했다. 달라진 것은 "그 비용을 치를 이유가 생겼다"는 점뿐이다.

### 구 PRP 파일 수정 (구현 범위에 포함 — 문서가 모순된 채 남지 않게)

`docs/prps/hub-theme-and-usage-panel.md` 에 **4곳**을 고친다. 내용은 지우지 않고 **대체
표기만 덧붙인다**(설계 이력은 보존한다).

| 위치 | 추가할 문장 |
|------|-------------|
| `### 결정 U5 …` 제목 바로 아래 (487행 근처) | `> **대체됨(superseded).** 이 결정은 [\`hub-usage-collapse-and-grid.md\`](./hub-usage-collapse-and-grid.md) 의 결정 C1 이 대체한다 — 사용자가 접기/펼치기를 명시적으로 요구했고, 폴링 내성은 불변식 H1′ 로 해결했다. 아래 근거는 당시 판단의 기록으로 남긴다.` |
| 불변식 H1 인용 블록 아래 (155행 근처) | `> **개정됨.** H1 은 [\`hub-usage-collapse-and-grid.md\`](./hub-usage-collapse-and-grid.md) 의 **H1′** 로 대체됐다 — 갱신 대상이 \`#dzh-usage\` 에서 \`#dzh-usage-body\`·\`#dzh-usage-summary\` 로 한 겹 안으로 이동했다.` |
| 결정 요약 표의 `M2` 행 근거 칸 (531행) | 끝에 ` → H1′ 로 개정됨` 추가 |
| 결정 요약 표의 `U5` 행 근거 칸 (541행) | 끝에 ` → **대체됨**(hub-usage-collapse-and-grid.md C1)` 추가 |

또한 패널 명세 표(509~511행)의 `배치`·`가림 방지` 행은 값이 낡게 되므로 각 칸 끝에
`(현행: hub-usage-collapse-and-grid.md L1·L3)` 을 덧붙인다.

---

## 테스트 계획

검증 정본: `bash tests/run.sh` (전체) / `python3 -m unittest discover -s tests/hub -t .` (파이썬).
이 레포에는 별도 linter·type checker 설정이 없다.

**JS 단위 테스트는 없다** — 이 레포에 JS 테스트 러너가 없고, 도입은 "새 외부 의존성 금지"에
정면으로 걸린다. 템플릿의 검증 수단은 직전 PRP 와 동일하게 **`tests/run.sh` 의 grep 회귀
테스트 + 수동 확인 목록** 두 축이다. `usageSummaryText()` 는 순수 함수로 뽑아 두되(장래
테스트 가능성 확보) 지금은 수동 확인으로 검증한다.

**파이썬 테스트는 한 줄도 바뀌지 않는다** — 이 PRP 는 Python 을 건드리지 않으므로 기존
`tests/hub/*.py` 전부가 무수정 통과해야 한다. **이것이 이 변경의 1차 회귀 안전망이다.**

### 자동 — `tests/run.sh` 추가 (T25-32 ~ T25-36)

`test_hub_docs_and_constants()` 안, 기존 T25-31 블록 **뒤**, `log_ok` **앞**에 넣는다.
`hub_template_file` 지역 변수는 2123행에 이미 선언돼 있으므로 재선언하지 않는다.
**함수 상단의 `test_desc` 문자열을 `"허브 문서·상수 정합성 (T25-1~T25-36)"` 으로 갱신할 것.**

```bash
  # T25-32(결정 G1~G5 회귀): 프로젝트 목록이 뷰포트 폭에 따라 열 수가 바뀌는 그리드이고,
  # 카드가 행 높이에 맞춰 늘어나지 않으며, 비-카드 요소는 한 행을 다 쓴다.
  local grid_token
  for grid_token in "max-width:1440px" "display:grid" "repeat(auto-fill,minmax(320px,1fr))" \
                    "align-items:start" "grid-column:1/-1"; do
    if ! grep -qF "$grid_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-32: hub_template.html 에 그리드 규칙($grid_token)이 없음"
      return 1
    fi
  done

  # T25-33(결정 C1 · 불변식 H1′ 회귀 — 이 파일에서 가장 중요한 검사):
  # 접기 버튼은 정적 마크업이어야 하고, 패널 컨테이너를 통째로 다시 그리는 코드가 되살아나면
  # 접힘 상태가 30초 틱마다 초기화된다.
  if ! grep -qF '<button id="dzh-usage-toggle"' "$hub_template_file"; then
    record_failure "$test_name" "T25-33: 접기 버튼이 정적 마크업으로 존재하지 않음"
    return 1
  fi
  if ! grep -qF 'id="dzh-usage-body"' "$hub_template_file"; then
    record_failure "$test_name" "T25-33: 파생 본문 컨테이너(#dzh-usage-body)가 없음"
    return 1
  fi
  if grep -qF "usageEl.innerHTML" "$hub_template_file"; then
    record_failure "$test_name" "T25-33: usageEl.innerHTML 대입이 부활함 — 재렌더가 접기 버튼을 파괴한다"
    return 1
  fi

  # T25-34(제약 C8 회귀): 접기 토글의 상태가 접근성 트리에 노출되고, 기존 막대의
  # progressbar 시맨틱이 리팩토링 중 유실되지 않는다.
  local a11y_token
  for a11y_token in "aria-expanded" 'aria-controls="dzh-usage-body"' 'role="progressbar"'; do
    if ! grep -qF "$a11y_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-34: hub_template.html 에 접근성 속성($a11y_token)이 없음"
      return 1
    fi
  done

  # T25-35(결정 L1·L3·C2 회귀): 패널은 우하단 고정이고(중앙 정렬 흔적이 남으면 안 된다),
  # 하단 여백은 실측 커스텀 속성으로 주며, 접힘 상태는 전용 키에 저장된다.
  if grep -qF "translateX(-50%)" "$hub_template_file"; then
    record_failure "$test_name" "T25-35: 하단 중앙 정렬(translateX(-50%))이 남아 있음"
    return 1
  fi
  local panel_token
  for panel_token in "right:16px;bottom:16px" "--usage-clearance" "'dzh-usage-collapsed'"; do
    if ! grep -qF "$panel_token" "$hub_template_file"; then
      record_failure "$test_name" "T25-35: hub_template.html 에 패널 규칙($panel_token)이 없음"
      return 1
    fi
  done

  # T25-36(문서 정합): 화면 배치 변경이 hub/README.md 에 반영돼 있다.
  local hub_readme_layout_file="$REPO_ROOT/hub/README.md"
  local doc_token
  for doc_token in "우하단" "접기" "그리드"; do
    if ! grep -qF "$doc_token" "$hub_readme_layout_file"; then
      record_failure "$test_name" "T25-36: hub/README.md 에 화면 배치 설명($doc_token)이 없음"
      return 1
    fi
  done
```

> `.usage` 규칙은 위 CSS 스펙대로 **`right:16px;bottom:16px` 순서·무공백**으로 써야 T25-35
> 가 통과한다. 그리드 값도 `repeat(auto-fill,minmax(320px,1fr))` **무공백**이어야 한다
> (이 파일의 기존 CSS 표기 관례와 같다).

### 기존 자동 테스트에 대한 영향 (확인 결과)

| 검사 | 판정 | 근거 |
|------|------|------|
| T25-1 (`HUB_FILE_COUNT`) | 무영향 | 신규 파일 0개 |
| T25-11 (`escapeHtml(session.short_id)`) | 무영향 | 세션 렌더 미변경 |
| T25-12 (`renderTier1ActiveStep`·`renderTier1ImplProgress`·`직전 `) | 무영향 | 함수명·문구 유지. `.tier1-active` 는 **CSS 만** 바뀐다 |
| T25-28 (`prefers-color-scheme`·`data-theme`·`'dzh-theme'`×2) | 무영향 | 테마 코드 미변경. **새 키 `'dzh-usage-collapsed'` 는 `'dzh-theme'` 카운트에 잡히지 않는다**(`grep -oF "'dzh-theme'"` 는 완전 리터럴 일치) |
| T25-29 (구 팔레트 부재) | 무영향 | 새 색 리터럴 0개 |
| T25-30 (`STATE_GLYPH`·`aria-hidden`) | 무영향 | 유지 + 캐럿에서 `aria-hidden` 이 하나 더 는다 |
| T25-31 (README `show_usage_panel`·`plan-usage-history.json`) | 무영향 | 해당 절을 지우지 않고 문장만 보강 |
| `tests/hub/*.py` 전부 | 무영향 | Python 무변경 |

### 수동 확인 목록 (브라우저 실검증 — 자동화 불가)

**A. 그리드**
- [ ] M1 — 뷰포트 390 / 768 / 1024 / 1440 / 2560 px 에서 열 수 = **1 / 2 / 3 / 4 / 4**
- [ ] M2 — 전환 경계 근처(683↔684, 1015↔1016, 1347↔1348)에서 열 수가 정확히 바뀐다
- [ ] M3 — 세션 목록이 긴 카드와 없는 카드가 **같은 행**에 있을 때 짧은 카드가 늘어나지 않는다
- [ ] M4 — 프로젝트 0개("아직 프로젝트가 없습니다"), 1개, 2개일 때의 배치가 어색하지 않다.
      "미확인 프로젝트 N개"·경고 줄이 **한 행 전체**를 쓴다
- [ ] M4b — 긴 프로젝트명·긴 경로(`.path{word-break:break-all}`)·긴 활성 단계명이 320px 열에서
      카드 밖으로 넘치지 않는다. 활성 단계는 **2줄까지** 보이고 그 뒤가 잘린다

**B. 접기/펼치기 지속성**
- [ ] M5 — 접은 뒤 **60초 이상**(30초 틱 2회) 방치 → 접힌 채로 유지
- [ ] M6 — 접은 뒤 새로고침(`http://127.0.0.1:8794`) → 접힌 채로 열린다
- [ ] M7 — 다른 프로젝트에서 활동을 일으켜 **폴링이 실제 갱신을 감지**하게 만든 뒤에도 접힘 유지
      (문자열 변화 경로 = 30초 틱과 다른 두 번째 재렌더 경로)
- [ ] M7b — `file://` 로 열어 토글 동작 + **콘솔 에러 없음**(저장은 실패할 수 있고, 그때는
      새로고침 시 펼침으로 돌아오는 것이 정상)

**C. 가림 방지**
- [ ] M8 — **펼침** 상태에서 페이지 최하단까지 스크롤 → 마지막 행의 카드와 푸터가 안 가려진다
- [ ] M8b — **접힘** 상태에서 같은 확인 → 여백이 과하지 않다(≈72px)
- [ ] M9 — `show_usage_panel:false`(패널 없음) → 하단에 빈 여백이 생기지 않는다

**D. 접근성·테마·좁은 화면**
- [ ] M10 — Tab 으로 토글 도달, Enter/Space 로 접힘, **포커스 링이 보인다**
- [ ] M10b — 재렌더(30초) 직후에도 **포커스가 버튼에 남아 있다**(노드 미교체 확인)
- [ ] M11 — VoiceOver: 접힘 시 `"Claude 사용 한도 세션 43% · 주간 71%, 축소됨"` 류로 낭독,
      펼침 시 요약이 **이중 낭독되지 않고** 막대 2개가 progressbar 로 낭독된다
- [ ] M12 — 라이트/다크 **양쪽**에서 알약·캐럿·포커스 링의 대비가 충분하다
- [ ] M13 — 375px 폭에서 테마 토글과 패널이 겹치지 않고, 접힘 알약이 화면 밖으로 넘치지 않는다
- [ ] M14 — 창 높이를 400px 로 줄여도 테마 토글과 패널이 겹치지 않는다

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 검증 |
|---|------|------|
| 1 | 그리드 CSS 5개 규칙(`.wrap` 폭, `#dzh-app` 그리드, `grid-column:1/-1`, `.card` margin 제거, `.tier1-active` 클램프) — **JS·DOM 무변경** | T25-32, 수동 M1~M4b |
| 2 | 패널 우하단 이동 + `<aside>` 내부 마크업 분리 + `renderUsagePanel` 을 2-write 로 리팩토링 (**접기 기능 없이**, 항상 펼침) | T25-33·34·35 일부, 화면에 패널이 종전대로 보인다 |
| 3 | 접힘 상태(변수·localStorage·클래스·aria) + `--usage-clearance` 실측 | T25-35 전부, 수동 M5~M9 |
| 4 | 문서 — 구 PRP 대체 표기 4곳 + `hub/README.md` + `tests/run.sh` T25-36·`test_desc` | `bash tests/run.sh` 전체 통과 |

1과 2는 서로 의존하지 않아 순서를 바꿔도 된다. 3은 2에 의존한다. 각 마일스톤은 그 자체로
커밋 가능하다.

---

## 리스크와 완화책

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | **`usageEl.innerHTML` 부활** — 훗날 누군가 패널을 손보며 통짜 대입으로 되돌린다 | 접힘 상태가 30초마다 초기화되는 유령 버그 | T25-33 이 문자열 부재를 자동 검사. 코드 주석에 이유를 남긴다 |
| 2 | **`.usage` 에 `display` 를 넣어 `[hidden]` 이 무력화** | 데이터가 없을 때 빈 패널이 뜬다(결정 U3 위반) | GOTCHA 1 로 명시. 수동 M9 가 잡는다 |
| 3 | **실측 여백이 창 크기 변경 직후 최대 30초 낡는다** | 마지막 카드 몇 px 이 잠깐 가려질 수 있다 | 다음 틱이 자가 치유. `resize` 리스너를 달지 않는 이유를 결정 L3 에 명시 |
| 4 | **320px 열에서 한국어 카드가 세로로 길어진다** | 스크롤 이득이 기대보다 작다 | 수동 M4b 로 확인. 필요하면 최소폭만 340~360px 로 올린다(열 전환점 재계산 필요) |
| 5 | **`max-width` 상향으로 페이지 인상이 바뀐다** | 제목·부제·푸터가 넓게 퍼져 허전해 보일 수 있다 | **승인 항목 1** 로 올림. 되돌리기는 상수 1개 수정 |
| 6 | **오리진별 상태 분리**(`http://127.0.0.1:8794` vs `file://`) | 서버 on/off 를 오갈 때 접힘 상태가 달라 보인다 | 테마(결정 T3)와 **완전히 같은 기존 한계**. 수용 |
| 7 | **`-webkit-line-clamp` 접두사 의존** | 표준 `line-clamp` 만 지원하는 미래 브라우저에서 깨질 가능성 | 현행 Chrome/Safari/Firefox 전부가 `-webkit-` 형태를 지원한다(사실상 표준). 깨져도 텍스트가 안 잘릴 뿐 정보 손실이 없다 |
| 8 | **리팩토링 중 `role="progressbar"`·`aria-label` 유실** | 스크린리더 회귀 | T25-34 가 grep 으로 고정 |

---

## 검토했으나 채택하지 않은 대안

1. **패널 전체를 계속 통짜 재렌더하고, 접힘 상태는 매번 HTML 문자열에 다시 구워 넣는다**
   (결정 M2 를 글자 그대로 유지). "DOM = f(스냅샷, 상태)" 라는 더 순수한 모델이고 이벤트
   위임(`closest`) 한 개면 리스너 재바인딩도 필요 없다. 그러나 **30초마다 버튼 노드가 파괴돼
   키보드 포커스가 `<body>` 로 튄다** — Tab 으로 조작 중인 사용자에게 30초짜리 시한폭탄이다
   (제약 C8 정면 위반) → 기각.
2. **접힘 상태를 `hub.html` 에 서버가 구워 넣는다.** 오리진 문제와 지속성이 한 번에 해결된다.
   그러나 읽기 전용 2경로 화이트리스트라는 서버 설계 정본을 깨야 하고, 여러 탭이 서로의
   상태를 덮어쓴다 → 기각(직전 PRP 대안 5와 같은 판단).
3. **`<details>`/`<summary>` 네이티브 요소.** 키보드·접근성·상태 저장(`open` 속성)이 공짜다.
   그러나 (a) `::-webkit-details-marker`/`list-style` 처리가 브라우저마다 달라 마커 제거 CSS 를
   따로 써야 하고, (b) 이 템플릿에는 이미 `.theme-toggle` 이라는 **손수 만든 버튼 선례**가
   있어 두 가지 문법이 공존하게 되며, (c) 낭독 라벨을 `aria-expanded` 만큼 정확히 통제하기
   어렵다 → 기각. (제약 C8 이 지정한 `<button>` + `aria-expanded` 를 따른다.)
4. **`auto-fit` + `minmax(320px,480px)`.** 카드가 적을 때 남는 폭을 나눠 가져 화면이 덜
   허전하다. 그러나 카드 폭이 **개수에 따라** 320~480px 사이에서 변해 예측이 어렵고
   상한 상수가 하나 더 생긴다 → 기각(결정 G3).
5. **CSS 멀티컬럼(`columns:320px`) 또는 masonry.** 벽돌 배치가 가변 높이 카드에 더 어울린다.
   그러나 멀티컬럼은 읽기 순서가 세로(열 우선)로 바뀌어 "최근 활동 순" 정렬이 무의미해지고
   카드가 열 경계에서 쪼개질 수 있다. `grid-template-rows:masonry` 는 아직 표준화 진행 중이라
   지원이 없다 → 기각.
6. **접기 상태에 슬라이드/페이드 애니메이션.** `transform`/`opacity` 만 쓰면 저렴하지만,
   `prefers-reduced-motion` 분기와 높이 측정 타이밍(GOTCHA 4)이 얽힌다. 요구는 "접고 펼친다"
   까지다 → 기각(YAGNI).
7. **JS 테스트 러너(node/jest) 도입으로 `usageSummaryText` 단위 테스트.**
   "새 외부 의존성 금지 · 빌드 단계 없음" 전제와 정면 충돌 → 기각. grep + 수동으로 대체.
8. **패널 폭을 접힘/펼침 모두 고정 420px 유지.** CSS 한 줄이 줄지만 접힘이 "얇고 긴 띠"가
   되어 "작게"라는 요구를 만족하지 못한다 → 기각(결정 L2).

---

## 사용자 승인이 필요한 미결 선택지

### 승인 항목 1 — 컨테이너 최대 폭 (결정 G2)

| 안 | 최대 열 수 | 2560px 화면에서 | 비고 |
|----|-----------|----------------|------|
| **A. `max-width:1440px`** (권고) | **4** | 4열, 좌우 여백 대칭 | 노트북에서 4열 확보. 제목/푸터가 벌판에 뜨지 않는다 |
| B. `max-width:1920px` | 5 | 5열 | 초광폭에서 한 칸 더. 27" 에서 여백이 커진다 |
| C. `max-width:none` | 제한 없음(2560px → **7열**) | 7열 | "브라우저 크기에 최대한" 이지만 좌우 눈 이동 2.3배, 헤더가 고립된다 |

세 안 모두 **뷰포트에 따라 열 수가 동적으로 변한다**는 요구는 만족한다. 차이는 **상한**뿐이다.

### 승인 항목 2 — 접힘 상태의 "간단한 정보" (결정 C5, 제약 C9)

세 안 모두 제목 `Claude 사용 한도` 는 유지한다(결정 C6).

| 안 | 표시 | 접힘 알약 폭(대략) | 장단 |
|----|------|------------------|------|
| A. 세션만 | `Claude 사용 한도  43% ▸` | ≈ 175px | 가장 작다. 그러나 **한 주를 태우는 것은 보통 주간 한도**인데 그 숫자가 사라진다 |
| **B. 세션 + 주간** (권고) | `Claude 사용 한도  세션 43% · 주간 71% ▸` | ≈ 260px | 펼침과 **같은 정보 구조**(두 개의 이름 붙은 수치)라 새 개념이 없다. 라벨 고정이라 값이 요동쳐도 위치가 안 변한다 |
| C. 더 임박한 쪽 하나 | `Claude 사용 한도  주간 71% ▸` | ≈ 215px | 가장 영리해 보이지만, 두 값이 비슷할 때(70 vs 69) 라벨이 왔다 갔다 하고 사용자는 "지금 보고 있는 게 어느 쪽인지" 매번 확인해야 한다 |

**권고 = B.** 이 선택은 접근성 낭독 문구(제약 C8)에도 그대로 반영된다.

### 승인 항목 3 — 결정 U5 의 폐기와 구 PRP 수정

이 PRP 는 직전 승인 설계의 **결정 U5(접기 버튼을 두지 않는다)를 명시적으로 대체**하고,
불변식 **H1 을 H1′ 로 개정**한다. 구현 범위에 `docs/prps/hub-theme-and-usage-panel.md` 의
**4곳 표기 수정**이 포함된다(내용 삭제 없이 대체 표기만 추가). 이 이력 보존 방식으로 진행할지
확인이 필요하다.
