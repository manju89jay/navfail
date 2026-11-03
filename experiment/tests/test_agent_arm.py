"""Tests for the agent arm (EXPERIMENT.md section 6, SPEC check 1).

The Meta API is faked everywhere here; one real call is made only as a
manual smoke check, never in this suite. No simulator is started.
"""
import json
from pathlib import Path

import pytest

from experiment.agent_arm import CANDIDATE_SCHEMA, AgentProposer, make_meta_client
from experiment.allowlist import SETTINGS
from experiment.search import run_search

REPO = Path(__file__).resolve().parents[2]
VALID = {"changes": {"CostCritic.cost_weight": 3.81}, "reason": "restore stock cost weight"}


def fake_incident(tmp_path):
    incident = tmp_path / "incident"
    (incident / "deployed").mkdir(parents=True)
    (incident / "operator_note.md").write_text(
        "# note\nThe robot does not enter the corridor and stays in one spot.\n")
    (incident / "deployed" / "nav2_params.yaml").write_text(
        "controller_server:\n  ros__parameters:\n    FollowPath:\n"
        "      CostCritic:\n        cost_weight: 25.0\n")
    run = incident / "runs" / "20260101-000000"
    run.mkdir(parents=True)
    (run / "result.json").write_text(json.dumps({"observed": {"nav2_result": "CANCELED"}}))
    (run / "nav2.log").write_text(
        "INFO starting up\nERROR failed to make progress\nWARN controller patience exceeded\n"
        "INFO all quiet\nERROR no valid path found\n")
    (run / "bag").mkdir()
    return incident


def fake_timeline(bag_dir):
    return {"points": 3, "duration_ms": 20000, "longest_still_ms": 18000,
            "travel_m": 1.1, "final": [0.1, 0.0], "samples": [], "topic": "/odom"}


class QueueClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        return {"candidate": reply, "usage": {"input_tokens": 100, "output_tokens": 10}}


def make_proposer(tmp_path, replies):
    client = QueueClient(replies)
    proposer = AgentProposer(fake_incident(tmp_path), client=client, timeline_fn=fake_timeline)
    return proposer, client


def test_schema_covers_exactly_the_allowlist_with_ranges():
    props = CANDIDATE_SCHEMA["properties"]["changes"]["properties"]
    assert set(props) == set(SETTINGS)
    for setting, spec in SETTINGS.items():
        assert props[setting]["minimum"] == spec["min"]
        assert props[setting]["maximum"] == spec["max"]
    changes_schema = CANDIDATE_SCHEMA["properties"]["changes"]
    assert changes_schema["additionalProperties"] is False
    assert changes_schema["minProperties"] == 1
    assert changes_schema["maxProperties"] == 3


def test_valid_first_reply_is_returned_with_one_call(tmp_path):
    proposer, client = make_proposer(tmp_path, [VALID])
    assert proposer.propose([]) == VALID
    assert len(client.calls) == 1


def test_invalid_reply_is_retried_exactly_once(tmp_path):
    bad = {"changes": {"CostCritic.cost_weight": 25.0}, "reason": "planted value, out of range"}
    proposer, client = make_proposer(tmp_path, [bad, VALID])
    assert proposer.propose([]) == VALID
    assert len(client.calls) == 2
    assert "invalid" in client.calls[1][-1]["content"].lower()


def test_second_invalid_reply_counts_as_used_with_no_runs(tmp_path):
    bad = {"changes": {"CostCritic.cost_weight": 25.0}, "reason": "out of range"}
    proposer, client = make_proposer(tmp_path, [bad, bad])
    proposal = proposer.propose([])
    assert proposal["changes"] is None
    assert len(client.calls) == 2

    class OnceInvalid:
        def __init__(self):
            self.done = False

        def propose(self, history):
            if self.done:
                return None
            self.done = True
            return {"changes": None, "reason": "invalid output after one retry"}

    def no_runs(incident_dir, empty=False):
        raise AssertionError("an invalid proposal must not start a run")

    result = run_search("t", tmp_path / "work", OnceInvalid(), no_runs, budget=40)
    assert result["runs_used"] == 0
    assert result["candidates"][0]["status"] == "invalid"


def test_prompt_prefix_is_byte_stable_and_history_only_changes_the_suffix(tmp_path):
    proposer, _ = make_proposer(tmp_path, [VALID])
    first = proposer.build_messages([])
    second = proposer.build_messages([{"changes": VALID["changes"], "status": "not_proven",
                                       "site_passed": 2, "empty_passed": 0}])
    assert first[0] == second[0]  # system: rules + allowlist + deployed config
    assert first[1] == second[1]  # incident evidence: note + filtered log + timeline
    assert first[-1] != second[-1]  # only the history suffix differs


def test_prompt_holds_the_allowed_inputs_and_no_answer_key(tmp_path):
    proposer, _ = make_proposer(tmp_path, [VALID])
    prompt = "\n".join(m["content"] for m in proposer.build_messages([]))
    assert "does not enter the corridor" in prompt  # operator note
    assert "failed to make progress" in prompt       # filtered nav2.log
    assert "all quiet" not in prompt                 # info lines are filtered out
    assert "longest_still_ms" in prompt              # bag timeline numbers
    assert "cost_weight: 25.0" in prompt             # deployed config (an allowed input)
    assert '"cx"' not in prompt                      # incident.json walls are not given
    assert "groundtruth" not in prompt.lower()


def test_missing_api_key_stops_before_any_call(tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    proposer = AgentProposer(fake_incident(tmp_path), timeline_fn=fake_timeline)
    with pytest.raises(RuntimeError, match="MODEL_API_KEY"):
        proposer.propose([])


def test_usage_is_tracked_for_the_spend_guard(tmp_path):
    proposer, _ = make_proposer(tmp_path, [VALID, VALID])
    proposer.propose([])
    proposer.propose([])
    assert proposer.usage == {"input_tokens": 200, "output_tokens": 20}
    assert 0 < proposer.estimated_cost_usd() < 0.01


def test_meta_client_sends_structured_outputs_and_never_leaks_the_key():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": json.dumps(VALID)}}],
                               "usage": {"prompt_tokens": 5, "completion_tokens": 2}}).encode()

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.data)
        return FakeResponse()

    client = make_meta_client("test-key-not-a-secret", opener=fake_opener)
    out = client([{"role": "user", "content": "hello"}])
    assert out["candidate"] == VALID
    assert captured["url"] == "https://api.meta.ai/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key-not-a-secret"
    assert captured["body"]["model"] == "muse-wonder-1.0"
    assert captured["body"]["response_format"]["type"] == "json_schema"
    assert captured["body"]["reasoning_effort"] == "max"
    assert "test-key-not-a-secret" not in json.dumps(captured["body"])
    sent_schema = json.dumps(captured["body"]["response_format"])
    assert "maxProperties" not in sent_schema  # the Meta API rejects these keywords
    assert "minProperties" not in sent_schema
