// Máy trạng thái nút đơn (không phụ thuộc phần cứng).
//   nhả < 3 s            -> kShortPress   : đánh thức, UAT, đo + báo cáo ngay, LED trạng thái
//   giữ tới 3 s          -> kHoldReached  : LED báo "đã tới 3 s, nhả ra để thực hiện"
//   nhả trong [3 s, 7 s) -> kLongPress    : chưa ghép -> mở cửa sổ commissioning;
//                                           đã ghép   -> UAT kéo dài + mã LED pin/mạng
//   giữ tới 7 s          -> kResetWarning : LED nháy nhanh cảnh báo
//   nhả trong [7 s,10 s) -> kResetCancelled
//   giữ tới 10 s         -> kFactoryReset (phát ngay khi đủ 10 s, không cần nhả)
// Lớp platform: ngắt GPIO (cổng A/B để đánh thức từ EM2) gọi OnPress/OnRelease sau chống dội;
// một sleeptimer ~100 ms chỉ chạy khi nút đang giữ gọi OnTick.
#pragma once

#include <cstdint>

namespace tsensor {

enum class ButtonEvent : uint8_t {
    kNone,
    kShortPress,
    kHoldReached,
    kLongPress,
    kResetWarning,
    kResetCancelled,
    kFactoryReset,
};

struct ButtonConfig {
    uint32_t minPressMs = 30;      // ngắn hơn = nhiễu
    uint32_t holdMs = 3000;
    uint32_t resetWarnMs = 7000;
    uint32_t resetMs = 10000;
};

class ButtonFsm {
public:
    explicit ButtonFsm(const ButtonConfig& cfg = ButtonConfig()) : mCfg(cfg) {}

    ButtonEvent OnPress(uint32_t nowMs) {
        mPressed = true;
        mStartMs = nowMs;
        mStage = 0;
        return ButtonEvent::kNone;
    }

    ButtonEvent OnTick(uint32_t nowMs) {
        if (!mPressed) return ButtonEvent::kNone;
        const uint32_t held = nowMs - mStartMs;
        if (mStage < 3 && held >= mCfg.resetMs) {
            mStage = 3;
            return ButtonEvent::kFactoryReset;
        }
        if (mStage < 2 && held >= mCfg.resetWarnMs) {
            mStage = 2;
            return ButtonEvent::kResetWarning;
        }
        if (mStage < 1 && held >= mCfg.holdMs) {
            mStage = 1;
            return ButtonEvent::kHoldReached;
        }
        return ButtonEvent::kNone;
    }

    ButtonEvent OnRelease(uint32_t nowMs) {
        if (!mPressed) return ButtonEvent::kNone;
        // Bắt kịp ngưỡng nếu tick bị trễ (ví dụ CPU bận).
        ButtonEvent late = OnTick(nowMs);
        mPressed = false;
        if (late == ButtonEvent::kFactoryReset) return late;
        const uint32_t held = nowMs - mStartMs;
        if (held < mCfg.minPressMs) return ButtonEvent::kNone;
        switch (mStage) {
            case 0: return ButtonEvent::kShortPress;
            case 1: return ButtonEvent::kLongPress;
            case 2: return ButtonEvent::kResetCancelled;
            default: return ButtonEvent::kNone;  // đã factory reset
        }
    }

    bool IsPressed() const { return mPressed; }

private:
    ButtonConfig mCfg;
    bool mPressed = false;
    uint32_t mStartMs = 0;
    uint8_t mStage = 0;
};

}  // namespace tsensor
