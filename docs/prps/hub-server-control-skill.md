# 허브 서버 재기동 커맨드 + 브라우저 포커스 (PRP)

| 항목 | 값 |
|------|-----|
| 대상 | `hub/bin/hub_daemon.py`(재기동 시퀀스·브라우저 실행) · `hub/bin/hub.py`(CLI) · `commands/hub.md`(호출 규약) |
| 브랜치 | `feature/hub-dashboard` (HEAD `d498d9e` + `hub_template.html`·`tests/run.sh` 미커밋 수정 있음 — 아래 「출발 상태」) |
| 상위 설계 정본 | [`hub-dashboard.md`](./hub-dashboard.md)(개정 쟁점 R1·R2 = 서버 수명·암묵 기동 금지) → **이 문서** |
| 워크플로우 경로 | **전체 경로** — 새 CLI 서브커맨드(공개 인터페이스) + 새 반환 계약 + 4개 이상 파일 |
| 규모 | Small~Medium — 신규 0개 / 수정 8개 파일. Python 증분 약 +70/−8줄, 템플릿 증분 **0줄** |
| 새 외부 의존성 | **없음** (표준 라이브러리 `subprocess`·`webbrowser` 만) |
| **승인 상태** | **미승인** — 「사용자 승인이 필요한 미결 선택지」 5건 확인 후 구현 착수 |

---

## 요구사항 요약

사용자 요청 원문은 이렇다.

> 대시보드 허브 서버를 실행, 종료하는 스킬을 만들어줘. 실행 시에는 기존 서버가 있으면 종료 후
> 다시 실행할 수 있게 해줘. 실행 후에 대시보드 페이지를 브라우저로 띄우고 포커싱 되게 해줘.

이 중 **"실행"·"종료" 자체는 이미 있다** — `/hub server start`·`/hub server stop` 이
`hub.py` 의 `server-start`·`server-stop` 을 부른다. 실제로 없는 것은 두 가지다.

1. **강제 재기동 경로가 없다.** `start_server()`(`hub_daemon.py:119`)는 **멱등**이다 —
   `_server_already_running()` 이 참이면 `{"ok":true,"already_running":true}` 로 즉시 돌아오고
   재기동하지 않는다. 코드를 고친 뒤(`hub/install.sh --force` 이후) 새 코드로 서버를 다시
   띄우려면 지금은 사용자가 `stop` → `start` 를 손으로 두 번 쳐야 하고, 그 사이의 실패
   (stop 이 `ok:false` 인데 start 를 이어 실행)를 막아 주는 것이 아무것도 없다.
2. **브라우저가 앞으로 나오지 않는다.** `hub.py:71 _open_browser()` 는 `webbrowser.open()` 을
   쓴다. macOS 기본 브라우저 경로에서 표준 라이브러리는 `MacOSXOSAScript.open()` →
   AppleScript `open location "url"` 만 실행하고 **`activate` 를 호출하지 않는다**(이 머신의
   stdlib 소스로 직접 확인: `name == 'default'` 분기에는 `activate` 가 없고, 특정 브라우저
   이름을 준 분기에만 있다). 그래서 탭은 열리지만 창은 뒤에 남는다.

따라서 이 PRP 는 **`/hub server restart` 를 추가하고, 브라우저 열기를 "포커스까지 되는" 경로로
바꾼다.** 종료는 기존 `/hub server stop` 을 그대로 쓴다(변경 0줄).

### 사용자 스토리

> 허브 코드를 고친 개발자로서, 한 번의 커맨드로 낡은 서버를 확실히 내리고 새 코드로 다시 띄운
> 다음, 대시보드 탭이 눈앞에 올라와 바로 확인되기를 원한다.

### 성공 기준 (검증 가능한 형태로)

| # | 기준 | 검증 |
|---|------|------|
| S1 | `/hub server restart` 한 번으로 기존 서버가 죽고 **PID 가 다른** 새 서버가 뜬다 | 자동 S2 + 수동 M1 |
| S2 | 서버가 꺼져 있을 때 `restart` 를 해도 정상 기동한다(`stopped_previous:false`) | 자동 S2' + 수동 M2 |
| S3 | **stop 이 실패하면 start 를 시도하지 않는다** | 자동 S1(호출 안 됨 단언) |
| S4 | `start_server()` 의 **멱등이 유지된다** — `/hub server start` 는 여전히 재기동하지 않는다 | T25-48 + 기존 테스트 무수정 통과 |
| S5 | macOS 에서 재기동 후 대시보드 탭이 **포그라운드로 올라온다** | 수동 M5 |
| S6 | 비-macOS 에서 열기 동작이 깨지지 않는다(기존 `webbrowser` 폴백) | 자동 O3 |
| S7 | `bash tests/run.sh` 실행 중 **브라우저 탭이 하나도 열리지 않는다** | 수동 M7 (GOTCHA 3) |
| S8 | `bash tests/run.sh` 전체 통과 (T25-48·49 신규 포함) | 자동 |

### 범위 밖 (명시적으로 하지 않는 것)

| 항목 | 이유 |
|------|------|
| **탭 중복 제거** | 재기동마다 새 탭이 생기는 문제. 브라우저별 AppleScript 열거(Safari·Chrome·Arc·Firefox 가 각각 다르다)가 필요해 호환 표면이 무한히 늘어난다. `/usr/bin/open` 에는 "이미 열린 탭 재사용" 옵션이 없다 → 리스크 1 에 완화책만 적는다 |
| **`stop` 시 탭 닫기** | 브라우저 탭을 외부에서 닫는 것은 신뢰성 있게 불가능하고, 사용자가 보던 화면을 도구가 없애는 것은 읽기 전용 도구의 성격에 맞지 않는다 |
| **재부팅 후 자동 기동 · 크래시 자동 부활** | `hub-dashboard.md` 개정 쟁점 R1 의 확정 사항("상시 = 세션이 죽여도 살아남는다, 재부팅 후 부활은 아니다")을 이 PRP 는 개정하지 않는다 |
| **`/hub`(인자 없음)의 서버 암묵 기동** | 요구 R-2 로 금지돼 있고 T25-20 이 기계적으로 강제한다. `restart` 는 **명시적 커맨드**라 이 금지와 충돌하지 않는다 |
| **포트 후보 순회** | 8794 고정은 "북마크 가능해야 한다"는 확정 전제다. 포트가 남의 프로세스에 점유됐으면 그 사실을 그대로 보고하고 끝낸다 |
| **훅·statusline·수집 로직** | 접점이 없다 |

---

## 출발 상태 (구현자가 먼저 알아야 하는 사실 — 착수 지시서의 정정 2건)

착수 지시서에 적힌 두 사실이 실제와 다르다. 아래가 직접 확인한 값이다.

1. **작업트리는 clean 이 아니다.** `git status --short` → `M hub/bin/hub_template.html` ·
   `M tests/run.sh` (합계 +23/−3). HEAD 도 `ac71456` 이 아니라 `d498d9e` 다.
2. **T25 의 현재 최대 번호는 `T25-45` 가 아니라 `T25-47` 이다.** 미커밋 `tests/run.sh` 수정이
   T25-46(탭 제목 `<title>Claude Agents Manager</title>`)·T25-47(인라인 SVG 파비콘)을 이미
   추가했고, 범위 헤더 2곳(2010행 주석 · 2013행 `test_desc`)도 이미 `T25-1~T25-47` 로 갱신돼
   있다. → **이 PRP 가 추가하는 검사 번호는 `T25-48` 부터**이고, 헤더 2곳을
   `T25-1~T25-49` 로 갱신한다.

그 외 확인된 출발 상태:

- `python3 -m unittest discover -s tests/hub -t .` → **226 tests OK**(변경 전 기준선).
- `hub/install.sh` 의 `HUB_FILE_COUNT=11`, 루트 `install.sh` 의 `COMMANDS_FILE_COUNT=9`
  (직접 읽은 현재 값). 이 PRP 는 **둘 다 건드리지 않는다**(신규 배포 파일 0개, 신규 커맨드
  파일 0개 — 결정 D1).
- `clear_server_state()` 는 `server.json` **과 하트비트 파일을 둘 다** 지운다
  (`hub_collect.py:551-552`). 따라서 stop 이 성공한 뒤에는 `_server_already_running()` 이
  거짓이 되어 `start_server()` 가 정상적으로 새 프로세스를 띄운다 — 이 사실이 D3(기존 stop
  시퀀스 재사용)의 전제다.
- `http.server.HTTPServer.allow_reuse_address = 1` 이므로 재bind 는 `TIME_WAIT` 에 막히지
  않는다(GOTCHA 2).

---

## 확정된 전제 (재론하지 않는다)

1. **허브는 머신 전역 자산이다.** 저장소를 고쳐도 `hub/install.sh --force` 를 실행하기
   전까지 `~/.claude/hub/bin/` 은 옛 코드다. 구현 완료 보고에 이 사실을 반드시 적는다
   (리스크 5).
2. **CLI 호출은 언제나 설치 경로**(`python3 ~/.claude/hub/bin/hub.py`)로 한다. 저장소
   체크아웃 경로로 부르면 `hub_daemon.HUB_PY_PATH` 와 어긋나 `is_our_server_process()` 가
   "PID 재사용"으로 오판하고 `server.json` 만 지워 고아 프로세스를 만든다.
3. **`hub_model.py` 는 순수하다**(T25-10 이 강제). 이 PRP 가 거기 추가하는 것은 dataclass
   하나뿐이며 로직은 넣지 않는다.
4. **stop 의 안전장치는 한 줄도 바꾸지 않는다.** ps 신원 확인 → SIGTERM → 5초 대기 →
   SIGKILL → `clear_server_state(expected_pid=...)`(compare-and-delete) 시퀀스를
   `restart` 가 **그대로 호출해서** 쓴다(결정 D3).
5. **`hub_template.html` 은 한 줄도 바뀌지 않는다.** 따라서 불변식 H1′(폴링 갱신 대상 4요소)
   과 T25-44(`title="` 0건)·T25-46·T25-47 은 전부 무영향이다.
6. **읽기 전용 서버**라는 성격은 유지된다. 새 HTTP 경로·정적 파일은 추가하지 않는다
   (허용 경로는 `/` 와 `/hub.html` 두 개뿐인 화이트리스트 그대로).

---

## 영향 범위

### 수정 파일 (8개)

| 파일 | 변경 | 이유 |
|------|------|------|
| `hub/bin/hub_daemon.py` | 상수 4개 추가, 순수 함수 2개(`browser_open_command`·`restart_note`) 신설, I/O 함수 2개(`restart_server`·`open_browser`) + private 1개(`_wait_for_port_release`) 신설, 모듈 docstring 의 "순수 함수 목록" 갱신 | 재기동 시퀀스와 브라우저 실행은 둘 다 **프로세스 spawn** — 이 모듈의 책임이다 |
| `hub/bin/hub.py` | `cmd_server_restart` 신설, `subcommand_names`·`COMMAND_HANDLERS` 에 `server-restart` 1항, `_open_browser()` **삭제** + `import webbrowser` 삭제, `cmd_open` 이 `hub_daemon.open_browser` 를 쓰고 payload 에 `browser_focus_requested` 1필드 추가 | CLI 디스패치 + I/O 조립 레이어 |
| `hub/bin/hub_model.py` | `BrowserOpenResult` dataclass 신설(3필드) | 레이어 간 통신은 명시적 타입으로 — 공유 dataclass 는 전부 이 파일에 있다(`ServerRecord`·`ServerStatus` 선례) |
| `commands/hub.md` | `argument-hint` 에 `server restart` 추가, 「호출 규약」에 1행, `/hub server restart` 전용 절 신설, `/hub` 절의 보고 규칙에 `browser_focus_requested` 추가, 낡은 설치본(exit 2) 대응 1줄 | 사용자가 실제로 부르는 창구 |
| `hub/README.md` | 「서버」 절의 `start\|stop\|status` → `start\|stop\|restart\|status`, 재기동 동작 2행, 브라우저 포커스 1행 | T25-49 문서 정합 + 사람이 읽는 정본 |
| `tests/hub/test_hub_daemon.py` | 신규 4클래스(B1~B4 · N1~N3 · S1~S4 · O1~O4) | 순수 로직 + 시퀀스 회귀 |
| `tests/hub/test_hub.py` | `mock.patch("webbrowser.open")` **3곳 교체**(101·120·136행) + 필드 테스트 1개 | **GOTCHA 3** — 안 고치면 테스트가 실제 브라우저를 띄운다 |
| `tests/run.sh` | T25-48·T25-49 신설, 헤더 2곳을 `T25-1~T25-49` 로 갱신 | 새 불변식의 grep 회귀 |

### 미영향 — 건드리지 않는 이유

| 파일 | 이유 |
|------|------|
| `hub/bin/hub_template.html` | **0줄.** 이 변경은 페이지 내용과 무관하다 → T25-44·46·47, 불변식 H1′ 무영향 |
| `hub/bin/hub_server.py` | 서버 본체는 그대로다. SIGTERM 핸들러·`clear_server_state(expected_pid=own_pid)` 재사용 |
| `hub/bin/hub_collect.py` | `clear_server_state`·`read_server_record`·`_is_port_occupied` 의 상대편을 그대로 쓴다 |
| `hub/bin/hub_hook.py`·`hub_settings.py`·`hub_statusline.py`·`hub_parse.py`·`hub_usage.py` | 접점 0 |
| `hub/install.sh` | 신규 배포 파일 0개 → `HUB_FILE_COUNT=11` 그대로, T25-1·T25-2 통과. `--uninstall` 의 `server-stop` 순서(T25-23)도 무영향 |
| 루트 `install.sh` | 신규 커맨드 파일 0개 → `COMMANDS_FILE_COUNT=9` 그대로, T22-5 통과. T25-21(루트 install.sh 에 `hub` 문자열 0건)도 무영향 |
| 루트 `README.md` | 허브 언급 **현재 8줄**. 커맨드 개수(9개)·"독립 커맨드 2종" 문구가 그대로여서 수정 불필요 → T25-22(14줄 상한)·2108행 검사 무영향 |
| `tests/hub/` 의 나머지 8개 파일 | 브라우저·재기동을 단언하는 테스트는 `test_hub.py`·`test_hub_daemon.py` 뿐이다(`webbrowser` grep 결과 3건 전부 `test_hub.py`) |

---

## 결정 목록

| # | 결정 | 근거 |
|---|------|------|
| **D1** | **`/hub` 를 확장한다**(옵션 A). 새 커맨드 파일을 만들지 않는다 | ① 하나의 자원(포트 8794 의 단일 데몬)을 제어하는 창구가 둘이 되면 "어느 쪽이 정본인가"가 영원한 질문으로 남는다. `hub/README.md`·`hub/install.sh --uninstall`·T25 검사가 모두 `/hub server …` 를 정본으로 참조한다. ② `commands/hub.md` 는 이미 "얇은 호출자"로 선언돼 있어(문서 9~10행) 서브커맨드 1행 추가가 정확히 그 문서의 형식이다. ③ 배포 레이어 변경이 **0** 이다 — 옵션 B 는 `COMMANDS_FILE_COUNT` 9→10, 루트 `README.md` 3곳("commands/ \| 9"·"commands 9개"·"9개 커맨드 … 독립 커맨드 2종"), T22-5 재확인까지 최소 5곳을 건드린다. 기능 하나를 위해 배포 계약을 흔들 이유가 없다. → **승인 항목 1** |
| **D2** | 새 서브커맨드 이름은 **`server-restart`**(커맨드 표기는 `/hub server restart`) | 기존 4개(`server-start`·`server-stop`·`server-status`·`server-run`)와 같은 `server-` 접두사 규칙. `force-start` 같은 이름은 "무엇을 강제하는지"가 모호하다 |
| **D3** | `restart_server()` 는 **기존 `stop_server()`·`start_server()` 를 그대로 호출한다.** 두 함수의 내부는 손대지 않는다 | 요구 3·6. stop 의 안전장치(ps 신원 확인·compare-and-delete)와 start 의 멱등을 복제하면 두 시퀀스가 갈라진다. 멱등 start 는 다른 호출자(문서·훅 폴백 안내)가 의존하는 계약이다 — **깨지 않고 옆에 새 경로를 만든다** |
| **D4** | **stop 이 `ok:false` 면 start 를 시도하지 않고 즉시 `phase:"stop"` 으로 실패 반환** | 요구 6. `stop_server()` 가 `ok:false` 를 돌려주는 유일한 경우는 "ps 실행 실패 — 확인할 수 없어 아무것도 하지 않았습니다"다. 즉 **낡은 서버가 살아 있을 수 있는 상태**이고, 여기서 start 를 하면 포트 충돌로 실패하거나(운 좋은 경우) 서버가 둘이 되려 시도한다 |
| **D5** | stop 성공 후 **포트 해제를 최대 3초 기다린다**(`_wait_for_port_release`) | `stop_server()` 는 ps 에서 프로세스가 사라진 시점에 돌아온다. SIGKILL 경로에서 커널이 리스닝 소켓을 정리하기까지의 짧은 창에 `_is_port_occupied()` 가 참이면, start 는 **"포트 8794 이 이미 사용 중입니다(다른 프로세스)"** 라는 완전히 틀린 진단으로 실패한다. 대기 루프 6줄이 그 오진을 없앤다. 3초를 넘겨도 start 를 그대로 호출한다 — 그때는 정말 남의 프로세스이고 위 메시지가 정확한 진단이다 |
| **D6** | start 가 `already_running:true` 를 돌려주면 **성공이 아니라 실패**로 보고한다(`phase:"start"`, 고아 하트비트 안내) | 방금 stop 을 성공시킨 직후이므로 이 응답은 정상 상태가 아니다. 도달 가능한 실제 경로가 있다: `server.json` 이 없으면 `stop_server()` 는 `clear_server_state` 를 부르지 않고 `was_running:false` 로 돌아오는데, 이때 **낡았지만 TTL 안쪽인 하트비트 파일**이 남아 있으면 `_server_already_running()` 이 참이 된다. 이것이 `server_status()` 가 이미 이름을 붙여 둔 `orphaned_evidence` 상태다. 그냥 `ok:true` 로 보고하면 사용자는 "재기동했다는데 페이지가 죽어 있다"를 만난다 |
| **D7** | 그 고아 하트비트를 **restart 가 지우지 않는다**. 보고만 한다 | 하트비트/`server.json` 을 조건 없이 지우는 것은 compare-and-delete 가 막으려 했던 바로 그 위험(그 사이 다른 셸이 띄운 새 서버의 기록을 지워 고아로 만드는 것)이다. 진단을 주고 사용자가 `/hub server status` 로 확인하게 한다 |
| **D8** | 브라우저 열기: **macOS 만 `/usr/bin/open <url>`**, 그 외 플랫폼과 실패 시는 **기존 `webbrowser.open()` 폴백** | `/usr/bin/open` 은 `-g` 가 없으면 앱을 포그라운드로 올린다 — 요구의 "포커싱"을 정확히 만족한다. 리눅스의 `xdg-open`·윈도우의 기본 핸들러는 `webbrowser` 경유로도 창을 올리므로 분기를 늘릴 이유가 없다(YAGNI). 폴백은 "열리기라도 한다"를 보장한다 |
| **D9** | 플랫폼 판정은 **순수 함수 `browser_open_command(platform_name, url)`** 로 분리한다 | 이 저장소에는 CI 가 없고 개발 머신은 macOS 하나다 — 리눅스/윈도우 경로를 실제로 밟아 볼 방법이 없다. 순수 함수로 떼어 놓으면 **세 플랫폼 전부를 단위 테스트로 덮을 수 있다**(B1~B3). `hub_daemon` 이 "순수 판정 함수 + 그것을 쓰는 I/O" 형태를 이미 갖고 있다(`is_our_server_process`, 모듈 docstring 에 명시) — 같은 형태를 따른다 |
| **D10** | 브라우저 실행은 **`hub_daemon.py`** 에 둔다. 새 모듈(`hub_browser.py`)을 만들지 않는다 | 외부 프로세스 spawn 은 이 모듈의 선언된 책임("분리 spawn · ps 신원 확인 · SIGTERM/SIGKILL")이고, `restart` 와 나란히 있어야 읽힌다. 새 파일은 `HUB_FILE_COUNT` 11→12 + T25-1·T25-2 재확인을 부르는데, 함수 3개(약 25줄)가 파일 하나를 가질 근거는 없다. 현재 `hub_daemon.py` 는 230줄이라 여유가 충분하다 |
| **D11** | `_open_browser()` 를 `hub.py` 에서 **삭제하고** `cmd_open` 도 새 경로를 쓴다 | 같은 일을 하는 함수를 두 개 두지 않는다. 부수 효과로 `/hub`(인자 없음)도 포커스를 얻는다 — 요구가 지적한 결함은 `cmd_open` 에서 발생하는 것이므로 이것이 오히려 정공법이다. `import webbrowser` 는 이 삭제로 고아가 되므로 함께 제거한다(내가 만든 고아만 치운다) |
| **D12** | 재기동 후 페이지 열기는 **커맨드 레이어에서 조합**한다 — `server-restart` 다음에 기존 `open` 을 호출한다. `server-restart` 자체는 브라우저를 열지 않는다 | 서브커맨드 하나가 "프로세스 제어 + 브라우저 + URL 판정(http vs file://)"을 다 하면 책임이 셋이 된다. `open` 은 이미 "서버가 살아 있으면 http, 아니면 1회 수집 후 file://" 판정을 갖고 있어 그대로 재사용하는 것이 맞다. `commands/hub.md` 의 조합 지시는 "ok:false 면 open 을 실행하지 않는다" 한 줄뿐이다. → **승인 항목 3** |
| **D13** | `/hub server start` 는 **아무것도 바뀌지 않는다**(브라우저도 열지 않는다) | 스크립트/문서가 부르는 기존 계약이다. 부수 효과로 브라우저가 뜨는 것은 놀라움이고, 요구는 "재기동 시"를 말한다. → **승인 항목 2** |
| **D14** | 종료(`/hub server stop`)는 **변경 0줄** | 요구의 "종료"를 이미 완전히 만족한다. 손댈 이유가 없다 |
| — | 디자인 패턴 도입 없음 | 순수 함수 2개 + I/O 함수 3개 + dataclass 1개다. 상태 기계·전략 객체·플러그인 레지스트리를 도입할 문제가 없다(YAGNI) |

---

## 데이터 모델

### 신설 — `hub_model.BrowserOpenResult`

```python
@dataclass(frozen=True)
class BrowserOpenResult:
    """브라우저 열기 시도의 결과. `focus_requested` 는 '포그라운드로 올리는 경로를 썼다'는
    뜻이며, 실제로 창이 올라왔는지는 OS 소관이라 확인하지 않는다."""

    opened: bool                  # URL 을 여는 데 성공했는가
    focus_requested: bool         # 포커스를 가져오는 경로(/usr/bin/open)로 열었는가
    fallback_reason: str | None    # 포커스 경로가 실패해 webbrowser 로 떨어진 사유(정상이면 None)
```

`fallback_reason` 이 필요한 이유: macOS 에서 탭은 떴는데 창이 뒤에 남는 상황이 이 PRP 가 고치려는
바로 그 증상이다. 폴백이 조용히 일어나면 사용자는 "고쳐졌다더니 그대로"만 보게 된다 —
이 필드가 그 원인을 표면화하는 유일한 창구다.

---

## 인터페이스

### `hub/bin/hub_daemon.py` — 신설 상수

```python
# /usr/bin/open 은 -g 가 없으면 앱을 포그라운드로 올린다. 절대 경로를 쓰는 이유: PATH 에
# 같은 이름의 사용자 스크립트가 있으면 그것이 실행될 수 있다.
MACOS_OPEN_COMMAND_PATH = "/usr/bin/open"
MACOS_PLATFORM_NAME = "darwin"
BROWSER_OPEN_TIMEOUT_SECONDS = 5
SERVER_RESTART_PORT_WAIT_SECONDS = 3
SERVER_RESTART_PORT_POLL_INTERVAL_SECONDS = 0.1
FORCED_STOP_NOTE = "정상 종료 신호에 응답하지 않아 강제 종료했습니다"
ORPHANED_HEARTBEAT_REASON = (
    "정지 직후에도 서버가 살아 있다고 판정됐습니다 — 고아 하트비트일 수 있습니다"
    "(`/hub server status` 의 orphaned_evidence 를 확인하십시오)"
)
```

### 순수 함수 2개 (단위 테스트 대상)

```python
def browser_open_command(platform_name: str, url: str) -> list[str] | None:
    """포커스까지 가져오며 URL 을 여는 외부 명령 argv. 지원 플랫폼이 아니면 None(webbrowser 폴백)."""

def restart_note(stop_result: dict) -> str | None:
    """stop 단계의 이례(PID 재사용·이미 종료·강제 종료)를 사용자에게 알릴 한 줄로 바꾼다. 정상이면 None."""
```

`browser_open_command` 규칙:

| # | 규칙 | 근거 |
|---|------|------|
| R1 | `platform_name == "darwin"` → `[MACOS_OPEN_COMMAND_PATH, url]` | D8 |
| R2 | 그 외 전부 → `None` | 리눅스·윈도우는 `webbrowser` 가 이미 창을 올린다. 검증할 수 없는 분기를 추측으로 만들지 않는다 |
| R3 | `url` 은 **argv 원소 하나**로 그대로 넣는다. 셸을 거치지 않는다 | `shell=True` 를 쓰면 `file:///Users/x y/…` 같은 공백 경로가 두 인자로 쪼개지고, 셸 메타문자 주입 표면이 생긴다 |

`restart_note` 규칙 (우선순위 순, 3줄):

| # | 조건 | 결과 |
|---|------|------|
| R4 | `stop_result.get("reason")` 이 있다 | 그 문구를 그대로 (한국어 설명은 `stop_server` 가 이미 만든다 — 문구를 두 곳에서 관리하지 않는다) |
| R5 | `stop_result.get("forced")` 가 참 | `FORCED_STOP_NOTE` (SIGKILL 이 필요했다는 것은 버그 신호이므로 조용히 넘기지 않는다) |
| R6 | 그 외 | `None` |

### I/O 함수 3개

```python
def open_browser(url: str, platform_name: str = sys.platform) -> hub_model.BrowserOpenResult:
    """포커스 경로로 URL 을 열고, 안 되면 webbrowser 로 폴백한다. 예외를 밖으로 내보내지 않는다."""

def restart_server() -> dict:
    """기존 서버를 확실히 내린 뒤 새로 띄운다(멱등 start 와 달리 항상 재기동한다).

    stop 이 실패하면 start 를 시도하지 않는다 — 낡은 서버가 살아 있을 수 있는 상태에서
    새로 띄우면 서버가 둘이 되려 시도하거나 포트 충돌로 엉뚱한 진단을 낸다.
    """

def _wait_for_port_release(port: int) -> None:
    """포트가 풀릴 때까지 최대 SERVER_RESTART_PORT_WAIT_SECONDS 동안 폴링한다(D5)."""
```

`restart_server()` 흐름 (약 20줄, 중첩 2단계 이하):

```
1. stop_result = stop_server()
2. stop_result["ok"] 가 거짓  → {"ok":false, "phase":"stop", "reason": stop_result["reason"]}  ← start 를 부르지 않는다
3. config 로드 → _wait_for_port_release(config.server_port)
4. start_result = start_server()
5. start_result.get("already_running")  → {"ok":false, "phase":"start", "reason": ORPHANED_HEARTBEAT_REASON}
6. start_result["ok"] 가 거짓  → {"ok":false, "phase":"start", "reason": …, "log_tail": …(있으면)}
7. 성공 → {"ok":true, "stopped_previous": stop_result["was_running"], "pid": …, "url": …}
          + restart_note(stop_result) 가 None 이 아니면 "note" 추가
```

### `hub/bin/hub.py` — 신설·변경

```python
def cmd_server_restart(args: argparse.Namespace) -> int:
    """`/hub server restart` — 기존 서버 종료 → 포트 해제 대기 → 재기동. 멱등이 아니다(항상 재기동)."""
```

- `subcommand_names` 에 `"server-restart"` 1항 추가(`server-status` 다음, `server-run` 앞).
- `COMMAND_HANDLERS` 에 `"server-restart": cmd_server_restart` 1항 추가.
- `_open_browser()` 삭제, `import webbrowser` 삭제.
- `cmd_open` 의 payload 조립부:

```python
    browser = hub_daemon.open_browser(url)
    payload = {
        "ok": True, "url": url, "server_alive": server_alive,
        "browser_opened": browser.opened,
        "browser_focus_requested": browser.focus_requested,   # ★신규
    }
    if browser.fallback_reason is not None:
        payload["browser_fallback_reason"] = browser.fallback_reason
```

> `cmd_open` 본문에 `start_server`·`server-start` 토큰이 새로 들어가지 않는다 —
> **T25-20**(암묵 기동 회귀 방지)이 그 두 토큰의 부재를 함수 본문에서 grep 으로 검사한다.

---

## 반환 JSON 계약 (필드 단위)

### `server-restart --json` (신규)

| 필드 | 타입 | 언제 | 뜻 |
|------|------|------|-----|
| `ok` | bool | 항상 | 재기동이 끝까지 성공했는가 |
| `stopped_previous` | bool | `ok:true` | 실제로 살아 있던 서버를 내렸는가(false = 원래 꺼져 있었다) |
| `pid` | int \| null | `ok:true` | 새 서버의 PID. `server.json` 을 못 읽으면 null |
| `url` | str | `ok:true` | `http://localhost:8794/hub.html` |
| `note` | str | 선택 | stop 단계의 이례(강제 종료 · PID 재사용 · 이미 종료). `restart_note` 의 결과 |
| `phase` | `"stop"` \| `"start"` | `ok:false` | 어느 단계에서 실패했는가 |
| `reason` | str | `ok:false` | 실패 사유(한국어 원문 그대로) |
| `log_tail` | str | 선택 | start 실패 시 `server.log` 꼬리 20줄 |

```json
{"ok": true, "stopped_previous": true, "pid": 41234, "url": "http://localhost:8794/hub.html"}
{"ok": true, "stopped_previous": false, "pid": 41250, "url": "http://localhost:8794/hub.html",
 "note": "PID 가 재사용됐습니다 — 그 프로세스는 건드리지 않고 상태 파일만 정리했습니다"}
{"ok": false, "phase": "stop", "reason": "ps 실행 실패 — 확인할 수 없어 아무것도 하지 않았습니다"}
{"ok": false, "phase": "start", "reason": "포트 8794 이 이미 사용 중입니다(다른 프로세스)"}
```

### `open --json` (기존 + 1~2필드)

| 필드 | 변화 |
|------|------|
| `ok`·`url`·`server_alive`·`browser_opened`·`note` | **그대로** (기존 `commands/hub.md` 보고 규칙 유효) |
| `browser_focus_requested` | **신규** bool — 포커스 경로로 열었는가 |
| `browser_fallback_reason` | **신규 선택** str — 포커스 경로 실패 사유(있을 때만) |

필드 **추가만** 한다(삭제·개명 없음) → 기존 보고 문구는 깨지지 않는다.

### 변경 없는 계약

`server-start` · `server-stop` · `server-status` · `status` · `collect` · 훅 이벤트 스키마 ·
`#dzh-data` JSON — **전부 무변경**.

---

## GOTCHA 목록

> **GOTCHA 1 — 멱등 start 를 force 로 바꾸지 마라.** `restart` 를 만드는 가장 짧은 길은
> `start_server()` 안의 `_server_already_running()` 분기를 없애는 것인데, 그러면 `/hub server
> start` 를 반복 호출하는 기존 문서·안내가 전부 "매번 서버를 죽였다 살리는" 동작으로 바뀐다.
> 멱등은 계약이다. T25-48 이 `"already_running": True` 리터럴의 존재를 grep 으로 지킨다.

> **GOTCHA 2 — 포트 오진.** stop 직후 `_is_port_occupied()` 가 참을 돌려주면 start 는
> "다른 프로세스가 점유 중"이라는 **틀린** 사유로 실패한다. 확인된 사실: `HTTPServer.
> allow_reuse_address = 1` 이라 `TIME_WAIT` 로 인한 bind 실패는 없고, 리스닝 소켓은 프로세스
> 사망과 함께 닫히므로 `connect_ex` 는 곧 거절된다. 남는 창은 SIGKILL 직후의 아주 짧은
> 순간뿐이다 — 그래서 대기는 **짧고 상한이 있어야**(3초) 하고, 초과하면 그냥 start 로 넘겨
> 정확한 실패 메시지를 받는다. 무한 대기·재시도 루프를 만들지 마라.

> **GOTCHA 3 — 테스트가 실제 브라우저를 띄운다.** `tests/hub/test_hub.py` 의 3개 테스트
> (101·120·136행)는 `mock.patch("webbrowser.open")` 으로 브라우저를 막고 있다. `cmd_open` 이
> `hub_daemon.open_browser` → `subprocess.run(["/usr/bin/open", …])` 로 바뀌면 **이 패치가
> 아무것도 막지 못해 `bash tests/run.sh` 가 탭 3개를 연다.** 반드시
> `mock.patch.object(hub_daemon, "open_browser", return_value=hub_model.BrowserOpenResult(...))`
> 로 교체한다. 수동 M7 이 이 회귀의 최종 확인이다.

> **GOTCHA 4 — 낡은 설치본.** `commands/hub.md` 가 `server-restart` 를 부르는데
> `~/.claude/hub/bin/hub.py` 가 옛 버전이면 `argparse` 가 `invalid choice: 'server-restart'`
> 로 **exit 2** 를 낸다. 이 경우 `hub/install.sh --force` 재실행이 답이다 — 커맨드 문서에
> 그 한 줄을 넣는다. `hub_daemon.py` 만 새 파일이고 `hub.py` 가 낡은 경우는 없다(둘 다 같은
> `cp -R` 로 배포된다).

> **GOTCHA 5 — 셸을 거치지 마라.** URL 은 `f"file://{HUB_HTML_PATH}"` 로도 만들어지고 홈
> 경로에는 공백이 들어갈 수 있다. `subprocess.run(argv_list, shell=False)` 만 쓴다.
> T25-49 가 `hub_daemon.py` 에 `shell=True` 가 없음을 검사한다.

> **GOTCHA 6 — `sys.platform` 을 함수 안에서 직접 읽지 마라.** 기본 인자
> (`platform_name: str = sys.platform`)로 받아야 세 플랫폼을 단위 테스트할 수 있다(D9).

> **GOTCHA 7 — 브라우저 실행 실패를 예외로 올리지 마라.** `open_browser` 는
> `OSError`·`subprocess.TimeoutExpired`·(webbrowser 의) 임의 예외를 모두 흡수하고
> `BrowserOpenResult(opened=False, …)` 를 돌려준다. 페이지를 못 연 것이 재기동 성공을
> 취소해서는 안 된다.

---

## 테스트 계획

검증 정본: `bash tests/run.sh`(전체) / `python3 -m unittest discover -s tests/hub -t .`(파이썬,
현재 기준선 **226 tests OK**). 이 저장소에는 별도 linter·type checker 설정이 없다.

### 자동 — 순수 로직 단위 테스트 (`tests/hub/test_hub_daemon.py`)

**신설 `BrowserOpenCommandTest`** (순수 — D9 의 존재 이유)

| # | 이름 | 입력 | 기대 |
|---|------|------|------|
| B1 | `test_b1_darwin_uses_open_command_that_focuses` | `("darwin", "http://localhost:8794/hub.html")` | `["/usr/bin/open", "http://localhost:8794/hub.html"]` |
| B2 | `test_b2_linux_falls_back_to_webbrowser` | `("linux", url)` | `None` |
| B3 | `test_b3_windows_falls_back_to_webbrowser` | `("win32", url)` | `None` |
| B4 | `test_b4_url_stays_one_argv_element_even_with_spaces` | `("darwin", "file:///Users/x y/.claude/hub/hub.html")` | 길이 2, `[1]` 이 원문과 완전히 동일(셸 인젝션 표면 부재의 회귀) |

**신설 `RestartNoteTest`** (순수)

| # | 이름 | 입력 | 기대 |
|---|------|------|------|
| N1 | `test_n1_clean_stop_has_no_note` | `{"ok":True,"was_running":True}` | `None` |
| N2 | `test_n2_forced_kill_is_reported` | `{"ok":True,"was_running":True,"forced":True}` | `FORCED_STOP_NOTE` |
| N3 | `test_n3_stop_reason_is_passed_through_verbatim` | `{"ok":True,"was_running":False,"reason":"PID 가 재사용됐습니다 …"}` | 그 문구 그대로(문구를 두 곳에서 관리하지 않는다) |

**신설 `RestartServerSequenceTest`** (I/O — `mock.patch.object` 로 `stop_server`·`start_server`·
`_wait_for_port_release` 를 대체. 기존 `HubDaemonIoScenarioTest` 의 임시 HUB_HOME 패턴을 재사용)

| # | 이름 | 시나리오 | 기대 |
|---|------|----------|------|
| S1 | `test_s1_stop_failure_never_starts_a_new_server` | stop → `{"ok":False,"reason":"ps 실행 실패 …"}` | `ok:false`, `phase=="stop"`, **`start_server` 가 호출되지 않았다**(요구 6 의 직접 회귀 테스트) |
| S2 | `test_s2_running_server_is_stopped_then_started` | stop → `{"ok":True,"was_running":True}`, start → `{"ok":True,"pid":2,"url":U}` | `ok:true`, `stopped_previous:true`, `pid==2`, `url==U`, `note` 없음. 호출 순서가 stop → 포트대기 → start |
| S2' | `test_s2b_absent_server_is_just_started` | stop → `{"ok":True,"was_running":False}` | `ok:true`, `stopped_previous:false` |
| S3 | `test_s3_already_running_after_stop_is_reported_as_failure` | start → `{"ok":True,"already_running":True}` | `ok:false`, `phase=="start"`, `reason` 에 `orphaned_evidence` 언급(D6) |
| S4 | `test_s4_forced_stop_surfaces_as_note` | stop → `{"ok":True,"was_running":True,"forced":True}`, start 성공 | `ok:true` + `note == FORCED_STOP_NOTE` (N2 와 조립되는지) |
| S5 | `test_s5_start_failure_carries_reason_and_log_tail` | start → `{"ok":False,"reason":R,"log_tail":L}` | `ok:false`, `phase=="start"`, `reason==R`, `log_tail==L` |

**신설 `OpenBrowserFallbackTest`** (I/O — `subprocess.run`·`webbrowser.open` 패치)

| # | 이름 | 시나리오 | 기대 |
|---|------|----------|------|
| O1 | `test_o1_darwin_success_does_not_touch_webbrowser` | darwin, `returncode=0` | `opened`·`focus_requested` 모두 True, `fallback_reason is None`, `webbrowser.open` **미호출** |
| O2 | `test_o2_darwin_failure_falls_back_with_reason` | darwin, `returncode=1` | `opened:True`, `focus_requested:False`, `fallback_reason` 이 채워짐, `webbrowser.open` 호출 |
| O3 | `test_o3_non_darwin_uses_webbrowser_only` | `"linux"` | `subprocess.run` 미호출, `opened:True`, `focus_requested:False` |
| O4 | `test_o4_both_paths_failing_is_not_an_exception` | darwin, `subprocess.run` 이 `OSError`, `webbrowser.open` 이 예외 | 예외 없음, `opened:False`(GOTCHA 7) |

### 자동 — 기존 테스트 수정 (`tests/hub/test_hub.py`)

| 위치 | 변경 |
|------|------|
| 101·120·136행 | `mock.patch("webbrowser.open")` → `mock.patch.object(hub_daemon, "open_browser", return_value=hub_model.BrowserOpenResult(opened=True, focus_requested=True, fallback_reason=None))` (**GOTCHA 3**) |
| `CmdOpenServerAwareTest` 에 1개 추가 | `test_open_payload_exposes_browser_focus_field` — payload 에 `browser_focus_requested` 키가 있다(계약 회귀) |

그 외 `tests/hub/` 전부 **무수정 통과**가 1차 회귀 안전망이다(특히 `StopServerCompareAndDeleteTest`
— stop 시퀀스를 건드리지 않았다는 증거).

### 자동 — `tests/run.sh` grep 회귀 (T25-48 · T25-49)

`test_hub_docs_and_constants()` 의 T25-47 블록 **다음**에 넣는다.
**2010행 주석과 2013행 `test_desc` 를 `T25-1~T25-49` 로 갱신할 것.**

```bash
  # T25-48(재기동 계약 회귀): server-restart 가 CLI·데몬·커맨드 문서 세 곳에 있고,
  # 그것을 만들면서 멱등 start 를 force 로 바꾸는 회귀(GOTCHA 1)가 없다.
  local restart_token
  for restart_token in "server-restart" "cmd_server_restart"; do
    if ! grep -qF "$restart_token" "$hub_py_file"; then
      record_failure "$test_name" "T25-48: hub.py 에 $restart_token 이 없음"
      return 1
    fi
  done
  for restart_token in "def restart_server" "def restart_note" "_wait_for_port_release"; do
    if ! grep -qF "$restart_token" "$hub_daemon_file"; then
      record_failure "$test_name" "T25-48: hub_daemon.py 에 $restart_token 이 없음"
      return 1
    fi
  done
  if ! grep -qF '"already_running": True' "$hub_daemon_file"; then
    record_failure "$test_name" "T25-48: start_server 의 멱등(already_running)이 사라짐 — restart 와 별도 경로여야 한다"
    return 1
  fi
  for restart_token in "server restart" "server-restart"; do
    if ! grep -qF "$restart_token" "$hub_command_file"; then
      record_failure "$test_name" "T25-48: commands/hub.md 에 $restart_token 이 없음"
      return 1
    fi
  done
  if ! grep -E '^argument-hint:' "$hub_command_file" | grep -qF "server restart"; then
    record_failure "$test_name" "T25-48: argument-hint 에 'server restart' 미노출"
    return 1
  fi

  # T25-49(브라우저 포커스 회귀): 포커스 경로가 hub_daemon 에 하나만 있고, 셸을 거치지 않으며,
  # hub.py 에는 webbrowser 직접 호출이 남지 않는다(경로 이중화 방지).
  local focus_token
  for focus_token in "def browser_open_command" "/usr/bin/open" "darwin" "webbrowser"; do
    if ! grep -qF "$focus_token" "$hub_daemon_file"; then
      record_failure "$test_name" "T25-49: hub_daemon.py 에 $focus_token 이 없음"
      return 1
    fi
  done
  if grep -qF "shell=True" "$hub_daemon_file"; then
    record_failure "$test_name" "T25-49: hub_daemon.py 가 shell=True 를 씀 — URL 을 셸에 넘기지 않는다"
    return 1
  fi
  if grep -qF "webbrowser" "$hub_py_file"; then
    record_failure "$test_name" "T25-49: hub.py 에 webbrowser 직접 호출이 남음 — hub_daemon.open_browser 로 단일화할 것"
    return 1
  fi
  if ! grep -qF "browser_focus_requested" "$hub_command_file"; then
    record_failure "$test_name" "T25-49: commands/hub.md 에 browser_focus_requested 보고 규칙이 없음"
    return 1
  fi
  for focus_token in "restart" "포커스"; do
    if ! grep -qF "$focus_token" "$hub_readme_file"; then
      record_failure "$test_name" "T25-49: hub/README.md 에 서버 제어 설명($focus_token)이 없음"
      return 1
    fi
  done
```

> `hub_py_file`·`hub_daemon_file`·`hub_command_file`·`hub_readme_file` 지역 변수는 이 함수
> 상단(및 T25-3 블록)에 **이미 선언돼 있다** — 재선언하지 않는다.

### 기존 자동 검사에 대한 영향 (확인 결과)

| 검사 | 판정 | 근거 |
|------|------|------|
| T22-5 (`COMMANDS_FILE_COUNT=9`) | 무영향 | 신규 커맨드 파일 0개(D1) |
| T25-1·T25-2 (`HUB_FILE_COUNT=11`) | 무영향 | 신규 배포 파일 0개(D10) |
| T25-20 (`cmd_open` 에 서버 기동 없음) | 무영향 | `cmd_open` 에 `start_server`·`server-start` 토큰이 새로 들어가지 않는다 |
| T25-21 (루트 `install.sh` 에 `hub` 0건) | 무영향 | 루트 `install.sh` 미수정 |
| T25-22 (README 허브 언급 14줄 이하) | 무영향 | 루트 `README.md` 미수정(현재 8줄) |
| T25-23 (`--uninstall` 의 `server-stop` 순서) | 무영향 | `hub/install.sh` 미수정 |
| T25-10 (순수 레이어에 파일시스템 접근 없음) | 무영향 | `hub_model.py` 에는 dataclass 만 추가 |
| T25-44·46·47 (템플릿 툴팁·타이틀·파비콘) | 무영향 | `hub_template.html` 0줄 변경 |

### 수동 확인 목록 (자동화 불가)

- [ ] **M1** — `/hub server start` 로 띄운 뒤 `/hub server restart` → `stopped_previous:true`,
      `pid` 가 **직전과 다르다**, `/hub server status` 가 `alive:true`
- [ ] **M2** — 서버가 꺼진 상태에서 `/hub server restart` → `stopped_previous:false`, 정상 기동
- [ ] **M3** — 재기동 직후 `/hub server status` → `crashed_evidence:false`,
      `orphaned_evidence:false`, `collect_stalled:false`, `http_ok:true`
- [ ] **M4** — 브라우저가 완전히 종료된 상태에서 재기동 → 브라우저 앱이 실행되며 포그라운드로 온다
- [ ] **M5** — **다른 앱 창이 맨 앞에 있는 상태**에서 재기동 → 대시보드 탭이 앞으로 나온다
      (요구의 핵심. 변경 전에는 탭만 열리고 창은 뒤에 남았다)
- [ ] **M6** — 포트를 남이 점유한 상태(`python3 -m http.server 8794`)에서 재기동 →
      `ok:false`·`phase:"start"`·"다른 프로세스" 메시지, **그 프로세스는 죽지 않는다**
- [ ] **M7** — `bash tests/run.sh` 전체 실행 중 **브라우저 탭이 하나도 열리지 않는다**
      (GOTCHA 3 의 최종 확인)
- [ ] **M8** — 재기동을 연속 2회 → 두 번째도 성공(포트 해제 대기가 동작한다)
- [ ] **M9** — 재기동 중(약 1~5초) 브라우저를 새로고침하면 연결 실패가 보이지만, 기동 완료 후
      다음 폴링에서 스스로 회복한다
- [ ] **M10** — 낡은 설치본으로 `/hub server restart` 호출 → exit 2 + `invalid choice` 를
      확인하고, 커맨드 문서의 안내대로 `hub/install.sh --force` 후 정상 동작(GOTCHA 4)
- 비-macOS 경로는 이 머신에서 실검증할 수 없다 → **B2·B3·O3 단위 테스트로 대체**(D9)

---

## 구현 마일스톤 (단계별 검증 기준)

| # | 범위 | 검증 |
|---|------|------|
| 1 | `hub_model.BrowserOpenResult` + `hub_daemon` 의 순수 함수 2개(`browser_open_command`·`restart_note`) + 상수 / 테스트 B1~B4·N1~N3 | `python3 -m unittest discover -s tests/hub -t .` 통과 |
| 2 | `hub_daemon.open_browser` + `hub.py` 의 `_open_browser` 삭제·`cmd_open` 배선 / `test_hub.py` 패치 3곳 교체 + 필드 테스트 / 테스트 O1~O4 | 파이썬 테스트 통과 + **수동 M7**(테스트가 탭을 열지 않는다) |
| 3 | `hub_daemon.restart_server` + `_wait_for_port_release` + `hub.py` 의 `cmd_server_restart`·파서·핸들러 / 테스트 S1~S5 | 파이썬 테스트 통과. `hub/install.sh --force` 후 수동 M1~M3·M6·M8 |
| 4 | 문서·검사: `commands/hub.md`(argument-hint·호출 규약·전용 절·`/hub` 보고 규칙·GOTCHA 4 안내) / `hub/README.md` / `tests/run.sh` T25-48·49 + 헤더 2곳 | `bash tests/run.sh` 전체 통과 + 수동 M4·M5·M9·M10 |

순서를 지켜야 한다: 2 는 1 의 dataclass·순수 함수를 쓰고, 3 은 2 의 배선이 끝나야 재기동 후
열기를 확인할 수 있다. 각 마일스톤은 그 자체로 커밋 가능하다.
**3 이후에는 `hub/install.sh --force` 없이는 수동 확인이 불가능하다** — 배포는 사용자 승인 사항
(승인 항목 5)이다.

---

## 리스크 목록

| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| 1 | **재기동마다 새 탭이 쌓인다**(macOS Chrome/Safari 는 같은 URL 도 새 탭으로 연다) | 잦은 재기동 시 탭 누적 | 범위 밖(위 「범위 밖」 표). 완화: 재기동 후에도 **기존 탭은 그대로 살아 있고** 30초 폴링으로 스스로 회복하므로, 대개 다시 열 필요가 없다. 누적이 실제로 거슬리면 후속 작업은 브라우저별 AppleScript 가 아니라 커맨드 문서에 "열기 생략" 선택지를 두는 방향이다 |
| 2 | **`/usr/bin/open` 이 실패하는 환경**(샌드박스·SSH 세션) | 포커스가 안 된다 | `webbrowser` 폴백으로 열기는 유지되고, `browser_fallback_reason` 이 사유를 표면화한다(O2) |
| 3 | **재기동 사이 1~5초 공백** | 그 순간 폴링이 연결 실패를 표시 | 정상 동작. 다음 틱에 회복(M9). 훅 폴백 수집도 계속 돈다 |
| 4 | **고아 하트비트 상태에서 재기동이 실패로 보고된다**(D6) | 사용자가 한 번 더 손을 써야 한다 | 그것이 의도다 — 조용한 `ok:true` 보다 낫다. 메시지가 `/hub server status` 확인을 지시한다. 해소 절차(`orphaned_evidence` 확인 → 필요 시 수동 정리)는 `hub/README.md` 의 기존 서술 범위 |
| 5 | **배포를 잊으면 새 커맨드가 exit 2 로 죽는다** | 사용자가 "커맨드가 깨졌다"고 느낀다 | GOTCHA 4 + 커맨드 문서의 1줄 안내 + 완료 보고에 `hub/install.sh --force` 명시(전제 1) |
| 6 | **`file://` URL 이 퍼센트 인코딩되지 않는다** — 홈 경로에 공백이 있으면 열기가 실패할 수 있다 | 공백 홈 경로 사용자만 | **기존 결함이며 이 변경이 만든 것이 아니다**(`webbrowser` 경로도 동일). 「발견 사항」에 언급만 한다 |
| 7 | **`restart` 가 `stop`+`start` 의 조합이라 두 함수의 변경에 취약** | 상류 변경 시 함께 깨진다 | 그것이 D3 의 대가이자 이득이다(로직 복제 없음). S1~S5 가 조합 계약을 고정한다 |

### 발견 사항 — 이번 변경이 만들지 않은 문제 (언급만 한다)

| # | 발견 | 처리 |
|---|------|------|
| 1 | `f"file://{HUB_HTML_PATH}"` 가 퍼센트 인코딩을 하지 않는다(리스크 6) | 언급만. 수정하면 URL 생성 규칙 변경 + 테스트 3곳 영향 → 별도 티켓 |
| 2 | `stop_server()` 는 `server.json` 이 없으면 하트비트 파일을 정리하지 않는다 — D6 이 다루는 고아 상태의 근원 | 언급만. 무조건 삭제는 compare-and-delete 의 취지에 반한다(D7). 고치려면 "하트비트만 있고 기록이 없을 때의 소유권 판정"이라는 별도 설계가 필요하다 |
| 3 | `hub/README.md` 「빠른 시작」이 `/hub server start` → `/hub` 2단계다 | `restart` 절 추가와 함께 자연히 언급되지만, 빠른 시작 절차 자체는 바꾸지 않는다 |

---

## 검토했으나 채택하지 않은 대안

1. **새 커맨드 파일 `commands/hub-server.md`(또는 `hub-restart.md`) 추가** — 옵션 B.
   "실행/종료 스킬"이라는 요청 문구에 가장 곧이곧대로 대응하고 발견성이 좋다. 그러나
   ① 같은 데몬을 제어하는 창구가 둘이 되어 정본이 흐려지고(`hub/README.md`·`--uninstall`·
   T25 는 `/hub server …` 를 참조한다), ② 배포 계약 5곳(`COMMANDS_FILE_COUNT` 9→10, 루트
   README 3곳, T22-5)이 흔들리고, ③ `/hub` 의 `argument-hint` 는 이미 서브커맨드를 전부
   노출하므로 발견성 이득도 크지 않다 → **기각**(결정 D1, 승인 항목 1 에서 재확인).
2. **`skills/` 디렉토리를 새로 만들고 `SKILL.md` 로 작성** — 이 저장소에는 `skills/` 가
   없다(설치 대상은 `rules/`·`agents/`·`commands/` 셋뿐). 새 설치 대상 디렉토리 + 개수 상수 +
   README 표 + 검사 추가가 필요한 **배포 레이어 변경**이며, 사용자 CLAUDE.md 는 일관되게
   `commands/*.md` 를 "스킬"이라 부른다(`/prp-plan` 스킬, `/code-review` 스킬). 게다가
   SKILL.md 형식은 모델이 읽는 참조 자료에 적합하고, 이 작업은 **결정론적인 2단계 CLI 호출**
   이라 슬래시 커맨드가 올바른 형태다 → **기각**.
3. **`start_server()` 에 `force` 플래그를 추가** — 코드가 가장 적다. 그러나 멱등 계약이
   플래그 하나에 달리게 되고, `--force` 를 빼먹은 호출이 조용히 다른 의미가 된다. 무엇보다
   "기존 서버를 죽인다"는 파괴적 동작이 `start` 라는 이름 뒤로 숨는다 → **기각**(D3).
4. **`commands/hub.md` 에서 `server-stop` → `server-start` 를 순차 호출**(Python 변경은
   `_open_browser` 뿐). 가장 작은 변경이다. 그러나 ① "stop 이 실패하면 중단"·"포트 해제
   대기"·"고아 하트비트 판정" 세 규칙이 전부 자연어 지시에 의존해 **결정론적이지 않고**,
   ② 단위 테스트할 표면이 0 이라 회귀를 잡을 수단이 없다 → **기각**. 재기동은 서버를
   죽이는 동작이므로 실패 처리가 LLM 의 해석에 달려서는 안 된다.
5. **`server-restart` 가 브라우저까지 직접 연다**(한 번의 CLI 호출로 끝). 호출이 하나라
   커맨드 문서가 더 짧다. 그러나 `open` 이 이미 갖고 있는 "서버 살아 있으면 http, 아니면
   1회 수집 후 `file://`" 판정을 복제하거나 서브커맨드가 책임 셋을 갖게 된다 →
   **기각**(D12, 승인 항목 3 에서 재확인).
6. **브라우저별 AppleScript 로 기존 탭을 재사용**(`tell application "Google Chrome" … set
   URL of tab …`). 탭 누적을 없앤다. 그러나 Safari·Chrome·Arc·Firefox 가 각각 다른 스크립트를
   요구하고, 기본 브라우저를 알아내는 신뢰할 만한 방법도 없다. 유지 비용이 이득(미용 문제
   하나)보다 훨씬 크다 → **기각**(범위 밖).
7. **`hub_browser.py` 신규 모듈로 브라우저 실행 분리.** 관심사 분리는 더 깨끗하다. 그러나
   함수 3개(약 25줄)를 위해 `HUB_FILE_COUNT` 11→12 + T25-1·T25-2 재확인 + 배포 검증까지
   3곳을 바꿔야 한다. `hub_daemon.py` 는 230줄로 여유가 있고 "외부 프로세스 spawn" 이라는
   책임이 정확히 일치한다 → **기각**(D10).
8. **`launchd`(macOS) 로 서버를 등록해 재기동을 OS 에 위임.** 크래시 부활·재부팅 기동까지
   공짜로 얻는다. 그러나 `hub_daemon.py` 라는 이름 자체가 "특정 OS 서비스 관리자에 묶이지
   않는다"는 확정 결정(개정 쟁점 R1)의 산물이고, 재부팅 후 자동 기동은 명시적으로 범위
   밖이다 → **기각**.
9. **재기동을 `hub.py` 안에서 `cmd_server_stop` → `cmd_server_start` 호출로 구성.**
   `hub_daemon` 변경이 없다. 그러나 커맨드 핸들러는 `_report` 로 **stdout 에 JSON 을 찍는
   것**이 책임이라, 두 번 호출하면 JSON 이 두 줄 나와 `--json` 계약이 깨진다 → **기각**.
   조합은 순수한 반환값 레이어(`hub_daemon`)에서 해야 한다.

---

## 사용자 승인이 필요한 항목

### 승인 항목 1 — 창구 설계: `/hub` 확장 vs 새 커맨드 파일 (결정 D1 · 이 설계의 핵심 쟁점)

| 안 | 사용자 호출 | 영향 파일 | 장단 |
|----|-------------|-----------|------|
| **A. `/hub` 확장** (권고) | `/hub server restart` | 8개 (배포 레이어 **0**) | 데몬 제어 창구가 하나로 유지된다. `commands/hub.md` 는 이미 "얇은 호출자"라 1행 추가가 그 문서의 형식이다. `COMMANDS_FILE_COUNT`·루트 README·T22-5 무영향 |
| B. 새 커맨드 파일 | 예: `/hub-server restart` | 9개 + 배포 5곳 | 발견성이 약간 좋다. 대가: 같은 서버를 제어하는 문서가 둘(어느 쪽이 정본인지 계속 물어야 한다), 배포 개수 상수·루트 README 3곳·T22-5 갱신 |

B 를 택할 경우 갱신 대상을 미리 확정해 둔다: `install.sh:14` 의 `COMMANDS_FILE_COUNT=9` → `10`,
루트 `README.md` 의 `| commands/ | 9 |`(89행) · `commands 9개`(94행) · `9개 커맨드 … 독립 커맨드
2종`(320행), 그리고 T25-22 의 허브 언급 14줄 상한(현재 8줄) 여유 확인.

### 승인 항목 2 — `/hub server start` 도 브라우저를 열게 할까 (결정 D13)

| 안 | 동작 | 비고 |
|----|------|------|
| **A. 열지 않는다** (권고) | `start` 는 지금과 완전히 동일 | 기존 계약 무변경. "열기"는 `/hub` 또는 `restart` 의 일이다 |
| B. `start` 도 열고 포커스한다 | 처음 켤 때도 한 번에 본다 | 기존 동작 변경(부수 효과로 브라우저가 뜬다). 스크립트/문서에서 `server-start` 를 부르던 흐름이 놀란다 |

### 승인 항목 3 — 브라우저 열기를 CLI 안에 넣을까, 커맨드 문서에서 조합할까 (결정 D12)

| 안 | 구성 | 비고 |
|----|------|------|
| **A. 커맨드 문서에서 조합** (권고) | `server-restart --json` → (`ok:true` 면) `open --json` | 서브커맨드가 각각 한 책임. `open` 의 URL 판정(http vs `file://`)을 재사용. 대가: 커맨드 문서가 JSON 두 개를 읽고 보고한다 |
| B. `server-restart` 가 직접 연다 | 호출 1회, JSON 1개 | 커맨드 문서가 짧다. 대가: URL 판정 복제 또는 서브커맨드가 책임 셋 보유 |

### 승인 항목 4 — 탭 중복을 이번에 다룰까 (범위 밖 판단)

권고: **다루지 않는다.** 재기동 후에도 기존 탭은 살아 있고 스스로 회복하므로 실사용에서
탭이 누적될 상황이 많지 않다. 브라우저별 AppleScript 는 유지 비용이 이득을 크게 넘는다(대안 6).
다르게 판단하면 "열기를 생략하는 선택지"를 커맨드 문서에 두는 방향으로 별도 설계한다.

### 승인 항목 5 — 배포(`hub/install.sh --force`) 실행 시점

이 변경은 `~/.claude/hub/bin/` 에 반영되기 전까지 **수동 확인(M1~M6·M8~M10)이 불가능**하다.
마일스톤 3 이후 어느 시점에 `hub/install.sh --force` 를 실행할지, 그리고 그 실행을 누가 할지
(구현자가 승인받아 실행 / 사용자가 직접 실행) 확정이 필요하다. 배포 직후에는 서버가 여전히
**옛 코드로 돌고 있다** — 첫 `/hub server restart` 가 새 코드로 갈아 끼우는 첫 사용례가 된다.

### 승인 항목 6 — 착수 지시서 정정 확인

착수 지시서의 두 사실(작업트리 clean / T25 최대 번호 45)이 실제와 다르다(「출발 상태」).
새 검사 번호를 **T25-48·49** 로 부여하고 헤더를 `T25-1~T25-49` 로 갱신하는 것으로 확정한다.
또한 미커밋 상태(`hub_template.html`·`tests/run.sh`)를 **이 작업 전에 커밋할지**, 아니면
그 위에 얹을지 확인이 필요하다 — 얹는 경우 이 PRP 의 변경과 무관한 diff 가 같은 커밋에
섞이지 않도록 주의한다.
