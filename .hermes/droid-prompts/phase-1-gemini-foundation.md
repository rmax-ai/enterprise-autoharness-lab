# Phase 1: Gemini Agent — Foundation (V2 — Codex-validated)

## Context

You are in `~/src/enterprise-autoharness-lab`. This phase creates the core building blocks for a Gemini 2.5 Flash agent.

Read `AGENTS.md` for conventions. Read these files for patterns:
- `src/autoharness_lab/models.py` — Agent protocol (line 209), ModelClient protocol (line 227)
- `src/autoharness_lab/agents/scripted.py` — existing agent pattern
- `src/autoharness_lab/cli.py` — agent registry + experiment runner usage
- `src/autoharness_lab/evaluation/runner.py` — `run_experiment()` at line 153
- `src/autoharness_lab/environments/expense_approval.py` — environment state machine
- `src/autoharness_lab/policy/expense.py` — policy rules (self-approval, approval limits, receipts)

## What to Build

### 1. Add dependency (`pyproject.toml`)

Add `"google-genai>=1.0,<2.0"` to `[project.dependencies]`. Run `uv sync` after.

### 2. `src/autoharness_lab/model_clients/__init__.py`

Empty init — just a package marker. No registry.

### 3. `src/autoharness_lab/model_clients/gemini.py`

`GeminiModelClient` — implements `ModelClient` protocol. Lazy-load google-genai.

```python
"""Gemini 2.5 Flash model client."""

from __future__ import annotations

import os
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class GeminiModelClient:
    """Gemini 2.5 Flash model client (ModelClient protocol).

    API key from GEMINI_API_KEY env var. google-genai imported lazily.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        timeout: float = 30.0,
    ):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model = model
        self._timeout = timeout
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not set")
        # Lazy import — don't force google-genai at module level
        from google import genai
        self._client = genai.Client(api_key=self._api_key)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Call Gemini with structured output. Returns deserialized Pydantic model."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )

            # Extract text and parse
            raw = response.text.strip()
            if not raw:
                raise ValueError("Gemini returned empty response")

            parsed = response_schema.model_validate_json(raw)
            logger.info(
                "gemini_generate_structured",
                model=self._model,
                response_chars=len(raw),
            )
            return parsed

        except Exception as e:
            # Catch auth errors, rate limits, JSON parse failures
            error_msg = str(e)
            if "401" in error_msg or "UNAUTHENTICATED" in error_msg:
                raise RuntimeError(f"Gemini auth failed: verify GEMINI_API_KEY. {error_msg}") from e
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                raise RuntimeError(f"Gemini rate limited: {error_msg}") from e
            raise RuntimeError(f"Gemini API error: {error_msg}") from e
```

Key points:
- Lazy `from google import genai` inside `__init__` — keeps import optional until used
- Matching Codex guidance: explicit handling for 401, 429, empty response
- Uses `model_validate_json` (not `model_validate`) for raw JSON text
- `structlog` for token/response logging

### 4. `src/autoharness_lab/agents/gemini.py`

`GeminiAgent` — implements `Agent` protocol. ModelClient is injectable for tests.

```python
"""Gemini 2.5 Flash agent implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

from autoharness_lab.models import Action


logger = structlog.get_logger(__name__)


class ActionResponse(BaseModel):
    """Thin wrapper for Gemini structured output deserialization."""
    type: str
    arguments: dict[str, Any] = {}


class GeminiAgent:
    """LLM-powered agent using Gemini 2.5 Flash."""

    name = "gemini"

    def __init__(self, client=None, system_prompt: str | None = None):
        # Lazy import — only load google-genai when GeminiAgent is actually used
        from autoharness_lab.model_clients.gemini import GeminiModelClient

        self._client = client or GeminiModelClient()
        self._system_prompt = system_prompt or self._load_prompt()

    @staticmethod
    def _load_prompt() -> str:
        """Load system prompt from versioned file. Computes hash for provenance."""
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "synthesis" / "prompts" / "expense_agent_v1.txt"
        )
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {prompt_path}")
        return prompt_path.read_text()

    def _build_user_prompt(
        self, task: str, observation: dict[str, Any], available_actions: list[str]
    ) -> str:
        """Build the user prompt with task context, observation, and available actions."""
        return json.dumps({
            "task": task,
            "observation": observation,
            "available_actions": available_actions,
        }, indent=2)

    def propose_action(
        self,
        task: str,
        observation: dict[str, Any],
        available_actions: list[str],
    ) -> Action:
        """Propose the next action using Gemini."""
        user_prompt = self._build_user_prompt(task, observation, available_actions)

        try:
            result = self._client.generate_structured(
                system_prompt=self._system_prompt,
                user_prompt=user_prompt,
                response_schema=ActionResponse,
            )

            # Validate action type
            if result.type not in available_actions:
                logger.warning(
                    "gemini_invalid_action_type",
                    returned=result.type,
                    available=available_actions,
                )
                return self._fallback_action(observation)

            # Validate expense_id exists in observation (if provided)
            expense_id = result.arguments.get("expense_id")
            if expense_id and expense_id not in observation.get("expenses", {}):
                logger.warning(
                    "gemini_bad_expense_id",
                    expense_id=expense_id,
                )
                return self._fallback_action(observation)

            return Action(type=result.type, arguments=result.arguments)

        except Exception as e:
            logger.warning("gemini_propose_action_failed", error=str(e))
            return self._fallback_action(observation)

    @staticmethod
    def _fallback_action(observation: dict[str, Any]) -> Action:
        """Return a valid safe action when Gemini fails.

        Strategy: find the first draft expense and request a receipt for it.
        Requesting receipts is always safe — it never changes state incorrectly
        and never triggers a policy violation.
        """
        expenses = observation.get("expenses", {})
        for eid, exp in expenses.items():
            if exp.get("state") == "draft" and not exp.get("has_receipt"):
                return Action(type="request_receipt", arguments={"expense_id": eid})

        # If all drafts have receipts or no drafts exist, submit the first draft
        for eid, exp in expenses.items():
            if exp.get("state") == "draft":
                return Action(type="submit_expense", arguments={"expense_id": eid})

        # Nothing left to do — approve the first submitted (will be blocked by policy if illegal)
        for eid, exp in expenses.items():
            if exp.get("state") == "submitted":
                return Action(
                    type="approve_expense",
                    arguments={"expense_id": eid, "actor": "gemini"},
                )

        # Truly nothing — this is a terminal state
        return Action(type="submit_expense", arguments={"expense_id": "none"})
```

### 5. `src/autoharness_lab/synthesis/prompts/expense_agent_v1.txt`

Complete system prompt. This is V1 — hashed for provenance.

```
You are an expense management agent. Your role is to choose the best next action
for processing expense reports in an expense-approval workflow.

## Domain: Expense Approval State Machine

Expenses flow through states:
  draft → submitted → approved
  draft → submitted → rejected
  draft → submitted → escalated
  rejected → escalated

## Available Actions

- submit_expense(expense_id) — Submit a draft expense for approval
- request_receipt(expense_id) — Attach a receipt to an expense (instant in this system)
- approve_expense(expense_id, actor) — Approve a submitted expense
- reject_expense(expense_id, actor) — Reject a submitted expense
- escalate_expense(expense_id, actor) — Escalate to higher authority

## Domain Rules

1. Draft expenses should be submitted first (with receipt if needed)
2. Receipt required for expenses above $50 — call request_receipt before submit
3. Only SUBMITTED expenses can be approved, rejected, or escalated
4. NEVER approve your own expense — check the submitter field
5. NEVER approve an already-approved or already-rejected expense
6. NEVER reject an escalated expense — it's under review
7. Expenses above $1000 can only be approved by managers/admins
8. Managers have an approval limit — expenses above it require escalation
9. Always use action types from the available_actions list
10. Always use expense_ids that exist in the observation

## Observation Format

{
  "expenses": {
    "<expense_id>": {
      "expense_id": "...",
      "amount": 150.0,
      "currency": "EUR",
      "description": "...",
      "category": "...",
      "submitter": "alice",
      "state": "draft",
      "has_receipt": false,
      "approver": null,
      "submitted_at": null,
      "resolved_at": null
    }
  },
  "config": {
    "approval_threshold": 1000.0,
    "receipt_threshold": 50.0,
    "require_receipt_for_all": false,
    "allow_self_approval": false,
    "supported_currencies": ["CHF", "EUR", "GBP", "JPY", "USD"],
    "max_approval_limit": 10000.0
  },
  "actor": {
    "user_id": "alice",
    "role": "employee",
    "approval_limit": 0
  }
}

The "actor" field tells you who you are acting as. Use this for:
- Checking if you're the submitter (to avoid self-approval)
- Knowing your role (employee vs manager vs admin)
- Knowing your approval limit (0 for employees, positive for managers)

## Strategy

1. First priority: submit draft expenses (with receipts if > receipt_threshold)
2. Second priority: approve submitted expenses (if authorized — check self-approval, limits)
3. If you can't approve (over limit, not manager): escalate
4. If the expense violates policy (no receipt, wrong submitter): reject

## Response Format

Always respond with JSON: {"type": "<action_type>", "arguments": {"expense_id": "<id>", ...}}

For approve/reject/escalate, include "actor" in arguments (use the actor's user_id from observation).
```

### 6. `src/autoharness_lab/agents/__init__.py` — modify

Add `GeminiAgent` to imports and `__all__`:
```python
from autoharness_lab.agents.gemini import GeminiAgent
__all__ = ["Agent", "GeminiAgent"]
```

### 7. `src/autoharness_lab/cli.py` — modify

Two changes:

**A)** Add `GeminiAgent` import and register it:
```python
from autoharness_lab.agents.gemini import GeminiAgent

def _get_agent(name: str, seed: int = 42):
    agents = {
        "scripted": ScriptedAgent(),
        "noisy": NoisyAgent(seed=seed),
        "gemini": GeminiAgent(),  # ADD THIS LINE
    }
```

**B)** Inject actor into observation in `compare` and `run_baseline` commands.

In the comparison loop (around line 166 of cli.py), before `run_experiment()`, add actor to the observation:
```python
# For the compare command, we need to pass actor context to the agent.
# The runner's run_experiment() function now injects actor into observation.
# But we also need to make sure the runner does this.

# Actually, the better fix is in run_experiment() itself.
# The runner has access to scenario.actor. We should inject it there.
```

### 8. `src/autoharness_lab/evaluation/runner.py` — modify

**CRITICAL:** Inject actor context into observation before calling `agent.propose_action()`.

In `run_experiment()` at line ~189, change:
```python
observation = env.state_snapshot()
```
To:
```python
observation = env.state_snapshot()
# INJECT ACTOR CONTEXT — agents need to know who they are acting as
# to avoid self-approval and respect approval limits
observation["actor"] = scenario.actor
```

This way the Agent protocol signature doesn't change, but the observation has what the Gemini agent needs. `ScriptedAgent` and `NoisyAgent` ignore the `actor` field — no regression.

## Key Design Decisions

1. **Actor injection via observation** — The cleanest fix. Doesn't change the Agent protocol. The runner already has `scenario.actor`. ScriptedAgent and NoisyAgent ignore the field. GeminiAgent uses it.

2. **Safe fallback** — Fallback action picks a valid expense_id from observation. First tries `request_receipt` (always safe), then `submit_expense` on a draft. Never produces an invalid action.

3. **Lazy google-genai import** — The import happens inside `GeminiModelClient.__init__`, not at module level. This means `uv run pytest tests/` doesn't require `google-genai` to be installed unless you're actually using GeminiAgent. Matches AGENTS "provider-agnostic" principle.

4. **Prompt versioning** — Prompt at `synthesis/prompts/expense_agent_v1.txt`. Matches AGENTS.md §6. Includes actor context, approval limits, and escalation rules.

5. **CLI target** — `autoharness run-baseline -e expense-approval -a gemini` works. `compare -c gemini` does NOT work (compare uses named conditions, not agent names) — that's a separate feature.

6. **Pin google-genai** — `>=1.0,<2.0` prevents silent breaking changes.

## Verification

```bash
unset VIRTUAL_ENV

# Install new dep
uv sync

# Import check (installs google-genai)
uv run python -c "
from autoharness_lab.model_clients.gemini import GeminiModelClient
from autoharness_lab.agents.gemini import GeminiAgent
from autoharness_lab.cli import _get_agent
agent = _get_agent('gemini', seed=42)
assert agent.name == 'gemini'
print('OK: agent registered')
"

# Full existing test suite (must still pass)
uv run pytest tests/ -v -q

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run ty check
```

Commit: `feat: add GeminiModelClient, GeminiAgent, actor-context injection in runner`
