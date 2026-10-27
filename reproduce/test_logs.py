"""Tests for logs: the machine's name and the user's home folder are replaced in saved logs."""
from logs import private_hits, recorder_state, redact


def test_private_hits_finds_host_or_home_in_any_file_including_binary(tmp_path):
    (tmp_path / "bag").mkdir()
    (tmp_path / "bag" / "bag_0.mcap").write_bytes(b"\x00\x01recording to '/home/alice/x'\x00")
    (tmp_path / "nav2.log").write_text("clean\n")
    (tmp_path / "result.json").write_text('{"host": "host-pc"}\n')
    assert private_hits(tmp_path, host="host-pc", home="/home/alice") == ["bag/bag_0.mcap", "result.json"]


def test_private_hits_clean_folder(tmp_path):
    (tmp_path / "nav2.log").write_text("nothing private\n")
    assert private_hits(tmp_path, host="host-pc", home="/home/alice") == []


def test_recorder_state_reads_subscriptions_and_start():
    log = ("[INFO] [1.0] [rosbag2_recorder]: Subscribed to topic '/scan'\n"
           "[INFO] [1.1] [rosbag2_recorder]: Subscribed to topic '/navigate_to_pose/_action/status'\n"
           "[INFO] [1.2] [rosbag2_recorder]: Recording...\n")
    topics, recording = recorder_state(log)
    assert topics == {"/scan", "/navigate_to_pose/_action/status"}
    assert recording is True


def test_recorder_state_before_start():
    assert recorder_state("") == (set(), False)


def test_hostname_and_home_are_replaced_everywhere():
    text = "log in /home/alice/.ros/log/2026-10-27-17-00-00-host-pc-123\nhost-pc says hi /home/alice\n"
    out = redact(text, host="host-pc", home="/home/alice")
    assert "host-pc" not in out
    assert "/home/alice" not in out
    assert out.count("<host>") == 2
    assert out.count("<home>") == 2


def test_text_without_them_is_unchanged():
    text = "planner_server: no valid path found\n"
    assert redact(text, host="host-pc", home="/home/alice") == text


def test_empty_names_change_nothing():
    text = "abc"
    assert redact(text, host="", home="") == text
