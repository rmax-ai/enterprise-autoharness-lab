"""Authoritative policy engine for customer support tickets.

The policy engine is the FINAL authority on permissions. Harness acceptance
never implies policy authorization. This invariant must be tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autoharness_lab.models import PolicyDecision


@dataclass(frozen=True)
class PolicyRule:
    """A single policy rule."""

    rule_id: str
    description: str
    priority: int  # Lower number = evaluated first


# ── Built-in Rules ────────────────────────────────────────────────────

RULE_NO_SELF_ASSIGN = PolicyRule(
    rule_id="SUPPORT-001",
    description="An agent cannot assign a ticket to themselves",
    priority=1,
)

RULE_REFUND_AUTHORIZATION = PolicyRule(
    rule_id="SUPPORT-002",
    description="Refunds above limit require manager authorization",
    priority=2,
)

RULE_UNAUTHORIZED_REFUND = PolicyRule(
    rule_id="SUPPORT-003",
    description="Only managers or authorized agents can issue refunds",
    priority=3,
)

RULE_CRITICAL_ESCALATION = PolicyRule(
    rule_id="SUPPORT-004",
    description="Critical priority tickets must be approved by a manager",
    priority=4,
)

RULE_NO_RESOLVE_CLOSED = PolicyRule(
    rule_id="SUPPORT-005",
    description="A resolved or closed ticket cannot be resolved again",
    priority=5,
)

RULE_NO_ASSIGN_CLOSED = PolicyRule(
    rule_id="SUPPORT-006",
    description="A closed ticket cannot be reassigned",
    priority=6,
)


# ── Policy Engine ─────────────────────────────────────────────────────


class SupportPolicyEngine:
    """Authoritative policy engine for support-ticket workflows.

    This engine is the FINAL authority. Even if the synthesized harness
    accepts an action, this engine may deny it based on business policy.
    """

    def __init__(
        self,
        refund_limit: float = 500.0,
        *,
        require_manager_for_refund: bool = True,
        require_manager_for_critical: bool = True,
    ):
        self.refund_limit = refund_limit
        self.require_manager_for_refund = require_manager_for_refund
        self.require_manager_for_critical = require_manager_for_critical

    def evaluate(
        self,
        actor: dict[str, Any],
        action: dict[str, Any],
        ticket: dict[str, Any] | None,
    ) -> PolicyDecision:
        """Evaluate whether an action is authorized by policy.

        Args:
            actor: Actor info dict (must include 'user_id' and 'role')
            action: Proposed action dict (must include 'type')
            ticket: Ticket state dict if applicable, or None

        Returns:
            PolicyDecision with allowed flag and rule reference.
        """
        action_type = action.get("type", "")
        actor_user = actor.get("user_id", "")
        actor_role = actor.get("role", "agent")

        # ── Assign checks ─────────────────────────────────────────────
        if action_type == "assign_ticket":
            if ticket is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="SUPPORT-000",
                    reason="Cannot assign without a ticket",
                )

            # SUPPORT-001: No self-assignment
            assignee = action.get("arguments", {}).get("assignee", "")
            if assignee and assignee == actor_user:
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_NO_SELF_ASSIGN.rule_id,
                    reason=RULE_NO_SELF_ASSIGN.description,
                )

            # SUPPORT-006: Cannot assign closed tickets
            ticket_state = ticket.get("state", "")
            if ticket_state == "closed":
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_NO_ASSIGN_CLOSED.rule_id,
                    reason=RULE_NO_ASSIGN_CLOSED.description,
                )

        # ── Refund checks ─────────────────────────────────────────────
        if action_type == "refund_customer":
            if ticket is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="SUPPORT-000",
                    reason="Cannot refund without a ticket",
                )

            # SUPPORT-003: Only managers or authorized agents can issue refunds
            if self.require_manager_for_refund and actor_role not in ("manager", "admin"):
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_UNAUTHORIZED_REFUND.rule_id,
                    reason=RULE_UNAUTHORIZED_REFUND.description,
                )

            # SUPPORT-002: Refunds above limit need manager
            amount = float(action.get("arguments", {}).get("amount", 0))
            if amount > self.refund_limit and not ticket.get(
                "refund_approved", False
            ):
                return PolicyDecision(
                        allowed=False,
                        rule_id=RULE_REFUND_AUTHORIZATION.rule_id,
                        reason=(
                            f"Refund of {amount} exceeds limit "
                            f"of {self.refund_limit} and requires manager approval"
                        ),
                    )

        # ── Resolve checks ────────────────────────────────────────────
        if action_type == "resolve_ticket":
            if ticket is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="SUPPORT-000",
                    reason="Cannot resolve without a ticket",
                )

            # SUPPORT-005: Cannot resolve resolved/closed tickets
            ticket_state = ticket.get("state", "")
            if ticket_state in ("resolved", "closed"):
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_NO_RESOLVE_CLOSED.rule_id,
                    reason=RULE_NO_RESOLVE_CLOSED.description,
                )

            # SUPPORT-004: Critical tickets need manager approval to resolve
            if (
                self.require_manager_for_critical
                and ticket.get("priority") == "critical"
                and actor_role not in ("manager", "admin")
            ):
                return PolicyDecision(
                        allowed=False,
                        rule_id=RULE_CRITICAL_ESCALATION.rule_id,
                        reason=RULE_CRITICAL_ESCALATION.description,
                    )

        # ── Set priority checks ───────────────────────────────────────
        if action_type == "set_priority":
            new_priority = action.get("arguments", {}).get("priority", "")
            # Setting to critical requires manager
            if (
                self.require_manager_for_critical
                and new_priority == "critical"
                and actor_role not in ("manager", "admin")
            ):
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_CRITICAL_ESCALATION.rule_id,
                    reason="Only managers can set priority to critical",
                )

        return PolicyDecision(
            allowed=True,
            rule_id="SUPPORT-000",
            reason="Action authorized",
        )
