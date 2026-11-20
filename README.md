# drone-audio

Audio capture on a drone (Raspberry Pi 5 + Pixhawk 6C): record ambient sound,
remove motor/propeller noise, estimate the ambient noise level and stream the
result to a PC.

## Layout

```
drone-audio/
├── pi/                         # runs on the Raspberry Pi
│   ├── run.py                  # entry point: menu that starts the modules
│   ├── interfaces.py           # data types + module interfaces (the contract)
│   ├── config.py               # all settings in one place
│   ├── motors/                 # drone motor control
│   │   ├── __init__.py         # exports run_motor_test
│   │   └── motor_test.py       # arm + throttle via MAVLink
│   ├── audio_capture/          # microphone -> AudioFrame
│   │   ├── __init__.py         # exports MicCapture
│   │   └── mic_capture.py
│   ├── noise_filter/           # AudioFrame -> FilteredFrame
│   │   ├── __init__.py         # exports the filter used by run.py
│   │   ├── passthrough.py      # placeholder filter (no change)
│   │   └── levels.py           # dBFS helpers
│   ├── communication/          # FilteredFrame -> network
│   │   ├── __init__.py         # exports UdpCommunication
│   │   ├── packet.py           # packet format (encode)
│   │   └── udp.py              # UDP sender
│   └── requirements.txt
└── desktop/                    # runs on the PC
    ├── receiver.py             # receives frames, prints levels, saves WAV
    └── requirements.txt
```

Each module is a folder (Python package). Files inside a folder can be split
or added freely; other code imports only what the folder's `__init__.py`
exports, e.g. `from noise_filter import PassThroughFilter`.

## Data flow

```
audio_capture  --AudioFrame-->  noise_filter  --FilteredFrame-->  communication  --UDP-->  desktop/receiver
```

`run.py` connects the three modules in one loop:

```python
frame = capture.read()
result = noise_filter.process(frame)
comm.send(result)
```

Each module depends only on `interfaces.py` and `config.py`, so it can be rewritten
independently as long as it keeps the same methods.

## Ownership

| File | Owner |
|---|---|
| `pi/noise_filter/` | Mateia |
| `pi/motors/`, `pi/audio_capture/`, `pi/communication/`, `desktop/` | Slava |
| `pi/interfaces.py`, `pi/run.py`, `pi/config.py` | shared (change only by agreement) |

## Git workflow

- `main`: stable, `develop`: integration.
- Work on `feature/<name>` branches created from `develop`.
- Changes to `interfaces.py` go in a separate small PR that both review.

```bash
git checkout develop
git checkout -b feature/noise-filter
# ... work ...
git push -u origin feature/noise-filter   # then open a PR into develop
```

## Setup

On the Pi:

```bash
cd pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Motor test alone: `python -m motors.motor_test` (from `pi/`).

On the PC:

```bash
cd desktop
pip install -r requirements.txt
python receiver.py --save out.wav
```

Set `DESKTOP_HOST` in `pi/config.py` to the PC's IP address.
List audio devices with `python -m sounddevice` and set `AUDIO_DEVICE` if needed.

**Remove the propellers before running the motor test.**
