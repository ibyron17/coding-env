"""hub_model 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M1~M20."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_model  # noqa: E402  (sys.path 조정 후 임포트)
import hub_parse  # noqa: E402
import hub_usage  # noqa: E402

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


class SummarizeAgentRunsTest(unittest.TestCase):
    """A1~A11 — 세션의 서브에이전트 요약(요구 1). infer_phase 를 대체한다."""

    def test_a1_all_started_types_survive_after_completion(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStart", 200, agent_id="agt-2", agent_type="implementer"),
            _event("SubagentStop", 300, agent_id="agt-2", agent_type="implementer"),
            _event("SubagentStart", 400, agent_id="agt-3", agent_type="code-reviewer"),
            _event("SubagentStop", 500, agent_id="agt-3", agent_type="code-reviewer"),
        ]
        facts = _facts_from(events)
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual(
            [run.agent_type for run in runs], ["code-reviewer", "implementer", "design-architect"]
        )
        self.assertTrue(all(not run.is_running for run in runs))
        self.assertEqual([run.phase for run in runs], ["검수", "구현", "설계"])

    def test_a2_same_type_is_merged_and_running_wins(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStart", 200, agent_id="agt-2", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0].is_running)

    def test_a3_empty_agent_type_is_excluded(self) -> None:
        facts = _facts_from([_event("SubagentStart", 0, agent_id="agt-1", agent_type="")])
        self.assertEqual(hub_model.summarize_agent_runs(facts), ())

    def test_a4_unmapped_type_has_no_phase(self) -> None:
        facts = _facts_from(
            [_event("SubagentStart", 0, agent_id="agt-1", agent_type="workflow-subagent")]
        )
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual(len(runs), 1)
        self.assertIsNone(runs[0].phase)
        self.assertTrue(runs[0].is_running)

    def test_a5_no_subagent_yields_empty_tuple(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit")])
        self.assertEqual(hub_model.summarize_agent_runs(facts), ())

    def test_a6_same_start_time_breaks_tie_by_type_name(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStart", 0, agent_id="agt-2", agent_type="design-architect"),
        ]
        facts = _facts_from(events)
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual([run.agent_type for run in runs], ["design-architect", "implementer"])

    def test_a7_done_session_still_exposes_agent_runs(self) -> None:
        """이 PRP 가 고치는 결함의 직접 회귀 테스트 — 완료된 세션도 agent_runs 를 잃지 않는다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
            _event("SessionEnd", 200),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")
        self.assertEqual(len(view.agent_runs), 1)
        self.assertFalse(view.agent_runs[0].is_running)

    def test_a8_agent_runs_reaches_json_contract(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        project = hub_model.ProjectView(
            display_name="coding-env", path="/repo", tier=2, state="working",
            last_activity_at_ms=BASE_TIME_MS, sessions=(view,), tier1=None, note=None,
        )
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
        )
        template = '<html><body><script type="application/json" id="dzh-data">{}</script></body></html>'
        rendered = hub_model.render_hub_html(template, snapshot)
        payload = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]
        parsed = json.loads(payload)
        session_json = parsed["projects"][0]["sessions"][0]
        self.assertEqual(session_json["agent_runs"][0]["agent_type"], "implementer")
        self.assertNotIn("active_agent_types", session_json)
        self.assertNotIn("inferred_phase", session_json)

    def test_a9_agent_runs_difference_changes_content_key(self) -> None:
        def _snapshot(agent_runs):
            session = hub_model.SessionView(
                session_id="s1", short_id="s1", state="working", base_state="working",
                last_event_at_ms=BASE_TIME_MS, task_excerpt=None, agent_runs=agent_runs,
            )
            project = hub_model.ProjectView(
                display_name="coding-env", path="/repo", tier=2, state="working",
                last_activity_at_ms=BASE_TIME_MS, sessions=(session,), tier1=None, note=None,
            )
            return hub_model.HubSnapshot(
                collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
            )

        key_without_runs = hub_model.snapshot_content_key(_snapshot(()))
        key_with_runs = hub_model.snapshot_content_key(
            _snapshot((hub_model.SubagentRunView(agent_type="implementer", phase="구현", is_running=True),))
        )
        self.assertNotEqual(key_without_runs, key_with_runs)

    def test_a10_running_type_sorted_before_later_started_ended_type(self) -> None:
        """결정 K2 — 실행 중 타입은 나중에 시작한 종료 타입보다 앞에 온다.

        상한(MAX_VISIBLE_AGENT_CHIPS) 밖으로 밀려도 지금 진행 중인 작업은 계속 보여야 한다
        (+N 오버플로 칩을 없앤 결정 K1~K3 의 전제).
        """
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("SubagentStart", 1000, agent_id="agt-2", agent_type="implementer"),
            _event("SubagentStop", 1100, agent_id="agt-2", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual([run.agent_type for run in runs], ["code-reviewer", "implementer"])
        self.assertTrue(runs[0].is_running)
        self.assertFalse(runs[1].is_running)

    def test_a11_running_group_sorted_by_recency_then_ended_group(self) -> None:
        """실행 중 타입이 여럿이면 그 안에서는 최근 시작 순, 그 다음에 종료 타입이 온다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="design-architect"),
            _event("SubagentStart", 200, agent_id="agt-2", agent_type="code-reviewer"),
            _event("SubagentStart", 300, agent_id="agt-3", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        runs = hub_model.summarize_agent_runs(facts)
        self.assertEqual(
            [run.agent_type for run in runs], ["implementer", "code-reviewer", "design-architect"]
        )


class SessionRevivalTest(unittest.TestCase):
    """RV1~RV10 — docs/prps/hub-session-revival-and-stale-tier1.md 결정 RV1·RV2."""

    def test_rv1_prompt_then_end_is_done(self) -> None:
        """회귀 방어 — 기존 M3 와 같은 사실. 부활 없이 SessionEnd 만 오면 done 이다."""
        facts = _facts_from([_event("UserPromptSubmit"), _event("SessionEnd", 1000)])
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv2_resume_after_end_clears_ended_at_ms(self) -> None:
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="resume")]
        facts = _facts_from(events)
        self.assertIsNone(facts.ended_at_ms)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")

    def test_rv3_resume_then_prompt_is_working(self) -> None:
        events = [
            _event("SessionEnd"),
            _event("SessionStart", 1000, source="resume"),
            _event("UserPromptSubmit", 2000),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")

    def test_rv4_compact_session_start_does_not_revive(self) -> None:
        """GOTCHA 1 동작 검증 — 필터가 compact 를 부활 트리거에서 원천 차단한다."""
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="compact")]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv5_delayed_subagent_stop_after_end_does_not_revive(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
            _event("SessionEnd", 200),
            _event("SubagentStop", 300, agent_id="agt-1", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv6_stop_after_end_does_not_revive(self) -> None:
        events = [_event("SessionEnd"), _event("Stop", 1000)]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv7_revived_session_goes_stale_after_thirty_one_minutes(self) -> None:
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="resume")]
        facts = _facts_from(events)
        thirty_one_minutes_later = facts.last_event_at_ms + 31 * 60 * 1000
        view = hub_model.compute_session_view(facts, now_ms=thirty_one_minutes_later, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "stale")
        self.assertEqual(view.base_state, "idle")

    def test_rv8_repeated_end_start_cycles_are_idempotent(self) -> None:
        events = [
            _event("SessionEnd", 0),
            _event("SessionStart", 1000, source="resume"),
            _event("SessionEnd", 2000),
            _event("SessionStart", 3000, source="resume"),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")

    def test_rv9_e1_observed_sequence_reproduces_working(self) -> None:
        """E1 실측 축약 — 사용자 보고 재현(G3)."""
        events = [
            _event("UserPromptSubmit", 0),
            _event("SessionEnd", 1000),
            _event("SessionStart", 2000, source="resume"),
            _event("UserPromptSubmit", 3000),
            _event("SubagentStart", 4000, agent_id="agt-1", agent_type="design-architect"),
            _event("Stop", 5000),
        ]
        facts = _facts_from(events)
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")
        self.assertEqual(view.base_state, "working")

    def test_rv10_lone_session_start_is_a_harmless_no_op(self) -> None:
        """X1 — ended_at_ms 가 이미 None 이므로 부활은 무해한 무동작이다."""
        facts = _facts_from([_event("SessionStart", source="startup")])
        view = hub_model.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")


class Tier1GenerationTest(unittest.TestCase):
    """GN1~GN10 — docs/prps/hub-session-revival-and-stale-tier1.md 결정 GN1~GN4."""

    def _session_facts(self, session_id, started_at_ms, ended_at_ms=None):
        return hub_model.SessionFacts(
            session_id=session_id, cwd="/repo", started_at_ms=started_at_ms,
            last_event_at_ms=started_at_ms, last_event_name="UserPromptSubmit",
            turn_state="running" if ended_at_ms is None else "ended",
            ended_at_ms=ended_at_ms, task_excerpt=None, subagents=(),
        )

    def _tier1(self, file_mtime_ms):
        return hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-",
            file_mtime_ms=file_mtime_ms,
        )

    def test_gn1_no_live_sessions_is_false(self) -> None:
        self.assertFalse(hub_model.is_tier1_from_previous_task(BASE_TIME_MS, ()))

    def test_gn2_live_session_started_after_mtime_is_true(self) -> None:
        self.assertTrue(hub_model.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS + 1,)))

    def test_gn3_live_session_started_before_mtime_is_false(self) -> None:
        self.assertFalse(hub_model.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS - 1,)))

    def test_gn4_one_earlier_session_among_many_makes_it_false(self) -> None:
        self.assertFalse(
            hub_model.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS - 1, BASE_TIME_MS + 1))
        )

    def test_gn5_boundary_equal_start_and_mtime_is_false(self) -> None:
        """경계는 엄격한 > 다 — 같은 밀리초면 그 세션이 갱신했다고 본다."""
        self.assertFalse(hub_model.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS,)))

    def test_gn6_compose_project_views_marks_previous_task(self) -> None:
        tier1 = self._tier1(BASE_TIME_MS)
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={"/repo": (working_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertTrue(views[0].tier1_is_previous_task)

    def test_gn7_zombie_stale_session_does_not_break_the_verdict(self) -> None:
        """klago 실측 형태(G5) — stale 좀비 세션이 있어도 working 세션 하나로 판정이 켜진다."""
        tier1 = self._tier1(BASE_TIME_MS)
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        zombie_session = self._session_facts("s-zombie", BASE_TIME_MS - 3_600_000)
        now_ms = zombie_session.started_at_ms + STALE_AFTER_MS + 60_000
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo": tier1},
            sessions_by_path={"/repo": (working_session, zombie_session)},
            tier3_last_activity_by_path={}, now_ms=now_ms, stale_after_ms=STALE_AFTER_MS,
        )
        zombie_view = next(view for view in views[0].sessions if view.session_id == "s-zombie")
        self.assertEqual(zombie_view.state, "stale")
        self.assertTrue(views[0].tier1_is_previous_task)

    def test_gn8_no_tier1_is_false(self) -> None:
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_model.compose_project_views(
            tier1_by_path={}, sessions_by_path={"/repo": (working_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertFalse(views[0].tier1_is_previous_task)

    def test_gn9_render_hub_html_round_trip_carries_the_field(self) -> None:
        tier1 = self._tier1(BASE_TIME_MS)
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={"/repo": (working_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=views, unresolved_dir_names=(), warnings=(),
        )
        template = '<html><body><script type="application/json" id="dzh-data">{}</script></body></html>'
        rendered = hub_model.render_hub_html(template, snapshot)
        payload = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]
        parsed = json.loads(payload)
        self.assertIs(parsed["projects"][0]["tier1_is_previous_task"], True)

    def test_gn10_idle_only_session_is_false(self) -> None:
        """결정 GN2 — idle 은 판정 집합 밖이다. 승인 항목 4 가 뒤집히면 이 케이스가 True 로 바뀐다."""
        idle_session = hub_model.SessionFacts(
            session_id="s-idle", cwd="/repo", started_at_ms=BASE_TIME_MS + 60_000,
            last_event_at_ms=BASE_TIME_MS + 60_000, last_event_name="Stop", turn_state="ended",
            ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        tier1 = self._tier1(BASE_TIME_MS)
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={"/repo": (idle_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertFalse(views[0].tier1_is_previous_task)


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
            last_event_at_ms=BASE_TIME_MS, task_excerpt=prompt_excerpt, agent_runs=(),
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

    def test_case28_usage_none_snapshot_renders_json_null(self) -> None:
        template = '<html><body><script type="application/json" id="dzh-data">{}</script></body></html>'
        rendered = hub_model.render_hub_html(template, self._minimal_snapshot())
        payload = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]
        self.assertIn('"usage": null', payload)
        parsed = json.loads(payload)
        self.assertIsNone(parsed["usage"])


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


class ProjectDashboardKeyTest(unittest.TestCase):
    """U1~U3 — project_dashboard_key 의 결정성·충돌 회피·형식(결정 N1)."""

    def test_u1_same_path_always_same_key(self) -> None:
        self.assertEqual(
            hub_model.project_dashboard_key("/Users/b/repo"),
            hub_model.project_dashboard_key("/Users/b/repo"),
        )

    def test_u2_different_paths_never_collide(self) -> None:
        """구 인코딩(encode_project_dir_name)은 '/a.b' 와 '/a/b' 를 같은 키로 만들었다 —
        sha256 기반은 그 충돌 사례를 포함해 서로 다른 경로가 다른 키를 갖는다."""
        self.assertNotEqual(
            hub_model.project_dashboard_key("/a.b"),
            hub_model.project_dashboard_key("/a/b"),
        )

    def test_u3_key_matches_hex_pattern_and_length(self) -> None:
        key = hub_model.project_dashboard_key("/Users/b/repo")
        self.assertRegex(key, r"^[0-9a-f]{16}$")
        self.assertEqual(len(key), hub_model.DASHBOARD_KEY_LENGTH)


class BuildDashboardRegistryTest(unittest.TestCase):
    """U4~U5 — build_dashboard_registry 는 티어 1 만 담고, 값은 <경로>/.claude/dashboard.html."""

    def _project_view(self, path: str, tier: int) -> hub_model.ProjectView:
        return hub_model.ProjectView(
            display_name=path.rsplit("/", 1)[-1], path=path, tier=tier, state="idle",
            last_activity_at_ms=BASE_TIME_MS, sessions=(), tier1=None, note=None,
        )

    def test_u4_only_tier1_projects_are_registered(self) -> None:
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(
                self._project_view("/repo/one", tier=1),
                self._project_view("/repo/two", tier=2),
                self._project_view("/repo/three", tier=3),
            ),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        self.assertEqual(len(registry), 1)
        self.assertIn(hub_model.project_dashboard_key("/repo/one"), registry)

    def test_u5_registry_value_is_dashboard_html_path(self) -> None:
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(self._project_view("/repo/one", tier=1),),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        key = hub_model.project_dashboard_key("/repo/one")
        self.assertEqual(registry[key], "/repo/one/.claude/dashboard.html")


class ComposeProjectViewsDashboardKeyTest(unittest.TestCase):
    """U6 — compose_project_views 가 티어 1 에만 dashboard_key 를 채운다."""

    def test_u6_only_tier1_view_has_dashboard_key(self) -> None:
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-", file_mtime_ms=BASE_TIME_MS,
        )
        tier2_session = hub_model.SessionFacts(
            session_id="s1", cwd="/repo/tier2", started_at_ms=BASE_TIME_MS,
            last_event_at_ms=BASE_TIME_MS, last_event_name="Stop", turn_state="ended",
            ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        views = hub_model.compose_project_views(
            tier1_by_path={"/repo/tier1": tier1},
            sessions_by_path={"/repo/tier2": (tier2_session,)},
            tier3_last_activity_by_path={"/repo/tier3": BASE_TIME_MS},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        by_path = {view.path: view for view in views}
        self.assertEqual(
            by_path["/repo/tier1"].dashboard_key, hub_model.project_dashboard_key("/repo/tier1")
        )
        self.assertIsNone(by_path["/repo/tier2"].dashboard_key)
        self.assertIsNone(by_path["/repo/tier3"].dashboard_key)


class SnapshotContentKeyDashboardKeyTest(unittest.TestCase):
    """U13 — dashboard_key 필드 추가 후에도 snapshot_content_key 가 같은 입력에 결정적이다."""

    def _snapshot(self) -> hub_model.HubSnapshot:
        project = hub_model.ProjectView(
            display_name="repo", path="/repo", tier=1, state="idle",
            last_activity_at_ms=BASE_TIME_MS, sessions=(), tier1=None, note=None,
            dashboard_key=hub_model.project_dashboard_key("/repo"),
        )
        return hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
        )

    def test_u13_same_input_yields_same_key(self) -> None:
        self.assertEqual(
            hub_model.snapshot_content_key(self._snapshot()),
            hub_model.snapshot_content_key(self._snapshot()),
        )


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
            last_event_at_ms=BASE_TIME_MS, task_excerpt=None, agent_runs=(),
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


class UsageSnapshotContentKeyTest(unittest.TestCase):
    """케이스 26~27 — usage 필드와 snapshot_content_key 의 상호작용(결정 D3 회귀 방지)."""

    def _snapshot(self, collected_at_ms=BASE_TIME_MS, usage=None):
        return hub_model.HubSnapshot(
            collected_at_ms=collected_at_ms, projects=(), unresolved_dir_names=(),
            warnings=(), usage=usage,
        )

    def test_case26_usage_only_difference_changes_key(self) -> None:
        key_without_usage = hub_model.snapshot_content_key(self._snapshot(usage=None))
        key_with_usage = hub_model.snapshot_content_key(
            self._snapshot(usage=hub_usage.UsageSample(sampled_at_ms=BASE_TIME_MS, session_percent=10, weekly_percent=19))
        )
        self.assertNotEqual(key_without_usage, key_with_usage)

    def test_case27_collected_at_ms_only_difference_same_key_usage_present(self) -> None:
        """D3 회귀 방지 — usage 가 있어도 collected_at_ms 만 다르면 키는 같다(5초마다 재작성되지 않는다)."""
        usage = hub_usage.UsageSample(sampled_at_ms=BASE_TIME_MS, session_percent=10, weekly_percent=19)
        key_a = hub_model.snapshot_content_key(self._snapshot(collected_at_ms=BASE_TIME_MS, usage=usage))
        key_b = hub_model.snapshot_content_key(self._snapshot(collected_at_ms=BASE_TIME_MS + 5000, usage=usage))
        self.assertEqual(key_a, key_b)


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


class ShouldAttemptUsageApiPollTest(unittest.TestCase):
    """U7~U8 — 첫 시도는 항상 True, 이후로는 주기 도달 여부로 판정한다(결정 A3)."""

    BASE_INTERVAL_SECONDS = 300

    def test_u7_first_attempt_is_always_true(self) -> None:
        state = hub_model.UsageApiPollState()
        self.assertTrue(
            hub_model.should_attempt_usage_api_poll(BASE_TIME_MS, state, self.BASE_INTERVAL_SECONDS)
        )

    def test_u8_before_delay_elapses_is_false(self) -> None:
        state = hub_model.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        almost_five_minutes_ms = 5 * 60 * 1000 - 1
        self.assertFalse(
            hub_model.should_attempt_usage_api_poll(
                BASE_TIME_MS + almost_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )

    def test_u8_exactly_at_delay_is_true(self) -> None:
        state = hub_model.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        exactly_five_minutes_ms = 5 * 60 * 1000
        self.assertTrue(
            hub_model.should_attempt_usage_api_poll(
                BASE_TIME_MS + exactly_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )

    def test_u8_past_delay_is_true(self) -> None:
        state = hub_model.UsageApiPollState(last_attempt_at_ms=BASE_TIME_MS, consecutive_failures=0)
        past_five_minutes_ms = 5 * 60 * 1000 + 1
        self.assertTrue(
            hub_model.should_attempt_usage_api_poll(
                BASE_TIME_MS + past_five_minutes_ms, state, self.BASE_INTERVAL_SECONDS
            )
        )


class UsageApiPollDelayMsTest(unittest.TestCase):
    """U9~U11 — 연속 실패마다 지연이 2배씩 늘고 상한(60분)에서 멈춘다. 429 는 즉시 상한(결정 A3)."""

    BASE_INTERVAL_SECONDS = 300  # 5분
    ONE_MINUTE_MS = 60 * 1000

    def _delay_minutes(self, consecutive_failures: int, forced_multiplier: int | None = None) -> float:
        state = hub_model.UsageApiPollState(
            consecutive_failures=consecutive_failures, forced_multiplier=forced_multiplier
        )
        return hub_model.usage_api_poll_delay_ms(state, self.BASE_INTERVAL_SECONDS) / self.ONE_MINUTE_MS

    def test_u9_delay_doubles_per_consecutive_failure_up_to_the_cap(self) -> None:
        self.assertEqual(self._delay_minutes(1), 5)
        self.assertEqual(self._delay_minutes(2), 10)
        self.assertEqual(self._delay_minutes(3), 20)
        self.assertEqual(self._delay_minutes(4), 40)
        self.assertEqual(self._delay_minutes(5), 60)

    def test_u9_delay_stays_capped_beyond_the_fifth_failure(self) -> None:
        self.assertEqual(self._delay_minutes(6), 60)
        self.assertEqual(self._delay_minutes(20), 60)

    def test_u10_success_resets_consecutive_failures_to_zero(self) -> None:
        state = hub_model.UsageApiPollState(consecutive_failures=4)
        next_state = hub_model.next_usage_api_poll_state(BASE_TIME_MS, state, failure_reason=None)
        self.assertEqual(next_state.consecutive_failures, 0)
        self.assertIsNone(next_state.forced_multiplier)

    def test_u11_http_rate_limited_jumps_straight_to_the_cap(self) -> None:
        state = hub_model.UsageApiPollState(consecutive_failures=0)
        next_state = hub_model.next_usage_api_poll_state(BASE_TIME_MS, state, failure_reason="http_rate_limited")
        self.assertEqual(
            hub_model.usage_api_poll_delay_ms(next_state, self.BASE_INTERVAL_SECONDS) / self.ONE_MINUTE_MS, 60
        )


class NextUsageApiPollStateTest(unittest.TestCase):
    """U12 — next_usage_api_poll_state 는 항상 새 객체를 돌려준다(원본 불변)."""

    def test_u12_returns_a_new_object_not_the_original(self) -> None:
        original = hub_model.UsageApiPollState()
        updated = hub_model.next_usage_api_poll_state(BASE_TIME_MS, original, failure_reason="network_error")
        self.assertIsNot(updated, original)
        self.assertEqual(original, hub_model.UsageApiPollState())  # 원본 필드도 그대로


if __name__ == "__main__":
    unittest.main()
