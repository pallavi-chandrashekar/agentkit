"""Shared pytest fixtures."""
import sqlite3
from pathlib import Path

import pytest

from agentkit.llm.provider import LLMProvider, LLMResponse, ToolCall


class MockLLMClient(LLMProvider):
    """Mock LLM that returns scripted responses in order."""

    def __init__(self, responses: list[LLMResponse], model: str = "mock-model"):
        super().__init__(model=model, max_tokens=1000)
        self._responses = list(responses)
        self.call_count = 0
        self.calls: list[dict] = []

    async def complete(self, system, messages, tools=None):
        self.call_count += 1
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        if not self._responses:
            return LLMResponse(text="(out of mock responses)", stop_reason="end_turn")
        response = self._responses.pop(0)
        # Mimic provider behavior of accumulating usage
        self.token_usage["input"] += response.input_tokens
        self.token_usage["output"] += response.output_tokens
        if not response.model:
            response.model = self.model
        return response


@pytest.fixture
def mock_llm():
    """Helper to create a MockLLMClient with given scripted responses."""
    def _make(responses: list[LLMResponse]):
        return MockLLMClient(responses=responses)
    return _make


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a tiny SQLite DB for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL);
        INSERT INTO users (id, name) VALUES (1, 'Alice'), (2, 'Bob');
        INSERT INTO orders (user_id, total) VALUES (1, 100.0), (1, 50.0), (2, 75.0);
    """)
    conn.commit()
    conn.close()
    return db_path
