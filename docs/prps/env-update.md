# PRP: coding-env 동적 업데이트 커맨드 (`env-update`)

**작성일**: 2026-07-31  
**분류**: 전체 경로 (설계 → 구현 → 검수)  
**상태**: 설계 - 검토 대기

---

## 0. 요구사항 요약

사용자가 coding-env 레포를 업데이트하면, 기존에 설치된 프로젝트/전역 환경이 자동으로 최신화되기를 원한다.  
**`env-update` 커맨드는**:
1. 이전 설치 때 저장된 **레포 경로와 scope**를 확인
2. 그 **레포의 최신 변경 사항을 자동 fetch**하고 
3. 변경이 있으면 **사용자 확인 후** `install.sh` 를 기존 scope와 동일하게 재실행한다

비목표:
- 자동 `--force` 강제 적용 (충돌 시 사용자 확인)
- 대상 디렉토리에서 **삭제된 배포 파일 정리** (v1 스코프 초과, v2 예정)
- 여러 scope 혼재 관리 (프로젝트 + 전역이 모두 설치된 경우, 각 scope별로 독립 실행)

---

## 1. 핵심 설계 결정

### 1.1 설치 정보 추적 방식: Manifest 파일 (설치 시점 기록)

**문제**: env-update 커맨드가 실행될 때, 어느 레포에서 설치되었고, project/user 중 어느 scope였는지 어떻게 아는가?

**검토 대안**:

| 접근법 | 장점 | 단점 | 결정 |
|--------|------|------|------|
| **Manifest 파일** (`.claude/.coding-env.json`) | 신뢰할 수 있는 단일 정보원; 설치 시점에 정확히 기록; 사용자가 필요시 수동 편집 가능 | install.sh 수정 필요; 파일 추가 | ✅ **선택** |
| 탐색 기반 (`.git/config` 내 origin URL 파싱 등) | install.sh 수정 없음 | 레포가 git이 아닌 경우(zip 다운로드) 실패; git 구조에 의존; 신뢰성 낮음 | ✗ 제외 |
| 대화형 입력 (매번 경로 물어보기) | 유연함 | 사용성 나쁨; 오류 가능성 높음 | ✗ 제외 |

**근거**: coding-env는 배포 패키지이며, install.sh가 이미 설치를 관리한다. manifest를 여기서 함께 기록하는 것이 가장 신뢰할 수 있다.

### 1.2 Manifest 스키마

**파일 위치**: `.claude/.coding-env.json` (project 또는 user scope에 따라)
- project scope: `$PWD/.claude/.coding-env.json`
- user scope: `$HOME/.claude/.coding-env.json`

**선택 근거**: 
- 이미 `.claude/` 아래 rules/agents/commands가 있으므로, 설치 관련 메타데이터도 여기 배치하는 게 자연스럼
- `settings.json`/`settings.local.json` 등 다른 Claude Code 예약 파일과 명확히 구분
- 점 접두사 (`.coding-env.json`)로 숨김 파일 취급 (선택적)

**스키마** (JSON, 배포되지 않는 런타임 파일):

```json
{
  "version": 1,
  "repo_path": "/absolute/path/to/coding-env",
  "scope": "project",
  "installed_at": "2026-07-31T10:30:00Z",
  "installed_from_commit": "abc1234def5678",
  "target_base_dir": "/absolute/path/to/target/dir",
  "files_count": {
    "CLAUDE_md": 1,
    "rules": 37,
    "agents": 4,
    "commands": 6
  }
}
```

**스키마 상세**:
- `version`: manifest 스키마 버전 (향후 호환성 관리용)
- `repo_path`: coding-env 레포의 절대 경로 (설치 시 install.sh가 `$REPO_ROOT`로부터 자동 계산)
- `scope`: `"project"` 또는 `"user"`
- `installed_at`: ISO 8601 타임스탬프 (설치 시점 기록)
- `installed_from_commit`: 설치 시점 coding-env 레포의 HEAD 커밋 해시 (변경 감지용)
- `target_base_dir`: 설치 대상의 기본 디렉토리 (`$PWD` 또는 `$HOME`)
- `files_count`: 설치 당시 배포된 파일 개수 (v1.0 기준: rules 37개 등, 향후 갱신됨)

### 1.3 Manifest가 없는 기존 설치 대응 (Fallback)

문제: env-update 기능 이전에 설치한 사용자는 manifest가 없다.

**정책**:
1. manifest 파일 없음 감지 시, 대화형 프롬프트로 사용자에게 물어보기:
   ```
   [INFO] Install manifest not found. Please provide the coding-env repo path:
   Enter path: /path/to/coding-env (or 'skip' to abort)
   ```
2. 사용자가 경로 입력 → 그 경로 사용
3. 사용자가 `skip` 또는 `Ctrl+C` → 중단 (manifest 생성 안 함)
4. 이 경우 사용자는 `install.sh --scope project|user` 를 직접 재실행하거나, 경로를 기억했다면 `env-update` 재실행 가능

**선택 근거**: 
- 자동 레포 탐색은 신뢰할 수 없음 (위 1.1 참조)
- manifest 없는 설치는 이미 레포에 대한 정보를 모르므로, 사용자 입력이 필수
- 첫 실행 시만 이 프롬프트가 뜨고, manifest 생성 후 다음 실행부터는 자동 진행

### 1.4 양쪽 scope에 모두 설치된 경우

문제: 어떤 프로젝트에 project scope로 설치했으면서, 동시에 전역에도 user scope로 설치한 경우?

**정책**:
- env-update는 **현재 실행 위치**에서 manifest를 찾는다
- **프로젝트 디렉토리에서** 실행 → 프로젝트 scope manifest 찾아 project 대상 갱신
- **프로젝트 외 위치에서** 실행 → user scope manifest 찾아 user 대상 갱신
- 양쪽이 필요하면 각 위치에서 별도로 `env-update` 실행

**선택 근거**:
- 명확한 우선순위 (위치 기반)
- 사용자가 한 곳에서만 주로 작업하고, 필요시 다른 scope도 업데이트 가능
- 복잡한 "모두 동시에" 로직을 피함 (YAGNI)

### 1.5 레포 최신화 절차 (git fetch & pull)

**흐름**:

1. **Manifest에서 repo_path 읽기** → manifest 검증 (버전, 필드 완결성)
2. **레포 상태 확인**:
   ```bash
   cd "$repo_path"
   git status → 전체 상태 파악
   ```
   - git 레포가 아니면? → ERROR: "Not a git repository"
   - dirty (tracked 파일 수정) → WARN: "Repo has uncommitted changes" 경고 후 계속 (사용자가 명시적으로 계속 선택)
   - detached HEAD? → WARN: "Detached HEAD" 경고 후 계속
3. **원격 최신 정보 fetch**:
   ```bash
   git fetch origin
   ```
   네트워크 실패 → ERROR: "Failed to fetch from origin"
4. **변경 감지** (현재 브랜치의 upstream `@{u}` 기준 — origin/main 하드코딩 금지, fork·다른 기본 브랜치에도 안전):
   ```bash
   git rev-parse --abbrev-ref '@{u}'    # upstream 미설정이면 실패 → ERROR 중단
   git log --oneline '@{u}..HEAD'       # Local에만 있는 커밋
   git log --oneline 'HEAD..@{u}'       # Upstream에만 있는 커밋 (새 버전)
   ```
   - 새 버전 있음 (뒤로 떨어짐) → 사용자 확인: "upstream has X new commits. Proceed?" (Y/N)
   - 새 버전 없음 → INFO: "Already up to date" → 종료
   - diverged (양쪽 모두 새 커밋) → WARN: "Branches have diverged" → 중단, 수동 해결 필요
   - upstream 미설정 (tracking branch 없음) → ERROR: 중단, `git branch --set-upstream-to` 안내
5. **병합 또는 fast-forward**:
   ```bash
   git pull --ff-only
   ```
   - 인자 없는 `git pull --ff-only`: 현재 브랜치의 upstream에서 직선 진행 (rebase 같은 복잡한 머지 피함)
   - 실패하면 (merge conflict) → ERROR: "Pull failed. Please resolve manually"
6. **설치 재실행**:
   ```bash
   "$repo_path/install.sh" --scope "$scope"
   ```
   - `--force` 플래그는 기본 미적용
   - 충돌 발생 시 사용자에게 `--force` 여부 확인

**에러 처리**:

| 상황 | 처리 |
|------|------|
| Manifest 파일 없음 | 대화형 입력 (fallback, §1.3) |
| git 레포 아님 | ERROR: 중단 |
| 네트워크 실패 (fetch) | ERROR: 중단 |
| Diverged branches | ERROR: 수동 해결 필요 |
| Merge conflict | ERROR: 수동 해결 필요 |
| install.sh 실패 (diff 충돌) | WARN 후 사용자에게 `--force` 여부 확인 |

---

## 2. 영향 범위

### 2.1 수정 파일

| 파일 | 변경 | 이유 |
|------|------|------|
| `install.sh` | **manifest 기록 추가** | env-update가 읽을 정보를 설치 후 JSON으로 저장 |
| `commands/env-update.md` | **신규 파일** | 커맨드 문서 (markdown 프롬프트) |
| `tests/run.sh` | **테스트 케이스 3~5개 추가** | manifest 생성, fallback, 정상 업데이트 등 |
| `README.md` | **usage 섹션 추가** | env-update 사용법 |
| `docs/prps/env-update.md` | 이 문서 | 설계 문서 |

### 2.2 신규 배포 파일 추가에 따른 상수 갱신

env-update.md 는 배포 대상 커맨드이므로 커맨드 개수 상수가 늘어난다:

```bash
# install.sh 라인 12-14
readonly RULES_FILE_COUNT=37      # (변화 없음)
readonly AGENTS_FILE_COUNT=4      # (변화 없음)
readonly COMMANDS_FILE_COUNT=7    # 기존 6 + env-update 1
```

| 커맨드 | 상태 |
|--------|------|
| prp-prd, prp-plan, prp-implement, prp-pr, prp-commit, code-review | 기존 6개 |
| **env-update** | **신규 추가** |

### 2.3 구조 변화 요약

```diff
commands/
├── prp-prd.md
├── prp-plan.md
├── prp-implement.md
├── prp-pr.md
├── prp-commit.md
├── code-review.md
+ └── env-update.md            # 신규, ~150줄 추정
```

### 2.4 런타임 파일 (배포 대상 아님)

설치된 대상 디렉토리에만 생성:
```
.claude/
├── .coding-env.json           # ← 신규, manifest (배포 X, 자동 생성)
├── rules/
├── agents/
└── commands/
```

---

## 3. 데이터 모델

### 3.1 Manifest 파일 (`.coding-env.json`)

**타입 정의** (TypeScript 스타일):

```typescript
interface InstallManifest {
  version: number;                    // 1
  repo_path: string;                  // Absolute path
  scope: "project" | "user";
  installed_at: string;               // ISO 8601
  installed_from_commit: string;       // git commit hash (12~40 chars)
  target_base_dir: string;            // $PWD or $HOME
  files_count: {
    CLAUDE_md: number;                // 1
    rules: number;                    // 37
    agents: number;                   // 4
    commands: number;                 // 7 (after env-update added)
  };
}
```

**검증**:
- `version` == 1 (스키마 호환성)
- `repo_path` 존재하고 git 레포 여부 확인
- `scope` ∈ { "project", "user" }
- `installed_at` 유효한 ISO 8601
- `installed_from_commit` 유효한 git hash 형식
- `files_count` 모든 필드 >= 0

---

## 4. 인터페이스

### 4.1 커맨드 호출

**위치**: `$PWD` (대상 프로젝트) 또는 시스템 어디든
**호출**: `/env-update` (Claude Code 커맨드 모드)
**입력**: 없음 (대화형이거나 manifest 기반 자동)
**출력**: 설치 진행 상황 + 결과 보고

### 4.2 env-update.md 커맨드 스펙 (마크다운 프롬프트)

**파일 형식**: `commands/env-update.md` (기존 커맨드 형식 따름, 예: prp-commit.md)

**주요 단계** (pseudo-code):

```
Phase 1. FIND MANIFEST
  - Look for .claude/.coding-env.json (project) or ~/.claude/.coding-env.json (user)
  - If not found → Interactive: ask user for repo path (fallback §1.3)
  - Validate manifest (schema check, repo_path exists, git status)

Phase 2. FETCH & DETECT
  - cd "$repo_path"
  - Check git status (warn if dirty/detached, but continue)
  - Resolve upstream: git rev-parse --abbrev-ref '@{u}' (미설정이면 Error → Exit)
  - git fetch origin
  - Compare HEAD vs '@{u}' (git log --oneline)
  - If up-to-date → Report "Already up to date" → Exit
  - If new commits exist → Ask user "Proceed with update?" (Y/N)
  - If diverged → Error: "Branches diverged. Please resolve manually" → Exit

Phase 3. PULL
  - git pull --ff-only
  - If conflict → Error + guidance → Exit
  - Report commits pulled

Phase 4. REINSTALL
  - project scope: cd "$target_base_dir" 후 "$repo_path/install.sh" --scope project
    (install.sh --scope project 는 $PWD 를 대상 삼으므로 반드시 대상 디렉토리에서 실행)
  - user scope: 실행 위치 무관 "$repo_path/install.sh" --scope user
  - If exit 0 → Success report
  - If exit 1 (conflict) → Warn "Install.sh reported conflicts" + 
    Ask user "--force?" (Y/N) →
    "$repo_path/install.sh" --scope "$scope" --force

Phase 5. VERIFY MANIFEST
  - install.sh 가 설치 성공 시 manifest 를 재기록하므로 env-update 는 별도로 쓰지 않는다
    (단일 기록 주체 원칙: manifest 의 writer 는 install.sh 하나)
  - .coding-env.json 의 installed_from_commit 이 새 HEAD 와 일치하는지 검증 후 완료 보고
```

### 4.3 사용자 인터페이스 메시지 (예상)

```
[INFO] Looking for install manifest...
[OK] Found: /path/to/project/.claude/.coding-env.json
[INFO] Checking upstream changes...
[OK] Fetched origin/main
[INFO] Local: abc1234 (2026-07-30 12:00)
[INFO] Remote: def5678 (2026-07-31 09:30)
[INFO] Remote has 3 new commits. Proceed? (y/n)
> y
[INFO] Pulling changes...
[OK] Merged 3 commits
[INFO] Running install.sh --scope project...
[OK] rules/ 37개 파일 → 변경 없음
[OK] agents/ 4개 파일 → 2개 갱신
[OK] CLAUDE.md → 변경 없음
[DONE] Updated successfully
[OK] Manifest updated: installed_from_commit = def5678
```

---

## 5. 파일 구조 및 모듈 경계

```
coding-env/
├── install.sh                    # 수정: manifest 기록 추가
├── commands/
│   └── env-update.md            # 신규: 커맨드 프롬프트 (~150줄)
├── tests/
│   └── run.sh                   # 수정: 테스트 케이스 추가 (T20~T24)
├── docs/
│   └── prps/
│       ├── coding-env.md        # (변화 없음)
│       └── env-update.md        # 신규: 이 문서
└── README.md                     # 수정: env-update 사용법 추가
```

---

## 6. 설계 결정과 근거

### 6.1 Manifest 파일 방식 (vs 탐색, vs 대화형)

**근거**: 
- coding-env는 install.sh가 이미 설치 시점을 관리한다
- 그 시점에 메타데이터를 JSON으로 기록하는 것이 가장 신뢰할 수 있다
- 사용자가 필요시 수동 편집 가능 (투명성)
- git이 아닌 설치 방식(zip 다운로드 등)도 지원하려면 manifest가 필수

### 6.2 Fallback: 대화형 입력

**근거**:
- env-update 기능 이전의 기존 사용자는 manifest가 없다
- 자동 탐색은 신뢰할 수 없다 (git 아님, diverged 등)
- 사용자 입력이 유일한 신뢰할 수 있는 출처
- 첫 실행 시만 프롬프트, 이후 자동

### 6.3 각 scope 독립 실행 (vs 동시 관리)

**근거**:
- 프로젝트 + 전역 동시 설치는 드문 시나리오
- 각 manifest를 독립적으로 관리하는 게 간단하고 명확
- 사용자가 필요시 각 위치에서 수동으로 실행 가능 (YAGNI)

### 6.4 `--ff-only` pull (vs rebase vs merge)

**근거**:
- coding-env는 배포 패키지이므로 linear history 유지
- 사용자가 install.sh 후에 manifest를 수정할 일은 없음
- diverged 상황은 드물고, 나면 수동 해결 필요
- `--ff-only`는 가장 안전한 자동화

### 6.5 install.sh 기존 `--force` 플래그 미사용

**근거**:
- 사용자가 로컬에서 rules/agents를 수정했을 가능성 있음
- 자동 `--force` 강제는 사용자 수정을 무시하므로 위험
- 명시적 확인을 받은 후에만 `--force` 사용
- 혹시 CLAUDE.md 충돌도 비슷하게 처리 (묻고 진행)

---

## 7. 테스트 계획

### 7.1 신규 테스트 케이스 (tests/run.sh)

| 테스트 | 항목 | 예상 |
|--------|------|------|
| **T20** | Manifest 생성 확인 | install.sh --scope project 후 ./.claude/.coding-env.json 존재 |
| **T21** | Manifest 스키마 검증 | jq로 JSON 파싱, version/repo_path/scope 필드 확인 |
| **T22** | env-update fallback (manifest 없음) | 대화형 입력 시뮬레이션 (echo | env-update 형태 또는 별도 테스트) |
| **T23** | 레포 최신화 감지 | manifest 기반 재설치 시나리오 (별도 git 레포 생성) |
| **T24** | install.sh --force 재실행 | diff 충돌 후 --force로 성공 |

**테스트 세팅 복잡도**: T23/T24는 별도 git 레포를 생성하고 커밋해야 하므로, 
반영하지 않거나 별도 통합 테스트 스크립트로 분리 고려

### 7.2 테스트 케이스 상세

```bash
# T20: Manifest 생성 및 내용 검증
test_manifest_created_after_install() {
  sandbox=$(mktemp -d)
  cd "$sandbox"
  "$INSTALL_SCRIPT" --scope project > /dev/null 2>&1
  
  # Manifest 존재 확인
  assert_file_exists "./.claude/.coding-env.json" "manifest"
  
  # Manifest 파싱 검증 (jq 사용)
  local manifest
  manifest=$(cat ./.claude/.coding-env.json)
  assert_contains "$manifest" '"version":1' "version field"
  assert_contains "$manifest" '"scope":"project"' "scope"
  assert_contains "$manifest" '"repo_path"' "repo_path"
  
  log_ok "T20 통과"
}

# T21: Manifest 필드 완결성
test_manifest_fields_complete() {
  # ... (T20과 유사, 모든 필드 검증)
}

# T22: Fallback (manifest 없음, 대화형 입력)
# → 복잡하므로 수동 테스트 또는 별도 스크립트로 분리 권장

# T23/T24: env-update 자체는 커맨드 실행이므로, 
# 이 repo의 unit tests에서는 manifest 생성만 검증하고,
# env-update 동작은 integration test (별도) 또는 수동으로 검증
```

### 7.3 통합 테스트 계획 (별도 문서 또는 수동)

env-update 커맨드 자체의 동작(git fetch, pull, install.sh 재실행)은 
테스트가 복잡하므로 (git 레포 생성 필요), 
아래 시나리오를 수동 또는 CI 통합 테스트로 검증:

1. **Manifest 기반 레포 탐색 성공**
   - env-update 실행 → manifest 읽기 → 레포 경로 확인 성공
2. **No-op (up-to-date)**
   - env-update 실행 → git fetch → "Already up to date" 메시지
3. **New commits 감지 → pull → install.sh 재실행**
   - 별도 git 레포에 새 커밋 추가 → env-update → pull 성공 → install.sh 재실행 확인
4. **Dirty repo warning**
   - 레포 수정 후 env-update → warning 출력 후 계속 (또는 계속? 중단?)
5. **install.sh conflict → --force 확인**
   - 로컬 rules 수정 후 env-update → diff 충돌 → --force 여부 묻기

---

## 8. 에러 처리 및 엣지 케이스

### 8.1 기본 에러 처리

| 상황 | 행동 | 메시지 |
|------|------|--------|
| Manifest 파일 없음 | Fallback: 대화형 입력 | `[INFO] Install manifest not found...` |
| git 레포 아님 | 에러 중단 | `[ERROR] Not a git repository: /path` |
| fetch 실패 (네트워크) | 에러 중단 | `[ERROR] Failed to fetch origin` |
| Branches diverged | 에러 중단 | `[ERROR] Branches have diverged. Manual resolution required.` |
| Merge conflict (pull) | 에러 중단 | `[ERROR] Pull failed with conflicts. Please resolve manually.` |
| install.sh 실패 (diff) | Warn → 사용자 확인 | `[WARN] Install reported conflicts. Use --force? (y/n)` |
| Detached HEAD | Warn 후 계속 | `[WARN] Repository is in detached HEAD state.` |
| Dirty working tree | Warn 후 계속 | `[WARN] Working tree has uncommitted changes.` |

### 8.2 흐름 제어

**사용자 확인이 필요한 시점**:
1. Fallback: 레포 경로 입력 (manifest 없을 때)
2. New commits detected: "Proceed with update?" (Y/N)
3. install.sh conflict: "--force?" (Y/N)

**계속하지 않는 경우 (사용자 선택)**:
- "Proceed?" → N 선택 → 중단 (update 수행 안 함, 종료 0)
- "--force?" → N 선택 → manifest만 갱신 안 함, 종료 1 (실패)

---

## 9. 리스크와 대안

### 9.1 리스크 1: Manifest 손상 (사용자 실수)

**상황**: 사용자가 `.coding-env.json`을 실수로 수정 또는 삭제

**대응**:
- 파일 없음 → fallback (대화형)
- 파일 손상 (JSON 파싱 실패) → 에러 메시지 + fallback 안내
- 필드 누락 → 각 필드 검증, 누락하면 에러 + 복구 방법 안내

**선택**: Manifest를 중요 자산으로 취급하지만, 언제든 재생성 가능하도록 fallback 제공

### 9.2 리스크 2: 여러 scope에서 동시 env-update

**상황**: 프로젝트와 전역 둘 다 설치되어 있고, 동시에 env-update 호출

**현재 정책**: 각 위치에서 독립 실행 (manifest도 독립)
**문제 가능성**: 낮음 (사용자가 의도적으로 각 위치에서 실행해야 함)
**선택**: 현재 정책 유지 (YAGNI)

### 9.3 리스크 3: install.sh 변경으로 manifest 스키마가 바뀜

**상황**: 향후 install.sh가 진화해 manifest 포맷이 바뀜

**대응**:
- `version` 필드로 호환성 관리
- v1 → v2 migration 필요시 env-update에서 처리
- 현재: version == 1 체크, 다르면 에러

**선택**: 스키마 진화를 고려해 `version` 필드 필수 포함

### 9.4 대안 1: Git 기반 탐색 (선택하지 않음)

**아이디어**: `.git/config` 의 origin URL에서 coding-env 레포 경로 추론

**문제**:
- coding-env를 zip 다운로드한 경우 `.git` 없음
- origin이 fork라면? (사용자 개인 fork일 가능성)
- 신뢰성 낮음

**선택**: 명시적 manifest가 더 신뢰할 수 있음

### 9.5 대안 2: 자동 `--force` (선택하지 않음)

**아이디어**: env-update 실행 시 항상 `--force` 사용해 빠르게 진행

**문제**:
- 사용자 로컬 수정이 손실될 수 있음 (위험)
- 사용자가 rules를 custom하게 수정한 경우 덮어써짐

**선택**: 사용자 확인 필수 (안전함)

### 9.6 대안 3: 삭제된 파일 정리 (v1에서 제외)

**아이디어**: Manifest에 설치 파일 목록을 기록, 
향후 레포에서 파일이 제거되면 대상에서도 삭제

**문제**:
- manifest에 전체 파일 목록 저장 → 스키마 복잡
- 사용자가 레포 언어를 다시 선택해서 파일이 줄어든 경우? (의도된 축소)
- "파일 삭제" 는 위험도 높음 (실수 시 복구 불가)

**선택**: v1에서는 제외, v2 이상에서 검토
- 대신: 설치 당시 파일 개수를 manifest에 기록해, v2에서는 "예전에 X개 있었는데 지금 Y개"라고 안내 가능

---

## 10. 구현 단계별 검증

### Phase 1: manifest 기록 추가 (install.sh)
- [ ] install.sh 완료 후 `.coding-env.json` 생성
- [ ] manifest 필드 검증
- [ ] T20: manifest 존재 확인
- [ ] T21: manifest 필드 완결성

### Phase 2: env-update.md 커맨드 작성
- [ ] 마크다운 프롬프트 작성 (~150줄)
- [ ] manifest 읽기 및 검증
- [ ] git fetch & pull 로직
- [ ] install.sh 재실행
- [ ] 에러 처리 (모든 경로)

### Phase 3: 통합 테스트
- [ ] 수동 테스트: 기본 flow (manifest 있음 → up-to-date)
- [ ] 수동 테스트: new commits → pull → reinstall
- [ ] 수동 테스트: fallback (manifest 없음)
- [ ] 수동 테스트: diff 충돌 → --force

### Phase 4: 문서 및 상수 갱신
- [ ] README.md: env-update 사용법 추가
- [ ] COMMANDS_FILE_COUNT 6 → 7
- [ ] tests/run.sh: T20, T21 추가 (T22~T24는 통합 테스트로 분리)

---

## 11. 문서 갱신 계획

| 파일 | 변경 |
|------|------|
| `README.md` | env-update 사용법 섹션 추가 (기본 사용, 주의사항) |
| `docs/prps/coding-env.md` | 상수 갱신 (COMMANDS_FILE_COUNT 7) |

**README.md 추가 예상 내용**:
```markdown
## 환경 업데이트

기존에 설치한 coding-env를 최신 버전으로 업데이트합니다.

### 기본 사용법

설치된 프로젝트 또는 전역 디렉토리 어디에서든:

```bash
/env-update
```

### 동작

1. 이전 설치 정보(레포 경로, scope) 확인
2. 코딩 환경 레포에서 최신 커밋 확인
3. 변경 있으면 사용자 확인 후 pull
4. install.sh 재실행으로 rules/agents/commands 갱신
5. manifest 갱신

### 주의

- 레포가 dirty(수정됨) 상태면 경고 후 계속 진행
- install.sh 실행 중 로컬 수정 파일 충돌 발생 시 --force 여부 확인
- 여러 scope(project + user) 설치 시 각각 실행 필요
```

---

## 12. 핵심 설계 결정 요약 (3줄)

1. **Manifest JSON 방식**: install.sh가 설치 완료 후 `.claude/.coding-env.json`에 레포 경로·scope·커밋 해시를 기록 → env-update가 읽어서 자동 갱신 대상 파악
2. **각 scope 독립 실행**: 프로젝트와 전역 manifest를 별도로 관리, 각 위치에서 독립 실행 (간단성 + 명확성)
3. **사용자 명시적 확인**: new commits 감지 시, install.sh 충돌 시 각각 사용자에게 진행 여부/강제 여부를 묻기 (안전성)
