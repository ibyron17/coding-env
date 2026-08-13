"""hub_parse.parse_dashboard_html 단위 테스트. docs/prps/hub-dashboard.md 「테스트 계획」 P1~P8."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_parse  # noqa: E402  (sys.path 조정 후 임포트)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read_fixture(file_name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, file_name), encoding="utf-8") as fixture_file:
        return fixture_file.read()


class ParseLinearDashboardTest(unittest.TestCase):
    """P1 — 실제 선형 대시보드 픅스처."""

    def setUp(self) -> None:
        self.snapshot = hub_parse.parse_dashboard_html(_read_fixture("linear_hub_dashboard.html"))

    def test_returns_snapshot(self) -> None:
        self.assertIsNotNone(self.snapshot)

    def test_title_and_subtitle(self) -> None:
        self.assertEqual(self.snapshot.title, "통합 허브 대시보드 (hub-dashboard)")
        self.assertEqual(self.snapshot.subtitle, "설계 → 승인 → 구현 → 검수 · 전체 경로")

    def test_progress(self) -> None:
        self.assertEqual((self.snapshot.completed, self.snapshot.total, self.snapshot.percent), (2, 4, 50))

    def test_four_steps_with_state_detail_started_at(self) -> None:
        self.assertEqual(len(self.snapshot.steps), 4)
        first, _, third, fourth = self.snapshot.steps
        self.assertEqual(first.state, "done")
        self.assertEqual(first.started_at, "2026-08-10 18:12")
        self.assertIn("PRP 작성 완료", first.detail)
        self.assertEqual(third.state, "active")
        self.assertEqual(fourth.state, "wait")
        self.assertIsNone(fourth.started_at)


class ParseMatrixDashboardTest(unittest.TestCase):
    """P2 — 매트릭스 대시보드 픅스처. P4 — CSS 규칙 줄은 완료 칸으로 세지 않는다."""

    def setUp(self) -> None:
        self.snapshot = hub_parse.parse_dashboard_html(_read_fixture("matrix_hub_dashboard.html"))

    def test_steps_is_empty_and_matrix_done_is_filled(self) -> None:
        self.assertEqual(self.snapshot.steps, ())
        self.assertEqual(self.snapshot.matrix_done, 4)


class ParseImplDashboardTest(unittest.TestCase):
    """P3 — impl 목록이 있는 픅스처."""

    def setUp(self) -> None:
        self.snapshot = hub_parse.parse_dashboard_html(_read_fixture("impl_dashboard.html"))

    def test_impl_counts(self) -> None:
        self.assertEqual((self.snapshot.impl_done, self.snapshot.impl_total), (7, 7))


class ParseOldGenerationDashboardTest(unittest.TestCase):
    """P6 — dz-now-card 가 없는 옛 세대 픅스처. 파싱은 성공하고 없는 필드는 기본값."""

    def setUp(self) -> None:
        self.snapshot = hub_parse.parse_dashboard_html(_read_fixture("old_generation_dashboard.html"))

    def test_parses_successfully_without_now_card(self) -> None:
        self.assertIsNotNone(self.snapshot)
        self.assertEqual(self.snapshot.title, "레거시 세션 대시보드 예시")

    def test_missing_started_at_defaults_to_none(self) -> None:
        for step in self.snapshot.steps:
            self.assertIsNone(step.started_at)

    def test_no_impl_items_defaults_to_zero(self) -> None:
        self.assertEqual((self.snapshot.impl_done, self.snapshot.impl_total), (0, 0))

    def test_missing_step_detail_span_defaults_to_empty_string(self) -> None:
        """검수 m3 회귀 — .step-detail 자체가 없는(이 기능 도입 이전) <li> 도 예외 없이 파싱된다."""
        third_step = self.snapshot.steps[2]
        self.assertEqual(third_step.state, "active")
        self.assertEqual(third_step.detail, "")


class ParseNewGenerationDashboardTest(unittest.TestCase):
    """P9 — 9f32074 이후 세대 픽스처(#dz-subtitle·data-started-at·세션 탭 없음). 파싱 성공."""

    def setUp(self) -> None:
        self.snapshot = hub_parse.parse_dashboard_html(_read_fixture("new_generation_dashboard.html"))

    def test_parses_successfully_without_subtitle(self) -> None:
        self.assertIsNotNone(self.snapshot)
        self.assertEqual(self.snapshot.title, "신세대 대시보드 예시")
        self.assertEqual(self.snapshot.subtitle, "")

    def test_progress_and_steps(self) -> None:
        self.assertEqual((self.snapshot.completed, self.snapshot.total, self.snapshot.percent), (2, 4, 50))
        self.assertEqual(len(self.snapshot.steps), 4)
        self.assertEqual([step.state for step in self.snapshot.steps], ["done", "done", "active", "wait"])

    def test_missing_started_at_defaults_to_none(self) -> None:
        for step in self.snapshot.steps:
            self.assertIsNone(step.started_at)

    def test_impl_counts(self) -> None:
        self.assertEqual((self.snapshot.impl_done, self.snapshot.impl_total), (1, 2))


class ParseInvalidInputTest(unittest.TestCase):
    """P7 — 대시보드가 아닌 HTML / 빈 문자열 / 잘린 파일 → None."""

    def test_empty_string(self) -> None:
        self.assertIsNone(hub_parse.parse_dashboard_html(""))

    def test_unrelated_html(self) -> None:
        self.assertIsNone(hub_parse.parse_dashboard_html("<html><body><h1>다른 페이지</h1></body></html>"))

    def test_truncated_file(self) -> None:
        truncated = _read_fixture("linear_hub_dashboard.html")[:80]
        self.assertIsNone(hub_parse.parse_dashboard_html(truncated))


class ParseEscapedDetailTest(unittest.TestCase):
    """P8 — .step-detail 의 이스케이프된 &lt;T&gt; 는 언이스케이프 없이 그대로 담긴다."""

    def test_escaped_html_entity_preserved(self) -> None:
        html = (
            '<h1 id="dz-title">t</h1>'
            '<div class="sub" id="dz-subtitle">s</div>'
            '<div class="pct" id="dz-progress-pct">0/1 · 0%</div>'
            '<li id="dz-step-1" class="active">'
            '<span class="num">1</span>구현<span class="chip">진행중</span>'
            '<span class="step-detail">Foo&lt;T&gt; 제네릭 처리</span></li>'
            'id="dz-updated">2026-08-10 10:00</div>'
        )
        snapshot = hub_parse.parse_dashboard_html(html)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.steps[0].detail, "Foo&lt;T&gt; 제네릭 처리")


class ParseLogSpanningMultipleLinesTest(unittest.TestCase):
    """P5 — 로그 항목이 여러 줄에 걸쳐 있어도 파서가 오작동하지 않고 로그를 무시한다."""

    def test_multiline_log_does_not_break_parsing(self) -> None:
        snapshot = hub_parse.parse_dashboard_html(_read_fixture("impl_dashboard.html"))
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.title, "음성 파일 저장 실패 대응 — STT 원챔버 저장")


if __name__ == "__main__":
    unittest.main()
