#!/usr/bin/env python3
"""
Đối chiếu netlist do KiCad xuất (kicad-cli sch export netlist --format kicadsexpr) với design.py.
Thay cho ERC dòng lệnh (KiCad 7 chưa có `kicad-cli sch erc`):
  - mọi chân có net phải nằm đúng net mong đợi;
  - chân NC phải nằm ở net "unconnected-…" một mình;
  - không có net (trừ unconnected) chỉ có 1 chân;
  - schematic có PWR_FLAG cho VBAT, VDCDC, GND.
Dùng: python3 verify_netlist.py <tsensor.net> <expected_nets.json> [tsensor.kicad_sch]
"""
import json
import re
import sys
from collections import defaultdict

NET_RE = re.compile(r'\(net \(code "(\d+)"\) \(name "((?:[^"\\]|\\.)*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', re.S)
NODE_RE = re.compile(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)')


def main() -> int:
    net_text = open(sys.argv[1], encoding="utf-8").read()
    expected = json.load(open(sys.argv[2], encoding="utf-8"))
    nets_part = net_text[net_text.index("(nets"):]
    actual = {}
    members = defaultdict(list)
    for m in NET_RE.finditer(nets_part):
        name = m.group(2)
        for ref, pin in NODE_RE.findall(m.group(3)):
            actual[f"{ref}.{pin}"] = name
            members[name].append(f"{ref}.{pin}")
    errors = []
    for key, exp in expected.items():
        got = actual.get(key)
        if exp is None:
            if got is None or not got.startswith("unconnected-") or len(members[got]) != 1:
                errors.append(f"{key}: mong đợi NC, thực tế {got} ({members.get(got)})")
            continue
        norm = got.lstrip("/") if got else None
        if norm != exp:
            errors.append(f"{key}: mong đợi {exp}, thực tế {got}")
    for key in actual:
        ref = key.split(".")[0]
        if key not in expected and not ref.startswith("#"):
            errors.append(f"{key}: chân không có trong design ({actual[key]})")
    for name, pins in members.items():
        real = [p for p in pins if not p.startswith("#")]
        if not name.startswith("unconnected-") and len(real) < 2:
            errors.append(f"net {name} chỉ có {real}")
    if len(sys.argv) > 3:  # netlist không chứa ký hiệu nguồn -> kiểm PWR_FLAG trong file schematic
        sch = open(sys.argv[3], encoding="utf-8").read()
        n_flags = sch.count('(lib_id "power:PWR_FLAG")')
        if n_flags < 3:
            errors.append(f"chỉ có {n_flags} PWR_FLAG (cần cho VBAT, VDCDC, GND)")
    n_nets = sum(1 for n in members if not n.startswith("unconnected-"))
    print(f"netlist: {n_nets} net, {len(actual)} chân (kể cả ký hiệu nguồn), "
          f"{sum(1 for v in expected.values() if v is None)} chân NC")
    for e in errors:
        print("  LỖI", e)
    print("KẾT QUẢ:", "ĐẠT" if not errors else f"{len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
