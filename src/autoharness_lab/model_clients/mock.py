"""Mock model client for deterministic testing.

Returns pre-registered or default structured responses without any
LLM calls. Enables deterministic end-to-end tests of the synthesis pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel


class MockModelClient:
    """Deterministic mock implementing the ModelClient protocol.

    Responses are registered by matching system_prompt + user_prompt against
    a lookup table. Falls back to a default response if configured, or raises
    ValueError if no match found.
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], tuple[type[BaseModel], BaseModel]] = {}
        self._default: tuple[type[BaseModel], BaseModel] | None = None
        self._static_response: BaseModel | None = None

    @classmethod
    def with_static(cls, response: BaseModel) -> "MockModelClient":
        """Create a client that always returns the same response."""
        client = cls()
        client._static_response = response
        return client

    def register(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        response: BaseModel,
    ) -> None:
        """Register a mock response for a specific prompt combination.

        Matching is prefix-based: if the first 40 chars of system_prompt
        and user_prompt match the registered pair, the response is returned.
        """
        self._responses[(system_prompt[:40], user_prompt[:40])] = (schema, response)

    def set_default(self, schema: type[BaseModel], response: BaseModel) -> None:
        """Set a default response returned when no match is found."""
        self._default = (schema, response)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Return a registered or default structured response.

        Order of precedence:
        1. Static response (if set via with_static)
        2. Registered response matching system + user prompt
           (empty user_prompt in registration = match any user_prompt)
        3. Default response (if set)
        4. ValueError
        """
        if self._static_response is not None:
            if not isinstance(self._static_response, response_schema):
                raise TypeError(
                    f"Static response type {type(self._static_response).__name__} "
                    f"does not match requested schema {response_schema.__name__}"
                )
            return self._static_response

        sys_key = system_prompt[:40]
        # Try exact match first, then wildcard user_prompt
        for (reg_sys, reg_usr), (schema, response) in self._responses.items():
            if reg_sys == sys_key:
                if reg_usr == "" or reg_usr == user_prompt[:40]:
                    if schema is not response_schema:
                        raise TypeError(
                            f"Registered schema {schema.__name__} does not match "
                            f"requested {response_schema.__name__}"
                        )
                    return response

        if self._default is not None:
            schema, response = self._default
            if schema is not response_schema:
                raise TypeError(
                    f"Default schema {schema.__name__} does not match "
                    f"requested {response_schema.__name__}"
                )
            return response

        raise ValueError(
            f"No mock response registered for prompt pair. "
            f"Sys: {system_prompt[:80]}... "
            f"Usr: {user_prompt[:80]}..."
        )
