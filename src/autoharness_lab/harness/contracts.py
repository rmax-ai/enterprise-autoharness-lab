"""Harness contracts and runtime for AutoHarness Lab.

The harness is deterministic code that predicts whether an action is
operationally valid. It does NOT replace the policy engine.

Generated harnesses must implement the evaluate_action contract.
"""

from __future__ import annotations

from typing import Any

# ── Harness Contract ──────────────────────────────────────────────────


def harness_contract_evaluate_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
) -> dict[str, Any]:
    """Reference contract that all harnesses must satisfy.

    Returns:
        {
            "accepted": bool,
            "normalized_action": dict | None,
            "reason": str,
            "confidence": float | None,
        }
    """
    return {
        "accepted": False,
        "normalized_action": None,
        "reason": "Base harness — override in implementation",
        "confidence": None,
    }


def harness_contract_repair_action(
    observation: dict[str, Any],
    proposed_action: dict[str, Any],
    failure: dict[str, Any],
) -> dict[str, Any] | None:
    """Optional repair contract. Return repaired action or None."""
    return None


# ── Harness Runtime ───────────────────────────────────────────────────


class HarnessRuntime:
    """Wraps a generated harness function for safe execution.

    Handles calling evaluate_action and repair_action with proper
    error handling and normalization of return values.
    """

    def __init__(self, harness_module):
        self._module = harness_module

    def evaluate(
        self, observation: dict[str, Any], proposed_action: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate an action through the harness.

        Always returns a dict with the standard contract shape,
        even if the harness throws.
        """
        try:
            result = self._module.evaluate_action(observation, proposed_action)
            # Normalize to standard shape
            return {
                "accepted": bool(result.get("accepted", False)),
                "normalized_action": result.get("normalized_action"),
                "reason": str(result.get("reason", "")),
                "confidence": (
                    float(result["confidence"]) if result.get("confidence") is not None else None
                ),
            }
        except Exception as e:
            return {
                "accepted": False,
                "normalized_action": None,
                "reason": f"Harness error: {e}",
                "confidence": None,
            }

    def repair(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
        failure: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Attempt to repair an action through the harness."""
        try:
            if hasattr(self._module, "repair_action"):
                result = self._module.repair_action(observation, proposed_action, failure)
                return result
        except Exception:
            pass
        return None
