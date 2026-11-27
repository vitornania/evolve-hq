# Evolve HQ

Run a 3D ecommerce office on your own computer. Choose a core workflow or an individual skill, watch assignments in the live office, and read the reports and quality reviews in the same app.

**Quick start for Mac and Windows**

1. Download the current source with **Code → Download ZIP** and unzip it. You can also use a packaged version from [Releases](https://github.com/vitornania/evolve-hq/releases).
2. Install [Python 3.9 or newer](https://www.python.org/downloads/) and [Node.js 20 or newer](https://nodejs.org/). Install and sign in to one AI tool using the [provider tutorial](docs/SETUP.md#choose-your-ai-provider).
3. On Mac, double-click **Open Evolve HQ.command**. On Windows, double-click **Open Evolve HQ.cmd**. The launcher installs the UI dependencies the first time and opens the office at **http://127.0.0.1:8739/**.
4. Choose **Workflows & skills**, select your AI provider, and open **Store Review & CRO**. Choose **Review store content and images**, add it to your run, then supply a product URL or screenshot and click **Start run**.

Prefer Terminal? Open it in the project folder and run:

```sh
npm ci
npm start
```

The Terminal setup also works with Python and Node on Linux. On Windows, use `py -3` in any example that calls `python3`. The optional video matte tool uses Apple Vision on Mac and a CPU foreground model on Windows and Linux.

## Tutorials

| Guide | What you’ll learn |
| --- | --- |
| [Setup and AI providers](docs/SETUP.md) | Codex, Claude Code, Cursor, Google Antigravity, Gemini CLI, and optional media tools |
| [Your first jobs](docs/FIRST-JOBS.md) | Run the six workflows, read quality reviews, reuse research, and calculate ROAS |
| [Skills and original libraries](docs/LIBRARIES.md) | Use the 62 bundled skills in your editor or add authorized Evolve and Origins libraries |

## What’s included

- The 3D office, 13 roles, Ask Evolve, six core workflows, and a searchable library of 62 independently written skill guides.
- The local draft and media scripts, sample inputs, and role and handoff instructions.
- A project-level skill installer for Codex, Claude Code, Cursor, and Google.
- A local import path for an authorized full Evolve library.

The interface and job history run on loopback. AI chat and selected-skill runs use the signed-in provider you choose. Your inputs are shared with that provider when you submit them. Runs save reports in `tasks/`. The demo floor and deterministic tools such as ROAS can be used without an AI account.

Public copy and locally imported materials have separate licenses or permission conditions. See [Libraries](docs/LIBRARIES.md) before redistributing an imported pack.
