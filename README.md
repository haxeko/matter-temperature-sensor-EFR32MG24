# Cảm biến nhiệt độ/độ ẩm Matter-over-Thread — EFR32MG24 + CR2450

Thiết kế sơ bộ (v0.1) cho một cảm biến nhiệt độ và độ ẩm chạy 1 pin CR2450:
- Matter 1.6 over Thread, thiết bị ICD ngủ, commissioning qua BLE.
- Bo tròn Ø35 mm, nạp qua Tag-Connect TC2030.

> **Trạng thái:** đã có kiến trúc, phân tích và tài liệu thiết kế. **BOM chưa chốt** — xem [Câu hỏi mở](#câu-hỏi-mở-cần-trả-lời-trước-khi-chốt-bom).
> Dữ liệu tra cứu ngày 07/11/2026.
> Nhãn trong tài liệu: **[SPEC]** bắt buộc theo spec · **[SDK]** đã đối chiếu mã nguồn · **[KN]** khuyến nghị · **[TT]** kinh nghiệm thực tế · **[ĐOÁN]** suy đoán.

## Quyết định chính

| Hạng mục | Chọn | Lý do ngắn |
|---|---|---|
| Spec | **Matter 1.6.x** (1.6 ra 17/06/2026, 1.6.1 ra 09/2026). 1.5 không còn mới nhất | ICD không đổi từ 1.4 nên thiết kế vẫn đúng với 1.5 |
| SoC | **EFR32MG24B010F1536IM40** (chip trần, QFN40, Vault High, +10 dBm) | Bo nhỏ + pin kim loại: chỉ chip trần cho phép dò anten theo bo, pin và vỏ. MGM240P quá lớn; anten loop của MGM240S hợp bo 55×30 mm |
| Cảm biến | **Sensirion SHT40-AD1B** (đo cả RH) | ±0,2 °C typ / ±1,8 %RH, 2,2 µC mỗi lần đo, chạy từ 1,08 V. SHT45 nếu cần ±0,1 °C |
| Vai trò Thread | **SED**, ICD **LIT-capable, tự fallback SIT**. **Không dùng SSED** | CSL bị giới hạn khoảng 10,5 s và = poll interval, nên tốn hơn (14 µA so với 5 µA) |
| ICD | Idle 1800 s · ActiveModeDuration 0 · Threshold 5 s · poll 15 s (SIT) / 30 phút (LIT) · fast 500 ms · ShortIdle = Idle | Tránh "bẫy" ShortIdle 60 s (+5,7 µA) |
| Báo cáo | Đo 30 s; vùng chết 0,2 °C / 2 %RH (mềm 0,1 / 1, đi kèm lần thức kế tiếp); đồng bộ subscription; report-on-active | Không thức radio thêm |
| Nguồn | P-MOSFET DMP2035U (chống ngược) + 2×100 µF + DC-DC nội; TX +8 dBm, +4 dBm khi pin yếu/lạnh | CR2450 không chịu +10 dBm cố định ở cuối đời/lạnh |
| Đo pin | IADC đo AVDD/4 nội (không cầu chia) + thuật toán lai: đếm điện tích + áp | Rò = 0; % pin không "đứng 100 % rồi rơi" |
| OTA | Bật; lưu trong flash nội (GBL nén LZMA) | Không cần SPI flash; EM2 thấp hơn |
| Năng lượng | Mô hình khoảng **5,1 µA** (SIT) / 3,9 µA (LIT). **Cho phép ≤ 20,8 µA** cho 18 tháng (thận trọng) | Biên gấp khoảng 4 lần. Rủi ro nằm ở cấu hình firmware, không ở phần cứng |

## Tài liệu (đi theo đúng thứ tự yêu cầu)

| # | Tài liệu | Nội dung |
|---|---|---|
| 1 | [docs/01-soc-and-architecture.md](docs/01-soc-and-architecture.md) | Yêu cầu, giả định; **chip trần vs MGM240S/P**; **các mâu thuẫn và phương án**; kiến trúc |
| 2 | [docs/02-matter-compliance.md](docs/02-matter-compliance.md) | Phiên bản spec; endpoint/cluster; Power Source; ICD SIT/LIT, Check-In, UAT, tham số; **hệ sinh thái nào hỗ trợ LIT**; subscription/đồng bộ; commissioning; DAC/PAI/PAA/CD; DIY vs thương mại; OTA |
| 3 | [docs/03-commercial-benchmark.md](docs/03-commercial-benchmark.md) | Eve Weather, Aqara W100, Onvis, IKEA TIMMERFLOTTE (**MG24 + SHT4x**), Aqara T1; phân rõ chính thức / cộng đồng / suy đoán |
| 4 | [docs/04-hardware.md](docs/04-hardware.md) | So sánh cảm biến; nguồn CR2450 và sụt áp; chống ngược; đo pin; RF/anten; thạch anh; layout; gán chân; BOM |
| 5 | [docs/05-firmware.md](docs/05-firmware.md) | Ví dụ gốc; luồng EM2→đo→ngưỡng→báo cáo; nút/LED; đo pin; chính sách ICD đa fabric; mất parent; thay pin; component; cấu hình ICD; provisioning |
| 6 | [docs/06-power-budget.md](docs/06-power-budget.md) | Bảng điện tích từng sự kiện, 7 kịch bản, hệ số an toàn, **3 thông số ảnh hưởng nhất**, quy trình đo Energy Profiler/PPK2 |
| 7 | [docs/07-test-plan.md](docs/07-test-plan.md) | Kế hoạch kiểm thử: bring-up, Matter, RF, dòng, độ chính xác, hệ sinh thái; tiêu chí "đóng băng" thiết kế |

Tệp đi kèm:
- [`hardware/bom.csv`](hardware/bom.csv): BOM nháp v0.1 có mã LCSC đã kiểm (07/11/2026). Biến thể A = chip trần, B = MGM240S.
- [`hardware/floorplan.svg`](hardware/floorplan.svg): bố trí đề xuất trên bo Ø35 mm theo tỉ lệ (anten, lưỡi cảm biến, TC2030, kẹp pin).
- [`tools/power_budget.py`](tools/power_budget.py): mô hình năng lượng có tham số, kịch bản và phân tích độ nhạy.
- [`firmware/app-logic/`](firmware/app-logic): logic firmware không phụ thuộc phần cứng, có test chạy trên host:
  - driver SHT4x (CRC, chuyển đổi);
  - chính sách báo cáo (vùng chết hai tầng);
  - ước tính pin (Power Source);
  - máy trạng thái nút.

```bash
python3 tools/power_budget.py --sensitivity            # ngân sách năng lượng
python3 tools/power_budget.py --markdown               # bảng Markdown
cmake -S firmware/app-logic -B build && cmake --build build && ctest --test-dir build   # 102 kiểm tra
```

## Câu hỏi mở (cần trả lời trước khi chốt BOM)

1. **Mục đích và số lượng**:
   - DIY (vài chiếc) hay bán thương mại?
   - Bao nhiêu chiếc/năm, bán ở thị trường nào (Việt Nam / Mỹ / EU)?

   Câu này quyết định chip trần hay MGM240S, và lộ trình chứng nhận (CSA, Thread, FCC/CE, hợp quy VN).
2. **Đo RF**: anh/chị có VNA (kể cả NanoVNA) hoặc tiếp cận được phòng đo RF không? Không có thì nên làm biến thể B (MGM240S) song song.
3. **Kích thước**:
   - Có chấp nhận **Ø35 mm** (Ø32 gần như không chứa được kẹp CR2450)?
   - Có được tăng lên **Ø38–40 mm** nếu thử RF (T3.5) không đạt?
4. **Môi trường dùng**:
   - Chỉ trong nhà?
   - Có phòng tắm/bếp (nên dùng SHT4x-AD1F có màng)?
   - Có nơi lạnh như garage/ngoài trời (CR2450 ở −10…−20 °C, cần vỏ IP)?
5. **Độ chính xác công bố**: ±0,2 °C (SHT40) hay ±0,1 °C (SHT45)? Có hiệu chuẩn offset cho từng chiếc không?
6. **Hệ sinh thái ưu tiên** (Apple / Google / Home Assistant / SmartThings). Có cần LIT ngay từ bản đầu, hay chấp nhận chỉ SIT để đơn giản?
7. **Lắp ráp**: JLCPCB PCBA 2 mặt (kẹp pin SMD ở mặt sau), hay hàn tay kẹp/bản THT?
8. **OTA** có cần ngay ở bản đầu (DIY có thể tạm tắt)?
9. **Vỏ**:
   - In 3D hay ép nhựa?
   - Đặt bàn hay dán tường?
   - Có nam châm hoặc tấm kim loại (ảnh hưởng anten) không?
10. **Ngân sách BOM** mục tiêu mỗi chiếc. Hiện ước tính khoảng 14 USD @100 ở LCSC, khoảng 9–10 USD @1k ở nhà phân phối chính hãng.

## Những điểm phải xác minh trước khi đặt mạch

- Giá trị mạng phối hợp RF cho **QFN40** (AN930.2 / schematic tham chiếu). Số hiện tại lấy từ BRD4186C (QFN48).
- Tụ decoupling cho từng chân nguồn MG24: chép đúng schematic tham chiếu Silicon Labs.
- Footprint kẹp MY-2450-03: khoảng 29,9 mm là tâm–tâm hay mép–mép.
- SiSDK có tự chuyển DC-DC sang bypass khi VBAT < 2,2–2,3 V không.
- Đường cong áp→% của CR2450 trong `battery_estimator.h` là **giả định** và phải thay bằng số đo.
