#!/usr/bin/env python3
"""
Audio visualizer via VialRGB direct mode.
Each of the 29 LEDs per side maps to a frequency band.
Left = lows, Right = highs (mirrored for symmetry).

Usage: python viz_direct.py [gain]
"""
import os, sys, time
sys.path.insert(0, '/usr/lib/python3.14/site-packages')
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import sounddevice as sd
from m57_hid import M57

RATE      = 48000
CHUNK     = 2048
N_LEDS    = 29
GAIN      = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
DECAY     = 20        # brightness units per frame drop
AUTO_DECAY = 0.995    # auto-gain decay per frame
AUTO_FLOOR = 80.0

import colorsys

_freqs     = np.fft.rfftfreq(CHUNK, 1.0 / RATE)
_log_edges = np.logspace(np.log10(20), np.log10(18000), N_LEDS + 1)
_bands     = [(_freqs >= _log_edges[i]) & (_freqs < _log_edges[i + 1]) for i in range(N_LEDS)]
_hues      = [i / (N_LEDS - 1) for i in range(N_LEDS)]  # red→blue

_display  = np.zeros(N_LEDS, dtype=np.float32)
_auto_max = np.ones(N_LEDS,  dtype=np.float32) * AUTO_FLOOR

def fft_to_frame(data):
    fft = np.abs(np.fft.rfft(data[:, 0] if data.ndim > 1 else data))
    raw = np.array([
        np.sqrt(np.mean(fft[m] ** 2)) if m.any() else 0.0
        for m in _bands
    ], dtype=np.float32)

    # auto-gain + decay
    _auto_max[:] = np.maximum(raw, _auto_max * AUTO_DECAY)
    _auto_max[:] = np.maximum(_auto_max, AUTO_FLOOR)
    normalized = np.clip(raw / _auto_max * 255 * 0.9, 0, 255)
    _display[:] = np.maximum(normalized, _display - DECAY)

    frame = []
    for i in range(N_LEDS):
        val = int(_display[i])
        r, g, b = colorsys.hsv_to_rgb(_hues[i], 1.0, val / 255.0)
        frame.append((int(r * 255), int(g * 255), int(b * 255)))

    # both sides same order (physical chain determines visual direction)
    return frame + frame

def get_monitor():
    import subprocess
    try:
        sink = subprocess.check_output(['pactl', 'get-default-sink'], text=True).strip()
        return sink + '.monitor'
    except Exception:
        return None

monitor = get_monitor()
if not monitor:
    sys.exit("No PulseAudio/PipeWire monitor found")

os.environ['PULSE_SOURCE'] = monitor

kb = M57()
kb.activate_direct()
print(f"Viz via direct mode [{monitor}] GAIN={GAIN}. Ctrl+C to stop.")

def callback(indata, frames, t, status):
    frame = fft_to_frame(indata)
    kb.send_frame(frame)

with sd.InputStream(device='pulse', channels=1, samplerate=RATE,
                    blocksize=CHUNK, callback=callback):
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

kb.activate_direct()
kb.send_frame([(0, 0, 0)] * 58)
kb.close()
