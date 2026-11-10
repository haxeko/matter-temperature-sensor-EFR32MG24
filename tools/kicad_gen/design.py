"""
Nguồn dữ liệu duy nhất cho project KiCad: linh kiện, net, vị trí trên schematic và PCB.

Biến thể A (khuyến nghị): EFR32MG24B010F1536IM40 chip trần, SHT40, CR2450, bo Ø35 mm 4 lớp.
Sơ đồ chân MG24 QFN40 lấy từ datasheet EFR32MG24 Rev 1.1, Table 6.3 (QFN40 / Standard).

Quy ước net: "GND" = ký hiệu nguồn GND; GLOBAL_NETS dùng global label; còn lại là label cục bộ.
NC = chân không nối (đặt dấu no-connect).
"""

NC = None
GLOBAL_NETS = {"VBAT", "VDCDC"}
# Net nối bằng dây thật trên schematic (chuỗi RF), thay vì nhãn ở mỗi chân
WIRED_NETS = {"RF_M1", "RF_M2", "RF_50", "ANT_FEED"}

# ---------------------------------------------------------------------------
# EFR32MG24B010F1536IM40 (QFN40 Standard): số chân -> (tên, loại điện, net)
# ---------------------------------------------------------------------------
MG24_PINS = {
    1: ("PC00", "bidirectional", NC),
    2: ("PC01", "bidirectional", "LED_K"),
    3: ("PC02", "bidirectional", "I2C_SDA"),
    4: ("PC03", "bidirectional", "I2C_SCL"),
    5: ("PC04", "bidirectional", "PTI_DATA"),
    6: ("PC05", "bidirectional", "PTI_FRAME"),
    7: ("PC06", "bidirectional", NC),
    8: ("PC07", "bidirectional", NC),
    9: ("HFXTAL_I", "input", "HFXO_I"),
    10: ("HFXTAL_O", "output", "HFXO_O"),
    11: ("RESETn", "input", "RESETn"),
    12: ("RFVDD", "power_in", "VDCDC"),
    13: ("RFVSS", "power_in", "GND"),
    14: ("RF2G4_IO", "bidirectional", "RF_IO"),
    15: ("PAVDD", "power_in", "VDCDC"),
    16: ("PB04", "bidirectional", NC),
    17: ("PB03", "bidirectional", NC),
    18: ("PB02", "bidirectional", NC),
    19: ("PB01", "bidirectional", "BTN"),        # EM2 wake (cổng B), EM4WU3
    20: ("PB00", "bidirectional", NC),
    21: ("PA00", "bidirectional", NC),
    22: ("PA01", "bidirectional", "SWCLK"),
    23: ("PA02", "bidirectional", "SWDIO"),
    24: ("PA03", "bidirectional", "SWO"),
    25: ("PA04", "bidirectional", NC),
    26: ("PA05", "bidirectional", "VCOM_TX"),
    27: ("PA06", "bidirectional", "VCOM_RX"),
    28: ("PA07", "bidirectional", NC),
    29: ("PA08", "bidirectional", NC),
    30: ("DECOUPLE", "power_out", "DECOUPLE"),
    31: ("VREGSW", "power_out", "DCDC_SW"),
    32: ("VREGVDD", "power_in", "VBAT"),
    33: ("VREGVSS", "power_in", "GND"),
    34: ("DVDD", "power_in", "VDCDC"),
    35: ("AVDD", "power_in", "VBAT"),            # AVDD = VBAT -> IADC đo AVDD/4 = áp pin
    36: ("IOVDD", "power_in", "VBAT"),
    37: ("PD03", "bidirectional", NC),
    38: ("PD02", "bidirectional", NC),
    39: ("PD01", "bidirectional", "LFXO_I"),     # LFXTAL_I
    40: ("PD00", "bidirectional", "LFXO_O"),     # LFXTAL_O
    41: ("VSS", "power_in", "GND"),              # exposed pad
}

# Bố cục chân trên symbol tuỳ biến (từ trên xuống, None = khoảng trống)
MG24_LEFT = [32, 35, 36, 34, 12, 15, 30, 31, None, 11, None, 9, 10, None, 40, 39, 38, 37]
MG24_RIGHT = [14, None, 21, 22, 23, 24, 25, 26, 27, 28, 29, None, 20, 19, 18, 17, 16, None,
              1, 2, 3, 4, 5, 6, 7, 8]
MG24_BOTTOM = [33, 13, 41]

FP_STD = "/usr/share/kicad/footprints"

# ---------------------------------------------------------------------------
# Linh kiện
#   sch: (x, y, rot) trên schematic A3 (mm); pcb: (x, y, rot, side) so với tâm bo (mm, y xuống)
#   pins: số chân -> net
# ---------------------------------------------------------------------------
def part(ref, lib_id, value, footprint, pins, sch, pcb, mpn="", mfr="", lcsc="", dnp=False, note="", spec="",
         virtual=False):
    return dict(ref=ref, lib_id=lib_id, value=value, footprint=footprint, pins=pins, sch=sch, pcb=pcb,
                mpn=mpn, mfr=mfr, lcsc=lcsc, dnp=dnp, note=note, spec=spec, virtual=virtual)


C0201 = "Capacitor_SMD:C_0201_0603Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
R0402 = "Resistor_SMD:R_0402_1005Metric"
L0201 = "Inductor_SMD:L_0201_0603Metric"

PARTS = [
    # ---------------- Nguồn ----------------
    part("BT1", "Device:Battery_Cell", "CR2450", "tsensor:BatteryClip_MYOUNG_MY-2450-03_CR2450",
         {"1": "BAT_P", "2": "GND"}, (38.1, 63.5, 0), (0.0, 2.0, 0, "B"),
         mpn="MY-2450-03", mfr="MYOUNG", lcsc="C2988622",
         note="Kẹp (+) SMD mặt sau; cực (−) là pad ENIG trên PCB"),
    part("Q1", "Device:Q_PMOS_GSD", "DMP2035U-7", "Package_TO_SOT_SMD:SOT-23",
         {"1": "Q1_G", "2": "VBAT", "3": "BAT_P"}, (68.58, 63.5, 0), (11.0, 0.9, 90, "F"),
         mpn="DMP2035U-7", mfr="Diodes Inc", lcsc="C110499", note="Chống cắm ngược: D->pin, S->VBAT, G->GND"),
    part("R5", "Device:R", "10k", R0402, {"1": "Q1_G", "2": "GND"}, (55.88, 76.2, 0), (11.0, -2.0, 0, "F"),
         mpn="0402WGF1002TCE", mfr="UNI-ROYAL", lcsc="C25744"),
    part("C1", "Device:C", "100uF", C1206, {"1": "VBAT", "2": "GND"}, (91.44, 63.5, 0),
         (8.0, 5.8, 90, "F"), mpn="CL31A107MQHNNNE", mfr="Samsung", lcsc="C15008", note="Tụ dự trữ cho xung RF", spec="6.3V X5R 1206"),
    part("C2", "Device:C", "100uF", C1206, {"1": "VBAT", "2": "GND"}, (101.6, 63.5, 0),
         (10.9, 5.8, 90, "F"), mpn="CL31A107MQHNNNE", mfr="Samsung", lcsc="C15008", spec="6.3V X5R 1206"),
    part("C3", "Device:C", "4.7uF", C0603, {"1": "VBAT", "2": "GND"}, (111.76, 63.5, 0),
         (-1.0, 3.1, 0, "F"), mpn="TCC0603X7R475K6R3CT", mfr="TCC", lcsc="C5360855", note="CIN tại VREGVDD", spec="6.3V X7R 0603"),
    part("L1", "Device:L", "2.2uH", "Inductor_SMD:L_1008_2520Metric", {"1": "DCDC_SW", "2": "VDCDC"},
         (132.08, 63.5, 0), (-3.6, 0.9, 0, "F"), mpn="DFE2HCAH2R2MJ0L", mfr="Murata", lcsc="C2043106",
         note="Cuộn DC-DC (datasheet: 2,2 µH)", spec="Isat 2.5A DCR 0.1R 1008"),
    part("C4", "Device:C", "4.7uF", C0603, {"1": "VDCDC", "2": "GND"}, (144.78, 63.5, 0),
         (-6.6, 0.9, 90, "F"), mpn="TCC0603X7R475K6R3CT", mfr="TCC", lcsc="C5360855", note="CDCDC 4,7 µF X7R", spec="6.3V X7R 0603"),
    part("C5", "Device:C", "100nF", C0402, {"1": "VBAT", "2": "GND"}, (91.44, 91.44, 0), (-0.05, 0.5, 90, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="AVDD"),
    part("C6", "Device:C", "100nF", C0402, {"1": "VBAT", "2": "GND"}, (101.6, 91.44, 0), (0.95, 0.5, 90, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="IOVDD"),
    part("C7", "Device:C", "100nF", C0402, {"1": "VDCDC", "2": "GND"}, (121.92, 91.44, 0), (-1.05, 0.5, 90, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="DVDD"),
    part("C8", "Device:C", "100nF", C0402, {"1": "VDCDC", "2": "GND"}, (132.08, 91.44, 0), (2.4, -7.45, 0, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="RFVDD"),
    part("C9", "Device:C", "100nF", C0402, {"1": "VDCDC", "2": "GND"}, (142.24, 91.44, 0), (-2.4, -7.45, 0, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="PAVDD"),
    part("C10", "Device:C", "1uF", C0402, {"1": "DECOUPLE", "2": "GND"}, (157.48, 91.44, 0), (-3.9, -2.6, 90, "F"),
         mpn="CL05A105KA5NQNC", mfr="Samsung", lcsc="C52923", note="DECOUPLE (datasheet: 1,0 µF, tối đa 2,75 µF)"),

    # ---------------- SoC ----------------
    part("U1", "tsensor:EFR32MG24B010F1536IM40", "EFR32MG24B010F1536IM40",
         "tsensor:EFR32MG24_QFN40_5x5mm_P0.4mm_EP3.85x3.85mm",
         {str(k): v[2] for k, v in MG24_PINS.items()}, (210.82, 142.24, 0), (0.0, -3.7, 180, "F"),
         mpn="EFR32MG24B010F1536IM40-B", mfr="Silicon Labs", lcsc="C6033375"),

    # ---------------- Clock ----------------
    part("Y1", "Device:Crystal_GND24", "39MHz", "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm",
         {"1": "HFXO_I", "2": "GND", "3": "HFXO_O", "4": "GND"}, (63.5, 137.16, 0), (4.6, -4.7, 90, "F"),
         mpn="TZ3541C", mfr="TST", lcsc="C5360883", note="Không tụ tải ngoài (CTUNE nội)", spec="CL 10pF ESR<=60R 2016"),
    part("Y2", "Device:Crystal", "32.768kHz", "Crystal:Crystal_SMD_2012-2Pin_2.0x1.2mm",
         {"1": "LFXO_I", "2": "LFXO_O"}, (63.5, 160.02, 0), (3.0, 0.6, 0, "F"),
         mpn="FC-12M 32.768kHz 9pF", mfr="Epson", lcsc="C96341", note="CL ≤ 12 pF -> không tụ ngoài", spec="CL 9pF 2012"),

    # ---------------- RF ----------------
    part("L2", "Device:L", "2.5nH", L0201, {"1": "RF_IO", "2": "RF_M1"}, (289.56, 60.96, 90), (0.6, -8.4, 180, "F"),
         mpn="LQP03HQ2N5B02D", mfr="Murata", lcsc="C237441", note="VERIFY: giá trị theo BRD4186C (QFN48)"),
    part("C11", "Device:C", "2.3pF", C0201, {"1": "RF_M1", "2": "GND"}, (299.72, 71.12, 0), (-0.1, -9.55, 0, "F"),
         mpn="GRM0335C1H2R3WA01D", mfr="Murata", lcsc="C710810", note="VERIFY", spec="C0G 0201"),
    part("L3", "Device:L", "1.7nH", L0201, {"1": "RF_M1", "2": "RF_M2"}, (309.88, 60.96, 90), (-0.85, -8.4, 180, "F"),
         mpn="LQP03HQ1N7B02D", mfr="Murata", lcsc="C2041495", note="VERIFY"),
    part("C12", "Device:C", "1.6pF", C0201, {"1": "RF_M2", "2": "GND"}, (320.04, 71.12, 0), (-1.55, -9.55, 0, "F"),
         mpn="GRM0335C1H1R6WA01D", mfr="Murata", lcsc="C1864525", note="VERIFY", spec="C0G 0201"),
    part("C13", "Device:C", "18pF", C0201, {"1": "RF_M2", "2": "RF_50"}, (330.2, 60.96, 90), (-2.3, -8.4, 180, "F"),
         mpn="GRM0335C1H180JA01D", mfr="Murata", lcsc="C85892", note="Tụ chặn DC", spec="C0G 0201"),
    part("C14", "Device:C", "DNP", C0402, {"1": "RF_50", "2": "GND"}, (340.36, 71.12, 0), (-3.2, -9.55, 0, "F"),
         dnp=True, note="π tinh chỉnh anten (shunt 1) — chỉnh bằng VNA"),
    part("R1", "Device:R", "0R", R0402, {"1": "RF_50", "2": "ANT_FEED"}, (350.52, 60.96, 90), (-3.95, -8.4, 180, "F"),
         mpn="0402WGF0000TCE", mfr="UNI-ROYAL", lcsc="C17168", note="π tinh chỉnh anten (series)"),
    part("C15", "Device:C", "DNP", C0402, {"1": "ANT_FEED", "2": "GND"}, (360.68, 71.12, 0), (-5.6, -8.4, 270, "F"),
         dnp=True, note="π tinh chỉnh anten (shunt 2)"),
    part("ANT1", "Device:Antenna_Shield", "PCB IFA 2.4GHz", "tsensor:PCB_Antenna_IFA_2G4_TI-AN043",
         {"1": "ANT_FEED", "2": "GND"}, (381.0, 55.88, 0), (0.0, -10.1, 0, "F"), virtual=True,
         note="Anten đồng trên PCB: meander IFA theo TI AN043 (15,2 × 5,7 mm), chân 2 nối GND qua via"),

    # ---------------- Cảm biến ----------------
    part("U2", "Sensor_Humidity:SHT4x", "SHT40-AD1B", "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
         {"1": "I2C_SDA", "2": "I2C_SCL", "3": "VBAT", "4": "GND"}, (330.2, 147.32, 0), (0.0, 15.6, 180, "F"),
         mpn="SHT40-AD1B-R3", mfr="Sensirion", lcsc="C2848306", note="Trên lưỡi PCB có khe phay"),
    part("C16", "Device:C", "100nF", C0402, {"1": "VBAT", "2": "GND"}, (350.52, 147.32, 0), (0.0, 10.5, 180, "F"),
         mpn="CL05B104KO5NNNC", mfr="Samsung", lcsc="C1525", note="Gốc lưỡi cảm biến"),
    part("R2", "Device:R", "10k", R0402, {"1": "VBAT", "2": "I2C_SDA"}, (365.76, 147.32, 0), (5.6, -2.2, 0, "F"),
         mpn="0402WGF1002TCE", mfr="UNI-ROYAL", lcsc="C25744"),
    part("R3", "Device:R", "10k", R0402, {"1": "VBAT", "2": "I2C_SCL"}, (375.92, 147.32, 0), (5.6, -1.1, 0, "F"),
         mpn="0402WGF1002TCE", mfr="UNI-ROYAL", lcsc="C25744"),

    # ---------------- Nút, LED ----------------
    part("SW1", "Switch:SW_Push", "TS-1088", "tsensor:SW_SPST_XUNPU_TS-1088_3.9x3mm",
         {"1": "BTN", "2": "GND"}, (53.34, 213.36, 0), (0.0, 6.6, 0, "F"),
         mpn="TS-1088-AR02016", mfr="XUNPU", lcsc="C720477",
         note="SMD 3,9×3 mm, 2 chân, cao 2,0 mm, 160 gf (Basic JLCPCB)"),
    part("R4", "Device:R", "680", R0402, {"1": "VBAT", "2": "LED_A"}, (101.6, 213.36, 0), (-5.8, 8.2, 0, "F"),
         mpn="0402WGF6800TCE", mfr="UNI-ROYAL", lcsc="C25130"),
    part("D1", "Device:LED", "Red", "LED_SMD:LED_0603_1608Metric", {"1": "LED_K", "2": "LED_A"},
         (124.46, 226.06, 0), (-5.8, 6.4, 180, "F"), mpn="APTD1608LSURCK", mfr="Kingbright", lcsc="C5342734",
         note="LED đỏ AlInGaP: còn sáng ở 2,2 V", spec="AlInGaP 2mA 0603"),

    # ---------------- Debug / test ----------------
    part("J1", "Connector:Conn_ARM_SWD_TagConnect_TC2030", "TC2030-NL",
         "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
         {"1": "VBAT", "2": "SWDIO", "3": "RESETn", "4": "SWCLK", "5": "GND", "6": "SWO"},
         (215.9, 223.52, 0), (-11.8, -8.1, 0, "F"), note="Không cần linh kiện; cáp TC2030-CTX-NL"),
    part("TP1", "Connector:TestPoint", "VBAT", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "VBAT"},
         (248.92, 213.36, 0), (-8.4, 10.4, 0, "F")),
    part("TP2", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "GND"},
         (256.54, 213.36, 0), (-5.4, 12.6, 0, "F")),
    part("TP3", "Connector:TestPoint", "VCOM_TX", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "VCOM_TX"},
         (264.16, 213.36, 0), (-12.6, 2.0, 0, "F")),
    part("TP4", "Connector:TestPoint", "VCOM_RX", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "VCOM_RX"},
         (271.78, 213.36, 0), (-12.6, 4.6, 0, "F")),
    part("TP5", "Connector:TestPoint", "PTI_DATA", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "PTI_DATA"},
         (279.4, 213.36, 0), (5.4, 12.6, 0, "F")),
    part("TP6", "Connector:TestPoint", "PTI_FRAME", "TestPoint:TestPoint_Pad_D1.0mm", {"1": "PTI_FRAME"},
         (287.02, 213.36, 0), (8.4, 10.4, 0, "F")),
]

# Cờ nguồn (PWR_FLAG) cho ERC: net -> vị trí trên schematic
PWR_FLAGS = {"VBAT": (165.1, 43.18), "VDCDC": (177.8, 43.18), "GND": (190.5, 43.18)}

# Khung chữ trên schematic: (x, y, cỡ chữ, nội dung)
SCH_TEXTS = [
    (20.32, 30.48, 2.0, "1. NGUỒN: CR2450 → P-MOSFET chống ngược → VBAT; DC-DC nội MG24 (VREGSW → 2,2 µH → VDCDC)"),
    (20.32, 34.29, 1.27, "VBAT nối VREGVDD, AVDD, IOVDD (IADC đo AVDD/4 = áp pin). VDCDC nối DVDD, RFVDD, PAVDD (PA +10 dBm chạy 1,8 V từ DC-DC)."),
    (20.32, 37.59, 1.27, "Tụ dự trữ 2×100 µF X5R 1206 (~80 µF hiệu dụng ở 3 V) giảm sụt áp khi phát. Không dùng tantalum/polymer (rò cao)."),
    (20.32, 121.92, 2.0, "2. CLOCK: HFXO 39 MHz (CTUNE nội, không tụ ngoài), LFXO 32,768 kHz CL ≤ 12 pF (tụ nội)"),
    (180.34, 99.06, 2.0, "3. SoC EFR32MG24B010F1536IM40 (QFN40, Vault High, +10 dBm, 1536/256 kB)"),
    (270.51, 30.48, 2.0, "4. RF: phối hợp SoC + chặn DC + π tinh chỉnh + anten PCB (IFA)"),
    (270.51, 34.29, 1.27, "VERIFY: giá trị L2/C11/L3/C12 lấy theo BRD4186C (QFN48) — đối chiếu AN930.2 cho QFN40 trước khi đặt hàng."),
    (270.51, 37.59, 1.27, "C14/C15 để trống (DNP), R1 = 0 Ω: tinh chỉnh bằng VNA khi đã có vỏ + pin. CPWG 50 Ω, khâu via GND ≤ 2 mm."),
    (270.51, 121.92, 2.0, "5. CẢM BIẾN SHT40 trên lưỡi PCB (2 khe phay), I2C1 (PC02/PC03)"),
    (20.32, 195.58, 2.0, "6. NÚT (PB01, đánh thức EM2/EM4) và LED đỏ (PC01, kéo xuống)"),
    (180.34, 195.58, 2.0, "7. DEBUG: Tag-Connect TC2030-NL (SWD) + pad test PPK2/VCOM/PTI"),
    (20.32, 248.92, 1.27, "Ghi chú: thiết kế sơ bộ v0.1 — sinh tự động bởi tools/kicad_gen. Xem docs/04-hardware.md, hardware/bom.csv."),
    (20.32, 252.73, 1.27, "Kiểm tra trước khi đặt mạch: mạng phối hợp RF cho QFN40; decoupling theo schematic tham chiếu Silicon Labs; chân SOT-23 của Q1 (G=1,S=2,D=3)."),
]

# ---------------------------------------------------------------------------
# Hình học bo (mm, tâm bo = (0,0), trục y hướng xuống như KiCad)
# ---------------------------------------------------------------------------
BOARD_R = 17.5
TONGUE_ANGLE_DEG = 90.0        # hướng 6 giờ (cảm biến ở mép dưới)
TONGUE_HALF_W = 2.0            # lưỡi rộng 4 mm
SLOT_W = 0.8                   # khe phay 0,8 mm
SLOT_INNER = 11.5              # khe kéo vào tới bán kính 11,5 mm (dọc trục lưỡi)
ANT_KEEPOUT_Y = -10.1          # mép mặt đất của anten PCB: vùng cấm đồng/via mọi lớp y < -10,1
# Theo TI AN043, mặt đất tham chiếu của anten là lớp 2 (ở đây In1.Cu); hai chân anten thò D4 = 0,5 mm xuống
# vùng mặt đất, chân trái nối đất bằng via. Trên F.Cu khoét rãnh không đổ GND quanh hai chân (cách 0,3 mm)
# để GND mặt trên không chạm chân feed.
ANT_LEG_NOTCH_X = (-7.5, -4.1)   # mm, theo toạ độ bo
ANT_LEG_NOTCH_DEPTH = 0.8        # rãnh từ mép mặt đất xuống tới y = ANT_KEEPOUT_Y + 0,8
BOARD_ORIGIN = (150.0, 100.0)  # vị trí tâm bo trên trang PCB
