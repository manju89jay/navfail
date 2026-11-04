import json
import random
from pathlib import Path

SHORTLIST = [
    {"id": "navigation2#5884", "symptom": "planner fails to create plan through a 1.1 m narrow aisle (inflation_radius 0.9, large footprint); another planner succeeds",
     "url": "https://github.com/ros-navigation/navigation2/issues/5884"},
    {"id": "navigation2#5709", "symptom": "robot moves 10-20 cm then rotates left/right on the spot indefinitely, never reaches the goal",
     "url": "https://github.com/ros-navigation/navigation2/issues/5709"},
    {"id": "navigation2#4938", "symptom": "robot reaches the goal position but oscillates on final orientation and fails to make progress",
     "url": "https://github.com/ros-navigation/navigation2/issues/4938"},
]
SEED = 20261104

pick = random.Random(SEED).choice(SHORTLIST)
out = {"seed": SEED, "shortlist": SHORTLIST, "pick": pick}
dest = Path("experiment/work/warehouse/PICK.json")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(pick, indent=2))
