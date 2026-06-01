# Changelog

## [1.0.0] - 2026-05-20

### Added
- **79 MCP tools** covering the full Sliver C2 operator workflow
- **Evasion pipeline** with Nim-based loaders, AES-256-CBC encryption, indirect syscalls, and Defender bypass
- **Raw protobuf wire-format generation** fixing `sliver-py` 0.0.19 incompatibility with Sliver 1.7.3+
- **Engagement state database** (SQLite) tracking targets, credentials, access events, findings, and pivot paths
- **OPSEC guard** with EDR/AV detection for 16 security products and pre-flight checks on high-risk tools
- **Operator playbooks** for initial recon, privesc assessment, credential harvesting, and persistence auditing
- **Portable configuration** via environment variables with auto-detection fallbacks
- **Cleanup manifest** for configurable artifact removal
- Support for Cursor IDE, Claude Desktop, and generic MCP clients
- `pyproject.toml` packaging with console script entry point
