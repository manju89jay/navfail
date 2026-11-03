"""Tests for the bag timeline extraction (EXPERIMENT.md section 6).

The timeline comes from the bag only (odometry/AMCL poses) - never from
groundtruth.csv, which the agent must not see.
"""
from pathlib import Path

import pytest

from experiment.timeline import summarize_timeline

REPO = Path(__file__).resolve().parents[2]


def test_summarize_reports_still_window_duration_and_travel():
    # still for 20 s at the origin, then drives 3 m in 10 s, sampled every 1 s
    points = [(k * 1000, 0.0, 0.0) for k in range(21)]
    points += [(21000 + k * 1000, 0.3 * (k + 1), 0.0) for k in range(10)]
    summary = summarize_timeline(points)
    assert summary["points"] == 31
    assert summary["duration_ms"] == 30000
    assert summary["longest_still_ms"] == 20000
    assert summary["travel_m"] == 3.0
    assert summary["final"] == [3.0, 0.0]


def test_summarize_empty_timeline():
    summary = summarize_timeline([])
    assert summary == {"points": 0, "duration_ms": 0, "longest_still_ms": 0,
                       "travel_m": 0.0, "final": None, "samples": []}


def test_summarize_downsamples_to_at_most_60_samples():
    points = [(k * 100, float(k), 0.0) for k in range(600)]
    summary = summarize_timeline(points)
    assert len(summary["samples"]) <= 60
    assert summary["samples"][0]["t_ms"] == 0


def test_extract_timeline_from_recorded_A_bag():
    pytest.importorskip("rosbag2_py", reason="ROS 2 Python libraries not sourced")
    from experiment.timeline import extract_timeline

    bag_dir = REPO / "incidents" / "A-doorway" / "runs" / "20261027-225219" / "bag"
    summary = extract_timeline(bag_dir)
    assert summary["points"] > 100
    assert summary["duration_ms"] > 30000
    # incident A stood still for at least 15 s in every recorded run (README section 5)
    assert summary["longest_still_ms"] >= 15000
