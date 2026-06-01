"""Multi-session orchestration tools (FEAT-2).

Fan-out execution, session ranking, and pivot path discovery across
active Sliver sessions.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import shlex
import time
from typing import Any

from sdk.errors import SessionNotFoundError, ValidationError
from sdk.types import AccessLevel, PivotHop, SessionScore, ToolResponse, ToolStatus
from sdk.validators import (
    safe_shell_split,
    validate_non_empty,
    validate_no_injection,
    validate_session_id,
)

from sliver_mcp.tools.attack_mapping import _get_state_db, log_technique

_PRIVILEGE_SCORES = {
    AccessLevel.SYSTEM.value: 100.0,
    "system": 100.0,
    AccessLevel.ADMIN.value: 70.0,
    "admin": 70.0,
    AccessLevel.USER.value: 30.0,
    "user": 30.0,
    AccessLevel.UNKNOWN.value: 15.0,
    "unknown": 15.0,
    "none": 10.0,
}


def _parse_session_id_list(session_ids: str) -> list[str]:
    """Parse and validate a comma-separated session ID list."""
    raw = validate_non_empty(session_ids, "session_ids")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValidationError("session_ids", session_ids, "no valid session IDs provided")
    return [validate_session_id(sid, "session_id") for sid in parts]


def _decode_execute_output(result: Any) -> str:
    """Extract stdout/stderr text from a Sliver execute result."""
    output_parts: list[str] = []
    stdout = getattr(result, "Stdout", b"")
    stderr = getattr(result, "Stderr", b"")
    if stdout:
        text = stdout if isinstance(stdout, str) else stdout.decode("utf-8", errors="replace")
        output_parts.append(text)
    if stderr:
        text = stderr if isinstance(stderr, str) else stderr.decode("utf-8", errors="replace")
        output_parts.append(f"[stderr]\n{text}")
    return "\n".join(output_parts) if output_parts else "(no output)"


def _infer_privilege(username: str) -> str:
    """Infer privilege level string from a session username."""
    if not username:
        return AccessLevel.UNKNOWN.value
    low = username.lower()
    if "system" in low or "nt authority\\system" in low:
        return AccessLevel.SYSTEM.value
    if "administrator" in low or "admin" in low:
        return AccessLevel.ADMIN.value
    return AccessLevel.USER.value


def _networks_from_addresses(addresses: list[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Derive private network objects from interface address strings."""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in addresses:
        addr = raw.split("%")[0].strip()
        if not addr:
            continue
        try:
            if "/" in addr:
                net = ipaddress.ip_network(addr, strict=False)
                if net.is_private or net.is_link_local:
                    networks.append(net)
                continue
            ip = ipaddress.ip_address(addr)
            if not ip.is_private and not ip.is_link_local:
                continue
            if ip.version == 4:
                networks.append(ipaddress.ip_network(f"{ip}/24", strict=False))
            else:
                networks.append(ipaddress.ip_network(f"{ip}/64", strict=False))
        except ValueError:
            continue
    return networks


def _subnet_label(net: ipaddress.IPv4Network | ipaddress.IPv6Network) -> str:
    return str(net)


def _networks_overlap(
    a: ipaddress.IPv4Network | ipaddress.IPv6Network,
    b: ipaddress.IPv4Network | ipaddress.IPv6Network,
) -> bool:
    if a.version != b.version:
        return False
    try:
        return a.overlaps(b)
    except TypeError:
        return False


async def _fetch_active_sessions() -> tuple[Any, list[Any], set[str]]:
    """Return (client, interactive_sessions, beacon_id_set)."""
    from server import _get_client  # noqa: PLC0415

    client = await _get_client()
    sessions = list(await client.sessions())
    beacons = await client.beacons()
    beacon_ids = {b.ID for b in beacons}
    return client, sessions, beacon_ids


async def _exec_on_session(
    session_id: str,
    exe: str,
    arg_list: list[str],
    *,
    beacon_ids: set[str],
) -> dict[str, Any]:
    """Execute a command on one session; return a per-session result dict."""
    from server import _interact, _opsec_preflight  # noqa: PLC0415

    start = time.monotonic()
    if session_id in beacon_ids:
        return {
            "session_id": session_id,
            "status": "skipped",
            "error": "Beacon sessions are excluded from multi_exec until beacon execution is approved",
            "duration_ms": 0,
        }

    block_msg = await _opsec_preflight(session_id, "sliver_execute")
    if block_msg and "[OPSEC BLOCKED]" in block_msg:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            db = _get_state_db()
            log_technique(db, "sliver_execute", session_id, None, "blocked")
        except Exception:
            pass
        return {
            "session_id": session_id,
            "status": "blocked",
            "error": block_msg,
            "duration_ms": duration_ms,
        }

    try:
        session = await _interact(session_id)
        result = await session.execute(exe, arg_list, output=True)
        output = _decode_execute_output(result)
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            db = _get_state_db()
            log_technique(db, "sliver_execute", session_id, None, "success")
        except Exception:
            pass
        return {
            "session_id": session_id,
            "status": "success",
            "output": output,
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            db = _get_state_db()
            log_technique(db, "sliver_execute", session_id, None, "error")
        except Exception:
            pass
        return {
            "session_id": session_id,
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration_ms": duration_ms,
        }


async def sliver_multi_exec(
    session_ids: str,
    exe: str,
    args: str = "",
) -> str:
    """Fan-out command execution across multiple sessions in parallel.

    Args:
        session_ids: Comma-separated list of session IDs to target.
        exe: Executable or command to run on each session.
        args: Optional space-separated arguments (shell-quoted).

    Returns:
        JSON ``ToolResponse`` with per-session results and aggregate summary.
    """
    try:
        sid_list = _parse_session_id_list(session_ids)
        exe_clean = validate_non_empty(exe, "exe")
        validate_no_injection(exe_clean, "exe")
        arg_list = safe_shell_split(args) if args.strip() else []

        _, sessions, beacon_ids = await _fetch_active_sessions()
        active_ids = {s.ID for s in sessions} | beacon_ids

        tasks = [
            _exec_on_session(sid, exe_clean, arg_list, beacon_ids=beacon_ids)
            for sid in sid_list
        ]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[dict[str, Any]] = []
        for sid, item in zip(sid_list, gathered):
            if isinstance(item, Exception):
                entry: dict[str, Any] = {
                    "session_id": sid,
                    "status": "error",
                    "error": str(item),
                    "error_type": type(item).__name__,
                    "duration_ms": 0,
                }
            else:
                entry = item
            if sid not in active_ids and entry.get("status") != "skipped":
                entry["status"] = "error"
                entry["error"] = f"Session not found: {sid}"
                entry["hints"] = ["Run sliver_sessions to list active session IDs."]
            results.append(entry)

        succeeded = sum(1 for r in results if r.get("status") == "success")
        failed = sum(
            1 for r in results
            if r.get("status") in ("error", "blocked", "skipped")
        )

        resp = ToolResponse(
            status=ToolStatus.SUCCESS,
            data={
                "results": results,
                "summary": {
                    "total": len(results),
                    "succeeded": succeeded,
                    "failed": failed,
                },
            },
            attack_technique="T1059",
        )
        return json.dumps(resp.to_json(), indent=2)

    except ValidationError as exc:
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error=str(exc),
            error_type="ValidationError",
            hints=exc.hints,
        )
        return json.dumps(resp.to_json(), indent=2)
    except SessionNotFoundError as exc:
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error=str(exc),
            error_type="SessionNotFoundError",
            hints=exc.hints,
        )
        return json.dumps(resp.to_json(), indent=2)
    except Exception as exc:
        from server import _format_tool_error  # noqa: PLC0415

        return _format_tool_error(
            "sliver_multi_exec",
            exc,
            context=f"exe={exe!r}",
            hints=["Verify all session IDs with sliver_sessions."],
        )


async def _score_session(
    session: Any,
    criteria: str,
    *,
    edr_count: int,
    edr_unknown: bool,
) -> SessionScore:
    """Compute a session score for the given selection criteria."""
    privilege = _infer_privilege(session.Username or "")
    priv_score = _PRIVILEGE_SCORES.get(privilege, 15.0)
    stealth_score = max(0.0, 100.0 - (edr_count * 25.0))
    if edr_unknown:
        stealth_score = max(0.0, stealth_score - 15.0)

    if criteria == "privilege":
        final = priv_score
    elif criteria == "stealth":
        final = stealth_score
    else:
        final = (priv_score * 0.5) + (stealth_score * 0.35) + (15.0 * 0.15)

    return SessionScore(
        session_id=session.ID,
        score=round(min(100.0, max(0.0, final)), 2),
        factors={
            "criteria": criteria,
            "privilege_level": privilege,
            "privilege_score": round(priv_score, 2),
            "stealth_score": round(stealth_score, 2),
            "edr_products_detected": edr_count,
            "edr_unknown": edr_unknown,
            "hostname": session.Hostname or "",
            "username": session.Username or "",
            "os": session.OS or "",
            "transport": session.Transport or "",
        },
    )


async def sliver_session_select(criteria: str = "auto") -> str:
    """Rank and select the optimal active session.

    Args:
        criteria: Ranking mode — ``privilege`` (highest privilege first),
            ``stealth`` (fewest detected EDR products), or ``auto`` (weighted
            combination of privilege, stealth, and baseline stability).

    Returns:
        JSON ``ToolResponse`` with ordered rankings and recommended session ID.
    """
    mode = (criteria or "auto").strip().lower()
    if mode not in ("privilege", "stealth", "auto"):
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error=f"Invalid criteria: {criteria}",
            error_type="ValidationError",
            hints=["Use one of: privilege, stealth, auto"],
        )
        return json.dumps(resp.to_json(), indent=2)

    try:
        from server import _opsec_scan_session, _session_object_to_dict  # noqa: PLC0415

        _, sessions, beacon_ids = await _fetch_active_sessions()
        interactive = [s for s in sessions if s.ID not in beacon_ids]

        if not interactive:
            resp = ToolResponse(
                status=ToolStatus.SUCCESS,
                data={
                    "recommended_session_id": None,
                    "rankings": [],
                    "message": "No active interactive sessions.",
                    "hints": ["Run sliver_sessions to list implants."],
                },
            )
            return json.dumps(resp.to_json(), indent=2)

        scores: list[SessionScore] = []
        for session in interactive:
            scan = await _opsec_scan_session(session.ID)
            edr_count = len(scan.get("detected", []))
            edr_unknown = bool(scan.get("error"))
            scores.append(
                await _score_session(
                    session,
                    mode,
                    edr_count=edr_count,
                    edr_unknown=edr_unknown,
                )
            )

        scores.sort(key=lambda s: s.score, reverse=True)
        for rank, entry in enumerate(scores, start=1):
            entry.rank = rank

        rankings = [
            {
                "session_id": s.session_id,
                "score": s.score,
                "rank": s.rank,
                "factors": s.factors,
                "session": _session_object_to_dict(
                    next(sess for sess in interactive if sess.ID == s.session_id)
                ),
            }
            for s in scores
        ]

        resp = ToolResponse(
            status=ToolStatus.SUCCESS,
            data={
                "recommended_session_id": scores[0].session_id if scores else None,
                "criteria": mode,
                "rankings": rankings,
            },
        )
        return json.dumps(resp.to_json(), indent=2)

    except Exception as exc:
        from server import _format_tool_error  # noqa: PLC0415

        return _format_tool_error(
            "sliver_session_select",
            exc,
            hints=["Run sliver_sessions and retry."],
        )


async def _collect_ifconfig(session_id: str) -> dict[str, Any]:
    """Run ifconfig on a session and return parsed interface data."""
    from server import _interact  # noqa: PLC0415

    out: dict[str, Any] = {
        "session_id": session_id,
        "interfaces": [],
        "networks": [],
        "error": None,
    }
    try:
        session = await _interact(session_id)
        result = await session.ifconfig()
        ifaces = getattr(result, "NetInterfaces", None) or []
        all_addrs: list[str] = []
        for iface in ifaces:
            addrs = list(getattr(iface, "IPAddresses", []) or [])
            all_addrs.extend(addrs)
            out["interfaces"].append({
                "name": getattr(iface, "Name", ""),
                "index": getattr(iface, "Index", 0),
                "mac": getattr(iface, "MAC", ""),
                "ip_addresses": addrs,
            })
        nets = _networks_from_addresses(all_addrs)
        out["networks"] = [_subnet_label(n) for n in nets]
        out["_network_objects"] = nets
    except Exception as exc:
        out["error"] = str(exc)
        out["_network_objects"] = []
    return out


def _upsert_pivot_path(
    db: Any,
    source_target_id: int | None,
    dest_target_id: int | None,
    method: str,
    status: str,
) -> None:
    """Insert a pivot_paths row when both target IDs are known."""
    if source_target_id is None or dest_target_id is None:
        return
    try:
        db.execute(
            """
            INSERT INTO pivot_paths (source_target_id, dest_target_id, method, status)
            VALUES (?, ?, ?, ?)
            """,
            (source_target_id, dest_target_id, method, status),
        )
        db.commit()
    except Exception:
        pass


def _target_id_for_hostname(db: Any, hostname: str) -> int | None:
    if not hostname:
        return None
    row = db.execute(
        "SELECT id FROM targets WHERE hostname = ?",
        (hostname,),
    ).fetchone()
    return int(row["id"]) if row else None


async def sliver_pivot_chain() -> str:
    """Discover potential pivot paths across all active sessions.

    Collects network interface configuration from each session, builds a
    subnet graph, and identifies overlapping networks that suggest lateral
    pivot opportunities.

    Returns:
        JSON ``ToolResponse`` with topology nodes, pivot hop candidates,
        and high-confidence paths persisted to ``pivot_paths`` when possible.
    """
    try:
        from server import _session_object_to_dict  # noqa: PLC0415

        _, sessions, beacon_ids = await _fetch_active_sessions()
        interactive = [s for s in sessions if s.ID not in beacon_ids]

        if not interactive:
            resp = ToolResponse(
                status=ToolStatus.ERROR,
                error="No active sessions available for pivot analysis",
                error_type="NO_SESSIONS",
                hints=["Run sliver_sessions to establish implants first."],
            )
            return json.dumps(resp.to_json(), indent=2)

        ifconfig_results = await asyncio.gather(
            *[_collect_ifconfig(s.ID) for s in interactive],
            return_exceptions=True,
        )

        session_meta: dict[str, dict[str, Any]] = {}
        topology_nodes: list[dict[str, Any]] = []
        partial = False

        for sess, cfg in zip(interactive, ifconfig_results):
            if isinstance(cfg, Exception):
                partial = True
                cfg = {
                    "session_id": sess.ID,
                    "interfaces": [],
                    "networks": [],
                    "error": str(cfg),
                    "_network_objects": [],
                }
            if cfg.get("error"):
                partial = True
            meta = _session_object_to_dict(sess)
            meta["networks"] = cfg.get("networks", [])
            session_meta[sess.ID] = meta
            for net_label in cfg.get("networks", []):
                topology_nodes.append({
                    "type": "subnet",
                    "subnet": net_label,
                    "session_id": sess.ID,
                    "hostname": sess.Hostname or "",
                })
            topology_nodes.append({
                "type": "session",
                "session_id": sess.ID,
                "hostname": sess.Hostname or "",
                "username": sess.Username or "",
            })

        pivot_hops: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        db = _get_state_db()

        cfg_by_session: dict[str, dict[str, Any]] = {}
        for sess, cfg in zip(interactive, ifconfig_results):
            if isinstance(cfg, Exception):
                cfg_by_session[sess.ID] = {
                    "session_id": sess.ID,
                    "interfaces": [],
                    "networks": [],
                    "error": str(cfg),
                    "_network_objects": [],
                }
            else:
                cfg_by_session[sess.ID] = cfg

        sid_list = list(session_meta.keys())
        for i, src_id in enumerate(sid_list):
            src_cfg = cfg_by_session.get(src_id)
            if not src_cfg:
                continue
            src_nets: list[Any] = src_cfg.get("_network_objects", [])
            src_sess = next(s for s in interactive if s.ID == src_id)

            for dst_id in sid_list[i + 1:]:
                dst_cfg = cfg_by_session.get(dst_id)
                if not dst_cfg:
                    continue
                dst_nets = dst_cfg.get("_network_objects", [])
                dst_sess = next(s for s in interactive if s.ID == dst_id)

                shared: list[str] = []
                for sn in src_nets:
                    for dn in dst_nets:
                        if _networks_overlap(sn, dn):
                            label = _subnet_label(sn)
                            if label not in shared:
                                shared.append(label)

                if not shared:
                    continue

                via = shared[0]
                confidence = "high" if len(shared) >= 2 else "medium"
                dest_ip = ""
                dst_addrs: list[str] = []
                for iface in dst_cfg.get("interfaces", []):
                    dst_addrs.extend(iface.get("ip_addresses", []))
                if dst_addrs:
                    dest_ip = dst_addrs[0].split("%")[0]

                hop = PivotHop(
                    source_session_id=src_id,
                    dest_target_ip=dest_ip,
                    via_subnet=via,
                    confidence=confidence,
                )
                hop_dict = {
                    "source_session_id": hop.source_session_id,
                    "dest_session_id": dst_id,
                    "dest_target_ip": hop.dest_target_ip,
                    "via_subnet": hop.via_subnet,
                    "confidence": hop.confidence,
                    "shared_subnets": shared,
                }
                pivot_hops.append(hop_dict)
                edges.append({
                    "source": src_id,
                    "destination": dst_id,
                    "via_subnet": via,
                    "confidence": confidence,
                })

                if confidence == "high":
                    src_tid = _target_id_for_hostname(db, src_sess.Hostname or "")
                    dst_tid = _target_id_for_hostname(db, dst_sess.Hostname or "")
                    _upsert_pivot_path(
                        db,
                        src_tid,
                        dst_tid,
                        "inferred_topology",
                        "planned",
                    )

        resp = ToolResponse(
            status=ToolStatus.SUCCESS,
            data={
                "partial": partial,
                "topology": {
                    "nodes": topology_nodes,
                    "edges": edges,
                },
                "sessions": list(session_meta.values()),
                "pivot_hops": pivot_hops,
                "pivot_hop_count": len(pivot_hops),
            },
        )
        return json.dumps(resp.to_json(), indent=2)

    except Exception as exc:
        from server import _format_tool_error  # noqa: PLC0415

        return _format_tool_error(
            "sliver_pivot_chain",
            exc,
            hints=["Ensure sessions are active and network tools are permitted."],
        )
