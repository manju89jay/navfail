# navfail

This page says what problem navfail addresses, what it aims for and how people will use it. It does not say how navfail works inside, and it does not yet say what "solved" means (decided later). The research behind it is summarised in `docs/RESEARCH.md`. Terms are explained in section 12.

## 1. The problem in one paragraph

A mobile robot fails during a mission: it stops, rocks back and forth, never arrives, or touches something. An operator or customer reports what they saw. A robotics engineer then has to find out why, without being told the cause. Today that is manual work: collect the robot's logs and recordings, reproduce the failure, check that it is not a one-off, strip the scene down to what matters, form a hypothesis, try a configuration change, and rerun enough times to trust the answer. Failures are often intermittent, so every step needs repeated runs. The kinds of failure are not specific to one navigation stack; their details (parameter names, error codes, log messages) are.

## 2. End goal

**navfail is a debugger for robot navigation.** It is an agent: a program that uses Meta's language models to decide what to look at and what to run next. Like gdb or a sanitizer for a program, it is run with one command on what was captured when the failure happened, and it reports the error and points to where it comes from:

- in the user's own files: the configuration key and line, the map, the behaviour tree;
- or in the navigation stack's source code, pinned to the installed version.

Unlike a debugger, navfail cannot read the cause directly; it can only suspect a place from the evidence. What it can do instead is test that suspicion: reproduce the failure in simulation, apply a change at the place it points to, rerun, and report whether the failure went away, with counts. A pointer is reported as confirmed or not confirmed by those reruns.

Open decision: our rule so far has been that model output is labelled "hypotheses" and never claims a root cause. How a pointer confirmed by reruns is worded is decided in the agent's specification (to be written).

## 3. Scope

- **The problem is generic.** Any mobile robot navigation stack has these failures.
- **Reading the incident and spotting the symptom work for any stack that records standard ROS 2 data**: position, velocity commands, sensor data, logs, diagnostics (section 6).
- **Everything that depends on the stack sits in one replaceable part, a stack adapter**: configuration format, error codes, log messages, source layout, and how to start the stack in a simulator.
- **The hackathon ships one adapter: ROS 2 Jazzy + Nav2 + Gazebo.** Nav2 is the open-source navigation stack of ROS 2.
- **Later adapters, not built now:** Autoware (ROS 2, for vehicles; it mainly uses its own simulators rather than Gazebo) and a company's private stack (the company writes a small adapter: how to launch, where the configuration is, which topics mean what). Pointing into source code needs access to that code.
- **Privacy for private stacks:** navfail calls Meta's models through an API, so log extracts or code would leave the company. Meta's Llama models are open weights and could run on the company's own machines. Design decision for later.

The statements about Autoware and private stacks in this section are general knowledge, not taken from our research.

## 4. How people will use it

**Once, at setup:**
1. Install navfail: one Docker image with ROS 2, Nav2 and Gazebo, or a Python package on a machine that has them.
2. Point it at the robot's own repository: Nav2 configuration, maps, launch files, behaviour tree, and the Gazebo world and robot model if they have them.
3. Choose which failure types navfail handles (section 7), and provide the Meta model API key from an environment variable.

**When a failure happens:**

| # | Step | Who | Hackathon version | Full product |
| --- | --- | --- | --- | --- |
| 1 | The robot fails at a site ("Robot 7 stood at dock door 3 for a minute, 14:02") | customer | simulated by `reproduce/` | real robot |
| 2 | Someone reports it: robot, time, place, what was seen (the operator note) | customer or support | written by hand from the recorded runs | ticket or fleet tool |
| 3 | The engineer collects the incident folder from the robot (section 6) | engineer | recording, logs and configuration written by `reproduce/` | manual; a later `navfail collect` |
| 4 | `navfail investigate <incident folder>` | engineer | yes | yes |
| 5 | **Read:** a timeline from logs and recording (goal sent, planner failures, recoveries, where the robot stood and for how long) | navfail | yes | yes |
| 6 | **Sort:** match the symptom to a supported failure type; if none matches, say so and stop | navfail | yes | yes |
| 7 | **Reproduce:** rebuild the scene in simulation and run it N times: "reproduced k of N" or "not reproduced" | navfail | the site is already known (our simulation) | site rebuilt from the user's world or map |
| 8 | **Narrow down:** remove what does not matter, find the setting or code path that changes the outcome | navfail | yes | yes |
| 9 | **Point:** the configuration line or source line, with the evidence cited | navfail | yes | yes |
| 10 | **Check by rerun:** apply the change, rerun it next to an unchanged comparison run, report counts | navfail | yes | yes |
| 11 | **Report:** error, location, evidence, suggested change, replay package | navfail | yes | yes |
| 12 | The engineer reviews it, changes their repository, and keeps the incident as a regression test (`navfail replay` in CI) | engineer | replay only | yes |

Steps 5 to 11 are what the user sees navfail do; how it does them is for the agent's specification. The hard part for a real site is step 7: walls and fixed obstacles can be rebuilt from the map, but people and objects that are not on the map appear only in the sensor recording.

## 5. The incidents navfail starts from

Two incidents, each modelled on a real, dated, public report (listed in navfail `docs/REFERENCES.md`). Both are reproduced in simulation by one command, `bash reproduce/reproduce.sh incidents/<name>`. Only what an operator sees is written here. navfail is built for incident A first; incident B is the second failure type, added once A works.

### Incident A: the robot gets stuck in front of a doorway

- Modelled on a 2023 field report: a differential-drive robot on Nav2 stops at the threshold of a doorway at about half of all crossings and rotates back and forth; sometimes it frees itself after about 30 seconds, often it needs a joystick nudge. The reporter says it is not entirely solved.
- In navfail: a wall with a doorway on the TurtleBot 3 sandbox, Nav2's stock configuration. In 3 of 3 runs the robot stayed in one spot in front of the doorway for 47.2 to 65.4 s; 2 runs then got through, 1 failed with Nav2's "no valid path" error (`incidents/A-doorway/operator_note.md`). The report says about half of crossings; our layout produced it every time.
- Why it comes first: the robot's visible behaviour, standing in one spot, is easy to detect in the recording, and it varies from run to run the way field failures do.

### Incident B: the mission fails with "no valid path" after the robot manoeuvres on the spot

- Modelled on a 2025 public report.
- In navfail: in 3 of 3 runs the robot never sets off; it turns, pauses, backs up and turns again, and the mission fails after 17.5 to 19.0 s with Nav2's "no valid path" error, code 208 (`incidents/B-drop-off/operator_note.md`).

## 6. The incident folder: what navfail reads

The incident folder is what the person reporting a failure hands over: a standard set of files, in formats widely used with ROS 2 robots. In navfail's repository, `incidents/<name>/` holds more than that: `incident.json` (the simulated site) and each run's `groundtruth.csv` describe the simulation and are not something a reporter would have.

| Part | Format | In navfail's incidents today |
| --- | --- | --- |
| Recording: tf, odometry, velocity commands, lidar scan, localisation pose, plan, costmaps, behaviour-tree log, rosout, diagnostics, navigation action status | rosbag2 with MCAP files (MCAP is the default storage in ROS 2 Jazzy) | yes |
| Text logs | the launch output; on a real robot `~/.ros/log/` | yes (`nav2.log`) |
| Configuration | ROS parameter YAML, launch files, behaviour-tree XML | parameters yes; launch file and behaviour tree are Nav2's stock files and are not copied |
| Map | `map.yaml` + `map.pgm` (map_server format) | yes |
| Versions | installed package list; on a real robot also the git commit of the robot repository | packages yes |
| Operator note | short text: robot, time, place, what was seen | yes, written by hand (`operator_note.md`) |

Which of these files the agent is given is decided in the agent's specification. The agent gets only what the person reporting the failure hands over; it may run inside that person's project or in production.

## 7. Failure types

We collected 50 real, dated, public reports of Nav2 navigation failures; they fall into eight categories (`docs/RESEARCH.md` sections 2 and 3):

| # | Category | Entries |
| --- | --- | ---: |
| C1 | Footprint, inflation and tight gaps | 12 |
| C2 | Costmap not clearing or clearing wrongly | 8 |
| C3 | Controller tuning | 7 |
| C4 | Late, dynamic or unseen obstacle | 6 |
| C5 | Recovery loop or recovery collision | 6 |
| C6 | Planner path validity | 6 |
| C7 | Goal in or near an obstacle | 4 |
| C8 | Localisation near obstacles | 1 |

The user chooses which failure types navfail handles. navfail starts with one (Incident A) and adds types only after the first one works. The rest are on the to-do list.

## 8. Why this is hard today

- **Failures are intermittent.** Incident A's reporter saw it at about half of crossings. One run proves nothing; every claim needs several runs.
- **Each run is slow.** One simulated mission with start and shutdown took 32 to 93 s in our final runs (`result.json`, field `wall_s`), and one machine runs one simulator at a time.
- **A full investigation takes many runs.** Our estimate for a scene with five obstacles: 3 baseline runs, 3 to confirm the failure, 15 to 30 to shrink the scene, 20 for a final confirmation and 24 to compare two configurations, 65 to 80 runs in all. At our measured 32 to 93 s per run, that is about 0.6 to 2.1 hours of simulation for one failure.
- **No existing tool covers the whole investigation** (section 9).

## 9. What existing tools cover, and what they miss

Tools checked (`docs/RESEARCH.md` section 4): RoboVAST and Scenario Execution (scenario test frameworks for ROS 2), Nav2's own system tests, DDEnv and the reducers of Valle and Zeller (research methods that shrink a failing test), robot fuzzers (random test generators), LLM scenario generators, and industry tools; the closest industry tool on ROS 2 is scenario_simulator_v2, for Autoware.

| Step | Coverage today |
| --- | --- |
| Detect the failure | partial: collisions, aborts and timeouts are seen; a plan through an obstacle or a wrong costmap cell is not, because none of the listed tools is described as checking the plan or the costmap |
| Confirm by repeated runs | covered by some tools, only for what they detect |
| Shrink the scene to what matters | partial: one tool reduces obstacles, but on ROS 1 and without a licence; no tool is stated to shrink the time an obstacle appears, or a parameter file |
| Explain the failure | not covered: no tool produces an explanation |
| Compare two configurations with repeated runs and a control | partial: parameter variation exists, but no verdict from repeated runs and no control (the same configuration run against itself, to see how much results vary by chance) |
| Package the failure for replay | partial |
| Point to the configuration or source line | our reading: none of the listed tools is described as doing this |

The gap is per step, not per failure type: shrinking, explaining, comparing and packaging are not fully covered for any of the eight categories.

## 10. The environment of the hackathon version

- ROS 2 Jazzy, Nav2 1.3.13, Gazebo Sim 8 (Harmonic), on Ubuntu 24.04 under WSL2 on one Windows laptop.
- Robot: TurtleBot 3 Waffle, round, radius 0.22 m, 2D lidar.
- Site: Nav2's TurtleBot 3 sandbox, a small walled arena with pillars, with walls and fixtures added per incident, drawn into the site map as well. A more realistic warehouse site is on the to-do list.
- The true robot position comes from the simulator, independent of what the robot believes.
- Hackathon rule: navfail uses only Meta's models.

## 11. Not in this document

- How navfail works inside.
- What counts as solved (decided later).
- The cause of either incident.

## 12. Terms

| Term | Meaning |
| --- | --- |
| ROS 2 | Robot Operating System 2: the common open-source software framework for robots |
| Navigation stack | the software that plans and drives a robot to a goal; Nav2 is ROS 2's |
| Gazebo | the robot simulator used with ROS 2 |
| gdb, sanitizer | tools that run a program and report where it fails, with file and line |
| rosbag2, MCAP | ROS 2's recorder and its file format: every message on chosen topics, with timestamps |
| tf, odometry, lidar, localisation pose | where the robot's parts are; how far its wheels say it moved; its laser distance sensor; where it believes it is on the map |
| Costmap | Nav2's grid of where the robot may and may not go |
| Behaviour tree | the decision logic Nav2 follows: plan, drive, and what to try when that fails |
| Recovery | what Nav2 tries after a failure: turn on the spot, pause, back up |
| "No valid path" (code 208) | Nav2's error when its planner finds no route to the goal |
| Regression test, CI | a saved test rerun automatically on every change, to catch the failure coming back |
| Open weights | a model whose files can be downloaded and run on one's own machines |

## 13. About this repository

- **Hackathon:** Meta Global AI Developer Hackathon, 26 October to 4 November 2026.
- **Prepared before the hackathon:** the development environment (ROS 2 Jazzy, Nav2 and Gazebo under WSL2), learning the stack, and the reading on existing tools (24 and 25 October). This preparation is kept in a private repository; no code from it is copied here.
- **On the kickoff day, 26 October:** the collection of the 50 reported failures (summarised in `docs/RESEARCH.md`).
- **Built during the hackathon, from 27 October:** this problem statement, the analysis of categories and gaps, `docs/RESEARCH.md`, the reproduction tooling in `reproduce/` and the two incidents in `incidents/`.
- **AI coding assistant used:** Claude Code (Anthropic), for writing code and documents. navfail itself uses only Meta's models.
- **Licence:** Apache-2.0 (`LICENSE`); the files derived from Nav2 are listed in `NOTICE`.
