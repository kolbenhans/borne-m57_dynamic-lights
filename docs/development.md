
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
source_code/m57/keymaps/via/rgb_matrix_user.inc
```

Dynamic lighting is implemented as a standalone custom RGB matrix effect (`dynamic_lights`).

It is independent of all built-in RGB matrix effects and does not overlay or conflict with them.

Activation:

* Default mode on startup (set via `RGB_MATRIX_DEFAULT_MODE`)
* Can be re-entered via `KEYBIND_USER01` (`0x7E01`) which calls `dynamic_lights_on_mode_enter()` and switches to the custom effect

The dynamic lighting system reads key assignments from the active Vial keymap and colors keys according to their function.

All built-in RGB matrix effects remain fully available and can be cycled through independently.

---

## Split EEPROM Behavior

Each half still stores its own Vial EEPROM data.

However, dynamic lighting now uses a master-driven synchronization mechanism.

The master half periodically detects Vial keymap changes and synchronizes the lighting color definitions to the slave half using split RPC communication.

As a result:

* Dynamic lighting remains synchronized across both halves.
* Layout changes made in Vial are reflected on the slave lighting automatically.
* Manual EEPROM synchronization between halves is no longer required for lighting purposes.

Note:

The actual keymap stored in EEPROM remains independent on each half. Only the dynamic lighting state is synchronized.

## Startup Comet

A startup comet animation is displayed when entering the dynamic lighting mode.

The animation traverses all LEDs based on their physical coordinates in a snake pattern.

The master half triggers the animation on the slave half via `USER_DYNAMIC_LIGHTS_STARTUP` split RPC, so both halves animate in sync.

---

## viz_frame (host-driven visualizer)

Implementation:

```text
source_code/m57/keymaps/via/entry_wave.c
source_code/m57/keymaps/via/rgb_matrix_user.inc
```

All rendering (FFT, palette, frame composition) happens host-side in
Python (see the `python/` submodule / [`viz-frame-tools`](https://github.com/kolbenhans/viz-frame-tools));
the firmware only reads `g_direct_mode_colors[]` (filled via Raw HID
FASTSET) into the LED buffer.

`g_direct_mode_colors[]` only reaches the master half over USB — the slave
half's copy is pushed via a dedicated split RPC (`USER_SYNC_RGB_DIRECT`),
independent of `dynamic_lights`'s own sync. Two gotchas found while
building this:

* **RPC buffer size.** QMK's default `RPC_M2S_BUFFER_SIZE` is 32 bytes.
  m57's half-buffer push is `29 LEDs × 3 bytes (HSV) = 87 bytes` — too big
  for the default, and `transaction_rpc_send()` silently returns `false`
  when the payload exceeds the configured size (no error, no crash — the
  slave half just never lights up). Fixed by setting `RPC_M2S_BUFFER_SIZE 96`
  in `config.h`.
* **Master/slave orientation.** The sync must branch on `is_keyboard_left()`
  rather than always assuming the left half is master — otherwise plugging
  USB into the right half instead silently breaks the slave sync.

The entry wave (`entry_wave_trigger()`, a short diagonal color sweep on
switching into viz_frame) uses the same push-to-other-half pattern via
`USER_ENTRY_WAVE_STARTUP`, so it plays on both halves regardless of which
is master.

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

## Reference Firmware

The original vendor firmware is preserved in:

firmware/reference/vendor_original.uf2

This file is included for archival and recovery purposes only.

The vendor firmware source was incomplete and required significant cleanup
before it could be built on modern Vial-QMK versions.
