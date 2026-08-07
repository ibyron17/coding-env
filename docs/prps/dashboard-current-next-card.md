# 대시보드 「지금」 카드 — 현재 단계 · 경과 시간 · 다음 단계 (PRP)

## 요구사항 요약

`/dashboard` 산출물 `.claude/dashboard.html` 에 **현재 진행중인 단계와 그 단계에 머문 시간, 그리고
다음 단계**를 한 블록으로 보여주는 카드를 추가한다. 핵심은 **경과 시간**이다 — 지금 대시보드
어디에도 "이 단계가 얼마나 오래 돌고 있는가"를 알려주는 값이 없고, 이 값은 **정적 HTML 로는 표현할
수 없어** 오직 스크립트만 만들 수 있다. 단계명·다음 단계는 이 새 정보를 담을 문맥이며, 카드가
플로팅(PiP) 창에서 **한 줄 곁눈질로 상황을 읽는 유일한 요약 블록**이 되게 한다.

동시에 이 기능은 **한 번 제거된 적이 있다**(→ 아래 「제거 이력」). 그때의 실패 원인을 정확히
피하는 것이 이 PRP 의 절반이다: **`step` 호출 규약에 인자를 단 하나도 추가하지 않는다.**

### 제거 이력 — 이번 설계가 반드시 피해야 할 것 (커밋 `a6966aa`, 2026-08-05)

거의 같은 기능이 이미 있었고 삭제됐다. 삭제된 자산과 사유는 아래와 같다.

| 삭제된 것 | 형태 |
|-----------|------|
| `#dz-current` · `#dz-current-meta` · `#dz-current-clock` · `#dz-next` | 동적 셀렉터 4종 (당시 표는 **11 셀렉터**였고 이 삭제로 7이 됐다) |
| `div.card.duo` + `.slot` · `.slot b` · `.slot .meta` | 카드 마크업 + CSS 3줄 |
| `_dzElapsed()` (4줄) | `data-started-at` 을 읽어 `N분 경과` 를 그리는 스크립트 |
| `step <n> <state> ["현재 위치"] ["다음 단계"] ["담당 에이전트 · 모델"]` | **`step` 의 선택 인자 3개** |

> 커밋 메시지 원문: *"불필요하다고 판단된 '현재 위치/다음 단계' 카드(`div.card.duo`)와 관련
> 셀렉터·인자(`dz-current` 등, `step` 호출 규약의 선택 인자 3개)를 제거해 인터페이스를 단순화한다."*

**진짜 원인은 카드가 아니라 인자였다.** 매 `step` 호출마다 "현재 위치"·"다음 단계"·"담당 에이전트"를
따옴표 3개로 더 넘겨야 했고, 그 세 값 중 둘은 **단계 목록에서 이미 파생 가능**했으며 하나는
자유 텍스트였다. 호출 비용은 매번 드는데 얻는 정보는 대부분 중복이었다. 그 상태에서 유일하게
새롭던 정보(경과 시간)까지 함께 버려졌다.

이번 설계는 **인자 0개 추가**로 그 정보만 되살린다.

### 사용자와 합의된 확정 사항 (재논의 대상 아님)

1. **`step`(및 `init`·`log`·`impl`)의 호출 규약에 새 인자를 추가하지 않는다.** 필수든 선택이든
   금지다. a6966aa 의 직접적 사유다.
2. **순수 파생만으로 이루어진 카드는 만들지 않는다.** 사용자 판정: *"파생형이면 굳이 컴포넌트를
   추가해서 보여줄 필요는 없는거 같은데?"* → 카드는 **어디에도 없던 정보**를 최소 하나 담아야 한다.
3. **이미 보이는 정보를 새 셀렉터로 중복시키지 않는다.** 특히 `.step-detail` 은 현재 단계 줄에
   이미 보이고 PiP 압축 뷰에서도 활성 단계의 것만 보인다 — 카드로 **재노출하지 않는다**(설계 결정 4).
4. **기존 불변식·셀렉터 계약을 깨지 않는다.** 「동적(치환 대상) — 7 셀렉터」 표의 **행 수는 7 그대로**,
   불변식 1~6 무손상. 회귀 테스트는 `tests/run.sh` 의 T22 에 이어 붙이고 `total_tests=22` 를 유지한다.

### 이 PRP 의 위치 — 선행 라운드와의 관계

| 문서 / 커밋 | 상태 | 이 PRP 와의 관계 |
|------------|------|-----------------|
| [`session-dashboard.md`](./session-dashboard.md) | 커밋됨 | 원형. "DOM 자체가 상태" · "메인 세션만 갱신" · **"CSS 로 되는 건 CSS 로"** |
| 커밋 `a6966aa` | **되돌리는 것이 아니라 교훈으로 삼는다** | 삭제된 4 셀렉터·3 인자를 **부활시키지 않는다.** 되살리는 것은 경과 시간 개념 하나뿐이다 |
| [`dashboard-group-matrix.md`](./dashboard-group-matrix.md) | 커밋됨 | 불변식 1(선형/매트릭스 비공존). **매트릭스 모드 방침의 근거**(설계 결정 3) |
| [`dashboard-pip-floating.md`](./dashboard-pip-floating.md) | 커밋됨 | 폴링 동기화 계약 · `apply()` · **`if(!isServed){…return;}` 조기 반환**(설계 결정 6의 함정) |
| [`dashboard-step-detail-pip-compact.md`](./dashboard-step-detail-pip-compact.md) | 커밋됨 | `.step-detail` · `:empty` 숨김 · PiP 압축 스코핑. **`.step-detail` 재사용의 선례이자 중복 금지의 근거** |
| [`dashboard-impl-substeps.md`](./dashboard-impl-substeps.md) | 커밋됨 | `:has()` 자동 숨김 · 5번째 sync 함수 추가 · 역방향 assertion 테스트 문체. **이번 라운드가 그대로 따르는 형판** |

> **기준선은 커밋된 HEAD(`48e47d0`)다.** 워킹 트리 clean.
> `commands/dashboard.md` **1113줄**, `tests/run.sh` **1705줄**(T22-1~T22-58, T23-1~T23-11),
> `README.md` **338줄**(L120 의 줄 수 `1113` 은 현재 정확하다).

### 사용자 스토리

> 전체 경로 작업을 돌리는 개발자로서, 화면 구석의 플로팅 창을 흘깃 보고 **"지금 어느 단계이고,
> 그 단계에 얼마나 오래 머물러 있는지"**를 알고 싶다. 지금은 `3 구현 [진행중]` 이 두 시간째
> 그대로인지 방금 시작한 것인지 화면만으로는 구분할 수 없고, `갱신: 2026-08-07 09:20` 이라는
> 절대 시각을 머릿속에서 현재 시각과 빼야 한다.

### 복잡도

**Low~Medium** — 3파일. 신규 자산은 **마크업 4줄 + CSS 6줄 + JS 함수 5개(약 25줄) + `step`·`init`
절차에 규칙 표 1개와 `<li>` 형태 1줄 + 테스트 9개.** 새 하위 명령 없음, 새 인자 없음,
새 색 토큰 없음, 새 의존성 없음, 동적 셀렉터 증가 0.

---

## 스코프와 비목표

### 스코프 안

- 「지금」 카드 1장: 현재 단계 번호·이름 / **경과 시간** / **마지막 기록 이후 경과** / 다음 단계.
- `step` 이 `active` 로 **전이하는 순간**에만 `<li>` 에 자동으로 찍는 `data-started-at` 속성.
  (인자가 아니다 — 상태 전이 자체가 트리거다.)
- 카드 전체를 CSS 만으로 자동 숨김: 매트릭스 세션 · 진행중 단계 없음.
- 폴링(`apply()`)·30초 틱 양쪽에서의 재렌더.

### 비목표 (명시적으로 만들지 않는 것)

| 제외 항목 | 사유 |
|-----------|------|
| **`step` 의 새 인자(`"현재 위치"`·`"다음 단계"`·`"담당 · 모델"`)** | 확정 사항 1. a6966aa 가 제거한 바로 그것이다 |
| **담당 에이전트·모델 전용 필드** | `.step-detail` 에 `"구현 착수 · implementer(sonnet) 디스패치 중"` 을 자유 텍스트로 적으면 끝난다. 별도 필드는 소비자가 없다(YAGNI) |
| **카드에서의 `.step-detail` 재노출** | 확정 사항 3. 바로 위 활성 단계 줄에 이미 보이고, PiP 에서도 활성 단계 것만 보인다 — 인접 요소의 순수 중복 |
| **매트릭스 모드용 카드(그룹별 다중 표시)** | 설계 결정 3. "현재/다음"이 개념적으로 성립하지 않는다 |
| **단계별 소요 시간의 누적·이력·통계** | 새 데이터 구조가 필요하다. `.claude/dashboard.html` 은 기능 단위 임시 산출물이다 |
| **`#dz-impl-{k}` 항목별 경과 시간** | `dashboard-impl-substeps.md` 비목표에서 이미 기각됐다. 이번에도 매크로 단계에만 붙인다 |
| **예상 완료 시각·ETA** | 과거 단계 소요 시간 이력이 없으면 추정 근거가 없다. 근거 없는 숫자는 대시보드 신뢰를 깎는다 |
| **초 단위 표시·1초 틱** | 분 단위로 충분하다. 곁눈질 화면에서 초가 흐르는 것은 소음이다 |
| **타임존·서버 시각 처리** | 대시보드를 쓰는 브라우저와 값을 쓰는 오케스트레이터가 같은 머신이다(리스크 4) |

---

## UX 전환

### Before

```
┌── 세션 진행 상황 ─────────────────────────────┐
│ ▇▇▇▇░░░░  2/5 · 40%                           │
│ 1 설계                              [완료]    │
│ 2 사용자 승인                       [완료]    │
│ 3 구현                            [진행중]    │  ← 방금 시작인지 두 시간째인지
│     implementer 디스패치 중                   │     화면만으로는 알 수 없다
│ 4 검수                              [대기]    │
│ 5 커밋                              [대기]    │
└───────────────────────────────────────────────┘
                        갱신: 2026-08-07 09:20   ← 절대 시각. 머릿속 뺄셈 필요
```

### After

```
┌── 세션 진행 상황 ─────────────────────────────┐
│ (그대로)                                      │
└───────────────────────────────────────────────┘
┌───────────────────────────────────────────────┐
│ 지금  3. 구현        42분 경과 · 마지막 기록 6분 전 │  ← 42분 = 새 정보
│       다음 → 4. 검수                          │     6분 전 = 정체 감지
└───────────────────────────────────────────────┘
┌── 구현 세부 작업 ─────────────────────────────┐ (그대로)
┌── 작업 추적 ─────────────────────────────────┐ (그대로)
```

매트릭스 세션(그룹 2개 이상)이거나 진행중 단계가 하나도 없으면 **카드가 통째로 렌더되지
않는다** — 오늘과 화면이 완전히 동일하다.

### 상호작용 변화

| 접점 | Before | After | 비고 |
|------|--------|-------|------|
| `/dashboard init "…" "A\|B\|C"` | 1번 단계 active | **동일 + 1번 `<li>` 에 `data-started-at`** | 인자 무변경 |
| `/dashboard init "…" "G:A,B\|H:A,B"` | 매트릭스 | **완전히 동일**(카드는 CSS 가 숨김) | 절차 무변경 |
| `step <n> <state> ["상세"]` | 상태 + 상세 | **동일 + active 전이 시 `data-started-at` 자동 각인** | **인자 0개 추가** |
| `step <g>.<p> <state>` | 칸 상태 | **완전히 동일** | 각인하지 않는다 |
| `impl` / `log` / 세션 탭 / 유형 필터 | — | **완전히 동일** | 한 글자도 안 바뀐다 |
| 매크로·세부 진행률 | — | **완전히 동일** | 카드는 진행률을 읽지도 쓰지도 않는다 |
| PiP 압축 뷰 | 로그 카드만 숨김 | **동일 규칙 + 「지금」 카드는 보인다** | 설계 결정 7 |
| `file://` 로 열기 | 포커스 시 리로드 | **동일 + 경과 시간이 30초마다 갱신된다** | 설계 결정 6 |

---

## 영향 범위

### 수정 파일 (3개)

| 파일 | 수정 내용 | 이유 |
|------|----------|------|
| `commands/dashboard.md` | ① 「동적 7 셀렉터」 표의 `#dz-step-{n}` **행 1개 수정**(치환 대상에 `data-started-at` 추가, 행 수 7 유지) ② 정적 요소 표 4행 추가 ③ **불변식 7 신설** ④ 폴링 동기화 계약 1행 추가 ⑤ `init` 6단계의 `<li>` 형태를 1번/그 외 두 줄로 명시 ⑥ `step` 1단계에 `data-started-at` 규칙 표 1개 ⑦ 템플릿: 헤더 주석 맵 5줄 · `<style>` 6줄 · `<body>` 4줄 · `<script>` 상수 2개 + 함수 5개 + 호출 3곳 | 이 커맨드가 유일한 실행 주체다. 템플릿·절차·규약이 전부 이 한 파일에 있다 |
| `tests/run.sh` | T22 에 하위 검증 **T22-59 ~ T22-67** 추가. 선행 주석(L998)·`test_desc`(L1002)의 `T22-1~T22-58` → `T22-1~T22-67` | 이 저장소의 회귀 방지 수단은 grep 기반 문서 정합성 테스트뿐이다 |
| `README.md` | L120 줄 수 `1113` → 실제 `wc -l` 값, L139~145 설명 문단에 **1문장** | 줄 수는 사실이어야 하고, 화면에 새 카드가 나타나는 것은 사용자 가시 변화다 |

### 미영향 (전수 확인)

| 대상 | 확인 근거 | 결과 |
|------|----------|------|
| **불변식 1** (`#dz-step-*` ↔ `#dz-cell-*` 비공존) | 카드는 두 요소 중 무엇도 만들지 않는다. `dz-now-` 는 독립 네임스페이스이고, 카드는 `#dz-steps` 를 **읽기만** 한다 | 무영향 |
| **불변식 2** (`<li>`·`<td>` 한 줄에 하나) | `data-started-at` 은 기존 `<li>` **같은 줄 안의 속성**이다. 줄 수·줄 경계 불변 | 유지 |
| **불변식 3** (`.step-detail` 줄바꿈 금지) | 속성값은 `2026-08-07 09:20` 고정 폭 문자열. 줄바꿈 없음 | 유지 |
| **불변식 4** (`#dz-log-card` 를 스크립트가 참조 안 함) | 새 스크립트는 `dz-now-*`·`#dz-steps`·`#dz-updated` 만 참조한다 | 유지 |
| **불변식 5** (`<li id="dz-impl-…">` 한 줄) | impl 자산을 건드리지 않는다 | 유지 |
| **불변식 6** (세부 작업이 매크로 진행률 불변) | `renderNowCard()` 는 `#dz-progress-bar`·`#dz-progress-pct` 를 **읽지도 쓰지도 않는다** | 유지 |
| 동적 셀렉터 **개수 7** | 새 셀렉터는 전부 **정적 요소 표**로 간다(절차가 치환하지 않으므로). 기존 표는 `#dz-step-{n}` 행의 「치환 대상」 칸에 속성 하나가 늘 뿐 | **7 유지** (T22-2 무영향) |
| `step` 0단계 "결과는 항상 3줄" | grep 패턴·대상 요소 수 불변. `data-started-at` 은 이미 매칭되는 그 줄 안에 있다 | 유지 |
| `step` 2단계 전이(±1) 산술 | `data-started-at` 각인 판정이 **같은 grep 결과 줄의 이전 상태**를 쓴다. 새 Bash 호출 0회 | 유지 |
| 감사용 `grep -c 'dz-step-.*class="done"'` | 속성을 `class` **뒤**에 붙이므로 `dz-step-.*class="done"` 매칭에 영향 없다. `dz-now-*` 줄에 `dz-step-` 문자열이 없다 | 계수 불변 |
| `log` 절차의 앵커 `grep -n 'id="dz-log"'` | 새 id 4종에 `dz-log` 가 없다 | 앵커 유일성 유지 |
| `syncVisualization` (`#dz-steps` outerHTML) | `data-started-at` 은 HTML 의 일부라 자동으로 함께 옮겨온다 | 정상 동작 |
| `syncImplCard` · `syncLog` · `syncText` · `syncProgressBar` | 한 글자도 고치지 않는다. `apply()` 에 호출 **1줄만 추가** | 계속 통과 (T22-43·51·53) |
| `resizePipToFit()` | `apply()` **맨 끝** 위치를 유지한다. 카드가 나타나/사라져도 높이 자동 반영 | 계속 통과 (T22-47) |
| `sessionTabsChanged(fresh)` | 카드 안에 `input[name="dzs"]` 이 없다 | 정상 동작 |
| T22-37 (pip 버튼이 `.wrap` 바깥) | `id="dz-updated"` 를 새로 만들지 않는다(현행 1회). 카드는 `#dz-updated` **앞**에 들어간다 | 계속 통과 |
| T22-38 (`[id="dz-` 금지) | 스크립트는 `getElementById('dz-now-…')` 만 쓴다. 대괄호 속성 셀렉터 0개 | 계속 통과 |
| T22-27 (`:root` 완전 일치) | 새 색 토큰 없음. `--blue`·`--navy`·`--muted` 재사용 | 계속 통과 |
| T22-24 (`dz-step-{n}` 패턴) | `init` 의 `wait` 용 `<li>` 형태에 `dz-step-{n}` 이 그대로 남는다 | 계속 통과 |
| T22-46 (`step <n> … ["상세"]` 규약) | 호출 규약 줄을 **한 글자도 바꾸지 않는다** | 계속 통과 |
| T23 전체 (설치·on/off 문서) | `argument-hint` 를 바꾸지 않는다. README 에 `settings.local.json` 을 추가로 쓰지 않는다 | 계속 통과 |
| `install.sh` 의 `COMMANDS_FILE_COUNT` | 새 커맨드 파일 없음 | 변경 불필요 |
| 프로젝트·전역 `CLAUDE.md` | 트리거 규약이 바뀌지 않는다(호출 형태 동일) | **수정하지 않는다** |

### 손대지 않는 것 (발견했지만 이번 요청과 무관)

- `commands/dashboard.md` L778 의 `~/Desktop/dashboard.html` 원본 경로 언급. 네 라운드 연속으로
  "언급만 하고 지우지 않는다"로 처리됐다. 이번에도 동일.
- `init` 가드의 알려진 한계("새 작업"과 "재개"를 구분하지 못한다).
- `docs/images/dashboard-sample.png` 는 카드가 없던 시점의 스크린샷이 된다 →
  **재촬영은 이번 범위 밖**이며, 승인 항목 6에서 사용자에게 확인한다.

---

## 필독 파일 (구현 착수 전)

| 우선순위 | 파일 | 범위 | 이유 |
|---------|------|------|------|
| P0 | `commands/dashboard.md` | L74~110 (동적 7 셀렉터 + 불변식 1~4) · L189~228 (정적 요소 + 폴링 계약 + grep 유일성) | 무엇을 건드리면 안 되는지의 근거. **행 수 7 유지의 정확한 위치** |
| P0 | `commands/dashboard.md` | L454~510 (`step` 절차) | `data-started-at` 규칙을 끼워 넣을 자리. 전이 산술의 정확한 문장 |
| P0 | `commands/dashboard.md` | L397~408 (`init` 6단계 `<li>` 형태) | 두 줄로 나눠 쓸 대상 |
| P0 | `commands/dashboard.md` | L963~1000 (스크립트 상단 + **`if(!isServed){…return;}`**) | **설계 결정 6의 함정.** 렌더러를 이 분기 뒤에 두면 `file://` 에서 죽는다 |
| P0 | `commands/dashboard.md` | L1030~1048 (`apply()`) | `renderNowCard()` 호출을 넣을 정확한 위치(`resizePipToFit()` **앞**) |
| P0 | `tests/run.sh` | L1416~1525 (T22-48~58 + 함수 말미) | 새 하위 검증을 붙일 자리와 역방향 assertion 문체 |
| P1 | `git show a6966aa -- commands/dashboard.md` | 전문 | **되살리지 말아야 할 것의 목록.** 특히 삭제된 `step` 인자 3개 |
| P1 | `docs/prps/dashboard-impl-substeps.md` | 설계 결정 3·5, 테스트 계획 | `:has()` 숨김·sync 추가·역방향 테스트의 형판 |
| P2 | `README.md` | L110~150 | 커맨드 표와 설명 문단의 문체(48e47d0 에서 축약됨 — **문장을 늘리지 않는다**) |

### 외부 조사

**필요 없음.** 새로 쓰는 브라우저 기능은 없다.

| 주제 | 근거 | 핵심 |
|------|------|------|
| `:has()` | 이미 템플릿에서 사용 중(`#dz-impl-card:not(:has(…))`) | 같은 형태를 한 번 더 쓴다. 실패 모드는 "빈 카드가 보인다" 뿐 |
| `Date` 문자열 파싱 | ECMA-262 — **ISO 8601 이 아닌 문자열의 파싱은 구현 정의**다 | 그래서 `new Date(문자열)` 을 **쓰지 않는다.** 정규식으로 5개 필드를 뽑아 `new Date(y, m-1, d, hh, mm)` 로 만든다(설계 결정 2) |
| 백그라운드 탭 타이머 스로틀링 | 숨은 탭의 `setInterval` 은 최대 1분으로 늘어난다 | 분 단위 표시라 무해하다. 게다가 `visibilitychange`·`focus`·PiP `pointerenter` 에서 즉시 재렌더된다 |

---

## 데이터 모델

### 개념 모델

```
NowView                        # 세션당 0개 또는 1개. 전적으로 파생되는 표시 전용 뷰
  phase      : Phase | null    # #dz-steps 의 첫 li.active. null 이면 카드가 CSS 로 숨는다
  next       : Phase | null    # phase 의 다음 형제 li. 없으면 다음 단계 줄이 비고 CSS 가 숨긴다
  startedAt  : Date | null     # phase 의 data-started-at 파싱 결과. null 이면 경과 시간을 비운다
  updatedAt  : Date | null     # #dz-updated 텍스트 파싱 결과. null 이면 "마지막 기록"을 비운다
Phase
  number : string              # li > .num 텍스트
  name   : string              # li 의 직계 텍스트 노드만 이어붙인 값 (자식 span 제외)
```

**이 뷰의 입력은 두 가지뿐이다**: `#dz-steps` 서브트리와 `#dz-updated` 텍스트. 그 밖의 어떤
소스도 없고, 어떤 절차도 이 카드에 직접 쓰지 않는다.

### 이 카드가 보여주는 것과 그 정보의 출처

| 표시 값 | 출처 | 새 정보인가 |
|--------|------|-----------|
| `3. 구현` | `#dz-steps` 의 첫 `li.active` | 파생 (맥락 제공용) |
| **`42분 경과`** | `data-started-at` + 브라우저 현재 시각 | **신규.** 정적 HTML 로 표현 불가 |
| **`마지막 기록 6분 전`** | `#dz-updated` 텍스트 + 브라우저 현재 시각 | **신규.** 절대 시각을 상대 시각으로 바꾼 값 = 정체 감지 |
| `다음 → 4. 검수` | `li.active` 의 다음 형제 | 파생 (맥락 제공용) |

> **정직성 경계**: `42분 경과` 는 "그 단계가 42분째 실제로 작업 중"이 아니라 **"오케스트레이터가
> 그 단계를 `active` 로 표시한 지 42분 지났다"**는 뜻이다. `dashboard-impl-substeps.md` 확정 사항 2와
> 같은 성질의 한계이며, `마지막 기록 N분 전`이 그 한계를 **화면에서 즉시 보정한다** — 경과가 42분인데
> 마지막 기록이 40분 전이면 세션이 멈춰 있다는 뜻이다. 이 두 숫자를 **같은 줄에 나란히 두는 것이
> 설계 의도**다(설계 결정 5).

### 셀렉터 — 동적 표는 **행 수 7 유지**, 한 행만 수정

기존 표에서 아래 **한 행만** 바뀐다(행이 늘지 않는다).

| 셀렉터 | 치환 대상 | 값 |
|--------|----------|-----|
| `#dz-step-{n}` **(그룹 1개)** | `class` 속성 + **`data-started-at` 속성** + 자식 `.chip` 텍스트 + 자식 `.step-detail` 텍스트 | `done`\|`active`\|`wait` / **`YYYY-MM-DD HH:MM`(active 전이 시에만 각인)** / `완료`\|`진행중`\|`대기` / 한 줄 상세 |

**정적 요소 표에 4행 추가** (`init`/`step`/`log`/`impl` 이 절대 치환하지 않고, **폴링도 치환하지
않는** 요소. 다만 `#dz-pip-btn` 과 달리 `.wrap` **안**에 있어 PiP 창으로 함께 이동한다):

| 요소 | 역할 |
|------|------|
| `#dz-now-card` | 「지금」 카드 `<div>`. 템플릿에 **항상** 존재하며, 진행중 단계가 없으면 CSS 가 통째로 숨긴다. DOM 에서 제거하지 않는다 |
| `#dz-now-phase` | 현재 단계 `번호. 이름`. **스크립트만** 쓴다 |
| `#dz-now-elapsed` | `42분 경과 · 마지막 기록 6분 전`. **스크립트만** 쓴다 |
| `#dz-now-next` | `다음 → 4. 검수`. **스크립트만** 쓴다. 비면 `:empty` 가 그 줄을 숨긴다 |

### 불변식 추가 (기존 1~6에 이어)

7. **「지금」 카드는 파생 뷰다 — `init`/`step`/`log`/`impl` 은 카드 안의 어떤 요소도 치환하지 않고,
   폴링도 카드를 치환하지 않는다.** 카드의 입력은 `#dz-steps` 의 `li.active`(와 그
   `data-started-at`) 및 `#dz-updated` 텍스트뿐이며, 그리는 주체는 `renderNowCard()` 하나다.
   **카드에 직접 값을 쓰는 경로를 만드는 순간 `step` 호출 규약에 인자가 붙고**(커밋 `a6966aa` 가
   제거한 바로 그 구조), 같은 정보의 출처가 둘로 갈라져 어느 쪽이 정답인지 알 수 없게 된다.

### 폴링 동기화 계약 — 1행 추가

| 대상 | 동기화 연산 | 근거 |
|------|------------|------|
| `#dz-now-card` (와 그 자식 전부) | **치환하지 않는다.** 대신 `apply()` 말미(`resizePipToFit()` **직전**)에 `renderNowCard()` 를 호출한다 | 카드 내용은 `#dz-steps`·`#dz-updated` **파생**이다. 파일에서 카드 HTML 을 가져와 대입하면 (a) 파일이 쓰인 시점의 낡은 경과 시간이 잠깐 들어왔다가 30초 틱이 덮어써 값이 깜빡이고, (b) 같은 값을 만드는 경로가 둘이 된다(불변식 7). `#dz-impl-card` 를 `outerHTML` 로 통째 교체하는 것과 **정반대 판단이며 그 이유는 파생 여부 하나**다 |

---

## 인터페이스

### 호출 규약 — **한 글자도 바뀌지 않는다**

```
/dashboard init "<제목>" "<단계1|단계2|...>"
/dashboard init "<제목>" "<그룹A:단계1,단계2|그룹B:단계1,단계2>"
/dashboard step <n> <done|active|wait> ["상세"]
/dashboard step <g>.<p> <done|active|wait>
/dashboard impl set "<작업1|작업2|...>"
/dashboard impl <k> <done|active|wait> ["상세"]
/dashboard log <impl|pass|fail|commit> "<한 줄 요약>" ["상세"] [--round N]
/dashboard serve [포트] | serve stop
/dashboard on | off
```

`argument-hint` 도 그대로다. **이 절의 무변경 자체가 이번 라운드의 핵심 성과**이며, T22-61 이
역방향 assertion 으로 이를 고정한다.

### `init` 6단계 — 선형 분기의 `<li>` 형태를 두 줄로 명시

기존 한 줄짜리 템플릿(`class="{active|wait}"`)을 **1번 단계용과 그 외용 두 줄**로 나눈다.
조건부 속성을 산문으로 설명하는 것보다 두 형태를 그대로 보여주는 편이 지시문으로서 결정적이다.

```html
<li id="dz-step-1" class="active" data-started-at="{YYYY-MM-DD HH:MM}"><span class="num">1</span>{단계명}<span class="chip">진행중</span><span class="step-detail"></span></li>
<li id="dz-step-{n}" class="wait"><span class="num">{n}</span>{단계명}<span class="chip">대기</span><span class="step-detail"></span></li>
```

- `{YYYY-MM-DD HH:MM}` 은 8단계에서 `#dz-updated` 에 쓰는 것과 **같은 문자열**이다. 새로 구할 값이 없다.
- **그룹 2개 이상(매트릭스) 분기는 한 글자도 바뀌지 않는다** — `data-state` 에 시각을 붙이지 않는다.

### `step` 1단계 — `data-started-at` 규칙 표 1개 추가

기존 「`.step-detail` 갱신 규칙 (선형 모드 전용)」 표 **바로 뒤**에 넣는다.

```markdown
**`data-started-at` 각인 규칙 (선형 모드 전용, 인자 없음)**

| 전이 | 동작 |
|------|------|
| 이전 상태 ≠ `active` **이고** 새 상태 = `active` | 같은 Edit 안에서 `class` 뒤에 `data-started-at="{YYYY-MM-DD HH:MM}"` 를 현재 시각으로 넣는다(이미 있으면 값만 바꾼다) |
| 그 외 모든 전이 | **건드리지 않는다.** 있으면 그대로 두고, 없으면 없는 대로 둔다 |

- **이전 상태는 0단계 grep 결과 줄에 그대로 적혀 있다** — 진행률 전이(±1) 산술과 **완전히 같은
  출처**를 한 번 더 읽을 뿐이다. 새 Bash 호출도, 새 Edit 도, 새 인자도 없다.
- 형식은 `#dz-updated` 와 **글자 하나까지 동일**하다(`2026-08-07 09:20`). 3단계에서 어차피 만드는
  문자열이라 오케스트레이터가 새로 배울 것이 없다.
- **이미 `active` 인 단계를 다시 `active` 로 부를 때(상세만 갱신하는 경우) 시각을 새로 찍지
  않는다.** 찍으면 경과 시간이 0으로 되돌아가 이 기능의 유일한 새 정보가 파괴된다.
- **매트릭스 모드(`<g>.<p>`)에서는 각인하지 않는다.** `.step-detail` 미지원과 같은 경계다
  (설계 결정 3). 보고도 하지 않는다 — 애초에 사용자가 요청한 동작이 아니기 때문이다.
```

### 템플릿 `<style>` — 6줄 추가 (기존 규칙 수정 0줄)

`.step-detail:empty{display:none}`(현행 L882) **바로 뒤**, `#dz-impl-card:not(:has(…))` **앞**에 넣는다
— "내용이 비면 CSS 가 숨긴다" 계열 규칙끼리 붙여 두는 기존 배치를 따른다.

```css
  .now-line{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;row-gap:3px}
  .now-label{font-size:11px;font-weight:800;letter-spacing:.3px;color:var(--muted);flex:none}
  #dz-now-phase{font-size:16px;font-weight:700;color:var(--navy)}
  #dz-now-elapsed{margin-left:auto;font-size:12px;font-weight:700;color:var(--blue);flex:none}
  #dz-now-elapsed:empty{display:none}
  .wrap:not(:has(#dz-steps li.active)) #dz-now-card{display:none}
```

- **새 색 토큰 0개** — `--muted`·`--navy`·`--blue` 재사용. `:root` 줄을 건드리지 않는다(T22-27).
- **`#dz-now-card` 자체에는 어떤 규칙도 주지 않는다.** `.card` 골격을 그대로 쓰고, 숨김 규칙
  하나만 이 id 를 대상으로 한다. 이렇게 해야 `display:flex` 같은 기본값과 `display:none` 이
  특이도를 다투는 상황이 **아예 생기지 않는다**(설계 결정 8).
- **다음 단계 줄은 기존 `.step-detail` 을 재사용**한다 — `.now-line` 이 `flex-wrap` 컨테이너이므로
  `flex-basis:100%`·`margin-left:38px`·말줄임·`:empty{display:none}` 이 설계 그대로 동작한다.
  `body.dz-pip ol.steps li:not(.active) .step-detail` 규칙은 `ol.steps li` 로 스코프되어 있어
  이 카드에 닿지 않는다(확인 완료).

### 템플릿 `<body>` — 4줄 추가

첫 번째 카드(제목·진행률·단계 목록)와 `#dz-impl-card` **사이**에 넣는다.

```html
  <div class="card" id="dz-now-card">
    <div class="now-line"><span class="now-label">지금</span><span id="dz-now-phase"></span><span id="dz-now-elapsed"></span></div>
    <div class="step-detail" id="dz-now-next"></div>
  </div>
```

- 세 요소 모두 **내용 없이** 시작한다. `<span …></span>` 안에 **공백조차 넣지 않는다**
  (`:empty` 매칭이 풀린다 — `dashboard-impl-substeps.md` 설계 결정 3의 교훈).
- 배치 근거: 단계 목록의 **요약**이므로 목록 바로 아래가 자연스럽고, PiP 압축 뷰에서
  `제목 → 진행률 → 단계 목록 → 지금 → 구현 세부` 순으로 읽힌다. `#dz-updated` **앞**이므로
  T22-37(pip 버튼 위치 판정)에 영향이 없다.

### 템플릿 `<script>` — 상수 2개 + 함수 5개 + 호출 3곳

**상수** (기존 상수 블록 끝에):

```js
  var NOW_TICK_MS = 30000;              // 「지금」 카드 경과 시간 갱신 주기
  var MINUTES_PER_HOUR = 60;
```

**함수** — `setHint` 정의 **바로 뒤**, `if(!isServed)` 분기 **앞**에 둔다(설계 결정 6):

```js
  // ── 「지금」 카드: #dz-steps 와 #dz-updated 에서 파생되는 표시 전용 뷰 (불변식 7) ──
  var nowPhase = document.getElementById('dz-now-phase');
  var nowElapsed = document.getElementById('dz-now-elapsed');
  var nowNext = document.getElementById('dz-now-next');

  // new Date(문자열) 은 ISO 8601 이 아닌 형식에서 파싱 결과가 구현 정의다 — 필드를 직접 뽑는다.
  function parseStamp(text){
    var f = /(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(text || '');
    return f ? new Date(+f[1], +f[2]-1, +f[3], +f[4], +f[5]) : null;
  }
  function formatDuration(from, now){
    var minutes = Math.floor((now - from) / 60000);
    if(!isFinite(minutes) || minutes < 0) return '';
    return minutes < MINUTES_PER_HOUR ? minutes + '분'
      : Math.floor(minutes / MINUTES_PER_HOUR) + '시간 ' + (minutes % MINUTES_PER_HOUR) + '분';
  }
  function phaseLabel(item){
    if(!item) return '';
    var number = item.querySelector('.num'), name = '';
    // 자식 span(.num/.chip/.step-detail)을 제외한 직계 텍스트만이 단계명이다.
    Array.prototype.forEach.call(item.childNodes, function(node){
      if(node.nodeType === 3) name += node.textContent;
    });
    return (number ? number.textContent + '. ' : '') + name.trim();
  }
  function elapsedLabel(active, now){
    var parts = [];
    var startedAt = parseStamp(active.getAttribute('data-started-at'));
    var updatedAt = parseStamp(wrap.querySelector('#dz-updated').textContent);
    if(startedAt) parts.push(formatDuration(startedAt, now) + ' 경과');
    if(updatedAt) parts.push('마지막 기록 ' + formatDuration(updatedAt, now) + ' 전');
    return parts.join(' · ');
  }
  function renderNowCard(){
    // 매트릭스 세션이거나 진행중 단계가 없으면 그릴 것이 없다 — 카드는 CSS 가 숨긴다.
    var active = wrap.querySelector('#dz-steps li.active');
    if(!active) return;
    var now = Date.now();
    nowPhase.textContent = phaseLabel(active);
    nowElapsed.textContent = elapsedLabel(active, now);
    nowNext.textContent = active.nextElementSibling
      ? '다음 → ' + phaseLabel(active.nextElementSibling) : '';
  }
  renderNowCard();
  setInterval(renderNowCard, NOW_TICK_MS);
```

**호출 3곳**

| 위치 | 호출 | 이유 |
|------|------|------|
| 정의 직후 (조기 반환 **앞**) | `renderNowCard();` | 첫 그리기. `file://`·미지원 브라우저에서도 실행돼야 한다 |
| 정의 직후 (조기 반환 **앞**) | `setInterval(renderNowCard, NOW_TICK_MS);` | 30초 틱. **`file://` 경로에서도 시계가 살아 있는 유일한 이유** |
| `apply()` 안, `resizePipToFit()` **직전** | `renderNowCard();` | 폴링으로 `#dz-steps` 가 갈아끼워진 직후 재파생. 그 뒤에 높이를 재야 한다 |

```js
    syncProgressBar(fresh); syncVisualization(fresh); syncImplCard(fresh); syncLog(fresh);
    renderNowCard();
    resizePipToFit();
```

### 템플릿 헤더 주석 맵 — 1줄 수정 + 4줄 추가

동적 항목의 `#dz-step-{n}` 설명에 한 줄 덧붙인다:

```
                          + data-started-at 속성(그 단계가 active 로 전이한 시각. 선형 모드 전용)
```

정적 목록에 추가:

```
  #dz-now-card               : 「지금」 카드 div. 안의 세 요소는 전부 스크립트가 그린다 —
                               init/step/log 도, 폴링도 이 카드를 치환하지 않는다(불변식 7).
                               진행중 단계가 없거나 매트릭스 세션이면 CSS 가 통째로 숨긴다
```

---

## 설계 결정과 근거

### 1. 경과 시간의 트리거는 **상태 전이**다 — 인자가 아니다

이번 설계의 전부다. `step <n> active` 라는 호출은 그 자체로 "지금 이 단계가 시작됐다"는 사건이고,
호출자는 그 순간의 시각을 **이미 알고 있다**(3단계에서 `#dz-updated` 에 쓴다). 따라서 시각은
**받아 적는 값이 아니라 관측되는 값**이다.

| 후보 | 판정 |
|------|------|
| `step <n> active ["상세"] ["착수 시각"]` | **기각.** a6966aa 가 제거한 구조의 재발. 호출자가 매번 인자를 하나 더 만들어야 하고, 빠뜨리면 조용히 낡은 값이 남는다 |
| 별도 하위 명령 `clock <n>` | **기각.** 호출이 2배가 된다. 잊으면 시계가 멈춘다 |
| 스크립트가 `class="active"` 변화를 `MutationObserver` 로 감지해 스스로 각인 | **기각.** 시각이 **브라우저를 연 시점**에 종속된다. 대시보드를 나중에 열면 전부 "0분 경과"가 된다. 게다가 값을 파일에 되쓸 수 없어 새로고침마다 리셋된다 |
| **`step` 1단계의 Edit 에 속성 하나를 얹는다** | **채택.** Edit 횟수 불변, Bash 호출 불변, 인자 0개. 판정 근거(이전 상태)는 이미 읽은 grep 결과 줄에 있다 |

### 2. 타임스탬프 형식을 `#dz-updated` 와 **동일**하게 한다 (ISO 8601 아님)

삭제된 옛 구현은 `data-started-at="2026-08-04T17:02:00+09:00"` 과 `new Date(el.dataset.startedAt)` 를
썼다. 두 가지가 나쁘다.

- 오케스트레이터가 **초·타임존까지 있는 새 형식**을 하나 더 만들어야 한다. 이 커맨드는 이미
  `YYYY-MM-DD HH:MM`(`#dz-updated`)과 `HH:MM`(로그 `.time`) 두 형식을 쓰고 있는데 세 번째가 는다.
- 파싱이 실패하면 옛 코드는 **`NaN분 경과`** 를 화면에 그렸다(가드 없음). 실제 결함이다.

**채택**: `YYYY-MM-DD HH:MM` — `#dz-updated` 와 글자 하나까지 같다. 스크립트는 정규식으로 5개
필드를 뽑아 `new Date(y, m-1, d, hh, mm)` 로 만든다. 부수 효과 셋: (a) 형식이 하나 줄고,
(b) 엔진별 파싱 편차가 사라지고, (c) **같은 정규식이 `#dz-updated` 에도 그대로 통해** "마지막 기록
N분 전"이 공짜로 따라온다(설계 결정 5). 파싱 실패 시에는 **빈 문자열**을 반환해 `:empty` 가 그
요소를 숨긴다 — `NaN` 을 그리지 않는다.

### 3. 매트릭스 모드에서는 카드를 **숨긴다** — 그리고 그 비용은 코드 0줄이다

매트릭스 세션은 그룹마다 독립적으로 진행되고 **여러 칸이 동시에 `active` 일 수 있다.**
"현재 단계"와 "다음 단계"라는 단수 개념이 성립하지 않는다.

| 후보 | 판정 |
|------|------|
| 그룹마다 한 줄씩 다중 표시 | **기각.** 그것은 이미 매트릭스 표가 하는 일이다. 표를 텍스트로 한 번 더 쓰는 순수 중복이며(확정 사항 2 위반), 행 수만큼 카드가 길어져 PiP 에서 오히려 손해다 |
| 첫 번째 active 그룹만 표시 | **기각.** "첫 번째"에 아무 의미가 없다. 보는 사람이 다른 그룹이 멈춘 줄로 오해한다 — 틀린 정보를 그리는 최악의 선택 |
| 매트릭스에서도 뭔가 보여주려 `data-started-at` 을 `<td>` 에도 각인 | **기각.** `step <g>.<p>` 절차가 커지고, 소비자가 없다(YAGNI) |
| **숨긴다** | **채택.** CSS 셀렉터가 `#dz-steps li.active` 를 대상으로 하므로 **매트릭스 세션에는 `#dz-steps` 가 아예 없어** 조건이 자동으로 성립한다(불변식 1 덕분이다). 스크립트의 `if(!active) return;` 도 같은 이유로 매트릭스를 자연히 걸러낸다 |

**분기 코드가 한 줄도 없다는 점이 이 결정의 핵심 근거다.** 불변식 1(한 파일에 `#dz-step-*` 과
`#dz-cell-*` 이 공존하지 않는다)이 이미 보장한 배타성을 그대로 활용한다.

### 4. `.step-detail` 을 카드에 **재노출하지 않는다**

사용자 제안 중 하나였고, 검토 결과 **기각**한다. 근거 셋:

1. **인접 중복이다.** 카드 바로 위 활성 `<li>` 에 같은 텍스트가 이미 보인다. 두 요소 사이 거리가
   50픽셀도 안 된다.
2. **PiP 압축 뷰에서 이미 해결된 문제다.** `body.dz-pip ol.steps li:not(.active) .step-detail{display:none}`
   덕분에 좁은 창에서는 **활성 단계의 상세만** 보인다 — 재노출이 해결할 문제가 남아 있지 않다.
3. **확정 사항 2 위반.** 사용자가 거부한 "이미 보이는 정보의 재진열"의 교과서적 사례다.

담당 에이전트·모델 표기는 `.step-detail` 에 자유 텍스트로 적으면 된다
(예: `step 3 active "implementer(sonnet) 디스패치 중"`). **이를 위한 필드를 새로 만드는 것이
a6966aa 가 제거한 `#dz-current-meta` 그 자체**이므로 다시 만들지 않는다.

카드가 차지하는 세 번째 줄은 **다음 단계**가 쓴다 — 파생이지만 `.step-detail` 과 달리
"이 뒤에 무엇이 오는가"를 목록에서 눈으로 훑지 않아도 되게 해 준다.

### 5. 「마지막 기록 N분 전」을 경과 시간 **옆에** 둔다

경과 시간만 있으면 위험한 오독이 가능하다: `42분 경과` 를 보고 "지금 42분째 작업 중"이라고 읽는데,
실제로는 오케스트레이터가 42분 전에 표시만 해 두고 세션이 죽었을 수도 있다
(`dashboard-impl-substeps.md` 리스크 1과 같은 성질).

두 숫자를 나란히 두면 판독이 즉시 가능해진다.

| 화면 | 읽는 법 |
|------|--------|
| `42분 경과 · 마지막 기록 2분 전` | 정상. 오래 걸리는 단계를 진행 중 |
| `42분 경과 · 마지막 기록 41분 전` | **세션이 멈췄거나 대기 중.** 확인이 필요하다 |

비용은 **함수 재사용 2줄**이다(같은 `parseStamp`·`formatDuration`). 소스는 `#dz-updated` 로 이미
존재하고 모든 하위 명령이 갱신한다 — 절차 변경 0. **이 항목만 따로 뺄 수 있다**(승인 항목 3).

### 6. 렌더러를 `if(!isServed)` 조기 반환 **앞**에 둔다

스크립트는 IIFE 안에서 **세 번 조기 반환**한다: `!isServed`(file://), `!hasPipSupport`, 그리고
`requestWindow` 실패 경로. 렌더러를 잘못된 위치에 두면 **`file://` 로 여는 사용자에게 카드가
영원히 빈 채로 보인다** — 그리고 `http://` 로 테스트하면 멀쩡히 동작해서 **알아채기 가장 어려운
형태의 버그**가 된다(`dashboard-impl-substeps.md` 설계 결정 5가 겪은 것과 같은 함정).

정의와 최초 호출, `setInterval` 을 **모두 `if(!isServed)` 앞**에 둔다. 그 결과 `file://` 모드에서도
30초마다 경과 시간이 갱신되며, 이는 **부가 효과가 아니라 요구사항**이다(file:// 는 포커스 시에만
리로드되므로 창을 띄워 두면 시각이 멈춘다). T22-64 가 줄 번호 비교로 이 배치를 강제한다
(T22-37 이 pip 버튼 위치를 강제하는 것과 같은 방식).

### 7. PiP 압축 뷰에서 카드를 **숨기지 않는다**

로그 카드는 숨기는데 이건 왜 안 숨기나 — **곁눈질 화면이 원하는 정보가 정확히 이것**이기
때문이다. 경과 시간은 전체 화면보다 좁은 창에서 더 값지고, 카드 자체가 두 줄짜리다.
`dashboard-impl-substeps.md` 설계 결정 6과 같은 판단이며, T22-67 이 역방향 assertion 으로
숨김 규칙의 몰래 추가를 막는다.

### 8. 숨김을 CSS 로만 하고, `#dz-now-card` 에 기본 `display` 를 주지 않는다

| 후보 | 판정 |
|------|------|
| 스크립트가 `card.hidden = !active` | **기각.** "CSS 로 되는 건 CSS 로"(`session-dashboard.md` 설계 결정 5). 상태가 스크립트로 새고, 미지원 경로에서 카드가 영구히 사라질 수 있다 |
| `#dz-now-card:has(…)` 로 카드 자신을 조건 삼기 | **기각.** 판정 대상(`#dz-steps`)이 카드 **바깥**이라 성립하지 않는다 |
| `#dz-now-card{display:flex}` + `.wrap:not(:has(…)) #dz-now-card{display:none}` | **기각(위험).** 두 규칙이 특이도를 다투게 된다. 지금은 후자가 이기지만, 누군가 앞 규칙을 `#dz-now-card{…}` 로 손보면 조용히 역전될 수 있다 |
| **`#dz-now-card` 에 규칙을 주지 않고, 레이아웃은 자식 `.now-line` 이 담당** | **채택.** 이 id 를 대상으로 하는 규칙이 **숨김 하나뿐**이라 다툴 상대가 없다. `.card` 골격을 그대로 상속한다 |

### 9. 스코프 아웃과 사유

| 제외 항목 | 사유 |
|-----------|------|
| `step` 의 새 인자 일체 | 확정 사항 1 = a6966aa 의 사유 |
| 담당 에이전트 전용 셀렉터 | `#dz-current-meta` 의 재발. `.step-detail` 로 충분하다 |
| 매트릭스용 카드 변형 | 설계 결정 3. 개념이 성립하지 않고, 숨기는 비용이 0이다 |
| 단계별 소요 시간 이력·ETA | 근거 데이터가 없다. 추정치는 신뢰를 깎는다 |
| 초 단위·1초 틱 | 곁눈질 화면의 소음 |
| `#dz-impl-{k}` 항목별 타이머 | 선행 PRP 비목표에서 이미 기각 |
| 카드에서의 `.step-detail` 재노출 | 설계 결정 4 |

---

## 불변식·grep 유일성 자체 점검

### 불변식 1~6 (기존)

| # | 내용 | 이번 변경의 영향 | 판정 |
|---|------|-----------------|------|
| 1 | `#dz-step-*` 과 `#dz-cell-*` 비공존 | 새 요소는 둘 중 무엇도 만들지 않는다. **오히려 이 불변식에 의존해** 매트릭스 분기를 코드 0줄로 처리한다(설계 결정 3) | **무손상 · 활용** |
| 2 | `<li>`·`<td>` 를 한 줄에 하나씩 | `data-started-at` 은 **기존 줄 안의 속성**이다. `<li>` 를 쪼개지 않는다. `init` 이 형태를 두 줄로 문서화하지만 **생성되는 `<li>` 는 여전히 한 줄에 하나**다 | **무손상** |
| 3 | `.step-detail` 에 줄바꿈 금지 | 속성값은 16자 고정 폭. `.step-detail` 자체를 이번에 쓰지 않는다(카드의 `#dz-now-next` 는 **스크립트가 `textContent` 로만** 쓰므로 파일에 줄바꿈이 들어갈 경로가 없다) | **무손상** |
| 4 | `#dz-log-card` 를 스크립트가 id 로 참조하지 않는다 | 새 스크립트는 `dz-now-*` 3종 + `#dz-steps` + `#dz-updated` 만 참조 | **무손상** |
| 5 | `<li id="dz-impl-…">` 한 줄에 하나 | impl 자산을 전혀 건드리지 않는다 | **무손상** |
| 6 | 세부 작업 변화가 매크로 진행률을 안 바꾼다 | `renderNowCard()` 는 `#dz-progress-bar`·`#dz-progress-pct` 를 **읽지도 쓰지도 않는다.** `step` 2단계 산술도 그대로다 | **무손상** |

### grep 앵커 유일성 (「grep 유일성 불변식」)

| 앵커 | 새 문자열이 걸리는가 | 근거 |
|------|--------------------|------|
| `grep -n 'id="dz-log"'` (`log` 0-a, `init` 1-a) | **아니오** | 새 id 4종에 `dz-log` 부분 문자열이 없다 |
| `grep -n 'id="dz-step-{n}"'` (`step` 0) | **아니오** | `id="dz-now-phase"` 는 `id="dz-step-` 을 포함하지 않는다. `id="` 접두어가 방어한다 |
| `grep -n 'id="dz-progress-bar\|pct"'` (`step` 0) | **아니오** | 무관 |
| `grep -n 'id="dz-impl-…"'` (`impl` 0) | **아니오** | 무관 |
| `grep -c 'dz-step-.*class="done"'` (감사) | **아니오** | `dz-now-phase` 에 `dz-step-` 부분 문자열이 없다(`w-step` ≠ `dz-step-`). 새 속성은 `class` **뒤**라 매칭 형태 불변 |
| `grep -c 'dz-cell-.*data-state="done"'` (감사) | **아니오** | `data-started-at` 은 `data-state` 가 아니다 |
| `grep -c 'dz-impl-[0-9].*class="done"'` (감사) | **아니오** | 무관 |
| `grep -c 'dzs-all'` (`init` 1-d) | **아니오** | 무관 |

### 「스크립트가 `id="…"` 문자열을 만들지 않는다」 규칙

- 새 스크립트는 `document.getElementById('dz-now-phase')` · `wrap.querySelector('#dz-steps li.active')` ·
  `wrap.querySelector('#dz-updated')` 만 쓴다. **대괄호 속성 셀렉터 0개** → T22-38 계속 통과.
- 새 CSS 도 `#dz-steps li.active` · `#dz-now-card` 형태이며 `[id="…"]` 를 쓰지 않는다.

### 동적 셀렉터 개수

**7 유지.** 새 4종은 절차가 치환하지 않으므로 전부 「정적 요소」 표로 간다. `#dz-step-{n}` 행의
「치환 대상」 칸에 속성 하나가 늘 뿐 **행 수는 그대로**다 → T22-2 무영향.

---

## 테스트 계획

### 무엇을 검증할 수 있고 무엇은 못 하는가

이 커맨드에는 실행 코드가 없다(LLM 지시문 + HTML 템플릿). **브라우저 런타임·CSS 렌더·시간 경과는
자동 검증 대상이 아니고**, 템플릿·절차의 문자열 정합성과 자산 비퇴화만 grep 으로 검증한다.
특히 **경과 시간이 실제로 흐르는지는 grep 으로 알 수 없다** → 수동 확인 4~7 이 전담한다.

### `tests/run.sh` — T22 에 하위 검증 추가 (T22-59 ~ T22-67)

새 테스트 함수를 만들지 않는다. `total_tests=22` 를 유지하고 `test_dashboard_template_integrity`
안, **T22-58 바로 뒤**(`log_ok` 앞)에 이어 붙인다. 선행 주석(L998)과 `test_desc`(L1002)의
`T22-1~T22-58` 표기를 `T22-1~T22-67` 로 고친다.

| ID | 검증 | 방법 | 막으려는 회귀 |
|----|------|------|--------------|
| T22-59 | 카드 셀렉터 4종 존재 | `grep -qF` × 4: `id="dz-now-card"` · `id="dz-now-phase"` · `id="dz-now-elapsed"` · `id="dz-now-next"` | 카드 자체의 유실 |
| T22-60 | **자동 숨김 규칙 존재** | `grep -qF '.wrap:not(:has(#dz-steps li.active)) #dz-now-card{display:none}'` | 매트릭스 세션·진행중 없음 상태에서 빈 카드가 노출(설계 결정 3·8 위반) |
| T22-61 | **호출 규약 비대화 방지 (최우선)** | 확장 정규식 `dz-current` 또는 `"현재 위치"` 가 매칭되면 **실패**(현재 baseline 은 둘 다 0회로 실측 확인). 더불어 `grep -qF 'step <n> <done\|active\|wait> ["상세"]'` 로 규약 줄 원형 확인 | **커밋 a6966aa 가 제거한 셀렉터·인자의 부활.** 이 저장소에서 같은 실수를 두 번 하지 않기 위한 핵심 assertion |
| T22-62 | 자동 각인 규칙 문서화 | `grep -qF 'data-started-at'` **및** `grep -q '이전 상태 ≠ \`active\` \*\*이고\*\* 새 상태 = \`active\`'`(문구 고정) | 각인 시점이 흐려져 매 호출마다 시각이 리셋되는 회귀 |
| T22-63 | **파생 뷰 불변식 문구** | `grep -q '「지금」 카드는 파생 뷰다'` | 불변식 7 유실 → 카드에 직접 쓰는 경로가 생기고 인자가 따라 붙는다 |
| T22-64 | **렌더러 배치 (줄 번호 비교)** | `grep -qF 'function renderNowCard(){'` **및** `setInterval(renderNowCard` 의 줄 번호 < `if(!isServed){` 의 줄 번호 | 조기 반환 뒤에 두면 `file://` 에서 시계가 죽는다. `http://` 테스트로는 안 잡힌다(설계 결정 6) |
| T22-65 | **폴링이 카드를 치환하지 않음 (역방향)** | `grep -n 'dz-now-card' \| grep -qE 'outerHTML\|innerHTML'` 가 매칭되면 **실패**. 더불어 `grep -qF 'renderNowCard();'` 로 `apply()` 안 호출 존재 확인 | 파생 뷰를 파일 문자열로도 동기화해 값 출처가 둘로 갈라짐(불변식 7) |
| T22-66 | 매트릭스 방침 문구 | `grep -q '매트릭스 모드(\`<g>.<p>\`)에서는 각인하지 않는다'` | 매트릭스에서 `<td>` 에 각인하는 범용화 유혹 |
| T22-67 | **PiP 미숨김 (역방향)** | `grep -qF 'body.dz-pip #dz-now-card{display:none}'` 가 매칭되면 **실패** | 곁눈질 화면에서 가장 값진 카드를 숨기는 규칙의 몰래 추가(설계 결정 7) |

T22-61 · T22-65 · T22-67 은 **역방향 assertion**(매칭되면 실패)이다 — T22-7·28·35·38·41·42·50·52·58
이 이미 쓰는 패턴이며, 저장소 관례대로 **왜 그 방향인지 한 줄 이유를 주석으로 남긴다.**

참고 구현 (T22-61, 이번 라운드에서 가장 중요한 검증):

```bash
  # T22-61: 호출 규약 비대화 방지 — 커밋 a6966aa 는 "현재 위치/다음 단계" 카드를 위해 step 에
  # 선택 인자 3개를 요구했다가 그 무게 때문에 기능째 제거됐다. 「지금」 카드는 순수 파생 뷰이므로
  # dz-current 계열 셀렉터나 규약상의 위치/다음단계 인자가 다시 나타나면 같은 실패의 재발이다
  # (역방향 assertion).
  if grep -qE 'dz-current|"현재 위치"' "$dashboard_command_file"; then
    record_failure "$test_name" "T22-61: 제거된 dz-current 계열 셀렉터·인자가 부활함"
    return 1
  fi
```

참고 구현 (T22-64, 줄 번호 비교 — T22-37 과 같은 방식):

```bash
  # T22-64: 「지금」 카드 렌더러가 file:// 조기 반환보다 앞에 있어야 한다. 뒤에 있으면
  # file:// 로 연 대시보드에서 경과 시간이 영원히 갱신되지 않는데, http:// 테스트로는
  # 정상으로 보여 발견이 가장 어렵다.
  local render_tick_line early_return_line
  render_tick_line=$(grep -n 'setInterval(renderNowCard' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  early_return_line=$(grep -n 'if(!isServed){' "$dashboard_command_file" | tail -1 | cut -d: -f1)
  if [[ -z "$render_tick_line" || -z "$early_return_line" || "$render_tick_line" -gt "$early_return_line" ]]; then
    record_failure "$test_name" "T22-64: renderNowCard 틱이 file:// 조기 반환 뒤에 있음"
    return 1
  fi
```

### 기존 테스트에 대한 영향 (전수 확인)

| 테스트 | 영향 | 근거 |
|--------|------|------|
| T22-2 (셀렉터 7종) | 계속 통과 | 느슨한 부분일치 grep 이고, 기존 7종을 전부 유지한다 |
| T22-5 (`COMMANDS_FILE_COUNT`) | 계속 통과 | 새 커맨드 파일 없음 |
| T22-24 (선형 자산) | 계속 통과 | `<ol class="steps" id="dz-steps">` 그대로. `dz-step-{n}` 은 `wait` 용 `<li>` 형태에 남는다 |
| T22-26 (감사 계수 명령) | 계속 통과 | 명령 문자열을 바꾸지 않는다 |
| T22-27 (`:root` 완전 일치) | 계속 통과 | 새 색 토큰·리터럴 색 없음 |
| T22-29~34 (PiP 스크립트) | 계속 통과 | 기존 함수를 한 글자도 고치지 않는다. `requestWindow` 호출 수 불변 |
| T22-37 (pip 버튼 위치) | 계속 통과 | `id="dz-updated"` 를 새로 만들지 않는다. 카드는 `.foot` **앞** |
| T22-38 (`[id="dz-` 금지) | 계속 통과 | 대괄호 속성 셀렉터 0개 |
| T22-41 (`id="dz-log"` 템플릿 내 1회) | 계속 통과 | `dz-log` 문자열을 추가하지 않는다 |
| T22-43·47·51·53 (sync·resize 비퇴화) | 계속 통과 | `apply()` 에 **호출 1줄만 추가**하고 `resizePipToFit()` 을 맨 끝에 유지한다 |
| T22-44·45 (`.step-detail` 자산) | 계속 통과 | 재사용만 하고 규칙을 고치지 않는다 |
| T22-46 (`step … ["상세"]` 규약) | 계속 통과 | 규약 줄 무변경 |
| T22-49·58 (impl 카드) | 계속 통과 | impl 자산 무변경 |
| T22-57 / T23-6 (`argument-hint`) | 계속 통과 | frontmatter 무변경 |
| T23-11 (README `settings.local.json` ≤3) | 계속 통과 | 추가 문장에 이 문자열을 쓰지 않는다 |

### 검증 명령

```bash
cd /Users/pascal/works/personal/coding-env
bash tests/run.sh                                          # 기대: 총 22 / 통과 22 / 실패 0
wc -l commands/dashboard.md                                # README L120 의 줄 수를 이 값으로 갱신
grep -c 'id="dz-updated"' commands/dashboard.md            # 1 (T22-37 보호)
grep -cE 'dz-current|"현재 위치"' commands/dashboard.md     # 0 (T22-61 보호)
grep -c '\[id="dz-' commands/dashboard.md                  # 0 (T22-38 보호)
git diff --stat commands/dashboard.md                      # frontmatter·호출 규약 줄이 diff 에 없어야 한다
grep -n 'setInterval(renderNowCard\|if(!isServed){' commands/dashboard.md   # 앞 줄이 더 작아야 한다
```

### 수동 확인 (자동화 불가 — Chrome 실기 + 시간 경과 필요)

| # | 절차 | 합격 기준 |
|---|------|----------|
| 1 | 빈 디렉토리에서 `/dashboard init "테스트" "설계\|승인\|구현\|검수"` 후 `file://` 로 연다 | 「지금」 카드가 보이고 `지금 1. 설계` · `0분 경과 · 마지막 기록 0분 전` · `다음 → 2. 승인` |
| 2 | 매트릭스 세션(`init "…" "A:설계,구현\|B:설계,구현"`)을 새로 만들어 연다 | **카드가 아예 보이지 않는다.** 개발자 도구에서 DOM 에는 존재하고 `display:none` |
| 3 | 1번 상태에서 `step 1 done` · `step 2 active` | `지금 2. 승인` 으로 바뀌고 경과가 `0분 경과` 로 리셋. 다음 → 3. 구현 |
| 4 | 3번 상태로 **2분 이상 방치**(창을 포그라운드로 둔다) | 30초 틱마다 `2분 경과` 로 자동 증가. **새로고침 없이** |
| 5 | 4번 상태에서 `step 2 active "상세만 갱신"` 재호출 | **경과 시간이 리셋되지 않는다**(설계 결정 1의 핵심). 상세만 바뀐다 |
| 6 | 모든 단계를 `done` 으로 만든다 | 카드가 사라진다(`li.active` 없음) |
| 7 | `data-started-at` 을 손으로 `2026-99-99 99:99` 로 망가뜨린다 | `NaN분 경과` 가 아니라 **경과 부분이 비고**, `마지막 기록 N분 전` 만 남는다 |
| 8 | 이 기능 도입 **이전에** 만들어진 대시보드(속성 없음)를 연다 | 카드는 보이되 경과 부분만 비어 있다. 마크업이 깨지지 않는다 |
| 9 | `/dashboard serve` → `http://localhost:8791/…` 로 열고 `step 3 active` | **5초 내** 카드가 3. 구현으로 바뀌고 경과가 리셋된다(폴링 경로) |
| 10 | 9번 상태에서 「플로팅」 진입 | 카드가 PiP 창에 **보이고**, 창 높이가 콘텐츠에 맞는다 |
| 11 | 10번 상태로 1분 이상 방치 후 창에 커서를 올린다 | 경과 시간이 최신값으로 갱신된다(`pointerenter` → `poll` → `apply` → `renderNowCard`) |
| 12 | 플로팅 창을 닫는다 | opener 로 복귀하며 카드가 내용 그대로 보인다 |
| 13 | 유형 필터·세션 탭을 조작한 뒤 폴링 5초 대기 | 선택이 유지된다(카드 렌더가 라디오를 건드리지 않음) |
| 14 | 단계명이 긴 세션(`"아주 긴 단계 이름을 가진 설계 단계\|…"`)으로 확인 | 카드가 두 줄로 자연 줄바꿈되고 경과 시간이 잘리지 않는다 |

---

## 구현 순서

각 단계 뒤에 `bash tests/run.sh` 로 비회귀를 확인한다. **착수 전에 기준선(22/22)을 먼저 기록한다.**

### Task 1 — 데이터 모델·불변식·동기화 계약 문서 갱신
- **ACTION**: 동적 표의 `#dz-step-{n}` **행 1개 수정**, 정적 요소 표 4행, 불변식 7, 폴링 계약 1행.
- **GOTCHA**: **동적 표의 행 수를 7 그대로 유지한다.** 새 셀렉터를 그 표에 넣지 않는다.
- **VALIDATE**: 표의 행 수를 눈으로 확인. `bash tests/run.sh`.

### Task 2 — 템플릿 `<style>` 6줄 추가
- **ACTION**: `.step-detail:empty` 뒤, `#dz-impl-card:not(…)` 앞에 6줄.
- **GOTCHA**: `#dz-now-card` 를 대상으로 하는 규칙은 **숨김 하나뿐**이어야 한다(설계 결정 8).
  `:root` 를 건드리지 않는다.
- **VALIDATE**: `git diff` 로 `:root` 무변경 확인(T22-27).

### Task 3 — 템플릿 마크업 4줄 + 헤더 주석 맵
- **ACTION**: 첫 카드와 `#dz-impl-card` 사이에 카드 4줄. 주석 맵 1줄 수정 + 4줄 추가.
- **GOTCHA**: 세 요소 안에 **공백조차 넣지 않는다**(`:empty` 매칭). `id="dz-updated"` 를 새로
  만들지 않는다(T22-37).
- **VALIDATE**: `grep -c 'id="dz-updated"'` = 1.

### Task 4 — 템플릿 `<script>` 에 렌더러 추가
- **ACTION**: 상수 2개, 함수 5개 + 요소 참조 3개, 최초 호출 + `setInterval`, `apply()` 안 1줄.
- **GOTCHA**: **정의·최초 호출·`setInterval` 을 전부 `if(!isServed){` 앞에 둔다**(설계 결정 6).
  `resizePipToFit()` 은 `apply()` 맨 끝에 그대로 남긴다(T22-47). 기존 sync 함수 5개를 한 글자도
  고치지 않는다(T22-29~34·43·51·53).
- **VALIDATE**: `grep -n 'setInterval(renderNowCard\|if(!isServed){'` 줄 번호 비교.

### Task 5 — `init` 6단계 `<li>` 형태 + `step` 1단계 규칙 표
- **ACTION**: `init` 의 선형 `<li>` 를 1번용/그 외용 두 줄로. `step` 1단계에 각인 규칙 표.
- **GOTCHA**: **호출 규약 절과 `argument-hint` 를 한 글자도 건드리지 않는다**(T22-61·46, T23-6).
  T22-62·63·66 이 고정하는 세 문장을 **문자 그대로** 쓴다. 매트릭스 분기는 무변경.
- **VALIDATE**: `git diff` 에 frontmatter·호출 규약 줄이 없어야 한다.

### Task 6 — `tests/run.sh` 에 T22-59~67 추가
- **ACTION**: T22-58 뒤(`log_ok` 앞)에 9개 하위 검증. 주석·`test_desc` 를 `T22-1~T22-67` 로.
- **MIRROR**: `record_failure "$test_name" "T22-NN: …"` 후 `return 1`. 역방향 3종에 이유 주석.
- **VALIDATE**: `bash tests/run.sh` → 22/22.

### Task 7 — `README.md`
- **ACTION**: L120 줄 수를 `wc -l` 실제 값으로. 설명 문단에 **1문장**.
- **GOTCHA**: 48e47d0 에서 축약한 문단이다 — 문장을 늘리지 않는다. `settings.local.json` 을
  쓰지 않는다(T23-11).
- **VALIDATE**: `bash tests/run.sh`.

### Task 8 — 수동 확인 1~14 수행

---

## 리스크와 대안

### 1. "이 카드는 결국 파생 정보 재진열 아닌가"라는 판정이 다시 내려질 수 있다 — 최대 리스크

**가능성 중 / 영향 상.** 카드가 보여주는 네 값 중 둘(단계명·다음 단계)은 바로 위 목록에서 파생된다.
a6966aa 의 판정("불필요")이 반복될 여지가 있다.
**완화**: (a) 새 정보 **둘**(경과 시간·마지막 기록 이후)이 카드 오른쪽 한 줄에 모여 있고, 둘 다
정적 HTML 로 표현 불가능하다. (b) **호출 비용이 0**이라 "값이 적어도 비용이 없으므로 지워야 할
이유도 없다" — a6966aa 의 진짜 사유는 카드가 아니라 인자였다. (c) 그래도 부족하다고 판단되면
**카드를 없애고 경과 시간만 첫 카드 안 스트립으로 옮기는 축소안**이 준비돼 있다(승인 항목 1).
**기각한 대안**: 단계명·다음 단계를 빼고 경과 시간만 카드에 남긴다 → 맥락 없는 숫자 하나짜리
카드가 되어 더 이상하다.

### 2. `data-started-at` 을 빠뜨리거나 잘못 각인한다

**가능성 중 / 영향 중.** `step` 을 호출하지 않고 상태를 손으로 고치면 시각이 안 찍히고,
이미 `active` 인 단계에 `step … active` 를 다시 불러 시각을 리셋할 수 있다.
**완화**: 각인 조건을 **전이(이전≠active → 새=active)** 로 못 박았고, 이전 상태는 0단계 grep
결과 줄에 그대로 적혀 있어 기억에 의존하지 않는다(진행률 ±1 산술과 같은 구조·같은 출처).
값이 없거나 깨져도 **경과 부분만 비고** 카드·마크업은 멀쩡하다(수동 확인 7·8).
**기각한 대안**: 스크립트가 스스로 각인 → 브라우저를 연 시점에 종속돼 값이 매번 리셋된다.

### 3. 스크립트를 다시 건드리는 라운드다 — 폴링 계약이 퇴화할 수 있다

**가능성 중 / 영향 상.** `apply()` 를 편집하며 `resizePipToFit()` 순서를 바꾸거나 sync 호출을
밀어내면 직전 세 라운드의 성과가 조용히 죽는다. 더 나쁜 경우는 렌더러를 조기 반환 뒤에 두는 것이다
(설계 결정 6) — `http://` 테스트로는 정상으로 보인다.
**완화**: T22-43·47·51·53 이 기존 자산을, **T22-64 가 렌더러 배치를 줄 번호로** 고정한다.
**검수자는 이 지점을 중점 항목으로 본다.**

### 4. 시각 왜곡 — 타임존·시계 오차

**가능성 하 / 영향 하.** `data-started-at` 은 오케스트레이터 머신의 로컬 벽시계이고,
경과 계산은 브라우저의 로컬 시각이다. **같은 머신이므로 일치**한다. 원격 브라우저로 보는
사용 사례는 없다(`serve` 는 `--bind 127.0.0.1` 로 루프백에 못 박혀 있다).
음수 경과(시계 되감김)는 `formatDuration` 이 빈 문자열로 처리한다.
**기각한 대안**: UTC + 오프셋 저장 → 오케스트레이터가 만들어야 할 형식이 하나 늘고, 얻는 것이 없다.

### 5. `.step-detail` 을 다음 단계 줄에 재사용해 결합이 생긴다

**가능성 하 / 영향 하.** `.step-detail` 의 `margin-left:38px`·말줄임 규칙이 바뀌면 카드의 다음
단계 줄도 함께 바뀐다.
**완화**: 두 용도의 요구가 사실상 같다(한 줄, muted, 넘치면 말줄임, 비면 숨김). `dashboard-impl-substeps.md`
설계 결정 2가 `ol.steps` 를 통째로 재사용해 같은 결합을 이미 수용했고, 그 판단이 유지되고 있다.
**기각한 대안**: `.now-next` 규칙을 새로 쓴다 → CSS 3~4줄이 늘고 두 벌이 갈라진다.

### 6. `:has()` 미지원 환경

**가능성 하 / 영향 하.** 실패 모드는 **"매트릭스 세션에서도 카드가 보이고 내용이 비어 있다"** 뿐이다
(스크립트의 `if(!active) return;` 때문에 잘못된 값이 그려지지는 않는다). 데이터도 절차도 안 깨진다.
이 프로젝트는 이미 Chromium 만 지원 대상이다.

### 7. 검토했으나 채택하지 않은 전체 대안

| 대안 | 기각 사유 |
|------|----------|
| **a6966aa 를 `git revert` 로 되살린다** | 제거된 인자 3개까지 함께 돌아온다. 사용자가 명시적으로 배제한 방향 |
| **`step` 에 선택 인자로 시각을 받는다** | 확정 사항 1 정면 위반 |
| **카드 없이 활성 `<li>` 안에 경과 시간 span 을 스크립트가 주입** | 폴링이 `outerHTML` 로 통째 교체하는 서브트리를 스크립트가 함께 변형하게 되어, 소유권이 모호해진다. "다음 단계"를 놓을 자리도 없다. **단, 축소안으로는 유효**(승인 항목 1) |
| **`#dz-updated` 를 "N분 전"으로 바꿔 표시** | 절대 시각이 사라진다. 두 정보(언제 / 얼마나 전)는 성격이 다르고, `#dz-updated` 는 폴링이 `textContent` 로 덮어쓰는 동기화 대상이라 스크립트가 손대면 계약이 충돌한다 |
| **매트릭스 모드에서 그룹별 현재/다음 다중 표시** | 표가 이미 하는 일의 텍스트 복제. 설계 결정 3 |
| **`.step-detail` 을 카드에 재노출** | 인접 중복. 확정 사항 3 · 설계 결정 4 |
| **경과 시간을 초 단위로 표시** | 곁눈질 화면의 소음. 1초 틱은 PiP 창에서 불필요한 재레이아웃을 만든다 |
| **`MutationObserver` 로 상태 변화를 감지해 각인** | 브라우저를 연 시점 종속. 파일에 되쓸 수 없어 새로고침마다 리셋 |

---

## 미해결 질문 (추측하지 않고 남긴다)

1. **카드 제목 문구** — 지금은 `지금` 이라는 라벨 한 단어다. `현재 진행` 또는 카드 제목 줄
   (`.impl-title` 같은 별도 줄)을 원하는지. 라벨 한 단어를 택한 이유는 세로 공간 절약이다.
2. **`마지막 기록 N분 전` 의 문구** — `갱신 N분 전` · `기록 N분 전` 등 대안이 있다.
   `#dz-updated` 의 `갱신:` 과 구별하려고 `마지막 기록` 을 골랐다.
3. **스크린샷 갱신 여부** — `docs/images/dashboard-sample.png` 가 카드 없는 화면이 된다.
   이번에 재촬영할지, 별도 작업으로 미룰지.

---

## 워크플로우 경로 판정

**전체 경로(설계 → 구현 → 검수)가 맞다.**

- **데이터 모델 변경**: `data-started-at` 속성 신설, 정적 셀렉터 4종, 불변식 7, 폴링 계약 1행.
- **파일 3개 이상**: `commands/dashboard.md`, `tests/run.sh`, `README.md`.
- **공개 인터페이스 변경**: **없다**(호출 규약·`argument-hint` 무변경 — 이번 라운드의 성과).
- **새 외부 의존성**: 없음.
- **민감 영역**: 아님. **검수는 sonnet 기본으로 충분하다.** 단 검수자는
  **① 렌더러가 `if(!isServed)` 앞에 있는지 ② `apply()` 의 기존 sync·`resizePipToFit` 순서 비퇴화
  ③ 동적 셀렉터 표 행 수 7 유지 ④ 호출 규약·frontmatter 무변경**을 중점 항목으로 본다.

**신뢰도(단일 패스 구현 가능성): 8/10.** 변경 지점이 문자열 수준까지 특정돼 있고 기존 자산 재사용
비중이 높다. 감점 2는 (a) 스크립트 조기 반환 배치가 자동 검증만으로는 완전히 안전하지 않고,
(b) 시간 경과 동작은 수동 확인 4~5 에 의존하기 때문이다.

---

## 사용자 승인이 필요한 핵심 결정

1. **「지금」을 독립 `.card` 로 둔다** (첫 카드 아래, impl 카드 위). 대안은 첫 카드 안의 한 줄
   스트립(카드 테두리 없음, 세로 60px 절약)이며, 더 축소하면 활성 `<li>` 안에 경과 시간만
   붙이는 안(카드 없음, "다음 단계" 없음)도 가능하다. **카드로 확정하는가?**

2. **경과 시각은 `step <n> active` 전이가 자동으로 각인한다 — 인자를 하나도 추가하지 않는다.**
   각인 형식은 `#dz-updated` 와 같은 `YYYY-MM-DD HH:MM` 이고, **이미 `active` 인 단계를 다시
   `active` 로 부를 때는 리셋하지 않는다.** 이 규칙으로 확정하는가?

3. **`마지막 기록 N분 전`(정체 감지)을 경과 시간 옆에 함께 표시한다.** 비용은 함수 재사용 2줄이고
   절차 변경은 0이다. 숫자 둘이 부담스러우면 **이 항목만 빼도 나머지 설계는 그대로 성립한다** —
   포함하는가?

4. **매트릭스 세션(그룹 2개 이상)에서는 카드를 통째로 숨긴다.** "현재/다음"이 개념적으로 성립하지
   않고, 불변식 1 덕분에 **분기 코드가 0줄**이다. 그룹별 다중 표시는 매트릭스 표의 텍스트 복제라
   기각했다. 이 방침에 동의하는가?

5. **`.step-detail`(담당 에이전트·모델 등)을 카드에 재노출하지 않는다.** 바로 위 활성 단계 줄에
   이미 보이고 PiP 압축 뷰에서도 활성 단계 것만 보이므로 인접 중복이다. 담당 표기는 계속
   `step 3 active "implementer(sonnet) 디스패치 중"` 처럼 상세 문자열로 적는다. 동의하는가?

6. **`README.md` L120 의 줄 수(현재 `1113`)를 실제 값으로 갱신하고, 설명 문단에 1문장만 추가한다.
   `docs/images/dashboard-sample.png` 재촬영은 이번 범위에서 제외한다**(카드가 없는 화면이 되어
   약간 stale 해진다). 이 처리로 진행하는가?
