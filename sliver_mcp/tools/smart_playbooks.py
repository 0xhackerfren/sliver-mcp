"""Smart playbooks and deterministic next-action advisor (FEAT-5).

Provides ``sliver_playbook_ad_enum``, ``sliver_playbook_network_sweep``,
and ``sliver_suggest_next``.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import shlex
from typing import Any

from sdk.attack_map import ATTACK_REGISTRY
from sdk.errors import SessionNotFoundError, StateDBError, ValidationError
from sdk.types import (
    FindingSeverity,
    PlaybookStatus,
    RecommendedAction,
    ToolResponse,
    ToolStatus,
)
from sdk.validators import validate_cidr, validate_session_id

from sliver_mcp.tools.attack_mapping import log_technique
from sliver_mcp.tools.reporting import _get_state_db as _ensure_reporting_schema

logger = logging.getLogger("sliver_mcp.playbooks")

DEFAULT_SWEEP_PORTS = (445, 3389, 5985, 22, 80, 443)
STEP_TIMEOUT_SEC = 120

_AD_STEPS: list[tuple[str, str, str, list[str]]] = [
    ("domain_trust", "nltest", "/domain_trusts", ["T1482"]),
    ("whoami_groups", "whoami", "/groups", ["T1069.002"]),
    ("domain_admins", "net", 'group "Domain Admins" /domain', ["T1069.002"]),
    ("domain_controllers", "net", 'group "Domain Controllers" /domain', ["T1087.002"]),
    ("cert_authorities", "certutil", "-dump", ["T1649"]),
    ("group_policy", "gpresult", "/r", ["T1615"]),
    ("services", "wmic", "service get name,displayname,startmode,pathname", ["T1007"]),
]


def _success(data: dict[str, Any]) -> str:
    return json.dumps(ToolResponse(status=ToolStatus.SUCCESS, data=data).to_json(), indent=2, default=str)


def _error(tool: str, exc: Exception) -> str:
    if isinstance(exc, (ValidationError, SessionNotFoundError, StateDBError)):
        resp = ToolResponse(
            status=ToolStatus.ERROR,
            error=str(exc),
            error_type=type(exc).__name__,
            hints=getattr(exc, "hints", []),
        )
        return json.dumps(resp.to_json(), indent=2)
    from server import _format_tool_error  # noqa: PLC0415

    return _format_tool_error(tool, exc)


async def _interact(session_id: str) -> Any:
    from server import _interact as server_interact  # noqa: PLC0415

    return await server_interact(session_id)


async def _exec_step(session_id: str, exe: str, args: str = "") -> tuple[str, bool]:
    """Run a command; return (output, success)."""
    try:
        session = await _interact(session_id)
        arg_list = shlex.split(args) if args else []
        result = await session.execute(exe, arg_list, output=True)
        stdout = getattr(result, "Stdout", b"")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        text = (stdout or "").strip()
        failed = "(error:" in text.lower() or "access is denied" in text.lower()
        return text, not failed
    except Exception as exc:
        return f"(error: {exc})", False


async def _verify_session(session_id: str) -> Any:
    from server import _get_client  # noqa: PLC0415

    client = await _get_client()
    for s in await client.sessions():
        if s.ID == session_id:
            return s
    raise SessionNotFoundError(session_id)


def _state_add_finding(
    db: Any,
    title: str,
    description: str,
    severity: str = "info",
    target_hostname: str = "",
) -> int:
    target_id = None
    if target_hostname:
        row = db.execute(
            "SELECT id FROM targets WHERE hostname = ?", (target_hostname,)
        ).fetchone()
        if row:
            target_id = row["id"]
    cur = db.execute(
        "INSERT INTO findings (title, severity, description, target_id) VALUES (?, ?, ?, ?)",
        (title, severity, description, target_id),
    )
    db.commit()
    return int(cur.lastrowid)


def _state_upsert_target_by_ip(
    db: Any,
    ip: str,
    *,
    hostname: str = "",
    os_name: str = "",
    notes: str = "",
) -> int:
    host = hostname or ip
    existing = db.execute(
        "SELECT id FROM targets WHERE ip = ? OR hostname = ?", (ip, host)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE targets SET ip=?, notes=COALESCE(NULLIF(?, ''), notes), "
            "updated_at=datetime('now') WHERE id=?",
            (ip, notes, existing["id"]),
        )
        db.commit()
        return int(existing["id"])
    cur = db.execute(
        "INSERT INTO targets (hostname, ip, os, notes) VALUES (?, ?, ?, ?)",
        (host, ip, os_name, notes),
    )
    db.commit()
    return int(cur.lastrowid)


def _state_upsert_service(
    db: Any,
    target_id: int,
    port: int,
    *,
    service_name: str = "",
    state: str = "open",
) -> None:
    row = db.execute(
        "SELECT id FROM target_services WHERE target_id = ? AND port = ?",
        (target_id, port),
    ).fetchone()
    if row:
        db.execute(
            "UPDATE target_services SET state=?, service_name=COALESCE(NULLIF(?, ''), service_name), "
            "discovered_at=datetime('now') WHERE id=?",
            (state, service_name, row["id"]),
        )
    else:
        db.execute(
            "INSERT INTO target_services (target_id, port, service_name, state) VALUES (?, ?, ?, ?)",
            (target_id, port, service_name, state),
        )
    db.commit()


def _start_playbook_run(db: Any, name: str, session_id: str) -> int:
    cur = db.execute(
        "INSERT INTO playbook_runs (playbook_name, session_id, status) VALUES (?, ?, ?)",
        (name, session_id, PlaybookStatus.RUNNING.value),
    )
    db.commit()
    return int(cur.lastrowid)


def _finish_playbook_run(
    db: Any,
    run_id: int,
    status: PlaybookStatus,
    summary: dict[str, Any],
) -> None:
    db.execute(
        "UPDATE playbook_runs SET status=?, summary_json=?, finished_at=datetime('now') WHERE id=?",
        (status.value, json.dumps(summary), run_id),
    )
    db.commit()


def _parse_ad_findings(sections: dict[str, str], hostname: str) -> list[tuple[str, str, str]]:
    """Return (title, description, severity) tuples from AD enum output."""
    findings: list[tuple[str, str, str]] = []
    da = sections.get("domain_admins", "")
    if da and "member" in da.lower():
        count = da.lower().count("member")
        if count:
            findings.append((
                "Domain Admins membership visible",
                f"Domain Admins group listing returned {count} member reference(s).",
                FindingSeverity.MEDIUM.value,
            ))
    dc = sections.get("domain_controllers", "")
    if dc and "\\\\" in dc:
        findings.append((
            "Domain controllers enumerated",
            "Domain Controllers group listing succeeded.",
            FindingSeverity.INFO.value,
        ))
    ca = sections.get("cert_authorities", "")
    if ca and "ca " in ca.lower():
        findings.append((
            "Certificate authorities discovered",
            "certutil exposed PKI / CA configuration details.",
            FindingSeverity.MEDIUM.value,
        ))
    trust = sections.get("domain_trust", "")
    if trust and "trusted" in trust.lower():
        findings.append((
            "Domain trusts enumerated",
            "nltest reported trust relationships for the domain.",
            FindingSeverity.INFO.value,
        ))
    return findings


async def sliver_playbook_ad_enum(session_id: str) -> str:
    """Active Directory enumeration playbook on a Windows domain-joined session.

    Runs nltest, whoami, net group, certutil, gpresult, and wmic via the
    implant. Auto-logs findings and ATT&CK techniques to the state database.

    Args:
        session_id: Target Sliver session ID.
    """
    tool = "sliver_playbook_ad_enum"
    try:
        sid = validate_session_id(session_id.strip())
        session = await _verify_session(sid)
        os_name = (getattr(session, "OS", "") or "").lower()
        if os_name and "windows" not in os_name:
            raise ValidationError(
                "session_id", sid, "AD enumeration requires a Windows session"
            )

        db = _ensure_reporting_schema()
        hostname = getattr(session, "Hostname", "") or ""
        run_id = _start_playbook_run(db, "ad_enum", sid)

        sections: dict[str, str] = {}
        steps: list[dict[str, Any]] = []
        techniques_logged: list[str] = []
        failed_steps = 0

        for key, exe, args, technique_ids in _AD_STEPS:
            output, ok = await _exec_step(sid, exe, args)
            sections[key] = output
            steps.append({
                "step": key,
                "command": f"{exe} {args}".strip(),
                "success": ok,
                "technique_ids": technique_ids,
            })
            if not ok:
                failed_steps += 1
            else:
                for tid in technique_ids:
                    db.execute(
                        """
                        INSERT INTO attack_techniques (
                            technique_id, tactic, name, tool_name,
                            session_id, outcome, evidence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tid,
                            _tactic_for_technique(tid),
                            key.replace("_", " ").title(),
                            tool,
                            sid,
                            "success",
                            output[:500],
                        ),
                    )
                    techniques_logged.append(tid)
        db.commit()
        log_technique(db, tool, sid, None, "ok")

        finding_ids: list[int] = []
        for title, desc, severity in _parse_ad_findings(sections, hostname):
            finding_ids.append(_state_add_finding(db, title, desc, severity, hostname))

        status = (
            PlaybookStatus.COMPLETED if failed_steps == 0
            else PlaybookStatus.PARTIAL if failed_steps < len(_AD_STEPS)
            else PlaybookStatus.FAILED
        )
        summary = {
            "hostname": hostname,
            "steps_completed": len(_AD_STEPS) - failed_steps,
            "steps_failed": failed_steps,
            "findings_logged": len(finding_ids),
            "attack_techniques_logged": sorted(set(techniques_logged)),
        }
        _finish_playbook_run(db, run_id, status, summary)

        return _success({
            "playbook": "ad_enum",
            "status": status.value,
            "summary": summary,
            "sections": sections,
            "steps": steps,
        })

    except Exception as exc:
        logger.exception("AD enum playbook failed")
        return _error(tool, exc)


def _tactic_for_technique(technique_id: str) -> str:
    for mappings in ATTACK_REGISTRY.values():
        for m in mappings:
            if m.technique_id == technique_id:
                return m.tactic
    return "Discovery"


def _hosts_in_cidr(cidr: str, max_hosts: int) -> list[str]:
    network = ipaddress.ip_network(cidr, strict=False)
    if network.num_addresses > max_hosts + 2:
        raise ValidationError(
            "cidr", cidr,
            f"network too large ({network.num_addresses} addresses); "
            f"max {max_hosts} hosts (set SLIVER_SWEEP_MAX_HOSTS to raise)",
        )
    return [str(h) for h in network.hosts()]


async def sliver_playbook_network_sweep(session_id: str, cidr: str) -> str:
    """Network discovery via implant: ping sweep and common-port checks.

    Ping-sweeps the CIDR range, then probes ports 445, 3389, 5985, 22, 80,
    and 443 on responding hosts. Upserts targets and services in the state DB.

    Args:
        session_id: Sliver session ID to run discovery from.
        cidr: Target network in CIDR notation (e.g. ``192.168.1.0/24``).
    """
    tool = "sliver_playbook_network_sweep"
    try:
        sid = validate_session_id(session_id.strip())
        cidr_val = validate_cidr(cidr.strip())
        await _verify_session(sid)

        max_hosts = int(os.environ.get("SLIVER_SWEEP_MAX_HOSTS", "256"))
        hosts = _hosts_in_cidr(cidr_val, max_hosts)

        db = _ensure_reporting_schema()
        run_id = _start_playbook_run(db, "network_sweep", sid)

        alive: list[str] = []
        batch_size = 32
        for i in range(0, len(hosts), batch_size):
            batch = hosts[i : i + batch_size]
            ps = (
                f"$ips=@({','.join(repr(ip) for ip in batch)});"
                "$ips | ForEach-Object { if (Test-Connection -ComputerName $_ -Count 1 -Quiet -ErrorAction SilentlyContinue) { $_ } }"
            )
            output, ok = await _exec_step(
                sid, "powershell.exe", f"-NoProfile -NonInteractive -Command {ps}"
            )
            if ok:
                for line in output.splitlines():
                    ip = line.strip()
                    if ip and _is_ipv4(ip):
                        alive.append(ip)

        if not alive and len(hosts) <= 16:
            for ip in hosts:
                out, ok = await _exec_step(sid, "ping", f"-n 1 -w 500 {ip}")
                if ok and ("ttl=" in out.lower() or "reply from" in out.lower()):
                    alive.append(ip)

        services_found: list[dict[str, Any]] = []
        for ip in alive:
            target_id = _state_upsert_target_by_ip(
                db, ip, notes=f"network_sweep {cidr_val}",
            )
            open_ports: list[int] = []
            for port in DEFAULT_SWEEP_PORTS:
                ps_port = (
                    f"$r = Test-NetConnection -ComputerName {ip} -Port {port} "
                    f"-WarningAction SilentlyContinue; if ($r.TcpTestSucceeded) {{ 'open' }}"
                )
                out, ok = await _exec_step(
                    sid, "powershell.exe",
                    f"-NoProfile -NonInteractive -Command {ps_port}",
                )
                if ok and "open" in out.lower():
                    open_ports.append(port)
                    svc_name = _service_name_for_port(port)
                    _state_upsert_service(db, target_id, port, service_name=svc_name)
                    services_found.append({
                        "ip": ip,
                        "port": port,
                        "service": svc_name,
                    })

        log_technique(db, tool, sid, None, "ok")
        status = PlaybookStatus.COMPLETED if alive else PlaybookStatus.PARTIAL
        summary = {
            "cidr": cidr_val,
            "hosts_scanned": len(hosts),
            "hosts_up": len(alive),
            "alive_hosts": alive,
            "ports_scanned": list(DEFAULT_SWEEP_PORTS),
            "services_found": services_found,
        }
        _finish_playbook_run(db, run_id, status, summary)

        return _success({
            "playbook": "network_sweep",
            "status": status.value,
            "summary": summary,
        })

    except Exception as exc:
        logger.exception("Network sweep playbook failed")
        return _error(tool, exc)


def _is_ipv4(value: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)
    except ValueError:
        return False


def _service_name_for_port(port: int) -> str:
    names = {
        22: "ssh",
        80: "http",
        443: "https",
        445: "smb",
        3389: "rdp",
        5985: "winrm",
    }
    return names.get(port, f"port-{port}")


def _query_coverage_gaps(db: Any) -> dict[str, list[str]]:
    from sliver_mcp.tools.attack_mapping import _build_registry_index, _query_technique_sets

    registry_index = _build_registry_index()
    exercised, _, _ = _query_technique_sets(db, "")
    gaps: dict[str, list[str]] = {}
    for tactic, techs in registry_index.items():
        available = set(techs.keys())
        gap = sorted(available - exercised)
        if gap:
            gaps[tactic] = gap
    return gaps


def _playbook_already_run(db: Any, name: str) -> bool:
    try:
        row = db.execute(
            "SELECT COUNT(*) AS c FROM playbook_runs WHERE playbook_name = ? AND status IN ('completed', 'partial')",
            (name,),
        ).fetchone()
        return bool(row and row["c"] > 0)
    except Exception:
        return False


def _has_target_services(db: Any) -> bool:
    try:
        row = db.execute("SELECT COUNT(*) AS c FROM target_services").fetchone()
        return bool(row and row["c"] > 0)
    except Exception:
        return False


def _domain_joined_sessions(sessions: list[Any]) -> list[Any]:
    joined = []
    for s in sessions:
        uname = getattr(s, "Username", "") or ""
        if "\\" in uname or "@" in uname:
            joined.append(s)
    return joined


def _build_recommendations(
    *,
    session_count: int,
    sessions: list[Any],
    coverage_pct: float,
    gaps: dict[str, list[str]],
    db: Any,
    critical_findings: int,
) -> list[RecommendedAction]:
    recs: list[RecommendedAction] = []
    priority = 1

    if session_count == 0:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_sessions",
            rationale="No active sessions — list implants to establish engagement context.",
            technique_ids=[],
            preconditions_met=True,
        ))
        priority += 1
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_generate",
            rationale="No callbacks — generate and deploy an implant if authorized.",
            technique_ids=["T1587.001"],
            preconditions_met=True,
        ))
        return recs[:10]

    if "Discovery" in gaps or coverage_pct < 20:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_discovery",
            rationale="Discovery tactic has coverage gaps — run host and network enumeration.",
            technique_ids=["T1082", "T1016"],
            preconditions_met=True,
        ))
        priority += 1

    if coverage_pct < 20:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_attack_coverage",
            rationale="Overall ATT&CK coverage is below 20% — review matrix before next actions.",
            technique_ids=[],
            preconditions_met=True,
        ))
        priority += 1

    user_sessions = [
        s for s in sessions
        if "administrator" not in (getattr(s, "Username", "") or "").lower()
        and "system" not in (getattr(s, "Username", "") or "").lower()
    ]
    if user_sessions and "Privilege Escalation" in gaps:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_playbook_privesc_check",
            rationale="User-level session with Privilege Escalation gaps — assess escalation paths.",
            technique_ids=["T1068"],
            preconditions_met=True,
        ))
        priority += 1

    if _domain_joined_sessions(sessions) and not _playbook_already_run(db, "ad_enum"):
        sid = _domain_joined_sessions(sessions)[0].ID
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_playbook_ad_enum",
            rationale="Domain-joined host without AD enumeration — run AD discovery playbook.",
            technique_ids=["T1087.002", "T1069.002"],
            preconditions_met=bool(sid),
        ))
        priority += 1

    if not _has_target_services(db) and sessions:
        sid = sessions[0].ID
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_playbook_network_sweep",
            rationale="No target services recorded — sweep adjacent network from implant.",
            technique_ids=["T1046", "T1018"],
            preconditions_met=bool(sid),
        ))
        priority += 1

    system_sessions = [
        s for s in sessions
        if "system" in (getattr(s, "Username", "") or "").lower()
    ]
    if system_sessions and "Credential Access" in gaps:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_process_dump",
            rationale="SYSTEM session with Credential Access gap — LSASS dump (high OPSEC risk).",
            technique_ids=["T1003.001"],
            preconditions_met=True,
        ))
        priority += 1

    if critical_findings:
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_state_findings",
            rationale=f"{critical_findings} critical finding(s) require operator review.",
            technique_ids=[],
            preconditions_met=True,
        ))
        priority += 1

    if not _playbook_already_run(db, "initial_recon"):
        recs.append(RecommendedAction(
            priority=priority,
            action="sliver_playbook_initial_recon",
            rationale="Initial recon playbook not completed — baseline target context.",
            technique_ids=["T1082", "T1518.001"],
            preconditions_met=True,
        ))
        priority += 1

    recs.sort(key=lambda r: (r.priority, r.action))
    return recs[:10]


async def sliver_suggest_next(session_id: str = "") -> str:
    """Deterministic rule-based advisor for prioritized next actions.

    Analyzes sessions, privilege levels, findings, and ATT&CK coverage gaps.
    Not an LLM — identical DB/session state yields identical recommendations.

    Args:
        session_id: Optional session context (reserved for future filtering).
    """
    tool = "sliver_suggest_next"
    try:
        if session_id and session_id.strip():
            validate_session_id(session_id.strip())

        db = _ensure_reporting_schema()
        from server import _get_client  # noqa: PLC0415

        client = await _get_client()
        sessions = await client.sessions()
        from sliver_mcp.tools.attack_mapping import _build_registry_index, _query_technique_sets

        registry_index = _build_registry_index()
        exercised, _, _ = _query_technique_sets(db, "")
        all_available: set[str] = set()
        for techs in registry_index.values():
            all_available.update(techs.keys())
        coverage_pct = (len(exercised) / len(all_available) * 100.0) if all_available else 0.0
        gaps = _query_coverage_gaps(db)

        critical = db.execute(
            "SELECT COUNT(*) AS c FROM findings WHERE severity = 'critical'"
        ).fetchone()["c"]

        recommendations = _build_recommendations(
            session_count=len(sessions),
            sessions=sessions,
            coverage_pct=coverage_pct,
            gaps=gaps,
            db=db,
            critical_findings=int(critical),
        )

        payload = {
            "coverage_percent": round(coverage_pct, 2),
            "tactic_gaps": {k: v[:5] for k, v in sorted(gaps.items())},
            "recommendations": [
                {
                    "priority": r.priority,
                    "action": r.action,
                    "rationale": r.rationale,
                    "technique_ids": r.technique_ids,
                    "preconditions_met": r.preconditions_met,
                }
                for r in recommendations
            ],
        }
        return _success(payload)

    except Exception as exc:
        logger.exception("suggest_next failed")
        return _error(tool, exc)
