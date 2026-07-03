"""Support-ticket workflow environment with full state machine.

Models a customer support ticket system with SLA enforcement,
priority management, and escalation paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from autoharness_lab.models import Action, ExecutionResult


class TicketState(StrEnum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SUPPORTED_ACTIONS = [
    "assign_ticket",
    "set_priority",
    "add_note",
    "resolve_ticket",
    "close_ticket",
    "escalate_ticket",
    "reopen_ticket",
]


@dataclass
class TicketItem:
    ticket_id: str
    subject: str
    description: str
    customer: str
    state: TicketState = TicketState.NEW
    priority: TicketPriority = TicketPriority.MEDIUM
    assignee: str | None = None
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved_at: str | None = None
    sla_deadline: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "subject": self.subject,
            "description": self.description,
            "customer": self.customer,
            "state": self.state.value,
            "priority": self.priority.value,
            "assignee": self.assignee,
            "notes": self.notes.copy(),
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "sla_deadline": self.sla_deadline,
        }


@dataclass
class SupportTicketConfig:
    escalation_threshold_hours: int = 24
    require_assignee_before_resolve: bool = True
    require_note_before_close: bool = True
    max_reopen_count: int = 2
    refund_limit: float = 500.0


class SupportTicketEnvironment:
    """Support-ticket workflow environment."""

    name = "support-ticket"

    def __init__(self, config: SupportTicketConfig | None = None):
        self.config = config or SupportTicketConfig()
        self._tickets: dict[str, TicketItem] = {}
        self._seed: int = 0

    def reset(self, seed: int) -> dict[str, Any]:
        self._seed = seed
        self._tickets = {}

        tickets = [
            TicketItem(
                ticket_id=f"tkt-{seed:04d}",
                subject="Login failure after update",
                description="User cannot log in after latest system update.",
                customer="acme-corp",
                priority=TicketPriority.HIGH,
            ),
            TicketItem(
                ticket_id=f"tkt-{seed + 1:04d}",
                subject="Billing discrepancy",
                description="Customer reports overcharge on last invoice.",
                customer="globex",
                priority=TicketPriority.MEDIUM,
                state=TicketState.ASSIGNED,
                assignee="agent_smith",
            ),
            TicketItem(
                ticket_id=f"tkt-{seed + 2:04d}",
                subject="Feature request: dark mode",
                description="Request to add dark mode to the dashboard.",
                customer="initech",
                priority=TicketPriority.LOW,
                state=TicketState.IN_PROGRESS,
                assignee="agent_neo",
            ),
            TicketItem(
                ticket_id=f"tkt-{seed + 3:04d}",
                subject="Data export timeout",
                description="Export of large dataset times out after 30s.",
                customer="acme-corp",
                priority=TicketPriority.CRITICAL,
                state=TicketState.ASSIGNED,
                assignee="agent_smith",
            ),
        ]
        for tkt in tickets:
            self._tickets[tkt.ticket_id] = tkt

        return self.state_snapshot()

    def execute(self, action: Action) -> ExecutionResult:
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
            "add_note": self._handle_add_note,
            "resolve_ticket": self._handle_resolve,
            "close_ticket": self._handle_close,
            "escalate_ticket": self._handle_escalate,
            "reopen_ticket": self._handle_reopen,
        }
        return handlers[action_type](args)

    def available_action_types(self) -> list[str]:
        return SUPPORTED_ACTIONS.copy()

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "tickets": {tid: t.to_dict() for tid, t in self._tickets.items()},
            "config": {
                "escalation_threshold_hours": self.config.escalation_threshold_hours,
                "require_assignee_before_resolve": self.config.require_assignee_before_resolve,
                "require_note_before_close": self.config.require_note_before_close,
                "max_reopen_count": self.config.max_reopen_count,
                "refund_limit": self.config.refund_limit,
            },
        }

    def _get_ticket(self, args: dict[str, Any]) -> TicketItem | None:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return None
        return self._tickets.get(ticket_id)

    def _missing_id_result(self) -> ExecutionResult:
        return ExecutionResult(
            status="invalid_action",
            observation=self.state_snapshot(),
            error_code="MISSING_TICKET_ID",
            message="ticket_id is required",
        )

    def _not_found_result(self, ticket_id: str) -> ExecutionResult:
        return ExecutionResult(
            status="invalid_action",
            observation=self.state_snapshot(),
            error_code="TICKET_NOT_FOUND",
            message=f"Ticket {ticket_id} not found",
        )

    def _handle_assign(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

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

        # Self-assignment check
        if ticket.assignee and ticket.assignee == assignee:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="SELF_ASSIGNMENT",
                message="Cannot reassign ticket to same agent",
            )

        ticket.assignee = assignee
        ticket.state = TicketState.ASSIGNED

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} assigned to {assignee}",
            reward=0.2,
        )

    def _handle_set_priority(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state in (TicketState.RESOLVED, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot change priority of {ticket.state.value} ticket",
            )

        new_priority = args.get("priority", "")
        valid = {p.value for p in TicketPriority}
        if new_priority not in valid:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_PRIORITY",
                message=f"Invalid priority: {new_priority}. Valid: {sorted(valid)}",
            )

        ticket.priority = TicketPriority(new_priority)
        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} priority set to {new_priority}",
            reward=0.05,
        )

    def _handle_add_note(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state in (TicketState.CLOSED,):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot add note to {ticket.state.value} ticket",
            )

        note = args.get("note", "")
        if not note:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_NOTE",
                message="note is required",
            )

        ticket.notes.append(note)
        if ticket.state == TicketState.ASSIGNED:
            ticket.state = TicketState.IN_PROGRESS

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Note added to ticket {ticket_id}",
            reward=0.05,
        )

    def _handle_resolve(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state not in (TicketState.IN_PROGRESS, TicketState.ESCALATED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot resolve ticket in state: {ticket.state.value}",
            )

        if self.config.require_assignee_before_resolve and not ticket.assignee:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="UNASSIGNED_RESOLVE",
                message="Ticket must be assigned before resolving",
            )

        ticket.state = TicketState.RESOLVED
        ticket.resolved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} resolved",
            reward=0.3,
        )

    def _handle_close(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state != TicketState.RESOLVED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot close ticket in state: {ticket.state.value}",
            )

        if self.config.require_note_before_close and not ticket.notes:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="NO_NOTES",
                message="Ticket requires at least one note before closing",
            )

        ticket.state = TicketState.CLOSED
        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} closed",
            reward=0.2,
        )

    def _handle_escalate(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state in (TicketState.RESOLVED, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot escalate {ticket.state.value} ticket",
            )

        ticket.state = TicketState.ESCALATED
        ticket.assignee = None

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} escalated",
            reward=0.15,
        )

    def _handle_reopen(self, args: dict[str, Any]) -> ExecutionResult:
        ticket_id = args.get("ticket_id")
        if not ticket_id:
            return self._missing_id_result()

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return self._not_found_result(ticket_id)

        if ticket.state not in (TicketState.RESOLVED, TicketState.CLOSED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot reopen ticket in state: {ticket.state.value}",
            )

        # Count previous reopens via notes
        reopen_count = sum(1 for n in ticket.notes if n.startswith("[REOPEN]"))
        if reopen_count >= self.config.max_reopen_count:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MAX_REOPENS",
                message=f"Ticket has reached max reopen limit ({self.config.max_reopen_count})",
            )

        ticket.state = TicketState.IN_PROGRESS
        ticket.notes.append("[REOPEN] Ticket reopened")
        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Ticket {ticket_id} reopened",
            reward=0.1,
        )
