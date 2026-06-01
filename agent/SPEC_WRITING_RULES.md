# Specification Writing Rules

Rules for agents assisting with specification writing inside a bounded context.

- Specifications must be precise enough to derive tests. If a behavior cannot be tested, it is not specified.
- Every behavior must have: description, preconditions, postconditions, error conditions.
- Edge cases must be enumerated explicitly. Do not leave them implicit.
- Failure modes must be documented: what happens when things go wrong.
- Use concrete examples where possible (given X input, expect Y output).
- Avoid vague language. "Handles errors gracefully" is not a specification. "Returns a ValidationError with code INVALID_INPUT when the title exceeds 200 characters" is.
- Do not make design decisions in the specification. The specification defines WHAT, not HOW (design belongs outside the behavioral contract unless the architecture explicitly freezes it).
- Cross-reference interface contracts when the module depends on or provides interfaces.
- Flag any unresolved ambiguity as an Open Question rather than making assumptions.
