# 세션 진행 상황 대시보드 (PRP)

## 요구사항 요약

개발 세션의 진행 상황을 브라우저에서 한눈에 볼 수 있는 대시보드를 워크플로우 자산으로 편입한다.
사용자가 수작업으로 운영하던 `~/Desktop/dashboard.html` 을 `/dashboard` 커맨드로 정식화하되,
가장 큰 불만이었던 **작업 추적 로그의 가독성**을 접기/배지/필터로 개선한다.

Phase 1(이번 구현 대상)은 단일 HTML 파일 + 포커스 시 자동 새로고침으로 서버 의존성 없이 동작한다.
Phase 2(계획만, 구현 제외)는 플로팅 윈도우(Document Picture-in-Picture)를 얹는다.

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

### 미영향

- `agents/` — 서브에이전트는 대시보드에 접근하지 않으므로 수정 없음
- `rules/` — 코드 품질 기준 계층이며 워크플로우 산출물과 무관

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

### 동적(치환 대상)

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-title` | 텍스트 | 세션 제목 |
| `#dz-subtitle` | 텍스트 | 단계 흐름 요약 · 작업 유형 |
| `#dz-progress-bar` | inline `style="width:N%"` | 완료 단계 / 전체 단계 |
| `#dz-progress-pct` | 텍스트 | `3/6 · 50%` |
| `#dz-step-{n}` | `class` 속성 + 자식 `.chip` 텍스트 | `done`\|`active`\|`wait` / `완료`\|`진행중`\|`대기` |
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
- `data-kind` — `impl` \| `review` \| `commit` \| `note` (필터 대상)
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
prepend해 세션 경계를 표시한다. 위 로그 항목 스키마의 `.entry` 가 아니라 별도
클래스이므로 필터 CSS(`.entry:not([data-kind=...])`)의 영향을 받지 않고 어떤
필터 상태에서도 항상 보인다. 개별 로그 항목에는 세션 태그를 달지 않는다 —
구분선만으로 세션 경계를 알 수 있으면 충분하다(YAGNI).

---

## 인터페이스

### 호출 규약

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard step <n> <done|active|wait>
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
```

### `init` — 메인 세션이 수행할 절차

1. `.claude/dashboard.html` 존재 여부 확인
   - **이미 존재하면**: 제목·단계 목록 등은 덮어쓰지 않는다. 대신 세션 경계를
     표시하기 위해 `#dz-log` 맨 위에 `<li class="session-head" data-session="N">`
     구분 항목을 prepend 한다. `N` 은 기존 `.session-head` 의 `data-session` 최댓값
     + 1(없으면 2 — 그 이전 로그는 암묵적으로 세션 1). 이후 "기존 대시보드를
     이어서 사용합니다"라는 취지로 안내한 뒤 기존 `file://` 경로를 출력하고 절차를
     종료한다(이후 단계 미실행). **한계**: "새 작업"과 "기존 작업 재개"를 구분하지
     못한다 — 같은 프로젝트에서 진짜 새 전체 경로 작업을 시작했는데 이전 대시보드
     파일이 남아 있으면 옛 대시보드를 계속 보여준다. 새 작업 시작 시 기존 파일을
     지우거나 다시 만들지 사용자에게 확인하도록 안내 문구에 명시한다.
   - **존재하지 않으면**: `commands/dashboard.md` 의 템플릿을 `.claude/dashboard.html`
     로 Write 하고 계속 진행
2. `#dz-title`·`#dz-subtitle` 치환, 단계 개수만큼 `#dz-step-{n}` li 생성(1번은 `active`, 나머지 `wait`)
3. `#dz-progress-bar`·`#dz-progress-pct` 를 `0/N · 0%` 로 설정
4. 사용자에게 `file://` 절대 경로를 출력해 브라우저로 열도록 안내

### `step` — 절차 (Edit 2~3회)

1. `#dz-step-{n}` 의 `class` 와 `.chip` 텍스트를 새 상태로 치환
2. `done` 으로 바뀐 경우 진행률 재계산 → `#dz-progress-bar` width 와 `#dz-progress-pct` 치환
3. `#dz-updated` 치환

### `log` — 절차 (Bash grep 1회 + Read 1~2회 + Edit 2회, 결정적)

0. **최신 항목만 확인**: 로그는 항상 맨 앞에 prepend되므로 최댓값 `S` 와 `S-2` 항목은
   항상 로그 앞부분에 있다. 따라서 파일 전체를 Read하지 않고 `grep`으로 `#dz-log` 시작 줄을
   찾은 뒤 그 지점부터 제한된 줄만 Read해 확인한다(로그가 길어져도 이 단계의 비용이 늘지 않는다).
1. **직전 펼침 회수**: 위에서 확인한 최대 `data-seq` 를 `S` 라 할 때, `data-seq="S-2"` 항목의
   `<details open>` 를 `<details>` 로 치환한다. 해당 seq 가 없으면 생략한다.
   → 결과적으로 **항상 최신 3건만 펼쳐진다.**
2. **prepend**: `<ul class="log" id="dz-log">` 바로 뒤에 `data-seq="S+1"` 인 새 `<li>` 를 삽입한다.
   삽입 전 요약·상세 텍스트는 `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;` 순서로 이스케이프한다
   (코드 조각이 그대로 들어가면 태그가 깨진다 — 검수 지적 반영).

`data-seq` 가 문서 내 유일 문자열이므로 두 치환 모두 앵커가 명확하고, 순번을 세는 판단이 개입하지 않는다.

### CLAUDE.md 트리거 (메인 세션 전용)

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

라디오 3개를 `#dz-log` 의 **앞 형제**로 두고 `~` 결합자로 제어한다.

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

원본의 골격·`:root` 색 토큰·단계 리스트는 그대로 유지한다.

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
경과 시간만은 CSS 로 불가능해 스크립트를 쓴다.

---

## 테스트 계획

LLM 지시문 방식이므로 자동 검증 가능한 것은 **설치·문서 정합성과 템플릿 무결성**이다.
런타임 동작(실제 Edit 결과)은 자동화 대상이 아니다 — 억지 테스트를 만들지 않는다.

### tests/run.sh 수정

- 기존 커맨드 개수 기대값 `7` → `8` (2곳)
- `test_commands_installed` 의 커맨드 이름 목록에 `dashboard` 추가

### tests/run.sh 신규 T22 — 템플릿 무결성

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

T22-5 는 이번 변경의 재발 방지책이다 — 커맨드를 추가하고 상수를 안 고치는 실수를 잡는다.
T22-6 은 두 번째 세션이 미완료 작업을 재개할 때 `init` 재호출로 기존 진행 상황(로그·단계 상태)이
통째로 날아가는 것을 막는 재발 방지책이다.
T22-7 은 범례 div 제거가 실수로 되돌려지지 않았는지 확인하는 회귀 방지책이다.
T22-8 은 세션 카테고리화 기능(세션 구분 마커) 자체가 구현 과정에서 누락되지 않았는지 확인하는
재발 방지책이다.
T22-9 는 `log` 절차가 다시 파일 전체 Read 방식으로 퇴행하지 않았는지 확인하는 재발 방지책이다
— 가변 비용 문제의 재발을 막는다.

### 수동 확인 항목 (테스트 스위트 밖)

- `/dashboard init` 후 브라우저에서 열어 레이아웃 확인
- 로그 5건 추가 후 최신 3건만 펼쳐지는지
- 필터 라디오 3종 동작
- 탭 포커스 복귀 시 자동 새로고침

---

## 리스크와 대안

### 1. 같은 프로젝트에서 세션 2개를 동시에 돌리면 서로 덮어쓴다

프로젝트 로컬 경로 채택으로 프로젝트 간 충돌은 사라졌지만 동일 프로젝트 병행은 남는다.
**YAGNI 로 미지원**한다. 필요해지면 파일명에 세션 식별자를 붙이는 것으로 확장 가능하다.

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

---

## Phase 2 계획 (구현 제외 — 별도 승인 대상)

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
