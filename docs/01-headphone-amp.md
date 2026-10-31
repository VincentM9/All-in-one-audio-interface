# Block 1: Headphone amplifier

Line-level stereo input in, **2 W into 32 Ω** out. The block is powered from a
bench ±16 V supply, so it can be built and tested before any other block
exists.

## What it does

- Gain ×5 (+14 dB): 1.6 Vrms in gives 8.0 Vrms out, which is 2.0 W into 32 Ω.
- Clips at about 2.3 W into 32 Ω. Into 300 Ω it delivers about 9.4 Vrms.
- Output impedance well under 0.1 Ω.

## How it works (one channel; the other is identical)

Input and volume:
```
 IN_L ──C1 10µ NP──┬── RV1 top
                   │   RV1 bottom ── GND
                   │   RV1 wiper ──R1 100Ω──┬──────────── U1A +IN (pin 3)
                                            ├── C2 470p ── GND
                                            └── R2 100k ── GND
```

Amplifier and output:
```
 U1A OUT (pin 1) ──┬── R5 47Ω ── U2 LME49600 ── R7 2.2Ω ──┐
                   └── R6 47Ω ── U3 LME49600 ── R8 2.2Ω ──┴── OUT_L ──┬── headphone jack tip
                                                                     ├── R9 10Ω ── C4 100n ── GND
                                                                     │
 U1A −IN (pin 2) ──┬── R3 2.00k ∥ C3 22p ────────────────────────────┘   (feedback from OUT_L)
                   └── R4 499Ω ── GND                                  gain = 1 + 2000/499 = 5.0
```

- **U1 (OPA1612)** sets the gain and keeps the output accurate.
- **U2 and U3 (LME49600)** are current buffers. Each supplies up to 250 mA,
  so two in parallel cover the 354 mA peak that 2 W into 32 Ω needs.
- **Feedback is taken from OUT_L, after the 2.2 Ω resistors.** That way the
  op-amp corrects for the resistors and the buffers, and the output stays
  accurate.
- **The 2.2 Ω ballast resistors** make the two buffers share the current
  evenly.
- **The 47 Ω isolation resistors** keep the op-amp stable while it drives
  the buffers.
- **The Zobel network** (10 Ω + 100 nF) keeps the output stable into long
  headphone cables.

## Connection list (draw this in Altium)

Pinouts:
- **OPA1612 (SOIC-8):** 1 OUT A, 2 −IN A, 3 +IN A, 4 V−, 5 +IN B, 6 −IN B,
  7 OUT B, 8 V+.
- **LME49600 (TO-263-5):** 1 BW, 2 IN, 3 V− (also the tab), 4 OUT, 5 V+.

Left channel uses U1 side A, U2, U3. Right channel uses U1 side B, U4, U5.

| Net | Connects |
|---|---|
| IN_L | J1 tip, C1 pin 1 |
| IN_R | J1 ring, C11 pin 1 |
| POT_L | C1 pin 2, RV1 section A top |
| POT_R | C11 pin 2, RV1 section B top |
| WIPER_L | RV1 A wiper, R1 pin 1 |
| WIPER_R | RV1 B wiper, R11 pin 1 |
| INP_L | R1 pin 2, C2, R2, U1 pin 3 |
| INP_R | R11 pin 2, C12, R12, U1 pin 5 |
| FB_L | U1 pin 2, Rf (R3), Cf (C3), Rg (R4) |
| FB_R | U1 pin 6, R13, C13, R14 |
| DRV_L | U1 pin 1, R5, R6 |
| DRV_R | U1 pin 7, R15, R16 |
| U2 IN / U3 IN | R5 pin 2 → U2 pin 2; R6 pin 2 → U3 pin 2 |
| U4 IN / U5 IN | R15 pin 2 → U4 pin 2; R16 pin 2 → U5 pin 2 |
| BUF outputs | U2 pin 4 → R7; U3 pin 4 → R8; U4 pin 4 → R17; U5 pin 4 → R18 |
| OUT_L | R7 pin 2, R8 pin 2, R3 (other end), C3 (other end), R9, J2 tip |
| OUT_R | R17 pin 2, R18 pin 2, R13, C13, R19, J2 ring |
| ZOB_L / ZOB_R | R9 → C4 → GND; R19 → C14 → GND |
| +16V | U1 pin 8, pin 5 of U2–U5, J3 pin 1, decoupling caps |
| −16V | U1 pin 4, pin 3 of U2–U5, J3 pin 3, decoupling caps |
| GND | J3 pin 2, J1 sleeve, J2 sleeve, RV1 bottoms, C2, R2, R4, C4, C12, R12, R14, C14 |
| BW pins | U2–U5 pin 1: **leave unconnected** (low-power mode) |

Decoupling:
- At each LME49600: a 10 µF and a 100 nF capacitor on each rail, right at
  pins 5 and 3.
- At U1: 100 nF on each rail.
- At the power connector: 220 µF on each rail.

## Parts list (JLCPCB / LCSC)

Every part is chosen to be orderable from LCSC, which is JLCPCB's parts
library, so JLCPCB can assemble the board. PCBWay can also source all of
them.

- **LCSC numbers in the table** were checked on LCSC's listings. Stock
  changes daily, so re-check before ordering.
- **"Basic" passives** are JLCPCB's preloaded parts, with no setup fee. Pick
  the exact part numbers in JLCPCB's parts search (filter: Basic) or at
  [basicp.art](https://basicp.art/).
- **"Extended"** parts cost about $3 setup per unique part per order.
  Expect roughly 6–8 extended types on this board.

| Ref | Qty | Value | Package | LCSC | JLCPCB class |
|---|---|---|---|---|---|
| U1 | 1 | OPA1612AIDR (dual op-amp) | SOIC-8 | [C94590](https://www.lcsc.com/product-detail/C94590.html) | Extended |
| U2–U5 | 4 | LME49600TS/NOPB (buffer) | TO-263-5 | [C191539](https://www.lcsc.com/product-detail/Audio-Power-OpAmps_Texas-Instruments-LME49600TS-NOPB_C191539.html) | Extended |
| R1, R11 | 2 | 100 Ω 1 % | 0603 | Basic, pick in JLCPCB search | Basic |
| R2, R12 | 2 | 100 kΩ 1 % | 0603 | Basic | Basic |
| R3, R13 | 2 | 2 kΩ 1 % | 0603 | Basic | Basic |
| R4, R14 | 2 | 499 Ω 1 % (or 510 Ω) | 0603 | whichever is Basic | Basic |
| R5, R6, R15, R16 | 4 | 47 Ω 1 % | 0603 | Basic | Basic |
| R7, R8, R17, R18 | 4 | 2.2 Ω 1 % 1 W | 2512 | e.g. [C147074](https://www.lcsc.com/product-detail/Chip-Resistor-Surface-Mount_Ever-Ohms-Tech_C147074.html), any 2.2 Ω 1 W 2512 | Extended |
| R9, R19 | 2 | 10 Ω 1 % | 0805 | Basic | Basic |
| C1, C11 | 2 | 10 µF 25 V **bipolar (NP)** electrolytic | SMD can | search "10uF 25V bipolar" | Extended |
| C2, C12 | 2 | 470 pF C0G | 0603 | Basic | Basic |
| C3, C13 | 2 | 22 pF C0G | 0603 | Basic | Basic |
| C4, C14 + decoupling | 12 | 100 nF X7R 50 V | 0603 | Basic | Basic |
| decoupling | 8 | 10 µF 25 V X7R | 1206 or 1210 | Basic | Basic |
| bulk | 2 | 220 µF 25 V electrolytic | SMD can | Basic | Basic |
| RV1 | 1 | 10 kΩ log (A10K) dual pot | THT | see note | Extended / hand-solder |
| J1 | 1 | 3.5 mm stereo jack (line in) | THT | [C668607](https://www.lcsc.com/product-detail/Audio-Connectors_SHOU-HAN_C668607.html) (PJ-313) or [C16684](https://jlcpcb.com/partdetail/BOOMELE_Boom_Precision_Elec-PJ307C/C16684) (PJ-307C) | Extended |
| J2 | 1 | 6.35 mm stereo jack (headphones) | THT | [C309284](https://jlcpcb.com/partdetail/HOOYA-PJ612/C309284) (PJ-612) | Extended |
| J3 | 1 | 3-pin screw terminal, 5.08 mm | THT | any 3P 5.08 mm terminal | Basic / Extended |

**Changes from the first version of this spec:**
- **0.1 % resistors → 1 %.** In this amp, the gain resistors only set the
  gain. 1 % parts keep the left/right gain within about 0.2 dB, which you
  won't hear. 1 % parts are JLCPCB basic parts. 0.1 % parts are not.
- **Input film cap → 10 µF bipolar electrolytic.** Large film caps are
  through-hole and hard to find on LCSC. A bipolar (non-polarised)
  electrolytic is a normal SMD part. With 10 µF into the 10 kΩ pot, it
  passes everything down to about 1.6 Hz, so it adds no audible
  distortion. Don't use a 10 µF X7R ceramic here: those add measurable
  distortion in the signal path.
- **R4/R14 can be 510 Ω** if 499 Ω isn't a Basic part. The gain becomes
  4.9 instead of 5.0, about 0.2 dB less, and you still get 2 W at about
  1.65 Vrms in.

**Notes:**
- **LME49600 stock:** LCSC showed only about 170 units at roughly $5.26
  each. That's plenty for a few boards (4 per board), but check before
  ordering. Digi-Key and Mouser carry many more if LCSC runs out, and
  PCBWay can source from them.
- **Volume pot:** I couldn't confirm a dual 10 kΩ **log** (A taper) pot on
  LCSC. The ALPS RK097 dual listings there may be linear (B taper), and a
  linear pot makes a poor volume control. Two options:
  1. Search LCSC for "A10K dual potentiometer" and confirm the taper says
     A or log on the datasheet.
  2. Use a 6-pin header on the board, and wire an off-board panel pot to
     it. This is easier to fit to an enclosure later anyway.
- **Through-hole parts** (jacks, pot, terminal) cost extra for JLCPCB to
  assemble. The cheapest route is to let JLCPCB place the SMD parts and
  solder the 4–5 through-hole parts yourself.
- **OPA1612 alternatives** in the same footprint, also on LCSC:
  - OPA1656IDR ([C1849431](https://www.lcsc.com/product-detail/Audio-Power-OpAmps_Texas-Instruments-OPA1656IDR_C1849431.html)), for lower DC offset.
  - The NE5532 family, for low cost.

## Layout notes

- 2-layer is fine for this block. Keep the bottom layer a solid ground pour
  wherever possible.
- **Heat:** each LME49600 dissipates up to about 1 W. Give each TO-263 tab
  (which is −16 V) at least 4 cm² of copper, with thermal vias to a matching
  area on the bottom layer.
- Put the decoupling caps right at the pins, and keep the feedback parts
  (Rf, Cf, Rg) close to the op-amp's pins 2 and 6.
- Use 1 mm+ tracks for OUT_L/OUT_R and the ±16 V rails, and 0.25–0.3 mm for
  everything else.

## Bring-up and test

1. Set the bench supply to ±16 V with a **100 mA current limit**. Power up
   with nothing connected to the input or output. Each rail should draw
   about 35 mA: 4 × 7.3 mA for the buffers plus the op-amp.
2. Measure DC at OUT_L and OUT_R: it should be **under ±10 mV**.
3. Raise the current limit to 500 mA. Connect a **33 Ω, 5 W resistor** to
   each output as a dummy load. Never test with headphones first.
4. Feed a 1 kHz sine at 1.6 Vrms with the volume at maximum. Expect about
   8.0 Vrms at the output (2.0 W). Raise the input slowly and watch on a
   scope: clipping should start at about 8.6–8.8 Vrms (about 2.3 W).
5. Check the LME49600s get warm but stay touchable. Above about 80 °C on
   the case, they need more copper.
6. Only then try headphones, with the volume low.

## Why ±16 V

- 2 W into 32 Ω needs 11.3 V peak at the output.
- The buffers lose about 2.5 V at full current, and the 2.2 Ω resistors
  lose about 1 V more.
- ±16 V leaves about 1 V of margin. ±15 V leaves almost none, so it
  would only just reach 2 W on a good day.
