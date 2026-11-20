# drone-audio

Audio capture on a drone (Raspberry Pi 5 + Pixhawk 6C): record ambient sound,
remove motor/propeller noise, estimate the ambient noise level and stream the
result to a PC.

## Layout

```
drone-audio/
├── pi/                     # runs on the Raspberry Pi
│   ├── run.py              # entry point: menu that starts the modules
│   ├── interfaces.py       # data types + module interfaces (the contract)
│   ├── config.py           # all settings in one place
│   ├── motors.py           # motor test (arm + throttle via MAVLink)
│   ├── audio_capture.py    # microphone -> AudioFrame
│   ├── noise_filter.py     # AudioFrame -> FilteredFrame
│   ├── communication.py    # FilteredFrame -> network (UDP)
│   └── requirements.txt
└── desktop/                # runs on the PC
    ├── receiver.py         # receives frames, prints levels, saves WAV
    └── requirements.txt
```

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

Each module only depends on `interfaces.py`, so it can be rewritten
independently as long as it keeps the same methods.

## Ownership

| File | Owner |
|---|---|
| `pi/noise_filter.py` | colleague |
| `pi/motors.py`, `pi/audio_capture.py`, `pi/communication.py`, `desktop/` | me |
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

On the PC:

```bash
cd desktop
pip install -r requirements.txt
python receiver.py --save out.wav
```

Set `DESKTOP_HOST` in `pi/config.py` to the PC's IP address.
List audio devices with `python -m sounddevice` and set `AUDIO_DEVICE` if needed.

**Remove the propellers before running the motor test.**
