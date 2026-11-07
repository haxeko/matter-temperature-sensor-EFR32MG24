# 3. Tham khảo sản phẩm thương mại

> Mỗi thông tin được gắn mức tin cậy:
> **[CHÍNH THỨC]** tài liệu, trang sản phẩm, hồ sơ CSA/DCL của hãng ·
> **[CỘNG ĐỒNG]** log/diagnostics công khai do người dùng đăng, hoặc phân tích ảnh firmware công khai trên DCL ·
> **[ĐOÁN]** suy luận của tôi.
> Tra cứu ngày 07/11/2026. Nguồn ghi ở cuối mỗi mục.

## 3.1 Tóm tắt

| Sản phẩm | Pin | Tuổi thọ công bố | Giao thức / vai trò | Hành vi báo cáo | Sai số công bố |
|---|---|---|---|---|---|
| **Eve Weather** | 1×CR2450 | "1+ năm" (tài liệu 2021) | Matter 1.3 (fw 3.5.0) / Thread MTD sleepy, có ICD Management | Ghi lịch sử 10 phút/lần [CHÍNH THỨC]. Báo đủ T/RH/áp suất mỗi 600 s, keep-alive rỗng khoảng 103 s [CỘNG ĐỒNG] | ±0,3 °C, ±3 %RH, ±1 mbar |
| **Aqara Climate Sensor W100** | 2×CR2450 (song song [ĐOÁN]) | Tới 2,3 năm (Thread), 2,4 năm (Zigbee) | Matter 1.3 / SED, **SIT, IdleModeDuration 300 s, AMT 1000 ms, FeatureMap 0** [CỘNG ĐỒNG] | Ở Thread không cấu hình được. Ở Zigbee chỉnh được ngưỡng 0,2–3 °C / 2–10 %RH hoặc chu kỳ 1–600 s | ±0,2 °C, ±2 %RH |
| **IKEA TIMMERFLOTTE** (E2314) | 2×AAA (khuyên NiMH LADDA) | Khoảng 24 tháng | Matter 1.3 (fw test 1.2.2 lên 1.5, Thread 1.4) / SED. **SoC EFR32MG24 + Sensirion SHT4x** [CỘNG ĐỒNG: chuỗi trong ảnh OTA trên DCL] | Subscription [0, 300]: báo cáo khoảng **293 s/lần, không có gì ở giữa** [CỘNG ĐỒNG] | Không công bố |
| **Onvis** | — | — | **Không có cảm biến T/RH Matter** (DCL chỉ có S4, T20). SMS2 (chuyển động + T/RH) là HomeKit-over-Thread, 2×AAA, "1 năm" | — | ±0,3 °C, ±5 %RH (SMS2) |
| **Aqara T1** (Zigbee 3.0, so sánh) | 1×CR2032 | Khoảng 2 năm (nhà bán lẻ) | Zigbee end device | **Báo ngay nếu ΔT > 0,5 °C hoặc ΔRH > 6 %, không thì 1 giờ/lần** [CHÍNH THỨC, qua bản sao FAQ] | ±0,3 °C, ±3 %RH |

**Chưa sản phẩm nào được chứng minh là chạy LIT.** W100 chỉ có SIT (FeatureMap = 0). Với Eve và IKEA, DCL không có hint UAT nên nhiều khả năng cũng chỉ SIT [ĐOÁN].

## 3.2 Chu kỳ lấy mẫu, chu kỳ báo cáo, ngưỡng

| Sản phẩm | Lấy mẫu | Báo cáo | Nhận xét |
|---|---|---|---|
| Eve Weather | 10 phút (ghi lịch sử) [CHÍNH THỨC] | Báo đủ 600 s; keep-alive khoảng 103 s; SII 4,5 s, SAI 2,3 s [CỘNG ĐỒNG, 1 mạng] | SII 4,5 s cho thấy slow poll ≤ 4,5 s [ĐOÁN]. Rất tốn so với giới hạn SIT 15 s |
| W100 | Ở Thread không công bố. Ở Zigbee: 0,5–600 s | Ở Thread: MaxInterval ≈ IdleModeDuration = 300 s | Thiết kế SIT "an toàn" phổ biến |
| TIMMERFLOTTE | Không rõ | Định kỳ khoảng 5 phút. SII 15,8 s gợi ý slow poll khoảng 15 s, fast poll khoảng 0,5 s, AMT khoảng 1 s [ĐOÁN] | Kiểu "báo định kỳ", không thấy báo theo ngưỡng |
| Aqara T1 | Không rõ | Ngưỡng 0,5 °C / 6 %RH, hoặc 1 h | Ngưỡng thô, ít báo cáo, pin bền |

**Thiết kế này** (mục 2.4, 5.3):
- Lấy mẫu 30 s, chỉ dùng MCU và I²C.
- Vùng chết hai tầng: cứng 0,2 °C / 2 %RH (gửi ngay); mềm 0,1 °C / 1 %RH (đi kèm lần thức kế tiếp hoặc tối đa 15 phút).
- Giới hạn 1 báo cáo/60 s. Keep-alive 30 phút.
- Kết quả: đồ thị mịn hơn T1 (0,5 °C) và phản hồi nhanh hơn kiểu báo định kỳ 5 phút của IKEA, mà không phải thức radio thêm.

## 3.3 Ước tính % pin và báo pin yếu

| Sản phẩm | Cách làm | Vấn đề ghi nhận |
|---|---|---|
| Aqara T1/WSDCGQ11LM | Zigbee2MQTT ánh xạ tuyến tính 2850–3000 mV sang 0–100 % [CỘNG ĐỒNG: mã converter] | Rơi khỏi mạng khi % vẫn "đầy", vì áp nghỉ phẳng, sụt áp khi phát không được đo |
| Eve Weather | Không công bố | % nhảy 100→75→100; có pin "chết" ở 30–40 % [CỘNG ĐỒNG] |
| TIMMERFLOTTE | Firmware có chuỗi `battery measure:%dmV %d%%` và `Low battery, stopped working!!!`. Khoảng 3,0 V hiển thị 100 % [CỘNG ĐỒNG] | Pin yếu: LED đỏ + thông báo app [CHÍNH THỨC] |
| W100 | Power Source: 3120 mV, 100 %, `"CR2450"`, quantity 2 [CỘNG ĐỒNG] | % có thể mất tới 24 h mới hiện (Zigbee) |
| KLIPPBOK (IKEA) | Kêu bíp mỗi 5 h khi pin yếu [CHÍNH THỨC] | — |

**Bài học**: chỉ dựa vào áp nghỉ thì % không có ý nghĩa với Li/MnO2. Thiết kế này dùng **đếm điện tích + trần theo áp có bù nhiệt + áp tải lúc TX + đếm reset BOD**, % chỉ giảm, đổi theo bước 2 %, và `BatChargeLevel` chốt mức (mục 5.5, `battery_estimator.cpp`).

## 3.4 Cơ khí để đo đúng nhiệt độ môi trường

| Sản phẩm | Điểm đáng chú ý |
|---|---|
| Eve Weather | Thân nhôm, IPX4, dùng ngoài trời [CHÍNH THỨC]. Khối nhiệt lớn nên đáp ứng chậm. Một reviewer thấy lệch "vài độ" so với Apple Weather (ngoài trời còn có nắng) [CỘNG ĐỒNG] |
| W100 | Khe thông gió ở **góc dưới bên trái**, xa màn hình. Hãng dặn chỉ dùng trong nhà, tránh nắng và nguồn nhiệt [CHÍNH THỨC/CỘNG ĐỒNG] |
| Onvis SMS2 | Khe thông gió **trên và dưới** (đối lưu kiểu ống khói). Có hiệu chỉnh offset trong app [CỘNG ĐỒNG] |
| TIMMERFLOTTE | Màn hình chỉ sáng khi chạm rồi tắt, nên không tự sưởi liên tục [CHÍNH THỨC]. Ø65 × 18 mm |
| Aqara T1 | 36×36×9 mm, rất nhỏ, khối nhiệt thấp [CHÍNH THỨC] |

Khuyến nghị Sensirion (Design Guide) áp vào vỏ của bạn:
- Khoang cảm biến nhỏ, **kín với phần còn lại của vỏ** (gân nhựa hoặc gioăng xốp).
- Lỗ thông gió lớn sát cảm biến, tốt nhất ở **hai độ cao**.
- Vật liệu ABS/PC, **không dùng PA/nylon** (hút ẩm).
- Tối đa 1 màng cho mỗi lỗ. Ngón tay không chạm được cảm biến (chống ESD).
- Vỏ sáng màu, có chân đế/khoảng hở 2–3 mm khi dán tường.

## 3.5 Tuổi thọ pin công bố và cấu hình ICD/Thread có thể đang dùng

So sánh thô dòng trung bình **ngầm định** từ tuổi thọ công bố [ĐOÁN, giả định dùng 80 % dung lượng]:

| Sản phẩm | Năng lượng | Tuổi thọ | I_avg ngầm định | Cấu hình quan sát/suy luận |
|---|---|---|---|---|
| Eve Weather | 1×CR2450 ≈ 620 mAh | ≥ 1 năm | ≤ khoảng 55 µA | Có LCD, poll ≤ 4,5 s, báo 600 s, keep-alive khoảng 100 s |
| W100 | 2×CR2450 ≈ 1240 mAh | 2,3 năm | khoảng 50 µA | LCD 3,4", SIT, idle 300 s, AMT 1 s |
| TIMMERFLOTTE | 2×AAA NiMH | 24 tháng | khoảng 40–50 µA | LED matrix khi chạm, SIT khoảng 15 s, báo 5 phút |
| Aqara T1 | 1×CR2032 ≈ 220 mAh | khoảng 2 năm | khoảng 10 µA | Zigbee, ít báo cáo |
| **Thiết kế này** | 1×CR2450 | mục tiêu ≥ 18 tháng | **mô hình khoảng 5 µA** (cho phép tới khoảng 21 µA) | Không màn hình, SIT 15 s ↔ LIT, idle 1800 s |

Các sản phẩm có màn hình tiêu thụ cao hơn khoảng 10 lần. Mục tiêu 18 tháng với 1×CR2450 là **khả thi và còn biên rộng**, *với điều kiện* firmware được cấu hình đúng như mục 5. Rủi ro nằm ở cấu hình phần mềm, không ở phần cứng.

## 3.6 Bài học trực tiếp cho thiết kế này

1. **TIMMERFLOTTE là bằng chứng sống cho đúng nền tảng này** (MG24 + SHT4x, SIT). Ta không phát minh gì rủi ro.
2. **Rớt mạng của IKEA** [CỘNG ĐỒNG, OpenThread issue #13701]:
   - GSDK 4.4.x đặt `CHILD_SUPERVISION_CHECK_TIMEOUT = 0`.
   - Khi parent khởi động lại và "quên" child, thiết bị ngủ không bao giờ phát hiện. Chỉ tháo pin mới hết.
   - SiSDK 2024.12.2 đã sửa.
   - Thiết kế này dùng SiSDK 2026.6.2 + Matter extension 2.9.2. Silicon Labs đặt check timeout = `SL_IDLE_MODE_DURATION_S` khi bật ICD. Thêm biện pháp ở mục 5.7: khi chạy **SIT**, đặt check timeout khoảng 190 s lúc chạy để phục hồi trong vài phút.
3. **IdleModeDuration**: hàng thương mại dùng 300 s. Thiết kế này chọn **1800 s** (bằng mặc định ví dụ multi-sensor của Silicon Labs). Keep-alive giảm khoảng 1,2 µA so với 300 s, controller vẫn phát hiện thiết bị chết trong ≤ khoảng 30 phút.
4. **OTA qua Thread của thiết bị ngủ chậm và dễ timeout** (Eve: khoảng 9 phút, hay lỗi nếu không là child trực tiếp của OTBR) [CỘNG ĐỒNG]. Giữ ảnh OTA nhỏ (LZMA). Thiết bị ở active trong suốt phiên BDX (mục 2.7).
5. **Subscription "liveness timeout" trên HA** gặp ở W100 (sự kiện nút ngừng sau 1–2 ngày) và TIMMERFLOTTE (timeout hằng ngày) [CỘNG ĐỒNG]. Đưa vào T6: theo dõi ≥ 7 ngày, có HA làm một trong các controller.

### Nguồn chính
- Eve Weather: evehome.com (Reviewer Guide 2021 + trang sản phẩm); csa-iot.org/csa_product/eve-weather-2; matteralpha.com; matter-js/matterjs-server issue #411 (log); community.home-assistant.io (OTA).
- W100: aqara.com specs; csa-iot.org/csa_product/climate-sensor-w100; python-matter-server issue #1168 (diagnostics); zigbee2mqtt.io/devices/TH-S04D.
- IKEA: hướng dẫn sử dụng TIMMERFLOTTE/MYGGSPRAY/MYGGBETT/KLIPPBOK trên ikea.com; csa-iot.org (TIMMERFLOTTE); ảnh OTA 1.0.21 trên DCL (on.dcl.csa-iot.org …/4476/32773/16777237); releases.homesmart.ikea.com (fw test 1.2.2); openthread/openthread issue #13701; home-assistant/app-matter-server issue #6.
- Onvis: DCL vendor 5181; manualslib (SMS2); homekitnews.com.
- Aqara T1: aqara.com specs; FAQ qua smart-secure.co.uk; zigbee-herdsman-converters `lumi.ts`.
