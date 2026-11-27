# Use and import skill libraries

## Use the included skills in your own tools

The source is one directory per skill under `skills/`. Each contains a complete `SKILL.md`. See the [Agent Skills specification](https://agentskills.io/specification).

```sh
python3 setup_hq.py skills all
```

This installs the bundled skills in `.agents/skills/` for Codex, Cursor, and Google and in `.claude/skills/` for Claude Code. Open a fresh session and ask it to use `store-content-cro-review` with a product link or screenshot. To install into another project, add `--workspace "/path/to/another/project"`.

After updating HQ, run the same command again. The installer recognizes unchanged public releases and refreshes those skill folders, including their local references. A folder with customized text or additional files stays in place and appears in the list of kept skills. To switch a kept skill to the bundled version, move the whole folder to a backup location and rerun the installer. Custom libraries installed with `--source` keep any existing same-named destinations.

Native installs in another project contain the chosen skill files and their bundled resources. The HQ browser workbench resolves an authorized course overlay locally as described below.

## Use an authorized full Evolve library in the office

If you have an approved Evolve package with the original instruction files, references, and templates, extract it to a folder. Then run:

```sh
python3 setup_hq.py import-evolve "/path/to/extracted-evolve-library"
```

For matching skills, HQ gives the writer and reviewer both the installed course method and the bundled skill guide. Each resolves references from its own folder. The saved quality review records the paths and hashes of the instruction files supplied to the provider. When a reviewer cites a separate local text reference, HQ checks its excerpt against the file and shows the decision it supported under **Quality review**. The imported files live under `.office/libraries/`, which is ignored by Git. Import only libraries you trust. The app supplies the selected instructions to the AI provider you choose.

For a skill with additional local course materials, create `references/local-sources.md` inside that skill’s folder. Both the writer and reviewer receive its location when that skill runs. Use the index to point to readable source files within the skill library, with PDF page numbers or worksheet names and row numbers where available. This lets the reviewer verify which source informed a decision.

## Add Origins Ecommerce or Origins for Friends

Extract each authorized library into its own folder. Install it into a separate working project to keep same-named skills and their references together:

```sh
python3 setup_hq.py skills all --source "/path/to/extracted-origins" --workspace "/path/to/my-origins-project"
```

Use the resulting skills in the native agent from that project. The office workbench is cataloged for the 62 Evolve skills. You can attach your own project context as task inputs in the office or put your authorized research and reference files in your native workspace.

## Public contents

The public 62-skill library uses independently written instructions. Redistribution permission is needed for proprietary course documents, Discord messages and attachments, third-party tutorials, and any additional source packs. Users can import those packs locally when they have authorized access. Runtime examples use fictional products and records. Personal task history, chat transcripts, uploads, credentials, and existing project databases belong to each local installation.
