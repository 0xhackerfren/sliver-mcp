# SDK Design Rules

Rules for agents translating specifications and interface contracts into the compilable SDK constraint surface (Phase 3).

- The SDK defines the vocabulary downstream molds and castings must speak. It is not a utility library. Every type, interface, and extension point represents an architectural decision.
- Read the specification and interface contracts before defining any SDK surface. The SDK derives from the spec, not from implementation convenience.
- One SDK module per bounded context. Each context's public surface is a separate package or namespace. Shared types live in a single shared-types module.
- Every type and interface must trace to a specification section or interface contract clause. If you cannot cite the source, the building block does not belong in the SDK.
- Define building blocks at the right abstraction level. Prefer domain concepts over implementation details. A `PaymentResult` type is an SDK building block; a `DatabaseRow` type is not.
- Include extension points where the specification indicates future growth. Extension points are explicit (plugin interfaces, event schemas, hooks), not implicit (any-typed escape hatches).
- The SDK must compile with no implementation behind it. Interfaces define shape. Implementation happens during code casting (Phase 5), not SDK design.
- For user-facing projects, design tokens from the design identity document become SDK building blocks. Colors, typography, spacing, shadows, radii, breakpoints, and motion values are all named tokens. Zero raw visual values in the SDK's public surface.
- Copy voice constraints, naming registries, and pattern catalogs from the design identity are part of the SDK when they constrain agent behavior mechanically (e.g., an enum of allowed component names, a type restricting CTA text to approved phrases).
- Do not add building blocks speculatively. If the specification does not require a capability, the SDK should not provide it. Growth follows the extension pipeline: spec change, then SDK extension, then new molds.
- When the specification is ambiguous about whether a concept is a first-class building block or an implementation detail, flag it for human resolution. Do not guess.
- Interface contracts between bounded contexts become compilable types in the SDK. Request schemas, response schemas, event payloads, error enums, and version markers are SDK surface.
- Validate consistency: every interface contract field appears in the SDK types. Every SDK type referenced by molds exists. No orphaned types that nothing tests against.
- Do not modify existing SDK interfaces without explicit human approval. SDK changes propagate to molds and castings; unauthorized changes cascade uncontrolled.
- Document each building block with its specification source reference so downstream agents can trace from type back to intent.
