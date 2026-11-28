"""Keep the user brief, exact source versions and reviewed output IDs distinct."""
import hashlib
import json


def creative_context(identity, product, url, brief, version, parent, change, files):
    return {
        "brand": identity.get("brand", ""),
        "product": product,
        "url": url,
        "brief": brief,
        "version": version,
        "parent": parent,
        "change": change,
        "assets": [{"file": path.name, "sha256": file_digest(path)} for path in files],
    }


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reviewed_id(run_id, step_id, artifact):
    scope = hashlib.sha256(json.dumps([run_id, step_id]).encode()).hexdigest()[:12]
    return f"hq-report-{scope}-{file_digest(artifact)[:16]}"


def idea_id(identity, idea):
    scope = identity.get("key")
    if not scope or not idea:
        return ""
    normalized = " ".join(idea.casefold().split())
    digest = hashlib.sha256(json.dumps([scope, normalized]).encode()).hexdigest()[:20]
    return f"hq-idea-{digest}"


def creative_prompt(creative):
    if not creative:
        return ""
    details = {key: value for key, value in creative.items() if key != "brief" and value}
    return (
        "\n\nShared run brief. Use only fields relevant to this job. Ground current SKU, offer, buyer situation "
        "and proof in supplied or inspected sources. Carry an approved creative idea and its evidence forward "
        "when appropriate. Treat suggestions as proposals and separate missing facts from approved locks. "
        "For an iteration, compare the exact parent and name intended and collateral changes. For performance, "
        "only a version matched to this asset by evidence supports a version-specific finding. "
        "User-entered version IDs are labels. Source hashes identify file bytes.\n"
        + json.dumps(details, ensure_ascii=False)
    )
