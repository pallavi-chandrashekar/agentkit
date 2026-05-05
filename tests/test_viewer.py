"""Tests for the HTML trace viewer."""
from pathlib import Path

import pytest

from agentkit.observability.tracer import Tracer
from agentkit.observability.viewer import render_trace_html, render_tracer_html


@pytest.fixture
def populated_tracer() -> Tracer:
    t = Tracer(run_id="test_run_001")
    t.record("task_start", {"task": "Find me a number"})
    t.record("plan", {"text": "I will count to ten"})
    t.record("action", {"tool": "count", "arguments": {"n": 10}, "id": "c1"})
    t.record("llm_call", {
        "model": "claude-sonnet-4-5-20250929",
        "input_tokens": 100,
        "output_tokens": 50,
        "stop_reason": "tool_use",
    }, duration_ms=850.5)
    t.record("observation", {"tool_call_id": "c1", "output": "10"})
    t.record("answer", {"text": "The answer is 10"})
    t.record("task_end", {"success": True, "duration_seconds": 1.2})
    return t


class TestRenderTracerHtml:
    def test_writes_html_file(self, populated_tracer, tmp_path):
        out = tmp_path / "trace.html"
        result = render_tracer_html(populated_tracer, out)
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "<!DOCTYPE html>" in content
        assert "test_run_001" in content

    def test_html_contains_all_steps(self, populated_tracer, tmp_path):
        out = tmp_path / "trace.html"
        render_tracer_html(populated_tracer, out)
        content = out.read_text()
        # Each step type should appear
        for event_type in ["plan", "action", "observation", "answer", "llm_call"]:
            assert f"step-{event_type}" in content, f"Missing step type: {event_type}"

    def test_html_renders_token_summary(self, populated_tracer, tmp_path):
        out = tmp_path / "trace.html"
        render_tracer_html(populated_tracer, out)
        content = out.read_text()
        # Summary should reflect 100 input + 50 output tokens
        assert "100" in content
        assert "50" in content

    def test_html_escapes_user_content(self, tmp_path):
        t = Tracer(run_id="xss_test")
        t.record("task_start", {"task": "<script>alert('xss')</script>"})
        out = tmp_path / "trace.html"
        render_tracer_html(t, out)
        content = out.read_text()
        # Raw script tag should NOT appear; escaped version should
        assert "<script>alert('xss')</script>" not in content
        assert "&lt;script&gt;" in content

    def test_empty_tracer_raises(self, tmp_path):
        t = Tracer()
        with pytest.raises(ValueError, match="no events"):
            render_tracer_html(t, tmp_path / "empty.html")


class TestRenderTraceHtml:
    def test_renders_from_jsonl(self, populated_tracer, tmp_path):
        # Use the run_id as filename so it survives the round trip (JSONL holds events only)
        jsonl_path = tmp_path / f"{populated_tracer.run_id}.jsonl"
        populated_tracer.write_jsonl(jsonl_path)
        html_path = render_trace_html(jsonl_path)
        assert html_path.exists()
        assert html_path.suffix == ".html"
        # run_id is derived from the filename stem
        content = html_path.read_text()
        assert populated_tracer.run_id in content
        # All step types should be rendered
        for event_type in ["plan", "action", "observation", "answer"]:
            assert f"step-{event_type}" in content

    def test_custom_output_path(self, populated_tracer, tmp_path):
        jsonl_path = tmp_path / "trace.jsonl"
        populated_tracer.write_jsonl(jsonl_path)
        custom_out = tmp_path / "custom.html"
        result = render_trace_html(jsonl_path, output_path=custom_out)
        assert result == custom_out
        assert custom_out.exists()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            render_trace_html(tmp_path / "missing.jsonl")

    def test_empty_file_raises(self, tmp_path):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("")
        with pytest.raises(ValueError, match="empty"):
            render_trace_html(empty)
