"""Support-ticket workflow environment with full state machine.

Implements the Environment protocol from autoharness_lab.models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from autoharness_lab.models import Action, ExecutionResult

# ── Domain Types ──────────────────────────────────────────────────────


class TicketState(StrEnum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


SUPPORTED_ACTIONS = [
    "assign_ticket",
    "set_priority",
    "resolve_ticket",
    "refund_customer",
    "escalate_ticket",
]

PRIORITY_LEVELS = {"low", "medium", "high", "critical"}
VALID_PRIORITY_LEVELS = {"low", "medium", "high", "critical"}

# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class SupportTicket:
    """A single customer support ticket."""

    ticket_id: str
    customer: str
    description: str
    priority: str  # "low", "medium", "high", "critical"
    category: str
    state: TicketState = TicketState.NEW
    assignee: str | None = None
    sla_deadline: str | None = None
    refund_amount: float = 0.0
    refund_approved: bool = False
    created_at: str | None = None
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "customer": self.customer,
            "description": self.description,
            "priority": self.priority,
            "category": self.category,
            "state": self.state.value,
            "assignee": self.assignee,
            "sla_deadline": self.sla_deadline,
            "refund_amount": self.refund_amount,
            "refund_approved": self.refund_approved,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class SupportTicketConfig:
    """Configuration for the support-ticket environment."""

    sla_hours: dict[str, int] = field(
        default_factory=lambda: {"low": 72, "medium": 24, "high": 4, "critical": 1}
    )
    refund_limit: float = 500.0
    allow_self_assignment: bool = False
    require_manager_for_refund: bool = True
    require_manager_for_critical: bool = True


# ── Environment Implementation ────────────────────────────────────────


class SupportTicketEnvironment:
    """Support-ticket workflow environment.

    Implements the Environment protocol.
    """

    name = "support-ticket"

    def __init__(self, config: SupportTicketConfig | None = None):
        self.config = config or SupportTicketConfig()
        self._tickets: dict[str, SupportTicket] = {}
        self._seed: int = 0

    # ── Environment Protocol ──────────────────────────────────────────

    def reset(self, seed: int) -> dict[str, Any]:
        """Reset environment for a new seed."""
        self._seed = seed
        self._tickets = {}

        rng_state = seed
        tickets = [
            SupportTicket(
                ticket_id=f"tkt-{rng_state:04d}",
                customer="acme-corp",
                description="Payment gateway timeout during checkout",
                priority="high",
                category="payments",
                state=TicketState.NEW,
                sla_deadline=datetime.now(UTC).isoformat(),
            ),
            SupportTicket(
                ticket_id=f"tkt-{rng_state + 1:04d}",
                customer="globex-inc",
                description="Invoice PDF not generating for enterprise plan",
                priority="medium",
                category="billing",
                state=TicketState.ASSIGNED,
                assignee="alice",
                sla_deadline=datetime.now(UTC).isoformat(),
            ),
            SupportTicket(
                ticket_id=f"tkt-{rng_state + 2:04d}",
                customer="initech",
                description="Critical — production API returning 503 errors",
                priority="critical",
                category="infrastructure",
                state=TicketState.NEW,
                sla_deadline=datetime.now(UTC).isoformat(),
            ),
        ]
        for t in tickets:
            self._tickets[t.ticket_id] = t

        return self.state_snapshot()

    def execute(self, action: Action) -> ExecutionResult:
        """Execute an action and return the result."""
        action_type = action.type
        args = action.arguments

        if action_type not in SUPPORTED_ACTIONS:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="UNKNOWN_ACTION",
                message=f"Unknown action type: {action_type}",
            )

        handlers = {
            "assign_ticket": self._handle_assign,
            "set_priority": self._handle_set_priority,
            "resolve_ticket": self._handle_resolve,
            "refund_customer": self._handle_refund,
            "escalate_ticket": self._handle_escalate,
        }
        return handlers[action_type](args)

    def available_action_types(self) -> list[str]:
        return SUPPORTED_ACTIONS.copy()

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "tickets": {tid: t.to_dict() for tid, t in self._tickets.items()},
            "config": {
                "sla_hours": dict(self.config.sla_hours),
                "refund_limit": self.config.refund_limit,
                "allow_self_assignment": self.config.allow_self_assignment,
                "require_manager_for_refund": self.config.require_manager_for_refund,
                "require_manager_for_critical": self.config.require_manager_for_critical,
            },
        }

    # ── Action Handlers ────────────────────────────────────────────────

    def _require_ticket(self, args: dict[str, Any]) -> SupportTicket | ExecutionResult:
        """Validate ticket_id and return the ticket or an error result."""
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_TICKET_ID",
                message="ticket_id is required",
            )
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="TICKET_NOT_FOUND",
                message=f"Ticket {ticket_id} not found",
            )
        return ticket

    def _handle_assign(self, args: dict[str, Any]) -> ExecutionResult:
        """Assign a ticket to an agent."""
        result = self._require_ticket(args)
        if isinstance(result, ExecutionResult):
            return result
        ticket = result

        if ticket.state not in (TicketState.NEW, TicketState.ESCALATED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot assign ticket in state: {ticket.state.value}",
            )

        assignee = args.get("assignee", "")
        if not assignee:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_ASSIGNEE",
                message="assignee is required",
            )

        ticket.assignee = assignee
        ticket.state = TicketState.ASSIGNED
        ticket.created_at = ticket.created_at or datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket.ticket_id} assigned to {assignee}",
            reward=0.1,
        )

    def _handle_set_priority(self, args: dict[str, Any]) -> ExecutionResult:
        """Change the priority of a ticket."""
        result = self._require_ticket(args)
        if isinstance(result, ExecutionResult):
            return result
        ticket = result

        if ticket.state in (TicketState.RESOLVED, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot change priority of ticket in state: {ticket.state.value}",
            )

        new_priority = args.get("priority", "")
        if not new_priority:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_PRIORITY",
                message="priority is required",
            )
        if new_priority not in VALID_PRIORITY_LEVELS:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_PRIORITY",
                message=(
                    "Invalid priority: "
                    f"{new_priority}. Must be one of {sorted(VALID_PRIORITY_LEVELS)}"
                ),
            )

        old_priority = ticket.priority
        ticket.priority = new_priority

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=(
                f"Ticket {ticket.ticket_id} priority changed"
                f" from {old_priority} to {new_priority}"
            ),
            reward=0.05,
        )

    def _handle_resolve(self, args: dict[str, Any]) -> ExecutionResult:
        """Resolve a ticket."""
        result = self._require_ticket(args)
        if isinstance(result, ExecutionResult):
            return result
        ticket = result

        if ticket.state in (TicketState.RESOLVED, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot resolve ticket already in state: {ticket.state.value}",
            )

        if ticket.state == TicketState.NEW:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message="Cannot resolve an unassigned ticket",
            )

        resolution = args.get("resolution", "Resolved")
        ticket.state = TicketState.RESOLVED
        ticket.resolved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket.ticket_id} resolved: {resolution}",
            reward=0.5,
        )

    def _handle_refund(self, args: dict[str, Any]) -> ExecutionResult:
        """Process a refund for a ticket."""
        result = self._require_ticket(args)
        if isinstance(result, ExecutionResult):
            return result
        ticket = result

        if ticket.state in (TicketState.NEW, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot refund ticket in state: {ticket.state.value}",
            )

        amount = args.get("amount", 0.0)
        if not isinstance(amount, (int, float)) or amount <= 0:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_REFUND_AMOUNT",
                message=f"Invalid refund amount: {amount}",
            )

        if amount > self.config.refund_limit and not ticket.refund_approved:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="REFUND_OVER_LIMIT",
                message=(
                    "Refund amount "
                    f"{amount} exceeds limit of {self.config.refund_limit}"
                    " and is not approved"
                ),
            )

        ticket.refund_amount = amount

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Refund of {amount} processed for ticket {ticket.ticket_id}",
            reward=0.3,
        )

    def _handle_escalate(self, args: dict[str, Any]) -> ExecutionResult:
        """Escalate a ticket to higher support tier."""
        result = self._require_ticket(args)
        if isinstance(result, ExecutionResult):
            return result
        ticket = result

        if ticket.state in (TicketState.RESOLVED, TicketState.CLOSED, TicketState.ESCALATED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot escalate ticket in state: {ticket.state.value}",
            )

        ticket.state = TicketState.ESCALATED

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket.ticket_id} escalated",
            reward=0.2,
        )
