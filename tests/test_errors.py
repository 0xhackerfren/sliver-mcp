"""Test molds for error hierarchy (architecture spec + SEC-1 through SEC-9).

Every error class must produce structured messages and contextual hints.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


class TestSliverMCPError:
    """Base error class contract."""

    def test_message_and_hints(self) -> None:
        err = SliverMCPError("test error", hints=["hint1", "hint2"])
        assert str(err) == "test error"
        assert err.hints == ["hint1", "hint2"]

    def test_default_empty_hints(self) -> None:
        err = SliverMCPError("test")
        assert err.hints == []

    def test_is_exception(self) -> None:
        assert issubclass(SliverMCPError, Exception)


class TestConnectionError:
    """SEC-1 adjacent: connection failures must guide operator."""

    def test_default_message(self) -> None:
        err = ConnectionError()
        assert "teamserver" in str(err).lower()

    def test_has_actionable_hints(self) -> None:
        err = ConnectionError()
        assert len(err.hints) >= 3
        assert any("sliver_reconnect" in h for h in err.hints)

    def test_inherits_base(self) -> None:
        assert issubclass(ConnectionError, SliverMCPError)


class TestSessionNotFoundError:
    """Session lookup failures must suggest next steps."""

    def test_includes_session_id(self) -> None:
        err = SessionNotFoundError("aabb1122")
        assert "aabb1122" in str(err)
        assert err.session_id == "aabb1122"

    def test_has_actionable_hints(self) -> None:
        err = SessionNotFoundError("dead")
        assert any("sliver_sessions" in h for h in err.hints)
        assert any("beacon" in h.lower() for h in err.hints)


class TestOpsecBlockedError:
    """SEC-2: OPSEC blocks must name the products."""

    def test_names_products(self) -> None:
        err = OpsecBlockedError("sliver_execute_assembly", ["CrowdStrike", "Defender"])
        assert "CrowdStrike" in str(err)
        assert "Defender" in str(err)
        assert err.tool_name == "sliver_execute_assembly"

    def test_suggests_alternatives(self) -> None:
        err = OpsecBlockedError("sliver_sideload", ["SentinelOne"])
        assert any("BOF" in h or "manual" in h.lower() for h in err.hints)

    def test_inherits_base(self) -> None:
        assert issubclass(OpsecBlockedError, SliverMCPError)


class TestValidationError:
    """SEC-4: Validation errors carry field context."""

    def test_field_and_reason(self) -> None:
        err = ValidationError("ip_address", "10.0.0.1;rm", "metacharacters")
        assert err.field == "ip_address"
        assert err.value == "10.0.0.1;rm"
        assert "metacharacters" in str(err)

    def test_inherits_base(self) -> None:
        assert issubclass(ValidationError, SliverMCPError)


class TestImplantGenerationError:
    def test_provides_hints(self) -> None:
        err = ImplantGenerationError("build failed")
        assert len(err.hints) >= 2
        assert any("compiler" in h for h in err.hints)


class TestStateDBError:
    def test_provides_hints(self) -> None:
        err = StateDBError("write failed")
        assert any("writable" in h for h in err.hints)


class TestEvasionError:
    def test_provides_hints(self) -> None:
        err = EvasionError("nim not found")
        assert any("Nim" in h for h in err.hints)


class TestBeaconNotInteractiveError:
    def test_message(self) -> None:
        err = BeaconNotInteractiveError("beacon-123")
        assert "beacon-123" in str(err)
        assert err.beacon_id == "beacon-123"

    def test_suggests_beacon_tasks(self) -> None:
        err = BeaconNotInteractiveError("b")
        assert any("beacon_tasks" in h for h in err.hints)


class TestToolResponseEnvelope:
    """Architecture spec: ToolResponse envelope contract."""

    def test_success_response(self) -> None:
        resp = ToolResponse(
            status=ToolStatus.SUCCESS,
            data={"sessions": 3},
            attack_technique="T1082",
        )
        j = resp.to_json()
        assert j["status"] == "success"
        assert j["data"]["sessions"] == 3
        assert j["attack_technique"] == "T1082"
        assert "error" not in j

    def test_error_response(self) -> None:
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error="connection failed",
            error_type="ConnectionError",
            hints=["check server"],
        )
        j = resp.to_json()
        assert j["status"] == "error"
        assert j["error"] == "connection failed"
        assert j["hints"] == ["check server"]
        assert "data" not in j

    def test_blocked_response(self) -> None:
        resp = ToolResponse(
            status=ToolStatus.BLOCKED,
            error="EDR detected",
            attack_technique="T1055",
        )
        j = resp.to_json()
        assert j["status"] == "blocked"

    def test_omits_none_fields(self) -> None:
        resp = ToolResponse(status=ToolStatus.SUCCESS, data={"ok": True})
        j = resp.to_json()
        assert "error" not in j
        assert "error_type" not in j
        assert "hints" not in j
        assert "attack_technique" not in j
        assert "duration_ms" not in j
