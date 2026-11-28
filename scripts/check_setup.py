"""Verify the public release from a new checkout without AI credentials."""
import base64
from importlib.util import find_spec
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
from activity import process_running  # noqa: E402
sys.path.insert(0, str(ROOT))
import setup_hq  # noqa: E402

assert process_running(os.getpid())
with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(.5)"]) as child:
    assert process_running(child.pid) and child.poll() is None
    child.wait(timeout=10)
    assert process_running(child.pid) is False

with tempfile.TemporaryDirectory() as folder:
    workspace = Path(folder)
    for filename in ("hq.py", "board.html", "team/catalog.json", "office/activity.py"):
        target = workspace / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / filename, target)
    subprocess.run([sys.executable, "hq.py", "board"], cwd=workspace, check=True)
    generated = (workspace / "index.html").read_text(encoding="utf-8")
    assert '<form id="cpa-form">' in generated and 'src="/cpa-calculator.js"' in generated
    assert generated == (ROOT / "index.html").read_text(encoding="utf-8"), "Regenerate the board with hq.py board."
    # Two installations from the previous public release, one customized by its owner.
    legacy = (ROOT / "scripts/fixtures/evolve-angles-before-native-refresh.md").read_bytes()
    native = workspace / ".agents/skills/evolve-angles"
    custom = workspace / ".claude/skills/evolve-angles"
    for destination in (native, custom):
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_bytes(legacy)
    (custom / "owner-notes.md").write_text("Keep my notes.", encoding="utf-8")
    install = [sys.executable, "setup_hq.py", "skills", "all", "--workspace", folder]
    subprocess.run(install, cwd=ROOT, check=True)
    assert (native / "SKILL.md").read_bytes() == (ROOT / "skills/evolve-angles/SKILL.md").read_bytes()
    assert (custom / "SKILL.md").read_bytes() == legacy and (custom / "owner-notes.md").is_file()
    # A later managed refresh must put the original back if committing its marker fails.
    state = native.parent / ".evolve-hq-native"
    marker = state / "evolve-angles.sha256"
    expected = marker.read_bytes()
    next_source = workspace / "next/evolve-angles"
    next_source.mkdir(parents=True)
    (next_source / "SKILL.md").write_text("New bundled version.", encoding="utf-8")
    with patch.object(Path, "replace", side_effect=OSError("simulated marker write failure")):
        try:
            setup_hq.install_native(next_source, native.parent, state, [])
        except OSError:
            pass
        else:
            raise AssertionError("Expected the simulated update to fail.")
    assert marker.read_bytes() == expected
    assert (native / "SKILL.md").read_bytes() == (ROOT / "skills/evolve-angles/SKILL.md").read_bytes()
    # Explicit third-party sources cannot replace a managed public destination.
    assert setup_hq.install_native(next_source, native.parent, state, None) == "kept"
    assert setup_hq.install_native(next_source, native.parent, state, []) == "updated"
    assert (native / "SKILL.md").read_text(encoding="utf-8") == "New bundled version."
    assert setup_hq.install_native(next_source, native.parent, state, []) == "current"
    (native / "SKILL.md").write_text("Personal custom instructions.", encoding="utf-8")
    subprocess.run(install, cwd=ROOT, check=True)
    assert (native / "SKILL.md").read_text(encoding="utf-8") == "Personal custom instructions."
    for path in (".agents/skills", ".claude/skills"):
        assert len(list((Path(folder) / path).glob("*/SKILL.md"))) == 62
        static = Path(folder) / path / "adapt-reference-ad"
        assert (static / "references/local-rendering.md").is_file()
        assert (static / "references/reference-review.md").is_file()
        for script in ("render_static.py", "check_coverage.py"):
            cli = subprocess.run([sys.executable, str(static / "scripts" / script), "--help"],
                                 capture_output=True, text=True, check=True)
            assert "usage:" in cli.stdout

report = subprocess.run([sys.executable, "hq.py", "run", "roas", "examples/ad-metrics.csv", "--product",
                         "Release check"], cwd=ROOT, capture_output=True, text=True, check=True)
artifact = Path(report.stdout.strip().splitlines()[-1]).resolve()
assert artifact.is_file()
expected_record = (artifact.parent / "RECORD.md").relative_to(ROOT).as_posix()

with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
if os.name == "nt":
    launch = f'cmd.exe /d /c call "Open Evolve HQ.cmd" --no-open --port {port}'
else:
    launch = ["node", "scripts/start.mjs", "--no-open", "--port", str(port)]
server = subprocess.Popen(launch, cwd=ROOT, stdout=subprocess.PIPE if os.name != "nt" else None,
                          start_new_session=os.name != "nt")
base = f"http://127.0.0.1:{port}"
try:
    for _ in range(100):
        try:
            with urlopen(base + "/api/providers", timeout=2) as response:
                assert len(json.load(response)) == 5
            break
        except OSError:
            if server.poll() is not None:
                raise RuntimeError("Launcher stopped before serving the office.")
            time.sleep(.10)
    else:
        raise RuntimeError("Launcher did not start the office.")
    for route in ("/", "/workflows", "/local-tools"):
        with urlopen(base + route, timeout=5) as response:
            assert response.read().count(b'<header class="hq-bar">') == 1
    with urlopen(base + "/skill-guide.json", timeout=5) as response:
        assert len(json.load(response)) == 62
    with urlopen(base + "/api/workflows", timeout=5) as response:
        workflows = json.load(response)
        assert len(workflows) == 6
        assert all(mode["steps"] for work in workflows for mode in work["modes"])
        modes = {mode["id"] for work in workflows if work["id"] == "ad-review" for mode in work["modes"]}
        assert {"diagnose-underperformance", "review-finished-ad"} <= modes
    for route in ("/workbench.js", "/cpa-calculator.js", "/static-libraries.js", "/scene.js", "/three/build/three.module.js"):
        with urlopen(base + route, timeout=5) as response:
            assert response.headers.get_content_type() == "text/javascript"
    costs = {"currency": "USD", "revenue": "75", "product_cost": "15", "fulfillment": "5",
             "other_costs": "4", "profit_target": "10"}

    def cpa(data):
        request = Request(base + "/api/cpa", data=json.dumps(data).encode("utf-8"),
                          headers={"Origin": base, "Content-Type": "application/json"})
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    estimate = cpa(costs)
    assert estimate["break_even_cpa"] == "51.00" and estimate["target_cpa"] == "41.00"
    assert estimate["break_even_roas"] == "1.47"
    assert cpa(dict(costs, product_cost="100"))["break_even_cpa"] is None
    zero = cpa(dict(costs, product_cost="66"))
    assert zero["break_even_cpa"] == "0.00" and zero["break_even_roas"] is None
    try:
        cpa(dict(costs, other_costs=""))
    except HTTPError as error:
        assert error.code == 400
    else:
        raise AssertionError("A missing cost was accepted as zero.")
    with tempfile.TemporaryDirectory(dir=artifact.parent) as directory:
        preview_task = Path(directory).resolve()
        preview_id = preview_task.relative_to(ROOT / "tasks").as_posix()
        snapshot = preview_task / "run.json"
        preview_layout = {"width": 1080, "height": 1350, "layers": [
            {"id": "headline", "type": "text", "text": "Check the fit", "font": "sans", "size": 64,
             "x": 100, "y": 155, "max_width": 880},
        ]}
        step = {"id": "build-static-ads-in-figma", "skill": "build-static-ads-in-figma", "status": "review"}

        def preview(layout):
            step["report"] = "```static-layout\n" + json.dumps(layout) + "\n```"
            snapshot.write_text(json.dumps({"steps": [step], "status": "review"}), encoding="utf-8")
            request = Request(base + "/api/static-preview",
                              data=json.dumps({"run": preview_id, "step": step["id"]}).encode("utf-8"),
                              headers={"Origin": base, "Content-Type": "application/json"})
            with urlopen(request, timeout=22) as response:
                return json.load(response)

        invalid = dict(preview_layout, layers=[{"id": "image", "type": "image", "file": "../not-an-upload.jpg",
                                               "x": 0, "y": 0, "width": 100, "height": 100}])
        try:
            preview(invalid)
        except HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("The preview accepted a photo outside its uploads.")
        if find_spec("PIL") and find_spec("fontTools"):
            output = preview(preview_layout)
            assert base64.b64decode(output["png"]).startswith(b"\x89PNG")
            svg = base64.b64decode(output["svg"])
            assert b"Check the fit</text>" in svg and b"data:font/" not in svg
    with urlopen(base + "/api/static-libraries", timeout=5) as response:
        assert json.load(response) == []
    with urlopen(base + "/api/activity", timeout=5) as response:
        assignments = json.load(response)["roles"]["Performance Analyst"]
    assert any(entry["record"] == expected_record for entry in assignments)
    with urlopen(base + "/" + expected_record, timeout=5) as response:
        assert b"Ready for review" in response.read()
finally:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"], capture_output=True)
        server.wait(timeout=10)
    else:
        server.terminate()
        try:
            server.communicate(timeout=10)
        except subprocess.TimeoutExpired as error:
            os.killpg(server.pid, signal.SIGKILL)
            server.communicate(timeout=10)
            raise AssertionError("Stopping the launcher left a process holding its output pipe.") from error
        with socket.socket() as probe:
            probe.settimeout(2)
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "The office port is still open."
print("Launcher, 62 skills, live activity, CPA, ROAS and native install verified.")
subprocess.run([sys.executable, "scripts/check_workflow_batches.py"], cwd=ROOT, check=True)
