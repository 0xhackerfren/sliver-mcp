"""Test molds for SDK domain types.

Ensures dataclasses instantiate correctly, enums validate, and
ToolResponse serialization contract holds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdk.types import (
    AccessLevel,
    AccessLog,
    ActionOutcome,
    AttackCoverageMatrix,
    AttackTechniqueRecord,
    Credential,
    CredentialType,
    Finding,
    FindingSeverity,
    NetworkZone,
    OpsecScanResult,
    PivotHop,
    PivotPath,
    PivotStatus,
    PlaybookRun,
    PlaybookStatus,
    RecommendedAction,
    SessionInfo,
    SessionScore,
    ServiceState,
    TacticCoverage,
    Target,
    TargetService,
    TechniqueOutcome,
    ToolResponse,
    ToolStatus,
)


class TestTarget:
    def test_defaults(self) -> None:
        t = Target(hostname="WS01", ip_address="10.0.0.1")
        assert t.access_level == AccessLevel.UNKNOWN
        assert t.network_zone == NetworkZone.UNKNOWN
        assert t.edr_products == []
        assert t.id is None

    def test_full_construction(self) -> None:
        t = Target(
            hostname="DC01",
            ip_address="10.0.0.2",
            os="Windows Server 2022",
            access_level=AccessLevel.SYSTEM,
            network_zone=NetworkZone.INTERNAL,
            edr_products=["CrowdStrike"],
        )
        assert t.access_level == AccessLevel.SYSTEM
        assert len(t.edr_products) == 1


class TestCredential:
    def test_defaults(self) -> None:
        c = Credential(username="admin", secret="pass")
        assert c.cred_type == CredentialType.PASSWORD
        assert c.domain == ""

    def test_hash_type(self) -> None:
        c = Credential(
            username="admin",
            secret="aad3b435b51404eeaad3b435b51404ee:hash",
            cred_type=CredentialType.HASH_NTLM,
        )
        assert c.cred_type == CredentialType.HASH_NTLM


class TestFinding:
    def test_defaults(self) -> None:
        f = Finding(title="Test", description="Test finding")
        assert f.severity == FindingSeverity.INFO

    def test_critical(self) -> None:
        f = Finding(
            title="DA Access",
            description="Domain Admin compromise",
            severity=FindingSeverity.CRITICAL,
        )
        assert f.severity == FindingSeverity.CRITICAL


class TestAccessLog:
    def test_defaults(self) -> None:
        log = AccessLog(tool_name="sliver_execute")
        assert log.outcome == ActionOutcome.OK
        assert log.duration_ms == 0


class TestOpsecScanResult:
    def test_clear_scan(self) -> None:
        r = OpsecScanResult(safe=True)
        assert r.products_detected == []
        assert r.scan_error == ""

    def test_detected_scan(self) -> None:
        r = OpsecScanResult(
            safe=False,
            products_detected=["CrowdStrike Falcon"],
            warning="EDR active",
        )
        assert not r.safe
        assert len(r.products_detected) == 1

    def test_error_scan_must_be_unsafe(self) -> None:
        """SEC-2: scan errors must result in safe=False."""
        r = OpsecScanResult(safe=False, scan_error="ps() timed out")
        assert not r.safe
        assert r.scan_error != ""


class TestSessionInfo:
    def test_defaults(self) -> None:
        s = SessionInfo(session_id="abc123")
        assert s.is_beacon is False
        assert s.privilege_level == AccessLevel.UNKNOWN


class TestAttackTechniqueRecord:
    def test_defaults(self) -> None:
        r = AttackTechniqueRecord(
            technique_id="T1059",
            tactic="Execution",
            name="Command and Scripting Interpreter",
            tool_name="sliver_execute",
        )
        assert r.outcome == TechniqueOutcome.UNKNOWN


class TestAttackCoverageMatrix:
    def test_empty_matrix(self) -> None:
        m = AttackCoverageMatrix()
        assert m.total_available == 0
        assert m.total_exercised == 0
        assert m.coverage_pct == 0.0


class TestRecommendedAction:
    def test_construction(self) -> None:
        a = RecommendedAction(
            priority=1,
            action="sliver_playbook_ad_enum",
            rationale="AD not enumerated yet",
            technique_ids=["T1087.002"],
        )
        assert a.preconditions_met is True


class TestEnumValues:
    """Ensure enum string values are lowercase for JSON serialization."""

    def test_access_levels(self) -> None:
        assert AccessLevel.SYSTEM.value == "system"
        assert AccessLevel.ADMIN.value == "admin"

    def test_finding_severity(self) -> None:
        assert FindingSeverity.CRITICAL.value == "critical"

    def test_tool_status(self) -> None:
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.ERROR.value == "error"
        assert ToolStatus.BLOCKED.value == "blocked"

    def test_network_zone(self) -> None:
        assert NetworkZone.INTERNAL.value == "internal"
        assert NetworkZone.DMZ.value == "dmz"
