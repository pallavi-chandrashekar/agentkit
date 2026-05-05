"""ReproAgent tools — paper reading + file system workspace."""
import json
from pathlib import Path

from agentkit.tools.base import Tool, ToolError, ToolResult
from agentkit.tools.registry import ToolRegistry

from examples.repro_agent.library import (
    list_papers as lib_list_papers,
    get_paper as lib_get_paper,
    get_section as lib_get_section,
    search_text as lib_search_text,
)


# ---- Paper reading tools ----

class _ListPapersTool(Tool):
    name = "list_papers"
    description = "List built-in papers available for reproduction. Returns paper IDs and titles."
    input_schema = {"type": "object", "properties": {}, "required": []}

    async def execute(self) -> ToolResult:
        papers = lib_list_papers()
        return ToolResult(output=papers, display=f"{len(papers)} papers: {[p['id'] for p in papers]}")


class _ReadPaperTool(Tool):
    name = "read_paper"
    description = (
        "Get the full text of a paper. Use this for short papers or when you need the entire context. "
        "For long papers, prefer get_section to avoid filling context with irrelevant material."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string", "description": "Built-in paper id, or URL/path to a markdown file"},
        },
        "required": ["paper_id"],
    }

    async def execute(self, paper_id: str) -> ToolResult:
        paper = lib_get_paper(paper_id)
        return ToolResult(
            output={"id": paper["id"], "title": paper["title"], "text": paper["text"]},
            display=f'Paper "{paper["title"]}" ({len(paper["text"])} chars)',
        )


class _GetSectionTool(Tool):
    name = "get_section"
    description = (
        "Get a specific section from a paper. Common section names: abstract, introduction, "
        "method, methodology, model architecture, training, results, evaluation, conclusion, etc."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string"},
            "section_name": {"type": "string"},
        },
        "required": ["paper_id", "section_name"],
    }

    async def execute(self, paper_id: str, section_name: str) -> ToolResult:
        text = lib_get_section(paper_id, section_name)
        return ToolResult(
            output=text,
            display=f"Section '{section_name}' ({len(text)} chars)",
        )


class _SearchPaperTool(Tool):
    name = "search_paper"
    description = (
        "Search for occurrences of a phrase in a paper, returning surrounding context. "
        "Use to find specific numbers, dataset names, code references, hyperparameters."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string"},
            "query": {"type": "string", "description": "Substring to find (case-insensitive)"},
        },
        "required": ["paper_id", "query"],
    }

    async def execute(self, paper_id: str, query: str) -> ToolResult:
        matches = lib_search_text(paper_id, query)
        return ToolResult(
            output=matches,
            display=f"{len(matches)} matches for '{query}'",
        )


# ---- Workspace (file system) tools ----

class _Workspace:
    """Bounded file system workspace for the agent's reproduction artifacts."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        # Prevent escaping the workspace
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise ToolError(f"Path '{path}' escapes the workspace", recoverable=False)
        return candidate

    def write_file(self, path: str, content: str) -> str:
        full_path = self._resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return str(full_path.relative_to(self.root))

    def read_file(self, path: str) -> str:
        full_path = self._resolve(path)
        if not full_path.is_file():
            raise ToolError(f"File '{path}' does not exist in workspace", recoverable=True)
        return full_path.read_text()

    def list_files(self) -> list[str]:
        files = []
        for p in self.root.rglob("*"):
            if p.is_file():
                files.append(str(p.relative_to(self.root)))
        return sorted(files)


class _WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Write a file to the reproduction workspace. Overwrites if it exists. "
        "Use for plan.md, claims.md, requirements.txt, code skeleton files, etc."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within the workspace"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, workspace: _Workspace):
        self.workspace = workspace

    async def execute(self, path: str, content: str) -> ToolResult:
        rel = self.workspace.write_file(path, content)
        return ToolResult(
            output={"path": rel, "bytes": len(content)},
            display=f"Wrote {rel} ({len(content)} bytes)",
        )


class _ReadFileTool(Tool):
    name = "read_file"
    description = "Read a file you previously wrote in the workspace."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def __init__(self, workspace: _Workspace):
        self.workspace = workspace

    async def execute(self, path: str) -> ToolResult:
        content = self.workspace.read_file(path)
        return ToolResult(output=content, display=f"{path} ({len(content)} bytes)")


class _ListFilesTool(Tool):
    name = "list_files"
    description = "List files in the reproduction workspace."
    input_schema = {"type": "object", "properties": {}, "required": []}

    def __init__(self, workspace: _Workspace):
        self.workspace = workspace

    async def execute(self) -> ToolResult:
        files = self.workspace.list_files()
        return ToolResult(output=files, display=f"{len(files)} files: {files}")


def build_tools(workspace_path: str | Path) -> tuple[ToolRegistry, _Workspace]:
    """Build the ReproAgent tool registry. Returns (registry, workspace) so callers can inspect output."""
    workspace = _Workspace(Path(workspace_path))
    registry = ToolRegistry([
        _ListPapersTool(),
        _ReadPaperTool(),
        _GetSectionTool(),
        _SearchPaperTool(),
        _WriteFileTool(workspace),
        _ReadFileTool(workspace),
        _ListFilesTool(workspace),
    ])
    return registry, workspace
