#!/usr/bin/env python3
"""
Sinh project KiCad 7 (mở được bằng KiCad 7/8/9+) cho cảm biến T/RH EFR32MG24 + CR2450:
  - lib/tsensor.kicad_sym           : symbol EFR32MG24B010F1536IM40 (QFN40)
  - lib/tsensor.pretty/*.kicad_mod   : footprint QFN40 theo land pattern datasheet, kẹp pin MY-2450-03
  - tsensor.kicad_sch                : schematic A3 kiểu "nhãn net" (sinh từ design.py)
  - tsensor.kicad_pro, sym-lib-table, fp-lib-table

Dùng:  python3 tools/kicad_gen/gen_kicad.py hardware/kicad
PCB sinh riêng bằng gen_pcb.py (cần module pcbnew của KiCad).
"""
from __future__ import annotations

import json
import math
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design as D  # noqa: E402

KICAD_SYM_DIR = Path("/usr/share/kicad/symbols")
KICAD_TEMPLATE_PRO = Path("/usr/share/kicad/template/kicad.kicad_pro")
PROJECT = "tsensor"
NS = uuid.UUID("6f1c2f4e-7a5b-4c1e-9a77-2b1d3e4f5a60")
GRID = 1.27


def uid(*parts: object) -> str:
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fmt(v: float) -> str:
    v = round(v, 4)
    if abs(v) < 1e-9:
        v = 0.0
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


# ---------------------------------------------------------------------------
# Đọc symbol từ thư viện KiCad (trích khối văn bản theo cặp ngoặc)
# ---------------------------------------------------------------------------
def extract_block(src: str, name: str) -> str:
    i = src.index("(symbol %s" % q(name))
    depth = 0
    in_str = False
    j = i
    while j < len(src):
        c = src[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise ValueError(name)


PIN_RE = re.compile(
    r'\(pin (\w+) (\w+) \(at ([-\d.]+) ([-\d.]+) (\d+)\) \(length ([\d.]+)\)( hide)?\s*'
    r'\(name "((?:[^"\\]|\\.)*)"[^\n]*\n\s*\(number "([^"]*)"')


def pins_of(block: str):
    out = {}
    for m in PIN_RE.finditer(block):
        etype, _shape, x, y, ang, _ln, _hide, name, num = m.groups()
        out[num] = dict(name=name, type=etype, x=float(x), y=float(y), angle=int(ang))
    return out


_lib_cache: dict[str, str] = {}


def lib_symbol(lib_id: str) -> tuple[str, dict]:
    """Trả về (khối symbol đã đổi tên thành 'Lib:Name', bảng chân)."""
    lib, name = lib_id.split(":")
    if lib == "tsensor":
        block = mg24_symbol_block()
    else:
        if lib not in _lib_cache:
            _lib_cache[lib] = (KICAD_SYM_DIR / f"{lib}.kicad_sym").read_text()
        block = extract_block(_lib_cache[lib], name)
        if "(extends" in block[:300]:
            raise ValueError(f"{lib_id}: symbol dẫn xuất (extends) chưa hỗ trợ")
    pins = pins_of(block)
    renamed = block.replace("(symbol %s" % q(name), "(symbol %s" % q(lib_id), 1)
    return renamed, pins


# ---------------------------------------------------------------------------
# Symbol tuỳ biến EFR32MG24B010F1536IM40
# ---------------------------------------------------------------------------
MG24_NAME = "EFR32MG24B010F1536IM40"
MG24_FP = "tsensor:EFR32MG24_QFN40_5x5mm_P0.4mm_EP3.85x3.85mm"


def _pin(etype: str, x: float, y: float, ang: int, name: str, num: str, length: float = 2.54) -> str:
    return (f'      (pin {etype} line (at {fmt(x)} {fmt(y)} {ang}) (length {fmt(length)})\n'
            f'        (name {q(name)} (effects (font (size 1.27 1.27))))\n'
            f'        (number {q(num)} (effects (font (size 1.27 1.27))))\n'
            f'      )\n')


def mg24_symbol_block(name: str = MG24_NAME) -> str:
    pins = []
    y0 = 30.48
    for i, num in enumerate(D.MG24_LEFT):
        if num is None:
            continue
        nm, et, _ = D.MG24_PINS[num]
        pins.append(_pin(et, -20.32, y0 - 2.54 * i, 0, nm, str(num)))
    for i, num in enumerate(D.MG24_RIGHT):
        if num is None:
            continue
        nm, et, _ = D.MG24_PINS[num]
        pins.append(_pin(et, 20.32, y0 - 2.54 * i, 180, nm, str(num)))
    for i, num in enumerate(D.MG24_BOTTOM):
        nm, et, _ = D.MG24_PINS[num]
        pins.append(_pin(et, -2.54 + 2.54 * i, -38.1, 90, nm, str(num)))
    props = [
        ("Reference", "U", 0, 34.29, False),
        ("Value", name, 0, -40.64, False),
        ("Footprint", MG24_FP, 0, -43.18, True),
        ("Datasheet", "https://www.silabs.com/documents/public/data-sheets/efr32mg24-datasheet.pdf", 0, -45.72, True),
        ("ki_keywords", "Silicon Labs EFR32 MG24 Matter Thread Zigbee BLE 802.15.4 2.4GHz", 0, 0, True),
        ("ki_description", "EFR32MG24 Wireless SoC, Cortex-M33 78 MHz, 1536 kB flash, 256 kB RAM, +10 dBm, "
                           "Secure Vault High, QFN-40 5x5 mm", 0, 0, True),
    ]
    out = [f'  (symbol {q(name)} (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n']
    for k, v, x, y, hide in props:
        out.append(f'    (property {q(k)} {q(v)} (at {fmt(x)} {fmt(y)} 0)\n'
                   f'      (effects (font (size 1.27 1.27)){" hide" if hide else ""})\n    )\n')
    out.append(f'    (symbol {q(name + "_0_1")}\n'
               f'      (rectangle (start -17.78 33.02) (end 17.78 -35.56)\n'
               f'        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n    )\n')
    out.append(f'    (symbol {q(name + "_1_1")}\n')
    out.extend(pins)
    out.append('    )\n  )\n')
    return "".join(out)


def write_symbol_lib(lib_dir: Path) -> None:
    text = ('(kicad_symbol_lib (version 20220914) (generator kicad_gen)\n'
            + mg24_symbol_block() + ')\n')
    (lib_dir / "tsensor.kicad_sym").write_text(text)


# ---------------------------------------------------------------------------
# Footprint tuỳ biến
# ---------------------------------------------------------------------------
def fp_header(name: str, descr: str, tags: str, attr: str = "smd") -> list[str]:
    return [f'(footprint {q(name)} (version 20221018) (generator kicad_gen)\n',
            '  (layer "F.Cu")\n',
            f'  (descr {q(descr)})\n',
            f'  (tags {q(tags)})\n',
            f'  (attr {attr})\n']


def fp_text(kind: str, text: str, x: float, y: float, layer: str, size: float = 1.0) -> str:
    return (f'  (fp_text {kind} {q(text)} (at {fmt(x)} {fmt(y)}) (layer {q(layer)})\n'
            f'    (effects (font (size {fmt(size)} {fmt(size)}) (thickness {fmt(size * 0.15)})))\n  )\n')


def fp_line(x1, y1, x2, y2, layer, w):
    return (f'  (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
            f'(stroke (width {fmt(w)}) (type solid)) (layer {q(layer)}))\n')


def fp_rect(x1, y1, x2, y2, layer, w):
    return (fp_line(x1, y1, x2, y1, layer, w) + fp_line(x2, y1, x2, y2, layer, w)
            + fp_line(x2, y2, x1, y2, layer, w) + fp_line(x1, y2, x1, y1, layer, w))


def fp_circle(cx, cy, r, layer, w):
    return (f'  (fp_circle (center {fmt(cx)} {fmt(cy)}) (end {fmt(cx + r)} {fmt(cy)}) '
            f'(stroke (width {fmt(w)}) (type solid)) (fill none) (layer {q(layer)}))\n')


def fp_poly(pts, layer, w):
    xy = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return (f'  (fp_poly (pts {xy}) (stroke (width {fmt(w)}) (type solid)) (fill none) (layer {q(layer)}))\n')


def write_qfn40(lib_dir: Path) -> None:
    """Land pattern theo datasheet EFR32MG24 Rev 1.1, Table 7.2:
    pad 0,74 × 0,22 mm, mép trong cách nhau S = 4,25 mm (tâm pad ±2,495), EP 3,85 × 3,85 mm,
    stencil EP 3×3 ô 0,90 mm bước 1,20 mm."""
    name = "EFR32MG24_QFN40_5x5mm_P0.4mm_EP3.85x3.85mm"
    out = fp_header(name, "EFR32MG24 QFN-40 5x5 mm P0.4 mm, land pattern per EFR32MG24 datasheet Rev 1.1 Table 7.2",
                    "QFN 40 EFR32MG24 Silicon Labs")
    out.append(fp_text("reference", "REF**", 0, -3.9, "F.SilkS"))
    out.append(fp_text("value", name, 0, 3.9, "F.Fab", 0.6))
    out.append(fp_text("user", "${REFERENCE}", 0, 0, "F.Fab", 0.8))
    c = 2.495
    L, W = 0.74, 0.22
    pads = []
    for n in range(1, 41):
        if n <= 10:
            x, y, sx, sy = -c, -1.8 + 0.4 * (n - 1), L, W
        elif n <= 20:
            x, y, sx, sy = -1.8 + 0.4 * (n - 11), c, W, L
        elif n <= 30:
            x, y, sx, sy = c, 1.8 - 0.4 * (n - 21), L, W
        else:
            x, y, sx, sy = 1.8 - 0.4 * (n - 31), -c, W, L
        pads.append(f'  (pad "{n}" smd roundrect (at {fmt(x)} {fmt(y)}) (size {fmt(sx)} {fmt(sy)}) '
                    f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))\n')
    # Exposed pad (GND), không phủ kem toàn bộ: dùng 3×3 ô kem riêng
    pads.append('  (pad "41" smd rect (at 0 0) (size 3.85 3.85) (layers "F.Cu" "F.Mask") (zone_connect 2))\n')
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            pads.append(f'  (pad "" smd rect (at {fmt(1.2 * i)} {fmt(1.2 * j)}) (size 0.9 0.9) (layers "F.Paste"))\n')
    # Via GND trong EP (nằm giữa các ô kem để hạn chế hút thiếc)
    for i in (-1, 1):
        for j in (-1, 1):
            pads.append(f'  (pad "41" thru_hole circle (at {fmt(0.6 * i)} {fmt(0.6 * j)}) (size 0.5 0.5) '
                        f'(drill 0.25) (layers "*.Cu") (zone_connect 2))\n')
    out.extend(pads)
    # Fab, silk, courtyard
    out.append(fp_poly([(-1.75, -2.5), (2.5, -2.5), (2.5, 2.5), (-2.5, 2.5), (-2.5, -1.75), (-1.75, -2.5)], "F.Fab", 0.1))
    for sx_, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x0, y0 = 2.61 * sx_, 2.61 * sy_
        out.append(fp_line(x0, y0, x0 - 0.45 * sx_, y0, "F.SilkS", 0.12))
        if not (sx_ == -1 and sy_ == -1):
            out.append(fp_line(x0, y0, x0, y0 - 0.45 * sy_, "F.SilkS", 0.12))
    out.append(fp_line(-2.61, -2.61, -3.05, -2.61, "F.SilkS", 0.12))  # dấu chân 1
    out.append(fp_rect(-3.15, -3.15, 3.15, 3.15, "F.CrtYd", 0.05))
    out.append(")\n")
    (lib_dir / f"{name}.kicad_mod").write_text("".join(out))


def write_battery_clip(lib_dir: Path) -> None:
    """MYOUNG MY-2450-03 (LCSC C2988622): 2 pad 2,6 × 7,6 mm, tổng bề ngang mép–mép 29,90 mm
    (tâm ±13,65 mm). Cực (−) là pad tròn ENIG trên PCB. Vẽ ở mặt trước; gen_pcb lật sang mặt sau."""
    name = "BatteryClip_MYOUNG_MY-2450-03_CR2450"
    out = fp_header(name, "CR2450 SMD retainer MYOUNG MY-2450-03 (+) with PCB pad as (-) contact, "
                          "pad span 29.90 mm outer per datasheet", "battery CR2450 coin cell retainer")
    out.append(fp_text("reference", "REF**", 0, -9.0, "F.SilkS"))
    out.append(fp_text("value", name, 0, 9.0, "F.Fab", 0.8))
    out.append(fp_text("user", "${REFERENCE}", 0, 4.5, "F.Fab", 1.0))
    for x in (-13.65, 13.65):
        out.append(f'  (pad "1" smd rect (at {fmt(x)} 0) (size 2.6 7.6) (layers "F.Cu" "F.Paste" "F.Mask"))\n')
    out.append('  (pad "2" smd circle (at 0 0) (size 9 9) (layers "F.Cu" "F.Mask") (zone_connect 2))\n')
    out.append(fp_circle(0, 0, 12.25, "F.Fab", 0.1))           # pin CR2450 Ø24,5
    out.append(fp_rect(-14.55, -7.7, 14.55, 7.7, "F.Fab", 0.1))  # kẹp 29,1 × 15,4
    out.append(fp_text("user", "CR2450 +", 0, -4.5, "F.Fab", 1.0))
    for x in (-11.8, 11.8):
        out.append(fp_line(x, -4.4, x, 4.4, "F.SilkS", 0.12))
    out.append(fp_line(10.4, -6.2, 11.4, -6.2, "F.SilkS", 0.15))
    out.append(fp_line(10.9, -6.7, 10.9, -5.7, "F.SilkS", 0.15))
    # Courtyard = hợp của hình tròn r=12,75 và chữ nhật ±15,25 × ±7,95
    r, hx, hy = 12.75, 15.25, 7.95
    xc = math.sqrt(r * r - hy * hy)
    n = 24

    def arc(a_from, a_to):
        return [(r * math.cos(a_from + (a_to - a_from) * k / n), r * math.sin(a_from + (a_to - a_from) * k / n))
                for k in range(1, n)]

    pts = [(hx, hy), (hx, -hy), (xc, -hy)]
    pts += arc(math.atan2(-hy, xc), math.atan2(-hy, -xc))      # cung trên (qua y = -r)
    pts += [(-xc, -hy), (-hx, -hy), (-hx, hy), (-xc, hy)]
    pts += arc(math.atan2(hy, -xc), math.atan2(hy, xc))        # cung dưới (qua y = +r)
    pts.append((xc, hy))
    out.append(fp_poly(pts, "F.CrtYd", 0.05))
    out.append(")\n")
    (lib_dir / f"{name}.kicad_mod").write_text("".join(out))


# ---------------------------------------------------------------------------
# Schematic
# ---------------------------------------------------------------------------
ROOT_UUID = uid("root-sheet")


def rot_vec(dx: float, dy: float, r: int) -> tuple[float, float]:
    """Xoay vector (toạ độ màn hình, y xuống) ngược chiều kim đồng hồ r độ."""
    a = math.radians(r)
    return (dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a))


def pin_geometry(pin: dict, sx: float, sy: float, rot: int):
    """Điểm nối (toạ độ schematic) và hướng ra ngoài (đơn vị) của một chân."""
    ox, oy = rot_vec(pin["x"], -pin["y"], rot)
    a = math.radians(pin["angle"])
    bx, by = rot_vec(math.cos(a), -math.sin(a), rot)   # hướng từ điểm nối vào thân
    out = (-round(bx), -round(by))
    return (snap(sx + ox), snap(sy + oy)), out


class Sch:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.lib_blocks: dict[str, str] = {}
        self.lib_pins: dict[str, dict] = {}
        self.pwr_n = 0
        self.flg_n = 0

    def need(self, lib_id: str) -> dict:
        if lib_id not in self.lib_blocks:
            block, pins = lib_symbol(lib_id)
            self.lib_blocks[lib_id] = block
            self.lib_pins[lib_id] = pins
        return self.lib_pins[lib_id]

    # --- phần tử cơ bản -------------------------------------------------
    def wire(self, x1, y1, x2, y2, key):
        self.items.append(f'  (wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)}))\n'
                          f'    (stroke (width 0) (type default))\n    (uuid {uid("wire", key)})\n  )\n')

    def junction(self, x, y, key):
        self.items.append(f'  (junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0)\n'
                          f'    (uuid {uid("junction", key)})\n  )\n')

    def no_connect(self, x, y, key):
        self.items.append(f'  (no_connect (at {fmt(x)} {fmt(y)}) (uuid {uid("nc", key)}))\n')

    def label(self, net, x, y, d, key):
        ang, just = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "right")}[d]
        if net in D.GLOBAL_NETS:
            self.items.append(
                f'  (global_label {q(net)} (shape passive) (at {fmt(x)} {fmt(y)} {ang}) (fields_autoplaced)\n'
                f'    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {uid("glabel", key)})\n'
                f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {fmt(x)} {fmt(y)} 0)\n'
                f'      (effects (font (size 1.27 1.27)) hide)\n    )\n  )\n')
        else:
            self.items.append(
                f'  (label {q(net)} (at {fmt(x)} {fmt(y)} {ang}) (fields_autoplaced)\n'
                f'    (effects (font (size 1.27 1.27)) (justify {just} bottom))\n    (uuid {uid("label", key)})\n  )\n')

    def text(self, s, x, y, size, key):
        self.items.append(f'  (text {q(s)} (at {fmt(x)} {fmt(y)} 0)\n'
                          f'    (effects (font (size {fmt(size)} {fmt(size)})) (justify left bottom))\n'
                          f'    (uuid {uid("text", key)})\n  )\n')

    def symbol(self, lib_id, ref, value, x, y, rot, props=None, dnp=False, in_bom=True, on_board=True,
               ref_at=None, val_at=None, hide_ref=False, hide_val=False):
        pins = self.need(lib_id)
        props = props or {}
        ra = ref_at or (x + 2.54, y - 1.27)
        va = val_at or (x + 2.54, y + 1.27)
        lines = [f'  (symbol (lib_id {q(lib_id)}) (at {fmt(x)} {fmt(y)} {rot}) (unit 1)\n'
                 f'    (in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if on_board else "no"}) '
                 f'(dnp {"yes" if dnp else "no"})\n'
                 f'    (uuid {uid("sym", ref)})\n']

        def prop(k, v, px, py, hide, just="left"):
            lines.append(f'    (property {q(k)} {q(v)} (at {fmt(px)} {fmt(py)} {rot % 180})\n'
                         f'      (effects (font (size 1.27 1.27)) (justify {just}){" hide" if hide else ""})\n    )\n')

        prop("Reference", ref, ra[0], ra[1], hide_ref)
        prop("Value", value, va[0], va[1], hide_val)
        for k, v in props.items():
            prop(k, v, x, y, True)
        for num in pins:
            lines.append(f'    (pin {q(num)} (uuid {uid("pin", ref, num)}))\n')
        lines.append(f'    (instances\n      (project {q(PROJECT)}\n'
                     f'        (path "/{ROOT_UUID}" (reference {q(ref)}) (unit 1))\n      )\n    )\n  )\n')
        self.items.append("".join(lines))
        return pins

    def gnd(self, x, y, d, key, hide_val=False):
        rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
        self.pwr_n += 1
        self.symbol("power:GND", f"#PWR{self.pwr_n:03d}", "GND", x, y, rot, in_bom=False, on_board=False,
                    ref_at=(x, y + 6.35), val_at=(x + 1.27 * d[0], y + 3.81 * (1 if d[1] >= 0 else -1)),
                    hide_ref=True, hide_val=hide_val)

    # --- kết nối một chân: đoạn dây + nhãn/GND, hoặc dấu NC ----------------
    def attach(self, ref, num, net, pt, d, stub, hide_gnd_val=False):
        key = f"{ref}.{num}"
        if net is None:
            self.no_connect(pt[0], pt[1], key)
            return
        end = (snap(pt[0] + d[0] * stub), snap(pt[1] + d[1] * stub))
        self.wire(pt[0], pt[1], end[0], end[1], key)
        if net == "GND":
            self.gnd(end[0], end[1], d, key, hide_val=hide_gnd_val)
        else:
            self.label(net, end[0], end[1], d, key)

    def wire_bus(self, net, points):
        """Nối các chân của một net bằng dây: chân ngang nằm trên trục y0 (chuỗi nối tiếp),
        chân khác (tụ shunt) thả dây dọc lên trục; thêm junction ở điểm chữ T."""
        ys = [p[1] for p in points]
        y0 = max(set(ys), key=ys.count)
        bus_x = sorted({p[0] for p in points})
        for i in range(len(bus_x) - 1):
            self.wire(bus_x[i], y0, bus_x[i + 1], y0, f"{net}.bus{i}")
        # một nhãn đặt trên dây để net có tên
        lx = snap(bus_x[0] + 1.27) if len(bus_x) > 1 and bus_x[1] - bus_x[0] > 1.27 else bus_x[0]
        self.label(net, lx, y0, (1, 0), f"{net}.name")
        pin_on_bus = {p[0] for p in points if abs(p[1] - y0) < 1e-6}
        for k, (x, y) in enumerate(points):
            if abs(y - y0) > 1e-6:
                self.wire(x, y, x, y0, f"{net}.drop{k}")
                if x not in pin_on_bus and bus_x[0] < x < bus_x[-1]:
                    self.junction(x, y0, f"{net}.{k}")


def build_schematic(out_dir: Path) -> dict:
    sch = Sch()
    expected = {}
    wired: dict[str, list] = {}
    for p in D.PARTS:
        x, y, rot = p["sch"]
        props = {"Footprint": p["footprint"], "Datasheet": "~"}
        if p["mpn"]:
            props["MPN"] = p["mpn"]
        if p["mfr"]:
            props["Manufacturer"] = p["mfr"]
        if p["lcsc"]:
            props["LCSC"] = p["lcsc"]
        if p["spec"]:
            props["Spec"] = p["spec"]
        if p["note"]:
            props["Note"] = p["note"]
        is_ic = p["ref"] in ("U1",)
        if is_ic:
            ra, va = (x - 2.54, y - 35.56), (x - 2.54, y + 41.91)
        elif rot == 90:
            ra, va = (x - 2.54, y - 3.81), (x - 2.54, y + 5.08)
        elif p["ref"].startswith(("TP",)):
            ra, va = (x + 1.27, y - 3.81), (x + 1.27, y - 6.35)
        elif p["ref"] == "U2":
            ra, va = (x - 5.08, y - 11.43), (x - 15.24, y + 10.16)
        elif p["ref"] == "J1":
            ra, va = (x - 5.08, y - 11.43), (x - 5.08, y + 12.7)
        elif p["ref"] == "Y1":
            ra, va = (x + 5.08, y - 3.81), (x + 5.08, y + 3.81)
        elif p["ref"] in ("Y2", "D1", "SW1", "ANT1"):
            ra, va = (x - 3.81, y - 6.35), (x - 3.81, y - 3.81)
        else:
            ra, va = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27)
        pins = sch.symbol(p["lib_id"], p["ref"], p["value"], x, y, rot, props=props, dnp=p["dnp"],
                          ref_at=ra, val_at=va, hide_val=p["ref"].startswith("TP"))
        stub = 5.08 if is_ic else 2.54
        for num, pin in pins.items():
            net = p["pins"].get(num, "MISSING")
            if net == "MISSING":
                raise SystemExit(f"{p['ref']} chân {num} ({pin['name']}) chưa có net trong design.py")
            pt, d = pin_geometry(pin, x, y, rot)
            expected[(p["ref"], num)] = net
            if net in D.WIRED_NETS:
                wired.setdefault(net, []).append(pt)
                continue
            sch.attach(p["ref"], num, net, pt, d, stub, hide_gnd_val=is_ic and num != "13")
        for num in p["pins"]:
            if num not in pins:
                raise SystemExit(f"{p['ref']}: chân {num} không có trong symbol {p['lib_id']}")

    for net, pts in wired.items():
        sch.wire_bus(net, pts)

    # Cờ nguồn cho ERC
    for net, (x, y) in D.PWR_FLAGS.items():
        sch.flg_n += 1
        ref = f"#FLG{sch.flg_n:02d}"
        sch.symbol("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0, in_bom=False, on_board=False,
                   ref_at=(x, y - 5.08), val_at=(x - 2.54, y - 3.81), hide_ref=True)
        end = (x, snap(y + 2.54))
        sch.wire(x, y, end[0], end[1], ref)
        if net == "GND":
            sch.gnd(end[0], end[1], (0, 1), ref)
        else:
            sch.label(net, end[0], end[1], (0, 1), ref)

    for i, (x, y, size, s) in enumerate(D.SCH_TEXTS):
        sch.text(s, x, y, size, f"t{i}")

    lib = "".join(sch.lib_blocks[k] for k in sorted(sch.lib_blocks))
    lib = "\n".join("  " + ln if ln.strip() else ln for ln in lib.splitlines())
    head = (f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {ROOT_UUID})\n\n  (paper "A3")\n\n'
            '  (title_block\n'
            '    (title "Matter T/RH sensor - EFR32MG24 + CR2450")\n'
            '    (date "2026-11-07")\n    (rev "0.1")\n'
            '    (company "haxeko/matter-temperature-sensor-EFR32MG24")\n'
            '    (comment 1 "Biến thể A: chip trần EFR32MG24B010F1536IM40, bo Ø35 mm 4 lớp")\n'
            '    (comment 2 "Sinh tự động: tools/kicad_gen — sửa trong KiCad sau khi sinh là bình thường")\n'
            '    (comment 3 "VERIFY trước khi đặt hàng: mạng phối hợp RF (QFN40), decoupling theo ref design")\n'
            '  )\n\n'
            f'  (lib_symbols\n{lib}\n  )\n\n')
    tail = '\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n'
    (out_dir / f"{PROJECT}.kicad_sch").write_text(head + "".join(sch.items) + tail)
    return expected


# ---------------------------------------------------------------------------
# Project, bảng thư viện, luật thiết kế (JLCPCB 4 lớp)
# ---------------------------------------------------------------------------
def write_project(out_dir: Path) -> None:
    pro = json.loads(KICAD_TEMPLATE_PRO.read_text())
    pro["meta"] = {"filename": f"{PROJECT}.kicad_pro", "version": 1}
    pro["sheets"] = [[ROOT_UUID, ""]]
    ds = pro.setdefault("board", {}).setdefault("design_settings", {})
    ds["defaults"] = {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.0,
                      "copper_text_size_v": 1.0, "copper_text_thickness": 0.15, "silk_line_width": 0.12,
                      "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12,
                      "fab_line_width": 0.1, "courtyard_line_width": 0.05, "other_line_width": 0.1}
    ds["rules"] = {"min_clearance": 0.09, "min_track_width": 0.09, "min_via_diameter": 0.4,
                   "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1,
                   "min_copper_edge_clearance": 0.3, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.2,
                   "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08,
                   "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 1,
                   "allow_blind_buried_vias": False, "allow_microvias": False}
    ds["rule_severities"] = {"silk_over_copper": "warning", "silk_overlap": "warning",
                             "silk_edge_clearance": "warning", "lib_footprint_mismatch": "ignore",
                             "lib_footprint_issues": "ignore", "text_height": "warning"}
    ds["track_widths"] = [0.0, 0.15, 0.2, 0.3, 0.5]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.45, "drill": 0.25}]
    ds["diff_pair_dimensions"] = []
    ds["drc_exclusions"] = []

    def cls(name, clearance, width, via_d=0.45, via_dr=0.25):
        return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
                "track_width": width, "via_diameter": via_d, "via_drill": via_dr, "wire_width": 6}

    pro["net_settings"] = {
        "classes": [cls("Default", 0.127, 0.15), cls("Power", 0.15, 0.3), cls("RF", 0.15, 0.2)],
        "meta": {"version": 3},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [{"netclass": "Power", "pattern": p} for p in
                              ("VBAT", "VDCDC", "BAT_P", "DCDC_SW", "GND")]
                             + [{"netclass": "RF", "pattern": p} for p in
                                ("/RF_IO", "/RF_M1", "/RF_M2", "/RF_50", "/ANT_FEED")],
    }
    (out_dir / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (out_dir / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n'
        '  (lib (name "tsensor")(type "KiCad")(uri "${KIPRJMOD}/lib/tsensor.kicad_sym")(options "")'
        '(descr "Thư viện riêng của dự án"))\n)\n')
    (out_dir / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n'
        '  (lib (name "tsensor")(type "KiCad")(uri "${KIPRJMOD}/lib/tsensor.pretty")(options "")'
        '(descr "Footprint riêng của dự án"))\n)\n')


def write_jlc_bom(out_dir: Path) -> None:
    """BOM định dạng JLCPCB (Comment, Designator, Footprint, LCSC) sinh từ design.py; bỏ DNP."""
    import csv
    groups: dict[tuple, list] = {}
    for p in D.PARTS:
        if p["dnp"] or p["ref"].startswith("TP") or p["ref"] == "J1":
            continue
        key = (p["value"] + (f" {p['spec']}" if p["spec"] else ""), p["footprint"].split(":")[1], p["lcsc"], p["mpn"])
        groups.setdefault(key, []).append(p["ref"])
    path = out_dir / "build" / "bom_jlcpcb.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC", "MPN", "Qty"])
        for (comment, fp, lcsc, mpn), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([comment, ",".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):] or 0)))),
                        fp, lcsc, mpn, len(refs)])


def main() -> None:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "hardware/kicad")
    lib_dir = out_dir / "lib"
    (lib_dir / "tsensor.pretty").mkdir(parents=True, exist_ok=True)
    write_symbol_lib(lib_dir)
    write_qfn40(lib_dir / "tsensor.pretty")
    write_battery_clip(lib_dir / "tsensor.pretty")
    expected = build_schematic(out_dir)
    write_project(out_dir)
    exp_path = out_dir / "build" / "expected_nets.json"
    exp_path.parent.mkdir(exist_ok=True)
    write_jlc_bom(out_dir)
    exp_path.write_text(json.dumps({f"{r}.{n}": v for (r, n), v in sorted(expected.items())}, indent=1,
                                   ensure_ascii=False))
    print(f"OK: {len(D.PARTS)} linh kiện, {len(expected)} chân -> {out_dir}")


if __name__ == "__main__":
    main()
