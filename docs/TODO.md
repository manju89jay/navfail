# navfail: to-do list (after the first version works)

Written 27 October 2026. Nothing here is planned yet; items are picked from it once incident A works end to end.

## Site

- **Realistic warehouse site.** Recommendation: Nav2's own warehouse world (`nav2_minimal_tb4_sim`, 30 × 50 m, shelf rows and aisles, a pallet, people models; map `nav2_bringup/maps/warehouse.yaml`), already installed. Before using it, a 20-minute check: launch it headless with our robot, measure start-up time and real-time speed on the laptop, and check the licence of each model it downloads from Gazebo Fuel (it needs internet on the first run). Alternative: Nav2's depot world (30 × 15 m). Later: generated layouts (racks, aisles, doors, docks from a few numbers, world and map written together) for variety, since existing tools are stronger than navfail at testing many environments.
- **Robot size.** Real warehouse robots are usually larger than the TurtleBot 3 (0.44 m); decide whether to model a larger footprint.
- **The runner reads world and map from `incident.json`** instead of the sandbox being fixed in the code (needed for any other site).

## Failure types (IDs refer to the table in `docs/RESEARCH.md`)

- Contact or lost clearance from inflation or footprint settings (P10, Q04, Q14, P11).
- Controller stall beside an obstacle (P13, P14; Q02, Q07, Q08 need DWB).
- Late box blocks the route (P07, N12, N34); needs boxes spawned at a chosen time.
- Back-and-forth near an obstacle (N39, P12); needs a back-and-forth rule.
- Obstacle the costmap never marks (Q01, N13).
- Planner path through an obstacle, or a false "no path" (N18, N01, N02, N26).
- Recovery loop (N19).
- Stale or ghost costmap cell (N23, N33, Q03, N36); needs boxes that can be removed.
- Localisation loss near obstacles (P06); needs a long corridor and people.

## Incidents

- Incident A: contrast runs (details kept privately with the incident's answer).
- Incident B: contrast runs (details kept privately with the incident's answer).

## Reproduction runner (from the 27 October reviews, "can wait")

- Decide the reporter / simulation split on disk: today `incidents/<name>/` mixes reporter files (note, deployed configuration and map, logs, bag) with simulation files (`incident.json`, world and robot files, `groundtruth.csv`) that show the site layout. Option: move the simulation files to `reproduce/scenarios/`. Belongs to the agent's specification (which files the agent receives).
- A run that ends `NOT_READY` or `NO_GOAL_REPLY` exits 0, so a script cannot tell it from a clean reproduction.
- `result.json` has no runner version or commit; hashes cover inputs but not the code or the stock source files.
- Tests for `run()` and `main()` end to end with fake processes (exit codes, signals, `NOT_READY`, `NO_GOAL_REPLY`, recorder timeout, redaction applied), `make_map.py`, and boundary cases of `observe.py` and `sim_assets.py`.
- A signal arriving between a process start and its assignment could leave that group untracked; `versions()` runs before the protected block, so a failure there leaves a run folder without `result.json`.
- `redact()` is a plain text replace, also inside hashes in `result.json`; a very short host name could alter them.
- `stop_group` reports "SIGKILL" even if the group survived the kill (the leftover check still catches it).
- `is_leftover` matches "ros2 launch", "ros2 run" and "gz sim" anywhere in a command line, so an unrelated command can cause a false refusal.
- `dpkg-query`, `gz sim --version` and `pgrep` are called without a time limit.
- The bag stores no message definition for the navigation action's status and feedback topics.
- A root `README.md` for the first public commit (the problem statement).
- Six bags of about 5 to 15 MB each go into git history as plain binaries; consider Git LFS later.
- `parse_pgm` loops forever on a truncated header.
- Same-second stamp collision with `--repeat`; `--repeat 0`; missing incident folder gives a traceback.
- `ROS_DOMAIN_ID` not set; another ROS stack on the machine could interfere.
- Rolling recording on a real robot (keep the last minutes, save on error): check how ROS 2's recorder supports it.

## Product, beyond the hackathon

- Autoware adapter; private-stack adapter interface.
- `navfail collect`: gather the incident folder from a robot.
- Privacy design for private stacks (local Llama models).
- How a pointer confirmed by reruns is worded (versus the "hypotheses only" rule).
- What "solved" means.
