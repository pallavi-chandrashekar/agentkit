"""PipelineDoctor — incident response agent for data pipelines."""
from agentkit.core.agent import Agent
from agentkit.core.result import AgentResult
from agentkit.llm.provider import LLMProvider
from agentkit.prompts.system import build_system_prompt

from examples.pipeline_doctor.backend import PipelineBackend, MockPipelineBackend
from examples.pipeline_doctor.tools import build_tools


SYSTEM_CONTEXT = """You are an on-call SRE for data pipelines (Airflow / Dagster).
Your job is to diagnose failures and propose fixes.

When given an alert about a failed pipeline, follow this investigation workflow:

1. **Get the lay of the land** — what DAG failed? What's the latest run state?
2. **Identify the failed task(s)** — which step broke? Was it just one task or a chain?
3. **Read the actual error logs** — don't guess from the task name. Get the full trace.
4. **Compare to history** — was this DAG working before? When did it last succeed?
   What's different about the failed run vs the last successful one?
5. **Read the failing code** — understand what the task is trying to do.
6. **Diagnose root cause** — categorize: schema drift / rate limit / OOM / bad data / network / code bug.
7. **Propose a fix** — concrete code change, config change, or operational action.
   Show the diff or new code if applicable.

Output format for your final answer:

**Root cause:** <one sentence>

**Evidence:** <2-3 specific log/code excerpts that prove it>

**Recommended fix:**
```python
# Before
<code or config>
# After
<code or config>
```

**Why this fix:** <one paragraph>

**Severity:** low | medium | high (production impact)
"""


class PipelineDoctor:
    """Diagnoses failed pipeline runs and proposes fixes."""

    def __init__(
        self,
        backend: PipelineBackend | None = None,
        scenario: str = "schema_drift",
        llm: LLMProvider | None = None,
        max_iterations: int = 15,
        on_step: callable = None,
    ):
        self.backend = backend or MockPipelineBackend(scenario=scenario)
        tools = build_tools(self.backend)
        system_prompt = build_system_prompt(tools.names(), task_context=SYSTEM_CONTEXT)
        self.agent = Agent(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            on_step=on_step,
        )

    async def diagnose(self, alert: str) -> AgentResult:
        """Diagnose a failed pipeline given an alert message."""
        return await self.agent.run(alert)

    @property
    def tracer(self):
        return self.agent.tracer
