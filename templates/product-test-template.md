# Product Test: [Scenario Name]

<!--
[Define a product test scenario where an AI agent operates the application as a real user. The agent receives a user profile and an objective, then navigates the product to accomplish the goal. For the full product testing reference, see https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/product-testing.md]
-->

## Metadata

| Field | Value |
|-------|-------|
| Scenario name | [ ] |
| Version | [ ] |
| Date | [YYYY-MM-DD] |
| Author | [name or role] |
| Priority | Critical / High / Medium / Low [pick one] |

## User Profile

[Reference the user profile document this test uses.]

- **Profile:** [name, e.g., "First-time visitor" or path to user profile document]
- **Technical literacy:** [high / moderate / low]
- **Domain knowledge:** [expert / familiar / novice]
- **Constraints:** [e.g., mobile-only, screen reader, slow network, non-native language, none]

## Objective

[State what the agent must accomplish as a goal, not a script. Write from the user's perspective.]

**Goal:** [ ]

**Example:** "As a first-time visitor, create an account, complete onboarding, and reach the main dashboard."

## Preconditions

[What state must the environment be in before this test runs?]

- **Application state:** [clean database / seeded with test data / specific configuration]
- **User state:** [no existing account / logged in / specific role or permissions]
- **Environment:** [staging URL / local / production canary]
- **Data fixtures:** [describe any required test data]

## Success Criteria

[What defines successful completion? Be specific about the end state.]

- [ ] [Observable condition that proves the objective was met, e.g., "Dashboard is displayed with the user's name"]
- [ ] [Additional conditions as needed]

## UX Budgets

[Quantitative thresholds for acceptable experience quality. Set based on product standards.]

| Metric | Budget | Rationale |
|--------|--------|-----------|
| Click budget | [max interactions] | [why this number] |
| Navigation depth | [max page transitions] | [why this number] |
| Backtracking limit | [max backward navigations] | [expected: 0 for simple flows] |
| Error encounters | [max user-facing errors] | [expected: 0 for happy path] |
| Time budget | [max seconds, normalized] | [baseline or industry benchmark] |

## Specification Traceability

[Link this test to the specification sections it verifies.]

| Spec section | Behavior tested |
|-------------|-----------------|
| [section ID] | [which user-facing behavior] |
| [ ] | [ ] |

## Failure Handling

[What should happen if the test fails?]

- **Objective not completed:** File as a product defect. The journey log identifies where the agent got stuck.
- **Budget exceeded:** Review the journey log for friction points. Determine whether the budget is too tight or the product needs improvement.
- **Critical error encountered:** File as a severity-1 defect. Product should not crash or lose data during normal use.

## Journey Log Requirements

[What should the agent record during execution?]

- Every page or view visited
- Every interaction (click, type, scroll, navigate)
- Every error message encountered and how it was handled
- Points where the agent hesitated or re-read content
- Dead ends where the agent had to backtrack
- Time spent on each step
- Screenshots at key decision points (optional but recommended)

## Notes

[Additional context, known limitations, or special instructions for this scenario.]

[ ]
