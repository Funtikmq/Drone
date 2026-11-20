"""Microphone capture (I2S/USB mic HAT via ALSA)."""
from __future__ import annotations

import queue
import time

import numpy as np
import sounddevice as sd

import config
from interfaces import AudioCapture, AudioFrame


class MicCapture(AudioCapture):
    def __init__(self) -> None:
        self._queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=100)
        self._stream: sd.InputStream | None = None
        self._seq = 0

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            print(f"[capture] {status}")
        frame = AudioFrame(
            samples=indata.copy().astype(np.float32),
            sample_rate=config.SAMPLE_RATE,
            timestamp=time.time(),
            seq=self._seq,
        )
        self._seq += 1
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            print("[capture] queue full, dropping frame")

    def start(self) -> None:
        self._stream = sd.InputStream(
            device=config.AUDIO_DEVICE,
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            blocksize=config.BLOCK_SIZE,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def read(self, timeout: float = 1.0) -> AudioFrame | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
