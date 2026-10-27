"""Teardown keeps going when a step fails, so no process is left behind. Needs ROS 2 sourced (imports rclpy)."""
import subprocess

import run_incident  # imported as a module: pytest would treat a top-level name "teardown" as its own hook


class FailingNode:
    def shutdown_nav2(self):
        raise RuntimeError("lifecycle service crashed")

    def destroy_node(self):
        raise RuntimeError("already destroyed")


def group(cmd):
    return subprocess.Popen(["bash", "-c", cmd], start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_failing_steps_do_not_stop_the_rest():
    launch, bridge = group("sleep 30"), group("sleep 30")
    record = {}
    run_incident.teardown(record, bag=None, node=FailingNode(), launch=launch, bridge=bridge)
    td = record["teardown"]
    assert td["nav2_shutdown"].startswith("error:")
    assert td["node"].startswith("error:")
    assert td["launch"] == "SIGTERM"
    assert td["bridge"] == "SIGTERM"
    assert launch.poll() is not None and bridge.poll() is not None
    assert td["bag"] == "gone"
