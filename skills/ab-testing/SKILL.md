---
name: ab-testing
description: "Set up an experiment or interpret a test you already ran. Use when the user asks to plan or read an A/B test."
---

# Plan or read an A/B test

Set up an experiment or interpret a test you already ran.

## Inputs

Variants, traffic, conversions, and expected change, if known.

## Steps

1. Define success and guardrails, randomization unit, planned comparison, and sample target.
2. For completed tests, verify denominators, assignment imbalance, exposure window, and uncertainty.
3. Report what the data supports and the most appropriate next decision.

## Design the decision before reading results

1. State the buyer behavior to change, the proposed cause, and what the team will do if the improvement is too small to matter. Define the eligible population, randomization unit, exposure event, primary outcome, guardrail and observation window. Use the same unit for inference or account for clustering.
2. Use the baseline, economically meaningful effect, traffic, power and uncertainty target to plan sample and duration. Spell out the units. A rise from 5% to 5.5% is 0.5 percentage points and a 10% relative lift. A payment or refund outcome may need time to mature.
3. Check assignment imbalance, dropped exposures and outcome maturity before interpreting the point estimate. Honor the planned stopping rule or a valid sequential design. Report both arms with denominators and an interval when estimable. An interval spanning a material loss and gain supports another observation, even if one arm currently leads.

When planning a behavior test, define eligibility, comparison and downstream cost. Add a measure that would reveal buyers selecting the wrong item. See [Buyer behavior and evidence](../evolve-skill/references/book-customer-decisions.md).

## Deliverable

A test plan or interpretation with limitations.

Keep source details with the deliverable. Label assumptions and missing evidence. Preserve the scope and any approvals supplied by the user.
