#!/usr/bin/env python3
"""
Sinh tsensor.kicad_pcb (KiCad 7) từ design.py + netlist do KiCad xuất từ schematic.
Chạy bằng Python có module pcbnew (cài KiCad):
    python3 tools/kicad_gen/gen_pcb.py hardware/kicad <tsensor.net>
Kết quả: bo Ø35 mm 4 lớp 0,8 mm, viền có lưỡi cảm biến, linh kiện đã đặt theo floorplan,
net đã gán, zone GND (F.Cu, In1.Cu, B.Cu) + VBAT (In2.Cu), vùng cấm anten/lưỡi, via khâu GND.
CHƯA đi dây — phần đó làm trong KiCad (đặc biệt đường RF 50 Ω).
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design as D  # noqa: E402
from gen_kicad import PROJECT, uid  # noqa: E402

MM = pcbnew.FromMM
OX, OY = D.BOARD_ORIGIN

PCB_TEMPLATE = """(kicad_pcb (version 20221018) (generator pcbnew)
  (general (thickness 0.8))
  (paper "A4")
  (title_block
    (title "Matter T/RH sensor - EFR32MG24 + CR2450")
    (date "2026-11-07")
    (rev "0.1")
    (company "haxeko/matter-temperature-sensor-EFR32MG24")
    (comment 1 "Ø35 mm, 4 lớp 0,8 mm, ENIG. Chưa đi dây — xem docs/04-hardware.md")
  )
  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" power "In1.Cu-GND")
    (2 "In2.Cu" mixed "In2.Cu-VBAT")
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )
  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.05) (loss_tangent 0.02))
      (layer "In1.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 2" (type "core") (thickness 0.47) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
      (layer "In2.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 3" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.05) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
    (pad_to_mask_clearance 0)
    (aux_axis_origin 150 100)
    (grid_origin 150 100)
  )
  (net 0 "")
)
"""


def P(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def read_netlist(path: str) -> dict:
    text = open(path, encoding="utf-8").read()
    nets_part = text[text.index("(nets"):]
    out = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "((?:[^"\\]|\\.)*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)',
                         nets_part, re.S):
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
            out[(ref, pin)] = m.group(1)
    return out


class Builder:
    def __init__(self, board: pcbnew.BOARD) -> None:
        self.b = board
        self.nets: dict[str, pcbnew.NETINFO_ITEM] = {}

    def net(self, name: str) -> pcbnew.NETINFO_ITEM:
        if name not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(ni)
            self.nets[name] = ni
        return self.nets[name]

    # --- viền bo -------------------------------------------------------
    def seg(self, a, c, layer=pcbnew.Edge_Cuts, w=0.1):
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*c))
        s.SetLayer(layer)
        s.SetWidth(MM(w))
        self.b.Add(s)

    def arc(self, a, m, c, layer=pcbnew.Edge_Cuts, w=0.1):
        s = pcbnew.PCB_SHAPE(self.b)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(*a), P(*m), P(*c))
        s.SetLayer(layer)
        s.SetWidth(MM(w))
        self.b.Add(s)

    def outline(self) -> None:
        R = D.BOARD_R
        phi = math.radians(D.TONGUE_ANGLE_DEG)
        u = (math.cos(phi), math.sin(phi))
        v = (-math.sin(phi), math.cos(phi))

        def T(a, b):  # toạ độ lưỡi (dọc trục a, ngang b) -> toạ độ bo
            return (a * u[0] + b * v[0], a * u[1] + b * v[1])

        hw, sw, a_in = D.TONGUE_HALF_W, D.SLOT_W, D.SLOT_INNER
        b_in, b_out = hw, hw + sw
        a_out_edge = math.sqrt(R * R - b_out * b_out)
        a_in_edge = math.sqrt(R * R - b_in * b_in)
        r_cap = sw / 2
        # Cung lớn: từ mép ngoài khe +b, vòng qua phía đối diện lưỡi, tới mép ngoài khe -b
        self.arc(T(a_out_edge, b_out), T(-R, 0), T(a_out_edge, -b_out))
        # Khe -b: mép ngoài vào trong, đầu tròn, mép trong ra ngoài
        self.seg(T(a_out_edge, -b_out), T(a_in, -b_out))
        self.arc(T(a_in, -b_out), T(a_in - r_cap, -(hw + r_cap)), T(a_in, -b_in))
        self.seg(T(a_in, -b_in), T(a_in_edge, -b_in))
        # Đầu lưỡi (cung nhỏ của đường tròn)
        self.arc(T(a_in_edge, -b_in), T(R, 0), T(a_in_edge, b_in))
        # Khe +b
        self.seg(T(a_in_edge, b_in), T(a_in, b_in))
        self.arc(T(a_in, b_in), T(a_in - r_cap, hw + r_cap), T(a_in, b_out))
        self.seg(T(a_in, b_out), T(a_out_edge, b_out))
        self.tongue_T = T

    # --- linh kiện -----------------------------------------------------
    def footprint(self, part: dict, netmap: dict) -> pcbnew.FOOTPRINT:
        lib, name = part["footprint"].split(":")
        lib_path = (self.kicad_dir / "lib" / "tsensor.pretty") if lib == "tsensor" else Path(D.FP_STD) / f"{lib}.pretty"
        fp = pcbnew.FootprintLoad(str(lib_path), name)
        if fp is None:
            raise SystemExit(f"Không tải được footprint {part['footprint']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(part["ref"])
        fp.SetValue(part["value"])
        x, y, rot, side = part["pcb"]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH("/" + uid("sym", part["ref"])))
        for k, v in (("Sheetfile", f"{PROJECT}.kicad_sch"), ("Sheetname", ""), ("LCSC", part["lcsc"]),
                     ("MPN", part["mpn"]), ("Manufacturer", part["mfr"])):
            if v or k == "Sheetname":
                fp.SetProperty(k, v)
        if part["dnp"]:
            fp.SetProperty("DNP", "DNP")
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
        # Bo nhỏ, dày linh kiện: tham chiếu đặt ở lớp Fab (in bản vẽ lắp ráp), silk chỉ giữ chữ chức năng
        ref = fp.Reference()
        ref.SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5)))
        ref.SetTextThickness(MM(0.08))
        ref.SetLayer(pcbnew.B_Fab if side == "B" else pcbnew.F_Fab)
        val = fp.Value()
        val.SetTextSize(pcbnew.VECTOR2I(MM(0.4), MM(0.4)))
        val.SetTextThickness(MM(0.06))
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue
            netname = netmap.get((part["ref"], num))
            if netname:
                pad.SetNet(self.net(netname))
        self.b.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), True)   # phải Add vào board trước khi lật
        return fp

    # --- zone ------------------------------------------------------------
    def poly_zone(self, pts, layer_or_set, netname=None, name="", rule=None, priority=0):
        z = pcbnew.ZONE(self.b)
        if isinstance(layer_or_set, pcbnew.LSET):
            z.SetLayerSet(layer_or_set)
        else:
            z.SetLayer(layer_or_set)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            p = P(x, y)
            ol.Append(p.x, p.y)
        if rule:
            z.SetIsRuleArea(True)
            z.SetDoNotAllowCopperPour(True)
            z.SetDoNotAllowVias(rule.get("vias", True))
            z.SetDoNotAllowTracks(rule.get("tracks", False))
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(False)
        else:
            z.SetNet(self.net(netname))
            z.SetMinThickness(MM(0.2))
            z.SetLocalClearance(MM(0.25))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(MM(0.25))
            z.SetThermalReliefSpokeWidth(MM(0.25))
            z.SetAssignedPriority(priority)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        self.b.Add(z)
        return z

    def via(self, x, y, netname="GND"):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetWidth(MM(0.45))
        v.SetDrill(MM(0.25))
        v.SetNet(self.net(netname))
        self.b.Add(v)

    def text(self, s, x, y, size=0.8, layer=pcbnew.F_SilkS, mirror=False, angle=0.0):
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(size * 0.15))
        t.SetMirrored(mirror)
        t.SetTextAngleDegrees(angle)
        self.b.Add(t)


def circle_pts(r, n=72, a0=0.0, a1=2 * math.pi):
    return [(r * math.cos(a0 + (a1 - a0) * k / n), r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n)]


def build(kicad_dir: Path, netlist: str) -> Path:
    pcb_path = kicad_dir / f"{PROJECT}.kicad_pcb"
    pcb_path.write_text(PCB_TEMPLATE)
    board = pcbnew.LoadBoard(str(pcb_path))
    bld = Builder(board)
    bld.kicad_dir = kicad_dir
    netmap = read_netlist(netlist)
    for name in sorted(set(netmap.values())):
        bld.net(name)

    bld.outline()
    for part in D.PARTS:
        bld.footprint(part, netmap)

    R = D.BOARD_R
    full = circle_pts(R + 0.3)
    gnd = "GND"
    bld.poly_zone(full, pcbnew.F_Cu, gnd, "GND_F")
    bld.poly_zone(full, pcbnew.In1_Cu, gnd, "GND_In1")
    bld.poly_zone(full, pcbnew.In2_Cu, "VBAT", "VBAT_In2")
    bld.poly_zone(full, pcbnew.B_Cu, gnd, "GND_B")

    allcu = pcbnew.LSET()
    for lyr in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        allcu.AddLayer(lyr)
    # Vùng cấm đồng anten: đoạn tròn y < ANT_KEEPOUT_Y (cho phép đường feed, cấm via/đổ đồng)
    yk = D.ANT_KEEPOUT_Y
    rk = R + 0.5
    xk = math.sqrt(rk * rk - yk * yk)
    a0, a1 = math.atan2(yk, -xk), math.atan2(yk, xk)
    if a1 < a0:
        a1 += 2 * math.pi
    ant = [(-xk, yk)] + [(rk * math.cos(a0 + (a1 - a0) * k / 24), rk * math.sin(a0 + (a1 - a0) * k / 24))
                         for k in range(1, 24)] + [(xk, yk)]
    bld.poly_zone(ant, allcu, name="KEEPOUT_ANTENNA", rule={"vias": True, "tracks": False})
    # Vùng cấm đổ đồng/via trên lưỡi cảm biến (cách nhiệt)
    T = bld.tongue_T
    hw = D.TONGUE_HALF_W + D.SLOT_W
    tongue = [T(D.SLOT_INNER - 0.6, -hw), T(R + 0.6, -hw), T(R + 0.6, hw), T(D.SLOT_INNER - 0.6, hw)]
    bld.poly_zone(tongue, allcu, name="KEEPOUT_SENSOR_TONGUE", rule={"vias": True, "tracks": False})

    # Via khâu GND quanh mép bo (tránh anten, lưỡi, TC2030, pad kẹp pin) và dọc mép vùng cấm anten
    skip = [(-140, -50), (-60, -10), (205, 255), (-25, 40), (140, 205)]
    for deg in range(0, 360, 12):
        d = deg if deg <= 180 else deg - 360
        if any(lo <= d <= hi for lo, hi in skip) or any(lo <= deg <= hi for lo, hi in skip):
            continue
        r = 16.3
        bld.via(r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))
    for x in (-9.0, -7.5, -4.5, -3.0, 5.0, 6.5, 8.0, 9.5):   # bỏ x=-6 (trùng lỗ định vị TC2030)
        bld.via(x, yk + 0.55)

    # Chữ trên silk (chức năng pad test, cổng debug)
    for ref, label, dx, dy in (("TP1", "VBAT", 0, 1.3), ("TP2", "GND", 0, 1.3), ("TP3", "TX", 1.6, 0),
                               ("TP4", "RX", 1.6, 0), ("TP5", "PTI-D", 0, 1.3), ("TP6", "PTI-F", 0, 1.3)):
        part = next(p for p in D.PARTS if p["ref"] == ref)
        bld.text(label, part["pcb"][0] + dx, part["pcb"][1] + dy, 0.6)
    bld.text("SWD", -11.6, -6.9, 0.6, angle=35)
    bld.text("TSENSOR v0.1", 0.0, 13.2, 0.8)
    bld.text("MG24 Matter T/RH", 0.0, 14.4, 0.6)
    bld.text("CR2450 (+)", 0.0, -6.6, 1.0, pcbnew.B_SilkS, mirror=True)
    bld.text("ANT KEEPOUT", -6.0, -15.2, 0.5, pcbnew.Cmts_User)

    pcbnew.SaveBoard(str(pcb_path), board)
    return pcb_path


def drc(pcb_path: Path, report: Path) -> None:
    board = pcbnew.LoadBoard(str(pcb_path))
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    pcbnew.WriteDRCReport(board, str(report), pcbnew.EDA_UNITS_MILLIMETRES, True)


def main() -> None:
    kicad_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "hardware/kicad")
    netlist = sys.argv[2] if len(sys.argv) > 2 else str(kicad_dir / "build" / f"{PROJECT}.net")
    pcb = build(kicad_dir, netlist)
    report = kicad_dir / "build" / "drc_report.txt"
    drc(pcb, report)
    print(f"OK: {pcb}  (DRC: {report})")


if __name__ == "__main__":
    main()
