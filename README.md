# sliver-mcp

The most comprehensive [Sliver C2](https://github.com/BishopFox/sliver) MCP server available. **91+ tools** covering the full red team lifecycle, from implant generation through post-exploitation to cleanup, with MITRE ATT&CK integration, multi-session orchestration, engagement reporting, and AI-powered next-action recommendations.

Built with the [Codex Automata](https://github.com/0xhackerfren/Codex-Automata) methodology: spec-first, test-first, SDK-constrained.

> **For authorized security testing only.** This tool is designed for professional penetration testers and red team operators working under explicit written authorization.

## Why sliver-mcp?

| Capability | sliver-mcp v2 | schwarztim/sec-sliver-c2-mcp | d4vydm/sliverc2_mcp | Sliver built-in MCP |
|---|---|---|---|---|
| Tools | **91+** | ~20 | ~14 | ~10 |
| MITRE ATT&CK mapping | Yes (48 tools mapped) | No | No | No |
| Multi-session orchestration | Yes | No | No | No |
| Engagement reporting | Yes (Markdown/JSON) | No | No | No |
| MCP Resources (live data) | Yes (3 resources) | No | No | No |
| AI advisor (suggest next) | Yes | No | No | No |
| Evasion pipeline | Yes | No | No | No |
| Engagement state DB | Yes | No | No | No |
| OPSEC guard (fail-closed) | Yes | No | No | No |
| Operator playbooks | 7 playbooks | No | No | No |
| Payload generation | Yes (raw protobuf fix) | Broken on 1.7+ | No | Basic |
| Post-exploitation | Full suite | Basic | Minimal | Minimal |
| Pivoting | SOCKS5 + port forwarding | No | No | No |
| Input validation | Yes (SEC hardened) | No | No | No |
| Structured logging | Yes (JSON audit trail) | No | No | No |
| Test suite | 100 tests | No | No | No |
| CI/CD | GitHub Actions | No | No | No |

## Architecture

```
MCP Client (Cursor/Claude) --> [stdio] --> FastMCP Server
                                               |
                    +--------------------------+--------------------------+
                    |                          |                          |
              Legacy Tools (82)          New Tools (9+)            MCP Resources (3)
              server.py                  sliver_mcp/tools/         sliver_mcp/resources.py
                    |                          |                          |
              gRPC/mTLS                   SDK Types                 State DB (SQLite)
                    |                     sdk/                           |
              Sliver Teamserver           - types.py              engagement_state.db
                                          - errors.py
                                          - validators.py
                                          - protocols.py
                                          - attack_map.py (48 ATT&CK mappings)
```

## Features

### Core Operator Tools (82 tools)
Full gRPC integration with Sliver covering sessions, beacons, implant generation, file operations, process management, network recon, pivoting, credential operations, persistence, lateral movement, and cleanup.

### MITRE ATT&CK Integration (NEW)
Every tool mapped to ATT&CK technique IDs. Track which techniques have been exercised across the engagement, identify coverage gaps, and generate ATT&CK matrices for reports.

### Multi-Session Orchestration (NEW)
Fan-out command execution across multiple sessions simultaneously. Smart session selection ranking by privilege level, EDR exposure, and network position. Automatic pivot chain discovery from session network topology.

### Engagement Reporting (NEW)
Generate structured engagement reports in Markdown or JSON with timelines, ATT&CK coverage, credential inventory (secrets redacted), network topology, and findings by severity.

### Smart Playbooks (NEW)
- **AD Enumeration**: Domain info, trusts, GPOs, group memberships, service accounts
- **Network Sweep**: CIDR ping sweep + port scanning via implant, auto-populate targets
- **AI Advisor**: Deterministic rule engine recommending next actions based on engagement state

### MCP Resources (NEW)
Live engagement data exposed as MCP resources:
- `sliver://sessions` - Current session list
- `sliver://state/summary` - Engagement dashboard
- `sliver://attack-surface` - Discovered targets and services

### Evasion Pipeline
Integrated payload generation that bypasses Windows Defender:
- Shellcode generation via Sliver with correct protobuf wire format for Sliver 1.7+
- AES-256-CBC encryption with per-build key generation
- Nim-based loaders using indirect syscalls and thread pool callback execution
- Pre-deployment Defender scanning
- Full end-to-end pipeline in a single tool call

### Engagement State Database
Persistent SQLite tracking that no other Sliver MCP offers:
- **Targets** - hostname, IP, OS, domain, access level
- **Credentials** - username, secret, type (plaintext/NTLM/kerberos), source
- **Access log** - session events with timestamps
- **Findings** - title, severity, evidence path, description
- **Pivot paths** - source/dest mapping with method and status
- Export to JSON for reporting

### OPSEC Guard
Built-in safety layer before dangerous operations:
- Scans target process list for 16 EDR/AV products (CrowdStrike, SentinelOne, Carbon Black, Defender ATP, Cortex XDR, Elastic, Cylance, ESET, Sophos, Kaspersky, Symantec, Trend Micro, FireEye, Wazuh, Velociraptor, Sysmon)
- Automatic pre-flight checks on 10 high-risk tools
- Three modes: `warn` (default), `block`, `silent`
- EDR signatures stored in editable config, not hardcoded

### Operator Playbooks
Single-command compound operations:
- **Initial Recon** - whoami, systeminfo, network, processes, users, admin groups, OPSEC scan, auto-target registration
- **Privesc Check** - privileges, groups, UAC, unquoted services, AlwaysInstallElevated, auto-logon
- **Credential Harvest** - cmdkey, vault, Wi-Fi, SAM backups, DPAPI, browser stores
- **Persistence Check** - Run keys, startup folders, scheduled tasks, services, WMI, IFEO, Winlogon

## Quick Start

### Prerequisites

- Python 3.10+
- Sliver C2 server running and accessible via gRPC
- Sliver operator config file (`.cfg`)

### Install

```bash
# Clone
git clone https://github.com/SuzuLabs/sliver-mcp.git
cd sliver-mcp

# Install dependencies
pip install -e .

# Or just install requirements
pip install -r requirements.txt
```

### Generate Operator Config

If you don't already have one:

```bash
# On the Sliver server
sliver-server operator --name cursor --lhost <server-ip> --save /path/to/cursor.cfg
```

### Configure

All configuration is via environment variables with sensible defaults:

| Variable | Description | Default |
|---|---|---|
| `SLIVER_CONFIG` | Path to operator `.cfg` file | Auto-detect from `~/.sliver-client/configs/` |
| `SLIVER_PROJECT_ROOT` | Project root directory | Auto-detected from `server.py` location |
| `SLIVER_EVASION_DIR` | Evasion scripts directory | `$SLIVER_PROJECT_ROOT/evasion` |
| `SLIVER_EVIDENCE_DIR` | Evidence output directory | `/tmp/sliver-evidence` |
| `SLIVER_STATE_DB` | Engagement state DB path | `$SLIVER_PROJECT_ROOT/engagement_state.db` |
| `SLIVER_OPSEC_MODE` | OPSEC guard mode | `warn` |

### MCP Client Setup

**Cursor IDE** - add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sliver": {
      "command": "wsl",
      "args": ["--distribution", "kali-linux", "--", "python3", "/path/to/server.py"],
      "env": {
        "SLIVER_CONFIG": "/home/user/.sliver-client/configs/cursor.cfg"
      }
    }
  }
}
```

**Claude Desktop** - add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sliver": {
      "command": "python3",
      "args": ["/path/to/server.py"],
      "env": {
        "SLIVER_CONFIG": "/path/to/cursor.cfg"
      }
    }
  }
}
```

**Direct** (any MCP client):

```bash
export SLIVER_CONFIG=/path/to/cursor.cfg
python3 server.py
```

## Usage

### Basic Workflow

```
1. sliver_status              # Verify connection
2. sliver_sessions             # List active sessions
3. sliver_execute(session_id, "whoami", "/all")  # Run commands
```

### Evasion Pipeline

```
sliver_evasion_pipeline(
    c2_url="https://10.0.0.1:443",
    callback_ip="10.0.0.1",
    host_label="dc01"
)
```

Generates shellcode, encrypts it, compiles evasion loaders, all in one call.

### Engagement Tracking

```
sliver_state_add_target(hostname="DC01", ip="10.0.0.5", os="Windows Server 2022")
sliver_state_add_cred(username="admin", secret="P@ssw0rd", cred_type="plaintext")
sliver_state_add_finding(title="Domain Admin via Kerberoasting", severity="critical")
sliver_state_summary()         # Dashboard view
sliver_state_export()          # Full JSON export for reporting
```

### OPSEC Check

```
sliver_opsec_check(session_id)  # Scan for EDR/AV before risky ops
```

### Playbooks

```
sliver_playbook_initial_recon(session_id)    # Full recon suite
sliver_playbook_privesc_check(session_id)    # Privesc assessment
sliver_playbook_cred_harvest(session_id)     # Credential enum
sliver_playbook_persist_check(session_id)    # Persistence audit
```

## Tool Reference

### Server / Connection (5)
`sliver_status`, `sliver_jobs`, `sliver_start_https_listener`, `sliver_start_dns_listener`, `sliver_stop_job`

### Session / Beacon Management (5)
`sliver_sessions`, `sliver_beacons`, `sliver_kill_session`, `sliver_generate`, `sliver_implant_builds`

### Evasion Pipeline (4)
`sliver_encrypt_shellcode`, `sliver_build_loaders`, `sliver_evasion_pipeline`, `sliver_preflight_defender`

### Implant Interaction (12)
`sliver_execute`, `sliver_ls`, `sliver_cd`, `sliver_pwd`, `sliver_ps`, `sliver_netstat`, `sliver_ifconfig`, `sliver_upload`, `sliver_download`, `sliver_screenshot`, `sliver_rm`, `sliver_mkdir`

### Post-Exploitation (3)
`sliver_discovery`, `sliver_lateral_check`, `sliver_collect_evidence`

### Pivoting (5)
`sliver_socks_start`, `sliver_socks_stop`, `sliver_portfwd_add`, `sliver_portfwd_list`, `sliver_portfwd_rm`

### Engagement State Database (10)
`sliver_state_add_target`, `sliver_state_targets`, `sliver_state_add_cred`, `sliver_state_creds`, `sliver_state_add_finding`, `sliver_state_findings`, `sliver_state_log_access`, `sliver_state_summary`, `sliver_state_export`, `sliver_state_add_pivot`

### OPSEC Guard (1 + preflight hooks)
`sliver_opsec_check` (plus automatic pre-flight on 10 high-risk tools)

### Operator Playbooks (4)
`sliver_playbook_initial_recon`, `sliver_playbook_privesc_check`, `sliver_playbook_cred_harvest`, `sliver_playbook_persist_check`

### Cleanup (2)
`sliver_cleanup_target`, `sliver_full_cleanup`

### Advanced (12)
`sliver_execute_assembly`, `sliver_execute_shellcode`, `sliver_sideload`, `sliver_get_system`, `sliver_make_token`, `sliver_run_as`, `sliver_migrate`, `sliver_process_dump`, `sliver_terminate_process`, `sliver_impersonate`, `sliver_revert_to_self`, `sliver_registry_read`

### Persistence / Services (6)
`sliver_registry_write`, `sliver_registry_create_key`, `sliver_start_service`, `sliver_stop_service`, `sliver_remove_service`, `sliver_set_env`

### Management (6)
`sliver_rename_session`, `sliver_rename_beacon`, `sliver_kill_beacon`, `sliver_regenerate_implant`, `sliver_start_http_listener`, `sliver_operators`

### Websites (2)
`sliver_website_add`, `sliver_websites`

## Evasion Architecture

The evasion pipeline uses a multi-stage approach:

```
Sliver Server                    sliver-mcp                         Target
    |                                |                                 |
    |-- Generate shellcode --------->|                                 |
    |                                |-- AES-256-CBC encrypt --------->|
    |                                |-- Compile Nim loader ---------->|
    |                                |   (indirect syscalls,           |
    |                                |    thread pool callbacks,       |
    |                                |    WinHTTP native fetch)        |
    |                                |                                 |
    |                                |-- Deploy loader + payload ----->|
    |                                |                                 |
    |<-- Session callback -----------|<--------------------------------|
```

### Protobuf Compatibility

`sliver-py` v0.0.19 has mismatched protobuf field numbers vs Sliver 1.7.3+. This MCP server includes raw protobuf wire-format construction that uses the correct server-side field numbers, fixing payload generation that is broken in every other Python-based Sliver MCP.

## Cleanup Manifest

Customize artifact paths for cleanup by editing `cleanup_manifest.json`:

```json
[
  "C:\\Users\\Public\\loader_remote.exe",
  "C:\\Users\\Public\\payload.enc",
  "C:\\custom\\path\\artifact.exe"
]
```

## Security Notice

This software is provided for authorized security testing and research purposes only. Users are responsible for:

- Obtaining proper written authorization before any testing
- Complying with all applicable laws and regulations
- Following responsible disclosure practices
- Not using this tool for unauthorized access

The authors assume no liability for misuse of this software.

## License

MIT - see [LICENSE](LICENSE)
