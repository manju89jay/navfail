#!/usr/bin/env python3
"""Reproduces one incident end to end in simulation and records everything an engineer could ask for.

Run through reproduce.sh, which sources ROS 2 Jazzy:
  bash reproduce.sh ../incidents/A-doorway          # headless
  bash reproduce.sh ../incidents/A-doorway --gui    # with Gazebo and RViz windows

Each run writes <incident>/runs/<stamp>/: nav2.log, bag/ (what the robot saw and did), groundtruth.csv
(true position from the simulator), the deployed configuration and map as used, world.sdf.xacro and
robot.sdf.xacro (the simulated site), and result.json (what happened, timings, versions, file hashes).
"""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ManageLifecycleNodes
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Trigger
from tf2_msgs.msg import TFMessage

from logs import private_hits, recorder_state, redact
from observe import observe
from procs import leftovers, start_group, stop_group
from sim_assets import robot_with_pose_publisher, world_with_walls

SHARE = Path("/opt/ros/jazzy/share")
STOCK_WORLD = SHARE / "nav2_minimal_tb3_sim/worlds/tb3_sandbox.sdf.xacro"
STOCK_ROBOT = SHARE / "nav2_minimal_tb3_sim/urdf/gz_waffle.sdf.xacro"
ROBOT_NAME = "turtlebot3_waffle"
GT_TOPIC = f"/model/{ROBOT_NAME}/pose"
BAG_TOPICS = [
    "/scan", "/odom", "/cmd_vel", "/cmd_vel_nav", "/cmd_vel_smoothed", "/plan",
    "/amcl_pose", "/particle_cloud", "/tf", "/tf_static", "/map",
    "/global_costmap/costmap", "/local_costmap/costmap", "/behavior_tree_log", "/rosout", "/diagnostics",
    "/navigate_to_pose/_action/status", "/navigate_to_pose/_action/feedback",
]
READY_TIMEOUT_S = 120.0
SETTLE_SIM_MS = 2000
SETTLE_TIMEOUT_S = 15.0
RECORDER_TIMEOUT_S = 15.0
GOAL_REPLY_TIMEOUT_S = 10.0
TRACE_PERIOD_MS = 100
STATUS_NAMES = {GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED", GoalStatus.STATUS_CANCELED: "CANCELED",
                GoalStatus.STATUS_ABORTED: "ABORTED"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def yaw_quat(yaw):
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class Mission(Node):
    def __init__(self):
        super().__init__("navfail_incident", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.sim_ms = None
        self.scan_seen = False
        self.amcl_seen = False
        self.gt = None  # (x, y, yaw)
        self.nav2_error = None  # Nav2's error code and message from the NavigateToPose result
        self.create_subscription(Clock, "/clock", self._on_clock, 10)
        self.create_subscription(LaserScan, "/scan", lambda _: setattr(self, "scan_seen", True),
                                 qos_profile_sensor_data)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose",
                                 lambda _: setattr(self, "amcl_seen", True),
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                            durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(TFMessage, GT_TOPIC, self._on_gt, 10)
        self.initial_pub = self.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        self.nav = ActionClient(self, NavigateToPose, "navigate_to_pose")

    def _on_clock(self, msg):
        self.sim_ms = msg.clock.sec * 1000 + msg.clock.nanosec // 1_000_000

    def _on_gt(self, msg):
        for t in msg.transforms:
            if t.child_frame_id in (ROBOT_NAME, "") or len(msg.transforms) == 1:
                q = t.transform.rotation
                yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
                self.gt = (t.transform.translation.x, t.transform.translation.y, yaw)
                return

    def send_initial_pose(self, start):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = "map"
        msg.pose.pose.position.x, msg.pose.pose.position.y = start["x"], start["y"]
        msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = yaw_quat(start["yaw"])
        msg.pose.covariance[0] = msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.0685
        self.initial_pub.publish(msg)

    def manager_active(self, name):
        cli = self.create_client(Trigger, f"/{name}/is_active")
        try:
            if not cli.wait_for_service(timeout_sec=0.5):
                return False
            fut = cli.call_async(Trigger.Request())
            end = time.monotonic() + 2.0
            while not fut.done() and time.monotonic() < end:
                rclpy.spin_once(self, timeout_sec=0.05)
            return bool(fut.done() and fut.result() and fut.result().success)
        finally:
            self.destroy_client(cli)

    def wait_ready(self, start):
        """Initial pose at once and every 2 s until AMCL answers; both lifecycle managers active;
        clock, scan and true position arriving; then 2 s of simulated settling. None if not ready in time."""
        t0 = time.monotonic()
        last_pose = -10.0
        while time.monotonic() - t0 < READY_TIMEOUT_S:
            now = time.monotonic()
            if not self.amcl_seen and now - last_pose >= 2.0:
                self.send_initial_pose(start)
                last_pose = now
            rclpy.spin_once(self, timeout_sec=0.1)
            if (self.amcl_seen and self.scan_seen and self.gt is not None and self.sim_ms is not None
                    and self.manager_active("lifecycle_manager_localization")
                    and self.manager_active("lifecycle_manager_navigation")):
                settle_from, wall_end = self.sim_ms, time.monotonic() + SETTLE_TIMEOUT_S
                while self.sim_ms - settle_from < SETTLE_SIM_MS:
                    if time.monotonic() > wall_end:
                        return None  # simulated time stopped advancing
                    rclpy.spin_once(self, timeout_sec=0.05)
                return time.monotonic() - t0
        return None

    def wait_for_recorder(self, bag_log, topics):
        """Spins until the recorder has subscribed to every topic and says it is recording, or the
        timeout passes. Returns the topics it has not subscribed to."""
        end = time.monotonic() + RECORDER_TIMEOUT_S
        while True:
            subscribed, recording = recorder_state(bag_log.read_text() if bag_log.exists() else "")
            missing = sorted(set(topics) - subscribed)
            if (recording and not missing) or time.monotonic() > end:
                return missing
            rclpy.spin_once(self, timeout_sec=0.1)

    def drive(self, goal, budget_ms, watchdog_s):
        """Sends one NavigateToPose goal and records the true position every 100 ms of simulated time.
        Returns (Nav2 result name, trace, how it ended)."""
        if not self.nav.wait_for_server(timeout_sec=10.0):
            return "NO_ACTION_SERVER", [], "no_action_server"
        req = NavigateToPose.Goal()
        req.pose = PoseStamped()
        req.pose.header.frame_id = "map"
        req.pose.pose.position.x, req.pose.pose.position.y = goal["x"], goal["y"]
        req.pose.pose.orientation.z, req.pose.pose.orientation.w = yaw_quat(goal["yaw"])
        send = self.nav.send_goal_async(req)
        end = time.monotonic() + GOAL_REPLY_TIMEOUT_S
        while not send.done():
            if time.monotonic() > end:
                return "NO_GOAL_REPLY", [], "no_goal_reply"
            rclpy.spin_once(self, timeout_sec=0.05)
        handle = send.result()
        if not handle.accepted:
            return "REJECTED", [], "rejected"
        result = handle.get_result_async()
        t_zero = self.sim_ms
        trace, next_ms, wall0, ended = [], 0, time.monotonic(), "result"
        while not result.done():
            rclpy.spin_once(self, timeout_sec=0.02)
            t = self.sim_ms - t_zero
            if t >= next_ms and self.gt is not None:
                trace.append((t, round(self.gt[0], 4), round(self.gt[1], 4), round(self.gt[2], 4)))
                next_ms = t - t % TRACE_PERIOD_MS + TRACE_PERIOD_MS
            if t > budget_ms or time.monotonic() - wall0 > watchdog_s:
                ended = "budget" if t > budget_ms else "watchdog"
                cancel = handle.cancel_goal_async()
                end = time.monotonic() + 10.0
                while not (cancel.done() and result.done()) and time.monotonic() < end:
                    rclpy.spin_once(self, timeout_sec=0.05)
                break
        status = result.result().status if result.done() else None
        if result.done():
            self.nav2_error = {"code": int(result.result().result.error_code),
                               "message": result.result().result.error_msg}
        return STATUS_NAMES.get(status, f"STATUS_{status}"), trace, ended

    def shutdown_nav2(self):
        for name in ("lifecycle_manager_navigation", "lifecycle_manager_localization"):
            cli = self.create_client(ManageLifecycleNodes, f"/{name}/manage_nodes")
            if cli.wait_for_service(timeout_sec=1.0):
                req = ManageLifecycleNodes.Request()
                req.command = ManageLifecycleNodes.Request.SHUTDOWN
                fut = cli.call_async(req)
                end = time.monotonic() + 10.0
                while not fut.done() and time.monotonic() < end:
                    rclpy.spin_once(self, timeout_sec=0.05)
            self.destroy_client(cli)
        return "done"


def versions():
    out =subprocess.run(["dpkg-query", "-W", "ros-jazzy-navigation2", "ros-jazzy-nav2-bringup",
                          "ros-jazzy-nav2-minimal-tb3-sim", "ros-jazzy-ros-gz-bridge"],
                         capture_output=True, text=True).stdout
    vs = dict(l.split("\t", 1) for l in out.splitlines() if "\t" in l)
    gz = subprocess.run(["gz", "sim", "--version"], capture_output=True, text=True).stdout.strip()
    vs["gz sim"] = gz.splitlines()[0] if gz else "unknown"
    return vs


def teardown(record, bag, node, launch, bridge):
    """Every step runs even if an earlier one fails; each step's outcome is recorded."""
    td = record["teardown"] = {}

    def step(name, fn):
        try:
            td[name] = fn()
        except Exception as e:  # keep going: the remaining processes must still be stopped
            td[name] = f"error: {e!r}"

    step("bag", lambda: stop_group(bag, signal.SIGINT, 15.0))
    if node is not None:
        step("nav2_shutdown", node.shutdown_nav2)
        step("node", lambda: (node.destroy_node(), "done")[1])
    step("rclpy", lambda: (rclpy.shutdown(), "done")[1] if rclpy.ok() else "not running")
    step("launch", lambda: stop_group(launch))
    step("bridge", lambda: stop_group(bridge))
    step("leftover", lambda: leftovers(os.getpid()))


def run(incident_dir, stamp, gui, host, home):
    incident = json.loads((incident_dir / "incident.json").read_text())
    run_dir = incident_dir / "runs" / stamp
    run_dir.mkdir(parents=True)
    params = incident_dir / incident["deployed"]["params"]
    map_yaml = incident_dir / incident["deployed"]["map"]
    for f in (params, map_yaml, map_yaml.with_suffix(".pgm")):
        shutil.copy(f, run_dir / f.name)
    world = run_dir / "world.sdf.xacro"
    robot = run_dir / "robot.sdf.xacro"
    world.write_text(world_with_walls(STOCK_WORLD.read_text(), incident["walls"]))
    robot.write_text(robot_with_pose_publisher(STOCK_ROBOT.read_text()))
    start, goal = incident["start"], incident["goal"]
    budget_ms = int(incident["budget_s"]) * 1000

    record = {"incident": incident["id"], "stamp": stamp, "gui": gui, "versions": versions(),
              "files": {f.name: sha256(f) for f in (params, map_yaml, map_yaml.with_suffix(".pgm"),
                                                    incident_dir / "incident.json", world, robot)},
              "observed": {"nav2_result": "RUNNER_ERROR"}, "ended": "runner_error"}
    wall0 = time.monotonic()
    launch = bridge = bag = node = None
    try:
        launch = start_group([
            "ros2", "launch", "nav2_bringup", "tb3_simulation_launch.py",
            f"headless:={not gui}", f"use_rviz:={gui}", "use_sim_time:=True", "use_composition:=False",
            f"world:={world}", f"robot_sdf:={robot}", f"map:={run_dir / map_yaml.name}",
            f"params_file:={run_dir / params.name}",
            f"x_pose:={start['x']}", f"y_pose:={start['y']}", f"yaw:={start['yaw']}"], run_dir / "nav2.log")
        bridge = start_group(["ros2", "run", "ros_gz_bridge", "parameter_bridge",
                              f"{GT_TOPIC}@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V"], run_dir / "bridge.log")
        rclpy.init()
        node = Mission()
        ready_s = node.wait_ready(start)
        record["ready_s"] = None if ready_s is None else round(ready_s, 1)
        if ready_s is None:
            record["observed"], record["ended"] = {"nav2_result": "NOT_READY"}, "not_ready"
        else:
            # started inside the run folder with a relative output path, so no absolute path ends up in the bag
            bag = start_group(["ros2", "bag", "record", "--use-sim-time", "--include-hidden-topics",
                               "-o", "bag"] + BAG_TOPICS, run_dir / "bag.log", cwd=run_dir)
            record["bag_missing_topics"] = node.wait_for_recorder(run_dir / "bag.log", BAG_TOPICS)
            result, trace, ended = node.drive(goal, budget_ms, watchdog_s=incident["budget_s"] + 60)
            record["ended"] = ended
            record["nav2_error"] = node.nav2_error
            record["observed"] = observe(result, [(t, x, y) for t, x, y, _ in trace], (goal["x"], goal["y"]))
            with open(run_dir / "groundtruth.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t_ms", "x", "y", "yaw"])
                w.writerows(trace)
    except BaseException:  # a crash, Ctrl-C or SIGTERM/SIGHUP: record it, tear down, stop the series
        record["error"] = traceback.format_exc()
    finally:
        previous = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        try:  # no second signal may interrupt the teardown
            teardown(record, bag, node, launch, bridge)
            record["wall_s"] = round(time.monotonic() - wall0, 1)
            for log in run_dir.glob("*.log"):
                log.write_text(redact(log.read_text(errors="replace"), host, home))
            record["private_hits"] = private_hits(run_dir, host, home)
            (run_dir / "result.json").write_text(redact(json.dumps(record, indent=2), host, home) + "\n")
        finally:
            for s, handler in previous.items():
                signal.signal(s, handler)
    left = record["teardown"]["leftover"]
    o = record["observed"]
    print(f"RESULT {incident['id']} {stamp}: nav2={o.get('nav2_result')} reached={o.get('reached_goal')} "
          f"longest_still={o.get('longest_still_ms', 0) / 1000:.1f}s at={o.get('longest_still_at')} "
          f"ended={record['ended']} wall={record['wall_s']}s leftover={left if left else 0} "
          f"private={len(record['private_hits'])} -> {run_dir}", flush=True)
    if left != []:
        return 3
    if "error" in record:
        return 4
    return 5 if record["private_hits"] else 0


def stop_on_signal(signum, _frame):
    raise SystemExit(f"stopped by signal {signal.Signals(signum).name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("incident_dir", type=Path)
    ap.add_argument("--gui", action="store_true", help="show Gazebo and RViz (for watching only)")
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()
    for s in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, stop_on_signal)  # so teardown still runs when the runner itself is stopped
    found = leftovers(os.getpid())
    if found:
        print("A simulator is still running; stop it first:\n" + "\n".join(found), file=sys.stderr)
        return 2
    host, home = socket.gethostname(), os.path.expanduser("~")
    rc = 0
    for _ in range(args.repeat):
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        rc = run(args.incident_dir.resolve(), stamp, args.gui, host, home)
        if rc:
            reason = {3: "teardown left processes behind", 4: "the runner failed or was stopped",
                      5: "the host name or home folder was found in the run files"}[rc]
            print(f"Stopping the series: {reason} (exit {rc}).", file=sys.stderr)
            break
    return rc


if __name__ == "__main__":
    sys.exit(main())
