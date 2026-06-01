---
name: architecture
description: Guides system decomposition into bounded contexts with interface contracts. Use when the user asks to architect, decompose, define modules, or create interface contracts.
disable-model-invocation: true
---

# Architecture Workflow

Follow this workflow to decompose a system into bounded contexts with interface contracts.

## Step 1: Gather Context

1. Read the project intake document (`docs/intake.md`).
2. Identify the domain boundaries from the problem statement and scope.
3. If research artifacts exist (landscape docs, comparison matrices), review them.

## Step 2: Decompose into Bounded Contexts

1. Identify natural domain boundaries where vocabulary, invariants, or lifecycle rules differ.
2. For each context, create a module boundary document using `templates/module-boundary-template.md`.
3. Aim for contexts small enough to be independently specifiable and testable.
4. Verify no circular dependencies between contexts.

## Step 3: Define Interface Contracts

1. For every boundary between contexts, create an interface contract using `templates/interface-contract-template.md`.
2. Define: API surface, request/response schemas, error semantics, versioning rules, temporal guarantees.
3. Minimize contract surface area to reduce coordination cost.

## Step 4: Record Architecture Decisions

1. For each significant decision, create an ADR using `templates/architecture-decision-record.md`.
2. Document: context, decision, alternatives considered, consequences, and research citations.
3. Decisions that are reversible should say so; decisions that are not should explain the lock-in.

## Step 5: Design Identity (User-Facing Projects)

1. If the project has user-facing surfaces, create a design identity document using `templates/design-identity-template.md`.
2. Define: aesthetic direction, banned patterns (slop fingerprints), typography, color system, spatial system, motion philosophy, copy voice.
3. This document feeds into the SDK as design tokens during Phase 3.

## Step 6: Validate and Report

1. Every module has a boundary document.
2. Every boundary has an interface contract.
3. No circular dependencies.
4. ADRs recorded for significant decisions.
5. Design identity complete (if user-facing).
6. Report readiness for specification writing.

## Reference

- Templates: `templates/module-boundary-template.md`, `templates/interface-contract-template.md`, `templates/architecture-decision-record.md`, `templates/design-identity-template.md`
- Playbook: `PLAYBOOK.md` (Phase 1)
