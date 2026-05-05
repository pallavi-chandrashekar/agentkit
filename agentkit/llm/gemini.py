"""Google Gemini provider with function calling support."""
import json
from agentkit.llm.provider import LLMProvider, Message, ToolCall, LLMResponse


class GeminiClient(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", max_tokens: int = 4096):
        super().__init__(model, max_tokens)
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    async def complete(
        self,
        system: str,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        # Build a single prompt (Gemini API is simpler — fold system into first turn)
        parts = [f"System: {system}\n"]
        for msg in messages:
            if msg.role == "tool":
                parts.append(f"Tool result ({msg.tool_call_id}): {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content or ''}")
                for tc in msg.tool_calls:
                    parts.append(f"  → called {tc.name}({json.dumps(tc.arguments)})")
            else:
                parts.append(f"User: {msg.content}")

        # Append tool schema as instruction (no native tool_use in basic Gemini API)
        if tools:
            tool_descriptions = "\n".join(
                f"- {t['name']}: {t['description']} | Schema: {json.dumps(t['input_schema'])}"
                for t in tools
            )
            parts.append(
                f"\n\nAvailable tools:\n{tool_descriptions}\n\n"
                "If you need to use a tool, respond with ONLY a JSON object:\n"
                '{"tool": "tool_name", "arguments": {...}}\n'
                "Otherwise respond with text answer."
            )

        prompt = "\n".join(parts)
        model = self._genai.GenerativeModel(self._model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config={"max_output_tokens": self.max_tokens},
        )

        usage = getattr(response, "usage_metadata", None)
        if usage:
            self.token_usage["input"] += getattr(usage, "prompt_token_count", 0)
            self.token_usage["output"] += getattr(usage, "candidates_token_count", 0)

        text = response.text
        # Try to detect tool call in JSON form
        tool_calls = []
        text_response = text
        try:
            # Look for JSON block
            stripped = text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                parsed = json.loads(stripped)
                if "tool" in parsed and "arguments" in parsed:
                    tool_calls.append(ToolCall(
                        id=f"gemini_call_{len(tool_calls)}",
                        name=parsed["tool"],
                        arguments=parsed["arguments"],
                    ))
                    text_response = None
        except (json.JSONDecodeError, KeyError):
            pass

        return LLMResponse(
            text=text_response,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            model=self.model,
        )
