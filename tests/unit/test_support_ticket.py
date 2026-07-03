"""Tests for support-ticket environment and policy."""

import pytest

from autoharness_lab.environments.support_ticket import (
    SupportTicketEnvironment,
    TicketPriority,
    TicketState,
)
from autoharness_lab.models import Action
from autoharness_lab.policy.support import SupportTicketPolicyEngine


@pytest.fixture
def env():
    e = SupportTicketEnvironment()
    e.reset(42)
    return e


class TestSupportTicketEnvironment:
    def test_name(self, env):
        assert env.name == "support-ticket"

    def test_reset_creates_tickets(self, env):
        snap = env.state_snapshot()
        assert len(snap["tickets"]) == 4

    def test_available_actions(self, env):
        actions = env.available_action_types()
        assert "assign_ticket" in actions
        assert "resolve_ticket" in actions

    def test_assign_new_ticket(self, env):
        result = env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0042", "assignee": "agent_neo"},
            )
        )
        assert result.status == "success"

    def test_assign_without_id_fails(self, env):
        result = env.execute(Action(type="assign_ticket", arguments={"assignee": "agent_neo"}))
        assert result.status == "invalid_action"
        assert result.error_code == "MISSING_TICKET_ID"

    def test_set_priority(self, env):
        result = env.execute(
            Action(
                type="set_priority",
                arguments={"ticket_id": "tkt-0042", "priority": "critical"},
            )
        )
        assert result.status == "success"

    def test_invalid_priority(self, env):
        result = env.execute(
            Action(
                type="set_priority",
                arguments={"ticket_id": "tkt-0042", "priority": "super-high"},
            )
        )
        assert result.status == "invalid_action"
        assert result.error_code == "INVALID_PRIORITY"

    def test_add_note(self, env):
        result = env.execute(
            Action(
                type="add_note",
                arguments={"ticket_id": "tkt-0043", "note": "Investigating"},
            )
        )
        assert result.status == "success"

    def test_resolve_in_progress(self, env):
        result = env.execute(
            Action(
                type="resolve_ticket",
                arguments={"ticket_id": "tkt-0044"},
            )
        )
        assert result.status == "success"

    def test_unknown_action(self, env):
        result = env.execute(Action(type="invalid_action_xyz", arguments={}))
        assert result.status == "invalid_action"

    def test_state_snapshot(self, env):
        snap = env.state_snapshot()
        assert "tickets" in snap
        assert "config" in snap


class TestSupportTicketPolicy:
    def test_agent_can_resolve_own_ticket(self):
        eng = SupportTicketPolicyEngine()
        result = eng.evaluate(
            {"user_id": "agent_neo", "role": "agent"},
            {"type": "resolve_ticket", "arguments": {}},
            {"assignee": "agent_neo", "state": "in_progress"},
        )
        assert result.allowed

    def test_agent_cannot_escalate(self):
        eng = SupportTicketPolicyEngine()
        result = eng.evaluate(
            {"user_id": "agent_neo", "role": "agent"},
            {"type": "escalate_ticket", "arguments": {}},
            {"state": "in_progress"},
        )
        assert not result.allowed
        assert result.rule_id == "ESC-003"

    def test_non_agent_blocked(self):
        eng = SupportTicketPolicyEngine()
        result = eng.evaluate(
            {"user_id": "guest", "role": "customer"},
            {"type": "add_note", "arguments": {}},
            None,
        )
        assert not result.allowed
        assert result.rule_id == "ESC-001"
