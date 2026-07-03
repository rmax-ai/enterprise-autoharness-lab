"""Gemini 2.5 Flash agent implementation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from autoharness_lab.models import Action

logger = structlog.get_logger(__name__)


class ActionResponse(BaseModel):
    """Thin wrapper for Gemini structured output deserialization."""

    type: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class GeminiAgent:
    """LLM-powered agent using Gemini 2.5 Flash."""

    name = "gemini"

    def __init__(self, client=None, system_prompt: str | None = None):
        # Lazy import, only load google-genai when GeminiAgent is actually used.
        from autoharness_lab.model_clients.gemini import GeminiModelClient

        self._client = client or GeminiModelClient()
        self._system_prompt = system_prompt or self._load_prompt()
        self._prompt_hash = hashlib.sha256(self._system_prompt.encode("utf-8")).hexdigest()
        logger.info("gemini_prompt_loaded", prompt_sha256=self._prompt_hash)

    @staticmethod
    def _load_prompt() -> str:
        """Load the versioned system prompt from disk."""
        prompt_path = (
            Path(__file__).resolve().parents[1] / "synthesis" / "prompts" / "expense_agent_v1.txt"
        )
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_prompt(
        self, task: str, observation: dict[str, Any], available_actions: list[str]
    ) -> str:
        """Build the user prompt with task context, observation, and available actions."""
        return json.dumps(
            {
                "task": task,
                "observation": observation,
                "available_actions": available_actions,
            },
            indent=2,
        )

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose the next action using Gemini."""
        user_prompt = self._build_user_prompt(task, observation, available_actions)

        try:
            result = self._client.generate_structured(
                system_prompt=self._system_prompt,
                user_prompt=user_prompt,
                response_schema=ActionResponse,
            )

            if result.type not in available_actions:
                logger.warning(
                    "gemini_invalid_action_type",
                    returned=result.type,
                    available=available_actions,
                )
                return self._fallback_action(observation)

            expense_id = result.arguments.get("expense_id")
            if expense_id and expense_id not in observation.get("expenses", {}):
                logger.warning("gemini_bad_expense_id", expense_id=expense_id)
                return self._fallback_action(observation)

            return Action(type=result.type, arguments=result.arguments)

        except Exception as e:
            logger.warning("gemini_propose_action_failed", error=str(e))
            return self._fallback_action(observation)

    @staticmethod
    def _fallback_action(observation: dict[str, Any]) -> Action:
        """Return a safe action when Gemini fails."""
        expenses = observation.get("expenses", {})
        for eid, exp in expenses.items():
            if exp.get("state") == "draft" and not exp.get("has_receipt"):
                return Action(type="request_receipt", arguments={"expense_id": eid})

        for eid, exp in expenses.items():
            if exp.get("state") == "draft":
                return Action(type="submit_expense", arguments={"expense_id": eid})

        actor_id = observation.get("actor", {}).get("user_id", "gemini")
        for eid, exp in expenses.items():
            if exp.get("state") == "submitted":
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": actor_id},
                )

        return Action(type="submit_expense", arguments={"expense_id": "none"})
