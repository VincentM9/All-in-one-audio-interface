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

- `AudioHwInit()`
  1. Drive `HP_EN` low (relay open), `DAC_PDN` low.
  2. Read STUSB4500 negotiated contract over I2C. If only 5 V at < 1.5 A is
     available, leave `HP_EN` low and blink the power LED.
  3. Release `DAC_PDN`, write the AK4493 register set: I2S 32-bit,
     sharp-roll-off filter, DSD off, soft-mute on.
- `AudioHwConfig(samFreq, mClk, ...)`
  1. Soft-mute the AK4493, select `MCLK_SEL` for the 44.1k/48k family.
  2. Set the AK4493 speed/DFS bits for `samFreq`, reset its digital core.
  3. The PCM1820 auto-detects the rate from BCLK/LRCK — nothing to do.
  4. Wait ~20 ms, un-mute, then drive `HP_EN` high (the analog protection
     circuit still gates the relay independently).

## GPIO map (proposal)

| Signal | Dir | Notes |
|---|---|---|
| `MCLK_SEL` | out | 0 = 24.576 MHz, 1 = 22.5792 MHz |
| `DAC_PDN` | out | AK4493 power-down |
| `HP_EN` | out, open-drain | ANDed into relay enable |
| `I2C_SCL/SDA` | bidir | AK4493, STUSB4500 |
| `PD_POWER_OK2/3` | in | STUSB4500 contract status |
| `LED_PWR` | out | |
