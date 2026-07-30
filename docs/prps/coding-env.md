# PRP: Claude Code 개발 환경 배포 시스템 (install.sh)

**작성일**: 2026-07-28
**상태**: 승인 완료 — 구현 완료
**분류**: 전체 경로 (설계 → 구현 → 검수)
**개정**:
- rev2 — `paths` frontmatter 실측 검증 결과로 rev1의 언어 선택자 설계를 폐기
- rev3 — `rules/common/karpathy-guidelines.md` 를 배포 자산에 추가 (rules 78 → 79개)
- rev4 — `commands/` 6종을 배포 자산에 추가 (총 84 → 90개 파일). 전역 커맨드 비교 보고 신설

---

## 0. rev1에서 정정된 사실 (설계 전제)

rev1은 두 가지 사실을 틀렸다. 실측으로 확정한 내용을 먼저 고정한다.

### 사실 1 — rules는 전량 자동 로드되지 않는다. `paths` frontmatter로 조건부 로드된다

`~/.claude/rules/` 89개 파일을 전수 조사한 결과:

| 구분 | 파일 수 | frontmatter | 로드 시점 |
|------|--------|-------------|----------|
| 언어별 12종 (cpp, csharp, dart, golang, java, kotlin, perl, php, python, rust, swift, typescript) | **60** | `paths: ["**/*.py"]` 등 | **조건부** — 해당 glob에 맞는 파일이 있을 때만 |
| README.md + common/ + web/ + zh/ | **29** | 없음 | **항상** (launch 시) |

검증 방법과 근거:
- `head -1` 로 60개 파일이 `---` YAML frontmatter로 시작함을 확인, `grep -rl "^paths:"` 로 60개 전부 `paths:` 보유 확인
- 나머지 29개는 frontmatter 없음
- 이 세션(코드 파일 0개인 프로젝트)의 실제 컨텍스트에 정확히 29개만 로드됨 → 60개 언어별은 전부 비활성
- 공식 문서: "Rules without `paths` frontmatter are loaded at launch with the same priority as `.claude/CLAUDE.md`" ([memory](https://code.claude.com/docs/en/memory))

**설계 귀결**: 언어 선택 설치는 불필요하다. 89개를 통째로 배포하면 Python 프로젝트에서 `python/` 규칙이, TS 프로젝트에서 `typescript/` 규칙이 자동으로 켜진다. 선택자를 두는 것은 이미 존재하는 메커니즘을 손으로 다시 만드는 것이며, 사용자 CLAUDE.md의 YAGNI 조항 위반이다.

### 사실 2 — 프로젝트 레벨 `.claude/rules/` 와 `.claude/agents/` 는 공식 지원된다

- rules: "you can organize instructions into multiple files using the `.claude/rules/` directory... All `.md` files are discovered recursively" / "User-level rules are loaded before project rules, giving project rules higher priority" ([memory](https://code.claude.com/docs/en/memory))
- agents: "Project subagents (`.claude/agents/`) ... discovered by walking up from the current working directory" / 우선순위 `.claude/agents/` > `~/.claude/agents/` > 플러그인 agents ([sub-agents](https://code.claude.com/docs/en/sub-agents))
- `@import` 은 **CLAUDE.md 전용** 문법이다. rules 파일에서는 지원이 문서화되지 않았다. 최대 4홉, 상대경로는 import를 포함한 파일 기준으로 해석. 백틱으로 감싸면 import되지 않음

**설계 귀결**: `--scope project` 는 성립한다. rev1의 미검증 리스크(T11)는 해소됐다.

### 사실 3 — 플러그인은 CLAUDE.md와 rules를 배포할 수 없다

- "A `CLAUDE.md` file at the plugin root is not loaded as project context. Plugins contribute context through skills, agents, and hooks rather than CLAUDE.md." ([plugins-reference](https://code.claude.com/docs/en/plugins-reference))
- `plugin.json` 지원 필드에 `claudeMd` / `rules` / `instructions` 없음. `settings.json` 의 `claudeMd` 는 조직 관리자 전용(managed settings)
- `agents` 필드는 플러그인에서 정상 지원됨

**설계 귀결**: CLAUDE.md와 rules는 install.sh 로만 배포 가능하다. 플러그인 단독 배포는 선택지가 아니다.

### 사실 4 — 대상 디렉토리는 우리 소유가 아니다 (rev2 구현 중 발견)

실측:
- `~/.claude/agents/` 에는 **51개** 파일이 있다. 이 배포가 관리하는 것은 **4개**뿐이다 (나머지 47개는 사용자의 다른 에이전트)
- `~/.claude/rules/` 에는 **89개** 가 있다. 이 배포가 관리하는 것은 **79개**뿐이다 (`zh/` 11개는 배포 제외이며 §2에 따라 삭제하지 않는다)

**설계 귀결**: "대상 디렉토리 파일 수 == 배포 파일 수" 를 검증하거나 "대상에만 있는 파일" 을 충돌로 판정하면, 이 사용자의 실제 머신에서 `--scope user` 가 **항상 실패**한다. 따라서 소유권 경계를 다음과 같이 고정한다.

| 상태 | 판정 | 동작 |
|------|------|------|
| 소스에 있고 대상에 없음 | 누락 | 복원 (안전 — 파괴 없음) |
| 소스·대상 양쪽에 있고 내용 다름 | **사용자 수정 의심** | `--force` 요구 |
| 대상에만 있음 | **우리 소유 아님** | 충돌로 보지 않음. 삭제하지 않음 |

검증 방식도 이에 맞춘다: 파일 개수 대조가 아니라 `diff -rq` 로 **소스 기준** 누락·차이가 0인지 확인한다. 회귀 테스트 T16이 이 경계를 고정한다.

---

## 1. 요구사항

사용자의 Claude Code 개발 환경을 독립 git 레포로 만들어, 어느 프로젝트에서든 동일 환경을 재구성할 수 있게 한다.

```bash
install.sh --scope project|user [--force] [--dry-run] [--help]
```

배포 자산 4종:

| 자산 | 파일 수 | 성격 | 덮어쓰기 정책 |
|------|--------|------|--------------|
| `CLAUDE.md` | 1 | **사용자가 프로젝트별로 수정하는 파일** | 보호 — 기존 파일 있으면 중단, `--force` 필수 |
| `rules/` | 79 | 벤더링 자산 (레포가 단일 출처) | 덮어쓰기 = 업데이트 수단 |
| `agents/` | 4 | 벤더링 자산 | 덮어쓰기 = 업데이트 수단 |
| `commands/` | 6 | 벤더링 자산 | 덮어쓰기 = 업데이트 수단 |

### 비목표

- **언어 선택 설치** — 사실 1에 의해 불필요
- **`zh/` 배포** — common의 중국어 번역판이며 **항상 로드**된다. 한국어 사용자에게는 매 세션 44K 순손실
- **스킬 배포** — 스킬은 호출하거나 모델이 관련성을 판단해야 로드되므로 "설치하면 자동 적용" 이 성립하지 않는다. `~/.claude/skills/` 로 별도 관리한다
  - rev4 정정: **커맨드는 배포한다.** rev1~rev3 에서 비목표였으나 사용자 워크플로우의 핵심이므로 `commands/` 6종을 자산에 포함했다 (§6i)
- **karpathy 지침의 스킬 형태 배포** — 스킬은 호출해야 로드된다. 자동 적용이 목적이므로 `rules/common/` 에 규칙 파일로 넣었다 (rev3, §6h)
- **플러그인 배포** — 사실 3에 의해 CLAUDE.md/rules가 불가능하므로, 자산이 두 경로로 쪼개지는 복잡도를 감수할 이유가 없다. 향후 skills를 추가할 때 재검토
- **자동 업그레이드, 프로필 시스템, JSON 매니페스트** — YAGNI

---

## 2. 영향 범위

### 레포 구조 (신규)

```
coding-env/
├── CLAUDE.md                  # 배포 대상 지침 (142줄). 원본: ~/.claude/CLAUDE.md
├── install.sh                  # 배포 엔트리포인트 (bash, 외부 의존 없음)
├── README.md                   # 설치·사용법
├── rules/                      # 79개 (zh/ 11개 제외)
│   ├── README.md               #   구조 설명 — paths frontmatter 동작 명시
│   ├── common/                 #   11개, frontmatter 없음 → 항상 로드
│   │   └── karpathy-guidelines.md   #   rev3 추가 — 설치 시 자동 적용되는 행동 지침
│   ├── web/                    #    7개, frontmatter 없음 → 항상 로드
│   └── {12개 언어}/            #   60개, paths frontmatter → 조건부 로드
├── agents/                     # 4개
│   ├── design-architect.md     #   52줄
│   ├── implementer.md          #   60줄
│   ├── code-reviewer.md        #  236줄
│   └── explore.md              #   24줄
├── commands/                   # 6개, 합 1,919줄 (rev4 추가)
│   ├── prp-prd.md · prp-plan.md · prp-implement.md · prp-pr.md
│   └── prp-commit.md · code-review.md
├── .claude/                    # 이 레포 자체의 설정 (배포 대상 아님)
│   └── settings.local.json     #   개인 권한 목록, git 제외
└── docs/prps/coding-env.md     # 이 문서
```

### 설치 결과

| `--scope` | CLAUDE.md | rules/ | agents/ | commands/ |
|-----------|-----------|--------|---------|-----------|
| `project` | `./CLAUDE.md` | `./.claude/rules/` | `./.claude/agents/` | `./.claude/commands/` |
| `user` | `~/.claude/CLAUDE.md` | `~/.claude/rules/` | `~/.claude/agents/` | `~/.claude/commands/` |

### 건드리지 않는 것

- `settings.json` / `settings.local.json` — 권한·env·훅은 머신 고유 설정이므로 배포 대상이 아니다. JSON 병합 로직이 필요 없어져 install.sh가 순수 bash로 유지된다
- 기존 플러그인, 스킬, 나머지 40여 개 에이전트
- `~/.claude/rules/zh/` — 이미 설치된 것을 **삭제하지 않는다**. 배포에서 제외할 뿐이다

---

## 3. 아키텍처

```
install.sh (설계 시 목표 100줄 → 실제 423줄, 함수 25개)
├── parse_arguments()        # 순수: argv → 설정값. 검증 실패 시 usage + exit 1
├── resolve_target_paths()   # 순수: scope → 절대 경로 4개
├── check_preconditions()    # I/O 읽기: 쓰기 권한, 심볼릭 링크, CLAUDE.md 존재
├── print_plan()             # 순수 출력: dry-run과 실제 실행이 같은 계획을 출력
├── install_claude_md()      # I/O 쓰기: 보호 정책 적용
├── install_directory()      # I/O 쓰기: rules/ · agents/ · commands/ 공통
└── main()                   # 위 함수 순차 호출
```

설계 근거:
- 순수 함수(파싱·경로 해석·계획 출력)와 I/O를 분리해 단위 테스트 가능하게 한다 (사용자 CLAUDE.md: "외부 세계에 닿는 코드와 순수 로직을 분리")
- 함수당 30줄 이내 유지
- `install_directory()` 하나로 rules/ · agents/ · commands/ 를 모두 처리 — 자산별 분기 함수를 만들지 않는다 (DRY). 자산이 3개에서 4개로 늘 때 호출 한 줄만 추가됐다
- 외부 의존 없음: `cp`, `mkdir`, `find`, `diff`, `date`, `sha256sum`(또는 `shasum`) 만 사용. jq/node 불필요

**규모 초과에 대한 기록**: 설계 시 100줄을 목표했으나 실제는 423줄이다. 초과분은 실행 검증에서 드러난 결함(E1~E6) 대응과 rev4 커맨드 자산 추가다 — 명시적 반환값 검사(E2), 소유권 경계 판정(E6), 차이 목록 출력(E4), 설치 후 검증(E3), 전역 비교 보고(rev4). 함수 25개 전부 30줄 이내이고, `rules/common/coding-style.md` 의 파일 크기 기준(200~400줄 typical)에는 부합한다. 목표치 자체가 낙관적이었다고 판단하고 스펙을 실측값으로 갱신한다.

---

## 4. 데이터 모델

rev1의 `ASSET_SOURCES` / `ASSET_DEPS` 연관 배열은 **폐기**한다. 언어 선택자가 없어지면 자산은 고정 개수이므로 맵이 필요 없다. rev4 에서 자산이 4개로 늘었지만 변수 하나만 추가됐다.

```bash
# 전부. 이것이 데이터 모델의 총량이다.
readonly SCOPE="$1"                    # project | user
readonly REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# resolve_target_paths() 의 산출물
target_claude_md=""      # ./CLAUDE.md          | ~/.claude/CLAUDE.md
target_rules_dir=""      # ./.claude/rules      | ~/.claude/rules
target_agents_dir=""     # ./.claude/agents     | ~/.claude/agents
target_commands_dir=""   # ./.claude/commands   | ~/.claude/commands
```

### 상태 파일을 두지 않는 이유

rev1은 `.install-state` 에 asset별 파일 개수를 기록해 부분 실패를 감지하려 했다. 폐기한다.

- `rules/` 와 `agents/` 는 벤더링 자산이므로 **재실행 시 전량 덮어쓰기가 정상 동작**이다. 이것이 곧 업데이트 수단이다
- 따라서 "누락 파일만 설치" 같은 차분 로직이 필요 없고, 그것을 위한 상태 추적도 필요 없다
- 부분 실패 복구 = 재실행. 상태 파일 없이 성립한다
- 상태 파일이 없으면 dry-run이 상태를 오염시킬 경로(rev1 리스크 5)도 원천적으로 사라진다

멱등성은 `cp -R` 의 성질에서 나온다. 별도 장치가 필요하지 않다.

---

## 5. 인터페이스

### CLI 스펙

| 플래그 | 필수 | 기본값 | 동작 |
|--------|------|--------|------|
| `--scope project` | 택1 필수 | — | 현재 디렉토리에 설치 |
| `--scope user` | 택1 필수 | — | `~/.claude/` 에 설치 |
| `--force` | 아니오 | off | 기존 `CLAUDE.md` 를 백업 후 덮어쓴다 |
| `--dry-run` | 아니오 | off | 계획만 출력. 파일시스템 변경 0 |
| `--help` | 아니오 | — | usage 출력 후 exit 0 |

`--scope` 를 생략하면 usage를 출력하고 exit 1. **기본값을 두지 않는다** — 잘못된 대상에 설치하는 사고가 이 스크립트의 최대 위험이므로 항상 명시를 요구한다.

### Exit Code

| 코드 | 의미 |
|------|------|
| 0 | 성공, 또는 `--dry-run` / `--help` 완료 |
| 1 | 실패 (인자 오류, 권한 없음, CLAUDE.md 충돌, 복사 실패) |

### 출력 형식

```
$ ./install.sh --scope project
[INFO] coding-env 설치 (scope: project)
[INFO] 대상: /Users/byron/works/some-project
[OK]   rules/  79개 파일 → ./.claude/rules/
[OK]   agents/  4개 파일 → ./.claude/agents/
[OK]   CLAUDE.md → ./CLAUDE.md
[DONE] 83개 파일 설치 완료
```

```
$ ./install.sh --scope project        # CLAUDE.md 가 이미 있을 때
[INFO] coding-env 설치 (scope: project)
[WARN] ./CLAUDE.md 가 이미 존재합니다 (수정일 2026-07-20, sha256 a3f1c8…)
[WARN] 덮어쓰려면 --force 를 쓰십시오. 실행 시 ./CLAUDE.md.bak-20260728-114500 로 백업됩니다
[ERROR] 설치 중단 — 변경된 파일 없음
```

```
$ ./install.sh --scope user --dry-run
[INFO] coding-env 설치 계획 (scope: user, DRY-RUN)
  [계획] mkdir -p ~/.claude/rules ~/.claude/agents
  [계획] cp -R rules/. ~/.claude/rules/            (79개, 기존 파일 덮어씀)
  [계획] cp -R agents/. ~/.claude/agents/          (4개, 기존 파일 덮어씀)
  [보호] ~/.claude/CLAUDE.md 존재 → 건너뜀 (--force 없음)
[DONE] 82개 파일이 변경될 예정. 실제 변경 없음
```

계획 출력은 dry-run과 실제 실행이 **같은 함수**를 쓴다. 두 경로가 달라지면 dry-run이 거짓말을 하게 된다.

---

## 6. 설계 결정

### (a) rules/ 는 zh/ 를 제외한 79개 전량 배포

**결정**: 언어 선택자 없음. `zh/` 만 제외.

**근거**:
1. 사실 1 — `paths` frontmatter가 언어별 60개를 자동으로 조건부화한다. 선택자는 중복 메커니즘
2. 언어별 60개는 매칭되지 않으면 컨텍스트를 전혀 차지하지 않는다. 전량 배포의 비용이 0에 가깝다
3. 반면 `zh/` 11개는 frontmatter가 없어 **항상 로드**된다. common의 중국어 번역이므로 한국어 사용자에게 내용상 순중복이며, 매 세션 44K를 소비한다
4. 제외 효과: 항상 로드되는 자산이 29개 116K → **18개 72K로 38% 감소**

**부수 발견 (D2에서 판단 요청)**: `web/` 7개 28K도 frontmatter가 없어 웹과 무관한 프로젝트에서도 항상 로드된다. 이 프로젝트가 그 예다. `paths: ["**/*.{ts,tsx,jsx,css,html,vue,svelte}"]` 를 붙이면 조건부화되지만, 이는 사용자 원본 자산의 내용 변경이므로 임의로 하지 않는다.

---

### (b) rules 로드 방식은 설계하지 않는다 — 이미 동작한다

**결정**: install.sh는 파일을 올바른 위치에 복사만 한다. import 문법이나 인덱스 파일을 만들지 않는다.

**근거**:
1. `.claude/rules/` 는 재귀 자동 발견 대상이다. 복사하면 끝이다
2. `@import` 는 CLAUDE.md 전용이고 rules 파일에서의 지원이 문서화되지 않았다. 쓰지 않는다
3. 단, `rules/README.md` 는 `paths` frontmatter 동작을 설명하도록 갱신이 필요하다. 현재 README는 install.sh로 언어별 디렉토리를 선택 복사하라고 안내하는데, 이는 `paths` 도입 이전의 서술로 보인다 → **D3**

---

### (c) CLAUDE.md 보호: 기본 중단 + 타임스탬프 백업

**결정**:
- 기존 파일이 있으면 **기본 동작은 중단**(exit 1). 자동 병합도, 자동 덮어쓰기도 하지 않는다
- `--force` 시에도 **먼저 백업**한다: `CLAUDE.md.bak-YYYYmmdd-HHMMSS`
- 백업 파일명에 타임스탬프를 넣어 **백업이 백업을 덮어쓰지 않게** 한다 (rev1 지적 반영)

```bash
install_claude_md() {
  if [[ ! -f "$target_claude_md" ]]; then
    copy_file "$REPO_ROOT/CLAUDE.md" "$target_claude_md"
    return 0
  fi

  local existing_hash
  existing_hash=$(compute_sha256 "$target_claude_md")

  if [[ "$force_overwrite" != "true" ]]; then
    log_warn "$target_claude_md 가 이미 존재합니다 (sha256 ${existing_hash:0:12}…)"
    log_warn "덮어쓰려면 --force 를 쓰십시오"
    return 1
  fi

  local backup_path="${target_claude_md}.bak-$(date +%Y%m%d-%H%M%S)"
  copy_file "$target_claude_md" "$backup_path"
  log_info "기존 파일 백업: $backup_path"
  copy_file "$REPO_ROOT/CLAUDE.md" "$target_claude_md"
}
```

**근거**: CLAUDE.md는 프로젝트 고유 정보(아키텍처, 병목, 빌드 명령)를 담도록 설계된 파일이다. 사용자 CLAUDE.md 스스로 "프로젝트별 컨텍스트는 각 프로젝트 루트의 CLAUDE.md에 정의한다"고 규정한다. 즉 **덮어쓰기는 거의 항상 사고**다.

rev1은 해시를 "로그에 남긴다"고 했으나 그것으로는 복구가 불가능하다. 실제 파일 백업으로 교체했다.

---

### (d) rules/ 와 agents/ 는 관리 대상 파일만 덮어쓴다 — D1=(B) 확정

**결정**: 벤더링 자산으로 취급하되, **소유권 경계는 사실 4를 따른다.**

- 누락된 관리 파일 → 자동 복원 (`--force` 불필요, 파괴 위험 없음)
- 수정된 관리 파일 → 차이 파일명을 최대 20건 출력하고 `--force` 요구
- 대상에만 있는 파일 → 손대지 않음

**근거**: 단일 출처는 레포다. 설치된 사본을 손으로 고치는 것은 지원하지 않는 사용법이며, 고치고 싶으면 레포에서 고치고 재설치한다. 다만 대상 디렉토리 전체를 우리 것으로 간주하면 사실 4에 의해 이 사용자의 머신에서 동작하지 않는다.

**rev1 원안과의 차이**: rev1은 "어떤 차이든 `--force`" 였다. 그대로 구현하면 `~/.claude/rules/zh/` 11개와 `~/.claude/agents/` 의 47개 때문에 `--scope user` 가 항상 충돌로 막힌다. 누락 복원과 수정 보호를 분리해 해결했다.

**검증**: T4(누락 복원) · T15(수정 보호 + 차이 목록 출력) · T16(대상 전용 파일 보존)

---

### (e) 스킬 의존성은 옵셔널로 둔다

**결정**: 배포하지 않는다. 에이전트는 스킬 없이도 동작해야 한다.

**근거**: 사용자 CLAUDE.md가 이미 `/prp-plan`, `/prp-implement` 를 "설치된 경우" 로 조건화하고, "스킬이 설치되지 않은 프로젝트에서는 동일한 산출물 기준을 지키며 일반 지시로 수행한다"고 폴백을 규정한다. 설계가 이미 옵셔널을 전제한다.

단 `code-reviewer.md` 는 `/code-review` 스킬 사용을 무조건으로 서술한다 → 폴백 문구 추가 필요. **D4.**

---

### (f) explore.md 포함

**결정**: 4종 전부 배포.

**근거**: 사용자 CLAUDE.md 모델 운용 원칙에 "탐색 (Explore): haiku" 로 명시되고, 세 에이전트가 넓은 탐색을 Explore에 위임하는 구조다. 3종만 배포하면 워크플로우에 구멍이 난다.

---

### (g) 원자성은 포기하고 재실행으로 대체한다

**결정**: 트랜잭션 없음. 중간 실패 시 부분 적용 상태로 남고, 재실행으로 수복한다.

**근거**: 벤더링 자산 전량 덮어쓰기이므로 재실행이 항상 올바른 최종 상태로 수렴한다. 롤백 메커니즘은 이 성질 위에서 불필요한 복잡도다. CLAUDE.md만 예외적으로 백업을 갖는데, 그것이 유일하게 복구 불가능한 자산이기 때문이다.

**예외**: `check_preconditions()` 를 모든 쓰기보다 **앞에** 배치해, 권한 문제는 파일을 하나도 건드리지 않은 상태에서 걸러낸다.

---

### (h) karpathy 지침은 스킬이 아니라 규칙으로 배포한다 (rev3)

**결정**: `~/.claude/skills/karpathy-guidelines` 의 내용을 `rules/common/karpathy-guidelines.md` 로 옮겨 배포 자산에 포함한다. `paths` frontmatter는 붙이지 않는다.

**근거**:
1. **스킬은 자동 적용되지 않는다.** 호출(`/karpathy-guidelines`)하거나 모델이 관련성을 판단해야 로드된다. 요구사항은 "설치하면 자동 적용"이므로 스킬 형태로는 충족되지 않는다
2. `paths` 없는 규칙은 launch 시 항상 로드된다 (사실 1). 즉 설치된 모든 프로젝트에서 매 세션 적용된다
3. `common/` 이 의미상 맞는 위치다 — 언어 무관 원칙이며 `coding-style.md`·`patterns.md` 와 같은 성격이다
4. `CLAUDE.md` 에 병합하지 않은 이유: 142줄 파일이 더 커지고, 같은 내용이 스킬과 CLAUDE.md 양쪽에 중복된다

**비용**: 항상 로드되는 자산이 18개 72K → **19개 76K** 로 늘어난다. 매 세션 약 4K 추가다. `zh/` 제외로 절감한 44K에 비하면 작다.

**이 레포 자체에는 적용되지 않는다**: Claude Code는 `.claude/rules/` 만 자동 로드하고 레포 루트의 `rules/` 는 읽지 않는다. 즉 coding-env 에서 작업할 때 karpathy 지침은 비활성이다. 활성화하려면 이 레포에서 `install.sh --scope project` 를 실행해야 하는데, 그러면 79개 파일이 `.claude/rules/` 에 복제되어 원본과 이중화된다. 드리프트 위험이 이득보다 크다고 판단해 하지 않는다.

### (i) 커맨드 6종을 배포하고 전역과 비교 보고한다 (rev4)

**결정**: `commands/` 를 네 번째 배포 자산으로 추가한다. 6종 전부이며, `--scope project` 설치 시 전역 커맨드와 비교해 상황을 보고한다.

**왜 6종 전부인가 — 닫힌 의존 사슬**:
```
prp-prd → prp-plan → prp-implement → prp-pr
                          │  │            │
                          │  └──→ code-review ←┘
                          └──→ prp-commit ←──────┘
```
사용자가 지목한 4종(`prp-prd`·`prp-plan`·`prp-implement`·`prp-pr`)만 배포하면 `prp-implement` 가 호출하는 `/code-review`·`/prp-commit` 이 없다. 배포되는 `agents/code-reviewer.md` 도 `/code-review` 를 3곳에서 참조한다. 부분 배포는 참조 깨짐을 만든다. T17이 이 완결성을 자동 검사한다.

**컨텍스트 비용 0**: 커맨드는 호출 시에만 로드된다. 1,919줄을 배포하지만 상시 컨텍스트는 늘지 않는다. `rules/` 와 결정적으로 다른 점이다.

**전역 비교 보고 (사용자 결정)**:
- 전역에 있어도 **항상 설치한다** — 프로젝트 자기완결성 우선. 나중에 전역을 정리해도 설치된 프로젝트는 살아남는다
- 전역과 내용이 같으면 `[INFO] 전역에 동일한 커맨드 N개 존재` 안내
- 다르면 `[WARN]` 으로 이름을 나열하고 **전역 버전이 실행됨**을 알린다. rev4 최초 구현은 "프로젝트 우선" 으로 잘못 적었다가 정정했다 — 커맨드/스킬의 실제 우선순위는 **personal(전역) > project** 다 ("When skills share the same name across levels, enterprise overrides personal, and personal overrides project", [skills](https://code.claude.com/docs/en/skills)). rules(프로젝트 우선)·agents(프로젝트 우선)와 방향이 반대라는 점에 주의. T18이 정정된 문구를 고정한다
- 같은 이름이 양쪽에 있어도 토큰 이중 비용은 없다 — 우선순위에서 이긴 쪽 하나만 목록에 등재되고(description 한 줄), 호출 시에도 이긴 쪽 본문만 로드된다
- `--scope user` 는 설치 대상이 곧 전역이므로 비교를 생략한다 (자기 자신과의 비교는 무의미). T19가 고정한다

**미해결 불일치 (기록)**: 사용자 `CLAUDE.md` 는 설계 산출물을 `docs/prps/{기능명}.md` 에 두라고 규정하지만, `/prp-plan` 커맨드는 `.claude/PRPs/plans/` 에 쓴다. 두 규정이 어긋난다. 기존 불일치이며 이번 범위에서 고치지 않았다.

---

---

## 7. 테스트 계획

`tests/` 아래 bash 스크립트. 각 케이스는 임시 디렉토리에서 실행하고 실제 `~/.claude` 를 건드리지 않는다 (`HOME` 을 임시 경로로 치환).

| ID | 케이스 | 검증 |
|----|--------|------|
| T1 | `--scope project` 신규 설치 | `./.claude/rules` 79개, `./.claude/agents` 4개, `./CLAUDE.md` 존재, exit 0 |
| T2 | `--scope user` 신규 설치 | `$HOME/.claude/{rules,agents}` 생성, exit 0 |
| T3 | 멱등성 | 2회 연속 실행 후 `diff -r` 차이 없음, exit 0 |
| T4 | 부분 손상 수복 | `rules/common/testing.md` 삭제 후 재실행 → 79개 복원 |
| T5 | CLAUDE.md 충돌 시 중단 | 기존 CLAUDE.md 내용 **불변**, exit 1, 다른 자산도 변경 없음 |
| T6 | `--force` 백업 | `CLAUDE.md.bak-*` 생성, 백업 내용 == 이전 원본, exit 0 |
| T7 | `--force` 2회 실행 | 백업 파일 **2개** 존재 (타임스탬프로 구분, 서로 덮어쓰지 않음) |
| T8 | `--dry-run` 부작용 0 | 실행 후 대상 디렉토리 미생성, 기존 파일 mtime 불변 |
| T9 | `--scope` 누락 | usage 출력, exit 1, 변경 없음 |
| T10 | 쓰기 권한 없음 | `chmod 500` 대상 → exit 1, **부분 설치 없음** |
| T11 | zh/ 미포함 | 설치 후 `.claude/rules/zh` 부재 |
| T12 | 언어별 조건부 로드 | 설치 후 `python/coding-style.md` 의 `paths:` frontmatter 원형 보존 |
| T13 | 상대경로 참조 보존 | `typescript/coding-style.md` 의 `../common/coding-style.md` 가 설치 후에도 실제 파일을 가리킴 |
| T14 | 심볼릭 링크 대상 | 대상 디렉토리가 symlink일 때 경고 후 중단 |
| T15 | D1 수정 보호 | 관리 파일 수정 후 재실행 → **차이 파일명이 출력**되고 exit 1, 사용자 수정이 **덮어써지지 않음**. `--force` 시 성공 |
| T16 | 소유권 원칙 | 대상에만 있는 파일(사용자 에이전트, `rules/zh/`) 추가 후 재실행 → **충돌 아님(exit 0)** 이며 해당 파일 **보존** |
| T17 | 커맨드 사슬 완결 | 6종 전부 설치 + 설치본이 참조하는 커맨드(`/prp-*`, `/code-review`)가 전부 존재 |
| T18 | 전역 비교 보고 | 가짜 전역(5 동일 + 1 수정)으로 설치 → 다른 것은 `[WARN]` 이름 나열, 동일 5개는 `[INFO]` |
| T19 | user 스코프 비교 생략 | `--scope user` 는 전역 비교 메시지 0건 |

T12·T13은 단순 복사가 frontmatter와 디렉토리 구조를 보존하는지 확인하는 회귀 테스트다. `paths` 가 깨지면 조건부 로드 전체가 무너지므로 사실 1의 안전망이다.

T16은 사실 4의 안전망이다. 이 경계가 무너지면 `--scope user` 가 사용자의 47개 에이전트를 충돌로 오판하거나 삭제한다.

**현재 상태: 19/19 통과** (실행 검증 완료, 실제 `~/.claude` 무손상 확인. bash 3.2/5.x 양쪽 검증)

---

## 8. 리스크

| # | 리스크 | 심각도 | 대응 | 테스트 |
|---|--------|--------|------|--------|
| 1 | `--scope user` 로 사용자의 기존 `~/.claude/rules/` 커스터마이즈 소실 | CRITICAL | **해소** — D1=(B) 확정. 수정된 관리 파일은 차이 목록과 함께 `--force` 요구 (6d) | T15 |
| 1b | `--scope user` 가 관리 대상 아닌 파일(에이전트 47개, `rules/zh/`)을 삭제하거나 충돌로 오판 | CRITICAL | **해소** — 소유권 경계 도입 (사실 4). 소스 기준 `diff -rq` 로만 판정 | T16 |
| 2 | CLAUDE.md 덮어쓰기로 프로젝트 고유 설정 소실 | CRITICAL | 기본 중단 + 타임스탬프 백업 (6c) | T5·T6·T7 |
| 3 | 잘못된 `--scope` 로 의도치 않은 대상에 설치 | HIGH | 기본값 없음, 항상 명시 요구. 대상 절대경로를 실행 전 출력 | T9 |
| 4 | 권한 실패로 부분 설치 | HIGH | `check_preconditions()` 를 모든 쓰기 앞에 배치 | T10 |
| 5 | 대상이 심볼릭 링크(NFS 등)일 때 예상 밖 위치에 기록 | MEDIUM | 감지 후 중단. `cp` 에 `-R` 사용하고 `-L` 을 쓰지 않는다 | T14 |
| 6 | `zh/` 를 제외했으나 기존 설치본이 남아 계속 로드됨 | MEDIUM | 삭제하지 않는다(비목표). README에 수동 제거 안내 | — |
| 7 | `web/` 가 무관한 프로젝트에서도 항상 로드 (28K) | LOW | D2 판단 대기 | — |

---

## 9. 승인 필요 결정사항

| # | 사항 | 선택지 | 권고 | 확정값 |
|---|------|--------|------|--------|
| **D1** | `--scope user` 의 rules/ 덮어쓰기 안전장치 | (A) `~/.claude/rules/` 를 통째로 `rules.bak-<ts>/` 로 백업 후 설치 — 388K 사본이 매번 생김 / (B) 레포와 대상을 `diff -r` 해서 차이 있을 때만 경고하고 `--force` 요구 / (C) 무백업 덮어쓰기 (6d 원안) | **(B)** — 최초 설치는 마찰 없이, 사용자가 손댄 뒤에만 개입한다. 백업 폭증도 없다 | **(B)** diff 감지 후 --force 필요 |
| **D2** | `web/` 7개를 `paths` frontmatter로 조건부화할지 | (A) 그대로 항상 로드 유지 / (B) `paths: ["**/*.{ts,tsx,jsx,css,html,vue,svelte}"]` 추가 — 항상 로드가 72K→44K로 추가 감소 | **(B)** — 단 사용자 원본 자산 수정이므로 승인 없이는 하지 않는다 | **미진행** |
| **D3** | `rules/README.md` 갱신 여부 | (A) 원본 유지 / (B) `paths` 조건부 로드 동작과 새 install.sh 사용법으로 갱신 | **(B)** — 현재 README는 언어별 선택 복사를 안내하는데 `paths` 도입으로 무효가 된 서술이다 | **진행** |
| **D4** | `code-reviewer.md` 폴백 문구 추가 | (A) 원본 유지 / (B) "`/code-review` 스킬 미설치 시 rules/common/code-review.md 체크리스트로 검수" 추가 | **(B)** — (e) 근거 | **진행** |
| **D5** | 레포 git 초기화 및 원격 | (A) 로컬 git init 만 / (B) GitHub 원격까지 생성 (public/private?) | 판단 필요 — 사내 자산 포함 여부와 연동 | **(A)** 로컬 git init 만 |

D1은 CRITICAL 리스크와 직결되므로 **확정 없이는 구현에 착수하지 않는다.** D2~D4는 사용자 원본 자산을 수정하는 항목이라 별도 승인이 필요하다.

---

### 구현 검수 (code-review · destruction)

#### code-review 지적 반영

| 지적 | 심각도 | 상태 |
|------|--------|------|
| install.sh main() 48줄 > 30줄 | HIGH | ✓ 반영 — perform_installation() + log_installation_plan() 분리 |
| install.sh install_directory() 40줄 > 30줄 | HIGH | ✓ 반영 — detect_user_conflict() 분리 |
| install.sh check_preconditions() 32줄 > 30줄 | HIGH | ✓ 반영 — check_claude_md_conflict() 분리 |
| 축약명 src_dir, tgt_dir, src_hash, tgt_hash | MEDIUM | ✓ 반영 — 전부 명확히 (source_directory, target_directory, source_file_hash, target_file_hash) |
| 매직 숫자 82, 78, 4 | MEDIUM | ✓ 반영 — 상수화 (RULES_FILE_COUNT, AGENTS_FILE_COUNT, EXPECTED_TOTAL_FILES) |
| tests/run.sh main() 62줄 > 30줄 | MEDIUM | ✓ 반영 — register_and_run_tests() + print_test_summary() 분리 |
| xargs echo 목적 불명확 | MEDIUM | ✓ 반영 — "Trim whitespace from wc output" 주석 추가 |
| 파일 개수 동적 계산 DRY | MEDIUM | ✓ 부분 반영 — 상수화로 싱크 개선 (전체 동적 계산은 추가 복잡도) |

#### destruction 지적 반영

| ID | 심각도 | 경로 | 상태 |
|----|--------|------|------|
| D1 | HIGH | cp -R 병합 동작 | ✓ 반영 — D1=(B) 구현: diff 감지 + --force 요구 |
| D2 | HIGH | 부분 설치 (rules OK, agents 실패) | ✓ 반영 — T4 & T15 테스트로 검증 완료 |
| D3 | MEDIUM | 백업 파일명 충돌 (같은 초) | ✓ 반영 — 타임스탐프에 나노초(%N) 추가 |
| D4 | MEDIUM | --dry-run 시 check 스킵 | ⊘ 의도적 미반영 — PRP 스펙상 --dry-run은 정보용 (부작용 없음) |
| D5 | LOW | trap 빈 값 | 확인 — 안전함 (set -euo pipefail 보호) |

#### 실행 검증에서 뒤집힌 결론 (rev2 최종)

위 검수 반영 직후의 자체 보고는 "14/15 통과, T10은 bash 환경 차이로 미해결" 이었다. **이 진단은 틀렸다.** 테스트를 실제로 실행하고 T10을 손으로 재현한 결과 CRITICAL 결함이 드러났다.

재현 결과 (`chmod 500` 대상에 `--scope project`):
```
mkdir: .../.claude: Permission denied
cp:    .../.claude/rules: No such file or directory
[OK]   rules/  0개 파일 → ...      ← 0개인데 성공 보고
cp:    .../CLAUDE.md: Permission denied
[OK]   CLAUDE.md → ...              ← 실패인데 성공 보고
[DONE] 1개 파일 설치 완료            ← 아무것도 안 됐는데 완료
exit = 0                             ← 전부 실패인데 성공
```

| # | 결함 | 심각도 | 원인 | 수정 |
|---|------|--------|------|------|
| E1 | 쓰기 권한 검사가 발동하지 않음 | **CRITICAL** | `[[ -d "$target_base" && ! -w ... ]]` — `.claude/` 가 없으면 검사를 건너뛴다. 정작 쓰기 불가인 `$PWD` 는 검사 대상이 아니었다 | `find_existing_ancestor()` 로 **존재하는 최상위 조상**의 쓰기 권한을 검사 |
| E2 | `mkdir`·`cp` 실패를 검사하지 않음 | **CRITICAL** | `set -e` 는 **조건문에서 호출된 함수 내부에 적용되지 않는다**(`if ! install_directory …`). `set -euo pipefail` 이 있어도 무력 | `copy_directory_contents()` 에서 각 명령의 반환값을 명시적으로 검사 |
| E3 | 파일 개수를 세고도 대조하지 않음 | HIGH | `RULES_FILE_COUNT` 상수가 dry-run 문구에만 쓰이는 죽은 코드였다 | `verify_managed_files_installed()` 로 설치 후 소스 기준 누락·차이 0 검증 |
| E4 | D1 차이 파일 목록 미출력 (스펙 미구현) | HIGH | `detect_user_conflict()` 가 `diff` 결과를 계산하고 버렸다 | `report_directory_differences()` 로 파일명 출력 (최대 20건 + "…외 N건") |
| E5 | 누락 복원 후에도 "변경 없음" 출력 | MEDIUM | 복사를 수행했는데 거짓 보고 | `N개 갱신 (관리 대상 M개)` 로 구분 |
| E6 | 파일 개수 대조가 사용자 환경에서 항상 실패 | **CRITICAL** | E3 수정안이 "대상 파일 수 == 78/4" 를 요구했다. 사용자의 `~/.claude/agents/` 는 51개다 → `--scope user --force` 가 항상 실패 | 사실 4 소유권 경계 도입. 개수 대조를 폐기하고 소스 기준 `diff -rq` 로 전환. T16 신설 |

E1·E2는 사용자 `rules/common/coding-style.md` 의 **"Never silently swallow errors"** 직접 위반이었다. E6은 E3 수정 과정에서 새로 만든 결함이며, 실제 머신 상태(에이전트 51개, `rules/zh/` 11개)를 시뮬레이션해서 잡았다.

**최종: 16/16 통과.** 실행 전후 `~/.claude` 지문 대조로 무손상 확인 (CLAUDE.md sha256 불변, rules 89개, agents 51개).

**교훈**: 실패한 테스트를 "환경 차이"로 분류하기 전에 손으로 재현해야 한다. 이 건에서는 그 한 줄이 CRITICAL 결함 2개를 덮고 있었다.

---

## 검수 이력

### rev1 적대적 검수 (3렌즈)

| 검수자 | 지적 | 반영 |
|--------|------|------|
| destruction-risk | CLAUDE.md 무방비 덮어쓰기 | 반영 — 기본 중단 + 실제 파일 백업 (rev1의 "해시를 로그에 남김"은 복구 불가라 폐기) |
| destruction-risk | 백업이 백업을 덮어쓸 위험 | 반영 — 백업명에 타임스탬프, T7로 검증 |
| destruction-risk | 부분 실패 복구 불가 | 반영 — 단 상태 파일 대신 "벤더링 자산 전량 덮어쓰기 + 재실행" 으로 해소 (§4) |
| destruction-risk | dry-run 부작용 | 해소 — 상태 파일 자체를 없애 원천 제거 |
| destruction-risk | 권한 에러 시 부분 적용 | 반영 — `check_preconditions()` 를 쓰기 앞에 배치, T10 |
| destruction-risk | 심볼릭 링크 추종 | 반영 — 리스크 5, T14 |
| destruction-risk | `--scope` 혼재 | 부분 반영 — rev1의 `.scope` 추적 파일은 YAGNI로 폐기, 기본값 없음 + 대상 경로 출력으로 대체 |
| spec-conformance | `plugin.json` 의 agents 필드는 지원됨 | 반영 — 사실 3 |
| spec-conformance | rules 자동 로드 서술 오류 | **재정정** — 검수자는 "전량 자동 로드"로 고쳤으나 이것도 틀렸다. 사실 1 참조 |
| spec-conformance | `@import` 미언급 | 반영 — 단 CLAUDE.md 전용이므로 rules에는 쓰지 않기로 결정 (6b) |
| spec-conformance | `./.claude/agents` 미검증 | 해소 — 공식 문서로 확인, rev1의 T11 리스크 삭제 |
| user-standards | JSON 매니페스트 과설계 | 반영 — 연관 배열까지 전부 폐기 (§4) |
| user-standards | `.install-state` 복잡 | 반영 — 파일 자체 삭제 |
| user-standards | 플래그 과다 | 반영 — 4개만 유지 |
| user-standards | exit 코드 과다 | 반영 — 0/1 |

### rev1 → rev2 사후 검증에서 정정된 것

| 항목 | rev1 | rev2 |
|------|------|------|
| rules 로드 방식 | "모든 .md 자동 로드" | 29개만 항상 로드, 60개는 `paths` 조건부 (사실 1) |
| 언어 선택 설치 | `[LANG ...]` 인자로 선택 | **폐기** — `paths` 와 중복 |
| 데이터 모델 | `ASSET_SOURCES`/`ASSET_DEPS` 연관 배열 + 상태 파일 | 변수 4개 |
| `zh/` | `--lang zh` 로 선택 가능 | 배포 제외 — 항상 로드되는 순중복 44K |
| CLAUDE.md 백업 | 해시를 로그에 기록 | 타임스탬프 백업 파일 |
| 프로젝트 agents | 미검증(T11 CRITICAL) | 공식 지원 확인 |
| 예상 규모 | 80줄 | 100줄 이내 (테스트 14케이스 별도) |

---

**설계**: design-architect (rev1) + 사후 실측 정정 (rev2)
**상태**: 승인 대기 — **D1 확정 전 구현 착수 금지**
**다음 단계**: D1~D5 확정 → implementer 가 install.sh + tests/ 구현 → code-reviewer 검수
