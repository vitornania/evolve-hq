---
name: analytics
description: "Check if your events and reporting answer the decision at hand. Use when the user asks to audit tracking and analytics."
---

# Audit tracking and analytics

Check if your events and reporting answer the decision at hand.

## Inputs

Event map, reporting examples, and key actions.

## Steps

1. Identify the event that answers the business decision and its source of truth.
2. Check event definitions, duplicates, missing parameters, timezone, filters, and attribution windows.
3. Provide test events, expected values, and fixes ranked by measurement impact.

## Reconcile the event with the transaction

1. For each decision-critical event specify the trigger, unit, event and transaction identifiers, timestamp, currency, value basis, consent condition and owner. Separate a completed payment from a button click. Decide how retries, cancellations and refunds appear.
2. Trace a known transaction from the browser or server through reporting and the order ledger. If both paths send the purchase, deduplicate by a shared stable ID and check that distinct orders still appear. Reconcile raw events, unique orders, source-of-truth totals and the difference for the same window and time zone.
3. Define rates with explicit eligible denominators and attribution scope. Write an unavailable rate as unknown when its denominator is zero or missing. Expose gaps from consent, filtering, currency conversion or incomplete refunds before interpreting movement.

Compare the eligible population, attribution window and net contribution after mature refunds. Establish whether a comparison can support an incremental claim. See [Offers, positioning and acquisition](../evolve-skill/references/book-offer-decisions.md).

## Deliverable

A tracking checklist and recommended fixes.

Keep source details with the deliverable. Label assumptions and missing evidence. Preserve the scope and any approvals supplied by the user.

## Decision checks for this skill

Join reporting at its actual measurement grain and show missing IDs. Preserve delivery date and denominator when deriving a comparison.
