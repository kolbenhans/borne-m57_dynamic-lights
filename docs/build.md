# Build Guide

## Platform

All shell commands in this guide use bash syntax.

| Platform | Recommended environment |
|---|---|
| Linux | Standard terminal |
| macOS | Standard terminal |
| Windows | [QMK MSYS](https://msys.qmk.fm/) or WSL (Windows Subsystem for Linux) |

In **QMK MSYS** and **WSL**, all commands in this guide work as written.  
Native Windows Command Prompt and PowerShell alternatives are noted where they differ.

---

## Prerequisites

| Tool | Linux / macOS | Windows |
|---|---|---|
| git | Package manager | [QMK MSYS](https://msys.qmk.fm/) (included) |
| QMK CLI | `pip install qmk` | [QMK MSYS](https://msys.qmk.fm/) (included) |
| Build toolchain | See [QMK Getting Started](https://docs.qmk.fm/newbs_getting_started) | [QMK MSYS](https://msys.qmk.fm/) (included) |

**Windows:** Install [QMK MSYS](https://msys.qmk.fm/). It includes git, the QMK CLI, and the complete build toolchain. No additional installation needed.

**Linux / macOS:** Install the QMK CLI, then follow the [QMK Getting Started guide](https://docs.qmk.fm/newbs_getting_started) to install the build toolchain for your distribution.

```bash
pip install qmk
```

---

## Verified Setup

Repository: `borne-m57_dynamic-lights`

Tested with:

* vial-kb/vial-qmk
* Python 3.11
* arm-none-eabi-gcc 14.2.0

Verified:

* Builds successfully
* UF2 generated
* Vial detected
* QK_BOOT functional
* TinyUF2 bootloader preserved
* Both M57 halves successfully flashed
* Keyboard detected by Vial
* Matrix test successful
* Dynamic lighting functional
* Startup comet functional

---

## Directory Layout

This guide uses the following structure. You can choose any base directory — just replace `~/projects` with your preferred path consistently throughout.

```
~/projects/
├── vial-qmk/                  ← vial-qmk checkout
└── borne-m57_dynamic-lights/  ← this repository
```

---

## Step 1 — Clone vial-qmk

```bash
git clone --depth 1 https://github.com/vial-kb/vial-qmk ~/projects/vial-qmk
cd ~/projects/vial-qmk
git submodule update --init --recursive --depth 1
```

---

## Step 2 — Clone this repository

```bash
git clone https://github.com/kolbenhans/borne-m57_dynamic-lights.git ~/projects/borne-m57_dynamic-lights
```

---

## Step 3 — Link the keyboard source into vial-qmk

**Linux / macOS / QMK MSYS / WSL:**

```bash
ln -s ~/projects/borne-m57_dynamic-lights/source_code/m57 \
      ~/projects/vial-qmk/keyboards/m57
```

**Windows (Command Prompt, without QMK MSYS):**

```cmd
mklink /D "%USERPROFILE%\projects\vial-qmk\keyboards\m57" ^
          "%USERPROFILE%\projects\borne-m57_dynamic-lights\source_code\m57"
```

> [!NOTE]
> `mklink /D` requires administrator privileges on Windows.  
> Using QMK MSYS avoids this — `ln -s` works there without elevation.

---

## Step 4 — Install linker scripts

> [!IMPORTANT]
> The custom linker scripts must be copied into the vial-qmk tree before building.
> Without them the build will fail.

**Linux / macOS / QMK MSYS / WSL:**

```bash
cp ~/projects/borne-m57_dynamic-lights/source_code/ld/*.ld \
   ~/projects/vial-qmk/platforms/chibios/boards/common/ld/
```

**Windows (Command Prompt, without QMK MSYS):**

```cmd
copy "%USERPROFILE%\projects\borne-m57_dynamic-lights\source_code\ld\*.ld" ^
     "%USERPROFILE%\projects\vial-qmk\platforms\chibios\boards\common\ld\"
```

---

## Step 5 — Build firmware

```bash
cd ~/projects/vial-qmk
qmk clean
qmk compile -kb m57 -km via
```

Output:

```
.build/m57_via.uf2
```

---

## Flashing

Only flash after verifying that:

* QK_BOOT is present in the keymap
* The UF2 bootloader is functional
* A tested firmware backup exists

> [!IMPORTANT]
> The keyboard is a split design.
>
> Firmware updates must be flashed to **both halves individually**.
>
> Flash the first half, reconnect it normally, then repeat for the second half.

---

## Notes

The original vendor source contained an invalid JSON definition and legacy matrix definitions in `config.h`.

For modern vial-qmk builds:

* `matrix_size` is defined in `keyboard.json`
* `MATRIX_ROWS` and `MATRIX_COLS` are intentionally removed from `config.h`

Reintroducing `MATRIX_ROWS` or `MATRIX_COLS` will break the build on newer QMK versions.

Current bootloader configuration:

```make
FIRMWARE_FORMAT = uf2
UF2_FAMILY = 0xabcdf401
OPT_DEFS += -DBOOTLOADER_TINYUF2
```

Vial configuration:

* Vial enabled
* VIA enabled
* QK_BOOT available from keymap
* Vial UID must remain unchanged to preserve stored layouts across firmware updates

EEPROM configuration:

* 10 dynamic layers
* 15 macros
* 4 KB logical EEPROM via wear leveling

If increasing dynamic layer count or EEPROM usage:

* Review `WEAR_LEVELING_BACKING_SIZE`
* Review `DYNAMIC_KEYMAP_EEPROM_MAX_ADDR`

before flashing.

---

## Dynamic Lighting

Dynamic lighting features:

* Implemented as a standalone custom RGB matrix effect (`dynamic_lights`)
* Active by default on startup
* Re-enterable via `KEYBIND_USER01` (`0x7E01`) in the keymap
* All other RGB Matrix modes remain fully available
* Startup comet animation runs when entering the dynamic lighting mode
* Animation is synchronized across both halves via split RPC
* Dynamic lighting uses the active Vial keymap as its color source
* Dynamic lighting state is synchronized from the master half to the slave half

Lighting synchronization features:

* Layer changes are synchronized automatically
* Vial keymap changes are detected automatically
* Slave lighting updates within approximately one second after layout changes
* Blink animations are rendered locally on each half to minimize split transport traffic

No manual layout synchronization is required for dynamic lighting.

Note:

Each half still maintains its own Vial EEPROM and keymap storage. The dynamic lighting system synchronizes lighting information only and does not synchronize EEPROM contents.
