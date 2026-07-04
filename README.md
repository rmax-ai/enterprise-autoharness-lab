# Enterprise AutoHarness Lab

> **Can an LLM automatically synthesize a code harness that reduces invalid agent actions, without becoming an ungoverned source of authority?**

An open-source research project demonstrating the AutoHarness idea: an LLM improves an agent by automatically generating and refining deterministic control code from execution failures.

Based on: [AutoHarness: Improving LLM Agents by Automatically Synthesizing a Code Harness](https://arxiv.org/abs/2603.03329) (arXiv:2603.03329)

## Architecture

The project preserves a strict architectural distinction between:

- **Probabilistic Agent** — proposes actions based on task + observation
- **Synthesized Harness** — deterministic code that predicts action validity
- **Authoritative Policy Engine** — final authority on permissions and business rules
- **Workflow Environment** — stateful simulation of enterprise workflows
- **Evaluation System** — structured traces, metrics, and reproducible experiments

> **The synthesized harness predicts operational applicability. The policy engine retains authority.**

## Environments

Three simulated enterprise workflow environments:

1. **Expense Approval** — submit, approve, reject, escalate expenses with configurable thresholds
2. **Customer Support Tickets** — assign, prioritize, resolve, refund with specialist routing
3. **Software Deployment** — create, approve, start, cancel, rollback with artifact validation

## Quick Start

```bash
# Install
git clone https://github.com/rmax-ai/enterprise-autoharness-lab.git
cd enterprise-autoharness-lab
uv sync --extra dev

# Run deterministic demo (no external LLM required)
uv run autoharness compare \
  --environment expense-approval \
  --conditions no-harness,manual

# List available commands
uv run autoharness --help
```

## CLI Commands

```bash
# List available workflow environments
uv run autoharness list-environments

# Run a single baseline experiment
uv run autoharness run-baseline \
  --environment expense-approval \
  --agent noisy \
  --dataset test

# Compare agent performance across conditions
uv run autoharness compare \
  --environment expense-approval \
  --conditions no-harness,manual

uv run autoharness compare \
  --environment support-ticket \
  --conditions no-harness,manual,scripted \
  --dataset test

uv run autoharness compare \
  --environment deployment \
  --conditions no-harness,manual,scripted \
  --dataset test
```

## Agent Types

| Agent | Description |
|-------|-------------|
| `noisy` | Deliberately weak agent — produces invalid actions at configurable rates for reproducible failure generation |
| `scripted` | Deterministic baseline — always produces valid, policy-compliant actions |
| `gemini` | LLM-backed agent using Gemini 2.5 Flash (requires `GEMINI_API_KEY`) |

## Conditions

Conditions specifiable via `--conditions` / `-c` on `compare`:

| Condition | Description |
|-----------|-------------|
| `no-harness` | Agent runs without any harness |
| `manual` | Agent runs with a hand-written validation harness |
| `scripted` | Scripted agent as deterministic upper bound |
| `generated` | Agent runs with the latest generated harness (requires prior synthesis — see roadmap) |

## Documentation

- [Architecture](ARCHITECTURE.md) — system design and component diagram
- [Decisions](DECISIONS.md) — rationale for key design choices
- [Roadmap](ROADMAP.md) — phased implementation plan
- [docs/](docs/) — architecture details, experiment design, threat model, harness lifecycle

## License

MIT

## Status

Research prototype. Not production-ready. Milestone 1 (deterministic research kernel) complete.
Milestones 2–5 (harness synthesis, reporting, mutation testing) are on the roadmap
but not yet implemented as CLI commands.
