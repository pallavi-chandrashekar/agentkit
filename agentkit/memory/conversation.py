"""ConversationMemory — chat history that persists across agent loop iterations."""
from agentkit.llm.provider import Message


class ConversationMemory:
    """Stores the full message history for a conversation."""

    def __init__(self, messages: list[Message] | None = None):
        self._messages: list[Message] = list(messages) if messages else []

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def add_user(self, content: str) -> None:
        self.add(Message(role="user", content=content))

    def add_assistant(self, content: str | None = None, tool_calls: list | None = None) -> None:
        self.add(Message(role="assistant", content=content, tool_calls=tool_calls or []))

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.add(Message(role="tool", content=content, tool_call_id=tool_call_id))

    def messages(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
