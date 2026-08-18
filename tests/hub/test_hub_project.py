"""hub_project 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M12~M20,
docs/prps/hub-session-revival-and-stale-tier1.md 결정 GN1~GN4(테스트 GN1~GN10),
쟁점 3(Tier1PriorityTest), 결정 N1(ProjectDashboardKeyTest), 결정 N3(ComposeProjectViewsDashboardKeyTest)."""

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


class Tier1GenerationTest(unittest.TestCase):
    """GN1~GN10 — docs/prps/hub-session-revival-and-stale-tier1.md 결정 GN1~GN4."""

    def _session_facts(self, session_id, started_at_ms, ended_at_ms=None):
        return hub_session.SessionFacts(
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
        self.assertFalse(hub_project.is_tier1_from_previous_task(BASE_TIME_MS, ()))

    def test_gn2_live_session_started_after_mtime_is_true(self) -> None:
        self.assertTrue(hub_project.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS + 1,)))

    def test_gn3_live_session_started_before_mtime_is_false(self) -> None:
        self.assertFalse(hub_project.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS - 1,)))

    def test_gn4_one_earlier_session_among_many_makes_it_false(self) -> None:
        self.assertFalse(
            hub_project.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS - 1, BASE_TIME_MS + 1))
        )

    def test_gn5_boundary_equal_start_and_mtime_is_false(self) -> None:
        """경계는 엄격한 > 다 — 같은 밀리초면 그 세션이 갱신했다고 본다."""
        self.assertFalse(hub_project.is_tier1_from_previous_task(BASE_TIME_MS, (BASE_TIME_MS,)))

    def test_gn6_compose_project_views_marks_previous_task(self) -> None:
        tier1 = self._tier1(BASE_TIME_MS)
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_project.compose_project_views(
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
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo": tier1},
            sessions_by_path={"/repo": (working_session, zombie_session)},
            tier3_last_activity_by_path={}, now_ms=now_ms, stale_after_ms=STALE_AFTER_MS,
        )
        zombie_view = next(view for view in views[0].sessions if view.session_id == "s-zombie")
        self.assertEqual(zombie_view.state, "stale")
        self.assertTrue(views[0].tier1_is_previous_task)

    def test_gn8_no_tier1_is_false(self) -> None:
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_project.compose_project_views(
            tier1_by_path={}, sessions_by_path={"/repo": (working_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertFalse(views[0].tier1_is_previous_task)

    def test_gn9_render_hub_html_round_trip_carries_the_field(self) -> None:
        tier1 = self._tier1(BASE_TIME_MS)
        working_session = self._session_facts("s-working", BASE_TIME_MS + 60_000)
        views = hub_project.compose_project_views(
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
        idle_session = hub_session.SessionFacts(
            session_id="s-idle", cwd="/repo", started_at_ms=BASE_TIME_MS + 60_000,
            last_event_at_ms=BASE_TIME_MS + 60_000, last_event_name="Stop", turn_state="ended",
            ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        tier1 = self._tier1(BASE_TIME_MS)
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={"/repo": (idle_session,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS + 60_000, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertFalse(views[0].tier1_is_previous_task)


class EncodeProjectDirNameTest(unittest.TestCase):
    """M12~M14 — 정방향 인코딩과 미확인 처리."""

    def test_m12_hyphenated_directory_name_untouched(self) -> None:
        encoded = hub_project.encode_project_dir_name(
            "/Users/b/private/project/claude-agents-manager"
        )
        self.assertEqual(encoded, "-Users-b-private-project-claude-agents-manager")

    def test_m13_dot_and_slash_both_become_dash(self) -> None:
        encoded = hub_project.encode_project_dir_name("/Users/b/.claude/projects/x")
        self.assertEqual(encoded, "-Users-b--claude-projects-x")

    def test_m14_unmatched_encoded_name_has_no_path(self) -> None:
        resolved, unresolved = hub_project.resolve_project_dirs(
            encoded_names=["-Users-b-unknown-project"],
            candidate_paths=["/Users/b/private/project/coding-env"],
        )
        self.assertEqual(resolved, {})
        self.assertEqual(unresolved, ("-Users-b-unknown-project",))


class ShouldIgnoreCwdTest(unittest.TestCase):
    """M15 — worktree·scratchpad 경로는 무시 대상이다."""

    def test_m15_worktree_and_tmp_paths_are_ignored(self) -> None:
        ignore_globs = hub_model.HubConfig().ignore_globs
        self.assertTrue(hub_project.should_ignore_cwd("/Users/b/repo/.claude/worktrees/f1", ignore_globs))
        self.assertTrue(hub_project.should_ignore_cwd("/private/tmp/claude-501/x", ignore_globs))
        self.assertFalse(hub_project.should_ignore_cwd("/Users/b/private/project/coding-env", ignore_globs))


class ComposeProjectViewsTest(unittest.TestCase):
    """M16~M17, M20 — 프로젝트 상태 합성과 정렬."""

    def _session_facts(self, session_id, cwd, last_event_at_ms, ended_at_ms=None):
        return hub_session.SessionFacts(
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
        working = hub_session.SessionFacts(
            session_id="s-working", cwd="/repo/a", started_at_ms=BASE_TIME_MS,
            last_event_at_ms=BASE_TIME_MS, last_event_name="UserPromptSubmit",
            turn_state="running", ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        views = hub_project.compose_project_views(
            tier1_by_path={}, sessions_by_path={"/repo/a": (working, *sessions[1:])},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].state, "working")

    def test_m17_sorted_by_last_activity_regardless_of_state(self) -> None:
        older_but_active = self._session_facts("s-old", "/repo/old", BASE_TIME_MS)
        newer_but_done = self._session_facts(
            "s-new", "/repo/new", BASE_TIME_MS + 10_000, ended_at_ms=BASE_TIME_MS + 10_000
        )
        views = hub_project.compose_project_views(
            tier1_by_path={},
            sessions_by_path={"/repo/old": (older_but_active,), "/repo/new": (newer_but_done,)},
            tier3_last_activity_by_path={}, now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual([view.path for view in views], ["/repo/new", "/repo/old"])

    def test_m20_tier3_only_project_has_no_sessions(self) -> None:
        views = hub_project.compose_project_views(
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
        views = hub_project.compose_project_views(
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
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo/old": tier1}, sessions_by_path={}, tier3_last_activity_by_path={},
            now_ms=past_stale_window_ms, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].state, "stale")
        self.assertNotEqual(views[0].state, "done")


class Tier1PriorityTest(unittest.TestCase):
    """쟁점 3 — 티어 1 이 있으면 티어 1 이 이긴다(합성 시 tier=1)."""

    def test_tier1_present_wins_over_sessions(self) -> None:
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-", file_mtime_ms=BASE_TIME_MS,
        )
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo": tier1}, sessions_by_path={}, tier3_last_activity_by_path={},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        self.assertEqual(views[0].tier, 1)


class ProjectDashboardKeyTest(unittest.TestCase):
    """U1~U3 — project_dashboard_key 의 결정성·충돌 회피·형식(결정 N1)."""

    def test_u1_same_path_always_same_key(self) -> None:
        self.assertEqual(
            hub_project.project_dashboard_key("/Users/b/repo"),
            hub_project.project_dashboard_key("/Users/b/repo"),
        )

    def test_u2_different_paths_never_collide(self) -> None:
        """구 인코딩(encode_project_dir_name)은 '/a.b' 와 '/a/b' 를 같은 키로 만들었다 —
        sha256 기반은 그 충돌 사례를 포함해 서로 다른 경로가 다른 키를 갖는다."""
        self.assertNotEqual(
            hub_project.project_dashboard_key("/a.b"),
            hub_project.project_dashboard_key("/a/b"),
        )

    def test_u3_key_matches_hex_pattern_and_length(self) -> None:
        key = hub_project.project_dashboard_key("/Users/b/repo")
        self.assertRegex(key, r"^[0-9a-f]{16}$")
        self.assertEqual(len(key), hub_project.DASHBOARD_KEY_LENGTH)


class ComposeProjectViewsDashboardKeyTest(unittest.TestCase):
    """U6 — compose_project_views 가 티어 1 에만 dashboard_key 를 채운다."""

    def test_u6_only_tier1_view_has_dashboard_key(self) -> None:
        tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-", file_mtime_ms=BASE_TIME_MS,
        )
        tier2_session = hub_session.SessionFacts(
            session_id="s1", cwd="/repo/tier2", started_at_ms=BASE_TIME_MS,
            last_event_at_ms=BASE_TIME_MS, last_event_name="Stop", turn_state="ended",
            ended_at_ms=None, task_excerpt=None, subagents=(),
        )
        views = hub_project.compose_project_views(
            tier1_by_path={"/repo/tier1": tier1},
            sessions_by_path={"/repo/tier2": (tier2_session,)},
            tier3_last_activity_by_path={"/repo/tier3": BASE_TIME_MS},
            now_ms=BASE_TIME_MS, stale_after_ms=STALE_AFTER_MS,
        )
        by_path = {view.path: view for view in views}
        self.assertEqual(
            by_path["/repo/tier1"].dashboard_key, hub_project.project_dashboard_key("/repo/tier1")
        )
        self.assertIsNone(by_path["/repo/tier2"].dashboard_key)
        self.assertIsNone(by_path["/repo/tier3"].dashboard_key)


if __name__ == "__main__":
    unittest.main()
