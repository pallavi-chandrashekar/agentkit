"""Anthropic Claude provider with native tool_use support."""
from agentkit.llm.provider import LLMProvider, Message, ToolCall, LLMResponse


class ClaudeClient(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", max_tokens: int = 4096):
        super().__init__(model, max_tokens)
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        system: str,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        # Convert AgentKit messages → Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg.role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content or "",
                    }],
                })
            elif msg.role == "assistant" and msg.tool_calls:
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content or ""})

        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": anthropic_messages,
        }
        if tools:
            params["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"],
                }
                for t in tools
            ]

        response = await self.client.messages.create(**params)

        # Track usage
        if response.usage:
            self.token_usage["input"] += response.usage.input_tokens
            self.token_usage["output"] += response.usage.output_tokens

        # Parse response into unified format
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
            model=self.model,
        )
