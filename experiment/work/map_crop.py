import sys
from pathlib import Path

sys.path.insert(0, "reproduce")
from sim_assets import parse_pgm

pixels, w, h = parse_pgm(Path("incidents/W-warehouse/deployed/map.pgm").read_bytes())
RES, OX, OY = 0.05, -10.0, -10.0

def cell(x, y):
    col = int((x - OX) / RES)
    row = h - 1 - int((y - OY) / RES)
    return pixels[row * w + col]

for y in [1.2, 0.8, 0.4, 0.0, -0.4, -0.8, -1.2]:
    line = ""
    x = -3.0
    while x <= 3.0:
        v = cell(x, y)
        line += "#" if v < 50 else ("+" if v < 200 else ".")
        x += 0.1
    print(f"y={y:+.1f} {line}")
print("start cell:", cell(-2.2, 0.0), "goal cell:", cell(1.8, 0.0))
