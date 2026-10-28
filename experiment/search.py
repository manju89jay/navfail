"""The search loop shared by both arms (EXPERIMENT.md sections 5-7).

One search: proposals from a proposer, each validated against the allowlist
before any run, evaluated in the frozen order (1 screening run; only if it
passes, 4 more site runs and 3 empty-site runs), stopping at the first proven
fix or at the run budget. Every run the simulator produces counts, screening
and not-ready runs included. A non-valid run (not ready, no goal reply,
runner error) is recorded and rerun for the same slot; it is never retried
to get a better valid result, and a valid result is never rerun.

run_one(incident_dir, empty=False) -> loaded run dict (scoring.load_run shape)
is injected, so the loop is testable without a simulator. The real
simulator-backed run_one lives in experiment/simulator.py.
"""
import json
from pathlib import Path

from experiment.allowlist import validate_candidate
from experiment.scoring import evaluate_candidate

MAX_CONSECUTIVE_NON_VALID = 10


def run_search(name, work_dir, proposer, run_one, budget=40, prepare_candidate=None):
    """prepare_candidate(index, changes, empty) -> incident dir for that run, if given."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    history, candidates = [], []
    runs_used = 0
    proven = False

    def take_valid(empty, record, index):
        """Run until a valid run lands (rerunning non-valid ones) or budget/abort."""
        nonlocal runs_used
        strikes = 0
        while runs_used < budget:
            target = (prepare_candidate(index, record["changes"], empty)
                      if prepare_candidate else work_dir)
            loaded = run_one(target, empty=empty)
            if loaded["kind"] == "incomplete":
                strikes += 1
                record["non_valid"].append("incomplete")
                if strikes >= MAX_CONSECUTIVE_NON_VALID:
                    raise RuntimeError("simulator produced no result.json 10 times in a row")
                continue
            runs_used += 1
            if loaded["kind"] != "valid":
                strikes += 1
                record["non_valid"].append(loaded["kind"])
                if strikes >= MAX_CONSECUTIVE_NON_VALID:
                    raise RuntimeError("too many consecutive non-valid runs")
                continue
            return loaded
        return None

    while runs_used < budget and not proven:
        proposal = proposer.propose(history)
        if proposal is None:
            break
        record = {"changes": proposal.get("changes"), "reason": proposal.get("reason", ""),
                  "status": None, "non_valid": [], "verdict": None}
        candidates.append(record)
        try:
            validate_candidate(proposal.get("changes"))
        except ValueError as e:
            record["status"] = "invalid"
            record["error"] = str(e)
            history.append({"changes": proposal.get("changes"), "status": "invalid", "runs": 0})
            continue

        site_runs, empty_runs = [], []
        screening = take_valid(False, record, len(candidates))
        if screening is None:
            record["status"] = "budget_exhausted"
            break
        site_runs.append(screening)
        if not screening["score"]["passed"]:
            record["status"] = "screening_failed"
            record["verdict"] = evaluate_candidate(site_runs, empty_runs)
            history.append({"changes": record["changes"], "status": record["status"],
                            "runs": 1, "site_passed": 0})
            continue
        while len(site_runs) < 5:
            nxt = take_valid(False, record, len(candidates))
            if nxt is None:
                break
            site_runs.append(nxt)
        if len(site_runs) == 5:
            site_only = evaluate_candidate(site_runs, [])
            if site_only["site_passed"] >= 4 and site_only["collisions"] == 0:
                while len(empty_runs) < 3:
                    nxt = take_valid(True, record, len(candidates))
                    if nxt is None:
                        break
                    empty_runs.append(nxt)
        verdict = evaluate_candidate(site_runs, empty_runs)
        record["verdict"] = verdict
        record["status"] = "proven" if verdict["proven"] else "not_proven"
        proven = verdict["proven"]
        history.append({"changes": record["changes"], "status": record["status"],
                        "runs": verdict["runs_counted"], "site_passed": verdict["site_passed"],
                        "empty_passed": verdict["empty_passed"]})

    result = {"search": name, "proven": proven, "runs_used": runs_used,
              "budget": budget, "candidates": candidates}
    (work_dir / "search.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
