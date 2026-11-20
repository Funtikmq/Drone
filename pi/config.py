"""All settings in one place."""

# Flight controller (Pixhawk over USB)
CONNECTION_STRING = "/dev/ttyACM0"   # e.g. "udp:127.0.0.1:14550" for MAVProxy
BAUD_RATE = 57600

# Audio capture
AUDIO_DEVICE = None        # None = default input; see `python -m sounddevice`
SAMPLE_RATE = 48000
CHANNELS = 1
BLOCK_SIZE = 1024          # samples per frame (~21 ms at 48 kHz)

# Communication (Pi -> PC)
DESKTOP_HOST = "192.168.1.100"   # PC IP address
DESKTOP_PORT = 5005
