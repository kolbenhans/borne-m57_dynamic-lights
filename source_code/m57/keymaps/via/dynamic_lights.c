#include QMK_KEYBOARD_H
#include "dynamic_lights.h"

#if defined(RGB_MATRIX_ENABLE)

// ---------------------------------------------------------------------------
// Hardware constants
// ---------------------------------------------------------------------------

#define KEY_ROWS      10
#define KEY_COLS      7
#define KEY_LED_COUNT 58

// ---------------------------------------------------------------------------
// Startup animation
// ---------------------------------------------------------------------------

#define STARTUP_DELAY_MS         800
#define STARTUP_STEP_MS           35
#define STARTUP_SWITCH_STEP_MS    25
#define STARTUP_TAIL              7

// ---------------------------------------------------------------------------
// Cache / blink
// ---------------------------------------------------------------------------

#define BLINK_CHECK_INTERVAL_MS 100
#define CACHE_INVALID_COLOR     0xFF

// ---------------------------------------------------------------------------
// Layer mask helpers
// ---------------------------------------------------------------------------

#define LAYER_ALL     0xFFFFFFFFUL
#define LAYER_MASK(n) (1UL << (n))

#define L_ALL         LAYER_ALL
#define L(n)          LAYER_MASK(n)
#define L_RANGE(a, b) (((1UL << ((b) - (a) + 1)) - 1) << (a))

// Alpha Mods on this board. Used as the custom dynamic-lighting mode.
#define MY_CUSTOM_RGB_MODE 2

// ---------------------------------------------------------------------------
// Color palette
// ---------------------------------------------------------------------------

enum color_id {
    CLR_OFF = 0,
    CLR_RED,
    CLR_LIGHTRED,
    CLR_YELLOW,
    CLR_PINK,
    CLR_GREEN,
    CLR_DARKGREEN,
    CLR_LIGHTGREEN,
    CLR_LEMONGREEN,
    CLR_BLUE,
    CLR_LIGHTBLUE,
    CLR_CYAN,
    CLR_LIGHTCYAN,
    CLR_PURPLE,
    CLR_ROSE,
    CLR_WHITE,
    CLR_ORANGE,
    CLR_LIGHTORANGE,
    CLR_DARKORANGE,
    CLR_GREY,
    CLR_COUNT
};

typedef struct {
    uint8_t r, g, b;
} rgb_color_t;

static const rgb_color_t color_palette[] = {
    [CLR_OFF]         = {   0,   0,   0 },
    [CLR_RED]         = { 255,   0,   0 },
    [CLR_LIGHTRED]    = { 255, 102, 102 },
    [CLR_YELLOW]      = { 255, 210,   0 },
    [CLR_PINK]        = { 255,   0, 128 },
    [CLR_GREEN]       = {   0, 255,   0 },
    [CLR_DARKGREEN]   = {   0,  51,  25 },
    [CLR_LIGHTGREEN]  = {  51, 255, 153 },
    [CLR_LEMONGREEN]  = { 153, 255,  51 },
    [CLR_BLUE]        = {   0,  80, 255 },
    [CLR_LIGHTBLUE]   = { 153, 204, 255 },
    [CLR_CYAN]        = {   0, 255, 255 },
    [CLR_LIGHTCYAN]   = { 204, 255, 255 },
    [CLR_PURPLE]      = {  76,   0, 153 },
    [CLR_ROSE]        = { 153,   0,  76 },
    [CLR_WHITE]       = { 255, 255, 255 },
    [CLR_ORANGE]      = { 255, 100,   0 },
    [CLR_LIGHTORANGE] = { 255, 204, 153 },
    [CLR_DARKORANGE]  = {  63,  25,   0 },
    [CLR_GREY]        = {  24,  24,  24 },
};

// ---------------------------------------------------------------------------
// Per-keycode color rules
// ---------------------------------------------------------------------------

typedef struct {
    uint16_t keycode;
    uint8_t  color_id;
    uint32_t layer_mask;
} key_color_rule_t;

static const key_color_rule_t key_color_rules[] = {
    // --- Always-visible action keys ---
    { KC_ENT,    CLR_CYAN,      L_ALL },
    { KC_SPC,    CLR_YELLOW,    L_ALL },
    { KC_BSPC,   CLR_PINK,      L_ALL },
    { KC_DELETE, CLR_BLUE,      L_ALL },
    { KC_DEL,    CLR_BLUE,      L_ALL },

    // --- Arrow keys (layers 1-4) ---
    { KC_LEFT,   CLR_RED,       L_RANGE(1, 4) },
    { KC_DOWN,   CLR_BLUE,      L_RANGE(1, 4) },
    { KC_UP,     CLR_GREEN,     L_RANGE(1, 4) },
    { KC_RGHT,   CLR_YELLOW,    L_RANGE(1, 4) },

    // --- Modifier keys (layers 1-4) ---
    { KC_LSFT,   CLR_ORANGE,    L_RANGE(1, 4) },
    { KC_RSFT,   CLR_ORANGE,    L_RANGE(1, 4) },
    { KC_LCTL,   CLR_PINK,      L_RANGE(1, 4) },
    { KC_RCTL,   CLR_PINK,      L_RANGE(1, 4) },
    { KC_LGUI,   CLR_BLUE,      L_RANGE(1, 4) },
    { KC_RGUI,   CLR_BLUE,      L_RANGE(1, 4) },
    { KC_LALT,   CLR_PURPLE,    L_RANGE(1, 4) },
    { KC_RALT,   CLR_PURPLE,    L_RANGE(1, 4) },
    { KC_TAB,    CLR_LIGHTCYAN, L_RANGE(1, 4) },

    // --- Tab cycling (layer 1 only) ---
    { C(S(KC_TAB)), CLR_PURPLE, L(1) },
    { C(KC_TAB),    CLR_ORANGE, L(1) },

    // --- Numpad ---
    { KC_P0,   CLR_BLUE,   L_ALL },
    { KC_P1,   CLR_BLUE,   L_ALL },
    { KC_P2,   CLR_BLUE,   L_ALL },
    { KC_P3,   CLR_BLUE,   L_ALL },
    { KC_P4,   CLR_BLUE,   L_ALL },
    { KC_P5,   CLR_ORANGE, L_ALL },
    { KC_P6,   CLR_BLUE,   L_ALL },
    { KC_P7,   CLR_BLUE,   L_ALL },
    { KC_P8,   CLR_BLUE,   L_ALL },
    { KC_P9,   CLR_BLUE,   L_ALL },
    { KC_PPLS, CLR_GREEN,  L_ALL },
    { KC_PAST, CLR_GREEN,  L_ALL },
    { KC_PMNS, CLR_RED,    L_ALL },
    { KC_PSLS, CLR_RED,    L_ALL },
};

// ---------------------------------------------------------------------------
// LED mapping
// ---------------------------------------------------------------------------

static const uint8_t matrix_to_led[KEY_ROWS][KEY_COLS] = {
    { 0,      1,      2,      3,      4,      5,      NO_LED },
    { 6,      7,      8,      9,      10,     11,     12     },
    { 13,     14,     15,     16,     17,     18,     19     },
    { 20,     21,     22,     23,     24,     25,     NO_LED },
    { NO_LED, NO_LED, NO_LED, 26,     27,     28,     NO_LED },

    { NO_LED, 29,     30,     31,     32,     33,     34     },
    { 35,     36,     37,     38,     39,     40,     41     },
    { 42,     43,     44,     45,     46,     47,     48     },
    { NO_LED, 49,     50,     51,     52,     53,     54     },
    { NO_LED, 55,     56,     57,     NO_LED, NO_LED, NO_LED }
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

static struct {
    uint32_t delay_timer;
    uint32_t anim_timer;
    bool     done;
    bool     from_mode_switch;
} startup = {0};

static struct {
    uint8_t       color_ids[KEY_LED_COUNT];
    layer_state_t layer_state;
    uint8_t       rgb_value;
    uint8_t       led_state_raw;
    bool          valid;
    uint32_t      check_timer;
} cache = {0};

static uint8_t last_rgb_mode = 0;

// ---------------------------------------------------------------------------
// Color helpers
// ---------------------------------------------------------------------------

static void clear_all(void) {
    for (uint8_t i = 0; i < KEY_LED_COUNT; i++) {
        rgb_matrix_set_color(i, 0, 0, 0);
    }
}

static uint8_t slow_blink(uint8_t color_a, uint8_t color_b) {
    return (timer_read32() / 800) % 2 ? color_a : color_b;
}

static void apply_color(uint8_t led, uint8_t color_id) {
    if (led == NO_LED) return;

    if (color_id == CLR_OFF || color_id >= CLR_COUNT) {
        rgb_matrix_set_color(led, 0, 0, 0);
        return;
    }

    uint8_t v = rgb_matrix_config.hsv.v;
    rgb_color_t c = color_palette[color_id];

    rgb_matrix_set_color(
        led,
        (uint16_t)c.r * v / 255,
        (uint16_t)c.g * v / 255,
        (uint16_t)c.b * v / 255
    );
}

// ---------------------------------------------------------------------------
// Keycode → color resolution
// ---------------------------------------------------------------------------

static uint8_t color_for_mod_tap(uint8_t base_key) {
    switch (base_key) {
        case KC_A:
        case KC_SCLN:
            return CLR_YELLOW;

        case KC_S:
        case KC_L:
            return CLR_GREEN;

        case KC_D:
        case KC_K:
            return CLR_BLUE;

        case KC_F:
        case KC_J:
            return CLR_RED;

        default:
            return CLR_OFF;
    }
}

static bool is_layer_switch_keycode(uint16_t keycode) {
    static const uint16_t layer_keycodes[] = {
        MO(1), MO(2), MO(3), MO(4),
        TG(1), TG(2), TG(3), TG(4),
        TO(1), TO(2), TO(3), TO(4),
        OSL(1), OSL(2), OSL(3), OSL(4),
        TT(1), TT(2), TT(3), TT(4),
        TD(0), TD(1), TD(2), TD(3),
    };

    for (uint8_t i = 0; i < ARRAY_SIZE(layer_keycodes); i++) {
        if (layer_keycodes[i] == keycode) return true;
    }

    return false;
}

static uint8_t color_for_keycode(uint16_t keycode, uint8_t layer) {
    if ((keycode >= QK_MOD_TAP && keycode <= QK_MOD_TAP_MAX) ||
        (keycode >= QK_LAYER_TAP && keycode <= QK_LAYER_TAP_MAX)) {
        uint8_t base = keycode & 0xFF;
        uint8_t c = color_for_mod_tap(base);

        if (c != CLR_OFF) return c;

        keycode = base;
    }

    if (is_layer_switch_keycode(keycode)) return CLR_GREY;

    if (keycode == EE_CLR)    return slow_blink(CLR_RED,    CLR_DARKORANGE);
    if (keycode == QK_BOOT)   return slow_blink(CLR_ORANGE, CLR_DARKORANGE);
    if (keycode == QK_REBOOT) return slow_blink(CLR_GREEN,  CLR_DARKGREEN);

    if (keycode == KC_CAPS) {
        return host_keyboard_led_state().caps_lock ? CLR_WHITE : CLR_OFF;
    }

    if (keycode == KC_NUM) {
        return host_keyboard_led_state().num_lock ? CLR_WHITE : CLR_OFF;
    }

    for (uint8_t i = 0; i < ARRAY_SIZE(key_color_rules); i++) {
        const key_color_rule_t *r = &key_color_rules[i];

        if (r->keycode == keycode &&
            (r->layer_mask == LAYER_ALL || (r->layer_mask & LAYER_MASK(layer)))) {
            return r->color_id;
        }
    }

    return CLR_OFF;
}

// ---------------------------------------------------------------------------
// Cache management
// ---------------------------------------------------------------------------

static void cache_invalidate(void) {
    cache.valid = false;
}

static void cache_rebuild(void) {
    uint8_t layer = get_highest_layer(layer_state);

    clear_all();

    for (uint8_t i = 0; i < KEY_LED_COUNT; i++) {
        cache.color_ids[i] = CACHE_INVALID_COLOR;
    }

    for (uint8_t row = 0; row < KEY_ROWS; row++) {
        for (uint8_t col = 0; col < KEY_COLS; col++) {
            uint8_t led = matrix_to_led[row][col];
            if (led == NO_LED) continue;

            uint16_t kc  = dynamic_keymap_get_keycode(layer, row, col);
            uint8_t  cid = color_for_keycode(kc, layer);

            cache.color_ids[led] = cid;
            apply_color(led, cid);
        }
    }

    cache.layer_state   = layer_state;
    cache.rgb_value     = rgb_matrix_config.hsv.v;
    cache.led_state_raw = host_keyboard_led_state().raw;
    cache.valid         = true;
    cache.check_timer   = timer_read32();
}

static void cache_flush(void) {
    for (uint8_t led = 0; led < KEY_LED_COUNT; led++) {
        if (cache.color_ids[led] != CACHE_INVALID_COLOR) {
            apply_color(led, cache.color_ids[led]);
        }
    }
}

static void cache_tick_blink(void) {
    if (timer_elapsed32(cache.check_timer) < BLINK_CHECK_INTERVAL_MS) return;

    cache.check_timer = timer_read32();

    uint8_t layer = get_highest_layer(layer_state);

    for (uint8_t row = 0; row < KEY_ROWS; row++) {
        for (uint8_t col = 0; col < KEY_COLS; col++) {
            uint8_t led = matrix_to_led[row][col];
            if (led == NO_LED) continue;

            uint16_t kc  = dynamic_keymap_get_keycode(layer, row, col);
            uint8_t  cid = color_for_keycode(kc, layer);

            if (cache.color_ids[led] != cid) {
                cache.color_ids[led] = cid;
            }
        }
    }
}

static void render_lighting(void) {
    bool stale =
        !cache.valid ||
        cache.layer_state   != layer_state ||
        cache.rgb_value     != rgb_matrix_config.hsv.v ||
        cache.led_state_raw != host_keyboard_led_state().raw;

    if (stale) {
        cache_rebuild();
        return;
    }

    cache_tick_blink();
    cache_flush();
}

// ---------------------------------------------------------------------------
// Startup comet
// ---------------------------------------------------------------------------

static void startup_tick(void) {
    uint16_t step_ms = startup.from_mode_switch
        ? STARTUP_SWITCH_STEP_MS
        : STARTUP_STEP_MS;

    uint32_t elapsed = timer_elapsed32(startup.anim_timer);
    uint8_t head = elapsed / step_ms;

    if (head > KEY_LED_COUNT + STARTUP_TAIL) {
        startup.done = true;
        startup.from_mode_switch = false;
        clear_all();
        cache_invalidate();
        return;
    }

    clear_all();

    for (uint8_t tail = 0; tail < STARTUP_TAIL; tail++) {
        int16_t pos = (int16_t)head - tail;

        if (pos < 0 || pos >= KEY_LED_COUNT) continue;

        uint8_t led = (uint8_t)pos;

        uint8_t hue = (uint8_t)(elapsed / 8) + (uint8_t)(pos * 10);
        uint8_t value = 255 - (uint8_t)((uint16_t)tail * 120 / STARTUP_TAIL);

        RGB rgb = hsv_to_rgb((HSV){ hue, 255, value });
        rgb_matrix_set_color(led, rgb.r, rgb.g, rgb.b);
    }
}

// ---------------------------------------------------------------------------
// QMK hooks
// ---------------------------------------------------------------------------

void keyboard_post_init_user(void) {
    startup.delay_timer = timer_read32();
}

bool rgb_matrix_indicators_advanced_user(uint8_t led_min, uint8_t led_max) {
    (void)led_min;
    (void)led_max;

    uint8_t current_mode = rgb_matrix_get_mode();

    if (current_mode != MY_CUSTOM_RGB_MODE) {
        last_rgb_mode = current_mode;
        return false;
    }

    if (last_rgb_mode != MY_CUSTOM_RGB_MODE && last_rgb_mode != 0) {
        startup = (typeof(startup)){
            .delay_timer      = timer_read32(),
            .from_mode_switch = true,
        };
        cache_invalidate();
    }

    last_rgb_mode = current_mode;

    if (!startup.done) {
        uint16_t delay = startup.from_mode_switch ? 0 : STARTUP_DELAY_MS;

        if (timer_elapsed32(startup.delay_timer) < delay) {
            return false;
        }

        if (startup.anim_timer == 0) {
            startup.anim_timer = timer_read32();
        }

        startup_tick();
        return false;
    }

    render_lighting();
    return false;
}

#endif // RGB_MATRIX_ENABLE