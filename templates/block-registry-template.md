# Building Block Registry

A project-level index of SDK building blocks. Consult this registry before creating new abstractions. If an existing building block's constraint surface satisfies the requirement, compose with it rather than reimplementing. New building blocks are added only through SDK extension following the specification pipeline.

## How to Use

- Add an entry for every building block produced during SDK design and code casting.
- Before implementing a new module, scan this registry for blocks that satisfy part or all of the mold.
- Update entries when a block's SDK surface changes through specification revision and SDK extension.
- Mark blocks as deprecated when they are superseded; do not silently remove entries.

## Registry

| Building Block | Bounded Context | SDK Surface | Molds Satisfied | Contracts Honored | Status |
|----------------|----------------|-------------|-----------------|-------------------|--------|
| _ExampleBlock_ | _ExampleContext_ | _`create()`, `get()`, `delete()`_ | _`test-plan.md` section 2.1_ | _`interface-contracts.md` StorageContract_ | _Active_ |

### Entry Field Definitions

**Building Block.** The name of the composable unit within the SDK constraint surface. Use the type, interface, or module name as it appears in `sdk/` or `src/`.

**Bounded Context.** The context this block belongs to. A block lives in exactly one context.

**SDK Surface.** The exported types, interfaces, functions, or extension points that consumers depend on. List only what is part of the published SDK constraint surface. Implementation internals are excluded.

**Molds Satisfied.** Links to test plan sections or test files that verify this block's behavior. Every building block must have at least one mold.

**Contracts Honored.** Links to interface contract documents or sections that this block's SDK surface implements. Leave empty for blocks that serve only internal composition within their context.

**Status.** One of: Active, Deprecated, Proposed. Active blocks are available for composition. Deprecated blocks are superseded and should not be used in new work. Proposed blocks are planned but not yet cast.
