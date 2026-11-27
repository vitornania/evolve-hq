"""Verify the public release from a new checkout without AI credentials."""
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
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
from activity import process_running  # noqa: E402

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
    subprocess.run([sys.executable, "setup_hq.py", "skills", "all", "--workspace", folder], cwd=ROOT, check=True)
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
assert Path(report.stdout.strip().splitlines()[-1]).is_file()

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
    with urlopen(base + "/api/static-libraries", timeout=5) as response:
        assert json.load(response) == []
    with urlopen(base + "/api/activity", timeout=5) as response:
        entry = json.load(response)["roles"]["Performance Analyst"][0]
    assert entry["record"].startswith("tasks/release-check/")
    with urlopen(base + "/" + entry["record"], timeout=5) as response:
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
