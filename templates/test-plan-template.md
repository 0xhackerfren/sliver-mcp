# Test Plan: [Module Name]

<!--
[Link this plan to the specification version. Tests are the mold; every behavior should map to at least one test. Contract tests lock interface contracts.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | [same as spec] |
| Specification reference | [path or ID, with version] |
| Version | [test plan version] |
| Date | [YYYY-MM-DD] |
| Author | [name or role] |

## Specification Coverage Matrix

| Spec behavior (ID or section) | Test case ID | Test type (unit / integration / contract) | Notes |
|-------------------------------|--------------|---------------------------------------------|-------|
| [e.g., §3.1] | [TC-001] | [unit] | [ ] |
| [ ] | [ ] | [ ] | [ ] |

[Every numbered behavior in the specification should appear in at least one row.]

## Unit Tests

| Test name | Spec reference | Input | Expected output | Notes |
|-----------|----------------|-------|-----------------|-------|
| [test_function_scenario] | [§x.y] | [fixtures, parameters] | [assertions, state] | [edge focus, mocks] |

## Integration Tests

| Test name | Modules in flow | Spec reference | Scenario | Expected outcome | Notes |
|-----------|-----------------|----------------|----------|------------------|-------|
| [test_end_to_end_slice] | [A, B] | [§] | [steps] | [observable result] | [environment] |

## Contract Tests

| Test name | Interface contract | Spec reference | Checks | Notes |
|-----------|-------------------|----------------|--------|-------|
| [test_provider_shape] | [Contract ID] | [§] | [schema, errors, idempotency] | [consumer vs provider] |

## Edge Case Tests

| Test name | Spec edge case | Input / setup | Expected behavior |
|-----------|----------------|---------------|-------------------|
| [ ] | [§ Edge Cases #n] | [ ] | [ ] |

## Performance Tests

[Include only if the specification defines non-functional targets.]

| Test name | Requirement | Method | Pass threshold | Notes |
|-----------|-------------|--------|----------------|-------|
| [ ] | [latency / throughput] | [load tool, benchmark] | [ ] | [ ] |

## Product Tests

[Include when the specification defines user-facing behaviors. Product tests verify the assembled application by having agents operate it as real users. See `templates/product-test-template.md` and `templates/user-profile-template.md` for full templates.]

| Objective | User profile | Spec reference | UX budget (clicks) | Priority |
|-----------|-------------|----------------|---------------------|----------|
| [goal-oriented statement] | [profile name] | [section] | [max clicks] | [critical / high / medium / low] |
| [ ] | [ ] | [ ] | [ ] | [ ] |

## Property-Based Tests

[Derive properties from specification invariants. Each property must hold for any valid input. Properties are written before implementation (red state). Use fast-check (TypeScript), Hypothesis (Python), or the appropriate PBT framework for your language.]

| Property | Spec Reference | Generator Strategy | Expected Invariant | Priority |
|----------|---------------|-------------------|-------------------|----------|
| _[e.g., "Valid title always creates task"]_ | _[spec section]_ | _[e.g., "Arbitrary string, length 1-200"]_ | _[e.g., "createTask succeeds and returned task has matching title"]_ | _[Must / Should / Could]_ |

## Accessibility Tests

[For user-facing modules. Define accessibility checks that run as quality gates. Use automated tools (axe-core, pa11y, Lighthouse) for mechanical verification and product test profiles for experiential verification.]

### Automated Accessibility Checks

| Check | WCAG Criterion | Tool | Scope | Priority |
|-------|---------------|------|-------|----------|
| _[e.g., "Color contrast"]_ | _[e.g., "1.4.3 Contrast (Minimum)"]_ | _[e.g., "axe-core"]_ | _[e.g., "All text elements"]_ | _[Must / Should]_ |
| _[e.g., "Keyboard operability"]_ | _[e.g., "2.1.1 Keyboard"]_ | _[e.g., "Manual + pa11y"]_ | _[e.g., "All interactive elements"]_ | _[Must]_ |
| _[e.g., "Alt text present"]_ | _[e.g., "1.1.1 Non-text Content"]_ | _[e.g., "axe-core"]_ | _[e.g., "All images"]_ | _[Must]_ |

### Accessibility Product Test Profiles

| Profile | Constraints | Key Objectives |
|---------|-----------|----------------|
| _[e.g., "Screen reader user"]_ | _[e.g., "VoiceOver, no visual"]_ | _[e.g., "Complete purchase, navigate settings"]_ |
| _[e.g., "Keyboard-only user"]_ | _[e.g., "No mouse, Tab/Enter only"]_ | _[e.g., "All critical journeys"]_ |

## Test Environment Requirements

- **Dependencies:** [services, databases, queues]
- **Fixtures:** [data sets, seeds]
- **Mock services:** [which boundaries are stubbed]
- **Secrets / config:** [how provided in CI and local]

## Exit Criteria

- [ ] All listed tests **compile** (or equivalent for the stack).
- [ ] All new tests **fail** against the current casting until implementation exists (red phase of the flow).
- [ ] Coverage targets: [statement / branch / critical paths; or explicit rationale if not numeric]
- [ ] Contract tests run in quality gate: [where, e.g., CI job name]
- [ ] Human review can verify traceability from spec to mold via the coverage matrix
