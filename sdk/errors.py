"""SDK constraint surface: error hierarchy.

All custom exceptions in sliver_mcp must inherit from SliverMCPError.
Error handlers use these types for structured responses and contextual hints.
"""

from __future__ import annotations


class SliverMCPError(Exception):
    """Base exception for all Sliver MCP errors."""

    def __init__(self, message: str, hints: list[str] | None = None):
        super().__init__(message)
        self.hints: list[str] = hints or []


class ConnectionError(SliverMCPError):
    """Failed to connect or lost connection to Sliver teamserver."""

    def __init__(self, message: str = "Cannot reach Sliver teamserver"):
        super().__init__(
            message,
            hints=[
                "Check that the Sliver teamserver is running",
                "Verify SLIVER_CONFIG points to a valid operator .cfg file",
                "Try sliver_reconnect to reset the connection",
            ],
        )


class SessionNotFoundError(SliverMCPError):
    """The requested session or beacon ID does not exist."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Session not found: {session_id}",
            hints=[
                "Run sliver_sessions to list active sessions",
                "The session may have died or been killed",
                "Check if the ID is a beacon -- use sliver_beacons",
            ],
        )
        self.session_id = session_id


class OpsecBlockedError(SliverMCPError):
    """OPSEC guard blocked a high-risk operation."""

    def __init__(self, tool_name: str, products: list[str]):
        products_str = ", ".join(products) if products else "unknown"
        super().__init__(
            f"OPSEC blocked {tool_name}: EDR detected ({products_str})",
            hints=[
                "Consider using a less detectable technique (BOF, manual execution)",
                "Set SLIVER_OPSEC_MODE=warn to proceed with warnings",
                "Run sliver_opsec_check for full EDR assessment",
            ],
        )
        self.tool_name = tool_name
        self.products = products


class ValidationError(SliverMCPError):
    """Input validation failed."""

    def __init__(self, field: str, value: str, reason: str):
        super().__init__(
            f"Invalid {field}: {reason}",
            hints=[f"Provided value: {value}"],
        )
        self.field = field
        self.value = value
        self.reason = reason


class ImplantGenerationError(SliverMCPError):
    """Implant generation failed."""

    def __init__(self, message: str):
        super().__init__(
            message,
            hints=[
                "Check that the Sliver teamserver has the required compilers",
                "Verify the C2 URL is reachable from the teamserver",
                "Try sliver_implant_builds to see existing builds",
            ],
        )


class StateDBError(SliverMCPError):
    """Engagement state database operation failed."""

    def __init__(self, message: str):
        super().__init__(
            message,
            hints=[
                "Check SLIVER_STATE_DB path is writable",
                "The database may be locked by another process",
            ],
        )


class EvasionError(SliverMCPError):
    """Evasion pipeline operation failed."""

    def __init__(self, message: str):
        super().__init__(
            message,
            hints=[
                "Verify the evasion/ directory exists with required scripts",
                "Check that Nim and mingw-w64 are installed (for loader builds)",
                "Set SLIVER_EVASION_DIR if the path is non-default",
            ],
        )


class BeaconNotInteractiveError(SliverMCPError):
    """Attempted interactive operation on a beacon (async-only)."""

    def __init__(self, beacon_id: str):
        super().__init__(
            f"Beacon {beacon_id} does not support interactive sessions",
            hints=[
                "Beacons use async task queuing, not interactive sessions",
                "Use sliver_beacon_tasks to manage beacon tasks",
                "Consider generating a session-mode implant for interactive ops",
            ],
        )
        self.beacon_id = beacon_id
