# 대시보드 플로팅(Document PiP) 폴백 모드 (PRP)

## 요구사항 요약

`/dashboard` 로 만든 `.claude/dashboard.html` 을 **화면 위에 항상 떠 있는 작은 창**으로 볼 수 있게 한다.
사용자가 대시보드 우상단 「플로팅」 버튼을 **한 번 클릭**하면 Document Picture-in-Picture 창이 열리고,
그 뒤로는 세션이 끝날 때까지 그 창이 유지되면서 메인 세션의 `init`/`step`/`log` 갱신이 자동으로 반영된다.
현재 방식(`location.reload()`)은 리로드 순간 PiP 참조를 죽이므로, **로컬 정적 서버 + HTML 폴링 +
부분 DOM 치환**으로 갱신 경로를 바꾼다. 서버는 **opt-in**(`/dashboard serve`)이고, 서버 없이
`file://` 로 여는 기존 사용자는 **오늘과 완전히 동일하게 동작**해야 한다(회귀 금지가 이번 라운드의
가장 강한 제약이다).

### 이 PRP 의 위치

[`docs/prps/session-dashboard.md`](./session-dashboard.md) 의 「Phase 2 계획」(L608~647)은 실측 스파이크
결과와 폴백 방향만 적어둔 **참고 자료**다. 자동 전환(Chrome auto-PiP, `navigator.mediaSession` + PWA)
경로는 사용자 지시로 **이번 스코프에서 제외**한다(YAGNI — 필요가 확인되면 별도 라운드).
**이 문서가 Phase 2 의 실제 실행 계획이다.**

### 확정 사항 (재논의 대상 아님)

1. **수동 버튼 클릭 → 고정 플로팅**, 단 하나의 경로만 만든다. 자동 전환 스파이크는 하지 않는다.
2. 갱신 방식을 폴링 + 부분 치환으로 바꾼다. 로컬 서버는 opt-in 이다.
3. `file://` 경로의 기존 동작(포커스 시 리로드)은 한 글자도 퇴화하지 않는다.
4. 그룹×단계 모델([`dashboard-group-matrix.md`](./dashboard-group-matrix.md), commit 67e86b4)의
   셀렉터 계약을 깨지 않는다.
5. `init`/`step`/`log`/`on`/`off` 의 **절차 서술은 건드리지 않는다**. 이번 변경은 템플릿(마크업·CSS·스크립트)과
   새 하위 명령 `serve` 에 한정된다.

### 사용자 스토리

> 전체 경로 작업을 돌리는 개발자로서, 에디터·터미널을 보는 동안에도 대시보드를 **화면 구석에 띄워둔 채**
> 진행 상황을 곁눈질하고 싶다. 탭을 오갈 필요가 없어져 "지금 어느 단계인지" 확인 비용이 0이 된다.

### 복잡도

**Medium** — 3~4 파일, 신규 코드는 템플릿 안 JS 약 85줄 + CSS 12줄 + 마크업 2줄 + `serve` 절차.
새 모듈·새 레이어는 없다.

---

## UX 전환

### Before

```
┌── 브라우저 탭 (file:///…/.claude/dashboard.html) ─────┐
│  세션 제목                                            │
│  ▇▇▇▇▇▇░░░░  3/6 · 50%                                │
│  단계 목록 / 매트릭스                                  │
│  작업 추적 로그                                        │
└───────────────────────────────────────────────────────┘
   ↑ 탭으로 돌아올 때마다 location.reload()
   ↑ 에디터를 보는 동안에는 아무것도 안 보인다
```

### After (`/dashboard serve` 후 http://localhost:8791/dashboard.html 로 연 경우)

```
┌── 브라우저 탭 ────────────────────[ 플로팅 ]──┐      ┌─ 항상 위 (420×620) ─┐
│  (플로팅 중에는 비어 있고 안내 문구만)         │  →   │ 세션 제목            │
│  "플로팅 창에서 보는 중입니다."                │      │ ▇▇▇▇▇░░ 3/6 · 50%   │
└───────────────────────────────────────────────┘      │ 단계/매트릭스        │
                                                       │ 작업 추적 로그       │
   5초마다 fetch → 바뀐 부분만 치환 →  ──────────────→ └─────────────────────┘
   (에디터를 보는 동안에도 계속 갱신된다)
```

### 상호작용 변화

| 접점 | Before | After | 비고 |
|------|--------|-------|------|
| `file://` 로 열기 | 포커스 시 전체 리로드 | **동일** | 버튼은 비활성 + 사유 안내 |
| `http://localhost` 로 열기 | (경로 없음) | 5초 폴링 + 부분 치환 | 리로드 없음 |
| 유형 필터·세션 탭 선택 | 리로드 시 초기화될 수 있음 | **폴링 중 보존됨** | 라디오를 치환 대상에서 제외해 얻는 부수 효과 |
| 플로팅 진입 | 없음 | 우상단 버튼 1클릭 | 사용자 제스처 필수(실측) — 자동 진입 시도 안 함 |
| 미지원 브라우저 | 없음 | 버튼 비활성 + 한 줄 사유 | Safari·Firefox·Claude 내장 브라우저 |

---

## 영향 범위

### 수정 파일 (3개 + 선택 1개)

| 파일 | 수정 내용 | 이유 |
|------|----------|------|
| `commands/dashboard.md` | frontmatter `argument-hint`, 「호출 규약」, 「데이터 모델 — 정적」 절, 신설 「갱신 모드와 폴링 동기화 계약」 절, 신설 「`serve`」 절, 템플릿의 헤더 주석 맵 · `<style>` · `<body>` 마크업 2줄 · `<script>` 전면 교체 | 이 커맨드가 유일한 실행 주체다. 템플릿·절차·규약이 전부 이 한 파일에 있다 |
| `tests/run.sh` | T22 에 하위 검증 **T22-29 ~ T22-38** 추가, T22 의 `test_desc`·선행 주석 갱신 | 이 저장소의 회귀 방지 수단은 grep 기반 문서 정합성 테스트뿐이다 |
| `README.md` | L120 커맨드 표의 `dashboard` 줄 수, L139~148 설명 문단에 2~3줄 추가 | 줄 수는 실제 값이어야 하고, 사용자가 `serve`·플로팅의 존재를 알 경로가 README 뿐이다 |
| `docs/prps/session-dashboard.md` (선택) | 「Phase 2 계획」 절 머리에 "실행 계획은 `dashboard-pip-floating.md` 로 이관" 2줄 | 두 문서가 각각 계획을 주장하는 상태를 막는다. **승인 항목 5** |

### 미영향 (전수 확인)

| 대상 | 확인 방법 | 결과 |
|------|----------|------|
| `install.sh` 의 `COMMANDS_FILE_COUNT=8` | `ls commands/*.md \| wc -l` = 8. 새 커맨드 파일을 만들지 않는다 | 변경 불필요 |
| `CLAUDE.md` | `/dashboard` 언급은 "착수 시 `init`, 단계 전환마다 `step`·`log`" 와 끄기 안내뿐. `serve` 는 워크플로우에 강제되지 않는 opt-in 이다 | **수정하지 않는다** |
| `init`/`step`/`log`/`on`/`off` 절차 서술 | 확정 사항 5 | 한 글자도 건드리지 않는다 |
| 셀렉터 계약 7종 · 불변식 2개 | 폴링은 **읽기 전용 소비자**다. 셀렉터를 소비만 하고 새로 만들지 않는다 | 계약 불변 |
| `.gitignore` | 서버는 프로젝트 밖 임시 디렉토리를 문서 루트로 쓴다(→ 설계 결정 4). 프로젝트 안에 새 파일이 생기지 않는다 | 변경 불필요 |
| T23-1~11 | `on`/`off` 절 · README 설치 절차 미변경. `argument-hint` 의 `\| on \| off` 연속 문자열 유지(→ 인터페이스 절) | 계속 통과 |

### 손대지 않는 것 (발견했지만 이번 요청과 무관)

- `commands/dashboard.md` L532 의 `~/Desktop/dashboard.html` 원본 경로 언급. 이전 라운드에서도 "언급만
  하고 지우지 않는다"로 처리됐다. 이번에도 동일.

---

## 필독 파일 (구현 착수 전)

| 우선순위 | 파일 | 범위 | 이유 |
|---------|------|------|------|
| P0 | `commands/dashboard.md` | L578~691 (템플릿 전문) | 유일한 수정 본체. 특히 L602~662 `<style>`, L664~688 `<body>`+`<script>` |
| P0 | `commands/dashboard.md` | L48~120 (데이터 모델), L473~575 (로그 UI 규격) | 라디오 `~` 결합자 제약과 셀렉터 계약. 폴링이 무엇을 건드리면 안 되는지의 근거 |
| P0 | `tests/run.sh` | L998~1233 (T22) | 새 하위 검증을 붙일 자리와 assert 스타일(`record_failure` 후 `return 1`) |
| P1 | `docs/prps/session-dashboard.md` | L608~647 | 실측된 PiP 제약 6가지. 이 PRP 의 모든 제약이 여기서 나온다 |
| P1 | `docs/prps/dashboard-group-matrix.md` | L123~148 (셀렉터 계약), L490~543 (리스크) | 선형/매트릭스 분기가 폴링·PiP 와 어떻게 만나는지 |
| P2 | `README.md` | L107~152 | 커맨드 표와 설명 문단의 문체 |

### 외부 조사

| 주제 | 근거 | 핵심 |
|------|------|------|
| Document PiP 동작 | **사용자 Chrome 149 실측**(`session-dashboard.md` L610~617) | 존재·`isSecureContext` true(localhost)·380×464 창 생성 확인 / **사용자 제스처 필수** / Electron 에서 `InvalidStateError` / opener 리로드 시 참조 소실 / CSS 미상속 / Safari·Firefox 미지원 |
| 자동 PiP(mediaSession + PWA) | **미검증** | `session-dashboard.md` 의 판단을 그대로 따른다 — 검증되지 않은 지식은 설계 가정으로 쓰지 않는다. 이번 스코프에서 제외 |
| `python3 -m http.server` | 표준 라이브러리 | `--bind`, `--directory`, 포트 인자를 지원. **기본 바인딩이 `0.0.0.0`** 이라 명시적으로 `--bind 127.0.0.1` 을 줘야 한다(→ 설계 결정 4) |

**새 npm/pip 의존성은 없다.** 유일한 외부 도구는 `python3`(opt-in 경로에서만, 표준 라이브러리 모듈).

---

## 데이터 모델

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
  **보강됨(R1, [`hub-first-entry-and-ui-signals.md`](./hub-first-entry-and-ui-signals.md)).**
  이 조건을 만족해도 허브 모달(iframe) 안에서 열린 문서는 `body.dz-embedded` 로 표시가
  CSS 로 숨는다 — 조건 자체는 바뀌지 않고 **표시 조건**이 하나 더해진다.

### 정적 요소 추가 (동적 셀렉터 표에 넣지 않는다)

`init`/`step`/`log` 가 절대 치환하지 않고, **폴링도 동기화하지 않는** 요소다.

| 요소 | 역할 |
|------|------|
| `#dz-pip-btn` | 플로팅 진입/종료 버튼. `.wrap` **바깥**(`<body>` 직계)에 둔다 |
| `#dz-pip-hint` | 상태·사유 한 줄. 기본 `hidden`, 스크립트가 텍스트를 넣을 때만 노출 |
| `body.dz-pip` | PiP 창 문서의 `<body>` 에만 붙는 클래스. 좁은 창용 여백 축소 규칙의 스코프 |

> **왜 `.wrap` 바깥인가**: 플로팅은 `.wrap` 서브트리를 **통째로 PiP 창으로 옮기는** 방식이다.
> 버튼이 `.wrap` 안에 있으면 버튼도 같이 옮겨가 (a) 좁은 창을 차지하고 (b) opener 에는 창을 닫을
> 수단이 남지 않는다. 이 배치는 **T22-37 이 줄 번호 비교로 강제**한다.

### 폴링 동기화 계약 — 무엇을 치환하고 무엇을 보존하는가

이 표가 스크립트와 DOM 사이의 계약이다. 기존 「동적(치환 대상) — 7 셀렉터」 표의 **소비자 측 대응표**다.

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
`querySelector('#dz-log')` 만 쓰고 `querySelector('[id="dz-log"]')` 는 **금지**한다.
→ T22-38 이 역방향 assertion 으로 막는다.

---

## 인터페이스

### 호출 규약 (`serve` 1개 추가)

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard init "<제목>" "<그룹A:단계1,단계2|그룹B:단계1,단계2>"
/dashboard step <n> <done|active|wait>
/dashboard step <g>.<p> <done|active|wait>
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
/dashboard serve [포트] | serve stop        # 플로팅용 로컬 정적 서버 (opt-in)
/dashboard on | off
```

### frontmatter

```yaml
argument-hint: "init \"<제목>\" \"<단계1|...> 또는 <그룹A:단계1,단계2|그룹B:...>\" | step <n>|<g>.<p> <done|active|wait> | log <impl|pass|fail|commit> \"<요약>\" [...] | serve [포트] | on | off"
```

> `| on | off` 를 **연속 문자열로 맨 뒤에 유지**한다 — T23-6 이 `head -4` 에서 이 부분일치를 확인한다.
> `serve` 는 그 앞에 넣는다.

### `serve` — 메인 세션이 수행할 절차

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

### 템플릿 마크업 추가 (`.wrap` **닫는 태그 뒤**, `<script>` 앞)

```html
<button id="dz-pip-btn" type="button">플로팅</button>
<div id="dz-pip-hint" hidden></div>
```

### 템플릿 CSS 추가 (`<style>` 의 `.foot` 규칙 **뒤**, 즉 블록 맨 끝)

```css
  #dz-pip-btn{position:fixed;top:18px;right:18px;z-index:9;font-family:inherit;font-size:12px;font-weight:700;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--navy);cursor:pointer;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-btn:disabled{color:var(--muted);cursor:not-allowed;box-shadow:none}
  #dz-pip-hint{position:fixed;top:54px;right:18px;z-index:9;max-width:300px;font-size:11px;line-height:1.5;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 10px;box-shadow:0 2px 8px rgba(19,51,91,.10)}
  #dz-pip-hint[hidden]{display:none}
  body.dz-pip .wrap{margin:10px auto;padding:0 10px}
  body.dz-pip .card{padding:14px 16px;border-radius:10px;margin-bottom:10px}
  body.dz-pip h1{font-size:16px}
  body.dz-pip .sub{margin-bottom:12px}
```

- **새 색 토큰을 만들지 않는다.** 전부 기존 `:root` 변수만 쓴다(T22-27 이 `:root` 줄 완전 일치를 검사).
- `body.dz-pip` 규칙은 opener 문서에서는 매칭 대상이 없어 아무 일도 하지 않는다
  (매트릭스 CSS 가 선형 세션에서 노는 것과 같은 구조 — 설계 결정 6, `dashboard-group-matrix.md`).

### 템플릿 스크립트 전면 교체 (현재 5줄 → 아래)

```html
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
```

### 템플릿 헤더 주석 맵 (마지막 줄 교체)

```
정적(불가침): 골격 · <style> · 제목 · 하단 스크립트
  #dz-pip-btn / #dz-pip-hint : 플로팅 진입 버튼과 안내 한 줄. .wrap 바깥에 있으며
                               init/step/log 도, 폴링 동기화도 이 둘을 건드리지 않는다
```

---

## 설계 결정과 근거

### 1. 갱신 모드는 **프로토콜 한 가지**로 가른다 (자동 폴백 없음)

`fetch` 를 먼저 시도해 보고 실패하면 리로드 모드로 떨어지는 구조를 만들지 않았다. 그러면
(a) 초기 상태가 비결정적이고, (b) 서버가 잠깐 죽었을 때 모드가 조용히 바뀌며, (c) 플로팅 버튼의
활성 조건이 시간에 따라 흔들린다. `location.protocol` 은 페이지 수명 내내 불변인 유일한 신호다.

그 대가로 **`file://` 에서는 플로팅을 아예 포기**한다. 이는 회피가 아니라 실측된 제약의 직접적 귀결이다 —
`file://` 에서는 `fetch` 가 막히고, 폴링이 없으면 `location.reload()` 가 유일한 갱신 수단이며,
리로드는 PiP 참조를 죽인다. **"정지 화면인 플로팅 창"은 대시보드로서 가치가 음수**이므로 버튼을
비활성화하고 사유를 보여주는 쪽을 택했다.

### 2. PiP 창에 콘텐츠를 **복제하지 않고 이동**한다

`pipDocument.body.appendChild(wrap)` 로 `.wrap` 서브트리를 통째로 옮긴다. 얻는 것:

- **동기화 코드가 한 벌로 유지된다.** 폴링은 `wrap.querySelector(...)` 로만 접근하므로 노드가 어느
  문서에 있든 같은 코드가 동작한다. 복제 방식이면 두 문서를 각각 갱신해야 하고, 라디오 상태가 두 벌이 된다.
- **요구사항 4(그룹×단계 모델 호환)가 자동으로 성립한다.** 선형(`#dz-step-*`)이든 매트릭스
  (`#dz-cell-*`)든 서브트리째 옮겨지므로 PiP 코드는 분기를 알 필요조차 없다. `<style>` 전문을
  복사하므로 `.matrix` 규칙과 `:root` 토큰도 같이 간다(`:root` 는 PiP 문서의 `<html>` 에 매칭된다).
- **라디오 필터가 그대로 산다.** `#dzf-impl:checked ~ #dz-log …` 같은 `~` 결합자는 DOM 트리 형제
  관계로 판정되는데, 형제들이 함께 이동하므로 관계가 보존된다. (래퍼 `div` 금지 제약과 충돌하지 않는다.)

대가: opener 페이지가 비게 된다 → `#dz-pip-hint` 로 "플로팅 창에서 보는 중" 을 안내하고,
`pagehide` 에서 원위치(`insertBefore(wrap, pipButton)`)로 되돌린다.

### 3. 폴링 비교 기준은 **직전 응답 문자열**이지 라이브 DOM 이 아니다

라이브 DOM 과 비교하면, 사용자가 오래된 로그 항목을 손으로 펼치는 순간 `<details open>` 이 파일과
달라져 **5초마다 다시 접힌다**. 직전 응답과 비교하면 "파일이 실제로 바뀐 순간에만" 치환이 일어나고,
그 사이의 사용자 조작(펼침·필터·탭)은 전부 살아남는다. 문자열 1회 비교라 비용도 더 싸다.

파일이 바뀐 순간에는 로그가 통째로 재구성되어 수동 펼침이 초기화되는데, 이건 **의도된 동작**이다 —
파일이 곧 상태라는 이 커맨드의 대전제(`session-dashboard.md`)와 일치한다.

### 4. 서버는 **프로젝트 밖 임시 디렉토리 + 심볼릭 링크 1개**를 문서 루트로 쓴다

`python3 -m http.server --directory .claude` 를 그대로 쓰면 `.claude/settings.local.json`(사용자의
권한 허용 목록)과 `.claude/commands/` 전부가 HTTP 로 노출된다. 기본 바인딩이 `0.0.0.0` 이라는 점까지
겹치면 같은 네트워크의 다른 기기에서도 읽을 수 있다.

그래서 두 가지를 함께 건다:

1. `--bind 127.0.0.1` — 루프백 고정. 절차에서 **생략 금지**로 명시하고 T22-35 가 회귀를 막는다.
2. `mktemp -d` 로 만든 임시 디렉토리에 `dashboard.html` **심볼릭 링크 하나만** 넣고 그곳을 문서
   루트로 삼는다 → 노출 표면이 정확히 파일 1개다. 디렉토리 목록에도 그 하나만 뜬다.

부수 효과로 프로젝트 안에 새 디렉토리가 생기지 않아 `.gitignore` 변경도 필요 없다.
**기각한 대안**: `--directory .claude`(간단하지만 위 노출을 감수해야 함),
`.claude/dz-serve/` 실디렉토리(프로젝트 오염 + `.gitignore` 항목 추가 필요).

### 5. 버튼은 **숨기지 않고 비활성 + 사유 한 줄**로 둔다

요구사항 3 은 "숨기거나 비활성화"를 허용하지만, 숨기면 사용자는 기능의 존재조차 모르고
"왜 안 되는지"를 알 방법이 없다. 비활성 버튼 + `#dz-pip-hint` 한 줄이면 **다음에 무엇을 해야 하는지**
(=`/dashboard serve` 실행 / Chrome 으로 열기)까지 전달된다. 사유는 세 가지뿐이라 분기도 얕다.

### 6. 자동 진입·자동 재시도를 **코드 수준에서 배제**한다

실측 결과 창 열기는 사용자 제스처를 요구한다. 따라서 `requestWindow` 호출은 **click 리스너 안 단 한
곳**에만 존재하고, `catch` 는 사유를 표시만 하며 재시도하지 않는다. `setTimeout`·`load` 이벤트에서
여는 코드를 두면 조용히 실패하는 경로가 생기고, 실패 원인이 "제스처 없음"인지 "미지원"인지 구분할 수
없게 된다.

### 7. 폴링 주기 5초 (상수)

로컬 파일 1개(수십 KB)를 5초마다 읽는 비용은 무시할 수 있고, 이 프로젝트의 실제 병목(메인 세션의
Edit/grep 호출 수)과는 무관하다. 사람이 "곁눈질" 용도로 쓰기에 5초는 충분히 즉각적이다. 설정 가능한
값으로 만들지 않는다(YAGNI). 매직 넘버 금지 규칙에 따라 `POLL_INTERVAL_MS` 상수로 선언한다.

### 8. 스코프 아웃과 사유

| 제외 항목 | 사유 |
|-----------|------|
| 자동 PiP 전환(mediaSession + PWA 매니페스트) | 사용자 지시로 이번 스코프에서 제외. 지식이 미검증이라 스파이크가 선행돼야 한다 |
| SSE·WebSocket 실시간 푸시 | 표준 `http.server` 로 불가능해 서버 코드를 직접 써야 한다. 5초 폴링으로 충분하다 |
| 서버 자동 기동(`init` 이 서버를 켜기) | opt-in 원칙 위반. 대시보드를 쓰는 대부분의 세션은 플로팅이 필요 없다 |
| PiP 창 크기·위치 기억 | 브라우저가 세션 내에서 관리한다. 저장소를 도입할 이유가 없다 |
| 여러 프로젝트 대시보드를 한 창에 | 대시보드는 프로젝트 로컬 임시 산출물이다. 다중화는 다른 제품이다 |
| `serve` 의 포트 자동 탐색 | 충돌 시 추측하지 않고 보고 후 중단 — 이 커맨드의 일관된 실패 정책 |

---

## 테스트 계획

### 무엇을 검증할 수 있고 무엇은 못 하는가

이 커맨드에는 실행 코드가 없다(LLM 지시문 + HTML 템플릿). **브라우저 런타임 동작은 자동 검증 대상이
아니고**, 템플릿·절차의 문자열 정합성과 자산 비퇴화만 grep 으로 검증한다 — T22 가 이미 채택한 방식이다.
런타임은 아래 「수동 확인」으로 커버한다.

### `tests/run.sh` — T22 에 하위 검증 추가 (T22-29 ~ T22-38)

새 테스트 함수를 만들지 않는다. `total_tests=22` 는 그대로 두고 `test_dashboard_template_integrity`
안에 이어 붙인다. 선행 주석과 `test_desc` 의 `T22-1~T22-28` 표기를 `T22-1~T22-38` 로 고친다.

| ID | 검증 | 방법 | 막으려는 회귀 |
|----|------|------|--------------|
| T22-29 | **file:// 리로드 경로 비퇴화** | `grep -q 'location.reload()'` **및** `grep -q "visibilitychange"` | 폴링으로 갈아치우면서 기존 사용자의 유일한 갱신 수단을 삭제 |
| T22-30 | 폴링 경로 존재 | `grep -q 'DOMParser'` **및** `grep -qF "cache:'no-store'"` | 폴링 미구현 / 브라우저 캐시로 갱신이 멈추는 퇴행 |
| T22-31 | 기능 감지 존재 | `grep -qF "'documentPictureInPicture' in window"` | 감지 없이 호출해 미지원 브라우저에서 예외 |
| T22-32 | 자동 진입 금지 문구 | `grep -q '자동 재시도하지 않는다'` | 제스처 제약을 잊고 자동 open 을 넣는 퇴행 |
| T22-33 | 스타일시트 복사 | `grep -qF "querySelectorAll('style')"` **및** `grep -q 'head.appendChild'` | PiP 창이 무스타일로 뜨는 퇴행(CSS 미상속은 실측된 제약) |
| T22-34 | 이동 방식 + 복귀 경로 | `grep -qF 'body.appendChild(wrap)'` **및** `grep -q 'pagehide'` | 복제 방식으로 바꾸거나 복귀를 빠뜨려 opener 가 영구히 비는 퇴행 |
| T22-35 | **서버 바인딩 안전** | `grep -qF -- '--bind 127.0.0.1'` **및** `grep -q '0\.0\.0\.0' 가 매칭되면 실패` | `.claude` 를 모든 인터페이스에 노출 |
| T22-36 | `serve` 가 인터페이스에 노출 | `head -4 \| grep -q 'serve'` **및** `grep -q '/dashboard serve'` | 절차만 있고 규약·힌트에 없어 아무도 못 씀 |
| T22-37 | **PiP UI 가 `.wrap` 바깥** | `id="dz-pip-btn"` 의 마지막 등장 줄 번호 > `id="dz-updated"` 줄 번호 | 버튼을 카드 안에 넣어 플로팅 창으로 같이 딸려가는 퇴행 |
| T22-38 | **grep 유일성 불변식** | `grep -q '\[id="dz-'` 가 매칭되면 실패 | 스크립트가 `[id="dz-log"]` 형태를 쓰면 `log`·`step` 의 grep 앵커가 줄 수를 잘못 세어 절차 전체가 깨진다 |

T22-35 · T22-38 은 **역방향 assertion**(매칭되면 실패)이다 — T22-7·T22-28 이 이미 쓰는 패턴이다.

T22-37 참고 구현(줄 번호 비교, 기존 스타일 준수):

```bash
  # T22-37: 플로팅 UI 가 .wrap 바깥에 있는지 — 템플릿에서의 마지막 등장 위치로 판정한다.
  # (.wrap 안에 있으면 PiP 창으로 같이 이동해 버튼으로 창을 닫을 수 없게 된다)
  local pip_button_line wrap_end_line
  pip_button_line=$(grep -n 'id="dz-pip-btn"' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  wrap_end_line=$(grep -n 'id="dz-updated"' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  if [[ -z "$pip_button_line" || -z "$wrap_end_line" || "$pip_button_line" -lt "$wrap_end_line" ]]; then
    record_failure "$test_name" "T22-37: 플로팅 버튼이 .wrap 바깥(#dz-updated 뒤)에 있지 않음"
    return 1
  fi
```

> `id="dz-updated"` 는 현재 문서에서 **정확히 1회**(L681, 템플릿) 등장함을 확인했다.

### 기존 테스트에 대한 영향 (전수 확인)

| 테스트 | 영향 | 근거 |
|--------|------|------|
| T22-2 (셀렉터 7종) | 계속 통과 | 셀렉터를 지우지 않는다 |
| T22-3·4 (배지·필터 라디오) | 계속 통과 | 마크업·CSS 미변경 |
| T22-5 (`COMMANDS_FILE_COUNT`) | 계속 통과 | 파일 수 불변(8) |
| T22-6·9·12 (init 가드·log 최적화·grep 패턴) | 계속 통과 | 절차 서술 미변경. **단 T22-38 이 새로 지키는 불변식과 짝을 이룬다** |
| T22-7 (`class="legend"` 부재) | 계속 통과 | 범례를 만들지 않는다 |
| T22-11·13~18 (세션 탭) | 계속 통과 | 세션 탭 마크업·CSS·절차 미변경 |
| T22-23·24·26 (매트릭스·선형 자산) | 계속 통과 | 진행 시각화 마크업 미변경 |
| T22-27 (`:root` 완전 일치) | 계속 통과 | 새 CSS 는 기존 토큰만 참조하고 `:root` 줄을 건드리지 않는다 |
| T23-6 (`argument-hint` 의 `\| on \| off`) | 계속 통과 | `serve` 를 `on` **앞**에 넣어 연속 문자열을 보존한다 |
| T23-11 (README `settings.local.json` 언급 ≤3) | 계속 통과 | README 추가 문장에 이 문자열을 넣지 않는다 |

### 검증 명령

```bash
cd /Users/pascal/works/personal/coding-env
bash tests/run.sh                    # 기대: 총 22 / 통과 22 / 실패 0
wc -l commands/dashboard.md          # README L120 의 줄 수를 이 값으로 갱신
head -4 commands/dashboard.md | grep -c '| on | off'   # 1 (T23-6 보호)
```

### 수동 확인 (자동화 불가 — Chrome 실기 필요)

| # | 절차 | 합격 기준 |
|---|------|----------|
| 1 | 기존 대시보드를 `file://` 로 연다 | 버튼 비활성 + `/dashboard serve` 안내. **탭 전환 시 리로드가 오늘과 동일하게 동작**(회귀 없음) |
| 2 | `/dashboard serve` → `http://localhost:8791/dashboard.html` | 버튼 활성. 페이지가 리로드되지 않음(스크롤 위치 유지로 확인) |
| 3 | 2번 상태에서 `/dashboard log impl "테스트"` | 5초 내 로그 항목이 **리로드 없이** 나타남 |
| 4 | 「구현」 필터를 고른 뒤 `log` 를 3회 호출 | 필터 선택이 유지됨(폴링이 라디오를 건드리지 않음) |
| 5 | 로그 항목을 손으로 펼치고 30초 대기 | 파일이 안 바뀌는 동안 펼침 상태가 유지됨 |
| 6 | 「플로팅」 클릭 | 별도 작은 창이 뜨고 **스타일이 정상**(색·카드·표). opener 는 안내 문구만 |
| 7 | 6번 상태에서 `/dashboard step 2 done`(선형) | 플로팅 창의 단계·진행률이 갱신됨 |
| 8 | 매트릭스 세션으로 6~7 반복(`step 2.3 done`) | 표가 그대로 렌더되고 칸이 갱신됨(그룹 모델 비회귀) |
| 9 | 플로팅 창을 닫는다 | 콘텐츠가 원래 탭으로 복귀, 버튼 라벨이 「플로팅」 으로 |
| 10 | 다른 탭으로 이동해 5분 방치 후 플로팅 창에 커서를 올린다 | 즉시 최신으로 갱신됨(타이머 스로틀링 보완 확인) |
| 11 | Safari 또는 Firefox 로 연다 | 버튼 비활성 + 미지원 안내 |
| 12 | Claude 내장 브라우저로 연다 | 클릭 시 `InvalidStateError` 안내가 표시되고 페이지는 정상 동작 |
| 13 | 서버를 끈 뒤 15초 대기 | 3회 실패 후 "서버가 켜져 있는지 확인" 안내 |
| 14 | 플로팅 중 다른(또는 같은) 세션에서 `/dashboard init` 으로 새 세션을 시작한다 | 다음 폴링 주기 내 창이 **스스로 닫히고** opener 가 자동 리로드되어 새 세션 탭이 나타남(사용자가 창을 직접 닫지 않아도 됨) |
| 15 | `curl http://<로컬IP>:8791/dashboard.html` | **연결 거부**(루프백 바인딩 확인) |

---

## 구현 순서

각 단계 뒤에 `bash tests/run.sh` 로 비회귀를 확인한다.

1. `commands/dashboard.md` — 「데이터 모델」에 정적 요소 3종 + 「폴링 동기화 계약」 + grep 유일성 불변식 추가
   → **검증**: 셀렉터 표 ↔ 스크립트가 같은 id 를 쓰는지 눈으로 대조
2. 템플릿 `<style>` 에 CSS 8줄 추가, `<body>` 에 마크업 2줄 추가, 헤더 주석 맵 갱신
   → **검증**: `git diff` 로 `:root` 줄 무변경 확인(T22-27)
3. 템플릿 `<script>` 전면 교체
   → **검증**: 생성될 HTML 에 `[id="dz-` 문자열이 없는지, `id="dz-log"` 가 여전히 1줄인지 확인
4. 「`serve`」 절 신설 + frontmatter·호출 규약 갱신
   → **검증**: `head -4 | grep '| on | off'` 가 1
5. `tests/run.sh` — T22-29~38 추가, `test_desc`·주석 갱신 → **검증**: 22/22
6. `README.md` — 줄 수(`wc -l`)와 설명 2~3줄 → **검증**: `bash tests/run.sh` 재실행
7. (승인 시) `session-dashboard.md` Phase 2 절에 이관 포인터 2줄
8. 위 「수동 확인」 1~15 수행

---

## 리스크와 대안

### 1. 숨은 탭의 타이머 스로틀링 — 폴링이 최대 1분까지 늘어질 수 있다

**가능성 상 / 영향 중.** 플로팅의 전형적 사용 상황이 바로 "opener 탭이 숨겨진 상태"다. Chrome 은 숨은
탭의 타이머를 1초로, 5분 뒤에는 1분 간격으로 조인다. **PiP 창이 열려 있을 때 opener 가 이 스로틀링에서
면제되는지는 검증되지 않았으므로 가정하지 않는다.**

완화(전부 우리 통제 범위 안):
- `pipDocument.body` 의 `pointerenter` 에 즉시 폴링을 건다 → 창을 쳐다보고 커서를 올리면 최신화된다.
- `visibilitychange`·`focus` 에도 즉시 폴링을 건다.
- `#dz-updated`(갱신 시각)가 창에 항상 보이므로 **정체가 눈에 보인다** — 조용히 틀린 화면이 되지 않는다.
- 최악(1분 지연)도 이 대시보드의 갱신 주기(단계 전환은 보통 수 분 간격)를 고려하면 수용 가능하다.

**기각한 대안**: `Worker` 나 `WebSocket` 으로 스로틀링을 우회 → 서버 코드를 직접 써야 하고
(표준 `http.server` 로 불가) opt-in 스크립트 하나가 서버 프로젝트가 된다.

### 2. 로컬 서버가 파일을 노출한다

**가능성 중 / 영향 중.** 설계 결정 4 에서 이중으로 막았다(루프백 바인딩 + 임시 디렉토리에 심볼릭 링크
1개). 남는 노출은 "같은 기기의 다른 로컬 프로세스가 dashboard.html 을 읽을 수 있다"뿐이고, 그 파일은
이미 프로젝트 로컬 임시 산출물이다. 브라우저의 다른 오리진에서는 CORS 헤더가 없어 응답을 읽지 못한다.
추가 완화: 절차 5단계가 항상 `/dashboard serve stop` 을 안내한다. **T22-35 가 회귀를 막는다.**

### 3. Claude 내장 브라우저(Electron)에서는 플로팅이 안 된다

**가능성 상 / 영향 하.** 실측된 사실이다(`InvalidStateError`). 완화: `catch` 에서 "Chrome 에서 열어
보세요"를 명시한다. 폴링·필터 등 나머지 기능은 전부 정상 동작하므로 열화가 국소적이다.
**기각한 대안**: 내장 브라우저 감지 후 다른 UI 로 분기 → user-agent 스니핑은 깨지기 쉽고, 실패 메시지
하나로 충분하다.

### 4. 그룹×단계 모델과의 호환 — 실제로 자동으로 맞는가?

**검증 결과: 맞는다. 단 조건이 하나 있다.**

- `.wrap` 을 통째로 옮기고 `<style>` 전문을 복사하므로 선형/매트릭스 어느 쪽이든 그대로 렌더된다.
  `:root` 토큰은 PiP 문서의 `<html>` 에 매칭되고, `.matrix` 규칙도 같은 `<style>` 안에 있다.
- 폴링의 진행 시각화 동기화는 `#dz-steps,#dz-matrix` **단일 셀렉터**로 두 분기를 흡수한다
  (불변식 1: 한 파일에 하나만 존재).
- **조건**: 좁은 창(420px)에서 5~6열 매트릭스는 열이 눌린다. `dashboard-group-matrix.md` 리스크 5 가
  이미 "줄바꿈으로 수용"으로 결론 낸 사안이며, `body.dz-pip` 의 패딩 축소 규칙이 이를 조금 완화한다.
  가로 스크롤 컨테이너는 래퍼 `div` 를 요구해 `~` 결합자 제약과 충돌하므로 **도입하지 않는다**(기존 결론과 동일).
- 파생 리스크 없음: 폴링은 `#dz-cell-*`·`#dz-step-*` 을 **개별적으로 알 필요가 없다**.

### 5. 플로팅 중 새 세션이 시작되면 창을 강제로 닫는다 (사용자 승인 반영 — 최종 결정)

**가능성 하 / 영향 하.** 라디오를 치환하지 않는다는 계약의 대가로 세션 탭 개수 변화는 부분 치환으로
반영할 수 없다. 최초 설계는 "사용자가 직접 닫을 때까지 대기"였으나, 사용자 승인 단계에서 **감지 즉시
`pipWindow.close()` 로 강제 종료 → `pagehide` 핸들러가 `reloadPending` 을 보고 자동 리로드**하는
쪽으로 확정했다(수동 확인 14 갱신). Document PiP 스펙상 닫기는 opener 가 언제든 호출할 수 있고
사용자 제스처 요건은 "여는" 동작에만 걸린다 — 실측 제약과 충돌하지 않는다.

대가: 사용자가 플로팅 창을 보고 있는 도중 예고 없이 닫힐 수 있다(새 세션은 전체 경로 작업당 보통
1회뿐이라 빈도는 낮다). opener 로 자동 복귀하고 새 세션 탭이 즉시 보이므로, 다시 보려면 「플로팅」을
한 번 더 클릭하면 된다.

**기각한 대안 1**: 창을 열어둔 채 대기(구 설계). 창이 갱신되지 않는 동안에도 열려 있어 "멈춘 화면"이
정상처럼 보이는 게 더 나쁘다고 판단했다.
**기각한 대안 2**: 새 라디오만 골라 DOM 에 끼워 넣는 증분 삽입. 동작은 하지만 **탭 마크업의 구조 지식이
`init` 절차와 스크립트 두 곳에 복제**된다 — 나중에 탭 마크업을 바꾸면 스크립트가 조용히 깨진다.

### 6. `python3` 부재

**가능성 하 / 영향 하.** macOS 는 Xcode CLT, 대부분의 Linux 는 기본 제공한다. 절차 2단계에서 확인 후
**중단하고 보고**하며, 다른 정적 서버를 임의로 설치하지 않는다. `serve` 는 opt-in 이므로 이 의존성이
기존 기능에 전파되지 않는다.

### 7. 스크립트가 5줄에서 ~85줄로 늘어난다

**가능성 확정 / 영향 하.** 템플릿이 커지지만 `init` 은 이 블록을 **그대로 Write** 할 뿐 파싱하지 않는다.
`log`·`step` 의 grep 앵커는 id 문자열 기반이라 스크립트 길이와 무관하다 — **단 grep 유일성 불변식을
지킬 때만** 그렇다(T22-38 이 강제).

### 8. 검토했으나 채택하지 않은 전체 대안

| 대안 | 기각 사유 |
|------|----------|
| **자동 PiP(mediaSession + PWA)** | 사용자 지시로 스코프 아웃. 지식 미검증이라 스파이크가 선행돼야 하고, 성립해도 PWA 설치라는 사용자 부담이 남는다 |
| **`location.reload()` 유지 + 리로드 후 PiP 자동 재진입** | 실측상 불가능 — 창 열기는 사용자 제스처를 요구한다 |
| **`file://` 에서도 버튼을 열어주되 정지 화면 허용** | 갱신되지 않는 대시보드는 오해를 부른다. 비활성 + 사유 안내가 정직하다 |
| **폴링 시 `document.body` 전체를 교체** | 코드는 3줄로 줄지만 라디오가 5초마다 리셋돼 필터·세션 탭이 사실상 못 쓰게 된다 |
| **PiP 창에 콘텐츠를 복제하고 양쪽 갱신** | 동기화 코드가 두 벌, 라디오 상태가 두 벌. 이동 방식이 모든 면에서 단순하다 |
| **`serve` 없이 `python3 -m http.server` 를 README 안내로만** | 포트·바인딩·문서 루트를 사용자가 매번 맞춰야 하고, 안전한 기본값(루프백·단일 파일)이 강제되지 않는다 |

---

## 워크플로우 경로 판정

**전체 경로(설계 → 구현 → 검수)가 맞다.** 근거는 각각 단독으로 충족한다:

- **공개 인터페이스 변경**: 하위 명령 `serve` 신설, `argument-hint` 변경.
- **데이터 모델 변경**: 정적 요소 3종(`#dz-pip-btn`·`#dz-pip-hint`·`body.dz-pip`) 추가,
  「폴링 동기화 계약」과 「grep 유일성 불변식」이라는 새 계약 도입.
- **파일 3개 이상**: `commands/dashboard.md`, `tests/run.sh`, `README.md`.
- **새 외부 의존성**: `python3`(opt-in 경로 한정).
- **민감 영역**: 로컬 네트워크 포트를 여는 변경이다. **검수는 opus 승격을 권장한다**
  (`serve` 절차의 바인딩·문서 루트가 검수 대상의 핵심).

---

## 사용자 승인이 필요한 핵심 결정

1. **`file://` 에서는 플로팅을 지원하지 않는다.** 버튼은 비활성 + "`/dashboard serve` 를 실행하세요"
   안내. 플로팅을 쓰려면 로컬 서버 기동이 **필수**다 — 이 추가 절차를 수용하는가?
   (대신 서버 없이 쓰던 기존 사용자는 오늘과 100% 동일하게 동작한다.)

2. **서버 문서 루트를 임시 디렉토리 + 심볼릭 링크 1개로 한다**(설계 결정 4). `--directory .claude`
   보다 절차가 한 줄 길어지는 대신 `settings.local.json` 등이 HTTP 로 노출되지 않는다.
   간단한 쪽(`--directory .claude --bind 127.0.0.1`)을 원하면 지금 말해달라.

3. **폴링은 라디오(`유형 필터`·`세션 탭`)와 `<style>` 을 치환하지 않는다.** 덕분에 사용자의 필터 선택이
   보존되지만, 플로팅 중에 새 세션이 시작되면 **창을 즉시 강제로 닫고 자동 리로드**한다(예고 없음 —
   사용자 승인으로 확정, 리스크 5 참조). 보고 있던 화면이 갑자기 사라지는 대신 정합성을 우선한다.

4. **템플릿 하단 스크립트가 5줄에서 약 85줄로 늘어난다.** 대시보드 HTML 이 "JS 거의 없음"에서
   "작은 클라이언트 런타임 있음"으로 성격이 바뀐다. 필터·탭이 여전히 **JS 없이 CSS 로만** 동작한다는
   기존 원칙은 유지된다(스크립트는 갱신과 플로팅만 담당).

5. **`docs/prps/session-dashboard.md` 의 Phase 2 절에 "실행 계획은 이 문서로 이관" 2줄을 추가할지.**
   추가하지 않으면 두 문서가 각각 Phase 2 계획을 주장하는 상태가 남는다.
