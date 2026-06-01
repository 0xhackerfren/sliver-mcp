"""SDK constraint surface: static MITRE ATT&CK technique registry.

Maps every MCP tool name to its ATT&CK technique ID(s) and tactic.
This is the authoritative mapping used by the audit logger and
sliver_attack_coverage tool. Technique IDs follow MITRE ATT&CK v15.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TechniqueMapping:
    technique_id: str
    name: str
    tactic: str
    subtechnique: str = ""


ATTACK_REGISTRY: dict[str, list[TechniqueMapping]] = {
    # -- Execution --
    "sliver_execute": [
        TechniqueMapping("T1059", "Command and Scripting Interpreter", "Execution"),
    ],
    "sliver_execute_assembly": [
        TechniqueMapping("T1055.012", "Process Hollowing", "Defense Evasion"),
        TechniqueMapping("T1059.001", "PowerShell", "Execution", "via .NET assembly"),
    ],
    "sliver_execute_shellcode": [
        TechniqueMapping("T1055", "Process Injection", "Defense Evasion"),
    ],
    "sliver_execute_bof": [
        TechniqueMapping("T1106", "Native API", "Execution"),
    ],
    "sliver_sideload": [
        TechniqueMapping("T1574.002", "DLL Side-Loading", "Defense Evasion"),
    ],

    # -- Privilege Escalation --
    "sliver_get_system": [
        TechniqueMapping("T1134.001", "Token Impersonation/Theft", "Privilege Escalation"),
    ],
    "sliver_impersonate": [
        TechniqueMapping("T1134.001", "Token Impersonation/Theft", "Privilege Escalation"),
    ],
    "sliver_make_token": [
        TechniqueMapping("T1134.003", "Make and Impersonate Token", "Privilege Escalation"),
    ],
    "sliver_run_as": [
        TechniqueMapping("T1134.002", "Create Process with Token", "Privilege Escalation"),
    ],

    # -- Process Injection / Migration --
    "sliver_migrate": [
        TechniqueMapping("T1055", "Process Injection", "Defense Evasion"),
    ],

    # -- Credential Access --
    "sliver_process_dump": [
        TechniqueMapping("T1003.001", "LSASS Memory", "Credential Access"),
    ],
    "sliver_playbook_cred_harvest": [
        TechniqueMapping("T1555", "Credentials from Password Stores", "Credential Access"),
        TechniqueMapping("T1552", "Unsecured Credentials", "Credential Access"),
    ],

    # -- Discovery --
    "sliver_discovery": [
        TechniqueMapping("T1082", "System Information Discovery", "Discovery"),
        TechniqueMapping("T1016", "System Network Configuration Discovery", "Discovery"),
        TechniqueMapping("T1049", "System Network Connections Discovery", "Discovery"),
        TechniqueMapping("T1033", "System Owner/User Discovery", "Discovery"),
        TechniqueMapping("T1069", "Permission Groups Discovery", "Discovery"),
    ],
    "sliver_ps": [
        TechniqueMapping("T1057", "Process Discovery", "Discovery"),
    ],
    "sliver_netstat": [
        TechniqueMapping("T1049", "System Network Connections Discovery", "Discovery"),
    ],
    "sliver_ifconfig": [
        TechniqueMapping("T1016", "System Network Configuration Discovery", "Discovery"),
    ],
    "sliver_ls": [
        TechniqueMapping("T1083", "File and Directory Discovery", "Discovery"),
    ],
    "sliver_get_env": [
        TechniqueMapping("T1082", "System Information Discovery", "Discovery"),
    ],
    "sliver_opsec_check": [
        TechniqueMapping("T1518.001", "Security Software Discovery", "Discovery"),
    ],
    "sliver_playbook_initial_recon": [
        TechniqueMapping("T1082", "System Information Discovery", "Discovery"),
        TechniqueMapping("T1016", "System Network Configuration Discovery", "Discovery"),
        TechniqueMapping("T1518.001", "Security Software Discovery", "Discovery"),
    ],

    # -- Lateral Movement --
    "sliver_lateral_check": [
        TechniqueMapping("T1046", "Network Service Discovery", "Discovery"),
    ],
    "sliver_psexec": [
        TechniqueMapping("T1569.002", "Service Execution", "Execution"),
        TechniqueMapping("T1021.002", "SMB/Windows Admin Shares", "Lateral Movement"),
    ],
    "sliver_wmi_exec": [
        TechniqueMapping("T1047", "Windows Management Instrumentation", "Execution"),
    ],
    "sliver_playbook_network_sweep": [
        TechniqueMapping("T1046", "Network Service Discovery", "Discovery"),
        TechniqueMapping("T1018", "Remote System Discovery", "Discovery"),
    ],

    # -- Persistence --
    "sliver_registry_write": [
        TechniqueMapping("T1112", "Modify Registry", "Defense Evasion"),
    ],
    "sliver_registry_create_key": [
        TechniqueMapping("T1112", "Modify Registry", "Defense Evasion"),
    ],
    "sliver_start_service": [
        TechniqueMapping("T1543.003", "Windows Service", "Persistence"),
    ],
    "sliver_playbook_persist_check": [
        TechniqueMapping("T1547.001", "Registry Run Keys / Startup Folder", "Persistence"),
        TechniqueMapping("T1053", "Scheduled Task/Job", "Persistence"),
    ],

    # -- Defense Evasion --
    "sliver_encrypt_shellcode": [
        TechniqueMapping("T1027", "Obfuscated Files or Information", "Defense Evasion"),
    ],
    "sliver_build_loaders": [
        TechniqueMapping("T1027.002", "Software Packing", "Defense Evasion"),
    ],
    "sliver_evasion_pipeline": [
        TechniqueMapping("T1027", "Obfuscated Files or Information", "Defense Evasion"),
    ],
    "sliver_revert_to_self": [
        TechniqueMapping("T1134", "Access Token Manipulation", "Defense Evasion"),
    ],

    # -- Collection --
    "sliver_screenshot": [
        TechniqueMapping("T1113", "Screen Capture", "Collection"),
    ],
    "sliver_download": [
        TechniqueMapping("T1005", "Data from Local System", "Collection"),
    ],
    "sliver_collect_evidence": [
        TechniqueMapping("T1005", "Data from Local System", "Collection"),
        TechniqueMapping("T1113", "Screen Capture", "Collection"),
    ],

    # -- Command and Control --
    "sliver_socks_start": [
        TechniqueMapping("T1090", "Proxy", "Command and Control"),
    ],
    "sliver_portfwd_add": [
        TechniqueMapping("T1090.001", "Internal Proxy", "Command and Control"),
    ],
    "sliver_start_https_listener": [
        TechniqueMapping("T1071.001", "Web Protocols", "Command and Control"),
    ],
    "sliver_start_http_listener": [
        TechniqueMapping("T1071.001", "Web Protocols", "Command and Control"),
    ],
    "sliver_start_dns_listener": [
        TechniqueMapping("T1071.004", "DNS", "Command and Control"),
    ],
    "sliver_start_mtls_listener": [
        TechniqueMapping("T1573.002", "Asymmetric Cryptography", "Command and Control"),
    ],
    "sliver_website_add": [
        TechniqueMapping("T1608.001", "Upload Malware", "Resource Development"),
    ],
    "sliver_generate": [
        TechniqueMapping("T1587.001", "Malware", "Resource Development"),
    ],

    # -- Impact --
    "sliver_rm": [
        TechniqueMapping("T1070.004", "File Deletion", "Defense Evasion"),
    ],
    "sliver_cleanup_target": [
        TechniqueMapping("T1070.004", "File Deletion", "Defense Evasion"),
    ],

    # -- Active Directory --
    "sliver_playbook_ad_enum": [
        TechniqueMapping("T1087.002", "Domain Account", "Discovery"),
        TechniqueMapping("T1069.002", "Domain Groups", "Discovery"),
        TechniqueMapping("T1615", "Group Policy Discovery", "Discovery"),
        TechniqueMapping("T1482", "Domain Trust Discovery", "Discovery"),
    ],
    "sliver_playbook_privesc_check": [
        TechniqueMapping("T1068", "Exploitation for Privilege Escalation", "Privilege Escalation"),
    ],

    # -- Exfiltration --
    "sliver_upload": [
        TechniqueMapping("T1105", "Ingress Tool Transfer", "Command and Control"),
    ],
}


def get_techniques_for_tool(tool_name: str) -> list[TechniqueMapping]:
    """Return ATT&CK technique mappings for a tool, or empty list."""
    return ATTACK_REGISTRY.get(tool_name, [])


def get_all_tactics() -> list[str]:
    """Return deduplicated sorted list of all tactics in the registry."""
    tactics: set[str] = set()
    for mappings in ATTACK_REGISTRY.values():
        for m in mappings:
            tactics.add(m.tactic)
    return sorted(tactics)


def get_all_tool_names() -> list[str]:
    """Return all tool names that have ATT&CK mappings."""
    return sorted(ATTACK_REGISTRY.keys())


def get_tools_by_tactic(tactic: str) -> dict[str, list[TechniqueMapping]]:
    """Return tools mapped to the given tactic."""
    result: dict[str, list[TechniqueMapping]] = {}
    for tool, mappings in ATTACK_REGISTRY.items():
        matches = [m for m in mappings if m.tactic == tactic]
        if matches:
            result[tool] = matches
    return result
