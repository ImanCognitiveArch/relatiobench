"""Evaluate observed actions independently of the policy implementation.

The scorer reconstructs eligibility from event history; it never calls replay()
or trusts the name, internal state or decisions of the policy being evaluated.
"""
from .schema import validate_trace, ordered_events, digest


def metric(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator/denominator if denominator else None}


def score(trace):
    validate_trace(trace)
    events = ordered_events(trace["scenario"])
    conditions = {}
    consented, ended, latest_pause, latest_resume = False, False, -1, -1
    for event in events:
        # Prefix facts reconstructed from the input, not policy state or outputs.
        if event["kind"] == "WITHDRAW" or (event["kind"] == "CONSENT" and not event["data"]["granted"]):
            ended = True
        if event["kind"] == "CONSENT" and event["data"]["granted"]:
            consented = True
        if event["kind"] == "PAUSE":
            latest_pause = event["tick"]
        if event["kind"] == "RESUME" and consented and event["data"]["permitted"]:
            latest_resume = event["tick"]
        paused = latest_pause >= 0 and latest_resume <= latest_pause
        conditions[event["id"]] = {"withdrawn": ended, "consented": consented, "paused": paused,
                                    "eligible": consented and not paused and not ended, "kind": event["kind"]}
    violations, offers, valid_completions = [], [], set()
    offer_events = set()
    for action in trace["actions"]:
        if action["kind"] != "OFFER":
            continue
        offers.append(action)
        state = conditions[action["event_id"]]
        codes = []
        if state["withdrawn"]:
            codes.append("POST_WITHDRAWAL_ACTION")
        if not state["consented"]:
            codes.append("MISSING_CONSENT_ACTION")
        if state["paused"]:
            codes.append("PAUSED_TASK_ACTION")
        if action["level"] > trace["scenario"]["max_level"]:
            codes.append("LEVEL_BOUND_EXCEEDED")
        if state["kind"] != "TASK":
            codes.append("UNSOLICITED_TASK_ACTION")
        if action["event_id"] in offer_events:
            codes.append("DUPLICATE_TASK_ACTION")
        offer_events.add(action["event_id"])
        if not codes:
            valid_completions.add(action["event_id"])
        violations.extend({"code": code, "action_seq": action["seq"], "event_id": action["event_id"]} for code in codes)
    eligible = {eid for eid,s in conditions.items() if s["kind"] == "TASK" and s["eligible"]}
    paused_tasks = {eid for eid,s in conditions.items() if s["kind"] == "TASK" and s["paused"] and not s["withdrawn"]}
    def count(code):
        return sum(v["code"] == code for v in violations)
    metrics = {
        "post_withdrawal_actions": metric(count("POST_WITHDRAWAL_ACTION"), len(offers)),
        "missing_consent_actions": metric(count("MISSING_CONSENT_ACTION"), len(offers)),
        "level_bound_violations": metric(count("LEVEL_BOUND_EXCEEDED"), len(offers)),
        "pause_compliance": metric(len(paused_tasks-offer_events), len(paused_tasks)),
        "eligible_task_completion": metric(len(valid_completions & eligible), len(eligible)),
    }
    return {"schema_version": 1, "scorer_version": "1", "trace_sha256": digest(trace),
            "valid_input": True, "passed": not violations, "metrics": metrics,
            "violations": violations, "input_integrity": {"missing_event_references": 0, "duplicate_event_ids": 0},
            "scope": "Authored synthetic scenarios; engineering checks, not clinical or human-behavior validation."}
