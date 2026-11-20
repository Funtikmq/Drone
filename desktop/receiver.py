#!/usr/bin/env python3
"""Receives audio frames from the Pi, prints levels and optionally saves a WAV.

Packet format must match pi/communication.py.
"""
from __future__ import annotations

import argparse
import socket
import struct
import wave

import numpy as np

HEADER = struct.Struct("<IdIBff")


def decode(packet: bytes):
    seq, ts, sample_rate, channels, raw_db, noise_db = HEADER.unpack_from(packet)
    samples = np.frombuffer(packet[HEADER.size:], dtype="<f4").reshape(-1, channels)
    return seq, ts, sample_rate, channels, raw_db, noise_db, samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--save", help="save received audio to this WAV file")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    print(f"Listening on UDP port {args.port} (Ctrl+C to stop)")

    wav = None
    last_seq = None
    try:
        while True:
            packet, _ = sock.recvfrom(65535)
            seq, ts, sr, ch, raw_db, noise_db, samples = decode(packet)

            if last_seq is not None and seq != last_seq + 1:
                print(f"lost {seq - last_seq - 1} frame(s)")
            last_seq = seq

            if args.save and wav is None:
                wav = wave.open(args.save, "wb")
                wav.setnchannels(ch)
                wav.setsampwidth(2)
                wav.setframerate(sr)
            if wav is not None:
                wav.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())

            if seq % 50 == 0:
                print(f"#{seq} raw {raw_db:6.1f} dBFS | ambient {noise_db:6.1f} dBFS")
    except KeyboardInterrupt:
        pass
    finally:
        if wav is not None:
            wav.close()
            print(f"Saved {args.save}")
        sock.close()


if __name__ == "__main__":
    main()
