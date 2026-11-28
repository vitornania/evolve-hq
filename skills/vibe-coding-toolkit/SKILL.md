---
name: vibe-coding-toolkit
description: "Turn an app or workflow request into implementation and verification steps. Use when the user asks to plan a technical improvement."
---

# Plan a technical improvement

Turn an app or workflow request into implementation and verification steps.

## Inputs

The feature, problem, or codebase context.

## Steps

1. Turn the request into an observable acceptance case. Identify the normal entry point, existing state and failure or retry most likely to break it. For planning-only work, distinguish confirmed behavior from details requiring repository access.
2. Inspect existing callers and persistence boundaries before changing behavior. Reuse the normal code path. For work that can be retried or run concurrently, identify the durable identity and atomic boundary needed to avoid duplicate effects. Preserve compatibility with existing data where the change touches its shape.
3. Verify the happy path and the consequential failure or concurrency case through the user's entry point. Check the resulting state or artifact, not only the response. Distinguish a proposed check from one actually run and keep setup assumptions in the handoff.

## Deliverable

Return the smallest complete plan or implementation for the requested scope, its acceptance result and any unverified behavior. Use the installed project workflow references for larger technical builds.

## Decision checks for this skill

Make a small change with an explicit locked baseline. Use fixture replays and, for rendering changes, compare outputs on known source material.
