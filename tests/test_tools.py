"""Tests for tool framework: registry, decorator."""
import pytest

from agentkit.tools.base import ToolError, ToolResult
from agentkit.tools.decorator import tool
from agentkit.tools.registry import ToolRegistry


@tool
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(name="say_hello", description="Greet a person.")
async def _hello(name: str) -> str:
    return f"Hello, {name}!"


class TestToolDecorator:
    async def test_basic_tool(self):
        result = await add.execute(a=2, b=3)
        assert result.output == 5

    async def test_schema_extraction(self):
        schema = add.to_schema()
        assert schema["name"] == "add"
        assert "Add two numbers" in schema["description"]
        assert schema["input_schema"]["properties"]["a"]["type"] == "integer"
        assert schema["input_schema"]["properties"]["b"]["type"] == "integer"
        assert "a" in schema["input_schema"]["required"]

    async def test_custom_name_and_description(self):
        assert _hello.name == "say_hello"
        assert _hello.description == "Greet a person."

    async def test_tool_returns_tool_result(self):
        @tool
        async def explicit_result(x: str) -> ToolResult:
            """Returns a custom ToolResult."""
            return ToolResult(output={"key": x}, display=f"x={x}")

        result = await explicit_result.execute(x="test")
        assert result.output == {"key": "test"}
        assert result.display == "x=test"

    async def test_sync_function_rejected(self):
        with pytest.raises(TypeError, match="async function"):
            @tool
            def sync_fn(x: int) -> int:
                return x


class TestToolRegistry:
    async def test_register_and_get(self):
        registry = ToolRegistry([add, _hello])
        assert "add" in registry
        assert "say_hello" in registry
        assert len(registry) == 2

    async def test_duplicate_registration_raises(self):
        registry = ToolRegistry([add])
        with pytest.raises(ValueError, match="already registered"):
            registry.register(add)

    async def test_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ToolError, match="Unknown tool"):
            registry.get("nope")

    async def test_execute(self):
        registry = ToolRegistry([add])
        result = await registry.execute("add", {"a": 10, "b": 20})
        assert result.output == 30

    async def test_schemas_export(self):
        registry = ToolRegistry([add, _hello])
        schemas = registry.schemas()
        assert len(schemas) == 2
        names = {s["name"] for s in schemas}
        assert names == {"add", "say_hello"}
