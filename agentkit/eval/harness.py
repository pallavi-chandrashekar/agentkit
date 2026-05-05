"""EvalHarness — run an agent across a set of test cases and report metrics."""
from dataclasses import dataclass, field
from typing import Callable

from agentkit.core.agent import Agent
from agentkit.core.result import AgentResult


@dataclass
class EvalCase:
    """A single evaluation case."""
    id: str
    task: str
    expected: str | None = None  # Expected answer (for exact-match scoring)
    grader: Callable[[AgentResult], bool] | None = None  # Custom grader
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of running one EvalCase."""
    case_id: str
    passed: bool
    answer: str
    iterations: int
    tool_calls: int
    cost_usd: float
    duration_seconds: float
    error: str | None = None


class EvalHarness:
    """Runs an agent across a set of EvalCases and computes metrics."""

    def __init__(self, agent_factory: Callable[[], Agent]):
        """Args:
            agent_factory: Zero-arg callable that returns a fresh Agent instance.
                           Used so each case starts with clean memory.
        """
        self.agent_factory = agent_factory

    async def run(self, cases: list[EvalCase], verbose: bool = False) -> list[EvalResult]:
        results = []
        for case in cases:
            if verbose:
                print(f"  [eval] {case.id}: {case.task[:60]}...")
            agent = self.agent_factory()
            try:
                agent_result = await agent.run(case.task)
                passed = self._grade(case, agent_result)
                results.append(EvalResult(
                    case_id=case.id,
                    passed=passed,
                    answer=agent_result.answer,
                    iterations=agent_result.iterations,
                    tool_calls=agent_result.tool_calls,
                    cost_usd=agent_result.cost_usd,
                    duration_seconds=agent_result.duration_seconds,
                    error=agent_result.error,
                ))
                if verbose:
                    status = "✓" if passed else "✗"
                    print(f"    {status} {agent_result.summary()}")
            except Exception as e:
                results.append(EvalResult(
                    case_id=case.id,
                    passed=False,
                    answer="",
                    iterations=0,
                    tool_calls=0,
                    cost_usd=0.0,
                    duration_seconds=0.0,
                    error=str(e),
                ))
                if verbose:
                    print(f"    ✗ ERROR: {e}")
        return results

    @staticmethod
    def _grade(case: EvalCase, result: AgentResult) -> bool:
        """Grade a result. Custom grader takes precedence over expected match."""
        if case.grader:
            try:
                return case.grader(result)
            except Exception:
                return False
        if case.expected is None:
            return result.success
        # Lenient string match: expected appears in answer (case-insensitive)
        return case.expected.lower().strip() in result.answer.lower()
