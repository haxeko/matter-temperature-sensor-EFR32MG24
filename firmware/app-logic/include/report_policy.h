// Chính sách đẩy giá trị đo vào thuộc tính Matter (mỗi lần ghi thuộc tính = một báo cáo
// subscription). Matter không có "reportable change" như Zigbee, nên vùng chết (deadband)
// phải làm ở tầng ứng dụng.
//
//  - Ngưỡng CỨNG: thay đổi lớn -> cập nhật ngay (vẫn tôn trọng khoảng cách tối thiểu).
//  - Ngưỡng MỀM: thay đổi nhỏ -> chờ "cơ hội" (thiết bị vốn đã thức để keep-alive/poll
//    active) hoặc tối đa maxSoftHoldoffS rồi mới cập nhật => không tạo thêm lần thức radio.
//  - Khi đã cập nhật, gửi kèm (piggyback) đại lượng còn lại nếu nó thay đổi dù rất nhỏ.
//  - Lỗi cảm biến liên tiếp -> đặt MeasuredValue = null (spec cho phép, nghĩa là "không biết").
#pragma once

#include <cstdint>

namespace tsensor {

struct ReportPolicyConfig {
    int16_t tempHardDeltaCenti = 20;       // 0,20 °C
    int16_t tempSoftDeltaCenti = 10;       // 0,10 °C
    uint16_t rhHardDeltaCenti = 200;       // 2,00 %RH
    uint16_t rhSoftDeltaCenti = 100;       // 1,00 %RH
    int16_t tempPiggybackDeltaCenti = 3;   // 0,03 °C
    uint16_t rhPiggybackDeltaCenti = 30;   // 0,30 %RH
    uint32_t minSpacingS = 60;             // không cập nhật dày hơn 1 lần/phút
    uint32_t maxSoftHoldoffS = 900;        // thay đổi mềm chờ tối đa 15 phút
    uint8_t emaShift = 1;                  // lọc EMA alpha = 1/2^emaShift (0 = tắt lọc)
    uint8_t failuresToNull = 3;            // số lần đọc lỗi liên tiếp trước khi báo null
};

struct Sample {
    bool valid;
    int16_t temperatureCenti;
    uint16_t humidityCenti;
};

struct Decision {
    bool publishTemperature = false;
    bool publishHumidity = false;
    bool publishNull = false;  // đặt cả hai MeasuredValue = null
    int16_t temperatureCenti = 0;
    uint16_t humidityCenti = 0;

    bool Any() const { return publishTemperature || publishHumidity || publishNull; }
};

class ReportPolicy {
public:
    explicit ReportPolicy(const ReportPolicyConfig& cfg = ReportPolicyConfig()) : mCfg(cfg) {}

    // Gọi sau mỗi lần đo (ví dụ mỗi 30 s).
    Decision OnSample(uint32_t nowS, const Sample& s);

    // Gọi khi thiết bị vốn đã thức radio (ICD vào active mode, keep-alive, nhấn nút...).
    Decision OnOpportunity(uint32_t nowS);

    // Nhấn nút: cập nhật cả hai giá trị hiện tại bất kể ngưỡng.
    Decision ForcePublish(uint32_t nowS);

    void Reset();

    bool HasPending() const { return mPendingSinceValid; }

private:
    Decision Publish(uint32_t nowS, bool force);
    bool SpacingOk(uint32_t nowS) const { return !mHasPublished || (nowS - mLastPublishS) >= mCfg.minSpacingS; }

    ReportPolicyConfig mCfg;
    bool mHasFiltered = false;
    int32_t mFiltT = 0;   // 0,01 °C
    int32_t mFiltRh = 0;  // 0,01 %RH
    bool mHasPublished = false;
    bool mNullPublished = false;
    int16_t mLastT = 0;
    uint16_t mLastRh = 0;
    uint32_t mLastPublishS = 0;
    bool mPendingSinceValid = false;
    uint32_t mPendingSinceS = 0;
    uint8_t mFailures = 0;
};

}  // namespace tsensor
