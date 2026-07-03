"""CLI for Enterprise AutoHarness Lab."""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autoharness_lab.agents.noisy import NoisyAgent
from autoharness_lab.agents.scripted import ScriptedAgent
from autoharness_lab.environments.expense_approval import (
    ExpenseApprovalEnvironment,
)
from autoharness_lab.evaluation.runner import (
    compute_all_metrics,
    load_scenarios,
    run_experiment,
)
from autoharness_lab.harness.contracts import HarnessRuntime
from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.policy.expense import ExpensePolicyEngine
from autoharness_lab.synthesis.generator import GeneratorResponse
from autoharness_lab.synthesis.search import SynthesisLoop

app = typer.Typer(help="Enterprise AutoHarness Lab CLI")
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "scenarios"


# ── Helpers ───────────────────────────────────────────────────────────


def _get_environment(name: str):
    """Get an environment factory by name."""
    environments = {
        "expense-approval": lambda: ExpenseApprovalEnvironment(),
    }
    if name not in environments:
        console.print(f"[red]Unknown environment: {name}[/red]")
        console.print(f"Available: {', '.join(environments.keys())}")
        raise typer.Exit(1)
    return environments[name]


def _get_agent(name: str, seed: int = 42):
    """Get an agent by name."""
    agents = {
        "scripted": ScriptedAgent(),
        "noisy": NoisyAgent(seed=seed),
    }
    if name not in agents:
        console.print(f"[red]Unknown agent: {name}[/red]")
        console.print(f"Available: {', '.join(agents.keys())}")
        raise typer.Exit(1)
    return agents[name]


def _get_policy_engine(environment: str):
    """Get a policy engine by environment name."""
    if environment == "expense-approval":
        return ExpensePolicyEngine()
    raise typer.Exit(1)


def _load_harness_runtime(environment: str, version: str | None = None) -> HarnessRuntime | None:
    """Load a harness runtime. Returns None if no harness available."""
    if version == "manual" or version == "latest":
        # Import manual harness
        import importlib.util
        import sys

        harness_path = REPO_ROOT / "src/autoharness_lab/harness/manual/expense_approval.py"
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
    table.add_row("support-ticket", "assign, priority, resolve, refund, escalate", "⏳ planned")
    table.add_row("deployment", "create, approve, start, cancel, rollback", "⏳ planned")

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


# ── Synthesize Command ────────────────────────────────────────────────


@app.command()
def synthesize(
    environment: str = typer.Option(
        "expense-approval", "--environment", "-e", help="Environment to synthesize harness for"
    ),
    agent: str = typer.Option("noisy", "--agent", "-a", help="Agent to generate failures from"),
    iterations: int = typer.Option(
        5, "--iterations", "-i", help="Maximum refinement iterations", min=1, max=20
    ),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed"),
    registry_dir: str = typer.Option(
        None, "--registry", "-r", help="Registry directory (default: temp dir)"
    ),
):
    """Synthesize a harness from agent execution failures.

    Runs the full synthesis pipeline:
    1. Generate initial harness from environment spec
    2. Evaluate against test scenarios
    3. Extract counterexamples from failures
    4. Refine harness
    5. Promote if score improved
    6. Repeat

    Uses a mock model client by default for deterministic synthesis.
    """
    env_spec = _get_environment_spec(environment)
    if env_spec is None:
        console.print(f"[red]No spec available for environment: {environment}[/red]")
        raise typer.Exit(1)

    registry_path = (
        Path(registry_dir) if registry_dir else Path(tempfile.mkdtemp(prefix="autoharness-"))
    )

    console.print("[bold]Synthesis Configuration[/bold]")
    console.print(f"  Environment: [cyan]{environment}[/cyan]")
    console.print(f"  Agent: [cyan]{agent}[/cyan]")
    console.print(f"  Max iterations: [cyan]{iterations}[/cyan]")
    console.print(f"  Registry: [dim]{registry_path}[/dim]")
    console.print()

    # Use mock client
    mock = MockModelClient()

    # Provide a default generator response
    mock.register(
        "You are a Python code generation system",
        "",
        GeneratorResponse,
        GeneratorResponse(
            code=(
                "def evaluate_action(observation, proposed_action):\n"
                '    return {"accepted": True, "normalized_action": proposed_action,'
                ' "reason": "default", "confidence": 0.5}\n'
            )
        ),
    )

    loop = SynthesisLoop(
        model_client=mock,
        registry_root=registry_path,
        environment=environment,
        agent_name=agent,
        max_iterations=iterations,
        seed=seed,
    )

    with console.status("[bold green]Running synthesis..."):
        result = loop.run(environment_spec=env_spec)

    console.print()
    console.print("[bold]Synthesis Complete[/bold]")
    console.print(f"  Iterations: [cyan]{result.iterations_completed}[/cyan]")
    console.print(
        f"  Best score: [yellow]{result.best_score:.3f}[/yellow]"
        if result.best_score
        else "  Best score: N/A"
    )

    # Show iteration history
    table = Table(title="Iteration History")
    table.add_column("Iter", style="dim")
    table.add_column("Harness ID", style="cyan")
    table.add_column("Score", style="yellow")
    table.add_column("Promoted", style="green")
    table.add_column("CE Count", style="red")

    for record in result.history:
        promoted_str = "[green]✓[/green]" if record.promoted else "[dim]-[/dim]"
        table.add_row(
            str(record.iteration),
            record.harness_id[:32] + "...",
            f"{record.composite_score:.3f}",
            promoted_str,
            str(record.num_counterexamples),
        )

    console.print(table)

    if result.final_harness:
        console.print()
        console.print("[bold]Final Harness Code:[/bold]")
        console.print(f"[dim]{result.final_harness.code[:500]}[/dim]")
        if len(result.final_harness.code) > 500:
            console.print(f"[dim]... [{len(result.final_harness.code) - 500} more chars][/dim]")


def _get_environment_spec(environment: str) -> dict | None:
    """Get the spec dict for an environment."""
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
                "Cannot approve own expense (self-approval denied)",
                "Cannot approve already approved expense",
                "Cannot approve rejected expense",
                "Receipt required for expenses above 50.0",
                "Manager approval required above 1000.0 threshold",
                "Unsupported currencies are rejected on submit",
                "Expense ID is required for all actions",
                "Unknown action types must be rejected",
            ],
        },
    }
    return specs.get(environment)
