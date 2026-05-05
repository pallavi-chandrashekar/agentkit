"""Tests for observability: tracer, cost tracker."""
import json
from pathlib import Path

from agentkit.observability.cost import CostTracker, MODEL_PRICING
from agentkit.observability.tracer import Tracer


class TestCostTracker:
    def test_record_known_model(self):
        ct = CostTracker()
        entry = ct.record("claude-sonnet-4-5-20250929", 1000, 500)
        # 1000 * 3.00/1M + 500 * 15.00/1M = 0.003 + 0.0075 = 0.0105
        assert entry.cost_usd == 0.0105

    def test_unknown_model_zero_cost(self):
        ct = CostTracker()
        entry = ct.record("future-model-9000", 1000, 500)
        assert entry.cost_usd == 0.0

    def test_summary(self):
        ct = CostTracker()
        ct.record("gpt-4o-mini", 100, 200)
        ct.record("gpt-4o-mini", 150, 100)
        s = ct.summary()
        assert s["calls"] == 2
        assert s["input_tokens"] == 250
        assert s["output_tokens"] == 300

    def test_pricing_table_has_known_models(self):
        # Sanity check that the pricing dict isn't empty
        assert "claude-sonnet-4-5-20250929" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING


class TestTracer:
    def test_record_event(self):
        t = Tracer()
        t.record("plan", {"text": "do the thing"})
        assert len(t.events) == 1
        assert t.events[0].type == "plan"

    def test_event_counts(self):
        t = Tracer()
        t.record("action", {})
        t.record("action", {})
        t.record("observation", {})
        counts = t.event_counts()
        assert counts == {"action": 2, "observation": 1}

    def test_write_jsonl(self, tmp_path: Path):
        t = Tracer()
        t.record("plan", {"text": "x"})
        t.record("answer", {"text": "y"})
        out = tmp_path / "trace.jsonl"
        t.write_jsonl(out)
        assert out.exists()
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["type"] == "plan"

    def test_timer(self):
        import time
        t = Tracer()
        t.start_timer("op")
        time.sleep(0.01)
        elapsed = t.stop_timer("op")
        assert elapsed > 0
