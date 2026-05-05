"""Tool base classes and result types."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Result of a tool execution.

    output: The actual return value (any JSON-serializable type)
    display: Optional short string for the trace viewer (defaults to repr(output))
    """
    output: Any
    display: str | None = None

    def __post_init__(self):
        if self.display is None:
            output_str = str(self.output)
            self.display = output_str if len(output_str) <= 200 else output_str[:200] + "..."


class ToolError(Exception):
    """Raised when a tool fails. Captured by the agent loop and fed back to the LLM."""

    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


class Tool(ABC):
    """Abstract base class for tools.

    Most tools are created via the @tool decorator (see decorator.py),
    but you can subclass Tool directly for stateful tools.
    """

    name: str
    description: str
    input_schema: dict  # JSON schema

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments. Return a ToolResult or raise ToolError."""
        ...

    def to_schema(self) -> dict:
        """Export this tool as a unified LLM tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
