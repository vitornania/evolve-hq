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
import providers  # noqa: E402
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
        assert isinstance(mode.get("inputs"), str) and mode["inputs"].strip(), mode["id"]
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


def check_standalone_modes(workspace):
    router = workspace / "skills/evolve-skill/SKILL.md"
    assert [p.name for p, _ in workflow_batches.decision_references(router, False)] == ["choosing-a-method.md"]
    total = 0
    for workflow in catalog:
        for mode in workflow["modes"]:
            steps = mode["steps"]
            route = f"{workflow['id']}/{mode['id']}"
            calls = []

            def respond(_provider, directory, prompt, *, files):
                index = len(calls) // 2
                stage = steps[index]
                assert "Choosing a method for an Evolve decision" in prompt
                reviewing = prompt.startswith("Independently review")
                assert reviewing == bool(len(calls) % 2)
                assert f"Stage: {stage['title']}\n" in prompt
                assert "Selected previous run summaries:\nNone" in prompt
                assert workflow_batches.HANDOFF_CHECK not in prompt
                assert not (directory / "reviewed-inputs").exists()
                for earlier in steps[:index]:
                    assert f"Reviewed fixture {route}/{earlier['id']}." in prompt
                token = f"{route}/{stage['id']}"
                calls.append((stage["id"], reviewing))
                if not reviewing:
                    return f"Draft fixture {token}."
                assert f"Draft fixture {token}." in prompt
                return json.dumps({
                    "checklist": [{"number": i, "status": "met", "evidence": token}
                                  for i in range(1, len(stage["checks"]) + 1)],
                    "feedback": "Fixture reviewed.", "handoff": f"Reviewed fixture {token}.",
                })

            with patch.object(skill_runs, "reply", side_effect=respond):
                run = wait_run(skill_runs.start_run({
                    "product": "Standalone fixture", "brief": f"Fresh inputs for {route}.",
                    "images": [original_image] if any(s.get("requires_image") for s in steps) else [],
                    "workflows": [{"workflow": workflow["id"], "mode": mode["id"]}],
                }))
            assert run["status"] == "review", (route, [(s["id"], s.get("quality")) for s in run["steps"]])
            assert calls == [(s["id"], reviewing) for s in steps for reviewing in (False, True)]
            assert not skill_runs.load_json(workspace / "tasks" / run["id"] / "run.json")["carried"]
            for result in run["steps"]:
                assert Path(result["artifact"]).read_text(encoding="utf-8").strip() == result["report"]
            total += len(steps)
    print(f"Standalone execution verified for {sum(len(w['modes']) for w in catalog)} modes and {total} stages.")


def check_individual_skills(workspace):
    # A local pack can augment the built-in method without replacing its decision guidance.
    name = "humanizer"
    pack = workspace / ".office/libraries/evolve/skills" / name
    pack.mkdir(parents=True)
    # Exercise Windows line endings even on a POSIX checkout. The runner preserves source bytes.
    installed_method = "Consult the installed method example.\r\nKeep its evidence in context.\r\n"
    (pack / "SKILL.md").write_bytes(installed_method.encode("utf-8"))
    (pack / "example.md").write_text("Authorized source fixture.", encoding="utf-8")
    source_index = pack / "references/local-sources.md"
    source_index.parent.mkdir()
    source_index.write_text("An optional local worksheet index.", encoding="utf-8")
    portable_method = (workspace / "skills" / name / "SKILL.md").read_bytes().decode("utf-8")
    cases = skill_runs.load_json(ROOT / "examples/skill-quality-cases.json")
    assert set(cases) == set(guide)
    assert all(case["brief"] and case["expect"] for case in cases.values())
    calls = Counter()
    methods = [{"file": str(pack / "SKILL.md")}]
    valid = {"file": "example.md", "anchor": "Authorized source", "decision": "Check the example."}
    verified = workflow_batches.verify_references({"references": [valid]}, methods)
    assert verified["references"][0]["file"] == str(pack / "example.md")
    assert verified["references"][0]["startLine"] == verified["references"][0]["endLine"] == 1
    original = pack / "references/Exact template (original).txt"
    anchor = "Original form field in its authored order."
    original.write_text(anchor + "\n\n[image]: <data:image/png;base64,aW1hZ2U=>", encoding="utf-8")
    linked_method = pack / "linked.md"
    linked_method.write_text(
        "[Selected form](references/Exact%20template%20%28original%29.txt)\n"
        "[External](https://example.com/file.md)\n[Escaped](../../../outside.md)\n",
        encoding="utf-8",
    )
    (pack.parents[2] / "outside.md").write_text("Unrelated input.", encoding="utf-8")
    selected, files = workflow_batches.selected_method(
        linked_method, original_links=("Selected form", "External", "Escaped", "Not present"),
    )
    assert files[-1]["role"] == "Original method" and Path(files[-1]["file"]) == original
    assert anchor in selected and "[embedded image in the local original]" in selected
    assert "aW1hZ2U=" not in selected and "Unrelated input." not in selected
    used = {"file": str(original), "anchor": anchor, "decision": "Kept the original field order."}
    assert workflow_batches.verify_references({"references": [used]}, files)["references"][0]["file"] == str(original)
    angles = pack.parent / "evolve-angles"
    angles.mkdir()
    (angles / "SKILL.md").write_text("[Angle development prompt](angle-method.md)\n", encoding="utf-8")
    angle_example = "Fixture for evaluating a specific buying belief."
    (angles / "angle-method.md").write_text(angle_example, encoding="utf-8")
    for invalid in (valid | {"anchor": "Invented words"}, valid | {"file": str(workspace / "tasks/run.json")}):
        try:
            workflow_batches.verify_references({"references": [invalid]}, methods)
        except workflow_batches.ReviewFormatError:
            pass
        else:
            raise AssertionError("Unverified local reference was accepted.")

    try:
        workflow_batches.review_reply(json.dumps({
            "checklist": [], "feedback": "Reviewed.", "handoff": "Reviewed recommendation.",
            "judgment": {"choice": "Launch.", "basis": "Unknown."},
        }), [])
    except workflow_batches.ReviewFormatError:
        pass
    else:
        raise AssertionError("An incomplete decision note was accepted.")

    guide_path = workspace / "skills/evolve-skill/references/choosing-a-method.md"
    supplied = methods + [{"role": "Decision reference", "file": str(guide_path)}]
    cited = {"file": str(guide_path), "anchor": "Match the evidence to the question",
             "decision": "Checked which source supports the claim."}
    assert workflow_batches.verify_references({"references": [cited]}, supplied)["references"][0]["startLine"] > 0

    def respond(_provider, directory, prompt, *, files):
        title = next(line[7:] for line in prompt.splitlines() if line.startswith("Stage: "))
        reviewing = prompt.startswith("Independently review")
        calls[title, reviewing] += 1
        if title == guide["vibe-coding-toolkit"]["title"]:
            assert "Choosing a method for an Evolve decision" not in prompt
        if title == guide["evolve-angles"]["title"]:
            assert angle_example in prompt and "Original method." in prompt
        if title == guide[name]["title"]:
            assert "Choosing a method for an Evolve decision" in prompt
            assert "book-copy-decisions.md" in prompt
            assert portable_method in prompt and installed_method in prompt
            assert str(pack) in prompt
            assert str(source_index) in prompt
        else:
            assert str(source_index) not in prompt
        if not reviewing:
            assert "Run exactly this selected Evolve skill:" in prompt
            return "A scoped report with an evidence-based decision."
        criteria = prompt.split("Check all of these:\n", 1)[1].split("\n\nInspect", 1)[0].splitlines()
        status = "met"
        if title == guide[name]["title"] and calls[title, reviewing] == 1:
            status = "fix"
        if title == guide["ab-testing"]["title"]:
            status = "missing"
        return json.dumps({
            "checklist": [{"number": n, "status": status, "evidence": "Selected method and draft inspected."}
                          for n in range(1, len(criteria) + 1)],
            "feedback": "Fixture review.", "handoff": "Reviewed decision." if status == "met" else "",
            "judgment": {"choice": "Use the narrower claim.", "basis": "One measured setup.",
                         "reconsiderIf": "A second setup verifies the broader claim."} if title == guide[name]["title"] else None,
        })

    with patch.object(skill_runs, "reply", side_effect=respond):
        for skill in guide:
            # Each skill starts cold; no previous report or answer key.
            run = wait_run(skill_runs.start_run({"skills": [skill], "brief": cases[skill]["brief"]}))
            step = run["steps"][0]
            assert not run["workflows"] and step["id"] == skill
            attempts = 2 if skill == name else 1
            assert calls[step["title"], True] == calls[step["title"], False] == attempts
            if skill == "ab-testing":
                assert step["status"] == "blocked" and not step.get("artifact")
                continue
            assert step["status"] == "review" and len(step["checks"]) == len(step["checkResults"])
            assert Path(step["artifact"]).name == f"01-{skill}.md"
            assert skill_runs.previous_results(run["id"])[0]["report"] == step["report"]
            if skill == name:
                assert step["revisions"] == 1 and step["judgment"]["basis"] == "One measured setup."
                assert [Path(m["file"]).name for m in step["methodFiles"]] == [
                    "SKILL.md", "SKILL.md", "choosing-a-method.md", "book-copy-decisions.md",
                ]
                methods, receipt = workflow_batches.selected_method(pack / "SKILL.md")
                assert step["methodFiles"] == receipt and portable_method in methods
        mixed = wait_run(skill_runs.start_run({"skills": ["ab-testing", name], "brief": "Two selected tasks."}))
        assert [step["status"] for step in mixed["steps"]] == ["blocked", "review"]
        assert [step["id"] for step in skill_runs.previous_results(mixed["id"])] == [name]
    print(f"Individual draft/review, artifact reuse and method resolution verified for {len(guide)} skills.")


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
            assert "Selected previous run summaries:\nNone" in prompt and "Reviewed copy:" not in prompt
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
            assert f"Reconsider if: New evidence for {sender}." in prompt
            assert not any(f"New evidence for {other}." in prompt for other in flows if other != sender)
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
            "judgment": {"choice": "Keep the control.", "basis": "The new offer is unverified.",
                         "reconsiderIf": f"New evidence for {receiver}."},
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
    long_prompt = "Reference evidence. " * 3000

    command, message = providers.command_for("antigravity", "agy", long_prompt, [], None)
    assert len(" ".join(command)) < 1024 and "stream-json" in command and "plan" in command
    assert json.loads(message)["message"]["content"] == long_prompt and len(message.splitlines()) == 1
    stream = '{"event":"init"}\n{"event":"result","result":{"status":"SUCCESS","response":"Verified."}}'
    assert providers.response_text("antigravity", stream) == "Verified."
    assert not providers.response_text("antigravity", '{"event":"result","result":{"status":"ERROR"}}')
    shutil.copytree(ROOT / "team", workspace / "team")
    shutil.copytree(ROOT / "skills", workspace / "skills")
    with ExitStack() as stack:
        for patcher in (
            patch.object(activity, "ROOT", workspace),
            patch.object(activity, "DB", workspace / "activity.sqlite3"),
            patch.object(skill_runs, "ROOT", workspace),
            patch.object(skill_runs, "PACKS", workspace / ".office/libraries"),
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
        check_individual_skills(workspace)
        check_handoff_matrix(workspace)
        check_standalone_modes(workspace)

print("Parallel workflows, ordered checklist reviews, revisions, provider recovery, isolated blocking, "
      "finished-asset requirement, selective report and image reuse, 36 sender/receiver combinations, "
      "and standalone skills verified.")
