"""Baseline gate (scratch): F with its own deployed config, 10 valid runs.

Runs on a copy under experiment/work/baseline (never the original folder).
A non-valid run is recorded and rerun for the same slot (search.py rule);
10 consecutive non-valid runs abort.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiment.scoring import load_run
from experiment.simulator import simulator_run_one

SOURCE = Path("incidents/C-corridor")
DEST = Path("experiment/work/baseline")


def main():
    import shutil
    if not DEST.exists():
        DEST.mkdir(parents=True)
        shutil.copy(SOURCE / "incident.json", DEST / "incident.json")
        shutil.copytree(SOURCE / "deployed", DEST / "deployed")
        if (SOURCE / "SYNTHETIC.md").exists():
            shutil.copy(SOURCE / "SYNTHETIC.md", DEST / "SYNTHETIC.md")
    run_one = simulator_run_one()
    results, strikes = [], 0
    while len([r for r in results if r["kind"] == "valid"]) < 10:
        loaded = run_one(DEST, empty=False)
        results.append({"run": loaded.get("run"), "kind": loaded["kind"],
                        "passed": loaded["score"]["passed"] if loaded.get("score") else None,
                        "reached_goal": loaded["score"]["reached_goal"] if loaded.get("score") else None,
                        "longest_still_ms": loaded["score"]["longest_still_ms"] if loaded.get("score") else None})
        if loaded["kind"] != "valid":
            strikes += 1
            if strikes >= 10:
                raise RuntimeError("10 consecutive non-valid baseline runs")
        else:
            strikes = 0
        print(results[-1], flush=True)
    valid = [r for r in results if r["kind"] == "valid"]
    failures = sum(1 for r in valid if not r["passed"])
    out = {"valid_runs": len(valid), "failures": failures,
           "gate_passed": failures >= 8, "all": results}
    (DEST / "baseline.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
