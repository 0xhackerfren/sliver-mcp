"""Sliver MCP Server v2 - Production-grade entry point.

This module creates the FastMCP app, registers all tools (legacy + new),
sets up MCP resources, configures structured logging, and serves as the
main entry point for the sliver-mcp console script.

Architecture:
    - Legacy tools: imported from the root server module (82 existing tools)
    - New tools: imported from sliver_mcp.tools.* modules
    - Resources: registered from sliver_mcp.resources
    - Infrastructure: config, errors, SDK types
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure project root is on the path so root-level server module is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import server as legacy_server  # noqa: E402

from sliver_mcp.tools import attack_mapping, orchestration, reporting, smart_playbooks  # noqa: E402
from sliver_mcp import resources  # noqa: E402

mcp = legacy_server.mcp

# ---------------------------------------------------------------------------
# Register new tools on the legacy FastMCP instance
# ---------------------------------------------------------------------------

mcp.tool()(attack_mapping.sliver_attack_coverage)
mcp.tool()(orchestration.sliver_multi_exec)
mcp.tool()(orchestration.sliver_session_select)
mcp.tool()(orchestration.sliver_pivot_chain)
mcp.tool()(reporting.sliver_generate_report)
mcp.tool()(reporting.sliver_engagement_timeline)
mcp.tool()(smart_playbooks.sliver_playbook_ad_enum)
mcp.tool()(smart_playbooks.sliver_playbook_network_sweep)
mcp.tool()(smart_playbooks.sliver_suggest_next)


# ---------------------------------------------------------------------------
# Register MCP resources
# ---------------------------------------------------------------------------

@mcp.resource("sliver://sessions")
async def sessions_resource() -> str:
    """Live session list from the Sliver teamserver."""
    return await resources.get_sessions_resource()


@mcp.resource("sliver://state/summary")
async def state_summary_resource() -> str:
    """Engagement state dashboard with counts and ATT&CK coverage."""
    return await resources.get_state_summary_resource()


@mcp.resource("sliver://attack-surface")
async def attack_surface_resource() -> str:
    """Discovered targets with ports, services, and OS info."""
    return await resources.get_attack_surface_resource()


# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    """Configure structured JSON logging for audit trail."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)

    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            for key in ("tool", "session_id", "outcome", "duration_ms",
                        "attack_technique", "error"):
                val = getattr(record, key, None)
                if val is not None:
                    log_data[key] = val
            return json.dumps(log_data)

    handler.setFormatter(JSONFormatter())

    for name in ("sliver_mcp", "sliver_mcp.audit"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False


# ---------------------------------------------------------------------------
# Update tool catalog to include new tools
# ---------------------------------------------------------------------------

_NEW_TOOLS = {
    "attack_mapping": [
        ("sliver_attack_coverage", "Show MITRE ATT&CK technique coverage for the engagement"),
    ],
    "orchestration": [
        ("sliver_multi_exec", "Execute a command across multiple sessions simultaneously"),
        ("sliver_session_select", "Rank and select optimal session for a task"),
        ("sliver_pivot_chain", "Discover pivot paths from session network topology"),
    ],
    "reporting": [
        ("sliver_generate_report", "Generate structured engagement report (Markdown/JSON)"),
        ("sliver_engagement_timeline", "Chronological action log with ATT&CK tags"),
    ],
    "smart_playbooks": [
        ("sliver_playbook_ad_enum", "Active Directory enumeration playbook"),
        ("sliver_playbook_network_sweep", "Network discovery and port scanning via implant"),
        ("sliver_suggest_next", "AI advisor: recommended next actions based on engagement state"),
    ],
}

if hasattr(legacy_server, "_TOOL_CATALOG"):
    for category, tools in _NEW_TOOLS.items():
        legacy_server._TOOL_CATALOG[category] = tools


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entry point for sliver-mcp v2."""
    _setup_logging()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
