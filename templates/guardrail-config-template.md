# Guardrail Configuration: [Project Name]

<!--
[Use this template to customize action classification for your project. Override defaults from the methodology when your project has different risk profiles. For the full guardrails reference, see reference/guardrails.md.]
-->

## Profile

| Field | Value |
|-------|-------|
| Adoption profile | Essential / Standard / Complete |
| Project name | [ ] |
| Last updated | [YYYY-MM-DD] |
| Approved by | [ ] |

## Classification Overrides

[Only list actions where your project differs from the methodology defaults. Unmodified actions use the default classification from reference/guardrails.md.]

| Action | Default Tier | Project Tier | Rationale |
|--------|-------------|-------------|-----------|
| _[e.g., "Database migrations"]_ | _[LOG]_ | _[APPROVE]_ | _[e.g., "Production data at risk"]_ |
| _[e.g., "Feature flag changes"]_ | _[LOG]_ | _[APPROVE]_ | _[e.g., "User-facing impact"]_ |

## Additional APPROVE Actions

[Actions specific to your project that are not in the default list but require approval.]

- [ ] _[Action description and rationale]_

## Reduced Actions

[Actions you've moved to a lower tier based on project context. Document the justification.]

| Action | Default Tier | Project Tier | Justification |
|--------|-------------|-------------|--------------|
| _[e.g., "Adding dependencies"]_ | _[APPROVE]_ | _[LOG]_ | _[e.g., "Pre-approved dependency list maintained"]_ |

## Override Log

[Track guardrail overrides for retroactive review.]

| Date | Action | Default Tier | Override | Reason | Reviewer |
|------|--------|-------------|----------|--------|----------|
| _[date]_ | _[action]_ | _[tier]_ | _[new tier]_ | _[why]_ | _[who]_ |
