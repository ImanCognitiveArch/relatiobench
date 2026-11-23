"""Strict versioned input contract; reject ambiguous events before running policies."""
import hashlib
import json
from pathlib import Path


class ValidationError(ValueError):
    """The supplied artifact does not satisfy the public versioned contract."""


PRIORITY = {"WITHDRAW": 0, "PAUSE": 1, "CONSENT": 2, "RESUME": 3,
            "REQUEST_REVIEW": 4, "TASK": 5}
ACTIONS = {"ASK_CONSENT", "OFFER", "ACKNOWLEDGE", "PAUSE", "RESUME", "STOP", "REQUEST_REVIEW"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    """Content checksum, not a signature, tamper-proof log or authentication claim."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def fields(value, required, optional=()):
    require(isinstance(value, dict), "expected an object")
    require(set(required) <= value.keys(), "missing fields: " + ", ".join(sorted(set(required)-value.keys())))
    require(value.keys() <= set(required) | set(optional), "unknown fields: " + ", ".join(sorted(value.keys()-set(required)-set(optional))))


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def text(value):
    return isinstance(value, str) and 0 < len(value) <= 1000 and bool(value.strip())


def parse_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValidationError(f"invalid JSON constant: {x}")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValidationError(f"invalid JSON: {exc}") from exc


def validate_scenario(value):
    fields(value, {"schema_version", "id", "version", "session_id", "context", "title", "max_level", "events"})
    require(type(value["schema_version"]) is int and value["schema_version"] == 1, "unsupported scenario schema_version")
    for name in ("id", "version", "session_id", "context", "title"):
        require(text(value[name]), f"{name} must be nonempty text")
    require(integer(value["max_level"], 1) and value["max_level"] <= 10, "max_level must be an integer in 1..10")
    require(isinstance(value["events"], list) and 0 < len(value["events"]) <= 10000, "events must contain 1..10000 entries")
    ids, last_seq, last_tick = set(), 0, -1
    for event in value["events"]:
        fields(event, {"id", "seq", "tick", "session_id", "kind", "data"}, {"label"})
        require(text(event["id"]) and event["id"] not in ids, "event IDs must be nonempty and unique (duplicate/replayed event)")
        ids.add(event["id"])
        require(integer(event["seq"], 1) and event["seq"] > last_seq, "event seq must strictly increase (stale/out-of-order event)")
        require(integer(event["tick"]) and event["tick"] >= last_tick, "event ticks must not decrease")
        last_seq, last_tick = event["seq"], event["tick"]
        require(event["session_id"] == value["session_id"], "cross-session event is not permitted")
        require(isinstance(event["kind"], str) and event["kind"] in PRIORITY, "unknown event kind")
        if "label" in event:
            require(text(event["label"]), "label must be nonempty text")
        if event["kind"] == "CONSENT":
            fields(event["data"], {"granted"})
            require(type(event["data"]["granted"]) is bool, "consent granted must be boolean")
        elif event["kind"] == "RESUME":
            fields(event["data"], {"permitted"})
            require(type(event["data"]["permitted"]) is bool, "resume permitted must be boolean")
        elif event["kind"] == "TASK":
            fields(event["data"], {"level"})
            require(integer(event["data"]["level"], 1) and event["data"]["level"] <= 100, "task level must be an integer in 1..100")
        else:
            fields(event["data"], set())
    return value


def ordered_events(scenario):
    """Same-tick control events precede task actions; original IDs/seq remain intact."""
    return sorted(scenario["events"], key=lambda e: (e["tick"], PRIORITY[e["kind"]], e["seq"]))


def load_scenario(path):
    return validate_scenario(parse_json(Path(path).read_text(encoding="utf-8")))


def validate_trace(trace):
    fields(trace, {"schema_version", "engine_version", "scenario", "scenario_sha256", "policy", "seed", "actions"})
    require(type(trace["schema_version"]) is int and trace["schema_version"] == 1, "unsupported trace schema_version")
    require(text(trace["engine_version"]), "engine_version must be text")
    scenario = validate_scenario(trace["scenario"])
    require(trace["scenario_sha256"] == digest(scenario), "scenario checksum mismatch")
    fields(trace["policy"], {"id", "version"})
    require(all(text(v) for v in trace["policy"].values()), "policy id/version must be text")
    require(integer(trace["seed"]), "seed must be a nonnegative integer")
    require(isinstance(trace["actions"], list) and len(trace["actions"]) <= 100000, "invalid action list")
    positions = {e["id"]: i for i,e in enumerate(ordered_events(scenario))}
    last_event = -1
    for i, action in enumerate(trace["actions"], 1):
        fields(action, {"seq", "event_id", "kind"}, {"level"})
        require(type(action["seq"]) is int and action["seq"] == i, "action seq must be contiguous from 1")
        require(isinstance(action["event_id"], str) and action["event_id"] in positions, "action references an unknown event")
        position = positions[action["event_id"]]
        require(position >= last_event, "action references a stale/out-of-order event")
        last_event = position
        require(isinstance(action["kind"], str) and action["kind"] in ACTIONS, "unknown action kind")
        if action["kind"] == "OFFER":
            require("level" in action and integer(action["level"], 1), "OFFER requires a positive integer level")
        else:
            require("level" not in action, "only OFFER carries level")
    return trace
