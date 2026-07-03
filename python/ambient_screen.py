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

def capture_tiny(scale=CAPTURE_SCALE):
    result = subprocess.run(
        ["grim", "-s", str(scale), "-"],
        capture_output=True,
        check=True,
    )
    return Image.open(BytesIO(result.stdout)).convert("RGB")

def sample_zones(img):
    """5 horizontal stripes from center third of image.
    Index 0 = bottom stripe → palette level 0 (low bar).
    Index 4 = top stripe    → palette level 4 (high bar).
    Uses saturation-weighted average so vibrant pixels dominate over dark/grey."""
    w, h = img.size
    arr  = np.asarray(img, dtype=np.float32)
    x0, x1 = w // 3, (2 * w) // 3
    zones = []
    stripe = h // 5
    for i in range(5):
        y1 = h - i * stripe
        y0 = max(0, h - (i + 1) * stripe)
        zone = arr[y0:y1, x0:x1].reshape(-1, 3)
        sat     = zone.max(axis=1) - zone.min(axis=1)  # per-pixel saturation
        weights = (sat + 1.0) ** 2                      # vibrant pixels dominate
        avg = np.average(zone, axis=0, weights=weights)
        zones.append(avg.astype(np.uint8))
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
