# 2. Tuân thủ Matter

> Nhãn: **[SPEC]** bắt buộc theo spec · **[SDK]** hành vi của connectedhomeip/Silicon Labs SDK (đã đọc mã nguồn) ·
> **[KN]** khuyến nghị · **[TT]** kinh nghiệm thực tế · **[ĐOÁN]** suy đoán, cần kiểm chứng.
> Mã nguồn tham chiếu: `project-chip/connectedhomeip` nhánh master (commit 11/2026, trùng tag `v1.6.1.0`).

## 2.0 Cập nhật phiên bản spec — 1.5 không còn là bản mới nhất

Tính đến 11/2026, các bản đã phát hành là:

| Bản | Ngày | Ghi chú liên quan tới thiết bị này |
|---|---|---|
| 1.4 | 07/11/2024 | ICD Management rev 3: thêm `ClientType`, `MaximumCheckInBackoff`, feature **DSLS**; LIT/CIP/UAT hết "provisional" |
| 1.4.1 / 1.4.2 | 05/2025 / 08/2025 | Không đổi ICD |
| 1.5 | 20/11/2025 | Temperature Sensor device type **rev 3** |
| 1.5.1 | 31/03/2026 | Humidity Sensor device type **rev 3**; Temperature Measurement rev 5, RH Measurement rev 4 |
| **1.6** | **17/06/2026** | Temperature Measurement rev 6, RH rev 5; ICD không đổi |
| 1.6.1 | 09/2026 (SDK tag `v1.6.1.0` ngày 24/09/2026) | Bản bảo trì; Root Node rev 5 |

**Kết luận:** thiết kế nhắm **Matter 1.6.x**. Mọi thứ bên dưới vẫn đúng với 1.5 vì cụm ICD
(cluster rev 3) không đổi từ 1.4 tới 1.6.1. Trên thực tế, phiên bản bạn dùng do bản **Silicon Labs
Matter extension** quyết định (xem mục 5). Hãy lấy bản extension mới nhất dựa trên SDK 1.5.x hoặc 1.6.x.

## 2.1 Cấu trúc endpoint

```
Node
├── EP0  Root Node (0x0016)  +  Power Source (0x0011)  [+ OTA Requestor (0x0012) nếu bật OTA]
│        Descriptor, Basic Information, Access Control, General Commissioning,
│        Network Commissioning (feature Thread), Administrator Commissioning,
│        Operational Credentials, Group Key Management, General Diagnostics,
│        ICD Management (0x0046), Power Source (0x002F)
│        [+ OTA Software Update Requestor (server) + OTA Provider (client)]
│        [tuỳ chọn: Thread Network Diagnostics (rút gọn), Software Diagnostics]
├── EP1  Temperature Sensor (0x0302, rev 3)
│        Descriptor, Identify, Temperature Measurement (0x0402)
└── EP2  Humidity Sensor (0x0307, rev 3)
         Descriptor, Identify, Relative Humidity Measurement (0x0405)
```

| Hạng mục | Mức | Ghi chú |
|---|---|---|
| Identify + Temperature Measurement trên EP1 | **[SPEC]** bắt buộc của device type 0x0302 | `IdentifyType` = VisibleIndicator (nháy LED) |
| Identify + Relative Humidity Measurement trên EP2 | **[SPEC]** bắt buộc của 0x0307 | |
| ICD Management trên EP0 | **[SPEC]** bắt buộc với mọi ICD (cả SIT lẫn LIT) từ 1.4 | |
| Tách nhiệt độ và độ ẩm thành 2 endpoint | [KN][TT] | Đây là cách phổ biến nhất. Apple, Google và HA đều hiển thị thành 2 cảm biến của cùng một thiết bị |
| Power Source trên EP0 | [KN] | Giống `lit-icd-app` (EP0, BAT) và cảm biến LIT mẫu của NXP. `smoke-co-alarm-app` thì đặt ở EP1. Cả hai cách đều hợp lệ |
| Thread Network Diagnostics | [KN] tuỳ chọn | Có ích cho chẩn đoán (HA). Mỗi lần controller đọc lại đánh thức thiết bị, nên chỉ bật một tập thuộc tính tối thiểu |
| Unit Localization / Thermostat UI Config | không cần | Chỉ có ý nghĩa khi thiết bị có màn hình |

Revision của device type và cluster do ZAP/SDK tự sinh theo bản extension. Không sửa tay.

### Giá trị thuộc tính đo

| Cluster | Thuộc tính | Giá trị đề xuất | Mức |
|---|---|---|---|
| Temperature Measurement | `MeasuredValue` | int16, đơn vị 0,01 °C. Đặt `null` sau 3 lần đọc lỗi liên tiếp | [SPEC] đơn vị/nullable · [TT] chính sách null |
| | `MinMeasuredValue` / `MaxMeasuredValue` | −2000 / 6000 (−20…+60 °C, dải hoạt động của sản phẩm chạy CR2450). Có thể đặt −4000/12500 nếu muốn khai báo theo cảm biến | [KN] |
| | `Tolerance` | Đặt theo sai số **tối đa** đã kiểm chứng ở T5 (SHT40: khoảng 20–40 = 0,2–0,4 °C) | [KN] |
| Relative Humidity Measurement | `MeasuredValue` | uint16, đơn vị 0,01 %RH (0…10000) | [SPEC] |
| | `Min` / `Max` / `Tolerance` | 0 / 10000 / theo T5 (khoảng 180–350) | [KN] |

## 2.2 Power Source cluster cho CR2450

FeatureMap = **BAT (0x02) | REPLC (0x08) = 0x0A**. WIRED và BAT loại trừ nhau trong một instance. REPLC phải đi kèm BAT.

| Thuộc tính | Bắt buộc? | Giá trị | Ghi chú |
|---|---|---|---|
| `Status` | [SPEC] M | Active (1) | |
| `Order` | [SPEC] M | 0 | |
| `Description` | [SPEC] M | "Battery" | |
| `EndpointList` | [SPEC] M | `[]` (rỗng = nguồn cho toàn node) hoặc `[0,1,2]` | Theo spec, danh sách rỗng nghĩa là nguồn cấp cho toàn bộ node |
| `BatChargeLevel` | [SPEC] M (BAT) | OK / Warning / Critical | Thuật toán ở mục 5.5 |
| `BatReplacementNeeded` | [SPEC] M (BAT) | true khi Critical | [KN] |
| `BatReplaceability` | [SPEC] M (BAT) | UserReplaceable (2) | |
| `BatPercentRemaining` | O (nên có) | 0…200, **đơn vị 0,5 %** | [SPEC] Từ 1.4 có quality **Q**: chỉ báo cáo tối đa 1 lần/10 s |
| `BatVoltage` | O (nên có) | mV | Quality C (changes omitted). Controller đọc khi cần, thay đổi giá trị không tự sinh báo cáo |
| `BatReplacementDescription` | [SPEC] M (REPLC) | `"CR2450"` | |
| `BatQuantity` | [SPEC] M (REPLC) | 1 | |
| `BatCommonDesignation` | O | **bỏ trống** | `BatCommonDesignationEnum` (giá trị 0…80) **không có pin cúc áo nào** |
| `BatIECDesignation` | O | `"CR2450"` | Dùng trường này thay cho enum |
| `BatANSIDesignation` | O | `"5029LC"` | ANSI của CR2450 |
| `BatApprovedChemistry` | O | LithiumManganeseDioxide | |
| `BatCapacity` | O | 600 (mAh, danh định) | |
| `BatPresent`, `ActiveBatFaults`, `BatTimeRemaining` | O | không dùng | `BatTimeRemaining` dễ sai, gây hiểu nhầm |

**Chính sách cập nhật** [TT]:
- Đo áp pin mỗi 6 h, hoặc ngay sau một lần radio phát lớn.
- Chỉ ghi thuộc tính khi % giảm ≥ 2 %, khi đổi mức Warning/Critical, hoặc khi áp lệch ≥ 20 mV.
- Gộp việc ghi thuộc tính pin vào cùng chu kỳ báo cáo nhiệt/ẩm, để không tạo thêm một lần thức radio.

## 2.3 ICD: SIT và LIT, Check-In, User Active Mode Trigger

### Khái niệm

| | **SIT** (Short Idle Time) | **LIT** (Long Idle Time) |
|---|---|---|
| Slow poll khi idle | **≤ 15 s** [SPEC] | > 15 s, có thể nhiều giờ |
| Controller liên lạc với thiết bị | Bất cứ lúc nào. Tin nhắn chờ ở parent tối đa 1 slow poll | Chỉ trong cửa sổ active: sau Check-In, sau khi thiết bị gửi báo cáo, hoặc khi người dùng nhấn nút (UAT) |
| Duy trì subscription | Controller tự subscribe lại khi mất | Controller phải đăng ký Check-In (`RegisterClient`). Thiết bị gửi Check-In khi client đó không còn subscription |
| Feature ICD Management | (không cần LITS) | **LITS bắt buộc kèm CIP + UAT** [SPEC] |
| `ActiveModeThreshold` | tự do | **≥ 5000 ms** [SPEC]. SDK `VerifyOrDie` khi khởi động nếu build có LIT |

**Hành vi quan trọng của SDK** [SDK]:
- Thiết bị build có LIT chỉ thực sự chạy LIT khi **có ít nhất 1 client đã đăng ký** trên bất kỳ fabric nào. Nếu không, nó chạy **SIT** và slow poll tự kẹp về ≤ 15 s. Đây là cơ chế **fallback tự động**.
- `ShortIdleModeDuration` là tham số riêng của SDK, không có trong spec. Nó chỉ có hiệu lực khi build có LITS **và** đang chạy SIT. Mẫu `lit-icd-app` của Silicon Labs đặt 60 s và bật report-on-active-mode. Khi rơi về SIT, mỗi subscription sẽ bị báo cáo **mỗi 60 s**, làm dòng trung bình tăng khoảng **+5,7 µA**, tức gấp đôi tổng tiêu thụ (kịch bản E, mục 6). **Hãy đặt ShortIdle = IdleModeDuration.**
- Silicon Labs tự đặt child timeout và child-supervision check timeout theo slow poll/IdleModeDuration khi bật ICD, nên poll dài không bị đánh thức giữa chừng.
- MRP của thiết bị tự cộng thêm fast-poll interval vào thời gian chờ ACK.

### Feature và tham số đề xuất

**FeatureMap: CIP | UAT | LITS = 0x07.** DSLS (0x08) là tuỳ chọn; xem chính sách đa fabric bên dưới.

| Tham số | Giá trị đề xuất | Silicon Labs `lit-icd-app` | Lý do |
|---|---|---|---|
| `IdleModeDuration` | **1800 s** | 3600 s (ví dụ multi-sensor: 1800 s) | Bằng MaxInterval của subscription (keep-alive ≤ 1 lần/30 phút/subscriber) và chu kỳ Check-In. Hàng thương mại dùng 300 s (W100); chọn 1800 s thì keep-alive giảm khoảng 1,2 µA so với 300 s |
| ShortIdleModeDuration (SDK) | **1800 s** (= Idle, tức tắt) | 60 s | Tránh bẫy +5,7 µA khi chạy SIT |
| `ActiveModeDuration` | **0 ms** | 0 ms | Không tự thức định kỳ. Thiết bị chỉ thức khi có việc |
| `ActiveModeThreshold` | **5000 ms** | 5000 ms | Mức tối thiểu cho LIT [SPEC] |
| Slow poll khi SIT | **15 s** (SDK kẹp) | 15 s | Giới hạn SIT |
| Slow poll khi LIT (`SL_TRANSPORT_IDLE_INTERVAL`) | **1 800 000 ms** (= Idle, như ví dụ multi-sensor) | 3 600 000 | Chênh năng lượng giữa 10 phút và 1 giờ < 0,03 µA. Giảm xuống 600 000 nếu muốn phát hiện mất parent nhanh hơn |
| Fast poll (`sl_transport_active_interval_ms`) | **500 ms** | 1000 ms | Đủ nhanh cho CASE và lệnh tương tác. Đuôi active chỉ khoảng 11 poll |
| `ClientsSupportedPerFabric` | 2 | 2 | |
| `MaximumCheckInBackoff` | **7200 s** (4 × Idle) | = Idle | Client "chết" (đã gỡ HA mà chưa huỷ đăng ký) sẽ không làm thiết bị gửi Check-In mỗi giờ mãi mãi |
| `UserActiveModeTriggerHint` | **SetupButton (0x1000)** | 0x111D | Thiết bị có đúng 1 nút |
| `UserActiveModeTriggerInstruction` | không cần | | Chỉ bắt buộc với các bit dạng Custom/Seconds/Times |
| Report on enter active mode | **bật** | bật | Mỗi lần thức radio, mọi subscriber đã qua min interval được báo cáo luôn, nên keep-alive về sau tự thẳng hàng |
| Subscription syncing | **bật** | bật | `SynchronizedReportScheduler` |

**Bản "chỉ SIT"** (không bật LITS) đơn giản hơn: `ActiveModeThreshold` có thể 1000 ms, fast poll 200 ms. Nó chỉ tiết kiệm được khoảng 0,05 µA so với bản LIT-capable đang chạy SIT (kịch bản A và C, mục 6). Vì vậy **khuyến nghị build LIT-capable**: không mất gì trên hệ sinh thái chưa hỗ trợ, và được lợi khoảng 1 µA (khoảng 25 % tuổi thọ) ở hệ sinh thái đã hỗ trợ.

### Check-In và UAT làm việc thế nào

1. Controller hỗ trợ LIT gọi `RegisterClient(CheckInNodeID, MonitoredSubject, Key[16], ClientType)` (thường ngay sau commissioning). Thiết bị lưu vào ICDMonitoringTable, mỗi fabric tối đa `ClientsSupportedPerFabric` client.
2. Hết `IdleModeDuration`, nếu client không còn subscription, thiết bị vào active mode và gửi **Check-In message** mã hoá bằng key đã đăng ký (kèm `ICDCounter`), rồi chờ ít nhất `ActiveModeThreshold`. Client dựng lại CASE và subscription trong cửa sổ đó.
3. Thiết bị gửi Check-In khi khởi động lại (thay pin) để controller biết mà subscribe lại.

Thực tế thị trường (mục 3): W100 chỉ SIT (FeatureMap 0, IdleModeDuration 300 s, AMT 1 s). IKEA TIMMERFLOTTE (cũng MG24 + SHT4x) cũng nhiều khả năng chỉ SIT. Chưa thấy sản phẩm nào chạy LIT.
4. **UAT**: nhấn nút → `ICDNotifier::GetInstance().NotifyNetworkActivityNotification()` (đúng như `BaseApplication` của Silicon Labs) → thiết bị vào active mode. Controller LIT hướng dẫn người dùng "nhấn nút setup" dựa trên `UserActiveModeTriggerHint`.

### Hệ sinh thái nào đã hỗ trợ LIT (tình trạng 11/2026)

| Hệ sinh thái | Hỗ trợ LIT / Check-In | Độ tin cậy |
|---|---|---|
| **Home Assistant** | **Có.** Matter Server mới (nền matter.js) v1.2.0 (09/07/2026): tự `RegisterClient` có bảo vệ đa admin, xử lý Check-In, yêu cầu thiết bị Matter 1.4+. Phát hành tới người dùng qua add-on 9.1.0 khoảng 15/07/2026. `python-matter-server` cũ (đã ngừng phát triển) **không** hỗ trợ | Changelog chính thức |
| **SmartThings** | **Có nhưng tắt mặc định.** Hub firmware 0.57.x (beta 05/2025) thêm LIT. Từ 0.60.12 (03/2026) LIT tắt mặc định, bật được cho từng thiết bị | Release notes beta (chính thức) + bản sao của đại lý; chưa xác nhận nó đăng ký Check-In |
| **Apple Home** | **Chưa có công bố chính thức.** Người dùng báo (06–11/2026) Apple giữ thiết bị ICD của IKEA "qua check-in" | Cộng đồng, chưa chắc |
| **Google Home** | **Không tìm thấy thông tin**, coi như chưa hỗ trợ | Không rõ |
| **Amazon Alexa** | Echo hỗ trợ "Matter 1.5 SDK", không nhắc LIT | Không rõ |

**Fallback**:
- Ở hệ sinh thái không đăng ký Check-In, thiết bị chạy SIT: poll 15 s, MaxInterval vẫn 30 phút, mọi thứ hoạt động bình thường, chỉ tốn thêm khoảng 1 µA.
- **Rủi ro đa fabric** [ĐOÁN, cần thử T6]: nếu fabric A (HA) đăng ký Check-In còn fabric B (Apple) không, SDK sẽ chuyển sang LIT (poll 30 phút). Khi đó fabric B có thể mất liên lạc sau khi hub B khởi động lại (không có Check-In cho B). Khuyến nghị bật **DSLS** và áp chính sách ứng dụng:
  - Chỉ cho chạy LIT khi **mọi** fabric đều có client đã đăng ký.
  - Ngược lại, gọi `ICDNotifier::GetInstance().NotifySITModeRequestNotification()`; khi đủ điều kiện thì gọi `...Withdrawal()`.
  - Xem mục 5.6.

## 2.4 Subscription và đồng bộ báo cáo với chu kỳ idle

**Cơ chế chuẩn** [SPEC]:
- Controller gửi `SubscribeRequest(MinIntervalFloor, MaxIntervalCeiling)`.
- Thiết bị chọn `MaxInterval` và phải gửi báo cáo, kể cả báo cáo rỗng, ít nhất 1 lần mỗi `MaxInterval` để giữ subscription sống.
- Thay đổi giá trị được báo cáo sớm nhất sau `MinInterval`.

**SDK cho ICD** [SDK]:
- `MaxInterval = IdleModeDuration`. Trần là `max(IdleModeDuration hoặc 3600 s, MaxIntervalCeiling)`, làm tròn lên bội số của IdleModeDuration và ≥ MinIntervalFloor. App vẫn có thể ghi đè trong `OnSubscriptionRequested`.
- Với cấu hình trên, mỗi subscriber nhận keep-alive tối đa 1 lần/30 phút.

**Các lớp đồng bộ để không thức nhiều lần**:

1. **SDK — subscription syncing** (`sl_use_subscription_syncing`, tức `CHIP_CONFIG_SYNCHRONOUS_REPORTS_ENABLED`). Mọi subscription được xếp lịch báo cáo cùng lúc, theo max interval sớm nhất. N subscriber chỉ tốn 1 lần thức.
2. **SDK — report on enter active mode** (`chip_icd_report_on_active_mode`). Bất cứ khi nào radio đã thức (báo cáo do thay đổi, Check-In, nhấn nút), mọi subscriber đã qua min interval được báo cáo luôn. Bộ đếm max interval của tất cả được đặt lại cùng lúc.
3. **Ứng dụng — đo độc lập với radio**. Timer đo (30 s) chỉ đánh thức MCU và I²C (khoảng 4 µC/lần), không đụng radio.
4. **Ứng dụng — vùng chết hai tầng** (`ReportPolicy`):
   - Thay đổi ≥ ngưỡng **cứng** (0,2 °C / 2 %RH) thì ghi thuộc tính ngay.
   - Thay đổi ≥ ngưỡng **mềm** (0,1 °C / 1 %RH) thì **chờ cơ hội**: lần thức radio kế tiếp, nhận qua `ICDStateObserver::OnEnterActiveMode`, hoặc tối đa 15 phút.
   - Không ghi dày hơn 1 lần/60 s.
   - Khi đã ghi, ghi kèm cả đại lượng còn lại nếu nó lệch dù nhỏ.
5. **Ứng dụng — ghi T, RH và pin trong cùng một lần khoá CHIP stack**, để chúng nằm trong cùng một ReportData.

## 2.5 Commissioning

| Hạng mục | Thiết kế | Mức |
|---|---|---|
| Kênh | BLE để commissioning, sau đó Thread. Discovery Capabilities = BLE (0x02) | [SPEC] |
| QR | `MT:` + Base38 (version, VID, PID, flow = Standard, discovery, discriminator 12 bit, passcode 27 bit) | [SPEC] |
| Mã nhập tay | **11 chữ số** (4 bit cao của discriminator + passcode + check digit Verhoeff) | [SPEC] |
| Passcode | Ngẫu nhiên, riêng từng thiết bị. Cấm: 00000000, 11111111…88888888, 12345678, 87654321, ≥ 99999999 | [SPEC/SDK] |
| Lưu trên thiết bị | Chỉ **SPAKE2+ verifier** (W0‖L, 97 byte), salt 16–32 byte, PBKDF2 1000–100000 vòng. Passcode chỉ in trên nhãn | [SDK][KN] |
| Nhãn | QR + 11 số ở mặt sau/trong khoang pin và trên hộp. **Không** dùng logo Matter nếu chưa chứng nhận | [SPEC/CSA] |
| Cửa sổ | Tự mở khi khởi động mà chưa có fabric: **15 phút** (spec cho phép 3–15 phút) | [SPEC] |
| Quảng bá BLE | 20–60 ms trong 30 s đầu, sau đó 150–1200 ms. **Tắt** "extended announcement" (1285 ms, tới 48 h) | [SDK mặc định][KN] |
| Mở lại cửa sổ | Chưa có fabric: giữ nút 3 s. **Đã có fabric: nút không mở BLE** (giống `BaseApplication` Silicon Labs). Thêm hệ sinh thái bằng "chia sẻ/pairing mode" từ admin hiện tại (Enhanced Commissioning qua Thread) | [KN] |
| ICD khi commissioning | SDK giữ active (CommissioningWindowOpen, FailSafeArmed) với fast poll | [SDK] |
| **Pin yếu** | Trước khi mở cửa sổ, đo áp. Nếu `BatChargeLevel = Critical` hoặc áp tải < 2,4 V thì **từ chối**, nháy mã LED "pin yếu" và giảm công suất BLE. Nếu sụt áp làm hỏng giữa chừng, cơ chế **fail-safe** của spec tự rollback | [KN] |

## 2.6 Bảo mật và chứng nhận

### Chuỗi chứng thực thiết bị [SPEC]
- **PAA**: root, được liệt kê trên DCL.
- **PAI**: gắn VID, có thể gắn PID.
- **DAC**: mỗi thiết bị một chứng chỉ, chứa VID/PID. Khoá P-256 nên được sinh và giữ trong Secure Vault/PSA của MG24.
- **CD (Certification Declaration)**: CMS do CSA ký sau khi chứng nhận. Chứa VID, danh sách PID, device type, `certification_type` (0 = development/test, 1 = provisional, 2 = official).
- Commissioner kiểm tra DAC → PAI → PAA và CD.

### Đường DIY
- **VID test 0xFFF1–0xFFF4**, PID tuỳ chọn (ví dụ 0x8005).
- Dùng **DAC/PAI test** sinh bằng `chip-cert` từ PAA test của SDK (`credentials/test/attestation`), và **CD test** (`certification_type = 0`).
- Nạp bằng công cụ provisioning của Silicon Labs (mục 5.8).
- Không bán, không dùng logo.
- Từng hệ sinh thái:
  - **Apple Home**: báo "phụ kiện chưa được chứng nhận", vẫn cho thêm. [TT]
  - **Google Home**: **phải** tạo dự án trên Google Home Developer Console, khai báo VID/PID test thì mới ghép được. [TT]
  - **SmartThings**: thiết bị test cần Developer Workspace/chế độ developer. [TT]
  - **HA**: thường ghép được với PAA test. Nếu bị từ chối, xem tuỳ chọn chứng chỉ test của Matter Server. [ĐOÁN]

### Đường thương mại
1. **Thành viên CSA**, tối thiểu hạng Adopter, để có **VID riêng**.
2. **PKI cho DAC**:
   - Thuê PAA/PAI từ nhà cung cấp được CSA chấp thuận, **hoặc**
   - Dùng dịch vụ nạp DAC tại nhà máy của Silicon Labs (CPMS / Matter provisioning, mục 5.8), nên chọn module/chip có DAC sẵn.
3. **Thread**: thành viên Thread Group, chứng nhận sản phẩm. Có thể "kế thừa" chứng nhận stack/component của Silicon Labs; hỏi lab.
4. **Matter**: tự chạy Test Harness (TH) của CSA, sau đó thử chính thức tại **ATL** (Authorized Test Lab). CSA cấp CD. Tạo bản ghi model/OTA trên **DCL**.
5. **Pháp quy vô tuyến** (tách biệt với CSA):
   - FCC/ISED, CE-RED (EN 300 328, EN 301 489, EN 62368-1, EN 62479), UKCA.
   - Việt Nam: chứng nhận/công bố hợp quy thiết bị vô tuyến cự ly ngắn 2,4 GHz. Quy chuẩn và cơ quan quản lý đã thay đổi sau sáp nhập bộ năm 2025, cần xác nhận với phòng thử nghiệm. [ĐOÁN]
   - Dùng **module đã chứng nhận** giảm mạnh phần đo RF (xem mục 1).
6. **Chi phí**: phí thành viên, phí chứng nhận và phí lab thay đổi theo năm. Hãy lấy báo giá CSA, Thread Group và lab trước khi lập ngân sách. Thứ tự độ lớn là vài nghìn tới vài chục nghìn USD cho lần đầu. [ĐOÁN]

## 2.7 OTA Requestor: có nên bật?

**Có, với sản phẩm thương mại** [KN]:
- Tài liệu Silicon Labs dẫn Core spec §11.20.4.2: thiết bị được chứng nhận phải có **cơ chế cập nhật firmware an toàn**.
- Spec không ép dùng đúng Matter OTA; Nordic ghi rõ có thể dùng cơ chế riêng.
- Với một thiết bị kín chạy pin, Matter OTA Requestor (EP0, cluster 0x002A + OTA Provider client) là đường thực tế nhất.

| Ảnh hưởng | Đánh giá |
|---|---|
| Flash | Ứng dụng Matter-Thread khoảng 0,7–0,9 MB [ĐOÁN, đo sau khi build]. Cần chỗ cho ảnh mới: slot trong flash nội (có nén LZMA) hoặc SPI-NOR ngoài (mục 4/5) |
| Pin, lúc nhàn rỗi | Requestor hỏi Provider định kỳ (mặc định 24 h). Không đáng kể nếu có sẵn CASE session; nếu phải dựng CASE thì khoảng 1–2 mC/lần [ĐOÁN] |
| Pin, khi cập nhật | Tải khoảng 0,8 MB qua BDX ở active mode, có thể mất 10–30 phút với fast poll, khoảng 2–4 mAh/lần (≤ 0,7 % pin) [ĐOÁN, đo ở T4] |
| ICD | SDK giữ active khi exchange đang mở. Ở LIT, việc kiểm tra bản mới do thiết bị chủ động, controller không gọi vào được |
| Rủi ro | Chỉ **áp dụng** ảnh mới khi `BatChargeLevel = OK` và áp tải ≥ 2,6 V. Bootloader phải xác thực chữ ký (GBL ký + mã hoá) trước khi chép |

**DIY**: có thể tắt OTA trong giai đoạn đầu (nạp qua SWD). Nên bật từ bản hardware có vỏ kín.
