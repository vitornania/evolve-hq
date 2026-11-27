# Your first jobs

## Run workflows together

1. Open **Workflows & skills**. Pick a mode in any of the six core workflows.
2. Check the stages you want and click **Add to run**. Add another workflow if it has its own inputs or can use the same starting brief. Put each workflow's objective in the brief if they differ.
3. Click **Start run**. Independent workflows run side by side. Each workflow works through its selected stages in order. A stage drafts its deliverable, checks every required criterion in a separate model call, and can revise and recheck up to twice. A dependent stage starts after every criterion passes. A blocked workflow leaves its draft and findings available while the others continue.
4. Open **Quality review** to see the finding and evidence for each criterion. After a research or brief run, click **Use reviewed results** to carry those outputs into a native or static ad. Use a new run when the next workflow needs an output that has yet to be produced.

Each stage and its quality review is a separate request to your chosen provider. Revisions target the failed criteria and get checked against the full list again. A passed review is an AI assessment. Inspect the final asset, factual claims, and any reported gaps before using it.

If the provider gives no answer, the workflow retries that call once. If a stage still needs input, open its review for the missing fact, image, or source and start again with that material.

| Workflow | How it uses your materials |
| --- | --- |
| Market Research | Indexes customer and competitor evidence, then turns it into a traceable customer insight or research brief. |
| Copywriting & Briefs | Locks the audience, desire, angle and grounded claims before drafting. The one-take mode checks the exact hook, single bridge and spoken delivery. |
| Native Ads | Uses the Evolve brief to draft and review native copy. Hook tests preserve the approved body and offer. |
| Static Ads | Reviews the selected library or reference, maps every visual and copy slot, and checks the evidence, typography and render handoff. |
| Review & Iterate Ads | Separates observations from performance findings, then tests a specific change to the parent ad. |
| Store Review & CRO | Audits the supplied page and gallery, prioritizes specific edits, and proposes a first conversion test. |

## Review a store

1. Open **Store Review & CRO** in **Workflows & skills**.
2. Choose the store audit mode and add it to **Your run**.
3. Add a public product link or a screenshot of the first mobile screen. Include what buyers hesitate over if you know.
4. Click **Start run**. Open the finished report for the first fixes, copy and image suggestions, and a test.

## Pick your own ad workflow

1. Click **All skills**, then search for “ad angles”.
2. Add **Find ad angles to test**. Add **Design a marketing test** if you want a test plan too.
3. Remove anything you don’t need. The list shows the order HQ will run.
4. Provide your product, buyer, and any customer observations. The second skill can use the first report.

## Browse references for a static ad

1. Expand **Browse static-ad libraries** on **Workflows & skills**. Add a Figma, Canva, Drive, or swipe link that you already have access to. Click **Include in run** to put it in the brief.
2. Open **Static Ads** and choose a mode. Include the test objective, target format, approved product facts, library links or local exports, and available product assets.
3. The template search accounts for the complete scoped library and separates visually reviewed templates from unavailable entries. For a supplied reference, choose the reference-adaptation mode.
4. The workbench produces a brief and slot map. For output you can edit locally, open the project in your assistant's full terminal session and follow [local rendering](../skills/adapt-reference-ad/references/local-rendering.md). It produces a PNG and an editable SVG on Mac and Windows. Canva is optional.

## Write a one-take script

1. Open **Copywriting & Briefs** and choose the one-take script mode.
2. Supply the exact hook, desire, angle, subject, and the evidence the speaker can use. Paste a previous script in the brief as a labeled comparison sample if you have one.
3. Read the final script aloud. Compare its opening, bridge, product reveal, support for factual lines, and close against your sample.

## Calculate ROAS locally

In Terminal from the Evolve HQ folder:

```sh
python3 hq.py run roas examples/ad-metrics.csv --product "Example store"
```

Open the printed report location, or select the Performance Analyst in the live office and open the task record. The sample uses fictional results. To use your own export, keep the input columns `ad,spend,revenue,currency`. Report each market and attribution window clearly.

See **Free local tools** in the app for the other actions, including storyboards, creator queues, and Resolve handoffs.
