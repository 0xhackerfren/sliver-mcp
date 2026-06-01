# Specification: [Module Name]

<!--
[Replace bracketed placeholders. This document is the primary engineering artifact; tests (mold) and code (casting) trace to it. Resolve Open Questions before deriving tests.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | [e.g., Order Matching] |
| Bounded context | [e.g., Trading] |
| Version | [e.g., 1.0.0-draft] |
| Date | [YYYY-MM-DD] |
| Author | [name or role] |
| Status | Draft / Review / Approved [pick one] |

## Overview

[One paragraph: what this module does, why it exists, how it fits the bounded context.]

## Scope

**Included:**

- [ capability or responsibility ]
- [ add rows as needed ]

**Excluded (explicit):**

- [ out-of-scope item; prevents scope creep ]
- [ add rows as needed ]

## Domain Model

[Describe entities, value objects, aggregates if any, and relationships. Use bullets or a short diagram reference.]

- **Entities:** [name, lifecycle, identity]
- **Value objects:** [immutable types, equality rules]
- **Relationships:** [1:1, 1:N, ownership]

## Behaviors

[Number each behavior. Preconditions, postconditions, and error conditions must be falsifiable so the mold can target them.]

1. **[Behavior name]**  
   - **Description:** [ observable behavior ]  
   - **Preconditions:** [ what must hold before ]  
   - **Postconditions:** [ what must hold after success ]  
   - **Error conditions:** [ validation failures, conflicts, timeouts; expected handling ]

2. **[Next behavior]**  
   - (repeat structure)

## Edge Cases

1. **[Edge case]:** [Expected behavior]
2. **[Edge case]:** [Expected behavior]

## Failure Modes

| Scenario | Expected behavior |
|----------|-------------------|
| Dependency unreachable | [degrade, fail fast, retry policy] |
| Invalid input | [errors surfaced to caller] |
| Resource exhaustion | [backpressure, limits, messaging] |

[Add rows for timeouts, partial writes, concurrency, etc.]

## Non-Functional Requirements

- **Performance:** [latency or throughput targets, with measurement context]
- **Availability:** [SLO-style statement if applicable]
- **Security:** [authz, encryption, secrets handling constraints]

## Interface Dependencies

**Depends on (consumer side):**

- [Interface contract reference or bounded context boundary]

**Provides (producer side):**

- [Interface contract reference]

## Open Questions

1. **[Question]:** [why it blocks test derivation or casting]
2. **[Question]:** [owner or forum to resolve]

[None may remain open before molds are finalized for this version.]

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| [0.1] | [YYYY-MM-DD] | [who] | [what changed] |
