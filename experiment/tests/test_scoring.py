"""Tests for experiment.scoring: the proof rule (EXPERIMENT.md section 5).

One task at a time (SPEC.md Tasks): T1 covers the pure stall/goal logic.
Later tasks append their tests below; nothing here writes under incidents/.
"""
from experiment.scoring import score_run

GOAL = (2.0, 0.5)


def still_trace(duration_ms, step_ms=1000):
    """A trace that stays at the start point for duration_ms, then reaches the goal."""
    trace = [(t, -2.0, -0.5) for t in range(0, duration_ms + 1, step_ms)]
    trace.append((duration_ms + step_ms, 2.0, 0.5))
    return trace


def test_stall_of_exactly_15_0s_is_a_failure():
    score = score_run("SUCCEEDED", still_trace(15000), GOAL)
    assert score["longest_still_ms"] == 15000
    assert score["reached_goal"] is True
    assert score["passed"] is False


def test_stall_of_14_9s_is_not_a_failure():
    score = score_run("SUCCEEDED", still_trace(14900, step_ms=100), GOAL)
    assert score["longest_still_ms"] == 14900
    assert score["passed"] is True


def test_reached_requires_succeeded_and_within_goal_tolerance():
    at_goal = [(0, -2.0, -0.5), (1000, 2.0, 0.5)]
    assert score_run("SUCCEEDED", at_goal, GOAL)["reached_goal"] is True
    # exactly at the 0.25 m tolerance still counts as reached
    at_edge = [(0, -2.0, -0.5), (1000, 1.75, 0.5)]
    assert score_run("SUCCEEDED", at_edge, GOAL)["reached_goal"] is True
    far = [(0, -2.0, -0.5), (1000, 1.0, 0.5)]
    assert score_run("SUCCEEDED", far, GOAL)["reached_goal"] is False
    assert score_run("CANCELED", at_goal, GOAL)["reached_goal"] is False
    assert score_run("ABORTED", at_goal, GOAL)["reached_goal"] is False


def test_pass_requires_reached_no_stall_no_collision():
    clean = [(0, -2.0, -0.5), (5000, 0.0, 0.0), (9000, 2.0, 0.5)]
    assert score_run("SUCCEEDED", clean, GOAL)["passed"] is True
    not_reached = [(0, -2.0, -0.5), (5000, 0.0, 0.0)]
    assert score_run("SUCCEEDED", not_reached, GOAL)["passed"] is False
    empty = score_run("NOT_READY", [], GOAL)
    assert empty["reached_goal"] is False
    assert empty["longest_still_ms"] == 0
    assert empty["passed"] is False
