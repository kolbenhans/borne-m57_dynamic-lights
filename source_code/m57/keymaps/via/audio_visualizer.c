#include "audio_visualizer.h"
#include "dynamic_lights.h"

#ifdef RAW_ENABLE

void raw_hid_receive_kb(uint8_t *data, uint8_t length) {
    if (length < 2 || data[0] != 0x02) return;

    switch (data[1]) {
        case 0xA3:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_m57_viz_frame);
            break;
        case 0xA4:
            dynamic_lights_on_mode_enter();
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_m57_dynamic_lights);
            break;
    }
}

#else
void raw_hid_receive_kb(uint8_t *data, uint8_t length) { (void)data; (void)length; }
#endif
