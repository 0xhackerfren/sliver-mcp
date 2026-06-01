# Brownfield Audit: [Project Name]

<!--
[Use this template before adopting Codex Automata on an existing codebase. The audit inventories modules, classifies risks, and produces a prioritized onboarding plan. For the full brownfield onboarding guide, see reference/brownfield-onboarding.md.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Project name | [ ] |
| Audited by | [ ] |
| Date | [YYYY-MM-DD] |
| Codebase age | _[approximate]_ |
| Estimated module count | [ ] |
| Current test coverage | _[percentage or unknown]_ |
| Current CI/CD | _[describe existing pipeline]_ |

## Module Inventory

[List every significant module, service, or bounded context in the existing codebase.]

| Module | Bounded Context | Risk Level | Change Frequency | Test Coverage | Spec Exists | SDK Exists | Priority |
|--------|----------------|------------|-----------------|---------------|-------------|------------|----------|
| _[name]_ | _[context]_ | _[Critical/High/Medium/Low]_ | _[Daily/Weekly/Monthly/Rare]_ | _[%/None/Unknown]_ | _[Yes/Partial/No]_ | _[Yes/No]_ | _[1-N]_ |

### Risk Level Criteria

- **Critical:** Production-facing, revenue-impacting, handles sensitive data, or has caused incidents
- **High:** Production-facing, frequently changed, or has complex business logic
- **Medium:** Internal tooling, moderately changed, or straightforward logic
- **Low:** Rarely changed, well-understood, or scheduled for replacement

### Priority Ranking Logic

Priority = Risk Level x Change Frequency. Critical modules that change frequently are onboarded first. Low-risk, rarely-changed modules are onboarded last (or not at all if scheduled for replacement).

## Dependency Map

[Which modules depend on which? This determines onboarding order -- onboard dependencies before dependents where practical.]

| Module | Depends On | Depended On By |
|--------|-----------|---------------|
| _[name]_ | _[modules]_ | _[modules]_ |

## Gap Summary

[Aggregate gap count across the codebase based on module inventory.]

| Gap Type | Count | Notes |
|----------|-------|-------|
| Spec gaps (code without spec) | [ ] | _[most common in brownfield]_ |
| Mold gaps (spec without tests) | [ ] | |
| SDK gaps (code without SDK types) | [ ] | |
| Contract gaps (boundaries without contract tests) | [ ] | |
| Coverage erosion (tests lost over time) | [ ] | |

## Existing Assets to Preserve

[What existing artifacts align with the methodology and should be kept?]

- **Existing tests worth keeping:** _[list test suites that test specified behavior, not just code coverage]_
- **Existing documentation:** _[API docs, architecture docs, READMEs that can inform specifications]_
- **Existing CI/CD gates:** _[linters, test runners, coverage checks to integrate with]_

## Onboarding Plan

### Phase 1: First Module (Week 1-2)

**Target module:** _[highest priority from inventory]_
**Profile:** Essential
**Steps:**
1. [ ] Write specification from domain knowledge (not code)
2. [ ] Derive tests from specification
3. [ ] Verify existing implementation against new tests
4. [ ] File gap assessments for any failures
5. [ ] Recast if needed

### Phase 2: Adjacent Modules (Week 3-6)

**Target modules:** _[next 2-4 highest priority]_
**Profile upgrade:** _[Essential or Standard]_
**Steps:**
1. [ ] Repeat recovery process for each module
2. [ ] Extract SDK types for shared interfaces
3. [ ] Define interface contracts between onboarded modules
4. [ ] Establish quality gates for new PRs

### Phase 3: Expansion (Month 2+)

**Target:** _[remaining high/medium priority modules]_
**Profile upgrade:** Standard
**Steps:**
1. [ ] Continue recovery-based onboarding
2. [ ] Implement context persistence
3. [ ] Activate full quality gate pipeline

## CI/CD Integration Plan

| Gate | When to Activate | Scope |
|------|-----------------|-------|
| _[e.g., "Spec required for new modules"]_ | _[e.g., "Immediately"]_ | _[e.g., "New PRs only"]_ |
| _[e.g., "Test coverage threshold"]_ | _[e.g., "After Phase 1"]_ | _[e.g., "Onboarded modules"]_ |
