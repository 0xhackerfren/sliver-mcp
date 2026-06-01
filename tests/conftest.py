"""Shared test fixtures for the Sliver MCP test suite.

Provides mocked SliverClient, temporary state DB, and SDK type factories.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdk.types import (
    AccessLevel,
    Credential,
    CredentialType,
    Finding,
    FindingSeverity,
    SessionInfo,
    Target,
)


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    """Return a temporary SQLite database path."""
    return str(tmp_path / "test_engagement.db")


@pytest.fixture
def mock_sliver_client() -> AsyncMock:
    """Return a mocked SliverClient satisfying the C2Client protocol."""
    client = AsyncMock()
    client.version = AsyncMock(return_value="1.7.3")
    client.connect = AsyncMock()
    client.is_connected = AsyncMock(return_value=True)

    session_mock = MagicMock()
    session_mock.ID = "aabbccdd-1234-5678-9abc-def012345678"
    session_mock.Name = "TEST_SESSION"
    session_mock.Hostname = "WORKSTATION-01"
    session_mock.Username = "admin"
    session_mock.OS = "windows"
    session_mock.Arch = "amd64"
    session_mock.RemoteAddress = "10.10.10.5:443"
    session_mock.PID = 4321
    session_mock.ActiveC2 = "https://10.10.10.1:443"
    session_mock.Transport = "mtls"

    client.sessions = AsyncMock(return_value=[session_mock])
    client.beacons = AsyncMock(return_value=[])
    client.interact_session = AsyncMock()
    client.kill_session = AsyncMock()
    client.jobs = AsyncMock(return_value=[])
    client.operators = AsyncMock(return_value=[])
    client.implant_builds = AsyncMock(return_value=[])

    return client


@pytest.fixture
def sample_target() -> Target:
    return Target(
        hostname="WORKSTATION-01",
        ip_address="10.10.10.5",
        os="Windows 10",
        access_level=AccessLevel.ADMIN,
    )


@pytest.fixture
def sample_credential() -> Credential:
    return Credential(
        username="admin",
        secret="Password123!",
        cred_type=CredentialType.PASSWORD,
        domain="CORP",
        source="mimikatz",
    )


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        title="Unquoted Service Path",
        description="Service 'VulnSvc' has an unquoted path allowing privilege escalation",
        severity=FindingSeverity.HIGH,
    )


@pytest.fixture
def sample_session_info() -> SessionInfo:
    return SessionInfo(
        session_id="aabbccdd-1234-5678-9abc-def012345678",
        name="TEST_SESSION",
        hostname="WORKSTATION-01",
        username="admin",
        os="windows",
        arch="amd64",
        remote_address="10.10.10.5:443",
        pid=4321,
        active_c2="https://10.10.10.1:443",
        transport="mtls",
    )
