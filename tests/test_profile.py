"""Tests for the user-level profile at ~/.config/visualgen-mcp/config.toml."""

from __future__ import annotations

from pathlib import Path

import pytest

from visualgen_mcp import profile


def test_config_path_honors_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / "visualgen-mcp" / "config.toml"


def test_config_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / ".config" / "visualgen-mcp" / "config.toml"


def test_config_path_ignores_empty_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "   ")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / ".config" / "visualgen-mcp" / "config.toml"
