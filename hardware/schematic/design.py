#!/usr/bin/env python3
"""Schematic source for the all-in-one audio interface.

Run:  python3 hardware/schematic/design.py
Writes the KiCad 7 project to hardware/schematic/kicad/ (open in KiCad, or in
Altium Designer 24+ via File > Import Wizard > KiCad).

Reference designators: 1xx power, 2xx USB/XMOS/clocks, 3xx DAC,
4xx headphone amp + protection, 5xx microphone input + ADC.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kigen import Design, make_ic_symbol, write_bom  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kicad')

R0603 = 'Resistor_SMD:R_0603_1608Metric'
R0805 = 'Resistor_SMD:R_0805_2012Metric'
R2512 = 'Resistor_SMD:R_2512_6332Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'
CP8 = 'Capacitor_SMD:CP_Elec_8x10'
CP10 = 'Capacitor_SMD:CP_Elec_10x10'
SO8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
DPAK = 'Package_TO_SOT_SMD:TO-252-2'
SMB = 'Diode_SMD:D_SMB'
SMA = 'Diode_SMD:D_SMA'
SOD123 = 'Diode_SMD:D_SOD-123'
LED0805 = 'LED_SMD:LED_0805_2012Metric'
FILM = 'Capacitor_THT:C_Rect_L18.0mm_W8.0mm_P15.00mm_FKS3_FKP3'

d = Design('All-in-one audio interface',
           rev='A', date='2026-10-23', company='VincentM9')

# =============================================================== POWER ====
P = d.sheet('pwr_input', 'Power input and +18V4 SEPIC converter', 1, notes=(
    'POWER INPUT / +18V4\n'
    '- VIN = USB-C VBUS (after the STUSB4500 load switch) OR 12-15 V DC jack, Schottky OR, TVS.\n'
    '- U101 LT3757 SEPIC -> +18V4. FBX = +1.6 V x (1 + 105k/10k). RT 41.2k = 300 kHz.\n'
    '  Current limit 110 mV / 30 mR = 3.7 A. Feedback is taken before the 1 uH post-filter.\n'
    '- VERIFY: LT3757 compensation, FET and inductor choices (simulate in LTspice).'))

P.add('Connector:Barrel_Jack', '12-15V DC', {'1': 'DCIN', '2': 'GND'}, fp='Connector_BarrelJack:BarrelJack_Horizontal', mpn='PJ-102AH')
P.add('Device:D_Schottky', 'SS54', {'1': 'VIN', '2': 'VBUS_SW'}, fp=SMB, rot=0, mpn='SS54')
P.add('Device:D_Schottky', 'SS54', {'1': 'VIN', '2': 'DCIN'}, fp=SMB, mpn='SS54')
P.add('Device:D_TVS', 'SMBJ16CA', {'1': 'VIN', '2': 'GND'}, fp=SMB, mpn='SMBJ16CA')
P.CP('220u 25V', 'VIN', 'GND', fp=CP10)
P.C('10u 25V', 'VIN', 'GND', fp=C1210)


def lt3757(sheet, tag, n_uvlo_top, rt, rsense, extra):
    """Common LT3757 core. Returns the IC part; extra = pin overrides."""
    u = 'U' + tag
    nets = {'10': 'VIN', '11': 'GND', '9': u + '_UVLO', '8': u + '_INTVCC', '4': u + '_RT',
            '5': 'GND', '3': u + '_SS', '1': u + '_VC', '2': u + '_FBX', '6': u + '_SENSE',
            '7': u + '_GATE'}
    ic = sheet.add('Regulator_Switching:LT3757EMSE', 'LT3757EMSE', nets,
                   fp='Package_SO:MSOP-10-1EP_3x3mm_P0.5mm_EP1.68x1.88mm', mpn='LT3757EMSE#PBF')
    sheet.R(n_uvlo_top, 'VIN', u + '_UVLO')
    sheet.R('100k', u + '_UVLO', 'GND')
    sheet.C('4.7u 16V', u + '_INTVCC', 'GND', fp=C0805)
    sheet.R(rt, u + '_RT', 'GND')
    sheet.C('100n', u + '_SS', 'GND')
    sheet.R('10k', u + '_VC', u + '_VCR')
    sheet.C('6.8n', u + '_VCR', 'GND')
    sheet.C('100p', u + '_VC', 'GND')
    sheet.R(rsense, u + '_SENSE', 'GND', fp=R2512, desc='current sense, 1 W')
    sheet.C('10u 25V', 'VIN', 'GND', fp=C1210)
    return ic


# ---- U101 SEPIC +18V4 ----
lt3757(P, '101', '249k', '41.2k', '30m', {})
P.add('Device:Q_NMOS_GDS', 'IPD25N06S4L-30', {'1': 'U101_GATE', '2': 'SW1', '3': 'U101_SENSE'}, fp=DPAK,
      mpn='IPD25N06S4L-30', desc='60 V logic-level N-MOSFET')
P.L('22u 4A', 'VIN', 'SW1', mpn='SRR1260-220M', desc='SEPIC input inductor')
P.L('22u 4A', 'GND', 'X1', mpn='SRR1260-220M', desc='SEPIC output inductor')
P.C('4.7u 50V', 'SW1', 'X1', fp=C1210, desc='SEPIC coupling cap')
P.add('Device:D_Schottky', 'SS36', {'1': '+18V4_SW', '2': 'X1'}, fp=SMB, mpn='SS36')
P.R('105k', '+18V4_SW', 'U101_FBX')
P.R('10k', 'U101_FBX', 'GND')
P.C('22u 50V', '+18V4_SW', 'GND', fp=C1210)
P.C('22u 50V', '+18V4_SW', 'GND', fp=C1210)
P.CP('100u 35V', '+18V4_SW', 'GND', fp=CP8)
P.L('1u', '+18V4_SW', '+18V4', fp='Inductor_SMD:L_1210_3225Metric')
P.C('22u 50V', '+18V4', 'GND', fp=C1210)
P.CP('100u 35V', '+18V4', 'GND', fp=CP8)

# ---- U102 Cuk / inverting -18V4 ----
P = d.sheet('pwr_neg', '-18V4 Cuk converter', 1, notes=(
    '-18V4\n'
    '- U102 LT3757 Cuk (inverting) -> -18V4. FBX = -0.8 V x (1 + 110k/4.99k).\n'
    '- Diode anode at the switch-side node X2, cathode to GND; output inductor from X2 to -18V4_SW.'))
lt3757(P, '102', '249k', '41.2k', '30m', {})
P.add('Device:Q_NMOS_GDS', 'IPD25N06S4L-30', {'1': 'U102_GATE', '2': 'SW2', '3': 'U102_SENSE'}, fp=DPAK,
      mpn='IPD25N06S4L-30')
P.L('22u 4A', 'VIN', 'SW2', mpn='SRR1260-220M', desc='Cuk input inductor')
P.L('22u 4A', '-18V4_SW', 'X2', mpn='SRR1260-220M', desc='Cuk output inductor')
P.C('4.7u 50V', 'SW2', 'X2', fp=C1210, desc='Cuk coupling cap')
P.add('Device:D_Schottky', 'SS36', {'1': 'GND', '2': 'X2'}, fp=SMB, mpn='SS36')
P.R('110k', '-18V4_SW', 'U102_FBX')
P.R('4.99k', 'U102_FBX', 'GND')
P.C('22u 50V', 'GND', '-18V4_SW', fp=C1210)
P.C('22u 50V', 'GND', '-18V4_SW', fp=C1210)
P.CP('100u 35V', 'GND', '-18V4_SW', fp=CP8)
P.L('1u', '-18V4_SW', '-18V4', fp='Inductor_SMD:L_1210_3225Metric')
P.C('22u 50V', 'GND', '-18V4', fp=C1210)
P.CP('100u 35V', 'GND', '-18V4', fp=CP8)

# ---- U103 boost +50V for phantom ----
P = d.sheet('pwr_phantom', '+50V boost and +48V phantom supply', 1, notes=(
    'PHANTOM SUPPLY\n'
    '- U103 LT3757 boost -> +50V (FBX = 1.6 V x (1 + 301k/10k)), 100 V FET and diode.\n'
    '- Q104 capacitance multiplier -> +48V (about 49.3 V open-circuit, 48.6 V at 15 mA).'))
lt3757(P, '103', '249k', '41.2k', '100m', {})
P.add('Device:Q_NMOS_GDS', 'IPD33CN10N', {'1': 'U103_GATE', '2': 'SW3', '3': 'U103_SENSE'}, fp=DPAK,
      mpn='IPD33CN10N G', desc='100 V N-MOSFET')
P.L('22u', 'VIN', 'SW3')
P.add('Device:D_Schottky', 'STPS1H100A', {'1': '+50V_SW', '2': 'SW3'}, fp=SMA, mpn='STPS1H100A')
P.R('301k', '+50V_SW', 'U103_FBX')
P.R('10k', 'U103_FBX', 'GND')
P.C('2.2u 100V', '+50V_SW', 'GND', fp=C1210)
P.C('2.2u 100V', '+50V_SW', 'GND', fp=C1210)
P.L('10u', '+50V_SW', '+50V', fp='Inductor_SMD:L_1210_3225Metric')
P.C('2.2u 100V', '+50V', 'GND', fp=C1210)
P.add('Device:Q_NPN_BEC', 'MMBTA06', {'1': 'CMUL_B', '2': '+48V', '3': '+50V'}, fp=SOT23, mpn='MMBTA06',
      desc='capacitance multiplier')
P.R('4.7k', '+50V', 'CMUL_B')
P.CP('100u 63V', 'CMUL_B', 'GND', fp=CP10)
P.CP('47u 63V', '+48V', 'GND', fp=CP10)

# ---- LDOs ----
P = d.sheet('pwr_ldo', 'Linear regulators: +-16V, +5VA, +3V3A', 1, notes=(
    'LINEAR REGULATORS\n'
    '- U104 TPS7A4701 ANY-OUT +16.0 V (6.4+6.4+1.6+0.2 grounded). U106 TPS7A4701 +5.0 V (3.2+0.4).\n'
    '- U105 TPS7A3301 -16.1 V = -1.176 V x (1 + 127k/10k). Pad = GND, EN = IN (datasheet).\n'
    '- U107 LT3042 +3V3A (100 uA x 33.2k) for oscillators and converters.\n'
    '- Put every thermal pad on copper pour; the +-16 V LDOs dissipate ~0.7 W at full power.'))
anyout = {'15': '+18V4', '16': '+18V4', '13': '+18V4', '1': '+16V', '20': '+16V', '3': '+16V',
          '7': 'GND', '21': 'GND', '14': 'U104_NR', '4': 'GND', '5': 'GND', '8': 'GND', '11': 'GND'}
P.add('Regulator_Linear:TPS7A4701xRGW', 'TPS7A4701 +16V', anyout, mpn='TPS7A4701RGWR')
P.C('1u', 'U104_NR', 'GND')
P.C('10u 25V', '+18V4', 'GND', fp=C1210)
P.C('10u 25V', '+16V', 'GND', fp=C1210)
P.CP('100u 25V', '+16V', 'GND', fp=CP8)

P.add('Regulator_Linear:TPS7A3301RGW', 'TPS7A3301 -16V',
      {'15': '-18V4', '16': '-18V4', '13': '-18V4', '1': '-16V', '20': '-16V', '3': 'U105_FB',
       '7': 'GND', '21': 'GND', '14': 'U105_NR'}, mpn='TPS7A3301RGWR')
P.R('127k', '-16V', 'U105_FB')
P.C('10n', '-16V', 'U105_FB')
P.R('10k', 'U105_FB', 'GND')
P.C('10n', 'U105_NR', 'GND')
P.C('10u 25V', 'GND', '-18V4', fp=C1210)
P.C('10u 25V', 'GND', '-16V', fp=C1210)
P.CP('100u 25V', 'GND', '-16V', fp=CP8)

P.add('Regulator_Linear:TPS7A4701xRGW', 'TPS7A4701 +5V',
      {'15': '+18V4', '16': '+18V4', '13': '+18V4', '1': '+5VA', '20': '+5VA', '3': '+5VA',
       '7': 'GND', '21': 'GND', '14': 'U106_NR', '6': 'GND', '10': 'GND'}, mpn='TPS7A4701RGWR')
P.C('1u', 'U106_NR', 'GND')
P.C('10u 25V', '+18V4', 'GND', fp=C1210)
P.C('10u 16V', '+5VA', 'GND', fp=C1206)

P.add('Regulator_Linear:LT3042xMSE', 'LT3042 +3V3A',
      {'1': '+5VA', '2': '+5VA', '3': '+5VA', '5': 'GND', '7': 'U107_SET', '10': '+3V3A', '9': '+3V3A',
       '6': 'U107_PGFB', '8': 'GND', '11': 'GND'}, mpn='LT3042EMSE#PBF')
P.R('33.2k', 'U107_SET', 'GND')
P.C('4.7u', 'U107_SET', 'GND', fp=C0805)
P.R('82.5k', '+3V3A', 'U107_PGFB')
P.R('10k', 'U107_PGFB', 'GND')
P.C('4.7u', '+5VA', 'GND', fp=C0805)
P.C('10u', '+3V3A', 'GND', fp=C0805)

P = d.sheet('pwr_digital', 'Digital supplies: +3V3D, +0V9, +1V8', 1, notes=(
    'DIGITAL SUPPLIES\n'
    '- U108 / U109 TPS62130 bucks from VIN -> +3V3D and +0V9 (XMOS core). Vout = 0.8 V x (1 + R1/100k).\n'
    '- U110 TLV75518 -> +1V8 (XMOS USB PHY).\n'
    '- VERIFY: TPS62130 FSW pin sense (GND = high frequency?).'))

for tag, net, r1, sw in (('108', '+3V3D', '316k', 'SW_3V3'), ('109', '+0V9', '12.4k', 'SW_0V9')):
    P.add('Regulator_Switching:TPS62130', 'TPS62130',
          {'10': 'VIN', '11': 'VIN', '12': 'VIN', '13': 'VIN', '1': sw, '2': sw, '3': sw, '14': net,
           '5': 'U%s_FB' % tag, '6': 'GND', '15': 'GND', '16': 'GND', '17': 'GND', '7': 'GND', '8': 'GND',
           '9': 'U%s_SS' % tag}, mpn='TPS62130RGTR')
    P.L('2.2u', sw, net, fp='Inductor_SMD:L_Bourns_SRP5030T', mpn='SRP5030T-2R2M')
    P.R(r1, net, 'U%s_FB' % tag)
    P.R('100k', 'U%s_FB' % tag, 'GND')
    P.C('3.3n', 'U%s_SS' % tag, 'GND')
    P.C('10u 25V', 'VIN', 'GND', fp=C1210)
    P.C('22u', net, 'GND', fp=C0805)
    P.C('22u', net, 'GND', fp=C0805)

P.add('Regulator_Linear:TLV75518PDBV', 'TLV75518 +1V8',
      {'1': '+3V3D', '3': '+3V3D', '2': 'GND', '5': '+1V8'}, fp='Package_TO_SOT_SMD:SOT-23-5', mpn='TLV75518PDBVR')
P.C('1u', '+3V3D', 'GND')
P.C('1u', '+1V8', 'GND')

# ======================================================== USB / XMOS =======
U = d.sheet('usb_pd', 'USB-C connector and PD sink', 2, notes=(
    'USB-C / PD\n'
    '- U202 STUSB4500: NVM PDO3 = 15V/1.5A, PDO2 = 12V/1.5A, PDO1 = 5V. VBUS_EN_SNK drives load switch Q201.\n'
    '- VSYS grounded (unused). DISCH and VBUS_VS_DISCH have current-limiting resistors.\n'
    '- U201 ESD protection on D+/D-/CC1/CC2. Shield to chassis through 1M || 4.7n.'))

U.add('Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C',
      {'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS', 'A5': 'CC1', 'B5': 'CC2',
       'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DM', 'B7': 'USB_DM',
       'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'S1': 'CHASSIS'},
      fp='Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal', mpn='USB4105-GF-A')
U.R('1M', 'CHASSIS', 'GND')
U.C('4.7n 250V', 'CHASSIS', 'GND', fp=C1206)
U.add('Power_Protection:TPD4E05U06DQA', 'TPD4E05U06',
      {'1': 'USB_DP', '2': 'USB_DM', '4': 'CC1', '5': 'CC2', '3': 'GND', '8': 'GND'}, mpn='TPD4E05U06DQAR')
U.add('Interface_USB:STUSB4500QTR', 'STUSB4500',
      {'1': 'CC1', '2': 'CC1', '4': 'CC2', '5': 'CC2', '24': 'VBUS', '22': 'GND', '21': 'U202_V12',
       '23': 'U202_V27', '10': 'GND', '25': 'GND', '6': 'GND', '7': 'I2C_SCL', '8': 'I2C_SDA',
       '12': 'GND', '13': 'GND', '18': 'U202_VS', '9': 'U202_DISCH', '16': 'PD_EN_N',
       '20': 'PD_POK2', '14': 'PD_POK3'}, mpn='STUSB4500QTR')
U.C('1u', 'U202_V12', 'GND')
U.C('1u', 'U202_V27', 'GND')
U.C('1u 25V', 'VBUS', 'GND', fp=C0805)
U.R('1k', 'VBUS', 'U202_VS', desc='limits VBUS_VS_DISCH current')
U.R('100R', 'VBUS_SW', 'U202_DISCH', fp=R0805, desc='limits DISCH current')
U.R('10k', 'PD_POK2', '+3V3D')
U.R('10k', 'PD_POK3', '+3V3D')
U.add('Device:Q_PMOS_GSD', 'AO3407A', {'1': 'PD_EN_N', '2': 'VBUS', '3': 'VBUS_SW'}, fp=SOT23, mpn='AO3407A',
      desc='VBUS load switch, -30 V, Vgs +-20 V')
U.R('100k', 'VBUS', 'PD_EN_N')
U.R('2.2k', 'I2C_SCL', '+3V3D')
U.R('2.2k', 'I2C_SDA', '+3V3D')

U = d.sheet('xmos', 'XMOS XU316, boot flash, debug', 2, notes=(
    'XMOS\n'
    '- U203 XU316-1024-QF60B: FUNCTION names only. Pin numbers are placeholders (?nn) and there is no footprint.\n'
    '  Replace it with the official XMOS library part before layout; assign I2S/GPIO to ports in the .xn file.\n'
    '  From the datasheet: USB_DM = 28, USB_DP = 29, USB_VDD33 = 30, USB_VDD18 = 31; core 0.855-0.945 V.\n'
    '- QSPI boot flash on X0D01 / X0D04-07 / X0D10 (check the boot-mode straps in the datasheet).\n'
    '- J202 debug header pinout is a placeholder: match it to your XTAG adapter.'))

xmos_pins_left = [
    ('?01', 'USB_DP', 'bidirectional'), ('?02', 'USB_DM', 'bidirectional'),
    ('?03', 'CLK_24M', 'input'), ('?04', 'RST_N', 'input'),
    ('?05', 'TCK', 'input'), ('?06', 'TMS', 'input'), ('?07', 'TDI', 'input'), ('?08', 'TDO', 'output'),
    ('?09', 'QSPI_CS_N', 'output'), ('?10', 'QSPI_CLK', 'output'), ('?11', 'QSPI_D0', 'bidirectional'),
    ('?12', 'QSPI_D1', 'bidirectional'), ('?13', 'QSPI_D2', 'bidirectional'), ('?14', 'QSPI_D3', 'bidirectional'),
    ('?15', 'I2C_SCL', 'bidirectional'), ('?16', 'I2C_SDA', 'bidirectional'),
]
xmos_pins_right = [
    ('?17', 'MCLK_IN', 'input'), ('?18', 'I2S_BCLK', 'output'), ('?19', 'I2S_LRCK', 'output'),
    ('?20', 'I2S_DOUT', 'output'), ('?21', 'I2S_DIN', 'input'), ('?22', 'MCLK_SEL', 'output'),
    ('?23', 'DAC_RST_N', 'output'), ('?24', 'DAC_MUTE', 'output'), ('?25', 'ADC_RST_N', 'output'),
    ('?26', 'ADC_M0', 'output'), ('?27', 'ADC_M1', 'output'), ('?28', 'HP_EN', 'output'),
    ('?29', 'PD_POK2', 'input'), ('?30', 'PD_POK3', 'input'), ('?31', 'LED_PWR', 'output'),
    ('?32', 'LED_ERR', 'output'),
]
xmos_top = [('?33', 'VDD', 'power_in'), ('?34', 'VDD', 'power_in'), ('?35', 'VDD', 'power_in'),
            ('?36', 'PLL_AVDD', 'power_in'), ('?37', 'VDDIO', 'power_in'), ('?38', 'VDDIO', 'power_in'),
            ('?39', 'VDDIO', 'power_in'), ('?40', 'USB_VDD33', 'power_in'), ('?41', 'USB_VDD18', 'power_in')]
xmos_bot = [('?42', 'GND', 'power_in')]
XSYM = make_ic_symbol('aio:XU316-1024-QF60B', xmos_pins_left, xmos_pins_right, xmos_top, xmos_bot,
                      value='XU316-1024-QF60B', fp='',
                      desc='XMOS xcore.ai USB Audio controller - PIN NUMBERS ARE PLACEHOLDERS')
xm = {'?01': 'USB_DP', '?02': 'USB_DM', '?03': 'CLK_24M', '?04': 'RST_N', '?05': 'TCK', '?06': 'TMS',
      '?07': 'TDI', '?08': 'TDO', '?09': 'QSPI_CS_N', '?10': 'QSPI_CLK', '?11': 'QSPI_D0', '?12': 'QSPI_D1',
      '?13': 'QSPI_D2', '?14': 'QSPI_D3', '?15': 'I2C_SCL', '?16': 'I2C_SDA',
      '?17': 'MCLK_XMOS', '?18': 'X_BCLK', '?19': 'X_LRCK', '?20': 'X_DOUT', '?21': 'I2S_DIN',
      '?22': 'MCLK_SEL', '?23': 'DAC_RST_N', '?24': 'DAC_MUTE', '?25': 'ADC_RST_N', '?26': 'ADC_M0',
      '?27': 'ADC_M1', '?28': 'HP_EN', '?29': 'PD_POK2', '?30': 'PD_POK3', '?31': 'LED_PWR', '?32': 'LED_ERR',
      '?33': '+0V9', '?34': '+0V9', '?35': '+0V9', '?36': '+0V9_PLL', '?37': '+3V3D', '?38': '+3V3D',
      '?39': '+3V3D', '?40': '+3V3D', '?41': '+1V8', '?42': 'GND'}
U.add('aio:XU316-1024-QF60B', 'XU316-1024-QF60B', xm, custom=XSYM, mpn='XU316-1024-QF60B-C24',
      fp='')
for _ in range(3):
    U.C('100n', '+0V9', 'GND')
U.C('22u', '+0V9', 'GND', fp=C0805)
U.FB('600R@100MHz', '+0V9', '+0V9_PLL')
U.C('1u', '+0V9_PLL', 'GND')
for _ in range(4):
    U.C('100n', '+3V3D', 'GND')
U.C('10u', '+3V3D', 'GND', fp=C0805)
U.C('100n', '+1V8', 'GND')
U.R('10k', 'RST_N', '+3V3D')
U.C('100n', 'RST_N', 'GND')
U.add('Oscillator:ASE-xxxMHz', '24.000MHz', {'1': '+3V3D', '2': 'GND', '3': 'CLK_24M', '4': '+3V3D'},
      mpn='ASE-24.000MHZ-LC-T')
U.add('Connector_Generic:Conn_02x05_Odd_Even', 'DEBUG (verify)',
      {'1': '+3V3D', '2': 'TMS', '3': 'GND', '4': 'TCK', '5': 'GND', '6': 'TDO', '8': 'TDI', '9': 'GND',
       '10': 'RST_N'}, fp='Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical')
U.add('Memory_Flash:W25Q32JVSS', 'W25Q32JVSS',
      {'1': 'QSPI_CS_N', '2': 'QSPI_D1', '3': 'QSPI_D2', '4': 'GND', '5': 'QSPI_D0', '6': 'QSPI_CLK',
       '7': 'QSPI_D3', '8': '+3V3D'}, mpn='W25Q32JVSSIQ')
U.R('10k', 'QSPI_CS_N', '+3V3D')
U.C('100n', '+3V3D', 'GND')
# audio master clocks
U = d.sheet('clocks', 'Audio master clocks, I2S, LEDs', 2, notes=(
    'CLOCKS / I2S\n'
    '- X202 24.576 MHz (48 kHz family) and X203 22.5792 MHz (44.1 kHz family), selected by U205 (MCLK_SEL = 0 -> 48k).\n'
    '- Mux output fans out through 22R to XMOS, DAC and ADC. XMOS drives BCLK / LRCK / DOUT through 33R.'))
U.add('Oscillator:ASE-xxxMHz', '24.576MHz', {'1': '+3V3A', '2': 'GND', '3': 'MCLK_48', '4': '+3V3A'},
      mpn='NZ2520SDA-24.576M (low phase noise)')
U.add('Oscillator:ASE-xxxMHz', '22.5792MHz', {'1': '+3V3A', '2': 'GND', '3': 'MCLK_44', '4': '+3V3A'},
      mpn='NZ2520SDA-22.5792M (low phase noise)')
U.C('100n', '+3V3A', 'GND')
U.C('100n', '+3V3A', 'GND')
U.add('74xGxx:74LVC1G3157', '74LVC1G3157',
      {'1': 'MCLK_44', '3': 'MCLK_48', '4': 'MCLK_MUX', '6': 'MCLK_SEL', '2': 'GND', '5': '+3V3A'},
      fp='Package_TO_SOT_SMD:SOT-363_SC-70-6', mpn='SN74LVC1G3157DCKR')
U.C('100n', '+3V3A', 'GND')
U.R('22R', 'MCLK_MUX', 'MCLK_XMOS')
U.R('22R', 'MCLK_MUX', 'MCLK_DAC')
U.R('22R', 'MCLK_MUX', 'MCLK_ADC')
U.R('33R', 'X_BCLK', 'I2S_BCLK')
U.R('33R', 'X_LRCK', 'I2S_LRCK')
U.R('33R', 'X_DOUT', 'I2S_DOUT')
U.R('330R', 'LED_PWR', 'LED_PWR_A')
U.add('Device:LED', 'green', {'1': 'GND', '2': 'LED_PWR_A'}, fp=LED0805)
U.R('330R', 'LED_ERR', 'LED_ERR_A')
U.add('Device:LED', 'red', {'1': 'GND', '2': 'LED_ERR_A'}, fp=LED0805)

# =============================================================== DAC ======
D = d.sheet('dac', 'DAC (PCM1794A)', 3, notes=(
    'DAC NOTES\n'
    '- U301 PCM1794A (hardware control). Output 7.8 mA p-p per pin around ~-6.2 mA.\n'
    '- I/V 750R: 5.85 V p-p per leg around +4.65 V. Diff stage gain 0.5 -> ~2.07 Vrms single-ended.\n'
    '  Diff stage inputs are swapped (P from IOUT-, N from IOUT+) so the output is non-inverted.\n'
    '- FMT0/FMT1 straps: fit pull-down OR pull-up per PCM1794A datasheet Table for 24-bit I2S (VERIFY).\n'
    '- 4.7 uF film caps block DC into the volume pot. Use 0.1 % resistors in the diff stage.'))

D.add('Audio:PCM1794A', 'PCM1794A',
      {'23': '+5VA', '28': '+5VA', '15': '+5VA', '9': '+3V3A', '19': 'GND', '24': 'GND', '27': 'GND',
       '16': 'GND', '8': 'GND', '22': 'VCOML', '21': 'VCOMR', '20': 'IREF', '7': 'MCLK_DAC',
       '6': 'I2S_BCLK', '4': 'I2S_LRCK', '5': 'I2S_DOUT', '14': 'DAC_RST_N', '10': 'DAC_MUTE',
       '1': 'GND', '2': 'GND', '3': 'GND', '11': 'DAC_FMT0', '12': 'DAC_FMT1',
       '25': 'IL_P', '26': 'IL_N', '17': 'IR_P', '18': 'IR_N'}, mpn='PCM1794ADBR')
for net in ('+5VA', '+5VA', '+5VA', '+3V3A'):
    D.C('10u', net, 'GND', fp=C0805)
    D.C('100n', net, 'GND')
D.C('10u', 'VCOML', 'GND', fp=C0805)
D.C('10u', 'VCOMR', 'GND', fp=C0805)
D.R('16k', 'IREF', 'GND')
D.R('10k', 'DAC_RST_N', 'GND')
D.R('10k', 'DAC_MUTE', '+3V3A')
D.R('10k', 'DAC_FMT0', 'GND', desc='format strap - verify')
D.R('10k', 'DAC_FMT0', '+3V3A', dnp=True, desc='format strap - verify')
D.R('10k', 'DAC_FMT1', 'GND', desc='format strap - verify')
D.R('10k', 'DAC_FMT1', '+3V3A', dnp=True, desc='format strap - verify')

OPA = 'Amplifier_Operational:OPA1612AxD'
D = d.sheet('dac_iv', 'DAC I/V stage, output filter, volume', 3, notes=(
    'I/V AND OUTPUT\n'
    '- I/V 750R || 2.2n per leg: 5.85 V p-p around +4.65 V. Diff stage gain 0.5 -> ~2.07 Vrms single-ended.\n'
    '- Diff stage inputs are crossed (P from IOUT-, N from IOUT+) so the output is not inverted.\n'
    '- 4.7 uF film caps block DC into the volume pot. Use 0.1 % resistors in the diff stage.'))
for ch in ('L', 'R'):
    D.add(OPA, 'OPA1612', {'2': 'I%s_P' % ch, '3': 'GND', '1': 'V%s_P' % ch,
                           '6': 'I%s_N' % ch, '5': 'GND', '7': 'V%s_N' % ch,
                           '8': '+16V', '4': '-16V'}, fp=SO8, mpn='OPA1612AIDR')
    for leg in ('P', 'N'):
        D.R('750R 0.1%', 'V%s_%s' % (ch, leg), 'I%s_%s' % (ch, leg))
        D.C('2.2n C0G', 'V%s_%s' % (ch, leg), 'I%s_%s' % (ch, leg))
    D.C('100n', '+16V', 'GND')
    D.C('100n', '-16V', 'GND')
D.add(OPA, 'OPA1612', {'3': 'DL_P', '2': 'DL_N', '1': 'DAC_L_OUT', '5': 'DR_P', '6': 'DR_N', '7': 'DAC_R_OUT',
                       '8': '+16V', '4': '-16V'}, fp=SO8, mpn='OPA1612AIDR')
D.C('100n', '+16V', 'GND')
D.C('100n', '-16V', 'GND')
for ch in ('L', 'R'):
    D.R('2.00k 0.1%', 'V%s_N' % ch, 'D%s_P' % ch)
    D.R('1.00k 0.1%', 'D%s_P' % ch, 'GND')
    D.C('1.5n C0G', 'D%s_P' % ch, 'GND')
    D.R('2.00k 0.1%', 'V%s_P' % ch, 'D%s_N' % ch)
    D.R('1.00k 0.1%', 'D%s_N' % ch, 'DAC_%s_OUT' % ch)
    D.C('1.5n C0G', 'D%s_N' % ch, 'DAC_%s_OUT' % ch)
    D.add('Device:C', '4.7u film', {'1': 'DAC_%s_OUT' % ch, '2': 'POT_%s' % ch}, fp=FILM, rot=90,
          mpn='WIMA MKS4 4.7uF 63V')
D.add('Device:R_Potentiometer_Dual', '10k log dual',
      {'1': 'POT_L', '2': 'HP_IN_L', '3': 'GND', '4': 'POT_R', '5': 'HP_IN_R', '6': 'GND'},
      fp='Potentiometer_THT:Potentiometer_Alps_RK097_Dual_Horizontal', mpn='ALPS RK097 dual 10k log (A)')

# =========================================================== HP AMP =======
H = d.sheet('hpamp', 'Headphone amplifier', 4, notes=(
    'HEADPHONE AMP NOTES\n'
    '- Per channel: OPA1612 + 2x LME49600 inside the loop, 2.2R ballast each, feedback from OUT_x.\n'
    '- Gain: 1 + 2.00k / (4.02k || 576R) = 4.97 (SW401 closed, High) or 1.50 (open, Low).\n'
    '- 2 W into 32R = 8 Vrms, 354 mA peak (177 mA per LME49600, rated 250 mA).\n'
    '- Relay K401 (NO contacts) connects jacks only when RDRV is high:\n'
    '  ~2-3 s after power-up (220k / 10u on RDRV), released at once if +18V4 sags (U406A), -16V collapses (U406B),\n'
    '  either output has DC beyond about +-0.6 V (Q402/Q403), or XMOS pulls HP_EN low (BAT54 D402).\n'
    '- LME49600 BW pin open = low-power mode (~7.3 mA Iq). Keep each TO-263 tab on >= 4 cm2 copper.'))

H.add(OPA, 'OPA1612', {'3': 'AMP_INL', '2': 'FB_L', '1': 'OA_L', '5': 'AMP_INR', '6': 'FB_R', '7': 'OA_R',
                       '8': '+16V', '4': '-16V'}, fp=SO8, mpn='OPA1612AIDR')
H.C('100n', '+16V', 'GND')
H.C('100n', '-16V', 'GND')
H.add('Switch:SW_DPDT_x2', 'GAIN H/L', {'2': 'GAIN_L', '1': 'GND', '5': 'GAIN_R', '4': 'GND'},
      fp='Button_Switch_SMD:SW_DPDT_CK_JS202011JCQN', mpn='JS202011JCQN')
for ch in ('L', 'R'):
    H.R('100R', 'HP_IN_%s' % ch, 'AMP_IN%s' % ch)
    H.C('470p C0G', 'AMP_IN%s' % ch, 'GND')
    H.R('100k', 'AMP_IN%s' % ch, 'GND')
    H.R('2.00k 0.1%', 'OUT_%s' % ch, 'FB_%s' % ch)
    H.C('22p C0G', 'OUT_%s' % ch, 'FB_%s' % ch)
    H.R('4.02k 0.1%', 'FB_%s' % ch, 'GND')
    H.R('576R 0.1%', 'FB_%s' % ch, 'GAIN_%s' % ch)
    for n in ('1', '2'):
        H.R('47R', 'OA_%s' % ch, 'BIN_%s%s' % (ch, n))
        H.add('Amplifier_Audio:LME49600', 'LME49600',
              {'2': 'BIN_%s%s' % (ch, n), '4': 'BO_%s%s' % (ch, n), '5': '+16V', '3': '-16V'},
              mpn='LME49600TS/NOPB')
        H.R('2.2R 1W', 'BO_%s%s' % (ch, n), 'OUT_%s' % ch, fp=R2512)
        H.C('10u 25V', '+16V', 'GND', fp=C1210)
        H.C('10u 25V', 'GND', '-16V', fp=C1210)
    H.R('10R', 'OUT_%s' % ch, 'ZB_%s' % ch, fp=R0805)
    H.C('100n', 'ZB_%s' % ch, 'GND')
H.CP('220u 25V', '+16V', 'GND', fp=CP10)
H.CP('220u 25V', 'GND', '-16V', fp=CP10)

H = d.sheet('hp_protect', 'Output relay, protection, headphone jacks', 4, notes=(
    'PROTECTION\n'
    '- Relay K401 (NO contacts) connects the jacks only when RDRV is high: ~2-3 s after power-up (220k / 10u),\n'
    '  released at once if +18V4 sags (U406A), -16V collapses (U406B), either output has DC beyond about\n'
    '  +-0.6 V (Q402 / Q403), or the XMOS pulls HP_EN low (BAT54 D402).'))

H.add('Relay:G6K-2', 'G6K-2F-Y 3VDC',
      {'1': '+3V3D', '8': 'RLY_DRV', '3': 'OUT_L', '4': 'HPJ_L', '6': 'OUT_R', '5': 'HPJ_R'},
      fp='Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y', mpn='G6K-2F-Y DC3')
H.add('Diode:1N4148W', '1N4148W', {'1': '+3V3D', '2': 'RLY_DRV'}, fp=SOD123)
H.add('Transistor_FET:2N7002', '2N7002', {'1': 'RLY_G', '3': 'RLY_DRV', '2': 'GND'}, mpn='2N7002')
H.R('1k', 'RDRV', 'RLY_G')
H.R('220k', '+3V3D', 'RDRV')
H.C('10u', 'RDRV', 'GND', fp=C0805)
H.add('Device:D_Schottky', 'BAT54', {'1': 'HP_EN', '2': 'RDRV'}, fp=SOD123, mpn='BAT54W')
H.add('Comparator:LM393', 'LM393',
      {'3': 'MON_P18', '2': 'VREF_1V65', '1': 'RDRV', '5': 'VREF_1V65', '6': 'MON_N16', '7': 'RDRV',
       '8': '+3V3D', '4': 'GND'}, fp=SO8, mpn='LM393DR')
H.C('100n', '+3V3D', 'GND')
H.R('100k', '+18V4', 'MON_P18')
H.R('10.7k', 'MON_P18', 'GND')
H.R('100k', '-16V', 'MON_N16')
H.R('16.9k', '+3V3D', 'MON_N16')
H.R('10k', '+3V3D', 'VREF_1V65')
H.R('10k', 'VREF_1V65', 'GND')
H.C('100n', 'VREF_1V65', 'GND')
H.R('47k', 'OUT_L', 'DCSUM')
H.R('47k', 'OUT_R', 'DCSUM')
H.CP('47u 25V', 'DCSUM', 'DCMID', fp=CP8)
H.CP('47u 25V', 'GND', 'DCMID', fp=CP8)
H.R('10k', 'DCSUM', 'DCB')
H.add('Transistor_BJT:BC847', 'BC847', {'1': 'DCB', '2': 'GND', '3': 'RDRV'}, mpn='BC847B')
H.R('10k', 'DCSUM', 'DCE')
H.add('Transistor_BJT:BC847', 'BC847', {'1': 'GND', '2': 'DCE', '3': 'RDRV'}, mpn='BC847B')
H.add('Connector_Audio:AudioJack3', '6.35mm', {'T': 'HPJ_L', 'R': 'HPJ_R', 'S': 'GND'},
      fp='Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal', mpn='NMJ6HCD2')
H.add('Connector_Audio:AudioJack3', '3.5mm', {'T': 'HPJ_L', 'R': 'HPJ_R', 'S': 'GND'},
      fp='Connector_Audio:Jack_3.5mm_CUI_SJ1-3533NG_Horizontal', mpn='SJ1-3533NG')

# ============================================================== MIC =======
M = d.sheet('mic', 'Microphone input, phantom feed, preamp', 5, notes=(
    'MIC INPUT NOTES\n'
    '- P48 phantom per IEC 61938: 6.81k 0.1 % matched feed pair, open-circuit ~48.6 V. SW501 switches it.\n'
    '- Hot-plug protection: 10R series + 1N4004 clamps to the +-16V rails + SMBJ18CA TVS on the rails.\n'
    '- U501 THAT1512: G = 0.5 + 5k / (5.1R + RV501) -> 0 dB to ~60 dB. 4700u cap blocks DC in the gain leg.\n'
    '- U502 makes a differential signal: 1 Vrms at PRE_OUT = 2 Vrms differential = 0 dBFS on CS5361\n'
    '  (full scale = 1.13 x VA = 5.65 V p-p differential at VA = 5 V).\n'
    '- U503 CS5361 slave mode, I2S, HPF on. M0/M1 speed mode set by XMOS per sample rate.\n'
    '  Unused right channel tied to VQ. OVFL drives the clip LED.\n'
    '- VERIFY: CS5361 FILT+/VQ capacitor values and input RC against the datasheet.'))

M.add('Connector_Audio:XLR3_AudioJack3_Combo_Ground', 'NCJ6FI-H',
      {'1': 'GND', '2': 'XLR_HOT', '3': 'XLR_COLD', 'G': 'CHASSIS'},
      fp='Connector_Audio:Jack_XLR-6.35mm_Neutrik_NCJ6FI-H_Horizontal', mpn='NCJ6FI-H')
M.FB('600R@100MHz', 'XLR_HOT', 'MIC_P')
M.FB('600R@100MHz', 'XLR_COLD', 'MIC_N')
M.C('100p C0G', 'MIC_P', 'GND')
M.C('100p C0G', 'MIC_N', 'GND')
M.C('470p C0G', 'MIC_P', 'MIC_N')
M.add('Switch:SW_SPST', '+48V', {'1': '+48V', '2': 'P48_SW'}, fp='Button_Switch_THT:SW_Slide_SPDT_Straight_CK_OS102011MS2Q',
      mpn='SPST latching (panel)')
M.R('47R', 'P48_SW', 'P48')
M.CP('47u 63V', 'P48', 'GND', fp=CP10)
M.R('22k', 'P48', 'P48_LED')
M.add('Device:LED', 'red 48V', {'1': 'GND', '2': 'P48_LED'}, fp=LED0805)
M.R('6.81k 0.1%', 'P48', 'MIC_P', fp=R0805, desc='phantom feed, matched pair')
M.R('6.81k 0.1%', 'P48', 'MIC_N', fp=R0805, desc='phantom feed, matched pair')
M.CP('47u 63V', 'MIC_P', 'PRE_P', fp=CP10)
M.CP('47u 63V', 'MIC_N', 'PRE_N', fp=CP10)
M.R('2.21k', 'PRE_P', 'GND')
M.R('2.21k', 'PRE_N', 'GND')
M.R('10R', 'PRE_P', 'THAT_P', fp=R0805)
M.R('10R', 'PRE_N', 'THAT_N', fp=R0805)
for n in ('THAT_P', 'THAT_N'):
    M.add('Diode:1N4004', '1N4004', {'1': '+16V', '2': n}, mpn='1N4004')
    M.add('Diode:1N4004', '1N4004', {'1': n, '2': '-16V'}, mpn='1N4004')
M.add('Device:D_TVS', 'SMBJ18CA', {'1': '+16V', '2': 'GND'}, fp=SMB, mpn='SMBJ18CA')
M.add('Device:D_TVS', 'SMBJ18CA', {'1': 'GND', '2': '-16V'}, fp=SMB, mpn='SMBJ18CA')
M.R('10R', '+16V', '+16V_MIC', fp=R0805)
M.CP('220u 25V', '+16V_MIC', 'GND', fp=CP10)
M.R('10R', '-16V', '-16V_MIC', fp=R0805)
M.CP('220u 25V', 'GND', '-16V_MIC', fp=CP10)
M.add('Amplifier_Audio:THAT151xx08', 'THAT1512S08',
      {'3': 'THAT_P', '2': 'THAT_N', '1': 'RG_A', '8': 'RG_B', '5': 'GND', '6': 'PRE_OUT',
       '7': '+16V_MIC', '4': '-16V_MIC'}, fp=SO8, mpn='THAT1512S08-U')
M.C('100n', '+16V_MIC', 'GND')
M.C('100n', '-16V_MIC', 'GND')
M.R('5.1R', 'RG_A', 'RG_C')
M.add('Device:R_Potentiometer', '10k rev-log (C)', {'1': 'RG_C', '2': 'RG_D', '3': 'RG_D'},
      fp='Potentiometer_THT:Potentiometer_Alps_RK097_Single_Horizontal', mpn='10k C-taper')
M.CP('4700u 6.3V', 'RG_D', 'RG_B', fp=CP10, desc='gain-leg DC block')
M = d.sheet('adc', 'ADC driver and ADC (CS5361)', 5, notes=(
    'ADC\n'
    '- U502 makes a differential signal: 1 Vrms at PRE_OUT = 2 Vrms differential = 0 dBFS on the CS5361\n'
    '  (full scale = 1.13 x VA = 5.65 V p-p differential at VA = 5 V).\n'
    '- U503 CS5361: slave mode, I2S, HPF on. M0/M1 speed mode set by XMOS per sample rate.\n'
    '  Unused right channel tied to VQ. OVFL drives the clip LED.\n'
    '- VERIFY: CS5361 FILT+/VQ capacitor values and input RC against the datasheet.'))

M.add(OPA, 'OPA1612', {'3': 'PRE_OUT', '2': 'DRV_P', '1': 'DRV_P', '5': 'GND', '6': 'INV_N', '7': 'DRV_N',
                       '8': '+16V_MIC', '4': '-16V_MIC'}, fp=SO8, mpn='OPA1612AIDR')
M.C('100n', '+16V_MIC', 'GND')
M.C('100n', '-16V_MIC', 'GND')
M.R('2.00k 0.1%', 'PRE_OUT', 'INV_N')
M.R('2.00k 0.1%', 'INV_N', 'DRV_N')
M.C('47p C0G', 'INV_N', 'DRV_N')
M.CP('22u 25V NP', 'DRV_P', 'AINP_B', fp=CP8, desc='bipolar audio electrolytic')
M.CP('22u 25V NP', 'DRV_N', 'AINN_B', fp=CP8, desc='bipolar audio electrolytic')
M.R('100k', 'AINP_B', 'VQ')
M.R('100k', 'AINN_B', 'VQ')
M.R('49.9R', 'AINP_B', 'AINL_P')
M.R('49.9R', 'AINN_B', 'AINL_N')
M.C('2.7n C0G', 'AINL_P', 'AINL_N')
M.add('Diode:BAT54S', 'BAT54S', {'1': 'GND', '2': '+5VA', '3': 'AINL_P'}, mpn='BAT54S')
M.add('Diode:BAT54S', 'BAT54S', {'1': 'GND', '2': '+5VA', '3': 'AINL_N'}, mpn='BAT54S')
M.add('Audio:CS5361', 'CS5361',
      {'19': '+5VA', '6': '+3V3A', '8': '+3V3A', '7': 'GND', '18': 'GND', '23': 'GND', '24': 'FILT',
       '22': 'VQ', '16': 'AINL_P', '17': 'AINL_N', '21': 'VQ', '20': 'VQ', '5': 'MCLK_ADC',
       '3': 'I2S_LRCK', '4': 'I2S_BCLK', '9': 'I2S_DIN', '1': 'ADC_RST_N', '2': 'GND', '12': '+3V3A',
       '11': 'GND', '10': 'GND', '13': 'ADC_M0', '14': 'ADC_M1', '15': 'ADC_OVFL'},
      fp='Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm', mpn='CS5361-KZZ')
M.C('47u', 'FILT', 'GND', fp=C1206)
M.C('100n', 'FILT', 'GND')
M.C('10u', 'VQ', 'GND', fp=C0805)
M.C('100n', 'VQ', 'GND')
M.C('10u', '+5VA', 'GND', fp=C0805)
M.C('100n', '+5VA', 'GND')
M.C('100n', '+3V3A', 'GND')
M.C('100n', '+3V3A', 'GND')
M.R('10k', 'ADC_RST_N', 'GND')
M.R('10k', 'ADC_M0', 'GND')
M.R('10k', 'ADC_M1', 'GND')
M.R('1k', '+3V3A', 'CLIP_A')
M.add('Device:LED', 'red CLIP', {'1': 'ADC_OVFL', '2': 'CLIP_A'}, fp=LED0805)

d.root_notes = (
    'ALL-IN-ONE AUDIO INTERFACE - schematic rev A (generated by hardware/schematic/design.py)\n'
    'USB-C UAC2 (XMOS XU316) | PCM1794A DAC | headphone amp >= 2 W @ 32R (OPA1612 + 2x LME49600 per ch)\n'
    'XLR mic input: THAT1512 preamp 0-60 dB, switchable +48 V phantom, CS5361 ADC\n'
    'Nets are joined by labels: global labels across sheets, local labels within a sheet.\n'
    'See docs/design.md for the full description and the list of items to verify before layout.')

if __name__ == '__main__':
    d.write(OUT)
    write_bom(d, os.path.join(os.path.dirname(OUT), '..', 'bom.csv'))
    print('wrote', OUT, 'and hardware/bom.csv')
