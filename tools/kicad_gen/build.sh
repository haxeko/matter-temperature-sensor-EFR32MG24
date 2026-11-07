#!/usr/bin/env bash
# Sinh lại toàn bộ project KiCad + kiểm tra. Cần KiCad 7.x (kicad-cli, module Python pcbnew).
#   tools/kicad_gen/build.sh [thư_mục_project]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/../../hardware/kicad}"
mkdir -p "$OUT/build" "$OUT/plots"
python3 "$HERE/gen_kicad.py" "$OUT"
kicad-cli sch export netlist --format kicadsexpr -o "$OUT/build/tsensor.net" "$OUT/tsensor.kicad_sch" >/dev/null
python3 "$HERE/verify_netlist.py" "$OUT/build/tsensor.net" "$OUT/build/expected_nets.json" "$OUT/tsensor.kicad_sch"
python3 "$HERE/gen_pcb.py" "$OUT" "$OUT/build/tsensor.net"
echo "--- DRC (ngoài 'unconnected_items' do chưa đi dây) ---"
grep "^\[" "$OUT/build/drc_report.txt" | sed 's/\].*/]/' | sort | uniq -c || true
kicad-cli sch export pdf -o "$OUT/plots/tsensor_schematic.pdf" "$OUT/tsensor.kicad_sch" >/dev/null
kicad-cli pcb export pos --format csv --units mm --side both -o "$OUT/build/cpl_positions.csv" "$OUT/tsensor.kicad_pcb" >/dev/null
kicad-cli pcb export svg -l F.Cu,F.SilkS,F.Fab,F.CrtYd,Edge.Cuts,Cmts.User --page-size-mode 2 --exclude-drawing-sheet \
  -o "$OUT/plots/pcb_front.svg" "$OUT/tsensor.kicad_pcb" >/dev/null
kicad-cli pcb export svg -l B.Cu,B.SilkS,B.Fab,B.CrtYd,Edge.Cuts --mirror --page-size-mode 2 --exclude-drawing-sheet \
  -o "$OUT/plots/pcb_back.svg" "$OUT/tsensor.kicad_pcb" >/dev/null
echo "Xong: $OUT"
