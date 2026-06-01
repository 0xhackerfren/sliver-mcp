# Test Molding Rules

Rules for agents deriving tests from specifications (test molding builds the mold; the SDK defines the constraint surface; casting follows).

- Every behavior in the specification must have at least one test.
- Every edge case must have a dedicated test.
- Test names must clearly reference the specification section they verify (for example `test_create_task_empty_title` maps to Behavior 1, Error Condition 1).
- Tests must be written against SDK interfaces. Do not reference or assert against abstractions outside the constraint surface.
- Tests must be sharp: they constrain the implementation so incorrect behavior fails. A test that passes for arbitrary implementations fails as a quality gate.
- Tests must not over-specify: assert behavior required by the specification, not incidental implementation detail. Do not assert on internal data structures unless the specification requires observable behavior tied to those structures.
- Contract tests must exist for every interface between modules (honor interface contracts explicitly).
- All tests must compile. All targeted tests must fail before code casting begins (red state).
- Do not write implementation code during test molding. The mold must exist before casting.
- If a specification section is untestable, flag it and request clarification rather than skipping it.
- If an SDK interface is missing for a behavior you need to test, report the gap and request SDK extension.
- When the specification defines input constraints (length limits, type restrictions, format requirements), derive property-based tests that verify the constraint holds for any valid input and rejects any invalid input. Use a PBT framework appropriate for the project language.
- Property-based tests trace to specification sections just like traditional tests. The specification invariant is the property. The generator strategy derives from the input constraints in the specification.
- Properties must be written in red state. The property definition and generator exist before the implementation. If the PBT framework requires the types to compile, the SDK types must exist first.
- Prefer properties over exhaustive example enumeration. Instead of testing 5 valid title lengths, write one property: "for any string of length 1-200, createTask succeeds."
