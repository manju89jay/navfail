"""The allowlist (EXPERIMENT.md section 4): the only settings a candidate may change.

Ranges are inclusive at both ends. Inflation settings write the local and the
global costmap together. Paths are key paths inside nav2_params.yaml.
"""

_MPPI = ("controller_server", "ros__parameters", "FollowPath")


def _costmap_paths(leaf):
    return [
        ("local_costmap", "local_costmap", "ros__parameters", "inflation_layer", leaf),
        ("global_costmap", "global_costmap", "ros__parameters", "inflation_layer", leaf),
    ]


SETTINGS = {
    "inflation_layer.inflation_radius": {
        "stock": 0.70, "min": 0.30, "max": 1.00, "paths": _costmap_paths("inflation_radius")},
    "inflation_layer.cost_scaling_factor": {
        "stock": 3.0, "min": 1.0, "max": 15.0, "paths": _costmap_paths("cost_scaling_factor")},
    "CostCritic.cost_weight": {
        "stock": 3.81, "min": 1.0, "max": 10.0, "paths": [_MPPI + ("CostCritic", "cost_weight")]},
    "PathAlignCritic.cost_weight": {
        "stock": 14.0, "min": 2.0, "max": 20.0, "paths": [_MPPI + ("PathAlignCritic", "cost_weight")]},
    "PathFollowCritic.cost_weight": {
        "stock": 5.0, "min": 1.0, "max": 10.0, "paths": [_MPPI + ("PathFollowCritic", "cost_weight")]},
    "PreferForwardCritic.cost_weight": {
        "stock": 5.0, "min": 0.0, "max": 10.0, "paths": [_MPPI + ("PreferForwardCritic", "cost_weight")]},
}


def validate_candidate(changes):
    """Return the changes dict unchanged, or raise ValueError before any run.

    A candidate changes 1 to 3 allowlisted settings, each value a real number
    inside its allowed range (bool is not a number here).
    """
    if not isinstance(changes, dict) or not 1 <= len(changes) <= 3:
        raise ValueError(f"candidate must change 1 to 3 settings, got {changes!r}")
    for setting, value in changes.items():
        spec = SETTINGS.get(setting)
        if spec is None:
            raise ValueError(f"setting not in allowlist: {setting!r}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"value for {setting} must be a number, got {value!r}")
        if not spec["min"] <= float(value) <= spec["max"]:
            raise ValueError(
                f"value for {setting} outside [{spec['min']}, {spec['max']}]: {value!r}")
    return changes
