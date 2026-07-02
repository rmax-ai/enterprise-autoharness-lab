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
uv run autoharness list-environments
uv run autoharness run-baseline --environment expense-approval --agent noisy --dataset test
uv run autoharness synthesize --environment expense-approval --agent noisy --iterations 10
uv run autoharness evaluate --environment expense-approval --agent noisy --harness latest --dataset test
uv run autoharness compare --environment expense-approval --conditions no-harness,manual,generated
uv run autoharness mutate --environment expense-approval --mutation approval-threshold-change
uv run autoharness report --experiment-id <id>
uv run autoharness inspect-harness --environment expense-approval --version 3
```

## Experimental Conditions

| Condition | Description |
|-----------|-------------|
| Small model, no harness | Baseline — unassisted agent |
| Small model, manual harness | Hand-written validation code |
| Small model, generated harness | Auto-synthesized harness |
| Large model, no harness | Scale comparison baseline |

## Documentation

- [Architecture](ARCHITECTURE.md) — system design and component diagram
- [Decisions](DECISIONS.md) — rationale for key design choices
- [Roadmap](ROADMAP.md) — phased implementation plan
- [docs/](docs/) — architecture details, experiment design, threat model, harness lifecycle

## License

MIT

## Status

Research prototype. Not production-ready.
