"""Tracer — records every step the agent takes.

Each step is a TraceEvent with timestamp, type, and payload. Traces can be
written to JSONL files and rendered as HTML for inspection.
"""
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    """A single event in the agent's execution trace."""
    type: str  # 'plan' | 'action' | 'observation' | 'reflection' | 'answer' | 'llm_call' | 'error'
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """Records and exports execution traces."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or f"run_{int(time.time() * 1000)}"
        self.events: list[TraceEvent] = []
        self._start_times: dict[str, float] = {}

    def record(self, event_type: str, data: dict | None = None, duration_ms: float = 0.0) -> TraceEvent:
        event = TraceEvent(
            type=event_type,
            duration_ms=duration_ms,
            data=data or {},
        )
        self.events.append(event)
        return event

    def start_timer(self, key: str) -> None:
        self._start_times[key] = time.time()

    def stop_timer(self, key: str) -> float:
        if key not in self._start_times:
            return 0.0
        elapsed = (time.time() - self._start_times.pop(key)) * 1000
        return elapsed

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.events[0].timestamp if self.events else None,
            "events": [asdict(e) for e in self.events],
        }

    def write_jsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for event in self.events:
                f.write(json.dumps(asdict(event)) + "\n")
        return path

    def event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.events:
            counts[e.type] = counts.get(e.type, 0) + 1
        return counts
