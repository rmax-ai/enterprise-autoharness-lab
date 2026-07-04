"""Deterministic baseline agent.

Always produces valid actions for known scenarios across environments.
Used to verify environments and harnesses work correctly.
"""

from __future__ import annotations

from typing import Any

from autoharness_lab.models import Action


class ScriptedAgent:
    """Deterministic baseline agent.

    Follows a fixed policy: detects domain from observation structure
    and takes the next correct step.
    """

    name = "scripted"

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose the next action based on a fixed policy."""
        # Detect domain from observation structure
        if "tickets" in observation:
            return self._propose_ticket_action(task, observation, available_actions)
        if "deployments" in observation:
            return self._propose_deployment_action(task, observation, available_actions)
        return self._propose_expense_action(task, observation, available_actions)

    def _propose_expense_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Expense-approval fixed policy."""
        expenses = observation.get("expenses", {})

        for eid, exp in expenses.items():
            if exp.get("state") == "draft":
                if exp.get("amount", 0) > 50 and not exp.get("has_receipt", False):
                    return Action(type="request_receipt", arguments={"expense_id": eid})
                return Action(
                    type="submit_expense",
                    arguments={"expense_id": eid, "actor": "scripted"},
                )

        for eid, exp in expenses.items():
            if exp.get("state") == "submitted":
                if exp.get("submitter") == "scripted":
                    continue
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": "scripted"},
                )

        return Action(type="submit_expense", arguments={"expense_id": "none"})

    def _propose_ticket_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Support-ticket fixed policy."""
        tickets = observation.get("tickets", {})

        # Step 1: Assign new tickets
        for tid, tkt in tickets.items():
            if tkt.get("state") == "new":
                return Action(
                    type="assign_ticket",
                    arguments={"ticket_id": tid, "assignee": "agent_bob"},
                )

        # Step 2: Set priority on unprioritized tickets
        for tid, tkt in tickets.items():
            if tkt.get("state") in ("assigned", "in_progress") and tkt.get("priority") == "low":
                return Action(
                    type="set_priority",
                    arguments={"ticket_id": tid, "priority": "medium"},
                )

        # Step 3: Resolve assigned tickets
        for tid, tkt in tickets.items():
            if tkt.get("state") in ("assigned", "in_progress"):
                return Action(
                    type="resolve_ticket",
                    arguments={"ticket_id": tid, "resolution": "Issue resolved"},
                )

        # Step 4: Escalate critical unresolved
        for tid, tkt in tickets.items():
            if tkt.get("state") not in ("resolved", "closed", "escalated") and tkt.get(
                "priority"
            ) == "critical":
                return Action(
                    type="escalate_ticket",
                    arguments={"ticket_id": tid},
                )

        return Action(type="resolve_ticket", arguments={"ticket_id": "none"})

    def _propose_deployment_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Software-deployment fixed policy."""
        deployments = observation.get("deployments", {})

        # Step 1: Approve created deployments (as different actor)
        for did, dep in deployments.items():
            if dep.get("state") == "created" and dep.get("checks_passed", False):
                return Action(
                    type="approve_deployment",
                    arguments={"deployment_id": did, "approver": "manager_alex"},
                )

        # Step 2: Start approved deployments (skip production freeze)
        for did, dep in deployments.items():
            if dep.get("state") == "approved":
                return Action(
                    type="start_deployment",
                    arguments={"deployment_id": did},
                )

        # Step 3: Cancel stale created deployments
        for did, dep in deployments.items():
            if dep.get("state") == "created" and not dep.get("checks_passed", False):
                return Action(
                    type="cancel_deployment",
                    arguments={"deployment_id": did},
                )

        return Action(
            type="create_deployment",
            arguments={
                "deployment_id": "none",
                "service": "none",
                "environment": "staging",
            },
        )
