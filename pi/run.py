#!/usr/bin/env python3
"""Entry point on the Pi. Starts the modules from a simple menu."""
from __future__ import annotations

import threading

from audio_capture import MicCapture
from communication import UdpCommunication
from noise_filter import PassThroughFilter


def audio_pipeline(stop_event: threading.Event, verbose: bool = True) -> None:
    """capture -> filter -> communication, until stop_event is set."""
    capture = MicCapture()
    noise_filter = PassThroughFilter()
    comm = UdpCommunication()

    capture.start()
    print("[audio] pipeline running")
    try:
        while not stop_event.is_set():
            frame = capture.read(timeout=0.5)
            if frame is None:
                continue
            result = noise_filter.process(frame)
            comm.send(result)
            if verbose and frame.seq % 50 == 0:   # ~1 line per second
                print(f"[audio] #{frame.seq} raw {result.raw_level_db:6.1f} dBFS"
                      f" | ambient {result.noise_level_db:6.1f} dBFS")
    finally:
        capture.stop()
        comm.close()
        print("[audio] pipeline stopped")


def main() -> None:
    print("1) Motor test only")
    print("2) Audio pipeline only (capture -> filter -> send to PC)")
    print("3) Audio pipeline + motor test")
    choice = input("Select: ").strip()

    if choice == "1":
        from motors import run_motor_test
        run_motor_test()

    elif choice == "2":
        stop = threading.Event()
        try:
            audio_pipeline(stop)
        except KeyboardInterrupt:
            stop.set()

    elif choice == "3":
        from motors import run_motor_test
        stop = threading.Event()
        # quieter output so it does not interfere with the motor test prompts
        audio = threading.Thread(target=audio_pipeline, args=(stop, False), daemon=True)
        audio.start()
        try:
            run_motor_test()
        finally:
            stop.set()
            audio.join(timeout=3)

    else:
        print("Unknown option.")


if __name__ == "__main__":
    main()
