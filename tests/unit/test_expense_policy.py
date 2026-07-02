"""Unit tests for expense-approval policy engine."""

import pytest

from autoharness_lab.policy.expense import ExpensePolicyEngine


@pytest.fixture
def policy():
    return ExpensePolicyEngine()


class TestPolicyEngine:
    def test_self_approval_denied(self, policy):
        """Employee cannot approve their own expense."""
        decision = policy.evaluate(
            actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-001"

    def test_self_approval_different_user_allowed(self, policy):
        """Different user can approve."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is True

    def test_already_approved_denied(self, policy):
        """Cannot approve an already-approved expense."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "approved",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-005"

    def test_rejected_cannot_approve(self, policy):
        """Rejected expense cannot be re-approved."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "rejected",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-006"

    def test_above_threshold_needs_manager(self, policy):
        """Expense above threshold requires manager role."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 2000,  # Above 1000 threshold
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-002"

    def test_above_threshold_manager_allowed(self, policy):
        """Manager can approve expense above threshold."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "manager", "approval_limit": 10000},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 2000,
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is True

    def test_above_manager_limit_denied(self, policy):
        """Manager cannot approve above their personal limit."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "manager", "approval_limit": 5000},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 6000,
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-002"

    def test_missing_receipt_denied(self, policy):
        """Large expense without receipt is denied."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "submitted",
                "has_receipt": False,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-003"

    def test_small_expense_no_receipt_allowed(self, policy):
        """Small expense (< 50) allowed without receipt."""
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "employee", "approval_limit": 0},
            action={"type": "approve_expense"},
            expense={
                "submitter": "alice",
                "amount": 30,
                "state": "submitted",
                "has_receipt": False,
            },
        )
        assert decision.allowed is True

    def test_non_approve_actions_pass(self, policy):
        """Submit actions don't need approval checks."""
        decision = policy.evaluate(
            actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
            action={"type": "submit_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "draft",
                "has_receipt": True,
                "currency": "EUR",
            },
        )
        assert decision.allowed is True

    def test_unsupported_currency_denied_on_submit(self, policy):
        """Unsupported currency denied on submit."""
        decision = policy.evaluate(
            actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
            action={"type": "submit_expense"},
            expense={
                "submitter": "alice",
                "amount": 100,
                "state": "draft",
                "has_receipt": True,
                "currency": "BTC",
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-004"

    def test_harness_acceptance_not_policy_authorization(self, policy):
        """Key invariant: harness acceptance never implies policy authorization.

        Even when a harness would accept an action for operational validity,
        the policy engine independently enforces business rules.
        """
        # A manager trying to self-approve — operationally valid (submitted state,
        # has receipt, manager role) but policy should deny
        decision = policy.evaluate(
            actor={"user_id": "bob", "role": "manager", "approval_limit": 10000},
            action={"type": "approve_expense"},
            expense={
                "submitter": "bob",  # Self-approval
                "amount": 2000,
                "state": "submitted",
                "has_receipt": True,
            },
        )
        assert decision.allowed is False
        assert decision.rule_id == "EXP-001"  # Self-approval rule
