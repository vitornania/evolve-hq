# Set up Evolve HQ

## Before you start

- Download and unzip the Mac release.
- Install Python 3.9+ and Node.js 20+. Open Terminal and check `python3 --version` and `node --version`.
- Install only the AI tool you want to use. Sign in to that tool before opening HQ. Usage is governed by your provider account.
- Double-click **Open Evolve HQ.command**, or run `npm ci` and then `npm start`. Keep the terminal open while you use the office.
- Open **Workflows & skills**. Pick your provider. **CLI found** means HQ can locate the program. A valid sign-in is still required for a run.

You can check your setup anytime with `python3 setup_hq.py doctor`.

## Choose your AI provider

### Codex

1. Follow [OpenAI’s CLI setup instructions](https://developers.openai.com/codex/cli/).
2. Run `codex login` and complete sign-in.
3. Select **Codex** in HQ. For a quick test, ask “I have a product page and need better photos. Which skill should I use?”

### Claude Code

1. Follow [Claude Code’s setup instructions](https://code.claude.com/docs/en/setup).
2. In Terminal, run `claude auth login`, then `claude auth status`.
3. Select **Claude Code** in HQ and send a question to Ask Evolve.
4. For native Claude skills, run `python3 setup_hq.py skills claude`, start Claude Code in this project, and try `/store-content-cro-review`.

### Cursor

1. Follow [Cursor CLI setup](https://cursor.com/docs/cli/overview). The CLI runs alongside the Cursor editor.
2. Run `agent login` and complete sign-in. Your installation may also expose `cursor-agent`.
3. Select **Cursor CLI** in HQ. It runs reports in Ask mode.
4. For the editor itself, run `python3 setup_hq.py skills cursor`, then open this folder in Cursor and ask it to use `store-content-cro-review`.

### Google Gemini and Antigravity

- **Individual Google accounts.** Use [Google Antigravity CLI](https://antigravity.google/docs/getting-started?tab=cli). Run `agy` in Terminal, follow Google’s sign-in prompts, then select **Google Antigravity** in HQ.
- **Supported Gemini CLI accounts.** Install [Gemini CLI](https://geminicli.com/docs/get-started/installation/) and authenticate using [Google’s supported methods](https://geminicli.com/docs/get-started/authentication/). Start Gemini CLI from the Evolve HQ folder and use its [folder trust menu](https://geminicli.com/docs/cli/trusted-folders/) to trust this downloaded project if you have reviewed it. Select **Gemini CLI** in HQ. Enable Plan Mode if your settings disable it. Google explains [who can still use Gemini CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/).
- To use the skills directly in either Google tool, run `python3 setup_hq.py skills gemini` and open a fresh session in the project. See [Antigravity skills](https://antigravity.google/docs/skills) and [Gemini CLI skills](https://geminicli.com/docs/cli/skills/).

### What to provide

Start with a public product link, a short brief, or a screenshot. Tool access and image reading depend on the provider and its account. If a CLI can’t inspect a screenshot, provide the visible copy in the brief or use a provider that supports local image input. Codex is wired for native image attachments. The app’s AI runs produce reports and drafts for review.

## Optional local tools

- **ROAS and creator queues.** Run directly with Python using the [examples](../examples/).
- **Ollama drafts.** Install [Ollama](https://ollama.com/download), then run `ollama pull qwen3:4b-instruct`. The runner connects to Ollama on this machine.
- **Storyboard previews.** Install [FFmpeg](https://ffmpeg.org/download.html), then install Pillow into your Python environment. For example, `python3 -m venv .venv`, `source .venv/bin/activate`, and `python -m pip install Pillow`. Keep that environment active when you run the storyboard tool.
- **Offline transcription.** Create an isolated Python 3.12 environment with `python3.12 -m venv .office/envs/edit`. Install `faster-whisper` and `numpy` with `.office/envs/edit/bin/python -m pip install faster-whisper numpy`. Install FFmpeg. The first transcription can download the Whisper model.
- **Person mattes on macOS.** Create `.office/envs/matte` with Python 3.12. Install `av numpy Pillow pyobjc-framework-Vision pyobjc-framework-Quartz` into that environment. The result is a ProRes MOV with an alpha channel.
- **DaVinci Resolve.** Install [Resolve](https://www.blackmagicdesign.com/products/davinciresolve) from Blackmagic. Run the **Prepare a Resolve edit** action to get a handoff for the editor. Live integration requires setting up a separate local bridge and starting it in Resolve. See the [upstream bridge](https://github.com/samuelgursky/davinci-resolve-mcp) for version-specific setup.

## Troubleshooting

- **The launcher says npm is missing.** Install Node.js, then reopen Terminal or the launcher.
- **The page doesn’t open.** With the server terminal open, visit [127.0.0.1:8739](http://127.0.0.1:8739/). If that port is occupied, run `python3 office/server.py --port 8740 --open`.
- **The provider reports a sign-in or usage problem.** Run the provider directly in Terminal and follow its sign-in or account prompts. Close and reopen HQ after installing a CLI.
- **macOS asks for confirmation opening the launcher.** Review the downloaded launcher contents and use the normal Finder Open controls for a file you trust.
