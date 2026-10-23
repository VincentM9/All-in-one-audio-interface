# All-in-one audio interface

A USB DAC / headphone amplifier with a phantom-powered microphone input.

| | |
|---|---|
| Headphone output | **≥ 2 W into 32 Ω** (≈ 2.3 W at clip), 0.3 W / 9.4 Vrms into 300 Ω, < 0.1 Ω output impedance |
| Gain | High ×5 / Low ×1.5 switch, analog volume pot |
| DAC | PCM1794A, 24-bit / 192 kHz, OPA1612 I/V stage |
| Mic input | XLR, THAT1512 preamp, 0–60 dB gain, switchable **+48 V phantom** (IEC 61938 P48) |
| ADC | CS5361, 114 dB, 24-bit / 192 kHz |
| USB | USB-C, USB Audio Class 2 (XMOS XU316), driverless on macOS / Linux / Windows 10+ / iOS / Android |
| Power | USB-C (5 V up to 3 A, or USB-PD 9–15 V) or 12–15 V DC jack |
| Protection | Turn-on delay, DC-detect and power-fail muting relay; phantom hot-plug clamps |

## How the 2 W @ 32 Ω is met

2 W into 32 Ω needs 8 Vrms and 354 mA peak. Each channel is an OPA1612
driving two paralleled LME49600 buffers (177 mA each, 250 mA rating) inside
the feedback loop. The rails are ±16 V from low-noise LDOs, fed by LT3757
SEPIC and Cuk converters. See `docs/design.md` §2 for the reasoning.

Checked two ways:

- `python3 tools/budget.py`: headroom, current sharing, thermal and
  input-power budget. At 32 Ω it predicts about 1.1 V of spare swing and a
  clean maximum of about 2.37 W.
- `sh sim/run.sh` (needs `ngspice`): transient/AC simulation of one channel
  with behavioural models. It gives 7.99 Vrms = **1.99 W** into 32 Ω at rated
  input, stays unclipped at 2.25 W, and starts clipping between 2.25 and
  2.5 W. The buffers share current at 187 / 171 mA peak.

The simulation checks swing, gain, stability and current sharing. It uses
idealised models, so its THD figures don't mean anything.

## Schematic (KiCad 7, imports into Altium)

`hardware/schematic/kicad/aio.kicad_pro` is the full schematic: a root sheet
plus five sheets (power, USB/XMOS/clocks, DAC, headphone amp, mic/ADC),
355 parts. A PDF is in `hardware/schematic/aio-schematic.pdf`.

**Opening it in Altium Designer (24 or newer):** File → Import Wizard →
KiCad Design Files, then select `hardware/schematic/kicad/aio.kicad_pro`.
Each sheet becomes a `.SchDoc`. The symbols are embedded in the files, so
nothing else is needed. Footprint names are KiCad's, so map them to your
Altium footprint libraries afterwards.

The schematic is generated from `hardware/schematic/design.py`. Edit that
file and run:

```
python3 hardware/schematic/design.py   # writes the KiCad files + hardware/bom.csv
python3 hardware/schematic/check.py    # KiCad's netlist vs. the intended one
```

`check.py` exports the netlist with `kicad-cli` and compares every net
against `design.py`. It also flags single-pin nets, shorted outputs and
unpowered power pins. KiCad 7's command line has no electrical rules check,
so this stands in for one.

Parts are connected by net labels at each pin rather than drawn wires: global
labels between sheets, local labels within a sheet.

**Before layout:** the XMOS XU316 symbol has the right function names, but its
**pin numbers are placeholders**, because I couldn't get the XMOS pin table.
Swap it for XMOS's official library part. The other open items are at the end
of `docs/design.md`.

## Repository layout

```
docs/design.md               full circuit description, values, power & protection
hardware/bom.csv             bill of materials, generated from the schematic
hardware/schematic/          schematic source (design.py), generator, checker, PDF
hardware/schematic/kicad/    KiCad 7 project (import this into Altium)
tools/budget.py              headroom / thermal / power budget calculator
sim/hp_amp.cir               ngspice model of one headphone-amp channel
sim/run.sh                   runs the simulation, prints the key results
firmware/README.md           XMOS sw_usb_audio configuration and board hooks
```

## Power note

Two channels at 2 W of continuous sine draw about 16 W from the input. Music
averages far less, because of its 10–15 dB crest factor.

- A plain USB-A port (≤ 4.5 W) can't run it, so the firmware keeps the
  headphone output muted.
- A 5 V USB-C port (1.5–3 A) handles music at full level.
- USB-PD (9 V or more) or a 12–15 V / 2 A DC jack handles a continuous 2 W
  sine as well.
