# PRP — 프로젝트 대시보드를 허브 디자인 언어에 맞춘다 (visual parity)

> 상태: **승인 완료 (2026-08-14)** — 구현 착수 가능
> 브랜치: `feature/dashboard-hub-visual-parity`
> 정본(기준): `hub/bin/hub_template.html` — 대시보드가 허브에 맞춘다. 반대 방향이 아니다.

### 사용자 승인 — 확정 (2026-08-14)

§12 의 3개 항목 모두 **권장안 그대로 채택**됐다:

1. **팔레트 전면 이식(S5)**: 채택. 초록·빨강 폐기, 파랑 채움 사다리 + 주황 경고로 재배치.
2. **iframe 테마 동기화(§7)**: **안 D**(임베드 시 `localStorage['dzh-theme']` 읽기 전용 참조 +
   `storage` 이벤트 실시간 추종). 허브 파일 무변경.
3. **부수 항목**: 토글 버튼은 허브와 같은 **`.icon-btn` 클래스를 재사용**한다. README 는
   스크린샷 재촬영과 커맨드 표 줄 수 정정을 **둘 다 이번 커밋에 반영**한다.

---

## 1. 요구사항 요약

`/dashboard` 가 생성하는 프로젝트 대시보드(`commands/dashboard.md` 안의 HTML 템플릿 전문)는
라이트 전용 화면이고, 색 토큰이 카테고리 리터럴(`--blue` `--navy` `--green` `--orange` `--red`)로
박혀 있다. 반면 통합 허브(`hub/bin/hub_template.html`)는 시맨틱 토큰 + 라이트/다크 2테마 +
FOUC 방지 + 토글 버튼을 갖춘 색각 안전(Okabe–Ito) 팔레트를 쓴다. **두 화면은 이미 한
뷰포트 안에서 겹쳐 보인다** — 허브 카드를 클릭하면 그 프로젝트 대시보드가 허브 모달의
`<iframe>` 안에 그대로 뜬다(`hub/bin/hub_template.html:301-309`). 허브가 다크인데 그 안의
대시보드만 흰 화면이면 곧바로 눈에 띈다. 이 PRP 는 대시보드의 색 체계를 허브 토큰으로
교체하고 다크 모드를 도입해, 두 화면이 **같은 디자인 언어**를 쓰게 한다.

**비목표**: 레이아웃 개편(그리드·카드 크기·정보 구조), 허브 전용 기능(사용량 패널·툴팁 싱글턴·
드래그 정렬)의 이식, `/dashboard` 절차(init/step/impl/log)의 인자·마크업 문법 변경.

---

## 2. 확정 전제 (재론하지 않는다)

1. **허브가 정본이다.** 토큰 이름·값은 허브에서 그대로 가져오고 대시보드 고유 색 토큰을
   새로 만들지 않는다.
2. **색각 안전 팔레트 전제는 사용자 수준의 제약이다.** 허브 PRP
   (`docs/prps/hub-theme-and-usage-panel.md:34`)가 "사용자의 `settings.json` 테마가
   `dark-daltonized`" 를 근거로 초록·빨강을 제거했다. 같은 사람이 같은 시간에 두 화면을 본다.
3. **단일 파일 자족성**은 두 도구 모두의 핵심 제약이다. 외부 CSS 파일로 분리하지 않는다
   (`file://` 로도 열려야 하고, 대시보드는 마크다운 리터럴을 Write 하는 방식이다).
4. **`commands/dashboard.md` 는 문서이자 스펙이다.** `<style>` 을 고치면 같은 파일 안의
   산문·표·CSS 사본을 같은 커밋에서 함께 고친다(§8).

---

## 3. 스코프 — 이식할 것 / 제외할 것

| # | 허브의 요소 | 판정 | 근거 |
|---|------------|------|------|
| S1 | 시맨틱 색 토큰 13종(`--bg` `--surface` `--ink` `--head` `--muted` `--line` `--soft` `--accent` `--accent-ink` `--accent-soft` `--attention` `--attention-soft` `--shadow`) | **이식** | 다크 모드의 전제. 토큰 없이는 배경·표면·텍스트를 테마별로 바꿀 수 없다 |
| S2 | 라이트/다크 3블록 구조(`:root` + `@media (prefers-color-scheme:dark) :root:not([data-theme="light"])` + `:root[data-theme="dark"]`) | **이식** | 요청의 본체. 미디어 쿼리 블록은 `localStorage` 가 던지는 환경의 유일한 안전망이다(허브 결정 Y2) |
| S3 | `<head>` FOUC 방지 인라인 스크립트 | **이식** | 다크 사용자에게 흰 화면 번쩍임이 남지 않게 하는 유일한 수단 |
| S4 | 테마 토글 버튼 + `.icon-btn`(32px 원형) | **이식(토글만)** | 수동 오버라이드가 없으면 허브와 동작이 어긋난다. `.icon-btn` 은 토글 1개만 쓰므로 클래스를 새로 만들 실익이 있는지 §6.4 에서 판단 |
| S5 | 색각 안전 축(파랑–주황)으로의 상태 색 재배치 — 초록·빨강 폐기 | **이식(승인 항목 1)** | 전제 2. 다만 사용자에게 보이는 의미 변화라 승인 대상 |
| S6 | `--shadow` 토큰화 | **이식** | 다크에서 `rgba(19,51,91,.07)` 그림자는 보이지 않는다. 테마별 값이 실제로 필요하다 |
| S7 | `.badge{display:inline-flex;align-items:center;line-height:1}` | **이식** | 허브가 실측으로 고친 수직 정렬 문제(`hub_template.html:134-136`)가 대시보드 배지에도 그대로 있다 |
| S8 | `body{line-height:1.5}` · `h1{font-size:20px;letter-spacing:-.4px}` | **이식** | 값 차이에 근거가 없다. 같은 값으로 맞추는 것이 parity 의 정의 |
| S9 | `:focus-visible` 처리 관례 | **이식(국소)** | 필터 라디오는 `opacity:0` 이라 지금 키보드 포커스가 **보이지 않는다**. 토큰 교체로 어차피 만지는 줄이라 같이 고친다 |
| S10 | `.icon-btn` 형태로의 `#dz-pip-btn` 전환 | **제외** | 허브 버튼은 아이콘 전용 단일 액션, `#dz-pip-btn` 은 **텍스트가 상태를 말하는**(`플로팅`/`플로팅 닫기`) + `disabled` 사유가 있는 토글이다. 아이콘화하면 정보를 잃는다. 색 토큰·hover/focus 처리만 맞춘다 |
| S11 | 상태 배지의 글리프 채널(`STATE_GLYPH` + `aria-hidden`) | **제외** | 대시보드 배지·칩은 **이미 텍스트 라벨**(`완료`/`진행중`/`대기`)을 항상 달고 있어 색 이외 채널이 이미 있다. 글리프를 넣으려면 `init`·`step`·`impl`·`log` 네 절차의 리터럴 마크업을 전부 바꿔야 하고(§8 의 결정성 계약), 얻는 것이 중복 채널 하나뿐이다 — YAGNI |
| S12 | 그리드 레이아웃(`#dzh-app`) · 카드 드래그 · `card-working` pulse | **제외** | 대시보드는 프로젝트 1개의 단일 컬럼 페이지다. 대상 자체가 없다 |
| S13 | 사용량 패널(`.usage`) · 툴팁 싱글턴(`.tooltip`) · 대시보드 모달(`.modal`) | **제외** | 허브 전용 기능. 대시보드에는 소비자가 없다 |
| S14 | `dzh-project-order` 등 허브 localStorage 상태 | **제외** | 대상 없음 |
| S15 | 3열 그리드 상수·`--usage-clearance` 등 허브 레이아웃 상수 | **제외** | 대상 없음 |

---

## 4. 영향 범위

### 4.1 `commands/dashboard.md` (1358행) — 주 변경 대상

| 구간(현재 행) | 무엇 | 변경 |
|--------------|------|------|
| 79 | 「정적(불가침)」 문장 | `<head>` 테마 스크립트·`#dz-theme-toggle` 추가 |
| 149-161 | 로그 항목 스키마 예시 HTML | 배지 마크업 자체는 불변(클래스명 유지). 변경 없음 확인용 |
| 169-174 | `log` 인자 ↔ 배지 ↔ **색(토큰)** 대응표 | `--blue`→`--accent`, `--green`→`--accent-ink`, `--red`(신규 토큰 `#C2410C`)→`--attention`, `--navy`→`--head` |
| 189-192 | `body.dz-embedded` 설명(허브 모달) | 테마 상속 규칙 1~2줄 추가 |
| 200-214 | 「정적 요소 추가」 표 | `#dz-theme-toggle`·`#dz-top-actions` 행 추가 |
| 223-236 | 폴링 동기화 계약 표 | "치환하지 않는다" 행에 테마 토글·`<html data-theme>` 추가 |
| 341-359 | 매트릭스 CSS **사본** | 템플릿과 글자 단위로 동일하게 갱신(§5.3) |
| 398-409 | `init` 5단계 마크업 | **변경 없음**(글리프 미도입 결정 S11 의 직접 효과) |
| 1019-1046 | 로그 UI 필터 CSS **사본** + 1046행 "원본의 `:root` 색 토큰은 그대로 유지한다" | CSS 사본 갱신 + 1046행을 "색 토큰의 정본은 `hub/bin/hub_template.html`" 로 개정 |
| 1054-1059 | 템플릿 `<head>` 시작 | `<meta name="color-scheme" content="light dark">` 추가 |
| 1078-1086 | 템플릿 안 `DZ:DASHBOARD` 주석의 정적 목록 | 테마 관련 정적 노드 추가 |
| 1088-1158 | `<style>` 전문 | 토큰 3블록 + 전 규칙 토큰화(§5) |
| 1158-1159 | `</style>` ~ `</head>` 사이 | FOUC 인라인 `<script>` 삽입(§6.2) |
| 1184-1185 | `#dz-pip-btn` · `#dz-pip-hint` | `#dz-top-actions` 클러스터로 감싸고 토글 버튼 추가(§6.3) |
| 1317-1353 | PiP `requestWindow().then` 블록 | `data-theme` 전파 1줄 추가(§6.5) |
| 1354(끝) | 스크립트 말미 | 테마 IIFE 추가(§6.4) |

### 4.2 `tests/run.sh` (3140행)

| 행 | 무엇 | 변경 |
|----|------|------|
| 999 · 1002 | `T22-1~T22-104` 범위 문구 2곳 | 새 최대 번호로 갱신 |
| 1176-1181 | **T22-27** `:root` 줄 완전 일치 | 재작성 — 유일하게 반드시 깨지는 기존 검사(§9.1) |
| 1866 부근(`log_ok` 직전) | 신규 하위 검증 삽입 지점 | T22-105~ 추가(§9.2) |

### 4.3 `hub/bin/hub_template.html` — **권장안에서는 무변경**

§7 의 권장안(D)은 허브 파일을 한 줄도 건드리지 않는다. 대안 B(쿼리 파라미터/postMessage)를
고르면 `hub_template.html` + `hub/bin/hub_server.py`(경로 정규식) + `tests/hub/test_hub_server.py`
+ T25 가 함께 열린다 — §7 에 영향 범위를 따로 적었다.

### 4.4 문서

| 파일 | 변경 | 필수 |
|------|------|------|
| `README.md:140-153` | `/dashboard` 설명에 테마 1줄 + **스크린샷 재촬영**(`docs/images/dashboard-sample.png`) | 스크린샷은 승인 항목 3 |
| `README.md:120` | 커맨드 표의 `dashboard` 줄 수 `1224` | 이미 실제(1358)와 어긋난 **선행 드리프트**. 이번 변경으로 더 벌어지므로 같이 고칠지 결정(승인 항목 3) |
| `hub/README.md:185-206` | 모달 절에 "모달 안 대시보드는 허브 테마를 따라간다" 1줄 | 권장안 D 채택 시 필수(사용자에게 보이는 동작) |

### 4.5 미영향 — 건드리지 않는 이유

- `hub/bin/hub_parse.py` — 대시보드 HTML 을 정규식으로 읽지만 대상은 `<h1 id="dz-title">` ·
  `id="dz-progress-pct"` · `id="dz-updated">` · `<li id="dz-step-N" class="…"` ·
  `<td class="cell" id="dz-cell-…"` · `<li id="dz-impl-N" class="…"` 뿐이다. **이 여섯 패턴이
  걸린 줄은 이번 변경에서 한 글자도 바뀌지 않는다**(§10 GOTCHA 1).
- `tests/hub/fixtures/*.html` — 파서 입력용 **동결 스냅샷**이다. 파서 계약이 안 바뀌므로 갱신 불필요.
- `docs/prps/dashboard-group-matrix.md:450` — 과거 PRP 안의 옛 `:root` 인용. 역사 기록이라 손대지 않는다.
- `install.sh` — 파일 수·경로 불변.

---

## 5. 색 토큰 재설계안

### 5.1 두 종류의 색을 구분한다

- **테마 종속(surface/text/line)** — 라이트·다크에서 값이 **달라져야** 하는 색.
- **상태 범주(state)** — 완료·진행중·대기·실패를 **구분해야** 하는 색.

기존 대시보드는 이 둘을 구분하지 않고 카테고리 리터럴 토큰 하나로 처리했다(`--green` 이
곧 완료색이자 완료 텍스트색). 허브는 테마 종속 토큰만 정의하고, **상태 구분은 그 토큰들의
조합(채움 강도)으로 표현**한다(`.badge.state-working` = 채움, `state-idle` = 플랫,
`state-done` = 윤곽선). 대시보드도 같은 방식을 쓴다 — **새 토큰을 만들지 않는다.**

### 5.2 토큰 블록 (허브 `hub_template.html:54-79` 를 그대로 이식)

```css
  :root{
    color-scheme:light;
    --bg:#EEF3F8;--surface:#FFFFFF;--ink:#172033;--head:#12335B;--muted:#5A6879;
    --line:#D9E2EC;--soft:#F4F7FB;
    --accent:#0072B2;--accent-ink:#005B8F;--accent-soft:#E4F0F8;
    --attention:#B45309;--attention-soft:#FBEEDC;
    --shadow:0 8px 24px rgba(19,51,91,.06);
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){ /* 다크 값 13종 — 허브와 동일 */ }
  }
  :root[data-theme="dark"]{ /* 같은 13종 — 허브와 동일 */ }
```

- 값은 허브와 **완전히 같아야** 한다(모달 iframe 안에서 두 표면이 맞붙는다).
- 다크 값 중복(미디어 쿼리 + 속성 선택자)은 허브의 기존 구조를 따른다. `localStorage` 가
  던져 `data-theme` 이 안 붙는 환경에서 미디어 쿼리가 유일한 안전망이기 때문이다(허브 결정 Y2).
- `--muted` 는 값이 바뀐다: 대시보드 `#5E6B7D` → 허브 `#5A6879`. 토큰 이름이 같아 치환이 아니라
  **값 정렬**이다.
- `--orange` 는 선언만 있고 사용처가 0이다(현행 확인). 이번 개편에서 자연히 사라진다.

### 5.3 규칙별 치환 매핑 (전수)

| 현재 행 | 현재 | 변경 후 | 비고 |
|--------|------|--------|------|
| 1091 | `body{background:#EEF3F8;line-height:1.55}` | `background:var(--bg);line-height:1.5` | S8 |
| 1093 | `.card{background:#fff;box-shadow:0 8px 24px rgba(19,51,91,.07)}` | `background:var(--surface);box-shadow:var(--shadow)` | S6 |
| 1094 | `h1{font-size:21px;color:var(--navy);letter-spacing:-.5px}` | `font-size:20px;color:var(--head);letter-spacing:-.4px` | S8 |
| 1096 | `.bar-inner{background:linear-gradient(90deg,var(--blue),#2D78C8)}` | `background:var(--accent)` | 허브 `.usage-bar>span` 과 같은 단색. 그라디언트는 다크에서 두 번째 정지색을 또 정해야 한다 |
| 1097 | `.pct{color:var(--blue)}` | `color:var(--accent-ink)` | 텍스트라 대비 확보용 `-ink` |
| 1102 | `li.done .num{background:var(--green);color:#fff}` | `background:var(--accent-soft);color:var(--accent-ink)` | 채움 사다리 중간 |
| 1103 | `li.active .num{background:var(--blue);color:#fff}` | `background:var(--accent-ink);color:var(--bg)` | 허브 `.badge.state-working` 과 **같은 공식**(대비 근거 포함) |
| 1105 | `li.active{color:var(--navy)}` | `color:var(--head)` | |
| 1107 | `li.done .chip{background:#E5F3EE;color:var(--green)}` | `background:var(--accent-soft);color:var(--accent-ink)` | 허브 `.agent-chip-running` 과 같은 공식 |
| 1108 | `li.active .chip{background:#EAF2FB;color:var(--blue)}` | `background:var(--accent-ink);color:var(--bg)` | |
| 1116 | `.matrix th.group{color:var(--navy)}` | `color:var(--head)` | |
| 1118 | `cell[data-state="done"]{background:#E5F3EE;color:var(--green)}` | `background:var(--accent-soft);color:var(--accent-ink)` | |
| 1119 | `cell[data-state="active"]{background:#EAF2FB;color:var(--blue)}` | `background:var(--accent-ink);color:var(--bg)` | |
| 1120 | `cell[data-state="na"]{background:#fff;color:var(--line)}` | `background:var(--surface);color:var(--line)` | |
| 1121 | `.badge{display:inline-block;padding:2px 8px;margin-right:6px}` | `display:inline-flex;align-items:center;line-height:1;padding:4px 9px;margin-right:6px` | S7 |
| 1123 | `.badge.impl{background:#EAF2FB;color:var(--blue)}` | `background:var(--accent-soft);color:var(--accent-ink)` | |
| 1124 | `.badge.pass{background:#E5F3EE;color:var(--green)}` | `background:var(--accent-ink);color:var(--bg)` | 채움으로 PASS 를 impl 과 가른다 |
| 1125 | `.badge.fail{background:#FBE9E2;color:var(--red)}` | `background:var(--attention-soft);color:var(--attention);border:1px dashed var(--attention)` | 허브 `.badge.state-stale` 공식(색+형태 2채널) |
| 1126 | `.badge.commit{background:#E7EAF3;color:var(--navy)}` | `background:var(--soft);color:var(--head);border:1px solid var(--line)` | 허브 `.badge.state-done` 계열 |
| 1129 | `.dzf:checked + label{background:var(--blue);color:#fff;border-color:var(--blue)}` | `background:var(--accent-ink);color:var(--bg);border-color:var(--accent-ink)` | |
| (신규) | — | `.dzf:focus-visible + label{outline:2px solid var(--accent);outline-offset:2px}` | S9 |
| 1132 | `ul.log{color:#4B5A6D}` | `color:var(--muted)` | |
| 1143 | `#dz-pip-btn{position:fixed;top:18px;right:18px;z-index:9;…background:#fff;color:var(--navy);box-shadow:0 2px 8px …}` | 위치 4선언을 `#dz-top-actions` 로 이동. `background:var(--surface);color:var(--head);box-shadow:var(--shadow)` + `:hover{color:var(--accent-ink);border-color:var(--accent)}` + `:focus-visible{outline:2px solid var(--accent);outline-offset:3px}` | S10 |
| 1145 | `#dz-pip-hint{…background:#fff;box-shadow:0 2px 8px …}` | `background:var(--surface);box-shadow:var(--shadow)` | |
| 1156 | `body.dz-pip ol.steps li.active{background:#EAF2FB}` | `background:var(--accent-soft)` | |

**변경 없음(토큰 이름이 이미 같음)**: `.bar-outer` · `.num` 기본 · `.chip` 기본 ·
`li.done{color:var(--muted)}` · `.step-detail` · `.matrix th/td` 테두리 · `.matrix thead th` ·
`.matrix td.cell` 기본 · `.badge.round` · `label[for^="dzf-"]` 기본 · `.entry` 계열 ·
`.log-title`/`.impl-title`/`.foot` · `#dz-impl-card:not(:has(…))` · `body.dz-embedded` 규칙 ·
`body.dz-pip` 여백 규칙.

### 5.4 상태 = 채움 강도 사다리 (색상 하나로 3단계)

| 상태 | 배경 | 텍스트 | 강도 |
|------|------|--------|------|
| 대기(wait) | `--soft` | `--muted` | 무채색 (최저) |
| 완료(done) | `--accent-soft` | `--accent-ink` | 파랑 틴트 (중간) |
| 진행중(active) | `--accent-ink` | `--bg` | 파랑 채움 (최고) |
| 실패(fail) | `--attention-soft` | `--attention` + 점선 | 주황 (경고) |

세 단계가 **명도로 갈린다** — 색상 인지가 어려워도 구분된다. "지금 하는 일"이 가장 진하다는
위계는 지금과 같고, 완료가 초록에서 파랑 틴트로 바뀌는 것만 사용자에게 보이는 변화다
(승인 항목 1).

> **검증 항목**: 다크에서 `--accent-soft(#12324A)` 와 `--soft(#1B2634)` 의 명도차가 작다.
> 실제 렌더에서 완료·대기 칸이 구분되지 않으면 **예비안** — 완료 `.num`/칸에
> `box-shadow:inset 0 0 0 1px var(--accent)` 로 형태 채널을 하나 더한다(레이아웃 이동 없음).
> 예비안은 실측 후에만 넣는다. 미리 넣지 않는다.
>
> **실측 결과(구현 완료 후, 2026-08-14)**: 브라우저에서 WCAG 상대 휘도 공식으로 직접 계산 —
> `accent-soft` vs `soft`(다크) 명도 대비 **1.15:1**(사실상 무구분. 텍스트 자체는
> `accent-ink` on `accent-soft` 7.52:1, `muted` on `soft` 6.07:1 로 둘 다 가독성은 문제없음).
> 리스크가 실측으로 확인돼 **예비안을 적용**했다 — `li.done .num`과
> `.matrix td.cell[data-state="done"]`(사본 2곳 포함, 총 3곳)에 inset ring 추가.
> `tests/run.sh` T22-114 가 정확히 3곳 존재를 강제한다.

---

## 6. 다크 모드 도입 설계

### 6.1 데이터 모델 (모듈 경계를 넘는 값)

```
ThemeName = "light" | "dark"            // 이 두 문자열 외의 값은 "부재"와 동일 취급

저장 계약
  localStorage["dz-theme"]   : ThemeName    // 단독 창(대시보드 자신의 오리진)
  localStorage["dzh-theme"]  : ThemeName    // 허브 소유. 임베드 시 읽기 전용으로 참조(§7)

표현 계약
  <html data-theme="light"|"dark">          // CSS 가 읽는 유일한 상태. 없으면 시스템 선호
```

- 허브 키(`dzh-theme`)와 **다른 이름**을 쓴다. 단독 탭은 프로젝트 서버 오리진
  (`localhost:8791`)이라 허브 오리진(`8794`)과 저장소가 애초에 분리돼 있지만, 임베드 시에는
  **같은 오리진에서 두 키가 공존**하므로 이름이 겹치면 안 된다.

### 6.2 FOUC 방지 — `<head>` 인라인 스크립트

`</style>`(1158) 다음, `</head>`(1159) 앞에 놓는다. 허브(`hub_template.html:259-270`)와 같은 자리다.

```html
<script>
/* body 파싱 전에 실행돼 첫 페인트부터 확정 테마로 그린다(FOUC 방지).
   허브 모달(iframe) 안이면 허브가 쓴 키를 읽는다 — 같은 오리진이라 값이 그대로 보인다(§7 결정).
   단독 창이면 자기 키를 읽고, 없으면 시스템 선호를 한 번만 읽어 확정해 저장한다.
   localStorage 는 file:// 나 저장소 차단 환경에서 던질 수 있어 통째로 감싼다. */
try{
  var embedded = window.self !== window.top;
  var key = embedded ? 'dzh-theme' : 'dz-theme';
  var stored = localStorage.getItem(key);
  var theme = (stored === 'light' || stored === 'dark') ? stored
            : ((window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  if(!embedded && stored !== theme) localStorage.setItem(key, theme);
}catch(e){}
</script>
```

- **임베드 상태에서는 쓰지 않는다** — 허브 키의 소유자는 허브다.
- 이 스크립트가 끝나면 `data-theme` 은 (예외가 없는 한) 항상 존재한다. 예외 시에는 미디어
  쿼리 블록이 받는다.
- 식별자 이름에 **`isEmbedded` 를 쓰지 않는다** — §10 GOTCHA 2.

### 6.3 토글 버튼 — 마크업과 위치

현재 `.wrap` 바깥(`<body>` 직계)에 `#dz-pip-btn`(1184) 과 `#dz-pip-hint`(1185) 가 있다.
토글도 **반드시 `.wrap` 바깥**이어야 한다 — `.wrap` 은 통째로 PiP 창으로 **이동**하므로,
안에 두면 토글이 opener 에서 사라진다(`#dz-pip-btn` 이 바깥에 있는 것과 같은 이유,
T22-37 이 강제).

```html
<div id="dz-top-actions">
  <button id="dz-pip-btn" type="button">플로팅</button>
  <button id="dz-theme-toggle" class="icon-btn" type="button"
          aria-label="다크 테마로 전환" title="다크 테마로 전환">☾</button>
</div>
<div id="dz-pip-hint" hidden></div>
```

```css
  #dz-top-actions{position:fixed;top:18px;right:18px;z-index:9;display:flex;align-items:center;gap:8px}
  .icon-btn{width:32px;height:32px;padding:0;color:var(--muted);background:var(--surface);
            border:1px solid var(--line);border-radius:999px;cursor:pointer;font-family:inherit;font-size:15px;
            line-height:1;display:inline-flex;align-items:center;justify-content:center;box-shadow:var(--shadow)}
  .icon-btn:hover{color:var(--accent-ink);border-color:var(--accent)}
  .icon-btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
  body.dz-embedded #dz-pip-btn,body.dz-embedded #dz-pip-hint,body.dz-embedded #dz-theme-toggle{display:none}
```

- **순서가 근거를 갖는다**: 토글이 **오른쪽 끝**이다. `#dz-pip-btn` 의 라벨은
  `플로팅`↔`플로팅 닫기` 로 길이가 변하는데, 오른쪽 정렬 클러스터에서는 그 변화가 왼쪽으로만
  번져 토글이 흔들리지 않는다(허브 결정 Y4 가 지적한 "클러스터 폭 흔들림"과 같은 문제).
- **글리프·라벨은 "전환될 대상"을 가리킨다**(허브 규약): 라이트면 `☾`/"다크 테마로 전환".
- 허브에는 툴팁 싱글턴이 있지만 대시보드에는 없다 — 네이티브 `title` 로 충분하다(§S13).
- `body.dz-embedded` 규칙은 **선택자를 나열**한다. 클러스터(`#dz-top-actions`) 하나로 묶어
  숨기면 T22-97 이 깨진다(§10 GOTCHA 3).
- `.icon-btn` 클래스를 새로 만드는 이유: 지금 사용처가 1곳이라 YAGNI 위반으로 보일 수 있다.
  **대안은 `#dz-theme-toggle` 에 직접 쓰는 것**이며, 그렇게 해도 무방하다. 클래스명을 허브와
  같게 두면 두 파일을 나란히 읽을 때 같은 이름이 같은 모양을 뜻한다는 이점만 있다 —
  구현자 판단에 맡기지 말고 **승인 항목 3** 으로 올린다.

### 6.4 토글 스크립트 — 인터페이스

기존 `<script>`(1186-1355)의 **뒤에** 독립 IIFE 로 붙인다. 앞이 아니다 — 기존 IIFE 는 폴링과
PiP 라는 이 도구의 핵심 기능이고, 테마 IIFE 가 먼저 실행되다 예외를 던지면 같은 `<script>`
블록의 나머지가 통째로 죽는다.

```js
/** 지금 유효한 테마를 돌려준다. 저장값이 light/dark 가 아니면 시스템 선호로 낙착한다. */
function currentTheme(): ThemeName

/** data-theme 속성·글리프·aria-label·title 을 한꺼번에 맞춘다. 열려 있는 PiP 창까지 포함한다. */
function applyTheme(theme: ThemeName): void

/** 지금 갱신해야 할 문서 목록 — 메인 문서 + (열려 있으면) PiP 문서. */
function themeDocuments(): Document[]
```

- `themeDocuments()` 는 `window.documentPictureInPicture && window.documentPictureInPicture.window`
  로 PiP 창을 찾는다. 기존 IIFE 의 `pipWindow` 지역 변수를 공유하지 않는다 — **두 IIFE 사이에
  새 결합을 만들지 않기 위해서**이며, 표준 API 가 같은 정보를 이미 준다.
- 저장은 클릭 핸들러에서만 한다. ~~임베드 상태에서는 버튼이 `display:none` 이라 포커스도
  클릭도 닿지 않으므로 별도 가드를 넣지 않는다(일어날 수 없는 상태를 방어하지 않는다).~~
  **개정(검수 후, 2026-08-14)**: 코드 리뷰에서 head 스크립트의 `setItem` 가드
  (`if(!embedded && …)`)와 클릭 핸들러의 방어 수준이 비대칭이라는 지적을 받아, 클릭
  핸들러 첫 줄에도 `if(embedded) return;` 을 추가했다. CSS 만으로는 "허브 키에 절대
  안 쓴다"는 §7 의 계약을 코드 레벨에서 증명하지 못하고(누군가 `body.dz-embedded` 규칙을
  잘못 고쳐도 grep 테스트가 못 잡는다), T22-112 도 이 가드 존재를 함께 검사하도록 보강했다.
- `storage` 이벤트를 듣는다: `window.addEventListener('storage', …)` — 같은 오리진의 다른
  문서가 키를 바꾸면 발화한다. 이것이 §7 권장안의 **실시간 동기화 경로**이자, 단독 탭을 두 개
  열었을 때의 자동 동기화이기도 하다.

### 6.5 PiP 창으로의 테마 전파

PiP 창은 opener 의 CSS 를 상속하지 않아 이미 `<style>` 전문을 복사한다(1324-1329). 복사되는
것은 `<style>` 뿐이므로 **`data-theme` 속성은 따라가지 않는다.** 복사 직후·`.wrap` 이동 전에
한 줄을 더한다:

```js
        var currentThemeAttribute = document.documentElement.getAttribute('data-theme');
        if(currentThemeAttribute) pipDocument.documentElement.setAttribute('data-theme', currentThemeAttribute);
```

- 속성이 없으면(=`localStorage` 예외 환경) 넣지 않는다. 그 경우 복사된 `<style>` 안의
  `@media (prefers-color-scheme:dark)` 가 PiP 창에서도 그대로 동작한다.
- 열려 있는 동안의 토글은 `applyTheme` 이 `themeDocuments()` 로 두 문서를 함께 갱신한다(§6.4).
- `color-scheme` 은 CSS(`:root{color-scheme:light}`) 안에 있으므로 `<style>` 복사만으로 따라간다.
  `<meta name="color-scheme">` 는 메인 문서용 보조다.

---

## 7. 허브 모달(iframe) 테마 동기화 — 트레이드오프

### 7.0 판단의 근거가 되는 사실 (직접 확인함)

1. 모달 iframe 은 **허브 서버가 서빙한다** — `hub_template.html:1096-1098` 이 상대 경로
   `/project/<key>/dashboard.html` 로 `src` 를 만든다. 즉 **iframe 은 허브 페이지와 항상
   같은 오리진**이다.
2. 카드 클릭은 서버 모드에서만 활성이다(`hub_template.html:747`
   `isClickable = Boolean(project.dashboard_key) && isServed`). 임베드는 `file://` 에서
   발생하지 않는다.
3. 따라서 **임베드된 대시보드는 허브의 `localStorage` 를 그대로 읽을 수 있고**, 허브가 테마를
   바꾸면 iframe 에 `storage` 이벤트가 발화한다(같은 오리진의 다른 문서에서 발생하는 변경).
4. 허브 서버의 경로 정규식은 `^/project/([0-9a-f]{16})/dashboard\.html\Z` 이고
   `self.path`(쿼리 포함)에 `.match()` 를 건다(`hub/bin/hub_server.py:28,52`) —
   **`?theme=dark` 를 붙이면 404 다.**

### 7.1 선택지 비교

| 안 | 동작 | 건드리는 파일 | 장점 | 단점 |
|----|------|--------------|------|------|
| **A. 독립** | iframe 도 자기 FOUC 스크립트로 시스템 선호만 본다 | `commands/dashboard.md` | 가장 단순. 계약 없음 | 허브에서 **수동으로** 라이트를 고른 사용자가 다크 시스템이면 모달만 다크로 뜬다 — 요청의 동기(한 화면 안 불일치)를 그대로 남긴다 |
| **B-1. 쿼리 파라미터** | 허브가 `?theme=dark` 를 붙여 연다 | `hub_template.html` + **`hub_server.py`(정규식)** + `tests/hub/test_hub_server.py` + T25 | 초기 표시가 정확 | **서버 경로 정규식을 풀어야 한다**(사실 4). 경로 검증을 느슨하게 만드는 변경이라 보안 리뷰 대상이 되고, 열린 뒤의 토글 변경은 여전히 반영 안 됨 |
| **B-2. postMessage** | 모달을 열고 iframe `load` 후 테마를 보낸다 | `hub_template.html` + `commands/dashboard.md` + T25 | 열린 뒤 변경도 전달 가능 | **첫 페인트 이후**에 도착해 FOUC 가 남는다(핸드셰이크 타이밍). 두 파일에 걸친 메시지 프로토콜이라는 새 계약이 생긴다 |
| **C. 시스템 선호만** | 대시보드에 토글 자체를 두지 않는다 | `commands/dashboard.md` | 가장 적은 코드 | 단독 탭 사용자가 오버라이드할 수단이 없다. 허브의 수동 선택과도 여전히 어긋난다 |
| **D. 같은 오리진 키 읽기 (권장)** | 임베드면 `localStorage['dzh-theme']` 를 **읽기 전용**으로 참조하고, `storage` 이벤트로 실시간 추종 | `commands/dashboard.md` **only** | 허브 무변경. 첫 페인트부터 정확(FOUC 없음). 열린 뒤 토글도 즉시 반영. 실패 시 시스템 선호로 조용히 낙착 | 허브의 키 이름·값 어휘(`'light'|'dark'`)에 **단방향 의존**이 생긴다 |

### 7.2 권장 — **안 D**

근거:
- **허브를 건드리지 않는다**(제약 4). 허브 서버 경로 검증을 푸는 B-1 은 보안 표면을 넓히고,
  B-2 는 FOUC 를 남기면서 두 파일에 프로토콜을 만든다. D 는 이미 존재하는 브라우저 계약
  (동일 오리진 `localStorage` + `storage` 이벤트)만 쓴다.
- **첫 페인트가 정확하다.** `<head>` 스크립트에서 동기적으로 읽으므로 핸드셰이크가 없다.
- **실패가 안전하다.** 허브가 키 이름을 바꾸거나 저장소가 막히면 값이 `null` → 시스템 선호로
  낙착한다. 깨지지 않고 **덜 정확해질 뿐**이다.
- 의존은 **단방향·읽기 전용**이다. 허브는 대시보드의 존재를 몰라도 된다.

**계약 명문화**(구현 시 문서에 남길 것):

> 허브 모달 안에서 열린 대시보드는 `localStorage['dzh-theme']` 를 **읽기만** 한다.
> 이 키의 소유자는 허브(`hub/bin/hub_template.html`)이며 대시보드는 절대 쓰지 않는다.
> 키가 없거나 값이 `light`/`dark` 가 아니면 시스템 선호로 낙착한다.

`hub/README.md` 모달 절에도 한 줄(“모달 안 대시보드는 허브 테마를 따라간다”)을 더한다 —
사용자에게 보이는 동작이므로 허브 문서에 기록되는 편이 맞다(코드 변경은 없다).

---

## 8. `commands/dashboard.md` 산문 동시 개정 (문서=스펙 제약)

| 위치 | 지금 | 개정 |
|------|------|------|
| 79 | "`<style>` 블록, `:root` 색 토큰, 카드 골격, 하단 스크립트" | "…, `<head>` 테마 스크립트, `#dz-theme-toggle`" 추가 |
| 169-174 | 배지 색 토큰 표(`--blue`/`--green`/`--red`/`--navy`) | 새 토큰명으로 교체. `--red`(신규 토큰 `#C2410C`) 문구 삭제 |
| 189-192 | `body.dz-embedded` 설명 | "임베드 시 테마는 허브 키를 읽어 따라가고, 자체 토글은 숨는다" 추가 |
| 200-214 정적 요소 표 | 5행 | `#dz-top-actions`·`#dz-theme-toggle` 2행 추가 |
| 223-236 폴링 계약 표 | "치환하지 않는다" 행 | `#dz-theme-toggle`·`<html data-theme>` 를 비치환 대상으로 명시 |
| 341-359 매트릭스 CSS 사본 | 옛 리터럴 | 템플릿과 **글자 단위 동일**하게. 343행 "새 색 토큰을 만들지 않는다"는 개편 후에도 **참이므로 유지** |
| 1019-1046 필터 CSS 사본 | 옛 리터럴 | 갱신. 1046행 "원본(`~/Desktop/dashboard.html`)의 … `:root` 색 토큰 … 그대로 유지" → "색 토큰의 정본은 `hub/bin/hub_template.html` 이며 그 값을 그대로 쓴다" |
| 1078-1086 템플릿 주석 | 정적 목록 | 테마 노드 추가 |

---

## 9. 테스트 계획

### 9.1 영향받는 기존 T22 하위 검증

| 검사 | 상태 | 조치 |
|------|------|------|
| **T22-27**(1176-1181) `:root` 줄 **완전 일치** | **반드시 깨진다** | 재작성. 세 갈래로 바꾼다 — ① 정방향: `--bg:` `--surface:` `--head:` `--accent:` `--accent-ink:` `--accent-soft:` `--attention:` `--attention-soft:` `--shadow:` 토큰명 존재 ② 역방향: `--navy:` `--blue:` `--green:` `--red:` `--orange:` 부재 ③ 역방향: `#1F8A70`·`#C2410C`·`#F59E0B` 부재(T25-29 와 대칭) |
| T22-99(1793-1802) `isEmbedded` 등장 **정확히 2줄** | **깨질 수 있다** | 새 코드가 `isEmbedded` 문자열을 포함하면 실패. 다른 이름을 쓰면 무변경 통과(§10 GOTCHA 2) |
| T22-97(1780-1785) `body.dz-embedded #dz-pip-btn` | **깨질 수 있다** | 선택자 나열 유지 시 통과. 클러스터로 묶어 숨기면 실패(§10 GOTCHA 3) |
| T22-3 배지 4종 · T22-4 필터 · T22-23 `table.matrix{` · T22-40 · T22-44 · T22-45 · T22-49 · T22-50 | 통과 유지 | 선택자·클래스명을 바꾸지 않으므로 무영향. **바꾸지 않는 것이 요구다** |
| T22-58 역방향(`body.dz-pip #dz-impl-card{display:none}` 부재) | 통과 유지 | 새 규칙을 추가하지 않는다 |
| T22-31/32(PiP 기능 감지·`requestWindow` **1줄**) | 통과 유지 | 테마 코드는 `documentPictureInPicture.window` 만 참조하고 `requestWindow` 를 쓰지 않는다 |
| T22-33/34(스타일 복사·PiP 이동/복귀) | 통과 유지 | 한 줄 추가일 뿐 기존 문자열 불변 |
| T22-38 역방향(`[id="dz-` 부재) | 통과 유지 | 새 코드는 `getElementById` 만 쓴다 |
| T22-84 역방향(`<script>` 범위에 `data-server-port` 부재) | 통과 유지 | `<head>` 스크립트가 늘어도 두 블록 모두 해당 문자열이 없다 |
| T22-85 역방향(`poll()` 범위에 `close()`/`reload` 부재) | 통과 유지 | 테마 코드는 그 범위 밖 |
| T22-37(플로팅 UI 가 `#dz-updated` 뒤) | 통과 유지 | 클러스터도 `.wrap` 바깥이라 줄 번호 비교가 그대로 성립 |
| 999·1002 범위 문구 | 갱신 | `T22-1~T22-104` → 새 최댓값 |

### 9.2 신규 하위 검증 (T22-105~, `log_ok` 직전에 추가)

| 번호 | 검사 | 막는 회귀 |
|------|------|----------|
| T22-105 | `prefers-color-scheme` **와** `:root[data-theme="dark"]` 가 둘 다 존재 | 한쪽만 남아 `localStorage` 차단 환경 또는 수동 오버라이드가 죽는다(T25-28 대칭) |
| T22-106 | `'dz-theme'` 리터럴이 2회 이상(head 스크립트 + 본문 IIFE) | head 스크립트는 자족적이어야 해 상수 공유가 불가능하다 — 한쪽 유실 감지 |
| T22-107 | `data-theme` 설정이 `<head>` 스크립트에 존재하고 그 줄이 `<body>` 줄보다 **앞** | FOUC 방지 스크립트가 본문으로 밀려나는 회귀(줄 번호 비교, T22-37 방식) |
| T22-108 | `id="dz-theme-toggle"` 의 마지막 등장이 `id="dz-updated"` 보다 **뒤** | 토글이 `.wrap` 안으로 들어가 PiP 창으로 딸려가는 회귀 |
| T22-109 | `body.dz-embedded #dz-theme-toggle` 규칙 존재 | 모달 안에 허브와 중복되는 토글이 남는 회귀 |
| T22-110 | PiP 분기에 `pipDocument.documentElement.setAttribute('data-theme'` 존재 | 다크에서 플로팅 창만 흰 화면이 되는 회귀 |
| T22-111 | 역방향 — `#E5F3EE` `#EAF2FB` `#FBE9E2` `#E7EAF3` `#2D78C8` `#4B5A6D` `#1F8A70` `#C2410C` `#F59E0B` 부재 | 토큰화한 자리에 리터럴이 다시 기어들어오는 회귀(T25-29 대칭) |
| T22-112 | `'dzh-theme'` 리터럴이 존재(권장안 D 채택 시) + `setItem('dzh-theme'` **부재** | 허브 키를 대시보드가 **쓰는** 회귀(단방향 읽기 계약 위반) |
| T22-113 | 문서 정합 — 「정적 요소」 표에 `#dz-theme-toggle` 행, 폴링 계약 표에 `data-theme` 언급 | 코드만 바뀌고 스펙 문서가 뒤처지는 회귀(제약 1) |

### 9.3 순수 로직 단위 테스트

이 변경에는 새 순수 함수가 없다(테마 결정 로직은 브라우저 `localStorage`/`matchMedia` 에
직접 닿는 12줄이며, 대시보드에는 JS 테스트 하네스가 없다). `tests/run.sh` 의 grep 계약이
이 저장소의 등가 수단이다 — 허브의 순수 로직(`hub_usage.py` 등)이 파이썬 단위 테스트를 갖는
것과 대비되는 구조적 차이이며, 새 하네스를 도입하지 않는다(YAGNI).

### 9.4 수동 확인 (자동화 대상 아님)

1. `/dashboard init` → 단독 탭에서 라이트/다크 토글, 새로고침 후 유지.
2. 시스템 다크 + 저장값 없음 → 첫 로드가 **번쩍임 없이** 다크.
3. 다크 상태에서 플로팅 진입 → PiP 창이 다크. 열린 채로 토글 → 두 창이 함께 바뀐다.
4. 허브를 다크로 두고 카드 클릭 → 모달 안 대시보드가 다크. 모달을 연 채 허브 토글 → 즉시 추종.
5. 허브를 **수동 라이트**(시스템은 다크)로 두고 모달 → 대시보드도 라이트.
6. 라이트·다크 각각에서 완료/진행중/대기 칸, PASS/FAIL/커밋 배지가 서로 구분되는지(§5.4 검증 항목).
7. 키보드 Tab 으로 필터 라디오·토글·플로팅 버튼의 포커스 링이 보이는지.

---

## 10. 구현 순서와 GOTCHA

**순서**: ① `<style>` 토큰 3블록 + 규칙 치환(§5) → ② `<head>` 스크립트·`<meta>`(§6.2) →
③ 마크업 클러스터·토글(§6.3) → ④ 테마 IIFE(§6.4) → ⑤ PiP 전파(§6.5) →
⑥ `dashboard.md` 산문·CSS 사본 동기화(§8) → ⑦ `tests/run.sh` 갱신(§9) → ⑧ `bash tests/run.sh`.

- **GOTCHA 1 — 허브 파서가 읽는 6줄은 건드리지 않는다.** `hub_parse.py` 는
  `<h1 id="dz-title">…</h1>` · `id="dz-progress-pct"` · `id="dz-updated">` ·
  `<li id="dz-step-N" class="…"` · `<td class="cell" id="dz-cell-…"` ·
  `<li id="dz-impl-N" class="…"` 를 정규식으로 맞춘다. **`<h1>` 에 클래스를 붙이거나 감싸면
  허브에서 이 프로젝트가 티어 2로 조용히 강등된다.** 토글을 `.wrap` 바깥에 두는 설계가 이
  문제를 구조적으로 피한다.
- **GOTCHA 2 — 새 코드에 `isEmbedded` 문자열을 쓰지 않는다.** T22-99 가
  `grep -c 'isEmbedded'` 로 **정확히 2줄**을 요구한다. 부분 문자열이라 `isEmbeddedInHub` 같은
  함수명도 카운트에 걸린다. `<head>` 스크립트와 테마 IIFE 는 `window.self !== window.top` 을
  각자 인라인으로 쓰거나 다른 이름(`embedded`)을 쓴다.
- **GOTCHA 3 — `body.dz-embedded` 는 선택자를 나열한다.** `#dz-top-actions` 하나로 묶어
  숨기면 T22-97 의 `grep -qF 'body.dz-embedded #dz-pip-btn'` 이 실패한다.
- **GOTCHA 4 — 기존 IIFE 는 세 곳에서 조기 `return` 한다**(`file://` 분기 1231행, PiP 미지원
  1311-1316행). 테마 코드를 그 안에 넣으면 `file://` 에서 테마가 죽는다. **반드시 별도 IIFE**,
  그리고 폴링 IIFE **뒤**에 둔다(앞에 두면 테마 예외가 폴링을 통째로 죽인다).
- **GOTCHA 5 — CSS 사본이 3벌이다.** 매트릭스 CSS(341-359 / 1112-1120), 필터 CSS
  (1035-1040 / 1127-1131). 한쪽만 고치면 문서와 코드가 어긋난다(제약 1).
- **GOTCHA 6 — `init` 절차의 Edit 은 "템플릿 줄 전문 그대로"를 `old_string` 으로 쓴다**(378-382행).
  `#dz-title`·`#dz-progress-bar`·`#dz-progress-pct`·`#dz-updated`·`<ol class="steps" id="dz-steps">`
  줄의 **문자열을 바꾸지 않는다**. §5 매핑에 이 줄들이 없는 것은 우연이 아니다.

---

## 11. 리스크와 대안

### 리스크

| # | 리스크 | 완화 |
|---|--------|------|
| R1 | 완료색이 초록→파랑 틴트로 바뀌어 익숙한 신호가 달라진다 | 텍스트 라벨(`완료`)은 그대로다. 승인 항목 1 로 명시 확인 |
| R2 | 다크에서 완료(`--accent-soft`)와 대기(`--soft`)의 명도차가 작다 | §5.4 검증 항목 + 실측 후에만 적용할 예비안(inset ring) |
| R3 | T22-27 의 "완전 일치" 안전망을 푸는 것이 임의 팔레트 변경의 문을 연다 | 토큰명 정방향 + 구 토큰·비안전 리터럴 역방향 **3중** 검사로 대체(§9.1). 안전망의 성격만 바뀌고 강도는 유지 |
| R4 | 허브가 `dzh-theme` 키를 개명하면 모달 동기화가 조용히 끊긴다 | 실패 모드가 "시스템 선호로 낙착"이라 화면이 깨지지 않는다. T22-112 가 대시보드 쪽 계약을, 허브 쪽은 T25-28 이 키 존재를 이미 고정한다 |
| R5 | README 스크린샷(`docs/images/dashboard-sample.png`)이 구식이 된다 | 승인 항목 3 — 재촬영 여부를 사용자가 정한다(자동화 불가) |
| R6 | `<style>` 이 커져 매 `init` 마다 Write 하는 바이트가 늘어난다 | 토큰 블록 3개 ≈ 20줄 증가. `init` 은 세션당 1회이며 이 도구의 병목은 Bash/Edit **호출 횟수**지 파일 크기가 아니다 |

### 검토했으나 채택하지 않은 대안

- **대안 1 — CSS 를 공용 파일로 추출해 두 화면이 공유한다.** 기각. 대시보드는 마크다운 안
  리터럴을 Write 하는 산출물이고 허브는 파이썬이 렌더하는 산출물이라 배포 경로가 다르며,
  둘 다 `file://` 단독 실행이 요구사항이다. 공유 파일은 두 배포 경로를 모두 복잡하게 만들고
  얻는 것은 중복 제거뿐이다.
- **대안 2 — 다크 값만 추가하고 초록·빨강은 유지한다.** 기각. `#E5F3EE`·`#FBE9E2` 같은
  틴트 배경은 다크에서 그대로 쓸 수 없어 결국 `--green-soft-dark` 류 토큰을 새로 만들어야
  하고(토큰 수 2배), 색각 안전 전제(전제 2)와 정면으로 충돌한다.
- **대안 3 — 토글 없이 `prefers-color-scheme` 만 따른다(안 C).** 기각. 허브가 수동
  오버라이드를 제공하는데 대시보드만 없으면 같은 화면 안에서 어긋난다 — 이 PRP 가 없애려는
  바로 그 불일치다.

---

## 12. 사용자 승인이 필요한 항목

1. **팔레트 전면 이식 여부(S5).** 초록(`완료`/`PASS`)·빨강(`FAIL`)을 폐기하고 파랑 채움
   사다리 + 주황 경고로 재배치한다. → **권장: 채택**(전제 2, 두 화면이 한 뷰포트에서 겹침).
   보류하면 다크 모드는 반쪽이 되고 T22-27 은 어차피 손대야 한다.
2. **iframe 테마 동기화 방식(§7).** → **권장: 안 D**(임베드 시 허브 키를 읽기 전용 참조 +
   `storage` 이벤트). 허브 파일 **무변경**, FOUC 없음, 실패 시 시스템 선호로 낙착.
   안 B 를 고르면 `hub_server.py` 의 경로 정규식까지 열어야 한다.
3. **부수 항목 3건.** ① 토글에 `.icon-btn` 클래스를 둘지 `#dz-theme-toggle` 직접 스타일로
   둘지 ② README 스크린샷 재촬영 여부 ③ README 커맨드 표의 줄 수(이미 `1224` vs 실제 `1358`
   로 어긋나 있음)를 이번에 같이 고칠지.
