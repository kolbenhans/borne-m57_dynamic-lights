# Known Limitations

Currently no known functional limitations.

Notes:

* Each half maintains its own independent Vial EEPROM storage.
* Dynamic lighting synchronization does not synchronize EEPROM contents.
* The startup comet animation is synchronized across both halves via split RPC (`USER_DYNAMIC_LIGHTS_STARTUP`).
