"""Tests for memory primitives."""
from agentkit.llm.provider import Message, ToolCall
from agentkit.memory.conversation import ConversationMemory
from agentkit.memory.working import WorkingMemory


class TestConversationMemory:
    def test_add_user(self):
        mem = ConversationMemory()
        mem.add_user("Hello")
        msgs = mem.messages()
        assert len(msgs) == 1
        assert msgs[0].role == "user"
        assert msgs[0].content == "Hello"

    def test_add_assistant_with_tool_calls(self):
        mem = ConversationMemory()
        tc = ToolCall(id="call_1", name="get_weather", arguments={"city": "NYC"})
        mem.add_assistant(content="Let me check", tool_calls=[tc])
        msgs = mem.messages()
        assert msgs[0].role == "assistant"
        assert msgs[0].tool_calls[0].name == "get_weather"

    def test_add_tool_result(self):
        mem = ConversationMemory()
        mem.add_tool_result("call_1", "65F sunny")
        msgs = mem.messages()
        assert msgs[0].role == "tool"
        assert msgs[0].tool_call_id == "call_1"
        assert msgs[0].content == "65F sunny"

    def test_clear(self):
        mem = ConversationMemory()
        mem.add_user("hi")
        assert len(mem) == 1
        mem.clear()
        assert len(mem) == 0


class TestWorkingMemory:
    def test_set_get(self):
        mem = WorkingMemory()
        mem.set("foo", 42)
        assert mem.get("foo") == 42

    def test_default(self):
        mem = WorkingMemory()
        assert mem.get("missing", "default") == "default"

    def test_has(self):
        mem = WorkingMemory()
        mem.set("x", 1)
        assert mem.has("x")
        assert "x" in mem
        assert not mem.has("y")

    def test_clear(self):
        mem = WorkingMemory()
        mem.set("a", 1)
        mem.set("b", 2)
        assert len(mem) == 2
        mem.clear()
        assert len(mem) == 0
