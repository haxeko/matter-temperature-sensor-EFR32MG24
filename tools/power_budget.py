#!/usr/bin/env python3
"""
Ngân sách năng lượng cho cảm biến nhiệt độ/độ ẩm Matter-over-Thread (EFR32MG24 + CR2450).

Mô hình: dòng trung bình = dòng nền khi ngủ + Σ(điện tích mỗi sự kiện × tần suất sự kiện).
Mọi điện tích tính bằng µC (micro-coulomb) đo ở phía pin 3,0 V (datasheet MG24 cho dòng
ở 3,0 V với DC-DC bật, nên dùng trực tiếp được).

QUAN TRỌNG: đây là ƯỚC TÍNH để chọn thông số. Giá trị thật phải đo bằng Simplicity
Energy Profiler / Nordic PPK2 (xem docs/07-power-budget.md) rồi cập nhật lại các tham số
`q_*` bên dưới.

Chạy:
    python3 tools/power_budget.py              # in bảng các kịch bản
    python3 tools/power_budget.py --sensitivity  # thêm phân tích độ nhạy
    python3 tools/power_budget.py --markdown     # xuất bảng Markdown
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field, replace

HOURS_PER_MONTH = 365.25 * 24 / 12  # 730.5 h


# ---------------------------------------------------------------------------
# Tham số
# ---------------------------------------------------------------------------
@dataclass
class Params:
    name: str

    # --- Nguồn ---
    capacity_mah: float = 600.0          # CR2450 danh định (hãng: 540–620 mAh)
    usable_fraction: float = 0.80        # cut-off áp + suy giảm do xung + lô/hãng
    temp_factor: float = 1.00            # 1,0 trong nhà 20–25 °C; ~0,85 nếu 0–10 °C
    self_discharge_pct_per_year: float = 1.0
    current_margin: float = 1.00         # hệ số an toàn nhân vào dòng (1,3 = +30 %)

    # --- Dòng nền (µA) ---
    i_em2_ua: float = 2.9                # MG24 datasheet: EM2, giữ 256 kB RAM, LFXO (1,3 µA nếu chỉ 16 kB)
    i_sensor_idle_ua: float = 0.08       # SHT40 idle (typ)
    i_leak_ua: float = 0.15              # rò tụ MLCC + PCB + MOSFET + nút bấm

    # --- Dòng tức thời (mA, phía pin 3 V, DC-DC bật) ---
    i_tx_ma: float = 13.0                # TX: datasheet 5,0 mA @0 dBm, 19,1 mA @+10 dBm; ~13 mA @+8 dBm (nội suy)
    i_rx_ma: float = 5.1                 # RX 802.15.4 (datasheet)
    i_cpu_ma: float = 2.5                # EM0 39 MHz (~1,3 mA) + HFXO + ngoại vi, có biên
    i_idle_radio_ma: float = 1.3         # EM1 + HFXO trong lúc CSMA backoff

    # --- Thread / ICD ---
    slow_poll_s: float = 15.0            # SIT: ≤15 s theo spec (SDK tự kẹp khi đang SIT)
    fast_poll_ms: float = 500.0          # active mode
    active_mode_threshold_ms: float = 5000.0  # LIT-capable: SDK bắt buộc ≥ 5000 ms
    active_mode_duration_ms: float = 0.0      # 0 = không tự thức định kỳ
    idle_mode_duration_s: float = 1800.0  # = MaxInterval của subscription (ICD)
    periodic_report_s: float = 0.0        # >0: ShortIdle + report-on-active (bẫy năng lượng)
    ssed_csl_period_ms: float = 0.0      # >0 => SSED: thay poll bằng CSL sample
    csl_sync_poll_s: float = 30.0        # SSED: poll/TX để giữ đồng bộ CSL
    supervision_interval_s: float = 129.0  # child supervision (0 = tắt)

    # --- Ứng dụng ---
    measure_interval_s: float = 30.0
    change_reports_per_day: float = 48.0  # số lần vượt ngưỡng ΔT/ΔRH mỗi ngày
    subscribers: int = 2                  # số subscription đồng thời (mỗi hệ sinh thái ≥1)
    checkins_per_day: float = 0.0         # LIT: khi controller mất subscription
    srp_updates_per_day: float = 12.0
    battery_meas_per_day: float = 4.0
    led_blinks_per_day: float = 2.0
    reattach_per_month: float = 2.0       # router/BR khởi động lại...
    outage_hours_per_month: float = 2.0   # mất parent kéo dài -> attach backoff
    attach_attempts_per_outage_hour: float = 3.0  # backoff tối đa ~20 phút

    # --- Thời gian các pha (ms) — chỉnh theo kết quả đo ---
    t_wake_ms: float = 0.8               # EM2->EM0 (13,7 µs) + HFXO (188 µs) + RAIL/OT, có biên
    t_backoff_ms: float = 1.1            # CSMA-CA: trung bình 3,5 × 320 µs
    t_poll_tx_ms: float = 0.85           # Data Request có bảo mật MAC ~27 byte @250 kbps
    t_poll_rx_ms: float = 0.85           # CCA + turnaround + chờ/nhận ACK
    t_report_tx_ms: float = 3.5          # ReportData ~110 byte PHY
    t_report_cpu_ms: float = 2.0         # mã hoá AES-CCM, encode IM
    t_resp_rx_ms: float = 2.6            # StatusResponse ~80 byte
    t_ack_tx_ms: float = 2.2             # MRP standalone ACK ~65 byte
    t_csl_rx_ms: float = 1.5             # cửa sổ CSL
    q_sensor_uc: float = 2.2             # SHT40 high repeatability: 6,9 ms × 320 µA
    q_meas_cpu_uc: float = 2.0
    q_srp_uc: float = 600.0
    q_attach_uc: float = 12000.0         # ~2 s RX khi tìm parent + Child ID
    q_led_uc: float = 100.0              # 2 mA × 50 ms
    q_batt_meas_uc: float = 5.0
    q_checkin_uc: float = 0.0            # 0 => tự tính như 1 lần gửi + đuôi active

    note: str = ""

    # -------------------------------------------------------------------
    # Điện tích từng sự kiện (µC)
    # -------------------------------------------------------------------
    def q_wake(self) -> float:
        return self.t_wake_ms * self.i_cpu_ma

    def q_poll(self) -> float:
        return (self.q_wake() + self.t_backoff_ms * self.i_idle_radio_ma
                + self.t_poll_tx_ms * self.i_tx_ma + self.t_poll_rx_ms * self.i_rx_ma)

    def q_csl_sample(self) -> float:
        return self.q_wake() + self.t_csl_rx_ms * self.i_rx_ma

    def q_tx_frame(self, t_tx_ms: float, t_cpu_ms: float) -> float:
        # backoff + CCA (~0,13 ms RX) + chờ/nhận MAC ACK (~0,6 ms RX) + phát + xử lý CPU
        return (self.t_backoff_ms * self.i_idle_radio_ma + t_tx_ms * self.i_tx_ma
                + 0.73 * self.i_rx_ma + t_cpu_ms * self.i_cpu_ma)

    def q_report_per_subscriber(self) -> float:
        q_tx_report = self.q_tx_frame(self.t_report_tx_ms, self.t_report_cpu_ms)
        # Nhận StatusResponse: 1 poll + nhận khung + phát MAC ACK + xử lý
        q_rx_resp = self.q_poll() + self.t_resp_rx_ms * self.i_rx_ma + 0.35 * self.i_tx_ma + 2.0 * self.i_cpu_ma
        q_tx_ack = self.q_tx_frame(self.t_ack_tx_ms, 1.0)
        return q_tx_report + q_rx_resp + q_tx_ack

    def q_active_tail(self, threshold_ms: float | None = None) -> float:
        """Các poll nhanh trong khoảng ActiveModeThreshold sau hoạt động mạng cuối."""
        thr = self.active_mode_threshold_ms if threshold_ms is None else threshold_ms
        n = thr / self.fast_poll_ms + 1.0  # +1 poll chờ phản hồi
        q_one = self.q_csl_sample() if self.ssed_csl_period_ms > 0 else self.q_poll()
        return n * q_one

    def q_report_event(self) -> float:
        """Một lần báo cáo đồng bộ cho tất cả subscriber (SynchronizedReportScheduler)."""
        return self.q_wake() + self.subscribers * self.q_report_per_subscriber() + self.q_active_tail()

    def q_checkin(self) -> float:
        if self.q_checkin_uc > 0:
            return self.q_checkin_uc
        return self.q_wake() + self.q_tx_frame(2.5, 2.0) + self.q_active_tail()

    def q_measure(self) -> float:
        return self.q_sensor_uc + self.q_meas_cpu_uc

    # -------------------------------------------------------------------
    # Dòng trung bình từng thành phần (µA)
    # -------------------------------------------------------------------
    def breakdown(self) -> dict[str, float]:
        day = 86400.0
        b: dict[str, float] = {}
        b["Ngủ EM2 (MG24, giữ RAM, LFXO)"] = self.i_em2_ua
        b["Cảm biến idle + rò rỉ"] = self.i_sensor_idle_ua + self.i_leak_ua

        if self.ssed_csl_period_ms > 0:
            b["CSL sample (SSED)"] = self.q_csl_sample() / (self.ssed_csl_period_ms / 1000.0)
            b["Poll giữ đồng bộ CSL"] = self.q_poll() / self.csl_sync_poll_s
        else:
            b["Poll Thread (idle)"] = self.q_poll() / self.slow_poll_s

        # Chu kỳ active định kỳ khi hết IdleModeDuration (fast poll trong ActiveModeDuration)
        n_fast = self.active_mode_duration_ms / self.fast_poll_ms
        b["Active định kỳ (hết IdleModeDuration)"] = n_fast * self.q_poll() / self.idle_mode_duration_s

        if self.supervision_interval_s > 0:
            q_sup = self.t_resp_rx_ms * 0.3 * self.i_rx_ma + 0.35 * self.i_tx_ma + 1.0 * self.i_cpu_ma
            b["Child supervision"] = q_sup / self.supervision_interval_s

        b["Đo cảm biến"] = self.q_measure() / self.measure_interval_s

        # Báo cáo do thay đổi + keep-alive (MaxInterval = IdleModeDuration)
        rate_change = self.change_reports_per_day / day  # /s
        p_no_change = math.exp(-rate_change * self.idle_mode_duration_s)
        keepalive_per_day = (day / self.idle_mode_duration_s) * p_no_change
        b["Báo cáo khi thay đổi"] = self.change_reports_per_day * self.q_report_event() / day
        b["Báo cáo keep-alive (MaxInterval)"] = keepalive_per_day * self.q_report_event() / day
        b["Check-In (LIT)"] = self.checkins_per_day * self.q_checkin() / day
        if self.periodic_report_s > 0:
            b["Báo cáo định kỳ (ShortIdle)"] = self.q_report_event() / self.periodic_report_s

        b["SRP refresh + bảo trì mạng"] = self.srp_updates_per_day * self.q_srp_uc / day
        b["Đo pin + LED"] = (self.battery_meas_per_day * self.q_batt_meas_uc
                             + self.led_blinks_per_day * self.q_led_uc) / day
        month_s = HOURS_PER_MONTH * 3600.0
        attaches = self.reattach_per_month + self.outage_hours_per_month * self.attach_attempts_per_outage_hour
        b["Re-attach / mất parent"] = attaches * self.q_attach_uc / month_s
        return b

    def i_avg_ua(self) -> float:
        return sum(self.breakdown().values())

    def self_discharge_ua(self) -> float:
        return self.capacity_mah * self.self_discharge_pct_per_year / 100.0 / (365.25 * 24) * 1000.0

    def usable_mah(self) -> float:
        return self.capacity_mah * self.usable_fraction * self.temp_factor

    def life_months(self) -> float:
        i_total_ma = (self.i_avg_ua() * self.current_margin + self.self_discharge_ua()) / 1000.0
        return self.usable_mah() / i_total_ma / HOURS_PER_MONTH


# ---------------------------------------------------------------------------
# Kịch bản
# ---------------------------------------------------------------------------
BASE = Params(name="A. LIT-capable, đang chạy SIT (khuyến nghị)",
              note="poll 15 s, fast 500 ms, AMT 5 s, 2 subscriber, 48 báo cáo/ngày")

SCENARIOS: list[Params] = [
    BASE,
    replace(BASE, name="B. Cùng firmware, đang chạy LIT",
            slow_poll_s=1800.0, checkins_per_day=1.0,
            note="controller đã RegisterClient (vd. HA matter.js server)"),
    replace(BASE, name="C. Firmware chỉ SIT (không LITS)",
            fast_poll_ms=200.0, active_mode_threshold_ms=1000.0,
            note="AMT được phép < 5 s"),
    replace(BASE, name="D. SSED, CSL 1 s",
            ssed_csl_period_ms=1000.0, note="SSED không có lợi cho cảm biến"),
    replace(BASE, name="E. Bẫy: ShortIdle 60 s + report-on-active",
            periodic_report_s=60.0, fast_poll_ms=1000.0,
            note="mặc định lit-icd-app khi rơi về SIT"),
    replace(BASE, name="F. Bẫy: SED poll 2 s",
            slow_poll_s=2.0, note="minh hoạ độ nhạy"),
    replace(BASE, name="G. Xấu nhưng thực tế",
            subscribers=4, change_reports_per_day=150.0, i_tx_ma=19.1, i_em2_ua=3.9,
            i_leak_ua=1.0, outage_hours_per_month=24.0, temp_factor=0.85,
            current_margin=1.3, note="4 hệ sinh thái, TX +10 dBm, phòng lạnh, rò 1 µA, PD0D quên tắt"),
]

CONSERVATIVE = dict(usable_fraction=0.70, current_margin=1.5)


def fmt_months(m: float) -> str:
    return f"{m:5.1f} th ({m / 12:4.1f} năm)"


def print_table(markdown: bool) -> None:
    rows = []
    for p in SCENARIOS:
        pc = replace(p, **CONSERVATIVE) if p.current_margin == 1.0 else p
        rows.append((p.name, p.i_avg_ua(), p.life_months(), pc.life_months(), p.note))
    if markdown:
        print("| Kịch bản | I_avg (µA) | Tuổi thọ danh định | Tuổi thọ thận trọng* | Ghi chú |")
        print("|---|---:|---:|---:|---|")
        for n, i, l1, l2, note in rows:
            print(f"| {n} | {i:.1f} | {fmt_months(l1)} | {fmt_months(l2)} | {note} |")
        print("\n*Thận trọng: dung lượng dùng được 70 %, dòng × 1,5, tự xả 1 %/năm "
              "(kịch bản G đã tự mang hệ số riêng).")
    else:
        print(f"{'Kịch bản':42s} {'I_avg':>8s} {'danh định':>20s} {'thận trọng':>20s}")
        for n, i, l1, l2, _ in rows:
            print(f"{n:42s} {i:7.2f}µA {fmt_months(l1):>20s} {fmt_months(l2):>20s}")


def print_breakdown(p: Params, markdown: bool) -> None:
    b = p.breakdown()
    total = sum(b.values())
    if markdown:
        print(f"\n**{p.name}** — điện tích mỗi sự kiện: poll {p.q_poll():.1f} µC, "
              f"đo {p.q_measure():.1f} µC, báo cáo (đồng bộ {p.subscribers} sub) "
              f"{p.q_report_event():.0f} µC\n")
        print("| Thành phần | µA | % |")
        print("|---|---:|---:|")
        for k, v in sorted(b.items(), key=lambda kv: -kv[1]):
            print(f"| {k} | {v:.3f} | {100 * v / total:.1f} |")
        print(f"| **Tổng** | **{total:.2f}** | 100 |")
    else:
        print(f"\n== {p.name} ==  (poll {p.q_poll():.1f} µC, report-event {p.q_report_event():.0f} µC)")
        for k, v in sorted(b.items(), key=lambda kv: -kv[1]):
            print(f"  {k:40s} {v:7.3f} µA  {100 * v / total:5.1f} %")
        print(f"  {'TỔNG':40s} {total:7.3f} µA")


SENS_PARAMS = [
    ("i_em2_ua", "Dòng EM2 nền"),
    ("i_leak_ua", "Rò rỉ (tụ/PCB/flux)"),
    ("slow_poll_s", "Slow poll interval"),
    ("change_reports_per_day", "Số báo cáo/ngày"),
    ("subscribers", "Số subscriber"),
    ("active_mode_threshold_ms", "ActiveModeThreshold"),
    ("fast_poll_ms", "Fast poll interval"),
    ("i_tx_ma", "Dòng TX (công suất phát)"),
    ("measure_interval_s", "Chu kỳ đo"),
]


def print_sensitivity(markdown: bool) -> None:
    base_life = BASE.life_months()
    res = []
    for attr, label in SENS_PARAMS:
        v = getattr(BASE, attr)
        lo = replace(BASE, **{attr: type(v)(v * 0.5) if attr != "subscribers" else max(1, v // 2)})
        hi = replace(BASE, **{attr: type(v)(v * 2.0)})
        res.append((label, attr, v, lo.life_months(), hi.life_months()))
    res.sort(key=lambda r: -abs(r[4] - r[3]))
    if markdown:
        print("\n| Tham số | Giá trị gốc | Tuổi thọ khi ×0,5 | Tuổi thọ khi ×2 | Biên độ |")
        print("|---|---:|---:|---:|---:|")
        for label, attr, v, l_lo, l_hi in res:
            print(f"| {label} (`{attr}`) | {v:g} | {l_lo:.1f} th | {l_hi:.1f} th | {abs(l_hi - l_lo):.1f} th |")
        print(f"\nTuổi thọ gốc (kịch bản A, danh định): {base_life:.1f} tháng")
    else:
        print(f"\nĐộ nhạy quanh kịch bản A (gốc {base_life:.1f} tháng):")
        for label, attr, v, l_lo, l_hi in res:
            print(f"  {label:32s} {v:>8g}  ×0.5 -> {l_lo:6.1f} th   ×2 -> {l_hi:6.1f} th")


def required_avg_current(target_months: float, p: Params) -> float:
    """Dòng trung bình danh định tối đa (µA) để đạt target với hệ số của p."""
    usable_mah = p.usable_mah()
    i_total_ma = usable_mah / (target_months * HOURS_PER_MONTH)
    return (i_total_ma * 1000.0 - p.self_discharge_ua()) / p.current_margin


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--sensitivity", action="store_true")
    ap.add_argument("--target-months", type=float, default=18.0)
    a = ap.parse_args()

    print_table(a.markdown)
    for p in SCENARIOS:
        print_breakdown(p, a.markdown)
    if a.sensitivity:
        print_sensitivity(a.markdown)

    cons = replace(BASE, **CONSERVATIVE)
    print(f"\nĐể đạt {a.target_months:.0f} tháng: I_avg danh định ≤ "
          f"{required_avg_current(a.target_months, BASE):.1f} µA (không hệ số an toàn), "
          f"≤ {required_avg_current(a.target_months, cons):.1f} µA (thận trọng: 70 % dung lượng, dòng × 1,5).")


if __name__ == "__main__":
    main()
