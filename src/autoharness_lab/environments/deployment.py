"""Software-deployment workflow environment with full state machine.

Implements the Environment protocol from autoharness_lab.models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from autoharness_lab.models import Action, ExecutionResult

# ── Domain Types ──────────────────────────────────────────────────────


class DeploymentState(StrEnum):
    DRAFT = "draft"
    CREATED = "created"
    APPROVED = "approved"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


SUPPORTED_ACTIONS = [
    "create_deployment",
    "approve_deployment",
    "start_deployment",
    "cancel_deployment",
    "rollback_deployment",
]

VALID_ENVIRONMENTS = {"staging", "production", "canary"}

# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class Deployment:
    """A single software deployment."""

    deployment_id: str
    service: str
    version: str
    environment: str  # staging / production / canary
    creator: str
    state: DeploymentState = DeploymentState.DRAFT
    approver: str | None = None
    checks_passed: bool = False
    created_at: str | None = None
    approved_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    change_description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "service": self.service,
            "version": self.version,
            "environment": self.environment,
            "creator": self.creator,
            "state": self.state.value,
            "approver": self.approver,
            "checks_passed": self.checks_passed,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "change_description": self.change_description,
        }


@dataclass
class DeploymentConfig:
    """Configuration for the deployment environment."""

    require_checks: bool = True
    require_approval: bool = True
    allow_self_approval: bool = False
    freeze_windows: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"environment": "production", "start": "2024-12-20", "end": "2025-01-05"},
        ]
    )
    require_manager_for_rollback: bool = True


# ── Environment Implementation ────────────────────────────────────────


class DeploymentEnvironment:
    """Software-deployment workflow environment.

    Implements the Environment protocol.
    """

    name = "deployment"

    def __init__(self, config: DeploymentConfig | None = None):
        self.config = config or DeploymentConfig()
        self._deployments: dict[str, Deployment] = {}
        self._seed: int = 0

    # ── Environment Protocol ──────────────────────────────────────────

    def reset(self, seed: int) -> dict[str, Any]:
        """Reset environment for a new seed."""
        self._seed = seed
        self._deployments = {}

        rng_state = seed
        deployments = [
            Deployment(
                deployment_id=f"dep-{rng_state:04d}",
                service="payments-api",
                version="v2.4.1",
                environment="staging",
                creator="alice",
                state=DeploymentState.DRAFT,
                change_description="Fix payment gateway timeout handling",
            ),
            Deployment(
                deployment_id=f"dep-{rng_state + 1:04d}",
                service="auth-service",
                version="v3.1.0",
                environment="production",
                creator="bob",
                state=DeploymentState.CREATED,
                checks_passed=True,
                created_at=datetime.now(UTC).isoformat(),
                change_description="New OIDC provider integration",
            ),
            Deployment(
                deployment_id=f"dep-{rng_state + 2:04d}",
                service="user-dashboard",
                version="v1.9.3",
                environment="canary",
                creator="charlie",
                state=DeploymentState.DRAFT,
                change_description="Dashboard performance improvements",
            ),
        ]
        for d in deployments:
            self._deployments[d.deployment_id] = d

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
            "create_deployment": self._handle_create,
            "approve_deployment": self._handle_approve,
            "start_deployment": self._handle_start,
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
                "require_checks": self.config.require_checks,
                "require_approval": self.config.require_approval,
                "allow_self_approval": self.config.allow_self_approval,
                "freeze_windows": list(self.config.freeze_windows),
                "require_manager_for_rollback": self.config.require_manager_for_rollback,
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _require_deployment(
        self, args: dict[str, Any]
    ) -> Deployment | ExecutionResult:
        """Validate deployment_id and return the deployment or an error result."""
        dep_id = args.get("deployment_id")
        if not dep_id:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_DEPLOYMENT_ID",
                message="deployment_id is required",
            )
        dep = self._deployments.get(dep_id)
        if dep is None:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="DEPLOYMENT_NOT_FOUND",
                message=f"Deployment {dep_id} not found",
            )
        return dep

    def _in_freeze_window(self, environment: str) -> bool:
        """Check if the given environment is in a freeze window."""
        now = datetime.now(UTC).date()
        for fw in self.config.freeze_windows:
            if fw["environment"] == environment:
                start = datetime.fromisoformat(fw["start"]).date()
                end = datetime.fromisoformat(fw["end"]).date()
                if start <= now <= end:
                    return True
        return False

    # ── Action Handlers ────────────────────────────────────────────────

    def _handle_create(self, args: dict[str, Any]) -> ExecutionResult:
        """Create a new deployment."""
        dep_id = args.get("deployment_id", f"dep-{self._seed + len(self._deployments):04d}")
        service = args.get("service", "")
        environment = args.get("environment", "")
        creator = args.get("creator", "unknown")

        if not service:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="MISSING_SERVICE",
                message="service is required",
            )

        if environment not in VALID_ENVIRONMENTS:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_ENVIRONMENT",
                message=(
                    f"Invalid environment: {environment}. "
                    f"Must be one of {sorted(VALID_ENVIRONMENTS)}"
                ),
            )

        deployment = Deployment(
            deployment_id=dep_id,
            service=service,
            version=args.get("version", "latest"),
            environment=environment,
            creator=creator,
            state=DeploymentState.CREATED,
            created_at=datetime.now(UTC).isoformat(),
            change_description=args.get("change_description", ""),
        )
        self._deployments[dep_id] = deployment

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep_id} created for {service} to {environment}",
            reward=0.1,
        )

    def _handle_approve(self, args: dict[str, Any]) -> ExecutionResult:
        """Approve a deployment."""
        result = self._require_deployment(args)
        if isinstance(result, ExecutionResult):
            return result
        dep = result

        if dep.state != DeploymentState.CREATED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot approve deployment in state: {dep.state.value}",
            )

        if self.config.require_checks and not dep.checks_passed:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="CHECKS_NOT_PASSED",
                message="Required checks have not passed",
            )

        approver = args.get("approver", "unknown")
        dep.approver = approver
        dep.state = DeploymentState.APPROVED
        dep.approved_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep.deployment_id} approved by {approver}",
            reward=0.3,
        )

    def _handle_start(self, args: dict[str, Any]) -> ExecutionResult:
        """Start a deployment to the target environment."""
        result = self._require_deployment(args)
        if isinstance(result, ExecutionResult):
            return result
        dep = result

        if dep.state != DeploymentState.APPROVED:
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot start deployment in state: {dep.state.value}",
            )

        # Production freeze check
        if self._in_freeze_window(dep.environment):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="FREEZE_WINDOW",
                message=(
                    f"Environment {dep.environment} is in a freeze window. "
                    "Deployments are blocked."
                ),
            )

        dep.state = DeploymentState.STARTED
        dep.started_at = datetime.now(UTC).isoformat()

        # Auto-complete for staging/canary (safety: production stays started)
        if dep.environment != "production":
            dep.state = DeploymentState.COMPLETED
            dep.completed_at = datetime.now(UTC).isoformat()

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep.deployment_id} started to {dep.environment}",
            reward=0.5,
        )

    def _handle_cancel(self, args: dict[str, Any]) -> ExecutionResult:
        """Cancel a deployment."""
        result = self._require_deployment(args)
        if isinstance(result, ExecutionResult):
            return result
        dep = result

        if dep.state in (DeploymentState.COMPLETED, DeploymentState.CANCELLED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot cancel deployment in state: {dep.state.value}",
            )

        dep.state = DeploymentState.CANCELLED

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep.deployment_id} cancelled",
            reward=0.1,
        )

    def _handle_rollback(self, args: dict[str, Any]) -> ExecutionResult:
        """Roll back a deployment."""
        result = self._require_deployment(args)
        if isinstance(result, ExecutionResult):
            return result
        dep = result

        if dep.state not in (DeploymentState.STARTED, DeploymentState.COMPLETED):
            return ExecutionResult(
                status="invalid_action",
                observation=self.state_snapshot(),
                error_code="INVALID_STATE",
                message=f"Cannot rollback deployment in state: {dep.state.value}",
            )

        dep.state = DeploymentState.ROLLED_BACK

        return ExecutionResult(
            status="success",
            observation=self.state_snapshot(),
            message=f"Deployment {dep.deployment_id} rolled back",
            reward=0.3,
        )
