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
