# Your first three jobs

## Review a store

1. Open **Workflows & skills** and choose **Review your store**.
2. Confirm **Review store copy and images** is listed in **Your run**.
3. Add a public product link or a screenshot of the first mobile screen. Include what buyers hesitate over if you know.
4. Click **Run selected skills**. Open the finished report for the first three fixes, draft copy, a gallery plan, and a test.

## Pick your own ad workflow

1. Click **Pick individual skills**, then search for “ad angles”.
2. Add **Find ad angles to test**. Add **Design a marketing test** if you want a test plan too.
3. Remove anything you don’t need. The list shows the order HQ will run.
4. Provide your product, buyer, and any customer observations. The second skill can use the first report.

## Browse references for a static ad

1. Expand **Browse static-ad libraries** on **Workflows & skills**. Add a Figma, Canva, Drive, or swipe link that you already have access to.
2. Add **Plan or build static ads** to your run. Include the test objective, target format, approved product facts, library sources or local exports, and available product assets.
3. When you want the best fit, ask the skill to review every template in the selected libraries. Expect a coverage count, a winner, and the reason it beat the alternatives. For a supplied reference, use **Adapt a reference ad** directly.
4. The workbench produces a brief and slot map. For output you can edit locally, open the project in your assistant's full terminal session and follow [local rendering](../skills/adapt-reference-ad/references/local-rendering.md). It produces a PNG and an editable SVG on Mac and Windows. Canva is optional.

## Calculate ROAS locally

In Terminal from the Evolve HQ folder:

```sh
python3 hq.py run roas examples/ad-metrics.csv --product "Example store"
```

Open the printed report location, or select the Performance Analyst in the live office and open the task record. The sample uses fictional results. To use your own export, keep the input columns `ad,spend,revenue,currency`. Report each market and attribution window clearly.

See **Free local tools** in the app for the other actions, including storyboards, creator queues, and Resolve handoffs.
