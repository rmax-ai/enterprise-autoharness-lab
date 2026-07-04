"""Authoritative policy engine for software deployments.

The policy engine is the FINAL authority on permissions. Harness acceptance
never implies policy authorization. This invariant must be tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from autoharness_lab.models import PolicyDecision


@dataclass(frozen=True)
class PolicyRule:
    """A single policy rule."""

    rule_id: str
    description: str
    priority: int


# ── Built-in Rules ────────────────────────────────────────────────────

RULE_NO_SELF_APPROVAL = PolicyRule(
    rule_id="DEPLOY-001",
    description="A developer cannot approve their own deployment",
    priority=1,
)

RULE_PRODUCTION_FREEZE = PolicyRule(
    rule_id="DEPLOY-002",
    description="Deployments to production are blocked during freeze windows",
    priority=2,
)

RULE_REQUIRED_CHECKS = PolicyRule(
    rule_id="DEPLOY-003",
    description="All required checks must pass before deployment approval",
    priority=3,
)

RULE_ROLLBACK_AUTHORIZATION = PolicyRule(
    rule_id="DEPLOY-004",
    description="Production rollbacks require manager authorization",
    priority=4,
)

RULE_NO_CANCEL_COMPLETED = PolicyRule(
    rule_id="DEPLOY-005",
    description="A completed deployment cannot be cancelled",
    priority=5,
)

RULE_START_REQUIRES_APPROVAL = PolicyRule(
    rule_id="DEPLOY-006",
    description="A deployment must be approved before it can be started",
    priority=6,
)


# ── Policy Engine ─────────────────────────────────────────────────────


class DeploymentPolicyEngine:
    """Authoritative policy engine for deployment workflows.

    This engine is the FINAL authority. Even if the synthesized harness
    accepts an action, this engine may deny it based on business policy.
    """

    def __init__(
        self,
        *,
        require_checks: bool = True,
        require_approval: bool = True,
        require_manager_for_rollback: bool = True,
    ):
        self.require_checks = require_checks
        self.require_approval = require_approval
        self.require_manager_for_rollback = require_manager_for_rollback

    def evaluate(
        self,
        actor: dict[str, Any],
        action: dict[str, Any],
        deployment: dict[str, Any] | None,
    ) -> PolicyDecision:
        """Evaluate whether an action is authorized by policy.

        Args:
            actor: Actor info dict (must include 'user_id' and 'role')
            action: Proposed action dict (must include 'type')
            deployment: Deployment state dict if applicable, or None

        Returns:
            PolicyDecision with allowed flag and rule reference.
        """
        action_type = action.get("type", "")
        actor_user = actor.get("user_id", "")
        actor_role = actor.get("role", "developer")

        # ── Approve checks ─────────────────────────────────────────
        if action_type == "approve_deployment":
            if deployment is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="DEPLOY-000",
                    reason="Cannot approve without a deployment",
                )

            # DEPLOY-001: No self-approval
            if deployment.get("creator") == actor_user:
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_NO_SELF_APPROVAL.rule_id,
                    reason=RULE_NO_SELF_APPROVAL.description,
                )

            # DEPLOY-003: Required checks
            if self.require_checks and not deployment.get("checks_passed", False):
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_REQUIRED_CHECKS.rule_id,
                    reason=RULE_REQUIRED_CHECKS.description,
                )

        # ── Start checks ───────────────────────────────────────────
        if action_type == "start_deployment":
            if deployment is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="DEPLOY-000",
                    reason="Cannot start without a deployment",
                )

            # DEPLOY-006: Must be approved
            if self.require_approval and deployment.get("state") != "approved":
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_START_REQUIRES_APPROVAL.rule_id,
                    reason=RULE_START_REQUIRES_APPROVAL.description,
                )

            # DEPLOY-002: Production freeze
            if (
                deployment.get("environment") == "production"
                and self._in_freeze_window()
            ):
                    return PolicyDecision(
                        allowed=False,
                        rule_id=RULE_PRODUCTION_FREEZE.rule_id,
                        reason=RULE_PRODUCTION_FREEZE.description,
                    )

        # ── Cancel checks ──────────────────────────────────────────
        if action_type == "cancel_deployment":
            if deployment is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="DEPLOY-000",
                    reason="Cannot cancel without a deployment",
                )

            # DEPLOY-005: Cannot cancel completed
            if deployment.get("state") == "completed":
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_NO_CANCEL_COMPLETED.rule_id,
                    reason=RULE_NO_CANCEL_COMPLETED.description,
                )

        # ── Rollback checks ────────────────────────────────────────
        if action_type == "rollback_deployment":
            if deployment is None:
                return PolicyDecision(
                    allowed=False,
                    rule_id="DEPLOY-000",
                    reason="Cannot rollback without a deployment",
                )

            # DEPLOY-004: Production rollback requires manager
            if (
                self.require_manager_for_rollback
                and deployment.get("environment") == "production"
                and actor_role not in ("manager", "admin")
            ):
                return PolicyDecision(
                    allowed=False,
                    rule_id=RULE_ROLLBACK_AUTHORIZATION.rule_id,
                    reason=RULE_ROLLBACK_AUTHORIZATION.description,
                )

        return PolicyDecision(
            allowed=True,
            rule_id="DEPLOY-000",
            reason="Action authorized",
        )

    def _in_freeze_window(self) -> bool:
        """Check if we're currently in a production freeze window."""
        now = datetime.now(UTC).date()
        # Dec 20 - Jan 5 is a standard freeze window
        freeze_start = datetime(2025, 12, 20).date()
        freeze_end = datetime(2026, 1, 5).date()
        return freeze_start <= now <= freeze_end
