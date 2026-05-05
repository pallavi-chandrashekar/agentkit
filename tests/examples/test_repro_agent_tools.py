"""Tests for ReproAgent library + tools (no LLM calls)."""
from pathlib import Path

import pytest

from agentkit.tools.base import ToolError
from examples.repro_agent.library import (
    list_papers, get_paper, get_section, search_text,
)
from examples.repro_agent.tools import build_tools


class TestPaperLibrary:
    def test_list_papers(self):
        papers = list_papers()
        ids = [p["id"] for p in papers]
        assert "attention_is_all_you_need" in ids
        assert "docaware" in ids
        assert "few_useful_things" in ids
        # All have titles
        assert all(p["title"] for p in papers)

    def test_get_builtin_paper(self):
        paper = get_paper("attention_is_all_you_need")
        assert paper["title"].startswith("Attention Is All You Need")
        assert "BLEU" in paper["text"]

    def test_get_unknown_paper_raises(self):
        with pytest.raises(ToolError, match="Unknown paper"):
            get_paper("nonexistent_paper")

    def test_get_section_exact(self):
        text = get_section("attention_is_all_you_need", "Abstract")
        assert "Transformer" in text
        assert "BLEU" in text

    def test_get_section_case_insensitive(self):
        text = get_section("attention_is_all_you_need", "abstract")
        assert "Transformer" in text

    def test_get_section_substring_match(self):
        # "Model Architecture" — substring of "## Model Architecture"
        text = get_section("attention_is_all_you_need", "Architecture")
        assert "encoder" in text.lower()

    def test_get_section_unknown_raises(self):
        with pytest.raises(ToolError, match="not found"):
            get_section("attention_is_all_you_need", "Conclusionary Remarks")

    def test_search_text(self):
        matches = search_text("attention_is_all_you_need", "BLEU")
        assert len(matches) > 0
        # Each match should have context
        for m in matches:
            assert "context" in m
            assert "BLEU" in m["context"] or "bleu" in m["context"].lower()

    def test_search_no_match(self):
        matches = search_text("attention_is_all_you_need", "phlogiston_xyz_doesnt_exist")
        assert matches == []


class TestWorkspaceTools:
    async def test_write_and_read(self, tmp_path):
        registry, ws = build_tools(tmp_path)
        write_result = await registry.execute("write_file", {"path": "plan.md", "content": "# Hello"})
        assert write_result.output["path"] == "plan.md"
        assert (tmp_path / "plan.md").exists()

        read_result = await registry.execute("read_file", {"path": "plan.md"})
        assert read_result.output == "# Hello"

    async def test_list_files(self, tmp_path):
        registry, ws = build_tools(tmp_path)
        await registry.execute("write_file", {"path": "a.md", "content": "a"})
        await registry.execute("write_file", {"path": "sub/b.md", "content": "b"})
        result = await registry.execute("list_files", {})
        files = result.output
        assert "a.md" in files
        assert "sub/b.md" in files

    async def test_path_traversal_blocked(self, tmp_path):
        registry, ws = build_tools(tmp_path)
        with pytest.raises(ToolError, match="escapes the workspace"):
            await registry.execute("write_file", {"path": "../escape.md", "content": "x"})

    async def test_read_missing_file(self, tmp_path):
        registry, ws = build_tools(tmp_path)
        with pytest.raises(ToolError, match="does not exist"):
            await registry.execute("read_file", {"path": "missing.md"})


class TestPaperTools:
    async def test_list_papers_via_registry(self, tmp_path):
        registry, _ = build_tools(tmp_path)
        result = await registry.execute("list_papers", {})
        ids = [p["id"] for p in result.output]
        assert "docaware" in ids

    async def test_read_paper_via_registry(self, tmp_path):
        registry, _ = build_tools(tmp_path)
        result = await registry.execute("read_paper", {"paper_id": "docaware"})
        assert "DocAware" in result.output["title"]
        assert "F1" in result.output["text"]

    async def test_get_section_via_registry(self, tmp_path):
        registry, _ = build_tools(tmp_path)
        result = await registry.execute("get_section", {
            "paper_id": "docaware",
            "section_name": "Results",
        })
        assert "F1" in result.output

    async def test_all_tools_registered(self, tmp_path):
        registry, _ = build_tools(tmp_path)
        expected = {"list_papers", "read_paper", "get_section", "search_paper",
                    "write_file", "read_file", "list_files"}
        assert set(registry.names()) == expected
