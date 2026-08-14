"""hub_collect 의 I/O 로직 단위 테스트. 실제 ~/.claude 는 건드리지 않고 모듈 상수를
임시 디렉토리로 바꿔치기(monkeypatch)한 뒤 원상복구한다. 검수 M2·M7·m3·m4·m5 회귀 대상.
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
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_model  # noqa: E402
import hub_usage  # noqa: E402


def _minimal_snapshot(collected_at_ms: int) -> hub_model.HubSnapshot:
    return hub_model.HubSnapshot(
        collected_at_ms=collected_at_ms, projects=(), unresolved_dir_names=(), warnings=()
    )


class ServerRecordRoundTripTest(unittest.TestCase):
    """검수 m3 — read_server_record 가 실제로 hub_model.parse_server_record(공유 파서)를
    거치는지 실사용 경로(파일 I/O)로 확인한다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_record_path = hub_collect.SERVER_RECORD_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.SERVER_RECORD_PATH = self.temp_dir / "server.json"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.SERVER_RECORD_PATH = self.original_record_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_then_read_round_trip(self) -> None:
        record = hub_model.ServerRecord(pid=123, port=8794, started_at_ms=1786000000000)
        hub_collect.write_server_record(record)
        self.assertEqual(hub_collect.read_server_record(), record)

    def test_missing_file_returns_none(self) -> None:
        self.assertIsNone(hub_collect.read_server_record())

    def test_broken_json_returns_none_without_raising(self) -> None:
        hub_collect.SERVER_RECORD_PATH.write_text("{not valid json")
        self.assertIsNone(hub_collect.read_server_record())


class ClearServerStateCompareAndDeleteTest(unittest.TestCase):
    """검수 m1 — expected_pid 가 주어지면 현재 server.json 의 pid 가 그것과 같을 때만 지운다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_record_path = hub_collect.SERVER_RECORD_PATH
        self.original_heartbeat_path = hub_collect.SERVER_HEARTBEAT_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.SERVER_RECORD_PATH = self.temp_dir / "server.json"
        hub_collect.SERVER_HEARTBEAT_PATH = self.temp_dir / "server_heartbeat"

    def tearDown(self) -> None:
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.SERVER_RECORD_PATH = self.original_record_path
        hub_collect.SERVER_HEARTBEAT_PATH = self.original_heartbeat_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_does_not_delete_when_pid_was_replaced_by_a_newer_server(self) -> None:
        """다른 셸이 이미 새 서버를 띄워 server.json 을 갈아 끼운 뒤에는 지우면 안 된다."""
        old_record = hub_model.ServerRecord(pid=111, port=8794, started_at_ms=1)
        hub_collect.write_server_record(old_record)
        hub_collect.touch_server_heartbeat()

        # 다른 프로세스가 새 서버를 등록했다고 가정한다.
        new_record = hub_model.ServerRecord(pid=222, port=8794, started_at_ms=2)
        hub_collect.write_server_record(new_record)

        hub_collect.clear_server_state(expected_pid=old_record.pid)

        self.assertEqual(hub_collect.read_server_record(), new_record)
        self.assertTrue(hub_collect.SERVER_HEARTBEAT_PATH.exists())

    def test_deletes_when_pid_still_matches(self) -> None:
        record = hub_model.ServerRecord(pid=111, port=8794, started_at_ms=1)
        hub_collect.write_server_record(record)
        hub_collect.touch_server_heartbeat()

        hub_collect.clear_server_state(expected_pid=record.pid)

        self.assertIsNone(hub_collect.read_server_record())
        self.assertFalse(hub_collect.SERVER_HEARTBEAT_PATH.exists())

    def test_deletes_when_record_already_absent(self) -> None:
        hub_collect.clear_server_state(expected_pid=111)  # 예외 없이 조용히 통과해야 한다
        self.assertIsNone(hub_collect.read_server_record())

    def test_no_expected_pid_always_deletes(self) -> None:
        record = hub_model.ServerRecord(pid=111, port=8794, started_at_ms=1)
        hub_collect.write_server_record(record)
        hub_collect.clear_server_state()
        self.assertIsNone(hub_collect.read_server_record())


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
        activity, warnings = hub_collect._tier3_activity_by_encoded_name(ignore_globs)

        self.assertEqual(list(activity), ["-Users-b-private-project-coding-env"])
        self.assertEqual(warnings, ())

    def test_r3_m1_iterdir_permission_error_gives_up_tier3_only(self) -> None:
        """검수 R3-m1 — PROJECTS_DIR.iterdir() 실패는 티어 3 전체를 포기하되 예외를 던지지 않는다."""
        self._make_encoded_project_dir("-Users-b-private-project-coding-env")
        self.temp_dir.chmod(0o000)
        try:
            activity, warnings = hub_collect._tier3_activity_by_encoded_name(())
        finally:
            self.temp_dir.chmod(0o755)

        self.assertEqual(activity, {})
        self.assertEqual(len(warnings), 1)
        self.assertIn("목록 조회 실패", warnings[0])

    def test_r3_m1_entry_stat_failure_skips_only_that_project(self) -> None:
        """검수 R3-m1 — glob 열거와 stat 사이의 TOCTOU(파일이 그 사이 사라짐)는 그 프로젝트만
        건너뛴다. 디렉토리 권한만으로는 이 race 를 재현할 수 없다(glob 이 권한 오류를 삼키고
        빈 목록을 반환함을 실측 확인) — Path.stat 을 패치해 결정적으로 재현한다."""
        self._make_encoded_project_dir("-Users-b-private-project-coding-env")
        self._make_encoded_project_dir("-Users-b-flaky")
        flaky_jsonl = self.temp_dir / "-Users-b-flaky" / "session.jsonl"
        original_stat = Path.stat

        def _flaky_stat(path_self, *args, **kwargs):
            if path_self == flaky_jsonl:
                raise OSError("simulated TOCTOU: file vanished between glob and stat")
            return original_stat(path_self, *args, **kwargs)

        with mock.patch.object(Path, "stat", _flaky_stat):
            activity, warnings = hub_collect._tier3_activity_by_encoded_name(())

        self.assertIn("-Users-b-private-project-coding-env", activity)
        self.assertNotIn("-Users-b-flaky", activity)
        self.assertEqual(len(warnings), 1)
        self.assertIn("mtime 조회 실패", warnings[0])


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

    def test_record_collect_failure_never_raises_when_write_itself_fails(self) -> None:
        """검수 M2-2 — 1차 실패의 가장 흔한 원인(HUB_HOME 쓰기 불가)이 기록 자신에게도
        똑같이 영향을 준다. 이 함수가 그대로 예외를 던지면 상관 실패가 호출자(상주 서버의
        수집 루프)의 예외 처리 범위를 뚫고 나가 스레드 전체를 죽인다 — 그래서 기록 실패는
        stderr 로만 남기고 절대 예외를 올리지 않는다."""
        with mock.patch.object(hub_collect, "_atomic_write_text", side_effect=OSError("디스크 가득 참")):
            try:
                hub_collect.record_collect_failure("원인 실패 사유")
            except OSError:
                self.fail("record_collect_failure 가 예외를 던졌다 — 절대 던지지 않아야 한다")


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

    def test_deprecated_field_warns_with_replacement_guidance(self) -> None:
        """검수 m4 — 폐기된 serve_port_candidates 는 무시하되 대체 필드를 안내한다."""
        hub_collect.CONFIG_PATH.write_text(json.dumps({"serve_port_candidates": [8794, 8795]}))
        config, warnings = hub_collect.load_config()
        self.assertEqual(config, hub_model.HubConfig())
        self.assertTrue(any("serve_port_candidates" in warning and "server_port" in warning for warning in warnings))

    def test_unknown_field_warns_generically(self) -> None:
        """검수 m4 — 오타 등 진짜 알 수 없는 키도 조용히 무시되지 않는다."""
        hub_collect.CONFIG_PATH.write_text(json.dumps({"scan_dpeth": 5}))
        _config, warnings = hub_collect.load_config()
        self.assertTrue(any("scan_dpeth" in warning for warning in warnings))

    def test_broken_json_returns_defaults_with_warning(self) -> None:
        hub_collect.CONFIG_PATH.write_text("{not valid json")
        config, warnings = hub_collect.load_config()
        self.assertEqual(config, hub_model.HubConfig())
        self.assertEqual(len(warnings), 1)

    def test_case25_show_usage_panel_wrong_type_falls_back_to_default_with_warning(self) -> None:
        """케이스 25 — config.json 의 show_usage_panel:"yes" 는 기본값 True + 경고 1건."""
        hub_collect.CONFIG_PATH.write_text(json.dumps({"show_usage_panel": "yes"}))
        config, warnings = hub_collect.load_config()
        self.assertTrue(config.show_usage_panel)
        self.assertTrue(any("show_usage_panel" in warning for warning in warnings))


class CaptureForSnapshotTest(unittest.TestCase):
    """케이스 N30~N36 — _capture_for_snapshot 이 캡처 파일을 사이클당 1회만 읽어 사용률·
    리셋 시각을 고르는 반환 계약(docs/prps/hub-card-cleanup-and-usage-source.md §5.5 표)."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"
        self.now_ms = 1786433123899

    def tearDown(self) -> None:
        for path in self.temp_dir.glob("*"):
            path.chmod(0o644)
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_capture(self, **overrides) -> None:
        payload = {
            "captured_at_ms": self.now_ms,
            "session_resets_at_ms": None,
            "weekly_resets_at_ms": None,
            "session_used_percent": None,
            "weekly_used_percent": None,
        }
        payload.update(overrides)
        hub_collect.RATE_LIMITS_PATH.write_text(json.dumps(payload))

    def test_n30_missing_capture_file_returns_none_pair_without_warnings(self) -> None:
        usage, resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNone(usage)
        self.assertIsNone(resets)
        self.assertEqual(warnings, ())

    def test_n31_switch_off_never_reads_the_file(self) -> None:
        """검수 m6 과 같은 이유 — 래퍼가 아니라 I/O 경계(Path.read_text)에서 직접 확인한다."""
        self._write_capture(session_used_percent=23, weekly_used_percent=41)
        config = hub_model.HubConfig(show_usage_panel=False)
        with mock.patch.object(hub_collect.Path, "read_text") as mocked_read_text:
            usage, resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, config)
        self.assertIsNone(usage)
        self.assertIsNone(resets)
        self.assertEqual(warnings, ())
        mocked_read_text.assert_not_called()

    def test_n32_normal_new_style_capture_fills_both_usage_and_resets(self) -> None:
        self._write_capture(
            session_resets_at_ms=self.now_ms + 10_000, weekly_resets_at_ms=self.now_ms + 20_000,
            session_used_percent=10, weekly_used_percent=19,
        )
        usage, resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertEqual(
            usage, hub_usage.UsageSample(sampled_at_ms=self.now_ms, session_percent=10, weekly_percent=19)
        )
        self.assertEqual(
            resets,
            hub_usage.RateLimitResets(
                captured_at_ms=self.now_ms,
                session_resets_at_ms=self.now_ms + 10_000,
                weekly_resets_at_ms=self.now_ms + 20_000,
            ),
        )
        self.assertEqual(warnings, ())

    def test_n33_legacy_capture_without_percent_fills_resets_only(self) -> None:
        self._write_capture(session_resets_at_ms=self.now_ms + 10_000)
        usage, resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNone(usage)
        self.assertIsNotNone(resets)
        self.assertEqual(warnings, ())

    def test_n34_six_hours_old_capture_marks_usage_stale_without_warnings(self) -> None:
        """R-B 개정 — 만료돼도 usage 는 숨겨지지 않고 살아남아 is_stale 로 표시된다."""
        six_hours_ms = 6 * 60 * 60 * 1000
        self._write_capture(
            captured_at_ms=self.now_ms - six_hours_ms, session_used_percent=10, weekly_used_percent=19
        )
        usage, _resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNotNone(usage)
        self.assertTrue(usage.is_stale)
        self.assertEqual(warnings, ())

    def test_n35_session_window_rolled_over_marks_usage_stale_even_when_fresh(self) -> None:
        """결정 P5·EX2 개정 — 나이가 3시간뿐이어도 세션 리셋 시각이 지났으면 확실히 틀린
        값이라 is_stale 로 표시된다(숨기지는 않는다)."""
        self._write_capture(
            captured_at_ms=self.now_ms - 3 * 60 * 60 * 1000,
            session_resets_at_ms=self.now_ms - 60 * 60 * 1000,
            session_used_percent=10, weekly_used_percent=19,
        )
        usage, _resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNotNone(usage)
        self.assertTrue(usage.is_stale)
        self.assertEqual(warnings, ())

    def test_u8_stale_usage_keeps_future_weekly_reset_row(self) -> None:
        """결정 EX8 — 만료 상태에서도 아직 지나지 않은 초기화 예정 시각은 그대로 실린다."""
        six_hours_ms = 6 * 60 * 60 * 1000
        weekly_reset_future_ms = self.now_ms + 3 * 24 * 60 * 60 * 1000
        self._write_capture(
            captured_at_ms=self.now_ms - six_hours_ms,
            weekly_resets_at_ms=weekly_reset_future_ms,
            session_used_percent=10, weekly_used_percent=19,
        )
        usage, resets, _warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNotNone(usage)
        self.assertTrue(usage.is_stale)
        self.assertIsNotNone(resets)
        self.assertEqual(resets.weekly_resets_at_ms, weekly_reset_future_ms)

    def test_n36_broken_capture_file_returns_none_pair_with_exactly_one_warning(self) -> None:
        """GOTCHA 5 회귀 — 캡처 파일을 사이클당 1회만 읽으므로 경고가 2건으로 중복되지 않는다."""
        hub_collect.RATE_LIMITS_PATH.write_text("{not valid json")
        usage, resets, warnings = hub_collect._capture_for_snapshot(self.now_ms, hub_model.HubConfig())
        self.assertIsNone(usage)
        self.assertIsNone(resets)
        self.assertEqual(len(warnings), 1)

    def test_n43_truncated_multibyte_capture_does_not_raise(self) -> None:
        """§17 발견 1 회귀 — 찢긴 멀티바이트 읽기가 UnicodeDecodeError 로 except OSError 를
        뚫지 않는다(read_latest_usage_sample 의 검수 M1 선례와 같은 문제, errors="replace" 로 흡수)."""
        truncated_bytes = b'{"captured_at_ms":1,"session_used_percent":' + b"\xed\xa0"
        hub_collect.RATE_LIMITS_PATH.write_bytes(truncated_bytes)
        try:
            capture, warnings = hub_collect.read_rate_limit_capture()
        except UnicodeDecodeError:
            self.fail("read_rate_limit_capture 가 UnicodeDecodeError 를 던졌다 — 절대 던지지 않아야 한다")
        self.assertIsNone(capture)
        self.assertEqual(len(warnings), 1)


class SnapshotContentKeyStaleTransitionTest(unittest.TestCase):
    """U9 — is_stale 만 다른 두 HubSnapshot 의 snapshot_content_key 가 서로 다르다(결정 EX4 의
    기계적 고정). 이 성질이 없으면 신선→만료 전이가 일어나도 hub.html 이 다시 쓰이지 않아
    화면이 스스로 "조회되지 않음"으로 바뀌지 않는 회귀를 아무도 못 잡는다."""

    def _snapshot(self, is_stale: bool) -> hub_model.HubSnapshot:
        usage = hub_usage.UsageSample(
            sampled_at_ms=1786433123899, session_percent=10, weekly_percent=19, is_stale=is_stale
        )
        return hub_model.HubSnapshot(
            collected_at_ms=1786433123899, projects=(), unresolved_dir_names=(), warnings=(), usage=usage
        )

    def test_u9_stale_transition_changes_content_key(self) -> None:
        fresh_key = hub_model.snapshot_content_key(self._snapshot(is_stale=False))
        stale_key = hub_model.snapshot_content_key(self._snapshot(is_stale=True))
        self.assertNotEqual(fresh_key, stale_key)


class RateLimitCaptureTest(unittest.TestCase):
    """케이스 R19~R20·R23b — read/write_rate_limit_capture 의 I/O 반환 계약(신형 5필드).
    스위치·만료·롤오버 시나리오는 CaptureForSnapshotTest(N30~N36)로 옮겼다."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_hub_home = hub_collect.HUB_HOME
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        hub_collect.HUB_HOME = self.temp_dir
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"
        self.now_ms = 1786433123899

    def tearDown(self) -> None:
        for path in self.temp_dir.glob("*"):
            path.chmod(0o644)
        hub_collect.HUB_HOME = self.original_hub_home
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _capture(
        self, session_resets_at_ms=None, weekly_resets_at_ms=None,
        session_used_percent=None, weekly_used_percent=None,
    ) -> hub_usage.RateLimitCapture:
        return hub_usage.RateLimitCapture(
            captured_at_ms=self.now_ms,
            session_resets_at_ms=session_resets_at_ms,
            weekly_resets_at_ms=weekly_resets_at_ms,
            session_used_percent=session_used_percent,
            weekly_used_percent=weekly_used_percent,
        )

    def test_r19_missing_capture_file_returns_none_without_warnings(self) -> None:
        capture, warnings = hub_collect.read_rate_limit_capture()
        self.assertIsNone(capture)
        self.assertEqual(warnings, ())

    def test_r20_broken_json_returns_none_with_one_warning(self) -> None:
        hub_collect.RATE_LIMITS_PATH.write_text("{not valid json")
        capture, warnings = hub_collect.read_rate_limit_capture()
        self.assertIsNone(capture)
        self.assertEqual(len(warnings), 1)

    def test_r20_unreadable_file_returns_none_with_one_warning(self) -> None:
        hub_collect.write_rate_limit_capture(self._capture(session_resets_at_ms=self.now_ms + 10_000))
        hub_collect.RATE_LIMITS_PATH.chmod(0o000)
        capture, warnings = hub_collect.read_rate_limit_capture()
        self.assertIsNone(capture)
        self.assertEqual(len(warnings), 1)

    def test_r23b_write_then_read_round_trip_is_atomic(self) -> None:
        original = self._capture(
            session_resets_at_ms=self.now_ms + 10_000, weekly_resets_at_ms=self.now_ms + 20_000,
            session_used_percent=23, weekly_used_percent=41,
        )
        hub_collect.write_rate_limit_capture(original)
        capture, warnings = hub_collect.read_rate_limit_capture()
        self.assertEqual(capture, original)
        self.assertEqual(warnings, ())
        leftover = list(self.temp_dir.glob("rate_limits.json.*.tmp"))
        self.assertEqual(leftover, [])


class CollectSnapshotRateLimitIsolationTest(unittest.TestCase):
    """케이스 R23·N37 — 캡처 파일 계약 불일치가 collect_snapshot() 전체를 죽이지 않는다
    (실패 격리 회귀 방지)."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_events_dir = hub_collect.EVENTS_DIR
        self.original_projects_dir = hub_collect.PROJECTS_DIR
        self.original_config_path = hub_collect.CONFIG_PATH
        self.original_rate_limits_path = hub_collect.RATE_LIMITS_PATH
        hub_collect.EVENTS_DIR = self.temp_dir / "events"
        hub_collect.PROJECTS_DIR = self.temp_dir / "projects"
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"
        hub_collect.RATE_LIMITS_PATH = self.temp_dir / "rate_limits.json"
        hub_collect.RATE_LIMITS_PATH.write_text("{not valid json")

    def tearDown(self) -> None:
        hub_collect.EVENTS_DIR = self.original_events_dir
        hub_collect.PROJECTS_DIR = self.original_projects_dir
        hub_collect.CONFIG_PATH = self.original_config_path
        hub_collect.RATE_LIMITS_PATH = self.original_rate_limits_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_r23_broken_capture_does_not_abort_project_collection(self) -> None:
        snapshot = hub_collect.collect_snapshot(1786433123899)
        self.assertEqual(snapshot.projects, ())
        self.assertIsNone(snapshot.usage)
        self.assertIsNone(snapshot.rate_limit_resets)
        self.assertTrue(any("캡처 파일 계약 불일치" in warning for warning in snapshot.warnings))


if __name__ == "__main__":
    unittest.main()
