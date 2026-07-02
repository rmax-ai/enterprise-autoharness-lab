"""Core domain models for Enterprise AutoHarness Lab.

All shared Pydantic models, protocols, and type aliases live here.
No framework dependencies. No I/O. Pure data contracts.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


# ── Action ───────────────────────────────────────────────────────────

class Action(BaseModel):
    """An action proposed by an agent for execution in an environment."""

    model_config = {"extra": "forbid", "frozen": True}

    type: str
    arguments: dict[str, Any] = Field(default_factory=dict)


# ── Execution Result ──────────────────────────────────────────────────

ExecutionStatus = Literal[
    "success",
    "invalid_action",
    "policy_denied",
    "runtime_error",
]


class ExecutionResult(BaseModel):
    """Result of executing an action in an environment."""

    model_config = {"extra": "forbid", "frozen": True}

    status: ExecutionStatus
    observation: dict[str, Any]
    error_code: str | None = None
    message: str | None = None
    reward: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Harness ──────────────────────────────────────────────────────────

class HarnessDecision(BaseModel):
    """Decision from the synthesized harness about an action's validity."""

    model_config = {"extra": "forbid", "frozen": True}

    accepted: bool
    normalized_action: Action | None = None
    reason: str
    confidence: float | None = None


# ── Policy ────────────────────────────────────────────────────────────

class PolicyDecision(BaseModel):
    """Authoritative decision from the policy engine.

    The policy engine is the final authority. Harness acceptance never
    implies policy authorization. This invariant must be tested.
    """

    model_config = {"extra": "forbid", "frozen": True}

    allowed: bool
    rule_id: str
    reason: str


# ── Attempt Record ────────────────────────────────────────────────────

class AttemptRecord(BaseModel):
    """A single execution step trace."""

    model_config = {"extra": "forbid"}

    run_id: str
    scenario_id: str
    environment: str
    agent: str
    harness_version: str | None = None
    observation: dict[str, Any]
    proposed_action: Action
    harness_decision: HarnessDecision | None = None
    policy_decision: PolicyDecision | None = None
    execution_result: ExecutionResult
    step_index: int


# ── Counterexample ────────────────────────────────────────────────────

class Counterexample(BaseModel):
    """A structured failure used to refine the harness."""

    model_config = {"extra": "forbid", "frozen": True}

    observation: dict[str, Any]
    proposed_action: Action
    expected_classification: str
    actual_result: ExecutionResult
    error_code: str | None = None
    explanation: str


# ── Failure Classification ───────────────────────────────────────────

FailureClass = Literal[
    "malformed_action",
    "unknown_action_type",
    "invalid_state_transition",
    "missing_required_data",
    "policy_denial",
    "execution_error",
    "false_harness_rejection",
    "false_harness_acceptance",
    "unrecoverable_task_failure",
]


# ── Scenario ──────────────────────────────────────────────────────────

class Scenario(BaseModel):
    """A test scenario for evaluation."""

    model_config = {"extra": "forbid", "frozen": True}

    scenario_id: str
    task: str
    initial_state: dict[str, Any]
    actor: dict[str, Any]
    expected_outcome: dict[str, Any]
    max_steps: int
    tags: list[str] = Field(default_factory=list)


# ── Harness Artifact ──────────────────────────────────────────────────

class HarnessArtifact(BaseModel):
    """Metadata for a stored harness version."""

    model_config = {"extra": "forbid", "frozen": True}

    harness_id: str
    environment: str
    version: int
    lifecycle_state: str  # GENERATED → ... → ACTIVE → RETIRED
    code: str
    code_hash: str
    parent_harness_id: str | None = None
    model_name: str
    generation_prompt_hash: str
    created_at: str
    static_validation: dict[str, Any] = Field(default_factory=dict)
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None


# ── Environment Protocol ──────────────────────────────────────────────

class Environment(Protocol):
    """Protocol for workflow environments.

    Environments are stateful — they maintain the current state and
    expose it via state_snapshot(). Actions mutate state through execute().
    """

    name: str

    def reset(self, seed: int) -> dict[str, Any]:
        """Reset environment to initial state for the given seed.

        Returns the initial observation.
        """
        ...

    def execute(self, action: Action) -> ExecutionResult:
        """Execute an action and return the result.

        Mutates internal state. Returns structured ExecutionResult.
        """
        ...

    def available_action_types(self) -> list[str]:
        """Return the list of action type strings this environment supports."""
        ...

    def state_snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of current environment state."""
        ...


# ── Agent Protocol ────────────────────────────────────────────────────

class Agent(Protocol):
    """Protocol for agents that propose actions."""

    name: str

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose an action given the current task and observation."""
        ...


# ── Model Client Protocol ─────────────────────────────────────────────

class ModelClient(Protocol):
    """Provider-agnostic LLM client protocol."""

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Generate a structured response matching the given Pydantic schema."""
        ...


# ── Harness Contract (Protocol) ──────────────────────────────────────

class HarnessContract(Protocol):
    """Protocol that generated harness code must satisfy."""

    def evaluate_action(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
    ) -> dict[str, Any]:
        """Return {"accepted": bool, "normalized_action": dict|None, "reason": str, "confidence": float|None}."""
        ...

    def repair_action(
        self,
        observation: dict[str, Any],
        proposed_action: dict[str, Any],
        failure: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return a repaired action dict or None."""
        ...


# ── Harness Lifecycle States ──────────────────────────────────────────

HarnessLifecycleState = Literal[
    "GENERATED",
    "STATICALLY_VALIDATED",
    "SANDBOX_TESTED",
    "EVALUATED",
    "APPROVED",
    "ACTIVE",
    "RETIRED",
]


# ── Experiment Config ─────────────────────────────────────────────────

class ExperimentConfig(BaseModel):
    """Configuration for a single experiment run."""

    model_config = {"extra": "forbid", "frozen": True}

    experiment_id: str
    environment: str
    agent: str
    harness_version: str | None = None  # None = no harness
    dataset: str  # train / validation / test
    seed: int = 42
    max_steps_per_scenario: int = 20
    model_name: str | None = None  # None = mock


# ── Mutation Spec ─────────────────────────────────────────────────────

class MutationSpec(BaseModel):
    """Description of an environment mutation."""

    model_config = {"extra": "forbid", "frozen": True}

    mutation_id: str
    environment: str
    description: str
    config_changes: dict[str, Any]
