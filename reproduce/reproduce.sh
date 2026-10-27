#!/usr/bin/env bash
# Reproduces one incident in simulation. Run from WSL Ubuntu:
#   bash reproduce.sh ../incidents/A-doorway [--gui] [--repeat N]
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
exec python3 "$HERE/run_incident.py" "$@"
