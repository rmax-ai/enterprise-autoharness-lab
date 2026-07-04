"""Manual harness for software-deployment workflows."""

from __future__ import annotations

from typing import Any

SUPPORTED_ACTIONS = [
    "create_deployment",
    "approve_deployment",
    "start_deployment",
    "cancel_deployment",
    "rollback_deployment",
]

CANONICAL_FIELDS = {
    "deployment_id": "deployment_id",
    "deploymentid": "deployment_id",
    "deploymentId": "deployment_id",
    "id": "deployment_id",
}

VALID_ENVIRONMENTS = {"staging", "production", "canary"}


def _normalize_field(key: str) -> str:
    return CANONICAL_FIELDS.get(key, key)


def evaluate_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
) -> dict[str, Any]:
    action_type = proposed_action.get("type", "")
    args = proposed_action.get("arguments", {})
    normalized_args = {_normalize_field(k): v for k, v in args.items()}

    if action_type not in SUPPORTED_ACTIONS:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": f"Unknown action type: {action_type}",
            "confidence": 0.99,
        }

    # create_deployment needs service + environment, not deployment_id lookup
    if action_type == "create_deployment":
        service = normalized_args.get("service", "")
        if not service:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Missing required field: service",
                "confidence": 0.95,
            }
        environment = normalized_args.get("environment", "")
        if environment not in VALID_ENVIRONMENTS:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Invalid environment: {environment}",
                "confidence": 0.95,
            }
        return {
            "accepted": True,
            "normalized_action": {"type": action_type, "arguments": normalized_args},
            "reason": "Action is operationally valid",
            "confidence": 0.85,
        }

    # All other actions need deployment_id
    if "deployment_id" not in normalized_args:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": "Missing required field: deployment_id",
            "confidence": 0.99,
        }

    dep_id = normalized_args["deployment_id"]
    deployments = observation.get("deployments", {})
    deployment = deployments.get(dep_id)

    if deployment is None:
        return {
            "accepted": False,
            "normalized_action": None,
            "reason": f"Deployment {dep_id} not found",
            "confidence": 0.99,
        }

    dep_state = deployment.get("state", "")

    if action_type == "approve_deployment":
        if dep_state != "created":
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot approve deployment in state: {dep_state}",
                "confidence": 0.95,
            }
        approver = normalized_args.get("approver", "")
        if approver and approver == deployment.get("creator", ""):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": "Self-approval is not allowed",
                "confidence": 0.99,
            }

    elif action_type == "start_deployment":
        if dep_state != "approved":
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot start deployment in state: {dep_state}",
                "confidence": 0.95,
            }

    elif action_type == "cancel_deployment":
        if dep_state in ("completed", "cancelled"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot cancel deployment in state: {dep_state}",
                "confidence": 0.95,
            }

    elif action_type == "rollback_deployment":
        if dep_state not in ("started", "completed"):
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Cannot rollback deployment in state: {dep_state}",
                "confidence": 0.95,
            }

    return {
        "accepted": True,
        "normalized_action": {"type": action_type, "arguments": normalized_args},
        "reason": "Action is operationally valid",
        "confidence": 0.85,
    }


def repair_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
    failure: dict[str, Any],
) -> dict[str, Any] | None:
    return None
