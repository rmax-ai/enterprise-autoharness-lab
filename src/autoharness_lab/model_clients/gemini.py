"""Gemini 2.5 Flash model client."""

from __future__ import annotations

import os

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

        # Lazy import, don't force google-genai at module level.
        from google import genai

        self._client = genai.Client(api_key=self._api_key)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Call Gemini with structured output and return a deserialized Pydantic model."""
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

            raw = (response.text or "").strip()
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
            error_msg = str(e)
            if "401" in error_msg or "UNAUTHENTICATED" in error_msg:
                raise RuntimeError(f"Gemini auth failed: verify GEMINI_API_KEY. {error_msg}") from e
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                raise RuntimeError(f"Gemini rate limited: {error_msg}") from e
            raise RuntimeError(f"Gemini API error: {error_msg}") from e
