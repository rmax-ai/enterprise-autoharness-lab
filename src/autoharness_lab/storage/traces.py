"""Trace recording and counterexample extraction.

Stores execution traces as JSONL and extracts structured counterexamples
from failed attempts for harness synthesis.
"""

from __future__ import annotations

from pathlib import Path

from autoharness_lab.models import (
    AttemptRecord,
    Counterexample,
    ExecutionResult,
    FailureClass,
)


def classify_failure(result: ExecutionResult) -> FailureClass:
    """Classify an execution failure into a failure category."""
    status = result.status
    error_code = result.error_code or ""

    if status == "invalid_action":
        if error_code == "UNKNOWN_ACTION":
            return "unknown_action_type"
        if error_code == "MISSING_EXPENSE_ID":
            return "malformed_action"
        if error_code == "INVALID_STATE":
            return "invalid_state_transition"
        if error_code == "MISSING_RECEIPT":
            return "missing_required_data"
        return "malformed_action"

    if status == "policy_denied":
        return "policy_denial"

    if status == "runtime_error":
        return "execution_error"

    return "unrecoverable_task_failure"


def extract_counterexamples(records: list[AttemptRecord]) -> list[Counterexample]:
    """Extract structured counterexamples from failed attempts.

    Only extracts from non-successful records (invalid_action, policy_denied,
    runtime_error).
    """
    counterexamples: list[Counterexample] = []

    for record in records:
        result = record.execution_result
        if result.status == "success":
            continue

        failure_class = classify_failure(result)

        # Determine expected classification based on what went wrong
        expected = "rejected"
        if failure_class in ("malformed_action", "unknown_action_type", "missing_required_data"):
            expected = "rejected"
        elif failure_class == "policy_denial":
            expected = "policy_denied"
        elif failure_class == "invalid_state_transition":
            expected = "rejected"

        counterexamples.append(
            Counterexample(
                observation=record.observation,
                proposed_action=record.proposed_action,
                expected_classification=expected,
                actual_result=result,
                error_code=result.error_code,
                explanation=(
                    f"Agent proposed {record.proposed_action.type} but "
                    f"resulted in {result.status}: {result.message}"
                ),
            )
        )

    return counterexamples


class TraceStore:
    """Append-only JSONL trace storage."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: AttemptRecord) -> None:
        """Append a single AttemptRecord as a JSONL line."""
        with open(self.path, "a") as f:
            f.write(record.model_dump_json() + "\n")

    def append_all(self, records: list[AttemptRecord]) -> None:
        """Append multiple records."""
        with open(self.path, "a") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")

    def load_all(self) -> list[AttemptRecord]:
        """Load all records from the trace file."""
        if not self.path.exists():
            return []
        records = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(AttemptRecord.model_validate_json(line))
        return records
