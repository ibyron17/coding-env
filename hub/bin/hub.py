#!/usr/bin/env python3
"""hub.py — CLI 엔트리. 서브커맨드(collect/open/serve/stop/install-hooks/uninstall-hooks/status)
디스패치와 I/O 조립. commands/hub.md 가 이 서브커맨드들을 호출한다.

`serve` 의 기본 포트 후보(hub_model.HubConfig.serve_port_candidates)는 8794·8795·8796 이다 —
`/dashboard` 가 쓰는 포트대와 겹치지 않게 분리했다(docs/prps/hub-dashboard.md 쟁점 6).
"""

import argparse
import json
import sys
import time
import webbrowser

import hub_collect
import hub_model
import hub_settings

MIN_PORT = 1024
MAX_PORT = 65535


def _now_ms() -> int:
    return int(time.time() * 1000)


def _report(payload: dict, as_json: bool) -> None:
    """결과를 JSON 한 줄 또는 사람이 읽을 줄글로 출력한다."""
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _collect_and_write() -> hub_model.HubSnapshot:
    """공용 collect+write 시퀀스. 실패하면 원인을 관측 가능한 위치에 남기고 그대로 올린다(검수 M7)."""
    snapshot = hub_collect.collect_snapshot(_now_ms())
    hub_collect.write_hub_html(snapshot)
    hub_collect.clear_collect_failure()
    return snapshot


def cmd_collect(args: argparse.Namespace) -> int:
    """수집 후 hub.html 만 갱신한다(발행·브라우저 열기는 하지 않는다).

    예상치 못한 예외를 여기서 잡아 `{"ok": false, "reason": ...}` 계약으로 보고한다(검수 M7) —
    PRP 설계 결정 5(예외를 던지는 경로는 settings.json 파싱 실패 하나뿐)를 collect 경로에도 지킨다.
    """
    try:
        snapshot = _collect_and_write()
    except Exception as error:
        hub_collect.record_collect_failure(str(error))
        _report({"ok": False, "reason": f"collect 실패: {error}"}, args.json)
        return 1
    _report(
        {"ok": True, "projects": len(snapshot.projects), "hub_html": str(hub_collect.HUB_HTML_PATH)},
        args.json,
    )
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """수집 → hub.html 갱신 → 발행(서버 재사용/기동) → 브라우저 열기."""
    try:
        _collect_and_write()
    except Exception as error:
        hub_collect.record_collect_failure(str(error))
        _report({"ok": False, "reason": f"collect 실패: {error}"}, args.json)
        return 1
    serve_result = hub_collect.start_serving(None)
    url = serve_result.get("url") if serve_result.get("ok") else f"file://{hub_collect.HUB_HTML_PATH}"
    try:
        webbrowser.open(url)
        opened = True
    except Exception:
        opened = False
    _report({"ok": True, "url": url, "served": bool(serve_result.get("ok")), "browser_opened": opened}, args.json)
    return 0


def _parse_serve_args(raw_args: list[str]) -> tuple[str, int | None] | None:
    """`serve [포트]` 또는 `serve stop [포트]` 를 (action, port) 로 해석한다. 실패하면 None."""
    if not raw_args:
        return "start", None
    if raw_args[0] == "stop":
        if len(raw_args) == 1:
            return "stop", None
        return ("stop", int(raw_args[1])) if raw_args[1].isdigit() else None
    return ("start", int(raw_args[0])) if raw_args[0].isdigit() else None


def cmd_serve(args: argparse.Namespace) -> int:
    """`/hub serve [포트]` · `/hub serve stop [포트]`."""
    parsed = _parse_serve_args(args.args)
    if parsed is None:
        _report({"ok": False, "reason": "포트는 1024~65535 숫자여야 합니다"}, args.json)
        return 1
    action, port = parsed
    if port is not None and not (MIN_PORT <= port <= MAX_PORT):
        _report({"ok": False, "reason": "포트는 1024~65535 범위여야 합니다"}, args.json)
        return 1
    result = hub_collect.stop_serving(port) if action == "stop" else hub_collect.start_serving(port)
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    """훅 6개 설치 여부, 오늘 이벤트 수, 마지막 수집 시각, 마지막 collect 실패(있으면)를 보고한다."""
    hook_status = hub_settings.hook_install_status()
    today_events, event_read_warnings = hub_collect.read_recent_events(_now_ms())
    last_collected_ms = (
        int(hub_collect.HUB_HTML_PATH.stat().st_mtime * 1000) if hub_collect.HUB_HTML_PATH.exists() else None
    )
    _report(
        {
            "ok": True,
            "hooks_installed": hook_status,
            "events_today_and_yesterday": len(today_events),
            "event_read_warnings": list(event_read_warnings),
            "last_collected_at_ms": last_collected_ms,
            "last_collect_failure": hub_collect.read_last_collect_failure(),
        },
        args.json,
    )
    return 0


def cmd_install_hooks(args: argparse.Namespace) -> int:
    """`/hub install` — 훅 6개를 옵트인으로 설치한다(멱등)."""
    result = hub_settings.install_hooks()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_uninstall_hooks(args: argparse.Namespace) -> int:
    """`/hub off` — 마커가 붙은 우리 훅 엔트리만 제거한다."""
    result = hub_settings.uninstall_hooks()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    """서브커맨드마다 --json 을 개별 지원한다(호출 예시가 서브커맨드 뒤에 --json 을 둔다)."""
    parser = argparse.ArgumentParser(prog="hub.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("collect", "open", "status", "install-hooks", "uninstall-hooks"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--json", action="store_true")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--json", action="store_true")
    serve_parser.add_argument("args", nargs="*")
    return parser


COMMAND_HANDLERS = {
    "collect": cmd_collect,
    "open": cmd_open,
    "serve": cmd_serve,
    "status": cmd_status,
    "install-hooks": cmd_install_hooks,
    "uninstall-hooks": cmd_uninstall_hooks,
}


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return COMMAND_HANDLERS[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
