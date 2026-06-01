# Security Audit: [Module / Scope]

<!--
[Use this template to document security audit findings. For each finding, provide severity, description, impact, and remediation. Findings of significant severity or above should be filed as gap assessments for the recovery pipeline.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Scope | [Module name or "full application"] |
| Audited by | [human / agent] |
| Date | [YYYY-MM-DD] |
| Specification version | [commit hash or version] |
| Code version | [commit hash or version] |

## Summary

| Severity | Count |
|----------|-------|
| Critical | [ ] |
| High | [ ] |
| Medium | [ ] |
| Low | [ ] |
| Informational | [ ] |

**Overall posture:** [Strong / Acceptable / Needs Improvement / Critical Risk]

## Findings

### Finding 1: [Title]

| Field | Value |
|-------|-------|
| Severity | Critical / High / Medium / Low / Informational |
| Category | [Injection / Auth / Data Exposure / Dependencies / Input Validation / Crypto / Configuration] |
| Location | [File path and line range] |
| Spec reference | [Specification section or "unspecified"] |

**Description:** [What the vulnerability is]

**Impact:** [What could happen if exploited]

**Remediation:** [Specific steps to fix]

**Gap assessment needed:** Yes / No

---

_[Repeat for each finding]_

## Unspecified Security Requirements

[List security behaviors that should be in the specification but are not. Each is a spec gap.]

- [ ] _[e.g., "No rate limiting specified for login endpoint"]_
- [ ] _[e.g., "No data retention policy specified"]_

## Recommendations

[Overall recommendations beyond individual findings.]

1. [ ] _[Recommendation]_
