# Borne M57 - Custom Vial Firmware

> [!IMPORTANT]
> This project is based on the original firmware sources provided by
> [sophronesis](https://github.com/sophronesis/borne-m57-firmware).
>
> The firmware has been extensively cleaned up, documented and extended with
> dynamic key lighting, startup animations and a modernized build workflow.

## Demo Video

Coming soon.

YouTube:
[![Dynamic lighting by key assignments with vial-qmk](https://img.youtube.com/vi/RrIkk1Ya_Js/maxresdefault.jpg)](https://youtu.be/RrIkk1Ya_Js)

## Features

- Vial support
- Dynamic key lighting
- Startup comet animation
- Split keyboard support
- STM32F401 UF2 bootloader support
- RGB Matrix support
- Dynamic keymap support
- Split EEPROM/Vial workflow documentation
- Host-driven audio/ambient visualizer (`viz_frame` effect + Python GUI)

## Documentation

- Build instructions: docs/build.md
- Flashing guide: docs/flashing.md
- Development notes: docs/development.md
- Known limitations: docs/known-limitations.md

## Python Visualizer GUI

The `viz_frame` RGB Matrix effect is driven entirely from the host — audio
bars/waterdrop, wallpaper ambient color and screen color-shot are all
computed in Python and streamed to the keyboard over Raw HID.

The GUI lives in [`viz-frame-tools`](https://github.com/kolbenhans/viz-frame-tools)
(a git submodule at `python/`, shared with the Sofle and ID75 builds):

```bash
git submodule update --init --recursive
pip install -r python/requirements.txt
python3 python/viz_gui.py
```
