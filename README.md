# navfail

**Status, 4 November 2026:** the hackathon experiment below is built and finished. The wider product described later in this page is not built; where this page describes it, it says so. Section 6 lists the known limits.

The research behind this page is summarised in `docs/RESEARCH.md`. Terms are explained in section 13.

## What was built and what it found

navfail is now three things that work together in this repository:

- **A reproduction harness** (`reproduce/`): rebuilds a recorded Nav2 failure in the TurtleBot 3 Gazebo sandbox and records every run (result, logs, true trajectory, deployed configuration).
- **A frozen referee** (`experiment/scoring.py` and `experiment/verify.py`): scores each run the same way and recomputes every reported number from the raw run files. A candidate fix is proven only if it reaches the goal with no stall of 15 s or more in at least 4 of 5 runs in the site, collides in no run, and reaches the goal in 3 of 3 runs on the empty site. The referee's files were frozen with SHA-256 hashes before the race and not edited afterwards.
- **A race** (`experiment/`): a Muse Wonder 1.0 agent, run through the Meta Model API at maximum reasoning effort, against seeded random search. Both may change only the same six Nav2 settings, both get the same 40-run budget per search, and every run counts.

The test failure is `incidents/C-corridor`, a synthetic 0.55 m corridor with one planted setting (`CostCritic.cost_weight` 25.0 instead of the stock 3.81). With its own deployed configuration it failed 10 of 10 baseline runs. Five searches per arm gave:

| Arm | Runs to first proven fix, per search | Median |
| --- | --- | ---: |
| Muse Wonder agent | 8, 8, 8, 8, 8 | 8 |
| Random search | 18, 9, 8, 28, 9 | 9 |

The verdict recorded in `docs/REPORT.md` is "fewer" for the agent. **Caveats, stated with the result:** the failure is synthetic and easy, and the planted cause is visible in the deployed configuration; the difference is one run of median over only five searches per arm, so this is descriptive, not a statistical claim; and in the earlier one-search dry run the agent did not prove a fix while random search did.

As a follow-up, a warehouse shelf-aisle incident (`incidents/W-warehouse`) was built to test a publicly reported failure (ros-navigation/navigation2 issue #4938, picked by recorded seed). **It did not reproduce:** the stock configuration passed 5 of 5 runs at aisle widths of 1.1 m, 0.8 m and 0.7 m, so no search was run on it.

To re-check every number in the race table from the committed evidence:

```bash
python3 -m experiment.verify experiment/work/race/agent-1/cand-1-site
python3 -m experiment.verify experiment/work/baseline
```

`verify.py` exits 0 when every recomputed value matches the recorded `result.json`. The frozen referee's SHA-256 table is in `docs/EXPERIMENT.md` section 8; `sha256sum` on the five listed files must reproduce it.

## 1. The problem

A mobile robot fails during a mission: it stops, rocks back and forth, never arrives, or touches something. An operator or customer reports what they saw. A robotics engineer then has to find out why, without being told the cause. Today that is manual work: collect the robot's logs and recordings, reproduce the failure, check that it is not a one-off, strip the scene down to what matters, form a hypothesis, try a change, and rerun enough times to trust the answer. Failures are often intermittent, so every step needs repeated runs.

## 2. The goal

An unproven aim: no part of it exists yet, no pointing, no rerun check and no call to a Meta model. Reading logs with a language model to explain a failure is already done by other tools (section 10); the part we test first is narrower, in `docs/EXPERIMENT.md`.

navfail aims to be an agent, a program that uses Meta's language models to decide what to look at and what to run next, that takes what was captured when a navigation failure happened and:

- reports what went wrong;
- points to where it suspects the cause: a configuration key and line in the user's files, or a line in the navigation stack's source code for the installed version;
- tests that suspicion by reproducing the failure in simulation, applying a change at that place, rerunning, and reporting with counts whether the failure went away.

The comparison we use for the idea is a debugger such as gdb, which runs on a failing program and points to a file and line. The comparison has a limit: gdb observes where a program failed, while navfail can only suspect a place from evidence. The reruns are what would turn a suspicion into something an engineer can check. Whether that works is what this project has to show.

## 3. Scope

- **Built and tested only on ROS 2 Jazzy, Nav2 1.3.13 and Gazebo**, with a TurtleBot 3 in simulation.
- We expect the same kinds of failure on other navigation stacks, but we have only collected and checked Nav2 reports.
- **Planned design, not built:** the parts that depend on the navigation stack (configuration format, error codes, log messages, how to start it in a simulator) are kept in one replaceable part, so that other stacks such as Autoware or a company's own stack could be added later. Nothing for other stacks is planned for the hackathon.
- **Privacy, not solved:** navfail would call Meta's models through an online service, so log extracts or code would leave the user's company. Meta's Llama models can be downloaded and run locally, which might address this; not designed yet.

## 4. How people would use it (planned product flow — not built)

This section describes the product this experiment points at. That product does not exist: there is no installer and no `navfail` command. What exists is the experiment above, run from this repository on prepared incident folders. The steps below are the intended flow, and the "Status today" column separates what the hackathon experiment demonstrated from what remains unbuilt.

**Once (planned):** install navfail (a Docker image with ROS 2, Nav2 and Gazebo, or a Python package), point it at the robot's configuration, maps and launch files, choose which failure types it should handle, and provide the Meta model key in an environment variable.

**When a failure happens:**

| # | Step | Who | Status today |
| --- | --- | --- | --- |
| 1 | The robot fails at a site | customer | simulated by `reproduce/` |
| 2 | Someone reports it: robot, time, place, what was seen | customer or support | written by us for each incident (`operator_note.md`) |
| 3 | The engineer collects the recording, logs, configuration and map (section 7) | engineer | written by `reproduce/` |
| 4 | `navfail investigate <incident folder>` | engineer | **not built as a command**; the hackathon experiment runs the same loop from driver scripts in `experiment/work/` |
| 5 | **Read:** a timeline from logs and recording | navfail | built for the experiment (`experiment/timeline.py`, `experiment/agent_arm.py`) |
| 6 | **Sort:** match the symptom to a supported failure type, or say it is not supported | navfail | not built |
| 7 | **Reproduce:** rebuild the scene in simulation and run it several times | navfail | built (`reproduce/`, `experiment/simulator.py`) |
| 8 | **Narrow down:** find the setting or code path that changes the outcome | navfail | partly: the agent proposes changes inside a fixed six-setting allowlist; no code-path search |
| 9 | **Point:** the configuration line or source line, with the evidence | navfail | partly: it names the setting and records its reason; it does not point at source lines |
| 10 | **Check by rerun:** the changed setup against the original and against itself, with counts | navfail | built for the experiment's proof rule (`experiment/search.py`, `experiment/scoring.py`) |
| 11 | **Report:** what went wrong, where, the evidence, the counts, how to replay it | navfail | built as `docs/REPORT.md` with the committed run evidence; no automatic per-incident report |
| 12 | The engineer decides and changes their own repository | engineer | — |

For the hackathon we aim at steps 4 to 11 for incident A only.

## 5. The two incidents

Both are reproduced in simulation by one command, `bash reproduce/reproduce.sh incidents/<name>`, and both are modelled on public reports (`docs/REFERENCES.md`). We designed and built both ourselves, and both are weak stand-ins for their reports, for the reasons given below. Their layouts can be read in each `incident.json`, so neither cause is hidden from a reader of this repository. **We have not verified that either reproduction has the same cause as its report.**

### Incident A: the robot stalls near a very narrow doorway

- The report (2023): a robot on Nav2 stops at a doorway at about half of all crossings and rotates back and forth; sometimes it frees itself after about 30 seconds, often it needs a push. The reporter says it is not entirely solved.
- Our reproduction: a wall with a doorway 0.5 m wide in Nav2's TurtleBot 3 sandbox, for a robot 0.44 m wide, with Nav2's stock configuration. In 3 of 3 runs the robot moved about 0.15 m from its start and then stayed within 0.10 m of one spot, its front about 0.2 m from the wall, for 47.2 to 65.4 s, while Nav2's controller logged that it was failing to make progress (all 3 runs) and that it could not compute a path (2 runs). 2 runs then got through, 1 failed with Nav2's "no valid path" error (`incidents/A-doorway/operator_note.md`).
- **How it differs from the report:** it happened in 3 of 3 runs, not about half of crossings, and lasted longer. In one earlier trial run with a 0.6 m doorway (not kept) the robot passed without stopping, so in our layout the stall appears only when the gap is a few centimetres wider than the robot. A reader could fairly call that expected behaviour rather than a fault.
- **Not tested yet:** whether any change removes the stall. If none does, navfail has nothing to confirm for this incident.

### Incident B: a goal inside an obstacle, and a slow, vague failure

- The report (2025): a Nav2 issue in which a planner works towards a goal that lies inside an obstacle when its goal tolerance is above zero, wasting time.
- Our reproduction: the goal is placed inside an obstacle that is drawn on the map, with Nav2's Smac 2D planner configured. In 3 of 3 runs the robot never sets off; Nav2 turns, pauses, backs up and turns again, and the mission fails after 17.5 to 19.0 s with "no valid path", code 208 (`incidents/B-drop-off/operator_note.md`).
- **How it differs from the report:** finding no path is the correct answer for a goal inside an obstacle; the planner here fails quickly instead of working towards the goal. What remains is about 18 s of recovery manoeuvres and an error that says "no valid path" rather than that the goal is occupied. B shares the area of the report, not its symptom, and whether it is a failure at all is debatable. It may be replaced (`docs/TODO.md`).

## 6. Known limits

1. **Two incidents we built ourselves, whose answers we know, are a demonstration, not an evaluation.** Results on them say little about failures nobody has prepared.
2. **The site is a toy:** a small walled arena with pillars and a basic robot. Real warehouses, robots and sensors are far more complex.
3. **Rebuilding the scene works only because we drew the walls on the map.** At a real site, people, pallets and anything not on the map appear only in the sensor recording; navfail has no answer for that yet.
4. **A model may answer from memory instead of investigating.** Both source reports are public, and common advice for such failures is in Nav2's tuning guide. Pointing at the right setting can therefore come from recall. A rerun check could measure more than recall; it is not built.
5. **Our incidents are not intermittent.** Both behave the same way in 3 of 3 runs, so the idea of judging intermittent failures by repeated runs is untested on a truly intermittent case.
6. **Meta model access and quality are not tested yet** for this task.
7. **Simulation only.** Nothing here says anything about real robots.
8. **The research is a search, not a census, and partly unbacked here.** The 50 entries are 28 Nav2 tracker issues, 13 posts from question-and-answer sites and robot trackers, and 9 from documentation and one paper. The tracker issues were found by keyword search and screened by title. The counts per category reflect what we searched for, not how often failures happen. The search counts and the release-history checks come from private notes; no file in this repository backs them (`docs/RESEARCH.md` section 5).
9. **Much of the work is AI-drafted** (section 14), including the research entries, which were not each re-read by a person.
10. **One person;** the hackathon build is about one week, after preparation from 13 October.

## 7. What navfail would read: the incident folder

What the person reporting a failure would hand over, in formats widely used with ROS 2 robots:

| Part | Format | In this repository's incidents |
| --- | --- | --- |
| Recording: tf, odometry, velocity commands, lidar scan, localisation pose, plan, costmaps, behaviour-tree log, rosout, diagnostics, navigation action status | rosbag2 with MCAP files | yes |
| Text logs | the launch output | yes (`nav2.log`) |
| Configuration | ROS parameter YAML | yes; launch file and behaviour tree are Nav2's stock files and are not copied |
| Map | `map.yaml` + `map.pgm` | yes |
| Versions | installed packages | yes |
| Operator note | robot, time, place, what was seen | yes, written by us |

`incidents/<name>/` also holds files a reporter would not have: `incident.json` and each run's world file describe the simulated site, and `groundtruth.csv` is the true position only a simulation knows. Which files the agent is given is decided in its specification, not written yet.

## 8. Failure types

The 50 entries fall into eight categories (`docs/RESEARCH.md` sections 2 and 3); C8 rests on a single entry:

| # | Category | Reports |
| --- | --- | ---: |
| C1 | Footprint, inflation and tight gaps | 12 |
| C2 | Costmap not clearing or clearing wrongly | 8 |
| C3 | Controller tuning | 7 |
| C4 | Late, dynamic or unseen obstacle | 6 |
| C5 | Recovery loop or recovery collision | 6 |
| C6 | Planner path validity | 6 |
| C7 | Goal in or near an obstacle | 4 |
| C8 | Localisation near obstacles | 1 |

The plan is that the user chooses which failure types navfail handles; it would start with one (incident A) and add more only after that one works (`docs/TODO.md`).

## 9. Why this is hard

- **Field failures are often intermittent.** Incident A's reporter saw it at about half of crossings, so one run proves nothing there. Our own two reproductions are not intermittent (section 6).
- **Each run is slow.** One simulated mission with start and shutdown took 32 to 93 s in our final runs (`result.json`, field `wall_s`), and one machine runs one simulator at a time.
- **A full investigation needs many runs.** Our estimate for a scene with five obstacles: 3 baseline runs, 3 to confirm the failure, 15 to 30 to shrink the scene, 20 for a final confirmation and 24 to compare two configurations, 65 to 80 runs in all, about 0.6 to 2.1 hours of simulation at the measured run times. This is an estimate, not a measurement.

## 10. What existing tools cover

Tools we looked at (`docs/RESEARCH.md` section 4): RoboVAST and Scenario Execution (scenario test frameworks for ROS 2), Nav2's own system tests, DDEnv and the reducers of Valle and Zeller (research methods that shrink a failing test), robot fuzzers, LLM scenario generators, and industry tools.

| Step | What we found in the sources we read |
| --- | --- |
| Detect the failure | partly: collisions, aborts and timeouts are seen; checking the plan or the costmap is not described |
| Confirm by repeated runs | some tools, only for what they detect |
| Shrink the scene | partly: one tool removes obstacles, but on ROS 1 and without a licence |
| Explain the failure | **already done by several tools** (below) |
| Compare two configurations | partly: parameter variation exists, without a verdict from repeated runs and a control |
| Package the failure for replay | partly |
| Point to the configuration or source line | one commercial tool says it traces failures into the codebase (below) |

**Tools that read robot logs with a language model and explain failures** (found on 28 October, after our first research missed them; read, not run):

- **ROSA** (NASA JPL, 2024, open source): an agent to inspect, diagnose and operate ROS 1 and ROS 2 robots. https://arxiv.org/abs/2410.06472
- **ROS Help Desk** (CSIRO, 2025): diagnoses ROS errors from logs and sensor data, with a code-review module; evaluated on a TurtleBot 3 in Gazebo with injected faults, the same robot and simulator as here. https://arxiv.org/abs/2507.07846
- **Roboto Agents** (2026, commercial): reviews each new recording, tags failures, traces root causes into the codebase and drafts fixes; no evaluation published. https://discourse.openrobotics.org/t/roboto-agents-agentic-triage-root-cause-analysis-and-data-curation-for-rosbags-and-mcap/57438
- **PyRoboReplay** (open source): says it does root-cause analysis and Nav2-specific diagnosis from recordings; self-described only. https://github.com/mullassery/pyroboreplay
- **Bagel 2.0**, **mcp-ros2-logs**, **explainable_ros**: ask questions of recordings and logs in plain language.

So explaining a failure from its logs is not new. What we did not find: starting from an incident, testing a suspected configuration change by rerunning it in simulation, and reporting the result with counts and a control. That is the question in `docs/EXPERIMENT.md`.

This is based on reading the tools' papers, documentation and announcements (listed here and in `docs/RESEARCH.md` section 6), not on running them; "not described" means we did not find it, not that it cannot be done. Where they are stronger (scale, many environments, cluster infrastructure), navfail does not compete.

## 11. The environment

ROS 2 Jazzy, Nav2 1.3.13, Gazebo Sim 8 (Harmonic), Ubuntu 24.04 under WSL2 on one Windows laptop. Robot: TurtleBot 3 Waffle, round, radius 0.22 m, 2D lidar. Site: Nav2's TurtleBot 3 sandbox with walls and fixtures added per incident. Hackathon rule: navfail uses only Meta's models.

## 12. Not in this page

How navfail would work inside; what counts as solved (not decided yet); the cause of either incident.

## 13. Terms

| Term | Meaning |
| --- | --- |
| ROS 2 | Robot Operating System 2: the common open-source software framework for robots |
| Navigation stack | the software that plans and drives a robot to a goal; Nav2 is ROS 2's |
| Gazebo | the robot simulator used with ROS 2 |
| gdb | a tool that runs a program and reports where it fails, with file and line |
| rosbag2, MCAP | ROS 2's recorder and its file format: every message on chosen topics, with timestamps |
| tf, odometry, lidar, localisation pose | where the robot's parts are; how far its wheels say it moved; its laser distance sensor; where it believes it is on the map |
| Costmap | Nav2's grid of where the robot may and may not go |
| Behaviour tree | the decision logic Nav2 follows: plan, drive, and what to try when that fails |
| Recovery | what Nav2 tries after a failure: turn on the spot, pause, back up |
| "No valid path" (code 208) | Nav2's error when its planner finds no route to the goal |
| Control | the same configuration run against itself, to see how much results vary by chance |

## 14. About this repository

- **Hackathon:** Meta Global AI Developer Hackathon, 26 October (kickoff 12:00 US Eastern, 17:00 German time) to 4 November 2026.
- **Prepared before the hackathon:** the development environment (ROS 2, Nav2 and Gazebo under WSL2), learning the stack, the project idea, and reading about existing tools (13 to 25 October). Kept in a private repository; no code from it is copied here.
- **Built during the hackathon:** the collection of the 50 entries (26 October, evening, after kickoff), the analysis of categories and gaps, this page, `docs/RESEARCH.md`, the reproduction tooling in `reproduce/` and the two incidents in `incidents/` (27 and 28 October). Then, still inside 27 October to 4 November: the scoring referee, both search arms, the race and its evidence in `experiment/`, the synthetic corridor incident, the warehouse follow-up incident, and `docs/REPORT.md`.
- **How it was built:** the work up to 28 October — `reproduce/`, incidents A, B and C, `docs/EXPERIMENT.md`, `docs/RESEARCH.md` and the README as it was then — was done before the experiment build, under the author's direction. The author chose the problem, the incidents, the scope and the design, and read the results. Separate AI review passes checked the numbers against the run files and the wording against the evidence; those reviews are not archived here.
- **Which tool built which part:** the experiment code in `experiment/` — the frozen referee, the agent and random arms, the search loop, the simulator bridge, the bag-timeline extraction — and the run drivers in `experiment/work/` were built with Muse Code (Meta). The investigating agent's model is Muse Wonder 1.0, called through the Meta Model API at maximum reasoning effort; it proposes configuration changes and gives reasons, and it never scores its own proposals. navfail uses only Meta's models for the agent itself.
- **Licence:** Apache-2.0 (`LICENSE`); the files derived from Nav2 are listed in `NOTICE`.
