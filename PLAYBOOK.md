# Codex Automata Playbook

A practical, phase-by-phase implementation guide for running a software project under the Codex Automata methodology.

## Overview

Every project follows the same sequence:

```
Phase 0: Idea Intake (with Research)
Phase 1: Architecture and Decomposition (with Research)
Phase 2: Specification Writing
Phase 3: SDK Design
Phase 4: Test Molding
Phase 5: Code Casting
Phase 6: Review
Phase 6b: Product Testing
Phase 7: Deployment and Observation
```

Research runs throughout the early phases: agents investigate technologies, survey existing solutions, and produce structured findings that inform specifications and architectural decisions. Research is not a separate phase but a continuous activity that feeds Phases 0-2.

The pipeline enforces a strict order: documentation first, then SDK, then tests, then code. Phases may iterate (a review can send work back to specification), but they do not skip forward. You do not cast without a mold. You do not mold without an SDK. You do not build an SDK without a specification. You do not specify without investigating.

For Cursor IDE users: each phase references the relevant `/skill-name` you can invoke in chat and the `.cursor/agents/` subagents available for delegation.

---

## Quick Changes

Not every change requires the full pipeline. Bug fixes, configuration tweaks, copy corrections, and small behavioral adjustments that touch a single bounded context with existing specifications, SDK interfaces, and tests can use the abbreviated quick-change workflow.

**Criteria (all must be true):** The change touches a single bounded context. An approved specification covers the behavior. SDK interfaces exist. Tests exist. No new SDK types, interfaces, or specs are needed. No interface contracts are modified.

**Sequence:** Read existing spec, SDK, and tests. Make the change within the constraint surface. Verify all tests pass. Self-review against a checklist. Commit referencing the spec section.

**When to escalate:** If any criterion fails, if you discover a spec gap, if you need a new SDK type, or if the change affects multiple contexts, escalate to the full pipeline starting at the appropriate phase.

Quick-change is available at all adoption profiles. Use `/quick-change` in Cursor. See `reference/quick-change.md` for the full protocol.

---

## Guardrails

Every agent action in the pipeline is classified by risk: AUTO (proceed), LOG (proceed and record), or APPROVE (halt for human). This classification applies across all phases.

**Phase-specific guidance:**

| Phase | Typical AUTO | Typical LOG | Typical APPROVE |
|-------|-------------|-------------|-----------------|
| 0-1: Intake/Architecture | Reading codebase, researching | Producing structured findings | Finalizing architecture decisions |
| 2: Specification | Reading existing docs | Writing spec sections | Approving completed specification |
| 3: SDK Design | Reading specs and contracts | Defining types and interfaces | Freezing SDK surface for casting |
| 4: Test Molding | Reading spec and SDK | Writing test cases | N/A (tests are additive) |
| 5: Code Casting | Reading spec/SDK/tests | Writing code, making commits | Modifying SDK or contracts |
| 6: Review | Reading all artifacts | Producing review notes | Approving or rejecting the casting |
| 6b: Product Testing | Running product tests | Recording journey metrics | Changing UX budgets |
| 7: Deployment | Running smoke tests | Executing deploy steps | Triggering production deploy |

Teams customize classification using the guardrail config template. See `reference/guardrails.md`.

---

## Brownfield Adoption

Most real-world projects aren't greenfield. To adopt Codex Automata on an existing codebase, use the brownfield onboarding protocol rather than the forward pipeline.

**Sequence:** Install the harness, audit the codebase using the brownfield audit template, classify modules by risk and change frequency, then onboard modules one at a time using the recovery protocol. Start with the Essential profile on the highest-risk module. Expand outward as modules are onboarded.

**Key principle:** Recovery IS onboarding. Every brownfield module goes through the recovery sequence: write the spec from domain knowledge (not code), extract SDK types, derive tests, verify or recast the implementation.

**Quality gates are incremental.** Gate new PRs immediately. Retroactively gate existing code as modules are onboarded through recovery. Do not require full coverage on day one.

Use `/brownfield-onboarding` in Cursor. See `reference/brownfield-onboarding.md` for the full protocol.

---

## Phase 0: Idea Intake

**Purpose**

Capture the raw project idea, its business context, constraints, and initial scope. Translate a vague request into a structured document that can be decomposed.

**Inputs**

- Feature request, business requirement, or problem statement
- Stakeholder conversations and domain context
- Existing system documentation (if applicable)

**Outputs**

- Completed project intake document (use `templates/project-intake-template.md`)
- Initial scope boundary and success criteria
- Known constraints and non-functional requirements
- List of open questions requiring resolution

**Exit Criteria**

- [ ] The intake document has been reviewed and accepted by a human stakeholder.
- [ ] The problem is understood well enough to begin architectural decomposition.
- [ ] Ambiguities are either resolved or explicitly documented as open questions.
- [ ] Non-functional requirements (performance, security, availability) are stated.

**Human Responsibilities**

- Conduct stakeholder interviews and define business context.
- Write the intake document. This is human work; it requires judgment about what matters.
- Define success criteria and constraints.
- Identify and document open questions.

**Agent Responsibilities**

- Research the domain: prior art, related systems, terminology, current market solutions, ecosystem health.
- Produce structured research artifacts: technology landscape summaries, comparison matrices, risk assessments.
- Help structure the intake document from raw notes or conversations.
- Surface missing information, contradictions, or unstated assumptions.
- Agents do not make scope decisions or define success criteria. They investigate; humans decide.

**Cursor Integration**

- Invoke `/project-intake` to use the project intake skill.

---

## Phase 1: Architecture and Decomposition

**Purpose**

Break the system into bounded contexts with clean interfaces. Define the module boundaries that will enable parallel agent execution in later phases.

**Inputs**

- Completed intake document from Phase 0
- Domain knowledge and existing system constraints
- Non-functional requirements

**Outputs**

- Architecture decision records (use `templates/architecture-decision-record.md`)
- Module boundary documents (use `templates/module-boundary-template.md`)
- Interface contracts between modules (use `templates/interface-contract-template.md`)
- Dependency graph showing module relationships
- Design identity document for projects with user-facing surfaces (use `templates/design-identity-template.md`)

**Exit Criteria**

- [ ] All bounded contexts are identified and named.
- [ ] Every interface between contexts has a contract document.
- [ ] No circular dependencies exist between modules.
- [ ] Each module is small enough to be independently specifiable and testable.
- [ ] Architecture decisions are recorded with rationale and trade-offs.
- [ ] For projects with user-facing surfaces, the design identity document is complete with aesthetic direction, anti-patterns, and reference targets.

**Human Responsibilities**

- Make architectural decisions. This requires taste, experience, and judgment.
- Define bounded context boundaries based on domain analysis.
- Design interface contracts between modules.
- Evaluate trade-offs and document the reasoning.
- For user-facing projects, author the design identity document: aesthetic direction, typography, color system, spatial system, motion philosophy, copy voice, naming conventions, banned patterns.

**Agent Responsibilities**

- Research technologies, patterns, and existing implementations relevant to the architectural decisions.
- Map the existing codebase to identify current module structure.
- Suggest decomposition options based on the intake document and research findings.
- Draft architecture decision records from human decisions, citing research artifacts.
- Validate that proposed boundaries do not create circular dependencies.
- Draft interface contract templates from human-defined boundaries.

**Cursor Integration**

- Invoke `/architecture` to use the architecture skill.
- Use the `spec-reviewer` subagent to validate architecture documents for completeness.

---

## Phase 2: Specification Writing

**Purpose**

Write precise, testable specifications for each bounded context. The specification is the primary engineering artifact. It defines exactly what the system must do.

**Inputs**

- Architecture documents and module boundaries from Phase 1
- Interface contracts between modules
- Domain knowledge and edge case analysis

**Outputs**

- Specification documents for each bounded context (use `templates/spec-template.md`)
- Updated interface contracts if spec writing reveals new integration points
- Edge case catalog for each module
- For user-facing modules, design tokens derived from the design identity document as SDK building blocks

**Exit Criteria**

- [ ] Every behavior is specified precisely enough to derive a test.
- [ ] Every edge case is documented with expected behavior.
- [ ] Failure modes are specified (what happens when things go wrong).
- [ ] Specifications are peer-reviewed by at least one other human.
- [ ] No unresolved ambiguities remain in the specification.
- [ ] Interface contracts are consistent across all modules that share a boundary.

**Human Responsibilities**

- Write specifications. This is the hardest intellectual work in the pipeline.
- Define edge cases and failure modes from domain knowledge.
- Peer-review specifications for completeness, precision, and testability.
- Resolve ambiguities. If something is unclear, clarify it before it becomes a test.

**Agent Responsibilities**

- Draft initial specification sections from the architecture documents.
- Identify potential edge cases by analyzing data models and interface contracts.
- Cross-reference specifications against interface contracts for consistency.
- Flag vague language or untestable assertions in the specification.
- Agents do not decide what the system should do. They help express what humans have decided.

**Cursor Integration**

- Invoke `/spec-writing` to use the specification writing skill.
- Use the `spec-reviewer` subagent to review completed specifications.

---

## Phase 3: SDK Design

**Purpose**

Translate architectural boundaries and specifications into a compilable constraint surface: the types, interfaces, extension points, and compositional primitives that all downstream work (tests and implementation) must use. The SDK makes modularity enforceable at the code level, forces abstraction, and constrains agents to operate within predefined building blocks.

**Inputs**

- Specification documents from Phase 2
- Interface contracts from Phase 1
- Architecture decision records from Phase 1
- Domain models and bounded context definitions

**Outputs**

- SDK package(s) defining types, interfaces, and contracts for each bounded context
- Shared primitives (error types, result patterns, event contracts, extension points)
- SDK documentation (auto-generated or hand-written) describing each building block
- Compilation proof (the SDK compiles with no implementation behind it)

**Exit Criteria**

- [ ] Every bounded context has a corresponding SDK module with typed interfaces.
- [ ] Shared types (errors, events, identifiers) are defined once in the SDK, not duplicated.
- [ ] The SDK compiles successfully with no implementation code.
- [ ] Extension points are explicit (where and how new building blocks may be added).
- [ ] Interface contracts from Phase 1 are expressed as compilable SDK types.
- [ ] The SDK enforces module boundaries (no cross-context internal access is possible through the public surface).
- [ ] SDK documentation matches the specification intent.

**Human Responsibilities**

- Make abstraction decisions. What are the building blocks? What compositional patterns should agents use?
- Define the extension model. How does the SDK grow as new capabilities are needed?
- Review the SDK for coherence across bounded contexts.
- Ensure the SDK does not over-constrain (leaving no freedom for implementation) or under-constrain (allowing agents to invent incompatible patterns).

**Agent Responsibilities**

- Draft SDK interfaces from specification documents and interface contracts.
- Generate type definitions, trait/interface declarations, and contract signatures.
- Verify that the SDK compiles and that no implementation leaks into the constraint surface.
- Cross-reference SDK modules against bounded context boundaries for completeness.
- Flag specifications that cannot be cleanly expressed as SDK building blocks (signal for spec revision).

**Cursor Integration**

- Invoke `/sdk-design` to use the SDK design skill.
- Use the `spec-reviewer` subagent to validate SDK interfaces against specifications.

---

## Phase 4: Test Molding

**Purpose**

Derive comprehensive test cases from specifications. Build the mold that implementation must fill. Tests are written against SDK interfaces, compile, but fail because no implementation exists yet.

**Inputs**

- Specification documents from Phase 2
- SDK interfaces and types from Phase 3
- Interface contracts from Phase 1
- Test plan template (use `templates/test-plan-template.md`)

**Outputs**

- Test plan document for each module
- Executable test code (unit tests, integration tests, contract tests)
- All tests compile and all tests fail (red state)

**Exit Criteria**

- [ ] Every behavior in the specification has at least one test.
- [ ] Every edge case in the specification has a corresponding test.
- [ ] Contract tests exist for every interface between modules.
- [ ] All tests are written against SDK interfaces (no out-of-band abstractions).
- [ ] All tests compile successfully.
- [ ] All tests fail (no implementation exists to pass them).
- [ ] Test names clearly trace back to specification sections.

**Human Responsibilities**

- Review test plans for completeness against the specification.
- Validate that tests are sharp enough to constrain implementation.
- Ensure tests do not over-specify implementation details (test behavior, not internals).
- Approve the test plan before code casting begins.

**Agent Responsibilities**

- Derive test cases systematically from each specification section.
- Write executable test code following the test plan.
- Generate contract tests from interface contract documents.
- Verify that all tests compile and all tests fail.
- Flag specification sections that lack testable assertions.

**Cursor Integration**

- Invoke `/test-molding` to use the test molding skill.
- Use the `test-deriver` subagent to derive tests from a specification.

---

## Phase 5: Code Casting

**Purpose**

Implement code that passes all tests. This is the phase where agents work in parallel across bounded contexts. The mold exists; now pour the casting. Agents implement SDK interfaces and must stay within the constraint surface.

**Inputs**

- Specification documents from Phase 2
- SDK interfaces and types from Phase 3
- Test suite in red state (compiles successfully, all tests failing) from Phase 4
- Interface contracts from Phase 1
- Agent task definitions (use `templates/agent-task-template.md`)

**Outputs**

- Implementation code for each module
- All tests passing (green state)
- Atomic commits traceable to specification sections

**Exit Criteria**

- [ ] All unit tests pass.
- [ ] All integration tests pass.
- [ ] All contract tests pass.
- [ ] Code implements SDK interfaces (no abstractions invented outside the constraint surface).
- [ ] Code respects module boundaries (no cross-boundary imports outside contracts).
- [ ] No interface contracts or SDK interfaces have been modified without explicit approval.
- [ ] Each commit maps to a specification section.

**Human Responsibilities**

- Create agent task definitions that scope the work precisely.
- Remain available for clarification if agents encounter ambiguity.
- Do not write implementation code unless the task is too complex for agents.
- Monitor agent progress and intervene if agents are stuck or diverging.

**Agent Responsibilities**

- Read the specification, SDK interfaces, tests, and interface contracts.
- For user-facing modules, read the design identity document and reference design tokens from the SDK.
- Write implementation code that implements SDK interfaces until all assigned tests pass.
- Stay within the boundaries of the assigned module and the SDK constraint surface.
- For user-facing code, all visual values must reference design tokens. Do not use hardcoded hex, px, rem, or font-family values. Do not use known AI-default patterns when the design identity specifies alternatives.
- Do not introduce abstractions outside the SDK. If new building blocks are needed, stop and request SDK extension.
- Make small, atomic commits. Each commit addresses one logical unit of work.
- If the specification is ambiguous, stop and ask. Do not guess.
- If a test appears incorrect, surface it. Do not modify tests without approval.

**Enforcement Scripts**

- Run `scripts/divergence-gate.sh` (or `.ps1`) to scan for slop fingerprints before submitting for review. Use `--config divergence.json` if the project has a custom fingerprint catalog derived from the design identity.
- Run `scripts/spec-check.sh` (or `.ps1`) to verify every source module has a corresponding specification.
- Use `scripts/commit-lint.sh` (or `.ps1`) as a git commit-msg hook or CI check to enforce spec-traceable commits (R7).

**Cursor Integration**

- Invoke `/code-casting` to use the code casting skill.
- Use the `code-caster` subagent for bounded implementation tasks.
- Multiple `code-caster` subagents can run in parallel across different modules.

### Assembly Pressure Checkpoint

After each bounded context is cast and its molds pass, assemble the running system and apply realistic pressure before proceeding to formal review. This is not Phase 6b Product Testing (which runs the full suite before deployment). It is an incremental validation that the newly cast block integrates with the existing assembly under realistic conditions.

**Checkpoint sequence:**

1. Assemble the running system with the newly cast block included.
2. Run critical-path smoke tests against the assembled system.
3. If the project has product test objectives defined, run the subset that touches the newly cast context.
4. Apply realistic data volumes, concurrency, and failure injection where applicable.
5. Route any discovered integration failures back as gap assessments: specification gaps (the spec did not account for this interaction), SDK gaps (the constraint surface lacks types for cross-context behavior), or mold gaps (no test covers the assembly-level behavior).

**When to skip:** If the cast block is purely internal (no user-facing surface, no integration surface) and has no cross-context dependencies, the checkpoint may be deferred to the next block that does integrate. Document the deferral in the context state file.

**At all profiles:** Essential profile runs smoke tests only. Standard runs smoke tests plus critical journey checks. Complete runs smoke tests, journey checks, and load profiles.

---

## Phase 6: Review

**Purpose**

Verify that castings match the mold and that the mold matches the original intent. This is the second human bottleneck after specification writing.

**Inputs**

- Implementation code from Phase 5
- Specification documents from Phase 2
- SDK interfaces from Phase 3
- Test results from Phase 5
- Interface contracts from Phase 1
- Human review template (use `templates/human-review-template.md`)

**Outputs**

- Completed review document
- Approved or rejected status for each module
- List of required changes (if rejected)

**Exit Criteria**

- [ ] Every module has been reviewed by at least one human.
- [ ] Implementation matches the specification (no extra behavior, no missing behavior).
- [ ] Interface contracts are honored (no silent changes).
- [ ] Code quality meets project standards.
- [ ] All automated quality gates pass (lint, tests, coverage, divergence checks).
- [ ] For user-facing modules, divergence gate confirms no slop fingerprints from the design identity's banned patterns list.
- [ ] Review document is completed and stored.

**Human Responsibilities**

- Review each module for correctness against the specification.
- Verify that the system still makes sense as a whole (coherence check).
- Check for interface contract violations.
- For user-facing modules, verify design identity compliance: do visual values trace to tokens? Are banned patterns absent? Does the casting match the aesthetic direction?
- Approve or reject with specific, actionable feedback.
- This is judgment work. Agents assist but do not replace human review.

**Agent Responsibilities**

- Run automated checks: lint, test suite, coverage reports.
- Run `scripts/divergence-gate.sh` (or `.ps1`) and include results in the review summary.
- Run `scripts/spec-check.sh` (or `.ps1`) to verify spec coverage.
- Generate a diff summary comparing implementation against the specification.
- Flag potential deviations from the specification.
- Flag interface contract violations.
- Agents do not approve or reject. That is a human decision.

**Cursor Integration**

- Invoke `/review` to use the review skill.
- Use the `spec-reviewer` subagent to generate automated review summaries.

---

## Phase 6b: Product Testing

**Purpose**

Verify the assembled product by deploying AI agents that operate the application as real users would. Product testing catches experience defects that module-level tests cannot: unusable workflows, excessive friction, confusing navigation, poor error guidance, and accessibility failures.

This phase runs after review confirms the code is correct and before deployment ships it to users. It answers the question: the code works, but does the product work for the people who use it?

For the full product testing reference, see the [Product Testing](https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/product-testing.md) document in the Codex Automata repository.

**Inputs**

- Approved code from Phase 6 (assembled, running in a staging or preview environment)
- User profile documents (use `templates/user-profile-template.md`)
- Product test scenarios (use `templates/product-test-template.md`)
- UX budgets from the specification (click budgets, navigation depth limits, time budgets)

**Outputs**

- Product test results with journey logs for each scenario
- UX metrics: click counts, backtracking rates, navigation depth, error encounters, time to completion
- Experience signals: hesitation points, dead ends, discovery paths, confusion indicators
- Defect reports for failed objectives or budget violations

**Exit Criteria**

- [ ] All critical journey objectives pass (agent completes the objective).
- [ ] All UX budgets are met (click count, navigation depth, time within thresholds).
- [ ] No critical errors (crashes, data loss, security failures) during any journey.
- [ ] Accessibility-constrained profiles complete all required objectives.
- [ ] Journey logs are stored for trend analysis.

**Human Responsibilities**

- Define user profiles that represent the actual user base.
- Set UX budgets grounded in product standards and competitive benchmarks.
- Interpret experience signals and decide whether friction patterns warrant specification changes.
- Product testing reveals experience defects, but humans decide which defects matter enough to fix before shipping.

**Agent Responsibilities**

- Operate the application through its user interface using browser tools, screen readers, or mobile emulators as the profile dictates.
- Follow the user profile's behavioral model (technical literacy, domain knowledge, behavioral tendencies).
- Do not use implementation knowledge. Navigate using only what is visible on screen and what the profile's user would reasonably know.
- Record every action, observation, hesitation, error, and recovery in a journey log.
- Report honestly when an objective cannot be completed, including where the agent got stuck and what it tried.

**Cursor Integration**

- Invoke `/product-testing` to use the product testing skill.
- Use the `product-tester` subagent to execute product test scenarios.

---

## Phase 7: Deployment and Observation

**Purpose**

Ship verified code to production and confirm that production behavior matches the specification. Close the feedback loop.

**Inputs**

- Approved code from Phase 6b
- Deployment configuration and infrastructure
- Monitoring and alerting requirements from the specification

**Outputs**

- Production deployment
- Monitoring dashboards and alerts configured
- Incident runbook (if applicable)
- Post-deployment verification report

**Exit Criteria**

- [ ] Deployment completes successfully.
- [ ] Smoke tests pass in production.
- [ ] Monitoring confirms behavior matches the specification.
- [ ] Alerting is configured for failure modes defined in the specification.
- [ ] Rollback procedure is documented and tested.

**Human Responsibilities**

- Approve the deployment.
- Monitor production behavior during the initial observation period.
- Respond to incidents and decide whether to roll back.
- Update specifications if production reveals gaps.

**Agent Responsibilities**

- Execute deployment scripts and pipelines.
- Configure monitoring and alerting from specification requirements.
- Run post-deployment verification (smoke tests, health checks).
- Report anomalies and deviations from expected behavior.
- Agents do not decide to roll back. That is a human decision.

---

## Iteration and Feedback

The pipeline is not strictly linear. Review can send work back to any earlier phase:

- **Back to Phase 2** if the specification is incomplete or incorrect.
- **Back to Phase 3** if the SDK constraint surface needs new building blocks or revision.
- **Back to Phase 4** if tests are insufficient or over-specified.
- **Back to Phase 5** if the spec, SDK, and tests are correct but the implementation diverges.

The key constraint is that backward movement always starts at the specification. If code is wrong, do not debug the implementation. Fix the spec, extend the SDK if needed, fix the tests, recast.

---

## Context Persistence

Agents start each session without memory of prior work. Context rot — the progressive loss of decisions, progress, and trade-offs across sessions — is mitigated by a structured context state file maintained as part of normal project operations.

Each project maintains a `context-state.md` file (initialized from `templates/context-state-template.md`) as the navigation layer for agent sessions. It answers "where are we?" so agents can find and prioritize the right artifacts quickly without re-reading the entire project.

For the full context persistence methodology, health checks, and update protocol, see the [Context Persistence](https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/context-persistence.md) document in the Codex Automata repository.

### Agent Responsibilities

- Read `context-state.md` at session start before other project artifacts.
- Update `context-state.md` at session end and after significant milestones (phase transitions, bounded context completion, gap filing, recovery closure).
- Keep the Checkpoint section current: Resume from, Prerequisites met, and Next action must reflect the exact handoff point for the next session.
- Append Session History entries; move completed work to Recently Completed; update Current Work in place.

### Human Responsibilities

- Review `context-state.md` periodically for drift (staleness, phase mismatch, stale Open Decisions).
- Resolve Open Decisions that have been open for more than two sessions.
- Verify Active Phase accuracy during phase reviews and kanban walkthroughs.
- Create `context-state.md` from the template when starting a new project if agents have not yet done so.

### Quality Gate

Context state must be updated before a phase transition is considered complete. An agent or human moving work to the next phase without an updated context state file has not finished the current phase's operational closure.

---

## Recovery: Closing Gaps After the Fact

The forward pipeline assumes specs and tests exist before code. When you discover they do not, recovery applies the same pipeline retroactively. Recovery is not an exception or a side project. It is first-class work that flows through the same kanban stations as forward work.

For the full recovery protocol, classification taxonomy, triage guidance, and metrics, see the [Recovery Protocol](https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/recovery.md) in the Codex Automata repository.

### When Recovery Applies

Recovery applies whenever you discover that code exists without the upstream artifacts the methodology requires:

- A module has no specification, or the specification is incomplete.
- A specification has no tests, or tests are too weak to constrain the implementation.
- Tests were deleted, disabled, or made flaky without remediation.
- A module boundary has no contract tests despite a defined interface contract.

These gaps are discovered through production incidents, review findings, coverage audits, team walkthroughs, dependency upgrades, security scans, or agent-detected gaps during routine tasks.

### Recovery Sequence

Recovery mirrors the forward pipeline but starts from an existing codebase.

```text
Audit --> Spec Patch --> SDK Patch --> Mold Patch --> Recast (if needed) --> Re-review
```

**Step 1: Audit.** Document the gap using `templates/gap-assessment-template.md`. Identify the affected module, gap class, discovery trigger, severity, and current state. This is a human task; agents assist with evidence gathering.

**Step 2: Spec Patch.** If the specification is missing or incomplete, write the missing sections following Phase 2 rules. Derive the specification from domain knowledge and stakeholder intent, not from the existing code. The code may be accidentally correct or silently wrong.

**Step 3: SDK Patch.** If the SDK constraint surface is missing types or interfaces for the affected behavior, extend it following Phase 3 rules. SDK extensions derive from the patched specification, not from the existing implementation.

**Step 4: Mold Patch.** Derive tests from the patched specification and SDK following Phase 4 rules. Tests must trace back to specification sections and use SDK interfaces. For coverage erosion, compare against the original test intent via version control history before restoring.

**Step 5: Recast (if needed).** If the existing implementation passes the new tests, no recast is needed. If it fails, recast following Phase 5 rules. Agents receive the specification, SDK, updated tests, and interface contracts.

**Step 6: Re-review.** A human reviews the recovery as a unit: spec patch, SDK patch, mold patch, and any recast code. The review confirms spec accuracy, SDK coherence, test traceability, implementation correctness, and that no new gaps were introduced.

### Recovery Exit Criteria

- [ ] The gap assessment document is complete.
- [ ] The specification is updated and covers the previously missing behavior.
- [ ] Tests exist for every specified behavior and trace to specification sections.
- [ ] All tests pass.
- [ ] A human has reviewed and approved the recovery unit.
- [ ] The recurrence prevention section of the gap assessment is filled in.

### Human Responsibilities During Recovery

- Triage discovered gaps by severity and schedule them on the board.
- Write or approve specification patches. Specification authority remains human-owned.
- Review the complete recovery unit before closing the card.
- Fill in the recurrence prevention section: what process gap allowed this debt to accumulate?

### Agent Responsibilities During Recovery

- When a gap is discovered during routine work, halt and report it using the gap assessment template. Do not silently work around gaps.
- During recovery tasks, follow the same forward rules (R1-R14) in the context of an existing codebase.
- Assist with evidence gathering: scan for related gaps, check version control history, surface specification sections that reference the affected behavior.
- Derive tests from the specification, not from the existing code.
- If the specification appears incorrect (code behavior contradicts it and the code is believed correct), surface the conflict for human resolution. Do not update the specification unilaterally.

**Cursor Integration**

- Invoke `/recovery` to use the recovery skill.
- The recovery skill walks through all six steps with template references.

### Recovery on the Kanban Board

Recovery cards use a distinct card type or tag ("Recovery" or "Gap Remediation") and flow through the same stations as forward work. They count against the same WIP limits. If a critical recovery card displaces forward work, that tradeoff is visible on the board.

Batch related gaps within a single module into one recovery card. Create separate cards for separate modules to maintain bounded context independence.

---

## Quick Reference

| Phase | Primary Owner | Bottleneck? | Key Template |
|-------|--------------|-------------|--------------|
| 0: Intake | Human | No | `project-intake-template.md` |
| 1: Architecture | Human | No | `architecture-decision-record.md` |
| 2: Specification | Human | **Yes** | `spec-template.md` |
| 3: SDK Design | Human + Agent | No | `interface-contract-template.md` |
| 4: Test Molding | Agent (human review) | No | `test-plan-template.md` |
| 5: Code Casting | Agent | No | `agent-task-template.md` |
| 6: Review | Human | **Yes** | `human-review-template.md` |
| 6b: Product Testing | Agent (human review) | No | `product-test-template.md` |
| 7: Deployment | Human + Agent | No | N/A |
| Recovery | Human + Agent | No | `gap-assessment-template.md` |
