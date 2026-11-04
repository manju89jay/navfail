import sys
from pathlib import Path

sys.path.insert(0, "reproduce")
from sim_assets import parse_pgm

pixels, w, h = parse_pgm(Path("/opt/ros/jazzy/share/nav2_bringup/maps/tb3_sandbox.pgm").read_bytes())
RES, OX, OY = 0.05, -10.0, -10.0

def cell(x, y):
    col = int((x - OX) / RES)
    row = h - 1 - int((y - OY) / RES)
    return pixels[row * w + col]

for y in [0.5, 0.0, -0.55, -1.1]:
    line = ""
    x = -3.0
    while x <= 3.0:
        v = cell(x, y)
        line += "#" if v < 50 else ("+" if v < 200 else ".")
        x += 0.1
    print(f"y={y:+.2f} {line}")
