"""Self-contained HTML report generation for synthesis experiments.

Produces a single HTML file with embedded CSS and JavaScript — no
external dependencies, no CDN links. Suitable for offline viewing
and archival.
"""

# ruff: noqa: E501 — CSS declarations are intentionally compact

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from autoharness_lab.harness.registry import HarnessRegistry
from autoharness_lab.synthesis.search import SynthesisResult


def generate_html_report(
    result: SynthesisResult,
    registry: HarnessRegistry,
    environment: str,
    title: str = "AutoHarness Synthesis Report",
) -> str:
    """Generate a self-contained HTML report.

    Args:
        result: SynthesisResult from a completed synthesis run.
        registry: HarnessRegistry containing the stored artifacts.
        environment: Environment name for context.
        title: Report title.

    Returns:
        Complete HTML string with embedded CSS.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{_css()}
</style>
</head>
<body>
<div class="container">
{_header_html(title, environment, result)}
{_summary_html(result)}
{_history_table_html(result)}
{_metrics_section_html(result)}
{_harness_code_html(result)}
</div>
</body>
</html>"""


def save_html_report(
    result: SynthesisResult,
    registry: HarnessRegistry,
    environment: str,
    output_path: Path,
    title: str = "AutoHarness Synthesis Report",
) -> Path:
    """Generate and save an HTML report to a file.

    Returns:
        The path to the saved file.
    """
    content = generate_html_report(result, registry, environment, title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path


# ── HTML Components ──────────────────────────────────────────────────


def _now() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _css() -> str:
    # ruff: noqa: E501 — CSS declarations are intentionally compact
    return """
:root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --text-dim: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --yellow: #d2991d;
    --magenta: #bc8cff;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; padding: 2rem; }
.container { max-width: 900px; margin: 0 auto; }
h1 { font-size: 1.8rem; color: var(--accent); margin-bottom: 0.5rem; }
h2 { font-size: 1.3rem; color: var(--text); margin: 2rem 0 0.75rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); }
h3 { font-size: 1.1rem; color: var(--text-dim); margin: 1.5rem 0 0.5rem; }
.meta { color: var(--text-dim); font-size: 0.9rem; margin-bottom: 1.5rem; }
.meta span { margin-right: 1.5rem; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin: 1rem 0; }
.summary-card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1rem; }
.summary-card .label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }
.summary-card .value { font-size: 1.4rem; font-weight: 600; margin-top: 0.25rem; }
.value.good { color: var(--green); }
.value.warn { color: var(--yellow); }
.value.bad { color: var(--red); }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }
th { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 2px solid var(--border); color: var(--text-dim); font-weight: 600; }
td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }
tr:hover { background: var(--surface); }
.promoted { color: var(--green); font-weight: 600; }
.not-promoted { color: var(--text-dim); }
.metric-table td:first-child { font-family: monospace; font-size: 0.85rem; }
pre { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.85rem; line-height: 1.5; }
code { font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; }
.mono { font-family: monospace; font-size: 0.85rem; color: var(--accent); }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
"""


def _header_html(title: str, environment: str, result: SynthesisResult) -> str:
    best = f"{result.best_score:.3f}" if result.best_score else "N/A"
    return f"""<h1>{title}</h1>
<div class="meta">
    <span>Environment: <strong>{environment}</strong></span>
    <span>Date: {_now()}</span>
    <span>Iterations: {result.iterations_completed}</span>
    <span>Best Score: <strong>{best}</strong></span>
</div>"""


def _summary_html(result: SynthesisResult) -> str:
    promotions = sum(1 for r in result.history if r.promoted)
    best = result.best_score or 0
    score_class = "good" if best > 0.5 else ("warn" if best > 0 else "bad")
    return f"""<h2>Summary</h2>
<div class="summary-grid">
    <div class="summary-card">
        <div class="label">Best Score</div>
        <div class="value {score_class}">{best:.3f}</div>
    </div>
    <div class="summary-card">
        <div class="label">Iterations</div>
        <div class="value">{result.iterations_completed}</div>
    </div>
    <div class="summary-card">
        <div class="label">Promotions</div>
        <div class="value">{promotions}</div>
    </div>
    <div class="summary-card">
        <div class="label">Final Harness</div>
        <div class="value" style="font-size:0.9rem;font-family:monospace;">{result.final_harness.harness_id[:20] if result.final_harness else "N/A"}...</div>
    </div>
</div>"""


def _history_table_html(result: SynthesisResult) -> str:
    rows = []
    for r in result.history:
        promoted_cell = (
            '<span class="promoted">✓</span>'
            if r.promoted
            else '<span class="not-promoted">-</span>'
        )
        rows.append(
            f"<tr><td>{r.iteration}</td>"
            f'<td><span class="mono">{r.harness_id[:16]}...</span></td>'
            f"<td>{r.composite_score:.3f}</td>"
            f"<td>{promoted_cell}</td>"
            f"<td>{r.num_counterexamples}</td></tr>"
        )
    return f"""<h2>Iteration History</h2>
<table>
<thead><tr><th>Iter</th><th>Harness ID</th><th>Score</th><th>Promoted</th><th>CEs</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>"""


def _metrics_section_html(result: SynthesisResult) -> str:
    if not result.history:
        return ""
    sections = []
    metric_order = [
        ("composite_score", "Composite Score"),
        ("task_success_rate", "Task Success"),
        ("invalid_action_rate", "Invalid Actions"),
        ("false_acceptance_rate", "False Acceptances"),
        ("false_rejection_rate", "False Rejections"),
        ("policy_denial_rate", "Policy Denials"),
        ("runtime_error_rate", "Runtime Errors"),
        ("total_actions", "Total Actions"),
    ]
    for record in result.history:
        if not record.metrics:
            continue
        rows = []
        for key, label in metric_order:
            if key in record.metrics:
                val = record.metrics[key]
                formatted = str(int(val)) if key == "total_actions" else f"{val:.4f}"
                rows.append(f"<tr><td>{label}</td><td>{formatted}</td></tr>")
        sections.append(
            f"<h3>Iteration {record.iteration} "
            f'&mdash; <span class="mono">{record.harness_id[:12]}...</span></h3>'
            f'<table class="metric-table"><tbody>{"".join(rows)}</tbody></table>'
        )
    heading = "<h2>Metrics Detail</h2>"
    body = "".join(sections)
    return f"{heading}{body}" if sections else ""


def _harness_code_html(result: SynthesisResult) -> str:
    if not result.final_harness:
        return ""
    code = _escape_html(result.final_harness.code)
    return f"""<hr>
<h2>Final Harness Code</h2>
<p class="meta">
    <span>ID: <span class="mono">{result.final_harness.harness_id}</span></span>
    <span>Hash: <span class="mono">{result.final_harness.code_hash}</span></span>
</p>
<pre><code>{code}</code></pre>"""


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
