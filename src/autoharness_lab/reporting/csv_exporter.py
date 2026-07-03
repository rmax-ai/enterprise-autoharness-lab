"""CSV export for synthesis experiment metrics."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from autoharness_lab.synthesis.search import SynthesisResult

CSV_COLUMNS = [
    "iteration",
    "harness_id",
    "composite_score",
    "task_success_rate",
    "invalid_action_rate",
    "false_acceptance_rate",
    "false_rejection_rate",
    "policy_denial_rate",
    "runtime_error_rate",
    "total_actions",
    "promoted",
    "num_counterexamples",
]


def generate_csv(result: SynthesisResult) -> str:
    """Generate a CSV string from a synthesis result.

    Args:
        result: SynthesisResult with iteration history.

    Returns:
        CSV string with header row.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()

    for record in result.history:
        row: dict[str, Any] = {
            "iteration": record.iteration,
            "harness_id": record.harness_id,
            "composite_score": f"{record.composite_score:.6f}",
            "task_success_rate": "",
            "invalid_action_rate": "",
            "false_acceptance_rate": "",
            "false_rejection_rate": "",
            "policy_denial_rate": "",
            "runtime_error_rate": "",
            "total_actions": "",
            "promoted": str(record.promoted),
            "num_counterexamples": record.num_counterexamples,
        }
        for key in record.metrics:
            if key in CSV_COLUMNS:
                if key == "total_actions":
                    row[key] = str(int(record.metrics[key]))
                else:
                    row[key] = f"{record.metrics[key]:.6f}"
        writer.writerow(row)

    return output.getvalue()


def save_csv(result: SynthesisResult, output_path: Path) -> Path:
    """Generate and save a CSV file.

    Returns:
        The path to the saved file.
    """
    content = generate_csv(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path
