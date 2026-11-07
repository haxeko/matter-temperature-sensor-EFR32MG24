// Sensirion SHT4x — hàm thuần (không phụ thuộc phần cứng): lệnh, CRC-8, chuyển đổi.
// Phần giao tiếp I2C thực tế nằm ở lớp platform (sl_i2cspm), xem docs/05-firmware.md.
#pragma once

#include <cstddef>
#include <cstdint>

namespace tsensor::sht4x {

// Địa chỉ I2C 7-bit theo biến thể: SHT40-AD1B = 0x44, SHT40-BD1B = 0x45, SHT40-CD1B = 0x46.
constexpr uint8_t kAddrAD1B = 0x44;

// Lệnh 1 byte (datasheet SHT4x).
constexpr uint8_t kCmdMeasureHigh   = 0xFD;  // ~6,9 ms typ / 8,3 ms max
constexpr uint8_t kCmdMeasureMedium = 0xF6;  // ~3,7 ms typ / 4,5 ms max
constexpr uint8_t kCmdMeasureLow    = 0xE0;  // ~1,3 ms typ / 1,6 ms max
constexpr uint8_t kCmdReadSerial    = 0x89;
constexpr uint8_t kCmdSoftReset     = 0x94;
// Heater: 200 mW ≈ 67 mA — CẤM dùng khi chạy CR2450. 20 mW/0,1 s chỉ để test với nguồn ngoài.
constexpr uint8_t kCmdHeater20mW100ms = 0x15;

// Thời gian chờ an toàn (max datasheet + biên) trước khi đọc kết quả.
constexpr uint32_t kWaitHighUs   = 9000;
constexpr uint32_t kWaitMediumUs = 5000;
constexpr uint32_t kWaitLowUs    = 2000;

// CRC-8: đa thức 0x31 (x^8 + x^5 + x^4 + 1), init 0xFF, không đảo bit, không XOR cuối.
constexpr uint8_t Crc8(const uint8_t* data, size_t len) {
    uint8_t crc = 0xFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) {
            crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x31) : static_cast<uint8_t>(crc << 1);
        }
    }
    return crc;
}

// Nhiệt độ theo đơn vị 0,01 °C (đúng đơn vị MeasuredValue của Temperature Measurement cluster).
// T = -45 + 175 * raw / 65535
constexpr int16_t RawToCentiCelsius(uint16_t raw) {
    const int32_t scaled = (17500 * static_cast<int32_t>(raw) + 32767) / 65535;  // làm tròn
    return static_cast<int16_t>(scaled - 4500);
}

// Độ ẩm theo đơn vị 0,01 %RH (đúng đơn vị MeasuredValue của Relative Humidity Measurement).
// RH = -6 + 125 * raw / 65535, cắt về [0, 100] như datasheet khuyến nghị.
constexpr uint16_t RawToCentiPercentRh(uint16_t raw) {
    const int32_t scaled = (12500 * static_cast<int32_t>(raw) + 32767) / 65535 - 600;
    if (scaled < 0) return 0;
    if (scaled > 10000) return 10000;
    return static_cast<uint16_t>(scaled);
}

struct Measurement {
    int16_t temperatureCenti;  // 0,01 °C
    uint16_t humidityCenti;    // 0,01 %RH
};

// Giải mã 6 byte phản hồi: T_MSB T_LSB CRC RH_MSB RH_LSB CRC. Trả về false nếu sai CRC.
inline bool Parse(const uint8_t rx[6], Measurement& out) {
    if (Crc8(&rx[0], 2) != rx[2] || Crc8(&rx[3], 2) != rx[5]) {
        return false;
    }
    const uint16_t rawT  = static_cast<uint16_t>((rx[0] << 8) | rx[1]);
    const uint16_t rawRh = static_cast<uint16_t>((rx[3] << 8) | rx[4]);
    out.temperatureCenti = RawToCentiCelsius(rawT);
    out.humidityCenti    = RawToCentiPercentRh(rawRh);
    return true;
}

}  // namespace tsensor::sht4x
