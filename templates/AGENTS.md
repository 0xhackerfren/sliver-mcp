# Agents: Codex Automata Templates

These files live under `templates/`. They are **templates**, not project-specific artifacts.

## How to Use This Directory

When a human asks you to create a new specification, test plan, interface contract, or other scaffolded document, locate the closest matching template here and treat it as the **starting structure** for the copied document in the user's project directory.

## Rules

1. **Do not edit files in `templates/`** to satisfy a one-off request. Copy the chosen template into the target project path, then fill it in there.
2. **Preserve template sections**. Do not delete sections because they seem unused; leave them in place with honest placeholders or `N/A` only when the specification truly does not apply, and explain why briefly in brackets if needed.
3. **Honor the Codex Automata flow**: specification first, SDK (constraint surface) second, mold (tests) third, casting (implementation) fourth. Templates align with interface contracts, SDK interfaces, and quality gates across bounded contexts.

## Terminology

Use consistent wording in filled-in documents: **research**, **specification**, **SDK**, **constraint surface**, **building block**, **local-first**, **design identity**, **design token**, **convergence**, **divergence gate**, **slop fingerprint**, **mold**, **casting**, **bounded context**, **interface contract**, **quality gate**, **agent task**, **assembly pressure**, **human review**, **flow**, **recovery**, **gap assessment**, **spec gap**, **SDK gap**, **mold gap**, **coverage erosion**, **contract gap**, **product test**, **user profile**, **test objective**, **UX budget**, **SDK extension**.
