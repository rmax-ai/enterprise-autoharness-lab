"""Expense-approval workflow environment with full state machine.

Implements the Environment protocol from autoharness_lab.models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from autoharness_lab.models import Action, ExecutionResult

# ── Domain Types ──────────────────────────────────────────────────────


class ExpenseState(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


SUPPORTED_ACTIONS = [
    "submit_expense",
    "request_receipt",
    "approve_expense",
    "reject_expense",
    "escalate_expense",
]

REQUIRED_EXPENSE_FIELDS = ["amount", "currency", "description", "category"]
SUPPORTED_CURRENCIES = {"EUR", "USD", "GBP", "CHF", "JPY"}


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class ExpenseItem:
    """A single expense claim."""

    expense_id: str
    amount: float
    currency: str
    description: str
    category: str
    submitter: str
    state: ExpenseState = ExpenseState.DRAFT
    has_receipt: bool = False
    approver: str | None = None
    submitted_at: str | None = None
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "expense_id": self.expense_id,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "category": self.category,
            "submitter": self.submitter,
            "state": self.state.value,
            "has_receipt": self.has_receipt,
            "approver": self.approver,
            "submitted_at": self.submitted_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class ExpenseApprovalConfig:
    """Configuration for the expense-approval environment."""

    approval_threshold: float = 1000.0  # Expenses above this need manager approval
    receipt_threshold: float = 50.0  # Expenses above this need a receipt
    require_receipt_for_all: bool = False
    allow_self_approval: bool = False
    supported_currencies: set[str] = field(default_factory=lambda: SUPPORTED_CURRENCIES.copy())
    max_approval_limit: float = 10000.0  # Managers cannot approve above this


# ── Environment Implementation ────────────────────────────────────────


class ExpenseApprovalEnvironment:
    """Expense-approval workflow environment.

    Implements the Environment protocol.
    """

    name = "expense-approval"

    def __init__(self, config: ExpenseApprovalConfig | None = None):
        self.config = config or ExpenseApprovalConfig()
        self._expenses: dict[str, ExpenseItem] = {}
        self._actor: dict[str, Any] = {}
        self._seed: int = 0

    # ── Environment Protocol ──────────────────────────────────────────

    def reset(self, seed: int) -> dict[str, Any]:
        """Reset environment for a new seed."""
        self._seed = seed
        self._expenses = {}

        # Create initial expenses from seed-derived data
        rng_state = seed
        expenses = [
            ExpenseItem(
                expense_id=f"exp-{rng_state:04d}",
                amount=150.0,
                currency="EUR",
                description="Office supplies",
                category="office",
                submitter="alice",
            ),
            ExpenseItem(
                expense_id=f"exp-{rng_state + 1:04d}",
                amount=2500.0,
                currency="USD",
                description="Conference registration",
                category="travel",
                submitter="bob",
                has_receipt=True,
            ),
            ExpenseItem(
                expense_id=f"exp-{rng_state + 2:04d}",
                amount=75.0,
                currency="EUR",
                description="Team lunch",
                category="meals",
                submitter="alice",
                state=ExpenseState.SUBMITTED,
                submitted_at=datetime.now(UTC).isoformat(),
            ),
        ]
        for exp in expenses:
            self._expenses[exp.expense_id] = exp

        return self.state_snapshot()

    def execute(self, action: Action) -> ExecutionResult:
        """Execute an action and return the result."""
        action_type = action.type
        args = action.arguments

        # --- Malformed action check ---
        if action_type not in SUPPORTED_ACTIONS:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="UNKNOWN_ACTION",
                message=f"Unknown action type: {action_type}",
            )

        # --- Dispatch ---
        handlers = {
            "submit_expense": self._handle_submit,
            "request_receipt": self._handle_request_receipt,
            "approve_expense": self._handle_approve,
            "reject_expense": self._handle_reject,
            "escalate_expense": self._handle_escalate,
        }
        return handlers[action_type](args)

    def available_action_types(self) -> list[str]:
        return SUPPORTED_ACTIONS.copy()

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "expenses": {eid: exp.to_dict() for eid, exp in self._expenses.items()},
            "config": {
                "approval_threshold": self.config.approval_threshold,
                "receipt_threshold": self.config.receipt_threshold,
                "require_receipt_for_all": self.config.require_receipt_for_all,
                "allow_self_approval": self.config.allow_self_approval,
                "supported_currencies": sorted(self.config.supported_currencies),
                "max_approval_limit": self.config.max_approval_limit,
            },
        }

    # ── Action Handlers ────────────────────────────────────────────────

    def _handle_submit(self, args: dict[str, Any]) -> ExecutionResult:
        """Submit an expense for approval."""
        expense_id = args.get("expense_id")

        if not expense_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_EXPENSE_ID",
                message="expense_id is required",
            )

        expense = self._expenses.get(expense_id)
        if expense is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="EXPENSE_NOT_FOUND",
                message=f"Expense {expense_id} not found",
            )

        if expense.state != ExpenseState.DRAFT:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot submit expense in state: {expense.state.value}",
            )

        # Validate currency
        if expense.currency not in self.config.supported_currencies:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="UNSUPPORTED_CURRENCY",
                message=f"Currency {expense.currency} is not supported",
            )

        # Receipt check
        if expense.amount > self.config.receipt_threshold and not expense.has_receipt:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_RECEIPT",
                message=f"Receipt required for expenses above {self.config.receipt_threshold}",
            )

        expense.state = ExpenseState.SUBMITTED
        expense.submitted_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Expense {expense_id} submitted",
            reward=0.1,
        )

    def _handle_request_receipt(self, args: dict[str, Any]) -> ExecutionResult:
        """Request or attach a receipt to an expense."""
        expense_id = args.get("expense_id")

        if not expense_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_EXPENSE_ID",
                message="expense_id is required",
            )

        expense = self._expenses.get(expense_id)
        if expense is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="EXPENSE_NOT_FOUND",
                message=f"Expense {expense_id} not found",
            )

        expense.has_receipt = True

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Receipt attached to expense {expense_id}",
            reward=0.05,
        )

    def _handle_approve(self, args: dict[str, Any]) -> ExecutionResult:
        """Approve an expense."""
        expense_id = args.get("expense_id")
        actor = args.get("actor", "unknown")

        if not expense_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_EXPENSE_ID",
                message="expense_id is required",
            )

        expense = self._expenses.get(expense_id)
        if expense is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="EXPENSE_NOT_FOUND",
                message=f"Expense {expense_id} not found",
            )

        if expense.state != ExpenseState.SUBMITTED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot approve expense in state: {expense.state.value}",
            )

        expense.state = ExpenseState.APPROVED
        expense.approver = actor
        expense.resolved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Expense {expense_id} approved by {actor}",
            reward=0.5,
        )

    def _handle_reject(self, args: dict[str, Any]) -> ExecutionResult:
        """Reject an expense."""
        expense_id = args.get("expense_id")
        actor = args.get("actor", "unknown")

        if not expense_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_EXPENSE_ID",
                message="expense_id is required",
            )

        expense = self._expenses.get(expense_id)
        if expense is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="EXPENSE_NOT_FOUND",
                message=f"Expense {expense_id} not found",
            )

        if expense.state != ExpenseState.SUBMITTED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot reject expense in state: {expense.state.value}",
            )

        expense.state = ExpenseState.REJECTED
        expense.approver = actor
        expense.resolved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Expense {expense_id} rejected by {actor}",
            reward=0.1,
        )

    def _handle_escalate(self, args: dict[str, Any]) -> ExecutionResult:
        """Escalate an expense to higher authority."""
        expense_id = args.get("expense_id")
        actor = args.get("actor", "unknown")

        if not expense_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_EXPENSE_ID",
                message="expense_id is required",
            )

        expense = self._expenses.get(expense_id)
        if expense is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="EXPENSE_NOT_FOUND",
                message=f"Expense {expense_id} not found",
            )

        # Can escalate from submitted or rejected states
        if expense.state not in (ExpenseState.SUBMITTED, ExpenseState.REJECTED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot escalate expense in state: {expense.state.value}",
            )

        expense.state = ExpenseState.ESCALATED
        expense.resolved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Expense {expense_id} escalated by {actor}",
            reward=0.2,
        )
