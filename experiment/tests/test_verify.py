"""Tests for experiment.verify: every number recomputed from run files only.

Tests copy run files into tmp_path; the real folders under incidents/ are
only ever read.
"""
import json
import shutil
from pathlib import Path

from experiment import verify

REPO = Path(__file__).resolve().parents[2]


def copy_incident(tmp_path, incident, stamps=None):
    src = REPO / "incidents" / incident
    dst = tmp_path / incident
    dst.mkdir()
    shutil.copy(src / "incident.json", dst / "incident.json")
    runs = dst / "runs"
    runs.mkdir()
    for run_dir in sorted((src / "runs").iterdir()):
        if stamps and run_dir.name not in stamps:
            continue
        out = runs / run_dir.name
        out.mkdir()
        for name in ("result.json", "groundtruth.csv"):
            if (run_dir / name).exists():
                shutil.copy(run_dir / name, out / name)
    return dst


def run_verify(capsys, incident_dir):
    code = verify.main([str(incident_dir)])
    out = json.loads(capsys.readouterr().out)
    return code, out


def test_verify_matches_recorded_A_incident(tmp_path, capsys):
    incident_dir = copy_incident(tmp_path, "A-doorway")
    code, out = run_verify(capsys, incident_dir)
    assert code == 0
    assert out["incident"] == "A-doorway"
    assert len(out["runs"]) == 3
    assert out["mismatches"] == []
    for run in out["runs"]:
        assert run["kind"] == "valid"
        assert run["match"] is True
        assert run["recomputed"]["reached_goal"] == run["recorded"]["reached_goal"]
        assert run["recomputed"]["longest_still_ms"] == run["recorded"]["longest_still_ms"]


def test_verify_matches_recorded_B_incident(tmp_path, capsys):
    incident_dir = copy_incident(tmp_path, "B-drop-off")
    code, out = run_verify(capsys, incident_dir)
    assert code == 0
    assert len(out["runs"]) == 3
    assert all(r["recomputed"]["reached_goal"] is False for r in out["runs"])


def test_verify_reports_mismatch_and_exits_1(tmp_path, capsys):
    incident_dir = copy_incident(tmp_path, "A-doorway")
    run_dir = sorted((incident_dir / "runs").iterdir())[0]
    record = json.loads((run_dir / "result.json").read_text())
    record["observed"]["longest_still_ms"] += 1  # doctor the recorded value in the copy only
    (run_dir / "result.json").write_text(json.dumps(record))
    code, out = run_verify(capsys, incident_dir)
    assert code == 1
    assert out["mismatches"] == [run_dir.name]
    bad = [r for r in out["runs"] if r["run"] == run_dir.name][0]
    assert bad["match"] is False


def test_verify_ignores_folder_without_result_json(tmp_path, capsys):
    incident_dir = copy_incident(tmp_path, "A-doorway")
    (incident_dir / "runs" / "19990101-000000").mkdir()
    code, out = run_verify(capsys, incident_dir)
    assert code == 0
    incomplete = [r for r in out["runs"] if r["run"] == "19990101-000000"]
    assert incomplete[0]["kind"] == "incomplete"
    assert out["summary"]["runs_counted"] == 3


def test_verify_usage_error_exits_2(capsys):
    assert verify.main([]) == 2
    assert verify.main(["/no/such/incident"]) == 2
    capsys.readouterr()
