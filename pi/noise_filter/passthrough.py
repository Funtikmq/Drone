"""Pass-through filter: audio is not changed, both levels are the raw level.

Lets the whole pipeline run end to end before the real filter is ready.
"""
from __future__ import annotations

from interfaces import AudioFrame, FilteredFrame, NoiseFilter

from .levels import rms_dbfs


class PassThroughFilter(NoiseFilter):
    def process(self, frame: AudioFrame) -> FilteredFrame:
        # TODO: replace with a real filter (e.g. notch filters on motor
        # frequencies and harmonics, spectral subtraction).
        level = rms_dbfs(frame.samples)
        return FilteredFrame(frame=frame, raw_level_db=level, noise_level_db=level)
