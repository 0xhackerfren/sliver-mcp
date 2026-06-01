"""SDK constraint surface: domain types and response envelope.

All tool implementations must return ToolResponse. All state DB records
must use the dataclasses defined here. This module is the single source
of truth for shapes crossing module boundaries.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Response envelope
# ---------------------------------------------------------------------------

class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"  # OPSEC guard prevented execution


@dataclass
class ToolResponse:
    """Standardized response envelope returned by every MCP tool."""

    status: ToolStatus
    data: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    hints: list[str] = field(default_factory=list)
    attack_technique: str | None = None  # e.g. "T1059"
    duration_ms: int | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status.value}
        if self.data is not None:
            out["data"] = self.data
        if self.error is not None:
            out["error"] = self.error
        if self.error_type is not None:
            out["error_type"] = self.error_type
        if self.hints:
            out["hints"] = self.hints
        if self.attack_technique is not None:
            out["attack_technique"] = self.attack_technique
        if self.duration_ms is not None:
            out["duration_ms"] = self.duration_ms
        return out


# ---------------------------------------------------------------------------
# Engagement state models
# ---------------------------------------------------------------------------

class AccessLevel(str, enum.Enum):
    UNKNOWN = "unknown"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class NetworkZone(str, enum.Enum):
    INTERNAL = "internal"
    DMZ = "dmz"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CredentialType(str, enum.Enum):
    PASSWORD = "password"
    HASH_NTLM = "hash_ntlm"
    HASH_NET_NTLM = "hash_net_ntlm"
    KERBEROS_TICKET = "kerberos_ticket"
    SSH_KEY = "ssh_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    API_KEY = "api_key"
    OTHER = "other"


class PivotStatus(str, enum.Enum):
    PLANNED = "planned"
    VALIDATED = "validated"
    ACTIVE = "active"


class ActionOutcome(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    BLOCKED = "blocked"


class TechniqueOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class PlaybookStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ServiceState(str, enum.Enum):
    OPEN = "open"
    FILTERED = "filtered"
    CLOSED = "closed"


class IncidentType(str, enum.Enum):
    EDR_DETECTED = "edr_detected"
    BLOCKED_TOOL = "blocked_tool"
    NOISY_COMMAND = "noisy_command"


@dataclass
class Target:
    hostname: str
    ip_address: str
    os: str = ""
    access_level: AccessLevel = AccessLevel.UNKNOWN
    network_zone: NetworkZone = NetworkZone.UNKNOWN
    edr_products: list[str] = field(default_factory=list)
    notes: str = ""
    last_seen_session_id: str = ""
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Credential:
    username: str
    secret: str  # encrypted at rest via Fernet (SEC-5)
    cred_type: CredentialType = CredentialType.PASSWORD
    domain: str = ""
    source: str = ""
    target_id: int | None = None
    id: int | None = None
    created_at: str = ""


@dataclass
class Finding:
    title: str
    description: str
    severity: FindingSeverity = FindingSeverity.INFO
    target_id: int | None = None
    attack_technique_id: str = ""
    evidence: str = ""
    id: int | None = None
    created_at: str = ""


@dataclass
class AccessLog:
    tool_name: str
    session_id: str = ""
    target_id: int | None = None
    outcome: ActionOutcome = ActionOutcome.OK
    attack_technique_id: str = ""
    duration_ms: int = 0
    details_json: str = ""
    parameters_redacted: str = ""
    id: int | None = None
    timestamp: str = ""


@dataclass
class PivotPath:
    source_target_id: int
    dest_target_id: int
    via: str = ""
    status: PivotStatus = PivotStatus.PLANNED
    id: int | None = None
    created_at: str = ""


@dataclass
class AttackTechniqueRecord:
    technique_id: str  # e.g. "T1055.012"
    tactic: str  # e.g. "Defense Evasion"
    name: str
    tool_name: str
    session_id: str = ""
    target_id: int | None = None
    outcome: TechniqueOutcome = TechniqueOutcome.UNKNOWN
    evidence: str = ""
    id: int | None = None
    timestamp: str = ""


@dataclass
class TargetService:
    target_id: int
    port: int
    protocol: str = "tcp"
    service_name: str = ""
    state: ServiceState = ServiceState.OPEN
    banner: str = ""
    id: int | None = None
    discovered_at: str = ""


@dataclass
class OpsecIncident:
    session_id: str
    incident_type: IncidentType
    severity: FindingSeverity
    description: str
    tool_name: str = ""
    id: int | None = None
    timestamp: str = ""


@dataclass
class PlaybookRun:
    playbook_name: str
    session_id: str
    status: PlaybookStatus = PlaybookStatus.RUNNING
    summary_json: str = ""
    id: int | None = None
    started_at: str = ""
    finished_at: str = ""


@dataclass
class EngagementMeta:
    key: str
    value: str  # JSON-encoded
    updated_at: str = ""


# ---------------------------------------------------------------------------
# Value objects for features
# ---------------------------------------------------------------------------

@dataclass
class TechniqueRegistryEntry:
    """Static ATT&CK technique mapping loaded from attack_registry.json."""
    technique_id: str
    name: str
    tactic: str
    subtechnique_name: str = ""
    description: str = ""
    platforms: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)


@dataclass
class TacticCoverage:
    tactic: str
    available: list[str] = field(default_factory=list)  # technique IDs
    exercised: list[str] = field(default_factory=list)
    gap: list[str] = field(default_factory=list)


@dataclass
class AttackCoverageMatrix:
    tactics: list[TacticCoverage] = field(default_factory=list)
    total_available: int = 0
    total_exercised: int = 0
    coverage_pct: float = 0.0


@dataclass
class SessionScore:
    session_id: str
    score: float  # 0-100
    rank: int = 0
    factors: dict[str, Any] = field(default_factory=dict)


@dataclass
class PivotHop:
    source_session_id: str
    dest_target_ip: str
    via_subnet: str = ""
    confidence: str = "medium"  # high, medium, low


@dataclass
class RecommendedAction:
    priority: int
    action: str  # tool name or playbook
    rationale: str
    technique_ids: list[str] = field(default_factory=list)
    preconditions_met: bool = True


@dataclass
class OpsecScanResult:
    safe: bool
    products_detected: list[str] = field(default_factory=list)
    warning: str = ""
    scan_error: str = ""


@dataclass
class SessionInfo:
    session_id: str
    name: str = ""
    hostname: str = ""
    username: str = ""
    os: str = ""
    arch: str = ""
    remote_address: str = ""
    pid: int = 0
    active_c2: str = ""
    transport: str = ""
    is_beacon: bool = False
    last_checkin: str = ""
    privilege_level: AccessLevel = AccessLevel.UNKNOWN
