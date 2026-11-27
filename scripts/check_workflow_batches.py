"""Exercise parallel workflows, sequential gates, and reuse without an AI account."""
from collections import Counter
from contextlib import ExitStack
import base64
import json
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Barrier, Lock
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "office"))
import activity  # noqa: E402
from providers import ProviderNoAnswer  # noqa: E402
import skill_runs  # noqa: E402
import workflow_batches  # noqa: E402


def wait_run(run):
    for _ in range(200):
        data = skill_runs.get_run(run["id"])
        if data["status"] not in ("queued", "working"):
            return data
        time.sleep(.05)
    raise AssertionError("Workflow batch did not reach a terminal state.")


catalog = workflow_batches.workflow_catalog()
guide = skill_runs.load_json(ROOT / "team/skill-guide.json")
assert [flow["id"] for flow in catalog] == list(workflow_batches.ORDER)
for flow in catalog:
    assert len({mode["id"] for mode in flow["modes"]}) == len(flow["modes"])
    for mode in flow["modes"]:
        assert len({stage["id"] for stage in mode["steps"]}) == len(mode["steps"])
        for stage in mode["steps"]:
            assert stage["checks"] and stage["instruction"] and stage["skill"] in guide
            assert (ROOT / "skills" / stage["skill"] / "SKILL.md").is_file()

barrier = Barrier(len(catalog), timeout=8)
counts = Counter()
events = []
event_lock = Lock()
first_titles = {flow["id"]: flow["modes"][0]["steps"][0]["title"] for flow in catalog}
original_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg=="


def provider(_provider, directory, prompt, *, files):
    path = directory.name
    if "Run exactly this selected Evolve skill" in prompt:
        return "Standalone report."
    is_review = prompt.startswith("Independently review")
    stage = next(line.removeprefix("Stage: ") for line in prompt.splitlines() if line.startswith("Stage: "))
    with event_lock:
        counts[path, stage, is_review] += 1
        events.append((path, stage, is_review))
        first = sum(count for (workflow, _, review), count in counts.items() if workflow == path and not review) == 1
        attempt = counts[path, stage, is_review]
    if first and not is_review and "Selected previous run summaries:\nNone" in prompt:
        barrier.wait()
    if "Useful approved example from " in prompt and not is_review:
        assert "Reviewed preceding stages" in prompt
    if "Check the selective handoff." in prompt and not is_review:
        assert "Useful approved example from market-research" in prompt
        assert "Useful approved example from native-ads" not in prompt
        assert "Images attached to this run: None" in prompt
        assert "Images carried forward as prior evidence:" in prompt
        assert [file.name for file in files] == ["reused-image-1.png"]
        assert files[0].read_bytes() == base64.b64decode(original_image)
    if not is_review:
        return "A concrete, inspectable draft."
    criteria = prompt.split("Check all of these:\n", 1)[1].split("\n\nInspect", 1)[0].splitlines()
    if path == "native-ads" and stage == first_titles[path] and attempt == 1:
        return "A review without the required JSON."
    if path == "native-ads" and stage == first_titles[path] and attempt == 2:
        assert "preceding response could not be saved" in prompt
    if path == "static-ads" and attempt == 1:
        raise ProviderNoAnswer("Simulated empty provider response.")
    status = "met"
    if path == "market-research" and stage == first_titles[path] and attempt <= 2:
        status = "fix"
    if path == "static-ads":
        status = "missing"
    if path == "store-cro":
        status = "fix"
    return json.dumps({
        "checklist": [{"number": index, "status": status, "evidence": "An exact line from the draft"}
                      for index, _ in enumerate(criteria, 1)],
        "feedback": f"Reviewer result: {status}",
        "handoff": f"Useful approved example from {path}" if status == "met" else "",
    })


def check_handoff_matrix(workspace):
    flows = [flow["id"] for flow in catalog]
    jobs = [{"workflow": flow["id"], "mode": flow["modes"][0]["id"],
             "stages": [flow["modes"][0]["steps"][0]["id"]]} for flow in catalog]
    jobs[flows.index("market-research")] = {
        "workflow": "market-research", "mode": "manual-research", "stages": ["manual-voc"],
    }
    reports = {flow: f'{flow} approved control — "$49 USD". Sample: four speakers; one objected.'
               for flow in flows}
    # Exercise the file-based route as well as the verbatim inline route.
    reports["static-ads"] += "\n" + "Visual slot description. " * 600
    observed = set()
    first_passes = set()
    sender = None

    def matrix_provider(_provider, directory, prompt, *, files):
        receiver = directory.name
        if prompt.startswith("Index only the new customer records"):
            assert receiver == "market-research" and sender is not None
            assert "Selected previous run summaries:\nNone" in prompt and "Approved copy:" not in prompt
            assert "Summary from " not in prompt and "reused-image" not in prompt
            assert [file.name for file in files] == ["supplied-image-1.png"]
            first_passes.add(sender)
            return "Independent customer records R1 and R2."
        reviewing = prompt.startswith("Independently review")
        if sender is not None:
            snapshots = list((directory / "reviewed-inputs").glob("*.md"))
            assert len(snapshots) == 1 and snapshots[0].read_text(encoding="utf-8") == reports[sender]
            assert str(snapshots[0]) in prompt and f"Summary from {sender}." in prompt
            assert not any(f"Summary from {other}." in prompt for other in flows if other != sender)
            if len(reports[sender]) <= workflow_batches.INLINE_REPORT_CHARS:
                assert reports[sender] in prompt
            else:
                assert "Read the complete approved copy" in prompt
            if reviewing:
                assert workflow_batches.HANDOFF_CHECK in prompt
            if receiver == "market-research":
                assert "Independent customer records R1 and R2." in prompt
                assert (directory / "01-manual-voc.source-index.md").is_file()
            with event_lock:
                observed.add((sender, receiver, reviewing))
        if not reviewing:
            return reports[receiver]
        checks = prompt.split("Check all of these:\n", 1)[1].split("\n\nInspect", 1)[0].splitlines()
        return json.dumps({
            "checklist": [{"number": n, "status": "met", "evidence": "Checked the approved fixture."}
                          for n in range(1, len(checks) + 1)],
            "feedback": "Fixture reviewed.", "handoff": f"Summary from {receiver}.",
        })

    with patch.object(skill_runs, "reply", side_effect=matrix_provider):
        source = wait_run(skill_runs.start_run({
            "brief": "Prepare six distinct reviewed reports.", "workflows": jobs, "images": [original_image],
        }))
        assert source["status"] == "review"
        run_path = workspace / "tasks" / source["id"] / "run.json"
        stored = skill_runs.load_json(run_path)
        for step in stored["steps"]:
            artifact = Path(step["artifact"])
            # A moved installation and a subsequently edited Markdown file must keep the approved version.
            artifact.write_text("Later edit, outside the independent review.", encoding="utf-8")
            step["artifact"] = str(Path("old-install") / step["workflow"] / artifact.name).replace("/", "\\")
        run_path.write_text(json.dumps(stored), encoding="utf-8")
        for step in source["steps"]:
            sender = step["workflow"]
            target = wait_run(skill_runs.start_run({
                "brief": "Use only the selected reviewed stage.", "sourceRun": source["id"],
                "sourceSteps": [step["id"]], "workflows": jobs, "sourceImages": True, "images": [original_image],
            }))
            assert target["status"] == "review", [(s["id"], s.get("quality")) for s in target["steps"]]
        assert observed == {(a, b, review) for a in flows for b in flows for review in (False, True)}
        assert first_passes == set(flows)


with tempfile.TemporaryDirectory() as folder:
    workspace = Path(folder).resolve()
    shutil.copytree(ROOT / "team", workspace / "team")
    shutil.copytree(ROOT / "skills", workspace / "skills")
    with ExitStack() as stack:
        for patcher in (
            patch.object(activity, "ROOT", workspace),
            patch.object(activity, "DB", workspace / "activity.sqlite3"),
            patch.object(skill_runs, "ROOT", workspace),
            patch.object(workflow_batches, "ROOT", workspace),
            patch.object(skill_runs, "require", return_value="stub"),
            patch.object(skill_runs, "reply", side_effect=provider),
        ):
            stack.enter_context(patcher)
        initial = skill_runs.start_run({
            "product": "Example product",
            "brief": "Include a concrete test plan.",
            "images": [original_image],
            "workflows": [{"workflow": flow["id"], "mode": flow["modes"][0]["id"]} for flow in catalog],
        })
        batch = wait_run(initial)
        assert batch["status"] == "blocked"
        assert {path for path, _, review in events[:6] if not review} == set(workflow_batches.ORDER)
        batch_steps = {flow["id"]: [stage for stage in batch["steps"] if stage["workflow"] == flow["id"]]
                       for flow in catalog}
        assert [step["status"] for step in batch_steps["static-ads"]] == ["blocked", "skipped"]
        assert [step["status"] for step in batch_steps["store-cro"]] == ["blocked", "skipped"]
        for workflow, steps in batch_steps.items():
            if workflow not in {"static-ads", "store-cro"}:
                assert all(step["status"] == "review" for step in steps)
                assert all(len(step["checkResults"]) == len(step["checks"]) for step in steps)
            for before, after in zip(steps, steps[1:]):
                if after["status"] == "review":
                    assert events.index((workflow, before["title"], True)) < events.index((workflow, after["title"], False))
        revised = batch_steps["market-research"][0]
        assert revised["revisions"] == 2
        assert counts["market-research", revised["title"], True] == 3
        assert counts["market-research", revised["title"], False] == 3
        assert counts["native-ads", first_titles["native-ads"], True] == 2
        assert counts["native-ads", first_titles["native-ads"], False] == 1
        assert counts["static-ads", first_titles["static-ads"], True] == 2
        assert counts["static-ads", first_titles["static-ads"], False] == 1
        assert counts["store-cro", first_titles["store-cro"], False] == 3
        assert batch_steps["store-cro"][0]["revisions"] == 2
        assert not any("static-ads" in step["artifact"] for step in skill_runs.previous_results(batch["id"]))
        provider_calls = len(events)
        no_asset = wait_run(skill_runs.start_run({
            "brief": "The script is attached as text only.",
            "workflows": [{"workflow": "ad-review", "mode": "review-finished-ad"}],
        }))
        assert no_asset["status"] == "blocked" and no_asset["steps"][0]["status"] == "blocked"
        assert "Attach the finished ad image" in no_asset["steps"][0]["quality"]
        assert len(events) == provider_calls
        one_stage = next(flow for flow in catalog if flow["id"] == "copywriting")["modes"][0]
        next_run = wait_run(skill_runs.start_run({
            "product": batch["product"], "sourceRun": batch["id"],
            "workflows": [{"workflow": "copywriting", "mode": one_stage["id"], "stages": [one_stage["steps"][0]["id"]]}],
        }))
        assert next_run["status"] == "review" and len(next_run["steps"]) == 1
        assert next_run["imageCount"] == 0 and batch["imageCount"] == 1
        handoff = {
            "product": batch["product"], "sourceRun": batch["id"], "sourceSteps": [revised["id"]],
            "sourceImages": True, "brief": "Check the selective handoff.",
            "workflows": [{"workflow": "copywriting", "mode": one_stage["id"],
                           "stages": [one_stage["steps"][0]["id"]]}],
        }
        reused = wait_run(skill_runs.start_run(handoff))
        assert reused["status"] == "review" and reused["imageCount"] == 1
        combined = wait_run(skill_runs.start_run(handoff | {
            "brief": "Keep new and reused images in order.", "images": [original_image],
        }))
        assert combined["status"] == "review" and combined["imageCount"] == 2
        assert [path.name for path in skill_runs.saved_images(workspace / "tasks" / combined["id"])] == [
            "supplied-image-1.png", "reused-image-1.png",
        ]
        for changes, message in (
            ({"sourceSteps": [batch_steps["static-ads"][0]["id"]]}, "available reviewed result"),
            ({"sourceSteps": []}, "available reviewed result"),
            ({"images": [original_image] * 3}, "across the previous and new run"),
        ):
            try:
                skill_runs.start_run(handoff | changes)
            except ValueError as error:
                assert message in str(error)
            else:
                raise AssertionError("Invalid handoff was accepted.")
        provider_calls = len(events)
        prior_image_only = wait_run(skill_runs.start_run(handoff | {
            "workflows": [{"workflow": "ad-review", "mode": "review-finished-ad"}],
        }))
        assert prior_image_only["status"] == "blocked" and len(events) == provider_calls
        standalone = wait_run(skill_runs.start_run({"skills": ["humanizer"], "brief": "Polish this line."}))
        assert standalone["status"] == "review" and standalone["steps"][0]["report"] == "Standalone report."
        check_handoff_matrix(workspace)

print("Parallel workflows, ordered checklist reviews, revisions, provider recovery, isolated blocking, "
      "finished-asset requirement, selective report and image reuse, 36 sender/receiver combinations, "
      "and standalone skills verified.")
