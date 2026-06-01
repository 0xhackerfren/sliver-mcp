"""Tests for sliver_mcp.tools.reporting (report, timeline, redaction)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sliver_mcp.tools.reporting import (
    REDACTED_SECRET,
    REPORT_WATERMARK,
    _build_coverage_section,
    _build_report_payload,
    _build_timeline_entries,
    _engagement_duration,
    _fetch_credentials,
    _fetch_findings,
    _fetch_pivot_paths,
    _fetch_targets,
    _get_state_db,
    _parse_ts,
    _redact_credential,
    _report_to_markdown,
)
from sdk.types import ToolStatus


@pytest.fixture
def reporting_db(tmp_path: Path) -> sqlite3.Connection:
    """Create a fresh reporting database with full schema."""
    db_path = str(tmp_path / "report_test.db")
    with patch("sliver_mcp.tools.reporting.resolve_state_db_path", return_value=db_path):
        import sliver_mcp.tools.reporting as mod
        mod._state_db = None
        import sliver_mcp.tools.attack_mapping as atk_mod
        atk_mod._state_db = None
        with patch("sliver_mcp.tools.attack_mapping.resolve_state_db_path", return_value=db_path):
            db = _get_state_db()
    yield db
    db.close()
    import sliver_mcp.tools.reporting as mod
    mod._state_db = None
    import sliver_mcp.tools.attack_mapping as atk_mod
    atk_mod._state_db = None


def _seed_targets(db: sqlite3.Connection) -> list[int]:
    ids = []
    for hostname, ip, os_name in [
        ("DC01", "10.0.0.1", "Windows Server 2022"),
        ("WS01", "10.0.0.10", "Windows 10"),
    ]:
        cur = db.execute(
            "INSERT INTO targets (hostname, ip, os) VALUES (?, ?, ?)",
            (hostname, ip, os_name),
        )
        ids.append(cur.lastrowid)
    db.commit()
    return ids


def _seed_credentials(db: sqlite3.Connection, target_id: int) -> None:
    db.execute(
        "INSERT INTO credentials (username, secret, domain, cred_type, target_id) VALUES (?, ?, ?, ?, ?)",
        ("admin", "P@ssw0rd!", "CORP", "plaintext", target_id),
    )
    db.commit()


def _seed_findings(db: sqlite3.Connection, target_id: int) -> None:
    db.execute(
        "INSERT INTO findings (title, severity, description, target_id) VALUES (?, ?, ?, ?)",
        ("Weak Admin Password", "critical", "Admin password is easily guessable", target_id),
    )
    db.execute(
        "INSERT INTO findings (title, severity, description, target_id) VALUES (?, ?, ?, ?)",
        ("Unquoted Service Path", "high", "Service path allows hijacking", target_id),
    )
    db.commit()


class TestParseTimestamp:
    def test_standard_format(self) -> None:
        dt = _parse_ts("2026-05-28 14:30:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 5

    def test_iso_format(self) -> None:
        dt = _parse_ts("2026-05-28T14:30:00Z")
        assert dt is not None

    def test_empty_returns_none(self) -> None:
        assert _parse_ts("") is None

    def test_garbage_returns_none(self) -> None:
        assert _parse_ts("not-a-date") is None


class TestRedactCredential:
    def test_secret_redacted(self) -> None:
        row = {"id": 1, "username": "admin", "secret": "P@ssw0rd!", "domain": "CORP"}
        redacted = _redact_credential(row)
        assert redacted["secret"] == REDACTED_SECRET
        assert redacted["username"] == "admin"

    def test_no_secret_field(self) -> None:
        row = {"id": 1, "username": "admin"}
        redacted = _redact_credential(row)
        assert "secret" not in redacted


class TestFetchFunctions:
    def test_fetch_targets(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        targets = _fetch_targets(reporting_db)
        assert len(targets) == 2
        assert targets[0]["hostname"] == "DC01"

    def test_fetch_credentials_redacted(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_credentials(reporting_db, ids[0])
        creds = _fetch_credentials(reporting_db)
        assert len(creds) == 1
        assert creds[0]["secret"] == REDACTED_SECRET

    def test_fetch_findings(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_findings(reporting_db, ids[0])
        findings = _fetch_findings(reporting_db)
        assert len(findings) == 2

    def test_fetch_pivot_paths_empty(self, reporting_db: sqlite3.Connection) -> None:
        pivots = _fetch_pivot_paths(reporting_db)
        assert pivots == []


class TestBuildTimeline:
    def test_empty_db(self, reporting_db: sqlite3.Connection) -> None:
        entries = _build_timeline_entries(reporting_db)
        assert entries == []

    def test_with_access_log(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        reporting_db.execute(
            "INSERT INTO access_log (session_id, target_id, method, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            ("sess-1", ids[0], "sliver_shell", "active", "2026-05-28 10:00:00"),
        )
        reporting_db.commit()
        entries = _build_timeline_entries(reporting_db)
        assert len(entries) >= 1
        assert entries[0]["session_id"] == "sess-1"

    def test_session_filter(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        reporting_db.execute(
            "INSERT INTO access_log (session_id, target_id, method, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            ("sess-A", ids[0], "sliver_shell", "active", "2026-05-28 10:00:00"),
        )
        reporting_db.execute(
            "INSERT INTO access_log (session_id, target_id, method, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            ("sess-B", ids[1], "sliver_ps", "active", "2026-05-28 10:05:00"),
        )
        reporting_db.commit()
        entries = _build_timeline_entries(reporting_db, session_id="sess-A")
        assert all(e["session_id"] == "sess-A" for e in entries)


class TestEngagementDuration:
    def test_no_data_returns_unknown(self, reporting_db: sqlite3.Connection) -> None:
        result = _engagement_duration(reporting_db)
        assert result["started_at"] == "unknown"
        assert result["ended_at"]

    def test_with_meta(self, reporting_db: sqlite3.Connection) -> None:
        reporting_db.execute(
            "INSERT INTO engagement_meta (key, value) VALUES (?, ?)",
            ("started_at", "2026-05-28 08:00:00"),
        )
        reporting_db.commit()
        result = _engagement_duration(reporting_db)
        assert result["started_at"] == "2026-05-28 08:00:00"
        assert result["duration_hours"] is not None
        assert result["duration_hours"] > 0


class TestBuildReportPayload:
    def test_empty_db_report(self, reporting_db: sqlite3.Connection) -> None:
        payload = _build_report_payload(reporting_db)
        assert "watermark" in payload
        assert payload["watermark"] == REPORT_WATERMARK
        assert payload["executive_summary"]["scope"]["targets"] == 0

    def test_populated_report(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_credentials(reporting_db, ids[0])
        _seed_findings(reporting_db, ids[0])
        payload = _build_report_payload(reporting_db)
        assert payload["executive_summary"]["scope"]["targets"] == 2
        assert payload["executive_summary"]["scope"]["credentials"] == 1
        assert payload["executive_summary"]["key_findings_count"] == 2
        for cred in payload["credentials"]:
            assert cred["secret"] == REDACTED_SECRET

    def test_recommendations_present(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_findings(reporting_db, ids[0])
        payload = _build_report_payload(reporting_db)
        assert len(payload["recommendations"]) > 0


class TestReportToMarkdown:
    def test_markdown_structure(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_findings(reporting_db, ids[0])
        payload = _build_report_payload(reporting_db)
        md = _report_to_markdown(payload)
        assert "# Engagement Report" in md
        assert "## Executive Summary" in md
        assert "## Timeline" in md
        assert "## MITRE ATT&CK Coverage" in md
        assert "## Targets" in md
        assert "## Findings by Severity" in md
        assert "## Recommendations" in md
        assert REPORT_WATERMARK in md

    def test_credentials_always_redacted_in_markdown(self, reporting_db: sqlite3.Connection) -> None:
        ids = _seed_targets(reporting_db)
        _seed_credentials(reporting_db, ids[0])
        payload = _build_report_payload(reporting_db)
        md = _report_to_markdown(payload)
        assert "P@ssw0rd!" not in md
        assert REDACTED_SECRET in md


class TestSliverGenerateReport:
    @pytest.mark.asyncio
    async def test_markdown_format(self, reporting_db: sqlite3.Connection) -> None:
        from sliver_mcp.tools.reporting import sliver_generate_report

        with patch("sliver_mcp.tools.reporting._get_state_db", return_value=reporting_db):
            result = json.loads(await sliver_generate_report("markdown"))
        assert result["status"] == ToolStatus.SUCCESS.value
        assert "report" in result["data"]
        assert "# Engagement Report" in result["data"]["report"]

    @pytest.mark.asyncio
    async def test_json_format(self, reporting_db: sqlite3.Connection) -> None:
        from sliver_mcp.tools.reporting import sliver_generate_report

        with patch("sliver_mcp.tools.reporting._get_state_db", return_value=reporting_db):
            result = json.loads(await sliver_generate_report("json"))
        assert result["status"] == ToolStatus.SUCCESS.value
        assert result["data"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_invalid_format(self, reporting_db: sqlite3.Connection) -> None:
        from sliver_mcp.tools.reporting import sliver_generate_report

        with patch("sliver_mcp.tools.reporting._get_state_db", return_value=reporting_db):
            result = json.loads(await sliver_generate_report("xml"))
        assert result["status"] == ToolStatus.ERROR.value


class TestSliverEngagementTimeline:
    @pytest.mark.asyncio
    async def test_empty_timeline(self, reporting_db: sqlite3.Connection) -> None:
        from sliver_mcp.tools.reporting import sliver_engagement_timeline

        with patch("sliver_mcp.tools.reporting._get_state_db", return_value=reporting_db):
            result = json.loads(await sliver_engagement_timeline())
        assert result["status"] == ToolStatus.SUCCESS.value
        assert result["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_negative_hours_rejected(self, reporting_db: sqlite3.Connection) -> None:
        from sliver_mcp.tools.reporting import sliver_engagement_timeline

        with patch("sliver_mcp.tools.reporting._get_state_db", return_value=reporting_db):
            result = json.loads(await sliver_engagement_timeline(hours=-1))
        assert result["status"] == ToolStatus.ERROR.value
