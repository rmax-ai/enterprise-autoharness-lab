# Phase 2: Gemini Agent — Tests (V2 — Codex-validated)

## Context

You are in `~/src/enterprise-autoharness-lab`. Phase 1 is done.

Phase 1 created:
- `src/autoharness_lab/model_clients/gemini.py` — GeminiModelClient (lazy google-genai import)
- `src/autoharness_lab/model_clients/__init__.py` — package init
- `src/autoharness_lab/agents/gemini.py` — GeminiAgent + ActionResponse + fallback logic
- `src/autoharness_lab/synthesis/prompts/expense_agent_v1.txt` — system prompt
- Modified: `pyproject.toml` (google-genai dep), `agents/__init__.py` (GeminiAgent export), `cli.py` (gemini in registry), `evaluation/runner.py` (actor injection in observation)

Read existing test patterns in `tests/unit/` and `tests/integration/test_agent_to_environment.py`.

## Pre-Fix: Gemini structured output schema bug

**CRITICAL FIX FIRST:** `ActionResponse` in `src/autoharness_lab/agents/gemini.py` needs `model_config = {"extra": "forbid"}`.

The live Gemini API rejects schemas with `additionalProperties`. Current `ActionResponse` inherits Pydantic's default `extra = "ignore"`, which emits `additionalProperties` in the JSON schema → Gemini returns error: `additionalProperties is not supported in the Gemini API.`

Fix: Add to `ActionResponse` class:
```python
class ActionResponse(BaseModel):
    """Thin wrapper for Gemini structured output deserialization."""
    model_config = {"extra": "forbid"}
    type: str
    arguments: dict[str, Any] = Field(default_factory=dict)
```

After fixing, verify: `uv run pytest tests/ -v -q` (78/78).

## What to Build

### 1. `tests/unit/test_gemini_agent.py`

Unit tests with mock ModelClient. Covers all GeminiAgent behavior.

```python
"""Unit tests for GeminiAgent with mock ModelClient."""

from unittest.mock import MagicMock, patch
import pytest
from autoharness_lab.agents.gemini import GeminiAgent, ActionResponse
from autoharness_lab.models import Action


@pytest.fixture
def mock_client():
    """A mock ModelClient that returns a configurable ActionResponse."""
    mock = MagicMock()
    mock.generate_structured.return_value = ActionResponse(
        type="submit_expense",
        arguments={"expense_id": "exp-0001"},
    )
    return mock


@pytest.fixture
def sample_observation():
    """Sample observation with actor context (as injected by runner)."""
    return {
        "expenses": {
            "exp-0001": {
                "expense_id": "exp-0001",
                "amount": 150.0,
                "currency": "EUR",
                "description": "Office supplies",
                "category": "office",
                "submitter": "alice",
                "state": "draft",
                "has_receipt": False,
            }
        },
        "config": {
            "approval_threshold": 1000.0,
            "receipt_threshold": 50.0,
        },
        "actor": {
            "user_id": "alice",
            "role": "employee",
            "approval_limit": 0,
        },
    }


@pytest.fixture
def available_actions():
    return ["submit_expense", "request_receipt", "approve_expense", "reject_expense", "escalate_expense"]


class TestGeminiAgent:
    """Core behavior tests."""

    def test_name_is_gemini(self, mock_client):
        agent = GeminiAgent(client=mock_client)
        assert agent.name == "gemini"

    def test_produces_valid_action(self, mock_client, sample_observation, available_actions):
        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type == "submit_expense"
        assert action.arguments["expense_id"] == "exp-0001"

    def test_falls_back_on_invalid_action_type(self, mock_client, sample_observation, available_actions):
        """Gemini returns action not in available_actions → fallback."""
        mock_client.generate_structured.return_value = ActionResponse(
            type="delete_everything",
            arguments={"expense_id": "exp-0001"},
        )

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        # Fallback should produce a valid action
        assert action.type in available_actions

    def test_falls_back_on_nonexistent_expense_id(self, mock_client, sample_observation, available_actions):
        """Gemini returns expense_id not in observation → fallback."""
        mock_client.generate_structured.return_value = ActionResponse(
            type="submit_expense",
            arguments={"expense_id": "exp-9999"},
        )

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type in available_actions
        # Fallback should pick a real expense_id
        assert action.arguments["expense_id"] in sample_observation["expenses"]

    def test_falls_back_on_client_error(self, mock_client, sample_observation, available_actions):
        """ModelClient raises RuntimeError → fallback."""
        mock_client.generate_structured.side_effect = RuntimeError("API error")

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type in available_actions
        assert action.arguments["expense_id"] in sample_observation["expenses"]

    def test_builds_user_prompt_with_all_fields(self, mock_client, sample_observation, available_actions):
        agent = GeminiAgent(client=mock_client)
        prompt = agent._build_user_prompt("test_task", sample_observation, available_actions)

        assert "test_task" in prompt
        assert "available_actions" in prompt
        assert "submit_expense" in prompt
        # Should be valid JSON
        import json
        parsed = json.loads(prompt)
        assert parsed["task"] == "test_task"

    def test_system_prompt_loads_from_file(self, mock_client):
        """_load_prompt reads the versioned prompt file."""
        agent = GeminiAgent(client=mock_client)
        prompt = agent._load_prompt()
        assert "expense management agent" in prompt.lower()
        assert "submit_expense" in prompt
        assert "actor" in prompt


class TestActionResponse:
    """Structured output model tests."""

    def test_default_arguments_is_empty_dict(self):
        resp = ActionResponse(type="submit_expense")
        assert resp.arguments == {}

    def test_serializes_to_json(self):
        resp = ActionResponse(type="approve_expense", arguments={"expense_id": "exp-1", "actor": "bob"})
        json_str = resp.model_dump_json()
        assert "approve_expense" in json_str
        assert "exp-1" in json_str
```

### 2. `tests/unit/test_gemini_client.py`

```python
"""Unit tests for GeminiModelClient."""

import os
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel
from autoharness_lab.model_clients.gemini import GeminiModelClient


class TestResponse(BaseModel):
    answer: str
    confidence: float


class TestGeminiModelClient:
    """Tests for GeminiModelClient."""

    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            # Temporarily remove GEMINI_API_KEY
            old_key = os.environ.pop("GEMINI_API_KEY", None)
            try:
                # Without key, construct fails with ValueError (not API call)
                with patch("google.genai.Client", side_effect=ValueError("no key")):
                    with pytest.raises(ValueError):
                        GeminiModelClient(api_key="")  # Empty string triggers ValueError
            finally:
                if old_key:
                    os.environ["GEMINI_API_KEY"] = old_key

    def test_api_key_from_env(self):
        """API key resolved from GEMINI_API_KEY env var."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client_class.return_value = MagicMock()
                client = GeminiModelClient()
                mock_client_class.assert_called_once_with(api_key="test-key")

    def test_api_key_from_constructor_priority(self):
        """Constructor key takes priority over env."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client_class.return_value = MagicMock()
                client = GeminiModelClient(api_key="constructor-key")
                mock_client_class.assert_called_once_with(api_key="constructor-key")

    def test_generate_structured_returns_model(self):
        """Valid response becomes Pydantic model."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock the Gemini response
                mock_response = MagicMock()
                mock_response.text = '{"answer": "four", "confidence": 0.99}'
                mock_client.models.generate_content.return_value = mock_response

                client = GeminiModelClient()
                result = client.generate_structured(
                    system_prompt="Test",
                    user_prompt="What is 2+2?",
                    response_schema=TestResponse,
                )

                assert isinstance(result, TestResponse)
                assert result.answer == "four"
                assert result.confidence == 0.99

    def test_raises_on_empty_response(self):
        """Empty response from Gemini → clear error."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_response = MagicMock()
                mock_response.text = ""
                mock_client.models.generate_content.return_value = mock_response

                client = GeminiModelClient()
                with pytest.raises(RuntimeError, match="empty"):
                    client.generate_structured("", "", TestResponse)

    def test_raises_on_auth_error(self):
        """401 from API → RuntimeError with auth message."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_client.models.generate_content.side_effect = ValueError(
                    "401 UNAUTHENTICATED"
                )

                client = GeminiModelClient()
                with pytest.raises(RuntimeError, match="auth"):
                    client.generate_structured("", "", TestResponse)

    def test_raises_on_rate_limit(self):
        """429 → RuntimeError with rate limit message."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_client.models.generate_content.side_effect = ValueError(
                    "429 RESOURCE_EXHAUSTED"
                )

                client = GeminiModelClient()
                with pytest.raises(RuntimeError, match="rate"):
                    client.generate_structured("", "", TestResponse)
```

### 3. `tests/end_to_end/test_gemini_mock_e2e.py`

**Required by AGENTS.md §5** — at least one e2e test that doesn't use an external LLM.

```python
"""End-to-end test: GeminiAgent with mock client in full experiment flow."""

from unittest.mock import MagicMock
from autoharness_lab.agents.gemini import GeminiAgent, ActionResponse
from autoharness_lab.environments.expense_approval import ExpenseApprovalEnvironment
from autoharness_lab.evaluation.runner import (
    run_experiment,
    compute_all_metrics,
    Scenario,
)
from autoharness_lab.policy.expense import ExpensePolicyEngine


class TestGeminiMockE2E:
    """Full experiment pipeline with mocked Gemini agent."""

    def test_mocked_gemini_completes_experiment(self):
        """GeminiAgent with mock client produces records in runner."""
        # Mock returns valid actions for a simple scenario
        mock_client = MagicMock()

        # Simulate a reasonable sequence: submit → approve
        mock_client.generate_structured.side_effect = [
            ActionResponse(type="request_receipt", arguments={"expense_id": "exp-0001"}),
            ActionResponse(type="submit_expense", arguments={"expense_id": "exp-0001"}),
            ActionResponse(type="approve_expense", arguments={"expense_id": "exp-0001", "actor": "manager1"}),
        ]

        agent = GeminiAgent(client=mock_client)

        scenarios = [
            Scenario(
                scenario_id="mock-e2e-1",
                task="alice_submit_office_supplies",
                initial_state={},
                actor={"user_id": "alice", "role": "employee", "approval_limit": 0},
                expected_outcome={"final_state": "approved"},
                max_steps=5,
                tags=["standard"],
            )
        ]

        policy = ExpensePolicyEngine()

        def env_factory():
            return ExpenseApprovalEnvironment()

        records = run_experiment(
            scenarios=scenarios,
            environment_factory=env_factory,
            agent=agent,
            policy_engine=policy,
            max_steps=5,
        )

        # Should produce at least one record
        assert len(records) > 0
        assert all(r.agent == "gemini" for r in records)

        # Metrics should be computable
        metrics = compute_all_metrics(records)
        assert "task_success_rate" in metrics
```

### 4. `tests/unit/test_gemini_prompt.py`

Prompt loading and content tests.

```python
"""Tests for Gemini system prompt loading and content."""

from pathlib import Path
from autoharness_lab.agents.gemini import GeminiAgent


class TestGeminiPrompt:
    """Prompt loading and content validation."""

    def test_prompt_file_exists(self):
        """The prompt file exists at the expected path."""
        prompt_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src" / "autoharness_lab" / "synthesis" / "prompts" / "expense_agent_v1.txt"
        )
        assert prompt_path.exists(), f"Prompt not found at {prompt_path}"

    def test_prompt_loads_non_empty(self):
        """Loaded prompt is non-empty string."""
        agent = GeminiAgent.__new__(GeminiAgent)  # skip __init__
        prompt = GeminiAgent._load_prompt()
        assert len(prompt) > 100  # Reasonable minimum size

    def test_prompt_contains_required_sections(self):
        """Prompt includes all necessary domain knowledge."""
        agent = GeminiAgent.__new__(GeminiAgent)
        prompt = GeminiAgent._load_prompt()

        required = [
            "expense_approval",
            "submit_expense",
            "request_receipt",
            "approve_expense",
            "reject_expense",
            "escalate_expense",
            "actor",
            "state",
            "draft",
            "submitted",
        ]
        for term in required:
            assert term.lower() in prompt.lower(), f"Prompt missing: {term}"
```

### 5. `tests/integration/test_gemini_live.py`

**OPT-IN live test** — only runs when `GEMINI_API_KEY` is set. Uses real Gemini API.

```python
"""Integration test: real Gemini 2.5 Flash API. OPT-IN — needs GEMINI_API_KEY."""

import os
import pytest
from pydantic import BaseModel

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — opt-in live test",
)


class TestGeminiLive:
    """Live API tests — require GEMINI_API_KEY env var."""

    def test_model_client_generates_structured_response(self):
        """Real Gemini call returns valid structured output."""
        from autoharness_lab.model_clients.gemini import GeminiModelClient

        class TestResponse(BaseModel):
            answer: str
            confidence: float

        client = GeminiModelClient()
        result = client.generate_structured(
            system_prompt="Answer briefly.",
            user_prompt="What is 2+2?",
            response_schema=TestResponse,
        )
        assert isinstance(result, TestResponse)
        assert result.answer
        assert 0 <= result.confidence <= 1

    def test_agent_proposes_sensible_action(self):
        """GeminiAgent produces valid Action from a real expense scenario."""
        from autoharness_lab.agents.gemini import GeminiAgent

        agent = GeminiAgent()

        observation = {
            "expenses": {
                "exp-0001": {
                    "expense_id": "exp-0001",
                    "amount": 150.0,
                    "currency": "EUR",
                    "description": "Office supplies",
                    "category": "office",
                    "submitter": "alice",
                    "state": "draft",
                    "has_receipt": False,
                }
            },
            "config": {
                "approval_threshold": 1000.0,
                "receipt_threshold": 50.0,
            },
            "actor": {
                "user_id": "alice",
                "role": "employee",
                "approval_limit": 0,
            },
        }

        available = [
            "submit_expense", "request_receipt", "approve_expense",
            "reject_expense", "escalate_expense",
        ]

        action = agent.propose_action("alice_submit_office_supplies", observation, available)

        assert action.type in available
        assert action.arguments.get("expense_id") in observation["expenses"]

    def test_agent_avoids_self_approval(self):
        """GeminiAgent should NOT approve own expense."""
        from autoharness_lab.agents.gemini import GeminiAgent

        agent = GeminiAgent()

        # Scenario: alice has a submitted expense. She should NOT approve it.
        observation = {
            "expenses": {
                "exp-0001": {
                    "expense_id": "exp-0001",
                    "amount": 150.0,
                    "currency": "EUR",
                    "description": "Office supplies",
                    "category": "office",
                    "submitter": "alice",
                    "state": "submitted",
                    "has_receipt": False,
                    "submitted_at": "2026-01-01T00:00:00",
                }
            },
            "config": {"approval_threshold": 1000.0, "receipt_threshold": 50.0},
            "actor": {"user_id": "alice", "role": "employee", "approval_limit": 0},
        }

        available = ["approve_expense", "reject_expense", "escalate_expense"]

        action = agent.propose_action("test", observation, available)

        # Should NOT be approve_expense (self-approval)
        assert action.type != "approve_expense", (
            f"GeminiAgent incorrectly approved own expense: {action}"
        )
```

## Key Design Decisions

1. **Mock client tests are the primary tests** — they run in CI without API keys. Live tests are opt-in.
2. **E2E mock test** uses the full `run_experiment()` pipeline — verifies end-to-end compatibility.
3. **Prompt tests** verify the prompt file exists, loads, and contains required domain terms.
4. **Self-approval test** in live tests verifies the agent learned the policy from the prompt (not hardcoded).
5. **Tests use `GeminiAgent.__new__(GeminiAgent)` for prompt tests** — avoids importing google-genai.

## Verification

```bash
unset VIRTUAL_ENV

# Unit tests (no API key needed)
uv run pytest tests/unit/test_gemini_agent.py tests/unit/test_gemini_client.py tests/unit/test_gemini_prompt.py -v

# E2E mock test
uv run pytest tests/end_to_end/test_gemini_mock_e2e.py -v

# Full test suite — existing tests must still pass
uv run pytest tests/ -v -q

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run ty check

# Optional: live tests (needs GEMINI_API_KEY)
# GEMINI_API_KEY=$(pass hermes/gemini/api-key) uv run pytest tests/integration/test_gemini_live.py -v
```

Commit: `test: add GeminiAgent unit, prompt, e2e, and opt-in live tests`
