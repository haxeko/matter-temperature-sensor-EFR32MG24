# 5. Firmware

> Nhãn: **[SPEC]** · **[SDK]** đã đối chiếu mã nguồn/tài liệu Silicon Labs, connectedhomeip · **[KN]** · **[TT]** · **[ĐOÁN]**.
> Phần logic không phụ thuộc phần cứng đã được viết và có test host trong `firmware/app-logic/` (xem 5.11).

## 5.1 Nền tảng và dự án khởi đầu

| Hạng mục | Lựa chọn | Ghi chú |
|---|---|---|
| IDE | **Simplicity Studio v6** | Extension mới chỉ hỗ trợ v6 |
| SDK | **Simplicity SDK (SiSDK) 2026.6.2** | GSDK không còn dùng cho Matter kể từ extension v2.3.0 (06/2024) |
| Matter | **Silicon Labs Matter extension v2.9.2-1.6** (GA 19/10/2026, Matter 1.6) | v2.10.0 (nhánh 1.6.1) đang pre-release. Chưa dùng cho sản phẩm |
| Ví dụ gốc | **"Matter Thread - SoC Multi Sensor FreeRTOS"** (`matter_thread_soc_multi_sensor_app_freertos`) | Mặc định đã là LIT ICD, có sẵn cluster Temperature Measurement + Relative Humidity (+ Occupancy), driver `matter_si70xx_sensor` |
| Bootloader | Biến thể **"with internal bootloader"** | OTA lưu trong flash nội, nén LZMA. Biến thể "external bootloader" dùng SPI flash và **làm tăng dòng EM2** |

Các bước chuyển ví dụ thành sản phẩm:
1. Phát triển firmware trước trên kit xG24 (Explorer Kit BRD2703A hoặc BRD4186C + mainboard có AEM). Sau đó tạo **custom board** cho EFR32MG24B010F1536IM40 và gán chân bằng Pin Tool (bảng 4.9).
2. **ZAP**:
   - Xoá Occupancy.
   - EP1 = Temperature Sensor, EP2 = Humidity Sensor, mỗi endpoint có Identify.
   - EP0 thêm device type Power Source + cluster Power Source (BAT|REPLC) và OTA Requestor.
   - ICD Management: feature CIP|UAT|LITS (|DSLS).
   - Giá trị mặc định theo mục 2.1–2.3.
3. Thay driver Si70xx bằng SHT4x (`firmware/app-logic/include/sht4x.h` + một instance `i2cspm` trên **I2C1**).
4. Chỉnh component và cấu hình theo 5.9 và 5.10.
5. Đổi PID test (ví dụ 0x8105) để không trùng PID 0x8005 của ví dụ khi khai báo trên Google Developer Console.

## 5.2 Kiến trúc phần mềm

```
FreeRTOS
├── CHIP task (Matter stack, ICD Manager, ReportScheduler)  ← mọi lần ghi thuộc tính phải khoá stack
├── OpenThread task (MTD/SED, RAIL)
├── BLE (chỉ khi commissioning)
└── AppTask (hàng đợi sự kiện)
     ├── SensorService   : SHT4x qua I2C1, timer đo 30 s (sl_sleeptimer)        → sht4x.h
     ├── ReportPolicy    : vùng chết cứng/mềm, giới hạn tần suất, null khi lỗi  → report_policy.{h,cpp}
     ├── BatteryService  : IADC (AVDD/4), BatteryEstimator, NVM3                → battery_estimator.{h,cpp}
     ├── ButtonFsm + Led : nhấn ngắn/3 s/7 s/10 s, mẫu nháy                    → button_fsm.h
     ├── IcdPolicy       : quan sát ICD (ICDStateObserver), chính sách DSLS đa fabric
     └── AttributeWriter : ghi T/RH/pin trong MỘT lần LockChipStack
```

## 5.3 Luồng hoạt động: ngủ EM2 → đo → so ngưỡng → báo cáo → ngủ

```
            ┌──────────────────────────── EM2 (2,9 µA) ─────────────────────────────┐
            │  Thread poll 15 s (SIT) / 30 phút (LIT) do OpenThread tự lo           │
            ▼                                                                        │
[sleeptimer 30 s] → AppTask: I2C1 gửi 0xFD → vTaskDelay(9 ms) (CPU về EM2) → đọc 6 byte, CRC
            │
            ▼
   ReportPolicy.OnSample(now, T, RH)
      ├─ |Δ| < ngưỡng mềm ............................................. ngủ lại (radio KHÔNG bật)
      ├─ ngưỡng mềm ≤ |Δ| < ngưỡng cứng ..... đánh dấu pending, ngủ lại (chờ "cơ hội" hoặc 15 phút)
      └─ |Δ| ≥ ngưỡng cứng và đã ≥ 60 s từ lần trước:
             LockChipStack → ghi MeasuredValue (T, RH) [+ pin nếu đổi] → UnlockChipStack
             → ReportScheduler gửi ReportData cho MỌI subscriber (đồng bộ)
             → ICD vào Active: fast poll 500 ms, nhận StatusResponse, gửi MRP ACK
             → 5 s không còn hoạt động mạng → Idle (slow poll)

ICDStateObserver::OnEnterActiveMode()   (radio đã thức vì lý do khác: keep-alive, Check-In, nút)
      → AppTask: ReportPolicy.OnOpportunity() → nếu có pending thì ghi luôn (miễn phí radio)
```

Mã khung (API thuộc tính kiểm tra theo bản extension; một số cluster đã chuyển sang dạng "code-driven" ở SDK 1.5/1.6, nên **làm theo cách ví dụ multi-sensor đang ghi nhiệt độ**) [SDK][ĐOÁN về tên hàm]:

```cpp
// AppTask — mỗi 30 s
void SensorService::OnMeasureTimer()
{
    uint8_t cmd = tsensor::sht4x::kCmdMeasureHigh, rx[6];
    tsensor::sht4x::Measurement m{};
    bool ok = I2c1Write(tsensor::sht4x::kAddrAD1B, &cmd, 1) == 0;
    vTaskDelay(pdMS_TO_TICKS(9));                       // tickless idle -> EM2
    ok = ok && I2c1Read(tsensor::sht4x::kAddrAD1B, rx, 6) == 0 && tsensor::sht4x::Parse(rx, m);
    mLastTempCenti = ok ? m.temperatureCenti : mLastTempCenti;   // dùng cho bù nhiệt pin
    auto d = mPolicy.OnSample(NowSeconds(), {ok, m.temperatureCenti, m.humidityCenti});
    if (d.Any()) AttributeWriter::Publish(d, mBattery.EvaluateIfDue());
}

void AttributeWriter::Publish(const tsensor::Decision & d, const BatteryUpdate & b)
{
    using namespace chip::app::Clusters;
    chip::DeviceLayer::PlatformMgr().LockChipStack();
    if (d.publishNull) {
        TemperatureMeasurement::Attributes::MeasuredValue::SetNull(1);
        RelativeHumidityMeasurement::Attributes::MeasuredValue::SetNull(2);
    } else {
        if (d.publishTemperature) TemperatureMeasurement::Attributes::MeasuredValue::Set(1, d.temperatureCenti);
        if (d.publishHumidity)    RelativeHumidityMeasurement::Attributes::MeasuredValue::Set(2, d.humidityCenti);
    }
    if (b.changed) {                                      // gộp vào cùng ReportData
        PowerSource::Attributes::BatPercentRemaining::Set(0, b.report.halfPercent);
        PowerSource::Attributes::BatVoltage::Set(0, b.report.voltageMv);
        PowerSource::Attributes::BatChargeLevel::Set(0, static_cast<PowerSource::BatChargeLevelEnum>(b.report.level));
        PowerSource::Attributes::BatReplacementNeeded::Set(0, b.report.replacementNeeded);
    }
    chip::DeviceLayer::PlatformMgr().UnlockChipStack();
}

// Quan sát ICD (4 hàm ảo của chip::app::ICDStateObserver)
class AppIcdObserver : public chip::app::ICDStateObserver {
    void OnEnterActiveMode() override  { AppTask::Post(AppEvent::kRadioOpportunity); }
    void OnEnterIdleMode() override    {}
    void OnTransitionToIdle() override {}
    void OnICDModeChange() override    { AppTask::Post(AppEvent::kIcdModeChanged); } // SIT<->LIT
};
// Đăng ký sau khi Server init: chip::Server::GetInstance().GetICDManager().RegisterObserver(&sObserver);
```

**Bẫy cần tránh**: không gọi `Set()` khi giá trị không đổi. Không ghi T và RH ở hai lần khoá stack khác nhau (thành 2 báo cáo). Không dùng một timer riêng để "đẩy" pin.

## 5.4 Nút bấm và LED

Logic nằm trong `ButtonFsm` (đã có test). Lớp platform:
- Ngắt GPIO **cổng A/B** (chỉ cổng A/B đánh thức được từ EM2) gọi `OnPress/OnRelease` sau khi chống dội 20–30 ms.
- Một sleeptimer 100 ms chỉ chạy **khi nút đang giữ** gọi `OnTick`.

| Sự kiện | Chưa ghép (không có fabric) | Đã ghép | LED (1 LED đỏ/hổ phách) |
|---|---|---|---|
| **Nhấn ngắn** (< 3 s) | Mở lại cửa sổ commissioning 15 phút (nếu pin OK) | **UAT**: `ICDNotifier::GetInstance().NotifyNetworkActivityNotification()` (như `BaseApplication`), cộng `ReportPolicy.ForcePublish()`: đo và báo cáo ngay | Mạng OK: 1 × 100 ms · Không có parent: 3 × 50 ms · Pin Warning/Critical: thêm 5 × 30 ms |
| **Giữ tới 3 s** | — | — | 1 × 300 ms ("nhả ra ngay để thực hiện") |
| **Nhả trong 3–7 s** | Mở cửa sổ commissioning | UAT kéo dài (trong `ActiveModeThreshold`) + nháy mã trạng thái: 1 = OK, 2 = mất parent, 3 = pin yếu | Mã trạng thái |
| **Giữ tới 7 s** | Cảnh báo reset | Cảnh báo reset | Nháy nhanh 10 Hz (25 ms bật / 75 ms tắt) |
| **Nhả trong 7–10 s** | Huỷ | Huỷ | 2 × 200 ms |
| **Giữ đủ 10 s** | Factory reset | **Factory reset**: xoá fabric/NVM ứng dụng, giữ factory data, khởi động lại, mở cửa sổ commissioning | Sáng liền 1 s |

Không dùng nút để mở cửa sổ BLE khi đã có fabric. Đây cũng là hành vi mặc định của Silicon Labs; multi-admin làm qua chức năng chia sẻ của hệ sinh thái.

**Ánh xạ sang `BaseApplication` của Silicon Labs** [SDK]:
- Mặc định reset sau 3 s giữ + 3 s cửa sổ huỷ (LED nháy), tức 6 s tổng. Đổi `FACTORY_RESET_TRIGGER_TIMEOUT = 7000` và `FACTORY_RESET_CANCEL_WINDOW_TIMEOUT = 3000` để có đúng 10 s và cảnh báo từ giây thứ 7. Hai hằng này là `#define` trong `.cpp`, nên phải override hàm xử lý nút trong `AppTask` hoặc sửa bản sao.
- Nhấn ngắn khi đã ghép thì `BaseApplication` đã tự gọi UAT. Chỉ cần thêm `ForcePublish`.

**Mẫu LED khác**:

| Trạng thái | Mẫu | Điện tích ước tính |
|---|---|---|
| Khởi động | 1 × 50 ms | 0,1 mC |
| Cửa sổ commissioning mở | 1 × 30 ms mỗi 2 s | khoảng 30 µA trung bình (chỉ trong ≤ 15 phút) |
| Đang commissioning (BLE đã nối) | 2 × 30 ms mỗi 1 s | |
| Commissioning thành công | 3 × 150 ms | |
| Commissioning thất bại / hết giờ | 1 × 1 s | |
| Identify (cluster Identify) | 0,5 s bật / 0,5 s tắt trong `IdentifyTime`. Hiệu ứng: Blink = 1 × 0,5 s, Okay = 2 × 100 ms | |

LED đỏ/hổ phách (AlInGaP, Vf ≈ 1,8–2,1 V) vẫn sáng khi pin còn 2,2 V; LED xanh lá/lam (Vf ≈ 2,7–3,1 V) thì không. Dòng 1–2 mA là đủ với LED hiệu suất cao.

## 5.5 Đo pin và % pin

1. **Phần cứng**: không cần cầu chia. IADC của MG24 đo **AVDD/4 nội bộ**, mà AVDD nối thẳng vào VBAT sau MOSFET chống ngược [SDK: em_iadc.h có đầu vào AVDD/IOVDD/DVDD chia 4, không có đầu vào VBAT riêng]. Dòng rò bằng 0.
2. **Đo khi nào**:
   - (a) Lúc khởi động, trước khi bật radio: lấy áp nghỉ để phát hiện pin mới.
   - (b) Mỗi 6 h, lúc yên tĩnh, có bù nhiệt bằng nhiệt độ SHT40.
   - (c) **Áp tải**: lấy mẫu AVDD 4–8 lần trong cửa sổ active ngay sau một lần phát, giữ giá trị nhỏ nhất. Với tụ dự trữ, đây là chỉ báo tốt cho nội trở pin.
   - Nâng cao [ĐOÁN]: dùng PRS nối tín hiệu "radio đang TX" làm trigger cho IADC để đo đúng đỉnh sụt áp.
3. **Cấu hình IADC**: tham chiếu nội 1,21 V, OSR 32×, chuyển đổi đơn. `mV = raw × 1210 × 4 / 4095`.
   - Sau khi đo, **tắt clock IADC0**. Ngoại vi thuộc power domain PD0B/PD0D còn bật trong EM2 sẽ thêm **+0,93 / +1,1 µA** [datasheet]. Áp dụng tương tự cho I2C0, nên SHT40 dùng **I2C1** (domain PD1, tự tắt trong EM2).
4. **Thuật toán** (`BatteryEstimator`, đã test):
   - `% = min(% đếm điện tích, trần % theo áp nghỉ đã bù nhiệt)`. Chỉ giảm, đổi theo bước 2 %.
   - Warning ở ≤ 20 % hoặc áp tải < 2,4 V. Critical ở ≤ 5 %, áp tải < 2,2 V, hoặc khi có reset BOD. Mức đã chốt thì giữ cho tới khi thay pin.
   - Đếm điện tích: mỗi giờ cộng `I_mô_hình(chế độ SIT/LIT) × 3600 s`, cộng thêm phần của từng báo cáo, commissioning, OTA. Hệ số lấy từ `tools/power_budget.py` **sau khi hiệu chỉnh bằng số đo T4**.
   - Lưu NVM3 mỗi 12 h hoặc khi đổi mức. Dùng key thuộc vùng dành cho ứng dụng, không đụng vùng key của Matter/OpenThread.
   - Phát hiện pin mới: lúc khởi động, áp nghỉ ≥ 3,05 V trong khi ước tính đang lưu < 80 %.
5. **Đường cong áp→% của CR2450** trong mã hiện là **[ĐOÁN]**. Phải thay bằng đường cong đo ở T4 (thử tăng tốc).

## 5.6 Chính sách ICD (SIT/LIT) cho nhiều hệ sinh thái

Quy tắc của SDK: có **≥ 1 client** đăng ký trên **bất kỳ** fabric nào thì chạy LIT. Vì vậy khi một fabric (ví dụ HA) đăng ký Check-In còn fabric khác (ví dụ Apple) không, fabric kia có thể mất liên lạc sau khi hub của nó khởi động lại. Đề xuất (bật `CHIP_CONFIG_ENABLE_ICD_DSLS=1` và feature DSLS trong ZAP) [KN][ĐOÁN, cần kiểm ở T6]:

```cpp
// Gọi khi: khởi động, thêm/xoá fabric (FabricTable::Delegate), OnICDModeChange(), sau RegisterClient/UnregisterClient
void IcdPolicy::Evaluate()
{
    bool everyFabricHasClient = true;
    for (const auto & fabric : chip::Server::GetInstance().GetFabricTable()) {
        if (!HasRegisteredClient(fabric.GetFabricIndex())) { everyFabricHasClient = false; break; }
        // HasRegisteredClient: duyệt ICDMonitoringTable của fabric (xem cách ICDManager.cpp kiểm tra IsEmpty())
    }
    if (!everyFabricHasClient && !mSitRequested) {
        chip::app::ICDNotifier::GetInstance().NotifySITModeRequestNotification();   // ép SIT
        mSitRequested = true;
    } else if (everyFabricHasClient && mSitRequested) {
        chip::app::ICDNotifier::GetInstance().NotifySITModeRequestWithdrawal();     // cho phép LIT
        mSitRequested = false;
    }
}
```

Giá đánh đổi: ở cấu hình hỗn hợp, thiết bị tiêu thụ khoảng 1,2 µA nhiều hơn (kịch bản A thay vì B, mục 6). Đổi lại, không hệ sinh thái nào bị "mất" thiết bị.

## 5.7 Mất kết nối với parent Thread

| Tình huống | Cơ chế | Việc firmware ứng dụng làm |
|---|---|---|
| Parent không ACK poll hoặc khung dữ liệu | OpenThread thử lại MAC, rồi re-attach (Child Update hoặc Parent Request) | Không cần làm gì |
| Parent khởi động lại và "quên" child (vẫn ACK poll, nhưng không còn child trong bảng) | Child supervision: không nhận được khung nào từ parent trong check timeout thì gửi Child Update Request rồi re-attach. Silicon Labs đặt check timeout = `SL_IDLE_MODE_DURATION_S` (1800 s) khi bật ICD. **GSDK 4.4.x đặt 0 → IKEA TIMMERFLOTTE treo tới khi tháo pin** (mục 3.6) | Trong `OnICDModeChange()`: khi **SIT**, gọi `otChildSupervisionSetCheckTimeout(instance, 190)` (mặc định OpenThread, parent gửi supervision mỗi 129 s) để phục hồi trong khoảng 3 phút. Khi **LIT**, trả về `SL_IDLE_MODE_DURATION_S`, để check không đánh thức thiết bị giữa các poll dài [ĐOÁN: API có trong OpenThread `child_supervision.h`, cần thử T2.15] |
| Không tìm được parent nào | Backoff mũ: tối thiểu 251 ms, **tối đa 20 phút** (mặc định OpenThread). Mỗi lần thử nghe khoảng 2 s (khoảng 10–12 mC), nên khi mồ côi trung bình khoảng 8–10 µA | Tuỳ chọn: tăng `OPENTHREAD_CONFIG_MLE_ATTACH_BACKOFF_MAXIMUM_INTERVAL` lên 60 phút (khoảng 3 µA khi mồ côi kéo dài), đổi lại phục hồi chậm hơn sau mất mạng dài |
| Mạng trở lại | SIT: controller tự subscribe lại. LIT: thiết bị gửi Check-In ở lần active kế tiếp (và khi báo cáo không được ACK) | ReportPolicy gửi giá trị mới nhất (pending). **Không** lưu lịch sử: Matter không có chuẩn lịch sử |
| Người dùng nhấn nút khi mất mạng | — | LED 3 × 50 ms ("không có mạng") |
| BR đổi kênh / PAN | Pending Operational Dataset | — |

## 5.8 Thay pin, khởi động lại, sụt áp

Trình tự khởi động [KN]:
1. Đọc nguyên nhân reset bằng `RMU_ResetCauseGet()`: POR, BOD (AVDD/DVDD/DECOUPLE), PIN, WDOG, SYSREQ, LOCKUP. Sau đó xoá cờ.
2. Đo **áp nghỉ** bằng IADC trước khi bật radio (< 1 ms).
3. Nếu reset do BOD: tăng bộ đếm trong NVM3 (chỉ ghi khi có BOD, hiếm). Nếu **≥ 3 lần BOD trong 10 phút** hoặc áp nghỉ < 2,3 V, vào **chế độ pin yếu**:
   - TX Thread +0…+4 dBm.
   - Tắt LED trạng thái.
   - Không mở cửa sổ commissioning.
   - `BatChargeLevel = Critical`, `BatReplacementNeeded = true`.
   - Vẫn đo và báo cáo nếu còn chạy được.
4. Gọi `BatteryEstimator.OnBoot(vRest)` để nhận diện pin mới và reset bộ đếm điện tích.
5. Khởi động Matter/OpenThread. Dataset và fabric đọc từ NVM3; thiết bị gắn lại parent cũ bằng Child Update, nhanh.
6. Subscription: `matter_subscription_persistence` khôi phục subscription sau reboot. Ở LIT, thiết bị gửi Check-In lúc khởi động.
7. Đo ngay và **báo cáo mẫu đầu tiên** (ReportPolicy coi mẫu đầu là bắt buộc gửi).
8. Chưa có fabric và pin OK thì mở cửa sổ commissioning 15 phút.

Thêm:
- **Watchdog** WDOG0 chạy trong EM0/EM1, tạm dừng ở EM2, nên không phải đánh thức chỉ để "cho ăn" [ĐOÁN tên trường cấu hình `em2Run`].
- Factory data (DAC, verifier) nằm ở vùng provisioning riêng, **không** bị factory reset xoá.

## 5.9 Component: bật/tắt để giảm dòng (checklist)

| Thao tác | Component / cấu hình | Lý do |
|---|---|---|
| **Thêm** | `matter_platform_low_power` | Gỡ OT CLI, LCD/QR, Matter UART, log ra UART, shell [SDK] |
| **Thêm (sản phẩm)** | `matter_no_debug` (`SL_MATTER_LOG_LEVEL=SL_MATTER_LOG_NONE`) | Log tốn CPU và giữ UART |
| **Thêm** | `matter_no_lcd_shell` | |
| **Giữ** | `matter_icd_core`, `matter_icd_management`, `matter_icd_checkin_sender`, `matter_subscription_persistence` | ICD + LIT + khôi phục subscription. `matter_icd_core` kéo theo `ot_stack_mtd` |
| **Không thêm** | `matter_synchronized_sed` (SSED/CSL) | Chu kỳ CSL = poll interval, tối đa khoảng 10,5 s. Tốn hơn poll 15 s/30 phút (mục 6, kịch bản D) |
| **Gỡ** | Các instance button/LED của WSTK, `matter_si70xx_sensor`, Occupancy | Thay bằng 1 nút + 1 LED theo bo |
| Log khi phát triển | **Chỉ một**: `matter_log_rtt` (qua SWD, không tốn chân) hoặc `matter_log_uart` | Không bật cả hai |
| Bootloader | Internal storage + LZMA | Không dùng SPI flash: rẻ hơn, EM2 thấp hơn |
| Clock | LFXO 32,768 kHz cho SYSRTC/sleeptimer | LFRCO precision mode tốn thêm khoảng 0,6 µA ở EM2 [datasheet] |
| Ngoại vi | I2C1 cho SHT4x. Tắt clock IADC0 sau khi đo. GPIO không dùng để disabled | Tránh PD0B/PD0D (+0,9…+1,1 µA) |
| TX Thread | **+8 dBm** mặc định (`otPlatRadioSetTransmitPower`). Hạ xuống +4 dBm khi pin Warning hoặc T < 0 °C | Dòng đỉnh khoảng 13 mA thay vì 19,1 mA ở +10 dBm |
| TX BLE | 0…+4 dBm (điện thoại ở gần khi ghép) | Giảm dòng đỉnh khi commissioning |
| Credentials | `SL_MATTER_ENABLE_EXAMPLE_CREDENTIALS=0` ở bản sản phẩm (mặc định là 1) | Tránh vô tình dùng chứng chỉ test |
| Đo dòng | Rút debugger trước khi đo | SWD giữ debug domain, EM2 không thật |

## 5.10 Cấu hình ICD (Silicon Labs)

`sl_matter_icd_config.h` và "Matter Core Components" (`ICDServerBuildConfig.h`) [SDK; tên macro theo mã v2.9.2. Tài liệu web còn dùng tên cũ `SL_OT_IDLE_INTERVAL`…]:

```c
// ICDServerBuildConfig.h (mặc định đều = 0)
#define CHIP_CONFIG_ENABLE_ICD_LIT   1
#define CHIP_CONFIG_ENABLE_ICD_CIP   1
#define CHIP_CONFIG_ENABLE_ICD_UAT   1
#define CHIP_CONFIG_ENABLE_ICD_DSLS  1      // cho chính sách 5.6; để 0 nếu không dùng

// sl_matter_icd_config.h
#define SL_IDLE_MODE_DURATION_S       1800     // mặc định file: 600; multi-sensor: 1800
#define SL_ACTIVE_MODE_DURATION_MS    0        // mặc định file: 1000
#define SL_ACTIVE_MODE_THRESHOLD      5000     // bắt buộc ≥ 5000 khi LIT (script kiểm tra sẽ báo lỗi)
#define SL_TRANSPORT_IDLE_INTERVAL    1800000  // slow poll khi LIT; khi SIT SDK tự kẹp về 15 s
#define SL_TRANSPORT_ACTIVE_INTERVAL  500      // fast poll
// Child timeout tự tính = 2 × idle + 1; supervision check = SL_IDLE_MODE_DURATION_S (OpenThreadConfig.h)

// CHIPConfig / project config
#define CHIP_CONFIG_ICD_SHORT_IDLE_MODE_DURATION_SEC   1800   // = Idle: TẮT bẫy ShortIdle 60 s
#define CHIP_CONFIG_ICD_MAXIMUM_CHECK_IN_BACKOFF_SEC   7200
#define CHIP_CONFIG_ICD_CLIENTS_SUPPORTED_PER_FABRIC   2
#define CHIP_CONFIG_SYNCHRONOUS_REPORTS_ENABLED        1      // multi-sensor đã bật
// ICD_REPORT_ON_ENTER_ACTIVE_MODE = 1 (tên tuỳ chọn trong extension có thể khác — kiểm tra)
```

Sau khi build, đọc lại bằng `chip-tool icdmanagement read ...` (T2.4) để chắc giá trị thực trên thiết bị khớp với file.

## 5.11 Logic dùng chung đã viết sẵn (`firmware/app-logic/`)

| File | Chức năng | Test |
|---|---|---|
| `include/sht4x.h` | Lệnh SHT4x, CRC-8 (0x31/0xFF), chuyển raw sang 0,01 °C và 0,01 %RH | CRC 0xBEEF→0x92, các điểm biên |
| `include/report_policy.h`, `src/report_policy.cpp` | Vùng chết hai tầng, giới hạn 60 s, holdoff 15 phút, piggyback, null sau 3 lỗi | 6 kịch bản |
| `include/battery_estimator.h`, `src/battery_estimator.cpp` | % pin lai (đếm điện tích + trần theo áp), bù nhiệt, chốt mức, phát hiện pin mới, BOD | 8 kịch bản |
| `include/button_fsm.h` | Nhấn ngắn / 3 s / 7 s / 10 s | 6 kịch bản |

```bash
cmake -S firmware/app-logic -B build && cmake --build build && ctest --test-dir build   # 102 kiểm tra
```

Biên dịch với `-Wall -Wextra -Wpedantic -Wconversion -Werror -fno-exceptions -fno-rtti`. Mã không cấp phát động, nên đưa thẳng vào dự án Simplicity Studio được.

## 5.12 Provisioning và sản xuất

- **Matter Provisioning Tool** (`provision.py`, dòng lệnh; GUI không có trong Studio v6 25Q4) [SDK]:
  - Nạp một "generator firmware", nói chuyện qua **J-Link RTT** (đi qua SWD, nên dùng được với TC2030) hoặc BLE.
  - **Sinh khoá DAC ngay trên chip** (CSR) rồi ký bằng PAI. Trên Vault High khoá được bọc bằng PUF.
  - Ghi factory data: VID/PID, discriminator, verifier/salt/iteration, serial, DAC/PAI/CD.
  - In ra QR và mã 11 số cho nhãn.
  - `--generate` tạo bộ PAA/PAI/DAC/CD test (VID 0xFFF1).
  - Xem `provision.py --help` của bản extension đang dùng.
- **Bản chip trần**: đo sai lệch tần số (RAILtest CW) rồi ghi token **CTUNE** cho từng bo. Mặc định board của Silicon Labs khoảng 87–140, tuỳ layout.
- **Sản xuất số lượng**: dịch vụ **CPMS** của Silicon Labs nạp firmware và DAC riêng từng chip tại nhà máy (PAA Kudelski IoT; DAC cho test DCL miễn phí). Bạn cung cấp VID/PID/CD.
