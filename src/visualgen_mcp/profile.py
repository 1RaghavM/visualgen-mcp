"""User-level profile stored at $XDG_CONFIG_HOME/visualgen-mcp/config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    """Values loaded from the TOML profile. All fields are optional."""

    api_key: str | None = None
    output_dir: str | None = None
    video_tier: str | None = None
    image_model: str | None = None
    video_aspect_ratio: str | None = None
    image_aspect_ratio: str | None = None


def config_path() -> Path:
    """Resolve the profile path, honoring XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "visualgen-mcp" / "config.toml"


def load_profile(path: Path | None = None) -> Profile | None:
    """Load the profile from disk. Returns None if the file doesn't exist.

    Raises ValueError (with the path) if the file exists but can't be parsed.
    """
    target = path if path is not None else config_path()
    if not target.exists():
        return None
    try:
        with target.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed profile at {target}: {exc}") from exc
    defaults = data.get("defaults", {})
    return Profile(
        api_key=data.get("api_key"),
        output_dir=data.get("output_dir"),
        video_tier=defaults.get("video_tier"),
        image_model=defaults.get("image_model"),
        video_aspect_ratio=defaults.get("video_aspect_ratio"),
        image_aspect_ratio=defaults.get("image_aspect_ratio"),
    )
