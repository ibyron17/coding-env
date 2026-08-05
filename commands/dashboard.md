---
description: "세션 진행 상황을 프로젝트 로컬 HTML 대시보드로 기록 — init/step/log + on/off 스위치"
argument-hint: "init \"<제목>\" \"<단계1|단계2|...>\" | step <n> <done|active|wait> | log <impl|pass|fail|commit> \"<요약>\" [...] | on | off"
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
/dashboard step <n> <done|active|wait>
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

`<style>` 블록, `:root` 색 토큰, 카드 골격, 하단 스크립트.

### 동적(치환 대상) — 7 셀렉터

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-subtitle` | 텍스트 | 단계 흐름 요약 · 작업 유형 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` | `class` 속성 + 자식 `.chip` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` |
| `#dz-log` | 자식 `<li>` **prepend** + `data-current-session` 속성 | 로그 항목(최신이 위) / 현재 세션 번호 |
| `#dz-updated` | 텍스트 | 갱신 시각 |

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
3. `#dz-subtitle` 텍스트를 `"<단계1> → <단계2> → ... · <작업 유형>"` 형식으로 치환한다.
   작업 유형(예: "전체 경로")은 호출한 오케스트레이터가 이미 알고 있는 값을 채운다.
4. `<단계1|단계2|...>` 를 `|` 로 분리해 개수 N을 구한다. 템플릿의
   `<ol class="steps" id="dz-steps">...</ol>` 내부를 아래 패턴으로 N개 생성한 `<li>` 로 통째로 치환한다
   (1번은 `active`, 나머지는 `wait`):
   ```html
   <li id="dz-step-{n}" class="{active|wait}"><span class="num">{n}</span>{단계명}<span class="chip">{진행중|대기}</span></li>
   ```
5. `#dz-progress-bar` 의 `style` 을 `width:0%` 로, `#dz-progress-pct` 텍스트를 `0/N · 0%` 로 치환한다.
6. `#dz-updated` 를 현재 시각(예: `2026-08-04 17:02`)으로 치환한다.
7. `#dz-log` 는 템플릿 그대로 빈 목록(`<ul class="log" id="dz-log" data-current-session="1"></ul>`)으로
   둔다 — 아직 로그가 없다.
8. 사용자에게 `file://<현재 작업 디렉토리 절대경로>/.claude/dashboard.html` 을 출력해
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

## `step` — 메인 세션이 수행할 절차 (Edit 2~3회)

1. `#dz-step-{n}` 의 `class` 속성과 자식 `.chip` 텍스트를 새 상태로 치환한다
   (`done`/`완료`, `active`/`진행중`, `wait`/`대기`).
2. 이번 치환으로 `done` 이 된 경우, 완료 단계 수를 세어 `#dz-progress-bar` 의 `style="width:N%"`
   와 `#dz-progress-pct` 텍스트(`M/N · P%`)를 재계산해 치환한다.
3. `#dz-updated` 텍스트를 현재 시각으로 치환한다.

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
  #dz-step-{n}          : 각 단계 li — class(done|active|wait) + .chip 텍스트(완료|진행중|대기)
  #dz-log               : 작업 추적 ul — li data-seq 앵커로 prepend / data-current-session 속성(현재 세션 번호)
  #dz-updated           : 갱신 시각 텍스트
정적(불가침): 골격 · <style> · 제목 · 하단 스크립트
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
  <div class="card">
    <div class="log-title">작업 추적</div>
    <input type="radio" name="dzf" id="dzf-all" class="dzf" checked><label for="dzf-all">전체</label>
    <input type="radio" name="dzf" id="dzf-impl" class="dzf"><label for="dzf-impl">구현</label>
    <input type="radio" name="dzf" id="dzf-review" class="dzf"><label for="dzf-review">검수</label>
    <ul class="log" id="dz-log" data-current-session="1"></ul>
  </div>
  <div class="foot" id="dz-updated">갱신: -</div>
</div>
<script>
  // 탭으로 돌아오거나 창에 포커스가 오면 최신 파일로 자동 새로고침 (새 탭 안 띄움)
  var _dzReloading=false; function _dzReload(){ if(_dzReloading) return; _dzReloading=true; location.reload(); }
  document.addEventListener('visibilitychange', function(){ if(document.visibilityState==='visible') _dzReload(); });
  window.addEventListener('focus', _dzReload);
</script>
</body>
</html>
```
