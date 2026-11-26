# RelatioBench 0.1.0a2 — Find the moment. Fix the boundary.

When a chatbot keeps offering a task after an explicit withdrawal, a score alone is not enough.
This alpha adds a complete local path from a reviewed annotated conversation to the offending
message, rule, suggested control change and a matched before/after regression check.

```sh
python -m pip install relatiobench==0.1.0a2
relatiobench quickstart --output boundary-demo
```

Open boundary-demo/before/index.html, then boundary-demo/after/index.html.
The included conversations are synthetic teaching examples: one offending message has two rule
findings; the corrected example retains eligible task completion and has zero findings.

- New: quickstart, audit and compare commands.
- Input: explicit human annotations; no hidden natural-language intent classifier.
- Output: self-contained escaped HTML, audit JSON, original trace contract and score JSON.
- Comparison: rejects changed user messages/events/annotations, recomputes scores,
  flags increased violation-code counts or reduced eligible completion.
- Existing replay/demo/score commands and trace/scorer v1 remain compatible.
- Local files, no account, upload, model key, ROS or third-party runtime dependencies.

[Annotation guide and first free bounded pilot](CHAT_AUDIT.md).
First pilot scope: up to 20 agreed synthetic scenarios, one private report and one review round;
access, scope and timing agreed first. No customer outcome, clinical validity, real operator
handoff or physical safety claims. Software remains an engineering alpha.

Validation evidence: evidence/chat-audit-windows.json.
That file records maintainer checks and isolated wheel installation, not independent evaluation.
CI and registry verification are recorded in the canonical owner pipeline after execution.
