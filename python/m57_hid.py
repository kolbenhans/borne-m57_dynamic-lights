import hid

VID, PID = 0x6401, 0x45D4
USAGE_PAGE, USAGE = 0xFF60, 0x61

# VIA command IDs
_VIA_LIGHTING_SET = 0x07
_VIA_LIGHTING_GET = 0x08

# VialRGB sub-commands
_GET_INFO      = 0x40
_GET_MODE      = 0x41
_SET_MODE      = 0x41
_GET_SUPPORTED = 0x42

# VialRGB standard effect IDs
EFFECT_OFF                = 0x0000
EFFECT_DIRECT             = 0x0001
EFFECT_SOLID_COLOR        = 0x0002
EFFECT_ALPHAS_MODS        = 0x0003
EFFECT_GRADIENT_UP_DOWN   = 0x0004
EFFECT_GRADIENT_LEFT_RIGHT= 0x0005
EFFECT_BREATHING          = 0x0006
EFFECT_BAND_SAT           = 0x0007
EFFECT_BAND_VAL           = 0x0008
EFFECT_BAND_PINWHEEL_SAT  = 0x0009
EFFECT_BAND_PINWHEEL_VAL  = 0x000A
EFFECT_CYCLE_ALL          = 0x000D
EFFECT_CYCLE_LEFT_RIGHT   = 0x000E
EFFECT_CYCLE_UP_DOWN      = 0x000F
EFFECT_CYCLE_PINWHEEL     = 0x0013
EFFECT_CYCLE_SPIRAL       = 0x0014
EFFECT_RAINDROPS          = 0x0018
EFFECT_HUE_BREATHING      = 0x001A
EFFECT_HUE_WAVE           = 0x001C


class M57:
    def __init__(self):
        for info in hid.enumerate(VID, PID):
            if info['usage_page'] == USAGE_PAGE and info['usage'] == USAGE:
                self.dev = hid.Device(path=info['path'])
                return
        raise RuntimeError("m57 not found — check USB and udev rules")

    def _wr(self, data):
        pkt = bytearray(33)
        for i, b in enumerate(data):
            pkt[i + 1] = b
        self.dev.write(bytes(pkt))
        return list(self.dev.read(32, timeout=500))

    def get_info(self):
        """Returns (protocol_version, max_brightness)."""
        r = self._wr([_VIA_LIGHTING_GET, _GET_INFO])
        return r[2] | (r[3] << 8), r[4]

    def get_mode(self):
        """Returns (effect_id, speed, hue, sat, val)."""
        r = self._wr([_VIA_LIGHTING_GET, _GET_MODE])
        return r[2] | (r[3] << 8), r[4], r[5], r[6], r[7]

    def set_mode(self, effect_id, speed=128, hue=0, sat=255, val=200):
        """Set RGB effect. Both halves update via QMK split sync."""
        self._wr([_VIA_LIGHTING_SET, _SET_MODE,
                  effect_id & 0xFF, (effect_id >> 8) & 0xFF,
                  speed, hue, sat, val])

    def close(self):
        self.dev.close()


if __name__ == "__main__":
    import sys, time

    kb = M57()
    ver, max_br = kb.get_info()
    print(f"VialRGB v{ver}, max_brightness={max_br}")

    if len(sys.argv) >= 2:
        effect = int(sys.argv[1], 0)
        hue    = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
        kb.set_mode(effect, hue=hue)
        print(f"Set effect 0x{effect:04X} hue={hue}")
    else:
        # Demo: cycle through a few effects
        for effect, name in [
            (EFFECT_SOLID_COLOR,  "solid red"),
            (EFFECT_BREATHING,    "breathing"),
            (EFFECT_CYCLE_ALL,    "cycle_all"),
            (EFFECT_RAINDROPS,    "raindrops"),
        ]:
            print(f"  {name} ...", end="", flush=True)
            kb.set_mode(effect, hue=0, sat=255, val=200)
            time.sleep(2)
            print(" ok")

    kb.close()
