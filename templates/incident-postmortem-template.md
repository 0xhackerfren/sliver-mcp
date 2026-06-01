# Incident Postmortem: [Incident Title]

<!--
[Use this template after a production incident to analyze root cause, document impact, and file gap assessments for the recovery pipeline. The postmortem is a blameless analysis focused on process improvement.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Incident date | [YYYY-MM-DD] |
| Severity | Critical / Major / Minor |
| Duration | [Time from detection to resolution] |
| Author | [ ] |
| Reviewers | [ ] |
| Status | Draft / Reviewed / Closed |

## Summary

_[One-paragraph summary of what happened, what was affected, and the resolution.]_

## Timeline

| Time | Event |
|------|-------|
| _[HH:MM]_ | _[Event description]_ |
| _[HH:MM]_ | _[Detection: how was the incident noticed?]_ |
| _[HH:MM]_ | _[Response: who responded and what did they do?]_ |
| _[HH:MM]_ | _[Resolution: what fixed it?]_ |

## Impact

| Dimension | Impact |
|-----------|--------|
| Users affected | _[count or percentage]_ |
| Revenue impact | _[estimated or N/A]_ |
| Data loss | _[yes/no, describe if yes]_ |
| SLO breach | _[which SLOs were violated]_ |

## Root Cause Analysis

**Proximate cause:** _[The direct technical cause]_

**Contributing factors:**
1. _[Factor 1]_
2. _[Factor 2]_

**Root cause:** _[The underlying process or system failure]_

## What the Methodology Missed

[This is the critical section for Codex Automata. Which quality gates, specifications, tests, or reviews should have caught this?]

- [ ] **Spec gap:** _[Was the failure mode specified? If not, this is a spec gap.]_
- [ ] **Mold gap:** _[Were there tests for this scenario? If not, this is a mold gap.]_
- [ ] **SDK gap:** _[Was the relevant behavior constrained by SDK interfaces? If not, this is an SDK gap.]_
- [ ] **Contract gap:** _[Did the failure cross a module boundary without contract tests?]_
- [ ] **Coverage erosion:** _[Did tests exist previously but were removed or disabled?]_
- [ ] **Review miss:** _[Should the human review have caught this?]_
- [ ] **Product test miss:** _[Should a product test have caught this?]_

## Gap Assessments Filed

| Gap | Type | Severity | Link |
|-----|------|----------|------|
| _[description]_ | _[spec/mold/SDK/contract/erosion]_ | _[severity]_ | _[path to gap assessment]_ |

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| _[action]_ | _[who]_ | _[when]_ | _[open/done]_ |

## Lessons Learned

1. _[Lesson and how it changes our process]_

## Recurrence Prevention

_[What systemic change prevents this class of incident from recurring? This should be specific and actionable, not "be more careful."]_
