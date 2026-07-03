"""Environment mutation engine and catalog for drift experiments.

Tests whether a synthesized harness degrades when the environment
changes, and whether re-synthesis can recover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autoharness_lab.environments.deployment import DeploymentConfig
from autoharness_lab.environments.expense_approval import ExpenseApprovalConfig
from autoharness_lab.environments.support_ticket import SupportTicketConfig
from autoharness_lab.models import MutationSpec


@dataclass(frozen=True)
class MutationResult:
    """Result of a single mutation experiment."""

    mutation_id: str
    environment: str
    description: str

    # Baseline (original environment, original harness)
    baseline_score: float
    baseline_metrics: dict[str, float]

    # Degraded (mutated environment, original harness)
    degraded_score: float
    degraded_metrics: dict[str, float]
    score_drop: float  # baseline - degraded

    # Recovered (mutated environment, re-synthesized harness)
    recovered_score: float | None = None
    recovered_metrics: dict[str, float] | None = None
    recovery_delta: float | None = None  # recovered - degraded

    # Recovery effort
    counterexamples_needed: int | None = None
    iterations_to_recover: int | None = None
    recovered: bool = False


# ── Mutation Catalog ──────────────────────────────────────────────────

EXPENSE_MUTATIONS = [
    MutationSpec(
        mutation_id="expense-threshold-halved",
        environment="expense-approval",
        description="Approval threshold lowered from 1000 to 500",
        config_changes={"approval_threshold": 500.0},
    ),
    MutationSpec(
        mutation_id="expense-threshold-doubled",
        environment="expense-approval",
        description="Approval threshold raised from 1000 to 2000",
        config_changes={"approval_threshold": 2000.0},
    ),
    MutationSpec(
        mutation_id="expense-receipt-all",
        environment="expense-approval",
        description="Receipt required for all expenses regardless of amount",
        config_changes={"receipt_threshold": 0.0, "require_receipt_for_all": True},
    ),
    MutationSpec(
        mutation_id="expense-self-approval-allowed",
        environment="expense-approval",
        description="Self-approval suddenly allowed",
        config_changes={"allow_self_approval": True},
    ),
    MutationSpec(
        mutation_id="expense-currency-restricted",
        environment="expense-approval",
        description="Only EUR accepted, USD/GBP removed",
        config_changes={"supported_currencies": {"EUR"}},
    ),
]

SUPPORT_MUTATIONS = [
    MutationSpec(
        mutation_id="support-sla-tightened",
        environment="support-ticket",
        description="SLA critical deadline reduced from 1h to 30min",
        config_changes={"sla_critical_hours": 0.5},
    ),
    MutationSpec(
        mutation_id="support-refund-capped",
        environment="support-ticket",
        description="Refund limit dropped from 500 to 100",
        config_changes={"refund_limit": 100.0},
    ),
    MutationSpec(
        mutation_id="support-no-assignee-resolve",
        environment="support-ticket",
        description="No longer require assignee before resolve",
        config_changes={"require_assignee_before_resolve": False},
    ),
]

DEPLOYMENT_MUTATIONS = [
    MutationSpec(
        mutation_id="deployment-freeze-on",
        environment="deployment",
        description="Production freeze activated",
        config_changes={"production_freeze": True},
    ),
    MutationSpec(
        mutation_id="deployment-approval-off",
        environment="deployment",
        description="Production approval requirement removed",
        config_changes={"require_approval_for_production": False},
    ),
    MutationSpec(
        mutation_id="deployment-rollback-tight",
        environment="deployment",
        description="Max rollback count reduced from 3 to 1",
        config_changes={"max_rollback_count": 1},
    ),
]


def get_mutations(environment: str) -> list[MutationSpec]:
    """Get all available mutations for an environment."""
    catalogs = {
        "expense-approval": EXPENSE_MUTATIONS,
        "support-ticket": SUPPORT_MUTATIONS,
        "deployment": DEPLOYMENT_MUTATIONS,
    }
    return catalogs.get(environment, [])


def get_mutation(environment: str, mutation_id: str) -> MutationSpec | None:
    """Get a specific mutation by ID."""
    for m in get_mutations(environment):
        if m.mutation_id == mutation_id:
            return m
    return None


# ── Mutation Engine ───────────────────────────────────────────────────


def apply_mutation_to_expense(
    base: ExpenseApprovalConfig,
    changes: dict[str, Any],
) -> ExpenseApprovalConfig:
    """Apply config changes to an expense approval config."""
    kwargs: dict[str, Any] = {
        "approval_threshold": base.approval_threshold,
        "receipt_threshold": base.receipt_threshold,
        "require_receipt_for_all": base.require_receipt_for_all,
        "allow_self_approval": base.allow_self_approval,
        "supported_currencies": base.supported_currencies.copy(),
        "max_approval_limit": base.max_approval_limit,
    }
    for key, value in changes.items():
        if key in kwargs:
            kwargs[key] = value
    return ExpenseApprovalConfig(**kwargs)


def apply_mutation_to_support(
    base: SupportTicketConfig,
    changes: dict[str, Any],
) -> SupportTicketConfig:
    """Apply config changes to a support ticket config."""
    kwargs: dict[str, Any] = {
        "escalation_threshold_hours": base.escalation_threshold_hours,
        "require_assignee_before_resolve": base.require_assignee_before_resolve,
        "require_note_before_close": base.require_note_before_close,
        "max_reopen_count": base.max_reopen_count,
        "refund_limit": base.refund_limit,
    }
    for key, value in changes.items():
        if key in kwargs:
            kwargs[key] = value
    return SupportTicketConfig(**kwargs)


def apply_mutation_to_deployment(
    base: DeploymentConfig,
    changes: dict[str, Any],
) -> DeploymentConfig:
    """Apply config changes to a deployment config."""
    kwargs: dict[str, Any] = {
        "require_approval_for_production": base.require_approval_for_production,
        "require_change_window": base.require_change_window,
        "allow_self_approval": base.allow_self_approval,
        "max_rollback_count": base.max_rollback_count,
        "production_freeze": base.production_freeze,
    }
    for key, value in changes.items():
        if key in kwargs:
            kwargs[key] = value
    return DeploymentConfig(**kwargs)


def apply_mutation(
    environment: str,
    base_config: object,
    changes: dict[str, Any],
) -> object:
    """Apply a mutation to any environment config.

    Args:
        environment: Environment name.
        base_config: Current environment config object.
        changes: Dict of field_name -> new_value.

    Returns:
        New config object with mutations applied.
    """
    handlers = {
        "expense-approval": apply_mutation_to_expense,
        "support-ticket": apply_mutation_to_support,
        "deployment": apply_mutation_to_deployment,
    }
    handler = handlers.get(environment)
    if handler is None:
        raise ValueError(f"Unknown environment: {environment}")
    return handler(base_config, changes)
