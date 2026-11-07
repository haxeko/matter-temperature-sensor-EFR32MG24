# 6. Ngân sách năng lượng

> Mô hình nằm trong `tools/power_budget.py`. Chạy `python3 tools/power_budget.py --markdown --sensitivity` để in lại các bảng dưới đây.
> Số liệu dòng lấy từ datasheet EFR32MG24 (3,0 V, DC-DC bật) và SHT4x. **Thời lượng từng pha là ước tính** và phải thay bằng số đo (mục 6.6).

## 6.1 Điện tích mỗi sự kiện (kịch bản A)

| Sự kiện | Thành phần (mô hình) | Điện tích | Tần suất | Dòng TB |
|---|---|---|---|---|
| **Ngủ EM2** | MG24 giữ 256 kB RAM + LFXO 2,9 µA [DS]; SHT40 idle 0,08 µA; rò tụ/PCB 0,15 µA | — | liên tục | **3,13 µA** |
| **Poll Thread** | wake + HFXO 0,8 ms × 2,5 mA; CSMA backoff 1,1 ms × 1,3 mA; TX Data Request 0,85 ms × 13 mA; CCA + ACK 0,85 ms × 5,1 mA | **≈ 19 µC** | SIT: 1/15 s · LIT: 1/1800 s | **1,25 µA** (SIT) · 0,01 µA (LIT) |
| **Đo SHT40** | 6,9 ms × 320 µA + CPU khoảng 2 µC | ≈ 4,2 µC | 1/30 s | 0,14 µA |
| **Báo cáo** (2 subscriber, đồng bộ) | Mỗi subscriber: TX ReportData khoảng 3,5 ms (≈ 56 µC) + nhận StatusResponse (≈ 42 µC) + TX MRP ACK (≈ 36 µC) ≈ 134 µC. Đuôi active: (5000/500 + 1) = 11 poll × 19 µC ≈ 207 µC | **≈ 476 µC** | 48/ngày (do thay đổi) + keep-alive còn thiếu | 0,26 + 0,10 µA |
| Child supervision | Khoảng 1 khung từ parent mỗi 129 s | ≈ 11 µC | 1/129 s | 0,09 µA |
| SRP refresh, bảo trì mạng | Khoảng 0,6 mC | | 12/ngày | 0,08 µA |
| Mất parent / re-attach | Khoảng 12 mC/lần thử (khoảng 2 s RX) | | 2 lần + 2 h mồ côi/tháng | 0,04 µA |
| Đo pin, LED | 5 µC/lần đo; 100 µC/lần nháy | | 4 + 2/ngày | 0,003 µA |
| **Commissioning BLE** (một lần) | Quảng bá nhanh 30 s (khoảng 8 mC) + chậm ≤ 14,5 phút (khoảng 16 mC) + PASE/attestation/attach/CASE khoảng 45 s × 6 mA (khoảng 270 mC) | **≈ 0,3 C ≈ 0,08 mAh** | 1 lần | ≈ 0,015 % pin |
| **OTA** (mỗi lần cập nhật) | Khoảng 0,5 MB ảnh LZMA qua BDX, active 10–30 phút | ≈ 2–4 mAh [ĐOÁN] | hiếm | ≤ 0,7 % pin/lần |

## 6.2 Các kịch bản

| Kịch bản | I_avg (µA) | Tuổi thọ danh định | Tuổi thọ thận trọng* | Ghi chú |
|---|---:|---:|---:|---|
| **A. LIT-capable, đang chạy SIT (khuyến nghị)** | **5,1** | 113,7 th (9,5 năm) | **69,1 th (5,8 năm)** | poll 15 s, fast 500 ms, AMT 5 s, 2 subscriber, 48 báo cáo/ngày |
| B. Cùng firmware, đang chạy LIT | 3,9 | 144,8 th (12,1 năm) | 88,9 th (7,4 năm) | controller đã RegisterClient (ví dụ HA matter.js server) |
| C. Firmware chỉ SIT (không LITS) | 5,0 | 115,1 th (9,6 năm) | 70,0 th (5,8 năm) | AMT được phép < 5 s |
| D. SSED, CSL 1 s | 14,0 | 44,6 th (3,7 năm) | 26,4 th (2,2 năm) | SSED không có lợi cho cảm biến |
| E. **Bẫy**: ShortIdle 60 s + report-on-active | 11,4 | 54,4 th (4,5 năm) | 32,4 th (2,7 năm) | Mặc định `lit-icd-app` khi rơi về SIT |
| F. **Bẫy**: SED poll 2 s | 13,2 | 47,2 th (3,9 năm) | 28,0 th (2,3 năm) | Minh hoạ độ nhạy |
| G. Xấu nhưng thực tế | 9,0 | 45,3 th (3,8 năm) | 45,3 th (3,8 năm) | 4 hệ sinh thái, TX +10 dBm, phòng lạnh, rò 1 µA, quên tắt PD0D |

\*Thận trọng: dung lượng dùng được 70 %, dòng × 1,5, tự xả 1 %/năm. Kịch bản G đã tự mang hệ số riêng (85 % do lạnh, × 1,3).

Phân rã kịch bản A:

| Thành phần | µA | % |
|---|---:|---:|
| Ngủ EM2 (MG24, giữ RAM, LFXO) | 2,900 | 56,9 |
| Poll Thread (idle) | 1,254 | 24,6 |
| Báo cáo khi thay đổi | 0,264 | 5,2 |
| Cảm biến idle + rò rỉ | 0,230 | 4,5 |
| Đo cảm biến | 0,140 | 2,7 |
| Báo cáo keep-alive (MaxInterval 1800 s) | 0,097 | 1,9 |
| Child supervision | 0,085 | 1,7 |
| SRP refresh + bảo trì mạng | 0,083 | 1,6 |
| Re-attach / mất parent | 0,037 | 0,7 |
| Đo pin + LED | 0,003 | 0,0 |
| **Tổng** | **5,09** | 100 |

## 6.3 Hệ số an toàn cho CR2450

| Yếu tố | Giá trị dùng | Cơ sở |
|---|---|---|
| Dung lượng danh định | 600 mAh (các hãng: 540–620) | DS Panasonic/Energizer/Murata/Renata/Varta |
| Cut-off và xung | Còn 80 % (danh định) / 70 % (thận trọng) | Varta: **với xung, chạm 2,0 V ở khoảng 68 % đời pin**. TI SWRA349: tụ 100 µF bù lại > 40 % ở pin yếu. Thiết kế có 2×100 µF và TX ≤ +8 dBm |
| Nhiệt độ thấp | × 0,85 khi phòng 0–10 °C (kịch bản G) | Murata: −20 °C tải 10 mA áp 2,8→2,1 V |
| Tự xả | 1 %/năm (≈ 0,7 µA tương đương) | Energizer khoảng 1 %/năm; Renata < 1 %/năm |
| Sai số mô hình dòng | × 1,5 | Lưu lượng mạng thật, retry, CASE lại, controller khởi động lại |

**Mục tiêu 18 tháng** cho phép:
- I_avg danh định ≤ **35,8 µA** khi không có hệ số an toàn;
- **≤ 20,8 µA** khi áp đủ hệ số thận trọng.

Ước tính kịch bản A là **5,1 µA, tức biên gấp khoảng 4 lần**.

**Giới hạn thực tế**: con số "9–12 năm" chỉ là toán học. Lão hoá và tự xả của pin, cộng sai số mô hình, giới hạn tuổi thọ thực tế ở khoảng 5 năm.

**Khuyến nghị công bố**: **"lên tới 2 năm"**, cho tới khi có số đo 24 h trên mạng thật (T4.9) và thử tăng tốc. Tham chiếu: W100 công bố 2,3 năm với 2×CR2450 + LCD; Eve Weather "1+ năm" với 1×CR2450 + LCD.

## 6.4 Ba thông số ảnh hưởng nhiều nhất

Phân tích độ nhạy quanh kịch bản A (nhân đôi / chia đôi từng thông số):

| Tham số | Giá trị gốc | Tuổi thọ khi ×0,5 | Tuổi thọ khi ×2 | Biên độ |
|---|---:|---:|---:|---:|
| **1. Dòng nền EM2** (`i_em2_ua`, gồm rò rỉ) | 2,9 µA | 151,8 th | 75,7 th | **76,1 th** |
| **2. Slow poll interval** (`slow_poll_s`) | 15 s | 93,4 th | 127,6 th | **34,1 th** |
| **3. Dòng TX / công suất phát** (`i_tx_ma`) | 13 mA | 124,5 th | 96,9 th | **27,6 th** |
| Số subscriber | 2 | 115,7 th | 109,9 th | 5,9 th |
| Số báo cáo/ngày | 48 | 115,1 th | 109,9 th | 5,2 th |
| Rò rỉ tụ/PCB | 0,15 µA | 115,2 th | 110,8 th | 4,4 th |
| ActiveModeThreshold | 5000 ms | 115,1 th | 111,0 th | 4,2 th |
| Fast poll | 500 ms | 111,0 th | 115,1 th | 4,2 th |
| Chu kỳ đo | 30 s | 111,0 th | 115,1 th | 4,1 th |

1. **Dòng nền EM2** chiếm khoảng 57 %. Mọi thứ làm tăng nền đều đắt:
   - giữ ngoại vi PD0B/PD0D bật (+0,9…+1,1 µA);
   - SPI flash ngoài (biến thể "external bootloader");
   - LFRCO precision (+0,6 µA);
   - rò tụ, flux;
   - debugger còn cắm;
   - quên tắt log/UART.
2. **Slow poll interval** chiếm khoảng 25 % ở SIT, gần 0 ở LIT. Đây là nơi có các **bẫy cấu hình**:
   - poll 2 s: khoảng 13 µA;
   - ShortIdle 60 s + report-on-active: khoảng 11 µA;
   - SSED/CSL 1 s: khoảng 14 µA.
3. **Dòng TX (công suất phát)** ảnh hưởng cả năng lượng mỗi poll/báo cáo **và** sụt áp đỉnh trên CR2450 (mục 4.2). +10 dBm so với +8 dBm: −13 % tuổi thọ và brown-out sớm hơn ở cuối đời pin.

Các thông số "cảm giác quan trọng" như chu kỳ đo, ngưỡng báo cáo hay số subscriber lại chỉ ảnh hưởng vài %, **miễn là** báo cáo được đồng bộ (mục 2.4).

## 6.5 SED, SSED và LIT

| Chế độ | Ưu điểm | Nhược điểm cho cảm biến nhiệt |
|---|---|---|
| SED, SIT (poll ≤ 15 s) | Tương thích mọi hệ sinh thái | Khoảng 1,25 µA cho poll |
| **SED, LIT** (poll 30 phút) | Poll gần 0 µA | Cần controller đăng ký Check-In (chưa phổ biến) |
| SSED (CSL) | Độ trễ downlink thấp ở dòng vừa phải | Trong Silicon Labs, **CSL period = poll interval** (`otLinkSetCslPeriod`). Trường CSL period 16 bit × 160 µs giới hạn khoảng 10,5 s, nên **không đạt được 15 s/30 phút**. Cần parent Thread ≥ 1.2 và LFXO chính xác. Cảm biến gần như không có downlink nên **SSED không có lợi**. Không dùng |

## 6.6 Quy trình đo bằng Energy Profiler / PPK2

**Chuẩn bị**:
1. Firmware bản sản phẩm: `matter_no_debug`, không log, LED chỉ khi cần. Rút debugger sau khi nạp.
2. Nguồn:
   - **PPK2 source mode 3,0 V** vào tiếp điểm pin qua **pin giả CR2450** (đĩa PCB Ø24,5 mm có 2 dây).
   - Hoặc **AEM của WSTK/Pro Kit** cấp qua VMCU (bản prototype có pad VAEM).
   - Kiểm tra sụt áp thật: **PPK2 ammeter mode** nối tiếp với pin thật.
3. Mạng: OTBR + 2–3 controller thật. Ghi nhiệt độ phòng.

**Các phép đo** (Energy Profiler: chọn vùng rồi đọc "Charge"/"Average"; PPK2: chọn vùng rồi đọc "Charge"):

| Bước | Đo | So với mô hình |
|---|---|---|
| 1 | Dòng giữa hai poll (cửa sổ ≥ 5 s, không có xung) | `i_em2_ua + i_sensor_idle_ua + i_leak_ua` (mục tiêu ≤ 3,3 µA) |
| 2 | Tích phân 1 xung poll (từ lúc dòng rời nền tới khi về nền) | `q_poll()` ≈ 19 µC |
| 3 | Xung đo SHT40 (đánh dấu bằng GPIO debug trên bản dev) | ≈ 4 µC |
| 4 | Một lần báo cáo với 1, 2, 3 subscriber (tạo thay đổi bằng hơi ấm) | `q_report_event()`. Đếm số fast poll ở đuôi |
| 5 | Trung bình 24 h trên mạng thật | `I_avg` của mô hình. Lệch > 30 % thì tìm nguyên nhân |
| 6 | Commissioning (từ lúc lắp pin tới khi ghép xong) | ≈ 0,08 mAh |
| 7 | Mồ côi 2 h (tắt toàn bộ router) | `q_attach_uc`, kiểm tra backoff |
| 8 | Sụt áp ở 25 °C và −18 °C (ngăn đông) với pin thật mới/đã dùng | Bảng mục 4.2; không có BOD |

**Cập nhật mô hình**: sửa các trường `t_*`, `q_*`, `i_*` trong `Params` theo số đo, chạy lại script. Đưa hệ số `I_mô_hình(SIT/LIT)` vào `BatteryEstimator` (mục 5.5).

**Mẹo**:
- Energy Profiler có "code correlation" (PC sampling qua SWO) để biết đoạn mã nào gây xung lạ. Chỉ dùng khi còn cắm debug, vì cắm debug làm sai dòng nền.
- Với PPK2 ở dải µA, dùng tần số lấy mẫu 100 kS/s cho xung poll.
- Đo tổng điện tích qua cửa sổ dài hơn là cố đọc dòng đỉnh.
