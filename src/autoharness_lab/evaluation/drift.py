"""Drift experiment runner.

Tests harness robustness to environment changes: applies a mutation,
measures degradation, re-synthesizes, and reports recovery metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.environments.deployment import DeploymentEnvironment
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.environments.support_ticket import SupportTicketEnvironment
from autoharness_lab.evaluation.mutations import (
    MutationResult,
    apply_mutation,
    get_mutation,
)
from autoharness_lab.evaluation.runner import (
    compute_all_metrics,
    load_scenarios,
    run_experiment,
)
from autoharness_lab.harness.sandbox import SandboxExecutor
from autoharness_lab.policy.deployment import DeploymentPolicyEngine
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.policy.support import SupportTicketPolicyEngine
from autoharness_lab.synthesis.search import SynthesisLoop


class _SandboxHarnessAdapter:
    """Adapts SandboxExecutor.evaluate_as_harness() to harness_runtime.evaluate()."""

    def __init__(self, sandbox: SandboxExecutor) -> None:
        self._sandbox = sandbox

    def evaluate(
        self, observation: dict[str, Any], proposed_action: dict[str, Any]
    ) -> dict[str, Any]:
        return self._sandbox.evaluate_as_harness(observation, proposed_action)


def _make_environment(env_name: str, config: object | None = None):
    """Create an environment with optional config override."""
    if env_name == "expense-approval":
        return ExpenseApprovalEnvironment(config) if config else ExpenseApprovalEnvironment()  # type: ignore[arg-type]
    elif env_name == "support-ticket":
        return SupportTicketEnvironment(config) if config else SupportTicketEnvironment()  # type: ignore[arg-type]
    elif env_name == "deployment":
        return DeploymentEnvironment(config) if config else DeploymentEnvironment()  # type: ignore[arg-type]
    raise ValueError(f"Unknown environment: {env_name}")


def _make_policy_engine(env_name: str, config: object | None = None):
    """Create a policy engine with optional config."""
    if env_name == "expense-approval":
        return ExpensePolicyEngine()
    elif env_name == "support-ticket":
        if config:
            return SupportTicketPolicyEngine(
                refund_limit=getattr(config, "refund_limit", 500.0),
            )
        return SupportTicketPolicyEngine()
    elif env_name == "deployment":
        if config:
            return DeploymentPolicyEngine(
                production_freeze=getattr(config, "production_freeze", False),
            )
        return DeploymentPolicyEngine()
    raise ValueError(f"Unknown environment: {env_name}")


def run_drift_experiment(
    environment: str,
    mutation_id: str,
    registry_root: Path,
    model_client,
    agent_name: str = "noisy",
    seed: int = 42,
    max_iterations: int = 5,
) -> MutationResult:
    """Run a complete drift experiment.

    1. Synthesize harness on original environment
    2. Measure baseline performance
    3. Apply mutation to environment config
    4. Measure degraded performance (same harness, mutated env)
    5. Re-synthesize harness on mutated environment
    6. Measure recovered performance

    Args:
        environment: Environment name.
        mutation_id: Mutation identifier from the catalog.
        registry_root: Directory for harness registry.
        model_client: Model client (mock for deterministic testing).
        agent_name: Agent name for failure generation.
        seed: Random seed.
        max_iterations: Max synthesis iterations.

    Returns:
        MutationResult with baseline, degraded, and recovered metrics.
    """
    mutation = get_mutation(environment, mutation_id)
    if mutation is None:
        raise ValueError(f"Mutation not found: {mutation_id} for {environment}")

    repo_root = Path(__file__).resolve().parents[3]
    scenario_path = repo_root / "scenarios" / environment / "test.jsonl"

    # ── Phase 1: Synthesize on original environment ────────────────────

    # Run synthesis on original environment
    synthesis_loop = SynthesisLoop(
        model_client=model_client,
        registry_root=registry_root,
        environment=environment,
        agent_name=agent_name,
        max_iterations=max_iterations,
        seed=seed,
    )

    env_spec = _get_spec(environment)
    synth_result = synthesis_loop.run(environment_spec=env_spec)

    if synth_result.final_harness is None:
        raise RuntimeError("Synthesis failed to produce a harness")

    original_harness = synth_result.final_harness

    # ── Phase 2: Baseline (original env, original harness) ────────────
    env_orig = _make_environment(environment)
    policy_orig = _make_policy_engine(environment)
    sandbox_orig = SandboxExecutor(original_harness.code)
    adapter_orig = _SandboxHarnessAdapter(sandbox_orig)

    if not scenario_path.exists():
        baseline_metrics = {"composite_score": 0.0}
    else:
        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=seed)
        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: _make_environment(environment),
            agent=agent,
            policy_engine=policy_orig,
            harness_runtime=adapter_orig,
            run_id=f"drift-baseline-{mutation_id}",
        )
        baseline_metrics = compute_all_metrics(records)

    baseline_score = baseline_metrics.get("composite_score", 0.0)

    # ── Phase 3: Degraded (mutated env, original harness) ─────────────
    mutated_config = apply_mutation(
        environment,
        env_orig.config if hasattr(env_orig, "config") else None,
        mutation.config_changes,
    )
    policy_mutated = _make_policy_engine(environment, mutated_config)

    if not scenario_path.exists():
        degraded_metrics = {"composite_score": 0.0}
    else:
        scenarios = load_scenarios(scenario_path)
        agent = NoisyAgent(seed=seed)
        records = run_experiment(
            scenarios=scenarios,
            environment_factory=lambda: _make_environment(environment, mutated_config),
            agent=agent,
            policy_engine=policy_mutated,
            harness_runtime=adapter_orig,  # Same harness, mutated env
            run_id=f"drift-degraded-{mutation_id}",
        )
        degraded_metrics = compute_all_metrics(records)

    degraded_score = degraded_metrics.get("composite_score", 0.0)
    score_drop = baseline_score - degraded_score

    # ── Phase 4: Recover (mutated env, re-synthesized harness) ────────
    recovery_registry_root = Path(registry_root) / "recovery"
    recovery_registry_root.mkdir(parents=True, exist_ok=True)

    recovery_loop = SynthesisLoop(
        model_client=model_client,
        registry_root=recovery_registry_root,
        environment=environment,
        agent_name=agent_name,
        max_iterations=max_iterations,
        seed=seed + 1,  # Different seed for recovery
    )

    recovery_result = recovery_loop.run(environment_spec=env_spec)

    recovered = recovery_result.final_harness is not None
    recovered_score = None
    recovered_metrics = None
    ce_needed = None
    iterations = None
    recovery_delta = None

    if recovered:
        recovery_harness = recovery_result.final_harness
        sandbox_rec = SandboxExecutor(recovery_harness.code)
        adapter_rec = _SandboxHarnessAdapter(sandbox_rec)

        if scenario_path.exists():
            scenarios = load_scenarios(scenario_path)
            agent = NoisyAgent(seed=seed)
            records = run_experiment(
                scenarios=scenarios,
                environment_factory=lambda: _make_environment(environment, mutated_config),
                agent=agent,
                policy_engine=policy_mutated,
                harness_runtime=adapter_rec,
                run_id=f"drift-recovered-{mutation_id}",
            )
            recovered_metrics = compute_all_metrics(records)
            recovered_score = recovered_metrics.get("composite_score", 0.0)
            recovery_delta = recovered_score - degraded_score

        ce_needed = sum(r.num_counterexamples for r in recovery_result.history)
        iterations = recovery_result.iterations_completed

    return MutationResult(
        mutation_id=mutation_id,
        environment=environment,
        description=mutation.description,
        baseline_score=baseline_score,
        baseline_metrics=baseline_metrics,
        degraded_score=degraded_score,
        degraded_metrics=degraded_metrics,
        score_drop=score_drop,
        recovered_score=recovered_score,
        recovered_metrics=recovered_metrics,
        recovery_delta=recovery_delta,
        counterexamples_needed=ce_needed,
        iterations_to_recover=iterations,
        recovered=recovered,
    )


def _get_spec(environment: str) -> dict[str, Any]:
    """Get environment spec for synthesis."""
    specs = {
        "expense-approval": {
            "name": "expense-approval",
            "supported_actions": [
                "submit_expense",
                "request_receipt",
                "approve_expense",
                "reject_expense",
                "escalate_expense",
            ],
            "state_transitions": {
                "draft": ["submitted"],
                "submitted": ["approved", "rejected"],
                "approved": [],
                "rejected": [],
            },
            "validation_rules": [
                "Cannot approve own expense",
                "Cannot approve already approved expense",
                "Receipt required above threshold",
                "Unknown action types must be rejected",
            ],
        },
        "support-ticket": {
            "name": "support-ticket",
            "supported_actions": [
                "assign_ticket",
                "set_priority",
                "add_note",
                "resolve_ticket",
                "close_ticket",
                "escalate_ticket",
                "reopen_ticket",
            ],
            "state_transitions": {
                "new": ["assigned"],
                "assigned": ["in_progress", "escalated"],
                "in_progress": ["resolved", "escalated"],
                "resolved": ["closed"],
                "closed": [],
                "escalated": ["assigned", "in_progress"],
            },
            "validation_rules": [
                "Cannot close without notes",
                "Cannot resolve unassigned",
                "Unknown actions rejected",
            ],
        },
        "deployment": {
            "name": "deployment",
            "supported_actions": [
                "create_deployment",
                "approve_deployment",
                "start_deployment",
                "verify_deployment",
                "cancel_deployment",
                "rollback_deployment",
            ],
            "state_transitions": {
                "draft": ["approved", "cancelled"],
                "approved": ["in_progress", "cancelled"],
                "in_progress": ["deployed", "cancelled"],
                "deployed": ["verified", "rolled_back"],
                "verified": ["rolled_back"],
                "rolled_back": [],
                "cancelled": [],
            },
            "validation_rules": [
                "Cannot self-approve",
                "High-risk needs manager",
                "Production freeze blocks deploys",
                "Unknown actions rejected",
            ],
        },
    }
    return specs.get(
        environment,
        {
            "name": environment,
            "supported_actions": [],
            "state_transitions": {},
            "validation_rules": [],
        },
    )
