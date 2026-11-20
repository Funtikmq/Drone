"""Sends filtered frames to the PC over UDP."""
from __future__ import annotations

import socket

import config
from interfaces import Communication, FilteredFrame

from .packet import encode


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
