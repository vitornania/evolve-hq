#!/usr/bin/env python3
"""Evolve HQ task intake and individual local workflow actions."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from office.activity import STATUSES, new_task, update


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "runtime/workflows.py"
CATALOG = json.loads((ROOT / "team/catalog.json").read_text(encoding="utf-8"))
ACTIONS = {action["id"]: action for action in CATALOG["actions"]}
ROLES = [role["name"] for role in CATALOG["roles"]]
SPRINT_STEPS = {
    "Chief of Staff": "Confirm the brief and choose the research method.",
    "Customer Researcher": "Collect dated customer evidence.",
    "Competitor Researcher": "Compare offers for the target market.",
    "Evidence Reviewer": "Review underlying sources and flag gaps.",
    "Ad Strategist": "Propose source-backed angles and test hypotheses.",
}
MEDIA_HELPERS = {
    "transcribe": ("edit", "transcribe_resolve.py"),
    "person-matte": ("matte", "make_resolve_person_matte.py"),
}


def write(path, text):
    path.write_text(text, encoding="utf-8")


def local_file(path):
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"File missing: {path}")
    return path


def stage_input(source, destination, action):
    if action == "storyboard":
        data = json.loads(source.read_text(encoding="utf-8"))
        for scene in data["scenes"]:
            if scene.get("image"):
                scene["image"] = str((source.parent / scene["image"]).resolve())
    elif action == "asset-handoff":
        data = json.loads(source.read_text(encoding="utf-8"))
        for entry in data:
            entry["asset"] = str((source.parent / entry["asset"]).resolve())
    else:
        shutil.copyfile(source, destination)
        return
    write(destination, json.dumps(data, indent=2) + "\n")


def run_local_runner(action, source, directory):
    runner = local_file(RUNNER)
    output = directory / action["output"]
    if action["id"] == "roas":
        # The batch runner also generates media analysis for metrics CSVs.
        # Reuse its report function to run the standalone calculation.
        spec = importlib.util.spec_from_file_location("evolve_runner", runner)
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        engine.report(source, output)
        return
    filename = next((name for name in action["inputs"] if Path(name).suffix == source.suffix.lower()), None)
    if filename is None:
        raise ValueError("Expected " + " or ".join(action["inputs"]))
    inbox = directory / "inbox"
    inbox.mkdir()
    stage_input(source, inbox / filename, action["id"])
    subprocess.run([sys.executable, str(runner), "run", "--inbox", str(inbox),
                    "--out", str(directory)], check=True)


def resolve_handoff(args, source, directory, assets):
    script = directory / f"approved-script{source.suffix}"
    shutil.copyfile(source, script)
    lines = [
        "# Resolve edit handoff", "",
        f"- Product: {args.product}",
        f"- Selected angle: {args.angle or 'Awaiting input'}",
        f"- Evidence IDs: {', '.join(args.evidence) or 'Awaiting input'}",
        f"- Approved script copy: {script.name}",
        "", "## Source assets", "",
        *([f"- {asset}" for asset in assets] or ["- Awaiting supplied footage."]),
        "", "## Edit plan", "",
        "1. Confirm the script, evidence, and source assets before editing.",
        "2. Transcribe the selected take. Create a person matte if the cut requires an overlay.",
        "3. Open the intended Resolve project and use a new timeline for the rough cut.",
        "4. Review script coverage, cuts, captions, crop, and audio before final export.",
        "",
    ]
    write(directory / "resolve-handoff.md", "\n".join(lines))


def run(args):
    action = ACTIONS[args.action]
    source = local_file(args.source)
    assets = [local_file(path) for path in args.asset]
    directory = new_task(args.product, args.action)
    record = directory / "RECORD.md"
    start = (f"# {action['title']}\n\n"
             f"- Product: {args.product}\n- Owner: {action['owner']}\n"
             f"- Source: {source}\n")
    write(record, start + "- Status: Working\n")
    try:
        update(record, action["title"], args.product, action["owner"],
               "working", f"Processing {source.name}", pid=os.getpid())
        output = directory / action["output"]
        if args.action == "resolve-handoff":
            resolve_handoff(args, source, directory, assets)
        elif args.action in MEDIA_HELPERS:
            env, script = MEDIA_HELPERS[args.action]
            environment = ROOT / ".office/envs" / env
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if not python.is_file():
                raise ValueError(f"Set up the optional {env} media environment using docs/SETUP.md.")
            subprocess.run([str(python), str(local_file(RUNNER.parent / script)),
                            str(source), str(output)], check=True)
        else:
            run_local_runner(action, source, directory)
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError(f"Expected output was not created: {output.name}")
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.CalledProcessError, KeyboardInterrupt) as error:
        status = "Interrupted" if isinstance(error, KeyboardInterrupt) else "Failed"
        write(record, start + f"- Status: {status}\n- Details: {error or status}\n")
        update(record, action["title"], args.product, action["owner"], status.lower(), str(error) or status)
        print(f"Task record: {record}", file=sys.stderr)
        raise
    write(record, start + f"- Status: Ready for review\n- Deliverable: {output.name}\n")
    update(record, action["title"], args.product, action["owner"], "review", f"Saved {output.name}")
    print(output)


def sprint(args):
    sources = [local_file(path) for path in args.source]
    directory = new_task(args.product, "research-sprint")
    record = directory / "RECORD.md"
    lines = [
        "# Market Research Team sprint", "",
        f"- Product: {args.product}", f"- Market: {args.market}",
        f"- Decision: {args.decision}", "- Status: Ready for assignment", "",
        "## Supplied sources", "",
        *([f"- {path}" for path in sources] or ["- No local files supplied."]),
        "", "## Steps", "",
        "1. Chief of Staff — confirm the brief and the applicable Evolve research method.",
        "2. Customer Researcher — collect dated customer evidence with source IDs.",
        "3. Competitor Researcher — compare offers and terms for the target market.",
        "4. Evidence Reviewer — verify findings and flag gaps before the brief uses them.",
        "5. Ad Strategist — propose up to three supported angles with test hypotheses.",
        "6. Chief of Staff — save the evidence, comparison, angles, and recommended decision here.",
        "", "Use the Evolve Ecommerce Market Research Team skill to run this sprint. Update this record as steps finish.",
        "",
    ]
    write(record, "\n".join(lines))
    for role, note in SPRINT_STEPS.items():
        update(record, "Market Research Team sprint", args.product, role, "queued", note)
    print(record)


def create_assignment(args):
    record = new_task(args.product, "assignment") / "RECORD.md"
    write(record, f"# {args.title}\n\n- Product: {args.product}\n- Owner: {args.role}\n\n{args.note}\n")
    update(record, args.title, args.product, args.role, "working", args.note)
    print(record)


def post_update(args):
    record = local_file(args.record)
    lines = record.read_text(encoding="utf-8").splitlines()
    title = next((line[2:] for line in lines if line.startswith("# ")), record.parent.name)
    product = next((line[len("- Product: "):] for line in lines if line.startswith("- Product: ")), "")
    update(record, title, product, args.role, args.status, args.note)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List the named workflow actions.")
    commands.add_parser("board", help="Build the standalone browser board.")
    action = commands.add_parser("run", help="Run a local workflow in its own task folder.")
    action.add_argument("action", choices=ACTIONS)
    action.add_argument("source", type=Path)
    action.add_argument("--product", required=True)
    action.add_argument("--angle", help="Selected angle for a Resolve handoff.")
    action.add_argument("--evidence", action="append", default=[], help="Evidence ID for a Resolve handoff.")
    action.add_argument("--asset", type=Path, action="append", default=[], help="Media file for a Resolve handoff.")
    research = commands.add_parser("sprint", help="Create a research sprint brief.")
    research.add_argument("--product", required=True)
    research.add_argument("--market", required=True)
    research.add_argument("--decision", required=True)
    research.add_argument("--source", type=Path, action="append", default=[])
    assignment = commands.add_parser("assign", help="Record the start of a role's assignment.")
    assignment.add_argument("--product", required=True)
    assignment.add_argument("--title", required=True)
    assignment.add_argument("--role", required=True, choices=ROLES)
    assignment.add_argument("--note", required=True)
    progress = commands.add_parser("update", help="Record a live status for a role on a task.")
    progress.add_argument("record", type=Path)
    progress.add_argument("--role", required=True, choices=ROLES)
    progress.add_argument("--status", required=True, choices=STATUSES)
    progress.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        if args.command == "list":
            for workflow in ACTIONS.values():
                print(f"{workflow['id']:<16} {workflow['desk']:<23} {workflow['title']}")
        elif args.command == "board":
            template = (ROOT / "board.html").read_text(encoding="utf-8")
            data = json.dumps(CATALOG).replace("<", "\\u003c")
            write(ROOT / "index.html", template.replace("__EVOLVE_HQ_CATALOG__", data))
            print(ROOT / "index.html")
        elif args.command == "run":
            if args.action != "resolve-handoff" and (args.angle or args.evidence or args.asset):
                action.error("--angle, --evidence, and --asset apply to resolve-handoff")
            run(args)
        elif args.command == "sprint":
            sprint(args)
        elif args.command == "assign":
            create_assignment(args)
        else:
            post_update(args)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
    except KeyboardInterrupt:
        parser.exit(130, "Interrupted.\n")


if __name__ == "__main__":
    main()
