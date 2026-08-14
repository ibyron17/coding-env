---
description: "모든 프로젝트의 세션 진행 상황을 한 페이지에서 읽기 전용으로 보는 통합 허브 — 상주 서버 제어/훅 설치"
argument-hint: "[install|off|status|server start|server stop|server restart|server status|statusline on|statusline off]"
---

# Hub

> 로컬에서 돌고 있는 **모든 Claude Code 프로젝트**의 진행 상황(프로젝트/세션/단계)을 한 페이지에서
> **읽기 전용**으로 본다. 명령·제어 기능은 범위 밖이다. 이 커맨드는 **얇다** — 아래 python3
> 서브커맨드를 부르고 결과를 보고하는 것 말고는 판단하지 않는다. 설명·설정·프라이버시 고지
> 전부는 [`hub/README.md`](../../hub/README.md), 설계 근거는
> [`docs/prps/hub-dashboard.md`](../../docs/prps/hub-dashboard.md)에 있다.

**`/dashboard` 와 반대 방향이다.** `/dashboard` 는 LLM 만 아는 사실을 오케스트레이터가 직접 쓴다.
`/hub` 는 파일에서 기계적으로 읽히는 사실만 집계하므로 코드가 하고, 이 문서는 그 코드를 부르는
절차만 담는다.

---

## 사전 조건 — 허브는 coding-env 설치와 분리돼 있다

`~/.claude/hub/bin/hub.py` 가 없으면 아래 절차로 안내하고 **아무것도 만들지 않고 중단**한다.

1. `~/.claude/.coding-env.json` 이 있으면 `repo_path` 필드를 읽는다(`/env-update` Phase 1 과
   같은 방법). 없으면 경로 없이 일반 문구로 안내한다.
2. 다음을 그대로 보고한다(경로가 있으면 `{repo_path}` 를 채운다):

   > 허브 실행 코드가 설치돼 있지 않습니다. 허브는 coding-env 설치와 **분리**돼 있어 별도로
   > 설치해야 합니다:
   >
   >     {repo_path}/hub/install.sh
   >
   > 무엇이 설치되고 무엇이 기록되는지: `{repo_path}/hub/README.md`

## 호출 규약

```
/hub                      # 서버가 살아 있으면 그 URL 을 연다. 아니면 1회 수집 후 file:// 를 연다
/hub install              # 전역 훅 6개 설치 (옵트인, 멱등)
/hub off                  # 전역 훅 제거 (우리 마커가 붙은 엔트리만)
/hub status               # 훅 · 이벤트 · 수집 실패 · 서버 요약 보고
/hub server start         # 상주 서버 기동 (분리 프로세스, 세션 무관 수명). 멱등
/hub server stop          # 상주 서버 종료 (신원 확인 → SIGTERM → 필요 시 SIGKILL)
/hub server restart       # 상주 서버 강제 재기동 (종료 → 재기동) 후 대시보드 탭을 포커스한다. 멱등이 아니다
/hub server status        # 프로세스 · 하트비트 · HTTP 응답 · 비정상 종료 흔적 보고
/hub statusline on        # 터미널 상태줄에 사용량 등록 (옵트인, 다른 statusLine 있으면 거부)
/hub statusline off       # 우리 statusLine 만 제거
```

**`/hub` 는 어떤 경로에서도 서버를 기동하지 않는다.** 서버 기동은 언제나 사용자가
`/hub server start`·`/hub server restart` 로 명시적으로 한다 — 자동으로 뜨지 않는다는 것이
이 개정의 핵심이다.

## `/hub` (인자 없음)

```bash
python3 "$HOME/.claude/hub/bin/hub.py" open --json
```

결과 JSON 의 `server_alive`·`url`·`browser_opened`·`browser_focus_requested`·`note`(있으면)를
한 문단으로 보고한다.

- `server_alive=true` — "상주 서버가 5초마다 갱신 중입니다."
- `server_alive=false` — `note` 를 그대로 보고한다(이번 한 번만 수집했고, `/hub server start`
  로 켜면 항상 최신 상태가 유지된다는 안내가 들어 있다).
- `browser_opened=false` — 위에 더해 "브라우저를 자동으로 열지 못했습니다. URL 을 직접 열어 주세요."
- `browser_focus_requested=false`(이면서 `browser_opened=true`) — 탭은 열렸지만 창이 앞으로
  오지 않았을 수 있다는 뜻이다(비-macOS 폴백 경로). `browser_fallback_reason`(있으면)을 곁들인다.

## `/hub server start` — 상주 서버 기동

```bash
python3 "$HOME/.claude/hub/bin/hub.py" server-start --json
```

`already_running=true` 면 "이미 실행 중입니다"만 보고한다(멱등, 재기동하지 않는다).
새로 뜬 경우 `pid`·`url` 을 보고하고 다음을 덧붙인다: "Claude 세션이 끝나도 계속 실행되며,
끄려면 `/hub server stop` 을 실행하십시오." `ok=false` 면 `reason`(포트 점유 또는
`log_tail`)을 그대로 보고한다.

## `/hub server stop` — 상주 서버 종료

```bash
python3 "$HOME/.claude/hub/bin/hub.py" server-stop --json
```

`was_running` 여부와 (있으면) `reason`을 보고한다. `reason` 이 있는 경우는 대부분 PID
재사용(재부팅 후 낡은 상태 파일 등)이며, **그 프로세스는 건드리지 않고 상태 파일만
정리**했다는 뜻이다 — 실패로 취급하지 않는다.

## `/hub server restart` — 상주 서버 강제 재기동 + 대시보드 포커스

기존 서버를 확실히 내린 뒤 새 코드로 다시 띄운다(멱등이 아니다 — 살아 있어도 항상
재기동한다). 두 호출을 순서대로 실행하고, **첫 호출이 `ok:false` 면 두 번째 호출을
하지 않는다**:

```bash
python3 "$HOME/.claude/hub/bin/hub.py" server-restart --json
```

`ok:true` 면 이어서 다음을 실행하고 두 JSON 을 함께 보고한다:

```bash
python3 "$HOME/.claude/hub/bin/hub.py" open --json
```

`ok:false` 면 `open` 을 실행하지 않고 `phase`(`"stop"`|`"start"`)와 `reason` 을 그대로
보고한다. `ok:true` 면 `stopped_previous`(원래 켜져 있었는가)·`pid`·`note`(있으면, 강제
종료·PID 재사용 등의 이례)와, `open` 결과의 `browser_focus_requested`·`browser_opened` 를
함께 보고한다.

`server-restart` 호출이 `invalid choice: 'server-restart'` 로 **exit 2** 를 내면 설치본이
낡았다는 뜻이다 — `hub/install.sh --force` 재실행을 안내한다.

## `/hub server status`

```bash
python3 "$HOME/.claude/hub/bin/hub.py" server-status --json
```

`alive`(핵심 한 줄) 를 먼저 보고한다. `crashed_evidence=true` 면 **"비정상 종료된 흔적이
있습니다"**, `collect_stalled=true` 면 **"프로세스는 살아 있지만 수집이 멈췄습니다"** 와
`log_tail`(있으면)을 함께 보고한다. 그 외 필드(`record`·`process_present`·
`heartbeat_age_ms`·`http_ok`·`orphaned_evidence`)는 참고용으로 표에 곁들인다.

## `/hub install` — 훅 + 상태줄 설치 (옵트인)

**1단계 — 훅.**

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-hooks --json
```

**2단계 — 상태줄.** 1단계의 `ok` 와 무관하게 이어서 실행한다(둘은 독립된 옵트인이다).

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-statusline --json
```

**두 명령 실행 전 아래 고지를 한 번에 보여주고 진행 여부를 확인한다**(최초 1회. 두 결과의
`already_installed` 가 모두 참이면 다음부터 생략):

> **① 전역 훅 6개** — `SessionStart`·`UserPromptSubmit`·`Stop`·`SubagentStart`·`SubagentStop`·
> `SessionEnd` 에 훅을 추가합니다. 프롬프트 앞부분(120자)이 `~/.claude/hub/events/` 에 평문으로
> 최대 7일 보관됩니다(`~/.claude/hub/config.json` 의 `record_prompt_excerpt:false` 로 끌 수 있음).
> **② 터미널 상태줄** — `~/.claude/settings.json` 의 `statusLine` 에 우리 커맨드를 등록합니다.
> **모든 프로젝트의 터미널 상태줄**에 `세션 23% · 주간 41%` 가 상시 표시되고, 그 값이
> `~/.claude/hub/rate_limits.json` 에 캡처돼 **허브의 사용량 패널을 채웁니다.** 이미 다른
> `statusLine` 이 설정돼 있으면 **덮어쓰지 않고 거부**합니다.
> 기존에 설치된 다른 도구의 훅(CAM·Litmus 등)은 건드리지 않습니다.
> 상태줄만 원하지 않으면 나중에 `/hub statusline off` 로 즉시 되돌릴 수 있습니다.

사용자가 **"훅만"** 이라고 답하면 2단계를 건너뛴다. 임의로 건너뛰거나 강행하지 않는다.

**보고** — 두 결과를 한 덩어리로 보고한다.

| 상황 | 보고 |
|------|------|
| 둘 다 성공 | 훅 `installed`/`already_installed` + 상태줄 `installed`/`already_installed`. 이어서 `/hub server start` 를 안내 |
| 훅 성공 · 상태줄 `ok:false` | **`/hub install` 을 실패로 보고하지 않는다.** 훅 결과를 먼저 보고하고, 상태줄은 `reason` 을 그대로 옮긴다. 남의 `statusLine` 충돌(`current_command` 동봉)이면 "기존 설정을 보존했습니다 — 사용량 패널이 필요하면 `/hub statusline on` 을 직접 실행하거나, 터미널을 건드리지 않는 대안으로 `config.json` 의 `usage_api_enabled:true`(macOS 전용, 옵트인)를 쓸 수 있습니다" 한 줄을 덧붙인다 |
| 훅 `ok:false` | 훅의 `reason` 을 그대로 보고하고 **재시도하지 않는다**(`settings.json` 파싱 실패는 사용자의 권한 설정을 보호하기 위한 의도적 중단이다). 2단계 결과도 함께 보고한다 |

두 명령 모두 **멱등**이다 — 이미 설치돼 있으면 `settings.json` 을 쓰지 않는다.

## `/hub off` — 훅 제거

```bash
python3 "$HOME/.claude/hub/bin/hub.py" uninstall-hooks --json
```

`removed` 목록을 보고한다. 서버가 켜져 있으면 계속 돈다 — 이 명령은 훅만 건드린다.

## `/hub statusline on` — 한도 초기화 예정 시각 캡처 등록 (단독 재실행, 옵트인)

`/hub install` 2단계와 같은 명령이다 — 그때 "훅만"을 선택했거나 상태줄 등록만 실패했던
경우 이 명령으로 단독으로 다시 시도한다.

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-statusline --json
```

**실행 전 반드시 아래 고지를 사용자에게 보여주고 진행 여부를 확인한다** (최초 1회, 이미
설치돼 있으면 건너뜀 — `already_installed` 로 판단):

> 이 명령은 `~/.claude/settings.json` 의 `statusLine` 에 우리 커맨드를 등록합니다 — **모든
> 프로젝트의 터미널 상태줄**에 영향을 줍니다. 등록 후에는 상태줄에 `세션 23% · 주간 41%` 가
> 상시 표시되고, 한도 초기화 예정 시각과 사용률이 `~/.claude/hub/rate_limits.json` 에
> 캡처돼 사용량 패널에 보입니다. 이미 다른 `statusLine` 이 설정돼 있으면 **덮어쓰지 않고
> 거부**합니다.

결과의 `installed`·`already_installed` 를 보고한다. `ok=false` 면 `reason` 을 그대로 보고하고
**재시도하지 않는다** — 다른 `statusLine` 과의 충돌(`current_command` 동봉)이거나
`hub_statusline.py` 가 배포되지 않은 상태(`hub/install.sh` 재실행 필요)다.

등록한 적이 없거나 세션을 한 번도 안 돌렸으면 사용량 패널 자체가 존재하지 않는다. 한
번이라도 등록·캡처된 뒤에는 세션을 한동안 안 돌려 캡처가 낡아도 패널이 사라지지 않고
**조회되지 않음**으로 표시된다(`hub/README.md` 「사용량 패널」 참조).

## `/hub statusline off` — 캡처 중단

```bash
python3 "$HOME/.claude/hub/bin/hub.py" uninstall-statusline --json
```

`removed` 여부를 보고한다. 우리 것이 아닌 `statusLine` 은 건드리지 않는다 — 그 경우
`removed:false` 로 보고하고 no-op 임을 알린다.

## `/hub status`

```bash
python3 "$HOME/.claude/hub/bin/hub.py" status --json
```

`last_collect_failure` 가 `null` 이 아니거나 `event_read_warnings` 가 비어 있지 않으면
**그 내용을 표보다 먼저 한 줄로 보고한다.** 허브가 조용히 멈춰 있는 상태를 사용자가 표의
숫자에서 유추하게 두지 않는다. 이어서 `hooks_installed`(이벤트별 설치 여부) ·
`events_today_and_yesterday`(오늘+어제 이벤트 수) · `server_alive`·`server_crashed_evidence`·
`server_collect_stalled`(서버 요약) · `last_collected_at_ms` 를 표로 보고한다.

`usage_panel_enabled`(사용량 패널 스위치)·`usage_sample_age_ms`(캡처에서 퍼센트를 실을 수
있을 때만 채워지는 나이, ms)도 같은 표에 곁들인다. 퍼센트의 출처는 `/hub statusline on`
이 등록하는 statusLine 캡처, 또는 `usage_api_enabled:true` 로 켜는 사용량 API 폴링 —
둘 중 하나가 채우는 같은 캡처 파일(`rate_limits.json`)이다. 둘 다 등록·활성화하지 않았거나
세션을 한 번도 안 돌렸으면 `usage_panel_enabled:true` 인데도 `usage_sample_age_ms` 는
항상 `null` 이다. `usage_panel_enabled:false` 면 `config.json` 에서 껐다는 뜻이고, `true`
인데 `usage_sample_age_ms` 가 `null` 이면 캡처가 없거나(두 생산자 모두 미등록·세션 미실행)
계약이 안 맞거나 퍼센트가 없는(구형 캡처 등) 것이며, 숫자인데 5시간(18,000,000ms)을 넘거나
세션(5시간) 창이 이미 리셋됐으면 만료돼 패널이 표시되지 않는 것이다 — 패널이 안 보이는
여러 이유를 이 필드와 아래 `rate_limit_capture_age_ms`·`usage_api_last_failure` 로 구분한다.

`statusline_installed`(우리 statusLine 설치 여부) · `rate_limit_capture_age_ms`(한도
초기화 시각 캡처를 처음 관측한 뒤 지난 시간, ms) · `rate_limit_resets_remaining_ms`
(`{"session": ms|null, "weekly": ms|null}` — 아직 지나지 않은 리셋까지 남은 시간)도 같은
표에 곁들인다. 초기화 예정 시각 줄이 안 보이는 이유(①statusLine 미설치 ②세션 미실행
③리셋 시각이 이미 지남 ④`show_usage_panel:false`)를 이 세 필드로 구분한다.

`usage_api_enabled`(`config.json` 의 사용량 API 스위치) · `usage_api_last_attempt_age_ms`
(마지막 폴링 시도로부터 지난 시간, ms — 시도한 적이 없으면 `null`) ·
`usage_api_last_failure`(`{at_ms, reason, response_keys?}` 또는 성공 시 `null`)도 같은
표에 곁들인다. `usage_api_enabled:false` 면 옵트인 기능이 꺼져 있다는 뜻이고(기본값),
`true` 인데 `usage_api_last_failure` 가 있으면 그 `reason` 으로 원인을 구분한다 —
`credential_unavailable`/`credential_unparsable` 은 macOS Keychain 접근 문제,
`http_unauthorized` 는 재로그인 필요, `http_rate_limited` 는 일시적 과다 요청,
`network_error` 는 연결 실패, `schema_mismatch` 는 응답 형식이 바뀐 경우다(이때만
`response_keys` 에 응답의 키 구조가 함께 실린다 — **값은 절대 포함되지 않는다**). 이
경로는 스위치 off·statusLine 미등록·세션 미실행·계약 불일치·만료와 함께 "패널이 안 뜨는
이유"의 사각지대를 마저 없앤다.

---

## 구현 노트 (사람이 읽는 참고용 — 이 절은 실행하지 않는다)

- **훅은 반드시 `type: "command"` 다.** `type: "http"` 는 v2.1.108 에서 발동하지 않음이 실측됐다
  (CAM 2026-08-03) — 이 사실을 모르고 되돌리는 회귀를 막기 위해 여기 적어 둔다.
- 훅 커맨드 문자열은 항상 아래와 **글자 하나까지 동일**해야 한다(6개 이벤트 공통):

  ```
  python3 "$HOME/.claude/hub/bin/hub_hook.py" >/dev/null 2>&1 || true   # DZH_HUB_HOOK
  ```

  `|| true` 는 `Stop` 훅의 종료 코드가 세션을 막지 않게 하고, `>/dev/null` 은
  `UserPromptSubmit` 훅의 stdout 이 세션 컨텍스트로 섞여 들어가는 것을 막는다. 둘 다 생략 금지.
  `# DZH_HUB_HOOK` 마커는 설치·제거의 유일한 판정 키다.
- `Notification` 훅은 설치하지 않는다 — Desktop·Cursor 의 GUI 승인 카드는 이 이벤트를 발화하지
  않는다(CAM 실측 2026-08-04).
- statusLine 커맨드 문자열은 항상 아래와 **글자 하나까지 동일**해야 한다:

  ```
  python3 "$HOME/.claude/hub/bin/hub_statusline.py" 2>/dev/null || true   # DZH_HUB_STATUSLINE
  ```

  훅 커맨드와 달리 **`>/dev/null`(stdout 리다이렉트)을 절대 넣지 않는다** — statusLine 에서는
  stdout 이 실제 출력 채널이라, 이를 막으면 상태줄이 통째로 사라진다. `2>/dev/null || true`
  만 쓴다. `# DZH_HUB_STATUSLINE` 마커는 설치·제거의 유일한 판정 키다.
- 서버 포트는 **8794 고정**이다(북마크 가능해야 하므로 후보 순회를 하지 않는다).
- 티어 1(`.claude/dashboard.html`)은 `commands/dashboard.md` 의 DOM 계약을 **읽기만** 한다.
  그 문서의 불변식 2·5(`<li id="dz-step-…">`·`<td id="dz-cell-…">` 는 한 줄에 하나씩)가 깨지면
  허브 파서가 조용히 티어 2로 강등한다 — 대시보드 커맨드를 고칠 때 이 의존을 기억할 것.
