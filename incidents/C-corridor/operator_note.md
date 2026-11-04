# Incident C-corridor: operator's note

Written by us from the recorded runs in `runs/` (28 October 2026), in the form of an operator's report; no real operator was involved. This incident is synthetic (`SYNTHETIC.md`).

- **Robot:** TurtleBot 3 Waffle, running Nav2 with the configuration in `deployed/nav2_params.yaml` and the site map in `deployed/map.yaml`.
- **Mission:** from start (-2.2, -0.55), in front of a narrow corridor, to the drop-off point (2.0, 0.5).
- **What I saw:** the robot does not enter the corridor. It moves about 1.1 m to the north-east, stops near (-1.8, 0.53) and stays there; it turns on the spot, pauses and backs up, and never reaches the drop-off point.
- **How long it stayed in one spot** (within 0.10 m, turning included): 77.9 s, 88.6 s and 88.6 s in the three runs that started.
- **How it ended:** each mission was cancelled after 120 s without arrival; Nav2 reported "failed to make progress" about ten times per run.
- **How often:** 3 of 3 runs that started. One further run did not start (Nav2 not ready within the time limit); it is kept in `runs/` as a recorded start-up failure and not counted.
- **Impact:** missions from this start never arrive.

How to see it again: `bash reproduce/reproduce.sh incidents/C-corridor` (headless) or add `--gui` to watch it.
