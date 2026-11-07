# 7. Kế hoạch kiểm thử

> Quy ước nhãn dùng trong toàn bộ tài liệu:
> **[SPEC]** = yêu cầu bắt buộc của spec Matter/Thread · **[KN]** = khuyến nghị (spec/nhà sản xuất) ·
> **[TT]** = kinh nghiệm thực tế · **[ĐOÁN]** = suy đoán, cần kiểm chứng.

Kiểm thử chia thành 6 nhóm, chạy theo thứ tự (nhóm sau dùng kết quả nhóm trước):

| # | Nhóm | Mục tiêu chính | Công cụ |
|---|---|---|---|
| T1 | Bring-up & chức năng phần cứng | Bo sống, nạp được, xung nhịp đúng, cảm biến/nút/LED/đo pin hoạt động | Simplicity Commander, RAILtest, đồng hồ vạn năng, nguồn lập trình |
| T2 | Chức năng Matter/Thread | Commissioning, cluster, ICD, subscription, OTA, xử lý lỗi | chip-tool, OTBR, Network Analyzer/Wireshark, Matter Test Harness |
| T3 | RF & tầm phủ | Tần số, công suất, phối hợp anten, tầm thực tế trong nhà | RAILtest, VNA, máy phân tích phổ, OTBR `ot-ctl` |
| T4 | Dòng tiêu thụ | Đo từng sự kiện, trung bình 24 h, so với mô hình | Energy Profiler + WSTK/Pro Kit AEM, Nordic PPK2 |
| T5 | Độ chính xác T/RH | Sai số tĩnh, tự sưởi, thời gian đáp ứng, ảnh hưởng vỏ | Nhiệt/ẩm kế chuẩn có hiệu chuẩn, hộp ổn nhiệt, muối bão hoà |
| T6 | Tương thích hệ sinh thái | Apple Home, Google Home, Home Assistant, (SmartThings, Alexa) | Thiết bị thật, nhật ký 7 ngày |

---

## T1. Bring-up & chức năng phần cứng

| ID | Bước kiểm tra | Tiêu chí đạt |
|---|---|---|
| T1.1 | Kiểm tra ngắn mạch VBAT–GND trước khi lắp pin (đo điện trở) | > 1 MΩ (sau khi tụ nạp) |
| T1.2 | Cấp 3,0 V qua tiếp điểm pin bằng nguồn giới hạn dòng 50 mA; đo dòng khi chip trắng (chưa nạp) | Ổn định, không quá dòng |
| T1.3 | Kết nối TC2030 → debugger, `commander device info` | Đọc được Unique ID, flash 1536 kB |
| T1.4 | Nạp bootloader + RAILtest; kiểm HFXO khởi động, LFXO khởi động (đo bằng cách xuất xung lên GPIO qua PRS/CMU CLKOUT) | 39 MHz / 32,768 kHz ổn định |
| T1.5 | **Hiệu chuẩn CTUNE** (chỉ bản chip trần): RAILtest phát CW ở 2440 MHz, đo sai lệch tần số bằng máy phân tích phổ, chỉnh CTUNE tới khi độ lệch tần số < 2–3 ppm, ghi vào token `MFG_CTUNE` | Sai lệch ≤ ±5 ppm sau hiệu chỉnh |
| T1.6 | I2C: đọc serial SHT4x (lệnh 0x89), đo T/RH | CRC đúng, giá trị hợp lý |
| T1.7 | **Chỉ khi cấp nguồn ngoài (không dùng CR2450)**: bật heater SHT4x mức thấp (20 mW, 0,1 s, lệnh 0x15) → T đo tăng rồi trở lại. Heater 200 mW kéo khoảng 67 mA, **cấm dùng với pin cúc áo** | Xác nhận cảm biến sống, kiểm tra cách nhiệt lưỡi PCB |
| T1.8 | Nút: nhấn ngắn / 3 s / 10 s, chống dội (bounce), đánh thức từ EM2 | Đúng hành vi mục 5.3 |
| T1.9 | LED: đủ sáng ở VBAT = 2,4 V (LED đỏ/hổ phách AlInGaP) | Nhìn thấy rõ trong phòng sáng |
| T1.10 | **Đo pin**: dùng nguồn lập trình (hoặc PPK2 source mode) quét 3,3 → 1,9 V, bước 0,1 V; so IADC (AVDD nội) với DMM | Sai số ≤ ±20 mV sau hiệu chỉnh offset/gain |
| T1.11 | **Mô phỏng pin yếu/lạnh**: nguồn 2,7 V nối tiếp điện trở 10/30/60/100 Ω (mô phỏng nội trở CR2450 mới/cũ/lạnh) → chạy commissioning + báo cáo liên tục | Không reset BOD ở 30 Ω; ở 60–100 Ω firmware chuyển sang chế độ pin yếu thay vì reset liên tục |
| T1.12 | Lắp ngược pin (nguồn −3 V giới hạn 100 mA vào tiếp điểm) | Dòng ≈ 0 (chỉ rò P-MOSFET), không hỏng |
| T1.13 | Quét áp chậm 3,2 → 1,6 V rồi lên lại (0,1 V/phút) | Không treo; reset sạch dưới ngưỡng BOD; khởi động lại đúng khi áp hồi |
| T1.14 | Rò rỉ bo: nạp firmware vào EM4 (hoặc giữ ở EM2 không radio) → đo dòng nền | Trong khoảng mô hình (xem 6). Nếu cao hơn > 0,5 µA: thử thay tụ 100 µF bằng hãng/lô khác, kiểm tra flux quanh VBAT. **Không rửa bo đã gắn SHT4x** (Sensirion: dùng kem hàn no-clean, không rửa, không phủ) |

## T2. Chức năng Matter/Thread

Môi trường: Raspberry Pi + OTBR (RCP là xG24 dev kit hoặc ZBT-1/ZBT-2) + `chip-tool`, thêm 1 WSTK/nRF52840 dongle làm sniffer (Network Analyzer hoặc Wireshark có Thread network key để giải mã).

| ID | Kiểm tra | Cách làm | Tiêu chí |
|---|---|---|---|
| T2.1 | Commissioning BLE-Thread | `chip-tool pairing ble-thread <node> hex:<dataset> <passcode> <discriminator>` và bằng QR (`code`) | Thành công 10/10 lần, < 60 s |
| T2.2 | Payload QR/mã 11 số | `chip-tool payload parse-setup-payload MT:...`; so với nhãn | VID/PID/discriminator/passcode khớp |
| T2.3 | Đọc toàn bộ thuộc tính | `chip-tool any read-all` hoặc đọc từng cluster EP0/EP1/EP2 | Đúng cấu trúc endpoint mục 2.1 |
| T2.4 | ICD Management | Đọc IdleModeDuration, ActiveModeDuration, ActiveModeThreshold, FeatureMap, OperatingMode, UserActiveModeTriggerHint | Đúng giá trị cấu hình |
| T2.5 | Đăng ký Check-In (LIT) | `chip-tool icd registerClient ...` (chạy chip-tool interactive để nhận check-in) → kiểm tra OperatingMode chuyển LIT; tắt chip-tool > IdleModeDuration → bật lại → nhận Check-In | Check-In đến sau ≤ IdleModeDuration |
| T2.6 | Fallback SIT | Huỷ đăng ký client → OperatingMode = SIT, slow poll ≤ 15 s (xem trên sniffer) | Đúng |
| T2.7 | Subscription | `chip-tool interactive start` → `subscribe` min 0 / max 60; quan sát MaxInterval do thiết bị chọn | MaxInterval = IdleModeDuration (theo cấu hình) |
| T2.8 | Đồng bộ báo cáo | 2–3 subscriber (chip-tool + HA + Apple) → sniffer: các ReportData nằm trong cùng một cửa sổ active | Không có wake riêng lẻ cho từng subscriber |
| T2.9 | Ngưỡng báo cáo | Thổi hơi ấm/đặt gần cốc nước ấm → đếm số báo cáo/biến thiên | Chỉ báo khi vượt ΔT/ΔRH, có giới hạn tần suất |
| T2.10 | UAT bằng nút | Ở LIT, nhấn nút → thiết bị active, controller gửi lệnh được ngay | Phản hồi trong ActiveModeDuration |
| T2.11 | Identify | `chip-tool identify identify 10 <node> 1` | LED nháy 10 s; thiết bị giữ active |
| T2.12 | Multi-admin | Mở cửa sổ từ admin 1 (`pairing open-commissioning-window`), ghép admin 2 | Hai fabric hoạt động song song |
| T2.13 | Factory reset | Giữ nút 10 s | Xoá fabric, mở lại cửa sổ commissioning |
| T2.14 | Thay pin | Tháo pin 10 s / 1 phút / 1 giờ rồi lắp lại | Tự nối lại Thread < 10 s (cùng parent); subscription khôi phục (persisted subscription / Check-In) |
| T2.15 | Mất parent | Tắt router đang là parent | Re-attach sang router khác; dòng khi mồ côi theo backoff đã cấu hình |
| T2.16 | BR khởi động lại / đổi kênh Thread | Reboot OTBR; đổi kênh qua pending dataset | Thiết bị theo được, không cần ghép lại |
| T2.17 | OTA (nếu bật) | `ota-provider-app` + `chip-tool otasoftwareupdaterequestor announce-otaprovider`; thử ảnh hỏng/sai chữ ký | Cập nhật thành công; ảnh xấu bị từ chối, không brick |
| T2.18 | Pin yếu khi commissioning | Nguồn 2,4 V + 60 Ω, giữ nút 3 s | Từ chối mở cửa sổ, báo LED pin yếu |
| T2.19 | Matter Test Harness (tiền chứng nhận) | Chạy các nhóm TC-DA, TC-SC, TC-CADMIN, TC-ICDM, TC-TMP, TC-RH, TC-PS, TC-DESC, TC-BINFO, TC-OTA (nếu có) bằng TH của CSA | Pass trước khi gửi lab |

## T3. RF & tầm phủ

| ID | Kiểm tra | Ghi chú |
|---|---|---|
| T3.1 | **S11 anten** bằng VNA: hàn pigtail coax bán cứng vào điểm nối mạng phối hợp anten, đo **có vỏ, có pin, đặt trên bàn và trên tường** | Mục tiêu S11 < −10 dB trong 2400–2483,5 MHz; chỉnh mạng π (3 linh kiện) |
| T3.2 | Công suất dẫn (bản prototype có đệm test hoặc U.FL tuỳ chọn) | RAILtest `setPower`, đo bằng máy phân tích phổ/power meter |
| T3.3 | Hài bậc 2/3 (2,4/4,8/7,2 GHz) | Tiền tuân thủ FCC 15.247/ETSI EN 300 328 (chỉ bản chip trần) |
| T3.4 | Độ nhạy RX/PER | RAILtest + máy phát chuẩn hoặc DK tham chiếu, so với datasheet |
| T3.5 | **So sánh bức xạ** với DK tham chiếu (xG24 Explorer Kit) | Cùng vị trí, đo RSSI tại parent (`ot-ctl child table` / `neighbor table`) ở 8 hướng → ước lượng chênh lệch dB |
| T3.6 | Tầm thực tế trong nhà | 3 vị trí: 5 m/1 tường, 10 m/2 tường, 15 m/3 tường; 24 h mỗi vị trí, ghi RSSI/LQI, số retry MAC (`ot-ctl counters mac`), báo cáo bị mất |
| T3.7 | Ảnh hưởng tay/tường/kim loại | Cầm trên tay, dán lên tường bê tông, đặt gần tủ lạnh/khung kim loại |
| T3.8 | Wi-Fi 2,4 GHz bận | Chạy iperf trên kênh Wi-Fi trùng kênh Thread; ghi tỷ lệ báo cáo thành công và số retry |

## T4. Dòng tiêu thụ

**Thiết bị đo** (một trong hai):
- **Simplicity Energy Profiler + AEM** trên WSTK/Pro Kit (BRD4002A) ở chế độ cấp nguồn cho bo ngoài qua đầu ra debug/VMCU; ưu điểm: đồng bộ với code (PC sampling), nhược: dải đo/độ phân giải thấp hơn PPK2 ở vùng µA [KN: kiểm tra spec AEM của bộ kit đang dùng].
- **Nordic PPK2** ở **source mode 3,0 V** nối vào tiếp điểm pin qua **"pin giả" CR2450** (đĩa in 3D/PCB Ø24,5 mm có 2 dây) → đo cả MOSFET chống ngược và tụ dự trữ; hoặc **ammeter mode** nối tiếp với pin thật để thấy sụt áp thật.

**Lưu ý đo**: rút debugger (SWD kết nối có thể giữ debug domain → EM2 không thật); tắt log; đo ít nhất 24 h cho trung bình; ghi lại nhiệt độ phòng.

| ID | Đại lượng | Cách đo | Cập nhật vào `tools/power_budget.py` |
|---|---|---|---|
| T4.1 | Dòng nền EM2 | Cửa sổ 10 s giữa hai poll | `i_em2_ua + i_leak_ua + i_sensor_idle_ua` |
| T4.2 | Điện tích 1 poll | Tích phân diện tích xung poll (µC) | `t_poll_*`, `t_wake_ms` |
| T4.3 | Điện tích 1 lần đo SHT4x | Kích đo bằng nút/timer, tích phân | `q_sensor_uc + q_meas_cpu_uc` |
| T4.4 | Điện tích 1 lần báo cáo (1, 2, 3 subscriber) | Tạo thay đổi nhiệt, tích phân từ wake tới khi về idle | `q_report_event()` |
| T4.5 | Đuôi active mode | Đếm số fast-poll sau báo cáo | `active_mode_threshold_ms`, `fast_poll_ms` |
| T4.6 | CASE / SRP / Check-In | Reboot controller → thiết bị dựng lại session | `q_srp_uc`, `q_checkin_uc` |
| T4.7 | Commissioning | Từ lúc lắp pin tới khi ghép xong (mAh) | Ghi chú tài liệu |
| T4.8 | Mồ côi (mất parent) | Tắt toàn bộ router 2 h | `q_attach_uc`, backoff |
| T4.9 | Trung bình 24 h thực tế | Mạng thật, 2–3 hệ sinh thái | So với mô hình (sai lệch > 30 % → tìm nguyên nhân) |
| T4.10 | Sụt áp pin thật | PPK2 ammeter + dao động ký đo VBAT khi TX, ở 25 °C và trong ngăn đông (−18 °C) | Biên áp so với BOD |

**Kiểm thử tăng tốc**: firmware test với tần suất báo cáo × 20 trên pin thật để thu đường cong VBAT(t) và kiểm tra thuật toán % pin (đi xuống đơn điệu, cảnh báo Warning/Critical đúng lúc).

## T5. Độ chính xác nhiệt độ/độ ẩm

**Chuẩn tham chiếu**: nhiệt kế/ẩm kế có giấy hiệu chuẩn truy xuất được (ví dụ đầu dò PT100 hạng A/1/3 DIN, hoặc thiết bị dùng SHT45/HYT có chứng chỉ; với RH: muối bão hoà hoặc máy chuẩn).

| ID | Kiểm tra | Cách làm | Tiêu chí (SHT40) |
|---|---|---|---|
| T5.1 | Sai số tĩnh | Hộp xốp kín không quạt trong phòng ổn định; DUT + chuẩn cạnh nhau; chờ ≥ 60 phút; log 4 h; lặp ở ~18, 25, 30 °C (phòng/điều hoà) hoặc buồng nhiệt ẩm | \|ΔT\| ≤ 0,3 °C; \|ΔRH\| ≤ 3 %RH |
| T5.2 | Tự sưởi | So sánh T đo khi: ngủ bình thường / commissioning 5 phút / báo cáo 1 lần/giây trong 10 phút / LED sáng liên tục | Tăng < 0,1 °C ở chế độ thường; ghi lại mức tăng ở chế độ nặng |
| T5.3 | Thời gian đáp ứng | Chuyển DUT từ 20 °C sang 30 °C (hai phòng/hộp), đo τ63 của T và RH, có vỏ và không vỏ | Ghi τ63; mục tiêu τ63(T) < 10 phút có vỏ [TT] |
| T5.4 | Ảnh hưởng gắn tường | Dán lên tường ngoài (lạnh) vs tường trong | Định lượng chênh lệch; tối ưu khe hở lưng vỏ |
| T5.5 | Ảnh hưởng tay cầm | Cầm 30 s, đo thời gian hồi về ±0,1 °C | Ghi lại |
| T5.6 | RH 2 điểm bằng muối bão hoà | MgCl₂ (~33 %RH) và NaCl (~75 %RH) ở 25 °C, hộp kín 12–24 h | Trong ±3 %RH |
| T5.7 | Độ trôi dài hạn | Log 2–4 tuần cạnh chuẩn | Không trôi > 0,1 °C/tháng |
| T5.8 | Sau ngưng tụ | Để trong môi trường > 90 %RH 24 h, rồi bật heater theo quy trình phục hồi | RH trở về đúng |

Kết quả T5.1 dùng để quyết định có cần **hiệu chỉnh offset theo từng thiết bị** (lưu token trong flash) hay chỉ offset chung theo thiết kế vỏ.

## T6. Tương thích hệ sinh thái

Ma trận (mỗi ô: commissioning ×5, theo dõi 7 ngày):

| Hệ sinh thái | Border router / hub | Kiểm tra riêng |
|---|---|---|
| Apple Home | HomePod mini / Apple TV 4K (bản OS mới nhất) | Cảnh báo "phụ kiện chưa chứng nhận" với DAC test; hiển thị pin, nhiệt, ẩm; độ trễ automation |
| Google Home | Nest Hub (2nd gen)/Nest Hub Max/Nest Wifi Pro/Google TV Streamer | **Phải tạo project trên Google Home Developer Console với VID/PID** (kể cả VID test 0xFFF1) trước khi ghép |
| Home Assistant | HA OS + Matter Server + OTBR (ZBT-1/ZBT-2 hoặc dùng chung BR của Apple/Google) | Thực thể pin %, áp pin, loại pin; trạng thái ICD/LIT; bản đồ Thread |
| SmartThings | Station / hub có Thread | Bật developer mode cho thiết bị test |
| Alexa (tuỳ chọn) | Echo có Thread BR | — |

Với mỗi hệ sinh thái ghi: thành công ghép, thời gian ghép, **OperatingMode (SIT/LIT) sau khi ghép**, MaxInterval thực tế, số lần "Không phản hồi" trong 7 ngày, số báo cáo/ngày, % pin hiển thị so với tính toán, hành vi sau khi hub khởi động lại.

## Tiêu chí "đóng băng" thiết kế (gate)

1. T1 đạt toàn bộ trên ≥ 3 bo.
2. T4.9: dòng trung bình đo được ≤ ngân sách (mục 6) với hệ số an toàn → tuổi thọ dự báo ≥ 18 tháng.
3. T3.5: suy hao bức xạ so với DK ≤ 6 dB (nếu kém hơn → sửa vị trí anten/kích thước bo).
4. T5.1: sai số sau hiệu chỉnh trong tiêu chí.
5. T6: ghép và chạy ổn 7 ngày trên ít nhất Apple Home, Google Home, Home Assistant.
