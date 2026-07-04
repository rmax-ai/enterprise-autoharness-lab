"""CLI for Enterprise AutoHarness Lab."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autoharness_lab.agents.gemini import GeminiAgent
from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.agents.scripted import ScriptedAgent
from autoharness_lab.environments.deployment import (
    DeploymentEnvironment,
)
from autoharness_lab.environments.expense_approval import (
    ExpenseApprovalEnvironment,
)
from autoharness_lab.environments.support_ticket import (
    SupportTicketEnvironment,
)
from autoharness_lab.evaluation.runner import (
    compute_all_metrics,
    load_scenarios,
    run_experiment,
)
from autoharness_lab.harness.contracts import HarnessRuntime
from autoharness_lab.policy.deployment import DeploymentPolicyEngine
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.policy.support import SupportPolicyEngine

app = typer.Typer(help="Enterprise AutoHarness Lab CLI")
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "scenarios"


# ── Helpers ───────────────────────────────────────────────────────────


def _get_environment(name: str):
    """Get an environment factory by name."""
    environments = {
        "expense-approval": lambda: ExpenseApprovalEnvironment(),
        "support-ticket": lambda: SupportTicketEnvironment(),
        "deployment": lambda: DeploymentEnvironment(),
    }
    if name not in environments:
        console.print(f"[red]Unknown environment: {name}[/red]")
        console.print(f"Available: {', '.join(environments.keys())}")
        raise typer.Exit(1)
    return environments[name]


def _get_agent(name: str, seed: int = 42):
    """Get an agent by name."""
    agent_factories = {
        "scripted": ScriptedAgent,
        "noisy": lambda: NoisyAgent(seed=seed),
        "gemini": GeminiAgent,
    }
    if name not in agent_factories:
        console.print(f"[red]Unknown agent: {name}[/red]")
        console.print(f"Available: {', '.join(agent_factories.keys())}")
        raise typer.Exit(1)
    return agent_factories[name]()


def _get_policy_engine(environment: str):
    """Get a policy engine by environment name."""
    engines = {
        "expense-approval": ExpensePolicyEngine,
        "support-ticket": SupportPolicyEngine,
        "deployment": DeploymentPolicyEngine,
    }
    if environment not in engines:
        console.print(f"[red]Unknown environment for policy: {environment}[/red]")
        raise typer.Exit(1)
    return engines[environment]()


def _load_harness_runtime(environment: str, version: str | None = None) -> HarnessRuntime | None:
    """Load a harness runtime. Returns None if no harness available."""
    if version in ("manual", "latest"):
        harness_paths = {
            "expense-approval": (
                REPO_ROOT / "src/autoharness_lab/harness/manual/expense_approval.py"
            ),
            "support-ticket": (
                REPO_ROOT / "src/autoharness_lab/harness/manual/support_ticket.py"
            ),
            "deployment": (
                REPO_ROOT / "src/autoharness_lab/harness/manual/deployment.py"
            ),
        }
        harness_path = harness_paths.get(environment)
        if harness_path is None or not harness_path.exists():
            console.print(f"[yellow]No manual harness for environment: {environment}[/yellow]")
            return None
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("manual_harness", harness_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["manual_harness"] = module
            spec.loader.exec_module(module)
            return HarnessRuntime(module)
    return None


# ── Commands ──────────────────────────────────────────────────────────


@app.command()
def list_environments():
    """List available workflow environments."""
    table = Table(title="Available Environments")
    table.add_column("Name", style="cyan")
    table.add_column("Actions", style="green")
    table.add_column("Status", style="yellow")

    table.add_row(
        "expense-approval",
        "submit, request_receipt, approve, reject, escalate",
        "✓ ready",
    )
    table.add_row("support-ticket", "assign, set_priority, resolve, refund, escalate", "✓ ready")
    table.add_row("deployment", "create, approve, start, cancel, rollback", "✓ ready")

    console.print(table)


@app.command()
def compare(
    environment: str = typer.Option(
        "expense-approval", "--environment", "-e", help="Environment to compare"
    ),
    conditions: str = typer.Option(
        "no-harness,manual",
        "--conditions",
        "-c",
        help="Comma-separated conditions to compare",
    ),
    dataset: str = typer.Option(
        "test", "--dataset", "-d", help="Dataset to use (train, validation, test)"
    ),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed"),
):
    """Compare agent performance across conditions."""
    condition_list = [c.strip() for c in conditions.split(",")]
    scenario_path = SCENARIOS_DIR / environment / f"{dataset}.jsonl"

    if not scenario_path.exists():
        console.print(f"[red]No scenarios found at {scenario_path}[/red]")
        console.print("Run with --dataset train if test scenarios not yet created.")
        raise typer.Exit(1)

    scenarios = load_scenarios(scenario_path)
    console.print(f"Loaded {len(scenarios)} scenarios from {scenario_path}")

    env_factory = _get_environment(environment)
    policy_engine = _get_policy_engine(environment)

    table = Table(title=f"Comparison: {environment} ({dataset})")
    table.add_column("Condition", style="cyan")
    table.add_column("Success Rate", style="green")
    table.add_column("Invalid Rate", style="red")
    table.add_column("Policy Denial", style="yellow")
    table.add_column("Composite", style="magenta")
    table.add_column("Actions", style="dim")

    for condition in condition_list:
        console.print(f"\nRunning condition: [bold]{condition}[/bold]")

        if condition == "no-harness":
            agent = _get_agent("noisy", seed=seed)
            harness = None
        elif condition == "manual":
            agent = _get_agent("noisy", seed=seed)
            harness = _load_harness_runtime(environment, "manual")
        elif condition == "generated":
            agent = _get_agent("noisy", seed=seed)
            harness = _load_harness_runtime(environment, "latest")
        elif condition == "large-model":
            # Placeholder — uses noisy agent as proxy
            agent = _get_agent("scripted", seed=seed)
            harness = None
        else:
            console.print(f"[yellow]Unknown condition: {condition}, skipping[/yellow]")
            continue

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=env_factory,
            agent=agent,
            policy_engine=policy_engine,
            harness_runtime=harness,
            run_id=f"compare-{condition}-{uuid.uuid4().hex[:8]}",
        )

        metrics = compute_all_metrics(records)

        table.add_row(
            condition,
            f"{metrics['task_success_rate']:.1%}",
            f"{metrics['invalid_action_rate']:.1%}",
            f"{metrics['policy_denial_rate']:.1%}",
            f"{metrics['composite_score']:.3f}",
            str(metrics["total_actions"]),
        )

    console.print()
    console.print(table)


@app.command()
def run_baseline(
    environment: str = typer.Option(..., "--environment", "-e"),
    agent_name: str = typer.Option(..., "--agent", "-a"),
    dataset: str = typer.Option("test", "--dataset", "-d"),
    seed: int = typer.Option(42, "--seed", "-s"),
):
    """Run a single baseline experiment."""
    scenario_path = SCENARIOS_DIR / environment / f"{dataset}.jsonl"

    if not scenario_path.exists():
        console.print(f"[red]No scenarios at {scenario_path}[/red]")
        raise typer.Exit(1)

    scenarios = load_scenarios(scenario_path)
    agent = _get_agent(agent_name, seed=seed)
    env_factory = _get_environment(environment)
    policy_engine = _get_policy_engine(environment)

    records = run_experiment(
        scenarios=scenarios,
        environment_factory=env_factory,
        agent=agent,
        policy_engine=policy_engine,
        run_id=f"baseline-{agent_name}-{uuid.uuid4().hex[:8]}",
    )

    metrics = compute_all_metrics(records)
    console.print_json(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    app()
