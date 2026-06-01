---
name: quick-change
description: Executes a small, bounded change against existing specifications and tests without running the full pipeline. Use when the user asks to fix a bug, tweak behavior, or make a minor change within an already-specified module.
disable-model-invocation: true
---

# Quick-Change Workflow

Follow this workflow for small changes that don't require the full pipeline.

## Step 1: Verify Quick-Change Criteria

Before proceeding, confirm ALL of the following:

1. The change touches a single bounded context.
2. An approved specification covers the affected behavior.
3. SDK interfaces exist for the affected module.
4. Tests exist that cover the affected area.
5. No new SDK types, interfaces, or extensions are needed.
6. No new specifications need to be written.
7. The change does not modify interface contracts.

If ANY criterion is false, stop and use the full pipeline (start with the appropriate phase).

## Step 2: Read Existing Artifacts

1. Read the specification section that covers the behavior being changed.
2. Read the SDK interfaces for the module.
3. Read the tests for the affected area.
4. Read the context state for current project status.

## Step 3: Make the Change

1. Implement the change within the existing SDK constraint surface.
2. Do not introduce new types, interfaces, or abstractions outside the SDK.
3. For user-facing changes, reference design tokens and follow the design identity.
4. Commit with a message referencing the specification section.

## Step 4: Verify

1. Run all existing tests for the module. All must pass.
2. If new edge cases are revealed, add tests (but if new behaviors are needed, escalate).
3. Run linters and quality checks.

## Step 5: Self-Review

1. Does the change stay within the specification? (Yes required)
2. Does it stay within the SDK constraint surface? (Yes required)
3. Do all tests pass? (Yes required)
4. Were any interface contracts modified? (No required)
5. Were any SDK interfaces modified? (No required)

If any answer is wrong, escalate to the full pipeline.

## Step 6: Report

1. Describe the change and which spec section it traces to.
2. Confirm all tests pass.
3. Note if the context state needs updating.

## Reference

- Reference: `reference/quick-change.md`
- Rules: `agent/AGENT_RULES.md`
