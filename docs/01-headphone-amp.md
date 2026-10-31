# Block 1: Balanced headphone amplifier

Line-level stereo input. Three outputs:

| Output | Connector | Max power into 32 Ω | Max power into 300 Ω |
|---|---|---|---|
| Balanced | 4.4 mm Pentaconn **and** 4-pin XLR | **~8.9 W** (16.9 Vrms) | ~1.2 W (19 Vrms) |
| Single-ended | 6.35 mm | ~2.5 W (8.9 Vrms) | ~0.3 W (9.5 Vrms) |

Powered from a bench ±16 V supply, so it can be built and tested on its own.
Output impedance is well under 0.1 Ω on every output.

## How it works

Each channel has two identical amplifier halves:

- **Hot side (+):** the original design. U1 (OPA1612) with gain ×5 drives
  three LME49600 buffers in parallel → OUT+.
- **Cold side (−):** U2 (OPA1612) wired as a **unity-gain inverter** of
  OUT+. It drives its own three LME49600s → OUT−. OUT− is always the
  mirror image of OUT+.

The headphone driver connects between OUT+ and OUT−. That doubles the
voltage across it compared with single-ended (OUT+ to ground), which gives
up to 4× the power. The single-ended jack uses only the hot sides.

```
                                ┌─ 3× LME49600 ── OUT_L+ ──┬─ 6.35 mm tip
 IN_L ── volume ── U1A ×5 ──────┤                          ├─ 4.4 mm tip, XLR pin 1
                                │                          │
                                │   U2A ×(−1) ◄────────────┘ (input taken from OUT_L+)
                                │       │
                                │       └─ 3× LME49600 ── OUT_L− ── 4.4 mm ring 1, XLR pin 2
```

**Why three buffers per side:** in balanced mode each side effectively sees
half the headphone impedance (16 Ω for 32 Ω headphones). At full power each
side delivers 0.75 A peak, so three 250 mA buffers share it at 249 mA each.

**Why the cold side copies OUT+ rather than the input:** taking its input
from the low-impedance OUT+ node means the volume pot only sees one load,
and the two halves can never drift apart in gain by more than the two 1 %
resistors allow (about 0.2 dB).

## Circuit, one channel (left shown; right = same refs + 40)

Input and volume (feeds the hot side):
```
 IN_L ──C1 10µ NP──┬── RV1 top
                   │   RV1 bottom ── GND
                   │   RV1 wiper ──R1 100Ω──┬──────────── U1A +IN (pin 3)
                                            ├── C2 470p ── GND
                                            └── R2 100k ── GND
```

Hot side (gain ×5):
```
 U1A OUT (pin 1) ──┬── R5 47Ω ── U3 LME49600 ── R8  2.2Ω ──┐
                   ├── R6 47Ω ── U4 LME49600 ── R9  2.2Ω ──┼── OUT_L+ ──┬── R11 10Ω ── C4 100n ── GND
                   └── R7 47Ω ── U5 LME49600 ── R10 2.2Ω ──┘            │
 U1A −IN (pin 2) ──┬── R3 2k ∥ C3 22p ─────────────────────────────────┘   (feedback from OUT_L+)
                   └── R4 499Ω ── GND                                gain = 1 + 2000/499 = 5.0
```

Cold side (gain ×−1, input from OUT_L+):
```
 OUT_L+ ── R22 2k ──┬── U2A −IN (pin 2)
                    └── R23 2k ∥ C21 22p ──────────────────────────────┐   (feedback from OUT_L−)
 U2A +IN (pin 3) ── R21 1k ── GND                                     │
 U2A OUT (pin 1) ──┬── R24 47Ω ── U6 LME49600 ── R27 2.2Ω ──┐          │
                   ├── R25 47Ω ── U7 LME49600 ── R28 2.2Ω ──┼── OUT_L− ┴──┬── R30 10Ω ── C22 100n ── GND
                   └── R26 47Ω ── U8 LME49600 ── R29 2.2Ω ──┘              │
```

- **R21 (1 kΩ)** equals R22 ∥ R23. That balances the op-amp's input bias
  currents, which keeps OUT_L− DC offset low.
- **C21:** the cold side runs at a lower gain than the hot side (noise gain
  2 instead of 5), so it has a little less stability margin. If you see
  ringing or oscillation on OUT_L− with a scope, raise C21 (and C61) from
  22 pF to 47 pF.

## Connection list (draw this in Altium)

Pinouts:
- **OPA1612 (SOIC-8):** 1 OUT A, 2 −IN A, 3 +IN A, 4 V−, 5 +IN B, 6 −IN B,
  7 OUT B, 8 V+.
- **LME49600 (TO-263-5):** 1 BW, 2 IN, 3 V− (also the tab), 4 OUT, 5 V+.

Op-amp sides:
- **U1:** side A = left hot (L+), side B = right hot (R+).
- **U2:** side A = left cold (L−), side B = right cold (R−).

Buffers:

| Side | Buffers | 47 Ω input resistors | 2.2 Ω ballast resistors | Zobel |
|---|---|---|---|---|
| L+ | U3, U4, U5 | R5, R6, R7 | R8, R9, R10 | R11 + C4 |
| L− | U6, U7, U8 | R24, R25, R26 | R27, R28, R29 | R30 + C22 |
| R+ | U9, U10, U11 | R45, R46, R47 | R48, R49, R50 | R51 + C44 |
| R− | U12, U13, U14 | R64, R65, R66 | R67, R68, R69 | R70 + C62 |

Nets:

| Net | Connects |
|---|---|
| IN_L / IN_R | J1 tip / ring, C1 / C41 pin 1 |
| POT_L / POT_R | C1 / C41 pin 2, RV1 top of section A / B |
| WIPER_L / WIPER_R | RV1 wiper A / B, R1 / R41 |
| INP_L | R1, C2, R2, U1 pin 3 |
| INP_R | R41, C42, R42, U1 pin 5 |
| FB_L+ | U1 pin 2, R3, C3, R4 |
| FB_R+ | U1 pin 6, R43, C43, R44 |
| DRV_L+ | U1 pin 1, R5, R6, R7 |
| DRV_R+ | U1 pin 7, R45, R46, R47 |
| OUT_L+ | R8, R9, R10, R3, C3, R11, R22, J2 tip, J3 tip, J4 pin 1 |
| OUT_R+ | R48, R49, R50, R43, C43, R51, R62, J2 ring, J3 ring 2, J4 pin 3 |
| BIAS_L− / BIAS_R− | U2 pin 3 / pin 5, R21 / R61 (other end to GND) |
| FB_L− | U2 pin 2, R22, R23, C21 |
| FB_R− | U2 pin 6, R62, R63, C61 |
| DRV_L− | U2 pin 1, R24, R25, R26 |
| DRV_R− | U2 pin 7, R64, R65, R66 |
| OUT_L− | R27, R28, R29, R23, C21, R30, J3 ring 1, J4 pin 2 |
| OUT_R− | R67, R68, R69, R63, C61, R70, J3 ring 3, J4 pin 4 |
| Buffer IN / OUT | each 47 Ω → its buffer's pin 2; each buffer's pin 4 → its 2.2 Ω |
| +16V | U1 pin 8, U2 pin 8, pin 5 of U3–U14, J5 pin 1, decoupling |
| −16V | U1 pin 4, U2 pin 4, pin 3 of U3–U14, J5 pin 3, decoupling |
| GND | J5 pin 2, J1 sleeve, J2 sleeve, J3 sleeve, J4 shell/ground contact, RV1 bottoms, R2, R4, R21, C2, C4, C22 and the right-channel equivalents |
| BW pins | pin 1 of U3–U14: **leave unconnected** (low-power mode) |

Output connectors:

| Connector | Contacts |
|---|---|
| J2: 6.35 mm stereo (single-ended) | tip OUT_L+, ring OUT_R+, sleeve GND |
| J3: 4.4 mm Pentaconn (balanced) | tip OUT_L+, ring 1 OUT_L−, ring 2 OUT_R+, ring 3 OUT_R−, sleeve GND |
| J4: 4-pin XLR female (balanced) | 1 OUT_L+, 2 OUT_L−, 3 OUT_R+, 4 OUT_R−, ground contact GND |

Decoupling:
- At each LME49600: a 10 µF and a 100 nF capacitor on each rail, right at
  pins 5 and 3.
- At U1 and U2: 100 nF on each rail.
- At the power terminal: 470 µF on each rail.

## Parts list (JLCPCB / LCSC)

The rules from before still apply:
- LCSC numbers were checked at the time of writing. Re-check stock before
  ordering.
- For the plain resistors and caps, pick JLCPCB **Basic** parts in their
  parts search or at [basicp.art](https://basicp.art/).
- Extended parts cost about $3 setup per unique part per order.

| Ref | Qty | Value | Package | LCSC | Class |
|---|---|---|---|---|---|
| U1, U2 | 2 | OPA1612AIDR | SOIC-8 | [C94590](https://www.lcsc.com/product-detail/C94590.html) | Extended |
| U3–U14 | 12 | LME49600TS/NOPB | TO-263-5 | [C191539](https://www.lcsc.com/product-detail/Audio-Power-OpAmps_Texas-Instruments-LME49600TS-NOPB_C191539.html) | Extended |
| R1, R41 | 2 | 100 Ω 1 % | 0603 | Basic | Basic |
| R2, R42 | 2 | 100 kΩ 1 % | 0603 | Basic | Basic |
| R3, R43, R22, R23, R62, R63 | 6 | 2 kΩ 1 % | 0603 | Basic | Basic |
| R4, R44 | 2 | 499 Ω 1 % (or 510 Ω) | 0603 | whichever is Basic | Basic |
| R21, R61 | 2 | 1 kΩ 1 % | 0603 | Basic | Basic |
| 47 Ω input resistors | 12 | 47 Ω 1 % | 0603 | Basic | Basic |
| 2.2 Ω ballast resistors | 12 | 2.2 Ω 1 % 1 W | 2512 | e.g. [C147074](https://www.lcsc.com/product-detail/Chip-Resistor-Surface-Mount_Ever-Ohms-Tech_C147074.html), any 2.2 Ω 1 W 2512 | Extended |
| R11, R30, R51, R70 | 4 | 10 Ω 1 % | 0805 | Basic | Basic |
| C1, C41 | 2 | 10 µF 25 V bipolar (NP) electrolytic | SMD can | search "10uF 25V bipolar" | Extended |
| C2, C42 | 2 | 470 pF C0G | 0603 | Basic | Basic |
| C3, C43, C21, C61 | 4 | 22 pF C0G | 0603 | Basic | Basic |
| Zobel + decoupling | 32 | 100 nF X7R 50 V | 0603 | Basic | Basic |
| decoupling | 24 | 10 µF 25 V X7R | 1206 / 1210 | Basic | Basic |
| bulk | 2 | 470 µF 25 V electrolytic | SMD or radial | Basic / Extended | — |
| RV1 | 1 | 10 kΩ log (A10K) dual pot | THT | see note | hand-solder |
| J1 | 1 | 3.5 mm stereo jack (line in) | THT | [C668607](https://www.lcsc.com/product-detail/Audio-Connectors_SHOU-HAN_C668607.html) or [C16684](https://jlcpcb.com/partdetail/BOOMELE_Boom_Precision_Elec-PJ307C/C16684) | Extended |
| J2 | 1 | 6.35 mm stereo jack | THT | [C309284](https://jlcpcb.com/partdetail/HOOYA-PJ612/C309284) | Extended |
| J3 | 1 | 4.4 mm Pentaconn 5-pole jack | THT | **not on LCSC**, see note | hand-solder |
| J4 | 1 | 4-pin XLR female, PCB (Neutrik NC4FAH-0) | THT | [C368492](https://jlcpcb.com/partdetail/Neutrik-NC4FAH0/C368492) | Extended |
| J5 | 1 | 3-pin screw terminal, 5.08 mm | THT | any 3P 5.08 mm | — |

Notes:
- **LME49600 stock:** LCSC showed only about 170 units, at about $5.26
  each. At 12 per board that's about 14 boards, about $63 of buffers each.
  Digi-Key and Mouser hold more if LCSC runs low.
- **4.4 mm jack:** I couldn't find a Pentaconn jack on LCSC. Two options:
  1. Order the genuine NBP1-44-J (Nippon DICS) from a distributor and
     solder it yourself.
  2. Fit a 5-pin header and wire a panel-mount 4.4 mm jack to it.
- **Volume pot:** confirm the LCSC listing is **A (log) taper**. Otherwise
  use a 6-pin header and an off-board panel pot.
- **Through-hole parts** (jacks, pot, terminal): solder them yourself to
  avoid JLCPCB's through-hole assembly fee.

## Heat and power supply

This is now a serious power amplifier.

| Condition | Current per rail | Heat on the board |
|---|---|---|
| Idle | ~0.10 A | ~3 W (12 buffers × 0.23 W, plus the op-amps) |
| Music at loud levels | ~0.2–0.4 A | ~5–8 W |
| Full-power sine, both channels balanced into 32 Ω | ~1.05 A | ~16 W worst case (≈ 1.1 W per buffer) |

- **Bench supply:** ±16 V, able to deliver **at least 1.2 A per rail**.
- **Copper:** give each LME49600 tab **at least 6 cm²** of copper on its
  pad, with thermal vias to the same area on the other side. Twelve of these
  need a lot of board area, so plan the board around them: about 75 cm² of
  copper for the buffers alone.
- **Tab voltage:** the tabs are −16 V. Never pour their copper as ground,
  and never let them touch a grounded case.
- **Enclosure:** the finished amp needs ventilation. A 4-layer board
  (Sig / GND / −16 V copper / Sig) helps spread the heat.

## Layout notes

- Keep each side's three buffers, their 47 Ω and 2.2 Ω resistors, and their
  decoupling together as one cluster.
- Mirror the + and − sides of each channel so their layouts match.
- Keep the feedback parts close to the op-amp pins: R3/C3/R4 for the hot
  side, R22/R23/C21 for the cold side.
- Use 1.5 mm+ tracks for OUT± and the ±16 V rails, and 0.25–0.3 mm for
  signals.
- Run each output pair (OUT_L+ / OUT_L−) side by side to the jacks.

## Bring-up and test

1. **First power-up.** Set the bench supply to ±16 V with a 200 mA current
   limit. Connect nothing to the inputs or outputs. Each rail should draw
   about 100 mA.
2. **DC offsets.** Measure DC at OUT_L+, OUT_L−, OUT_R+ and OUT_R− to
   ground. Each should be under ±10 mV, and L+ minus L− (and R+ minus R−)
   under ±20 mV.
3. **Cold side stability.** Feed a 1 kHz sine at 0.5 Vrms. With a scope,
   confirm OUT_L− is a clean inverted copy of OUT_L+. Repeat for the right
   channel. If either shows fuzz or ringing, raise C21 / C61 to 47 pF.
4. **Single-ended load test.** Raise the current limit to 1.5 A. Connect a
   33 Ω, 10 W resistor from OUT_L+ to GND. At 1.6 Vrms in, with the volume
   at max, expect about 8 Vrms (2 W).
5. **Balanced load test.** Move the 33 Ω, 10 W resistor to OUT_L+ → OUT_L−
   (**not** to ground). At 1.6 Vrms in, expect about 16 Vrms across it (8 W).
   Clipping should start around 16.9 Vrms. Repeat for the right channel.
6. **Heat soak.** Run at half power for 10 minutes. The buffers get hot but
   should stay below about 90 °C on the case. If they run hotter, add
   copper or a heatsink.
7. Only then try headphones, with the volume **low**. Balanced is 6 dB
   louder than single-ended at the same volume setting.

## Safety rules for the balanced outputs

- **Never use a balanced-to-single-ended adapter that ties L− or R− to
  ground.** It shorts the cold-side buffers into ground at full power. Use
  the 6.35 mm jack for single-ended headphones.
- **Don't connect headphones to the 4.4 mm and the XLR at the same time.**
  They share the same amplifiers. It won't break anything, but each pair
  gets half the current when the amp is driven hard.
- **Mind the volume on balanced.** It can reach 8.9 W, enough to damage most
  headphones. Start low.

## Why ±16 V

- At 8 W balanced, each side needs 11.3 V peak.
- The buffers lose about 2.5 V at full current, and the ballast resistors
  plus the buffers' output resistance lose about 1.5 V more.
- That adds up to about 15.3 V, so ±16 V leaves about 0.7 V of margin at
  8 W. Clipping starts at about 8.9 W.
- The OPA1612 and LME49600 are 36 V parts (±18 V), so ±16 V also keeps a
  2 V safety margin to their maximum rating.
