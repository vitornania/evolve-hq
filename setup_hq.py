#!/usr/bin/env python3
"""Check installation, or copy skills into project-local discovery folders."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
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


def native_fingerprint(folder):
    """Hash the complete skill tree, including extra files and empty directories."""
    digest = hashlib.sha256()
    for item in sorted(folder.rglob("*"), key=lambda p: p.relative_to(folder).as_posix()):
        if item.is_symlink() or not (item.is_file() or item.is_dir()):
            return None
        digest.update(item.relative_to(folder).as_posix().encode() + b"\0")
        if item.is_dir():
            digest.update(b"D")
        else:
            contents = hashlib.sha256()
            with item.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    contents.update(chunk)
            digest.update(b"F" + contents.digest())
    return digest.hexdigest()


@contextmanager
def native_lock(state):
    """OS releases this advisory install lock if the installer stops."""
    if state.is_symlink():
        raise ValueError(f"Cannot store installer state in a linked directory: {state}")
    state.mkdir(exist_ok=True)
    lock = state / "install.lock"
    if lock.is_symlink():
        raise ValueError(f"Cannot use a linked installer lock: {lock}")
    with lock.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def install_native(folder, target, state, legacy):
    destination = target / folder.name
    marker = state / (folder.name + ".sha256")
    managed = legacy is not None
    if destination.is_symlink() or marker.is_symlink():
        return "kept"
    exists = destination.exists()
    if exists and (not managed or not destination.is_dir()):
        return "kept"
    source_hash = native_fingerprint(folder) if managed else None
    if managed and source_hash is None:
        raise ValueError(f"Cannot fingerprint the bundled skill {folder.name}.")
    old_hash = None
    if exists:
        old_hash = native_fingerprint(destination)
        recorded = marker.read_text(encoding="ascii").strip() if marker.is_file() else ""
        if old_hash is None or (old_hash != source_hash and old_hash != recorded and old_hash not in legacy):
            return "kept"
        if old_hash == source_hash and old_hash == recorded:
            return "current"

    temp = Path(tempfile.mkdtemp(prefix="stage-", dir=state))
    staged, original = temp / "next", temp / "original"
    installed = False
    committed = False
    try:
        if managed:
            (temp / "fingerprint").write_text(source_hash, encoding="ascii")
        if not exists or source_hash != old_hash:
            shutil.copytree(folder, staged)
            if exists:
                destination.rename(original)
                if native_fingerprint(original) != old_hash:
                    raise ValueError(f"{destination} changed during installation. Its original copy was kept.")
            staged.rename(destination)
            installed = True
        if managed:
            (temp / "fingerprint").replace(marker)
        committed = True
    except BaseException:
        if installed:
            destination.rename(staged)
        if original.exists():
            original.rename(destination)
        raise
    finally:
        # A failed rollback leaves the previous tree in stage-*/original for recovery.
        if committed or not original.exists():
            shutil.rmtree(temp)
    return ("updated" if installed else "current") if exists else "installed"


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
    bundled = skills[0].parent == (ROOT / "skills").resolve() and not (ROOT / ".office/portable-skills").is_dir()
    legacy = (json.loads((ROOT / "team/native-skill-history.json").read_text(encoding="utf-8"))
              if bundled else {})
    for name in destinations[args.provider]:
        target = workspace / name
        target.mkdir(parents=True, exist_ok=True)
        state = target / ".evolve-hq-native"
        results = {k: [] for k in ("installed", "updated", "current", "kept")}
        with native_lock(state):
            for folder in skills:
                outcome = install_native(folder, target, state, legacy.get(folder.name, []) if bundled else None)
                results[outcome].append(folder.name)
        print(f"{target}: " + ", ".join(f"{len(v)} {k}" for k, v in results.items()))
        if results["kept"]:
            print("Existing skills kept: " + ", ".join(results["kept"]))


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
