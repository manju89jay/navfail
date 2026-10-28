"""Simulator bridge: candidate incident folders and one-run-at-a-time execution.

A candidate is a copy of the incident folder (never the original, never under
incidents/*/runs/) with the candidate's allowlisted changes written into its
deployed/nav2_params.yaml. Empty-site candidates additionally have no walls
and a map redrawn without them by the frozen reproduce/make_map.py.

reproduce.sh exit 2 means a simulator is already running: wait and retry the
launch, never kill anything (EXPERIMENT.md section 9 rule 2).
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from experiment.allowlist import SETTINGS, validate_candidate
from experiment.scoring import load_run

REPO = Path(__file__).resolve().parents[1]
WAIT_ON_BUSY_S = 20


def _set_path(params, path, value):
    node = params
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = float(value)


def prepare_candidate_incident(source_incident, dest, changes, empty=False):
    """Copy source_incident to dest with changes applied; returns dest. Source untouched."""
    validate_candidate(changes)
    source_incident, dest = Path(source_incident), Path(dest)
    if dest.exists():
        return dest  # already prepared for an earlier run of the same candidate
    (dest / "deployed").mkdir(parents=True)
    incident = json.loads((source_incident / "incident.json").read_text())
    if empty:
        incident["walls"] = []
    (dest / "incident.json").write_text(json.dumps(incident, indent=2) + "\n")
    for name in Path(source_incident, "deployed").iterdir():
        if name.is_file():
            shutil.copy(name, dest / "deployed" / name.name)
    params_path = dest / "deployed" / Path(incident["deployed"]["params"]).name
    params = yaml.safe_load(params_path.read_text())
    for setting, value in changes.items():
        for path in SETTINGS[setting]["paths"]:
            _set_path(params, path, value)
    params_path.write_text(yaml.safe_dump(params, sort_keys=False))
    if empty:
        subprocess.run(["python3", str(REPO / "reproduce" / "make_map.py"), str(dest)],
                       check=True, capture_output=True, text=True)
    return dest


def simulator_run_one(runner=subprocess.run, sleep=time.sleep):
    """Return run_one(incident_dir, empty=False) -> loaded run dict for the new run folder."""

    def run_one(incident_dir, empty=False):
        incident_dir = Path(incident_dir)
        runs_dir = incident_dir / "runs"
        before = {p.name for p in runs_dir.iterdir()} if runs_dir.exists() else set()
        while True:
            done = runner(["bash", str(REPO / "reproduce" / "reproduce.sh"), str(incident_dir)],
                          capture_output=True, text=True)
            if done.returncode == 2:
                sleep(WAIT_ON_BUSY_S)  # a simulator is already running: wait, never kill
                continue
            break
        after = sorted(p for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.exists() else []
        new = [p for p in after if p.name not in before]
        if not new:
            return {"run": None, "kind": "incomplete", "score": None}
        return load_run(incident_dir, new[-1])

    return run_one
