#!/usr/bin/env python3
"""Check installation, or copy skills into project-local discovery folders."""
import argparse
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "office"))
from providers import status  # noqa: E402


def skills_dir(source):
    source = source.expanduser().resolve()
    if (source / "skills").is_dir():
        source = source / "skills"
    skills = sorted(folder for folder in source.iterdir()
                    if folder.is_dir() and (folder / "SKILL.md").is_file())
    if not skills or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item.name) for item in skills):
        raise ValueError("Choose an extracted library containing a skills folder with named SKILL.md files.")
    if any(path.is_symlink() for folder in skills for path in [folder, *folder.rglob("*")]):
        raise ValueError("Use a self-contained skill library with regular files and directories.")
    return skills


def install(args):
    skills = skills_dir(args.source)
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError("Create or choose an existing project folder with --workspace.")
    destinations = {
        "claude": (".claude/skills",), "codex": (".agents/skills",),
        "cursor": (".agents/skills",), "gemini": (".agents/skills",),
        "all": (".agents/skills", ".claude/skills"),
    }
    for name in destinations[args.provider]:
        target = workspace / name
        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        conflicts = []
        for folder in skills:
            destination = target / folder.name
            if destination.exists() or destination.is_symlink():
                conflicts.append(folder.name)
                continue
            shutil.copytree(folder, destination)
            copied += 1
        print(f"{target}: {copied} installed, {len(conflicts)} existing")
        if conflicts:
            print("Existing skills kept: " + ", ".join(conflicts))


def overlay(args):
    skills = skills_dir(args.source)
    required = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    if not required.issubset({folder.name for folder in skills}):
        raise ValueError("The Evolve overlay should contain every skill in this release. Import other libraries into their own workspaces.")
    parent = ROOT / ".office/libraries"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / "evolve"
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"An overlay already exists at {destination}. Move it to a backup folder to import a replacement.")
    with tempfile.TemporaryDirectory(prefix="import-", dir=parent) as temp:
        stage = Path(temp) / "evolve"
        (stage / "skills").mkdir(parents=True)
        for folder in skills:
            shutil.copytree(folder, stage / "skills" / folder.name)
        stage.rename(destination)
    print(f"Imported {len(skills)} full Evolve skill folders to {destination}.")


def doctor():
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    print(f"Bundled skill files: {len(list((ROOT / 'skills').glob('*/SKILL.md')))}")
    print("Scene packages:", "installed" if (ROOT / "node_modules/three").is_dir() else "run npm ci")
    for item in status():
        print(item["label"] + (": CLI found" if item["installed"] else ": optional CLI missing"))
    for tool in ("ollama", "ffmpeg"):
        print(tool + (": found" if shutil.which(tool) else ": optional, see docs/SETUP.md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check your local installation.")
    install_args = commands.add_parser("skills", help="Install into the selected project.")
    install_args.add_argument("provider", choices=("all", "codex", "claude", "cursor", "gemini"))
    install_args.add_argument("--workspace", type=Path, default=ROOT)
    install_args.add_argument("--source", type=Path, default=ROOT / "skills")
    overlay_args = commands.add_parser("import-evolve", help="Use your authorized full Evolve library in HQ.")
    overlay_args.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "skills":
            install(args)
        else:
            overlay(args)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
