# Design description

Reference designators here match `hardware/bom.csv`. Values marked **(verify)**
come from datasheet figures that should be re-checked against the current
revision before layout.

## 1. Block diagram

```
                 USB-C (data + power)               DC jack 12-15 V (optional)
                        |                                   |
          +-------------+-------------+                     |
          |                           |                     |
   USB 2.0 HS data            STUSB4500 PD sink             |
          |                   (asks 15/12/9 V)              |
          v                           |                     |
   +-------------+                    +------ OR (D1,D2) ---+
   | XMOS XU316  |                                |  VIN 5-15 V
   | USB Audio 2 |          +---------------------+---------------------+
   | 2 out/2 in  |          |                     |                     |
   +--+-----+----+     LT8582 ch1 SEPIC    LT8582 ch2 inverting   LT8362 boost
      | I2S  | I2S          +18.5 V             -18.5 V              +50 V
      |      |               |                     |                    |
      |      |          TPS7A4701 +16 V      TPS7A3301 -16 V     cap-multiplier
      |      |               |                     |               +48 V P48
      |      |               +------ +/-16 V analog rails ----+         |
      v      ^                                                |         |
  AK4493S  PCM1820 <-- OPA1612 ADC driver <-- THAT1512 <--+---+-- XLR mic in
   DAC       ADC        (SE -> diff)          mic pre     |   (6.81k feed,
      |                                        (0-60 dB)  |    switchable)
      v                                                   |
  OPA1612 diff->SE + 2-pole LPF                           |
      |                                                   |
  Volume pot (dual log 10k) -> gain switch (x1.5 / x5)    |
      |                                                   |
  OPA1612 + 2x BUF634A per channel (in-loop) -------------+
      |
  DC-protect + turn-on-delay relay -> 6.35 mm + 3.5 mm jacks
```

Digital-side supplies (TPS62A02 buck from VIN -> 3.3 V, TLV75509 -> 0.9 V core,
LT3042 -> clean 5.0 V / 3.3 V for DAC and ADC analog) are omitted from the
diagram for clarity.

## 2. Headphone amplifier (per channel) — the 2 W @ 32 Ω stage

**Requirement:** 2 W into 32 Ω = 8.0 Vrms = 11.3 V peak at 354 mA peak.

**Topology:** OPA1612 (U20A/B) non-inverting amp driving two BUF634A
(U21/U22 left, U23/U24 right) in parallel *inside* the op-amp's feedback loop.
The feedback is taken from the common output node after the ballast
resistors, so the ballast resistors, buffer output resistance and buffer
offsets are all corrected by loop gain.

| Part | Value | Purpose |
|---|---|---|
| R_in / C_in | 100 Ω / 470 pF C0G | RF filter at amp input |
| R_bias | 100 kΩ | DC path to ground if the pot wiper lifts |
| RF | 2.00 kΩ 0.1 % | feedback |
| RG_hi | 499 Ω 0.1 % | gain 5.0 (+14 dB), "High" |
| RG_lo | 4.02 kΩ 0.1 % | gain 1.5 (+3.5 dB), "Low" (IEMs) |
| CF | 22 pF C0G across RF | loop phase margin |
| R_iso | 47 Ω, one per buffer input | isolates op-amp from buffer input C |
| R_bal | 2.2 Ω 1 W, one per buffer output | current sharing |
| BW pin | open (low-BW / low-Iq mode) **(verify)** | 1.5 mA Iq per buffer |
| Rails | ±16 V, 10 µF X7R + 100 nF at each buffer | |

Gain switch S2 is a DPDT switching RG for both channels; pick the switch so
the RG leg is never open (make-before-break), or add 20 kΩ permanently
across RG_lo so an open leg only drops to unity-ish gain.

**Why two buffers:** one BUF634A is rated ±250 mA continuous. 354 mA peak
needs two; each then carries 177 mA (71 % of rating). Mismatched buffer
offsets (assumed ≤100 mV worst case) circulate ≤23 mA through 2 × 2.2 Ω.

**Headroom (see `tools/budget.py`):** on ±16 V with an assumed 2.5 V buffer
dropout at 180 mA and 4 Ω buffer output resistance, the buffer needs to swing
12.4 V and can swing 13.5 V. Predicted clean maximum is ~2.37 W into 32 Ω;
the ngspice simulation (`sim/hp_amp.cir`) shows 2.25 W at 0 % clipping and
the onset of clipping between 2.25 and 2.5 W.

| Load | Max clean output (predicted) | Limited by |
|---|---|---|
| 16 Ω | 2.0 W (5.7 Vrms) | 2 × 250 mA buffer current |
| 32 Ω | 2.37 W (8.7 Vrms) | voltage |
| 64 Ω | 1.30 W (9.1 Vrms) | voltage |
| 300 Ω | 0.30 W (9.45 Vrms) | voltage |
| 600 Ω | 0.15 W (9.5 Vrms) | voltage |

**Thermal:** worst-case class-AB dissipation is 1.62 W per channel
(0.86 W per buffer including Iq). With the DDA PowerPAD soldered to ≥4 cm²
of 2 oz copper per buffer (θJA ≈ 40 °C/W **(verify)**), Tj ≈ 75 °C at
40 °C ambient. Keep the four buffers spread out, not clustered.

**Output impedance:** closed-loop, well under 0.1 Ω at 1 kHz — the ballast
resistors are inside the loop. The relay contacts (~50 mΩ) dominate.

## 3. Headphone protection

- **Relay K1** — Omron G6K-2F-Y-5VDC (DPDT signal relay, 1 A contacts,
  verify rating vs 354 mA peak), one pole per channel. Contacts break the
  hot line between amp and jacks.
- **Turn-on delay:** 2.2 s (RC into comparator U30A, LM393) after both
  `PG_+16V` (TPS7A4701 PG) and a -16 V window comparator (U30B) are good.
- **DC detect:** each output through 47 kΩ into a 22 µF bipolar cap (1.1 s
  time constant); a bidirectional detector (two BC847/BC857 pairs) pulls the
  relay-enable low if either output sits beyond ±0.7 V DC.
- **Power-fail:** comparator on VIN (before bulk caps) drops the relay in
  < 5 ms when input power is removed, before the rails collapse.
- **Firmware mute:** XMOS GPIO `HP_EN` is ANDed in (open-drain) so the host
  can mute during sample-rate changes.
- Relay coil driver: 2N7002 with 1N4148 flyback.

## 4. DAC and reconstruction filter

- **U10 AK4493SEQ** in register (I2C) control mode, addressed by the XMOS.
  VREFH = 5.0 V from a dedicated LT3042 (U13), AVDD = 5.0 V (U13),
  TVDD = 3.3 V, DVDD from its internal LDO.
- Output: differential, 2.8 Vpp per leg × (VREFH−VREFL)/5 ⇒ ≈ 5.6 Vpp
  differential ≈ 1.98 Vrms **(verify)**.
- **U11 OPA1612** per channel: differential-to-single-ended, unity gain,
  2nd-order MFB low-pass, fc ≈ 80 kHz. Resistor matching 0.1 % for CMRR;
  the 2.5 V common-mode is rejected.
- Output coupled through 4.7 µF film (C_dac) into the volume pot → removes
  any residual DC from resistor mismatch (fc with 10 kΩ pot ≈ 3.4 Hz).
- **RV1** ALPS RK27 dual 10 kΩ log (or RK097 for small builds).

Result: 2 Vrms at full scale × gain 5 = 10 Vrms demand, so the amp clips
(≈2.3–2.4 W) about 1.2 dB before digital full scale in High gain. That is
intentional: 2 W is reachable at about −2 dBFS and the pot at max.
Low gain (×1.5) gives 3 Vrms max — plenty for IEMs with a much quieter
noise floor.

## 5. Microphone input with 48 V phantom power

**Connector J5:** Neutrik NCJ6FI-S combo; XLR pins 2 (+), 3 (−), 1 (ground
to chassis at the jack via 10 nF + short to signal ground at the star point).
The TRS part of the combo is left unconnected in this revision.

**Phantom supply (IEC 61938 P48):**
- **U40 LT8362** boost from VIN to 50 V (60 V switch), 1 MHz, soft-start.
- Capacitance multiplier (Q40 MJD47 + 100 kΩ/47 µF RC) drops to 48 V and
  removes switching ripple; 10 µH + 10 µF LC in front of it.
- 48 V ±4 V is the standard window; the unloaded output should read
  47.5–48.5 V.
- **S1** (DPST, front panel) switches phantom on via a 1 kΩ + 100 µF
  slow-ramp RC so the mic sees a soft ramp and the preamp input is not hit
  with a step. LED D40 indicates +48 V present.

**Feed network (per the IEC standard):**
- R50/R51 6.81 kΩ 0.1 % matched pair (matching sets CMRR with phantom on).
- C50/C51 47 µF 63 V electrolytic DC blocking caps (+ side toward the mic).
- R52/R53 2.21 kΩ bias resistors to ground after the caps (discharge path
  and input bias for the THAT1512).
- R54/R55 10 Ω series, then D50–D53 (1N4004, per THAT's recommendation)
  clamping each input to ±16 V rails, plus D54/D55 SMBJ18CA TVS on the
  ±16 V preamp rails. This survives a hot-plugged or shorted mic with
  phantom on.
- RFI: 470 pF differential + 2 × 100 pF to ground at the XLR, ferrite beads
  in series with pins 2 and 3.

**Preamp U51 THAT1512** on ±16 V (separately RC-filtered from the headphone
rails: 10 Ω + 220 µF per rail).
- Gain G = 0.5 + 5 kΩ / RG.
- RG = RGF (5.1 Ω fixed) + RV2 (10 kΩ reverse-log / C-taper pot) ⇒ 0 dB at
  pot max resistance, ≈ 60 dB at pot minimum.
- RG leg DC blocked with C_RG 4700 µF / 6.3 V (fc ≈ 6.6 Hz at 60 dB), so the
  output DC offset doesn't shift as gain changes (no scratchy pot noise).
- 100 pF compensation caps from each input to its gain pin as per the
  datasheet application circuit **(verify)**.

**ADC driver U52 OPA1612** converts single-ended to differential:
non-inverting unity buffer (+ leg) and unity inverter (− leg). With 1 Vrms at
the THAT1512 output the ADC sees 2 Vrms differential = 0 dBFS. That puts
the full-scale mic input at +2.2 dBu (0 dB gain) down to −58 dBu (60 dB).

**ADC protection:** the driver runs on ±16 V but the ADC input is a 3.3 V
part, so each leg goes through 1 µF film AC coupling, 100 Ω, then BAT54S
Schottky clamps to AVDD/AGND, with 2.2 nF C0G to ground (charge-kickback
filter). A 5 mA clamp current is harmless to the ADC and to the op amp.

**U53 PCM1820** (hardware-controlled, 113 dB DR, 2 Vrms differential FS):
strapped for I2S, target (slave) mode, 32-bit — see the datasheet's hardware
configuration table. Channel 1 = mic; channel 2 input is AC-grounded and the
firmware duplicates ch1 to both USB input channels by default.

**Clip LED:** window comparator (U54, TLV3202) at THAT1512 output ±1.3 V
peak (≈ −1 dBFS) with 100 ms pulse stretch → red LED next to the gain knob.

## 6. Digital / USB

- **U1 XMOS XU316-1024-QF60B**: USB 2.0 HS device, runs XMOS
  `sw_usb_audio` (UAC2, 44.1–192 kHz, 24/32-bit, 2 out / 2 in). Class
  compliant on macOS, Linux, iOS/Android and Windows 10 1703+.
- **U2** 16 Mbit QSPI flash (IS25LP016D) for firmware; **Y1** 24 MHz crystal
  for the XMOS PLL.
- **Audio master clocks:** Y2 24.576 MHz and Y3 22.5792 MHz low-phase-noise
  oscillators (NDK NZ2520SDA or Crystek CCHD-575), one enabled at a time by
  XMOS GPIO `MCLK_SEL`, merged with a 74LVC1G157 mux, then fanned out with
  22 Ω series terminators to XMOS MCLK_IN and AK4493 MCLK. The PCM1820
  runs from BCLK/LRCK and needs no MCLK **(verify)**.
- XMOS is I2S master (BCLK, LRCK) for both converters.
- I2C (XMOS → AK4493 and STUSB4500 status read), 2.2 kΩ pull-ups.
- USB-C J1: USB2 D+/D− only, 5.1 kΩ on CC1/CC2 are provided by the
  STUSB4500. ESD: TPD4E05U06 on D+/D−/CC.

## 7. Power

Full 2 W sine into both channels needs ≈ 13.3 W at the input
(`tools/budget.py`). Accepted sources:

| Source | Available | Result |
|---|---|---|
| USB 2/3 port, 5 V 0.5–0.9 A | 2.5–4.5 W | **not supported** — XMOS keeps relay open, LED blinks |
| USB-C 5 V 1.5 A | 7.5 W | full function; music peaks to 2 W, sustained sine less |
| USB-C 5 V 3 A | 15 W | full 2 W sine |
| USB-PD 9/12/15 V | ≥ 27 W | full 2 W sine |
| DC jack 12–15 V ≥ 1.5 A | ≥ 18 W | full 2 W sine (recommended for desktop use) |

- **U3 STUSB4500** stand-alone PD sink, NVM programmed PDO3 = 15 V/1.5 A,
  PDO2 = 12 V/1.5 A, PDO1 = 5 V; its `POWER_OK` pins tell the XMOS what was
  negotiated.
- **D1/D2** SS54 Schottky OR between USB VBUS and the DC jack
  (upgrade: LM74700 ideal-diode controllers to save ~0.5 W).
- **U5 LT8582** dual converter, 1 MHz, synchronised to a clean clock:
  ch1 SEPIC → +18.5 V, ch2 inverting → −18.5 V. Works across the whole
  5–15 V input range (switch stress at 15 V in: 15 + 18.5 = 33.5 V < 42 V).
  Each output: 2 × 22 µF 35 V X7R + 1 µH / 22 µF π-filter.
- **U6 TPS7A4701** → +16.0 V, **U7 TPS7A3301** → −16.0 V (1 A each, ~4 µV
  noise). Dissipation 0.65 W each at full power — thermal pad to copper pour.
- Mic preamp and ADC driver get their own RC-filtered branch off ±16 V.
- **U8 TPS62A02** buck VIN → 3.3 V (digital), **U9 TLV75509** 3.3 → 0.9 V
  XMOS core. **U13/U14 LT3042** → 5.0 V DAC analog/VREF, 3.3 V ADC analog,
  fed from a separate 5.5 V buck tap (U12 TPS62A02).
- Grounding: one ground plane, split only by placement (digital/USB corner,
  switchers in the opposite corner behind the analog area, amp next to the
  jacks). Star point at the headphone jack sleeve for the amp return; chassis
  bonded at the USB shield (1 MΩ ∥ 4.7 nF) and XLR pin 1.

## 8. Expected performance (targets, not measurements)

| Parameter | Target |
|---|---|
| Headphone output, 32 Ω | ≥ 2.0 W (≈ 2.3 W at clip) |
| Headphone output, 300 Ω | ≈ 0.3 W / 9.4 Vrms |
| Output impedance | < 0.1 Ω (amp) |
| DAC → HP dynamic range, low gain | > 118 dB(A) |
| Mic EIN at 60 dB | ≈ −128 dBu (THAT1512 datasheet ~1 nV/√Hz) |
| Mic input gain | 0 to 60 dB |
| Phantom | 48 V ± 1 V, 10 mA available |
| Sample rates | 44.1 – 192 kHz, 24/32-bit, both directions |

## 9. Open items before layout

1. Re-confirm BUF634A dropout at 180 mA / 85 °C and open-loop Rout; if the
   dropout is > 3 V, raise the rails to ±17 V (TPS7A47/TPS7A33 are fine,
   BUF634A abs max 36 V total — do **not** exceed ±18 V).
2. Confirm AK4493 register-mode start-up sequence and the exact full-scale
   output; adjust the diff-to-SE gain so SE full scale ≈ 2.0 Vrms.
3. Confirm PCM1820 strap pins for I2S / target mode / word length.
4. Measure LT8582 ripple at the LDO inputs; add a 2nd π-stage if > 5 mVpp.
5. Draw the KiCad schematic and 4-layer PCB (Sig / GND / PWR / Sig).
