"""ReproAgent — research paper reproduction planner."""
from pathlib import Path

from agentkit.core.agent import Agent
from agentkit.core.result import AgentResult
from agentkit.llm.provider import LLMProvider
from agentkit.prompts.system import build_system_prompt

from examples.repro_agent.tools import build_tools


SYSTEM_CONTEXT = """You are a research engineer who specializes in reproducing
published machine learning and software engineering papers. Given a paper,
your job is to produce a complete reproduction plan and skeleton code.

Workflow:

1. **Discover** — list available papers if needed; pick the right one.
2. **Skim** — read the abstract to understand the paper's core claim.
3. **Extract testable claims** — read the results/evaluation section. Find SPECIFIC
   numerical claims (e.g., "F1 = 0.868", "BLEU 28.4 on WMT 2014 EN-DE"). Don't
   accept vague claims; extract concrete numbers and conditions.
4. **Identify methodology** — read the method/architecture/model section. Note
   key hyperparameters, datasets, hardware requirements.
5. **Find code/data references** — search the paper for "github", "code", "dataset",
   "available at", "https://", etc. Note any links.
6. **Write the artifacts** — produce these files in the workspace:
     - `plan.md` — complete reproduction plan: setup, datasets, training, evaluation
     - `claims.md` — bullet list of every testable claim with source quote
     - `requirements.txt` — Python dependencies needed
     - `setup.md` — environment setup instructions (hardware, OS, accounts)
     - `skeleton/main.py` — minimal Python skeleton with the right imports
       and function signatures, with TODO markers for actual implementation

7. **Verify** — list_files at the end to confirm everything was written.
8. **Final answer** — summarize: paper title, top-3 claims to reproduce, estimated
   effort (hours/days/weeks), main risks, and which files you wrote.

Style:
- Be honest about what's hard. Some papers are nearly impossible to reproduce
  (proprietary data, missing code). Say so explicitly if true.
- Don't pad. A 200-word plan that's correct beats a 2000-word plan that's vague.
- The skeleton code should compile (syntactically valid Python), even if it doesn't
  actually run end-to-end. TODO markers belong inside function bodies, not as
  half-finished function signatures."""


class ReproAgent:
    """Reproduces (plans + skeletons) a research paper into a workspace directory."""

    def __init__(
        self,
        workspace_path: str | Path = "./repro_workspace",
        llm: LLMProvider | None = None,
        max_iterations: int = 40,
        on_step: callable = None,
    ):
        self.workspace_path = Path(workspace_path)
        tools, self.workspace = build_tools(self.workspace_path)
        system_prompt = build_system_prompt(tools.names(), task_context=SYSTEM_CONTEXT)
        self.agent = Agent(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            on_step=on_step,
        )

    async def reproduce(self, request: str) -> AgentResult:
        """Reproduce a paper. Request can be a paper id ('attention_is_all_you_need')
        or a free-form ask ('Reproduce the docaware paper')."""
        return await self.agent.run(request)

    @property
    def tracer(self):
        return self.agent.tracer

    def list_outputs(self) -> list[str]:
        """List files written to the workspace."""
        return self.workspace.list_files()
