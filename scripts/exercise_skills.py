"""Exercise selected individual skills on fictional briefs through the normal HQ runner."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
from skill_runs import get_run, start_run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="One or more catalog skill IDs.")
    parser.add_argument("--all", action="store_true", help="Run every exercise in catalog order.")
    parser.add_argument("--provider", default="codex", help="A configured HQ provider.")
    args = parser.parse_args()
    cases = json.loads((ROOT / "examples/skill-quality-cases.json").read_text(encoding="utf-8"))
    if args.all == bool(args.skills):
        parser.error("Choose individual skill IDs or --all.")
    names = list(cases) if args.all else args.skills
    invalid = sorted(set(names) - cases.keys())
    if invalid:
        parser.error("Unknown skill IDs: " + ", ".join(invalid))
    for name in names:
        case = cases[name]
        run = start_run({
            "provider": args.provider, "product": f"Skill exercise {name}", "skills": [name],
            "brief": case["brief"] + "\nUse only the supplied case and relevant method files. "
                     "Treat the brief as a bounded exercise and return the requested decision. "
                     "Do not look up the fixture or its expected outcome.",
        })
        print(f"Running {name} in {run['id']}", flush=True)
        while run["status"] in {"working", "queued"}:
            time.sleep(.5)
            run = get_run(run["id"])
        result = run["steps"][0]
        print(f"HQ review: {result['status']}. {result.get('quality') or run.get('error', '')}")
        print(f"Open: {ROOT / 'tasks' / run['id'] / 'run.json'}")
        print(f"Compare the actual deliverable with this expected decision:\n{case['expect']}\n", flush=True)


if __name__ == "__main__":
    main()
