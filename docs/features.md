# Specification: Differentiating Features (Conference Tier)

<!--
Primary engineering artifact for ATT&CK integration, multi-session orchestration, MCP resources,
engagement reporting, and smart playbooks. SDK interfaces and molds trace to behavior IDs
(FEAT-n.B-m). Resolve Open Questions before deriving tests for this version.
-->

## Metadata

| Field | Value |
|-------|-------|
| Module name | Differentiating Features |
| Bounded context | Engagement Intelligence (+ Orchestration, MCP Resources) |
| Version | 1.0.0-draft |
| Date | 2026-05-28 |
| Author | Codex Automata (brownfield onboarding) |
| Status | Draft |

## Overview

This specification defines the **conference-tier capabilities** that differentiate sliver-mcp from other Sliver MCP integrations: MITRE ATT&CK–aware operation logging and gap analysis, multi-session orchestration with pivot topology reasoning, MCP **resources** for live engagement context, structured engagement reporting for deliverables, and opinionated smart playbooks with an AI-facing “next action” advisor. These features sit on top of the existing engagement SQLite state database and gRPC implant tool surface described in `docs/architecture.md`. They exist so AI agents can reason about **coverage**, **topology**, and **engagement progress**—not merely invoke isolated RPCs—and so operators can produce DEF CON / Black Hat–quality narratives (ATT&CK matrix, timeline, pivot map) without manual spreadsheet work.

## Scope

**Included:**

- Static MITRE ATT&CK technique registry mapping every MCP tool (current ~79 + planned) to technique IDs and tactics
- Runtime logging of exercised techniques into `attack_techniques` with success/failure, session, and evidence references
- `sliver_attack_coverage` tool: exercised vs available techniques grouped by tactic
- `sliver_multi_exec`, `sliver_pivot_chain`, `sliver_session_select` orchestration tools
- MCP resources: `sliver://sessions`, `sliver://events`, `sliver://state/summary`, `sliver://attack-surface`
- `sliver_generate_report`, `sliver_engagement_timeline` reporting tools
- `sliver_playbook_ad_enum`, `sliver_playbook_network_sweep`, `sliver_suggest_next` smart playbooks / advisor
- Schema migrations and domain model extensions in `sliver_mcp/state/`
- Integration with `@tool_handler` audit logging and `ToolResponse` envelope (see architecture spec)

**Excluded (explicit):**

- MITRE ATT&CK Navigator layer file export (`.layer` JSON) — future spec unless added via Open Question resolution
- Real-time push notifications to MCP clients (resources refresh on **read** only; no SSE/WebSocket transport)
- Automated exploit selection or autonomous attack execution without operator authorization context
- STIX/TAXII live sync with MITRE (static registry only in v1.0; see Open Questions)
- Replacement of Sliver teamserver event bus — events resource **mirrors** teamserver events available via sliver-py, not a new C2 channel
- User-facing web UI or PDF report rendering (Markdown and JSON export only)
- Beacon task orchestration in `sliver_multi_exec` until beacon execution spec is approved (`docs/architecture.md` Open Question #3)

## Domain Model

### Existing entities (extended)

| Entity | Extension |
|--------|-----------|
| **Target** | Optional columns: `network_zone` (`internal` \| `dmz` \| `external` \| `unknown`), `edr_products` (JSON array of strings), `last_seen_session_id` |
| **AccessLog** | Optional columns: `tool_name`, `attack_technique_id`, `outcome` (`ok` \| `error` \| `blocked`), `duration_ms`, `details_json` — or parallel **EngagementAction** table (see FEAT-4) |
| **Finding** | Playbooks may set `attack_technique_id` in metadata JSON on insert |
| **PivotPath** | Populated by `sliver_pivot_chain` analysis (`status`: `planned` \| `validated` \| `active`) |

### New entities

| Entity | Identity | Key fields | Lifecycle |
|--------|----------|------------|-----------|
| **AttackTechniqueRecord** | `id` (integer PK) | `technique_id` (e.g. `T1055.012`), `tactic`, `name`, `tool_name`, `session_id`, `target_id` FK, `outcome` (`success` \| `failure` \| `blocked` \| `unknown`), `evidence`, `timestamp` UTC | Inserted on each mapped tool invocation or playbook step; immutable append-only |
| **TechniqueRegistryEntry** | `technique_id` + `tool_name` (static file) | `name`, `tactic`, `subtechnique_name`, `description`, `platforms[]` | Loaded at process start from `attack_registry.json`; versioned with spec |
| **TargetService** | `id` | `target_id` FK, `port`, `protocol`, `service_name`, `state` (`open` \| `filtered` \| `closed`), `banner`, `discovered_at` | Upserted by network sweep playbook |
| **EngagementMeta** | `key` (text PK) | `value` (JSON), `updated_at` | Stores engagement title, scope, objectives, start time |
| **OpsecIncident** | `id` | `session_id`, `incident_type` (`edr_detected` \| `blocked_tool` \| `noisy_command`), `severity`, `description`, `tool_name`, `timestamp` | Append-only; feeds report OPSEC section |
| **PlaybookRun** | `id` | `playbook_name`, `session_id`, `status` (`running` \| `completed` \| `partial` \| `failed`), `started_at`, `finished_at`, `summary_json` | One row per playbook invocation |

### Value objects

| Name | Fields | Validation |
|------|--------|------------|
| **AttackCoverageMatrix** | `tactics[]` → `{tactic, available[], exercised[], gap[]}` | Each technique ID must exist in registry |
| **SessionScore** | `session_id`, `score` (float 0–100), `rank`, `factors{}` | Used by `sliver_session_select` |
| **PivotHop** | `source_session_id`, `dest_target_ip`, `via_subnet`, `confidence` (`high` \| `medium` \| `low`) | Produced by pivot chain analysis |
| **RecommendedAction** | `priority` (int), `action` (tool name or playbook), `rationale`, `technique_ids[]`, `preconditions_met` (bool) | Returned by `sliver_suggest_next` |
| **ReportDocument** | `format`, `sections{}`, `generated_at`, `redaction_applied` (bool) | Markdown or JSON serializable |

### Relationships

- Target 1:N TargetService, AttackTechniqueRecord (optional FK)
- Target N:N PivotPath (unchanged)
- PlaybookRun 1:N AttackTechniqueRecord (via logged steps)
- TechniqueRegistryEntry (static) 1:N AttackTechniqueRecord (logical reference by `technique_id`)

### Static registry (`attack_registry.json`)

Repository-root JSON (or `sliver_mcp/data/attack_registry.json`) listing:

```json
{
  "version": "14.1",
  "mappings": [
    {
      "tool": "sliver_execute_assembly",
      "techniques": [
        { "id": "T1055.012", "name": "Process Hollowing", "tactic": "Defense Evasion" }
      ]
    }
  ]
}
```

**Normative example mappings** (non-exhaustive; full catalog MUST cover all tools in `_TOOL_CATALOG`):

| MCP tool | ATT&CK ID | Tactic |
|----------|-----------|--------|
| `sliver_execute_assembly` | T1055.012 | Defense Evasion |
| `sliver_get_system` | T1134.001 | Privilege Escalation |
| `sliver_execute` | T1059 | Execution |
| `sliver_discovery` | T1082, T1016, T1049 | Discovery |
| `sliver_registry_write` | T1112 | Defense Evasion |
| `sliver_sideload` | T1574.002 | Defense Evasion |
| `sliver_migrate` | T1055 | Defense Evasion |
| `sliver_process_dump` | T1003.001 | Credential Access |

Tools MAY map to multiple techniques (e.g. `sliver_discovery`). Playbook-internal steps MAY map to sub-techniques (e.g. Kerberoast → T1558.003).

## Behaviors

### FEAT-1: MITRE ATT&CK Integration

#### FEAT-1.B-1: Load technique registry at startup

- **Description:** On server init, load and validate `attack_registry.json`. Build in-memory map `tool_name → TechniqueRegistryEntry[]`.
- **Preconditions:** Registry file exists and parses as JSON; schema version field present.
- **Postconditions:** Invalid entries logged; server starts with empty map for broken file only if `SLIVER_ATTACK_REGISTRY_STRICT=false` (default `true` → fail fast on invalid registry).
- **Error conditions:** Missing file when strict mode → stderr error, exit code 1 before MCP handshake. Malformed JSON → same. Unknown tactic name → validation error at load.
- **Data model additions:** None (file-backed).
- **Agent experience:** Agent can call `sliver_help` / read spec knowing every tool has ATT&CK semantics.

#### FEAT-1.B-2: Log technique on tool invocation

- **Description:** After each successful or attempted mapped tool run, `@tool_handler` (or dedicated hook) inserts `AttackTechniqueRecord` row(s) for all techniques linked to that tool in the registry.
- **Preconditions:** Registry loaded; tool name appears in registry (unmapped tools log `technique_id: "UNMAPPED"` optionally, configurable).
- **Postconditions:** One row per technique ID per invocation with `session_id`, `outcome`, UTC `timestamp`, optional `target_id` resolved from session hostname via state DB.
- **Error conditions:** State DB write failure → tool result still returned; `data.attack_log_warning` set; no silent drop in strict audit mode (`SLIVER_ATTACK_LOG_REQUIRED=true`).
- **Data model additions:** Table `attack_techniques` (see §Domain Model).
- **Agent experience:** Engagement history becomes ATT&CK-grounded automatically; agent does not manually tag actions.

#### FEAT-1.B-3: `sliver_attack_coverage`

- **Description:** Returns `AttackCoverageMatrix` JSON: for each tactic in the engagement taxonomy (Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control), lists `available` (registry), `exercised` (distinct IDs in DB with ≥1 success), `attempted_failed`, and `gap` (available − exercised).
- **Preconditions:** Registry loaded; state DB readable.
- **Postconditions:** `ToolResponse.status == "ok"`; `data.coverage` contains per-tactic arrays and `summary` with counts (`total_available`, `total_exercised`, `coverage_percent`).
- **Error conditions:** Empty registry → error `ATTACK_REGISTRY_EMPTY`. DB error → `STATE_BUSY` per architecture spec.
- **Data model additions:** Read-only query over `attack_techniques` + registry.
- **Agent experience:** Agent answers “what ATT&CK gaps exist?” with structured JSON suitable for planning next steps.

**Example (given 3 tools exercised in Discovery only):**

```json
{
  "status": "ok",
  "tool": "sliver_attack_coverage",
  "data": {
    "coverage": {
      "Discovery": {
        "available": ["T1082", "T1016", "T1049"],
        "exercised": ["T1082"],
        "gap": ["T1016", "T1049"]
      }
    },
    "summary": { "coverage_percent": 12.5 }
  }
}
```

---

### FEAT-2: Multi-Session Orchestration

#### FEAT-2.B-1: `sliver_multi_exec`

- **Description:** Fan-out `session.execute` (or equivalent) across `session_ids[]` **concurrently** via `asyncio.gather`, returning per-session `{session_id, status, output, error, duration_ms}`.
- **Preconditions:** Connected gRPC client; `session_ids` non-empty; all IDs exist on teamserver (or partial success mode documented below); `command` and `args` pass validation per `docs/security.md`.
- **Postconditions:** Aggregated `data.results[]` ordered by input; `data.summary` with `{total, succeeded, failed}`; each success/failure logged to `attack_techniques` if `sliver_execute` (or mapped tool) semantics apply; OPSEC pre-flight runs **per session** before each RPC when tool is high-risk.
- **Error conditions:** Empty `session_ids` → `ValidationError` `EMPTY_SESSION_LIST`. Unknown session ID → entry `status: "error"`, others continue. Global client disconnect → all entries error, top-level `status: "error"`. OPSEC `block` on one session → that entry `status: "blocked"`, others proceed.
- **Data model additions:** Batch insert into `attack_techniques` / engagement actions per session.
- **Agent experience:** Agent runs lateral consistency checks (e.g. `whoami` on all hosts) in one call instead of N serial tool loops.

#### FEAT-2.B-2: `sliver_pivot_chain`

- **Description:** Collect `sliver_ifconfig` + `sliver_netstat` (or cached equivalents) from **all active sessions**, build subnet graph, cross-reference overlaps to propose `PivotHop[]` and upsert `pivot_paths` rows with `method: "inferred_topology"`.
- **Preconditions:** ≥1 active session; network tools succeed on ≥1 session.
- **Postconditions:** `data.topology` with nodes (subnets, sessions) and edges (potential pivots); `data.pivot_hops[]` with confidence; state DB `pivot_paths` updated for high-confidence hops.
- **Error conditions:** No sessions → error hint `sliver_sessions`. All netstat failures → `data.partial: true` with per-session errors. Single session → returns local topology only, empty cross-session hops (not an error).
- **Data model additions:** Updates `pivot_paths`; may update `targets.network_zone` heuristically.
- **Agent experience:** Agent discovers “session A’s 10.0.1.0/24 overlaps session B’s route table” without manual correlation.

#### FEAT-2.B-3: `sliver_session_select`

- **Description:** Rank sessions matching optional `criteria` filter; return ordered `SessionScore[]` with explanatory `factors`.
- **Preconditions:** ≥1 active session.
- **Postconditions:** `data.recommended_session_id` (top rank); `data.rankings[]` with scores. Scoring weights (defaults, env-overridable): privilege `SYSTEM=100, Admin=70, User=30`; EDR count inverse; `network_zone` internal=+20, dmz=+10; stability = min(uptime_hours×2, 40) + recency bonus if last check-in &lt; 5 min.
- **Error conditions:** No matching sessions after filter → `status: "ok"`, `data.rankings: []`, hint to relax criteria. OPSEC scan failure on a session → factor `edr_unknown: true`, score penalty -15 (documented).
- **Data model additions:** Read-only; may read `targets`, latest OPSEC scan cache (if added).
- **Agent experience:** Agent picks optimal implant for credential dumping vs safe discovery without heuristic guessing.

**Criteria object (optional):**

| Field | Type | Description |
|-------|------|-------------|
| `min_privilege` | `user` \| `admin` \| `system` | Filter floor |
| `require_internal` | bool | Prefer internal network_zone |
| `max_edr_count` | int | Exclude sessions above threshold |
| `hostname_pattern` | string | SQL LIKE filter on hostname |
| `task` | string | Hint (`cred_access`, `discovery`, `lateral`) adjusting weights |

---

### FEAT-3: MCP Resources (Event Streaming)

Resources are registered on the FastMCP instance per MCP spec. Each resource returns **UTF-8 JSON** body on read; MIME type `application/json`.

#### FEAT-3.B-1: `sliver://sessions`

- **Description:** Live session list snapshot; refreshed on every resource read (calls `sliver_sessions` logic without side-effect `auto_register` unless `?register=true` query on URI).
- **Preconditions:** gRPC client connectable.
- **Postconditions:** JSON array of session dicts matching `_session_object_to_dict()` shape + `count`.
- **Error conditions:** Connection failure → resource body `{"error": "...", "hints": [...]}` (not MCP transport crash).
- **Data model additions:** None.
- **Agent experience:** Client can pin session list in context panel; reduces redundant `sliver_sessions` tool calls.

#### FEAT-3.B-2: `sliver://events`

- **Description:** Returns recent Sliver events (new session, disconnect, job start/stop) from teamserver event API or ring buffer populated by background poll (implementation frozen in SDK phase).
- **Preconditions:** Connected client; event subscription or poll loop started at server init.
- **Postconditions:** JSON `{events: [{type, timestamp, payload}], cursor}`; max 100 events per read unless `since_cursor` provided.
- **Error conditions:** Event API unavailable on server version → degrade to session diff only (connect/disconnect inferred from session list poll).
- **Data model additions:** Optional in-memory ring buffer only (not required in SQLite).
- **Agent experience:** Agent detects new callbacks without polling `sliver_sessions` in a loop.

#### FEAT-3.B-3: `sliver://state/summary`

- **Description:** Engagement dashboard counts: targets, credentials, findings by severity, active sessions, pivot_paths count, ATT&CK coverage percent.
- **Preconditions:** State DB initialized.
- **Postconditions:** JSON summary object; credentials count only (no secrets).
- **Error conditions:** DB locked → retry once, then error object in resource body.
- **Data model additions:** Read-only aggregate queries.
- **Agent experience:** Single read orients agent on engagement progress.

#### FEAT-3.B-4: `sliver://attack-surface`

- **Description:** Discovered targets with ports/services/OS from state DB (`targets` + `target_services`).
- **Preconditions:** State DB readable.
- **Postconditions:** JSON `{targets: [{hostname, ip, os, services: [...]}]}`.
- **Error conditions:** Empty DB → `{targets: []}` (success, not error).
- **Data model additions:** Reads `target_services`.
- **Agent experience:** Agent plans lateral movement against structured surface, not raw command output.

---

### FEAT-4: Engagement Reporting

#### FEAT-4.B-1: `sliver_generate_report`

- **Description:** Produce deliverable engagement report in `format: "markdown" | "json"`.
- **Preconditions:** State DB contains engagement data; `EngagementMeta.started_at` set or inferred from earliest `attack_techniques.timestamp`.
- **Postconditions:** `data.report` string (Markdown) or object (JSON) containing sections: **Engagement summary**, **Timeline**, **ATT&CK coverage matrix**, **Credentials** (secrets redacted: `***REDACTED***` or hash last 4), **Network topology / pivot paths**, **Findings by severity**, **OPSEC incidents**, **Recommendations** (rule-based from gaps + critical findings).
- **Error conditions:** Unsupported format → `ValidationError`. DB unreadable → error. Report &gt; 10 MB → truncate timeline with `data.truncated: true`.
- **Data model additions:** Reads all tables; optional write `EngagementMeta.last_report_at`.
- **Agent experience:** One-shot export for conference demo or client deliverable.

**Report section requirements (normative):**

| Section | Source data |
|---------|-------------|
| Engagement summary | `EngagementMeta`, session count, duration |
| Timeline | `engagement_actions` or extended `access_log` |
| ATT&CK matrix | `sliver_attack_coverage` output embedded |
| Credentials | `credentials` with redaction |
| Network topology | `pivot_paths`, `targets`, `target_services` |
| Findings | `findings` grouped by severity |
| OPSEC incidents | `opsec_incidents` |
| Recommendations | Template strings keyed off gap tactics + Critical/High findings |

#### FEAT-4.B-2: `sliver_engagement_timeline`

- **Description:** Chronological action log with optional filters: `session_id`, `start_time`, `end_time` (ISO 8601 UTC).
- **Preconditions:** State DB readable.
- **Postconditions:** `data.entries[]` each with `{timestamp, tool_name, session_id, outcome, attack_technique_ids[], summary, target_hostname?}` sorted ascending.
- **Error conditions:** Invalid time range (end before start) → `ValidationError`. No entries → `status: "ok"`, empty array.
- **Data model additions:** Table `engagement_actions` (recommended) — see schema below.
- **Agent experience:** Agent drills into “what happened on this session between 14:00–15:00?” for narrative and debugging.

**Schema `engagement_actions`:**

```sql
CREATE TABLE IF NOT EXISTS engagement_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    session_id TEXT,
    target_id INTEGER,
    outcome TEXT DEFAULT 'ok',
    attack_technique_ids TEXT DEFAULT '[]',  -- JSON array
    summary TEXT DEFAULT '',
    details_json TEXT DEFAULT '{}',
    FOREIGN KEY (target_id) REFERENCES targets(id)
);
CREATE INDEX IF NOT EXISTS idx_engagement_actions_ts ON engagement_actions(timestamp);
CREATE INDEX IF NOT EXISTS idx_engagement_actions_session ON engagement_actions(session_id);
```

---

### FEAT-5: Smart Playbooks

#### FEAT-5.B-1: `sliver_playbook_ad_enum`

- **Description:** Active Directory enumeration playbook on `session_id`: domain info (`nltest`, `whoami /all`), trust enumeration, GPO listing, ACL queries, group membership, service accounts, Kerberoastable accounts, AS-REP roastable accounts. Parses output into findings + credentials + `attack_techniques` per step.
- **Preconditions:** Valid session; target is domain-joined Windows (detected via `sliver_discovery` or session metadata); OPSEC pre-flight for playbook (warn/block per mode).
- **Postconditions:** `PlaybookRun` row `status: completed|partial`; findings for weak ACLs, roastable accounts; credentials stored with source tag `ad_enum`; `data.summary` with counts; `data.attack_techniques_logged[]`.
- **Error conditions:** Non-Windows session → error with hint. Domain not reachable → partial results, `status: partial`. Individual step timeout (120s default) → step marked failed in `data.steps[]`, playbook continues.
- **Data model additions:** Findings, credentials, `attack_techniques`, `PlaybookRun`.
- **Agent experience:** One command replaces 10+ manual `sliver_execute` calls; ATT&CK tags applied (e.g. T1087, T1482, T1558.003).

**Normative step → technique mapping (minimum):**

| Step | ATT&CK ID |
|------|-----------|
| Domain / user enumeration | T1087.002 |
| Trust enumeration | T1482 |
| GPO discovery | T1615 |
| ACL enumeration | T1222 |
| Kerberoastable users | T1558.003 |
| AS-REP roastable | T1558.004 |

#### FEAT-5.B-2: `sliver_playbook_network_sweep`

- **Description:** From implant, run ping sweep and TCP connect scan of **common ports** on `cidr` (validated CIDR, max `/16` prefix unless `SLIVER_SWEEP_MAX_HOSTS` overridden). Identify services; upsert `targets` and `target_services`.
- **Preconditions:** Valid session with network egress to `cidr`; `cidr` passes validation (no RFC1918 bypass of scope — operator responsibility).
- **Postconditions:** `data.hosts_up`, `data.ports_scanned`, `data.services_found[]`; state DB updated.
- **Error conditions:** Invalid CIDR → `ValidationError`. Sweep timeout → partial hosts in DB, `status: partial`. Implant has no raw socket capability → error hint alternative tools.
- **Data model additions:** `target_services`; targets upserted by IP.
- **Agent experience:** Agent expands attack surface map stored for `sliver://attack-surface` and reporting.

**Default common ports (configurable list):** 22, 80, 443, 445, 3389, 5985, 5986, 8080, 8443, 135, 139, 389, 636, 1433, 3306, 5432, 6379, 27017.

#### FEAT-5.B-3: `sliver_suggest_next`

- **Description:** Rule-based advisor (not an LLM inside the server) analyzing sessions, privileges, findings, ATT&CK coverage gaps, targets, and OPSEC state; returns prioritized `RecommendedAction[]` with rationale and technique IDs.
- **Preconditions:** State DB readable; registry loaded.
- **Postconditions:** `data.recommendations[]` length ≤ 10; each entry includes `priority`, `action` (tool or playbook name), `rationale`, `technique_ids`, `preconditions_met`.
- **Error conditions:** No sessions and no historical data → recommendations limited to `sliver_sessions`, `sliver_generate` hints. DB error → error envelope.
- **Data model additions:** Read-only analysis.
- **Agent experience:** Agent receives explicit “do X because gap Y” guidance for conference live-demo narration.

**Example recommendation rules (normative minimum set):**

| Condition | Recommendation |
|-----------|----------------|
| Discovery tactic gap & active session | `sliver_discovery` — T1082/T1016 |
| User-level session + PrivEsc gap | `sliver_playbook_privesc_check` |
| Domain joined + no AD enum run | `sliver_playbook_ad_enum` |
| No target_services + internal session | `sliver_playbook_network_sweep` with inferred /24 |
| Cred Access gap + SYSTEM session | `sliver_process_dump` (OPSEC warn expected) |
| Coverage report &lt; 20% | `sliver_attack_coverage` then highest-gap tactic tool |

---

## Edge Cases

1. **Tool mapped to multiple techniques:** Log one `attack_techniques` row per technique ID per invocation (not a single combined row).
2. **Playbook partial failure:** Techniques logged only for completed steps; `PlaybookRun.status = partial`.
3. **Duplicate technique exercise:** Coverage counts distinct technique IDs with ≥1 success; repeated runs increase `exercise_count` in detailed JSON but not coverage numerator.
4. **`sliver_multi_exec` with one session:** Valid; behaves as single execute with gather overhead only.
5. **Session dies mid–multi-exec:** That task returns gRPC error; others unaffected.
6. **Registry entry for deprecated tool:** Tool invocations never occur; technique remains in `available` but not `exercised`.
7. **Resource read during gRPC reconnect:** Resource returns transitional error JSON; next read succeeds after reconnect.
8. **Report on empty engagement:** Markdown report with “No data” sections, `status: ok` (not error).
9. **Credential secret redaction:** JSON report never includes `credentials.secret` plaintext; Markdown shows username/domain only.
10. **AD enum on workgroup machine:** Fails fast with clear message before LDAP-oriented steps.
11. **Network sweep on /8:** Rejected unless operator raises `SLIVER_SWEEP_MAX_HOSTS`; prevents accidental denial of service.
12. **Concurrent playbook + multi_exec on same session:** Serialized by implant command queue on teamserver; server does not guarantee parallel RPC safety—document as operator limitation.
13. **UNMAPPED tools:** Logged in `engagement_actions` with empty `attack_technique_ids`; coverage summary includes `unmapped_tool_count`.
14. **Beacon sessions in orchestration:** Excluded from `sliver_multi_exec` until beacon execution approved; `sliver_session_select` ranks beacons lower than interactive sessions.

## Failure Modes

| Scenario | Expected behavior |
|----------|-------------------|
| `attack_registry.json` missing (strict) | Server refuses start; stderr message with path hint |
| State DB migration failure | Tools return `STATE_SCHEMA_ERROR`; no partial writes |
| `asyncio.gather` task exception in multi_exec | Per-session error captured; no unhandled exception to MCP layer |
| Event stream poll overload | Ring buffer drops oldest events; `sliver://events` includes `dropped_count` |
| Report generation OOM risk | Stream sections or truncate timeline > 10k entries |
| Pivot analysis with NAT-only addresses | Hops marked `confidence: low`; not written to `pivot_paths` |
| Technique log write fails mid-tool | Tool outcome stands; warning in `data.warnings[]` |
| Invalid CIDR in network sweep | ValidationError before any implant traffic |
| OPSEC block on playbook | Playbook aborts; `PlaybookRun.status = failed`; OPSEC incident row created |
| SQLite WAL checkpoint locked | Retry with backoff (3×, 50ms); then `STATE_BUSY` |

## Non-Functional Requirements

- **NFR-F1 (Traceability):** Every behavior ID `FEAT-n.B-m` MUST map to ≥1 SDK interface and ≥1 mold test before casting.
- **NFR-F2 (Performance):** `sliver_multi_exec` on ≤10 sessions SHOULD complete within 30s wall time assuming per-RPC &lt; 3s; `sliver_attack_coverage` &lt; 200ms on DB &lt; 10k rows.
- **NFR-F3 (Concurrency):** Multi-session fan-out MUST use `asyncio.gather`; MUST NOT block event loop on SQLite (use `asyncio.to_thread` + lock per architecture).
- **NFR-F4 (Security):** Reports MUST redact credential secrets; command injection protections from `docs/security.md` apply to all playbook commands.
- **NFR-F5 (Authorization):** Tool descriptions MUST state authorized-use requirement; report watermark: `Generated by sliver-mcp — authorized engagement only`.
- **NFR-F6 (Audit):** Technique logging MUST NOT be disabled in production profile; env `SLIVER_ATTACK_LOG=false` only for local dev.
- **NFR-F7 (Registry versioning):** `attack_registry.json` includes `version` field; report appendix cites registry version used.
- **NFR-F8 (Resource freshness):** `sliver://sessions` data age MUST be &lt; 1s from read time (live query, no stale cache).
- **NFR-F9 (Determinism):** `sliver_suggest_next` MUST be deterministic for identical DB state (no random tie-break); tie-break by lexicographic `action` name.
- **NFR-F10 (Portability):** Markdown reports MUST use LF line endings and UTF-8 encoding.

## Interface Dependencies

**Depends on (consumer side):**

| Dependency | Contract reference | Usage |
|------------|-------------------|--------|
| C2 Connection | `docs/architecture.md` — `_get_client`, `_interact` | Session execution, netstat/ifconfig |
| Engagement State | `docs/architecture.md` — `state/db.py`, models | Persistence for techniques, targets, timeline |
| OPSEC Guard | `docs/architecture.md` — `_opsec_preflight` | Playbooks and high-risk mapped tools |
| Tool handler / audit | `ToolResponse`, `@tool_handler` | Logging engagement_actions + techniques |
| MITRE ATT&CK v14.1 (static) | `attack_registry.json` | Technique IDs and tactic names |
| MCP Resources protocol | MCP 2024-11-05 resource spec | URI registration and read |
| Security validation | `docs/security.md` (when published) | CIDR, command args, injection |

**Provides (producer side):**

| Surface | Consumers | Contract |
|---------|-----------|----------|
| `sliver_attack_coverage` | AI agents | JSON `AttackCoverageMatrix` in `ToolResponse.data` |
| `sliver_multi_exec`, `sliver_pivot_chain`, `sliver_session_select` | AI agents | Orchestration payloads in `tools/orchestration.py` |
| MCP resources `sliver://*` | MCP clients with resource support | JSON snapshots on read |
| `sliver_generate_report`, `sliver_engagement_timeline` | AI agents, operators | Markdown/JSON deliverables |
| `sliver_playbook_ad_enum`, `sliver_playbook_network_sweep`, `sliver_suggest_next` | AI agents | Playbook summaries + state DB updates |

**Module placement (target package):**

| Feature | Module |
|---------|--------|
| FEAT-1 | `sliver_mcp/tools/attack_mapping.py`, `sliver_mcp/state/models.py`, `data/attack_registry.json` |
| FEAT-2 | `sliver_mcp/tools/orchestration.py` |
| FEAT-3 | `sliver_mcp/resources.py` (registered from `server.py`) |
| FEAT-4 | `sliver_mcp/tools/reporting.py` |
| FEAT-5 | `sliver_mcp/tools/playbooks.py` (extend existing) |

**SDK interfaces (Phase 2 — planned):**

- `AttackRegistry` — load, validate, lookup techniques by tool
- `TechniqueLogger` — append `AttackTechniqueRecord`
- `CoverageAnalyzer` — build `AttackCoverageMatrix`
- `SessionRanker` — score sessions from `SessionScore` factors
- `PivotAnalyzer` — graph build from network snapshots
- `ReportBuilder` — section assembly with redaction policy
- `PlaybookRunner` — shared step runner with technique logging
- `RecommendationEngine` — deterministic rules for `sliver_suggest_next`
- `MCPResourceProvider` — register and read handlers for `sliver://` URIs

## Open Questions

1. **Single vs dual audit tables:** Should `engagement_actions` subsume `access_log` or remain separate? Blocks state migration script. Owner: architecture + this spec revision.
2. **ATT&CK registry completeness gate:** Must 100% of `_TOOL_CATALOG` map before release, or allow `UNMAPPED` bucket in coverage? Blocks mold for registry validation.
3. **Event API source:** Which sliver-py RPC provides teamserver events for `sliver://events` on Sliver 1.7.3+? Blocks `resources.py` casting.
4. **Network sweep implementation:** In-implant script vs staged `sliver_execute` one-liners? Blocks playbook mold (behavior observable either way).
5. **Coverage numerator:** Count techniques with any outcome vs success-only? Current spec: success-only for `exercised`; confirm with product owner.
6. **Navigator layer export:** Include `.layer` JSON in `sliver_generate_report` v1.1? Blocks reporting scope creep.
7. **Fail-open OPSEC interaction:** If scan fails, does `sliver_session_select` exclude session or penalize only? Align with `docs/architecture.md` OQ #1.

## Revision History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0-draft | 2026-05-28 | Codex Automata | Initial differentiating features spec: FEAT-1–5 behaviors, domain model, schemas, NFRs, interface deps |
