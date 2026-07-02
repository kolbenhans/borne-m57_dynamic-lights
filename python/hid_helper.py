import sys
# ponytail: system hid needed — venv hidapi 0.15.0 returns usage_page=0 on Linux
sys.path.insert(0, '/usr/lib/python3.14/site-packages')

import hid
import re

USAGE_PAGE = 0xFF60
USAGE      = 0x61

def _search_text(d):
    return " ".join([
        d.get("manufacturer_string") or "",
        d.get("product_string") or "",
        str(d.get("path") or ""),
    ])

def find_raw_hid_devices():
    return [d for d in hid.enumerate()
            if d.get("usage_page") == USAGE_PAGE and d.get("usage") == USAGE]

def select_device(devices, selector=None):
    if not devices:
        raise RuntimeError("No compatible Raw HID device found")

    if selector:
        if selector.isdigit():
            i = int(selector)
            if 0 <= i < len(devices):
                return devices[i]
            raise RuntimeError(f"index out of range: {selector}")

        pattern = re.compile(selector, re.IGNORECASE)
        matches = [d for d in devices if pattern.search(_search_text(d))]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise RuntimeError(f"No device matches: {selector}")
        devices = matches

    if len(devices) == 1:
        return devices[0]

    print("Multiple Raw HID devices found:")
    for i, d in enumerate(devices):
        print(f"  [{i}] {d.get('manufacturer_string')} {d.get('product_string')} path={d.get('path')}")

    while True:
        choice = input("Select [0]: ").strip()
        if choice == "":
            return devices[0]
        try:
            i = int(choice)
            if 0 <= i < len(devices):
                return devices[i]
        except ValueError:
            pass

def open_raw_hid(selector=None):
    info = select_device(find_raw_hid_devices(), selector=selector)
    dev  = hid.Device(path=info["path"])
    print(f"Opened: {info.get('manufacturer_string')} {info.get('product_string')}")
    return dev

def hid_write(dev, packet):
    dev.write(bytes(packet))
