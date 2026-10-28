"""Tests for candidate-incident preparation and the simulator bridge.

No real simulator is started: the subprocess runner is faked. The real thing
is exercised only by the G2 dry runs.
"""
import json
from pathlib import Path

import yaml

from experiment.simulator import prepare_candidate_incident, simulator_run_one

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "incidents" / "C-corridor"  # synthetic failure F


def params_of(incident_dir):
    return yaml.safe_load((incident_dir / "deployed" / "nav2_params.yaml").read_text())


def test_prepare_applies_mppi_change_and_keeps_the_rest(tmp_path):
    dest = prepare_candidate_incident(
        SOURCE, tmp_path / "cand", {"CostCritic.cost_weight": 3.81})
    params = params_of(dest)
    follow = params["controller_server"]["ros__parameters"]["FollowPath"]
    assert follow["CostCritic"]["cost_weight"] == 3.81
    assert follow["PathAlignCritic"]["cost_weight"] == 14.0  # untouched
    assert json.loads((dest / "incident.json").read_text())["walls"] != []


def test_prepare_inflation_change_writes_both_costmaps(tmp_path):
    dest = prepare_candidate_incident(
        SOURCE, tmp_path / "cand",
        {"inflation_layer.inflation_radius": 0.5, "inflation_layer.cost_scaling_factor": 15.0})
    params = params_of(dest)
    for top in ("local_costmap", "global_costmap"):
        layer = params[top][top]["ros__parameters"]["inflation_layer"]
        assert layer["inflation_radius"] == 0.5
        assert layer["cost_scaling_factor"] == 15.0


def test_prepare_empty_site_has_no_walls(tmp_path):
    dest = prepare_candidate_incident(
        SOURCE, tmp_path / "cand", {"CostCritic.cost_weight": 3.81}, empty=True)
    incident = json.loads((dest / "incident.json").read_text())
    assert incident["walls"] == []
    assert incident["goal"] == json.loads((SOURCE / "incident.json").read_text())["goal"]


def test_prepare_never_touches_the_source_incident(tmp_path):
    before = (SOURCE / "deployed" / "nav2_params.yaml").read_bytes()
    prepare_candidate_incident(SOURCE, tmp_path / "cand", {"CostCritic.cost_weight": 1.0})
    assert (SOURCE / "deployed" / "nav2_params.yaml").read_bytes() == before
    assert not (tmp_path / "cand" / "runs").exists() or list((tmp_path / "cand" / "runs").iterdir()) == []


class FakeRunner:
    """Stands in for reproduce.sh: writes one run folder per call, or exit 2."""

    def __init__(self, exit_codes=(0,)):
        self.exit_codes = list(exit_codes)
        self.calls = 0

    def __call__(self, argv, **kwargs):
        code = self.exit_codes[min(self.calls, len(self.exit_codes) - 1)]
        self.calls += 1

        class Done:
            returncode = code

        if code == 2:
            return Done()
        incident_dir = Path(argv[-1])
        run_dir = incident_dir / "runs" / f"20260101-00000{self.calls}"
        run_dir.mkdir(parents=True)
        (run_dir / "result.json").write_text(json.dumps({"observed": {
            "nav2_result": "SUCCEEDED", "reached_goal": True, "longest_still_ms": 0}}))
        (run_dir / "groundtruth.csv").write_text(
            "t_ms,x,y,yaw\n0,-2.2,-0.55,0\n1000,2.0,0.5,0\n")
        return Done()


def test_simulator_run_one_waits_on_exit_2_and_loads_the_new_run(tmp_path):
    dest = prepare_candidate_incident(SOURCE, tmp_path / "cand", {"CostCritic.cost_weight": 3.81})
    runner = FakeRunner(exit_codes=(2, 2, 0))
    run_one = simulator_run_one(runner=runner, sleep=lambda s: None)
    loaded = run_one(dest, empty=False)
    assert runner.calls == 3  # exit 2 means wait, never kill, then retry
    assert loaded["kind"] == "valid"
    assert loaded["score"]["passed"] is True


def test_simulator_run_one_reports_incomplete_when_no_run_folder_appears(tmp_path):
    dest = prepare_candidate_incident(SOURCE, tmp_path / "cand", {"CostCritic.cost_weight": 3.81})

    def silent_runner(argv, **kwargs):
        class Done:
            returncode = 4
        return Done()

    loaded = simulator_run_one(runner=silent_runner, sleep=lambda s: None)(dest, empty=False)
    assert loaded["kind"] == "incomplete"
    assert loaded["score"] is None
