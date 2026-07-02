#!/usr/bin/env python3
"""
Audio visualizer sender for borne m57.
Protocol: Raw HID [0x02, 0xA1, band0..11, peak0..11, pad...]
"""
import argparse
import os
import subprocess
import time

import numpy as np
from hid_helper import open_raw_hid, hid_write

PACKET_SIZE    = 32
CMD            = 0x02
SUBCMD         = 0xA1
RATE           = 48000
CHANNELS       = 2
BAND_COUNT     = 12
FPS            = 20
DECAY          = 15
PEAK_DECAY     = 5
PEAK_HOLD_FRAMES = 16
ENABLE_PEAK_HOLD = False
AUTO_GAIN_DECAY  = 0.995
AUTO_GAIN_FLOOR  = 80.0
AUTO_GAIN_LEVEL  = 0.85

CHUNK_BYTES = int(RATE * CHANNELS * 2 / FPS)
BAND_EDGES  = np.geomspace(60, 12000, BAND_COUNT + 1)

running_max   = np.ones(BAND_COUNT,  dtype=np.float32) * AUTO_GAIN_FLOOR
display_bands = np.zeros(BAND_COUNT, dtype=np.float32)
peak_bands    = np.zeros(BAND_COUNT, dtype=np.float32)
peak_hold     = np.zeros(BAND_COUNT, dtype=np.int16)

def get_default_monitor():
    result = subprocess.run(["pactl", "info"], capture_output=True, text=True, check=True)
    for line in result.stdout.splitlines():
        if line.startswith("Default Sink:"):
            return line.split(":", 1)[1].strip() + ".monitor"
    raise RuntimeError("Could not determine PulseAudio/PipeWire default sink")

def start_audio(monitor):
    return subprocess.Popen(
        ["parec", "-d", monitor, "--format=s16le",
         f"--rate={RATE}", f"--channels={CHANNELS}", "--latency-msec=20"],
        stdout=subprocess.PIPE,
    )

def read_samples(proc):
    data = proc.stdout.read(CHUNK_BYTES)
    if not data:
        return None
    s = np.frombuffer(data, dtype=np.int16)
    if s.size == 0:
        return None
    return s.reshape(-1, CHANNELS).mean(axis=1)

def calc_bands(samples):
    windowed = samples * np.hanning(samples.size)
    fft      = np.abs(np.fft.rfft(windowed))
    freqs    = np.fft.rfftfreq(windowed.size, d=1.0 / RATE)
    vals     = []
    for lo, hi in zip(BAND_EDGES[:-1], BAND_EDGES[1:]):
        mask = (freqs >= lo) & (freqs < hi)
        vals.append(np.sqrt(np.mean(fft[mask])) if np.any(mask) else 0.0)
    return np.array(vals, dtype=np.float32)

def normalize(values):
    running_max[:] = np.maximum(values, running_max * AUTO_GAIN_DECAY)
    return np.clip(values / running_max * 255 * AUTO_GAIN_LEVEL, 0, 255)

def apply_decay(raw):
    display_bands[:] = np.maximum(raw, display_bands - DECAY)
    return display_bands

def update_peaks():
    if not ENABLE_PEAK_HOLD:
        peak_bands[:] = display_bands
        return peak_bands
    for i in range(BAND_COUNT):
        if display_bands[i] >= peak_bands[i]:
            peak_bands[i] = display_bands[i]
            peak_hold[i]  = PEAK_HOLD_FRAMES
        else:
            if peak_hold[i] > 0:
                peak_hold[i] -= 1
            else:
                peak_bands[i] = max(display_bands[i], peak_bands[i] - PEAK_DECAY)
    return peak_bands

def build_packet(levels, peaks):
    pkt = [CMD, SUBCMD] + levels + peaks
    pkt += [0x00] * (PACKET_SIZE - len(pkt))
    return pkt[:PACKET_SIZE]

def open_hid(selector=None):
    while True:
        try:
            return open_raw_hid(selector=selector)
        except Exception as e:
            print("waiting for HID:", e)
            time.sleep(1)

def write_packet(dev, pkt, selector=None):
    try:
        hid_write(dev, pkt)
        return dev
    except Exception as e:
        print("HID write failed:", e)
        try:
            dev.close()
        except Exception:
            pass
        time.sleep(0.5)
        return open_hid(selector=selector)

def main():
    parser = argparse.ArgumentParser(description="m57 audio visualizer")
    parser.add_argument("--select", type=str, help="HID device index or regex")
    args = parser.parse_args()

    monitor = get_default_monitor()
    print("monitor:", monitor)

    dev  = open_hid(selector=args.select)
    proc = start_audio(monitor)

    try:
        while True:
            samples = read_samples(proc)
            if samples is None:
                continue
            raw     = normalize(calc_bands(samples))
            display = apply_decay(raw)
            peaks   = update_peaks()
            levels  = [min(255, int(v)) for v in display]
            p_list  = [min(255, int(v)) for v in peaks]
            pkt     = build_packet(levels, p_list)
            dev     = write_packet(dev, pkt, selector=args.select)
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        dev.close()

if __name__ == "__main__":
    main()
