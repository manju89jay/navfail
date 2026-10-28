"""Scoring for the navfail experiment (EXPERIMENT.md section 5, SPEC.md Plan).

Pure core: the same inputs give the same output. Times are integer milliseconds
of simulation time, distances are metres. Conventions mirror reproduce/observe.py
so a recomputed number can be compared with a recorded result.json.
"""
import math

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


def score_run(nav2_result, trace, goal, walls=None):
    """Score one run. walls is accepted for the T2 collision check; None = no walls."""
    if trace:
        _, fx, fy = trace[-1]
        final_distance = math.hypot(fx - goal[0], fy - goal[1])
        reached = nav2_result == "SUCCEEDED" and final_distance <= GOAL_TOLERANCE_M
        still_ms = longest_still_ms(trace)
    else:
        final_distance = None
        reached = False
        still_ms = 0
    collided = False
    return {
        "nav2_result": nav2_result,
        "reached_goal": reached,
        "final_goal_distance_m": None if final_distance is None else round(final_distance, 3),
        "longest_still_ms": still_ms,
        "min_wall_clearance_m": None,
        "collided": collided,
        "passed": bool(reached and still_ms < STALL_LIMIT_MS and not collided),
    }
