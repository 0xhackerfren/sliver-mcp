# SDK Design: [Module Name]

<!--
[Use this template during Phase 3 (SDK Design) to define the constraint surface for a module. The SDK contains types, interfaces, and building blocks that agents implement against. No implementation logic belongs here. For the full methodology, see the PLAYBOOK.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | [ ] |
| Bounded context | [ ] |
| Specification reference | [path to spec document] |
| Architecture reference | [path to architecture document] |
| Designed by | [ ] |
| Date | [YYYY-MM-DD] |
| Status | Draft / Approved / Extended |

## Domain Types

[Define types that model domain entities from the specification. Every type must trace to the spec's domain model.]

### [Type Name]

```
[Language-appropriate type definition, e.g., TypeScript interface, Python dataclass, Go struct]
```

**Spec reference:** [Section in specification]
**Constraints:** [Validation rules, invariants]

---

_[Repeat for each domain type]_

## Interfaces

[Define interfaces that expose behaviors specified in the specification. Every method must trace to a spec section.]

### [Interface Name]

```
[Language-appropriate interface definition]
```

| Method | Spec Reference | Input | Output | Errors |
|--------|---------------|-------|--------|--------|
| _[method]_ | _[spec section]_ | _[params]_ | _[return type]_ | _[error conditions]_ |

---

_[Repeat for each interface]_

## Building Blocks

[Identify composable, reusable units. Each block should be registered in the block registry.]

| Block Name | Purpose | SDK Surface | Reusable By |
|-----------|---------|-------------|-------------|
| _[name]_ | _[what it does]_ | _[exported types/interfaces]_ | _[which modules can compose with it]_ |

## Extension Points

[Where does the SDK allow variation without modifying the core surface?]

| Extension Point | Purpose | Constraint |
|----------------|---------|-----------|
| _[e.g., StorageBackend]_ | _[Allow swappable storage]_ | _[Must implement Storage interface]_ |

## Dependencies

[Other SDK modules this design depends on.]

| Dependency | What It Provides | Interface Contract |
|-----------|-----------------|-------------------|
| _[module]_ | _[types/interfaces used]_ | _[path to contract document]_ |

## Design Decisions

[Decisions made during SDK design that constrain implementation. Link to ADRs if applicable.]

1. _[Decision and rationale]_

## Checklist

- [ ] Every specified behavior has a corresponding interface method
- [ ] Every domain entity has a corresponding type
- [ ] No implementation logic exists in the SDK
- [ ] Building blocks registered in the block registry
- [ ] Extension points documented for expected variation
- [ ] Interface contracts align with cross-module boundaries
- [ ] Types and interfaces exported from the SDK module
