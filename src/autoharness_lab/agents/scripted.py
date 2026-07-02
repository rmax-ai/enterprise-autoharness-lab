"""Deterministic baseline agent.

Always produces valid actions for known expense approval scenarios.
Used to verify environments and harnesses work correctly.
"""

from __future__ import annotations

from typing import Any

from autoharness_lab.models import Action


class ScriptedAgent:
    """Deterministic baseline agent.

    Follows a fixed policy: submit drafts, approve submitted items.
    Always produces structurally valid actions.
    """

    name = "scripted"

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose the next action based on a fixed policy."""
        expenses = observation.get("expenses", {})

        # Find first expense in draft state → submit it
        for eid, exp in expenses.items():
            if exp.get("state") == "draft":
                # If needs receipt, request it first
                if exp.get("amount", 0) > 50 and not exp.get("has_receipt", False):
                    return Action(type="request_receipt", arguments={"expense_id": eid})
                return Action(
                    type="submit_expense",
                    arguments={"expense_id": eid, "actor": "scripted"},
                )

        # Find first expense in submitted state → approve it (as manager)
        for eid, exp in expenses.items():
            if exp.get("state") == "submitted":
                # Don't self-approve
                if exp.get("submitter") == "scripted":
                    continue
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": "scripted"},
                )

        # Nothing to do
        return Action(type="submit_expense", arguments={"expense_id": "none"})
