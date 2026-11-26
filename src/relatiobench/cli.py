"""Command-line entry points; no network access or external service is required."""
import argparse
import json
import sys
import time
from importlib.resources import files
from pathlib import Path
from . import __version__
from .engine import replay, POLICIES
from .schema import ValidationError, load_scenario, parse_json, validate_scenario, canonical
from .scoring import score


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def demo(output):
    from .report import render
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    comparisons, evidence = [], []
    for name in ("social_robot", "virtual_roleplay"):
        scenario = validate_scenario(parse_json(files("relatiobench").joinpath(f"scenarios/{name}.json").read_text(encoding="utf-8")))
        runs = []
        for policy in POLICIES:
            started = time.perf_counter()
            trace = replay(scenario, policy, seed=7)
            result = score(trace)
            elapsed = time.perf_counter()-started
            same = canonical(trace) == canonical(replay(scenario, policy, seed=7))
            write_json(output/f"{name}-{policy}.trace.json", trace)
            write_json(output/f"{name}-{policy}.score.json", result)
            runs.append({"trace": trace, "score": result})
            evidence.append({"context": name, "policy": policy, "replay_equal": same,
                             "execution_seconds": elapsed, "passed": result["passed"],
                             "violations": len(result["violations"])})
        comparisons.append({"scenario": scenario, "runs": runs})
    (output/"index.html").write_text(render(comparisons), encoding="utf-8")
    write_json(output/"demo-evidence.json", {"version": __version__, "python": sys.version,
               "synthetic": True, "runs": evidence, "duration_note": "Execution only; excludes installation/setup; not part of deterministic equality."})
    print(f"RelatioBench {__version__} | synthetic fixtures | no network/LLM/ROS required")
    for row in evidence:
        print(f"{row['context']:18} {row['policy']:12} violations={row['violations']} replay_equal={row['replay_equal']}")
    print(f"Report: {(output/'index.html').resolve()}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="relatiobench", description="Replay the interaction. Inspect the decision.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("demo", help="Generate two synthetic contexts and policy comparisons")
    p.add_argument("--output", default="./demo-output")
    p = sub.add_parser("quickstart", help="Create and audit synthetic before/after chat examples")
    p.add_argument("--output", default="./boundary-demo")
    p = sub.add_parser("audit", help="Audit explicitly annotated chat JSON; no intent inference")
    p.add_argument("chat"); p.add_argument("--output", required=True)
    p = sub.add_parser("compare", help="Compare audit.json files on identical user inputs")
    p.add_argument("before"); p.add_argument("after"); p.add_argument("--output")
    p = sub.add_parser("run", help="Replay a versioned scenario")
    p.add_argument("scenario"); p.add_argument("--policy", choices=POLICIES, default="respectful")
    p.add_argument("--seed", type=int, default=0); p.add_argument("--output", required=True)
    p = sub.add_parser("score", help="Independently score an exported/imported trace")
    p.add_argument("trace"); p.add_argument("--output")
    p = sub.add_parser("validate", help="Validate scenario schema, sequence and sessions")
    p.add_argument("scenario")
    try:
        args = parser.parse_args(argv)
        if args.command == "demo":
            return demo(args.output)
        if args.command in ("quickstart", "audit", "compare"):
            from .audit import sample, write_audit, compare_audits
            from .schema import require
            if args.command == "quickstart":
                import copy
                output = Path(args.output)
                require(not output.exists() or not any(output.iterdir()), "output directory must be empty")
                before = sample()
                after = copy.deepcopy(before)
                after["policy"]["version"] = "after"
                after["messages"] = after["messages"][:-1]
                write_json(output/"before.chat.json", before)
                write_json(output/"after.chat.json", after)
                b = write_audit(before, output/"before")
                a = write_audit(after, output/"after")
                write_json(output/"comparison.json", compare_audits(b, a))
                print("SYNTHETIC annotated examples: before=2 findings; after=0. Not a live chatbot test.")
                print(f"Open: {(output/'before'/'index.html').resolve()}")
                print(f"Then: {(output/'after'/'index.html').resolve()}")
                print("Edit a copy of before.chat.json for your own explicitly labeled log; guide: https://github.com/ImanCognitiveArch/relatiobench/blob/main/docs/CHAT_AUDIT.md")
                return 0
            if args.command == "audit":
                result = write_audit(parse_json(Path(args.chat).read_text(encoding="utf-8")), args.output)
                print(f"Findings: {len(result['findings'])} | report: {(Path(args.output)/'index.html').resolve()}")
                print("Local only. Human annotations; supported rules only. Exit 1 means findings.")
                return 0 if result["score"]["passed"] else 1
            result = compare_audits(
                parse_json(Path(args.before).read_text(encoding="utf-8")),
                parse_json(Path(args.after).read_text(encoding="utf-8")))
            if args.output:
                write_json(args.output, result)
            print(json.dumps(result, indent=2))
            return 1 if result["regression"] else 0
        if args.command == "run":
            write_json(args.output, replay(load_scenario(args.scenario), args.policy, args.seed))
            return 0
        if args.command == "validate":
            scenario = load_scenario(args.scenario)
            print(f"Valid: {scenario['id']} v{scenario['version']} ({len(scenario['events'])} events)")
            return 0
        result = score(parse_json(Path(args.trace).read_text(encoding="utf-8")))
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
