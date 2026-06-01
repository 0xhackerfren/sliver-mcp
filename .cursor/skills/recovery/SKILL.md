---
name: recovery
description: Walks through the gap recovery protocol to close specification, SDK, test, or coverage gaps in existing code. Use when the user discovers a gap, asks to recover, or needs to retroactively add specs/tests.
disable-model-invocation: true
---

# Recovery Workflow

Follow this workflow when existing code lacks specifications, SDK interfaces, or tests.

## Step 1: Audit the Gap

1. Identify the affected module and the gap class:
   - **Spec gap**: behavior exists in code but is not documented in any specification.
   - **SDK gap**: behavior has no corresponding types or interfaces in the SDK.
   - **Mold gap**: behavior is in the spec but has no tests (or tests are too weak).
   - **Coverage erosion**: tests were deleted, disabled, skipped, or became flaky.
   - **Contract gap**: a module boundary has no contract tests despite a documented interface contract.
2. Document the gap using `templates/gap-assessment-template.md`.
3. Record: affected module, gap class, discovery trigger, severity, current state, required state.

## Step 2: Patch the Specification

1. If the spec is missing or incomplete, write it from domain knowledge and stakeholder intent.
2. Do NOT derive the specification from the current code. The code may be wrong.
3. If the spec and the code conflict, surface the conflict for human resolution.
4. Follow all spec-writing rules (`agent/SPEC_WRITING_RULES.md`).

## Step 3: Patch the SDK

1. If SDK types or interfaces are missing, derive them from the patched specification.
2. Follow SDK design rules (`agent/SDK_DESIGN_RULES.md`).
3. Ensure new SDK surface compiles with no implementation.

## Step 4: Patch the Mold

1. Derive tests from the patched specification against SDK interfaces.
2. Do NOT derive tests from the existing code.
3. Follow test molding rules (`agent/TEST_MOLDING_RULES.md`).
4. Run the tests. Some may fail against the existing code. This is expected.

## Step 5: Recast (If Needed)

1. If patched tests fail against existing code, fix the implementation.
2. Follow code casting rules (`agent/CODE_CASTING_RULES.md`).
3. Make small, atomic commits traceable to the gap assessment.

## Step 6: Re-Review

1. Submit the recovered module for human review.
2. The reviewer verifies: spec is complete, SDK covers boundaries, tests pass, casting matches spec.
3. Fill in the recurrence prevention section of the gap assessment.

## Step 7: Update State

1. Update `context-state.md` with the recovery outcome.
2. Close the gap assessment and mark the recovery kanban card as done.

## Reference

- Template: `templates/gap-assessment-template.md`
- Protocol: `reference/recovery.md` (in the methodology repo)
- Rules: R13 (halt and report gaps), R15 (recovery task behavior)
