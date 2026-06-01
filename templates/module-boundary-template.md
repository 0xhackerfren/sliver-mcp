# Module Boundary: [Module Name]

<!--
[Clarifies ownership within a bounded context: what crosses the boundary via interface contracts, what stays internal. Use with architecture decision records where trade-offs appear.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | [ ] |
| Bounded context | [ ] |
| Owner | [team or role] |
| Date | [YYYY-MM-DD] |

## Purpose

[One paragraph: role of this module in the system flow, without listing every implementation detail.]

## Responsibilities

**Owns:**

- [ ]

**Does not own:**

- [ ]

## Provided Interfaces

| Interface | Contract reference | Consumers (typical) |
|-----------|-------------------|---------------------|
| [name] | [link or ID] | [ ] |

## Required Interfaces

| Interface | Contract reference | Providers (typical) |
|-----------|-------------------|---------------------|
| [name] | [link or ID] | [ ] |

## Internal Domain Model

[Entities, aggregates, or key state owned inside the module; not necessarily exposed at boundaries.]

- [ ]

## Data Ownership

[Which records or streams are source of truth here; consistency rules.]

## Deployment Unit

[Standalone service, library package, monolith component, serverless function, etc.]

- **Unit:** [ ]
- **Scaling:** [horizontal / vertical, triggers]

## Dependencies

- **External systems:** [ ]
- **Libraries:** [ ]
- **Infrastructure:** [queues, object storage, identity]

## Constraints

- **Performance envelope:** [ ]
- **Security boundary:** [trust zone, secrets]
- **Other:** [regulatory, residency]
