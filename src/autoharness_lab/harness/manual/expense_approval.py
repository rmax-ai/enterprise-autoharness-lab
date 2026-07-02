"""Manual harness for expense-approval workflows.

Hand-written validation code that demonstrates what a generated harness
should learn to do. Used as the "manual" condition in experiments.
"""

from __future__ import annotations

from typing import Any

SUPPORTED_ACTIONS = [
    "submit_expense",
    "request_receipt",
    "approve_expense",
    "reject_expense",
    "escalate_expense",
]

SUPPORTED_CURRENCIES = {"EUR", "USD", "GBP", "CHF", "JPY"}

CANONICAL_FIELDS = {
    "expense_id": "expense_id",
    "expenseid": "expense_id",
    "expenseId": "expense_id",
    "id": "expense_id",
}


def _normalize_field(key: str) -> str:
    """Normalize a field name to its canonical form."""
    return CANONICAL_FIELDS.get(key, key)


def evaluate_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether a proposed action is operationally valid.

    This is a manual harness — it knows the expense-approval domain rules
    and validates actions against them.

    Returns:
        {"accepted": bool, "normalized_action": dict|None, "reason": str, "confidence": float|None}
    """
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})

    # Normalize arguments
    normalized_args = {_normalize_field(k): v for k, v in args.items()}

    # ── Unknown action type ────────────────────────────────────────
    if action_type not in SUPPORTED_ACTIONS:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": f"Unknown action type: {action_type}",
            "confidence": 0.99,
        }

    # ── Missing expense_id ──────────────────────────────────────────
    if "expense_id" not in normalized_args:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": "Missing required field: expense_id",
            "confidence": 0.99,
        }

    expense_id = normalized_args["expense_id"]
    expenses = observation.get("expenses", {})
    expense = expenses.get(expense_id)

    # ── Expense not found ───────────────────────────────────────────
    if expense is None:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": f"Expense {expense_id} not found",
            "confidence": 0.99,
        }

    expense_state = expense.get("state", "")

    # ── State-specific validation ───────────────────────────────────

    if action_type == "submit_expense":
        if expense_state != "draft":
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot submit expense in state: {expense_state}",
                "confidence": 0.95,
            }
        # Currency check
        currency = expense.get("currency", "")
        if currency and currency not in SUPPORTED_CURRENCIES:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Unsupported currency: {currency}",
                "confidence": 0.95,
            }
        # Receipt check
        amount = expense.get("amount", 0)
        if amount > 50 and not expense.get("has_receipt", False):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Receipt required for amount {amount}",
                "confidence": 0.90,
            }

    elif action_type in ("approve_expense", "reject_expense"):
        if expense_state != "submitted":
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot {action_type} expense in state: {expense_state}",
                "confidence": 0.95,
            }
        # Self-approval check
        if action_type == "approve_expense":
            actor = normalized_args.get("actor", "")
            submitter = expense.get("submitter", "")
            if actor and submitter and actor == submitter:
                return {
                    "accepted": False,
                    "normalized_action": None,
                    "reason": "Self-approval is not allowed",
                    "confidence": 0.99,
                }

    elif action_type == "escalate_expense":
        if expense_state not in ("submitted", "rejected"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot escalate expense in state: {expense_state}",
                "confidence": 0.95,
            }

    # ── Action accepted ────────────────────────────────────────────
    return {
        "accepted": True,
        "normalized_action": {
            "type": action_type,
            "arguments": normalized_args,
        },
        "reason": "Action is operationally valid",
        "confidence": 0.85,
    }


def repair_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
    failure: dict[str, Any],
) -> dict[str, Any] | None:
    """Attempt to repair a failed action."""
    error_code = failure.get("error_code", "")
    args = proposed_action.get("arguments", {})
    normalized_args = {_normalize_field(k): v for k, v in args.items()}

    # If missing receipt, suggest requesting it
    if error_code == "MISSING_RECEIPT" and "expense_id" in normalized_args:
        return {
            "type": "request_receipt",
            "arguments": {"expense_id": normalized_args["expense_id"]},
        }

    return None
