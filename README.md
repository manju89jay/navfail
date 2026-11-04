# navfail

**When a robot fails to navigate, navfail reproduces the failure in simulation, has an AI agent propose a fix from the same evidence an engineer would get, and accepts the fix only after the robot proves it in repeated runs.**

Built for the Meta Global AI Developer Hackathon, 27 October to 4 November 2026. Theme: *Push the Frontier*, giving a machine a new capability.

**Demo video (under 3 minutes):** https://www.youtube.com/watch?v=GcGkKBwSlXA

| | |
| --- | --- |
| Agent model | Muse Wonder 1.0 through the Meta Model API, maximum reasoning effort |
| Coding agent | Muse Code (Meta) built the experiment code in `experiment/` |
| Robot stack | ROS 2 Jazzy, Nav2 1.3.13, Gazebo Harmonic, TurtleBot 3 Waffle (open source, not ours) |
| Result | Agent 8 runs to a proven fix in each of 5 searches; random search 18, 9, 8, 28, 9 (median 8 vs 9), $0.46 of API |
| Check it | `python3 -m experiment.verify experiment/work/race/agent-1/cand-1-site` exits 0 |

## 1. The problem

A mobile robot fails during a mission: it stops in front of an open gap, rocks back and forth, never arrives. Its navigation stack has hundreds of settings (333 in the configuration used here), and the cause is usually one or two of them. Today a robotics engineer finds it by hand: read the logs, guess a setting, rerun the simulation, look again. Every guess costs a simulator run of a few minutes, and a lucky run can look like a fix that is not one.

## 2. What we built during the hackathon

Three parts, all written between 27 October and 4 November 2026 (first commit 27 October):

| Part | Folder | What it does |
| --- | --- | --- |
| Reproduction harness | `reproduce/`, `incidents/` | Rebuilds a recorded Nav2 failure in Gazebo on demand and records every run: result, logs, the true trajectory from the simulator, the deployed configuration. One command: `bash reproduce/reproduce.sh incidents/<name>`. |
| Investigating agent and search loop | `experiment/agent_arm.py`, `timeline.py`, `allowlist.py`, `search.py`, `simulator.py`, `random_arm.py` | Packs the evidence, asks the model for one change, checks the change against an allowlist, runs it, feeds failures back, counts every run against a budget. A seeded random-search arm runs the same loop as the control. |
| Frozen referee | `experiment/scoring.py`, `experiment/verify.py` | Scores every run the same way and recomputes every reported number from the raw run files. Frozen with SHA-256 hashes (`docs/EXPERIMENT.md` section 8) before the race. |

Not ours: ROS 2, Nav2, Gazebo and the TurtleBot 3 models (Apache-2.0); files derived from Nav2 are listed in `NOTICE`.

## 3. How it works

1. **Evidence.** The agent gets what an engineer would get: the operator's note, the error and warning lines of `nav2.log`, a timeline extracted from the robot's rosbag2 recording (`experiment/timeline.py`), and the deployed configuration. It never sees the incident definition or any scoring answer.
2. **Proposal.** The model answers in strict JSON: `{"changes": {setting: value}, "reason": "..."}`. Invalid output gets one retry, then the proposal counts as used.
3. **Allowlist check, before any run.** 1 to 3 changes, only among six Nav2 settings, each inside its allowed range (`experiment/allowlist.py`).
4. **Proof.** One screening run; only if it passes, 4 more runs in the site and 3 on an empty floor. A fix is proven when at least 4 of 5 site runs reach the goal with no stall of 15 s or more, no run touches a wall (judged on the true position from the simulator, not on what the robot believes), and 3 of 3 empty-floor runs reach the goal.
5. **Feedback.** A rejected proposal and its result go back to the agent, which proposes again.
6. **Budget.** Every simulator run counts, screening runs included: 40 per search. 8 runs is the minimum for one proven fix.

## 4. How Meta's AI is used

- **Muse Wonder 1.0** (Meta Model API, maximum reasoning effort) is the investigating agent. It reads the evidence, proposes one change and explains why. It never scores its own proposals; the referee does.
- **Prompt caching by design:** the prompt's stable prefix (rules, allowlist, configuration, evidence) is byte-identical across one search's proposals and only the history suffix changes, so repeated proposals hit the cached-input rate. The whole race cost $0.46 of API.
- **Muse Code** (Meta's coding agent) built the experiment code in `experiment/` and the run drivers in `experiment/work/`.
- **The model is replaceable:** the API address and model name are two constants in `experiment/agent_arm.py`. Only Muse Wonder has been run.

Its first proposal on the test failure, verbatim from `experiment/work/race/agent-1/search.json`:

> Deployed CostCritic cost_weight is 25.0 versus stock 3.81. In the narrow corridor, inflated wall costs dominate MPPI trajectory scoring, so corridor-entering trajectories are rejected and the robot stalls at the entrance with repeated progress failures. Restoring the stock weight retains obstacle avoidance while allowing passage through the corridor.

## 5. Results

The test failure is `incidents/C-corridor`: a synthetic corridor with one planted setting (`CostCritic.cost_weight` 25.0 instead of the stock 3.81). With its deployed configuration it failed 10 of 10 baseline runs.

| Arm | Runs to first proven fix, per search | Median |
| --- | --- | ---: |
| navfail agent (Muse Wonder) | 8, 8, 8, 8, 8 | 8 |
| Random search | 18, 9, 8, 28, 9 | 9 |

The agent proved its first proposal in every search, at the minimum possible cost. The proposals varied: in three searches the agent changed only `CostCritic.cost_weight` to 3.81; in two it also changed `inflation_layer.cost_scaling_factor` to 10.0 and `inflation_layer.inflation_radius` to 0.4 (`experiment/work/race/agent-*/search.json`). All five were proven in 8 runs. The verdict recorded in `docs/REPORT.md` is "fewer" for the agent. The caveats are in section 8 and belong with this table.

## 6. Check it yourself

No simulator is needed for these:

```bash
python3 -m experiment.verify experiment/work/race/agent-1/cand-1-site   # exits 0, "mismatches": []
python3 -m experiment.verify experiment/work/baseline
sha256sum experiment/scoring.py experiment/verify.py experiment/allowlist.py \
  experiment/tests/test_scoring.py experiment/tests/test_verify.py      # compare with docs/EXPERIMENT.md section 8
python3 -m pytest experiment/tests -q                                    # 56 passed with ROS 2 sourced; without it 55 passed, 1 skipped (test_timeline needs rosbag2_py)
```

With ROS 2 Jazzy, Nav2 and Gazebo Harmonic installed (Ubuntu 24.04):

```bash
bash reproduce/reproduce.sh incidents/C-corridor          # one run, headless
bash reproduce/reproduce.sh incidents/C-corridor --gui    # with Gazebo and RViz windows
```

The race itself: `experiment/work/race_driver.py` (needs `MODEL_API_KEY` for the agent arm; up to about 2.5 minutes per simulator run). It skips every search already saved under `experiment/work/race/`, and all ten are committed, so to rerun the race move that folder aside first; the full race is ten searches and takes several hours. During a search the simulator runs without a window; use `reproduce.sh --gui` to watch a single run.

## 7. Using navfail on a customer project

What exists today runs from this repository on a prepared incident folder; the one-command tool is the next step and is **not built**.

| Step | Today | Next (not built) |
| --- | --- | --- |
| 1. Collect the incident | An incident folder: rosbag2 recording, `nav2.log`, `deployed/nav2_params.yaml`, map, `operator_note.md` | Import straight from the robot's logs |
| 2. Rebuild the site and reproduce | Describe the site for simulation in `incident.json`; `bash reproduce/reproduce.sh incidents/<site>` confirms the failure N of N | Rebuild obstacles that appear only in the recording |
| 3. Investigate | The search loop; the settings it may change are set in `experiment/allowlist.py` | `navfail investigate <incident>` |
| 4. Hand over | A proven change with its runs, trajectories and `verify` output; the engineer reviews and applies it | An automatic per-incident report |

**Who it is for:** teams running mobile robots in warehouses and factories, integrators commissioning robots at a customer site, and the test engineers who validate robot behaviour.

## 8. Limits

1. **The test failure is planted, and its cause is visible in the deployed configuration.** It is a demonstration, not an evaluation on failures nobody prepared.
2. **The gap is one run** of median over five searches per arm: descriptive, not a statistical claim.
3. **In the earlier one-search dry run the agent did not prove a fix while random search did.**
4. **A real reported failure did not reproduce.** A warehouse shelf-aisle incident (`incidents/W-warehouse`) built from ros-navigation/navigation2 issue #4938 passed 5 of 5 stock runs at aisle widths of 1.1 m, 0.8 m and 0.7 m, so no search was run on it.
5. **A model may answer from memory instead of investigating.** Advice for this kind of failure is public in Nav2's tuning guide.
6. **The site is a toy and the walls are drawn on the map.** Real sites have people, pallets and obstacles that appear only in the sensor recording.
7. **Simulation only.** Nothing here says anything about real robots.
8. **The incidents are not intermittent.** They behave the same way in every run, so judging intermittent failures by repeated runs is untested.
9. **The research is a search, not a census.** The 50 reported failures in `docs/RESEARCH.md` were found by keyword search, and much of that work is AI-drafted (section 12); the entries were not each re-read by a person.
10. **One person, about one week of building.**

## 9. Demo video

The warehouse scenes are a visual re-render of the recorded demo runs (the robot's path from each run's `groundtruth.csv`), using the "Depot" model by Open Robotics (CC BY 4.0); the experiment itself ran in Nav2's TurtleBot 3 sandbox. The narration is a synthetic voice (Kokoro, open source).

## 10. Repository map

| Path | Contents |
| --- | --- |
| `reproduce/` | Reproduction harness and its tests |
| `incidents/` | A-doorway, B-drop-off, C-corridor (the race), W-warehouse (did not reproduce) |
| `experiment/` | Agent arm, random arm, search loop, simulator bridge, bag timeline, allowlist, frozen referee, tests |
| `experiment/work/` | Run drivers and the committed evidence (race, baseline), without the bags |
| `docs/EXPERIMENT.md` | The experiment's specification, frozen before the race, with the referee's hashes |
| `docs/REPORT.md` | The result and its caveats |
| `docs/RESEARCH.md` | 50 reported Nav2 failures in eight categories, and the existing tools |

## 11. Related work

Explaining a failure from its logs with a language model is not new: ROSA (NASA JPL, https://arxiv.org/abs/2410.06472), ROS Help Desk (CSIRO, https://arxiv.org/abs/2507.07846), Roboto Agents, PyRoboReplay and others (`docs/RESEARCH.md` section 6). What we did not find in the sources we read: starting from an incident, testing a proposed configuration change by rerunning it in simulation, and reporting it only when it passes a fixed rule, with every run counted and a random-search control. We read their papers and documentation; we did not run them.

## 12. About this repository

- **Hackathon:** Meta Global AI Developer Hackathon, 26 October (kickoff 12:00 US Eastern, 17:00 German time) to 4 November 2026.
- **Prepared before the hackathon:** the development environment (ROS 2, Nav2 and Gazebo under WSL2), learning the stack, the project idea, and reading about existing tools (13 to 25 October). Kept in a private repository; no code from it is copied here.
- **Built during the hackathon:** the collection of the 50 entries (26 October, evening, after kickoff), the analysis of categories and gaps, this page, `docs/RESEARCH.md`, the reproduction tooling in `reproduce/` and the two incidents in `incidents/` (27 and 28 October). Then, still inside 27 October to 4 November: the scoring referee, both search arms, the race and its evidence in `experiment/`, the synthetic corridor incident, the warehouse follow-up incident, and `docs/REPORT.md`.
- **How it was built:** the work up to 28 October — `reproduce/`, incidents A, B and C, `docs/EXPERIMENT.md`, `docs/RESEARCH.md` and the README as it was then — was done before the experiment build, under the author's direction. The author chose the problem, the incidents, the scope and the design, and read the results. Separate AI review passes checked the numbers against the run files and the wording against the evidence; those reviews are not archived here.
- **Which tool built which part:** the experiment code in `experiment/` — the frozen referee, the agent and random arms, the search loop, the simulator bridge, the bag-timeline extraction — and the run drivers in `experiment/work/` were built with Muse Code (Meta). The investigating agent's model is Muse Wonder 1.0, called through the Meta Model API at maximum reasoning effort; it proposes configuration changes and gives reasons, and it never scores its own proposals. navfail uses only Meta's models for the agent itself.
- **Licence:** Apache-2.0 (`LICENSE`); the files derived from Nav2 are listed in `NOTICE`.

## 13. Terms

| Term | Meaning |
| --- | --- |
| ROS 2 | Robot Operating System 2: the common open-source software framework for robots |
| Nav2 | ROS 2's navigation stack: the software that plans and drives a robot to a goal |
| Gazebo | the robot simulator used with ROS 2 |
| rosbag2, MCAP | ROS 2's recorder and its file format: every message on chosen topics, with timestamps |
| Costmap | Nav2's grid of where the robot may and may not go |
| MPPI, CostCritic | Nav2's controller that scores many candidate trajectories; CostCritic is the part that penalises costly cells |
| Allowlist | the fixed list of settings, and their ranges, that a proposal may change |
| Screening run | the first run of a proposal; the rest of its runs happen only if it passes |
| Random search | the control: proposals drawn at random from the same allowlist, run through the same loop and budget |
