"""Agent arm (EXPERIMENT.md section 6, SPEC check 1).

Muse Wonder 1.0 via the Meta Model API proposes one allowlisted candidate
as strict JSON. The prompt's stable prefix (system rules + allowlist +
deployed config, then the incident evidence) is byte-identical across the
proposals of one search; only the history suffix varies, so the prefix hits
the cached-input rate. The agent sees the operator note, the filtered
nav2.log, the bag timeline and the deployed config - never the incident
definition or any scoring answer key. Invalid output gets exactly one
retry, then the proposal counts as used with no runs.
"""
import json
import os
import urllib.request
from pathlib import Path

from experiment.allowlist import SETTINGS, validate_candidate
from experiment.timeline import extract_timeline

API_URL = "https://api.meta.ai/v1/chat/completions"
MODEL = "muse-wonder-1.0"
INPUT_USD_PER_TOKEN = 4 / 1_000_000
OUTPUT_USD_PER_TOKEN = 20 / 1_000_000

CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "object",
            "properties": {
                setting: {"type": "number", "minimum": spec["min"], "maximum": spec["max"]}
                for setting, spec in SETTINGS.items()
            },
            "additionalProperties": False,
            "minProperties": 1,
            "maxProperties": 3,
        },
        "reason": {"type": "string"},
    },
    "required": ["changes", "reason"],
    "additionalProperties": False,
}


def _filtered_log(log_path):
    """Only error/warning lines of nav2.log are evidence; info lines are noise."""
    if not log_path.exists():
        return ""
    lines = [line for line in log_path.read_text(errors="replace").splitlines()
             if "ERROR" in line or "WARN" in line or "FATAL" in line]
    return "\n".join(lines[:200])


class AgentProposer:
    def __init__(self, incident_dir, client=None, timeline_fn=extract_timeline):
        self.incident_dir = Path(incident_dir)
        self._client = client
        self._timeline_fn = timeline_fn
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def _get_client(self):
        if self._client is None:
            key = os.environ.get("MODEL_API_KEY")
            if not key:
                raise RuntimeError("MODEL_API_KEY is not set; the agent arm cannot call the model")
            self._client = make_meta_client(key)
        return self._client

    def build_messages(self, history):
        params = (self.incident_dir / "deployed" / "nav2_params.yaml").read_text()
        allowlist = "\n".join(
            f"- {setting}: stock {spec['stock']}, allowed {spec['min']} to {spec['max']}"
            for setting, spec in SETTINGS.items())
        system = (
            "You investigate one reproducible Nav2 navigation failure. Propose ONE "
            "configuration change as JSON: {\"changes\": {setting: value}, \"reason\": \"...\"}. "
            "Change 1 to 3 of these allowlisted settings, values inside the allowed ranges. "
            "Set every setting you do not change to null:\n"
            f"{allowlist}\n"
            "Nothing else may be changed. The deployed configuration under test is:\n"
            f"{params}")
        note = (self.incident_dir / "operator_note.md").read_text()
        runs = sorted((self.incident_dir / "runs").glob("*/")) \
            if (self.incident_dir / "runs").exists() else []
        log_text, timeline = "", {}
        if runs:
            log_text = _filtered_log(runs[-1] / "nav2.log")
            timeline = self._timeline_fn(runs[-1] / "bag")
        evidence = (
            f"Operator note:\n{note}\n"
            f"Filtered nav2.log (error/warning lines only):\n{log_text}\n"
            f"Bag timeline (numbers extracted by code):\n{json.dumps(timeline, indent=2)}")
        suffix = (
            "Candidates already tried in this search, with their run results as numbers:\n"
            f"{json.dumps(history, indent=2)}\n"
            "Propose the next candidate now.")
        return [{"role": "system", "content": system},
                {"role": "user", "content": evidence},
                {"role": "user", "content": suffix}]

    def propose(self, history):
        client = self._get_client()
        messages = self.build_messages(history)
        error = None
        for attempt in range(2):
            if attempt:
                messages = messages + [{
                    "role": "user",
                    "content": f"That candidate was invalid: {error}. "
                               "Propose a valid candidate inside the allowlist ranges."}]
            reply = client(messages)
            usage = reply.get("usage") or {}
            self.usage["input_tokens"] += usage.get("input_tokens", 0)
            self.usage["output_tokens"] += usage.get("output_tokens", 0)
            candidate = reply.get("candidate") or {}
            try:
                validate_candidate(candidate.get("changes"))
                if not isinstance(candidate.get("reason"), str):
                    raise ValueError("candidate reason must be a string")
            except ValueError as e:
                error = e
                continue
            return candidate
        return {"changes": None, "reason": f"invalid output after one retry: {error}"}

    def estimated_cost_usd(self):
        return (self.usage["input_tokens"] * INPUT_USD_PER_TOKEN
                + self.usage["output_tokens"] * OUTPUT_USD_PER_TOKEN)


def _api_schema(node):
    """Adapt CANDIDATE_SCHEMA to what the Meta structured-outputs API accepts.

    It rejects min/maxProperties (validate_candidate enforces 1-to-3 locally)
    and, in strict mode, requires every property in `required`; optional
    settings become nullable there and the client drops the nulls.
    """
    if not isinstance(node, dict):
        return node
    out = {k: _api_schema(v) for k, v in node.items()
           if k not in ("minProperties", "maxProperties")}
    if "properties" in out and "required" not in out:
        out["required"] = list(out["properties"])
        for prop in out["properties"].values():
            if isinstance(prop, dict) and "type" in prop:
                prop["type"] = [prop["type"], "null"]
    return out


def make_meta_client(api_key, opener=urllib.request.urlopen):
    """OpenAI-compatible chat client; the key travels only in the auth header."""
    def client(messages):
        body = {
            "model": MODEL,
            "messages": messages,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "candidate", "strict": True, "schema": _api_schema(CANDIDATE_SCHEMA)}},
            "reasoning_effort": "max",
        }
        request = urllib.request.Request(
            API_URL, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"})
        with opener(request) as response:
            payload = json.loads(response.read())
        candidate = json.loads(payload["choices"][0]["message"]["content"])
        if isinstance(candidate.get("changes"), dict):
            candidate["changes"] = {k: v for k, v in candidate["changes"].items()
                                     if v is not None}
        usage = payload.get("usage") or {}
        return {"candidate": candidate,
                "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                          "output_tokens": usage.get("completion_tokens", 0)}}

    return client
