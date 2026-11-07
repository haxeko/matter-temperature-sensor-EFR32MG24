// Test chạy trên máy host (g++/clang): cmake -S firmware/app-logic -B build && cmake --build build && ctest --test-dir build
#include <cstdio>
#include <cstdlib>

#include "battery_estimator.h"
#include "button_fsm.h"
#include "report_policy.h"
#include "sht4x.h"

static int gFailures = 0;
static int gChecks = 0;

#define CHECK(cond)                                                              \
    do {                                                                         \
        ++gChecks;                                                               \
        if (!(cond)) {                                                           \
            ++gFailures;                                                         \
            std::printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
        }                                                                        \
    } while (0)

#define CHECK_EQ(a, b)                                                           \
    do {                                                                         \
        ++gChecks;                                                               \
        const long long va = static_cast<long long>(a);                          \
        const long long vb = static_cast<long long>(b);                          \
        if (va != vb) {                                                          \
            ++gFailures;                                                         \
            std::printf("  FAIL %s:%d: %s == %s (%lld != %lld)\n", __FILE__,     \
                        __LINE__, #a, #b, va, vb);                               \
        }                                                                        \
    } while (0)

using namespace tsensor;

static void TestSht4x() {
    std::printf("sht4x\n");
    const uint8_t beef[2] = {0xBE, 0xEF};
    CHECK_EQ(sht4x::Crc8(beef, 2), 0x92);  // ví dụ chuẩn trong datasheet Sensirion

    CHECK_EQ(sht4x::RawToCentiCelsius(0), -4500);
    CHECK_EQ(sht4x::RawToCentiCelsius(65535), 13000);
    CHECK_EQ(sht4x::RawToCentiCelsius(26214), 2500);  // 25,00 °C

    CHECK_EQ(sht4x::RawToCentiPercentRh(0), 0);         // cắt dưới
    CHECK_EQ(sht4x::RawToCentiPercentRh(65535), 10000); // cắt trên
    CHECK_EQ(sht4x::RawToCentiPercentRh(29360), 5000);  // 50,00 %RH

    uint8_t rx[6] = {0x66, 0x66, 0, 0x72, 0xB0, 0};
    rx[2] = sht4x::Crc8(&rx[0], 2);
    rx[5] = sht4x::Crc8(&rx[3], 2);
    sht4x::Measurement m{};
    CHECK(sht4x::Parse(rx, m));
    CHECK_EQ(m.temperatureCenti, 2500);
    CHECK_EQ(m.humidityCenti, 5000);
    rx[5] ^= 0x01;
    CHECK(!sht4x::Parse(rx, m));
}

static Sample S(int16_t t, uint16_t rh) { return Sample{true, t, rh}; }

static void TestReportPolicy() {
    std::printf("report_policy\n");
    {
        ReportPolicy p;  // EMA 1/2, spacing 60 s, hard 0,2 °C
        Decision d = p.OnSample(0, S(2500, 5000));
        CHECK(d.publishTemperature && d.publishHumidity);
        CHECK_EQ(d.temperatureCenti, 2500);

        d = p.OnSample(30, S(2505, 5000));  // nhiễu nhỏ
        CHECK(!d.Any());

        d = p.OnSample(60, S(2600, 5000));  // EMA -> 2551, ΔT = 0,51 °C
        CHECK(d.publishTemperature);
        CHECK(!d.publishHumidity);
        CHECK_EQ(d.temperatureCenti, 2551);

        d = p.OnSample(90, S(2700, 5000));  // vượt ngưỡng cứng nhưng < 60 s
        CHECK(!d.Any());
        CHECK(p.HasPending());
        d = p.OnSample(120, S(2700, 5000));
        CHECK(d.publishTemperature);
        CHECK_EQ(d.temperatureCenti, 2662);
    }
    {
        ReportPolicyConfig c;
        c.emaShift = 0;
        ReportPolicy p(c);
        p.OnSample(0, S(2500, 5000));
        Decision d = p.OnSample(30, S(2512, 5000));  // thay đổi mềm 0,12 °C
        CHECK(!d.Any());
        CHECK(p.HasPending());
        for (uint32_t t = 60; t <= 900; t += 30) {
            d = p.OnSample(t, S(2512, 5000));
            CHECK(!d.Any());
        }
        d = p.OnSample(930, S(2512, 5000));  // hết holdoff (900 s kể từ t=30)
        CHECK(d.publishTemperature);
    }
    {
        ReportPolicyConfig c;
        c.emaShift = 0;
        ReportPolicy p(c);
        p.OnSample(0, S(2500, 5000));
        p.OnSample(30, S(2512, 5000));
        Decision d = p.OnOpportunity(40);  // chưa đủ 60 s
        CHECK(!d.Any());
        d = p.OnOpportunity(100);          // thiết bị vốn đang thức -> gửi kèm
        CHECK(d.publishTemperature);
        CHECK(!p.HasPending());
    }
    {
        ReportPolicyConfig c;
        c.emaShift = 0;
        ReportPolicy p(c);
        p.OnSample(0, S(2500, 5000));
        Decision d = p.OnSample(60, S(2530, 5040));  // T cứng, RH +0,40 % >= piggyback
        CHECK(d.publishTemperature && d.publishHumidity);
        CHECK_EQ(d.humidityCenti, 5040);
    }
    {
        ReportPolicy p;
        p.OnSample(0, S(2500, 5000));
        const Sample bad{false, 0, 0};
        CHECK(!p.OnSample(30, bad).Any());
        CHECK(!p.OnSample(60, bad).Any());
        Decision d = p.OnSample(90, bad);
        CHECK(d.publishNull);
        CHECK(!p.OnSample(120, bad).Any());  // chỉ báo null một lần
        d = p.OnSample(150, S(2400, 4000));  // hồi phục -> gửi ngay cả hai
        CHECK(d.publishTemperature && d.publishHumidity && !d.publishNull);
    }
    {
        ReportPolicy p;
        p.OnSample(0, S(2500, 5000));
        Decision d = p.ForcePublish(5);  // nhấn nút
        CHECK(d.publishTemperature && d.publishHumidity);
    }
}

static void TestBattery() {
    std::printf("battery_estimator\n");
    constexpr uint64_t kUsableUc = 600ULL * 3600000ULL * 850ULL / 1000ULL;
    bool changed = false;
    {
        BatteryEstimator b;
        BatteryReport r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 200);
        CHECK(r.level == ChargeLevel::kOk);
        CHECK(!r.replacementNeeded);

        b.AddChargeUc(kUsableUc / 100);  // 1 % -> chưa đủ bước 2 %
        r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 200);
        b.AddChargeUc(kUsableUc / 100);  // 2 %
        r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 196);
        CHECK(changed);

        b.AddChargeUc(kUsableUc / 2);  // tổng ~52 %
        r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 96);

        b.OnRestVoltage(2800, 2500);  // trần theo áp: 15 %
        r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 30);
        CHECK(r.level == ChargeLevel::kWarning);

        b.OnRestVoltage(2950, 2500);  // áp hồi lên: % không được tăng
        r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 30);
        CHECK(r.level == ChargeLevel::kWarning);  // mức đã chốt

        b.OnLoadedVoltage(2150);  // sụt áp khi TX dưới ngưỡng tới hạn
        r = b.Evaluate(changed);
        CHECK(r.level == ChargeLevel::kCritical);
        CHECK(r.replacementNeeded);

        // Lưu/khôi phục rồi lắp pin mới.
        const BatteryPersisted saved = b.Snapshot();
        BatteryEstimator b2;
        b2.Restore(saved);
        CHECK(!b2.OnBoot(2900));  // không đủ cao để kết luận pin mới
        CHECK(b2.OnBoot(3120));
        r = b2.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 200);
        CHECK(r.level == ChargeLevel::kOk);
    }
    {
        CHECK_EQ(BatteryEstimator::CurvePercent(3100), 100);
        CHECK_EQ(BatteryEstimator::CurvePercent(2900), 50);
        CHECK_EQ(BatteryEstimator::CurvePercent(2875), 38);
        CHECK_EQ(BatteryEstimator::CurvePercent(2200), 0);
        CHECK_EQ(BatteryEstimator::CurvePercent(1900), 0);
    }
    {
        // Bù nhiệt: 2850 mV ở 0 °C ~ 2887 mV ở 25 °C -> 44 % thay vì 25 %.
        BatteryEstimator b;
        b.OnRestVoltage(2850, 0);
        BatteryReport r = b.Evaluate(changed);
        CHECK_EQ(r.halfPercent, 88);
        CHECK_EQ(r.voltageMv, 2850);  // BatVoltage báo áp đo thật
    }
    {
        // Vượt ngưỡng Warning dù bước < 2 %.
        BatteryEstimator b;
        BatteryPersisted p;
        p.reportedHalfPercent = 42;  // 21 %
        p.consumedUc = kUsableUc * 80 / 100;
        b.Restore(p);
        BatteryReport r = b.Evaluate(changed);  // coulomb = 20 % -> 40
        CHECK_EQ(r.halfPercent, 40);
        CHECK(r.level == ChargeLevel::kWarning);
    }
    {
        BatteryEstimator b;
        b.OnBrownoutReset();
        BatteryReport r = b.Evaluate(changed);
        CHECK(r.level == ChargeLevel::kCritical);
    }
}

static void TestButton() {
    std::printf("button_fsm\n");
    ButtonFsm f;
    f.OnPress(0);
    CHECK(f.OnRelease(200) == ButtonEvent::kShortPress);

    f.OnPress(1000);
    CHECK(f.OnRelease(1010) == ButtonEvent::kNone);  // nhiễu

    f.OnPress(0);
    CHECK(f.OnTick(2900) == ButtonEvent::kNone);
    CHECK(f.OnTick(3000) == ButtonEvent::kHoldReached);
    CHECK(f.OnTick(3100) == ButtonEvent::kNone);
    CHECK(f.OnRelease(4000) == ButtonEvent::kLongPress);

    f.OnPress(0);
    f.OnTick(3000);
    CHECK(f.OnTick(7000) == ButtonEvent::kResetWarning);
    CHECK(f.OnRelease(8000) == ButtonEvent::kResetCancelled);

    f.OnPress(0);
    f.OnTick(3000);
    f.OnTick(7000);
    CHECK(f.OnTick(10000) == ButtonEvent::kFactoryReset);
    CHECK(f.OnRelease(10500) == ButtonEvent::kNone);

    f.OnPress(0);  // tick bị trễ hoàn toàn
    CHECK(f.OnRelease(10500) == ButtonEvent::kFactoryReset);
}

int main() {
    TestSht4x();
    TestReportPolicy();
    TestBattery();
    TestButton();
    std::printf("%d checks, %d failures\n", gChecks, gFailures);
    return gFailures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
