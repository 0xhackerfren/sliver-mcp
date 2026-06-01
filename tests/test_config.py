"""Tests for sliver_mcp.config module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sliver_mcp.config import (
    get_opsec_mode,
    get_state_key,
    resolve_config_path,
    resolve_evasion_dir,
    resolve_evidence_dir,
    resolve_project_root,
    resolve_state_db_path,
)


class TestResolveConfigPath:
    def test_env_override(self, tmp_path: Path) -> None:
        cfg = tmp_path / "operator.cfg"
        cfg.write_text("{}")
        with patch.dict(os.environ, {"SLIVER_CONFIG": str(cfg)}):
            assert resolve_config_path() == str(cfg)

    def test_env_with_tilde(self) -> None:
        with patch.dict(os.environ, {"SLIVER_CONFIG": "~/test.cfg"}):
            result = resolve_config_path()
            assert "~" not in result

    def test_auto_discover(self, tmp_path: Path) -> None:
        configs_dir = tmp_path / ".sliver-client" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "default.cfg").write_text("{}")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("sliver_mcp.config.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("SLIVER_CONFIG", None)
            result = resolve_config_path()
            assert result.endswith("default.cfg")

    def test_no_config_raises(self, tmp_path: Path) -> None:
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("sliver_mcp.config.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("SLIVER_CONFIG", None)
            with pytest.raises(FileNotFoundError, match="No Sliver operator config"):
                resolve_config_path()


class TestResolveProjectRoot:
    def test_env_override(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"SLIVER_PROJECT_ROOT": str(tmp_path)}):
            assert resolve_project_root() == tmp_path

    def test_default_uses_parent(self) -> None:
        os.environ.pop("SLIVER_PROJECT_ROOT", None)
        root = resolve_project_root()
        assert root.is_dir()


class TestResolveEvasionDir:
    def test_env_override(self, tmp_path: Path) -> None:
        evasion = tmp_path / "my_evasion"
        with patch.dict(os.environ, {"SLIVER_EVASION_DIR": str(evasion)}):
            assert resolve_evasion_dir() == evasion

    def test_default_joins_project_root(self) -> None:
        os.environ.pop("SLIVER_EVASION_DIR", None)
        result = resolve_evasion_dir()
        assert str(result).endswith("evasion")


class TestResolveEvidenceDir:
    def test_env_override(self, tmp_path: Path) -> None:
        ev = tmp_path / "evidence_custom"
        with patch.dict(os.environ, {"SLIVER_EVIDENCE_DIR": str(ev)}):
            assert resolve_evidence_dir() == ev

    def test_default_path(self) -> None:
        os.environ.pop("SLIVER_EVIDENCE_DIR", None)
        result = resolve_evidence_dir()
        assert "sliver-evidence" in str(result)


class TestResolveStateDbPath:
    def test_env_override(self, tmp_path: Path) -> None:
        db = tmp_path / "custom.db"
        with patch.dict(os.environ, {"SLIVER_STATE_DB": str(db)}):
            assert resolve_state_db_path() == str(db)

    def test_default_in_project_root(self) -> None:
        os.environ.pop("SLIVER_STATE_DB", None)
        result = resolve_state_db_path()
        assert result.endswith("engagement_state.db")


class TestGetOpsecMode:
    @pytest.mark.parametrize("value,expected", [
        ("warn", "warn"),
        ("block", "block"),
        ("silent", "silent"),
        ("WARN", "warn"),
        ("BLOCK", "block"),
    ])
    def test_valid_modes(self, value: str, expected: str) -> None:
        with patch.dict(os.environ, {"SLIVER_OPSEC_MODE": value}):
            assert get_opsec_mode() == expected

    def test_invalid_falls_back_to_warn(self) -> None:
        with patch.dict(os.environ, {"SLIVER_OPSEC_MODE": "yolo"}):
            assert get_opsec_mode() == "warn"

    def test_default_is_warn(self) -> None:
        os.environ.pop("SLIVER_OPSEC_MODE", None)
        assert get_opsec_mode() == "warn"


class TestGetStateKey:
    def test_returns_key_when_set(self) -> None:
        with patch.dict(os.environ, {"SLIVER_STATE_KEY": "my-secret-key"}):
            assert get_state_key() == "my-secret-key"

    def test_returns_none_when_empty(self) -> None:
        with patch.dict(os.environ, {"SLIVER_STATE_KEY": ""}):
            assert get_state_key() is None

    def test_returns_none_when_missing(self) -> None:
        os.environ.pop("SLIVER_STATE_KEY", None)
        assert get_state_key() is None
