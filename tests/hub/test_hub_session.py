"""hub_session 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M1~M11,
docs/prps/hub-zombie-subagent-guard.md 결정 ZG1~ZG7(테스트 ZG1~ZG15),
docs/prps/hub-session-revival-and-stale-tier1.md 결정 RV1~RV3(테스트 RV1~RV10)."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_model  # noqa: E402  (sys.path 조정 후 임포트)
import hub_parse  # noqa: E402
import hub_project  # noqa: E402
import hub_session  # noqa: E402

STALE_AFTER_MS = 30 * 60 * 1000
BASE_TIME_MS = 1_786_000_000_000


def _event(hook_event_name: str, offset_ms: int = 0, **overrides) -> hub_session.HookEvent:
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
    return hub_session.HookEvent(**fields)


def _facts_from(events):
    return hub_session.build_session_facts(events)["session-1"]


class SessionStateLadderTest(unittest.TestCase):
    """M1~M4 — 우선순위 사다리 + stale 오버레이."""

    def test_m1_prompt_submit_is_working(self) -> None:
        facts = _facts_from([_event("SessionStart"), _event("UserPromptSubmit", 1000)])
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")

    def test_m2_stop_is_idle(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit"), _event("Stop", 1000)])
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")

    def test_m3_ended_session_stays_done_after_two_hours(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit"), _event("SessionEnd", 1000)])
        two_hours_later = facts.last_event_at_ms + 2 * 60 * 60 * 1000
        view = hub_session.compute_session_view(facts, now_ms=two_hours_later, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_m4_stale_overlay_preserves_base_state(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit")])
        thirty_one_minutes_later = facts.last_event_at_ms + 31 * 60 * 1000
        view = hub_session.compute_session_view(facts, now_ms=thirty_one_minutes_later, stale_after_ms=STALE_AFTER_MS)
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


class SubagentZombieGuardTest(unittest.TestCase):
    """ZG1~ZG15 — docs/prps/hub-zombie-subagent-guard.md 결정 ZG1~ZG7.

    `SubagentStop` 을 못 본 서브에이전트가 나이(`now_ms - started_at_ms`)로 좀비 판정을 받는지,
    그리고 그 판정이 상태(`base_state`)와 칩(`is_running`)에 동시에 반영되는지를 검증한다.
    """

    ZOMBIE_AFTER_MS = 90 * 60 * 1000
    ONE_MINUTE_MS = 60 * 1000
    # stale 오버레이(30분)는 M4·RV7 이 이미 별도로 잠갔다. 이 클래스는 base_state·is_running 이
    # 나이만으로 어떻게 갈리는지를 보려는 것이라, 오버레이가 우연히 결과를 가리지 않도록 시나리오
    # 지속 시간(최대 약 3시간)보다 넉넉히 큰 stale_after_ms 를 쓴다(실측 E9 — 오버레이는 sticky
    # working 을 "부분적으로만" 구제하므로, 오버레이에 기대지 않는 경로를 따로 확인해야 한다).
    NO_OVERLAY_STALE_AFTER_MS = 24 * 60 * 60 * 1000

    def test_zg1_ended_subagent_is_never_running_regardless_of_age(self) -> None:
        subagent = hub_session.SubagentFact(
            agent_id="agt-1", agent_type="implementer",
            started_at_ms=BASE_TIME_MS, ended_at_ms=BASE_TIME_MS + 1000,
        )
        self.assertFalse(
            hub_session.is_running_subagent(subagent, now_ms=BASE_TIME_MS + 2000, zombie_after_ms=self.ZOMBIE_AFTER_MS)
        )

    def test_zg2_age_one_ms_under_threshold_is_running(self) -> None:
        subagent = hub_session.SubagentFact(
            agent_id="agt-1", agent_type="implementer", started_at_ms=BASE_TIME_MS, ended_at_ms=None,
        )
        now_ms = BASE_TIME_MS + self.ZOMBIE_AFTER_MS - 1
        self.assertTrue(hub_session.is_running_subagent(subagent, now_ms=now_ms, zombie_after_ms=self.ZOMBIE_AFTER_MS))

    def test_zg3_age_exactly_threshold_is_zombie(self) -> None:
        """경계는 >= 가 좀비다(GOTCHA 5) — < 로 잘못 쓰면 이 테스트가 잡는다."""
        subagent = hub_session.SubagentFact(
            agent_id="agt-1", agent_type="implementer", started_at_ms=BASE_TIME_MS, ended_at_ms=None,
        )
        now_ms = BASE_TIME_MS + self.ZOMBIE_AFTER_MS
        self.assertFalse(hub_session.is_running_subagent(subagent, now_ms=now_ms, zombie_after_ms=self.ZOMBIE_AFTER_MS))

    def test_zg4_age_past_threshold_by_an_hour_is_zombie(self) -> None:
        subagent = hub_session.SubagentFact(
            agent_id="agt-1", agent_type="implementer", started_at_ms=BASE_TIME_MS, ended_at_ms=None,
        )
        one_hour_ms = 60 * self.ONE_MINUTE_MS
        now_ms = BASE_TIME_MS + self.ZOMBIE_AFTER_MS + one_hour_ms
        self.assertFalse(hub_session.is_running_subagent(subagent, now_ms=now_ms, zombie_after_ms=self.ZOMBIE_AFTER_MS))

    def test_zg5_negative_age_from_clock_skew_is_running(self) -> None:
        """X4 — now_ms < started_at_ms 이면 안전한 방향(실행 중)으로 본다."""
        subagent = hub_session.SubagentFact(
            agent_id="agt-1", agent_type="implementer", started_at_ms=BASE_TIME_MS, ended_at_ms=None,
        )
        now_ms = BASE_TIME_MS - 1000
        self.assertTrue(hub_session.is_running_subagent(subagent, now_ms=now_ms, zombie_after_ms=self.ZOMBIE_AFTER_MS))

    def test_zg6_e1_zombie_after_three_hours_reproduces_idle(self) -> None:
        """E1 실측 재현(G1) — 현재 코드에서는 working 이다(버그 재현)."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("UserPromptSubmit", 1000),
            _event("Stop", 2000),
        ]
        facts = _facts_from(events)
        three_hours_later = facts.started_at_ms + 3 * 60 * self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(
            facts, now_ms=three_hours_later, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS
        )
        self.assertEqual(view.state, "idle")
        self.assertEqual(view.base_state, "idle")

    def test_zg7_age_89_minutes_still_working(self) -> None:
        """오탐 방어 — 아직 90분이 안 됐으면 좀비가 아니다. 구현 전에도 통과해야 한다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("UserPromptSubmit", 1000),
            _event("Stop", 2000),
        ]
        facts = _facts_from(events)
        eighty_nine_minutes_later = facts.started_at_ms + 89 * self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(
            facts, now_ms=eighty_nine_minutes_later, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS
        )
        self.assertEqual(view.state, "working")

    def test_zg8_running_type_wins_over_zombie_same_type(self) -> None:
        """X2 — 같은 타입에 좀비 1 + 정상 실행 1 이면 정상 쪽이 이긴다. 구현 전에도 통과해야 한다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStart", self.ZOMBIE_AFTER_MS, agent_id="agt-2", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS
        view = hub_session.compute_session_view(facts, now_ms=now_ms, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS)
        self.assertEqual(view.state, "working")
        self.assertEqual(len(view.agent_runs), 1)
        self.assertTrue(view.agent_runs[0].is_running)

    def test_zg9_zombie_chip_demotes_to_ended_group_ordering(self) -> None:
        """결정 ZG4 — 좀비 칩은 종료 그룹으로 내려가 최근 시작순에 편입된다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("SubagentStart", 1000, agent_id="agt-2", agent_type="implementer"),
            _event("SubagentStop", 2000, agent_id="agt-2", agent_type="implementer"),
            _event("Stop", 3000),
        ]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        runs = hub_session.summarize_agent_runs(facts, now_ms=now_ms)
        self.assertTrue(all(not run.is_running for run in runs))
        self.assertEqual([run.agent_type for run in runs], ["implementer", "code-reviewer"])

    def test_zg10_running_turn_overrides_zombie_only_session(self) -> None:
        """X3 — turn_state=="running" 이면 좀비뿐이어도 working. 구현 전에도 통과해야 한다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("UserPromptSubmit", 1000),
        ]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(facts, now_ms=now_ms, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS)
        self.assertEqual(view.state, "working")

    def test_zg11_state_and_chips_never_contradict_for_zombie_only_session(self) -> None:
        """G4·S4 — 좀비만 있는 세션에서 상태와 칩이 동시에 어긋나지 않는다(동시 단정)."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("UserPromptSubmit", 1000),
            _event("Stop", 2000),
        ]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(facts, now_ms=now_ms, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS)
        self.assertNotEqual(view.state, "working")
        self.assertTrue(all(not run.is_running for run in view.agent_runs))

    def test_zg12_longest_real_run_reproduces_e6(self) -> None:
        """E6 실측 최장 재현(G2) — T=기본값(SUBAGENT_ZOMBIE_AFTER_MS)에서도 좀비로 오인되지 않는다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("Stop", 100),
        ]
        facts = _facts_from(events)
        forty_seven_point_three_minutes_ms = int(47.3 * self.ONE_MINUTE_MS)
        now_ms = facts.started_at_ms + forty_seven_point_three_minutes_ms
        runs = hub_session.summarize_agent_runs(facts, now_ms=now_ms)
        self.assertTrue(runs[0].is_running)

    def test_zg13_zombie_session_is_excluded_from_tier1_generation_verdict(self) -> None:
        """결정 ZG6·G5 — 좀비가 살아 있는 세션 집합에서 빠져 세대 판정 오염이 해소된다."""
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-",
            file_mtime_ms=BASE_TIME_MS,
        )
        events = [
            _event("SubagentStart", 60_000, agent_id="agt-1", agent_type="code-reviewer"),
            _event("Stop", 61_000),
        ]
        facts = hub_session.build_session_facts(events)["session-1"]
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo": tier1},
            sessions_by_path={"/repo": (facts,)},
            tier3_last_activity_by_path={},
            now_ms=now_ms, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS,
        )
        self.assertNotEqual(views[0].state, "working")
        self.assertFalse(views[0].tier1_is_previous_task)

    def test_zg14_zombie_chip_survives_json_round_trip_as_not_running(self) -> None:
        """선례: 기존 test_a8·test_gn9 — 렌더링 왕복 후에도 계약이 유지된다."""
        events = [_event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer")]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + self.ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(
            facts, now_ms=now_ms, stale_after_ms=self.NO_OVERLAY_STALE_AFTER_MS
        )
        project = hub_project.ProjectView(
            display_name="coding-env", path="/repo", tier=2, state=view.state,
            last_activity_at_ms=BASE_TIME_MS, sessions=(view,), tier1=None, note=None,
        )
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
        )
        template = '<html><body><script type="application/json" id="dzh-data">{}</script></body></html>'
        rendered = hub_model.render_hub_html(template, snapshot)
        payload = rendered.split('id="dzh-data">', 1)[1].rsplit("</script>", 1)[0]
        parsed = json.loads(payload)
        self.assertIs(parsed["projects"][0]["sessions"][0]["agent_runs"][0]["is_running"], False)

    def test_zg15_compute_session_view_default_zombie_threshold_applies(self) -> None:
        """GOTCHA 8 회귀 — zombie_after_ms 없이 호출해도 SUBAGENT_ZOMBIE_AFTER_MS 가 적용된다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="code-reviewer"),
            _event("Stop", 1000),
        ]
        facts = _facts_from(events)
        now_ms = facts.started_at_ms + hub_session.SUBAGENT_ZOMBIE_AFTER_MS + self.ONE_MINUTE_MS
        view = hub_session.compute_session_view(facts, now_ms, self.NO_OVERLAY_STALE_AFTER_MS)
        self.assertEqual(view.base_state, "idle")


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
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
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
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0].is_running)

    def test_a3_empty_agent_type_is_excluded(self) -> None:
        facts = _facts_from([_event("SubagentStart", 0, agent_id="agt-1", agent_type="")])
        self.assertEqual(hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms), ())

    def test_a4_unmapped_type_has_no_phase(self) -> None:
        facts = _facts_from(
            [_event("SubagentStart", 0, agent_id="agt-1", agent_type="workflow-subagent")]
        )
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
        self.assertEqual(len(runs), 1)
        self.assertIsNone(runs[0].phase)
        self.assertTrue(runs[0].is_running)

    def test_a5_no_subagent_yields_empty_tuple(self) -> None:
        facts = _facts_from([_event("UserPromptSubmit")])
        self.assertEqual(hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms), ())

    def test_a6_same_start_time_breaks_tie_by_type_name(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStart", 0, agent_id="agt-2", agent_type="design-architect"),
        ]
        facts = _facts_from(events)
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
        self.assertEqual([run.agent_type for run in runs], ["design-architect", "implementer"])

    def test_a7_done_session_still_exposes_agent_runs(self) -> None:
        """이 PRP 가 고치는 결함의 직접 회귀 테스트 — 완료된 세션도 agent_runs 를 잃지 않는다."""
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
            _event("SessionEnd", 200),
        ]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")
        self.assertEqual(len(view.agent_runs), 1)
        self.assertFalse(view.agent_runs[0].is_running)

    def test_a8_agent_runs_reaches_json_contract(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        project = hub_project.ProjectView(
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
            session = hub_session.SessionView(
                session_id="s1", short_id="s1", state="working", base_state="working",
                last_event_at_ms=BASE_TIME_MS, task_excerpt=None, agent_runs=agent_runs,
            )
            project = hub_project.ProjectView(
                display_name="coding-env", path="/repo", tier=2, state="working",
                last_activity_at_ms=BASE_TIME_MS, sessions=(session,), tier1=None, note=None,
            )
            return hub_model.HubSnapshot(
                collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
            )

        key_without_runs = hub_model.snapshot_content_key(_snapshot(()))
        key_with_runs = hub_model.snapshot_content_key(
            _snapshot((hub_session.SubagentRunView(agent_type="implementer", phase="구현", is_running=True),))
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
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
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
        runs = hub_session.summarize_agent_runs(facts, now_ms=facts.last_event_at_ms)
        self.assertEqual(
            [run.agent_type for run in runs], ["implementer", "code-reviewer", "design-architect"]
        )


class SessionRevivalTest(unittest.TestCase):
    """RV1~RV10 — docs/prps/hub-session-revival-and-stale-tier1.md 결정 RV1·RV2."""

    def test_rv1_prompt_then_end_is_done(self) -> None:
        """회귀 방어 — 기존 M3 와 같은 사실. 부활 없이 SessionEnd 만 오면 done 이다."""
        facts = _facts_from([_event("UserPromptSubmit"), _event("SessionEnd", 1000)])
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv2_resume_after_end_clears_ended_at_ms(self) -> None:
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="resume")]
        facts = _facts_from(events)
        self.assertIsNone(facts.ended_at_ms)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")

    def test_rv3_resume_then_prompt_is_working(self) -> None:
        events = [
            _event("SessionEnd"),
            _event("SessionStart", 1000, source="resume"),
            _event("UserPromptSubmit", 2000),
        ]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")

    def test_rv4_compact_session_start_does_not_revive(self) -> None:
        """GOTCHA 1 동작 검증 — 필터가 compact 를 부활 트리거에서 원천 차단한다."""
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="compact")]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv5_delayed_subagent_stop_after_end_does_not_revive(self) -> None:
        events = [
            _event("SubagentStart", 0, agent_id="agt-1", agent_type="implementer"),
            _event("SubagentStop", 100, agent_id="agt-1", agent_type="implementer"),
            _event("SessionEnd", 200),
            _event("SubagentStop", 300, agent_id="agt-1", agent_type="implementer"),
        ]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv6_stop_after_end_does_not_revive(self) -> None:
        events = [_event("SessionEnd"), _event("Stop", 1000)]
        facts = _facts_from(events)
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "done")

    def test_rv7_revived_session_goes_stale_after_thirty_one_minutes(self) -> None:
        events = [_event("SessionEnd"), _event("SessionStart", 1000, source="resume")]
        facts = _facts_from(events)
        thirty_one_minutes_later = facts.last_event_at_ms + 31 * 60 * 1000
        view = hub_session.compute_session_view(facts, now_ms=thirty_one_minutes_later, stale_after_ms=STALE_AFTER_MS)
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
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
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
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "working")
        self.assertEqual(view.base_state, "working")

    def test_rv10_lone_session_start_is_a_harmless_no_op(self) -> None:
        """X1 — ended_at_ms 가 이미 None 이므로 부활은 무해한 무동작이다."""
        facts = _facts_from([_event("SessionStart", source="startup")])
        view = hub_session.compute_session_view(facts, now_ms=facts.last_event_at_ms, stale_after_ms=STALE_AFTER_MS)
        self.assertEqual(view.state, "idle")


class ParseEventLineTest(unittest.TestCase):
    """M11 — 깨진 JSON 줄 · 필드 누락 줄은 건너뛰고 나머지로 상태를 만든다."""

    def test_m11_broken_and_missing_field_lines_are_skipped(self) -> None:
        lines = [
            '{"t":1,"e":"SessionStart","s":"s1","c":"/repo"}',
            "not-json-at-all",
            '{"t":2,"e":"UserPromptSubmit"}',
            '{"t":3,"e":"Stop","s":"s1","c":"/repo"}',
        ]
        events = [event for event in (hub_session.parse_event_line(line) for line in lines) if event]
        self.assertEqual(len(events), 2)
        facts = hub_session.build_session_facts(events)["s1"]
        self.assertEqual(facts.last_event_name, "Stop")


if __name__ == "__main__":
    unittest.main()
