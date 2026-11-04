# S6 Report (FINAL — approved by the author at wrap-up, 4 Nov 2026)

Experiment: does reading the logs help find a proven fix with fewer simulator
runs? Failure F is `incidents/C-corridor`, SYNTHETIC in every label below.
Design and rules: `docs/EXPERIMENT.md`. Every number in this report was
recomputed by `experiment/verify.py` from run files; mismatches: none.
Run-count cross-check between each `search.json` and its run folders:
all agree.

## Verdict

**"fewer"** (descriptive only; 5 searches per arm is too few for a
statistical claim, EXPERIMENT.md section 7).

The agent found a proven fix in 5 of 5 searches, median 8 runs.
Random search found a proven fix in 5 of 5 searches, median 9 runs.

## Baseline (gate before the race)

F with its own deployed configuration, 10 valid runs on a copy:
10 of 10 failed (longest still 77.6–98.7 s, goal never reached).
Gate required at least 8 failures. `verify.py` exit 0.

## Race results (budget 40 runs per search; stop at first proven fix)

| Search | Runs to proven fix | Winning candidate |
| --- | ---: | --- |
| agent-1 | 8 | CostCritic.cost_weight 3.81 |
| agent-2 | 8 | CostCritic.cost_weight 3.81 |
| agent-3 | 8 | CostCritic.cost_weight 3.81 |
| agent-4 | 8 | CostCritic 3.81, cost_scaling 10.0, inflation_radius 0.4 |
| agent-5 | 8 | CostCritic 3.81, cost_scaling 10.0, inflation_radius 0.4 |
| random-1 | 18 | PathAlign 14.7036, cost_scaling 12.6959, PreferForward 8.1329 |
| random-2 | 9 | CostCritic 4.8131, PreferForward 2.9699, PathAlign 18.9659 |
| random-3 | 8 | CostCritic 3.1157, inflation_radius 0.7323, PathAlign 7.8513 |
| random-4 | 28 | cost_scaling 12.6076, CostCritic 5.6274, inflation_radius 0.6628 |
| random-5 | 9 | cost_scaling 11.6723 |

Every agent search proved its first candidate. No search recorded a
non-valid run. No collision occurred in any winning candidate's runs
(site clearances recomputed per run by verify.py; see analysis.json).

## G2 dry runs (before the race, budget 10 each)

- Random (seed 20261028): proven in 8 runs (5/5 site, 3/3 empty).
- Agent: not proven in 10 runs. First candidate stalled 39.7 s in
  screening; second passed 5/5 site but only 2/3 empty.

## Incidents during the race

- agent-3, first attempt: the API became unreachable (network) after
  9 runs and the search died before writing its result. The attempt's
  folders are preserved at `experiment/work/race/agent-3-attempt1-network-crash/`
  and are excluded from every count above. The restarted agent-3 (with
  network-retry added to the scratch race driver) proved in 8 runs.
- Nothing else failed. Total race simulator runs: 112.

## Cost

Agent API spend during the race: $0.46 (race_state.json).
Earlier smoke, probe and G2 agent calls: about $0.45. Total under $1,
far below the $90 stop.

## Caveats

- F is synthetic and easy (EXPERIMENT.md sections 3 and 10): the planted
  value is 6.5x stock, and a model that knows Nav2 defaults may spot it
  at once — that is allowed and is part of what was measured.
- 5 searches per arm show a tendency at best.
- The agent was perfectly consistent (8, 8, 8, 8, 8); random was
  variable (8–28). The verdict rests on medians 8 vs 9.

## Evidence

- Per-search records: `experiment/work/race/*/search.json`
- Recomputation and verdict: `experiment/work/race/analysis.json`
- Baseline: `experiment/work/baseline/baseline.json`
- G2: `experiment/work/g2-random/search.json`, `experiment/work/g2-agent/search.json`

## Follow-up: warehouse test on a publicly reported failure

After the race, a second test was specced (SPEC-SANDBOX-TEST.md): a
warehouse shelf aisle built in the same sandbox, with the failure picked
by recorded seed (20261104) from public Nav2 reports. The pick was
ros-navigation/navigation2 issue #4938 (robot reaches the goal, then
fails on final orientation; the reporter's controller was DWB, ours is
MPPI). Result: **does not reproduce**. At aisle widths 1.1 m, 0.8 m and
0.7 m the stock configuration passed 5 of 5 runs each time; the gate
(≥4 of 5 baseline failures) was never met, so no search ran and nothing
was substituted. An earlier site placement crossed by stock sandbox
obstacles was preserved separately and excluded. Evidence:
`experiment/work/warehouse/` and `incidents/W-warehouse/SOURCE.md`.

## Demo video

`experiment/work/navfail-demo.mp4` (77 s, silent, captioned cards):
recorded baseline and winning-run traces from `groundtruth.csv`, the
race chart generated from `analysis.json`, and the limitations on the
closing card. Built by `experiment/work/make_video.py`; no generated
footage depicts the robot or any result.

Status: FINAL as an internal submission record, approved by the author
at wrap-up on 4 Nov 2026. External publishing remains the author's step.
