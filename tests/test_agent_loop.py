"""Tests for the Agent class with mocked LLM."""
import pytest

from agentkit.core.agent import Agent
from agentkit.llm.provider import LLMResponse, ToolCall
from agentkit.tools.decorator import tool
from agentkit.tools.registry import ToolRegistry


@tool
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool
async def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


class TestAgentLoop:
    async def test_immediate_answer(self, mock_llm):
        """Agent that returns text immediately without tool calls."""
        llm = mock_llm([
            LLMResponse(text="The answer is 42.", stop_reason="end_turn", input_tokens=10, output_tokens=5),
        ])
        agent = Agent(tools=ToolRegistry([add]), llm=llm)
        result = await agent.run("What is the answer to everything?")
        assert result.success
        assert result.answer == "The answer is 42."
        assert result.iterations == 1
        assert result.tool_calls == 0
        assert result.confidence == "high"

    async def test_single_tool_call(self, mock_llm):
        """Agent calls a tool, then returns final answer."""
        llm = mock_llm([
            LLMResponse(
                text="Computing.",
                tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 5, "b": 7})],
                stop_reason="tool_use",
                input_tokens=20, output_tokens=10,
            ),
            LLMResponse(text="The sum is 12.", stop_reason="end_turn", input_tokens=15, output_tokens=8),
        ])
        agent = Agent(tools=ToolRegistry([add]), llm=llm)
        result = await agent.run("What is 5 + 7?")
        assert result.success
        assert result.answer == "The sum is 12."
        assert result.tool_calls == 1
        assert result.iterations == 2

    async def test_multiple_tool_calls(self, mock_llm):
        """Agent uses two tools across iterations."""
        llm = mock_llm([
            LLMResponse(
                tool_calls=[ToolCall(id="t1", name="add", arguments={"a": 2, "b": 3})],
                stop_reason="tool_use",
            ),
            LLMResponse(
                tool_calls=[ToolCall(id="t2", name="multiply", arguments={"a": 5, "b": 4})],
                stop_reason="tool_use",
            ),
            LLMResponse(text="Result is 20.", stop_reason="end_turn"),
        ])
        agent = Agent(tools=ToolRegistry([add, multiply]), llm=llm)
        result = await agent.run("Compute (2+3)*4")
        assert result.success
        assert result.tool_calls == 2
        assert "20" in result.answer

    async def test_tool_error_recovers(self, mock_llm):
        """Agent receives a tool error, then succeeds on retry."""
        @tool
        async def maybe_fails(x: int) -> int:
            """Sometimes fails."""
            if x < 0:
                from agentkit.tools.base import ToolError
                raise ToolError("x must be positive")
            return x * 2

        llm = mock_llm([
            LLMResponse(
                tool_calls=[ToolCall(id="t1", name="maybe_fails", arguments={"x": -1})],
                stop_reason="tool_use",
            ),
            LLMResponse(
                tool_calls=[ToolCall(id="t2", name="maybe_fails", arguments={"x": 5})],
                stop_reason="tool_use",
            ),
            LLMResponse(text="Got 10.", stop_reason="end_turn"),
        ])
        agent = Agent(tools=ToolRegistry([maybe_fails]), llm=llm)
        result = await agent.run("Double this")
        assert result.success
        assert result.tool_calls == 2

    async def test_max_iterations_exceeded(self, mock_llm):
        """Agent that loops forever hits max_iterations and reports failure."""
        # Provide many tool-call responses in a row so the agent never reaches an answer
        responses = [
            LLMResponse(
                tool_calls=[ToolCall(id=f"t{i}", name="add", arguments={"a": 1, "b": 1})],
                stop_reason="tool_use",
            )
            for i in range(10)
        ]
        llm = mock_llm(responses)
        agent = Agent(tools=ToolRegistry([add]), llm=llm, max_iterations=3)
        result = await agent.run("Loop")
        assert not result.success
        assert result.iterations == 3
        assert result.error and "Max iterations" in result.error

    async def test_unknown_tool_handled(self, mock_llm):
        """Agent gets an unknown tool error in observation, then recovers."""
        llm = mock_llm([
            LLMResponse(
                tool_calls=[ToolCall(id="t1", name="nonexistent", arguments={})],
                stop_reason="tool_use",
            ),
            LLMResponse(text="That tool doesn't exist; here's my answer instead.", stop_reason="end_turn"),
        ])
        agent = Agent(tools=ToolRegistry([add]), llm=llm)
        result = await agent.run("Try a fake tool")
        assert result.success
        assert "doesn't exist" in result.answer
