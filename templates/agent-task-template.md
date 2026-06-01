# Agent Task: [Task ID] - [Task Title]

<!--
[One agent task equals one bounded slice of work. Inputs are specifications, molds, and frozen interface contracts; outputs must satisfy acceptance criteria and pass human review at the quality gate.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Task ID | [e.g., TASK-42] |
| Assigned agent or agent type | [name or role, e.g., implementation agent] |
| Date | [YYYY-MM-DD] |
| Status | Open / In Progress / Complete / Blocked [pick one] |

## Specification Reference

[Exact specification sections or behavior IDs this task implements, with document path and version.]

## Scope

**In scope:**

- [ concrete deliverable tied to spec ]

**Boundaries:**

- [ what file areas or modules may change ]

## Inputs

- **Specification sections:** [ ]
- **Test files / mold:** [paths]
- **Interface contracts:** [frozen IDs]
- **Existing code:** [entry points, patterns to match]

## Expected Outputs

- **Source:** [files or modules]
- **Tests:** [new or updated; must align with mold]
- **Commits:** [granularity expectation, optional]
- **Documentation:** [only if spec requires deltas to specs or contracts]

## Acceptance Criteria

- [ ] Test case **[ID]** passes [link or name]
- [ ] Test case **[ID]** passes
- [ ] Interface contract **[ID]** unchanged or version bump per strategy
- [ ] No quality gate regressions [define which]

## Constraints

- **Module boundaries:** [must not leak into bounded context X]
- **Interface contracts:** [frozen fields, error codes]
- **Dependencies:** [allowed libraries only]

## Out of Scope

- [ refactoring not tied to acceptance criteria ]
- [ feature Y ]
- [ editing templates under `templates/` ]

## Notes

[Runtime flags, secrets location, flaky-test history, design sketches, links to related human review findings.]
