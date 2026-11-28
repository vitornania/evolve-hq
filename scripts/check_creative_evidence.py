"""Check a real clip upload, frame retrieval, review handoff and tracker matching."""
import base64
from contextlib import ExitStack
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
import time
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
import activity
import server
import skill_runs
import workflow_batches


def provider(_provider, _folder, prompt, *, files):
    pictures = {file.name for file in files}
    assert {"video-frame-01.jpg", "video-frame-02.jpg"} <= pictures
    if "Compare with the prior clip." in prompt:
        assert "prior-video-frame-01.jpg" in pictures
        assert "previous export, for comparison only" in prompt
    assert "sampled decoded frames with measured presentation timestamps" in prompt
    assert "Possible scene transitions selected by FFmpeg" in prompt
    assert "exact version ID and source file hash" in prompt
    assert "version ID matches but supplied file hash differs" in prompt
    assert "outside-project" not in prompt
    if not prompt.startswith("Independently review"):
        return "The first frame is dark. At 1.5 seconds the background is pink."
    count = len(prompt.split("Check all of these:\n", 1)[1].split("\n\nInspect", 1)[0].splitlines())
    return json.dumps({
        "checklist": [{"number": index, "status": "met", "evidence": "Checked the sampled evidence."}
                      for index in range(1, count + 1)],
        "feedback": "The scene observation is supported.",
        "handoff": "Review the dark-to-pink transition.",
        "creativeBrief": {"idea": "Dark-to-pink transition", "offer": False},
    })


def request(base, path, payload=None):
    headers = {"Origin": base, "Content-Type": "application/json"}
    body = json.dumps(payload).encode() if payload is not None else None
    return urlopen(Request(base + path, data=body, headers=headers), timeout=15)


def check_additional_formats(clip, folder):
    for extension, codec in (("mov", "libx264"), ("webm", "libvpx-vp9")):
        sample = folder / extension
        sample.mkdir()
        exported = sample / ("supplied-video." + extension)
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-c:v", codec,
                        "-threads", "2", str(exported)], check=True)
        upload = {"name": exported.name, "body": base64.b64encode(exported.read_bytes()).decode()}
        assert skill_runs.decode_video(upload)[0] == "." + extension
        evidence, stills = skill_runs.prepare_video(exported)
        assert evidence["duration"] == 3.0 and len(stills) >= 5


def main():
    if not all(shutil.which(name) for name in ("ffmpeg", "ffprobe")):
        if os.environ.get("HQ_REQUIRE_VIDEO_TEST") == "1":
            raise SystemExit("FFmpeg and FFprobe are required for the CI video integration check.")
        print("Skipped video integration check. Install FFmpeg and FFprobe to run it.")
        return
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        folder = Path(temporary).resolve()
        for name in ("team", "skills"):
            shutil.copytree(ROOT / name, folder / name)
        clip = folder / "fixture.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc2=size=160x200:rate=20:duration=1.5",
            "-f", "lavfi", "-i", "color=pink:size=160x200:rate=20:duration=1.5",
            "-filter_complex", "concat=n=2:v=1:a=0", "-c:v", "libx264", "-threads", "2", str(clip),
        ], check=True)
        check_additional_formats(clip, folder)
        body = clip.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        row = {"brand": "HQ Fixture", "product": "Bottle", "creative": "creative-02",
               "window": "2025-10-01 to 2025-10-07", "source": "fixture CSV"}
        (folder / ".office").mkdir()
        (folder / ".office/creative-results.json").write_text(json.dumps({"version": 1, "records": [
            {**row, "asset_sha256": digest}, {**row, "asset_sha256": "0" * 64},
            {**row, "brand": "outside-project", "observation": "outside-project"},
        ]}), encoding="utf-8")
        for module in (activity, server, skill_runs, workflow_batches):
            stack.enter_context(patch.object(module, "ROOT", folder))
        stack.enter_context(patch.object(activity, "DB", folder / "activity.sqlite3"))
        stack.enter_context(patch.object(skill_runs, "PACKS", folder / ".office/libraries"))
        stack.enter_context(patch.object(skill_runs, "require", return_value="fixture"))
        stack.enter_context(patch.object(skill_runs, "reply", side_effect=provider))
        with ThreadingHTTPServer(("127.0.0.1", 0), server.Handler) as http:
            thread = Thread(target=http.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{http.server_port}"
            try:
                prior_id = ""
                for selection in (
                    {"workflows": [{"workflow": "ad-review", "mode": "review-finished-ad"}]},
                    {"skills": ["analyze-ads"]},
                    {"workflows": [{"workflow": "ad-review", "mode": "review-finished-ad"}], "sourceVideo": True},
                ):
                    payload = {**selection, "brand": row["brand"], "product": row["product"],
                               "creativeVersion": row["creative"], "creativeParent": "creative-01",
                               "creativeChange": "New visual transition",
                               "video": {"name": clip.name, "body": base64.b64encode(body).decode()}}
                    if selection.get("sourceVideo"):
                        payload.update(sourceRun=prior_id, brief="Compare with the prior clip.")
                    with request(base, "/api/run", payload) as response:
                        run = json.load(response)
                    run_path = "/api/run?" + urlencode({"id": run["id"]})
                    deadline = time.monotonic() + 15
                    while run["status"] in {"queued", "working"} and time.monotonic() < deadline:
                        time.sleep(0.05)
                        with request(base, run_path) as response:
                            run = json.load(response)
                    assert run["status"] == "review", run.get("error") or run["steps"][0].get("quality")
                    prior_id = prior_id or run["id"]
                    assert run["creative"]["assets"][0]["sha256"] == digest
                    assert run["steps"][0]["reviewedId"].startswith("hq-report-")
                    brief = run["steps"][0]["creativeBrief"]
                    assert brief["idea"] == "Dark-to-pink transition" and "offer" not in brief
                    assert brief["ideaId"].startswith("hq-idea-")
                    assert run["video"]["duration"] == 3.0
                    assert run["video"]["sceneCandidates"][0]["seconds"] == 1.5
                    assert any(frame["seconds"] == 1.5 for frame in run["video"]["frames"])
                    path = "/api/run-video-frame?" + urlencode({"id": run["id"], "frame": "video-frame-01.jpg"})
                    with request(base, path) as response:
                        assert response.headers.get_content_type() == "image/jpeg"
                        assert response.read().startswith(b"\xff\xd8\xff")
                    if selection.get("sourceVideo"):
                        assert run["previousVideo"]["frames"][0]["file"] == "prior-video-frame-01.jpg"
                        with request(base, path.replace("video-frame-01.jpg", "prior-video-frame-01.jpg")) as response:
                            assert response.headers.get_content_type() == "image/jpeg"
                    try:
                        request(base, path.replace("video-frame-01.jpg", "../run.json"))
                    except HTTPError as error:
                        assert error.code == 404
                    else:
                        raise AssertionError("The frame route served an unrelated file.")
            finally:
                http.shutdown()
                thread.join()
    print("Verified MP4, MOV and WebM decoding, clip uploads in a workflow and standalone skill, measured frames, local preview, review IDs, and tracker isolation.")


if __name__ == "__main__":
    main()
