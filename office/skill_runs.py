"""Run the explicitly selected Evolve skills as a read-only Codex review."""
import base64
import binascii
import json
import logging
import os
from pathlib import Path, PureWindowsPath
import re
from threading import Lock, Thread
from urllib.parse import urlsplit

from activity import ROOT, new_task, process_running, update
from providers import reply, require
from workflow_batches import HANDOFF_CHECK, MAX_WORKFLOWS, run_batches, workflow_catalog

MAX_REQUEST_BYTES = 22 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 3
SAVED_IMAGE = re.compile(r"(?:supplied|reused)-image-[1-3]\.(?:png|jpg|webp)")
RUN_LOCK = Lock()
STATE_LOCK = Lock()
PACKS = ROOT / ".office/libraries"
DESK_OWNERS = {
    "Chief of Staff": "Chief of Staff", "Research & Evidence": "Customer Researcher",
    "Strategy & Copy": "Ad Strategist", "Creative Studio": "Creative Producer",
    "Video Editing": "Video Editor", "Performance & Testing": "Performance Analyst",
    "Storefront & Lifecycle": "Lifecycle Lead", "Organic Growth": "Organic Growth Lead",
    "Office Development": "Office Developer",
}
ROLE_OVERRIDES = {
    "market-research-team": "Chief of Staff", "competitor-profiling": "Competitor Researcher",
    "evolve-competitor-creative": "Competitor Researcher", "competitors": "Competitor Researcher",
    "evolve-ugc": "Creator Coordinator", "evolve-partnership-ads": "Creator Coordinator",
    "free-ecommerce-workflows": "Chief of Staff",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def skill_location(name):
    # The optional Evolve overlay preserves the full imported folder structure.
    for root in (PACKS / "evolve" / "skills", ROOT / "skills"):
        skill = root / name / "SKILL.md"
        if skill.is_file():
            return skill
    raise ValueError(f"The Evolve HQ download is missing {name}. Reinstall the release.")


def field(payload, key, limit):
    value = payload.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"The {key} field must be text up to {limit:,} characters.")
    return value.strip()


def decode_images(values):
    if not isinstance(values, list) or len(values) > MAX_IMAGES:
        raise ValueError(f"Add up to {MAX_IMAGES} screenshots or product images.")
    images = []
    for value in values:
        if not isinstance(value, str) or len(value) > (MAX_IMAGE_BYTES * 4 // 3) + 8:
            raise ValueError("Each screenshot or image must be 5 MB or less.")
        try:
            body = base64.b64decode(value, validate=True)
        except binascii.Error:
            raise ValueError("One image could not be read.") from None
        images.append(check_image(body))
    return images


def check_image(body):
    if len(body) > MAX_IMAGE_BYTES:
        raise ValueError("Each screenshot or image must be 5 MB or less.")
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", body
    if body.startswith(b"\xff\xd8\xff"):
        return "jpg", body
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "webp", body
    raise ValueError("Use PNG, JPG, or WebP images.")


def saved_images(directory):
    paths = (path for path in directory.glob("*-image-*")
             if SAVED_IMAGE.fullmatch(path.name) and not path.is_symlink() and path.is_file())
    return sorted(paths, key=lambda path: (path.name.startswith("reused-"), path.name))


def selected_workflows(payload, guide, owners):
    requests = payload.get("workflows", [])
    if not isinstance(requests, list) or len(requests) > MAX_WORKFLOWS:
        raise ValueError("Choose up to six workflows.")
    if not requests:
        return [], [], {}
    workflows = {workflow["id"]: workflow for workflow in workflow_catalog()}
    selected, steps, sources = [], [], {}
    seen = set()
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Choose a workflow and mode.")
        job_id, mode_id = request.get("workflow"), request.get("mode")
        if not isinstance(job_id, str) or job_id not in workflows or job_id in seen:
            raise ValueError("Choose each workflow once per batch.")
        workflow = workflows[job_id]
        mode = next((mode for mode in workflow["modes"] if mode["id"] == mode_id), None)
        if mode is None:
            raise ValueError("Choose an available workflow mode.")
        available = {stage["id"] for stage in mode["steps"]}
        requested = request.get("stages", list(available))
        if (not isinstance(requested, list) or not requested
                or any(not isinstance(key, str) or key not in available for key in requested)
                or len(set(requested)) != len(requested)):
            raise ValueError("Choose at least one available stage in each workflow.")
        seen.add(job_id)
        selected.append({"id": job_id, "title": workflow["title"], "mode": mode_id, "modeTitle": mode["title"]})
        for stage in mode["steps"]:
            if stage["id"] not in requested:
                continue
            name = stage["skill"]
            key = f"{job_id}-{stage['id']}"
            sources[key] = skill_location(name)
            steps.append({
                **stage, "stage": stage["id"], "id": key, "workflow": job_id, "kind": guide[name]["kind"],
                "role": ROLE_OVERRIDES.get(name, owners.get(name)), "status": "queued",
            })
    return selected, steps, sources


def previous_results(identifier, selected=None):
    if not identifier:
        return []
    run = get_run(identifier)
    if not run or run["status"] in {"working", "queued"}:
        raise ValueError("Choose a previous run that has finished.")
    directory = (ROOT / "tasks" / identifier).resolve()
    collected = []
    for step in run["steps"]:
        if step["status"] != "review" or not step.get("handoff") or not step.get("artifact"):
            continue
        # Older records store an absolute path from the original installation.
        filename = PureWindowsPath(step["artifact"]).name
        artifact = (directory / step.get("workflow", "") / filename).resolve()
        if artifact.is_relative_to(directory) and artifact.is_file():
            collected.append({"id": step["id"], "title": step["title"],
                              "workflow": step.get("workflow", "Individual skill"), "artifact": str(artifact),
                              "handoff": step["handoff"], "report": step.get("report"),
                              "judgment": step.get("judgment")})
    if not collected:
        raise ValueError("That run has no reviewed results to reuse.")
    if selected is not None:
        available = {step["id"] for step in collected}
        if (not isinstance(selected, list) or not selected
                or any(not isinstance(key, str) or key not in available for key in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError("Choose at least one available reviewed result from the previous run.")
        collected = [step for step in collected if step["id"] in selected]
    return collected


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("The request must contain a run brief.")
    guide = load_json(ROOT / "team/skill-guide.json")
    catalog = load_json(ROOT / "team/catalog.json")
    owners = {name: DESK_OWNERS[desk["name"]] for desk in catalog["desks"] for name in desk["skills"]}
    workflows, steps, sources = selected_workflows(payload, guide, owners)
    requested = payload.get("skills", [])
    if not isinstance(requested, list) or any(
            not isinstance(name, str) or name not in guide for name in requested):
        raise ValueError("Choose at least one skill from the library.")
    if len(set(requested)) != len(requested):
        raise ValueError("Each skill can appear once in a run.")
    if bool(requested) == bool(workflows):
        raise ValueError("Choose workflows or individual skills for this run.")
    steps.extend(
        {"id": name, "stage": name, "skill": name, "title": guide[name]["title"], "kind": guide[name]["kind"],
         "original_links": guide[name].get("original_links", []),
         "instruction": (f"{guide[name]['description']} Deliver the part requested in the brief. "
                         f"For a full assignment the usual output is: {guide[name]['output']}"
                         + (" For a request to make one original image, prepare the complete static-layout JSON "
                            "for the HQ Preview image button. Keep image layers limited to the named attachments. "
                            "The user renders after review. Do not claim an image file exists before that step."
                            if name == "build-static-ads-in-figma" else "")),
         "checks": [
             "Deliver the specific work requested in the brief, with its constraints and a usable result. "
             "For an explicitly scoped exercise, evaluate only that scope.",
             "Apply the selected skill's relevant decision rules. In the review, identify an actual decision "
             "and the input or method supporting it. Use relevant available primary references. Judge a scoped "
             "deliverable on its own evidence. Missing optional examples or worksheets limit source-conformity "
             "claims. Block only a part that actually requires the missing source or when the user requested its exact use.",
             "Check material claims, calculations, quoted words, evidence limits and next action against "
             "the supplied inputs. Separate observations, hypotheses and recommendations where relevant.",
         ] + (["For a request to make one original image with enough inputs, verify the static-layout block against "
               "the provided HQ image-preview reference. Treat repairable layout errors as fixes. A headline, prompt or "
               "reference-only request does not need a layout. An available product photo is an input, not an export."]
              if name == "build-static-ads-in-figma" else []),
         "role": ROLE_OVERRIDES.get(name, owners.get(name)), "status": "queued"}
        for name in requested
    )
    sources.update({name: skill_location(name) for name in requested})
    product = field(payload, "product", 120)
    url = field(payload, "url", 1800)
    brief = field(payload, "brief", 12000)
    images = decode_images(payload.get("images", []))
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter a public page link starting with https:// or http://.")
    prior_id = field(payload, "sourceRun", 350)
    selected = payload.get("sourceSteps")
    reuse = payload.get("sourceImages", False)
    if prior_id and not workflows:
        raise ValueError("Choose a workflow to reuse reviewed results.")
    if not isinstance(reuse, bool) or (not prior_id and (selected is not None or reuse)):
        raise ValueError("Choose a previous run to reuse its results or images.")
    carried = previous_results(prior_id, selected)
    if carried:
        for step in steps:
            step["checks"] = [*step["checks"], HANDOFF_CHECK]
    reused_images = []
    if reuse:
        paths = saved_images((ROOT / "tasks" / prior_id).resolve())
        if not paths:
            raise ValueError("The previous run has no saved images to reuse.")
        if len(paths) + len(images) > MAX_IMAGES:
            raise ValueError(f"Use up to {MAX_IMAGES} images across the previous and new run.")
        try:
            for path in paths:
                with path.open("rb") as image:
                    reused_images.append(check_image(image.read(MAX_IMAGE_BYTES + 1)))
        except OSError:
            raise ValueError("A saved image could not be read. Attach it again to use it.") from None
    if not (url or brief or images or carried):
        raise ValueError("Add a page link, describe what you want, or attach a screenshot.")
    provider = payload.get("provider", "codex")
    require(provider)
    return (product or (urlsplit(url).hostname if url else "Skill review"), url, brief,
            images, reused_images, steps, sources, provider, workflows, carried)


def save_run(directory, data):
    draft = directory / "run.tmp"
    with STATE_LOCK:
        stored = dict(data)
        if data.get("carried"):
            stored["carried"] = [
                {key: value for key, value in step.items() if key != "report"}
                for step in data["carried"]
            ]
        draft.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
        draft.replace(directory / "run.json")
    record = directory / "RECORD.md"
    record.write_text("\n".join([
        "# Evolve workflow batch" if data.get("workflows") else "# Selected Evolve skills",
        "", f"- Product: {data['product']}",
        f"- Status: {data['status']}", "",
        *[f"- {step['title']} ({step['id']}) — {step['status']}" for step in data["steps"]],
        "", f"Open in Evolve HQ: {data['view']}", "",
    ]), encoding="utf-8")


def get_run(run_id):
    directory = (ROOT / "tasks" / run_id).resolve()
    if not directory.is_relative_to(ROOT / "tasks") or not (directory / "run.json").is_file():
        return None
    with STATE_LOCK:
        data = load_json(directory / "run.json")
    if data["status"] in {"queued", "working"}:
        if process_running(data["pid"]) is False:
            data["status"] = "interrupted"
    data.pop("pid", None)
    data.pop("carried", None)
    data["imageCount"] = len(saved_images(directory))
    return data


def run_steps(provider, data, directory, files, sources, fields):
    record = directory / "RECORD.md"
    try:
        data["status"] = "working"
        save_run(directory, data)
        run_batches(
            data, directory, files, fields, sources,
            lambda folder, prompt, inputs: reply(provider, folder, prompt, files=inputs),
            save_run, Lock(),
        )
    except Exception as error:
        logging.exception("Evolve HQ skill run failed")
        data["status"] = "failed"
        data["error"] = (str(error) if isinstance(error, RuntimeError)
                         else "The run stopped. Any finished reports are still here.")
        for step in data["steps"]:
            if step["status"] in {"working", "queued"}:
                step["status"] = "failed" if step["status"] == "working" else "skipped"
                update(record, step["title"], data["product"], step["role"], "failed",
                       "The selected run stopped. Open the run for details.")
        save_run(directory, data)
    finally:
        RUN_LOCK.release()


def start_run(payload):
    product, url, brief, images, reused_images, steps, sources, provider, workflows, carried = validate(payload)
    if not RUN_LOCK.acquire(blocking=False):
        raise RuntimeError("A skill run is already in progress. Wait for it to finish before starting another.")
    try:
        directory = new_task(product, "skill-run")
        files = []
        for label, attachments in (("supplied", images), ("reused", reused_images)):
            for idx, (extension, body) in enumerate(attachments, 1):
                file = directory / f"{label}-image-{idx}.{extension}"
                file.write_bytes(body)
                files.append(file)
        run_id = directory.relative_to(ROOT / "tasks").as_posix()
        from urllib.parse import quote
        data = {"id": run_id, "product": product, "status": "queued", "steps": steps, "provider": provider,
                "workflows": workflows, "carried": carried,
                "view": "/workflows?run=" + quote(run_id, safe=""), "pid": os.getpid()}
        save_run(directory, data)
        if not (queued := get_run(run_id)):
            raise OSError("Run could not be saved.")
        Thread(target=run_steps,
               args=(provider, data, directory, files, sources, (product, url, brief)),
               daemon=True).start()
        return queued
    except Exception:
        RUN_LOCK.release()
        raise
