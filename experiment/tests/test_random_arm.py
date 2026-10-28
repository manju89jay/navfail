"""Tests for the random arm and the search loop (EXPERIMENT.md sections 6-7).

The simulator is faked here: run_one returns loaded-run dicts in the shape of
experiment.scoring.load_run. Real simulator runs are the G2 dry runs.
"""
from experiment.allowlist import SETTINGS, validate_candidate
from experiment.random_arm import RandomProposer
from experiment.search import run_search


def test_same_seed_draws_the_same_candidates():
    a, b = RandomProposer(7), RandomProposer(7)
    assert [a.propose([]) for _ in range(5)] == [b.propose([]) for _ in range(5)]


def test_different_seed_draws_different_candidates():
    a, b = RandomProposer(7), RandomProposer(8)
    assert [a.propose([]) for _ in range(3)] != [b.propose([]) for _ in range(3)]


def test_every_draw_is_inside_the_allowlist():
    proposer = RandomProposer(123)
    for _ in range(200):
        changes = proposer.propose([])["changes"]
        assert validate_candidate(changes) is changes or validate_candidate(changes) == changes
        assert 1 <= len(changes) <= 3
        for setting, value in changes.items():
            assert SETTINGS[setting]["min"] <= value <= SETTINGS[setting]["max"]


def test_draws_cover_all_six_settings_over_many_candidates():
    proposer = RandomProposer(99)
    seen = set()
    for _ in range(200):
        seen.update(proposer.propose([])["changes"])
    assert seen == set(SETTINGS)


# --- search loop with a fake simulator --------------------------------------

def fake_loaded(passed, kind="valid", reached=None):
    if kind != "valid":
        return {"run": "fake", "kind": kind, "score": None}
    return {"run": "fake", "kind": "valid", "score": {
        "reached_goal": passed if reached is None else reached,
        "longest_still_ms": 0, "min_wall_clearance_m": 1.0,
        "collided": False, "passed": passed}}


class ScriptedRuns:
    """run_one that returns scripted outcomes in call order (site and empty share the script)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, incident_dir, empty=False):
        self.calls.append(empty)
        return self.outcomes.pop(0)


class FixedProposer:
    def __init__(self, candidates):
        self.candidates = list(candidates)

    def propose(self, history):
        return self.candidates.pop(0) if self.candidates else None


CANDIDATE = {"changes": {"CostCritic.cost_weight": 3.81}, "reason": "test"}


def test_failed_screening_uses_one_run_and_moves_on(tmp_path):
    runs = ScriptedRuns([fake_loaded(False), fake_loaded(False)])
    result = run_search("t", tmp_path, FixedProposer([CANDIDATE, CANDIDATE]), runs, budget=40)
    assert result["runs_used"] == 2
    assert result["proven"] is False
    assert [c["status"] for c in result["candidates"]] == ["screening_failed", "screening_failed"]


def test_passing_candidate_runs_four_more_and_three_empty_then_stops(tmp_path):
    script = [fake_loaded(True)] * 5 + [fake_loaded(True)] * 3
    runs = ScriptedRuns(script)
    result = run_search("t", tmp_path, FixedProposer([CANDIDATE, CANDIDATE]), runs, budget=40)
    assert result["proven"] is True
    assert result["runs_used"] == 8
    assert runs.calls == [False] * 5 + [True] * 3
    assert len(result["candidates"]) == 1  # stops at the first proven fix


def test_budget_stops_the_search_and_counts_every_run(tmp_path):
    runs = ScriptedRuns([fake_loaded(False)] * 50)
    result = run_search("t", tmp_path, FixedProposer([CANDIDATE] * 50), runs, budget=6)
    assert result["runs_used"] == 6
    assert result["proven"] is False


def test_not_ready_run_counts_and_is_rerun_for_the_same_slot(tmp_path):
    script = [fake_loaded(None, kind="not_ready"), fake_loaded(False)]
    runs = ScriptedRuns(script)
    result = run_search("t", tmp_path, FixedProposer([CANDIDATE]), runs, budget=40)
    assert result["runs_used"] == 2
    assert result["candidates"][0]["status"] == "screening_failed"
    assert result["candidates"][0]["non_valid"] == ["not_ready"]


def test_invalid_candidate_counts_as_used_with_no_runs(tmp_path):
    bad = {"changes": {"CostCritic.cost_weight": 25.0}, "reason": "planted value"}
    runs = ScriptedRuns([])
    result = run_search("t", tmp_path, FixedProposer([bad]), runs, budget=40)
    assert result["runs_used"] == 0
    assert result["candidates"][0]["status"] == "invalid"
    assert runs.calls == []


def test_site_pass_but_empty_fail_is_not_proven(tmp_path):
    script = [fake_loaded(True)] * 5 + [fake_loaded(True), fake_loaded(True), fake_loaded(False, reached=False)]
    runs = ScriptedRuns(script)
    result = run_search("t", tmp_path, FixedProposer([CANDIDATE]), runs, budget=40)
    assert result["proven"] is False
    assert result["candidates"][0]["status"] == "not_proven"
    assert result["candidates"][0]["verdict"]["empty_passed"] == 2
