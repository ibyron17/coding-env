"""hub_settings.py — ~/.claude/settings.json 의 훅 6개를 병합 설치/제거한다.

settings.json 소유권 원칙(docs/prps/session-dashboard.md 설계 결정 4)을 따른다 — install.sh 는
이 파일을 건드리지 않는다. `/hub install`·`/hub off` 로 사용자가 명시적으로 부를 때만 이 모듈이 손댄다.
기존 훅(CAM 의 curl 엔트리, Litmus 등)은 절대 읽지도 고치지도 않는다 — 마커로만 우리 엔트리를 찾는다.

병합/제거 로직(merge_hub_hooks·strip_hub_hooks)은 ★순수하다 — settings dict 를 입력으로 받아
새 dict 를 돌려주고 원본은 바꾸지 않는다. 스키마가 어긋나면(hooks 가 객체가 아님 등) 예외를 던져
호출자가 `ok:false` 로 변환한다(검수 m1·m2, tests/hub/test_hub_settings.py 대상).
"""

import copy
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
HOOK_MARKER = "# DZH_HUB_HOOK"
HOOK_COMMAND = (
    'python3 "$HOME/.claude/hub/bin/hub_hook.py" >/dev/null 2>&1 || true   ' + HOOK_MARKER
)
HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "SessionEnd",
)
SETTINGS_PARSE_ERROR = "settings.json 파싱 실패 — 손대지 않고 중단합니다"


class HubHooksSchemaError(Exception):
    """settings.json 의 'hooks' 구조가 예상(객체 → 이벤트별 배열)과 다를 때 발생한다."""


def _entry_has_hub_marker(entry: object) -> bool:
    """entry 가 dict 가 아니거나 hooks 가 배열이 아니면 조용히 False — 손상 스키마에도 트레이스백을 내지 않는다."""
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks", [])
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(hook, dict) and HOOK_MARKER in str(hook.get("command", ""))
        for hook in hooks
    )


def _hub_hook_entry() -> dict:
    """matcher 없는 엔트리 1개 — CAM 의 기존 엔트리와 같은 모양이다."""
    return {"hooks": [{"type": "command", "command": HOOK_COMMAND}]}


def _validated_entries(hooks: dict, event_name: str) -> list:
    """hooks[event_name] 이 배열이 아니면 HubHooksSchemaError."""
    entries = hooks.get(event_name, [])
    if not isinstance(entries, list):
        raise HubHooksSchemaError(f"settings.json 의 hooks.{event_name} 이 배열이 아닙니다")
    return entries


def _validated_hooks_container(settings: dict) -> dict:
    """settings['hooks'] 가 없으면 빈 dict, 있는데 dict 가 아니면 HubHooksSchemaError."""
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise HubHooksSchemaError("settings.json 의 'hooks' 가 객체가 아닙니다")
    return hooks


def merge_hub_hooks(settings: dict) -> dict:
    """훅 6개를 matcher 없는 엔트리로 append 한 새 settings dict 를 돌려준다(입력 불변, 멱등)."""
    new_settings = copy.deepcopy(settings)
    hooks = _validated_hooks_container(new_settings)
    for event_name in HOOK_EVENTS:
        entries = _validated_entries(hooks, event_name)
        if not any(_entry_has_hub_marker(entry) for entry in entries):
            entries = [*entries, _hub_hook_entry()]
        hooks[event_name] = entries
    new_settings["hooks"] = hooks
    return new_settings


def strip_hub_hooks(settings: dict) -> dict:
    """마커가 붙은 엔트리만 제거한 새 settings dict 를 돌려준다(입력 불변).

    우리 엔트리를 제거해서 비게 된 키만 pop 한다 — 원래(우리가 만들지 않고) 이미 비어 있던
    키는 손대지 않는다(검수 n2). `hooks` 전체가 비면 `hooks` 를 지운다.
    """
    new_settings = copy.deepcopy(settings)
    if "hooks" not in new_settings:
        return new_settings
    hooks = _validated_hooks_container(new_settings)
    for event_name in HOOK_EVENTS:
        entries = _validated_entries(hooks, event_name)
        if not entries:
            continue  # 이미 비어 있던 키는 우리가 만든 게 아니므로 보존한다
        kept = [entry for entry in entries if not _entry_has_hub_marker(entry)]
        if kept:
            hooks[event_name] = kept
        else:
            hooks.pop(event_name, None)
    if hooks:
        new_settings["hooks"] = hooks
    else:
        new_settings.pop("hooks", None)
    return new_settings


def hook_install_status_from_settings(settings: dict) -> dict[str, bool]:
    """settings dict 하나로부터 6개 이벤트 각각의 설치 여부를 판정한다(순수)."""
    try:
        hooks = _validated_hooks_container(settings)
    except HubHooksSchemaError:
        return {event_name: False for event_name in HOOK_EVENTS}
    result = {}
    for event_name in HOOK_EVENTS:
        try:
            entries = _validated_entries(hooks, event_name)
        except HubHooksSchemaError:
            entries = []
        result[event_name] = any(_entry_has_hub_marker(entry) for entry in entries)
    return result


# ---- I/O 경계 ----
def _load_settings() -> dict | None:
    """settings.json 을 읽어 판다. 파일이 없으면 빈 dict, 파싱 실패면 None(중단 신호)."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _backup_timestamp() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H-%M-%S-") + f"{now.microsecond // 1000:03d}Z"


def _write_settings_atomically(settings: dict) -> None:
    """백업 후 프로세스마다 고유한 임시 파일에 쓰고 원자적으로 교체한다.

    고정된 임시 파일명을 공유하면 동시 쓰기가 뒤섞인 파일을 발행할 수 있다(검수 M2) —
    `tempfile.mkstemp` 로 매 호출마다 고유한 이름을 받는다. `mkstemp` 는 새 파일을 0600 으로
    만드므로, 기존 파일이 있으면 교체 전에 그 파일 모드를 그대로 옮긴다(검수 n1) — 그러지
    않으면 사용자의 `settings.json` 권한이 0644 에서 조용히 0600 으로 바뀐다.
    """
    if SETTINGS_PATH.exists():
        backup_path = SETTINGS_PATH.with_name(f"settings.json.bak-{_backup_timestamp()}")
        backup_path.write_bytes(SETTINGS_PATH.read_bytes())

    temp_fd, temp_name = tempfile.mkstemp(
        dir=SETTINGS_PATH.parent, prefix="settings.json.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
        if SETTINGS_PATH.exists():
            shutil.copymode(SETTINGS_PATH, temp_path)
        temp_path.replace(SETTINGS_PATH)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def install_hooks() -> dict:
    """훅 6개를 matcher 없는 엔트리로 append 한다. 이미 있으면 건드리지 않는다(멱등)."""
    settings = _load_settings()
    if settings is None:
        return {"ok": False, "reason": SETTINGS_PARSE_ERROR}

    before_status = hook_install_status_from_settings(settings)
    try:
        merged = merge_hub_hooks(settings)
    except HubHooksSchemaError as error:
        return {"ok": False, "reason": str(error)}
    after_status = hook_install_status_from_settings(merged)

    installed = [name for name in HOOK_EVENTS if after_status[name] and not before_status[name]]
    already_installed = [name for name in HOOK_EVENTS if before_status[name]]
    if installed:
        _write_settings_atomically(merged)
    return {"ok": True, "installed": installed, "already_installed": already_installed}


def uninstall_hooks() -> dict:
    """마커가 붙은 엔트리만 제거한다. 배열이 비면 그 키를, hooks 가 비면 hooks 를 지운다."""
    settings = _load_settings()
    if settings is None:
        return {"ok": False, "reason": SETTINGS_PARSE_ERROR}

    before_status = hook_install_status_from_settings(settings)
    try:
        stripped = strip_hub_hooks(settings)
    except HubHooksSchemaError as error:
        return {"ok": False, "reason": str(error)}

    removed = [name for name in HOOK_EVENTS if before_status[name]]
    if removed:
        _write_settings_atomically(stripped)
    return {"ok": True, "removed": removed}


def hook_install_status() -> dict[str, bool]:
    """6개 이벤트 각각의 설치 여부를 이벤트명 → bool 로 보고한다."""
    settings = _load_settings()
    if settings is None:
        return {event_name: False for event_name in HOOK_EVENTS}
    return hook_install_status_from_settings(settings)
