"""Harness refinement from execution counterexamples.

Takes a current harness and counterexamples from failed executions,
produces an improved harness via the model client.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field

from autoharness_lab.models import HarnessArtifact


class RefinerResponse(BaseModel):
    """Structured response from the model client for harness refinement."""

    model_config = {"extra": "forbid", "frozen": True}
    code: str = Field(description="Refined Python harness code")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the versioned prompts directory."""
    pkg = resources.files("autoharness_lab.synthesis")
    prompt_path = pkg / "prompts" / name
    return prompt_path.read_text()


class HarnessRefiner:
    """Refine a harness using counterexamples from execution failures.

    Uses the ModelClient protocol to generate improved code based on
    what the current harness gets wrong.
    """

    def __init__(self, model_client) -> None:
        self._client = model_client

    def refine(
        self,
        current_code: str,
        counterexamples: list[dict[str, Any]],
        environment: str,
        parent_harness_id: str | None = None,
    ) -> HarnessArtifact:
        """Refine harness code based on counterexamples.

        Args:
            current_code: Current harness source code.
            counterexamples: List of failure dicts from extract_counterexamples().
            environment: Environment name.
            parent_harness_id: ID of the harness being refined.

        Returns:
            HarnessArtifact with refined code.
        """
        prompt_template = _load_prompt("refine.txt")

        ce_str = json.dumps(counterexamples, indent=2, default=str)
        if len(ce_str) > 4000:
            ce_str = ce_str[:4000] + "\n... [truncated]"

        user_prompt = prompt_template.format(
            current_code=current_code,
            counterexamples=ce_str,
        )

        system_prompt = "You are a Python code refinement system."

        prompt_hash = hashlib.sha256(f"{system_prompt}{user_prompt}".encode()).hexdigest()[:16]

        response = self._client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=RefinerResponse,
        )

        code = response.code
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        return HarnessArtifact(
            harness_id=f"ref-{uuid.uuid4().hex[:8]}",
            environment=environment,
            version=0,
            lifecycle_state="GENERATED",
            code=code,
            code_hash=code_hash,
            parent_harness_id=parent_harness_id,
            model_name="mock",
            generation_prompt_hash=prompt_hash,
            created_at=datetime.now(UTC).isoformat(),
            static_validation={},
            evaluation_metrics={},
        )
