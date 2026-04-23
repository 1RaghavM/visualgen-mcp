"""User-level profile stored at $XDG_CONFIG_HOME/visualgen-mcp/config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w


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


def save_profile(prof: Profile, path: Path | None = None) -> None:
    """Write the profile to disk with dir chmod 0700 and file chmod 0600."""
    target = path if path is not None else config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)

    data: dict[str, object] = {}
    if prof.api_key is not None:
        data["api_key"] = prof.api_key
    if prof.output_dir is not None:
        data["output_dir"] = prof.output_dir

    defaults: dict[str, object] = {}
    if prof.video_tier is not None:
        defaults["video_tier"] = prof.video_tier
    if prof.image_model is not None:
        defaults["image_model"] = prof.image_model
    if prof.video_aspect_ratio is not None:
        defaults["video_aspect_ratio"] = prof.video_aspect_ratio
    if prof.image_aspect_ratio is not None:
        defaults["image_aspect_ratio"] = prof.image_aspect_ratio
    if defaults:
        data["defaults"] = defaults

    with target.open("wb") as f:
        tomli_w.dump(data, f)
    os.chmod(target, 0o600)
