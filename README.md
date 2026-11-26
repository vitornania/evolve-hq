# Evolve HQ

Run a 3D ecommerce office on your own computer. Choose one skill or combine several. Ask Evolve what to run, watch assignments in the live office, and read the reports in the same app.

**Quick start for Mac**

1. Download **evolve-hq-mac.zip** from [Releases](https://github.com/vitornania/evolve-hq/releases) and unzip it.
2. Install [Python 3.9 or newer](https://www.python.org/downloads/) and [Node.js 20 or newer](https://nodejs.org/). Install and sign in to one AI tool using the [provider tutorial](docs/SETUP.md#choose-your-ai-provider).
3. Double-click **Open Evolve HQ.command**. The launcher installs the web UI dependencies the first time. The office opens at **http://127.0.0.1:8739/**.
4. Choose **Workflows & skills**, select your AI provider, then try **Review your store**. Paste a product URL or attach a screenshot, then click **Run selected skills**.

Prefer Terminal? Open it in the project folder and run:

```sh
npm ci
npm start
```

Windows and Linux users can try the same Terminal setup with Python and Node installed. The Mac launcher and Apple Vision person matte are macOS-specific. The initial release was verified on macOS.

## Tutorials

| Guide | What you’ll learn |
| --- | --- |
| [Setup and AI providers](docs/SETUP.md) | Codex, Claude Code, Cursor, Google Antigravity, Gemini CLI, and optional media tools |
| [Your first three jobs](docs/FIRST-JOBS.md) | Review a storefront, select ad skills, and calculate ROAS |
| [Skills and original libraries](docs/LIBRARIES.md) | Use the 62 bundled skills in your editor or add authorized Evolve and Origins libraries |

## What’s included

- The 3D office, 13 roles, Ask Evolve, and a searchable library of 62 independently written skill guides.
- The local draft and media scripts, sample inputs, and role and handoff instructions.
- A project-level skill installer for Codex, Claude Code, Cursor, and Google.
- A local import path for an authorized full Evolve library.

The interface and job history run on loopback. AI chat and selected-skill runs use the signed-in provider you choose. Your inputs are shared with that provider when you submit them. Runs save reports in `tasks/`. The demo floor and deterministic tools such as ROAS can be used without an AI account.

Public copy and locally imported materials have separate licenses or permission conditions. See [Libraries](docs/LIBRARIES.md) before redistributing an imported pack.
