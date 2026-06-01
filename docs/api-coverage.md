# Specification: Sliver MCP API Coverage

## Metadata

| Field | Value |
|-------|-------|
| Module name | API Coverage (Sliver MCP Server) |
| Bounded context | C2 Client / Implant Interaction |
| Version | 1.0.0-draft |
| Date | 2026-05-28 |
| Author | Codex Automata (brownfield onboarding) |
| Status | Draft |

## Overview

This specification defines the **target Sliver API surface** for the `sliver-mcp` MCP server: what is implemented today in `server.py` (82 MCP tools), what is intentionally excluded, and seven **planned capability expansions** (API-1 through API-7) required for parity with professional red team workflows. The MCP server is a Python gRPC bridge to [Sliver C2](https://github.com/BishopFox/sliver) via [sliver-py](https://github.com/sliverarmory/sliver-py) (`>=0.0.19`), targeting Sliver server **1.7.x** with protobuf wire-format workarounds where sliver-py field numbers diverge from the server (see existing `_build_generate_req` in `server.py`).

Downstream artifacts (SDK interfaces in `sdk/`, molds in `tests/`, castings in `src/`) must trace every new MCP tool and modified parameter to a section in this document before implementation.

## Scope

**Included:**

- MCP tool contracts for API-1 through API-7 (new tools and unified implant targeting).
- Mapping to sliver-py high-level APIs where they exist, and to `SliverRPC` gRPC stubs where sliver-py lacks wrappers (pattern established by `client._stub.Generate`).
- OPSEC preflight requirements for high-risk operations (aligned with `_opsec_preflight`, `edr_processes.json`, `SLIVER_OPSEC_MODE`).
- Complementary use of teamserver loot vs. local engagement SQLite (`SLIVER_STATE_DB`).
- Baseline inventory of the **current** 82-tool implementation.

**Excluded (explicit):**

- Metasploit integration (`msf`, `msf_remote`) unless added in a future spec revision.
- SSH lateral movement (`SSHStr` in Sliver CLI) — out of scope for API-5.
- WASM extensions (`ExecWasmExtension`) — separate from BOF/COFF and classic extensions.
- AI console, crackstation, traffic encoders, cursed browser tooling.
- Replacing the local engagement state database; loot API **complements** it only.
- Armory package manager UI (install/update) — only extension **load/list/call** on implants (API-7); armory catalog discovery may be a follow-on SDK extension.
- Automatic credential Pass-the-Hash in native PsExec (Sliver issue #557); credential validation uses state DB, not kernel auth primitives.

### Current baseline (`server.py`)

| Category | Count | Coverage notes |
|----------|-------|----------------|
| Connection / listeners | 9 | HTTP, HTTPS, DNS only; jobs, operators, reconnect |
| Sessions / beacons | 8 | Beacons: list, kill, rename only — **no interact, no tasks** |
| Implant generation | 3 | Limited `sliver_generate`; raw protobuf; no profiles/beacon/debug/canary |
| Remote execution | 12 | Session-only via `_interact`; assembly, shellcode, sideload, token ops |
| Filesystem | 8 | Session-only |
| Process / network | 3 | Session-only |
| Registry / services | 8 | Session-only; OPSEC on writes |
| Evasion pipeline | 4 | Local scripts + generate |
| Post-exploit / playbooks | 7 | `sliver_lateral_check` is **reachability assessment only** |
| Pivoting | 5 | SOCKS5, port forwards |
| State database | 11 | Local SQLite only — **no teamserver loot** |
| Cleanup / hosting | 5 | |
| **Total MCP tools** | **82** | Documented in `_TOOL_CATALOG` |

## Domain Model

- **SliverClient:** Connected gRPC client (`_get_client()`), teamserver scope (listeners, generate, loot, beacons list).
- **InteractiveSession:** Synchronous implant handle; commands return results immediately (`interact_session`).
- **InteractiveBeacon:** Asynchronous implant handle; commands enqueue **tasks** returning `asyncio.Future` (must be awaited).
- **ImplantRef (new, unified):** Value object `{ id: str, kind: "session" \| "beacon" }` used by refactored tools; resolved by `_resolve_implant()` (checks active sessions, then beacons).
- **BeaconTask:** Server-side task record (`client_pb2.BeaconTask` / `client_pb2.Task`); states include pending, completed, cancelled.
- **ImplantProfile:** Named `client_pb2.ImplantProfile` stored on teamserver (`save_implant_profile`, `implant_profiles`).
- **Loot:** Teamserver artifact (`client_pb2.Loot`, types `LOOT_FILE`, `LOOT_CREDENTIAL`) distinct from state DB rows.
- **Extension:** Implant-loaded module (`register_extension`, `list_extensions`, `call_extension`); BOF execution uses **coff-loader** extension pattern.
- **ListenerJob:** Teamserver job (`client_pb2.Job`) started by `start_*_listener` RPCs.

**Relationships:**

- One `SliverClient` → many sessions, beacons, jobs, loot entries, profiles.
- One `ImplantRef` → exactly one `InteractiveSession` **or** `InteractiveBeacon` at interaction time.
- Local state DB targets may reference `session_id` or `beacon_id` interchangeably once unified targeting lands.

## Behaviors

### API-1: Beacon Interaction

#### 1.1 `sliver_interact_beacon`

- **Description:** Establish an `InteractiveBeacon` handle for a beacon ID and return metadata confirming interaction readiness (hostname, interval, jitter, pending task count if available). Does not execute implant commands; prepares the handle for subsequent unified tools.
- **Preconditions:**
  - gRPC connection active (`_get_client()` succeeds).
  - `beacon_id` exists in `client.beacons()`.
- **Postconditions:**
  - MCP returns JSON with `status: "ok"`, `beacon_id`, and beacon summary fields mirroring `sliver_beacons` output.
  - Internal optional cache: `ImplantRef(beacon_id, "beacon")` may be registered for subsequent calls in the same process (implementation detail; not required for mold).
- **Error conditions:**
  - Unknown `beacon_id` → structured error, hint to run `sliver_beacons`.
  - gRPC failure / stale channel → `sliver_reconnect` hint.
- **OPSEC considerations:** Listing/interacting is low risk; no preflight required.
- **sliver-py API mapping:**
  - `await client.interact_beacon(beacon_id)` → `InteractiveBeacon`
  - `await client.beacon_by_id(beacon_id)` for validation

#### 1.2 `sliver_beacon_tasks`

- **Description:** List pending and completed beacon tasks with task ID, command type, state, and timestamps where available.
- **Preconditions:**
  - Valid `beacon_id`.
  - gRPC connection active.
- **Postconditions:**
  - JSON array of normalized task objects: `{ task_id, beacon_id, description, state, created_at?, completed_at? }`.
  - Empty list if beacon has no tasks (not an error).
- **Error conditions:**
  - Unknown beacon → error with hint.
  - Timeout on gRPC → fail with retry/reconnect message.
- **OPSEC considerations:** Read-only; no preflight.
- **sliver-py API mapping:**
  - `await client.beacon_tasks(beacon_id)` → `List[client_pb2.Task]`
  - Optional detail: `await client.beacon_task_content(task_id)` for result payloads (future tool; not required for list)

#### 1.3 Unified `session_id` / `beacon_id` interface (refactor)

- **Description:** All implant-scoped tools that today accept only `session_id` accept a unified target parameter (SDK name: `implant_id`) and optional `implant_kind: "session" | "beacon" | "auto"` (default `auto`). When `auto`, resolver queries `client.sessions()` then `client.beacons()` by ID.
- **Preconditions:**
  - Target implant exists and is interactable.
  - Beacon-backed tools must await task Futures (beacon) or handle sync responses (session) transparently to the MCP caller where feasible (see edge cases).
- **Postconditions:**
  - Session path: behavior unchanged vs. current `_interact(session_id)`.
  - Beacon path: commands that support beacons enqueue tasks; MCP waits up to configurable timeout (default: beacon interval + jitter + 60s) and returns decoded output.
  - Response envelope includes `implant_kind` so agents know latency expectations.
- **Error conditions:**
  - ID not found in either list.
  - Command not supported on beacons (e.g., real-time shell) → explicit `unsupported_on_beacon` error.
  - Task timeout on beacon → error with `task_id` if known.
- **OPSEC considerations:** Existing `_opsec_preflight` runs against resolved implant; extend `_opsec_scan_session` to `_opsec_scan_implant` using beacon `ps` task when kind is beacon.
- **sliver-py API mapping:**
  - Sessions: `await client.interact_session(session_id)` → `InteractiveSession`
  - Beacons: `await client.interact_beacon(beacon_id)` → `InteractiveBeacon`
  - Shared commands via `BaseInteractiveCommands` on both types (`execute`, `ls`, `ps`, etc.)

**Affected tools (minimum set for API-1):** All entries in `_TOOL_CATALOG` under `remote_execution`, `filesystem`, `process_network`, `registry_services`, `pivoting`, and playbooks that currently take `session_id`.

---

### API-2: Missing Listener Types

#### 2.1 `sliver_start_mtls_listener`

- **Description:** Start a mutual-TLS C2 listener on the teamserver.
- **Preconditions:**
  - Operator config authorized for listener management.
  - `host` valid bind address; `port` available (1–65535).
- **Postconditions:**
  - Returns `{ status: "started", job_id, lhost, lport, protocol: "mtls" }`.
  - Job visible via `sliver_jobs`.
- **Error conditions:**
  - Port in use → gRPC error surfaced with job conflict hint.
  - Permission denied on low ports (<1024) on hardened hosts.
- **OPSEC considerations:** mTLS is preferred for lab OPSEC; document listener exposure in engagement notes. No implant preflight.
- **sliver-py API mapping:**
  - `await client.start_mtls_listener(host, port, persistent=False)`

#### 2.2 `sliver_start_tcp_listener`

- **Description:** Start a **TCP stager listener** on the teamserver (Sliver `tcp` stage listener). Delivers staged payloads to connecting implants; distinct from session-scoped TCP **pivot** listeners (`PivotStartListener`).
- **Preconditions:**
  - `host`, `port` valid.
  - `stager_data` (bytes, base64, or path) provided **unless** MCP first generates stage via `generate_msf_stager` / profile (optional parameter).
- **Postconditions:**
  - Listener job started; `job_id` returned.
- **Error conditions:**
  - Missing stager payload when required by server.
  - Invalid bind address.
- **OPSEC considerations:** Stager listeners are high visibility; LOG tier minimum; recommend mTLS/HTTPS for production engagements.
- **sliver-py API mapping:**
  - `await client.start_tcp_stager_listener(host, port, data: bytes)`
  - **Note:** There is no `start_tcp_listener` in sliver-py 0.0.19; only `StartTCPStagerListener` gRPC. Session pivot TCP uses `SliverRPC.PivotStartListener` with `PivotType.TCP` on an **interactive session** — out of scope for this teamserver listener tool unless renamed in a future revision.

#### 2.3 `sliver_start_wg_listener`

- **Description:** Start a WireGuard C2 listener.
- **Preconditions:**
  - `host`, `port` (UDP), `key_port` valid.
  - WG keys/cfg may be auto-generated server-side.
- **Postconditions:**
  - Returns `{ status: "started", job_id, host, port, n_port, key_port }` per server response (`client_pb2.WGListener`).
- **Error conditions:**
  - WG subsystem unavailable on server build.
  - Port conflicts.
- **OPSEC considerations:** WG profile distinct from HTTP(S); document peer IPs and keys in evidence handling (sensitive).
- **sliver-py API mapping:**
  - `await client.start_wg_listener(tun_ip=None, host=host, port=port, n_port=port, key_port=key_port, persistent=False)`
  - Align parameter names: MCP `key_port` → sliver-py `key_port`; document `n_port` default (8888) in tool docstring.

---

### API-3: BOF/COFF Loader

#### 3.1 `sliver_execute_bof`

- **Description:** Load and execute a Beacon Object File (BOF) or COFF object on a Windows session via the **coff-loader** extension pattern: register extension if absent, pack BOF + arguments, call `LoadAndRun`.
- **Preconditions:**
  - Target is a **Windows session** (beacon support optional phase-2; initial impl session-only).
  - `bof_path` readable on operator machine; file size ≤ SDK max upload (recommend 1 MB default cap).
  - `entry_point` defaults to `"go"` (coff-loader convention).
  - `args` encoded per Beacon Object File argument packing (SDK helper required).
  - **OPSEC preflight** passes (`_opsec_preflight` with tool name `sliver_execute_bof`).
- **Postconditions:**
  - Returns `{ status: "ok", output: str, extension: "coff-loader" }` from `CallExtension` decoded output.
  - coff-loader registered on implant if not in `list_extensions()`.
- **Error conditions:**
  - Non-Windows target.
  - Missing coff-loader DLL on operator path (`SLIVER_COFF_LOADER_PATH` env).
  - EDR block mode → `[OPSEC BLOCKED]` (no execution).
  - Extension call failure → surface `Response.Err` from protobuf.
- **OPSEC considerations:**
  - **Critical:** Preferred execution path when EDR present (`sliver_opsec_check` already recommends BOF).
  - Add `sliver_execute_bof` to `high_risk_tools` in `edr_processes.json` with preflight.
  - Avoid default service names / disk artifacts; BOF is in-memory after load.
- **sliver-py API mapping:**
  - `await session.list_extensions()` → check `Names` for `coff-loader`
  - `await session.register_extension("coff-loader", coff_loader_bytes, session.os, init=None)`
  - Pack args: SDK `BeaconPack` equivalent (port from community pattern / PR #39)
  - `await session.call_extension("coff-loader", "LoadAndRun", packed_buffer)` → `sliver_pb2.CallExtension`
  - **Gap:** sliver-py 0.0.19 installed package omits `call_extension` / `register_extension` on `BaseInteractiveCommands` but gRPC stubs exist (`RegisterExtension`, `CallExtension`, `ListExtensions`). Casting may use `session._stub.*` with `session._request()` until sliver-py release includes wrappers.

---

### API-4: Implant Generation Enhancements

#### 4.1 Profile support

- **Description:**
  - `sliver_save_implant_profile(name, config_json)` — save profile to teamserver.
  - `sliver_implant_profiles()` — list profiles (wraps / extends catalog).
  - `sliver_delete_implant_profile(name)` — remove profile.
  - `sliver_generate` accepts `profile_name` to generate from stored `ImplantConfig`.
- **Preconditions:**
  - Valid `client_pb2.ImplantProfile` / `ImplantConfig` fields.
  - Profile name unique on save.
- **Postconditions:**
  - Profile persisted server-side; generate returns implant bytes consistent with profile.
- **Error conditions:**
  - Unknown profile name on generate.
  - Invalid config JSON → validation error before RPC.
- **OPSEC considerations:** Profiles may embed canary domains and debug flags — warn when `Debug=true`.
- **sliver-py API mapping:**
  - `await client.implant_profiles()`
  - `await client.save_implant_profile(profile)`
  - `await client.delete_implant_profile(profile_name)`
  - `await client.generate_implant(config)` or `stub.Generate` with profile config

#### 4.2 Beacon vs session mode toggle

- **Description:** `sliver_generate` and profile save accept `is_beacon: bool`, `beacon_interval: int` (seconds), `beacon_jitter: int` (seconds).
- **Preconditions:** Interval ≥ 1; jitter ≤ interval.
- **Postconditions:** `ImplantConfig.IsBeacon` set; beacon implants register via beacon pipeline.
- **Error conditions:** Invalid interval/jitter combination.
- **OPSEC considerations:** Beacons reduce network noise; slower operator feedback.
- **sliver-py API mapping:** `ImplantConfig.IsBeacon`, `BeaconInterval`, `BeaconJitter` in `client_pb2.ImplantConfig`; wire-format via extended `_build_generate_req` or `generate_implant(config)`.

#### 4.3 Canary domain configuration

- **Description:** Accept `canary_domains: list[str]` on generate/profile; list triggered canaries via `sliver_canaries()` (new read tool).
- **Preconditions:** Domains non-empty strings when provided.
- **Postconditions:** Config includes `CanaryDomains`; DNS canary events queryable.
- **Error conditions:** Server rejects malformed domain.
- **OPSEC considerations:** Canaries detect blue-team DNS monitoring; LOG when enabled.
- **sliver-py API mapping:**
  - `ImplantConfig.CanaryDomains`
  - `await client.canaries()` → `List[client_pb2.DNSCanary]`

#### 4.4 Debug build flag

- **Description:** `debug: bool` on generate/profile (default `false`). When `true`, implant includes debug symbols/logging (lab only).
- **Preconditions:** Operator acknowledges lab use (warn in response when `debug=true`).
- **Postconditions:** `ImplantConfig.Debug = true`.
- **Error conditions:** None beyond generate failure.
- **OPSEC considerations:** **APPROVE** tier in production engagements; block when `SLIVER_OPSEC_MODE=block` and debug requested.
- **sliver-py API mapping:** `ImplantConfig.Debug`; extend protobuf builder field **12+** per server 1.7.3 field map (verify against server `client.proto` during SDK design).

---

### API-5: Lateral Movement Execution

#### 5.1 `sliver_psexec`

- **Description:** Remote service-based lateral movement mirroring Sliver CLI `psexec`: upload service binary to `\\target\ADMIN$\...`, start remote service, remove service. Parameters: `session_id` (source), `target` (hostname), `service_name`, `exe_path` (local custom binary) **or** `profile_name` (generate from profile).
- **Preconditions:**
  - Source is Windows **session** with rights to reach admin share on `target`.
  - Either `exe_path` exists locally OR `profile_name` resolves via `implant_profiles()`.
  - **OPSEC preflight** required.
  - **Credential validation:** at least one credential in state DB matching target domain OR explicit operator confirmation when `SLIVER_OPSEC_MODE=warn` (SDK: `CredentialValidator.validate_for_target(target)`).
  - Default service name must not be `Sliver` / `Sliver implant` in production (warn or reject per SDK policy).
- **Postconditions:**
  - Service binary uploaded to UNC path; service started then removed.
  - JSON includes `{ uploaded_path, service_name, target, new_session_hint }` if server emits session-connected event (best-effort poll `sliver_sessions`).
- **Error conditions:**
  - Upload RPC failure (AV quarantine, access denied).
  - `StartService` / `RemoveService` error in protobuf `Response.Err`.
  - Missing profile when `exe_path` omitted.
  - OPSEC block / credential validation failure.
- **OPSEC considerations:**
  - **Critical:** Sigma-detectable default service name; enforce custom `service_name`.
  - 5-second post-upload delay (Sliver client behavior) before start — replicate to avoid Defender race.
  - High forensic footprint (7045 service install events).
- **sliver-py API mapping (composite, no single RPC):**
  1. `profiles = await client.implant_profiles()` + server generate binary if `profile_name` (same as Sliver `GetSliverBinary` / `generate_implant`)
  2. `gzip` encode payload per Sliver encoder convention
  3. `await session.upload(unc_path, upload_gzip)` — `sliverpb.UploadReq` with `Encoder="gzip"`
  4. `await asyncio.sleep(5)`
  5. `await session.start_service(service_name, service_desc, binary_path, target, arguments="")`
  6. `await session.remove_service(service_name, target)`

#### 5.2 `sliver_wmi_exec`

- **Description:** Execute a command on a remote host via WMI. Native Sliver has **no dedicated WMI RPC**; implementation uses **SharpWMI** (or equivalent) armory extension through `call_extension`, or documents failure with install guidance.
- **Preconditions:**
  - Windows session source.
  - `target` hostname resolvable; `command` non-empty.
  - Extension `sharpwmi` (or configured alias) available: either pre-loaded on implant via `sliver_load_extension` or MCP bundles extension path from `SLIVER_ARMORY_EXTENSIONS_DIR`.
  - **OPSEC preflight** and **credential validation** (same as 5.1).
- **Postconditions:**
  - Returns WMI command output text in JSON.
- **Error conditions:**
  - Extension not loaded → actionable error referencing armory install.
  - Auth failure → credential hint from state DB.
  - OPSEC block.
- **OPSEC considerations:** WMI process creation is high visibility (Defender ASR, 4688). Prefer BOF/API-3 where possible.
- **sliver-py API mapping:**
  - Primary: `await session.call_extension("sharpwmi", "<export>", packed_args)` (export name from extension manifest during SDK design)
  - Fallback: not available via raw gRPC without extension

---

### API-6: Loot API Integration

#### 6.1 `sliver_loot_add`

- **Description:** Store loot on the Sliver teamserver (files, credentials) with metadata; complements `sliver_state_add_cred` / findings in SQLite.
- **Preconditions:**
  - `loot_type` ∈ `{ "file", "credential" }` mapped to `client_pb2.LootType`.
  - `name` non-empty; `data` bytes or UTF-8 string (for credentials).
  - Optional `host_uuid` from session/beacon for provenance.
- **Postconditions:**
  - Returns `{ loot_id, name, type, size_bytes }` without echoing secret material in logs.
  - Local state DB MAY record cross-reference `{ loot_id, name }` via optional `sync_state_db: bool` (default false).
- **Error conditions:**
  - Invalid type enum.
  - Server storage failure.
  - Payload exceeds gRPC max message size.
- **OPSEC considerations:** Loot at rest on teamserver; encrypt teamserver disk; never commit loot to git. Credentials still duplicated in SQLite if operator enables sync — warn on dual storage.
- **sliver-py API mapping:**
  - Build `client_pb2.Loot` with `File.Data`, `Type`, `Name`
  - `await client._stub.LootAdd(loot, timeout=60)` (wrapper to add in SDK: `SliverClient.loot_add`)
  - Map `loot_type` string → `LootType.LOOT_FILE` / `LOOT_CREDENTIAL`

#### 6.2 `sliver_loot_list`

- **Description:** List all loot metadata from teamserver (no bulk file bytes by default).
- **Preconditions:** gRPC connected.
- **Postconditions:** JSON list `{ loot_id, name, type, size, host_uuid?, file_type? }[]`.
- **Error conditions:** gRPC failure; empty list is success.
- **OPSEC considerations:** Listing may expose credential names; restrict tool to authorized engagements.
- **sliver-py API mapping:**
  - `await client._stub.LootAll(common_pb2.Empty())` → `client_pb2.AllLoot`
  - Optional fetch: `LootContent` for single ID (future tool)

---

### API-7: Extension/Alias Support

#### 7.1 `sliver_load_extension`

- **Description:** Load/register a Sliver extension binary on the target implant session (DLL/shared lib/Wasm excluded here — native **extensions** only per Sliver extension model).
- **Preconditions:**
  - `extension_path` readable locally; matches target `GOOS`/`arch`.
  - `session_id` or unified `implant_id` (session recommended; beacon support follows API-1).
  - `name` optional (defaults to file basename).
- **Postconditions:**
  - `register_extension` succeeds; extension appears in `list_extensions`.
- **Error conditions:**
  - Architecture mismatch.
  - Already loaded → idempotent success or explicit `already_loaded`.
  - Registration RPC error.
- **OPSEC considerations:** Loading unsigned DLL into implant is high risk; OPSEC preflight for non-armory extensions.
- **sliver-py API mapping:**
  - `data = Path(extension_path).read_bytes()`
  - `await session.register_extension(name, data, session.os, init=None)` or `stub.RegisterExtension`

#### 7.2 `sliver_list_extensions`

- **Description:** List extensions **loaded on the implant** via RPC. Separate optional future tool may list **armory** manifests from operator filesystem.
- **Preconditions:** Active interactable implant.
- **Postconditions:** `{ names: string[] }` from `ListExtensions`.
- **Error conditions:** Implant not interactable.
- **OPSEC considerations:** Low risk.
- **sliver-py API mapping:**
  - `await session.list_extensions()` → `sliver_pb2.ListExtensions.Names`
  - Armory catalog: **not** a teamserver RPC — document as SDK extension reading armory JSON paths

#### 7.3 `sliver_call_extension`

- **Description:** Invoke an export on a loaded extension with opaque byte args (hex/base64 input in MCP).
- **Preconditions:**
  - Extension `name` loaded on implant.
  - `function` export exists (e.g., coff-loader `LoadAndRun`).
  - OPSEC preflight for known high-risk extensions (configurable list).
- **Postconditions:** Decoded `output` text in JSON; raw bytes available as base64 if binary.
- **Error conditions:**
  - Extension not found → load hint.
  - `CallExtension` error in `Response.Err`.
- **OPSEC considerations:** Same tier as execute-assembly; extension-specific fingerprints.
- **sliver-py API mapping:**
  - `await session.call_extension(name, function, ext_args: bytes)`

---

## Edge Cases

1. **Beacon task latency:** Unified tools on beacons must await Futures; MCP default timeout should exceed `interval + jitter` to avoid false failures on slow beacons.
2. **ID collision:** Session ID and beacon ID namespaces are distinct UUIDs; `auto` resolution is safe. If both lists return empty, fail fast.
3. **Stale implant:** Mid-task beacon disconnect → return `implant_lost` with last known `task_id`.
4. **sliver-py wrapper gaps:** When high-level methods are missing (extensions, loot, BOF), casting uses `_stub` with `_request()` — molds must not assume sliver-py version exposes wrappers until SDK pins version.
5. **Protobuf field drift (1.7.3):** Generate/profile/loot may require raw wire builders like `_build_generate_req`; molds should allow golden-byte tests against recorded server version.
6. **PsExec without profile or exe:** Must error; no implicit default implant.
7. **WMI without SharpWMI:** Clear error with armory install instructions; do not silently fall back to `cmd.exe` over SMB without spec update.
8. **TCP listener naming:** Operators may confuse TCP stager with TCP pivot; tool docstrings must state stager semantics (API-2.2).
9. **OPSEC scan on beacons:** `ps` via beacon returns Future; preflight must await before high-risk execution.
10. **Large BOF / loot payloads:** Enforce size limits below gRPC 2 GB cap; chunking out of scope.

## Failure Modes

| Scenario | Expected behavior |
|----------|-------------------|
| gRPC channel stale | `_get_client()` reconnect; retry interact once (existing pattern). |
| `SLIVER_OPSEC_MODE=block` + high-risk tool | Return `[OPSEC BLOCKED]` string; no RPC side effects. |
| OPSEC scan exception (today: fail-open) | **Target:** fail-closed for API-3/5; document migration in security spec. |
| sliver-py missing method | Use `_stub` RPC; if RPC missing, `capability_unavailable` with server version. |
| Listener port conflict | Surface server error; suggest `sliver_jobs` / `sliver_stop_job`. |
| Beacon task cancelled | `sliver_beacon_tasks` shows cancelled; unified tools report cancellation. |
| Loot add without host UUID | Server accepts with nil host; warn in response. |
| Extension pack mismatch | Validate PE/ELF arch before upload; client-side error. |
| Credential validator finds no creds | `sliver_psexec` / `sliver_wmi_exec` reject unless explicit override flag (APPROVE tier). |
| Generate debug in block mode | Reject before RPC. |

## Non-Functional Requirements

- **Performance:** Beacon unified calls may take up to 5 minutes (configurable `SLIVER_BEACON_TASK_TIMEOUT`); session calls remain ≤ 60s default gRPC timeout unless overridden.
- **Availability:** MCP server remains stateless regarding implants; reconnect on channel failure without requiring MCP restart.
- **Security:**
  - Authorized use only; tools assume valid operator `.cfg`.
  - No secrets in MCP responses (credentials, loot contents redacted by default).
  - Input validation on `target`, paths, hostnames (no PowerShell injection — fixes audit finding on `sliver_lateral_check`).
  - High-risk tools require OPSEC preflight per `edr_processes.json`.
  - PsExec service names must be customizable; reject defaults in `block` mode.
- **Compatibility:** Sliver server 1.7.x + sliver-py 0.0.19 minimum; document tested matrix in SDK.
- **Traceability:** Each new tool maps to API-1..7 section IDs for commit-lint and spec-check gates.

## Interface Dependencies

**Depends on (consumer side):**

- `SliverClient` / `SliverClientConfig` (sliver-py) — gRPC connectivity.
- `docs/security.md` (planned) — OPSEC modes, credential validation, input sanitization.
- `sdk/` constraint surface (planned):
  - `ImplantRef`, `BeaconPack`, `CredentialValidator`, `LootStore`, `ExtensionRegistry`
- `edr_processes.json` — high-risk tool registry.
- Environment: `SLIVER_CONFIG`, `SLIVER_OPSEC_MODE`, optional `SLIVER_COFF_LOADER_PATH`, `SLIVER_ARMORY_EXTENSIONS_DIR`, `SLIVER_BEACON_TASK_TIMEOUT`.

**Provides (producer side):**

- MCP tools API-1 through API-7 as extension of `_TOOL_CATALOG`.
- Unified implant targeting contract for all refactored session-scoped tools.
- Teamserver loot integration contract complementing local `engagement_state.db`.

**sliver-py coverage summary (0.0.19):**

| Capability | High-level API | Stub fallback |
|------------|--------------|---------------|
| Beacon interact | `interact_beacon` | — |
| Beacon tasks | `beacon_tasks` | `GetBeaconTasks` |
| mTLS listener | `start_mtls_listener` | — |
| TCP stager | `start_tcp_stager_listener` | `StartTCPStagerListener` |
| WG listener | `start_wg_listener` | — |
| Profiles | `implant_profiles`, `save_implant_profile` | `Generate` / `ImplantProfiles` |
| Loot | *missing* | `LootAdd`, `LootAll` |
| Extensions | *missing on session* | `RegisterExtension`, `ListExtensions`, `CallExtension` |
| PsExec workflow | `upload`, `start_service`, `remove_service` | `Upload`, `StartService`, `RemoveService` |
| WMI | *via extension* | `CallExtension` |

## Open Questions

1. **TCP listener semantics:** Confirm operators want `StartTCPStagerListener` vs. session `PivotStartListener` for tool name `sliver_start_tcp_listener`. *Blocks:* API-2.2 mold design.
2. **WMI export manifest:** SharpWMI packed argument format for `call_extension`. *Blocks:* API-5.2 casting.
3. **sliver-py version bump:** Target release that exposes `call_extension`, `loot_add` on `SliverClient`. *Blocks:* SDK dependency pin.
4. **Beacon-unified scope:** Which tools are in v1 (execute/ls/ps only) vs. full parity? *Blocks:* API-1 task sizing.
5. **Armory catalog listing:** Whether `sliver_list_extensions` includes filesystem armory or implant-only. *Blocks:* API-7.2 SDK interface.
6. **OPSEC fail-open remediation:** Align `_opsec_scan_session` with fail-closed for API-3/5. *Owner:* security spec.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0-draft | 2026-05-28 | Codex Automata | Initial API coverage spec: baseline 82 tools, API-1–API-7 planned capabilities, sliver-py/gRPC mappings |
