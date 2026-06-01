# Interface Contract: [Provider Module] to [Consumer Module]

<!--
[Freeze interface contracts before casting against them. Contract tests verify both sides. Breaking changes follow the versioning strategy.]
-->

## Metadata

| Field | Value |
|-------|-------|
| Provider | [module or service name] |
| Consumer | [module or service name] |
| Version | [contract semver or ID] |
| Date | [YYYY-MM-DD] |
| Status | Draft / Frozen / Deprecated [pick one] |

## Overview

[One paragraph: purpose of the boundary, which bounded context owns the contract, and what flows cross it.]

## Endpoints or Methods

### [Name: operation or route]

| Attribute | Definition |
|-----------|------------|
| Name | [ ] |
| Input schema | [types, required fields, validation rules] |
| Output schema | [types, nullability] |
| Error responses | [codes, conditions, payload shape] |
| Idempotency | [yes / no; key or natural idempotency] |
| Rate limits | [if applicable; else N/A] |

[Repeat subsection per endpoint or method.]

## Data Models

[Shared DTOs or events at this boundary.]

**[Model name]**

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| [ ] | [ ] | [ ] | [ ] |

## Invariants

1. [Condition that must always hold at this boundary, e.g., ordering, uniqueness]
2. [ ]

## Versioning Strategy

[How breaking vs non-breaking changes are signaled: URL version, header, package major, deprecation window, consumer notification.]

## Contract Tests

| Test ID | Location (file or suite) | What it proves |
|---------|--------------------------|----------------|
| [CT-001] | [path] | [request/response shape, errors, idempotency] |

[Reference the mold that guards this interface contract in the quality gate.]
