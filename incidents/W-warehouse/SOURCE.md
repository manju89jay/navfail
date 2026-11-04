# Source of the failure under test

Public report: ros-navigation/navigation2 issue #4938,
"Differential Drive Robot Oscillates and Fails When Trying to Reach Final
Goal Orientation" — https://github.com/ros-navigation/navigation2/issues/4938

Symptom taken from that report: the robot drives to the goal position, then
oscillates while trying to achieve the final heading and fails with
progress errors.

Rebuild here (symptom rebuild, not the reporter's setup): a warehouse
shelf aisle 1.1 m wide in the TB3 sandbox. The goal sits near the end of
the aisle facing back the way the robot came (yaw pi), so the final turn
must happen between the shelves. The deployed configuration is Nav2 stock
(CostCritic.cost_weight 3.81); no setting is planted. The reporter's
controller was DWB; this stack uses MPPI — whether the symptom reproduces
at all is decided by the 5-run gate in SPEC-SANDBOX-TEST.md.

Seeded pick: seed 20261104 over a 3-issue shortlist (see
experiment/work/warehouse/PICK.json, recorded before any run).
