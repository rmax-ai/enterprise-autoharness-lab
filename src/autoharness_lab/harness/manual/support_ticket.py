"""Manual harness for support-ticket workflows.

Hand-written validation code that demonstrates what a generated harness
should learn to do. Used as the "manual" condition in experiments.
"""

from __future__ import annotations

from typing import Any

SUPPORTED_ACTIONS = [
    "assign_ticket",
    "set_priority",
    "resolve_ticket",
    "refund_customer",
    "escalate_ticket",
]

VALID_PRIORITIES = {"low", "medium", "high", "critical"}

CANONICAL_FIELDS = {
    "ticket_id": "ticket_id",
    "ticketid": "ticket_id",
    "ticketId": "ticket_id",
    "id": "ticket_id",
}


def _normalize_field(key: str) -> str:
    """Normalize a field name to its canonical form."""
    return CANONICAL_FIELDS.get(key, key)


def evaluate_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether a proposed action is operationally valid.

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

    # ── Missing ticket_id ──────────────────────────────────────────
    if "ticket_id" not in normalized_args:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": "Missing required field: ticket_id",
            "confidence": 0.99,
        }

    ticket_id = normalized_args["ticket_id"]
    tickets = observation.get("tickets", {})
    ticket = tickets.get(ticket_id)

    # ── Ticket not found ───────────────────────────────────────────
    if ticket is None:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": f"Ticket {ticket_id} not found",
            "confidence": 0.99,
        }

    ticket_state = ticket.get("state", "")

    # ── State-specific validation ───────────────────────────────────

    if action_type == "assign_ticket":
        if ticket_state not in ("new", "escalated"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot assign ticket in state: {ticket_state}",
                "confidence": 0.95,
            }
        assignee = normalized_args.get("assignee", "")
        if not assignee:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Missing required field: assignee",
                "confidence": 0.95,
            }
        # Self-assignment check
        actor = observation.get("actor", {})
        if assignee == actor.get("user_id", ""):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Self-assignment is not allowed",
                "confidence": 0.99,
            }

    elif action_type == "set_priority":
        if ticket_state in ("resolved", "closed"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot change priority of ticket in state: {ticket_state}",
                "confidence": 0.95,
            }
        new_priority = normalized_args.get("priority", "")
        if not new_priority:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Missing required field: priority",
                "confidence": 0.95,
            }
        if new_priority not in VALID_PRIORITIES:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Invalid priority: {new_priority}",
                "confidence": 0.95,
            }

    elif action_type == "resolve_ticket":
        if ticket_state in ("resolved", "closed"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot resolve ticket already in state: {ticket_state}",
                "confidence": 0.95,
            }
        if ticket_state == "new":
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Cannot resolve an unassigned ticket",
                "confidence": 0.95,
            }

    elif action_type == "refund_customer":
        if ticket_state in ("new", "closed"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot refund ticket in state: {ticket_state}",
                "confidence": 0.95,
            }
        amount = normalized_args.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Invalid refund amount: {amount}",
                "confidence": 0.95,
            }

    elif action_type == "escalate_ticket":
        if ticket_state in ("resolved", "closed", "escalated"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot escalate ticket in state: {ticket_state}",
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

    # If ticket is critical and not escalated, suggest escalation
    if error_code == "POLICY_DENIED" and "ticket_id" in normalized_args:
        ticket_id = normalized_args["ticket_id"]
        tickets = observation.get("tickets", {})
        ticket = tickets.get(ticket_id)
        if ticket and ticket.get("priority") == "critical":
            return {
                "type": "escalate_ticket",
                "arguments": {"ticket_id": ticket_id},
            }

    return None
