# References: the public reports the incidents are modelled on

Kept outside `incidents/`, because an incident folder holds only what the person reporting a failure would hand over.

| Incident | Modelled on | Date | How close our reproduction is |
| --- | --- | --- | --- |
| `incidents/A-doorway` | Q06: "Helping diff drive robot get through doorways", Robotics Stack Exchange, https://robotics.stackexchange.com/questions/103181/helping-diff-drive-robot-get-through-doorways | 12 April 2023 | similar visible symptom (the robot stalls at a doorway), but in a doorway only a few centimetres wider than the robot, in 3 of 3 runs instead of about half; same cause not verified |
| `incidents/B-drop-off` | N38: Nav2 issue 5566, https://github.com/ros-navigation/navigation2/issues/5566 | 30 September 2025 | same area (a goal inside an obstacle, with a goal tolerance above zero), different symptom: our planner fails quickly instead of working towards the goal |

The IDs Q06 and N38 refer to the table of 50 reported failures in `docs/RESEARCH.md`.
