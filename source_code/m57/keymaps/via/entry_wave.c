#include "entry_wave.h"
#include "dynamic_lights.h"
#include "transactions.h"

#ifdef RAW_ENABLE

static bool     entry_wave_active = false;
static uint32_t entry_wave_timer  = 0;

void entry_wave_start(void) {
    entry_wave_active = true;
    entry_wave_timer  = timer_read32();
}

bool entry_wave_running(void) {
    return entry_wave_active;
}

uint32_t entry_wave_elapsed(void) {
    return timer_elapsed32(entry_wave_timer);
}

void entry_wave_stop(void) {
    entry_wave_active = false;
}

static void entry_wave_sync_handler(uint8_t in_buflen, const void *in_data,
                                     uint8_t out_buflen, void *out_data) {
    (void)in_buflen;
    (void)in_data;
    (void)out_buflen;
    (void)out_data;
    entry_wave_start();
}

void entry_wave_register_rpc(void) {
    transaction_register_rpc(USER_ENTRY_WAVE_STARTUP, entry_wave_sync_handler);
}

// Starts the wave locally and pushes it to the other half too — a plain
// entry_wave_start() only fires where it's called, which is always the
// master (raw HID / key events never reach the slave directly).
void entry_wave_trigger(void) {
    entry_wave_start();
    if (is_keyboard_master()) {
        transaction_rpc_send(USER_ENTRY_WAVE_STARTUP, 0, NULL);
    }
}

// Mode-switch commands sent by the Python viz tool (m57_hid.py / viz_hid.py).
void raw_hid_receive_kb(uint8_t *data, uint8_t length) {
    if (length < 2 || data[0] != 0x02) return;

    switch (data[1]) {
        case 0xA3:
            entry_wave_trigger();
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_viz_frame);
            break;

        case 0xA4:
            dynamic_lights_on_mode_enter();
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_dynamic_lights);
            break;
    }
}

#else

bool     entry_wave_running(void)      { return false; }
uint32_t entry_wave_elapsed(void)      { return 0; }
void     entry_wave_stop(void)         {}
void     entry_wave_start(void)        {}
void     entry_wave_trigger(void)      {}
void     entry_wave_register_rpc(void) {}
void     raw_hid_receive_kb(uint8_t *data, uint8_t length) { (void)data; (void)length; }

#endif
