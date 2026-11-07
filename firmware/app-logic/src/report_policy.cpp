#include "report_policy.h"

#include <cstdlib>

namespace tsensor {

namespace {
int32_t Abs32(int32_t v) { return v < 0 ? -v : v; }
}  // namespace

void ReportPolicy::Reset() {
    const ReportPolicyConfig cfg = mCfg;
    *this = ReportPolicy(cfg);
}

Decision ReportPolicy::OnSample(uint32_t nowS, const Sample& s) {
    Decision d;
    if (!s.valid) {
        if (mFailures < 255) ++mFailures;
        if (mFailures >= mCfg.failuresToNull && !mNullPublished) {
            mNullPublished = true;
            mPendingSinceValid = false;
            d.publishNull = true;
        }
        return d;
    }
    mFailures = 0;

    // Lọc EMA số nguyên: f += (x - f) >> shift
    if (!mHasFiltered || mCfg.emaShift == 0) {
        mFiltT = s.temperatureCenti;
        mFiltRh = s.humidityCenti;
        mHasFiltered = true;
    } else {
        mFiltT += (static_cast<int32_t>(s.temperatureCenti) - mFiltT) / (1 << mCfg.emaShift);
        mFiltRh += (static_cast<int32_t>(s.humidityCenti) - mFiltRh) / (1 << mCfg.emaShift);
    }

    // Mẫu hợp lệ đầu tiên sau khởi động, hoặc hồi phục sau null: cập nhật ngay.
    if (!mHasPublished || mNullPublished) {
        return Publish(nowS, true);
    }

    const int32_t dT = Abs32(mFiltT - mLastT);
    const int32_t dRh = Abs32(mFiltRh - static_cast<int32_t>(mLastRh));
    const bool hard = dT >= mCfg.tempHardDeltaCenti || dRh >= mCfg.rhHardDeltaCenti;
    const bool soft = dT >= mCfg.tempSoftDeltaCenti || dRh >= mCfg.rhSoftDeltaCenti;

    if (!hard && !soft) {
        mPendingSinceValid = false;  // đã quay lại gần giá trị đã báo
        return d;
    }
    if (!mPendingSinceValid) {
        mPendingSinceValid = true;
        mPendingSinceS = nowS;
    }
    if (!SpacingOk(nowS)) {
        return d;  // giữ pending, sẽ gửi ở mẫu sau khi đủ khoảng cách
    }
    if (hard || (nowS - mPendingSinceS) >= mCfg.maxSoftHoldoffS) {
        return Publish(nowS, false);
    }
    return d;
}

Decision ReportPolicy::OnOpportunity(uint32_t nowS) {
    if (mPendingSinceValid && mHasFiltered && SpacingOk(nowS)) {
        return Publish(nowS, false);
    }
    return Decision();
}

Decision ReportPolicy::ForcePublish(uint32_t nowS) {
    if (!mHasFiltered || mNullPublished) {
        return Decision();
    }
    return Publish(nowS, true);
}

Decision ReportPolicy::Publish(uint32_t nowS, bool force) {
    Decision d;
    const int16_t t = static_cast<int16_t>(mFiltT);
    const uint16_t rh = static_cast<uint16_t>(mFiltRh);
    const bool first = !mHasPublished || mNullPublished;
    d.publishTemperature = force || first || Abs32(t - mLastT) >= mCfg.tempPiggybackDeltaCenti;
    d.publishHumidity = force || first ||
                        Abs32(static_cast<int32_t>(rh) - static_cast<int32_t>(mLastRh)) >= mCfg.rhPiggybackDeltaCenti;
    d.temperatureCenti = t;
    d.humidityCenti = rh;
    if (d.publishTemperature) mLastT = t;
    if (d.publishHumidity) mLastRh = rh;
    mHasPublished = true;
    mNullPublished = false;
    mLastPublishS = nowS;
    mPendingSinceValid = false;
    return d;
}

}  // namespace tsensor
