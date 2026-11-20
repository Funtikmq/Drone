#!/usr/bin/env python3
"""Entry point on the Pi. Starts the modules from a simple menu."""
from __future__ import annotations

import threading

from audio_capture import MicCapture
from interfaces import Communication
from noise_filter import PassThroughFilter


def audio_pipeline(stop_event: threading.Event,
                   comm: Communication | None = None,
                   verbose: bool = True) -> None:
    """capture -> filter (-> communication if given), until stop_event is set."""
    capture = MicCapture()
    noise_filter = PassThroughFilter()

    capture.start()
    print("[audio] pipeline running" + (" (sending to PC)" if comm else " (local only)"))
    try:
        while not stop_event.is_set():
            frame = capture.read(timeout=0.5)
            if frame is None:
                continue
            result = noise_filter.process(frame)
            if comm is not None:
                comm.send(result)
            if verbose and frame.seq % 50 == 0:   # ~1 line per second
                print(f"[audio] #{frame.seq} raw {result.raw_level_db:6.1f} dBFS"
                      f" | ambient {result.noise_level_db:6.1f} dBFS")
    finally:
        capture.stop()
        if comm is not None:
            comm.close()
        print("[audio] pipeline stopped")


def run_until_ctrl_c(comm: Communication | None = None) -> None:
    stop = threading.Event()
    try:
        audio_pipeline(stop, comm)
    except KeyboardInterrupt:
        stop.set()


def main() -> None:
    print("1) Motor test only")
    print("2) Audio capture + filter (local, prints levels)")
    print("3) Audio capture + filter + motor test")
    print("4) Audio capture + filter + send to PC")
    choice = input("Select: ").strip()

    if choice == "1":
        from motors import run_motor_test
        run_motor_test()

    elif choice == "2":
        print("Press Ctrl+C to stop.")
        run_until_ctrl_c()

    elif choice == "3":
        from motors import run_motor_test
        stop = threading.Event()
        audio = threading.Thread(target=audio_pipeline, args=(stop,), daemon=True)
        audio.start()
        try:
            run_motor_test()
        finally:
            stop.set()
            audio.join(timeout=3)

    elif choice == "4":
        from communication import UdpCommunication
        print("Press Ctrl+C to stop.")
        run_until_ctrl_c(UdpCommunication())

    else:
        print("Unknown option.")


if __name__ == "__main__":
    main()
