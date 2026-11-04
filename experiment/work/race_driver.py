"""S5 race driver (scratch, EXPERIMENT.md section 7): 5 searches per arm,
interleaved agent/random, budget 40 runs per search, stops at the first
proven fix per search. Resumable: a search with a search.json on disk is
skipped. Cumulative agent spend is kept in race_state.json; the race stops
before a new agent search once spend reaches $90. Run with ROS sourced."""
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

SOURCE = Path("incidents/C-corridor")
RACE = Path("experiment/work/race")
SEED_BASE = 20261103
BUDGET = 40
SPEND_STOP_USD = 90.0


class ResilientAgent(AgentProposer):
    """Retry transient network failures instead of killing the search."""

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


def main():
    RACE.mkdir(parents=True, exist_ok=True)
    state_path = RACE / "race_state.json"
    state = (json.loads(state_path.read_text()) if state_path.exists()
             else {"agent_cost_usd": 0.0, "done": []})
    run_one = simulator_run_one()
    for i in range(1, 6):
        for arm in ("agent", "random"):
            name = f"{arm}-{i}"
            work = RACE / name
            if (work / "search.json").exists() or name in state["done"]:
                print(f"SKIP {name} (already done)", flush=True)
                continue
            if arm == "agent":
                if state["agent_cost_usd"] >= SPEND_STOP_USD:
                    print(f"STOP spend ${state['agent_cost_usd']:.2f} >= $90", flush=True)
                    return
                proposer = ResilientAgent(SOURCE)
            else:
                proposer = RandomProposer(seed=SEED_BASE + i)
            print(f"START {name}", flush=True)
            result = run_search(name, work, proposer, run_one, budget=BUDGET,
                                prepare_candidate=make_prepare(work))
            if arm == "agent":
                state["agent_cost_usd"] += proposer.estimated_cost_usd()
            state["done"].append(name)
            state_path.write_text(json.dumps(state, indent=2) + "\n")
            print(f"DONE {name} proven={result['proven']} runs={result['runs_used']} "
                  f"agent_spend=${state['agent_cost_usd']:.2f}", flush=True)
    print("RACE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
