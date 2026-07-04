"""Unit tests for metrics."""

from autoharness_lab.evaluation.runner import (
    compute_composite_score,
    compute_false_acceptance_rate,
    compute_invalid_action_rate,
    compute_task_success_rate,
)
from autoharness_lab.models import (
    Action,
    AttemptRecord,
    ExecutionResult,
    HarnessDecision,
)


def _record(status, harness_accepted=None, scenario_id="s1", **kwargs):
    """Helper to create test records."""
    hd = None
    if harness_accepted is not None:
        hd = HarnessDecision(accepted=harness_accepted, reason="test")
    return AttemptRecord(
        run_id="test",
        scenario_id=scenario_id,
        environment="expense-approval",
        agent="test",
        observation={},
        proposed_action=Action(type="test"),
        harness_decision=hd,
        execution_result=ExecutionResult(status=status, observation={}),
        step_index=0,
        **kwargs,
    )


class TestTaskSuccessRate:
    def test_all_success(self):
        records = [_record("success", scenario_id="s1")]
        assert compute_task_success_rate(records) == 1.0

    def test_all_fail(self):
        records = [_record("invalid_action", scenario_id="s1")]
        assert compute_task_success_rate(records) == 0.0

    def test_mixed(self):
        records = [
            _record("invalid_action", scenario_id="s1"),
            _record("invalid_action", scenario_id="s1"),
            _record("success", scenario_id="s1"),
        ]
        # Last record is success → scenario counts as success
        assert compute_task_success_rate(records) == 1.0

    def test_empty(self):
        assert compute_task_success_rate([]) == 0.0


class TestInvalidActionRate:
    def test_all_invalid(self):
        records = [
            _record("invalid_action"),
            _record("invalid_action"),
        ]
        assert compute_invalid_action_rate(records) == 1.0

    def test_half_invalid(self):
        records = [
            _record("invalid_action"),
            _record("success"),
        ]
        assert compute_invalid_action_rate(records) == 0.5


class TestCompositeScore:
    def test_perfect_score(self):
        records = [_record("success")]
        score = compute_composite_score(records)
        assert score > 0.0

    def test_all_fail_poor_score(self):
        records = [_record("invalid_action") for _ in range(10)]
        score = compute_composite_score(records)
        assert score < 0.0

    def test_reject_all_harness_scores_poorly(self):
        """A harness that rejects every action must score poorly."""
        records = []
        for _i in range(5):
            records.append(_record("success", harness_accepted=False))
        # All actions would have succeeded but harness rejected them
        # Composite score should be poor due to false_rejection penalty
        score = compute_composite_score(records)
        assert score < 0.5  # Should be penalized heavily


class TestFalseAcceptanceRate:
    def test_all_false_acceptances(self):
        records = [
            _record("invalid_action", harness_accepted=True),
            _record("invalid_action", harness_accepted=True),
        ]
        assert compute_false_acceptance_rate(records) == 1.0

    def test_no_false_acceptances(self):
        records = [
            _record("success", harness_accepted=True),
            _record("success", harness_accepted=True),
        ]
        assert compute_false_acceptance_rate(records) == 0.0
