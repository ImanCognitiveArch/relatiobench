# Reproduce the alpha

Supported requirement: Python >=3.11. Actually tested environments and artifact hashes belong in `evidence/acceptance.json`; do not infer coverage from this requirement.

1. Install development tools in a fresh virtual environment: `python -m pip install build`.
2. Run `python -m unittest discover -s tests -v`.
3. Run `python -m build`. Inspect the wheel and source distribution; package code should contain only the standalone package and fixtures.
4. Create another virtual environment outside this source tree, install the wheel with `python -m pip install --no-deps /absolute/path/to/wheel.whl`.
5. In that outside directory run `relatiobench demo --output ./demo-output`. Re-run and compare canonical traces/scores, not execution durations.
6. Repeat on Windows and Linux. Record interpreter version, commands, return codes, artifact SHA256 and fixture findings. CI is additional evidence only after a real successful run.

The demo generates six traces, six score files, one HTML report and a timing/equality record. Expected fixture results: respectful 0 violations, faulty 3, always-stop 0; respectful completion 2/2 and always-stop 0/2, for each context.

The contract tests exercise missing consent, refusal, terminal withdrawal, same-tick priority, pause/resume, malformed and replayed inputs, trace integrity, imported actions with spoofed policy identity, duplicate execution, HTML escaping, CLI exit codes and replay equality.

No network service is used by the runtime. Network-free verification can monkey-patch socket connections to raise while running the installed CLI; this verifies the tested execution path, not arbitrary user extensions.
