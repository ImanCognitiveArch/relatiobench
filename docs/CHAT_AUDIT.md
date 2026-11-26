# Audit a conversation. Keep the evidence.
RelatioBench checks explicit interaction boundaries in **human-annotated** chat logs.
It runs locally, without an LLM key, upload, account, or runtime dependencies.

## First useful result
Python 3.11+ in a virtual environment:
```sh
python -m pip install relatiobench==0.1.0a2
relatiobench quickstart --output boundary-demo
```
Open `boundary-demo/before/index.html`, then `boundary-demo/after/index.html`.
The six-message synthetic example contains one offending message with **two rule findings**.
The corrected synthetic variant has zero findings and retains the one eligible task completion.
This is a teaching example, not proof a real chatbot was repaired.

## Use your own log
Copy `boundary-demo/before.chat.json`. Replace it with synthetic or authorized, redacted messages.
Preserve message order and assign a stable unique ID to each message. Review the annotations:
| Role | annotation | Meaning / extra fields |
| --- | --- | --- |
| user | consent | Explicit agreement for this session |
| user | task | An eligible task request; integer level required |
| user | pause | Suspend task offers |
| user | resume | Explicit permission to resume; cannot undo withdrawal |
| user | withdraw | End task delivery in this session |
| user | review_request | A request recorded, not an actual human handoff |
| assistant | task_offer | A task/promotion delivered; integer level and reply_to required |
| assistant | control_ack | Acknowledgment, not task delivery; reply_to required |
| assistant | stop | Recorded stop; reply_to required |
| assistant | review_recorded | Review event recorded; reply_to required |

Each assistant `reply_to` must identify the latest user message.
No assumed consent. No guessed labels. Unsupported system/tool turns and ambiguous labels fail explicitly:
preprocess into a reviewed supported log rather than silently dropping meaning.
Both task and offer levels must be positive integers; max_level is 1..10.
If the meaning does not fit this contract, do not label it as a pass.

```sh
relatiobench audit my.chat.json --output audit-before
```
Output: standalone `index.html`, `audit.json`, `trace.json`, `score.json`.
Exit 0 = supported rules pass; 1 = rule findings; 2 = invalid input/file failure.
Audit requires an empty output directory, protecting previous evidence from accidental overwrite.
The HTML includes message text; the JSON contains structural evidence without message content.
IDs may identify people too: redact IDs as well as text. Do not commit real customer logs or reports.

## Close the loop
Fix the chatbot or policy, collect a new observed log on the **same user events/session/limits**,
review its labels, and audit into a new directory. Keep policy.id stable and update policy.version.
```sh
relatiobench audit fixed.chat.json --output audit-after
relatiobench compare audit-before/audit.json audit-after/audit.json --output comparison.json
```
Compare exit 1 = any violation-code count increased **or** eligible task completion fell.
It recomputes stored scores and rejects different user-event contracts. Exit 0 means no regression
on these matched annotated inputs; it is not a certificate or a claim of real-world improvement.
Counts are findings per action/opportunity, not the percentage of customers or conversations.
Editing an annotation is not evidence that a product behavior changed. Record annotator/review provenance privately.

## What you can trust
Trace schema/scorer 1 remain unchanged. Text stays local. HTML escapes message content and loads no external assets.
No automatic language understanding, clinical assessment, emergency response, emotion measurement,
real operator-handoff verification, or physical safety guarantee is provided.
Use one supported rule and one known failure first. Keep ambiguous cases separate for expert review.

## First evaluator / free pilot
Run quickstart and send one installation obstacle or one incorrect/missing rule in
[an issue](https://github.com/ImanCognitiveArch/relatiobench/issues). Do not attach private logs.
The owner offers a first bounded pilot free of charge: up to 20 agreed synthetic scenarios,
one privately delivered report and one review round, after access, scope and timing are agreed.
Open an issue containing only the scenario type and desired boundary to discuss a private contact route.
No promise of reduced churn, a delivery deadline before scoping, or automatic production remediation.
