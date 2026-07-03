"""Evaluation runner and metrics for AutoHarness Lab.

Runs experiments, calculates metrics, and produces comparison results.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from autoharness_lab.models import (
    AttemptRecord,
    ExecutionResult,
    HarnessDecision,
    Scenario,
)
from autoharness_lab.storage.traces import TraceStore

# ── Metric Calculations ──────────────────────────────────────────────


def compute_task_success_rate(records: list[AttemptRecord]) -> float:
    """Fraction of scenarios where the final step was successful."""
    if not records:
        return 0.0
    # Group by scenario
    by_scenario: dict[str, list[AttemptRecord]] = {}
    for r in records:
        by_scenario.setdefault(r.scenario_id, []).append(r)

    successes = 0
    for _sid, recs in by_scenario.items():
        if recs and recs[-1].execution_result.status == "success":
            successes += 1
    return successes / len(by_scenario) if by_scenario else 0.0


def compute_invalid_action_rate(records: list[AttemptRecord]) -> float:
    """Fraction of actions that were invalid."""
    if not records:
        return 0.0
    invalid = sum(1 for r in records if r.execution_result.status == "invalid_action")
    return invalid / len(records)


def compute_policy_denial_rate(records: list[AttemptRecord]) -> float:
    """Fraction of actions denied by policy."""
    if not records:
        return 0.0
    denied = sum(1 for r in records if r.execution_result.status == "policy_denied")
    return denied / len(records)


def compute_runtime_error_rate(records: list[AttemptRecord]) -> float:
    """Fraction of actions that caused runtime errors."""
    if not records:
        return 0.0
    errors = sum(1 for r in records if r.execution_result.status == "runtime_error")
    return errors / len(records)


def compute_false_rejection_rate(records: list[AttemptRecord]) -> float:
    """Fraction of actions rejected by harness but would have succeeded."""
    if not records:
        return 0.0
    false_rejections = 0
    total_harness_rejections = 0
    for r in records:
        if r.harness_decision and not r.harness_decision.accepted:
            total_harness_rejections += 1
            # False rejection: harness said no, environment would have said yes
            if r.execution_result.status == "success":
                false_rejections += 1
    # Note: we can't know for certain if a rejected action would succeed
    # This metric uses actions that bypassed the harness as proxy
    return false_rejections / max(total_harness_rejections, 1)


def compute_false_acceptance_rate(records: list[AttemptRecord]) -> float:
    """Fraction of actions accepted by harness but failed in environment."""
    if not records:
        return 0.0
    false_acceptances = 0
    total_harness_acceptances = 0
    for r in records:
        if r.harness_decision and r.harness_decision.accepted:
            total_harness_acceptances += 1
            if r.execution_result.status != "success":
                false_acceptances += 1
    return false_acceptances / max(total_harness_acceptances, 1)


def compute_composite_score(
    records: list[AttemptRecord],
    weights: dict[str, float] | None = None,
) -> float:
    """Multi-objective composite score.

    Default weights penalize false rejections (reject-all harnesses score poorly)
    and false acceptances (which are safety failures).
    """
    w = weights or {
        "task_success": 1.0,
        "invalid_action": 0.5,
        "false_rejection": 0.8,
        "false_acceptance": 2.0,
        "policy_denial": 0.1,
    }

    score = (
        w["task_success"] * compute_task_success_rate(records)
        - w["invalid_action"] * compute_invalid_action_rate(records)
        - w["false_rejection"] * compute_false_rejection_rate(records)
        - w["false_acceptance"] * compute_false_acceptance_rate(records)
        - w["policy_denial"] * compute_policy_denial_rate(records)
    )
    return max(score, -1.0)  # Floor at -1.0


def compute_all_metrics(records: list[AttemptRecord]) -> dict[str, float]:
    """Compute all metrics for a set of records."""
    return {
        "task_success_rate": compute_task_success_rate(records),
        "invalid_action_rate": compute_invalid_action_rate(records),
        "policy_denial_rate": compute_policy_denial_rate(records),
        "runtime_error_rate": compute_runtime_error_rate(records),
        "false_rejection_rate": compute_false_rejection_rate(records),
        "false_acceptance_rate": compute_false_acceptance_rate(records),
        "composite_score": compute_composite_score(records),
        "total_actions": len(records),
    }


# ── Scenario Loader ──────────────────────────────────────────────────


def load_scenarios(path: Path) -> list[Scenario]:
    """Load scenarios from a JSONL file."""
    scenarios = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                scenarios.append(Scenario(**data))
    return scenarios


# ── Experiment Runner ────────────────────────────────────────────────


def run_experiment(
    scenarios: list[Scenario],
    environment_factory,
    agent,
    policy_engine,
    harness_runtime=None,
    max_steps: int = 20,
    run_id: str | None = None,
    trace_dir: Path | None = None,
) -> list[AttemptRecord]:
    """Run an experiment across all scenarios.

    Args:
        scenarios: List of scenarios to evaluate
        environment_factory: Callable that returns a fresh environment
        agent: Agent instance with propose_action()
        policy_engine: Policy engine with evaluate()
        harness_runtime: Optional HarnessRuntime for harness evaluation
        max_steps: Maximum steps per scenario
        run_id: Experiment run ID (auto-generated if None)
        trace_dir: Directory for trace storage

    Returns:
        List of all AttemptRecords from the experiment
    """
    run_id = run_id or str(uuid.uuid4())[:8]
    all_records: list[AttemptRecord] = []

    for scenario in scenarios:
        env = environment_factory()
        env.reset(seed=hash(scenario.scenario_id) % 10000)
        available_actions = env.available_action_types()

        for step in range(max_steps):
            observation = env.state_snapshot()
            observation["actor"] = scenario.actor

            # Agent proposes action
            proposed_action = agent.propose_action(
                task=scenario.task,
                observation=observation,
                available_actions=available_actions,
            )

            # Harness evaluates (if available)
            harness_decision = None
            if harness_runtime is not None:
                harness_result = harness_runtime.evaluate(
                    observation,
                    {"type": proposed_action.type, "arguments": proposed_action.arguments},
                )
                harness_decision = HarnessDecision(**harness_result)

            # Policy engine evaluates
            expense_id = proposed_action.arguments.get("expense_id")
            expense_state = observation.get("expenses", {}).get(expense_id)
            policy_decision = policy_engine.evaluate(
                actor=scenario.actor,
                action={
                    "type": proposed_action.type,
                    "arguments": proposed_action.arguments,
                },
                expense=expense_state,
            )

            # If policy denies, don't execute — record and continue
            if not policy_decision.allowed:
                result = ExecutionResult(
                    status="policy_denied",
                    observation=observation,
                    error_code=policy_decision.rule_id,
                    message=f"Policy denied: {policy_decision.reason}",
                )
            else:
                # Execute action in environment
                result = env.execute(proposed_action)

            # Record attempt
            record = AttemptRecord(
                run_id=run_id,
                scenario_id=scenario.scenario_id,
                environment=env.name,
                agent=agent.name,
                observation=observation,
                proposed_action=proposed_action,
                harness_decision=harness_decision,
                policy_decision=policy_decision,
                execution_result=result,
                step_index=step,
            )
            all_records.append(record)

            # Stop on terminal states
            if result.status in ("success", "runtime_error"):
                if result.status == "runtime_error":
                    break
                # Success — check if task is complete
                # For now, break after first success
                break

        # Write traces if trace_dir specified
        if trace_dir:
            trace_store = TraceStore(trace_dir / f"{scenario.scenario_id}.jsonl")
            trace_store.append_all(all_records[-max_steps:])

    return all_records
