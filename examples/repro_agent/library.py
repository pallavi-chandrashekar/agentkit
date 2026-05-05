"""Paper library — built-in papers shipped with the demo, plus arbitrary file/URL loading."""
import re
import urllib.request
from pathlib import Path

from agentkit.tools.base import ToolError

_PAPERS_DIR = Path(__file__).parent / "papers"


def _load_builtins() -> dict[str, dict]:
    """Discover and parse built-in papers."""
    papers = {}
    for path in sorted(_PAPERS_DIR.glob("*.md")):
        paper_id = path.stem
        text = path.read_text()
        title = _extract_title(text)
        papers[paper_id] = {
            "id": paper_id,
            "title": title,
            "source": "builtin",
            "path": str(path),
            "text": text,
        }
    return papers


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


_BUILTIN = _load_builtins()


def list_papers() -> list[dict]:
    """List all available papers (id + title only — keep responses small)."""
    return [{"id": p["id"], "title": p["title"]} for p in _BUILTIN.values()]


def get_paper(paper_id: str) -> dict:
    """Fetch a paper's full text. Built-in IDs OR URL/path to a markdown file."""
    if paper_id in _BUILTIN:
        return _BUILTIN[paper_id]

    # Allow loading from URL or local path for advanced use
    if paper_id.startswith("http://") or paper_id.startswith("https://"):
        try:
            with urllib.request.urlopen(paper_id, timeout=10) as resp:
                text = resp.read().decode("utf-8")
            return {"id": paper_id, "title": _extract_title(text), "source": "url", "text": text}
        except Exception as e:
            raise ToolError(f"Could not fetch URL {paper_id}: {e}", recoverable=True)

    if Path(paper_id).is_file():
        text = Path(paper_id).read_text()
        return {"id": paper_id, "title": _extract_title(text), "source": "file", "text": text}

    available = ", ".join(_BUILTIN.keys())
    raise ToolError(
        f"Unknown paper '{paper_id}'. Built-in: {available}. Or pass a URL or file path.",
        recoverable=True,
    )


def get_section(paper_id: str, section_name: str) -> str:
    """Extract a named section. Tries case-insensitive heading match."""
    paper = get_paper(paper_id)
    text = paper["text"]
    # Match `## Section Name` or `### Section Name` (case-insensitive)
    pattern = re.compile(
        rf"^#{{2,3}}\s+(?:\d+\.?\s*)?{re.escape(section_name)}\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        # Fallback: substring match in any heading
        for m in re.finditer(r"^#{2,3}\s+(.+)$", text, re.MULTILINE):
            if section_name.lower() in m.group(1).lower():
                match = m
                break
    if not match:
        # List available sections to help the agent
        headings = re.findall(r"^#{2,3}\s+(.+)$", text, re.MULTILINE)
        raise ToolError(
            f"Section '{section_name}' not found. Available: {headings}",
            recoverable=True,
        )
    # Determine the heading level (## = 2, ### = 3) to know where this section ends
    heading_line = text[match.start():match.end()]
    level = len(heading_line) - len(heading_line.lstrip("#"))
    start = match.end()
    # Stop at next heading of same or higher level (lower-numbered #'s)
    stop_pattern = rf"^#{{1,{level}}}\s+"
    next_heading = re.search(stop_pattern, text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def search_text(paper_id: str, query: str, context_chars: int = 200) -> list[dict]:
    """Find occurrences of query in the paper, return surrounding context."""
    paper = get_paper(paper_id)
    text = paper["text"]
    matches = []
    for m in re.finditer(re.escape(query), text, re.IGNORECASE):
        start = max(0, m.start() - context_chars)
        end = min(len(text), m.end() + context_chars)
        matches.append({
            "position": m.start(),
            "match": m.group(0),
            "context": text[start:end].strip(),
        })
    return matches
