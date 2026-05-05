"""DataAssistant agent — composes the AgentKit core with SQL tools."""
from pathlib import Path

from agentkit.core.agent import Agent
from agentkit.core.result import AgentResult
from agentkit.llm.provider import LLMProvider
from agentkit.prompts.system import build_system_prompt
from examples.data_assistant.tools import build_tools


SYSTEM_CONTEXT = """You are a data analyst assistant. Your job is to answer business
questions by querying a SQL database.

Workflow you should always follow:
1. List tables to understand what data is available
2. Describe relevant tables to learn columns, types, and see sample rows
3. Write a SQL query that answers the question
4. Validate the result makes sense (e.g., 0 rows might mean wrong filter)
5. If results look wrong, try a different query — don't give up after one attempt
6. Present the final answer in plain English with the key number

Important:
- Use SQLite syntax (date('now', '-1 month'), strftime(), etc.)
- Always JOIN to get human-readable values (e.g., product name, not product_id)
- For "last month" use date('now', 'start of month', '-1 month') and date('now', 'start of month')
- Round currency to 2 decimals
- If the user's question is ambiguous, make a reasonable assumption and state it"""


class DataAssistant:
    """Wrapper around Agent with SQL tools and a data-analyst system prompt."""

    def __init__(
        self,
        db_path: str | Path,
        llm: LLMProvider | None = None,
        max_iterations: int = 12,
        on_step: callable = None,
        trace_dir: str | Path | None = None,
    ):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. "
                f"Run `python -m examples.data_assistant.seed_db` to create one."
            )

        tools = build_tools(self.db_path)
        system_prompt = build_system_prompt(tools.names(), task_context=SYSTEM_CONTEXT)

        self.agent = Agent(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            on_step=on_step,
            trace_dir=trace_dir,
        )

    async def ask(self, question: str) -> AgentResult:
        """Ask a question. Returns AgentResult with answer + trace + cost."""
        return await self.agent.run(question)

    @property
    def tracer(self):
        return self.agent.tracer
