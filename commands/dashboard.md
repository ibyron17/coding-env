---
description: "세션 진행 상황을 프로젝트 로컬 HTML 대시보드로 기록 — init/step/log 세 하위 명령"
argument-hint: "init \"<제목>\" \"<단계1|단계2|...>\" | step <n> <done|active|wait> [...] | log <impl|pass|fail|commit> \"<요약>\" [...]"
---

# Dashboard

> 개발 세션의 진행 상황을 브라우저에서 확인할 수 있는 단일 HTML 파일을 유지한다.
> 실행 주체는 **메인 세션(오케스트레이터)뿐**이다. 서브에이전트는 이 파일에 접근하지 않는다.
> 별도 상태 파일(JSON)은 두지 않는다 — `.claude/dashboard.html` 의 DOM 자체가 상태다.
> 설계 근거: [`docs/prps/session-dashboard.md`](../../docs/prps/session-dashboard.md)

**적용 범위**: 전체 경로(설계 → 구현 → 검수) 작업에만 사용한다. 축약 경로는 단계가 둘뿐이라 과하다.

**Input**: `$ARGUMENTS` (첫 토큰이 `init` | `step` | `log`)

---

## 호출 규약

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard step <n> <done|active|wait> ["현재 위치"] ["다음 단계"] ["담당 에이전트 · 모델"]
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
```

## CLAUDE.md 트리거 (메인 세션 전용, 참고)

| 시점 | 호출 |
|------|------|
| 전체 경로 착수 보고 시 | `init` |
| PRP 작성 완료 | `step 1 done` + `log impl` |
| 사용자 승인 수령 | `step 2 done` + `step 3 active` |
| 구현 완료 | `step 3 done` + `log impl` |
| 검수 PASS / FAIL | `step 4 done|wait` + `log pass|fail` |
| 커밋·푸시 | `log commit` |

---

## 데이터 모델 — DOM 상 표현 규격

상태는 아래 셀렉터와 속성으로만 표현한다. 이 표가 이 문서와 HTML 사이의 계약이다.

### 정적(불가침)

`<style>` 블록, `:root` 색 토큰, 카드 골격, 로그 카드의 범례(4종 배지 샘플), 하단 스크립트.

### 동적(치환 대상) — 11 셀렉터

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-subtitle` | 텍스트 | 단계 흐름 요약 · 작업 유형 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` | `class` 속성 + 자식 `.chip` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` |
| `#dz-current` | 텍스트 | 현재 위치 한 줄 |
| `#dz-current-meta` | 텍스트 | `implementer · sonnet` |
| `#dz-current-clock` | `data-started-at` 속성 | 현재 단계 착수 시각(ISO 8601) |
| `#dz-next` | 텍스트 | 다음 단계 한 줄 |
| `#dz-log` | 자식 `<li>` **prepend** | 로그 항목 (최신이 위) |
| `#dz-updated` | 텍스트 | 갱신 시각 |

### 로그 항목 스키마

```html
<li class="entry" data-kind="review" data-seq="12">
  <details open>
    <summary>
      <span class="time">17:07</span>
      <span class="badge round">R2</span>
      <span class="badge fail">검수 FAIL</span>
      <span class="lead">applyGap margin 직할당 → 중첩 경계에서 외부 간격이 내부 패딩을 덮어씀</span>
    </summary>
    <div class="detail">검수자 32px→12px 재현. buildChipBadge·runBottom 은 통과. margin 누적으로 전환 지시.</div>
  </details>
</li>
```

- `data-seq` — 1부터 증가하는 정수. **필터·펼침 제어의 유일 키**이자 Edit 문자열 매칭의 앵커
- `data-kind` — `impl` \| `review` \| `commit` \| `note` (필터 대상). `note` 는 `/dashboard log` 가 생성하지
  않는(수동 편집 전용) 예비 값이다.
- `.badge.round` — 회차(`R1`, `R2`…). `--round` 인자가 없는 항목은 생략한다.
- `log` 하위 명령의 결과 유형과 `data-kind`·배지의 대응:

| `log` 인자 | `data-kind` | 배지 class | 배지 라벨 | 색(토큰) |
|-----------|-------------|-----------|----------|---------|
| `impl` | `impl` | `.badge.impl` | 구현 | `--blue` |
| `pass` | `review` | `.badge.pass` | 검수 PASS | `--green` |
| `fail` | `review` | `.badge.fail` | 검수 FAIL | `--red`(신규 토큰 `#C2410C`) |
| `commit` | `commit` | `.badge.commit` | 커밋 | `--navy` |

---

## `init` — 메인 세션이 수행할 절차

1. `.claude/` 디렉토리가 없으면 생성한 뒤, 아래 [템플릿 전문](#템플릿-전문)을 그대로
   `.claude/dashboard.html` 로 Write 한다.
2. `#dz-title` 텍스트를 `<제목>` 인자로 치환한다.
3. `#dz-subtitle` 텍스트를 `"<단계1> → <단계2> → ... · <작업 유형>"` 형식으로 치환한다.
   작업 유형(예: "전체 경로")은 호출한 오케스트레이터가 이미 알고 있는 값을 채운다.
4. `<단계1|단계2|...>` 를 `|` 로 분리해 개수 N을 구한다. 템플릿의
   `<ol class="steps" id="dz-steps">...</ol>` 내부를 아래 패턴으로 N개 생성한 `<li>` 로 통째로 치환한다
   (1번은 `active`, 나머지는 `wait`):
   ```html
   <li id="dz-step-{n}" class="{active|wait}"><span class="num">{n}</span>{단계명}<span class="chip">{진행중|대기}</span></li>
   ```
5. `#dz-progress-bar` 의 `style` 을 `width:0%` 로, `#dz-progress-pct` 텍스트를 `0/N · 0%` 로 치환한다.
6. `#dz-current` 를 첫 단계명으로, `#dz-next` 를 두 번째 단계명(없으면 `-`)으로 치환한다.
7. `#dz-updated` 를 현재 시각(예: `2026-08-04 17:02`)으로 치환한다.
8. `#dz-log` 는 템플릿 그대로 빈 목록(`<ul class="log" id="dz-log"></ul>`)으로 둔다 — 아직 로그가 없다.
9. 사용자에게 `file://<현재 작업 디렉토리 절대경로>/.claude/dashboard.html` 을 출력해
   브라우저로 열도록 안내한다.

## `step` — 메인 세션이 수행할 절차 (Edit 3~5회)

1. `#dz-step-{n}` 의 `class` 속성과 자식 `.chip` 텍스트를 새 상태로 치환한다
   (`done`/`완료`, `active`/`진행중`, `wait`/`대기`).
2. 이번 치환으로 `done` 이 된 경우, 완료 단계 수를 세어 `#dz-progress-bar` 의 `style="width:N%"`
   와 `#dz-progress-pct` 텍스트(`M/N · P%`)를 재계산해 치환한다.
3. `["현재 위치"]` · `["다음 단계"]` · `["담당 에이전트 · 모델"]` 인자가 주어졌으면 각각
   `#dz-current` · `#dz-next` · `#dz-current-meta` 텍스트를 치환한다.
4. 이번 치환으로 `active` 가 된 경우, `#dz-current-clock` 의 `data-started-at` 속성을
   현재 ISO 8601 시각으로 치환한다.
5. `#dz-updated` 텍스트를 현재 시각으로 치환한다.

## `log` — 메인 세션이 수행할 절차 (Edit 2회, 결정적)

0. `.claude/dashboard.html` 을 Read 해 현재 존재하는 `data-seq` 값 중 최댓값 `S` 를 확인한다
   (로그가 비어 있으면 `S=0`).
1. **직전 펼침 회수**: `data-seq="S-2"` 인 `<li>` 가 존재하면, 그 안의 `<details open>` 를
   `<details>` 로 치환한다(연 상태 해제). 해당 seq 가 없으면(로그 3건 미만) 이 단계를 생략한다.
   → 결과적으로 **항상 최신 3건만 펼쳐진다.**
2. **prepend**: `<ul class="log" id="dz-log">` 여는 태그 바로 뒤에 `data-seq="S+1"` 인 새
   `<li>` 를 위 [로그 항목 스키마](#로그-항목-스키마)대로 삽입한다.
   - `data-kind` 는 위 대응표를 따른다.
   - `--round N` 이 주어졌으면 `<span class="badge round">R{N}</span>` 을 결과 배지 앞에 넣는다.
     없으면 이 배지를 생략한다.
   - `["상세"]` 가 주어지지 않았으면 `.detail` 내용은 `(상세 없음)` 으로 채운다.
   - `<span class="time">` 은 현재 시각의 `HH:MM` 만 채운다.
   - **이스케이프**: `"<한 줄 요약>"`·`["상세"]` 를 `.lead`·`.detail` 에 넣기 전에
     `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` 순서로 치환한다. 코드 조각(`Foo<T>`, `a && b` 등)이
     그대로 삽입되면 태그가 깨진다.

`data-seq` 가 문서 내 유일 문자열이므로 두 치환 모두 앵커가 명확하고, 순번을 세는 판단이
개입하지 않는다.

---

## 로그 UI 규격

### 접기

`<details>`/`<summary>` 로 요약 한 줄과 상세를 분리한다. `.lead` 는 1줄로 자른다
(`overflow:hidden; text-overflow:ellipsis; white-space:nowrap`). `.detail` 은 펼쳤을 때
줄바꿈을 허용한다.

### 펼침 정책

최신 3건만 `open`. 제어는 위 `log` 절차 1~2단계로만 이뤄진다. CSS 로는 `details` 의 열림
상태를 판단해 바꿀 수 없으므로 속성 치환으로만 처리한다.

### 필터 — JS 없이 CSS 로

라디오 3개를 `#dz-log` 의 **앞 형제**(같은 부모의 직전 형제들)로 둔다. 래퍼 `div` 로 감싸면
`~` 결합자가 `#dz-log` 에 닿지 않으므로 감싸지 않는다.

```html
<input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
<input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
<input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
<ul class="log" id="dz-log">…</ul>
```

```css
.dzf{position:absolute;opacity:0;pointer-events:none}
#dzf-impl:checked   ~ #dz-log .entry:not([data-kind="impl"]){display:none}
#dzf-review:checked ~ #dz-log .entry:not([data-kind="review"]){display:none}
```

라디오는 시각적으로 숨기되 포커스는 유지한다(`display:none` 이 아니라 `opacity:0`).
`:has()` 같은 최신 셀렉터에 의존하지 않으므로 지원 범위가 넓다.

### 현재 task 카드

```html
<div class="slot">
  <b>현재 위치</b>
  <span id="dz-current">…</span>
  <div class="meta"><span id="dz-current-meta">implementer · sonnet</span>
       · <span id="dz-current-clock" data-started-at="2026-08-04T17:02:00+09:00"></span></div>
</div>
```

경과 시간은 정적 HTML 로 표현할 수 없으므로 하단 스크립트에 아래 4줄이 포함돼 있다(순수 표시용):

```js
function _dzElapsed(){ var el=document.getElementById('dz-current-clock'); if(!el) return;
  var m=Math.floor((Date.now()-new Date(el.dataset.startedAt))/60000);
  el.textContent = m<60 ? m+'분 경과' : Math.floor(m/60)+'시간 '+(m%60)+'분 경과'; }
_dzElapsed(); setInterval(_dzElapsed, 30000);
```

원본(`~/Desktop/dashboard.html`)의 골격·`:root` 색 토큰·단계 리스트 스타일은 그대로 유지한다.

---

## 템플릿 전문

`init` 절차 1단계에서 이 내용을 그대로 `.claude/dashboard.html` 로 Write 한다.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>세션 진행 상황 대시보드</title>
<!--
DZ:DASHBOARD 갱신 맵 (동적 영역 — 셀렉터 기반 정밀 치환, commands/dashboard.md 참조)
  #dz-title            : 세션 제목 텍스트
  #dz-subtitle          : 단계 흐름 요약 · 작업 유형 텍스트
  #dz-progress-bar      : inline style width:N%
  #dz-progress-pct      : 진행률 텍스트 (예: 3/6 · 50%)
  #dz-step-{n}          : 각 단계 li — class(done|active|wait) + .chip 텍스트(완료|진행중|대기)
  #dz-current           : 현재 위치 텍스트
  #dz-current-meta      : 담당 에이전트 · 모델 텍스트
  #dz-current-clock     : data-started-at 속성 (ISO 8601)
  #dz-next              : 다음 단계 텍스트
  #dz-log               : 작업 추적 ul — li data-seq 앵커로 prepend
  #dz-updated           : 갱신 시각 텍스트
정적(불가침): 골격 · <style> · 범례 · 제목 · 하단 스크립트
-->
<style>
  :root{--ink:#172033;--muted:#5E6B7D;--line:#D9E2EC;--soft:#F4F7FB;--blue:#1E5AA8;--navy:#12335B;--green:#1F8A70;--orange:#F59E0B;--red:#C2410C;}
  *{box-sizing:border-box}
  body{margin:0;font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:var(--ink);background:#EEF3F8;line-height:1.55}
  .wrap{max-width:860px;margin:32px auto;padding:0 16px}
  .card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:26px 30px;box-shadow:0 8px 24px rgba(19,51,91,.07);margin-bottom:16px}
  h1{font-size:21px;margin:0 0 4px;color:var(--navy);letter-spacing:-.5px}
  .sub{font-size:13px;color:var(--muted);margin-bottom:18px}
  .bar-outer{height:14px;background:var(--soft);border-radius:999px;overflow:hidden;border:1px solid var(--line)}
  .bar-inner{height:100%;background:linear-gradient(90deg,var(--blue),#2D78C8);border-radius:999px;transition:width .4s}
  .pct{font-size:13px;font-weight:700;color:var(--blue);margin-top:6px}
  ol.steps{list-style:none;margin:14px 0 0;padding:0}
  ol.steps li{display:flex;align-items:center;gap:12px;padding:11px 4px;border-bottom:1px solid var(--soft);font-size:15px}
  ol.steps li:last-child{border-bottom:0}
  .num{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:13px;font-weight:800;background:var(--soft);color:var(--muted);flex:none}
  li.done .num{background:var(--green);color:#fff}
  li.active .num{background:var(--blue);color:#fff}
  li.done{color:var(--muted)}
  li.active{font-weight:700;color:var(--navy)}
  .chip{margin-left:auto;font-size:12px;font-weight:800;padding:3px 10px;border-radius:999px;background:var(--soft);color:var(--muted);flex:none}
  li.done .chip{background:#E5F3EE;color:var(--green)}
  li.active .chip{background:#EAF2FB;color:var(--blue)}
  .duo{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .slot{background:var(--soft);border-radius:10px;padding:13px 16px;font-size:14px}
  .slot b{display:block;font-size:12px;color:var(--muted);margin-bottom:4px;font-weight:700}
  .slot .meta{margin-top:6px;font-size:12px;color:var(--muted)}
  .legend{margin:10px 0 12px}
  .badge{display:inline-block;font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;margin-right:6px}
  .badge.round{background:var(--soft);color:var(--muted)}
  .badge.impl{background:#EAF2FB;color:var(--blue)}
  .badge.pass{background:#E5F3EE;color:var(--green)}
  .badge.fail{background:#FBE9E2;color:var(--red)}
  .badge.commit{background:#E7EAF3;color:var(--navy)}
  .dzf{position:absolute;opacity:0;pointer-events:none}
  label[for^="dzf-"]{display:inline-block;font-size:12px;font-weight:700;padding:4px 12px;margin:8px 6px 8px 0;border-radius:999px;background:var(--soft);color:var(--muted);cursor:pointer;border:1px solid var(--line)}
  .dzf:checked + label{background:var(--blue);color:#fff;border-color:var(--blue)}
  #dzf-impl:checked   ~ #dz-log .entry:not([data-kind="impl"]){display:none}
  #dzf-review:checked ~ #dz-log .entry:not([data-kind="review"]){display:none}
  ul.log{list-style:none;margin:6px 0 0;padding:0;font-size:13px;color:#4B5A6D}
  .entry{border-bottom:1px solid var(--soft);padding:8px 4px}
  .entry:last-child{border-bottom:0}
  .entry summary{cursor:pointer;display:flex;align-items:center;gap:8px;list-style:none}
  .entry summary::-webkit-details-marker{display:none}
  .entry summary::marker{content:""}
  .entry .time{font-size:11px;color:var(--muted);flex:none;width:40px}
  .entry .lead{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;color:var(--ink)}
  .entry .detail{margin:6px 0 0 48px;font-size:12.5px;color:var(--muted);white-space:pre-wrap}
  .foot{font-size:12px;color:var(--muted);text-align:right}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1 id="dz-title">세션 제목</h1>
    <div class="sub" id="dz-subtitle">단계 흐름 요약 · 작업 유형</div>
    <div class="bar-outer"><div class="bar-inner" id="dz-progress-bar" style="width:0%"></div></div>
    <div class="pct" id="dz-progress-pct">0/0 · 0%</div>
    <ol class="steps" id="dz-steps">
    </ol>
  </div>
  <div class="card duo">
    <div class="slot">
      <b>현재 위치</b>
      <span id="dz-current">-</span>
      <div class="meta"><span id="dz-current-meta">-</span> · <span id="dz-current-clock" data-started-at=""></span></div>
    </div>
    <div class="slot">
      <b>다음 단계</b>
      <span id="dz-next">-</span>
    </div>
  </div>
  <div class="card">
    <b style="font-size:13px;color:var(--muted)">작업 추적</b>
    <div class="legend">
      <span class="badge impl">구현</span><span class="badge pass">검수 PASS</span><span class="badge fail">검수 FAIL</span><span class="badge commit">커밋</span>
    </div>
    <input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
    <input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
    <input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
    <ul class="log" id="dz-log"></ul>
  </div>
  <div class="foot" id="dz-updated">갱신: -</div>
</div>
<script>
  // 탭으로 돌아오거나 창에 포커스가 오면 최신 파일로 자동 새로고침 (새 탭 안 띄움)
  var _dzReloading=false; function _dzReload(){ if(_dzReloading) return; _dzReloading=true; location.reload(); }
  document.addEventListener('visibilitychange', function(){ if(document.visibilityState==='visible') _dzReload(); });
  window.addEventListener('focus', _dzReload);

  // 현재 단계 경과 시간 표시 (순수 표시용, data-started-at 은 메인 세션이 치환)
  function _dzElapsed(){ var el=document.getElementById('dz-current-clock'); if(!el) return;
    var m=Math.floor((Date.now()-new Date(el.dataset.startedAt))/60000);
    el.textContent = m<60 ? m+'분 경과' : Math.floor(m/60)+'시간 '+(m%60)+'분 경과'; }
  _dzElapsed(); setInterval(_dzElapsed, 30000);
</script>
</body>
</html>
```
