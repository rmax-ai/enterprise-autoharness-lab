# AGENTS.md – Guidelines for Enterprise AutoHarness Lab

This document captures conventions for all contributors and AI coding agents working on **Enterprise AutoHarness Lab**.

---

## 1. Project DNA

AutoHarness Lab is a research system that demonstrates automated synthesis of deterministic control code (harnesses) from agent execution failures. The core architectural invariant is:

> **The synthesized harness predicts operational applicability. The policy engine retains authority.**

## 2. Code Organisation

- `src/autoharness_lab/` — single package, flat namespace
- `src/autoharness_lab/models.py` — shared Pydantic models (Action, ExecutionResult, HarnessDecision, etc.)
- `src/autoharness_lab/agents/` — agent implementations (base protocol, scripted, noisy, LLM-backed)
- `src/autoharness_lab/environments/` — workflow environments (expense, support, deployment)
- `src/autoharness_lab/policy/` — authoritative policy engines per environment
- `src/autoharness_lab/harness/` — harness contracts, runtime, sandbox, static validation, registry
- `src/autoharness_lab/synthesis/` — generation, critic, refinement, counterexamples, search
- `src/autoharness_lab/evaluation/` — runner, metrics, comparison, mutations
- `src/autoharness_lab/reporting/` — markdown, HTML, charts
- `src/autoharness_lab/storage/` — traces, experiments
- One module = one responsibility. No god classes.

## 3. Architecture Non-Negotiables

1. **Harness ≠ Policy.** The harness predicts operational validity. The policy engine is the final authority. Harness acceptance never implies policy authorization. This invariant MUST be tested.
2. **Generated code is sandboxed.** Harness code runs in a restricted subprocess with AST validation, timeout, no network, no filesystem access.
3. **Deterministic where possible.** State transitions, policy evaluation, metric calculations are pure functions.
4. **Provider-agnostic.** Core logic never depends on a specific LLM vendor. Use the ModelClient protocol.
5. **Reproducible.** All experiments reproducible from config, seed, prompt version, model identifier, and code hash.

## 4. Generated Harness Constraints

Generated harness code MUST NOT:
- Access the network
- Access the filesystem
- Spawn processes
- Import arbitrary modules
- Use eval, exec, compile
- Use reflection (getattr, setattr, globals, locals, vars)
- Mutate external state
- Call the model
- Bypass the policy engine

Generated harness code MUST:
- Be deterministic given the same inputs
- Return structured dicts matching the harness contract
- Handle unknown or malformed actions gracefully (return rejected=False)

## 5. Testing

- `tests/unit/` — pure function tests (models, metrics, state transitions, policy decisions, AST validation)
- `tests/integration/` — agent → harness → policy → environment flow, counterexample extraction, artifact registry
- `tests/end_to_end/` — complete deterministic experiments with mock model client
- Target: >85% coverage on core modules
- Run: `uv run pytest tests/ -v`
- At least one e2e test must run without external LLM (mock model client)
- Test the invariant: harness cannot bypass policy denial
- Test that reject-all harness fails the objective

## 6. Prompt Management

- All LLM prompts are versioned as files (not embedded inline)
- Store in `src/autoharness_lab/synthesis/prompts/`
- Each prompt file has a hash for provenance tracking
- Never modify prompts without versioning

## 7. Formatting and Linting

```bash
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
uv run ty check
```

- Line length: 100
- Double quotes for strings
- Type annotations on all public interfaces
- No `dict[str, Any]` in public signatures (use typed models)

## 8. Key Gotchas

- `datetime.utcnow()` is deprecated — use `datetime.now(UTC)`
- Pydantic `model_config` is reserved — never name a field after it
- Trailing comma in parenthesized f-strings creates tuples
- `src/__init__.py` can cause "Source file found twice" — do not create it
- Use `default_factory` for mutable defaults in Pydantic models
- `py.typed` marker required for type checking: `touch src/autoharness_lab/py.typed`

## 9. References

- PYTHON_DEVELOPMENT.md — day-to-day Python engineering
- PYTHON_API_DESIGN.md — API design conventions
- PYTHON_ARCHITECTURE.md — architecture patterns
- docs/architecture.md — system architecture
- docs/harness-lifecycle.md — harness state machine
- docs/threat-model.md — security analysis
- docs/limitations.md — known limitations
