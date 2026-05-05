"""Tests for the eval harness."""
from agentkit.core.agent import Agent
from agentkit.eval.harness import EvalCase, EvalHarness
from agentkit.eval.metrics import compute_metrics
from agentkit.llm.provider import LLMResponse
from agentkit.tools.decorator import tool
from agentkit.tools.registry import ToolRegistry


@tool
async def echo(message: str) -> str:
    """Echo a message."""
    return message


class TestEvalHarness:
    async def test_run_passes(self, mock_llm):
        llm = mock_llm([LLMResponse(text="Paris", stop_reason="end_turn")])
        harness = EvalHarness(agent_factory=lambda: Agent(tools=ToolRegistry([echo]), llm=llm))
        results = await harness.run([EvalCase(id="t1", task="Capital of France?", expected="Paris")])
        assert len(results) == 1
        assert results[0].passed
        assert "Paris" in results[0].answer

    async def test_run_fails(self, mock_llm):
        llm = mock_llm([LLMResponse(text="Berlin", stop_reason="end_turn")])
        harness = EvalHarness(agent_factory=lambda: Agent(tools=ToolRegistry([echo]), llm=llm))
        results = await harness.run([EvalCase(id="t1", task="Capital of France?", expected="Paris")])
        assert not results[0].passed

    async def test_custom_grader(self, mock_llm):
        llm = mock_llm([LLMResponse(text="42", stop_reason="end_turn")])
        harness = EvalHarness(agent_factory=lambda: Agent(tools=ToolRegistry([echo]), llm=llm))
        results = await harness.run([
            EvalCase(id="t1", task="Number?", grader=lambda r: "42" in r.answer),
        ])
        assert results[0].passed

    async def test_compute_metrics(self):
        from agentkit.eval.harness import EvalResult
        results = [
            EvalResult(case_id="a", passed=True, answer="x", iterations=2, tool_calls=1, cost_usd=0.01, duration_seconds=1.0),
            EvalResult(case_id="b", passed=False, answer="y", iterations=5, tool_calls=3, cost_usd=0.05, duration_seconds=3.0),
            EvalResult(case_id="c", passed=True, answer="z", iterations=1, tool_calls=0, cost_usd=0.001, duration_seconds=0.5),
        ]
        m = compute_metrics(results)
        assert m["total"] == 3
        assert m["passed"] == 2
        assert m["success_rate"] == round(2/3, 3)
        assert m["avg_iterations"] == round((2 + 5 + 1) / 3, 2)
