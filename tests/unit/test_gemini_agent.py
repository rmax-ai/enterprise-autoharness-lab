"""Unit tests for GeminiAgent with a mock ModelClient."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from autoharness_lab.agents.gemini import ActionResponse, GeminiAgent


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
    return [
        "submit_expense",
        "request_receipt",
        "approve_expense",
        "reject_expense",
        "escalate_expense",
    ]


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

    def test_falls_back_on_invalid_action_type(
        self, mock_client, sample_observation, available_actions
    ):
        """Gemini returns an action not in available_actions, so fallback is used."""
        mock_client.generate_structured.return_value = ActionResponse(
            type="delete_everything",
            arguments={"expense_id": "exp-0001"},
        )

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type in available_actions

    def test_falls_back_on_nonexistent_expense_id(
        self, mock_client, sample_observation, available_actions
    ):
        """Gemini returns expense_id not in observation, so fallback is used."""
        mock_client.generate_structured.return_value = ActionResponse(
            type="submit_expense",
            arguments={"expense_id": "exp-9999"},
        )

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type in available_actions
        assert action.arguments["expense_id"] in sample_observation["expenses"]

    def test_falls_back_on_client_error(self, mock_client, sample_observation, available_actions):
        """ModelClient raises RuntimeError, so fallback is used."""
        mock_client.generate_structured.side_effect = RuntimeError("API error")

        agent = GeminiAgent(client=mock_client)
        action = agent.propose_action("test_task", sample_observation, available_actions)

        assert action.type in available_actions
        assert action.arguments["expense_id"] in sample_observation["expenses"]

    def test_builds_user_prompt_with_all_fields(
        self, mock_client, sample_observation, available_actions
    ):
        agent = GeminiAgent(client=mock_client)
        prompt = agent._build_user_prompt("test_task", sample_observation, available_actions)

        assert "test_task" in prompt
        assert "available_actions" in prompt
        assert "submit_expense" in prompt

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
        resp = ActionResponse(
            type="approve_expense",
            arguments={"expense_id": "exp-1", "actor": "bob"},
        )
        json_str = resp.model_dump_json()
        assert "approve_expense" in json_str
        assert "exp-1" in json_str

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            ActionResponse(type="submit_expense", extra_field="nope")
