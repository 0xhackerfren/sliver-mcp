# User Profile: [Profile Name]

<!--
[Define a simulated user persona for product testing. This profile constrains how an AI agent behaves when operating the application. It is a test fixture, not a marketing persona. For the full product testing reference, see https://github.com/0xhackerfren/Codex-Automata/blob/main/reference/product-testing.md]
-->

## Metadata

| Field | Value |
|-------|-------|
| Profile name | [e.g., "First-time visitor," "Power user," "Accessibility-dependent user"] |
| Version | [ ] |
| Date | [YYYY-MM-DD] |
| Author | [name or role] |

## Identity

- **Role:** [What role does this user play? e.g., end user, admin, team lead, external partner]
- **Context:** [What situation is this user in? e.g., evaluating the product for the first time, performing a daily task, handling an emergency]

## Technical Literacy

[How comfortable is this user with software?]

- **Level:** High / Moderate / Low [pick one]
- **Behavioral implications:**
  - High: scans for patterns, uses keyboard shortcuts, skips tutorials, expects conventional UI placement
  - Moderate: follows visible cues, reads labels, uses help when stuck, tries obvious actions first
  - Low: reads everything carefully, avoids unfamiliar interfaces, needs explicit guidance at each step

## Domain Knowledge

[How well does this user understand the problem domain?]

- **Level:** Expert / Familiar / Novice [pick one]
- **Behavioral implications:**
  - Expert: understands terminology, anticipates workflows, uses domain-specific shortcuts
  - Familiar: recognizes core concepts, may need help with advanced features
  - Novice: needs plain-language explanations, may not understand domain jargon

## Goals

[What is this user generally trying to accomplish? Goals shape how the agent prioritizes actions.]

1. [ ]
2. [ ]

## Constraints

[What limitations does this user operate under? Check all that apply and elaborate.]

- **Accessibility constraints:** _[Screen reader dependency / Keyboard-only / Low vision (zoom level) / Reduced motion / Cognitive load sensitivity / None]_
- [ ] **Device:** [desktop / mobile / tablet; screen size; input method]
- [ ] **Accessibility:** [screen reader / keyboard-only / high contrast / reduced motion / magnification]
- [ ] **Network:** [broadband / slow connection / intermittent connectivity]
- [ ] **Session time:** [unlimited / limited to N minutes / frequently interrupted]
- [ ] **Language:** [native speaker / non-native / specific language]
- [ ] **None:** This profile has no special constraints.

## Behavioral Tendencies

[How does this user approach software? These tendencies constrain the agent's navigation strategy.]

- **Instructions:** [reads carefully / skims / skips entirely]
- **Exploration:** [follows the most obvious path / explores menus and options / uses search first]
- **Error response:** [reads error messages carefully / retries the same action / abandons the task / seeks help]
- **Patience:** [persistent, tries many approaches / gives up after 2-3 failures]
- **Trust level:** [trusts the application / suspicious of data collection / cautious with permissions]

## Specification Traceability

[Link this profile to the specification sections that define target users.]

| Spec section | User class described |
|-------------|---------------------|
| [section ID] | [which user class this profile represents] |
| [ ] | [ ] |

## Notes

[Additional context about this profile. What makes this user type important to test?]

[ ]

---

## Example: Accessibility-Constrained Profile

| Field | Value |
|-------|-------|
| Name | Screen Reader User |
| Role | Returning customer completing a purchase |
| Technical literacy | High (experienced screen reader user) |
| Domain knowledge | Moderate (familiar with the product category) |
| Accessibility constraints | Screen reader only (VoiceOver/NVDA), no visual scanning |
| Behavioral tendencies | Navigates by headings and landmarks. Skips decorative content. Relies on link text and button labels for orientation. Frustrated by unlabeled form fields and focus traps. |

**Goals:** Complete a purchase using only screen reader navigation. Verify all interactive elements are reachable and labeled.

**UX Budget overrides:** Click budget may be higher (screen reader navigation requires more interactions). Backtracking budget should be tight (backtracking indicates navigation confusion).
