"""@tool decorator — turn an async function into an LLM-callable Tool.

Usage:
    @tool
    async def list_tables() -> ToolResult:
        '''List all tables in the database.'''
        ...

    @tool(name="custom_name", description="Override docstring")
    async def my_func(query: str, limit: int = 10) -> ToolResult:
        '''...'''
"""
import inspect
from functools import wraps
from typing import Callable, get_type_hints

from agentkit.tools.base import Tool, ToolResult


def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
):
    """Decorator that converts an async function into a Tool instance."""

    def wrap(fn: Callable) -> Tool:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError(f"@tool requires an async function, got {fn.__name__}")

        tool_name = name or fn.__name__
        tool_desc = description or (fn.__doc__ or "").strip().split("\n")[0]
        if not tool_desc:
            raise ValueError(f"Tool {tool_name} must have a docstring or explicit description")

        # Build JSON schema from function signature
        sig = inspect.signature(fn)
        type_hints = get_type_hints(fn)
        properties: dict = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            py_type = type_hints.get(param_name, str)
            json_schema = _python_type_to_json_schema(py_type)
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            else:
                json_schema["default"] = param.default
            properties[param_name] = json_schema

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        class FunctionTool(Tool):
            def __init__(self):
                self.name = tool_name
                self.description = tool_desc
                self.input_schema = input_schema
                self._fn = fn

            async def execute(self, **kwargs) -> ToolResult:
                result = await self._fn(**kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult(output=result)

        instance = FunctionTool()
        instance.__name__ = tool_name  # for debugging
        return instance

    if func is None:
        return wrap
    return wrap(func)


def _python_type_to_json_schema(py_type) -> dict:
    """Convert a Python type hint to a JSON schema fragment."""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    if py_type in type_map:
        return type_map[py_type].copy()

    origin = getattr(py_type, "__origin__", None)
    if origin is list:
        return {"type": "array"}
    if origin is dict:
        return {"type": "object"}

    # Fallback
    return {"type": "string"}
