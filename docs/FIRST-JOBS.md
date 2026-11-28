# Your first jobs

## Start with one workflow

1. Open **Workflows & skills** and click a workflow. Its workspace opens in a new browser tab.
2. Choose what you want to do. The page shows what to bring and which steps are selected. Keep the suggested steps for a first run, or uncheck specific steps you do not need.
3. Answer the question beside the plan, add any useful link or images, and click **Start run**. The run and its reports stay in that tab.
4. Click the skill beside a step to open it by itself. **Skills available for this workflow** also lists tools for its other tasks.

## Run workflows together

1. Open **Workflows & skills**. Open **Combine workflows in one run**, then pick a mode in any of the six core workflows.
2. Check the stages you want and click **Add to run**. Add another workflow if it has its own inputs or can use the same starting brief. Put each workflow's objective in the brief if they differ.
3. Click **Start run**. Independent workflows run side by side. Each workflow works through its selected stages in order. A stage drafts its deliverable, checks every required criterion in a separate model call, and can revise and recheck up to twice. A dependent stage starts after every criterion passes. A blocked workflow leaves its draft and findings available while the others continue.
4. Open **Quality review** to see the finding and evidence for each criterion. After a research or brief run, click **Use reviewed results**, choose the reports you need, and optionally include the earlier images. Add the next job's brief and select a workflow. For a finished-ad review, attach the ad or its timecoded frames to the new run.

The run form shows what to bring for each selected workflow mode or individual skill.

For one task, open the individual skills library, select a skill and describe the exact deliverable. The writer and a separate review call both receive the selected method. Open **Quality review** to see which criteria passed and why. A draft can be revised twice. When you select several individual skills, each is checked separately and only approved results carry forward.

For an exact course exercise, name the method in the brief. Individual skills can load installed originals such as Evolve New Mechanisms, the Ideation Brief, or Perry’s native ad prompts. The draft and reviewer get the same available original. The public installation includes the portable decision guides. Attach an authorized local course pack for exercises that require its originals.

An individual image ad with an HQ preview layout must pass the same layout validation used by **Preview image**. Use the preview at phone size to check design quality before sharing the export.

Each receiving workflow gets the complete reviewed reports in its local `reviewed-inputs` folder. Its quality review checks the new work against those reports for exact wording, figures, source evidence and claim limits. When Copywriting hands a control to Native Ads for a hook test, the reviewer can compare the fixed body word for word. Review status means the work is ready to hand off for its stated scope. Check the report for deployment gates such as an unverified paired visual, outdated destination or an unsupported claim printed on locked packaging.

When you hand earlier work to **Analyze customer material I provide**, the first pass indexes the current brief, page and newly attached material. It saves that index before the next pass receives the earlier reports and images. That makes it possible to check whether a new interview really supports an old ad angle.

Each stage and its quality review is a separate request to your chosen provider. Revisions target the failed criteria and get checked against the full list again. A passed review is an AI assessment. Inspect the final asset, factual claims, and any reported gaps before using it.

If the provider gives no answer, the workflow retries that call once. If a stage still needs input, open its review for the missing fact, image, or source and start again with that material.

| Workflow | How it uses your materials |
| --- | --- |
| Market Research | Indexes customer and competitor evidence, then turns it into a traceable customer insight or research brief. |
| Copywriting & Briefs | Locks the audience, desire, angle and grounded claims before drafting. The one-take mode checks the exact hook, single bridge and spoken delivery. |
| Native Ads | Uses the Evolve brief to draft and review native copy. Hook tests preserve the approved body and offer. |
| Static Ads | Reviews the selected library or reference, maps every visual and copy slot, and checks the evidence, typography and render handoff. |
| Review & Iterate Ads | Diagnoses misses across the ad and the store, checks finished creative, and plans the next controlled test. |
| Store Review & CRO | Audits the supplied page and gallery, prioritizes specific edits, and proposes a first conversion test. |

## Find why shoppers hesitate

In **Market Research**, pick **Why are people hesitating to buy?** Paste a few real buyer comments or include the product link and what you’ve observed. The report gives you the strongest supported explanation, another possibility worth checking, and one action. When the evidence is thin, it gives you a precise question to ask or an observation to look for.

## Plan images for an existing story ad

In **Native Ads**, pick **Plan images for my story ad**. Paste the ad text in the brief or reuse the reviewed draft. You’ll get a first pick and a small set of distinct photo ideas tied to lines in the ad. Send a shot brief to a photographer or use **Copy image prompt** to take a generator-ready option to your image tool. If a shot needs to show a real result or product comparison, the brief tells you what evidence to supply.

## Make a first image ad

Open **All skills** and search for “make a picture ad.” Choose **Plan or build an image ad**, attach the product photo, and say you want one image. Add the product link or any confirmed product facts. When the reviewed layout is ready, click **Preview image** to check it at phone size and download a PNG or editable SVG. [Set up the local preview](SETUP.md#optional-local-tools) if HQ asks for it. The editable SVG uses the fonts installed on the computer that opens it.

## Check an individual skill on a practice brief

Run `python3 scripts/exercise_skills.py evolve-angles` from the HQ folder. You can list several skill IDs or select `--all` for all 62. This uses your signed-in provider for each draft, review and any revisions. Each exercise starts a fresh run. Open the report at the printed path and compare the actual decision with the expected result printed afterward. The [practice briefs](../examples/skill-quality-cases.json) use fictional products and include cases where declining a claim or requesting evidence is the correct decision.

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

For a new ad idea, choose **Shortlist original ad headlines** under **Static Ads**. Supply your buyer, product facts and customer observations. Pick a headline, then choose **Build an original static ad** and include the reviewed shortlist from the previous run.

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

## Diagnose a miss or review the final creative

- Choose **Diagnose an underperforming ad**. Supply the exact ad or transcript, its page and offer, and comparable delivery and purchase figures. Add checkout observations if available. The workflow ranks plausible causes against your evidence and proposes one change or one observation to collect.
- Choose **Review a finished ad before launch**. Attach the final image and give its version and approved brief. For video, attach representative frames and list their timestamps in the brief with the relevant transcript. The review names what it could inspect and any remaining footage or audio checks.

### Prepare video references and sound effects

With the optional Rea-video and Earshot tools installed, run these commands in a terminal from the folder containing your reference video:

```sh
rea-video decompose reference.mp4 -o reference-breakdown --lang en --no-vlm
earshot make "a soft click" --seed 17 -o reveal-click.wav
```

For **Ad Review**, open `reference-breakdown/report.html`, check the cuts and captions against the clip, and attach up to three representative frames with their timestamps. For **Copywriting**, those observations can help plan when the hook, demonstration and product reveal occur. Production-method labels are estimates.

For **Video Editing**, listen to the WAV against the actual cut. Include it with the footage, script and cue time when preparing the Resolve handoff. The commands above use local processing. Rea-video may download model files on first use. [Rea-video setup](https://github.com/JuneYaooo/rea-video) · [Earshot setup](https://github.com/Leonxlnx/earshot)

## Calculate first-order CPA

Open **Free local tools → Calculate break-even CPA** and enter average first-order revenue and costs from the same period and currency. Break-even CPA uses the contribution before ads. Target CPA also subtracts the contribution you want to keep per order. The tool runs locally without an AI provider. Click **Copy for ad review** to include the calculation in a Weekly Review brief alongside the same-basis acquisition figures.

To practice choosing between approaches, run `python3 scripts/check_judgment.py` or select a pair such as `python3 scripts/check_judgment.py review`. Each pair varies one fact. Compare the actual recommendations and their evidence with the expected decisions printed after both runs. This uses your selected signed-in provider.
