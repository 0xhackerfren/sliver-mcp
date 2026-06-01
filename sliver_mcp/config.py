"""Environment variable resolution and path handling.

All configuration flows through this module. No other module should
read os.environ directly for Sliver MCP settings.
"""

from __future__ import annotations

import os
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def resolve_config_path() -> str:
    """Return Sliver operator config (.cfg) path."""
    raw = _env("SLIVER_CONFIG")
    if raw:
        return os.path.expanduser(raw)
    home = Path.home()
    default = home / ".sliver-client" / "configs"
    if default.is_dir():
        cfgs = sorted(default.glob("*.cfg"))
        if cfgs:
            return str(cfgs[0])
    raise FileNotFoundError(
        "No Sliver operator config found. Set SLIVER_CONFIG env var or place "
        "a .cfg file in ~/.sliver-client/configs/. Generate one with: "
        "sliver-server operator --name cursor --lhost localhost --save <path>"
    )


def resolve_project_root() -> Path:
    """Return project root directory."""
    raw = _env("SLIVER_PROJECT_ROOT")
    if raw:
        return Path(raw)
    here = Path(__file__).resolve().parent.parent
    if (here / "evasion").is_dir():
        return here
    return here


def resolve_evasion_dir() -> Path:
    """Return evasion scripts directory."""
    raw = _env("SLIVER_EVASION_DIR")
    if raw:
        return Path(raw)
    return resolve_project_root() / "evasion"


def resolve_evidence_dir() -> Path:
    """Return evidence collection output directory."""
    raw = _env("SLIVER_EVIDENCE_DIR", "/tmp/sliver-evidence")
    return Path(raw)


def resolve_state_db_path() -> str:
    """Return engagement state SQLite database path."""
    raw = _env("SLIVER_STATE_DB")
    if raw:
        return raw
    return str(resolve_project_root() / "engagement_state.db")


def get_opsec_mode() -> str:
    """Return OPSEC mode: 'warn', 'block', or 'silent'."""
    mode = _env("SLIVER_OPSEC_MODE", "warn").lower()
    if mode not in ("warn", "block", "silent"):
        return "warn"
    return mode


def get_state_key() -> str | None:
    """Return encryption key for credential at-rest encryption, or None."""
    return _env("SLIVER_STATE_KEY") or None
