"""Verify the public release from a new checkout without AI credentials."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
from activity import process_running  # noqa: E402

assert process_running(os.getpid())
with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(.5)"]) as child:
    assert process_running(child.pid) and child.poll() is None
    child.wait(timeout=10)
    assert process_running(child.pid) is False

with tempfile.TemporaryDirectory() as folder:
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
server = subprocess.Popen(launch, cwd=ROOT)
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
    for route in ("/workbench.js", "/static-libraries.js", "/scene.js", "/three/build/three.module.js"):
        with urlopen(base + route, timeout=5) as response:
            assert response.headers.get_content_type() == "text/javascript"
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
    else:
        server.terminate()
    server.wait(timeout=10)
print("Launcher, 62 skills, live activity, ROAS and native install verified.")
