# Incident A-doorway: operator's note

Written from the three recorded runs in `runs/` (27 October 2026).

- **Robot:** TurtleBot 3 Waffle, running Nav2 with the configuration in `deployed/nav2_params.yaml` and the site map in `deployed/map.yaml`.
- **Mission:** from the west room, start (-2.2, -0.55), through the doorway in the wall at x = -1.65, to the drop-off point (2.0, 0.5).
- **What I saw:** the robot moves about 0.2 m towards the doorway and stops just before it. It stays there and turns on the spot; in one run it also paused and backed up. Then either it goes through the doorway and completes the mission, or the mission fails without it ever getting through.
- **How long it stayed in one spot** (within 0.10 m, turning included): 47.7 s, 47.2 s and 65.4 s in the three runs.
- **How it ended:** 2 runs reached the drop-off point, 63.4 s and 63.9 s after the goal was sent; 1 run failed after 66.1 s with error code 208 (`NO_VALID_PATH`).
- **How often:** the robot got stuck in front of the doorway in 3 of 3 runs.
- **Impact:** missions through this doorway take far longer than they should or fail, and what happens varies from run to run.

How to see it again: `bash reproduce/reproduce.sh incidents/A-doorway` (headless) or add `--gui` to watch it.
