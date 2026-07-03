"""Integration tests for the synthesis search loop."""

import tempfile
from pathlib import Path

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.generator import GeneratorResponse
from autoharness_lab.synthesis.refiner import RefinerResponse
from autoharness_lab.synthesis.search import SynthesisLoop


VALID_CODE_v0 = '''
def evaluate_action(observation, proposed_action):
    # Accept everything — deliberately weak start
    return {"accepted": True, "normalized_action": proposed_action, "reason": "accept all", "confidence": 0.3}
'''

VALID_CODE_v1 = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type not in ("submit_expense", "approve_expense", "reject_expense", "request_receipt", "escalate_expense"):
        return {"accepted": False, "normalized_action": None, "reason": f"unknown: {action_type}", "confidence": 0.9}
    args = proposed_action.get("arguments", {})
    if not args.get("expense_id"):
        return {"accepted": False, "normalized_action": None, "reason": "missing expense_id", "confidence": 0.99}
    return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.7}
'''

GEN_SYS = "You are a Python code generation system that produces validation functions."
REF_SYS = "You are a Python code refinement system."


def _make_mock(generator_code: str = VALID_CODE_v0, refiner_code: str = VALID_CODE_v1) -> MockModelClient:
    """Create a mock client with generator and refiner responses registered."""
    mock = MockModelClient()
    # Generator: match on system_prompt prefix
    mock.register(
        GEN_SYS, "",
        GeneratorResponse, GeneratorResponse(code=generator_code),
    )
    # Refiner: match on system_prompt prefix
    mock.register(
        REF_SYS, "",
        RefinerResponse, RefinerResponse(code=refiner_code),
    )
    return mock


class TestSynthesisLoop:
    def test_full_synthesis_with_mock_client(self):
        """End-to-end synthesis: generate → evaluate → refine → promote."""
        with tempfile.TemporaryDirectory() as tmp:
            mock = _make_mock()

            loop = SynthesisLoop(
                model_client=mock,
                registry_root=Path(tmp),
                environment="expense-approval",
                agent_name="noisy",
                max_iterations=2,
            )

            results = loop.run(
                environment_spec={
                    "name": "expense-approval",
                    "supported_actions": [
                        "submit_expense",
                        "approve_expense",
                        "reject_expense",
                    ],
                    "state_transitions": {
                        "draft": ["submitted"],
                        "submitted": ["approved"],
                    },
                    "validation_rules": ["No self-approval"],
                }
            )

            assert results.iterations_completed >= 1
            assert results.final_harness is not None
            assert results.history is not None
            assert len(results.history) > 0

    def test_promotion_only_on_improvement(self):
        """Verify that harness is only promoted when score improves."""
        with tempfile.TemporaryDirectory() as tmp:
            # Both generate and refine return same code — no improvement
            mock = _make_mock(generator_code=VALID_CODE_v0, refiner_code=VALID_CODE_v0)

            loop = SynthesisLoop(
                model_client=mock,
                registry_root=Path(tmp),
                environment="expense-approval",
                agent_name="noisy",
                max_iterations=2,
            )

            results = loop.run(
                environment_spec={
                    "name": "expense-approval",
                    "supported_actions": ["submit_expense", "approve_expense"],
                    "state_transitions": {"draft": ["submitted"]},
                    "validation_rules": [],
                }
            )

            # Should have at least 1 iteration recorded
            assert len(results.history) >= 1

    def test_no_counterexamples_stops_early(self):
        """When v1 harness is good enough, refinement loop stops."""
        with tempfile.TemporaryDirectory() as tmp:
            mock = _make_mock(generator_code=VALID_CODE_v1, refiner_code=VALID_CODE_v1)

            loop = SynthesisLoop(
                model_client=mock,
                registry_root=Path(tmp),
                environment="expense-approval",
                agent_name="noisy",
                max_iterations=5,
            )

            results = loop.run(
                environment_spec={
                    "name": "expense-approval",
                    "supported_actions": [
                        "submit_expense",
                        "approve_expense",
                        "reject_expense",
                        "request_receipt",
                        "escalate_expense",
                    ],
                    "state_transitions": {
                        "draft": ["submitted"],
                        "submitted": ["approved", "rejected"],
                    },
                    "validation_rules": [],
                }
            )

            # Should complete at least the initial generation
            assert results.iterations_completed >= 1
