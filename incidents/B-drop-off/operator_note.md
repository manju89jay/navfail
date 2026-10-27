# Incident B-drop-off: operator's note

Written from the three recorded runs in `runs/` (27 October 2026).

- **Robot:** TurtleBot 3 Waffle, running Nav2 with the configuration in `deployed/nav2_params.yaml` and the site map in `deployed/map.yaml`.
- **Mission:** from start (-2.0, -0.5) to the drop-off point (1.75, -0.55).
- **What I saw:** the robot never sets off towards the drop-off point. It turns on the spot, pauses, backs up a little, turns on the spot again, and then the mission fails.
- **What the system reported:** the mission failed with error code 208 (`NO_VALID_PATH`); the planner log says "no valid path found" again and again.
- **How long until it failed:** 17.5 s, 18.2 s and 19.0 s after sending the goal.
- **How often:** 3 of 3 runs, the same sequence each time.
- **Impact:** the mission fails only after the robot has spent this time manoeuvring, and the error does not say why there is no path.

How to see it again: `bash reproduce/reproduce.sh incidents/B-drop-off` (headless) or add `--gui` to watch it.
