#!/usr/bin/env python3
"""Headroom, power and thermal budget for the headphone amp and supplies.

Run: python3 tools/budget.py
All inputs are at the top of the file; datasheet-derived figures that should
be re-checked before layout are marked ASSUMED.
"""
import math

# ---- Targets -------------------------------------------------------------
P_TARGET = 2.0          # W per channel, continuous sine
R_LOAD = 32.0           # ohm
CHANNELS = 2

# ---- Headphone amp output stage -----------------------------------------
V_RAIL = 16.0           # +/- rail after the TPS7A47 / TPS7A33 LDOs
N_BUF = 2               # LME49600 in parallel per channel
R_BALLAST = 2.2         # ohm, one per buffer, feedback taken after them
BUF_HEADROOM = 2.5      # V, ASSUMED LME49600 (V+)-Vout at ~180 mA, hot
BUF_ROUT = 4.0          # ohm, ASSUMED LME49600 open-loop output resistance
BUF_IOUT_MAX = 0.250    # A, LME49600 continuous output current rating
BUF_VOS_MAX = 0.100     # V, ASSUMED worst-case buffer offset mismatch
BUF_IQ = 0.0073         # A, LME49600 quiescent, BW pin open (datasheet)
OPAMP_IQ = 0.0036 * 2   # A, OPA1612 per package (2 ch)
N_OPAMP_PKGS_ON_RAILS = 5   # HP amp 1, DAC I/V + diff 3, ADC driver 1
THAT1512_IQ = 0.007     # A
THETA_JA_BUF = 40.0     # degC/W, ASSUMED LME49600 TO-263 tab on ~4 cm2 copper
T_AMBIENT = 40.0        # degC inside enclosure

# ---- Pre-regulators ------------------------------------------------------
V_SW = 18.4             # LT3757 SEPIC / Cuk outputs
I_5VA = 0.07            # A, ASSUMED +5VA analog LDO load (DAC + ADC + LT3042), fed from +V_SW
ETA_SW = 0.85
V_PHANTOM = 48.0
I_PHANTOM = 0.010       # A, worst case (one mic drawing IEC 61938 P48 max)
ETA_PHANTOM = 0.80
P_DIGITAL = 1.2         # W: XU316 + clocks + DAC + ADC + LEDs, ASSUMED
ETA_DIGITAL = 0.88


def hdr(t):
    print(f"\n== {t} " + "=" * (60 - len(t)))


def main():
    v_rms = math.sqrt(P_TARGET * R_LOAD)
    v_pk = v_rms * math.sqrt(2)
    i_pk = v_pk / R_LOAD
    i_pk_buf = i_pk / N_BUF

    hdr("Output requirement")
    print(f"{P_TARGET:.1f} W into {R_LOAD:.0f} ohm -> {v_rms:.2f} Vrms, "
          f"{v_pk:.2f} Vpk, {i_pk*1000:.0f} mA pk")

    hdr("Voltage headroom")
    r_int = R_BALLAST + BUF_ROUT   # drop inside the loop, per buffer
    v_buf_needed = v_pk + i_pk_buf * r_int
    v_buf_avail = V_RAIL - BUF_HEADROOM
    print(f"buffer must swing   {v_buf_needed:.2f} V (incl. Rout + ballast drop)")
    print(f"buffer can swing    {v_buf_avail:.2f} V on +/-{V_RAIL:.0f} V rails")
    margin = v_buf_avail - v_buf_needed
    print(f"margin              {margin:.2f} V  -> {'OK' if margin > 0.5 else 'FAIL'}")
    print("max clean output (voltage- or current-limited):")
    for rl in (16, 32, 64, 300, 600):
        v_lim = v_buf_avail / (1 + r_int / (N_BUF * rl))
        i_lim = BUF_IOUT_MAX * N_BUF * rl
        vpk = min(v_lim, i_lim)
        why = "V" if v_lim <= i_lim else "I"
        print(f"  {rl:4d} ohm: ~{vpk**2/2/rl:5.2f} W  ({vpk/math.sqrt(2):5.2f} Vrms, {why}-limited)")

    hdr("Current sharing")
    print(f"peak per buffer     {i_pk_buf*1000:.0f} mA of {BUF_IOUT_MAX*1000:.0f} mA rating "
          f"({'OK' if i_pk_buf < 0.8*BUF_IOUT_MAX else 'CHECK'})")
    i_circ = BUF_VOS_MAX / (N_BUF * R_BALLAST)
    print(f"worst circulating   {i_circ*1000:.1f} mA from {BUF_VOS_MAX*1000:.0f} mV offset mismatch")

    hdr("Rail current and dissipation at full power (sine, both ch)")
    i_avg_per_rail_ch = i_pk / math.pi
    i_q = N_BUF * BUF_IQ * CHANNELS + OPAMP_IQ * N_OPAMP_PKGS_ON_RAILS + THAT1512_IQ
    i_rail = i_avg_per_rail_ch * CHANNELS + i_q
    print(f"avg per rail        {i_rail*1000:.0f} mA (signal {i_avg_per_rail_ch*CHANNELS*1000:.0f} + Iq {i_q*1000:.0f})")
    p_supply_ch = 2 * V_RAIL * v_pk / (math.pi * R_LOAD)
    p_diss_ch = p_supply_ch - P_TARGET
    p_diss_worst_ch = 2 * V_RAIL**2 / (math.pi**2 * R_LOAD)  # at Vpk = 2/pi Vrail
    print(f"per ch: supply {p_supply_ch:.2f} W, output {P_TARGET:.2f} W, "
          f"stage diss {p_diss_ch:.2f} W (worst-case level {p_diss_worst_ch:.2f} W)")
    p_buf = p_diss_worst_ch / N_BUF + 2 * V_RAIL * BUF_IQ
    tj = T_AMBIENT + p_buf * THETA_JA_BUF
    print(f"per LME49600 worst  {p_buf:.2f} W -> Tj ~{tj:.0f} degC "
          f"({'OK' if tj < 125 else 'FAIL'}, abs max 150)")
    p_ldo = (V_SW - V_RAIL) * i_rail
    print(f"per LDO             {p_ldo:.2f} W ({V_SW} -> {V_RAIL} V at {i_rail*1000:.0f} mA)")

    hdr("Input power budget")
    p_rails = (2 * V_SW * i_rail + V_SW * I_5VA) / ETA_SW
    p_ph = V_PHANTOM * I_PHANTOM / ETA_PHANTOM
    p_dig = P_DIGITAL / ETA_DIGITAL
    total = p_rails + p_ph + p_dig
    print(f"+/-{V_SW} V switcher in  {p_rails:.2f} W")
    print(f"phantom boost in     {p_ph:.2f} W")
    print(f"digital/3.3V/0.9V in {p_dig:.2f} W")
    print(f"TOTAL (2x{P_TARGET} W sine) {total:.2f} W")
    for v, i, name in ((5, 0.9, "USB 3.0 port"), (5, 1.5, "USB-C 1.5 A"),
                       (5, 3.0, "USB-C 3 A"), (9, 3.0, "PD 9 V"),
                       (12, 1.5, "12 V DC jack"), (15, 3.0, "PD 15 V")):
        ok = "full 2 W sine" if v * i >= total * 1.1 else (
            "music peaks only" if v * i >= total * 0.35 else "insufficient")
        print(f"  {name:13s} {v*i:5.1f} W available -> {ok}")


if __name__ == "__main__":
    main()
