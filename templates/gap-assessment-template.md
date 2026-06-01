# Gap Assessment: [Module Name]

<!--
[Use this template when a gap is discovered in specification, tests, or coverage for an existing module. Fill in each section to document the gap, plan recovery, and prevent recurrence. For the full recovery protocol, see https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/recovery.md]
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | [ ] |
| Assessed by | [ ] |
| Date discovered | [YYYY-MM-DD] |
| Severity | Critical / Significant / Moderate / Low [pick one] |
| Status | Open / In Recovery / Closed [pick one] |

## Gap Classification

[Pick one. Definitions: spec gap = behavior in code but not in spec; mold gap = behavior in spec but no tests; coverage erosion = tests lost over time; contract gap = boundary lacks contract tests.]

- [ ] **Spec gap:** behavior exists in code but is not documented in any specification.
- [ ] **Mold gap:** behavior is documented in the specification but has no tests, or tests are too weak.
- [ ] **Coverage erosion:** tests existed but were deleted, disabled, or made flaky without remediation.
- [ ] **Contract gap:** a module boundary has no contract tests despite a defined interface contract.
- [ ] **SDK gap:** behavior exists in code but has no corresponding types or interfaces in the SDK constraint surface.

## Discovery Trigger

[How was this gap found? Pick one or describe.]

- [ ] Production incident
- [ ] Review finding
- [ ] Coverage audit
- [ ] Team walkthrough
- [ ] Dependency upgrade
- [ ] Security scan
- [ ] Agent-detected during routine task
- [ ] Other: [ ]

[If incident-related, link the incident report or postmortem.]

## Current State

[What exists today? Describe the specification, tests, and code as they currently stand.]

- **Specification:** [complete / partial / missing; cite relevant spec document and sections if they exist]
- **Tests:** [present / partial / missing / disabled; cite test files if they exist]
- **Code:** [describe the behavior that exists without adequate upstream artifacts]
- **Contract tests:** [present / missing; cite the interface contract document]

## Required State

[What should exist according to the methodology? Be specific.]

- **Specification should cover:** [list the behaviors, edge cases, and failure modes that need to be specified]
- **Tests should cover:** [list the test cases that need to exist, traced to specification sections]
- **Implementation changes (if any):** [describe expected recast scope, or note "none expected" if the code is believed correct]

## Recovery Plan

[Specific tasks to close this gap. Each task should map to a recovery sequence step.]

1. **Spec patch:** [ ]
2. **SDK patch:** [ ]
3. **Mold patch:** [ ]
4. **Recast (if needed):** [ ]
5. **Re-review:** [ ]

**Estimated effort:** [ ]

**Assigned to:** [ ]

## Recurrence Prevention

[What process gap allowed this debt to accumulate? What change prevents this class of gap from recurring?]

- **Root cause:** [ ]
- **Process change:** [ ]

<!--
Common root causes and remediation:
- Review checklist did not require coverage verification --> add the check to the review and PR templates.
- Contract tests were not required at the boundary --> update architecture and module boundary templates.
- Spec was reviewed by someone unfamiliar with the domain --> establish domain-owner review requirements.
- Tests were disabled to unblock a deadline --> require tracking issues with due dates for disabled tests.
- Module predates the methodology --> schedule systematic audit of pre-methodology modules.
- Emergency bypass of the forward pipeline --> ensure bypass policy includes mandatory recovery scheduling.
-->

## Resolution

[Fill in when the gap is closed.]

| Field | Value |
|-------|-------|
| Date closed | [YYYY-MM-DD] |
| Reviewed by | [ ] |
| Spec patch commit/PR | [ ] |
| SDK patch commit/PR | [ ] |
| Mold patch commit/PR | [ ] |
| Recast commit/PR | [N/A or link] |
| Review approval | [ ] |
