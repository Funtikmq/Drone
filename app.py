#!/usr/bin/env python3
"""
Pornește TOATE motoarele simultan (ArduCopter), pe banc, FĂRĂ ELICE.

Cum funcționează: setează modul STABILIZE, armează drona și trimite
RC override pe canalul 3 (throttle). Testul de motoare MAVLink din
ArduPilot nu poate porni mai multe motoare în același timp, așa că
aici se folosește armarea + throttle.

Notă: în STABILIZE controlerul de atitudine este activ, deci pe banc
motoarele pot avea turații puțin diferite (încearcă să "corecteze").
Este normal.
"""
import select
import sys
import time

import collections
import collections.abc

collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect, VehicleMode
from pymavlink import mavutil


CONNECTION_STRING = "/dev/ttyACM0"  # Example: "udp:127.0.0.1:14550"
BAUD_RATE = 57600
MAX_THROTTLE_PERCENT = 40           # Limită de siguranță; mărește doar dacă e nevoie
MAX_DURATION_SEC = 30
RAMP_SEC = 1.0                      # Creștere lină a throttle-ului
SEND_RATE_HZ = 10                   # RC override trebuie retrimis des (RC_OVERRIDE_TIME)
FORCE_ARM = False                   # True = sare peste pre-arm checks (doar pe banc!)
ARM_TIMEOUT_SEC = 10
DISARM_TIMEOUT_SEC = 10
FORCE_MAGIC = 21196                 # Valoare MAVLink pentru arm/disarm forțat


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
    """Roll/pitch/yaw la centru (1500), throttle pe canalul 3."""
    master = vehicle._master
    msg = vehicle.message_factory.rc_channels_override_encode(
        master.target_system,
        master.target_component,
        1500,          # ch1 roll
        1500,          # ch2 pitch
        throttle_pwm,  # ch3 throttle
        1500,          # ch4 yaw
        0, 0, 0, 0,    # ch5-ch8: eliberate
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
    """Throttle la minim, apoi armare. Returnează True dacă a armat."""
    # Throttle jos înainte de armare (cerință ArduCopter)
    for _ in range(10):
        send_rc_override(vehicle, min_pwm)
        time.sleep(0.1)

    send_arm_command(vehicle, True, FORCE_ARM)
    deadline = time.monotonic() + ARM_TIMEOUT_SEC
    while not vehicle.armed and time.monotonic() < deadline:
        send_rc_override(vehicle, min_pwm)
        time.sleep(0.1)

    if not vehicle.armed:
        print("Armarea a eșuat. Verifică mesajele din Mission Planner / "
              "pre-arm checks (sau setează FORCE_ARM = True, doar pe banc).")
    return vehicle.armed


def disarm(vehicle, min_pwm):
    """Throttle la minim, apoi dezarmare forțată și eliberare override."""
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
            print("ATENȚIE: drona raportează în continuare că e armată!")
        else:
            print("Dezarmare confirmată.")
    except Exception as exc:
        print(f"Nu s-a putut confirma dezarmarea: {exc}")
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
            print("Scrie q sau d pentru oprire.")
    return False


def run_all_motors(vehicle, throttle_percent, duration_sec):
    min_pwm = throttle_to_pwm(vehicle, 0)

    if not set_mode(vehicle, "STABILIZE"):
        print(f"Nu s-a putut seta STABILIZE (mod curent: {vehicle.mode.name}).")
        return

    if not arm(vehicle, min_pwm):
        return

    print(f"Toate motoarele la {throttle_percent:g}% timp de {duration_sec:g} s.")
    print("Scrie q sau d și apasă Enter pentru oprire.")

    start = time.monotonic()
    period = 1.0 / SEND_RATE_HZ
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= duration_sec:
                break
            if not vehicle.armed:
                print("Drona s-a dezarmat singură; oprire.")
                break
            if stop_requested():
                break

            ramp = min(1.0, elapsed / RAMP_SEC) if RAMP_SEC > 0 else 1.0
            pwm = throttle_to_pwm(vehicle, throttle_percent * ramp)
            send_rc_override(vehicle, pwm)
            time.sleep(period)
    finally:
        disarm(vehicle, min_pwm)


def main():
    vehicle = None
    try:
        print(f"Conectare la {CONNECTION_STRING} ...")
        vehicle = connect(
            CONNECTION_STRING,
            baud=BAUD_RATE,
            wait_ready=True,
            heartbeat_timeout=30,
        )
        print(f"Conectat. Armat: {vehicle.armed}, mod: {vehicle.mode.name}")
        print("!!! SCOATE ELICELE ÎNAINTE DE TEST !!!")

        while True:
            raw = input(f"Throttle 1–{MAX_THROTTLE_PERCENT}% (Enter pentru ieșire): ").strip()
            if not raw:
                break
            try:
                throttle = float(raw)
            except ValueError:
                print("Introdu un număr.")
                continue
            if not 0 < throttle <= MAX_THROTTLE_PERCENT:
                print(f"Throttle trebuie să fie între 1 și {MAX_THROTTLE_PERCENT}.")
                continue

            try:
                duration = float(input(f"Durata în secunde (0.5–{MAX_DURATION_SEC}): "))
            except (ValueError, EOFError):
                print("Durată invalidă.")
                continue
            if not 0.5 <= duration <= MAX_DURATION_SEC:
                print(f"Durata trebuie să fie între 0.5 și {MAX_DURATION_SEC} s.")
                continue

            if vehicle.armed:
                print("Drona este deja armată; testul nu pornește.")
                continue

            if input("Elicele sunt scoase? (da/nu): ").strip().lower() != "da":
                print("Test anulat.")
                continue

            run_all_motors(vehicle, throttle, duration)

    except (KeyboardInterrupt, EOFError):
        print("\nOprire cerută.")
    except Exception as exc:
        print(f"Eroare: {exc}")
    finally:
        if vehicle is not None:
            disarm(vehicle, throttle_to_pwm(vehicle, 0))
            vehicle.close()
            print("Conexiune închisă.")


if __name__ == "__main__":
    main()