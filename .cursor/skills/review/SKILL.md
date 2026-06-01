---
name: review
description: Assists with human review by checking spec compliance, contract adherence, test coverage, and divergence. Use when the user asks to review code, prepare for review, or check a module against its spec.
disable-model-invocation: true
---

# Review Workflow

Follow this workflow to prepare or assist with a human review of a casting.

## Step 1: Gather Artifacts

1. Read the specification for the module under review.
2. Read the interface contracts the module participates in.
3. Read the test plan and verify which tests pass.
4. Read the design identity document (if user-facing).
5. Read the module's source code (the casting).

## Step 2: Specification Compliance

1. For each behavior in the specification, verify the casting implements it.
2. Check for missing behavior (spec says X, code does not do X).
3. Check for extra behavior (code does Y, spec does not mention Y).
4. Quote the specification section alongside any discrepancy found.

## Step 3: Contract Compliance

1. Verify the module honors all interface contracts it participates in.
2. Check that no contracts were silently modified during casting.
3. Verify contract test results.

## Step 4: Test Coverage

1. Verify every specification behavior has at least one passing test.
2. Check for tests that were skipped, disabled, or marked flaky.
3. Flag any specification behavior without test coverage.

## Step 5: Divergence Check (User-Facing)

1. Verify all visual values reference design tokens (no hardcoded hex, px, rem, font-family).
2. Check for banned patterns from the design identity's slop fingerprint catalog.
3. Verify aesthetic direction matches the design identity.
4. If the divergence gate script is available, run it and include results.

## Step 6: Produce Review Summary

1. Create a review document using `templates/human-review-template.md`.
2. List: checks that passed, potential issues, items requiring human judgment.
3. Flag findings without silently fixing them.
4. The human reviewer makes the final accept/reject decision.

## Reference

- Template: `templates/human-review-template.md`
- Rules: `agent/REVIEW_RULES.md`
- Divergence gate: `scripts/divergence-gate.sh` or `scripts/divergence-gate.ps1`
