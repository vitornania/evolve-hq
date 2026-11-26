# Use and import skill libraries

## Use the included skills in your own tools

The source is one directory per skill under `skills/`. Each contains a complete `SKILL.md`. See the [Agent Skills specification](https://agentskills.io/specification).

```sh
python3 setup_hq.py skills all
```

This copies skills into `.agents/skills/` for Codex, Cursor, and Google, and into `.claude/skills/` for Claude Code. Open a fresh session in this folder. Ask it to use `store-content-cro-review` with a product link or screenshot. Existing same-named folders are kept. Use `--workspace "/path/to/another/project"` to install into another project you own.

## Use an authorized full Evolve library in the office

If you have an approved Evolve package with the original instruction files, references, and templates, extract it to a folder. Then run:

```sh
python3 setup_hq.py import-evolve "/path/to/extracted-evolve-library"
```

HQ will use that local copy for matching skills, with internal folder paths and supporting materials intact. The imported files live under `.office/libraries/`, which is ignored by Git. Import only libraries you trust. The app supplies the selected instructions to the AI provider you choose.

## Add Origins Ecommerce or Origins for Friends

Extract each authorized library into its own folder. Install it into a separate working project to keep same-named skills and their references together:

```sh
python3 setup_hq.py skills all --source "/path/to/extracted-origins" --workspace "/path/to/my-origins-project"
```

Use the resulting skills in the native agent from that project. The office workbench is cataloged for the 62 Evolve skills. You can attach your own project context as task inputs in the office or put your authorized research and reference files in your native workspace.

## Public contents

The public 62-skill library uses independently written instructions. Redistribution permission is needed for proprietary course documents, Discord messages and attachments, third-party tutorials, and any additional source packs. Users can import those packs locally when they have authorized access. Runtime examples use fictional products and records. Personal task history, chat transcripts, uploads, credentials, and existing project databases belong to each local installation.
