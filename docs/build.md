# BORNE M57 Dynamic Lights

## Verified Setup

Repository:
`borne-m57_dynamic-lights`

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

Verified on hardware:

* Both M57 halves successfully flashed
* Keyboard detected by Vial
* Matrix test successful
* QK_BOOT verified
* TinyUF2 bootloader preserved
* Dynamic lighting functional
* Startup comet functional

---

## Python Environment

> [!IMPORTANT]
> Current builds are verified with **Python 3.11**.
>
> Newer Python versions may work, but were not tested and may introduce
> dependency issues inside the Vial/QMK toolchain.

Verify your Python version:

```bash
python --version
```

Expected:

```text
Python 3.11.x
```

---

## Create a Virtual Environment

Using a dedicated virtual environment is strongly recommended.

Example:

```bash
python3.11 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip
```

Install QMK requirements:

```bash
pip install -r requirements.txt
```

Verify the active interpreter:

```bash
which python
python --version
```

The interpreter should point to your virtual environment.

---

## QMK / Vial Requirements

Verified against:

* vial-kb/vial-qmk
* Python 3.11
* arm-none-eabi-gcc 14.2.0

This repository is intended to be built inside a working
`vial-qmk` checkout.

The keyboard sources are linked into the Vial tree via a symbolic link.

---

## Clone this repository

```bash
git clone https://github.com/<user>/borne-m57_dynamic-lights.git
cd borne-m57_dynamic-lights
```

---

## Clone vial-qmk

```bash
git clone https://github.com/vial-kb/vial-qmk ~/projects/vial-qmk
cd ~/projects/vial-qmk
git submodule update --init --recursive --depth 1
```

---

## Link this repository into your vial-qmk working tree

```bash
ln -s /path/to/borne-m57_dynamic-lights/source_code/m57 \
      ~/projects/vial-qmk/keyboards/m57
```

---

## Install linker scripts

> [!IMPORTANT]
> The custom linker scripts must be copied into the vial-qmk tree before building.
> Without them the build will fail.

```bash
cp /path/to/borne-m57_dynamic-lights/source_code/ld/*.ld \
   ~/projects/vial-qmk/platforms/chibios/boards/common/ld/
```

---

## Build firmware

```bash
cd ~/projects/vial-qmk

qmk clean
qmk compile -kb m57 -km via
```

Output:

```text
.build/m57_via.uf2
```

---

## Flashing

Only flash after verifying that:

* QK_BOOT is present in the keymap
* The UF2 bootloader is functional
* A tested firmware backup exists

Flash the generated UF2 file using the keyboard bootloader.

> [!IMPORTANT]
> The keyboard is a split design.
>
> Firmware updates must be flashed to both halves individually.
>
> Flash the first half, reconnect it normally, then repeat the process
> for the second half.

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

* Activated through RGB Matrix → Alpha Mods
* All other RGB Matrix modes remain available
* Startup comet animation runs when entering the dynamic lighting mode
* Dynamic lighting reads key assignments from the local Vial EEPROM of each half

After changing layouts in Vial:

1. Save the layout as a `.vil` file
2. Connect the other half directly via USB
3. Load the saved layout
4. Reconnect the preferred master half

This ensures that both halves use identical dynamic lighting mappings.
