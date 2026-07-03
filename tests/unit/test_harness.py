"""Unit tests for manual harness and harness contracts."""

# Import the manual harness module directly
import importlib.util
import sys
from pathlib import Path

import pytest

from autoharness_lab.harness.contracts import HarnessRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO_ROOT / "src/autoharness_lab/harness/manual/expense_approval.py"


@pytest.fixture
def manual_harness():
    spec = importlib.util.spec_from_file_location("manual_harness", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["manual_harness"] = module
    spec.loader.exec_module(module)
    return HarnessRuntime(module)


class TestManualHarness:
    def test_accepts_valid_submit(self, manual_harness):
        result = manual_harness.evaluate(
            observation={
                "expenses": {
                    "exp-1": {
                        "expense_id": "exp-1",
                        "amount": 30,
                        "state": "draft",
                        "has_receipt": False,
                        "submitter": "alice",
                    }
                }
            },
            proposed_action={
                "type": "submit_expense",
                "arguments": {"expense_id": "exp-1"},
            },
        )
        assert result["accepted"] is True
        assert result["normalized_action"] is not None

    def test_rejects_unknown_action(self, manual_harness):
        result = manual_harness.evaluate(
            observation={"expenses": {}},
            proposed_action={"type": "nonexistent", "arguments": {}},
        )
        assert result["accepted"] is False
        assert "Unknown action type" in result["reason"]

    def test_rejects_missing_expense_id(self, manual_harness):
        result = manual_harness.evaluate(
            observation={"expenses": {}},
            proposed_action={"type": "submit_expense", "arguments": {}},
        )
        assert result["accepted"] is False
        assert "Missing required field" in result["reason"]

    def test_rejects_invalid_state(self, manual_harness):
        """Cannot approve an expense in draft state."""
        result = manual_harness.evaluate(
            observation={
                "expenses": {
                    "exp-1": {
                        "expense_id": "exp-1",
                        "amount": 100,
                        "state": "draft",
                        "has_receipt": True,
                        "submitter": "alice",
                    }
                }
            },
            proposed_action={
                "type": "approve_expense",
                "arguments": {"expense_id": "exp-1"},
            },
        )
        assert result["accepted"] is False
        assert "draft" in result["reason"].lower()

    def test_rejects_self_approval(self, manual_harness):
        result = manual_harness.evaluate(
            observation={
                "expenses": {
                    "exp-1": {
                        "expense_id": "exp-1",
                        "amount": 100,
                        "state": "submitted",
                        "has_receipt": True,
                        "submitter": "alice",
                    }
                }
            },
            proposed_action={
                "type": "approve_expense",
                "arguments": {"expense_id": "exp-1", "actor": "alice"},
            },
        )
        assert result["accepted"] is False
        assert "Self-approval" in result["reason"]

    def test_rejects_unsupported_currency(self, manual_harness):
        result = manual_harness.evaluate(
            observation={
                "expenses": {
                    "exp-1": {
                        "expense_id": "exp-1",
                        "amount": 100,
                        "currency": "BTC",
                        "state": "draft",
                        "has_receipt": True,
                        "submitter": "alice",
                    }
                }
            },
            proposed_action={
                "type": "submit_expense",
                "arguments": {"expense_id": "exp-1"},
            },
        )
        assert result["accepted"] is False
        assert "Unsupported currency" in result["reason"]

    def test_normalizes_field_names(self, manual_harness):
        """Canonicalizes expenseId to expense_id."""
        result = manual_harness.evaluate(
            observation={
                "expenses": {
                    "exp-1": {
                        "expense_id": "exp-1",
                        "amount": 30,
                        "state": "draft",
                        "has_receipt": False,
                        "submitter": "alice",
                    }
                }
            },
            proposed_action={
                "type": "submit_expense",
                "arguments": {"expenseId": "exp-1"},  # CamelCase
            },
        )
        assert result["accepted"] is True
        assert result["normalized_action"]["arguments"]["expense_id"] == "exp-1"


class TestHarnessRuntime:
    def test_handles_harness_error_gracefully(self):
        """Runtime should not crash if harness throws."""
        import types

        module = types.ModuleType("broken")

        def broken_evaluate(obs, action):
            raise RuntimeError("harness crash")

        module.evaluate_action = broken_evaluate
        runtime = HarnessRuntime(module)

        result = runtime.evaluate({}, {"type": "test", "arguments": {}})
        assert result["accepted"] is False
        assert "Harness error" in result["reason"]
