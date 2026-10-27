"""What an operator would see, computed from the true robot position and the Nav2 result.

Pure: the same inputs give the same output. Times are integer milliseconds of simulation time.
"""
import math

GOAL_TOLERANCE_M = 0.25  # Nav2's stock xy_goal_tolerance
STILL_RADIUS_M = 0.10    # "standing still" means staying within this distance of where the window began


def observe(nav_result, trace, goal):
    """nav_result: Nav2's final status name. trace: [(t_ms, x, y)] in time order. goal: (x, y)."""
    if not trace:
        return {"nav2_result": nav_result, "reached_goal": False, "final_goal_distance_m": None,
                "longest_still_ms": 0, "longest_still_at": None, "duration_ms": 0}
    _, fx, fy = trace[-1]
    dist = math.hypot(fx - goal[0], fy - goal[1])
    still_ms, still_at = 0, None
    for i, (ti, xi, yi) in enumerate(trace):
        end = ti
        for tj, xj, yj in trace[i + 1:]:
            if math.hypot(xj - xi, yj - yi) >= STILL_RADIUS_M:
                break
            end = tj
        if end - ti > still_ms:
            still_ms, still_at = end - ti, [round(xi, 2), round(yi, 2)]
    return {
        "nav2_result": nav_result,
        "reached_goal": nav_result == "SUCCEEDED" and dist <= GOAL_TOLERANCE_M,
        "final_goal_distance_m": round(dist, 3),
        "longest_still_ms": still_ms,
        "longest_still_at": still_at,
        "duration_ms": trace[-1][0] - trace[0][0],
    }
