RGB_MATRIX_EFFECT(m57_dynamic_lights)
RGB_MATRIX_EFFECT(m57_audio_visualizer)

#ifdef RGB_MATRIX_CUSTOM_EFFECT_IMPLS

#include "audio_visualizer.h"

extern void dynamic_lights_render(uint8_t led_min, uint8_t led_max);

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

#define VIS_BRIGHTNESS_LIMIT 150

static uint8_t vis_scale(uint8_t v) {
    return ((uint16_t)v * VIS_BRIGHTNESS_LIMIT) / 255;
}

static uint8_t vis_absdiff(uint8_t a, uint8_t b) {
    return a > b ? a - b : b - a;
}

// ---------------------------------------------------------------------------
// Bars mode  (render_mode 0 = filled, 1 = outline)
// ---------------------------------------------------------------------------

static void render_bars(const visualizer_palette_t *pal, uint8_t render_mode,
                        uint8_t led_min, uint8_t led_max) {
    for (uint8_t led = led_min; led < led_max; led++) {
        uint8_t x = g_led_config.point[led].x;
        uint8_t y = g_led_config.point[led].y;

        uint8_t band  = ((uint16_t)x * VISUALIZER_BAND_COUNT) / 224;
        uint8_t level = ((uint16_t)y * VISUALIZER_LEVEL_COUNT) / 64;

        if (band  >= VISUALIZER_BAND_COUNT)  band  = VISUALIZER_BAND_COUNT  - 1;
        if (level >= VISUALIZER_LEVEL_COUNT) level = VISUALIZER_LEVEL_COUNT - 1;

        // invert y so bottom row is level 0 (loudest = top)
        level = (VISUALIZER_LEVEL_COUNT - 1) - level;

        uint8_t value      = audio_visualizer_get_band(band);
        uint8_t height     = ((uint16_t)value * (VISUALIZER_LEVEL_COUNT + 1)) / 256;
        uint8_t peak_value = audio_visualizer_get_peak(band);
        uint8_t peak_h     = ((uint16_t)peak_value * (VISUALIZER_LEVEL_COUNT + 1)) / 256;

        if (height > VISUALIZER_LEVEL_COUNT) height = VISUALIZER_LEVEL_COUNT;
        if (peak_h > VISUALIZER_LEVEL_COUNT) peak_h = VISUALIZER_LEVEL_COUNT;

        bool show_peak = (peak_h > height) && (peak_h > 0) && (level == peak_h - 1);
        bool show_bar  = (render_mode == 0) ? (level < height)
                                            : (height > 0 && level == height - 1);

        if (show_peak) {
            rgb_matrix_set_color(led, vis_scale(pal->peak_r), vis_scale(pal->peak_g), vis_scale(pal->peak_b));
        } else if (show_bar) {
            rgb_matrix_set_color(led, vis_scale(pal->level_r[level]), vis_scale(pal->level_g[level]), vis_scale(pal->level_b[level]));
        } else {
            rgb_matrix_set_color(led, 0, 0, 0);
        }
    }
}

// ---------------------------------------------------------------------------
// Center mode  (horizontal bars from center out)
// ---------------------------------------------------------------------------

static void render_center(const visualizer_palette_t *pal,
                          uint8_t led_min, uint8_t led_max) {
    // ponytail: hardcoded split constants — works for 6-col split with x 0-224
    const uint8_t center_x    = 112;
    const uint8_t max_distance = 112;

    uint8_t values[VISUALIZER_LEVEL_COUNT] = {
        audio_visualizer_get_band(0),
        audio_visualizer_get_band(2),
        audio_visualizer_get_band(4),
        audio_visualizer_get_band(6),
        audio_visualizer_get_band(8),
    };

    for (uint8_t led = led_min; led < led_max; led++) {
        uint8_t x = g_led_config.point[led].x;
        uint8_t y = g_led_config.point[led].y;

        uint8_t row = ((uint16_t)y * VISUALIZER_LEVEL_COUNT) / 64;
        if (row >= VISUALIZER_LEVEL_COUNT) row = VISUALIZER_LEVEL_COUNT - 1;

        uint8_t value = values[row];
        if (value == 0) { rgb_matrix_set_color(led, 0, 0, 0); continue; }

        uint8_t width      = ((uint16_t)value * max_distance) / 210;
        uint8_t peak_value = audio_visualizer_get_peak(row * 2);
        uint8_t peak_w     = ((uint16_t)peak_value * max_distance) / 210;
        uint8_t distance   = (x > center_x) ? (x - center_x) : (center_x - x);

        if (distance <= width) {
            uint8_t ci = ((uint16_t)distance * VISUALIZER_LEVEL_COUNT) / max_distance;
            if (ci >= VISUALIZER_LEVEL_COUNT) ci = VISUALIZER_LEVEL_COUNT - 1;
            rgb_matrix_set_color(led, vis_scale(pal->level_r[ci]), vis_scale(pal->level_g[ci]), vis_scale(pal->level_b[ci]));
        } else if (peak_w > width && distance <= peak_w && distance + 8 >= peak_w) {
            rgb_matrix_set_color(led, vis_scale(pal->peak_r), vis_scale(pal->peak_g), vis_scale(pal->peak_b));
        } else {
            rgb_matrix_set_color(led, 0, 0, 0);
        }
    }
}

// ---------------------------------------------------------------------------
// Kitt mode  (horizontal bars, row-colored)
// ---------------------------------------------------------------------------

static void render_kitt(const visualizer_palette_t *pal,
                        uint8_t led_min, uint8_t led_max) {
    const uint8_t center_x    = 112;
    const uint8_t max_distance = 112;

    uint8_t values[VISUALIZER_LEVEL_COUNT] = {
        audio_visualizer_get_band(0),
        audio_visualizer_get_band(2),
        audio_visualizer_get_band(4),
        audio_visualizer_get_band(6),
        audio_visualizer_get_band(8),
    };

    for (uint8_t led = led_min; led < led_max; led++) {
        uint8_t x = g_led_config.point[led].x;
        uint8_t y = g_led_config.point[led].y;

        uint8_t row = ((uint16_t)y * VISUALIZER_LEVEL_COUNT) / 64;
        if (row >= VISUALIZER_LEVEL_COUNT) row = VISUALIZER_LEVEL_COUNT - 1;

        uint8_t value = values[row];
        if (value == 0) { rgb_matrix_set_color(led, 0, 0, 0); continue; }

        uint8_t width      = ((uint16_t)value * max_distance) / 210;
        uint8_t peak_value = audio_visualizer_get_peak(row * 2);
        uint8_t peak_w     = ((uint16_t)peak_value * max_distance) / 210;
        uint8_t distance   = (x > center_x) ? (x - center_x) : (center_x - x);

        if (distance <= width) {
            rgb_matrix_set_color(led, vis_scale(pal->level_r[row]), vis_scale(pal->level_g[row]), vis_scale(pal->level_b[row]));
        } else if (peak_w > width && distance <= peak_w && distance + 8 >= peak_w) {
            rgb_matrix_set_color(led, vis_scale(pal->peak_r), vis_scale(pal->peak_g), vis_scale(pal->peak_b));
        } else {
            rgb_matrix_set_color(led, 0, 0, 0);
        }
    }
}

// ---------------------------------------------------------------------------
// Waterdrop mode
// ---------------------------------------------------------------------------

#define WATERDROP_COUNT           6
#define WATERDROP_SPEED           6
#define WATERDROP_BASS_THRESHOLD  187
#define WATERDROP_RETRIGGER_GAP   3

typedef struct {
    uint16_t radius;
    uint8_t  age;
    bool     active;
    uint8_t  color_index;
} waterdrop_t;

static waterdrop_t waterdrops[WATERDROP_COUNT] = {0};
static uint8_t     waterdrop_next_color        = 0;
static uint8_t     waterdrop_cooldown          = 0;

static void render_waterdrop(const visualizer_palette_t *pal,
                             uint8_t led_min, uint8_t led_max) {
    uint8_t bass = audio_visualizer_get_band(0);
    uint8_t b1   = audio_visualizer_get_band(1);
    uint8_t b2   = audio_visualizer_get_band(2);
    if (b1 > bass) bass = b1;
    if (b2 > bass) bass = b2;

    if (waterdrop_cooldown > 0) waterdrop_cooldown--;

    if (bass > WATERDROP_BASS_THRESHOLD && waterdrop_cooldown == 0) {
        for (uint8_t i = 0; i < WATERDROP_COUNT; i++) {
            if (!waterdrops[i].active) {
                waterdrops[i].radius      = 0;
                waterdrops[i].age         = 255;
                waterdrops[i].active      = true;
                waterdrops[i].color_index = waterdrop_next_color;
                waterdrop_next_color      = (waterdrop_next_color + 1) % 5;
                waterdrop_cooldown        = WATERDROP_RETRIGGER_GAP;
                break;
            }
        }
    }

    // Per-half centers for split layout (x 0-224, y ~0-64)
    const uint8_t left_cx  = 56;
    const uint8_t right_cx = 168;
    const uint8_t center_y = 32;

    for (uint8_t led = led_min; led < led_max; led++) {
        uint8_t x = g_led_config.point[led].x;
        uint8_t y = g_led_config.point[led].y;

        uint8_t cx   = (x < 112) ? left_cx : right_cx;
        uint8_t dx   = vis_absdiff(x, cx);
        uint8_t dy   = vis_absdiff(y, center_y);
        uint8_t dist = sqrt16((uint16_t)dx * dx + (uint16_t)dy * dy);

        uint8_t r = 0, g = 0, b = 0;

        for (uint8_t i = 0; i < WATERDROP_COUNT; i++) {
            if (!waterdrops[i].active) continue;

            uint16_t rad    = waterdrops[i].radius;
            uint16_t effect = (rad >= dist) ? (rad - dist) : 0;
            if (effect > 255) effect = 255;

            uint8_t brightness = (uint8_t)(255 - effect);
            if (brightness == 0) continue;

            uint8_t delta = vis_absdiff(dist, (uint8_t)(rad & 0xFF));
            uint8_t color;
            if      (delta < 12) color = 4;
            else if (delta < 28) color = 3;
            else if (delta < 44) color = 2;
            else if (delta < 64) color = 1;
            else                 color = 0;

            uint8_t fade = (delta > 0) ? qsub8(255, delta * 4) : 255;
            uint8_t fb   = scale8(scale8(brightness, fade), waterdrops[i].age);

            r = qadd8(r, scale8(vis_scale(pal->level_r[color]), fb));
            g = qadd8(g, scale8(vis_scale(pal->level_g[color]), fb));
            b = qadd8(b, scale8(vis_scale(pal->level_b[color]), fb));
        }

        rgb_matrix_set_color(led, r, g, b);
    }

    for (uint8_t i = 0; i < WATERDROP_COUNT; i++) {
        if (!waterdrops[i].active) continue;
        waterdrops[i].radius += WATERDROP_SPEED;
        if (waterdrops[i].age > 8) {
            waterdrops[i].age -= 8;
        } else {
            waterdrops[i].active = false;
        }
    }
}

// ---------------------------------------------------------------------------
// Effects
// ---------------------------------------------------------------------------

static bool m57_dynamic_lights(effect_params_t *params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    dynamic_lights_render(led_min, led_max);
    return rgb_matrix_check_finished_leds(led_max);
}

static bool m57_audio_visualizer(effect_params_t *params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    if (!audio_visualizer_is_active()) {
        for (uint8_t i = led_min; i < led_max; i++) rgb_matrix_set_color(i, 0, 0, 0);
        return rgb_matrix_check_finished_leds(led_max);
    }

    uint8_t render_mode             = audio_visualizer_get_render_mode();
    const visualizer_palette_t *pal = audio_visualizer_get_palette();

    switch (render_mode) {
        case 4:  render_waterdrop(pal, led_min, led_max); break;
        case 3:  render_kitt(pal, led_min, led_max);      break;
        case 2:  render_center(pal, led_min, led_max);    break;
        case 1:  render_bars(pal, 1, led_min, led_max);   break;
        default: render_bars(pal, 0, led_min, led_max);   break;
    }

    return rgb_matrix_check_finished_leds(led_max);
}

#endif
