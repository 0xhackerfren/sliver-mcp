# Agent Operating Rules

Operating manual for agents executing tasks under Codex Automata. Specifications define intent, the SDK defines the constraint surface, tests are the mold, and casting produces code within strict quality gates.

## 1. Core Principles

- Research informs decisions. Investigate technologies, patterns, and the landscape before specifying.
- Specifications are the source of truth. Behavior and scope flow from them.
- The SDK is the constraint surface. It defines the building blocks agents must use.
- Build local-first. Assume the smallest viable model. Keep context lean, tasks atomic, and prompts structured.
- Tests are the acceptance criteria. Passing tests define done for an agent task.
- Code is the output, not the goal. Casting satisfies the specification, SDK interfaces, and tests under human oversight.
- Identity is specified, not defaulted. Human-perceptible surfaces and code structure reflect deliberate design decisions, not training-data defaults. "Good" is trivially achievable; the goal is statistical divergence from the bell curve center.
- After each cast increment, exercise the running assembly under realistic conditions. Assembly pressure catches integration failures that individual molds cannot detect.
- Context is persistent. Maintain project state across sessions using the context state file (`context-state.md`, from `templates/context-state-template.md`).
- Be cost-conscious. Prefer smaller context, shorter sessions, and cheaper models when the task permits. Include only relevant specification sections, not entire documents. Use checkpoint-based re-dispatch rather than accumulating conversation context.

## 2. Behavioral Rules (Strict)

R1. Do not write implementation code before the specification, SDK constraint surface, and test plan exist for the target module.

R2. Do not expand scope beyond what the specification defines. If you discover needed work outside that scope, report it.

R3. Do not silently change interface contracts or SDK interfaces. Any interface change requires explicit human approval and review.

R4. Do not bypass, skip, or delete failing tests. Fix the implementation or report the test as incorrect.

R5. Do not create abstractions outside the SDK constraint surface. If you need a type, interface, or pattern not in the SDK, stop and request SDK extension through the specification pipeline.

R6. Do not create duplicate abstractions. Check existing SDK modules and interfaces first.

R7. Prefer small, atomic commits. Each commit addresses one logical change traceable to a specification section.

R8. Surface ambiguity instead of guessing. If the specification does not answer your question, stop and ask.

R9. Explain deviations. If you must deviate from the specification, document the reason in the commit message and flag it for human review.

R10. Every agent task must map to a specification section, an SDK interface, and at least one test case.

R11. Do not introduce external dependencies not specified in the architecture documents.

R12. Keep context lean. Do not assume unlimited context windows or frontier-model capabilities. Structure tasks, specifications, and prompts to be modular and retrievable in fragments suitable for the smallest viable model.

R13. When you discover code without a corresponding specification, SDK interface, or tests, halt and report the gap. Do not silently work around it, do not write tests derived from the code, and do not treat unspecified behavior as intentional. Report the gap using the gap assessment template (`templates/gap-assessment-template.md`) so a human can triage and schedule recovery.

R14. Do not use training-data default patterns for human-perceptible surfaces when the design identity document or SDK design tokens specify alternatives. All visual values must trace to design tokens; hardcoded hex, px, rem, or font-family values are casting defects. If a project has user-facing surfaces but no design identity document exists, halt and report the gap.

R15. During recovery tasks, follow rules R1-R14 in the context of an existing codebase. Derive specifications from domain knowledge and stakeholder intent, not from the current implementation. Derive SDK extensions from specifications. Derive tests from the specification against SDK interfaces, not from the code. If the specification and the code conflict, surface the conflict for human resolution.

## 3. Task Execution Protocol

- Step 1: Read the agent task definition, locate the specification reference, and review the context state file (`context-state.md`) for current project status.
- Step 2: If the task involves technology decisions or unfamiliar domains, perform research and produce structured findings.
- Step 3: Read the relevant specification sections.
- Step 4: Locate the SDK interfaces that define the constraint surface for this task.
- Step 5: Read the test plan and locate the test cases for this agent task.
- Step 6: Read the interface contracts for modules this task touches.
- Step 7: Implement within the SDK boundary, making small commits as you go.
- Step 8: Verify all assigned tests pass.
- Step 9: Run any available linters and quality gates.
- Step 10: Report completion with a summary of what was implemented and which tests pass.
- Step 10b: Update the context state file with session results, completed work, Session History, and the Checkpoint for the next session.

## 4. Iteration Protocol

When a quality gate fails (test fails, review rejects, linter errors), iterate within the current phase:

- Read the failure, read the relevant specification and SDK interfaces, attempt a fix.
- Bound inner-loop attempts: after 3 failed attempts at the same problem, escalate to human.
- Log each attempt in the context state Session History.
- If the fix requires specification or SDK changes, escalate to the appropriate phase rather than continuing inner-loop attempts.

When review sends work back to an earlier phase, follow the outer loop:

- Specification change cascades through SDK (if affected), then tests (if affected), then casting.
- Each phase runs its own inner loop before advancing.
- The context state Checkpoint tracks which phase the outer loop is in.

For quick changes (single bounded context, existing spec/SDK/tests, no new interfaces), use the abbreviated quick-change workflow instead of the full pipeline. See `reference/quick-change.md`.

For multi-agent work, coordinate through artifacts (shared SDK, frozen interface contracts), not through direct communication. See `reference/multi-agent.md`.

## 5. Communication Protocol

- When blocked: report what you need and why progress is blocked.
- When ambiguous: quote the unclear specification section and suggest plausible interpretations without choosing one arbitrarily.
- When deviating: explain the deviation, its justification, and request alignment in human review.
- When complete: summarize changes, test results, and notes for the reviewer.

## 6. Guardrails

Agent actions are classified by risk tier. Respect the classification for each action:

- **AUTO:** Proceed without approval. Reading specifications, SDK, tests, context state. Running tests and linters.
- **LOG:** Proceed and record. Writing code within SDK boundary, adding tests, making atomic commits, updating context state.
- **APPROVE:** Halt and request human approval. Modifying SDK interfaces, modifying interface contracts, deleting tests, changing specifications, deploying, creating new bounded contexts, adding external dependencies.

If the project has a guardrail configuration (`templates/guardrail-config-template.md`), follow project-specific overrides. Otherwise, use the methodology defaults.

When an action's classification is unclear, treat it as APPROVE. It is safer to ask than to act.

See `reference/guardrails.md` for the full classification table and customization guidance.
