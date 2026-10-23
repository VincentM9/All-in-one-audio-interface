# Firmware

The USB side runs XMOS's open-source USB Audio reference firmware
([`sw_usb_audio`](https://github.com/xmos/sw_usb_audio), built on `lib_xua`).
Start from the `app_usb_aud_xk_316_mc` application (same XU316 device) and
make a new build config for this board.

## Build configuration

| Define | Value | Why |
|---|---|---|
| `XUA_NUM_USB_CHAN_OUT` | 2 | stereo playback |
| `XUA_NUM_USB_CHAN_IN` | 2 | mic duplicated to L/R (set 1 for mono) |
| `I2S_CHANS_DAC` / `I2S_CHANS_ADC` | 2 / 2 | |
| `XUA_PCM_FORMAT` | `XUA_PCM_FORMAT_I2S` | |
| `CODEC_MASTER` | 0 | XMOS is I2S master |
| `MAX_FREQ` / `MIN_FREQ` | 192000 / 44100 | |
| `MCLK_441` / `MCLK_48` | 22579200 / 24576000 | Y3 / Y2 |
| `XUA_SPDIF_TX_EN`, `XUA_MIDI_EN`, `XUA_ADAT_*` | 0 | not fitted |
| `XUA_MIXER` | 1 (optional) | low-latency direct monitoring of the mic |

## Board hooks (`audiohw.xc`)

Both converters are hardware-controlled (no codec I2C), so the hooks only
drive GPIOs. Names match the schematic (`hardware/schematic`, sheet "USB-C,
PD sink, XMOS, clocks").

- `AudioHwInit()`
  1. Drive `HP_EN` low (relay open), `DAC_MUTE` high, `DAC_RST_N` and
     `ADC_RST_N` low.
  2. Read the STUSB4500's negotiated contract over I2C (or sample `PD_POK2/3`).
     If only 5 V at < 1.5 A is available, leave `HP_EN` low and blink `LED_ERR`.
  3. Release `DAC_RST_N` and `ADC_RST_N`.
- `AudioHwConfig(samFreq, mClk, ...)`
  1. Set `DAC_MUTE` high and `HP_EN` low. Set `MCLK_SEL` (0 = 24.576 MHz for
     48 kHz rates, 1 = 22.5792 MHz for 44.1 kHz rates).
  2. Set the CS5361 speed mode: `ADC_M1:ADC_M0` = 00 for ≤ 48 kHz, 01 for
     88.2/96 kHz, 10 for 176.4/192 kHz. Pulse `ADC_RST_N`.
  3. The PCM1794A follows the new clocks. Pulse `DAC_RST_N` if needed.
  4. Wait about 20 ms, set `DAC_MUTE` low, then `HP_EN` high. The analog
     protection circuit still gates the relay independently.

## GPIO map

Pin numbers are assigned in the `.xn` file once the XU316 symbol has been
replaced with the official XMOS part (see `docs/design.md` §6).

| Signal | Dir | Notes |
|---|---|---|
| `MCLK_IN` | in | from the MCLK mux via 22 Ω |
| `I2S_BCLK`, `I2S_LRCK`, `I2S_DOUT` | out | to PCM1794A (and BCLK/LRCK to CS5361), via 33 Ω |
| `I2S_DIN` | in | from CS5361 SDOUT |
| `MCLK_SEL` | out | 0 = 24.576 MHz, 1 = 22.5792 MHz |
| `DAC_RST_N`, `DAC_MUTE` | out | PCM1794A reset (pulled low) and mute (pulled high) |
| `ADC_RST_N`, `ADC_M0`, `ADC_M1` | out | CS5361 reset and speed mode (pulled low) |
| `HP_EN` | out | low forces the headphone relay open (via BAT54) |
| `I2C_SCL/SDA` | bidir | STUSB4500 |
| `PD_POK2/3` | in | STUSB4500 contract status |
| `LED_PWR`, `LED_ERR` | out | green / red LEDs |
