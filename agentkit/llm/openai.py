"""OpenAI provider with function calling support."""
import json
from agentkit.llm.provider import LLMProvider, Message, ToolCall, LLMResponse


class OpenAIClient(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 4096):
        super().__init__(model, max_tokens)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        system: str,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        openai_messages = [{"role": "system", "content": system}]
        for msg in messages:
            if msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content or "",
                })
            elif msg.role == "assistant" and msg.tool_calls:
                openai_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                openai_messages.append({"role": msg.role, "content": msg.content or ""})

        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": openai_messages,
        }
        if tools:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]

        response = await self.client.chat.completions.create(**params)

        if response.usage:
            self.token_usage["input"] += response.usage.prompt_tokens
            self.token_usage["output"] += response.usage.completion_tokens

        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))

        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=self.model,
        )
