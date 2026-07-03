RGB_MATRIX_EFFECT(m57_dynamic_lights)
RGB_MATRIX_EFFECT(m57_viz_frame)

#ifdef RGB_MATRIX_CUSTOM_EFFECT_IMPLS

extern void dynamic_lights_render(uint8_t led_min, uint8_t led_max);

// ---------------------------------------------------------------------------
// Effects
// ---------------------------------------------------------------------------

static bool m57_dynamic_lights(effect_params_t *params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    dynamic_lights_render(led_min, led_max);
    return rgb_matrix_check_finished_leds(led_max);
}

// ---------------------------------------------------------------------------
// Python frame receiver — reads from g_direct_mode_colors[] populated by
// VialRGB FASTSET (0x07/0x42). Activated via Raw HID 0x02/0xA3 or USER05.
// ---------------------------------------------------------------------------

#ifdef RGB_MATRIX_EFFECT_VIALRGB_DIRECT
extern HSV g_direct_mode_colors[RGB_MATRIX_LED_COUNT];
#endif

static bool m57_viz_frame(effect_params_t *params) {
#ifdef RGB_MATRIX_EFFECT_VIALRGB_DIRECT
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB rgb = rgb_matrix_hsv_to_rgb(g_direct_mode_colors[i]);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    return rgb_matrix_check_finished_leds(led_max);
#else
    return true;
#endif
}

#endif
