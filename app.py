#!/usr/bin/env python3
import select
import sys
import time

import collections
import collections.abc

collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect
from pymavlink import mavutil


CONNECTION_STRING = "/dev/ttyACM0"  # Example: "udp:127.0.0.1:14550"
BAUD_RATE = 57600                  # Used for serial connections
FIRST_MOTOR = 1                    # MAVLink motor numbering starts at 1
MOTOR_COUNT = 4                    # Test motors 1, 2, 3, 4 in sequence
DISARM_TIMEOUT_SEC = 10


def send_motor_test(vehicle, throttle_percent, duration_sec,
                    motor_instance, motor_count=1):
    """Send MAV_CMD_DO_MOTOR_TEST.

    With motor_count > 1 the autopilot tests motor_instance,
    motor_instance+1, ... one after another, each for duration_sec.
    """
    msg = vehicle.message_factory.command_long_encode(
        0, 0,  # Target system/component; DroneKit sets these when sending
        mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST,
        0,  # Confirmation
        motor_instance,                                # Param1: first motor
        mavutil.mavlink.MOTOR_TEST_THROTTLE_PERCENT,  # Param2: throttle type
        throttle_percent,                              # Param3: throttle
        duration_sec,                                  # Param4: time per motor
        motor_count,                                   # Param5: motor count
        0,  # Param6: test order (0 = default/sequence)
        0,  # Param7, reserved
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()


def stop_motors(vehicle):
    """Send an explicit zero-throttle motor-test command."""
    send_motor_test(vehicle, 0, 1, FIRST_MOTOR, 1)


def wait_for_test_or_stop(vehicle, duration_sec, motor_count):
    """Wait for the whole sequence; accept q or d plus Enter to stop early."""
    total_sec = duration_sec * motor_count
    deadline = time.monotonic() + total_sec
    print(f"Total test time: about {total_sec:g} seconds.")
    print("During the test, type q or d and press Enter to stop.")

    while time.monotonic() < deadline:
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            command = sys.stdin.readline().strip().lower()
            if command in {"q", "d"}:
                break
            if command:
                print("Type q or d to stop the test.")

    stop_motors(vehicle)
    print("Stop command sent.")


def request_disarm(vehicle):
    """Request disarming and wait for vehicle.armed to become False."""
    try:
        vehicle.armed = False
        deadline = time.monotonic() + DISARM_TIMEOUT_SEC

        while vehicle.armed and time.monotonic() < deadline:
            print("Waiting for disarm confirmation...")
            time.sleep(0.5)

        if vehicle.armed:
            print("WARNING: The vehicle still reports as armed.")
        else:
            print("Disarm confirmed.")
    except Exception as exc:
        print(f"Could not confirm disarming: {exc}")


def main():
    vehicle = None

    try:
        print(f"Connecting to {CONNECTION_STRING} ...")
        vehicle = connect(
            CONNECTION_STRING,
            baud=BAUD_RATE,
            wait_ready=True,
            heartbeat_timeout=30,
        )
        print(f"Connected. Armed state: {vehicle.armed}")

        while True:
            try:
                throttle = float(input("Motor throttle, 0–100% (Enter to quit): "))
            except ValueError:
                print("Enter a number from 0 to 100.")
                continue
            except EOFError:
                break

            if not 0 <= throttle <= 100:
                print("Throttle must be between 0 and 100.")
                continue
            if throttle == 0:
                print("Throttle is 0%; no test started.")
                continue

            try:
                duration = float(input("Duration per motor in seconds (0.1–30): "))
            except (ValueError, EOFError):
                print("Invalid duration.")
                continue

            if not 0.1 <= duration <= 30:
                print("Duration must be between 0.1 and 30 seconds.")
                continue

            if vehicle.armed:
                print("The vehicle is armed; the test will not be started.")
                continue

            last_motor = FIRST_MOTOR + MOTOR_COUNT - 1
            print(
                f"Testing motors {FIRST_MOTOR}–{last_motor} at {throttle:g}%, "
                f"{duration:g} seconds each."
            )
            send_motor_test(vehicle, throttle, duration, FIRST_MOTOR, MOTOR_COUNT)
            wait_for_test_or_stop(vehicle, duration, MOTOR_COUNT)

    except KeyboardInterrupt:
        print("\nCtrl+C: stop requested.")
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        if vehicle is not None:
            try:
                # Safety stop before requesting disarm.
                stop_motors(vehicle)
            except Exception as exc:
                print(f"Could not send the stop command: {exc}")

            request_disarm(vehicle)
            vehicle.close()
            print("Connection closed.")


if __name__ == "__main__":
    main()