# Experiment: does reading the logs help find a proven fix with fewer simulator runs?

DRAFT, 28 October 2026, for the author to review and edit before anything is built. Steps S2 to S6 are meant to be carried out by Muse Code agents with limited human intervention; this page is their instructions.

## 1. Question

Given one reproducible Nav2 failure, does an agent built on a Meta model, reading the incident's logs, find a configuration change that **provably** removes the failure in **fewer simulator runs** than random search over the same allowed settings?

Any answer counts: "fewer", "not fewer" or "inconclusive" is reported as it comes out.

## 2. Not in scope

Real robots; explaining the failure in prose; more than one failure F (a second only if time allows); changing Nav2's code; rebuilding a site from a map (both arms get the same simulated site from `incident.json`).

## 3. The failure F

**F = `incidents/C-corridor`, SYNTHETIC** (S1 done, 28 October; awaiting the author's check at G1).

- Site: a corridor 1.5 m long and 0.55 m wide, ahead of the robot's start in the TurtleBot 3 sandbox. With Nav2's stock configuration the robot drives through it.
- Planted setting: MPPI `CostCritic.cost_weight` 25.0 instead of the stock 3.81 (`incidents/C-corridor/SYNTHETIC.md`). Note that 25.0 lies outside the allowlist range of 1.0 to 10.0; candidates stay inside the range.
- Lab evidence (author's private lab, 28 October): with the planted setting, 5 of 5 runs failed (the robot never reached the goal, stood still 45.5 to 88.3 s, cancelled at the 120 s budget). Two allowlisted changes passed the proof rule: `CostCritic.cost_weight` back to 3.81 (5 of 5, empty site 3 of 3), and `cost_scaling_factor` 15.0 in both costmaps with the planted 25.0 kept (4 of 4 valid runs, 1 run not ready and excluded; empty site 3 of 3). No run came closer than 0.30 m to a wall.
- Consequence for the race: the planted value is 6.5 times the stock value, so a model that knows Nav2's defaults may spot it at once, and random search touches that setting in about a third of its candidates. The race therefore mainly tests whether reading the logs and configuration leads to a fix faster than blind search on an easy case; report it as such.

Requirements that F had to meet:

- F is a navfail incident folder (`incidents/<name>/`) reproduced by `reproduce/reproduce.sh`.
- With F's deployed configuration, the failure (a stall of 15 s or more, or not reaching the goal) happens in at least 4 of 5 runs.
- At least one change inside the allowlist (section 4) passes the proof rule (section 5). Without this the experiment is void.
- F uses Nav2's stock configuration, anchored to an entry in `docs/RESEARCH.md`. Only if no such F is found may F use one planted bad setting, labelled "synthetic" in its folder and in every result.

Why synthetic: no stock F was found. Eight stock layouts (doorways 0.50 to 0.575 m, 1.5 m corridors 0.55 to 0.65 m, a symmetric fork, a gap beside a box) either passed cleanly or, at 0.50 m, were blocked for the planner itself, which no allowed setting fixes. Planted values inside the allowed ranges (cost scaling 1.0, inflation 1.0, cost weight 10.0) did not cause a failure.

## 4. Allowed changes (the allowlist)

Each candidate changes one to three of these. Inflation settings change in the global and the local costmap together.

| Setting | Stock value | Allowed range |
| --- | ---: | --- |
| `inflation_layer.inflation_radius` | 0.70 | 0.30 to 1.00 |
| `inflation_layer.cost_scaling_factor` | 3.0 | 1.0 to 15.0 |
| MPPI `CostCritic.cost_weight` | 3.81 | 1.0 to 10.0 |
| MPPI `PathAlignCritic.cost_weight` | 14.0 | 2.0 to 20.0 |
| MPPI `PathFollowCritic.cost_weight` | 5.0 | 1.0 to 10.0 |
| MPPI `PreferForwardCritic.cost_weight` | 5.0 | 0.0 to 10.0 |

Never allowed: the robot's radius or footprint, the collision monitor, speed limits, goal tolerances, plugins, the behaviour tree, the map, the site.

## 5. Proof rule (frozen after checkpoint G1)

A candidate is a **proven fix** when all of these hold:

1. In F's site, with the candidate configuration, the robot reaches the goal with no stall of 15 s or more in at least 4 of 5 runs.
2. No run collides with a wall (checked against the true position in `groundtruth.csv` and the walls in `incident.json`).
3. In the same site without the walls of the incident (empty-site check), it reaches the goal in 3 of 3 runs.

Evaluation order per candidate: 1 screening run; only if it passes, 4 more runs and the 3 empty-site runs. **Every run counts towards the budget**, screening runs included.

Baseline: before the race, F's own configuration is run 10 times; the failure must appear in at least 8. This is the control: it shows how often F fails with nothing changed.

## 6. The two arms

- **Random arm:** draws a candidate uniformly from the allowlist (1 to 3 settings, values uniform in their ranges), with a recorded seed per search.
- **Agent arm:** `muse-wonder-1.0` (Meta Model API, Standard mode, reasoning effort `xhigh`), receives the operator note, `nav2.log`, a timeline extracted from the bag by code, the deployed configuration and the allowlist. It returns one candidate as JSON: `{"changes": {setting: value}, "reason": "..."}`. Invalid output: one retry, then the proposal is counted as used, with no runs. After each candidate it is told only that candidate's run results (as numbers from the run files).

Neither arm sees `incident.json`, the answer key, or the other arm's results.

## 7. The race

- 5 searches per arm, interleaved (agent, random, agent, ...).
- Budget per search: 40 simulator runs. A search stops at the first proven fix or when the budget is used.
- Measure per search: runs used until the first proven fix; "none" if the budget ran out.
- Expected simulator time: up to 400 runs at 1 to 1.5 minutes each, about 7 to 10 hours, run overnight.

**Verdict, descriptive only** (5 searches per arm is too few for a statistical claim):

- **"fewer"** if the agent found a proven fix in at least as many searches as random, with a lower median of runs used;
- **"not fewer"** if its median is equal or higher;
- **"inconclusive"** if fewer than 3 searches of either arm found a fix.

## 8. Steps and checkpoints

| Step | Who | What | Done when |
| --- | --- | --- | --- |
| G0 | author | Meta API reachable, spend cap of $100 set on the Billing page, credit terms read, Muse Code installed in WSL | one API call succeeds |
| S1 | lab (author) | find F (section 3) | done 28 Oct: F = `incidents/C-corridor` (synthetic), two proven fixes |
| G1 | author | watch one run of F and of its fix; freeze section 5 | agreed |
| S2 | Muse | scoring code: proof rule, collision check, empty-site check, run counting, plus `experiment/verify.py`, which recomputes every number from the run files; tests first | tests pass; SHA-256 of the scoring files written into this page |
| S3 | Muse | random arm | one search runs end to end |
| S4 | Muse | agent arm, including the bag timeline extraction | one search runs end to end |
| G2 | author | check both dry runs against the run files | numbers match |
| S5 | Muse | the race (section 7) | all 10 searches finished |
| S6 | Muse, then author | report: table per search, verdict, all numbers checked by `verify.py`; then the author's review and the demo video | verdict stated |

**S2 freeze (28 October 2026):** scoring files and their tests are frozen at these SHA-256 hashes (rule 3 below). A changed hash voids the result; tell the author instead of editing.

| File | SHA-256 |
| --- | --- |
| `experiment/allowlist.py` | `444eacad07376d4dbd159947235031c3f92736b6d4b605e9ae8dd9f71b1ce59f` |
| `experiment/scoring.py` | `1ac0d599f3f5cf2efa16d20a49bf0766691f0dd3b6fe5951c7cdd3a6180df8e2` |
| `experiment/verify.py` | `f4dffaf342c54a857860691a3605e29be266262e2039f1784f20117637bfc13e` |
| `experiment/tests/test_scoring.py` | `571a633805ac1e75cb7b9b012a8cea70676b1049adfd3f1eed5baecde55c91e3` |
| `experiment/tests/test_verify.py` | `0a48c7fa130f0a67b014b8d29d58061ed0880bd69b285ce206e4f527ad84e625` |

At G1, G2 and before S6's report is published, the agents stop and wait for the author.

## 9. Rules for the agents

1. Work only in this repository, on a branch named `experiment`, inside WSL. Muse Code sub-agents each work in their own worktree.
2. **One simulator at a time.** Only one agent (the runner) starts simulations; the others queue their requests. `reproduce.sh` refuses to start a second simulator (exit 2); treat that as "wait", never kill another run.
3. **Frozen files may not be edited:** `reproduce/` (except adding a new incident folder) and, after G1, the scoring files and their tests. A changed frozen file voids the result.
4. **Never write, edit or delete run files** (`incidents/*/runs/`); results are read from them only.
5. **Every number in a report comes from a run file** and is recomputed by `verify.py`. A number that `verify.py` cannot reproduce is removed.
6. Report failures, crashes and negative results as they are. Do not retry a run to get a better result; a crashed run (simulator not ready) is rerun and the crash recorded.
7. Stop and wait for the author at G1, G2 and before publishing the report, and immediately if the spend reaches $90 or the budget rules cannot be kept.
8. The API key comes only from the environment (`MODEL_API_KEY`), never in code, logs or commits.
9. Commit messages describe the change; no co-author lines.

## 10. Known risks

- F is synthetic and easy (section 3); a clear win for either arm says little about real failures.
- Nav2 occasionally fails to start (1 of 25 lab runs on 28 October was not ready); such runs are rerun and recorded, never counted.
- A model may propose the commonly advised fix from memory; that is allowed and is part of what is measured.
- 5 searches per arm show a tendency at best.
- Muse Code's sub-agent and long-running features are known from launch coverage only, not tested by us.
