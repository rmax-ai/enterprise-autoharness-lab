"""Tests for harness refiner."""

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.refiner import HarnessRefiner, RefinerResponse


ORIGINAL_CODE = '''
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": proposed_action, "reason": "accept all", "confidence": 0.5}
'''

IMPROVED_CODE = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.9}
    return {"accepted": False, "normalized_action": None, "reason": "reject unknown", "confidence": 0.5}
'''


class TestHarnessRefiner:
    def test_refines_from_counterexamples(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        counterexamples = [
            {
                "observation": {"expenses": {}},
                "proposed_action": {"type": "invalid_action", "arguments": {}},
                "expected_classification": "rejected",
                "actual_result": {"status": "invalid_action"},
                "explanation": "Unknown action type should be rejected",
            }
        ]

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=counterexamples,
            environment="expense-approval",
        )
        assert result.code == IMPROVED_CODE
        assert result.code_hash is not None

    def test_parent_tracking(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=[],
            environment="expense-approval",
            parent_harness_id="harness-expense-approval-v0-abc12345",
        )
        assert result.parent_harness_id == "harness-expense-approval-v0-abc12345"

    def test_code_hash_changes_on_refinement(self):
        mock = MockModelClient.with_static(RefinerResponse(code=IMPROVED_CODE))
        refiner = HarnessRefiner(mock)

        result = refiner.refine(
            current_code=ORIGINAL_CODE,
            counterexamples=[],
            environment="expense-approval",
        )
        import hashlib

        original_hash = hashlib.sha256(ORIGINAL_CODE.encode()).hexdigest()[:16]
        assert result.code_hash != original_hash
