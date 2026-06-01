# Brownfield Audit: Sliver MCP Server

## Metadata

| Field | Value |
|-------|-------|
| Project name | sliver-mcp |
| Audited by | Agent (Codex Automata brownfield onboarding) |
| Date | 2026-05-28 |
| Codebase age | ~1 month (v1.0.0 released 2026-05-20) |
| Estimated module count | 1 (monolith `server.py`, 3821 lines) |
| Current test coverage | SDK layer: 100 unit tests via pytest (validators, errors, types, ATT&CK map) |
| Current CI/CD | GitHub Actions (ci.yml): ruff lint, pytest, Python 3.10-3.12 matrix |

## Module Inventory

| Module | Bounded Context | Risk Level | Change Frequency | Test Coverage | Spec Exists | SDK Exists | Priority |
|--------|----------------|------------|-----------------|---------------|-------------|------------|----------|
| Connection Management | C2 Client | Critical | Weekly | None | No | No | 1 |
| OPSEC Guard | Operational Security | Critical | Weekly | None | No | No | 2 |
| Session/Beacon Tools | Implant Interaction | Critical | Daily | None | No | No | 3 |
| Execution Tools | Remote Execution | Critical | Daily | None | No | No | 4 |
| State Database | Engagement Tracking | High | Weekly | None | No | No | 5 |
| Implant Generation | Payload Creation | High | Weekly | None | No | No | 6 |
| Playbooks | Automated Workflows | High | Weekly | None | No | No | 7 |
| Filesystem Tools | File Operations | Medium | Monthly | None | No | No | 8 |
| Process/Network Tools | Reconnaissance | Medium | Monthly | None | No | No | 9 |
| Registry/Service Tools | Windows Post-Exploit | Medium | Monthly | None | No | No | 10 |
| Pivoting Tools | Lateral Movement | High | Monthly | None | No | No | 11 |
| Evasion Pipeline | AV Bypass | High | Monthly | None | No | No | 12 |
| Cleanup Tools | Engagement Teardown | Medium | Rare | None | No | No | 13 |
| Hosting Tools | C2 Web Hosting | Low | Rare | None | No | No | 14 |
| Error Handling | Cross-cutting | Critical | Daily | None | No | No | 15 |
| Configuration | Cross-cutting | High | Weekly | None | No | No | 16 |

## Dependency Map

| Module | Depends On | Depended On By |
|--------|-----------|---------------|
| Connection Management | Configuration | All tool modules |
| OPSEC Guard | Connection Management, Configuration | Execution Tools, Playbooks |
| Session/Beacon Tools | Connection Management | Execution, Filesystem, Process, Registry, Pivoting, Playbooks |
| Execution Tools | Connection Management, OPSEC Guard, Session Tools | Playbooks |
| State Database | Configuration | Playbooks, Cleanup, Session Tools, Post-Exploit |
| Implant Generation | Connection Management | Evasion Pipeline |
| Playbooks | Execution, Session, OPSEC, State Database | (terminal consumer) |
| Error Handling | (none) | All modules |
| Configuration | (none) | All modules |

## Gap Summary

| Gap Type | Count | Notes |
|----------|-------|-------|
| Spec gaps (code without spec) | 16 | Every module -- no specifications exist |
| Mold gaps (spec without tests) | 16 | No specs and no tests anywhere |
| SDK gaps (code without SDK types) | 16 | No typed interfaces, protocols, or constraint surface |
| Contract gaps (boundaries without contract tests) | 16 | All module boundaries are implicit (single file) |
| Coverage erosion (tests lost over time) | 0 | Tests never existed |

## Existing Assets to Preserve

- **Existing tests worth keeping:** `check.py` (syntax + import validation; trivial but useful as smoke check)
- **Existing documentation:** `README.md` (feature matrix, tool reference), `INSTRUCTIONS.md` (agent workflows), `CONTRIBUTING.md` (dev conventions), `CHANGELOG.md` (v1.0.0 notes)
- **Existing CI/CD gates:** None
- **Existing code patterns worth extracting into SDK:**
  - `_format_tool_error()` -- structured error response with hints
  - `_json_out()` -- JSON serialization helper
  - `_get_client()` / `_interact()` -- connection management with auto-reconnect
  - `_opsec_preflight()` / `_opsec_scan_session()` -- EDR scanning
  - `_get_state_db()` -- SQLite state management
  - `_TOOL_CATALOG` -- tool metadata registry
  - `edr_processes.json` -- EDR signature database
  - `cleanup_manifest.json` -- cleanup artifact paths

## Critical Bugs Identified

1. **~~Hardcoded C2 fallback IP~~** in `sliver_migrate` (~line 3169) -- **FIXED**: now fails explicitly when `ActiveC2` is empty instead of falling back to a hardcoded address
2. **~~OPSEC fail-open~~** -- **FIXED**: `_opsec_scan_session` now returns `safe: False` on exception (fail-closed)
3. **ps() return type inconsistency**: `sliver_ps` treats ps() as list, `_opsec_scan_session` treats as `{Processes: [...]}`
4. **Command injection**: `target_ip` and other user inputs interpolated into PowerShell without validation
5. **Arg splitting**: `_exec_quiet` uses `args.split()` which breaks quoted arguments
6. **Dead code**: `_FORMAT_MAP` defined but never used
7. **Plaintext credentials**: `credentials.secret` stored unencrypted in SQLite
8. **Beacon support**: beacons are list/kill/rename only, no interaction/task execution

## Onboarding Plan

### Approach: Full Recovery (Complete Profile)

Since no specs, SDK, or tests exist, this is a ground-up onboarding. We adopt the Complete profile immediately and build forward through the full Codex Automata pipeline.

### Phase 1: Specification (All Modules)

Write specifications for all bounded contexts from domain knowledge:
1. `docs/architecture.md` -- system decomposition, data flow, module boundaries
2. `docs/security.md` -- threat model, input validation, credential handling, OPSEC
3. `docs/api-coverage.md` -- Sliver API surface, missing capabilities, interface contracts
4. `docs/features.md` -- differentiating features (ATT&CK, orchestration, reporting)

### Phase 2: SDK Constraint Surface

Extract and define typed interfaces:
1. `sdk/types.py` -- response envelopes, domain models
2. `sdk/protocols.py` -- abstract interfaces (C2Client, StateStore, OpsecGuard)
3. `sdk/errors.py` -- error hierarchy
4. `sdk/validators.py` -- input validation contracts
5. `sdk/attack_map.py` -- ATT&CK technique registry

### Phase 3: Test Molding

Derive tests from specifications against SDK interfaces.

### Phase 4: Code Casting

Implement against molds, starting with critical bug fixes through modularization to new features.

## CI/CD Integration Plan

| Gate | When to Activate | Scope |
|------|-----------------|-------|
| Syntax check (check.py) | Immediately | All commits |
| Lint (ruff) | After SDK phase | All Python files |
| Type check (pyright) | After SDK phase | SDK + src |
| Unit tests (pytest) | After test molding | tests/ |
| Spec check | After first spec | New PRs |
| Divergence gate | After code casting | All PRs |
