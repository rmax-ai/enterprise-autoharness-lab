"""Authoritative policy engine for expense approval.

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

RULE_SELF_APPROVAL = PolicyRule(
    rule_id="EXP-001",
    description="An employee cannot approve their own expenses",
    priority=1,
)

RULE_APPROVAL_LIMIT = PolicyRule(
    rule_id="EXP-002",
    description="Manager approval limit enforced",
    priority=2,
)

RULE_RECEIPT_REQUIRED = PolicyRule(
    rule_id="EXP-003",
    description="Receipt required for expenses above threshold",
    priority=3,
)

RULE_CURRENCY_VALID = PolicyRule(
    rule_id="EXP-004",
    description="Currency must be supported",
    priority=4,
)

RULE_APPROVED_ONLY_ONCE = PolicyRule(
    rule_id="EXP-005",
    description="An expense cannot be approved twice",
    priority=5,
)

RULE_REJECTED_CANNOT_APPROVE = PolicyRule(
    rule_id="EXP-006",
    description="A rejected expense cannot be approved",
    priority=6,
)


# ── Actor Roles ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Actor:
    """An actor in the system."""

    user_id: str
    role: str  # "employee", "manager", "admin"
    approval_limit: float = 0.0


# ── Policy Engine ─────────────────────────────────────────────────────


class ExpensePolicyEngine:
    """Authoritative policy engine for expense-approval workflows.

    This engine is the FINAL authority. Even if the synthesized harness
    accepts an action, this engine may deny it based on business policy.
    """

    def __init__(
        self,
        approval_threshold: float = 1000.0,
        max_approval_limit: float = 10000.0,
        supported_currencies: set[str] | None = None,
    ):
        self.approval_threshold = approval_threshold
        self.max_approval_limit = max_approval_limit
        self.supported_currencies = supported_currencies or {"EUR", "USD", "GBP", "CHF", "JPY"}

    def evaluate(
        self,
        actor: dict[str, Any],
        action: dict[str, Any],
        expense: dict[str, Any] | None,
    ) -> PolicyDecision:
        """Evaluate whether an action is authorized by policy.

        Args:
            actor: Actor info dict (must include 'user_id' and 'role')
            action: Proposed action dict (must include 'type')
            expense: Expense state dict if applicable, or None

        Returns:
            PolicyDecision with allowed flag and rule reference.
        """
        action_type = action.get("type", "")
        actor_user = actor.get("user_id", "")
        actor_role = actor.get("role", "employee")
        actor_limit = float(actor.get("approval_limit", 0))

        # ── Approve/reject actions need deeper checks ─────────────────
        if action_type in ("approve_expense", "reject_expense"):
            if expense is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="EXP-000",
                    reason="Cannot approve/reject without an expense",
                )

            # EXP-001: No self-approval
            if expense.get("submitter") == actor_user:
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_SELF_APPROVAL.rule_id,
                    reason=RULE_SELF_APPROVAL.description,
                )

            # EXP-005: Cannot approve already-approved expense
            if expense.get("state") == "approved":
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_APPROVED_ONLY_ONCE.rule_id,
                    reason=RULE_APPROVED_ONLY_ONCE.description,
                )

            # EXP-006: Cannot approve rejected expense
            if expense.get("state") == "rejected" and action_type == "approve_expense":
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_REJECTED_CANNOT_APPROVE.rule_id,
                    reason=RULE_REJECTED_CANNOT_APPROVE.description,
                )

            # EXP-002: Approval limit check (only for approve)
            if action_type == "approve_expense":
                expense_amount = float(expense.get("amount", 0))
                if expense_amount > self.approval_threshold:
                    if actor_role != "manager" and actor_role != "admin":
                        return PolicyDecision(
                            allowed=False,
                            rule_id=RULE_APPROVAL_LIMIT.rule_id,
                            reason=(
                                f"Expense amount {expense_amount} "
                                f"exceeds {actor_role} approval threshold"
                            ),
                        )
                    if actor_limit > 0 and expense_amount > actor_limit:
                        return PolicyDecision(
                            allowed=False,
                            rule_id=RULE_APPROVAL_LIMIT.rule_id,
                            reason=(
                                f"Expense amount {expense_amount} "
                                f"exceeds manager approval limit of {actor_limit}"
                            ),
                        )

            # EXP-003: Receipt check for approve
            if action_type == "approve_expense":
                expense_amount = float(expense.get("amount", 0))
                if expense_amount > 50.0 and not expense.get("has_receipt", False):
                    return PolicyDecision(
                        allowed=False,
                        rule_id=RULE_RECEIPT_REQUIRED.rule_id,
                        reason=f"Receipt required for expense amount {expense_amount}",
                    )

        # ── Currency check for submission ─────────────────────────────
        if action_type == "submit_expense":
            currency = expense.get("currency", "") if expense else ""
            if currency and currency not in self.supported_currencies:
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_CURRENCY_VALID.rule_id,
                    reason=f"Currency {currency} is not supported",
                )

        return PolicyDecision(
            allowed=True,
            rule_id="EXP-000",
            reason="Action authorized",
        )
