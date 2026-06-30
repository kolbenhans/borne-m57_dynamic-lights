#!/usr/bin/env python3
import os, subprocess, sys, time

# system hid has correct usage_page support; venv hid does not
sys.path.insert(0, '/usr/lib/python3.14/site-packages')
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import sounddevice as sd
from m57_hid import M57, EFFECT_SOLID_COLOR

RATE  = 48000
CHUNK = 2048
GAIN  = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0  # ponytail: tune if too dim/bright

_freqs = np.fft.rfftfreq(CHUNK, 1.0 / RATE)
_bass  = (_freqs >= 20) & (_freqs <= 250)

def bass_val(data):
    fft = np.abs(np.fft.rfft(data[:, 0]))
    return min(200, int(np.sqrt(np.mean(fft[_bass] ** 2)) * GAIN))

def get_monitor():
    try:
        sink = subprocess.check_output(['pactl', 'get-default-sink'], text=True).strip()
        return sink + '.monitor'
    except Exception:
        return None

monitor = get_monitor()
if not monitor:
    sys.exit("No PulseAudio/PipeWire monitor source found")

os.environ['PULSE_SOURCE'] = monitor
kb = M57()
kb.set_mode(EFFECT_SOLID_COLOR, hue=0, sat=255, val=0)
print(f"Bass-reactive on [{monitor}] GAIN={GAIN}. Ctrl+C to stop.")

def callback(indata, frames, t, status):
    kb.set_mode(EFFECT_SOLID_COLOR, hue=0, sat=255, val=bass_val(indata))

with sd.InputStream(device='pulse', channels=1, samplerate=RATE,
                    blocksize=CHUNK, callback=callback):
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

kb.set_mode(EFFECT_SOLID_COLOR, val=0)
kb.close()
