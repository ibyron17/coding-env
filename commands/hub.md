---
description: "모든 프로젝트의 세션 진행 상황을 한 페이지에서 읽기 전용으로 보는 통합 허브 — 수집/발행/훅 설치"
argument-hint: "[install|off|status|serve [포트]|serve stop [포트]]"
---

# Hub

> 로컬에서 돌고 있는 **모든 Claude Code 프로젝트**의 진행 상황(프로젝트/세션/단계)을 한 페이지에서
> **읽기 전용**으로 본다. 명령·제어 기능은 범위 밖이다. 이 커맨드는 **얇다** — 아래 python3
> 서브커맨드를 부르고 결과를 보고하는 것 말고는 판단하지 않는다. 실제 로직은
> `~/.claude/hub/bin/*.py` 에 있다. 설계 근거: [`docs/prps/hub-dashboard.md`](../../docs/prps/hub-dashboard.md)

**`/dashboard` 와 반대 방향이다.** `/dashboard` 는 LLM 만 아는 사실을 오케스트레이터가 직접 쓴다.
`/hub` 는 파일에서 기계적으로 읽히는 사실만 집계하므로 코드가 하고, 이 문서는 그 코드를 부르는
절차만 담는다.

---

## 사전 조건

`~/.claude/hub/bin/` 이 없으면(아직 `install.sh --scope user` 를 실행하지 않은 머신) 아래를
그대로 보고하고 중단한다:

```
허브가 설치돼 있지 않습니다. install.sh --scope user 를 먼저 실행하십시오
(허브는 머신 전역 자산이라 --scope project 에는 설치되지 않습니다).
```

## 호출 규약

```
/hub                      # 수집 → hub.html 갱신 → 발행(서버 재사용/기동) → 브라우저 열기
/hub install              # 전역 훅 6개 설치 (옵트인, 멱등)
/hub off                  # 전역 훅 제거 (우리 마커가 붙은 엔트리만)
/hub status               # 훅 설치 상태 · 이벤트 파일 · 마지막 수집 시각 보고
/hub serve [포트] | /hub serve stop [포트]
```

## `/hub` (인자 없음)

```bash
python3 "$HOME/.claude/hub/bin/hub.py" open --json
```

결과 JSON 의 `url`·`served`·`browser_opened` 를 한 문단으로 보고한다.

- `served=true` — "5초마다 자동 갱신됩니다. 끝나면 `/hub serve stop` 으로 서버를 끌 수 있습니다."
- `served=false` — "서버를 띄우지 못해 파일을 직접 엽니다. 포커스를 줄 때 갱신됩니다."
- `browser_opened=false` — 위에 더해 "브라우저를 자동으로 열지 못했습니다. URL 을 직접 열어 주세요."

## `/hub install` — 훅 설치 (옵트인)

```bash
python3 "$HOME/.claude/hub/bin/hub.py" install-hooks --json
```

**실행 전 반드시 아래 프라이버시 고지를 사용자에게 보여주고 진행 여부를 확인한다** (최초 1회,
이미 설치돼 있으면 건너뜀 — `already_installed` 로 판단):

> 이 명령은 `SessionStart`·`UserPromptSubmit`·`Stop`·`SubagentStart`·`SubagentStop`·`SessionEnd`
> 6개 이벤트에 전역 훅을 추가합니다. 프롬프트 앞부분(120자)이 `~/.claude/hub/events/`에 평문으로
> 최대 7일 보관됩니다(`~/.claude/hub/config.json` 의 `record_prompt_excerpt:false` 로 끌 수 있음).
> 기존에 설치된 다른 도구의 훅(CAM·Litmus 등)은 건드리지 않습니다.

결과의 `installed`(새로 추가된 이벤트) · `already_installed`(이미 있던 이벤트)를 보고한다.
`ok=false` 면 `reason` 을 그대로 보고하고 **재시도하지 않는다** — `settings.json` 파싱 실패는
사용자의 권한 설정을 보호하기 위한 의도적 중단이다.

## `/hub off` — 훅 제거

```bash
python3 "$HOME/.claude/hub/bin/hub.py" uninstall-hooks --json
```

`removed` 목록을 보고한다. 이후에도 세션은 계속 쓸 수 있지만 이벤트 파일이 더 늘지 않는다
(`hub.html` 은 남아 있고 티어 1·3 만으로 계속 보인다).

## `/hub status`

```bash
python3 "$HOME/.claude/hub/bin/hub.py" status --json
```

`hooks_installed`(이벤트별 설치 여부) · `events_today_and_yesterday`(오늘+어제 이벤트 수) ·
`last_collected_at_ms`(마지막 `hub.html` 갱신 시각, 없으면 `null`)를 표로 보고한다.

## `/hub serve [포트]` · `/hub serve stop [포트]`

```bash
python3 "$HOME/.claude/hub/bin/hub.py" serve [포트] --json
python3 "$HOME/.claude/hub/bin/hub.py" serve stop [포트] --json
```

`/hub` 가 이미 서버를 자동으로 재사용/기동하므로 이 서브커맨드는 **수동 제어가 필요할 때만**
쓴다(포트를 바꾸거나 명시적으로 끄고 싶을 때). 포트 후보는 `8794 · 8795 · 8796` 이다 —
`/dashboard` 가 쓰는 포트대와 겹치지 않게 분리했다.

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
- 티어 1(`.claude/dashboard.html`)은 `commands/dashboard.md` 의 DOM 계약을 **읽기만** 한다.
  그 문서의 불변식 2·5(`<li id="dz-step-…">`·`<td id="dz-cell-…">` 는 한 줄에 하나씩)가 깨지면
  허브 파서가 조용히 티어 2로 강등한다 — 대시보드 커맨드를 고칠 때 이 의존을 기억할 것.
