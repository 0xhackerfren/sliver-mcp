---
name: project-intake
description: Initializes a new project using Codex Automata templates and workflows. Use when the user asks to start a new project, set up a project, or initialize the harness.
disable-model-invocation: true
---

# Project Intake Workflow

Follow this workflow to begin a new project. The Codex Automata harness has already created the directory structure (`docs/`, `tests/`, `tasks/`, `review/`, `src/`). Your job is to fill it.

## Step 1: Project Intake

1. Copy `templates/project-intake-template.md` to `docs/intake.md`.
2. Work with the user to fill in: problem statement, business context, scope, constraints, success criteria.
3. Document open questions for later resolution.

## Step 2: Architecture

1. Copy `templates/architecture-decision-record.md` to `docs/` for each major decision.
2. Copy `templates/module-boundary-template.md` to `docs/` for each bounded context.
3. Copy `templates/interface-contract-template.md` to `docs/` for each module boundary.
4. Help the user decompose the system into bounded contexts.

## Step 3: Prepare for Specification

1. Create a spec file for each bounded context using `templates/spec-template.md`.
2. The user writes the specifications (invoke `/spec-writing` for guidance).

## Step 4: SDK Design

1. For each bounded context, translate specifications and interface contracts into a compilable SDK constraint surface: types, interfaces, building blocks, and extension points.
2. Place SDK artifacts under `sdk/` per project layout.
3. Invoke `/sdk-design` for guidance if available, or follow `agent/` SDK design rules.
4. After the SDK constraint surface is complete for a module, proceed to test molding for that module.

## Step 5: Test Molding

1. After specs and SDK exist for a module, invoke `/test-molding` to derive executable molds from specification language, written against SDK interfaces.

## Reference

- Templates: `templates/` directory
- Playbook: `PLAYBOOK.md`
