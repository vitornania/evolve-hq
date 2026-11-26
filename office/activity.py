"""Persist task activity for this workspace's roster."""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("EVOLVE_HQ_ACTIVITY_DB") or ROOT / ".office/activity.sqlite3")
STATUSES = ("queued", "working", "review", "blocked", "done", "failed", "interrupted")
STALE_SECONDS = 25 * 60
SCHEMA = """
CREATE TABLE IF NOT EXISTS activity (
    sequence INTEGER PRIMARY KEY,
    record TEXT NOT NULL, title TEXT NOT NULL, product TEXT NOT NULL,
    role TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL,
    updated REAL NOT NULL, pid INTEGER
);
CREATE INDEX IF NOT EXISTS activity_assignment ON activity(record, role, sequence);
"""


def new_task(product, kind):
    slug = re.sub(r"[^a-z0-9]+", "-", product.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Supply a product name containing a letter or number.")
    parent = ROOT / "tasks" / slug[:90]
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return Path(tempfile.mkdtemp(prefix=f"{stamp}-{kind}-", dir=parent))


def update(record, title, product, role, status, note, pid=None):
    if status not in STATUSES:
        raise ValueError("Unknown office status.")
    catalog = json.loads((ROOT / "team/catalog.json").read_text(encoding="utf-8"))
    if role not in {entry["name"] for entry in catalog["roles"]}:
        raise ValueError(f"Unknown Evolve HQ role: {role}")
    record = record.resolve()
    if not record.is_file() or record.name != "RECORD.md" or not record.is_relative_to(ROOT / "tasks"):
        raise ValueError("Choose a task RECORD.md inside Evolve HQ/tasks.")
    DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB, timeout=5)) as db, db:
        db.executescript(SCHEMA)
        db.execute(
            """INSERT INTO activity(record, title, product, role, status, note, updated, pid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.relative_to(ROOT).as_posix(), title[:180], product[:120], role, status,
             note[:500], time.time(), pid),
        )


def process_running(pid):
    if os.name == "nt":
        # os.kill(pid, 0) is destructive on Windows. Query a read-only process handle.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = wintypes.DWORD()
            return code.value == 259 if kernel.GetExitCodeProcess(handle, ctypes.byref(code)) else None
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    return True


def worker_state(item, now):
    if item["status"] != "working":
        return item["status"]
    if item["pid"] is not None:
        running = process_running(item["pid"])
        return "stale" if running is None else "working" if running else "interrupted"
    return "stale" if now - item["updated"] > STALE_SECONDS else "working"


def snapshot():
    current = time.time()
    rows, history = [], []
    if DB.is_file():
        with closing(sqlite3.connect(f"{DB.resolve().as_uri()}?mode=ro", uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'activity'").fetchone():
                rows = db.execute("""
                    SELECT * FROM activity
                    WHERE sequence IN (SELECT MAX(sequence) FROM activity GROUP BY record, role)
                    ORDER BY sequence DESC
                """).fetchall()
                history = db.execute("SELECT * FROM activity ORDER BY sequence DESC LIMIT 18").fetchall()

    def serialize(row, current_state=False):
        item = dict(row)
        if current_state:
            item["status"] = worker_state(item, current)
        item.pop("pid")
        item["updated"] = datetime.fromtimestamp(item["updated"], timezone.utc).isoformat()
        return item

    assignments = {}
    for row in rows:
        item = serialize(row, current_state=True)
        if not (ROOT / item["record"]).is_file():
            continue
        # Keep every open assignment and the latest completed assignment per role.
        items = assignments.setdefault(item["role"], [])
        if item["status"] in {"queued", "working", "review", "blocked", "stale"} or not items:
            items.append(item)
    return {"roles": assignments, "history": [serialize(row) for row in history]}
