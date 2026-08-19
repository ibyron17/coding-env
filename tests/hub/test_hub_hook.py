"""hub_hook.py 단위 테스트. 실제 ~/.claude 는 건드리지 않고 hub_collect 의 모듈 상수를
임시 디렉토리로 바꿔치기한 뒤 원상복구한다. 검수 M4(서브프로세스 분리)·M5(리텐션 도달성) 대상.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_collect  # noqa: E402
import hub_hook  # noqa: E402

EIGHT_DAYS_SECONDS = 8 * 24 * 60 * 60
ONE_HOUR_SECONDS = 60 * 60
MACOS_PATH_MAX_BYTES = 1024      # 이벤트 줄에 함께 실리는 cwd 의 현실적 최댓값
SESSION_ID_LENGTH = 36           # UUID 문자열 길이


class HubHookScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_events_dir = hub_collect.EVENTS_DIR
        self.original_html_path = hub_collect.HUB_HTML_PATH
        self.original_config_path = hub_collect.CONFIG_PATH
        self.original_spawn_stamp_path = hub_collect.SPAWN_STAMP_PATH
        self.original_heartbeat_path = hub_collect.SERVER_HEARTBEAT_PATH

        hub_collect.EVENTS_DIR = self.temp_dir / "events"
        hub_collect.EVENTS_DIR.mkdir()
        hub_collect.HUB_HTML_PATH = self.temp_dir / "hub.html"
        hub_collect.CONFIG_PATH = self.temp_dir / "config.json"
        hub_collect.SPAWN_STAMP_PATH = self.temp_dir / ".collect_spawn_stamp"
        hub_collect.SERVER_HEARTBEAT_PATH = self.temp_dir / "server_heartbeat"

    def tearDown(self) -> None:
        hub_collect.EVENTS_DIR = self.original_events_dir
        hub_collect.HUB_HTML_PATH = self.original_html_path
        hub_collect.CONFIG_PATH = self.original_config_path
        hub_collect.SPAWN_STAMP_PATH = self.original_spawn_stamp_path
        hub_collect.SERVER_HEARTBEAT_PATH = self.original_heartbeat_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_hook_with_stdin(self, payload: dict) -> None:
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            hub_hook.main()


class RetentionReachabilityTest(HubHookScenarioTest):
    """검수 M5 — hub.html 이 없어도(허브 off 상태) 리텐션이 여전히 동작해야 한다."""

    def test_old_event_file_pruned_even_without_hub_html(self) -> None:
        old_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - EIGHT_DAYS_SECONDS))
        old_file = hub_collect.EVENTS_DIR / f"{old_date}.jsonl"
        old_file.write_text('{"t":1,"e":"Stop","s":"s","c":"/repo"}\n')

        self.assertFalse(hub_collect.HUB_HTML_PATH.exists())  # 허브 off 상태 전제

        # 검수 M2-5 이후로는 이 조합(hub.html 없음 + 서버 죽음)이 실제로 spawn 을 한다 — 이
        # 테스트의 관심사는 리텐션 정리이므로 subprocess.Popen 을 모킹해 실제 프로세스를
        # 띄우지 않는다(실제 ~/.claude 를 건드리지 않는다는 이 파일의 전제를 지킨다).
        with mock.patch("subprocess.Popen"):
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s2", "cwd": "/repo"})

        self.assertFalse(old_file.exists())


class SpawnsBackgroundCollectTest(HubHookScenarioTest):
    """검수 M4 — 훅은 재수집을 서브프로세스로 떼어내고 자신은 무거운 작업을 하지 않는다."""

    def test_stale_hub_html_triggers_subprocess_spawn_not_inline_collect(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        with mock.patch("subprocess.Popen") as mock_popen, \
             mock.patch.object(hub_collect, "collect_snapshot") as mock_collect_snapshot, \
             mock.patch.object(hub_collect, "write_hub_html") as mock_write_hub_html:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()
        spawned_command = mock_popen.call_args[0][0]
        self.assertIn("collect", spawned_command)
        mock_collect_snapshot.assert_not_called()
        mock_write_hub_html.assert_not_called()

    def test_fresh_hub_html_does_not_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("fresh-marker")  # mtime = 지금

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_not_called()

    def test_missing_hub_html_spawns_when_server_is_not_alive(self) -> None:
        """검수 M2-5 — 서버가 죽어 있고(하트비트 없음) hub.html 도 없으면 훅 폴백이 뚫려야
        한다. 예전에는 이 조합이 항상 False 라, 상주 서버가 HUB_HOME 쓰기 실패 등으로
        hub.html 을 한 번도 못 만든 채 수집 스레드까지 죽으면 훅 폴백조차 영원히 막혀
        사용자가 영구히 빈 페이지만 보는 이중 실패였다(hub_server_state.should_spawn_collect 참조)."""
        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()


class ServerDelegationTest(HubHookScenarioTest):
    """검수 개정 쟁점 R3 — 상주 서버가 살아 있으면(하트비트 신선) 훅은 spawn 하지 않는다."""

    def test_fresh_heartbeat_suppresses_spawn_even_with_stale_hub_html(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")  # mtime = 지금 = 신선한 하트비트

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_not_called()

    def test_stale_heartbeat_falls_back_to_hook_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))
        hub_collect.SERVER_HEARTBEAT_PATH.write_text("")
        os.utime(hub_collect.SERVER_HEARTBEAT_PATH, (old_time, old_time))  # 서버 크래시 흉내

        with mock.patch("subprocess.Popen") as mock_popen:
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()


class ThrottleDebounceStampTest(HubHookScenarioTest):
    """검수 n3 — 훅 버스트(여러 세션이 거의 동시에 훅을 쏘는 경우) 에서 spawn 이 한 번만 일어난다.

    hub.html 의 mtime 은 spawn 된 자식 프로세스가 다 끝나야 바뀌므로, 그것만 보면 뒤따르는
    훅들이 전부 spawn 을 결정해 버린다(실측: 훅 6개 버스트 → 동시 collect 6개). spawn 직전에
    스탬프를 찍어 디바운스 판정 시점을 옮긴다.
    """

    def test_burst_of_hooks_spawns_collect_only_once(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        with mock.patch("subprocess.Popen") as mock_popen:
            for _ in range(3):
                self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})

        mock_popen.assert_called_once()

    def test_stamp_is_touched_before_first_spawn(self) -> None:
        hub_collect.HUB_HTML_PATH.write_text("stale-marker")
        old_time = time.time() - ONE_HOUR_SECONDS
        os.utime(hub_collect.HUB_HTML_PATH, (old_time, old_time))

        self.assertFalse(hub_collect.SPAWN_STAMP_PATH.exists())
        with mock.patch("subprocess.Popen"):
            self._run_hook_with_stdin({"hook_event_name": "Stop", "session_id": "s", "cwd": "/repo"})
        self.assertTrue(hub_collect.SPAWN_STAMP_PATH.exists())


class PromptRecordingTest(HubHookScenarioTest):
    """프롬프트 기록 상한 — 카드 발췌(120자)가 아니라 툴팁이 보여줄 전문의 상한이다."""

    def _record_prompt(self, prompt: str) -> dict:
        """UserPromptSubmit 훅을 1회 실행하고 그 줄이 남긴 이벤트를 돌려준다."""
        hub_collect.HUB_HTML_PATH.write_text("fresh-marker")   # spawn 억제(이 테스트의 관심사 밖)
        self._run_hook_with_stdin({
            "hook_event_name": "UserPromptSubmit", "session_id": "s", "cwd": "/repo",
            "prompt": prompt,
        })
        today = time.strftime("%Y-%m-%d", time.localtime())
        lines = (hub_collect.EVENTS_DIR / f"{today}.jsonl").read_text(encoding="utf-8").splitlines()
        return json.loads(lines[-1])

    def test_prompt_within_limit_is_recorded_verbatim(self) -> None:
        prompt = "가" * hub_hook.PROMPT_EXCERPT_MAX_CHARS
        self.assertEqual(self._record_prompt(prompt)["p"], prompt)

    def test_prompt_longer_than_display_excerpt_is_recorded_whole(self) -> None:
        """카드에 보이는 120자보다 긴 프롬프트도 기록돼야 툴팁이 보여줄 뒷부분이 존재한다."""
        prompt = ("긴 프롬프트 " * 60).strip()      # 419자 — 종전 상한(120)의 3.5배
        self.assertEqual(self._record_prompt(prompt)["p"], prompt)

    def test_surrounding_whitespace_is_trimmed(self) -> None:
        self.assertEqual(self._record_prompt("  \n 프롬프트 \n\n ")["p"], "프롬프트")

    def test_prompt_over_limit_is_clipped_with_truncation_mark(self) -> None:
        prompt = "나" * (hub_hook.PROMPT_EXCERPT_MAX_CHARS + 500)
        recorded = self._record_prompt(prompt)["p"]

        self.assertEqual(
            recorded, "나" * hub_hook.PROMPT_EXCERPT_MAX_CHARS + hub_hook.PROMPT_TRUNCATION_MARK
        )
        self.assertTrue(recorded.endswith(hub_hook.PROMPT_TRUNCATION_MARK))

    def test_recorded_line_stays_within_single_write_buffer(self) -> None:
        """`_append_event_line` 의 원자성 논거(1회 write())가 성립하는 줄 길이인지 확인한다.

        최악의 줄은 프롬프트 하나가 아니라 "가장 깊은 cwd + 문자당 가장 긴 프롬프트"의 합이다 —
        cwd 는 어디서도 길이를 제한하지 않으므로 함께 넣어야 경계가 진짜 경계가 된다. 상한을
        올릴 때 이 테스트가 먼저 깨져야 한다 — 깨지지 않고 넘어가면 동시 append 가 조용히
        섞이기 시작한다.
        """
        # 문자당 가장 긴 것은 비BMP(4B)가 아니라 제어문자다 — JSON 이 `\uXXXX`(6B)로 이스케이프한다.
        # 상한을 넘겨 말줄임표(3B)까지 붙은 상태가 기록될 수 있는 가장 긴 줄이다.
        prompt = "\x01" * (hub_hook.PROMPT_EXCERPT_MAX_CHARS + 1)
        deepest_cwd = "/" + "a" * (MACOS_PATH_MAX_BYTES - 1)
        hub_collect.HUB_HTML_PATH.write_text("fresh-marker")
        self._run_hook_with_stdin({
            "hook_event_name": "UserPromptSubmit", "session_id": "s" * SESSION_ID_LENGTH,
            "cwd": deepest_cwd, "prompt": prompt,
        })
        today = time.strftime("%Y-%m-%d", time.localtime())
        line_bytes = (hub_collect.EVENTS_DIR / f"{today}.jsonl").read_bytes()

        self.assertLess(len(line_bytes), io.DEFAULT_BUFFER_SIZE)

    def test_record_prompt_excerpt_false_omits_the_field(self) -> None:
        hub_collect.CONFIG_PATH.write_text(json.dumps({"record_prompt_excerpt": False}))
        self.assertNotIn("p", self._record_prompt("기록되지 않아야 하는 프롬프트"))


class AutoInjectedPromptTest(HubHookScenarioTest):
    """CLI 자동주입 블록 처리 — 실측 187건에서 관측된 세 태그(`ide_selection`·`ide_opened_file`·
    `task-notification`)의 두 성격(뒤에 입력이 이어짐 / 순수 알림)을 그대로 시험한다."""

    IDE_SELECTION_BLOCK = (
        "<ide_selection>The user selected the lines 79 to 80 from /repo/a.js:\n"
        "const x = 1;\nconst y = 2;\n</ide_selection>"
    )
    TASK_NOTIFICATION_BLOCK = (
        "<task-notification>\n<task-id>abc123</task-id>\n"
        "<status>completed</status>\n</task-notification>"
    )

    def _record_prompt(self, prompt: str) -> dict:
        hub_collect.HUB_HTML_PATH.write_text("fresh-marker")
        self._run_hook_with_stdin({
            "hook_event_name": "UserPromptSubmit", "session_id": "s", "cwd": "/repo",
            "prompt": prompt,
        })
        today = time.strftime("%Y-%m-%d", time.localtime())
        lines = (hub_collect.EVENTS_DIR / f"{today}.jsonl").read_text(encoding="utf-8").splitlines()
        return json.loads(lines[-1])

    def test_ide_block_is_stripped_and_typed_prompt_survives(self) -> None:
        """실측 사례 — IDE 선택 블록 뒤에 붙어 온 실제 입력이 발췌가 돼야 한다."""
        prompt = self.IDE_SELECTION_BLOCK + "현재 수정사항들을 slide 에도 동일하게 적용해줘."
        self.assertEqual(self._record_prompt(prompt)["p"], "현재 수정사항들을 slide 에도 동일하게 적용해줘.")

    def test_consecutive_auto_injected_blocks_are_all_stripped(self) -> None:
        prompt = (
            "<ide_opened_file>The user opened /repo/b.js</ide_opened_file>\n"
            + self.IDE_SELECTION_BLOCK + "\n푸시해줘"
        )
        self.assertEqual(self._record_prompt(prompt)["p"], "푸시해줘")

    def test_pure_auto_injection_records_no_prompt_field(self) -> None:
        """뒤에 입력이 없는 순수 알림은 기록할 프롬프트가 없다 — 필드를 싣지 않는다."""
        self.assertNotIn("p", self._record_prompt(self.TASK_NOTIFICATION_BLOCK))

    def test_turn_state_event_is_still_recorded_without_prompt_field(self) -> None:
        """`p` 를 빼도 UserPromptSubmit 줄 자체는 남아야 한다 — 턴 상태(working) 판정의 근거다."""
        event = self._record_prompt(self.TASK_NOTIFICATION_BLOCK)
        self.assertEqual(event["e"], "UserPromptSubmit")

    def test_tag_inside_the_body_is_not_stripped(self) -> None:
        """앞에서만 벗긴다 — 본문 중간의 태그를 지우는 것은 입력 왜곡이다."""
        prompt = "이 태그를 설명해줘: " + self.IDE_SELECTION_BLOCK
        self.assertEqual(self._record_prompt(prompt)["p"], prompt)

    def test_unknown_tag_is_left_alone(self) -> None:
        prompt = "<div>사용자가 직접 쓴 태그</div> 이건 벗기지 않는다"
        self.assertEqual(self._record_prompt(prompt)["p"], prompt)


if __name__ == "__main__":
    unittest.main()
