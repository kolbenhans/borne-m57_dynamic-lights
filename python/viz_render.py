"""
M57 frame renderers — shared by VizWorker (GUI) and viz_matrix.py (standalone).

All render_* functions take:
  display  : np.ndarray shape (N_BANDS,), values 0-255 (smoothed band magnitudes)
  pal      : list of 5 (r, g, b) tuples, index 0=low/bottom, 4=high/top
and return a list of 58 (r, g, b) tuples ready for M57.send_frame().
"""

import math
import numpy as np

N_BANDS  = 12
N_LEVELS = 5
VIS_BRIGHTNESS = 150   # max brightness cap (out of 255)

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

# Bars: (band 0-11, level 0=bottom .. 4=top)
LED_MAP = [
    (min(x * N_BANDS // 224, N_BANDS - 1),
     (N_LEVELS - 1) - min(y * N_LEVELS // 64, N_LEVELS - 1))
    for x, y in LED_POS
]

# Center / Kitt: (row 0=top .. 4=bottom, distance from x=112)
LED_MAP_CENTER = [
    (min(y * N_LEVELS // 64, N_LEVELS - 1), abs(x - 112))
    for x, y in LED_POS
]

LED_COUNT = len(LED_POS)   # 58


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vs(v):
    """Apply VIS_BRIGHTNESS cap."""
    return int(v * VIS_BRIGHTNESS // 255)

def _s8(a, b):
    """scale8: a * b / 255, integer."""
    return a * b // 255

def _qa8(a, b):
    """qadd8: saturating add."""
    return min(255, a + b)


# ── Render modes ──────────────────────────────────────────────────────────────

def render_bars(display, pal, outline=False):
    """Mode 0 (filled) / Mode 1 (top-dot / dots).
    outline=False → filled bars; outline=True → only the topmost LED per bar."""
    heights = np.minimum((display * (N_LEVELS + 1) / 256).astype(int), N_LEVELS)
    frame = [(0, 0, 0)] * LED_COUNT
    for led, (band, level) in enumerate(LED_MAP):
        h = int(heights[band])
        lit = (level < h) if not outline else (h > 0 and level == h - 1)
        if lit:
            r, g, b = pal[level]
            frame[led] = (_vs(r), _vs(g), _vs(b))
    return frame


def render_center(display, pal, kitt=False):
    """Mode 2 (Center) / Mode 3 (Kitt): horizontal bars expanding from x=112.
    Each of the 5 rows is driven by every other band (0,2,4,6,8).
    Center: color = palette index by distance; Kitt: color = palette index by row."""
    MAX_DIST = 112
    frame = [(0, 0, 0)] * LED_COUNT
    row_vals = [float(display[min(i * 2, N_BANDS - 1)]) for i in range(N_LEVELS)]
    for led, (row, dist) in enumerate(LED_MAP_CENTER):
        val = row_vals[row]
        if val <= 0:
            continue
        width = int(val * MAX_DIST / 210)
        if dist <= width:
            ci = row if kitt else min(dist * N_LEVELS // MAX_DIST, N_LEVELS - 1)
            r, g, b = pal[ci]
            frame[led] = (_vs(r), _vs(g), _vs(b))
    return frame


# ── Waterdrop ─────────────────────────────────────────────────────────────────

_WD_COUNT     = 6
_WD_SPEED     = 6
_WD_THRESHOLD = 187   # 0-255; bass above this triggers a drop
_WD_GAP       = 3     # frames between consecutive drops

class WaterdropState:
    def __init__(self):
        self.drops      = [{'radius': 0, 'age': 0, 'active': False, 'color': 0}
                           for _ in range(_WD_COUNT)]
        self.next_color = 0
        self.cooldown   = 0

def render_waterdrop(display, pal, state):
    """Mode 4: bass-triggered ripple rings expanding from each half-center."""
    bass = float(max(display[0], display[1], display[2]))

    if state.cooldown > 0:
        state.cooldown -= 1

    if bass > _WD_THRESHOLD and state.cooldown == 0:
        for drop in state.drops:
            if not drop['active']:
                drop.update(radius=0, age=255, active=True, color=state.next_color)
                state.next_color = (state.next_color + 1) % N_LEVELS
                state.cooldown   = _WD_GAP
                break

    frame = [(0, 0, 0)] * LED_COUNT
    for led, (x, y) in enumerate(LED_POS):
        cx   = 56 if x < 112 else 168
        dist = int(math.sqrt((x - cx) ** 2 + (y - 32) ** 2))

        r = g = b = 0
        for drop in state.drops:
            if not drop['active']:
                continue
            rad    = drop['radius']
            effect = max(0, min(255, rad - dist))
            bright = 255 - effect
            if bright == 0:
                continue
            delta = abs(dist - rad)
            ci    = 4 if delta < 12 else 3 if delta < 28 else 2 if delta < 44 else 1 if delta < 64 else 0
            fade  = max(0, 255 - delta * 4)
            fb    = _s8(_s8(bright, fade), drop['age'])
            pr, pg, pb = pal[drop['color']]
            r = _qa8(r, _s8(_vs(pr), fb))
            g = _qa8(g, _s8(_vs(pg), fb))
            b = _qa8(b, _s8(_vs(pb), fb))

        frame[led] = (r, g, b)

    for drop in state.drops:
        if not drop['active']:
            continue
        drop['radius'] += _WD_SPEED
        if drop['age'] > 8:
            drop['age'] -= 8
        else:
            drop['active'] = False

    return frame
