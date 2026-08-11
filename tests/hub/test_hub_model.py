"""hub_model 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M1~M20."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_model  # noqa: E402  (sys.path 조정 후 임포트)
import hub_parse  # noqa: E402

STALE_AFTER_MS = 30 * 60 * 1000
BASE_TIME_MS = 1_786_000_000_000


def _event(hook_event_name: str, offset_ms: int = 0, **overrides) -> hub_model.HookEvent:
    fields = {
        "received_at_ms": BASE_TIME_MS + offset_ms,
        "hook_event_name": hook_event_name,
        "session_id": "session-1",
        "cwd": "/Users/byron/private/project/coding-env",
        "source": None,
        "reason": None,
        "agent_id": None,
        "agent_type": None,
        "prompt_excerpt": None,
    }
    fields.update(overrides)
    return hub_model.HookEvent(**fields)


def _facts_from(events):
    return hub_model.build_session_facts(events)["session-1"]


class SessionStateLadderTest(unittest.TestCase):
    """M1~M4 — 우선순위 사다리 + stale 오버레이."""

    def test_m1_prompt_submit_is_working(self) -> None:
        facts = _facts_from([_event("SessionStart"), _event("UserPromptSubmit", 1000)])
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")

    def test_m2_stop_is_idle(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit"), _event("Stop", 1000)])
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")

    def test_m3_ended_session_stays_done_after_two_hours(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit"), _event("SessionEnd", 1000)])
        two_hours_later = facts.last_event_at_ms + 2 * 60 * 60 * 1000
        view = hub_model.compute_session_view(facts, now_ms=two_hours_later, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_m4_stale_overlay_preserves_base_state(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit")])
        thirty_one_minutes_later = facts.last_event_at_ms + 31 * 60 * 1000
        view = hub_model.compute_session_view(facts, now_ms=thirty_one_minutes_later, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "stale")
        self.assertEqual(view.base_state, "working")


class InternalEventFilterTest(unittest.TestCase):
    """M5~M7 — 내부 이벤트 필터와 안전판."""

    def test_m5_compact_session_start_does_not_touch_task_excerpt(self) -> None:
        events = [
            _event("UserPromptSubmit", 0, prompt_excerpt="원래 작업"),
            _event("SessionStart", 1000, source="compact"),
        ]
        facts = _facts_from(events)
        self.assertEqual(facts.task_excerpt, "원래 작업")
        self.assertEqual(facts.last_event_name, "SessionStart")

    def test_m6_untracked_subagent_stop_creates_no_subagent(self) -> None:
        facts = _facts_from([_event("SubagentStop", agent_type="", agent_id="agt-1")])
        self.assertEqual(facts.subagents, ())

    def test_m7_tracked_subagent_stop_is_finalized(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 1000, agent_id="agt-1", agent_type=""),
        ]
        facts = _facts_from(events)
        self.assertEqual(len(facts.subagents), 1)
        self.assertIsNotNone(facts.subagents[0].ended_at_ms)


class SubagentTrackingTest(unittest.TestCase):
    """M8 — 같은 타입 두 개 동시 실행."""

    def test_m8_two_concurrent_same_type_tracked_independently(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStart", 100, agent_id="agt-2", agent_type="implementer"),
            _event("SubagentStop", 200, agent_id="agt-1", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        by_id = {sub.agent_id: sub for sub in facts.subagents}
        self.assertIsNotNone(by_id["agt-1"].ended_at_ms)
        self.assertIsNone(by_id["agt-2"].ended_at_ms)


class InferPhaseTest(unittest.TestCase):
    """M9~M10 — 단계 추정."""

    def test_m9_latest_mapped_subagent_wins(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStart", 200, agent_id="agt-2", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        phase, running = hub_model.infer_phase(facts)
        self.assertEqual(phase, "구현")
        self.assertTrue(running)

    def test_m10_unmapped_agent_type_infers_nothing(self) -> None:
        facts = _facts_from([_event("SubagentStart", 0, agent_id="agt-1", agent_type="Explore")])
        phase, running = hub_model.infer_phase(facts)
        self.assertIsNone(phase)
        self.assertFalse(running)


class ParseEventLineTest(unittest.TestCase):
    """M11 — 깨진 JSON 줄 · 필드 누락 줄은 건너뛰고 나머지로 상태를 만든다."""

    def test_m11_broken_and_missing_field_lines_are_skipped(self) -> None:
        lines = [
            '{"t":1,"e":"SessionStart","s":"s1","c":"/repo"}',
            "not-json-at-all",
            '{"t":2,"e":"UserPromptSubmit"}',
            '{"t":3,"e":"Stop","s":"s1","c":"/repo"}',
        ]
        events = [event for event in (hub_model.parse_event_line(line) for line in lines) if event]
        self.assertEqual(len(events), 2)
        facts = hub_model.build_session_facts(events)["s1"]
        self.assertEqual(facts.last_event_name, "Stop")


class EncodeProjectDirNameTest(unittest.TestCase):
    """M12~M14 — 정방향 인코딩과 미확인 처리."""

    def test_m12_hyphenated_directory_name_untouched(self) -> None:
        encoded = hub_model.encode_project_dir_name(
            "/Users/b/private/project/claude-agents-manager"
        )
        self.assertEqual(encoded, "-Users-b-private-project-claude-agents-manager")

    def test_m13_dot_and_slash_both_become_dash(self) -> None:
        encoded = hub_model.encode_project_dir_name("/Users/b/.claude/projects/x")
        self.assertEqual(encoded, "-Users-b--claude-projects-x")

    def test_m14_unmatched_encoded_name_has_no_path(self) -> None:
        resolved, unresolved = hub_model.resolve_project_dirs(
            encoded_names=["-Users-b-unknown-project"],
            candidate_paths=["/Users/b/private/project/coding-env"],
        )
        self.assertEqual(resolved, {})
        self.assertEqual(unresolved, ("-Users-b-unknown-project",))


class ShouldIgnoreCwdTest(unittest.TestCase):
    """M15 — worktree·scratchpad 경로는 무시 대상이다."""

    def test_m15_worktree_and_tmp_paths_are_ignored(self) -> None:
        ignore_globs = hub_model.HubConfig().ignore_globs
        self.assertTrue(hub_model.should_ignore_cwd("/Users/b/repo/.claude/worktrees/f1", ignore_globs))
        self.assertTrue(hub_model.should_ignore_cwd("/private/tmp/claude-501/x", ignore_globs))
        self.assertFalse(hub_model.should_ignore_cwd("/Users/b/private/project/coding-env", ignore_globs))


class ComposeProjectViewsTest(unittest.TestCase):
    """M16~M17, M20 — 프로젝트 상태 합성과 정렬."""

    def _session_facts(self, session_id, cwd, last_event_at_ms, ended_at_ms=None):
        return hub_model.SessionFacts(
            session_id=session_id, cwd=cwd, started_at_ms=last_event_at_ms,
            last_event_at_ms=last_event_at_ms, last_event_name="Stop", turn_state="ended",
            ended_at_ms=ended_at_ms, task_excerpt=None, subagents=(),
        )

    def test_m16_one_working_beats_three_done(self) -> None:
        sessions = (
            self._session_facts("s-working", "/repo/a", BASE_TIME_MS),
            self._session_facts("s-done-1", "/repo/a", BASE_TIME_MS, ended_at_ms=BASE_TIME_MS),
            self._session_facts("s-done-2", "/repo/a", BASE_TIME_MS, ended_at_ms=BASE_TIME_MS),
            self._session_facts("s-done-3", "/repo/a", BASE_TIME_MS, ended_at_ms=BASE_TIME_MS),
        )
        working = hub_model.SessionFacts(
            session_id="s-working", cwd="/repo/a", started_at_ms=BASE_TIME_MS,
            last_event_at_ms=BASE_TIME_MS, last_event_name="UserPromptSubmit",
            turn_state="running", ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        views = hub_model.compose_project_views(
            tier1_by_path={}, sessions_by_path={"/repo/a": (working, *sessions[1:])},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].state, "working")

    def test_m17_sorted_by_last_activity_regardless_of_state(self) -> None:
        older_but_active = self._session_facts("s-old", "/repo/old", BASE_TIME_MS)
        newer_but_done = self._session_facts(
            "s-new", "/repo/new", BASE_TIME_MS + 10_000, ended_at_ms=BASE_TIME_MS + 10_000
        )
        views = hub_model.compose_project_views(
            tier1_by_path={},
            sessions_by_path={"/repo/old": (older_but_active,), "/repo/new": (newer_but_done,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual([view.path for view in views], ["/repo/new", "/repo/old"])

    def test_m20_tier3_only_project_has_no_sessions(self) -> None:
        views = hub_model.compose_project_views(
            tier1_by_path={}, sessions_by_path={},
            tier3_last_activity_by_path={"/repo/quiet": BASE_TIME_MS},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0].tier, 3)
        self.assertEqual(views[0].sessions, ())
        self.assertEqual(views[0].last_activity_at_ms, BASE_TIME_MS)

    def test_sessionless_tier3_project_with_recent_activity_is_idle_not_done(self) -> None:
        """검수 M3 회귀 — 세션이 없다는 이유로 영구히 'done' 이 되면 안 된다."""
        views = hub_model.compose_project_views(
            tier1_by_path={}, sessions_by_path={},
            tier3_last_activity_by_path={"/repo/quiet": BASE_TIME_MS},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].state, "idle")

    def test_sessionless_tier1_project_past_stale_window_is_stale_not_done(self) -> None:
        """검수 M3 회귀 — 티어 1 전용(세션 없음) 프로젝트도 오래되면 stale, done 은 아니다."""
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-",
            file_mtime_ms=BASE_TIME_MS,
        )
        past_stale_window_ms = BASE_TIME_MS + STALE_AFTER_MS + 1
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo/old": tier1}, sessions_by_path={}, tier3_last_activity_by_path={},
            now_ms=past_stale_window_ms, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].state, "stale")
        self.assertNotEqual(views[0].state, "done")


class RenderHubHtmlTest(unittest.TestCase):
    """M18~M19 — 데이터 마커 치환의 안전성과 정확성."""

    def _minimal_snapshot(self, prompt_excerpt="</script> 공격 시도"):
        session = hub_model.SessionView(
            session_id="s1", short_id="s1", state="working", base_state="working",
            last_event_at_ms=BASE_TIME_MS, task_excerpt=prompt_excerpt,
            inferred_phase=None, inferred_phase_running=False, active_agent_types=(),
        )
        project = hub_model.ProjectView(
            display_name="coding-env", path="/repo", tier=2, state="working",
            last_activity_at_ms=BASE_TIME_MS, sessions=(session,), tier1=None, note=None,
        )
        return hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=(project,),
            unresolved_dir_names=(), warnings=(),
        )

    def test_m18_script_closing_tag_survives_json_round_trip(self) -> None:
        """검수 M1 — HTML 엔티티가 아니라 JSON 유니코드 이스케이프를 써야 JSON.parse 후
        원문(&·<·> 포함)이 그대로 복원된다. <script> 내부는 raw text 라 엔티티가 복원되지 않는다."""
        template = '<html><body><script type="application/json" id="dzh-data">{}</script></body></html>'
        original_excerpt = "A & <b></script>attack</b>"
        rendered = hub_model.render_hub_html(template, self._minimal_snapshot(prompt_excerpt=original_excerpt))
        payload = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]

        self.assertNotIn("</script>", payload)
        self.assertNotIn("&lt;", payload)  # HTML 엔티티가 아니라 \uXXXX 이스케이프여야 한다

        parsed = json.loads(payload)
        round_tripped_excerpt = parsed["projects"][0]["sessions"][0]["task_excerpt"]
        self.assertEqual(round_tripped_excerpt, original_excerpt)

    def test_m19_marker_replaced_exactly_once_rest_untouched(self) -> None:
        template = (
            '<html><head><title>허브</title></head><body>'
            '<script type="application/json" id="dzh-data">PLACEHOLDER</script>'
            "</body></html>"
        )
        rendered = hub_model.render_hub_html(template, self._minimal_snapshot(prompt_excerpt="정상 문자열"))
        self.assertTrue(rendered.startswith('<html><head><title>허브</title></head><body>'))
        self.assertTrue(rendered.endswith("</script></body></html>"))
        inner = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]
        parsed = json.loads(inner)
        self.assertEqual(parsed["collected_at_ms"], BASE_TIME_MS)


class Tier1PriorityTest(unittest.TestCase):
    """쟁점 3 — 티어 1 이 있으면 티어 1 이 이긴다(합성 시 tier=1)."""

    def test_tier1_present_wins_over_sessions(self) -> None:
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-", file_mtime_ms=BASE_TIME_MS,
        )
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={}, tier3_last_activity_by_path={},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].tier, 1)


class ShouldSpawnCollectTest(unittest.TestCase):
    """M21~M24 — 훅의 재수집 spawn 판정(개정 쟁점 R3)."""

    THROTTLE_MS = 5000

    def test_m21_server_alive_always_false(self) -> None:
        """서버가 살아 있으면 쓰로틀이 지났어도 spawn 하지 않는다 — 서버가 전담한다."""
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=True,
            hub_html_mtime_ms=BASE_TIME_MS - 60_000, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m22_server_dead_no_stamp_hub_html_stale(self) -> None:
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=BASE_TIME_MS - 6000, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertTrue(result)

    def test_m23_server_dead_recent_stamp_is_throttled(self) -> None:
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=BASE_TIME_MS - 60_000, spawn_stamp_mtime_ms=BASE_TIME_MS - 2000,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m24_hub_html_missing_but_server_alive_is_false(self) -> None:
        """서버가 살아 있으면 hub.html 이 없어도 False — 다음 사이클에 서버가 만든다."""
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=True,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)

    def test_m24b_hub_html_missing_and_server_dead_with_no_stamp_spawns_immediately(self) -> None:
        """검수 M2-5 — 서버가 죽고 hub.html 도 없으면(HUB_HOME 쓰기 실패 등으로 한 번도 못
        만든 경우 포함) 훅 폴백이 곧바로 뚫려야 한다. 예전에는 hub_html_mtime_ms 가 None 이면
        서버 상태와 무관하게 항상 False 라, 상주 서버가 hub.html 을 한 번도 못 만든 채 수집
        스레드까지 죽으면 훅 폴백조차 영원히 막히는 이중 실패였다."""
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=None,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertTrue(result)

    def test_m24c_hub_html_missing_and_server_dead_but_recent_stamp_is_throttled(self) -> None:
        """즉시 재시도를 허용해도 쓰로틀은 여전히 산다 — 매 훅마다 spawn 하지 않는다."""
        result = hub_model.should_spawn_collect(
            now_ms=BASE_TIME_MS, server_alive=False,
            hub_html_mtime_ms=None, spawn_stamp_mtime_ms=BASE_TIME_MS - 2000,
            throttle_ms=self.THROTTLE_MS,
        )
        self.assertFalse(result)


class IsServerAliveTest(unittest.TestCase):
    """M25 — 하트비트 나이로 상주 서버 생존을 판정한다."""

    TTL_MS = 15_000

    def test_m25_no_heartbeat_file(self) -> None:
        self.assertFalse(hub_model.is_server_alive(BASE_TIME_MS, None, self.TTL_MS))

    def test_m25_just_before_ttl(self) -> None:
        heartbeat_mtime_ms = BASE_TIME_MS - (self.TTL_MS - 1)
        self.assertTrue(hub_model.is_server_alive(BASE_TIME_MS, heartbeat_mtime_ms, self.TTL_MS))

    def test_m25_just_after_ttl(self) -> None:
        heartbeat_mtime_ms = BASE_TIME_MS - self.TTL_MS
        self.assertFalse(hub_model.is_server_alive(BASE_TIME_MS, heartbeat_mtime_ms, self.TTL_MS))


class ServerHeartbeatTtlMsTest(unittest.TestCase):
    """M26 — 수집 주기 3배, 하한 15초."""

    def test_m26_short_interval_hits_floor(self) -> None:
        self.assertEqual(hub_model.server_heartbeat_ttl_ms(1), 15_000)

    def test_m26_default_interval_hits_floor(self) -> None:
        self.assertEqual(hub_model.server_heartbeat_ttl_ms(5), 15_000)

    def test_m26_long_interval_uses_multiplier(self) -> None:
        self.assertEqual(hub_model.server_heartbeat_ttl_ms(60), 180_000)


class SnapshotContentKeyTest(unittest.TestCase):
    """M27~M29 — collected_at_ms 를 뺀 안정적 키(쓰기 억제, 개정 쟁점 R3)."""

    def _session(self, state="working", base_state="working"):
        return hub_model.SessionView(
            session_id="s1", short_id="s1", state=state, base_state=base_state,
            last_event_at_ms=BASE_TIME_MS, task_excerpt=None,
            inferred_phase=None, inferred_phase_running=False, active_agent_types=(),
        )

    def _snapshot(self, collected_at_ms=BASE_TIME_MS, session_state="working", warnings=()):
        project = hub_model.ProjectView(
            display_name="coding-env", path="/repo", tier=2, state=session_state,
            last_activity_at_ms=BASE_TIME_MS, sessions=(self._session(session_state),),
            tier1=None, note=None,
        )
        return hub_model.HubSnapshot(
            collected_at_ms=collected_at_ms, projects=(project,),
            unresolved_dir_names=(), warnings=warnings,
        )

    def test_m27_only_collected_at_ms_differs_same_key(self) -> None:
        key_a = hub_model.snapshot_content_key(self._snapshot(collected_at_ms=BASE_TIME_MS))
        key_b = hub_model.snapshot_content_key(self._snapshot(collected_at_ms=BASE_TIME_MS + 5000))
        self.assertEqual(key_a, key_b)

    def test_m28_session_state_transition_changes_key(self) -> None:
        key_working = hub_model.snapshot_content_key(self._snapshot(session_state="working"))
        key_stale = hub_model.snapshot_content_key(self._snapshot(session_state="stale"))
        self.assertNotEqual(key_working, key_stale)

    def test_m29_warnings_only_difference_changes_key(self) -> None:
        key_clean = hub_model.snapshot_content_key(self._snapshot(warnings=()))
        key_warned = hub_model.snapshot_content_key(self._snapshot(warnings=("문제 발생",)))
        self.assertNotEqual(key_clean, key_warned)


class ParseServerRecordTest(unittest.TestCase):
    """D6 — 정상 1건, 나머지 전부 None(예외 없음). hub_daemon.py 와 hub_collect.py 가 공유하는
    파서를 hub_model.py 하나로 합쳤다(검수 m3) — 실사용 경로(hub_collect.read_server_record)를
    이 테스트가 직접 덮는다."""

    def test_d6_valid_record(self) -> None:
        record = hub_model.parse_server_record(
            '{"pid": 123, "port": 8794, "started_at_ms": 1786000000000}'
        )
        self.assertIsNotNone(record)
        self.assertEqual((record.pid, record.port, record.started_at_ms), (123, 8794, 1786000000000))

    def test_d6_missing_field(self) -> None:
        self.assertIsNone(hub_model.parse_server_record('{"pid": 123, "port": 8794}'))

    def test_d6_broken_json(self) -> None:
        self.assertIsNone(hub_model.parse_server_record("{not valid json"))

    def test_d6_empty_file(self) -> None:
        self.assertIsNone(hub_model.parse_server_record(""))


if __name__ == "__main__":
    unittest.main()
