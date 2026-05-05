"""Abstract LLM provider interface for AgentKit.

Unlike simple chat wrappers, this interface is built for agent loops:
- Native tool_use support (returns parsed tool calls, not just text)
- Unified response across providers
- Token usage tracking
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A single message in a conversation.

    role: 'user' | 'assistant' | 'tool'
    content: text content (for user/assistant) or tool result (for tool)
    tool_call_id: required when role == 'tool'
    tool_calls: optional list of tool calls made by the assistant
    """
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list["ToolCall"] = field(default_factory=list)


@dataclass
class ToolCall:
    """A single tool invocation requested by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Unified response from any LLM provider.

    Either text is set (for plain text responses) or tool_calls is non-empty
    (for tool use). Both can be set for providers that support thinking + tool use.
    """
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None  # 'end_turn' | 'tool_use' | 'max_tokens' | etc.
    input_tokens: int = 0
    output_tokens: int = 0
    model: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        self.token_usage = {"input": 0, "output": 0}

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send messages + tools, get back text or tool calls.

        Args:
            system: System prompt
            messages: Conversation history
            tools: Optional list of tool schemas in unified format:
                   [{"name": str, "description": str, "input_schema": dict}, ...]

        Returns:
            LLMResponse with either text or tool_calls populated
        """
        ...

    def get_token_usage(self) -> dict[str, int]:
        return {**self.token_usage}
