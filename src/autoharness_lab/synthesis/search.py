"""Synthesis search loop with promotion logic and history tracking.

Orchestrates: generate → validate → sandbox → evaluate → extract
counterexamples → refine → promote (if improved) → repeat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.evaluation.runner import (
    compute_all_metrics,
    load_scenarios,
    run_experiment,
)
from autoharness_lab.harness.registry import HarnessRegistry
from autoharness_lab.harness.sandbox import SandboxExecutor
from autoharness_lab.harness.static_validation import validate_harness_code
from autoharness_lab.models import HarnessArtifact
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.storage.traces import extract_counterexamples
from autoharness_lab.synthesis.generator import HarnessGenerator
from autoharness_lab.synthesis.refiner import HarnessRefiner


@dataclass
class IterationRecord:
    """Record of one synthesis iteration."""

    iteration: int
    harness_id: str
    composite_score: float
    metrics: dict[str, float]
    promoted: bool
    num_counterexamples: int


@dataclass
class SynthesisResult:
    """Result of a full synthesis run."""

    iterations_completed: int
    final_harness: HarnessArtifact | None
    best_score: float | None
    history: list[IterationRecord] = field(default_factory=list)


class _SandboxHarnessAdapter:
    """Adapts SandboxExecutor.evaluate_as_harness() to harness_runtime.evaluate().

    run_experiment() expects harness_runtime.evaluate(obs, action) -> dict.
    SandboxExecutor provides evaluate_as_harness() which returns the right dict shape.
    This adapter bridges the two.
    """

    def __init__(self, sandbox: SandboxExecutor) -> None:
        self._sandbox = sandbox

    def evaluate(
        self, observation: dict[str, Any], proposed_action: dict[str, Any]
    ) -> dict[str, Any]:
        return self._sandbox.evaluate_as_harness(observation, proposed_action)


class SynthesisLoop:
    """Orchestrate the complete harness synthesis workflow.

    Linear refinement loop:
    1. Generate initial harness from environment spec
    2. Static validate + store in registry
    3. Sandbox test (basic sanity check)
    4. Evaluate against scenarios
    5. Extract counterexamples from failures
    6. Refine harness from counterexamples
    7. Promote if composite score improved
    8. Repeat until max_iterations or convergence
    """

    def __init__(
        self,
        model_client,
        registry_root: Path,
        environment: str,
        agent_name: str = "noisy",
        max_iterations: int = 5,
        seed: int = 42,
    ) -> None:
        self._client = model_client
        self._registry = HarnessRegistry(registry_root)
        self._generator = HarnessGenerator(model_client)
        self._refiner = HarnessRefiner(model_client)
        self._environment = environment
        self._agent_name = agent_name
        self._max_iterations = max_iterations
        self._seed = seed

        self._repo_root = Path(__file__).resolve().parents[3]

    def run(self, environment_spec: dict[str, Any]) -> SynthesisResult:
        """Run the full synthesis loop.

        Args:
            environment_spec: Environment description for harness generation.

        Returns:
            SynthesisResult with iteration history and final harness.
        """
        history: list[IterationRecord] = []
        best_score: float | None = None
        best_harness: HarnessArtifact | None = None

        # ── Step 1: Generate initial harness ──────────────────────────
        artifact = self._generator.generate(environment_spec)

        # Static validation
        validation = validate_harness_code(artifact.code)
        if not validation.valid:
            # Initial generation failed validation
            history.append(
                IterationRecord(
                    iteration=0,
                    harness_id=artifact.harness_id,
                    composite_score=0.0,
                    metrics={},
                    promoted=False,
                    num_counterexamples=0,
                )
            )

        # Store in registry
        stored = self._registry.store(
            environment=environment_spec["name"],
            code=artifact.code,
            model_name="mock",
            generation_prompt_hash=artifact.generation_prompt_hash,
        )
        self._registry.update_static_validation(
            stored.harness_id,
            {"valid": validation.valid, "errors": validation.errors},
        )

        # ── Step 2: Evaluate ──────────────────────────────────────────
        metrics = self._evaluate_harness(stored)
        score = metrics.get("composite_score", 0.0)

        if best_score is None or score > best_score:
            best_score = score
            best_harness = stored
            self._registry.update_metrics(stored.harness_id, metrics)
            self._registry.set_active(stored.harness_id)
            promoted = True
        else:
            promoted = False

        ce_count = self._count_counterexamples(stored)
        history.append(
            IterationRecord(
                iteration=0,
                harness_id=stored.harness_id,
                composite_score=score,
                metrics=metrics,
                promoted=promoted,
                num_counterexamples=ce_count,
            )
        )

        # ── Step 3-7: Refinement loop ─────────────────────────────────
        current_id = stored.harness_id

        for iteration in range(1, self._max_iterations):
            # Extract counterexamples from latest stored harness
            counterexamples = self._extract_counterexamples(stored)

            if not counterexamples:
                break  # No more failures to learn from

            # Refine
            refined = self._refiner.refine(
                current_code=stored.code,
                counterexamples=[ce.model_dump() for ce in counterexamples],
                environment=environment_spec["name"],
                parent_harness_id=current_id,
            )

            # Static validate refined
            refined_validation = validate_harness_code(refined.code)
            if not refined_validation.valid:
                history.append(
                    IterationRecord(
                        iteration=iteration,
                        harness_id=refined.harness_id,
                        composite_score=score,
                        metrics=metrics,
                        promoted=False,
                        num_counterexamples=len(counterexamples),
                    )
                )
                continue

            # Store refined
            refined_stored = self._registry.store(
                environment=environment_spec["name"],
                code=refined.code,
                model_name="mock",
                generation_prompt_hash=refined.generation_prompt_hash,
                parent_harness_id=current_id,
            )
            self._registry.update_static_validation(
                refined_stored.harness_id,
                {"valid": refined_validation.valid, "errors": refined_validation.errors},
            )

            # Evaluate refined
            refined_metrics = self._evaluate_harness(refined_stored)
            refined_score = refined_metrics.get("composite_score", 0.0)

            # Promote if improved
            if best_score is None or refined_score > best_score:
                best_score = refined_score
                best_harness = refined_stored
                self._registry.update_metrics(refined_stored.harness_id, refined_metrics)
                self._registry.set_active(refined_stored.harness_id)
                promoted = True
            else:
                promoted = False

            ref_ce_count = self._count_counterexamples(refined_stored)
            history.append(
                IterationRecord(
                    iteration=iteration,
                    harness_id=refined_stored.harness_id,
                    composite_score=refined_score,
                    metrics=refined_metrics,
                    promoted=promoted,
                    num_counterexamples=ref_ce_count,
                )
            )

            stored = refined_stored
            current_id = refined_stored.harness_id

            if not promoted:
                break  # No improvement, stop early

        return SynthesisResult(
            iterations_completed=len(history),
            final_harness=best_harness,
            best_score=best_score,
            history=history,
        )

    def _evaluate_harness(self, artifact: HarnessArtifact) -> dict[str, float]:
        """Evaluate a harness against test scenarios."""
        scenario_path = self._repo_root / "scenarios" / self._environment / "test.jsonl"

        if not scenario_path.exists():
            return {"composite_score": 0.0}

        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=self._seed)
        policy = ExpensePolicyEngine()
        sandbox = SandboxExecutor(artifact.code)
        adapter = _SandboxHarnessAdapter(sandbox)

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: ExpenseApprovalEnvironment(),
            agent=agent,
            policy_engine=policy,
            harness_runtime=adapter,
            run_id=f"synthesis-{artifact.harness_id}",
        )

        return compute_all_metrics(records)

    def _extract_counterexamples(self, artifact: HarnessArtifact) -> list:
        """Extract counterexamples by running the harness and checking failures."""
        scenario_path = self._repo_root / "scenarios" / self._environment / "test.jsonl"

        if not scenario_path.exists():
            return []

        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=self._seed)
        policy = ExpensePolicyEngine()
        sandbox = SandboxExecutor(artifact.code)
        adapter = _SandboxHarnessAdapter(sandbox)

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: ExpenseApprovalEnvironment(),
            agent=agent,
            policy_engine=policy,
            harness_runtime=adapter,
            run_id=f"ce-{artifact.harness_id}",
        )

        return extract_counterexamples(records)

    def _count_counterexamples(self, artifact: HarnessArtifact) -> int:
        """Count counterexamples for an artifact."""
        return len(self._extract_counterexamples(artifact))
