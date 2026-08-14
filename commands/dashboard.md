---
description: "세션 진행 상황을 프로젝트 로컬 HTML 대시보드로 기록 — init/step/log + on/off 스위치"
argument-hint: "init \"<제목>\" \"<단계1|...> 또는 <그룹A:단계1,단계2|그룹B:...>\" | step <n>|<g>.<p> <done|active|wait> [\"상세\"] | impl set \"<작업1|...>\"|<k> <done|active|wait> | log <impl|pass|fail|commit> \"<요약>\" [...] | serve [포트] | on | off"
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
/dashboard impl set "<작업1|작업2|...>"            # 「구현」 단계의 세부 작업 목록을 한 번 정의
/dashboard impl <k> <done|active|wait> ["상세"]    # 세부 작업 1개 갱신. active 동시 다중 허용
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
/dashboard serve [포트] | serve stop        # 플로팅용 로컬 정적 서버 (opt-in)
/dashboard on | off
```

`step` 의 첫 인자에 `.` 이 있으면 매트릭스 칸, 없으면 선형 단계다. 인덱스는 모두 1부터 시작한다.

`impl` 의 첫 인자가 `set` 이면 목록 정의, 정수면 항목 갱신이다. `step` 이 `.` 유무로 두 형태를
가르는 것과 같은 **단일 토큰 판정**이다. **`log impl` 과 혼동하지 않는다.** `impl` 은 **첫 번째**
토큰일 때만 이 기능이고, `log` 다음에 오는 `impl` 은 로그 항목의 종류다. 위치가 다르므로
판정에 모호함이 없다.

## CLAUDE.md 트리거 (메인 세션 전용, 참고)

| 시점 | 호출 |
|------|------|
| 전체 경로 착수 보고 시 | `init` |
| PRP 작성 완료 | `step 1 done` + `log impl` |
| 사용자 승인 수령 | `step 2 done` + `step 3 active` |
| 구현 착수 — 세부 작업 목록이 확정됐을 때(선택) | `impl set "<작업1\|…>"` |
| 서브에이전트를 디스패치하기 직전 | `impl <k> active ["담당·범위"]` |
| 서브에이전트 결과 보고를 받은 직후 | `impl <k> done ["결과 요약"]` |
| 구현 완료 | `step 3 done` + `log impl` |
| 검수 PASS / FAIL | `step 4 done|wait` + `log pass|fail` |
| 커밋·푸시 | `log commit` — 자동 발행이 띄운 로컬 서버를 함께 종료한다 |

> `impl` 은 **선택**이다. 세부 작업이 서넛 이하이거나 병렬이 없으면 부르지 않아도 되며, 부르지
> 않으면 카드 자체가 화면에 나타나지 않는다. 갱신 시점은 오케스트레이터가 직접 아는 두 순간
> (디스패치 · 결과 보고)뿐이다 — 서브에이전트는 이 파일에 접근하지 않는다.

> 그룹 모드에서는 `step <n>` 자리에 `step <g>.<p>` 를 쓴다. 한 단계가 여러 그룹에 걸쳐 끝나면
> 그룹 수만큼 호출한다(칸 단위 갱신이 곧 진행률의 단위다).

> `step` 의 네 번째 인자로 한 줄 상세를 붙이면(예: `step 3 active "폴링 스크립트 작성 중"`) 그 단계가
> 지금 무엇을 하고 있는지가 대시보드에 바로 보인다. 생략해도 되며, 생략하면 기존 상세가 유지된다.

> **`init` 은 기존 `.claude/dashboard.html` 을 보존하지 않는다.** 호출될 때마다 파일을 지우고
> 처음부터 새로 만든다 — 이전 작업의 진행 상태도, 작업 추적 로그도 남지 않는다.
> 전체 경로 착수 시 **1회만** 부른다.

---

## 데이터 모델 — DOM 상 표현 규격

상태는 아래 셀렉터와 속성으로만 표현한다. 이 표가 이 문서와 HTML 사이의 계약이다.

> 이 DOM 계약에는 외부 읽기 소비자(`/hub`)가 있다. 불변식 2·5(요소 1줄 1개)를 깨면
> 허브 파서가 조용히 티어를 강등한다 — 자세한 내용은 [`docs/prps/hub-dashboard.md`](../../docs/prps/hub-dashboard.md) 참조.

### 정적(불가침)

`<style>` 블록, `:root` 색 토큰, 카드 골격, 하단 스크립트.

### 동적(치환 대상) — 6 셀렉터

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` **(그룹 1개)** | `class` 속성 + 자식 `.chip` 텍스트 + 자식 `.step-detail` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` / 한 줄 상세(빈 문자열 허용) |
| `#dz-cell-{g}-{p}` **(그룹 2개 이상)** | `data-state` 속성 + 칸 텍스트 | `done`\|`active`\|`wait`\|`na` / `완료`\|`진행중`\|`대기`\|`–` |
| `#dz-log` | 자식 `<li>` **prepend** + `data-server-port` 속성 + **`data-owner-token` 속성** | 로그 항목(최신이 위) / 서빙 중인 로컬 서버 포트(없으면 빈 문자열) / **이 대시보드를 발행한 세션의 소유 토큰** |
| `#dz-updated` | 텍스트 | 갱신 시각 |

진행 시각화 행은 **렌더링 분기에 따라 둘 중 하나**만 존재한다(셀렉터 개수는 여전히 6이며,
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

`data-server-port` 는 새 행이 아니라 `#dz-log` 행의 하위 개념이다 — `log` 절차가 어차피 매번
grep 하는 `#dz-log` 여는 태그에 얹혀 있어야 `log commit` 의 자동 종료가 Bash 호출을 추가하지
않는다. 「자동 발행」과 `serve` 가 쓰고, `log commit` 이 읽은 뒤 비운다. 값은 1024~65535 순수
숫자 또는 빈 문자열이며, **빈 문자열과 속성 부재는 같은 뜻**(서빙 중인 서버 없음)이다.

`data-owner-token` 도 새 행이 아니라 `#dz-log` 행의 하위 개념이다 — `data-server-port` 와 **같은
줄**에 얹혀 있어야 `step`·`impl` 이 grep 패턴 하나(`-e 'id="dz-log"'`)만 더해 소유권을 확인할 수
있고, **Bash 호출은 한 번도 늘지 않는다**. `init` 이 발행 시 **한 번만** 각인하고 `step`·`log`·
`impl` 은 **읽기만** 한다. 값은 소문자 hex 8자리(`[0-9a-f]{8}`) 또는 빈 문자열이며, **빈 문자열과
속성 부재는 같은 뜻**(소유자 미상 — 이 기능 도입 이전에 만들어진 대시보드)이다.

### 구현 세부 작업 슬롯 — 동적 2 + 구조 1 (기본 상태: 비어 있음)

**「동적(치환 대상) — 6 셀렉터」 표는 위 그대로 무수정이다.** 「구현」 매크로 단계 전용 고정
슬롯의 셀렉터는 별도 하위 절로 둔다.

| 셀렉터 | 치환 대상 | 값 | 치환 주체 |
|--------|----------|-----|----------|
| `#dz-impl-{k}` | `class` 속성 + 자식 `.chip` 텍스트 + 자식 `.step-detail` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` / 한 줄 상세(빈 문자열 허용) | `impl <k>` |
| `#dz-impl-count` | 텍스트 | `3/8 · 38%` (매크로 진행률과 **같은 형식**) | `impl set` · `impl <k>` |
| `#dz-impl-tasks` | 자식 `<li>` 목록 | `impl set` 이 **한 번만** 채운다. 이후 항목 단위로만 갱신한다 | `impl set` |

**정적 요소 표에 1행 추가** (`init`/`step`/`log` 가 절대 치환하지 않는 요소):

| 요소 | 역할 |
|------|------|
| `#dz-impl-card` | 「구현 세부 작업」 카드 `<div>`. 템플릿에 **항상** 존재하며, 목록이 비면 CSS `:has()` 가 통째로 숨긴다. DOM 에서 제거하지 않는다 |

> `#dz-impl-card` 는 정적 요소지만 **폴링 동기화 대상**이다. `#dz-log-card` 와 다른 점이
> 여기다 — 로그 카드는 안쪽 `#dz-log` 만 동기화되지만, impl 카드는 안쪽에 별도 동기화 대상이 둘
> (`#dz-impl-tasks`·`#dz-impl-count`)이라 카드째 교체가 더 싸다.

### 불변식 추가 (기존 1~4에 이어)

5. **`<li id="dz-impl-…">` 는 반드시 한 줄에 하나씩 생성한다.** 불변식 2와 같은 이유다 — `impl`
   절차의 grep 앵커와 감사용 `grep -c 'dz-impl-.*class="done"'` 가 줄 단위 계수에 의존한다.
   상세에 줄바꿈을 넣지 않는 규칙(불변식 3)도 그대로 적용된다.
6. **구현 세부 작업의 상태 변화는 매크로 진행률을 바꾸지 않는다.** `impl` 절차는
   `#dz-progress-bar` 와 `#dz-progress-pct` 를 **읽지도 쓰지도 않는다.** 세부 진행은
   `#dz-impl-count` 만 쓴다. 두 분모를 섞으면 `step` 2단계의 전이(±1) 산술이 무너진다.

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
- 위 조건을 만족해도 허브 모달(iframe) 안에서 열린 문서는 `body.dz-embedded` 로 플로팅
  버튼·안내 줄이 CSS 로 숨는다 — 모달을 닫으면 iframe 이 `about:blank` 로 가 opener 문서가
  파괴되므로, 그 안에서 플로팅에 진입하면 되돌아갈 곳이 사라진다. 폴링은 이 판정과 무관하게
  그대로 동작한다.
- 창 높이는 고정값이 아니다. 압축 뷰는 작업 추적 카드가 빠져 콘텐츠가 짧으므로,
  `measureCompactHeight()` 가 여는 시점에 `.wrap` 을 `body.dz-pip` 상태로 순간 측정해 그 실제
  높이(+24px 여백 +`PIP_CHROME_ALLOWANCE` 창 여백)를 PiP 창을 여는 호출의 초기 크기로 넘긴다.
  `PIP_MIN_HEIGHT`~`PIP_MAX_HEIGHT`(200~720) 로 클램프한다. 열린 뒤의 `resizePipToFit()` 는
  Document PiP 의 `resizeTo()` 가 사용자 제스처를 요구해(실측: `NotAllowedError`) rAF·폴링에서
  호출하면 대개 조용히 실패한다 — 그래서 정확한 크기는 여는 시점 한 번에 정해진다.

### 정적 요소 추가 (동적 셀렉터 표에 넣지 않는다)

`init`/`step`/`log` 가 절대 치환하지 않고, **폴링도 동기화하지 않는** 요소다.

| 요소 | 역할 |
|------|------|
| `#dz-pip-btn` | 플로팅 진입/종료 버튼. `.wrap` **바깥**(`<body>` 직계)에 둔다. 허브 모달(iframe) 안에서는 `body.dz-embedded` 로 숨는다(R1) |
| `#dz-pip-hint` | 상태·사유 한 줄. 기본 `hidden`, 스크립트가 텍스트를 넣을 때만 노출 |
| `body.dz-pip` | PiP 창 문서의 `<body>` 에만 붙는 클래스. 좁은 창용 여백 축소 규칙의 스코프 |
| `body.dz-embedded` | `window.self !== window.top` 이면 붙는 클래스. `#dz-pip-btn`·`#dz-pip-hint` 를 숨기는 스코프이며 폴링·동기화와 무관하다(R1) |
| `#dz-log-card` | 「작업 추적」 카드 `<div>`. `init`/`step`/`log` 도, 폴링도 이 요소 자체를 치환하지 않는다. PiP 압축 뷰가 CSS 로 숨기기 위한 유일한 용도이며, DOM 에서 제거하지 않는다 |

> **왜 `.wrap` 바깥인가**: 플로팅은 `.wrap` 서브트리를 **통째로 PiP 창으로 옮기는** 방식이다.
> 버튼이 `.wrap` 안에 있으면 버튼도 같이 옮겨가 (a) 좁은 창을 차지하고 (b) opener 에는 창을 닫을
> 수단이 남지 않는다. 이 배치는 **T22-37 이 줄 번호 비교로 강제**한다.

### 불변식 추가 (기존 1~6에 이어)

8. **`data-server-port` 는 오케스트레이터만 읽고 쓴다 — 스크립트(폴링·PiP)는 이 속성을 읽지도
   쓰지도 않는다.** `syncLog` 가 `innerHTML` 만 대입하므로 라이브 DOM 의 값은 파일과 어긋날 수
   있다. 이 속성에 의존하는 JS 를 추가하는 순간 "낡은 화면 값"과 "파일의 참값"이 갈라지고,
   같은 정보의 출처가 둘이 된다. 파일이 유일한 정답이다.

### 불변식 9 (신설 — 기존 1~6, 8에 이어. **7은 결번**이다)

9. **`data-owner-token` 은 `init` 만 쓴다. `step`·`log`·`impl` 은 읽기만 하고, 스크립트(폴링·PiP)는
   읽지도 쓰지도 않는다.** 불변식 8과 같은 이유이며 보호 장치도 같다 — `syncLog` 가 `innerHTML` 만
   대입하므로 여는 태그의 속성은 폴링 대상이 아니다. 라이브 DOM 의 값이 파일보다 낡아도 무해한
   이유는, 이 값을 읽는 유일한 주체가 **파일을 직접 grep 하는 오케스트레이터**이기 때문이다.
   이 속성에 의존하는 JS 를 추가하는 순간 같은 정보의 출처가 둘이 된다.

### 폴링 동기화 계약 — 무엇을 치환하고 무엇을 보존하는가

이 표가 스크립트와 DOM 사이의 계약이다. 위 「동적(치환 대상) — 6 셀렉터」 표의 **소비자 측 대응표**다.

| 대상 | 동기화 연산 | 근거 |
|------|------------|------|
| `#dz-title` · `#dz-progress-pct` · `#dz-updated` | `textContent` 대입 | 순수 텍스트 노드 |
| `#dz-progress-bar` | `style` 속성 대입 | 인라인 `width:N%` 만 바뀐다. 속성 대입이라 CSS transition 이 살아 있다 |
| `#dz-steps, #dz-matrix` (둘 중 존재하는 것) | `outerHTML` 대입 | **선형/매트릭스 분기를 하나의 연산으로 흡수**한다. 한 파일에 하나만 존재한다는 불변식 1 덕분에 셀렉터 하나로 족하다 |
| `#dz-log` | `innerHTML` 대입 | 항목 prepend·`<details open>` 회수까지 파일이 곧 정답이다. **여는 태그의 속성(`data-server-port`)은 `innerHTML` 대입 대상이 아니어서 폴링이 건드리지 않는다** — 라이브 DOM 의 값은 파일보다 낡을 수 있으며, 그래도 되는 이유는 불변식 8 이다 |
| `input[name="dzf"]` · `label[for^="dzf-"]` · `<style>` | **치환하지 않는다** | 라디오를 재삽입하면 사용자가 고른 유형 필터가 5초마다 초기화된다 |
| `#dz-pip-btn` · `#dz-pip-hint` | **치환하지 않는다** | `.wrap` 바깥 = 동기화 영역 밖 |
| `#dz-impl-card` | `outerHTML` 대입 | 카드 안에 라디오·`<details>` 같은 **사용자 상태가 하나도 없어** 통째 교체가 안전하다. 항목·카운터를 따로 동기화하면 함수가 둘로 늘고, 목록 길이가 바뀌는 `impl set` 순간을 별도로 처리해야 한다 |

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
  결정되므로 선형 화면이 나오고, 그룹명은 화면에 표시되지 않는다(선형 렌더링에는 행 머리가 없다).

### 열(column) 확정 규칙

열 목록 = **모든 그룹의 단계명을 최초 등장 순서로 중복 없이 모은 것**(합집합).

- 모든 그룹이 같은 단계 목록을 가지는 일반적인 경우, 열 목록 = 그 목록이고 `na` 칸은 하나도 생기지 않는다.
- 어떤 그룹에 없는 단계의 자리는 `data-state="na"` 칸이 된다.
- 셀 좌표 `{p}` 는 **열 번호**(합집합 순번)이지 그룹 내 순번이 아니다. 직사각형인 경우 둘은 같다.
- 관례(강제 아님): 게이트처럼 단계가 1개인 그룹은 인자 목록 **맨 뒤**에 둔다. 그래야 그 그룹만의
  고유 열이 표의 오른쪽 끝에 생겨 `na` 칸이 한곳에 모인다.

### 매트릭스 마크업 (`init` 5단계가 생성)

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

> **`init` 은 언제나 대시보드를 처음부터 새로 만든다.** 기존 `.claude/dashboard.html` 이 있으면
> 로그를 포함해 전부 버리고 이번 인자로 새로 그린다. 오케스트레이터에게는 "새 메인 세션인지 같은
> 세션의 다음 작업인지"를 구분할 수단이 없고 — `init` 호출 자체가 유일한 신호다 — 이 파일은
> 기능 단위로 만들고 끝나면 지우는 임시 산출물이다. 그래서 존재 여부로 분기하지 않는다.
>
> 다만 **다른 세션이 지금 쓰고 있을 수 있는 대시보드**는 조용히 지우지 않는다 — 0단계가 그 경우만
> 골라내 확인을 받는다. 그 외(파일 없음 · 30분 이상 방치 · 내가 발행한 것)에는 종전과 정확히 같이
> 동작한다.

0. **다른 세션이 쓰고 있는 대시보드인지 먼저 판정한다.** Bash 1회. 출력 첫 줄은 폐쇄 어휘 3개
   중 하나이며, 파일이 있으면 참고 정보 1~2줄이 뒤따른다.

   ```bash
   if [ ! -f .claude/dashboard.html ]; then echo ABSENT; else
     if [ -n "$(find .claude/dashboard.html -mmin -30)" ]; then echo RECENT; else echo STALE; fi
     grep -o -e 'data-owner-token="[^"]*"' -e 'id="dz-title">[^<]*' .claude/dashboard.html || true
   fi
   ```

   - `30` 은 허브의 `stale_after_minutes` 기본값과 같은 값이다. 두 도구가 "활동 중"을 다른 숫자로
     판정하면 화면과 프롬프트가 어긋난다.
   - 2번째 줄부터는 **순서와 무관하게 접두어로 식별한다**(`data-owner-token="` / `id="dz-title">`).
     토큰 줄이 없으면 이 기능 도입 이전에 만들어진 대시보드다.
   - **`|| true` 를 지우지 않는다** — 토큰이 없는 대시보드에서 `grep` 이 종료 코드 1을 내
     명령 전체가 실패로 보인다.
   - 위 셋이 아닌 출력이 나오거나 명령이 실패하면 **추측하지 말고 `RECENT` 로 본다**(안전한 쪽).

   | 첫 줄 | 파일의 토큰 | 행동 |
   |------|-----------|------|
   | `ABSENT` | — | 1번으로. 묻지 않는다 |
   | `STALE` | 무엇이든 | 1번으로. 묻지 않는다 |
   | `RECENT` | 이번 세션이 각인한 토큰과 **같다** | 1번으로. 묻지 않는다 — 같은 세션의 다음 작업이다 |
   | `RECENT` | 다르다 · 없다 · 이번 세션에 토큰이 없다 | **아래 확인 절차로 간다** |

   **확인 절차** — `AskUserQuestion` 도구가 있으면 선택지 2개로 묻고, 없으면 같은 내용을 평문으로
   묻고 답을 기다린다. **묻기 전에 아무것도 지우지 않는다.**

   - 질문: "`.claude/dashboard.html` 이 30분 이내에 갱신됐습니다 — 다른 메인 세션이 사용 중일 수
     있습니다(현재 제목: 「{제목}」). 어떻게 할까요?"
   - **덮어쓰기**: 기존 대시보드를 지우고 이번 작업으로 새로 발행합니다. 그 세션의 진행 상태와
     작업 추적 로그는 남지 않습니다.
   - **대시보드 없이 진행**: 이번 작업에서는 대시보드를 만들지 않습니다. 기존 파일을 그대로 두고,
     이후 `step`·`log`·`impl` 호출도 생략합니다. 앞으로 계속 끄려면 `/dashboard off` 를 쓰세요.

   「덮어쓰기」 → 1번으로 진행한다.
   「대시보드 없이 진행」 → **절차를 여기서 끝낸다.** 파일을 만들지도 지우지도 않고, 이번 작업
   동안 `/dashboard` 하위 명령을 더 부르지 않는다. `.claude/settings.local.json` 은 **건드리지
   않는다** — 영구 스위치는 `/dashboard off` 의 책임이다.

1. **자리를 비우고 템플릿을 쓴다.** 먼저 Bash 1회:
   ```bash
   mkdir -p .claude && rm -f .claude/dashboard.html && od -An -N4 -tx1 /dev/urandom | tr -d ' \n' && echo
   ```
   `mkdir -p` 도 `rm -f` 도 대상이 없을 때 조용히 성공하므로 존재 확인이 필요 없다.
   **이 제거를 생략하지 않는다** — Write 도구는 이 세션에서 읽지 않은 기존 파일을 덮어쓰지 못한다.
   먼저 지우면 Write 는 언제나 "새 파일 생성"이 되어 절차가 결정적이다.

   마지막 출력 8글자(`[0-9a-f]{8}`)가 **이번 세션의 소유 토큰**이다. 대화 컨텍스트에 기억하고,
   8단계에서 파일에 각인하며, 10단계 보고에 한 줄 적는다. `/dev/urandom` 은 어디에나 있고 `od`·`tr`
   은 POSIX 유틸리티다 — `python3`·`openssl` 에 의존하지 않는다(둘 다 없을 수 있는 환경을 이 문서는
   이미 정상 경로로 다룬다).

   이어서 [템플릿 전문](#템플릿-전문)을 **한 글자도 고치지 않고** 그대로 `.claude/dashboard.html`
   로 Write 한다. 값 채우기는 2번부터의 Edit 이 한다.

   > 아래 모든 Edit 의 `old_string` 은 **방금 쓴 템플릿의 해당 줄 전문 그대로**다. 파일 내용을
   > 우리가 직접 썼으므로 grep 으로 앵커를 찾을 필요가 없다.

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

5. **진행 시각화를 렌더링한다 — 분기 기준은 그룹 수 하나뿐이다.**
   - **그룹이 1개**: 템플릿의 `<ol class="steps" id="dz-steps">` 내부를 아래 `<li>` N개로 채운다
     (기존과 완전히 동일. 1번이 active, 나머지는 wait).
     ```html
     <li id="dz-step-1" class="active"><span class="num">1</span>{단계명}<span class="chip">진행중</span><span class="step-detail"></span></li>
     <li id="dz-step-{n}" class="wait"><span class="num">{n}</span>{단계명}<span class="chip">대기</span><span class="step-detail"></span></li>
     ```
   - **그룹이 2개 이상**: 템플릿의 아래 두 줄(`<ol>` 요소 전체)을 [매트릭스 마크업](#매트릭스-마크업-init-5단계가-생성)의
     `<table>` 로 통째로 치환한다. 각 그룹의 **첫 단계 칸**이 active, 나머지 칸은 wait, 그룹에 없는 단계는 na 다.
     ```html
     <ol class="steps" id="dz-steps">
     </ol>
     ```

6. `#dz-progress-bar` 의 `style` 을 `width:0%` 로, `#dz-progress-pct` 텍스트를 `0/N · 0%` 로 치환한다.

7. `#dz-updated` 를 현재 시각(예: `2026-08-12 17:02`)으로 치환한다.

8. **소유 토큰을 각인한다.** `#dz-log` 는 여전히 **빈 목록**이며 자식은 건드리지 않는다.
   템플릿의 아래 줄을 `old_string` 으로 Edit 1회.
   ```html
   <ul class="log" id="dz-log" data-owner-token="" data-server-port=""></ul>
   ```
   → `data-owner-token` 값만 1단계에서 얻은 토큰으로 채운다.
   각인에 실패해도 `init` 을 중단하지 않는다 — 이후 `step`·`log`·`impl` 이 전부 `SKIP` 판정으로
   떨어질 뿐 기능은 동작한다(「자동 발행」과 같은 실패 비차단 원칙). 다만 그 사실을 보고에 남긴다.

9. 아래 [자동 발행](#자동-발행--init-의-공통-하위-절차) 절차를 수행한다.
   (기존의 `file://` 안내는 자동 발행이 서버를 띄우지 못했을 때의 **폴백 티어**로 그 안에 살아 있다.)

10. **보고**에 "대시보드를 새로 발행했습니다 — 이전 대시보드의 내용(작업 추적 로그 포함)은
    남지 않습니다"를 한 줄 포함한다. 이어서 소유 토큰을 한 줄 적는다: "소유 토큰 `{토큰}` —
    이 세션이 발행한 대시보드입니다."(0단계에서 「대시보드 없이 진행」을 골랐다면 대신 "이번
    작업은 대시보드를 만들지 않습니다 — 기존 대시보드를 그대로 두었습니다"만 보고하고 끝낸다.)

## 소유권 검증 — `step` · `log` · `impl` 의 공통 0단계

입력은 각 절차의 0단계 grep 이 이미 가져온 **`#dz-log` 여는 태그 전문** 하나다.
**Bash 호출을 새로 만들지 않는다.** 판정은 폐쇄 어휘 3개다.

| 파일의 `data-owner-token` | 이번 세션의 토큰 | 판정 | 행동 |
|--------------------------|-----------------|------|------|
| 같다 | 있다 | `MINE` | 그대로 1단계로 진행한다 |
| 다르다 | 있다 | `FOREIGN` | **어떤 Edit 도 하지 않고 중단한다** |
| 속성 없음 · 빈 문자열 | 있든 없든 | `SKIP` | 진행하되 보고에 한 줄 덧붙인다 |
| 무엇이든 | **없다**(이 세션이 `init` 을 부르지 않았거나 토큰을 잃었다) | `SKIP` | 위와 같다 |

- `FOREIGN` 보고: "이 대시보드는 다른 세션이 발행한 것입니다(파일 `{파일값}` ≠ 내 `{내값}`).
  내 대시보드가 다른 세션의 `init` 으로 대체됐습니다 — **이번 갱신은 수행하지 않았습니다.**
  계속 기록하려면 `/dashboard init` 으로 새로 발행하십시오(그 세션의 대시보드는 사라집니다)."
- `SKIP` 보고: "소유 토큰이 없어 소유권을 확인하지 못했습니다 — 갱신은 수행했습니다."
  (내 토큰을 잃은 경우라면 `/dashboard init` 재발행으로 회복된다는 한 줄을 덧붙인다.)
- **`FOREIGN` 에서 다른 파일·다른 셀렉터를 찾아보지 않는다.** 이 판정의 목적은 **조용한 오염을
  감지된 중단으로 바꾸는 것 하나**뿐이다. 복구는 사용자가 정한다.

## `step` — 메인 세션이 수행할 절차 (Bash 1회 + Edit 3회, 결정적)

> 기존 절차는 대상 줄의 전문을 LLM 이 "알고 있다"고 가정했다. 칸이 16개로 늘면 줄 전문을
> 기억한다는 가정이 자주 깨진다. 그래서 `log` 가 이미 검증한 **grep 앵커** 방식으로
> 두 분기(선형/그룹)를 통일한다.

0. **대상 줄과 진행률 줄을 한 번에 확보한다.** Bash 1회:
   ```bash
   grep -n -e 'id="dz-cell-{g}-{p}"' -e 'id="dz-progress-bar"' -e 'id="dz-progress-pct"' -e 'id="dz-log"' .claude/dashboard.html
   ```
   (선형 모드면 첫 패턴을 `id="dz-step-{n}"` 로 바꾼다.)
   각 요소는 한 줄에 하나씩 생성되므로 **결과는 항상 4줄이다**(대상 1 + 진행률 2 + 소유 토큰 1).
   마지막 패턴은 **소유권 검증 전용**이며 Bash 호출을 늘리지 않는다. 이 줄로 위
   [소유권 검증](#소유권-검증--step--log--impl-의-공통-0단계)을 수행하고, `FOREIGN` 이면 **1~3단계를
   전부 생략하고 중단한다.**
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

## `impl` — 「구현」 단계 전용 세부 작업 패널 (메인 세션이 수행할 절차)

> 이 패널은 **오케스트레이터가 직접 관측한 두 시점만** 기록한다. `active` 로 표시된 항목이 "얼마나
> 진행됐는지"는 **서브에이전트 내부의 실시간 진행률이 아니다** — 디스패치 이후 아직 결과 보고가
> 오지 않았다는 뜻일 뿐이다. 서브에이전트가 이 파일에 접근하지 않는다는 원칙
> (`session-dashboard.md` 설계 결정 4)은 이 기능에서도 예외 없이 유지된다.
>
> **동시에 여러 항목이 active 일 수 있다.** 매크로 `step` 과 달리 단일 활성 가정을 두지 않으며,
> 개수를 검증하거나 강제하지 않는다. **구현 세부 작업의 상태 변화는 매크로 진행률을 바꾸지
> 않는다** — `impl` 절차는 `#dz-progress-bar`·`#dz-progress-pct` 를 읽지도 쓰지도 않는다.

### `impl set` — 절차 (Bash 1회 + Edit 3회, 결정적)

0. **대상 줄 3종을 한 번에 확보한다.** Bash 1회:
   ```bash
   grep -n -e 'id="dz-log"' -e 'id="dz-impl-tasks"' -e 'id="dz-impl-count"' -e 'id="dz-impl-1"' .claude/dashboard.html
   ```
   `id="dz-log"` 줄은 **어떤 대시보드에도 항상 1줄** 매칭된다. 이 줄로 위
   [소유권 검증](#소유권-검증--step--log--impl-의-공통-0단계)을 먼저 수행하고(`FOREIGN` 이면 중단),
   **아래 표의 개수는 그 줄을 뺀 나머지로 센다.**
   - **결과 3줄** → 이미 목록이 있다. **이미 목록이 있으면 덮어쓰지 않는다** — 진행 중인 상태를
     날린다. 보고 후 중단하고, 목록을 새로 만들려면 `.claude/dashboard.html` 을 지우고
     `/dashboard init` 부터 다시 하라고 안내한다.
   - **결과 2줄** → 정상. 1번으로 진행한다.
   - **결과 0~1줄** → 이 기능 도입 이전에 만들어진 대시보드다. 마이그레이션하지 않는다.
     보고 후 중단하고 위와 같은 안내를 한다(`.claude/dashboard.html` 은 임시 산출물이다).

1. **인자 파싱** — 두 번째 인자를 `|` 로 나눈다. 결과가 작업 목록이고 개수를 `K` 라 한다.
   그룹 문법(`:`)은 **없다** — 세부 작업 목록은 평면이다. 작업명에 `|` 를 쓰지 않는다.

2. **목록 생성** — 0에서 얻은 `id="dz-impl-tasks"` 줄 전문을 `old_string` 으로 Edit 1회.
   그 줄 **뒤에** 아래 `<li>` 를 K개 삽입한다. **전부 `wait` 이고 상세는 빈 span 이다.**
   ```html
      <li id="dz-impl-{k}" class="wait"><span class="num">{k}</span>{작업명}<span class="chip">대기</span><span class="step-detail"></span></li>
   ```
   - **한 줄에 하나씩** 쓴다(불변식 5).
   - `<span class="step-detail"></span>` 안에 **공백조차 넣지 않는다**(`:empty` 매칭이 풀린다).
   - 작업명은 `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` 순서로 이스케이프한다.
   - **첫 항목을 `active` 로 만들지 않는다.** `init` 이 1번 단계를 active 로 두는 것과 다르다 —
     목록 정의와 디스패치는 다른 시점이고, 부르지도 않은 서브에이전트를 진행중으로 그리면
     이 패널의 유일한 신뢰 근거(관측된 두 시점만 기록)가 깨진다.

3. `#dz-impl-count` 텍스트를 `0/K · 0%` 로 Edit 1회.
4. `#dz-updated` 텍스트를 현재 시각으로 Edit 1회.

### `impl <k>` — 절차 (Bash 1회 + Edit 3회, `step` 과 동일 구조)

0. **대상 줄과 세부 진행률 줄을 한 번에 확보한다.** Bash 1회:
   ```bash
   grep -n -e 'id="dz-impl-{k}"' -e 'id="dz-impl-count"' -e 'id="dz-log"' .claude/dashboard.html
   ```
   각 요소는 한 줄에 하나씩 생성되므로 **결과는 항상 3줄이다.** 마지막 줄로 위
   [소유권 검증](#소유권-검증--step--log--impl-의-공통-0단계)을 수행하고, `FOREIGN` 이면 1~3단계를
   생략하고 중단한다.
   - 대상 줄이 안 나온다 → 인덱스가 틀렸거나 `impl set` 을 부른 적이 없다. **다른 항목을 추측해서
     고치지 말고 보고 후 중단한다.** 인덱스를 잊었으면 `grep -n 'dz-impl-[0-9]'` 로 목록 전체
     지도를 한 번에 얻는다.

1. **상태 치환** — 0에서 얻은 줄 전문을 `old_string` 으로 Edit 1회.
   `class="{state}"` 와 자식 `.chip` 텍스트를 바꾼다. `.step-detail` 갱신 규칙은
   `step` 절차 1단계의 표(생략=유지 / `"내용"`=치환 / `""`=지움)와 **완전히 동일**하다.
   이스케이프·줄바꿈 금지 규칙도 그대로 적용된다.
   - **동시에 여러 항목이 active 일 수 있다.** 다른 항목의 상태를 확인하거나 되돌리지 않는다.
     이 호출은 지정된 한 항목만 건드린다.

2. **세부 진행률 재계산** — 0에서 읽은 `#dz-impl-count` 텍스트가 `"M/K · P%"` 이므로 M·K 를 그대로
   얻는다. 완료 항목 수는 다시 세지 않고 **전이로 계산한다**(`step` 2단계와 같은 산술):
   - 이전 상태 ≠ done 이고 새 상태 = done  → M+1
   - 이전 상태 = done 이고 새 상태 ≠ done  → M-1
   - 그 외                                  → M 그대로

   P = round(M/K × 100). M 이 바뀌지 않았으면 이 단계를 건너뛴다.
   **`#dz-progress-bar`·`#dz-progress-pct` 는 건드리지 않는다**(불변식 6).

3. `#dz-updated` 텍스트를 현재 시각으로 치환한다. (Edit 1회)

**감사(audit)용 재계수** — 세부 진행률이 어긋난 것 같으면 아래로 다시 센다.
```bash
grep -c 'dz-impl-[0-9].*class="done"' .claude/dashboard.html
```

## `log` — 메인 세션이 수행할 절차 (Bash grep 1회 + Read 1~2회 + Edit 2회, 결정적)

> `commit` 인자일 때만 여기에 **Bash 1회 + Edit 1회**가 더해진다(3단계). 나머지 세 인자의
> 비용과 결과는 종전과 완전히 같다.

0. **최신 항목만 확인한다(파일 전체를 Read하지 않는다)**:
   a. Bash 로 `grep -n 'id="dz-log"' .claude/dashboard.html` 를 실행해 로그 시작 줄 번호 `L` 과
      그 줄의 전문을 얻는다. `id="dz-log"` 는 문서 내 유일 문자열이다(`<style>` 과 헤더 주석의
      `#dz-log` 는 `id=` 형태가 아니라 매칭되지 않는다). 태그 전문은 `data-server-port` 값이
      상황마다 달라지므로, grep 은 반드시 이 부분일치 패턴을 쓴다 — 완전일치는 속성이 붙는
      순간 영원히 매칭에 실패한다.

      이 줄의 `data-owner-token` 값으로 위 [소유권 검증](#소유권-검증--step--log--impl-의-공통-0단계)을
      수행한다. **grep 을 추가하지 않는다 — 이미 읽은 줄이다.** `FOREIGN` 이면 1·2·3단계를 전부
      생략하고 중단한다(`commit` 인자여도 서버를 끄지 않는다 — 그 서버는 다른 세션의 것이다).
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
   뒤에 `data-seq="S+1"` 인 새 `<li>` 를 위
   [로그 항목 스키마](#로그-항목-스키마)대로 삽입한다(태그 텍스트가 상황마다 다르므로
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

3. **자동 종료 — 첫 인자가 `commit` 일 때만 수행한다.**
   `impl`·`pass`·`fail` 호출은 이 단계를 **건너뛴다**(0~2단계로 끝나며 결과가 종전과 동일하다).

   a. **포트 판정** — 0-a 에서 읽은 `#dz-log` 여는 태그의 `data-server-port="{포트}"` 값을 본다.
      새 Bash 호출을 하지 않는다. 그 줄에 이미 적혀 있다.

      | `{포트}` | 행동 |
      |---------|------|
      | 속성 없음 · 빈 문자열 | **아무것도 하지 않는다.** 보고도 하지 않는다(서버가 없는 것이 정상 상태다) |
      | 1024~65535 범위의 순수 숫자 | b 로 진행 |
      | 그 밖의 값 | 아무것도 하지 않고 그 사실만 한 줄 보고한다. **받은 값을 셸 명령에 치환하지 않는다** (`serve` 0단계와 같은 검증이다) |

   b. **종료** — Bash 1회. `{포트}` 는 a 를 통과한 숫자다.

          sleep 6 && pkill -f "http.server {포트} --bind 127.0.0.1"

      - **`sleep 6` 을 지우지 않는다.** 2단계가 방금 쓴 커밋 항목을 브라우저가 가져갈 시간이다
        (`POLL_INTERVAL_MS` = 5초 + 여유 1초). 이것이 없으면 서버가 먼저 죽어 플로팅 창이
        **커밋 직전** 화면에서 얼어붙는다 — 이 기능이 보여주려던 바로 그 화면을 놓친다.
      - `pkill` 패턴은 `serve` 4단계와 **글자 하나까지 같다**(복제해 변형하지 않는다).
        `--bind 127.0.0.1` 까지 포함해야 다른 프로세스의 부분 일치를 죽이지 않는다.
      - **종료 코드 1(해당 프로세스 없음)은 에러가 아니다.** 사용자가 이미 손으로 껐다는
        뜻이므로 조용히 c 로 넘어간다 — 다만 이 경우 d 의 보고 문구를 다르게 고른다(아래 표).

   c. **각인 해제** — Edit 1회. `data-server-port="{포트}"` → `data-server-port=""`.
      이 문자열은 문서 내 유일하므로 줄 전문을 다시 읽지 않는다. 비워 두지 않으면 같은 세션에서
      `log commit` 이 두 번 불릴 때(수정 커밋 등) 그 사이 그 포트를 차지한 **다른 서버**를 끈다.

   d. **보고 1줄** — b 의 pkill 종료 코드로 문구를 고른다. **무조건 "종료했습니다"로 단정하지
      않는다** — 이미 꺼져 있던 경우(종료 코드 1) 그 표현은 사실과 어긋난다:

      | pkill 종료 코드 | 보고 문구 |
      |----------------|----------|
      | 0(정상 종료) | 로컬 서버(포트 {포트})를 종료했습니다 — 이미 열려 있는 플로팅 창은 마지막 화면 그대로 남습니다. 다시 보려면 `/dashboard serve {포트}`. |
      | 1(이미 꺼져 있었음) | 로컬 서버(포트 {포트})는 이미 종료돼 있었습니다 — 각인만 정리했습니다. 다시 보려면 `/dashboard serve {포트}`. |

---

## 자동 발행 — `init` 의 공통 하위 절차

> `init` 의 마지막 단계(9단계)가 이 절차를 부른다.
> **`step`·`log`·`impl` 은 이 절차를 부르지 않는다** — 서버를 띄우지도, 브라우저를 열지도 않는다.
> 세션 중 수십 번 불리는 명령이 프로세스를 만들거나 창을 띄우면 안 된다.
>
> **이 절차의 어떤 실패도 `init` 을 중단시키지 않는다.** 대시보드 파일은 이미 만들어졌고
> 그것이 본체다. 서버·브라우저는 편의이며, 실패는 에러가 아니라 **한 티어 낮은 안내**로 처리한다.

### 발행 티어 — 위에서부터 시도하고, 안 되면 조용히 내려앉는다

| 티어 | URL | 조건 | 얻는 것 |
|------|-----|------|--------|
| 1 | `http://localhost:{포트}/dashboard.html` | 서버 재사용 또는 기동 성공 | 5초 폴링 자동 갱신 + 플로팅 버튼 활성(**단독 탭에서만** — 허브 모달 안에서는 숨는다) |
| 2 | `file://{절대경로}/.claude/dashboard.html` | 서버 불가(python3 없음 · 후보 포트 전부 점유 · 기동 실패) | 포커스 시 갱신 |

**브라우저 열기는 티어와 직교한다.** 티어 1·2 어느 쪽이든 아래 [3-a](#3-a-열기-대상-확정--허브가-살아-있으면-허브를-연다)
가 정한 **열기 대상 URL** 에 대해 아래 「브라우저 열기」를 시도하고, 그마저 불가능하면 URL 을
출력해 사용자가 직접 열게 한다. 즉 최악의 결과가 **현재 동작과 정확히 같다** — 이 기능은
어떤 환경에서도 기존 경험을 나쁘게 만들지 않는다.

### 1. 서버 가용성 확인

`python3 --version` 이 실패하면 **티어 2로 내려간다**(3번으로). 다른 서버를 설치하지 않는다.

### 2. 포트 스캔 — Bash 1회, 결과는 3형태 중 하나

후보 포트는 **8791 · 8792 · 8793** 이다(`serve` 의 기본 포트에서 시작해 3개).
아래를 그대로 실행한다. 셸이 변수 확장을 하지 않도록 `$` 를 쓰지 않는다.

```bash
python3 -c "
import socket, urllib.request, pathlib
mine = pathlib.Path('.claude/dashboard.html').read_bytes()
free = None
for port in (8791, 8792, 8793):
    if socket.socket().connect_ex(('127.0.0.1', port)) != 0:
        if free is None: free = port
        continue
    try:
        got = urllib.request.urlopen('http://127.0.0.1:%d/dashboard.html' % port, timeout=1).read()
    except Exception:
        continue
    if got == mine:
        print(port, 'REUSE'); raise SystemExit
print(free, 'FREE') if free else print('NONE')
"
```

출력은 반드시 아래 셋 중 하나다. **다른 해석을 만들지 않는다.**

| 출력 | 의미 | 다음 행동 |
|------|------|----------|
| `{포트} REUSE` | 그 포트에서 **이 프로젝트의 대시보드**가 이미 서빙 중이다 | 기동하지 않는다. 3번으로 (`started=false`) |
| `{포트} FREE` | 그 포트가 비어 있다 | 아래 2-a 로 기동한 뒤 3번으로 (`started=true`) |
| `NONE` | 후보 3개가 전부 **다른 프로젝트**의 서버다 | **티어 2로 내려간다.** 3번으로. 보고에 "포트 8791~8793 이 다른 대시보드에 쓰이고 있습니다. `/dashboard serve stop <포트>` 로 정리할 수 있습니다"를 덧붙인다 |

- **`REUSE` 가 `FREE` 보다 우선한다.** 위 명령이 이미 그 순서를 보장한다 — 재사용 대상을 찾으면
  즉시 끝내고, 못 찾았을 때만 가장 낮은 빈 포트를 낸다. **이 우선순위가 없으면 같은 프로젝트에
  서버가 계속 쌓인다.**
- 명령 자체가 실패하거나(파일 없음 등) 위 셋이 아닌 출력이 나오면 **추측하지 말고 티어 2로 내려간다.**

**2-a. 기동** — `serve` 절차 3단계의 명령을 **그대로** 쓴다(복제해 변형하지 않는다).
`{포트}` 만 스캔이 확정한 값으로 채운다.

    DZ_DIR=$(mktemp -d) && ln -s "$PWD/.claude/dashboard.html" "$DZ_DIR/dashboard.html" \
      && python3 -m http.server {포트} --bind 127.0.0.1 --directory "$DZ_DIR"

- Bash 도구의 **백그라운드** 옵션으로 실행한다.
- `--bind 127.0.0.1` 은 **생략 금지**다(`serve` 와 같은 이유 — 기본값은 모든 인터페이스다).
- 기동 직후 그 백그라운드 태스크의 출력을 **한 번** 확인한다. `Address already in use` 가 보이면
  스캔과 기동 사이에 다른 세션이 그 포트를 채간 것이다. **다른 포트를 추측하지 말고 티어 2로
  내려간다**(3번으로). 이 경합은 드물고, 폴백이 이미 준비돼 있다.
- **`nohup`·`setsid` 로 프로세스를 분리하지 않는다.** 세션에 매인 수명이 의도된 기본값이다.

### 3. URL 확정과 포트 각인

- 티어 1: `http://localhost:{포트}/dashboard.html`
- 티어 2: `file://<현재 작업 디렉토리 절대경로>/.claude/dashboard.html`

확정된 티어에 따라 아래 [포트 각인](#포트-각인--자동-발행--serve-의-공통-하위-절차) 절차를
**반드시** 수행한다. 이 URL 이 **대시보드 URL** 이다(보고·각인용 — 실제로 브라우저에 여는
URL 은 아래 3-a 가 별도로 정한다).

| 티어 | 각인할 값 | 왜 |
|------|----------|-----|
| 1 | `{포트}` | `REUSE`·`FREE` 어느 쪽이든 그 포트에서 **이 프로젝트의 대시보드**가 서빙 중이다(스캔이 바이트 비교로 이미 확인했다) |
| 2 | 빈 문자열 | 서버가 없다. **직전 세션이 남긴 낡은 값을 반드시 지운다** — 그 사이 그 포트를 다른 프로젝트가 차지했을 수 있고, 지우지 않으면 `log commit` 이 남의 서버를 끈다 |

> 스캔은 `127.0.0.1` 로 확인하고 안내는 `localhost` 로 한다. 스캔은 **바인딩한 그 주소**를 정확히
> 찔러야 하고, 사용자 대면 URL 은 `serve` 5단계가 이미 쓰던 표기와 같아야 하기 때문이다.
> 브라우저에서 `localhost` 가 안 열리면 `http://127.0.0.1:{포트}/dashboard.html` 을 안내한다.

### 3-a. 열기 대상 확정 — 허브가 살아 있으면 허브를 연다

> 3번이 확정한 것은 **대시보드 URL**(보고·각인용)이다. 이 단계는 **브라우저로 열 URL** 만
> 따로 정한다. 통합 허브(`/hub`) 서버가 살아 있으면 프로젝트 대시보드 대신 **허브 페이지**를
> 연다 — 허브에서 이 프로젝트 카드를 클릭하면 같은 대시보드가 모달로 열리므로, 여러
> 프로젝트를 함께 보는 화면이 진입점이 되는 편이 낫다.

허브 생존 판정은 허브의 공개 인터페이스인 `hub.py server-status --json` 하나로 한다 — 그
출력의 `alive`·`http_ok`·`record.port` 세 필드만 읽는다. Bash 1회. 셸이 변수 확장을 하지
않도록 `$` 를 쓰지 않는다(2번과 같은 관례).

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

### 4. 브라우저 열기 — 되면 하고, 안 되면 **조용히** 넘어간다

여기서 `<URL>` 은 3-a 가 정한 **열기 대상 URL** 이다.

아래 순서로 **한 번씩만** 시도한다. **재시도하지 않고, 루프를 돌지 않고, 실패를 에러로 보고하지
않는다.** 성공하면 즉시 5번으로 간다.

1. **이 세션에 URL 을 여는 도구가 이미 있으면 그것을 쓴다.** 브라우저 pane, 브라우저 MCP 서버 등
   **지금 사용 가능한 도구 목록에 실제로 존재하는** 것만 해당한다. **없다고 새로 설치하거나
   설정하지 않는다.**
   - 그 도구가 탭 목록 조회·탭 선택(select/activate/focus 계열) 도구를 **함께 제공하면**,
     navigate 직후 방금 연 탭을 **전면으로 올리는 호출을 한 번만** 더 한다. navigate 만으로는
     탭이 백그라운드에 열려 사용자가 보던 화면이 그대로일 수 있다.
   - 그런 도구가 **없으면 navigate 로 끝낸다.** 없는 기능을 다른 수단으로 흉내 내지 않는다
     (「없으면 설치하지 않는다」와 같은 원칙이다).
   - 두 호출 모두 **한 번씩만** 하고, 실패는 무시하고 5번으로 간다.
2. **없으면 OS 경로로 간다.** `$SSH_CONNECTION` 이 설정돼 **있으면** 원격 세션이므로 2-a·2-b 를
   **모두 건너뛴다** — 명령이 열어 봐야 사용자가 보는 화면이 아니고, 애초에 그 포트는 원격
   머신 것이다.

**2-a. (macOS 만) 이미 열린 탭을 찾아 앞으로 가져온다.** `uname -s` 가 `Darwin` 일 때만 의미가
있다. Bash 1회, 출력은 폐쇄 어휘 3개(`FOCUSED`/`NOTFOUND`/`UNSUPPORTED`) 중 하나다.
`{열기 대상 URL}` 만 채우고 나머지는 그대로 쓴다. **아래 코드는 들여쓰기 없이 그대로 옮긴다**
— heredoc 종료 표시(`APPLESCRIPT`)는 줄 맨 앞에 있어야만 유효하다.

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

**2-b. `FOCUSED` 가 아니면 기존 OS 기본 열기 명령을 시도한다.**
- `uname -s` 결과가 `Darwin` → `open "<URL>"`
- `uname -s` 결과가 `Linux` **이고** `$DISPLAY` 또는 `$WAYLAND_DISPLAY` 중 하나가 설정돼 있다
  → `xdg-open "<URL>"`
- 그 밖의 경우(판정 불가, 헤드리스, 컨테이너) → **시도하지 않는다.**
- `open`/`xdg-open` 은 **기본이 곧 포커스**다. macOS 에서 `-g`(백그라운드) 옵션을 **붙이지
  않는다** — 붙이면 탭은 열리지만 창이 뒤에 남아 이번 요구가 무너진다.

3. **둘 다 못 하면 아무것도 하지 않는다.** 5번의 보고에 URL 이 이미 들어 있으므로 사용자가 직접 연다.

> 명령이 실패했는지 성공했는지 **깊이 판정하지 않는다.** 종료 코드가 0 이 아니면 열지 못한 것으로
> 보고 그대로 5번으로 간다. 브라우저가 실제로 떴는지를 확인할 방법은 없고, 확인하려 들면
> 절차가 비결정적이 된다.

### 5. 보고 — 한 덩어리로 한 번만

| 상황 | 보고에 반드시 포함 |
|------|------------------|
| 허브를 연 경우(3-a `HUB`) | 허브 URL(`http://localhost:{포트}/hub.html`) · "허브 페이지를 열었습니다 — 이 프로젝트 카드를 클릭하면 이 대시보드가 모달로 열립니다" · **대시보드 URL 도 함께** 표기(플로팅 창은 이 단독 탭에서만 동작합니다) |
| 티어 1 · 기동함 | URL · "5초마다 자동 갱신됩니다" · `/dashboard serve stop {포트}` (끝나면 서버를 끄라는 안내) · 최초 1회라면 `Bash(python3 -m http.server:*)`·`Bash(open:*)` 등을 허용 목록에 추가하면 다음부터 권한 프롬프트가 사라진다는 안내 한 줄 |
| 티어 1 · 재사용 | URL · "이미 떠 있는 서버를 재사용했습니다" · `/dashboard serve stop {포트}` |
| 티어 2 | `file://` URL · "자동 갱신이 아니라 창에 포커스를 줄 때 갱신됩니다" · 내려앉은 사유 한 줄 |
| 브라우저를 못 연 경우 | 위에 더해 "브라우저에서 직접 열어 주세요" 한 줄 |

**서버가 세션 종료 후에도 남을 수 있다**는 사실을 티어 1 보고에 **매번** 적는다. 정리 명령은
포트를 포함한 완전한 형태(`/dashboard serve stop 8792`)로 쓴다 — 자동 경로는 8791 이 아닐 수 있고,
포트를 빼면 `stop` 이 기본값 8791 을 죽이러 가서 엉뚱한 서버를 끈다.

**탭 재사용(2-a)을 쓰려면 최초 1회 자동화(Automation) 권한 승인이 필요하다** — 기존 허용 목록
안내와 같은 자리에 한 줄로 덧붙인다: "탭 재사용을 쓰려면 최초 1회 자동화(Automation) 권한
승인이 필요합니다 — 거부해도 새 탭으로 열리며 다른 동작에는 영향이 없습니다."

### 포트 각인 — 「자동 발행」 · `serve` 의 공통 하위 절차

입력은 각인할 값 `{포트}` 하나다(포트 숫자 또는 빈 문자열). **호출자가 이미 1024~65535 검증을
통과시킨 숫자이거나 빈 문자열이어야 한다 — 사용자 인자를 여기로 직접 넘기지 않는다.**
**Bash 1회 + Edit 0~1회.**

1. `grep -n 'id="dz-log"' .claude/dashboard.html` 로 여는 태그의 줄 번호와 전문을 얻는다.
2. **현재 값이 이미 `{포트}` 와 같으면 이 단계를 생략한다**(이 경우 이 절차의 비용은 Bash 1회뿐이다
   — `old_string` 과 `new_string` 이 같은 Edit 은 실패한다). 다르면 Edit 1회로 그 줄을 치환한다.
   `old_string` 은 1에서 읽은 전문을 그대로 쓴다.
   - `data-server-port="…"` 가 이미 있으면 **값만** `{포트}` 로 바꾼다.
   - 없으면(이 기능 도입 이전에 만들어진 대시보드) 여는 태그의 `>` **바로 앞**에
     ` data-server-port="{포트}"` 를 삽입한다.
3. **이 절차의 실패는 호출자를 중단시키지 않는다.** 각인이 없으면 `log commit` 이 아무것도 하지
   않을 뿐이고, 사용자는 `/dashboard serve stop {포트}` 로 언제든 직접 끌 수 있다
   (「자동 발행」의 실패 비차단 원칙과 같다).

이 절차는 `data-owner-token` 을 **읽지도 바꾸지도 않는다.** `old_string` 이 1번에서 읽은 줄
전문이므로 토큰은 그대로 보존된다(불변식 9).

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
   - **기동에 성공했으면**(위 오류 없이 백그라운드 태스크가 살아 있으면) 위
     [포트 각인](#포트-각인--자동-발행--serve-의-공통-하위-절차) 절차로
     `{포트}` 를 각인한다. 실패해 보고하고 끝나는 경로에서는 각인하지 않는다.

4. `stop`: `pkill -f "http.server {포트} --bind 127.0.0.1"` 를 실행하고 결과를 보고한다.
   (0단계에서 정한 대상 포트를 쓴다. 패턴에 `--bind 127.0.0.1` 까지 포함해 다른 프로세스의
   부분 일치를 죽이지 않는다. 임시 디렉토리는 OS 가 정리하므로 따로 지우지 않는다.)
   실행 후, 위 [포트 각인](#포트-각인--자동-발행--serve-의-공통-하위-절차) 절차의 1번(grep)을
   그대로 수행해 `#dz-log` 의 현재 `data-server-port` 값을 읽는다(새 Bash 호출을 늘리지 않는다
   — 이 grep 이 곧 그 1번이다). 그 값이 **이번에 중지한 포트와 같으면** 방금 읽은 결과를 이어
   [포트 각인](#포트-각인--자동-발행--serve-의-공통-하위-절차) 절차의 2번(Edit)으로 빈 문자열을
   각인한다. **다르면 건드리지 않는다** — 다른 서버에 대한 기록이다.
   낡은 각인이 남으면 `log commit` 의 자동 종료가 그 사이 그 포트를 차지한 **다른 프로젝트의
   서버**를 끌 수 있다. 이 한 줄이 그 경로를 막는다.

5. 위 [자동 발행](#자동-발행--init-의-공통-하위-절차) 4번 「브라우저 열기」를 수행한 뒤 보고한다:
   `http://localhost:{포트}/dashboard.html` 을 출력하고
   "이 URL 로 열어야 우상단 「플로팅」 버튼이 활성화된다"를 한 줄 덧붙인다.
   작업이 끝나면 `/dashboard serve stop {포트}` 로 서버를 끄도록 안내한다.
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
래퍼 `div` 로 감싸면 `~` 결합자가 `#dz-log` 에 닿지 않으므로 감싸지 않는다. 라디오·라벨·
`#dz-log` 는 모두 `.card` 의 직계 형제여야 하며, `display:contents` 로도 우회할 수 없다 —
형제 결합자는 박스 트리가 아니라 DOM 트리로 판정하기 때문이다. 라디오 그룹은 유형 필터
(`name="dzf"`, 전체/구현/검수) 하나뿐이며 템플릿에 고정 3개다.

```html
<div class="log-title">작업 추적</div>
<input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
<input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
<input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
<ul class="log" id="dz-log" data-server-port="">…</ul>
```

```css
/* 유형 필터 — 템플릿 고정 */
.dzf{position:absolute;opacity:0;pointer-events:none}
#dzf-impl:checked   ~ #dz-log .entry:not([data-kind="impl"]){display:none}
#dzf-review:checked ~ #dz-log .entry:not([data-kind="review"]){display:none}
```

라디오는 시각적으로 숨기되 포커스는 유지한다(`display:none` 이 아니라 `opacity:0`).
`:has()` 같은 최신 셀렉터에 의존하지 않으므로 지원 범위가 넓다. 유형 필터는 알약(pill)
형태다.

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
  #dz-progress-bar      : inline style width:N%
  #dz-progress-pct      : 진행률 텍스트 (예: 3/6 · 50%)
  #dz-step-{n}          : [그룹 1개] 각 단계 li — class(done|active|wait) + .chip 텍스트
                          + .step-detail 텍스트(그 단계의 한 줄 상세. 비어 있으면 CSS 가 숨긴다)
  #dz-cell-{g}-{p}      : [그룹 2+] 매트릭스 칸 td — data-state(done|active|wait|na) + 칸 텍스트
                          {g}=행(그룹) 번호, {p}=열(단계) 번호. 한 파일에 step/cell 이 공존하지 않는다
  #dz-group-{g}         : [그룹 2+] 행 머리 th — init 이 그룹명을 넣고 이후 치환하지 않는다
  #dz-log               : 작업 추적 ul — li data-seq 앵커로 prepend / data-server-port 속성(이
                            대시보드를 서빙 중인 로컬 서버 포트. 비어 있으면 서버 없음. 오케스트레이터만
                            읽고 쓴다 — 스크립트는 건드리지 않는다)
                          / data-owner-token 속성(이 대시보드를 발행한 세션의 소유 토큰. init 만
                            각인하고 step·log·impl 은 읽기만 한다 — 스크립트는 건드리지 않는다)
  #dz-updated           : 갱신 시각 텍스트
  #dz-impl-{k}          : [선택] 구현 세부 작업 li — class(done|active|wait) + .chip 텍스트
                          + .step-detail 텍스트. active 가 동시에 여러 개일 수 있다
  #dz-impl-count        : [선택] 구현 세부 진행 텍스트 (예: 3/8 · 38%). 매크로 진행률과 별개다
  #dz-impl-tasks        : [선택] 세부 작업 ol — impl set 이 한 번 채운다
정적(불가침): 골격 · <style> · 제목 · 하단 스크립트
  #dz-pip-btn / #dz-pip-hint : 플로팅 진입 버튼과 안내 한 줄. .wrap 바깥에 있으며
                               init/step/log 도, 폴링 동기화도 이 둘을 건드리지 않는다
  #dz-log-card               : 작업 추적 카드 div. PiP 압축 뷰가 CSS 로만 숨긴다
                               (DOM 에서 제거하지 않는다 — 복귀 시 로그가 사라진다)
  #dz-impl-card              : 구현 세부 작업 카드 div. 목록이 비면 CSS :has() 가 통째로 숨긴다
                               (DOM 에서 제거하지 않는다 — 폴링이 outerHTML 로 동기화한다)
  body.dz-embedded           : 허브 모달(iframe) 안에서 열렸다는 표시. #dz-pip-btn/#dz-pip-hint 를
                               CSS 로만 숨기는 스코프일 뿐 폴링·동기화와는 무관하다
-->
<style>
  :root{--ink:#172033;--muted:#5E6B7D;--line:#D9E2EC;--soft:#F4F7FB;--blue:#1E5AA8;--navy:#12335B;--green:#1F8A70;--orange:#F59E0B;--red:#C2410C;}
  *{box-sizing:border-box}
  body{margin:0;font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:var(--ink);background:#EEF3F8;line-height:1.55}
  .wrap{max-width:860px;margin:32px auto;padding:0 16px}
  .card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:26px 30px;box-shadow:0 8px 24px rgba(19,51,91,.07);margin-bottom:16px}
  h1{font-size:21px;margin:0 0 4px;color:var(--navy);letter-spacing:-.5px}
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
  #dz-impl-card:not(:has(#dz-impl-tasks li)){display:none}
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
  ul.log{list-style:none;margin:6px 0 0;padding:0;font-size:13px;color:#4B5A6D}
  .entry{border-bottom:1px solid var(--soft);padding:8px 4px}
  .entry:last-child{border-bottom:0}
  .entry summary{cursor:pointer;display:flex;align-items:center;gap:8px;list-style:none}
  .entry summary::-webkit-details-marker{display:none}
  .entry summary::marker{content:""}
  .entry .time{font-size:11px;color:var(--muted);flex:none;width:40px}
  .entry .lead{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;color:var(--ink)}
  .entry .detail{margin:6px 0 0 48px;font-size:12.5px;color:var(--muted);white-space:pre-wrap}
  .log-title,.impl-title{font-size:13px;font-weight:700;color:var(--muted);margin:0 0 10px}
  .foot{font-size:12px;color:var(--muted);text-align:right}
  #dz-pip-btn{position:fixed;top:18px;right:18px;z-index:9;font-family:inherit;font-size:12px;font-weight:700;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--navy);cursor:pointer;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-btn:disabled{color:var(--muted);cursor:not-allowed;box-shadow:none}
  #dz-pip-hint{position:fixed;top:54px;right:18px;z-index:9;max-width:300px;font-size:11px;line-height:1.5;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 10px;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-hint[hidden]{display:none}
  /* 허브 모달(iframe) 안에서 열린 문서는 body.dz-embedded 가 붙는다 — 플로팅은 iframe 안에서
     구조적으로 깨진다(모달을 닫으면 iframe 이 about:blank 로 가 opener 문서 자체가 파괴된다).
     CSS 로만 숨긴다 — DOM 제거는 이 파일의 기존 불변식(id="dz-pip-*" 유지)을 어긴다. */
  body.dz-embedded #dz-pip-btn,body.dz-embedded #dz-pip-hint{display:none}
  body.dz-pip .wrap{margin:10px auto;padding:0 10px}
  body.dz-pip .card{padding:14px 16px;border-radius:10px;margin-bottom:10px}
  body.dz-pip h1{font-size:16px}
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
    <div class="bar-outer"><div class="bar-inner" id="dz-progress-bar" style="width:0%"></div></div>
    <div class="pct" id="dz-progress-pct">0/0 · 0%</div>
    <ol class="steps" id="dz-steps">
    </ol>
  </div>
  <div class="card" id="dz-impl-card">
    <div class="impl-title">구현 세부 작업 · 디스패치와 결과 보고 시점에만 갱신</div>
    <div class="pct" id="dz-impl-count">0/0 · 0%</div>
    <ol class="steps" id="dz-impl-tasks">
    </ol>
  </div>
  <div class="card" id="dz-log-card">
    <div class="log-title">작업 추적</div>
    <input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
    <input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
    <input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
    <ul class="log" id="dz-log" data-owner-token="" data-server-port=""></ul>
  </div>
  <div class="foot" id="dz-updated">갱신: -</div>
</div>
<button id="dz-pip-btn" type="button">플로팅</button>
<div id="dz-pip-hint" hidden></div>
<script>
(function(){
  var POLL_INTERVAL_MS = 5000;          // 로컬 파일 폴링 주기
  var FAILURE_LIMIT = 3;                // 연속 실패 이 횟수부터 사용자에게 알린다
  var PIP_WIDTH = 420;
  var PIP_MIN_HEIGHT = 200, PIP_MAX_HEIGHT = 720;
  // documentPictureInPicture 창의 요청 height 는 콘텐츠 높이가 아니라 outerHeight(제목
  // 표시줄 포함) 로 해석된다(실측). 그 여백은 OS·브라우저마다 달라 미리 알 수 없다 — 창을
  // 연 직후 outerHeight-innerHeight 를 재서 다음 열기부터 보정하는 방식도 시도했으나,
  // .then() 시점엔 창 크기가 아직 안정되지 않아 값이 널뛰어 더 위험했다(실측: 두 번째
  // 열기에서 요청 높이가 음수로 접혀 200px 바닥으로 떨어짐). 그래서 실측 보정 대신 여러
  // 환경에서 관찰한 제목 표시줄 여백보다 넉넉한 고정값을 쓴다 — 몇십 px 여백이 남는 것이
  // 콘텐츠가 잘리는 것보다 안전하다.
  var PIP_CHROME_ALLOWANCE = 100;
  var PIP_CONTENT_PADDING = 24;         // 콘텐츠 하단 여백(카드 그림자·라운딩 여유)

  var wrap = document.querySelector('.wrap');
  var pipButton = document.getElementById('dz-pip-btn');
  var pipHint = document.getElementById('dz-pip-hint');
  var isServed = location.protocol === 'http:' || location.protocol === 'https:';
  var hasPipSupport = 'documentPictureInPicture' in window;
  var pipWindow = null;
  var lastHtml = '';
  var busy = false;
  var failureCount = 0;
  var reasonHint = '';            // 버튼이 비활성인 영구 사유. 해소되기 전까지 유지된다

  // 허브 모달(iframe) 로 열렸는지 판정(R1). self !== top 은 WindowProxy 신원 비교라 크로스
  // 오리진에서도 예외를 던지지 않는다(top.location 을 읽으면 던진다 — 그건 하지 않는다).
  // 표시(body.dz-embedded)에만 쓰고 폴링·동기화는 분기하지 않는다 — 모달 안 라이브 갱신이
  // 이 판정으로 죽으면 안 된다.
  var isEmbedded = window.self !== window.top;
  if(isEmbedded) document.body.classList.add('dz-embedded');

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
  function syncImplCard(fresh){
    // 이 카드는 .wrap 안이지만 #dz-steps 동기화 대상이 아니다 — 별도 대입이 없으면 영구히 stale 된다.
    var live = wrap.querySelector('#dz-impl-card'), next = fresh.getElementById('dz-impl-card');
    if(live && next) live.outerHTML = next.outerHTML;
  }
  // 압축 뷰는 작업 추적 카드가 빠져 실제 콘텐츠가 훨씬 짧다 — 여는 시점의 크기를
  // measureCompactHeight() 로 미리 맞추므로(아래), 이 함수는 열린 뒤 콘텐츠 높이가
  // 바뀌었을 때(단계 상세 추가 등)의 보정 시도다. pipWindow.resizeTo() 는 Document PiP 창에서
  // 사용자 제스처(transient activation)를 요구한다(Chrome 실측: NotAllowedError). 이 함수는
  // rAF·폴링에서 호출되므로 제스처가 이미 소진된 뒤라 대개 조용히 실패한다 — 브라우저 API
  // 한계이며 무해하게 catch 된다.
  function resizePipToFit(){
    if(!pipWindow) return;
    var h = Math.ceil(wrap.getBoundingClientRect().height) + PIP_CONTENT_PADDING;
    try{ pipWindow.resizeTo(PIP_WIDTH, Math.max(PIP_MIN_HEIGHT, Math.min(PIP_MAX_HEIGHT, h))); }
    catch(e){ /* 리사이즈 불가 환경이어도 폴링·동기화는 계속돼야 한다 */ }
  }
  // .wrap 은 아직 메인 문서(body.dz-pip 아님)에 있다 — 압축 뷰 클래스를 순간적으로 얹어
  // 실제 렌더 높이를 재고 즉시 되돌린다. 읽기와 되돌리기가 같은 동기 구간 안에서 끝나므로
  // 브라우저가 그 사이의 레이아웃을 페인트할 기회가 없어 화면 깜빡임이 없다. PiP 창을 여는
  // 호출은 열린 뒤의 resizeTo() 와 달리 사용자 제스처를 그대로 쓸 수 있으므로, 크기는 여기서
  // "처음부터 맞게" 정한다 — resizePipToFit() 의 사후 보정에 기대지 않는다.
  // 메인 창은 보통 .wrap 의 max-width(860px)만큼 넓어 PIP_WIDTH(420)보다 훨씬 넓게 렌더링된다
  // — 폭을 강제하지 않으면 실제 PiP 창에서 줄바꿈되는 텍스트(제목·단계 상세 등)가 측정
  // 시점엔 한 줄로 남아 높이를 과소평가한다. 그래서 측정 동안만 .wrap 폭도 함께 좁힌다.
  function measureCompactHeight(){
    document.body.classList.add('dz-pip');
    wrap.style.width = PIP_WIDTH + 'px';
    var h = Math.ceil(wrap.getBoundingClientRect().height) + PIP_CONTENT_PADDING + PIP_CHROME_ALLOWANCE;
    wrap.style.width = '';
    document.body.classList.remove('dz-pip');
    return Math.max(PIP_MIN_HEIGHT, Math.min(PIP_MAX_HEIGHT, h));
  }
  function apply(html){
    if(html === lastHtml) return;
    lastHtml = html;
    var fresh = new DOMParser().parseFromString(html, 'text/html');
    // 라디오와 <style> 은 치환 대상이 아니다(사용자가 고른 필터가 날아간다).
    syncText(fresh,'dz-title');
    syncText(fresh,'dz-progress-pct'); syncText(fresh,'dz-updated');
    syncProgressBar(fresh); syncVisualization(fresh); syncImplCard(fresh); syncLog(fresh);
    resizePipToFit();
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
    window.documentPictureInPicture.requestWindow({width:PIP_WIDTH, height:measureCompactHeight()})
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
        // 이동 직후엔 새 문서가 아직 레이아웃을 못 잡았을 수 있어 프레임을 한 번 넘기고 잰다.
        requestAnimationFrame(function(){ requestAnimationFrame(resizePipToFit); });
        pipButton.textContent = '플로팅 닫기';
        reasonHint = '';
        setHint('플로팅 창에서 보는 중입니다. 창을 닫으면 여기로 돌아옵니다.');
        win.addEventListener('pagehide', function(){
          pipWindow = null;
          document.body.insertBefore(wrap, pipButton);
          pipButton.textContent = '플로팅';
          setHint(reasonHint);
          poll();
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
