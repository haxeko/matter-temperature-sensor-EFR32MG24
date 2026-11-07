# 1. Yêu cầu, chọn SoC và kiến trúc

> Nhãn: **[DS]** datasheet · **[DIST]** giá/tồn kho nhà phân phối (07/11/2026) · **[KN]** · **[TT]** · **[ĐOÁN]**.

## 1.1 Yêu cầu và các giả định tôi đã đặt

| Yêu cầu | Diễn giải trong thiết kế |
|---|---|
| Cảm biến nhiệt độ (+ độ ẩm "nếu hợp lý") | **Có đo độ ẩm**: SHT40 đo cả hai, cùng chip, cùng năng lượng (mục 4.1) |
| Matter over Thread, ICD, commissioning BLE | ICD **LIT-capable, tự fallback SIT** (mục 2.3). **Không dùng SSED** (mục 6.5) |
| 1×CR2450, ≥ 18 tháng | Mô hình khoảng 5 µA. Ngưỡng cho phép (thận trọng) 20,8 µA |
| Bo tròn Ø32–35 mm, pin mặt sau | **Ø35 mm**, pin lệch tâm 2,0 mm (mục 1.3; lý do ở mục 4.11) |
| KiCad, Simplicity Studio + Matter extension | Studio v6, SiSDK 2026.6.2, Matter extension v2.9.2 (Matter 1.6) |
| Nạp qua TC2030 | TC2030-NL đặt ngoài bóng pin |
| 1 nút, 1 LED | Nút giữa bo (cổng B); LED đỏ/hổ phách |

**Giả định** (sai thì báo lại, xem câu hỏi mở trong README):
- Dùng trong nhà, 0–40 °C.
- Không có màn hình.
- Lắp ráp tại JLCPCB.
- Mục tiêu sai số ±0,3 °C / ±3 %RH sau hiệu chỉnh.
- Spec đích là Matter 1.6.x: 1.5 không còn là bản mới nhất (mục 2.0).

## 1.2 Chip trần EFR32MG24 hay module MGM240S/MGM240P

| Tiêu chí | **EFR32MG24 chip trần** (B010 QFN40 / B210 QFN48) | **MGM240S** (SiP) | **MGM240P** (module PCB) |
|---|---|---|---|
| Kích thước | QFN40 **5×5 mm** (QFN48 6×6) + khoảng 15 linh kiện nhỏ + anten chip 3,2×1,6 mm. Tổng khoảng 60–80 mm² + vùng cấm anten | **7×7×1,18 mm**, nhưng **anten là một vòng (loop) vẽ bằng đồng trên PCB chủ** theo các điểm A–M trong datasheet, có cutout lớp trong/dưới | **12,9×15 mm** |
| RF trên bo Ø35 | Tự thiết kế phối hợp + anten, **tinh chỉnh được** theo bo, pin, vỏ (cần VNA) | Đặt cách mép đồng 1,5 mm, giữa cạnh dài. **Hiệu năng tốt nhất trên bo 55×30 mm, giảm nhanh khi bo nhỏ hơn** [DS]. Không có chỗ tinh chỉnh | Cần **mặt GND rộng 55–60 mm** [DS], **không phù hợp** |
| Dải áp | VREGVDD: DC-DC 2,2–3,8 V; **bypass xuống 1,8 V** | (không rõ trong tài liệu đã đọc) | **VDD 2,2–3,8 V**: mất phần cuối đời pin |
| Công suất phát | +10 dBm (B010/B210) | +10 dBm | +10 / +20 dBm |
| Bảo mật | **B = Secure Vault High** (khoá DAC bọc PUF) | SD22 = Vault High, SA22 = Vault Mid | PB = Vault High |
| Giá @1k (DigiKey) | B210 khoảng **5,68 USD** + khoảng 1,5 USD linh kiện phụ (thạch anh, cuộn, anten, RF) | khoảng 7,62 USD | khoảng 7,37 USD |
| Giá/tồn LCSC @100 | B010 9,66 (49 cái) · B210 8,94 (23 cái) | SA22 15,45 (4 cái) · SD22 hết hàng | PB22 15,46 (19 cái) |
| Chứng nhận vô tuyến | **Đo RF đầy đủ** cho từng thị trường: FCC 15.247, ISED, CE-RED (EN 300 328), UKCA, Việt Nam… Thêm hiệu chỉnh CTUNE từng bo | **Có sẵn** FCC/ISED/CE/UKCA/MIC/KC (modular) nếu chép **đúng** hình học anten. Vẫn phải đo phần không cố ý phát (FCC 15B, EMC). Việt Nam vẫn cần hợp quy riêng [ĐOÁN] | Như MGM240S |
| Thread/Matter | Như nhau: chứng nhận Thread/Matter là theo **sản phẩm**, không theo module | | |
| Rủi ro chính | Layout RF/DC-DC, dò anten, CTUNE | Hiệu suất anten kém trên bo nhỏ + pin kim loại sát | Không vừa bo |

### Kết luận

1. **MGM240P: loại.** Không vừa Ø35 và cần GND rộng 55–60 mm.
2. **Khuyến nghị: chip trần `EFR32MG24B010F1536IM40`** (QFN40, Vault High, +10 dBm, 1536 kB/256 kB), cộng anten chip Johanson và mạng π tinh chỉnh, PCB 4 lớp.
   - Lý do chính: bo Ø35 có pin CR2450 che mặt sau là đúng trường hợp anten tích hợp/loop của module mất hiệu suất nhiều nhất, và chỉ chip trần cho phép dò lại anten theo vỏ và pin thật.
   - Chip trần còn chạy được tới 1,8 V (bypass), tận dụng phần cuối của pin.
   - Chi phí ở ≥ 1k tương đương hoặc rẻ hơn.
   - Lưu ý: **QFN40 không có bản B210**. Các bản 1536/256 trên QFN40 là B010/B020/A410/A420 [DS]. B020 là +19,5 dBm (156,8 mA), không dùng với pin cúc áo.
   - **Bản thay thế cùng firmware**: `EFR32MG24B210F1536IM48` (QFN48, có MVP, là chip của kit phát triển).
3. **MGM240SD22VNA2 (biến thể B)** hợp lý khi:
   - không có VNA hay kinh nghiệm RF, **hoặc**
   - muốn bán ở Mỹ/EU với số lượng nhỏ và tận dụng chứng nhận modular.

   Phải chấp nhận tầm phủ kém hơn và chép đúng hình học anten. Kiểm thử T3.5 sẽ cho biết mức suy hao thật.
4. **Lộ trình**:
   - Bo phát triển: kit xG24 (BRD2703A hoặc BRD4186C).
   - Prototype 1: chip trần + anten chip, có pad test RF/PTI.
   - Nếu kiểm thử T3.5 suy hao > 6 dB so với kit và không cải thiện được bằng tinh chỉnh: tăng đường kính bo (1.3), hoặc làm thử biến thể B để so.

## 1.3 Các mâu thuẫn trong yêu cầu và phương án

| # | Mâu thuẫn | Định lượng | Phương án đề xuất |
|---|---|---|---|
| 1 | **Bo Ø32–35 mm và anten** (pin che gần hết mặt sau) | Ø35 với pin lệch tâm 2,0 mm còn **dải 7,25 mm** không có pin. Không lệch tâm hơn được vì thân kẹp MY-2450-03 (29,1 × 15,4 mm) khi đó thò ra ngoài mép bo. Ở Ø32 kẹp **không vừa** | Chọn **Ø35** (cận trên). Nếu RF không đạt: **Ø38–40** (dải 10–12 mm). Hoặc đổi sang **CR2032** (Ø20, 225 mAh): mô hình vẫn khoảng 27 tháng (thận trọng) nhưng chịu xung kém hơn |
| 2 | **CR2450 và dòng đỉnh RF** | +10 dBm: khoảng 20,5 mA. Với R = 100 Ω (cuối đời/−20 °C), khung dài sụt **0,85 V** dù có 80 µF (mục 4.2) | **+8 dBm** mặc định, **+4 dBm** khi pin yếu/lạnh, tụ 2×100 µF, BLE 0…+4 dBm, cấm heater SHT4x |
| 3 | **"Ưu tiên SSED"** và năng lượng | CSL 1 s: 14 µA. SED SIT 15 s: 5,1 µA. LIT: 3,9 µA | **Dùng SED/ICD**, không dùng SSED |
| 4 | **"Spec mới nhất 1.5"** | 1.6 (06/2026), 1.6.1 (09/2026) đã ra | Nhắm 1.6.x qua extension v2.9.2 |
| 5 | **Linh kiện 1 mặt** và đế pin mặt sau | Kẹp SMD ở mặt sau | PCBA 2 mặt, hoặc hàn tay kẹp. Bản THT: Keystone 3009 |
| 6 | **TC2030 và pin mặt sau** | TC2030-NL vẫn cần 3 lỗ NPTH xuyên bo | Đặt TC2030 ở dải ngoài bóng pin và thân kẹp (hướng 11 giờ) |
| 7 | **18 tháng** | Cho phép ≤ 20,8 µA (thận trọng); mô hình 5,1 µA | **Không mâu thuẫn.** Rủi ro nằm ở cấu hình firmware (các bẫy E/F, mục 6) và dòng rò |

## 1.4 Kiến trúc tổng thể

```
                 ┌────────────── Ø35 mm, 4 lớp, 0,8 mm ──────────────┐
CR2450 ─ P-MOSFET ─ VBAT ─┬─ 2×100 µF                              │
(kẹp MY-2450-03)          ├─ EFR32MG24B010 (DC-DC 2,2 µH, HFXO 39 MHz, LFXO 32 kHz)
                          │     ├─ RF: phối hợp → π tinh chỉnh → anten chip (dải không pin)
                          │     ├─ I2C1 (PC02/PC03) → SHT40 trên lưỡi PCB có khe phay
                          │     ├─ PB01 ← nút (đánh thức EM2)  · PC01 → LED đỏ
                          │     ├─ IADC: AVDD/4 nội = áp pin (không cầu chia)
                          │     └─ SWD → TC2030-NL
                          └──────────────────────────────────────────┘
Firmware: Matter 1.6 (extension 2.9.2) · ICD LIT-capable (SIT 15 s ↔ LIT 30 phút) · Idle 1800 s
          · đo 30 s · vùng chết 0,2 °C / 2 %RH (mềm 0,1 / 1) · báo cáo đồng bộ · OTA nội (LZMA)
```

| Quyết định | Chọn | Mục chi tiết |
|---|---|---|
| SoC | EFR32MG24B010F1536IM40 (chip trần) | 1.2 |
| Cảm biến | SHT40-AD1B | 4.1 |
| Vai trò Thread | SED (MTD), ICD LIT-capable, fallback SIT | 2.3, 6.5 |
| ICD | Idle 1800 s · AMD 0 · AMT 5 s · poll 15 s (SIT) / 1800 s (LIT) · fast 500 ms | 2.3 |
| Nguồn | P-MOSFET DMP2035U + 2×100 µF + DC-DC nội | 4.2, 4.3 |
| Đo pin | IADC AVDD/4 nội + thuật toán lai | 4.4, 5.5 |
| Anten | Johanson 2450AT18A100E + mạng π | 4.5 |
| OTA | Bật, lưu flash nội, LZMA | 2.7 |
| Ví dụ firmware gốc | "Matter Thread - SoC Multi Sensor FreeRTOS" | 5.1 |
