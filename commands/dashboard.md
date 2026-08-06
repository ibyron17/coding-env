---
description: "세션 진행 상황을 프로젝트 로컬 HTML 대시보드로 기록 — init/step/log + on/off 스위치"
argument-hint: "init \"<제목>\" \"<단계1|...> 또는 <그룹A:단계1,단계2|그룹B:...>\" | step <n>|<g>.<p> <done|active|wait> [\"상세\"] | log <impl|pass|fail|commit> \"<요약>\" [...] | serve [포트] | on | off"
---

# Dashboard

> 개발 세션의 진행 상황을 브라우저에서 확인할 수 있는 단일 HTML 파일을 유지한다.
> 실행 주체는 **메인 세션(오케스트레이터)뿐**이다. 서브에이전트는 이 파일에 접근하지 않는다.
> 별도 상태 파일(JSON)은 두지 않는다 — `.claude/dashboard.html` 의 DOM 자체가 상태다.
> 설계 근거: [`docs/prps/session-dashboard.md`](../../docs/prps/session-dashboard.md)

**적용 범위**: 전체 경로(설계 → 구현 → 검수) 작업에만 사용한다. 축약 경로는 단계가 둘뿐이라 과하다.

**Input**: `$ARGUMENTS` (첫 토큰이 `init` | `step` | `log` | `on` | `off`)

---

## 호출 규약

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard init "<제목>" "<그룹A:단계1,단계2|그룹B:단계1,단계2>"
/dashboard step <n> <done|active|wait> ["상세"]    # 그룹 1개 — 단계 번호. 상세는 선택
/dashboard step <g>.<p> <done|active|wait>         # 그룹 2개 이상 — 행.열 (상세 미지원)
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
/dashboard serve [포트] | serve stop        # 플로팅용 로컬 정적 서버 (opt-in)
/dashboard on | off
```

`step` 의 첫 인자에 `.` 이 있으면 매트릭스 칸, 없으면 선형 단계다. 인덱스는 모두 1부터 시작한다.

## CLAUDE.md 트리거 (메인 세션 전용, 참고)

| 시점 | 호출 |
|------|------|
| 전체 경로 착수 보고 시 | `init` |
| PRP 작성 완료 | `step 1 done` + `log impl` |
| 사용자 승인 수령 | `step 2 done` + `step 3 active` |
| 구현 완료 | `step 3 done` + `log impl` |
| 검수 PASS / FAIL | `step 4 done|wait` + `log pass|fail` |
| 커밋·푸시 | `log commit` |

> 그룹 모드에서는 `step <n>` 자리에 `step <g>.<p>` 를 쓴다. 한 단계가 여러 그룹에 걸쳐 끝나면
> 그룹 수만큼 호출한다(칸 단위 갱신이 곧 진행률의 단위다).

> `step` 의 네 번째 인자로 한 줄 상세를 붙이면(예: `step 3 active "폴링 스크립트 작성 중"`) 그 단계가
> 지금 무엇을 하고 있는지가 대시보드에 바로 보인다. 생략해도 되며, 생략하면 기존 상세가 유지된다.

---

## 데이터 모델 — DOM 상 표현 규격

상태는 아래 셀렉터와 속성으로만 표현한다. 이 표가 이 문서와 HTML 사이의 계약이다.

### 정적(불가침)

`<style>` 블록, `:root` 색 토큰, 카드 골격, 하단 스크립트.

### 동적(치환 대상) — 7 셀렉터

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-subtitle` | 텍스트 | 단계 흐름 요약 · 작업 유형 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` **(그룹 1개)** | `class` 속성 + 자식 `.chip` 텍스트 + 자식 `.step-detail` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` / 한 줄 상세(빈 문자열 허용) |
| `#dz-cell-{g}-{p}` **(그룹 2개 이상)** | `data-state` 속성 + 칸 텍스트 | `done`\|`active`\|`wait`\|`na` / `완료`\|`진행중`\|`대기`\|`–` |
| `#dz-log` | 자식 `<li>` **prepend** + `data-current-session` 속성 | 로그 항목(최신이 위) / 현재 세션 번호 |
| `#dz-updated` | 텍스트 | 갱신 시각 |

진행 시각화 행은 **렌더링 분기에 따라 둘 중 하나**만 존재한다(셀렉터 개수는 여전히 7이며,
한 파일 안에 `#dz-step-*` 과 `#dz-cell-*` 이 공존하지 않는다). 문법·모드 판정·매트릭스 마크업은
아래 [진행 시각화 규격](#진행-시각화-규격--그룹--단계-모델) 참조.

**init 시점에만 생성되고 이후 치환되지 않는 구조 요소** (위 표에 넣지 않는다):

- `#dz-matrix` — 매트릭스 `<table>` 자체
- `#dz-group-{g}` — 행 머리 `<th>`. 그룹명 텍스트를 담는다

**불변식 (이 두 가지가 깨지면 `step` 의 결정성이 무너진다)**

1. **한 파일에 `#dz-step-*` 과 `#dz-cell-*` 이 동시에 존재하지 않는다.** `init` 이 둘 중 하나만 만든다.
2. **`<li id="dz-step-…">` 와 `<td id="dz-cell-…">` 는 반드시 한 줄에 하나씩 생성한다.**
   `step` 의 완료 칸 카운트가 `grep -c`(줄 단위 계수)에 의존하기 때문이다.
3. **`.step-detail` 의 내용에 줄바꿈이 들어가지 않는다.** `<li>` 가 여러 줄로 쪼개지면 불변식 2가
   깨지고, `step` 0단계의 grep 앵커와 감사용 `grep -c 'dz-step-.*class="done"'` 가 동시에 어긋난다.
4. **`#dz-log-card` 는 CSS 로만 감춘다.** 스크립트가 이 id 를 `getElementById`/`querySelector` 로
   참조하지 않는다.

`data-current-session` 은 새 행이 아니라 `#dz-log` 행의 하위 개념이다 — `log` 절차가
어차피 매번 grep 하는 `#dz-log` 여는 태그에 얹혀 있어 탐색 단계를 늘리지 않는다
(`<ul class="log" id="dz-log" data-current-session="2">`). `init` 이 세션 시작 때 갱신하고
`log` 는 읽기만 한다. 속성이 없는 파일(세션 탭 도입 이전에 만들어진 대시보드)은 `1` 로 간주한다.

### 로그 항목 스키마

```html
<li class="entry" data-kind="review" data-seq="12" data-session="2">
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
- `data-session` — 이 항목이 속한 세션 번호(**세션 탭 필터 대상**). `log` 절차가 `#dz-log` 의
  `data-current-session` 값을 **그대로 복사**해 넣는다. 세거나 추론하는 판단이 개입하지 않는다.
- `.badge.round` — 회차(`R1`, `R2`…). `--round` 인자가 없는 항목은 생략한다.
- `log` 하위 명령의 결과 유형과 `data-kind`·배지의 대응:

| `log` 인자 | `data-kind` | 배지 class | 배지 라벨 | 색(토큰) |
|-----------|-------------|-----------|----------|---------|
| `impl` | `impl` | `.badge.impl` | 구현 | `--blue` |
| `pass` | `review` | `.badge.pass` | 검수 PASS | `--green` |
| `fail` | `review` | `.badge.fail` | 검수 FAIL | `--red`(신규 토큰 `#C2410C`) |
| `commit` | `commit` | `.badge.commit` | 커밋 | `--navy` |

### 갱신 모드 — 런타임에 결정되는 두 갈래

```
UpdateMode
  "reload"  : location.protocol 이 http(s) 가 아님 (file://, 기타)
  "poll"    : location.protocol 이 http: 또는 https:
```

- 판정 기준은 **프로토콜 한 가지뿐**이다. `fetch` 성공 여부로 추론하거나, 실패 후 폴백하는 구조를
  만들지 않는다(판정이 비결정적이 되고 실패 경로가 둘로 늘어난다).
- `reload` 모드의 코드 경로는 **현재 스크립트와 의미상 동일**해야 한다. 플로팅 버튼은 비활성이다.
- 플로팅 가능 조건 = `mode === "poll"` **AND** `'documentPictureInPicture' in window`.
  둘 중 하나라도 아니면 버튼은 `disabled` 이고 `#dz-pip-hint` 가 사유 한 줄을 보여준다.

### 정적 요소 추가 (동적 셀렉터 표에 넣지 않는다)

`init`/`step`/`log` 가 절대 치환하지 않고, **폴링도 동기화하지 않는** 요소다.

| 요소 | 역할 |
|------|------|
| `#dz-pip-btn` | 플로팅 진입/종료 버튼. `.wrap` **바깥**(`<body>` 직계)에 둔다 |
| `#dz-pip-hint` | 상태·사유 한 줄. 기본 `hidden`, 스크립트가 텍스트를 넣을 때만 노출 |
| `body.dz-pip` | PiP 창 문서의 `<body>` 에만 붙는 클래스. 좁은 창용 여백 축소 규칙의 스코프 |
| `#dz-log-card` | 「작업 추적」 카드 `<div>`. `init`/`step`/`log` 도, 폴링도 이 요소 자체를 치환하지 않는다. PiP 압축 뷰가 CSS 로 숨기기 위한 유일한 용도이며, DOM 에서 제거하지 않는다 |

> **왜 `.wrap` 바깥인가**: 플로팅은 `.wrap` 서브트리를 **통째로 PiP 창으로 옮기는** 방식이다.
> 버튼이 `.wrap` 안에 있으면 버튼도 같이 옮겨가 (a) 좁은 창을 차지하고 (b) opener 에는 창을 닫을
> 수단이 남지 않는다. 이 배치는 **T22-37 이 줄 번호 비교로 강제**한다.

### 폴링 동기화 계약 — 무엇을 치환하고 무엇을 보존하는가

이 표가 스크립트와 DOM 사이의 계약이다. 위 「동적(치환 대상) — 7 셀렉터」 표의 **소비자 측 대응표**다.

| 대상 | 동기화 연산 | 근거 |
|------|------------|------|
| `#dz-title` · `#dz-subtitle` · `#dz-progress-pct` · `#dz-updated` | `textContent` 대입 | 순수 텍스트 노드 |
| `#dz-progress-bar` | `style` 속성 대입 | 인라인 `width:N%` 만 바뀐다. 속성 대입이라 CSS transition 이 살아 있다 |
| `#dz-steps, #dz-matrix` (둘 중 존재하는 것) | `outerHTML` 대입 | **선형/매트릭스 분기를 하나의 연산으로 흡수**한다. 한 파일에 하나만 존재한다는 불변식 1 덕분에 셀렉터 하나로 족하다 |
| `#dz-log` | `innerHTML` 대입 | 항목 prepend·`<details open>` 회수까지 파일이 곧 정답이다 |
| `input[name="dzs"]` · `input[name="dzf"]` · `label[for^="dz…"]` · `<style>` | **치환하지 않는다** | 라디오를 재삽입하면 사용자가 고른 유형 필터·세션 탭이 5초마다 초기화된다. 개수가 달라지면(=새 세션) **전체 리로드**로 처리한다 |
| `#dz-pip-btn` · `#dz-pip-hint` | **치환하지 않는다** | `.wrap` 바깥 = 동기화 영역 밖 |

**동기화 단위는 "파일 전체 문자열"이다.** 직전 폴링에서 받은 HTML 과 **문자열이 같으면 아무것도 하지
않는다.** 라이브 DOM 과 비교하지 않는 이유: 사용자가 `<details>` 를 손으로 펼치면 라이브 DOM 은
파일과 달라지고, 라이브 비교 방식은 그 펼침을 5초마다 되접는다.

**grep 유일성 불변식 (신규, 매우 중요)**
스크립트는 생성물 `.claude/dashboard.html` 안에서 `id="dz-log"` · `id="dz-progress-bar"` ·
`id="dz-progress-pct"` · `id="dz-cell-` 같은 **`id="…"` 형태의 문자열을 만들면 안 된다.**
`log` 0-a 단계와 `step` 0단계가 이 문자열들의 **줄 단위 유일성**에 의존하기 때문이다
(`step` 은 "결과는 항상 3줄"을 전제한다). 따라서 스크립트에서는 `getElementById('dz-log')` 나
`querySelector('#dz-log')` 만 쓰고, `id` 완전일치 대괄호 속성 셀렉터(`querySelector` 인자에
`id=` 값 전체를 대괄호로 감싸 넣는 형태)는 **금지**한다.

---

## 진행 시각화 규격 — 그룹 × 단계 모델

`init` 두 번째 인자는 **선형 문법**과 **그룹 문법** 중 하나로 해석된다. 그룹이 1개면 기존과 완전히
동일한 단계 띠(`#dz-step-{n}`)로, 2개 이상이면 매트릭스 표(행=그룹, 열=단계)로 렌더링한다.

### 개념 모델

```
Session
  title   : string
  groups  : Group[]          # 순서 있음. len(groups) >= 1
Group
  name    : string | null    # 선형 문법으로 만들어진 그룹 1개만 null 을 가진다
  phases  : string[]         # 순서 있음. len(phases) >= 1
Cell
  state   : "done" | "active" | "wait" | "na"
```

- **칸(Cell)** = (그룹, 단계) 쌍 중 **그 그룹이 실제로 가진 단계**. 진행률의 단위다.
- **전체 칸 수 `N` = Σ len(group.phases)**. 열 수 × 그룹 수가 **아니다**.
- `na` 는 표를 직사각형으로 유지하기 위한 **자리 채움**이며 칸이 아니다(분모에 들어가지 않는다).
- 게이트는 별도 개념이 아니라 `phases` 길이가 1인 그룹이다.

### 문자열 문법 (`init` 두 번째 인자)

```
선형 문법 :  "단계1|단계2|단계3"                                   ← 기존. 그대로 동작한다
그룹 문법 :  "그룹A:단계1,단계2|그룹B:단계1,단계2|그룹C:단계1"
```

**모드 판정 규칙 (결정적)** — `|` 로 나눈 세그먼트 목록을 보고:

| 조건 | 해석 |
|------|------|
| 모든 세그먼트에 `:` 가 **없다** | 선형 문법. 전체를 **이름 없는 그룹 1개**로 정규화한다 |
| 모든 세그먼트에 `:` 가 **있다** | 그룹 문법. 세그먼트마다 첫 `:` 앞=그룹명, 뒤를 `,` 로 나눈 것=단계 목록 |
| **섞여 있다** | 오타다. 한쪽으로 추측 해석하지 않고 **보고 후 중단**한다 |

- 그룹명·단계명에 `|` `:` `,` 를 쓰지 않는다(구분자와 충돌).
- 그룹 문법으로 그룹을 1개만 준 경우(`"worktree:설계,구현"`)도 유효하다. 렌더링은 **그룹 수**로
  결정되므로 선형 화면이 나오고, 잃어버릴 뻔한 그룹명은 `#dz-subtitle` 앞머리에 들어간다.

### 열(column) 확정 규칙

열 목록 = **모든 그룹의 단계명을 최초 등장 순서로 중복 없이 모은 것**(합집합).

- 모든 그룹이 같은 단계 목록을 가지는 일반적인 경우, 열 목록 = 그 목록이고 `na` 칸은 하나도 생기지 않는다.
- 어떤 그룹에 없는 단계의 자리는 `data-state="na"` 칸이 된다.
- 셀 좌표 `{p}` 는 **열 번호**(합집합 순번)이지 그룹 내 순번이 아니다. 직사각형인 경우 둘은 같다.
- 관례(강제 아님): 게이트처럼 단계가 1개인 그룹은 인자 목록 **맨 뒤**에 둔다. 그래야 그 그룹만의
  고유 열이 표의 오른쪽 끝에 생겨 `na` 칸이 한곳에 모인다.

### 매트릭스 마크업 (`init` 6단계가 생성)

`.card` 안, 기존 `<ol class="steps" id="dz-steps">...</ol>` 이 있던 자리를 통째로 대체한다.
**칸은 반드시 한 줄에 하나씩** 쓴다.

```html
    <table class="matrix" id="dz-matrix">
      <thead>
        <tr>
          <th class="corner">영역</th>
          <th>설계</th>
          <th>구현</th>
          <th>테스트</th>
          <th>검수</th>
          <th>승인</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th class="group" id="dz-group-1">worktree 격리</th>
          <td class="cell" id="dz-cell-1-1" data-state="active">진행중</td>
          <td class="cell" id="dz-cell-1-2" data-state="wait">대기</td>
          <td class="cell" id="dz-cell-1-3" data-state="wait">대기</td>
          <td class="cell" id="dz-cell-1-4" data-state="wait">대기</td>
          <td class="cell" id="dz-cell-1-5" data-state="na">–</td>
        </tr>
        <tr>
          <th class="group" id="dz-group-2">G-1 PRP 승인</th>
          <td class="cell" id="dz-cell-2-1" data-state="na">–</td>
          <td class="cell" id="dz-cell-2-2" data-state="na">–</td>
          <td class="cell" id="dz-cell-2-3" data-state="na">–</td>
          <td class="cell" id="dz-cell-2-4" data-state="na">–</td>
          <td class="cell" id="dz-cell-2-5" data-state="active">진행중</td>
        </tr>
      </tbody>
    </table>
```

### 매트릭스 CSS (템플릿 `<style>` 에 상주)

`.chip` 규칙 바로 뒤, `.badge` 규칙 앞에 있다. **새 색 토큰을 만들지 않는다** — 상태별 색쌍은
기존 `.chip`/`.num` 이 쓰던 것과 글자 하나까지 동일하다.

```css
  table.matrix{width:100%;border-collapse:collapse;margin:14px 0 0;font-size:14px}
  .matrix th,.matrix td{border:1px solid var(--line);padding:9px 10px}
  .matrix thead th{font-size:12px;font-weight:800;background:var(--soft);color:var(--muted);text-align:center}
  .matrix th.corner{text-align:left}
  .matrix th.group{text-align:left;font-weight:700;color:var(--navy);width:34%}
  .matrix td.cell{text-align:center;font-size:12px;font-weight:800;background:var(--soft);color:var(--muted)}
  .matrix td.cell[data-state="done"]{background:#E5F3EE;color:var(--green)}
  .matrix td.cell[data-state="active"]{background:#EAF2FB;color:var(--blue)}
  .matrix td.cell[data-state="na"]{background:#fff;color:var(--line)}
```

`wait` 에는 규칙이 없다 — `td.cell` 기본값이 곧 대기 상태다(선형 분기에서 `li` 기본값이 대기인 것과 같은 구조).
이 CSS 는 선형 세션에서는 매칭 대상이 없어 아무 일도 하지 않는다.

---

## `init` — 메인 세션이 수행할 절차

1. `.claude/dashboard.html` 존재 여부를 확인한다.
   - **이미 존재하면**: 제목·단계 목록 등은 덮어쓰지 않는다(다시 채우면 기존
     진행 상태와 충돌한다). 대신 아래 a~d 를 수행해 세션 경계와 세션 탭만 갱신하고,
     "기존 대시보드를 이어서 사용합니다"라는 취지로 안내하며
     `file://<현재 작업 디렉토리 절대경로>/.claude/dashboard.html` 을 출력한 뒤
     절차를 **여기서 종료**한다(2번 이하 단계를 실행하지 않는다).
     > **한계**: 이 가드는 "완전히 새 작업"과 "기존 미완료 작업 재개"를 구분하지
     > 못한다. 같은 프로젝트에서 정말 새로운 전체 경로 작업을 시작했는데 이전
     > 작업의 대시보드 파일이 남아 있으면, 엉뚱한 옛 대시보드를 계속 보여준다.
     > 새 작업을 시작할 때는 기존 `.claude/dashboard.html` 을 먼저 지우거나
     > 다시 만들지 사용자에게 확인하라.

     a. **세션 번호 확정**: Bash 로 `grep -n 'id="dz-log"' .claude/dashboard.html` 을 실행해
        `#dz-log` 여는 태그의 줄 번호와 전문을 얻는다. 그 태그의 `data-current-session="{P}"`
        값이 직전 세션 번호다. 이번 세션 번호는 `N = P + 1`.
        속성이 아예 없으면 세션 탭 도입 이전에 만들어진 파일이므로, 그 줄부터 `limit=60` 으로
        Read 해 보이는 `.session-head` 의 `data-session` 최댓값을 `P` 로 삼는다(하나도 없으면 `P=1`).

     b. **현재 세션 번호 갱신**: `#dz-log` 여는 태그를 `data-current-session="{N}"` 으로 치환한다.
        속성이 없었다면 `id="dz-log"` 바로 뒤에 새로 넣는다. Edit 의 `old_string` 은 a 에서 읽은
        태그 전문을 그대로 쓴다(태그 내용이 세션마다 달라지므로 고정 문자열로 매칭하지 않는다).

     c. **세션 구분 항목 prepend**: 그 태그 바로 뒤에 아래를 삽입한다. `{HH:MM}` 은 현재 시각.
        ```html
        <li class="session-head" data-session="{N}">세션 {N} 시작 · {HH:MM}</li>
        ```

     d. **세션 탭 갱신**: 아래 [세션 탭 갱신](#세션-탭-갱신--init-1-d-의-하위-절차) 절차를 수행한다.

   - **존재하지 않으면**: `.claude/` 디렉토리가 없으면 생성한 뒤, 아래
     [템플릿 전문](#템플릿-전문)을 그대로 `.claude/dashboard.html` 로 Write하고
     2번부터 계속 진행한다(템플릿은 `data-current-session="1"`, 탭 바 없음).
2. `#dz-title` 텍스트를 `<제목>` 인자로 치환한다.

3. **인자 파싱 — 그룹 목록으로 정규화한다.**
   두 번째 인자를 `|` 로 나눠 세그먼트 목록을 만든 뒤 [진행 시각화 규격](#진행-시각화-규격--그룹--단계-모델)의
   「모드 판정 규칙」을 적용한다.
   - 모든 세그먼트에 `:` 가 없다 → 선형 문법. **이름 없는 그룹 1개**로 본다.
   - 모든 세그먼트에 `:` 가 있다 → 그룹 문법. 첫 `:` 앞이 그룹명, 뒤를 `,` 로 나눈 것이 단계 목록.
   - 섞여 있다 → 오타다. 추측해서 한쪽으로 해석하지 말고 그 사실을 보고하고 중단한다.

4. **열 목록과 전체 칸 수를 확정한다.**
   열 목록 = 모든 그룹의 단계명을 최초 등장 순서로 중복 없이 모은 것.
   전체 칸 수 N = 각 그룹의 단계 개수의 합(열 수 × 그룹 수가 아니다).

5. `#dz-subtitle` 을 아래 형식으로 치환한다. 작업 유형(예: "전체 경로")은 호출한 오케스트레이터가
   이미 알고 있는 값을 채운다.
   - 그룹 1개(이름 없음): `"<단계1> → <단계2> → … · <작업 유형>"`          (기존과 동일)
   - 그룹 1개(이름 있음): `"<그룹명> · <단계1> → <단계2> → … · <작업 유형>"`
   - 그룹 2개 이상:       `"<G>개 영역 · <열1> → <열2> → … · <작업 유형>"`

6. **진행 시각화를 렌더링한다 — 분기 기준은 그룹 수 하나뿐이다.**
   - **그룹이 1개**: 템플릿의 `<ol class="steps" id="dz-steps">` 내부를 아래 `<li>` N개로 채운다
     (기존과 완전히 동일. 1번이 active, 나머지는 wait).
     ```html
     <li id="dz-step-{n}" class="{active|wait}"><span class="num">{n}</span>{단계명}<span class="chip">{진행중|대기}</span><span class="step-detail"></span></li>
     ```
   - **그룹이 2개 이상**: 템플릿의 아래 두 줄(`<ol>` 요소 전체)을 [매트릭스 마크업](#매트릭스-마크업-init-6단계가-생성)의
     `<table>` 로 통째로 치환한다. 각 그룹의 **첫 단계 칸**이 active, 나머지 칸은 wait, 그룹에 없는 단계는 na 다.
     ```html
     <ol class="steps" id="dz-steps">
     </ol>
     ```

7. `#dz-progress-bar` 의 `style` 을 `width:0%` 로, `#dz-progress-pct` 텍스트를 `0/N · 0%` 로 치환한다.
8. `#dz-updated` 를 현재 시각(예: `2026-08-04 17:02`)으로 치환한다.
9. `#dz-log` 는 템플릿 그대로 빈 목록(`<ul class="log" id="dz-log" data-current-session="1"></ul>`)으로
   둔다 — 아직 로그가 없다.
10. 사용자에게 `file://<현재 작업 디렉토리 절대경로>/.claude/dashboard.html` 을 출력해
    브라우저로 열도록 안내한다.

#### 세션 탭 갱신 — `init` 1-d 의 하위 절차

`grep -c 'dzs-all' .claude/dashboard.html` 로 탭 바 존재 여부를 판정한다.

**결과가 0 (탭 바 없음 — 이 대시보드에 세션이 둘이 된 첫 순간)**

1. `<input type="radio" name="dzf" id="dzf-all" class="dzf" checked>` 줄 **앞**에
   아래를 삽입한다. `모든 세션` 이 기본 선택이고, 세션 탭은 **큰 번호가 왼쪽**이다
   (`{N}`, `{N-1}`, …, `1` 순으로 나열. 보통 `N=2` 이므로 탭 3개).
   ```html
   <input type="radio" name="dzs" id="dzs-all" class="dzs" checked><label for="dzs-all">모든 세션</label>
   <input type="radio" name="dzs" id="dzs-{N}" class="dzs"><label for="dzs-{N}">세션 {N}</label>
   <input type="radio" name="dzs" id="dzs-1" class="dzs"><label for="dzs-1">세션 1</label>
   <br>
   ```
   `<br>` 은 세션 탭 줄과 유형 필터 줄을 분리하는 줄바꿈이다. wrapper `div` 와 달리 `<br>` 은
   빈 요소라 `~` 형제 결합자를 끊지 않는다 — 라디오·`#dz-log` 는 여전히 `.card` 의 직계
   형제로 남는다. 세션 1 탭은 이후 절대 삭제되지 않는 고정 앵커이므로, 세션이 늘어나도
   이 `<br>` 의 위치(세션 탭 그룹의 맨 끝)는 항상 유지된다.
2. `<style>` 안의 `/* DZ:SESSION-RULES */` 마커 줄 **바로 뒤**에 세션 `1`~`{N}` 각각에 대해
   아래 규칙을 한 줄씩 추가한다.
   ```css
   #dzs-{n}:checked ~ #dz-log .entry:not([data-session="{n}"]){display:none}
   ```

**결과가 1 이상 (탭 바 있음)**

1. `<label for="dzs-all">모든 세션</label>` **바로 뒤**에 이번 세션 탭 1개를 삽입한다.
   ```html
   <input type="radio" name="dzs" id="dzs-{N}" class="dzs"><label for="dzs-{N}">세션 {N}</label>
   ```
2. `/* DZ:SESSION-RULES */` 마커 바로 뒤에 이번 세션 규칙 1줄을 추가한다.

**새 탭 라디오에 `checked` 를 넣지 않는다.** 기본 선택은 언제나 `#dzs-all` 이다. 새 탭에도
`checked` 를 달면 같은 그룹에 `checked` 가 둘이 되어 문서 순서상 뒤엣것이 이기고, 페이지가
새로고침될 때마다 사용자가 고른 탭이 무시된다.

## `step` — 메인 세션이 수행할 절차 (Bash 1회 + Edit 3회, 결정적)

> 기존 절차는 대상 줄의 전문을 LLM 이 "알고 있다"고 가정했다. 세션 2 가 기존 대시보드를 이어받는
> 경우(단계명을 모른다) 이 가정이 깨진다. 칸이 16개로 늘어나면 훨씬 자주 깨진다. 그래서 `log` 가
> 이미 검증한 **grep 앵커** 방식으로 두 분기(선형/그룹)를 통일한다.

0. **대상 줄과 진행률 줄을 한 번에 확보한다.** Bash 1회:
   ```bash
   grep -n -e 'id="dz-cell-{g}-{p}"' -e 'id="dz-progress-bar"' -e 'id="dz-progress-pct"' .claude/dashboard.html
   ```
   (선형 모드면 첫 패턴을 `id="dz-step-{n}"` 로 바꾼다.)
   각 요소는 한 줄에 하나씩 생성되므로 결과는 항상 3줄이다.
   - 대상 줄이 안 나온다 → 인덱스가 틀렸거나 모드를 혼동한 것이다. **다른 칸을 추측해서 고치지 말고
     보고 후 중단한다.** 인덱스를 잊었으면 `grep -n 'dz-group-\|dz-cell-'` 로 표 전체 지도를 한 번에 얻는다.
   - 대상 칸이 `data-state="na"` 다 → 그 그룹에 없는 단계다. 보고 후 중단한다.

1. **상태 치환** — 0에서 얻은 줄 전문을 `old_string` 으로 Edit 1회.
   - 선형: `class="{state}"` 와 자식 `.chip` 텍스트, 그리고 아래 표에 따른 `.step-detail` 텍스트
   - 그룹: `data-state="{state}"` 와 칸 텍스트       (같은 어휘를 쓴다)

   **`.step-detail` 갱신 규칙 (선형 모드 전용)**

   | 네 번째 인자 | 동작 |
   |-------------|------|
   | 주어지지 않음 | `.step-detail` 을 **건드리지 않는다**(기존 값 유지). 상세 없이 부르던 기존 호출과 결과가 완전히 같다 |
   | `"내용"` | 이스케이프한 내용으로 `<span class="step-detail">내용</span>` 를 치환한다 |
   | `""`(빈 문자열) | 내용을 비운다. `.step-detail:empty` 규칙이 그 줄을 통째로 숨긴다 |

   - **이스케이프**: `log` 와 동일하게 `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` 순서로 치환한다.
     코드 조각(`Foo<T>`, `a && b`)이 그대로 들어가면 태그가 깨진다.
   - **줄바꿈을 넣지 않는다.** `<li>` 가 여러 줄로 쪼개지면 불변식 2가 깨져 이후 `step` 의 grep 앵커와
     감사용 `grep -c` 가 전부 어긋난다. 길이는 40자 내외를 권장하며, 넘치면 CSS 가 말줄임 처리한다.
   - 대상 `<li>` 에 `.step-detail` span 이 **없으면**(이 기능 도입 이전에 만들어진 대시보드)
     `</li>` 바로 앞에 새로 삽입한다. 같은 Edit 1회 안에서 처리되므로 비용이 늘지 않는다.
   - **매트릭스 모드(`<g>.<p>`)에서 상세 인자가 주어지면**, 상태 갱신은 정상 수행하고 **상세는
     무시했음을 한 줄 보고한다.** 중단하지 않는다 — 상태 갱신까지 막으면 부가 정보 손실이
     진행률 정지라는 더 큰 손실로 번진다.

2. **진행률 재계산** — 0에서 읽은 `#dz-progress-pct` 텍스트가 `"M/N · P%"` 이므로 M·N 을 그대로 얻는다.
   완료 칸 수는 다시 세지 않고 **전이로 계산한다**:
   - 이전 상태 ≠ done 이고 새 상태 = done  → M+1
   - 이전 상태 = done 이고 새 상태 ≠ done  → M-1
   - 그 외                                  → M 그대로

   (이전 상태는 0에서 읽은 줄에 그대로 적혀 있다 — 기억에 의존하지 않는다.)
   P = round(M/N × 100) 의 정수. `#dz-progress-bar` 의 `style="width:P%"` 와 `#dz-progress-pct`
   텍스트를 Edit 1회로 함께 치환한다(두 줄이 인접해 있다). M 이 바뀌지 않았으면 이 단계를 건너뛴다.

3. `#dz-updated` 텍스트를 현재 시각으로 치환한다. (Edit 1회)

**감사(audit)용 재계수** — 진행률이 어긋난 것 같으면 아래 한 줄로 다시 센다. `id` 접두어를 함께
매칭하므로 `<style>` 안의 `.matrix td.cell[data-state="done"]` 규칙 줄에 걸리지 않는다.

```bash
grep -c 'dz-cell-.*data-state="done"' .claude/dashboard.html   # 그룹 모드
grep -c 'dz-step-.*class="done"' .claude/dashboard.html        # 선형 모드
```

## `log` — 메인 세션이 수행할 절차 (Bash grep 1회 + Read 1~2회 + Edit 2회, 결정적)

0. **최신 항목만 확인한다(파일 전체를 Read하지 않는다)**:
   a. Bash 로 `grep -n 'id="dz-log"' .claude/dashboard.html` 를 실행해 로그 시작 줄 번호 `L` 과
      그 줄의 전문을 얻는다. `id="dz-log"` 는 문서 내 유일 문자열이다(`<style>` 과 헤더 주석의
      `#dz-log` 는 `id=` 형태가 아니라 매칭되지 않는다). 이 줄의 `data-current-session="{C}"`
      값이 **이번 항목이 속할 세션 번호**다(속성이 없으면 `C=1`). 태그 전문이 세션마다
      달라지므로 grep 은 반드시 이 부분일치 패턴을 쓴다 — 완전일치는 속성이 붙는 순간
      영원히 매칭에 실패한다.
   b. `Read` 도구로 `offset=L, limit=60` 만 읽어 최신 항목 몇 개(보통 3~4개)의 `data-seq` 를
      확인한다. 로그는 항상 최신순으로 prepend 되므로, 이 창(window) 안에서 처음 만나는
      `data-seq` 가 곧 전체 로그의 최댓값 `S` 다(로그가 비어 있으면 `S=0`).
   c. 이 창 안에서 `data-seq="S-2"` 항목을 찾지 못하면(상세 텍스트가 길어 항목 3개가
      60줄을 넘긴 경우) `limit` 을 120 으로 늘려 같은 지점부터 한 번 더 Read 한다.
      그래도 없으면 로그가 3건 미만인 것이므로 1단계(펼침 회수)를 생략한다.
   > **왜 이렇게 하는가**: `data-seq` 는 항상 증가하는 순서로 로그 맨 앞에 prepend되므로
   > 최댓값과 `S-2` 항목은 로그 길이와 무관하게 항상 맨 앞부분에 있다. 파일 전체를 Read할
   > 필요가 없어, 세션이 길어져 로그가 수십~수백 건으로 늘어나도 이 단계의 비용은 늘지 않는다
   > (기존 설계가 안고 있던 "가변 비용" 문제 해결).
1. **직전 펼침 회수**: 위 0단계에서 찾은 `data-seq="S-2"` 인 `<li>` 가 존재하면, 그 안의
   `<details open>` 를 `<details>` 로 치환한다(연 상태 해제). 해당 seq 가 없으면(로그 3건 미만)
   이 단계를 생략한다.
   → 결과적으로 **항상 최신 3건만 펼쳐진다.**
2. **prepend**: 0-a 에서 읽은 `#dz-log` 여는 태그 **전문**을 `old_string` 앵커로 삼아 그 바로
   뒤에 `data-seq="S+1"`, `data-session="C"` 인 새 `<li>` 를 위
   [로그 항목 스키마](#로그-항목-스키마)대로 삽입한다(태그 텍스트가 세션마다 다르므로
   고정 문자열을 앵커로 쓰지 않는다).
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

## `serve` — 메인 세션이 수행할 절차

> **이 하위 명령은 워크플로우에 강제되지 않는다.** 플로팅을 쓰려는 사용자가 명시적으로 부를 때만
> 실행한다. `init`/`step`/`log` 는 서버 유무와 무관하게 동작한다.

```
0. 인자 해석:
   - 첫 인자가 `stop` 이면 4번으로 간다. 두 번째 인자가 있으면 그것이 중지 대상 포트,
     없으면 기본 포트 8791 을 쓴다. 중지 대상 포트에도 아래와 같은 1024~65535 순수 숫자
     검증을 똑같이 적용한다 — 통과하지 못하면 중단하고 보고하며 셸 명령에 치환하지 않는다.
   - 첫 인자가 1024~65535 범위의 순수 숫자면 포트로 쓴다. 인자가 없으면 8791.
   - 그 밖의 값이면 중단하고 "포트는 1024~65535 숫자여야 한다"를 보고한다.
     받은 값을 셸 명령에 치환하지 않는다.

1. `.claude/dashboard.html` 이 없으면 **중단**하고 `/dashboard init` 을 먼저 부르라고 안내한다.
   (서버만 띄우면 404 가 나올 뿐이다.)

2. `python3 --version` 이 실패하면 **중단**하고 그 사실을 보고한다. 다른 서버를 대신 설치하지 않는다.
   사용자가 원하면 임의의 정적 서버로 같은 URL 을 열 수 있음을 한 줄로 안내한다.

3. 아래를 **백그라운드**로 실행한다(Bash 도구의 background 옵션).
   문서 루트는 프로젝트 밖 임시 디렉토리이며, 그 안에는 대시보드 심볼릭 링크 하나만 둔다.

       DZ_DIR=$(mktemp -d) && ln -s "$PWD/.claude/dashboard.html" "$DZ_DIR/dashboard.html" \
         && python3 -m http.server {포트} --bind 127.0.0.1 --directory "$DZ_DIR"

   - `--bind 127.0.0.1` 은 **생략 금지**다. `http.server` 의 기본값은 루프백이 아니라 모든 네트워크
     인터페이스에 열리는 값이다.
   - "Address already in use" 로 죽으면 포트 충돌이다. 다른 포트를 **추측해서 재시도하지 말고**
     보고하고 `/dashboard serve 8792` 를 제안한다.

4. `stop`: `pkill -f "http.server {포트} --bind 127.0.0.1"` 를 실행하고 결과를 보고한다.
   (0단계에서 정한 대상 포트를 쓴다. 패턴에 `--bind 127.0.0.1` 까지 포함해 다른 프로세스의
   부분 일치를 죽이지 않는다. 임시 디렉토리는 OS 가 정리하므로 따로 지우지 않는다.)

5. 보고: `http://localhost:{포트}/dashboard.html` 을 출력하고
   "이 URL 로 열어야 우상단 「플로팅」 버튼이 활성화된다"를 한 줄 덧붙인다.
   작업이 끝나면 `/dashboard serve stop` 으로 서버를 끄도록 안내한다.
```

---

## `on` / `off`

#### 호출 규약

```
/dashboard on      # 이 프로젝트에서 대시보드 기록을 켠다 (기본값)
/dashboard off     # 이 프로젝트에서, 나만, 대시보드 기록을 끈다
```

**대상 파일은 `.claude/settings.local.json` 뿐이다.** `on`/`off` 는 `.claude/dashboard.html` 을
만들지도 지우지도 않는다 — 생성은 `init` 의 책임이다. `off` 이후에도 기존 대시보드 파일은
그대로 남으며, 지울지는 사용자가 정한다(안내만 한다).

#### 절차 (Read 1회 + Edit 또는 Write 1회 + Read-back 1회)

1. **읽기** — `.claude/settings.local.json` 이 있으면 Read 한다.
   - 파일이 없다 → 요청이 `off` 면 3-a 로, `on` 이면 3-b 로(아무것도 하지 않는다).
   - **JSON 으로 파싱되지 않는다 → 절차를 중단하고 그 사실만 보고한다.** 깨진 파일을
     덮어쓰면 사용자의 권한 허용 목록이 사라진다.
2. **현재 값 판정** — `dashboard_enabled` 필드의 유무와 값을 확인한다. 필드가 없으면 켜짐이다.
   요청한 상태와 현재 상태가 같으면 **아무것도 하지 않고** 그 사실을 보고한다.
3. **쓰기**
   - **a. 파일 없음 + `off`**: `.claude/` 를 만든 뒤 아래를 Write 한다.
     ```json
     {
       "dashboard_enabled": false
     }
     ```
   - **b. 파일 없음 + `on`**: 아무것도 하지 않는다. 기본값이 켜짐이다.
   - **c. 필드 있음**: 값만 Edit 로 치환한다 (`"dashboard_enabled": false` ↔ `"dashboard_enabled": true`).
   - **d. 필드 없음 + `off`**: **여는 `{` 바로 뒤 첫 필드 자리**에 삽입한다.
     ```
     {
       "dashboard_enabled": false,
     ```
     빈 객체(`{}` 또는 `{ }`)이면 뒤따르는 필드가 없으므로 **쉼표 없이** 넣는다.

     > **왜 첫 자리인가**: 마지막 필드 뒤에 넣으려면 직전 줄에 쉼표를 붙이는 Edit 이 하나 더
     > 필요하고, 그 줄의 내용은 프로젝트마다 다르다. 첫 자리는 앵커가 항상 `{` 하나로 고정된다.
   - **기존 필드는 어떤 경우에도 건드리지 않는다.**
4. **검증** — 쓴 파일을 다시 Read 해 **유효한 JSON 인지 눈으로 확인한다**(파일은 보통 20줄 미만).
   `python3` 이 있으면 `python3 -m json.tool .claude/settings.local.json > /dev/null` 로 확인해도 된다
   (없어도 되는 선택지다 — 새 의존성을 만들지 않는다).
5. **보고** — 최종 상태 한 줄. `off` 인 경우 "이번 프로젝트에서 나에게만 적용되며 커밋되지 않는다"를
   덧붙인다. `.claude/settings.local.json` 이 대상 프로젝트의 `.gitignore` 에 없으면 그 사실을 알린다.

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

라디오를 `#dz-log` 의 **앞 형제**(같은 부모의 직전 형제들)로 두고 `~` 결합자로 제어한다.
래퍼 `div` 로 감싸면 `~` 결합자가 `#dz-log` 에 닿지 않으므로 감싸지 않는다. 두 개의
독립된 라디오 그룹이 있다:

| 그룹 | `name` | 항목 | 생성 시점 |
|------|--------|------|----------|
| 유형 필터 | `dzf` | 전체 / 구현 / 검수 | 템플릿에 고정 (3개) |
| 세션 탭 | `dzs` | 모든 세션 / 세션 N … 세션 1 | 두 번째 세션부터 `init` 이 동적 생성 |

```html
<div class="log-title">작업 추적</div>
<!-- 세션 탭: init 이 두 번째 세션 시작 시 이 자리에 만든다 (첫 세션에는 없음) -->
<input type="radio" name="dzs" id="dzs-all" class="dzs" checked><label for="dzs-all">모든 세션</label>
<input type="radio" name="dzs" id="dzs-2" class="dzs"><label for="dzs-2">세션 2</label>
<input type="radio" name="dzs" id="dzs-1" class="dzs"><label for="dzs-1">세션 1</label>
<br>
<input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
<input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
<input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
<ul class="log" id="dz-log" data-current-session="2">…</ul>
```

```css
/* 유형 필터 — 템플릿 고정 */
.dzf{position:absolute;opacity:0;pointer-events:none}
#dzf-impl:checked   ~ #dz-log .entry:not([data-kind="impl"]){display:none}
#dzf-review:checked ~ #dz-log .entry:not([data-kind="review"]){display:none}

/* 세션 탭 — 스타일·구분선 숨김 규칙은 고정, 항목 필터 규칙만 세션마다 1줄씩 추가 */
.dzs{position:absolute;opacity:0;pointer-events:none}
label[for^="dzs-"]{display:inline-block;font-size:12px;font-weight:700;padding:5px 13px;margin:0 4px 6px 0;border-radius:8px 8px 0 0;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent}
.dzs:checked + label{color:var(--navy);background:var(--soft);border-bottom-color:var(--navy)}
/* 모든 세션 이 아닌 특정 세션 탭에서는 구분선을 아예 숨긴다 (세션 개수와 무관한 고정 규칙) */
input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head{display:none}
/* DZ:SESSION-RULES — 세션 탭 필터 규칙. init 이 세션마다 아래에 1줄씩 추가한다 */
#dzs-1:checked ~ #dz-log .entry:not([data-session="1"]){display:none}
#dzs-2:checked ~ #dz-log .entry:not([data-session="2"]){display:none}
```

라디오는 시각적으로 숨기되 포커스는 유지한다(`display:none` 이 아니라 `opacity:0`).
`:has()` 같은 최신 셀렉터에 의존하지 않으므로 지원 범위가 넓다.
유형 필터는 알약(pill), 세션 탭은 밑줄 탭으로 형태를 달리해 두 줄의 역할을 구분하고,
`<br>` 로 두 그룹을 물리적으로 다른 줄에 고정한다(카드 폭에 따라 자연 줄바꿈에 기대지 않는다).

원본(`~/Desktop/dashboard.html`)의 골격·`:root` 색 토큰·단계 리스트 스타일은 그대로 유지한다.

#### 이 구조가 성립하는 이유

- **구분선은 특정 세션 탭에서 아예 숨긴다.** `input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`
  는 세션 개수와 무관한 고정 규칙 1개다 — 어떤 `dzs-N` 이 선택되든(`dzs-all` 만 예외)
  `.session-head` 를 전부 숨긴다. 세션이 늘어나도 이 규칙은 늘지 않는다(`:not(#dzs-all)`
  이 "전체가 아닌 모든 세션 라디오"를 이미 포괄하므로).
- **항목 필터는 `.entry` 만 대상으로 한다.** `#dzs-{n}:checked ~ #dz-log .entry:not([data-session="{n}"])`
  는 유형 필터와 동일한 패턴(`.entry` 대상)이다. `.session-head` 는 위 규칙이 이미 전담하므로
  이 규칙에서는 신경 쓰지 않는다 — 두 관심사(항목 필터링 vs 구분선 노출)가 규칙 단위로 분리된다.
- **모든 규칙은 `display:none` 만 지정한다.** 되돌리는 규칙(`display:block` 등)을 쓰지
  않으므로 두 그룹의 규칙이 서로의 특이도(specificity)를 다투지 않고, "둘 다 통과해야
  보인다"는 **AND 결합이 저절로 성립**한다. 이 불변식을 깨는 규칙을 추가하지 않는다.
- **래퍼 `div` 금지 제약은 세션 탭에도 그대로 적용된다.** 라디오·라벨·`#dz-log` 는 모두
  `.card` 의 직계 형제여야 한다. `display:contents` 로도 우회할 수 없다 — 형제 결합자는
  박스 트리가 아니라 DOM 트리로 판정하기 때문이다.
- 규칙 증가량은 세션당 정확히 1줄이다(`#dz-step-{n}` 처럼 "개수만큼 생성" 하는 기존
  패턴과 동일).

#### 탭이 많아지면

`label[for^="dzs-"]` 은 `inline-block` 이라 카드 폭을 넘으면 **자연히 줄바꿈**된다. 이대로 둔다.

- 가로 스크롤 컨테이너는 래퍼 `div` 가 필요한데 그러면 `~` 결합자가 끊겨 필터 전체가 깨진다.
  즉 **줄바꿈 외의 선택지가 애초에 없다.**
- 현실적 상한도 낮다. 대시보드는 기능 단위로 만들고 끝나면 지우는 파일이라 세션 수가
  두 자리로 가는 경우가 드물고, 그 지경이면 대시보드를 새로 만드는 편이 맞다.
- 그러므로 접기·"더 보기"·상한 같은 장치는 만들지 않는다(YAGNI).

### 세션 구분

`init` 이 삽입하는 `<li class="session-head" data-session="N">` 로 세션 경계를 표시한다.
`모든 세션` 탭에서만 경계선으로 보이고, 특정 세션 탭을 선택하면 구분선 자체가 사라진다
(사용자 피드백 반영 — 애초에 하나의 세션만 보고 있는 화면에서는 "경계"가 무의미하다).

- `.entry` 가 아니므로 **유형 필터**(`.entry:not([data-kind=...])`)의 영향을 받지 않는다 —
  `모든 세션` 탭 안에서는 어떤 유형 필터 상태에서도 항상 보인다.
- **세션 탭 필터**(`input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`)의
  영향은 받는다. `dzs-all` 이 아닌 특정 세션이 선택되면 소속 세션과 무관하게 전부 숨는다.
- 세션 탭 도입 이전에 만들어진 대시보드의 옛 로그 항목에는 `data-session` 이 없어
  **어떤 세션 탭에서도 보이지 않는다**(`모든 세션` 탭에서만 보인다). `.claude/dashboard.html`
  은 임시 산출물이라 이 정도 열화는 수용한다.

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
  #dz-step-{n}          : [그룹 1개] 각 단계 li — class(done|active|wait) + .chip 텍스트
                          + .step-detail 텍스트(그 단계의 한 줄 상세. 비어 있으면 CSS 가 숨긴다)
  #dz-cell-{g}-{p}      : [그룹 2+] 매트릭스 칸 td — data-state(done|active|wait|na) + 칸 텍스트
                          {g}=행(그룹) 번호, {p}=열(단계) 번호. 한 파일에 step/cell 이 공존하지 않는다
  #dz-group-{g}         : [그룹 2+] 행 머리 th — init 이 그룹명을 넣고 이후 치환하지 않는다
  #dz-log               : 작업 추적 ul — li data-seq 앵커로 prepend / data-current-session 속성(현재 세션 번호)
  #dz-updated           : 갱신 시각 텍스트
정적(불가침): 골격 · <style> · 제목 · 하단 스크립트
  #dz-pip-btn / #dz-pip-hint : 플로팅 진입 버튼과 안내 한 줄. .wrap 바깥에 있으며
                               init/step/log 도, 폴링 동기화도 이 둘을 건드리지 않는다
  #dz-log-card               : 작업 추적 카드 div. PiP 압축 뷰가 CSS 로만 숨긴다
                               (DOM 에서 제거하지 않는다 — 복귀 시 로그가 사라진다)
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
  ol.steps li{display:flex;align-items:center;gap:12px;padding:11px 4px;border-bottom:1px solid var(--soft);font-size:15px;flex-wrap:wrap;row-gap:3px}
  ol.steps li:last-child{border-bottom:0}
  .num{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:13px;font-weight:800;background:var(--soft);color:var(--muted);flex:none}
  li.done .num{background:var(--green);color:#fff}
  li.active .num{background:var(--blue);color:#fff}
  li.done{color:var(--muted)}
  li.active{font-weight:700;color:var(--navy)}
  .chip{margin-left:auto;font-size:12px;font-weight:800;padding:3px 10px;border-radius:999px;background:var(--soft);color:var(--muted);flex:none}
  li.done .chip{background:#E5F3EE;color:var(--green)}
  li.active .chip{background:#EAF2FB;color:var(--blue)}
  .step-detail{flex-basis:100%;margin-left:38px;font-size:12.5px;font-weight:400;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .step-detail:empty{display:none}
  table.matrix{width:100%;border-collapse:collapse;margin:14px 0 0;font-size:14px}
  .matrix th,.matrix td{border:1px solid var(--line);padding:9px 10px}
  .matrix thead th{font-size:12px;font-weight:800;background:var(--soft);color:var(--muted);text-align:center}
  .matrix th.corner{text-align:left}
  .matrix th.group{text-align:left;font-weight:700;color:var(--navy);width:34%}
  .matrix td.cell{text-align:center;font-size:12px;font-weight:800;background:var(--soft);color:var(--muted)}
  .matrix td.cell[data-state="done"]{background:#E5F3EE;color:var(--green)}
  .matrix td.cell[data-state="active"]{background:#EAF2FB;color:var(--blue)}
  .matrix td.cell[data-state="na"]{background:#fff;color:var(--line)}
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
  .dzs{position:absolute;opacity:0;pointer-events:none}
  label[for^="dzs-"]{display:inline-block;font-size:12px;font-weight:700;padding:5px 13px;margin:0 4px 6px 0;border-radius:8px 8px 0 0;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent}
  .dzs:checked + label{color:var(--navy);background:var(--soft);border-bottom-color:var(--navy)}
  input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head{display:none}
  /* DZ:SESSION-RULES — 세션 탭 필터 규칙. init 이 세션마다 아래에 1줄씩 추가한다 */
  ul.log{list-style:none;margin:6px 0 0;padding:0;font-size:13px;color:#4B5A6D}
  .entry{border-bottom:1px solid var(--soft);padding:8px 4px}
  .entry:last-child{border-bottom:0}
  .entry summary{cursor:pointer;display:flex;align-items:center;gap:8px;list-style:none}
  .entry summary::-webkit-details-marker{display:none}
  .entry summary::marker{content:""}
  .entry .time{font-size:11px;color:var(--muted);flex:none;width:40px}
  .entry .lead{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;color:var(--ink)}
  .entry .detail{margin:6px 0 0 48px;font-size:12.5px;color:var(--muted);white-space:pre-wrap}
  .session-head{margin:14px 0 6px;padding:0 4px 6px;border-bottom:2px solid var(--line);font-size:11px;font-weight:800;letter-spacing:.3px;color:var(--navy)}
  .session-head:first-child{margin-top:0}
  .log-title{font-size:13px;font-weight:700;color:var(--muted);margin:0 0 10px}
  .foot{font-size:12px;color:var(--muted);text-align:right}
  #dz-pip-btn{position:fixed;top:18px;right:18px;z-index:9;font-family:inherit;font-size:12px;font-weight:700;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--navy);cursor:pointer;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-btn:disabled{color:var(--muted);cursor:not-allowed;box-shadow:none}
  #dz-pip-hint{position:fixed;top:54px;right:18px;z-index:9;max-width:300px;font-size:11px;line-height:1.5;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 10px;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-hint[hidden]{display:none}
  body.dz-pip .wrap{margin:10px auto;padding:0 10px}
  body.dz-pip .card{padding:14px 16px;border-radius:10px;margin-bottom:10px}
  body.dz-pip h1{font-size:16px}
  body.dz-pip .sub{margin-bottom:12px}
  body.dz-pip #dz-log-card{display:none}
  body.dz-pip ol.steps li{padding:9px 4px}
  body.dz-pip ol.steps li.active{background:#EAF2FB;border-radius:8px;padding-left:8px;padding-right:8px}
  body.dz-pip ol.steps li:not(.active) .step-detail{display:none}
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
  <div class="card" id="dz-log-card">
    <div class="log-title">작업 추적</div>
    <input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
    <input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
    <input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
    <ul class="log" id="dz-log" data-current-session="1"></ul>
  </div>
  <div class="foot" id="dz-updated">갱신: -</div>
</div>
<button id="dz-pip-btn" type="button">플로팅</button>
<div id="dz-pip-hint" hidden></div>
<script>
(function(){
  var POLL_INTERVAL_MS = 5000;          // 로컬 파일 폴링 주기
  var FAILURE_LIMIT = 3;                // 연속 실패 이 횟수부터 사용자에게 알린다
  var PIP_WIDTH = 420, PIP_HEIGHT = 620;

  var wrap = document.querySelector('.wrap');
  var pipButton = document.getElementById('dz-pip-btn');
  var pipHint = document.getElementById('dz-pip-hint');
  var isServed = location.protocol === 'http:' || location.protocol === 'https:';
  var hasPipSupport = 'documentPictureInPicture' in window;
  var pipWindow = null;
  var lastHtml = '';
  var busy = false;
  var failureCount = 0;
  var reloadPending = false;
  var reasonHint = '';            // 버튼이 비활성인 영구 사유. 해소되기 전까지 유지된다

  function setHint(text){ pipHint.textContent = text || ''; pipHint.hidden = !text; }

  // ── 갱신 경로 A: file:// — Phase 1 방식 그대로. 이 분기는 회귀 금지 대상이다 ──
  if(!isServed){
    var reloading = false;
    var reloadOnce = function(){ if(reloading) return; reloading = true; location.reload(); };
    document.addEventListener('visibilitychange', function(){ if(document.visibilityState==='visible') reloadOnce(); });
    window.addEventListener('focus', reloadOnce);
    pipButton.disabled = true;
    setHint('플로팅 창은 로컬 서버에서만 동작합니다. /dashboard serve 를 실행하고 http://localhost:8791/dashboard.html 로 여세요.');
    return;
  }

  // ── 갱신 경로 B: http(s):// — 폴링 + 부분 치환 ──
  function syncText(fresh, id){
    var live = wrap.querySelector('#'+id), next = fresh.getElementById(id);
    if(live && next) live.textContent = next.textContent;
  }
  function syncProgressBar(fresh){
    var live = wrap.querySelector('#dz-progress-bar'), next = fresh.getElementById('dz-progress-bar');
    if(live && next) live.setAttribute('style', next.getAttribute('style') || '');
  }
  function syncVisualization(fresh){
    // 선형(#dz-steps)과 매트릭스(#dz-matrix)는 한 파일에 하나만 존재한다(불변식 1).
    var live = wrap.querySelector('#dz-steps,#dz-matrix'), next = fresh.querySelector('#dz-steps,#dz-matrix');
    if(live && next) live.outerHTML = next.outerHTML;
  }
  function syncLog(fresh){
    var live = wrap.querySelector('#dz-log'), next = fresh.getElementById('dz-log');
    if(live && next) live.innerHTML = next.innerHTML;
  }
  function sessionTabsChanged(fresh){
    return fresh.querySelectorAll('input[name="dzs"]').length
        !== wrap.querySelectorAll('input[name="dzs"]').length;
  }
  function apply(html){
    if(html === lastHtml) return;
    lastHtml = html;
    var fresh = new DOMParser().parseFromString(html, 'text/html');
    // 라디오와 <style> 은 치환 대상이 아니다(사용자가 고른 필터·탭이 날아간다).
    // 세션 탭 개수가 달라지면 전체 리로드가 유일하게 안전한 경로다. 플로팅 중에는
    // 리로드가 PiP 참조를 죽이므로, 창을 먼저 강제로 닫는다 — opener 쪽에서
    // pipWindow.close() 를 호출하는 것은 Document PiP 스펙이 지원하는 정상 동작이다
    // (사용자 제스처 요건은 '여는' 쪽에만 적용되고 닫는 쪽에는 없다).
    if(sessionTabsChanged(fresh)){
      if(!pipWindow){ location.reload(); return; }
      reloadPending = true;
      pipWindow.close();   // pagehide 핸들러가 reloadPending 을 보고 즉시 리로드한다
    }
    syncText(fresh,'dz-title'); syncText(fresh,'dz-subtitle');
    syncText(fresh,'dz-progress-pct'); syncText(fresh,'dz-updated');
    syncProgressBar(fresh); syncVisualization(fresh); syncLog(fresh);
  }
  function poll(){
    if(busy) return;
    busy = true;
    fetch(location.pathname, {cache:'no-store'})
      .then(function(res){ if(!res.ok) throw new Error(res.status); return res.text(); })
      .then(function(html){ failureCount = 0; if(!pipWindow) setHint(reasonHint); apply(html); })
      .catch(function(){
        if(++failureCount >= FAILURE_LIMIT)
          setHint('대시보드를 읽지 못했습니다. /dashboard serve 로 로컬 서버가 켜져 있는지 확인하세요.');
      })
      .then(function(){ busy = false; });
  }
  setInterval(poll, POLL_INTERVAL_MS);
  document.addEventListener('visibilitychange', function(){ if(document.visibilityState==='visible') poll(); });
  window.addEventListener('focus', poll);

  // ── 플로팅(Document PiP) — 반드시 사용자 제스처로만 진입한다 ──
  if(!hasPipSupport){
    pipButton.disabled = true;
    reasonHint = '이 브라우저는 Document Picture-in-Picture 를 지원하지 않습니다 (Chrome·Edge 에서 동작).';
    setHint(reasonHint);
    return;
  }
  pipButton.addEventListener('click', function(){
    if(pipWindow){ pipWindow.close(); return; }
    window.documentPictureInPicture.requestWindow({width:PIP_WIDTH, height:PIP_HEIGHT})
      .then(function(win){
        pipWindow = win;
        var pipDocument = win.document;
        pipDocument.title = document.title;
        // PiP 창은 opener 의 CSS 를 상속하지 않는다(실측) — <style> 전문을 복사한다.
        Array.prototype.forEach.call(document.querySelectorAll('style'), function(source){
          var copy = pipDocument.createElement('style');
          copy.textContent = source.textContent;
          pipDocument.head.appendChild(copy);
        });
        pipDocument.body.className = 'dz-pip';
        // 복제가 아니라 '이동'이다 — 폴링이 계속 같은 노드를 갱신하므로 동기화 코드가 하나로 유지된다.
        pipDocument.body.appendChild(wrap);
        // 숨은 탭의 타이머 스로틀링(최대 1분)을 보완한다: 창에 커서를 올리면 즉시 갱신.
        pipDocument.body.addEventListener('pointerenter', poll);
        pipButton.textContent = '플로팅 닫기';
        reasonHint = '';
        setHint('플로팅 창에서 보는 중입니다. 창을 닫으면 여기로 돌아옵니다.');
        win.addEventListener('pagehide', function(){
          pipWindow = null;
          document.body.insertBefore(wrap, pipButton);
          pipButton.textContent = '플로팅';
          setHint(reasonHint);
          if(reloadPending) location.reload(); else poll();
        });
      })
      .catch(function(err){
        // 자동 재시도하지 않는다 — 창 열기는 사용자 제스처가 있어야만 허용된다.
        reasonHint = '플로팅 창을 열 수 없습니다 (' + ((err && err.name) || 'error') + '). Claude 내장 브라우저 대신 Chrome 에서 열어 보세요.';
        setHint(reasonHint);
      });
  });
})();
</script>
</body>
</html>
```
