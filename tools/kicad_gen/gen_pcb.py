#!/usr/bin/env python3
"""
Sinh tsensor.kicad_pcb (KiCad 7) từ design.py + netlist do KiCad xuất từ schematic.
Chạy bằng Python có module pcbnew (cài KiCad):
    python3 tools/kicad_gen/gen_pcb.py hardware/kicad <tsensor.net>
Kết quả: bo Ø35 mm 4 lớp 0,8 mm, viền có lưỡi cảm biến (hướng 6 giờ), anten IFA đồng trên PCB
(mép trên, hướng 12 giờ), linh kiện đã đặt theo floorplan, net đã gán, zone GND (F.Cu, In1.Cu, B.Cu)
+ VBAT (In2.Cu), vùng cấm anten/lưỡi, via khâu GND (tự lọc theo pad, courtyard, vùng cấm, chữ silk).
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
        self.texts: list = []

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
        if part["dnp"] or part["virtual"]:   # virtual = anten đồng trên PCB, không phải linh kiện lắp ráp
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
        self.texts.append(t)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(size * 0.15))
        t.SetMirrored(mirror)
        t.SetTextAngleDegrees(angle)
        self.b.Add(t)

    # --- via khâu GND tự lọc ------------------------------------------------
    def stitch_vias(self, cands, via_d=0.45, clr=0.25, min_pitch=1.2):
        """Đặt via GND tại các điểm ứng viên không vướng: pad của mọi footprint, courtyard (trừ footprint
        ảo như anten PCB), đồng của anten, vùng cấm (rule area), chữ silk, mép bo. Trả về danh sách điểm đã đặt."""
        r = via_d / 2
        virtual_refs = {p["ref"] for p in D.PARTS if p["virtual"]}
        boxes, polys = [], []
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                boxes.append(box_mm(pad.GetBoundingBox()))
            if fp.GetReference() in virtual_refs:
                boxes += [box_mm(g.GetBoundingBox()) for g in fp.GraphicalItems() if g.IsOnLayer(pcbnew.F_Cu)]
                continue
            fp.BuildCourtyardCaches()
            for lyr in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                poly = fp.GetCourtyard(lyr)
                if poly.OutlineCount():
                    polys.append((poly, MM(r)))
        for z in self.b.Zones():
            if z.GetIsRuleArea():
                polys.append((z.Outline(), MM(r + 0.05)))
        boxes += [box_mm(t.GetBoundingBox()) for t in self.texts
                  if t.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
        placed = []
        for x, y in cands:
            if math.hypot(x, y) > D.BOARD_R - 0.5 - r:
                continue
            if any(box_dist(b, x, y) < r + clr for b in boxes):
                continue
            if any(poly.Collide(P(x, y), c) for poly, c in polys):
                continue
            if any(math.hypot(x - u, y - v) < min_pitch for u, v in placed):
                continue
            self.via(x, y)
            placed.append((x, y))
        return placed


def box_mm(bb) -> tuple:
    """BOX2I (toạ độ trang, nm) -> (x0, y0, x1, y1) mm so với tâm bo."""
    o, e = bb.GetOrigin(), bb.GetEnd()
    xs = sorted((pcbnew.ToMM(o.x) - OX, pcbnew.ToMM(e.x) - OX))
    ys = sorted((pcbnew.ToMM(o.y) - OY, pcbnew.ToMM(e.y) - OY))
    return xs[0], ys[0], xs[1], ys[1]


def box_dist(b, x, y) -> float:
    dx = max(b[0] - x, 0.0, x - b[2])
    dy = max(b[1] - y, 0.0, y - b[3])
    return math.hypot(dx, dy)


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
    # Vùng cấm anten PCB: đoạn tròn y < ANT_KEEPOUT_Y trên mọi lớp đồng (cấm đổ đồng, via và track).
    # Đồng của anten là hình vẽ trong footprint ANT1 nên không bị luật này chặn.
    yk = D.ANT_KEEPOUT_Y
    rk = R + 0.5
    xk = math.sqrt(rk * rk - yk * yk)
    a0, a1 = math.atan2(yk, -xk), math.atan2(yk, xk)
    if a1 < a0:
        a1 += 2 * math.pi
    ant = [(-xk, yk)] + [(rk * math.cos(a0 + (a1 - a0) * k / 24), rk * math.sin(a0 + (a1 - a0) * k / 24))
                         for k in range(1, 24)] + [(xk, yk)]
    bld.poly_zone(ant, allcu, name="KEEPOUT_ANTENNA", rule={"vias": True, "tracks": True})
    # Rãnh F.Cu quanh hai chân anten (feed + nối đất): không đổ GND mặt trên; chân đất nối In1/B.Cu qua via
    nx0, nx1 = D.ANT_LEG_NOTCH_X
    ny1 = yk + D.ANT_LEG_NOTCH_DEPTH
    bld.poly_zone([(nx0, yk - 0.2), (nx1, yk - 0.2), (nx1, ny1), (nx0, ny1)], pcbnew.F_Cu,
                  name="NOTCH_ANT_LEGS_FCU", rule={"vias": True, "tracks": False})
    # Vùng cấm đổ đồng/via trên lưỡi cảm biến (cách nhiệt); cho phép 4 đường tín hiệu
    T = bld.tongue_T
    hw = D.TONGUE_HALF_W + D.SLOT_W
    tongue = [T(D.SLOT_INNER - 0.6, -hw), T(R + 0.6, -hw), T(R + 0.6, hw), T(D.SLOT_INNER - 0.6, hw)]
    bld.poly_zone(tongue, allcu, name="KEEPOUT_SENSOR_TONGUE", rule={"vias": True, "tracks": False})

    # Chữ trên silk mặt trước: chức năng pad test, cổng debug, phiên bản
    pos = {p["ref"]: p["pcb"] for p in D.PARTS}
    for ref, label, dx, dy in (("TP1", "VBAT", 0, 1.3), ("TP2", "GND", 0, 1.3), ("TP3", "TX", 1.6, 0),
                               ("TP4", "RX", 1.6, 0), ("TP5", "PTI-D", 0, 1.3), ("TP6", "PTI-F", 0, 1.3)):
        bld.text(label, pos[ref][0] + dx, pos[ref][1] + dy, 0.6)
    bld.text("SWD", pos["J1"][0], pos["J1"][1] + 2.7, 0.6)      # ngay dưới courtyard TC2030
    bld.text("v0.1", 12.2, 9.0, 0.6)
    # Chữ mặt sau: dải trăng khuyết phía trên pin (sau lưng anten) — không bị pin che, không có đồng
    for txt, y, size in (("Temperature sensor", -14.7, 0.95), ("Design by Haxeko", -13.25, 0.8),
                         ("Made in Vietnam", -12.0, 0.8)):
        bld.text(txt, 0.0, y, size, pcbnew.B_SilkS, mirror=True)
    bld.text("ANT KEEPOUT", 4.0, -11.2, 0.5, pcbnew.Cmts_User)

    # Via khâu GND: ứng viên quanh mép bo (r = 16,3 mm, bước 10°) và dọc mép mặt đất của anten,
    # lọc tự động (tránh pad, courtyard, kẹp pin, lỗ TC2030, đồng anten, vùng cấm, chữ silk)
    cands = [(16.3 * math.cos(math.radians(d)), 16.3 * math.sin(math.radians(d))) for d in range(0, 360, 10)]
    cands += [(-15.0 + 1.5 * k, yk + 0.55) for k in range(21)]
    placed = bld.stitch_vias(cands)
    print(f"Via khâu GND: {len(placed)} via")

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
