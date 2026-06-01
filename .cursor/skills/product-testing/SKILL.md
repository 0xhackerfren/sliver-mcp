---
name: product-testing
description: Defines and runs agentic product tests where AI agents operate the application as real users. Use when the user asks to create product tests, define user profiles, set UX budgets, or verify user journeys.
disable-model-invocation: true
---

# Product Testing Workflow

Follow this workflow to define and execute agentic product tests (Phase 6b).

## Step 1: Define User Profiles

1. Identify the user classes from the specification's user-facing sections.
2. For each class, create a user profile using `templates/user-profile-template.md`.
3. Define: technical literacy, domain knowledge, goals, constraints (accessibility, device, network), behavioral tendencies.
4. Include at least one constrained profile (screen reader, keyboard-only, mobile-only, slow network).

## Step 2: Define Test Objectives

1. For each critical user journey, write a goal-oriented objective.
2. Objectives are outcomes, not scripts: "As a new user, create an account and reach the dashboard."
3. Do NOT write step-by-step instructions. The point is testing discoverability.
4. Trace each objective to a specification section.

## Step 3: Set UX Budgets

1. For each objective and profile combination, set quantitative thresholds:
   - Click budget (maximum interactions)
   - Navigation depth (maximum page transitions)
   - Backtracking count (maximum backward navigations)
   - Error encounters (maximum user-facing errors)
   - Time budget (maximum wall-clock time, normalized)
2. Ground budgets in industry norms, accessibility standards, and product goals.
3. Start generous and tighten as baselines are established.

## Step 4: Create Product Test Documents

1. For each test, fill in `templates/product-test-template.md`.
2. Include: user profile reference, objective, preconditions, success criteria, UX budgets, spec traceability.

## Step 5: Execute Tests

1. The test agent adopts the user profile's behavioral model.
2. The agent uses the product through its user interface only (browser, screen reader, mobile emulator).
3. The agent does NOT use implementation knowledge.
4. The agent records every action, observation, hesitation, error, and recovery in a journey log.
5. If the agent cannot accomplish the objective, it reports exactly where it got stuck and why.

## Step 6: Evaluate Results

1. **Pass/fail**: Did the agent accomplish the objective?
2. **Budget compliance**: Did the journey stay within all UX budgets?
3. **Critical errors**: Did the agent encounter crashes, data loss, or security failures?
4. Record diagnostic metrics: click count, navigation depth, backtracking rate, confusion index.

## Step 7: Route Feedback

1. Specification defects go back to Phase 2.
2. Implementation defects go back to Phase 5.
3. Design defects require human judgment about spec revision.
4. Tighten budgets if journeys consistently beat them.

## Reference

- Templates: `templates/product-test-template.md`, `templates/user-profile-template.md`
- Reference: `reference/product-testing.md` (in the methodology repo)
- Playbook: `PLAYBOOK.md` (Phase 6b)
