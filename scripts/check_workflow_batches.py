"""Exercise parallel workflows, sequential gates, and reuse without an AI account."""
from collections import Counter
from contextlib import ExitStack
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
        one_stage = next(flow for flow in catalog if flow["id"] == "copywriting")["modes"][0]
        next_run = wait_run(skill_runs.start_run({
            "product": batch["product"], "sourceRun": batch["id"],
            "workflows": [{"workflow": "copywriting", "mode": one_stage["id"], "stages": [one_stage["steps"][0]["id"]]}],
        }))
        assert next_run["status"] == "review" and len(next_run["steps"]) == 1
        standalone = wait_run(skill_runs.start_run({"skills": ["humanizer"], "brief": "Polish this line."}))
        assert standalone["status"] == "review" and standalone["steps"][0]["report"] == "Standalone report."

print("Six parallel workflows, ordered checklist reviews, two revisions, provider and review recovery, "
      "isolated blocking, handoff reuse and standalone skills verified.")
