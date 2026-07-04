"""Unit tests for the support-ticket environment."""

from autoharness_lab.environments.support_ticket import (
    SupportTicketConfig,
    SupportTicketEnvironment,
    TicketState,
)
from autoharness_lab.models import Action


class TestSupportTicketEnvironment:
    def test_name(self):
        env = SupportTicketEnvironment()
        assert env.name == "support-ticket"

    def test_reset_creates_tickets(self):
        env = SupportTicketEnvironment()
        obs = env.reset(42)
        assert "tickets" in obs
        tickets = obs["tickets"]
        assert len(tickets) == 3
        # Check first ticket
        tkt = tickets["tkt-0042"]
        assert tkt["state"] == "new"
        assert tkt["customer"] == "acme-corp"
        assert tkt["priority"] == "high"

    def test_available_action_types(self):
        env = SupportTicketEnvironment()
        actions = env.available_action_types()
        assert "assign_ticket" in actions
        assert "resolve_ticket" in actions

    def test_assign_new_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        action = Action(
            type="assign_ticket",
            arguments={"ticket_id": "tkt-0100", "assignee": "agent_bob"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert result.reward == 0.1
        tkt = env._tickets["tkt-0100"]
        assert tkt.state == TicketState.ASSIGNED
        assert tkt.assignee == "agent_bob"

    def test_assign_missing_ticket_id(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        action = Action(
            type="assign_ticket",
            arguments={"assignee": "agent_bob"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "MISSING_TICKET_ID"

    def test_assign_nonexistent_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        action = Action(
            type="assign_ticket",
            arguments={"ticket_id": "tkt-9999", "assignee": "agent_bob"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "TICKET_NOT_FOUND"

    def test_unknown_action_type(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        action = Action(type="invalid_action", arguments={})
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "UNKNOWN_ACTION"

    def test_resolve_assigned_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        # First assign
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        # Then resolve
        action = Action(
            type="resolve_ticket",
            arguments={"ticket_id": "tkt-0101", "resolution": "Fixed"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert result.reward == 0.5
        tkt = env._tickets["tkt-0101"]
        assert tkt.state == TicketState.RESOLVED

    def test_cannot_resolve_new_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        action = Action(
            type="resolve_ticket",
            arguments={"ticket_id": "tkt-0100"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "INVALID_STATE"

    def test_cannot_resolve_resolved_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        # Assign and resolve first
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        env.execute(
            Action(
                type="resolve_ticket",
                arguments={"ticket_id": "tkt-0101"},
            )
        )
        # Try again
        action = Action(type="resolve_ticket", arguments={"ticket_id": "tkt-0101"})
        result = env.execute(action)
        assert result.status == "invalid_action"

    def test_set_priority(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        # Assign first
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="set_priority",
            arguments={"ticket_id": "tkt-0101", "priority": "high"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert env._tickets["tkt-0101"].priority == "high"

    def test_set_priority_invalid_value(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="set_priority",
            arguments={"ticket_id": "tkt-0101", "priority": "extreme"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "INVALID_PRIORITY"

    def test_cannot_set_priority_resolved(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        env.execute(
            Action(type="resolve_ticket", arguments={"ticket_id": "tkt-0101"})
        )
        action = Action(
            type="set_priority",
            arguments={"ticket_id": "tkt-0101", "priority": "high"},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"

    def test_escalate_assigned_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="escalate_ticket",
            arguments={"ticket_id": "tkt-0101"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert result.reward == 0.2
        assert env._tickets["tkt-0101"].state == TicketState.ESCALATED

    def test_cannot_escalate_resolved(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        env.execute(
            Action(type="resolve_ticket", arguments={"ticket_id": "tkt-0101"})
        )
        action = Action(type="escalate_ticket", arguments={"ticket_id": "tkt-0101"})
        result = env.execute(action)
        assert result.status == "invalid_action"

    def test_refund_with_valid_amount(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="refund_customer",
            arguments={"ticket_id": "tkt-0101", "amount": 100.0},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert result.reward == 0.3
        assert env._tickets["tkt-0101"].refund_amount == 100.0

    def test_refund_above_limit_without_approval(self):
        env = SupportTicketEnvironment(config=SupportTicketConfig(refund_limit=200.0))
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="refund_customer",
            arguments={"ticket_id": "tkt-0101", "amount": 300.0},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "REFUND_OVER_LIMIT"

    def test_refund_invalid_amount(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        action = Action(
            type="refund_customer",
            arguments={"ticket_id": "tkt-0101", "amount": -50.0},
        )
        result = env.execute(action)
        assert result.status == "invalid_action"
        assert result.error_code == "INVALID_REFUND_AMOUNT"

    def test_reassign_escalated_ticket(self):
        env = SupportTicketEnvironment()
        env.reset(100)
        env.execute(
            Action(
                type="assign_ticket",
                arguments={"ticket_id": "tkt-0101", "assignee": "agent_bob"},
            )
        )
        env.execute(
            Action(type="escalate_ticket", arguments={"ticket_id": "tkt-0101"})
        )
        action = Action(
            type="assign_ticket",
            arguments={"ticket_id": "tkt-0101", "assignee": "agent_charlie"},
        )
        result = env.execute(action)
        assert result.status == "success"
        assert env._tickets["tkt-0101"].assignee == "agent_charlie"
