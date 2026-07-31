# Claude Code 개발 환경 배포

개인 Claude Code 워크플로우, 코드 품질 규칙, 에이전트 설정을 독립 git 레포로 패키징했습니다. 어느 프로젝트든 동일한 개발 환경을 재구성할 수 있습니다.

## 설치

### 기본 사용법

**프로젝트 레벨 설치** (현재 프로젝트에 적용)

```bash
# 설치하려는 프로젝트 디렉토리에서 실행
cd /path/to/my-project
/path/to/coding-env/install.sh --scope project
```

**사용자 레벨 설치** (`~/.claude` 에 전역 적용)

```bash
/path/to/coding-env/install.sh --scope user
```

**계획만 확인 (파일시스템 변경 없음)**

```bash
./install.sh --scope project --dry-run
```

**기존 파일 덮어쓰기**

```bash
./install.sh --scope project --force
```

### 플래그 상세

| 플래그 | 필수 | 동작 |
|--------|------|------|
| `--scope project` | 택1 필수 | 현재 디렉토리(`$PWD`)에 설치 |
| `--scope user` | 택1 필수 | `~/.claude/` 에 설치 |
| `--force` | 아니오 | CLAUDE.md 백업 후 덮어쓰기. rules/agents/commands 차이가 있어도 덮어쓰기 |
| `--dry-run` | 아니오 | 계획만 출력. 파일시스템 변경 없음 |
| `--help` | 아니오 | 사용법 출력 후 종료 |

**중요**: `--scope` 를 생략하면 오류 발생. 잘못된 대상에 설치하는 사고를 방지하기 위해 항상 명시해야 합니다.

## 설치 대상

| 항목 | 파일 수 | project 경로 | user 경로 | 로드 시점 |
|------|--------|-------------|----------|----------|
| CLAUDE.md | 1 | `./CLAUDE.md` | `~/.claude/CLAUDE.md` | **항상** |
| rules/ | 37 | `./.claude/rules/` | `~/.claude/rules/` | 12개 항상 · 25개 조건부 |
| agents/ | 4 | `./.claude/agents/` | `~/.claude/agents/` | 호출 시 |
| commands/ | 6 | `./.claude/commands/` | `~/.claude/commands/` | 호출 시 |

**합계**: 48개 파일

상시 컨텍스트를 차지하는 것은 **CLAUDE.md 1개 + rules 12개 = 13개(약 34KB)** 뿐입니다.
나머지는 조건이 맞을 때(rules 25개) 또는 호출할 때(agents 4개, commands 6개)만 로드됩니다.

### CLAUDE.md 구성

배포되는 CLAUDE.md는 **범용 개발 지침**입니다. 프로젝트 고유 내용(아키텍처, 성능 병목,
빌드 명령, 팀 커밋 컨벤션)은 각 프로젝트가 자체 CLAUDE.md에 추가하며, 충돌 시 프로젝트가 우선합니다.

- **개발 워크플로우** — 작업 규모로 경로를 분류: 전체 경로(설계→구현→검수) /
  축약 경로(구현→검수) / 생략(로직 없는 수정). 어느 경로든 **검수는 생략하지 않습니다**
- **모델 운용 원칙** — 설계 opus / 구현 sonnet / 검수 sonnet(민감 영역은 opus 승격) / 탐색 haiku
- **코드 품질 가이드라인** — 함수 50줄·중첩 3단계 이내, 외부 I/O와 순수 로직 분리,
  YAGNI, 매직 넘버 상수화, 축약 없는 이름 등. 아래 rules와 수치 기준이 통일되어 있습니다

### commands 구성

`prp-prd` → `prp-plan` → `prp-implement` → `prp-pr` 워크플로우와 그 의존 대상입니다.

| 커맨드 | 줄 수 | 역할 |
|--------|------|------|
| `prp-prd` | 447 | 문제 정의 우선 PRD 작성 (대화형) |
| `prp-plan` | 502 | 코드베이스 분석 기반 구현 계획 수립 |
| `prp-implement` | 385 | 계획 실행 + 검증 루프 |
| `prp-pr` | 184 | 브랜치 변경 분석 후 GitHub PR 생성 |
| `prp-commit` | 131 | 자연어로 파일 지정해 커밋 (컨벤션: 프로젝트 CLAUDE.md > commitlint 설정 > 기본 형식) |
| `code-review` | 289 | 로컬 변경 또는 PR 검수 |

각 커맨드의 동작:

- **`/prp-prd`** — 대화형 질문으로 문제 정의부터 시작해 PRD 문서를 생성합니다.
  결과물의 Implementation Phases 표가 `/prp-plan` 의 입력이 됩니다.
- **`/prp-plan`** — PRD 또는 기능 설명을 받아 코드베이스를 분석하고,
  단계별 검증 기준이 포함된 구현 계획 문서를 만듭니다.
- **`/prp-implement`** — 계획을 순서대로 실행하며 단계마다 테스트·lint 검증 루프를 돕니다.
- **`/prp-pr`** — 브랜치의 전체 커밋을 분석해 요약과 테스트 계획이 담긴 GitHub PR을 생성합니다.
- **`/prp-commit`** — "the auth changes" 같은 자연어로 커밋 대상을 지정하면
  스테이징부터 메시지 작성까지 수행합니다. 메시지 형식은
  **프로젝트 CLAUDE.md 컨벤션 > commitlint 설정(`.commitlintrc*` 등) > 기본 `{type}: {description}`**
  순으로 해석합니다.
- **`/code-review`** — 로컬 미커밋 변경 또는 GitHub PR을 보안(CRITICAL)부터
  베스트 프랙티스(LOW)까지 심각도별로 검수하고, CRITICAL/HIGH 발견 시 커밋·머지 차단을 권고합니다.

**6종이 닫힌 의존 사슬을 이룹니다.** `prp-implement` 가 `/code-review`·`/prp-commit`·`/prp-pr` 을,
`prp-pr` 이 `/code-review`·`/prp-commit` 을 호출합니다. 일부만 설치하면 사슬이 끊기므로 전부 배포합니다.
배포되는 `agents/code-reviewer.md` 도 `/code-review` 를 참조합니다.

`--scope project` 로 설치하면 전역(`~/.claude/commands/`)과 비교해 상황을 보고합니다.
`--scope user` 는 설치 대상이 곧 전역이므로 비교를 생략합니다.

**주의 — 커맨드 우선순위는 전역이 프로젝트를 이깁니다** ([skills 문서](https://code.claude.com/docs/en/skills):
"personal overrides project"). rules·agents 와 방향이 반대입니다:

| 자산 | 같은 이름일 때 이기는 쪽 |
|------|------------------------|
| rules | 프로젝트 |
| agents | 프로젝트 |
| commands | **전역** |

따라서 전역에 같은 이름의 커맨드가 **다른 내용**으로 존재하면, 프로젝트 사본은 무시되고
전역 버전이 실행됩니다. install.sh 가 이 상황을 감지해 경고하며, 프로젝트 사본을 쓰려면
`install.sh --scope user` 로 전역을 갱신하면 됩니다. 전역에 커맨드가 없는 새 머신에서는
프로젝트 사본이 그대로 동작합니다.

같은 이름이 양쪽에 있어도 **토큰 이중 비용은 없습니다** — 이긴 쪽 하나만 커맨드 목록에
등재되고(description 한 줄), 본문은 호출할 때 이긴 쪽 것만 로드됩니다.

### agents 구성

CLAUDE.md 「개발 워크플로우」의 3단계(설계 → 구현 → 검수)를 역할별 서브에이전트가 분담합니다.

| 에이전트 | 모델 | 역할 |
|---------|------|------|
| `design-architect` | opus | **설계 전담.** 전체 경로 작업에서 구현 전에 설계 문서(PRP)를 생성. 구현 코드는 작성하지 않음 |
| `implementer` | sonnet | **구현 전담.** 승인된 PRP 기반(전체 경로) 또는 접근 방식 보고 후(축약 경로) 코드 작성. 테스트·lint·type check 전부 통과가 완료 기준 |
| `code-reviewer` | sonnet | **검수 전담.** 코드를 직접 수정하지 않고 보고만 — Edit/Write 권한이 의도적으로 없음. PASS/FAIL 판정이 커밋 게이트 |
| `explore` | haiku | **탐색·수집 전용** 저비용 에이전트. 판단이 필요한 작업(설계·구현·검수 판정)에는 사용하지 않음 |

- 작업 에이전트 3종은 `Skill` 도구를 보유해, 설치된 `/prp-plan`·`/prp-implement`·`/code-review`
  커맨드를 직접 로드해 절차대로 수행합니다. 커맨드 미설치 환경에서는 각자의 내장 체크리스트로
  동작합니다 (fallback).
- 모델 배분은 CLAUDE.md 「모델 운용 원칙」을 따릅니다: 판단 오류의 파급이 가장 큰 설계에 opus,
  토큰 소비가 가장 큰 구현에 sonnet, 수집 전용에 haiku.

### rules 구성

37개 규칙 파일은 JS/TS + React + 웹 + React Native/Expo 스택에 맞춰 큐레이션되어 있습니다:

| 분류 | 파일 수 | 로드 방식 | 설명 |
|------|--------|----------|------|
| common/ | 11 | **항상** | 언어 무관 원칙 (coding-style, testing, git-workflow, karpathy-guidelines 등) |
| README.md | 1 | **항상** | rules 구조·우선순위 안내 |
| typescript/ | 5 | **조건부** | `paths`(ts/tsx/js/jsx) 매칭 시 로드 |
| react/ | 5 | **조건부** | `paths`(tsx/jsx, components·hooks 디렉토리의 ts/js) 매칭 시 로드 |
| web/ | 7 | **조건부** | `paths`(tsx/jsx/vue/svelte/css/scss/sass/less/html) 매칭 시 로드 |
| react-native/ | 8 | **조건부** | React Native/Expo 확장 (accessibility·production-readiness 포함) |

**항상 로드되는 rules**: 12개, ~26KB (CLAUDE.md 포함 시 13개, ~34KB)

`common/karpathy-guidelines.md` 는 Andrej Karpathy의 관찰에서 파생된, LLM 코딩의 흔한 실패를 줄이기 위한 행동 지침입니다. 4개 원칙으로 구성됩니다:

1. **Think Before Coding** — 전제를 명시하고, 불명확하면 추측하지 않고 질문. 여러 해석이 있으면 임의로 고르지 않고 제시
2. **Simplicity First** — 요청 범위를 넘는 기능, 추측성 추상화, 불가능한 시나리오의 에러 처리 금지
3. **Surgical Changes** — 요청과 무관한 인접 코드를 "개선"하지 않음. 모든 변경 줄이 요청으로 소급 가능해야 함
4. **Goal-Driven Execution** — 작업을 검증 가능한 목표로 변환 ("버그 수정" → "재현 테스트 작성 후 통과시키기")

`paths` frontmatter가 없으므로 **설치된 모든 프로젝트에서 자동 적용**됩니다. `common/coding-style.md` 의 에러 처리 정책(실제 발생 가능한 실패만 처리)도 이 지침의 #2와 정렬되어 있습니다.

**조건부 로드 방식**: `paths` 규칙은 Claude가 **매칭되는 파일을 실제로 Read/Edit하는 시점**에 동적으로 로드됩니다 ([공식 문서](https://code.claude.com/docs/en/memory) — "Path-scoped rules trigger when Claude reads files matching the pattern"). 예: `.tsx` 파일을 편집하는 순간 react/ 규칙이 붙습니다. 매칭 파일을 다루지 않는 세션에서는 로드되지 않아 컨텍스트를 절약합니다.

**주의 — react-native/ 와 웹 규칙의 glob 겹침**: RN 소스도 `.ts(x)`라서 react-native 규칙 역시 `**/*.ts(x)`를 사용합니다(확장자로는 구분 불가). 따라서 순수 웹 프로젝트에서도 TS 파일 편집 시 RN 규칙이 함께 로드됩니다. 웹 전용 프로젝트라면 설치 후 `.claude/rules/react-native/` 를 삭제하세요 (RN 프로젝트에서는 반대로 web/ 삭제 가능). 단, 재설치하면 누락 파일로 간주되어 자동 복원되므로 그때 다시 삭제해야 합니다.

자세한 구조는 [`rules/README.md`](./rules/README.md)를 참조하세요.

## 안전장치

### CLAUDE.md (프로젝트 고유 지침)

- **기존 파일 없음**: 복사 진행
- **기존 파일 있음, `--force` 없음**: **중단** (exit 1). 다른 자산도 변경 안 함
  - 출력 예: `[WARN] ./CLAUDE.md 가 이미 존재합니다 (sha256 a3f1c8…)`
  - 복구: `--force` 플래그 추가 후 재실행
- **기존 파일 있음, `--force` 있음**: 먼저 백업 후 교체
  - 백업 파일: `CLAUDE.md.bak-20260728-144500` (타임스탬프)
  - 타임스탬프 덕분에 여러 번 `--force` 실행해도 백업이 백업을 덮어쓰지 않음

**이유**: CLAUDE.md는 프로젝트별 설정(아키텍처, 병목, 빌드 명령)을 담으며, 사용자 CLAUDE.md가 스스로 "프로젝트 루트의 CLAUDE.md에 정의한다"고 규정합니다. 자동 덮어쓰기는 거의 항상 사고입니다.

### rules/ · agents/ · commands/ (벤더링 자산)

**소유권 원칙**: 이 스크립트는 **레포가 배포하는 파일만** 관리합니다. 대상 디렉토리에만 있는 파일은 손대지 않습니다.

이 구분이 중요한 이유는 대상 디렉토리가 보통 우리 것이 아니기 때문입니다. 예를 들어 `~/.claude/agents/` 에는 이 레포가 배포하는 4개 외에 수십 개가 공존하고, `~/.claude/commands/` 에도 배포 대상 6개 외 수십 개가 있습니다.

| 대상 상태 | 판정 | 동작 |
|-----------|------|------|
| 대상 디렉토리 없음 | — | 생성 후 복사 |
| 관리 파일이 대상에 없음 | 누락 | **자동 복원** (`--force` 불필요 — 파괴 위험이 없음) |
| 관리 파일 내용이 다름 | 사용자 수정 의심 | 차이 **파일명 출력**(최대 20건) 후 **중단**(exit 1). `--force` 요구 |
| 대상에만 있는 파일 | **우리 소유 아님** | 충돌로 보지 않음. 삭제하지 않음 |

설치 후에는 배포한 파일이 전부 반영됐는지 `diff -rq` 로 검증합니다. 대상에만 있는 파일은 검증 대상이 아닙니다.

**이유**: 단일 출처는 이 레포입니다. 업데이트가 필요하면 레포에서 수정하고 재설치합니다. 다만 대상 디렉토리 전체를 레포 소유로 간주하면 사용자의 다른 자산을 오판하거나 파괴합니다.

## 멱등성

동일한 명령을 여러 번 실행해도 안전합니다:

```bash
./install.sh --scope project  # 1회차
./install.sh --scope project  # 2회차 — 이미 설치된 파일을 그대로 복사. 부작용 없음
```

## 파일 구조

```
coding-env/
├── README.md                      # 이 파일
├── install.sh                     # 배포 스크립트 (순수 bash, 외부 의존 없음)
├── CLAUDE.md                      # 배포 대상 사용자 지침
├── rules/                         # 37개 규칙 (JS/TS·React·웹·RN/Expo 스택 큐레이션)
│   ├── README.md                  # rules 구조 설명
│   ├── common/                    # 언어 무관 (11개, karpathy-guidelines 포함)
│   ├── typescript/                # TS/JS 전용 (5개, 조건부 로드)
│   ├── react/                     # React 전용 (5개, 조건부 로드)
│   ├── react-native/              # React Native/Expo 전용 (8개, 조건부 로드)
│   └── web/                       # 웹 프론트엔드 전용 (7개, 조건부 로드)
├── agents/                        # 4개 에이전트
│   ├── design-architect.md
│   ├── implementer.md
│   ├── code-reviewer.md
│   └── explore.md
├── commands/                      # 6개 커맨드 (닫힌 의존 사슬)
│   ├── prp-prd.md
│   ├── prp-plan.md
│   ├── prp-implement.md
│   ├── prp-pr.md
│   ├── prp-commit.md
│   └── code-review.md
├── docs/prps/
│   └── coding-env.md              # 설계 문서 (PRP rev4)
└── tests/
    └── run.sh                     # 테스트 스크립트
```

## 설계 문서

전체 설계 원리와 리스크 분석은 [`docs/prps/coding-env.md`](./docs/prps/coding-env.md)를 참조하세요.

## 요구사항

- bash 3.2 이상 (macOS 기본 `/bin/bash` 로 검증됨 — 별도 설치 불필요)
- `cp`, `mkdir`, `find`, `diff`, `date` (표준 유틸리티)
- 대상 디렉토리에 쓰기 권한

## 라이선스

사용자 개인 워크플로우 패키징입니다.
