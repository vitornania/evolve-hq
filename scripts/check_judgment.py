"""Run paired workflow briefs through HQ and compare the decisions with the supplied rubric."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
from skill_runs import get_run, start_run  # noqa: E402


def run_variant(case, variant, provider):
    run = start_run({
        "provider": provider,
        "product": case["product"],
        "brief": (case["brief"] + "\n" + variant["evidence"] +
                  "\nUse the supplied case and relevant skill methods only. "
                  "Do not open exercise fixtures, expected outcomes, or other task records."),
        "workflows": [{
            "workflow": case["workflow"], "mode": case["mode"], "stages": [case["stage"]],
        }],
    })
    print(f"Running {case['product']}: {run['id']}", flush=True)
    while run["status"] in {"working", "queued"}:
        time.sleep(1)
        run = get_run(run["id"])
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="Selected case names, or all six when omitted.")
    parser.add_argument("--provider", default="codex", help="A configured HQ provider.")
    args = parser.parse_args()
    cases = json.loads((ROOT / "examples/judgment-cases.json").read_text(encoding="utf-8"))
    unknown = set(args.cases).difference(cases)
    if unknown:
        parser.error("Unknown cases: " + ", ".join(sorted(unknown)))
    failed = False
    for name in args.cases or cases:
        case = cases[name]
        runs = [run_variant(case, variant, args.provider) for variant in case["variants"]]
        for index, (run, variant) in enumerate(zip(runs, case["variants"]), 1):
            step = run["steps"][0]
            print(f"\n{name} / {index}. HQ status: {step['status']}")
            note = step.get("judgment")
            if note:
                print(f"Decision: {note['choice']}")
                print(f"Evidence: {note['basis']}")
                print(f"Would reconsider if: {note['reconsiderIf']}")
            print(f"Read: {ROOT / 'tasks' / run['id'] / 'run.json'}")
            print(f"Check the actual decision: {variant['expect']}")
            if step["status"] not in variant.get("allowedStatuses", ["review"]):
                failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
