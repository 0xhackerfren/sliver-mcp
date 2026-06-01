"""Test molds for input validation (SEC-4, SEC-6, SEC-7).

Derived from docs/security.md validation contracts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdk.errors import ValidationError
from sdk.validators import (
    safe_shell_split,
    validate_cidr,
    validate_ip,
    validate_no_injection,
    validate_non_empty,
    validate_path,
    validate_port,
    validate_session_id,
)


class TestValidateIP:
    """SEC-4: IP address validation."""

    def test_valid_ipv4(self) -> None:
        assert validate_ip("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv6(self) -> None:
        assert validate_ip("::1") == "::1"

    def test_valid_cidr(self) -> None:
        assert validate_ip("10.0.0.0/24") == "10.0.0.0/24"

    def test_strips_whitespace(self) -> None:
        assert validate_ip("  10.0.0.1  ") == "10.0.0.1"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_ip("")

    def test_rejects_shell_metachar(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_ip("10.0.0.1; rm -rf /")

    def test_rejects_invalid_format(self) -> None:
        with pytest.raises(ValidationError, match="not a valid"):
            validate_ip("not-an-ip")

    def test_rejects_backtick_injection(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_ip("`whoami`")

    def test_rejects_pipe_injection(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_ip("10.0.0.1|calc")


class TestValidateSessionID:
    """SEC-4: Session ID format validation."""

    def test_valid_uuid_style(self) -> None:
        sid = "aabbccdd-1234-5678-9abc-def012345678"
        assert validate_session_id(sid) == sid

    def test_valid_hex_short(self) -> None:
        assert validate_session_id("aabbccdd") == "aabbccdd"

    def test_strips_whitespace(self) -> None:
        assert validate_session_id("  aabb1122  ") == "aabb1122"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_session_id("")

    def test_rejects_non_hex(self) -> None:
        with pytest.raises(ValidationError, match="hex string"):
            validate_session_id("not-a-valid-session-xyz!")

    def test_rejects_too_short(self) -> None:
        with pytest.raises(ValidationError, match="hex string"):
            validate_session_id("aabb")

    def test_rejects_shell_chars(self) -> None:
        with pytest.raises(ValidationError, match="hex string"):
            validate_session_id("aabb; whoami")


class TestValidatePort:
    """SEC-4: Port number validation."""

    def test_valid_port(self) -> None:
        assert validate_port(443) == 443

    def test_valid_port_string(self) -> None:
        assert validate_port("8080") == 8080

    def test_min_port(self) -> None:
        assert validate_port(1) == 1

    def test_max_port(self) -> None:
        assert validate_port(65535) == 65535

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValidationError, match="between 1 and 65535"):
            validate_port(0)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError, match="between 1 and 65535"):
            validate_port(-1)

    def test_rejects_too_high(self) -> None:
        with pytest.raises(ValidationError, match="between 1 and 65535"):
            validate_port(70000)

    def test_rejects_non_integer(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_port("abc")


class TestValidatePath:
    """SEC-4: Path traversal prevention."""

    def test_valid_path(self) -> None:
        assert validate_path("C:\\Users\\Public\\file.exe") == "C:\\Users\\Public\\file.exe"

    def test_valid_unix_path(self) -> None:
        assert validate_path("/tmp/evidence/file.bin") == "/tmp/evidence/file.bin"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_path("")

    def test_rejects_dot_dot(self) -> None:
        with pytest.raises(ValidationError, match="path traversal"):
            validate_path("../../etc/passwd")

    def test_rejects_backslash_traversal(self) -> None:
        with pytest.raises(ValidationError, match="path traversal"):
            validate_path("..\\..\\windows\\system32")


class TestSafeShellSplit:
    """SEC-7: Argument splitting with quote support."""

    def test_simple_args(self) -> None:
        assert safe_shell_split("arg1 arg2 arg3") == ["arg1", "arg2", "arg3"]

    def test_quoted_arg(self) -> None:
        result = safe_shell_split('arg1 "arg with spaces" arg3')
        assert result == ["arg1", "arg with spaces", "arg3"]

    def test_single_quoted(self) -> None:
        result = safe_shell_split("arg1 'arg with spaces' arg3")
        assert result == ["arg1", "arg with spaces", "arg3"]

    def test_empty_string(self) -> None:
        assert safe_shell_split("") == []

    def test_malformed_quotes_raises(self) -> None:
        with pytest.raises(ValidationError, match="malformed"):
            safe_shell_split('arg1 "unterminated')


class TestValidateNoInjection:
    """SEC-6: Shell metacharacter rejection."""

    def test_clean_value(self) -> None:
        assert validate_no_injection("hostname") == "hostname"

    def test_rejects_semicolon(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_no_injection("value; rm -rf /")

    def test_rejects_pipe(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_no_injection("value|evil")

    def test_rejects_backtick(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_no_injection("`whoami`")

    def test_rejects_dollar(self) -> None:
        with pytest.raises(ValidationError, match="metacharacters"):
            validate_no_injection("$(id)")


class TestValidateCIDR:
    """Network CIDR validation."""

    def test_valid_cidr(self) -> None:
        assert validate_cidr("10.0.0.0/24") == "10.0.0.0/24"

    def test_valid_single_host(self) -> None:
        assert validate_cidr("10.0.0.1/32") == "10.0.0.1/32"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_cidr("")

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError, match="not a valid CIDR"):
            validate_cidr("not-a-cidr")


class TestValidateNonEmpty:
    """Generic non-empty validation."""

    def test_valid_string(self) -> None:
        assert validate_non_empty("hello") == "hello"

    def test_strips_and_validates(self) -> None:
        assert validate_non_empty("  hello  ") == "hello"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_non_empty("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_non_empty("   ")
