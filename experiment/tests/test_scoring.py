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


# --- T2: collision check vs groundtruth + walls -----------------------------

WALL = {"cx": 0.0, "cy": 0.0, "sx": 2.0, "sy": 2.0}  # rectangle x,y in [-1, 1]


def run_along_y(points):
    return score_run("SUCCEEDED", [(k * 1000, x, y) for k, (x, y) in enumerate(points)], GOAL, walls=[WALL])


def test_collision_when_clearance_below_robot_radius():
    score = run_along_y([(-2.0, -0.5), (1.10, 0.0), (2.0, 0.5)])  # 0.10 m from the wall face
    assert score["min_wall_clearance_m"] == 0.10
    assert score["collided"] is True
    assert score["passed"] is False


def test_no_collision_at_exactly_robot_radius():
    score = run_along_y([(-2.0, -0.5), (1.22, 0.0), (2.0, 0.5)])  # exactly 0.22 m: tangent, not overlap
    assert score["min_wall_clearance_m"] == 0.22
    assert score["collided"] is False


def test_trace_inside_wall_collides():
    score = run_along_y([(-2.0, -0.5), (0.0, 0.0), (2.0, 0.5)])
    assert score["min_wall_clearance_m"] == 0.0
    assert score["collided"] is True


def test_no_walls_never_collides():
    trace = [(0, -2.0, -0.5), (1000, 0.0, 0.0), (2000, 2.0, 0.5)]
    for walls in (None, []):
        score = score_run("SUCCEEDED", trace, GOAL, walls=walls)
        assert score["min_wall_clearance_m"] is None
        assert score["collided"] is False


def test_clearance_uses_nearest_wall():
    far_wall = {"cx": 10.0, "cy": 10.0, "sx": 2.0, "sy": 2.0}  # corner at (9, 9)
    trace = [(0, -2.0, -0.5), (1000, 2.0, 0.5)]
    score = score_run("SUCCEEDED", trace, GOAL, walls=[WALL, far_wall])
    # nearest approach is the first point (-2.0, -0.5), 1.0 m from WALL's left face
    assert score["min_wall_clearance_m"] == 1.0
    assert score["collided"] is False


# --- T3: run-file loader against the recorded A/B/C runs (read-only) --------

import json
from pathlib import Path

from experiment.scoring import load_run

REPO = Path(__file__).resolve().parents[2]


def recorded(run_dir):
    return json.loads((run_dir / "result.json").read_text())["observed"]


def run_dirs(incident):
    return sorted((REPO / "incidents" / incident / "runs").iterdir())


def test_recorded_A_runs_recompute_to_recorded_result_json():
    incident_dir = REPO / "incidents" / "A-doorway"
    dirs = run_dirs("A-doorway")
    assert len(dirs) == 3
    for run_dir in dirs:
        loaded = load_run(incident_dir, run_dir)
        assert loaded["kind"] == "valid"
        want = recorded(run_dir)
        assert loaded["score"]["reached_goal"] == want["reached_goal"]
        assert loaded["score"]["longest_still_ms"] == want["longest_still_ms"]


def test_recorded_B_runs_all_fail_the_proof_scoring():
    incident_dir = REPO / "incidents" / "B-drop-off"
    dirs = run_dirs("B-drop-off")
    assert len(dirs) == 3
    for run_dir in dirs:
        loaded = load_run(incident_dir, run_dir)
        assert loaded["kind"] == "valid"
        assert loaded["score"]["reached_goal"] is False
        assert loaded["score"]["passed"] is False


def test_recorded_C_runs_recompute_and_not_ready_is_classified():
    incident_dir = REPO / "incidents" / "C-corridor"
    kinds = {}
    for run_dir in run_dirs("C-corridor"):
        loaded = load_run(incident_dir, run_dir)
        kinds[run_dir.name] = loaded["kind"]
        if loaded["kind"] == "valid":
            want = recorded(run_dir)
            assert loaded["score"]["reached_goal"] == want["reached_goal"]
            assert loaded["score"]["longest_still_ms"] == want["longest_still_ms"]
            assert loaded["score"]["collided"] is False  # lab: never closer than 0.30 m to a wall
    # the recorded start-up failure is present and classified, never scored as a pass
    assert "not_ready" in kinds.values()
    for run_dir in run_dirs("C-corridor"):
        loaded = load_run(incident_dir, run_dir)
        if loaded["kind"] == "not_ready":
            assert loaded["score"] is None


def test_folder_without_result_json_is_incomplete(tmp_path):
    run_dir = tmp_path / "20260101-000000"
    run_dir.mkdir()
    loaded = load_run(REPO / "incidents" / "A-doorway", run_dir)
    assert loaded["kind"] == "incomplete"
    assert loaded["score"] is None


# --- T4: candidate verdict, run counting, allowlist -------------------------

import pytest

from experiment.allowlist import validate_candidate
from experiment.scoring import evaluate_candidate, runs_counted


def fake_run(passed=True, collided=False, reached=True, kind="valid"):
    if kind != "valid":
        return {"run": "x", "kind": kind, "score": None}
    return {"run": "x", "kind": "valid", "score": {
        "reached_goal": reached, "longest_still_ms": 0, "collided": collided,
        "passed": passed}}


def site(n_pass, extra=None):
    runs = [fake_run(passed=True) for _ in range(n_pass)]
    runs += [fake_run(passed=False, reached=False) for _ in range(5 - n_pass)]
    return runs + (extra or [])


EMPTY_OK = [fake_run() for _ in range(3)]


def test_proven_needs_four_of_five_site_passes():
    assert evaluate_candidate(site(4), EMPTY_OK)["proven"] is True
    assert evaluate_candidate(site(5), EMPTY_OK)["proven"] is True


def test_three_of_five_is_not_proven():
    verdict = evaluate_candidate(site(3), EMPTY_OK)
    assert verdict["proven"] is False
    assert verdict["site_passed"] == 3


def test_any_collision_voids_proof():
    runs = site(5)
    runs[4] = fake_run(passed=False, collided=True)
    verdict = evaluate_candidate(runs, EMPTY_OK)
    assert verdict["proven"] is False
    assert verdict["collisions"] == 1


def test_proven_needs_three_of_three_empty_site():
    empty_bad = [fake_run(), fake_run(), fake_run(passed=False, reached=False)]
    assert evaluate_candidate(site(5), empty_bad)["proven"] is False
    assert evaluate_candidate(site(5), EMPTY_OK[:2])["proven"] is False


def test_fewer_than_five_valid_site_runs_is_not_proven():
    runs = [fake_run() for _ in range(4)] + [fake_run(kind="not_ready")]
    assert evaluate_candidate(runs, EMPTY_OK)["proven"] is False


def test_every_result_json_counts_toward_budget_including_screening_and_not_ready():
    loaded = [fake_run(), fake_run(kind="not_ready"), fake_run(kind="no_goal_reply"),
              fake_run(kind="runner_error"), fake_run(kind="incomplete")]
    assert runs_counted(loaded) == 4


def test_incomplete_folder_counts_zero():
    assert runs_counted([fake_run(kind="incomplete")]) == 0
    assert runs_counted([]) == 0


def test_candidate_outside_allowlist_rejected_before_any_run():
    # the planted synthetic value itself is outside the allowlist
    with pytest.raises(ValueError):
        validate_candidate({"CostCritic.cost_weight": 25.0})
    with pytest.raises(ValueError):
        validate_candidate({"CostCritic.cost_weight": 0.5})
    with pytest.raises(ValueError):
        validate_candidate({"inflation_layer.inflation_radius": 1.01})


def test_allowlist_boundaries_are_inclusive_and_size_is_one_to_three():
    assert validate_candidate({"CostCritic.cost_weight": 1.0}) == {"CostCritic.cost_weight": 1.0}
    assert validate_candidate({"CostCritic.cost_weight": 10.0}) == {"CostCritic.cost_weight": 10.0}
    three = {"CostCritic.cost_weight": 3.81, "inflation_layer.cost_scaling_factor": 15.0,
             "PreferForwardCritic.cost_weight": 0.0}
    assert validate_candidate(three) == three
    with pytest.raises(ValueError):
        validate_candidate({})
    with pytest.raises(ValueError):
        validate_candidate({**three, "PathFollowCritic.cost_weight": 5.0})
    with pytest.raises(ValueError):
        validate_candidate({"no_such_setting": 1.0})
    with pytest.raises(ValueError):
        validate_candidate({"CostCritic.cost_weight": True})
    with pytest.raises(ValueError):
        validate_candidate({"CostCritic.cost_weight": "3.81"})
