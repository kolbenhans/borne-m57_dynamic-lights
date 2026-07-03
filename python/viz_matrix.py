#!/usr/bin/env python3
"""
Bar-graph visualizer via VialRGB direct mode.
Python computes bands + renders each LED — palette/gain/bands changeable without reflash.
Audio: parec (int16), same pipeline as sound_grabber.py.
Rendering: same x/y→band/level formula as firmware render_bars().
"""
import os, sys, time, subprocess
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, '/usr/lib/python3.14/site-packages')
sys.path.insert(1, _here)

import numpy as np
from m57_hid import M57

RATE       = 48000
CHANNELS   = 2
FPS        = 20
DECAY      = 15
AUTO_DECAY = 0.995
AUTO_FLOOR = 80.0
AUTO_LEVEL = 0.85

N_BANDS  = 12
N_LEVELS = 5

CHUNK_BYTES = int(RATE * CHANNELS * 2 / FPS)
BAND_EDGES  = np.geomspace(60, 12000, N_BANDS + 1)

# Physical positions from g_led_config, LEDs 0-57
LED_POS = [
    (0,12),(16,12),(32,12),(48,12),(64,12),(80,12),
    (0,25),(16,25),(32,25),(48,25),(64,25),(80,25),(96,25),
    (0,38),(16,38),(32,38),(48,38),(64,38),(80,38),(96,38),
    (0,51),(16,51),(32,51),(48,51),(64,51),(80,51),
    (32,63),(48,63),(64,63),
    (128,12),(144,12),(160,12),(178,12),(194,12),(210,12),
    (112,25),(128,25),(144,25),(160,25),(178,25),(194,25),(210,25),
    (112,38),(128,38),(144,38),(160,38),(178,38),(194,38),(210,38),
    (128,51),(144,51),(160,51),(178,51),(194,51),(210,51),
    (112,63),(128,63),(144,63),
]

# (band, level) per LED — same formula as firmware render_bars()
LED_MAP = []
for x, y in LED_POS:
    b  = min(x * N_BANDS  // 224, N_BANDS  - 1)
    lv = min(y * N_LEVELS // 64,  N_LEVELS - 1)
    LED_MAP.append((b, (N_LEVELS - 1) - lv))  # invert: bottom=level0

# ── Palette (change freely, no reflash needed) ──────────────────────────────
PALETTE = [          # level 0 (bottom) → level 4 (top)
    (  0, 255,   0), # green
    (160, 255,   0), # yellow-green
    (255, 220,   0), # yellow
    (255,  80,   0), # orange
    (255,   0,   0), # red
]

_display  = np.zeros(N_BANDS, dtype=np.float32)
_auto_max = np.ones(N_BANDS,  dtype=np.float32) * AUTO_FLOOR

def calc_frame(samples):
    windowed = samples * np.hanning(samples.size)
    fft      = np.abs(np.fft.rfft(windowed))
    freqs    = np.fft.rfftfreq(samples.size, d=1.0 / RATE)
    raw = np.array([
        np.sqrt(np.mean(fft[mask])) if np.any(mask) else 0.0
        for mask in ((freqs >= lo) & (freqs < hi)
                     for lo, hi in zip(BAND_EDGES[:-1], BAND_EDGES[1:]))
    ], dtype=np.float32)
    _auto_max[:] = np.maximum(raw, _auto_max * AUTO_DECAY)
    _auto_max[:] = np.maximum(_auto_max, AUTO_FLOOR)
    normalized   = np.clip(raw / _auto_max * 255 * AUTO_LEVEL, 0, 255)
    _display[:]  = np.maximum(normalized, _display - DECAY)
    heights = np.minimum((_display * (N_LEVELS + 1) / 256).astype(int), N_LEVELS)
    frame = [(0, 0, 0)] * 58
    for led, (band, level) in enumerate(LED_MAP):
        if level < heights[band]:
            frame[led] = PALETTE[level]
    return frame

def get_monitor():
    result = subprocess.run(['pactl', 'info'], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.startswith('Default Sink:'):
            return line.split(':', 1)[1].strip() + '.monitor'
    raise RuntimeError('no PulseAudio monitor found')

monitor = get_monitor()
kb = M57()
kb.activate_viz_frame()
print(f"Winamp bars [{monitor}]. Ctrl+C to stop.")

proc = subprocess.Popen(
    ['parec', '-d', monitor, '--format=s16le',
     f'--rate={RATE}', f'--channels={CHANNELS}', '--latency-msec=20'],
    stdout=subprocess.PIPE,
)

try:
    while True:
        data = proc.stdout.read(CHUNK_BYTES)
        if not data:
            break
        samples = np.frombuffer(data, dtype=np.int16).reshape(-1, CHANNELS).mean(axis=1)
        kb.send_frame(calc_frame(samples))
except KeyboardInterrupt:
    pass
finally:
    proc.terminate()
    kb.send_frame([(0, 0, 0)] * 58)
    kb.close()
