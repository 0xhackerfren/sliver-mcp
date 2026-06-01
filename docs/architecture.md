# Specification: Sliver MCP System Architecture

## Metadata

| Field | Value |
|-------|-------|
| Module name | Sliver MCP (system) |
| Bounded context | Full application — C2 operator bridge for AI agents |
| Version | 1.0.0-draft |
| Date | 2026-05-28 |
| Author | Codex Automata (brownfield onboarding) |
| Status | Draft |

## Overview

Sliver MCP is a Model Context Protocol (MCP) server that enables AI agents (Cursor, Claude Desktop, and other MCP clients) to operate the [Sliver C2](https://github.com/BishopFox/sliver) framework during authorized red team engagements. The server exposes Sliver teamserver capabilities as typed MCP tools over **stdio** transport using FastMCP, delegating all C2 operations to **sliver-py** over **mTLS gRPC**. A local **SQLite engagement state database** tracks targets, credentials, findings, access events, and pivot paths across the engagement lifecycle. Cross-cutting concerns—connection health with auto-reconnect, structured error responses, OPSEC pre-flight scanning, and subprocess-based evasion pipelines—are centralized so tool modules remain thin orchestration layers.

Today the implementation lives in a single monolith (`server.py`, ~3821 lines, ~79 MCP tools). This specification defines the **target modular package layout**, bounded contexts, data flows, and non-functional contracts that subsequent SDK, mold, and casting work must satisfy. Brownfield inventory and gap analysis are recorded in `docs/audit.md`.

## Scope

**Included:**

- MCP server process lifecycle: FastMCP app creation, stdio transport, `main()` entry point
- Decomposition of `server.py` into the `sliver_mcp/` package structure (see [Target package layout](#target-package-layout))
- gRPC/mTLS connection management to Sliver teamserver via `SliverClient`
- All existing MCP tools (connection, sessions, implants, execution, filesystem, process, registry, pivoting, evasion, post-exploit, state, cleanup, hosting, playbooks)
- Planned tools marked **(new)** in the target layout: beacon task interaction, BOF execution, ATT&CK coverage, multi-session orchestration, engagement reporting
- Engagement state persistence (SQLite WAL, async-safe access)
- OPSEC guard (EDR signature config, pre-flight on high-risk tools)
- Tool registration pattern, `ToolResponse` envelope, `@tool_handler` wrapper, access audit logging
- External configuration via environment variables and project-root-relative assets (`edr_processes.json`, `cleanup_manifest.json`, `evasion/`)

**Excluded (explicit):**

- Sliver teamserver installation, operator certificate issuance, or implant callback infrastructure (out of repo; assumed running and reachable)
- MCP client UI/UX (Cursor, Claude, etc.) beyond stdio protocol compliance
- Encryption at rest for credentials in SQLite (deferred; see Open Questions and `docs/security.md`)
- Non-stdio MCP transports (HTTP/SSE) unless added via a future spec revision
- Automated deployment of implants to targets (operators trigger callbacks through normal Sliver workflows)
- User-facing web dashboards or design tokens (no human UI in this project)

## Target package layout

The monolith `server.py` at the repository root is **deprecated** after modularization. All runtime code moves under `sliver_mcp/`:

```
sliver_mcp/
  __init__.py              # Package init, __version__
  server.py                # FastMCP app creation, tool registration, main()
  client.py                # SliverClient singleton, _get_client(), _interact(), health, auto-reconnect
  errors.py                # SliverMCPError hierarchy, _format_tool_error(), contextual hints
  opsec.py                 # OPSEC guard, EDR signature loading, _opsec_preflight(), _opsec_scan_session()
  config.py                # Environment variable resolution, path handling, defaults
  utils.py                 # _json_out(), _run_cmd(), protobuf wire helpers, _session_object_to_dict()
  state/
    __init__.py
    db.py                  # SQLite engagement state DB with WAL, async-safe locking
    models.py              # Dataclasses: Target, Credential, Finding, AccessLog, PivotPath, AttackTechnique
  tools/
    __init__.py            # register_tools(mcp) helper
    connection.py          # sliver_status, sliver_reconnect, sliver_help, sliver_jobs,
                           #   sliver_start_*_listener, sliver_stop_job, sliver_operators
    sessions.py            # sliver_sessions, sliver_session_info, sliver_beacons, sliver_beacon_tasks (new),
                           #   sliver_kill_*, sliver_rename_*, sliver_interact_beacon (new)
    implants.py            # sliver_generate, sliver_regenerate_implant, sliver_implant_builds
    execution.py           # sliver_execute, sliver_execute_assembly, sliver_execute_shellcode,
                           #   sliver_execute_bof (new), sliver_sideload, token ops, migrate, process_dump
    filesystem.py          # sliver_ls, sliver_cd, sliver_pwd, sliver_upload, sliver_download,
                           #   sliver_screenshot, sliver_rm, sliver_mkdir
    process.py             # sliver_ps, sliver_netstat, sliver_ifconfig, sliver_terminate_process
    registry.py            # sliver_registry_read/write/create, sliver_start/stop/remove_service,
                           #   sliver_get/set_env
    pivoting.py            # sliver_socks_start/stop, sliver_portfwd_add/list/rm
    evasion.py             # sliver_encrypt_shellcode, sliver_build_loaders, sliver_evasion_pipeline,
                           #   sliver_preflight_defender
    postexploit.py         # sliver_discovery, sliver_lateral_check, sliver_collect_evidence, sliver_opsec_check
    state_tools.py         # sliver_state_* (targets, creds, findings, pivots, summary, export,
                           #   auto_discover, log_access)
    cleanup.py             # sliver_cleanup_target, sliver_full_cleanup
    hosting.py             # sliver_website_add, sliver_websites
    playbooks.py           # sliver_playbook_initial_recon, privesc_check, cred_harvest, persist_check
    attack_mapping.py      # sliver_attack_coverage (new)
    orchestration.py       # sliver_multi_exec, sliver_pivot_chain, sliver_session_select (new)
    reporting.py           # sliver_generate_report, sliver_engagement_timeline (new)
```

**Entry point migration:** `pyproject.toml` `[project.scripts]` must point to `sliver_mcp.server:main`. Root `server.py` may remain temporarily as a thin shim importing `main` for backward-compatible MCP client paths.

## Data flow

```mermaid
flowchart LR
  subgraph client [MCP Client]
    Agent[AI Agent / IDE]
  end
  subgraph mcp [sliver_mcp]
    FMCP[FastMCP server.py]
    Tools[tools/*.py]
    Client[client.py]
    State[(state/db.py SQLite)]
    Opsec[opsec.py]
    Utils[utils.py / errors.py]
  end
  subgraph external [External]
    TS[Sliver Teamserver gRPC/mTLS]
    FS[Local FS: evasion, evidence, configs]
  end
  Agent -->|stdio JSON-RPC| FMCP
  FMCP -->|@mcp.tool dispatch| Tools
  Tools --> Utils
  Tools --> Opsec
  Tools --> Client
  Tools --> State
  Client -->|SliverClient| TS
  Tools -->|subprocess| FS
  State --> FS
```

**Request path (typical implant tool):**

1. MCP client invokes a tool (e.g. `sliver_execute`) over stdio.
2. FastMCP routes to the registered async handler in the appropriate `tools/` module.
3. `@tool_handler` logs the invocation, runs OPSEC pre-flight when applicable, and wraps execution.
4. Handler calls `_interact(session_id)` → `_get_client()` → gRPC RPC on the teamserver.
5. Handler builds a `ToolResponse` success envelope via `_json_out()` and returns a JSON string to the client.

**State path:** `state_tools`, `playbooks`, `postexploit`, and `cleanup` read/write the engagement DB through `state/db.py` (never opening SQLite connections ad hoc in tool modules). `sliver_sessions` and discovery playbooks may auto-register targets via shared state helpers.

**Evasion path:** `evasion` tools invoke local scripts under `SLIVER_EVASION_DIR` via `_run_cmd()` and may call `sliver_generate` / shellcode paths on the teamserver before compiling loaders locally.

## Bounded contexts

| Context | Modules | Responsibility | Upstream deps |
|---------|---------|----------------|---------------|
| **C2 Connection** | `client.py`, `config.py` | mTLS gRPC lifecycle, config path resolution, channel health, reconnect | `config` → env; `client` → sliver-py |
| **Implant Operations** | `tools/sessions`, `implants`, `execution`, `filesystem`, `process`, `registry` | Session/beacon management, remote execution, file/process/registry ops | C2 Connection, OPSEC (execution subset) |
| **Network Operations** | `tools/pivoting`, `hosting` | SOCKS5, port forwards, C2 web hosting | C2 Connection, Implant Operations (session_id) |
| **Engagement Intelligence** | `state/*`, `tools/postexploit`, `playbooks`, `attack_mapping`, `reporting`, `state_tools` | Persistent engagement model, discovery, playbooks, ATT&CK mapping, reports | C2 Connection, State DB; optional Implant Operations |
| **Operational Security** | `opsec.py`, `tools/evasion`, OPSEC hooks in `execution` | EDR detection, high-risk preflight, evasion pipeline | C2 Connection, `edr_processes.json` |
| **Orchestration** | `tools/orchestration` | Multi-session commands, pivot chains, session selection heuristics | Implant Operations, Engagement Intelligence |
| **Infrastructure** | `errors.py`, `utils.py`, `config.py`, `server.py` | JSON envelopes, protobuf fixes, subprocess runner, tool catalog | None (foundational) |

**Dependency rule:** Bounded contexts must not form cycles. `Engagement Intelligence` may call into `Implant Operations` only through orchestration/playbook layers, not from low-level `client.py`. `Infrastructure` is acyclic and consumed by all contexts.

## Tool registration pattern

1. **`server.py`** constructs a single shared `FastMCP` instance (`mcp = FastMCP("sliver", instructions=...)`).
2. Each file under `tools/` defines **async** tool functions decorated with `@mcp.tool()` (decorator applied after importing the shared `mcp` from `server` or via a registration callback to avoid circular imports).
3. **`tools/__init__.py`** exposes `register_all_tools(mcp: FastMCP) -> None` that imports every tool module for side-effect registration (or explicitly registers callables).
4. **`server.py` `main()`** calls `register_all_tools(mcp)` then `mcp.run(transport="stdio")`.
5. Tool names remain stable: `sliver_<verb>_<noun>` matching existing MCP catalog in `_TOOL_CATALOG`.
6. **`sliver_help`** reads categorized metadata from a single registry (evolved from `_TOOL_CATALOG`) owned by `tools/__init__.py` or `server.py`.

**Import order constraint:** `config` and `errors` load before `client`; `client` before any tool module; `state/db` before `state_tools` and playbooks.

## Domain Model

### Runtime entities (Sliver teamserver — read-only via gRPC)

| Entity | Identity | Key attributes | Lifecycle |
|--------|----------|----------------|-----------|
| **Session** | `session_id` (UUID string) | hostname, username, OS, arch, transport, remote_address, PID | Created on implant callback; ends on kill or disconnect |
| **Beacon** | `beacon_id` | check-in interval, tasks queue | Long-haul; rename/kill supported; task interaction **(new)** |
| **Job / Listener** | numeric `job_id` | protocol (HTTP/HTTPS/DNS), bind address | Started/stopped via connection tools |
| **Implant build** | build name / hash | GOOS, GOARCH, format, C2 URLs | Generated/regenerated via implants tools |
| **Operator** | operator name | connection metadata | Listed via `sliver_operators` |

### Engagement entities (local SQLite — `state/models.py`)

| Entity | Identity | Required fields | Optional / defaults |
|--------|----------|-----------------|---------------------|
| **Target** | `id` (integer PK) | `hostname` | `ip`, `os`, `domain`, `access_level` (default `none`), `notes`, timestamps |
| **Credential** | `id` | `username`, `secret`, `cred_type` (default `plaintext`) | `domain`, `source`, `target_id` FK |
| **Finding** | `id` | `title`, `severity` (default `info`) | `description`, `evidence_path`, `target_id` FK |
| **AccessLog** | `id` | `session_id`, `timestamp` | `target_id` FK, `method`, `status` (default `active`) |
| **PivotPath** | `id` | `source_target_id`, `dest_target_id` | `method`, `status` (default `planned`) |
| **AttackTechnique** | `technique_id` (ATT&CK ID, e.g. `T1059.001`) | `name`, `tactic` | `tool_used`, `session_id`, `target_id`, `evidence`, `timestamp` — persisted for coverage/reporting **(new table)** |

**Relationships:**

- Target 1:N Credential, Finding, AccessLog (via `target_id`)
- Target N:N PivotPath (source/dest FKs)
- AttackTechnique N:1 Target (optional), references session/tool invocation metadata

### Value objects

| Name | Fields | Equality / validation |
|------|--------|-------------------------|
| **ToolResponse** | See [ToolResponse envelope](#toolresponse-envelope) | Serialized JSON; `status` discriminates success vs error |
| **OpsecScanResult** | `detected: list[{product, process}]`, `safe: bool`, optional `error` | `safe` is true iff `detected` is empty and no error |
| **SessionDict** | Plain dict from `_session_object_to_dict()` | Used in tool output only |
| **DiscoverySummary** | hostname, domain, username, is_admin, os_*, ip_addresses, access_level | Produced by discovery/playbook parsers in `utils.py` |

## Behaviors

### Connection and transport

1. **MCP stdio serving**  
   - **Description:** Process starts, advertises tools, accepts JSON-RPC over stdin/stdout.  
   - **Preconditions:** Python ≥3.10; `mcp[cli]` installed; valid operator config resolvable.  
   - **Postconditions:** `mcp.run(transport="stdio")` blocks until parent process closes stdio.  
   - **Error conditions:** Missing `sliver-py` → exit code 1 with stderr message before MCP handshake.

2. **Lazy gRPC connect with health probe**  
   - **Description:** `_get_client()` returns a connected `SliverClient`, probing gRPC channel state and `version()` RPC (5s timeout).  
   - **Preconditions:** `SLIVER_CONFIG` or default `~/.sliver-client/configs/*.cfg` exists.  
   - **Postconditions:** `_client` singleton set; subsequent calls reuse client if channel is READY/IDLE and `version()` succeeds.  
   - **Error conditions:** `FileNotFoundError` for missing config; gRPC errors surfaced to caller tools as `ToolResponse` errors with reconnect hints.

3. **Force reconnect**  
   - **Description:** `sliver_reconnect` clears `_client` under `_client_lock` and establishes a new connection.  
   - **Preconditions:** Same as (2).  
   - **Postconditions:** New client passes `version()`; JSON `{status: "reconnected", version: "..."}`.  
   - **Error conditions:** Returns `_format_tool_error` with config/teamserver hints.

4. **Session interact with single retry**  
   - **Description:** `_interact(session_id)` calls `interact_session`; on failure clears client and retries once.  
   - **Preconditions:** Valid active `session_id`.  
   - **Postconditions:** Interactive session handle returned to tool.  
   - **Error conditions:** `SessionNotFound` / gRPC errors → tool error envelope with `sliver_sessions` hint.

### Tool execution envelope

5. **Standardized tool handler wrapper**  
   - **Description:** Every `@mcp.tool()` function is wrapped by `@tool_handler` (decorator in `errors.py` or `tools/__init__.py`).  
   - **Preconditions:** Tool function is async; returns `str` (JSON).  
   - **Postconditions:** On success, return value is valid JSON matching `ToolResponse` with `status: "ok"`. On exception, return `_format_tool_error(tool_name, exc, ...)` without raising through MCP stack. Invocation appended to access audit log (tool name, timestamp, session_id if param present, outcome).  
   - **Error conditions:** Uncaught exceptions never crash the server process.

6. **OPSEC pre-flight for high-risk tools**  
   - **Description:** Before configured tools run, `_opsec_preflight(session_id, tool_name)` scans process list via `_opsec_scan_session`.  
   - **Preconditions:** `SLIVER_OPSEC_MODE` ∈ `{warn, block, silent}`; `edr_processes.json` loaded.  
   - **Postconditions:** `silent` → no message; safe → proceed; `warn` + EDR → warning string prepended to result but execution continues; `block` + EDR → return blocked message, no RPC side effects.  
   - **Error conditions:** Scan exception currently yields `safe: True` (fail-open) — **must be addressed in security spec**; document as known brownfield behavior until changed.

### State database

7. **Lazy DB init with WAL**  
   - **Description:** First state access opens SQLite at `SLIVER_STATE_DB`, enables `PRAGMA journal_mode=WAL`, creates tables if absent.  
   - **Preconditions:** Writable directory for DB path.  
   - **Postconditions:** Schema for targets, credentials, access_log, findings, pivot_paths, attack_techniques **(new)**.  
   - **Error conditions:** Disk full / permission denied → `ToolResponse` error, no partial schema.

8. **Async-safe state access**  
   - **Description:** All DB operations acquire `asyncio.Lock` (`_state_lock` in `state/db.py`); sync sqlite3 calls run in `asyncio.to_thread()` to avoid blocking the event loop.  
   - **Preconditions:** Lock initialized at module load.  
   - **Postconditions:** Concurrent tool calls serialize DB writes; readers see committed WAL snapshots.  
   - **Error conditions:** Lock timeout (if configured) → error envelope `STATE_BUSY`.

9. **Auto target registration**  
   - **Description:** `sliver_sessions(auto_register=True)` and `sliver_state_auto_discover` upsert targets and access_log from live session metadata.  
   - **Preconditions:** Active sessions on teamserver.  
   - **Postconditions:** Targets merged by hostname; access events logged.  
   - **Error conditions:** Per-session errors collected in result array without aborting entire batch.

### Implant and C2 operations (representative)

10. **Implant generation with protobuf wire fix**  
    - **Description:** `sliver_generate` builds `GenerateReq` using raw wire-format field numbers compatible with Sliver 1.7.3+ (`utils.py` helpers).  
    - **Preconditions:** Connected client; valid GOOS/GOARCH/format/C2 URLs.  
    - **Postconditions:** Implant artifact returned or saved per Sliver API.  
    - **Error conditions:** gRPC `InvalidArgument` → error envelope with format hints.

11. **Remote command execution**  
    - **Description:** `sliver_execute` runs `session.execute(exe, args, output=True)` via `_interact`.  
    - **Preconditions:** Valid `session_id`; implant supports execution.  
    - **Postconditions:** Combined stdout/stderr in `ToolResponse.data.output`.  
    - **Error conditions:** Missing session, timeout, access denied → structured error with hints.

12. **Playbook compound execution**  
    - **Description:** Playbook tools run ordered `_exec_on_session` / `_exec_quiet` steps, parse output, write findings/state, return summary + raw sections.  
    - **Preconditions:** Valid session; OPSEC scan embedded where specified (initial recon).  
    - **Postconditions:** State DB updated; JSON summary with `next_steps`.  
    - **Error conditions:** Individual step failure captured in `results` dict without failing entire playbook unless connection lost.

### Planned behaviors **(new tools)**

13. **Beacon task interaction** — `sliver_beacon_tasks`, `sliver_interact_beacon`: list/submit beacon tasks via gRPC; postconditions include task ID in response.  
14. **BOF execution** — `sliver_execute_bof`: upload/execute Beacon Object File with session context; OPSEC pre-flight required.  
15. **ATT&CK coverage** — `sliver_attack_coverage`: map logged tools/findings to ATT&CK techniques stored in `AttackTechnique` table.  
16. **Orchestration** — `sliver_multi_exec`: run command on multiple session IDs sequentially; `sliver_pivot_chain`: document/execute staged pivot; `sliver_session_select`: rank sessions by hostname/privilege/OPSEC safety.  
17. **Reporting** — `sliver_generate_report`, `sliver_engagement_timeline`: export state DB + access log into markdown/JSON timeline for deliverables.

## ToolResponse envelope

All MCP tools return a **JSON string** (not raw prose). The canonical shape is defined here for SDK extraction:

**Success:**

```json
{
  "status": "ok",
  "tool": "sliver_execute",
  "data": { }
}
```

- `data` holds tool-specific payload (session lists, command output, summaries).
- Legacy tools that return unstructured JSON may nest prior fields under `data` during migration.

**Error** (via `_format_tool_error`):

```json
{
  "status": "error",
  "tool": "sliver_execute",
  "error_type": "GrpcError",
  "message": "human-readable detail",
  "hints": ["Run sliver_sessions to verify..."],
  "session_id": "optional-uuid",
  "context": "optional-operation-context"
}
```

**OPSEC warn/block** (may prefix or short-circuit):

```json
{
  "status": "blocked",
  "tool": "sliver_execute_shellcode",
  "opsec": { "detected": [{"product": "...", "process": "..."}], "mode": "block" }
}
```

## Edge Cases

1. **Stale gRPC channel after teamserver restart:** `_get_client()` detects non-READY/IDLE state or failed `version()` probe and reconnects transparently; `_interact` retries once after forced reconnect.
2. **Empty session list:** `sliver_sessions` returns `{status: "ok", sessions: [], count: 0}` without error.
3. **Duplicate hostname in state DB:** `_state_upsert_target` updates existing row (COALESCE merge on ip/os/domain) rather than inserting duplicates.
4. **Missing `edr_processes.json`:** OPSEC scan uses empty signatures; all sessions reported safe; high-risk list empty.
5. **Concurrent state writes from playbook + auto_register:** Serialized by `_state_lock`; last committed write wins per hostname upsert semantics.
6. **sliver-py/protobuf field mismatch:** Generate path uses wire-format builder only for `GenerateReq`; other RPCs use sliver-py as-is with documented version pin (`>=0.0.19`).
7. **WSL vs native Python paths:** `SLIVER_PROJECT_ROOT` and `SLIVER_CONFIG` must be set explicitly in MCP client env when auto-detection fails across filesystem boundaries.
8. **Beacon-only engagement (no interactive sessions):** Orchestration and execution tools return error hints directing operator to `sliver_interact_beacon` **(new)** or wait for session promotion.
9. **Quoted arguments in remote execution:** `_exec_quiet` must not split args on whitespace only — spec requires argv list or shell-safe quoting (brownfield bug; fix during casting).
10. **Large file download/upload:** Tools stream or chunk per Sliver API limits; timeout surfaced in error envelope.

## Failure Modes

| Scenario | Expected behavior |
|----------|-------------------|
| Teamserver unreachable | `_get_client()` raises; tools return `status: "error"` with gRPC/connect hints; no process crash |
| Invalid / expired session ID | gRPC/session error; hint to run `sliver_sessions` |
| OPSEC scan failure (RPC error) | Current: fail-open (`safe: true`); Target: configurable fail-closed per `docs/security.md` |
| SQLite locked / busy | Retry with backoff under `_state_lock`; after max retries return `STATE_BUSY` error |
| Subprocess timeout (`_run_cmd`) | Returncode -1; stderr message `Command timed out after Ns` in tool data |
| Disk full on evidence export | `sliver_collect_evidence` fails with explicit path in error context |
| Invalid user input (IP, registry path) | Validators in SDK reject before RPC; return `ValidationError` in envelope |
| MCP client disconnect | Server stdin closes; `main()` exits cleanly |
| Partial playbook failure | Per-step errors in `results`; summary flags failed steps |
| Missing implant privilege | Permission denied message + hint for token/privilege escalation tools |

## Non-Functional Requirements

### Response contract

- **NFR-1:** Every tool return value MUST be parseable JSON with a top-level `status` field (`ok`, `error`, or `blocked`).
- **NFR-2:** Every tool MUST be wrapped in `@tool_handler` for consistent exception handling and audit logging (no bare `@mcp.tool()` without wrapper after modularization).
- **NFR-3:** Error responses MUST include `tool` and `message`; SHOULD include `hints[]` with actionable next steps.

### Reliability

- **NFR-4:** gRPC connection MUST auto-reconnect when channel state is not READY/IDLE or `version()` fails within 5 seconds.
- **NFR-5:** `_interact` MUST retry exactly once after forced reconnect on first failure.
- **NFR-6:** State DB MUST use WAL journal mode and `asyncio.Lock` (or equivalent) for all concurrent access.

### Observability and audit

- **NFR-7:** Every tool invocation MUST append a row to `access_log` or a dedicated `tool_audit` table with: UTC timestamp, tool name, session_id (if any), outcome (`ok`/`error`/`blocked`), duration_ms.
- **NFR-8:** Playbooks and high-risk tools SHOULD log findings to state DB when severity ≥ medium.

### Performance

- **NFR-9:** Connection probe (`version()`) timeout ≤ 5s.
- **NFR-10:** Default subprocess timeout for evasion compile steps ≤ 300s (configurable per call).
- **NFR-11:** State DB operations SHOULD complete &lt; 100ms for single-row reads under normal load.

### Security and compliance

- **NFR-12:** For authorized testing only; README and tool descriptions MUST state authorization requirement.
- **NFR-13:** No hardcoded C2 URLs or teamserver addresses in source (brownfield: remove migrate fallback IP during casting).
- **NFR-14:** EDR signatures and high-risk tool lists MUST load from `edr_processes.json`, not hardcoded in Python.
- **NFR-15:** User-controlled strings passed to remote execution MUST be validated per `docs/security.md` before interpolation into commands.

### Maintainability

- **NFR-16:** No tool module file SHOULD exceed ~500 lines; shared logic lives in `client`, `utils`, `opsec`, or `state`.
- **NFR-17:** Each tool maps to one specification section and one SDK interface for mold traceability.
- **NFR-18:** Commits touching tools MUST reference spec section IDs (enforced by `scripts/spec-check` once specs exist).

### Packaging

- **NFR-19:** Installable package name `sliver-mcp`; import path `sliver_mcp`.
- **NFR-20:** Configuration exclusively via documented environment variables (see `config.py` table below).

| Variable | Purpose | Default |
|----------|---------|---------|
| `SLIVER_CONFIG` | Operator `.cfg` path | First `~/.sliver-client/configs/*.cfg` |
| `SLIVER_PROJECT_ROOT` | Repo root for assets | Auto-detect via `evasion/` directory |
| `SLIVER_EVASION_DIR` | Evasion scripts | `$PROJECT_ROOT/evasion` |
| `SLIVER_EVIDENCE_DIR` | Evidence output | `/tmp/sliver-evidence` |
| `SLIVER_STATE_DB` | SQLite path | `$PROJECT_ROOT/engagement_state.db` |
| `SLIVER_OPSEC_MODE` | `warn` \| `block` \| `silent` | `warn` |

## Interface Dependencies

**Depends on (consumer side):**

| Dependency | Version / contract | Usage |
|------------|-------------------|--------|
| **MCP FastMCP** | `mcp[cli]>=1.0.0` | stdio server, `@mcp.tool()` registration |
| **sliver-py** | `>=0.0.19` | `SliverClient`, `SliverClientConfig`, protobuf RPCs |
| **Sliver teamserver** | 1.7.3+ (tested) | gRPC/mTLS endpoint from operator config |
| **SQLite3** | stdlib | Engagement state |
| **Local JSON configs** | `edr_processes.json`, `cleanup_manifest.json` | OPSEC and cleanup |
| **Evasion toolchain** | Nim, shell scripts under `evasion/` | Pipeline tools (optional per engagement) |

**Provides (producer side):**

| Surface | Consumers | Contract |
|---------|-----------|----------|
| **MCP tool catalog** | AI agents via MCP | Stable tool names; JSON `ToolResponse` strings |
| **Engagement state export** | Reporting tools, operators | `sliver_state_export` full JSON snapshot |
| **CLI entry point** | `mcp.json`, Claude/Cursor configs | `sliver-mcp` → `sliver_mcp.server:main` |

**Future SDK interfaces** (Phase 2 — not yet implemented; see `docs/audit.md`):

- `C2Client` protocol wrapping `_get_client` / `_interact`
- `StateStore` protocol wrapping `state/db.py`
- `OpsecGuard` protocol wrapping `opsec.py`
- `ToolResponse` TypedDict / dataclass in `sdk/types.py`

Interface contracts per bounded context will be added under `docs/contracts/` as separate documents per `templates/interface-contract-template.md`.

## Open Questions

1. **OPSEC fail-open on scan errors:** Should `_opsec_scan_session` return `safe: false` or abort the tool when `ps()` fails? Blocks security spec and mold for OPSEC. Owner: security spec author.
2. **Credential encryption at rest:** Is SQLite encryption (SQLCipher) in scope for v1.1, or operator-managed disk encryption only? Blocks credential storage molds.
3. **Beacon task API surface:** Which sliver-py RPCs map to `sliver_beacon_tasks` / `sliver_interact_beacon` for the pinned server version? Blocks implants/sessions casting.
4. **`tool_audit` vs `access_log`:** Separate audit table or extend `access_log` with tool_name column? Blocks state schema migration.
5. **ATT&CK mapping source of truth:** Static JSON registry in repo vs MITRE STIX import? Blocks `attack_mapping.py` and `AttackTechnique` model.
6. **Migrate C2 fallback:** Confirm removal of hardcoded IP and required operator-provided C2 URL — APPROVE tier change. See `docs/audit.md` bug #1.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0-draft | 2026-05-28 | Codex Automata | Initial system architecture spec: package decomposition, bounded contexts, data flow, ToolResponse/handler contracts, NFRs, planned tools |
