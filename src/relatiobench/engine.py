"""Deterministic example policies; no transport, motor control, LLM or patient model."""
import copy
from .schema import ordered_events, validate_scenario, digest, require

POLICIES = ("respectful", "faulty", "always_stop")


def replay(scenario, policy="respectful", seed=0):
    validate_scenario(scenario)
    require(policy in POLICIES, f"unknown policy: {policy}")
    require(type(seed) is int and seed >= 0, "seed must be a nonnegative integer")
    consent, paused, withdrawn, pause_tick = False, False, False, -1
    actions = []

    def emit(event, kind, level=None):
        row = {"seq": len(actions)+1, "event_id": event["id"], "kind": kind}
        if level is not None:
            row["level"] = level
        actions.append(row)

    for event in ordered_events(scenario):
        kind, data = event["kind"], event["data"]
        if policy == "always_stop":
            emit(event, "STOP")
            continue
        if policy == "faulty":
            # Deliberately wrong fixture: ignore control state and requested bounds.
            emit(event, "OFFER", data["level"]) if kind == "TASK" else emit(event, "ACKNOWLEDGE")
            continue
        if withdrawn:
            emit(event, "STOP")
        elif kind == "WITHDRAW" or (kind == "CONSENT" and not data["granted"]):
            withdrawn = True
            emit(event, "STOP")
        elif kind == "PAUSE":
            paused, pause_tick = True, event["tick"]
            emit(event, "PAUSE")
        elif kind == "CONSENT":
            consent = True
            emit(event, "ACKNOWLEDGE")
        elif kind == "RESUME":
            if consent and data["permitted"] and event["tick"] > pause_tick:
                paused = False
                emit(event, "RESUME")
            else:
                emit(event, "ACKNOWLEDGE")
        elif kind == "REQUEST_REVIEW":
            emit(event, "REQUEST_REVIEW")
        elif not consent:
            emit(event, "ASK_CONSENT")
        elif paused:
            emit(event, "PAUSE")
        else:
            emit(event, "OFFER", min(data["level"], scenario["max_level"]))

    from . import __version__
    return {"schema_version": 1, "engine_version": __version__, "scenario": copy.deepcopy(scenario),
            "scenario_sha256": digest(scenario), "policy": {"id": policy, "version": "1"},
            "seed": seed, "actions": actions}
