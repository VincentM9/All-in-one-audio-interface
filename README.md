# All-in-one audio interface

A USB DAC / headphone amplifier with a phantom-powered microphone input,
built one block at a time. Each block is designed, drawn in Altium, built and
tested on its own before the next one starts.

## Goal

- Headphone output: **at least 2 W into 32 Ω**
- USB DAC for playback
- XLR microphone input with 48 V phantom power for condenser mics

## Blocks

| # | Block | Status |
|---|---|---|
| 1 | [Headphone amplifier](docs/01-headphone-amp.md): line in → 2 W @ 32 Ω, runs from a bench ±16 V supply | **designing** |
| 2 | Power supply: DC jack → ±16 V for the amp | not started |
| 3 | USB DAC: USB → line out | not started |
| 4 | Mic preamp with 48 V phantom | not started |
| 5 | Put it together: one board, one enclosure | not started |

The earlier all-in-one attempt (full schematic, generated PCB) is in git
history before this commit, if any part of it is ever useful again.
