"""SDK constraint surface: input validation contracts.

Every user-supplied value that crosses a trust boundary (tool parameters
destined for shell commands, gRPC calls, or database queries) must pass
through one of these validators. Validators raise ValidationError on
failure and return the validated value on success.
"""

from __future__ import annotations

import ipaddress
import re
import shlex

from .errors import ValidationError

# ---------------------------------------------------------------------------
# IP address
# ---------------------------------------------------------------------------

_SHELL_META_RE = re.compile(r"[;&|`$(){}!<>'\"\\\n\r]")


def validate_ip(value: str, field: str = "ip_address") -> str:
    """Validate IPv4 or IPv6 address format. No shell metacharacters."""
    value = value.strip()
    if not value:
        raise ValidationError(field, value, "IP address cannot be empty")
    if _SHELL_META_RE.search(value):
        raise ValidationError(field, value, "contains disallowed shell metacharacters")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise ValidationError(field, value, "not a valid IPv4/IPv6 address or CIDR")
    return value


# ---------------------------------------------------------------------------
# Session ID
# ---------------------------------------------------------------------------

_SESSION_ID_RE = re.compile(r"^[a-fA-F0-9\-]{8,64}$")


def validate_session_id(value: str, field: str = "session_id") -> str:
    """Validate session/beacon ID: hex string with optional hyphens, 8-64 chars."""
    value = value.strip()
    if not value:
        raise ValidationError(field, value, "session ID cannot be empty")
    if not _SESSION_ID_RE.match(value):
        raise ValidationError(
            field, value,
            "must be a hex string (8-64 chars, a-f 0-9 and hyphens only)"
        )
    return value


# ---------------------------------------------------------------------------
# Port number
# ---------------------------------------------------------------------------

def validate_port(value: int | str, field: str = "port") -> int:
    """Validate port number: integer 1-65535."""
    try:
        port = int(value)
    except (ValueError, TypeError):
        raise ValidationError(field, str(value), "must be an integer")
    if port < 1 or port > 65535:
        raise ValidationError(field, str(port), "must be between 1 and 65535")
    return port


# ---------------------------------------------------------------------------
# File path (no traversal)
# ---------------------------------------------------------------------------

_TRAVERSAL_PATTERNS = ["..", "..\\", "../"]


def validate_path(value: str, field: str = "path") -> str:
    """Validate file path: no path traversal sequences."""
    value = value.strip()
    if not value:
        raise ValidationError(field, value, "path cannot be empty")
    for pattern in _TRAVERSAL_PATTERNS:
        if pattern in value:
            raise ValidationError(
                field, value,
                f"path traversal detected ({pattern})"
            )
    return value


# ---------------------------------------------------------------------------
# Shell argument safety
# ---------------------------------------------------------------------------

def safe_shell_split(args: str) -> list[str]:
    """Split command arguments respecting quotes. shlex.split wrapper."""
    try:
        return shlex.split(args)
    except ValueError as exc:
        raise ValidationError("args", args, f"malformed shell arguments: {exc}")


def validate_no_injection(value: str, field: str = "parameter") -> str:
    """Reject values containing shell metacharacters for safe interpolation."""
    value = value.strip()
    if _SHELL_META_RE.search(value):
        raise ValidationError(field, value, "contains disallowed shell metacharacters")
    return value


# ---------------------------------------------------------------------------
# CIDR notation
# ---------------------------------------------------------------------------

def validate_cidr(value: str, field: str = "cidr") -> str:
    """Validate CIDR network notation."""
    value = value.strip()
    if not value:
        raise ValidationError(field, value, "CIDR cannot be empty")
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise ValidationError(field, value, "not a valid CIDR notation")
    return value


# ---------------------------------------------------------------------------
# Generic string length
# ---------------------------------------------------------------------------

def validate_non_empty(value: str, field: str = "value") -> str:
    """Ensure string is non-empty after stripping."""
    value = value.strip()
    if not value:
        raise ValidationError(field, value, f"{field} cannot be empty")
    return value
