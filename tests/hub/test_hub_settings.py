"""hub_settings 의 순수 병합/제거 로직 단위 테스트.
검수 m1(손상 스키마 내구성)·m2(순수 함수 분리)·n1(파일 모드 보존)·n2(원래 빈 키 보존) 대상.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_settings  # noqa: E402  (sys.path 조정 후 임포트)

CAM_ENTRY = {
    "hooks": [
        {
            "type": "command",
            "command": (
                "curl -s -m 2 -o /dev/null --data-binary @- -H 'content-type: application/json' "
                "-X POST 'http://127.0.0.1:8790/event' 2>/dev/null || true"
            ),
        }
    ]
}
LITMUS_ENTRY = {
    "hooks": [{"type": "command", "command": '"/Applications/Litmus.app/Contents/MacOS/litmus-hook" claude-stop'}],
    "matcher": "",
}


def _settings_with_all_events(overrides: dict | None = None) -> dict:
    hooks = {name: [] for name in hub_settings.HOOK_EVENTS}
    if overrides:
        hooks.update(overrides)
    return {"hooks": hooks}


class MergeHubHooksTest(unittest.TestCase):
    def test_appends_matcherless_entry_for_every_event(self) -> None:
        merged = hub_settings.merge_hub_hooks(_settings_with_all_events())
        for event_name in hub_settings.HOOK_EVENTS:
            self.assertTrue(hub_settings._entry_has_hub_marker(merged["hooks"][event_name][-1]))

    def test_preserves_existing_cam_and_litmus_entries(self) -> None:
        settings = _settings_with_all_events({"Stop": [CAM_ENTRY, LITMUS_ENTRY]})
        merged = hub_settings.merge_hub_hooks(settings)
        self.assertIn(CAM_ENTRY, merged["hooks"]["Stop"])
        self.assertIn(LITMUS_ENTRY, merged["hooks"]["Stop"])
        self.assertEqual(len(merged["hooks"]["Stop"]), 3)

    def test_idempotent_when_already_installed(self) -> None:
        already_installed = {name: [hub_settings._hub_hook_entry()] for name in hub_settings.HOOK_EVENTS}
        merged = hub_settings.merge_hub_hooks({"hooks": already_installed})
        for event_name in hub_settings.HOOK_EVENTS:
            self.assertEqual(len(merged["hooks"][event_name]), 1)

    def test_input_settings_is_not_mutated(self) -> None:
        settings = _settings_with_all_events()
        original = copy.deepcopy(settings)
        hub_settings.merge_hub_hooks(settings)
        self.assertEqual(settings, original)

    def test_hooks_not_a_dict_raises_schema_error(self) -> None:
        with self.assertRaises(hub_settings.HubHooksSchemaError):
            hub_settings.merge_hub_hooks({"hooks": "not-a-dict"})

    def test_event_entries_not_a_list_raises_schema_error(self) -> None:
        with self.assertRaises(hub_settings.HubHooksSchemaError):
            hub_settings.merge_hub_hooks({"hooks": {"Stop": "not-a-list"}})


class StripHubHooksTest(unittest.TestCase):
    def test_removes_only_marker_entries_preserves_others(self) -> None:
        settings = _settings_with_all_events({"Stop": [CAM_ENTRY, LITMUS_ENTRY, hub_settings._hub_hook_entry()]})
        stripped = hub_settings.strip_hub_hooks(settings)
        self.assertEqual(stripped["hooks"]["Stop"], [CAM_ENTRY, LITMUS_ENTRY])

    def test_removes_event_key_when_empty_after_strip(self) -> None:
        settings = {"hooks": {"SessionStart": [hub_settings._hub_hook_entry()]}}
        stripped = hub_settings.strip_hub_hooks(settings)
        self.assertNotIn("SessionStart", stripped.get("hooks", {}))

    def test_removes_hooks_key_when_all_events_empty_after_strip(self) -> None:
        installed = {name: [hub_settings._hub_hook_entry()] for name in hub_settings.HOOK_EVENTS}
        stripped = hub_settings.strip_hub_hooks({"hooks": installed})
        self.assertNotIn("hooks", stripped)

    def test_no_hooks_key_is_a_no_op(self) -> None:
        settings = {"model": "opus"}
        stripped = hub_settings.strip_hub_hooks(settings)
        self.assertEqual(stripped, settings)

    def test_input_settings_is_not_mutated(self) -> None:
        settings = {"hooks": {"Stop": [hub_settings._hub_hook_entry()]}}
        original = copy.deepcopy(settings)
        hub_settings.strip_hub_hooks(settings)
        self.assertEqual(settings, original)

    def test_hooks_not_a_dict_raises_schema_error(self) -> None:
        with self.assertRaises(hub_settings.HubHooksSchemaError):
            hub_settings.strip_hub_hooks({"hooks": "not-a-dict"})

    def test_preexisting_empty_array_key_survives_strip_untouched(self) -> None:
        """검수 n2 — 우리가 만들지 않은(원래 비어 있던) 키는 제거하지 않는다.

        SubagentStart 는 애초에 설치된 적이 없어(빈 배열) 그대로 남아야 하고, Stop 은 우리가
        설치했던 엔트리라 제거로 비면 키 자체가 사라져야 한다 — 두 결과가 달라야 이 회귀를 잡는다.
        """
        settings = {"hooks": {"SubagentStart": [], "Stop": [hub_settings._hub_hook_entry()]}}
        stripped = hub_settings.strip_hub_hooks(settings)
        self.assertEqual(stripped["hooks"]["SubagentStart"], [])
        self.assertNotIn("Stop", stripped["hooks"])


class HookInstallStatusFromSettingsTest(unittest.TestCase):
    def test_detects_installed_and_missing_events(self) -> None:
        settings = {"hooks": {"Stop": [hub_settings._hub_hook_entry()]}}
        status = hub_settings.hook_install_status_from_settings(settings)
        self.assertTrue(status["Stop"])
        self.assertFalse(status["SessionStart"])

    def test_malformed_schema_returns_all_false_without_raising(self) -> None:
        """검수 m1 — 손상 스키마에서도 트레이스백 대신 False 계약을 지킨다."""
        status = hub_settings.hook_install_status_from_settings({"hooks": "broken"})
        self.assertTrue(all(value is False for value in status.values()))


class EntryHasHubMarkerRobustnessTest(unittest.TestCase):
    """검수 m1 — 손상된 엔트리 구조에서도 트레이스백 없이 False 를 돌려준다."""

    def test_non_dict_entry(self) -> None:
        self.assertFalse(hub_settings._entry_has_hub_marker("not-a-dict"))

    def test_hooks_field_not_a_list(self) -> None:
        self.assertFalse(hub_settings._entry_has_hub_marker({"hooks": "not-a-list"}))

    def test_hook_item_not_a_dict(self) -> None:
        self.assertFalse(hub_settings._entry_has_hub_marker({"hooks": ["not-a-dict"]}))


class StatuslineOwnerTest(unittest.TestCase):
    """케이스 R15 — 소유자 판정표(결정 S4 의 전부)."""

    def test_r15_key_missing_is_none(self) -> None:
        self.assertEqual(hub_settings.statusline_owner({}), "none")

    def test_r15_null_value_is_none(self) -> None:
        self.assertEqual(hub_settings.statusline_owner({"statusLine": None}), "none")

    def test_r15_our_marker_is_hub(self) -> None:
        settings = {"statusLine": {"type": "command", "command": hub_settings.STATUSLINE_COMMAND}}
        self.assertEqual(hub_settings.statusline_owner(settings), "hub")

    def test_r15_foreign_command_dict_is_foreign(self) -> None:
        settings = {"statusLine": {"type": "command", "command": "python3 my_own_statusline.py"}}
        self.assertEqual(hub_settings.statusline_owner(settings), "foreign")

    def test_r15_string_value_is_foreign(self) -> None:
        self.assertEqual(hub_settings.statusline_owner({"statusLine": "not-a-dict"}), "foreign")


class MergeHubStatuslineTest(unittest.TestCase):
    """케이스 R16~R17."""

    def test_r16_installs_from_none_and_is_idempotent(self) -> None:
        merged_once = hub_settings.merge_hub_statusline({})
        self.assertEqual(hub_settings.statusline_owner(merged_once), "hub")

        merged_twice = hub_settings.merge_hub_statusline(merged_once)
        self.assertEqual(merged_once, merged_twice)

    def test_r16_input_settings_is_not_mutated(self) -> None:
        settings = {"hooks": {}}
        original = copy.deepcopy(settings)
        hub_settings.merge_hub_statusline(settings)
        self.assertEqual(settings, original)

    def test_r17_foreign_statusline_raises_and_original_value_survives(self) -> None:
        foreign_command = {"type": "command", "command": "python3 my_own_statusline.py"}
        settings = {"statusLine": foreign_command}
        with self.assertRaises(hub_settings.HubStatusLineConflictError):
            hub_settings.merge_hub_statusline(settings)
        self.assertEqual(settings["statusLine"], foreign_command)


class StripHubStatuslineTest(unittest.TestCase):
    """케이스 R18 — hooks 키는 어느 경우에도 손대지 않는다."""

    def test_r18_our_statusline_is_removed(self) -> None:
        settings = {
            "hooks": {"Stop": [hub_settings._hub_hook_entry()]},
            "statusLine": {"type": "command", "command": hub_settings.STATUSLINE_COMMAND},
        }
        stripped = hub_settings.strip_hub_statusline(settings)
        self.assertNotIn("statusLine", stripped)
        self.assertEqual(stripped["hooks"], settings["hooks"])

    def test_r18_foreign_statusline_is_preserved(self) -> None:
        foreign_command = {"type": "command", "command": "python3 my_own_statusline.py"}
        settings = {"hooks": {}, "statusLine": foreign_command}
        stripped = hub_settings.strip_hub_statusline(settings)
        self.assertEqual(stripped["statusLine"], foreign_command)

    def test_r18_no_key_is_a_no_op(self) -> None:
        settings = {"hooks": {}}
        stripped = hub_settings.strip_hub_statusline(settings)
        self.assertEqual(stripped, settings)


class InstallStatuslineMissingEntrypointTest(unittest.TestCase):
    """케이스 R18b — hub_statusline.py 가 없으면 settings.json 을 건드리지 않고 거부한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_settings_path = hub_settings.SETTINGS_PATH
        self.original_entrypoint_path = hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH
        hub_settings.SETTINGS_PATH = self.temp_dir / "settings.json"
        hub_settings.SETTINGS_PATH.write_text(json.dumps({"model": "opus"}))
        hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH = self.temp_dir / "missing_hub_statusline.py"

    def tearDown(self) -> None:
        hub_settings.SETTINGS_PATH = self.original_settings_path
        hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH = self.original_entrypoint_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_r18b_missing_entrypoint_is_rejected_without_touching_settings(self) -> None:
        before = hub_settings.SETTINGS_PATH.read_text()
        result = hub_settings.install_statusline()
        self.assertFalse(result["ok"])
        self.assertIn(str(hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH), result["reason"])
        self.assertEqual(hub_settings.SETTINGS_PATH.read_text(), before)


class InstallStatuslineForeignConflictIoTest(unittest.TestCase):
    """검수 MEDIUM 3 — install_statusline()/uninstall_statusline() 는 merge_hub_statusline·
    strip_hub_statusline(R17·R18) 를 거치지 않고 자체 statusline_owner 검사로 단락하므로,
    이 기능의 최대 안전 주장("남의 statusLine 을 절대 건드리지 않는다")을 순수 함수 테스트만으로는
    보증하지 못한다. I/O 진입점 자체가 foreign 값을 만나면 파일 바이트가 한 글자도 안 바뀌는지
    직접 확인한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_settings_path = hub_settings.SETTINGS_PATH
        self.original_entrypoint_path = hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH
        hub_settings.SETTINGS_PATH = self.temp_dir / "settings.json"
        hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH = self.temp_dir / "hub_statusline.py"
        hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH.write_text("# stub")

    def tearDown(self) -> None:
        hub_settings.SETTINGS_PATH = self.original_settings_path
        hub_settings.HUB_STATUSLINE_ENTRYPOINT_PATH = self.original_entrypoint_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_install_rejects_foreign_statusline_without_touching_settings(self) -> None:
        foreign_settings = {"model": "opus", "statusLine": {"type": "command", "command": "my-own-script.sh"}}
        hub_settings.SETTINGS_PATH.write_text(json.dumps(foreign_settings))
        before = hub_settings.SETTINGS_PATH.read_text()

        result = hub_settings.install_statusline()

        self.assertFalse(result["ok"])
        self.assertEqual(result["current_command"], foreign_settings["statusLine"])
        self.assertEqual(hub_settings.SETTINGS_PATH.read_text(), before)

    def test_uninstall_preserves_foreign_statusline_without_touching_settings(self) -> None:
        foreign_settings = {"model": "opus", "statusLine": {"type": "command", "command": "my-own-script.sh"}}
        hub_settings.SETTINGS_PATH.write_text(json.dumps(foreign_settings))
        before = hub_settings.SETTINGS_PATH.read_text()

        result = hub_settings.uninstall_statusline()

        self.assertTrue(result["ok"])
        self.assertFalse(result["removed"])
        self.assertEqual(hub_settings.SETTINGS_PATH.read_text(), before)


class WriteSettingsAtomicallyModePreservationTest(unittest.TestCase):
    """검수 n1 — mkstemp 는 새 파일을 0600 으로 만든다. 기존 파일 모드(보통 0644)를
    조용히 바꾸면 안 된다 — 교체 전에 기존 모드를 그대로 옮긴다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_settings_path = hub_settings.SETTINGS_PATH
        hub_settings.SETTINGS_PATH = self.temp_dir / "settings.json"
        hub_settings.SETTINGS_PATH.write_text(json.dumps({"hooks": {}}))
        hub_settings.SETTINGS_PATH.chmod(0o644)

    def tearDown(self) -> None:
        hub_settings.SETTINGS_PATH = self.original_settings_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_existing_file_mode_is_preserved_after_write(self) -> None:
        before_mode = hub_settings.SETTINGS_PATH.stat().st_mode & 0o777
        hub_settings._write_settings_atomically({"hooks": {"Stop": [hub_settings._hub_hook_entry()]}})
        after_mode = hub_settings.SETTINGS_PATH.stat().st_mode & 0o777
        self.assertEqual(after_mode, before_mode)


if __name__ == "__main__":
    unittest.main()
