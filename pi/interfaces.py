"""Contract between the modules.

Every module implements one of the classes below. run.py only uses these
methods, so a module can be rewritten freely as long as it keeps them.
Change this file only by agreement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


# ---------- data passed between modules ----------

@dataclass
class AudioFrame:
    """A block of captured audio."""
    samples: np.ndarray    # shape (n_samples, n_channels), float32 in [-1, 1]
    sample_rate: int
    timestamp: float       # time.time() when captured
    seq: int               # frame counter, used to detect lost frames


@dataclass
class FilteredFrame:
    """Output of the noise filter."""
    frame: AudioFrame      # cleaned audio
    raw_level_db: float    # level before filtering (dBFS)
    noise_level_db: float  # estimated ambient noise level (dBFS)


# ---------- module interfaces ----------

class AudioCapture(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def read(self, timeout: float = 1.0) -> AudioFrame | None:
        """Return the next frame, or None if nothing arrived within timeout."""

    @abstractmethod
    def stop(self) -> None: ...


class NoiseFilter(ABC):
    @abstractmethod
    def process(self, frame: AudioFrame) -> FilteredFrame: ...


class Communication(ABC):
    @abstractmethod
    def send(self, result: FilteredFrame) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
