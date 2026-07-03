"""Markdown report generation for synthesis experiments."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry
from autoharness_lab.synthesis.search import SynthesisResult


def generate_markdown_report(
    result: SynthesisResult,
    registry: HarnessRegistry,
    environment: str,
    title: str = "AutoHarness Synthesis Report",
) -> str:
    """Generate a markdown report from a synthesis result.

    Args:
        result: SynthesisResult from a completed synthesis run.
        registry: HarnessRegistry containing the stored artifacts.
        environment: Environment name for context.
        title: Report title.

    Returns:
        Markdown string.
    """
    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────────────
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Environment:** `{environment}`")
    lines.append(f"**Date:** {_now()}")
    lines.append(f"**Iterations:** {result.iterations_completed}")
    if result.best_score is not None:
        lines.append(f"**Best Composite Score:** {result.best_score:.3f}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Summary ─────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    if result.best_score is not None:
        lines.append(f"- **Best score achieved:** {result.best_score:.3f}")
    lines.append(f"- **Total iterations:** {result.iterations_completed}")
    lines.append(f"- **Promotions:** {sum(1 for r in result.history if r.promoted)}")
    if result.final_harness:
        lines.append(f"- **Final harness:** `{result.final_harness.harness_id}`")
        lines.append(f"- **Code hash:** `{result.final_harness.code_hash}`")
    lines.append("")

    # ── Iteration History ───────────────────────────────────────────
    lines.append("## Iteration History")
    lines.append("")
    lines.append("| Iter | Harness ID | Score | Promoted | CEs |")
    lines.append("|------|-----------|-------|----------|-----|")
    for record in result.history:
        promoted = "✓" if record.promoted else "-"
        lines.append(
            f"| {record.iteration} "
            f"| `{record.harness_id[:16]}...` "
            f"| {record.composite_score:.3f} "
            f"| {promoted} "
            f"| {record.num_counterexamples} |"
        )
    lines.append("")

    # ── Metrics Detail ──────────────────────────────────────────────
    lines.append("## Metrics Detail")
    lines.append("")
    for record in result.history:
        if record.metrics:
            lines.append(f"### Iteration {record.iteration} — `{record.harness_id[:12]}...`")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            metric_order = [
                "composite_score",
                "task_success_rate",
                "invalid_action_rate",
                "false_acceptance_rate",
                "false_rejection_rate",
                "policy_denial_rate",
                "runtime_error_rate",
                "total_actions",
            ]
            for key in metric_order:
                if key in record.metrics:
                    lines.append(f"| {key} | {record.metrics[key]:.4f} |")
            lines.append("")

    # ── Harness Code ────────────────────────────────────────────────
    if result.final_harness:
        lines.append("---")
        lines.append("")
        lines.append("## Final Harness Code")
        lines.append("")
        lines.append(f"**Harness ID:** `{result.final_harness.harness_id}`")
        lines.append(f"**Code hash:** `{result.final_harness.code_hash}`")
        lines.append("")
        lines.append("```python")
        lines.append(result.final_harness.code)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def save_markdown_report(
    result: SynthesisResult,
    registry: HarnessRegistry,
    environment: str,
    output_path: Path,
    title: str = "AutoHarness Synthesis Report",
) -> Path:
    """Generate and save a markdown report to a file.

    Returns:
        The path to the saved file.
    """
    content = generate_markdown_report(result, registry, environment, title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path


def _now() -> str:
    """Return current timestamp as ISO string."""
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
