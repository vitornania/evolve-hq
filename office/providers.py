"""Read-only adapters for locally installed AI command-line tools."""
import json
import os
from pathlib import Path
import shutil
import subprocess

PROVIDERS = {
    "codex": ("Codex", ("codex",)),
    "claude": ("Claude Code", ("claude",)),
    "cursor": ("Cursor CLI", ("cursor-agent", "agent")),
    "antigravity": ("Google Antigravity", ("agy",)),
    "gemini": ("Gemini CLI", ("gemini",)),
}


def find(provider):
    folders = [Path.home() / ".local/bin", Path.home() / ".antigravity/bin"]
    if os.name == "nt":
        folders.extend([Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "npm",
                        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "agy/bin"])
    for candidate in PROVIDERS[provider][1]:
        installed = shutil.which(candidate)
        if installed:
            return installed
        for folder in folders:
            installed = shutil.which(str(folder / candidate))
            if installed:
                return installed
    return None


def status():
    return [{"id": key, "label": label, "installed": bool(find(key))}
            for key, (label, _) in PROVIDERS.items()]


def require(provider):
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ValueError("Choose a supported AI provider.")
    executable = find(provider)
    if not executable:
        label = PROVIDERS[provider][0]
        raise ValueError(f"Install {label} first, then follow its sign-in steps in the setup guide.")
    return executable


def command_for(provider, executable, prompt, files, schema):
    if provider == "codex":
        command = [
            executable, "exec", "--ignore-user-config", "--skip-git-repo-check", "--ephemeral",
            "--sandbox", "read-only", "--disable", "apps", "--disable", "plugins",
            "--disable", "computer_use", "--disable", "hooks", "--disable", "multi_agent",
            "-c", 'approval_policy="never"', "--json",
        ]
        if schema:
            command.extend(["--disable", "shell_tool", "--disable", "unified_exec", "-c",
                            'web_search="disabled"', "--output-schema", str(schema)])
        else:
            command.extend(["-c", 'web_search="live"'])
        for picture in files:
            command.extend(["-i", str(picture)])
        return command + ["-"], prompt

    if schema:
        prompt += "\nReturn exactly one JSON object and no commentary or Markdown fences. Schema:\n"
        prompt += schema.read_text(encoding="utf-8")
    if provider == "claude":
        tools = "" if schema else "Read,Glob,Grep,WebFetch,WebSearch"
        return [executable, "--print", "--output-format", "json", "--permission-mode", "plan",
                "--strict-mcp-config", "--disallowedTools=mcp__*", "--no-session-persistence",
                "--setting-sources=", f"--tools={tools}"], prompt
    if provider == "cursor":
        return [executable, "--print", "--mode", "ask", "--output-format", "json",
                "--sandbox", "enabled", "--trust"], prompt
    if provider == "antigravity":
        return [executable, "--mode", "plan", "--sandbox", "--disable-slash-commands",
                "--output-format", "text", "--print=" + prompt], ""
    return [executable, "--approval-mode", "plan", "--sandbox",
            "--policy", str(Path(__file__).with_name("gemini-review.toml")),
            "--allowed-mcp-server-names", "evolve-hq-no-mcp",
            "--output-format", "json", "--prompt", ""], prompt


def response_text(provider, output):
    if provider == "antigravity":
        return output.strip()
    reply = ""
    for line in output.splitlines() if provider == "codex" else (output.strip(),):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if provider == "codex":
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                reply = item.get("text") or reply
        elif provider == "gemini":
            reply = event.get("response") or ""
        elif not event.get("is_error"):
            reply = event.get("result") or ""
    return reply.strip() if isinstance(reply, str) else ""


def reply(provider, directory, prompt, *, files=(), schema=None, timeout=600):
    executable = require(provider)
    label = PROVIDERS[provider][0]
    command, prompt = command_for(provider, executable, prompt, files, schema)
    try:
        result = subprocess.run(command, cwd=directory, input=prompt, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label} took too long to reply. Try again.") from None
    text = response_text(provider, result.stdout)
    if result.returncode or not text:
        hints = (result.stderr or "").lower()
        if "quota" in hints or "limit reached" in hints:
            raise RuntimeError(f"{label} reported a usage limit. Check your provider account.")
        raise RuntimeError(f"{label} didn’t return an answer. Check its sign-in, workspace permissions, and usage.")
    return text
