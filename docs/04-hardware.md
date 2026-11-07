# 4. Phần cứng

> Nhãn: **[DS]** datasheet · **[DIST]** nhà phân phối (LCSC/JLCPCB API, 07/11/2026) · **[KN]** · **[TT]** · **[ĐOÁN]**.
> BOM chi tiết: `hardware/bom.csv`. Sơ đồ bố trí: `hardware/floorplan.svg`.

## 4.1 Chọn cảm biến

| Cảm biến | Sai số typ (max) | VDD | Idle / đo | t đo (typ) | Điện tích/lần đo* | Gói | LCSC, $@100 |
|---|---|---|---|---|---|---|---|
| **SHT40-AD1B** | ±0,2 (±0,4 @0–65) °C; ±1,8 (±3,5) %RH | 1,08–3,6 V | 0,08 (1,0) / 320 µA | 6,9 ms (high) · 1,3 ms (low) | **2,2 µC** | DFN 1,5×1,5; 0x44 | C2848306, 1,22 |
| SHT41-AD1B | ±0,2 (±0,4) °C; ±1,8 (±2,5) %RH | ″ | ″ | ″ | 2,2 µC | ″ | C7461861, 2,17 |
| SHT45-AD1B | **±0,1 (±0,3)** °C; ±1,0 (±2,0) %RH | ″ | ″ | ″ | 2,2 µC | ″ | C5221601, 4,07 |
| SHT4x-AD1F | Như trên + màng polyimide 40 µm (IP68) | | | | | | SHT40F C7461846 |
| STS40 | ±0,2 (±0,4) °C, chỉ nhiệt | 1,08–3,6 V | như SHT4x | 6,9 ms | 2,2 µC | DFN 1,5 | C3663715, 0,38 |
| SHTC3 | ±0,2 (±0,4) °C; ±2 (±3,5) %RH | 1,62–3,6 V | sleep 0,3 / **idle 45** / 430 µA | 10,8 ms | 4,6 µC | DFN 2×2; 0x70 | C194656, 1,48 |
| TI TMP117 | **±0,1 max** (−20…50 °C), chỉ nhiệt | 1,7–5,5 V | 0,15 / 135 µA | 15,5 ms | 2,1 µC | WSON-6 2×2 | C699536, 0,70 |
| TI TMP119 | ±0,08 max (0–45 °C) | 1,7–5,5 V | 0,15 / 135 µA | 15,5 ms | 2,1 µC | DSBGA 0,95×1,49 | C22428347, 2,55 |
| Aosong AHT20 | ±0,3 °C; ±2 %RH | 2,2–5,5 V | 0,2 / 570 µA | **80 ms** | **≈46 µC** | 3×3 | C2757850, 0,53 |
| Bosch BME280 | ±0,5 °C (đo cao hơn môi trường do tự sưởi), ±3 %RH, có áp suất | 1,71–3,6 V | 0,1 / 340–714 µA | 5,5 ms | 2–4 µC | LGA 2,5×2,5 | C92489, 5,72 |
| TE HTU31D | ±0,2 °C; ±2 %RH | **3,0–5,5 V** | | | | DFN 2,5 | **loại**: không chạy được với CR2450 |

\*Điện tích/lần đo = dòng đo × thời gian đo (typ). Ở chu kỳ 30 s, SHT40 chỉ tốn khoảng 0,07 µA trung bình. AHT20 tốn gấp khoảng 20 lần, sai số kém hơn.

**Kết luận: SHT40-AD1B.** Nó tốt nhất về giá, kích thước, năng lượng mỗi lần đo và dải VDD (chạy tới 1,08 V), lại đo cả RH. Nên đo cả độ ẩm: cùng chip, không tốn thêm linh kiện hay năng lượng.
- **SHT45** nếu muốn công bố ±0,1 °C (+2,9 USD). Footprint giống hệt, có thể để tuỳ chọn lắp.
- **TMP117** chỉ đáng dùng khi cần nhiệt độ cấp đo lường mà không cần RH.
- Bản **-AD1F** (màng) dùng cho phòng tắm/bếp/bụi; màng làm phản ứng RH chậm hơn.
- Lưu ý vận hành [DS]: **heater SHT4x kéo 6–100 mA, không dùng với CR2450.** Sau reflow có lệch −1…−2 %RH, tự hồi sau 1–3 ngày.

## 4.2 Nguồn từ CR2450

### Pin và dòng tải

| Pin CR2450 [DS] | Dung lượng | Dòng liên tục / xung | Nội trở | Nhiệt độ |
|---|---|---|---|---|
| Panasonic | 620 mAh | chuẩn 0,2 mA | không công bố | −30…+85 °C |
| Energizer | 620 mAh | — | ≈10 Ω mới → >100 Ω cuối đời | −30…+60 °C |
| Murata CR2450 / CR2450R | 610 / 500 mAh | R: ≤3 mA / xung 50 mA | R: 5/10/15 Ω (23/−20/−40 °C) mới. Ở −20 °C tải 10 mA áp 2,8→2,1 V (≈40–75 Ω) | −30…+70 °C |
| Renata CR2450N | 540 mAh | 0,8 mA, tối đa 3 mA | — | −40…+85 °C |
| Varta 6450 | 620 typ (560 danh định) | 2 mA / **xung 20 mA** | ≈23 Ω mới → ≈40 Ω giữa đời. **Với xung, chạm 2,0 V ở ≈68 % đời pin** | −20…+70 °C |

| Tải của MG24 (3,0 V, DC-DC bật) [DS] | Dòng |
|---|---|
| TX +10 dBm | 19,1 mA |
| TX +8 dBm (nội suy theo mW) [ĐOÁN] | ≈13 mA |
| TX 0 dBm | 5,0 mA |
| RX 802.15.4 / BLE 1M | 5,1 / 4,4 mA |
| EM0 39 MHz | 33,4 µA/MHz ≈ 1,3 mA |
| EM2, giữ 256 kB RAM | 2,9 µA |
| Đánh thức EM2→EM0 / khởi động HFXO | 13,7 µs / 188 µs |

**Dòng đỉnh** (radio + CPU khoảng 1,4 mA): khoảng 20,5 mA ở +10 dBm, khoảng 14,5 mA ở +8 dBm.

### Sụt áp tính theo mô hình RC

Mô hình: R nội trở pin, C = 2×100 µF (≈80 µF hiệu dụng ở 3 V), `ΔV = I·R·(1−e^(−t/RC))`.

| Sụt áp (V) | R = 10 Ω (mới) | 23 Ω | 40 Ω (giữa đời / lạnh) | 100 Ω (cuối đời / −20 °C) |
|---|---|---|---|---|
| Poll 1 ms, +10 dBm | 0,15 | 0,20 | 0,22 | 0,24 |
| Khung 127 B (4,3 ms), +10 dBm | 0,20 | 0,43 | 0,61 | **0,85** |
| Khung 127 B, +8 dBm | 0,14 | 0,30 | 0,43 | 0,60 |
| Khung 127 B, +4 dBm | 0,09 | 0,20 | 0,28 | 0,40 |
| RX liên tục (tìm parent 2 s) | 0,07 | 0,15 | 0,26 | 0,65 |

Ngưỡng của MG24 [DS]:
- DC-DC chỉ **điều áp khi VREGVDD ≥ 2,2 V** ở tải đầy (1,8 V ở tải 5 mA).
- Chế độ **bypass** chạy được 1,8–3,8 V (≤ 60 mA).
- BOD của DVDD ở 1,62–1,65 V.

**Kết luận**:
1. **CR2450 không chịu nổi +10 dBm cố định trong nửa cuối đời pin hoặc khi lạnh.** Với pin 2,8 V và R = 100 Ω, một khung dài làm áp rơi về khoảng 1,95 V: ra ngoài vùng điều áp của DC-DC, gần BOD.
2. Phương án:
   - TX Thread mặc định **+8 dBm**.
   - Firmware **hạ xuống +4 dBm** khi `BatChargeLevel ≥ Warning` hoặc T < 0 °C.
   - BLE commissioning 0…+4 dBm.
   - Tụ dự trữ **2×100 µF X5R 1206**.
   - Không bao giờ dùng heater SHT4x.
   - Theo TI SWRA349, tụ 100 µF song song giúp CR2032 yếu cho thêm > 40 % dung lượng.
3. **Có dùng DC-DC nội không: CÓ.** Nó giảm dòng pin khi phát/thu khoảng 30 % so với LDO (ước tính từ tỉ số 1,8 V/3,0 V và hiệu suất khoảng 85 %). Các số dòng trong datasheet ở trên cũng đã tính với DC-DC bật.
   - Khi VBAT < 2,2–2,3 V, supply monitor (ngưỡng 2,0–2,3 V, SiSDK mặc định 2,3 V) báo ngắt để phần mềm chuyển **bypass**. Datasheet không nói việc chuyển này là tự động **[ĐOÁN: kiểm tra `sl_device_init_dcdc` của SiSDK]**.
   - Ở bypass, radio lấy dòng thẳng từ pin, mất lợi ích DC-DC, dòng pin khi TX tăng khoảng 40 % [ĐOÁN]. Đây là lý do thêm để hạ công suất phát khi pin yếu.
4. **Tụ dự trữ**:
   - MLCC 100 µF 1206 6,3 V X5R (Samsung CL31A107MQHNNNE, C15008, Basic) ×2.
   - DC-bias làm còn khoảng 41 µF/tụ ở 3 V (số liệu Murata GRM31CR60J107ME39).
   - Rò theo spec tối đa lên tới vài µA, thực tế thấp hơn nhiều; **đo ở T1.14**.
   - **Không** dùng tantalum (DCL ≤ 6,3 µA) hay polymer (≤ 63 µA).
   - Siêu tụ/HLC: không đáng (rò ≈ 3–10 µA, kích thước lớn).

## 4.3 Chống cắm ngược pin (P-MOSFET)

```
CR2450(+) ──► D ┌──────┐ S ──► VBAT (sau bảo vệ) ──► tải
                │ Q1   │
                └──┬───┘
                   G ── R5 10 kΩ (hoặc 0 Ω) ── GND        CR2450(−) = pad ENIG = GND
```

- Lắp đúng: diode thân dẫn trước, kéo S lên. Vgs ≈ −VBAT nên kênh dẫn hoàn toàn. Sụt áp = I·Rds(on) ≈ 20 mA × 62 mΩ ≈ **1,2 mV**.
- Lắp ngược: G cao hơn S nên khoá, diode thân phân cực ngược, dòng chỉ là rò.
- **Dòng tĩnh = 0** (cổng nối GND, không có dòng). Không cần gì thêm.
- **Chọn DMP2035U-7** (C110499): −20 V, Vgs(th) −0,4…−1,0 V, Rds(on) ≤ 45 mΩ @−2,5 V và **≤ 62 mΩ @−1,8 V**. Nó được đặc tả ở áp cuối đời pin.
  - Thay thế rẻ, Basic: Si2301CDS (C10487), chỉ đặc tả ở −2,5 V.
  - **Tránh AO3401A**: Vgs(th) tới −1,3 V, sát áp cuối đời.
- Không dùng diode Schottky: mất 0,2–0,3 V (khoảng 10 % dải áp dùng được) và rò ngược cỡ µA khi nóng.

## 4.4 Đo điện áp pin không tốn dòng

- **Không cần cầu chia, không cần công tắc.** IADC của MG24 có đầu vào nội **AVDD/4** (cùng IOVDD/4, DVDD/4) [DS/SDK].
  - Nối **AVDD = VBAT** (sau MOSFET) là đo trực tiếp áp pin.
  - Tham chiếu nội 1,21 V. Toàn thang AVDD/4 ≤ 0,95 V nằm trong dải.
- **Đo lúc có tải**: lấy mẫu vài lần ngay sau một khung phát, giữ min. Chi tiết và thuật toán % ở mục 5.5.
- Sau khi đo, **tắt clock IADC0**. Domain PD0B/PD0D còn bật trong EM2 sẽ tốn thêm +0,93/+1,1 µA [DS].
- Nếu sau này đặt LDO/boost trước AVDD (thiết kế này **không** làm vậy), lúc đó mới cần cầu chia có công tắc high-side P-FET, hoặc cầu chia 10 MΩ có tụ giữ 100 nF.

## 4.5 Mạch RF và anten

### Lựa chọn: anten chip + mạng phối hợp có chỗ tinh chỉnh
```
MG24 RF2G4 ─ [mạng phối hợp SoC: L 2,5 nH · C 2,3 pF · L 1,7 nH · C 1,6 pF] ─ DC-block 18 pF
            ─ CPWG 50 Ω ngắn ─ [π tinh chỉnh: shunt(DNP) · series 0 Ω · shunt(DNP)] ─ Johanson 2450AT18A100E
```
- **Giá trị mạng phối hợp SoC** lấy theo BRD4186C. Số liệu đọc từ trích đoạn manual, **phải đối chiếu AN930.2/schematic** cho đúng gói QFN40 trước khi chốt.
  - Linh kiện: LQP03HQ2N5B02D C237441, LQP03HQ1N7B02D C2041495 (LCSC chỉ còn 4 cái), GRM0335C1H2R3WA01D C710810, GRM0335C1H1R6WA01D C1864525, GRM0335C1H180JA01D C85892.
- **Anten**: Johanson 2450AT18A100E (3,2×1,6 mm, C89334, tồn kho thấp) hoặc 2450AT18D0100002E (C17410360, 915 cái).
  - Đặt **ở mép bo, trong dải không có pin**, theo layout khuyến nghị của Johanson (vùng trống GND, đường feed).
  - BRD2703A và BRD2601B của Silicon Labs cũng dùng anten chip. BRD4186C dùng inverted-F in trên PCB, nhưng IFA cần khoảng 20 mm chiều dài, không vừa dải 8,75 mm.
- **Vùng cấm đồng**: mọi lớp dưới và quanh anten. Không linh kiện, không via trong vùng. Khâu via GND dọc đường RF và mép vùng cấm, bước ≤ 2 mm.
- **Ảnh hưởng của pin kim loại**: CR2450 là đĩa kim loại Ø24,5 mm, cách bo 1–2 mm, như một tấm phản xạ/mặt đất lệch tâm.
  - Đẩy pin **lệch tâm 3,5 mm** về phía đối diện anten, để được dải 8,75 mm không pin.
  - Anten cách mép bóng pin ≥ 3–5 mm.
  - Hai càng kẹp (+) của MY-2450-03 nằm ở vị trí khoảng 3 giờ và 9 giờ, xa anten (12 giờ).
- **Ảnh hưởng của vỏ nhựa**: ABS/PC (εr ≈ 2,7–3,2) kéo tần số cộng hưởng xuống vài chục tới hơn 100 MHz, tuỳ khoảng cách [ĐOÁN về độ lớn].
  - **Tinh chỉnh π khi đã đóng vỏ và lắp pin.**
  - Giữ khe không khí ≥ 1 mm giữa anten và thành vỏ.
- **Hiệu suất**: bo Ø35 nhỏ hơn nhiều so với 55×30 mm mà Silicon Labs khuyến nghị cho module. Dự kiến kém kit tham chiếu vài dB [ĐOÁN]. Cổng kiểm thử T3.5 đặt mức suy hao ≤ 6 dB. Không đạt thì tăng đường kính bo (mục 1.3).

## 4.6 Thạch anh

| | Yêu cầu MG24 [DS] | Chọn | Tụ tải ngoài |
|---|---|---|---|
| HFXO 39 MHz | ESR ≤ 60 Ω, CL 10 pF, tổng sai số ≤ ±40 ppm (802.15.4) | **TST TZ3541C** 2016, CL 10 pF, ESR 35 Ω (C5360883). Thay thế: ECS-390-CDX-1932 (C5441444). Tránh các mã ESR 80 Ω | **Không**: tụ nội CTUNE, bước 0,04 pF. Hiệu chỉnh CTUNE từng bo (T1.5) |
| LFXO 32,768 kHz | ESR ≤ 80–100 kΩ, CL 4–18 pF; tụ nội 5,2–26,2 pF/chân. **CL > 12 pF cần tụ ngoài** | **Epson FC-12M 9 pF** 2012 (C96341). Thay thế: NDK NX1610SA 6 pF (C1987116), FC-135 7 pF (C48615) | **Không** (CL ≤ 12 pF). Tránh bản 12,5 pF |

**Có cần LFXO không? CÓ** [KN]:
- Sleeptimer/SYSRTC chạy từ LFXO cho mọi lần thức (poll, đo, MaxInterval) với sai số cỡ ppm.
- Dùng LFRCO precision mode thì sai số ±500 ppm, tốn thêm khoảng 0,6 µA ở EM2, và phải hiệu chuẩn định kỳ bằng HFXO.
- Nếu sau này dùng CSL (SSED), độ chính xác LFXO là bắt buộc trên thực tế.

Layout: thạch anh cách chân ≤ 2–3 mm, vòng GND bao quanh, không đi dây bên dưới (L2 GND liền), xa cuộn DC-DC và đường RF.

## 4.7 Layout

**PCB**: Ø35 mm, **4 lớp**, dày 0,8 mm (ít khối nhiệt, máy mỏng hơn), ENIG (cho pad tiếp xúc pin và pad TC2030).

| Lớp | Nội dung |
|---|---|
| L1 | Linh kiện, đường RF CPWG 50 Ω (bề rộng tính bằng impedance calculator của JLCPCB theo stack-up 4 lớp 0,8 mm đã chọn), dây tín hiệu ngắn |
| L2 | **GND liền khối** (không cắt dưới RF/thạch anh), trừ vùng anten và lưỡi cảm biến |
| L3 | VBAT, VDCDC, vài tín hiệu chậm |
| L4 | GND + **pad (−) ENIG Ø8–10 mm** ở tâm pin + 2 pad kẹp (+) MY-2450-03 (tổng bề ngang pad 29,9 mm). **Kiểm lại footprint trong datasheet**: nếu 29,9 mm là tâm–tâm thì pad tràn mép bo khi pin lệch tâm 3,5 mm, phải giảm lệch tâm về khoảng 2 mm |

2 lớp vẫn làm được, nhưng với chip trần có DC-DC và RF thì 4 lớp an toàn hơn nhiều. Các thiết kế tham chiếu của Silicon Labs đều 4 lớp [KN].

**Xếp linh kiện trên bo tròn** (xem `hardware/floorplan.svg`):
- Pin lệch tâm 3,5 mm về hướng 6 giờ.
- 12 giờ: anten + vùng cấm. Ngay dưới là MG24 (QFN40), mạng phối hợp, HFXO, LFXO, cuộn DC-DC.
- Khoảng 10 giờ: **lưỡi cảm biến**.
- Khoảng 2 giờ: TC2030-NL, đặt ngoài bóng pin vì 3 lỗ NPTH định vị xuyên bo.
- Tâm bo: nút bấm. LED cạnh nút.
- Tụ dự trữ và MOSFET gần đường cấp từ kẹp (+).

**Lưỡi cảm biến (cách ly nhiệt)** theo Sensirion Design Guide:
- 2 khe phay rộng 0,8–1,0 mm từ mép bo vào khoảng 6 mm, tạo "ngón" rộng khoảng 4 mm, nối với bo ở gốc.
- **Không đổ đồng trên lưỡi ở mọi lớp.** Chỉ 4 dây 0,15 mm (VDD, GND, SDA, SCL).
- Không có đồng dưới cảm biến ngoài pad. Không hàn pad giữa/die pad. Không đặt via cạnh cảm biến.
- Tụ 100 nF ở gốc lưỡi.
- Lưỡi cách MG24, cuộn DC-DC và LED ≥ 10 mm, nằm ngoài bóng pin (khối kim loại khoảng 7 g làm chậm đáp ứng).
- Ghi chú định lượng [TT]: công suất trung bình của thiết bị chỉ khoảng 15 µW, nên **tự sưởi ở chế độ thường gần như bằng 0**. Lưỡi PCB chủ yếu để:
  1. cách ly với nhiệt lúc commissioning (vài mA trong khoảng 1 phút);
  2. giảm khối nhiệt để đáp ứng nhanh;
  3. cách ly với tay người và pin.
- Với độ ẩm, sai 1 °C tương đương khoảng 5 %RH ở 90 %RH, nên cách ly nhiệt quan trọng gấp đôi.

**DC-DC**: vòng VREGSW–L1–C ra ngắn nhất, cuộn cạnh chân, xa RF, thạch anh và lưỡi cảm biến.

## 4.8 Sơ đồ khối và kết nối

```
             ┌──────────── VBAT (sau Q1) ───────────────────────────────────────────┐
CR2450 ─ Q1 ─┤ C1,C2 2×100µF  C3 10µF   AVDD   IOVDD   VREGVDD                      │
 (kẹp+/pad−) │                           │       │       │                          │
             │                     ┌─────┴───────┴───────┴──────┐  VREGSW ─ L1 2,2µH ─┐
             │                     │        EFR32MG24B010       │                     │
             │  SHT40 ── I2C1 ─────┤ PCx/PCy                    │◄─ VDCDC (C4 10µF) ──┘
             │  (lưỡi PCB)         │                            │   → DVDD, RFVDD, PAVDD
             │  SW1 ── PBx (EM2) ──┤                            │  DECOUPLE ─ C5 1µF
             │  D1 ← R4 ← VBAT ────┤ PCz/PDz (sink)             │
             │                     │ HFXTAL ─ Y1 39 MHz         │
             │                     │ LFXTAL ─ Y2 32,768 kHz     │
             │  TC2030: VCC,SWDIO(PA02),nRESET,SWCLK(PA01),GND,SWO(PA03)
             │                     │ RF2G4 ─ match ─ π ─ ANT1   │
             └─────────────────────┴────────────────────────────┘
```

Chân cấp nguồn theo Figure 5.2 của datasheet: DVDD, RFVDD, PAVDD lấy từ VDCDC (PA +10 dBm chạy ở 1,8 V từ DC-DC); AVDD, IOVDD, VREGVDD lấy từ VBAT. Giá trị tụ cho từng chân (ngoài DC-DC 4,7 µF X7R ≥ 3,6 µF hiệu dụng và DECOUPLE 1 µF) **phải chép đúng schematic tham chiếu** của Silicon Labs.

## 4.9 Gán chân (yêu cầu, chốt bằng Pin Tool)

| Chức năng | Yêu cầu | Đề xuất |
|---|---|---|
| SWCLK / SWDIO / SWO | Cố định | PA01 / PA02 / PA03 |
| nRESET | Chân reset | TC2030 chân 3 |
| HFXO / LFXO | Chân thạch anh chuyên dụng | Theo datasheet QFN40 |
| Nút | **Cổng A/B** (chỉ A/B đánh thức được từ EM2). Nên chọn chân có EM4WU nếu muốn chế độ "shipping" EM4 | PBx, pull-up nội |
| I²C SHT40 | **I2C1** (domain PD1, tự tắt ở EM2) → cổng C/D | PCx/PCy |
| LED | Bất kỳ, kéo xuống (sink) | Cổng C/D |
| VCOM TX, PTI_DATA/PTI_FRAME | Chỉ prototype, ra pad test | Theo Pin Tool |

## 4.10 BOM (bản nháp v0.1, CHƯA chốt)

Biến thể **A = chip trần (khuyến nghị)**, **B = module MGM240S** (xem mục 1). Đầy đủ trong `hardware/bom.csv`.

| Nhóm | Linh kiện chính | Ghi chú |
|---|---|---|
| SoC | EFR32MG24B010F1536IM40-B (C6033375, 49 cái, 9,66 USD @100). Hoặc B210 QFN48 (C7271972) | LCSC tồn kho ít, giá cao. Mua số lượng ở nhà phân phối chính hãng (DigiKey B210 khoảng 5,68 USD @980) rồi gửi JLCPCB |
| Cảm biến | SHT40-AD1B (C2848306) | |
| Thạch anh | TZ3541C 39 MHz (C5360883), FC-12M 9 pF (C96341) | |
| Nguồn | DMP2035U-7 (C110499), 2×CL31A107MQHNNNE (C15008), DFE2HCAH2R2MJ0L (C2043106), 2×10 µF 0603 (C19702), 1 µF (C52923), 100 nF (C1525) | |
| RF | 2450AT18A100E (C89334), mạng phối hợp 0201 Murata (C237441, C2041495, C710810, C1864525, C85892), π 0 Ω (C17168) | Giá trị phối hợp **cần xác minh** |
| Giao tiếp người dùng | TS-1088-AR02016 (C720477), APTD1608LSURCK (C5342734), 680 Ω (C25130) | |
| Pin | Kẹp MY-2450-03 (C2988622) + pad ENIG | Mặt sau: PCBA 2 mặt hoặc hàn tay |
| Debug | Footprint TC2030-NL + pad test | |

**Ước tính chi phí linh kiện** (LCSC, 100 bộ): khoảng **14 USD/bo** (riêng MG24 khoảng 9,7). Ở 1k+ với giá nhà phân phối chính hãng còn khoảng 9–10 USD. Chưa gồm PCB, lắp ráp, vỏ, pin.

**Lưu ý JLCPCB**:
- Hầu hết linh kiện là "Extended", phí khoảng 3 USD/mã/lô.
- Linh kiện RF 0201 và QFN40 0,4 mm lắp được.
- Kẹp pin ở mặt sau cần PCBA 2 mặt. Cách khác: dùng bản THT (Keystone 3009, C238101) hàn tay.
