"""MCP resource providers (FEAT-3).

Functions return UTF-8 JSON strings for registration as MCP resources:
``sliver://sessions``, ``sliver://state/summary``, ``sliver://attack-surface``.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from typing import Any

from sdk.errors import StateDBError

from sliver_mcp.tools.attack_mapping import _query_technique_sets
from sliver_mcp.tools.reporting import (
    _build_coverage_section,
    _fetch_targets,
    _get_state_db,
)

logger = logging.getLogger("sliver_mcp.resources")


def _json_resource(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def _error_resource(message: str, hints: list[str] | None = None) -> str:
    return _json_resource({"error": message, "hints": hints or []})


def _retry_db_read(fn: Any, retries: int = 2) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            last_exc = exc
            if "locked" not in str(exc).lower() or attempt >= retries:
                raise
    if last_exc:
        raise last_exc
    return None


async def get_sessions_resource() -> str:
    """Return current Sliver session list as JSON (``sliver://sessions``).

    Live query against the teamserver; no auto-registration side effects.
    """
    try:
        from server import _get_client, _infer_access_level, _session_object_to_dict  # noqa: PLC0415

        client = await _get_client()
        sessions = await client.sessions()
        rows = [_session_object_to_dict(s) for s in sessions]
        for row, s in zip(rows, sessions):
            row["privilege_level"] = _infer_access_level(getattr(s, "Username", "") or "")
        return _json_resource({
            "count": len(rows),
            "sessions": rows,
            "refreshed_at": _utc_now(),
        })
    except Exception as exc:
        logger.warning("sessions resource failed: %s", exc)
        return _error_resource(
            str(exc),
            hints=[
                "Ensure the Sliver teamserver is running.",
                "Verify SLIVER_CONFIG points to a valid operator config.",
                "Retry after sliver_reconnect if the gRPC channel is stale.",
            ],
        )


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def get_state_summary_resource() -> str:
    """Return engagement dashboard counts (``sliver://state/summary``).

    Aggregates targets, credentials, findings, access events, pivots,
    active sessions, and ATT&CK coverage. Never includes credential secrets.
    """
    def _build() -> dict[str, Any]:
        db = _get_state_db()
        targets_total = db.execute("SELECT COUNT(*) AS c FROM targets").fetchone()["c"]
        targets_elevated = db.execute(
            "SELECT COUNT(*) AS c FROM targets WHERE access_level IN ('admin', 'system')"
        ).fetchone()["c"]
        creds = db.execute("SELECT COUNT(*) AS c FROM credentials").fetchone()["c"]
        findings_total = db.execute("SELECT COUNT(*) AS c FROM findings").fetchone()["c"]
        by_severity: dict[str, int] = {}
        for row in db.execute(
            "SELECT severity, COUNT(*) AS c FROM findings GROUP BY severity"
        ).fetchall():
            by_severity[row["severity"] or "info"] = row["c"]
        accesses = db.execute("SELECT COUNT(*) AS c FROM access_log").fetchone()["c"]
        active_access = db.execute(
            "SELECT COUNT(*) AS c FROM access_log WHERE status = 'active'"
        ).fetchone()["c"]
        pivots = db.execute("SELECT COUNT(*) AS c FROM pivot_paths").fetchone()["c"]
        coverage = _build_coverage_section(db)
        exercised, _, _ = _query_technique_sets(db, "")
        return {
            "refreshed_at": _utc_now(),
            "targets": {"total": targets_total, "admin_or_system": targets_elevated},
            "credentials": {"total": creds},
            "findings": {"total": findings_total, "by_severity": by_severity},
            "access_events": {"total": accesses, "active": active_access},
            "pivot_paths": {"total": pivots},
            "attack_techniques": {"distinct_exercised": len(exercised)},
            "attack_coverage_percent": coverage.get("summary", {}).get("coverage_percent", 0.0),
            "active_sessions": None,
        }

    try:
        summary = _retry_db_read(_build)
        try:
            from server import _get_client  # noqa: PLC0415

            client = await _get_client()
            summary["active_sessions"] = len(await client.sessions())
        except Exception as exc:
            summary["active_sessions"] = None
            summary["sessions_error"] = str(exc)
        return _json_resource(summary)
    except StateDBError as exc:
        return _error_resource(str(exc), hints=exc.hints)
    except sqlite3.OperationalError as exc:
        return _error_resource(f"State database busy: {exc}", hints=["Retry resource read."])
    except Exception as exc:
        logger.warning("state summary resource failed: %s", exc)
        return _error_resource(str(exc))


async def get_attack_surface_resource() -> str:
    """Return discovered targets with ports and services (``sliver://attack-surface``).

    Reads ``targets`` and ``target_services`` from the engagement state DB.
    """
    def _build() -> dict[str, Any]:
        db = _get_state_db()
        targets = _fetch_targets(db)
        services_by_target: dict[int, list[dict[str, Any]]] = defaultdict(list)
        try:
            for row in db.execute(
                "SELECT * FROM target_services ORDER BY target_id, port"
            ).fetchall():
                rec = dict(row)
                services_by_target[rec["target_id"]].append({
                    "port": rec.get("port"),
                    "protocol": rec.get("protocol", "tcp"),
                    "service_name": rec.get("service_name", ""),
                    "state": rec.get("state", "open"),
                    "banner": rec.get("banner", ""),
                    "discovered_at": rec.get("discovered_at", ""),
                })
        except sqlite3.Error:
            pass

        surface = []
        for t in targets:
            tid = t.get("id")
            surface.append({
                "hostname": t.get("hostname", ""),
                "ip": t.get("ip", ""),
                "os": t.get("os", ""),
                "domain": t.get("domain", ""),
                "access_level": t.get("access_level", "unknown"),
                "services": services_by_target.get(tid, []) if tid else [],
            })
        return {"targets": surface, "count": len(surface), "refreshed_at": _utc_now()}

    try:
        payload = _retry_db_read(_build)
        return _json_resource(payload)
    except StateDBError as exc:
        return _error_resource(str(exc), hints=exc.hints)
    except sqlite3.OperationalError as exc:
        return _error_resource(f"State database busy: {exc}")
    except Exception as exc:
        logger.warning("attack-surface resource failed: %s", exc)
        return _error_resource(str(exc))
