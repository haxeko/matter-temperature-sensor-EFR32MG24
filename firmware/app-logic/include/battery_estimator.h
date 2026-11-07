// Ước tính dung lượng CR2450 cho Power Source cluster.
//
// Pin Li/MnO2 có điện áp gần như phẳng (~2,9–3,0 V ở tải µA) trong ~85–90 % đời pin, nên
// chỉ dựa vào điện áp sẽ báo 100 % rất lâu rồi rơi tự do. Cách làm "lai":
//   % = min( % theo đếm điện tích (coulomb counting từ mô hình sự kiện),
//            trần % theo điện áp nghỉ đã bù nhiệt )
// và áp tải (đo lúc radio phát) + reset do BOD dùng để bật Warning/Critical sớm.
// Giá trị % chỉ đi xuống (trừ khi phát hiện thay pin) và đổi theo bước để tránh báo cáo thừa.
//
// Đơn vị đầu ra khớp Matter Power Source cluster:
//   BatPercentRemaining: 0..200 (đơn vị 0,5 %), BatVoltage: mV, BatChargeLevel: 0/1/2.
#pragma once

#include <cstddef>
#include <cstdint>

namespace tsensor {

enum class ChargeLevel : uint8_t { kOk = 0, kWarning = 1, kCritical = 2 };  // BatChargeLevelEnum

struct VoltagePoint {
    uint16_t mv;
    uint8_t percent;
};

// [ĐOÁN] Đường cong điện áp nghỉ CR2450 ở 25 °C, tải µA. PHẢI thay bằng dữ liệu đo (T4).
// Chỉ dùng làm "trần" — phần phẳng (>2,95 V) không mang thông tin.
constexpr VoltagePoint kCr2450RestCurve[] = {
    {3000, 100}, {2950, 80}, {2900, 50}, {2850, 25}, {2800, 15},
    {2700, 8},   {2600, 4},  {2500, 2},  {2400, 1},  {2200, 0},
};

struct BatteryConfig {
    uint32_t nominalCapacityMah = 600;
    uint16_t usablePermille = 850;         // phần dung lượng coi là dùng được (cut-off, xung)
    uint8_t warningPercent = 20;
    uint8_t criticalPercent = 5;
    uint16_t loadedWarningMv = 2400;       // áp nhỏ nhất đo được trong lúc TX
    uint16_t loadedCriticalMv = 2200;
    uint16_t freshCellMv = 3050;           // áp nghỉ lúc khởi động coi là pin mới
    uint8_t freshDetectBelowPercent = 80;  // ...nếu ước tính đang lưu thấp hơn mức này
    uint16_t tempCoeffUvPerCenti = 15;     // [ĐOÁN] 1,5 mV/°C, chỉ bù khi T < 25 °C
    uint8_t reportStepHalfPercent = 4;     // chỉ đổi giá trị báo cáo theo bước 2 %
    bool replacementNeededAtWarning = false;  // mặc định chỉ bật ở Critical
};

// Trạng thái cần lưu NVM3 (ghi thưa: vài giờ/lần hoặc khi đổi mức).
struct BatteryPersisted {
    uint64_t consumedUc = 0;        // điện tích đã dùng, µC
    uint8_t reportedHalfPercent = 200;
    uint8_t level = 0;
};

struct BatteryReport {
    uint8_t halfPercent;   // BatPercentRemaining
    uint32_t voltageMv;    // BatVoltage (0 nếu chưa đo)
    ChargeLevel level;     // BatChargeLevel
    bool replacementNeeded;  // BatReplacementNeeded
};

class BatteryEstimator {
public:
    explicit BatteryEstimator(const BatteryConfig& cfg = BatteryConfig()) : mCfg(cfg) {}

    void Restore(const BatteryPersisted& p);
    BatteryPersisted Snapshot() const;

    // Gọi ngay sau khi khởi động, với áp nghỉ đo trước khi bật radio.
    // Trả về true nếu kết luận là pin mới (đã reset bộ đếm).
    bool OnBoot(uint16_t restMv);

    void AddChargeUc(uint64_t uc) { mState.consumedUc += uc; }
    void OnRestVoltage(uint16_t mv, int16_t temperatureCenti);
    void OnLoadedVoltage(uint16_t mv);
    void OnBrownoutReset();
    void ResetForNewBattery();

    // Cập nhật và trả về giá trị để ghi vào thuộc tính. `changed` = có gì khác lần trước.
    BatteryReport Evaluate(bool& changed);

    uint8_t CoulombPercent() const;
    static uint8_t CurvePercent(uint16_t mv);

private:
    BatteryConfig mCfg;
    BatteryPersisted mState;
    bool mHaveRest = false;
    uint16_t mRestMv = 0;
    uint16_t mRestCompMv = 0;
    bool mHaveLoaded = false;
    uint16_t mMinLoadedMv = 0xFFFF;
    bool mBrownout = false;
    BatteryReport mLast{200, 0, ChargeLevel::kOk, false};
};

}  // namespace tsensor
