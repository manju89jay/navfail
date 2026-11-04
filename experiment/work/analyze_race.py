"""S6 analysis (scratch): verify every race candidate folder from run files,
cross-check search.json run counts, compute medians and the section-7 verdict."""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiment.verify import verify_incident

RACE = Path("experiment/work/race")
ARMS = {"agent": [f"agent-{i}" for i in range(1, 6)],
        "random": [f"random-{i}" for i in range(1, 6)]}


def main():
    out = {"searches": {}, "verify_mismatches": [], "count_disagreements": []}
    for arm, names in ARMS.items():
        for name in names:
            work = RACE / name
            search = json.loads((work / "search.json").read_text())
            folder_runs = 0
            for cand in sorted(work.glob("cand-*")):
                if not cand.is_dir():
                    continue
                report = verify_incident(cand)
                folder_runs += report["summary"]["runs_counted"]
                if report["mismatches"]:
                    out["verify_mismatches"].append(
                        {"folder": str(cand), "runs": report["mismatches"]})
            agree = folder_runs == search["runs_used"]
            if not agree:
                out["count_disagreements"].append(
                    {"search": name, "search_json": search["runs_used"],
                     "folders": folder_runs})
            out["searches"][name] = {
                "proven": search["proven"], "runs_used": search["runs_used"],
                "runs_in_folders": folder_runs, "counts_agree": agree,
                "candidates": [
                    {"changes": c["changes"], "status": c["status"],
                     "non_valid": c["non_valid"],
                     "verdict": c["verdict"]}
                    for c in search["candidates"]]}
    medians, found = {}, {}
    for arm, names in ARMS.items():
        used = [out["searches"][n]["runs_used"] for n in names
                if out["searches"][n]["proven"]]
        found[arm] = len(used)
        medians[arm] = statistics.median(used) if used else None
    if found["agent"] < 3 or found["random"] < 3:
        verdict = "inconclusive"
    elif found["agent"] >= found["random"] and medians["agent"] < medians["random"]:
        verdict = "fewer"
    else:
        verdict = "not fewer"
    out["found"] = found
    out["medians"] = medians
    out["verdict"] = verdict
    out["agent_cost_usd"] = json.loads(
        (RACE / "race_state.json").read_text())["agent_cost_usd"]
    Path("experiment/work/race/analysis.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("found", "medians", "verdict", "agent_cost_usd",
                       "verify_mismatches", "count_disagreements")}, indent=2))
    for name in ARMS["agent"] + ARMS["random"]:
        s = out["searches"][name]
        print(name, "proven:", s["proven"], "runs:", s["runs_used"],
              "folders:", s["runs_in_folders"], "agree:", s["counts_agree"])


if __name__ == "__main__":
    main()
