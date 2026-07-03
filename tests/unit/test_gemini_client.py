"""Unit tests for GeminiModelClient."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from autoharness_lab.model_clients.gemini import GeminiModelClient


class ResponseSchema(BaseModel):
    answer: str
    confidence: float


class TestGeminiModelClient:
    """Tests for GeminiModelClient."""

    def test_raises_without_api_key(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="GEMINI_API_KEY"),
        ):
            GeminiModelClient(api_key="")

    def test_api_key_from_env(self):
        """API key resolved from GEMINI_API_KEY env var."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client_class.return_value = MagicMock()
            GeminiModelClient()
            mock_client_class.assert_called_once_with(api_key="test-key")

    def test_api_key_from_constructor_priority(self):
        """Constructor key takes priority over env."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client_class.return_value = MagicMock()
            GeminiModelClient(api_key="constructor-key")
            mock_client_class.assert_called_once_with(api_key="constructor-key")

    def test_generate_structured_returns_model(self):
        """Valid response becomes Pydantic model."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"answer": "four", "confidence": 0.99}'
            mock_client.models.generate_content.return_value = mock_response

            client = GeminiModelClient()
            result = client.generate_structured(
                system_prompt="Test",
                user_prompt="What is 2+2?",
                response_schema=ResponseSchema,
            )

            assert isinstance(result, ResponseSchema)
            assert result.answer == "four"
            assert result.confidence == 0.99

    def test_raises_on_empty_response(self):
        """Empty response from Gemini yields a clear RuntimeError."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = ""
            mock_client.models.generate_content.return_value = mock_response

            client = GeminiModelClient()
            with pytest.raises(RuntimeError, match="empty"):
                client.generate_structured("", "", ResponseSchema)

    def test_raises_on_auth_error(self):
        """401 from API yields RuntimeError with auth guidance."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.models.generate_content.side_effect = ValueError("401 UNAUTHENTICATED")

            client = GeminiModelClient()
            with pytest.raises(RuntimeError, match="auth"):
                client.generate_structured("", "", ResponseSchema)

    def test_raises_on_rate_limit(self):
        """429 yields RuntimeError with rate-limit guidance."""
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch("google.genai.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.models.generate_content.side_effect = ValueError("429 RESOURCE_EXHAUSTED")

            client = GeminiModelClient()
            with pytest.raises(RuntimeError, match="rate"):
                client.generate_structured("", "", ResponseSchema)
