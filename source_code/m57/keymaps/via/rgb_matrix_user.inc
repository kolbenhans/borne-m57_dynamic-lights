RGB_MATRIX_EFFECT(dynamic_lights)
RGB_MATRIX_EFFECT(viz_frame)

#ifdef RGB_MATRIX_CUSTOM_EFFECT_IMPLS

#include "entry_wave.h"

extern void dynamic_lights_render(uint8_t led_min, uint8_t led_max);

// ---------------------------------------------------------------------------
// Entry wave — plays once on switching into viz_frame, before Python frames
// start arriving. Ignores RGB_MATRIX_USE_LIMITS on purpose: sweeps the full
// board geometry so both halves animate from the same shared timer.
// ---------------------------------------------------------------------------

#define VIS_BRIGHTNESS_LIMIT 150

static uint8_t vis_scale(uint8_t v) {
    return ((uint16_t)v * VIS_BRIGHTNESS_LIMIT) / 255;
}

#define ENTRY_WAVE_STEP_MS     6
#define ENTRY_WAVE_WIDTH       48
#define ENTRY_WAVE_DURATION_MS ((224 + ENTRY_WAVE_WIDTH) * ENTRY_WAVE_STEP_MS)

static bool render_entry_wave(void) {
    if (!entry_wave_running()) return false;

    uint32_t elapsed = entry_wave_elapsed();
    if (elapsed > ENTRY_WAVE_DURATION_MS) {
        entry_wave_stop();
        return false;
    }

    int16_t head = (int16_t)(elapsed / ENTRY_WAVE_STEP_MS);

    for (uint8_t led = 0; led < RGB_MATRIX_LED_COUNT; led++) {
        uint8_t  x        = g_led_config.point[led].x;
        uint8_t  y        = g_led_config.point[led].y;
        int16_t  distance = head - (int16_t)x;

        if (distance < 0 || distance >= ENTRY_WAVE_WIDTH) {
            rgb_matrix_set_color(led, 0, 0, 0);
            continue;
        }

        // Full height at head, shrinks toward tail
        uint8_t y_min = (64 * (uint8_t)distance) / ENTRY_WAVE_WIDTH;
        if (y < y_min) {
            rgb_matrix_set_color(led, 0, 0, 0);
            continue;
        }

        uint8_t hue = (uint8_t)(x / 2 + y * 2);
        RGB     rgb = hsv_to_rgb((HSV){ hue, 220, 255 });
        rgb_matrix_set_color(led, vis_scale(rgb.r), vis_scale(rgb.g), vis_scale(rgb.b));
    }

    return true;
}

// ---------------------------------------------------------------------------
// Effects
// ---------------------------------------------------------------------------

static bool dynamic_lights(effect_params_t *params) {
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

static bool viz_frame(effect_params_t *params) {
    if (render_entry_wave()) return false;
#ifdef RGB_MATRIX_EFFECT_VIALRGB_DIRECT
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    uint8_t v = rgb_matrix_config.hsv.v;
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB rgb = rgb_matrix_hsv_to_rgb(g_direct_mode_colors[i]);
        rgb_matrix_set_color(i, (uint16_t)rgb.r * v / 255, (uint16_t)rgb.g * v / 255, (uint16_t)rgb.b * v / 255);
    }
    return rgb_matrix_check_finished_leds(led_max);
#else
    return true;
#endif
}

#endif
