"""Tests for mutation engine and drift experiments."""

import tempfile
from pathlib import Path

from autoharness_lab.environments.deployment import DeploymentConfig
from autoharness_lab.environments.expense_approval import ExpenseApprovalConfig
from autoharness_lab.environments.support_ticket import SupportTicketConfig
from autoharness_lab.evaluation.mutations import (
    apply_mutation,
    get_mutation,
    get_mutations,
    MutationResult,
)


class TestMutationCatalog:
    def test_expense_mutations_exist(self):
        mutations = get_mutations("expense-approval")
        assert len(mutations) >= 3
        ids = {m.mutation_id for m in mutations}
        assert "expense-threshold-halved" in ids

    def test_support_mutations_exist(self):
        mutations = get_mutations("support-ticket")
        assert len(mutations) >= 2

    def test_deployment_mutations_exist(self):
        mutations = get_mutations("deployment")
        assert len(mutations) >= 2

    def test_get_specific_mutation(self):
        m = get_mutation("expense-approval", "expense-threshold-halved")
        assert m is not None
        assert m.mutation_id == "expense-threshold-halved"
        assert m.config_changes["approval_threshold"] == 500.0

    def test_get_nonexistent_mutation(self):
        m = get_mutation("expense-approval", "nonexistent")
        assert m is None


class TestApplyMutation:
    def test_expense_threshold_change(self):
        base = ExpenseApprovalConfig(approval_threshold=1000.0)
        mutated = apply_mutation("expense-approval", base, {"approval_threshold": 500.0})
        assert mutated.approval_threshold == 500.0
        assert mutated.receipt_threshold == 50.0  # Unchanged

    def test_expense_self_approval(self):
        base = ExpenseApprovalConfig(allow_self_approval=False)
        mutated = apply_mutation("expense-approval", base, {"allow_self_approval": True})
        assert mutated.allow_self_approval is True

    def test_support_refund_limit(self):
        base = SupportTicketConfig(refund_limit=500.0)
        mutated = apply_mutation("support-ticket", base, {"refund_limit": 100.0})
        assert mutated.refund_limit == 100.0

    def test_deployment_freeze(self):
        base = DeploymentConfig(production_freeze=False)
        mutated = apply_mutation("deployment", base, {"production_freeze": True})
        assert mutated.production_freeze is True

    def test_deployment_rollback_limit(self):
        base = DeploymentConfig(max_rollback_count=3)
        mutated = apply_mutation("deployment", base, {"max_rollback_count": 1})
        assert mutated.max_rollback_count == 1


class TestMutationResult:
    def test_mutation_result_fields(self):
        result = MutationResult(
            mutation_id="test",
            environment="expense-approval",
            description="test mutation",
            baseline_score=0.8,
            baseline_metrics={"composite_score": 0.8},
            degraded_score=0.4,
            degraded_metrics={"composite_score": 0.4},
            score_drop=0.4,
        )
        assert result.mutation_id == "test"
        assert result.score_drop == 0.4
        assert result.recovered is False

    def test_mutation_result_recovered(self):
        result = MutationResult(
            mutation_id="test",
            environment="expense-approval",
            description="test",
            baseline_score=0.8,
            baseline_metrics={"composite_score": 0.8},
            degraded_score=0.4,
            degraded_metrics={"composite_score": 0.4},
            score_drop=0.4,
            recovered_score=0.75,
            recovered_metrics={"composite_score": 0.75},
            recovery_delta=0.35,
            counterexamples_needed=5,
            iterations_to_recover=2,
            recovered=True,
        )
        assert result.recovered is True
        assert result.recovery_delta == 0.35
        assert result.counterexamples_needed == 5


class TestDriftExperiment:
    def test_run_drift_expense(self):
        """Full drift experiment on expense-approval with threshold change."""
        from autoharness_lab.evaluation.drift import run_drift_experiment
        from autoharness_lab.model_clients.mock import MockModelClient
        from autoharness_lab.synthesis.generator import GeneratorResponse
        from autoharness_lab.synthesis.refiner import RefinerResponse

        harness_code = """
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})
    if not args.get("expense_id"):
        return {"accepted": False, "normalized_action": None, "reason": "missing id", "confidence": 0.99}
    if action_type in ("submit_expense", "approve_expense", "reject_expense", "request_receipt", "escalate_expense"):
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.7}
    return {"accepted": False, "normalized_action": None, "reason": "unknown", "confidence": 0.5}
"""

        GEN_SYS = "You are a Python code generation system that produces validation functions."
        mock = MockModelClient()
        mock.register(
            GEN_SYS,
            "",
            GeneratorResponse,
            GeneratorResponse(code=harness_code),
        )
        REF_SYS = "You are a Python code refinement system."
        mock.register(
            REF_SYS,
            "",
            RefinerResponse,
            RefinerResponse(code=harness_code),
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_drift_experiment(
                environment="expense-approval",
                mutation_id="expense-threshold-halved",
                registry_root=Path(tmp),
                model_client=mock,
                agent_name="noisy",
                seed=42,
                max_iterations=2,
            )
            assert result.environment == "expense-approval"
            assert result.mutation_id == "expense-threshold-halved"
            assert result.baseline_score is not None
            assert result.degraded_score is not None
            assert result.score_drop is not None
