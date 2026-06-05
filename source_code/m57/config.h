#pragma once

// -----------------------------------------------------------------------------
// MCU / clock
// -----------------------------------------------------------------------------

#undef STM32_HSECLK
#define STM32_HSECLK 16000000

#define NEW_401_BL

// -----------------------------------------------------------------------------
// Vial / dynamic keymap
// -----------------------------------------------------------------------------

#define TAPPING_TOGGLE 2

#define DYNAMIC_KEYMAP_LAYER_COUNT 10
#define DYNAMIC_KEYMAP_MACRO_COUNT 15

#define WEAR_LEVELING_LOGICAL_SIZE 4096
#define WEAR_LEVELING_BACKING_SIZE (WEAR_LEVELING_LOGICAL_SIZE * 2)
#define DYNAMIC_KEYMAP_EEPROM_MAX_ADDR 4095

// -----------------------------------------------------------------------------
// Matrix
// Matrix size is defined in keyboard.json.
// Do not reintroduce MATRIX_ROWS or MATRIX_COLS here.
// -----------------------------------------------------------------------------

#define MATRIX_ROW_PINS { C8, C7, B2, A6, A5 }
#define MATRIX_COL_PINS { B13, B14, B15, C6, C9, A8, C12 }

#define MATRIX_ROW_PINS_RIGHT { A1, B7, C5, B0, B1 }
#define MATRIX_COL_PINS_RIGHT { B8, C10, C8, C7, C6, B15, B14 }

/*
 * Alternative half assignment kept for hardware reference.
 *
 * #define MATRIX_ROW_PINS { A1, B7, C5, B0, B1 }
 * #define MATRIX_COL_PINS { B8, C9, C8, C7, C6, B15, B14 }
 * #define MATRIX_ROW_PINS_RIGHT { C8, C7, B2, A6, A5 }
 * #define MATRIX_COL_PINS_RIGHT { B13, B14, B15, C6, C9, A8, C12 }
 */

#define DIODE_DIRECTION COL2ROW
#define DEBOUNCE 5

// -----------------------------------------------------------------------------
// Encoder
// -----------------------------------------------------------------------------

#define ENCODER_MAP_KEY_DELAY 10

// -----------------------------------------------------------------------------
// Split transport
// -----------------------------------------------------------------------------

#define SERIAL_USART_FULL_DUPLEX
#define SERIAL_USART_TX_PIN A9
#define SERIAL_USART_RX_PIN A10

// 0: 460800 baud
// 1: 230400 baud (default)
// 2: 115200 baud
// 3: 57600 baud
// 4: 38400 baud
// 5: 19200 baud
#define SELECT_SOFT_SERIAL_SPEED 5

#define SERIAL_USART_DRIVER SD1
#define SERIAL_USART_TX_PAL_MODE 7
#define SERIAL_USART_RX_PAL_MODE 7
#define SERIAL_USART_TIMEOUT 20

#define MASTER_RIGHT

#define SPLIT_HAND_PIN C1
#define SPLIT_HAND_PIN_LOW_IS_LEFT

#define SPLIT_USB_DETECT
#define SPLIT_USB_TIMEOUT 2000
#define SPLIT_USB_TIMEOUT_POLL 10

#define SPLIT_MODS_ENABLE

#define SPLIT_WATCHDOG_ENABLE
#define SPLIT_WATCHDOG_TIMEOUT 3000

// -----------------------------------------------------------------------------
// RGB matrix / WS2812
// -----------------------------------------------------------------------------

#define WS2812_PWM_DRIVER PWMD3
#define WS2812_PWM_CHANNEL 2
#define WS2812_PWM_PAL_MODE 2
#define WS2812_DMA_STREAM STM32_DMA1_STREAM2
#define WS2812_DMA_CHANNEL 5

#define RGB_MATRIX_SLEEP

// -----------------------------------------------------------------------------
// USB
// -----------------------------------------------------------------------------

#define USB_POLLING_INTERVAL_MS 1