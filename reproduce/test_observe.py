"""Tests for observe: what an operator would see, computed from the true robot position and the Nav2 result."""
from observe import observe

GOAL = (2.0, 0.5)


def test_reached_when_succeeded_and_near_the_goal():
    trace = [(0, -2.0, -0.5), (30000, 1.9, 0.5)]
    o = observe("SUCCEEDED", trace, GOAL)
    assert o["reached_goal"] is True
    assert o["final_goal_distance_m"] == 0.1


def test_not_reached_when_succeeded_but_far():
    trace = [(0, -2.0, -0.5), (30000, 1.0, 0.5)]
    assert observe("SUCCEEDED", trace, GOAL)["reached_goal"] is False


def test_not_reached_when_nav2_did_not_succeed():
    trace = [(0, -2.0, -0.5), (30000, 2.0, 0.5)]
    assert observe("CANCELED", trace, GOAL)["reached_goal"] is False


def test_longest_still_window_and_where():
    trace = [(0, -2.0, -0.5), (5000, -1.0, -0.5)]
    trace += [(5000 + k * 1000, -1.0 + 0.002 * (k % 2), -0.5) for k in range(1, 21)]
    trace += [(30000, 0.0, 0.0)]
    o = observe("CANCELED", trace, GOAL)
    assert o["longest_still_ms"] == 20000
    assert o["longest_still_at"] == [-1.0, -0.5]


def test_empty_trace():
    o = observe("UNKNOWN", [], GOAL)
    assert o["reached_goal"] is False
    assert o["longest_still_ms"] == 0
    assert o["final_goal_distance_m"] is None
