"""Authoritative policy engine for deployment workflows."""

from __future__ import annotations

from typing import Any

from autoharness_lab.models import PolicyDecision


class DeploymentPolicyEngine:
    """Policy engine for deployment workflows.

    Enforces:
    - DEP-001: Production deployments require separate approver
    - DEP-002: High-risk deployments need manager sign-off
    - DEP-003: Production freeze blocks all production activity
    - DEP-004: Rollback requires manager auth for production
    - DEP-005: Cannot cancel verified deployments
    """

    def __init__(
        self,
        *,
        require_approval_for_production: bool = True,
        production_freeze: bool = False,
    ):
        self.require_approval_for_production = require_approval_for_production
        self.production_freeze = production_freeze

    def evaluate(
        self,
        actor: dict[str, Any],
        action: dict[str, Any],
        deployment: dict[str, Any] | None,
    ) -> PolicyDecision:
        action_type = action.get("type", "")
        actor_role = actor.get("role", "developer")
        actor_id = actor.get("user_id", "")

        # DEP-001: Production deployments need separate approver
        if (
            action_type == "approve_deployment"
            and deployment
            and self.require_approval_for_production
            and deployment.get("requester") == actor_id
        ):
            return PolicyDecision(
                allowed=False,
                rule_id="DEP-001",
                reason="Cannot self-approve deployment",
            )

        # DEP-002: High-risk needs manager
        if (
            action_type in ("start_deployment", "approve_deployment")
            and deployment
            and deployment.get("risk_level") == "high"
            and actor_role not in ("manager", "admin")
        ):
            return PolicyDecision(
                allowed=False,
                rule_id="DEP-002",
                reason="High-risk deployment requires manager approval",
            )

        # DEP-003: Production freeze
        if (
            self.production_freeze
            and deployment
            and deployment.get("environment") == "production"
            and action_type not in ("rollback_deployment",)
        ):
            return PolicyDecision(
                allowed=False,
                rule_id="DEP-003",
                reason="Production deployments are frozen",
            )

        # DEP-004: Production rollback needs manager
        if (
            action_type == "rollback_deployment"
            and deployment
            and deployment.get("environment") == "production"
            and actor_role not in ("manager", "admin")
        ):
            return PolicyDecision(
                allowed=False,
                rule_id="DEP-004",
                reason="Production rollback requires manager authorization",
            )

        # DEP-005: Cannot cancel verified
        if (
            action_type == "cancel_deployment"
            and deployment
            and deployment.get("state") == "verified"
        ):
            return PolicyDecision(
                allowed=False,
                rule_id="DEP-005",
                reason="Cannot cancel verified deployment",
            )

        return PolicyDecision(
            allowed=True,
            rule_id="DEP-000",
            reason="Action authorized",
        )
