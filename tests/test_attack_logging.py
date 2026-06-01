"""Tests for sliver_mcp.tools.attack_mapping (log_technique, coverage)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sliver_mcp.tools.attack_mapping import (
    _build_registry_index,
    _get_state_db,
    _normalize_outcome,
    _query_technique_sets,
    _resolve_target_id,
    log_technique,
)
from sdk.types import TechniqueOutcome


@pytest.fixture
def attack_db(tmp_path: Path) -> sqlite3.Connection:
    """Create a fresh attack_techniques database."""
    db_path = str(tmp_path / "attack_test.db")
    with patch("sliver_mcp.tools.attack_mapping.resolve_state_db_path", return_value=db_path):
        import sliver_mcp.tools.attack_mapping as mod
        mod._state_db = None
        db = _get_state_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            target_id INTEGER,
            method TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            timestamp TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit()
    yield db
    db.close()
    import sliver_mcp.tools.attack_mapping as mod
    mod._state_db = None


class TestNormalizeOutcome:
    @pytest.mark.parametrize("raw,expected", [
        ("ok", TechniqueOutcome.SUCCESS.value),
        ("success", TechniqueOutcome.SUCCESS.value),
        ("SUCCESS", TechniqueOutcome.SUCCESS.value),
        ("error", TechniqueOutcome.FAILURE.value),
        ("failure", TechniqueOutcome.FAILURE.value),
        ("blocked", TechniqueOutcome.BLOCKED.value),
        ("unknown", TechniqueOutcome.UNKNOWN.value),
        ("", TechniqueOutcome.UNKNOWN.value),
        ("garbage", TechniqueOutcome.UNKNOWN.value),
    ])
    def test_normalize(self, raw: str, expected: str) -> None:
        assert _normalize_outcome(raw) == expected


class TestLogTechnique:
    def test_logs_known_tool(self, attack_db: sqlite3.Connection) -> None:
        row_ids = log_technique(attack_db, "sliver_execute", "sess-1", None, "ok")
        assert len(row_ids) > 0
        rows = attack_db.execute("SELECT * FROM attack_techniques").fetchall()
        assert len(rows) == len(row_ids)
        for row in rows:
            assert row["tool_name"] == "sliver_execute"
            assert row["outcome"] == TechniqueOutcome.SUCCESS.value

    def test_unknown_tool_returns_empty(self, attack_db: sqlite3.Connection) -> None:
        row_ids = log_technique(attack_db, "nonexistent_tool", "sess-1", None, "ok")
        assert row_ids == []
        rows = attack_db.execute("SELECT * FROM attack_techniques").fetchall()
        assert len(rows) == 0

    def test_resolves_target_from_access_log(self, attack_db: sqlite3.Connection) -> None:
        attack_db.execute(
            "INSERT INTO access_log (session_id, target_id, method) VALUES (?, ?, ?)",
            ("sess-42", 7, "sliver_shell"),
        )
        attack_db.commit()
        row_ids = log_technique(attack_db, "sliver_execute", "sess-42", None, "ok")
        assert len(row_ids) > 0
        row = attack_db.execute(
            "SELECT target_id FROM attack_techniques WHERE id = ?", (row_ids[0],)
        ).fetchone()
        assert row["target_id"] == 7

    def test_explicit_target_id_used(self, attack_db: sqlite3.Connection) -> None:
        row_ids = log_technique(attack_db, "sliver_execute", "sess-1", 99, "ok")
        row = attack_db.execute(
            "SELECT target_id FROM attack_techniques WHERE id = ?", (row_ids[0],)
        ).fetchone()
        assert row["target_id"] == 99


class TestResolveTargetId:
    def test_returns_none_when_no_access_log(self, attack_db: sqlite3.Connection) -> None:
        assert _resolve_target_id(attack_db, "nonexistent") is None

    def test_returns_none_for_empty_session(self, attack_db: sqlite3.Connection) -> None:
        assert _resolve_target_id(attack_db, "") is None

    def test_returns_most_recent(self, attack_db: sqlite3.Connection) -> None:
        attack_db.execute(
            "INSERT INTO access_log (session_id, target_id) VALUES (?, ?)",
            ("sess-1", 10),
        )
        attack_db.execute(
            "INSERT INTO access_log (session_id, target_id) VALUES (?, ?)",
            ("sess-1", 20),
        )
        attack_db.commit()
        assert _resolve_target_id(attack_db, "sess-1") == 20


class TestBuildRegistryIndex:
    def test_structure(self) -> None:
        index = _build_registry_index()
        assert isinstance(index, dict)
        assert len(index) > 0
        for tactic, techniques in index.items():
            assert isinstance(tactic, str)
            for tid, meta in techniques.items():
                assert tid.startswith("T")
                assert "name" in meta
                assert "tools" in meta
                assert len(meta["tools"]) > 0


class TestQueryTechniqueSets:
    def test_empty_db(self, attack_db: sqlite3.Connection) -> None:
        exercised, failed, all_attempted = _query_technique_sets(attack_db, "")
        assert exercised == set()
        assert failed == set()
        assert all_attempted == set()

    def test_with_data(self, attack_db: sqlite3.Connection) -> None:
        attack_db.execute(
            "INSERT INTO attack_techniques (technique_id, tactic, name, tool_name, outcome) VALUES (?, ?, ?, ?, ?)",
            ("T1059", "Execution", "Command Interpreter", "sliver_execute", "success"),
        )
        attack_db.execute(
            "INSERT INTO attack_techniques (technique_id, tactic, name, tool_name, outcome) VALUES (?, ?, ?, ?, ?)",
            ("T1082", "Discovery", "System Info", "sliver_info", "failure"),
        )
        attack_db.commit()

        exercised, failed, all_attempted = _query_technique_sets(attack_db, "")
        assert "T1059" in exercised
        assert "T1082" in failed
        assert "T1059" in all_attempted
        assert "T1082" in all_attempted

    def test_session_filter(self, attack_db: sqlite3.Connection) -> None:
        attack_db.execute(
            "INSERT INTO attack_techniques (technique_id, tactic, name, tool_name, session_id, outcome) VALUES (?, ?, ?, ?, ?, ?)",
            ("T1059", "Execution", "Cmd", "sliver_execute", "sess-A", "success"),
        )
        attack_db.execute(
            "INSERT INTO attack_techniques (technique_id, tactic, name, tool_name, session_id, outcome) VALUES (?, ?, ?, ?, ?, ?)",
            ("T1082", "Discovery", "Info", "sliver_info", "sess-B", "success"),
        )
        attack_db.commit()

        exercised, _, _ = _query_technique_sets(attack_db, "sess-A")
        assert "T1059" in exercised
        assert "T1082" not in exercised
