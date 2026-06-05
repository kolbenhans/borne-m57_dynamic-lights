
# Development Notes

## Firmware Origin

The original vendor source was provided through the BORNE Discord community.

The project is based on the source package published by:

https://github.com/sophronesis/borne-m57-firmware

Several parts of the original source required cleanup before successful compilation on modern Vial-QMK versions.

---

## Bootloader

The keyboard uses a custom TinyUF2-based STM32F401 bootloader.

Relevant files:

* `source_code/m57/m57.c`
* `source_code/m57/rules.mk`

Bootloader entry:

```c
*(volatile uint32_t *)0x2000FC00UL = 0xC220B134UL;
NVIC_SystemReset();
```

This implementation was verified on hardware.

---

## Dynamic Lighting

Implementation:

```text
source_code/m57/keymaps/via/dynamic_lights.c
```

Activation:

```text
RGB Matrix → Alpha Mods
```

The dynamic lighting system reads key assignments from the active Vial keymap and colors keys according to their function.

Normal RGB Matrix effects remain available.

---

## Split EEPROM Behavior

Each half stores its own Vial EEPROM data.

Dynamic lighting therefore uses the locally stored keymap of the currently connected half.

After layout changes:

1. Save layout from Vial
2. Connect the opposite half directly via USB
3. Load the saved layout
4. Reconnect preferred master half

This keeps both halves synchronized.

---

## Startup Comet

A startup comet animation is displayed when entering the dynamic lighting mode.

Known issue:

* The right half may execute the startup animation twice during split initialization.

See:

```text
docs/known-limitations.md
```

---

## Modern QMK Cleanup

The original source relied on several legacy definitions.

The following items were migrated to modern Vial-QMK conventions:

* keyboard.json based metadata
* matrix_size definitions
* RGB Matrix configuration
* bootloader configuration
* split transport configuration

Legacy matrix size definitions were removed from:

```text
config.h
```

and are now defined in:

```text
keyboard.json
```

---

## Safe Recovery

Before modifying:

* bootloader code
* split transport
* RGB Matrix initialization
* keyboard.json layouts

always keep a known working UF2 backup.

The file stored in:

```text
firmware/working/
```

is intended as a recovery build.
