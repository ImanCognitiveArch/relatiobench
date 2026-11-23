# Security policy

## Supported version
The 0.1.0a1 engineering alpha is the current review target. There is no guaranteed
response time, production certification or long-term-support commitment.

## Reporting a vulnerability
Use this repository's GitHub **Security > Report a vulnerability** option if it
is available. Do not put exploit details, credentials or participant information
in a public issue. If private reporting is unavailable, open a minimal issue
requesting a private reporting channel without including sensitive details.
Maintainer: Iman Khorami.

Include the affected version, a minimal synthetic reproduction, expected and
observed behavior, and likely impact. Share only data you are permitted to share.

## Scope
RelatioBench reads local scenario/trace files and writes local outputs.
Do not run untrusted Python policies or treat a passing score as a security
boundary. Use synthetic or appropriately anonymized inputs. The tool is not a
sandbox, medical device, physical emergency stop, or clinical safety guarantee.
