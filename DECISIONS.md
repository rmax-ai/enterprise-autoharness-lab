# Decisions

## Major Assumptions

1. **Research prototype, not production system.** The sandbox is AST-based, not container-based. The harness registry is file-system, not a database. These are appropriate for a research prototype but insufficient for production.
2. **Single-machine execution.** No distributed architecture. All experiments run locally.
3. **Deterministic where possible.** State transitions, policy evaluation, and metrics are pure functions. Only agent proposals and harness synthesis involve non-determinism (LLM calls).
4. **Mock-first testing.** The mock model client enables deterministic end-to-end tests without paid API access.

## Key Decisions

### Python 3.12+ with uv

**Chosen:** Python 3.12+, uv for dependency management
**Rejected:** Poetry (slower), pip (no lockfile), conda (heavy)
**Rationale:** uv is fast, produces standard lockfiles, and is the user's preferred tool.

### Pydantic v2 for All Schemas

**Chosen:** Pydantic v2 with `model_config = {"extra": "forbid", "frozen": True}`
**Rejected:** dataclasses (no validation), TypedDicts (no runtime checking)
**Rationale:** Strict validation at boundaries, JSON Schema generation for action discovery, frozen models prevent accidental mutation.

### Protocol Classes for Abstractions

**Chosen:** `typing.Protocol` for Agent, Environment, ModelClient
**Rejected:** ABC with abstract methods (more boilerplate), duck typing (no IDE support)
**Rationale:** Protocols enable structural subtyping — mock implementations don't need to inherit from a base class.

### AST-Based Sandbox

**Chosen:** `ast.parse()` + node whitelist + subprocess execution
**Rejected:** Docker/podman (heavy, requires daemon), RestrictedPython (unmaintained), eval with restricted builtins (too weak)
**Rationale:** Sufficient for research prototype. Documented as not a production security boundary.

### Linear Harness Refinement

**Chosen:** Generate → Evaluate → Select counterexamples → Revise (linear)
**Rejected:** Beam search, Thompson sampling, evolutionary search (overengineered for MVP)
**Rationale:** Spec calls for linear refinement first. Interfaces designed so search strategies can be added later.

### File-System Registry

**Chosen:** `generated_harnesses/<env>/<version>/` with JSON metadata
**Rejected:** SQLite, Postgres, S3
**Rationale:** Zero dependencies, human-inspectable, sufficient for single-machine research prototype.

### JSONL Trace Storage

**Chosen:** Append-only JSON Lines files
**Rejected:** SQLite (adds dependency), Parquet (overkill), in-memory only (not reproducible)
**Rationale:** Human-readable, machine-parseable, append-only for integrity.

## Known Limitations

- Sandbox is not a production security boundary (AST-level, not OS-level isolation)
- No concurrent experiment execution (single-machine, sequential)
- Linear synthesis may miss better harnesses that tree search would find
- Mock model client doesn't test real LLM behavior (by design)
- No network sandboxing at OS level (relies on AST restrictions)
- Harness code size limited by context window of the synthesis model
