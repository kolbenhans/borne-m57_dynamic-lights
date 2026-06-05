## Build

qmk compile -kb m57 -km via

## Flash

Copy:

.build/m57_via.uf2

to the keyboard UF2 drive.

Both halves must be flashed individually.


## Entering Bootloader Mode

### If a firmware based on this repository is already installed

The firmware supports the standard QMK `QK_BOOT` keycode.

If a key has been assigned to `QK_BOOT` (for example through Vial), pressing that key will immediately reboot the keyboard into the UF2 bootloader.

The keyboard should then appear as a removable USB storage device and can be updated by copying the generated `.uf2` file.

---

### First-time bootloader entry (factory firmware)

If the keyboard is still running the original vendor firmware and no `QK_BOOT` key is available, follow the original bootloader entry procedure documented by Sophronesis:

https://github.com/sophronesis/borne-m57-firmware

See:

**"First-time bootloader entry (tweezer method)"**

This procedure is typically only required for the initial installation.

After flashing a QMK/Vial firmware, a `QK_BOOT` key can be assigned through Vial, allowing future firmware updates without opening the keyboard.
