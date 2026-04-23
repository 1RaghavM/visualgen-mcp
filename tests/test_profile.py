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


def test_load_profile_returns_none_when_missing(tmp_path: Path) -> None:
    assert profile.load_profile(tmp_path / "nope.toml") is None


def test_load_profile_reads_all_fields(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        'api_key = "k-1"\n'
        'output_dir = "~/out"\n'
        "\n"
        "[defaults]\n"
        'video_tier = "standard"\n'
        'image_model = "imagen"\n'
        'video_aspect_ratio = "9:16"\n'
        'image_aspect_ratio = "1:1"\n'
    )
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "k-1"
    assert prof.output_dir == "~/out"
    assert prof.video_tier == "standard"
    assert prof.image_model == "imagen"
    assert prof.video_aspect_ratio == "9:16"
    assert prof.image_aspect_ratio == "1:1"


def test_load_profile_missing_optional_fields(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('api_key = "only-key"\n')
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "only-key"
    assert prof.output_dir is None
    assert prof.video_tier is None


def test_load_profile_ignores_unknown_keys(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        'api_key = "k"\n'
        'future_thing = "ignored"\n'
        "\n"
        "[defaults]\n"
        'future_default = "also-ignored"\n'
    )
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "k"


def test_load_profile_malformed_raises_with_path(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text("this = is = not = toml")
    with pytest.raises(ValueError, match=str(p)):
        profile.load_profile(p)
