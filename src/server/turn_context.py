"""
TurnContext - Per-turn context for managing conversation state and cancellation.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional
import asyncio


@dataclass
class TurnContext:
    """Per-turn context shared between VoiceTurn and StreamingSynthesis."""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)
    audio_data: Optional["np.ndarray"] = None  # type: ignore[name-defined]
    transcript: str = ""
    full_response: str = ""
    perf_data: dict = field(default_factory=dict)

    def cancel(self):
        """Signal cancellation."""
        self.cancelled.set()

    def is_cancelled(self) -> bool:
        """Check if cancelled."""
        return self.cancelled.is_set()

    def reset(self):
        """Reset for next turn."""
        self.cancelled.clear()
        self.audio_data = None
        self.transcript = ""
        self.full_response = ""
        self.perf_data = {}
