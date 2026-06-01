---
name: spec-writing
description: Guides specification writing following the Codex Automata methodology. Use when the user asks to write a spec, create a specification, or define module behavior.
disable-model-invocation: true
---

# Specification Writing Workflow

Follow this workflow when writing a new specification.

## Step 1: Gather Context

1. Identify the module or feature being specified.
2. Read the project intake document if one exists.
3. Read the architecture documents to understand the bounded context.
4. Read any existing interface contracts the module participates in.

## Step 2: Create the Specification

1. Copy `templates/spec-template.md` into the project's docs directory.
2. Fill in the metadata section (module name, bounded context, version, date).
3. Write the Overview: one paragraph describing what this module does and why.
4. Define the Scope: what is included, what is explicitly excluded.

## Step 3: Define the Domain Model

1. List all entities and value objects.
2. Define fields with types, constraints, and relationships.
3. Note which fields are required vs optional.

## Step 4: Specify Behaviors

For each behavior the module must support:
1. Write a clear description of the behavior.
2. Define preconditions (what must be true before).
3. Define postconditions (what must be true after).
4. Define error conditions (what can go wrong and what happens).

## Step 5: Document Edge Cases and Failure Modes

1. Enumerate edge cases with expected behavior.
2. Document failure modes (dependency failures, resource exhaustion, invalid input).

## Step 6: Review

1. Verify every behavior is testable.
2. Verify no vague language remains.
3. Flag any Open Questions for human resolution.

## Reference

- Template: `templates/spec-template.md`
- Rules: `agent/SPEC_WRITING_RULES.md`
