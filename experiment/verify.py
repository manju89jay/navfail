#!/usr/bin/env python3
"""Recompute every reported number from run files only (SPEC check 6).

Usage: python3 -m experiment.verify <incident folder>
Prints JSON: per run, the values recomputed from groundtruth.csv next to the
values recorded in result.json, and whether they match. Exit 0 when every
valid run matches, 1 on any mismatch, 2 on usage error. Read-only.
"""
import json
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a plain script: experiment/verify.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment.scoring import load_run, runs_counted
else:
    from experiment.scoring import load_run, runs_counted


def verify_incident(incident_dir):
    incident_dir = Path(incident_dir)
    incident = json.loads((incident_dir / "incident.json").read_text())
    runs_dir = incident_dir / "runs"
    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.exists() else []
    runs, mismatches = [], []
    for run_dir in run_dirs:
        loaded = load_run(incident_dir, run_dir)
        entry = {"run": loaded["run"], "kind": loaded["kind"],
                 "recomputed": None, "recorded": None, "match": None}
        if loaded["kind"] == "valid":
            record = json.loads((run_dir / "result.json").read_text())
            recorded = record["observed"]
            entry["recomputed"] = {
                "reached_goal": loaded["score"]["reached_goal"],
                "longest_still_ms": loaded["score"]["longest_still_ms"],
                "min_wall_clearance_m": loaded["score"]["min_wall_clearance_m"],
                "collided": loaded["score"]["collided"],
                "passed": loaded["score"]["passed"],
            }
            entry["recorded"] = {
                "reached_goal": recorded["reached_goal"],
                "longest_still_ms": recorded["longest_still_ms"],
            }
            entry["match"] = (
                entry["recomputed"]["reached_goal"] == entry["recorded"]["reached_goal"]
                and entry["recomputed"]["longest_still_ms"] == entry["recorded"]["longest_still_ms"])
            if not entry["match"]:
                mismatches.append(loaded["run"])
        runs.append(entry)
    loaded_runs = [load_run(incident_dir, p) for p in run_dirs]
    return {
        "incident": incident["id"],
        "label": "synthetic" if (incident_dir / "SYNTHETIC.md").exists() else "recorded",
        "runs": runs,
        "mismatches": mismatches,
        "summary": {
            "runs_counted": runs_counted(loaded_runs),
            "valid": sum(1 for r in runs if r["kind"] == "valid"),
            "passed": sum(1 for r in runs if r["recomputed"] and r["recomputed"]["passed"]),
        },
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or not (Path(argv[0]) / "incident.json").exists():
        print("usage: verify.py <incident folder>", file=sys.stderr)
        return 2
    report = verify_incident(argv[0])
    print(json.dumps(report, indent=2))
    return 1 if report["mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
