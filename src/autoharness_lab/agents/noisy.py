"""Agent implementations for AutoHarness Lab.

- ScriptedAgent: deterministic baseline that always produces valid actions
- NoisyAgent: deliberately weak agent for reproducible failure generation
"""

from __future__ import annotations

import random
from typing import Any

from autoharness_lab.models import Action


class ScriptedAgent:
    """Deterministic baseline agent.

    Follows a fixed policy: always produces valid actions for known expense
    approval scenarios. Used to verify environments and harnesses work correctly.
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

        # Find first expense in submitted state → approve it
        for eid, exp in expenses.items():
            if exp.get("state") == "submitted":
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": "scripted"},
                )

        # Nothing to do
        return Action(type="submit_expense", arguments={"expense_id": "none"})


class NoisyAgent:
    """Deliberately weak agent for reproducible failure generation.

    Introduces controlled errors at configurable rates to generate the
    failure corpus needed for harness synthesis.

    Error types:
    - wrong_action_type: emits an action type that doesn't exist
    - missing_fields: omits required fields in arguments
    - invalid_state: proposes an action valid in the wrong state
    - self_approval: proposes approving own expense
    """

    name = "noisy"

    def __init__(
        self,
        seed: int = 42,
        wrong_type_rate: float = 0.15,
        missing_fields_rate: float = 0.10,
        invalid_state_rate: float = 0.10,
        self_approval_rate: float = 0.10,
    ):
        self._rng = random.Random(seed)
        self.wrong_type_rate = wrong_type_rate
        self.missing_fields_rate = missing_fields_rate
        self.invalid_state_rate = invalid_state_rate
        self.self_approval_rate = self_approval_rate

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose an action, sometimes incorrectly."""
        # Detect domain from observation structure
        if "tickets" in observation:
            return self._propose_ticket_action(task, observation, available_actions)
        return self._propose_expense_action(task, observation, available_actions)

    def _propose_expense_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Noisy expense-approval action proposal."""
        expenses = observation.get("expenses", {})
        actor = task.split("_")[0] if "_" in task else "noisy"

        # ── Wrong action type ────────────────────────────────────────
        if self._rng.random() < self.wrong_type_rate:
            return Action(
                type="invalid_action_type_xyz",
                arguments={"expense_id": "exp-0001"},
            )

        # ── Find the action we'd normally take ────────────────────────
        for eid, exp in expenses.items():
            state = exp.get("state", "")

            if state == "draft":
                if self._rng.random() < self.missing_fields_rate:
                    return Action(
                        type="submit_expense",
                        arguments={},
                    )
                return Action(
                    type="submit_expense",
                    arguments={"expense_id": eid},
                )

            if state == "submitted":
                if self._rng.random() < self.self_approval_rate:
                    return Action(
                        type="approve_expense",
                        arguments={"expense_id": eid, "actor": exp.get("submitter", actor)},
                    )
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": actor},
                )

        # ── Invalid state: try approving already-approved ─────────────
        if self._rng.random() < self.invalid_state_rate:
            for eid, exp in expenses.items():
                if exp.get("state") == "approved":
                    return Action(
                        type="approve_expense",
                        arguments={"expense_id": eid, "actor": actor},
                    )

        return Action(type="submit_expense", arguments={"expense_id": "exp-0001", "actor": actor})

    def _propose_ticket_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Noisy support-ticket action proposal."""
        tickets = observation.get("tickets", {})
        actor = task.split("_")[0] if "_" in task else "noisy"

        error_types = [
            "assign_ticket",
            "set_priority",
            "resolve_ticket",
            "refund_customer",
            "escalate_ticket",
        ]

        # ── Wrong action type ────────────────────────────────────
        if self._rng.random() < self.wrong_type_rate:
            return Action(
                type="invalid_action_type_xyz",
                arguments={"ticket_id": "tkt-0001"},
            )

        # ── Missing fields ───────────────────────────────────────
        if self._rng.random() < self.missing_fields_rate:
            action_type = self._rng.choice(error_types)
            return Action(
                type=action_type,
                arguments={},
            )

        # ── Operate on first available ticket ────────────────────
        for tid, tkt in tickets.items():
            state = tkt.get("state", "")

            if state == "new":
                assignee = (
                    tkt.get("customer", actor)
                    if self._rng.random() < self.self_approval_rate
                    else "agent_bob"
                )
                return Action(
                    type="assign_ticket",
                    arguments={"ticket_id": tid, "assignee": assignee},
                )

            if state in ("assigned", "in_progress"):
                if self._rng.random() < 0.3:
                    return Action(
                        type="set_priority",
                        arguments={"ticket_id": tid, "priority": "high"},
                    )
                return Action(
                    type="resolve_ticket",
                    arguments={"ticket_id": tid, "resolution": "Done"},
                )

        # ── Invalid state ────────────────────────────────────────
        if self._rng.random() < self.invalid_state_rate:
            for tid, tkt in tickets.items():
                if tkt.get("state") == "resolved":
                    return Action(
                        type="resolve_ticket",
                        arguments={"ticket_id": tid},
                    )

        return Action(type="assign_ticket", arguments={"ticket_id": "tkt-0001", "assignee": actor})
