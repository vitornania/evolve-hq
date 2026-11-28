"""Exercise automatic correction capture, recall, and promotion through the HQ runner."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "office"))
import activity
import learning
import learning_replay
import skill_runs
import workflow_batches

SKILL = "build-static-ads-in-figma"
BEFORE = "Use Lemon Mint in the slot reserved for a verified benefit."
AFTER = "Leave the unsupported benefit slot open and place the flavor in its own slot."
CORRECTION = "Fill a benefit slot using a supported product benefit and keep flavor in its own slot."
CUE = "benefit slot"
BRIEF = "Check the benefit slot for the supplied static ad. The flavor is verified and the result is not."
manual = {"criterion": 1, "trigger": "A template benefit slot has only a verified flavor.",
          "correction": CORRECTION, "verification": "Match the slot purpose to a supported product claim.",
          "before": BEFORE, "after": AFTER, "cues": [CUE], "portable": True}


def wait(run):
    for _ in range(400):
        current = skill_runs.get_run(run["id"])
        if current["status"] not in ("working", "queued"):
            assert current["status"] == "review", current
            return current
        time.sleep(.01)
    raise AssertionError("The learning test run did not finish.")


def exercise(root):
    calls = []

    def provider(_provider, _folder, prompt, *, files):
        calls.append(prompt)
        if prompt.startswith("Extract one reusable correction"):
            return json.dumps(manual)
        if not prompt.startswith("Independently review"):
            if "Independent review corrections:" in prompt or CORRECTION in prompt:
                return AFTER
            return BEFORE
        checks = prompt.split("Check all of these:\n", 1)[1].split("\n\nInspect", 1)[0].splitlines()
        initial = "Source exercise" in prompt and "First review findings:" not in prompt
        draft = prompt.split("\nDraft to review:\n")[-1]
        return json.dumps({
            "checklist": [{"number": i, "status": "fix" if i == 1 and initial else "met",
                           "evidence": "The text replaces a supported benefit with a flavor." if initial else draft.strip()}
                          for i in range(1, len(checks) + 1)],
            "feedback": "Separate the flavor from the benefit.",
            "handoff": "" if initial else "Use the supported slot structure.",
            "learning": None,
        })

    with patch.object(activity, "ROOT", root), patch.object(activity, "DB", root / ".office/activity.sqlite3"), \
            patch.object(skill_runs, "ROOT", root), patch.object(skill_runs, "PACKS", root / ".office/libraries"), \
            patch.object(workflow_batches, "ROOT", root), patch.object(skill_runs, "require", return_value="provided"), \
            patch.object(skill_runs, "reply", side_effect=provider):
        common = {"brand": "Demo Skincare", "product": "Trial Cream"}
        prior = wait(skill_runs.start_run({
            **common, "brief": "Source exercise. " + BRIEF, "workflows": [
                {"workflow": "static-ads", "mode": "shortlist-headlines"},
            ],
        }))
        saved = prior["steps"][0]["learning"]
        ident = saved["saved"]
        assert not saved["firstPass"] and not saved["recalled"]
        assert prior["steps"][0]["revisions"] == 1
        assert sum(prompt.startswith("Extract one reusable correction") for prompt in calls) == 1

        fixture = {"version": 1, "records": [{"brand": "Demo Skincare", "product": "Trial Cream",
                   "creative": "Creative version 7", "window": "Test period, 7 days",
                   "source": "Owner report", "verdict": "Win", "metrics": "10 purchases"}]}
        (root / ".office/creative-results.json").write_text(json.dumps(fixture), encoding="utf-8")
        before = len(calls)
        fresh = wait(skill_runs.start_run({**common, "brief": BRIEF, "skills": [SKILL]}))
        outcome = fresh["steps"][0]["learning"]
        assert outcome["firstPass"] and outcome["recalled"][0]["id"] == ident
        assert outcome["tracker"][0]["creative"] == "Creative version 7"
        assert len(calls) == before + 2
        assert all(CORRECTION in call and "Creative version 7" in call for call in calls[before:])

        other = {"brand": "Other store", "product": "Trail snacks"}
        before_validation = wait(skill_runs.start_run({**other, "brief": BRIEF, "skills": [SKILL]}))
        assert not before_validation["steps"][0]["learning"]["recalled"]
        assert not before_validation["steps"][0]["learning"]["tracker"]
        # A user can pause the background workload without disabling automatic capture and recall.
        learning.change(root, {"dailyReplays": 0})
        assert learning.claim_replay(root) is None
        learning.change(root, {"dailyReplays": 1})
        candidate = learning.claim_replay(root)
        assert candidate["id"] == ident and learning.claim_replay(root) is None

        def replay_provider(_provider, _folder, prompt, **_kwargs):
            if prompt.startswith("Create two"):
                return json.dumps({
                    "transfer": "Write a headline for a hiking headlamp. The template has a battery-life benefit slot but the evidence only confirms size.",
                    "exception": "Write a label for a tea package. The template explicitly asks for the flavor and the signed label confirms it.",
                })
            if prompt.startswith("Independently grade"):
                cases = json.loads(prompt.split("rule should stay out.\n", 1)[1])
                assert list(cases) == ["replay", "transfer", "exception"]
                return json.dumps({
                    name: {"valid": True, "winner": "tie" if name == "exception" else (
                        "A" if hashlib.sha256(f"{ident}:{name}".encode()).digest()[0] % 2 else "B"
                    ), "reason": "The correction kept the claim within its evidence."}
                    for name in cases
                })
            return AFTER if CORRECTION in prompt else BEFORE

        passed, note = learning_replay.evaluate(root, candidate, replay_provider)
        assert passed
        learning.finish_replay(root, ident, passed, note)
        promoted = wait(skill_runs.start_run({**other, "brief": BRIEF, "skills": [SKILL]}))
        assert promoted["steps"][0]["learning"]["recalled"][0]["scope"] == "tested"
        unrelated = wait(skill_runs.start_run({
            **other, "brief": "Only explain what is visible on this photo as a flavor label.", "skills": [SKILL],
        }))
        assert not unrelated["steps"][0]["learning"]["recalled"]
        dashboard = learning.dashboard(root)
        assert dashboard["outcomes"][0]["stages"] == 5
        assert dashboard["outcomes"][0]["firstPass"] == 4
        assert dashboard["outcomes"][0]["recalled"] == 2
        learning.change(root, {"id": ident, "correction": "Put verified flavor wording only in a flavor slot."})
        rows = learning.dashboard(root)["lessons"]
        assert len(rows) == 2 and sum(record["retired"] for record in rows) == 1
        assert any(record["scope"] == "project" and record["testing"] == "queued" for record in rows)
        learning.change(root, {"id": ident, "retired": False})
        assert not learning.record_conflicts(root, "one", {"key": "other-1"}, BRIEF, {ident})
        assert not learning.record_conflicts(root, "one-again", {"key": "other-1"}, BRIEF, {ident})
        assert learning.record_conflicts(root, "two", {"key": "other-2"}, BRIEF, {ident}) == [ident]
        assert not learning.recall(root, {"key": "other-2"}, {"test": (SKILL, BRIEF)})["test"]
        learning.change(root, {"preference": "One clear first recommendation."})
        assert learning.preference_for(root) == "One clear first recommendation."
    print("Verified automatic correction capture, recall to a fresh first draft, tracker isolation, "
          "replay budgeting, transfer, exception, and editable local history.")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        for directory in ("team", "skills"):
            shutil.copytree(REPO / directory, root / directory)
        exercise(root)
