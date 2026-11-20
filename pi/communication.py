"""Sends filtered frames to the PC over UDP.

Packet format (must match desktop/receiver.py):
    header: seq (uint32), timestamp (float64), sample_rate (uint32),
            channels (uint8), raw_level_db (float32), noise_level_db (float32)
    payload: samples as float32, little-endian
"""
from __future__ import annotations

import socket
import struct

import numpy as np

import config
from interfaces import Communication, FilteredFrame

HEADER = struct.Struct("<IdIBff")


def encode(result: FilteredFrame) -> bytes:
    f = result.frame
    channels = 1 if f.samples.ndim == 1 else f.samples.shape[1]
    header = HEADER.pack(f.seq, f.timestamp, f.sample_rate, channels,
                         result.raw_level_db, result.noise_level_db)
    return header + f.samples.astype("<f4").tobytes()


class UdpCommunication(Communication):
    def __init__(self, host: str = config.DESKTOP_HOST, port: int = config.DESKTOP_PORT) -> None:
        self._addr = (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, result: FilteredFrame) -> None:
        try:
            self._sock.sendto(encode(result), self._addr)
        except OSError as exc:
            print(f"[comm] send failed: {exc}")

    def close(self) -> None:
        self._sock.close()
