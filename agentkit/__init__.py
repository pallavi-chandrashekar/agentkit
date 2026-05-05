"""AgentKit — Production-grade AI agent framework with built-in observability and evaluation."""

__version__ = "0.1.0"

from agentkit.core.agent import Agent
from agentkit.core.result import AgentResult
from agentkit.tools.decorator import tool
from agentkit.tools.registry import ToolRegistry

__all__ = ["Agent", "AgentResult", "tool", "ToolRegistry"]
