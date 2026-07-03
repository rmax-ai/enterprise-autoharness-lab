"""Tests for reporting modules — markdown, HTML, CSV, differ."""

import tempfile
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry
from autoharness_lab.reporting.csv_exporter import generate_csv, save_csv
from autoharness_lab.reporting.differ import (
    diff_harness_versions,
    diff_parent_child,
    save_diff,
)
from autoharness_lab.reporting.html import generate_html_report, save_html_report
from autoharness_lab.reporting.markdown import (
    generate_markdown_report,
    save_markdown_report,
)
from autoharness_lab.synthesis.search import IterationRecord, SynthesisResult

VALID_CODE_A = """
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": proposed_action, "reason": "v0", "confidence": 0.5}
"""

VALID_CODE_B = """
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {"accepted": True, "normalized_action": proposed_action, "reason": "v1", "confidence": 0.9}
    return {"accepted": False, "normalized_action": None, "reason": "unknown", "confidence": 0.5}
"""


def _make_result() -> SynthesisResult:
    """Create a minimal SynthesisResult for testing."""
    return SynthesisResult(
        iterations_completed=1,
        final_harness=None,
        best_score=0.75,
        history=[
            IterationRecord(
                iteration=0,
                harness_id="harness-expense-approval-v0-abc12345",
                composite_score=0.75,
                metrics={
                    "composite_score": 0.75,
                    "task_success_rate": 0.8,
                    "invalid_action_rate": 0.1,
                    "total_actions": 20,
                },
                promoted=True,
                num_counterexamples=3,
            )
        ],
    )


class TestMarkdownReport:
    def test_generates_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            result = _make_result()
            md = generate_markdown_report(result, registry, "expense-approval")
            assert "# AutoHarness" in md
            assert "expense-approval" in md
            assert "0.75" in md

    def test_saves_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            result = _make_result()
            path = save_markdown_report(
                result, registry, "expense-approval", Path(tmp) / "report.md"
            )
            assert path.exists()
            content = path.read_text()
            assert "# AutoHarness" in content


class TestHTMLReport:
    def test_generates_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            result = _make_result()
            html = generate_html_report(result, registry, "expense-approval")
            assert "<!DOCTYPE html>" in html
            assert "expense-approval" in html
            assert "0.75" in html
            assert "<style>" in html  # Self-contained

    def test_saves_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            result = _make_result()
            path = save_html_report(result, registry, "expense-approval", Path(tmp) / "report.html")
            assert path.exists()
            content = path.read_text()
            assert "<!DOCTYPE html>" in content


class TestCSVExporter:
    def test_generates_csv(self):
        result = _make_result()
        csv = generate_csv(result)
        assert "iteration" in csv
        assert "composite_score" in csv
        assert "0.750000" in csv
        assert "True" in csv

    def test_header_row(self):
        result = _make_result()
        csv = generate_csv(result)
        lines = csv.strip().split("\n")
        assert lines[0].startswith("iteration,")

    def test_saves_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _make_result()
            path = save_csv(result, Path(tmp) / "metrics.csv")
            assert path.exists()
            content = path.read_text()
            assert "iteration" in content


class TestDiffer:
    def test_diff_between_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            registry.store("expense-approval", VALID_CODE_A, "mock", "h1")
            registry.store("expense-approval", VALID_CODE_B, "mock", "h2")

            diff = diff_harness_versions(registry, "expense-approval", 0, 1)
            assert "---" in diff
            assert "+++" in diff
            assert "v0" in diff or "v1" in diff

    def test_diff_parent_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            parent = registry.store("expense-approval", VALID_CODE_A, "mock", "h1")
            child = registry.store(
                "expense-approval",
                VALID_CODE_B,
                "mock",
                "h2",
                parent_harness_id=parent.harness_id,
            )

            diff = diff_parent_child(registry, child.harness_id)
            assert "---" in diff
            assert "+++" in diff

    def test_diff_parent_child_no_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = HarnessRegistry(Path(tmp))
            artifact = registry.store("expense-approval", VALID_CODE_A, "mock", "h1")
            diff = diff_parent_child(registry, artifact.harness_id)
            assert "No parent" in diff

    def test_save_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_diff("test diff content", Path(tmp) / "diff.txt")
            assert path.exists()
            assert path.read_text() == "test diff content"
