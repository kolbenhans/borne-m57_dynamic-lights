#!/usr/bin/env python3
"""
Ambient screen color → keyboard palette.
Captures a tiny screenshot every interval, samples 12 grid zones,
picks 5 most saturated colors, sends via HID 0xA2.
"""
import argparse
import subprocess
import time
from io import BytesIO

import numpy as np
from PIL import Image

from hid_helper import open_raw_hid, hid_write
from send_palette_from_image import build_palette_packet, correct_for_keyboard_leds

PALETTE_SIZE = 5

# ponytail: grim scale 0.05 → ~100×56px at 1080p, fast enough for ambient
CAPTURE_SCALE = 0.05

# Sample positions: dice-5 pattern (cx, cy as fractions of image size)
#   ●       ●
#       ●
#   ●       ●
DICE_5_POSITIONS = [
    (0.33, 0.33),  # top-left
    (0.67, 0.33),  # top-right
    (0.50, 0.50),  # center
    (0.33, 0.67),  # bottom-left
    (0.67, 0.67),  # bottom-right
]
# Each zone samples a square region of this fraction of image size around the point
ZONE_RADIUS = 0.10

def capture_tiny():
    result = subprocess.run(
        ["grim", "-s", str(CAPTURE_SCALE), "-"],
        capture_output=True,
        check=True,
    )
    return Image.open(BytesIO(result.stdout)).convert("RGB")

def sample_zones(img):
    w, h  = img.size
    arr   = np.asarray(img, dtype=np.float32)
    zones = []

    for cx_frac, cy_frac in DICE_5_POSITIONS:
        cx, cy = int(cx_frac * w), int(cy_frac * h)
        rx, ry = max(1, int(ZONE_RADIUS * w)), max(1, int(ZONE_RADIUS * h))
        x0, x1 = max(0, cx - rx), min(w, cx + rx)
        y0, y1 = max(0, cy - ry), min(h, cy + ry)
        zone = arr[y0:y1, x0:x1].reshape(-1, 3)
        zones.append(zone.mean(axis=0).astype(np.uint8))

    return np.array(zones, dtype=np.uint8)   # (5, 3)

def pick_palette(zones, gamma=2.2, apply_correction=True):
    # Dice-5: zones ARE the palette — one color per zone, fixed positions, no selection
    selected = np.array(zones[:PALETTE_SIZE], dtype=np.uint8)

    if apply_correction:
        selected = np.array(
            [correct_for_keyboard_leds(c, gamma=gamma) for c in selected],
            dtype=np.uint8,
        )
    return selected

def blend_palette(a, b, t):
    return ((a.astype(np.float32) * (1.0 - t)) + (b.astype(np.float32) * t)).astype(np.uint8)

def palette_distance(a, b):
    return float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))

def main():
    parser = argparse.ArgumentParser(description="Ambient screen color → m57 palette")
    parser.add_argument("--interval",    type=float, default=0.5,  help="Capture interval in seconds (default: 0.5)")
    parser.add_argument("--threshold",   type=float, default=8.0,  help="Min palette distance to trigger update (default: 8)")
    parser.add_argument("--fade-steps",  type=int,   default=4,    help="Blend steps on palette change (default: 4)")
    parser.add_argument("--fade-delay",  type=float, default=0.04, help="Delay between blend steps (default: 0.04)")
    parser.add_argument("--gamma",       type=float, default=2.2)
    parser.add_argument("--no-correction", action="store_true")
    parser.add_argument("--select",      type=str,   help="HID device index or regex")
    args = parser.parse_args()

    dev          = open_raw_hid(selector=args.select)
    last_palette = None

    try:
        while True:
            t0 = time.monotonic()

            try:
                img   = capture_tiny()
                zones = sample_zones(img)
                pal   = pick_palette(zones, gamma=args.gamma,
                                     apply_correction=not args.no_correction)
            except Exception as e:
                print(f"capture error: {e}")
                time.sleep(args.interval)
                continue

            if last_palette is None or palette_distance(last_palette, pal) >= args.threshold:
                if last_palette is not None and args.fade_steps > 1:
                    for step in range(1, args.fade_steps + 1):
                        blended = blend_palette(last_palette, pal, step / args.fade_steps)
                        hid_write(dev, build_palette_packet(blended))
                        time.sleep(args.fade_delay)
                else:
                    hid_write(dev, build_palette_packet(pal))
                last_palette = pal.copy()

            elapsed = time.monotonic() - t0
            sleep   = max(0.0, args.interval - elapsed)
            time.sleep(sleep)

    except KeyboardInterrupt:
        pass
    finally:
        dev.close()

if __name__ == "__main__":
    main()
