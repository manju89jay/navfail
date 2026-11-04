# Incident C-corridor is synthetic

This incident was made by us, not taken from a report. Its deployed configuration has one planted setting: the MPPI controller's `CostCritic.cost_weight` is 25.0 instead of Nav2's stock 3.81. With the stock value the robot drives through the 0.55 m corridor; with 25.0 it failed in 5 of 5 lab runs (28 October 2026).

It exists for the experiment in `docs/EXPERIMENT.md`, because no stock layout we tried gave a failure that an allowed setting can fix. This file and `incident.json` are not given to either arm of the experiment.
