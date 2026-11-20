"""Signal level helpers."""
from __future__ import annotations

import numpy as np


def rms_dbfs(samples: np.ndarray) -> float:
    """RMS level in dBFS (0 dBFS = full scale)."""
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return 20.0 * np.log10(rms) if rms > 0 else -120.0
