"""Motor/propeller noise removal and ambient noise level estimation.

Owner: colleague. Currently a pass-through: the audio is not changed and
both levels are the raw RMS level, so the whole pipeline works end to end.
"""
from __future__ import annotations

import numpy as np

from interfaces import AudioFrame, FilteredFrame, NoiseFilter


def rms_dbfs(samples: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return 20.0 * np.log10(rms) if rms > 0 else -120.0


class PassThroughFilter(NoiseFilter):
    def process(self, frame: AudioFrame) -> FilteredFrame:
        # TODO: replace with real filtering (e.g. notch filters on motor
        # frequencies and harmonics, spectral subtraction).
        level = rms_dbfs(frame.samples)
        return FilteredFrame(frame=frame, raw_level_db=level, noise_level_db=level)
