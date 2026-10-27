#!/usr/bin/env python3
"""Writes an incident's site map: Nav2's stock sandbox map with the incident's walls drawn in.

  python3 make_map.py ../incidents/A-doorway     # writes <incident>/deployed/map.pgm and map.yaml
"""
import json
import sys
from pathlib import Path

from sim_assets import draw_walls, parse_pgm, write_pgm

STOCK_MAP = Path("/opt/ros/jazzy/share/nav2_bringup/maps/tb3_sandbox.pgm")
RESOLUTION = 0.05          # from the stock tb3_sandbox.yaml
ORIGIN = (-10.0, -10.0)    # from the stock tb3_sandbox.yaml


def main(incident_dir):
    incident = json.loads((incident_dir / "incident.json").read_text())
    pixels, w, h = parse_pgm(STOCK_MAP.read_bytes())
    out = draw_walls(pixels, w, h, RESOLUTION, ORIGIN, incident["walls"])
    map_yaml = incident_dir / incident["deployed"]["map"]
    map_yaml.parent.mkdir(parents=True, exist_ok=True)
    map_yaml.with_suffix(".pgm").write_bytes(write_pgm(out, w, h))
    map_yaml.write_text(
        f"image: {map_yaml.with_suffix('.pgm').name}\n"
        f"resolution: {RESOLUTION:.6f}\n"
        f"origin: [{ORIGIN[0]:.6f}, {ORIGIN[1]:.6f}, 0.000000]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
    print(f"wrote {map_yaml} and {map_yaml.with_suffix('.pgm').name}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
