"""Bag timeline extraction (EXPERIMENT.md section 6).

Reads poses from a rosbag2 MCAP bag (odometry preferred for its dense rate,
AMCL pose as fallback; AMCL alone gave only 36 poses for a 63 s recorded run)
and summarises them as numbers. This is the only motion evidence the agent
arm receives; groundtruth.csv is never used here. The pure summariser is
separate from the ROS-dependent reader so it tests without ROS sourced.
"""
import math
from pathlib import Path

from experiment.scoring import longest_still_ms

MAX_SAMPLES = 60


def summarize_timeline(points):
    """points: [(t_ms, x, y)] in time order. Returns counts and downsampled samples."""
    if not points:
        return {"points": 0, "duration_ms": 0, "longest_still_ms": 0,
                "travel_m": 0.0, "final": None, "samples": []}
    travel = sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(points, points[1:]))
    step = max(1, len(points) // MAX_SAMPLES)
    samples = [{"t_ms": t, "x": round(x, 3), "y": round(y, 3)}
               for t, x, y in points[::step]][:MAX_SAMPLES]
    return {
        "points": len(points),
        "duration_ms": points[-1][0] - points[0][0],
        "longest_still_ms": longest_still_ms(points),
        "travel_m": round(travel, 3),
        "final": [round(points[-1][1], 3), round(points[-1][2], 3)],
        "samples": samples,
    }


def extract_timeline(bag_dir):
    """Extract the pose timeline from a rosbag2 bag folder. Requires ROS 2 sourced."""
    try:
        import rosbag2_py
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
    except ImportError as e:
        raise RuntimeError(
            "bag timeline needs ROS 2 Python libraries: source /opt/ros/jazzy/setup.bash") from e
    bag_dir = Path(bag_dir)
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag_dir), storage_id="mcap"),
                rosbag2_py.ConverterOptions(input_serialization_format="cdr",
                                            output_serialization_format="cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    topic = "/odom" if "/odom" in types else "/amcl_pose"
    if topic not in types:
        raise RuntimeError(f"bag holds neither /odom nor /amcl_pose: {sorted(types)}")
    msg_type = get_message(types[topic])
    points, t0 = [], None
    while reader.has_next():
        name, data, stamp_ns = reader.read_next()
        if name != topic:
            continue
        msg = deserialize_message(data, msg_type)
        pose = msg.pose.pose
        if t0 is None:
            t0 = stamp_ns
        points.append(((stamp_ns - t0) // 1_000_000,
                       round(pose.position.x, 4), round(pose.position.y, 4)))
    summary = summarize_timeline(points)
    summary["topic"] = topic
    return summary
