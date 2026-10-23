# All-in-one audio interface

A USB DAC / headphone amplifier with a phantom-powered microphone input.

| | |
|---|---|
| Headphone output | **≥ 2 W into 32 Ω** (≈ 2.3 W at clip), 0.3 W / 9.4 Vrms into 300 Ω, < 0.1 Ω output impedance |
| Gain | High ×5 / Low ×1.5 switch, analog volume pot |
| DAC | AK4493S, 32-bit / 192 kHz |
| Mic input | XLR, THAT1512 preamp, 0–60 dB gain, switchable **+48 V phantom** (IEC 61938 P48) |
| ADC | PCM1820, 113 dB, 32-bit / 192 kHz |
| USB | USB-C, USB Audio Class 2 (XMOS XU316), driverless on macOS / Linux / Windows 10+ / iOS / Android |
| Power | USB-C (5 V 3 A or USB-PD 9–15 V) or 12–15 V DC jack |
| Protection | Turn-on delay, DC-detect and power-fail muting relay; phantom hot-plug clamps |

## How the 2 W @ 32 Ω is met

2 W into 32 Ω needs 8 Vrms and 354 mA peak. Each channel is an OPA1612
driving two paralleled BUF634A buffers (177 mA each, 250 mA rating) inside
the feedback loop, on ±16 V rails from low-noise LDOs fed by a dual SEPIC /
inverting converter. See `docs/design.md` §2 for the full reasoning.

Checked two ways:

- `python3 tools/budget.py`: headroom, current sharing, thermal and
  input-power budget. At 32 Ω it predicts about 1.1 V of spare swing and a
  clean maximum of about 2.37 W.
- `sh sim/run.sh` (needs `ngspice`): transient/AC simulation of one channel
  with behavioural models. Results: 7.99 Vrms = **1.99 W** into 32 Ω at
  rated input, 2.25 W still unclipped, clipping starts between 2.25 and
  2.5 W, and the buffers share current at 187 / 171 mA peak.

The simulation checks swing, gain, stability and current sharing. It uses
idealised models, so its THD figures don't mean anything.

## Repository layout

```
docs/design.md      full circuit description, values, power & protection
hardware/bom.csv    bill of materials with reference designators
tools/budget.py     headroom / thermal / power budget calculator
sim/hp_amp.cir      ngspice model of one headphone-amp channel
sim/run.sh          runs the simulation, prints the key results
firmware/README.md  XMOS sw_usb_audio configuration and board hooks
```

## Status

This is a complete **design** (architecture, part selection, component
values, calculations, simulation). It is not yet a schematic capture or PCB.
Before layout, see "Open items" at the end of `docs/design.md`. The items
marked **(verify)** are datasheet figures that I couldn't confirm offline
(BUF634A dropout, AK4493 full-scale level, PCM1820 strapping).

## Power note

Two channels at 2 W of continuous sine draw about 13 W from the input.
A plain USB-A port (≤ 4.5 W) cannot run it; in that case the firmware
keeps the headphone output muted. A USB-C port that advertises 3 A,
USB-PD, or the DC jack gives full power.
