# 통합 허브 대시보드

로컬 머신에서 돌고 있는 **모든 Claude Code 프로젝트**의 진행 상황(프로젝트/세션/단계)을
한 페이지에서 **읽기 전용**으로 본다. 명령·제어 기능(중단·프롬프트 주입·승인)은 범위 밖이다.

**coding-env 설치와 완전히 별개다.** `install.sh --scope project|user` 를 실행해도 허브는
설치되지 않는다 — 허브는 상주 프로세스와 전역 훅을 남기는 별도 자산이라, 설치 동의도
분리돼 있다. 설계 근거는 [`../docs/prps/hub-dashboard.md`](../docs/prps/hub-dashboard.md).

---

## 설치

```bash
hub/install.sh
```

`~/.claude/hub/bin/` 에 11개 파일을 설치한다. `--scope` 인자가 없다 — 설치 위치는 이 하나뿐이며,
머신 전역 자산이라 프로젝트마다 사본을 두지 않는다.

- `--force` — 수정된 파일이 있어도 덮어쓴다
- `--dry-run` — 계획만 출력(파일시스템 변경 없음)
- `--uninstall` — 서버 정지 → 훅 제거 → `bin/` 삭제(순서 고정, 아래 「제거」 참조)

## 빠른 시작

```bash
hub/install.sh              # 1. 실행 코드 설치
/hub install                 # 2. 전역 훅 6개 설치(옵트인)
/hub server start             # 3. 상주 서버 기동
/hub                         # 4. 브라우저에서 열기
```

## 서버

`/hub server start|stop|restart|status` 로 제어하는 상주 프로세스가 포트 **8794**(고정)에서
`hub.html` 을 서빙하고, 5초마다 모든 프로젝트를 다시 수집한다.

- **Claude Code 세션과 무관하게 산다.** `start_new_session=True`(POSIX `setsid`)로 띄우므로
  세션이 끝나거나 터미널이 닫혀도 서버는 계속 돈다.
- **`/hub server restart` 는 멱등이 아니다.** `start` 와 달리 살아 있어도 항상 종료 후 다시
  띄운다 — 코드를 고친 뒤(`hub/install.sh --force`) 새 코드로 갈아 끼우는 용도다. 종료가
  실패하면 재기동을 시도하지 않고 그 사실을 그대로 보고한다.
- **재기동 후에는 대시보드 탭이 포커스된다.** macOS 에서는 `/usr/bin/open` 이 브라우저를
  포그라운드로 올린다(안 되는 환경은 기존 `webbrowser` 열기로 폴백한다).
- **재부팅하면 사라진다.** 자동 재기동을 하지 않는다 — "상시"는 "세션이 죽여도 살아남는다"는
  뜻이지 "재부팅 후에도 뜬다"는 뜻이 아니다.
- **크래시하면 그대로 죽는다.** 자동으로 되살리지 않는다. 대신 `/hub server status` 의
  `crashed_evidence` 필드 + `server.log` 마지막 줄, 그리고 브라우저의 "서버 연결 끊김" 표시
  세 곳에서 죽었다는 사실을 확인할 수 있다. 하트비트 TTL(수집 주기의 3배, 최소 15초)이
  지나면 훅이 자동으로 폴백 수집을 시작해 갱신이 완전히 멎지는 않는다.
- **`/hub`(인자 없음)는 서버를 켜지 않는다.** 서버가 이미 살아 있으면 그 URL 을 열고, 꺼져
  있으면 1회만 수집한 뒤 `file://` 로 열면서 `/hub server start` 를 안내한다. 서버 기동은
  언제나 사용자가 명시적으로 한다.

## 훅 옵트인

`/hub install` 이 `SessionStart`·`UserPromptSubmit`·`Stop`·`SubagentStart`·`SubagentStop`·
`SessionEnd` 6개 이벤트에 전역 훅을 추가한다(`# DZH_HUB_HOOK` 마커로 식별). 이미 설치된 다른
도구의 훅(CAM·Litmus 등)은 절대 읽지도 고치지도 않는다 — 마커가 붙은 엔트리만 우리 소유다.
서버가 켜져 있으면 훅은 이벤트를 파일에 append 만 하고 재수집은 서버에 맡긴다(중복 수집 없음).
서버가 꺼져 있으면(또는 크래시했으면) 훅이 폴백으로 재수집을 spawn 한다.

## 프라이버시 고지

- 프롬프트 앞부분 **120자**가 `~/.claude/hub/events/*.jsonl` 에 평문으로 최대 **7일** 보관된다.
  `config.json` 의 `record_prompt_excerpt: false` 로 끌 수 있다.
- **서버 가동 중에는 `127.0.0.1:8794` 가 열려 있다.** 루프백 바인딩(원격 불가) +
  허용 경로 2개(`/`, `/hub.html`) 화이트리스트로 제한돼 있어 `events/*.jsonl`·`bin/*.py`·
  `config.json` 은 어떤 경로로도 노출되지 않는다. 다만 이 포트에 닿는 **로컬**의 다른 프로세스는
  `hub.html` 에 인라인된 프롬프트 발췌를 읽을 수 있다. 끄는 수단은 `record_prompt_excerpt:false`
  와 `/hub server stop`.
- 아래 「사용량 패널」의 계정 단위 사용률도 같은 방식으로 `hub.html` 에 인라인된다. 끄는
  수단은 `config.json` 의 `show_usage_panel: false` — 이 경우 사용량 파일 자체를 읽지 않는다.
- `/hub statusline on` 을 켜면 세션·주간 사용률 한 줄(`세션 23% · 주간 41%`)이 **터미널
  상태줄**에도 상시 표시된다 — 화면을 함께 보는 사람에게도 보이는 위치라는 점에 유의한다.
  끄는 수단은 `/hub statusline off`.

## 화면 배치

- 프로젝트 카드는 뷰포트 폭에 따라 1~4열 그리드로 자동 전환된다(≤683px 1열 · 684~1015px 2열 ·
  1016~1347px 3열 · 1348px 이상 4열이 상한이다). 같은 행의 카드도 세션 목록 유무와 무관하게
  자기 높이만큼만 차지한다.
- 사용량 패널(있을 때만)은 화면 우하단에 고정된다 — 접힘·펼침 상태와 무관하게 위치는 항상
  같다.
- 마지막 카드와 푸터는 패널이 접혀 있든 펼쳐 있든 가려지지 않는다. 하단 여백은 패널의
  실측 높이에 맞춰 매 렌더마다 다시 계산된다.
- 세션 줄에는 상태 배지·경과 시간과 함께, 그 세션에서 실행됐던 **서브에이전트** 타입 칩이
  최대 2개까지 보인다 — 세션이 이미 완료됐어도 무슨 서브에이전트가 돌았는지 남는다. 같은
  타입은 하나로 합치고, 상한을 넘는 타입은 "+N" 칩 하나로 접는다.
- 실행 중인 서브에이전트 칩은 글리프(●)와 강조색으로 구분되고, 종료된 칩은 중립색이다.
- 새로고침 버튼·프로젝트명·티어 배지·사용량 갱신 시각·서브에이전트 칩에 마우스를 올리거나
  Tab 으로 포커스하면 이 파일 안의 커스텀 **툴팁**이 뜬다 — 네이티브 title 툴팁의 지연 없이
  약 120ms 안에 나타나고, Escape·스크롤·클릭으로 즉시 닫힌다.

## 사용량 패널 — 5시간·7일 한도 사용률

허브 페이지 우하단에 세션(5시간)·주간(7일) 한도 사용률을 막대 2개로 보여준다. 출처는
Claude 데스크톱 앱이 남기는 비공개 파일 `~/Library/Application Support/Claude/plan-usage-history.json`
**하나뿐**이다 — **macOS 데스크톱 앱이 설치된 환경에서만** 표시된다. 리눅스·윈도우·터미널
전용 환경에서는 파일이 애초에 없으므로 이 기능이 조용히 존재하지 않는다(경고 없음).

- 제목 줄(`Claude 사용 한도`)을 클릭하거나 Tab 으로 포커스한 뒤 Enter/Space 를 누르면
  접기/펼치기가 전환된다. 접으면 세션·주간 수치를 한 줄 요약(`세션 43% · 주간 71%`)으로
  줄이고, 선택은 새로고침 후에도 `localStorage` 로 유지된다.
- 데이터가 없거나(파일 부재), 5시간보다 오래됐거나(앱을 안 켠 지 오래됨), 스위치가 꺼져
  있으면 패널 전체를 표시하지 않는다 — 부분 패널이나 "0%" 오해를 만들지 않는다.
- 앱 업데이트로 파일 스키마가 바뀌면(계약 불일치) 패널이 사라지고 `warnings` 에 경고가 1건
  뜬다. `/hub status` 의 `usage_panel_enabled`·`usage_sample_age_ms` 로 원인을 일부 구분할
  수 있다 — `usage_panel_enabled:false` 면 스위치로 껐다는 뜻이고, `true` 인데
  `usage_sample_age_ms` 가 `null` 이면 파일이 없거나 계약이 안 맞는 것이며(이 둘은 값만으로는
  구분되지 않는다), 숫자인데 5시간을 넘으면 만료된 것이다.
- 갱신 주기는 데스크톱 앱이 정한다(실측 중앙값 15.2분) — 5초 폴링과 별개다. 패널에 "약 15분
  주기" 문구를 항상 병기해 실시간 수치로 오해하지 않게 한다.
- 실측 환경은 조직(org) 1종뿐이라 여러 조직을 오가는 계정에서는 마지막 샘플이 어느
  조직 것인지 필터하지 않는다 — 표시가 어색하면 `show_usage_panel:false` 로 끈다.

## 한도 초기화 예정 시각

사용량 패널을 **펼치면** 세션·주간 막대 각각 아래에 `초기화 18:32 · 2시간 12분 뒤` 형태의 줄이
더해진다. 출처는 Claude 데스크톱 앱의 히스토리 파일이 아니라 **Claude Code CLI 가 statusLine
명령에 stdin 으로 주는 공식 입력 JSON**(`rate_limits.*.resets_at`)이다 — macOS 가 아니어도,
터미널 전용 환경에서도 동작한다.

- 설치: `/hub statusline on` — `~/.claude/settings.json` 의 `statusLine` 에 우리 커맨드를
  등록한다(`# DZH_HUB_STATUSLINE` 마커로 식별). 이미 다른 `statusLine` 이 설정돼 있으면
  **설치를 거부**하고 기존 값을 그대로 둔다 — `hooks` 와 달리 `statusLine` 은 배열이 아니라
  단일 값이라 병합할 수 없기 때문이다. 제거는 `/hub statusline off`.
- 설치 후에는 터미널 상태줄에도 `세션 23% · 주간 41%` 한 줄이 함께 표시된다(위 프라이버시
  고지 참조).
- 값은 Claude Code 세션이 한 번이라도 진행돼야 생긴다(`~/.claude/hub/rate_limits.json` 에
  캡처된다). 세션을 안 돌리면 캡처가 없거나 낡을 수 있다 — 리셋 시각이 **아직 지나지
  않았다면** 캡처가 며칠 묵어도 여전히 표시된다(절대 시각이라 지나기 전까지는 참이다).
  리셋 시각이 지나면 그 줄은 자동으로 사라진다. 캡처가 실제로 확인된 시각은 줄에 마우스를
  올리면 툴팁으로 보인다.
- 퍼센트(데스크톱 앱)가 없으면 패널 자체가 뜨지 않으므로, 이 기능도 함께 보이지 않는다 —
  초기화 시각은 기존 패널의 장식이지 별도 표시 조건이 아니다.
- `/hub status` 의 `statusline_installed`·`rate_limit_capture_age_ms`·
  `rate_limit_resets_remaining_ms` 로 설치·캡처 상태를 진단할 수 있다.

## 티어 한계 — 프로젝트마다 "가진 것 중 가장 높은 티어"로 표시한다

| 티어 | 출처 | 얻는 것 | 없으면 |
|------|------|--------|-------|
| 1 | `<프로젝트>/.claude/dashboard.html` | 제목·단계별 상태·진행률 | 티어 2로 강등 |
| 2 | `~/.claude/hub/events/*.jsonl` | 세션 목록·상태·단계 **추정** | 티어 3으로 강등 |
| 3 | `~/.claude/projects/<인코딩>/*.jsonl` 의 **mtime** | 마지막 활동 시각뿐(내용은 절대 읽지 않는다) | 그 프로젝트는 목록에 없다 |

`~/.claude/projects` 디렉토리명은 정방향으로만 매칭한다(역디코딩하지 않음) — 매칭되지 않은
이름은 "미확인 프로젝트 N개"로 접혀 표시된다. 경로를 지어내는 일은 없다.

## 설정 — `~/.claude/hub/config.json` (선택, 없으면 전부 기본값)

| 필드 | 기본값 | 뜻 |
|------|--------|-----|
| `roots` | `[]` | 이 경로들을 훑어 `.claude`·`.git` 이 있는 디렉토리를 프로젝트로 추가한다 |
| `ignore_globs` | worktree·`/tmp`·`/private/tmp` | 이 패턴에 맞는 경로는 제외한다 |
| `scan_depth` | `3` | `roots` 스캔 깊이 |
| `stale_after_minutes` | `30` | 이 시간 무활동이면 `stale` 로 표시 |
| `event_retention_days` | `7` | 이보다 오래된 이벤트 파일은 삭제 |
| `record_prompt_excerpt` | `true` | 프롬프트 발췌 기록 여부 |
| `server_port` | `8794` | 상주 서버 고정 포트 |
| `server_collect_interval_seconds` | `5` | 수집 루프 주기 |
| `show_usage_panel` | `true` | `false` 면 사용량 패널을 끈다 — 사용량 히스토리 파일을 아예 읽지 않는다 |

## 제거

```bash
hub/install.sh --uninstall
```

순서가 고정돼 있다: **서버 정지 → 훅 제거 → statusLine 제거 → `bin/` 삭제.**
`events/`·`hub.html`·`config.json`·`rate_limits.json`
은 지우지 않는다 — 사용자 데이터이며, 지울지는 직접 결정한다(경로는 완료 메시지에 안내된다).

## 파일 배치

```
~/.claude/hub/
├── bin/                     # hub/install.sh 가 배포. 11개 파일
├── config.json              # 선택
├── rate_limits.json          # /hub statusline on 이 캡처한 한도 초기화 예정 시각
├── server.json               # 서버 자신이 bind 직후 1회 쓴다(PID·포트·기동 시각)
├── server_heartbeat          # 수집 루프가 매 사이클 touch — 생존 판정의 정본
├── server.log                # 서버의 stderr. 크래시 원인 규명 창구
├── events/YYYY-MM-DD.jsonl   # 훅 이벤트 로그(append-only, 날짜별)
└── hub.html                  # 생성물 — 브라우저로 여는 유일한 파일
```

## 설계 근거

전체 설계 결정과 근거는 [`../docs/prps/hub-dashboard.md`](../docs/prps/hub-dashboard.md) 참조.
