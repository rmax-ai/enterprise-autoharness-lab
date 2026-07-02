# Enterprise AutoHarness Lab — Architecture

## Problem Statement

LLM-based agents frequently emit invalid, malformed, or policy-violating actions when interacting with enterprise workflow environments. Human-authored validation code is expensive to write and maintain. Can an LLM automatically synthesize a deterministic harness that reduces invalid agent actions, without becoming an ungoverned source of authority?

## Design Goals

1. **Separation of concerns:** probabilistic agent ≠ synthesized harness ≠ authoritative policy engine
2. **Reproducibility:** all experiments deterministic from config, seed, prompts, model version, and code hash
3. **Safety:** generated harness code sandboxed; policy engine remains authoritative
4. **Measurability:** structured traces, counterexamples, multi-metric evaluation
5. **Extensibility:** provider-agnostic, environment-pluggable, synthesis-strategy-pluggable

## Core Loop

```
Agent proposes action
        ↓
Synthesized harness evaluates action
        ↓
Authoritative policy engine checks action
        ↓
Environment executes action
        ↓
Failure or success is recorded
        ↓
Failures become structured counterexamples
        ↓
LLM generates a revised harness
        ↓
New harness is evaluated on held-out scenarios
```

## Component Diagram

```
┌──────────────────────────────────────────────────┐
│                    CLI (typer)                     │
│  list-environments | run-baseline | synthesize     │
│  evaluate | compare | mutate | report              │
└────────────────────┬─────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐   ┌──────▼──────┐   ┌───▼──────────┐
│  Agent  │   │   Harness   │   │ Policy Engine │
│ (prob.) │   │  (determ.)  │   │  (authority)  │
└────┬────┘   └──────┬──────┘   └───┬──────────┘
     │               │               │
     └───────────────┼───────────────┘
                     │
              ┌──────▼──────┐
              │ Environment │
              │  (stateful)  │
              └──────┬──────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐   ┌──────▼──────┐   ┌───▼──────────┐
│ Traces  │   │  Synthesis  │   │  Evaluation   │
│ (JSONL) │   │    Loop     │   │   Engine      │
└─────────┘   └──────┬──────┘   └──────────────┘
                     │
              ┌──────▼──────┐
              │  Registry   │
              │ (versions)  │
              └─────────────┘
```

## Trust Boundaries

```
┌──────────────────────────────────────────────┐
│                                              │
│  ┌─────────┐   Boundary 1   ┌─────────────┐ │
│  │  Agent  │────────────────▶│   Harness   │ │
│  │ (untr.) │                 │ (sandboxed) │ │
│  └─────────┘                 └──────┬──────┘ │
│                                     │        │
│                          Boundary 2 │        │
│                                     ▼        │
│                              ┌─────────────┐ │
│                              │ Policy Eng.  │ │
│                              │ (authority)  │ │
│                              └──────┬──────┘ │
│                                     │        │
│                          Boundary 3 │        │
│                                     ▼        │
│                              ┌─────────────┐ │
│                              │ Environment │ │
│                              │ (state)     │ │
│                              └─────────────┘ │
│                                              │
└──────────────────────────────────────────────┘

Boundary 1: Harness validates agent output (syntactic + operational validity).
Boundary 2: Policy engine retains final authority (authorization + business rules).
Boundary 3: Environment enforces state transitions (transactional integrity).
```

**Key invariant:** Harness acceptance never implies policy authorization. The policy engine MUST be called even when the harness accepts an action.

## Module Layout

```
src/autoharness_lab/
├── models.py              # Action, ExecutionResult, HarnessDecision, PolicyDecision
├── config.py              # Experiment configuration, scenario loading
├── cli.py                 # Typer CLI entry point
├── agents/
│   ├── base.py            # Agent protocol
│   ├── scripted.py        # Deterministic baseline
│   ├── noisy.py           # Deliberately weak for failure generation
│   └── llm.py             # LLM-backed agent (provider-agnostic)
├── model_clients/
│   ├── base.py            # ModelClient protocol
│   ├── mock.py            # Mock for deterministic testing
│   └── provider.py        # Real provider adapter
├── environments/
│   ├── base.py            # Environment protocol
│   ├── expense_approval.py
│   ├── support_ticket.py
│   └── deployment.py
├── policy/
│   ├── base.py            # PolicyEngine base
│   ├── expense.py
│   ├── support.py
│   └── deployment.py
├── harness/
│   ├── contracts.py       # evaluate_action/repair_action contracts
│   ├── runtime.py         # Harness execution wrapper
│   ├── sandbox.py         # AST validation + subprocess sandbox
│   ├── static_validation.py
│   └── registry.py        # HarnessArtifact storage and versioning
├── synthesis/
│   ├── generator.py       # Initial harness generation
│   ├── critic.py          # Failure analysis
│   ├── refiner.py         # Harness revision from counterexamples
│   ├── counterexamples.py # Extract counterexamples from traces
│   └── search.py          # Iteration loop
├── evaluation/
│   ├── runner.py          # Experiment runner
│   ├── metrics.py         # Metric calculations
│   ├── comparison.py      # Cross-condition comparison
│   └── mutations.py       # Environment mutation engine
├── reporting/
│   ├── markdown.py
│   ├── html.py
│   ├── charts.py
│   └── templates/
├── storage/
│   ├── traces.py          # AttemptRecord, Counterexample storage
│   └── experiments.py     # Experiment metadata persistence
```

## Data Flow

1. **Agent** receives task + observation + available actions → produces Action
2. **Harness** receives observation + proposed action → produces HarnessDecision
3. **Policy Engine** receives actor + action + environment state → produces PolicyDecision
4. **Environment** receives action → produces ExecutionResult + updated state
5. **Traces** record complete AttemptRecord per step
6. **Counterexamples** extracted from failed attempts
7. **Synthesis** generates/refines harness from counterexamples + spec
8. **Registry** stores all harness versions with provenance

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pydantic v2 for all schemas | Strict validation, JSON Schema export, typed contracts |
| Protocol classes for Agent/Environment/ModelClient | Provider-agnostic, testable with mocks |
| AST-based sandbox (not Docker) | Research prototype — lighter weight, no container dependency |
| JSONL trace storage | Append-only, human-readable, easy to replay |
| File-system harness registry | No database dependency for research prototype |
| Typer CLI | Rich help text, shell completion, composable commands |

## Trade-offs

| Decision | Trade-off |
|----------|-----------|
| AST sandbox over container | Simpler but weaker isolation — documented as research sandbox |
| File-system registry over DB | Simpler but no concurrent access, no querying |
| Linear synthesis over search | Simpler but may miss better candidates — interfaces designed for search later |
| Mock model client for testing | Deterministic but doesn't test real LLM behavior |
| Single package (no monorepo) | Simpler but less separation — appropriate for research prototype |
