"""ToolRegistry — register, lookup, schema export."""
from agentkit.tools.base import Tool, ToolError, ToolResult


class ToolRegistry:
    """Registry of tools available to an agent."""

    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        if tools:
            for t in tools:
                self.register(t)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}", recoverable=True)
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def schemas(self) -> list[dict]:
        """Export all tools as LLM-compatible schemas."""
        return [t.to_schema() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool = self.get(name)
        return await tool.execute(**arguments)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
