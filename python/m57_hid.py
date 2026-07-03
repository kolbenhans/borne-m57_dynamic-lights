import hid
import colorsys

VID, PID = 0x6401, 0x45D4
USAGE_PAGE, USAGE = 0xFF60, 0x61
LED_COUNT   = 58
LEDS_PER_PKT = 9

# VIA command IDs
_VIA_LIGHTING_SET = 0x07
_VIA_LIGHTING_GET = 0x08

# VialRGB sub-commands
_GET_INFO      = 0x40
_GET_MODE      = 0x41
_SET_MODE      = 0x41
_FASTSET       = 0x42

def _rgb_to_qhsv(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return int(h * 255), int(s * 255), int(v * 255)

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
    @staticmethod
    def _open(path):
        if hasattr(hid, 'Device'):
            return hid.Device(path=path)
        dev = hid.device()
        dev.open_path(path)
        return dev

    @staticmethod
    def list_devices():
        """Return list of (path, label) for all connectable M57 interfaces."""
        candidates = hid.enumerate(VID, PID)
        result, seen = [], set()
        for info in candidates:
            if info['usage_page'] == USAGE_PAGE and info['usage'] == USAGE:
                p = info['path']
                if p not in seen:
                    seen.add(p)
                    label = (info.get('product_string') or 'M57').strip() or 'M57'
                    result.append((p, label))
        if not result:
            for info in candidates:
                if info.get('interface_number') == 1:
                    p = info['path']
                    if p not in seen:
                        seen.add(p)
                        label = (info.get('product_string') or 'M57').strip() or 'M57'
                        result.append((p, label))
        return result

    def __init__(self, path=None):
        if path:
            self.dev = self._open(path)
            return
        candidates = hid.enumerate(VID, PID)
        for info in candidates:
            if info['usage_page'] == USAGE_PAGE and info['usage'] == USAGE:
                self.dev = self._open(info['path'])
                return
        # hidapi on Linux reports usage_page=0; fall back to interface 1 (VIA raw HID)
        for info in candidates:
            if info.get('interface_number') == 1:
                self.dev = self._open(info['path'])
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

    def activate_direct(self):
        """Switch to VialRGB direct mode (effect ID 1)."""
        self.set_mode(EFFECT_DIRECT)

    def activate_viz_frame(self):
        """Switch firmware to m57_viz_frame effect via Raw HID 0x02/0xA3."""
        pkt = bytearray(33)
        pkt[1], pkt[2] = 0x02, 0xA3
        self.dev.write(bytes(pkt))

    def activate_dynamic_lights(self):
        """Switch firmware to m57_dynamic_lights (key coloring) via 0x02/0xA4."""
        pkt = bytearray(33)
        pkt[1], pkt[2] = 0x02, 0xA4
        self.dev.write(bytes(pkt))

    def activate_fw_visualizer(self):
        """Switch firmware to m57_audio_visualizer effect via 0x02/0xA5."""
        pkt = bytearray(33)
        pkt[1], pkt[2] = 0x02, 0xA5
        self.dev.write(bytes(pkt))

    def send_palette(self, palette):
        """Upload 5-color palette to fw_visualizer (0x02/0xA2).
        palette: list of 5 (r,g,b), index 0=low (level 0), 4=high (level 4).
        Firmware reads data[3..5]=high, data[9..11]=mid, data[12..14]=low
        and interpolates levels 1 and 3."""
        pkt = bytearray(33)
        pkt[1], pkt[2] = 0x02, 0xA2
        lo, mid, hi = palette[0], palette[2], palette[4]
        pkt[4],  pkt[5],  pkt[6]  = hi[0],  hi[1],  hi[2]
        pkt[10], pkt[11], pkt[12] = mid[0], mid[1], mid[2]
        pkt[13], pkt[14], pkt[15] = lo[0],  lo[1],  lo[2]
        self.dev.write(bytes(pkt))

    def send_frame(self, rgb):
        """Send list of LED_COUNT (r,g,b) tuples via 0x42 fastset."""
        for start in range(0, LED_COUNT, LEDS_PER_PKT):
            chunk = rgb[start:start + LEDS_PER_PKT]
            pkt = bytearray(33)
            pkt[1], pkt[2] = _VIA_LIGHTING_SET, _FASTSET
            pkt[3], pkt[4] = start & 0xFF, (start >> 8) & 0xFF
            pkt[5] = len(chunk)
            for i, (r, g, b) in enumerate(chunk):
                h, s, v = _rgb_to_qhsv(r, g, b)
                pkt[6 + i*3], pkt[7 + i*3], pkt[8 + i*3] = h, s, v
            self.dev.write(bytes(pkt))

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
