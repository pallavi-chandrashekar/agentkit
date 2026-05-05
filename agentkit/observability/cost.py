"""Token cost tracking. Prices in USD per 1M tokens."""
from dataclasses import dataclass

# As of mid-2026 — easy to update when prices change
MODEL_PRICING = {
    # Anthropic
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Google
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Local
    "llama3.1": {"input": 0.0, "output": 0.0},
}


@dataclass
class CostEntry:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostTracker:
    """Tracks token usage and dollar cost across LLM calls."""

    def __init__(self):
        self.entries: list[CostEntry] = []

    def record(self, model: str, input_tokens: int, output_tokens: int) -> CostEntry:
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        entry = CostEntry(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self.entries.append(entry)
        return entry

    def total_cost(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    def total_input_tokens(self) -> int:
        return sum(e.input_tokens for e in self.entries)

    def total_output_tokens(self) -> int:
        return sum(e.output_tokens for e in self.entries)

    def summary(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost(), 6),
            "input_tokens": self.total_input_tokens(),
            "output_tokens": self.total_output_tokens(),
            "calls": len(self.entries),
        }
