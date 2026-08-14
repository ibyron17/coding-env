# 세션 진행 상황 대시보드 (PRP)

## 요구사항 요약

개발 세션의 진행 상황을 브라우저에서 한눈에 볼 수 있는 대시보드를 워크플로우 자산으로 편입한다.
사용자가 수작업으로 운영하던 `~/Desktop/dashboard.html` 을 `/dashboard` 커맨드로 정식화하되,
가장 큰 불만이었던 **작업 추적 로그의 가독성**을 접기/배지/필터로 개선한다.

Phase 1(이번 구현 대상)은 단일 HTML 파일 + 포커스 시 자동 새로고침으로 서버 의존성 없이 동작한다.
Phase 2(계획만, 구현 제외)는 플로팅 윈도우(Document Picture-in-Picture)를 얹는다.

### 이번 라운드 추가 요구 — 세션 탭

같은 프로젝트에서 여러 세션이 하나의 대시보드를 이어 쓰면 작업 추적 목록에 여러 세션의
로그가 뒤섞인다. 직전 라운드에서 넣은 `session-head` 구분선은 "경계 표시"까지만 하고
**세션별로 나눠 보는 것**은 못 한다. 이번 라운드는 `모든 세션 / 세션 N / … / 세션 1` 탭으로
전환하며 해당 세션의 로그만 볼 수 있게 한다. 기존 원칙(JS 없이 CSS 로, 래퍼 `div` 금지,
`log` 절차의 고정 비용)을 하나도 깨지 않는 범위에서 구현한다.

---

## 영향 범위

### 신설 파일

- **`commands/dashboard.md`** (약 200~260줄)
  - `/dashboard init` · `/dashboard step` · `/dashboard log` 세 하위 명령의 호출 규약
  - 대시보드 HTML 템플릿 전문
  - 각 하위 명령에 대응하는 **메인 세션의 Edit 절차**(어떤 셀렉터의 무엇을 어떤 값으로 치환하는지)

### 수정 파일

- **`CLAUDE.md`** — 「개발 워크플로우 → 공통 규칙」에 트리거 4줄 추가
  (전체 경로 착수 시 생성 / 단계 전환마다 갱신 / **메인 세션만 갱신, 서브에이전트는 접근 금지**)
- **`README.md`** ([README.md:72](../../README.md) 부근) — 커맨드 표에 1행 추가,
  "7종이 닫힌 의존 사슬" 문구를 "**의존 사슬 7종 + 독립 커맨드 1종**"으로 조정
- **`install.sh`** ([install.sh:14](../../install.sh)) — `COMMANDS_FILE_COUNT=7` → `8`
- **`tests/run.sh`** — 커맨드 개수 기대값 7 → 8(2곳), `test_commands_installed` 목록에 `dashboard` 추가,
  신규 T22(템플릿 무결성 검증) 추가
- **`.gitignore`** — `.claude/dashboard.html` 1줄 추가
  (레포에 `.claude/settings.local.json` 만 무시 중이고 `.claude/` 하위 추적 파일이 없음을 확인함.
  `.claude/` 전체를 무시하면 안 된다 — 향후 추적 대상이 생길 수 있다)

### 이번 라운드(세션 탭)의 영향 범위

- **`commands/dashboard.md`** — 아래 5곳만 수정한다
  1. 데이터 모델 표의 `#dz-log` 행 (`data-current-session` 을 하위 개념으로 추가)
  2. 로그 항목 스키마 (`data-session` 속성 추가)
  3. `init` 절차 — "이미 존재하면" 분기에 세션 번호 계산·탭 갱신 추가, 7번 항목의 빈 `#dz-log` 표기 갱신
  4. `log` 절차 — 0단계 grep 패턴 교체(**필수, 아래 리스크 6 참조**), 2단계에 `data-session` 부여
  5. 템플릿 전문 — `<style>` 에 `.dzs` 3줄 + `DZ:SESSION-RULES` 마커, `#dz-log` 여는 태그에
     `data-current-session="1"`, 헤더 주석 맵 1줄
  6. (세션 탭과 무관, 같은 사용자 요청 턴에 함께 처리) 작업 추적 타이틀을 인라인 `<b>` 에서
     block `<div class="log-title">` 로 분리 — 필터 라디오와 같은 줄에 붙어 보이던 레이아웃
     버그 수정. `tests/run.sh` T22-10 대응.
- **`tests/run.sh`** — T22-10(위 6번 대응) ~ T22-15 추가 (아래 테스트 계획)
- **`docs/prps/session-dashboard.md`** — 이 문서

### 미영향

- `agents/` — 서브에이전트는 대시보드에 접근하지 않으므로 수정 없음
- `rules/` — 코드 품질 기준 계층이며 워크플로우 산출물과 무관
- `install.sh` / `README.md` / `CLAUDE.md` — 이번 라운드는 파일 수·커맨드 목록·트리거가 불변

---

## 파일 구조와 모듈 경계

이 기능에는 실행 코드가 없다. **커맨드 문서(지시문) → 메인 세션의 Edit → HTML 파일** 세 층이며,
층 사이의 계약은 아래 셀렉터 규약이다.

| 층 | 실체 | 책임 |
|----|------|------|
| 지시문 | `commands/dashboard.md` | 템플릿 원본과 치환 규약을 소유. 호출 시에만 컨텍스트에 로드 |
| 실행 | 메인 세션(오케스트레이터) | 규약대로 Edit 도구로 HTML 부분 치환 |
| 표현 | `.claude/dashboard.html` | **상태를 스스로 보유**한다(별도 상태 파일 없음) |

**별도 상태 파일(JSON)을 두지 않는다.** DOM 자체가 상태다.
Phase 2 의 폴링도 HTML 을 통째로 받아 DOM 을 치환하면 성립하므로 JSON 은 지금 필요 없다(YAGNI).
`jq` 등 신규 의존성도 도입하지 않는다.

---

## 데이터 모델 — DOM 상 표현 규격

상태는 다음 셀렉터와 속성으로만 표현한다. 이 표가 지시문과 HTML 사이의 계약이다.

### 정적(불가침)

`<style>` 블록, `:root` 색 토큰, 카드 골격, 하단 스크립트.

### 동적(치환 대상) — 7 셀렉터 (변동 없음)

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-subtitle` | 텍스트 | 단계 흐름 요약 · 작업 유형 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` | `class` 속성 + 자식 `.chip` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` |
| `#dz-log` | 자식 `<li>` **prepend** + `data-current-session` 속성 | 로그 항목(최신이 위) / 현재 세션 번호 |
| `#dz-updated` | 텍스트 | 갱신 시각 |

**셀렉터 개수는 7 로 유지한다.** `data-current-session` 은 새 행이 아니라 `#dz-log` 행의
하위 개념으로 문서화한다 — 이 표의 "7" 은 *절차가 따로 찾아가야 하는 지점의 수*를 뜻하는데,
`data-current-session` 은 `log` 절차가 어차피 매번 grep 하는 `#dz-log` 여는 태그에 얹혀 있어
탐색 단계를 하나도 늘리지 않기 때문이다. (`tests/run.sh` T22-2 의 셀렉터 목록도 그대로 둔다.)

### 세션 번호의 보관 위치 — `#dz-log[data-current-session]`

```html
<ul class="log" id="dz-log" data-current-session="2"> … </ul>
```

- **의미**: 지금 진행 중인 세션의 번호. `init` 이 세션 시작 때 +1 하고, `log` 는 읽기만 한다.
- **왜 여기인가**: `log` 절차는 이미 `#dz-log` 여는 태그를 grep 으로 찾는다(windowed read 최적화).
  세션 번호를 이 태그의 속성으로 두면 **추가 I/O 0회**로 매 `log` 호출이 자기 세션 번호를 안다.
- **기각한 대안**: `.session-head` 마커를 거슬러 올라가 최댓값을 찾는 방식. 세션이 길어지면
  가장 최근 마커가 60~120줄 창(window) 밖으로 밀려나 못 찾는다 — 로그 길이에 따라 실패하는,
  즉 "가변 비용" 문제를 다시 불러들이는 설계다.
- **속성이 없는 파일**(이 라운드 이전에 만들어진 대시보드)은 `1` 로 간주한다.

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

- `data-seq` — 1부터 증가하는 정수. **펼침 제어의 유일 키**이자 Edit 문자열 매칭의 앵커
- `data-kind` — `impl` \| `review` \| `commit` \| `note` (유형 필터 대상)
- `data-session` — 이 항목이 속한 세션 번호 (**세션 탭 필터 대상**).
  `log` 절차가 `#dz-log` 의 `data-current-session` 값을 **그대로 복사**해 넣는다.
  세거나 추론하는 판단이 개입하지 않는다.
- `.badge.round` — 회차(`R1`, `R2`…). 회차 개념이 없는 항목은 생략
- 결과 배지 4종:

| class | 라벨 | 색(토큰) |
|-------|------|---------|
| `.badge.impl` | 구현 | `--blue` |
| `.badge.pass` | 검수 PASS | `--green` |
| `.badge.fail` | 검수 FAIL | `--red`(신규 토큰 `#C2410C`) |
| `.badge.commit` | 커밋 | `--navy` |

### 세션 구분 항목

두 번째 이후 세션이 기존 대시보드를 이어서 쓸 때, `init` 절차가 `#dz-log` 맨
위에 `<li class="session-head" data-session="N">세션 N 시작 · HH:MM</li>` 를
prepend해 세션 경계를 표시한다.

- `.entry` 가 아니므로 **유형 필터**(`.entry:not([data-kind=...])`)의 영향을 받지 않는다 —
  `모든 세션` 탭 안에서는 어떤 유형 필터 상태에서도 항상 보인다.
- **세션 탭 필터**(`input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`)의
  영향은 받는다. `dzs-all` 이 아닌 특정 세션 탭이 선택되면 소속 세션과 무관하게 전부 숨는다
  — 사용자 피드백 반영(2026-08-05): 하나의 세션만 보는 화면에서 "경계"는 무의미하다고
  판단해, 애초 설계였던 "선택한 세션의 구분선만 시작 시각 캡션으로 남기는" 방식을 폐기했다.

---

## 인터페이스

### 호출 규약 (변동 없음)

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard step <n> <done|active|wait>
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
```

세션 탭은 새 하위 명령을 만들지 않는다. 세션 전환의 유일한 트리거는 `init` 이다.

### `init` — 메인 세션이 수행할 절차

1. `.claude/dashboard.html` 존재 여부 확인
   - **이미 존재하면**: 제목·단계 목록 등은 덮어쓰지 않는다. 아래 a~d 를 수행해 세션 경계와
     세션 탭만 갱신하고, "기존 대시보드를 이어서 사용합니다" 안내 + `file://` 경로 출력 후
     절차를 종료한다(2번 이하 미실행).
     **한계**: "새 작업"과 "기존 작업 재개"를 구분하지 못한다 — 새 작업 시작 시 기존 파일을
     지우거나 다시 만들지 사용자에게 확인하도록 안내 문구에 명시한다.
   - **존재하지 않으면**: `commands/dashboard.md` 의 템플릿을 `.claude/dashboard.html`
     로 Write 하고 계속 진행 (템플릿은 `data-current-session="1"`, 탭 바 없음)
2. `#dz-title`·`#dz-subtitle` 치환, 단계 개수만큼 `#dz-step-{n}` li 생성(1번은 `active`, 나머지 `wait`)
3. `#dz-progress-bar`·`#dz-progress-pct` 를 `0/N · 0%` 로 설정
4. 사용자에게 `file://` 절대 경로를 출력해 브라우저로 열도록 안내

#### 1번 "이미 존재하면" 분기 — `commands/dashboard.md` 에 옮겨적을 문구

> a. **세션 번호 확정**: Bash 로 `grep -n 'id="dz-log"' .claude/dashboard.html` 을 실행해
>    `#dz-log` 여는 태그의 줄 번호와 전문을 얻는다. 그 태그의 `data-current-session="{P}"` 값이
>    직전 세션 번호다. 이번 세션 번호는 `N = P + 1`.
>    속성이 아예 없으면 세션 탭 도입 이전에 만들어진 파일이므로, 그 줄부터 `limit=60` 으로
>    Read 해 보이는 `.session-head` 의 `data-session` 최댓값을 `P` 로 삼는다(하나도 없으면 `P=1`).
>
> b. **현재 세션 번호 갱신**: `#dz-log` 여는 태그를 `data-current-session="{N}"` 으로 치환한다.
>    속성이 없었다면 `id="dz-log"` 바로 뒤에 새로 넣는다. Edit 의 `old_string` 은 a 에서 읽은
>    태그 전문을 그대로 쓴다(태그 내용이 세션마다 달라지므로 고정 문자열로 매칭하지 않는다).
>
> c. **세션 구분 항목 prepend**: 그 태그 바로 뒤에 아래를 삽입한다. `{HH:MM}` 은 현재 시각.
>    ```html
>    <li class="session-head" data-session="{N}">세션 {N} 시작 · {HH:MM}</li>
>    ```
>
> d. **세션 탭 갱신**: 아래 「세션 탭 갱신」 절차를 수행한다.

#### 세션 탭 갱신 — `init` 1-d 의 하위 절차

> `grep -c 'dzs-all' .claude/dashboard.html` 로 탭 바 존재 여부를 판정한다.
>
> **결과가 0 (탭 바 없음 — 이 대시보드에 세션이 둘이 된 첫 순간)**
>
> 1. `<input type="radio" name="dzf" id="dzf-all" class="dzf" checked>` 줄 **앞**에
>    아래를 삽입한다. `모든 세션` 이 기본 선택이고, 세션 탭은 **큰 번호가 왼쪽**이다
>    (`{N}`, `{N-1}`, …, `1` 순으로 나열. 보통 `N=2` 이므로 탭 3개).
>    ```html
>    <input type="radio" name="dzs" id="dzs-all" class="dzs" checked><label for="dzs-all">모든 세션</label>
>    <input type="radio" name="dzs" id="dzs-{N}" class="dzs"><label for="dzs-{N}">세션 {N}</label>
>    <input type="radio" name="dzs" id="dzs-1" class="dzs"><label for="dzs-1">세션 1</label>
>    <br>
>    ```
>    `<br>` 은 세션 탭 줄과 유형 필터 줄을 물리적으로 분리한다(사용자 피드백 반영 —
>    카드 폭에 따른 자연 줄바꿈에 기대지 않는다). wrapper `div` 와 달리 빈 요소라
>    `~` 형제 결합자를 끊지 않는다.
> 2. `<style>` 안의 `/* DZ:SESSION-RULES */` 마커 줄 **바로 뒤**에 세션 `1`~`{N}` 각각에 대해
>    아래 규칙을 한 줄씩 추가한다. 대상은 `.entry` 다 — 구분선(`.session-head`) 숨김은
>    별도의 고정 규칙(`input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`)이
>    전담하므로 이 규칙에서는 신경 쓰지 않는다.
>    ```css
>    #dzs-{n}:checked ~ #dz-log .entry:not([data-session="{n}"]){display:none}
>    ```
>
> **결과가 1 이상 (탭 바 있음)**
>
> 1. `<label for="dzs-all">모든 세션</label>` **바로 뒤**에 이번 세션 탭 1개를 삽입한다.
>    ```html
>    <input type="radio" name="dzs" id="dzs-{N}" class="dzs"><label for="dzs-{N}">세션 {N}</label>
>    ```
> 2. `/* DZ:SESSION-RULES */` 마커 바로 뒤에 이번 세션 규칙 1줄을 추가한다.
>
> **새 탭 라디오에 `checked` 를 넣지 않는다.** 기본 선택은 언제나 `#dzs-all` 이다. 새 탭에도
> `checked` 를 달면 같은 그룹에 `checked` 가 둘이 되어 문서 순서상 뒤엣것이 이기고, 페이지가
> 새로고침될 때마다 사용자가 고른 탭이 무시된다.

`init` 7번 항목(빈 로그 표기)도 `<ul class="log" id="dz-log" data-current-session="1"></ul>` 로 갱신한다.

### `step` — 절차 (Edit 2~3회, 변동 없음)

1. `#dz-step-{n}` 의 `class` 와 `.chip` 텍스트를 새 상태로 치환
2. `done` 으로 바뀐 경우 진행률 재계산 → `#dz-progress-bar` width 와 `#dz-progress-pct` 치환
3. `#dz-updated` 치환

### `log` — 절차 (Bash grep 1회 + Read 1~2회 + Edit 2회, 결정적)

0. **최신 항목만 확인**: 로그는 항상 맨 앞에 prepend되므로 최댓값 `S` 와 `S-2` 항목은
   항상 로그 앞부분에 있다. 따라서 파일 전체를 Read하지 않고 `grep`으로 `#dz-log` 시작 줄을
   찾은 뒤 그 지점부터 제한된 줄만 Read해 확인한다(로그가 길어져도 이 단계의 비용이 늘지 않는다).
   같은 grep 결과 줄에서 **현재 세션 번호 `C`(`data-current-session` 값)** 도 함께 읽어 둔다.
1. **직전 펼침 회수**: 위에서 확인한 최대 `data-seq` 를 `S` 라 할 때, `data-seq="S-2"` 항목의
   `<details open>` 를 `<details>` 로 치환한다. 해당 seq 가 없으면 생략한다.
   → 결과적으로 **항상 최신 3건만 펼쳐진다.** (세션과 무관한 전역 정책이다)
2. **prepend**: `#dz-log` 여는 태그 바로 뒤에 `data-seq="S+1"`, `data-session="C"` 인 새 `<li>` 를
   삽입한다. 삽입 전 요약·상세 텍스트는 `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` 순서로 이스케이프한다
   (코드 조각이 그대로 들어가면 태그가 깨진다 — 검수 지적 반영).

`data-seq` 가 문서 내 유일 문자열이므로 두 치환 모두 앵커가 명확하고, 순번을 세는 판단이 개입하지 않는다.

#### 0단계·2단계의 grep/앵커 변경 — `commands/dashboard.md` 에 옮겨적을 문구

`#dz-log` 여는 태그가 `data-current-session` 을 갖게 되면서 **태그 전문이 세션마다 달라진다.**
기존의 완전 일치 grep(`'<ul class="log" id="dz-log">'`)은 더 이상 매칭되지 않으므로 반드시 바꾼다.

> 0-a. Bash 로 `grep -n 'id="dz-log"' .claude/dashboard.html` 를 실행해 로그 시작 줄 번호 `L` 과
>      그 줄의 내용을 얻는다. `id="dz-log"` 는 문서 내 유일 문자열이다(`<style>` 과 헤더 주석의
>      `#dz-log` 는 `id=` 형태가 아니라 매칭되지 않는다). 이 줄에 있는
>      `data-current-session="{C}"` 값이 **이번 항목이 속할 세션 번호**다(속성이 없으면 `C=1`).
>
> 2. **prepend**: 0-a 에서 읽은 `#dz-log` 여는 태그 **전문**을 `old_string` 앵커로 삼아 그 뒤에
>    새 `<li>` 를 삽입한다(태그 텍스트가 세션마다 다르므로 고정 문자열을 쓰지 않는다).
>    새 `<li>` 에는 `data-session="{C}"` 를 포함한다.

### CLAUDE.md 트리거 (메인 세션 전용, 변동 없음)

| 시점 | 호출 |
|------|------|
| 전체 경로 착수 보고 시 | `init` |
| PRP 작성 완료 | `step 1 done` + `log impl` |
| 사용자 승인 수령 | `step 2 done` + `step 3 active` |
| 구현 완료 | `step 3 done` + `log impl` |
| 검수 PASS / FAIL | `step 4 done|wait` + `log pass|fail` |
| 커밋·푸시 | `log commit` |

**축약 경로에는 적용하지 않는다** — 단계가 둘뿐이라 대시보드가 과하다.

---

## 로그 UI 규격

사용자의 핵심 요구다. 원본은 한 항목이 300~700자인 문단 33개라 스캔이 불가능했다.

### 접기

`<details>` / `<summary>` 로 요약 한 줄과 상세를 분리한다. 요약 줄만으로 흐름을 읽을 수 있어야 하므로
`.lead` 는 **1줄로 자른다**(`overflow:hidden; text-overflow:ellipsis; white-space:nowrap`).
상세 전문은 펼쳤을 때 `.detail` 에서 줄바꿈 허용.

### 펼침 정책

최신 3건만 `open`. 제어는 위 `log` 절차 1~2단계로 이뤄지며, CSS 로는 `details` 의 열림을 바꿀 수 없으므로
속성 치환으로만 처리한다.

### 필터 — JS 없이 CSS 로

라디오를 `#dz-log` 의 **앞 형제**로 두고 `~` 결합자로 제어한다. 두 개의 독립된 라디오 그룹이 있다:

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
`<br>` 로 두 그룹을 물리적으로 다른 줄에 고정한다.

원본의 골격·`:root` 색 토큰·단계 리스트는 그대로 유지한다.

#### 이 구조가 성립하는 이유 (검증 결과, 2026-08-05 사용자 피드백으로 일부 수정)

- **구분선은 특정 세션 탭에서 아예 숨긴다.** `input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`
  는 세션 개수와 무관한 고정 규칙 1개다. 애초 설계는 `#dz-log > li` 로 항목과 구분선을 한
  규칙으로 처리해 "선택한 세션의 구분선만 시작 시각 캡션으로 남기는" 효과를 노렸으나,
  사용자가 "하나의 세션만 보는 화면에서 구분선 자체가 불필요하다"고 판단해 폐기했다.
  대신 항목 필터(`.entry` 대상)와 구분선 숨김(`.session-head` 대상)을 규칙 단위로 분리했다.
- **모든 규칙은 `display:none` 만 지정한다.** 되돌리는 규칙(`display:block` 등)을 쓰지 않으므로
  두 그룹의 규칙이 서로의 특이도(specificity)를 다투지 않고, "둘 다 통과해야 보인다"는
  **AND 결합이 저절로 성립**한다. 이 불변식을 깨는 규칙을 추가하지 않는다.
- **래퍼 `div` 금지 제약은 세션 탭에도 그대로 적용된다.** 라디오·라벨·`#dz-log` 는 모두
  `.card` 의 직계 형제여야 한다. `display:contents` 로도 우회할 수 없다 — 형제 결합자는
  박스 트리가 아니라 DOM 트리로 판정하기 때문이다.
- 규칙 증가량은 세션당 정확히 1줄이다(`#dz-step-{n}` 처럼 "개수만큼 생성" 하는 기존 패턴과 동일).

#### 탭이 많아지면

`label[for^="dzs-"]` 은 `inline-block` 이라 카드 폭을 넘으면 **자연히 줄바꿈**된다. 이대로 둔다.

- 가로 스크롤 컨테이너는 래퍼 `div` 가 필요한데 그러면 `~` 결합자가 끊겨 필터 전체가 깨진다.
  즉 **줄바꿈 외의 선택지가 애초에 없다.**
- 현실적 상한도 낮다. 대시보드는 기능 단위로 만들고 끝나면 지우는 파일이라 세션 수가 두 자리로
  가는 경우가 드물고, 그 지경이면 대시보드를 새로 만드는 편이 맞다.
- 그러므로 접기·"더 보기"·상한 같은 장치는 만들지 않는다(YAGNI).

### 세션 구분

`init` 이 삽입하는 `<li class="session-head" data-session="N">` 로 세션 경계를 표시한다.
`모든 세션` 탭에서만 경계선으로 보이고, 특정 세션 탭에서는 구분선 자체가 사라진다.

---

## 설계 결정과 근거

### 1. 실행 주체는 LLM(메인 세션), 셸 스크립트를 만들지 않는다

마크다운 슬래시 커맨드는 지시문이지 실행 파일이 아니다. 셸 자산을 만들면 `install.sh` 의
배포 카운트(`COMMANDS_FILE_COUNT`)와 소유권 로직을 확장해야 하고 `jq` 의존성이 따라온다.
사용자의 기존 `Desktop/dashboard.html` 이 이미 LLM Edit 방식으로 운영돼 실증된 방식이다.

**대가**: 갱신이 비결정적일 수 있다. 그래서 `data-seq` 앵커와 셀렉터 표로 판단 여지를 없앴다.

### 2. 상태 파일을 두지 않는다

DOM 이 곧 상태다. JSON 을 따로 두면 HTML 과 이중 관리가 되고, 두 파일이 어긋날 때
어느 쪽이 진실인지 정하는 규칙이 또 필요해진다. Phase 2 의 폴링도 HTML 폴링으로 성립한다.

### 3. 산출물은 프로젝트 로컬 `.claude/dashboard.html`

프로젝트별로 분리돼 세션 간 덮어쓰기가 사라지고, `.gitignore` 한 줄이 실제로 의미를 갖는다.
홈 디렉토리 캐시 경로는 사용자가 매번 손으로 열어야 하는 파일로서 접근성이 나쁘다.

### 4. 메인 세션만 갱신한다

서브에이전트는 별도 컨텍스트라 전체 단계를 모르고, 병렬 실행 시 같은 파일에 경합이 생긴다.
전체 진행 상태를 아는 주체는 오케스트레이터뿐이다.

**기각한 대안**: `agents/dashboard-updater.md` 신설(맥락 부재로 판단 불가),
`settings.json` hooks(install.sh 가 settings.json 소유권을 갖지 않으며, 셸 훅은 "지금 어느 단계인지"를 판단할 수 없다),
`rules/common/` 배치(코드 품질 기준 계층이고 템플릿을 상시 로드하는 비용이 크다).

### 5. 필터를 CSS 로 구현한다

JS 로 하면 이벤트 바인딩과 상태 관리가 붙는다. 라디오 + 형제 결합자면 코드 3줄로 끝난다.
경과 시간만은 CSS 로 불가능해 스크립트를 쓴다. 세션 탭도 같은 패턴을 재사용한다 —
새 메커니즘을 들이지 않는 것이 이번 라운드에서 가장 중요한 제약이었다.

### 6. 세션 번호를 `#dz-log` 여는 태그에 박는다

`log` 는 세션당 수십 번 호출되는 가장 잦은 경로다. 여기서 세션 번호를 알아내는 비용이
로그 길이에 비례하면 직전 라운드에 해결한 가변 비용 문제가 되살아난다.
`#dz-log` 여는 태그는 `log` 가 어차피 매번 grep 하는 줄이므로, 여기에 얹으면 **추가 I/O 0회**다.

**대가**: 여는 태그의 텍스트가 더 이상 고정 문자열이 아니다. 그래서 grep 패턴을
부분 일치(`id="dz-log"`)로 바꾸고, Edit 앵커는 "0단계에서 읽은 태그 전문"으로 규정했다.
이 변경을 빠뜨리면 `log` 가 통째로 실패하므로 T22-12 로 회귀를 막는다.

### 7. 탭 바는 두 번째 세션부터 만든다

세션이 하나뿐인 대시보드(대다수)에 `모든 세션 | 세션 1` 두 탭을 띄우는 것은 의미 없는 UI 소음이다.
템플릿에는 탭 바를 넣지 않고, 세션이 둘이 되는 순간 `init` 이 만든다.

**대가**: `init` 에 분기가 하나 는다("탭 바가 있는가"). 판정은 `grep -c 'dzs-all'` 한 번이고
두 분기 모두 고정 앵커에 대한 기계적 문자열 삽입이라, 판단 여지를 늘리지 않는다는
이 문서의 원칙을 깨지 않는다.

**기각한 대안**: 템플릿에 `모든 세션`·`세션 1` 탭을 처음부터 넣어 분기를 없애는 안.
분기는 사라지지만 단일 세션 대시보드 전부에 무의미한 탭 바가 남는다. CSS 로는 항목 수를
셀 수 없어(`:has()` 없이는) 조건부로 숨길 방법도 없다.

### 8. 최신 세션이 왼쪽(`모든 세션` 바로 다음)

대시보드 전체가 "최신이 앞" 규칙으로 일관돼 있고(로그 prepend, 구분선 prepend),
탭 삽입 앵커도 `<label for="dzs-all">모든 세션</label>` 하나로 고정돼 절차가 단순해진다.
오름차순이면 목록 끝을 찾아야 하는데, 끝의 위치는 세션마다 달라진다.

**대가**: 세션이 늘면 각 탭의 가로 위치가 밀린다. 대신 가장 자주 쓰는 "현재 세션" 탭은
항상 `모든 세션` 바로 옆 고정 위치에 있다.

---

## 테스트 계획

LLM 지시문 방식이므로 자동 검증 가능한 것은 **설치·문서 정합성과 템플릿 무결성**이다.
런타임 동작(실제 Edit 결과)은 자동화 대상이 아니다 — 억지 테스트를 만들지 않는다.

### tests/run.sh 수정

- 기존 커맨드 개수 기대값 `7` → `8` (2곳)
- `test_commands_installed` 의 커맨드 이름 목록에 `dashboard` 추가

### tests/run.sh T22 — 템플릿 무결성

| TC | 검증 | 방법 |
|----|------|------|
| T22-1 | `commands/dashboard.md` 설치됨 | `[[ -f ./.claude/commands/dashboard.md ]]` |
| T22-2 | 필수 셀렉터 7종이 템플릿에 모두 존재 | `dz-title` 등 id 목록을 순회하며 `grep -q` |
| T22-3 | 결과 배지 4종 CSS class 정의 존재 | `grep -q '\.badge\.\(impl\|pass\|fail\|commit\)'` |
| T22-4 | 필터 라디오 3종과 CSS 규칙 존재 | `grep -q 'dzf-review:checked'` |
| T22-5 | `install.sh` 의 `COMMANDS_FILE_COUNT` 가 실제 파일 수와 일치 | 상수 파싱 후 `ls commands/*.md \| wc -l` 과 비교 |
| T22-6 | `init` 절차에 기존 파일 덮어쓰기 가드 문구 존재 | `grep -q "덮어쓰지 않는다"` |
| T22-7 | `div.legend` 컴포넌트가 템플릿에서 제거됨 | `! grep -q 'class="legend"'` |
| T22-8 | 세션 구분 마커(`session-head`) CSS 정의 존재 | `grep -q "session-head"` |
| T22-9 | `log` 절차의 windowed-read 최적화 문구 존재 | `grep -q "파일 전체를 Read하지 않는다"` |
| T22-10 | 작업 추적 타이틀이 block 요소로 분리됨 | `grep -q 'class="log-title"'` |

T22-5 는 커맨드를 추가하고 상수를 안 고치는 실수를 잡는다.
T22-6 은 두 번째 세션이 미완료 작업을 재개할 때 `init` 재호출로 기존 진행 상황이 날아가는 것을 막는다.
T22-7 은 범례 div 제거가 되돌려지지 않았는지 확인한다.
T22-8 은 세션 구분 마커가 구현 과정에서 누락되지 않았는지 확인한다.
T22-9 는 `log` 절차가 파일 전체 Read 방식으로 퇴행하지 않았는지 확인한다.
T22-10 은 필터 라디오와 제목이 한 줄에 붙던 레이아웃 버그의 회귀를 막는다.

### 신규 — 세션 탭 (T22-11 ~ T22-15)

| TC | 검증 | 방법 |
|----|------|------|
| T22-11 | 템플릿의 `#dz-log` 여는 태그에 현재 세션 번호가 박혀 있음 | `grep -q 'id="dz-log" data-current-session="1"'` |
| T22-12 | **`log` 절차가 깨진 완전일치 grep 으로 퇴행하지 않음** | `! grep -q "grep -n '<ul class=\"log\" id=\"dz-log\">'"` **그리고** `grep -q "grep -n 'id=\"dz-log\"'"` |
| T22-13 | 로그 항목 스키마에 `data-session` 이 포함됨 | `grep -q 'data-seq="12" data-session="2"'` |
| T22-14 | 세션 탭 CSS 골격과 삽입 마커가 템플릿에 존재 | `grep -q 'label\[for\^="dzs-"\]'` **그리고** `grep -q 'DZ:SESSION-RULES'` |
| T22-15 | 새 탭에 `checked` 를 넣지 말라는 문구가 절차에 존재 | `grep -q '새 탭 라디오에 `checked` 를 넣지 않는다'` |

- **T22-12 가 이번 라운드에서 가장 중요한 테스트다.** 여는 태그에 속성이 붙는 순간 기존
  완전일치 grep 은 영원히 0건을 반환하고, 그러면 `log` 가 매번 실패한다. 이 한 줄을 고치지
  않은 채 나머지만 구현되는 것이 가장 그럴듯한 실패 모드라 양방향(옛 패턴 부재 + 새 패턴 존재)으로 막는다.
- **T22-15** 는 `checked` 중복으로 사용자의 탭 선택이 매 새로고침마다 리셋되는 버그를 막는다.
- 세션마다 동적으로 늘어나는 것(탭 `<input>`, CSS 규칙)은 **템플릿에 없는 것이 정상**이므로
  존재 여부를 테스트하지 않는다. 검증 대상은 "골격과 앵커가 있는가"까지다.

### 수동 확인 항목 (테스트 스위트 밖)

- `/dashboard init` 후 브라우저에서 열어 레이아웃 확인
- 로그 5건 추가 후 최신 3건만 펼쳐지는지
- 유형 필터 라디오 3종 동작
- **두 번째 `init` 후 탭 바가 나타나고, 세션 탭 전환 시 해당 세션 항목만 보이는지**
- **세션 탭 + 유형 필터를 동시에 걸었을 때 교집합(AND)으로 걸러지는지**
- **세션 탭 선택 시 다른 세션의 구분선이 사라지고 자기 구분선만 남는지**
- 탭 포커스 복귀 시 자동 새로고침

---

## 리스크와 대안

### 1. 같은 프로젝트에서 세션 2개를 동시에 돌리면 서로 덮어쓴다

프로젝트 로컬 경로 채택으로 프로젝트 간 충돌은 사라졌지만 동일 프로젝트 병행은 남는다.
**YAGNI 로 미지원**한다. 필요해지면 파일명에 세션 식별자를 붙이는 것으로 확장 가능하다.

> **[부분 개정 — `dashboard-ownership-guard.md`]** 동시 병행은 여전히 **미지원**이지만,
> 조용한 덮어쓰기는 아니다. `init` 이 소유 토큰을 각인하고(R1), 최근 갱신된 남의 대시보드는
> 확인을 받으며(R2), `step`·`log`·`impl` 은 토큰이 다르면 **수정 없이 중단한다**(R3).
> "파일명에 세션 식별자를 붙이는" 확장(안 1)은 그 문서의 R4 절에 보류 근거와 재방문 트리거가
> 기록돼 있다.

### 2. Edit 기반 갱신의 비결정성

LLM 이 셀렉터를 잘못 찾으면 대시보드가 깨진다. `data-seq` 앵커와 셀렉터 표로 완화했고,
최악의 경우 `/dashboard init` 로 재생성하면 복구된다(진행 로그는 소실).

### 3. Phase 2 의 `file://` fetch 차단

`file://` 에서는 `fetch` 가 차단되므로 부분 DOM 치환용 폴링이 불가능하다.
Phase 2 는 로컬 정적 서버를 전제로 한다. Phase 1 에는 영향 없다(`location.reload()` 는 fetch 불필요).

### 4. Document PiP 자동 전환의 기술적 미확정

Phase 2 의 핵심 요구인 "자동 플로팅 전환"이 성립하는지 미검증이다. 아래 실측 스파이크로 먼저 판정한다.

### 5. `log` 절차의 Read 비용이 로그 길이에 비례해 늘어난다

최댓값·`S-2` 탐색을 파일 전체가 아니라 `#dz-log` 시작 지점부터 제한된 줄 수만 Read하는
방식으로 완화했다(로그는 항상 최신순으로 prepend되므로 탐색 대상이 항상 맨 앞에 있다).
극단적으로 상세 텍스트가 길어 창을 벗어나는 경우에만 `limit` 을 늘려 재시도한다.

### 6. `#dz-log` 여는 태그가 가변 문자열이 된다 (이번 라운드 신규)

`data-current-session` 도입으로 `<ul class="log" id="dz-log">` 완전일치 매칭이 전부 깨진다.
영향 지점은 `commands/dashboard.md` 안의 4곳(`init` 1번·7번, `log` 0-a·2번)이며,
**하나라도 놓치면 `log` 가 매번 실패한다.** 대응:

- grep 은 부분 일치(`id="dz-log"`)로 바꾼다. `id="dz-log"` 는 문서 내 유일하다
  (`<style>`·헤더 주석의 `#dz-log` 는 `id=` 형태가 아니라 매칭되지 않음을 확인함).
- Edit 앵커는 "0단계에서 읽은 태그 전문"으로 규정해 고정 문자열 의존을 없앤다.
- T22-12 로 옛 패턴의 부활과 새 패턴의 누락을 양방향으로 막는다.

**기각한 대안**: 세션 번호를 별도의 숨은 요소(`<span id="dz-session" data-n="2">`)에 두어
`#dz-log` 태그를 건드리지 않는 안. 여는 태그는 안 깨지지만 `log` 가 매번 grep 을 한 번 더
해야 한다(가장 잦은 경로의 고정 비용 +1). 셀렉터 표의 행도 8개로 늘어난다.

### 7. 세션 탭 도입 이전에 만들어진 대시보드 (하위 호환)

기존 파일에는 `data-current-session` 도 `.entry[data-session]` 도 없다. 동작은 이렇게 갈린다:

- `init` 은 `.session-head` 최댓값으로 `P` 를 복구하므로 **세션 번호는 이어진다.**
- 그러나 **속성이 없는 옛 항목들은 어느 세션 탭에서도 보이지 않는다**(`모든 세션` 탭에서만 보인다).
  세션 탭 필터가 `li:not([data-session="N"])` 이라 속성 없는 항목은 모든 N 에 대해 숨겨지기 때문이다.
- 이 정도 열화는 수용한다. `.claude/dashboard.html` 은 `.gitignore` 대상의 임시 산출물이고,
  거슬리면 파일을 지우고 `/dashboard init` 을 다시 부르면 된다.

**기각한 대안**: 세션 1 규칙만 `li[data-session]:not([data-session="1"])` 로 비대칭 처리해
속성 없는 옛 항목을 세션 1 탭에 포함시키는 안. 옛 파일 하나 때문에 "세션마다 같은 규칙 1줄"
이라는 균일성이 깨지고, 균일성이야말로 LLM 이 규칙을 틀리지 않게 하는 장치다.

### 8. 새로고침 시 탭·필터 선택이 초기화될 수 있다

대시보드는 포커스가 돌아올 때마다 `location.reload()` 한다. 라디오 상태는 문서 상태이므로
브라우저의 폼 상태 복원이 동작하면 유지되고, 동작하지 않으면 `모든 세션` / `전체` 로 돌아간다.
**보장되지 않는다.** 유형 필터도 원래 같은 성질이었고 기본 화면이 가장 유용한 화면이라
치명적이지 않다고 판단해 그대로 둔다.

**기각한 대안**: `:target` + URL 해시로 상태를 URL 에 남기는 안. 해시는 새로고침에도 살아남지만
**한 문서에 활성 target 이 하나뿐**이라 세션 탭과 유형 필터를 동시에 걸 수 없다 —
지금 공짜로 얻고 있는 AND 결합을 잃는다. JS 로 상태를 저장하는 안은 "JS 없이" 원칙에 어긋난다.

---

## 워크플로우 경로 판정 (이번 라운드)

**전체 경로(설계 → 구현 → 검수) 대상이 맞다.** 근거:

- **데이터 모델 변경**: DOM 계약에 `data-session`·`data-current-session` 두 속성이 추가된다.
- **공개 인터페이스 변경**: `init` 의 세션 분기와 `log` 의 0·2단계 절차 서술이 바뀐다.
  특히 `log` 의 grep 패턴 변경은 **하위 호환을 깨는 변경**이라 놓치면 기능 전체가 죽는다(리스크 6).
- 파일 수는 2개(`commands/dashboard.md`, `tests/run.sh`)로 3개 기준에는 못 미치지만,
  위 두 조건이 각각 단독으로 전체 경로 요건을 충족한다.

---

## Phase 2 계획 (구현 제외 — 별도 승인 대상)

> **실행 계획은 [`dashboard-pip-floating.md`](./dashboard-pip-floating.md) 로 이관됐다.**
> 아래는 그 실행 계획의 출발점이 된 실측 스파이크 결과와 방향 판단만 남긴 참고 자료다.

### 실측 완료된 사실 (사용자 Chrome 149 에서 측정)

- `documentPictureInPicture` 존재, `isSecureContext` true(localhost), 실제 380×464 플로팅 창 생성 확인
- **사용자 제스처 필수** — 프로그래매틱 클릭으로는 창이 열리지 않음
- Claude 내장 브라우저(Electron)에서는 `requestWindow` 가 `InvalidStateError` → 실제 Chrome 필요
- opener 를 `location.reload()` 하면 PiP 참조 소실 → **Phase 1 의 갱신 방식과 상충**
- PiP 창은 opener 의 CSS 를 상속하지 않아 스타일시트 복사 필요
- Safari·Firefox 미지원

### 스파이크 (Phase 2 착수 전 필수)

Chrome auto-PiP 경로 — `navigator.mediaSession.setActionHandler('enterpictureinpicture', …)` +
설치형 PWA 또는 카메라/마이크 조건 + "자동 PiP" 콘텐츠 설정 — 가 대시보드 용도로 성립하는지 실측한다.
**이 경로에 대한 지식은 미검증이므로 문서상 가정으로 쓰지 않는다.**

- **성립 시**: 매니페스트 추가 + PWA 설치 안내 → 탭 포커스 이탈 시 자동 플로팅
- **미성립 시(폴백)**: 대시보드 우상단 "플로팅" 버튼 1회 클릭 → 세션 내내 유지되는 고정 플로팅

### 갱신 방식 전환

`location.reload()` → **HTML 폴링 + DOM 부분 치환**으로 바꾼다.
`fetch('dashboard.html')` → `DOMParser` 파싱 → `#dz-log` 와 동적 셀렉터만 교체.
`file://` 제약 때문에 로컬 정적 서버가 필요하다:

```bash
python3 -m http.server --directory .claude 8791
```

서버 기동을 워크플로우에 강제하지 않고 **opt-in** 으로 둔다(`/dashboard serve`).
서버 없이도 Phase 1 방식(파일 열기 + 포커스 리로드)이 계속 동작해야 한다.

부분 치환으로 바뀌면 라디오 상태가 리로드로 날아가지 않으므로 위 리스크 8 이 자연히 해소된다.

### 마이그레이션 (Phase 1 자산 보존)

- HTML 템플릿·셀렉터 규약·로그 마크업은 **그대로 재사용**한다
- 하단 스크립트만 교체된다(reload → 폴링 + PiP 진입)
- 즉 Phase 1 산출물 중 버려지는 것은 스크립트 블록 약 10줄뿐이다

---

## 사용자 승인이 필요한 핵심 결정

1. **갱신은 메인 세션의 Edit 로만 수행한다** — 셸 스크립트·`jq`·상태 JSON 을 모두 도입하지 않는다.
   대가는 갱신의 비결정성이며, `data-seq` 앵커와 셀렉터 표로 완화했다.
2. **대시보드는 전체 경로 작업에만 생성한다** — 축약 경로(단계 2개)에는 과하다.
3. **Phase 2 는 스파이크 결과에 따라 자동/수동 플로팅이 갈린다** — 자동 전환은 아직 보장할 수 없다.

### 세션 탭 라운드에서 승인이 필요한 결정

4. **현재 세션 번호를 `#dz-log` 여는 태그에 둔다** — `log` 의 추가 I/O 를 0으로 유지하는 대신
   `log`·`init` 의 grep/Edit 앵커를 부분 일치 방식으로 바꿔야 한다(놓치면 `log` 전체 실패).
5. **탭 바는 두 번째 세션부터 생성한다** — 단일 세션 대시보드를 깨끗하게 유지하는 대신
   `init` 에 "탭 바 유무" 분기가 하나 생긴다.
6. **세션 탭 전환 시 구분선을 전부 숨긴다**(`input[name="dzs"]:checked:not(#dzs-all) ~ #dz-log .session-head`
   고정 규칙 1개로 처리, 세션 개수와 무관) — 2026-08-05 사용자 피드백으로 애초 설계
   ("선택된 세션의 구분선만 시작 시각 캡션으로 남긴다")에서 수정. 세션 탭 도입 이전 로그는
   `모든 세션` 탭에서만 보인다(이 부분은 변경 없음).
