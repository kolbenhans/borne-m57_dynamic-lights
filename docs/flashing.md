# Flashing Guide

## Linux: USB Device Permissions

On Linux, udev rules are required to access the keyboard in bootloader mode without `sudo`.

This is a one-time setup:

```bash
sudo cp ~/projects/vial-qmk/util/udev/50-qmk.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

> [!NOTE]
> Adjust the path to match your actual `vial-qmk` location if it differs from `~/projects/vial-qmk`.

---

## Build

qmk compile -kb m57 -km via

## Flash

Copy:

.build/m57_via.uf2

to the keyboard UF2 drive.

Both halves must be flashed individually.


## Entering Bootloader Mode

### If a firmware based on this repository is already installed

#### Option 1: Bootmagic (hold a key while connecting USB)

Works on any firmware built from this repo, no `QK_BOOT` key assignment required:

* **Left half**: hold `ESC` (top-left key) while plugging in USB.
* **Right half**: hold `6` (leftmost key of the top row) while plugging in USB.

Only hold the key on whichever half you're actually connecting — not both at once.

#### Option 2: QK_BOOT

The firmware supports the standard QMK `QK_BOOT` keycode.

If a key has been assigned to `QK_BOOT` (for example through Vial), pressing that key will immediately reboot the keyboard into the UF2 bootloader.

Either option makes the keyboard appear as a removable USB storage device, which can be updated by copying the generated `.uf2` file.

---

### First-time bootloader entry (factory firmware)

If the keyboard is still running the original vendor firmware and no `QK_BOOT` key is available, follow the original bootloader entry procedure documented by Sophronesis:

https://github.com/sophronesis/borne-m57-firmware

See:

**"First-time bootloader entry (tweezer method)"**

This procedure is typically only required for the initial installation.

After flashing a QMK/Vial firmware, a `QK_BOOT` key can be assigned through Vial, allowing future firmware updates without opening the keyboard.
