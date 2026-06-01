"""Test molds for MITRE ATT&CK registry (FEAT-1).

Derived from docs/features.md FEAT-1.B-1 through FEAT-1.B-3.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdk.attack_map import (
    ATTACK_REGISTRY,
    get_all_tactics,
    get_all_tool_names,
    get_techniques_for_tool,
    get_tools_by_tactic,
)


class TestAttackRegistry:
    """FEAT-1.B-1: Static registry must map tools to ATT&CK techniques."""

    def test_registry_not_empty(self) -> None:
        assert len(ATTACK_REGISTRY) > 0

    def test_high_risk_tools_mapped(self) -> None:
        """All OPSEC high-risk tools must have ATT&CK mappings."""
        high_risk = [
            "sliver_execute_assembly",
            "sliver_execute_shellcode",
            "sliver_sideload",
            "sliver_get_system",
            "sliver_process_dump",
            "sliver_migrate",
            "sliver_make_token",
            "sliver_registry_write",
            "sliver_registry_create_key",
            "sliver_start_service",
        ]
        for tool in high_risk:
            assert tool in ATTACK_REGISTRY, f"{tool} missing ATT&CK mapping"

    def test_every_mapping_has_required_fields(self) -> None:
        for tool, mappings in ATTACK_REGISTRY.items():
            for m in mappings:
                assert m.technique_id, f"{tool}: missing technique_id"
                assert m.name, f"{tool}: missing name"
                assert m.tactic, f"{tool}: missing tactic"

    def test_technique_ids_format(self) -> None:
        """Technique IDs must match T#### or T####.### format."""
        import re
        pattern = re.compile(r"^T\d{4}(\.\d{3})?$")
        for tool, mappings in ATTACK_REGISTRY.items():
            for m in mappings:
                assert pattern.match(m.technique_id), (
                    f"{tool}: invalid technique ID format: {m.technique_id}"
                )

    def test_discovery_tools_mapped(self) -> None:
        discovery_tools = [
            "sliver_discovery",
            "sliver_ps",
            "sliver_netstat",
            "sliver_ifconfig",
            "sliver_ls",
        ]
        for tool in discovery_tools:
            assert tool in ATTACK_REGISTRY

    def test_execution_tools_mapped(self) -> None:
        exec_tools = [
            "sliver_execute",
            "sliver_execute_assembly",
            "sliver_execute_shellcode",
            "sliver_sideload",
        ]
        for tool in exec_tools:
            assert tool in ATTACK_REGISTRY


class TestGetTechniquesForTool:
    def test_known_tool(self) -> None:
        techs = get_techniques_for_tool("sliver_execute")
        assert len(techs) >= 1
        assert techs[0].technique_id == "T1059"

    def test_unknown_tool_returns_empty(self) -> None:
        assert get_techniques_for_tool("sliver_nonexistent") == []


class TestGetAllTactics:
    def test_includes_core_tactics(self) -> None:
        tactics = get_all_tactics()
        expected = [
            "Execution",
            "Discovery",
            "Privilege Escalation",
            "Defense Evasion",
            "Credential Access",
            "Lateral Movement",
            "Collection",
            "Command and Control",
        ]
        for t in expected:
            assert t in tactics, f"Missing tactic: {t}"


class TestGetToolsByTactic:
    def test_discovery_tactic(self) -> None:
        tools = get_tools_by_tactic("Discovery")
        assert "sliver_ps" in tools
        assert "sliver_discovery" in tools

    def test_empty_tactic(self) -> None:
        tools = get_tools_by_tactic("Nonexistent Tactic")
        assert len(tools) == 0


class TestGetAllToolNames:
    def test_returns_sorted(self) -> None:
        names = get_all_tool_names()
        assert names == sorted(names)

    def test_all_in_registry(self) -> None:
        names = get_all_tool_names()
        for name in names:
            assert name in ATTACK_REGISTRY
