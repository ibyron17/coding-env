"""hub_collect 의 I/O 로직 단위 테스트. 실제 ~/.claude 는 건드리지 않고 모듈 상수를
임시 디렉토리로 바꿔치기(monkeypatch)한 뒤 원상복구한다. 검수 M2·M7·m4·m5 회귀 대상.
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_model  # noqa: E402


def _minimal_snapshot(collected_at_ms: int) -> hub_model.HubSnapshot:
    return hub_model.HubSnapshot(
        collected_at_ms=collected_at_ms, projects=(), unresolved_dir_names=(), warnings=()
    )


class WriteHubHtmlAtomicityTest(unittest.TestCase):
    """검수 M2 — 고정 임시 파일명을 공유하면 동시 쓰기가 뒤섞인다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_hub_html_path = hub_collect.HUB_HTML_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_hub_html_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_writes_never_produce_corrupted_output(self) -> None:
        barrier = threading.Barrier(2)

        def write(collected_at_ms: int) -> None:
            barrier.wait()
            hub_collect.write_hub_html(_minimal_snapshot(collected_at_ms))

        threads = [threading.Thread(target=write, args=(value,)) for value in (111, 222)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        final_text = hub_collect.HUB_HTML_PATH.read_text(encoding="utf-8")
        payload = final_text.split('id="dzh-data">', 1)[1].split("</script>", 1)[0]
        data = json.loads(payload)  # 뒤섞였다면 여기서 JSONDecodeError 가 난다
        self.assertIn(data["collected_at_ms"], (111, 222))

    def test_no_leftover_temp_files_after_write(self) -> None:
        hub_collect.write_hub_html(_minimal_snapshot(1))
        leftover = list(self.temp_dir.glob("hub.html.*.tmp"))
        self.assertEqual(leftover, [])


class Tier3IgnoreFilterTest(unittest.TestCase):
    """검수 m4 — ignore_globs 를 인코딩한 패턴으로 티어 3 소음(worktree·scratchpad)을 원천 제거한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_projects_dir = hub_collect.PROJECTS_DIR
        hub_collect.PROJECTS_DIR = self.temp_dir

    def tearDown(self) -> None:
        hub_collect.PROJECTS_DIR = self.original_projects_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_encoded_project_dir(self, encoded_name: str) -> None:
        project_dir = self.temp_dir / encoded_name
        project_dir.mkdir()
        (project_dir / "session.jsonl").write_text("{}")

    def test_worktree_and_tmp_encoded_names_are_excluded(self) -> None:
        self._make_encoded_project_dir("-Users-b-repo--claude-worktrees-f1")
        self._make_encoded_project_dir("-private-tmp-claude-501-x")
        self._make_encoded_project_dir("-Users-b-private-project-coding-env")

        ignore_globs = hub_model.HubConfig().ignore_globs
        activity = hub_collect._tier3_activity_by_encoded_name(ignore_globs)

        self.assertEqual(list(activity), ["-Users-b-private-project-coding-env"])


class ReadRecentEventsFailureIsolationTest(unittest.TestCase):
    """검수 M7 — collect 파이프라인은 이벤트 파일 하나의 실패로 전체가 죽지 않는다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_events_dir = hub_collect.EVENTS_DIR
        hub_collect.EVENTS_DIR = self.temp_dir
        self.now_ms = int(time.time() * 1000)

    def tearDown(self) -> None:
        hub_collect.EVENTS_DIR = self.original_events_dir
        for path in self.temp_dir.glob("*"):
            path.chmod(0o644)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _today_file(self) -> Path:
        today = hub_collect._date_string(self.now_ms)
        return self.temp_dir / f"{today}.jsonl"

    def _yesterday_file(self) -> Path:
        yesterday = hub_collect._date_string(self.now_ms - hub_collect.MILLISECONDS_PER_DAY)
        return self.temp_dir / f"{yesterday}.jsonl"

    def test_permission_denied_file_is_skipped_with_warning(self) -> None:
        """실측 (1) — 이벤트 파일 권한 없음 → PermissionError 로 collect 전체가 죽지 않는다."""
        good_file = self._yesterday_file()
        good_file.write_text('{"t":1,"e":"Stop","s":"s1","c":"/repo"}\n')
        bad_file = self._today_file()
        bad_file.write_text('{"t":2,"e":"Stop","s":"s2","c":"/repo"}\n')
        bad_file.chmod(0o000)

        events, warnings = hub_collect.read_recent_events(self.now_ms)

        self.assertEqual([event.session_id for event in events], ["s1"])
        self.assertTrue(any("읽기 실패" in warning for warning in warnings))

    def test_invalid_utf8_tail_byte_does_not_abort_the_whole_file(self) -> None:
        """실측 (2) — 이벤트 파일 꼬리의 비UTF-8 1바이트(동시 append 찢김) → 그 줄만 탈락."""
        today_file = self._today_file()
        with open(today_file, "wb") as raw_file:
            raw_file.write(b'{"t":1,"e":"Stop","s":"s1","c":"/repo"}\n')
            raw_file.write(b'{"t":2,"e":"Stop","s":"s2","c":"/repo"\xff}\n')

        events, warnings = hub_collect.read_recent_events(self.now_ms)

        self.assertEqual([event.session_id for event in events], ["s1"])
        self.assertEqual(warnings, ())  # 디코딩 자체는 죽지 않는다 — errors="replace" 가 흡수한다


class ScanDirectoryFailureIsolationTest(unittest.TestCase):
    """검수 M7 — (3) config.roots 스캔 중 EACCES 로 스캔 전체가 죽지 않는다.

    `Path.exists()` 는 ENOENT 만 흡수하고 EACCES 는 그대로 올린다(macOS 실측) — 마커 탐침을
    try/except 로 감싸지 않으면 권한 없는 디렉토리 하나가 collect 전체를 중단시킨다.
    """

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.restricted_dir = self.temp_dir / "restricted"
        self.restricted_dir.mkdir()
        self.readable_project_dir = self.temp_dir / "readable_project"
        self.readable_project_dir.mkdir()
        (self.readable_project_dir / ".git").mkdir()
        self.restricted_dir.chmod(0o000)

    def tearDown(self) -> None:
        self.restricted_dir.chmod(0o755)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_eacces_on_marker_probe_is_skipped_not_raised(self) -> None:
        matches = hub_collect._scan_directory(self.temp_dir, remaining_depth=2)
        self.assertIn(str(self.readable_project_dir), matches)
        self.assertNotIn(str(self.restricted_dir), matches)


class WriteHubHtmlMissingTemplateTest(unittest.TestCase):
    """검수 M7 — (4) hub_template.html 부재 시 원시 FileNotFoundError 대신 HubCollectError."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_template_path = hub_collect.TEMPLATE_PATH
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_hub_html_path = hub_collect.HUB_HTML_PATH
        hub_collect.TEMPLATE_PATH = self.temp_dir / "missing_template.html"
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"

    def tearDown(self) -> None:
        hub_collect.TEMPLATE_PATH = self.original_template_path
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.HUB_HTML_PATH = self.original_hub_html_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_template_raises_hub_collect_error(self) -> None:
        with self.assertRaises(hub_collect.HubCollectError):
            hub_collect.write_hub_html(_minimal_snapshot(1))


class CollectFailureObservabilityTest(unittest.TestCase):
    """검수 M7 — 배경 spawn 은 stdout/stderr 가 무성음이라 실패를 파일로 남겨 관측 가능하게 한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_error_path = hub_collect.LAST_COLLECT_ERROR_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.LAST_COLLECT_ERROR_PATH = self.temp_dir / "last_collect_error.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.LAST_COLLECT_ERROR_PATH = self.original_error_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_then_clear_round_trip(self) -> None:
        hub_collect.record_collect_failure("템플릿 없음")
        recorded = hub_collect.read_last_collect_failure()
        self.assertEqual(recorded["reason"], "템플릿 없음")

        hub_collect.clear_collect_failure()
        self.assertIsNone(hub_collect.read_last_collect_failure())

    def test_no_failure_recorded_returns_none(self) -> None:
        self.assertIsNone(hub_collect.read_last_collect_failure())


class LoadConfigValidationTest(unittest.TestCase):
    """검수 m5 — 필드 타입이 안 맞으면 그 필드만 기본값으로 되돌리고 사유를 warnings 로 남긴다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_config_path = hub_collect.CONFIG_PATH
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"

    def tearDown(self) -> None:
        hub_collect.CONFIG_PATH = self.original_config_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_wrong_type_field_falls_back_to_default_with_warning(self) -> None:
        hub_collect.CONFIG_PATH.write_text(
            json.dumps({"scan_depth": "three", "stale_after_minutes": 45})
        )
        config, warnings = hub_collect.load_config()
        self.assertEqual(config.scan_depth, hub_model.HubConfig().scan_depth)
        self.assertEqual(config.stale_after_minutes, 45)
        self.assertTrue(any("scan_depth" in warning for warning in warnings))

    def test_no_config_file_returns_defaults_without_warnings(self) -> None:
        config, warnings = hub_collect.load_config()
        self.assertEqual(config, hub_model.HubConfig())
        self.assertEqual(warnings, ())

    def test_broken_json_returns_defaults_with_warning(self) -> None:
        hub_collect.CONFIG_PATH.write_text("{not valid json")
        config, warnings = hub_collect.load_config()
        self.assertEqual(config, hub_model.HubConfig())
        self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()
