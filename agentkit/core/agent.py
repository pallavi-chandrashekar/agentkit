"""Agent — orchestrates the Plan-Act-Reflect loop.

The agent is the main entry point. It composes:
- An LLM provider (for reasoning)
- A tool registry (for acting)
- Conversation + working memory
- A tracer (for observability)
- A cost tracker (for $ accounting)
"""
import time
from pathlib import Path

from agentkit.core.result import AgentResult
from agentkit.core.step import Step
from agentkit.llm.provider import LLMProvider, Message
from agentkit.llm.factory import create_llm_client
from agentkit.memory.conversation import ConversationMemory
from agentkit.memory.working import WorkingMemory
from agentkit.observability.cost import CostTracker
from agentkit.observability.tracer import Tracer
from agentkit.observability.viewer import render_tracer_html
from agentkit.prompts.system import build_system_prompt
from agentkit.tools.base import ToolError
from agentkit.tools.registry import ToolRegistry


class Agent:
    """Plan-Act-Reflect agent."""

    def __init__(
        self,
        tools: ToolRegistry,
        llm: LLMProvider | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 15,
        on_step: callable = None,
        trace_dir: str | Path | None = None,
    ):
        """
        Args:
            tools: Tool registry the agent can use.
            llm: LLM provider (auto-detected from env if None).
            system_prompt: System prompt (default built from tool names).
            max_iterations: Hard cap on agent loop iterations.
            on_step: Optional callback fired for each Step (for streaming).
            trace_dir: If set, JSONL + HTML traces are written here on each run.
                       Pass `None` to disable, or a path like "./traces".
        """
        self.tools = tools
        self.llm = llm or create_llm_client()
        self.system_prompt = system_prompt or build_system_prompt(tools.names())
        self.max_iterations = max_iterations
        self.on_step = on_step
        self.trace_dir = Path(trace_dir) if trace_dir else None

        self.conversation = ConversationMemory()
        self.working = WorkingMemory()
        self.tracer = Tracer()
        self.cost = CostTracker()

    async def run(self, task: str) -> AgentResult:
        """Run the agent on a single task. Returns AgentResult."""
        start = time.time()
        self.conversation.add_user(task)
        self.tracer.record("task_start", {"task": task})
        self._emit(Step(type="task", content=task))

        steps: list[Step] = []
        iterations = 0
        tool_calls = 0
        final_answer: str | None = None
        success = True
        error: str | None = None

        try:
            while iterations < self.max_iterations:
                iterations += 1

                self.tracer.start_timer("llm_call")
                response = await self.llm.complete(
                    system=self.system_prompt,
                    messages=self.conversation.messages(),
                    tools=self.tools.schemas(),
                )
                duration_ms = self.tracer.stop_timer("llm_call")
                self.cost.record(self.llm.model, response.input_tokens, response.output_tokens)

                self.tracer.record("llm_call", {
                    "model": self.llm.model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "stop_reason": response.stop_reason,
                    "tool_calls_count": len(response.tool_calls),
                }, duration_ms=duration_ms)

                # Save the assistant's response (text + any tool calls) to conversation
                self.conversation.add_assistant(
                    content=response.text,
                    tool_calls=response.tool_calls,
                )

                # No tool calls → final answer
                if not response.tool_calls:
                    final_answer = response.text or "(no answer)"
                    step = Step(type="answer", content=final_answer)
                    steps.append(step)
                    self.tracer.record("answer", {"text": final_answer})
                    self._emit(step)
                    break

                # If model produced text alongside tool calls, treat as planning/reasoning
                if response.text:
                    plan_step = Step(type="plan", content=response.text)
                    steps.append(plan_step)
                    self.tracer.record("plan", {"text": response.text})
                    self._emit(plan_step)

                # Execute tool calls
                for tc in response.tool_calls:
                    tool_calls += 1
                    self.tracer.start_timer(f"tool_{tc.id}")
                    action_step = Step(
                        type="action",
                        content=f"{tc.name}({_format_args(tc.arguments)})",
                        data={"tool": tc.name, "arguments": tc.arguments, "id": tc.id},
                    )
                    steps.append(action_step)
                    self.tracer.record("action", action_step.data)
                    self._emit(action_step)

                    try:
                        result = await self.tools.execute(tc.name, tc.arguments)
                        observation_text = str(result.output)
                        obs_step = Step(
                            type="observation",
                            content=result.display,
                            data={"tool_call_id": tc.id, "output": result.output},
                        )
                    except ToolError as e:
                        observation_text = f"Tool error: {e}"
                        obs_step = Step(
                            type="observation",
                            content=observation_text,
                            data={"tool_call_id": tc.id, "error": str(e)},
                        )
                    except Exception as e:
                        observation_text = f"Tool failed unexpectedly: {e}"
                        obs_step = Step(
                            type="observation",
                            content=observation_text,
                            data={"tool_call_id": tc.id, "error": str(e)},
                        )

                    duration_ms = self.tracer.stop_timer(f"tool_{tc.id}")
                    steps.append(obs_step)
                    self.tracer.record("observation", obs_step.data, duration_ms=duration_ms)
                    self._emit(obs_step)

                    # Feed result back to LLM
                    self.conversation.add_tool_result(tc.id, observation_text)

            else:
                # max_iterations exceeded
                success = False
                error = f"Max iterations ({self.max_iterations}) exceeded without reaching final answer"
                final_answer = error

        except Exception as e:
            success = False
            error = f"Agent failed: {e}"
            final_answer = error
            self.tracer.record("error", {"message": str(e)})

        duration = time.time() - start
        confidence = self._compute_confidence(success, iterations, tool_calls, error)
        cost_summary = self.cost.summary()

        result = AgentResult(
            answer=final_answer or "",
            steps=steps,
            confidence=confidence,
            iterations=iterations,
            tool_calls=tool_calls,
            cost_usd=cost_summary["total_cost_usd"],
            input_tokens=cost_summary["input_tokens"],
            output_tokens=cost_summary["output_tokens"],
            duration_seconds=duration,
            success=success,
            error=error,
        )
        self.tracer.record("task_end", {"success": success, "duration_seconds": duration})

        if self.trace_dir:
            try:
                jsonl_path = self.trace_dir / f"{self.tracer.run_id}.jsonl"
                self.tracer.write_jsonl(jsonl_path)
                html_path = self.trace_dir / f"{self.tracer.run_id}.html"
                render_tracer_html(self.tracer, html_path, title=f"Agent: {task[:60]}")
                # Also write/symlink "latest" for convenience
                latest_html = self.trace_dir / "latest.html"
                latest_html.write_text(html_path.read_text())
                result.trace_path = str(html_path)
            except Exception:
                pass  # never let trace writing break the agent

        return result

    def _emit(self, step: Step) -> None:
        if self.on_step:
            try:
                self.on_step(step)
            except Exception:
                pass

    @staticmethod
    def _compute_confidence(success: bool, iterations: int, tool_calls: int, error: str | None) -> str:
        if not success:
            return "low"
        if error:
            return "low"
        if iterations <= 3 and tool_calls <= 2:
            return "high"
        if iterations <= 8:
            return "medium"
        return "low"


def _format_args(args: dict, max_len: int = 80) -> str:
    parts = [f"{k}={v!r}" for k, v in args.items()]
    s = ", ".join(parts)
    return s if len(s) <= max_len else s[:max_len] + "..."
