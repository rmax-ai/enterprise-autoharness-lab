# Gemini 2.5 Flash Agent — Implementation Plan

## Architecture

```
                    ┌─────────────────────────────┐
                    │        GeminiAgent           │
                    │  (Agent protocol)            │
                    │                              │
                    │  propose_action(task, obs,   │
                    │    available_actions) → Action│
                    └──────────┬──────────────────┘
                               │ calls
                    ┌──────────▼──────────────────┐
                    │    GeminiModelClient          │
                    │  (ModelClient protocol)       │
                    │                               │
                    │  generate_structured(sys,     │
                    │    user, schema) → BaseModel  │
                    └──────────┬──────────────────┘
                               │ HTTP
                    ┌──────────▼──────────────────┐
                    │  Gemini 2.5 Flash API         │
                    │  (google-genai SDK)           │
                    └──────────────────────────────┘
```

## Files to create

| # | File | Purpose |
|---|------|---------|
| 1 | `src/autoharness_lab/model_clients/__init__.py` | Re-export ModelClient + registry |
| 2 | `src/autoharness_lab/model_clients/gemini.py` | `GeminiModelClient` — wraps google-genai SDK, implements `generate_structured()` |
| 3 | `src/autoharness_lab/agents/gemini.py` | `GeminiAgent` — constructs task+obs → prompt → calls ModelClient → returns Action |
| 4 | `src/autoharness_lab/agents/prompts/expense_agent_system.txt` | System prompt: domain rules, action schema, constraints |
| 5 | `tests/unit/test_gemini_agent.py` | Unit tests with mock ModelClient |
| 6 | `tests/unit/test_gemini_client.py` | Unit tests for GeminiModelClient (API key resolution, token counting, error handling) |
| 7 | `tests/integration/test_gemini_live.py` | Live API test (skipped if no GEMINI_API_KEY) |

## Files to modify

| # | File | Change |
|---|------|--------|
| 8 | `pyproject.toml` | Add `google-genai>=1.0` to core dependencies |
| 9 | `src/autoharness_lab/cli.py` | Add `gemini` to `_get_agent()` registry |
| 10 | `src/autoharness_lab/agents/__init__.py` | Export GeminiAgent |

## Step-by-step

### Step 1: Add `google-genai` dependency

```toml
# pyproject.toml — add to [project.dependencies]
"google-genai>=1.0",
```

### Step 2: GeminiModelClient (`model_clients/gemini.py`)

```python
class GeminiModelClient:
    """Gemini 2.5 Flash model client implementing ModelClient protocol."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        self._api_key = api_key or os.environ["GEMINI_API_KEY"]
        self._model = model
        self._client = genai.Client(api_key=self._api_key)

    def generate_structured(
        self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel]
    ) -> BaseModel:
        """Call Gemini with structured output, return deserialized model."""
        # Uses Gemini's native response_schema for structured output
```

Key design decisions:
- API key from env `GEMINI_API_KEY`
- Model default: `gemini-2.5-flash`
- Token usage logged at INFO level for observability
- Timeout: 30s default, configurable via constructor
- `generate_structured` returns the Pydantic model directly (matches protocol)
- Error handling: raise typed exceptions for auth (401), rate limit (429), malformed JSON

### Step 3: GeminiAgent (`agents/gemini.py`)

```python
class GeminiAgent:
    """LLM-powered agent using Gemini 2.5 Flash."""

    name = "gemini"

    def __init__(self, client: ModelClient | None = None, system_prompt: str | None = None):
        self._client = client or GeminiModelClient()
        self._system_prompt = system_prompt or self._load_prompt()

    def propose_action(
        self, task: str, observation: dict[str, Any], available_actions: list[str]
    ) -> Action:
        # 1. Build user prompt: JSON with task + observation + available_actions
        # 2. Call client.generate_structured(system, user, ActionResponse)
        # 3. Validate returned action type is in available_actions
        # 4. Fallback to Action(type="submit_expense", arguments={"expense_id": "none"}) on failure
```

Key design decisions:
- `ActionResponse` — thin Pydantic wrapper for structured output: `{type: str, arguments: dict}`
- Graceful degradation: if Gemini returns invalid action type, fallback to no-op
- If `expense_id` in response doesn't exist in observation, falls back
- ModelClient is injectable (for testing with mock)

### Step 4: System prompt (`agents/prompts/expense_agent_system.txt`)

Prompt content:
- **Role:** You are an expense management agent
- **Domain:** expense approval workflow with 5 states (draft, submitted, approved, rejected, escalated)
- **Actions:** submit_expense, request_receipt, approve_expense, reject_expense, escalate_expense
- **Rules:** submit drafts, attach receipts for >$50, approve submitted (not own), don't approve already-approved/rejected
- **Constraints:** only use available_actions, only target existing expense_ids, respect state transitions
- **Output:** JSON with {"type": "<action>", "arguments": {"expense_id": "<id>", ...}}

⚠️ **Versioned prompt file** — stored under `agents/prompts/`, hashed for provenance tracking (matches AGENTS.md section 6).

### Step 5: CLI integration

```python
# cli.py — _get_agent()
"gemini": GeminiAgent(),
```

Then: `autoharness compare -e expense-approval -c gemini` works without changes.

Also: `autoharness run-baseline -e expense-approval -a gemini`

### Step 6: Tests

| Test | Type | What it verifies |
|------|------|-----------------|
| GeminiAgent produces valid Action from mock client | unit | Prompt construction, response parsing, validation |
| GeminiAgent rejects invalid action type from model | unit | Safety: hallucinated action → fallback no-op |
| GeminiAgent handles missing arguments | unit | Safety: partial response → still valid Action |
| GeminiAgent handles non-existent expense_id | unit | Safety: bad ID → fallback no-op |
| GeminiModelClient resolves key from env | unit | Config: env var fallback |
| GeminiModelClient handles auth error gracefully | unit | Error handling: 401 → clear error message |
| Live API call produces sensible action | integration | End-to-end: real Gemini → real environment |
| Live API handles rate limits gracefully | integration | Resilience: 429 → retry or clear error |

### Risk Assessment

| Risk | Mitigation |
|------|-----------|
| **Cost** — Gemini API charges per token | Tests use mock; live test optional (guard: `pytest.mark.skipif(no key)`); prompt caching feasible post-v0.1 |
| **Latency** — API call adds ~1-3s per step | Acceptable for research; each scenario is ~5 steps |
| **Non-determinism** — Gemini may produce different actions for same input | Desired for harness synthesis — we want to observe failure patterns |
| **Prompt fragility** — prompt tweaks change behavior | Versioned as file under `agents/prompts/`, hashed for provenance (AGENTS.md §6) |
| **Structured output rejection** — Gemini may refuse schema | Fallback: return fallback Action, log warning |
| **Auth failure** — missing or invalid API key | Clear error message at agent init; test guard skips live tests |
| **google-genai v2 API** — breaking changes from v1 | Pin to known working version; see droid skill reference for v2 migration patterns |

## Dependencies

- `google-genai>=1.0` added to `pyproject.toml` core dependencies
- `GEMINI_API_KEY` env var (stored in pass vault at `hermes/gemini/api-key`)
- No new system dependencies. No Docker.

## Net new code estimate

- `model_clients/gemini.py`: ~80 lines
- `model_clients/__init__.py`: ~10 lines
- `agents/gemini.py`: ~100 lines
- `agents/prompts/expense_agent_system.txt`: ~50 lines
- Tests: ~150 lines total
- CLI + init changes: ~15 lines
- **Total: ~405 lines net new**
