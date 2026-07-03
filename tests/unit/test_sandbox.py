"""Tests for harness sandbox execution."""

from autoharness_lab.harness.sandbox import SandboxExecutor, SandboxResult

VALID_HARNESS_CODE = """
def evaluate_action(observation, proposed_action):
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})

    if not args.get("expense_id"):
        return {"accepted": False, "normalized_action": None, "reason": "missing id", "confidence": 0.99}

    return {"accepted": True, "normalized_action": proposed_action, "reason": "ok", "confidence": 0.8}

def repair_action(observation, proposed_action, failure):
    return None
"""

HARNESS_WITH_IMPORT = """
import os

def evaluate_action(observation, proposed_action):
    os.system("echo test")
    return {"accepted": True, "normalized_action": None, "reason": "", "confidence": None}
"""

HARNESS_INFINITE_LOOP = """
def evaluate_action(observation, proposed_action):
    while True:
        pass
"""


class TestSandboxExecutor:
    def test_executes_valid_harness(self):
        executor = SandboxExecutor(VALID_HARNESS_CODE)
        result = executor.evaluate(
            {"expenses": {"e1": {"state": "draft"}}},
            {"type": "submit_expense", "arguments": {"expense_id": "e1"}},
        )
        assert result.accepted is True
        assert result.data is not None

    def test_rejects_missing_expense_id(self):
        executor = SandboxExecutor(VALID_HARNESS_CODE)
        result = executor.evaluate(
            {"expenses": {}},
            {"type": "submit_expense", "arguments": {}},
        )
        assert result.accepted is False

    def test_static_validation_blocks_import(self):
        executor = SandboxExecutor(HARNESS_WITH_IMPORT)
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None
        assert "import" in result.error.lower()

    def test_timeout_on_infinite_loop(self):
        executor = SandboxExecutor(HARNESS_INFINITE_LOOP, timeout=0.5)
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None
        assert "timed out" in result.error.lower()

    def test_handles_syntax_error(self):
        executor = SandboxExecutor("not valid python {{{")
        result = executor.evaluate({}, {"type": "x", "arguments": {}})
        assert result.accepted is False
        assert result.error is not None

    def test_calls_repair(self):
        code = """
def evaluate_action(observation, proposed_action):
    return {"accepted": True, "normalized_action": proposed_action, "reason": "", "confidence": 0.5}

def repair_action(observation, proposed_action, failure):
    return {"type": "submit_expense", "arguments": {"expense_id": "e1"}}
"""
        executor = SandboxExecutor(code)
        result = executor.repair(
            {"expenses": {}},
            {"type": "x", "arguments": {}},
            {"error_code": "MISSING_RECEIPT"},
        )
        assert result is not None
        assert result["type"] == "submit_expense"

    def test_evaluate_as_harness_returns_dict(self):
        """Verify evaluate_as_harness produces HarnessDecision-compatible dict."""
        executor = SandboxExecutor(VALID_HARNESS_CODE)
        result = executor.evaluate_as_harness(
            {"expenses": {"e1": {"state": "draft"}}},
            {"type": "submit_expense", "arguments": {"expense_id": "e1"}},
        )
        assert isinstance(result, dict)
        assert "accepted" in result
        assert result["accepted"] is True
        assert "normalized_action" in result
        assert "reason" in result
        assert "confidence" in result

    def test_evaluate_as_harness_on_error_returns_rejected(self):
        """Verify error conditions produce a rejected HarnessDecision dict, not an exception."""
        executor = SandboxExecutor(HARNESS_WITH_IMPORT)
        result = executor.evaluate_as_harness({}, {"type": "x", "arguments": {}})
        assert isinstance(result, dict)
        assert result["accepted"] is False
        assert result["reason"]


def test_sandbox_result_immutable():
    result = SandboxResult(
        accepted=True,
        data={"normalized_action": {"type": "x"}},
    )
    assert result.accepted is True
    assert result.data == {"normalized_action": {"type": "x"}}
    assert result.error is None
