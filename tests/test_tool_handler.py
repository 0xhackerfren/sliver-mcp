"""Tests for sliver_mcp.errors (tool_handler decorator, format_tool_error)."""

from __future__ import annotations

import json

import pytest

from sdk.errors import (
    ConnectionError,
    OpsecBlockedError,
    SessionNotFoundError,
    SliverMCPError,
    ValidationError,
)
from sdk.types import ToolStatus
from sliver_mcp.errors import format_tool_error, tool_handler


class TestFormatToolError:
    def test_sliver_mcp_error_preserves_hints(self) -> None:
        exc = ValidationError("ip", "bad-input", "not a valid IP")
        result = json.loads(format_tool_error("sliver_test", exc))
        assert result["status"] == ToolStatus.ERROR.value
        assert result["error_type"] == "ValidationError"
        assert any("bad-input" in h for h in result.get("hints", []))

    def test_generic_exception_infers_grpc_hints(self) -> None:
        exc = RuntimeError("gRPC channel closed unexpectedly")
        result = json.loads(format_tool_error("sliver_test", exc))
        assert result["status"] == ToolStatus.ERROR.value
        assert any("sliver_status" in h or "reconnect" in h.lower() for h in result.get("hints", []))

    def test_generic_not_found_hint(self) -> None:
        exc = RuntimeError("Session not found")
        result = json.loads(
            format_tool_error("sliver_test", exc, session_id="abc-123")
        )
        assert any("sliver_sessions" in h for h in result.get("hints", []))

    def test_permission_hint(self) -> None:
        exc = RuntimeError("Access denied for this operation")
        result = json.loads(format_tool_error("sliver_test", exc))
        assert any("privilege" in h.lower() for h in result.get("hints", []))

    def test_timeout_hint(self) -> None:
        exc = RuntimeError("Operation timeout after 30s")
        result = json.loads(format_tool_error("sliver_test", exc))
        assert any("timeout" in h.lower() for h in result.get("hints", []))

    def test_no_hints_for_unknown_error(self) -> None:
        exc = RuntimeError("Something completely unexpected")
        result = json.loads(format_tool_error("sliver_test", exc))
        assert result.get("hints", []) == []


class TestToolHandlerDecorator:
    @pytest.mark.asyncio
    async def test_success_returns_original_result(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            return '{"result": "ok"}'

        result = await mock_tool()
        assert result == '{"result": "ok"}'

    @pytest.mark.asyncio
    async def test_sliver_error_returns_structured_json(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            raise SessionNotFoundError("dead-session")

        result = json.loads(await mock_tool())
        assert result["status"] == ToolStatus.ERROR.value
        assert result["error_type"] == "SessionNotFoundError"
        assert "dead-session" in result["error"]

    @pytest.mark.asyncio
    async def test_opsec_blocked_returns_blocked_status(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            raise OpsecBlockedError("sliver_execute", ["CrowdStrike"])

        result = json.loads(await mock_tool())
        assert result["status"] == ToolStatus.BLOCKED.value
        assert result["error_type"] == "OpsecBlockedError"

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_with_hints(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            raise RuntimeError("gRPC connection lost")

        result = json.loads(await mock_tool())
        assert result["status"] == ToolStatus.ERROR.value
        assert result["error_type"] == "RuntimeError"
        assert len(result.get("hints", [])) > 0

    @pytest.mark.asyncio
    async def test_attack_technique_passed_through(self) -> None:
        @tool_handler("test_tool", attack_technique="T1059")
        async def mock_tool() -> str:
            raise SliverMCPError("test fail")

        result = json.loads(await mock_tool())
        assert result["attack_technique"] == "T1059"

    @pytest.mark.asyncio
    async def test_duration_ms_present(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            raise SliverMCPError("test fail")

        result = json.loads(await mock_tool())
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_kwargs_session_id_extraction(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool(session_id: str = "") -> str:
            raise SliverMCPError("fail")

        result = json.loads(await mock_tool(session_id="test-sid"))
        assert result["status"] == ToolStatus.ERROR.value

    @pytest.mark.asyncio
    async def test_validation_error_with_hints(self) -> None:
        @tool_handler("test_tool")
        async def mock_tool() -> str:
            raise ValidationError("port", "99999", "out of range")

        result = json.loads(await mock_tool())
        assert result["status"] == ToolStatus.ERROR.value
        assert "out of range" in result["error"]
        assert any("99999" in h for h in result.get("hints", []))
