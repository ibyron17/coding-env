"""hub_model 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 M18~M19, M27~M29,
결정 U4~U5(BuildDashboardRegistryTest), U13(SnapshotContentKeyDashboardKeyTest),
결정 D3(UsageSnapshotContentKeyTest)."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_model  # noqa: E402  (sys.path 조정 후 임포트)
import hub_parse  # noqa: E402
import hub_project  # noqa: E402
import hub_session  # noqa: E402
import hub_usage  # noqa: E402

BASE_TIME_MS = 1_786_000_000_000


class RenderHubHtmlTest(unittest.TestCase):
    """M18~M19 — 데이터 마커 치환의 안전성과 정확성."""

    def _minimal_snapshot(self, prompt_excerpt="</script> 공격 시도"):
        session = hub_session.SessionView(
            session_id="s1", short_id="s1", state="working", base_state="working",
            last_event_at_ms=BASE_TIME_MS, task_excerpt=prompt_excerpt, agent_runs=(),
        )
        project = hub_project.ProjectView(
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


class BuildDashboardRegistryTest(unittest.TestCase):
    """U4~U5 — build_dashboard_registry 는 티어 1 만 담고, 값은 <경로>/.claude/dashboard.html.
    U-17 — 승자가 워크트리 파일이면 값은 project.path 가 아니라 그 워크트리 경로다(S5, 결정 WT8)."""

    def _tier1(self, source_path: str) -> hub_parse.Tier1Snapshot:
        return hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-",
            file_mtime_ms=BASE_TIME_MS, source_path=source_path,
        )

    def _project_view(
        self, path: str, tier: int, tier1: hub_parse.Tier1Snapshot | None = None
    ) -> hub_project.ProjectView:
        return hub_project.ProjectView(
            display_name=path.rsplit("/", 1)[-1], path=path, tier=tier, state="idle",
            last_activity_at_ms=BASE_TIME_MS, sessions=(), tier1=tier1, note=None,
        )

    def test_u4_only_tier1_projects_are_registered(self) -> None:
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(
                self._project_view("/repo/one", tier=1, tier1=self._tier1("/repo/one")),
                self._project_view("/repo/two", tier=2),
                self._project_view("/repo/three", tier=3),
            ),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        self.assertEqual(len(registry), 1)
        self.assertIn(hub_project.project_dashboard_key("/repo/one"), registry)

    def test_u5_registry_value_is_dashboard_html_path(self) -> None:
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(self._project_view("/repo/one", tier=1, tier1=self._tier1("/repo/one")),),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        key = hub_project.project_dashboard_key("/repo/one")
        self.assertEqual(registry[key], "/repo/one/.claude/dashboard.html")

    def test_u17_registry_value_uses_worktree_source_path_when_it_wins(self) -> None:
        worktree_path = "/repo/one/.claude/worktrees/w"
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(self._project_view("/repo/one", tier=1, tier1=self._tier1(worktree_path)),),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        key = hub_project.project_dashboard_key("/repo/one")
        self.assertEqual(registry[key], worktree_path + "/.claude/dashboard.html")

    def test_tier1_with_unset_source_path_is_excluded_defensively(self) -> None:
        """검토 지적 반영 — tier==1 인데 tier1.source_path 가 UNSET_SOURCE_PATH(계약 위반)로
        남으면 "" + "/.claude/dashboard.html" 이라는 엉뚱한 경로를 등록하지 않고 제외한다."""
        broken_tier1 = hub_parse.Tier1Snapshot(
            title="t", subtitle="s", completed=1, total=2, percent=50, steps=(),
            matrix_done=None, impl_done=0, impl_total=0, updated_text="-",
            file_mtime_ms=BASE_TIME_MS,   # source_path 생략 → UNSET_SOURCE_PATH
        )
        snapshot = hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS,
            projects=(self._project_view("/repo/one", tier=1, tier1=broken_tier1),),
            unresolved_dir_names=(), warnings=(),
        )
        registry = hub_model.build_dashboard_registry(snapshot)
        self.assertEqual(registry, {})


class SnapshotContentKeyTest(unittest.TestCase):
    """M27~M29 — collected_at_ms 를 뺀 안정적 키(쓰기 억제, 개정 쟁점 R3)."""

    def _session(self, state="working", base_state="working"):
        return hub_session.SessionView(
            session_id="s1", short_id="s1", state=state, base_state=base_state,
            last_event_at_ms=BASE_TIME_MS, task_excerpt=None, agent_runs=(),
        )

    def _snapshot(self, collected_at_ms=BASE_TIME_MS, session_state="working", warnings=()):
        project = hub_project.ProjectView(
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


class SnapshotContentKeyDashboardKeyTest(unittest.TestCase):
    """U13 — dashboard_key 필드 추가 후에도 snapshot_content_key 가 같은 입력에 결정적이다."""

    def _snapshot(self) -> hub_model.HubSnapshot:
        project = hub_project.ProjectView(
            display_name="repo", path="/repo", tier=1, state="idle",
            last_activity_at_ms=BASE_TIME_MS, sessions=(), tier1=None, note=None,
            dashboard_key=hub_project.project_dashboard_key("/repo"),
        )
        return hub_model.HubSnapshot(
            collected_at_ms=BASE_TIME_MS, projects=(project,), unresolved_dir_names=(), warnings=(),
        )

    def test_u13_same_input_yields_same_key(self) -> None:
        self.assertEqual(
            hub_model.snapshot_content_key(self._snapshot()),
            hub_model.snapshot_content_key(self._snapshot()),
        )


if __name__ == "__main__":
    unittest.main()
