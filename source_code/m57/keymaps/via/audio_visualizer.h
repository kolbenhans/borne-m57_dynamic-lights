#pragma once

#include "quantum.h"

#define VISUALIZER_BAND_COUNT  12
#define VISUALIZER_LEVEL_COUNT  5

typedef struct {
    uint8_t peak_r, peak_g, peak_b;
    uint8_t level_r[VISUALIZER_LEVEL_COUNT];
    uint8_t level_g[VISUALIZER_LEVEL_COUNT];
    uint8_t level_b[VISUALIZER_LEVEL_COUNT];
    uint8_t underglow_r, underglow_g, underglow_b;
} visualizer_palette_t;

uint8_t audio_visualizer_is_active(void);
uint8_t audio_visualizer_get_band(uint8_t index);
uint8_t audio_visualizer_get_peak(uint8_t index);

void raw_hid_receive_kb(uint8_t *data, uint8_t length);
void audio_visualizer_register_rpc(void);
void audio_visualizer_sync_to_slave(void);

void    audio_visualizer_toggle_underglow(void);
uint8_t audio_visualizer_underglow_enabled(void);

uint8_t audio_visualizer_get_mode(void);
void    audio_visualizer_next_mode(void);

uint8_t audio_visualizer_get_render_mode(void);
void    audio_visualizer_next_render_mode(void);

const visualizer_palette_t *audio_visualizer_get_palette(void);
