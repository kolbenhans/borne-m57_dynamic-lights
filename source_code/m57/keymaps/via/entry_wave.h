#pragma once

#include "quantum.h"

void     entry_wave_start(void);
void     entry_wave_trigger(void);
bool     entry_wave_running(void);
uint32_t entry_wave_elapsed(void);
void     entry_wave_stop(void);
void     entry_wave_register_rpc(void);

void raw_hid_receive_kb(uint8_t *data, uint8_t length);
