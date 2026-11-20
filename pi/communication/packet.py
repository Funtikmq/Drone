"""Network packet format. Must match desktop/receiver.py.

header: seq (uint32), timestamp (float64), sample_rate (uint32),
        channels (uint8), raw_level_db (float32), noise_level_db (float32)
payload: samples as float32, little-endian
"""
from __future__ import annotations

import struct

from interfaces import FilteredFrame

HEADER = struct.Struct("<IdIBff")


def encode(result: FilteredFrame) -> bytes:
    f = result.frame
    channels = 1 if f.samples.ndim == 1 else f.samples.shape[1]
    header = HEADER.pack(f.seq, f.timestamp, f.sample_rate, channels,
                         result.raw_level_db, result.noise_level_db)
    return header + f.samples.astype("<f4").tobytes()
