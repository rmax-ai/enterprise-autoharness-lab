"""Unit tests for expense-approval environment state machine."""

import pytest

from autoharness_lab.environments.expense_approval import (
    ExpenseApprovalConfig,
    ExpenseApprovalEnvironment,
)
from autoharness_lab.models import Action


@pytest.fixture
def env():
    return ExpenseApprovalEnvironment()


def test_reset_creates_expenses(env):
    obs = env.reset(42)
    assert "expenses" in obs
    assert len(obs["expenses"]) == 3


def test_available_actions(env):
    actions = env.available_action_types()
    assert "submit_expense" in actions
    assert "approve_expense" in actions
    assert "reject_expense" in actions


def test_state_snapshot(env):
    env.reset(42)
    snap = env.state_snapshot()
    assert "config" in snap
    assert "expenses" in snap


def test_submit_draft_expense(env):
    env.reset(42)
    # Find a draft expense and add receipt
    obs = env.state_snapshot()
    draft = None
    for eid, e in obs["expenses"].items():
        if e["state"] == "draft":
            draft = eid
            # Add receipt if amount > 50
            if e["amount"] > 50:
                env.execute(Action(type="request_receipt", arguments={"expense_id": eid}))
            break
    assert draft is not None

    result = env.execute(
        Action(type="submit_expense", arguments={"expense_id": draft})
    )
    assert result.status == "success"
    obs = env.state_snapshot()
    assert obs["expenses"][draft]["state"] == "submitted"


def test_submit_without_receipt_fails(env):
    env.reset(42)
    obs = env.state_snapshot()
    # Find a draft with amount > threshold and no receipt
    draft = None
    for eid, e in obs["expenses"].items():
        if e["state"] == "draft" and e["amount"] > 50 and not e["has_receipt"]:
            draft = eid
            break

    if draft:
        result = env.execute(
            Action(type="submit_expense", arguments={"expense_id": draft})
        )
        assert result.status == "invalid_action"
        assert result.error_code == "MISSING_RECEIPT"


def test_cannot_submit_already_submitted(env):
    env.reset(42)
    obs = env.state_snapshot()
    submitted = next(
        (eid for eid, e in obs["expenses"].items() if e["state"] == "submitted"),
        None,
    )
    assert submitted is not None

    result = env.execute(
        Action(type="submit_expense", arguments={"expense_id": submitted})
    )
    assert result.status == "invalid_action"
    assert result.error_code == "INVALID_STATE"


def test_approve_submitted(env):
    env.reset(42)
    obs = env.state_snapshot()
    submitted = next(
        (eid for eid, e in obs["expenses"].items() if e["state"] == "submitted"),
        None,
    )
    assert submitted is not None

    result = env.execute(
        Action(type="approve_expense", arguments={"expense_id": submitted, "actor": "manager1"})
    )
    assert result.status == "success"
    obs = env.state_snapshot()
    assert obs["expenses"][submitted]["state"] == "approved"


def test_invalid_action_type(env):
    result = env.execute(Action(type="nonexistent_action", arguments={}))
    assert result.status == "invalid_action"
    assert result.error_code == "UNKNOWN_ACTION"


def test_missing_expense_id(env):
    result = env.execute(Action(type="submit_expense", arguments={}))
    assert result.status == "invalid_action"
    assert result.error_code == "MISSING_EXPENSE_ID"


def test_unsupported_currency(env):
    env.reset(42)
    obs = env.state_snapshot()
    # The expenses from reset(42) all have EUR or USD
    # Test by checking config
    snap = env.state_snapshot()
    assert "EUR" in snap["config"]["supported_currencies"]
    assert "BTC" not in snap["config"]["supported_currencies"]


def test_cannot_approve_draft(env):
    env.reset(42)
    obs = env.state_snapshot()
    draft = next(
        (eid for eid, e in obs["expenses"].items() if e["state"] == "draft"),
        None,
    )
    assert draft is not None

    result = env.execute(
        Action(type="approve_expense", arguments={"expense_id": draft, "actor": "manager1"})
    )
    assert result.status == "invalid_action"
    assert result.error_code == "INVALID_STATE"


def test_reject_expense(env):
    env.reset(42)
    obs = env.state_snapshot()
    submitted = next(
        (eid for eid, e in obs["expenses"].items() if e["state"] == "submitted"),
        None,
    )
    assert submitted is not None

    result = env.execute(
        Action(type="reject_expense", arguments={"expense_id": submitted, "actor": "manager1"})
    )
    assert result.status == "success"
    obs = env.state_snapshot()
    assert obs["expenses"][submitted]["state"] == "rejected"


def test_escalate_submitted(env):
    env.reset(42)
    obs = env.state_snapshot()
    submitted = next(
        (eid for eid, e in obs["expenses"].items() if e["state"] == "submitted"),
        None,
    )
    assert submitted is not None

    result = env.execute(
        Action(type="escalate_expense", arguments={"expense_id": submitted, "actor": "manager1"})
    )
    assert result.status == "success"
    obs = env.state_snapshot()
    assert obs["expenses"][submitted]["state"] == "escalated"
