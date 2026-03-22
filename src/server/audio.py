"""
Audio buffer management for voice recording.

Collects audio chunks during LISTENING state and provides
concatenation for STT processing.
"""

from typing import Optional

import numpy as np


class AudioBuffer:
    """Collects and manages audio chunks during recording."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []

    def append(self, chunk: np.ndarray) -> None:
        """Append an audio chunk to the buffer."""
        self._chunks.append(chunk)

    def concatenate(self) -> np.ndarray:
        """Concatenate all chunks into a single audio array."""
        if not self._chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._chunks)

    def clear(self) -> None:
        """Clear all chunks from the buffer."""
        self._chunks.clear()

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._chunks) == 0

    def __len__(self) -> int:
        """Return number of chunks in buffer."""
        return len(self._chunks)
