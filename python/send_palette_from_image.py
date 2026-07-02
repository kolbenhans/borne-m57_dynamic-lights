import argparse
from pathlib import Path

from hid_helper import open_raw_hid, hid_write

import numpy as np
from PIL import Image


PALETTE_SIZE = 5
PACKET_SIZE = 32
PACKET_COMMAND = 0x02
PACKET_SUBCOMMAND_PALETTE = 0xA2

# Wallpaper integration
#
# The implementation below is specific to Caelestia Shell on Hyprland.
# It reads the currently active wallpaper path from Caelestia's state file.
#
# Other desktop environments can implement their own wallpaper provider.
# For example:
#   - Windows: Registry or SystemParametersInfoW()
#   - KDE Plasma: wallpaper configuration files / DBus
#   - GNOME: gsettings
#
# The only requirement is returning a valid image path.
CAELESTIA_WALLPAPER_PATH = Path(
    "~/.local/state/caelestia/wallpaper/path.txt"
).expanduser()

def get_current_wallpaper():
    if CAELESTIA_WALLPAPER_PATH.exists():
        path = Path(CAELESTIA_WALLPAPER_PATH.read_text().strip()).expanduser()

        if path.exists():
            return path

        raise RuntimeError(f"Wallpaper path does not exist: {path}")

    raise RuntimeError("No supported current-wallpaper source found")

def load_image(path):
    return Image.open(path).convert("RGB")


def image_to_pixels(image, size=120):
    image.thumbnail((size, size))

    pixels = np.asarray(image, dtype=np.uint8).reshape(-1, 3)
    return pixels


def filter_pixels(pixels):
    pixels_f = pixels.astype(np.float32)

    brightness = pixels_f.mean(axis=1)
    saturation = pixels_f.max(axis=1) - pixels_f.min(axis=1)

    mask = (
        (brightness > 30) &
        (brightness < 210) &
        (saturation > 20)
    )

    filtered = pixels[mask]

    if filtered.size == 0:
        return pixels

    return filtered


def quantize_pixels(pixels, step=32):
    return (pixels // step) * step


def extract_palette(pixels, count=PALETTE_SIZE, gamma=2.2, apply_correction=True):
    quantized = quantize_pixels(pixels, step=16)

    colors, counts = np.unique(
        quantized,
        axis=0,
        return_counts=True,
    )

    colors_f = colors.astype(np.float32)

    r = colors_f[:, 0]
    g = colors_f[:, 1]
    b = colors_f[:, 2]

    brightness = colors_f.mean(axis=1)
    saturation = colors_f.max(axis=1) - colors_f.min(axis=1)

    valid = (
        (brightness > 25) &
        (brightness < 245) &
        (saturation > 35)
    )

    colors = colors[valid]
    counts = counts[valid]
    colors_f = colors.astype(np.float32)

    r = colors_f[:, 0]
    g = colors_f[:, 1]
    b = colors_f[:, 2]

    brightness = colors_f.mean(axis=1)
    saturation = colors_f.max(axis=1) - colors_f.min(axis=1)

    families = [
        ("yellow", (r > 160) & (g > 140) & (b < 100)),
        ("pink",   (r > 160) & (b > 80)  & (g < 120)),
        ("cyan",   (g > 140) & (b > 120) & (r < 140)),
        ("dark", (brightness < 90) & (saturation > 20) & (b > 30)),
        ("accent", (saturation > 80) & ~((r > 140) & (g > 140) & (b < 120))),
    ]

    selected = []

    for _, mask in families:
        if len(selected) >= count:
            break

        idxs = np.where(mask)[0]
        if len(idxs) == 0:
            continue

        local_score = counts[idxs] * ((saturation[idxs] + 1) ** 1.3)
        best = idxs[np.argmax(local_score)]
        color = colors[best]

        if selected:
            distances = [
                np.linalg.norm(color.astype(np.int16) - c.astype(np.int16))
                for c in selected
            ]
            if min(distances) < 55:
                continue

        selected.append(color)

    score = counts * ((saturation + 1) ** 1.3)
    order = np.argsort(score)[::-1]

    for idx in order:
        if len(selected) >= count:
            break

        color = colors[idx]

        if not selected:
            selected.append(color)
            continue

        distances = [
            np.linalg.norm(color.astype(np.int16) - c.astype(np.int16))
            for c in selected
        ]

        if min(distances) > 70:
            selected.append(color)

    while len(selected) < count:
        selected.append(np.array([80, 80, 80], dtype=np.uint8))

    selected = np.array(selected[:count], dtype=np.uint8)

    if apply_correction:
        selected = np.array(
            [correct_for_keyboard_leds(c, gamma=gamma) for c in selected],
            dtype=np.uint8,
        )

    return selected

def print_palette(palette):
    print("Detected palette:\n")

    for i, color in enumerate(palette):
        r, g, b = [int(v) for v in color]
        print(f"{i}: ({r:3}, {g:3}, {b:3})  #{r:02X}{g:02X}{b:02X}")

def send_palette_hid(palette, selector=None):
    packet = build_palette_packet(palette)

    dev = open_raw_hid(selector=selector)

    try:
        hid_write(dev, packet)
    finally:
        dev.close()

def build_palette_packet(palette):
    packet = bytearray(PACKET_SIZE)

    packet[0] = PACKET_COMMAND
    packet[1] = PACKET_SUBCOMMAND_PALETTE
    packet[2] = len(palette)

    offset = 3

    for color in palette:
        r, g, b = [int(v) for v in color]

        packet[offset + 0] = r
        packet[offset + 1] = g
        packet[offset + 2] = b

        offset += 3

    return bytes(packet)

def correct_for_keyboard_leds(color, gamma=2.2, brightness=1.35):
    r, g, b = [int(v) for v in color]

    r = ((r / 255.0) ** gamma) * 255
    g = ((g / 255.0) ** gamma) * 255
    b = ((b / 255.0) ** gamma) * 255

    r = min(255, int(r * brightness))
    g = min(255, int(g * brightness))
    b = min(255, int(b * brightness))

    return np.array([r, g, b], dtype=np.uint8)

def main():
    parser = argparse.ArgumentParser(
        description="Extract and optionally send a keyboard visualizer palette from an image.",
    )

    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        help="Path to an image file",
    )

    parser.add_argument(
        "--current-wallpaper",
        action="store_true",
        help="Use current wallpaper from supported desktop integrations",
    )

    parser.add_argument(
        "--send",
        action="store_true",
        help="Send palette to keyboard via HID",
    )

    parser.add_argument(
        "--show-packet",
        action="store_true",
        help="Print HID packet bytes",
    )

    parser.add_argument(
        "--gamma",
        type=float,
        default=2.2,
        help="Gamma correction for keyboard LEDs",
    )

    parser.add_argument(
        "--no-correction",
        action="store_true",
        help="Disable keyboard LED correction",
    )

    parser.add_argument(
        "--select",
        type=str,
        help="Automatically select Raw HID device matching this regex",
    )

    args = parser.parse_args()

    if args.current_wallpaper:
        image_path = get_current_wallpaper()
        print(f"Using current wallpaper: {image_path}\n")
    elif args.image is not None:
        image_path = args.image
    else:
        parser.error("Please provide an image path or use --current-wallpaper")

    image = load_image(image_path)
    pixels = image_to_pixels(image)
    pixels = filter_pixels(pixels)

    palette = extract_palette(
        pixels,
        gamma=args.gamma,
        apply_correction=not args.no_correction,
    )

    print_palette(palette)

    packet = build_palette_packet(palette)

    if args.show_packet:
        print("\nHID packet:")
        print(" ".join(f"{byte:02X}" for byte in packet))

    if args.send:
        send_palette_hid(palette, selector=args.select)
        print("\nPalette sent via HID.")
    else:
        print("\nDry run only. Use --send to upload palette.")

if __name__ == "__main__":
    main()
