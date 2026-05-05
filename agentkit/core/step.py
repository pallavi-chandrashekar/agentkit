"""Step types for the agent execution trace."""
from dataclasses import dataclass
from typing import Any


@dataclass
class Step:
    """A single step in the agent loop.

    type: 'plan' | 'action' | 'observation' | 'reflection' | 'answer'
    """
    type: str
    content: str | None = None
    data: dict[str, Any] | None = None
