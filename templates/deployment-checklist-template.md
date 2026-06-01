# Deployment Checklist: [Release / Version]

<!--
[Use this template during Phase 7 (Deployment and Observation) to verify readiness, execute deployment, and confirm success. Every item must be checked before proceeding to the next section.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Release version | [ ] |
| Deploy target | [staging / production / canary] |
| Deploy date | [YYYY-MM-DD] |
| Deploy owner | [ ] |
| Rollback owner | [ ] |

## Pre-Deployment

### Quality Gates

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All contract tests pass
- [ ] Product tests pass for critical user journeys (if Phase 6b is active)
- [ ] Linting and static analysis clean
- [ ] Divergence gates pass (no slop fingerprints, if design identity is active)
- [ ] Security audit findings addressed (no open Critical or High)
- [ ] Code coverage meets project thresholds

### Review and Approval

- [ ] Human review approved for all modules in this release
- [ ] Interface contracts frozen and verified
- [ ] Specification changes documented and approved
- [ ] CHANGELOG updated
- [ ] Context state file reflects deployment-ready status

### Environment Readiness

- [ ] Target environment is accessible and healthy
- [ ] Configuration values verified for target environment
- [ ] Database migrations prepared and tested (if applicable)
- [ ] Feature flags configured (if applicable)
- [ ] Monitoring and alerting active for target environment

## Deployment Steps

1. [ ] _[Step 1: e.g., "Run database migrations"]_
2. [ ] _[Step 2: e.g., "Deploy backend services"]_
3. [ ] _[Step 3: e.g., "Deploy frontend"]_
4. [ ] _[Step 4: e.g., "Enable feature flags"]_

## Post-Deployment Verification

### Smoke Tests

- [ ] Core user journey works (manual or automated)
- [ ] Critical API endpoints respond correctly
- [ ] Authentication flow works
- [ ] Data integrity verified

### Monitoring

- [ ] Error rates within normal bounds
- [ ] Response times within SLO
- [ ] No unexpected log patterns
- [ ] Resource utilization within expected range

## Rollback Plan

**Trigger criteria:** _[What conditions trigger a rollback? e.g., "Error rate exceeds 5% for 5 minutes"]_

**Rollback steps:**
1. [ ] _[Step 1]_
2. [ ] _[Step 2]_

**Rollback verification:**
- [ ] Smoke tests pass on rolled-back version
- [ ] Monitoring confirms recovery

## Post-Deployment Notes

[Any observations, issues encountered, or follow-up items.]

| Item | Type | Action Needed |
|------|------|--------------|
| _[observation]_ | _[issue / follow-up / none]_ | _[description]_ |
