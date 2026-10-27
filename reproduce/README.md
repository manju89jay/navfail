# reproduce: make a reported incident happen in simulation

Written 27 October 2026, during the hackathon. This folder reproduces an incident end to end and records everything about it. It does not investigate or explain anything.

## Run it

From a WSL Ubuntu terminal with ROS 2 Jazzy, Nav2 1.3.13 and Gazebo Harmonic installed:

```bash
cd /mnt/d/repo/navfail
bash reproduce/reproduce.sh incidents/A-doorway             # one run, headless
bash reproduce/reproduce.sh incidents/A-doorway --repeat 3  # three runs
bash reproduce/reproduce.sh incidents/A-doorway --gui       # with Gazebo and RViz, to watch
source /opt/ros/jazzy/setup.bash && python3 -m pytest -q -p no:cacheprovider reproduce/   # the tests
```

If you change an incident's walls, redraw its site map first: `python3 reproduce/make_map.py incidents/A-doorway`.

## An incident folder

| File | What | Would a reporter hand it over? |
| --- | --- | --- |
| `incident.json` | start, goal, walls of the simulated site, time budget, which deployed files to use | no: it builds the simulation |
| `operator_note.md` | what the operator saw, in plain words, written by hand from the runs | yes |
| `deployed/nav2_params.yaml` | the Nav2 configuration on the robot | yes |
| `deployed/map.yaml`, `map.pgm` | the site map the robot localises and plans on | yes |
| `runs/<stamp>/` | one folder per run (below) | partly (below) |

Which of these files an investigating agent receives is decided in the agent's specification, not here.

## One run's output

Simulation only, not something a reporter would have: `groundtruth.csv`, `world.sdf.xacro`, `robot.sdf.xacro`, and the `observed` and `teardown` parts of `result.json`.

| File | What |
| --- | --- |
| `result.json` | what happened (Nav2 result, Nav2's error code and message, reached the goal or not, longest time standing still and where), readiness time, how it ended, each teardown step, topics the recording missed, versions, SHA-256 of every input, and the error text if the runner failed |
| `nav2.log` | everything Nav2 and Gazebo printed |
| `bag/` | ros2 bag (MCAP): scan, odometry, velocity commands, plans, AMCL pose and particles, tf, map, both costmaps, behaviour-tree log, rosout, diagnostics, navigation action status and feedback |
| `groundtruth.csv` | the true robot position from the simulator, every 100 ms of simulated time. Only a simulation has this |
| `nav2_params.yaml`, `map.yaml`, `map.pgm` | the deployed files exactly as used |
| `world.sdf.xacro`, `robot.sdf.xacro` | the simulated site and robot |
| `bridge.log`, `bag.log` | helper process output |

## Specification

**Goal.** One command reproduces a reported incident in simulation, without knowing its cause, and leaves everything an engineer could ask for in one folder.

**Not in scope.** Finding, explaining or fixing the cause. Deciding which outputs an investigating agent receives (that is the agent's specification).

**Interface.** `bash reproduce/reproduce.sh <incident folder> [--gui] [--repeat N]`. One `RESULT` line per run. Exit codes: 0 clean; 2 a simulator was already running; 3 teardown left processes behind; 4 the runner failed or was stopped; 5 the host name or home folder was found in the run files. A series stops at the first non-zero run.

**How a run goes.**
1. Write the world (Nav2's stock TurtleBot 3 sandbox plus the incident's walls) and the robot (stock Waffle plus a pose publisher for the true position) into the run folder.
2. Launch Nav2's `tb3_simulation_launch.py` with those files and the deployed configuration and map, one process per server.
3. Ready means: the initial pose sent at once and every 2 s until AMCL answers, both Nav2 lifecycle managers active, clock, scan and true position arriving, then 2 s of simulated settling.
4. Start the recording and wait until it has subscribed to every topic, then send the goal and record the true position every 100 ms. Stop at Nav2's result, or cancel at the time budget, or at a wall-clock watchdog of budget + 60 s.
5. Close the recording (SIGINT), shut down Nav2 through its lifecycle managers, stop every process group (SIGTERM, then SIGKILL after 10 s), and check that nothing is left running. Every step runs even if an earlier one fails.
6. Replace the machine's name and the user's home folder with `<host>` and `<home>` in the saved logs and `result.json`, then search every file of the run, the bag included, for either; any hit is listed in `private_hits` and gives exit 5. The recorder runs inside the run folder, so the bag holds no absolute path.

**Checks, measured 27 October 2026, 3 runs per incident:**

| # | Check | A-doorway | B-drop-off |
| --- | --- | --- | --- |
| 1 | The command runs headless from start to finish and leaves no simulator process behind | pass: 3 of 3, `leftover` empty; in 1 run the launch group did not stop on SIGTERM within 10 s and was killed | pass: 3 of 3, `leftover` empty; every group stopped on SIGINT or SIGTERM |
| 2 | Each run folder holds `result.json`, `nav2.log`, a readable bag, `groundtruth.csv` and the deployed files | pass: 3 of 3; bags 14.2 to 14.9 MB | pass: 3 of 3; bags 4.6 to 5.4 MB |
| 3 | The recording covers the whole mission, including the action status and diagnostics | pass: 3 of 3 bags last as long as the mission or longer; no topic missing | same |
| 4 | The reported behaviour appears | pass: 3 of 3 stayed within 0.10 m of one spot in front of the doorway for at least 15 s (47.7 s, 47.2 s, 65.4 s); 2 then got through, 1 failed with code 208 | pass: 3 of 3 failed with code 208 after turning, pausing, backing up and turning again (17.5 s, 18.2 s, 19.0 s) |
| 5 | Nothing the reporter would hand over states a cause | pass: the deployed configuration is Nav2's stock file plus one attribution line; no links to the source reports (they are in `docs/REFERENCES.md`); the note states only what was seen. `incident.json` and the run's world file describe the simulated site and are not reporter files | pass: Nav2's stock configuration with the Smac 2D planner; otherwise as A |
| 6 | No host name or home folder in any run file, bag included | pass: `private_hits` empty in 3 of 3 | same |
| 7 | The unit tests pass | pass: 23 of 23, for `observe`, `sim_assets`, `procs`, `logs` and one teardown case. Each test failed before its code was written or fixed, except the teardown test, which was written after the code and checked by running it against the old teardown order, which fails it | same |

Not covered by any test yet: `run()` and `main()` end to end, the exit codes, the signal handling, `NOT_READY`, `NO_GOAL_REPLY` and the recorder timeout. They are on the to-do list.

Known limit: the recorder stores no message definition for `/navigate_to_pose/_action/status` and `/feedback` (`bag.log` says so). ROS 2 tools read them; tools that rely on the stored definition may not.

**Edge cases.**
- A simulator already running: refused before anything starts (exit 2).
- Nav2 never ready within 120 s, or simulated time stops during the 2 s settling: recorded as `NOT_READY`, then torn down.
- The goal gets no reply within 10 s: recorded as `NO_GOAL_REPLY`.
- The recorder has not subscribed to every topic within 15 s: the run goes on and `bag_missing_topics` lists what is missing.
- The runner crashes, or is stopped with Ctrl-C, SIGTERM or SIGHUP: teardown still runs with further signals ignored, `result.json` holds the error text, the result says `RUNNER_ERROR`, exit 4.
- A process group that ignores SIGTERM: SIGKILL after 10 s.

## Licences

navfail is Apache-2.0 (`LICENSE`). The files derived from Nav2's packages, and what was changed in them, are listed in `NOTICE`.
