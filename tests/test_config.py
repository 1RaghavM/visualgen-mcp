"""Tests for config loading and parameter validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from visualgen_mcp import config


def test_resolve_video_model_fast() -> None:
    assert config.resolve_video_model("fast") == "veo-3.1-fast-generate-preview"


def test_resolve_video_model_standard() -> None:
    assert config.resolve_video_model("standard") == "veo-3.1-generate-preview"


def test_resolve_video_model_lite() -> None:
    assert config.resolve_video_model("lite") == "veo-3.1-lite-generate-preview"


def test_resolve_video_model_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown video tier"):
        config.resolve_video_model("turbo")


def test_resolve_image_model_nano_banana() -> None:
    assert config.resolve_image_model("nano-banana") == "gemini-2.5-flash-image"


def test_resolve_image_model_imagen() -> None:
    assert config.resolve_image_model("imagen") == "imagen-4.0-generate-001"


def test_resolve_image_model_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown image model"):
        config.resolve_image_model("dalle")


def test_validate_video_params_fast_720p_ok() -> None:
    config.validate_video_params("fast", "16:9", "720p")


def test_validate_video_params_fast_4k_ok() -> None:
    config.validate_video_params("fast", "9:16", "4k")


def test_validate_video_params_rejects_lite_4k() -> None:
    with pytest.raises(ValueError, match="lite"):
        config.validate_video_params("lite", "16:9", "4k")


def test_validate_video_params_allows_lite_1080p() -> None:
    config.validate_video_params("lite", "16:9", "1080p")


def test_validate_video_params_bad_aspect() -> None:
    with pytest.raises(ValueError, match="aspect_ratio"):
        config.validate_video_params("fast", "1:1", "720p")


def test_validate_video_params_bad_resolution() -> None:
    with pytest.raises(ValueError, match="resolution"):
        config.validate_video_params("fast", "16:9", "480p")


def test_validate_image_params_all_valid() -> None:
    for ar in ["1:1", "16:9", "9:16", "4:3", "3:4"]:
        config.validate_image_params(ar)


def test_validate_image_params_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="aspect_ratio"):
        config.validate_image_params("21:9")


def test_config_from_env_loads_key_and_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    out = tmp_path / "gen"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc")
    monkeypatch.setenv("OUTPUT_DIR", str(out))
    c = config.Config.from_env()
    assert c.api_key == "test-key-abc"
    assert c.output_dir == out.resolve()
    assert c.output_dir.exists()


def test_config_from_env_creates_nested_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    out = tmp_path / "a" / "b" / "c"
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("OUTPUT_DIR", str(out))
    c = config.Config.from_env()
    assert c.output_dir.exists()


def test_config_from_env_defaults_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    c = config.Config.from_env()
    assert c.output_dir == (tmp_path / "generated").resolve()


def test_config_from_env_missing_key_signposts_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="visualgen-mcp init"):
        config.Config.from_env()


def test_config_from_env_empty_key_signposts_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="visualgen-mcp init"):
        config.Config.from_env()


def test_config_from_env_uses_profile_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    profile.save_profile(profile.Profile(api_key="profile-key"))
    c = config.Config.from_env()
    assert c.api_key == "profile-key"


def test_config_from_env_env_overrides_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.chdir(tmp_path)
    profile.save_profile(profile.Profile(api_key="profile-key"))
    c = config.Config.from_env()
    assert c.api_key == "env-key"


def test_config_from_env_defaults_from_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.chdir(tmp_path)
    profile.save_profile(
        profile.Profile(
            api_key="k",
            video_tier="standard",
            image_model="imagen",
            video_aspect_ratio="9:16",
            image_aspect_ratio="1:1",
        )
    )
    c = config.Config.from_env()
    assert c.default_video_tier == "standard"
    assert c.default_image_model == "imagen"
    assert c.default_video_aspect_ratio == "9:16"
    assert c.default_image_aspect_ratio == "1:1"


def test_config_from_env_hardcoded_defaults_when_no_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    c = config.Config.from_env()
    assert c.default_video_tier == "fast"
    assert c.default_image_model == "nano-banana"
    assert c.default_video_aspect_ratio == "16:9"
    assert c.default_image_aspect_ratio == "16:9"
