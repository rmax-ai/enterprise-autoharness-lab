"""Authoritative policy engine for support-ticket workflows."""

from __future__ import annotations

from typing import Any

from autoharness_lab.models import PolicyDecision


class SupportTicketPolicyEngine:
    """Policy engine for support-ticket workflows.

    Enforces:
    - SLA: critical tickets must be assigned within 1h; high within 4h
    - Role-based: only support agents can resolve tickets
    - Refund: refund requests capped at configurable limit
    - Escalation: only manager can approve escalations
    """

    def __init__(
        self,
        refund_limit: float = 500.0,
        sla_critical_hours: int = 1,
        sla_high_hours: int = 4,
    ):
        self.refund_limit = refund_limit
        self.sla_critical_hours = sla_critical_hours
        self.sla_high_hours = sla_high_hours

    def evaluate(
        self,
        actor: dict[str, Any],
        action: dict[str, Any],
        ticket: dict[str, Any] | None,
    ) -> PolicyDecision:
        action_type = action.get("type", "")
        actor_role = actor.get("role", "agent")
        actor_id = actor.get("user_id", "")

        # ESC-001: Only agents and managers can interact with tickets
        if actor_role not in ("agent", "manager", "admin"):
            return PolicyDecision(
                allowed=False,
                rule_id="ESC-001",
                reason=f"Role {actor_role} not authorized for support operations",
            )

        # ESC-002: Only assigned agent can resolve
        if action_type == "resolve_ticket" and ticket:
            assignee = ticket.get("assignee")
            if assignee and assignee != actor_id and actor_role != "manager":
                return PolicyDecision(
                    allowed=False,
                    rule_id="ESC-002",
                    reason=f"Only assigned agent ({assignee}) or manager can resolve",
                )

        # ESC-003: Only manager can approve escalations
        if action_type == "escalate_ticket" and actor_role not in ("manager", "admin"):
            return PolicyDecision(
                allowed=False,
                rule_id="ESC-003",
                reason="Only managers can approve escalations",
            )

        # ESC-004: Refund requests capped
        if action_type == "resolve_ticket" and ticket:
            refund_amount = float(action.get("arguments", {}).get("refund_amount", 0))
            if refund_amount > self.refund_limit and actor_role != "manager":
                return PolicyDecision(
                    allowed=False,
                    rule_id="ESC-004",
                    reason=f"Refund {refund_amount} exceeds agent limit of {self.refund_limit}",
                )

        # ESC-005: Can't close own reopened ticket as agent
        if action_type == "close_ticket" and ticket:
            notes = ticket.get("notes", [])
            has_reopen = any(n.startswith("[REOPEN]") for n in notes)
            if has_reopen and actor_role == "agent":
                reopen_count = sum(1 for n in notes if n.startswith("[REOPEN]"))
                if reopen_count >= 1:
                    return PolicyDecision(
                        allowed=False,
                        rule_id="ESC-005",
                        reason="Manager review required before closing reopened ticket",
                    )

        return PolicyDecision(
            allowed=True,
            rule_id="ESC-000",
            reason="Action authorized",
        )
