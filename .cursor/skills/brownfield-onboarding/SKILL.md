---
name: brownfield-onboarding
description: Guides adoption of Codex Automata on an existing codebase by auditing modules, classifying gaps, and producing a prioritized onboarding plan. Use when applying the methodology to a legacy or brownfield project.
disable-model-invocation: true
---

# Brownfield Onboarding Workflow

Follow this workflow to adopt Codex Automata on an existing codebase.

## Step 1: Inventory

1. Scan the codebase for modules, services, and significant code boundaries.
2. For each module, assess: risk level, change frequency, existing test coverage, existing documentation.
3. Fill in the brownfield audit template (`templates/brownfield-audit-template.md`).

## Step 2: Classify

1. Rank modules by priority (risk x change frequency).
2. Map dependencies between modules.
3. Identify existing assets to preserve (tests, docs, CI gates).
4. Classify gaps: how many spec gaps, mold gaps, SDK gaps, contract gaps exist?

## Step 3: Plan

1. Select the first module to onboard (highest priority).
2. Choose the starting adoption profile (usually Essential).
3. Define the onboarding phases with timelines.
4. Plan CI/CD integration (which gates, when, what scope).

## Step 4: Execute First Module

1. Apply the recovery protocol to the selected module:
   - Write the specification from domain knowledge (not from code).
   - Extract SDK types from the specification.
   - Derive tests from the specification.
   - Verify the existing implementation against new tests.
   - File gap assessments for failures.
   - Recast if needed.
2. Update the context state file with onboarding progress.

## Step 5: Expand

1. Repeat Step 4 for adjacent modules in priority order.
2. Define interface contracts as module boundaries are onboarded.
3. Upgrade the adoption profile when criteria are met.
4. Activate quality gates incrementally.

## Step 6: Report

1. Summarize modules onboarded and their status.
2. List remaining modules and estimated timeline.
3. Recommend profile upgrade when appropriate.

## Reference

- Template: `templates/brownfield-audit-template.md`
- Reference: `reference/brownfield-onboarding.md`
- Reference: `reference/recovery.md`
- Reference: `reference/adoption-profiles.md`
