"""Unit tests for the support-ticket policy engine."""

from autoharness_lab.policy.support import SupportPolicyEngine


class TestSupportPolicyEngine:
    def test_allows_agent_assign_to_other(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "assign_ticket",
                "arguments": {"ticket_id": "tkt-0001", "assignee": "agent_charlie"},
            },
            ticket={"state": "new", "assignee": None},
        )
        assert result.allowed is True

    def test_blocks_self_assignment(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "assign_ticket",
                "arguments": {"ticket_id": "tkt-0001", "assignee": "agent_bob"},
            },
            ticket={"state": "new", "assignee": None},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-001"

    def test_blocks_assign_to_closed_ticket(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "assign_ticket",
                "arguments": {"ticket_id": "tkt-0001", "assignee": "agent_charlie"},
            },
            ticket={"state": "closed"},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-006"

    def test_blocks_unauthorized_refund(self):
        engine = SupportPolicyEngine(require_manager_for_refund=True)
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "refund_customer",
                "arguments": {"ticket_id": "tkt-0001", "amount": 100.0},
            },
            ticket={"state": "assigned", "refund_approved": False},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-003"

    def test_allows_manager_refund(self):
        engine = SupportPolicyEngine(require_manager_for_refund=True)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "refund_customer",
                "arguments": {"ticket_id": "tkt-0001", "amount": 100.0},
            },
            ticket={"state": "assigned", "refund_approved": False},
        )
        assert result.allowed is True

    def test_blocks_refund_above_limit_without_approval(self):
        engine = SupportPolicyEngine(refund_limit=200.0)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "refund_customer",
                "arguments": {"ticket_id": "tkt-0001", "amount": 300.0},
            },
            ticket={"state": "assigned", "refund_approved": False},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-002"

    def test_allows_refund_above_limit_with_approval(self):
        engine = SupportPolicyEngine(refund_limit=200.0)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "refund_customer",
                "arguments": {"ticket_id": "tkt-0001", "amount": 300.0},
            },
            ticket={"state": "assigned", "refund_approved": True},
        )
        assert result.allowed is True

    def test_blocks_resolve_resolved_ticket(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "resolve_ticket",
                "arguments": {"ticket_id": "tkt-0001"},
            },
            ticket={"state": "resolved", "assignee": "agent_bob"},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-005"

    def test_blocks_resolve_closed_ticket(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "resolve_ticket",
                "arguments": {"ticket_id": "tkt-0001"},
            },
            ticket={"state": "closed"},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-005"

    def test_blocks_agent_resolve_critical(self):
        engine = SupportPolicyEngine(require_manager_for_critical=True)
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "resolve_ticket",
                "arguments": {"ticket_id": "tkt-0001"},
            },
            ticket={"state": "assigned", "priority": "critical"},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-004"

    def test_allows_manager_resolve_critical(self):
        engine = SupportPolicyEngine(require_manager_for_critical=True)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "resolve_ticket",
                "arguments": {"ticket_id": "tkt-0001"},
            },
            ticket={"state": "assigned", "priority": "critical"},
        )
        assert result.allowed is True

    def test_blocks_agent_set_priority_to_critical(self):
        engine = SupportPolicyEngine(require_manager_for_critical=True)
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "set_priority",
                "arguments": {"ticket_id": "tkt-0001", "priority": "critical"},
            },
            ticket={"state": "assigned", "priority": "low"},
        )
        assert result.allowed is False
        assert result.rule_id == "SUPPORT-004"

    def test_allows_manager_set_priority_to_critical(self):
        engine = SupportPolicyEngine(require_manager_for_critical=True)
        result = engine.evaluate(
            actor={"user_id": "manager_alex", "role": "manager"},
            action={
                "type": "set_priority",
                "arguments": {"ticket_id": "tkt-0001", "priority": "critical"},
            },
            ticket={"state": "assigned", "priority": "low"},
        )
        assert result.allowed is True

    def test_allows_non_critical_actions(self):
        engine = SupportPolicyEngine()
        result = engine.evaluate(
            actor={"user_id": "agent_bob", "role": "agent"},
            action={
                "type": "escalate_ticket",
                "arguments": {"ticket_id": "tkt-0001"},
            },
            ticket={"state": "assigned"},
        )
        assert result.allowed is True
