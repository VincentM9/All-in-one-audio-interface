# Design description

Reference designators match the schematic (`hardware/schematic/`) and the
generated BOM (`hardware/bom.csv`): 1xx power, 2xx USB/XMOS/clocks, 3xx DAC,
4xx headphone amp and protection, 5xx microphone input and ADC. Values marked
**(verify)** come from datasheet figures I couldn't confirm against the
current datasheet revision; check them before layout.

## 1. Block diagram

```
                 USB-C (data + power)                 DC jack 12-15 V
                        |                                   |
          +-------------+-------------+                     |
          |                           |                     |
   USB 2.0 HS data            STUSB4500 PD sink             |
          |                   + Q201 load switch            |
          v                           |                     |
   +-------------+                    +---- SS54 OR (D101,D102)
   | XMOS XU316  |                                |  VIN 5-15 V
   | USB Audio 2 |          +---------------------+---------------------+
   | 2 out/2 in  |          |                     |                     |
   +--+-----+----+     LT3757 SEPIC         LT3757 Cuk            LT3757 boost
      | I2S  | I2S        +18.4 V              -18.4 V               +50 V
      |      |              |                     |                    |
      |      |        TPS7A4701 +16 V       TPS7A3301 -16 V      cap multiplier
      |      |        TPS7A4701 +5 VA             |              +48.6 V (P48)
      |      |              +------ +/-16 V analog rails ----+         |
      v      ^                                               |         |
  PCM1794A  CS5361 <-- OPA1612 ADC driver <-- THAT1512 <--+--+--- XLR mic in
   DAC       ADC        (SE -> diff)          mic pre     |   (6.81k feed,
      |                                        (0-60 dB)  |    switchable)
      v                                                   |
  OPA1612 I/V (x2 per ch) -> OPA1612 diff stage           |
      |                                                   |
  Volume pot (dual log 10k) -> gain switch (x1.5 / x5)    |
      |                                                   |
  OPA1612 + 2x LME49600 per channel (in-loop) ------------+
      |
  DC-protect + turn-on-delay relay -> 6.35 mm + 3.5 mm jacks
```

The digital-side supplies are omitted from the diagram: TPS62130 bucks from
VIN to +3V3D and +0V9 (XMOS core), TLV75518 to +1V8 (USB PHY), and an LT3042
from +5VA to a clean +3V3A for the oscillators and converters.

## 2. Headphone amplifier (per channel), the 2 W @ 32 Ω stage

**Requirement:** 2 W into 32 Ω = 8.0 Vrms = 11.3 V peak at 354 mA peak.

**Topology:** OPA1612 (U401A/B) non-inverting amp driving two LME49600
buffers in parallel *inside* the op-amp's feedback loop (U402/U403 left,
U404/U405 right). The feedback is taken from the common output node after
the ballast resistors, so loop gain corrects the ballast resistors, buffer
output resistance and buffer offsets.

| Part | Value | Purpose |
|---|---|---|
| Input R / C | 100 Ω / 470 pF C0G | RF filter at amp input |
| Bias R | 100 kΩ | DC path to ground if the pot wiper lifts |
| Feedback R | 2.00 kΩ 0.1 % | |
| Gain R (always in) | 4.02 kΩ 0.1 % | gain 1.50 ("Low", for IEMs) |
| Gain R (switched) | 576 Ω 0.1 % via SW401 | in parallel → 503 Ω, gain 4.97 ("High") |
| Feedback C | 22 pF C0G | loop phase margin |
| Isolation R | 47 Ω, one per buffer input | isolates op-amp from buffer input capacitance |
| Ballast R | 2.2 Ω 1 W, one per buffer output | current sharing |
| Zobel | 10 Ω + 100 nF per output | stability into cable capacitance |
| LME49600 BW pin | open | low-power mode, ~7.3 mA Iq (datasheet) |
| Rails | ±16 V, 10 µF X7R at each buffer, 220 µF bulk | |

The gain switch only ever *adds* a resistor in parallel, so the gain leg is
never left open while switching.

**Why two buffers:** one LME49600 is rated 250 mA continuous. 354 mA peak
needs two, so each carries 177 mA (71 % of its rating). Mismatched buffer
offsets (assumed ≤100 mV worst case) circulate ≤23 mA through 2 × 2.2 Ω.

**Headroom (`tools/budget.py`):** I assumed a 2.5 V buffer dropout at 180 mA
and 4 Ω buffer output resistance **(verify)**. On ±16 V the buffer needs to
swing 12.4 V and can swing 13.5 V. The predicted clean maximum is about
2.37 W into 32 Ω. The ngspice simulation (`sim/hp_amp.cir`) shows 2.25 W
unclipped, with clipping starting between 2.25 and 2.5 W.

| Load | Max clean output (predicted) | Limited by |
|---|---|---|
| 16 Ω | 2.0 W (5.7 Vrms) | 2 × 250 mA buffer current |
| 32 Ω | 2.37 W (8.7 Vrms) | voltage |
| 64 Ω | 1.30 W (9.1 Vrms) | voltage |
| 300 Ω | 0.30 W (9.45 Vrms) | voltage |
| 600 Ω | 0.15 W (9.5 Vrms) | voltage |

**Thermal:** worst-case class-AB dissipation is 1.62 W per channel. That is
about 1.04 W per buffer including its 7.3 mA Iq. With each TO-263 tab on
≥4 cm² of 2 oz copper (θJA ≈ 40 °C/W **(verify)**), Tj ≈ 82 °C at 40 °C
ambient. Keep the four buffers spread out.

**Output impedance:** well under 0.1 Ω at 1 kHz, because the ballast
resistors are inside the loop. The relay contacts (~50 mΩ) dominate.

## 3. Headphone protection

The relay K401 (Omron G6K-2F-Y, 3 V coil, normally-open contacts) connects
the jacks only while node `RDRV` is high:

- **Turn-on delay:** RDRV charges through 220 kΩ into 10 µF, so the relay
  closes about 2–3 s after power-up.
- **Power-fail:** U406A (LM393) pulls RDRV low as soon as the +18V4
  switcher rail drops below about 17 V. That happens before the ±16 V LDO
  outputs move, so the relay opens before the amp rails collapse.
- **Negative rail lost:** U406B pulls RDRV low if −16 V collapses.
- **DC detect:** both outputs are summed through 47 kΩ resistors into about
  23 µF (two 47 µF back-to-back), giving ~0.3 Hz. Q402 trips on positive DC
  and Q403 on negative DC beyond about ±0.6 V.
- **Firmware mute:** XMOS `HP_EN` low pulls RDRV low through a BAT54, for
  sample-rate changes and when the power source is too weak.
- Coil driver: 2N7002 with 1N4148W flyback diode. The coil runs from
  +3V3D, so it doesn't load the analog LDOs.

## 4. DAC and I/V stage

- **U301 PCM1794A** (hardware control, 132 dB-class DAC). +5VA on VCC1 and
  VCC2L/R, +3V3A on VDD. IREF 16 kΩ **(verify)**. MUTE is pulled high
  (muted) until the XMOS drives it low, and RST is pulled low until the XMOS
  releases it.
- Format straps FMT0/FMT1: each has a fitted pull-down and a DNP pull-up.
  Set them for 24-bit I2S per the datasheet's format table **(verify)**.
- Output current is 7.8 mA p-p per pin, centred near −6.2 mA.
- **I/V:** OPA1612 per leg with 750 Ω ∥ 2.2 nF (≈96 kHz pole). That gives
  5.85 V p-p per leg, sitting at about +4.65 V DC.
- **Differential stage:** OPA1612 with 2.00 k / 1.00 k (gain 0.5) and 1.5 nF
  across each 1 k (≈106 kHz). Output is ≈2.07 Vrms single-ended, and 0.1 %
  resistors reject the 4.65 V common mode. The inputs are deliberately
  crossed (I/V of IOUT− to the + input), so the output is not inverted.
- A 4.7 µF film cap into the 10 kΩ log pot removes any residual DC
  (fc ≈ 3.4 Hz).

Result: 2.07 Vrms × 4.97 ≈ 10.3 Vrms demand at digital full scale, so in
High gain the amp clips about 1.5 dB before 0 dBFS. That is intentional: 2 W
is reachable at about −2 dBFS with the pot at max. Low gain (×1.5) gives
3.1 Vrms maximum with a much lower noise floor for IEMs.

## 5. Microphone input with 48 V phantom power

**Connector J501:** Neutrik NCJ6FI-S combo. XLR pin 1 goes to signal
ground, the shell to chassis. The TRS part is unused in this revision.

**Phantom supply (IEC 61938 P48):**
- U103 LT3757 boost from VIN to 50 V. A 100 V FET and diode, then an LC
  filter.
- Q104 capacitance multiplier, with a 4.7 kΩ / 100 µF base filter. Output is
  about 49.3 V open-circuit and 48.6 V at 15 mA, inside the 48 ± 4 V window.
- SW501 (panel switch) feeds P48 through 47 Ω with 47 µF to ground. A red LED
  on P48 shows when phantom is on and also bleeds P48 down after switch-off.

**Feed network:**
- 6.81 kΩ 0.1 % matched pair, whose matching sets CMRR with phantom on.
- 47 µF 63 V DC-blocking caps, + side toward the mic.
- 2.21 kΩ to ground after the caps, for discharge and preamp input bias.
- 10 Ω series, then 1N4004 clamps from each input to the ±16 V rails
  (THAT's recommendation), plus SMBJ18CA TVS on the rails. This survives a
  hot-plugged or shorted mic with phantom on.
- RFI: ferrite beads in pins 2/3, 100 pF to ground on each leg, 470 pF across.

**Preamp U501 THAT1512** on ±16 V, filtered separately from the amp rails
(10 Ω + 220 µF per rail).
- Gain G = 0.5 + 5 kΩ / RG, with RG = 5.1 Ω + RV501 (10 kΩ reverse-log pot).
  That gives 0 dB at full pot resistance and ≈60 dB at minimum.
- The gain leg is DC-blocked by 4700 µF / 6.3 V, so the output DC doesn't
  shift with gain and the pot doesn't scratch.

**ADC driver U502 OPA1612:** a unity follower (+ leg) and a unity inverter
(− leg). 1 Vrms at the THAT1512 output becomes 2 Vrms differential, which is
0 dBFS on the CS5361 (full scale = 1.13 × VA = 5.65 V p-p differential at
5 V). Full-scale mic input is therefore +2.2 dBu at 0 dB gain and about
−58 dBu at 60 dB.

**ADC input network:** 22 µF bipolar electrolytic coupling, 100 kΩ bias to
VQ, 49.9 Ω series, 2.7 nF C0G across the inputs, and BAT54S clamps to
+5VA/GND. The driver runs on ±16 V, so the clamps protect the 5 V ADC.

**U503 CS5361** (114 dB): slave mode, I2S, high-pass filter on, MDIV = 0.
XMOS GPIOs drive M0/M1 for the speed mode (single/double/quad) at each
sample rate. The unused right channel is tied to VQ. OVFL drives the red
CLIP LED.

## 6. Digital / USB

- **U203 XMOS XU316-1024-QF60B:** USB 2.0 HS device running XMOS
  `sw_usb_audio` (UAC2, 44.1–192 kHz, 24/32-bit, 2 out / 2 in). Class
  compliant on macOS, Linux, iOS/Android and Windows 10 1703+.
  **Its schematic symbol has function names only. The pin numbers are
  placeholders (`?nn`).** I couldn't get the XMOS pin table here, so replace
  the symbol with XMOS's official library part before layout and assign the
  I2S/GPIO functions to ports in the `.xn` file. Datasheet values found so
  far: USB_DM = 28, USB_DP = 29, USB_VDD33 = 30, USB_VDD18 = 31, core
  0.855–0.945 V.
- **U204** W25Q32JV QSPI flash for firmware. **X201** 24 MHz oscillator for
  the XMOS.
- **Audio master clocks:** X202 24.576 MHz and X203 22.5792 MHz
  low-phase-noise oscillators on +3V3A, selected by U205 (74LVC1G3157,
  `MCLK_SEL` = 0 gives the 48 kHz family). The mux output fans out through
  22 Ω to the XMOS, DAC and ADC.
- XMOS is I2S master (BCLK/LRCK through 33 Ω) for both converters.
- I2C (XMOS ↔ STUSB4500), 2.2 kΩ pull-ups.
- USB-C J201: USB2 D+/D− only. CC is handled by the STUSB4500. ESD
  protection is a TPD4E05U06 on D+/D−/CC1/CC2. The shield goes to chassis
  through 1 MΩ ∥ 4.7 nF.
- J202 debug header: the pinout is a placeholder, so match it to your XTAG
  adapter.

## 7. Power

Full 2 W continuous sine into both channels needs ≈16.4 W at the input
(`tools/budget.py`). Real music has a 10–15 dB crest factor, so it averages
far less.

| Source | Available | Result |
|---|---|---|
| USB 2/3 port, 5 V 0.5–0.9 A | 2.5–4.5 W | **not supported**: XMOS keeps the relay open and blinks the LED |
| USB-C 5 V 1.5 A | 7.5 W | works; music peaks reach 2 W, not a continuous sine |
| USB-C 5 V 3 A | 15 W | works; music peaks reach 2 W, continuous sine just short |
| USB-PD 9/12/15 V | ≥ 27 W | full 2 W continuous sine |
| DC jack 12–15 V ≥ 2 A | ≥ 24 W | full 2 W continuous sine (recommended for desktop use) |

- **U202 STUSB4500** stand-alone PD sink. NVM is programmed PDO3 = 15 V/1.5 A,
  PDO2 = 12 V/1.5 A, PDO1 = 5 V. VBUS_EN_SNK switches Q201 (AO3407A,
  Vgs ±20 V) to pass VBUS once a contract exists. POWER_OK2/3 tell the XMOS
  what was negotiated. VSYS is grounded, as the datasheet requires when
  unused. DISCH and VBUS_VS_DISCH have current-limiting resistors.
- **D101/D102** SS54 Schottky OR between USB and the DC jack. SMBJ16CA TVS
  on VIN.
- **U101 LT3757 SEPIC → +18.4 V**, **U102 LT3757 Cuk → −18.4 V**, both with
  coupled 22 µH inductors, 60 V FETs, 300 kHz, and 30 mΩ sense resistors
  (3.7 A limit). FBX regulates to +1.6 V / −0.8 V (datasheet). Each output
  has a 1 µH + 22 µF + 100 µF post-filter. They work over the whole 5–15 V
  input range; switch stress is Vin + Vout ≤ 33.4 V.
- **U104 TPS7A4701 → +16.0 V** (ANY-OUT: 6.4 + 6.4 + 1.6 + 0.2 grounded),
  **U105 TPS7A3301 → −16.1 V** (127 k / 10 k), and **U106 TPS7A4701 → +5.0 V**
  analog (3.2 + 0.4). The ±16 V LDOs dissipate about 0.7 W each at full
  power, so put their thermal pads on copper pour.
- **U107 LT3042 → +3V3A** (clean 3.3 V for oscillators, mux and converters).
- **U108/U109 TPS62130 → +3V3D / +0V9**, then **U110 TLV75518 → +1V8**.
- Grounding: one ground plane, split only by placement (digital/USB corner,
  switchers in the opposite corner behind the analog area, amp next to the
  jacks). Chassis is bonded at the USB shield and the XLR shell.

## 8. Expected performance (targets, not measurements)

| Parameter | Target |
|---|---|
| Headphone output, 32 Ω | ≥ 2.0 W (≈ 2.3 W at clip) |
| Headphone output, 300 Ω | ≈ 0.3 W / 9.4 Vrms |
| Output impedance | < 0.1 Ω (amp) |
| DAC → HP dynamic range, low gain | > 115 dB(A) |
| Mic EIN at 60 dB | ≈ −128 dBu (THAT1512 ~1 nV/√Hz) |
| Mic input gain | 0 to 60 dB |
| ADC dynamic range | ≈ 114 dB (CS5361) |
| Phantom | 48.6 V, ≥ 10 mA |
| Sample rates | 44.1–192 kHz, 24/32-bit, both directions |

## 9. Open items before layout

1. Replace the XU316 placeholder symbol with XMOS's official library part,
   and assign ports in the `.xn` file.
2. Confirm LME49600 dropout at 180 mA / 85 °C. If it is over 3 V, raise the
   rails to ±17 V (LME49600 abs max ±22 V; TPS7A47/33 are fine).
3. Confirm PCM1794A FMT0/FMT1 for 24-bit I2S and the IREF resistor value.
4. Confirm CS5361 FILT+/VQ capacitor values, the input RC, and the MCLK
   ratio in slave mode.
5. Confirm the TPS62130 FSW pin sense, and the LT3757 compensation, FET and
   inductor choices (simulate in LTspice).
6. Measure switcher ripple at the LDO inputs; add a second π-stage if it is
   over 5 mV p-p.
7. 4-layer PCB (Sig / GND / PWR / Sig).
