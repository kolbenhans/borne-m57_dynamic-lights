#include "audio_visualizer.h"
#ifdef SPLIT_KEYBOARD
#    include "transactions.h"
#endif
#include <string.h>

#ifdef RAW_ENABLE

#define VISUALIZER_SYNC_SIZE ((VISUALIZER_BAND_COUNT * 2) + 3)

static uint8_t visualizer_bands[VISUALIZER_BAND_COUNT] = {0};
static uint8_t visualizer_peaks[VISUALIZER_BAND_COUNT] = {0};
static bool    visualizer_active                        = false;
static bool    visualizer_underglow_enabled             = false;
static uint8_t visualizer_mode                          = 0;
static uint8_t visualizer_render_mode                   = 0;

static visualizer_palette_t palette_uploaded = {
    .peak_r = 255, .peak_g = 255, .peak_b = 255,
    .level_r = {255,   0,   0, 255, 255},
    .level_g = {  0, 255,   0, 255,   0},
    .level_b = {  0,   0, 255,   0, 255},
    .underglow_r = 255, .underglow_g = 0, .underglow_b = 0,
};

static uint8_t mix_u8(uint8_t a, uint8_t b, uint8_t amount) {
    return a + (((int16_t)b - a) * amount) / 255;
}

static void set_uploaded_level(uint8_t level, uint8_t r, uint8_t g, uint8_t b) {
    palette_uploaded.level_r[level] = r;
    palette_uploaded.level_g[level] = g;
    palette_uploaded.level_b[level] = b;
}

void audio_visualizer_next_mode(void) {
    visualizer_mode = (visualizer_mode + 1) % 5;
}

void audio_visualizer_next_render_mode(void) {
    visualizer_render_mode = (visualizer_render_mode + 1) % 5;
}

uint8_t audio_visualizer_get_mode(void)        { return visualizer_mode; }
uint8_t audio_visualizer_get_render_mode(void) { return visualizer_render_mode; }

void    audio_visualizer_toggle_underglow(void)    { visualizer_underglow_enabled = !visualizer_underglow_enabled; }
uint8_t audio_visualizer_underglow_enabled(void)   { return visualizer_underglow_enabled ? 1 : 0; }

uint8_t audio_visualizer_is_active(void)           { return visualizer_active ? 1 : 0; }
uint8_t audio_visualizer_get_band(uint8_t index)   { return index < VISUALIZER_BAND_COUNT ? visualizer_bands[index] : 0; }
uint8_t audio_visualizer_get_peak(uint8_t index)   { return index < VISUALIZER_BAND_COUNT ? visualizer_peaks[index] : 0; }

static const visualizer_palette_t palette_winamp = {
    .peak_r = 255, .peak_g = 255, .peak_b = 255,
    .level_r = {  0, 160, 255, 255, 255},
    .level_g = {255, 255, 220,  80,   0},
    .level_b = {  0,   0,   0,   0,   0},
    .underglow_r = 255, .underglow_g = 90, .underglow_b = 0,
};

static const visualizer_palette_t palette_purple = {
    .peak_r = 255, .peak_g = 60, .peak_b = 0,
    .level_r = { 76, 180,   0,   0, 255},
    .level_g = {  0,   0,   0, 255, 255},
    .level_b = {153, 255, 255, 255, 255},
    .underglow_r = 76, .underglow_g = 0, .underglow_b = 153,
};

static const visualizer_palette_t palette_ice = {
    .peak_r = 255, .peak_g = 255, .peak_b = 255,
    .level_r = {  0,   0,   0, 120, 255},
    .level_g = { 80, 180, 255, 255, 255},
    .level_b = {255, 255, 255, 255, 255},
    .underglow_r = 0, .underglow_g = 80, .underglow_b = 255,
};

static const visualizer_palette_t palette_fire = {
    .peak_r = 255, .peak_g = 255, .peak_b = 255,
    .level_r = {120, 255, 255, 255, 255},
    .level_g = {  0,   0,  80, 180, 255},
    .level_b = {  0,   0,   0,   0,   0},
    .underglow_r = 255, .underglow_g = 0, .underglow_b = 0,
};

const visualizer_palette_t *audio_visualizer_get_palette(void) {
    switch (visualizer_mode) {
        default:
        case 0: return &palette_winamp;
        case 1: return &palette_purple;
        case 2: return &palette_ice;
        case 3: return &palette_fire;
        case 4: return &palette_uploaded;
    }
}

#ifdef SPLIT_KEYBOARD

static uint8_t visualizer_sync_data[VISUALIZER_SYNC_SIZE];

static void visualizer_sync_handler(uint8_t in_size, const void *in_data,
                                    uint8_t out_size, void *out_data) {
    (void)out_size; (void)out_data;
    if (in_size != VISUALIZER_SYNC_SIZE || in_data == NULL) return;

    const uint8_t *d = (const uint8_t *)in_data;
    memcpy(visualizer_bands, d, VISUALIZER_BAND_COUNT);
    memcpy(visualizer_peaks, d + VISUALIZER_BAND_COUNT, VISUALIZER_BAND_COUNT);
    visualizer_underglow_enabled = d[VISUALIZER_BAND_COUNT * 2] != 0;
    visualizer_mode               = d[VISUALIZER_BAND_COUNT * 2 + 1];
    visualizer_render_mode        = d[VISUALIZER_BAND_COUNT * 2 + 2];
    visualizer_active             = true;
}

static void palette_sync_handler(uint8_t in_size, const void *in_data,
                                 uint8_t out_size, void *out_data) {
    (void)out_size; (void)out_data;
    if (in_size != sizeof(visualizer_palette_t) || in_data == NULL) return;
    memcpy(&palette_uploaded, in_data, sizeof(visualizer_palette_t));
}

void audio_visualizer_register_rpc(void) {
    transaction_register_rpc(USER_SYNC_VISUALIZER, visualizer_sync_handler);
    transaction_register_rpc(USER_SYNC_PALETTE,    palette_sync_handler);
}

void audio_visualizer_sync_to_slave(void) {
    if (!is_keyboard_master()) return;
    memcpy(&visualizer_sync_data[0], visualizer_bands, VISUALIZER_BAND_COUNT);
    memcpy(&visualizer_sync_data[VISUALIZER_BAND_COUNT], visualizer_peaks, VISUALIZER_BAND_COUNT);
    visualizer_sync_data[VISUALIZER_BAND_COUNT * 2]     = visualizer_underglow_enabled ? 1 : 0;
    visualizer_sync_data[VISUALIZER_BAND_COUNT * 2 + 1] = visualizer_mode;
    visualizer_sync_data[VISUALIZER_BAND_COUNT * 2 + 2] = visualizer_render_mode;
    transaction_rpc_send(USER_SYNC_VISUALIZER, VISUALIZER_SYNC_SIZE, visualizer_sync_data);
}

void audio_visualizer_sync_palette_to_slave(void) {
    if (!is_keyboard_master()) return;
    transaction_rpc_send(USER_SYNC_PALETTE, sizeof(visualizer_palette_t), &palette_uploaded);
}

#else
void audio_visualizer_register_rpc(void)         {}
void audio_visualizer_sync_to_slave(void)        {}
void audio_visualizer_sync_palette_to_slave(void) {}
#endif

void raw_hid_receive_kb(uint8_t *data, uint8_t length) {
    if (length < 2 || data[0] != 0x02) return;

    static uint32_t sync_timer = 0;

    switch (data[1]) {
        case 0xA1: {
            if (length < 26) break;
            for (uint8_t i = 0; i < VISUALIZER_BAND_COUNT; i++) {
                visualizer_bands[i] = data[i + 2];
                visualizer_peaks[i] = data[i + 2 + VISUALIZER_BAND_COUNT];
            }
            visualizer_active = true;
            if (timer_elapsed32(sync_timer) > 50) {
                sync_timer = timer_read32();
                audio_visualizer_sync_to_slave();
            }
            break;
        }
        case 0xA2: {
            if (length < 18) break;
            uint8_t r0 = data[12], g0 = data[13], b0 = data[14];
            uint8_t r1 = data[9],  g1 = data[10], b1 = data[11];
            uint8_t r2 = data[3],  g2 = data[4],  b2 = data[5];
            set_uploaded_level(0, r0, g0, b0);
            set_uploaded_level(1, mix_u8(r0, r1, 128), mix_u8(g0, g1, 128), mix_u8(b0, b1, 128));
            set_uploaded_level(2, r1, g1, b1);
            set_uploaded_level(3, mix_u8(r1, r2, 128), mix_u8(g1, g2, 128), mix_u8(b1, b2, 128));
            set_uploaded_level(4, r2, g2, b2);
            palette_uploaded.underglow_r = r0;
            palette_uploaded.underglow_g = g0;
            palette_uploaded.underglow_b = b0;
            palette_uploaded.peak_r = palette_uploaded.peak_g = palette_uploaded.peak_b = 255;
            audio_visualizer_sync_palette_to_slave();
            break;
        }
    }
}

#else

uint8_t audio_visualizer_is_active(void)         { return 0; }
uint8_t audio_visualizer_get_band(uint8_t index) { (void)index; return 0; }
uint8_t audio_visualizer_get_peak(uint8_t index) { (void)index; return 0; }
void    audio_visualizer_toggle_underglow(void)   {}
uint8_t audio_visualizer_underglow_enabled(void)  { return 0; }
uint8_t audio_visualizer_get_mode(void)           { return 0; }
void    audio_visualizer_next_mode(void)          {}
const visualizer_palette_t *audio_visualizer_get_palette(void) { return NULL; }
void    audio_visualizer_next_render_mode(void)   {}
uint8_t audio_visualizer_get_render_mode(void)    { return 0; }
void    audio_visualizer_register_rpc(void)       {}
void    audio_visualizer_sync_to_slave(void)      {}
void    raw_hid_receive_kb(uint8_t *data, uint8_t length) { (void)data; (void)length; }

#endif
