# BORNE M57 Dynamic Lights

## Verified Setup

Repository:
`borne-m57_dynamic-lights`

Tested with:

- vial-kb/vial-qmk
- Python 3.11
- arm-none-eabi-gcc 14.2.0

Verified:

- Builds successfully
- UF2 generated
- Vial detected
- QK_BOOT functional
- TinyUF2 bootloader preserved

Verified on hardware:

- Single M57 half successfully flashed
- Keyboard detected by Vial
- Matrix test successful
- QK_BOOT verified
- TinyUF2 bootloader preserved

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

- QK_BOOT is present in the keymap
- The UF2 bootloader is functional
- A tested firmware backup exists

Flash the generated UF2 file using the keyboard bootloader.

---

## Notes

The original vendor source contained an invalid JSON definition and legacy matrix definitions in `config.h`.

For modern vial-qmk builds:

- `matrix_size` is defined in `info.json`
- `MATRIX_ROWS` and `MATRIX_COLS` are intentionally removed from `config.h`

Reintroducing `MATRIX_ROWS` or `MATRIX_COLS` will break the build on newer QMK versions.

Current bootloader configuration:

```make
FIRMWARE_FORMAT = uf2
UF2_FAMILY = 0xabcdf401
OPT_DEFS += -DBOOTLOADER_TINYUF2
```

Vial configuration:

- Vial enabled
- VIA enabled
- QK_BOOT available from keymap
- Vial UID must remain unchanged to preserve stored layouts across firmware updates

EEPROM configuration:

- 10 dynamic layers
- 15 macros
- 4 KB logical EEPROM via wear leveling

If increasing dynamic layer count or EEPROM usage:

- Review `WEAR_LEVELING_BACKING_SIZE`
- Review `DYNAMIC_KEYMAP_EEPROM_MAX_ADDR`

before flashing.


-lights


k

cc 14.2.0


ully


nal
der preserved

xisting yet
/github.com/vial-kb/vial-qmk ~/projects/vial-qmk
l-qmk
ate --init --recursive --depth 1

 to your vial-qmk working directory
rne-m57-dynamic-lights/source_code/m57 \
vial-qmk/keyboards/m57

-m57-dynamic-lights/source_code/ld/*.ld \
l-qmk/platforms/chibios/boards/common/ld/

our firmware
l-qmk
57 -km via
lash -kb m57 -km via

