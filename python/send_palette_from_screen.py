import argparse
import json
import subprocess
import time
from io import BytesIO

import numpy as np
from PIL import Image

from hid_helper import open_raw_hid, hid_write

from send_palette_from_image import (
    image_to_pixels,
    filter_pixels,
    print_palette,
    quantize_pixels,
    correct_for_keyboard_leds,
    build_palette_packet,
)

def get_active_monitor_geometry():
    active = json.loads(
        subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    monitor_id = active["monitor"]

    monitors = json.loads(
        subprocess.run(
            ["hyprctl", "monitors", "-j"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    monitor = next(
        m for m in monitors
        if m["id"] == monitor_id
    )

    return (
        f'{monitor["x"]},'
        f'{monitor["y"]} '
        f'{monitor["width"]}x'
        f'{monitor["height"]}'
    )

def grab_active_monitor(scale=1.0):
    geometry = get_active_monitor_geometry()
    cmd = ["grim", "-g", geometry]
    if scale != 1.0:
        cmd += ["-s", str(scale)]
    cmd.append("-")
    result = subprocess.run(cmd, check=True, capture_output=True)
    return Image.open(BytesIO(result.stdout)).convert("RGB")

def extract_dominant_palette(pixels, count=5, gamma=2.2, apply_correction=True):
    quantized = quantize_pixels(pixels, step=24)

    colors, counts = np.unique(
        quantized,
        axis=0,
        return_counts=True,
    )

    colors_f = colors.astype(np.float32)
    brightness = colors_f.mean(axis=1)
    saturation = colors_f.max(axis=1) - colors_f.min(axis=1)

    valid = (brightness > 40) & (saturation > 20)
    if valid.any():
        colors = colors[valid]
        counts = counts[valid]
        saturation = saturation[valid]

    score = counts * ((saturation + 1) ** 1.3)
    order = np.argsort(score)[::-1]
    colors = colors[order]

    selected = []

    for color in colors:
        if len(selected) >= count:
            break

        if selected:
            distances = [
                np.linalg.norm(color.astype(np.int16) - c.astype(np.int16))
                for c in selected
            ]

            if min(distances) < 40:
                continue

        selected.append(color)

    while len(selected) < count:
        selected.append(selected[-1] if selected else np.array([16, 16, 16], dtype=np.uint8))

    selected = np.array(selected[:count], dtype=np.uint8)

    if apply_correction:
        selected = np.array(
            [correct_for_keyboard_leds(c, gamma=gamma) for c in selected],
            dtype=np.uint8,
        )

    return selected

def palette_distance(a, b):
    if a is None or b is None:
        return 9999.0

    diff = a.astype(np.int16) - b.astype(np.int16)
    return float(np.mean(np.abs(diff)))


def blend_palette(a, b, t):
    mixed = (a.astype(np.float32) * (1.0 - t)) + (b.astype(np.float32) * t)
    return mixed.astype(np.uint8)

def send_palette_packet_to_device(dev, palette):
    packet = build_palette_packet(palette)
    hid_write(dev, packet)

def send_palette_transition(from_palette, to_palette, selector=None, steps=8, delay=0.04):
    dev = open_raw_hid(selector=selector)

    try:
        if from_palette is None:
            send_palette_packet_to_device(dev, to_palette)
            return

        for step in range(1, steps + 1):
            t = step / steps
            palette = blend_palette(from_palette, to_palette, t)
            send_palette_packet_to_device(dev, palette)
            time.sleep(delay)
    finally:
        dev.close()

def main():
    parser = argparse.ArgumentParser(
        description="Extract keyboard palette from active window screenshot.",
    )

    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--select", type=str, help="Raw HID device index or regex")
    parser.add_argument("--gamma", type=float, default=1.5)
    parser.add_argument("--no-correction", action="store_true")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--threshold", type=float, default=18.0)
    parser.add_argument("--fade-steps", type=int, default=8)
    parser.add_argument("--fade-delay", type=float, default=0.04)

    args = parser.parse_args()

    last_palette = None

    while True:
        image = grab_active_monitor()

        pixels = image_to_pixels(image, size=96)
        pixels = filter_pixels(pixels)

        palette = extract_dominant_palette(
            pixels,
            gamma=args.gamma,
            apply_correction=not args.no_correction,
        )

        distance = palette_distance(last_palette, palette)

        if distance >= args.threshold:
            print(f"\nNew screen palette (distance={distance:.1f}):\n")
            print_palette(palette)

            if args.send:
                send_palette_transition(
                    last_palette,
                    palette,
                    selector=args.select,
                    steps=args.fade_steps,
                    delay=args.fade_delay,
                )

            last_palette = palette.copy()

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
