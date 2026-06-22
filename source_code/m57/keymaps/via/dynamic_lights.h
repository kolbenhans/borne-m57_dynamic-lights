#pragma once

#include QMK_KEYBOARD_H

void dynamic_lights_on_mode_enter(void);
void dynamic_lights_render(uint8_t led_min, uint8_t led_max);