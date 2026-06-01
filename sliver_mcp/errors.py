"""Error handling infrastructure.

Provides the @tool_handler decorator that wraps every MCP tool for
consistent error handling, audit logging, and ToolResponse formatting.
Re-exports SDK error types for convenience.
"""

from __future__ import annotations

import functools
import json
import logging
import time
from typing import Any, Callable, Coroutine

from sdk.errors import (
    BeaconNotInteractiveError,
    ConnectionError,
    EvasionError,
    ImplantGenerationError,
    OpsecBlockedError,
    SessionNotFoundError,
    SliverMCPError,
    StateDBError,
    ValidationError,
)
from sdk.types import ToolResponse, ToolStatus

logger = logging.getLogger("sliver_mcp")
audit_logger = logging.getLogger("sliver_mcp.audit")

__all__ = [
    "BeaconNotInteractiveError",
    "ConnectionError",
    "EvasionError",
    "ImplantGenerationError",
    "OpsecBlockedError",
    "SessionNotFoundError",
    "SliverMCPError",
    "StateDBError",
    "ValidationError",
    "format_tool_error",
    "tool_handler",
]


def format_tool_error(
    tool_name: str,
    exc: Exception,
    *,
    session_id: str = "",
    context: str = "",
) -> str:
    """Format an exception into a standardized JSON error response."""
    error_type = type(exc).__name__
    message = str(exc)

    hints: list[str] = []
    if isinstance(exc, SliverMCPError):
        hints = exc.hints
    else:
        hints = _infer_hints(exc, session_id=session_id)

    resp = ToolResponse(
        status=ToolStatus.ERROR,
        error=message,
        error_type=error_type,
        hints=hints,
    )

    return json.dumps(resp.to_json(), indent=2)


def _infer_hints(exc: Exception, session_id: str = "") -> list[str]:
    """Infer contextual hints from exception type and message."""
    hints: list[str] = []
    msg = str(exc).lower()

    if "not found" in msg and session_id:
        hints.append("Run sliver_sessions to list active sessions.")
        hints.append("The session may have died. Check sliver_beacons too.")
    elif "grpc" in msg or "connect" in msg or "channel" in msg:
        hints.append("Run sliver_status to check the teamserver connection.")
        hints.append("Try sliver_reconnect to reset the gRPC channel.")
    elif "permission" in msg or "access" in msg:
        hints.append("The implant may lack privileges for this operation.")
        hints.append("Try sliver_get_system or sliver_impersonate first.")
    elif "timeout" in msg:
        hints.append("The operation timed out. The target may be under load.")
        hints.append("Try again or increase the timeout if applicable.")

    return hints


def tool_handler(
    tool_name: str,
    *,
    attack_technique: str | None = None,
) -> Callable:
    """Decorator wrapping MCP tools for consistent error handling and audit logging.

    Usage:
        @mcp.tool()
        @tool_handler("sliver_execute", attack_technique="T1059")
        async def sliver_execute(session_id: str, ...) -> str:
            ...
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, str]],
    ) -> Callable[..., Coroutine[Any, Any, str]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> str:
            start = time.monotonic()
            session_id = kwargs.get("session_id", "") or (
                args[0] if args and isinstance(args[0], str) else ""
            )
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                audit_logger.info(
                    "tool_call",
                    extra={
                        "tool": tool_name,
                        "session_id": session_id,
                        "outcome": "ok",
                        "duration_ms": elapsed_ms,
                        "attack_technique": attack_technique,
                    },
                )
                return result

            except SliverMCPError as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                status = ToolStatus.BLOCKED if isinstance(exc, OpsecBlockedError) else ToolStatus.ERROR
                audit_logger.warning(
                    "tool_error",
                    extra={
                        "tool": tool_name,
                        "session_id": session_id,
                        "outcome": status.value,
                        "error": str(exc),
                        "duration_ms": elapsed_ms,
                    },
                )
                resp = ToolResponse(
                    status=status,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    hints=exc.hints,
                    attack_technique=attack_technique,
                    duration_ms=elapsed_ms,
                )
                return json.dumps(resp.to_json(), indent=2)

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                audit_logger.error(
                    "tool_error",
                    extra={
                        "tool": tool_name,
                        "session_id": session_id,
                        "outcome": "error",
                        "error": str(exc),
                        "duration_ms": elapsed_ms,
                    },
                )
                return format_tool_error(
                    tool_name, exc, session_id=session_id,
                )

        return wrapper
    return decorator
