"""Warehouse test driver (scratch, SPEC-SANDBOX-TEST.md).

Modes: baseline (5 runs of the deployed config on a copy, gate >=4 failures),
agent / random (one 40-run search each on candidate copies).
Run with ROS sourced."""
import json
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiment.agent_arm import AgentProposer
from experiment.random_arm import RandomProposer
from experiment.search import run_search
from experiment.simulator import prepare_candidate_incident, simulator_run_one

SOURCE = Path("incidents/W-warehouse")
WORK = Path("experiment/work/warehouse")


class ResilientAgent(AgentProposer):
    def propose(self, history):
        for attempt in range(10):
            try:
                return super().propose(history)
            except urllib.error.URLError:
                if attempt == 9:
                    raise
                print("network unreachable, waiting 60 s", flush=True)
                time.sleep(60)


def make_prepare(work):
    def prepare(index, changes, empty):
        return prepare_candidate_incident(
            SOURCE, work / f"cand-{index}-{'empty' if empty else 'site'}",
            changes, empty=empty)
    return prepare


def baseline():
    import shutil
    dest = WORK / "baseline"
    if not dest.exists():
        dest.mkdir(parents=True)
        shutil.copy(SOURCE / "incident.json", dest / "incident.json")
        shutil.copytree(SOURCE / "deployed", dest / "deployed")
        shutil.copy(SOURCE / "SOURCE.md", dest / "SOURCE.md")
    run_one = simulator_run_one()
    results, strikes = [], 0
    while len([r for r in results if r["kind"] == "valid"]) < 5:
        loaded = run_one(dest, empty=False)
        row = {"run": loaded.get("run"), "kind": loaded["kind"],
               "passed": loaded["score"]["passed"] if loaded.get("score") else None,
               "reached_goal": loaded["score"]["reached_goal"] if loaded.get("score") else None,
               "longest_still_ms": loaded["score"]["longest_still_ms"] if loaded.get("score") else None}
        results.append(row)
        print(row, flush=True)
        if loaded["kind"] != "valid":
            strikes += 1
            if strikes >= 10:
                raise RuntimeError("10 consecutive non-valid baseline runs")
        else:
            strikes = 0
    valid = [r for r in results if r["kind"] == "valid"]
    failures = sum(1 for r in valid if not r["passed"])
    out = {"valid_runs": len(valid), "failures": failures,
           "gate_passed": failures >= 4, "all": results}
    (dest / "baseline.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2), flush=True)


def search(mode):
    work = WORK / f"search-{mode}"
    proposer = (ResilientAgent(SOURCE) if mode == "agent"
                else RandomProposer(seed=20261104))
    result = run_search(f"warehouse-{mode}", work, proposer, simulator_run_one(),
                        budget=40, prepare_candidate=make_prepare(work))
    print(json.dumps(result, indent=2), flush=True)
    if mode == "agent":
        print("AGENT_USAGE:", proposer.usage, flush=True)
        print("AGENT_EST_COST_USD:", round(proposer.estimated_cost_usd(), 6), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1].strip()
    baseline() if mode == "baseline" else search(mode)
