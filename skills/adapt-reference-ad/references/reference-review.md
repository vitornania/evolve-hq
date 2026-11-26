# Review the library and transfer the message

## Review the full library when choosing a template

1. Write the test objective, buyer, stage, supported benefits and proof, and visual or format constraints. Read the product page and any supplied research before looking at templates.
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
4. Check each new claim against the available target evidence. A product page can verify stated specs, instructions and offer terms. A testimonial, outcome, or comparative number requires appropriate target-specific evidence. If an essential role cannot be supported, choose the next eligible reference during a search. For a locked reference, identify the gap before claiming the build is complete.
5. Record each slot's source words or asset, role, evidence, replacement, line count, and measured placement. Compare the finished result over the reference and at phone size.

## Match the type

Use editable layer metadata or original PDF font metadata first. Record the exact family, weight, style, internal PostScript name, size, width, tracking, leading and baseline. Load the actual licensed font and check several distinctive characters and widths against the source. Preserve type metrics and write copy to fit the available slot. Check line breaks and the final render. For raster-only sources, an inferred font stays provisional until the font file or source metadata verifies the match.
