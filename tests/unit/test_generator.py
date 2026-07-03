"""Tests for harness code generator."""

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.synthesis.generator import GeneratorResponse, HarnessGenerator


VALID_CODE = '''
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    if action_type == "submit_expense":
        return {"accepted": True, "normalized_action": proposed_action, "reason": "valid", "confidence": 0.9}
    return {"accepted": False, "normalized_action": None, "reason": "unknown", "confidence": 0.5}
'''


class TestHarnessGenerator:
    def test_generates_from_spec(self):
        mock = MockModelClient.with_static(GeneratorResponse(code=VALID_CODE))
        generator = HarnessGenerator(mock)

        spec = {
            "name": "expense-approval",
            "supported_actions": ["submit_expense", "approve_expense"],
            "state_transitions": {
                "draft": ["submitted"],
                "submitted": ["approved", "rejected"],
            },
            "validation_rules": [
                "Cannot approve own expense",
                "Cannot approve already approved expense",
            ],
        }

        result = generator.generate(spec)
        assert result.code == VALID_CODE
        assert result.environment == "expense-approval"
        assert result.harness_id is not None

    def test_includes_code_hash(self):
        mock = MockModelClient.with_static(GeneratorResponse(code=VALID_CODE))
        generator = HarnessGenerator(mock)

        result = generator.generate(
            {
                "name": "expense-approval",
                "supported_actions": ["submit"],
                "state_transitions": {},
                "validation_rules": [],
            }
        )
        assert result.code_hash is not None
        assert len(result.code_hash) > 0


def test_generator_response_schema():
    resp = GeneratorResponse(code="def foo(): pass")
    assert resp.code == "def foo(): pass"
