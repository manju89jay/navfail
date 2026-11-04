"""G2 dry-run driver (scratch): one seeded random search + one agent search
on synthetic incidents/C-corridor with the real simulator, budget 10 runs
each, candidate copies under experiment/work/. Run with ROS sourced."""
import json
import sys
from pathlib import Path

from experiment.agent_arm import AgentProposer
from experiment.random_arm import RandomProposer
from experiment.search import run_search
from experiment.simulator import prepare_candidate_incident, simulator_run_one

SOURCE = Path("incidents/C-corridor")
WORK = Path("experiment/work")
SEED = 20261028


def make_prepare(work):
    def prepare(index, changes, empty):
        return prepare_candidate_incident(
            SOURCE, work / f"cand-{index}-{'empty' if empty else 'site'}",
            changes, empty=empty)
    return prepare


def main():
    mode = sys.argv[1].strip()
    work = WORK / f"g2-{mode}"
    if mode == "random":
        proposer = RandomProposer(seed=SEED)
    else:
        proposer = AgentProposer(SOURCE)
    result = run_search(f"g2-{mode}", work, proposer, simulator_run_one(),
                        budget=10, prepare_candidate=make_prepare(work))
    print(json.dumps(result, indent=2))
    if mode == "agent":
        print("AGENT_USAGE:", proposer.usage)
        print("AGENT_EST_COST_USD:", round(proposer.estimated_cost_usd(), 6))


if __name__ == "__main__":
    main()
