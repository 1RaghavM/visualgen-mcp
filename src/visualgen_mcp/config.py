"""Environment loading, model ID mapping, and parameter validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from visualgen_mcp import profile as profile_mod

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
    """Runtime configuration resolved from env > profile > hard-coded defaults."""

    api_key: str
    output_dir: Path
    default_video_tier: str
    default_image_model: str
    default_video_aspect_ratio: str
    default_image_aspect_ratio: str

    @classmethod
    def from_env(cls) -> Config:
        """Resolve config from env > profile > hard-coded defaults.

        Creates `output_dir` if it does not exist. Raises `ValueError` if no
        API key resolves from any source.
        """
        prof = profile_mod.load_profile()

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key and prof is not None and prof.api_key:
            api_key = prof.api_key.strip()
        if not api_key:
            raise ValueError(
                "No Gemini API key found. Run `visualgen-mcp init` to set up "
                "your profile, or set `GEMINI_API_KEY` in your environment "
                "(e.g. in `.env` or your `.mcp.json` env block)."
            )

        raw_dir = os.environ.get("OUTPUT_DIR", "").strip()
        if not raw_dir and prof is not None and prof.output_dir:
            raw_dir = prof.output_dir
        if not raw_dir:
            raw_dir = "./generated"
        output_dir = Path(raw_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            api_key=api_key,
            output_dir=output_dir,
            default_video_tier=(prof.video_tier if prof and prof.video_tier else "fast"),
            default_image_model=(
                prof.image_model if prof and prof.image_model else "nano-banana"
            ),
            default_video_aspect_ratio=(
                prof.video_aspect_ratio if prof and prof.video_aspect_ratio else "16:9"
            ),
            default_image_aspect_ratio=(
                prof.image_aspect_ratio if prof and prof.image_aspect_ratio else "16:9"
            ),
        )


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
