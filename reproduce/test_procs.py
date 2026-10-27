"""Tests for procs: stopping process groups and spotting simulator processes left behind."""
import os
import subprocess
import time

from procs import is_leftover, stop_group


def start(cmd):
    return subprocess.Popen(["bash", "-c", cmd], start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_group_that_obeys_sigterm_stops_without_sigkill_and_quickly():
    proc = start("sleep 30")
    t0 = time.monotonic()
    assert stop_group(proc, wait_s=3.0) == "SIGTERM"
    assert time.monotonic() - t0 < 2.0


def test_group_that_ignores_sigterm_is_killed():
    proc = start("trap '' TERM; sleep 30 & wait; sleep 30")
    time.sleep(0.3)
    assert stop_group(proc, wait_s=1.0) == "SIGKILL"
    try:
        os.killpg(proc.pid, 0)
        alive = True
    except ProcessLookupError:
        alive = False
    assert not alive


def test_already_finished_group_is_gone():
    proc = start("true")
    proc.wait()
    assert stop_group(proc) == "gone"
    assert stop_group(None) == "gone"


def test_leftover_names_cover_the_whole_simulation_stack():
    stack = [
        "/opt/ros/jazzy/lib/nav2_planner/planner_server --ros-args -r __node:=planner_server",
        "/opt/ros/jazzy/lib/nav2_controller/controller_server --ros-args",
        "/opt/ros/jazzy/lib/nav2_amcl/amcl --ros-args",
        "/opt/ros/jazzy/lib/nav2_bt_navigator/bt_navigator --ros-args",
        "/opt/ros/jazzy/lib/nav2_map_server/map_server --ros-args",
        "/opt/ros/jazzy/lib/nav2_lifecycle_manager/lifecycle_manager --ros-args",
        "/opt/ros/jazzy/lib/rviz2/rviz2 -d nav2_default_view.rviz",
        "ruby /opt/ros/jazzy/opt/gz_tools_vendor/bin/gz sim -r -s /tmp/nav2_x.sdf",
        "/usr/bin/python3 /opt/ros/jazzy/bin/ros2 launch nav2_bringup tb3_simulation_launch.py",
        "/usr/bin/python3 /opt/ros/jazzy/bin/ros2 bag record -o bag",
        "/opt/ros/jazzy/lib/ros_gz_bridge/parameter_bridge /model/turtlebot3_waffle/pose@x",
        "/opt/ros/jazzy/lib/opennav_docking/opennav_docking --ros-args",
        "/opt/ros/jazzy/lib/nav2_route/route_server --ros-args",
    ]
    for cmd in stack:
        assert is_leftover(cmd), cmd


def test_unrelated_processes_are_not_leftovers():
    for cmd in ["python3 /mnt/d/repo/navfail/reproduce/run_incident.py incidents/A-doorway",
                "bash reproduce.sh incidents/A-doorway", "/usr/bin/python3 -m pytest", "sleep 30"]:
        assert not is_leftover(cmd), cmd
