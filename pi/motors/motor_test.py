"""Motor test (run standalone with: python -m motors.motor_test): spin ALL motors at once (ArduCopter), on the bench, WITHOUT PROPELLERS.

How it works: set STABILIZE mode, arm, and send RC override on channel 3
(throttle). ArduPilot's MAVLink motor test cannot spin several motors at
the same time, so arming + throttle is used instead.

Note: in STABILIZE the attitude controller is active, so on the bench the
motors may spin at slightly different speeds (it tries to "correct"). This
is normal.
"""
import select
import sys
import time

import collections
import collections.abc

collections.MutableMapping = collections.abc.MutableMapping  # dronekit fix for Python 3.10+

from dronekit import connect, VehicleMode
from pymavlink import mavutil

import config

MAX_THROTTLE_PERCENT = 40     # safety limit; raise only if needed
MAX_DURATION_SEC = 30
RAMP_SEC = 1.0                # smooth throttle ramp-up
SEND_RATE_HZ = 10             # RC override must be resent often (RC_OVERRIDE_TIME)
FORCE_ARM = False             # True = skip pre-arm checks (bench only!)
ARM_TIMEOUT_SEC = 10
DISARM_TIMEOUT_SEC = 10
FORCE_MAGIC = 21196           # MAVLink value for forced arm/disarm


def get_param(vehicle, name, default):
    try:
        value = vehicle.parameters[name]
        return int(value) if value is not None else default
    except Exception:
        return default


def throttle_to_pwm(vehicle, percent):
    rc_min = get_param(vehicle, "RC3_MIN", 1000)
    rc_max = get_param(vehicle, "RC3_MAX", 2000)
    return int(rc_min + (rc_max - rc_min) * percent / 100.0)


def send_rc_override(vehicle, throttle_pwm):
    """Roll/pitch/yaw centered (1500), throttle on channel 3."""
    master = vehicle._master
    msg = vehicle.message_factory.rc_channels_override_encode(
        master.target_system,
        master.target_component,
        1500,          # ch1 roll
        1500,          # ch2 pitch
        throttle_pwm,  # ch3 throttle
        1500,          # ch4 yaw
        0, 0, 0, 0,    # ch5-ch8: released
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()


def release_rc_override(vehicle):
    master = vehicle._master
    msg = vehicle.message_factory.rc_channels_override_encode(
        master.target_system, master.target_component,
        0, 0, 0, 0, 0, 0, 0, 0,
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()


def send_arm_command(vehicle, arm, force):
    msg = vehicle.message_factory.command_long_encode(
        0, 0,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1 if arm else 0,
        FORCE_MAGIC if force else 0,
        0, 0, 0, 0, 0,
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()


def set_mode(vehicle, mode_name, timeout=5):
    vehicle.mode = VehicleMode(mode_name)
    deadline = time.monotonic() + timeout
    while vehicle.mode.name != mode_name and time.monotonic() < deadline:
        time.sleep(0.2)
    return vehicle.mode.name == mode_name


def arm(vehicle, min_pwm):
    """Throttle to minimum, then arm. Returns True if armed."""
    # Throttle low before arming (ArduCopter requirement)
    for _ in range(10):
        send_rc_override(vehicle, min_pwm)
        time.sleep(0.1)

    send_arm_command(vehicle, True, FORCE_ARM)
    deadline = time.monotonic() + ARM_TIMEOUT_SEC
    while not vehicle.armed and time.monotonic() < deadline:
        send_rc_override(vehicle, min_pwm)
        time.sleep(0.1)

    if not vehicle.armed:
        print("Arming failed. Check Mission Planner messages / pre-arm checks "
              "(or set FORCE_ARM = True, bench only).")
    return vehicle.armed


def disarm(vehicle, min_pwm):
    """Throttle to minimum, then forced disarm and release the override."""
    try:
        for _ in range(5):
            send_rc_override(vehicle, min_pwm)
            time.sleep(0.1)

        deadline = time.monotonic() + DISARM_TIMEOUT_SEC
        while vehicle.armed and time.monotonic() < deadline:
            send_arm_command(vehicle, False, True)
            send_rc_override(vehicle, min_pwm)
            time.sleep(0.5)

        if vehicle.armed:
            print("WARNING: the drone still reports being armed!")
        else:
            print("Disarm confirmed.")
    except Exception as exc:
        print(f"Could not confirm disarm: {exc}")
    finally:
        try:
            release_rc_override(vehicle)
        except Exception:
            pass


def stop_requested():
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        command = sys.stdin.readline().strip().lower()
        if command in {"q", "d"}:
            return True
        if command:
            print("Type q or d to stop.")
    return False


def run_all_motors(vehicle, throttle_percent, duration_sec):
    min_pwm = throttle_to_pwm(vehicle, 0)

    if not set_mode(vehicle, "STABILIZE"):
        print(f"Could not set STABILIZE (current mode: {vehicle.mode.name}).")
        return

    if not arm(vehicle, min_pwm):
        return

    print(f"All motors at {throttle_percent:g}% for {duration_sec:g} s.")
    print("Type q or d and press Enter to stop.")

    start = time.monotonic()
    period = 1.0 / SEND_RATE_HZ
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= duration_sec:
                break
            if not vehicle.armed:
                print("The drone disarmed itself; stopping.")
                break
            if stop_requested():
                break

            ramp = min(1.0, elapsed / RAMP_SEC) if RAMP_SEC > 0 else 1.0
            pwm = throttle_to_pwm(vehicle, throttle_percent * ramp)
            send_rc_override(vehicle, pwm)
            time.sleep(period)
    finally:
        disarm(vehicle, min_pwm)


def run_motor_test():
    """Interactive motor test (previously app.py main())."""
    vehicle = None
    try:
        print(f"Connecting to {config.CONNECTION_STRING} ...")
        vehicle = connect(
            config.CONNECTION_STRING,
            baud=config.BAUD_RATE,
            wait_ready=True,
            heartbeat_timeout=30,
        )
        print(f"Connected. Armed: {vehicle.armed}, mode: {vehicle.mode.name}")
        print("!!! REMOVE THE PROPELLERS BEFORE TESTING !!!")

        while True:
            raw = input(f"Throttle 1-{MAX_THROTTLE_PERCENT}% (Enter to exit): ").strip()
            if not raw:
                break
            try:
                throttle = float(raw)
            except ValueError:
                print("Enter a number.")
                continue
            if not 0 < throttle <= MAX_THROTTLE_PERCENT:
                print(f"Throttle must be between 1 and {MAX_THROTTLE_PERCENT}.")
                continue

            try:
                duration = float(input(f"Duration in seconds (0.5-{MAX_DURATION_SEC}): "))
            except (ValueError, EOFError):
                print("Invalid duration.")
                continue
            if not 0.5 <= duration <= MAX_DURATION_SEC:
                print(f"Duration must be between 0.5 and {MAX_DURATION_SEC} s.")
                continue

            if vehicle.armed:
                print("The drone is already armed; test not started.")
                continue

            if input("Are the propellers removed? (yes/no): ").strip().lower() != "yes":
                print("Test cancelled.")
                continue

            run_all_motors(vehicle, throttle, duration)

    except (KeyboardInterrupt, EOFError):
        print("\nStop requested.")
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        if vehicle is not None:
            disarm(vehicle, throttle_to_pwm(vehicle, 0))
            vehicle.close()
            print("Connection closed.")


if __name__ == "__main__":
    run_motor_test()
