#include "battery_estimator.h"

namespace tsensor {

namespace {
constexpr uint64_t kUcPerMah = 3600ULL * 1000ULL;  // 1 mAh = 3,6 C = 3 600 000 µC

uint8_t MaxLevel(uint8_t a, uint8_t b) { return a > b ? a : b; }
}  // namespace

void BatteryEstimator::Restore(const BatteryPersisted& p) {
    mState = p;
    if (mState.reportedHalfPercent > 200) mState.reportedHalfPercent = 200;
    if (mState.level > 2) mState.level = 2;
    mLast.halfPercent = mState.reportedHalfPercent;
    mLast.level = static_cast<ChargeLevel>(mState.level);
}

BatteryPersisted BatteryEstimator::Snapshot() const { return mState; }

void BatteryEstimator::ResetForNewBattery() {
    mState = BatteryPersisted();
    mHaveLoaded = false;
    mMinLoadedMv = 0xFFFF;
    mBrownout = false;
    mLast = BatteryReport{200, mLast.voltageMv, ChargeLevel::kOk, false};
}

bool BatteryEstimator::OnBoot(uint16_t restMv) {
    mHaveRest = true;
    mRestMv = restMv;
    mRestCompMv = restMv;
    if (restMv >= mCfg.freshCellMv && (mState.reportedHalfPercent / 2) < mCfg.freshDetectBelowPercent) {
        ResetForNewBattery();
        return true;
    }
    return false;
}

void BatteryEstimator::OnRestVoltage(uint16_t mv, int16_t temperatureCenti) {
    mHaveRest = true;
    mRestMv = mv;
    uint32_t comp = mv;
    if (temperatureCenti < 2500) {
        // Pin lạnh có áp thấp hơn mà không phải do cạn -> cộng bù để không báo pin yếu giả.
        const uint32_t deltaCenti = static_cast<uint32_t>(2500 - temperatureCenti);
        comp += (deltaCenti * mCfg.tempCoeffUvPerCenti) / 1000U;
    }
    mRestCompMv = static_cast<uint16_t>(comp > 0xFFFF ? 0xFFFF : comp);
}

void BatteryEstimator::OnLoadedVoltage(uint16_t mv) {
    mHaveLoaded = true;
    if (mv < mMinLoadedMv) mMinLoadedMv = mv;
}

void BatteryEstimator::OnBrownoutReset() { mBrownout = true; }

uint8_t BatteryEstimator::CoulombPercent() const {
    const uint64_t usableUc = static_cast<uint64_t>(mCfg.nominalCapacityMah) * kUcPerMah * mCfg.usablePermille / 1000ULL;
    if (usableUc == 0 || mState.consumedUc >= usableUc) return 0;
    const uint64_t remaining = usableUc - mState.consumedUc;
    return static_cast<uint8_t>((remaining * 100ULL) / usableUc);
}

uint8_t BatteryEstimator::CurvePercent(uint16_t mv) {
    constexpr size_t n = sizeof(kCr2450RestCurve) / sizeof(kCr2450RestCurve[0]);
    if (mv >= kCr2450RestCurve[0].mv) return kCr2450RestCurve[0].percent;
    for (size_t i = 1; i < n; ++i) {
        const VoltagePoint hi = kCr2450RestCurve[i - 1];
        const VoltagePoint lo = kCr2450RestCurve[i];
        if (mv >= lo.mv) {
            const uint32_t span = hi.mv - lo.mv;
            const uint32_t pos = mv - lo.mv;
            return static_cast<uint8_t>(lo.percent + ((hi.percent - lo.percent) * pos + span / 2) / span);
        }
    }
    return 0;
}

BatteryReport BatteryEstimator::Evaluate(bool& changed) {
    uint8_t pct = CoulombPercent();
    if (mHaveRest) {
        const uint8_t cap = CurvePercent(mRestCompMv);
        if (cap < pct) pct = cap;
    }

    // Đơn điệu giảm + theo bước.
    uint8_t half = static_cast<uint8_t>(pct * 2);
    const uint8_t prevHalf = mState.reportedHalfPercent;
    if (half > prevHalf) {
        half = prevHalf;
    } else if (prevHalf - half < mCfg.reportStepHalfPercent && half != 0) {
        // Chưa đủ bước — nhưng vẫn cho đi xuống nếu vượt ngưỡng Warning/Critical.
        const uint8_t warnHalf = static_cast<uint8_t>(mCfg.warningPercent * 2);
        const uint8_t critHalf = static_cast<uint8_t>(mCfg.criticalPercent * 2);
        const bool crossesWarn = prevHalf > warnHalf && half <= warnHalf;
        const bool crossesCrit = prevHalf > critHalf && half <= critHalf;
        if (!crossesWarn && !crossesCrit) half = prevHalf;
    }

    // Mức sạc: chốt (latch) — chỉ tăng mức nghiêm trọng cho tới khi thay pin.
    uint8_t level = mState.level;
    const uint8_t reportedPct = half / 2;
    if (reportedPct <= mCfg.criticalPercent || mBrownout ||
        (mHaveLoaded && mMinLoadedMv < mCfg.loadedCriticalMv)) {
        level = MaxLevel(level, static_cast<uint8_t>(ChargeLevel::kCritical));
    } else if (reportedPct <= mCfg.warningPercent || (mHaveLoaded && mMinLoadedMv < mCfg.loadedWarningMv)) {
        level = MaxLevel(level, static_cast<uint8_t>(ChargeLevel::kWarning));
    }

    mState.reportedHalfPercent = half;
    mState.level = level;

    BatteryReport r;
    r.halfPercent = half;
    r.voltageMv = mHaveRest ? mRestMv : 0;
    r.level = static_cast<ChargeLevel>(level);
    r.replacementNeeded = (r.level == ChargeLevel::kCritical) ||
                          (mCfg.replacementNeededAtWarning && r.level == ChargeLevel::kWarning);

    // BatVoltage chỉ coi là "thay đổi" khi lệch ≥ 20 mV để không tạo báo cáo vì nhiễu.
    const uint32_t dv = r.voltageMv > mLast.voltageMv ? r.voltageMv - mLast.voltageMv : mLast.voltageMv - r.voltageMv;
    changed = r.halfPercent != mLast.halfPercent || r.level != mLast.level ||
              r.replacementNeeded != mLast.replacementNeeded || dv >= 20;
    if (changed) mLast = r;
    return changed ? r : mLast;
}

}  // namespace tsensor
