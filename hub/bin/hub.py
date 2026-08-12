#!/usr/bin/env python3
"""hub.py — CLI 엔트리. 서브커맨드 디스패치와 I/O 조립. commands/hub.md 가 이 서브커맨드들을 호출한다.

`/hub`(인자 없음)는 서버를 기동하지 않는다(요구 R-2) — 하트비트가 신선하면 그 URL 을 열고,
아니면 1회만 수집한다. 상주 서버 제어는 `server-start`/`server-stop`/`server-status`/`server-run`
(포그라운드 디버깅용 진입점)이 전담한다(docs/prps/hub-dashboard.md 개정 쟁점 R1·R2).
"""

import argparse
import dataclasses
import json
import sys
import time
import webbrowser

import hub_collect
import hub_daemon
import hub_model
import hub_server
import hub_settings
import hub_usage


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


def _server_is_alive() -> tuple[bool, hub_model.HubConfig]:
    config, _config_warnings = hub_collect.load_config()
    ttl_ms = hub_model.server_heartbeat_ttl_ms(config.server_collect_interval_seconds)
    heartbeat_mtime_ms = hub_collect.read_server_heartbeat_mtime_ms()
    return hub_model.is_server_alive(_now_ms(), heartbeat_mtime_ms, ttl_ms), config


def _open_browser(url: str) -> bool:
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def cmd_open(args: argparse.Namespace) -> int:
    """서버가 살아 있고 hub.html 도 실재하면 수집 없이 그 URL 을 연다. 그 외에는 1회만
    수집하고 `file://` 를 연다.

    어떤 분기에서도 서버를 기동하지 않는다(요구 R-2) — "자동으로 뜨지 않는다"가 이 함수의
    존재 이유다. 초판의 임시 서버 암묵 기동은 이 개정에서 완전히 제거됐다.

    `server_alive`(하트비트)만 보고 URL 을 결정하지 않는다(검수 M1) — 하트비트가 신선해도
    `hub.html` 이 아직 없거나(막 기동해 첫 사이클 전) 지워졌으면 그 URL 은 404 를 반환한다.
    `hub.html` 실재까지 확인해야 사용자가 깨진 링크를 열지 않는다.
    """
    server_alive, config = _server_is_alive()
    server_ready = server_alive and hub_collect.HUB_HTML_PATH.exists()
    note = None
    if server_ready:
        url = f"http://localhost:{config.server_port}/hub.html"
    else:
        try:
            _collect_and_write()
        except Exception as error:
            hub_collect.record_collect_failure(str(error))
            _report({"ok": False, "reason": f"collect 실패: {error}"}, args.json)
            return 1
        url = f"file://{hub_collect.HUB_HTML_PATH}"
        if server_alive:
            note = (
                "허브 서버는 살아 있지만 hub.html 이 아직 없어 이번 한 번만 직접 수집했습니다. "
                "서버가 다음 수집 주기에 자동으로 다시 만듭니다."
            )
        else:
            note = (
                "허브 서버가 꺼져 있어 이번 한 번만 수집했습니다. "
                "`/hub server start` 로 켜면 항상 최신 상태가 유지됩니다."
            )

    payload = {
        "ok": True, "url": url, "server_alive": server_alive,
        "browser_opened": _open_browser(url),
    }
    if note is not None:
        payload["note"] = note
    _report(payload, args.json)
    return 0


def _rate_limit_capture_age_ms(now_ms: int, config: hub_model.HubConfig) -> int | None:
    """진단용 — 한도 초기화 시각 캡처의 나이(ms). 스위치 off·캡처 부재·계약 불일치면 None.

    리셋 줄이 안 보이는 이유(①statusLine 미설치 ②세션 미실행 ③리셋 시각이 이미 지남
    ④show_usage_panel:false)는 화면상 전부 "줄 없음"으로 똑같이 보인다 — 이 필드와
    아래 rate_limit_resets_remaining_ms 가 원인을 구분하는 유일한 창구다.
    스위치가 꺼져 있으면 캡처 파일을 열지도 않는다(PRP 「확정된 전제」4 — show_usage_panel:false
    는 usage 파일뿐 아니라 rate_limits 캡처 파일도 읽지 않는다).
    """
    if not config.show_usage_panel:
        return None
    resets, _warnings = hub_collect.read_rate_limit_capture()
    if resets is None:
        return None
    return now_ms - resets.captured_at_ms


def _rate_limit_resets_remaining_ms(now_ms: int, config: hub_model.HubConfig) -> dict | None:
    """진단용 — 아직 지나지 않은 리셋까지 남은 시간(ms). 스위치 off·캡처 없음이면 None."""
    if not config.show_usage_panel:
        return None
    resets, _warnings = hub_collect.read_rate_limit_capture()
    if resets is None:
        return None
    remaining = hub_usage.drop_passed_resets(resets, now_ms)
    session_remaining_ms = None
    weekly_remaining_ms = None
    if remaining is not None:
        if remaining.session_resets_at_ms is not None:
            session_remaining_ms = remaining.session_resets_at_ms - now_ms
        if remaining.weekly_resets_at_ms is not None:
            weekly_remaining_ms = remaining.weekly_resets_at_ms - now_ms
    return {"session": session_remaining_ms, "weekly": weekly_remaining_ms}


def _usage_sample_age_ms(now_ms: int, config: hub_model.HubConfig) -> int | None:
    """진단용 — 사용량 샘플의 나이(ms). 스위치 off·파일 없음·계약 불일치면 None.

    만료 여부와 무관하게 나이를 보고한다 — 패널이 안 보이는 네 가지 이유(스위치 off·파일
    없음·계약 불일치·만료)는 화면상 전부 "패널 없음"으로 똑같이 보이는데, 계약 불일치만
    warnings 로 드러나므로 나머지를 구분할 창구가 이 필드뿐이다
    (docs/prps/hub-theme-and-usage-panel.md).
    """
    if not config.show_usage_panel:
        return None
    sample, _warnings = hub_collect.read_latest_usage_sample()
    if sample is None:
        return None
    return now_ms - sample.sampled_at_ms


def cmd_status(args: argparse.Namespace) -> int:
    """훅 설치 상태 · 이벤트 · 마지막 수집 실패 · 서버 요약 · 사용량 진단을 보고한다(검수 R3-m2)."""
    now_ms = _now_ms()
    hook_status = hub_settings.hook_install_status()
    today_events, event_read_warnings = hub_collect.read_recent_events(now_ms)
    last_collected_ms = (
        int(hub_collect.HUB_HTML_PATH.stat().st_mtime * 1000) if hub_collect.HUB_HTML_PATH.exists() else None
    )
    server = hub_daemon.server_status()
    config, _config_warnings = hub_collect.load_config()
    _report(
        {
            "ok": True,
            "hooks_installed": hook_status,
            "events_today_and_yesterday": len(today_events),
            "event_read_warnings": list(event_read_warnings),
            "last_collected_at_ms": last_collected_ms,
            "last_collect_failure": hub_collect.read_last_collect_failure(),
            "server_alive": server.alive,
            "server_crashed_evidence": server.crashed_evidence,
            "server_collect_stalled": server.collect_stalled,
            "usage_panel_enabled": config.show_usage_panel,
            "usage_sample_age_ms": _usage_sample_age_ms(now_ms, config),
            "statusline_installed": hub_settings.statusline_install_status(),
            "rate_limit_capture_age_ms": _rate_limit_capture_age_ms(now_ms, config),
            "rate_limit_resets_remaining_ms": _rate_limit_resets_remaining_ms(now_ms, config),
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


def cmd_install_statusline(args: argparse.Namespace) -> int:
    """`/hub statusline on` — settings.json 에 우리 statusLine 을 넣는다(멱등, 충돌 시 거부)."""
    result = hub_settings.install_statusline()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_uninstall_statusline(args: argparse.Namespace) -> int:
    """`/hub statusline off` — 우리 statusLine 만 제거한다."""
    result = hub_settings.uninstall_statusline()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_server_start(args: argparse.Namespace) -> int:
    """`/hub server start` — 상주 서버 기동(세션 무관 분리 프로세스). 멱등."""
    result = hub_daemon.start_server()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_server_stop(args: argparse.Namespace) -> int:
    """`/hub server stop` — 신원 확인 → SIGTERM → 필요 시 SIGKILL → 상태 파일 정리."""
    result = hub_daemon.stop_server()
    _report(result, args.json)
    return 0 if result.get("ok") else 1


def cmd_server_status(args: argparse.Namespace) -> int:
    """`/hub server status` — 프로세스 · 하트비트 · HTTP 응답 · 비정상 종료 흔적 보고."""
    _report(dataclasses.asdict(hub_daemon.server_status()), args.json)
    return 0


def cmd_server_run(args: argparse.Namespace) -> int:
    """`server-run` — 상주 서버 본체(포그라운드로 블로킹). `server-start` 가 spawn 하는
    내부 엔트리이며, 사람이 직접 부르는 것은 포그라운드 디버깅용이다."""
    config, _config_warnings = hub_collect.load_config()
    return hub_server.run_server(config)


def build_parser() -> argparse.ArgumentParser:
    """서브커맨드마다 --json 을 개별 지원한다(호출 예시가 서브커맨드 뒤에 --json 을 둔다)."""
    parser = argparse.ArgumentParser(prog="hub.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subcommand_names = (
        "collect", "open", "status", "install-hooks", "uninstall-hooks",
        "install-statusline", "uninstall-statusline",
        "server-start", "server-stop", "server-status", "server-run",
    )
    for name in subcommand_names:
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--json", action="store_true")
    return parser


COMMAND_HANDLERS = {
    "collect": cmd_collect,
    "open": cmd_open,
    "status": cmd_status,
    "install-hooks": cmd_install_hooks,
    "uninstall-hooks": cmd_uninstall_hooks,
    "install-statusline": cmd_install_statusline,
    "uninstall-statusline": cmd_uninstall_statusline,
    "server-start": cmd_server_start,
    "server-stop": cmd_server_stop,
    "server-status": cmd_server_status,
    "server-run": cmd_server_run,
}


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return COMMAND_HANDLERS[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
