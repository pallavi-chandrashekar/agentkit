"""PipelineDoctor tools — wrap a PipelineBackend with agent-friendly tools."""
from dataclasses import asdict

from agentkit.tools.base import Tool, ToolResult
from agentkit.tools.registry import ToolRegistry

from examples.pipeline_doctor.backend import PipelineBackend


class _ListDagsTool(Tool):
    name = "list_dags"
    description = "List all pipelines (DAGs) in the system. Use this first to know what's available."
    input_schema = {"type": "object", "properties": {}, "required": []}

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self) -> ToolResult:
        dags = self.backend.list_dags()
        return ToolResult(output=dags, display=f"DAGs: {dags}")


class _GetDagStatusTool(Tool):
    name = "get_dag_status"
    description = "Get the current status of a DAG (latest run state and ID)."
    input_schema = {
        "type": "object",
        "properties": {"dag_id": {"type": "string"}},
        "required": ["dag_id"],
    }

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self, dag_id: str) -> ToolResult:
        status = self.backend.get_dag_status(dag_id)
        return ToolResult(output=status, display=f"{dag_id}: {status['latest_state']} (run {status['latest_run_id']})")


class _GetRecentRunsTool(Tool):
    name = "get_recent_runs"
    description = "Get the most recent runs of a DAG. Use to compare failed runs against successful ones to spot what changed."
    input_schema = {
        "type": "object",
        "properties": {
            "dag_id": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["dag_id"],
    }

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self, dag_id: str, limit: int = 5) -> ToolResult:
        runs = self.backend.get_recent_runs(dag_id, limit=limit)
        out = [
            {
                "run_id": r.run_id,
                "state": r.state,
                "started_at": r.started_at,
                "duration_seconds": r.duration_seconds,
                "task_states": {t.task_id: t.state for t in r.tasks},
            }
            for r in runs
        ]
        states = ", ".join(f"{r.started_at[:10]}={r.state}" for r in runs)
        return ToolResult(output=out, display=f"{len(runs)} runs: {states}")


class _GetFailedTasksTool(Tool):
    name = "get_failed_tasks"
    description = "Get the tasks that failed in a specific run. Returns task IDs and brief log excerpts."
    input_schema = {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    }

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self, run_id: str) -> ToolResult:
        tasks = self.backend.get_failed_tasks(run_id)
        out = [{"task_id": t.task_id, "log_excerpt": t.log_excerpt[:300]} for t in tasks]
        return ToolResult(
            output=out,
            display=f"{len(tasks)} failed: {[t.task_id for t in tasks]}",
        )


class _GetTaskLogsTool(Tool):
    name = "get_task_logs"
    description = "Retrieve full log output for a specific failed task. Use after get_failed_tasks to dig into the actual error."
    input_schema = {
        "type": "object",
        "properties": {
            "run_id": {"type": "string"},
            "task_id": {"type": "string"},
            "tail_lines": {"type": "integer", "default": 100},
        },
        "required": ["run_id", "task_id"],
    }

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self, run_id: str, task_id: str, tail_lines: int = 100) -> ToolResult:
        logs = self.backend.get_task_logs(run_id, task_id, tail_lines=tail_lines)
        first_line = logs.split("\n")[0] if logs else "(empty)"
        return ToolResult(output=logs, display=f"{len(logs)} chars · first line: {first_line[:80]}")


class _GetTaskCodeTool(Tool):
    name = "get_task_code"
    description = "Read the source code for a task in a DAG. Use this to identify what the failing code does and propose a fix."
    input_schema = {
        "type": "object",
        "properties": {
            "dag_id": {"type": "string"},
            "task_id": {"type": "string"},
        },
        "required": ["dag_id", "task_id"],
    }

    def __init__(self, backend: PipelineBackend):
        self.backend = backend

    async def execute(self, dag_id: str, task_id: str) -> ToolResult:
        code = self.backend.get_task_code(dag_id, task_id)
        return ToolResult(output=code, display=f"{len(code.splitlines())} lines of code for {dag_id}.{task_id}")


def build_tools(backend: PipelineBackend) -> ToolRegistry:
    return ToolRegistry([
        _ListDagsTool(backend),
        _GetDagStatusTool(backend),
        _GetRecentRunsTool(backend),
        _GetFailedTasksTool(backend),
        _GetTaskLogsTool(backend),
        _GetTaskCodeTool(backend),
    ])
