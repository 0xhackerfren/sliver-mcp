"""MITRE ATT&CK coverage and technique logging (FEAT-1).

Provides ``sliver_attack_coverage`` and ``log_technique`` for the
``@tool_handler`` decorator to persist technique executions.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from typing import Any

from sdk.attack_map import ATTACK_REGISTRY, get_techniques_for_tool
from sdk.errors import StateDBError, ValidationError
from sdk.types import (
    AttackCoverageMatrix,
    TacticCoverage,
    TechniqueOutcome,
    ToolResponse,
    ToolStatus,
)
from sdk.validators import validate_session_id

from sliver_mcp.config import resolve_state_db_path

logger = logging.getLogger("sliver_mcp.attack")

_ATTACK_TECHNIQUES_DDL = """
CREATE TABLE IF NOT EXISTS attack_techniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technique_id TEXT NOT NULL,
    tactic TEXT NOT NULL,
    name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    session_id TEXT DEFAULT '',
    target_id INTEGER,
    outcome TEXT DEFAULT 'unknown',
    evidence TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attack_techniques_tactic
    ON attack_techniques(tactic);
CREATE INDEX IF NOT EXISTS idx_attack_techniques_session
    ON attack_techniques(session_id);
CREATE INDEX IF NOT EXISTS idx_attack_techniques_technique
    ON attack_techniques(technique_id);
"""

_state_db: sqlite3.Connection | None = None


def _get_state_db() -> sqlite3.Connection:
    """Return (and lazily create) the engagement state SQLite connection."""
    global _state_db
    if _state_db is not None:
        return _state_db
    db_path = resolve_state_db_path()
    try:
        _state_db = sqlite3.connect(db_path, check_same_thread=False)
    except sqlite3.Error as exc:
        raise StateDBError(f"Cannot open state database at {db_path}: {exc}") from exc
    _state_db.row_factory = sqlite3.Row
    _state_db.execute("PRAGMA journal_mode=WAL")
    _state_db.executescript(_ATTACK_TECHNIQUES_DDL)
    _state_db.commit()
    return _state_db


def _normalize_outcome(outcome: str) -> str:
    """Map assorted outcome strings to TechniqueOutcome values."""
    raw = (outcome or "").strip().lower()
    mapping = {
        "ok": TechniqueOutcome.SUCCESS.value,
        "success": TechniqueOutcome.SUCCESS.value,
        "error": TechniqueOutcome.FAILURE.value,
        "failure": TechniqueOutcome.FAILURE.value,
        "fail": TechniqueOutcome.FAILURE.value,
        "blocked": TechniqueOutcome.BLOCKED.value,
        "unknown": TechniqueOutcome.UNKNOWN.value,
    }
    return mapping.get(raw, TechniqueOutcome.UNKNOWN.value)


def _resolve_target_id(
    db_conn: sqlite3.Connection,
    session_id: str,
) -> int | None:
    """Resolve target_id from the most recent access_log row for the session."""
    if not session_id:
        return None
    try:
        row = db_conn.execute(
            """
            SELECT target_id FROM access_log
            WHERE session_id = ? AND target_id IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row and row["target_id"] is not None:
            return int(row["target_id"])
    except sqlite3.Error:
        pass
    return None


def log_technique(
    db_conn: sqlite3.Connection,
    tool_name: str,
    session_id: str,
    target_id: int | None,
    outcome: str,
) -> list[int]:
    """Log ATT&CK technique execution(s) for a tool invocation.

    Inserts one row per technique mapped to ``tool_name`` in the static
    registry. Called by the ``@tool_handler`` decorator after each tool run.

    Args:
        db_conn: Open SQLite connection to the engagement state DB.
        tool_name: MCP tool name (e.g. ``sliver_execute``).
        session_id: Active session ID, if any.
        target_id: Optional FK to ``targets.id``; resolved when omitted.
        outcome: Invocation outcome (``ok``, ``success``, ``error``, ``blocked``, etc.).

    Returns:
        List of inserted row IDs (empty when the tool has no registry mapping).
    """
    mappings = get_techniques_for_tool(tool_name)
    if not mappings:
        logger.debug("No ATT&CK mapping for tool %s", tool_name)
        return []

    resolved_target = target_id
    if resolved_target is None and session_id:
        resolved_target = _resolve_target_id(db_conn, session_id)

    outcome_val = _normalize_outcome(outcome)
    row_ids: list[int] = []

    for mapping in mappings:
        try:
            cur = db_conn.execute(
                """
                INSERT INTO attack_techniques (
                    technique_id, tactic, name, tool_name,
                    session_id, target_id, outcome
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping.technique_id,
                    mapping.tactic,
                    mapping.name,
                    tool_name,
                    session_id or "",
                    resolved_target,
                    outcome_val,
                ),
            )
            row_ids.append(int(cur.lastrowid))
        except sqlite3.Error as exc:
            logger.warning(
                "Failed to log technique %s for %s: %s",
                mapping.technique_id,
                tool_name,
                exc,
            )
    if row_ids:
        db_conn.commit()
    return row_ids


def _build_registry_index() -> dict[str, dict[str, dict[str, Any]]]:
    """Build tactic -> technique_id -> metadata from the static registry."""
    index: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for tool_name, mappings in ATTACK_REGISTRY.items():
        for m in mappings:
            entry = index[m.tactic].setdefault(
                m.technique_id,
                {"name": m.name, "tools": []},
            )
            if tool_name not in entry["tools"]:
                entry["tools"].append(tool_name)
    return dict(index)


def _query_technique_sets(
    db: sqlite3.Connection,
    session_id: str,
) -> tuple[set[str], set[str], set[str]]:
    """Return (exercised, attempted_failed, all_attempted) technique ID sets."""
    params: list[str] = []
    where = ""
    if session_id:
        where = "WHERE session_id = ?"
        params.append(session_id)

    exercised: set[str] = set()
    attempted_failed: set[str] = set()
    all_attempted: set[str] = set()

    try:
        rows = db.execute(
            f"""
            SELECT technique_id, outcome
            FROM attack_techniques
            {where}
            """,
            params,
        ).fetchall()
    except sqlite3.Error as exc:
        raise StateDBError(f"Failed to query attack_techniques: {exc}") from exc

    for row in rows:
        tid = row["technique_id"]
        if not tid:
            continue
        all_attempted.add(tid)
        outcome = (row["outcome"] or "").lower()
        if outcome == TechniqueOutcome.SUCCESS.value:
            exercised.add(tid)
        elif outcome in (
            TechniqueOutcome.FAILURE.value,
            TechniqueOutcome.BLOCKED.value,
        ):
            attempted_failed.add(tid)

    return exercised, attempted_failed, all_attempted


def _coverage_matrix_to_dict(
    matrix: AttackCoverageMatrix,
    attempted_failed: set[str],
) -> dict[str, Any]:
    """Serialize AttackCoverageMatrix for ToolResponse.data."""
    coverage: dict[str, Any] = {}
    for tc in matrix.tactics:
        coverage[tc.tactic] = {
            "available": sorted(tc.available),
            "exercised": sorted(tc.exercised),
            "attempted_failed": sorted(set(tc.available) & attempted_failed),
            "gap": sorted(tc.gap),
        }
    return {
        "coverage": coverage,
        "summary": {
            "total_available": matrix.total_available,
            "total_exercised": matrix.total_exercised,
            "coverage_percent": round(matrix.coverage_pct, 2),
        },
    }


async def sliver_attack_coverage(session_id: str = "") -> str:
    """Return ATT&CK coverage matrix for the engagement.

    Compares the static technique registry against logged executions in
    the ``attack_techniques`` state table. Optionally filters exercised
    techniques to a single session.

    Args:
        session_id: Optional session ID filter. When empty, coverage reflects
            the full engagement. When set, only techniques exercised on that
            session count toward ``exercised`` (available set is unchanged).

    Returns:
        JSON ``ToolResponse`` with per-tactic breakdown, overall coverage
        percentage, and gap analysis (techniques not yet successfully exercised).
    """
    if not ATTACK_REGISTRY:
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error="ATTACK registry is empty",
            error_type="ATTACK_REGISTRY_EMPTY",
            hints=[
                "Verify sdk/attack_map.py ATTACK_REGISTRY is populated",
                "Check server startup logs for registry load errors",
            ],
        )
        return json.dumps(resp.to_json(), indent=2)

    filter_session = ""
    if session_id and session_id.strip():
        try:
            filter_session = validate_session_id(session_id.strip())
        except ValidationError as exc:
            resp = ToolResponse(
                status=ToolStatus.ERROR,
                error=str(exc),
                error_type="ValidationError",
                hints=exc.hints,
            )
            return json.dumps(resp.to_json(), indent=2)

    try:
        db = _get_state_db()
        registry_index = _build_registry_index()
        exercised, attempted_failed, _ = _query_technique_sets(db, filter_session)

        tactic_coverages: list[TacticCoverage] = []
        all_available: set[str] = set()
        all_exercised: set[str] = set()

        for tactic in sorted(registry_index.keys()):
            tech_meta = registry_index[tactic]
            available_ids = sorted(tech_meta.keys())
            exercised_ids = sorted(set(available_ids) & exercised)
            gap_ids = sorted(set(available_ids) - set(exercised_ids))

            all_available.update(available_ids)
            all_exercised.update(exercised_ids)

            tactic_coverages.append(
                TacticCoverage(
                    tactic=tactic,
                    available=available_ids,
                    exercised=exercised_ids,
                    gap=gap_ids,
                )
            )

        total_available = len(all_available)
        total_exercised = len(all_exercised)
        coverage_pct = (
            (total_exercised / total_available * 100.0) if total_available else 0.0
        )

        matrix = AttackCoverageMatrix(
            tactics=tactic_coverages,
            total_available=total_available,
            total_exercised=total_exercised,
            coverage_pct=coverage_pct,
        )

        data = _coverage_matrix_to_dict(matrix, attempted_failed)
        if filter_session:
            data["session_filter"] = filter_session

        gap_all = sorted(all_available - all_exercised)
        data["gap_analysis"] = {
            "techniques_not_attempted": gap_all,
            "count": len(gap_all),
        }
        if attempted_failed:
            data["attempted_failed_global"] = sorted(
                all_available & attempted_failed
            )

        resp = ToolResponse(status=ToolStatus.SUCCESS, data=data)
        return json.dumps(resp.to_json(), indent=2)

    except StateDBError as exc:
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error=str(exc),
            error_type="StateDBError",
            hints=exc.hints,
        )
        return json.dumps(resp.to_json(), indent=2)
    except Exception as exc:
        from server import _format_tool_error  # noqa: PLC0415

        return _format_tool_error(
            "sliver_attack_coverage",
            exc,
            session_id=filter_session,
            hints=["Ensure SLIVER_STATE_DB is writable and not locked."],
        )
