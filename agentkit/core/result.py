"""AgentResult — what an agent returns after running on a task."""
from dataclasses import dataclass, field

from agentkit.core.step import Step


@dataclass
class AgentResult:
    """Final result of an agent execution."""
    answer: str
    steps: list[Step] = field(default_factory=list)
    confidence: str = "medium"  # 'low' | 'medium' | 'high'
    iterations: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    success: bool = True
    error: str | None = None
    trace_path: str | None = None  # Path to HTML trace (if Agent has trace_dir set)

    def summary(self) -> str:
        """Short human-readable summary line."""
        return (
            f"{self.iterations} iter · {self.tool_calls} tools · "
            f"${self.cost_usd:.4f} · {self.duration_seconds:.1f}s · "
            f"confidence: {self.confidence}"
        )
