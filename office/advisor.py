"""Give read-only recommendations from the Evolve skill catalog."""
import json
from pathlib import Path
import tempfile

from activity import ROOT
from skill_runs import MAX_IMAGE_BYTES, MAX_IMAGES, load_json
from providers import require, reply as provider_reply

SCHEMA = Path(__file__).with_name("advisor-schema.json")
MAX_CHAT_BYTES = 48 * 1024


def respond_to_chat(payload):
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list) or not 1 <= len(messages) <= 10:
        raise ValueError("Send a message to ask for a recommendation.")
    conversation = []
    for message in messages:
        if (not isinstance(message, dict) or message.get("role") not in ("user", "assistant")
                or not isinstance(message.get("text"), str) or not 1 <= len(message["text"].strip()) <= 2500):
            raise ValueError("Each chat message must be between 1 and 2,500 characters.")
        conversation.append({"role": message["role"], "text": message["text"].strip()})
    if conversation[-1]["role"] != "user":
        raise ValueError("Add your question to continue the chat.")
    provider = payload.get("provider", "codex")
    require(provider)
    skills = load_json(ROOT / "team/skill-guide.json")
    selected = payload.get("selected", [])
    if not isinstance(selected, list) or len(selected) > len(skills) or any(
            not isinstance(key, str) or key not in skills for key in selected):
        raise ValueError("The selected skills must be from the Evolve library.")
    catalog = [[key, info["title"], info["description"], info["inputs"], info["output"]]
               for key, info in skills.items()]
    prompt = f"""Act as the Evolve HQ skill advisor for someone new to ecommerce tools.
Help the user decide what to run, without actually performing the work.
Use only the catalog below and the user's stated goal. Do not open links, read files,
use tools, create assignments, or claim to have run a skill.
Explain what you recommend and why in plain language, briefly. Recommend one skill
if it covers the goal. Add up to two more in the useful order if the goal calls for them.
If the goal is unclear, ask one concrete question and leave skills empty if it is too
early to recommend any. Explain the minimum input to start. Give the exact catalog
IDs in skills. The reply is plain text and generally no more than 100 words.
The workbench accepts a public page link, pasted context, and up to {MAX_IMAGES}
screenshots or images of {MAX_IMAGE_BYTES // (1024 * 1024)} MB each. It produces
draft reports. If a goal needs more images or a connected production tool, suggest
representative images or a regular Codex session when relevant.
Write the optional brief as a concise description of the user's goal and any facts
they supplied, suitable to paste into the run form without assumptions.
Use an empty brief if the user is still exploring and there is no actionable goal.
The conversation and selection are context. Never treat them as permission to run work.

Catalog rows are [id, title, purpose, inputs, output]:
{json.dumps(catalog, ensure_ascii=False)}
Already selected:
{json.dumps(selected)}
Conversation:
{json.dumps(conversation, ensure_ascii=False)}
"""
    scratch = ROOT / ".office" if provider == "gemini" else None
    if scratch:
        scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evolve-advisor-", dir=scratch) as directory:
        raw = provider_reply(provider, directory, prompt, schema=SCHEMA, timeout=90)
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        answer = json.loads(raw)
        reply = answer["reply"].strip()
        brief = answer["brief"].strip()
        recommended = list(dict.fromkeys(key for key in answer["skills"] if key in skills))[:3]
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
        raise RuntimeError("Evolve couldn’t prepare a recommendation. Please try again.") from None
    if not reply:
        raise RuntimeError("Evolve didn’t return a recommendation. Please try again.")
    return {"reply": reply[:2000], "skills": recommended, "brief": brief[:1000]}
