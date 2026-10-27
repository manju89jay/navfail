"""Starting and stopping process groups, and spotting simulator processes left behind."""
import os
import signal
import subprocess
import time
from pathlib import Path

# Executables the simulation starts: Gazebo, the ROS 2 command line, the bridge, every Nav2 server
# (one process each with use_composition:=False), and RViz with --gui.
PROGRAMS = {
    "parameter_bridge", "robot_state_publisher", "component_container", "component_container_isolated",
    "controller_server", "planner_server", "smoother_server", "behavior_server", "bt_navigator",
    "waypoint_follower", "velocity_smoother", "collision_monitor", "opennav_docking", "route_server",
    "map_server", "amcl", "lifecycle_manager", "rviz2", "create",
}
COMMANDS = ("gz sim", "ros2 launch", "ros2 bag", "ros2 run")


def is_leftover(cmdline):
    """True if a process command line belongs to the simulation stack."""
    tokens = cmdline.split()
    if any(Path(t).name in PROGRAMS for t in tokens[:2]):
        return True
    return any(c in cmdline for c in COMMANDS)


def leftovers(own_pid):
    """Command lines of simulation processes still running, other than this one."""
    out = subprocess.run(["pgrep", "-a", "."], capture_output=True, text=True).stdout
    found = []
    for line in out.splitlines():
        pid, _, cmd = line.partition(" ")
        if pid != str(own_pid) and is_leftover(cmd):
            found.append(line)
    return found


def start_group(cmd, log_path, cwd=None):
    log = open(log_path, "w")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, cwd=cwd)


def group_alive(proc):
    proc.poll()  # reap the group leader once it has exited; an unreaped leader would count as alive
    try:
        os.killpg(proc.pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(proc, first=signal.SIGTERM, wait_s=10.0):
    """Signals the whole process group, waits, then SIGKILLs whatever is left.
    Returns "gone" (nothing to stop), the first signal's name (it was enough), or "SIGKILL"."""
    if proc is None or not group_alive(proc):
        return "gone"
    os.killpg(proc.pid, first)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if not group_alive(proc):
            return first.name
        time.sleep(0.1)
    os.killpg(proc.pid, signal.SIGKILL)
    deadline = time.monotonic() + 5.0
    while group_alive(proc) and time.monotonic() < deadline:
        time.sleep(0.1)
    return "SIGKILL"
