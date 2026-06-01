# Codex Automata: Agent Operating Instructions

This repository follows the Codex Automata methodology. All AI agents operating in this codebase must follow these rules.

## Core Doctrine

1. Research informs decisions. Investigate before specifying.
2. Documentation comes first. SDK comes second. Tests come third. Code comes last.
3. Specifications are the primary engineering artifact.
4. The SDK is the constraint surface. Tests are the mold. Code is the casting.
5. Build local-first. Design for the smallest viable model, expand to frontier as needed.
6. Do not write tests or implementation before the specification and SDK exist.
7. Do not introduce abstractions outside the SDK. If new building blocks are needed, request SDK extension.

## Constraints

- Do not expand scope without updating the specification first.
- Do not silently change interface contracts or SDK interfaces. Both are frozen before code casting begins.
- Do not bypass failing tests. Fix the implementation or surface the test as incorrect.
- Do not create abstractions outside the SDK constraint surface. If you need a type, interface, or pattern not in the SDK, stop and request extension through the specification pipeline.
- Do not create duplicate abstractions. Check existing SDK modules and interface contracts before adding new ones.
- Keep context lean. Specifications, prompts, and task definitions must be modular and retrievable in fragments. Do not assume unlimited context windows.
- Prefer small, atomic commits traceable to specification sections.
- Surface ambiguity instead of guessing. If the specification is unclear, stop and ask.
- Every task must map to a specification section, an SDK interface, and at least one test case.
- Explain deviations. If you must deviate from the specification, document why.
- When you discover code without a corresponding specification, SDK interface, or tests, halt and report the gap. Do not work around it or derive specs or tests from existing code. Use `templates/gap-assessment-template.md` for triage.

## Workflow

When given a task:

1. If the task involves technology decisions or unfamiliar domains, perform or locate research first.
2. Locate the relevant specification in `docs/` or the project's spec directory.
3. Locate the SDK interfaces that define the constraint surface for this task.
4. Locate the corresponding test plan and test cases (written against SDK interfaces).
5. Implement only what the specification, SDK, and tests require. Stay within the SDK boundary.
6. Verify all tests pass before marking the task complete.
7. If the specification, SDK, or tests are missing, stop and report this before proceeding.

## Directory Guide

- `docs/` is for project documentation: specifications, architecture decisions, interface contracts.
- `sdk/` is for the SDK constraint surface: types, interfaces, and building blocks.
- `tests/` is for test plans and test code (written against SDK interfaces).
- `tasks/` is for agent task definitions.
- `review/` is for human review records.
- `src/` is for source code (the castings, implementing SDK interfaces).
- `templates/` contains reusable templates. Copy them into `docs/`, `tests/`, or `tasks/` as needed.
- `agent/` contains detailed agent operating rules for each phase (spec writing, SDK design, test molding, code casting, review).
- `scripts/` contains enforcement scripts: `divergence-gate` (slop fingerprint scanner), `spec-check` (spec-before-code gate), `commit-lint` (commit traceability). Run them locally or in CI.
- `PLAYBOOK.md` contains the phase-by-phase methodology guide.

If your project includes a `.cursor/` directory, it provides optional Cursor IDE integration only. All AI coding tools should follow this file and `agent/`.

For the complete agent operating manual, see `agent/AGENT_RULES.md`.

## Terminology

Use these terms consistently: **research**, **specification**, **SDK**, **constraint surface**, **building block**, **local-first**, **design identity**, **design token**, **deployment checklist**, **convergence**, **divergence gate**, **slop fingerprint**, **mold**, **casting**, **bounded context**, **interface contract**, **iteration**, **quality gate**, **quick change**, **accessibility**, **action classification**, **agent task**, **assembly pressure**, **brownfield**, **cost budget**, **generator**, **guardrail**, **human review**, **incident postmortem**, **invariant**, **flow**, **recovery**, **retrospective**, **gap assessment**, **spec gap**, **SDK gap**, **mold gap**, **multi-agent orchestration**, **coverage erosion**, **contract gap**, **product test**, **property-based test**, **user profile**, **test objective**, **token budget**, **UX budget**, **security audit**, **SDK extension**, **WCAG**.

See `reference/glossary.md` in the methodology repository (or your project's glossary copy) for canonical definitions.
