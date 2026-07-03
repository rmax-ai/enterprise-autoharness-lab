"""Tests for Gemini system prompt loading and content."""

from __future__ import annotations

from pathlib import Path

from autoharness_lab.agents.gemini import GeminiAgent


class TestGeminiPrompt:
    """Prompt loading and content validation."""

    def test_prompt_file_exists(self):
        """The prompt file exists at the expected path."""
        prompt_path = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "autoharness_lab"
            / "synthesis"
            / "prompts"
            / "expense_agent_v1.txt"
        )
        assert prompt_path.exists(), f"Prompt not found at {prompt_path}"

    def test_prompt_loads_non_empty(self):
        """Loaded prompt is non-empty string."""
        prompt = GeminiAgent._load_prompt()
        assert len(prompt) > 100

    def test_prompt_contains_required_sections(self):
        """Prompt includes all necessary domain knowledge."""
        prompt = GeminiAgent._load_prompt()

        required_terms = [
            "expense-approval",
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
        for term in required_terms:
            assert term.lower() in prompt.lower(), f"Prompt missing: {term}"
