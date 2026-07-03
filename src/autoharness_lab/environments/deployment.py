"""Deployment workflow environment with full state machine.

Models a software deployment pipeline with approval gates,
change windows, and rollback capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from autoharness_lab.models import Action, ExecutionResult


class DeploymentState(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    DEPLOYED = "deployed"
    VERIFIED = "verified"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


SUPPORTED_ACTIONS = [
    "create_deployment",
    "approve_deployment",
    "start_deployment",
    "verify_deployment",
    "cancel_deployment",
    "rollback_deployment",
]


@dataclass
class DeploymentItem:
    deployment_id: str
    service: str
    version: str
    description: str
    environment: str  # staging, production
    requester: str
    state: DeploymentState = DeploymentState.DRAFT
    approver: str | None = None
    risk_level: str = "low"  # low, medium, high
    change_window: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "service": self.service,
            "version": self.version,
            "description": self.description,
            "environment": self.environment,
            "requester": self.requester,
            "state": self.state.value,
            "approver": self.approver,
            "risk_level": self.risk_level,
            "change_window": self.change_window,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class DeploymentConfig:
    require_approval_for_production: bool = True
    require_change_window: bool = True
    allow_self_approval: bool = False
    max_rollback_count: int = 3
    production_freeze: bool = False  # When true, no production deploys allowed


class DeploymentEnvironment:
    """Deployment workflow environment."""

    name = "deployment"

    def __init__(self, config: DeploymentConfig | None = None):
        self.config = config or DeploymentConfig()
        self._deployments: dict[str, DeploymentItem] = {}
        self._seed: int = 0
        self._rollback_counts: dict[str, int] = {}

    def reset(self, seed: int) -> dict[str, Any]:
        self._seed = seed
        self._deployments = {}
        self._rollback_counts = {}

        deps = [
            DeploymentItem(
                deployment_id=f"dep-{seed:04d}",
                service="payment-api",
                version="v2.4.1",
                description="Fix payment timeout issue",
                environment="staging",
                requester="dev_alex",
            ),
            DeploymentItem(
                deployment_id=f"dep-{seed + 1:04d}",
                service="auth-service",
                version="v3.1.0",
                description="OAuth2 provider migration",
                environment="production",
                requester="dev_blake",
                risk_level="high",
            ),
            DeploymentItem(
                deployment_id=f"dep-{seed + 2:04d}",
                service="user-dashboard",
                version="v1.8.3",
                description="New analytics widgets",
                environment="staging",
                requester="dev_alex",
                state=DeploymentState.APPROVED,
                approver="manager_carol",
            ),
        ]
        for d in deps:
            self._deployments[d.deployment_id] = d

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
            "create_deployment": self._handle_create,
            "approve_deployment": self._handle_approve,
            "start_deployment": self._handle_start,
            "verify_deployment": self._handle_verify,
            "cancel_deployment": self._handle_cancel,
            "rollback_deployment": self._handle_rollback,
        }
        return handlers[action_type](args)

    def available_action_types(self) -> list[str]:
        return SUPPORTED_ACTIONS.copy()

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "deployments": {did: d.to_dict() for did, d in self._deployments.items()},
            "config": {
                "require_approval_for_production": self.config.require_approval_for_production,
                "require_change_window": self.config.require_change_window,
                "allow_self_approval": self.config.allow_self_approval,
                "max_rollback_count": self.config.max_rollback_count,
                "production_freeze": self.config.production_freeze,
            },
        }

    def _get_dep(self, args: dict[str, Any]) -> DeploymentItem | None:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return None
        return self._deployments.get(dep_id)

    def _missing_id(self) -> ExecutionResult:
        return ExecutionResult(
            status="invalid_action",
            observation=self.state_snapshot(),
            error_code="MISSING_DEPLOYMENT_ID",
            message="deployment_id is required",
        )

    def _not_found(self, dep_id: str) -> ExecutionResult:
        return ExecutionResult(
            status="invalid_action",
            observation=self.state_snapshot(),
            error_code="DEPLOYMENT_NOT_FOUND",
            message=f"Deployment {dep_id} not found",
        )

    def _handle_create(self, args: dict[str, Any]) -> ExecutionResult:
        service = args.get("service", "")
        version = args.get("version", "")
        environment = args.get("environment", "staging")

        if not service or not version:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_FIELDS",
                message="service and version are required",
            )

        if environment not in ("staging", "production"):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_ENVIRONMENT",
                message=f"Invalid environment: {environment}",
            )

        # Production freeze check
        if environment == "production" and self.config.production_freeze:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="PRODUCTION_FREEZE",
                message="Production deployments are currently frozen",
            )

        dep_id = f"dep-{len(self._deployments):04d}"
        dep = DeploymentItem(
            deployment_id=dep_id,
            service=service,
            version=version,
            description=args.get("description", ""),
            environment=environment,
            requester=args.get("requester", "unknown"),
        )
        self._deployments[dep_id] = dep

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} created for {service} {version}",
            reward=0.1,
        )

    def _handle_approve(self, args: dict[str, Any]) -> ExecutionResult:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return self._missing_id()

        dep = self._deployments.get(dep_id)
        if dep is None:
            return self._not_found(dep_id)

        if dep.state != DeploymentState.DRAFT:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot approve deployment in state: {dep.state.value}",
            )

        approver = args.get("approver", "")
        if not approver:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_APPROVER",
                message="approver is required",
            )

        # Self-approval check
        if not self.config.allow_self_approval and approver == dep.requester:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="SELF_APPROVAL",
                message="Cannot self-approve deployment",
            )

        # Production requires change window
        if (
            dep.environment == "production"
            and self.config.require_change_window
            and not args.get("change_window")
        ):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="NO_CHANGE_WINDOW",
                message="Production deployment requires a change window",
            )

        dep.state = DeploymentState.APPROVED
        dep.approver = approver
        dep.change_window = args.get("change_window")

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} approved by {approver}",
            reward=0.2,
        )

    def _handle_start(self, args: dict[str, Any]) -> ExecutionResult:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return self._missing_id()

        dep = self._deployments.get(dep_id)
        if dep is None:
            return self._not_found(dep_id)

        if dep.state != DeploymentState.APPROVED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot start deployment in state: {dep.state.value}",
            )

        # Production requires approval
        if (
            dep.environment == "production"
            and self.config.require_approval_for_production
            and not dep.approver
        ):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="UNAPPROVED",
                message="Production deployment requires approval before starting",
            )

        dep.state = DeploymentState.IN_PROGRESS
        dep.started_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} started",
            reward=0.15,
        )

    def _handle_verify(self, args: dict[str, Any]) -> ExecutionResult:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return self._missing_id()

        dep = self._deployments.get(dep_id)
        if dep is None:
            return self._not_found(dep_id)

        if dep.state not in (DeploymentState.DEPLOYED, DeploymentState.IN_PROGRESS):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot verify deployment in state: {dep.state.value}",
            )

        # Auto-transition to deployed if in progress
        if dep.state == DeploymentState.IN_PROGRESS:
            dep.state = DeploymentState.DEPLOYED

        dep.state = DeploymentState.VERIFIED
        dep.completed_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} verified",
            reward=0.3,
        )

    def _handle_cancel(self, args: dict[str, Any]) -> ExecutionResult:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return self._missing_id()

        dep = self._deployments.get(dep_id)
        if dep is None:
            return self._not_found(dep_id)

        if dep.state in (DeploymentState.DEPLOYED, DeploymentState.VERIFIED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot cancel {dep.state.value} deployment",
            )

        dep.state = DeploymentState.CANCELLED
        dep.completed_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} cancelled",
            reward=0.1,
        )

    def _handle_rollback(self, args: dict[str, Any]) -> ExecutionResult:
        dep_id = args.get("deployment_id")
        if not dep_id:
            return self._missing_id()

        dep = self._deployments.get(dep_id)
        if dep is None:
            return self._not_found(dep_id)

        if dep.state not in (DeploymentState.DEPLOYED, DeploymentState.VERIFIED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot rollback deployment in state: {dep.state.value}",
            )

        # Rollback count limit
        count = self._rollback_counts.get(dep.service, 0)
        if count >= self.config.max_rollback_count:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MAX_ROLLBACKS",
                message=(
                    f"Service {dep.service} has reached max rollback limit "
                    f"({self.config.max_rollback_count})"
                ),
            )

        dep.state = DeploymentState.ROLLED_BACK
        dep.completed_at = datetime.now(UTC).isoformat()
        self._rollback_counts[dep.service] = count + 1

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} rolled back",
            reward=0.05,
        )
