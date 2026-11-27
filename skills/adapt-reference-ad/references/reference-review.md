# Review the library and transfer the message

## Start with product research

Use research from the exact product, variant, market, and offer. Locate the existing product research brief, voice-of-customer vault, account findings, and approved claim or offer evidence. Read the findings themselves and follow the source references for claims that drive the ad. Reuse a previous selected research report when it covers the current decision. Refresh changed product, offer, or proof facts.

If research is missing, do a focused evidence pass before selecting a template or writing publishable copy. Read the product page and available approved product documents, and investigate relevant customer objections, desires, or language from accessible sources. Use the existing customer or market research workflow if the user asks for deeper research. Keep category evidence separate from first-party product evidence. Use category research to choose what to test and what language to try. Use target-product evidence to establish what this product does and can claim. Treat a seller's stated outcome as a claim until appropriate substantiation is available.

Record one research handoff for the ad. Include the product and market, target buyer and buying situation, prioritized problem or desire, best-supported buyer benefit, product feature or mechanism that supports it, relevant proof and offer terms, and unresolved evidence. Cite source IDs or links with a short finding and scope for each. Mark unverified buyer assumptions and test hypotheses clearly. Sparse evidence can support a narrower test. It cannot support invented certainty.

Choose the reference for that handoff. In the replacement map, tie every material promise, benefit, proof, mechanism or offer to its supporting finding. Apply it to every image, callout and embedded graphic. The reference provides the message sequence and format. Its claims are evidence only for what the source ad says. When a required role lacks support, flag it before rendering or choose a better-fitting reference. A review-only job can return provisional options with evidence gaps clearly marked.

## Review the full library when choosing a template

1. Write the test objective, buyer, stage, supported benefits and proof, and visual or format constraints. Use the product research handoff before looking at templates.
2. Inventory every template and format variant in each authorized library in scope. Reconcile pagination and the known count for each source. When a PDF contains a multi-frame template board, count and inspect the individual layouts. Keep source links and IDs for exact duplicates and reuse an assessment only after confirming visual identity.
3. Review every candidate in batches. For each, log the actual headline and core message, copy sequence, proof dependencies, layout and assets, and a verdict with a reason. Use saved content and visual annotations if their assets and versions still match. OCR and tags speed up triage. A visual review includes the full frame, embedded images, icons, and legible text at a readable size.
4. Rank the eligible candidates by message and audience fit, direct support for all essential evidence slots, quality of the visual demonstration for the test, and production feasibility. Use aesthetic fit to resolve a close call. Inspect the finalists at full resolution and verify the exact source frame. Give the winner, runner-up, and decisive reasons.
5. Report the number inventoried, reviewed, excluded, unavailable, and any library whose complete count could not be verified. Resume the missing batches before claiming the best template across all sources. If a source stays inaccessible, qualify the recommendation to the coverage achieved.

For a coverage receipt, save the frozen inventory as JSON Lines with one `id` (or `creative_id`) per template. Save the review ledger as JSON Lines with each `id`, its `status` (`eligible`, `excluded`, or `unavailable`), and a `reason`. Run `python3 skills/adapt-reference-ad/scripts/check_coverage.py inventory.jsonl reviews.jsonl` (or `py -3` on Windows). The checker reconciles the records. Confirm the source inventories separately.

A browse-only request may list collections. A supplied-reference build starts with that reference.

## Map every source slot to the target

1. Transcribe every visible line and assign it a function. Common functions include a problem, desired outcome, benefit, mechanism, proof, offer, action, or qualifier. A product feature explains what it is. A benefit explains what the buyer gets or can do.
2. Preserve the original message sequence, sentence skeleton, location, line order, and copy hierarchy. Map benefit to supported benefit, mechanism to supported mechanism, and proof to comparable proof. For “When it comes to [benefit A] and [benefit B], [brand] has you covered,” match both outcomes to the chosen buyer and test. A flavor belongs in a sensory or flavor slot. It can fill a benefit slot only when taste is itself the tested benefit and the reference sells that benefit.
3. Apply the map throughout every output, including carousel pages, secondary panels, inset screenshots, callouts, icons, packaging, crops, and image variants. Include embedded text that is legible. Retain an approved target packshot's own label. Keep each icon and photo's meaning aligned with the copy it supports. Check both the image and the text after every replacement.
4. Check each new claim against the available target evidence. A product page can verify stated specs, instructions and offer terms. A testimonial, outcome, or comparative number requires appropriate target-specific evidence. If an essential role cannot be supported, choose the next eligible reference during a search. For a locked reference, mark the exact adaptation blocked when a required proposition has no counterpart. This also applies when two promises share a headline and only one is supported. Record the evidence separately for each promise. A one-benefit alternative needs its own test label and must not be counted as a faithful two-benefit adaptation.
5. Record each slot's source words or asset, role, evidence, replacement, line count, and measured placement. Compare the finished result over the reference and at phone size. Read each badge on its own. An inclusion badge must name the actual item in the box, such as a cable, and its relationship to the offer. Keep the noun visible when adjusting line breaks.

## Match the type

Use editable layer metadata or original PDF font metadata first. Record the exact family, weight, style, internal PostScript name, size, width, tracking, leading and baseline. Load the actual licensed font and check several distinctive characters and widths against the source. Preserve type metrics and write copy to fit the available slot. Check line breaks and the final render. For raster-only sources, an inferred font stays provisional until the font file or source metadata verifies the match.
