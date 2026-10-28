"""Scoring for the navfail experiment (EXPERIMENT.md section 5, SPEC.md Plan).

Pure core: the same inputs give the same output. Times are integer milliseconds
of simulation time, distances are metres. Conventions mirror reproduce/observe.py
so a recomputed number can be compared with a recorded result.json.
"""
import csv
import json
import math
from pathlib import Path

GOAL_TOLERANCE_M = 0.25  # Nav2's stock xy_goal_tolerance (reproduce/observe.py)
STILL_RADIUS_M = 0.10    # staying within this distance of a window's start is "still"
STALL_LIMIT_MS = 15000   # a stall of 15.0 s or more fails a run (inclusive)
ROBOT_RADIUS_M = 0.22    # TurtleBot 3 Waffle footprint radius


def longest_still_ms(trace):
    """Longest window in which the trace stays within STILL_RADIUS_M of its start.

    trace: [(t_ms, x, y)] in time order. Same algorithm as reproduce/observe.py.
    """
    still_ms = 0
    for i, (ti, xi, yi) in enumerate(trace):
        end = ti
        for tj, xj, yj in trace[i + 1:]:
            if math.hypot(xj - xi, yj - yi) >= STILL_RADIUS_M:
                break
            end = tj
        if end - ti > still_ms:
            still_ms = end - ti
    return still_ms


def clearance_to_wall(x, y, wall):
    """Distance from a point to an axis-aligned wall rectangle; 0.0 inside or on it.

    Walls are {"cx", "cy", "sx", "sy"}: centre and size in metres
    (reproduce/sim_assets.py).
    """
    dx = max(abs(x - wall["cx"]) - wall["sx"] / 2.0, 0.0)
    dy = max(abs(y - wall["cy"]) - wall["sy"] / 2.0, 0.0)
    return math.hypot(dx, dy)


def min_wall_clearance(trace, walls):
    """Smallest clearance over the whole trace, or None when there is nothing to measure."""
    if not trace or not walls:
        return None
    return round(min(clearance_to_wall(x, y, w) for _, x, y in trace for w in walls), 3)


def score_run(nav2_result, trace, goal, walls=None):
    """Score one run against the proof rule's per-run conditions."""
    if trace:
        _, fx, fy = trace[-1]
        final_distance = math.hypot(fx - goal[0], fy - goal[1])
        reached = nav2_result == "SUCCEEDED" and final_distance <= GOAL_TOLERANCE_M
        still_ms = longest_still_ms(trace)
    else:
        final_distance = None
        reached = False
        still_ms = 0
    clearance = min_wall_clearance(trace, walls)
    collided = clearance is not None and clearance < ROBOT_RADIUS_M
    return {
        "nav2_result": nav2_result,
        "reached_goal": reached,
        "final_goal_distance_m": None if final_distance is None else round(final_distance, 3),
        "longest_still_ms": still_ms,
        "min_wall_clearance_m": clearance,
        "collided": collided,
        "passed": bool(reached and still_ms < STALL_LIMIT_MS and not collided),
    }


_KIND_BY_RESULT = {"NOT_READY": "not_ready", "NO_GOAL_REPLY": "no_goal_reply",
                   "RUNNER_ERROR": "runner_error"}


def load_run(incident_dir, run_dir):
    """Load and score one run folder. Read-only; never writes under incidents/*/runs/.

    Returns {"run": name, "kind": kind, "score": score-or-None}. A folder without
    result.json is "incomplete" (not a run). NOT_READY / NO_GOAL_REPLY / RUNNER_ERROR
    runs are classified and recorded, never scored as passes.
    """
    incident_dir, run_dir = Path(incident_dir), Path(run_dir)
    result_path = run_dir / "result.json"
    if not result_path.exists():
        return {"run": run_dir.name, "kind": "incomplete", "score": None}
    record = json.loads(result_path.read_text())
    nav2_result = record.get("observed", {}).get("nav2_result")
    if "error" in record:
        return {"run": run_dir.name, "kind": "runner_error", "score": None}
    if nav2_result in _KIND_BY_RESULT:
        return {"run": run_dir.name, "kind": _KIND_BY_RESULT[nav2_result], "score": None}
    incident = json.loads((incident_dir / "incident.json").read_text())
    goal = (incident["goal"]["x"], incident["goal"]["y"])
    trace = []
    with open(run_dir / "groundtruth.csv", newline="") as f:
        for row in csv.DictReader(f):
            trace.append((int(row["t_ms"]), float(row["x"]), float(row["y"])))
    score = score_run(nav2_result, trace, goal, walls=incident.get("walls") or [])
    return {"run": run_dir.name, "kind": "valid", "score": score}
