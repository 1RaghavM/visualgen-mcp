"""Environment loading, model ID mapping, and parameter validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VIDEO_MODELS: dict[str, str] = {
    "lite": "veo-3.1-lite-generate-preview",
    "fast": "veo-3.1-fast-generate-preview",
    "standard": "veo-3.1-generate-preview",
}

IMAGE_MODELS: dict[str, str] = {
    "nano-banana": "gemini-2.5-flash-image",
    "imagen": "imagen-4.0-generate-001",
}

VIDEO_ASPECT_RATIOS: frozenset[str] = frozenset({"16:9", "9:16"})
VIDEO_RESOLUTIONS: frozenset[str] = frozenset({"720p", "1080p", "4k"})
IMAGE_ASPECT_RATIOS: frozenset[str] = frozenset({"1:1", "16:9", "9:16", "4:3", "3:4"})

DEFAULT_VIDEO_DURATION_SECONDS: int = 8


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from the environment."""

    api_key: str
    output_dir: Path

    @classmethod
    def from_env(cls) -> Config:
        """Build a Config from `GEMINI_API_KEY` and `OUTPUT_DIR` env vars.

        Creates `output_dir` if it does not exist. Raises `ValueError` if
        `GEMINI_API_KEY` is missing or empty.
        """
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Get a key at https://aistudio.google.com/apikey and add it "
                "to your .env file or your MCP client's env config."
            )
        raw_dir = os.environ.get("OUTPUT_DIR", "./generated").strip() or "./generated"
        output_dir = Path(raw_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return cls(api_key=api_key, output_dir=output_dir)


def resolve_video_model(tier: str) -> str:
    """Map a user-facing tier name to the Veo model ID."""
    try:
        return VIDEO_MODELS[tier]
    except KeyError as exc:
        valid = sorted(VIDEO_MODELS)
        raise ValueError(f"Unknown video tier {tier!r}. Valid tiers: {valid}") from exc


def resolve_image_model(alias: str) -> str:
    """Map a user-facing image model alias to the underlying model ID."""
    try:
        return IMAGE_MODELS[alias]
    except KeyError as exc:
        valid = sorted(IMAGE_MODELS)
        raise ValueError(f"Unknown image model {alias!r}. Valid models: {valid}") from exc


def validate_video_params(tier: str, aspect_ratio: str, resolution: str) -> None:
    """Reject invalid combinations before spending money on an API call."""
    if aspect_ratio not in VIDEO_ASPECT_RATIOS:
        valid = sorted(VIDEO_ASPECT_RATIOS)
        raise ValueError(f"Invalid aspect_ratio {aspect_ratio!r}. Valid: {valid}")
    if resolution not in VIDEO_RESOLUTIONS:
        valid = sorted(VIDEO_RESOLUTIONS)
        raise ValueError(f"Invalid resolution {resolution!r}. Valid: {valid}")
    if tier == "lite" and resolution == "4k":
        raise ValueError(
            "Resolution '4k' is not supported on the 'lite' tier. "
            "Use '720p' or '1080p', or switch to 'fast' or 'standard'."
        )


def validate_image_params(aspect_ratio: str) -> None:
    """Reject invalid image aspect ratios."""
    if aspect_ratio not in IMAGE_ASPECT_RATIOS:
        valid = sorted(IMAGE_ASPECT_RATIOS)
        raise ValueError(f"Invalid aspect_ratio {aspect_ratio!r}. Valid: {valid}")
