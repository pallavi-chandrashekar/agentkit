"""Ollama provider for local models."""
import json
import httpx
from agentkit.llm.provider import LLMProvider, Message, ToolCall, LLMResponse


class OllamaClient(LLMProvider):
    def __init__(self, model: str = "llama3.1", max_tokens: int = 4096, base_url: str = "http://localhost:11434"):
        super().__init__(model, max_tokens)
        self.base_url = base_url

    async def complete(
        self,
        system: str,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        ollama_messages = [{"role": "system", "content": system}]
        for msg in messages:
            if msg.role == "tool":
                ollama_messages.append({
                    "role": "tool",
                    "content": msg.content or "",
                })
            elif msg.role == "assistant" and msg.tool_calls:
                ollama_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"function": {"name": tc.name, "arguments": tc.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
            else:
                ollama_messages.append({"role": msg.role, "content": msg.content or ""})

        body = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"num_predict": self.max_tokens},
        }
        if tools:
            body["tools"] = [
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

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=body)
            response.raise_for_status()
            data = response.json()

        if data.get("prompt_eval_count") or data.get("eval_count"):
            self.token_usage["input"] += data.get("prompt_eval_count", 0)
            self.token_usage["output"] += data.get("eval_count", 0)

        message_data = data.get("message", {})
        text = message_data.get("content", "")
        tool_calls = []
        for tc in message_data.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(ToolCall(
                id=f"ollama_call_{len(tool_calls)}",
                name=fn.get("name", ""),
                arguments=args,
            ))

        return LLMResponse(
            text=text if text else None,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            model=self.model,
        )
