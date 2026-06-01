---
name: code-casting
description: Implements code against tests and specifications within bounded module boundaries. Use when the user asks to implement, code, or cast a module.
disable-model-invocation: true
---

# Code Casting Workflow

Follow this workflow to implement a module.

## Step 1: Read Before Writing

1. Read the agent task definition to understand scope and boundaries.
2. Read the specification for the target module.
3. Read the test plan and locate all test cases assigned to this task.
4. Read the interface contracts for modules this implementation touches.

## Step 2: Verify Preconditions

1. Confirm the specification exists and is approved.
2. Confirm the tests exist and are in red state (compiling but failing).
3. Confirm interface contracts are frozen.
4. For user-facing modules, confirm the design identity document exists and design tokens are available in the SDK. If no design identity exists, stop and report the gap.
5. If any precondition is not met, stop and report.

## Step 3: Implement

1. Start with the simplest failing test.
2. Write the minimal code to make it pass. For user-facing code, reference design tokens for all visual values and follow the design identity's aesthetic direction and banned patterns.
3. Commit when a test passes (atomic commits).
4. Move to the next failing test.
5. Repeat until all assigned tests pass.

## Step 4: Verify

1. Run the full test suite for the module.
2. Run contract tests for interfaces this module provides.
3. Run any available linters and quality checks.
4. Verify no interface contracts were modified.

## Step 5: Report

1. List which tests now pass.
2. Note any deviations from the specification (there should be none).
3. Flag any issues encountered for human review.

## Reference

- Template: `templates/agent-task-template.md`
- Rules: `agent/CODE_CASTING_RULES.md`
