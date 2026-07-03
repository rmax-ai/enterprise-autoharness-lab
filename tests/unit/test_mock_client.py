"""Tests for MockModelClient."""

from pydantic import BaseModel

from autoharness_lab.model_clients.mock import MockModelClient
from autoharness_lab.models import ModelClient


class MockResponse(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}
    code: str
    reasoning: str = ""


class TestMockClient:
    def test_implements_model_client_protocol(self):
        client = MockModelClient()
        assert isinstance(client, ModelClient)

    def test_returns_registered_response(self):
        client = MockModelClient()
        client.register("test prompt", "test prompt", MockResponse, MockResponse(code="x = 1"))
        result = client.generate_structured("test prompt", "test prompt", MockResponse)
        assert result.code == "x = 1"

    def test_returns_default_when_no_match(self):
        client = MockModelClient()
        client.set_default(MockResponse, MockResponse(code="default"))
        result = client.generate_structured("anything", "anything", MockResponse)
        assert result.code == "default"

    def test_raises_when_no_match_and_no_default(self):
        client = MockModelClient()
        try:
            client.generate_structured("unmatched", "unmatched", MockResponse)
            assert False, "Should have raised"
        except ValueError as e:
            assert "No mock" in str(e)

    def test_returns_static_response(self):
        client = MockModelClient.with_static(MockResponse(code="static"))
        result = client.generate_structured("any", "any", MockResponse)
        assert result.code == "static"

    def test_schema_mismatch_raises(self):
        client = MockModelClient()

        class OtherSchema(BaseModel):
            model_config = {"extra": "forbid", "frozen": True}
            value: int

        client.register("a", "b", OtherSchema, OtherSchema(value=42))
        try:
            client.generate_structured("a", "b", MockResponse)
            assert False, "Should have raised"
        except TypeError as e:
            assert "schema" in str(e).lower() or "type" in str(e).lower()
