---
name: sdk-design
description: Translates specifications and interface contracts into the SDK constraint surface. Use when the user asks to design the SDK, define types, create building blocks, or set up the constraint surface for a module.
disable-model-invocation: true
---

# SDK Design Workflow

Follow this workflow to translate specifications into the compilable SDK constraint surface.

## Step 1: Read Before Designing

1. Read the specification for the target bounded context.
2. Read all interface contracts this context participates in.
3. Read the architecture documents for module boundary definitions.
4. For user-facing modules, read the design identity document.
5. Read any existing SDK modules to avoid duplication.

## Step 2: Verify Preconditions

1. Confirm the specification is approved and peer-reviewed.
2. Confirm interface contracts exist for every module boundary.
3. For user-facing modules, confirm the design identity document exists. If missing, stop and report the gap.

## Step 3: Define Building Blocks

1. For each bounded context, create an SDK module (package or namespace).
2. Translate specification entities and value objects into types.
3. Translate interface contract schemas into shared types.
4. Translate error conditions into error enums or union types.
5. Define extension points where the spec indicates future growth.
6. For user-facing modules, create design tokens from the design identity (colors, typography, spacing, shadows, radii, breakpoints, motion).
7. Ensure every building block traces to a specification section.

## Step 4: Validate

1. The SDK must compile with no implementation behind it.
2. Every interface contract field must appear in SDK types.
3. No orphaned types (every type should be referenced by at least one planned mold).
4. No raw visual values in user-facing SDK modules (all must be named tokens).
5. No duplicate abstractions across modules.

## Step 5: Document and Report

1. Update the block registry (`templates/block-registry-template.md`) with new building blocks.
2. List which specification sections each building block traces to.
3. Flag any specification ambiguities discovered during design.
4. Report readiness for test molding.

## Reference

- Template: `templates/block-registry-template.md`
- Rules: `agent/SDK_DESIGN_RULES.md`
- Design identity: `templates/design-identity-template.md`
