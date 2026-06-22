RGB_MATRIX_EFFECT(m57_dynamic_lights)

#ifdef RGB_MATRIX_CUSTOM_EFFECT_IMPLS

extern void dynamic_lights_render(uint8_t led_min, uint8_t led_max);

static bool m57_dynamic_lights(effect_params_t *params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    dynamic_lights_render(led_min, led_max);

    return rgb_matrix_check_finished_leds(led_max);
}

#endif