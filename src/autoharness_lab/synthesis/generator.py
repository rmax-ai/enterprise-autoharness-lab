"""Initial harness code generation from environment spec.

Uses the ModelClient protocol to generate harness code. The actual
prompt templating reads from versioned prompt files.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field

from autoharness_lab.models import HarnessArtifact


class GeneratorResponse(BaseModel):
    """Structured response from the model client for harness generation."""

    model_config = {"extra": "forbid", "frozen": True}
    code: str = Field(description="Generated Python harness code")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the versioned prompts directory."""
    pkg = resources.files("autoharness_lab.synthesis")
    prompt_path = pkg / "prompts" / name
    return prompt_path.read_text()


class HarnessGenerator:
    """Generate initial harness code from an environment spec.

    Uses the ModelClient protocol to generate code and returns
    a HarnessArtifact with provenance metadata.
    """

    def __init__(self, model_client) -> None:
        self._client = model_client

    def generate(self, environment_spec: dict[str, Any]) -> HarnessArtifact:
        """Generate initial harness code for an environment.

        Args:
            environment_spec: Dict with keys:
                - name: Environment name
                - supported_actions: List of action type strings
                - state_transitions: Dict of state -> [next_states]
                - validation_rules: List of human-readable validation rules

        Returns:
            HarnessArtifact with generated code and provenance metadata.
        """
        prompt_template = _load_prompt("generate.txt")

        system_prompt = (
            "You are a Python code generation system that produces validation functions."
        )
        user_prompt = prompt_template.format(
            environment_spec=environment_spec.get("name", "unknown"),
            supported_actions="\n".join(
                f"- {a}" for a in environment_spec.get("supported_actions", [])
            ),
            state_transitions="\n".join(
                f"- {s} -> {', '.join(t)}"
                for s, t in environment_spec.get("state_transitions", {}).items()
            ),
            validation_rules="\n".join(
                f"- {r}" for r in environment_spec.get("validation_rules", [])
            ),
        )

        prompt_hash = hashlib.sha256(f"{system_prompt}{user_prompt}".encode()).hexdigest()[:16]

        response = self._client.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=GeneratorResponse,
        )

        code = response.code
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        return HarnessArtifact(
            harness_id=f"gen-{uuid.uuid4().hex[:8]}",
            environment=environment_spec["name"],
            version=0,
            lifecycle_state="GENERATED",
            code=code,
            code_hash=code_hash,
            parent_harness_id=None,
            model_name="mock",
            generation_prompt_hash=prompt_hash,
            created_at=datetime.now(UTC).isoformat(),
            static_validation={},
            evaluation_metrics={},
        )
