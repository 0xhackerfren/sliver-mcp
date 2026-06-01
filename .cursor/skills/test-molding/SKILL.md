---
name: test-molding
description: Derives test cases from specifications to build the mold. Use when the user asks to write tests, create a test plan, or build the mold for a module.
disable-model-invocation: true
---

# Test Molding Workflow

Follow this workflow to derive tests from a specification.

## Step 1: Read the Specification

1. Read the specification document for the target module.
2. Note every numbered behavior, edge case, and failure mode.
3. Read the interface contracts to identify contract test targets.

## Step 2: Create the Test Plan

1. Copy `templates/test-plan-template.md` into the project's tests directory.
2. Fill in the metadata (module name, spec reference, date).
3. Build the specification coverage matrix: one row per spec behavior, one column per test case.

## Step 3: Write Unit Tests

For each behavior in the specification:
1. Create at least one test case.
2. Name the test to reference the spec section (e.g., test_create_task_empty_title).
3. Define input, expected output, and assertion.

For each edge case:
1. Create a dedicated test case.
2. Name it to reference the edge case.

## Step 4: Write Contract Tests

For each interface contract the module participates in:
1. Write tests that verify the contract from both sides.
2. Test normal operations and error conditions.

## Step 5: Derive Properties (if applicable)

1. Review each specification section for input constraints, data transformations, and invariants.
2. For each invariant, define a property-based test: the property statement, generator strategy, and expected invariant.
3. Add properties to the test plan's "Property-Based Tests" section.
4. Properties are red-state: they define what must hold before implementation exists.
5. At Complete profile, every spec section with input constraints must have at least one property. At Standard, properties are recommended. At Essential, optional.

## Step 6: Verify Red State

1. Confirm all tests compile.
2. Confirm all tests fail (no implementation exists yet).
3. If any test passes without implementation, it is testing the wrong thing.

## Reference

- Template: `templates/test-plan-template.md`
- Rules: `agent/TEST_MOLDING_RULES.md`
- Property-based testing: `reference/property-based-testing.md` (in methodology repo; or project copy of reference docs)
