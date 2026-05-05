"""WorkingMemory — scratchpad for the current task.

Stores intermediate observations, partial plans, and notes the agent
accumulates during task execution. Cleared between top-level user queries.
"""
from typing import Any


class WorkingMemory:
    """Key-value scratchpad for a single task execution."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._store

    def all(self) -> dict[str, Any]:
        return dict(self._store)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store
